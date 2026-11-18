"""
Unit tests for Prebuilt and Custom Node Definitions.
Tests table creation, idempotent seeding, listing, filtering, fetching,
custom node creation, duplicate prevention, prebuilt protection, and safe deactivation.
"""

import asyncio
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

# Ensure the backend directory is in the Python search path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import get_db, PREBUILT_NODE_DEFINITIONS
from app.models import Base, Flow, NodeDefinition
from tests.test_config import (
    clean_isolated_test_db,
    init_isolated_test_db,
    override_get_test_db,
    test_engine,
    TestingSessionLocal,
)
from sqlalchemy import inspect
from app.main import app


async def invoke_asgi(
    method: str,
    path: str,
    body: dict = None,
    raw_body: bytes = None,
    custom_headers: dict = None,
) -> tuple:
    """
    Simulate an HTTP request against the ASGI FastAPI application using Python standard library.
    """
    if raw_body is not None:
        payload_bytes = raw_body
    elif body is not None:
        payload_bytes = json.dumps(body).encode("utf-8")
    else:
        payload_bytes = b""

    headers = [
        (b"host", b"testserver"),
        (b"content-type", b"application/json"),
        (b"content-length", str(len(payload_bytes)).encode("latin1")),
    ]

    if custom_headers:
        for k, v in custom_headers.items():
            headers.append((k.lower().encode("latin1"), v.encode("latin1")))

    messages = []
    has_sent_body = False

    async def receive():
        nonlocal has_sent_body
        if not has_sent_body:
            has_sent_body = True
            return {"type": "http.request", "body": payload_bytes, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    parsed_path = path.split("?", 1)
    raw_path = parsed_path[0].encode("latin1")
    query_string = parsed_path[1].encode("latin1") if len(parsed_path) > 1 else b""

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": parsed_path[0],
        "raw_path": raw_path,
        "query_string": query_string,
        "root_path": "",
        "headers": headers,
        "server": ("127.0.0.1", 80),
        "client": ("127.0.0.1", 12345),
    }

    await app(scope, receive, send)

    status_code = None
    resp_headers = {}
    resp_body = b""

    for msg in messages:
        if msg["type"] == "http.response.start":
            status_code = msg["status"]
            for h_key, h_val in msg.get("headers", []):
                resp_headers[h_key.decode("latin1").lower()] = h_val.decode("latin1")
        elif msg["type"] == "http.response.body":
            resp_body += msg.get("body", b"")

    try:
        json_data = json.loads(resp_body.decode("utf-8")) if resp_body else None
    except Exception:
        json_data = resp_body.decode("utf-8", errors="replace")

    return status_code, json_data


class TestNodeDefinitions(unittest.TestCase):
    """Test suite for Node Definitions database foundation and API endpoints."""

    def setUp(self):
        """Set up an isolated test database for each test."""
        clean_isolated_test_db()
        init_isolated_test_db()
        app.dependency_overrides[get_db] = override_get_test_db

    def tearDown(self):
        """Clean up dependency overrides and clean test database after each test."""
        app.dependency_overrides.clear()
        clean_isolated_test_db()

    def run_async(self, coro):
        """Helper to run async ASGI invocation in unittest."""
        return asyncio.run(coro)

    # 1. Database table creation
    def test_database_table_creation(self):
        """Verify node_definitions table is created with all required columns and index."""
        inspector = inspect(test_engine)
        cols = [col["name"] for col in inspector.get_columns("node_definitions")]
        expected_cols = [
            "id", "name", "node_type", "category", "description", "node_source",
            "input_schema", "output_schema", "config_schema", "executor_type",
            "executor_config", "is_active", "created_at", "updated_at",
        ]
        for col in expected_cols:
            self.assertIn(col, cols, f"Missing column '{col}' in node_definitions table.")

        indexes = [idx["name"] for idx in inspector.get_indexes("node_definitions")]
        self.assertIn("idx_node_definitions_filter", indexes)

    # 2. Prebuilt node seeding
    def test_prebuilt_node_seeding(self):
        """Verify all prebuilt node types are seeded into node_definitions table."""
        with TestingSessionLocal() as session:
            rows = session.query(NodeDefinition).filter_by(node_source="prebuilt").all()
            seeded_types = {row.node_type for row in rows}

            expected_types = {
                "start", "message", "answer", "router", "llm", "api_request",
                "condition", "database", "response", "employee_search", "rag", "tts"
            }
            for expected in expected_types:
                self.assertIn(expected, seeded_types, f"Prebuilt type '{expected}' was not seeded.")

    # 3. No duplicate prebuilt definitions after repeated initialization
    def test_idempotent_seeding_no_duplicates(self):
        """Verify running init_db multiple times does not produce duplicate prebuilt node definitions."""
        with TestingSessionLocal() as session:
            initial_count = session.query(NodeDefinition).filter_by(node_source="prebuilt").count()

        # Run initialization again
        init_isolated_test_db()
        init_isolated_test_db()

        with TestingSessionLocal() as session:
            subsequent_count = session.query(NodeDefinition).filter_by(node_source="prebuilt").count()

        self.assertEqual(initial_count, subsequent_count)

    # 4. Listing all node definitions
    def test_list_all_node_definitions(self):
        """Verify GET /node-definitions returns all active node definitions."""
        status_code, data = self.run_async(invoke_asgi("GET", "/node-definitions"))
        self.assertEqual(status_code, 200)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 11)

        first = data[0]
        self.assertIn("id", first)
        self.assertIn("node_type", first)
        self.assertIn("config_schema", first)
        self.assertIsInstance(first["config_schema"], dict)

    # 5. Filtering by node source and category
    def test_filter_by_source_and_category(self):
        """Verify filtering by node_source and category."""
        # Prebuilt filter
        status_code, data = self.run_async(invoke_asgi("GET", "/node-definitions?node_source=prebuilt"))
        self.assertEqual(status_code, 200)
        for node in data:
            self.assertEqual(node["node_source"], "prebuilt")

        # Category filter (e.g. AI)
        status_code, ai_nodes = self.run_async(invoke_asgi("GET", "/node-definitions?category=AI"))
        self.assertEqual(status_code, 200)
        self.assertGreater(len(ai_nodes), 0)
        for node in ai_nodes:
            self.assertEqual(node["category"].upper(), "AI")

        # Active filter
        status_code, active_nodes = self.run_async(invoke_asgi("GET", "/node-definitions?is_active=true"))
        self.assertEqual(status_code, 200)
        for node in active_nodes:
            self.assertTrue(node["is_active"])

    # 6. Fetching an existing node
    def test_get_existing_node_definition(self):
        """Verify GET /node-definitions/{id} returns full definition."""
        status_code, data = self.run_async(invoke_asgi("GET", "/node-definitions/prebuilt-start"))
        self.assertEqual(status_code, 200)
        self.assertEqual(data["id"], "prebuilt-start")
        self.assertEqual(data["node_type"], "start")
        self.assertEqual(data["node_source"], "prebuilt")

    # 7. Handling a nonexistent node
    def test_get_nonexistent_node_definition(self):
        """Verify GET /node-definitions/{id} returns 404 for unknown ID."""
        status_code, data = self.run_async(invoke_asgi("GET", "/node-definitions/nonexistent-id-12345"))
        self.assertEqual(status_code, 404)
        self.assertIn("detail", data)

    # 8. Creating a custom node
    def test_create_custom_node(self):
        """Verify POST /node-definitions creates a custom node with node_source='custom'."""
        payload = {
            "name": "Sentiment Analyzer",
            "node_type": "sentiment_analyzer",
            "category": "AI",
            "description": "Analyzes sentiment of incoming user messages",
            "input_schema": {"properties": {"message": {"type": "string"}}},
            "output_schema": {"properties": {"sentiment": {"type": "string"}, "score": {"type": "number"}}},
            "config_schema": {
                "fields": [
                    {"name": "threshold", "label": "Confidence Threshold", "type": "number", "required": True, "default": 0.8}
                ]
            },
        }
        status_code, created = self.run_async(invoke_asgi("POST", "/node-definitions", body=payload))
        self.assertEqual(status_code, 201)
        self.assertEqual(created["name"], "Sentiment Analyzer")
        self.assertEqual(created["node_type"], "sentiment_analyzer")
        self.assertEqual(created["node_source"], "custom")
        self.assertTrue(created["is_active"])
        self.assertEqual(created["config_schema"]["fields"][0]["name"], "threshold")

        # Verify it appears in list filter for custom
        status_code, custom_list = self.run_async(invoke_asgi("GET", "/node-definitions?node_source=custom"))
        self.assertEqual(status_code, 200)
        custom_types = [n["node_type"] for n in custom_list]
        self.assertIn("sentiment_analyzer", custom_types)

    # 9. Rejecting invalid input
    def test_create_custom_node_invalid_input(self):
        """Verify validation errors for empty name or invalid node_type slug."""
        # Empty name
        code1, _ = self.run_async(invoke_asgi("POST", "/node-definitions", body={"name": "   ", "node_type": "valid_slug", "category": "AI"}))
        self.assertEqual(code1, 422)

        # Invalid slug with spaces or special chars
        code2, _ = self.run_async(invoke_asgi("POST", "/node-definitions", body={"name": "My Node", "node_type": "invalid slug @!", "category": "AI"}))
        self.assertEqual(code2, 422)

    # 10. Handling duplicate node types safely
    def test_duplicate_node_type_conflict(self):
        """Verify POST /node-definitions returns 409 Conflict if node_type already exists."""
        payload = {
            "name": "Custom Router Duplicate",
            "node_type": "router",
            "category": "Routing",
        }
        code1, data1 = self.run_async(invoke_asgi("POST", "/node-definitions", body=payload))
        self.assertEqual(code1, 409)
        self.assertIn("already exists", data1["detail"].lower())

        # Create unique custom node first
        payload2 = {"name": "Webhook Notifier", "node_type": "webhook_notifier", "category": "Integration"}
        code2, _ = self.run_async(invoke_asgi("POST", "/node-definitions", body=payload2))
        self.assertEqual(code2, 201)

        # Duplicate attempt of custom node
        code3, data3 = self.run_async(invoke_asgi("POST", "/node-definitions", body=payload2))
        self.assertEqual(code3, 409)
        self.assertIn("already exists", data3["detail"].lower())

    # 11. Updating a custom node
    def test_update_custom_node(self):
        """Verify PUT /node-definitions/{id} updates fields of a custom node."""
        create_payload = {"name": "Original Name", "node_type": "custom_step_1", "category": "Logic"}
        _, created = self.run_async(invoke_asgi("POST", "/node-definitions", body=create_payload))
        node_id = created["id"]

        update_payload = {
            "name": "Updated Custom Name",
            "description": "New updated description",
            "category": "Advanced Logic",
        }
        status_code, updated = self.run_async(invoke_asgi("PUT", f"/node-definitions/{node_id}", body=update_payload))
        self.assertEqual(status_code, 200)
        self.assertEqual(updated["name"], "Updated Custom Name")
        self.assertEqual(updated["description"], "New updated description")
        self.assertEqual(updated["category"], "Advanced Logic")

    # 12. Preventing modification of prebuilt nodes
    def test_prevent_prebuilt_modification(self):
        """Verify PUT /node-definitions/{id} rejects attempts to modify prebuilt definitions with 403."""
        update_payload = {"name": "Hacked Router"}
        status_code, data = self.run_async(invoke_asgi("PUT", "/node-definitions/prebuilt-router", body=update_payload))
        self.assertEqual(status_code, 403)
        self.assertIn("cannot be modified", data["detail"].lower())

    # 13. Safe deletion or deactivation behavior
    def test_safe_deletion_and_deactivation(self):
        """
        Verify:
        1. Prebuilts cannot be deleted (403).
        2. Unreferenced custom nodes are deleted permanently.
        3. Custom nodes referenced by a saved flow are deactivated instead of deleted.
        """
        # 1. Prebuilt delete attempt
        code_prebuilt, _ = self.run_async(invoke_asgi("DELETE", "/node-definitions/prebuilt-start"))
        self.assertEqual(code_prebuilt, 403)

        # 2. Unreferenced custom node -> hard delete
        _, custom_node = self.run_async(invoke_asgi("POST", "/node-definitions", body={"name": "Temporary", "node_type": "temp_delete", "category": "Tools"}))
        code_del, del_data = self.run_async(invoke_asgi("DELETE", f"/node-definitions/{custom_node['id']}"))
        self.assertEqual(code_del, 200)
        self.assertFalse(del_data["deactivated"])

        # Subsequent GET should return 404
        code_get, _ = self.run_async(invoke_asgi("GET", f"/node-definitions/{custom_node['id']}"))
        self.assertEqual(code_get, 404)

        # 3. Referenced custom node -> safe deactivation
        _, used_node = self.run_async(invoke_asgi("POST", "/node-definitions", body={"name": "Referenced Node", "node_type": "used_in_flow", "category": "Data"}))

        # Create a flow referencing 'used_in_flow'
        flow_payload = {
            "name": "Flow With Custom Node",
            "flow_data": {
                "nodes": [{"id": "n1", "type": "used_in_flow", "data": {"label": "Used Node"}}],
                "edges": [],
            },
        }
        self.run_async(invoke_asgi("POST", "/flows", body=flow_payload))

        # Attempt to delete referenced node
        code_deact, deact_data = self.run_async(invoke_asgi("DELETE", f"/node-definitions/{used_node['id']}"))
        self.assertEqual(code_deact, 200)
        self.assertTrue(deact_data["deactivated"])
        self.assertIn("deactivated instead of deleted", deact_data["message"].lower())

        # Verify it still exists in database with is_active = False
        _, fetched = self.run_async(invoke_asgi("GET", f"/node-definitions/{used_node['id']}"))
        self.assertFalse(fetched["is_active"])

    # 14 & 15. Flow compatibility with custom node instances
    def test_flow_save_and_reload_with_custom_node(self):
        """Verify flows can save, reload, and preserve custom node definitions and instances."""
        _, custom_node = self.run_async(invoke_asgi(
            "POST",
            "/node-definitions",
            body={
                "name": "CRM Sync",
                "node_type": "crm_sync",
                "category": "Integration",
                "config_schema": {
                    "fields": [{"name": "crm_id", "label": "CRM Identifier", "type": "string", "default": "CRM-123"}]
                },
            },
        ))

        flow_payload = {
            "name": "Enterprise CRM Flow",
            "flow_data": {
                "nodes": [
                    {
                        "id": "start-1",
                        "type": "start",
                        "position": {"x": 100, "y": 100},
                        "data": {"label": "Start Step"},
                    },
                    {
                        "id": "crm-1",
                        "type": "crm_sync",
                        "position": {"x": 300, "y": 100},
                        "data": {"label": "CRM Sync", "crm_id": "ORG-9988"},
                    },
                ],
                "edges": [{"id": "e1-2", "source": "start-1", "target": "crm-1"}],
            },
        }
        code_flow, created_flow = self.run_async(invoke_asgi("POST", "/flows", body=flow_payload))
        self.assertEqual(code_flow, 201)
        flow_id = created_flow["id"]

        # Reload flow
        code_get, loaded = self.run_async(invoke_asgi("GET", f"/flows/{flow_id}"))
        self.assertEqual(code_get, 200)
        self.assertEqual(len(loaded["flow_data"]["nodes"]), 2)
        crm_node = next(n for n in loaded["flow_data"]["nodes"] if n["id"] == "crm-1")
        self.assertEqual(crm_node["type"], "crm_sync")
        self.assertEqual(crm_node["data"]["crm_id"], "ORG-9988")

    def test_custom_node_buttons_configuration_and_flow_persistence(self):
        """
        Verify:
        1. Custom node definition with buttons is stored in node_definitions.
        2. Flow containing custom node instances with multiple buttons and sourceHandle edges persists.
        3. Reloading flow preserves all button IDs, labels, and handle connections.
        """
        # 1. Create custom node definition with 3 buttons (e.g. NABH Welcome menu)
        node_def_payload = {
            "name": "NABH Menu Selector",
            "node_type": "nabh_menu_selector",
            "category": "Communication",
            "description": "Presents branching options for NABH visitors",
            "config_schema": {
                "buttons": [
                    {"id": "btn_about", "label": "About NABH"},
                    {"id": "btn_accredit", "label": "Accreditation"},
                    {"id": "btn_question", "label": "Ask a Question"},
                ],
                "fields": [],
            },
        }
        status_code, created_def = self.run_async(invoke_asgi("POST", "/node-definitions", body=node_def_payload))
        self.assertEqual(status_code, 201)
        self.assertEqual(len(created_def["config_schema"]["buttons"]), 3)
        self.assertEqual(created_def["config_schema"]["buttons"][0]["id"], "btn_about")

        # 2. Create flow with this custom node and 3 target destination nodes
        flow_payload = {
            "name": "NABH Branching Flow",
            "flow_data": {
                "nodes": [
                    {
                        "id": "menu-node-1",
                        "type": "nabh_menu_selector",
                        "position": {"x": 200, "y": 150},
                        "data": {
                            "label": "NABH Welcome Menu",
                            "buttons": [
                                {"id": "btn_about", "label": "About NABH", "target": "msg-about"},
                                {"id": "btn_accredit", "label": "Accreditation", "target": "msg-accredit"},
                                {"id": "btn_question", "label": "Ask a Question", "target": "rag-question"},
                            ],
                        },
                    },
                    {
                        "id": "msg-about",
                        "type": "message",
                        "position": {"x": 500, "y": 50},
                        "data": {"label": "About NABH Message", "text": "NABH is a constituent board..."},
                    },
                    {
                        "id": "msg-accredit",
                        "type": "message",
                        "position": {"x": 500, "y": 180},
                        "data": {"label": "Accreditation Info", "text": "Hospital accreditation standards..."},
                    },
                    {
                        "id": "rag-question",
                        "type": "rag",
                        "position": {"x": 500, "y": 310},
                        "data": {"label": "Ask Question RAG", "top_k": 3},
                    },
                ],
                "edges": [
                    {
                        "id": "edge-menu-btn_about-msg-about",
                        "source": "menu-node-1",
                        "sourceHandle": "btn_about",
                        "target": "msg-about",
                    },
                    {
                        "id": "edge-menu-btn_accredit-msg-accredit",
                        "source": "menu-node-1",
                        "sourceHandle": "btn_accredit",
                        "target": "msg-accredit",
                    },
                    {
                        "id": "edge-menu-btn_question-rag-question",
                        "source": "menu-node-1",
                        "sourceHandle": "btn_question",
                        "target": "rag-question",
                    },
                ],
            },
        }

        code_flow, created_flow = self.run_async(invoke_asgi("POST", "/flows", body=flow_payload))
        self.assertEqual(code_flow, 201)
        flow_id = created_flow["id"]

        # 3. Reload flow and verify all 3 button branches and sourceHandle edges are preserved
        code_get, loaded_flow = self.run_async(invoke_asgi("GET", f"/flows/{flow_id}"))
        self.assertEqual(code_get, 200)

        nodes = loaded_flow["flow_data"]["nodes"]
        edges = loaded_flow["flow_data"]["edges"]
        self.assertEqual(len(nodes), 4)
        self.assertEqual(len(edges), 3)

        menu_node = next(n for n in nodes if n["id"] == "menu-node-1")
        self.assertEqual(len(menu_node["data"]["buttons"]), 3)
        self.assertEqual(menu_node["data"]["buttons"][0]["label"], "About NABH")
        self.assertEqual(menu_node["data"]["buttons"][0]["target"], "msg-about")
        self.assertEqual(menu_node["data"]["buttons"][1]["target"], "msg-accredit")
        self.assertEqual(menu_node["data"]["buttons"][2]["target"], "rag-question")

        # Verify edge handles
        edge_about = next(e for e in edges if e["sourceHandle"] == "btn_about")
        self.assertEqual(edge_about["source"], "menu-node-1")
        self.assertEqual(edge_about["target"], "msg-about")

        edge_accredit = next(e for e in edges if e["sourceHandle"] == "btn_accredit")
        self.assertEqual(edge_accredit["target"], "msg-accredit")

        edge_question = next(e for e in edges if e["sourceHandle"] == "btn_question")
        self.assertEqual(edge_question["target"], "rag-question")


if __name__ == "__main__":
    unittest.main()
