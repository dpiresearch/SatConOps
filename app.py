"""
Satellite Mission Planner — Web Application
Generates FCC-compliant Concept of Operations documents for all satellite types.
"""

import os
from datetime import datetime
from flask import Flask, jsonify, render_template, request, send_file

from conops_pdf import generate_conops_pdf
from timeline_generator import generate_timeline
from timeline_pdf import generate_timeline_pdf
from project_planner import generate_project_plan
from project_plan_pdf import generate_project_plan_pdf
from mission_parser import parse_mission_narrative

app = Flask(__name__)
app.secret_key = os.urandom(24)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


DEFAULT_MISSION = {
    "mission_name": "",
    "organization": "",
    "author": "",
    "version": "1.0",
    "mission_description": "",
    "objectives": "",
    "success_criteria": "",
    "satellite_class": "Small Satellite",
    "form_factor": "3U",
    "spacecraft_mass": "",
    "dimensions": "",
    "mission_lifetime": "",
    "target_launch_date": "",
    "adcs": "",
    "propulsion": "",
    "power_system": "",
    "power_generation": "",
    "battery_capacity": "",
    "battery_type": "Li-ion",
    "solar_area": "",
    "obc": "",
    "thermal": "Passive (MLI + surface coatings)",
    "payload_type": "",
    "payload_description": "",
    "payload_purpose": "",
    "orbit_altitude": "",
    "orbit_inclination": "",
    "orbit_type": "Sun-Synchronous (SSO)",
    "eccentricity": "~0 (near-circular)",
    "raan": "TBD",
    "ltan": "",
    "uplink_freq": "",
    "downlink_freq": "",
    "uplink_bw": "",
    "downlink_bw": "",
    "modulation": "GMSK",
    "data_rate": "",
    "protocol": "AX.25",
    "polarization": "RHCP",
    "eirp": "",
    "comm_system": "",
    "ground_station": "",
    "gs_location": "",
    "gs_antenna": "",
    "gs_radio": "",
    "gs_tx_power": "",
    "sc_tx_power": "",
    "gs_ant_gain": "",
    "sc_ant_gain": "",
    "passes_per_day": "4",
    "avg_pass_duration": "10",
    "daily_data_gen": "",
    "fcc_license_type": "Part 25.114 (Standard Application)",
    "launch_provider": "",
    "disposal_method": "Atmospheric reentry (uncontrolled) — natural drag",
    "team_size": "6",
    "experience_level": "experienced_industry",
    "budget_tier": "moderate",
}


REQUIRED_INTAKE_FIELDS = [
    {
        "field": "mission_name",
        "label": "Mission Name",
        "question": "What is the mission or spacecraft name?",
        "placeholder": "e.g., HarborWatch-1",
        "input_type": "text",
    },
    {
        "field": "organization",
        "label": "Organization",
        "question": "Which organization, team, or company is responsible for the mission?",
        "placeholder": "e.g., Northstar Orbital",
        "input_type": "text",
    },
    {
        "field": "spacecraft_mass",
        "label": "Spacecraft Mass",
        "question": "What is the spacecraft mass in kilograms?",
        "placeholder": "e.g., 120",
        "input_type": "number",
    },
    {
        "field": "mission_lifetime",
        "label": "Mission Lifetime",
        "question": "What is the planned mission lifetime in years?",
        "placeholder": "e.g., 3",
        "input_type": "number",
    },
    {
        "field": "target_launch_date",
        "label": "Target Launch",
        "question": "What is the target launch date or window?",
        "placeholder": "e.g., 2029-Q2 or 2029-06",
        "input_type": "text",
    },
    {
        "field": "payload_type",
        "label": "Payload Type",
        "question": "What is the primary payload or instrument?",
        "placeholder": "e.g., AIS Receiver, SAR Radar, Optical Camera",
        "input_type": "text",
    },
    {
        "field": "orbit_altitude",
        "label": "Orbit Altitude",
        "question": "What is the target orbit altitude in kilometers?",
        "placeholder": "e.g., 550",
        "input_type": "number",
    },
    {
        "field": "orbit_inclination",
        "label": "Orbit Inclination",
        "question": "What is the target orbit inclination in degrees?",
        "placeholder": "e.g., 53 or 97.6",
        "input_type": "number",
    },
]

MISSING_PLACEHOLDERS = {"", "tbd", "tbd organization", "draftsat", "unknown"}


def _collect_mission():
    return _collect_mission_from(request.form)


def _collect_mission_from(source):
    mission = {}
    for key in DEFAULT_MISSION:
        value = source.get(key, DEFAULT_MISSION[key]) if source else DEFAULT_MISSION[key]
        mission[key] = "" if value is None else str(value)
    return mission


def _populate_generated_descriptions(mission):
    if not mission.get("mission_description"):
        mission["mission_description"] = (
            f"The {mission['mission_name']} mission is a {mission['satellite_class']} "
            f"designed to operate in {mission['orbit_type']} at {mission['orbit_altitude']} km "
            f"altitude. The primary payload is a {mission['payload_type']} for "
            f"{mission.get('payload_purpose', 'technology demonstration')}. "
            f"Operated by {mission['organization']}, the mission targets a "
            f"{mission['mission_lifetime']}-year operational lifetime with full compliance to "
            f"FCC regulations under {mission['fcc_license_type']}."
        )

    if not mission.get("payload_description"):
        mission["payload_description"] = (
            f"The primary payload is a {mission['payload_type']} designed for "
            f"{mission.get('payload_purpose', 'technology demonstration')}. "
            f"Data is stored onboard and downlinked during scheduled ground station passes "
            f"at {mission['data_rate']} bps."
        )


def _safe_team_size(value, default=6):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _is_missing(value):
    return str(value or "").strip().lower() in MISSING_PLACEHOLDERS


def _mission_intake_status(mission):
    missing = []
    for item in REQUIRED_INTAKE_FIELDS:
        if _is_missing(mission.get(item["field"])):
            missing.append(item)
    return {
        "complete": not missing,
        "missing": missing,
        "next_question": missing[0] if missing else None,
    }


def _pdf_filename(prefix, mission):
    name = mission.get("mission_name", "").strip() or "Mission"
    safe_name = name.replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{safe_name}_{timestamp}.pdf"


def _team_config_from_mission(mission):
    return {
        "team_size": _safe_team_size(mission.get("team_size")),
        "experience_level": mission.get("experience_level", "experienced_industry"),
        "budget_tier": mission.get("budget_tier", "moderate"),
    }


def _json_safe(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _flatten_risks(risks_by_phase):
    risks = []
    for phase, phase_risks in (risks_by_phase or {}).items():
        for idx, risk in enumerate(phase_risks or [], 1):
            risks.append({
                "id": f"R-{len(risks) + 1:03d}",
                "phase": phase,
                "status": "Open",
                **risk,
            })
    return risks


def _planner_payload(mission):
    _populate_generated_descriptions(mission)
    timeline_data = generate_timeline(mission)
    team_config = _team_config_from_mission(mission)
    plan_data = generate_project_plan(mission, timeline_data, team_config)

    tasks = []
    for wp in plan_data.get("wbs", {}).get("all_work_packages", []):
        required_roles = wp.get("required_roles", [])
        tasks.append({
            **wp,
            "owner": required_roles[0] if required_roles else "Project Manager",
            "status": "Not Started",
            "priority": "Normal",
            "progress": 0,
            "notes": "",
        })

    milestones = []
    for item in plan_data.get("milestones", []):
        milestones.append({
            "status": "Pending",
            **item,
        })

    metadata = plan_data.get("metadata", {})
    workspace = {
        "mission": mission,
        "timeline": timeline_data,
        "plan": {
            "tasks": tasks,
            "milestones": milestones,
            "raci": plan_data.get("raci", {}),
            "meetings": plan_data.get("meeting_cadence", []),
            "dependencies": plan_data.get("dependencies", []),
            "risks": _flatten_risks(plan_data.get("risks", {})),
            "staffing_profile": plan_data.get("staffing_profile", []),
            "budget": plan_data.get("budget", []),
            "team_config": plan_data.get("team_config", team_config),
            "metadata": metadata,
        },
    }
    return _json_safe(workspace)


def _pdf_plan_from_workspace(workspace):
    plan = workspace.get("plan", {})
    return {
        "wbs": plan.get("tasks", []),
        "milestones": plan.get("milestones", []),
        "raci": plan.get("raci", {}),
        "meeting_cadence": plan.get("meetings", []),
        "dependencies": plan.get("dependencies", []),
        "risks": plan.get("risks", []),
        "staffing_profile": plan.get("staffing_profile", []),
        "budget": plan.get("budget", []),
        "team_config": plan.get("team_config", {}),
        "metadata": plan.get("metadata", {}),
    }


@app.route("/")
def index():
    return render_template("index.html", mission=DEFAULT_MISSION)


@app.route("/planner")
def planner():
    return render_template("planner.html", mission=DEFAULT_MISSION)


@app.route("/generate", methods=["POST"])
def generate():
    mission = _collect_mission()
    _populate_generated_descriptions(mission)

    filename = _pdf_filename("ConOps", mission)
    output_path = os.path.join(OUTPUT_DIR, filename)

    generate_conops_pdf(mission, output_path)

    response = send_file(output_path, as_attachment=True, download_name=filename)
    response.headers["X-Download-Complete"] = "true"
    return response


@app.route("/timeline", methods=["POST"])
def timeline():
    mission = _collect_mission()

    timeline_data = generate_timeline(mission)

    filename = _pdf_filename("Timeline", mission)
    output_path = os.path.join(OUTPUT_DIR, filename)

    generate_timeline_pdf(mission, timeline_data, output_path)

    response = send_file(output_path, as_attachment=True, download_name=filename)
    response.headers["X-Download-Complete"] = "true"
    return response


@app.route("/project_plan", methods=["POST"])
def project_plan():
    mission = _collect_mission()
    _populate_generated_descriptions(mission)

    timeline_data = generate_timeline(mission)
    team_config = _team_config_from_mission(mission)
    plan_data = generate_project_plan(mission, timeline_data, team_config)

    filename = _pdf_filename("ProjectPlan", mission)
    output_path = os.path.join(OUTPUT_DIR, filename)

    generate_project_plan_pdf(mission, timeline_data, plan_data, output_path)

    response = send_file(output_path, as_attachment=True, download_name=filename)
    response.headers["X-Download-Complete"] = "true"
    return response


@app.route("/api/project_plan", methods=["POST"])
def api_project_plan():
    payload = request.get_json(silent=True) or {}
    mission_source = payload.get("mission", payload)
    mission = _collect_mission_from(mission_source)
    return jsonify(_planner_payload(mission))


@app.route("/api/parse_mission", methods=["POST"])
def api_parse_mission():
    payload = request.get_json(silent=True) or {}
    narrative = payload.get("narrative", "")
    current = _collect_mission_from(payload.get("current", {}))
    parsed = parse_mission_narrative(narrative, current)
    parsed["intake"] = _mission_intake_status(parsed["mission"])
    return jsonify(parsed)


@app.route("/api/mission_intake_status", methods=["POST"])
def api_mission_intake_status():
    payload = request.get_json(silent=True) or {}
    mission = _collect_mission_from(payload.get("mission", payload))
    return jsonify(_mission_intake_status(mission))


@app.route("/api/project_plan_pdf", methods=["POST"])
def api_project_plan_pdf():
    workspace = request.get_json(silent=True) or {}
    mission = _collect_mission_from(workspace.get("mission", {}))
    timeline_data = workspace.get("timeline") or generate_timeline(mission)
    plan_data = _pdf_plan_from_workspace(workspace)

    filename = _pdf_filename("ProjectPlan", mission)
    output_path = os.path.join(OUTPUT_DIR, filename)

    generate_project_plan_pdf(mission, timeline_data, plan_data, output_path)

    response = send_file(output_path, as_attachment=True, download_name=filename)
    response.headers["X-Download-Complete"] = "true"
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5002)
