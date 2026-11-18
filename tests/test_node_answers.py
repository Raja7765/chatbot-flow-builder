"""
Automated unit and integration tests for Node Answers and Answer Blocks CRUD APIs.
Tests creation, retrieval, position ordering, transactional updates, deletion,
validation rules, duplicate prevention, and foreign-key constraints using an isolated PostgreSQL test database.
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

from app.database import DEFAULT_CHATBOT_ID, get_db, get_utc_now
from app.main import app
from app.models import AnswerBlock, Flow, MediaAsset, NodeAnswer
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
            for h_k, h_v in msg.get("headers", []):
                resp_headers[h_k.decode("latin1").lower()] = h_v.decode("latin1")
        elif msg["type"] == "http.response.body":
            resp_body += msg.get("body", b"")

    try:
        parsed_json = json.loads(resp_body.decode("utf-8")) if resp_body else None
    except Exception:
        parsed_json = resp_body.decode("utf-8", errors="replace")

    return status_code, parsed_json, resp_headers


class TestNodeAnswersApi(unittest.TestCase):
    """
    Test suite for Node Answers and Content Blocks CRUD APIs.
    """

    @classmethod
    def setUpClass(cls):
        init_isolated_test_db()
        app.dependency_overrides[get_db] = override_get_test_db

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.pop(get_db, None)

    def setUp(self):
        clean_isolated_test_db()
        init_isolated_test_db()

        # Seed a test flow with known node IDs for tests
        self.flow_id = str(uuid.uuid4())
        self.node_id_1 = "node-welcome"
        self.node_id_2 = "node-accreditation"

        now = get_utc_now()
        with TestingSessionLocal() as db:
            flow = Flow(
                id=self.flow_id,
                chatbot_id=DEFAULT_CHATBOT_ID,
                name="Test Flow for Node Answers",
                description="Flow containing nodes to test answer block associations",
                flow_data={
                    "nodes": [
                        {"id": self.node_id_1, "type": "landing_page", "data": {"label": "Welcome"}},
                        {"id": self.node_id_2, "type": "menu", "data": {"label": "Accreditation"}},
                    ],
                    "edges": [
                        {"id": "e1-2", "source": self.node_id_1, "target": self.node_id_2}
                    ],
                },
                created_at=now,
                updated_at=now,
            )
            db.add(flow)
            db.commit()

    # 1. Create an answer with multiple text blocks
    def test_create_answer_with_multiple_text_blocks(self):
        """Verify POST creates an answer with multiple text blocks returning HTTP 201."""
        payload = {
            "language": "en",
            "blocks": [
                {
                    "block_type": "text",
                    "content": "Welcome to NABH",
                    "position": 1,
                },
                {
                    "block_type": "text",
                    "content": "This program is designed for hospitals with more than 50 beds.",
                    "position": 2,
                },
            ],
        }

        status_code, body, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer", body=payload)
        )

        self.assertEqual(status_code, 201)
        self.assertIn("id", body)
        self.assertEqual(body["flow_id"], self.flow_id)
        self.assertEqual(body["node_id"], self.node_id_1)
        self.assertEqual(body["language"], "en")
        self.assertEqual(len(body["blocks"]), 2)
        self.assertEqual(body["blocks"][0]["content"], "Welcome to NABH")
        self.assertEqual(body["blocks"][0]["position"], 1)
        self.assertEqual(body["blocks"][1]["content"], "This program is designed for hospitals with more than 50 beds.")
        self.assertEqual(body["blocks"][1]["position"], 2)

    # 2. Retrieve an answer
    def test_retrieve_answer_success(self):
        """Verify GET returns the created answer and its blocks."""
        payload = {
            "language": "en",
            "blocks": [
                {"block_type": "text", "content": "First greeting", "position": 1},
            ],
        }

        # Create
        status_code, create_body, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer", body=payload)
        )
        self.assertEqual(status_code, 201)

        # Retrieve
        status_code, get_body, _ = asyncio.run(
            invoke_asgi("GET", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer?language=en")
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(get_body["id"], create_body["id"])
        self.assertEqual(get_body["flow_id"], self.flow_id)
        self.assertEqual(get_body["node_id"], self.node_id_1)
        self.assertEqual(get_body["language"], "en")
        self.assertEqual(len(get_body["blocks"]), 1)
        self.assertEqual(get_body["blocks"][0]["content"], "First greeting")

    # 3. Verify blocks are returned in correct position order
    def test_blocks_returned_in_ascending_position_order(self):
        """Verify that blocks inserted out of order are returned sorted by position ascending."""
        payload = {
            "language": "en",
            "blocks": [
                {"block_type": "text", "content": "Third block", "position": 3},
                {"block_type": "text", "content": "First block", "position": 1},
                {"block_type": "text", "content": "Second block", "position": 2},
            ],
        }

        status_code, body, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer", body=payload)
        )
        self.assertEqual(status_code, 201)
        self.assertEqual(body["blocks"][0]["position"], 1)
        self.assertEqual(body["blocks"][0]["content"], "First block")
        self.assertEqual(body["blocks"][1]["position"], 2)
        self.assertEqual(body["blocks"][1]["content"], "Second block")
        self.assertEqual(body["blocks"][2]["position"], 3)
        self.assertEqual(body["blocks"][2]["content"], "Third block")

        # Also verify GET returns them in the same sorted order
        status_code, get_body, _ = asyncio.run(
            invoke_asgi("GET", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer?language=en")
        )
        self.assertEqual(status_code, 200)
        positions = [b["position"] for b in get_body["blocks"]]
        self.assertEqual(positions, [1, 2, 3])

    # 4. Update an existing answer
    def test_update_existing_answer_replaces_blocks_transactionally(self):
        """Verify PUT updates answer and replaces blocks transactionally."""
        create_payload = {
            "language": "en",
            "blocks": [
                {"block_type": "text", "content": "Initial text", "position": 1},
            ],
        }
        status_code, created, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer", body=create_payload)
        )
        self.assertEqual(status_code, 201)

        update_payload = {
            "language": "en",
            "blocks": [
                {"block_type": "text", "content": "Updated block alpha", "position": 1},
                {"block_type": "text", "content": "Updated block beta", "position": 2},
            ],
        }
        status_code, updated, _ = asyncio.run(
            invoke_asgi("PUT", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer", body=update_payload)
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(updated["id"], created["id"])
        self.assertEqual(len(updated["blocks"]), 2)
        self.assertEqual(updated["blocks"][0]["content"], "Updated block alpha")
        self.assertEqual(updated["blocks"][1]["content"], "Updated block beta")

        # Verify in database that old block was deleted and only 2 blocks exist
        with TestingSessionLocal() as db:
            blocks = db.query(AnswerBlock).filter(AnswerBlock.answer_id == uuid.UUID(created["id"])).all()
            self.assertEqual(len(blocks), 2)

    # 5. Delete an answer
    def test_delete_answer_success(self):
        """Verify DELETE removes answer and cascades removal to answer blocks."""
        create_payload = {
            "language": "en",
            "blocks": [
                {"block_type": "text", "content": "To be deleted", "position": 1},
            ],
        }
        status_code, created, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer", body=create_payload)
        )
        self.assertEqual(status_code, 201)
        answer_id = created["id"]

        # Delete
        status_code, del_body, _ = asyncio.run(
            invoke_asgi("DELETE", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer?language=en")
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(del_body["id"], answer_id)

        # GET should now return 404
        status_code, _, _ = asyncio.run(
            invoke_asgi("GET", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer?language=en")
        )
        self.assertEqual(status_code, 404)

        # Database check: answer and blocks must be completely gone
        with TestingSessionLocal() as db:
            ans = db.get(NodeAnswer, uuid.UUID(answer_id))
            self.assertIsNone(ans)
            blocks = db.query(AnswerBlock).filter(AnswerBlock.answer_id == uuid.UUID(answer_id)).all()
            self.assertEqual(len(blocks), 0)

    # 6. Create an answer for a nonexistent flow
    def test_create_answer_nonexistent_flow_returns_404(self):
        """Verify POST returns HTTP 404 when flow does not exist."""
        payload = {
            "language": "en",
            "blocks": [{"block_type": "text", "content": "Sample", "position": 1}],
        }
        status_code, body, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/unknown-flow-id/nodes/{self.node_id_1}/answer", body=payload)
        )
        self.assertEqual(status_code, 404)
        self.assertIn("not found", body["detail"].lower())

    # 7. Create an answer for a nonexistent node
    def test_create_answer_nonexistent_node_returns_404(self):
        """Verify POST returns HTTP 404 when node_id does not exist inside flow."""
        payload = {
            "language": "en",
            "blocks": [{"block_type": "text", "content": "Sample", "position": 1}],
        }
        status_code, body, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{self.flow_id}/nodes/ghost-node/answer", body=payload)
        )
        self.assertEqual(status_code, 404)
        self.assertIn("not found", body["detail"].lower())

    # 8. Retrieve a nonexistent answer
    def test_retrieve_nonexistent_answer_returns_404(self):
        """Verify GET returns HTTP 404 when answer does not exist."""
        status_code, body, _ = asyncio.run(
            invoke_asgi("GET", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer?language=en")
        )
        self.assertEqual(status_code, 404)
        self.assertIn("not found", body["detail"].lower())

    # 9. Duplicate answer prevention
    def test_duplicate_answer_prevention_returns_409(self):
        """Verify POST returns HTTP 409 Conflict when answer for (flow, node, language) already exists."""
        payload = {
            "language": "en",
            "blocks": [{"block_type": "text", "content": "First instance", "position": 1}],
        }
        status_code, _, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer", body=payload)
        )
        self.assertEqual(status_code, 201)

        # Attempt to create duplicate with same language
        status_code, body, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer", body=payload)
        )
        self.assertEqual(status_code, 409)
        self.assertIn("already exists", body["detail"].lower())

        # Creating for a DIFFERENT language (e.g. 'hi') should succeed
        hi_payload = {
            "language": "hi",
            "blocks": [{"block_type": "text", "content": "Hindi translation", "position": 1}],
        }
        status_code, body, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer", body=hi_payload)
        )
        self.assertEqual(status_code, 201)
        self.assertEqual(body["language"], "hi")

    # 10. Invalid block type and empty text validation
    def test_invalid_block_type_and_empty_text_validation(self):
        """Verify validation errors for unknown block type and empty text content."""
        # Invalid block type
        invalid_type_payload = {
            "language": "en",
            "blocks": [{"block_type": "audio", "content": "Audio file", "position": 1}],
        }
        status_code, _, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer", body=invalid_type_payload)
        )
        self.assertEqual(status_code, 422)

        # Empty text content
        empty_text_payload = {
            "language": "en",
            "blocks": [{"block_type": "text", "content": "   ", "position": 1}],
        }
        status_code, _, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer", body=empty_text_payload)
        )
        self.assertEqual(status_code, 422)

    # 11. Media block with nonexistent media_id
    def test_media_block_with_nonexistent_media_id_returns_404(self):
        """Verify referencing a non-existent media asset returns HTTP 404."""
        missing_media_id = str(uuid.uuid4())
        payload = {
            "language": "en",
            "blocks": [
                {
                    "block_type": "image",
                    "media_id": missing_media_id,
                    "position": 1,
                }
            ],
        }
        status_code, body, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer", body=payload)
        )
        self.assertEqual(status_code, 404)
        self.assertIn("not found", body["detail"].lower())

    # 11b. Media block with valid media_id succeeds
    def test_media_block_with_existing_media_id_succeeds(self):
        """Verify creating an answer with a valid media asset succeeds."""
        media_id = uuid.uuid4()
        now = get_utc_now()
        with TestingSessionLocal() as db:
            asset = MediaAsset(
                id=media_id,
                file_name="flowchart.png",
                stored_name=f"stored_{media_id.hex}.png",
                mime_type="image/png",
                media_type="image",
                storage_key="/uploads/flowchart.png",
                file_size=54321,
                checksum="abc123hash",
                created_at=now,
            )
            db.add(asset)
            db.commit()

        payload = {
            "language": "en",
            "blocks": [
                {
                    "block_type": "image",
                    "media_id": str(media_id),
                    "position": 1,
                    "metadata": {"alt": "Flowchart diagram"},
                }
            ],
        }
        status_code, body, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{self.flow_id}/nodes/{self.node_id_1}/answer", body=payload)
        )
        self.assertEqual(status_code, 201)
        self.assertEqual(body["blocks"][0]["block_type"], "image")
        self.assertEqual(body["blocks"][0]["media_id"], str(media_id))
        self.assertEqual(body["blocks"][0]["metadata"]["alt"], "Flowchart diagram")

    # 12. Verify existing chatbot, flow and node definition APIs still work
    def test_existing_apis_continue_working(self):
        """Verify that existing chatbots, flows, and node_definitions endpoints remain fully operational."""
        # Chatbots list
        status_code, bots, _ = asyncio.run(invoke_asgi("GET", "/chatbots"))
        self.assertEqual(status_code, 200)
        self.assertIsInstance(bots, list)

        # Flows list
        status_code, flows, _ = asyncio.run(invoke_asgi("GET", "/flows"))
        self.assertEqual(status_code, 200)
        self.assertIsInstance(flows, list)

        # Node definitions list
        status_code, node_defs, _ = asyncio.run(invoke_asgi("GET", "/node-definitions"))
        self.assertEqual(status_code, 200)
        self.assertIsInstance(node_defs, list)
        self.assertGreaterEqual(len(node_defs), 12)


if __name__ == "__main__":
    unittest.main()

