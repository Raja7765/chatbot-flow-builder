"""
Exhaustive verification script for NABH IPC.8 integration.
Validates:
1. standard_ipc menu button for IPC.8.
2. ipc_8 main standard node, message, and 5 sub-standard buttons.
3. 5 sub-standard answer nodes and bidirectional navigation edges.
4. Description and Interpretation in PostgreSQL node_answers and answer_blocks.
5. GET /flows/{flow_id}/nodes/{node_id}/answer returns HTTP 200 for all 5 sub-standards.
6. Back navigation edges.
7. No duplicate node or edge IDs.
8. No broken source or target edge references across all 1172 edges.
9. Preservation of AAC, COP, MOM, PRE, and other nodes and answers.
"""

import asyncio
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

from app.database import SessionLocal
from app.models import Flow, NodeAnswer, AnswerBlock
from scripts.integrate_ipc_8_standards import (
    IPC_8_DATA,
    TARGET_FLOW_ID,
    TARGET_CHATBOT_ID,
    CHAPTER_NODE_ID,
    invoke_asgi,
)


async def verify():
    print("=" * 80)
    print("EXHAUSTIVE AUDIT: NABH IPC.8 STANDARDS INTEGRATION")
    print("=" * 80)

    db = SessionLocal()
    try:
        flow = db.get(Flow, TARGET_FLOW_ID)
        assert flow is not None, "Target flow not found in database!"

        flow_data = flow.flow_data or {}
        nodes = flow_data.get("nodes", [])
        edges = flow_data.get("edges", [])
        node_map = {n["id"]: n for n in nodes}
        edge_map = {e["id"]: e for e in edges}

        print(f"Total Nodes: {len(nodes)}")
        print(f"Total Edges: {len(edges)}")
        assert len(nodes) == 541, f"Expected 541 nodes, got {len(nodes)}"
        assert len(edges) == 1172, f"Expected 1172 edges, got {len(edges)}"

        # 1. No duplicate node IDs across flow, and no duplicate IPC.8 edges introduced
        node_ids = [n["id"] for n in nodes]
        assert len(node_ids) == len(set(node_ids)), "Duplicate node IDs detected!"
        ipc_8_edges = [e["id"] for e in edges if "ipc_8" in e["id"]]
        assert len(ipc_8_edges) == 17, f"Expected exactly 17 IPC.8 edges, got {len(ipc_8_edges)}"
        assert len(ipc_8_edges) == len(set(ipc_8_edges)), "Duplicate IPC.8 edge IDs detected!"
        print("  ✓ Zero duplicate node IDs and all 17 IPC.8 edge IDs are strictly unique.")

        # 2. Verify standard_ipc Chapter Node has IPC.8 button
        print("\n[1] Verifying standard_ipc Chapter Node...")
        ipc_chapter = node_map.get(CHAPTER_NODE_ID)
        assert ipc_chapter is not None, "standard_ipc node missing!"
        ipc_buttons = ipc_chapter.get("data", {}).get("buttons", [])
        ipc_8_btn = next((b for b in ipc_buttons if b.get("next") == "ipc_8"), None)
        assert ipc_8_btn is not None, "IPC.8 button missing from standard_ipc!"
        assert ipc_8_btn["label"] == "STANDARD: IPC.8"
        assert ipc_8_btn["id"] == "standard_ipc__ipc_8__0"

        # Verify forward edge from standard_ipc to ipc_8
        fwd_edge_id = f"edge-standard_ipc-ipc_8-{ipc_8_btn['id']}"
        assert fwd_edge_id in edge_map, f"Forward edge {fwd_edge_id} missing!"
        fwd_edge = edge_map[fwd_edge_id]
        assert fwd_edge["source"] == CHAPTER_NODE_ID
        assert fwd_edge["target"] == "ipc_8"
        assert fwd_edge["sourceHandle"] == ipc_8_btn["id"]
        print("  ✓ standard_ipc has STANDARD: IPC.8 button and valid forward edge.")

        # 3. Verify ipc_8 Main Standard Node
        print("\n[2] Verifying ipc_8 Main Standard Menu Node...")
        ipc_8_node = node_map.get("ipc_8")
        assert ipc_8_node is not None, "Node ipc_8 missing!"
        assert ipc_8_node["type"] == "menu"
        assert ipc_8_node["data"]["label"] == "STANDARD: IPC.8"
        assert ipc_8_node["data"]["message"] == f"IPC.8 — {IPC_8_DATA['title']}"

        ipc_8_buttons = ipc_8_node.get("data", {}).get("buttons", [])
        assert len(ipc_8_buttons) == 6, f"Expected 6 buttons on ipc_8, got {len(ipc_8_buttons)}"

        # Verify 5 sub-standard buttons
        for s_idx, (letter, desc, _) in enumerate(IPC_8_DATA["subs"]):
            btn = ipc_8_buttons[s_idx]
            sub_id = f"ipc_8_{letter}"
            assert btn["id"] == f"ipc_8__{sub_id}__{s_idx}"
            assert btn["next"] == sub_id
            assert btn["label"] == f"IPC.8.{letter}"

            # Verify forward edge
            fwd_sub_edge_id = f"edge-ipc_8-{sub_id}-{btn['id']}"
            assert fwd_sub_edge_id in edge_map, f"Forward edge {fwd_sub_edge_id} missing!"
            edge = edge_map[fwd_sub_edge_id]
            assert edge["source"] == "ipc_8"
            assert edge["target"] == sub_id
            assert edge["sourceHandle"] == btn["id"]

        # Verify Back button to standard_ipc
        back_btn = ipc_8_buttons[5]
        assert back_btn["id"] == "ipc_8__back_standard_ipc__5"
        assert back_btn["next"] == CHAPTER_NODE_ID
        assert back_btn["label"] == "Back to IPC Standards"

        back_edge_id = f"edge-ipc_8-standard_ipc-{back_btn['id']}"
        assert back_edge_id in edge_map, f"Back edge {back_edge_id} missing!"
        edge = edge_map[back_edge_id]
        assert edge["source"] == "ipc_8"
        assert edge["target"] == CHAPTER_NODE_ID
        assert edge["sourceHandle"] == back_btn["id"]
        print("  ✓ ipc_8 has all 5 sub-standard buttons + 1 Back button, with verified edges.")

        # 4. Verify 5 Sub-Standard Answer Nodes and Navigation
        print("\n[3] Verifying 5 Sub-Standard Answer Nodes & Navigation...")
        for letter, desc, interp in IPC_8_DATA["subs"]:
            sub_id = f"ipc_8_{letter}"
            sub_node = node_map.get(sub_id)
            assert sub_node is not None, f"Node {sub_id} missing!"
            assert sub_node["type"] == "answer"
            assert sub_node["data"]["label"] == f"IPC.8.{letter} — {desc}"
            assert sub_node["data"]["message"] == desc

            buttons = sub_node.get("data", {}).get("buttons", [])
            assert len(buttons) == 2, f"Expected 2 buttons on {sub_id}, got {len(buttons)}"

            # Button 0: Back to IPC.8
            assert buttons[0]["id"] == f"{sub_id}__back_ipc_8__0"
            assert buttons[0]["next"] == "ipc_8"
            assert buttons[0]["label"] == "Back to IPC.8"

            edge_back_std_id = f"edge-{sub_id}-ipc_8-{buttons[0]['id']}"
            assert edge_back_std_id in edge_map, f"Edge {edge_back_std_id} missing!"
            edge = edge_map[edge_back_std_id]
            assert edge["source"] == sub_id
            assert edge["target"] == "ipc_8"
            assert edge["sourceHandle"] == buttons[0]["id"]

            # Button 1: Back to IPC Standards
            assert buttons[1]["id"] == f"{sub_id}__back_standard_ipc__1"
            assert buttons[1]["next"] == CHAPTER_NODE_ID
            assert buttons[1]["label"] == "Back to IPC Standards"

            edge_back_chap_id = f"edge-{sub_id}-standard_ipc-{buttons[1]['id']}"
            assert edge_back_chap_id in edge_map, f"Edge {edge_back_chap_id} missing!"
            edge = edge_map[edge_back_chap_id]
            assert edge["source"] == sub_id
            assert edge["target"] == CHAPTER_NODE_ID
            assert edge["sourceHandle"] == buttons[1]["id"]

            print(f"  ✓ {sub_id}: answer node + dual back navigation verified.")

        # 5. Verify PostgreSQL node_answers & answer_blocks for IPC.8
        print("\n[4] Verifying PostgreSQL node_answers & answer_blocks for IPC.8...")
        ipc_answers = db.query(NodeAnswer).filter(
            NodeAnswer.flow_id == TARGET_FLOW_ID,
            NodeAnswer.node_id.like("ipc_%")
        ).all()
        assert len(ipc_answers) == 5, f"Expected 5 IPC answers in DB, found {len(ipc_answers)}"

        for letter, desc, interp in IPC_8_DATA["subs"]:
            sub_id = f"ipc_8_{letter}"
            ans = next((a for a in ipc_answers if a.node_id == sub_id), None)
            assert ans is not None, f"Answer missing for {sub_id}"
            assert ans.language == "en"

            blocks = db.query(AnswerBlock).filter(AnswerBlock.answer_id == ans.id).order_by(AnswerBlock.position.asc()).all()
            assert len(blocks) == 2, f"Expected 2 blocks for {sub_id}, got {len(blocks)}"

            assert blocks[0].position == 1
            assert blocks[0].block_type == "text"
            assert blocks[0].content == f"### Description\n{desc}"

            assert blocks[1].position == 2
            assert blocks[1].block_type == "text"
            assert blocks[1].content == f"### Interpretation\n{interp}"

            # 6. Verify GET Answer API endpoint
            ans_code, ans_data = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_id}/answer?language=en")
            assert ans_code == 200, f"Expected 200 for {sub_id} API, got {ans_code}"
            assert len(ans_data["blocks"]) == 2, f"Expected 2 blocks in API response for {sub_id}"
            assert ans_data["blocks"][0]["content"] == f"### Description\n{desc}"
            assert ans_data["blocks"][1]["content"] == f"### Interpretation\n{interp}"

        print("  ✓ All 5 answers persisted in PostgreSQL and return HTTP 200 via GET API.")

        # 7. Total database answers count
        print("\n[5] Verifying Total Database Answers Count across the Active Flow...")
        all_flow_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID).all()
        print(f"  Total Active Flow Answers: {len(all_flow_answers)}")
        assert len(all_flow_answers) == 269, f"Expected 269 answers (264 previous + 5 IPC.8), got {len(all_flow_answers)}"

        # 8. Referential integrity across all 1172 edges
        print("\n[6] Verifying Global Edge Referential Integrity (All 1172 Edges)...")
        for e in edges:
            src = e.get("source")
            tgt = e.get("target")
            assert src in node_map, f"Edge {e.get('id')} has invalid source '{src}'"
            assert tgt in node_map, f"Edge {e.get('id')} has invalid target '{tgt}'"
        print("  ✓ All 1172 edges point to valid, existing source and target nodes with zero broken links.")

        # 9. Verify AAC, COP, MOM, PRE integrity
        print("\n[7] Verifying Preservation of Existing AAC, COP, MOM, and PRE Standards...")
        aac_nodes = [n for n in nodes if n["id"].startswith("aac_") or n["id"] == "standard_aac"]
        cop_nodes = [n for n in nodes if n["id"].startswith("cop_") or n["id"] == "standard_cop"]
        mom_nodes = [n for n in nodes if n["id"].startswith("mom_") or n["id"] == "standard_mom"]
        pre_nodes = [n for n in nodes if n["id"].startswith("pre_") or n["id"] == "standard_pre"]
        assert len(aac_nodes) == 18, f"AAC nodes altered: {len(aac_nodes)}"
        assert len(cop_nodes) == 156, f"COP nodes altered: {len(cop_nodes)}"
        assert len(mom_nodes) == 80, f"MOM nodes altered: {len(mom_nodes)}"
        assert len(pre_nodes) == 61, f"PRE nodes altered: {len(pre_nodes)}"
        print(f"  ✓ AAC nodes: {len(aac_nodes)} intact")
        print(f"  ✓ COP nodes: {len(cop_nodes)} intact")
        print(f"  ✓ MOM nodes: {len(mom_nodes)} intact")
        print(f"  ✓ PRE nodes: {len(pre_nodes)} intact")

        print("\n" + "=" * 80)
        print("AUDIT RESULT: 100% PASS - IPC.8 INTEGRATION IS COMPLETE AND VERIFIED!")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(verify())
