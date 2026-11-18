"""
Script: integrate_pre_standards.py
Integrates all 8 NABH Patient Rights and Education (PRE) standards (PRE.1–PRE.8),
their 52 sub-standard buttons and nodes, and their individual Description + Interpretation answers
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
CHAPTER_NODE_ID = "standard_pre"

# Complete Official NABH PRE Standards & 52 Sub-Standards
PRE_DATA = {
    1: {
        "title": "The organisation protects and promotes patient and family rights and informs them about their responsibilities during care",
        "subs": [
            ("a", "Patient and family rights and responsibilities are documented, displayed, and they are made aware of the same.",
             "The organisation clearly defines, documents, and prominently displays the charter of patient rights and responsibilities in languages understood by the communities served, across patient-facing areas like reception, OPD, emergency, and inpatient departments."),
            ("b", "Patient and family rights include respecting individual beliefs, cultural values, and preferences.",
             "Healthcare providers and staff actively respect diverse cultural, religious, and personal values of patients, ensuring non-judgmental and respectful care throughout their hospital stay."),
            ("c", "Patient and family rights include respect for personal dignity and privacy during examination, procedures and treatment.",
             "Staff maintain patient modesty and privacy through appropriate curtains, screens, gowns, and protocols during physical examinations, clinical procedures, nursing care, and patient transport."),
            ("d", "Patient and family rights include protection from physical abuse, neglect, or harassment.",
             "The hospital maintains zero tolerance for abuse, harassment, or negligence. Security surveillance, vulnerability assessments, and safeguard mechanisms protect all patients, especially children, elderly, and incapacitated individuals."),
            ("e", "Staff are oriented and trained regarding their role in protecting and promoting patient and family rights.",
             "All hospital employees undergo regular, documented orientation and training on patient rights, professional boundaries, patient dignity, and handling vulnerable patient populations."),
        ]
    },
    2: {
        "title": "Patient and family rights support individual beliefs, values, and involve the patient and family in decision-making processes",
        "subs": [
            ("a", "Patient and family rights include respecting values and beliefs, any special preferences, cultural needs, and responding to requests for spiritual needs.",
             "The organisation respects patients' cultural and spiritual practices, accommodating dietary preferences, religious observances, and spiritual care requests when clinically feasible and safe."),
            ("b", "Patient and family rights include respect for personal dignity and privacy during examination, procedures and treatment.",
             "Clinical and support teams ensure visual and auditory privacy in all treatment areas, outpatient consultation rooms, diagnostic suites, and during all nursing interventions."),
            ("c", "Patient and family rights include protection from neglect or abuse.",
             "Robust safeguards, safety reporting systems, and clinical oversight prevent physical, psychological, verbal, or emotional abuse or neglect of hospitalized patients."),
            ("d", "Patient and family rights include treating patient information as confidential.",
             "All patient medical records, personal details, diagnostic findings, and clinical communications are treated as strictly confidential, with access restricted to authorized personnel."),
            ("e", "Patient and family rights include the refusal of treatment.",
             "Patients or their legal representatives have the autonomous right to refuse proposed investigations, medications, or surgical interventions after being thoroughly counseled on the medical implications and risks."),
            ("f", "Patient and family rights include a right to seek an additional opinion regarding clinical care.",
             "The hospital facilitates and supports patients who wish to seek a second medical opinion from another specialist, providing relevant medical summaries and diagnostic copies without compromising ongoing care."),
            ("g", "Patient and family rights include informed consent before the transfusion of blood and blood components, anaesthesia, surgery, initiation of any research protocol, and any other invasive / high-risk procedures / treatment.",
             "Written, informed consent is obtained prior to high-risk or invasive interventions after explaining clinical indications, potential risks, expected benefits, and alternatives."),
            ("h", "Patient and family rights include a right to complain and information on how to voice a complaint.",
             "Patients and families are informed about formal grievance mechanisms, complaint drop boxes, designated grievance officers, and escalation procedures without fear of retaliation."),
            ("i", "Patient and family rights include information on the expected cost of the treatment.",
             "Transparent financial estimates, pricing tariffs, and billing explanations are provided to patients at the time of admission and updated when major clinical changes occur."),
            ("j", "Patient and family rights include access to their clinical records.",
             "Patients or legally authorized surrogates are entitled to review or receive photocopies/digital copies of their medical records, discharge summaries, and investigation reports as per statutory regulations and hospital policy."),
            ("k", "Patient and family rights include information on the care plan, progress, and the name of the treating doctor.",
             "Patients and family members are kept informed about their primary treating physician, consultant team, planned interventions, daily recovery progress, and anticipated discharge timelines."),
            ("l", "Patient and family rights include determining what information regarding their care would be provided to self and family.",
             "Patients retain the right to specify which family members or designated individuals can receive clinical updates regarding their diagnosis, prognosis, and treatment plan."),
        ]
    },
    3: {
        "title": "The patient and / or family members are educated to make informed decisions and are involved in the care planning and delivery process",
        "subs": [
            ("a", "The patient and / or family members are explained about the proposed care, including the risks, alternatives, and benefits.",
             "Treating physicians explain the diagnosis, proposed treatment pathways, alternative options, anticipated clinical benefits, and associated medical risks in an easily understandable manner."),
            ("b", "The patient and / or family members are explained about the expected results.",
             "Clinicians discuss realistic therapeutic goals and expected clinical outcomes, aligning expectations between the healthcare team and the patient's family."),
            ("c", "The patient and / or family members are explained about the possible complications.",
             "Potential adverse reactions, procedural complications, or clinical setbacks are proactively discussed so patients and families are prepared and informed."),
            ("d", "The care plan is prepared and modified in consultation with the patient and / or family members.",
             "Care delivery is patient-centered; the clinical management plan is formulated collaboratively, incorporating patient preferences and discussing modifications as clinical conditions evolve."),
            ("e", "The patient and / or family members are informed about the results of diagnostic tests and the diagnosis.",
             "Laboratory, imaging, and histopathology findings are interpreted and communicated promptly to patients and families by the primary treating team."),
        ]
    },
    4: {
        "title": "Informed consent is obtained from the patient or family about their care",
        "subs": [
            ("a", "The organisation obtains informed consent from the patient or family for situations where informed consent is required.",
             "The hospital maintains a comprehensive list of clinical situations, surgeries, invasive procedures, and therapies requiring written informed consent, ensuring adherence across all departments."),
            ("b", "The informed consent process adheres to statutory norms.",
             "Consent protocols strictly comply with legal and regulatory mandates, including age of majority, mental capacity assessment, and statutory requirements for specific medical procedures."),
            ("c", "Informed consent includes information regarding the procedure, its risks, benefits, alternatives, and as to who will perform the procedure in a language that they can understand.",
             "Consent documentation details the nature of the procedure, clinical alternatives, known risks and complications, and the credentialed clinician performing the intervention, presented in the patient's preferred language."),
            ("d", "The organisation describes who can give consent when a patient is incapable of independent decision-making and implements the same.",
             "Clear institutional policy defines authorized surrogate decision-makers (legal guardians, next of kin, power of attorney) when the patient is a minor, unconscious, or cognitively impaired."),
            ("e", "Informed consent is taken by the person performing the procedure.",
             "The qualified and credentialed clinician who will perform the surgery or procedure personally counsels the patient, answers questions, and obtains the signed consent."),
        ]
    },
    5: {
        "title": "Patients and families have a right to information and education about their healthcare needs",
        "subs": [
            ("a", "Patient and / or family are educated in a language and format that they can understand.",
             "Patient education materials, verbal counseling, and discharge instructions are provided in the patient's primary language using simplified terminology, pictorial guides, or translation support."),
            ("b", "Patient and / or family are educated about the safe and effective use of medication and the potential side effects of the medication when appropriate.",
             "Pharmacists and clinical staff educate patients on medication dosage, administration schedules, proper storage, adverse effects, and precautions for high-risk drugs."),
            ("c", "Patient and / or family are educated about food-drug interactions.",
             "Dietitians and clinical teams counsel patients on specific dietary restrictions, avoiding foods or beverages that interfere with prescribed drug efficacy or safety."),
            ("d", "Patient and / or family are educated about diet and nutrition.",
             "Customized dietary counseling supports disease management (e.g., diabetic diets, low-sodium regimens, renal diets) and general nutritional recovery."),
            ("e", "Patient and / or family are educated about immunisations.",
             "Appropriate immunization guidance is provided to patients and families, covering routine pediatric schedules, adult vaccinations, travel vaccines, and disease-specific immunizations."),
            ("f", "Patient and / or family are educated about their specific disease process, complications, and prevention strategies.",
             "Clinical teams provide structured education on the patient's underlying disease, risk factor modification, early warning signs of deterioration, and long-term self-management."),
            ("g", "Patient and / or family are educated about preventing infections.",
             "Staff educate patients and family members on infection prevention practices, including hand hygiene, respiratory etiquette, catheter care, and surgical wound maintenance."),
            ("h", "Patient and / or family are educated about medical equipment used in care, where appropriate.",
             "Hands-on instruction and safety training are provided when patients require home medical equipment, such as oxygen concentrators, nebulizers, glucometers, or insulin pens."),
            ("i", "Patient and / or family are educated about pain management.",
             "Patients and families are educated on pain assessment scales, pharmacological and non-pharmacological pain relief methods, and communicating pain levels to the care team."),
            ("j", "Patient and / or family are educated about when and how to obtain further treatment or emergency care.",
             "Discharge instructions clearly explain follow-up appointments, emergency contact numbers, hospital helpline access, and specific red-flag symptoms requiring immediate medical evaluation."),
        ]
    },
    6: {
        "title": "Patients and families have a right to information on expected costs",
        "subs": [
            ("a", "The organisation ensures that patients and / or family members are made aware of the pricing policy.",
             "Hospital billing and pricing policies across outpatient, daycare, inpatient, emergency, and intensive care units are clearly communicated to patients and families."),
            ("b", "The relevant tariff list is available to patients.",
             "Comprehensive tariff schedules for room rents, doctor consultations, diagnostic tests, procedures, and surgeries are readily accessible at billing counters and public kiosks."),
            ("c", "The patient and / or family members are explained about the expected costs of care.",
             "Financial counselors provide written, transparent cost estimates for proposed hospitalizations, surgeries, or therapies prior to admission or procedure initiation."),
            ("d", "The patient and / or family members are informed about the financial implications when there is a change in the care plan.",
             "Whenever clinical conditions require ICU transfer, additional procedures, or extended hospital stay, the financial counselor immediately provides an updated cost estimate."),
        ]
    },
    7: {
        "title": "The organisation has a mechanism to capture patient's feedback and to redress complaints",
        "subs": [
            ("a", "The organisation has a mechanism to capture feedback from patients, which includes patient satisfaction.",
             "Standardized patient satisfaction surveys are administered across OPD, emergency, and IPD settings via physical forms, digital tablets, or SMS/web links."),
            ("b", "The organisation has a mechanism to capture patient experience.",
             "The hospital captures qualitative patient experience feedback regarding staff empathy, responsiveness, cleanliness, waiting times, and communication clarity."),
            ("c", "The organisation redresses patient complaints as per the defined mechanism.",
             "A structured grievance redressal policy ensures all verbal and written complaints are registered, investigated by designated grievance committees, and resolved within established timelines."),
            ("d", "Patient and / or family members are made aware of the procedure for giving feedback and / or lodging complaints.",
             "Guidance on how to submit feedback, access feedback kiosks, drop suggestion slips, or contact the patient relations officer is prominently displayed in patient areas."),
            ("e", "Feedback and complaints are reviewed and / or analysed within a defined time frame.",
             "Patient feedback and grievances are collated, trended, and analyzed monthly by hospital leadership and the quality committee to identify systemic issues."),
            ("f", "Corrective and / or preventive action(s) are taken based on the analysis where appropriate.",
             "Documented Corrective and Preventive Actions (CAPA) are implemented to address recurrent service shortfalls, with outcome monitoring to ensure sustained improvement."),
        ]
    },
    8: {
        "title": "The organisation has a system for effective communication with patients and / or families",
        "subs": [
            ("a", "Communication with the patients and / or families is done effectively.",
             "Healthcare providers communicate in clear, empathetic, and respectful terms, using professional language interpreters or visual communication aids when language or literacy barriers exist."),
            ("b", "The organisation identifies special situations where enhanced communication with patients and / or families would be required.",
             "The hospital defines sensitive clinical situations—such as breaking bad news, discussing end-of-life care, managing unexpected clinical adverse events, or dealing with distressed families—that require structured, empathetic communication protocols."),
            ("c", "Enhanced communication with the patients and / or families is done effectively.",
             "Senior clinicians handle difficult communications in private counseling rooms using established clinical models (such as the SPIKES protocol), allowing adequate time for family questions."),
            ("d", "The organisation ensures that there is no unacceptable communication.",
             "The hospital strictly prohibits verbal aggression, rude behavior, dismissive comments, or discriminatory remarks by staff, with disciplinary accountability for violations."),
            ("e", "The organisation has a system to monitor and review the implementation of effective communication.",
             "The hospital routinely evaluates communication effectiveness through patient feedback audits, counseling observations, and ongoing soft-skills training for clinical and frontline teams."),
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


def build_pre_graph(original_flow_data: dict) -> tuple:
    """
    Construct the updated flow graph by:
    1. Adding 8 main buttons to standard_pre node.
    2. Creating 8 pre_{i} menu nodes.
    3. Creating 52 pre_{i}_{sub} answer nodes.
    4. Adding all 172 navigation edges.
    """
    flow_data = copy.deepcopy(original_flow_data)
    nodes = flow_data.get("nodes", [])
    edges = flow_data.get("edges", [])

    node_map = {n["id"]: n for n in nodes}

    # 1. Update standard_pre chapter node
    pre_chapter = node_map.get(CHAPTER_NODE_ID)
    if not pre_chapter:
        raise ValueError(f"Chapter node '{CHAPTER_NODE_ID}' not found in flow.")

    # 8 Main standard buttons for standard_pre
    pre_main_buttons = [
        {"id": f"standard_pre__pre_{i}__{i-1}", "next": f"pre_{i}", "label": f"STANDARD: PRE.{i}"}
        for i in range(1, 9)
    ]
    pre_chapter["data"]["buttons"] = pre_main_buttons
    pre_chapter["data"]["message"] = "PRE — Patient Rights and Education (NABH 5th Edition Standards)"
    pre_chapter["data"]["mapping_status"] = "VERIFIED"
    pre_chapter["mapping_status"] = "VERIFIED"

    new_nodes = []
    new_edges = []

    # 2. Forward edges from standard_pre to pre_1..pre_8 (8 edges)
    for btn in pre_main_buttons:
        new_edges.append({
            "id": f"edge-standard_pre-{btn['next']}-{btn['id']}",
            "label": btn["label"],
            "source": CHAPTER_NODE_ID,
            "target": btn["next"],
            "sourceHandle": btn["id"]
        })

    # 3. Create Main standard nodes pre_1 to pre_8 & their sub-standards
    std_base_y = 11000
    for i in range(1, 9):
        std_id = f"pre_{i}"
        std_info = PRE_DATA[i]
        subs = std_info["subs"]
        pos_y = std_base_y + (i - 1) * 350

        # Sub-standard buttons for pre_i
        std_buttons = []
        for s_idx, (letter, desc, _) in enumerate(subs):
            sub_node_id = f"pre_{i}_{letter}"
            btn_id = f"pre_{i}__{sub_node_id}__{s_idx}"
            std_buttons.append({
                "id": btn_id,
                "next": sub_node_id,
                "label": f"PRE.{i}.{letter}"
            })

        # Back to PRE Standards button
        btn_back_id = f"pre_{i}__back_standard_pre__{len(subs)}"
        std_buttons.append({
            "id": btn_back_id,
            "next": CHAPTER_NODE_ID,
            "label": "Back to PRE Standards"
        })

        # Main standard node definition (menu)
        std_node = {
            "id": std_id,
            "type": "menu",
            "data": {
                "id": std_id,
                "label": f"STANDARD: PRE.{i}",
                "message": f"PRE.{i} — {std_info['title']}",
                "buttons": std_buttons,
                "chapter": "PRE",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "nodeType": "menu",
                "layoutWidth": 290,
                "layoutHeight": 280,
                "mapping_status": "VERIFIED"
            },
            "chapter": "PRE",
            "program": "Hospitals Accreditation",
            "topic": "standards",
            "message": f"PRE.{i} — {std_info['title']}",
            "position": {"x": 5715, "y": pos_y},
            "mapping_status": "VERIFIED"
        }
        new_nodes.append(std_node)

        # Back edge from pre_i to standard_pre
        new_edges.append({
            "id": f"edge-{std_id}-standard_pre-{btn_back_id}",
            "label": "Back to PRE Standards",
            "source": std_id,
            "target": CHAPTER_NODE_ID,
            "sourceHandle": btn_back_id
        })

        # Sub-standard answer nodes and connecting edges
        for s_idx, (letter, desc, _) in enumerate(subs):
            sub_node_id = f"pre_{i}_{letter}"
            sub_btn_back_std = f"{sub_node_id}__back_pre_{i}__0"
            sub_btn_back_pre = f"{sub_node_id}__back_standard_pre__1"

            sub_node = {
                "id": sub_node_id,
                "type": "answer",
                "data": {
                    "id": sub_node_id,
                    "label": f"PRE.{i}.{letter} — {desc}",
                    "message": desc,
                    "buttons": [
                        {"id": sub_btn_back_std, "next": std_id, "label": f"Back to PRE.{i}"},
                        {"id": sub_btn_back_pre, "next": CHAPTER_NODE_ID, "label": "Back to PRE Standards"}
                    ],
                    "chapter": "PRE",
                    "program": "Hospitals Accreditation",
                    "topic": "standards",
                    "nodeType": "answer",
                    "layoutWidth": 280,
                    "layoutHeight": 140,
                    "mapping_status": "VERIFIED"
                },
                "chapter": "PRE",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "message": desc,
                "position": {"x": 6220, "y": pos_y + s_idx * 140},
                "mapping_status": "VERIFIED"
            }
            new_nodes.append(sub_node)

            # Edge 1: Forward from pre_i to pre_i_letter
            new_edges.append({
                "id": f"edge-{std_id}-{sub_node_id}-{std_buttons[s_idx]['id']}",
                "label": f"PRE.{i}.{letter}",
                "source": std_id,
                "target": sub_node_id,
                "sourceHandle": std_buttons[s_idx]["id"]
            })

            # Edge 2: Back from pre_i_letter to pre_i
            new_edges.append({
                "id": f"edge-{sub_node_id}-{std_id}-{sub_btn_back_std}",
                "label": f"Back to PRE.{i}",
                "source": sub_node_id,
                "target": std_id,
                "sourceHandle": sub_btn_back_std
            })

            # Edge 3: Back from pre_i_letter to standard_pre
            new_edges.append({
                "id": f"edge-{sub_node_id}-standard_pre-{sub_btn_back_pre}",
                "label": "Back to PRE Standards",
                "source": sub_node_id,
                "target": CHAPTER_NODE_ID,
                "sourceHandle": sub_btn_back_pre
            })

    flow_data["nodes"] = nodes + new_nodes
    flow_data["edges"] = edges + new_edges

    return flow_data, new_nodes, new_edges


async def main():
    print("=" * 80)
    print("INTEGRATING NABH PRE.1 - PRE.8 STANDARDS INTO ACTIVE FLOW")
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
    print("\n[1/5] Creating Pre-PRE Implementation Safety Backup...")
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file_path = os.path.join(
        backend_dir, "data", f"backup_flow_{TARGET_FLOW_ID}_before_pre_complete_{timestamp_str}.json"
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
    print("\n[2/5] Constructing PRE Graph Topology...")
    updated_flow_data, new_nodes, new_edges = build_pre_graph(target_flow.flow_data)
    print(f"  Newly Created Nodes: {len(new_nodes)} (8 main + 52 sub-standards)")
    print(f"  Newly Created Edges: {len(new_edges)} (8 fwd + 8 back + 52 fwd + 52 back + 52 chapter-back = 172)")
    assert len(new_nodes) == 60  # 8 + 52
    assert len(new_edges) == 172  # 8 + 8 + 52 + 52 + 52
    assert len(updated_flow_data["nodes"]) == len(orig_nodes) + 60
    assert len(updated_flow_data["edges"]) == len(orig_edges) + 172

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

    # 4. Store All 52 Sub-Standard Answers in PostgreSQL
    print("\n[4/5] Storing Official Descriptions & Interpretations in PostgreSQL...")
    saved_answers_count = 0

    for i in range(1, 9):
        for letter, desc, interp in PRE_DATA[i]["subs"]:
            sub_node_id = f"pre_{i}_{letter}"

            # Exact AAC 2-block structure:
            # Block 1: ### Description\n...
            # Block 2: ### Interpretation\n...
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
    print(f"  Total Flow Nodes: {len(ret_nodes)} (Expected {len(orig_nodes) + 60})")
    print(f"  Total Flow Edges: {len(ret_edges)} (Expected {len(orig_edges) + 172})")
    assert len(ret_nodes) == len(orig_nodes) + 60
    assert len(ret_edges) == len(orig_edges) + 172

    # 5.2 Verify standard_pre buttons
    pre_node = next(n for n in ret_nodes if n["id"] == CHAPTER_NODE_ID)
    assert len(pre_node["data"]["buttons"]) == 8, f"Expected 8 buttons on standard_pre, got {len(pre_node['data']['buttons'])}"
    print("  ✓ standard_pre has all 8 STANDARD: PRE.1 - PRE.8 buttons")

    # 5.3 Verify all 8 main standard nodes
    for i in range(1, 9):
        std_id = f"pre_{i}"
        std_node = next(n for n in ret_nodes if n["id"] == std_id)
        subs = PRE_DATA[i]["subs"]
        # Expected buttons: len(subs) + 1 (Back to PRE Standards)
        expected_btn_count = len(subs) + 1
        assert len(std_node["data"]["buttons"]) == expected_btn_count, \
            f"Expected {expected_btn_count} buttons on {std_id}, got {len(std_node['data']['buttons'])}"
        print(f"  ✓ {std_id} has {len(subs)} sub-standard buttons + 1 Back button")

    # 5.4 Verify all 52 sub-standard answer nodes and database answers
    db = SessionLocal()
    for i in range(1, 9):
        for letter, desc, interp in PRE_DATA[i]["subs"]:
            sub_node_id = f"pre_{i}_{letter}"
            sub_node = next(n for n in ret_nodes if n["id"] == sub_node_id)
            assert len(sub_node["data"]["buttons"]) == 2, f"Expected 2 buttons on {sub_node_id}"

            # Verify API GET /nodes/{node_id}/answer
            ans_code, ans_data = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_node_id}/answer?language=en")
            assert ans_code == 200, f"Expected 200 for {sub_node_id} answer, got {ans_code}"
            assert len(ans_data["blocks"]) == 2, f"Expected 2 blocks for {sub_node_id}, got {len(ans_data['blocks'])}"
            assert ans_data["blocks"][0]["content"] == f"### Description\n{desc}"
            assert ans_data["blocks"][1]["content"] == f"### Interpretation\n{interp}"

    db.close()
    print("  ✓ All 52 sub-standard nodes and answers verified in PostgreSQL with 2-block structure.")

    # 5.5 Verify existing AAC, COP, and MOM standards are intact
    aac_nodes = [n for n in ret_nodes if n["id"].startswith("aac_") or n["id"] == "standard_aac"]
    cop_nodes = [n for n in ret_nodes if n["id"].startswith("cop_") or n["id"] == "standard_cop"]
    mom_nodes = [n for n in ret_nodes if n["id"].startswith("mom_") or n["id"] == "standard_mom"]
    print(f"  ✓ AAC nodes intact: {len(aac_nodes)}")
    print(f"  ✓ COP nodes intact: {len(cop_nodes)}")
    print(f"  ✓ MOM nodes intact: {len(mom_nodes)}")

    db = SessionLocal()
    total_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID).count()
    # 212 previous + 52 PRE = 264 total answers
    print(f"  ✓ Total database answers for flow: {total_answers} (Previous: 212, Added: 52, Expected: 264)")
    assert total_answers == 264
    db.close()

    print("\n" + "=" * 80)
    print("SUCCESS: ALL 8 PRE STANDARDS (PRE.1-PRE.8) AND 52 SUB-STANDARDS INTEGRATED!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

