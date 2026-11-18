"""
Automated unit and integration tests for the Chatbot Flow APIs (POST /flows and GET /flows).
Tests flow creation, validation errors, listing multiple flows, returning empty lists,
and database persistence using an isolated temporary SQLite database to protect the production database.
"""

import asyncio
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import uuid

# Ensure backend directory is importable
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import DEFAULT_CHATBOT_ID, get_db
from app.models import Chatbot, Flow
from tests.test_config import (
    clean_isolated_test_db,
    init_isolated_test_db,
    override_get_test_db,
    TestingSessionLocal,
)
from app.main import app


async def invoke_asgi(
    method: str,
    path: str,
    body: dict = None,
    raw_body: bytes = None,
    custom_headers: dict = None,
    return_headers: bool = False,
) -> tuple:
    """
    Simulate an HTTP request against the ASGI FastAPI application using Python standard library.
    Allows end-to-end testing of routes, middleware, and Pydantic validation without external libraries.
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

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode("latin1"),
        "query_string": b"",
        "headers": headers,
        "app": app,
    }

    await app(scope, receive, send)

    start_msg = next(m for m in messages if m["type"] == "http.response.start")
    status_code = start_msg["status"]
    response_headers = {
        k.decode("latin1").lower(): v.decode("latin1")
        for k, v in start_msg.get("headers", [])
    }
    response_body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    parsed_json = json.loads(response_body.decode("utf-8")) if response_body else None

    if return_headers:
        return status_code, parsed_json, response_headers
    return status_code, parsed_json



class TestFlowsApi(unittest.TestCase):
    """Test suite for /flows endpoints (POST and GET)."""

    def setUp(self):
        """Create a fresh isolated test database for each test."""
        clean_isolated_test_db()
        init_isolated_test_db()
        app.dependency_overrides[get_db] = override_get_test_db

    def tearDown(self):
        """Clean up dependency overrides and clean test database."""
        app.dependency_overrides.clear()
        clean_isolated_test_db()

    # --- POST /flows Tests ---

    def test_create_flow_success(self):
        """Verify successful flow creation returns HTTP 201 and expected payload."""
        payload = {
            "name": "Customer Support Onboarding",
            "description": "Guides a new customer through product setup",
            "flow_data": {
                "nodes": [
                    {"id": "node-1", "type": "start", "data": {"label": "Welcome"}, "position": {"x": 50, "y": 50}},
                    {"id": "node-2", "type": "message", "data": {"text": "How can I help?"}, "position": {"x": 50, "y": 150}},
                ],
                "edges": [
                    {"id": "edge-1", "source": "node-1", "target": "node-2"},
                ],
            },
        }

        status_code, body = asyncio.run(invoke_asgi("POST", "/flows", body=payload))

        self.assertEqual(status_code, 201)
        self.assertIn("id", body)
        # Verify generated ID is a valid UUID
        parsed_uuid = uuid.UUID(body["id"])
        self.assertEqual(str(parsed_uuid), body["id"])

        self.assertEqual(body["name"], payload["name"])
        self.assertEqual(body["description"], payload["description"])
        self.assertEqual(body["flow_data"]["nodes"], payload["flow_data"]["nodes"])
        self.assertEqual(body["flow_data"]["edges"], payload["flow_data"]["edges"])

        # Verify timestamps are ISO 8601
        self.assertIn("created_at", body)
        self.assertIn("updated_at", body)
        datetime.fromisoformat(body["created_at"])
        datetime.fromisoformat(body["updated_at"])

    def test_create_flow_persistence(self):
        """Verify the created flow is genuinely persisted in SQLite table."""
        payload = {
            "name": "Persisted Flow",
            "description": "Checking database persistence directly",
            "flow_data": {"nodes": [{"id": "n1"}], "edges": []},
        }

        status_code, body = asyncio.run(invoke_asgi("POST", "/flows", body=payload))
        self.assertEqual(status_code, 201)
        flow_id = body["id"]

        # Directly query the test database to verify persistence
        with TestingSessionLocal() as session:
            flow_obj = session.get(Flow, flow_id)

        self.assertIsNotNone(flow_obj, "Flow record was not persisted in database")
        self.assertEqual(flow_obj.id, flow_id)
        self.assertEqual(flow_obj.name, "Persisted Flow")
        self.assertEqual(flow_obj.description, "Checking database persistence directly")
        self.assertEqual(flow_obj.flow_data, payload["flow_data"])

    def test_create_flow_without_optional_description(self):
        """Verify creation succeeds when optional description is omitted or None."""
        payload = {
            "name": "Minimal Flow",
            "flow_data": {"nodes": [], "edges": []},
        }

        status_code, body = asyncio.run(invoke_asgi("POST", "/flows", body=payload))
        self.assertEqual(status_code, 201)
        self.assertIsNone(body.get("description"))

    def test_validation_error_missing_name(self):
        """Verify HTTP 422 when required 'name' field is missing."""
        payload = {
            "description": "Missing name",
            "flow_data": {"nodes": [], "edges": []},
        }
        status_code, body = asyncio.run(invoke_asgi("POST", "/flows", body=payload))
        self.assertEqual(status_code, 422)

    def test_validation_error_empty_name(self):
        """Verify HTTP 422 when 'name' is empty or whitespace-only."""
        for invalid_name in ["", "   ", "\t\n"]:
            payload = {
                "name": invalid_name,
                "flow_data": {"nodes": [], "edges": []},
            }
            status_code, body = asyncio.run(invoke_asgi("POST", "/flows", body=payload))
            self.assertEqual(status_code, 422, f"Failed to reject invalid name: {repr(invalid_name)}")

    def test_validation_error_missing_flow_data(self):
        """Verify HTTP 422 when 'flow_data' is missing."""
        payload = {
            "name": "Valid Name",
        }
        status_code, body = asyncio.run(invoke_asgi("POST", "/flows", body=payload))
        self.assertEqual(status_code, 422)

    def test_validation_error_flow_data_missing_nodes(self):
        """Verify HTTP 422 when 'flow_data' does not contain 'nodes' array."""
        payload = {
            "name": "Valid Name",
            "flow_data": {"edges": []},
        }
        status_code, body = asyncio.run(invoke_asgi("POST", "/flows", body=payload))
        self.assertEqual(status_code, 422)

    def test_validation_error_flow_data_nodes_not_list(self):
        """Verify HTTP 422 when 'nodes' is not a list."""
        payload = {
            "name": "Valid Name",
            "flow_data": {"nodes": "invalid-string", "edges": []},
        }
        status_code, body = asyncio.run(invoke_asgi("POST", "/flows", body=payload))
        self.assertEqual(status_code, 422)

    def test_validation_error_flow_data_edges_not_list(self):
        """Verify HTTP 422 when 'edges' is not a list."""
        payload = {
            "name": "Valid Name",
            "flow_data": {"nodes": [], "edges": 12345},
        }
        status_code, body = asyncio.run(invoke_asgi("POST", "/flows", body=payload))
        self.assertEqual(status_code, 422)

    def test_validation_error_malformed_json_body(self):
        """Verify HTTP 422 when request body is not valid JSON."""
        status_code, body = asyncio.run(invoke_asgi("POST", "/flows", raw_body=b"{malformed json..."))
        self.assertEqual(status_code, 422)

    # --- GET /flows Tests ---

    def test_list_flows_empty(self):
        """Verify GET /flows returns an empty JSON array ([]) when no flows exist."""
        status_code, body = asyncio.run(invoke_asgi("GET", "/flows"))

        self.assertEqual(status_code, 200)
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 0)

    def test_list_flows_multiple(self):
        """Verify GET /flows retrieves all flows with parsed flow_data and expected fields."""
        flow_1_payload = {
            "name": "Flow Alpha",
            "description": "First test flow",
            "flow_data": {
                "nodes": [{"id": "n1", "type": "start", "data": {"label": "Start"}, "position": {"x": 0, "y": 0}}],
                "edges": [],
            },
        }
        flow_2_payload = {
            "name": "Flow Beta",
            "description": "Second test flow",
            "flow_data": {
                "nodes": [
                    {"id": "n2", "type": "input", "data": {"label": "User Input"}, "position": {"x": 10, "y": 20}},
                    {"id": "n3", "type": "output", "data": {"label": "Response"}, "position": {"x": 10, "y": 80}},
                ],
                "edges": [{"id": "e1", "source": "n2", "target": "n3"}],
            },
        }

        # Create two flows
        status_1, created_1 = asyncio.run(invoke_asgi("POST", "/flows", body=flow_1_payload))
        self.assertEqual(status_1, 201)

        status_2, created_2 = asyncio.run(invoke_asgi("POST", "/flows", body=flow_2_payload))
        self.assertEqual(status_2, 201)

        # Retrieve flows
        status_code, body = asyncio.run(invoke_asgi("GET", "/flows"))

        self.assertEqual(status_code, 200)
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 2)

        # Map by ID to verify attributes
        flows_by_id = {flow["id"]: flow for flow in body}
        self.assertIn(created_1["id"], flows_by_id)
        self.assertIn(created_2["id"], flows_by_id)

        # Verify flow 1 contents
        retrieved_1 = flows_by_id[created_1["id"]]
        self.assertEqual(retrieved_1["name"], "Flow Alpha")
        self.assertEqual(retrieved_1["description"], "First test flow")
        self.assertIsInstance(retrieved_1["flow_data"], dict)
        self.assertIsInstance(retrieved_1["flow_data"]["nodes"], list)
        self.assertEqual(len(retrieved_1["flow_data"]["nodes"]), 1)
        self.assertEqual(retrieved_1["flow_data"]["nodes"][0]["id"], "n1")
        self.assertEqual(retrieved_1["flow_data"]["edges"], [])
        self.assertIn("created_at", retrieved_1)
        self.assertIn("updated_at", retrieved_1)

        # Verify flow 2 contents
        retrieved_2 = flows_by_id[created_2["id"]]
        self.assertEqual(retrieved_2["name"], "Flow Beta")
        self.assertEqual(retrieved_2["description"], "Second test flow")
        self.assertIsInstance(retrieved_2["flow_data"], dict)
        self.assertEqual(len(retrieved_2["flow_data"]["nodes"]), 2)
        self.assertEqual(len(retrieved_2["flow_data"]["edges"]), 1)
        self.assertEqual(retrieved_2["flow_data"]["edges"][0]["source"], "n2")

    def test_list_flows_preserves_production_database(self):
        """Verify tests run against the isolated test database without touching production database."""
        from tests.test_config import TEST_DATABASE_URL
        from app.database import DATABASE_URL
        self.assertNotEqual(TEST_DATABASE_URL, DATABASE_URL)

    # --- GET /flows/{flow_id} Tests ---

    def test_get_flow_by_id_success(self):
        """Verify GET /flows/{flow_id} returns HTTP 200 and the requested flow."""
        payload = {
            "name": "Single Flow Test",
            "description": "Testing retrieval by unique ID",
            "flow_data": {
                "nodes": [{"id": "n1", "type": "prompt", "data": {"text": "Hello"}}],
                "edges": [],
            },
        }

        # Create flow first
        create_status, created = asyncio.run(invoke_asgi("POST", "/flows", body=payload))
        self.assertEqual(create_status, 201)
        flow_id = created["id"]

        # Fetch flow by ID
        get_status, fetched = asyncio.run(invoke_asgi("GET", f"/flows/{flow_id}"))
        self.assertEqual(get_status, 200)

        self.assertEqual(fetched["id"], flow_id)
        self.assertEqual(fetched["name"], payload["name"])
        self.assertEqual(fetched["description"], payload["description"])
        self.assertIsInstance(fetched["flow_data"], dict)
        self.assertEqual(fetched["flow_data"]["nodes"], payload["flow_data"]["nodes"])
        self.assertEqual(fetched["flow_data"]["edges"], payload["flow_data"]["edges"])
        self.assertEqual(fetched["created_at"], created["created_at"])
        self.assertEqual(fetched["updated_at"], created["updated_at"])

    def test_get_flow_by_id_not_found(self):
        """Verify GET /flows/{flow_id} returns HTTP 404 when flow does not exist."""
        non_existent_id = "non-existent-flow-id-99999"
        status_code, body = asyncio.run(invoke_asgi("GET", f"/flows/{non_existent_id}"))

        self.assertEqual(status_code, 404)
        self.assertIn("detail", body)
        self.assertIn(non_existent_id, body["detail"])

    def test_get_flow_by_id_whitespace_returns_404(self):
        """Verify GET /flows/{flow_id} returns HTTP 404 when ID is whitespace."""
        status_code, body = asyncio.run(invoke_asgi("GET", "/flows/%20%20"))
        self.assertEqual(status_code, 404)
        self.assertIn("detail", body)

    def test_get_flow_by_id_nonexistent_uuid(self):
        """Verify GET /flows/{flow_id} returns HTTP 404 when querying an unrecorded UUID."""
        random_uuid = str(uuid.uuid4())
        status_code, body = asyncio.run(invoke_asgi("GET", f"/flows/{random_uuid}"))
        self.assertEqual(status_code, 404)
        self.assertIn("detail", body)
        self.assertIn(random_uuid, body["detail"])

    # --- PUT /flows/{flow_id} Tests ---

    def test_update_flow_success_and_preserves_created_at(self):
        """Verify PUT /flows/{flow_id} updates record, preserves created_at, and sets new updated_at."""
        initial_payload = {
            "name": "Initial Name",
            "description": "Initial Description",
            "flow_data": {"nodes": [{"id": "n1"}], "edges": []},
        }

        # Create flow
        create_status, created = asyncio.run(invoke_asgi("POST", "/flows", body=initial_payload))
        self.assertEqual(create_status, 201)
        flow_id = created["id"]
        original_created_at = created["created_at"]

        # Update payload
        update_payload = {
            "name": "Updated Flow Name",
            "description": "Updated Description text",
            "flow_data": {
                "nodes": [
                    {"id": "n1", "type": "start"},
                    {"id": "n2", "type": "end"},
                ],
                "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
            },
        }

        # Execute PUT
        put_status, updated = asyncio.run(invoke_asgi("PUT", f"/flows/{flow_id}", body=update_payload))
        self.assertEqual(put_status, 200)

        # Verify returned data
        self.assertEqual(updated["id"], flow_id)
        self.assertEqual(updated["name"], update_payload["name"])
        self.assertEqual(updated["description"], update_payload["description"])
        self.assertEqual(updated["flow_data"], update_payload["flow_data"])
        # Created at must be preserved exactly
        self.assertEqual(updated["created_at"], original_created_at)
        # Updated at must be a valid ISO timestamp
        datetime.fromisoformat(updated["updated_at"])
        self.assertGreaterEqual(updated["updated_at"], created["updated_at"])

    def test_update_flow_persistence(self):
        """Verify PUT /flows/{flow_id} updates the database in place without creating extra rows."""
        create_payload = {
            "name": "Before Update",
            "flow_data": {"nodes": [], "edges": []},
        }
        _, created = asyncio.run(invoke_asgi("POST", "/flows", body=create_payload))
        flow_id = created["id"]

        update_payload = {
            "name": "After Update",
            "description": "Added description in update",
            "flow_data": {"nodes": [{"id": "n10"}], "edges": []},
        }
        put_status, _ = asyncio.run(invoke_asgi("PUT", f"/flows/{flow_id}", body=update_payload))
        self.assertEqual(put_status, 200)

        # Check database directly
        with TestingSessionLocal() as session:
            total = session.query(Flow).count()
            self.assertEqual(total, 1)

            flow_obj = session.get(Flow, flow_id)
            self.assertIsNotNone(flow_obj)
            self.assertEqual(flow_obj.name, "After Update")
            self.assertEqual(flow_obj.description, "Added description in update")
            self.assertEqual(flow_obj.flow_data, update_payload["flow_data"])

    def test_update_flow_nodes_persistence_and_refetch(self):
        """Regression test: updating a flow with additional nodes persists immediately and re-fetches with accurate count."""
        # 1. Create a flow with 6 nodes (similar to SEBI flow)
        initial_nodes = [{"id": f"node-{i}", "type": "message", "position": {"x": 100, "y": i * 60}} for i in range(6)]
        create_payload = {
            "name": "SEBI Knowledge Flow",
            "flow_data": {
                "nodes": initial_nodes,
                "edges": [{"id": "e1", "source": "node-0", "target": "node-1"}],
            },
        }
        create_status, created = asyncio.run(invoke_asgi("POST", "/flows", body=create_payload))
        self.assertEqual(create_status, 201)
        flow_id = created["id"]
        self.assertEqual(len(created["flow_data"]["nodes"]), 6)

        # 2. Add 7th node and submit PUT
        updated_nodes = list(initial_nodes) + [{"id": "node-6-tts", "type": "tts", "position": {"x": 200, "y": 400}}]
        update_payload = {
            "name": "SEBI Knowledge Flow (Updated)",
            "flow_data": {
                "nodes": updated_nodes,
                "edges": created["flow_data"]["edges"],
            },
        }
        put_status, put_resp = asyncio.run(invoke_asgi("PUT", f"/flows/{flow_id}", body=update_payload))
        self.assertEqual(put_status, 200)
        self.assertEqual(len(put_resp["flow_data"]["nodes"]), 7)

        # 3. Verify subsequent GET returns all 7 nodes
        get_status, get_resp = asyncio.run(invoke_asgi("GET", f"/flows/{flow_id}"))
        self.assertEqual(get_status, 200)
        self.assertEqual(len(get_resp["flow_data"]["nodes"]), 7)
        self.assertEqual(get_resp["flow_data"]["nodes"][-1]["id"], "node-6-tts")

        # 4. Verify database directly
        with TestingSessionLocal() as session:
            flow_obj = session.get(Flow, flow_id)
            persisted = flow_obj.flow_data
            self.assertEqual(len(persisted["nodes"]), 7)
            self.assertEqual(persisted["nodes"][-1]["id"], "node-6-tts")


    def test_update_flow_not_found(self):
        """Verify PUT /flows/{flow_id} returns HTTP 404 when flow does not exist."""
        non_existent_id = "non-existent-uuid-777"
        payload = {
            "name": "Nonexistent",
            "flow_data": {"nodes": [], "edges": []},
        }
        status_code, body = asyncio.run(invoke_asgi("PUT", f"/flows/{non_existent_id}", body=payload))

        self.assertEqual(status_code, 404)
        self.assertIn("detail", body)
        self.assertIn(non_existent_id, body["detail"])

    def test_update_flow_whitespace_id_returns_404(self):
        """Verify PUT /flows/{flow_id} returns HTTP 404 when flow_id is whitespace."""
        payload = {
            "name": "Whitespace ID test",
            "flow_data": {"nodes": [], "edges": []},
        }
        status_code, body = asyncio.run(invoke_asgi("PUT", "/flows/%20%20", body=payload))
        self.assertEqual(status_code, 404)
        self.assertIn("detail", body)

    def test_update_flow_invalid_request_data(self):
        """Verify PUT /flows/{flow_id} returns HTTP 422 for invalid payloads and leaves record intact."""
        create_payload = {
            "name": "Original Name",
            "description": "Original Desc",
            "flow_data": {"nodes": [], "edges": []},
        }
        _, created = asyncio.run(invoke_asgi("POST", "/flows", body=create_payload))
        flow_id = created["id"]

        invalid_payloads = [
            # Empty name
            {"name": "", "flow_data": {"nodes": [], "edges": []}},
            # Whitespace name
            {"name": "   ", "flow_data": {"nodes": [], "edges": []}},
            # Missing flow_data
            {"name": "Valid Name"},
            # flow_data nodes is not a list
            {"name": "Valid Name", "flow_data": {"nodes": "invalid", "edges": []}},
            # flow_data missing edges
            {"name": "Valid Name", "flow_data": {"nodes": []}},
        ]

        for invalid_payload in invalid_payloads:
            status_code, body = asyncio.run(invoke_asgi("PUT", f"/flows/{flow_id}", body=invalid_payload))
            self.assertEqual(status_code, 422, f"Expected 422 for payload: {invalid_payload}")

        # Verify the database record was not altered by failed validation
        with TestingSessionLocal() as session:
            flow_obj = session.get(Flow, flow_id)
            self.assertEqual(flow_obj.name, "Original Name")
            self.assertEqual(flow_obj.description, "Original Desc")

    # --- DELETE /flows/{flow_id} Tests ---

    def test_delete_flow_success_and_verifies_row_removed(self):
        """Verify DELETE /flows/{flow_id} returns HTTP 200 with success JSON and deletes the record from database."""
        create_payload = {
            "name": "Flow to Delete",
            "description": "Will be deleted",
            "flow_data": {"nodes": [{"id": "n1"}], "edges": []},
        }
        create_status, created = asyncio.run(invoke_asgi("POST", "/flows", body=create_payload))
        self.assertEqual(create_status, 201)
        flow_id = created["id"]

        # Call DELETE
        delete_status, body = asyncio.run(invoke_asgi("DELETE", f"/flows/{flow_id}"))
        self.assertEqual(delete_status, 200)
        self.assertIsInstance(body, dict)
        self.assertEqual(body["message"], "Flow deleted successfully.")
        self.assertEqual(body["id"], flow_id)

        # Directly verify the row is removed from database
        with TestingSessionLocal() as session:
            flow_obj = session.get(Flow, flow_id)
            self.assertIsNone(flow_obj, "Flow was not removed from database")

        # Verify subsequent GET returns 404
        get_status, get_body = asyncio.run(invoke_asgi("GET", f"/flows/{flow_id}"))
        self.assertEqual(get_status, 404)

    def test_delete_flow_preserves_other_flows(self):
        """Verify deleting one flow does not affect any other flows in the database."""
        flow_a_payload = {
            "name": "Flow A - To Delete",
            "flow_data": {"nodes": [], "edges": []},
        }
        flow_b_payload = {
            "name": "Flow B - Preserved",
            "description": "Should stay intact",
            "flow_data": {"nodes": [{"id": "b1"}], "edges": []},
        }

        _, created_a = asyncio.run(invoke_asgi("POST", "/flows", body=flow_a_payload))
        _, created_b = asyncio.run(invoke_asgi("POST", "/flows", body=flow_b_payload))
        id_a = created_a["id"]
        id_b = created_b["id"]

        # Delete Flow A
        delete_status, body_a = asyncio.run(invoke_asgi("DELETE", f"/flows/{id_a}"))
        self.assertEqual(delete_status, 200)
        self.assertEqual(body_a["message"], "Flow deleted successfully.")
        self.assertEqual(body_a["id"], id_a)

        # Confirm Flow B remains intact via GET /flows/{id_b}
        get_b_status, fetched_b = asyncio.run(invoke_asgi("GET", f"/flows/{id_b}"))
        self.assertEqual(get_b_status, 200)
        self.assertEqual(fetched_b["name"], "Flow B - Preserved")

        # Confirm GET /flows returns exactly 1 item (Flow B)
        list_status, all_flows = asyncio.run(invoke_asgi("GET", "/flows"))
        self.assertEqual(list_status, 200)
        self.assertEqual(len(all_flows), 1)
        self.assertEqual(all_flows[0]["id"], id_b)

    def test_delete_flow_not_found(self):
        """Verify DELETE /flows/{flow_id} returns HTTP 404 with friendly message when flow does not exist."""
        non_existent_id = "non-existent-uuid-delete"
        status_code, body = asyncio.run(invoke_asgi("DELETE", f"/flows/{non_existent_id}"))

        self.assertEqual(status_code, 404)
        self.assertIn("detail", body)
        self.assertEqual(body["detail"], "Flow not found. It may have already been deleted.")

    def test_delete_flow_whitespace_id_returns_404(self):
        """Verify DELETE /flows/{flow_id} returns HTTP 404 with friendly message when ID is whitespace."""
        status_code, body = asyncio.run(invoke_asgi("DELETE", "/flows/%20%20"))
        self.assertEqual(status_code, 404)
        self.assertIn("detail", body)
        self.assertEqual(body["detail"], "Flow not found. It may have already been deleted.")

    # --- CORS Tests for Vite Development Server ---

    def test_cors_allowed_for_localhost_vite(self):
        """Verify CORS allows requests from http://localhost:5173."""
        status_code, _, headers = asyncio.run(
            invoke_asgi(
                "GET",
                "/flows",
                custom_headers={"origin": "http://localhost:5173"},
                return_headers=True,
            )
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(headers.get("access-control-allow-origin"), "http://localhost:5173")

    def test_cors_allowed_for_127_vite(self):
        """Verify CORS allows requests from http://127.0.0.1:5173."""
        status_code, _, headers = asyncio.run(
            invoke_asgi(
                "GET",
                "/flows",
                custom_headers={"origin": "http://127.0.0.1:5173"},
                return_headers=True,
            )
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(headers.get("access-control-allow-origin"), "http://127.0.0.1:5173")

    def test_cors_rejected_for_unauthorized_origin(self):
        """Verify CORS does not grant access-control-allow-origin to untrusted origins."""
    # --- Conversation Flow Design & Button Branching Tests ---

    def test_message_node_multiple_buttons_and_branching_persistence(self):
        """
        Verify:
        1. A Message node can contain multiple buttons with stable unique IDs.
        2. Each button has its own outgoing edge handle (sourceHandle).
        3. Different buttons connect to different Answer nodes.
        4. Multiple buttons can share a destination.
        5. Answer nodes persist answer_text, source_document, page_number, source_url.
        6. Editing button label preserves button ID.
        7. Full flow survives save (POST), reload (GET), and update (PUT).
        """
        flow_payload = {
            "name": "Higher Education Support Flow",
            "description": "Conversation flow with multiple interactive buttons and answer nodes",
            "flow_data": {
                "nodes": [
                    {
                        "id": "start-1",
                        "type": "start",
                        "position": {"x": 100, "y": 100},
                        "data": {
                            "label": "Start",
                            "text": "Triggered on conversation start",
                        },
                    },
                    {
                        "id": "message-welcome",
                        "type": "message",
                        "position": {"x": 100, "y": 250},
                        "data": {
                            "label": "Welcome Greeting",
                            "text": "Namaste! Welcome. How can I help you?",
                            "buttons": [
                                {
                                    "id": "btn_explore_programs",
                                    "label": "Explore All the Programs",
                                    "target": "answer-programs",
                                },
                                {
                                    "id": "btn_fee_calculator",
                                    "label": "Fee & ROI Calculator",
                                    "target": "answer-fee",
                                },
                                {
                                    "id": "btn_eligible_programs",
                                    "label": "Explore Eligible Programs",
                                    "target": "answer-programs",
                                },
                                {
                                    "id": "btn_accounts_detail",
                                    "label": "Accounts Detail",
                                    "target": "answer-accounts",
                                },
                            ],
                        },
                    },
                    {
                        "id": "answer-programs",
                        "type": "answer",
                        "position": {"x": 450, "y": 150},
                        "data": {
                            "label": "Programs Information",
                            "answer_text": "We offer Undergraduate, Postgraduate, and Executive Diplomas across engineering and management.",
                            "source_document": "Academic Prospectus 2026.pdf",
                            "page_number": "4",
                            "source_url": "https://university.edu/programs",
                        },
                    },
                    {
                        "id": "answer-fee",
                        "type": "answer",
                        "position": {"x": 450, "y": 300},
                        "data": {
                            "label": "Fee & Calculator",
                            "answer_text": "Please use the official Tuition Fee Calculator to estimate total program costs and financial aid.",
                            "source_document": "Tuition and Scholarship Policy.pdf",
                            "page_number": "12",
                            "source_url": "https://university.edu/calculator",
                        },
                    },
                    {
                        "id": "answer-accounts",
                        "type": "answer",
                        "position": {"x": 450, "y": 450},
                        "data": {
                            "label": "Accounts Support",
                            "answer_text": "For invoice receipts and fee payment installments, contact the accounts desk directly.",
                            "source_document": "Fee Schedule & Accounts.pdf",
                            "page_number": "8",
                            "source_url": "https://university.edu/accounts",
                        },
                    },
                ],
                "edges": [
                    {
                        "id": "edge-start-welcome",
                        "source": "start-1",
                        "target": "message-welcome",
                    },
                    {
                        "id": "edge-btn-programs",
                        "source": "message-welcome",
                        "sourceHandle": "btn_explore_programs",
                        "target": "answer-programs",
                        "label": "Explore All the Programs",
                    },
                    {
                        "id": "edge-btn-fee",
                        "source": "message-welcome",
                        "sourceHandle": "btn_fee_calculator",
                        "target": "answer-fee",
                        "label": "Fee & ROI Calculator",
                    },
                    {
                        "id": "edge-btn-eligible",
                        "source": "message-welcome",
                        "sourceHandle": "btn_eligible_programs",
                        "target": "answer-programs",
                        "label": "Explore Eligible Programs",
                    },
                    {
                        "id": "edge-btn-accounts",
                        "source": "message-welcome",
                        "sourceHandle": "btn_accounts_detail",
                        "target": "answer-accounts",
                        "label": "Accounts Detail",
                    },
                ],
            },
        }

        # 1. Create flow via POST
        create_status, created = asyncio.run(invoke_asgi("POST", "/flows", body=flow_payload))
        self.assertEqual(create_status, 201)
        flow_id = created["id"]

        # 2. Fetch flow via GET and verify structure
        get_status, fetched = asyncio.run(invoke_asgi("GET", f"/flows/{flow_id}"))
        self.assertEqual(get_status, 200)

        nodes = fetched["flow_data"]["nodes"]
        edges = fetched["flow_data"]["edges"]
        self.assertEqual(len(nodes), 5)
        self.assertEqual(len(edges), 5)

        # Verify Message Node buttons
        msg_node = next(n for n in nodes if n["id"] == "message-welcome")
        self.assertEqual(msg_node["type"], "message")
        buttons = msg_node["data"]["buttons"]
        self.assertEqual(len(buttons), 4)

        button_ids = [b["id"] for b in buttons]
        self.assertEqual(
            button_ids,
            ["btn_explore_programs", "btn_fee_calculator", "btn_eligible_programs", "btn_accounts_detail"]
        )

        # Verify branching handles on edges
        edge_handles = {e["id"]: e.get("sourceHandle") for e in edges if "sourceHandle" in e}
        self.assertEqual(len(edge_handles), 4)
        self.assertEqual(edge_handles["edge-btn-programs"], "btn_explore_programs")
        self.assertEqual(edge_handles["edge-btn-fee"], "btn_fee_calculator")
        self.assertEqual(edge_handles["edge-btn-eligible"], "btn_eligible_programs")
        self.assertEqual(edge_handles["edge-btn-accounts"], "btn_accounts_detail")

        # Verify shared destination (both btn_explore_programs and btn_eligible_programs point to answer-programs)
        programs_edges = [e for e in edges if e["target"] == "answer-programs"]
        self.assertEqual(len(programs_edges), 2)

        # Verify Answer Node manual sources
        ans_programs = next(n for n in nodes if n["id"] == "answer-programs")
        self.assertEqual(ans_programs["type"], "answer")
        self.assertEqual(ans_programs["data"]["source_document"], "Academic Prospectus 2026.pdf")
        self.assertEqual(ans_programs["data"]["page_number"], "4")
        self.assertEqual(ans_programs["data"]["source_url"], "https://university.edu/programs")

        # 3. Update button label without mutating button ID (PUT)
        buttons[0]["label"] = "Explore All Academic Programs (Updated)"
        update_payload = {
            "name": "Higher Education Support Flow - V2",
            "flow_data": {
                "nodes": nodes,
                "edges": edges,
            },
        }
        put_status, updated = asyncio.run(invoke_asgi("PUT", f"/flows/{flow_id}", body=update_payload))
        self.assertEqual(put_status, 200)

        # Verify persistence after PUT
        get_status_2, fetched_2 = asyncio.run(invoke_asgi("GET", f"/flows/{flow_id}"))
        self.assertEqual(get_status_2, 200)
        updated_msg_node = next(n for n in fetched_2["flow_data"]["nodes"] if n["id"] == "message-welcome")
        updated_btn = updated_msg_node["data"]["buttons"][0]
        self.assertEqual(updated_btn["id"], "btn_explore_programs")
        self.assertEqual(updated_btn["label"], "Explore All Academic Programs (Updated)")

    def test_backward_compatibility_flows_without_buttons_or_sources(self):
        """Verify legacy flows without buttons or source metadata load without error."""
        legacy_flow = {
            "name": "Legacy Flow",
            "flow_data": {
                "nodes": [
                    {"id": "node-1", "type": "start", "position": {"x": 0, "y": 0}, "data": {"text": "Legacy start"}},
                    {"id": "node-2", "type": "message", "position": {"x": 0, "y": 100}, "data": {"text": "Legacy message"}},
                ],
                "edges": [
                    {"id": "e-1-2", "source": "node-1", "target": "node-2"},
                ],
            },
        }
        status_code, created = asyncio.run(invoke_asgi("POST", "/flows", body=legacy_flow))
        self.assertEqual(status_code, 201)

        get_status, fetched = asyncio.run(invoke_asgi("GET", f"/flows/{created['id']}"))
        self.assertEqual(get_status, 200)
        self.assertEqual(len(fetched["flow_data"]["nodes"]), 2)
        self.assertEqual(len(fetched["flow_data"]["edges"]), 1)

    def test_sebi_flow_integrity(self):
        """
        Verify existing SEBI flow remains intact:
        Flow ID: 1b9c3c0c-dc3f-4902-990f-1f1226af3431
        Chatbot ID: 3843cdcb-72a2-46b1-80ba-28330e2b9a52
        """
        sebi_flow_id = "1b9c3c0c-dc3f-4902-990f-1f1226af3431"
        sebi_chatbot_id = "3843cdcb-72a2-46b1-80ba-28330e2b9a52"
        real_db_path = BACKEND_DIR / "data" / "flows.db"

        if real_db_path.exists():
            import sqlite3
            uri_path = f"file:{real_db_path.resolve()}?mode=ro"
            with sqlite3.connect(uri_path, uri=True) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT id, chatbot_id, name, flow_data FROM flows WHERE id = ?;",
                    (sebi_flow_id,)
                ).fetchone()
                self.assertIsNotNone(row, f"SEBI flow {sebi_flow_id} not found in database!")
                self.assertEqual(row["chatbot_id"], sebi_chatbot_id)
                self.assertIn("SEBI", row["name"])

                flow_data = json.loads(row["flow_data"])
                self.assertIn("nodes", flow_data)
                self.assertIn("edges", flow_data)
                self.assertGreaterEqual(len(flow_data["nodes"]), 7)
                self.assertGreaterEqual(len(flow_data["edges"]), 6)


if __name__ == "__main__":
    unittest.main()
