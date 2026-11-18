"""
Script: apply_and_verify_aac_buttons.py
Applies 13 AAC Standard Buttons to the standard_aac node in flow 4dce6cd9-9ef4-4cb8-bba9-49e3736adde5
via the official PUT /flows/{flow_id} endpoint, and verifies all preservation requirements.
"""

import asyncio
import copy
import json
import os
import sys

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


TARGET_FLOW_ID = "4dce6cd9-9ef4-4cb8-bba9-49e3736adde5"
TARGET_CHATBOT_ID = "96359635-3ff9-4bfb-befa-13827094b16e"
TARGET_NODE_ID = "standard_aac"

NEW_BUTTONS = [
    {"id": "standard_aac__aac_1__0", "next": "aac_1", "label": "STANDARD: AAC.1"},
    {"id": "standard_aac__aac_2__1", "next": "aac_2", "label": "STANDARD: AAC.2"},
    {"id": "standard_aac__aac_3__2", "next": "aac_3", "label": "STANDARD: AAC.3"},
    {"id": "standard_aac__aac_4__3", "next": "aac_4", "label": "STANDARD: AAC.4"},
    {"id": "standard_aac__aac_5__4", "next": "aac_5", "label": "STANDARD: AAC.5"},
    {"id": "standard_aac__aac_6__5", "next": "aac_6", "label": "STANDARD: AAC.6"},
    {"id": "standard_aac__aac_7__6", "next": "aac_7", "label": "STANDARD: AAC.7"},
    {"id": "standard_aac__aac_8__7", "next": "aac_8", "label": "STANDARD: AAC.8"},
    {"id": "standard_aac__aac_9__8", "next": "aac_9", "label": "STANDARD: AAC.9"},
    {"id": "standard_aac__aac_10__9", "next": "aac_10", "label": "STANDARD: AAC.10"},
    {"id": "standard_aac__aac_11__10", "next": "aac_11", "label": "STANDARD: AAC.11"},
    {"id": "standard_aac__aac_12__11", "next": "aac_12", "label": "STANDARD: AAC.12"},
    {"id": "standard_aac__aac_13__12", "next": "aac_13", "label": "STANDARD: AAC.13"},
]


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
    print("STEP 1: PRE-INSPECTION OF EXISTING FLOW")
    print("=" * 70)

    # Initial flow count in DB
    session = SessionLocal()
    initial_db_flow_count = session.query(Flow).count()
    session.close()
    print(f"Total flows in PostgreSQL before update: {initial_db_flow_count}")

    # Fetch existing flow via GET /flows/{flow_id}
    status, existing_flow = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}")
    assert status == 200, f"Failed to fetch flow {TARGET_FLOW_ID}, got HTTP {status}: {existing_flow}"
    assert existing_flow["id"] == TARGET_FLOW_ID
    assert existing_flow["chatbot_id"] == TARGET_CHATBOT_ID

    original_flow_data = existing_flow["flow_data"]
    original_nodes = original_flow_data.get("nodes", [])
    original_edges = original_flow_data.get("edges", [])

    print(f"✓ Found target flow '{existing_flow['name']}' ({TARGET_FLOW_ID})")
    print(f"  Nodes count: {len(original_nodes)}")
    print(f"  Edges count: {len(original_edges)}")
    print(f"  Root flow_data keys: {list(original_flow_data.keys())}")

    # Locate standard_aac
    aac_node_index = -1
    for idx, n in enumerate(original_nodes):
        if n.get("id") == TARGET_NODE_ID:
            aac_node_index = idx
            break

    assert aac_node_index != -1, f"Node {TARGET_NODE_ID} not found in nodes!"
    original_aac_node = original_nodes[aac_node_index]
    print(f"✓ Found node '{TARGET_NODE_ID}' at index {aac_node_index}")
    print(f"  Type: {original_aac_node.get('type')}")
    print(f"  Label: {original_aac_node.get('data', {}).get('label')}")
    print(f"  Message: {original_aac_node.get('data', {}).get('message')}")
    print(f"  Existing buttons: {len(original_aac_node.get('data', {}).get('buttons', []))}")

    print("\n" + "=" * 70)
    print("STEP 2: PREPARE AND VALIDATE PAYLOAD")
    print("=" * 70)

    # Clone all 206 nodes and update ONLY standard_aac
    updated_nodes = copy.deepcopy(original_nodes)
    target_node = updated_nodes[aac_node_index]

    if "data" not in target_node or not isinstance(target_node["data"], dict):
        target_node["data"] = {}

    # Set buttons on data.buttons
    target_node["data"]["buttons"] = copy.deepcopy(NEW_BUTTONS)
    # Also mirror on node.buttons for legacy readers
    target_node["buttons"] = copy.deepcopy(NEW_BUTTONS)

    # Verify other 205 nodes are identical
    for idx in range(len(original_nodes)):
        if idx == aac_node_index:
            continue
        assert original_nodes[idx] == updated_nodes[idx], f"Node {idx} ({original_nodes[idx].get('id')}) was modified!"
    print(f"✓ Confirmed: All other 205 nodes remain 100% untouched.")

    # Prepare complete update payload
    updated_flow_data = copy.deepcopy(original_flow_data)
    updated_flow_data["nodes"] = updated_nodes
    updated_flow_data["edges"] = original_edges  # Edges unchanged

    update_payload = {
        "name": existing_flow["name"],
        "description": existing_flow.get("description"),
        "chatbot_id": existing_flow["chatbot_id"],
        "flow_data": updated_flow_data,
    }

    print(f"✓ Payload prepared:")
    print(f"  Name: {update_payload['name']}")
    print(f"  Chatbot ID: {update_payload['chatbot_id']}")
    print(f"  Total nodes in payload: {len(updated_flow_data['nodes'])}")
    print(f"  Total edges in payload: {len(updated_flow_data['edges'])}")
    print(f"  standard_aac buttons in payload: {len(target_node['data']['buttons'])}")

    print("\n" + "=" * 70)
    print("STEP 3: EXECUTE PUT /flows/{flow_id}")
    print("=" * 70)

    put_status, put_response = await invoke_asgi("PUT", f"/flows/{TARGET_FLOW_ID}", body=update_payload)
    assert put_status == 200, f"PUT failed with HTTP {put_status}: {put_response}"
    assert put_response["id"] == TARGET_FLOW_ID, f"Flow ID changed from {TARGET_FLOW_ID} to {put_response['id']}!"
    print(f"✓ PUT /flows/{TARGET_FLOW_ID} succeeded with HTTP 200 OK.")

    print("\n" + "=" * 70)
    print("STEP 4: VERIFY PERSISTENCE & DATA INTEGRITY")
    print("=" * 70)

    # 1. Refetch via GET /flows/{flow_id}
    get_status, verified_flow = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}")
    assert get_status == 200
    assert verified_flow["id"] == TARGET_FLOW_ID
    assert verified_flow["name"] == existing_flow["name"]
    assert verified_flow["chatbot_id"] == TARGET_CHATBOT_ID

    v_nodes = verified_flow["flow_data"].get("nodes", [])
    v_edges = verified_flow["flow_data"].get("edges", [])

    print(f"1. Flow ID preserved: {verified_flow['id']} == {TARGET_FLOW_ID}")
    print(f"2. Total nodes count: {len(v_nodes)} (expected {len(original_nodes)})")
    assert len(v_nodes) == len(original_nodes), f"Node count mismatch: {len(v_nodes)} vs {len(original_nodes)}"

    print(f"3. Total edges count: {len(v_edges)} (expected {len(original_edges)})")
    assert len(v_edges) == len(original_edges), f"Edge count mismatch: {len(v_edges)} vs {len(original_edges)}"

    # 2. Check standard_aac node in verified response
    v_aac = [n for n in v_nodes if n.get("id") == TARGET_NODE_ID][0]
    v_buttons = v_aac.get("data", {}).get("buttons", [])
    print(f"4. standard_aac buttons count: {len(v_buttons)} (expected 13)")
    assert len(v_buttons) == 13, f"Expected 13 buttons, found {len(v_buttons)}"

    for idx, expected_btn in enumerate(NEW_BUTTONS):
        actual_btn = v_buttons[idx]
        assert actual_btn["id"] == expected_btn["id"], f"Button {idx} ID mismatch: {actual_btn['id']} vs {expected_btn['id']}"
        assert actual_btn["next"] == expected_btn["next"], f"Button {idx} next mismatch: {actual_btn['next']} vs {expected_btn['next']}"
        assert actual_btn["label"] == expected_btn["label"], f"Button {idx} label mismatch: {actual_btn['label']} vs {expected_btn['label']}"
        print(f"   [{idx + 1}/13] id={actual_btn['id']} -> next={actual_btn['next']} (label='{actual_btn['label']}')")

    # 3. Check AAC overview text preserved
    print("5. Verifying AAC overview text preservation:")
    print(f"   Label: '{v_aac.get('data', {}).get('label')}'")
    print(f"   Message: '{v_aac.get('data', {}).get('message')}'")
    assert v_aac.get("data", {}).get("label") == original_aac_node.get("data", {}).get("label")
    assert v_aac.get("data", {}).get("message") == original_aac_node.get("data", {}).get("message")
    print("   ✓ AAC overview text 100% preserved.")

    # 4. Check that no duplicate flows were created in PostgreSQL
    session = SessionLocal()
    final_db_flow_count = session.query(Flow).count()
    matching_flows = session.query(Flow).filter_by(id=TARGET_FLOW_ID).all()
    session.close()

    print(f"6. Total flows in DB: {final_db_flow_count} (expected {initial_db_flow_count})")
    assert final_db_flow_count == initial_db_flow_count, f"Flow count changed from {initial_db_flow_count} to {final_db_flow_count}!"
    assert len(matching_flows) == 1, f"Expected 1 matching flow, found {len(matching_flows)}!"
    print("   ✓ Confirmed: Zero duplicate flow records created.")

    print("\n" + "=" * 70)
    print("ALL 13 AAC STANDARD BUTTONS APPLIED & VERIFIED WITH 100% SUCCESS")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

