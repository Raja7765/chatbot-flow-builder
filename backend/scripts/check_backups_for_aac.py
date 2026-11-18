import json
import glob
import os

backup_files = glob.glob(r"C:\Users\rajas\chatbot-flow-builder\backend\data\*.json")
print(f"Found {len(backup_files)} backup files.")

for bf in sorted(backup_files):
    fname = os.path.basename(bf)
    try:
        with open(bf, "r", encoding="utf-8") as f:
            data = json.load(f)
            flow_data = data.get("flow", {}).get("flow_data", {})
            nodes = flow_data.get("nodes", [])
            aac_subs = [n["id"] for n in nodes if n["id"].startswith("aac_") and len(n["id"].split("_")) > 2]
            answers = data.get("node_answers", [])
            aac_ans = [a["node_id"] for a in answers if a["node_id"].startswith("aac_")]
            print(f"{fname}: nodes={len(nodes)}, aac_subs={aac_subs}, aac_ans={len(aac_ans)}")
    except Exception as e:
        print(f"{fname}: error {e}")

