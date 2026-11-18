"""
Test configuration and fixtures for running tests against an isolated test database.
Ensures tests NEVER touch or modify the production database 'chatbot_flow_builder'.
"""

import os
from pathlib import Path
import sys
from urllib.parse import urlparse, urlunparse

# 1. On Windows, ensure PostgreSQL bin directory is in PATH and DLL search path for libpq.dll
pg_bin = r"C:\Program Files\PostgreSQL\18\bin"
if os.path.exists(pg_bin):
    if pg_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = pg_bin + ";" + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(pg_bin)
        except Exception:
            pass

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.database import (
    DEFAULT_CHATBOT_ID,
    PREBUILT_NODE_DEFINITIONS,
    get_db,
    get_utc_now,
)
from app.models import AnswerBlock, Base, Chatbot, Flow, MediaAsset, NodeAnswer, NodeDefinition

# Construct isolated test database URL (chatbot_flow_builder_test)
prod_url = os.getenv("DATABASE_URL")
if not prod_url:
    raise RuntimeError("DATABASE_URL not set in environment or backend/.env.")

parsed = urlparse(prod_url)
TEST_DATABASE_URL = urlunparse(parsed._replace(path="/chatbot_flow_builder_test"))

test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def init_isolated_test_db():
    """Create tables and seed default records in the isolated test database."""
    Base.metadata.create_all(test_engine)
    with TestingSessionLocal() as db:
        # 1. Default chatbot
        if db.get(Chatbot, DEFAULT_CHATBOT_ID) is None:
            now = get_utc_now()
            db.add(
                Chatbot(
                    id=DEFAULT_CHATBOT_ID,
                    name="Default Chatbot",
                    description="Default system chatbot for flows",
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )

        # 2. Prebuilt nodes
        now = get_utc_now()
        for node in PREBUILT_NODE_DEFINITIONS:
            existing = db.query(NodeDefinition).filter_by(node_type=node["node_type"]).first()
            if existing is None:
                db.add(
                    NodeDefinition(
                        id=node["id"],
                        name=node["name"],
                        node_type=node["node_type"],
                        category=node["category"],
                        description=node.get("description", ""),
                        node_source="prebuilt",
                        input_schema=node.get("input_schema", {}),
                        output_schema=node.get("output_schema", {}),
                        config_schema=node.get("config_schema", {}),
                        executor_type=node.get("executor_type"),
                        executor_config=node.get("executor_config", {}),
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                )
        db.commit()


def clean_isolated_test_db():
    """Clean all tables in the isolated test database."""
    try:
        with test_engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE answer_blocks, node_answers, media_assets, flows, chatbots, node_definitions RESTART IDENTITY CASCADE;"))
    except Exception:
        # Fallback if truncate fails (e.g. SQLite test)
        with TestingSessionLocal() as db:
            db.query(AnswerBlock).delete()
            db.query(NodeAnswer).delete()
            db.query(MediaAsset).delete()
            db.query(Flow).delete()
            db.query(Chatbot).delete()
            db.query(NodeDefinition).delete()
            db.commit()


def override_get_test_db():
    """FastAPI dependency override yielding a session for the isolated test database."""
    db = TestingSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

