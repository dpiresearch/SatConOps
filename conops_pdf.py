"""
ConOps PDF generator for satellite missions of all types.
Generates an FCC-compliant Concept of Operations document with diagrams, tables, and images.

References:
- ANSI/AIAA G-043A-2012: Guide for the Preparation of Operational Concept Documents
- IEEE 1362-1998: Concept of Operations Document Guide
- 47 CFR Part 25.114, 25.122: FCC Satellite Application Requirements
- 47 CFR Part 97.207: Amateur Space Station Requirements
- NASA CubeSat Launch Initiative (CSLI) guidance
- CubeSat Design Specification Rev 14.1 (Cal Poly / CubeSat.org)
- ITU Radio Regulations
- IARU Satellite Frequency Coordination (https://www.iaru.org/reference/satellites/)
- FCC-22-74: 5-Year Deorbit Rule (2022)
"""

import io
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from datetime import datetime
from typing import Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image,
)
from reportlab.pdfgen import canvas


SOURCES = {
    "fcc_part25": "47 CFR Part 25 — Satellite Communications (https://www.law.cornell.edu/cfr/text/47/part-25)",
    "fcc_25_114": "47 CFR 25.114 — Applications for Space Station Authorizations (https://www.law.cornell.edu/cfr/text/47/25.114)",
    "fcc_25_122": "47 CFR 25.122 — Streamlined Small Satellite Process (https://www.law.cornell.edu/cfr/text/47/25.122)",
    "fcc_part97": "47 CFR Part 97 — Amateur Radio Service (https://www.law.cornell.edu/cfr/text/47/part-97)",
    "fcc_97_207": "47 CFR 97.207 — Space Station (https://www.law.cornell.edu/cfr/text/47/97.207)",
    "aiaa_conops": "ANSI/AIAA G-043A-2012: Guide for the Preparation of Operational Concept Documents",
    "ieee_conops": "IEEE 1362-1998: IEEE Guide for Information Technology — System Definition — Concept of Operations Document",
    "cubesat_spec": "CubeSat Design Specification Rev 14.1 (https://www.cubesat.org/cubesatinfo)",
    "nasa_csli": "NASA CubeSat Launch Initiative Resources (https://www.nasa.gov/content/cubesat-launch-initiative-resources)",
    "nasa_gsfc": "NASA GSFC-STD-1001A: Flight Project Lifecycle Reviews (https://standards.nasa.gov/standard/GSFC/GSFC-STD-1001)",
    "iaru_sat": "IARU Satellite Frequency Coordination (https://www.iaru.org/reference/satellites/)",
    "fcc_debris": "FCC 5-Year Deorbit Rule, FCC-22-74 (2022)",
    "itu_rr": "ITU Radio Regulations (https://www.itu.int/pub/R-REG-RR)",
}


def _create_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        'DocTitle', parent=styles['Title'],
        fontSize=28, leading=34, spaceAfter=6, textColor=colors.HexColor('#1a237e'),
        fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        'DocSubtitle', parent=styles['Normal'],
        fontSize=16, leading=20, spaceAfter=20, textColor=colors.HexColor('#37474f'),
        fontName='Helvetica', alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        'SectionHeader', parent=styles['Heading1'],
        fontSize=16, leading=20, spaceBefore=20, spaceAfter=10,
        textColor=colors.HexColor('#1a237e'), fontName='Helvetica-Bold',
        borderWidth=1, borderColor=colors.HexColor('#1a237e'), borderPadding=4,
    ))
    styles.add(ParagraphStyle(
        'SubSection', parent=styles['Heading2'],
        fontSize=13, leading=16, spaceBefore=14, spaceAfter=6,
        textColor=colors.HexColor('#283593'), fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        'BodyText2', parent=styles['Normal'],
        fontSize=10, leading=14, spaceAfter=8, alignment=TA_JUSTIFY,
        fontName='Helvetica',
    ))
    styles.add(ParagraphStyle(
        'Caption', parent=styles['Normal'],
        fontSize=9, leading=11, spaceAfter=12, alignment=TA_CENTER,
        fontName='Helvetica-Oblique', textColor=colors.HexColor('#546e7a'),
    ))
    styles.add(ParagraphStyle(
        'BulletText', parent=styles['Normal'],
        fontSize=10, leading=14, spaceAfter=4, leftIndent=20, fontName='Helvetica',
    ))
    return styles


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _fig_to_image(fig, width=6*inch, height=4*inch) -> Image:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width, height=height)


def _make_table(data: List[List], col_widths=None, header_color='#1a237e'):
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_color)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#b0bec5')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(style)
    return t


# ── Diagram generators ──────────────────────────────────────────

def _generate_spacecraft_diagram(m: Dict) -> Image:
    fig, ax = plt.subplots(1, 1, figsize=(6, 5))
    ax.set_xlim(-5, 5)
    ax.set_ylim(-5, 5)
    ax.set_aspect('equal')

    sat_class = m.get("satellite_class", "Small Satellite")
    if "CubeSat" in sat_class:
        form = m.get("form_factor", "3U")
        if "1U" in form: w, h = 1.0, 1.0
        elif "2U" in form: w, h = 1.0, 2.0
        elif "6U" in form: w, h = 2.0, 3.0
        elif "12U" in form: w, h = 2.0, 6.0
        else: w, h = 1.0, 3.0
    elif "Micro" in sat_class or "Small" in sat_class:
        w, h = 2.0, 3.0
    elif "Medium" in sat_class:
        w, h = 3.0, 4.0
    else:
        w, h = 3.5, 4.5

    body = FancyBboxPatch((-w/2, -h/2), w, h, boxstyle="round,pad=0.05",
                          facecolor='#e3f2fd', edgecolor='#1565c0', linewidth=2)
    ax.add_patch(body)

    panel_w = w * 1.5
    panel_h = h * 0.5
    lp = plt.Rectangle((-w/2 - panel_w - 0.15, -panel_h/2), panel_w, panel_h,
                        facecolor='#1565c0', edgecolor='#0d47a1', linewidth=1.5, alpha=0.8)
    rp = plt.Rectangle((w/2 + 0.15, -panel_h/2), panel_w, panel_h,
                        facecolor='#1565c0', edgecolor='#0d47a1', linewidth=1.5, alpha=0.8)
    ax.add_patch(lp)
    ax.add_patch(rp)
    for x_start in [-w/2 - panel_w - 0.15, w/2 + 0.15]:
        for i in range(3):
            for j in range(2):
                cw, ch = panel_w / 3, panel_h / 2
                cell = plt.Rectangle((x_start + i*cw, -panel_h/2 + j*ch), cw, ch,
                                     facecolor='none', edgecolor='#0d47a1', linewidth=0.5, alpha=0.5)
                ax.add_patch(cell)

    ax.plot([0, 0], [h/2, h/2 + 0.8], 'k-', linewidth=2)
    ax.plot([-0.3, 0, 0.3], [h/2 + 0.8, h/2 + 1.1, h/2 + 0.8], 'k-', linewidth=2)

    payload_name = m.get("payload_type", "Payload")[:14]
    pp = FancyBboxPatch((-w/4, -h/4), w/2, h/3, boxstyle="round,pad=0.02",
                        facecolor='#fff9c4', edgecolor='#f57f17', linewidth=1.5)
    ax.add_patch(pp)
    ax.text(0, -h/4 + h/6, payload_name, ha='center', va='center', fontsize=8, fontweight='bold')

    for tx, ty in [(-w/2, -h/2+0.2), (w/2, -h/2+0.2), (-w/2, h/2-0.2), (w/2, h/2-0.2)]:
        ax.plot(tx, ty, 'rv', markersize=8)

    label = m.get("form_factor", sat_class) if "CubeSat" in sat_class else sat_class
    ax.text(0, -h/2 - 0.5, f'{label} Satellite Bus', ha='center', fontsize=10, fontweight='bold')
    ax.text(-w/2 - panel_w/2 - 0.15, panel_h/2 + 0.2, 'Solar Panel', ha='center', fontsize=8)
    ax.text(w/2 + panel_w/2 + 0.15, panel_h/2 + 0.2, 'Solar Panel', ha='center', fontsize=8)
    ax.text(0.4, h/2 + 1.0, 'Antenna', fontsize=8)

    ax.set_title(f'{m.get("mission_name", "Satellite")} — Spacecraft Configuration',
                 fontsize=13, fontweight='bold')
    ax.axis('off')
    fig.tight_layout()
    return _fig_to_image(fig, width=5*inch, height=4.2*inch)


def _generate_orbit_diagram(m: Dict) -> Image:
    fig, ax = plt.subplots(1, 1, figsize=(6, 6))
    ax.set_xlim(-2.8, 2.8)
    ax.set_ylim(-2.8, 2.8)
    ax.set_aspect('equal')

    earth = plt.Circle((0, 0), 1.0, color='#1565c0', alpha=0.8)
    ax.add_patch(earth)
    ax.text(0, 0, 'Earth', ha='center', va='center', color='white', fontsize=10, fontweight='bold')

    alt_km = _safe_float(m.get("orbit_altitude"), 500)
    orbit_type = m.get("orbit_type", "LEO")
    inc = _safe_float(m.get("orbit_inclination"), 97.4)

    if "GEO" in orbit_type.upper():
        r_display = 2.3
    elif alt_km > 2000:
        r_display = 2.0
    else:
        r_display = 1.0 + 0.5 * (alt_km / 600.0)

    theta = np.linspace(0, 2 * np.pi, 200)
    inc_rad = math.radians(inc)
    x_orbit = r_display * np.cos(theta)
    y_orbit = r_display * np.sin(theta) * math.cos(inc_rad * 0.3)

    ax.plot(x_orbit, y_orbit, 'g-', linewidth=2,
            label=f'{orbit_type} ({alt_km:.0f} km, {inc:.1f}°)')

    sa = np.pi / 4
    sx = r_display * np.cos(sa)
    sy = r_display * np.sin(sa) * math.cos(inc_rad * 0.3)
    ax.plot(sx, sy, 'r^', markersize=12, zorder=5)
    ax.annotate(m.get("mission_name", "Sat")[:15],
                xy=(sx, sy), xytext=(sx + 0.3, sy + 0.3),
                fontsize=9, fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='red'))

    gs_angle = -np.pi / 3
    gx = 1.0 * np.cos(gs_angle)
    gy = 1.0 * np.sin(gs_angle)
    ax.plot(gx, gy, 's', color='yellow', markersize=8, markeredgecolor='black', zorder=5)
    ax.plot([gx, sx], [gy, sy], 'y--', linewidth=1, alpha=0.6)
    ax.text(gx - 0.5, gy - 0.2, 'Ground\nStation', fontsize=8, ha='center')

    if "GEO" not in orbit_type.upper():
        period_min = 2 * np.pi * np.sqrt((6371 + alt_km)**3 / 398600.4418) / 60
        ax.text(-2.6, -2.5, f'Period: {period_min:.1f} min', fontsize=9)
    else:
        ax.text(-2.6, -2.5, 'Period: ~24 h (geostationary)', fontsize=9)
    ax.text(-2.6, -2.3, f'Alt: {alt_km:.0f} km | Inc: {inc:.1f}°', fontsize=9)

    ax.set_title('Orbital Configuration', fontsize=13, fontweight='bold')
    ax.legend(loc='upper left', fontsize=9)
    ax.axis('off')
    fig.tight_layout()
    return _fig_to_image(fig, width=4.5*inch, height=4.5*inch)


def _generate_mission_phases_diagram(m: Dict) -> Image:
    fig, ax = plt.subplots(1, 1, figsize=(10, 3))
    phases = [
        ("Pre-Launch\n& Integration", "#9e9e9e", 0.8),
        ("Launch &\nDeployment", "#f44336", 0.5),
        ("Early Ops /\nDetumble", "#ff9800", 0.8),
        ("Commissioning", "#ffc107", 1.0),
        ("Nominal\nOperations", "#4caf50", 3.0),
        ("Extended Ops\n(if applicable)", "#2196f3", 1.5),
        ("End-of-Life /\nDisposal", "#795548", 0.8),
    ]
    x = 0
    for i, (name, color, width) in enumerate(phases):
        rect = FancyBboxPatch((x, 0.3), width, 0.4, boxstyle="round,pad=0.02",
                               facecolor=color, edgecolor='white', linewidth=2, alpha=0.85)
        ax.add_patch(rect)
        ax.text(x + width/2, 0.5, name, ha='center', va='center',
                fontsize=7.5, fontweight='bold', color='white')
        if i < len(phases) - 1:
            ax.annotate('', xy=(x + width + 0.05, 0.5), xytext=(x + width - 0.05, 0.5),
                        arrowprops=dict(arrowstyle='->', color='black', lw=2))
        x += width + 0.15
    ax.set_xlim(-0.2, x + 0.2)
    ax.set_ylim(0, 1.0)
    ax.set_title('Mission Phase Timeline', fontsize=13, fontweight='bold', pad=10)
    ax.axis('off')
    fig.tight_layout()
    return _fig_to_image(fig, width=6.5*inch, height=2*inch)


def _generate_mode_diagram(m: Dict) -> Image:
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    ax.set_xlim(-1, 9)
    ax.set_ylim(-1, 7)
    modes = {
        "Safe Mode": (4, 6, '#f44336'),
        "Detumble": (1, 4, '#ff9800'),
        "Nominal": (4, 4, '#4caf50'),
        "Science /\nPayload": (7, 4, '#2196f3'),
        "Comms": (4, 2, '#9c27b0'),
        "Low Power": (1, 2, '#795548'),
        "Disposal": (7, 2, '#607d8b'),
    }
    for name, (cx, cy, color) in modes.items():
        box = FancyBboxPatch((cx-0.9, cy-0.4), 1.8, 0.8, boxstyle="round,pad=0.1",
                              facecolor=color, edgecolor='white', linewidth=2, alpha=0.85)
        ax.add_patch(box)
        ax.text(cx, cy, name, ha='center', va='center', fontsize=9, fontweight='bold', color='white')
    transitions = [
        ("Safe Mode", "Detumble"), ("Safe Mode", "Nominal"),
        ("Detumble", "Nominal"), ("Nominal", "Science /\nPayload"),
        ("Nominal", "Comms"), ("Nominal", "Low Power"),
        ("Nominal", "Disposal"), ("Low Power", "Safe Mode"),
        ("Science /\nPayload", "Nominal"), ("Comms", "Nominal"),
    ]
    for src, dst in transitions:
        sx, sy, _ = modes[src]
        dx, dy, _ = modes[dst]
        ax.annotate('', xy=(dx, dy), xytext=(sx, sy),
                     arrowprops=dict(arrowstyle='->', color='#37474f', lw=1.5,
                                     connectionstyle='arc3,rad=0.1'))
    ax.set_title('Operational Mode State Diagram', fontsize=13, fontweight='bold')
    ax.axis('off')
    fig.tight_layout()
    return _fig_to_image(fig, width=5.5*inch, height=4*inch)


def _generate_comm_diagram(m: Dict) -> Image:
    fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    ax.set_xlim(-1, 11)
    ax.set_ylim(-1, 7)

    sat_box = FancyBboxPatch((3.5, 5), 3, 1.2, boxstyle="round,pad=0.1",
                              facecolor='#1565c0', edgecolor='#0d47a1', linewidth=2)
    ax.add_patch(sat_box)
    ax.text(5, 5.6, f'{m.get("mission_name", "Satellite")[:18]}\nSpacecraft',
            ha='center', va='center', color='white', fontsize=10, fontweight='bold')

    gs_box = FancyBboxPatch((0, 0.5), 3, 1.2, boxstyle="round,pad=0.1",
                             facecolor='#2e7d32', edgecolor='#1b5e20', linewidth=2)
    ax.add_patch(gs_box)
    ax.text(1.5, 1.1, 'Ground Station\n' + m.get("ground_station", "Primary GS")[:20],
            ha='center', va='center', color='white', fontsize=9, fontweight='bold')

    moc_box = FancyBboxPatch((4, 0.5), 3, 1.2, boxstyle="round,pad=0.1",
                              facecolor='#e65100', edgecolor='#bf360c', linewidth=2)
    ax.add_patch(moc_box)
    ax.text(5.5, 1.1, 'Mission Operations\nCenter (MOC)',
            ha='center', va='center', color='white', fontsize=9, fontweight='bold')

    user_box = FancyBboxPatch((8, 0.5), 2.5, 1.2, boxstyle="round,pad=0.1",
                               facecolor='#6a1b9a', edgecolor='#4a148c', linewidth=2)
    ax.add_patch(user_box)
    ax.text(9.25, 1.1, 'End Users /\nData Archive',
            ha='center', va='center', color='white', fontsize=9, fontweight='bold')

    freq_up = m.get("uplink_freq", "435 MHz")
    freq_down = m.get("downlink_freq", "437 MHz")

    ax.annotate('', xy=(2.5, 1.7), xytext=(4.2, 5.0),
                arrowprops=dict(arrowstyle='->', color='#f44336', lw=2))
    ax.text(1.5, 3.5, f'Downlink\n{freq_down}', fontsize=8, color='#f44336', fontweight='bold')

    ax.annotate('', xy=(5.5, 5.0), xytext=(2.0, 1.7),
                arrowprops=dict(arrowstyle='->', color='#2196f3', lw=2))
    ax.text(5.2, 3.5, f'Uplink\n{freq_up}', fontsize=8, color='#2196f3', fontweight='bold')

    ax.annotate('', xy=(4, 1.1), xytext=(3, 1.1),
                arrowprops=dict(arrowstyle='<->', color='#37474f', lw=1.5))
    ax.annotate('', xy=(8, 1.1), xytext=(7, 1.1),
                arrowprops=dict(arrowstyle='->', color='#37474f', lw=1.5))

    ax.set_title('Communication Architecture', fontsize=13, fontweight='bold')
    ax.axis('off')
    fig.tight_layout()
    return _fig_to_image(fig, width=6*inch, height=3.8*inch)


def _generate_power_budget_diagram(m: Dict) -> Image:
    fig, ax = plt.subplots(1, 1, figsize=(7, 4))
    modes = ['Safe', 'Detumble', 'Nominal', 'Science', 'Comms', 'Low Power']
    power_gen = _safe_float(m.get("power_generation"), 20)

    base = [2, 3, 5, 7, 6, 2]
    scale = power_gen / 20.0
    power_values = [v * scale for v in base]

    bars = ax.bar(modes, power_values, color=['#f44336', '#ff9800', '#4caf50',
                                               '#2196f3', '#9c27b0', '#795548'],
                  edgecolor='white', linewidth=1.5, alpha=0.85)
    ax.axhline(y=power_gen, color='#1b5e20', linestyle='--', linewidth=2,
               label=f'Solar Generation ({power_gen:.0f} W)')
    batt = _safe_float(m.get("battery_capacity"), power_gen * 0.6)
    ax.axhline(y=batt, color='#e65100', linestyle=':', linewidth=2,
               label=f'Battery Capacity ({batt:.0f} Wh)')

    for bar, val in zip(bars, power_values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f'{val:.1f} W', ha='center', fontsize=9, fontweight='bold')

    ax.set_ylabel('Power (W)', fontsize=11)
    ax.set_title('Power Budget by Operational Mode', fontsize=13, fontweight='bold')
    ax.legend(fontsize=9, loc='upper right')
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    return _fig_to_image(fig, width=5.5*inch, height=3.2*inch)


def _generate_link_margin_diagram(m: Dict) -> Image:
    alt = _safe_float(m.get("orbit_altitude"), 500)
    elevations = [5, 10, 15, 20, 30, 45, 60, 90]
    margins_down = []
    margins_up = []

    dl_str = m.get("downlink_freq", "437") or "437"
    freq_mhz = _safe_float(dl_str.split()[0], 437)
    sc_tx = max(_safe_float(m.get("sc_tx_power"), 1), 0.001)
    gs_tx = max(_safe_float(m.get("gs_tx_power"), 20), 0.001)
    tx_gain = _safe_float((m.get("sc_ant_gain") or "0").split()[0], 0)
    rx_gain = _safe_float((m.get("gs_ant_gain") or "14").split()[0], 14)
    noise_bw = max(_safe_float(m.get("data_rate"), 9600), 1)

    for el in elevations:
        slant = alt / math.sin(math.radians(el))
        fspl = 20*math.log10(max(slant*1000, 1)) + 20*math.log10(max(freq_mhz*1e6, 1)) - 147.55
        atm_loss = 2.0 if el < 10 else (1.0 if el < 30 else 0.5)
        tx_pow_dbm = 10 * math.log10(sc_tx * 1000)
        received = tx_pow_dbm + tx_gain + rx_gain - fspl - atm_loss - 1.0
        noise_floor = -174 + 10*math.log10(noise_bw) + 3
        margin = received - noise_floor - 10
        margins_down.append(margin)

        gs_pow_dbm = 10 * math.log10(gs_tx * 1000)
        received_up = gs_pow_dbm + rx_gain + tx_gain - fspl - atm_loss - 1.0
        margin_up = received_up - noise_floor - 10
        margins_up.append(margin_up)

    fig, ax = plt.subplots(1, 1, figsize=(6, 4))
    ax.plot(elevations, margins_down, 'b-o', linewidth=2, markersize=6, label='Downlink')
    ax.plot(elevations, margins_up, 'r-s', linewidth=2, markersize=6, label='Uplink')
    ax.axhline(y=3, color='orange', linestyle='--', linewidth=1.5, label='Min Margin (3 dB)')
    ax.axhline(y=6, color='green', linestyle='--', linewidth=1.5, label='Design Margin (6 dB)')
    ax.fill_between(elevations, 3, [min(d, u) for d, u in zip(margins_down, margins_up)],
                     where=[min(d, u) > 3 for d, u in zip(margins_down, margins_up)],
                     alpha=0.1, color='green')
    ax.set_xlabel('Elevation Angle (°)', fontsize=11)
    ax.set_ylabel('Link Margin (dB)', fontsize=11)
    ax.set_title('Link Margin vs. Elevation Angle', fontsize=13, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return _fig_to_image(fig, width=5.5*inch, height=3.5*inch)


# ── Page numbering canvas ────────────────────────────────────────

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _draw_page_number(self, page_count):
        self.saveState()
        self.setFont('Helvetica', 8)
        self.setFillColor(colors.HexColor('#78909c'))
        self.drawRightString(letter[0] - 0.75*inch, 0.5*inch,
                             f"Page {self._pageNumber} of {page_count}")
        self.drawString(0.75*inch, 0.5*inch, "DISTRIBUTION: LIMITED — PRE-DECISIONAL")
        self.setStrokeColor(colors.HexColor('#b0bec5'))
        self.line(0.75*inch, 0.65*inch, letter[0] - 0.75*inch, 0.65*inch)
        self.restoreState()


# ── Main PDF generator ───────────────────────────────────────────

def generate_conops_pdf(m: Dict, output_path: str):
    """Generate the complete ConOps PDF for any satellite type."""
    styles = _create_styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.85*inch,
    )
    story = []
    mn = m.get("mission_name", "Satellite Mission")
    org = m.get("organization", "Organization")
    today = datetime.now().strftime("%B %d, %Y")
    version = m.get("version", "1.0")
    sat_class = m.get("satellite_class", "Small Satellite")

    # ── Title Page ──
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph("Concept of Operations", styles['DocTitle']))
    story.append(Paragraph(mn, styles['DocTitle']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(org, styles['DocSubtitle']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"Document Version {version} — {today}", styles['DocSubtitle']))
    story.append(Spacer(1, 0.5*inch))
    story.append(_make_table([
        ["Field", "Value"],
        ["Document Type", "Concept of Operations (ConOps)"],
        ["Classification", "Unclassified / FOUO"],
        ["Distribution", "Limited — Pre-Decisional"],
        ["Prepared By", org],
        ["Date", today],
        ["Satellite Class", sat_class],
        ["FCC License Type", m.get("fcc_license_type", "Part 25.114 (Standard Application)")],
    ], col_widths=[2.5*inch, 4*inch]))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(
        "This document has been prepared in accordance with ANSI/AIAA G-043A-2012, "
        "IEEE 1362-1998, and the requirements of 47 CFR Parts 25 and 97 of the "
        "Federal Communications Commission (FCC) regulations.",
        styles['BodyText2']))
    story.append(PageBreak())

    # ── Revision History + TOC ──
    story.append(Paragraph("Revision History", styles['SectionHeader']))
    story.append(_make_table([
        ["Version", "Date", "Author", "Description"],
        [version, today, m.get("author", "Mission Team"), "Initial release"],
    ], col_widths=[1*inch, 1.5*inch, 2*inch, 2.5*inch]))
    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph("Table of Contents", styles['SectionHeader']))
    toc = [
        "1.0 Introduction", "2.0 Mission Overview", "3.0 Space Segment Description",
        "4.0 Orbit Description", "5.0 Mission Phases", "6.0 Operational Modes",
        "7.0 Communication Architecture", "8.0 Ground Segment",
        "9.0 Command and Data Handling", "10.0 Power Budget Analysis",
        "11.0 Orbital Debris Mitigation Plan", "12.0 End-of-Life Disposal",
        "13.0 Risk Assessment and Contingency Operations",
        "14.0 Regulatory Compliance Summary", "15.0 References",
        "Appendix A: Link Budget Analysis",
        "Appendix B: FCC Cross-Reference Matrix",
        "Appendix C: Acronyms and Abbreviations",
    ]
    for entry in toc:
        story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{entry}", styles['BodyText2']))
    story.append(PageBreak())

    # ═══════ Section 1: Introduction ═══════
    story.append(Paragraph("1.0 Introduction", styles['SectionHeader']))
    story.append(Paragraph("1.1 Purpose and Scope", styles['SubSection']))
    story.append(Paragraph(
        f"This Concept of Operations (ConOps) document describes the operational concept for the "
        f"{mn} mission. It provides a comprehensive description of the mission objectives, system "
        f"architecture, operational modes, communication architecture, and disposal plan. This document "
        f"serves as the primary operational reference for FCC licensing under "
        f"{m.get('fcc_license_type', '47 CFR Part 25')} and supports frequency coordination "
        f"with the IARU and ITU.", styles['BodyText2']))
    story.append(Paragraph(
        "The ConOps is prepared in accordance with ANSI/AIAA G-043A-2012 "
        "(Guide for the Preparation of Operational Concept Documents) and IEEE 1362-1998.",
        styles['BodyText2']))

    story.append(Paragraph("1.2 Mission Objectives", styles['SubSection']))
    for obj in m.get("objectives", "Demonstrate satellite technology.").split('\n'):
        obj = obj.strip()
        if obj:
            story.append(Paragraph(f"&bull; {obj}", styles['BulletText']))

    story.append(Paragraph("1.3 Applicable Documents and Standards", styles['SubSection']))
    story.append(_make_table([
        ["Reference", "Title"],
        ["47 CFR 25.114", "Applications for Space Station Authorizations"],
        ["47 CFR 25.122", "Streamlined Small Satellite Authorization Process"],
        ["47 CFR 97.207", "Space Station (Amateur Radio)"],
        ["ANSI/AIAA G-043A-2012", "Guide for Operational Concept Documents"],
        ["IEEE 1362-1998", "Concept of Operations Document Guide"],
        ["CDS Rev 14.1", "CubeSat Design Specification (Cal Poly)"],
        ["NASA-STD-8719.14", "Process for Limiting Orbital Debris"],
        ["ITU Radio Regulations", "International Frequency Coordination"],
    ], col_widths=[2*inch, 5*inch]))

    story.append(Paragraph("1.4 Regulatory Framework", styles['SubSection']))
    fcc_type = m.get("fcc_license_type", "Part 25.114")
    if "25.122" in fcc_type:
        story.append(Paragraph(
            f"This mission will operate under FCC Part 25.122 (Streamlined Small Satellite Process). "
            f"Per 47 CFR 25.122, the mission meets the following eligibility criteria: "
            f"(1) single space station, (2) NGSO orbit, (3) operational lifetime of 6 years or less, "
            f"(4) mass of 180 kg or less, (5) minimum dimension of 10 cm or larger, and "
            f"(6) deployed at or below 600 km altitude.", styles['BodyText2']))
    elif "97" in fcc_type:
        story.append(Paragraph(
            f"This mission will operate under FCC Part 97 (Amateur Radio Service). "
            f"Per 47 CFR 97.207, the spacecraft will be capable of ceasing transmissions via "
            f"telecommand when ordered by the FCC. Three written notifications to the FCC Space Bureau "
            f"are required: pre-space (≤90 days before integration), in-space (within 7 days of first "
            f"transmission), and post-space (within 3 months of transmission termination).",
            styles['BodyText2']))
    else:
        story.append(Paragraph(
            f"This mission will operate under FCC Part 25.114 (Standard Application). "
            f"The application will include all required information per 47 CFR 25.114, including "
            f"orbital parameters, frequency information, system operations narrative, interference "
            f"analysis, and orbital debris mitigation plan.", styles['BodyText2']))
    story.append(Paragraph(
        "The FCC requires compliance with orbital debris mitigation rules, including the 5-year "
        "post-mission deorbit requirement (FCC-22-74).", styles['BodyText2']))
    story.append(PageBreak())

    # ═══════ Section 2: Mission Overview ═══════
    story.append(Paragraph("2.0 Mission Overview", styles['SectionHeader']))
    story.append(Paragraph("2.1 Mission Description and Rationale", styles['SubSection']))
    story.append(Paragraph(m.get("mission_description",
        f"The {mn} mission is a {sat_class} designed to operate in "
        f"{m.get('orbit_type', 'low Earth orbit')} at {m.get('orbit_altitude', '500')} km altitude."),
        styles['BodyText2']))

    story.append(Paragraph("2.2 Stakeholders and Responsibilities", styles['SubSection']))
    story.append(_make_table([
        ["Stakeholder", "Role", "Responsibility"],
        [org, "Mission Owner", "Overall mission management and operations"],
        [m.get("launch_provider", "Launch Provider TBD"), "Launch Services",
         "Launch vehicle integration and deployment"],
        ["FCC", "Regulatory Authority", "Spectrum licensing and debris compliance"],
        [m.get("ground_station", "Ground Station Operator"), "Ground Segment",
         "Communication and command operations"],
    ], col_widths=[2*inch, 1.5*inch, 3.5*inch]))

    story.append(Paragraph("2.3 Mission Success Criteria", styles['SubSection']))
    for c in m.get("success_criteria",
                   "Achieve stable orbit\nEstablish comm link\nComplete payload ops").split('\n'):
        c = c.strip()
        if c:
            story.append(Paragraph(f"&bull; {c}", styles['BulletText']))

    story.append(Paragraph("2.4 Mission Constraints and Assumptions", styles['SubSection']))
    mass_str = m.get("spacecraft_mass", "N/A")
    lifetime_str = m.get("mission_lifetime", "N/A")
    story.append(Paragraph(
        f"<b>Constraints:</b> Mission lifetime shall not exceed {lifetime_str} years. "
        f"Spacecraft mass is {mass_str} kg. "
        f"All transmissions must be capable of immediate cessation via ground command.",
        styles['BodyText2']))
    story.append(Paragraph(
        "<b>Assumptions:</b> Launch vehicle will deliver to target orbit within specified tolerances. "
        "Ground station availability meets minimum contact requirements. "
        "Solar power generation is sufficient for all operational modes.",
        styles['BodyText2']))

    story.append(Paragraph("2.5 Mission Timeline", styles['SubSection']))
    story.append(_make_table([
        ["Phase", "Duration", "Target Date"],
        ["Design & Development", "12-24 months", "In progress"],
        ["Integration & Test", "3-6 months", "TBD"],
        ["FCC Filing & Coordination", "6-12 months", "TBD"],
        ["Launch Readiness Review", "1 month", "TBD"],
        ["Launch", "—", m.get("target_launch_date", "TBD")],
        ["Nominal Operations", f"{lifetime_str} years",
         f"L + {lifetime_str} years"],
        ["End-of-Life Disposal", "< 5 years post-mission", "Per FCC-22-74"],
    ], col_widths=[2.5*inch, 2*inch, 2.5*inch]))
    story.append(PageBreak())

    # ═══════ Section 3: Space Segment ═══════
    story.append(Paragraph("3.0 Space Segment Description", styles['SectionHeader']))
    story.append(Paragraph("3.1 Spacecraft Configuration", styles['SubSection']))
    story.append(_generate_spacecraft_diagram(m))
    story.append(Paragraph(f"Figure 1: {mn} spacecraft configuration diagram", styles['Caption']))

    sc_params = [
        ["Parameter", "Value"],
        ["Satellite Class", sat_class],
    ]
    if "CubeSat" in sat_class:
        sc_params.append(["Form Factor", m.get("form_factor", "3U")])
    sc_params += [
        ["Mass", f"{mass_str} kg"],
        ["Dimensions", m.get("dimensions", "N/A")],
        ["Design Life", f"{lifetime_str} years"],
        ["Attitude Control", m.get("adcs", "N/A")],
        ["Propulsion", m.get("propulsion", "None / N/A")],
        ["Power System", m.get("power_system", "Solar panels + battery")],
        ["On-Board Computer", m.get("obc", "N/A")],
        ["Unique Telemetry Marker", "Embedded in downlink beacon — per 47 CFR 25.122"],
    ]
    story.append(_make_table(sc_params, col_widths=[2.5*inch, 4.5*inch]))
    story.append(Paragraph("Table 1: Spacecraft key parameters", styles['Caption']))

    story.append(Paragraph("3.2 Subsystem Summary", styles['SubSection']))
    story.append(_make_table([
        ["Subsystem", "Description", "Heritage / TRL"],
        ["EPS", m.get("power_system", "Solar + battery"), m.get("eps_trl", "TRL 7-8")],
        ["ADCS", m.get("adcs", "TBD"), m.get("adcs_trl", "TRL 7")],
        ["C&DH", m.get("obc", "TBD"), m.get("cdh_trl", "TRL 8")],
        ["Comms", f'{m.get("comm_system", "Radio transceiver")}, {m.get("data_rate", "9600")} bps',
         m.get("comms_trl", "TRL 8")],
        ["Thermal", m.get("thermal", "Passive (MLI + coatings)"), m.get("thermal_trl", "TRL 9")],
        ["Propulsion", m.get("propulsion", "None"), m.get("prop_trl", "N/A")],
        ["Payload", m.get("payload_type", "TBD"), m.get("payload_trl", "TRL 5-6")],
    ], col_widths=[1.2*inch, 3.5*inch, 2.3*inch]))

    story.append(Paragraph("3.3 Payload Description", styles['SubSection']))
    story.append(Paragraph(m.get("payload_description",
        f"The primary payload is a {m.get('payload_type', 'sensor')} designed for "
        f"{m.get('payload_purpose', 'technology demonstration')}."),
        styles['BodyText2']))
    story.append(PageBreak())

    # ═══════ Section 4: Orbit ═══════
    story.append(Paragraph("4.0 Orbit Description", styles['SectionHeader']))
    story.append(Paragraph("4.1 Orbital Parameters", styles['SubSection']))
    alt = _safe_float(m.get("orbit_altitude"), 500)
    inc = _safe_float(m.get("orbit_inclination"), 97.4)
    orbit_type = m.get("orbit_type", "LEO")
    mu = 398600.4418
    r = 6371.0 + alt
    period_s = 2 * math.pi * math.sqrt(r**3 / mu)
    period_min = period_s / 60
    v_orbital = math.sqrt(mu / r)
    orbits_per_day = 86400 / period_s

    orbit_params = [
        ["Parameter", "Value"],
        ["Orbit Type", orbit_type],
        ["Altitude", f"{alt:.0f} km"],
        ["Inclination", f"{inc:.1f}°"],
        ["Eccentricity", m.get("eccentricity", "~0 (near-circular)")],
        ["RAAN", m.get("raan", "TBD")],
        ["Orbital Period", f"{period_min:.1f} minutes"],
        ["Orbital Velocity", f"{v_orbital:.2f} km/s"],
        ["Orbits per Day", f"~{orbits_per_day:.1f}"],
    ]
    if "SSO" in orbit_type or "Sun" in orbit_type:
        orbit_params.append(["LTAN", m.get("ltan", "TBD")])
    story.append(_make_table(orbit_params, col_widths=[2.5*inch, 4.5*inch]))

    story.append(_generate_orbit_diagram(m))
    story.append(Paragraph("Figure 2: Orbital configuration diagram", styles['Caption']))

    story.append(Paragraph("4.2 Eclipse Analysis", styles['SubSection']))
    eclipse_frac = 0.35 if alt < 600 else (0.37 if alt < 2000 else 0.0)
    if "GEO" in orbit_type.upper():
        story.append(Paragraph(
            "In geostationary orbit, the spacecraft will experience eclipse seasons near the equinoxes, "
            "with maximum eclipse duration of approximately 72 minutes. The power system is sized to "
            "sustain all essential subsystems through eclipse.", styles['BodyText2']))
    else:
        eclipse_min = eclipse_frac * period_min
        story.append(Paragraph(
            f"At {alt:.0f} km altitude, the spacecraft will experience approximately "
            f"{eclipse_min:.1f} minutes of eclipse per {period_min:.1f}-minute orbit "
            f"(~{eclipse_frac*100:.0f}% duty cycle). The power system is sized to sustain "
            f"all essential subsystems through eclipse.", styles['BodyText2']))

    story.append(Paragraph("4.3 Orbital Decay Analysis", styles['SubSection']))
    if alt <= 400:
        decay = "< 2 years (natural decay)"
    elif alt <= 500:
        decay = "3-7 years (natural decay, solar activity dependent)"
    elif alt <= 600:
        decay = "7-15 years (may require drag augmentation)"
    elif alt <= 2000:
        decay = "Decades to centuries (propulsive deorbit required)"
    else:
        decay = "N/A — orbit above LEO regime"

    story.append(Paragraph(
        f"Estimated natural orbital decay time at {alt:.0f} km: {decay}. "
        f"{'The spacecraft will comply with the FCC 5-year post-mission disposal requirement.' if alt <= 450 else 'Active measures may be required to meet the FCC 5-year post-mission disposal requirement (FCC-22-74).'}",
        styles['BodyText2']))
    story.append(PageBreak())

    # ═══════ Section 5: Mission Phases ═══════
    story.append(Paragraph("5.0 Mission Phases", styles['SectionHeader']))
    story.append(_generate_mission_phases_diagram(m))
    story.append(Paragraph("Figure 3: Mission phase timeline", styles['Caption']))

    phases_detail = [
        ("5.1 Pre-Launch (Integration & Testing)",
         "Final spacecraft integration, environmental testing (vibration, thermal vacuum), "
         "end-to-end communication testing, and launch vehicle integration. "
         "FCC license application and IARU frequency coordination must be completed prior to launch."),
        ("5.2 Launch and Deployment",
         f"The spacecraft will be launched via {m.get('launch_provider', 'the selected launch provider')}. "
         "Post-deployment, the spacecraft will enter a pre-programmed inhibit period before "
         "activating any transmitters."),
        ("5.3 Early Operations / Detumbling",
         "Upon deployment, the ADCS will execute detumbling to reduce tip-off rates. "
         "Initial beacon transmission will commence after the inhibit period. "
         "Ground station acquisition is expected within the first 24-48 hours."),
        ("5.4 Commissioning",
         "Systematic checkout of all subsystems over approximately 2-4 weeks, including "
         "ADCS calibration, communication link verification, payload checkout, and flight "
         "software validation."),
        ("5.5 Nominal Operations",
         f"Primary mission operations lasting {m.get('mission_lifetime', 'N/A')} years. "
         "The spacecraft will alternate between science data collection, data downlink, and "
         "housekeeping modes."),
        ("5.6 End-of-Life / Decommissioning",
         "Upon mission completion, the spacecraft will enter disposal mode. "
         "All stored energy will be passivated. The spacecraft must deorbit within "
         "5 years per FCC-22-74."),
    ]
    for title, desc in phases_detail:
        story.append(Paragraph(title, styles['SubSection']))
        story.append(Paragraph(desc, styles['BodyText2']))
    story.append(PageBreak())

    # ═══════ Section 6: Operational Modes ═══════
    story.append(Paragraph("6.0 Operational Modes", styles['SectionHeader']))
    story.append(_generate_mode_diagram(m))
    story.append(Paragraph("Figure 4: Operational mode state transition diagram", styles['Caption']))

    story.append(_make_table([
        ["Mode", "Description", "Power (W)", "Duration", "ADCS State"],
        ["Safe Mode", "Minimum power, beacon only, sun-pointing", "Low", "Until recovery", "Sun-pointing"],
        ["Detumble", "Reduce angular rates post-deployment", "Low-Med", "Min to hours", "B-dot"],
        ["Nominal", "Standard housekeeping and attitude control", "Medium", "Default", "3-axis"],
        ["Science/Payload", "Active payload data collection", "High", "Per schedule", "Nadir/Target"],
        ["Communication", "Ground station pass, uplink/downlink", "Med-High", "~10 min/pass", "GS tracking"],
        ["Low Power", "Battery conservation during eclipse", "Low", "Eclipse", "Coarse"],
        ["Disposal", "Deorbit maneuver / passivation", "Medium", "One-time", "As required"],
    ], col_widths=[1.1*inch, 2.2*inch, 0.8*inch, 1.1*inch, 1.3*inch]))
    story.append(Paragraph("Table 2: Operational modes summary", styles['Caption']))

    story.append(Paragraph("6.1 Mode Transition Logic", styles['SubSection']))
    story.append(Paragraph(
        "Mode transitions are governed by the onboard flight software. Safe Mode is the highest "
        "priority and can be entered from any mode upon detection of an anomaly (under-voltage, "
        "communication timeout, attitude error exceedance). Ground command can override any mode "
        "transition.", styles['BodyText2']))
    story.append(PageBreak())

    # ═══════ Section 7: Communication Architecture ═══════
    story.append(Paragraph("7.0 Communication Architecture", styles['SectionHeader']))
    story.append(Paragraph(
        "<i>Per 47 CFR 25.114(d)(1) and 25.122(a), this section provides the required narrative "
        "description of the communication system operations, frequencies, and spectrum-sharing strategy.</i>",
        styles['BodyText2']))
    story.append(_generate_comm_diagram(m))
    story.append(Paragraph("Figure 5: Communication architecture diagram", styles['Caption']))

    story.append(Paragraph("7.1 Frequency Plan", styles['SubSection']))
    story.append(_make_table([
        ["Parameter", "Uplink", "Downlink"],
        ["Frequency", m.get("uplink_freq", "TBD"), m.get("downlink_freq", "TBD")],
        ["Bandwidth", m.get("uplink_bw", "TBD"), m.get("downlink_bw", "TBD")],
        ["Modulation", m.get("modulation", "TBD"), m.get("modulation", "TBD")],
        ["Data Rate", f'{m.get("data_rate", "TBD")} bps', f'{m.get("data_rate", "TBD")} bps'],
        ["Protocol", m.get("protocol", "TBD"), m.get("protocol", "TBD")],
        ["Polarization", m.get("polarization", "RHCP"), m.get("polarization", "RHCP")],
        ["EIRP", m.get("eirp", "TBD"), "—"],
    ], col_widths=[1.8*inch, 2.6*inch, 2.6*inch]))

    story.append(Paragraph("7.2 Spectrum Sharing Strategy", styles['SubSection']))
    story.append(Paragraph(
        f"The {mn} mission is designed to share spectrum without constraining future satellite "
        f"or terrestrial operators. The spacecraft uses narrowband transmissions with duty-cycled "
        f"operation (active only during scheduled ground passes). IARU frequency coordination will "
        f"be completed prior to launch.", styles['BodyText2']))

    story.append(Paragraph("7.3 Transmission Cessation Capability", styles['SubSection']))
    story.append(Paragraph(
        "Per 47 CFR 25.122(a) and 97.207, the spacecraft is capable of immediate cessation "
        "of all radio transmissions upon ground command. The telecommand link provides a "
        "dedicated 'TX OFF' command with highest priority in the command processing queue.",
        styles['BodyText2']))

    story.append(Paragraph("7.4 Link Budget Summary", styles['SubSection']))
    story.append(_make_table([
        ["Parameter", "Uplink", "Downlink"],
        ["Tx Power", m.get("gs_tx_power", "TBD"), m.get("sc_tx_power", "TBD")],
        ["Tx Antenna Gain", m.get("gs_ant_gain", "TBD"), m.get("sc_ant_gain", "TBD")],
        ["Rx Antenna Gain", m.get("sc_ant_gain", "TBD"), m.get("gs_ant_gain", "TBD")],
        ["System Noise Temp", "1000 K", "200 K"],
        ["Required Eb/N0", "10 dB", "10 dB"],
        ["Link Margin", "> 6 dB", "> 6 dB"],
    ], col_widths=[2.2*inch, 2.4*inch, 2.4*inch]))
    story.append(Paragraph("Table 3: Link budget summary (see Appendix A for analysis)", styles['Caption']))
    story.append(PageBreak())

    # ═══════ Section 8: Ground Segment ═══════
    story.append(Paragraph("8.0 Ground Segment", styles['SectionHeader']))
    story.append(Paragraph("8.1 Ground Station Description", styles['SubSection']))
    story.append(Paragraph(
        f"The primary ground station is located at {m.get('gs_location', 'TBD')}. "
        f"The station is equipped with a {m.get('gs_antenna', 'tracking antenna')} and "
        f"{m.get('gs_radio', 'transceiver')}. The ground station supports both manual and "
        f"automated pass operations.", styles['BodyText2']))

    story.append(Paragraph("8.2 Contact Schedule", styles['SubSection']))
    ppd = int(_safe_float(m.get("passes_per_day"), 4))
    apd = int(_safe_float(m.get("avg_pass_duration"), 10))
    daily_contact = ppd * apd
    story.append(Paragraph(
        f"The ground station will have approximately {ppd} passes per day with an average "
        f"duration of {apd} minutes (total daily contact time: ~{daily_contact} minutes).",
        styles['BodyText2']))

    story.append(Paragraph("8.3 Data Budget", styles['SubSection']))
    data_rate = int(_safe_float(m.get("data_rate"), 9600))
    daily_mb = daily_contact * 60 * data_rate / 8 / 1024 / 1024
    story.append(_make_table([
        ["Parameter", "Value"],
        ["Downlink Data Rate", f"{data_rate} bps"],
        ["Passes per Day", str(ppd)],
        ["Daily Downlink Capacity", f"~{daily_mb:.1f} MB"],
        ["Daily Payload Data Generated", m.get("daily_data_gen", "TBD")],
    ], col_widths=[3*inch, 4*inch]))
    story.append(PageBreak())

    # ═══════ Section 9: C&DH ═══════
    story.append(Paragraph("9.0 Command and Data Handling", styles['SectionHeader']))
    story.append(Paragraph("9.1 Command Protocol", styles['SubSection']))
    story.append(Paragraph(
        f"Telecommands are transmitted via the uplink ({m.get('uplink_freq', 'TBD')}) using "
        f"{m.get('protocol', 'AX.25')} protocol. Commands are authenticated to prevent "
        f"unauthorized execution. Per 47 CFR 97.211, encrypted telecommand is permitted.",
        styles['BodyText2']))

    story.append(Paragraph("9.2 Telemetry and Health Monitoring", styles['SubSection']))
    story.append(Paragraph(
        "The spacecraft transmits periodic health beacons containing: battery voltage, solar panel "
        "current, temperatures, ADCS state, mode, and error flags. A unique signal-based telemetry "
        "marker (per 47 CFR 25.122) is embedded in every downlink frame.", styles['BodyText2']))

    story.append(Paragraph("9.3 Autonomy and Fault Management", styles['SubSection']))
    story.append(Paragraph(
        "The flight software implements a three-tier fault management architecture: "
        "(1) hardware watchdog timer, (2) software FDIR for subsystem anomalies, and "
        "(3) mission-level safe mode entry upon detection of critical faults.",
        styles['BodyText2']))
    story.append(PageBreak())

    # ═══════ Section 10: Power Budget ═══════
    story.append(Paragraph("10.0 Power Budget Analysis", styles['SectionHeader']))
    story.append(Paragraph(
        "This section presents the power generation and consumption analysis for each "
        "operational mode.", styles['BodyText2']))
    story.append(_generate_power_budget_diagram(m))
    story.append(Paragraph("Figure 6: Power budget by operational mode", styles['Caption']))

    pg = _safe_float(m.get("power_generation"), 20)
    bc = _safe_float(m.get("battery_capacity"), pg * 0.6)
    story.append(_make_table([
        ["Parameter", "Value"],
        ["Peak Solar Generation", f"{pg:.0f} W"],
        ["Battery Capacity", f"{bc:.0f} Wh"],
        ["Battery Type", m.get("battery_type", "Li-ion")],
        ["Solar Panel Area", m.get("solar_area", "TBD")],
        ["Eclipse Duration (per orbit)", f"{eclipse_frac*period_min:.1f} min" if "GEO" not in orbit_type.upper() else "Up to 72 min (equinox)"],
    ], col_widths=[3*inch, 4*inch]))
    story.append(PageBreak())

    # ═══════ Section 11: Debris Mitigation ═══════
    story.append(Paragraph("11.0 Orbital Debris Mitigation Plan", styles['SectionHeader']))
    story.append(Paragraph(
        "<i>Per 47 CFR 25.114(d)(14) and FCC-22-74 (5-year deorbit rule).</i>",
        styles['BodyText2']))

    story.append(Paragraph("11.1 Operational Debris Release", styles['SubSection']))
    story.append(Paragraph(
        "No debris will be released during normal mission operations. All deployment mechanisms "
        "use captive fasteners.", styles['BodyText2']))

    story.append(Paragraph("11.2 Collision Risk Assessment", styles['SubSection']))
    story.append(_make_table([
        ["Requirement", "Threshold", "Assessment", "Compliance"],
        ["Small debris collision (<10 cm)", "P < 0.01", "TBD (NASA DAS)", "Expected compliant"],
        ["Large object collision (>10 cm)", "P < 0.001", "TBD (NASA DAS)", "Expected compliant"],
        ["Accidental explosion", "Minimize probability", "Passivation at EOL", "Compliant"],
    ], col_widths=[2*inch, 1.3*inch, 1.7*inch, 1.3*inch]))

    story.append(Paragraph("11.3 Trackability", styles['SubSection']))
    story.append(Paragraph(
        f"The {mn} spacecraft meets minimum dimension requirements for tracking by the "
        f"18th Space Defense Squadron Space Surveillance Network. The spacecraft will be "
        f"registered with the U.S. Space Command catalog.", styles['BodyText2']))

    story.append(Paragraph("11.4 Conjunction Assessment and Response", styles['SubSection']))
    story.append(Paragraph(
        "The mission operations team will subscribe to conjunction data messages (CDMs) from the "
        "18th Space Defense Squadron. Ephemeris data will be shared with the Space Surveillance "
        "Network to support conjunction screening.", styles['BodyText2']))
    story.append(PageBreak())

    # ═══════ Section 12: End-of-Life ═══════
    story.append(Paragraph("12.0 End-of-Life Disposal", styles['SectionHeader']))
    story.append(Paragraph(
        "<i>Per 47 CFR 25.114(d)(14) and FCC-22-74 (5-year deorbit rule).</i>",
        styles['BodyText2']))

    story.append(Paragraph("12.1 Deorbit Method", styles['SubSection']))
    disposal = m.get("disposal_method", "TBD")
    story.append(Paragraph(f"Disposal method: {disposal}.", styles['BodyText2']))

    story.append(_make_table([
        ["Parameter", "Value"],
        ["Disposal Method", disposal],
        ["Post-Mission Orbital Lifetime", "< 5 years (per FCC-22-74)"],
        ["Disposal Success Probability", "≥ 0.9 (per 47 CFR 25.122)"],
        ["Human Casualty Risk", "< 1:10,000 (per 47 CFR 25.114)"],
    ], col_widths=[2.5*inch, 4.5*inch]))

    story.append(Paragraph("12.2 Passivation", styles['SubSection']))
    story.append(Paragraph(
        "At end of life, all stored energy will be removed: batteries discharged, pressurized "
        "systems vented, reaction wheels de-spun. This eliminates accidental explosion risk "
        "per 47 CFR 25.114(d)(14)(ii).", styles['BodyText2']))

    story.append(Paragraph("12.3 Casualty Risk Assessment", styles['SubSection']))
    story.append(Paragraph(
        f"For a {mass_str} kg satellite, {'complete demise during atmospheric reentry is expected, resulting in zero casualty risk' if _safe_float(mass_str, 0) < 50 else 'a detailed casualty risk analysis using NASA DAS will be performed to demonstrate compliance with the < 1:10,000 casualty risk requirement'}.",
        styles['BodyText2']))
    story.append(PageBreak())

    # ═══════ Section 13: Risk ═══════
    story.append(Paragraph("13.0 Risk Assessment and Contingency Operations", styles['SectionHeader']))
    story.append(Paragraph("13.1 Mission Risk Register", styles['SubSection']))
    story.append(_make_table([
        ["ID", "Risk", "Likelihood", "Impact", "Mitigation"],
        ["R1", "Launch delay", "Medium", "Medium", "Flexible manifest, rideshare options"],
        ["R2", "Communication loss", "Low", "High", "Redundant GS, autonomous safe mode"],
        ["R3", "ADCS failure", "Low", "High", "Backup modes, sun-pointing safe mode"],
        ["R4", "Power degradation", "Medium", "Medium", "Oversized arrays, battery management"],
        ["R5", "Payload malfunction", "Low", "Medium", "Pre-flight testing, calibration"],
        ["R6", "Debris collision", "Very Low", "Very High", "Conjunction monitoring, avoidance"],
        ["R7", "Software anomaly", "Medium", "Medium", "Watchdog, safe mode, patching"],
        ["R8", "Deorbit failure", "Low", "High", "Drag augmentation backup"],
    ], col_widths=[0.4*inch, 1.5*inch, 0.9*inch, 0.8*inch, 3*inch]))
    story.append(Paragraph("Table 5: Mission risk register", styles['Caption']))

    story.append(Paragraph("13.2 Contingency Operations", styles['SubSection']))
    story.append(Paragraph(
        "<b>Loss of Communication:</b> If no ground contact within 72 hours, spacecraft will "
        "autonomously cycle through communication modes. After 30 days, permanent safe mode.",
        styles['BodyText2']))
    story.append(Paragraph(
        "<b>Safe Mode Recovery:</b> Entered upon under-voltage, attitude error, or comm timeout. "
        "Recovery requires ground command after root cause analysis.",
        styles['BodyText2']))
    story.append(PageBreak())

    # ═══════ Section 14: Regulatory Compliance ═══════
    story.append(Paragraph("14.0 Regulatory Compliance Summary", styles['SectionHeader']))
    story.append(_make_table([
        ["Requirement", "Regulation", "Status", "Section"],
        ["FCC Space Station License", fcc_type, "In preparation", "§1.4"],
        ["Orbital Parameters", "47 CFR 25.114(c)", "Provided", "§4.0"],
        ["System Operations Narrative", "47 CFR 25.114(d)(1)", "Provided", "§5.0–§9.0"],
        ["Communication Architecture", "47 CFR 25.114(c)(4)", "Provided", "§7.0"],
        ["Spectrum Sharing Strategy", "47 CFR 25.122(a)", "Provided", "§7.2"],
        ["Transmission Cessation", "47 CFR 25.122(a) / 97.207", "Implemented", "§7.3"],
        ["Unique Telemetry Marker", "47 CFR 25.122(a)", "Designed", "§3.1"],
        ["Debris Mitigation Plan", "47 CFR 25.114(d)(14)", "Provided", "§11.0"],
        ["Collision Risk Assessment", "47 CFR 25.114(d)(14)(iii)", "Pending", "§11.2"],
        ["Trackability", "47 CFR 25.114(d)(14)(v)", "Compliant", "§11.3"],
        ["Conjunction Response", "47 CFR 25.114(d)(14)(vi)", "Planned", "§11.4"],
        ["5-Year Deorbit", "FCC-22-74", "Compliant", "§12.0"],
        ["Casualty Risk < 1:10,000", "47 CFR 25.114(d)(14)(iv)", "Assessed", "§12.3"],
        ["Passivation Plan", "47 CFR 25.114(d)(14)(ii)", "Planned", "§12.2"],
        ["IARU Frequency Coordination", "IARU Form V40", "In preparation", "§7.1"],
    ], col_widths=[2*inch, 1.8*inch, 1.2*inch, 1.2*inch]))
    story.append(Paragraph("Table 6: FCC regulatory compliance cross-reference matrix", styles['Caption']))

    if "97" in fcc_type:
        story.append(Paragraph("14.1 Part 97 Notification Requirements", styles['SubSection']))
        story.append(_make_table([
            ["Notification", "Timing", "Content"],
            ["Pre-Space", "≤ 90 days before integration", "Debris mitigation, trackability, disposal"],
            ["In-Space", "Within 7 days of first Tx", "Updates to pre-space information"],
            ["Post-Space", "Within 3 months of Tx end", "Final disposition report"],
        ], col_widths=[1.5*inch, 2*inch, 3.5*inch]))
    story.append(PageBreak())

    # ═══════ Section 15: References ═══════
    story.append(Paragraph("15.0 References", styles['SectionHeader']))
    for val in SOURCES.values():
        story.append(Paragraph(f"&bull; {val}", styles['BulletText']))
    story.append(PageBreak())

    # ═══════ Appendix A: Link Budget ═══════
    story.append(Paragraph("Appendix A: Link Budget Analysis", styles['SectionHeader']))
    story.append(_generate_link_margin_diagram(m))
    story.append(Paragraph("Figure 7: Link margin vs. elevation angle", styles['Caption']))

    slant_5 = alt / math.sin(math.radians(5))
    slant_90 = alt
    dl_str2 = m.get("downlink_freq", "437") or "437"
    freq_mhz = _safe_float(dl_str2.split()[0], 437)
    fspl_5 = 20*math.log10(slant_5*1000) + 20*math.log10(freq_mhz*1e6) - 147.55
    fspl_90 = 20*math.log10(slant_90*1000) + 20*math.log10(freq_mhz*1e6) - 147.55
    story.append(_make_table([
        ["Parameter", "5° Elevation (Worst)", "90° Elevation (Best)"],
        ["Slant Range", f"{slant_5:.0f} km", f"{slant_90:.0f} km"],
        ["Free Space Path Loss", f"{fspl_5:.1f} dB", f"{fspl_90:.1f} dB"],
        ["Atmospheric Loss", "2.0 dB", "0.5 dB"],
        ["Total Path Loss", f"{fspl_5+3:.1f} dB", f"{fspl_90+1:.1f} dB"],
    ], col_widths=[2*inch, 2.5*inch, 2.5*inch]))
    story.append(PageBreak())

    # ═══════ Appendix B: FCC Cross-Ref ═══════
    story.append(Paragraph("Appendix B: FCC Application Cross-Reference Matrix", styles['SectionHeader']))
    story.append(_make_table([
        ["FCC Requirement", "CFR Citation", "ConOps Section"],
        ["Applicant Information", "25.114(a)", "Title Page"],
        ["Orbital Parameters", "25.114(c)(1)-(5)", "§4.0"],
        ["Frequency Information", "25.114(c)(4)", "§7.1"],
        ["Antenna Characteristics", "25.114(c)(4)(iii)", "§7.4"],
        ["System Operations", "25.114(d)(1)", "§5.0–§9.0"],
        ["Interference Analysis", "25.114(d)(3)", "§7.2"],
        ["Cessation of Emissions", "25.122(a)", "§7.3"],
        ["Debris Mitigation", "25.114(d)(14)", "§11.0"],
        ["Collision Avoidance", "25.114(d)(14)(iii)", "§11.2, §11.4"],
        ["End-of-Life Disposal", "25.114(d)(14)(iv)", "§12.0"],
        ["Trackability", "25.114(d)(14)(v)", "§11.3"],
        ["Casualty Risk", "25.114(d)(14)(iv)", "§12.3"],
        ["Unique Telemetry Marker", "25.122(a)", "§3.1"],
        ["Maneuverability", "25.122(a)", "§3.1"],
    ], col_widths=[2.2*inch, 1.8*inch, 2*inch]))
    story.append(PageBreak())

    # ═══════ Appendix C: Acronyms ═══════
    story.append(Paragraph("Appendix C: Acronyms and Abbreviations", styles['SectionHeader']))
    story.append(_make_table([
        ["Acronym", "Definition"],
        ["ADCS", "Attitude Determination and Control System"],
        ["C&DH", "Command and Data Handling"],
        ["CDM", "Conjunction Data Message"],
        ["ConOps", "Concept of Operations"],
        ["DAS", "Debris Assessment Software"],
        ["EIRP", "Effective Isotropic Radiated Power"],
        ["EOL", "End of Life"],
        ["EPS", "Electrical Power System"],
        ["FCC", "Federal Communications Commission"],
        ["FDIR", "Fault Detection, Isolation, and Recovery"],
        ["GEO", "Geostationary Earth Orbit"],
        ["IARU", "International Amateur Radio Union"],
        ["ITU", "International Telecommunication Union"],
        ["LEO", "Low Earth Orbit"],
        ["LTAN", "Local Time of Ascending Node"],
        ["MEO", "Medium Earth Orbit"],
        ["MLI", "Multi-Layer Insulation"],
        ["MOC", "Mission Operations Center"],
        ["NGSO", "Non-Geostationary Orbit"],
        ["RAAN", "Right Ascension of the Ascending Node"],
        ["RHCP", "Right-Hand Circular Polarization"],
        ["SDS", "Space Defense Squadron"],
        ["SSO", "Sun-Synchronous Orbit"],
        ["TRL", "Technology Readiness Level"],
    ], col_widths=[1.5*inch, 5.5*inch]))

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
