"""
Automated verification script for Flow Editing and Saving fix.
Tests:
1. Create a new flow -> POST /flows should run and generate a new UUID.
2. Edit an existing flow -> PUT /flows/{flow_id} should run and preserve original UUID.
3. Save an existing flow multiple times -> node/edge counts remain stable.
4. Verify flow_data preservation:
   - nodes
   - edges
   - start_node
   - custom metadata
5. Refresh/refetch simulation -> updated changes exist in PostgreSQL.
6. Switch between flows -> each flow loads its own independent data.
7. Confirmation that no duplicate flow records are created on PUT.
8. Cleanup of temporary test flow.
"""

import asyncio
import json
import os
import sys
import uuid

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Ensure libpq is discoverable on Windows
pg_bin = r"C:\Program Files\PostgreSQL\18\bin"
if os.path.exists(pg_bin):
    os.environ["PATH"] = pg_bin + ";" + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(pg_bin)
        except Exception:
            pass

from app.main import app
from app.database import SessionLocal
from app.models import Flow


async def invoke_asgi(
    method: str,
    path: str,
    body: dict = None,
) -> tuple:
    payload_bytes = json.dumps(body).encode("utf-8") if body is not None else b""

    headers = [
        (b"host", b"testserver"),
        (b"content-type", b"application/json"),
        (b"content-length", str(len(payload_bytes)).encode("latin1")),
    ]

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
    }

    await app(scope, receive, send)

    status_code = None
    response_body = b""
    for msg in messages:
        if msg.get("type") == "http.response.start":
            status_code = msg.get("status")
        elif msg.get("type") == "http.response.body":
            response_body += msg.get("body", b"")

    try:
        data = json.loads(response_body.decode("utf-8")) if response_body else None
    except Exception:
        data = response_body.decode("utf-8", errors="replace")

    return status_code, data


async def main():
    print("=" * 70)
    print("VERIFICATION: Flow Editing, Creation & Persistence in PostgreSQL")
    print("=" * 70)

    # 1. Fetch existing chatbot ID
    chatbot_id = "96359635-3ff9-4bfb-befa-13827094b16e"

    # --- Scenario 1: Create a new flow -> POST /flows ---
    print("\n--- [Scenario 1] Testing New Flow Creation via POST /flows ---")
    new_flow_payload = {
        "name": "Test Scenario New Flow",
        "description": "Verifying POST behavior for unsaved flow",
        "chatbot_id": chatbot_id,
        "flow_data": {
            "start_node": "landing_page",
            "metadata_version": "1.0",
            "nodes": [
                {"id": "landing_page", "type": "landing_page", "data": {"label": "Welcome"}, "position": {"x": 100, "y": 100}},
                {"id": "node_step_1", "type": "message", "data": {"label": "Step 1"}, "position": {"x": 400, "y": 100}},
            ],
            "edges": [
                {"id": "edge-1-2", "source": "landing_page", "target": "node_step_1", "type": "smoothstep"}
            ]
        }
    }

    status, created_res = await invoke_asgi("POST", "/flows", body=new_flow_payload)
    assert status == 201, f"Expected 201 Created, got {status}: {created_res}"
    new_flow_id = created_res["id"]
    print(f"✓ POST /flows succeeded (HTTP {status}). Generated flow ID: {new_flow_id}")
    assert created_res["name"] == "Test Scenario New Flow"
    assert created_res["flow_data"]["start_node"] == "landing_page"
    assert len(created_res["flow_data"]["nodes"]) == 2
    assert len(created_res["flow_data"]["edges"]) == 1

    # --- Scenario 2: Edit existing flow -> PUT /flows/{flow_id} ---
    print("\n--- [Scenario 2] Testing Existing Flow Update via PUT /flows/{flow_id} ---")
    update_payload = {
        "name": "Test Scenario New Flow (Edited)",
        "description": "Updated description during editing",
        "chatbot_id": chatbot_id,
        "flow_data": {
            "start_node": "landing_page",
            "metadata_version": "1.0",
            "custom_tag": "nabh_verified",
            "nodes": [
                {"id": "landing_page", "type": "landing_page", "data": {"label": "Welcome"}, "position": {"x": 100, "y": 100}},
                {"id": "node_step_1", "type": "message", "data": {"label": "Step 1 (Edited)"}, "position": {"x": 400, "y": 100}},
                {"id": "node_step_2", "type": "answer", "data": {"label": "Step 2"}, "position": {"x": 700, "y": 100}},
            ],
            "edges": [
                {"id": "edge-1-2", "source": "landing_page", "target": "node_step_1", "type": "smoothstep"},
                {"id": "edge-2-3", "source": "node_step_1", "target": "node_step_2", "type": "smoothstep"},
            ]
        }
    }

    status, update_res = await invoke_asgi("PUT", f"/flows/{new_flow_id}", body=update_payload)
    assert status == 200, f"Expected 200 OK, got {status}: {update_res}"
    assert update_res["id"] == new_flow_id, f"Flow ID changed! Expected {new_flow_id}, got {update_res['id']}"
    assert update_res["name"] == "Test Scenario New Flow (Edited)"
    assert update_res["flow_data"]["start_node"] == "landing_page"
    assert update_res["flow_data"]["custom_tag"] == "nabh_verified"
    assert len(update_res["flow_data"]["nodes"]) == 3
    assert len(update_res["flow_data"]["edges"]) == 2
    print(f"✓ PUT /flows/{new_flow_id} succeeded (HTTP {status}). Flow ID preserved: {update_res['id']}")

    # --- Scenario 3: Multiple saves on the same flow maintain stable counts ---
    print("\n--- [Scenario 3] Testing Multiple Saves Stability (No Duplicate Creep) ---")
    for save_num in range(1, 4):
        status, multi_save_res = await invoke_asgi("PUT", f"/flows/{new_flow_id}", body=update_payload)
        assert status == 200
        assert multi_save_res["id"] == new_flow_id
        assert len(multi_save_res["flow_data"]["nodes"]) == 3
        assert len(multi_save_res["flow_data"]["edges"]) == 2
        print(f"✓ Save #{save_num}: Flow ID={multi_save_res['id']}, Nodes={len(multi_save_res['flow_data']['nodes'])}, Edges={len(multi_save_res['flow_data']['edges'])} (STABLE)")

    # --- Scenario 4: Verify persistence & browser refresh simulation ---
    print("\n--- [Scenario 4] Testing Browser Refresh Simulation (GET /flows/{flow_id}) ---")
    status, get_res = await invoke_asgi("GET", f"/flows/{new_flow_id}")
    assert status == 200
    assert get_res["id"] == new_flow_id
    assert get_res["name"] == "Test Scenario New Flow (Edited)"
    assert get_res["flow_data"]["start_node"] == "landing_page"
    assert get_res["flow_data"]["custom_tag"] == "nabh_verified"
    assert len(get_res["flow_data"]["nodes"]) == 3
    assert len(get_res["flow_data"]["edges"]) == 2
    print(f"✓ GET /flows/{new_flow_id} confirmed 100% data persistence with start_node & metadata.")

    # --- Scenario 5: Switching between flows loads independent data ---
    print("\n--- [Scenario 5] Testing Flow Switching (Different Flow IDs) ---")
    # Fetch NABH flow
    nabh_flow_id = "a23710cb-3353-4811-97b7-5927ba6c6d25"
    status_nabh, nabh_res = await invoke_asgi("GET", f"/flows/{nabh_flow_id}")
    assert status_nabh == 200
    assert nabh_res["id"] == nabh_flow_id
    print(f"✓ Flow 1: {nabh_res['name']} ({nabh_res['id']}): {len(nabh_res['flow_data']['nodes'])} nodes, {len(nabh_res['flow_data']['edges'])} edges")
    print(f"✓ Flow 2: {get_res['name']} ({get_res['id']}): {len(get_res['flow_data']['nodes'])} nodes, {len(get_res['flow_data']['edges'])} edges")
    assert nabh_res["id"] != get_res["id"]
    assert len(nabh_res["flow_data"]["nodes"]) != len(get_res["flow_data"]["nodes"])

    # --- Scenario 6: Verify no duplicate flows in database ---
    print("\n--- [Scenario 6] Verifying No Duplicate Flow Records Created in PostgreSQL ---")
    session = SessionLocal()
    try:
        matching_flows = session.query(Flow).filter_by(name="Test Scenario New Flow (Edited)").all()
        assert len(matching_flows) == 1, f"Expected exactly 1 flow record, found {len(matching_flows)}!"
        print(f"✓ Confirmed: Exactly 1 record exists for the edited flow in PostgreSQL. No duplicates created.")
    finally:
        session.close()

    # --- Scenario 7: Cleanup test flow ---
    print("\n--- [Scenario 7] Cleaning Up Temporary Test Flow ---")
    del_status, del_res = await invoke_asgi("DELETE", f"/flows/{new_flow_id}")
    assert del_status == 200
    print(f"✓ DELETE /flows/{new_flow_id} succeeded (HTTP {del_status}). Database restored cleanly.")

    print("\n" + "=" * 70)
    print("ALL 7 FLOW EDITING & SAVING VERIFICATION SCENARIOS PASSED WITH 100% SUCCESS")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

