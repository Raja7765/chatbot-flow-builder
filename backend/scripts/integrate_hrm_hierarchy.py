"""
Script: integrate_hrm_hierarchy.py
Implements the complete HRM chapter button hierarchy in the existing NABH QMitra chatbot flow.
Target Flow ID: a23710cb-3353-4811-97b7-5927ba6c6d25
Target Chatbot ID: 96359635-3ff9-4bfb-befa-13827094b16e
"""

import asyncio
import copy
from datetime import datetime, timezone
import json
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

pg_bin = r"C:\Program Files\PostgreSQL\18\bin"
if os.path.exists(pg_bin):
    os.environ["PATH"] = pg_bin + ";" + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(pg_bin)
        except Exception:
            pass

from app.main import app
from app.database import SessionLocal, get_utc_now
from app.models import Flow, NodeAnswer, AnswerBlock, format_utc_iso

TARGET_CHATBOT_ID = "96359635-3ff9-4bfb-befa-13827094b16e"
TARGET_FLOW_ID = "a23710cb-3353-4811-97b7-5927ba6c6d25"
CHAPTER_NODE_ID = "standard_hrm"

HRM_STANDARDS_DATA = {
    1: {
        "statement": "The organisation has a documented system of human resource planning.",
        "subs": ["a", "b", "c", "d", "e", "f", "g"],
    },
    2: {
        "statement": "The organisation implements a defined process for staff recruitment.",
        "subs": ["a", "b", "c", "d"],
    },
    3: {
        "statement": "Staff are provided induction training at the time of joining the organisation.",
        "subs": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"],
    },
    4: {
        "statement": "There is an on-going programme for professional training and development of the staff.",
        "subs": ["a", "b", "c", "d", "e", "f"],
    },
    5: {
        "statement": "Staff are appropriately trained based on their specific job description.",
        "subs": ["a", "b", "c", "d", "e", "f"],
    },
    6: {
        "statement": "Staff are trained on safety and quality-related aspects.",
        "subs": ["a", "b", "c", "d", "e", "f", "g"],
    },
    7: {
        "statement": "An appraisal system for evaluating the performance of an employee exists as an integral part of the human resources management process.",
        "subs": ["a", "b", "c", "d", "e"],
    },
    8: {
        "statement": "Process for disciplinary and grievance handling is defined and implemented in the organisation.",
        "subs": ["a", "b", "c", "d", "e", "f"],
    },
    9: {
        "statement": "The organisation promotes staff well-being and addresses their health and safety needs.",
        "subs": ["a", "b", "c", "d"],
    },
    10: {
        "statement": "There is documented personal information for each staff member.",
        "subs": ["a", "b", "c", "d"],
    },
    11: {
        "statement": "There is a process for credentialing and privileging of medical professionals, permitted to provide patient care without supervision.",
        "subs": ["a", "b", "c", "d", "e", "f"],
    },
    12: {
        "statement": "There is a process for credentialing and privileging of nursing professionals, permitted to provide patient care without supervision.",
        "subs": ["a", "b", "c", "d", "e", "f"],
    },
    13: {
        "statement": "There is a process for credentialing and privileging of para-clinical professionals, permitted to provide patient care without supervision.",
        "subs": ["a", "b", "c", "d", "e"],
    },
}


async def invoke_asgi(method: str, path: str, payload: dict = None) -> tuple:
    payload_bytes = json.dumps(payload).encode("utf-8") if payload is not None else b""
    headers = [
        (b"host", b"testserver"),
        (b"accept", b"application/json"),
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
        if msg["type"] == "http.response.start":
            status_code = msg["status"]
        elif msg["type"] == "http.response.body":
            response_body += msg.get("body", b"")

    try:
        response_json = json.loads(response_body.decode("utf-8")) if response_body else None
    except Exception:
        response_json = response_body.decode("utf-8", errors="replace")

    return status_code, response_json


def build_updated_flow(flow_data: dict) -> tuple:
    nodes = copy.deepcopy(flow_data.get("nodes", []))
    edges = copy.deepcopy(flow_data.get("edges", []))

    node_map = {n["id"]: n for n in nodes}

    # 1. Update standard_hrm (HRM Parent Node)
    hrm_chapter = node_map.get(CHAPTER_NODE_ID)
    if not hrm_chapter:
        raise RuntimeError(f"Parent node '{CHAPTER_NODE_ID}' not found in flow!")

    hrm_main_buttons = []
    for i in range(1, 14):
        hrm_main_buttons.append({
            "id": f"standard_hrm__hrm_{i}__{i-1}",
            "next": f"hrm_{i}",
            "label": f"STANDARD: HRM.{i}"
        })

    hrm_chapter["type"] = "rag"
    hrm_chapter["message"] = "HRM — Human Resource Management (NABH 5th Edition Standards)"
    hrm_chapter["mapping_status"] = "VERIFIED"
    if "data" not in hrm_chapter:
        hrm_chapter["data"] = {}
    hrm_chapter["data"]["id"] = CHAPTER_NODE_ID
    hrm_chapter["data"]["label"] = "HRM — Human Resource Management"
    hrm_chapter["data"]["message"] = "HRM — Human Resource Management (NABH 5th Edition Standards)"
    hrm_chapter["data"]["chapter"] = "HRM"
    hrm_chapter["data"]["program"] = "Hospitals Accreditation"
    hrm_chapter["data"]["topic"] = "standards"
    hrm_chapter["data"]["nodeType"] = "rag"
    hrm_chapter["data"]["mapping_status"] = "VERIFIED"
    hrm_chapter["data"]["buttons"] = hrm_main_buttons

    # 2. Build 13 HRM sub-nodes and 26 edges
    new_nodes = []
    new_edges = []

    # Forward edges from standard_hrm to hrm_1..hrm_13
    for btn in hrm_main_buttons:
        new_edges.append({
            "id": f"edge-standard_hrm-{btn['next']}-{btn['id']}",
            "label": btn["label"],
            "source": CHAPTER_NODE_ID,
            "target": btn["next"],
            "sourceHandle": btn["id"]
        })

    # Sub-nodes hrm_1 to hrm_13
    std_base_y = 27000
    for i in range(1, 14):
        std_id = f"hrm_{i}"
        std_info = HRM_STANDARDS_DATA[i]
        statement = std_info["statement"]
        subs = std_info["subs"]
        pos_y = std_base_y + (i - 1) * 350

        # Sub-buttons on hrm_i
        std_buttons = []
        for s_idx, letter in enumerate(subs):
            btn_id = f"hrm_{i}__hrm_{i}_{letter}__{s_idx}"
            std_buttons.append({
                "id": btn_id,
                "next": "",
                "label": f"HRM.{i}.{letter}"
            })

        # Back to HRM Standards button
        btn_back_id = f"hrm_{i}__back_standard_hrm__{len(subs)}"
        std_buttons.append({
            "id": btn_back_id,
            "next": CHAPTER_NODE_ID,
            "label": "Back to HRM Standards"
        })

        node_message = f"HRM.{i} — {statement}"

        std_node = {
            "id": std_id,
            "type": "menu",
            "data": {
                "id": std_id,
                "label": f"STANDARD: HRM.{i}",
                "message": node_message,
                "buttons": std_buttons,
                "chapter": "HRM",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "nodeType": "menu",
                "layoutWidth": 290,
                "layoutHeight": 280 + max(0, (len(std_buttons) - 5) * 20),
                "mapping_status": "VERIFIED"
            },
            "chapter": "HRM",
            "program": "Hospitals Accreditation",
            "topic": "standards",
            "message": node_message,
            "position": {"x": 5715, "y": pos_y},
            "mapping_status": "VERIFIED"
        }
        new_nodes.append(std_node)

        # Back edge from hrm_i to standard_hrm
        new_edges.append({
            "id": f"edge-{std_id}-standard_hrm-{btn_back_id}",
            "label": "Back to HRM Standards",
            "source": std_id,
            "target": CHAPTER_NODE_ID,
            "sourceHandle": btn_back_id
        })

    # Clean out any previous hrm_1..hrm_13 nodes and edges if rerun (idempotent)
    clean_nodes = [n for n in nodes if not n["id"].startswith("hrm_")]
    clean_edges = [
        e for e in edges
        if not (e.get("source", "").startswith("hrm_") or e.get("target", "").startswith("hrm_"))
        and not (e.get("source") == CHAPTER_NODE_ID and e.get("target", "").startswith("hrm_"))
    ]

    flow_data["nodes"] = clean_nodes + new_nodes
    flow_data["edges"] = clean_edges + new_edges

    return flow_data, new_nodes, new_edges


async def main():
    print("=" * 80)
    print("INTEGRATING NABH HRM CHAPTER BUTTON HIERARCHY")
    print(f"Target Flow ID:    {TARGET_FLOW_ID}")
    print(f"Target Chatbot ID: {TARGET_CHATBOT_ID}")
    print("=" * 80)

    db = SessionLocal()
    target_flow = db.get(Flow, TARGET_FLOW_ID)
    if not target_flow:
        print(f"ERROR: Flow {TARGET_FLOW_ID} not found!")
        db.close()
        sys.exit(1)

    flow_data = target_flow.flow_data or {}
    nodes_before = flow_data.get("nodes", [])
    edges_before = flow_data.get("edges", [])
    print(f"Nodes before: {len(nodes_before)}")
    print(f"Edges before: {len(edges_before)}")

    # 1. Create Safety Backup
    print("\n[1/4] Creating Pre-Update Safety Backup...")
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file_path = os.path.join(
        backend_dir, "data", f"backup_flow_{TARGET_FLOW_ID}_before_hrm_hierarchy_{timestamp_str}.json"
    )
    all_answers = db.query(NodeAnswer).all()
    all_blocks = db.query(AnswerBlock).all()
    backup_payload = {
        "timestamp_utc": format_utc_iso(get_utc_now()),
        "flow": target_flow.to_dict(),
        "node_answers": [a.to_dict() for a in all_answers],
        "answer_blocks": [b.to_dict() for b in all_blocks],
    }
    with open(backup_file_path, "w", encoding="utf-8") as bf:
        json.dump(backup_payload, bf, indent=2, ensure_ascii=False)
    print(f"  ✓ Safety backup saved to: {backup_file_path}")
    db.close()

    # 2. Build updated flow hierarchy
    print("\n[2/4] Constructing HRM parent buttons, 13 sub-nodes, and 26 connecting edges...")
    updated_flow_data, new_nodes, new_edges = build_updated_flow(flow_data)

    print(f"  ✓ Added {len(new_nodes)} HRM sub-nodes (hrm_1 to hrm_13)")
    print(f"  ✓ Added {len(new_edges)} connecting edges (13 forward + 13 back)")
    print(f"  ✓ Total nodes now: {len(updated_flow_data['nodes'])} (Expected: {len(nodes_before) + 13})")
    print(f"  ✓ Total edges now: {len(updated_flow_data['edges'])} (Expected: {len(edges_before) + 26})")

    # 3. Save flow via FastAPI REST API
    print("\n[3/4] Persisting updated flow to PostgreSQL via PUT /flows/{flow_id}...")
    put_payload = {
        "name": target_flow.name,
        "description": target_flow.description,
        "chatbot_id": TARGET_CHATBOT_ID,
        "flow_data": updated_flow_data
    }
    st, res = await invoke_asgi("PUT", f"/flows/{TARGET_FLOW_ID}", put_payload)
    if st != 200:
        print(f"ERROR saving flow: {st} {res}")
        sys.exit(1)
    print("  ✓ Flow successfully saved to database with HTTP 200.")

    # 4. Reload and Verify Persistence
    print("\n[4/4] Reloading flow via GET /flows/{flow_id} to verify persistence...")
    get_st, get_res = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}")
    assert get_st == 200, f"Failed GET: {get_st}"
    reloaded_nodes = get_res["flow_data"]["nodes"]
    reloaded_edges = get_res["flow_data"]["edges"]
    reloaded_map = {n["id"]: n for n in reloaded_nodes}

    # Verify standard_hrm
    hrm_parent = reloaded_map.get(CHAPTER_NODE_ID)
    assert hrm_parent is not None, "standard_hrm missing in reloaded flow"
    parent_btns = hrm_parent.get("data", {}).get("buttons", [])
    assert len(parent_btns) == 13, f"Expected 13 buttons on standard_hrm, got {len(parent_btns)}"
    for i in range(1, 14):
        btn = parent_btns[i - 1]
        assert btn["label"] == f"STANDARD: HRM.{i}"
        assert btn["next"] == f"hrm_{i}"
    print("  ✓ standard_hrm has all 13 STANDARD: HRM.1 - HRM.13 buttons verified.")

    # Verify 13 sub-nodes
    total_sub_buttons = 0
    for i in range(1, 14):
        std_id = f"hrm_{i}"
        sub_node = reloaded_map.get(std_id)
        assert sub_node is not None, f"Node {std_id} missing in reloaded flow"
        assert sub_node["type"] == "menu"

        statement = HRM_STANDARDS_DATA[i]["statement"]
        expected_msg = f"HRM.{i} — {statement}"
        assert sub_node["message"] == expected_msg
        assert sub_node["data"]["message"] == expected_msg

        btns = sub_node.get("data", {}).get("buttons", [])
        expected_subs = HRM_STANDARDS_DATA[i]["subs"]
        expected_total_btns = len(expected_subs) + 1  # sub-buttons + Back button
        assert len(btns) == expected_total_btns, f"{std_id} expected {expected_total_btns} buttons, got {len(btns)}"

        # Check sub-buttons
        for s_idx, letter in enumerate(expected_subs):
            sub_btn = btns[s_idx]
            assert sub_btn["label"] == f"HRM.{i}.{letter}"
            assert sub_btn["id"] == f"hrm_{i}__hrm_{i}_{letter}__{s_idx}"
            total_sub_buttons += 1

        # Check back button
        back_btn = btns[-1]
        assert back_btn["label"] == "Back to HRM Standards"
        assert back_btn["next"] == CHAPTER_NODE_ID
        assert back_btn["id"] == f"hrm_{i}__back_standard_hrm__{len(expected_subs)}"

    print(f"  ✓ All 13 HRM sub-nodes verified with exact statements and {total_sub_buttons} lettered sub-buttons.")

    # Verify 26 connecting edges
    reloaded_edge_ids = {e["id"] for e in reloaded_edges}
    for i in range(1, 14):
        fwd_id = f"edge-standard_hrm-hrm_{i}-standard_hrm__hrm_{i}__{i-1}"
        back_id = f"edge-hrm_{i}-standard_hrm-hrm_{i}__back_standard_hrm__{len(HRM_STANDARDS_DATA[i]['subs'])}"
        assert fwd_id in reloaded_edge_ids, f"Missing edge {fwd_id}"
        assert back_id in reloaded_edge_ids, f"Missing edge {back_id}"
    print("  ✓ All 26 connecting edges verified (13 forward + 13 back).")

    # Verify duplicate checks
    node_ids = [n["id"] for n in reloaded_nodes]
    dup_nodes = [nid for nid in set(node_ids) if node_ids.count(nid) > 1]
    assert len(dup_nodes) == 0, f"Duplicate nodes found: {dup_nodes}"
    print("  ✓ Zero duplicate nodes verified.")

    print("\n" + "=" * 80)
    print("SUCCESS: HRM CHAPTER BUTTON HIERARCHY FULLY INTEGRATED & PERSISTED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

