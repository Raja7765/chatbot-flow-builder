"""
Script: cleanup_nabh_duplicate_flows.py
Executes safe NABH QMitra duplicate flow cleanup with:
1. Complete JSON backup of all 3 flows, all node_answers, answer_blocks, and media_assets.
2. Safe migration of official hospital answers (eligibility, application, assessment, documents, fee_structure)
   from Flow 2 (0d9e493a...) to Flow 3 (a23710cb...).
3. Pre-deletion verification of all answers, block counts, ordering, and graph counts.
4. Transactional deletion of Flow 1 (4dce6cd9...) and Flow 2 (0d9e493a...).
5. Comprehensive post-deletion verification and integrity audit.
"""

import copy
from datetime import datetime, timezone
import json
import os
import sys
import uuid

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Ensure libpq is discoverable on Windows
pg_bin = r"C:\Program Files\PostgreSQL\18\bin"
if os.path.exists(pg_bin):
    os.environ["PATH"] = pg_bin + ";" + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(pg_bin)
        except Exception:
            pass

from app.database import SessionLocal, get_utc_now
from app.models import Chatbot, Flow, NodeAnswer, AnswerBlock, MediaAsset, format_utc_iso


TARGET_CHATBOT_ID = "96359635-3ff9-4bfb-befa-13827094b16e"
FLOW_1_ID = "4dce6cd9-9ef4-4cb8-bba9-49e3736adde5"  # 206 nodes, 242 edges -> delete
FLOW_2_ID = "0d9e493a-4818-4b42-82ab-ce23a6bcfccc"  # 10 nodes, 0 edges -> migrate answers, then delete
FLOW_3_ID = "a23710cb-3353-4811-97b7-5927ba6c6d25"  # 240 nodes, 311 edges -> preserve as the only active flow


def run_cleanup():
    print("=" * 80)
    print("NABH QMITRA DUPLICATE FLOW CLEANUP & ANSWER MIGRATION")
    print(f"Chatbot ID: {TARGET_CHATBOT_ID}")
    print(f"Flow 1 to delete:  {FLOW_1_ID}")
    print(f"Flow 2 to migrate: {FLOW_2_ID}")
    print(f"Flow 3 to preserve:{FLOW_3_ID}")
    print("=" * 80)

    db = SessionLocal()

    # --------------------------------------------------------------------------
    # PHASE 1: BACKUP
    # --------------------------------------------------------------------------
    print("\n>>> PHASE 1: PRE-MIGRATION SAFETY BACKUP")
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file_path = os.path.join(
        backend_dir, "data", f"backup_nabh_cleanup_pre_migration_{timestamp_str}.json"
    )

    f1 = db.get(Flow, FLOW_1_ID)
    f2 = db.get(Flow, FLOW_2_ID)
    f3 = db.get(Flow, FLOW_3_ID)
    bot = db.get(Chatbot, TARGET_CHATBOT_ID)

    if not f1 or not f2 or not f3 or not bot:
        print("ERROR: One or more target flow/chatbot records missing in database!")
        db.close()
        sys.exit(1)

    all_answers = db.query(NodeAnswer).all()
    all_blocks = db.query(AnswerBlock).all()
    all_media = db.query(MediaAsset).all()

    backup_payload = {
        "timestamp_utc": format_utc_iso(get_utc_now()),
        "chatbot": bot.to_dict(),
        "flows": {
            "flow_1": f1.to_dict(),
            "flow_2": f2.to_dict(),
            "flow_3": f3.to_dict(),
        },
        "node_answers": [a.to_dict() for a in all_answers],
        "answer_blocks": [b.to_dict() for b in all_blocks],
        "media_assets": [m.to_dict() for m in all_media],
    }

    os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
    with open(backup_file_path, "w", encoding="utf-8") as bf:
        json.dump(backup_payload, bf, indent=2, ensure_ascii=False)

    print(f"  ✓ Full database state backed up to: {backup_file_path}")
    print(f"    - Backed up Flows: 3 ({len(f1.flow_data.get('nodes', []))} nodes, {len(f2.flow_data.get('nodes', []))} nodes, {len(f3.flow_data.get('nodes', []))} nodes)")
    print(f"    - Backed up Answers: {len(all_answers)}")
    print(f"    - Backed up Answer Blocks: {len(all_blocks)}")
    print(f"    - Backed up Media Assets: {len(all_media)}")

    # --------------------------------------------------------------------------
    # PHASE 2: MIGRATE ANSWERS FROM FLOW 2 TO FLOW 3
    # --------------------------------------------------------------------------
    print("\n>>> PHASE 2: MIGRATE ANSWERS FROM FLOW 2 TO FLOW 3")
    f3_nodes = {n["id"] for n in f3.flow_data.get("nodes", [])}

    # Fetch answers for Flow 2
    f2_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == FLOW_2_ID).all()
    print(f"  Found {len(f2_answers)} answers on Flow 2:")
    for a in f2_answers:
        blocks_count = db.query(AnswerBlock).filter(AnswerBlock.answer_id == a.id).count()
        print(f"    - {a.node_id} (lang: {a.language}): {blocks_count} blocks")

    migrated_count = 0
    now = get_utc_now()

    for a2 in f2_answers:
        node_id = a2.node_id
        lang = a2.language

        # Verify destination node exists in Flow 3
        if node_id not in f3_nodes:
            print(f"  ERROR: Destination node '{node_id}' does not exist in Flow 3! Aborting.")
            db.rollback()
            db.close()
            sys.exit(1)

        # Get existing answer blocks from Flow 2
        f2_blocks = (
            db.query(AnswerBlock)
            .filter(AnswerBlock.answer_id == a2.id)
            .order_by(AnswerBlock.position.asc())
            .all()
        )

        # Check if answer already exists on Flow 3
        existing_a3 = (
            db.query(NodeAnswer)
            .filter(
                NodeAnswer.flow_id == FLOW_3_ID,
                NodeAnswer.node_id == node_id,
                NodeAnswer.language == lang,
            )
            .first()
        )

        if existing_a3:
            # hospitals_eligibility comparison and replacement
            existing_blocks = (
                db.query(AnswerBlock)
                .filter(AnswerBlock.answer_id == existing_a3.id)
                .order_by(AnswerBlock.position.asc())
                .all()
            )
            print(f"  Updating existing answer on Flow 3 for '{node_id}':")
            print(f"    Existing Flow 3 blocks: {len(existing_blocks)}")
            print(f"    Incoming Flow 2 blocks: {len(f2_blocks)}")

            # Delete old blocks of existing answer
            for ob in existing_blocks:
                db.delete(ob)
            db.flush()

            # Insert new official blocks
            for b in f2_blocks:
                new_block = AnswerBlock(
                    id=uuid.uuid4(),
                    answer_id=existing_a3.id,
                    block_type=b.block_type,
                    content=b.content,
                    media_id=b.media_id,
                    position=b.position,
                    metadata=copy.deepcopy(b.block_metadata) if b.block_metadata else None,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_block)

            existing_a3.updated_at = now
            db.flush()
            print(f"    ✓ Replaced test content of '{node_id}' with {len(f2_blocks)} official blocks.")
            migrated_count += 1

        else:
            # Create new answer on Flow 3
            new_answer_id = uuid.uuid4()
            new_a3 = NodeAnswer(
                id=new_answer_id,
                flow_id=FLOW_3_ID,
                node_id=node_id,
                language=lang,
                created_at=now,
                updated_at=now,
            )
            db.add(new_a3)
            db.flush()

            # Copy blocks
            for b in f2_blocks:
                new_block = AnswerBlock(
                    id=uuid.uuid4(),
                    answer_id=new_answer_id,
                    block_type=b.block_type,
                    content=b.content,
                    media_id=b.media_id,
                    position=b.position,
                    metadata=copy.deepcopy(b.block_metadata) if b.block_metadata else None,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_block)

            db.flush()
            print(f"    ✓ Created new answer for '{node_id}' with {len(f2_blocks)} blocks on Flow 3.")
            migrated_count += 1

    print(f"  ✓ Migration completed: {migrated_count} answers processed.")

    # --------------------------------------------------------------------------
    # PHASE 3: VERIFY MIGRATION BEFORE DELETION
    # --------------------------------------------------------------------------
    print("\n>>> PHASE 3: PRE-DELETION VERIFICATION")

    # 3.1 Check all 5 hospital answers + 4 AAC answers on Flow 3
    expected_hospital_answers = {
        "hospitals_eligibility": 6,
        "hospitals_application": 6,
        "hospitals_assessment": 7,
        "hospitals_documents": 13,
        "hospitals_fee_structure": 1,
    }
    expected_aac_answers = {
        "aac_1_a": 2,
        "aac_1_b": 2,
        "aac_1_c": 2,
        "aac_1_d": 2,
    }

    f3_current_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == FLOW_3_ID).all()
    f3_ans_map = {a.node_id: a for a in f3_current_answers}

    print(f"  Flow 3 Total Answers in DB: {len(f3_current_answers)} (Expected 9)")
    assert len(f3_current_answers) == 9, f"Expected 9 answers on Flow 3, found {len(f3_current_answers)}"

    for node_id, exp_blocks in expected_hospital_answers.items():
        assert node_id in f3_ans_map, f"Missing hospital answer '{node_id}' on Flow 3!"
        ans = f3_ans_map[node_id]
        blocks = (
            db.query(AnswerBlock)
            .filter(AnswerBlock.answer_id == ans.id)
            .order_by(AnswerBlock.position.asc())
            .all()
        )
        assert len(blocks) == exp_blocks, f"Expected {exp_blocks} blocks for '{node_id}', found {len(blocks)}"
        assert [b.position for b in blocks] == list(range(1, exp_blocks + 1)), f"Positions invalid for '{node_id}'"
        print(f"    ✓ Hospital answer verified: {node_id} ({len(blocks)} blocks, ordered 1..{exp_blocks})")

    for node_id, exp_blocks in expected_aac_answers.items():
        assert node_id in f3_ans_map, f"Missing AAC answer '{node_id}' on Flow 3!"
        ans = f3_ans_map[node_id]
        blocks = (
            db.query(AnswerBlock)
            .filter(AnswerBlock.answer_id == ans.id)
            .order_by(AnswerBlock.position.asc())
            .all()
        )
        assert len(blocks) == exp_blocks, f"Expected {exp_blocks} blocks for '{node_id}', found {len(blocks)}"
        print(f"    ✓ AAC answer verified: {node_id} ({len(blocks)} blocks)")

    # 3.2 Confirm Flow 3 graph counts intact
    assert len(f3.flow_data["nodes"]) == 240, f"Expected 240 nodes in Flow 3, got {len(f3.flow_data['nodes'])}"
    assert len(f3.flow_data["edges"]) == 311, f"Expected 311 edges in Flow 3, got {len(f3.flow_data['edges'])}"
    print("    ✓ Flow 3 graph intact: 240 nodes, 311 edges confirmed.")

    # --------------------------------------------------------------------------
    # PHASE 4: DELETE STALE FLOWS
    # --------------------------------------------------------------------------
    print("\n>>> PHASE 4: TRANSACTIONAL DELETION OF STALE FLOWS")

    # Delete Flow 1
    print(f"  Deleting Flow 1 ({FLOW_1_ID})...")
    db.delete(f1)
    db.flush()
    print("    ✓ Flow 1 deleted.")

    # Delete Flow 2 (and its old answer records cascade safely since they were copied)
    print(f"  Deleting Flow 2 ({FLOW_2_ID})...")
    db.delete(f2)
    db.flush()
    print("    ✓ Flow 2 deleted.")

    # Commit all changes atomically
    db.commit()
    print("  ✓ Database transaction committed successfully.")

    # --------------------------------------------------------------------------
    # PHASE 5: POST-DELETION FINAL VERIFICATION
    # --------------------------------------------------------------------------
    print("\n>>> PHASE 5: FINAL POST-CLEANUP VERIFICATION")

    # 5.1 Check flows associated with chatbot
    remaining_flows = db.query(Flow).filter(Flow.chatbot_id == TARGET_CHATBOT_ID).all()
    print(f"  Flows remaining for Chatbot {TARGET_CHATBOT_ID}: {len(remaining_flows)} (Expected 1)")
    assert len(remaining_flows) == 1, f"Expected exactly 1 flow, found {len(remaining_flows)}"
    surviving_flow = remaining_flows[0]
    assert surviving_flow.id == FLOW_3_ID, f"Unexpected surviving flow ID: {surviving_flow.id}"
    print(f"    ✓ Surviving Flow: ID={surviving_flow.id} | Name='{surviving_flow.name}'")

    # 5.2 Confirm node and edge counts
    surviving_nodes = surviving_flow.flow_data.get("nodes", [])
    surviving_edges = surviving_flow.flow_data.get("edges", [])
    assert len(surviving_nodes) == 240, f"Expected 240 nodes, got {len(surviving_nodes)}"
    assert len(surviving_edges) == 311, f"Expected 311 edges, got {len(surviving_edges)}"
    print(f"    ✓ Node count: {len(surviving_nodes)}, Edge count: {len(surviving_edges)}")

    # 5.3 Confirm all 9 answers on Flow 3 remain present
    final_f3_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == FLOW_3_ID).all()
    assert len(final_f3_answers) == 9, f"Expected 9 answers on Flow 3, found {len(final_f3_answers)}"
    total_blocks_count = sum(
        db.query(AnswerBlock).filter(AnswerBlock.answer_id == a.id).count()
        for a in final_f3_answers
    )
    print(f"    ✓ Total Answers on Flow 3: {len(final_f3_answers)}")
    print(f"    ✓ Total Answer Blocks on Flow 3: {total_blocks_count} (33 hospital blocks + 8 AAC blocks = 41 blocks)")
    assert total_blocks_count == 41, f"Expected 41 total blocks, found {total_blocks_count}"

    # 5.4 Check orphan records in whole database
    all_remaining_answers = db.query(NodeAnswer).all()
    all_flow_ids = {f.id for f in db.query(Flow).all()}
    orphan_answers = [a for a in all_remaining_answers if a.flow_id not in all_flow_ids]
    print(f"  Orphan node_answers in entire database: {len(orphan_answers)}")
    assert len(orphan_answers) == 0, f"Found orphan answers: {orphan_answers}"

    all_remaining_blocks = db.query(AnswerBlock).all()
    all_answer_ids = {a.id for a in all_remaining_answers}
    orphan_blocks = [b for b in all_remaining_blocks if b.answer_id not in all_answer_ids]
    print(f"  Orphan answer_blocks in entire database: {len(orphan_blocks)}")
    assert len(orphan_blocks) == 0, f"Found orphan blocks: {orphan_blocks}"

    # 5.5 Check other chatbots are completely untouched
    all_chatbots = db.query(Chatbot).all()
    print(f"  Total Chatbots in database: {len(all_chatbots)}")
    total_flows_in_db = db.query(Flow).all()
    print(f"  Total Flows in database: {len(total_flows_in_db)}")
    for f in total_flows_in_db:
        print(f"    - Flow {f.id} | Name: '{f.name}' | Chatbot: {f.chatbot_id}")

    db.close()

    print("\n" + "=" * 80)
    print("DUPLICATE FLOW CLEANUP & ANSWER MIGRATION COMPLETED SUCCESSFULLY (100%)")
    print("=" * 80)


if __name__ == "__main__":
    run_cleanup()

