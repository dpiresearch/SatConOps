"""
Project Planner Module for SatConOps

Generates a comprehensive project plan from satellite mission timeline data
and team configuration. Produces work breakdown structures, milestones,
RACI matrices, staffing profiles, and budget estimates.
"""

from datetime import datetime, timedelta
from copy import deepcopy
import math


# ---------------------------------------------------------------------------
# Constants & Reference Data
# ---------------------------------------------------------------------------

STANDARD_ROLES = [
    "Project Manager",
    "Systems Engineer",
    "Mechanical Engineer",
    "Electrical/Power Engineer",
    "RF/Comms Engineer",
    "Software Engineer",
    "Payload Specialist",
    "Regulatory Specialist",
    "Quality Assurance",
    "Integration & Test Lead",
]

GOVERNMENT_EXTRA_ROLES = [
    "Program Manager",
    "Chief Engineer",
    "Mission Assurance",
    "Safety Officer",
    "Contracts",
]

COMPLEXITY_SCALE = {
    "cubesat": 0.4,
    "smallsat": 0.6,
    "medium": 0.8,
    "large": 1.0,
    "geo": 1.0,
}

BUDGET_MULTIPLIERS = {
    "shoestring": 0.5,
    "moderate": 1.0,
    "well_funded": 1.8,
}

EXPERIENCE_STAFFING = {
    "university": 0.4,
    "startup": 0.7,
    "experienced_industry": 1.0,
    "government_prime": 1.4,
}

# Phase name normalization mapping
PHASE_ALIASES = {
    "concept": "Concept",
    "concept development": "Concept",
    "concept development & feasibility": "Concept",
    "preliminary design": "PDR",
    "preliminary design & pdr": "PDR",
    "pdr": "PDR",
    "detailed design": "CDR",
    "detailed design & cdr": "CDR",
    "cdr": "CDR",
    "critical design": "CDR",
    "procurement": "Procurement",
    "component procurement": "Procurement",
    "fabrication": "Fabrication",
    "fabrication & assembly": "Fabrication",
    "manufacturing": "Fabrication",
    "integration": "Integration",
    "integration & functional testing": "Integration",
    "ait": "Integration",
    "assembly": "Integration",
    "environmental testing": "Environmental Testing",
    "environmental testing (tvac, vibe, emi)": "Environmental Testing",
    "environmental & qualification testing": "Environmental Testing",
    "environmental test": "Environmental Testing",
    "env test": "Environmental Testing",
    "testing": "Environmental Testing",
    "regulatory": "Regulatory",
    "fcc": "Regulatory",
    "fcc / regulatory filing & approval": "Regulatory",
    "itar / export control review": "Regulatory",
    "spectrum": "Regulatory",
    "iaru": "IARU/ITU",
    "itu": "IARU/ITU",
    "iaru/itu": "IARU/ITU",
    "iaru frequency coordination": "IARU/ITU",
    "iaru / itu frequency coordination": "IARU/ITU",
    "itu frequency coordination & filing": "IARU/ITU",
    "orbital slot coordination (itu br)": "IARU/ITU",
    "frequency coordination": "IARU/ITU",
    "launch procurement": "Launch Procurement",
    "launch selection": "Launch Procurement",
    "launch contract": "Launch Procurement",
    "launch vehicle procurement & contracting": "Launch Procurement",
    "range safety": "Range Safety",
    "range safety review & approval": "Range Safety",
    "pre-ship": "Pre-Ship",
    "pre-ship review & shipping": "Pre-Ship",
    "shipping": "Pre-Ship",
    "ship": "Pre-Ship",
    "launch campaign": "Launch Campaign",
    "launch campaign & integration": "Launch Campaign",
    "launch": "Launch Campaign",
    "launch ops": "Launch Campaign",
    "operations": "Operations",
    "commissioning": "Operations",
    "on-orbit": "Operations",
}


# ---------------------------------------------------------------------------
# WBS Templates by Phase
# ---------------------------------------------------------------------------

WBS_TEMPLATES = {
    "Concept": [
        {
            "name": "Mission Requirements Definition",
            "duration_weeks": 4,
            "deliverable": "Mission Requirements Document (MRD)",
            "required_roles": ["Systems Engineer", "Project Manager"],
            "is_milestone": False,
            "entry_criteria": "Project authorization received",
            "exit_criteria": "MRD approved by stakeholders",
        },
        {
            "name": "Trade Study: Orbit Selection",
            "duration_weeks": 3,
            "deliverable": "Orbit Trade Study Report",
            "required_roles": ["Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Mission objectives defined",
            "exit_criteria": "Orbit parameters baselined",
        },
        {
            "name": "Trade Study: Subsystem Architecture",
            "duration_weeks": 4,
            "deliverable": "Architecture Trade Study Report",
            "required_roles": ["Systems Engineer", "Electrical/Power Engineer", "RF/Comms Engineer"],
            "is_milestone": False,
            "entry_criteria": "Orbit selected",
            "exit_criteria": "Preferred architecture identified",
        },
        {
            "name": "Preliminary Cost Estimate",
            "duration_weeks": 2,
            "deliverable": "ROM Cost Estimate",
            "required_roles": ["Project Manager", "Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Architecture defined",
            "exit_criteria": "Cost estimate approved by sponsor",
        },
        {
            "name": "ConOps Document Development",
            "duration_weeks": 3,
            "deliverable": "Concept of Operations Document",
            "required_roles": ["Systems Engineer", "Payload Specialist"],
            "is_milestone": False,
            "entry_criteria": "Mission requirements defined",
            "exit_criteria": "ConOps reviewed and approved",
        },
        {
            "name": "Mission Concept Review (MCR) Package",
            "duration_weeks": 2,
            "deliverable": "MCR Presentation and Supporting Data",
            "required_roles": ["Project Manager", "Systems Engineer"],
            "is_milestone": True,
            "entry_criteria": "All concept phase deliverables complete",
            "exit_criteria": "MCR board approves proceeding to design",
        },
    ],
    "PDR": [
        {
            "name": "System-Level Design",
            "duration_weeks": 4,
            "deliverable": "System Design Document",
            "required_roles": ["Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "MCR passed",
            "exit_criteria": "System design document reviewed",
        },
        {
            "name": "Subsystem Preliminary Designs",
            "duration_weeks": 6,
            "deliverable": "Subsystem Design Packages",
            "required_roles": ["Mechanical Engineer", "Electrical/Power Engineer", "RF/Comms Engineer", "Software Engineer"],
            "is_milestone": False,
            "entry_criteria": "System design baselined",
            "exit_criteria": "All subsystem prelim designs reviewed",
        },
        {
            "name": "Interface Control Documents",
            "duration_weeks": 4,
            "deliverable": "ICD Set (Mechanical, Electrical, Data)",
            "required_roles": ["Systems Engineer", "Mechanical Engineer", "Electrical/Power Engineer"],
            "is_milestone": False,
            "entry_criteria": "Subsystem designs started",
            "exit_criteria": "ICDs reviewed and signed by subsystem leads",
        },
        {
            "name": "Power Budget Analysis",
            "duration_weeks": 2,
            "deliverable": "Power Budget Report",
            "required_roles": ["Electrical/Power Engineer", "Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Subsystem power requirements identified",
            "exit_criteria": "Positive power margin demonstrated",
        },
        {
            "name": "Link Budget Analysis",
            "duration_weeks": 2,
            "deliverable": "Link Budget Report",
            "required_roles": ["RF/Comms Engineer", "Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Orbit and ground station parameters defined",
            "exit_criteria": "Positive link margin demonstrated",
        },
        {
            "name": "Risk Register Development",
            "duration_weeks": 2,
            "deliverable": "Project Risk Register",
            "required_roles": ["Project Manager", "Systems Engineer", "Quality Assurance"],
            "is_milestone": False,
            "entry_criteria": "Preliminary designs available",
            "exit_criteria": "All risks identified, scored, and mitigated",
        },
        {
            "name": "PDR Presentation & Review",
            "duration_weeks": 2,
            "deliverable": "PDR Package and Review Minutes",
            "required_roles": ["Project Manager", "Systems Engineer"],
            "is_milestone": True,
            "entry_criteria": "All PDR-phase deliverables complete",
            "exit_criteria": "PDR board approves proceeding to detailed design",
        },
    ],
    "CDR": [
        {
            "name": "Detailed Mechanical Design",
            "duration_weeks": 6,
            "deliverable": "Mechanical Drawing Package (3D CAD, 2D drawings)",
            "required_roles": ["Mechanical Engineer"],
            "is_milestone": False,
            "entry_criteria": "PDR passed, prelim design approved",
            "exit_criteria": "Drawings released for manufacturing review",
        },
        {
            "name": "Detailed Electrical Design",
            "duration_weeks": 6,
            "deliverable": "Schematics, PCB Layouts, Wiring Diagrams",
            "required_roles": ["Electrical/Power Engineer"],
            "is_milestone": False,
            "entry_criteria": "PDR passed, prelim design approved",
            "exit_criteria": "EE designs peer-reviewed and released",
        },
        {
            "name": "RF/Comms Detailed Design",
            "duration_weeks": 5,
            "deliverable": "RF Design Package (antenna, transceiver specs)",
            "required_roles": ["RF/Comms Engineer"],
            "is_milestone": False,
            "entry_criteria": "Link budget approved",
            "exit_criteria": "RF design peer-reviewed and released",
        },
        {
            "name": "Flight Software Architecture & Design",
            "duration_weeks": 6,
            "deliverable": "FSW Design Document and Module Specs",
            "required_roles": ["Software Engineer", "Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Command & data handling requirements defined",
            "exit_criteria": "FSW design reviewed, coding can begin",
        },
        {
            "name": "Structural/Thermal Analysis",
            "duration_weeks": 4,
            "deliverable": "FEA Report, Thermal Model Results",
            "required_roles": ["Mechanical Engineer", "Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Detailed mechanical design available",
            "exit_criteria": "Positive structural and thermal margins",
        },
        {
            "name": "Test Plan Development",
            "duration_weeks": 3,
            "deliverable": "Integration & Test Plan",
            "required_roles": ["Integration & Test Lead", "Quality Assurance", "Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Detailed designs nearing completion",
            "exit_criteria": "Test plan reviewed and approved",
        },
        {
            "name": "CDR Presentation & Review",
            "duration_weeks": 2,
            "deliverable": "CDR Package and Review Minutes",
            "required_roles": ["Project Manager", "Systems Engineer"],
            "is_milestone": True,
            "entry_criteria": "All CDR-phase deliverables complete",
            "exit_criteria": "CDR board approves proceeding to build",
        },
    ],
    "Procurement": [
        {
            "name": "Vendor Identification & Selection",
            "duration_weeks": 3,
            "deliverable": "Vendor Selection Matrix",
            "required_roles": ["Project Manager", "Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Component specifications finalized",
            "exit_criteria": "Vendors selected for all major items",
        },
        {
            "name": "Long-Lead Item Orders",
            "duration_weeks": 2,
            "deliverable": "Purchase Orders for Long-Lead Items",
            "required_roles": ["Project Manager"],
            "is_milestone": False,
            "entry_criteria": "Vendors selected, budget approved",
            "exit_criteria": "All long-lead POs placed and confirmed",
        },
        {
            "name": "Standard Component Procurement",
            "duration_weeks": 4,
            "deliverable": "Purchase Orders for Standard Components",
            "required_roles": ["Project Manager", "Electrical/Power Engineer"],
            "is_milestone": False,
            "entry_criteria": "Detailed BOM finalized",
            "exit_criteria": "All standard component POs placed",
        },
        {
            "name": "Receiving Inspection",
            "duration_weeks": 3,
            "deliverable": "Receiving Inspection Reports",
            "required_roles": ["Quality Assurance", "Integration & Test Lead"],
            "is_milestone": False,
            "entry_criteria": "Components arriving",
            "exit_criteria": "All components inspected and accepted",
        },
        {
            "name": "Long-Lead Delivery Tracking",
            "duration_weeks": 8,
            "deliverable": "Procurement Status Tracker",
            "required_roles": ["Project Manager"],
            "is_milestone": False,
            "entry_criteria": "Long-lead POs placed",
            "exit_criteria": "All long-lead items received and inspected",
        },
    ],
    "Fabrication": [
        {
            "name": "Structure Fabrication",
            "duration_weeks": 6,
            "deliverable": "Flight Structure Assembly",
            "required_roles": ["Mechanical Engineer", "Quality Assurance"],
            "is_milestone": False,
            "entry_criteria": "Mechanical drawings released, material received",
            "exit_criteria": "Structure passes dimensional inspection",
        },
        {
            "name": "Harness Fabrication",
            "duration_weeks": 4,
            "deliverable": "Flight Harness Set",
            "required_roles": ["Electrical/Power Engineer", "Quality Assurance"],
            "is_milestone": False,
            "entry_criteria": "Wiring diagrams released, connectors received",
            "exit_criteria": "Harness passes continuity and hipot testing",
        },
        {
            "name": "PCB Population & Test",
            "duration_weeks": 5,
            "deliverable": "Populated and Tested Circuit Boards",
            "required_roles": ["Electrical/Power Engineer", "Quality Assurance"],
            "is_milestone": False,
            "entry_criteria": "PCB layouts released, components received",
            "exit_criteria": "All boards pass functional test",
        },
        {
            "name": "Subsystem Assembly & Checkout",
            "duration_weeks": 4,
            "deliverable": "Tested Subsystem Units",
            "required_roles": ["Mechanical Engineer", "Electrical/Power Engineer", "Integration & Test Lead"],
            "is_milestone": False,
            "entry_criteria": "Structure, harness, and boards fabricated",
            "exit_criteria": "All subsystems pass unit-level checkout",
        },
        {
            "name": "Flight Software Development & Unit Test",
            "duration_weeks": 8,
            "deliverable": "Flight Software Build (unit tested)",
            "required_roles": ["Software Engineer"],
            "is_milestone": False,
            "entry_criteria": "FSW design approved",
            "exit_criteria": "All FSW modules pass unit tests, code reviewed",
        },
    ],
    "Integration": [
        {
            "name": "Mechanical Integration",
            "duration_weeks": 3,
            "deliverable": "Mechanically Integrated Spacecraft",
            "required_roles": ["Mechanical Engineer", "Integration & Test Lead", "Quality Assurance"],
            "is_milestone": False,
            "entry_criteria": "All subsystems fabricated and checked out",
            "exit_criteria": "Spacecraft mechanically assembled, torque records complete",
        },
        {
            "name": "Electrical Integration",
            "duration_weeks": 3,
            "deliverable": "Electrically Integrated Spacecraft",
            "required_roles": ["Electrical/Power Engineer", "Integration & Test Lead"],
            "is_milestone": False,
            "entry_criteria": "Mechanical integration complete",
            "exit_criteria": "All electrical connections verified, power-on successful",
        },
        {
            "name": "Flight Software Load & Integration Test",
            "duration_weeks": 3,
            "deliverable": "FSW Integration Test Report",
            "required_roles": ["Software Engineer", "Integration & Test Lead", "Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Electrical integration complete, FSW build ready",
            "exit_criteria": "FSW boots, telemetry flows, commands execute",
        },
        {
            "name": "Comprehensive Functional Test",
            "duration_weeks": 3,
            "deliverable": "Functional Test Report",
            "required_roles": ["Integration & Test Lead", "Systems Engineer", "Quality Assurance"],
            "is_milestone": False,
            "entry_criteria": "FSW integrated",
            "exit_criteria": "All functional test cases pass",
        },
        {
            "name": "RF Compatibility Test",
            "duration_weeks": 2,
            "deliverable": "RF Compatibility Test Report",
            "required_roles": ["RF/Comms Engineer", "Integration & Test Lead"],
            "is_milestone": False,
            "entry_criteria": "Functional test complete",
            "exit_criteria": "End-to-end RF link verified with ground station",
        },
    ],
    "Environmental Testing": [
        {
            "name": "Pre-Environmental Baseline Test",
            "duration_weeks": 1,
            "deliverable": "Pre-Env Baseline Test Report",
            "required_roles": ["Integration & Test Lead", "Quality Assurance"],
            "is_milestone": False,
            "entry_criteria": "Functional test passed",
            "exit_criteria": "Baseline performance data recorded",
        },
        {
            "name": "Thermal Vacuum (TVAC) Testing",
            "duration_weeks": 3,
            "deliverable": "TVAC Test Report",
            "required_roles": ["Integration & Test Lead", "Mechanical Engineer", "Electrical/Power Engineer"],
            "is_milestone": False,
            "entry_criteria": "Pre-env baseline complete, TVAC chamber reserved",
            "exit_criteria": "Spacecraft survives thermal cycling, performance nominal",
        },
        {
            "name": "Vibration Testing",
            "duration_weeks": 2,
            "deliverable": "Vibration Test Report",
            "required_roles": ["Integration & Test Lead", "Mechanical Engineer", "Quality Assurance"],
            "is_milestone": False,
            "entry_criteria": "TVAC complete (or parallel path approved)",
            "exit_criteria": "Spacecraft survives qualification/acceptance levels",
        },
        {
            "name": "EMI/EMC Testing",
            "duration_weeks": 2,
            "deliverable": "EMI/EMC Test Report",
            "required_roles": ["RF/Comms Engineer", "Electrical/Power Engineer", "Integration & Test Lead"],
            "is_milestone": False,
            "entry_criteria": "Spacecraft fully integrated",
            "exit_criteria": "Emissions and susceptibility within limits",
        },
        {
            "name": "Post-Environmental Functional Test",
            "duration_weeks": 1,
            "deliverable": "Post-Env Functional Test Report",
            "required_roles": ["Integration & Test Lead", "Quality Assurance", "Systems Engineer"],
            "is_milestone": True,
            "entry_criteria": "All environmental tests complete",
            "exit_criteria": "Performance matches pre-env baseline within tolerance",
        },
    ],
    "Regulatory": [
        {
            "name": "FCC Application Preparation",
            "duration_weeks": 4,
            "deliverable": "FCC Application Package (Part 25/97)",
            "required_roles": ["Regulatory Specialist", "RF/Comms Engineer", "Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Frequency plan and orbital parameters defined",
            "exit_criteria": "Application package reviewed and ready to file",
        },
        {
            "name": "FCC Filing & Fee Payment",
            "duration_weeks": 1,
            "deliverable": "FCC Filing Confirmation",
            "required_roles": ["Regulatory Specialist", "Project Manager"],
            "is_milestone": False,
            "entry_criteria": "Application package complete",
            "exit_criteria": "Filing confirmation received from FCC",
        },
        {
            "name": "Response to FCC Information Requests",
            "duration_weeks": 6,
            "deliverable": "FCC Correspondence Record",
            "required_roles": ["Regulatory Specialist", "RF/Comms Engineer"],
            "is_milestone": False,
            "entry_criteria": "FCC questions received",
            "exit_criteria": "All FCC questions satisfactorily answered",
        },
        {
            "name": "License Receipt & Conditions Review",
            "duration_weeks": 1,
            "deliverable": "FCC License and Compliance Checklist",
            "required_roles": ["Regulatory Specialist", "Project Manager"],
            "is_milestone": True,
            "entry_criteria": "FCC issues license",
            "exit_criteria": "License conditions understood and compliance plan in place",
        },
    ],
    "IARU/ITU": [
        {
            "name": "IARU Coordination Request Submission",
            "duration_weeks": 2,
            "deliverable": "IARU Coordination Request",
            "required_roles": ["Regulatory Specialist", "RF/Comms Engineer"],
            "is_milestone": False,
            "entry_criteria": "Frequency plan defined",
            "exit_criteria": "Request submitted to IARU Satellite Coordinator",
        },
        {
            "name": "Interference Analysis",
            "duration_weeks": 4,
            "deliverable": "Interference Analysis Report",
            "required_roles": ["RF/Comms Engineer", "Regulatory Specialist"],
            "is_milestone": False,
            "entry_criteria": "IARU acknowledges request",
            "exit_criteria": "Analysis demonstrates acceptable interference levels",
        },
        {
            "name": "Frequency Assignment Coordination",
            "duration_weeks": 8,
            "deliverable": "IARU Frequency Coordination Letter",
            "required_roles": ["Regulatory Specialist"],
            "is_milestone": False,
            "entry_criteria": "Interference analysis submitted",
            "exit_criteria": "Positive coordination letter received",
        },
        {
            "name": "ITU Filing (via Administration)",
            "duration_weeks": 4,
            "deliverable": "ITU API Filing Confirmation",
            "required_roles": ["Regulatory Specialist", "Project Manager"],
            "is_milestone": True,
            "entry_criteria": "IARU coordination complete",
            "exit_criteria": "National administration confirms ITU filing",
        },
    ],
    "Launch Procurement": [
        {
            "name": "Launch Vehicle RFP Development",
            "duration_weeks": 3,
            "deliverable": "Launch Services RFP",
            "required_roles": ["Project Manager", "Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Spacecraft mass/volume envelope defined",
            "exit_criteria": "RFP issued to candidate launch providers",
        },
        {
            "name": "Launch Services Agreement Negotiation",
            "duration_weeks": 6,
            "deliverable": "Signed Launch Services Agreement (LSA)",
            "required_roles": ["Project Manager", "Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Proposals received and evaluated",
            "exit_criteria": "LSA executed with selected provider",
        },
        {
            "name": "Launch Vehicle ICD Compliance",
            "duration_weeks": 4,
            "deliverable": "ICD Compliance Matrix",
            "required_roles": ["Systems Engineer", "Mechanical Engineer", "Electrical/Power Engineer"],
            "is_milestone": False,
            "entry_criteria": "LSA signed, LV ICD received",
            "exit_criteria": "All ICD requirements met or waivered",
        },
        {
            "name": "Mission Analysis & Orbit Injection",
            "duration_weeks": 3,
            "deliverable": "Mission Analysis Report",
            "required_roles": ["Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Launch vehicle selected, orbit defined",
            "exit_criteria": "Injection accuracy and separation conditions confirmed",
        },
    ],
    "Range Safety": [
        {
            "name": "Safety Data Package Preparation",
            "duration_weeks": 4,
            "deliverable": "Range Safety Data Package",
            "required_roles": ["Systems Engineer", "Quality Assurance", "Project Manager"],
            "is_milestone": False,
            "entry_criteria": "Spacecraft design finalized, hazardous materials identified",
            "exit_criteria": "Safety data package submitted to range",
        },
        {
            "name": "Range Safety Review",
            "duration_weeks": 4,
            "deliverable": "Range Safety Review Minutes",
            "required_roles": ["Systems Engineer", "Quality Assurance"],
            "is_milestone": False,
            "entry_criteria": "Safety data package submitted",
            "exit_criteria": "Range safety questions addressed",
        },
        {
            "name": "Range Safety Approval",
            "duration_weeks": 2,
            "deliverable": "Range Safety Approval Letter",
            "required_roles": ["Project Manager"],
            "is_milestone": True,
            "entry_criteria": "All range safety concerns resolved",
            "exit_criteria": "Written approval received from range",
        },
    ],
    "Pre-Ship": [
        {
            "name": "Final Inspection & Closeout",
            "duration_weeks": 1,
            "deliverable": "Final Inspection Report, Closeout Photos",
            "required_roles": ["Quality Assurance", "Integration & Test Lead", "Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Post-env test complete, all anomalies resolved",
            "exit_criteria": "Spacecraft declared flight-ready",
        },
        {
            "name": "Pre-Ship Review (PSR)",
            "duration_weeks": 1,
            "deliverable": "PSR Package and Approval",
            "required_roles": ["Project Manager", "Systems Engineer", "Quality Assurance"],
            "is_milestone": True,
            "entry_criteria": "Final inspection complete, all open items closed",
            "exit_criteria": "PSR board approves shipment",
        },
        {
            "name": "Packing & Shipping Preparation",
            "duration_weeks": 1,
            "deliverable": "Shipping Container (sealed, with indicators)",
            "required_roles": ["Integration & Test Lead", "Quality Assurance"],
            "is_milestone": False,
            "entry_criteria": "PSR passed",
            "exit_criteria": "Spacecraft packed, shock/tilt indicators installed",
        },
        {
            "name": "Transport to Launch Site",
            "duration_weeks": 1,
            "deliverable": "Delivery Confirmation at Launch Site",
            "required_roles": ["Project Manager", "Integration & Test Lead"],
            "is_milestone": False,
            "entry_criteria": "Shipping container sealed, logistics arranged",
            "exit_criteria": "Spacecraft received at launch site, indicators nominal",
        },
    ],
    "Launch Campaign": [
        {
            "name": "Receiving & Unpacking at Launch Site",
            "duration_weeks": 1,
            "deliverable": "Receiving Inspection Report (Launch Site)",
            "required_roles": ["Integration & Test Lead", "Quality Assurance"],
            "is_milestone": False,
            "entry_criteria": "Spacecraft arrived at launch site",
            "exit_criteria": "Spacecraft unpacked, visual inspection nominal",
        },
        {
            "name": "Post-Ship Checkout",
            "duration_weeks": 1,
            "deliverable": "Post-Ship Abbreviated Functional Test Report",
            "required_roles": ["Integration & Test Lead", "Electrical/Power Engineer", "Software Engineer"],
            "is_milestone": False,
            "entry_criteria": "Spacecraft unpacked",
            "exit_criteria": "Abbreviated functional test passes",
        },
        {
            "name": "Launch Vehicle Integration",
            "duration_weeks": 1,
            "deliverable": "LV Integration Report, Separation System Verification",
            "required_roles": ["Integration & Test Lead", "Mechanical Engineer", "Systems Engineer"],
            "is_milestone": False,
            "entry_criteria": "Post-ship checkout passed, LV ready for payload",
            "exit_criteria": "Spacecraft mated to LV, separation system verified",
        },
        {
            "name": "Launch Rehearsal",
            "duration_weeks": 1,
            "deliverable": "Rehearsal Report, Countdown Procedure Verified",
            "required_roles": ["Project Manager", "Systems Engineer", "Integration & Test Lead"],
            "is_milestone": False,
            "entry_criteria": "LV integration complete, ground station ready",
            "exit_criteria": "Countdown rehearsal complete, all teams trained",
        },
        {
            "name": "Final Countdown & Launch",
            "duration_weeks": 1,
            "deliverable": "Launch Confirmation, Initial Telemetry Acquisition",
            "required_roles": ["Project Manager", "Systems Engineer", "RF/Comms Engineer", "Integration & Test Lead"],
            "is_milestone": True,
            "entry_criteria": "All readiness reviews passed, weather GO",
            "exit_criteria": "Spacecraft separated, telemetry acquired, solar arrays deployed",
        },
    ],
    "Operations": [
        {
            "name": "Early Operations & Commissioning",
            "duration_weeks": 4,
            "deliverable": "Commissioning Report",
            "required_roles": ["Systems Engineer", "Software Engineer", "RF/Comms Engineer", "Payload Specialist"],
            "is_milestone": False,
            "entry_criteria": "Telemetry acquired post-separation",
            "exit_criteria": "All subsystems checked out, payload activated",
        },
        {
            "name": "Nominal Operations Transition",
            "duration_weeks": 2,
            "deliverable": "Operations Handover Package",
            "required_roles": ["Project Manager", "Systems Engineer"],
            "is_milestone": True,
            "entry_criteria": "Commissioning complete",
            "exit_criteria": "Operations team trained and running independently",
        },
    ],
}

# Additional WBS for experimental missions
EXPERIMENTAL_WBS = [
    {
        "name": "Experimental License Application",
        "duration_weeks": 4,
        "deliverable": "FCC Experimental License Application (Part 5)",
        "required_roles": ["Regulatory Specialist", "RF/Comms Engineer"],
        "is_milestone": False,
        "entry_criteria": "Experiment parameters defined",
        "exit_criteria": "Experimental license application filed",
        "phase": "Regulatory",
    },
    {
        "name": "Experimental Protocol Development",
        "duration_weeks": 3,
        "deliverable": "Experiment Protocol Document",
        "required_roles": ["Payload Specialist", "Systems Engineer"],
        "is_milestone": False,
        "entry_criteria": "Payload design finalized",
        "exit_criteria": "Experiment protocol reviewed and approved",
        "phase": "CDR",
    },
    {
        "name": "Experimental Payload Qualification",
        "duration_weeks": 4,
        "deliverable": "Payload Qualification Test Report",
        "required_roles": ["Payload Specialist", "Integration & Test Lead"],
        "is_milestone": False,
        "entry_criteria": "Payload fabricated",
        "exit_criteria": "Payload passes qualification testing",
        "phase": "Environmental Testing",
    },
]

# Additional WBS for ITAR/export-controlled missions
EXPORT_CONTROL_WBS = [
    {
        "name": "Export Control Classification (ECCN/USML)",
        "duration_weeks": 3,
        "deliverable": "Commodity Jurisdiction / Classification Determination",
        "required_roles": ["Regulatory Specialist", "Project Manager"],
        "is_milestone": False,
        "entry_criteria": "System design defined",
        "exit_criteria": "Classification determination documented",
        "phase": "Concept",
    },
    {
        "name": "Technology Control Plan Development",
        "duration_weeks": 2,
        "deliverable": "Technology Control Plan (TCP)",
        "required_roles": ["Regulatory Specialist", "Project Manager", "Quality Assurance"],
        "is_milestone": False,
        "entry_criteria": "Export classification complete",
        "exit_criteria": "TCP approved by export control officer",
        "phase": "PDR",
    },
    {
        "name": "Export License Application (if needed)",
        "duration_weeks": 8,
        "deliverable": "Export License or License Exception Documentation",
        "required_roles": ["Regulatory Specialist", "Project Manager"],
        "is_milestone": False,
        "entry_criteria": "TCP in place, foreign persons identified",
        "exit_criteria": "License granted or exception documented",
        "phase": "Procurement",
    },
    {
        "name": "ITAR Compliance Audit",
        "duration_weeks": 2,
        "deliverable": "ITAR Compliance Audit Report",
        "required_roles": ["Regulatory Specialist", "Quality Assurance"],
        "is_milestone": False,
        "entry_criteria": "Pre-ship phase entered",
        "exit_criteria": "No compliance findings, or findings resolved",
        "phase": "Pre-Ship",
    },
]


# ---------------------------------------------------------------------------
# Milestone Templates
# ---------------------------------------------------------------------------

MILESTONE_TEMPLATES = [
    {
        "name": "Mission Concept Review (MCR)",
        "phase": "Concept",
        "position": 0.9,  # fraction through the phase
        "entry_criteria": [
            "Mission requirements document complete",
            "Concept of operations defined",
            "Preliminary cost estimate available",
            "Trade studies complete",
        ],
        "success_criteria": [
            "Review board concurs with mission concept",
            "No unresolved critical issues",
            "Proceed-to-design recommendation issued",
        ],
    },
    {
        "name": "System Requirements Review (SRR)",
        "phase": "PDR",
        "position": 0.2,
        "entry_criteria": [
            "System requirements document complete",
            "Requirements traceability matrix populated",
            "Verification cross-reference matrix started",
        ],
        "success_criteria": [
            "All requirements measurable and verifiable",
            "No TBDs in critical requirements",
            "Stakeholder concurrence on requirements set",
        ],
    },
    {
        "name": "Preliminary Design Review (PDR)",
        "phase": "PDR",
        "position": 0.95,
        "entry_criteria": [
            "All subsystem preliminary designs complete",
            "Interface control documents drafted",
            "Power and link budgets show positive margins",
            "Risk register populated and reviewed",
        ],
        "success_criteria": [
            "Design is feasible and meets requirements",
            "No unresolved critical technical risks",
            "Proceed-to-detailed-design recommendation issued",
        ],
    },
    {
        "name": "Critical Design Review (CDR)",
        "phase": "CDR",
        "position": 0.95,
        "entry_criteria": [
            "Detailed designs complete for all subsystems",
            "Structural and thermal analyses complete",
            "Test plan approved",
            "Manufacturing drawings released",
        ],
        "success_criteria": [
            "Design is build-ready",
            "All analyses show positive margins",
            "Proceed-to-build recommendation issued",
        ],
    },
    {
        "name": "Test Readiness Review (TRR)",
        "phase": "Integration",
        "position": 0.8,
        "entry_criteria": [
            "Spacecraft integrated and functionally tested",
            "Test procedures approved",
            "Test facilities reserved and calibrated",
            "Test team trained",
        ],
        "success_criteria": [
            "Spacecraft ready for environmental testing",
            "All test prerequisites met",
            "Proceed-to-test recommendation issued",
        ],
    },
    {
        "name": "Pre-Ship Review (PSR)",
        "phase": "Pre-Ship",
        "position": 0.4,
        "entry_criteria": [
            "All environmental tests complete and passed",
            "All anomalies resolved or waived",
            "Final inspection complete",
            "Shipping container and logistics ready",
        ],
        "success_criteria": [
            "Spacecraft declared flight-worthy",
            "All open items closed or tracked",
            "Proceed-to-ship recommendation issued",
        ],
    },
    {
        "name": "Flight Readiness Review (FRR)",
        "phase": "Launch Campaign",
        "position": 0.6,
        "entry_criteria": [
            "Post-ship checkout complete",
            "LV integration complete",
            "Ground station validated",
            "Launch rehearsal successful",
            "All regulatory approvals in hand",
        ],
        "success_criteria": [
            "All systems GO for launch",
            "No unresolved constraints",
            "Launch date confirmed",
        ],
    },
    {
        "name": "Launch Readiness Review (LRR)",
        "phase": "Launch Campaign",
        "position": 0.85,
        "entry_criteria": [
            "FRR passed",
            "Final countdown timeline reviewed",
            "Weather forecast acceptable",
            "Range safety approval current",
        ],
        "success_criteria": [
            "All teams report GO",
            "Countdown authorized to proceed",
        ],
    },
    {
        "name": "Post-Launch Assessment Review (PLAR)",
        "phase": "Operations",
        "position": 0.8,
        "entry_criteria": [
            "Initial commissioning complete",
            "All subsystems checked out on-orbit",
            "Performance data collected for assessment",
        ],
        "success_criteria": [
            "Mission objectives achievable with on-orbit performance",
            "Lessons learned documented",
            "Transition to nominal operations approved",
        ],
    },
]


# ---------------------------------------------------------------------------
# RACI Templates by Phase
# ---------------------------------------------------------------------------

# Default RACI assignments: R=Responsible, A=Accountable, C=Consulted, I=Informed
RACI_BY_PHASE = {
    "Concept": {
        "Project Manager": "A",
        "Systems Engineer": "R",
        "Mechanical Engineer": "C",
        "Electrical/Power Engineer": "C",
        "RF/Comms Engineer": "C",
        "Software Engineer": "I",
        "Payload Specialist": "R",
        "Regulatory Specialist": "C",
        "Quality Assurance": "I",
        "Integration & Test Lead": "I",
    },
    "PDR": {
        "Project Manager": "A",
        "Systems Engineer": "R",
        "Mechanical Engineer": "R",
        "Electrical/Power Engineer": "R",
        "RF/Comms Engineer": "R",
        "Software Engineer": "C",
        "Payload Specialist": "C",
        "Regulatory Specialist": "I",
        "Quality Assurance": "C",
        "Integration & Test Lead": "C",
    },
    "CDR": {
        "Project Manager": "A",
        "Systems Engineer": "R",
        "Mechanical Engineer": "R",
        "Electrical/Power Engineer": "R",
        "RF/Comms Engineer": "R",
        "Software Engineer": "R",
        "Payload Specialist": "C",
        "Regulatory Specialist": "I",
        "Quality Assurance": "C",
        "Integration & Test Lead": "R",
    },
    "Procurement": {
        "Project Manager": "R",
        "Systems Engineer": "C",
        "Mechanical Engineer": "C",
        "Electrical/Power Engineer": "C",
        "RF/Comms Engineer": "C",
        "Software Engineer": "I",
        "Payload Specialist": "I",
        "Regulatory Specialist": "I",
        "Quality Assurance": "R",
        "Integration & Test Lead": "C",
    },
    "Fabrication": {
        "Project Manager": "A",
        "Systems Engineer": "C",
        "Mechanical Engineer": "R",
        "Electrical/Power Engineer": "R",
        "RF/Comms Engineer": "C",
        "Software Engineer": "R",
        "Payload Specialist": "C",
        "Regulatory Specialist": "I",
        "Quality Assurance": "R",
        "Integration & Test Lead": "C",
    },
    "Integration": {
        "Project Manager": "A",
        "Systems Engineer": "R",
        "Mechanical Engineer": "R",
        "Electrical/Power Engineer": "R",
        "RF/Comms Engineer": "R",
        "Software Engineer": "R",
        "Payload Specialist": "C",
        "Regulatory Specialist": "I",
        "Quality Assurance": "R",
        "Integration & Test Lead": "R",
    },
    "Environmental Testing": {
        "Project Manager": "A",
        "Systems Engineer": "C",
        "Mechanical Engineer": "R",
        "Electrical/Power Engineer": "R",
        "RF/Comms Engineer": "R",
        "Software Engineer": "C",
        "Payload Specialist": "C",
        "Regulatory Specialist": "I",
        "Quality Assurance": "R",
        "Integration & Test Lead": "R",
    },
    "Regulatory": {
        "Project Manager": "A",
        "Systems Engineer": "C",
        "Mechanical Engineer": "I",
        "Electrical/Power Engineer": "I",
        "RF/Comms Engineer": "R",
        "Software Engineer": "I",
        "Payload Specialist": "I",
        "Regulatory Specialist": "R",
        "Quality Assurance": "I",
        "Integration & Test Lead": "I",
    },
    "IARU/ITU": {
        "Project Manager": "A",
        "Systems Engineer": "C",
        "Mechanical Engineer": "I",
        "Electrical/Power Engineer": "I",
        "RF/Comms Engineer": "R",
        "Software Engineer": "I",
        "Payload Specialist": "I",
        "Regulatory Specialist": "R",
        "Quality Assurance": "I",
        "Integration & Test Lead": "I",
    },
    "Launch Procurement": {
        "Project Manager": "R",
        "Systems Engineer": "R",
        "Mechanical Engineer": "C",
        "Electrical/Power Engineer": "C",
        "RF/Comms Engineer": "I",
        "Software Engineer": "I",
        "Payload Specialist": "I",
        "Regulatory Specialist": "C",
        "Quality Assurance": "C",
        "Integration & Test Lead": "C",
    },
    "Range Safety": {
        "Project Manager": "A",
        "Systems Engineer": "R",
        "Mechanical Engineer": "C",
        "Electrical/Power Engineer": "C",
        "RF/Comms Engineer": "I",
        "Software Engineer": "I",
        "Payload Specialist": "I",
        "Regulatory Specialist": "C",
        "Quality Assurance": "R",
        "Integration & Test Lead": "C",
    },
    "Pre-Ship": {
        "Project Manager": "A",
        "Systems Engineer": "R",
        "Mechanical Engineer": "C",
        "Electrical/Power Engineer": "C",
        "RF/Comms Engineer": "I",
        "Software Engineer": "I",
        "Payload Specialist": "I",
        "Regulatory Specialist": "I",
        "Quality Assurance": "R",
        "Integration & Test Lead": "R",
    },
    "Launch Campaign": {
        "Project Manager": "A",
        "Systems Engineer": "R",
        "Mechanical Engineer": "R",
        "Electrical/Power Engineer": "R",
        "RF/Comms Engineer": "R",
        "Software Engineer": "R",
        "Payload Specialist": "C",
        "Regulatory Specialist": "I",
        "Quality Assurance": "R",
        "Integration & Test Lead": "R",
    },
    "Operations": {
        "Project Manager": "A",
        "Systems Engineer": "R",
        "Mechanical Engineer": "I",
        "Electrical/Power Engineer": "C",
        "RF/Comms Engineer": "R",
        "Software Engineer": "R",
        "Payload Specialist": "R",
        "Regulatory Specialist": "I",
        "Quality Assurance": "I",
        "Integration & Test Lead": "I",
    },
}

# Role-combining rules for small teams
ROLE_COMBINATIONS_UNIVERSITY = {
    "Project Manager": ["Project Manager", "Regulatory Specialist"],
    "Systems Engineer": ["Systems Engineer", "Integration & Test Lead"],
    "Mechanical Engineer": ["Mechanical Engineer", "Quality Assurance"],
    "Electrical/Power Engineer": ["Electrical/Power Engineer", "RF/Comms Engineer"],
    "Software Engineer": ["Software Engineer", "Payload Specialist"],
}

ROLE_COMBINATIONS_STARTUP = {
    "Project Manager": ["Project Manager"],
    "Systems Engineer": ["Systems Engineer", "Integration & Test Lead"],
    "Mechanical Engineer": ["Mechanical Engineer"],
    "Electrical/Power Engineer": ["Electrical/Power Engineer"],
    "RF/Comms Engineer": ["RF/Comms Engineer"],
    "Software Engineer": ["Software Engineer"],
    "Payload Specialist": ["Payload Specialist"],
    "Regulatory Specialist": ["Regulatory Specialist", "Quality Assurance"],
}


# ---------------------------------------------------------------------------
# Risk Templates
# ---------------------------------------------------------------------------

RISK_TEMPLATES = {
    "Concept": [
        {
            "description": "Requirements creep leads to infeasible design",
            "likelihood": "M",
            "impact": "H",
            "mitigation": "Strict change control process from project start; formal requirements baselining",
            "owner_role": "Systems Engineer",
            "trigger": "More than 3 requirements changes after MCR",
        },
        {
            "description": "Insufficient budget allocation for mission scope",
            "likelihood": "M",
            "impact": "H",
            "mitigation": "Independent cost estimate; management reserve of 20-30%",
            "owner_role": "Project Manager",
            "trigger": "Cost estimate exceeds budget by more than 15%",
        },
        {
            "description": "Key trade study assumptions prove invalid",
            "likelihood": "L",
            "impact": "M",
            "mitigation": "Validate assumptions early with prototyping; maintain backup architecture",
            "owner_role": "Systems Engineer",
            "trigger": "Analysis shows margin less than 10% on critical parameter",
        },
    ],
    "PDR": [
        {
            "description": "Interface incompatibilities discovered late",
            "likelihood": "M",
            "impact": "H",
            "mitigation": "Early ICD development; interface working group meetings",
            "owner_role": "Systems Engineer",
            "trigger": "ICD discrepancies found during peer review",
        },
        {
            "description": "Negative power or link margin",
            "likelihood": "M",
            "impact": "H",
            "mitigation": "Conservative assumptions in budgets; identify margin recovery options",
            "owner_role": "Electrical/Power Engineer",
            "trigger": "Budget margin below 3 dB (link) or 10% (power)",
        },
        {
            "description": "Heritage component obsolescence",
            "likelihood": "L",
            "impact": "M",
            "mitigation": "Early vendor engagement; identify alternate sources",
            "owner_role": "Project Manager",
            "trigger": "Vendor end-of-life notice received",
        },
    ],
    "CDR": [
        {
            "description": "Structural analysis reveals insufficient margin",
            "likelihood": "L",
            "impact": "H",
            "mitigation": "Conservative design factors; iterate design before CDR",
            "owner_role": "Mechanical Engineer",
            "trigger": "FEA shows margin of safety below 0.25",
        },
        {
            "description": "Thermal design cannot maintain component temperatures",
            "likelihood": "M",
            "impact": "H",
            "mitigation": "Thermal model early; identify heater/radiator design space",
            "owner_role": "Mechanical Engineer",
            "trigger": "Thermal model shows component above/below allowable range",
        },
        {
            "description": "Flight software complexity exceeds team capacity",
            "likelihood": "M",
            "impact": "M",
            "mitigation": "Incremental development; reuse heritage code where possible",
            "owner_role": "Software Engineer",
            "trigger": "Schedule slip of more than 2 weeks on FSW tasks",
        },
        {
            "description": "Test facility availability conflict",
            "likelihood": "L",
            "impact": "M",
            "mitigation": "Reserve test slots early; identify backup facilities",
            "owner_role": "Integration & Test Lead",
            "trigger": "Facility schedule conflict identified",
        },
    ],
    "Procurement": [
        {
            "description": "Long-lead item delivery delay",
            "likelihood": "H",
            "impact": "H",
            "mitigation": "Order early; maintain buffer in schedule; identify alternate vendors",
            "owner_role": "Project Manager",
            "trigger": "Vendor misses committed delivery date",
        },
        {
            "description": "Component counterfeit or quality issue",
            "likelihood": "L",
            "impact": "H",
            "mitigation": "Buy from authorized distributors; receiving inspection",
            "owner_role": "Quality Assurance",
            "trigger": "Component fails incoming inspection or has suspect markings",
        },
        {
            "description": "Budget overrun on hardware costs",
            "likelihood": "M",
            "impact": "M",
            "mitigation": "Track actuals vs. budget weekly; early escalation",
            "owner_role": "Project Manager",
            "trigger": "Cumulative spend exceeds plan by 10%",
        },
    ],
    "Fabrication": [
        {
            "description": "PCB fabrication defect requiring re-spin",
            "likelihood": "M",
            "impact": "M",
            "mitigation": "Design rule checks; prototype boards before flight build",
            "owner_role": "Electrical/Power Engineer",
            "trigger": "Board fails electrical test or inspection reveals defect",
        },
        {
            "description": "Mechanical part tolerance issue",
            "likelihood": "L",
            "impact": "M",
            "mitigation": "GD&T review; first-article inspection before batch",
            "owner_role": "Mechanical Engineer",
            "trigger": "Part fails dimensional inspection",
        },
        {
            "description": "Workmanship defect in harness fabrication",
            "likelihood": "M",
            "impact": "M",
            "mitigation": "IPC-certified technicians; in-process inspection",
            "owner_role": "Quality Assurance",
            "trigger": "Harness fails continuity or hipot test",
        },
    ],
    "Integration": [
        {
            "description": "Unexpected electromagnetic interference between subsystems",
            "likelihood": "M",
            "impact": "H",
            "mitigation": "EMI analysis during design; shielding and filtering provisions",
            "owner_role": "RF/Comms Engineer",
            "trigger": "Anomalous behavior during powered integration",
        },
        {
            "description": "Mechanical fit-check failure",
            "likelihood": "L",
            "impact": "M",
            "mitigation": "3D model interference checks; fit-check with mass models",
            "owner_role": "Mechanical Engineer",
            "trigger": "Component does not fit during integration",
        },
        {
            "description": "Flight software integration anomaly",
            "likelihood": "M",
            "impact": "M",
            "mitigation": "Hardware-in-the-loop testing; incremental integration",
            "owner_role": "Software Engineer",
            "trigger": "Unexpected behavior during FSW integration test",
        },
    ],
    "Environmental Testing": [
        {
            "description": "Workmanship failure during vibration testing",
            "likelihood": "M",
            "impact": "H",
            "mitigation": "Proper torque values; workmanship screening before qual",
            "owner_role": "Integration & Test Lead",
            "trigger": "Post-vibe inspection or functional test reveals anomaly",
        },
        {
            "description": "Thermal vacuum test reveals design flaw",
            "likelihood": "L",
            "impact": "H",
            "mitigation": "Accurate thermal modeling; component-level thermal testing",
            "owner_role": "Integration & Test Lead",
            "trigger": "Component exceeds temperature limit during TVAC",
        },
        {
            "description": "Test facility anomaly damages hardware",
            "likelihood": "L",
            "impact": "H",
            "mitigation": "Facility pre-checks; abort criteria defined; insurance",
            "owner_role": "Integration & Test Lead",
            "trigger": "Chamber or shaker malfunction during test",
        },
    ],
    "Regulatory": [
        {
            "description": "FCC license delayed beyond schedule need-date",
            "likelihood": "M",
            "impact": "H",
            "mitigation": "File early (18+ months before launch); maintain FCC liaison",
            "owner_role": "Regulatory Specialist",
            "trigger": "No FCC response 6 months after filing",
        },
        {
            "description": "Interference objection from existing operator",
            "likelihood": "M",
            "impact": "M",
            "mitigation": "Thorough interference analysis; coordination with incumbents",
            "owner_role": "Regulatory Specialist",
            "trigger": "Formal objection received during comment period",
        },
    ],
    "IARU/ITU": [
        {
            "description": "IARU coordination rejection or extended timeline",
            "likelihood": "M",
            "impact": "M",
            "mitigation": "Engage IARU early; select frequencies with least congestion",
            "owner_role": "Regulatory Specialist",
            "trigger": "Negative coordination response or no response in 4 months",
        },
        {
            "description": "Frequency band becomes unavailable due to new allocation",
            "likelihood": "L",
            "impact": "H",
            "mitigation": "Monitor WRC decisions; design for frequency agility",
            "owner_role": "RF/Comms Engineer",
            "trigger": "Regulatory change affecting planned frequency band",
        },
    ],
    "Launch Procurement": [
        {
            "description": "Launch vehicle failure delays manifest",
            "likelihood": "L",
            "impact": "H",
            "mitigation": "Maintain backup launch option; schedule margin",
            "owner_role": "Project Manager",
            "trigger": "Launch provider announces stand-down or investigation",
        },
        {
            "description": "Launch cost increase or unfavorable contract terms",
            "likelihood": "M",
            "impact": "M",
            "mitigation": "Competitive procurement; budget reserve for cost growth",
            "owner_role": "Project Manager",
            "trigger": "Launch provider proposes price increase >10%",
        },
        {
            "description": "ICD non-compliance discovered late",
            "likelihood": "L",
            "impact": "H",
            "mitigation": "Early ICD review; compliance matrix tracking",
            "owner_role": "Systems Engineer",
            "trigger": "Compliance gap found during verification",
        },
    ],
    "Range Safety": [
        {
            "description": "Range safety review identifies show-stopper",
            "likelihood": "L",
            "impact": "H",
            "mitigation": "Early engagement with range; conservative hazard mitigations",
            "owner_role": "Systems Engineer",
            "trigger": "Range requests hardware modification for safety",
        },
        {
            "description": "Safety data package requires extensive rework",
            "likelihood": "M",
            "impact": "M",
            "mitigation": "Use templates from previous missions; pre-submission review",
            "owner_role": "Quality Assurance",
            "trigger": "Range returns package with multiple deficiencies",
        },
    ],
    "Pre-Ship": [
        {
            "description": "Open anomaly blocks shipment",
            "likelihood": "M",
            "impact": "M",
            "mitigation": "Aggressive anomaly closure tracking; daily stand-ups",
            "owner_role": "Integration & Test Lead",
            "trigger": "Open anomaly remains unresolved at PSR",
        },
        {
            "description": "Shipping damage to spacecraft",
            "likelihood": "L",
            "impact": "H",
            "mitigation": "Proper shipping container design; shock indicators; insurance",
            "owner_role": "Integration & Test Lead",
            "trigger": "Shock or tilt indicator tripped upon arrival",
        },
    ],
    "Launch Campaign": [
        {
            "description": "Post-ship functional test reveals anomaly",
            "likelihood": "L",
            "impact": "H",
            "mitigation": "Thorough pre-ship testing; bring spares and repair capability",
            "owner_role": "Integration & Test Lead",
            "trigger": "Abbreviated functional test fails at launch site",
        },
        {
            "description": "Weather or range schedule delays launch",
            "likelihood": "M",
            "impact": "M",
            "mitigation": "Schedule buffer; team prepared for extended campaign",
            "owner_role": "Project Manager",
            "trigger": "Launch scrubbed or slip announced",
        },
        {
            "description": "Ground station readiness issue",
            "likelihood": "L",
            "impact": "H",
            "mitigation": "Early ground station testing; backup station agreements",
            "owner_role": "RF/Comms Engineer",
            "trigger": "Ground station fails rehearsal or compatibility test",
        },
    ],
    "Operations": [
        {
            "description": "Spacecraft anomaly during commissioning",
            "likelihood": "M",
            "impact": "H",
            "mitigation": "Comprehensive on-orbit test procedures; anomaly response plan",
            "owner_role": "Systems Engineer",
            "trigger": "Telemetry shows off-nominal behavior",
        },
        {
            "description": "Solar array or deployment mechanism failure",
            "likelihood": "L",
            "impact": "H",
            "mitigation": "Extensive ground testing of deployables; redundant mechanisms",
            "owner_role": "Mechanical Engineer",
            "trigger": "Deployment telemetry does not confirm full deployment",
        },
    ],
}


# ---------------------------------------------------------------------------
# Meeting Cadence Templates
# ---------------------------------------------------------------------------

MEETING_TEMPLATES = {
    "daily_standup": {
        "name": "Daily Standup",
        "frequency": "Daily (during active I&T and launch campaign)",
        "duration_minutes": 15,
        "purpose": "Status updates, blocker identification, task coordination",
        "attendees": ["Project Manager", "Integration & Test Lead", "Active discipline leads"],
    },
    "weekly_technical": {
        "name": "Weekly Technical Meeting",
        "frequency": "Weekly",
        "duration_minutes": 60,
        "purpose": "Technical progress review, issue resolution, design decisions",
        "attendees": ["Systems Engineer", "All discipline leads", "Integration & Test Lead"],
    },
    "biweekly_management": {
        "name": "Biweekly Management Review",
        "frequency": "Every 2 weeks",
        "duration_minutes": 45,
        "purpose": "Schedule status, budget tracking, risk review, decisions needed",
        "attendees": ["Project Manager", "Systems Engineer", "Quality Assurance"],
    },
    "monthly_program": {
        "name": "Monthly Program Review",
        "frequency": "Monthly",
        "duration_minutes": 90,
        "purpose": "Comprehensive program status to stakeholders/sponsor",
        "attendees": ["Project Manager", "Systems Engineer", "All leads", "Stakeholders"],
    },
    "phase_gate": {
        "name": "Phase Gate Review",
        "frequency": "At each major milestone",
        "duration_minutes": 240,
        "purpose": "Formal review of phase deliverables; go/no-go decision for next phase",
        "attendees": ["Full team", "Review board", "Stakeholders"],
    },
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _normalize_phase_name(name: str) -> str:
    """Normalize a phase name from timeline to a canonical form."""
    lower = name.lower().strip()
    return PHASE_ALIASES.get(lower, name)


def _parse_date(date_val) -> datetime:
    """Parse a date value that could be a string or datetime."""
    if isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, str):
        # Try common formats
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y", "%d %b %Y"):
            try:
                return datetime.strptime(date_val, fmt)
            except ValueError:
                continue
    # Default fallback
    return datetime.now()


def _get_complexity(timeline: dict) -> float:
    """Get complexity scaling factor from satellite class."""
    sat_class = timeline.get("satellite_class", "smallsat").lower()
    for key, val in COMPLEXITY_SCALE.items():
        if key in sat_class:
            return val
    return 0.6


def _scale_duration(base_weeks: int, complexity: float) -> int:
    """Scale a task duration by complexity factor."""
    scaled = max(1, round(base_weeks * complexity))
    return scaled


def _interpolate_date(start: datetime, end: datetime, fraction: float) -> datetime:
    """Get a date at a given fraction between start and end."""
    delta = end - start
    return start + timedelta(days=int(delta.days * fraction))


def _months_between(start: datetime, end: datetime) -> list:
    """Generate list of YYYY-MM strings between start and end."""
    months = []
    current = start.replace(day=1)
    end_month = end.replace(day=1)
    while current <= end_month:
        months.append(current.strftime("%Y-%m"))
        # Advance to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return months


def _get_launch_cost(timeline: dict) -> float:
    """Estimate launch services cost from timeline launch vehicles."""
    launch_vehicles = timeline.get("launch_vehicles", [])
    if not launch_vehicles:
        return 5_000_000  # default estimate

    # Use first (primary) launch vehicle cost if available
    if isinstance(launch_vehicles[0], dict):
        cost = launch_vehicles[0].get("cost_usd", launch_vehicles[0].get("price_usd", 5_000_000))
        if cost:
            return float(cost)

    # Estimate from mass
    mass_kg = timeline.get("mass_kg", 10)
    if mass_kg <= 5:
        return 300_000
    elif mass_kg <= 50:
        return 1_000_000
    elif mass_kg <= 300:
        return 5_000_000
    elif mass_kg <= 1000:
        return 30_000_000
    else:
        return 100_000_000


# ---------------------------------------------------------------------------
# Main Generation Functions
# ---------------------------------------------------------------------------

def _generate_wbs(timeline: dict, team_config: dict) -> dict:
    """Generate Work Breakdown Structure from timeline phases."""
    complexity = _get_complexity(timeline)
    phases = timeline.get("phases", [])
    is_experimental = timeline.get("is_experimental", False)
    needs_export_control = timeline.get("needs_export_control", False)

    wbs = {}
    all_work_packages = []
    phase_number = 0

    for phase_data in phases:
        phase_raw_name = phase_data.get("name", "Unknown")
        phase_name = _normalize_phase_name(phase_raw_name)
        phase_start = _parse_date(phase_data.get("start", datetime.now()))
        phase_end = _parse_date(phase_data.get("end", datetime.now() + timedelta(days=90)))

        # Get WBS template for this phase
        template = WBS_TEMPLATES.get(phase_name, [])
        if not template:
            # Try partial match
            for key in WBS_TEMPLATES:
                if key.lower() in phase_name.lower() or phase_name.lower() in key.lower():
                    template = WBS_TEMPLATES[key]
                    phase_name = key
                    break

        if not template:
            # Generate a minimal WBS for unknown phases
            template = [
                {
                    "name": f"{phase_raw_name} Planning",
                    "duration_weeks": 2,
                    "deliverable": f"{phase_raw_name} Plan",
                    "required_roles": ["Project Manager", "Systems Engineer"],
                    "is_milestone": False,
                    "entry_criteria": "Previous phase complete",
                    "exit_criteria": f"{phase_raw_name} plan approved",
                },
                {
                    "name": f"{phase_raw_name} Execution",
                    "duration_weeks": 4,
                    "deliverable": f"{phase_raw_name} Deliverables",
                    "required_roles": ["Systems Engineer"],
                    "is_milestone": False,
                    "entry_criteria": "Plan approved",
                    "exit_criteria": "All deliverables complete",
                },
                {
                    "name": f"{phase_raw_name} Review",
                    "duration_weeks": 1,
                    "deliverable": f"{phase_raw_name} Review Minutes",
                    "required_roles": ["Project Manager", "Systems Engineer"],
                    "is_milestone": True,
                    "entry_criteria": "All deliverables ready",
                    "exit_criteria": "Review board approves",
                },
            ]

        phase_number += 1
        phase_wps = []
        total_template_weeks = sum(t["duration_weeks"] for t in template)
        phase_duration_days = (phase_end - phase_start).days
        if phase_duration_days <= 0:
            phase_duration_days = 90  # fallback

        # Scale tasks to fit within phase duration
        time_scale = phase_duration_days / (total_template_weeks * 7) if total_template_weeks > 0 else 1.0

        current_start = phase_start
        for idx, task_template in enumerate(template):
            wp_id = f"{phase_number}.{idx + 1}"
            scaled_weeks = max(1, round(task_template["duration_weeks"] * complexity * time_scale))
            wp_end = current_start + timedelta(weeks=scaled_weeks)

            # Don't let task extend beyond phase end
            if wp_end > phase_end:
                wp_end = phase_end

            wp = {
                "id": wp_id,
                "name": task_template["name"],
                "phase": phase_name,
                "duration_weeks": scaled_weeks,
                "start": current_start.strftime("%Y-%m-%d"),
                "end": wp_end.strftime("%Y-%m-%d"),
                "deliverable": task_template["deliverable"],
                "required_roles": task_template["required_roles"],
                "is_milestone": task_template["is_milestone"],
                "entry_criteria": task_template["entry_criteria"],
                "exit_criteria": task_template["exit_criteria"],
            }
            phase_wps.append(wp)
            all_work_packages.append(wp)

            # Advance start for next task (allow some overlap for complex phases)
            overlap_factor = 0.7 if complexity >= 0.8 else 0.85
            advance_days = max(1, int(scaled_weeks * 7 * overlap_factor))
            current_start = current_start + timedelta(days=advance_days)
            if current_start >= phase_end:
                current_start = phase_end - timedelta(days=7)

        wbs[phase_name] = phase_wps

    # Add experimental work packages
    if is_experimental:
        for exp_wp in EXPERIMENTAL_WBS:
            target_phase = exp_wp["phase"]
            if target_phase in wbs:
                existing = wbs[target_phase]
                phase_num = None
                if existing:
                    phase_num = existing[0]["id"].split(".")[0]
                else:
                    phase_num = str(phase_number + 1)
                new_idx = len(existing) + 1
                wp_id = f"{phase_num}.{new_idx}"

                # Find phase dates
                phase_start = _parse_date(existing[0]["start"]) if existing else datetime.now()
                phase_end = _parse_date(existing[-1]["end"]) if existing else datetime.now() + timedelta(days=60)
                wp_start = _interpolate_date(phase_start, phase_end, 0.3)
                wp_end = wp_start + timedelta(weeks=_scale_duration(exp_wp["duration_weeks"], complexity))

                wp = {
                    "id": wp_id,
                    "name": exp_wp["name"],
                    "phase": target_phase,
                    "duration_weeks": _scale_duration(exp_wp["duration_weeks"], complexity),
                    "start": wp_start.strftime("%Y-%m-%d"),
                    "end": wp_end.strftime("%Y-%m-%d"),
                    "deliverable": exp_wp["deliverable"],
                    "required_roles": exp_wp["required_roles"],
                    "is_milestone": exp_wp["is_milestone"],
                    "entry_criteria": exp_wp["entry_criteria"],
                    "exit_criteria": exp_wp["exit_criteria"],
                }
                wbs[target_phase].append(wp)
                all_work_packages.append(wp)

    # Add export control work packages
    if needs_export_control:
        for ec_wp in EXPORT_CONTROL_WBS:
            target_phase = ec_wp["phase"]
            if target_phase in wbs:
                existing = wbs[target_phase]
                phase_num = None
                if existing:
                    phase_num = existing[0]["id"].split(".")[0]
                else:
                    phase_num = str(phase_number + 1)
                new_idx = len(existing) + 1
                wp_id = f"{phase_num}.{new_idx}"

                phase_start = _parse_date(existing[0]["start"]) if existing else datetime.now()
                phase_end = _parse_date(existing[-1]["end"]) if existing else datetime.now() + timedelta(days=60)
                wp_start = _interpolate_date(phase_start, phase_end, 0.1)
                wp_end = wp_start + timedelta(weeks=_scale_duration(ec_wp["duration_weeks"], complexity))

                wp = {
                    "id": wp_id,
                    "name": ec_wp["name"],
                    "phase": target_phase,
                    "duration_weeks": _scale_duration(ec_wp["duration_weeks"], complexity),
                    "start": wp_start.strftime("%Y-%m-%d"),
                    "end": wp_end.strftime("%Y-%m-%d"),
                    "deliverable": ec_wp["deliverable"],
                    "required_roles": ec_wp["required_roles"],
                    "is_milestone": ec_wp["is_milestone"],
                    "entry_criteria": ec_wp["entry_criteria"],
                    "exit_criteria": ec_wp["exit_criteria"],
                }
                wbs[target_phase].append(wp)
                all_work_packages.append(wp)

    return {"by_phase": wbs, "all_work_packages": all_work_packages}


def _generate_milestones(timeline: dict, wbs: dict) -> list:
    """Generate milestone schedule from phase dates."""
    phases = timeline.get("phases", [])
    milestones = []

    # Build phase date lookup
    phase_dates = {}
    for phase_data in phases:
        phase_name = _normalize_phase_name(phase_data.get("name", ""))
        phase_dates[phase_name] = {
            "start": _parse_date(phase_data.get("start", datetime.now())),
            "end": _parse_date(phase_data.get("end", datetime.now() + timedelta(days=90))),
        }

    for template in MILESTONE_TEMPLATES:
        phase_name = template["phase"]
        if phase_name in phase_dates:
            dates = phase_dates[phase_name]
            milestone_date = _interpolate_date(dates["start"], dates["end"], template["position"])
            milestones.append({
                "name": template["name"],
                "date": milestone_date.strftime("%Y-%m-%d"),
                "phase": phase_name,
                "entry_criteria": template["entry_criteria"],
                "success_criteria": template["success_criteria"],
            })
        else:
            # Try to find a close match
            for pname, pdates in phase_dates.items():
                if template["phase"].lower() in pname.lower():
                    milestone_date = _interpolate_date(pdates["start"], pdates["end"], template["position"])
                    milestones.append({
                        "name": template["name"],
                        "date": milestone_date.strftime("%Y-%m-%d"),
                        "phase": pname,
                        "entry_criteria": template["entry_criteria"],
                        "success_criteria": template["success_criteria"],
                    })
                    break

    # Sort milestones by date
    milestones.sort(key=lambda m: m["date"])
    return milestones


def _generate_raci(timeline: dict, team_config: dict) -> dict:
    """Generate RACI matrix based on team configuration."""
    experience = team_config.get("experience_level", "experienced_industry")
    phases = timeline.get("phases", [])

    # Determine active roles
    if experience == "government_prime":
        roles = STANDARD_ROLES + GOVERNMENT_EXTRA_ROLES
    else:
        roles = list(STANDARD_ROLES)

    raci_matrix = {}
    role_combinations = None

    if experience == "university":
        role_combinations = ROLE_COMBINATIONS_UNIVERSITY
    elif experience == "startup":
        role_combinations = ROLE_COMBINATIONS_STARTUP

    for phase_data in phases:
        phase_name = _normalize_phase_name(phase_data.get("name", ""))
        base_raci = RACI_BY_PHASE.get(phase_name, {})

        if not base_raci:
            # Find closest match
            for key in RACI_BY_PHASE:
                if key.lower() in phase_name.lower() or phase_name.lower() in key.lower():
                    base_raci = RACI_BY_PHASE[key]
                    break

        if not base_raci:
            # Default RACI
            base_raci = {role: "I" for role in STANDARD_ROLES}
            base_raci["Project Manager"] = "A"
            base_raci["Systems Engineer"] = "R"

        phase_raci = {}
        for role in roles:
            if role in base_raci:
                phase_raci[role] = base_raci[role]
            elif role in GOVERNMENT_EXTRA_ROLES:
                # Assign government-specific roles
                if role == "Program Manager":
                    phase_raci[role] = "A"
                    # Downgrade PM from A to R when Program Manager is present
                    if "Project Manager" in phase_raci and phase_raci["Project Manager"] == "A":
                        phase_raci["Project Manager"] = "R"
                elif role == "Chief Engineer":
                    phase_raci[role] = "C"
                elif role == "Mission Assurance":
                    phase_raci[role] = "C"
                elif role == "Safety Officer":
                    phase_raci[role] = "I"
                elif role == "Contracts":
                    phase_raci[role] = "I"
            else:
                phase_raci[role] = "I"

        raci_matrix[phase_name] = phase_raci

    # Generate role combination notes for small teams
    combined_roles_note = None
    if role_combinations:
        combined_roles_note = {}
        for combined_person, held_roles in role_combinations.items():
            if len(held_roles) > 1:
                combined_roles_note[combined_person] = held_roles

    return {
        "matrix": raci_matrix,
        "roles": roles,
        "combined_roles": combined_roles_note,
        "experience_level": experience,
    }


def _generate_meeting_cadence(team_config: dict) -> list:
    """Generate meeting schedule based on team configuration."""
    experience = team_config.get("experience_level", "experienced_industry")
    team_size = team_config.get("team_size", 5)

    meetings = []

    # Daily standups - always for active phases
    standup = dict(MEETING_TEMPLATES["daily_standup"])
    if team_size <= 4:
        standup["duration_minutes"] = 10
        standup["notes"] = "Brief sync; can be informal for very small teams"
    elif experience == "university":
        standup["notes"] = "Consider async updates (Slack/Discord) instead of formal standup"
    meetings.append(standup)

    # Weekly technical
    weekly = dict(MEETING_TEMPLATES["weekly_technical"])
    if team_size <= 6:
        weekly["duration_minutes"] = 45
        weekly["notes"] = "Combined technical and management for small teams"
    elif experience == "government_prime":
        weekly["duration_minutes"] = 90
        weekly["attendees"] = weekly["attendees"] + ["Program Manager", "Chief Engineer"]
        weekly["notes"] = "Include action item tracking and formal minutes"
    meetings.append(weekly)

    # Biweekly management
    biweekly = dict(MEETING_TEMPLATES["biweekly_management"])
    if experience == "university":
        biweekly["frequency"] = "Monthly (combined with program review)"
        biweekly["notes"] = "Combine with advisor/sponsor check-in"
    elif experience == "government_prime":
        biweekly["frequency"] = "Weekly"
        biweekly["duration_minutes"] = 60
        biweekly["attendees"] = ["Program Manager", "Project Manager", "Chief Engineer", "Contracts", "Mission Assurance"]
        biweekly["notes"] = "Formal management review with action tracking"
    meetings.append(biweekly)

    # Monthly program review
    monthly = dict(MEETING_TEMPLATES["monthly_program"])
    if experience == "government_prime":
        monthly["duration_minutes"] = 120
        monthly["attendees"] = monthly["attendees"] + ["Customer/Sponsor", "Contracting Officer"]
        monthly["notes"] = "Formal program review with EVM reporting"
    elif experience == "university":
        monthly["duration_minutes"] = 60
        monthly["notes"] = "Faculty advisor review; include student team progress"
    meetings.append(monthly)

    # Phase gate reviews
    phase_gate = dict(MEETING_TEMPLATES["phase_gate"])
    if experience == "university":
        phase_gate["duration_minutes"] = 120
        phase_gate["notes"] = "Include faculty committee; may combine with academic milestones"
    elif experience == "government_prime":
        phase_gate["duration_minutes"] = 480
        phase_gate["notes"] = "Multi-day review for large programs; independent review team"
    meetings.append(phase_gate)

    return meetings


def _generate_dependencies(wbs: dict) -> list:
    """Generate critical path dependencies between work packages."""
    all_wps = wbs.get("all_work_packages", [])
    by_phase = wbs.get("by_phase", {})
    dependencies = []

    # Phase ordering for inter-phase dependencies
    phase_order = [
        "Concept", "PDR", "CDR", "Procurement", "Fabrication",
        "Integration", "Environmental Testing", "Pre-Ship", "Launch Campaign", "Operations"
    ]

    # Intra-phase dependencies (sequential within each phase)
    for phase_name, wps in by_phase.items():
        for i in range(len(wps) - 1):
            # Each task depends on the previous one (with some exceptions for parallel work)
            dep = {
                "from_id": wps[i]["id"],
                "to_id": wps[i + 1]["id"],
                "type": "finish-to-start",
                "lag_weeks": 0,
                "description": f"{wps[i]['name']} -> {wps[i + 1]['name']}",
            }
            dependencies.append(dep)

    # Inter-phase dependencies (last task of phase N -> first task of phase N+1)
    prev_phase = None
    for phase_name in phase_order:
        if phase_name in by_phase and by_phase[phase_name]:
            if prev_phase and prev_phase in by_phase and by_phase[prev_phase]:
                last_wp = by_phase[prev_phase][-1]
                first_wp = by_phase[phase_name][0]
                dep = {
                    "from_id": last_wp["id"],
                    "to_id": first_wp["id"],
                    "type": "finish-to-start",
                    "lag_weeks": 0,
                    "description": f"Phase gate: {prev_phase} -> {phase_name}",
                }
                dependencies.append(dep)
            prev_phase = phase_name

    # Regulatory can start in parallel with design phases
    if "Regulatory" in by_phase and by_phase["Regulatory"]:
        if "PDR" in by_phase and by_phase["PDR"]:
            # Regulatory starts when PDR starts (start-to-start)
            dep = {
                "from_id": by_phase["PDR"][0]["id"],
                "to_id": by_phase["Regulatory"][0]["id"],
                "type": "start-to-start",
                "lag_weeks": 2,
                "description": "Regulatory work begins shortly after design starts",
            }
            dependencies.append(dep)

    # IARU/ITU can start with Regulatory
    if "IARU/ITU" in by_phase and by_phase["IARU/ITU"]:
        if "Regulatory" in by_phase and by_phase["Regulatory"]:
            dep = {
                "from_id": by_phase["Regulatory"][0]["id"],
                "to_id": by_phase["IARU/ITU"][0]["id"],
                "type": "start-to-start",
                "lag_weeks": 0,
                "description": "IARU coordination begins with regulatory work",
            }
            dependencies.append(dep)

    # Launch procurement starts during CDR
    if "Launch Procurement" in by_phase and by_phase["Launch Procurement"]:
        if "CDR" in by_phase and by_phase["CDR"]:
            dep = {
                "from_id": by_phase["CDR"][0]["id"],
                "to_id": by_phase["Launch Procurement"][0]["id"],
                "type": "start-to-start",
                "lag_weeks": 4,
                "description": "Launch procurement begins during detailed design",
            }
            dependencies.append(dep)

    # Regulatory must complete before Launch Campaign
    if "Regulatory" in by_phase and by_phase["Regulatory"]:
        if "Launch Campaign" in by_phase and by_phase["Launch Campaign"]:
            dep = {
                "from_id": by_phase["Regulatory"][-1]["id"],
                "to_id": by_phase["Launch Campaign"][0]["id"],
                "type": "finish-to-start",
                "lag_weeks": 0,
                "description": "License required before launch",
            }
            dependencies.append(dep)

    # Range Safety must complete before Launch Campaign
    if "Range Safety" in by_phase and by_phase["Range Safety"]:
        if "Launch Campaign" in by_phase and by_phase["Launch Campaign"]:
            dep = {
                "from_id": by_phase["Range Safety"][-1]["id"],
                "to_id": by_phase["Launch Campaign"][0]["id"],
                "type": "finish-to-start",
                "lag_weeks": 0,
                "description": "Range safety approval required before launch campaign",
            }
            dependencies.append(dep)

    return dependencies


def _generate_risks(timeline: dict, team_config: dict) -> dict:
    """Generate risk register by phase."""
    phases = timeline.get("phases", [])
    experience = team_config.get("experience_level", "experienced_industry")
    risks_by_phase = {}

    for phase_data in phases:
        phase_name = _normalize_phase_name(phase_data.get("name", ""))
        phase_risks = RISK_TEMPLATES.get(phase_name, [])

        if not phase_risks:
            for key in RISK_TEMPLATES:
                if key.lower() in phase_name.lower() or phase_name.lower() in key.lower():
                    phase_risks = RISK_TEMPLATES[key]
                    break

        if not phase_risks:
            # Generate generic risks for unknown phases
            phase_risks = [
                {
                    "description": f"Schedule slip in {phase_name}",
                    "likelihood": "M",
                    "impact": "M",
                    "mitigation": "Close schedule tracking; weekly status updates",
                    "owner_role": "Project Manager",
                    "trigger": "Tasks fall behind plan by more than 1 week",
                },
                {
                    "description": f"Resource availability issue during {phase_name}",
                    "likelihood": "M",
                    "impact": "M",
                    "mitigation": "Cross-training; resource planning",
                    "owner_role": "Project Manager",
                    "trigger": "Key person unavailable for more than 1 week",
                },
            ]

        # Adjust risk likelihood for experience level
        adjusted_risks = []
        for risk in phase_risks:
            adjusted_risk = dict(risk)
            if experience == "university":
                # University teams face higher likelihood on technical risks
                if adjusted_risk["likelihood"] == "L":
                    adjusted_risk["likelihood"] = "M"
                elif adjusted_risk["likelihood"] == "M":
                    adjusted_risk["likelihood"] = "H"
            elif experience == "government_prime":
                # Experienced teams face lower technical risk but higher process risk
                if "schedule" in adjusted_risk["description"].lower() or "cost" in adjusted_risk["description"].lower():
                    pass  # keep as-is for programmatic risks
                elif adjusted_risk["likelihood"] == "H":
                    adjusted_risk["likelihood"] = "M"
                elif adjusted_risk["likelihood"] == "M":
                    adjusted_risk["likelihood"] = "L"
            adjusted_risks.append(adjusted_risk)

        risks_by_phase[phase_name] = adjusted_risks

    return risks_by_phase


def _generate_staffing_profile(timeline: dict, team_config: dict, wbs: dict) -> list:
    """Generate month-by-month staffing profile."""
    phases = timeline.get("phases", [])
    team_size = team_config.get("team_size", 5)
    experience = team_config.get("experience_level", "experienced_industry")
    staffing_multiplier = EXPERIENCE_STAFFING.get(experience, 1.0)

    if not phases:
        return []

    # Determine overall date range
    all_starts = [_parse_date(p.get("start", datetime.now())) for p in phases]
    all_ends = [_parse_date(p.get("end", datetime.now() + timedelta(days=180))) for p in phases]
    project_start = min(all_starts)
    project_end = max(all_ends)

    months = _months_between(project_start, project_end)

    # Base staffing needs by phase (FTE fractions for experienced_industry team)
    phase_staffing = {
        "Concept": {
            "Project Manager": 0.5, "Systems Engineer": 1.0, "Mechanical Engineer": 0.2,
            "Electrical/Power Engineer": 0.2, "RF/Comms Engineer": 0.2, "Software Engineer": 0.1,
            "Payload Specialist": 0.5, "Regulatory Specialist": 0.2, "Quality Assurance": 0.1,
            "Integration & Test Lead": 0.1,
        },
        "PDR": {
            "Project Manager": 0.5, "Systems Engineer": 1.0, "Mechanical Engineer": 0.8,
            "Electrical/Power Engineer": 0.8, "RF/Comms Engineer": 0.8, "Software Engineer": 0.3,
            "Payload Specialist": 0.5, "Regulatory Specialist": 0.3, "Quality Assurance": 0.2,
            "Integration & Test Lead": 0.3,
        },
        "CDR": {
            "Project Manager": 0.5, "Systems Engineer": 1.0, "Mechanical Engineer": 1.0,
            "Electrical/Power Engineer": 1.0, "RF/Comms Engineer": 1.0, "Software Engineer": 0.8,
            "Payload Specialist": 0.5, "Regulatory Specialist": 0.2, "Quality Assurance": 0.3,
            "Integration & Test Lead": 0.5,
        },
        "Procurement": {
            "Project Manager": 0.8, "Systems Engineer": 0.3, "Mechanical Engineer": 0.2,
            "Electrical/Power Engineer": 0.3, "RF/Comms Engineer": 0.2, "Software Engineer": 0.1,
            "Payload Specialist": 0.2, "Regulatory Specialist": 0.1, "Quality Assurance": 0.5,
            "Integration & Test Lead": 0.2,
        },
        "Fabrication": {
            "Project Manager": 0.5, "Systems Engineer": 0.5, "Mechanical Engineer": 1.0,
            "Electrical/Power Engineer": 1.0, "RF/Comms Engineer": 0.5, "Software Engineer": 1.0,
            "Payload Specialist": 0.3, "Regulatory Specialist": 0.1, "Quality Assurance": 0.8,
            "Integration & Test Lead": 0.3,
        },
        "Integration": {
            "Project Manager": 0.5, "Systems Engineer": 1.0, "Mechanical Engineer": 0.8,
            "Electrical/Power Engineer": 1.0, "RF/Comms Engineer": 0.8, "Software Engineer": 1.0,
            "Payload Specialist": 0.3, "Regulatory Specialist": 0.0, "Quality Assurance": 1.0,
            "Integration & Test Lead": 1.0,
        },
        "Environmental Testing": {
            "Project Manager": 0.3, "Systems Engineer": 0.5, "Mechanical Engineer": 0.8,
            "Electrical/Power Engineer": 0.8, "RF/Comms Engineer": 0.5, "Software Engineer": 0.3,
            "Payload Specialist": 0.2, "Regulatory Specialist": 0.0, "Quality Assurance": 1.0,
            "Integration & Test Lead": 1.0,
        },
        "Regulatory": {
            "Project Manager": 0.3, "Systems Engineer": 0.2, "Mechanical Engineer": 0.0,
            "Electrical/Power Engineer": 0.0, "RF/Comms Engineer": 0.5, "Software Engineer": 0.0,
            "Payload Specialist": 0.0, "Regulatory Specialist": 1.0, "Quality Assurance": 0.0,
            "Integration & Test Lead": 0.0,
        },
        "IARU/ITU": {
            "Project Manager": 0.1, "Systems Engineer": 0.1, "Mechanical Engineer": 0.0,
            "Electrical/Power Engineer": 0.0, "RF/Comms Engineer": 0.3, "Software Engineer": 0.0,
            "Payload Specialist": 0.0, "Regulatory Specialist": 0.8, "Quality Assurance": 0.0,
            "Integration & Test Lead": 0.0,
        },
        "Launch Procurement": {
            "Project Manager": 0.5, "Systems Engineer": 0.5, "Mechanical Engineer": 0.2,
            "Electrical/Power Engineer": 0.1, "RF/Comms Engineer": 0.0, "Software Engineer": 0.0,
            "Payload Specialist": 0.0, "Regulatory Specialist": 0.2, "Quality Assurance": 0.1,
            "Integration & Test Lead": 0.1,
        },
        "Range Safety": {
            "Project Manager": 0.2, "Systems Engineer": 0.5, "Mechanical Engineer": 0.1,
            "Electrical/Power Engineer": 0.1, "RF/Comms Engineer": 0.0, "Software Engineer": 0.0,
            "Payload Specialist": 0.0, "Regulatory Specialist": 0.3, "Quality Assurance": 0.5,
            "Integration & Test Lead": 0.0,
        },
        "Pre-Ship": {
            "Project Manager": 0.5, "Systems Engineer": 0.8, "Mechanical Engineer": 0.3,
            "Electrical/Power Engineer": 0.3, "RF/Comms Engineer": 0.2, "Software Engineer": 0.2,
            "Payload Specialist": 0.1, "Regulatory Specialist": 0.1, "Quality Assurance": 1.0,
            "Integration & Test Lead": 1.0,
        },
        "Launch Campaign": {
            "Project Manager": 1.0, "Systems Engineer": 1.0, "Mechanical Engineer": 0.5,
            "Electrical/Power Engineer": 0.8, "RF/Comms Engineer": 1.0, "Software Engineer": 0.8,
            "Payload Specialist": 0.3, "Regulatory Specialist": 0.1, "Quality Assurance": 0.5,
            "Integration & Test Lead": 1.0,
        },
        "Operations": {
            "Project Manager": 0.3, "Systems Engineer": 0.8, "Mechanical Engineer": 0.1,
            "Electrical/Power Engineer": 0.3, "RF/Comms Engineer": 0.5, "Software Engineer": 0.5,
            "Payload Specialist": 0.8, "Regulatory Specialist": 0.0, "Quality Assurance": 0.1,
            "Integration & Test Lead": 0.1,
        },
    }

    # Build month-to-phase mapping
    month_phases = {m: [] for m in months}
    for phase_data in phases:
        phase_name = _normalize_phase_name(phase_data.get("name", ""))
        phase_start = _parse_date(phase_data.get("start", datetime.now()))
        phase_end = _parse_date(phase_data.get("end", datetime.now() + timedelta(days=90)))
        phase_months = _months_between(phase_start, phase_end)
        for m in phase_months:
            if m in month_phases:
                month_phases[m].append(phase_name)

    # Generate staffing for each month
    staffing_profile = []
    complexity = _get_complexity(timeline)

    for month in months:
        active_phases = month_phases.get(month, [])
        month_roles = {}

        for role in STANDARD_ROLES:
            total_fte = 0.0
            for phase in active_phases:
                base = phase_staffing.get(phase, {}).get(role, 0.0)
                total_fte += base

            # Scale by complexity and team multiplier
            total_fte = total_fte * complexity * staffing_multiplier

            # Cap at reasonable levels based on team size
            max_for_role = team_size * 0.3  # No single role exceeds 30% of team
            total_fte = min(total_fte, max_for_role)

            # Round to nearest 0.25
            total_fte = round(total_fte * 4) / 4

            if total_fte > 0:
                month_roles[role] = total_fte

        if month_roles:
            staffing_profile.append({
                "month": month,
                "roles": month_roles,
                "total_fte": sum(month_roles.values()),
            })

    return staffing_profile


def _generate_budget(timeline: dict, team_config: dict, staffing_profile: list) -> list:
    """Generate rough order of magnitude budget breakdown."""
    experience = team_config.get("experience_level", "experienced_industry")
    budget_tier = team_config.get("budget_tier", "moderate")
    complexity = _get_complexity(timeline)
    mass_kg = timeline.get("mass_kg", 10)

    budget_mult = BUDGET_MULTIPLIERS.get(budget_tier, 1.0)
    launch_cost = _get_launch_cost(timeline)

    # Base salary rates by experience level (annual per FTE)
    salary_rates = {
        "university": 30_000,       # Stipends/part-time
        "startup": 120_000,
        "experienced_industry": 180_000,
        "government_prime": 220_000,
    }
    annual_rate = salary_rates.get(experience, 150_000)

    # Calculate total person-months from staffing profile
    total_fte_months = sum(s.get("total_fte", 0) for s in staffing_profile)
    personnel_cost = total_fte_months * (annual_rate / 12)

    # Add overhead/burden for industry and government
    if experience == "experienced_industry":
        personnel_cost *= 1.5  # Overhead
    elif experience == "government_prime":
        personnel_cost *= 2.2  # Full wrap rate

    # Hardware costs based on satellite class and mass
    if mass_kg <= 5:
        hardware_base = 100_000
    elif mass_kg <= 50:
        hardware_base = 500_000
    elif mass_kg <= 300:
        hardware_base = 3_000_000
    elif mass_kg <= 1000:
        hardware_base = 20_000_000
    else:
        hardware_base = 100_000_000

    hardware_cost = hardware_base * complexity * budget_mult

    # Ground segment costs
    if mass_kg <= 50:
        ground_cost = 50_000 * budget_mult
    elif mass_kg <= 300:
        ground_cost = 500_000 * budget_mult
    else:
        ground_cost = 3_000_000 * budget_mult

    # Regulatory/legal costs
    if experience == "university":
        regulatory_cost = 10_000
    elif experience == "government_prime":
        regulatory_cost = 200_000
    else:
        regulatory_cost = 50_000 * budget_mult

    # Testing costs (facility fees)
    if mass_kg <= 5:
        testing_cost = 30_000
    elif mass_kg <= 50:
        testing_cost = 150_000
    elif mass_kg <= 300:
        testing_cost = 800_000
    else:
        testing_cost = 3_000_000

    testing_cost *= budget_mult

    # Travel/logistics
    total_months = len(staffing_profile)
    if experience == "university":
        travel_cost = 5_000 * (total_months / 12)
    elif experience == "government_prime":
        travel_cost = 200_000 * (total_months / 12)
    else:
        travel_cost = 50_000 * (total_months / 12)

    # Management reserve (percentage of subtotal)
    subtotal = personnel_cost + hardware_cost + launch_cost + ground_cost + regulatory_cost + testing_cost + travel_cost
    if experience == "government_prime":
        reserve_pct = 0.25
    elif experience == "university":
        reserve_pct = 0.10
    else:
        reserve_pct = 0.20

    reserve_cost = subtotal * reserve_pct

    budget = [
        {
            "category": "Personnel",
            "estimate_usd": round(personnel_cost),
            "notes": f"Based on {total_fte_months:.0f} FTE-months at ${annual_rate:,.0f}/yr"
                     + (f" with overhead/burden" if experience in ("experienced_industry", "government_prime") else ""),
        },
        {
            "category": "Hardware/Components",
            "estimate_usd": round(hardware_cost),
            "notes": f"Satellite hardware for {mass_kg} kg {timeline.get('satellite_class', 'satellite')}",
        },
        {
            "category": "Launch Services",
            "estimate_usd": round(launch_cost),
            "notes": "Launch vehicle and integration services"
                     + (f" ({timeline['launch_vehicles'][0].get('name', '')})" if timeline.get("launch_vehicles") and isinstance(timeline["launch_vehicles"][0], dict) else ""),
        },
        {
            "category": "Ground Segment",
            "estimate_usd": round(ground_cost),
            "notes": "Ground station development/access, mission operations center",
        },
        {
            "category": "Regulatory/Legal",
            "estimate_usd": round(regulatory_cost),
            "notes": "FCC licensing, IARU coordination, legal counsel"
                     + (", ITAR compliance" if timeline.get("needs_export_control") else ""),
        },
        {
            "category": "Testing",
            "estimate_usd": round(testing_cost),
            "notes": "Environmental test facility fees (TVAC, vibration, EMI/EMC)",
        },
        {
            "category": "Travel/Logistics",
            "estimate_usd": round(travel_cost),
            "notes": "Launch campaign travel, vendor visits, shipping",
        },
        {
            "category": "Reserves",
            "estimate_usd": round(reserve_cost),
            "notes": f"Management reserve ({int(reserve_pct * 100)}% of subtotal)",
        },
    ]

    # Add total
    total = sum(item["estimate_usd"] for item in budget)
    budget.append({
        "category": "TOTAL",
        "estimate_usd": total,
        "notes": "Rough order of magnitude; actual costs may vary significantly",
    })

    return budget


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def generate_project_plan(mission: dict, timeline: dict, team_config: dict) -> dict:
    """
    Generate a comprehensive project plan from mission parameters, timeline,
    and team configuration.

    Parameters
    ----------
    mission : dict
        Mission parameters (name, objectives, orbit, payload, etc.)
    timeline : dict
        Timeline output from timeline_generator.py containing:
        - phases: list of {name, start, end, duration_nom, ...}
        - launch_vehicles: list of vehicle options
        - critical_path_months: float
        - available_months: float
        - target_launch_date: str
        - estimated_completion: str
        - probability_pct: int
        - probability_reasons: list
        - is_experimental: bool
        - needs_export_control: bool
        - satellite_class: str
        - mass_kg: float
    team_config : dict
        Team configuration:
        - team_size: int
        - experience_level: str ("university", "startup", "experienced_industry", "government_prime")
        - budget_tier: str ("shoestring", "moderate", "well_funded")

    Returns
    -------
    dict
        Comprehensive project plan containing:
        - wbs: Work Breakdown Structure (by_phase dict and all_work_packages list)
        - milestones: List of key review gates with dates
        - raci: RACI matrix by phase with role assignments
        - meeting_cadence: Recommended meeting schedule
        - dependencies: Critical path dependencies between work packages
        - risks: Risk watch items by phase
        - staffing_profile: Month-by-month FTE estimates by discipline
        - budget: Rough order of magnitude budget breakdown
        - metadata: Summary information about the plan
    """
    # Validate inputs
    if not timeline.get("phases"):
        raise ValueError("Timeline must contain at least one phase")

    team_size = team_config.get("team_size", 5)
    experience = team_config.get("experience_level", "experienced_industry")
    budget_tier = team_config.get("budget_tier", "moderate")

    # Generate all plan components
    wbs = _generate_wbs(timeline, team_config)
    milestones = _generate_milestones(timeline, wbs)
    raci = _generate_raci(timeline, team_config)
    meeting_cadence = _generate_meeting_cadence(team_config)
    dependencies = _generate_dependencies(wbs)
    risks = _generate_risks(timeline, team_config)
    staffing_profile = _generate_staffing_profile(timeline, team_config, wbs)
    budget = _generate_budget(timeline, team_config, staffing_profile)

    # Compute metadata/summary
    all_wps = wbs.get("all_work_packages", [])
    total_work_packages = len(all_wps)
    total_milestones_in_wbs = sum(1 for wp in all_wps if wp.get("is_milestone"))
    total_dependencies = len(dependencies)
    total_risks = sum(len(r) for r in risks.values())

    phases_covered = list(wbs.get("by_phase", {}).keys())

    # Calculate total budget
    total_budget = next((item["estimate_usd"] for item in budget if item["category"] == "TOTAL"), 0)

    # Peak staffing
    peak_fte = max((s.get("total_fte", 0) for s in staffing_profile), default=0)
    peak_month = ""
    for s in staffing_profile:
        if s.get("total_fte", 0) == peak_fte:
            peak_month = s.get("month", "")
            break

    metadata = {
        "mission_name": mission.get("mission_name") or mission.get("name", "Unnamed Mission"),
        "satellite_class": timeline.get("satellite_class", "unknown"),
        "mass_kg": timeline.get("mass_kg", 0),
        "target_launch_date": timeline.get("target_launch_date", "TBD"),
        "estimated_completion": timeline.get("estimated_completion", "TBD"),
        "probability_pct": timeline.get("probability_pct", 0),
        "team_size": team_size,
        "experience_level": experience,
        "budget_tier": budget_tier,
        "total_work_packages": total_work_packages,
        "total_milestones": len(milestones),
        "total_dependencies": total_dependencies,
        "total_risks": total_risks,
        "phases_covered": phases_covered,
        "total_budget_usd": total_budget,
        "peak_staffing_fte": peak_fte,
        "peak_staffing_month": peak_month,
        "is_experimental": timeline.get("is_experimental", False),
        "needs_export_control": timeline.get("needs_export_control", False),
    }

    return {
        "wbs": wbs,
        "milestones": milestones,
        "raci": raci,
        "meeting_cadence": meeting_cadence,
        "dependencies": dependencies,
        "risks": risks,
        "staffing_profile": staffing_profile,
        "budget": budget,
        "team_config": {
            "team_size": team_size,
            "experience_level": experience,
            "budget_tier": budget_tier,
        },
        "metadata": metadata,
    }
