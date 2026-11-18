import os
import sys
from pathlib import Path

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
from app.database import SessionLocal
from app.models import Flow, NodeAnswer, AnswerBlock

FLOW_ID = "a23710cb-3353-4811-97b7-5927ba6c6d25"

def main():
    db = SessionLocal()
    flow = db.get(Flow, FLOW_ID)
    if not flow:
        print("Flow not found!")
        return

    nodes = flow.flow_data.get("nodes", [])
    edges = flow.flow_data.get("edges", [])
    print(f"Total nodes in flow: {len(nodes)}")
    print(f"Total edges in flow: {len(edges)}")

    # 1. AAC Nodes & Buttons
    aac_nodes = [n for n in nodes if "aac" in n["id"].lower()]
    print(f"\n--- AAC Nodes ({len(aac_nodes)}) ---")
    for n in sorted(aac_nodes, key=lambda x: x["id"]):
        btns = n.get("data", {}).get("buttons", [])
        print(f"  {n['id']} (type: {n.get('type')}, btns: {len(btns)}, pos: {n.get('position')})")
        if n["id"] in ["standard_aac", "aac_1", "aac_2", "aac_3", "aac_4", "aac_5", "aac_6"]:
            for b in btns:
                print(f"    -> btn: {b}")

    # Check incoming/outgoing edges for aac_1 to aac_6
    aac_node_ids = {n["id"] for n in aac_nodes}
    aac_edges = [e for e in edges if e.get("source") in aac_node_ids or e.get("target") in aac_node_ids]
    print(f"\nAAC edges: {len(aac_edges)}")

    # 2. Existing answers for AAC
    aac_answers = db.query(NodeAnswer).filter(
        NodeAnswer.flow_id == FLOW_ID,
        NodeAnswer.node_id.like("%aac%")
    ).all()
    print(f"\n--- Existing AAC Answers in DB ({len(aac_answers)}) ---")
    for a in aac_answers:
        blocks = a.answer_blocks
        print(f"  NodeAnswer: {a.node_id} (lang: {a.language}, blocks: {len(blocks)})")
        for b in blocks:
            print(f"    pos {b.position} ({b.block_type}): {repr(b.content[:60])}...")

    # 3. Existing answers for MOM
    mom_answers = db.query(NodeAnswer).filter(
        NodeAnswer.flow_id == FLOW_ID,
        NodeAnswer.node_id.like("mom_1_a%")
    ).all()
    print(f"\n--- Existing MOM.1.a Answers in DB ({len(mom_answers)}) ---")
    for a in mom_answers:
        blocks = a.answer_blocks
        print(f"  NodeAnswer: {a.node_id} (lang: {a.language}, blocks: {len(blocks)})")
        for b in blocks:
            print(f"    pos {b.position} ({b.block_type}): {repr(b.content[:60])}...")

    # 4. Check existing format of description/interpretation in other standards (e.g. ROM, PSQ, PRE)
    sample_answers = db.query(NodeAnswer).filter(
        NodeAnswer.flow_id == FLOW_ID,
        NodeAnswer.node_id.in_(["rom_1_a", "psq_1_a", "pre_1_a", "mom_1_a", "aac_1_a"])
    ).all()
    print(f"\n--- Sample Answers Format Across Standards ---")
    for a in sample_answers:
        print(f"  {a.node_id}:")
        for b in a.answer_blocks:
            print(f"    pos {b.position} ({b.block_type}): {repr(b.content[:80])}")

    # 5. Check FMS.3, FMS.5, FMS.7 statements currently on nodes
    fms_nodes = [n for n in nodes if n["id"] in ["fms_3", "fms_5", "fms_7"]]
    print(f"\n--- Current FMS.3, FMS.5, FMS.7 nodes ---")
    for n in fms_nodes:
        print(f"  {n['id']}: label={n.get('data', {}).get('label')}, message={n.get('data', {}).get('message')}")

    db.close()

if __name__ == "__main__":
    main()

