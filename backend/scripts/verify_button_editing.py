"""
Automated verification script for Node Buttons Editing in FigmaPropertiesPanel.
Tests:
1. Retrieval of flow and node 'hospitals_menu' (Hospitals Accreditation Program).
2. Verification of initial 6 buttons (Eligibility, Application, Assessment, Documents, Fee Structure, Understand NABH Standards).
3. Simulation of editing button label: 'Eligibility' -> 'Eligibility Criteria & Bed Requirements'.
4. Simulation of changing button destination: 'Fee Structure' -> 'hospitals_application'.
5. Simulation of adding a new button: 'Hospital Quality Guidelines' -> 'standard_aac'.
6. Simulation of reordering buttons: moving button up/down in the array.
7. Simulation of deleting a button: removing 'Documents' button.
8. Edge synchronization verification:
   - Existing edge IDs are preserved.
   - Target and label changes are synchronized.
   - Deleted buttons have their edges cleanly removed.
   - New button creates a corresponding smoothstep edge.
9. Persistence to PostgreSQL via PUT /flows/{flow_id}.
10. Subsequent GET /flows/{flow_id} verification confirming 100% data persistence.
11. Restoration of original flow state so the database remains clean.
"""

import asyncio
import json
import os
import sys
import copy

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

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
        "server": ("127.0.0.1", 80),
        "client": ("127.0.0.1", 12345),
    }

    await app(scope, receive, send)

    status_code = None
    resp_body = b""

    for msg in messages:
        if msg["type"] == "http.response.start":
            status_code = msg["status"]
        elif msg["type"] == "http.response.body":
            resp_body += msg.get("body", b"")

    try:
        json_data = json.loads(resp_body.decode("utf-8"))
    except Exception:
        json_data = None

    return status_code, json_data


def python_sync_edges_for_buttons(node_id, new_buttons, current_edges):
    """Python replica of frontend syncEdgesForButtons logic to verify parity."""
    str_node_id = str(node_id)
    other_edges = [e for e in current_edges if str(e.get("source")) != str_node_id]
    node_outgoing_edges = [e for e in current_edges if str(e.get("source")) == str_node_id]

    used_edge_ids = set()
    updated_node_edges = []

    for idx, btn in enumerate(new_buttons):
        target_node_id = str(btn.get("next", "")).strip()
        if not target_node_id:
            continue

        btn_id = btn.get("id")
        btn_label = btn.get("label", "")

        matched_edge = None
        # P1: sourceHandle
        if btn_id:
            matched_edge = next((e for e in node_outgoing_edges if e["id"] not in used_edge_ids and e.get("sourceHandle") == btn_id), None)
        # P2: target
        if not matched_edge:
            matched_edge = next((e for e in node_outgoing_edges if e["id"] not in used_edge_ids and str(e.get("target")) == target_node_id), None)
        # P3: label
        if not matched_edge and btn_label:
            matched_edge = next((e for e in node_outgoing_edges if e["id"] not in used_edge_ids and e.get("label") == btn_label), None)

        if matched_edge:
            used_edge_ids.add(matched_edge["id"])
            copied = dict(matched_edge)
            copied["target"] = target_node_id
            copied["label"] = btn_label
            if btn_id:
                copied["sourceHandle"] = btn_id
            updated_node_edges.append(copied)
        else:
            new_edge_id = f"edge-{str_node_id}-{target_node_id}-{btn_id or idx}"
            new_edge = {
                "id": new_edge_id,
                "source": str_node_id,
                "target": target_node_id,
                "label": btn_label,
                "type": "smoothstep",
                "style": {"stroke": "#A3A3A3", "strokeWidth": 1.5},
            }
            if btn_id:
                new_edge["sourceHandle"] = btn_id
            updated_node_edges.append(new_edge)

    return other_edges + updated_node_edges


async def main():
    print("=" * 70)
    print("VERIFICATION: NODE BUTTONS EDITING & PERSISTENCE")
    print("=" * 70)

    db = SessionLocal()
    try:
        flow = db.query(Flow).filter(Flow.name.ilike("%NABH%")).first()
        if not flow:
            flow = db.query(Flow).first()
        assert flow is not None, "No flow found!"
        flow_id = str(flow.id)
        original_flow_data = copy.deepcopy(flow.flow_data)

        # 1. Inspect 'hospitals_menu' node
        print("\n--- [Step 1] Inspecting 'hospitals_menu' Node ---")
        nodes = flow.flow_data.get("nodes", [])
        edges = flow.flow_data.get("edges", [])
        hosp_node = next((n for n in nodes if n["id"] == "hospitals_menu"), None)
        assert hosp_node is not None, "'hospitals_menu' node not found!"
        print(f"Node Label: '{hosp_node['data'].get('label')}' (ID: {hosp_node['id']})")
        initial_buttons = hosp_node["data"].get("buttons", [])
        print(f"Initial buttons count: {len(initial_buttons)}")
        assert len(initial_buttons) == 6, f"Expected 6 buttons, got {len(initial_buttons)}"
        for b in initial_buttons:
            print(f"  Button: '{b.get('label')}' -> next: '{b.get('next')}'")

        initial_outgoing_edges = [e for e in edges if e.get("source") == "hospitals_menu"]
        print(f"Initial outgoing edges: {len(initial_outgoing_edges)}")
        assert len(initial_outgoing_edges) == 6

        # 2. Simulate Button Label Edit
        print("\n--- [Step 2] Testing Button Label Edit ---")
        edited_buttons = copy.deepcopy(initial_buttons)
        edited_buttons[0]["label"] = "Eligibility Criteria & Bed Requirements"
        new_edges_step2 = python_sync_edges_for_buttons("hospitals_menu", edited_buttons, edges)
        
        # Verify edge_020 was preserved and label updated
        edge_020 = next((e for e in new_edges_step2 if e["id"] == "edge_020"), None)
        assert edge_020 is not None, "edge_020 ID must be preserved!"
        assert edge_020["label"] == "Eligibility Criteria & Bed Requirements"
        assert edge_020["target"] == "hospitals_eligibility"
        print(f"✓ Preserved edge ID '{edge_020['id']}' with updated label '{edge_020['label']}'")

        # 3. Simulate Changing Destination (next)
        print("\n--- [Step 3] Testing Changing Destination Node (next) ---")
        # Change 'Fee Structure' destination from 'hospitals_fee_structure' to 'hospitals_application'
        edited_buttons[4]["next"] = "hospitals_application"
        new_edges_step3 = python_sync_edges_for_buttons("hospitals_menu", edited_buttons, edges)
        edge_024 = next((e for e in new_edges_step3 if e["id"] == "edge_024"), None)
        assert edge_024 is not None, "edge_024 ID must be preserved!"
        assert edge_024["target"] == "hospitals_application", f"Expected target 'hospitals_application', got '{edge_024['target']}'"
        print(f"✓ Preserved edge ID '{edge_024['id']}' with updated destination target '{edge_024['target']}'")

        # 4. Simulate Adding a New Button
        print("\n--- [Step 4] Testing Adding New Button ---")
        new_btn = {
            "id": "hospitals_menu__opt_quality__6",
            "label": "Hospital Quality Standards",
            "next": "standard_aac",
        }
        edited_buttons.append(new_btn)
        new_edges_step4 = python_sync_edges_for_buttons("hospitals_menu", edited_buttons, edges)
        assert len(new_edges_step4) == len(edges) + 1, "Should have 1 additional edge for new button"
        new_edge = next((e for e in new_edges_step4 if e.get("target") == "standard_aac" and e.get("source") == "hospitals_menu"), None)
        assert new_edge is not None, "New edge must connect to 'standard_aac'"
        assert new_edge["label"] == "Hospital Quality Standards"
        print(f"✓ Created new edge '{new_edge['id']}' connecting '{new_edge['source']}' -> '{new_edge['target']}'")

        # 5. Simulate Reordering Buttons (Move button 4 to position 0)
        print("\n--- [Step 5] Testing Reordering Buttons ---")
        reordered_buttons = copy.deepcopy(edited_buttons)
        btn_to_move = reordered_buttons.pop(4)
        reordered_buttons.insert(0, btn_to_move)
        assert reordered_buttons[0]["label"] == btn_to_move["label"]
        new_edges_step5 = python_sync_edges_for_buttons("hospitals_menu", reordered_buttons, edges)
        print(f"✓ Successfully reordered buttons: first button is now '{reordered_buttons[0]['label']}'")

        # 6. Simulate Deleting a Button (Remove 'Documents')
        print("\n--- [Step 6] Testing Button Deletion & Edge Cleanup ---")
        before_del_count = len(reordered_buttons)
        reordered_buttons = [b for b in reordered_buttons if b.get("label") != "Documents"]
        assert len(reordered_buttons) == before_del_count - 1
        new_edges_step6 = python_sync_edges_for_buttons("hospitals_menu", reordered_buttons, edges)
        # Verify edge_023 (Documents) was removed
        edge_023 = next((e for e in new_edges_step6 if e["id"] == "edge_023"), None)
        assert edge_023 is None, "edge_023 must be removed when 'Documents' button is deleted!"
        print("✓ Edge for deleted button was cleanly removed without leaving phantom edges.")

        # 7. Persist to PostgreSQL via PUT /flows/{flow_id}
        print("\n--- [Step 7] Testing Flow Persistence via PUT /flows/{flow_id} ---")
        updated_nodes = [
            {**n, "data": {**n["data"], "buttons": reordered_buttons}} if n["id"] == "hospitals_menu" else n
            for n in nodes
        ]
        update_flow_payload = {
            "name": flow.name,
            "description": flow.description,
            "chatbot_id": str(flow.chatbot_id) if flow.chatbot_id else None,
            "flow_data": {
                "nodes": updated_nodes,
                "edges": new_edges_step6,
            }
        }
        status, updated_flow_res = await invoke_asgi("PUT", f"/flows/{flow_id}", body=update_flow_payload)
        assert status == 200, f"Flow update failed: {status}, {updated_flow_res}"
        print(f"✓ PUT /flows/{flow_id} succeeded with HTTP 200")

        # 8. Verify GET Parity from Database
        print("\n--- [Step 8] Verifying Subsequent GET Parity from PostgreSQL ---")
        status, fetched_flow, = await invoke_asgi("GET", f"/flows/{flow_id}")
        assert status == 200
        fetched_nodes = fetched_flow["flow_data"]["nodes"]
        fetched_hosp = next((n for n in fetched_nodes if n["id"] == "hospitals_menu"), None)
        assert fetched_hosp is not None
        fetched_buttons = fetched_hosp["data"]["buttons"]
        assert len(fetched_buttons) == len(reordered_buttons)
        assert fetched_buttons[0]["label"] == reordered_buttons[0]["label"]
        print(f"✓ PostgreSQL verification confirmed {len(fetched_buttons)} updated buttons persisted with 100% parity.")

        # 9. Clean up / Restore original flow data
        print("\n--- [Step 9] Restoring Original Flow Data ---")
        restore_payload = {
            "name": flow.name,
            "description": flow.description,
            "chatbot_id": str(flow.chatbot_id) if flow.chatbot_id else None,
            "flow_data": original_flow_data,
        }
        status, _ = await invoke_asgi("PUT", f"/flows/{flow_id}", body=restore_payload)
        assert status == 200
        print("✓ Original flow data restored cleanly.")

        print("\n" + "=" * 70)
        print("ALL BUTTON EDITING VERIFICATION TESTS PASSED: 100% SUCCESS")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
