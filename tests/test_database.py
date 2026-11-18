"""
Automated unit tests for the PostgreSQL database foundation.
Tests PostgreSQL connectivity, session lifecycle, transaction rollbacks,
idempotent seeding, foreign-key constraints, and JSONB serialization
using an isolated PostgreSQL test database ('chatbot_flow_builder_test').
"""

import concurrent.futures
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest
import uuid

# Ensure backend and test directories are in Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import DEFAULT_CHATBOT_ID, get_utc_now, get_utc_now_iso
from app.models import Base, Chatbot, Flow, NodeDefinition
from tests.test_config import (
    clean_isolated_test_db,
    init_isolated_test_db,
    test_engine,
    TestingSessionLocal,
)


class TestDatabaseFoundation(unittest.TestCase):
    """Test suite for PostgreSQL database operations, sessions, and constraints."""

    def setUp(self):
        """Initialize clean tables in the isolated test database."""
        clean_isolated_test_db()
        init_isolated_test_db()

    def tearDown(self):
        """Clean all tables in the isolated test database."""
        clean_isolated_test_db()

    def test_database_connection(self):
        """Verify PostgreSQL engine connects successfully and executes queries."""
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT 1;")).scalar()
            self.assertEqual(result, 1)

    def test_init_db_creates_required_tables_and_indexes(self):
        """Verify all three tables and required indexes exist in PostgreSQL."""
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        for t in ["chatbots", "flows", "node_definitions"]:
            self.assertIn(t, tables, f"Missing table in PostgreSQL: {t}")

        # Check composite index on node_definitions
        indexes = [idx["name"] for idx in inspector.get_indexes("node_definitions")]
        self.assertIn("idx_node_definitions_filter", indexes)

    def test_init_db_is_idempotent(self):
        """Verify repeated initialization calls do not duplicate seed records."""
        with TestingSessionLocal() as session:
            init_bots = session.query(Chatbot).count()
            init_nodes = session.query(NodeDefinition).count()

        # Run initialization again twice
        init_isolated_test_db()
        init_isolated_test_db()

        with TestingSessionLocal() as session:
            final_bots = session.query(Chatbot).count()
            final_nodes = session.query(NodeDefinition).count()

        self.assertEqual(init_bots, final_bots)
        self.assertEqual(init_nodes, final_nodes)

    def test_insert_and_query_flow_with_jsonb(self):
        """Verify inserting and querying a flow using SQLAlchemy and PostgreSQL JSONB."""
        flow_id = str(uuid.uuid4())
        now = get_utc_now()
        flow_data_payload = {
            "nodes": [
                {"id": "node-1", "type": "start", "position": {"x": 50, "y": 100}, "data": {"label": "Start"}},
                {"id": "node-2", "type": "message", "position": {"x": 300, "y": 100}, "data": {"text": "Hello"}},
            ],
            "edges": [
                {"id": "edge-1", "source": "node-1", "target": "node-2"}
            ]
        }

        with TestingSessionLocal() as session:
            flow = Flow(
                id=flow_id,
                chatbot_id=DEFAULT_CHATBOT_ID,
                name="Customer Support Flow",
                description="Handles initial greetings",
                flow_data=flow_data_payload,
                created_at=now,
                updated_at=now,
            )
            session.add(flow)
            session.commit()

        # Query back and verify integrity
        with TestingSessionLocal() as session:
            saved_flow = session.get(Flow, flow_id)
            self.assertIsNotNone(saved_flow)
            self.assertEqual(saved_flow.name, "Customer Support Flow")
            self.assertEqual(saved_flow.chatbot_id, DEFAULT_CHATBOT_ID)
            self.assertEqual(saved_flow.flow_data, flow_data_payload)
            self.assertEqual(len(saved_flow.flow_data["nodes"]), 2)
            self.assertEqual(len(saved_flow.flow_data["edges"]), 1)

    def test_session_error_rolls_back_transaction(self):
        """Verify session.rollback() cleanly reverts partial writes on exception."""
        bot_id = f"bot-rollback-{uuid.uuid4().hex[:6]}"
        now = get_utc_now()

        session = TestingSessionLocal()
        try:
            bot = Chatbot(
                id=bot_id,
                name="Rollback Bot",
                status="active",
                created_at=now,
                updated_at=now,
            )
            session.add(bot)
            session.flush()

            # Simulate an unhandled exception before commit
            raise RuntimeError("Simulated failure before commit")
        except RuntimeError:
            session.rollback()
        finally:
            session.close()

        # Verify bot was not persisted
        with TestingSessionLocal() as verify_session:
            self.assertIsNone(verify_session.get(Chatbot, bot_id))

    def test_foreign_key_constraint_prevents_orphan_flow(self):
        """Verify inserting a flow with a nonexistent chatbot_id raises IntegrityError."""
        fake_bot_id = f"nonexistent-bot-{uuid.uuid4()}"
        now = get_utc_now()

        with TestingSessionLocal() as session:
            flow = Flow(
                id=str(uuid.uuid4()),
                chatbot_id=fake_bot_id,
                name="Orphan Flow",
                flow_data={"nodes": [], "edges": []},
                created_at=now,
                updated_at=now,
            )
            session.add(flow)
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_connection_allows_cross_thread_worker_usage(self):
        """
        Verify that database operations across worker threads (FastAPI AnyIO threadpool model)
        execute cleanly without thread affinity errors.
        """
        def query_in_worker_thread():
            with TestingSessionLocal() as session:
                bot = session.get(Chatbot, DEFAULT_CHATBOT_ID)
                return bot.name if bot else None

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future = executor.submit(query_in_worker_thread)
            result = future.result(timeout=5)
            self.assertEqual(result, "Default Chatbot")


if __name__ == "__main__":
    unittest.main()
