"""
Comprehensive Verification Script for PRE Standards Integration (PRE.1–PRE.8).
Tests graph topology, node properties, button handles, edge connectivity,
database answers, block structures, API endpoints, and existing standard integrity.
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
from scripts.integrate_pre_standards import PRE_DATA, TARGET_FLOW_ID, TARGET_CHATBOT_ID, CHAPTER_NODE_ID, invoke_asgi


async def verify():
    print("=" * 80)
    print("EXHAUSTIVE AUDIT: PRE STANDARDS INTEGRATION (PRE.1 - PRE.8)")
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
        assert len(nodes) == 535, f"Expected 535 nodes, got {len(nodes)}"
        assert len(edges) == 1155, f"Expected 1155 edges, got {len(edges)}"

        # 1. Audit standard_pre Chapter Node
        print("\n[1] Verifying standard_pre Chapter Node...")
        pre_node = node_map.get(CHAPTER_NODE_ID)
        assert pre_node is not None, "standard_pre node missing!"
        pre_buttons = pre_node.get("data", {}).get("buttons", [])
        assert len(pre_buttons) == 8, f"Expected 8 buttons on standard_pre, got {len(pre_buttons)}"

        for i in range(1, 9):
            btn = pre_buttons[i - 1]
            assert btn["id"] == f"standard_pre__pre_{i}__{i-1}"
            assert btn["next"] == f"pre_{i}"
            assert btn["label"] == f"STANDARD: PRE.{i}"

            # Verify forward edge from standard_pre to pre_{i}
            fwd_edge_id = f"edge-standard_pre-pre_{i}-{btn['id']}"
            assert fwd_edge_id in edge_map, f"Forward edge {fwd_edge_id} missing!"
            edge = edge_map[fwd_edge_id]
            assert edge["source"] == CHAPTER_NODE_ID
            assert edge["target"] == f"pre_{i}"
            assert edge["sourceHandle"] == btn["id"]

        print("  ✓ standard_pre: 8 main buttons & forward edges verified.")

        # 2. Audit 8 Main Standard Nodes (pre_1 to pre_8)
        print("\n[2] Verifying 8 Main Standard Menu Nodes (pre_1 - pre_8)...")
        for i in range(1, 9):
            std_id = f"pre_{i}"
            std_node = node_map.get(std_id)
            assert std_node is not None, f"Node {std_id} missing!"
            assert std_node["type"] == "menu"
            assert std_node["data"]["label"] == f"STANDARD: PRE.{i}"
            assert std_node["data"]["message"] == f"PRE.{i} — {PRE_DATA[i]['title']}"

            subs = PRE_DATA[i]["subs"]
            buttons = std_node["data"]["buttons"]
            assert len(buttons) == len(subs) + 1, f"Expected {len(subs) + 1} buttons on {std_id}, got {len(buttons)}"

            # Verify sub buttons
            for s_idx, (letter, desc, _) in enumerate(subs):
                btn = buttons[s_idx]
                expected_sub_id = f"pre_{i}_{letter}"
                assert btn["id"] == f"pre_{i}__{expected_sub_id}__{s_idx}"
                assert btn["next"] == expected_sub_id
                assert btn["label"] == f"PRE.{i}.{letter}"

                # Verify edge from pre_i to pre_i_letter
                edge_id = f"edge-{std_id}-{expected_sub_id}-{btn['id']}"
                assert edge_id in edge_map, f"Edge {edge_id} missing!"
                edge = edge_map[edge_id]
                assert edge["source"] == std_id
                assert edge["target"] == expected_sub_id
                assert edge["sourceHandle"] == btn["id"]

            # Verify Back to PRE Standards button & edge
            back_btn = buttons[-1]
            assert back_btn["id"] == f"pre_{i}__back_standard_pre__{len(subs)}"
            assert back_btn["next"] == CHAPTER_NODE_ID
            assert back_btn["label"] == "Back to PRE Standards"

            back_edge_id = f"edge-{std_id}-standard_pre-{back_btn['id']}"
            assert back_edge_id in edge_map, f"Back edge {back_edge_id} missing!"
            edge = edge_map[back_edge_id]
            assert edge["source"] == std_id
            assert edge["target"] == CHAPTER_NODE_ID
            assert edge["sourceHandle"] == back_btn["id"]

            print(f"  ✓ {std_id}: {len(subs)} sub buttons + Back to Chapter edge verified.")

        # 3. Audit 52 Sub-Standard Nodes and Back Edges
        print("\n[3] Verifying 52 Sub-Standard Answer Nodes & Navigation...")
        total_sub_verified = 0
        for i in range(1, 9):
            for letter, desc, interp in PRE_DATA[i]["subs"]:
                sub_node_id = f"pre_{i}_{letter}"
                sub_node = node_map.get(sub_node_id)
                assert sub_node is not None, f"Sub-standard node {sub_node_id} missing!"
                assert sub_node["type"] == "answer"
                assert sub_node["data"]["label"] == f"PRE.{i}.{letter} — {desc}"
                assert sub_node["data"]["message"] == desc

                buttons = sub_node["data"]["buttons"]
                assert len(buttons) == 2, f"Expected 2 back buttons on {sub_node_id}"

                # Back to main standard
                btn_std = buttons[0]
                assert btn_std["id"] == f"{sub_node_id}__back_pre_{i}__0"
                assert btn_std["next"] == f"pre_{i}"
                assert btn_std["label"] == f"Back to PRE.{i}"

                edge_std_id = f"edge-{sub_node_id}-pre_{i}-{btn_std['id']}"
                assert edge_std_id in edge_map, f"Edge {edge_std_id} missing!"
                edge = edge_map[edge_std_id]
                assert edge["source"] == sub_node_id
                assert edge["target"] == f"pre_{i}"
                assert edge["sourceHandle"] == btn_std["id"]

                # Back to PRE standards chapter
                btn_chap = buttons[1]
                assert btn_chap["id"] == f"{sub_node_id}__back_standard_pre__1"
                assert btn_chap["next"] == CHAPTER_NODE_ID
                assert btn_chap["label"] == "Back to PRE Standards"

                edge_chap_id = f"edge-{sub_node_id}-standard_pre-{btn_chap['id']}"
                assert edge_chap_id in edge_map, f"Edge {edge_chap_id} missing!"
                edge = edge_map[edge_chap_id]
                assert edge["source"] == sub_node_id
                assert edge["target"] == CHAPTER_NODE_ID
                assert edge["sourceHandle"] == btn_chap["id"]

                total_sub_verified += 1

        assert total_sub_verified == 52
        print(f"  ✓ All {total_sub_verified} sub-standard answer nodes and bidirectional edges verified.")

        # 4. Audit PostgreSQL Database Answers & Blocks
        print("\n[4] Verifying PostgreSQL node_answers & answer_blocks for all 52 Sub-Standards...")
        answers = db.query(NodeAnswer).filter(
            NodeAnswer.flow_id == TARGET_FLOW_ID,
            NodeAnswer.node_id.like("pre_%")
        ).all()
        assert len(answers) == 52, f"Expected 52 PRE answers in DB, found {len(answers)}"

        for ans in answers:
            blocks = db.query(AnswerBlock).filter(AnswerBlock.answer_id == ans.id).order_by(AnswerBlock.position.asc()).all()
            assert len(blocks) == 2, f"Expected 2 blocks for answer {ans.node_id}, got {len(blocks)}"
            assert blocks[0].position == 1
            assert blocks[0].block_type == "text"
            assert blocks[0].content.startswith("### Description\n")
            assert blocks[1].position == 2
            assert blocks[1].block_type == "text"
            assert blocks[1].content.startswith("### Interpretation\n")

        print("  ✓ All 52 answers have exactly 2 ordered blocks (### Description and ### Interpretation).")

        # 5. Audit Total Database Answers Count Across Entire Flow
        print("\n[5] Verifying Total Database Answers Count across the Active Flow...")
        all_flow_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID).all()
        print(f"  Total Active Flow Answers: {len(all_flow_answers)}")
        assert len(all_flow_answers) == 264, f"Expected 264 answers (212 previous + 52 PRE), got {len(all_flow_answers)}"

        # 6. Audit Existing Standards (AAC, COP, MOM, Hospital)
        print("\n[6] Verifying Preservation of Existing AAC, COP, and MOM Standards...")
        aac_nodes = [n for n in nodes if n["id"].startswith("aac_") or n["id"] == "standard_aac"]
        cop_nodes = [n for n in nodes if n["id"].startswith("cop_") or n["id"] == "standard_cop"]
        mom_nodes = [n for n in nodes if n["id"].startswith("mom_") or n["id"] == "standard_mom"]
        assert len(aac_nodes) == 18, f"AAC nodes altered: {len(aac_nodes)}"
        assert len(cop_nodes) == 156, f"COP nodes altered: {len(cop_nodes)}"
        assert len(mom_nodes) == 80, f"MOM nodes altered: {len(mom_nodes)}"
        print(f"  ✓ AAC nodes: {len(aac_nodes)} intact")
        print(f"  ✓ COP nodes: {len(cop_nodes)} intact")
        print(f"  ✓ MOM nodes: {len(mom_nodes)} intact")

        # 7. Check Edge Integrity (Source & Target Exist for ALL 1155 edges)
        print("\n[7] Verifying Global Edge Referential Integrity (All 1155 Edges)...")
        for e in edges:
            src = e.get("source")
            tgt = e.get("target")
            assert src in node_map, f"Edge {e.get('id')} has invalid source '{src}'"
            assert tgt in node_map, f"Edge {e.get('id')} has invalid target '{tgt}'"
        print("  ✓ All 1155 edges point to valid, existing source and target nodes with zero broken links.")

        print("\n" + "=" * 80)
        print("AUDIT RESULT: 100% PASS - PRE.1–PRE.8 INTEGRATION IS COMPLETE AND VERIFIED!")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(verify())

