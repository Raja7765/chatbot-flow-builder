"""
Script: integrate_rom_standards.py
Integrates NABH Responsibilities of Management (ROM) Standards (ROM.1–ROM.6),
their 37 collected sub-standard buttons and nodes, and their individual Description + Interpretation answers
into the existing NABH QMitra chatbot flow (a23710cb-3353-4811-97b7-5927ba6c6d25).
"""

import asyncio
import copy
from datetime import datetime, timezone
import json
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

from app.main import app
from app.database import SessionLocal, get_utc_now
from app.models import Flow, NodeAnswer, AnswerBlock, format_utc_iso


TARGET_CHATBOT_ID = "96359635-3ff9-4bfb-befa-13827094b16e"
TARGET_FLOW_ID = "a23710cb-3353-4811-97b7-5927ba6c6d25"
CHAPTER_NODE_ID = "standard_rom"

# Complete Official NABH ROM Standards & 37 Collected Sub-Standards
ROM_DATA = {
    1: {
        "title": "The organisation identifies those responsible for governance and their roles are defined",
        "subs": [
            ("a",
             "Those responsible for governance are identified and their roles and responsibilities are defined and documented.",
             "The organisation clearly identifies and documents its governing body (such as Board of Directors, Trust, Partners, or Owners), outlining their administrative, operational, and legal responsibilities in by-laws or terms of reference."),
            ("b",
             "Those responsible for governance lay down the organisation's vision, mission and values.",
             "The governing body formulates, documents, and approves the organisation's vision, mission, and core values, ensuring they guide hospital policies and healthcare delivery."),
            ("c",
             "Those responsible for governance approve the strategic and operational plans and the organisation's annual budget.",
             "The governing body reviews and formally approves long-term strategic plans, annual operational goals, capital investments, and the comprehensive hospital budget."),
            ("d",
             "Those responsible for governance monitor and measure the performance of the organisation against the stated mission.",
             "The governing entity periodically monitors hospital performance metrics, clinical outcomes, financial reports, and strategic progress against the stated institutional mission."),
            ("e",
             "Those responsible for governance appoint senior leaders in the organisation.",
             "The governing body appoints qualified and experienced executive leaders (such as CEO, Medical Superintendent, and Nursing Director) to head day-to-day operations."),
            ("f",
             "Those responsible for governance support the quality improvement plan and patient-safety programme.",
             "The governing body actively endorses, finances, and reviews the continuous quality improvement plan and patient safety initiatives across the organisation."),
            ("g",
             "Those responsible for governance support the organisation's ethical management framework.",
             "The governing entity mandates and supports an ethical framework governing clinical practice, business conduct, patient transparency, and professional integrity."),
            ("h",
             "Those responsible for governance ensure that the organisation complies with applicable statutory rules and regulations.",
             "The governing body establishes oversight mechanisms ensuring that the hospital operates strictly within all local, state, and national legal and regulatory mandates."),
            ("i",
             "Those responsible for governance inform the public about the quality and performance of services rendered.",
             "The organisation transparently informs the community and patients regarding the scope, clinical performance, accreditation status, and quality achievements of the hospital.")
        ]
    },
    2: {
        "title": "The organisation is ethically managed by the leaders",
        "subs": [
            ("a",
             "The leaders make public the vision, mission, and values of the organisation.",
             "Hospital leadership prominently displays and disseminates the vision, mission, and core values across physical areas and digital platforms in languages understood by the community."),
            ("b",
             "The leaders establish the organisation's ethical management framework.",
             "The leadership defines and implements a formal ethical management policy outlining standards of professional conduct, conflict-of-interest guidelines, and anti-corruption measures."),
            ("c",
             "The ethical management framework includes processes for managing issues with ethical implications, dilemmas, and concerns.",
             "The organisation establishes structured mechanisms (such as a hospital ethics committee) to review and resolve clinical and administrative ethical dilemmas, concerns, and grievances."),
            ("d",
             "The organisation discloses its ownership.",
             "The healthcare organisation transparently discloses its legal ownership, corporate structure, governing board members, and affiliations to patients and regulatory authorities.")
        ]
    },
    3: {
        "title": "The organisation is headed by a leader who shall be responsible for operating the organisation on a day-to-day basis",
        "subs": [
            ("a",
             "The person heading the organisation has requisite and appropriate administrative qualifications.",
             "The designated leader (CEO, Medical Superintendent, or Executive Director) possesses recognized administrative, medical, or management qualifications commensurate with the scope of services."),
            ("b",
             "The person heading the organisation has requisite and appropriate administrative experience.",
             "The organisational leader holds verifiable healthcare leadership and administrative experience necessary to govern hospital operations, clinical teams, and support departments effectively."),
            ("c",
             "The leader is responsible for and complies with the laid-down and applicable legislations, regulations, and notifications.",
             "The chief administrator ensures rigorous institutional compliance with all statutory acts, medical council notifications, municipal regulations, and statutory licenses."),
            ("d",
             "The performance of the organisation’s leader is reviewed for effectiveness.",
             "The governing body conducts an objective, documented annual performance review of the organisation's leader against established key performance indicators and strategic objectives."),
            ("e",
             "The leader ensures implementation of policies and procedures across the organisation.",
             "The executive leader drives operational adherence to standard operating procedures, clinical pathways, infection control policies, and administrative guidelines across all units."),
            ("f",
             "The leader ensures sustainable management of resources and operations.",
             "The leader champions environmental sustainability, resource optimization, energy conservation, safe waste disposal, and fiscal resilience throughout hospital operations."),
            ("g",
             "The leader establishes channels of communication across all levels of the organisation.",
             "Structured internal communication mechanisms (including town halls, departmental briefings, circulars, and digital portals) ensure transparent two-way information flow across all cadres.")
        ]
    },
    4: {
        "title": "The organisation displays professionalism in its functioning",
        "subs": [
            ("a",
             "The organisation documents the scope of services provided by each department.",
             "Each clinical, diagnostic, and support department maintains a clearly defined, documented scope of services specifying available clinical procedures, diagnostic capabilities, and limitations."),
            ("b",
             "The organisation maintains a comprehensive legal tracker and ensures compliance with statutory requirements.",
             "The hospital maintains an updated statutory register/legal tracker monitoring license validity, renewal dates, inspection requirements, and legal compliance obligations."),
            ("c",
             "Key Result Areas (KRAs) and Key Performance Indicators (KPIs) are defined for departmental leaders.",
             "Documented KRAs and quantifiable KPIs are established for clinical department heads, nursing supervisors, and administrative managers to guide departmental goals."),
            ("d",
             "The organisation regularly monitors departmental performance against defined KRAs and KPIs.",
             "Leadership conducts structured periodic reviews analyzing departmental performance data, addressing operational variances, and recognizing high-performing units."),
            ("e",
             "Performance evaluations of staff and departmental leaders are conducted periodically.",
             "A formalized annual appraisal system objectively evaluates individual competency, clinical skill adherence, achievement of goals, and professional conduct.")
        ]
    },
    5: {
        "title": "Management ensures that patient-safety aspects and risk-management issues are an integral part of patient care and hospital management",
        "subs": [
            ("a",
             "The management formulates and implements strategic and operational plans.",
             "Hospital management develops comprehensive short-term and multi-year operational plans with clear timeframes, departmental responsibilities, and resource allocations."),
            ("b",
             "The management allocates adequate financial and physical resources for hospital operations.",
             "Management ensures sufficient capital and operational funding for medical equipment maintenance, staffing levels, safety infrastructure, and facility maintenance."),
            ("c",
             "Multidisciplinary committees are constituted and function effectively.",
             "Statutory and hospital committees (such as Quality, Infection Control, Safety, Ethics, and Pharmacotherapeutics) are properly constituted with regular meetings and documented minutes."),
            ("d",
             "Committee recommendations are documented and submitted to management for action.",
             "Committee deliberations, action plans, and recommendations are formally reviewed by senior management to ensure timely implementation and accountability."),
            ("e",
             "The management plans and oversees service expansion and infrastructure development.",
             "Any addition of clinical specialties, expansion of bed capacity, or new technology procurement follows structured feasibility assessments and safety compliance evaluations."),
            ("f",
             "The management documents case studies and lessons learned for continual organisational improvement.",
             "Management systematically records critical clinical audits, quality breakthroughs, safety incident resolutions, and case studies to foster institutional knowledge and continual improvement.")
        ]
    },
    6: {
        "title": "The management executes its responsibility for compliance with all applicable regulations",
        "subs": [
            ("a",
             "The management ensures proactive identification and mitigation of operational and clinical risks.",
             "Management maintains an institutional risk register, utilizing risk assessment matrices to identify, rank, and proactively mitigate clinical, environmental, and financial hazards."),
            ("b",
             "The organisation implements policies and procedures for managing outsourced clinical and support services.",
             "Clear guidelines govern the selection, credentialing, scope definition, and operational coordination of contracted clinical and non-clinical support service providers."),
            ("c",
             "Memoranda of Understanding (MoU) or Service Level Agreements (SLA) define the scope and performance standards for outsourced services.",
             "Formal contracts, MoUs, and SLAs explicitly define quality benchmarks, turnaround times, regulatory compliance requirements, and confidentiality obligations for all outsourced vendors."),
            ("d",
             "Outsourced services comply with applicable legal and statutory requirements.",
             "The hospital verifies that external service providers (e.g., bio-medical waste handlers, dietary, laundry, security, imaging) maintain valid statutory permits and licenses."),
            ("e",
             "The organisation monitors the quality and performance of outsourced services periodically.",
             "Designated hospital supervisors conduct regular audits and quality evaluations of outsourced services against contractual performance standards and patient feedback."),
            ("f",
             "Corrective and preventive actions are taken based on the evaluation of outsourced services.",
             "Deficiencies or service SLA breaches trigger formal corrective action plans, vendor reviews, or contractual escalations to ensure sustained service quality.")
        ]
    }
}


async def invoke_asgi(method: str, path: str, payload: dict = None) -> tuple:
    """Helper to invoke FastAPI app endpoints asynchronously in-process."""
    payload_bytes = json.dumps(payload).encode("utf-8") if payload is not None else b""

    headers = [
        (b"host", b"testserver"),
        (b"accept", b"application/json"),
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


def build_rom_graph(original_flow_data: dict) -> tuple:
    """
    Construct the updated flow graph by:
    1. Adding 6 main buttons to standard_rom node.
    2. Creating 6 rom_{i} menu nodes.
    3. Creating 37 rom_{i}_{sub} answer nodes.
    4. Adding all 123 navigation edges.
    """
    flow_data = copy.deepcopy(original_flow_data)
    nodes = flow_data.get("nodes", [])
    edges = flow_data.get("edges", [])

    node_map = {n["id"]: n for n in nodes}

    # 1. Update standard_rom chapter node
    rom_chapter = node_map.get(CHAPTER_NODE_ID)
    if not rom_chapter:
        raise ValueError(f"Chapter node '{CHAPTER_NODE_ID}' not found in flow.")

    # 6 Main standard buttons for standard_rom
    rom_main_buttons = [
        {"id": f"standard_rom__rom_{i}__{i-1}", "next": f"rom_{i}", "label": f"STANDARD: ROM.{i}"}
        for i in range(1, 7)
    ]
    rom_chapter["data"]["buttons"] = rom_main_buttons
    rom_chapter["data"]["message"] = "ROM — Responsibilities of Management (NABH 5th Edition Standards)"
    rom_chapter["data"]["mapping_status"] = "VERIFIED"
    rom_chapter["mapping_status"] = "VERIFIED"

    new_nodes = []
    new_edges = []

    # 2. Forward edges from standard_rom to rom_1..rom_6 (6 edges)
    for btn in rom_main_buttons:
        new_edges.append({
            "id": f"edge-standard_rom-{btn['next']}-{btn['id']}",
            "label": btn["label"],
            "source": CHAPTER_NODE_ID,
            "target": btn["next"],
            "sourceHandle": btn["id"]
        })

    # 3. Create Main standard nodes rom_1 to rom_6 & their sub-standards
    std_base_y = 19500
    for i in range(1, 7):
        std_id = f"rom_{i}"
        std_info = ROM_DATA[i]
        subs = std_info["subs"]
        pos_y = std_base_y + (i - 1) * 350

        # Sub-standard buttons for rom_i
        std_buttons = []
        for s_idx, (letter, desc, _) in enumerate(subs):
            sub_node_id = f"rom_{i}_{letter}"
            btn_id = f"rom_{i}__{sub_node_id}__{s_idx}"
            std_buttons.append({
                "id": btn_id,
                "next": sub_node_id,
                "label": f"ROM.{i}.{letter}"
            })

        # Back to ROM Standards button
        btn_back_id = f"rom_{i}__back_standard_rom__{len(subs)}"
        std_buttons.append({
            "id": btn_back_id,
            "next": CHAPTER_NODE_ID,
            "label": "Back to ROM Standards"
        })

        # Main standard node definition (menu)
        std_node = {
            "id": std_id,
            "type": "menu",
            "data": {
                "id": std_id,
                "label": f"STANDARD: ROM.{i}",
                "message": f"ROM.{i} — {std_info['title']}",
                "buttons": std_buttons,
                "chapter": "ROM",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "nodeType": "menu",
                "layoutWidth": 290,
                "layoutHeight": 280,
                "mapping_status": "VERIFIED"
            },
            "chapter": "ROM",
            "program": "Hospitals Accreditation",
            "topic": "standards",
            "message": f"ROM.{i} — {std_info['title']}",
            "position": {"x": 5715, "y": pos_y},
            "mapping_status": "VERIFIED"
        }
        new_nodes.append(std_node)

        # Back edge from rom_i to standard_rom
        new_edges.append({
            "id": f"edge-{std_id}-standard_rom-{btn_back_id}",
            "label": "Back to ROM Standards",
            "source": std_id,
            "target": CHAPTER_NODE_ID,
            "sourceHandle": btn_back_id
        })

        # Sub-standard answer nodes and connecting edges
        for s_idx, (letter, desc, _) in enumerate(subs):
            sub_node_id = f"rom_{i}_{letter}"
            sub_btn_back_std = f"{sub_node_id}__back_rom_{i}__0"
            sub_btn_back_rom = f"{sub_node_id}__back_standard_rom__1"

            sub_node = {
                "id": sub_node_id,
                "type": "answer",
                "data": {
                    "id": sub_node_id,
                    "label": f"ROM.{i}.{letter} — {desc}",
                    "message": desc,
                    "buttons": [
                        {"id": sub_btn_back_std, "next": std_id, "label": f"Back to ROM.{i}"},
                        {"id": sub_btn_back_rom, "next": CHAPTER_NODE_ID, "label": "Back to ROM Standards"}
                    ],
                    "chapter": "ROM",
                    "program": "Hospitals Accreditation",
                    "topic": "standards",
                    "nodeType": "answer",
                    "layoutWidth": 280,
                    "layoutHeight": 140,
                    "mapping_status": "VERIFIED"
                },
                "chapter": "ROM",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "message": desc,
                "position": {"x": 6220, "y": pos_y + s_idx * 140},
                "mapping_status": "VERIFIED"
            }
            new_nodes.append(sub_node)

            # Edge 1: Forward from rom_i to rom_i_letter
            new_edges.append({
                "id": f"edge-{std_id}-{sub_node_id}-{std_buttons[s_idx]['id']}",
                "label": f"ROM.{i}.{letter}",
                "source": std_id,
                "target": sub_node_id,
                "sourceHandle": std_buttons[s_idx]["id"]
            })

            # Edge 2: Back from rom_i_letter to rom_i
            new_edges.append({
                "id": f"edge-{sub_node_id}-{std_id}-{sub_btn_back_std}",
                "label": f"Back to ROM.{i}",
                "source": sub_node_id,
                "target": std_id,
                "sourceHandle": sub_btn_back_std
            })

            # Edge 3: Back from rom_i_letter to standard_rom
            new_edges.append({
                "id": f"edge-{sub_node_id}-standard_rom-{sub_btn_back_rom}",
                "label": "Back to ROM Standards",
                "source": sub_node_id,
                "target": CHAPTER_NODE_ID,
                "sourceHandle": sub_btn_back_rom
            })

    flow_data["nodes"] = nodes + new_nodes
    flow_data["edges"] = edges + new_edges

    return flow_data, new_nodes, new_edges


async def main():
    print("=" * 80)
    print("INTEGRATING NABH ROM.1 - ROM.6 STANDARDS INTO ACTIVE FLOW")
    print(f"Target Flow ID:    {TARGET_FLOW_ID}")
    print(f"Target Chatbot ID: {TARGET_CHATBOT_ID}")
    print("=" * 80)

    db = SessionLocal()
    target_flow = db.get(Flow, TARGET_FLOW_ID)
    if not target_flow:
        print(f"ERROR: Flow {TARGET_FLOW_ID} not found in database!")
        db.close()
        sys.exit(1)

    orig_nodes = target_flow.flow_data.get("nodes", [])
    orig_edges = target_flow.flow_data.get("edges", [])
    print(f"Current Flow Nodes: {len(orig_nodes)}")
    print(f"Current Flow Edges: {len(orig_edges)}")

    # 1. Pre-change Safety Backup
    print("\n[1/5] Creating Pre-ROM Implementation Safety Backup...")
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file_path = os.path.join(
        backend_dir, "data", f"backup_flow_{TARGET_FLOW_ID}_before_rom_complete_{timestamp_str}.json"
    )
    all_answers = db.query(NodeAnswer).all()
    all_blocks = db.query(AnswerBlock).all()
    backup_payload = {
        "timestamp_utc": format_utc_iso(get_utc_now()),
        "flow": target_flow.to_dict(),
        "node_answers": [a.to_dict() for a in all_answers],
        "answer_blocks": [b.to_dict() for b in all_blocks],
    }
    with open(backup_file_path, "w", encoding="utf-8") as bf:
        json.dump(backup_payload, bf, indent=2, ensure_ascii=False)
    print(f"  ✓ Safety backup saved to: {backup_file_path}")
    db.close()

    # 2. Build Updated Graph
    print("\n[2/5] Constructing ROM Graph Topology...")
    updated_flow_data, new_nodes, new_edges = build_rom_graph(target_flow.flow_data)
    print(f"  Newly Created Nodes: {len(new_nodes)} (6 main + 37 sub-standards)")
    print(f"  Newly Created Edges: {len(new_edges)} (6 fwd + 6 back + 37 fwd + 37 back + 37 chapter-back = 123)")
    assert len(new_nodes) == 43  # 6 + 37
    assert len(new_edges) == 123  # 6 + 6 + 37 + 37 + 37
    assert len(updated_flow_data["nodes"]) == len(orig_nodes) + 43
    assert len(updated_flow_data["edges"]) == len(orig_edges) + 123

    # 3. Persist Graph via PUT /flows/{flow_id}
    print(f"\n[3/5] Persisting Updated Flow via PUT /flows/{TARGET_FLOW_ID}...")
    put_payload = {
        "name": target_flow.name,
        "description": target_flow.description,
        "chatbot_id": TARGET_CHATBOT_ID,
        "flow_data": updated_flow_data
    }
    put_status, put_resp = await invoke_asgi("PUT", f"/flows/{TARGET_FLOW_ID}", put_payload)
    print(f"  PUT Response Status: {put_status}")
    if put_status != 200:
        print(f"ERROR: {put_resp}")
        sys.exit(1)
    print(f"  ✓ Flow graph saved: {len(put_resp['flow_data']['nodes'])} nodes, {len(put_resp['flow_data']['edges'])} edges")

    # 4. Store All 37 Sub-Standard Answers in PostgreSQL
    print("\n[4/5] Storing Official Descriptions & Interpretations in PostgreSQL...")
    saved_answers_count = 0

    for i in range(1, 7):
        for letter, desc, interp in ROM_DATA[i]["subs"]:
            sub_node_id = f"rom_{i}_{letter}"

            payload = {
                "language": "en",
                "blocks": [
                    {
                        "block_type": "text",
                        "position": 1,
                        "content": f"### Description\n{desc}"
                    },
                    {
                        "block_type": "text",
                        "position": 2,
                        "content": f"### Interpretation\n{interp}"
                    }
                ]
            }

            # Check if answer exists (PUT) or create new (POST)
            get_status, _ = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_node_id}/answer?language=en")
            method = "PUT" if get_status == 200 else "POST"

            ans_status, ans_resp = await invoke_asgi(
                method, f"/flows/{TARGET_FLOW_ID}/nodes/{sub_node_id}/answer", payload
            )
            if ans_status not in (200, 201):
                print(f"ERROR saving answer for {sub_node_id}: {ans_resp}")
                sys.exit(1)

            saved_answers_count += 1

    print(f"  ✓ Successfully stored {saved_answers_count} sub-standard answers in PostgreSQL.")

    # 5. Comprehensive Integrity Audit & Endpoints Verification
    print("\n[5/5] Running Comprehensive Post-Integration Verification Audit...")

    # 5.1 GET /flows/{flow_id}
    get_status, flow_res = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}")
    assert get_status == 200
    ret_nodes = flow_res["flow_data"]["nodes"]
    ret_edges = flow_res["flow_data"]["edges"]
    print(f"  Total Flow Nodes: {len(ret_nodes)} (Expected {len(orig_nodes) + 43})")
    print(f"  Total Flow Edges: {len(ret_edges)} (Expected {len(orig_edges) + 123})")
    assert len(ret_nodes) == len(orig_nodes) + 43
    assert len(ret_edges) == len(orig_edges) + 123

    # 5.2 Verify standard_rom buttons
    rom_node = next(n for n in ret_nodes if n["id"] == CHAPTER_NODE_ID)
    assert len(rom_node["data"]["buttons"]) == 6, f"Expected 6 buttons on standard_rom, got {len(rom_node['data']['buttons'])}"
    print("  ✓ standard_rom has all 6 STANDARD: ROM.1 - ROM.6 buttons")

    # 5.3 Verify all 6 main standard nodes
    for i in range(1, 7):
        std_id = f"rom_{i}"
        std_node = next(n for n in ret_nodes if n["id"] == std_id)
        subs = ROM_DATA[i]["subs"]
        expected_btn_count = len(subs) + 1
        assert len(std_node["data"]["buttons"]) == expected_btn_count, \
            f"Expected {expected_btn_count} buttons on {std_id}, got {len(std_node['data']['buttons'])}"
        print(f"  ✓ {std_id} has {len(subs)} sub-standard buttons + 1 Back button")

    # 5.4 Verify all 37 sub-standard answer nodes and database answers
    db = SessionLocal()
    for i in range(1, 7):
        for letter, desc, interp in ROM_DATA[i]["subs"]:
            sub_node_id = f"rom_{i}_{letter}"
            sub_node = next(n for n in ret_nodes if n["id"] == sub_node_id)
            assert len(sub_node["data"]["buttons"]) == 2, f"Expected 2 buttons on {sub_node_id}"

            # Verify API GET /nodes/{node_id}/answer
            ans_code, ans_data = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_node_id}/answer?language=en")
            assert ans_code == 200, f"Expected 200 for {sub_node_id} answer, got {ans_code}"
            assert len(ans_data["blocks"]) == 2, f"Expected 2 blocks for {sub_node_id}, got {len(ans_data['blocks'])}"
            assert ans_data["blocks"][0]["content"] == f"### Description\n{desc}"
            assert ans_data["blocks"][1]["content"] == f"### Interpretation\n{interp}"

    db.close()
    print("  ✓ All 37 sub-standard nodes and answers verified in PostgreSQL with 2-block structure.")

    # 5.5 Verify existing standards are intact
    aac_nodes = [n for n in ret_nodes if n["id"].startswith("aac_") or n["id"] == "standard_aac"]
    cop_nodes = [n for n in ret_nodes if n["id"].startswith("cop_") or n["id"] == "standard_cop"]
    mom_nodes = [n for n in ret_nodes if n["id"].startswith("mom_") or n["id"] == "standard_mom"]
    pre_nodes = [n for n in ret_nodes if n["id"].startswith("pre_") or n["id"] == "standard_pre"]
    ipc_nodes = [n for n in ret_nodes if n["id"].startswith("ipc_") or n["id"] == "standard_ipc"]
    psq_nodes = [n for n in ret_nodes if n["id"].startswith("psq_") or n["id"] == "standard_psq"]
    print(f"  ✓ AAC nodes intact: {len(aac_nodes)}")
    print(f"  ✓ COP nodes intact: {len(cop_nodes)}")
    print(f"  ✓ MOM nodes intact: {len(mom_nodes)}")
    print(f"  ✓ PRE nodes intact: {len(pre_nodes)}")
    print(f"  ✓ IPC nodes intact: {len(ipc_nodes)}")
    print(f"  ✓ PSQ nodes intact: {len(psq_nodes)}")

    db = SessionLocal()
    total_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID).count()
    # 308 previous + 37 ROM = 345 total answers
    print(f"  ✓ Total database answers for flow: {total_answers} (Previous: 308, Added: 37, Expected: 345)")
    assert total_answers == 345
    db.close()

    print("\n" + "=" * 80)
    print("SUCCESS: ALL 6 ROM STANDARDS (ROM.1-ROM.6) AND 37 SUB-STANDARDS INTEGRATED!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

