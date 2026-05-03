"""
Project Plan PDF generator — produces a comprehensive project management
document with WBS, RACI matrix, staffing profile, risk register, budget,
milestones, dependencies, and communication plan.
"""

import io
from datetime import datetime, date
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether,
)
from reportlab.lib.colors import HexColor


NAVY = HexColor("#1a237e")
ACCENT = HexColor("#ff6f00")
LIGHT_BG = HexColor("#e8eaf6")
WHITE = colors.white
BLACK = colors.black

# RACI cell colors
RACI_COLORS = {
    "R": HexColor("#1565C0"),   # Blue - Responsible
    "A": HexColor("#C62828"),   # Red - Accountable
    "C": HexColor("#F9A825"),   # Yellow/Amber - Consulted
    "I": HexColor("#9E9E9E"),   # Grey - Informed
}

# Risk level colors
RISK_COLORS = {
    "H": HexColor("#C62828"),   # Red
    "M": HexColor("#FF8F00"),   # Amber
    "L": HexColor("#2E7D32"),   # Green
}

# Staffing chart colors (distinct palette for roles)
ROLE_COLORS = [
    "#1565C0", "#2E7D32", "#F57F17", "#7B1FA2", "#C62828",
    "#00695C", "#AD1457", "#4527A0", "#E65100", "#1B5E20",
    "#880E4F", "#004D40", "#BF360C", "#311B92", "#33691E",
]


def _parse_date(d):
    """Flexibly parse a date from string, date, or datetime."""
    if isinstance(d, datetime):
        return d.date() if hasattr(d, 'date') else d
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        for fmt in ("%Y-%m-%d", "%Y-%m", "%B %Y", "%b %Y"):
            try:
                return datetime.strptime(d, fmt).date()
            except ValueError:
                continue
    return None


def _format_date(d):
    """Format a date for display."""
    parsed = _parse_date(d)
    if parsed:
        return parsed.strftime("%b %Y")
    return str(d) if d else "TBD"


def _flatten_wbs(wbs):
    """Accept either planner-native nested WBS or a flat work-package list."""
    if isinstance(wbs, dict):
        if isinstance(wbs.get("all_work_packages"), list):
            return wbs["all_work_packages"]
        by_phase = wbs.get("by_phase", wbs)
        if isinstance(by_phase, dict):
            flattened = []
            for phase, packages in by_phase.items():
                for wp in packages or []:
                    flattened.append({**wp, "phase": wp.get("phase", phase)})
            return flattened
    return wbs or []


def _flatten_risks(risks):
    """Accept either planner-native risks-by-phase or a flat risk list."""
    if isinstance(risks, dict):
        flattened = []
        for phase, phase_risks in risks.items():
            for risk in phase_risks or []:
                flattened.append({**risk, "phase": risk.get("phase", phase)})
        return flattened
    return risks or []


def _normalize_raci(raw_raci, fallback_roles=None, fallback_notes=None):
    """Accept planner-native RACI payload or a pre-flattened matrix."""
    if isinstance(raw_raci, dict) and "matrix" in raw_raci:
        notes = list(fallback_notes or [])
        combined_roles = raw_raci.get("combined_roles") or {}
        for person, roles in combined_roles.items():
            role_list = ", ".join(roles)
            notes.append(f"{person} combines roles: {role_list}")
        return raw_raci.get("matrix", {}), raw_raci.get("roles", []), notes

    return raw_raci or {}, fallback_roles or [], fallback_notes or []


def _budget_total(budget):
    """Use an explicit TOTAL row when present; otherwise sum line items."""
    for item in budget or []:
        if str(item.get("category", "")).upper() == "TOTAL":
            return item.get("estimate_usd", 0)
    return sum(item.get("estimate_usd", 0) for item in budget or [])


def _meeting_duration(meeting):
    if meeting.get("duration"):
        return meeting["duration"]
    if meeting.get("duration_minutes"):
        return f'{meeting["duration_minutes"]} min'
    return ""


def _generate_milestone_chart(milestones, target_launch_date=None):
    """Generate a horizontal milestone timeline chart with diamond markers."""
    if not milestones:
        return None

    valid_milestones = []
    for m in milestones:
        parsed = _parse_date(m.get("date"))
        if parsed:
            valid_milestones.append({**m, "_parsed_date": parsed})

    if not valid_milestones:
        return None

    valid_milestones.sort(key=lambda x: x["_parsed_date"])

    fig, ax = plt.subplots(figsize=(10, 4))

    dates = [m["_parsed_date"] for m in valid_milestones]
    names = [m["name"] for m in valid_milestones]

    # Convert dates to matplotlib format
    date_nums = mdates.date2num(dates)

    # Alternate label positions above and below the line
    y_positions = []
    for i in range(len(valid_milestones)):
        y_positions.append(0.3 if i % 2 == 0 else -0.3)

    # Draw horizontal timeline
    ax.axhline(y=0, color="#546E7A", linewidth=2, alpha=0.6, zorder=1)

    # Plot diamond markers
    ax.scatter(date_nums, [0] * len(date_nums), marker="D", s=80,
               color="#1a237e", zorder=3, edgecolors="white", linewidth=0.5)

    # Labels
    for i, (dn, name, yp) in enumerate(zip(date_nums, names, y_positions)):
        ax.annotate(name, (dn, 0), xytext=(0, 30 if yp > 0 else -30),
                    textcoords="offset points", ha="center", va="bottom" if yp > 0 else "top",
                    fontsize=7, fontweight="bold", color="#1a237e",
                    arrowprops=dict(arrowstyle="-", color="#9E9E9E", lw=0.8))

    # Today marker
    today = date.today()
    today_num = mdates.date2num(today)
    if date_nums[0] - 30 <= today_num <= date_nums[-1] + 30:
        ax.axvline(x=today_num, color="green", linewidth=1.5, linestyle="-",
                   alpha=0.7, label="Today", zorder=2)

    # Target launch line
    if target_launch_date:
        launch_parsed = _parse_date(target_launch_date)
        if launch_parsed:
            launch_num = mdates.date2num(launch_parsed)
            ax.axvline(x=launch_num, color="red", linewidth=2, linestyle="--",
                       alpha=0.8, label="Target Launch", zorder=2)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=30, ha="right", fontsize=8)

    ax.set_ylim(-1, 1)
    ax.set_yticks([])
    ax.set_title("Milestone Schedule", fontsize=12, fontweight="bold", pad=12)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(axis="x", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _generate_staffing_chart(staffing_profile):
    """Generate a stacked area chart of FTEs by role over time."""
    if not staffing_profile:
        return None

    # Collect all roles
    all_roles = set()
    for entry in staffing_profile:
        if entry.get("roles"):
            all_roles.update(entry["roles"].keys())

    if not all_roles:
        return None

    all_roles = sorted(all_roles)
    months = [entry.get("month", i + 1) for i, entry in enumerate(staffing_profile)]

    # Build data arrays
    data = np.zeros((len(all_roles), len(staffing_profile)))
    for j, entry in enumerate(staffing_profile):
        roles = entry.get("roles", {})
        for i, role in enumerate(all_roles):
            data[i, j] = roles.get(role, 0)

    fig, ax = plt.subplots(figsize=(10, 4.5))

    colors_list = [ROLE_COLORS[i % len(ROLE_COLORS)] for i in range(len(all_roles))]

    ax.stackplot(months, data, labels=all_roles, colors=colors_list, alpha=0.85)

    ax.set_xlabel("Month", fontsize=9)
    ax.set_ylabel("FTE Count", fontsize=9)
    ax.set_title("Staffing Profile by Discipline", fontsize=12, fontweight="bold", pad=12)
    ax.legend(loc="upper left", fontsize=7, ncol=2, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    ax.set_xlim(months[0], months[-1])
    ax.set_ylim(0, None)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _generate_budget_pie_chart(budget):
    """Generate a pie chart of budget allocation by category."""
    if not budget:
        return None

    categories = []
    amounts = []
    for item in budget:
        est = item.get("estimate_usd", 0)
        if est and est > 0:
            categories.append(item.get("category", "Unknown"))
            amounts.append(est)

    if not categories:
        return None

    fig, ax = plt.subplots(figsize=(7, 5))

    pie_colors = [ROLE_COLORS[i % len(ROLE_COLORS)] for i in range(len(categories))]

    wedges, texts, autotexts = ax.pie(
        amounts, labels=categories, autopct="%1.1f%%",
        colors=pie_colors, pctdistance=0.8,
        textprops={"fontsize": 8},
    )
    for autotext in autotexts:
        autotext.set_fontsize(7)
        autotext.set_color("white")
        autotext.set_fontweight("bold")

    ax.set_title("Budget Allocation by Category", fontsize=12, fontweight="bold", pad=12)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


class NumberedCanvas:
    """Adds page numbers and header/footer to every page."""
    def __init__(self, filename, **kwargs):
        from reportlab.pdfgen.canvas import Canvas
        self._canvas = Canvas(filename, **kwargs)
        self._pages = []

    def __getattr__(self, name):
        return getattr(self._canvas, name)

    def showPage(self):
        self._pages.append(dict(self._canvas.__dict__))
        self._canvas.showPage()

    def save(self):
        num_pages = len(self._pages)
        for i, page in enumerate(self._pages):
            self._canvas.__dict__.update(page)
            self._draw_footer(i + 1, num_pages)
            self._canvas.showPage()
        self._canvas.save()

    def _draw_footer(self, page_num, total):
        c = self._canvas
        w, h = letter
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.grey)
        c.drawCentredString(w / 2, 25, f"Page {page_num} of {total}")
        c.drawString(50, 25, "PROJECT PLAN — PRE-DECISIONAL")
        c.drawRightString(w - 50, 25, datetime.now().strftime("%Y-%m-%d"))


def generate_project_plan_pdf(mission: dict, timeline: dict, plan: dict, output_path: str):
    """Generate a comprehensive project plan PDF document.

    Args:
        mission: Mission configuration dict (mission_name, organization, etc.)
        timeline: Timeline dict from timeline_generator (target_launch_date, etc.)
        plan: Project plan dict from project_planner.generate_project_plan() containing
              wbs, milestones, raci, raci_roles, raci_notes, meetings, dependencies,
              risks, staffing_profile, budget, team_config.
        output_path: File path for the generated PDF.

    Returns:
        The output_path string.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "TitleCustom", parent=styles["Title"],
        fontSize=22, textColor=NAVY, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "Heading1Custom", parent=styles["Heading1"],
        fontSize=16, textColor=NAVY, spaceBefore=18, spaceAfter=8,
        borderWidth=0, borderPadding=0, borderColor=NAVY,
    ))
    styles.add(ParagraphStyle(
        "Heading2Custom", parent=styles["Heading2"],
        fontSize=13, textColor=NAVY, spaceBefore=12, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "Heading3Custom", parent=styles["Heading3"],
        fontSize=11, textColor=NAVY, spaceBefore=8, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "BodyCustom", parent=styles["Normal"],
        fontSize=10, leading=14, spaceAfter=6, alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        "BodySmall", parent=styles["Normal"],
        fontSize=9, leading=12, spaceAfter=4, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        "Caption", parent=styles["Normal"],
        fontSize=8.5, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        "Note", parent=styles["Normal"],
        fontSize=8.5, textColor=HexColor("#546E7A"), leading=11, spaceAfter=4,
        leftIndent=12,
    ))

    elements = []

    # Extract data with safe defaults
    wbs = _flatten_wbs(plan.get("wbs", []))
    milestones = plan.get("milestones", [])
    raci, raci_roles, raci_notes = _normalize_raci(
        plan.get("raci", {}),
        plan.get("raci_roles", []),
        plan.get("raci_notes", []),
    )
    meetings = plan.get("meeting_cadence") or plan.get("meetings", [])
    dependencies = plan.get("dependencies", [])
    risks = _flatten_risks(plan.get("risks", []))
    staffing_profile = plan.get("staffing_profile", [])
    budget = plan.get("budget", [])
    metadata = plan.get("metadata", {})
    team_config = plan.get("team_config", {})
    if not team_config and metadata:
        team_config = {
            "team_size": metadata.get("team_size"),
            "experience_level": metadata.get("experience_level"),
            "budget_tier": metadata.get("budget_tier"),
        }

    # ── Title Page ──
    elements.append(Spacer(1, 1.5 * inch))
    elements.append(Paragraph("Mission Project Plan", styles["TitleCustom"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        mission.get("mission_name", "Satellite Mission"),
        ParagraphStyle("MissionTitle", parent=styles["Title"], fontSize=18, textColor=ACCENT)
    ))
    elements.append(Spacer(1, 24))

    # Team summary
    team_size = team_config.get("team_size", team_config.get("total_staff", "TBD"))
    team_type = (
        team_config.get("team_type")
        or str(team_config.get("experience_level", "")).replace("_", " ").title()
    )

    meta_data = [
        ["Organization:", mission.get("organization", "—")],
        ["Mission:", mission.get("mission_name", "—")],
        ["Team Size:", f"{team_size} staff ({team_type})" if team_type else str(team_size)],
        ["Target Launch:", _format_date(timeline.get("target_launch_date"))],
        ["Document Date:", datetime.now().strftime("%Y-%m-%d")],
    ]
    meta_table = Table(meta_data, colWidths=[2.2 * inch, 4 * inch])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
    ]))
    elements.append(meta_table)
    elements.append(PageBreak())

    # ── 1. Executive Summary ──
    elements.append(Paragraph("1. Executive Summary", styles["Heading1Custom"]))

    # Calculate summary metrics
    total_budget = _budget_total(budget)
    num_milestones = len(milestones)
    num_wbs_items = len(wbs)

    # Determine key dates
    earliest_start = None
    latest_end = None
    for wp in wbs:
        s = _parse_date(wp.get("start"))
        e = _parse_date(wp.get("end"))
        if s and (earliest_start is None or s < earliest_start):
            earliest_start = s
        if e and (latest_end is None or e > latest_end):
            latest_end = e

    summary_text = (
        f'This document presents the project management plan for the '
        f'<b>{mission.get("mission_name", "satellite")}</b> mission. '
    )
    if earliest_start and latest_end:
        summary_text += (
            f'The plan spans from {earliest_start.strftime("%B %Y")} to '
            f'{latest_end.strftime("%B %Y")}. '
        )
    summary_text += (
        f'The work breakdown structure contains <b>{num_wbs_items} work packages</b> '
        f'organized across multiple phases, with <b>{num_milestones} review milestones</b>. '
    )
    if team_size and team_size != "TBD":
        summary_text += f'The team comprises <b>{team_size} staff members</b>. '
    if total_budget > 0:
        if total_budget >= 1_000_000:
            summary_text += (
                f'The rough order of magnitude (ROM) budget is '
                f'<b>${total_budget / 1_000_000:.1f}M</b>. '
            )
        else:
            summary_text += (
                f'The rough order of magnitude (ROM) budget is '
                f'<b>${total_budget:,.0f}</b>. '
            )

    elements.append(Paragraph(summary_text, styles["BodyCustom"]))
    elements.append(Spacer(1, 8))

    # Summary metrics table
    summary_metrics = [
        ["Metric", "Value"],
        ["Work Packages", str(num_wbs_items)],
        ["Review Milestones", str(num_milestones)],
        ["Team Size", str(team_size) if team_size else "TBD"],
        ["Plan Start", earliest_start.strftime("%b %Y") if earliest_start else "TBD"],
        ["Plan End", latest_end.strftime("%b %Y") if latest_end else "TBD"],
        ["Budget ROM", f"${total_budget / 1_000_000:.1f}M" if total_budget >= 1_000_000
         else f"${total_budget:,.0f}" if total_budget > 0 else "TBD"],
        ["Risk Items", str(len(risks))],
    ]
    summary_table = Table(summary_metrics, colWidths=[3.5 * inch, 3 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Paragraph("Table 1 — Project Plan Summary Metrics", styles["Caption"]))
    elements.append(PageBreak())

    # ── 2. Work Breakdown Structure ──
    elements.append(Paragraph("2. Work Breakdown Structure", styles["Heading1Custom"]))
    elements.append(Paragraph(
        "The following table presents all work packages organized by project phase. "
        "Milestone items (review gates) are highlighted. Durations are in weeks.",
        styles["BodyCustom"]
    ))
    elements.append(Spacer(1, 6))

    if wbs:
        # Group WBS by phase
        phases_order = []
        phase_groups = {}
        for wp in wbs:
            phase = wp.get("phase", "Unassigned")
            if phase not in phase_groups:
                phases_order.append(phase)
                phase_groups[phase] = []
            phase_groups[phase].append(wp)

        wbs_header = ["WBS #", "Task", "Deliverable", "Duration", "Start", "End"]
        col_widths = [0.55 * inch, 2.2 * inch, 1.8 * inch, 0.65 * inch, 0.7 * inch, 0.7 * inch]

        wbs_rows = [wbs_header]
        phase_row_indices = []  # Track which rows are phase headers
        milestone_row_indices = []  # Track which rows are milestones

        for phase in phases_order:
            # Phase header row (spanning full width)
            phase_row_indices.append(len(wbs_rows))
            wbs_rows.append([phase, "", "", "", "", ""])

            for wp in phase_groups[phase]:
                row_idx = len(wbs_rows)
                if wp.get("is_milestone"):
                    milestone_row_indices.append(row_idx)

                duration_str = f'{wp.get("duration_weeks", 0)}w'
                wbs_rows.append([
                    wp.get("id", ""),
                    wp.get("name", ""),
                    wp.get("deliverable", ""),
                    duration_str,
                    _format_date(wp.get("start")),
                    _format_date(wp.get("end")),
                ])

        wbs_table = Table(wbs_rows, colWidths=col_widths, repeatRows=1)

        wbs_style = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (3, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]

        # Style phase header rows
        for idx in phase_row_indices:
            wbs_style.append(("BACKGROUND", (0, idx), (-1, idx), HexColor("#546E7A")))
            wbs_style.append(("TEXTCOLOR", (0, idx), (-1, idx), WHITE))
            wbs_style.append(("FONTNAME", (0, idx), (-1, idx), "Helvetica-Bold"))
            wbs_style.append(("SPAN", (0, idx), (-1, idx)))
            wbs_style.append(("ALIGN", (0, idx), (-1, idx), "LEFT"))
            wbs_style.append(("LEFTPADDING", (0, idx), (0, idx), 8))

        # Highlight milestone rows
        for idx in milestone_row_indices:
            wbs_style.append(("BACKGROUND", (0, idx), (-1, idx), HexColor("#FFF3E0")))
            wbs_style.append(("FONTNAME", (0, idx), (-1, idx), "Helvetica-Bold"))

        wbs_table.setStyle(TableStyle(wbs_style))
        elements.append(wbs_table)
        elements.append(Paragraph("Table 2 — Work Breakdown Structure", styles["Caption"]))
    else:
        elements.append(Paragraph(
            "<i>No work breakdown structure data available.</i>", styles["BodyCustom"]
        ))

    elements.append(PageBreak())

    # ── 3. Milestone Schedule ──
    elements.append(Paragraph("3. Milestone Schedule", styles["Heading1Custom"]))
    elements.append(Paragraph(
        "The following review gates and milestones define the project's key decision points. "
        "Each milestone has defined success criteria that must be met before proceeding.",
        styles["BodyCustom"]
    ))
    elements.append(Spacer(1, 6))

    if milestones:
        ms_header = ["Milestone", "Date", "Phase", "Success Criteria"]
        ms_rows = [ms_header]
        for m in milestones:
            criteria = m.get("success_criteria", "")
            if isinstance(criteria, list):
                criteria = "; ".join(criteria)
            # Truncate long criteria for table display
            if len(str(criteria)) > 80:
                criteria = str(criteria)[:77] + "..."
            ms_rows.append([
                m.get("name", ""),
                _format_date(m.get("date")),
                m.get("phase", ""),
                criteria,
            ])

        ms_widths = [1.8 * inch, 0.8 * inch, 1.2 * inch, 3 * inch]
        ms_table = Table(ms_rows, colWidths=ms_widths, repeatRows=1)
        ms_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(ms_table)
        elements.append(Paragraph("Table 3 — Milestone Schedule", styles["Caption"]))

        # Milestone chart
        target_launch = timeline.get("target_launch_date")
        ms_buf = _generate_milestone_chart(milestones, target_launch)
        if ms_buf:
            elements.append(Spacer(1, 8))
            elements.append(Image(ms_buf, width=7 * inch, height=2.8 * inch))
            elements.append(Paragraph("Figure 1 — Milestone Timeline Chart", styles["Caption"]))
    else:
        elements.append(Paragraph(
            "<i>No milestones defined.</i>", styles["BodyCustom"]
        ))

    elements.append(PageBreak())

    # ── 4. RACI Matrix ──
    elements.append(Paragraph("4. RACI Matrix", styles["Heading1Custom"]))
    elements.append(Paragraph(
        "The RACI matrix defines responsibility assignments for each project phase. "
        "<b>R</b>=Responsible (does the work), <b>A</b>=Accountable (approves/owns), "
        "<b>C</b>=Consulted (provides input), <b>I</b>=Informed (kept updated).",
        styles["BodyCustom"]
    ))
    elements.append(Spacer(1, 6))

    if raci and raci_roles:
        # Build RACI table: phases as rows, roles as columns
        # Truncate role names if too many columns
        display_roles = raci_roles[:10]  # Max 10 roles to fit on page
        role_col_width = min(0.6 * inch, (6.5 * inch - 1.8 * inch) / len(display_roles))

        raci_header = ["Phase"] + [r[:10] for r in display_roles]  # Truncate long role names
        raci_rows = [raci_header]

        raci_phases = list(raci.keys())
        for phase in raci_phases:
            row = [phase]
            phase_assignments = raci[phase]
            for role in display_roles:
                cell_value = phase_assignments.get(role, "")
                row.append(cell_value)
            raci_rows.append(row)

        raci_col_widths = [1.8 * inch] + [role_col_width] * len(display_roles)
        raci_table = Table(raci_rows, colWidths=raci_col_widths, repeatRows=1)

        raci_style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]

        # Color-code RACI cells
        for row_idx in range(1, len(raci_rows)):
            for col_idx in range(1, len(raci_rows[row_idx])):
                cell_val = raci_rows[row_idx][col_idx].strip().upper() if raci_rows[row_idx][col_idx] else ""
                if cell_val in RACI_COLORS:
                    raci_style_cmds.append(
                        ("TEXTCOLOR", (col_idx, row_idx), (col_idx, row_idx), RACI_COLORS[cell_val])
                    )
                    raci_style_cmds.append(
                        ("FONTNAME", (col_idx, row_idx), (col_idx, row_idx), "Helvetica-Bold")
                    )

        raci_table.setStyle(TableStyle(raci_style_cmds))
        elements.append(raci_table)
        elements.append(Paragraph("Table 4 — RACI Responsibility Matrix", styles["Caption"]))

        # RACI notes
        if raci_notes:
            elements.append(Spacer(1, 4))
            elements.append(Paragraph("Notes:", styles["Heading3Custom"]))
            for note in raci_notes:
                elements.append(Paragraph(f"• {note}", styles["Note"]))
    else:
        elements.append(Paragraph(
            "<i>No RACI matrix data available.</i>", styles["BodyCustom"]
        ))

    elements.append(PageBreak())

    # ── 5. Staffing Profile ──
    elements.append(Paragraph("5. Staffing Profile", styles["Heading1Custom"]))
    elements.append(Paragraph(
        "The staffing profile shows the planned full-time equivalent (FTE) allocation "
        "by discipline over the project lifecycle.",
        styles["BodyCustom"]
    ))

    if staffing_profile:
        staffing_buf = _generate_staffing_chart(staffing_profile)
        if staffing_buf:
            elements.append(Spacer(1, 8))
            elements.append(Image(staffing_buf, width=7 * inch, height=3.2 * inch))
            elements.append(Paragraph("Figure 2 — Staffing Profile (FTE by Discipline)", styles["Caption"]))

        # Peak staffing summary
        peak_total = 0
        peak_month = 0
        for entry in staffing_profile:
            total = sum(entry.get("roles", {}).values())
            if total > peak_total:
                peak_total = total
                peak_month = entry.get("month", 0)

        if peak_total > 0:
            elements.append(Paragraph(
                f"Peak staffing of <b>{peak_total:.1f} FTEs</b> occurs in {peak_month}.",
                styles["BodyCustom"]
            ))
    else:
        elements.append(Paragraph(
            "<i>No staffing profile data available.</i>", styles["BodyCustom"]
        ))

    elements.append(PageBreak())

    # ── 6. Dependencies ──
    elements.append(Paragraph("6. Dependencies", styles["Heading1Custom"]))
    elements.append(Paragraph(
        "The following table identifies critical inter-task dependencies that constrain "
        "the project schedule. Lag values indicate minimum wait time between tasks.",
        styles["BodyCustom"]
    ))
    elements.append(Spacer(1, 6))

    if dependencies:
        # Build lookup for WBS names
        wbs_lookup = {wp.get("id", ""): wp.get("name", wp.get("id", "")) for wp in wbs}

        dep_header = ["#", "Predecessor", "Successor", "Type", "Lag"]
        dep_rows = [dep_header]
        for i, dep in enumerate(dependencies, 1):
            from_id = dep.get("from_id", "")
            to_id = dep.get("to_id", "")
            from_name = wbs_lookup.get(from_id, from_id)
            to_name = wbs_lookup.get(to_id, to_id)
            dep_type = dep.get("type", "FS")
            lag = dep.get("lag_weeks", 0)
            lag_str = f"{lag}w" if lag else "—"
            dep_rows.append([str(i), from_name, to_name, dep_type, lag_str])

        dep_widths = [0.4 * inch, 2.4 * inch, 2.4 * inch, 0.6 * inch, 0.5 * inch]
        dep_table = Table(dep_rows, colWidths=dep_widths, repeatRows=1)
        dep_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (3, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(dep_table)
        elements.append(Paragraph("Table 5 — Critical Dependencies", styles["Caption"]))
    else:
        elements.append(Paragraph(
            "<i>No dependency data available.</i>", styles["BodyCustom"]
        ))

    elements.append(PageBreak())

    # ── 7. Risk Register ──
    elements.append(Paragraph("7. Risk Register", styles["Heading1Custom"]))
    elements.append(Paragraph(
        "The risk register identifies key project risks, their likelihood and impact "
        "assessments, and planned mitigation strategies. Likelihood and impact are rated "
        "as High (H), Medium (M), or Low (L).",
        styles["BodyCustom"]
    ))
    elements.append(Spacer(1, 6))

    if risks:
        risk_header = ["#", "Risk Description", "Phase", "L", "I", "Mitigation", "Owner"]
        risk_rows = [risk_header]
        for i, r in enumerate(risks, 1):
            desc = r.get("description", "")
            if len(desc) > 60:
                desc = desc[:57] + "..."
            mitigation = r.get("mitigation", "")
            if len(mitigation) > 50:
                mitigation = mitigation[:47] + "..."
            risk_rows.append([
                str(i),
                desc,
                r.get("phase", "")[:15],
                r.get("likelihood", "M")[0].upper(),
                r.get("impact", "M")[0].upper(),
                mitigation,
                r.get("owner_role", "")[:12],
            ])

        risk_widths = [0.3 * inch, 1.9 * inch, 0.8 * inch, 0.3 * inch, 0.3 * inch, 1.9 * inch, 0.8 * inch]
        risk_table = Table(risk_rows, colWidths=risk_widths, repeatRows=1)

        risk_style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 7.5),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (3, 0), (4, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]

        # Color-code likelihood and impact cells
        for row_idx in range(1, len(risk_rows)):
            likelihood = risk_rows[row_idx][3]
            impact = risk_rows[row_idx][4]
            if likelihood in RISK_COLORS:
                risk_style_cmds.append(
                    ("TEXTCOLOR", (3, row_idx), (3, row_idx), RISK_COLORS[likelihood])
                )
                risk_style_cmds.append(
                    ("FONTNAME", (3, row_idx), (3, row_idx), "Helvetica-Bold")
                )
            if impact in RISK_COLORS:
                risk_style_cmds.append(
                    ("TEXTCOLOR", (4, row_idx), (4, row_idx), RISK_COLORS[impact])
                )
                risk_style_cmds.append(
                    ("FONTNAME", (4, row_idx), (4, row_idx), "Helvetica-Bold")
                )

        risk_table.setStyle(TableStyle(risk_style_cmds))
        elements.append(risk_table)
        elements.append(Paragraph("Table 6 — Risk Register", styles["Caption"]))

        # Risk summary
        high_risks = sum(1 for r in risks
                         if r.get("likelihood", "")[0:1].upper() == "H"
                         or r.get("impact", "")[0:1].upper() == "H")
        if high_risks > 0:
            elements.append(Paragraph(
                f"<b>{high_risks} risk(s)</b> have a High likelihood or High impact rating "
                f"and require active monitoring and mitigation.",
                styles["BodyCustom"]
            ))
    else:
        elements.append(Paragraph(
            "<i>No risks identified.</i>", styles["BodyCustom"]
        ))

    elements.append(PageBreak())

    # ── 8. Meeting & Communication Plan ──
    elements.append(Paragraph("8. Meeting & Communication Plan", styles["Heading1Custom"]))
    elements.append(Paragraph(
        "The following recurring meetings establish the project's communication cadence "
        "and coordination rhythm across all active phases.",
        styles["BodyCustom"]
    ))
    elements.append(Spacer(1, 6))

    if meetings:
        mtg_header = ["Meeting", "Frequency", "Duration", "Attendees", "Purpose"]
        mtg_rows = [mtg_header]
        for m in meetings:
            attendees = m.get("attendees", [])
            if isinstance(attendees, list):
                attendees_str = ", ".join(attendees[:4])
                if len(attendees) > 4:
                    attendees_str += f" +{len(attendees) - 4}"
            else:
                attendees_str = str(attendees)
            purpose = m.get("purpose", "")
            if len(purpose) > 50:
                purpose = purpose[:47] + "..."
            mtg_rows.append([
                m.get("name", ""),
                m.get("frequency", ""),
                _meeting_duration(m),
                attendees_str,
                purpose,
            ])

        mtg_widths = [1.4 * inch, 0.8 * inch, 0.7 * inch, 1.8 * inch, 2.1 * inch]
        mtg_table = Table(mtg_rows, colWidths=mtg_widths, repeatRows=1)
        mtg_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (1, 0), (2, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(mtg_table)
        elements.append(Paragraph("Table 7 — Meeting & Communication Plan", styles["Caption"]))

        # Active phases note
        meetings_with_phases = [m for m in meetings if m.get("active_phases")]
        if meetings_with_phases:
            elements.append(Spacer(1, 4))
            elements.append(Paragraph("Active Phase Coverage:", styles["Heading3Custom"]))
            for m in meetings_with_phases:
                phases_list = m.get("active_phases", [])
                if isinstance(phases_list, list):
                    phases_str = ", ".join(phases_list)
                else:
                    phases_str = str(phases_list)
                elements.append(Paragraph(
                    f"• <b>{m.get('name', '')}</b>: {phases_str}",
                    styles["Note"]
                ))
    else:
        elements.append(Paragraph(
            "<i>No meeting plan data available.</i>", styles["BodyCustom"]
        ))

    elements.append(PageBreak())

    # ── 9. Budget Estimate ──
    elements.append(Paragraph("9. Budget Estimate", styles["Heading1Custom"]))
    elements.append(Paragraph(
        "The following rough order of magnitude (ROM) budget estimate covers the major "
        "cost categories for the project. These are planning-level estimates subject "
        "to refinement during detailed design.",
        styles["BodyCustom"]
    ))
    elements.append(Spacer(1, 6))

    if budget:
        bgt_header = ["Category", "Estimate (USD)", "Notes"]
        bgt_rows = [bgt_header]
        for item in budget:
            if str(item.get("category", "")).upper() == "TOTAL":
                continue
            est = item.get("estimate_usd", 0)
            if est >= 1_000_000:
                est_str = f"${est / 1_000_000:.2f}M"
            elif est >= 1_000:
                est_str = f"${est / 1_000:.0f}K"
            elif est > 0:
                est_str = f"${est:,.0f}"
            else:
                est_str = "TBD"
            notes = item.get("notes", "")
            if len(notes) > 60:
                notes = notes[:57] + "..."
            bgt_rows.append([
                item.get("category", ""),
                est_str,
                notes,
            ])

        # Total row
        if total_budget > 0:
            if total_budget >= 1_000_000:
                total_str = f"${total_budget / 1_000_000:.2f}M"
            else:
                total_str = f"${total_budget:,.0f}"
            bgt_rows.append(["TOTAL", total_str, ""])

        bgt_widths = [2 * inch, 1.3 * inch, 3.5 * inch]
        bgt_table = Table(bgt_rows, colWidths=bgt_widths, repeatRows=1)

        bgt_style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]

        # Bold the total row
        if total_budget > 0:
            total_row_idx = len(bgt_rows) - 1
            bgt_style_cmds.append(("FONTNAME", (0, total_row_idx), (-1, total_row_idx), "Helvetica-Bold"))
            bgt_style_cmds.append(("BACKGROUND", (0, total_row_idx), (-1, total_row_idx), LIGHT_BG))
            bgt_style_cmds.append(("LINEABOVE", (0, total_row_idx), (-1, total_row_idx), 1.5, NAVY))

        bgt_table.setStyle(TableStyle(bgt_style_cmds))
        elements.append(bgt_table)
        elements.append(Paragraph("Table 8 — Budget Estimate (ROM)", styles["Caption"]))

        # Budget pie chart
        pie_buf = _generate_budget_pie_chart(budget)
        if pie_buf:
            elements.append(Spacer(1, 8))
            elements.append(Image(pie_buf, width=5 * inch, height=3.5 * inch))
            elements.append(Paragraph("Figure 3 — Budget Allocation by Category", styles["Caption"]))
    else:
        elements.append(Paragraph(
            "<i>No budget data available.</i>", styles["BodyCustom"]
        ))

    elements.append(PageBreak())

    # ── 10. Appendix: Phase Entry/Exit Criteria ──
    elements.append(Paragraph("10. Appendix: Phase Entry/Exit Criteria", styles["Heading1Custom"]))
    elements.append(Paragraph(
        "The following entry and exit criteria define the quality gates for each project phase. "
        "All entry criteria must be satisfied before commencing a phase; all exit criteria "
        "must be met before proceeding to the next phase.",
        styles["BodyCustom"]
    ))
    elements.append(Spacer(1, 8))

    # Collect entry/exit criteria from WBS milestones and the milestones list
    phase_criteria = {}  # {phase: {"entry": [...], "exit": [...]}}

    for wp in wbs:
        phase = wp.get("phase", "Unassigned")
        if phase not in phase_criteria:
            phase_criteria[phase] = {"entry": [], "exit": []}

        entry = wp.get("entry_criteria")
        exit_c = wp.get("exit_criteria")

        if entry:
            if isinstance(entry, list):
                phase_criteria[phase]["entry"].extend(entry)
            elif isinstance(entry, str) and entry:
                phase_criteria[phase]["entry"].append(entry)

        if exit_c:
            if isinstance(exit_c, list):
                phase_criteria[phase]["exit"].extend(exit_c)
            elif isinstance(exit_c, str) and exit_c:
                phase_criteria[phase]["exit"].append(exit_c)

    # Also pull from milestones
    for m in milestones:
        phase = m.get("phase", "")
        if phase and phase not in phase_criteria:
            phase_criteria[phase] = {"entry": [], "exit": []}

        entry = m.get("entry_criteria")
        success = m.get("success_criteria")

        if phase and entry:
            if isinstance(entry, list):
                phase_criteria[phase]["entry"].extend(entry)
            elif isinstance(entry, str) and entry:
                phase_criteria[phase]["entry"].append(entry)

        if phase and success:
            if isinstance(success, list):
                phase_criteria[phase]["exit"].extend(success)
            elif isinstance(success, str) and success:
                phase_criteria[phase]["exit"].append(success)

    if phase_criteria:
        for phase, criteria in phase_criteria.items():
            # De-duplicate criteria
            entry_list = list(dict.fromkeys(criteria["entry"]))
            exit_list = list(dict.fromkeys(criteria["exit"]))

            if not entry_list and not exit_list:
                continue

            elements.append(Paragraph(phase, styles["Heading2Custom"]))

            if entry_list:
                elements.append(Paragraph("<b>Entry Criteria:</b>", styles["BodySmall"]))
                for item in entry_list:
                    elements.append(Paragraph(
                        f"&bull; {item}",
                        styles["Note"]
                    ))
                elements.append(Spacer(1, 4))

            if exit_list:
                elements.append(Paragraph("<b>Exit Criteria:</b>", styles["BodySmall"]))
                for item in exit_list:
                    elements.append(Paragraph(
                        f"&bull; {item}",
                        styles["Note"]
                    ))
                elements.append(Spacer(1, 6))
    else:
        elements.append(Paragraph(
            "<i>No entry/exit criteria data available.</i>", styles["BodyCustom"]
        ))

    # Build PDF
    doc.build(elements, canvasmaker=NumberedCanvas)
    return output_path
