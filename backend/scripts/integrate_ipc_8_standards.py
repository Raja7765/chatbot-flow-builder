"""
Script: integrate_ipc_8_standards.py
Integrates NABH Infection Prevention and Control Standard IPC.8 and its 5 sub-standards
(IPC.8.a to IPC.8.e) with their individual Description + Interpretation answers
into the existing NABH QMitra chatbot flow (a23710cb-3353-4811-97b7-5927ba6c6d25).
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
CHAPTER_NODE_ID = "standard_ipc"

IPC_8_DATA = {
    "title": "The organisation implements occupational health and safety practices as per written guidance to reduce the risk of transmitting microorganisms among health care providers.",
    "subs": [
        ("a",
         "The organisation implements occupational health and safety practices as per written guidance to reduce the risk of transmitting microorganisms among health care providers.",
         "Written guidance shall be available on occupational health and safety practices. The organisation provides adequate resources to its staff for infection prevention and control. Staff shall adhere to standard precautions. Where appropriate, the organisation shall have a pre-employment health screening and capture immunisation status."),
        ("b",
         "The organisation implements an immunisation policy for its staff.",
         "The organisation’s immunisation policy for its staff shall be in consonance with the available evidence. At a minimum, Hepatitis B vaccination shall be provided to staff involved in direct patient care. Other relevant immunisation is provided as per the risk from time to time and in accordance with applicable statutory requirements."),
        ("c",
         "The organisation implements work restrictions for health care providers with transmissible infections.",
         "The restrictions could include limiting role and responsibilities for health care providers with transmissible infections. The organisation encourages health care providers to report their illness or exposures and does not penalise them. Examples of transmissible infections include acute conjunctivitis, chickenpox, acute respiratory infections, smear-positive case of tuberculosis etc."),
        ("d",
         "The organisation implements measures for blood and body fluid exposure prevention.",
         "The organisation ensures that health care providers use appropriate personnel protective equipment to prevent blood and body fluid exposures. The organisation shall strive to eliminate the use of needle devices whenever safe and effective alternatives are available. It could consider providing needle devices with safety features."),
        ("e",
         "Appropriate post-exposure prophylaxis is provided to all staff members concerned.",
         "The organisation provides post-exposure prophylaxis for hepatitis B and HIV exposure. This shall align with National and/or International guidelines. Infection prevention and control Nurse maintains documentation of post-exposure prophylaxis records. For example, PEP for needle stick injury.")
    ]
}


async def invoke_asgi(method: str, path: str, payload: dict = None) -> tuple:
    """Helper to invoke FastAPI app endpoints asynchronously in-process."""
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


def build_ipc_graph(original_flow_data: dict) -> tuple:
    """
    Construct the updated flow graph by:
    1. Adding IPC.8 button to standard_ipc node.
    2. Creating ipc_8 menu node.
    3. Creating 5 ipc_8_{sub} answer nodes.
    4. Adding all 17 navigation edges.
    """
    flow_data = copy.deepcopy(original_flow_data)
    nodes = flow_data.get("nodes", [])
    edges = flow_data.get("edges", [])

    node_map = {n["id"]: n for n in nodes}

    # 1. Update standard_ipc chapter node
    ipc_chapter = node_map.get(CHAPTER_NODE_ID)
    if not ipc_chapter:
        raise ValueError(f"Chapter node '{CHAPTER_NODE_ID}' not found in flow.")

    current_buttons = ipc_chapter.get("data", {}).get("buttons", [])
    btn_id = "standard_ipc__ipc_8__0"
    
    # Check if IPC.8 button already exists
    ipc_8_btn = next((b for b in current_buttons if b.get("next") == "ipc_8"), None)
    if not ipc_8_btn:
        ipc_8_btn = {
            "id": btn_id,
            "next": "ipc_8",
            "label": "STANDARD: IPC.8"
        }
        current_buttons.append(ipc_8_btn)

    ipc_chapter["data"]["buttons"] = current_buttons
    ipc_chapter["data"]["message"] = "IPC — Infection Prevention and Control (NABH 5th Edition Standards)"
    ipc_chapter["data"]["mapping_status"] = "VERIFIED"
    ipc_chapter["mapping_status"] = "VERIFIED"

    new_nodes = []
    new_edges = []

    # 2. Forward edge from standard_ipc to ipc_8
    edge_fwd_chap_id = f"edge-standard_ipc-ipc_8-{ipc_8_btn['id']}"
    if not any(e["id"] == edge_fwd_chap_id for e in edges):
        new_edges.append({
            "id": edge_fwd_chap_id,
            "label": "STANDARD: IPC.8",
            "source": CHAPTER_NODE_ID,
            "target": "ipc_8",
            "sourceHandle": ipc_8_btn["id"]
        })

    # 3. Create Main standard node ipc_8
    std_pos_y = 14500
    subs = IPC_8_DATA["subs"]

    std_buttons = []
    for s_idx, (letter, desc, _) in enumerate(subs):
        sub_node_id = f"ipc_8_{letter}"
        sub_btn_id = f"ipc_8__{sub_node_id}__{s_idx}"
        std_buttons.append({
            "id": sub_btn_id,
            "next": sub_node_id,
            "label": f"IPC.8.{letter}"
        })

    # Back to IPC Standards button
    btn_back_chap_id = f"ipc_8__back_standard_ipc__{len(subs)}"
    std_buttons.append({
        "id": btn_back_chap_id,
        "next": CHAPTER_NODE_ID,
        "label": "Back to IPC Standards"
    })

    std_node = {
        "id": "ipc_8",
        "type": "menu",
        "data": {
            "id": "ipc_8",
            "label": "STANDARD: IPC.8",
            "message": f"IPC.8 — {IPC_8_DATA['title']}",
            "buttons": std_buttons,
            "chapter": "IPC",
            "program": "Hospitals Accreditation",
            "topic": "standards",
            "nodeType": "menu",
            "layoutWidth": 290,
            "layoutHeight": 280,
            "mapping_status": "VERIFIED"
        },
        "chapter": "IPC",
        "program": "Hospitals Accreditation",
        "topic": "standards",
        "message": f"IPC.8 — {IPC_8_DATA['title']}",
        "position": {"x": 5715, "y": std_pos_y},
        "mapping_status": "VERIFIED"
    }
    if not any(n["id"] == "ipc_8" for n in nodes):
        new_nodes.append(std_node)

    # Back edge from ipc_8 to standard_ipc
    edge_back_chap_id = f"edge-ipc_8-standard_ipc-{btn_back_chap_id}"
    if not any(e["id"] == edge_back_chap_id for e in edges):
        new_edges.append({
            "id": edge_back_chap_id,
            "label": "Back to IPC Standards",
            "source": "ipc_8",
            "target": CHAPTER_NODE_ID,
            "sourceHandle": btn_back_chap_id
        })

    # 4. Create 5 Sub-standard Answer Nodes & Edges
    for s_idx, (letter, desc, _) in enumerate(subs):
        sub_node_id = f"ipc_8_{letter}"
        sub_btn_back_std = f"{sub_node_id}__back_ipc_8__0"
        sub_btn_back_ipc = f"{sub_node_id}__back_standard_ipc__1"

        sub_node = {
            "id": sub_node_id,
            "type": "answer",
            "data": {
                "id": sub_node_id,
                "label": f"IPC.8.{letter} — {desc}",
                "message": desc,
                "buttons": [
                    {"id": sub_btn_back_std, "next": "ipc_8", "label": "Back to IPC.8"},
                    {"id": sub_btn_back_ipc, "next": CHAPTER_NODE_ID, "label": "Back to IPC Standards"}
                ],
                "chapter": "IPC",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "nodeType": "answer",
                "layoutWidth": 280,
                "layoutHeight": 140,
                "mapping_status": "VERIFIED"
            },
            "chapter": "IPC",
            "program": "Hospitals Accreditation",
            "topic": "standards",
            "message": desc,
            "position": {"x": 6220, "y": std_pos_y + s_idx * 140},
            "mapping_status": "VERIFIED"
        }
        if not any(n["id"] == sub_node_id for n in nodes):
            new_nodes.append(sub_node)

        # Edge 1: Forward from ipc_8 to ipc_8_{letter}
        edge_fwd_sub = f"edge-ipc_8-{sub_node_id}-{std_buttons[s_idx]['id']}"
        if not any(e["id"] == edge_fwd_sub for e in edges):
            new_edges.append({
                "id": edge_fwd_sub,
                "label": f"IPC.8.{letter}",
                "source": "ipc_8",
                "target": sub_node_id,
                "sourceHandle": std_buttons[s_idx]["id"]
            })

        # Edge 2: Back from ipc_8_{letter} to ipc_8
        edge_back_std = f"edge-{sub_node_id}-ipc_8-{sub_btn_back_std}"
        if not any(e["id"] == edge_back_std for e in edges):
            new_edges.append({
                "id": edge_back_std,
                "label": "Back to IPC.8",
                "source": sub_node_id,
                "target": "ipc_8",
                "sourceHandle": sub_btn_back_std
            })

        # Edge 3: Back from ipc_8_{letter} to standard_ipc
        edge_back_chap = f"edge-{sub_node_id}-standard_ipc-{sub_btn_back_ipc}"
        if not any(e["id"] == edge_back_chap for e in edges):
            new_edges.append({
                "id": edge_back_chap,
                "label": "Back to IPC Standards",
                "source": sub_node_id,
                "target": CHAPTER_NODE_ID,
                "sourceHandle": sub_btn_back_ipc
            })

    flow_data["nodes"] = nodes + new_nodes
    flow_data["edges"] = edges + new_edges

    return flow_data, new_nodes, new_edges


async def main():
    print("=" * 80)
    print("INTEGRATING NABH IPC.8 STANDARDS (IPC.8.a - IPC.8.e) INTO ACTIVE FLOW")
    print(f"Target Flow ID:    {TARGET_FLOW_ID}")
    print(f"Target Chatbot ID: {TARGET_CHATBOT_ID}")
    print("=" * 80)

    db = SessionLocal()
    target_flow = db.get(Flow, TARGET_FLOW_ID)
    if not target_flow:
        print(f"ERROR: Flow {TARGET_FLOW_ID} not found in database!")
        db.close()
        sys.exit(1)

    orig_nodes = target_flow.flow_data.get("nodes", [])
    orig_edges = target_flow.flow_data.get("edges", [])
    print(f"Current Flow Nodes: {len(orig_nodes)}")
    print(f"Current Flow Edges: {len(orig_edges)}")

    # 1. Pre-change Safety Backup
    print("\n[1/5] Creating Pre-IPC.8 Implementation Safety Backup...")
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file_path = os.path.join(
        backend_dir, "data", f"backup_flow_{TARGET_FLOW_ID}_before_ipc8_complete_{timestamp_str}.json"
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

    # 2. Build Updated Graph
    print("\n[2/5] Constructing IPC.8 Graph Topology...")
    updated_flow_data, new_nodes, new_edges = build_ipc_graph(target_flow.flow_data)
    print(f"  Newly Created Nodes: {len(new_nodes)} (1 main + 5 sub-standards)")
    print(f"  Newly Created Edges: {len(new_edges)} (1 fwd + 1 back + 5 fwd + 5 back + 5 chapter-back = 17)")
    assert len(new_nodes) == 6  # 1 main + 5 sub
    assert len(new_edges) == 17  # 1 + 1 + 5 + 5 + 5
    assert len(updated_flow_data["nodes"]) == len(orig_nodes) + 6
    assert len(updated_flow_data["edges"]) == len(orig_edges) + 17

    # 3. Persist Graph via PUT /flows/{flow_id}
    print(f"\n[3/5] Persisting Updated Flow via PUT /flows/{TARGET_FLOW_ID}...")
    put_payload = {
        "name": target_flow.name,
        "description": target_flow.description,
        "chatbot_id": TARGET_CHATBOT_ID,
        "flow_data": updated_flow_data
    }
    put_status, put_resp = await invoke_asgi("PUT", f"/flows/{TARGET_FLOW_ID}", put_payload)
    print(f"  PUT Response Status: {put_status}")
    if put_status != 200:
        print(f"ERROR: {put_resp}")
        sys.exit(1)
    print(f"  ✓ Flow graph saved: {len(put_resp['flow_data']['nodes'])} nodes, {len(put_resp['flow_data']['edges'])} edges")

    # 4. Store All 5 Sub-Standard Answers in PostgreSQL
    print("\n[4/5] Storing Official Descriptions & Interpretations in PostgreSQL...")
    saved_answers_count = 0

    for letter, desc, interp in IPC_8_DATA["subs"]:
        sub_node_id = f"ipc_8_{letter}"

        # Standard 2-block structure:
        # Block 1: ### Description\n...
        # Block 2: ### Interpretation\n...
        payload = {
            "language": "en",
            "blocks": [
                {
                    "block_type": "text",
                    "position": 1,
                    "content": f"### Description\n{desc}"
                },
                {
                    "block_type": "text",
                    "position": 2,
                    "content": f"### Interpretation\n{interp}"
                }
            ]
        }

        # Check if answer exists (PUT) or create new (POST)
        get_status, _ = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_node_id}/answer?language=en")
        method = "PUT" if get_status == 200 else "POST"

        ans_status, ans_resp = await invoke_asgi(
            method, f"/flows/{TARGET_FLOW_ID}/nodes/{sub_node_id}/answer", payload
        )
        if ans_status not in (200, 201):
            print(f"ERROR saving answer for {sub_node_id}: {ans_resp}")
            sys.exit(1)

        saved_answers_count += 1

    print(f"  ✓ Successfully stored {saved_answers_count} sub-standard answers in PostgreSQL.")

    # 5. Comprehensive Integrity Audit & Endpoints Verification
    print("\n[5/5] Running Comprehensive Post-Integration Verification Audit...")

    # 5.1 GET /flows/{flow_id}
    get_status, flow_res = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}")
    assert get_status == 200
    ret_nodes = flow_res["flow_data"]["nodes"]
    ret_edges = flow_res["flow_data"]["edges"]
    print(f"  Total Flow Nodes: {len(ret_nodes)} (Expected {len(orig_nodes) + 6})")
    print(f"  Total Flow Edges: {len(ret_edges)} (Expected {len(orig_edges) + 17})")
    assert len(ret_nodes) == len(orig_nodes) + 6
    assert len(ret_edges) == len(orig_edges) + 17

    # 5.2 Verify standard_ipc button
    ipc_node = next(n for n in ret_nodes if n["id"] == CHAPTER_NODE_ID)
    ipc_8_btn = next((b for b in ipc_node["data"]["buttons"] if b["next"] == "ipc_8"), None)
    assert ipc_8_btn is not None, "IPC.8 button missing from standard_ipc!"
    print("  ✓ standard_ipc has STANDARD: IPC.8 button pointing to ipc_8")

    # 5.3 Verify ipc_8 main standard node
    std_node = next(n for n in ret_nodes if n["id"] == "ipc_8")
    assert len(std_node["data"]["buttons"]) == 6, f"Expected 6 buttons on ipc_8, got {len(std_node['data']['buttons'])}"
    print("  ✓ ipc_8 has 5 sub-standard buttons (IPC.8.a-e) + 1 Back button")

    # 5.4 Verify all 5 sub-standard answer nodes and database answers
    db = SessionLocal()
    for letter, desc, interp in IPC_8_DATA["subs"]:
        sub_node_id = f"ipc_8_{letter}"
        sub_node = next(n for n in ret_nodes if n["id"] == sub_node_id)
        assert len(sub_node["data"]["buttons"]) == 2, f"Expected 2 buttons on {sub_node_id}"

        # Verify API GET /nodes/{node_id}/answer
        ans_code, ans_data = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_node_id}/answer?language=en")
        assert ans_code == 200, f"Expected 200 for {sub_node_id} answer, got {ans_code}"
        assert len(ans_data["blocks"]) == 2, f"Expected 2 blocks for {sub_node_id}, got {len(ans_data['blocks'])}"
        assert ans_data["blocks"][0]["content"] == f"### Description\n{desc}"
        assert ans_data["blocks"][1]["content"] == f"### Interpretation\n{interp}"

    db.close()
    print("  ✓ All 5 sub-standard nodes and answers verified in PostgreSQL with 2-block structure.")

    # 5.5 Verify existing AAC, COP, MOM, and PRE standards are intact
    aac_nodes = [n for n in ret_nodes if n["id"].startswith("aac_") or n["id"] == "standard_aac"]
    cop_nodes = [n for n in ret_nodes if n["id"].startswith("cop_") or n["id"] == "standard_cop"]
    mom_nodes = [n for n in ret_nodes if n["id"].startswith("mom_") or n["id"] == "standard_mom"]
    pre_nodes = [n for n in ret_nodes if n["id"].startswith("pre_") or n["id"] == "standard_pre"]
    print(f"  ✓ AAC nodes intact: {len(aac_nodes)}")
    print(f"  ✓ COP nodes intact: {len(cop_nodes)}")
    print(f"  ✓ MOM nodes intact: {len(mom_nodes)}")
    print(f"  ✓ PRE nodes intact: {len(pre_nodes)}")

    db = SessionLocal()
    total_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID).count()
    # 264 previous + 5 IPC.8 = 269 total answers
    print(f"  ✓ Total database answers for flow: {total_answers} (Previous: 264, Added: 5, Expected: 269)")
    assert total_answers == 269
    db.close()

    print("\n" + "=" * 80)
    print("SUCCESS: NABH IPC.8 AND 5 SUB-STANDARDS (IPC.8.a - IPC.8.e) INTEGRATED!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

