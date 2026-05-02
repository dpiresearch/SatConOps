"""
Satellite ConOps Generator — Web Application
Generates FCC-compliant Concept of Operations documents for all satellite types.
"""

import os
import uuid
from datetime import datetime
from flask import (Flask, render_template, request, send_file, jsonify,
                   after_this_request)

from conops_pdf import generate_conops_pdf
from timeline_generator import generate_timeline
from timeline_pdf import generate_timeline_pdf

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
}


@app.route("/")
def index():
    return render_template("index.html", mission=DEFAULT_MISSION)


@app.route("/generate", methods=["POST"])
def generate():
    mission = {}
    for key in DEFAULT_MISSION:
        mission[key] = request.form.get(key, DEFAULT_MISSION[key])

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

    filename = f"ConOps_{mission['mission_name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = os.path.join(OUTPUT_DIR, filename)

    generate_conops_pdf(mission, output_path)

    response = send_file(output_path, as_attachment=True, download_name=filename)
    response.headers["X-Download-Complete"] = "true"
    return response


@app.route("/timeline", methods=["POST"])
def timeline():
    mission = {}
    for key in DEFAULT_MISSION:
        mission[key] = request.form.get(key, DEFAULT_MISSION[key])

    timeline_data = generate_timeline(mission)

    filename = f"Timeline_{mission['mission_name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = os.path.join(OUTPUT_DIR, filename)

    generate_timeline_pdf(mission, timeline_data, output_path)

    response = send_file(output_path, as_attachment=True, download_name=filename)
    response.headers["X-Download-Complete"] = "true"
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5002)
