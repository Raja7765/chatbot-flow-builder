"""
Script: integrate_mom_standards.py
Integrates all 11 NABH Management of Medication (MOM) standards (MOM.1–MOM.11),
their 68 sub-standard buttons and nodes, and their individual Description + Interpretation answers
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
CHAPTER_NODE_ID = "standard_mom"

# Complete Official NABH MOM Standards & 68 Sub-Standards
MOM_DATA = {
    1: {
        "title": "Pharmacy services and medication management is done safely",
        "subs": [
            ("a", "Pharmacy services and medication management are implemented following written guidance.",
             "The organisation establishes and implements comprehensive policies, procedures, and standard operating procedures (SOPs) governing the complete medication management process, including procurement, safe storage, prescription, dispensing, administration, and monitoring."),
            ("b", "A multidisciplinary committee guides the formulation and implementation of pharmacy services and medication management.",
             "A formally constituted multidisciplinary committee (such as the Pharmacy and Therapeutics Committee / DTC) comprising clinicians, clinical pharmacists, nursing leadership, and quality managers meets regularly to oversee medication management and safety policies."),
            ("c", "The multidisciplinary committee actively updates medication management processes by reviewing literature, tracking changes, and incorporating best practices.",
             "The committee periodically reviews evidence-based literature, updates standard treatment guidelines, tracks regulatory notifications, and integrates modern clinical pharmacy practices into the hospital's clinical workflows."),
            ("d", "There is a clear, documented procedure to obtain medications when the pharmacy is closed or during unexpected stock-outs.",
             "The organisation maintains a robust protocol for emergency access to essential medications after pharmacy operating hours or during unexpected stock shortages, ensuring uninterrupted patient care through designated emergency night cupboards or rapid procurement systems."),
            ("e", "The organisation maintains a mechanism to inform relevant clinical and support staff of key changes in pharmacy services and medication processes to ensure uninterrupted, safe care.",
             "Effective communication mechanisms (circulars, digital alerts, clinical briefings) promptly notify medical, nursing, and administrative staff regarding changes in formulary status, drug recalls, stock outages, or updated medication administration policies."),
        ]
    },
    2: {
        "title": "The organisation develops, updates and implements a hospital formulary",
        "subs": [
            ("a", "A list of medications appropriate for the patients and as per the scope of the organisation's clinical services is developed collaboratively by the multidisciplinary committee.",
             "The Pharmacy and Therapeutics Committee collaboratively develops a formulary of approved medications tailored to the hospital's clinical specialties, patient demographic needs, and therapeutic efficacy evidence."),
            ("b", "The list is reviewed and updated collaboratively by the multidisciplinary committee at least annually.",
             "The formulary undergoes systematic, documented annual review by the committee to add newly approved therapeutic agents, delete obsolete or toxic drugs, and review drug safety alerts."),
            ("c", "The current formulary is available for clinicians to refer to.",
             "The updated hospital formulary is readily accessible in physical and/or digital formats at all nursing stations, outpatient consultation chambers, emergency areas, and intensive care units."),
            ("d", "The clinicians adhere to the current formulary when prescribing.",
             "Prescribers adhere to the formulary list when ordering medications, supported by regular clinical audits tracking formulary compliance rates across clinical departments."),
            ("e", "The organisation adheres to a defined procedure for the acquisition of formulary medications.",
             "Procurement of formulary medications follows established procurement workflows, quality screening, vendor evaluation, and approved distributor networks to ensure medicine authenticity and timely supply."),
            ("f", "The organisation adheres to a defined procedure to obtain non-formulary medications when required.",
             "A clear, time-sensitive protocol enables authorized clinicians to justify and obtain non-formulary medications for specific clinical indications or rare conditions without compromising patient care timelines."),
        ]
    },
    3: {
        "title": "Medications are stored appropriately and are available where required",
        "subs": [
            ("a", "Documented policies and procedures exist for the storage of medication.",
             "Standard operating procedures define proper handling and storage standards across the main pharmacy, sub-pharmacies, ward drug rooms, OTs, and intensive care units."),
            ("b", "Medications are stored in a clean, safe, and secure environment, incorporating manufacturer's recommendations.",
             "Drug storage areas maintain cleanliness, pest control, proper ventilation, and continuous temperature/humidity monitoring. Thermolabile medications are maintained in dedicated medical refrigerators with calibrated temperature logs (2°C to 8°C)."),
            ("c", "Sound inventory control practices guide the storage of medications.",
             "Stock rotation enforces First-Expired, First-Out (FEFO) and First-In, First-Out (FIFO) principles to minimize medication wastage and prevent the dispensing of near-expiry products."),
            ("d", "Look-Alike, Sound-Alike (LASA) medications are identified and stored separately.",
             "Formulary drugs with similar names or packaging are identified, visually distinguished using Tall Man lettering, and physically separated on shelves to prevent selection errors."),
            ("e", "The list of emergency medications is defined and stored in a uniform manner.",
             "A standardized emergency medication list is maintained across all clinical areas, and emergency medications (crash carts, resuscitation trays) follow identical layouts and sealing mechanisms hospital-wide."),
            ("f", "Emergency medications are available at all times.",
             "Emergency trays and crash carts remain immediately accessible 24/7 in all clinical units, monitored with daily checklists and verification of unexpired drug stocks."),
            ("g", "Emergency medications are replenished in a timely manner when used.",
             "Immediate replenishment protocols guarantee that any opened emergency box or used crash cart is restocked, verified by pharmacy, and resealed within defined turnaround times."),
        ]
    },
    4: {
        "title": "Medications are prescribed safely and rationally",
        "subs": [
            ("a", "Medication prescriptions must align with established good practices and clinical guidelines for the rational use of medicines.",
             "Prescriptions follow evidence-based Standard Treatment Guidelines (STGs), promoting generic prescribing, avoiding polypharmacy, and ensuring rational antimicrobial and therapeutic choices."),
            ("b", "The organisation adheres to defined minimum criteria for what constitutes a valid prescription.",
             "Mandatory prescription elements must be present: patient full name, unique identification number (UHID), age/gender, date/time, drug name, strength, dosage form, route, frequency, duration, prescriber name, and registration signature."),
            ("c", "Known drug allergies and previous adverse drug reactions are systematically checked and ascertained before a medication is prescribed.",
             "Clinicians proactively ascertain, record, and highlight patient drug allergies and prior adverse reactions in clinical charts and digital prescribing interfaces before authorizing new medications."),
            ("d", "The organisation provides mechanisms or tools to assist clinicians in prescribing appropriate medications.",
             "Reference resources, clinical decision support software, drug interaction checkers, and antimicrobial stewardship guidelines are available at points of care to guide prescribers."),
            ("e", "Medication reconciliation occurs at critical transition points of patient care.",
             "Structured medication reconciliation is conducted upon admission, transfer between clinical units, and hospital discharge to resolve omissions, duplications, dosing discrepancies, or drug interactions."),
            ("f", "Verbal medication orders are regulated and implemented by following strict safe medication management protocols.",
             "Verbal or telephonic orders are restricted to genuine emergencies, requiring mandatory 'read-back and confirm' verification and counter-signature by the prescribing clinician within a specified timeframe (e.g., 24 hours)."),
            ("g", "Regular audits of medication orders and prescriptions are carried out to evaluate and ensure compliance with safe and rational prescribing practices.",
             "Clinical pharmacists and the quality team perform routine, documented audits of inpatient case sheets and outpatient prescriptions to monitor legibility, completeness, drug interactions, and rationality."),
            ("h", "Corrective and/or preventive actions are implemented based on the findings from medication prescription audits.",
             "Audit results are presented to the Pharmacy and Therapeutics Committee, triggering targeted clinical feedback, prescriber education, and systemic workflow improvements."),
        ]
    },
    5: {
        "title": "Medication orders are written in a uniform manner",
        "subs": [
            ("a", "Only authorized personnel are permitted to write medication orders.",
             "The organisation strictly restricts medication prescribing privileges to credentialed and licensed medical practitioners in compliance with national and state medical council regulations."),
            ("b", "Medication orders are written in a designated, uniform location in the medical records.",
             "All medication orders are recorded in a standardized, designated Medication Administration Record (MAR) or Doctor's Order Sheet within physical or electronic patient health records."),
            ("c", "Medication orders are clear, legible, dated, timed, and signed by the prescriber.",
             "Orders must be written legibly (avoiding prohibited abbreviations), with the exact date, time, and legible signature and identification of the ordering clinician."),
            ("d", "Medication orders precisely specify the medicine name, route of administration, strength, and frequency/timing of administration.",
             "Each drug order explicitly states the full generic or brand name, metric dosage, pharmaceutical strength, route, and dosing interval, avoiding vague instructions like 'as directed'."),
        ]
    },
    6: {
        "title": "Medications are dispensed in a safe manner",
        "subs": [
            ("a", "Medications are dispensed only against a valid prescription or medication order.",
             "Pharmacy personnel dispense prescription medications exclusively upon receipt and verification of an authorized, signed prescription or electronic order."),
            ("b", "Drugs are dispensed exclusively by authorized personnel who are legally registered.",
             "Dispensing is performed or directly supervised by qualified, registered pharmacists licensed with the State Pharmacy Council."),
            ("c", "Prescriptions or indents are screened and checked prior to dispensing for clinical appropriateness, therapeutic duplications, drug-drug interactions, allergies, and formulary status.",
             "Pharmacists perform pre-dispensing clinical checks reviewing patient allergy status, dose appropriateness, potential interactions, contraindications, and duplications."),
            ("d", "Near-expiry medications are managed effectively through systematic checks before dispensing.",
             "A documented near-expiry tracking protocol prevents the dispensing of medicines whose expiry date falls within the expected course of treatment."),
            ("e", "High-risk medication orders undergo independent checks or verification before they are dispensed.",
             "Orders for high-alert medications (e.g., concentrated electrolytes, anticoagulants, insulin, chemotherapeutics) require an independent double-check before leaving the pharmacy."),
            ("f", "There is a documented policy and procedure directing the safe return of medications to the pharmacy.",
             "Standard operating procedures govern the return of unused, discontinued, or recalled medications from inpatient wards, ensuring temperature integrity checks and proper credit/destruction documentation."),
        ]
    },
    7: {
        "title": "Medications are administered safely",
        "subs": [
            ("a", "Medications are administered only by those who are permitted by law to do so.",
             "Medication administration is restricted to qualified, privileged healthcare professionals (registered nurses and doctors) authorized within their clinical scope of practice."),
            ("b", "Prepared medications are properly labelled before the preparation of a second drug.",
             "Any medication drawn into a syringe or prepared in an infusion container must be immediately labeled with the drug name, dose, volume, date, time, and patient name before preparing any other medication."),
            ("c", "The patient is positively identified prior to administration.",
             "Nurses verify patient identity using at least two unique identifiers (full name and hospital UHID/wristband) against the active medication order before administration."),
            ("d", "Medication is verified against the medication order and physically inspected prior to administration.",
             "The administering nurse verifies the drug against the prescription, checking packaging integrity, clarity, color changes, particulate matter, and expiration dates."),
            ("e", "The strength/dosage of the medication is verified from the order before administration.",
             "Dosages and calculations (especially pediatric or weight-based dosing) are independently verified prior to administration."),
            ("f", "The route of administration is verified from the order before administration.",
             "The prescribed route (oral, IV, IM, subcutaneous, topical, inhalation) is confirmed, ensuring appropriate anatomical site selection and technique."),
            ("g", "The timing and frequency are verified from the order before administration.",
             "Medications are administered according to standardized hospital administration schedules to maintain optimal therapeutic blood levels."),
            ("h", "Measures to avoid catheter and tubing mis-connections during medication administration are implemented.",
             "Strict clinical protocols and physical tracing of lines from the infusion container to the patient insertion site prevent catheter and tubing misconnections (such as enteral feeds into IV lines)."),
            ("i", "Medication administration is accurately documented in the patient's medical records.",
             "Prompt documentation in the Medication Administration Record (MAR) records the exact drug, dose, route, date, time, and signature/initials of the administering clinician, noting any omissions or refusals."),
            ("j", "Measures to govern a patient's self-administration of medications are implemented.",
             "Hospital policy defines whether self-administration is permitted, requiring physician authorization, patient competency assessment, nursing verification, and secure bedside storage."),
            ("k", "Measures to govern medications brought by patients from outside the organisation are implemented.",
             "Outside medications brought by patients must be clinically evaluated, verified for quality and authenticity by the treating physician/pharmacist, and documented in the hospital chart prior to use."),
        ]
    },
    8: {
        "title": "Patients are monitored after medication administration",
        "subs": [
            ("a", "Patients are monitored after medication administration.",
             "Clinical teams observe and evaluate patient clinical response, vital signs, and therapeutic outcomes following medication administration, paying particular attention to high-risk drugs."),
            ("b", "Medications are changed or adjusted where appropriate based on monitoring findings.",
             "Treating clinicians review therapeutic drug monitoring results, laboratory parameters, and patient recovery indicators to titrate dosages, discontinue ineffective drugs, or adjust therapy."),
            ("c", "A documented procedure exists to capture near misses, medication errors, and adverse drug events.",
             "Standard operating procedures define mechanisms for identifying, reporting, and documenting medication incidents, near misses, and adverse drug reactions (ADRs)."),
            ("d", "Near misses, medication errors, and adverse drug events are clearly defined by the organisation.",
             "Standard definitions and severity classifications are disseminated to all clinical staff to support consistent identification and non-punitive incident reporting."),
            ("e", "These incidents are reported within a specified time frame.",
             "Mandatory incident reporting timelines (e.g., immediate notification for sentinel events and within 24 hours for minor errors) ensure rapid clinical intervention and root cause investigation."),
            ("f", "The data regarding these events is systematically collected, analyzed, and used for corrective and preventive actions.",
             "The Pharmacy and Therapeutics and Quality Committees analyze aggregate error data, identify systemic root causes, and implement corrective and preventive actions (CAPA) to prevent recurrence."),
        ]
    },
    9: {
        "title": "Narcotic drugs and psychotropic substances, chemotherapeutic agents and radio-pharmaceuticals are used in a safe manner",
        "subs": [
            ("a", "Documented policies and procedures guide the safe use of narcotic drugs, psychotropic substances, chemotherapeutic agents, and radio-pharmaceuticals in strict consonance with statutory regulations.",
             "Institutional standard operating procedures comply with statutory laws (such as the NDPS Act, Atomic Energy Act, and Hazardous Waste Management Rules) governing the handling of controlled and hazardous substances."),
            ("b", "These specialized agents are prescribed only by appropriate, qualified caregivers who hold the necessary credentials and competence.",
             "Prescribing rights for narcotics, chemotherapy, and radiopharmaceuticals are restricted to registered oncologists, palliative care physicians, or authorized specialists holding valid statutory permits."),
            ("c", "These drugs are stored in a secure, restricted, and safe manner.",
             "Narcotics and psychotropic drugs are stored in double-locked, heavy-gauge steel cupboards with keys kept in the custody of designated senior nursing or pharmacy supervisors. Chemotherapy and radioactive drugs are segregated with specialized shielding."),
            ("d", "Chemotherapeutic agents and radio-pharmaceuticals are prepared in a proper, clean, and safe manner and administered exclusively by trained, qualified personnel.",
             "Cytotoxic reconstitution is conducted in specialized biological safety cabinets (Class II Type B2) with appropriate personal protective equipment (PPE), spill kits, and chemotherapy-certified oncology nurses administering the infusions."),
            ("e", "A rigorous, traceable record is maintained tracking the complete lifecycle of these substances including receipt, usage, patient administration, wastage, and safe legal disposal.",
             "Dedicated physical or electronic registers record batch numbers, ampoule issue, exact doses administered, witnessed wastage destruction, and empty container disposal in accordance with statutory requirements."),
        ]
    },
    10: {
        "title": "Implantable prosthesis and medical devices are used in accordance with laid down criteria",
        "subs": [
            ("a", "The usage of implantable prosthesis and medical devices is guided by scientific criteria for each item and national/international recognized guidelines/approvals.",
             "Implants (e.g., orthopedic joints, stents, pacemakers, surgical mesh) must possess valid regulatory certifications (CDSCO, US-FDA, CE-mark) and be approved based on clinical evidence and hospital committee selection."),
            ("b", "The organisation implements a clear, documented mechanism for the procurement, storage, and usage of implantable prostheses and medical devices.",
             "Standard operating procedures govern the vendor qualification, sterility inspection, specialized storage conditions, and issuance of implantable medical devices."),
            ("c", "The patient and his/her family are properly counseled regarding the usage of the implantable prosthesis or medical device, including any necessary post-procedure precautions.",
             "Clinicians provide detailed pre-procedure counseling regarding implant options, expected lifespan, potential risks or failure signs, and post-implantation care instructions."),
            ("d", "The batch number and serial number of the implantable prosthesis and medical devices are explicitly recorded in the patient's medical records, the master logbook, and the discharge summary.",
             "Complete traceability is maintained by affixing device barcode stickers or recording model, batch, and serial numbers in the operative note, implant register, and patient discharge summary."),
            ("e", "An effective process is in place to handle the recall of implantable prostheses and medical devices based on alerts from regulatory authorities, manufacturers, or internal feedback.",
             "Documented recall protocols ensure immediate quarantine of affected implant stock, notification of operating surgeons, patient registry tracking, and clinical surveillance of implanted patients."),
        ]
    },
    11: {
        "title": "Medical supplies and consumables are stored appropriately and are available where required",
        "subs": [
            ("a", "The organisation adheres to a defined, systematic process for the acquisition and purchasing of medical supplies and consumables.",
             "Procurement specifications, purchase requisitions, and vendor evaluations are established collaboratively with clinical departments to ensure high-quality consumables."),
            ("b", "Medical supplies and consumables are inspected upon receipt and checked for integrity and sterility.",
             "Incoming consignments undergo physical verification of packaging integrity, sterile seal status, manufacturing/expiry dates, and batch conformity prior to inventory acceptance."),
            ("c", "Supplies and consumables are stored in clean, safe, and secure environments layout-compliant with manufacturer guidelines and inventory control metrics.",
             "Storage maintains optimal environmental conditions, preventing moisture, dust, or heat damage, with systematic stock rotation adhering to FIFO/FEFO principles."),
            ("d", "Medical supplies and consumables are utilized safely and verified for expiry prior to patient application.",
             "Healthcare providers visually inspect packaging integrity and confirm unexpired status before opening any disposable item or medical supply at the bedside."),
            ("e", "Mechanisms are in place to ensure that medical supplies and consumables are available at all clinical points of care without shortages.",
             "Buffer stock levels, re-order thresholds, and streamlined distribution systems maintain steady availability of critical supplies across all wards, OTs, and intensive care areas."),
        ]
    }
}


async def invoke_asgi(method: str, path: str, body: dict = None) -> tuple:
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


def build_mom_graph(original_flow_data: dict) -> tuple:
    flow_data = copy.deepcopy(original_flow_data)
    nodes = flow_data.get("nodes", [])
    edges = flow_data.get("edges", [])

    node_map = {n["id"]: n for n in nodes}

    # 1. Update standard_mom chapter node
    mom_chapter = node_map.get(CHAPTER_NODE_ID)
    if not mom_chapter:
        raise ValueError(f"Chapter node '{CHAPTER_NODE_ID}' not found in flow.")

    # 11 Main standard buttons for standard_mom
    mom_main_buttons = [
        {"id": f"standard_mom__mom_{i}__{i-1}", "next": f"mom_{i}", "label": f"STANDARD: MOM.{i}"}
        for i in range(1, 12)
    ]
    mom_chapter["data"]["buttons"] = mom_main_buttons
    mom_chapter["data"]["message"] = "MOM — Management of Medication (NABH 5th Edition Standards)"
    mom_chapter["data"]["mapping_status"] = "VERIFIED"
    mom_chapter["mapping_status"] = "VERIFIED"

    new_nodes = []
    new_edges = []

    # 2. Forward edges from standard_mom to mom_1..mom_11 (11 edges)
    for btn in mom_main_buttons:
        new_edges.append({
            "id": f"edge-standard_mom-{btn['next']}-{btn['id']}",
            "label": btn["label"],
            "source": CHAPTER_NODE_ID,
            "target": btn["next"],
            "sourceHandle": btn["id"]
        })

    # 3. Create Main standard nodes mom_1 to mom_11 & their sub-standards
    std_base_y = 8000
    for i in range(1, 12):
        std_id = f"mom_{i}"
        std_info = MOM_DATA[i]
        subs = std_info["subs"]
        pos_y = std_base_y + (i - 1) * 220

        # Sub-standard buttons for mom_i
        std_buttons = []
        for s_idx, (letter, desc, _) in enumerate(subs):
            sub_node_id = f"mom_{i}_{letter}"
            btn_id = f"mom_{i}__{sub_node_id}__{s_idx}"
            std_buttons.append({
                "id": btn_id,
                "next": sub_node_id,
                "label": f"MOM.{i}.{letter}"
            })

        # Back to MOM Standards button
        btn_back_id = f"mom_{i}__back_standard_mom__{len(subs)}"
        std_buttons.append({
            "id": btn_back_id,
            "next": CHAPTER_NODE_ID,
            "label": "Back to MOM Standards"
        })

        # Main standard node definition (menu)
        std_node = {
            "id": std_id,
            "type": "menu",
            "data": {
                "id": std_id,
                "label": f"STANDARD: MOM.{i}",
                "message": f"MOM.{i} — {std_info['title']}",
                "buttons": std_buttons,
                "chapter": "MOM",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "nodeType": "menu",
                "layoutWidth": 290,
                "layoutHeight": 280,
                "mapping_status": "VERIFIED"
            },
            "chapter": "MOM",
            "program": "Hospitals Accreditation",
            "topic": "standards",
            "message": f"MOM.{i} — {std_info['title']}",
            "position": {"x": 5715, "y": pos_y},
            "mapping_status": "VERIFIED"
        }
        new_nodes.append(std_node)

        # Back edge from mom_i to standard_mom
        new_edges.append({
            "id": f"edge-{std_id}-standard_mom-{btn_back_id}",
            "label": "Back to MOM Standards",
            "source": std_id,
            "target": CHAPTER_NODE_ID,
            "sourceHandle": btn_back_id
        })

        # Sub-standard answer nodes and connecting edges
        for s_idx, (letter, desc, _) in enumerate(subs):
            sub_node_id = f"mom_{i}_{letter}"
            sub_btn_back_std = f"{sub_node_id}__back_mom_{i}__0"
            sub_btn_back_mom = f"{sub_node_id}__back_standard_mom__1"

            sub_node = {
                "id": sub_node_id,
                "type": "answer",
                "data": {
                    "id": sub_node_id,
                    "label": f"MOM.{i}.{letter} — {desc}",
                    "message": desc,
                    "buttons": [
                        {"id": sub_btn_back_std, "next": std_id, "label": f"Back to MOM.{i}"},
                        {"id": sub_btn_back_mom, "next": CHAPTER_NODE_ID, "label": "Back to MOM Standards"}
                    ],
                    "chapter": "MOM",
                    "program": "Hospitals Accreditation",
                    "topic": "standards",
                    "nodeType": "answer",
                    "layoutWidth": 280,
                    "layoutHeight": 140,
                    "mapping_status": "VERIFIED"
                },
                "chapter": "MOM",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "message": desc,
                "position": {"x": 6220, "y": pos_y + s_idx * 140},
                "mapping_status": "VERIFIED"
            }
            new_nodes.append(sub_node)

            # Forward edge from mom_{i} to mom_{i}_{letter}
            fwd_btn_id = f"mom_{i}__{sub_node_id}__{s_idx}"
            new_edges.append({
                "id": f"edge-{std_id}-{sub_node_id}-{fwd_btn_id}",
                "label": f"MOM.{i}.{letter}",
                "source": std_id,
                "target": sub_node_id,
                "sourceHandle": fwd_btn_id
            })

            # Back edge to mom_{i}
            new_edges.append({
                "id": f"edge-{sub_node_id}-{std_id}-{sub_btn_back_std}",
                "label": f"Back to MOM.{i}",
                "source": sub_node_id,
                "target": std_id,
                "sourceHandle": sub_btn_back_std
            })

            # Back edge to standard_mom
            new_edges.append({
                "id": f"edge-{sub_node_id}-standard_mom-{sub_btn_back_mom}",
                "label": "Back to MOM Standards",
                "source": sub_node_id,
                "target": CHAPTER_NODE_ID,
                "sourceHandle": sub_btn_back_mom
            })

    flow_data["nodes"] = nodes + new_nodes
    flow_data["edges"] = edges + new_edges

    return flow_data, new_nodes, new_edges


async def main():
    print("=" * 80)
    print("INTEGRATING NABH MOM.1 - MOM.11 STANDARDS INTO ACTIVE FLOW")
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
    print("\n[1/5] Creating Pre-MOM Implementation Safety Backup...")
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file_path = os.path.join(
        backend_dir, "data", f"backup_flow_{TARGET_FLOW_ID}_before_mom_complete_{timestamp_str}.json"
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
    print("\n[2/5] Constructing MOM Graph Topology...")
    updated_flow_data, new_nodes, new_edges = build_mom_graph(target_flow.flow_data)
    print(f"  Newly Created Nodes: {len(new_nodes)} (11 main + 68 sub-standards)")
    print(f"  Newly Created Edges: {len(new_edges)} (11 fwd + 11 back + 68 fwd + 68 back + 68 chapter-back)")
    assert len(new_nodes) == 79  # 11 + 68
    assert len(new_edges) == 226  # 11 + 11 + 68 + 68 + 68
    assert len(updated_flow_data["nodes"]) == len(orig_nodes) + 79
    assert len(updated_flow_data["edges"]) == len(orig_edges) + 226

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

    # 4. Store All 68 Sub-Standard Answers in PostgreSQL
    print("\n[4/5] Storing Official Descriptions & Interpretations in PostgreSQL...")
    saved_answers_count = 0

    for i in range(1, 12):
        for letter, desc, interp in MOM_DATA[i]["subs"]:
            sub_node_id = f"mom_{i}_{letter}"

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
    node_map = {n["id"]: n for n in ret_nodes}
    assert len(ret_nodes) == len(orig_nodes) + 79
    assert len(ret_edges) == len(orig_edges) + 226
    print(f"  ✓ Verified GET /flows: {len(ret_nodes)} nodes, {len(ret_edges)} edges.")

    # 5.2 Verify 11 MOM Main Standard Buttons on standard_mom
    mom_chapter_ret = node_map.get(CHAPTER_NODE_ID)
    assert mom_chapter_ret is not None
    mom_btns = mom_chapter_ret.get("data", {}).get("buttons", [])
    assert len(mom_btns) == 11, f"Expected 11 MOM buttons, found {len(mom_btns)}"
    for idx, b in enumerate(mom_btns):
        assert b["id"] == f"standard_mom__mom_{idx+1}__{idx}"
        assert b["next"] == f"mom_{idx+1}"
        assert b["label"] == f"STANDARD: MOM.{idx+1}"
    print("  ✓ All 11 main-standard buttons on standard_mom verified.")

    # 5.3 Verify all 68 sub-standard nodes and answer GET endpoints
    total_sub_verified = 0
    for i in range(1, 12):
        std_id = f"mom_{i}"
        std_n = node_map.get(std_id)
        assert std_n is not None, f"Node {std_id} missing"
        assert std_n["type"] == "menu"

        s_btns = std_n.get("data", {}).get("buttons", [])
        expected_subs = MOM_DATA[i]["subs"]
        assert len(s_btns) == len(expected_subs) + 1  # subs + back

        for s_idx, (letter, desc, interp) in enumerate(expected_subs):
            sub_id = f"mom_{i}_{letter}"
            sub_n = node_map.get(sub_id)
            assert sub_n is not None, f"Sub-node {sub_id} missing"
            assert sub_n["type"] == "answer"

            sub_b = sub_n.get("data", {}).get("buttons", [])
            assert len(sub_b) == 2
            assert sub_b[0]["next"] == std_id
            assert sub_b[1]["next"] == CHAPTER_NODE_ID

            # GET Answer API verification
            ans_code, ans_data = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_id}/answer?language=en")
            assert ans_code == 200, f"GET answer failed for {sub_id}"
            assert len(ans_data["blocks"]) == 2, f"Expected 2 blocks for {sub_id}"
            assert ans_data["blocks"][0]["position"] == 1
            assert "### Description" in ans_data["blocks"][0]["content"]
            assert ans_data["blocks"][1]["position"] == 2
            assert "### Interpretation" in ans_data["blocks"][1]["content"]

            total_sub_verified += 1

    assert total_sub_verified == 68, f"Expected 68 verified sub-standards, got {total_sub_verified}"
    print(f"  ✓ Exactly 68 unique sub-standard nodes, buttons, and 2-block answers verified.")

    # 5.4 Graph Duplicate & Referential Checks
    from collections import Counter
    node_id_counts = Counter(n["id"] for n in ret_nodes)
    dup_n = [k for k, v in node_id_counts.items() if v > 1]
    assert len(dup_n) == 0, f"Duplicate node IDs: {dup_n}"
    print("  ✓ Zero duplicate node IDs.")

    edge_id_counts = Counter(e["id"] for e in ret_edges)
    dup_e = [k for k, v in edge_id_counts.items() if v > 1 and "default" not in k]
    assert len(dup_e) == 0, f"Duplicate edge IDs: {dup_e}"
    print("  ✓ Zero duplicate edge IDs.")

    missing_sources = [e for e in ret_edges if e.get("source") not in node_map]
    missing_targets = [e for e in ret_edges if e.get("target") not in node_map]
    assert len(missing_sources) == 0, f"Dangling sources: {missing_sources}"
    assert len(missing_targets) == 0, f"Dangling targets: {missing_targets}"
    print("  ✓ 100% of edge sources and targets exist in graph.")

    # 5.5 Handle matching check for all MOM nodes
    mom_handle_mismatches = []
    for e in ret_edges:
        src = e.get("source", "")
        handle = e.get("sourceHandle")
        if src.startswith("mom_") or src == CHAPTER_NODE_ID:
            s_node = node_map.get(src)
            if s_node:
                b_ids = {b["id"] for b in s_node.get("data", {}).get("buttons", [])}
                if handle and handle not in b_ids:
                    mom_handle_mismatches.append((e["id"], src, handle))
    assert len(mom_handle_mismatches) == 0, f"Handle mismatches: {mom_handle_mismatches}"
    print("  ✓ 100% of MOM edge handles match button IDs.")

    # 5.6 Preservation of Existing AAC, COP, and Hospital Answers
    db = SessionLocal()
    for h in ["hospitals_eligibility", "hospitals_application", "hospitals_assessment", "hospitals_documents", "hospitals_fee_structure"]:
        ha = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID, NodeAnswer.node_id == h).first()
        assert ha is not None, f"Hospital answer {h} missing!"
    for a in ["aac_1_a", "aac_1_b", "aac_1_c", "aac_1_d"]:
        aa = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID, NodeAnswer.node_id == a).first()
        assert aa is not None, f"AAC answer {a} missing!"
    # Sample COP answers check
    for c in ["cop_1_a", "cop_2_a", "cop_10_a", "cop_18_e", "cop_20_a"]:
        ca = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID, NodeAnswer.node_id == c).first()
        assert ca is not None, f"COP answer {c} missing!"
    total_db_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID).count()
    print(f"  ✓ All existing AAC, COP, and Hospital answers preserved.")
    print(f"  ✓ Total database answers for Flow 3: {total_db_answers} (144 existing + 68 MOM = 212)")
    assert total_db_answers == 212
    db.close()

    print("\n" + "=" * 80)
    print("MOM.1 - MOM.11 INTEGRATION AND AUDIT 100% SUCCESSFUL")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

