import os, sys, json
sys.path.insert(0, os.path.abspath('backend'))
from app.database import SessionLocal
from app.models import Flow

db = SessionLocal()
flow = db.get(Flow, 'a23710cb-3353-4811-97b7-5927ba6c6d25')
nodes = flow.flow_data.get('nodes', [])
edges = flow.flow_data.get('edges', [])

for n in nodes:
    if n['id'] in ('standard_hrm', 'hospital_standards_chapters'):
        print(f"=== Node {n['id']} ===")
        print(json.dumps(n, indent=2))

print('=== Edges involving standard_hrm ===')
for e in edges:
    if e.get('source') == 'standard_hrm' or e.get('target') == 'standard_hrm':
        print(json.dumps(e, indent=2))

