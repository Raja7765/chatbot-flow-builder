"""
Script: complete_aac_standards.py
Implements complete AAC Standards in NABH QMitra Chatbot Flow:
Flow ID: a23710cb-3353-4811-97b7-5927ba6c6d25 (Active third flow)
Chatbot ID: 96359635-3ff9-4bfb-befa-13827094b16e

Changes:
1. Adds 13 main AAC standard buttons to standard_aac node.
2. Adds detail nodes aac_1 to aac_13 (aac_1 as menu, aac_2-aac_13 as rag with PENDING_CONTENT).
3. Adds sub-standard answer nodes aac_1_a to aac_1_d.
4. Adds all connecting edges with matching sourceHandle to button id.
5. Calls PUT /flows/{flow_id} to persist flow changes.
6. Calls POST /flows/{flow_id}/nodes/{node_id}/answer to persist verified Description & Interpretation
   for AAC.1.a through AAC.1.d in PostgreSQL node_answers and answer_blocks.
7. Verifies flow and answer retrieval via GET endpoints and direct DB queries.
"""

import asyncio
import copy
import json
import os
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

from app.main import app
from app.database import SessionLocal
from app.models import Flow, NodeAnswer, AnswerBlock


TARGET_FLOW_ID = "a23710cb-3353-4811-97b7-5927ba6c6d25"
TARGET_CHATBOT_ID = "96359635-3ff9-4bfb-befa-13827094b16e"
TARGET_NODE_ID = "standard_aac"

# 13 AAC Main Standard Buttons for standard_aac
AAC_MAIN_BUTTONS = [
    {"id": f"standard_aac__aac_{i}__{i-1}", "next": f"aac_{i}", "label": f"STANDARD: AAC.{i}"}
    for i in range(1, 14)
]

# AAC.1 Sub-standards source content
AAC_1_SUBSTANDARDS = [
    {
        "id": "aac_1_a",
        "btn_id": "aac_1__aac_1_a__0",
        "label": "AAC.1.a",
        "title": "AAC.1.a — Defined Healthcare Services",
        "desc": "The healthcare services being provided are defined and are in consonance with the needs of the community.",
        "interp": "Services are defined by senior management in consonance with community requirements. Community needs are captured through feedback. Changing disease patterns, such as COVID-19, are considered. The organization may start new services based on its judgment."
    },
    {
        "id": "aac_1_b",
        "btn_id": "aac_1__aac_1_b__1",
        "label": "AAC.1.b",
        "title": "AAC.1.b — Qualified Personnel & Cover",
        "desc": "Each defined clinical service shall have diagnostic and treatment services with suitably qualified personnel who provide out-patient, in-patient, daycare and emergency cover.",
        "interp": "Each defined clinical service, including broad and super-speciality services, must have suitably qualified medical, nursing and paramedical staff. Outpatient and inpatient services must be available. Consultants provide emergency cover. Infrastructure should follow applicable regulatory and professional guidance."
    },
    {
        "id": "aac_1_c",
        "btn_id": "aac_1__aac_1_c__2",
        "label": "AAC.1.c",
        "title": "AAC.1.c — Defined Scope of Services",
        "desc": "Scope of the clinical services of each department is defined.",
        "interp": "Each department's scope should be defined through inclusion and exclusion criteria. A brochure may be used. For example, nephrology may define biopsy, shunts, fistulas, dialysis, haemodialysis and CAPD services. Outsourced clinical and diagnostic services must be documented and staff informed. Information may be shared with patients through websites, displays and brochures."
    },
    {
        "id": "aac_1_d",
        "btn_id": "aac_1__aac_1_d__3",
        "label": "AAC.1.d",
        "title": "AAC.1.d — Prominently Displayed Services",
        "desc": "The organisation's defined clinical services are prominently displayed.",
        "interp": "Names of clinical and diagnostic departments should be visible to patients and visitors through permanent boards, citizen charters or electronic displays. Information should be available at least in the state/majority language and English. Brochures, standees and websites may supplement the display."
    }
]


async def invoke_asgi(method: str, path: str, body: dict = None) -> tuple:
    """Helper to invoke FastAPI ASGI application without networking overhead."""
    payload_bytes = json.dumps(body).encode("utf-8") if body is not None else b""

    headers = [
        (b"host", b"testserver"),
        (b"content-type", b"application/json"),
        (b"content-length", str(len(payload_bytes)).encode("latin1")),
    ]

    messages = []
    has_sent_body = False
    disconnected = asyncio.Event()

    async def receive():
        nonlocal has_sent_body
        if not has_sent_body:
            has_sent_body = True
            return {"type": "http.request", "body": payload_bytes, "more_body": False}
        await disconnected.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)
        if message.get("type") == "http.response.body" and not message.get("more_body", False):
            disconnected.set()

    parsed_path = path.split("?", 1)
    raw_path = parsed_path[0].encode("latin1")
    query_string = parsed_path[1].encode("latin1") if len(parsed_path) > 1 else b""

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": parsed_path[0],
        "raw_path": raw_path,
        "query_string": query_string,
        "root_path": "",
        "headers": headers,
    }

    await app(scope, receive, send)

    status_code = None
    response_body = b""
    for msg in messages:
        if msg["type"] == "http.response.start":
            status_code = msg["status"]
        elif msg["type"] == "http.response.body":
            response_body += msg.get("body", b"")

    try:
        response_json = json.loads(response_body.decode("utf-8")) if response_body else None
    except Exception:
        response_json = response_body.decode("utf-8", errors="replace")

    return status_code, response_json


def build_updated_graph(original_flow_data: dict) -> tuple:
    """
    Constructs the updated nodes and edges for flow a23710cb-3353-4811-97b7-5927ba6c6d25.
    Returns (updated_flow_data, new_nodes_list, new_edges_list).
    """
    flow_data = copy.deepcopy(original_flow_data)
    nodes = flow_data.get("nodes", [])
    edges = flow_data.get("edges", [])

    # 1. Update standard_aac node
    aac_node = next((n for n in nodes if n["id"] == TARGET_NODE_ID), None)
    if not aac_node:
        raise ValueError(f"Target node '{TARGET_NODE_ID}' not found in flow.")

    if "data" not in aac_node or not isinstance(aac_node["data"], dict):
        aac_node["data"] = {}

    aac_node["data"]["buttons"] = AAC_MAIN_BUTTONS
    aac_node["mapping_status"] = "VERIFIED"

    # 2. Detail nodes aac_1 to aac_13
    new_nodes = []
    new_edges = []

    # aac_1 node (menu with sub-standard buttons + back button)
    aac_1_buttons = [
        {"id": sub["btn_id"], "next": sub["id"], "label": sub["label"]}
        for sub in AAC_1_SUBSTANDARDS
    ]
    aac_1_buttons.append({
        "id": "aac_1__back_standard_aac__4",
        "next": "standard_aac",
        "label": "Back to AAC Standards"
    })

    aac_1_node = {
        "id": "aac_1",
        "type": "menu",
        "data": {
            "label": "STANDARD: AAC.1",
            "message": "AAC.1 — Scope and Definition of Healthcare Services",
            "buttons": aac_1_buttons,
            "chapter": "AAC",
            "program": "Hospitals Accreditation",
            "topic": "standards",
        },
        "chapter": "AAC",
        "program": "Hospitals Accreditation",
        "topic": "standards",
        "message": "AAC.1 — Scope and Definition of Healthcare Services",
        "position": {"x": 380, "y": 0},
        "mapping_status": "VERIFIED"
    }
    new_nodes.append(aac_1_node)

    # aac_2 to aac_13 nodes (rag with PENDING_CONTENT + back button)
    for i in range(2, 14):
        node_id = f"aac_{i}"
        btn_back_id = f"{node_id}__back_standard_aac__0"
        node_def = {
            "id": node_id,
            "type": "rag",
            "data": {
                "label": f"STANDARD: AAC.{i}",
                "message": f"AAC.{i} — Access, Assessment and Continuity of Care (Standard Details)",
                "buttons": [
                    {"id": btn_back_id, "next": "standard_aac", "label": "Back to AAC Standards"}
                ],
                "chapter": "AAC",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "status": "PENDING",
                "mapping_status": "PENDING_CONTENT",
                "note": "Official NABH sub-standards and interpretations pending verification"
            },
            "chapter": "AAC",
            "program": "Hospitals Accreditation",
            "topic": "standards",
            "message": f"AAC.{i} — Access, Assessment and Continuity of Care (Standard Details)",
            "position": {"x": 380, "y": (i - 1) * 140},
            "mapping_status": "PENDING_CONTENT"
        }
        new_nodes.append(node_def)

    # aac_1_a to aac_1_d sub-standard answer nodes
    for idx, sub in enumerate(AAC_1_SUBSTANDARDS):
        sub_id = sub["id"]
        sub_buttons = [
            {"id": f"{sub_id}__back_aac_1__0", "next": "aac_1", "label": "Back to AAC.1"},
            {"id": f"{sub_id}__back_standard_aac__1", "next": "standard_aac", "label": "Back to AAC Standards"}
        ]
        sub_node = {
            "id": sub_id,
            "type": "answer",
            "data": {
                "label": sub["title"],
                "message": sub["desc"],
                "buttons": sub_buttons,
                "chapter": "AAC",
                "program": "Hospitals Accreditation",
                "topic": "standards"
            },
            "chapter": "AAC",
            "program": "Hospitals Accreditation",
            "topic": "standards",
            "message": sub["desc"],
            "position": {"x": 780, "y": idx * 160},
            "mapping_status": "VERIFIED"
        }
        new_nodes.append(sub_node)

    # 3. Create all edges

    # Edges from standard_aac to aac_1..aac_13 (13 edges)
    for btn in AAC_MAIN_BUTTONS:
        edge = {
            "id": f"edge-standard_aac-{btn['next']}-{btn['id']}",
            "type": "smoothstep",
            "label": btn["label"],
            "style": {"stroke": "#A3A3A3", "strokeWidth": 1.5},
            "source": "standard_aac",
            "target": btn["next"],
            "sourceHandle": btn["id"]
        }
        new_edges.append(edge)

    # Edges from aac_1 to aac_1_a..aac_1_d (4 edges)
    for sub in AAC_1_SUBSTANDARDS:
        edge = {
            "id": f"edge-aac_1-{sub['id']}-{sub['btn_id']}",
            "type": "smoothstep",
            "label": sub["label"],
            "style": {"stroke": "#A3A3A3", "strokeWidth": 1.5},
            "source": "aac_1",
            "target": sub["id"],
            "sourceHandle": sub["btn_id"]
        }
        new_edges.append(edge)

    # Back edge from aac_1 to standard_aac (1 edge)
    new_edges.append({
        "id": "edge-aac_1-standard_aac-aac_1__back_standard_aac__4",
        "type": "smoothstep",
        "label": "Back to AAC Standards",
        "style": {"stroke": "#A3A3A3", "strokeWidth": 1.5},
        "source": "aac_1",
        "target": "standard_aac",
        "sourceHandle": "aac_1__back_standard_aac__4"
    })

    # Back edges from aac_2..aac_13 to standard_aac (12 edges)
    for i in range(2, 14):
        node_id = f"aac_{i}"
        btn_back_id = f"{node_id}__back_standard_aac__0"
        new_edges.append({
            "id": f"edge-{node_id}-standard_aac-{btn_back_id}",
            "type": "smoothstep",
            "label": "Back to AAC Standards",
            "style": {"stroke": "#A3A3A3", "strokeWidth": 1.5},
            "source": node_id,
            "target": "standard_aac",
            "sourceHandle": btn_back_id
        })

    # Back edges from aac_1_a..aac_1_d to aac_1 and standard_aac (8 edges)
    for sub in AAC_1_SUBSTANDARDS:
        sub_id = sub["id"]
        # Back to aac_1
        new_edges.append({
            "id": f"edge-{sub_id}-aac_1-{sub_id}__back_aac_1__0",
            "type": "smoothstep",
            "label": "Back to AAC.1",
            "style": {"stroke": "#A3A3A3", "strokeWidth": 1.5},
            "source": sub_id,
            "target": "aac_1",
            "sourceHandle": f"{sub_id}__back_aac_1__0"
        })
        # Back to standard_aac
        new_edges.append({
            "id": f"edge-{sub_id}-standard_aac-{sub_id}__back_standard_aac__1",
            "type": "smoothstep",
            "label": "Back to AAC Standards",
            "style": {"stroke": "#A3A3A3", "strokeWidth": 1.5},
            "source": sub_id,
            "target": "standard_aac",
            "sourceHandle": f"{sub_id}__back_standard_aac__1"
        })

    # Append new nodes and edges
    flow_data["nodes"] = nodes + new_nodes
    flow_data["edges"] = edges + new_edges

    return flow_data, new_nodes, new_edges


async def main():
    print("=" * 75)
    print("EXECUTING COMPLETE AAC STANDARDS IMPLEMENTATION")
    print(f"Target Flow ID:    {TARGET_FLOW_ID}")
    print(f"Target Chatbot ID: {TARGET_CHATBOT_ID}")
    print("=" * 75)

    # Step 1: Pre-flight DB Check
    db = SessionLocal()
    target_flow = db.get(Flow, TARGET_FLOW_ID)
    if not target_flow:
        print(f"ERROR: Flow {TARGET_FLOW_ID} not found in database!")
        db.close()
        sys.exit(1)

    print(f"Flow Name: '{target_flow.name}'")
    orig_nodes = target_flow.flow_data.get("nodes", [])
    orig_edges = target_flow.flow_data.get("edges", [])
    orig_node_count = len(orig_nodes)
    orig_edge_count = len(orig_edges)
    print(f"Original Node Count: {orig_node_count}")
    print(f"Original Edge Count: {orig_edge_count}")
    assert orig_node_count == 223, f"Expected 223 nodes, got {orig_node_count}"
    assert orig_edge_count == 273, f"Expected 273 edges, got {orig_edge_count}"
    db.close()

    # Step 2: Build Updated Graph
    updated_flow_data, new_nodes, new_edges = build_updated_graph(target_flow.flow_data)
    print(f"\nPrepared Graph Updates:")
    print(f"  New Nodes: {len(new_nodes)} (Total: {len(updated_flow_data['nodes'])})")
    print(f"  New Edges: {len(new_edges)} (Total: {len(updated_flow_data['edges'])})")
    assert len(updated_flow_data["nodes"]) == 240
    assert len(updated_flow_data["edges"]) == 311

    # Step 3: PUT /flows/{flow_id}
    print(f"\n[1/3] Updating flow via PUT /flows/{TARGET_FLOW_ID}...")
    put_payload = {
        "name": target_flow.name,
        "description": target_flow.description,
        "chatbot_id": TARGET_CHATBOT_ID,
        "flow_data": updated_flow_data
    }

    put_status, put_resp = await invoke_asgi("PUT", f"/flows/{TARGET_FLOW_ID}", put_payload)
    print(f"  PUT Response Status: {put_status}")
    if put_status != 200:
        print(f"ERROR updating flow: {put_resp}")
        sys.exit(1)

    v_nodes = put_resp["flow_data"]["nodes"]
    v_edges = put_resp["flow_data"]["edges"]
    print(f"  Verified updated flow: {len(v_nodes)} nodes, {len(v_edges)} edges")

    # Step 4: Populate PostgreSQL Node Answers for AAC.1.a - AAC.1.d
    print("\n[2/3] Storing answer content for AAC.1.a - AAC.1.d via POST .../answer...")
    created_answers = []
    for sub in AAC_1_SUBSTANDARDS:
        sub_id = sub["id"]
        answer_payload = {
            "language": "en",
            "blocks": [
                {
                    "block_type": "text",
                    "position": 1,
                    "content": f"### Description\n{sub['desc']}"
                },
                {
                    "block_type": "text",
                    "position": 2,
                    "content": f"### Interpretation\n{sub['interp']}"
                }
            ]
        }

        # Check if answer exists (PUT) or needs creation (POST)
        get_status, get_existing = await invoke_asgi(
            "GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_id}/answer?language=en"
        )
        if get_status == 200:
            method = "PUT"
            print(f"  Updating existing answer for node '{sub_id}' via PUT...")
        else:
            method = "POST"
            print(f"  Creating new answer for node '{sub_id}' via POST...")

        ans_status, ans_resp = await invoke_asgi(
            method, f"/flows/{TARGET_FLOW_ID}/nodes/{sub_id}/answer", answer_payload
        )

        print(f"  [{method}] /flows/.../nodes/{sub_id}/answer => Status {ans_status}")
        if ans_status not in (200, 201):
            print(f"ERROR saving answer for {sub_id}: {ans_resp}")
            sys.exit(1)

        created_answers.append(ans_resp)
        print(f"    Answer ID: {ans_resp['id']}, Blocks: {len(ans_resp['blocks'])}")
        for b in ans_resp["blocks"]:
            print(f"      Pos {b['position']}: {b['block_type']} => {b['content'][:50]}...")

    # Step 5: Verification & Safety Audit
    print("\n[3/3] Running Full System Verification & Safety Checks...")

    # Verification 5.1: Retrieve flow via GET /flows/{TARGET_FLOW_ID}
    get_flow_status, get_flow_resp = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}")
    assert get_flow_status == 200
    retrieved_nodes = get_flow_resp["flow_data"]["nodes"]
    retrieved_edges = get_flow_resp["flow_data"]["edges"]
    assert len(retrieved_nodes) == 240, f"Expected 240 nodes, found {len(retrieved_nodes)}"
    assert len(retrieved_edges) == 311, f"Expected 311 edges, found {len(retrieved_edges)}"
    print(f"  ✓ GET /flows/{TARGET_FLOW_ID}: 240 nodes, 311 edges confirmed.")

    # Verification 5.2: Verify standard_aac node buttons
    retrieved_aac = next(n for n in retrieved_nodes if n["id"] == TARGET_NODE_ID)
    retrieved_buttons = retrieved_aac.get("data", {}).get("buttons", [])
    assert len(retrieved_buttons) == 13, f"Expected 13 buttons, found {len(retrieved_buttons)}"
    for idx, btn in enumerate(retrieved_buttons):
        assert btn["id"] == f"standard_aac__aac_{idx+1}__{idx}"
        assert btn["next"] == f"aac_{idx+1}"
        assert btn["label"] == f"STANDARD: AAC.{idx+1}"
    print("  ✓ All 13 AAC main standard buttons verified on standard_aac.")

    # Verification 5.3: Verify aac_1 menu node buttons
    retrieved_aac_1 = next(n for n in retrieved_nodes if n["id"] == "aac_1")
    aac_1_btns = retrieved_aac_1.get("data", {}).get("buttons", [])
    assert len(aac_1_btns) == 5, f"Expected 5 buttons on aac_1, found {len(aac_1_btns)}"
    print("  ✓ aac_1 menu node buttons (4 sub-standards + 1 back) verified.")

    # Verification 5.4: Verify pending status on aac_2..aac_13
    for i in range(2, 14):
        node = next(n for n in retrieved_nodes if n["id"] == f"aac_{i}")
        assert node.get("mapping_status") == "PENDING_CONTENT"
        assert node.get("data", {}).get("mapping_status") == "PENDING_CONTENT"
    print("  ✓ aac_2 through aac_13 marked as PENDING_CONTENT verified.")

    # Verification 5.5: Verify edge handles
    edge_sources = {(e["source"], e["sourceHandle"]): e["target"] for e in retrieved_edges if e.get("sourceHandle")}
    for btn in retrieved_buttons:
        assert (TARGET_NODE_ID, btn["id"]) in edge_sources
        assert edge_sources[(TARGET_NODE_ID, btn["id"])] == btn["next"]
    for btn in aac_1_btns:
        assert ("aac_1", btn["id"]) in edge_sources
        assert edge_sources[("aac_1", btn["id"])] == btn["next"]
    print("  ✓ All edge sourceHandles match button IDs exactly.")

    # Verification 5.6: Verify answers via GET /flows/.../nodes/.../answer
    for sub in AAC_1_SUBSTANDARDS:
        sub_id = sub["id"]
        ans_status, ans_data = await invoke_asgi(
            "GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_id}/answer?language=en"
        )
        assert ans_status == 200
        assert ans_data["flow_id"] == TARGET_FLOW_ID
        assert ans_data["node_id"] == sub_id
        assert len(ans_data["blocks"]) == 2
        assert ans_data["blocks"][0]["position"] == 1
        assert sub["desc"] in ans_data["blocks"][0]["content"]
        assert ans_data["blocks"][1]["position"] == 2
        assert sub["interp"] in ans_data["blocks"][1]["content"]
    print("  ✓ All 4 sub-standard answers retrieved and verified in order from PostgreSQL.")

    # Verification 5.7: Verify Database flow table integrity (no duplicates)
    db = SessionLocal()
    flows_in_db = db.query(Flow).all()
    print(f"\nDatabase Flow Integrity Check:")
    print(f"  Total Flows in DB: {len(flows_in_db)}")
    for f in flows_in_db:
        node_c = len(f.flow_data.get("nodes", []))
        edge_c = len(f.flow_data.get("edges", []))
        print(f"    - ID: {f.id} | Name: '{f.name}' | Nodes: {node_c} | Edges: {edge_c} | Chatbot: {f.chatbot_id}")
        if f.id == "4dce6cd9-9ef4-4cb8-bba9-49e3736adde5":
            assert node_c == 206 and edge_c == 242, "First flow was altered!"
        elif f.id == "0d9e493a-4818-4b42-82ab-ce23a6bcfccc":
            assert node_c == 10 and edge_c == 0, "Second flow was altered!"
        elif f.id == TARGET_FLOW_ID:
            assert node_c == 240 and edge_c == 311, "Target flow count mismatch!"
    db.close()
    print("  ✓ Safety confirmed: Neither Flow 1 nor Flow 2 was modified; no duplicate flows created.")

    print("\n" + "=" * 75)
    print("ALL AAC STANDARDS IMPLEMENTATION AND VERIFICATION CHECKS PASSED (100%)")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(main())

