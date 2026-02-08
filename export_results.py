from fpdf import FPDF
from fpdf.enums import XPos, YPos
import os
import shutil
import re

# Paths
SOURCE_DIR = "/Users/nakulvasani/altrios"
REPORT_MD = "/Users/nakulvasani/.gemini/antigravity/brain/5085ee85-5401-4228-930f-47d8492da54d/track_demand_analysis_report.md"
FIGURES = [
    "results/presentation/henderson_geometry_presentation.png",
    "results/presentation/henderson_nb_track_demand_directional.png",
    "results/presentation/henderson_sb_track_demand_directional.png",
    "results/presentation/henderson_nb_resistance_analysis.png",
    "results/presentation/henderson_sb_resistance_analysis.png",
    "results/presentation/henderson_nb_railtec_presentation_stack.png",
    "results/presentation/henderson_sb_railtec_presentation_stack.png",
    "results/track_demand_comparison_overlay.png"
]
CSV_RESULTS = [
    "results/henderson_nb_simulation.csv",
    "results/henderson_sb_simulation.csv",
    "results/track_demand_hotspots.csv"
]
EXPORT_DIR = os.path.expanduser("~/Downloads/ALTRIOS 02-01")

def clean_text(text):
    substitutions = {
        "$$": "", "\\": "", "_": "", "{": "(", "}": ")",
        "\u2192": "->", "\u2013": "-", "\u2014": "--",
        "🔴": "[CRITICAL]", "🟡": "[MODERATE]", "🟢": "[OK]",
        "✅": "[SUCCESS]", "❌": "[FAILED]", "⚠️": "[WARNING]"
    }
    for old, new in substitutions.items():
        text = text.replace(old, new)
    return text.encode('ascii', 'ignore').decode('ascii')

def export_results():
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)

    for fig in FIGURES:
        src = os.path.join(SOURCE_DIR, fig)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(EXPORT_DIR, os.path.basename(fig)))

    for csv_file in CSV_RESULTS:
        src = os.path.join(SOURCE_DIR, csv_file)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(EXPORT_DIR, os.path.basename(csv_file)))

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    # Constants
    PAGE_WIDTH = 210
    MARGIN = 20
    CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

    pdf.set_font("helvetica", "B", 20)
    pdf.cell(0, 20, "Henderson Corridor: Track Demand Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(5)

    with open(REPORT_MD, "r") as f:
        content = f.read()

    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(3)
            continue
            
        # Image Handling
        img_match = re.search(r"!\[(.*?)\]\((.*?)\)", line)
        if img_match:
            label = img_match.group(1)
            img_filename = os.path.basename(img_match.group(2))
            img_path = os.path.join(EXPORT_DIR, img_filename)
            
            if os.path.exists(img_path):
                if pdf.get_y() > 200: pdf.add_page()
                pdf.image(img_path, x=MARGIN, w=CONTENT_WIDTH)
                pdf.ln(1)
                pdf.set_font("helvetica", "I", 10)
                pdf.cell(0, 10, f"Figure: {label}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
                pdf.ln(2)
            continue

        if "slide" in line or "carousel" in line or line.startswith("```"):
            continue
            
        line = clean_text(line)
        
        # Header Logic
        if line.startswith("## "):
            pdf.ln(4)
            pdf.set_font("helvetica", "B", 16)
            pdf.multi_cell(CONTENT_WIDTH, 10, line[3:])
            pdf.ln(1)
        elif line.startswith("### "):
            pdf.set_font("helvetica", "B", 14)
            pdf.multi_cell(CONTENT_WIDTH, 8, line[4:])
            pdf.ln(1)
        elif line.startswith("- "):
            pdf.set_font("helvetica", "", 12)
            # Indent bullet points
            pdf.set_x(MARGIN + 5)
            # Adjust width for indentation
            pdf.multi_cell(CONTENT_WIDTH - 5, 7, f" {line}")
        elif "|" in line:
            # Handle table lines with fixed-width font
            pdf.set_font("courier", "", 8)
            pdf.set_x(MARGIN)
            pdf.multi_cell(CONTENT_WIDTH, 6, line)
        else:
            pdf.set_font("helvetica", "", 12)
            pdf.set_x(MARGIN)
            pdf.multi_cell(CONTENT_WIDTH, 7, line)

    save_path = os.path.join(EXPORT_DIR, "Track_Demand_Analysis_Report.pdf")
    pdf.output(save_path)
    print(f"Generated PDF: {save_path}")

if __name__ == "__main__":
    export_results()
