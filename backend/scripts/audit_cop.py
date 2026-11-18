import sqlite3
import os
import json
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Ensure libpq DLL is discoverable on Windows
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

def check_sqlite(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    print(f"\n--- Checking SQLite: {path} ---")
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print("Tables:", tables)
    for (t,) in tables:
        cur.execute(f"SELECT count(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f"  {t}: {cnt} rows")
        if t in ('flows', 'node_answers', 'answer_blocks'):
            cur.execute(f"SELECT * FROM {t} LIMIT 3")
            rows = cur.fetchall()
            print(f"  Sample {t}: {rows[:1]}")
    con.close()

def main():
    print("=== AUDIT SOURCES ===")
    check_sqlite("backend/chatbot_flow_builder.db")
    check_sqlite("backend/data/flows.db")

    print("\n--- Checking PostgreSQL Flow 3 ---")
    db = SessionLocal()
    f = db.get(Flow, "a23710cb-3353-4811-97b7-5927ba6c6d25")
    if not f:
        print("Flow 3 not found in Postgres!")
        return

    nodes = f.flow_data.get("nodes", [])
    edges = f.flow_data.get("edges", [])
    print(f"Postgres Flow 3: {len(nodes)} nodes, {len(edges)} edges")
    
    # Audit COP.1 to COP.20 in Postgres Flow 3
    cop_nodes = [n for n in nodes if n["id"].startswith("cop_") or n["id"] == "standard_cop"]
    print(f"Total COP-related nodes: {len(cop_nodes)}")
    
    # List COP standards
    for i in range(1, 21):
        std_id = f"cop_{i}"
        std_node = next((n for n in nodes if n["id"] == std_id), None)
        if not std_node:
            print(f"COP.{i}: MISSING NODE {std_id}")
            continue
        
        btns = std_node.get("data", {}).get("buttons", [])
        sub_nodes = [n for n in nodes if n["id"].startswith(f"cop_{i}_")]
        
        # Check answers in DB
        ans_std = db.query(NodeAnswer).filter(NodeAnswer.flow_id == f.id, NodeAnswer.node_id == std_id).all()
        ans_subs = db.query(NodeAnswer).filter(NodeAnswer.flow_id == f.id, NodeAnswer.node_id.like(f"cop_{i}_%")).all()
        
        print(f"COP.{i} (type: {std_node.get('type')}): {len(btns)} buttons on node, {len(sub_nodes)} sub-nodes in graph, {len(ans_subs)} sub-answers in DB")
        if btns:
            btn_labels = [b.get("label") for b in btns]
            print(f"   Buttons: {btn_labels[:4]} ... total {len(btns)}")

    db.close()

if __name__ == "__main__":
    main()

