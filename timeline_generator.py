"""
Mission project timeline generator.
Produces a comprehensive phased timeline from concept through launch,
calculates probability of on-time completion, and identifies risk factors.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from launch_vehicles import find_compatible_vehicles


# ── Phase duration tables (months) by satellite class ──
# Each tuple: (optimistic, nominal, pessimistic)

BASE_PHASES = {
    "CubeSat": [
        ("Concept Development & Feasibility",           (1, 2, 4)),
        ("Preliminary Design & PDR",                    (2, 3, 5)),
        ("Detailed Design & CDR",                       (2, 4, 6)),
        ("Component Procurement",                       (2, 3, 6)),
        ("Fabrication & Assembly",                      (2, 3, 5)),
        ("Integration & Functional Testing",            (1, 2, 3)),
        ("Environmental Testing (TVAC, Vibe, EMI)",     (1, 2, 3)),
        ("FCC / Regulatory Filing & Approval",          (3, 6, 12)),
        ("IARU Frequency Coordination",                 (2, 4, 8)),
        ("Launch Vehicle Procurement & Contracting",    (2, 4, 8)),
        ("Pre-Ship Review & Shipping",                  (0.5, 1, 2)),
        ("Launch Campaign & Integration",               (0.5, 1, 2)),
    ],
    "Microsatellite": [
        ("Concept Development & Feasibility",           (2, 3, 5)),
        ("Preliminary Design & PDR",                    (3, 5, 8)),
        ("Detailed Design & CDR",                       (3, 5, 8)),
        ("Component Procurement",                       (3, 5, 9)),
        ("Fabrication & Assembly",                      (3, 5, 8)),
        ("Integration & Functional Testing",            (2, 3, 5)),
        ("Environmental Testing (TVAC, Vibe, EMI)",     (2, 3, 5)),
        ("FCC / Regulatory Filing & Approval",          (4, 8, 14)),
        ("IARU Frequency Coordination",                 (2, 4, 8)),
        ("Launch Vehicle Procurement & Contracting",    (3, 6, 10)),
        ("Pre-Ship Review & Shipping",                  (0.5, 1, 2)),
        ("Launch Campaign & Integration",               (1, 2, 3)),
    ],
    "Small Satellite": [
        ("Concept Development & Feasibility",           (2, 4, 6)),
        ("Preliminary Design & PDR",                    (4, 6, 10)),
        ("Detailed Design & CDR",                       (4, 6, 10)),
        ("Component Procurement",                       (4, 6, 12)),
        ("Fabrication & Assembly",                      (4, 6, 10)),
        ("Integration & Functional Testing",            (2, 4, 6)),
        ("Environmental Testing (TVAC, Vibe, EMI)",     (2, 4, 6)),
        ("FCC / Regulatory Filing & Approval",          (6, 10, 18)),
        ("IARU Frequency Coordination",                 (3, 6, 10)),
        ("Launch Vehicle Procurement & Contracting",    (4, 8, 14)),
        ("Pre-Ship Review & Shipping",                  (1, 1.5, 3)),
        ("Launch Campaign & Integration",               (1, 2, 3)),
    ],
    "Medium Satellite": [
        ("Concept Development & Feasibility",           (3, 5, 8)),
        ("Preliminary Design & PDR",                    (5, 8, 12)),
        ("Detailed Design & CDR",                       (6, 9, 14)),
        ("Component Procurement",                       (6, 9, 15)),
        ("Fabrication & Assembly",                      (6, 9, 14)),
        ("Integration & Functional Testing",            (3, 5, 8)),
        ("Environmental Testing (TVAC, Vibe, EMI)",     (3, 5, 8)),
        ("FCC / Regulatory Filing & Approval",          (8, 12, 20)),
        ("IARU / ITU Frequency Coordination",           (4, 8, 14)),
        ("Launch Vehicle Procurement & Contracting",    (6, 12, 18)),
        ("Pre-Ship Review & Shipping",                  (1, 2, 3)),
        ("Launch Campaign & Integration",               (1, 2, 4)),
    ],
    "Large Satellite": [
        ("Concept Development & Feasibility",           (4, 6, 10)),
        ("Preliminary Design & PDR",                    (6, 10, 16)),
        ("Detailed Design & CDR",                       (8, 12, 18)),
        ("Component Procurement",                       (8, 12, 18)),
        ("Fabrication & Assembly",                      (10, 14, 20)),
        ("Integration & Functional Testing",            (4, 6, 10)),
        ("Environmental Testing (TVAC, Vibe, EMI)",     (4, 6, 10)),
        ("FCC / Regulatory Filing & Approval",          (10, 14, 24)),
        ("ITU Frequency Coordination & Filing",         (6, 12, 18)),
        ("Launch Vehicle Procurement & Contracting",    (8, 14, 24)),
        ("Pre-Ship Review & Shipping",                  (1, 2, 3)),
        ("Launch Campaign & Integration",               (2, 3, 5)),
    ],
    "GEO Communications": [
        ("Concept Development & Feasibility",           (4, 6, 10)),
        ("Preliminary Design & PDR",                    (6, 10, 16)),
        ("Detailed Design & CDR",                       (8, 14, 20)),
        ("Component Procurement",                       (8, 14, 20)),
        ("Fabrication & Assembly",                      (10, 16, 24)),
        ("Integration & Functional Testing",            (4, 8, 12)),
        ("Environmental Testing (TVAC, Vibe, EMI)",     (4, 6, 10)),
        ("FCC / Regulatory Filing & Approval",          (10, 16, 24)),
        ("ITU Frequency Coordination & Filing",         (8, 14, 24)),
        ("Orbital Slot Coordination (ITU BR)",          (6, 12, 24)),
        ("Launch Vehicle Procurement & Contracting",    (10, 18, 30)),
        ("Pre-Ship Review & Shipping",                  (1, 2, 4)),
        ("Launch Campaign & Integration",               (2, 3, 5)),
    ],
    "Science / Exploration": [
        ("Concept Development & Feasibility",           (6, 10, 18)),
        ("Technology Readiness Maturation",              (6, 12, 24)),
        ("Preliminary Design & PDR",                    (6, 10, 16)),
        ("Detailed Design & CDR",                       (8, 14, 20)),
        ("Component Procurement",                       (8, 12, 18)),
        ("Fabrication & Assembly",                      (10, 16, 24)),
        ("Integration & Functional Testing",            (4, 8, 12)),
        ("Environmental & Qualification Testing",       (4, 8, 12)),
        ("FCC / Regulatory Filing & Approval",          (8, 12, 20)),
        ("IARU / ITU Frequency Coordination",           (4, 8, 14)),
        ("Launch Vehicle Procurement & Contracting",    (8, 14, 24)),
        ("Pre-Ship Review & Shipping",                  (1, 2, 4)),
        ("Launch Campaign & Integration",               (2, 4, 6)),
    ],
}

# Additional phases for experimental/complex payloads
EXPERIMENTAL_PHASES = [
    ("Experimental Payload Qualification",              (3, 6, 12)),
    ("Radiation Testing & Hardening Verification",      (2, 4, 8)),
    ("Extended Life Testing",                           (2, 4, 8)),
]

EXPORT_CONTROL_PHASE = [
    ("ITAR / Export Control Review",                    (2, 4, 8)),
]

RANGE_SAFETY_PHASE = [
    ("Range Safety Review & Approval",                  (2, 3, 6)),
]

# Which phases can overlap (parallel tracks)
PARALLEL_GROUPS = {
    "design": [
        "Concept Development & Feasibility",
        "Technology Readiness Maturation",
    ],
    "build": [
        "Component Procurement",
        "Fabrication & Assembly",
    ],
    "regulatory": [
        "FCC / Regulatory Filing & Approval",
        "IARU Frequency Coordination",
        "IARU / ITU Frequency Coordination",
        "ITU Frequency Coordination & Filing",
        "Orbital Slot Coordination (ITU BR)",
        "ITAR / Export Control Review",
    ],
    "test": [
        "Environmental Testing (TVAC, Vibe, EMI)",
        "Environmental & Qualification Testing",
        "Experimental Payload Qualification",
        "Radiation Testing & Hardening Verification",
        "Extended Life Testing",
    ],
    "launch_prep": [
        "Launch Vehicle Procurement & Contracting",
    ],
}


def _parse_launch_date(date_str: str) -> datetime:
    """Parse various date formats into a datetime."""
    date_str = date_str.strip()
    for fmt in (
        "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m",
        "%b %Y", "%B %Y", "%b %d %Y", "%B %d %Y",
        "%d %b %Y", "%d %B %Y",
    ):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    # Handle "2027-Q3" style
    if "-Q" in date_str.upper():
        parts = date_str.upper().split("-Q")
        year = int(parts[0])
        quarter = int(parts[1])
        month = {1: 2, 2: 5, 3: 8, 4: 11}[quarter]
        return datetime(year, month, 15)
    # Handle "Q3 2027"
    if date_str.upper().startswith("Q"):
        parts = date_str.upper().replace("Q", "").split()
        quarter = int(parts[0])
        year = int(parts[1])
        month = {1: 2, 2: 5, 3: 8, 4: 11}[quarter]
        return datetime(year, month, 15)
    # Handle just a year
    if date_str.isdigit() and len(date_str) == 4:
        return datetime(int(date_str), 6, 15)
    raise ValueError(f"Cannot parse date: {date_str}")


def _months_between(d1: datetime, d2: datetime) -> float:
    return (d2 - d1).days / 30.44


def _is_experimental(mission: Dict) -> bool:
    payload_type = mission.get("payload_type", "").lower()
    payload_desc = mission.get("payload_description", "").lower()
    payload_purpose = mission.get("payload_purpose", "").lower()
    combined = payload_type + " " + payload_desc + " " + payload_purpose
    experimental_keywords = [
        "experimental", "prototype", "demonstration", "novel",
        "first-of-kind", "technology readiness", "trl", "new design",
        "unproven", "research", "developmental", "pathfinder",
    ]
    return any(kw in combined for kw in experimental_keywords)


def _needs_export_control(mission: Dict) -> bool:
    payload_type = mission.get("payload_type", "").lower()
    payload_desc = mission.get("payload_description", "").lower()
    combined = payload_type + " " + payload_desc
    itar_keywords = [
        "sar", "radar", "imaging", "national security", "defense",
        "military", "classified", "itar", "dual-use", "infrared",
        "hyperspectral", "sigint", "elint", "reconnaissance",
    ]
    return any(kw in combined for kw in itar_keywords)


def _safe_float(val, default):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def generate_timeline(mission: Dict) -> Dict:
    """
    Generate a comprehensive mission timeline.

    Returns dict with:
      - phases: list of phase dicts with dates and durations
      - launch_vehicles: compatible vehicles
      - total_months_needed: nominal total months (serial path)
      - available_months: months from now to target launch
      - probability_pct: probability of on-time completion
      - probability_reasons: list of (factor, impact, explanation)
      - gantt_data: data for rendering a Gantt chart
      - critical_path_months: months on the critical path (with parallelism)
    """
    sat_class = mission.get("satellite_class", "Small Satellite")
    mass_kg = _safe_float(mission.get("spacecraft_mass"), 100)
    orbit_type = mission.get("orbit_type", "LEO")

    # Get base phases for this satellite class
    if sat_class in BASE_PHASES:
        phases_template = list(BASE_PHASES[sat_class])
    else:
        phases_template = list(BASE_PHASES["Small Satellite"])

    # Add experimental phases if needed
    is_exp = _is_experimental(mission)
    if is_exp:
        insert_idx = None
        for i, (name, _) in enumerate(phases_template):
            if "Environmental" in name:
                insert_idx = i + 1
                break
        if insert_idx is None:
            insert_idx = len(phases_template) - 2
        for ep in reversed(EXPERIMENTAL_PHASES):
            phases_template.insert(insert_idx, ep)

    # Add export control if needed
    if _needs_export_control(mission):
        reg_idx = None
        for i, (name, _) in enumerate(phases_template):
            if "FCC" in name:
                reg_idx = i
                break
        if reg_idx is not None:
            phases_template.insert(reg_idx, EXPORT_CONTROL_PHASE[0])

    # Add range safety
    launch_idx = None
    for i, (name, _) in enumerate(phases_template):
        if "Launch Campaign" in name:
            launch_idx = i
            break
    if launch_idx is not None:
        phases_template.insert(launch_idx, RANGE_SAFETY_PHASE[0])

    # Find compatible launch vehicles
    orbit_key = orbit_type.split("(")[-1].replace(")", "").strip() if "(" in orbit_type else orbit_type
    for abbrev in ["SSO", "LEO", "GEO", "MEO", "HEO", "Polar"]:
        if abbrev.lower() in orbit_type.lower():
            orbit_key = abbrev
            break
    vehicles = find_compatible_vehicles(mass_kg, orbit_key, sat_class)

    # Parse target launch date
    launch_date_str = mission.get("target_launch_date", "").strip()
    now = datetime.now()
    if launch_date_str:
        try:
            target_launch = _parse_launch_date(launch_date_str)
        except ValueError:
            target_launch = now + timedelta(days=3 * 365)
    else:
        target_launch = now + timedelta(days=3 * 365)

    available_months = _months_between(now, target_launch)

    # Build phase schedule working BACKWARDS from launch date
    # First, compute serial nominal total
    serial_nominal = sum(dur[1] for _, dur in phases_template)

    # Build schedule with parallelism
    # Group phases into sequential blocks with parallel sub-tracks
    phase_list = []
    current_date = now

    # Identify which parallel group each phase belongs to
    def _get_group(phase_name):
        for grp, members in PARALLEL_GROUPS.items():
            for m in members:
                if m in phase_name:
                    return grp
        return None

    # Build sequential blocks: phases in the same parallel group run concurrently
    blocks = []
    current_block = []
    current_group = None

    for name, durations in phases_template:
        grp = _get_group(name)
        if grp is not None and grp == current_group:
            current_block.append((name, durations))
        else:
            if current_block:
                blocks.append(current_block)
            current_block = [(name, durations)]
            current_group = grp

    if current_block:
        blocks.append(current_block)

    # Schedule each block
    critical_path_months = 0
    gantt_data = []

    for block in blocks:
        block_duration = max(dur[1] for _, dur in block)
        critical_path_months += block_duration
        for name, (opt, nom, pess) in block:
            start = current_date
            end = current_date + timedelta(days=nom * 30.44)
            phase_list.append({
                "name": name,
                "duration_opt": opt,
                "duration_nom": nom,
                "duration_pess": pess,
                "start": start,
                "end": end,
            })
            gantt_data.append({
                "name": name,
                "start_month": _months_between(now, start),
                "duration": nom,
                "opt": opt,
                "pess": pess,
            })
        current_date = current_date + timedelta(days=block_duration * 30.44)

    estimated_completion = current_date

    # ── Probability calculation ──
    # Uses a weighted scoring system across multiple risk dimensions

    probability_reasons = []
    score = 80.0  # start at 80% baseline

    # 1. Schedule margin
    margin_months = available_months - critical_path_months
    margin_ratio = margin_months / max(critical_path_months, 1)
    if margin_ratio >= 0.3:
        adj = +8
        explanation = f"{margin_months:.0f} months of margin ({margin_ratio:.0%} buffer) — comfortable schedule"
    elif margin_ratio >= 0.15:
        adj = +4
        explanation = f"{margin_months:.0f} months of margin ({margin_ratio:.0%} buffer) — adequate but tight"
    elif margin_ratio >= 0:
        adj = -5
        explanation = f"Only {margin_months:.0f} months margin ({margin_ratio:.0%} buffer) — very tight schedule"
    elif margin_ratio >= -0.15:
        adj = -15
        explanation = f"Schedule is {abs(margin_months):.0f} months short — likely delay without acceleration"
    else:
        adj = -30
        explanation = f"Schedule is {abs(margin_months):.0f} months short — major timeline risk"
    score += adj
    probability_reasons.append(("Schedule Margin", adj, explanation))

    # 2. Satellite class complexity
    complexity_map = {
        "CubeSat": (+5, "CubeSat — well-understood class with COTS components, short timelines"),
        "Microsatellite": (+3, "Microsatellite — moderate complexity, good heritage availability"),
        "Small Satellite": (0, "Small Satellite — standard complexity"),
        "Medium Satellite": (-3, "Medium Satellite — significant engineering effort required"),
        "Large Satellite": (-5, "Large Satellite — complex integration, long lead-time items"),
        "GEO Communications": (-7, "GEO Comms — high complexity, orbital slot coordination, long lead times"),
        "Science / Exploration": (-8, "Science/Exploration — highest complexity, often first-of-kind elements"),
    }
    adj, explanation = complexity_map.get(sat_class, (0, "Standard complexity"))
    score += adj
    probability_reasons.append(("Satellite Complexity", adj, explanation))

    # 3. Experimental payload
    if is_exp:
        adj = -10
        explanation = "Experimental/novel payload — additional qualification and testing risk"
        score += adj
        probability_reasons.append(("Experimental Payload", adj, explanation))

    # 4. Launch vehicle availability
    operational_vehicles = [v for v in vehicles if v["status"] == "Operational"]
    if len(operational_vehicles) >= 5:
        adj = +5
        explanation = f"{len(operational_vehicles)} operational vehicles available — excellent launch flexibility"
    elif len(operational_vehicles) >= 3:
        adj = +2
        explanation = f"{len(operational_vehicles)} operational vehicles — good availability"
    elif len(operational_vehicles) >= 1:
        adj = -3
        explanation = f"Only {len(operational_vehicles)} operational vehicle(s) — limited launch options"
    else:
        adj = -10
        explanation = "No operational launch vehicles matched — may need custom arrangement"
    score += adj
    probability_reasons.append(("Launch Vehicle Availability", adj, explanation))

    # 5. Regulatory path complexity
    fcc_type = mission.get("fcc_license_type", "")
    if "25.122" in fcc_type:
        adj = +4
        explanation = "Streamlined Part 25.122 — faster FCC processing for qualifying small sats"
    elif "97" in fcc_type:
        adj = +2
        explanation = "Part 97 amateur — simpler but requires IARU coordination"
    elif "Part 5" in fcc_type:
        adj = +1
        explanation = "Part 5 experimental — generally faster but limited operational scope"
    else:
        adj = -2
        explanation = "Standard Part 25.114 — full FCC review process, typically 12+ months"
    score += adj
    probability_reasons.append(("Regulatory Path", adj, explanation))

    # 6. Export control
    if _needs_export_control(mission):
        adj = -5
        explanation = "Payload may require ITAR/export control review — adds time and uncertainty"
        score += adj
        probability_reasons.append(("Export Control Risk", adj, explanation))

    # 7. Mission lifetime requirement (longer missions need more qualification)
    lifetime = _safe_float(mission.get("mission_lifetime"), 2)
    if lifetime > 10:
        adj = -5
        explanation = f"{lifetime:.0f}-year lifetime requirement — extensive qualification testing needed"
    elif lifetime > 5:
        adj = -2
        explanation = f"{lifetime:.0f}-year lifetime — above-average qualification burden"
    else:
        adj = 0
        explanation = f"{lifetime:.0f}-year lifetime — standard qualification scope"
    if adj != 0:
        score += adj
        probability_reasons.append(("Mission Lifetime", adj, explanation))

    # 8. Orbit complexity
    orbit_adj = 0
    if "GEO" in orbit_type or "Geostationary" in orbit_type:
        orbit_adj = -4
        orbit_exp = "GEO orbit — requires GTO-to-GEO transfer, orbital slot coordination"
    elif "Molniya" in orbit_type or "HEO" in orbit_type:
        orbit_adj = -3
        orbit_exp = "Highly elliptical orbit — complex orbital mechanics and ground coverage planning"
    elif "MEO" in orbit_type:
        orbit_adj = -2
        orbit_exp = "MEO orbit — radiation environment and transfer orbit considerations"
    else:
        orbit_adj = 0
        orbit_exp = ""
    if orbit_adj != 0:
        score += orbit_adj
        probability_reasons.append(("Orbit Complexity", orbit_adj, orbit_exp))

    # Clamp score
    score = max(5, min(98, score))

    return {
        "phases": phase_list,
        "launch_vehicles": vehicles[:10],
        "serial_months_needed": serial_nominal,
        "critical_path_months": critical_path_months,
        "available_months": available_months,
        "target_launch_date": target_launch,
        "estimated_completion": estimated_completion,
        "probability_pct": round(score),
        "probability_reasons": probability_reasons,
        "gantt_data": gantt_data,
        "is_experimental": is_exp,
        "needs_export_control": _needs_export_control(mission),
        "satellite_class": sat_class,
        "mass_kg": mass_kg,
    }
