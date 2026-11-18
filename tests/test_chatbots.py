"""
Automated unit and integration tests for Chatbot APIs and Flow-to-Chatbot relationships.
Tests chatbot CRUD, validation, missing IDs, safe deletion behavior, flow association,
and filtering by chatbot using an isolated PostgreSQL test database.
"""

import asyncio
from datetime import datetime
import json
from pathlib import Path
import sys
import unittest
import uuid

# Ensure backend and test directories are importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import DEFAULT_CHATBOT_ID, get_db
from app.main import app
from app.models import Chatbot, Flow
from tests.test_config import (
    clean_isolated_test_db,
    init_isolated_test_db,
    override_get_test_db,
    TestingSessionLocal,
)


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


class TestChatbotsApi(unittest.TestCase):
    """Test suite for Chatbot endpoints and flow relationships."""

    def setUp(self):
        """Create an isolated temporary database for each test and override FastAPI get_db."""
        clean_isolated_test_db()
        init_isolated_test_db()
        app.dependency_overrides[get_db] = override_get_test_db

    def tearDown(self):
        """Reset FastAPI dependency overrides and clean test database."""
        app.dependency_overrides.clear()
        clean_isolated_test_db()

    def run_async(self, coro):
        """Helper to run async ASGI invocation in unittest."""
        return asyncio.run(coro)

    # ---------------------------------------------------------
    # Chatbot Creation Tests
    # ---------------------------------------------------------

    def test_create_chatbot_success(self):
        """Verify POST /chatbots creates a chatbot and persists to database."""
        payload = {
            "name": "Customer Support Bot",
            "description": "Handles FAQ and tier 1 support",
            "status": "active",
        }
        status_code, data = self.run_async(invoke_asgi("POST", "/chatbots", body=payload))

        self.assertEqual(status_code, 201)
        self.assertIn("id", data)
        self.assertEqual(data["name"], "Customer Support Bot")
        self.assertEqual(data["description"], "Handles FAQ and tier 1 support")
        self.assertEqual(data["status"], "active")
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

        # Verify DB persistence
        with TestingSessionLocal() as session:
            bot = session.get(Chatbot, data["id"])
            self.assertIsNotNone(bot)
            self.assertEqual(bot.name, "Customer Support Bot")

    def test_create_chatbot_validation_errors(self):
        """Verify POST /chatbots returns 422 for missing name, empty name, or invalid status."""
        # Missing name
        status_code, _ = self.run_async(invoke_asgi("POST", "/chatbots", body={"description": "No name"}))
        self.assertEqual(status_code, 422)

        # Empty/whitespace name
        status_code, _ = self.run_async(invoke_asgi("POST", "/chatbots", body={"name": "   "}))
        self.assertEqual(status_code, 422)

        # Invalid status
        status_code, _ = self.run_async(
            invoke_asgi("POST", "/chatbots", body={"name": "Bot", "status": "unknown_status"})
        )
        self.assertEqual(status_code, 422)

    # ---------------------------------------------------------
    # Chatbot Retrieval & List Tests
    # ---------------------------------------------------------

    def test_list_chatbots_empty_and_populated(self):
        """Verify GET /chatbots retrieves all chatbots including the default chatbot."""
        # Initially only default-chatbot exists from init_db
        status_code, data = self.run_async(invoke_asgi("GET", "/chatbots"))
        self.assertEqual(status_code, 200)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], DEFAULT_CHATBOT_ID)

        # Create two more chatbots
        self.run_async(invoke_asgi("POST", "/chatbots", body={"name": "Bot Alpha", "status": "active"}))
        self.run_async(invoke_asgi("POST", "/chatbots", body={"name": "Bot Beta", "status": "inactive"}))

        status_code, data = self.run_async(invoke_asgi("GET", "/chatbots"))
        self.assertEqual(status_code, 200)
        self.assertEqual(len(data), 3)

    def test_get_chatbot_by_id_success(self):
        """Verify GET /chatbots/{chatbot_id} returns the specific chatbot."""
        payload = {"name": "Sales Assistant", "description": "Lead generation", "status": "active"}
        _, created = self.run_async(invoke_asgi("POST", "/chatbots", body=payload))
        bot_id = created["id"]

        status_code, data = self.run_async(invoke_asgi("GET", f"/chatbots/{bot_id}"))
        self.assertEqual(status_code, 200)
        self.assertEqual(data["id"], bot_id)
        self.assertEqual(data["name"], "Sales Assistant")

    def test_get_chatbot_by_id_not_found(self):
        """Verify GET /chatbots/{chatbot_id} returns 404 for nonexistent chatbot."""
        fake_id = str(uuid.uuid4())
        status_code, data = self.run_async(invoke_asgi("GET", f"/chatbots/{fake_id}"))
        self.assertEqual(status_code, 404)
        self.assertIn("not found", data["detail"].lower())

    def test_get_chatbot_invalid_empty_id(self):
        """Verify GET /chatbots/{whitespace} returns 404."""
        status_code, _ = self.run_async(invoke_asgi("GET", "/chatbots/%20%20"))
        self.assertEqual(status_code, 404)

    # ---------------------------------------------------------
    # Chatbot Update Tests
    # ---------------------------------------------------------

    def test_update_chatbot_success(self):
        """Verify PUT /chatbots/{chatbot_id} updates name, description, status and updated_at."""
        _, created = self.run_async(
            invoke_asgi("POST", "/chatbots", body={"name": "Initial Name", "status": "active"})
        )
        bot_id = created["id"]

        update_payload = {
            "name": "Updated Name",
            "description": "New description",
            "status": "inactive",
        }
        status_code, updated = self.run_async(
            invoke_asgi("PUT", f"/chatbots/{bot_id}", body=update_payload)
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(updated["name"], "Updated Name")
        self.assertEqual(updated["description"], "New description")
        self.assertEqual(updated["status"], "inactive")
        self.assertEqual(updated["created_at"], created["created_at"])

    def test_update_chatbot_not_found(self):
        """Verify PUT /chatbots/{chatbot_id} returns 404 for nonexistent ID."""
        status_code, _ = self.run_async(
            invoke_asgi("PUT", f"/chatbots/{uuid.uuid4()}", body={"name": "New Name", "status": "active"})
        )
        self.assertEqual(status_code, 404)

    def test_update_chatbot_validation_errors(self):
        """Verify PUT /chatbots/{chatbot_id} returns 422 for invalid payloads."""
        _, created = self.run_async(
            invoke_asgi("POST", "/chatbots", body={"name": "Valid Bot", "status": "active"})
        )
        bot_id = created["id"]

        # Empty name
        status_code, _ = self.run_async(
            invoke_asgi("PUT", f"/chatbots/{bot_id}", body={"name": "   ", "status": "active"})
        )
        self.assertEqual(status_code, 422)

    # ---------------------------------------------------------
    # Chatbot Delete Tests & Safe Deletion Policy
    # ---------------------------------------------------------

    def test_delete_chatbot_success_when_no_flows_associated(self):
        """Verify DELETE /chatbots/{chatbot_id} removes a chatbot that has zero flows."""
        _, bot = self.run_async(
            invoke_asgi("POST", "/chatbots", body={"name": "Orphan Bot", "status": "active"})
        )
        bot_id = bot["id"]

        status_code, data = self.run_async(invoke_asgi("DELETE", f"/chatbots/{bot_id}"))
        self.assertEqual(status_code, 200)
        self.assertEqual(data["id"], bot_id)
        self.assertIn("deleted successfully", data["message"])

        # Verify row is removed from DB
        with TestingSessionLocal() as session:
            bot = session.get(Chatbot, bot_id)
            self.assertIsNone(bot)

    def test_delete_chatbot_safe_deletion_rejects_when_flows_exist(self):
        """
        Safe deletion requirement:
        Verify DELETE /chatbots/{chatbot_id} returns 400 Bad Request and does NOT
        silently delete or orphan flows when the chatbot has associated flows.
        """
        # Create a chatbot
        _, bot = self.run_async(
            invoke_asgi("POST", "/chatbots", body={"name": "Parent Bot", "status": "active"})
        )
        bot_id = bot["id"]

        # Create a flow linked to this chatbot
        flow_payload = {
            "chatbot_id": bot_id,
            "name": "Linked Flow",
            "flow_data": {"nodes": [], "edges": []},
        }
        _, flow = self.run_async(invoke_asgi("POST", "/flows", body=flow_payload))
        flow_id = flow["id"]

        # Attempt to delete the chatbot -> MUST be rejected with HTTP 400
        status_code, err_data = self.run_async(invoke_asgi("DELETE", f"/chatbots/{bot_id}"))
        self.assertEqual(status_code, 400)
        self.assertIn("Cannot delete chatbot", err_data["detail"])
        self.assertIn("associated flow", err_data["detail"])

        # Verify chatbot still exists in DB
        with TestingSessionLocal() as session:
            bot = session.get(Chatbot, bot_id)
            self.assertIsNotNone(bot, "Chatbot should not have been deleted")

            # Verify flow still exists in DB
            flow_obj = session.get(Flow, flow_id)
            self.assertIsNotNone(flow_obj, "Flow must be preserved intact")

    def test_delete_chatbot_not_found(self):
        """Verify DELETE /chatbots/{chatbot_id} returns 404 for nonexistent chatbot."""
        status_code, _ = self.run_async(invoke_asgi("DELETE", f"/chatbots/{uuid.uuid4()}"))
        self.assertEqual(status_code, 404)

    # ---------------------------------------------------------
    # Chatbot Flows Listing Tests
    # ---------------------------------------------------------

    def test_list_flows_by_chatbot_success(self):
        """Verify GET /chatbots/{chatbot_id}/flows returns only flows for that chatbot."""
        # Create two chatbots
        _, bot1 = self.run_async(invoke_asgi("POST", "/chatbots", body={"name": "Bot 1", "status": "active"}))
        _, bot2 = self.run_async(invoke_asgi("POST", "/chatbots", body={"name": "Bot 2", "status": "active"}))

        # Create 2 flows for Bot 1
        self.run_async(
            invoke_asgi("POST", "/flows", body={"chatbot_id": bot1["id"], "name": "Flow 1A", "flow_data": {"nodes": [], "edges": []}})
        )
        self.run_async(
            invoke_asgi("POST", "/flows", body={"chatbot_id": bot1["id"], "name": "Flow 1B", "flow_data": {"nodes": [], "edges": []}})
        )

        # Create 1 flow for Bot 2
        self.run_async(
            invoke_asgi("POST", "/flows", body={"chatbot_id": bot2["id"], "name": "Flow 2A", "flow_data": {"nodes": [], "edges": []}})
        )

        # Fetch flows for Bot 1
        status_code, bot1_flows = self.run_async(invoke_asgi("GET", f"/chatbots/{bot1['id']}/flows"))
        self.assertEqual(status_code, 200)
        self.assertEqual(len(bot1_flows), 2)
        flow_names = {f["name"] for f in bot1_flows}
        self.assertEqual(flow_names, {"Flow 1A", "Flow 1B"})

        # Fetch flows for Bot 2
        status_code, bot2_flows = self.run_async(invoke_asgi("GET", f"/chatbots/{bot2['id']}/flows"))
        self.assertEqual(status_code, 200)
        self.assertEqual(len(bot2_flows), 1)
        self.assertEqual(bot2_flows[0]["name"], "Flow 2A")

    def test_list_flows_by_chatbot_not_found(self):
        """Verify GET /chatbots/{chatbot_id}/flows returns 404 if chatbot does not exist."""
        status_code, _ = self.run_async(invoke_asgi("GET", f"/chatbots/{uuid.uuid4()}/flows"))
        self.assertEqual(status_code, 404)


if __name__ == "__main__":
    unittest.main()
