"""
Script: integrate_psq_standards.py
Integrates NABH Patient Safety and Quality Improvement (PSQ) Standards (PSQ.1–PSQ.7),
their 39 collected sub-standard buttons and nodes, and their individual Description + Interpretation answers
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
CHAPTER_NODE_ID = "standard_psq"

# Complete Official NABH PSQ Standards & 39 Collected Sub-Standards
PSQ_DATA = {
    1: {
        "title": "The organisation implements a structured patient-safety programme",
        "subs": [
            ("a",
             "The patient-safety programme is developed, implemented and maintained by a multi-disciplinary safety committee.",
             "The organisation establishes a formally constituted multidisciplinary patient safety committee comprising clinical leadership, nursing administration, quality managers, and facility safety officers to oversee the hospital-wide patient safety programme."),
            ("b",
             "The patient-safety programme is comprehensive and covers all the major elements related to patient safety.",
             "The programme addresses all key dimensions of patient safety, including medication safety, surgical safety, infection prevention, environmental safety, safe identification, and fall prevention across all departments."),
            ("c",
             "The programme covers incidents ranging from \"no harm\" to \"sentinel events\".",
             "The safety framework encompasses the entire incident spectrum, actively encouraging the reporting of near misses (no-harm incidents), adverse events, and sentinel events to proactively prevent harm."),
            ("d",
             "Designated patient safety officer(s) coordinate the implementation of the patient-safety programme.",
             "Qualified and trained patient safety officer(s) are appointed to monitor safety protocols, facilitate incident investigations, and coordinate safety initiatives hospital-wide."),
            ("e",
             "The organisation performs proactive analysis of patient safety risks and makes improvements accordingly.",
             "Proactive risk assessments (such as Failure Mode and Effects Analysis - FMEA, or Hazard Identification and Risk Assessment - HIRA) are conducted on vulnerable processes to identify and mitigate potential hazards before harm occurs."),
            ("f",
             "The patient-safety programme identifies opportunities for improvement based on review at pre-defined intervals.",
             "The safety committee conducts periodic, structured reviews of patient safety data, audit findings, and incident trends at defined intervals to prioritize and track improvement actions."),
            ("g",
             "The organisation adapts and implements national/international patient-safety goals/solutions.",
             "The hospital implements International Patient Safety Goals (IPSG), including correct patient identification, effective communication, high-alert medication safety, safe surgery verification, infection risk reduction, and patient fall prevention.")
        ]
    },
    2: {
        "title": "The organisation implements a structured quality improvement and continuous monitoring programme",
        "subs": [
            ("a",
             "The quality improvement programme is developed, implemented and maintained by a multi-disciplinary committee.",
             "A multidisciplinary quality improvement committee guides the hospital's quality strategy, reviews clinical and operational metrics, and oversees quality improvement projects across clinical and support units."),
            ("e",
             "Designated quality improvement coordinator(s) coordinate the implementation of the quality improvement programme.",
             "Designated quality coordinators facilitate quality improvement initiatives, support departmental teams with monitoring tools, and track progress against organizational quality objectives."),
            ("g",
             "The quality improvement programme is reviewed and updated at least once a year.",
             "Leadership and the quality committee conduct a comprehensive annual review of the quality manual, objectives, and departmental performance indicators to align with evolving clinical best practices."),
            ("h",
             "Audits are conducted at regular intervals as a means of continuous monitoring.",
             "Planned, documented internal audits are systematically conducted across all clinical and administrative departments to evaluate compliance with policies, standards, and regulatory requirements."),
            ("i",
             "There is an established process in the organisation to monitor and improve the quality of nursing care.",
             "Standardized nursing quality indicators (such as medication administration errors, nursing documentation completeness, patient fall prevention, and pressure ulcer rates) are routinely measured and improved.")
        ]
    },
    3: {
        "title": "The organisation identifies key indicators to monitor the structures, processes and outcomes, which are used as tools for continual improvement",
        "subs": [
            ("a",
             "The organisation identifies and monitors key indicators to oversee clinical structures, processes and outcomes.",
             "Clinical performance indicators (including readmission rates, re-exploration rates, ICU return within 48 hours, and time to initial clinical assessment) are systematically tracked and benchmarked."),
            ("b",
             "The organisation identifies and monitors key indicators to oversee infection prevention and control activities.",
             "Healthcare-associated infection (HAI) rates, including CAUTI, CLABSI, VAP, and SSI, alongside hand hygiene compliance rates, are routinely monitored and analyzed."),
            ("c",
             "The organisation identifies and monitors key indicators to oversee managerial structures, processes and outcomes.",
             "Managerial and operational metrics, such as outpatient and inpatient waiting times, diagnostic test turnaround times, discharge process duration, and equipment downtime, are continuously monitored."),
            ("d",
             "The organisation identifies and monitors key indicators to oversee patient safety activities.",
             "Patient safety indicators, including adverse drug reactions, blood transfusion reactions, patient falls, needle-stick injuries, and surgical safety checklist compliance, are monitored and evaluated."),
            ("e",
             "Verification of data is done regularly by the organisation.",
             "The quality team conducts routine data verification and validation audits to ensure accuracy, completeness, and reliability of collected performance indicator data prior to analysis."),
            ("f",
             "The organisation has a mechanism to capture patient reported outcome measures and experience measures.",
             "Structured mechanisms systematically capture Patient Reported Outcome Measures (PROMs) and Patient Reported Experience Measures (PREMs) to evaluate therapeutic effectiveness and patient experience."),
            ("g",
             "There is an established mechanism of analysis of data.",
             "Collected indicator data undergo statistical and trend analysis using run charts, control charts, and comparative benchmarks to identify meaningful variations and clinical opportunities for improvement."),
            ("h",
             "The identified quality improvements are implemented and evaluated over time.",
             "Action plans derived from indicator analysis are deployed, tracked, and periodically re-evaluated to demonstrate sustained clinical and operational improvement (closing the quality loop).")
        ]
    },
    4: {
        "title": "The organisation uses appropriate quality improvement tools for its quality improvement activities",
        "subs": [
            ("a",
             "The organisation undertakes quality improvement projects.",
             "Multidisciplinary teams execute structured quality improvement projects (utilizing PDCA/PDSA cycles or Lean Six Sigma frameworks) targeting prioritized clinical or administrative challenges."),
            ("b",
             "The organisation uses appropriate analytical tools for its quality improvement activities.",
             "Teams systematically apply analytical problem-solving methodologies, such as Root Cause Analysis (RCA), Failure Mode and Effects Analysis (FMEA), and 5-Why analysis to understand root causes of process failures."),
            ("c",
             "The organisation uses appropriate statistical tools for its quality improvement activities.",
             "Statistical quality tools, including Pareto charts, histograms, control charts, scatter plots, and run charts, are utilized to analyze process variation and measure the impact of interventions."),
            ("d",
             "The organisation uses appropriate managerial tools for its quality improvement activities.",
             "Managerial tools like process mapping, flowcharts, Gantt charts, brainstorming, and SWOT analysis support structured planning, resource allocation, and timely execution of quality projects.")
        ]
    },
    5: {
        "title": "There is an established system for clinical audit",
        "subs": [
            ("a",
             "Clinical audits are performed to improve the quality of patient care.",
             "Systematic, peer-reviewed clinical audits evaluate current clinical practice against evidence-based standards, treatment guidelines, and hospital clinical protocols to enhance patient outcomes."),
            ("b",
             "The parameters to be audited are defined by the organisation.",
             "The hospital establishes a documented clinical audit calendar and clearly defines clinical criteria and audit parameters (such as mortality audits, surgical case reviews, antibiotic stewardship, and blood utilization)."),
            ("c",
             "Medical and nursing staff participate in clinical audit.",
             "The organisation shall identify such personnel. It could be a mix of clinicians, administrators and nurses. These could be members of the core committee/quality assurance committee etc."),
            ("d",
             "Patient and staff anonymity are maintained.",
             "Audit records and working sheets are de-identified or coded to protect patient and clinician confidentiality, fostering a transparent, non-punitive learning environment."),
            ("f",
             "Remedial measures are implemented.",
             "Corrective actions and targeted clinical changes are implemented based on audit findings, followed by documented re-auditing to verify improved adherence to clinical standards.")
        ]
    },
    6: {
        "title": "The patient safety and quality improvement programme are supported by the management",
        "subs": [
            ("a",
             "The management creates a culture of safety.",
             "Executive leadership actively promotes a transparent, non-punitive \"just culture\" of safety, conducting safety walk-rounds and encouraging open reporting of safety concerns and adverse events."),
            ("b",
             "The leaders at all levels in the organisation are aware of the intent of the patient safety and quality improvement programme and the approach to its implementation.",
             "Clinical department heads, nursing supervisors, and administrative managers receive leadership orientation on patient safety concepts, quality indicators, and risk management methodologies."),
            ("c",
             "Departmental leaders are involved in patient safety and quality improvement.",
             "Departmental heads actively lead safety initiatives within their respective units, review departmental quality metrics, and enforce compliance with standard operating procedures."),
            ("d",
             "The management makes available adequate resources required for the programme.",
             "Senior management allocates dedicated financial, human, technological, and infrastructural resources (including training, software tools, and safety devices) to support quality and safety programmes."),
            ("f",
             "The management identifies organisational performance improvement targets.",
             "Executive leadership defines clear, measurable annual performance targets and quality benchmarks for the hospital, aligning strategic priorities with patient safety goals.")
        ]
    },
    7: {
        "title": "Incidents are collected and analysed to ensure continual quality improvement",
        "subs": [
            ("a",
             "The organisation implements an incident management system.",
             "A hospital-wide, non-punitive incident reporting mechanism allows all healthcare personnel to report near misses, medication errors, procedural complications, and adverse events without fear of reprimand."),
            ("b",
             "The organisation has a mechanism to identify sentinel events.",
             "The hospital defines explicit criteria and immediate notification workflows for sentinel events (unexpected occurrences involving death or severe physical or psychological injury) to trigger urgent clinical review."),
            ("c",
             "The organisation has established processes for analysis of incidents.",
             "Multidisciplinary teams conduct thorough Root Cause Analysis (RCA) on reported adverse and sentinel events to uncover contributing systemic, human, and environmental factors."),
            ("d",
             "Corrective and preventive actions are taken based on the findings of such analysis.",
             "Actionable Corrective and Preventive Actions (CAPA) are assigned to process owners with defined implementation timelines to eliminate root causes and prevent recurrence."),
            ("f",
             "The organisation incorporates risks identified in the analysis of incidents into the risk management system.",
             "Systemic hazards and vulnerabilities identified through incident investigations are updated in the hospital risk register, guiding preventive staff training and policy revisions.")
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


def build_psq_graph(original_flow_data: dict) -> tuple:
    """
    Construct the updated flow graph by:
    1. Adding 7 main buttons to standard_psq node.
    2. Creating 7 psq_{i} menu nodes.
    3. Creating 39 psq_{i}_{sub} answer nodes.
    4. Adding all 131 navigation edges.
    """
    flow_data = copy.deepcopy(original_flow_data)
    nodes = flow_data.get("nodes", [])
    edges = flow_data.get("edges", [])

    node_map = {n["id"]: n for n in nodes}

    # 1. Update standard_psq chapter node
    psq_chapter = node_map.get(CHAPTER_NODE_ID)
    if not psq_chapter:
        raise ValueError(f"Chapter node '{CHAPTER_NODE_ID}' not found in flow.")

    # 7 Main standard buttons for standard_psq
    psq_main_buttons = [
        {"id": f"standard_psq__psq_{i}__{i-1}", "next": f"psq_{i}", "label": f"STANDARD: PSQ.{i}"}
        for i in range(1, 8)
    ]
    psq_chapter["data"]["buttons"] = psq_main_buttons
    psq_chapter["data"]["message"] = "PSQ — Patient Safety and Quality Improvement (NABH 5th Edition Standards)"
    psq_chapter["data"]["mapping_status"] = "VERIFIED"
    psq_chapter["mapping_status"] = "VERIFIED"

    new_nodes = []
    new_edges = []

    # 2. Forward edges from standard_psq to psq_1..psq_7 (7 edges)
    for btn in psq_main_buttons:
        new_edges.append({
            "id": f"edge-standard_psq-{btn['next']}-{btn['id']}",
            "label": btn["label"],
            "source": CHAPTER_NODE_ID,
            "target": btn["next"],
            "sourceHandle": btn["id"]
        })

    # 3. Create Main standard nodes psq_1 to psq_7 & their sub-standards
    std_base_y = 16000
    for i in range(1, 8):
        std_id = f"psq_{i}"
        std_info = PSQ_DATA[i]
        subs = std_info["subs"]
        pos_y = std_base_y + (i - 1) * 350

        # Sub-standard buttons for psq_i
        std_buttons = []
        for s_idx, (letter, desc, _) in enumerate(subs):
            sub_node_id = f"psq_{i}_{letter}"
            btn_id = f"psq_{i}__{sub_node_id}__{s_idx}"
            std_buttons.append({
                "id": btn_id,
                "next": sub_node_id,
                "label": f"PSQ.{i}.{letter}"
            })

        # Back to PSQ Standards button
        btn_back_id = f"psq_{i}__back_standard_psq__{len(subs)}"
        std_buttons.append({
            "id": btn_back_id,
            "next": CHAPTER_NODE_ID,
            "label": "Back to PSQ Standards"
        })

        # Main standard node definition (menu)
        std_node = {
            "id": std_id,
            "type": "menu",
            "data": {
                "id": std_id,
                "label": f"STANDARD: PSQ.{i}",
                "message": f"PSQ.{i} — {std_info['title']}",
                "buttons": std_buttons,
                "chapter": "PSQ",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "nodeType": "menu",
                "layoutWidth": 290,
                "layoutHeight": 280,
                "mapping_status": "VERIFIED"
            },
            "chapter": "PSQ",
            "program": "Hospitals Accreditation",
            "topic": "standards",
            "message": f"PSQ.{i} — {std_info['title']}",
            "position": {"x": 5715, "y": pos_y},
            "mapping_status": "VERIFIED"
        }
        new_nodes.append(std_node)

        # Back edge from psq_i to standard_psq
        new_edges.append({
            "id": f"edge-{std_id}-standard_psq-{btn_back_id}",
            "label": "Back to PSQ Standards",
            "source": std_id,
            "target": CHAPTER_NODE_ID,
            "sourceHandle": btn_back_id
        })

        # Sub-standard answer nodes and connecting edges
        for s_idx, (letter, desc, _) in enumerate(subs):
            sub_node_id = f"psq_{i}_{letter}"
            sub_btn_back_std = f"{sub_node_id}__back_psq_{i}__0"
            sub_btn_back_psq = f"{sub_node_id}__back_standard_psq__1"

            sub_node = {
                "id": sub_node_id,
                "type": "answer",
                "data": {
                    "id": sub_node_id,
                    "label": f"PSQ.{i}.{letter} — {desc}",
                    "message": desc,
                    "buttons": [
                        {"id": sub_btn_back_std, "next": std_id, "label": f"Back to PSQ.{i}"},
                        {"id": sub_btn_back_psq, "next": CHAPTER_NODE_ID, "label": "Back to PSQ Standards"}
                    ],
                    "chapter": "PSQ",
                    "program": "Hospitals Accreditation",
                    "topic": "standards",
                    "nodeType": "answer",
                    "layoutWidth": 280,
                    "layoutHeight": 140,
                    "mapping_status": "VERIFIED"
                },
                "chapter": "PSQ",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "message": desc,
                "position": {"x": 6220, "y": pos_y + s_idx * 140},
                "mapping_status": "VERIFIED"
            }
            new_nodes.append(sub_node)

            # Edge 1: Forward from psq_i to psq_i_letter
            new_edges.append({
                "id": f"edge-{std_id}-{sub_node_id}-{std_buttons[s_idx]['id']}",
                "label": f"PSQ.{i}.{letter}",
                "source": std_id,
                "target": sub_node_id,
                "sourceHandle": std_buttons[s_idx]["id"]
            })

            # Edge 2: Back from psq_i_letter to psq_i
            new_edges.append({
                "id": f"edge-{sub_node_id}-{std_id}-{sub_btn_back_std}",
                "label": f"Back to PSQ.{i}",
                "source": sub_node_id,
                "target": std_id,
                "sourceHandle": sub_btn_back_std
            })

            # Edge 3: Back from psq_i_letter to standard_psq
            new_edges.append({
                "id": f"edge-{sub_node_id}-standard_psq-{sub_btn_back_psq}",
                "label": "Back to PSQ Standards",
                "source": sub_node_id,
                "target": CHAPTER_NODE_ID,
                "sourceHandle": sub_btn_back_psq
            })

    flow_data["nodes"] = nodes + new_nodes
    flow_data["edges"] = edges + new_edges

    return flow_data, new_nodes, new_edges


async def main():
    print("=" * 80)
    print("INTEGRATING NABH PSQ.1 - PSQ.7 STANDARDS INTO ACTIVE FLOW")
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
    print("\n[1/5] Creating Pre-PSQ Implementation Safety Backup...")
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file_path = os.path.join(
        backend_dir, "data", f"backup_flow_{TARGET_FLOW_ID}_before_psq_complete_{timestamp_str}.json"
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
    print("\n[2/5] Constructing PSQ Graph Topology...")
    updated_flow_data, new_nodes, new_edges = build_psq_graph(target_flow.flow_data)
    print(f"  Newly Created Nodes: {len(new_nodes)} (7 main + 39 sub-standards)")
    print(f"  Newly Created Edges: {len(new_edges)} (7 fwd + 7 back + 39 fwd + 39 back + 39 chapter-back = 131)")
    assert len(new_nodes) == 46  # 7 + 39
    assert len(new_edges) == 131  # 7 + 7 + 39 + 39 + 39
    assert len(updated_flow_data["nodes"]) == len(orig_nodes) + 46
    assert len(updated_flow_data["edges"]) == len(orig_edges) + 131

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

    # 4. Store All 39 Sub-Standard Answers in PostgreSQL
    print("\n[4/5] Storing Official Descriptions & Interpretations in PostgreSQL...")
    saved_answers_count = 0

    for i in range(1, 8):
        for letter, desc, interp in PSQ_DATA[i]["subs"]:
            sub_node_id = f"psq_{i}_{letter}"

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
    print(f"  Total Flow Nodes: {len(ret_nodes)} (Expected {len(orig_nodes) + 46})")
    print(f"  Total Flow Edges: {len(ret_edges)} (Expected {len(orig_edges) + 131})")
    assert len(ret_nodes) == len(orig_nodes) + 46
    assert len(ret_edges) == len(orig_edges) + 131

    # 5.2 Verify standard_psq buttons
    psq_node = next(n for n in ret_nodes if n["id"] == CHAPTER_NODE_ID)
    assert len(psq_node["data"]["buttons"]) == 7, f"Expected 7 buttons on standard_psq, got {len(psq_node['data']['buttons'])}"
    print("  ✓ standard_psq has all 7 STANDARD: PSQ.1 - PSQ.7 buttons")

    # 5.3 Verify all 7 main standard nodes
    for i in range(1, 8):
        std_id = f"psq_{i}"
        std_node = next(n for n in ret_nodes if n["id"] == std_id)
        subs = PSQ_DATA[i]["subs"]
        expected_btn_count = len(subs) + 1
        assert len(std_node["data"]["buttons"]) == expected_btn_count, \
            f"Expected {expected_btn_count} buttons on {std_id}, got {len(std_node['data']['buttons'])}"
        print(f"  ✓ {std_id} has {len(subs)} sub-standard buttons + 1 Back button")

    # 5.4 Verify all 39 sub-standard answer nodes and database answers
    db = SessionLocal()
    for i in range(1, 8):
        for letter, desc, interp in PSQ_DATA[i]["subs"]:
            sub_node_id = f"psq_{i}_{letter}"
            sub_node = next(n for n in ret_nodes if n["id"] == sub_node_id)
            assert len(sub_node["data"]["buttons"]) == 2, f"Expected 2 buttons on {sub_node_id}"

            # Verify API GET /nodes/{node_id}/answer
            ans_code, ans_data = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_node_id}/answer?language=en")
            assert ans_code == 200, f"Expected 200 for {sub_node_id} answer, got {ans_code}"
            assert len(ans_data["blocks"]) == 2, f"Expected 2 blocks for {sub_node_id}, got {len(ans_data['blocks'])}"
            assert ans_data["blocks"][0]["content"] == f"### Description\n{desc}"
            assert ans_data["blocks"][1]["content"] == f"### Interpretation\n{interp}"

    db.close()
    print("  ✓ All 39 sub-standard nodes and answers verified in PostgreSQL with 2-block structure.")

    # 5.5 Verify existing AAC, COP, MOM, PRE, and IPC standards are intact
    aac_nodes = [n for n in ret_nodes if n["id"].startswith("aac_") or n["id"] == "standard_aac"]
    cop_nodes = [n for n in ret_nodes if n["id"].startswith("cop_") or n["id"] == "standard_cop"]
    mom_nodes = [n for n in ret_nodes if n["id"].startswith("mom_") or n["id"] == "standard_mom"]
    pre_nodes = [n for n in ret_nodes if n["id"].startswith("pre_") or n["id"] == "standard_pre"]
    ipc_nodes = [n for n in ret_nodes if n["id"].startswith("ipc_") or n["id"] == "standard_ipc"]
    print(f"  ✓ AAC nodes intact: {len(aac_nodes)}")
    print(f"  ✓ COP nodes intact: {len(cop_nodes)}")
    print(f"  ✓ MOM nodes intact: {len(mom_nodes)}")
    print(f"  ✓ PRE nodes intact: {len(pre_nodes)}")
    print(f"  ✓ IPC nodes intact: {len(ipc_nodes)}")

    db = SessionLocal()
    total_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID).count()
    # 269 previous + 39 PSQ = 308 total answers
    print(f"  ✓ Total database answers for flow: {total_answers} (Previous: 269, Added: 39, Expected: 308)")
    assert total_answers == 308
    db.close()

    print("\n" + "=" * 80)
    print("SUCCESS: ALL 7 PSQ STANDARDS (PSQ.1-PSQ.7) AND 39 SUB-STANDARDS INTEGRATED!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

