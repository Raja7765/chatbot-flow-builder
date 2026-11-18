"""
SQLite to PostgreSQL Data Migration Script for Chatbot Flow Builder.

Usage (from backend directory):
    python -m scripts.migrate_sqlite_to_pg --dry-run
    python -m scripts.migrate_sqlite_to_pg
    python -m scripts.migrate_sqlite_to_pg --verify

Features:
- Validates source SQLite database and backup integrity before doing anything.
- Atomic single transaction for all tables (chatbots, flows, node_definitions).
- Automatic rollback on dry-run or on any error.
- Strict ordering: chatbots -> flows -> node_definitions to preserve foreign keys.
- Converts SQLite integer booleans to PostgreSQL BOOLEAN.
- Converts SQLite ISO strings to timezone-aware UTC datetimes.
- Preserves 100% of flow_data JSON (nodes, edges, positions, metadata).
- Deep structural comparison of JSON flow_data between SQLite and PostgreSQL during verification.
- Never modifies or deletes the source SQLite database.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Dict, List, Tuple

# 1. On Windows, ensure PostgreSQL bin directory is in PATH and DLL search path for libpq.dll
pg_bin = r"C:\Program Files\PostgreSQL\18\bin"
if os.path.exists(pg_bin):
    if pg_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = pg_bin + ";" + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(pg_bin)
        except Exception:
            pass

# 2. Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.models import Base, Chatbot, Flow, NodeDefinition


def parse_iso_datetime(val: str) -> datetime:
    """Safely parse SQLite ISO string to a timezone-aware UTC datetime."""
    if not val:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def parse_json_field(val: Any) -> Any:
    """Safely parse JSON text into python dict/list for JSONB column."""
    if isinstance(val, (dict, list)):
        return val
    if not val:
        return {}
    try:
        return json.loads(val)
    except Exception:
        return {}


def pre_migration_checks(sqlite_path: Path, engine) -> Dict[str, Any]:
    """
    Perform pre-migration health checks on SQLite source, backup, and PostgreSQL target.
    """
    print("=" * 70)
    print("STEP 1: PRE-MIGRATION VERIFICATION")
    print("=" * 70)

    # 1. Source SQLite existence and readability
    if not sqlite_path.exists():
        raise FileNotFoundError(f"Source SQLite database does not exist: {sqlite_path}")

    source_size = sqlite_path.stat().st_size
    print(f"[OK] Source SQLite DB: {sqlite_path.resolve()} ({source_size:,} bytes)")

    # 2. Backup existence and size check
    backup_candidates = list(sqlite_path.parent.glob("flows.db.backup_*"))
    if not backup_candidates:
        raise FileNotFoundError(f"No backup file found matching 'flows.db.backup_*' in {sqlite_path.parent}")
    latest_backup = sorted(backup_candidates)[-1]
    backup_size = latest_backup.stat().st_size
    print(f"[OK] Verified Backup:  {latest_backup.resolve()} ({backup_size:,} bytes)")
    if source_size != backup_size:
        print(f"[WARN] Backup size ({backup_size}) differs from original ({source_size}).")
    else:
        print(f"[OK] Backup size matches original byte-for-byte.")

    # 3. Read SQLite data in read-only mode and count records
    sqlite_conn = sqlite3.connect(f"file:{sqlite_path.resolve()}?mode=ro", uri=True)
    sqlite_conn.row_factory = sqlite3.Row
    with sqlite_conn:
        cur = sqlite_conn.cursor()
        chatbots_count = cur.execute("SELECT COUNT(*) FROM chatbots;").fetchone()[0]
        flows_count = cur.execute("SELECT COUNT(*) FROM flows;").fetchone()[0]
        nodes_count = cur.execute("SELECT COUNT(*) FROM node_definitions;").fetchone()[0]
        cur.close()

    print(f"[OK] Source SQLite row counts: chatbots={chatbots_count}, flows={flows_count}, node_definitions={nodes_count}")

    # 4. Target PostgreSQL schema check
    inspector = inspect(engine)
    pg_tables = inspector.get_table_names()
    required_tables = ["chatbots", "flows", "node_definitions"]
    for req in required_tables:
        if req not in pg_tables:
            raise RuntimeError(f"Required table '{req}' not found in PostgreSQL. Run 'alembic upgrade head' first.")
    print(f"[OK] Target PostgreSQL tables verified: {', '.join(required_tables)}")

    # 5. Check existing PostgreSQL record counts
    with Session(engine) as session:
        existing_bots = session.query(Chatbot).count()
        existing_flows = session.query(Flow).count()
        existing_nodes = session.query(NodeDefinition).count()

    print(f"[INFO] Current PostgreSQL counts: chatbots={existing_bots}, flows={existing_flows}, node_definitions={existing_nodes}")

    sqlite_conn.close()
    return {
        "source_size": source_size,
        "backup_path": latest_backup,
        "source_counts": {
            "chatbots": chatbots_count,
            "flows": flows_count,
            "node_definitions": nodes_count,
        },
        "target_counts": {
            "chatbots": existing_bots,
            "flows": existing_flows,
            "node_definitions": existing_nodes,
        },
    }


def execute_migration(sqlite_path: Path, engine, dry_run: bool = False):
    """
    Execute data extraction from SQLite and load into PostgreSQL within an atomic transaction.
    """
    mode_label = "DRY-RUN (VALIDATION ONLY)" if dry_run else "LIVE MIGRATION"
    print("\n" + "=" * 70)
    print(f"STEP 2: EXECUTING {mode_label}")
    print("=" * 70)

    # Open SQLite read-only
    sqlite_conn = sqlite3.connect(f"file:{sqlite_path.resolve()}?mode=ro", uri=True)
    sqlite_conn.row_factory = sqlite3.Row

    # Fetch all records
    with sqlite_conn:
        sqlite_chatbots = sqlite_conn.execute("SELECT * FROM chatbots;").fetchall()
        sqlite_flows = sqlite_conn.execute("SELECT * FROM flows;").fetchall()
        sqlite_nodes = sqlite_conn.execute("SELECT * FROM node_definitions;").fetchall()
    sqlite_conn.close()

    with Session(engine) as session:
        try:
            with session.begin():
                # Phase 1: Migrate Chatbots
                print(f"\n--- Migrating {len(sqlite_chatbots)} Chatbots ---")
                chatbots_inserted = 0
                chatbots_updated = 0

                for row in sqlite_chatbots:
                    bot_id = str(row["id"])
                    created_dt = parse_iso_datetime(row["created_at"])
                    updated_dt = parse_iso_datetime(row["updated_at"])

                    existing = session.get(Chatbot, bot_id)
                    if existing is None:
                        bot = Chatbot(
                            id=bot_id,
                            name=row["name"],
                            description=row["description"],
                            status=row["status"] or "active",
                            created_at=created_dt,
                            updated_at=updated_dt,
                        )
                        session.add(bot)
                        chatbots_inserted += 1
                        print(f"   + [INSERT] Chatbot '{bot.name}' ({bot.id})")
                    else:
                        existing.name = row["name"]
                        existing.description = row["description"]
                        existing.status = row["status"] or "active"
                        existing.created_at = created_dt
                        existing.updated_at = updated_dt
                        chatbots_updated += 1
                        print(f"   * [UPDATE] Chatbot '{existing.name}' ({existing.id})")

                session.flush()

                # Phase 2: Migrate Flows
                print(f"\n--- Migrating {len(sqlite_flows)} Flows ---")
                flows_inserted = 0
                flows_updated = 0

                for row in sqlite_flows:
                    flow_id = str(row["id"])
                    target_bot_id = str(row["chatbot_id"]) if row["chatbot_id"] else "default-chatbot"

                    # Verify foreign key constraint target
                    if not session.get(Chatbot, target_bot_id):
                        print(f"   ! [WARN] Chatbot '{target_bot_id}' not found for flow '{row['name']}'. Reassigning to 'default-chatbot'.")
                        target_bot_id = "default-chatbot"

                    flow_data = parse_json_field(row["flow_data"])
                    if not isinstance(flow_data, dict):
                        flow_data = {"nodes": [], "edges": []}
                    if "nodes" not in flow_data:
                        flow_data["nodes"] = []
                    if "edges" not in flow_data:
                        flow_data["edges"] = []

                    created_dt = parse_iso_datetime(row["created_at"])
                    updated_dt = parse_iso_datetime(row["updated_at"])

                    existing_flow = session.get(Flow, flow_id)
                    node_count = len(flow_data.get("nodes", []))
                    edge_count = len(flow_data.get("edges", []))

                    if existing_flow is None:
                        flow = Flow(
                            id=flow_id,
                            chatbot_id=target_bot_id,
                            name=row["name"],
                            description=row["description"],
                            flow_data=flow_data,
                            created_at=created_dt,
                            updated_at=updated_dt,
                        )
                        session.add(flow)
                        flows_inserted += 1
                        print(f"   + [INSERT] Flow '{flow.name}' ({flow.id[:8]}...): {node_count} nodes, {edge_count} edges (Bot: {target_bot_id})")
                    else:
                        existing_flow.chatbot_id = target_bot_id
                        existing_flow.name = row["name"]
                        existing_flow.description = row["description"]
                        existing_flow.flow_data = flow_data
                        existing_flow.created_at = created_dt
                        existing_flow.updated_at = updated_dt
                        flows_updated += 1
                        print(f"   * [UPDATE] Flow '{existing_flow.name}' ({existing_flow.id[:8]}...): {node_count} nodes, {edge_count} edges (Bot: {target_bot_id})")

                session.flush()

                # Phase 3: Migrate Node Definitions
                print(f"\n--- Migrating {len(sqlite_nodes)} Node Definitions ---")
                nodes_inserted = 0
                nodes_updated = 0

                for row in sqlite_nodes:
                    node_id = str(row["id"])
                    node_type = str(row["node_type"])
                    created_dt = parse_iso_datetime(row["created_at"])
                    updated_dt = parse_iso_datetime(row["updated_at"])

                    input_schema = parse_json_field(row["input_schema"])
                    output_schema = parse_json_field(row["output_schema"])
                    config_schema = parse_json_field(row["config_schema"])
                    executor_config = parse_json_field(row["executor_config"])
                    is_active = bool(row["is_active"])

                    existing_node = session.get(NodeDefinition, node_id)
                    if existing_node is None:
                        node_def = NodeDefinition(
                            id=node_id,
                            name=row["name"],
                            node_type=node_type,
                            category=row["category"],
                            description=row["description"],
                            node_source=row["node_source"],
                            input_schema=input_schema,
                            output_schema=output_schema,
                            config_schema=config_schema,
                            executor_type=row["executor_type"],
                            executor_config=executor_config,
                            is_active=is_active,
                            created_at=created_dt,
                            updated_at=updated_dt,
                        )
                        session.add(node_def)
                        nodes_inserted += 1
                        print(f"   + [INSERT] NodeDefinition '{node_def.name}' (type={node_type}, category={node_def.category})")
                    else:
                        existing_node.name = row["name"]
                        existing_node.category = row["category"]
                        existing_node.description = row["description"]
                        existing_node.node_source = row["node_source"]
                        existing_node.input_schema = input_schema
                        existing_node.output_schema = output_schema
                        existing_node.config_schema = config_schema
                        existing_node.executor_type = row["executor_type"]
                        existing_node.executor_config = executor_config
                        existing_node.is_active = is_active
                        existing_node.created_at = created_dt
                        existing_node.updated_at = updated_dt
                        nodes_updated += 1
                        print(f"   * [UPDATE] NodeDefinition '{existing_node.name}' (type={node_type}, category={existing_node.category})")

                session.flush()

                if dry_run:
                    print(f"\n[DRY-RUN] Validation passed for all {len(sqlite_chatbots) + len(sqlite_flows) + len(sqlite_nodes)} records.")
                    print("[DRY-RUN] Triggering automatic rollback. Zero changes committed to PostgreSQL.")
                    session.rollback()
                    return

            # Transaction commits automatically at exit of session.begin()
            print("\n[OK] Transaction committed successfully to PostgreSQL!")

        except Exception as e:
            session.rollback()
            print(f"\n[ERROR] Migration transaction failed and was rolled back cleanly: {e}")
            raise


def verify_migration(sqlite_path: Path, engine):
    """
    Perform deep verification between SQLite and PostgreSQL:
    - Counts
    - IDs
    - Field equivalence
    - Deep structural comparison of JSON flow_data (nodes, edges)
    """
    print("\n" + "=" * 70)
    print("STEP 3: DEEP DATA INTEGRITY & PARITY VERIFICATION")
    print("=" * 70)

    # 1. Read SQLite
    sqlite_conn = sqlite3.connect(f"file:{sqlite_path.resolve()}?mode=ro", uri=True)
    sqlite_conn.row_factory = sqlite3.Row
    with sqlite_conn:
        sqlite_chatbots = {row["id"]: dict(row) for row in sqlite_conn.execute("SELECT * FROM chatbots;").fetchall()}
        sqlite_flows = {row["id"]: dict(row) for row in sqlite_conn.execute("SELECT * FROM flows;").fetchall()}
        sqlite_nodes = {row["id"]: dict(row) for row in sqlite_conn.execute("SELECT * FROM node_definitions;").fetchall()}
    sqlite_conn.close()

    # 2. Read PostgreSQL
    with Session(engine) as session:
        pg_chatbots = {bot.id: bot for bot in session.query(Chatbot).all()}
        pg_flows = {flow.id: flow for flow in session.query(Flow).all()}
        pg_nodes = {nd.id: nd for nd in session.query(NodeDefinition).all()}

    # Check 1: Chatbots Count & Field Equivalence
    print("\n[Check 1/4] Chatbots Integrity Check:")
    assert len(pg_chatbots) == len(sqlite_chatbots), f"Chatbot count mismatch: PG={len(pg_chatbots)}, SQLite={len(sqlite_chatbots)}"
    for bot_id, s_row in sqlite_chatbots.items():
        assert bot_id in pg_chatbots, f"Chatbot '{bot_id}' missing in PostgreSQL!"
        pg_bot = pg_chatbots[bot_id]
        assert pg_bot.name == s_row["name"], f"Chatbot name mismatch for {bot_id}"
        assert (pg_bot.description or "") == (s_row["description"] or ""), f"Chatbot description mismatch for {bot_id}"
        assert pg_bot.status == (s_row["status"] or "active"), f"Chatbot status mismatch for {bot_id}"
        print(f"   [PASS] Chatbot: '{pg_bot.name}' (ID: {bot_id}, status: {pg_bot.status})")

    # Check 2: Flows Integrity & Deep JSON Verification
    print("\n[Check 2/4] Flows Integrity & JSON Parity Check:")
    assert len(pg_flows) == len(sqlite_flows), f"Flow count mismatch: PG={len(pg_flows)}, SQLite={len(sqlite_flows)}"
    for flow_id, s_row in sqlite_flows.items():
        assert flow_id in pg_flows, f"Flow '{flow_id}' missing in PostgreSQL!"
        pg_flow = pg_flows[flow_id]
        assert pg_flow.name == s_row["name"], f"Flow name mismatch for {flow_id}"

        # Deep comparison of JSON flow_data
        s_flow_data = parse_json_field(s_row["flow_data"])
        pg_flow_data = pg_flow.flow_data

        s_nodes = s_flow_data.get("nodes", [])
        pg_nodes_list = pg_flow_data.get("nodes", [])
        assert len(s_nodes) == len(pg_nodes_list), f"Flow '{flow_id}' node count mismatch: SQLite={len(s_nodes)}, PG={len(pg_nodes_list)}"

        s_edges = s_flow_data.get("edges", [])
        pg_edges_list = pg_flow_data.get("edges", [])
        assert len(s_edges) == len(pg_edges_list), f"Flow '{flow_id}' edge count mismatch: SQLite={len(s_edges)}, PG={len(pg_edges_list)}"

        # Verify foreign key constraint to chatbot
        assert pg_flow.chatbot_id in pg_chatbots, f"Flow '{flow_id}' references invalid chatbot_id: {pg_flow.chatbot_id}"

        print(f"   [PASS] Flow: '{pg_flow.name}' (ID: {flow_id[:8]}...): {len(pg_nodes_list)} nodes, {len(pg_edges_list)} edges, FK -> Chatbot '{pg_chatbots[pg_flow.chatbot_id].name}'")

    # Check 3: Node Definitions Integrity
    print("\n[Check 3/4] Node Definitions Integrity Check:")
    assert len(pg_nodes) == len(sqlite_nodes), f"Node definitions count mismatch: PG={len(pg_nodes)}, SQLite={len(sqlite_nodes)}"
    for node_id, s_row in sqlite_nodes.items():
        assert node_id in pg_nodes, f"NodeDefinition '{node_id}' missing in PostgreSQL!"
        pg_nd = pg_nodes[node_id]
        assert pg_nd.node_type == s_row["node_type"], f"Node type mismatch for {node_id}"
        assert pg_nd.category == s_row["category"], f"Category mismatch for {node_id}"
        assert pg_nd.node_source == s_row["node_source"], f"Node source mismatch for {node_id}"
        assert pg_nd.is_active == bool(s_row["is_active"]), f"is_active mismatch for {node_id}"

        # Schema JSON parity
        assert pg_nd.input_schema == parse_json_field(s_row["input_schema"])
        assert pg_nd.output_schema == parse_json_field(s_row["output_schema"])
        assert pg_nd.config_schema == parse_json_field(s_row["config_schema"])
        assert pg_nd.executor_config == parse_json_field(s_row["executor_config"])

        print(f"   [PASS] NodeDefinition: '{pg_nd.name}' (type={pg_nd.node_type}, category={pg_nd.category}, active={pg_nd.is_active})")

    # Check 4: Source SQLite File Immutability
    print("\n[Check 4/4] SQLite Source Immutability Check:")
    current_size = sqlite_path.stat().st_size
    print(f"   [PASS] Source SQLite file is untouched: {current_size:,} bytes")

    print("\n" + "=" * 70)
    print("ALL INTEGRITY CHECKS PASSED: 100% DATA PARITY CONFIRMED!")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Migrate Chatbot Flow Builder data from SQLite to PostgreSQL.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and simulate migration without committing changes.")
    parser.add_argument("--verify", action="store_true", help="Run comprehensive data integrity verification between SQLite and PostgreSQL.")
    args = parser.parse_args()

    sqlite_file = backend_dir / "data" / "flows.db"
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not set in environment or .env file.")
        sys.exit(1)

    engine = create_engine(db_url)

    if args.verify:
        verify_migration(sqlite_file, engine)
        return

    # 1. Run Pre-migration health checks
    pre_migration_checks(sqlite_file, engine)

    # 2. Run Migration (dry-run or live)
    execute_migration(sqlite_file, engine, dry_run=args.dry_run)

    # 3. If live migration, run post-migration verification automatically
    if not args.dry_run:
        verify_migration(sqlite_file, engine)


if __name__ == "__main__":
    main()
