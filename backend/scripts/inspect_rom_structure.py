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

TARGET_FLOW_ID = "a23710cb-3353-4811-97b7-5927ba6c6d25"

db = SessionLocal()
try:
    flow = db.get(Flow, TARGET_FLOW_ID)
    if not flow:
        print(f"Flow {TARGET_FLOW_ID} not found!")
        sys.exit(1)

    flow_data = flow.flow_data or {}
    nodes = flow_data.get("nodes", [])
    edges = flow_data.get("edges", [])

    print(f"Total Nodes: {len(nodes)}, Total Edges: {len(edges)}")

    rom_nodes = [n for n in nodes if "rom" in n.get("id", "").lower()]
    print(f"\nAll nodes with 'rom' in ID ({len(rom_nodes)}):")
    for n in rom_nodes:
        print(f"  ID: {n.get('id')} | Type: {n.get('type')} | Label: {n.get('data', {}).get('label')}")

    standard_rom = next((n for n in nodes if n.get("id") == "standard_rom"), None)
    if standard_rom:
        print("\n--- standard_rom Node ---")
        print(f"ID: {standard_rom.get('id')}")
        print(f"Type: {standard_rom.get('type')}")
        print(f"Position: {standard_rom.get('position')}")
        data = standard_rom.get("data", {})
        print(f"Label: {data.get('label')}")
        print(f"Message: {data.get('message')}")
        buttons = data.get("buttons", [])
        print(f"Buttons ({len(buttons)}):")
        for b in buttons:
            print("  ", b)

    incoming = [e for e in edges if e.get("target") == "standard_rom"]
    outgoing = [e for e in edges if e.get("source") == "standard_rom"]
    print(f"\nIncoming edges to standard_rom: {len(incoming)}")
    for e in incoming:
        print(f"  {e.get('id')}: {e.get('source')} ({e.get('sourceHandle')}) -> {e.get('target')}")
    print(f"Outgoing edges from standard_rom: {len(outgoing)}")
    for e in outgoing:
        print(f"  {e.get('id')}: {e.get('source')} ({e.get('sourceHandle')}) -> {e.get('target')}")

    rom_answers = db.query(NodeAnswer).filter(
        NodeAnswer.flow_id == TARGET_FLOW_ID,
        NodeAnswer.node_id.like("rom%")
    ).all()
    print(f"\nExisting ROM answers in DB: {len(rom_answers)}")

finally:
    db.close()

