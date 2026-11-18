"""
Script: verify_mom_full.py
Complete verification of MOM.1-MOM.11 standards, sub-standard nodes, edges, handles,
answers, and backward compatibility with AAC and COP.
"""

import asyncio
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
from app.database import SessionLocal
from app.models import Flow, NodeAnswer, AnswerBlock

TARGET_CHATBOT_ID = "96359635-3ff9-4bfb-befa-13827094b16e"
TARGET_FLOW_ID = "a23710cb-3353-4811-97b7-5927ba6c6d25"


async def invoke_asgi(method: str, path: str) -> tuple:
    parsed_path = path.split("?", 1)
    raw_path = parsed_path[0].encode("latin1")
    query_string = parsed_path[1].encode("latin1") if len(parsed_path) > 1 else b""

    headers = [
        (b"host", b"testserver"),
        (b"content-type", b"application/json"),
        (b"content-length", b"0"),
    ]

    messages = []
    disconnected = asyncio.Event()

    async def receive():
        await disconnected.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)
        if message.get("type") == "http.response.body" and not message.get("more_body", False):
            disconnected.set()

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


async def main():
    print("=" * 80)
    print("RUNNING FINAL VERIFICATION AUDIT FOR MOM INTEGRATION")
    print("=" * 80)

    db = SessionLocal()

    # 1. Flow checks
    status, flow_res = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}")
    assert status == 200, f"Failed to get flow: status {status}"
    nodes = flow_res["flow_data"]["nodes"]
    edges = flow_res["flow_data"]["edges"]
    node_map = {n["id"]: n for n in nodes}
    print(f"Total Nodes: {len(nodes)} (Expected 475)")
    print(f"Total Edges: {len(edges)} (Expected 983)")
    assert len(nodes) == 475
    assert len(edges) == 983

    # 2. Main standard buttons on standard_mom
    mom_chap = node_map.get("standard_mom")
    assert mom_chap is not None
    mom_btns = mom_chap.get("data", {}).get("buttons", [])
    assert len(mom_btns) == 11
    print("✓ All 11 MOM main-standard buttons verified on standard_mom.")

    # 3. Sub-standard buttons & nodes breakdown
    expected_sub_counts = {
        1: 5, 2: 6, 3: 7, 4: 8, 5: 4, 6: 6,
        7: 11, 8: 6, 9: 5, 10: 5, 11: 5
    }

    total_sub_buttons = 0
    total_answers_ok = 0
    table_rows = []

    for i in range(1, 12):
        std_id = f"mom_{i}"
        std_node = node_map.get(std_id)
        assert std_node is not None, f"Missing node {std_id}"
        assert std_node["type"] == "menu"

        btns = std_node.get("data", {}).get("buttons", [])
        sub_btns = [b for b in btns if b["next"] != "standard_mom"]
        back_btn = next((b for b in btns if b["next"] == "standard_mom"), None)
        assert back_btn is not None, f"Missing Back to MOM Standards on {std_id}"

        expected_count = expected_sub_counts[i]
        assert len(sub_btns) == expected_count, f"MOM.{i} expected {expected_count} buttons, got {len(sub_btns)}"
        total_sub_buttons += len(sub_btns)

        # Check answers for each sub-standard
        for b in sub_btns:
            sub_id = b["next"]
            sub_node = node_map.get(sub_id)
            assert sub_node is not None, f"Missing node {sub_id}"
            assert sub_node["type"] == "answer"

            sub_back = sub_node.get("data", {}).get("buttons", [])
            assert len(sub_back) == 2
            assert sub_back[0]["next"] == std_id
            assert sub_back[1]["next"] == "standard_mom"

            # Check GET answer API
            ans_code, ans_data = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_id}/answer?language=en")
            assert ans_code == 200, f"Answer GET failed for {sub_id}"
            blocks = ans_data.get("blocks", [])
            assert len(blocks) == 2, f"Expected 2 blocks for {sub_id}, got {len(blocks)}"
            assert "### Description" in blocks[0]["content"]
            assert "### Interpretation" in blocks[1]["content"]
            total_answers_ok += 1

        table_rows.append({
            "std": f"MOM.{i}",
            "subs": len(sub_btns),
            "answers": len(sub_btns),
            "missing": 0
        })

    print(f"✓ Verified all 68 sub-standards: buttons, nodes, and 2-block answers.")
    assert total_sub_buttons == 68
    assert total_answers_ok == 68

    # 4. Duplicate checks
    from collections import Counter
    node_counts = Counter(n["id"] for n in nodes)
    dup_nodes = [k for k, v in node_counts.items() if v > 1]
    assert len(dup_nodes) == 0, f"Duplicate nodes: {dup_nodes}"
    print("✓ Zero duplicate node IDs.")

    edge_counts = Counter(e["id"] for e in edges)
    dup_edges = [k for k, v in edge_counts.items() if v > 1 and "default" not in k]
    assert len(dup_edges) == 0, f"Duplicate edges: {dup_edges}"
    print("✓ Zero duplicate edge IDs.")

    # 5. Handle matching check
    for e in edges:
        src = e.get("source", "")
        handle = e.get("sourceHandle")
        if src.startswith("mom_") or src == "standard_mom":
            s_node = node_map.get(src)
            b_ids = {b["id"] for b in s_node.get("data", {}).get("buttons", [])}
            assert handle in b_ids, f"Handle mismatch: {e['id']} handle {handle} not in {b_ids}"
    print("✓ 100% of MOM edge handles match button IDs.")

    # 6. Check existing AAC and COP answers
    aac_count = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID, NodeAnswer.node_id.like("aac_%")).count()
    assert aac_count == 4, f"Expected 4 AAC answers, found {aac_count}"
    cop_count = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID, NodeAnswer.node_id.like("cop_%")).count()
    assert cop_count == 135, f"Expected 135 COP answers, found {cop_count}"
    hosp_count = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID, NodeAnswer.node_id.like("hospitals_%")).count()
    assert hosp_count == 5, f"Expected 5 hospital answers, found {hosp_count}"
    mom_count = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID, NodeAnswer.node_id.like("mom_%")).count()
    assert mom_count == 68, f"Expected 68 MOM answers, found {mom_count}"
    total_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID).count()
    assert total_answers == 212
    print(f"✓ All existing answers preserved: 4 AAC + 135 COP + 5 Hospital + 68 MOM = {total_answers} total answers.")

    # 7. Print summary table
    print("\n" + "=" * 60)
    print(f"{'Standard':<10} | {'Sub-standards':>15} | {'Answers Saved':>15} | {'Missing':>8}")
    print("-" * 60)
    for r in table_rows:
        print(f"{r['std']:<10} | {r['subs']:>15} | {r['answers']:>15} | {r['missing']:>8}")
    print("-" * 60)
    print(f"{'TOTAL':<10} | {total_sub_buttons:>15} | {total_answers_ok:>15} | {0:>8}")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    asyncio.run(main())

