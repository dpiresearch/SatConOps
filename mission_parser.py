"""
Mission narrative parser for SatConOps.

This module extracts a useful first-pass mission configuration from plain
English. It is intentionally deterministic and dependency-free: the user can
review and edit every inferred field before generating documents or a planner
workspace.
"""

import re


SATELLITE_CLASSES = [
    ("GEO Communications", ("geo communications", "geostationary communications", "broadband relay", "communications satellite")),
    ("Science / Exploration", ("science", "exploration", "deep space", "lunar", "mars", "probe")),
    ("CubeSat", ("cubesat", "cube sat", "1u", "1.5u", "2u", "3u", "6u", "12u", "16u")),
    ("Microsatellite", ("microsatellite", "micro satellite", "microsat")),
    ("Small Satellite", ("small satellite", "smallsat", "small sat")),
    ("Medium Satellite", ("medium satellite",)),
    ("Large Satellite", ("large satellite",)),
]

ORBIT_TYPES = [
    ("Sun-Synchronous (SSO)", ("sun-synchronous", "sun synchronous", "sso")),
    ("Low Earth Orbit (LEO)", ("low earth orbit", "leo")),
    ("Medium Earth Orbit (MEO)", ("medium earth orbit", "meo")),
    ("Geostationary (GEO)", ("geostationary", "geo")),
    ("Highly Elliptical (HEO)", ("highly elliptical", "heo")),
    ("Molniya", ("molniya",)),
    ("Polar", ("polar",)),
    ("ISS Orbit (51.6deg)", ("iss", "51.6")),
    ("Equatorial LEO", ("equatorial",)),
]

PAYLOAD_TYPES = [
    ("SAR Radar", ("sar", "synthetic aperture radar", "radar")),
    ("Optical Camera", ("optical", "camera", "imager", "imaging", "earth observation")),
    ("AIS Receiver", ("ais", "maritime", "ship tracking")),
    ("IoT Receiver", ("iot", "internet of things", "sensor relay")),
    ("Weather Sensor", ("weather", "meteorology", "atmospheric")),
    ("Communications Payload", ("communications payload", "broadband", "relay", "transponder")),
    ("Hyperspectral Imager", ("hyperspectral",)),
    ("Technology Demonstration Payload", ("technology demonstration", "tech demo", "prototype", "demonstration")),
]


def _clean(value):
    return re.sub(r"\s+", " ", value or "").strip(" .,\n\t")


def _match(pattern, text, flags=re.IGNORECASE):
    result = re.search(pattern, text, flags)
    return result.group(1).strip() if result else ""


def _find_keyword_value(text, options, default=""):
    lower = text.lower()
    for value, keywords in options:
        if any(keyword in lower for keyword in keywords):
            return value
    return default


def _first_number(pattern, text):
    value = _match(pattern, text)
    if not value:
        return ""
    return value.replace(",", "")


def _extract_mission_name(text):
    first_word = re.search(r"^\s*([A-Z][A-Za-z0-9_-]{2,})\s+(?:is|will|,|\()", text)
    if first_word:
        return first_word.group(1)
    patterns = [
        r"(?:mission|spacecraft|satellite)\s+(?:named|called)\s+([A-Z][A-Za-z0-9_-]+)",
        r"(?:named|called)\s+([A-Z][A-Za-z0-9_-]+)",
        r"([A-Z][A-Za-z0-9_-]+)\s+(?:mission|spacecraft|satellite)\b",
    ]
    for pattern in patterns:
        value = _match(pattern, text, flags=0)
        if value and value.lower() not in {"the", "a", "an"}:
            return value
    title = _match(r"^\s*([A-Z][A-Za-z0-9_-]{2,})\b", text, flags=0)
    return title if title else ""


def _extract_organization(text):
    patterns = [
        r"(?:operated by|built by|developed by|from)\s+([A-Z][A-Za-z0-9&.'\- ]{2,80}?)(?=\s+(?:launching|launches|to launch|will|with|for|carrying|using)|\.|,|;|\n|$)",
        r"(?:organization|company|team|sponsor)\s+(?:is|:)\s*([A-Z][A-Za-z0-9&.'\- ]{2,80}?)(?:\.|,|;|\n|$)",
    ]
    for pattern in patterns:
        value = _clean(_match(pattern, text))
        if value:
            return value
    return ""


def _extract_launch_date(text):
    quarter_match = re.search(r"\b(20\d{2})\s*[- ]?\s*Q([1-4])\b", text, re.IGNORECASE)
    if quarter_match:
        return f"{quarter_match.group(1)}-Q{quarter_match.group(2)}"
    quarter_match = re.search(r"\bQ([1-4])\s+(20\d{2})\b", text, re.IGNORECASE)
    if quarter_match:
        return f"Q{quarter_match.group(1)} {quarter_match.group(2)}"
    month_year = _match(r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+20\d{2})\b", text)
    if month_year:
        return month_year
    year_month = _match(r"\b(20\d{2}-\d{1,2})\b", text)
    if year_month:
        return year_month
    year = _match(r"\b(?:launch|deploy|fly|rideshare|target)[a-z ]{0,30}\b(20\d{2})\b", text)
    return year


def _extract_license(text):
    lower = text.lower()
    if "25.122" in lower or "streamlined" in lower:
        return "Part 25.122 (Streamlined Small Satellite)"
    if "part 97" in lower or "amateur" in lower:
        return "Part 97 (Amateur Radio)"
    if "part 5" in lower or "experimental license" in lower:
        return "Part 5 (Experimental)"
    if "25.114" in lower or "standard application" in lower:
        return "Part 25.114 (Standard Application)"
    return ""


def _extract_team_experience(text):
    lower = text.lower()
    if "university" in lower or "student" in lower or "academic" in lower:
        return "university"
    if "startup" in lower or "new space" in lower:
        return "startup"
    if "government prime" in lower or "prime contractor" in lower or "large program" in lower:
        return "government_prime"
    if "experienced" in lower or "industry" in lower:
        return "experienced_industry"
    return ""


def _extract_budget_tier(text):
    lower = text.lower()
    if "shoestring" in lower or "low budget" in lower or "lean budget" in lower:
        return "shoestring"
    if "well funded" in lower or "well-funded" in lower or "large budget" in lower:
        return "well_funded"
    if "moderate budget" in lower or "moderate funding" in lower:
        return "moderate"
    return ""


def _normalize_data_rate(value):
    match = re.search(r"([\d.]+)\s*(gbps|mbps|kbps|bps)?", value or "", re.IGNORECASE)
    if not match:
        return ""
    amount = float(match.group(1))
    unit = (match.group(2) or "bps").lower()
    multiplier = {"bps": 1, "kbps": 1_000, "mbps": 1_000_000, "gbps": 1_000_000_000}[unit]
    return str(int(amount * multiplier))


def parse_mission_narrative(text, defaults):
    """Return an inferred mission dict plus extraction notes."""
    text = _clean(text)
    mission = dict(defaults)
    extracted = []
    warnings = []

    def set_field(key, value, label, confidence="medium"):
        value = _clean(str(value))
        if not value:
            return
        mission[key] = value
        extracted.append({
            "field": key,
            "label": label,
            "value": value,
            "confidence": confidence,
        })

    set_field("mission_name", _extract_mission_name(text), "Mission name")
    set_field("organization", _extract_organization(text), "Organization")
    set_field("satellite_class", _find_keyword_value(text, SATELLITE_CLASSES), "Satellite class")

    form_factor = _match(r"\b(1U|1\.5U|2U|3U|6U|12U|16U)\b", text, flags=re.IGNORECASE)
    if form_factor:
        set_field("form_factor", form_factor.upper(), "CubeSat form factor", "high")
        set_field("satellite_class", "CubeSat", "Satellite class", "high")

    mass = _first_number(r"\b(\d+(?:\.\d+)?)\s*(?:kg|kilograms?)\b", text)
    set_field("spacecraft_mass", mass, "Spacecraft mass", "high")

    lifetime = _first_number(r"\b(\d+(?:\.\d+)?)\s*[- ]?(?:year|yr)s?\s+(?:mission|lifetime|life|operations?)\b", text)
    if not lifetime:
        lifetime = _first_number(r"\b(?:lifetime|life|operate|operations?)\s+(?:of|for|is|:)?\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b", text)
    set_field("mission_lifetime", lifetime, "Mission lifetime", "high")

    set_field("target_launch_date", _extract_launch_date(text), "Target launch")

    orbit_type = _find_keyword_value(text, ORBIT_TYPES)
    set_field("orbit_type", orbit_type, "Orbit type")
    altitude = _first_number(r"\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*km\s+(?:altitude|orbit|leo|sso|circular)", text)
    if not altitude:
        altitude = _first_number(r"\b(?:altitude|orbit)\s+(?:of|at|is|:)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*km\b", text)
    set_field("orbit_altitude", altitude, "Orbit altitude", "high")
    inclination = _first_number(r"\b(\d+(?:\.\d+)?)\s*(?:deg|degree|degrees|degree inclination|inclination)\b", text)
    if not inclination:
        inclination = _first_number(r"\b(?:inclination|inclined)\s+(?:of|at|is|:)?\s*(\d+(?:\.\d+)?)\b", text)
    set_field("orbit_inclination", inclination, "Orbit inclination", "high")

    payload_type = _find_keyword_value(text, PAYLOAD_TYPES)
    if not payload_type:
        payload_type = _clean(_match(r"\b(?:payload|instrument)\s+(?:is|:|will be)?\s*(?:an?|the)?\s*([A-Za-z0-9 /-]{3,60})(?:\.|,|;|\n|$)", text))
    set_field("payload_type", payload_type, "Payload type")

    purpose = _clean(_match(r"\b(?:for|to support|supporting|will support)\s+([A-Za-z0-9 /-]{8,120})(?:\.|,|;|\n|$)", text))
    set_field("payload_purpose", purpose, "Payload purpose")

    uplink = _clean(_match(r"\buplink(?: frequency)?\s*(?:of|at|:)?\s*([\d.]+\s*(?:MHz|GHz|kHz))", text))
    downlink = _clean(_match(r"\bdownlink(?: frequency)?\s*(?:of|at|:)?\s*([\d.]+\s*(?:MHz|GHz|kHz))", text))
    set_field("uplink_freq", uplink, "Uplink frequency", "high")
    set_field("downlink_freq", downlink, "Downlink frequency", "high")

    data_rate = _clean(_match(r"\b(?:data rate|downlink rate)\s*(?:of|at|:)?\s*([\d.]+\s*(?:bps|kbps|Mbps|Gbps))", text))
    if data_rate:
        set_field("data_rate", _normalize_data_rate(data_rate), "Data rate", "high")

    set_field("fcc_license_type", _extract_license(text), "FCC license")

    launch_provider = _clean(_match(r"\b(?:launch provider|launcher|launch vehicle|rideshare on|launching on)\s*(?:is|:)?\s*([A-Za-z0-9 +/.-]{3,60})(?:\.|,|;|\n|$)", text))
    set_field("launch_provider", launch_provider, "Launch provider")

    ground_station = _clean(_match(r"\b(?:ground station|primary gs)\s*(?:is|at|in|:)?\s*([A-Za-z0-9 ,()./-]{3,80})(?:\.|;|\n|$)", text))
    set_field("ground_station", ground_station, "Ground station")

    team_size = _first_number(r"\b(?:team of|team size|staff of|with)\s+(\d{1,3})\s+(?:people|engineers|staff|members|person team)\b", text)
    if not team_size:
        team_size = _first_number(r"\b(\d{1,3})\s*(?:person|people|member|engineer|staff)\s+(?:[a-z]+\s+){0,4}?team\b", text)
    set_field("team_size", team_size, "Team size", "high")
    set_field("experience_level", _extract_team_experience(text), "Team experience")
    set_field("budget_tier", _extract_budget_tier(text), "Budget posture")

    if text:
        set_field("mission_description", text, "Mission description", "high")

    if not mission.get("payload_purpose") and mission.get("payload_type"):
        mission["payload_purpose"] = "mission objectives described in the narrative"
        warnings.append("Payload purpose was not explicit; used a general placeholder.")

    if not mission.get("orbit_altitude") and "geo" in mission.get("orbit_type", "").lower():
        mission["orbit_altitude"] = "35786"
        mission["orbit_inclination"] = mission.get("orbit_inclination") or "0"
        warnings.append("Used nominal GEO altitude/inclination.")

    required = [
        ("mission_name", "mission name"),
        ("organization", "organization"),
        ("spacecraft_mass", "spacecraft mass"),
        ("mission_lifetime", "mission lifetime"),
        ("target_launch_date", "target launch"),
        ("payload_type", "payload type"),
        ("orbit_altitude", "orbit altitude"),
        ("orbit_inclination", "orbit inclination"),
    ]
    missing = [label for key, label in required if not mission.get(key)]
    if missing:
        warnings.append("Still needs: " + ", ".join(missing) + ".")

    return {
        "mission": mission,
        "extracted": extracted,
        "warnings": warnings,
    }
