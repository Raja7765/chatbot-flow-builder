#!/usr/bin/env python3
"""
Comprehensive verification audit script for NABH FMS.1-FMS.7 implementation.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

pg_bin = r"C:\Program Files\PostgreSQL\18\bin"
if os.path.exists(pg_bin):
    os.environ["PATH"] = pg_bin + ";" + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(pg_bin)
        except Exception:
            pass

from sqlalchemy import text
from app.main import app
from app.database import SessionLocal

FLOW_ID = "a23710cb-3353-4811-97b7-5927ba6c6d25"
CHATBOT_ID = "96359635-3ff9-4bfb-befa-13827094b16e"

FMS_STANDARDS = {
    1: {"name": "FMS.1", "subs": ["a", "b", "c", "d", "e"]},
    2: {"name": "FMS.2", "subs": ["a", "b", "c", "d", "e", "f"]},
    3: {"name": "FMS.3", "subs": ["a", "b", "c", "d", "e", "f"]},
    4: {"name": "FMS.4", "subs": ["a", "b", "c", "d", "e", "f", "g", "h"]},
    5: {"name": "FMS.5", "subs": ["a", "b", "c", "d", "e", "f", "g", "h"]},
    6: {"name": "FMS.6", "subs": ["a", "b", "c", "d", "e"]},
    7: {"name": "FMS.7", "subs": ["a", "b", "c", "d", "e"]},
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


async def run_audit():
    print("=" * 80)
    print("STARTING NABH FMS FULL AUDIT")
    print(f"Flow ID: {FLOW_ID}")
    print("=" * 80)

    db = SessionLocal()
    errors = []

    # 1. Fetch flow via API
    status_code, flow_data = await invoke_asgi("GET", f"/flows/{FLOW_ID}")
    if status_code != 200:
        print(f"FAILED to fetch flow: {status_code} {flow_data}")
        return 1

    nodes = flow_data.get("flow_data", {}).get("nodes", []) if "flow_data" in flow_data else flow_data.get("nodes", [])
    edges = flow_data.get("flow_data", {}).get("edges", []) if "flow_data" in flow_data else flow_data.get("edges", [])

    print(f"\n[1] Flow Overview:")
    print(f"  Name: {flow_data.get('name')}")
    print(f"  Chatbot ID: {flow_data.get('chatbot_id')}")
    print(f"  Total Nodes: {len(nodes)} (Expected: 680)")
    print(f"  Total Edges: {len(edges)} (Expected: 1569)")

    if len(nodes) != 680:
        errors.append(f"Expected 680 nodes, got {len(nodes)}")
    if len(edges) != 1569:
        errors.append(f"Expected 1569 edges, got {len(edges)}")

    node_map = {n["id"]: n for n in nodes}

    # 2. Referential integrity check
    print("\n[2] Edge Referential Integrity:")
    missing_sources = [e["id"] for e in edges if e.get("source") not in node_map]
    missing_targets = [e["id"] for e in edges if e.get("target") not in node_map]
    if missing_sources:
        errors.append(f"Edges with missing sources: {len(missing_sources)}")
    if missing_targets:
        errors.append(f"Edges with missing targets: {len(missing_targets)}")
    print(f"  Missing sources: {len(missing_sources)}")
    print(f"  Missing targets: {len(missing_targets)}")

    # 3. Chapter node check
    print("\n[3] standard_fms Chapter Node:")
    if "standard_fms" not in node_map:
        errors.append("standard_fms node missing!")
    else:
        fms_node = node_map["standard_fms"]
        buttons = fms_node.get("data", {}).get("buttons", [])
        print(f"  Buttons count: {len(buttons)} (Expected: 7)")
        expected_btn_targets = [f"fms_{i}" for i in range(1, 8)]
        btn_targets = [b.get("targetNodeId") or b.get("next") for b in buttons]
        if btn_targets != expected_btn_targets:
            errors.append(f"standard_fms button targets mismatch: {btn_targets} vs {expected_btn_targets}")
        else:
            print("  ✓ All 7 FMS main buttons properly configured and targeted.")

    # 4. Main standard menu nodes check
    print("\n[4] Main Standard Menu Nodes (fms_1 - fms_7):")
    total_subs = 0
    for std_num, info in FMS_STANDARDS.items():
        main_id = f"fms_{std_num}"
        if main_id not in node_map:
            errors.append(f"Main node {main_id} missing!")
            continue
        m_node = node_map[main_id]
        m_btns = m_node.get("data", {}).get("buttons", [])
        expected_sub_targets = [f"fms_{std_num}_{letter}" for letter in info["subs"]]
        expected_btn_targets = expected_sub_targets + ["standard_fms"]
        actual_targets = [b.get("targetNodeId") or b.get("next") for b in m_btns]
        if actual_targets != expected_btn_targets:
            errors.append(f"{main_id} button targets mismatch: got {actual_targets}, expected {expected_btn_targets}")
        else:
            print(f"  ✓ {main_id}: {len(info['subs'])} sub-standard buttons + 1 Back button OK.")
        total_subs += len(info["subs"])

    print(f"  Total expected sub-standards: {total_subs} (Expected: 43)")

    # 5. Sub-standard nodes & edges check
    print("\n[5] Sub-Standard Nodes and Dual Back Buttons:")
    for std_num, info in FMS_STANDARDS.items():
        main_id = f"fms_{std_num}"
        for letter in info["subs"]:
            sub_id = f"fms_{std_num}_{letter}"
            if sub_id not in node_map:
                errors.append(f"Sub-standard node {sub_id} missing!")
                continue
            s_node = node_map[sub_id]
            s_btns = s_node.get("data", {}).get("buttons", [])
            if len(s_btns) != 2:
                errors.append(f"{sub_id} should have exactly 2 back buttons, got {len(s_btns)}")
            else:
                t1 = s_btns[0].get("targetNodeId") or s_btns[0].get("next")
                t2 = s_btns[1].get("targetNodeId") or s_btns[1].get("next")
                if t1 != main_id:
                    errors.append(f"{sub_id} btn 1 target should be {main_id}, got {t1}")
                if t2 != "standard_fms":
                    errors.append(f"{sub_id} btn 2 target should be standard_fms, got {t2}")

    # 6. Database answers and blocks verification
    print("\n[6] Database Answer Records & Answer Blocks (SQLAlchemy):")
    answers_query = text("""
        SELECT na.id, na.node_id, na.flow_id, na.language,
               COUNT(ab.id) as block_count
        FROM node_answers na
        LEFT JOIN answer_blocks ab ON na.id = ab.answer_id
        WHERE na.flow_id = :flow_id AND na.node_id LIKE 'fms_%'
        GROUP BY na.id, na.node_id, na.flow_id, na.language
        ORDER BY na.node_id
    """)
    fms_answers = db.execute(answers_query, {"flow_id": FLOW_ID}).fetchall()
    print(f"  Total FMS answer records in DB: {len(fms_answers)} (Expected: 43)")
    if len(fms_answers) != 43:
        errors.append(f"Expected 43 FMS answers, got {len(fms_answers)}")

    for row in fms_answers:
        if row.block_count != 2:
            errors.append(f"Answer for {row.node_id} has {row.block_count} blocks instead of 2")

    # Detailed block check
    blocks_query = text("""
        SELECT ab.answer_id, ab.position, ab.block_type, ab.content, na.node_id
        FROM answer_blocks ab
        JOIN node_answers na ON ab.answer_id = na.id
        WHERE na.flow_id = :flow_id AND na.node_id LIKE 'fms_%'
        ORDER BY na.node_id, ab.position
    """)
    all_blocks = db.execute(blocks_query, {"flow_id": FLOW_ID}).fetchall()
    print(f"  Total FMS answer blocks in DB: {len(all_blocks)} (Expected: 86)")
    if len(all_blocks) != 86:
        errors.append(f"Expected 86 FMS blocks, got {len(all_blocks)}")

    for b in all_blocks:
        if b.position == 1:
            if not b.content.startswith("### Description"):
                errors.append(f"{b.node_id} block 1 does not start with '### Description'")
        elif b.position == 2:
            if not b.content.startswith("### Interpretation"):
                errors.append(f"{b.node_id} block 2 does not start with '### Interpretation'")

    # 7. AsyncClient GET API verification for each answer
    print("\n[7] Testing GET /flows/{flow_id}/nodes/{node_id}/answer?language=en for all 43 sub-standards:")
    api_success_count = 0
    for std_num, info in FMS_STANDARDS.items():
        for letter in info["subs"]:
            sub_id = f"fms_{std_num}_{letter}"
            st, ans = await invoke_asgi("GET", f"/flows/{FLOW_ID}/nodes/{sub_id}/answer?language=en")
            if st != 200:
                errors.append(f"GET answer API failed for {sub_id}: {st}")
            else:
                blocks = ans.get("blocks", [])
                if len(blocks) != 2:
                    errors.append(f"API answer for {sub_id} returned {len(blocks)} blocks instead of 2")
                else:
                    api_success_count += 1

    print(f"  ✓ Successfully verified {api_success_count}/43 sub-standards via REST API.")

    # 8. Check total answers in active flow
    total_answers_query = text("SELECT COUNT(*) FROM node_answers WHERE flow_id = :flow_id")
    total_flow_answers = db.execute(total_answers_query, {"flow_id": FLOW_ID}).scalar()
    total_blocks_query = text("""
        SELECT COUNT(ab.id) 
        FROM answer_blocks ab 
        JOIN node_answers na ON ab.answer_id = na.id 
        WHERE na.flow_id = :flow_id
    """)
    total_flow_blocks = db.execute(total_blocks_query, {"flow_id": FLOW_ID}).scalar()
    print(f"\n[8] Total Active Flow Answers & Blocks in PostgreSQL:")
    print(f"  Total answers: {total_flow_answers} (Expected: 388)")
    print(f"  Total blocks:  {total_flow_blocks} (Expected: 664)")
    if total_flow_answers != 388:
        errors.append(f"Expected 388 total flow answers, got {total_flow_answers}")
    if total_flow_blocks != 664:
        errors.append(f"Expected 664 total flow blocks, got {total_flow_blocks}")

    # 9. Verify preservation of other standards
    print("\n[9] Standards Node Count Preservation Check:")
    aac_nodes = [n for n in nodes if n["id"].startswith("aac_") or n["id"] == "standard_aac"]
    cop_nodes = [n for n in nodes if n["id"].startswith("cop_") or n["id"] == "standard_cop"]
    mom_nodes = [n for n in nodes if n["id"].startswith("mom_") or n["id"] == "standard_mom"]
    pre_nodes = [n for n in nodes if n["id"].startswith("pre_") or n["id"] == "standard_pre"]
    ipc_nodes = [n for n in nodes if n["id"].startswith("ipc_") or n["id"] == "standard_ipc"]
    psq_nodes = [n for n in nodes if n["id"].startswith("psq_") or n["id"] == "standard_psq"]
    rom_nodes = [n for n in nodes if n["id"].startswith("rom_") or n["id"] == "standard_rom"]
    fms_nodes = [n for n in nodes if n["id"].startswith("fms_") or n["id"] == "standard_fms"]

    print(f"  AAC nodes: {len(aac_nodes)} (Expected 18)")
    print(f"  COP nodes: {len(cop_nodes)} (Expected 156)")
    print(f"  MOM nodes: {len(mom_nodes)} (Expected 80)")
    print(f"  PRE nodes: {len(pre_nodes)} (Expected 61)")
    print(f"  IPC nodes: {len(ipc_nodes)} (Expected 7)")
    print(f"  PSQ nodes: {len(psq_nodes)} (Expected 47)")
    print(f"  ROM nodes: {len(rom_nodes)} (Expected 44)")
    print(f"  FMS nodes: {len(fms_nodes)} (Expected 51)")

    if len(aac_nodes) != 18: errors.append(f"AAC nodes count changed: {len(aac_nodes)}")
    if len(cop_nodes) != 156: errors.append(f"COP nodes count changed: {len(cop_nodes)}")
    if len(mom_nodes) != 80: errors.append(f"MOM nodes count changed: {len(mom_nodes)}")
    if len(pre_nodes) != 61: errors.append(f"PRE nodes count changed: {len(pre_nodes)}")
    if len(ipc_nodes) != 7: errors.append(f"IPC nodes count changed: {len(ipc_nodes)}")
    if len(psq_nodes) != 47: errors.append(f"PSQ nodes count changed: {len(psq_nodes)}")
    if len(rom_nodes) != 44: errors.append(f"ROM nodes count changed: {len(rom_nodes)}")
    if len(fms_nodes) != 51: errors.append(f"FMS nodes count mismatch: {len(fms_nodes)}")

    db.close()

    print("\n" + "=" * 80)
    if errors:
        print(f"AUDIT FAILED WITH {len(errors)} ERRORS:")
        for err in errors:
            print(f"  - {err}")
        return 1
    else:
        print("AUDIT PASSED! All FMS standards, nodes, edges, answers, blocks, and APIs 100% verified.")
        print("=" * 80)
        return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(run_audit()))

