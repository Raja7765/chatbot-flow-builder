"""
Verification script for Dynamic Node Answer & Media integration with PostgreSQL.
Tests:
1. Media uploads (Image, PDF, Video).
2. Answer creation with 6 blocks (Heading, Description, Bullet list, Image, PDF, Video) for 'hospitals_eligibility'.
3. Answer retrieval and position ordering verification.
4. Answer update via PUT and parity verification.
5. Fallback verification on node without answer.
6. Media streaming link validation.
"""

import asyncio
import json
import os
import sys
import uuid

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(__file__)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.database import SessionLocal
from app.models import Flow, NodeAnswer, AnswerBlock, MediaAsset


def build_multipart_payload(
    fields: dict = None,
    filename: str = "test.png",
    content: bytes = b"",
    content_type: str = "image/png",
) -> tuple:
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
        json_data = json.loads(resp_body.decode("utf-8"))
    except Exception:
        json_data = None

    return status_code, json_data, resp_headers, resp_body


async def main():
    print("=" * 65)
    print("PHASE 2 - DYNAMIC NODE ANSWER & MEDIA INTEGRATION VERIFICATION")
    print("=" * 65)

    db = SessionLocal()
    try:
        # 1. Locate NABH QMitra Flow
        nabh_flow = db.query(Flow).filter(Flow.name.ilike("%NABH%")).first()
        if not nabh_flow:
            nabh_flow = db.query(Flow).first()
        assert nabh_flow is not None, "No flow found in database!"
        flow_id = str(nabh_flow.id)
        print(f"Target Flow ID: {flow_id} ('{nabh_flow.name}')")

        nodes = nabh_flow.flow_data.get("nodes", [])
        node_ids = [n.get("id") for n in nodes]
        target_node = "hospitals_eligibility" if "hospitals_eligibility" in node_ids else node_ids[0]
        print(f"Target Node ID: {target_node}")

        # 2. Upload Test Media Files
        print("\n--- 1. Uploading Test Media Files ---")
        
        # Test Image
        png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        body, hdrs = build_multipart_payload(
            fields={"description": "NABH Hospital Accreditation Scheme Banner"},
            filename="nabh_hospital_banner.png",
            content=png_bytes,
            content_type="image/png"
        )
        status, data, _, _ = await invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=hdrs)
        assert status == 201, f"Image upload failed: {status}, {data}"
        img_id = data["id"]
        print(f"Uploaded Image -> media_id: {img_id}, filename: {data['file_name']}")

        # Test PDF
        pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000108 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n167\n%%EOF"
        body, hdrs = build_multipart_payload(
            fields={"description": "NABH Hospital Standards 5th Edition"},
            filename="nabh_standards_5th_ed.pdf",
            content=pdf_bytes,
            content_type="application/pdf"
        )
        status, data, _, _ = await invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=hdrs)
        assert status == 201, f"PDF upload failed: {status}, {data}"
        pdf_id = data["id"]
        print(f"Uploaded PDF   -> media_id: {pdf_id}, filename: {data['file_name']}")

        # Test Video
        vid_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42\x00\x00\x00\x08free"
        body, hdrs = build_multipart_payload(
            fields={"description": "NABH Patient Safety Video Guide"},
            filename="nabh_guide.mp4",
            content=vid_bytes,
            content_type="video/mp4"
        )
        status, data, _, _ = await invoke_asgi("POST", "/media/upload", raw_body=body, custom_headers=hdrs)
        assert status == 201, f"Video upload failed: {status}, {data}"
        vid_id = data["id"]
        print(f"Uploaded Video -> media_id: {vid_id}, filename: {data['file_name']}")

        # 3. Create 6-Block Answer for Target Node
        print(f"\n--- 2. Creating 6-Block Answer for Node '{target_node}' ---")
        answer_payload = {
            "language": "en",
            "blocks": [
                {
                    "block_type": "text",
                    "position": 1,
                    "content": "# Hospital Accreditation Program Eligibility"
                },
                {
                    "block_type": "text",
                    "position": 2,
                    "content": "The National Accreditation Board for Hospitals & Healthcare Providers (NABH) offers comprehensive accreditation for healthcare institutions across India."
                },
                {
                    "block_type": "text",
                    "position": 3,
                    "content": "### Key Eligibility Criteria:\n* Minimum of 50 inpatient operational beds\n* Full statutory and regulatory compliances\n* Operational for at least 6 months prior to application\n* Documented quality manual and SOPs adhering to 5th Edition standards"
                },
                {
                    "block_type": "image",
                    "position": 4,
                    "media_id": img_id,
                    "metadata": {
                        "title": "NABH Hospital Accreditation Overview Infographic",
                        "caption": "Figure 1: NABH Quality Assessment Framework"
                    }
                },
                {
                    "block_type": "pdf",
                    "position": 5,
                    "media_id": pdf_id,
                    "metadata": {
                        "title": "NABH Accreditation Standards for Hospitals (5th Edition)",
                        "file_size": len(pdf_bytes)
                    }
                },
                {
                    "block_type": "video",
                    "position": 6,
                    "media_id": vid_id,
                    "metadata": {
                        "caption": "Video Guide: Patient Safety and Healthcare Excellence Standards"
                    }
                }
            ]
        }

        # Clear existing answer if present
        await invoke_asgi("DELETE", f"/flows/{flow_id}/nodes/{target_node}/answer?language=en")

        # Create
        status, data, _, _ = await invoke_asgi("POST", f"/flows/{flow_id}/nodes/{target_node}/answer", body=answer_payload)
        assert status == 201, f"Create answer failed: {status}, {data}"
        print(f"Created Node Answer ID: {data['id']}")
        assert len(data["blocks"]) == 6, f"Expected 6 blocks, got {len(data['blocks'])}"
        print(f"Successfully created {len(data['blocks'])} blocks.")

        # 4. Verify GET Endpoint & Ascending Position Ordering
        print("\n--- 3. Verifying GET Endpoint & Ascending Position Order ---")
        status, fetched_answer, _, _ = await invoke_asgi("GET", f"/flows/{flow_id}/nodes/{target_node}/answer?language=en")
        assert status == 200, f"GET answer failed: {status}, {fetched_answer}"
        positions = [b["position"] for b in fetched_answer["blocks"]]
        types = [b["block_type"] for b in fetched_answer["blocks"]]
        print(f"Ascending Positions: {positions}")
        print(f"Block Types Order  : {types}")
        assert positions == [1, 2, 3, 4, 5, 6], f"Positions out of order: {positions}"
        assert types == ["text", "text", "text", "image", "pdf", "video"], f"Types mismatch: {types}"
        print("Verified: Blocks strictly ordered by ascending position (1 -> 6).")

        # 5. Verify Media Stream Links Integrity
        print("\n--- 4. Verifying Media Retrieval & Streaming ---")
        for m_id, expected_type in [(img_id, "image/png"), (pdf_id, "application/pdf"), (vid_id, "video/mp4")]:
            m_status, _, m_headers, m_body = await invoke_asgi("GET", f"/media/{m_id}")
            assert m_status == 200, f"Media GET {m_id} failed: status {m_status}"
            assert m_headers.get("content-type") == expected_type, f"Content-type mismatch: {m_headers.get('content-type')} != {expected_type}"
            print(f"Media {m_id[:8]}... : status={m_status}, type={m_headers.get('content-type')}, size={len(m_body)} bytes")

        # 6. Test 2: Update content through API (PUT)
        print("\n--- 5. Test 2: Updating Answer Content via PUT ---")
        updated_payload = {
            "language": "en",
            "blocks": [
                {
                    "block_type": "text",
                    "position": 1,
                    "content": "# Updated: NABH Hospital Accreditation Guidelines 2026"
                },
                {
                    "block_type": "text",
                    "position": 2,
                    "content": "This revised edition includes updated protocols for digital healthcare and infection control."
                },
                {
                    "block_type": "image",
                    "position": 3,
                    "media_id": img_id,
                    "metadata": {
                        "caption": "Updated Figure 1: 2026 Assessment Workflow"
                    }
                }
            ]
        }
        status, updated_data, _, _ = await invoke_asgi("PUT", f"/flows/{flow_id}/nodes/{target_node}/answer", body=updated_payload)
        assert status == 200, f"PUT failed: {status}, {updated_data}"
        assert len(updated_data["blocks"]) == 3, f"Expected 3 blocks, got {len(updated_data['blocks'])}"
        print(f"PUT succeeded. New block count: {len(updated_data['blocks'])}")

        status, get_after_put, _, _ = await invoke_asgi("GET", f"/flows/{flow_id}/nodes/{target_node}/answer?language=en")
        assert status == 200
        assert get_after_put["blocks"][0]["content"] == "# Updated: NABH Hospital Accreditation Guidelines 2026"
        print("Verified: Immediate reflection of updated content upon refetch.")

        # Re-apply full 6 blocks so it is active in the preview
        await invoke_asgi("PUT", f"/flows/{flow_id}/nodes/{target_node}/answer", body=answer_payload)
        print("Restored full 6-block answer in PostgreSQL for frontend preview.")

        # 7. Test 3: Fallback Verification on node without answer
        print("\n--- 6. Test 3: Fallback Verification on Node Without DB Answer ---")
        fallback_node = "accreditation_menu" if "accreditation_menu" in node_ids else "other_node"
        status, fallback_res, _, _ = await invoke_asgi("GET", f"/flows/{flow_id}/nodes/{fallback_node}/answer?language=en")
        assert status == 404, f"Expected 404, got {status}"
        print(f"Node '{fallback_node}' returns HTTP 404 as expected.")
        print("Frontend client converts 404 to null and displays existing RAG / flow_data seamlessly.")

        print("\n" + "=" * 65)
        print("ALL VERIFICATION CHECKS PASSED: 100% SUCCESS")
        print("=" * 65)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
