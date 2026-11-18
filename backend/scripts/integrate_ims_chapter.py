"""
Script: integrate_ims_chapter.py
Implements the IMS chapter parent node and 7 subnodes with exact messages,
buttons, and connecting React Flow edges in the active flow.
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
CHAPTER_NODE_ID = "standard_ims"

IMS_PARENT_MESSAGE = (
    "The organisation ensures secure, accurate, and timely information management through MIS and HIS, "
    "supporting quality patient care. Confidentiality, integrity, periodic reviews, and proper medical "
    "record maintenance are prioritized."
)

IMS_SUBNODES_DATA = {
    1: {
        "message": "The organisation identifies and meets the information needs of patients, visitors, staff, management, and external agencies.",
        "subs": ["a", "b", "c", "d", "e", "f", "g", "h"],
    },
    2: {
        "message": "The organisation has processes in place for management and control of data and information.",
        "subs": ["a", "b", "c", "d", "e"],
    },
    3: {
        "message": "Patients cared for by the organisation have a complete and accurate medical record.",
        "subs": ["a", "b", "c", "d", "e", "f", "g"],
    },
    4: {
        "message": "The medical record reflects the continuity of care.",
        "subs": ["a", "b", "c", "d", "e", "f", "g", "h"],
    },
    5: {
        "message": "The organisation maintains confidentiality, integrity, and security of records, data, and information.",
        "subs": ["a", "b", "c", "d", "e", "f"],
    },
    6: {
        "message": "The organisation ensures availability of current and relevant documents, records, data, and information and provides for retention of the same.",
        "subs": ["a", "b", "c", "d"],
    },
    7: {
        "message": "The organisation carries out a review of medical records.",
        "subs": ["a", "b", "c", "d", "e", "f", "g"],
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

    # 1. Reuse and update standard_ims (Parent Node)
    ims_parent = node_map.get(CHAPTER_NODE_ID)
    if not ims_parent:
        raise RuntimeError(f"Parent node '{CHAPTER_NODE_ID}' not found in flow!")

    parent_buttons = []
    for i in range(1, 8):
        parent_buttons.append({
            "id": f"IMS.{i}",
            "next": f"ims_{i}",
            "label": f"IMS.{i}"
        })

    ims_parent["type"] = "rag"
    ims_parent["message"] = IMS_PARENT_MESSAGE
    ims_parent["mapping_status"] = "VERIFIED"
    if "data" not in ims_parent:
        ims_parent["data"] = {}
    ims_parent["data"]["id"] = CHAPTER_NODE_ID
    ims_parent["data"]["label"] = "IMS — Information Management System"
    ims_parent["data"]["message"] = IMS_PARENT_MESSAGE
    ims_parent["data"]["chapter"] = "IMS"
    ims_parent["data"]["program"] = "Hospitals Accreditation"
    ims_parent["data"]["topic"] = "standards"
    ims_parent["data"]["nodeType"] = "rag"
    ims_parent["data"]["mapping_status"] = "VERIFIED"
    ims_parent["data"]["buttons"] = parent_buttons

    # 2. Build 7 IMS subnodes and 14 connecting edges
    new_subnodes = []
    new_edges = []

    # Forward edges from standard_ims to ims_1..ims_7 (7 edges)
    for btn in parent_buttons:
        new_edges.append({
            "id": f"edge-standard_ims-{btn['next']}-{btn['id']}",
            "label": btn["label"],
            "source": CHAPTER_NODE_ID,
            "target": btn["next"],
            "sourceHandle": btn["id"]
        })

    # Subnodes ims_1 to ims_7
    base_y = 32000
    for i in range(1, 8):
        std_id = f"ims_{i}"
        info = IMS_SUBNODES_DATA[i]
        msg = info["message"]
        subs = info["subs"]
        pos_y = base_y + (i - 1) * 350

        # Subnode buttons: IMS.i.a, IMS.i.b, ...
        sub_buttons = []
        for s_idx, letter in enumerate(subs):
            sub_buttons.append({
                "id": f"IMS.{i}.{letter}",
                "next": "",
                "label": f"IMS.{i}.{letter}"
            })

        # Back to IMS Standards button
        back_btn_id = f"ims_{i}__back_standard_ims__{len(subs)}"
        sub_buttons.append({
            "id": back_btn_id,
            "next": CHAPTER_NODE_ID,
            "label": "Back to IMS Standards"
        })

        subnode = {
            "id": std_id,
            "type": "menu",
            "data": {
                "id": std_id,
                "label": f"IMS.{i}",
                "message": msg,
                "buttons": sub_buttons,
                "chapter": "IMS",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "nodeType": "menu",
                "layoutWidth": 290,
                "layoutHeight": 280 + max(0, (len(sub_buttons) - 5) * 20),
                "mapping_status": "VERIFIED"
            },
            "chapter": "IMS",
            "program": "Hospitals Accreditation",
            "topic": "standards",
            "message": msg,
            "position": {"x": 5715, "y": pos_y},
            "mapping_status": "VERIFIED"
        }
        new_subnodes.append(subnode)

        # Return edge from ims_i to standard_ims
        new_edges.append({
            "id": f"edge-{std_id}-standard_ims-{back_btn_id}",
            "label": "Back to IMS Standards",
            "source": std_id,
            "target": CHAPTER_NODE_ID,
            "sourceHandle": back_btn_id
        })

    # Clean existing ims_1..ims_7 nodes and edges if rerun (idempotent)
    clean_nodes = [n for n in nodes if not (n["id"].startswith("ims_") and n["id"] != CHAPTER_NODE_ID)]
    clean_edges = [
        e for e in edges
        if not (e.get("source", "").startswith("ims_") or e.get("target", "").startswith("ims_"))
        and not (e.get("source") == CHAPTER_NODE_ID and e.get("target", "").startswith("ims_"))
    ]

    flow_data["nodes"] = clean_nodes + new_subnodes
    flow_data["edges"] = clean_edges + new_edges

    return flow_data, new_subnodes, new_edges


async def main():
    print("=" * 80)
    print("IMPLEMENTING IMS CHAPTER NODES AND CONNECTIONS")
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

    # 1. Pre-Update Safety Backup
    print("\n[1/4] Creating Pre-Update Safety Backup...")
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file_path = os.path.join(
        backend_dir, "data", f"backup_flow_{TARGET_FLOW_ID}_before_ims_chapter_{timestamp_str}.json"
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

    # 2. Build updated flow
    print("\n[2/4] Constructing IMS parent node, 7 subnodes, and 14 connecting edges...")
    updated_flow_data, new_nodes, new_edges = build_updated_flow(flow_data)

    print(f"  ✓ Reused parent node: {CHAPTER_NODE_ID}")
    print(f"  ✓ Created {len(new_nodes)} new IMS subnodes (ims_1 to ims_7)")
    print(f"  ✓ Connected {len(new_edges)} new edges (7 forward + 7 return)")
    print(f"  ✓ Total nodes: {len(updated_flow_data['nodes'])} (Expected: {len(nodes_before) + 7})")
    print(f"  ✓ Total edges: {len(updated_flow_data['edges'])} (Expected: {len(edges_before) + 14})")

    # 3. Save flow via FastAPI REST API
    print("\n[3/4] Persisting updated flow via PUT /flows/{flow_id}...")
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
    print("  ✓ Flow successfully saved with HTTP 200.")

    # 4. Reload and Verify Persistence
    print("\n[4/4] Reloading flow via GET /flows/{flow_id} to verify persistence...")
    get_st, get_res = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}")
    assert get_st == 200, f"Failed GET: {get_st}"
    reloaded_nodes = get_res["flow_data"]["nodes"]
    reloaded_edges = get_res["flow_data"]["edges"]
    reloaded_map = {n["id"]: n for n in reloaded_nodes}

    # Verify standard_ims
    ims_parent = reloaded_map.get(CHAPTER_NODE_ID)
    assert ims_parent is not None, "standard_ims missing in reloaded flow"
    assert ims_parent["message"] == IMS_PARENT_MESSAGE, "Parent message mismatch"
    assert ims_parent["data"]["message"] == IMS_PARENT_MESSAGE, "Parent data.message mismatch"
    parent_btns = ims_parent.get("data", {}).get("buttons", [])
    assert len(parent_btns) == 7, f"Expected 7 buttons on standard_ims, got {len(parent_btns)}"
    for i in range(1, 8):
        btn = parent_btns[i - 1]
        assert btn["label"] == f"IMS.{i}", f"Button label mismatch: {btn['label']}"
        assert btn["id"] == f"IMS.{i}", f"Button id mismatch: {btn['id']}"
        assert btn["next"] == f"ims_{i}", f"Button next mismatch: {btn['next']}"
    print("  ✓ standard_ims parent node verified with exact message and 7 buttons (IMS.1 to IMS.7).")

    # Verify 7 subnodes
    total_sub_buttons = 0
    for i in range(1, 8):
        std_id = f"ims_{i}"
        node = reloaded_map.get(std_id)
        assert node is not None, f"Node {std_id} missing in reloaded flow"
        assert node["type"] == "menu"

        expected_msg = IMS_SUBNODES_DATA[i]["message"]
        assert node["message"] == expected_msg, f"Message mismatch for {std_id}"
        assert node["data"]["message"] == expected_msg, f"data.message mismatch for {std_id}"

        btns = node.get("data", {}).get("buttons", [])
        expected_subs = IMS_SUBNODES_DATA[i]["subs"]
        assert len(btns) == len(expected_subs) + 1, f"{std_id} button count mismatch"

        for s_idx, letter in enumerate(expected_subs):
            sub_btn = btns[s_idx]
            expected_label = f"IMS.{i}.{letter}"
            assert sub_btn["label"] == expected_label, f"Sub-button label mismatch: {sub_btn['label']}"
            assert sub_btn["id"] == expected_label, f"Sub-button id mismatch: {sub_btn['id']}"
            assert sub_btn["next"] == "", f"Sub-button next should be unlinked"
            total_sub_buttons += 1

        back_btn = btns[-1]
        assert back_btn["label"] == "Back to IMS Standards"
        assert back_btn["next"] == CHAPTER_NODE_ID

    print(f"  ✓ All 7 IMS subnodes verified with exact messages and {total_sub_buttons} lettered sub-buttons.")

    # Verify 14 edges
    reloaded_edge_ids = {e["id"] for e in reloaded_edges}
    for i in range(1, 8):
        fwd_edge_id = f"edge-standard_ims-ims_{i}-IMS.{i}"
        back_edge_id = f"edge-ims_{i}-standard_ims-ims_{i}__back_standard_ims__{len(IMS_SUBNODES_DATA[i]['subs'])}"
        assert fwd_edge_id in reloaded_edge_ids, f"Missing edge {fwd_edge_id}"
        assert back_edge_id in reloaded_edge_ids, f"Missing edge {back_edge_id}"
    print("  ✓ All 14 connecting edges verified (7 forward + 7 return).")

    # Verify duplicate checks
    node_ids = [n["id"] for n in reloaded_nodes]
    dup_nodes = [nid for nid in set(node_ids) if node_ids.count(nid) > 1]
    assert len(dup_nodes) == 0, f"Duplicate nodes found: {dup_nodes}"
    print("  ✓ Zero duplicate nodes verified across entire flow.")

    print("\n" + "=" * 80)
    print("SUCCESS: IMS CHAPTER NODES AND CONNECTIONS FULLY INTEGRATED & PERSISTED")
    print(f"  - Reused Nodes: 1 ({CHAPTER_NODE_ID})")
    print(f"  - Newly Created Nodes: 7 (ims_1 to ims_7)")
    print(f"  - Successfully Connected Edges: 14 (7 forward + 7 return)")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

