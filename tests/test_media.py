"""
Automated unit and integration tests for Media Assets Upload, Retrieval, and Lifecycle APIs.
Tests image/PDF/video uploads, MIME verification, size limits, download streaming,
metadata inspection, reference-protected deletion, and filesystem cleanup upon failure.
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
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
from app.media_storage import (
    MAX_FILE_SIZE,
    UPLOAD_DIRS,
    UPLOADS_BASE_DIR,
    ensure_upload_dirs,
    resolve_storage_path,
)
from app.models import AnswerBlock, Flow, MediaAsset, NodeAnswer
from tests.test_config import (
    clean_isolated_test_db,
    init_isolated_test_db,
    override_get_test_db,
    TestingSessionLocal,
)


def build_multipart_payload(
    fields: dict = None,
    filename: str = "test.png",
    content: bytes = b"",
    content_type: str = "image/png",
) -> tuple:
    """Helper to build raw multipart/form-data payload and headers."""
    boundary = "----TestBoundary" + uuid.uuid4().hex
    body = bytearray()

    if fields:
        for k, v in fields.items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
            body.extend(f"{v}\r\n".encode("utf-8"))

    # File part
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
    body.extend(content)
    body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    headers = {"content-type": f"multipart/form-data; boundary={boundary}"}
    return bytes(body), headers


async def invoke_asgi(
    method: str,
    path: str,
    body: dict = None,
    raw_body: bytes = None,
    custom_headers: dict = None,
) -> tuple:
    """Simulate ASGI HTTP request with proper content-type handling for multipart."""
    if raw_body is not None:
        payload_bytes = raw_body
    elif body is not None:
        payload_bytes = json.dumps(body).encode("utf-8")
    else:
        payload_bytes = b""

    headers = [
        (b"host", b"testserver"),
        (b"content-length", str(len(payload_bytes)).encode("latin1")),
    ]

    has_content_type = False
    if custom_headers:
        for k, v in custom_headers.items():
            if k.lower() == "content-type":
                has_content_type = True
            headers.append((k.lower().encode("latin1"), v.encode("latin1")))

    if not has_content_type:
        headers.append((b"content-type", b"application/json"))

    messages = []
    has_sent_body = False
    disconnected = asyncio.Event()

    async def receive():
        nonlocal has_sent_body
        if not has_sent_body:
            has_sent_body = True
            return {"type": "http.request", "body": payload_bytes, "more_body": False}
        await disconnected.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)
        if message.get("type") == "http.response.body" and not message.get("more_body", False):
            disconnected.set()

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
        parsed_json = resp_body

    return status_code, parsed_json, resp_headers


class TestMediaApi(unittest.TestCase):
    """
    Test suite for Media Asset upload, download, metadata, and deletion APIs.
    """

    # Valid binary signatures for tests
    VALID_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    VALID_PDF = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    VALID_MP4 = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free"

    @classmethod
    def setUpClass(cls):
        init_isolated_test_db()
        ensure_upload_dirs()
        app.dependency_overrides[get_db] = override_get_test_db

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.pop(get_db, None)

    def setUp(self):
        clean_isolated_test_db()
        init_isolated_test_db()
        ensure_upload_dirs()

    def tearDown(self):
        # Clean any files in upload dirs created during test
        for d in UPLOAD_DIRS.values():
            if d.is_dir():
                for f in d.iterdir():
                    if f.is_file():
                        try:
                            f.unlink()
                        except Exception:
                            pass

    # 1. Successful image upload
    def test_successful_image_upload(self):
        """Verify uploading a valid PNG creates database record and saves file in images directory."""
        body, headers = build_multipart_payload(
            filename="diagram.png",
            content=self.VALID_PNG,
            content_type="image/png",
        )

        status, resp, _ = asyncio.run(invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=headers))
        self.assertEqual(status, 201)
        self.assertIn("id", resp)
        self.assertEqual(resp["file_name"], "diagram.png")
        self.assertEqual(resp["mime_type"], "image/png")
        self.assertEqual(resp["media_type"], "image")
        self.assertTrue(resp["storage_key"].startswith("uploads/images/"))
        self.assertEqual(resp["file_size"], len(self.VALID_PNG))
        self.assertEqual(resp["checksum"], hashlib.sha256(self.VALID_PNG).hexdigest())

        # Verify physical file exists
        file_path = resolve_storage_path(resp["storage_key"])
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_bytes(), self.VALID_PNG)

    # 2. Successful PDF upload
    def test_successful_pdf_upload(self):
        """Verify uploading a valid PDF saves to documents directory."""
        body, headers = build_multipart_payload(
            filename="guidelines.pdf",
            content=self.VALID_PDF,
            content_type="application/pdf",
        )

        status, resp, _ = asyncio.run(invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=headers))
        self.assertEqual(status, 201)
        self.assertEqual(resp["file_name"], "guidelines.pdf")
        self.assertEqual(resp["mime_type"], "application/pdf")
        self.assertEqual(resp["media_type"], "document")
        self.assertTrue(resp["storage_key"].startswith("uploads/documents/"))

        file_path = resolve_storage_path(resp["storage_key"])
        self.assertTrue(file_path.is_file())

    # 3. Successful video upload
    def test_successful_video_upload(self):
        """Verify uploading a valid MP4 saves to videos directory."""
        body, headers = build_multipart_payload(
            filename="demo.mp4",
            content=self.VALID_MP4,
            content_type="video/mp4",
        )

        status, resp, _ = asyncio.run(invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=headers))
        self.assertEqual(status, 201)
        self.assertEqual(resp["file_name"], "demo.mp4")
        self.assertEqual(resp["mime_type"], "video/mp4")
        self.assertEqual(resp["media_type"], "video")
        self.assertTrue(resp["storage_key"].startswith("uploads/videos/"))

        file_path = resolve_storage_path(resp["storage_key"])
        self.assertTrue(file_path.is_file())

    # 4. Unsupported extension
    def test_unsupported_extension_returns_422(self):
        """Verify that uploading files with dangerous/unsupported extensions is rejected."""
        body, headers = build_multipart_payload(
            filename="script.exe",
            content=b"MZ\x90\x00executable content",
            content_type="application/x-msdownload",
        )

        status, resp, _ = asyncio.run(invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=headers))
        self.assertEqual(status, 422)
        self.assertIn("unsupported file extension", resp["detail"].lower())

    # 5. Invalid MIME / content (spoofed extension)
    def test_spoofed_extension_returns_422(self):
        """Verify that a text file disguised with a .png extension is rejected via magic byte inspection."""
        spoofed_content = b"This is plain text pretending to be an image file."
        body, headers = build_multipart_payload(
            filename="fake_image.png",
            content=spoofed_content,
            content_type="image/png",
        )

        status, resp, _ = asyncio.run(invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=headers))
        self.assertEqual(status, 422)
        self.assertIn("does not match", resp["detail"].lower())

    # 6. Oversized file
    def test_oversized_file_returns_413(self):
        """Verify that uploading a file larger than MAX_FILE_SIZE (20 MB) is rejected with 413."""
        # Header for valid PNG + dummy payload exceeding 20 MB
        oversized_data = b"\x89PNG\r\n\x1a\n" + b"A" * (MAX_FILE_SIZE + 1024)
        body, headers = build_multipart_payload(
            filename="huge.png",
            content=oversized_data,
            content_type="image/png",
        )

        status, resp, _ = asyncio.run(invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=headers))
        self.assertEqual(status, 413)
        self.assertIn("exceeds maximum permitted limit", resp["detail"].lower())

    # 7. Retrieve existing media
    def test_retrieve_existing_media_file(self):
        """Verify GET /media/{media_id} returns the binary file with correct Content-Type."""
        body, headers = build_multipart_payload(
            filename="avatar.png",
            content=self.VALID_PNG,
            content_type="image/png",
        )
        status, upload_resp, _ = asyncio.run(invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=headers))
        self.assertEqual(status, 201)
        media_id = upload_resp["id"]

        status, raw_file_bytes, resp_headers = asyncio.run(invoke_asgi("GET", f"/media/{media_id}"))
        self.assertEqual(status, 200)
        self.assertEqual(raw_file_bytes, self.VALID_PNG)
        self.assertIn("image/png", resp_headers.get("content-type", ""))

    # 8. Retrieve nonexistent media
    def test_retrieve_nonexistent_media_returns_404(self):
        """Verify GET returns 404 for unknown media UUID."""
        missing_id = str(uuid.uuid4())
        status, resp, _ = asyncio.run(invoke_asgi("GET", f"/media/{missing_id}"))
        self.assertEqual(status, 404)
        self.assertIn("not found", resp["detail"].lower())

    # 9. Metadata retrieval
    def test_retrieve_media_metadata(self):
        """Verify GET /media/{media_id}/metadata returns asset details from database."""
        body, headers = build_multipart_payload(
            filename="guide.pdf",
            content=self.VALID_PDF,
            content_type="application/pdf",
        )
        status, upload_resp, _ = asyncio.run(invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=headers))
        self.assertEqual(status, 201)
        media_id = upload_resp["id"]

        status, meta_resp, _ = asyncio.run(invoke_asgi("GET", f"/media/{media_id}/metadata"))
        self.assertEqual(status, 200)
        self.assertEqual(meta_resp["id"], media_id)
        self.assertEqual(meta_resp["file_name"], "guide.pdf")
        self.assertEqual(meta_resp["mime_type"], "application/pdf")
        self.assertIn("created_at", meta_resp)

    # 10. Delete unreferenced media
    def test_delete_unreferenced_media_success(self):
        """Verify DELETE removes media record and physical file when not referenced."""
        body, headers = build_multipart_payload(
            filename="temp.png",
            content=self.VALID_PNG,
            content_type="image/png",
        )
        status, upload_resp, _ = asyncio.run(invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=headers))
        self.assertEqual(status, 201)
        media_id = upload_resp["id"]
        storage_key = upload_resp["storage_key"]

        file_path = resolve_storage_path(storage_key)
        self.assertTrue(file_path.is_file())

        status, del_resp, _ = asyncio.run(invoke_asgi("DELETE", f"/media/{media_id}"))
        self.assertEqual(status, 200)
        self.assertEqual(del_resp["id"], media_id)

        # Physical file must be deleted from disk
        self.assertFalse(file_path.exists())

        # DB record must be gone
        with TestingSessionLocal() as db:
            self.assertIsNone(db.get(MediaAsset, uuid.UUID(media_id)))

    # 11. Prevent deletion of referenced media
    def test_prevent_deletion_of_referenced_media_returns_409(self):
        """Verify that DELETE returns 409 Conflict if media is referenced by an answer block."""
        body, headers = build_multipart_payload(
            filename="protected.png",
            content=self.VALID_PNG,
            content_type="image/png",
        )
        status, upload_resp, _ = asyncio.run(invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=headers))
        self.assertEqual(status, 201)
        media_id = upload_resp["id"]

        # Create flow, node answer, and answer block referencing this media_id
        flow_id = str(uuid.uuid4())
        node_id = "test-node-1"
        now = get_utc_now()
        with TestingSessionLocal() as db:
            flow = Flow(
                id=flow_id,
                chatbot_id=DEFAULT_CHATBOT_ID,
                name="Flow with Media",
                flow_data={"nodes": [{"id": node_id}], "edges": []},
                created_at=now,
                updated_at=now,
            )
            db.add(flow)
            db.flush()

            answer = NodeAnswer(
                id=uuid.uuid4(),
                flow_id=flow_id,
                node_id=node_id,
                language="en",
                created_at=now,
                updated_at=now,
            )
            db.add(answer)
            db.flush()

            block = AnswerBlock(
                id=uuid.uuid4(),
                answer_id=answer.id,
                block_type="image",
                media_id=uuid.UUID(media_id),
                position=1,
                created_at=now,
                updated_at=now,
            )
            db.add(block)
            db.commit()

        # Attempt DELETE should fail with 409 Conflict
        status, del_resp, _ = asyncio.run(invoke_asgi("DELETE", f"/media/{media_id}"))
        self.assertEqual(status, 409)
        self.assertIn("referenced by 1 answer block", del_resp["detail"].lower())

        # Physical file and database record must still exist
        file_path = resolve_storage_path(upload_resp["storage_key"])
        self.assertTrue(file_path.is_file())

    # 12. File cleanup after database failure
    def test_file_cleanup_after_database_failure(self):
        """Verify that if database commit raises an exception, the written file is removed from disk."""
        body, headers = build_multipart_payload(
            filename="cleanup_test.png",
            content=self.VALID_PNG,
            content_type="image/png",
        )

        # Mock Session.commit to raise an exception
        with patch("sqlalchemy.orm.Session.commit", side_effect=RuntimeError("Simulated DB failure")):
            try:
                status, resp, _ = asyncio.run(invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=headers))
            except Exception:
                pass

        # Check images directory - no files should linger
        image_files = list(UPLOAD_DIRS["image"].glob("*"))
        self.assertEqual(len(image_files), 0, f"Expected 0 image files after failure cleanup, found: {image_files}")

    # 13. Existing Node Answer APIs still work with uploaded media
    def test_node_answer_referencing_uploaded_media_integration(self):
        """Verify that an uploaded media asset can be cleanly referenced in a Node Answer block."""
        # 1. Upload image
        body, headers = build_multipart_payload(
            filename="infographic.png",
            content=self.VALID_PNG,
            content_type="image/png",
        )
        status, upload_resp, _ = asyncio.run(invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=headers))
        self.assertEqual(status, 201)
        media_id = upload_resp["id"]

        # 2. Create flow with node
        flow_id = str(uuid.uuid4())
        node_id = "node-infographic"
        now = get_utc_now()
        with TestingSessionLocal() as db:
            flow = Flow(
                id=flow_id,
                chatbot_id=DEFAULT_CHATBOT_ID,
                name="Flow for Media Test",
                flow_data={"nodes": [{"id": node_id}], "edges": []},
                created_at=now,
                updated_at=now,
            )
            db.add(flow)
            db.commit()

        # 3. Create node answer referencing this media_id
        answer_payload = {
            "language": "en",
            "blocks": [
                {"block_type": "text", "content": "Please inspect the diagram below:", "position": 1},
                {"block_type": "image", "media_id": media_id, "position": 2, "metadata": {"caption": "Accreditation stages"}},
            ],
        }
        status, ans_resp, _ = asyncio.run(
            invoke_asgi("POST", f"/flows/{flow_id}/nodes/{node_id}/answer", body=answer_payload)
        )
        self.assertEqual(status, 201)
        self.assertEqual(len(ans_resp["blocks"]), 2)
        self.assertEqual(ans_resp["blocks"][1]["block_type"], "image")
        self.assertEqual(ans_resp["blocks"][1]["media_id"], media_id)
        self.assertEqual(ans_resp["blocks"][1]["metadata"]["caption"], "Accreditation stages")

        # 4. Fetch answer
        status, get_ans, _ = asyncio.run(
            invoke_asgi("GET", f"/flows/{flow_id}/nodes/{node_id}/answer?language=en")
        )
        self.assertEqual(status, 200)
        self.assertEqual(get_ans["blocks"][1]["media_id"], media_id)


if __name__ == "__main__":
    unittest.main()
