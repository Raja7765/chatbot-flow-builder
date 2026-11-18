"""
Exhaustive verification script for NABH PSQ.1–PSQ.7 integration.
Validates:
1. standard_psq menu buttons for PSQ.1–PSQ.7.
2. 7 main standard menu nodes and their sub-standard button lists.
3. 39 sub-standard answer nodes and bidirectional navigation edges.
4. PSQ.5.c contains the newly supplied exact content.
5. Description and Interpretation in PostgreSQL node_answers and answer_blocks.
6. GET /flows/{flow_id}/nodes/{node_id}/answer returns HTTP 200 for all 39 sub-standards.
7. Back navigation edges (both to main standard and to standard_psq).
8. Zero duplicate node IDs and all 131 PSQ edge IDs are strictly unique.
9. No broken source or target edge references across all 1303 edges.
10. Preservation of AAC, COP, MOM, PRE, IPC nodes and answers.
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
from scripts.integrate_psq_standards import (
    PSQ_DATA,
    TARGET_FLOW_ID,
    TARGET_CHATBOT_ID,
    CHAPTER_NODE_ID,
    invoke_asgi,
)


async def verify():
    print("=" * 80)
    print("EXHAUSTIVE AUDIT: NABH PSQ.1 - PSQ.7 STANDARDS INTEGRATION")
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
        assert len(nodes) == 587, f"Expected 587 nodes, got {len(nodes)}"
        assert len(edges) == 1303, f"Expected 1303 edges, got {len(edges)}"

        # 1. Zero duplicate node IDs and strictly unique PSQ edges
        node_ids = [n["id"] for n in nodes]
        assert len(node_ids) == len(set(node_ids)), "Duplicate node IDs detected!"
        psq_edges = [e["id"] for e in edges if "psq" in e["id"] and e["id"] != "edge_031"]
        assert len(psq_edges) == 131, f"Expected 131 PSQ edges, got {len(psq_edges)}"
        assert len(psq_edges) == len(set(psq_edges)), "Duplicate PSQ edge IDs detected!"
        print("  ✓ Zero duplicate node IDs and all 131 PSQ edge IDs are strictly unique.")

        # 2. Verify standard_psq Chapter Node has 7 buttons
        print("\n[1] Verifying standard_psq Chapter Node...")
        psq_chapter = node_map.get(CHAPTER_NODE_ID)
        assert psq_chapter is not None, "standard_psq node missing!"
        psq_buttons = psq_chapter.get("data", {}).get("buttons", [])
        assert len(psq_buttons) == 7, f"Expected 7 buttons on standard_psq, got {len(psq_buttons)}"

        for i in range(1, 8):
            btn = psq_buttons[i - 1]
            assert btn["id"] == f"standard_psq__psq_{i}__{i-1}"
            assert btn["next"] == f"psq_{i}"
            assert btn["label"] == f"STANDARD: PSQ.{i}"

            fwd_edge_id = f"edge-standard_psq-psq_{i}-{btn['id']}"
            assert fwd_edge_id in edge_map, f"Forward edge {fwd_edge_id} missing!"
            fwd_edge = edge_map[fwd_edge_id]
            assert fwd_edge["source"] == CHAPTER_NODE_ID
            assert fwd_edge["target"] == f"psq_{i}"
            assert fwd_edge["sourceHandle"] == btn["id"]

        print("  ✓ standard_psq has all 7 STANDARD: PSQ.1 - PSQ.7 buttons and forward edges.")

        # 3. Verify 7 Main Standard Menu Nodes
        print("\n[2] Verifying 7 Main Standard Menu Nodes (psq_1 to psq_7)...")
        expected_inventory_counts = {1: 7, 2: 5, 3: 8, 4: 4, 5: 5, 6: 5, 7: 5}
        total_sub_verified = 0

        for i in range(1, 8):
            std_id = f"psq_{i}"
            std_node = node_map.get(std_id)
            assert std_node is not None, f"Node {std_id} missing!"
            assert std_node["type"] == "menu"
            assert std_node["data"]["label"] == f"STANDARD: PSQ.{i}"
            assert std_node["data"]["message"] == f"PSQ.{i} — {PSQ_DATA[i]['title']}"

            subs = PSQ_DATA[i]["subs"]
            assert len(subs) == expected_inventory_counts[i], \
                f"Expected {expected_inventory_counts[i]} sub-standards on {std_id}, got {len(subs)}"

            buttons = std_node.get("data", {}).get("buttons", [])
            assert len(buttons) == len(subs) + 1, f"Expected {len(subs) + 1} buttons on {std_id}, got {len(buttons)}"

            # Sub-standard buttons
            for s_idx, (letter, desc, _) in enumerate(subs):
                btn = buttons[s_idx]
                sub_id = f"psq_{i}_{letter}"
                assert btn["id"] == f"psq_{i}__{sub_id}__{s_idx}"
                assert btn["next"] == sub_id
                assert btn["label"] == f"PSQ.{i}.{letter}"

                fwd_sub_edge = f"edge-{std_id}-{sub_id}-{btn['id']}"
                assert fwd_sub_edge in edge_map, f"Forward edge {fwd_sub_edge} missing!"
                edge = edge_map[fwd_sub_edge]
                assert edge["source"] == std_id
                assert edge["target"] == sub_id
                assert edge["sourceHandle"] == btn["id"]

            # Back button to standard_psq
            back_btn = buttons[-1]
            assert back_btn["id"] == f"psq_{i}__back_standard_psq__{len(subs)}"
            assert back_btn["next"] == CHAPTER_NODE_ID
            assert back_btn["label"] == "Back to PSQ Standards"

            back_edge_id = f"edge-{std_id}-standard_psq-{back_btn['id']}"
            assert back_edge_id in edge_map, f"Back edge {back_edge_id} missing!"
            edge = edge_map[back_edge_id]
            assert edge["source"] == std_id
            assert edge["target"] == CHAPTER_NODE_ID
            assert edge["sourceHandle"] == back_btn["id"]

            print(f"  ✓ {std_id}: {len(subs)} sub-standard buttons + 1 Back button verified.")

        # 4. Verify 39 Sub-Standard Answer Nodes & Navigation
        print("\n[3] Verifying 39 Sub-Standard Answer Nodes & Navigation...")
        for i in range(1, 8):
            for letter, desc, interp in PSQ_DATA[i]["subs"]:
                sub_id = f"psq_{i}_{letter}"
                sub_node = node_map.get(sub_id)
                assert sub_node is not None, f"Node {sub_id} missing!"
                assert sub_node["type"] == "answer"
                assert sub_node["data"]["label"] == f"PSQ.{i}.{letter} — {desc}"
                assert sub_node["data"]["message"] == desc

                buttons = sub_node.get("data", {}).get("buttons", [])
                assert len(buttons) == 2, f"Expected 2 buttons on {sub_id}, got {len(buttons)}"

                # Back to main standard
                assert buttons[0]["id"] == f"{sub_id}__back_psq_{i}__0"
                assert buttons[0]["next"] == f"psq_{i}"
                assert buttons[0]["label"] == f"Back to PSQ.{i}"

                edge_back_std = f"edge-{sub_id}-psq_{i}-{buttons[0]['id']}"
                assert edge_back_std in edge_map, f"Edge {edge_back_std} missing!"
                edge = edge_map[edge_back_std]
                assert edge["source"] == sub_id
                assert edge["target"] == f"psq_{i}"
                assert edge["sourceHandle"] == buttons[0]["id"]

                # Back to standard_psq
                assert buttons[1]["id"] == f"{sub_id}__back_standard_psq__1"
                assert buttons[1]["next"] == CHAPTER_NODE_ID
                assert buttons[1]["label"] == "Back to PSQ Standards"

                edge_back_chap = f"edge-{sub_id}-standard_psq-{buttons[1]['id']}"
                assert edge_back_chap in edge_map, f"Edge {edge_back_chap} missing!"
                edge = edge_map[edge_back_chap]
                assert edge["source"] == sub_id
                assert edge["target"] == CHAPTER_NODE_ID
                assert edge["sourceHandle"] == buttons[1]["id"]

                total_sub_verified += 1

        assert total_sub_verified == 39
        print(f"  ✓ All {total_sub_verified} sub-standard answer nodes and bidirectional edges verified.")

        # 5. Verify PostgreSQL node_answers & answer_blocks for PSQ
        print("\n[4] Verifying PostgreSQL node_answers & answer_blocks for PSQ...")
        psq_answers = db.query(NodeAnswer).filter(
            NodeAnswer.flow_id == TARGET_FLOW_ID,
            NodeAnswer.node_id.like("psq_%")
        ).all()
        assert len(psq_answers) == 39, f"Expected 39 PSQ answers in DB, found {len(psq_answers)}"

        for i in range(1, 8):
            for letter, desc, interp in PSQ_DATA[i]["subs"]:
                sub_id = f"psq_{i}_{letter}"
                ans = next((a for a in psq_answers if a.node_id == sub_id), None)
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

                # API Verification
                ans_code, ans_data = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_id}/answer?language=en")
                assert ans_code == 200, f"Expected 200 for {sub_id} API, got {ans_code}"
                assert len(ans_data["blocks"]) == 2
                assert ans_data["blocks"][0]["content"] == f"### Description\n{desc}"
                assert ans_data["blocks"][1]["content"] == f"### Interpretation\n{interp}"

        print("  ✓ All 39 answers persisted in PostgreSQL and return HTTP 200 via GET API.")

        # 6. Specific Verification for PSQ.5.c
        print("\n[5] Verifying Special Instruction for PSQ.5.c...")
        psq_5_c_ans = next(a for a in psq_answers if a.node_id == "psq_5_c")
        psq_5_c_blocks = db.query(AnswerBlock).filter(AnswerBlock.answer_id == psq_5_c_ans.id).order_by(AnswerBlock.position.asc()).all()
        assert psq_5_c_blocks[0].content == "### Description\nMedical and nursing staff participate in clinical audit."
        assert psq_5_c_blocks[1].content == "### Interpretation\nThe organisation shall identify such personnel. It could be a mix of clinicians, administrators and nurses. These could be members of the core committee/quality assurance committee etc."
        print("  ✓ PSQ.5.c matches the exact user-specified Description and Interpretation.")

        # 7. Total Database Answers
        print("\n[6] Verifying Total Database Answers Count across the Active Flow...")
        all_flow_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID).all()
        print(f"  Total Active Flow Answers: {len(all_flow_answers)}")
        assert len(all_flow_answers) == 308, f"Expected 308 answers (269 previous + 39 PSQ), got {len(all_flow_answers)}"

        # 8. Referential integrity across all 1303 edges
        print("\n[7] Verifying Global Edge Referential Integrity (All 1303 Edges)...")
        for e in edges:
            src = e.get("source")
            tgt = e.get("target")
            assert src in node_map, f"Edge {e.get('id')} has invalid source '{src}'"
            assert tgt in node_map, f"Edge {e.get('id')} has invalid target '{tgt}'"
        print("  ✓ All 1303 edges point to valid, existing source and target nodes with zero broken links.")

        # 9. Verify AAC, COP, MOM, PRE, and IPC integrity
        print("\n[8] Verifying Preservation of Existing AAC, COP, MOM, PRE, and IPC Standards...")
        aac_nodes = [n for n in nodes if n["id"].startswith("aac_") or n["id"] == "standard_aac"]
        cop_nodes = [n for n in nodes if n["id"].startswith("cop_") or n["id"] == "standard_cop"]
        mom_nodes = [n for n in nodes if n["id"].startswith("mom_") or n["id"] == "standard_mom"]
        pre_nodes = [n for n in nodes if n["id"].startswith("pre_") or n["id"] == "standard_pre"]
        ipc_nodes = [n for n in nodes if n["id"].startswith("ipc_") or n["id"] == "standard_ipc"]
        assert len(aac_nodes) == 18, f"AAC nodes altered: {len(aac_nodes)}"
        assert len(cop_nodes) == 156, f"COP nodes altered: {len(cop_nodes)}"
        assert len(mom_nodes) == 80, f"MOM nodes altered: {len(mom_nodes)}"
        assert len(pre_nodes) == 61, f"PRE nodes altered: {len(pre_nodes)}"
        assert len(ipc_nodes) == 7, f"IPC nodes altered: {len(ipc_nodes)}"
        print(f"  ✓ AAC nodes: {len(aac_nodes)} intact")
        print(f"  ✓ COP nodes: {len(cop_nodes)} intact")
        print(f"  ✓ MOM nodes: {len(mom_nodes)} intact")
        print(f"  ✓ PRE nodes: {len(pre_nodes)} intact")
        print(f"  ✓ IPC nodes: {len(ipc_nodes)} intact")

        print("\n" + "=" * 80)
        print("AUDIT RESULT: 100% PASS - PSQ.1–PSQ.7 INTEGRATION IS COMPLETE AND VERIFIED!")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(verify())

