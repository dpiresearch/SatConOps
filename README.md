# Satellite ConOps Generator

A web application that generates FCC-compliant Concept of Operations (ConOps) PDF documents for satellite missions of any class — from CubeSats to large GEO communications platforms.

## What It Does

Users fill in their satellite mission parameters through a web form, and the tool generates a professional ~23-page ConOps PDF containing:

- 15 numbered sections covering all aspects of mission operations
- 7 auto-generated diagrams (spacecraft configuration, orbit, mission phases, operational modes, communication architecture, power budget, link margin analysis)
- 6+ data tables (spacecraft parameters, subsystems, frequency plan, link budget, risk register, regulatory compliance matrix)
- 3 appendices (link budget analysis, FCC cross-reference matrix, acronyms)
- Page numbers, distribution markings, and figure/table captions throughout

The generated document is structured to satisfy FCC filing requirements and follows aerospace industry ConOps standards.

## Supported Satellite Classes

| Class | Typical Mass | Example |
|-------|-------------|---------|
| CubeSat | 1-24 kg | 3U Earth observation satellite |
| Microsatellite | 10-100 kg | Technology demonstration platform |
| Small Satellite | 100-500 kg | SAR radar constellation member |
| Medium Satellite | 500-1000 kg | Weather satellite |
| Large Satellite | > 1000 kg | National security payload |
| GEO Communications | 2000-6000 kg | Broadband relay platform |
| Science / Exploration | Varies | Deep space probe |

The UI dynamically adjusts based on the selected class (e.g., CubeSat form factor selector only appears for CubeSats; orbit parameters auto-fill for GEO/MEO/Molniya selections).

## PDF Sections

| # | Section | FCC Relevance |
|---|---------|---------------|
| 1 | Introduction | Purpose, objectives, applicable standards, regulatory framework |
| 2 | Mission Overview | Description, stakeholders, success criteria, timeline |
| 3 | Space Segment Description | Spacecraft config diagram, subsystem summary, payload |
| 4 | Orbit Description | Orbital parameters, orbit diagram, eclipse & decay analysis |
| 5 | Mission Phases | Phase timeline diagram, detailed phase descriptions |
| 6 | Operational Modes | State transition diagram, mode table, transition logic |
| 7 | Communication Architecture | Comm diagram, frequency plan, spectrum sharing, link budget | 
| 8 | Ground Segment | Station description, contact schedule, data budget |
| 9 | Command and Data Handling | Command protocol, telemetry, autonomy & fault management |
| 10 | Power Budget Analysis | Power-by-mode chart, generation/storage parameters |
| 11 | Orbital Debris Mitigation | Debris release, collision risk, trackability, conjunction response |
| 12 | End-of-Life Disposal | Deorbit method, passivation, casualty risk assessment |
| 13 | Risk Assessment | Risk register (8 risks), contingency operations |
| 14 | Regulatory Compliance | 16-row FCC cross-reference matrix, Part 97 notifications |
| 15 | References | All cited standards and regulations with URLs |
| A | Link Budget Analysis | Link margin vs. elevation angle plot, path loss table |
| B | FCC Cross-Reference Matrix | Maps 47 CFR requirements to ConOps sections |
| C | Acronyms | 25 aerospace/regulatory acronyms |

## Regulatory Standards Referenced

- **47 CFR Part 25.114** — Standard satellite application requirements
- **47 CFR Part 25.122** — Streamlined small satellite process (LEO, <=180 kg, <=600 km)
- **47 CFR Part 97.207** — Amateur radio space station rules
- **FCC-22-74** — 5-year post-mission deorbit rule (2022)
- **ANSI/AIAA G-043A-2012** — Guide for Operational Concept Documents
- **IEEE 1362-1998** — Concept of Operations Document standard
- **CubeSat Design Specification Rev 14.1** — Cal Poly / CubeSat.org
- **NASA GSFC-STD-1001A** — Flight Project Lifecycle Reviews
- **IARU Satellite Frequency Coordination** — Form V40
- **ITU Radio Regulations** — International frequency coordination

## Quick Start

```bash
# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install flask reportlab matplotlib numpy pillow

# Run the application
python app.py
```

Open http://127.0.0.1:5002 in your browser.

Fill in the form and click **Generate ConOps PDF**. The PDF opens in a new tab.

## Project Structure

```
SatConOps/
  app.py              Flask web application (port 5002)
  conops_pdf.py       PDF generator (reportlab + matplotlib)
  templates/
    index.html        Web UI with collapsible form sections
  output/             Generated PDFs (created automatically)
  venv/               Python virtual environment
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.1 | Web framework |
| ReportLab | 4.5 | PDF generation |
| Matplotlib | 3.10 | Diagram and chart generation |
| NumPy | 2.4 | Numerical computations (link budget, orbital mechanics) |
| Pillow | 12.2 | Image handling for PDF embedding |

Python 3.10+ required.

## How the PDF Is Generated

1. The user submits mission parameters via the web form.
2. `app.py` collects form data, auto-generates any missing descriptions.
3. `conops_pdf.py` builds the PDF using ReportLab's `SimpleDocTemplate`:
   - Matplotlib generates 7 PNG figures (spacecraft diagram, orbit plot, phase timeline, mode state diagram, comm architecture, power budget bar chart, link margin curve).
   - Each figure is rendered to an in-memory buffer and embedded in the PDF.
   - Tables are styled with alternating row colors and navy headers.
   - Orbital mechanics (period, velocity, eclipse fraction, path loss) are computed from the input altitude and inclination.
   - A custom `NumberedCanvas` adds page numbers and distribution markings to every page.
4. The PDF is saved to `output/` and returned as a download.

## FCC License Types

The tool supports four FCC licensing paths. The generated ConOps adjusts its regulatory language accordingly:

| License | When to Use |
|---------|-------------|
| **Part 25.122** | LEO small satellites: <=180 kg, <=600 km altitude, <=6 year lifetime |
| **Part 25.114** | Standard application for all other commercial satellites |
| **Part 97** | Amateur radio satellites (adds pre-space/in-space/post-space notification section) |
| **Part 5** | Experimental licenses |

## Notes

- The generated ConOps is a starting point for an FCC filing, not a complete application. Collision probability analysis (NASA DAS), detailed interference studies, and IARU frequency coordination must be completed separately.
- Link budget calculations use simplified free-space path loss models. Production filings should use validated RF analysis tools.
- Orbital decay estimates are approximate. Use STK, GMAT, or NASA DAS for authoritative decay analysis.
- The "DISTRIBUTION: LIMITED — PRE-DECISIONAL" marking on each page is a placeholder. Update classification markings to match your organization's policies before distribution.
