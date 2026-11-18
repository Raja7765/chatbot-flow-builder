"""
Script: complete_all_cop_standards.py
Audits and completes all COP sub-standard buttons, nodes, edges, and answers
for COP.1 through COP.20 in NABH QMitra active flow (a23710cb-3353-4811-97b7-5927ba6c6d25).
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
from app.models import Flow, NodeAnswer, AnswerBlock, format_utc_iso


TARGET_CHATBOT_ID = "96359635-3ff9-4bfb-befa-13827094b16e"
TARGET_FLOW_ID = "a23710cb-3353-4811-97b7-5927ba6c6d25"
CHAPTER_NODE_ID = "standard_cop"

# Complete NABH 5th Edition COP Standards Metadata (COP.1 to COP.20)
COP_DATA = {
    1: {
        "title": "Uniform Care to Patients",
        "subs": [
            ("a", "Uniform care is provided following written guidance.",
             "The hospital must establish documented policies and procedures ensuring that identical clinical care processes (such as clinical management, nursing practices, or safety precautions) are applied consistently when similar clinical conditions are treated across different departments or settings (outpatient units, inpatient wards, day-care, and intensive care units)."),
            ("b", "The organisation has a uniform process for identification of patients and at a minimum, uses two identifiers.",
             "The hospital must use a standardized patient identification mechanism across all clinical areas. At least two unique patient identifiers (such as the patient's full name and hospital UHID number) must be used before any care-related activity, including medication administration, blood transfusion, sample collection, and clinical procedures. Room or bed numbers cannot be used as identifiers."),
            ("c", "Care shall be provided in consonance with applicable laws and regulations.",
             "All clinical and operational practices must explicitly align with local, state, and national statutory requirements and legal frameworks governing healthcare delivery (including the Clinical Establishments Act, PCPNDT Act, MTP Act, and Biomedical Waste Management Rules)."),
            ("d", "The organisation manages medico-legal cases in accordance with statutory requirements.",
             "The hospital must have clearly defined protocols describing what constitutes a medico-legal case (MLC) per statutory guidelines, along with standard operating procedures for documentation, safe custody of evidence, and prompt intimation to local law enforcement authorities."),
            ("e", "Initiation of appropriate care is guided by a system of triage.",
             "A systematic triage process must be implemented to sort and prioritize patients based on the urgency of their clinical needs so that timely and appropriate medical intervention is initiated, preventing delays for critical patients."),
        ]
    },
    2: {
        "title": "Emergency Services",
        "subs": [
            ("a", "There shall be an identified area in the organisation which is easily accessible to receive and manage emergency patients, with adequate and appropriate resources.",
             "The emergency department must be prominently situated, easily accessible from the hospital entrance with dedicated signage, and adequately resourced 24/7 with qualified emergency medical officers, trained emergency nurses, resuscitation bays, and emergency diagnostic support."),
            ("b", "Prevention of patient over-crowding is planned, and crowd management measures are implemented.",
             "The hospital must implement documented crowd management protocols and surge capacity plans to handle patient overcrowding in emergency areas, restricting unauthorized visitor entry, streamlining admissions, and tracking emergency turnaround times."),
            ("c", "Emergency care is provided in consonance with statutory requirements and in accordance with the written guidance.",
             "Emergency care must follow institutional Standard Operating Procedures (SOPs) based on standard clinical treatment guidelines and strictly conform to statutory obligations, such as the Supreme Court guidelines on emergency care and preservation of medico-legal records."),
            ("d", "The organisation manages medico-legal cases in accordance with statutory requirements.",
             "Clear procedures exist for receiving, treating, and reporting medico-legal cases presenting to the emergency department, including chain of custody for clinical specimens, police notification, and maintaining a secure MLC register."),
            ("e", "Initiation of appropriate care is guided by a system of triage.",
             "A validated triage system (e.g., color-coded red/yellow/green triage) must be operated in the emergency area by trained staff to ensure priority categorization and immediate attention for life-threatening conditions."),
            ("f", "Patients waiting in the emergency are reassessed as appropriate for change in status.",
             "Clinical reassessment of patients in the emergency waiting area must be conducted at defined intervals to detect any clinical deterioration and escalate triage priority without delay."),
            ("g", "Admission, discharge to home, or transfer to another organisation is documented.",
             "Final disposition of emergency patients—whether admitted as inpatient, discharged with home-care instructions, or transferred to another specialized center—must be systematically recorded with complete clinical handover summaries."),
        ]
    },
    3: {
        "title": "Ambulance Services",
        "subs": [
            ("a", "The organisation has access to ambulance services commensurate with the scope of the services provided by it.",
             "The hospital ensures access to round-the-clock ambulance services (BLS and/or ACLS) corresponding to its clinical specialty profile, either through hospital-owned vehicles or legally binding service contracts/MoUs with licensed external providers."),
            ("b", "There are adequate access and space for the ambulance(s).",
             "Dedicated ambulance bays, unobstructed driveways, and clear ingress/egress routes must be provided to facilitate smooth and expeditious transfer of patients without traffic interference."),
            ("c", "The ambulance(s) is fit for purpose and is appropriately equipped.",
             "Ambulances must meet national roadworthiness standards and National Ambulance Code specifications, equipped with oxygen supply, functional suction units, emergency resuscitation kits, stretchers, immobilization devices, and portable monitors."),
            ("d", "The ambulance(s) is operated by trained personnel.",
             "Ambulance crew must include licensed drivers trained in emergency transit and certified healthcare providers (paramedics, nurses, or doctors) trained in Basic and Advanced Life Support."),
            ("e", "The ambulance(s) is checked daily.",
             "Daily vehicle maintenance checks (fuel, tires, sirens, battery, emergency lights) must be documented in standardized vehicle inspection logs."),
            ("f", "Equipment is checked daily using a checklist.",
             "All biomedical and life-saving equipment inside the ambulance must be verified daily using a standardized checklist, with calibration and battery levels verified."),
            ("g", "A mechanism is in place to ensure that emergency medications are available in the ambulance.",
             "Standard emergency medications must be stocked in the ambulance, verified daily for quantities and expiry dates, and replenished immediately following each patient transit."),
            ("h", "The ambulance(s) has a proper communication system.",
             "Functional two-way communication systems (wireless radio, cellular communication, GPS tracking) must link the ambulance en route directly with the hospital emergency triage desk."),
            ("i", "The emergency department identifies opportunities to initiate treatment at the earliest when the patient is in transit to the organisation.",
             "Pre-arrival medical instructions and telemetry guidance are communicated to the transport crew to initiate early resuscitation and clinical interventions before the patient reaches the hospital doors."),
        ]
    },
    4: {
        "title": "Community Emergencies and Disaster Management",
        "subs": [
            ("a", "The organisation identifies potential community emergencies, epidemics and other disasters.",
             "The hospital performs a comprehensive Hazard Vulnerability Analysis (HVA) to identify probable natural disasters (earthquakes, floods), man-made incidents (fires, toxic spills, industrial mass casualties), and epidemic outbreaks applicable to its geographical region."),
            ("b", "The organisation manages community emergencies, epidemics and other disasters as per a documented plan.",
             "A multidisciplinary Disaster Management Plan (Hospital Incident Command System) is established, detailing leadership hierarchy, communication codes, surge bed allocations, triage areas, and departmental action cards."),
            ("c", "Provision is made for availability of medical supplies, equipment and materials during such emergencies.",
             "Dedicated emergency stockpiles of essential pharmaceuticals, personal protective equipment (PPE), intravenous fluids, surgical consumables, and portable ventilators are reserved and audited for emergency surge demands."),
            ("d", "The plan is tested at least twice a year.",
             "The disaster management plan must be tested through realistic mock drills at least twice every year, with documented debriefings and corrective action plans (CAPA) addressing observed gaps."),
        ]
    },
    5: {
        "title": "Cardio-Pulmonary Resuscitation Services",
        "subs": [
            ("a", "Resuscitation services are available to patients at all times.",
             "Cardiopulmonary resuscitation capability (Code Blue activation) must be available 24/7 across all hospital areas, ensuring rapid emergency response to cardiac arrests anywhere on campus."),
            ("b", "During cardio-pulmonary resuscitation, assigned roles and responsibilities are complied with.",
             "Resuscitation teams must function with clear, assigned roles (team leader, airway manager, compressor, drug administrator, and record keeper) in accordance with standardized resuscitation algorithms."),
            ("c", "Equipment and medications for use during cardio-pulmonary resuscitation are available in various areas of the organisation.",
             "Standardized crash carts containing functional defibrillators, bag-valve-masks, intubation sets, suction units, and unexpired emergency drugs must be strategically located and checked daily across all clinical and diagnostic areas."),
            ("d", "The events during cardio-pulmonary resuscitation are recorded.",
             "Comprehensive documentation of the resuscitation event (Code Blue form) must record exact timelines, interventions performed, defibrillation shocks, medications administered, and post-resuscitation outcomes."),
            ("e", "A multidisciplinary committee does a post-event analysis of cardiopulmonary resuscitations.",
             "A specialized resuscitation committee conducts multidisciplinary audits of all resuscitation events to assess protocol compliance, response times, clinical outcomes, and equipment readiness."),
            ("f", "Corrective and preventive measures are taken based on the post-event analysis.",
             "Actionable recommendations, protocol adjustments, and refresher training sessions are instituted based on post-event audit findings to continuously enhance CPR success rates."),
        ]
    },
    6: {
        "title": "Nursing Care",
        "subs": [
            ("a", "Nursing care is provided to patients in accordance with written guidance.",
             "Institutional nursing manuals and standard operating procedures govern nursing care activities across all wards, ensuring consistent standards in vital sign monitoring, hygiene, and patient safety."),
            ("b", "The organisation develops and implements nursing clinical practice guidelines reflecting current standards of practice.",
             "Nursing guidelines are regularly updated to reflect evidence-based nursing science and statutory recommendations, supporting standardized patient care workflows."),
            ("c", "Assignment of patient care is done as per current good clinical/nursing practice guidelines.",
             "Patient allocation is determined systematically based on patient acuity and nursing competency, maintaining safe nurse-to-patient staffing ratios across all shifts."),
            ("d", "The organisation implements acuity-based staffing to improve patient outcomes.",
             "Dynamic staffing models adjust nursing deployments in real time based on patient dependency scores, critical illness severity, and turnover rates."),
            ("e", "Nursing care is aligned and integrated with overall patient care.",
             "Nursing care plans are developed collaboratively with medical teams, ensuring that nursing interventions align with diagnostic, therapeutic, and dietary treatment goals."),
            ("f", "Care provided by nurses is documented in the patient record.",
             "Nurses maintain timely, dated, and signed clinical notes recording assessments, medication administration, nursing procedures, and patient responses in medical records."),
            ("g", "Nurses are provided with appropriate and adequate equipment for providing safe and efficient nursing care.",
             "Essential nursing equipment (infusion pumps, glucometers, vitals monitors, patient transfer aids) must be readily accessible, calibrated, and maintained in operational condition."),
            ("h", "Nurses are empowered to make patient care decisions within their scope of practice.",
             "Policies empower nurses to initiate emergency protocols, escalate clinical deterioration alerts, and advocate for patient safety within their certified clinical privileges."),
        ]
    },
    7: {
        "title": "Clinical Procedures",
        "subs": [
            ("a", "Procedures are performed based on the clinical needs of the patient.",
             "Every invasive and bedside clinical procedure must be clinically indicated, authorized by a qualified doctor, and documented in patient progress records."),
            ("b", "Performance of various clinical procedures is based on written guidance.",
             "Written clinical protocols govern the execution of clinical procedures outside the OT, specifying equipment, steps, precautions, and contraindications."),
            ("c", "Qualified personnel order, plan, perform and assist in performing procedures.",
             "Only credentialed and privileged clinicians and nurses perform or assist in diagnostic and therapeutic procedures based on verified competency."),
            ("d", "Care is taken to prevent adverse events like a wrong patient, wrong procedure and wrong site.",
             "Universal safety protocols and pre-procedure time-outs (verifying patient identity, procedure type, and anatomical site marking) are mandatory prior to any procedure."),
            ("e", "Informed consent is taken by the personnel performing the procedure, where applicable.",
             "Valid written informed consent outlining indications, procedural risks, benefits, and alternatives must be obtained directly by the performing clinician prior to intervention."),
            ("f", "The procedure is done adhering to standard precautions.",
             "Rigorous aseptic techniques, personal protective equipment, hand hygiene, and biomedical waste segregation are maintained throughout procedure execution."),
            ("g", "Patients are appropriately monitored during and after the procedure.",
             "Patient physiological vitals and pain levels are systematically monitored and documented during the procedure and in the designated recovery area until clinical stabilization."),
            ("h", "Procedures are documented accurately in the patient record.",
             "Comprehensive procedure notes detailing findings, techniques, specimens collected, medications or implants used, and post-procedure monitoring instructions are promptly entered into the patient record."),
        ]
    },
    8: {
        "title": "Transfusion Services",
        "subs": [
            ("a", "Scope of transfusion services is commensurate with the services provided by the organisation.",
             "The hospital defines its transfusion capabilities (whole blood, packed red cells, platelets, fresh frozen plasma) based on clinical specialties, supported by an authorized in-house blood center or formal MoU with a licensed external blood bank."),
            ("b", "Transfusion of blood and blood components is done safely.",
             "Stringent safety protocols govern blood collection, pre-transfusion cross-matching, bedside two-person verification of patient identity and unit labels, and rate-controlled administration using blood administration sets."),
            ("c", "Blood and blood components are used rationally.",
             "Clinical transfusion guidelines define authorized indications for blood component therapy, monitored through regular audits by the Hospital Transfusion Committee."),
            ("d", "Informed consent is obtained for transfusion of blood and blood components.",
             "Explicit informed consent detailing the necessity, benefits, potential risks, and alternatives of blood transfusion is documented prior to administration."),
            ("e", "Informed consent also includes patient and family education about the donation.",
             "Educational materials and counseling regarding voluntary blood donation and autologous options are made available to patients and their relatives."),
            ("f", "Blood/blood components are available for use in emergency situations within a defined time-frame.",
             "Emergency blood issue protocols (such as un-crossmatched O-negative or type-specific blood) ensure immediate availability for massive hemorrhage within established institutional turnaround times."),
            ("g", "Post-transfusion form is collected, reactions if any identified and are analysed for preventive and corrective actions.",
             "Standardized hemovigilance protocols require immediate cessation of transfusion upon adverse reactions, clinical management, laboratory workup, reporting, and committee root cause analysis."),
            ("h", "The organisation shall implement a quality assurance programme.",
             "Comprehensive quality control encompasses storage temperature monitoring, cross-matching proficiency testing, discard analysis, and regular transfusion committee reviews."),
        ]
    },
    9: {
        "title": "Intensive Care and High Dependency Units",
        "subs": [
            ("a", "Care of patients in intensive care and high dependency units is provided based on written guidance.",
             "Documented clinical practice guidelines and evidence-based care bundles govern patient care in ICUs and HDUs, standardizing hemodynamic management, ventilation, sedation, and infection prevention."),
            ("b", "The defined admission and discharge criteria for intensive care and high dependency units are implemented.",
             "Transparent, objective clinical scoring and triage criteria dictate patient admission, prioritization, and timely step-down or discharge from intensive care beds."),
            ("c", "Adequate and appropriate staff and medical equipment are available.",
             "Critical care units maintain round-the-clock intensivist coverage, specialized ICU nurse ratios (1:1 or 1:2 depending on ventilation status), multiparameter monitors, ventilators, and blood gas analysis facilities."),
            ("d", "The organisation endeavours to upgrade its physical infrastructure and equipment to meet national and international guidelines.",
             "Critical care physical plant layout, isolation cubicles, negative pressure facilities, and medical technology are continuously reviewed and upgraded to meet national critical care standards."),
            ("e", "Defined procedures and protocols are followed for managing situations involving bed shortages.",
             "Documented bed surge policies provide clinical escalation pathways, temporary stabilization protocols, and transfer arrangements when all critical care beds are fully occupied."),
            ("f", "Stringent infection control practices are documented and followed.",
             "Evidence-based infection control bundles—including central line insertion bundles (CLABSI), ventilator-associated pneumonia bundles (VAP), catheter bundles (CAUTI), and strict hand hygiene—are audited continuously."),
            ("g", "The organisation shall implement a structured quality-assurance programme.",
             "Dedicated quality indicators for critical care (ICU mortality, length of stay, ventilator days, re-intubation rates, bed occupancy) are tracked and reviewed monthly."),
            ("h", "The organisation has a well-defined mechanism to counsel the patient and/or family at periodic intervals and whenever there is a significant change in the patient's clinical condition.",
             "Regular, documented family counseling sessions conducted in a private consultation room keep surrogates informed of clinical status, prognosis, therapeutic plans, and changes in patient condition."),
        ]
    },
    10: {
        "title": "Safe Obstetric Care",
        "subs": [
            ("a", "Obstetric services are organised and provided safely.",
             "Documented policies, standard operating procedures (SOPs), and clinical pathways based on standard treatment guidelines govern the organization and delivery of safe obstetric care, covering ante-natal (ANC), peri-natal, and post-natal care. Patient assessments must systematically incorporate maternal nutrition, immunization status, and education. The organization's written guidance must explicitly define what constitutes a high-risk obstetric case and state whether the hospital undertakes its management or arranges timely referral. Clinical and nursing staff must receive regular training on identifying and managing obstetric emergencies (such as postpartum hemorrhage, eclampsia, and fetal distress), and infrastructure for newborn care must align with neonatal and pediatric safety standards."),
            ("b", "The organisation identifies and provides care to high-risk obstetric cases, and where needed, refers them to another appropriate centre.",
             "The hospital must establish clinical criteria and screening tools during initial antenatal check-ups to classify pregnancies as high-risk. Facilities with higher-level infrastructure (ICU/NICU) provide specialized care, while facilities lacking such resources enforce a documented stabilization and timely referral protocol."),
            ("c", "Persons caring for high-risk obstetric cases are competent.",
             "Only qualified obstetricians and credentialed nursing staff with specialized intrapartum and emergency obstetric training manage high-risk pregnancies and deliveries, with HR maintaining updated competency files."),
            ("d", "Ante-natal services are provided.",
             "Comprehensive outpatient antenatal care is systematically organized, maintaining serial records of maternal weight, blood pressure, lab investigations, ultrasound scans, and patient education on pregnancy danger signs."),
            ("e", "Organisation encourages and welcomes the presence of a birth companion during labour.",
             "The hospital promotes maternal emotional support by facilitating a designated birth companion of the mother's choice throughout active labor and childbirth in accordance with national guidelines."),
            ("f", "Organisation treats pregnant woman and her companion cordially and respectfully, ensures privacy and confidentiality for pregnant woman during her stay.",
             "All clinical interactions and labor room environments ensure patient dignity, respectful maternity care, visual and auditory privacy, and strict medical confidentiality."),
            ("g", "The treating doctor explains danger signs and important care activities to pregnant woman and her companion.",
             "Clinicians provide structured counseling to the pregnant woman and her companion regarding obstetric danger signs (bleeding, severe headache, reduced fetal movements) and self-care practices."),
            ("h", "Obstetric patient's assessment also includes maternal nutrition.",
             "Nutritional assessment including maternal BMI tracking, dietary evaluation, and micronutrient supplementation (iron, folic acid, calcium) is integrated into routine care."),
            ("i", "Appropriate peri-natal and post-natal monitoring is performed.",
             "Intrapartum progress is tracked using the Partograph, and post-natal monitoring systematically assesses maternal vital signs, lochia, uterine involution, and newborn wellness."),
            ("j", "The organisation caring for high-risk obstetric cases has the facilities to take care of neonates of such cases.",
             "Hospitals managing high-risk deliveries must maintain dedicated newborn resuscitation and neonatal intensive care unit (NICU) infrastructure with trained neonatologists."),
            ("k", "Organization shall adhere to legal and defined Assisted Reproductive Technology (ART) practices.",
             "All assisted reproductive technology services strictly adhere to statutory requirements under the ART Act and Surrogacy Regulation Act, ensuring ethical practice and documented consent."),
        ]
    },
    11: {
        "title": "Safe Paediatric Services",
        "subs": [
            ("a", "Paediatric services are organised and provided safely.",
             "The hospital must establish structured and safe workflows explicitly tailored for children, supported by dedicated infrastructure matching the scope of pediatric care provided (including safe cots, child-friendly environment, and prevention of falls and injuries). Clinical protocols ensure pediatric care is administered exclusively by personnel possessing age-specific competency and pediatric training."),
            ("b", "Neonatal care is in consonance with national and international guidelines.",
             "Neonatal intensive care and nursery units adhere to evidence-based neonatal protocols, thermo-regulation, aseptic handling, and standardized feeding guidelines."),
            ("c", "Those who care for children have age-specific competency.",
             "Pediatricians, pediatric nurses, and allied professionals undergo credentialing to verify competency in pediatric medication dosing, resuscitation, and developmental care."),
            ("d", "Provisions are made for special care of children.",
             "Infrastructure incorporates child-safe electrical outlets, secure windows, pediatric-sized equipment, play therapy areas, and parent accommodation provisions."),
            ("e", "Paediatric assessment includes growth, developmental, immunisation, and nutritional assessment.",
             "Clinical evaluation of pediatric patients systematically assesses growth percentiles, developmental milestones, national immunization schedule adherence, and nutritional status."),
            ("f", "The organisation has measures in place to prevent child and neonate abduction and abuse.",
             "Robust security mechanisms—including infant ID tags, access-controlled nursery entry, CCTV surveillance, and Code Pink emergency protocols—protect neonates and children from abduction and abuse."),
            ("g", "The child's family members are educated about nutrition, immunisation, and safe parenting.",
             "Family education covers exclusive breastfeeding, age-appropriate complementary feeding, vaccination schedules, oral rehydration, and injury prevention."),
            ("h", "Defined clinical scope and adolescent-friendly healthcare provisions are maintained.",
             "Services address adolescent healthcare needs with sensitivity, ensuring confidentiality, psychological support, and transition planning to adult care."),
        ]
    },
    12: {
        "title": "Procedural Sedation",
        "subs": [
            ("a", "Documented procedures guide the administration of procedural and moderate sedation.",
             "Procedural sedation practices cannot vary arbitrarily across departments; they must adhere to a uniform, hospital-approved Standard Operating Procedure (SOP) across all locations (including emergency, endoscopy suites, radiology, and minor procedure rooms). Protocols mandate pre-sedation risk assessment, written informed consent, patient monitoring by an independent clinician distinct from the proceduralist, and documented discharge criteria."),
            ("b", "Informed consent for the administration of moderate sedation is obtained.",
             "Patients or surrogates are informed of sedation risks, benefits, and alternative techniques, documented through signed informed consent prior to administration."),
            ("c", "Competent and trained persons perform procedural sedation.",
             "Only clinicians privileged and credentialed in sedation administration, airway rescue, and reversal pharmacology are permitted to administer procedural sedation."),
            ("d", "The person administering and monitoring sedation is separate and distinct from the person performing the procedure.",
             "A dedicated healthcare professional, separate from the clinician performing the diagnostic or therapeutic procedure, is assigned solely to monitor the patient's physiological status."),
            ("e", "Intra-procedure monitoring includes heart rate, cardiac rhythm, respiratory rate, blood pressure, oxygen saturation, and level of sedation.",
             "Continuous physiological monitoring of vitals, pulse oximetry, respiratory dynamics, and sedation depth is documented at regular intervals during the procedure."),
            ("f", "Patients are monitored post-sedation and recovery status is documented.",
             "Patients remain in a designated recovery area with continuous observation until protective reflexes, vital signs, and mental baseline fully return."),
            ("g", "Criteria are utilized and documented to determine appropriateness of discharge from the recovery area.",
             "Standardized objective discharge scoring systems (such as the Aldrete Score) are documented to authorize safe transfer or discharge from recovery."),
            ("h", "Appropriate equipment and trained manpower are readily available to manage patients who drift into deeper sedation.",
             "Emergency airway equipment, reversal agents (flumazenil, naloxone), suction, and resuscitation carts must be immediately accessible to rescue patients drifting into unintended deep sedation."),
        ]
    },
    13: {
        "title": "Anaesthesia Services",
        "subs": [
            ("a", "Documented policies and procedures guide the administration of anaesthesia.",
             "Anaesthesia delivery must follow standardized institutional policies and safety checklists (including pre-induction time-outs). Documented policies clearly define indications, authorized techniques, emergency readiness, and safety rules uniformly across all operating theaters. Anesthesia must be administered exclusively by qualified, privileged anesthesiologists."),
            ("b", "All patients scheduled for anaesthesia undergo a pre-anaesthesia assessment by a qualified anaesthesiologist.",
             "A comprehensive pre-anesthesia assessment evaluates patient medical history, airway classification, cardiac risk, and current medications to assign an ASA physical status score."),
            ("c", "The pre-anaesthesia assessment results in the formulation of a documented anaesthesia plan.",
             "A personalized anesthesia care plan outlines the proposed technique (general, regional, or monitored anesthesia care), premedication, airway strategy, and post-operative analgesia."),
            ("d", "An immediate pre-induction assessment and re-evaluation is performed prior to administering anaesthesia.",
             "Immediately before induction, the anesthesiologist verifies patient stability, fasting status, informed consent, and baseline physiological parameters."),
            ("e", "Informed consent for the administration of anaesthesia is obtained.",
             "Specific informed consent for anesthesia, detailing potential complications and anesthetic alternatives, is obtained by an anesthesiologist."),
            ("f", "Intra-anaesthesia monitoring includes regular recording of vital physiological parameters.",
             "Standard intraoperative monitoring encompasses ECG, non-invasive or invasive blood pressure, oxygen saturation, end-tidal CO2, and temperature at timed intervals."),
        ]
    },
    14: {
        "title": "Surgical Services",
        "subs": [
            ("a", "Surgical services are provided in a consistent and safe manner.",
             "The organization provides surgical services guided by written policies and standard procedures based on evidence-based clinical practices. The scope of surgical services (elective and emergency) is clearly defined based on clinical facilities, operating theater infrastructure, and surgeon privileges. Surgical care encompasses pre-operative, intra-operative, and post-operative phases. Appropriate staffing, equipment, sterility controls, and emergency backup systems are maintained across all surgical theaters."),
            ("b", "Surgical patients have a pre-operative assessment, a documented pre-operative diagnosis, and pre-operative instructions are provided before surgery.",
             "A complete surgical workup documents the pre-operative diagnosis, planned surgical procedure, pre-anesthetic clearance, and pre-operative fasting and medication instructions."),
            ("c", "Informed consent is obtained by a surgeon before the procedure.",
             "The operating surgeon directly explains the nature of surgery, risks, benefits, and alternatives to obtain written informed consent before surgical intervention."),
            ("d", "Care is taken to prevent adverse events like wrong site, wrong patient, and wrong surgery.",
             "The organization strictly implements standardized peri-operative verification protocols in accordance with the WHO Surgical Safety Checklist. The protocol includes three distinct phases: Sign-In (before induction of anesthesia), Time-Out (immediately before skin incision), and Sign-Out (before patient leaves the operating room). Surgical site marking is done by the operating team before surgery in the presence of the conscious patient wherever applicable."),
            ("e", "An operative note is documented before transfer out of the recovery area.",
             "A comprehensive operative note detailing operative findings, surgical technique, specimens removed, blood loss, and sponge/instrument count completion is documented prior to recovery transfer."),
            ("f", "Post-operative care is guided by a documented plan.",
             "A written post-operative care plan specifies monitoring frequency, fluid therapy, pain management, wound care, medication orders, and discharge criteria."),
            ("g", "Patient, personnel, and material flow conform to infection control practices.",
             "Operating theater traffic flows ensure strict zoning (unrestricted, semi-restricted, and restricted areas) with unidirectional material and personnel movement to minimize contamination."),
            ("h", "Appropriate facilities, equipment, instruments, and supplies are available in the operating theatre.",
             "Operating suites are equipped with functional surgical tables, shadowless lights, diathermy machines, suction, sterile instrument sets, and emergency life support."),
            ("i", "The organisation shall implement a surgical quality assurance programme.",
             "Surgical quality metrics—including surgical site infection (SSI) rates, unplanned re-exploration, anesthesia complications, and mortality audits—are tracked continuously."),
            ("j", "The quality assurance programme includes surveillance of the operation theatre environment.",
             "Environmental surveillance of the operation theatre (OT) complex is conducted systematically as part of the hospital quality assurance and infection control program. This includes regular monitoring of OT positive pressure gradients, air changes per hour (ACPH), temperature, humidity, and HEPA filter integrity. Microbiological surveillance, routine surface swabs, and settle plate air sampling are performed according to documented institutional frequency."),
        ]
    },
    15: {
        "title": "Organ Transplant Programme",
        "subs": [
            ("a", "The organ transplant program shall be in consonance with legal requirements and shall be conducted ethically.",
             "The hospital must possess valid, up-to-date statutory registrations and licenses under applicable national and state transplantation laws (such as THAUT). Strict institutional mechanisms prevent commercial dealings, ensure independent authorization committee approvals, prevent coercion, and enforce complete documentation of donor and recipient counseling."),
            ("b", "Care of transplant patients is guided by clinical practice guidelines.",
             "Standardized clinical protocols govern candidate selection, donor evaluation, HLA tissue typing, immunosuppressive therapy, and post-transplant infection prophylaxis."),
            ("c", "The organization ensures education and counselling of the recipient and donor through qualified counsellors.",
             "Independent medical and psychological counselors provide structured counseling to donors and recipients regarding clinical risks, long-term outcomes, and legal voluntariness."),
            ("d", "The organization shall take measures to create awareness regarding organ donation.",
             "The hospital actively conducts public and hospital awareness initiatives promoting deceased organ donation in coordination with regional organ retrieval bodies."),
        ]
    },
    16: {
        "title": "Care of Vulnerable and High-Risk Patients",
        "subs": [
            ("a", "The organisation identifies and manages vulnerable patients.",
             "The organization defines and identifies categories of vulnerable patients, including pediatric patients, unaccompanied elderly patients, pregnant women, physically or mentally challenged individuals, and patients with altered sensorium. Documented policies ensure enhanced monitoring, physical safety, protection from abuse or exploitation, chaperone assistance during clinical examinations, and specialized nursing support throughout outpatient and inpatient care."),
            ("b", "The organisation identifies and manages patients who are at risk of falls.",
             "Validated fall risk assessment scales (e.g., Morse Fall Scale) identify at-risk patients upon admission, triggering fall prevention interventions like bed rails, call bells, and assisted ambulation."),
            ("c", "The organisation identifies and manages patients who are at risk of developing or worsening pressure ulcers.",
             "Pressure injury screening using validated tools (e.g., Braden Scale) initiates preventive measures, including regular patient repositioning, pressure-relieving mattresses, and nutritional support."),
            ("d", "The organisation identifies and manages patients who are at risk of developing deep vein thrombosis (DVT).",
             "Clinical risk assessment for venous thromboembolism guides the administration of mechanical prophylaxis (compression stockings) and pharmacological thromboprophylaxis."),
            ("e", "The organisation identifies and manages patients requiring restraints.",
             "Strict clinical guidelines govern physical or chemical restraint application, requiring authorized physician orders, time-limited use, continuous monitoring, and frequent clinical re-evaluation."),
        ]
    },
    17: {
        "title": "Pain Management",
        "subs": [
            ("a", "Documented policies and procedures guide the management of pain.",
             "Pain management is recognized as an integral part of patient care and treated as the fifth vital sign. Written guidelines govern pain screening, comprehensive pain assessment, pharmacological and non-pharmacological interventions, and periodic reassessment. Clinical staff are trained in pain assessment methodologies and safe opioid and analgesic administration following standard clinical protocols."),
            ("b", "Patients are screened for pain during initial and ongoing clinical assessments.",
             "All patients undergo routine pain screening at outpatient triage and inpatient admission using age-appropriate standardized scoring scales (e.g., Visual Analog Scale, NRS, or Wong-Baker Faces)."),
            ("c", "Patients in pain undergo detailed assessment and periodic reassessment using validated scales.",
             "Patients identified with pain undergo comprehensive evaluation (location, intensity, character, aggravating factors) and timed reassessment following analgesic interventions to evaluate treatment efficacy."),
        ]
    },
    18: {
        "title": "Rehabilitation Services",
        "subs": [
            ("a", "Scope of the rehabilitation services at a minimum is commensurate to the services provided by the organisation.",
             "The organization explicitly defines the scope of rehabilitation services (physiotherapy, occupational therapy, speech therapy) based on clinical specialties offered and patient requirements. Services are provided consistently according to clinical practice guidelines, with documented departmental procedures, qualified therapists, and appropriate therapeutic space and equipment."),
            ("b", "Rehabilitation services are provided in a consistent manner guided by clinical treatment guidelines.",
             "Evidence-based therapeutic protocols guide rehabilitation interventions across inpatient, outpatient, and critical care units."),
            ("c", "Care providers collaboratively plan rehabilitation services.",
             "Multidisciplinary rehabilitation plans are formulated in consultation with primary treating physicians, physical therapists, nurses, and patient families."),
            ("d", "There is adequate space, infrastructure, and equipment to provide safe rehabilitation.",
             "Rehabilitation departments maintain dedicated exercise therapy space, gait training areas, modality equipment, and emergency safety features."),
            ("e", "Care is guided by functional assessment and periodic re-assessments which are done and documented.",
             "The assessment and ongoing evaluation of a patient requiring rehabilitation (physical therapy, occupational therapy, or speech therapy) must utilize relevant, validated functional assessment scales appropriate to the patient's condition (such as FIM score, Barthel Index, or Glasgow Outcome Scale). Functional assessments and periodic re-assessments must be performed and documented by qualified individuals authorized within their clinical scope. Re-assessments must be carried out at defined intervals or milestone markers to track recovery, modify therapeutic goals, or justify continuation or cessation of interventions. Assessors verify completed baseline assessments and dated, signed periodic re-assessments in medical records."),
            ("f", "Rehabilitation care is provided adhering to infection control and safety practices.",
             "Therapy equipment and treatment surfaces undergo routine decontamination between patient sessions adhering to hospital infection control standards."),
            ("g", "Rehabilitation care pathways are developed, implemented, and reviewed periodically.",
             "Clinical care pathways for common rehabilitation conditions (e.g., stroke rehab, total joint arthroplasty, cardiac rehab) are audited and reviewed periodically for clinical efficacy."),
        ]
    },
    19: {
        "title": "Nutritional Therapy",
        "subs": [
            ("a", "Patients admitted to the organisation are screened for nutritional risk.",
             "All admitted patients undergo nutritional screening at the time of initial assessment to identify individuals who are malnourished or at risk of developing malnutrition. Standardized, validated screening criteria (such as MUST or NRS-2002) are utilized. Patients identified as nutritional risks are promptly referred to qualified dietitians for detailed nutritional assessment and therapeutic dietary planning."),
            ("b", "Nutritional assessment is done for patients found at risk during nutritional screening.",
             "Qualified clinical dietitians perform detailed dietary assessments, calculating caloric requirements, macronutrient distributions, and therapeutic restrictions."),
            ("c", "The therapeutic diet is planned and provided collaboratively.",
             "Dietary plans are established in coordination with treating physicians and dietitians, customized to medical diagnoses (e.g., diabetic diet, renal diet, cardiac diet, enteral nutrition)."),
            ("d", "Patients receive food according to the written order for the diet.",
             "Food preparation, kitchen hygiene, and meal tray delivery conform to strict dietary orders, ensuring correct therapeutic meal distribution."),
            ("e", "When family provides food, they are educated about the patient's diet limitations.",
             "Clinical staff educate family members regarding strict therapeutic dietary limitations and food safety hygiene when home-cooked food is permitted."),
        ]
    },
    20: {
        "title": "End-of-Life Care",
        "subs": [
            ("a", "Documented policies and procedures guide the provision of end-of-life care.",
             "Documented institutional policies guide palliative and end-of-life care for terminally ill patients in compliance with applicable statutory and ethical guidelines. Care focuses on symptom control, compassionate pain relief, respecting patient and family preferences, honoring spiritual and cultural practices, emotional counseling, and transparent communication regarding treatment limits and DNR orders where legally recognized."),
            ("b", "Pain management and palliative care measures provide compassionate symptom relief.",
             "Interdisciplinary teams deliver aggressive symptom management addressing pain, dyspnea, nausea, and delirium to ensure patient dignity and comfort in terminal stages."),
            ("c", "End-of-life care addresses and respects religious and socio-cultural needs of the patient and family.",
             "Hospital staff accommodate spiritual counselors, religious rites, and cultural rituals requested by the patient and family during the terminal phase."),
            ("d", "Transparent communication with patient and family guides treatment limitations and care planning.",
             "Sensitively documented goals-of-care conversations address palliative treatment pathways, withholding of futile aggressive interventions, and family bereavement support."),
            ("e", "Protocols ensure respectful handling of deceased patients and facilitate post-death procedures.",
             "Standard operating procedures govern dignified post-mortem care, mortuary transfer, safe body release, and compassionate assistance with statutory death certification."),
        ]
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


def audit_existing_flow(flow_data: dict, db_session) -> dict:
    """Performs a comprehensive audit of COP.1 to COP.20 before modification."""
    nodes = flow_data.get("nodes", [])
    edges = flow_data.get("edges", [])
    node_map = {n["id"]: n for n in nodes}

    audit_results = {}
    for i in range(1, 21):
        std_id = f"cop_{i}"
        std_node = node_map.get(std_id)
        if not std_node:
            audit_results[i] = {"exists": False}
            continue

        btns = std_node.get("data", {}).get("buttons", [])
        sub_nodes = [n for n in nodes if n["id"].startswith(f"cop_{i}_")]
        expected_subs = COP_DATA[i]["subs"]

        # Check answers in DB
        db_answers = db_session.query(NodeAnswer).filter(
            NodeAnswer.flow_id == TARGET_FLOW_ID,
            NodeAnswer.node_id.like(f"cop_{i}_%")
        ).all()
        # Filter accurately (avoid matching cop_10 when querying cop_1)
        valid_db_ans = [a for a in db_answers if a.node_id.startswith(f"cop_{i}_")]

        audit_results[i] = {
            "exists": True,
            "type": std_node.get("type"),
            "existing_buttons_count": len(btns),
            "existing_sub_nodes_count": len(sub_nodes),
            "expected_subs_count": len(expected_subs),
            "db_answers_count": len(valid_db_ans),
            "missing_sub_nodes": [f"cop_{i}_{s[0]}" for s in expected_subs if f"cop_{i}_{s[0]}" not in node_map],
        }

    return audit_results


def build_updated_graph(original_flow_data: dict) -> tuple:
    """
    Builds the updated flow graph by adding missing sub-standard nodes and buttons for COP.1-COP.9,
    and connecting all edges. Preserves existing COP.10-COP.20 nodes and edges.
    """
    flow_data = copy.deepcopy(original_flow_data)
    nodes = flow_data.get("nodes", [])
    edges = flow_data.get("edges", [])

    # Index nodes and edges
    node_map = {n["id"]: n for n in nodes}
    edge_map = {e["id"]: e for e in edges}

    # Verify standard_cop chapter node
    cop_chapter = node_map.get(CHAPTER_NODE_ID)
    if not cop_chapter:
        raise ValueError(f"Chapter node '{CHAPTER_NODE_ID}' not found in flow.")

    new_nodes = []
    new_edges = []
    edges_to_remove = set()

    # Update COP.1 through COP.9: convert to menu nodes, add sub-standard buttons, create sub-nodes and edges
    std_base_y = 1575
    for i in range(1, 10):
        std_id = f"cop_{i}"
        std_info = COP_DATA[i]
        subs = std_info["subs"]
        pos_y = std_base_y + (i - 1) * 160

        # Sub-standard buttons for this standard
        std_buttons = []
        for s_idx, (letter, desc, _) in enumerate(subs):
            sub_node_id = f"cop_{i}_{letter}"
            btn_id = f"cop_{i}__{sub_node_id}__{s_idx}"
            std_buttons.append({
                "id": btn_id,
                "next": sub_node_id,
                "label": f"COP.{i}.{letter}"
            })

        # Back to COP Standards button
        btn_back_id = f"cop_{i}__back_standard_cop__{len(subs)}"
        std_buttons.append({
            "id": btn_back_id,
            "next": CHAPTER_NODE_ID,
            "label": "Back to COP Standards"
        })

        # Update cop_i node
        std_node = node_map.get(std_id)
        if std_node:
            std_node["type"] = "menu"
            std_node["data"]["buttons"] = std_buttons
            std_node["data"]["message"] = f"COP.{i} — {std_info['title']}"
            std_node["data"]["nodeType"] = "menu"
            std_node["data"]["layoutWidth"] = 290
            std_node["data"]["layoutHeight"] = 280
            std_node["data"]["mapping_status"] = "VERIFIED"
            std_node["mapping_status"] = "VERIFIED"
            std_node["position"] = {"x": 5715, "y": pos_y}
        else:
            std_node = {
                "id": std_id,
                "type": "menu",
                "data": {
                    "id": std_id,
                    "label": f"STANDARD: COP.{i}",
                    "message": f"COP.{i} — {std_info['title']}",
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
                "message": f"COP.{i} — {std_info['title']}",
                "position": {"x": 5715, "y": pos_y},
                "mapping_status": "VERIFIED"
            }
            new_nodes.append(std_node)

        # Remove old back edge to standard_cop if it had old handle
        old_back_edge_id = f"edge-{std_id}-standard_cop-{std_id}__back_standard_cop__0"
        if old_back_edge_id in edge_map:
            edges_to_remove.add(old_back_edge_id)

        # Add updated back edge to standard_cop
        new_edges.append({
            "id": f"edge-{std_id}-standard_cop-{btn_back_id}",
            "label": "Back to COP Standards",
            "source": std_id,
            "target": CHAPTER_NODE_ID,
            "sourceHandle": btn_back_id
        })

        # Create sub-standard answer nodes and connecting edges
        for s_idx, (letter, desc, _) in enumerate(subs):
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
                        {"id": sub_btn_back_std, "next": std_id, "label": f"Back to COP.{i}"},
                        {"id": sub_btn_back_cop, "next": CHAPTER_NODE_ID, "label": "Back to COP Standards"}
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
                "position": {"x": 6220, "y": pos_y + s_idx * 140},
                "mapping_status": "VERIFIED"
            }
            new_nodes.append(sub_node)

            # Forward edge from cop_{i} to cop_{i}_{letter}
            fwd_btn_id = f"cop_{i}__{sub_node_id}__{s_idx}"
            new_edges.append({
                "id": f"edge-{std_id}-{sub_node_id}-{fwd_btn_id}",
                "label": f"COP.{i}.{letter}",
                "source": std_id,
                "target": sub_node_id,
                "sourceHandle": fwd_btn_id
            })

            # Back edge to cop_{i}
            new_edges.append({
                "id": f"edge-{sub_node_id}-{std_id}-{sub_btn_back_std}",
                "label": f"Back to COP.{i}",
                "source": sub_node_id,
                "target": std_id,
                "sourceHandle": sub_btn_back_std
            })

            # Back edge to standard_cop
            new_edges.append({
                "id": f"edge-{sub_node_id}-standard_cop-{sub_btn_back_cop}",
                "label": "Back to COP Standards",
                "source": sub_node_id,
                "target": CHAPTER_NODE_ID,
                "sourceHandle": sub_btn_back_cop
            })

    # Filter out removed edges and combine
    remaining_edges = [e for e in edges if e["id"] not in edges_to_remove]
    flow_data["nodes"] = nodes + new_nodes
    flow_data["edges"] = remaining_edges + new_edges

    return flow_data, new_nodes, new_edges, len(edges_to_remove)


async def main():
    print("=" * 80)
    print("AUDITING AND COMPLETING COP.1 - COP.20 SUB-STANDARDS & ANSWERS")
    print(f"Target Flow ID:    {TARGET_FLOW_ID}")
    print(f"Target Chatbot ID: {TARGET_CHATBOT_ID}")
    print("=" * 80)

    db = SessionLocal()
    target_flow = db.get(Flow, TARGET_FLOW_ID)
    if not target_flow:
        print(f"ERROR: Flow {TARGET_FLOW_ID} not found!")
        db.close()
        sys.exit(1)

    # 1. Audit Existing Flow
    print("\n[Phase 1] Auditing Existing Flow State...")
    audit = audit_existing_flow(target_flow.flow_data, db)
    for std_num, res in audit.items():
        print(f"  COP.{std_num:2d}: {res['existing_buttons_count']} buttons, "
              f"{res['existing_sub_nodes_count']} sub-nodes (Expected: {res['expected_subs_count']}), "
              f"{res['db_answers_count']} DB answers")

    # 2. Safety Backup
    print("\n[Phase 2] Creating Pre-Modification Safety Backup...")
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file_path = os.path.join(
        backend_dir, "data", f"backup_flow_{TARGET_FLOW_ID}_before_all_cop_complete_{timestamp_str}.json"
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

    # 3. Build Graph
    print("\n[Phase 3] Constructing Missing Graph Elements...")
    updated_flow_data, new_nodes, new_edges, removed_edges_count = build_updated_graph(target_flow.flow_data)
    print(f"  Newly Created Sub-Standard Nodes: {len(new_nodes)} (COP.1 to COP.9)")
    print(f"  Newly Created Edges: {len(new_edges)}")
    print(f"  Old Placeholder Edges Replaced: {removed_edges_count}")
    print(f"  Total Flow Nodes: {len(updated_flow_data['nodes'])}")
    print(f"  Total Flow Edges: {len(updated_flow_data['edges'])}")

    # 4. Persist Graph via PUT /flows/{flow_id}
    print(f"\n[Phase 4] Persisting Updated Flow via PUT /flows/{TARGET_FLOW_ID}...")
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
    print(f"  ✓ Flow graph saved successfully with {len(put_resp['flow_data']['nodes'])} nodes, {len(put_resp['flow_data']['edges'])} edges")

    # 5. Store Official Answers in node_answers and answer_blocks
    print("\n[Phase 5] Storing Official Descriptions & Interpretations in PostgreSQL...")
    stored_count = 0
    updated_count = 0
    preserved_count = 0

    for i in range(1, 21):
        for letter, desc, interp in COP_DATA[i]["subs"]:
            sub_node_id = f"cop_{i}_{letter}"
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

            # Check if answer already exists
            get_status, _ = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_node_id}/answer?language=en")
            if get_status == 200:
                # Update existing
                ans_status, ans_resp = await invoke_asgi("PUT", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_node_id}/answer", payload)
                updated_count += 1
            else:
                # Create new
                ans_status, ans_resp = await invoke_asgi("POST", f"/flows/{TARGET_FLOW_ID}/nodes/{sub_node_id}/answer", payload)
                stored_count += 1

            if ans_status not in (200, 201):
                print(f"ERROR saving answer for {sub_node_id}: {ans_resp}")
                sys.exit(1)

    print(f"  ✓ Total Sub-Standard Answers Processed: {stored_count + updated_count} ({stored_count} new, {updated_count} refreshed)")

    # 6. Comprehensive Verification
    print("\n" + "=" * 80)
    print("RUNNING FINAL SYSTEM & GRAPH INTEGRITY AUDIT")
    print("=" * 80)

    # 6.1 GET Flow Verification
    get_status, flow_res = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}")
    assert get_status == 200
    ret_nodes = flow_res["flow_data"]["nodes"]
    ret_edges = flow_res["flow_data"]["edges"]
    node_map = {n["id"]: n for n in ret_nodes}
    print(f"  ✓ GET /flows/{TARGET_FLOW_ID}: Confirmed {len(ret_nodes)} nodes, {len(ret_edges)} edges.")

    # 6.2 Duplicate checks
    from collections import Counter
    node_counts = Counter(n["id"] for n in ret_nodes)
    dup_nodes = [k for k, v in node_counts.items() if v > 1]
    assert len(dup_nodes) == 0, f"Duplicate nodes: {dup_nodes}"
    print("  ✓ Zero duplicate node IDs.")

    edge_counts = Counter(e["id"] for e in ret_edges)
    # Check duplicate non-default edges
    dup_edges = [k for k, v in edge_counts.items() if v > 1 and "default" not in k]
    assert len(dup_edges) == 0, f"Duplicate edges: {dup_edges}"
    print("  ✓ Zero duplicate COP edge IDs.")

    # 6.3 Edge referential integrity
    missing_sources = [e for e in ret_edges if e.get("source") not in node_map]
    missing_targets = [e for e in ret_edges if e.get("target") not in node_map]
    assert len(missing_sources) == 0, f"Missing sources: {missing_sources}"
    assert len(missing_targets) == 0, f"Missing targets: {missing_targets}"
    print("  ✓ 100% of edge sources and targets exist in graph.")

    # 6.4 Handle matching check for all COP nodes
    cop_edge_mismatches = []
    for e in ret_edges:
        src_id = e.get("source", "")
        handle = e.get("sourceHandle")
        if src_id.startswith("cop_") or src_id == CHAPTER_NODE_ID:
            src_node = node_map.get(src_id)
            if src_node:
                btns = src_node.get("data", {}).get("buttons", [])
                btn_ids = {b["id"] for b in btns}
                if handle and handle not in btn_ids:
                    cop_edge_mismatches.append((e["id"], src_id, handle))
    assert len(cop_edge_mismatches) == 0, f"Handle mismatches: {cop_edge_mismatches}"
    print("  ✓ 100% of COP edge handles match button IDs.")

    # 6.5 Sample Answer Retrieval across all chapters
    test_nodes = ["cop_1_a", "cop_2_c", "cop_3_a", "cop_4_a", "cop_5_a", "cop_6_a", "cop_7_d",
                  "cop_8_b", "cop_9_a", "cop_10_a", "cop_14_d", "cop_18_e", "cop_20_a"]
    for tn in test_nodes:
        ans_status, ans_data = await invoke_asgi("GET", f"/flows/{TARGET_FLOW_ID}/nodes/{tn}/answer?language=en")
        assert ans_status == 200
        assert len(ans_data["blocks"]) >= 1
        assert "**Description:**" in ans_data["blocks"][0]["content"]
        assert "**Interpretation:**" in ans_data["blocks"][0]["content"]
    print(f"  ✓ Successfully verified {len(test_nodes)} sample answer GET API responses across COP.1 to COP.20.")

    # 6.6 Verify hospital and AAC answers preserved
    db = SessionLocal()
    for h in ["hospitals_eligibility", "hospitals_application", "hospitals_assessment", "hospitals_documents", "hospitals_fee_structure"]:
        ha = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID, NodeAnswer.node_id == h).first()
        assert ha is not None, f"Missing hospital answer {h}"
    for a in ["aac_1_a", "aac_1_b", "aac_1_c", "aac_1_d"]:
        aa = db.query(NodeAnswer).filter(NodeAnswer.flow_id == TARGET_FLOW_ID, NodeAnswer.node_id == a).first()
        assert aa is not None, f"Missing AAC answer {a}"
    print("  ✓ All 5 official hospital answers and 4 AAC answers preserved.")
    db.close()

    print("\n" + "=" * 80)
    print("ALL COP.1 - COP.20 STANDARDS, BUTTONS, EDGES & ANSWERS COMPLETED (100%)")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

