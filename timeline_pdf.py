"""
Timeline PDF generator — produces a mission project timeline document
with Gantt chart, launch vehicle comparison, phase details, and
probability-of-completion analysis.
"""

import io
import os
from datetime import datetime
from typing import Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
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
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.colors import HexColor


NAVY = HexColor("#1a237e")
ACCENT = HexColor("#ff6f00")
LIGHT_BG = HexColor("#e8eaf6")
WHITE = colors.white
BLACK = colors.black

PHASE_COLORS = {
    "Concept":      "#1565C0",
    "Preliminary":  "#1976D2",
    "Detailed":     "#1E88E5",
    "Technology":   "#7B1FA2",
    "Component":    "#43A047",
    "Fabrication":  "#2E7D32",
    "Integration":  "#F57F17",
    "Environmental":"#E65100",
    "Experimental": "#AD1457",
    "Radiation":    "#880E4F",
    "Extended":     "#4A148C",
    "FCC":          "#00695C",
    "IARU":         "#00838F",
    "ITU":          "#006064",
    "Orbital Slot": "#004D40",
    "ITAR":         "#BF360C",
    "Launch Vehicle":"#5D4037",
    "Range":        "#3E2723",
    "Pre-Ship":     "#546E7A",
    "Launch Campaign":"#D32F2F",
}


def _phase_color(name: str) -> str:
    for key, color in PHASE_COLORS.items():
        if key.lower() in name.lower():
            return color
    return "#78909C"


def _generate_gantt_chart(gantt_data, target_months, available_months):
    """Generate a horizontal Gantt chart."""
    n = len(gantt_data)
    fig_height = max(6, n * 0.38 + 1.5)
    fig, ax = plt.subplots(figsize=(10, fig_height))

    y_positions = list(range(n - 1, -1, -1))

    for i, phase in enumerate(gantt_data):
        y = y_positions[i]
        color = _phase_color(phase["name"])

        # Nominal bar
        ax.barh(y, phase["duration"], left=phase["start_month"],
                height=0.6, color=color, alpha=0.85, edgecolor="white", linewidth=0.5)

        # Optimistic/pessimistic whiskers
        opt_start = phase["start_month"]
        pess_end = phase["start_month"] + phase["pess"]
        ax.plot([opt_start, opt_start + phase["opt"]], [y, y],
                color=color, linewidth=2, alpha=0.4)
        ax.plot([phase["start_month"] + phase["duration"], pess_end], [y, y],
                color=color, linewidth=2, alpha=0.4, linestyle="--")

        # Duration label
        mid = phase["start_month"] + phase["duration"] / 2
        label = f'{phase["duration"]:.0f}mo' if phase["duration"] >= 1 else f'{phase["duration"]*30:.0f}d'
        ax.text(mid, y, label, ha="center", va="center",
                fontsize=7, color="white", fontweight="bold")

    ax.set_yticks(y_positions)
    ax.set_yticklabels([p["name"] for p in gantt_data], fontsize=7.5)

    # Today line
    ax.axvline(x=0, color="green", linewidth=1.5, linestyle="-", alpha=0.7, label="Today")

    # Target launch line
    if available_months > 0:
        ax.axvline(x=available_months, color="red", linewidth=2, linestyle="--",
                   alpha=0.8, label=f"Target Launch ({available_months:.0f} mo)")

    max_month = max(p["start_month"] + p["pess"] for p in gantt_data) if gantt_data else 36
    ax.set_xlim(-1, max(max_month + 2, available_months + 2) if available_months > 0 else max_month + 2)

    # X-axis: months with year markers
    ax.set_xlabel("Months from Project Start", fontsize=9)
    ax.set_title("Mission Project Timeline (Gantt Chart)", fontsize=12, fontweight="bold", pad=12)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _generate_probability_gauge(probability_pct):
    """Generate a semicircular gauge chart for completion probability."""
    fig, ax = plt.subplots(figsize=(5, 3), subplot_kw={"projection": "polar"})

    # Semicircle gauge
    theta = np.linspace(np.pi, 0, 100)
    r = np.ones(100)

    # Background segments
    colors_gradient = plt.cm.RdYlGn(np.linspace(0, 1, 100))
    for i in range(99):
        ax.fill_between([theta[i], theta[i+1]], 0, 1,
                       color=colors_gradient[i], alpha=0.3)

    # Needle
    needle_angle = np.pi - (probability_pct / 100) * np.pi
    ax.plot([needle_angle, needle_angle], [0, 0.85], color="#212121",
            linewidth=3, solid_capstyle="round")
    ax.plot(needle_angle, 0.85, "o", color="#212121", markersize=6)
    ax.plot(0, 0, "o", color="#212121", markersize=10, zorder=5)

    # Labels
    ax.text(np.pi, -0.15, "0%", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(np.pi/2, -0.15, "50%", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(0, -0.15, "100%", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(np.pi/2, -0.4, f"{probability_pct}%", ha="center", va="center",
            fontsize=24, fontweight="bold",
            color="#2E7D32" if probability_pct >= 70 else "#F57F17" if probability_pct >= 40 else "#C62828")

    ax.set_ylim(-0.5, 1.1)
    ax.set_theta_zero_location("E")
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    ax.axis("off")

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _generate_vehicle_comparison(vehicles):
    """Bar chart comparing top launch vehicles by cost."""
    priced = [v for v in vehicles[:8] if v.get("cost_usd")]
    if not priced:
        return None

    fig, ax = plt.subplots(figsize=(9, 4))
    names = [v["name"] for v in priced]
    costs = [v["cost_usd"] / 1e6 for v in priced]
    capacities = [v["capacity_for_orbit"] for v in priced]

    x = np.arange(len(names))
    width = 0.4

    bars1 = ax.bar(x - width/2, costs, width, label="Cost ($M)", color="#1565C0", alpha=0.85)
    ax.set_ylabel("Cost ($M)", color="#1565C0")

    ax2 = ax.twinx()
    bars2 = ax2.bar(x + width/2, capacities, width, label="Capacity (kg)", color="#E65100", alpha=0.85)
    ax2.set_ylabel("Capacity (kg)", color="#E65100")

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
    ax.set_title("Launch Vehicle Comparison", fontsize=12, fontweight="bold")

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)

    ax.grid(axis="y", alpha=0.3)
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
        c.drawString(50, 25, "MISSION TIMELINE — PRE-DECISIONAL")
        c.drawRightString(w - 50, 25, datetime.now().strftime("%Y-%m-%d"))


def generate_timeline_pdf(mission: Dict, timeline: Dict, output_path: str):
    """Generate a comprehensive mission timeline PDF."""
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
        "BodyCustom", parent=styles["Normal"],
        fontSize=10, leading=14, spaceAfter=6, alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        "Caption", parent=styles["Normal"],
        fontSize=8.5, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        "PositiveImpact", parent=styles["Normal"],
        fontSize=9.5, textColor=HexColor("#2E7D32"), leading=13,
    ))
    styles.add(ParagraphStyle(
        "NegativeImpact", parent=styles["Normal"],
        fontSize=9.5, textColor=HexColor("#C62828"), leading=13,
    ))
    styles.add(ParagraphStyle(
        "NeutralImpact", parent=styles["Normal"],
        fontSize=9.5, textColor=HexColor("#546E7A"), leading=13,
    ))

    elements = []

    # ── Title Page ──
    elements.append(Spacer(1, 1.5 * inch))
    elements.append(Paragraph("Mission Project Timeline", styles["TitleCustom"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        mission.get("mission_name", "Satellite Mission"),
        ParagraphStyle("MissionTitle", parent=styles["Title"], fontSize=18, textColor=ACCENT)
    ))
    elements.append(Spacer(1, 24))

    meta_data = [
        ["Organization:", mission.get("organization", "—")],
        ["Satellite Class:", timeline["satellite_class"]],
        ["Spacecraft Mass:", f'{timeline["mass_kg"]:.1f} kg'],
        ["Target Launch:", timeline["target_launch_date"].strftime("%B %Y")],
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

    prob = timeline["probability_pct"]
    if prob >= 70:
        risk_word = "favorable"
    elif prob >= 40:
        risk_word = "moderate"
    else:
        risk_word = "challenging"

    avail = timeline["available_months"]
    crit = timeline["critical_path_months"]
    margin = avail - crit

    summary_text = (
        f'This document presents a comprehensive project timeline for the '
        f'<b>{mission.get("mission_name", "satellite")}</b> mission, a '
        f'{timeline["satellite_class"]} with a target launch date of '
        f'{timeline["target_launch_date"].strftime("%B %Y")}. '
        f'The critical path analysis estimates <b>{crit:.0f} months</b> from project '
        f'initiation to launch readiness (with parallel activities), compared to '
        f'<b>{avail:.0f} months</b> available. '
    )
    if margin >= 0:
        summary_text += (
            f'This provides a schedule margin of <b>{margin:.0f} months</b>. '
        )
    else:
        summary_text += (
            f'This indicates a schedule shortfall of <b>{abs(margin):.0f} months</b> '
            f'under nominal assumptions. '
        )
    summary_text += (
        f'The overall probability of on-time completion is assessed at '
        f'<b>{prob}%</b> ({risk_word} outlook). '
        f'{len(timeline["launch_vehicles"])} compatible launch vehicles were identified.'
    )
    elements.append(Paragraph(summary_text, styles["BodyCustom"]))
    elements.append(Spacer(1, 12))

    # Key metrics table
    key_data = [
        ["Metric", "Value"],
        ["Critical Path Duration", f'{crit:.0f} months'],
        ["Serial (No Parallel) Duration", f'{timeline["serial_months_needed"]:.0f} months'],
        ["Time Available to Launch", f'{avail:.0f} months'],
        ["Schedule Margin", f'{margin:+.0f} months'],
        ["On-Time Probability", f'{prob}%'],
        ["Compatible Launch Vehicles", str(len(timeline["launch_vehicles"]))],
    ]
    key_table = Table(key_data, colWidths=[3.5 * inch, 3 * inch])
    key_table.setStyle(TableStyle([
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
    elements.append(key_table)
    elements.append(Paragraph("Table 1 — Timeline Key Metrics", styles["Caption"]))

    # ── 2. Project Gantt Chart ──
    elements.append(Paragraph("2. Project Timeline (Gantt Chart)", styles["Heading1Custom"]))
    elements.append(Paragraph(
        "The following chart shows all project phases from concept through launch. "
        "Solid bars represent nominal durations; dashed extensions show pessimistic estimates. "
        "The red dashed line marks the target launch date.",
        styles["BodyCustom"]
    ))

    gantt_buf = _generate_gantt_chart(
        timeline["gantt_data"],
        timeline["critical_path_months"],
        timeline["available_months"],
    )
    gantt_img = Image(gantt_buf, width=7 * inch, height=min(8 * inch, len(timeline["gantt_data"]) * 0.3 * inch + 1.2 * inch))
    elements.append(gantt_img)
    elements.append(Paragraph("Figure 1 — Mission Project Gantt Chart", styles["Caption"]))

    # ── 3. Phase Details ──
    elements.append(PageBreak())
    elements.append(Paragraph("3. Phase Details", styles["Heading1Custom"]))
    elements.append(Paragraph(
        "Each phase includes optimistic, nominal, and pessimistic duration estimates "
        "based on industry data for the satellite class and mission parameters.",
        styles["BodyCustom"]
    ))

    phase_header = ["Phase", "Start", "End", "Opt", "Nom", "Pess"]
    phase_rows = [phase_header]
    for p in timeline["phases"]:
        phase_rows.append([
            p["name"],
            p["start"].strftime("%b %Y"),
            p["end"].strftime("%b %Y"),
            f'{p["duration_opt"]:.1f} mo',
            f'{p["duration_nom"]:.1f} mo',
            f'{p["duration_pess"]:.1f} mo',
        ])

    col_widths = [2.7 * inch, 0.85 * inch, 0.85 * inch, 0.7 * inch, 0.7 * inch, 0.7 * inch]
    phase_table = Table(phase_rows, colWidths=col_widths, repeatRows=1)
    phase_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
    ]))
    elements.append(phase_table)
    elements.append(Paragraph("Table 2 — Phase Schedule Detail", styles["Caption"]))

    # Phase descriptions
    elements.append(Paragraph("3.1 Phase Descriptions", styles["Heading2Custom"]))

    phase_descriptions = {
        "Concept Development & Feasibility": (
            "Define mission objectives, perform trade studies, establish preliminary requirements, "
            "assess technical feasibility, identify key risks, and produce the Mission Concept Review (MCR) package."
        ),
        "Technology Readiness Maturation": (
            "Advance key technologies from current TRL to the required level (typically TRL 6+). "
            "Includes breadboard demonstrations, lab testing, and risk reduction prototyping."
        ),
        "Preliminary Design & PDR": (
            "Develop subsystem-level designs, interface definitions, and preliminary analysis. "
            "Culminates in the Preliminary Design Review (PDR) with independent review board."
        ),
        "Detailed Design & CDR": (
            "Complete detailed design of all subsystems, finalize drawings and specifications, "
            "perform detailed analysis (thermal, structural, RF, power). Critical Design Review (CDR)."
        ),
        "Component Procurement": (
            "Procure flight hardware components, including long-lead items (reaction wheels, "
            "solar cells, RF components, propulsion hardware). Establish vendor delivery schedules."
        ),
        "Fabrication & Assembly": (
            "Manufacture custom structural components, assemble subsystems, integrate harnesses, "
            "populate circuit boards, and build the flight unit. Includes workmanship inspections."
        ),
        "Integration & Functional Testing": (
            "Integrate all subsystems into the spacecraft bus, perform end-to-end functional tests, "
            "RF compatibility testing, deploy mechanism tests, and comprehensive systems checkout."
        ),
        "Environmental Testing (TVAC, Vibe, EMI)": (
            "Thermal vacuum cycling, vibration (sine and random), shock, EMI/EMC testing per "
            "launch vehicle ICD requirements. Includes pre- and post-environmental functional tests."
        ),
        "Environmental & Qualification Testing": (
            "Full qualification-level environmental testing including thermal vacuum, vibration, "
            "shock, EMI/EMC, and mission-specific tests. May include extended duration tests."
        ),
        "Experimental Payload Qualification": (
            "Additional qualification campaign for novel/experimental payload elements. "
            "Includes performance verification under flight-representative conditions."
        ),
        "Radiation Testing & Hardening Verification": (
            "Total ionizing dose (TID), single event effects (SEE), and displacement damage testing "
            "of critical components. Verify radiation design margins."
        ),
        "Extended Life Testing": (
            "Accelerated life testing and wear-out characterization for mechanisms, batteries, "
            "and other limited-life items to verify mission lifetime margins."
        ),
        "FCC / Regulatory Filing & Approval": (
            "Prepare and submit FCC application (Part 25.114, 25.122, 97, or 5 as applicable). "
            "Respond to information requests. Timeline highly variable by filing type and backlog."
        ),
        "IARU Frequency Coordination": (
            "Submit IARU satellite frequency coordination request (Form V40). Coordinate with "
            "amateur satellite community. Typical processing time 4-8 months."
        ),
        "IARU / ITU Frequency Coordination": (
            "International frequency coordination through IARU and/or ITU. Includes "
            "interference analysis, coordination meetings, and notification filing."
        ),
        "ITU Frequency Coordination & Filing": (
            "Submit Advance Publication Information (API), coordinate with affected administrations, "
            "file notification with ITU Radiocommunication Bureau."
        ),
        "Orbital Slot Coordination (ITU BR)": (
            "Coordinate geostationary orbital slot with ITU BR and potentially affected operators. "
            "This process can take 12-24+ months for contested positions."
        ),
        "ITAR / Export Control Review": (
            "Determine ITAR/EAR jurisdiction and classification. Obtain required export licenses "
            "or agreements (TAA, MLA). Establish technology control plans."
        ),
        "Launch Vehicle Procurement & Contracting": (
            "Evaluate launch options, negotiate launch services agreement (LSA), establish "
            "payload interface requirements, and secure a launch slot. Includes mission analysis."
        ),
        "Range Safety Review & Approval": (
            "Submit range safety package to launch range (e.g., 45th Space Wing, VSFB). "
            "Includes flight termination analysis, toxic/hazardous materials review, RF compatibility."
        ),
        "Pre-Ship Review & Shipping": (
            "Final spacecraft inspection, closeout photography, pack and ship to launch site. "
            "Pre-shipment review with launch provider to confirm readiness."
        ),
        "Launch Campaign & Integration": (
            "On-site activities at launch facility: spacecraft unpacking, inspection, fueling (if applicable), "
            "integration onto launch vehicle, final RF testing, launch rehearsal, and countdown."
        ),
    }

    for p in timeline["phases"]:
        desc = phase_descriptions.get(p["name"], "")
        if desc:
            elements.append(Paragraph(
                f'<b>{p["name"]}</b> ({p["start"].strftime("%b %Y")} — {p["end"].strftime("%b %Y")})',
                ParagraphStyle("PhaseTitle", parent=styles["Normal"],
                              fontSize=10, textColor=NAVY, spaceBefore=8, spaceAfter=2)
            ))
            elements.append(Paragraph(desc, styles["BodyCustom"]))

    # ── 4. Launch Vehicle Analysis ──
    elements.append(PageBreak())
    elements.append(Paragraph("4. Launch Vehicle Analysis", styles["Heading1Custom"]))
    elements.append(Paragraph(
        f'Based on the spacecraft mass ({timeline["mass_kg"]:.0f} kg) and target orbit '
        f'({mission.get("orbit_type", "LEO")}), the following launch vehicles are compatible:',
        styles["BodyCustom"]
    ))

    if timeline["launch_vehicles"]:
        lv_header = ["Vehicle", "Operator", "Capacity", "Cost ($M)", "Lead Time", "Status"]
        lv_rows = [lv_header]
        for v in timeline["launch_vehicles"]:
            cost_str = f'${v["cost_usd"]/1e6:.1f}M' if v.get("cost_usd") else "TBD"
            lead_str = f'{v["lead_time_months"]} mo' if v.get("lead_time_months") else "TBD"
            lv_rows.append([
                v["name"],
                v["operator"],
                f'{v["capacity_for_orbit"]:,.0f} kg',
                cost_str,
                lead_str,
                v["status"],
            ])

        lv_widths = [1.6*inch, 1.2*inch, 0.8*inch, 0.8*inch, 0.7*inch, 1.4*inch]
        lv_table = Table(lv_rows, colWidths=lv_widths, repeatRows=1)
        lv_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(lv_table)
        elements.append(Paragraph("Table 3 — Compatible Launch Vehicles", styles["Caption"]))

        # Vehicle comparison chart
        veh_buf = _generate_vehicle_comparison(timeline["launch_vehicles"])
        if veh_buf:
            elements.append(Image(veh_buf, width=6.5 * inch, height=3 * inch))
            elements.append(Paragraph("Figure 2 — Launch Vehicle Cost & Capacity Comparison", styles["Caption"]))

        # Top recommendation
        top_v = timeline["launch_vehicles"][0]
        elements.append(Paragraph("4.1 Recommended Primary Vehicle", styles["Heading2Custom"]))
        rec_text = (
            f'<b>{top_v["name"]}</b> by {top_v["operator"]} is the top-ranked match based on '
            f'capacity fit, operational status, and cost efficiency. '
            f'It offers {top_v["capacity_for_orbit"]:,.0f} kg to the target orbit '
            f'({top_v["mass_margin_pct"]:.0f}% mass margin). '
        )
        if top_v.get("cost_usd"):
            rec_text += f'Estimated launch cost is ${top_v["cost_usd"]/1e6:.1f}M. '
        if top_v.get("lead_time_months"):
            rec_text += f'Typical procurement lead time is {top_v["lead_time_months"]} months. '
        rec_text += f'Notes: {top_v.get("notes", "")}'
        elements.append(Paragraph(rec_text, styles["BodyCustom"]))
    else:
        elements.append(Paragraph(
            "No compatible launch vehicles were found for the specified mass and orbit. "
            "Consider rideshare options, mass reduction, or alternative orbit parameters.",
            styles["BodyCustom"]
        ))

    # ── 5. Probability of Completion ──
    elements.append(PageBreak())
    elements.append(Paragraph("5. Probability of On-Time Completion", styles["Heading1Custom"]))

    prob_pct = timeline["probability_pct"]
    if prob_pct >= 70:
        outlook_desc = "favorable"
        outlook_color = "#2E7D32"
    elif prob_pct >= 40:
        outlook_desc = "moderate — active risk management needed"
        outlook_color = "#F57F17"
    else:
        outlook_desc = "challenging — significant schedule risk"
        outlook_color = "#C62828"

    elements.append(Paragraph(
        f'The assessed probability of launching on or before '
        f'{timeline["target_launch_date"].strftime("%B %Y")} is '
        f'<b><font color="{outlook_color}">{prob_pct}%</font></b> '
        f'({outlook_desc}).',
        styles["BodyCustom"]
    ))

    # Gauge chart
    gauge_buf = _generate_probability_gauge(prob_pct)
    elements.append(Image(gauge_buf, width=3.5 * inch, height=2.1 * inch))
    elements.append(Paragraph("Figure 3 — On-Time Completion Probability", styles["Caption"]))

    # Risk factor table
    elements.append(Paragraph("5.1 Risk Factor Analysis", styles["Heading2Custom"]))
    elements.append(Paragraph(
        "The probability assessment considers the following factors. Positive values "
        "increase confidence; negative values decrease it.",
        styles["BodyCustom"]
    ))

    risk_header = ["Factor", "Impact", "Assessment"]
    risk_rows = [risk_header]
    for factor, impact, explanation in timeline["probability_reasons"]:
        impact_str = f"+{impact}" if impact > 0 else str(impact)
        risk_rows.append([factor, impact_str, explanation])

    risk_widths = [1.6*inch, 0.7*inch, 4.2*inch]
    risk_table = Table(risk_rows, colWidths=risk_widths, repeatRows=1)

    risk_style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for i, (_, impact, _) in enumerate(timeline["probability_reasons"]):
        row = i + 1
        if impact > 0:
            risk_style.append(("TEXTCOLOR", (1, row), (1, row), HexColor("#2E7D32")))
        elif impact < 0:
            risk_style.append(("TEXTCOLOR", (1, row), (1, row), HexColor("#C62828")))

    risk_table.setStyle(TableStyle(risk_style))
    elements.append(risk_table)
    elements.append(Paragraph("Table 4 — Probability Risk Factors", styles["Caption"]))

    # ── 6. Recommendations ──
    elements.append(Paragraph("6. Recommendations", styles["Heading1Custom"]))

    recommendations = []
    if margin < 0:
        recommendations.append(
            "<b>Schedule Acceleration Required:</b> The current timeline exceeds the target "
            f"launch date by approximately {abs(margin):.0f} months. Consider: increasing team size, "
            "parallel engineering tracks, early long-lead procurement, or adjusting the launch date."
        )
    if margin >= 0 and margin < crit * 0.15:
        recommendations.append(
            "<b>Limited Schedule Margin:</b> The current margin is thin. Identify and pre-mitigate "
            "critical-path risks. Consider initiating regulatory filings and launch procurement "
            "as early as possible to preserve flexibility."
        )
    if timeline["is_experimental"]:
        recommendations.append(
            "<b>Experimental Payload Risk:</b> Begin payload qualification testing as early as possible. "
            "Consider building an engineering model for early testing to decouple payload risk from "
            "the flight unit schedule."
        )
    if timeline["needs_export_control"]:
        recommendations.append(
            "<b>Export Control:</b> Initiate ITAR/EAR classification and license applications early. "
            "Export control delays can cascade to launch vehicle selection and international partner coordination."
        )

    operational_count = sum(1 for v in timeline["launch_vehicles"] if v["status"] == "Operational")
    if operational_count < 2:
        recommendations.append(
            "<b>Launch Vehicle Risk:</b> Limited operational vehicle options. Begin launch procurement "
            "dialogue early and consider backup options including rideshare or alternative orbits."
        )

    recommendations.append(
        "<b>Regulatory Filing:</b> Initiate FCC filing and frequency coordination in parallel with "
        "preliminary design. Regulatory approvals are often on the critical path and have "
        "unpredictable timelines."
    )

    if not recommendations:
        recommendations.append(
            "The timeline appears achievable with standard project management practices. "
            "Maintain regular schedule reviews and address risks as they emerge."
        )

    for rec in recommendations:
        elements.append(Paragraph(f"&bull; {rec}", styles["BodyCustom"]))
        elements.append(Spacer(1, 4))

    # ── 7. Assumptions & Caveats ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("7. Assumptions & Caveats", styles["Heading1Custom"]))
    caveats = [
        "Phase durations are based on industry averages for the selected satellite class and may vary "
        "significantly based on team experience, funding profile, and supply chain conditions.",
        "Parallel phase execution assumes adequate staffing and facilities to support concurrent activities.",
        "FCC processing times are estimates; actual timelines depend on application completeness, "
        "FCC backlog, and any requests for additional information.",
        "Launch vehicle costs and availability are based on publicly available data as of 2025 and "
        "are subject to change. Actual pricing requires a formal quote from the launch provider.",
        "The probability assessment is a heuristic estimate, not a rigorous Monte Carlo analysis. "
        "It should be used for planning guidance, not contractual commitments.",
        "This timeline does not account for funding gaps, organizational delays, force majeure events, "
        "or changes in regulatory requirements.",
    ]
    for c in caveats:
        elements.append(Paragraph(f"&bull; {c}", styles["BodyCustom"]))
        elements.append(Spacer(1, 2))

    # Build PDF
    doc.build(elements, canvasmaker=NumberedCanvas)
    return output_path
