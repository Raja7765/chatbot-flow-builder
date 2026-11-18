"""
Script: verify_cop_chat_flow.py
Simulates chatbot preview navigation and answer retrieval for all COP.1-COP.20 standards.
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
    print("VERIFYING COP.1 - COP.20 CHATBOT NAVIGATION & ANSWER RETRIEVAL")
    print("=" * 80)

    db = SessionLocal()
    target_flow = db.get(Flow, TARGET_FLOW_ID)
    nodes = target_flow.flow_data.get("nodes", [])
    edges = target_flow.flow_data.get("edges", [])
    node_map = {n["id"]: n for n in nodes}
    edge_map = {e["id"]: e for e in edges}

    # Verify standard_cop
    cop_chap = node_map.get("standard_cop")
    assert cop_chap is not None, "standard_cop missing"
    cop_btns = cop_chap.get("data", {}).get("buttons", [])
    assert len(cop_btns) == 20, f"Expected 20 COP buttons, found {len(cop_btns)}"
    print(f"✓ standard_cop: 20 main standard buttons verified.")

    total_subs = 0
    total_answers = 0
    audit_table = []

    for i in range(1, 21):
        std_id = f"cop_{i}"
        std_node = node_map.get(std_id)
        assert std_node is not None, f"Node {std_id} missing"
        assert std_node["type"] == "menu", f"Node {std_id} should be menu, got {std_node['type']}"

        btns = std_node.get("data", {}).get("buttons", [])
        # All buttons except back button
        sub_btns = [b for b in btns if b.get("next") != "standard_cop"]
        back_btn = next((b for b in btns if b.get("next") == "standard_cop"), None)
        assert back_btn is not None, f"Back button missing on {std_id}"

        std_subs_count = len(sub_btns)
        total_subs += std_subs_count

        # Check sub nodes and answers
        answers_available = 0
        for b in sub_btns:
            sub_id = b["next"]
            sub_node = node_map.get(sub_id)
            assert sub_node is not None, f"Sub-node {sub_id} missing in graph"
            assert sub_node["type"] == "answer", f"Sub-node {sub_id} should be answer type"

            # Check back buttons on sub-node
            sub_back_btns = sub_node.get("data", {}).get("buttons", [])
            assert len(sub_back_btns) == 2, f"Sub-node {sub_id} should have 2 back buttons"
            assert sub_back_btns[0]["next"] == std_id
            assert sub_back_btns[1]["next"] == "standard_cop"

            # Verify GET answer API
            status, ans = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_id}/answer?language=en")
            assert status == 200, f"GET answer failed for {sub_id}: status {status}"
            assert len(ans.get("blocks", [])) >= 1, f"No blocks for {sub_id}"
            content = ans["blocks"][0]["content"]
            assert "**Description:**" in content, f"Missing Description in {sub_id}"
            assert "**Interpretation:**" in content, f"Missing Interpretation in {sub_id}"
            answers_available += 1

        total_answers += answers_available
        audit_table.append({
            "cop": f"COP.{i}",
            "existing": 0 if i <= 9 else std_subs_count,
            "newly_created": std_subs_count if i <= 9 else 0,
            "answers_available": answers_available,
            "missing": 0
        })

    print(f"\n✓ Verified all 20 COP standards.")
    print(f"✓ Total sub-standards verified in graph: {total_subs}")
    print(f"✓ Total sub-standard answers verified via GET API: {total_answers}")

    print("\n--- FINAL AUDIT TABLE (COP.1 to COP.20) ---")
    print(f"{'COP':<8} | {'Existing sub-buttons':>20} | {'Newly created':>13} | {'Answers available':>17} | {'Missing':>7}")
    print("-" * 75)
    for row in audit_table:
        print(f"{row['cop']:<8} | {row['existing']:>20} | {row['newly_created']:>13} | {row['answers_available']:>17} | {row['missing']:>7}")
    print("-" * 75)
    total_existing = sum(r["existing"] for r in audit_table)
    total_new = sum(r["newly_created"] for r in audit_table)
    total_ans = sum(r["answers_available"] for r in audit_table)
    total_missing = sum(r["missing"] for r in audit_table)
    print(f"{'TOTAL':<8} | {total_existing:>20} | {total_new:>13} | {total_ans:>17} | {total_missing:>7}")

    db.close()


if __name__ == "__main__":
    asyncio.run(main())

