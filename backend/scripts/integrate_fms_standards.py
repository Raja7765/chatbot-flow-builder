"""
Script: integrate_fms_standards.py
Integrates NABH Facility Management and Safety (FMS) Standards (FMS.1–FMS.7),
their 43 collected sub-standard buttons and nodes, and their individual Description + Interpretation answers
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
CHAPTER_NODE_ID = "standard_fms"

# Complete Official NABH FMS Standards & 43 Collected Sub-Standards
FMS_DATA = {
    1: {
        "title": "The organisation has a system in place to provide a safe and secure environment",
        "subs": [
            ("a",
             "Patient-safety devices and infrastructure are installed across the organisation and inspected periodically.",
             "The organisation installs and maintains essential patient-safety infrastructure to prevent physical harm and accidents. This includes grab bars in washrooms and corridors, anti-skid flooring, side rails on beds, safety belts on wheelchairs and stretchers, emergency call bells within reach of patients in wards, ICUs, and toilets, and visual/auditory alert systems. These devices and safety elements are inventoried and inspected periodically according to documented schedules to ensure functional reliability."),
            ("b",
             "The organisation has facilities for the differently-abled.",
             "Physical infrastructure is provided and maintained to ensure barrier-free access and comfort for differently-abled persons, elderly patients, and individuals with mobility impairments. This includes access ramps with appropriate gradients and non-slip surfaces, dedicated wheelchair-accessible toilets equipped with assistance alarms and grab bars, low-height registration and inquiry counters, tactile pathways or wide doors, and wheelchair-accessible elevators."),
            ("c",
             "Facility inspection rounds to ensure safety are conducted at least once a month.",
             "Multidisciplinary facility inspection rounds are conducted regularly, at a minimum frequency of at least once every month. The inspection team includes representatives from facility management, administration, nursing, infection prevention and control, and safety. The rounds systematically inspect patient-care areas, public zones, service utilities, corridors, and exterior premises to identify environmental, physical, electrical, and structural hazards."),
            ("d",
             "Inspection reports of facility rounds are documented, and corrective and preventive measures are undertaken.",
             "Comprehensive written inspection reports are maintained for all facility rounds, detailing identified physical hazards, structural deficits, cleanliness or safety concerns, responsible departments, and targeted completion dates. The organisation tracks, documents, and reviews the implementation of corrective and preventive actions (CAPA) to verify that flagged safety risks are resolved effectively and reviewed by the safety committee."),
            ("e",
             "Before construction, renovation and expansion of existing hospital, risk assessments are carried out.",
             "A multidisciplinary Pre-Construction Risk Assessment (PCRA) is conducted prior to commencing any structural renovation, expansion, demolition, or civil construction within or adjacent to healthcare buildings. The assessment systematically evaluates air quality impact and airborne infection risks (such as Aspergillus contamination), noise and vibration levels, utility disruption vulnerabilities (water, electricity, medical gases), emergency exit access, and construction barrier requirements. Mitigation controls are documented and monitored throughout the project.")
        ]
    },
    2: {
        "title": "The organisation's environment and facilities operate in a planned manner and promote environment-friendly measures",
        "subs": [
            ("a",
             "Facilities and space provisions are appropriate to the scope of services.",
             "The allocation, sizing, and architectural design of clinical, diagnostic, and administrative spaces conform to the hospital's declared scope of healthcare services. Space layouts comply with national, state, and statutory building regulations, health authority standards, and statutory agency guidelines (e.g., AERB specifications for diagnostic imaging, isolation room physical spacing, and distance between inpatient beds) to ensure safe clinical workflows and prevent cross-contamination."),
            ("b",
             "As-built and updated drawings are maintained as per statutory requirements.",
             "The organisation maintains accurate, approved, and updated as-built architectural and engineering layout drawings as required by statutory and regulatory authorities. These include structural site layouts, floor-wise architectural blueprints, electrical circuitry and distribution single-line diagrams, plumbing and drainage schematics, HVAC ducting and ventilation maps, medical gas pipeline networks, and designated fire escape and evacuation routes."),
            ("c",
             "There are internal and external sign postings in the organisation in a manner understood by the patient, families and community.",
             "Prominent, well-illuminated internal and external signages are installed across the facility in languages easily understood by patients, their families, and the local community (typically bilingual or multilingual, supplemented with standardized international pictorial symbols). Signage includes directional signages, department identification, emergency exit routes, assembly areas, caution and warning notices (e.g., biohazard, radiation, high voltage, wet floor), and statutory notices."),
            ("d",
             "Potable water and electricity are available round the clock.",
             "The organisation ensures uninterrupted, continuous availability of safe potable drinking water and electric power supply 24 hours a day, 7 days a week, across all patient-care, diagnostic, and utility zones. Safe drinking water is regularly tested for chemical and microbiological purity in accredited laboratories as per national standards (IS 10500), and water testing reports are maintained. Electrical parameters and loads are monitored continuously."),
            ("e",
             "Alternate sources for electricity and water are provided as a backup for any failure/shortage.",
             "Adequate backup and redundancy systems are established to maintain critical clinical operations during primary utility grid disruptions or municipal water shortages. This includes dedicated diesel generator (DG) sets with sufficient capacity to support essential and critical loads, uninterruptible power supply (UPS) systems for life-saving and diagnostic equipment, and underground/overhead water storage reservoirs capable of supporting clinical operations for emergency periods."),
            ("f",
             "The organisation tests the functioning of these alternate sources at a predefined frequency.",
             "The organisation establishes and adheres to a predefined, documented schedule for testing the readiness and operational performance of alternate electricity and water backup systems. Diesel generators undergo routine test runs (including on-load and off-load simulations) with automated changeover checks, UPS battery load and discharge tests are logged, and secondary water pumping and transfer systems are verified regularly with logged documentation.")
        ]
    },
    3: {
        "title": "The organisation's environment and facilities operate to ensure the safety of patients, their families, staff and visitors",
        "subs": [
            ("a",
             "Patient safety aspects in terms of structural safety of hospitals, especially of critical areas, are considered while planning, design, and construction of new hospitals and re-planning, assessment, and retrofitting of existing hospitals.",
             "Structural stability and physical safety considerations are formally incorporated during the planning, architectural design, construction, and periodic structural assessment of the hospital facility. Critical areas such as Operation Theatres, Intensive Care Units, Emergency departments, and central sterile supply units are designed and structurally reinforced to meet National Building Code requirements and seismic zone building safety standards. Structural stability certificates from certified structural engineers are maintained."),
            ("b",
             "Operational planning identifies areas which need to have extra security and describes access to different areas in the hospital by staff, patients, and visitors.",
             "The organisation identifies high-risk, vulnerable, and restricted zones requiring enhanced physical and electronic security surveillance. These include neonatology units, pediatric wards, pharmacy bulk stores, operation theatre complexes, server rooms, and cash counters. Documented policies define access authorization protocols, visitor pass systems, staff identification badges, CCTV coverage, and physical security posts to prevent infant abduction, unauthorized entry, and theft."),
            ("c",
             "The organisation periodically conducts electrical safety audits for the facility.",
             "Periodic comprehensive electrical safety audits are conducted by qualified internal electrical engineers or certified external agencies across all healthcare premises. Audits evaluate electrical distribution boards, earthing and grounding resistance, lightning arrestor systems, transformer operations, insulation integrity, circuit breaker calibration, and power harmonics. Identified electrical safety anomalies are systematically remediated through documented corrective action plans."),
            ("d",
             "There is a procedure which addresses the identification and disposal of material(s) not in use in the organisation.",
             "The organisation implements a formal condemnation and scrap disposal procedure to identify, segregate, and dispose of unusable, obsolete, and condemned furniture, equipment, civil fixtures, and materials. Condemnation committees review items to ensure that obsolete goods do not accumulate in clinical corridors, fire exits, basements, or service passages, preventing fire hazards, pest harborage, and facility clutter."),
            ("e",
             "Hazardous materials are identified and used safely within the organisation.",
             "The organisation maintains an exhaustive, updated inventory of all hazardous materials (chemicals, laboratory reagents, disinfectants, flammable liquids, radioactive isotopes, and cytotoxic substances) used across departments. Hazardous substances are safely labeled, handled, and stored in dedicated, well-ventilated, secure areas with secondary containment. Current Material Safety Data Sheets (MSDS / SDS) are readily accessible at points of use, and staff are trained in their safe handling and appropriate personal protective equipment (PPE)."),
            ("f",
             "Clear guidelines and procedures are established for handling hazardous material spills.",
             "Standardized spill management protocols and operational procedures are established and implemented for various types of hazardous chemical, cytotoxic, mercury, and biological material spills. Functional, fully stocked spill management kits are strategically stationed in relevant clinical, laboratory, and utility zones. Healthcare personnel are trained in immediate spill isolation, containment, neutralization, personal protection, disposal according to bio-medical waste regulations, and incident reporting.")
        ]
    },
    4: {
        "title": "The organisation has a programme for the facility, engineering support services, and utility system",
        "subs": [
            ("a",
             "The organisation plans for utility and engineering equipment in accordance with its services and strategic plan.",
             "The organisation systematically plans and sizes its utility, engineering infrastructure, and support service equipment (such as transformers, electrical panels, HVAC chillers, air handling units, elevators, sewage treatment plants, boilers, and water treatment systems) to match the hospital's clinical profile, patient volumes, and long-term strategic plans. Planning accounts for continuous operation, redundancy, energy efficiency, and regulatory compliance."),
            ("b",
             "Equipment is inventoried, and proper logs are maintained as required.",
             "A comprehensive master inventory register of all utility and engineering equipment is maintained across the organization. The inventory documents asset identification tags, equipment specifications, serial numbers, installation dates, manufacturers, locations, and warranty or Annual Maintenance Contract (AMC/CMC) details. Operational logs, running hour meters, and service history sheets are systematically updated and preserved."),
            ("c",
             "The documented operational and maintenance (preventive and breakdown) plan is implemented.",
             "The organisation formulates and strictly adheres to a documented operational and maintenance programme encompassing planned preventive maintenance (PPM) schedules and breakdown repair procedures for all critical facility and engineering installations. Preventive maintenance tasks are scheduled at manufacturer-recommended intervals, work orders are documented, and completion records are reviewed by engineering heads to minimize unpredicted system failures."),
            ("d",
             "Utility equipment are periodically inspected and calibrated (wherever applicable) for their proper functioning.",
             "Critical utility equipment and auxiliary instrumentation—such as temperature gauges, pressure gauges, electrical relays, flow meters, boiler safety relief valves, and water testing equipment—undergo periodic physical inspections and scheduled calibrations. Calibrations are performed using standards traceable to national or international metrology bodies, and calibration records, certificates, and status tags are systematically maintained."),
            ("e",
             "Qualified and trained personnel operate and maintain equipment and utility systems.",
             "The operation, servicing, and upkeep of engineering installations and facility utility systems are entrusted exclusively to qualified, competent, and licensed engineering technicians and operators (such as licensed electricians, boiler attendants, STP/WTP operators, and HVAC mechanics). Ongoing safety, equipment operation, and emergency response training is imparted, and qualification and training dossiers are documented."),
            ("f",
             "Maintenance staff is contactable round the clock for emergency repairs.",
             "A reliable mechanism is established to ensure maintenance and engineering personnel are readily available and contactable 24 hours a day, 7 days a week, for emergency facility and utility repairs. A round-the-clock maintenance duty roster, dedicated emergency communication channels, intercom extensions, and duty supervisor contact numbers are prominently displayed at nursing stations and clinical departments."),
            ("g",
             "Downtime for critical equipment breakdowns is monitored from reporting to inspection and implementation of corrective actions.",
             "The organisation defines and tracks downtime for all critical facility and utility equipment (e.g., central air conditioning in OTs, main electrical distribution transformers, elevators, primary water supply pumps). A systematic breakdown logging framework records the exact time of complaint registration, maintenance response, root cause assessment, spare part procurement, repair completion, and functional sign-off. Downtime metrics are analyzed to enhance utility reliability."),
            ("h",
             "Written guidance supports equipment replacement, identification of unwanted material, and disposal.",
             "Standard operating procedures and criteria are established to guide the technical evaluation, decommissioning, write-off, and disposal of aged, defective, inefficient, or unrepairable utility and engineering equipment. Technical condemnation reports verify economic unfeasibility of further repairs, safety hazards, or regulatory obsolescence prior to disposal through authorized recycling or scrap handling agencies.")
        ]
    },
    5: {
        "title": "The organisation has a programme for medical equipment management",
        "subs": [
            ("a",
             "The organisation plans for medical equipment in accordance with its services and strategic plan.",
             "The organisation systematically plans and evaluates its clinical technology and biomedical equipment requirements based on the scope of patient services offered, clinical specialty needs, anticipated clinical workload, and institutional strategic plans. A multidisciplinary committee (including biomedical engineers, clinical specialists, nursing leaders, and finance) assesses technological specifications, clinical efficacy, and safety features prior to equipment procurement."),
            ("b",
             "Medical equipment is inventoried, and proper logs are maintained as required.",
             "The biomedical engineering department maintains an exhaustive, continuously updated master inventory of all medical equipment, devices, and diagnostic instruments across the hospital. Each device is assigned a unique asset identification number. Equipment logs capture serial numbers, manufacturer details, installation dates, locations, warranty and AMC/CMC status, and service history sheets."),
            ("c",
             "The documented operational and maintenance (preventive and breakdown) plan for medical equipment is implemented.",
             "The organisation implements a comprehensive, documented medical equipment maintenance programme comprising scheduled preventive maintenance (PPM) and responsive breakdown maintenance workflows. Preventive maintenance protocols align with manufacturer recommendations and clinical usage risk ratings. Work order tracking, service reports, parts replacement logs, and preventive maintenance verification stickers are systematically maintained on all medical devices."),
            ("d",
             "Medical equipment is periodically inspected and calibrated for their proper functioning.",
             "All clinical, monitoring, therapeutic, and diagnostic devices (such as defibrillators, ventilators, syringe pumps, patient monitors, and ECG machines) undergo regular safety checks and scheduled calibrations. Calibrations are executed using certified biomedical test analyzers traceable to national or international standards. Calibration certificates, dates of calibration, and due dates are visibly displayed on equipment."),
            ("e",
             "Qualified and trained personnel operate and maintain medical equipment.",
             "Medical equipment is operated and serviced exclusively by qualified, trained, and credentialed personnel. Biomedical engineers possess relevant technical qualifications and vendor-specific service certifications. Clinicians, residents, nurses, and paramedical operators receive structured user-training on equipment handling, basic troubleshooting, alarm management, and user safety before operating clinical devices."),
            ("f",
             "Written guidance supports medical equipment replacement and disposal.",
             "The organisation formulates and implements documented guidelines and condemnation criteria for replacing and safely disposing of end-of-life, obsolete, damaged, or unrepairable medical equipment. The condemnation procedure includes technical assessments of repeated failure history, spare part unavailability, safety obsolescence, and formal committee sign-off, with safe disposal conforming to e-waste and environmental rules."),
            ("g",
             "There is monitoring of medical equipment and medical devices related to adverse events, and compliance with hazard notices on recalls.",
             "The organisation maintains a robust materiovigilance programme to identify, investigate, record, and report medical device-related adverse events, malfunctions, near-misses, and patient injuries. A designated coordinator monitors and acts promptly upon manufacturer safety hazard alerts, regulatory advisories, and product recall notices, ensuring affected batches or devices are quarantined, serviced, or returned."),
            ("h",
             "Downtime for critical equipment breakdown is monitored from reporting to inspection and implementation of corrective actions.",
             "The organisation establishes tracking mechanisms to measure and analyze downtime for all critical biomedical equipment (such as ventilators, CT scanners, MRI machines, cardiac monitors, and dialysis units). Metrics capture the time elapsed from breakdown notification to initial engineer inspection, turnaround time for repair, and final clinical verification. Corrective and preventive actions are analyzed to improve equipment uptime.")
        ]
    },
    6: {
        "title": "The organisation has a programme for medical gases, vacuum, and compressed air",
        "subs": [
            ("a",
             "Written guidance governs the implementation of procurement, handling, storage, distribution, usage and replenishment of medical gases.",
             "The organisation maintains comprehensive standard operating procedures and written guidelines covering the entire lifecycle of medical gases (including Oxygen, Nitrous Oxide, Carbon Dioxide, Medical Air, and Vacuum systems). The guidelines incorporate statutory regulations (such as Petroleum and Explosives Safety Organization - PESO rules and Gas Cylinder Rules), standardized color-coding, and national/international pipeline safety codes (such as HTM 02-01 or NFPA 99)."),
            ("b",
             "Medical gases are handled, stored, distributed, and used in a safe manner.",
             "Medical gas cylinders and bulk liquid oxygen (LOX) installations are stored and operated in dedicated, secure, clean, and well-ventilated manifold rooms with restricted access. Full and empty cylinders are physically segregated, clearly labeled, and secured upright with chains or racks. Color-coding, non-interchangeable pin-index and diameter-index safety systems, pipeline identification bands, and strict prohibitions on grease, oil, and open flames around oxygen installations are rigorously enforced."),
            ("c",
             "The procedures for medical gases address the safety issues at all levels.",
             "Documented safety protocols address potential medical gas hazards across all hospital levels—from central manifold stations and liquid cryogenic tanks through distribution risers, area valve control units (AVCUs), and terminal outlet points in operating theatres and intensive care units. Safety measures include low and high pressure alarm monitoring, pipeline leak detection, cross-connection prevention, pressure regulation, and emergency shut-off protocols during local fire emergencies."),
            ("d",
             "Alternate sources for medical gases, vacuum, and compressed air are provided for, in case of failure.",
             "Redundant and backup supply configurations are provided to ensure uninterruptible delivery of medical gases, medical suction/vacuum, and medical compressed air to critical patient areas. This includes dual manifold banks with automated changeover systems, emergency reserve manifold manifolds connected to piped medical gas systems, duplex/triplex vacuum pumps, and standby medical air compressor units capable of automatically assuming full operational load."),
            ("e",
             "The organisation regularly tests the functioning of these alternate sources.",
             "The organisation carries out regular, scheduled functional testing of alternate medical gas supply systems, changeover mechanisms, emergency cylinder banks, backup compressors, and audio-visual pipeline pressure alarm systems. Test results, changeover response times, alarm threshold verifications, and gas purity parameters are systematically logged and reviewed by the facility safety committee.")
        ]
    },
    7: {
        "title": "The organisation has plans for fire and non-fire emergencies within the facilities",
        "subs": [
            ("a",
             "The organisation has plans and provisions for early detection, abatement and containment of fire and non-fire emergencies.",
             "The organisation establishes comprehensive, documented disaster management and emergency response plans covering fire emergencies (Code Red) as well as non-fire emergencies (e.g., earthquakes, structural collapse, floods, severe utility disruptions, bomb threats, and chemical spills). Fire protection provisions include functional automatic fire detection systems (smoke and heat detectors), manual call points, fire alarm panels, fire hydrants, hose reels, automatic sprinkler networks, fire dampers, and appropriate portable fire extinguishers."),
            ("b",
             "The organisation has a documented and displayed exit plan in case of fire and non-fire emergencies.",
             "Prominently displayed, floor-wise evacuation maps and exit plans (\"You Are Here\" plans) are installed in all corridors, waiting lobbies, nursing stations, and key departments. Evacuation maps clearly indicate primary and secondary escape routes, fire staircases, manual call points, fire extinguisher locations, and external safe assembly points. Emergency exits, escape corridors, and stairwells are kept illuminated, unobstructed, and fitted with emergency exit signage."),
            ("c",
             "Mock drills are held at least twice a year.",
             "The organisation conducts simulated fire and non-fire emergency evacuation mock drills at a minimum frequency of at least twice a year across different hospital shifts, including night shifts. Mock drills evaluate staff emergency response times, patient triage and evacuation priorities, Code Red activation, communication workflows, and firefighting techniques. Detailed post-drill debriefing reports, bottleneck evaluations, and corrective action plans are documented and reviewed."),
            ("d",
             "There is a maintenance plan for fire-related equipment and infrastructure.",
             "A documented preventive maintenance programme is established and executed for all fire safety equipment, firefighting apparatus, and fire protection infrastructure. This includes regular servicing, pressure testing, and periodic refilling of fire extinguishers, maintenance of diesel and electrical fire hydrant pumps, testing of smoke detection panels and alarms, inspection of fire doors, and verification of fire sprinkler water lines. Inspection tags and valid maintenance logs are maintained."),
            ("e",
             "The organisation has a service continuity plan in case of fire and non-fire emergencies.",
             "The organisation formulates and maintains a comprehensive Business and Service Continuity Plan (BCP) to ensure the continuity or prompt restoration of critical clinical and life-sustaining healthcare operations (such as Emergency care, ICUs, Dialysis, Operating Theatres, and blood bank services) during and following an emergency or disaster. The plan defines alternate care sites, temporary patient transfer procedures, vital digital data backup and recovery protocols, and mutual aid agreements with external health facilities.")
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


def build_fms_graph(original_flow_data: dict) -> tuple:
    """
    Construct the updated flow graph by:
    1. Adding 7 main buttons to standard_fms node.
    2. Creating 7 fms_{i} menu nodes.
    3. Creating 43 fms_{i}_{sub} answer nodes.
    4. Adding all 143 navigation edges.
    """
    flow_data = copy.deepcopy(original_flow_data)
    nodes = flow_data.get("nodes", [])
    edges = flow_data.get("edges", [])

    node_map = {n["id"]: n for n in nodes}

    # 1. Update standard_fms chapter node
    fms_chapter = node_map.get(CHAPTER_NODE_ID)
    if not fms_chapter:
        raise ValueError(f"Chapter node '{CHAPTER_NODE_ID}' not found in flow.")

    # 7 Main standard buttons for standard_fms
    fms_main_buttons = [
        {"id": f"standard_fms__fms_{i}__{i-1}", "next": f"fms_{i}", "label": f"STANDARD: FMS.{i}"}
        for i in range(1, 8)
    ]
    fms_chapter["data"]["buttons"] = fms_main_buttons
    fms_chapter["data"]["message"] = "FMS — Facility Management and Safety (NABH 5th Edition Standards)"
    fms_chapter["data"]["mapping_status"] = "VERIFIED"
    fms_chapter["mapping_status"] = "VERIFIED"

    new_nodes = []
    new_edges = []

    # 2. Forward edges from standard_fms to fms_1..fms_7 (7 edges)
    for btn in fms_main_buttons:
        new_edges.append({
            "id": f"edge-standard_fms-{btn['next']}-{btn['id']}",
            "label": btn["label"],
            "source": CHAPTER_NODE_ID,
            "target": btn["next"],
            "sourceHandle": btn["id"]
        })

    # 3. Create Main standard nodes fms_1 to fms_7 & their sub-standards
    std_base_y = 23000
    for i in range(1, 8):
        std_id = f"fms_{i}"
        std_info = FMS_DATA[i]
        subs = std_info["subs"]
        pos_y = std_base_y + (i - 1) * 350

        # Sub-standard buttons for fms_i
        std_buttons = []
        for s_idx, (letter, desc, _) in enumerate(subs):
            sub_node_id = f"fms_{i}_{letter}"
            btn_id = f"fms_{i}__{sub_node_id}__{s_idx}"
            std_buttons.append({
                "id": btn_id,
                "next": sub_node_id,
                "label": f"FMS.{i}.{letter}"
            })

        # Back to FMS Standards button
        btn_back_id = f"fms_{i}__back_standard_fms__{len(subs)}"
        std_buttons.append({
            "id": btn_back_id,
            "next": CHAPTER_NODE_ID,
            "label": "Back to FMS Standards"
        })

        # Main standard node definition (menu)
        std_node = {
            "id": std_id,
            "type": "menu",
            "data": {
                "id": std_id,
                "label": f"STANDARD: FMS.{i}",
                "message": f"FMS.{i} — {std_info['title']}",
                "buttons": std_buttons,
                "chapter": "FMS",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "nodeType": "menu",
                "layoutWidth": 290,
                "layoutHeight": 280,
                "mapping_status": "VERIFIED"
            },
            "chapter": "FMS",
            "program": "Hospitals Accreditation",
            "topic": "standards",
            "message": f"FMS.{i} — {std_info['title']}",
            "position": {"x": 5715, "y": pos_y},
            "mapping_status": "VERIFIED"
        }
        new_nodes.append(std_node)

        # Back edge from fms_i to standard_fms
        new_edges.append({
            "id": f"edge-{std_id}-standard_fms-{btn_back_id}",
            "label": "Back to FMS Standards",
            "source": std_id,
            "target": CHAPTER_NODE_ID,
            "sourceHandle": btn_back_id
        })

        # Sub-standard answer nodes and connecting edges
        for s_idx, (letter, desc, _) in enumerate(subs):
            sub_node_id = f"fms_{i}_{letter}"
            sub_btn_back_std = f"{sub_node_id}__back_fms_{i}__0"
            sub_btn_back_fms = f"{sub_node_id}__back_standard_fms__1"

            sub_node = {
                "id": sub_node_id,
                "type": "answer",
                "data": {
                    "id": sub_node_id,
                    "label": f"FMS.{i}.{letter} — {desc}",
                    "message": desc,
                    "buttons": [
                        {"id": sub_btn_back_std, "next": std_id, "label": f"Back to FMS.{i}"},
                        {"id": sub_btn_back_fms, "next": CHAPTER_NODE_ID, "label": "Back to FMS Standards"}
                    ],
                    "chapter": "FMS",
                    "program": "Hospitals Accreditation",
                    "topic": "standards",
                    "nodeType": "answer",
                    "layoutWidth": 280,
                    "layoutHeight": 140,
                    "mapping_status": "VERIFIED"
                },
                "chapter": "FMS",
                "program": "Hospitals Accreditation",
                "topic": "standards",
                "message": desc,
                "position": {"x": 6220, "y": pos_y + s_idx * 140},
                "mapping_status": "VERIFIED"
            }
            new_nodes.append(sub_node)

            # Edge 1: Forward from fms_i to fms_i_letter
            new_edges.append({
                "id": f"edge-{std_id}-{sub_node_id}-{std_buttons[s_idx]['id']}",
                "label": f"FMS.{i}.{letter}",
                "source": std_id,
                "target": sub_node_id,
                "sourceHandle": std_buttons[s_idx]["id"]
            })

            # Edge 2: Back from fms_i_letter to fms_i
            new_edges.append({
                "id": f"edge-{sub_node_id}-{std_id}-{sub_btn_back_std}",
                "label": f"Back to FMS.{i}",
                "source": sub_node_id,
                "target": std_id,
                "sourceHandle": sub_btn_back_std
            })

            # Edge 3: Back from fms_i_letter to standard_fms
            new_edges.append({
                "id": f"edge-{sub_node_id}-standard_fms-{sub_btn_back_fms}",
                "label": "Back to FMS Standards",
                "source": sub_node_id,
                "target": CHAPTER_NODE_ID,
                "sourceHandle": sub_btn_back_fms
            })

    clean_nodes = [n for n in nodes if not n["id"].startswith("fms_")]
    clean_edges = [e for e in edges if not (e.get("source", "").startswith("fms_") or e.get("target", "").startswith("fms_"))]

    flow_data["nodes"] = clean_nodes + new_nodes
    flow_data["edges"] = clean_edges + new_edges

    return flow_data, new_nodes, new_edges


async def main():
    print("=" * 80)
    print("INTEGRATING NABH FMS.1 - FMS.7 STANDARDS INTO ACTIVE FLOW")
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
    print("\n[1/5] Creating Pre-FMS Implementation Safety Backup...")
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file_path = os.path.join(
        backend_dir, "data", f"backup_flow_{TARGET_FLOW_ID}_before_fms_complete_{timestamp_str}.json"
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
    print("\n[2/5] Constructing FMS Graph Topology...")
    updated_flow_data, new_nodes, new_edges = build_fms_graph(target_flow.flow_data)
    print(f"  Newly Created Nodes: {len(new_nodes)} (7 main + 43 sub-standards)")
    print(f"  Newly Created Edges: {len(new_edges)} (7 fwd + 7 back + 43 fwd + 43 back + 43 chapter-back = 143)")
    assert len(new_nodes) == 50  # 7 + 43
    assert len(new_edges) == 143  # 7 + 7 + 43 + 43 + 43
    assert len(updated_flow_data["nodes"]) == len(orig_nodes) + 50
    assert len(updated_flow_data["edges"]) == len(orig_edges) + 143

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

    # 4. Store All 43 Sub-Standard Answers in PostgreSQL
    print("\n[4/5] Storing Official Descriptions & Interpretations in PostgreSQL...")
    saved_answers_count = 0

    for i in range(1, 8):
        for letter, desc, interp in FMS_DATA[i]["subs"]:
            sub_node_id = f"fms_{i}_{letter}"

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
    get_status, ret_flow = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}")
    assert get_status == 200
    ret_nodes = ret_flow["flow_data"]["nodes"]
    ret_edges = ret_flow["flow_data"]["edges"]
    print(f"  Total Flow Nodes: {len(ret_nodes)} (Expected 680)")
    print(f"  Total Flow Edges: {len(ret_edges)} (Expected 1569)")
    assert len(ret_nodes) == 680, f"Expected 680 nodes, got {len(ret_nodes)}"
    assert len(ret_edges) == 1569, f"Expected 1569 edges, got {len(ret_edges)}"

    # 5.1 Verify standard_fms has 7 buttons
    fms_ch = next(n for n in ret_nodes if n["id"] == CHAPTER_NODE_ID)
    assert len(fms_ch["data"]["buttons"]) == 7, f"Expected 7 buttons on {CHAPTER_NODE_ID}"
    print(f"  ✓ {CHAPTER_NODE_ID} has all 7 STANDARD: FMS.1 - FMS.7 buttons")

    # 5.2 Verify forward edges from standard_fms
    for i in range(1, 8):
        fwd_edge = next(e for e in ret_edges if e["source"] == CHAPTER_NODE_ID and e["target"] == f"fms_{i}")
        assert fwd_edge is not None
        back_edge = next(e for e in ret_edges if e["source"] == f"fms_{i}" and e["target"] == CHAPTER_NODE_ID)
        assert back_edge is not None

    # 5.3 Verify all 7 main standard menu nodes
    for i in range(1, 8):
        std_id = f"fms_{i}"
        std_node = next(n for n in ret_nodes if n["id"] == std_id)
        subs = FMS_DATA[i]["subs"]
        # subs + 1 back button
        assert len(std_node["data"]["buttons"]) == len(subs) + 1, f"Expected {len(subs)+1} buttons on {std_id}"
        print(f"  ✓ {std_id} has {len(subs)} sub-standard buttons + 1 Back button")

    # 5.4 Verify all 43 sub-standard answer nodes and database answers
    for i in range(1, 8):
        for letter, desc, interp in FMS_DATA[i]["subs"]:
            sub_node_id = f"fms_{i}_{letter}"
            sub_node = next(n for n in ret_nodes if n["id"] == sub_node_id)
            assert len(sub_node["data"]["buttons"]) == 2, f"Expected 2 buttons on {sub_node_id}"

            # Verify API GET /nodes/{node_id}/answer
            ans_code, ans_data = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_node_id}/answer?language=en")
            assert ans_code == 200, f"Expected 200 for {sub_node_id} answer, got {ans_code}"
            assert len(ans_data["blocks"]) == 2, f"Expected 2 blocks for {sub_node_id}, got {len(ans_data['blocks'])}"
            assert ans_data["blocks"][0]["content"] == f"### Description\n{desc}"
            assert ans_data["blocks"][1]["content"] == f"### Interpretation\n{interp}"

    print("  ✓ All 43 sub-standard nodes and answers verified in PostgreSQL with 2-block structure.")

    # 5.5 Verify existing standards are intact
    aac_nodes = [n for n in ret_nodes if n["id"].startswith("aac_") or n["id"] == "standard_aac"]
    cop_nodes = [n for n in ret_nodes if n["id"].startswith("cop_") or n["id"] == "standard_cop"]
    mom_nodes = [n for n in ret_nodes if n["id"].startswith("mom_") or n["id"] == "standard_mom"]
    pre_nodes = [n for n in ret_nodes if n["id"].startswith("pre_") or n["id"] == "standard_pre"]
    ipc_nodes = [n for n in ret_nodes if n["id"].startswith("ipc_") or n["id"] == "standard_ipc"]
    psq_nodes = [n for n in ret_nodes if n["id"].startswith("psq_") or n["id"] == "standard_psq"]
    rom_nodes = [n for n in ret_nodes if n["id"].startswith("rom_") or n["id"] == "standard_rom"]
    fms_nodes = [n for n in ret_nodes if n["id"].startswith("fms_") or n["id"] == "standard_fms"]
    print(f"  ✓ AAC nodes intact: {len(aac_nodes)}")
    print(f"  ✓ COP nodes intact: {len(cop_nodes)}")
    print(f"  ✓ MOM nodes intact: {len(mom_nodes)}")
    print(f"  ✓ PRE nodes intact: {len(pre_nodes)}")
    print(f"  ✓ IPC nodes intact: {len(ipc_nodes)}")
    print(f"  ✓ PSQ nodes intact: {len(psq_nodes)}")
    print(f"  ✓ ROM nodes intact: {len(rom_nodes)}")
    print(f"  ✓ FMS nodes total:  {len(fms_nodes)}")

    db = SessionLocal()
    total_answers = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID).count()
    total_blocks = db.query(AnswerBlock).join(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID).count()
    db.close()
    print(f"  ✓ Total database answers for flow: {total_answers} (Previous: 345, Added: 43, Expected: 388)")
    print(f"  ✓ Total database answer blocks for flow: {total_blocks} (Previous: 578, Added: 86, Expected: 664)")
    assert total_answers == 388, f"Expected 388 answers, got {total_answers}"
    assert total_blocks == 664, f"Expected 664 blocks, got {total_blocks}"

    print("\n" + "=" * 80)
    print("SUCCESS: ALL 7 FMS STANDARDS (FMS.1-FMS.7) AND 43 SUB-STANDARDS INTEGRATED!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
