"""
Script: implement_cop_standards.py
Implements COP.1 through COP.20 in NABH QMitra active flow (a23710cb-3353-4811-97b7-5927ba6c6d25)
following the exact AAC implementation pattern.
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
from app.database import SessionLocal, get_utc_now
from app.models import Flow, NodeAnswer, AnswerBlock, MediaAsset, format_utc_iso


TARGET_CHATBOT_ID = "96359635-3ff9-4bfb-befa-13827094b16e"
TARGET_FLOW_ID = "a23710cb-3353-4811-97b7-5927ba6c6d25"
CHAPTER_NODE_ID = "standard_cop"

# COP Standards Metadata (COP.1 to COP.20)
COP_STANDARDS_INFO = {
    1: {"title": "Uniform Care to Patients", "subs": []},
    2: {"title": "Emergency Services", "subs": []},
    3: {"title": "Ambulance Services", "subs": []},
    4: {"title": "Community Emergencies and Disaster Management", "subs": []},
    5: {"title": "Cardio-Pulmonary Resuscitation Services", "subs": []},
    6: {"title": "Nursing Care", "subs": []},
    7: {"title": "Clinical Procedures", "subs": []},
    8: {"title": "Transfusion Services", "subs": []},
    9: {"title": "Intensive Care and High Dependency Care", "subs": []},
    10: {
        "title": "Safe Obstetric Care",
        "subs": [
            ("a", "Obstetric services are organised and provided safely"),
            ("b", "The organisation identifies and provides care to high-risk obstetric cases, and where needed, refers them to another appropriate centre"),
            ("c", "Persons caring for high-risk obstetric cases are competent"),
            ("d", "Ante-natal services are provided"),
            ("e", "Organisation encourages and welcomes the presence of a birth companion during labour"),
            ("f", "Organisation treats pregnant woman and her companion cordially and respectfully, ensures privacy and confidentiality for pregnant woman during her stay"),
            ("g", "The treating doctor explains danger signs and important care activities to pregnant woman and her companion"),
            ("h", "Obstetric patient's assessment also includes maternal nutrition"),
            ("i", "Appropriate peri-natal and post-natal monitoring is performed"),
            ("j", "The organisation caring for high-risk obstetric cases has the facilities to take care of neonates of such cases"),
            ("k", "Organization shall adhere to legal and defined Assisted Reproductive Technology (ART) practices"),
        ]
    },
    11: {
        "title": "Safe Paediatric Services",
        "subs": [
            ("a", "Paediatric services are organised and provided safely"),
            ("b", "Neonatal care is in consonance with national and international guidelines"),
            ("c", "Those who care for children have age-specific competency"),
            ("d", "Provisions are made for special care of children"),
            ("e", "Paediatric assessment includes growth, developmental, immunisation, and nutritional assessment"),
            ("f", "The organisation has measures in place to prevent child and neonate abduction and abuse"),
            ("g", "The child's family members are educated about nutrition, immunisation, and safe parenting"),
            ("h", "Defined clinical scope and adolescent-friendly healthcare provisions are maintained"),
        ]
    },
    12: {
        "title": "Procedural Sedation",
        "subs": [
            ("a", "Documented procedures guide the administration of procedural and moderate sedation"),
            ("b", "Informed consent for the administration of moderate sedation is obtained"),
            ("c", "Competent and trained persons perform procedural sedation"),
            ("d", "The person administering and monitoring sedation is separate and distinct from the person performing the procedure"),
            ("e", "Intra-procedure monitoring includes heart rate, cardiac rhythm, respiratory rate, blood pressure, oxygen saturation, and level of sedation"),
            ("f", "Patients are monitored post-sedation and recovery status is documented"),
            ("g", "Criteria are utilized and documented to determine appropriateness of discharge from the recovery area"),
            ("h", "Appropriate equipment and trained manpower are readily available to manage patients who drift into deeper sedation"),
        ]
    },
    13: {
        "title": "Anaesthesia Services",
        "subs": [
            ("a", "Documented policies and procedures guide the administration of anaesthesia"),
            ("b", "All patients scheduled for anaesthesia undergo a pre-anaesthesia assessment by a qualified anaesthesiologist"),
            ("c", "The pre-anaesthesia assessment results in the formulation of a documented anaesthesia plan"),
            ("d", "An immediate pre-induction assessment and re-evaluation is performed prior to administering anaesthesia"),
            ("e", "Informed consent for the administration of anaesthesia is obtained"),
            ("f", "Intra-anaesthesia monitoring includes regular recording of vital physiological parameters"),
        ]
    },
    14: {
        "title": "Surgical Services",
        "subs": [
            ("a", "Surgical services are provided in a consistent and safe manner"),
            ("b", "Surgical patients have a pre-operative assessment, a documented pre-operative diagnosis, and pre-operative instructions are provided before surgery"),
            ("c", "Informed consent is obtained by a surgeon before the procedure"),
            ("d", "Care is taken to prevent adverse events like wrong site, wrong patient, and wrong surgery"),
            ("e", "An operative note is documented before transfer out of the recovery area"),
            ("f", "Post-operative care is guided by a documented plan"),
            ("g", "Patient, personnel, and material flow conform to infection control practices"),
            ("h", "Appropriate facilities, equipment, instruments, and supplies are available in the operating theatre"),
            ("i", "The organisation shall implement a surgical quality assurance programme"),
            ("j", "The quality assurance programme includes surveillance of the operation theatre environment"),
        ]
    },
    15: {
        "title": "Organ Transplant Programme",
        "subs": [
            ("a", "The organ transplant program shall be in consonance with legal requirements and shall be conducted ethically"),
            ("b", "Care of transplant patients is guided by clinical practice guidelines"),
            ("c", "The organization ensures education and counselling of the recipient and donor through qualified counsellors"),
            ("d", "The organization shall take measures to create awareness regarding organ donation"),
        ]
    },
    16: {
        "title": "Care of Vulnerable and High-Risk Patients",
        "subs": [
            ("a", "The organisation identifies and manages vulnerable patients"),
            ("b", "The organisation identifies and manages patients who are at risk of falls"),
            ("c", "The organisation identifies and manages patients who are at risk of developing or worsening pressure ulcers"),
            ("d", "The organisation identifies and manages patients who are at risk of developing deep vein thrombosis (DVT)"),
            ("e", "The organisation identifies and manages patients requiring restraints"),
        ]
    },
    17: {
        "title": "Pain Management",
        "subs": [
            ("a", "Documented policies and procedures guide the management of pain"),
            ("b", "Patients are screened for pain during initial and ongoing clinical assessments"),
            ("c", "Patients in pain undergo detailed assessment and periodic reassessment using validated scales"),
        ]
    },
    18: {
        "title": "Rehabilitation Services",
        "subs": [
            ("a", "Scope of the rehabilitation services at a minimum is commensurate to the services provided by the organisation"),
            ("b", "Rehabilitation services are provided in a consistent manner guided by clinical treatment guidelines"),
            ("c", "Care providers collaboratively plan rehabilitation services"),
            ("d", "There is adequate space, infrastructure, and equipment to provide safe rehabilitation"),
            ("e", "Care is guided by functional assessment and periodic re-assessments which are done and documented"),
            ("f", "Rehabilitation care is provided adhering to infection control and safety practices"),
            ("g", "Rehabilitation care pathways are developed, implemented, and reviewed periodically"),
        ]
    },
    19: {
        "title": "Nutritional Therapy",
        "subs": [
            ("a", "Patients admitted to the organisation are screened for nutritional risk"),
            ("b", "Nutritional assessment is done for patients found at risk during nutritional screening"),
            ("c", "The therapeutic diet is planned and provided collaboratively"),
            ("d", "Patients receive food according to the written order for the diet"),
            ("e", "When family provides food, they are educated about the patient's diet limitations"),
        ]
    },
    20: {
        "title": "End-of-Life Care",
        "subs": [
            ("a", "Documented policies and procedures guide the provision of end-of-life care"),
            ("b", "Pain management and palliative care measures provide compassionate symptom relief"),
            ("c", "End-of-life care addresses and respects religious and socio-cultural needs of the patient and family"),
            ("d", "Transparent communication with patient and family guides treatment limitations and care planning"),
            ("e", "Protocols ensure respectful handling of deceased patients and facilitate post-death procedures"),
        ]
    }
}


# Verified Official Answers (Description and Interpretation)
VERIFIED_COP_ANSWERS = {
    "cop_18_e": {
        "desc": "Care is guided by functional assessment and periodic re-assessments which are done and documented.",
        "interp": "The assessment and ongoing evaluation of a patient requiring rehabilitation (physical therapy, occupational therapy, or speech therapy) must utilize relevant, validated functional assessment scales appropriate to the patient's condition (such as FIM score, Barthel Index, or Glasgow Outcome Scale). Functional assessments and periodic re-assessments must be performed and documented by qualified individuals authorized within their clinical scope. Re-assessments must be carried out at defined intervals or milestone markers to track recovery, modify therapeutic goals, or justify continuation or cessation of interventions. Assessors verify completed baseline assessments and dated, signed periodic re-assessments in medical records."
    },
    "cop_10_a": {
        "desc": "Obstetric services are organised and provided safely.",
        "interp": "Documented policies, standard operating procedures (SOPs), and clinical pathways based on standard treatment guidelines govern the organization and delivery of safe obstetric care, covering ante-natal (ANC), peri-natal, and post-natal care. Patient assessments must systematically incorporate maternal nutrition, immunization status, and education. The organization's written guidance must explicitly define what constitutes a high-risk obstetric case and state whether the hospital undertakes its management or arranges timely referral. Clinical and nursing staff must receive regular training on identifying and managing obstetric emergencies (such as postpartum hemorrhage, eclampsia, and fetal distress), and infrastructure for newborn care must align with neonatal and pediatric safety standards."
    },
    "cop_11_a": {
        "desc": "Paediatric services are organised and provided safely.",
        "interp": "The hospital must establish structured and safe workflows explicitly tailored for children, supported by dedicated infrastructure matching the scope of pediatric care provided (including safe cots, child-friendly environment, and prevention of falls and injuries). Clinical protocols ensure pediatric care is administered exclusively by personnel possessing age-specific competency and pediatric training."
    },
    "cop_12_a": {
        "desc": "Documented procedures guide the administration of procedural and moderate sedation.",
        "interp": "Procedural sedation practices cannot vary arbitrarily across departments; they must adhere to a uniform, hospital-approved Standard Operating Procedure (SOP) across all locations (including emergency, endoscopy suites, radiology, and minor procedure rooms). Protocols mandate pre-sedation risk assessment, written informed consent, patient monitoring by an independent clinician distinct from the proceduralist, and documented discharge criteria."
    },
    "cop_13_a": {
        "desc": "Documented policies and procedures guide the administration of anaesthesia.",
        "interp": "Anaesthesia delivery must follow standardized institutional policies and safety checklists (including pre-induction time-outs). Documented policies clearly define indications, authorized techniques, emergency readiness, and safety rules uniformly across all operating theaters. Anesthesia must be administered exclusively by qualified, privileged anesthesiologists."
    },
    "cop_14_a": {
        "desc": "Surgical services are provided in a consistent and safe manner.",
        "interp": "The organization provides surgical services guided by written policies and standard procedures based on evidence-based clinical practices. The scope of surgical services (elective and emergency) is clearly defined based on clinical facilities, operating theater infrastructure, and surgeon privileges. Surgical care encompasses pre-operative, intra-operative, and post-operative phases. Appropriate staffing, equipment, sterility controls, and emergency backup systems are maintained across all surgical theaters."
    },
    "cop_14_d": {
        "desc": "Care is taken to prevent adverse events like wrong site, wrong patient, and wrong surgery.",
        "interp": "The organization strictly implements standardized peri-operative verification protocols in accordance with the WHO Surgical Safety Checklist. The protocol includes three distinct phases: Sign-In (before induction of anesthesia), Time-Out (immediately before skin incision), and Sign-Out (before patient leaves the operating room). Surgical site marking is done by the operating team before surgery in the presence of the conscious patient wherever applicable."
    },
    "cop_14_j": {
        "desc": "The quality assurance programme includes surveillance of the operation theatre environment.",
        "interp": "Environmental surveillance of the operation theatre (OT) complex is conducted systematically as part of the hospital quality assurance and infection control program. This includes regular monitoring of OT positive pressure gradients, air changes per hour (ACPH), temperature, humidity, and HEPA filter integrity. Microbiological surveillance, routine surface swabs, and settle plate air sampling are performed according to documented institutional frequency."
    },
    "cop_15_a": {
        "desc": "The organ transplant program shall be in consonance with legal requirements and shall be conducted ethically.",
        "interp": "The hospital must possess valid, up-to-date statutory registrations and licenses under applicable national and state transplantation laws (such as THAUT). Strict institutional mechanisms prevent commercial dealings, ensure independent authorization committee approvals, prevent coercion, and enforce complete documentation of donor and recipient counseling."
    },
    "cop_16_a": {
        "desc": "The organisation identifies and manages vulnerable patients.",
        "interp": "The organization defines and identifies categories of vulnerable patients, including pediatric patients, unaccompanied elderly patients, pregnant women, physically or mentally challenged individuals, and patients with altered sensorium. Documented policies ensure enhanced monitoring, physical safety, protection from abuse or exploitation, chaperone assistance during clinical examinations, and specialized nursing support throughout outpatient and inpatient care."
    },
    "cop_17_a": {
        "desc": "Documented policies and procedures guide the management of pain.",
        "interp": "Pain management is recognized as an integral part of patient care and treated as the fifth vital sign. Written guidelines govern pain screening, comprehensive pain assessment, pharmacological and non-pharmacological interventions, and periodic reassessment. Clinical staff are trained in pain assessment methodologies and safe opioid and analgesic administration following standard clinical protocols."
    },
    "cop_18_a": {
        "desc": "Scope of the rehabilitation services at a minimum is commensurate to the services provided by the organisation.",
        "interp": "The organization explicitly defines the scope of rehabilitation services (physiotherapy, occupational therapy, speech therapy) based on clinical specialties offered and patient requirements. Services are provided consistently according to clinical practice guidelines, with documented departmental procedures, qualified therapists, and appropriate therapeutic space and equipment."
    },
    "cop_19_a": {
        "desc": "Patients admitted to the organisation are screened for nutritional risk.",
        "interp": "All admitted patients undergo nutritional screening at the time of initial assessment to identify individuals who are malnourished or at risk of developing malnutrition. Standardized, validated screening criteria (such as MUST or NRS-2002) are utilized. Patients identified as nutritional risks are promptly referred to qualified dietitians for detailed nutritional assessment and therapeutic dietary planning."
    },
    "cop_20_a": {
        "desc": "Documented policies and procedures guide the provision of end-of-life care.",
        "interp": "Documented institutional policies guide palliative and end-of-life care for terminally ill patients in compliance with applicable statutory and ethical guidelines. Care focuses on symptom control, compassionate pain relief, respecting patient and family preferences, honoring spiritual and cultural practices, emotional counseling, and transparent communication regarding treatment limits and DNR orders where legally recognized."
    }
}


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


def build_cop_graph(original_flow_data: dict) -> tuple:
    """
    Builds updated nodes and edges for COP.1 through COP.20 in flow a23710cb-3353-4811-97b7-5927ba6c6d25.
    Returns (updated_flow_data, new_nodes_list, new_edges_list).
    """
    flow_data = copy.deepcopy(original_flow_data)
    nodes = flow_data.get("nodes", [])
    edges = flow_data.get("edges", [])

    # 1. Update standard_cop chapter node
    cop_chapter = next((n for n in nodes if n["id"] == CHAPTER_NODE_ID), None)
    if not cop_chapter:
        raise ValueError(f"Chapter node '{CHAPTER_NODE_ID}' not found in flow.")

    if "data" not in cop_chapter or not isinstance(cop_chapter["data"], dict):
        cop_chapter["data"] = {}

    # 20 Main standard buttons for standard_cop
    cop_main_buttons = [
        {"id": f"standard_cop__cop_{i}__{i-1}", "next": f"cop_{i}", "label": f"STANDARD: COP.{i}"}
        for i in range(1, 21)
    ]
    cop_chapter["data"]["buttons"] = cop_main_buttons
    cop_chapter["data"]["message"] = "COP — Care of Patients (NABH 5th Edition Standards)"
    cop_chapter["mapping_status"] = "VERIFIED"

    new_nodes = []
    new_edges = []

    # 2. Main standard nodes cop_1 to cop_20
    std_base_y = 3200
    for i in range(1, 21):
        node_id = f"cop_{i}"
        info = COP_STANDARDS_INFO.get(i, {"title": f"Standard COP.{i}", "subs": []})
        subs = info["subs"]
        pos_y = std_base_y + (i - 1) * 220

        if i <= 9 or len(subs) == 0:
            # cop_1 through cop_9: rag nodes with PENDING_CONTENT + Back to COP Standards
            btn_back_id = f"{node_id}__back_standard_cop__0"
            node_def = {
                "id": node_id,
                "type": "rag",
                "data": {
                    "id": node_id,
                    "label": f"STANDARD: COP.{i}",
                    "message": f"COP.{i} — {info['title']} (Standard Details)",
                    "buttons": [
                        {"id": btn_back_id, "next": "standard_cop", "label": "Back to COP Standards"}
                    ],
                    "chapter": "COP",
                    "program": "Hospitals Accreditation",
                    "topic": "standards",
                    "status": "PENDING",
                    "nodeType": "rag",
                    "layoutWidth": 280,
                    "layoutHeight": 150,
                    "mapping_status": "PENDING_CONTENT",
                    "note": f"Official NABH sub-standards and interpretations pending verification for COP.{i}"
                },
                "chapter": "COP",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "message": f"COP.{i} — {info['title']} (Standard Details)",
                "position": {"x": 5715, "y": pos_y},
                "mapping_status": "PENDING_CONTENT"
            }
            new_nodes.append(node_def)

            # Back edge to standard_cop
            new_edges.append({
                "id": f"edge-{node_id}-standard_cop-{btn_back_id}",
                "label": "Back to COP Standards",
                "source": node_id,
                "target": "standard_cop",
                "sourceHandle": btn_back_id
            })

        else:
            # cop_10 through cop_20: menu nodes with sub-standard buttons + Back to COP Standards
            std_buttons = []
            for s_idx, (letter, desc) in enumerate(subs):
                sub_node_id = f"cop_{i}_{letter}"
                btn_id = f"cop_{i}__{sub_node_id}__{s_idx}"
                std_buttons.append({
                    "id": btn_id,
                    "next": sub_node_id,
                    "label": f"COP.{i}.{letter}"
                })

            btn_back_id = f"cop_{i}__back_standard_cop__{len(subs)}"
            std_buttons.append({
                "id": btn_back_id,
                "next": "standard_cop",
                "label": "Back to COP Standards"
            })

            node_def = {
                "id": node_id,
                "type": "menu",
                "data": {
                    "id": node_id,
                    "label": f"STANDARD: COP.{i}",
                    "message": f"COP.{i} — {info['title']}",
                    "buttons": std_buttons,
                    "chapter": "COP",
                    "program": "Hospitals Accreditation",
                    "topic": "standards",
                    "nodeType": "menu",
                    "layoutWidth": 290,
                    "layoutHeight": 280,
                    "mapping_status": "VERIFIED"
                },
                "chapter": "COP",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "message": f"COP.{i} — {info['title']}",
                "position": {"x": 5715, "y": pos_y},
                "mapping_status": "VERIFIED"
            }
            new_nodes.append(node_def)

            # Back edge to standard_cop
            new_edges.append({
                "id": f"edge-{node_id}-standard_cop-{btn_back_id}",
                "label": "Back to COP Standards",
                "source": node_id,
                "target": "standard_cop",
                "sourceHandle": btn_back_id
            })

            # Sub-standard answer nodes and connecting edges
            for s_idx, (letter, desc) in enumerate(subs):
                sub_node_id = f"cop_{i}_{letter}"
                sub_btn_back_std = f"{sub_node_id}__back_cop_{i}__0"
                sub_btn_back_cop = f"{sub_node_id}__back_standard_cop__1"

                sub_node = {
                    "id": sub_node_id,
                    "type": "answer",
                    "data": {
                        "id": sub_node_id,
                        "label": f"COP.{i}.{letter} — {desc}",
                        "message": desc,
                        "buttons": [
                            {"id": sub_btn_back_std, "next": node_id, "label": f"Back to COP.{i}"},
                            {"id": sub_btn_back_cop, "next": "standard_cop", "label": "Back to COP Standards"}
                        ],
                        "chapter": "COP",
                        "program": "Hospitals Accreditation",
                        "topic": "standards",
                        "nodeType": "answer",
                        "layoutWidth": 280,
                        "layoutHeight": 140,
                        "mapping_status": "VERIFIED"
                    },
                    "chapter": "COP",
                    "program": "Hospitals Accreditation",
                    "topic": "standards",
                    "message": desc,
                    "position": {"x": 6220, "y": pos_y + s_idx * 160},
                    "mapping_status": "VERIFIED"
                }
                new_nodes.append(sub_node)

                # Forward edge from cop_{i} to cop_{i}_{letter}
                fwd_btn_id = f"cop_{i}__{sub_node_id}__{s_idx}"
                new_edges.append({
                    "id": f"edge-{node_id}-{sub_node_id}-{fwd_btn_id}",
                    "label": f"COP.{i}.{letter}",
                    "source": node_id,
                    "target": sub_node_id,
                    "sourceHandle": fwd_btn_id
                })

                # Back edge to cop_{i}
                new_edges.append({
                    "id": f"edge-{sub_node_id}-{node_id}-{sub_btn_back_std}",
                    "label": f"Back to COP.{i}",
                    "source": sub_node_id,
                    "target": node_id,
                    "sourceHandle": sub_btn_back_std
                })

                # Back edge to standard_cop
                new_edges.append({
                    "id": f"edge-{sub_node_id}-standard_cop-{sub_btn_back_cop}",
                    "label": "Back to COP Standards",
                    "source": sub_node_id,
                    "target": "standard_cop",
                    "sourceHandle": sub_btn_back_cop
                })

    # Forward edges from standard_cop to cop_1..cop_20 (20 edges)
    for btn in cop_main_buttons:
        new_edges.append({
            "id": f"edge-standard_cop-{btn['next']}-{btn['id']}",
            "type": "smoothstep",
            "label": btn["label"],
            "style": {"stroke": "#A3A3A3", "strokeWidth": 1.5},
            "source": "standard_cop",
            "target": btn["next"],
            "sourceHandle": btn["id"]
        })

    flow_data["nodes"] = nodes + new_nodes
    flow_data["edges"] = edges + new_edges

    return flow_data, new_nodes, new_edges


async def main():
    print("=" * 80)
    print("EXECUTING COP.1 - COP.20 IMPLEMENTATION (AAC PATTERN)")
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
    orig_node_count = len(orig_nodes)
    orig_edge_count = len(orig_edges)
    print(f"Pre-migration Node Count: {orig_node_count}")
    print(f"Pre-migration Edge Count: {orig_edge_count}")
    expected_new_nodes = 92  # 20 main standard nodes + 72 sub-standard nodes
    expected_new_edges = 256  # 20 + 9 + 11 + 72 + 72 + 72
    expected_final_nodes = orig_node_count + expected_new_nodes
    expected_final_edges = orig_edge_count + expected_new_edges

    # Step 1: Backup
    print("\n[1/4] Creating pre-COP implementation safety backup...")
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file_path = os.path.join(
        backend_dir, "data", f"backup_flow_{TARGET_FLOW_ID}_before_cop_complete_{timestamp_str}.json"
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
    print(f"  ✓ Backup saved to: {backup_file_path}")
    db.close()

    # Step 2: Build updated graph
    print("\n[2/4] Constructing COP graph updates...")
    updated_flow_data, new_nodes, new_edges = build_cop_graph(target_flow.flow_data)
    print(f"  New Nodes: {len(new_nodes)} (Total: {len(updated_flow_data['nodes'])})")
    print(f"  New Edges: {len(new_edges)} (Total: {len(updated_flow_data['edges'])})")
    assert len(new_nodes) == expected_new_nodes
    assert len(new_edges) == expected_new_edges
    assert len(updated_flow_data["nodes"]) == expected_final_nodes
    assert len(updated_flow_data["edges"]) == expected_final_edges

    # Step 3: PUT /flows/{flow_id}
    print(f"\n[3/4] Persisting updated flow via PUT /flows/{TARGET_FLOW_ID}...")
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
    print(f"  ✓ Flow graph updated: {len(put_resp['flow_data']['nodes'])} nodes, {len(put_resp['flow_data']['edges'])} edges")

    # Step 4: Storing verified COP answers in node_answers and answer_blocks
    print("\n[4/4] Storing verified COP answers in node_answers and answer_blocks...")
    created_answers_count = 0
    now = get_utc_now()

    for node_id, content_dict in VERIFIED_COP_ANSWERS.items():
        desc = content_dict["desc"]
        interp = content_dict["interp"]
        formatted_content = f"**Description:** {desc}\n\n**Interpretation:** {interp}"

        payload = {
            "language": "en",
            "blocks": [
                {
                    "block_type": "text",
                    "position": 1,
                    "content": formatted_content
                }
            ]
        }

        # Check if answer exists (PUT) or needs creation (POST)
        get_status, _ = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{node_id}/answer?language=en")
        method = "PUT" if get_status == 200 else "POST"

        ans_status, ans_resp = await invoke_asgi(
            method, f"/flows/{TARGET_FLOW_ID}/nodes/{node_id}/answer", payload
        )
        if ans_status not in (200, 201):
            print(f"ERROR saving answer for {node_id}: {ans_resp}")
            sys.exit(1)

        print(f"  ✓ [{method}] {node_id} answer stored: ID={ans_resp['id']}, 1 block")
        created_answers_count += 1

    # Step 5: Verification & Integrity Audit
    print("\n" + "=" * 80)
    print("RUNNING POST-COP SYSTEM VERIFICATION AUDIT")
    print("=" * 80)

    # 5.1 GET /flows/{flow_id}
    get_status, flow_res = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}")
    assert get_status == 200
    ret_nodes = flow_res["flow_data"]["nodes"]
    ret_edges = flow_res["flow_data"]["edges"]
    assert len(ret_nodes) == expected_final_nodes
    assert len(ret_edges) == expected_final_edges
    print(f"  ✓ GET /flows/{TARGET_FLOW_ID}: Confirmed {len(ret_nodes)} nodes, {len(ret_edges)} edges.")

    # 5.2 Verify standard_cop has 20 buttons
    ret_cop_chap = next(n for n in ret_nodes if n["id"] == "standard_cop")
    cop_btns = ret_cop_chap.get("data", {}).get("buttons", [])
    assert len(cop_btns) == 20
    for idx, b in enumerate(cop_btns):
        assert b["id"] == f"standard_cop__cop_{idx+1}__{idx}"
        assert b["next"] == f"cop_{idx+1}"
        assert b["label"] == f"STANDARD: COP.{idx+1}"
    print("  ✓ All 20 main standard buttons on standard_cop confirmed.")

    # 5.3 Verify all 72 sub-standard nodes exist
    sub_count = 0
    for i in range(10, 21):
        subs = COP_STANDARDS_INFO[i]["subs"]
        sub_count += len(subs)
        menu_node = next(n for n in ret_nodes if n["id"] == f"cop_{i}")
        assert len(menu_node.get("data", {}).get("buttons", [])) == len(subs) + 1  # subs + back
        for letter, desc in subs:
            sub_n = next(n for n in ret_nodes if n["id"] == f"cop_{i}_{letter}")
            assert sub_n["type"] == "answer"
            assert len(sub_n.get("data", {}).get("buttons", [])) == 2  # back to std + back to chapter
    assert sub_count == 72
    print(f"  ✓ All {sub_count} sub-standard nodes for COP.10–COP.20 confirmed.")

    # 5.4 Test COP.18.e answer retrieval explicitly
    ans_18e_status, ans_18e = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/cop_18_e/answer?language=en")
    assert ans_18e_status == 200
    assert len(ans_18e["blocks"]) == 1
    assert "**Description:**" in ans_18e["blocks"][0]["content"]
    assert "**Interpretation:**" in ans_18e["blocks"][0]["content"]
    assert "functional assessment" in ans_18e["blocks"][0]["content"]
    print(f"  ✓ Runtime test case COP.18.e successfully retrieved via GET answer API (HTTP 200 OK).")

    # 5.5 Verify existing hospital answers and AAC answers remain 100% intact
    db = SessionLocal()
    all_flow_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID).all()
    print(f"  Total Answers on Flow 3: {len(all_flow_answers)} (9 previous + {created_answers_count} new COP)")
    ans_node_ids = {a.node_id for a in all_flow_answers}

    # Verify hospital answers preserved
    for h in ["hospitals_eligibility", "hospitals_application", "hospitals_assessment", "hospitals_documents", "hospitals_fee_structure"]:
        assert h in ans_node_ids
    print("  ✓ All 5 official hospital answers preserved.")

    # Verify AAC answers preserved
    for aac in ["aac_1_a", "aac_1_b", "aac_1_c", "aac_1_d"]:
        assert aac in ans_node_ids
    print("  ✓ All 4 official AAC answers preserved.")

    # 5.6 Verify duplicate node IDs and edge IDs in graph
    from collections import Counter
    node_id_counts = Counter(n["id"] for n in ret_nodes)
    dup_n = {k: v for k, v in node_id_counts.items() if v > 1}
    assert len(dup_n) == 0, f"Duplicate nodes found: {dup_n}"
    print("  ✓ Zero duplicate node IDs in updated graph.")

    # 5.7 Verify edges source and target existence
    node_id_set = set(n["id"] for n in ret_nodes)
    missing_sources = [e for e in ret_edges if e.get("source") not in node_id_set]
    missing_targets = [e for e in ret_edges if e.get("target") not in node_id_set]
    assert len(missing_sources) == 0
    assert len(missing_targets) == 0
    print("  ✓ 100% of edge sources and targets exist in graph.")

    db.close()

    print("\n" + "=" * 80)
    print("ALL COP.1 - COP.20 IMPLEMENTATION & VERIFICATION CHECKS PASSED (100%)")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
