#!/usr/bin/env python3
"""
Generate a Word document from the resistance physics explanation markdown.
This script converts the markdown content to a formatted Word document.
"""

try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    print("python-docx not installed. Installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "python-docx"])
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

def create_resistance_physics_doc():
    """Create a Word document explaining train resistance physics in Altrios."""
    
    doc = Document()
    
    # Title
    title = doc.add_heading('Train Resistance Physics in Altrios', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Overview
    doc.add_heading('Overview', 1)
    p = doc.add_paragraph()
    p.add_run('Altrios calculates train resistance forces using the ').bold = False
    p.add_run('Modified Davis Equation').bold = True
    p.add_run(', which determines how much resistive force acts against a train\'s motion. This resistance directly impacts fuel consumption because the locomotive must generate enough power to overcome these forces.')
    
    # The Complete Resistance Formula
    doc.add_heading('The Complete Resistance Formula', 1)
    doc.add_paragraph('The complete train resistance formula is:')
    
    formula = doc.add_paragraph('R = A + BV + CV² + 20G + 0.8c', style='Intense Quote')
    formula.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph('Where:')
    items = [
        ('R', 'total resistance in lbs per ton'),
        ('A', 'rolling resistance (constant)'),
        ('B', 'bearing/mechanical resistance coefficient'),
        ('V', 'velocity (speed)'),
        ('C', 'aerodynamic drag coefficient'),
        ('G', 'grade in percent'),
        ('c', 'curvature in degrees'),
    ]
    
    for var, desc in items:
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(f'{var}').bold = True
        p.add_run(f' = {desc}')
    
    # Code Location
    doc.add_heading('Code Location', 1)
    doc.add_paragraph('All resistance calculations are located in:')
    doc.add_paragraph('altrios-core/src/train/resistance/', style='Intense Quote')
    
    doc.add_paragraph('This directory contains:')
    doc.add_paragraph('kind/ - Individual resistance component implementations', style='List Bullet')
    doc.add_paragraph('method/ - Methods for combining resistances (Point vs Strap)', style='List Bullet')
    doc.add_paragraph('mod.rs - Main resistance trait and wrapper', style='List Bullet')
    
    # Resistance Components Breakdown
    doc.add_heading('Resistance Components Breakdown', 1)
    
    # 1. Rolling Resistance
    doc.add_heading('1. Rolling Resistance (A term)', 2)
    doc.add_paragraph().add_run('Physics: ').bold = True
    doc.add_paragraph('Constant resistance from wheel-rail contact, independent of speed.')
    
    doc.add_paragraph().add_run('Code File: ').bold = True
    doc.add_paragraph('rolling.rs')
    
    doc.add_paragraph().add_run('Formula: ').bold = True
    doc.add_paragraph('F_rolling = ratio × weight', style='Intense Quote')
    
    doc.add_paragraph().add_run('Typical value: ').bold = True
    doc.add_paragraph('1.5 lb/ton')
    
    # 2. Bearing Resistance
    doc.add_heading('2. Bearing Resistance (part of A term)', 2)
    doc.add_paragraph().add_run('Physics: ').bold = True
    doc.add_paragraph('Constant friction from axle bearings.')
    
    doc.add_paragraph().add_run('Code File: ').bold = True
    doc.add_paragraph('bearing.rs')
    
    doc.add_paragraph().add_run('Formula: ').bold = True
    doc.add_paragraph('F_bearing = constant force', style='Intense Quote')
    
    doc.add_paragraph().add_run('Typical value: ').bold = True
    doc.add_paragraph('4,000 lbf (40 cars × 100 lbf)')
    
    # 3. Davis B Term
    doc.add_heading('3. Davis B Term (BV term)', 2)
    doc.add_paragraph().add_run('Physics: ').bold = True
    doc.add_paragraph('Speed-dependent mechanical resistance, linear with velocity.')
    
    doc.add_paragraph().add_run('Code File: ').bold = True
    doc.add_paragraph('davis_b.rs')
    
    doc.add_paragraph().add_run('Formula: ').bold = True
    doc.add_paragraph('F_davis_b = B × velocity × weight', style='Intense Quote')
    
    doc.add_paragraph().add_run('Typical value: ').bold = True
    doc.add_paragraph('0.03 (lb/ton)/(mph)')
    
    # 4. Aerodynamic Resistance
    doc.add_heading('4. Aerodynamic Resistance (CV² term)', 2)
    doc.add_paragraph().add_run('Physics: ').bold = True
    doc.add_paragraph('Air drag, proportional to velocity squared.')
    
    doc.add_paragraph().add_run('Code File: ').bold = True
    doc.add_paragraph('aerodynamic.rs')
    
    doc.add_paragraph().add_run('Formula: ').bold = True
    doc.add_paragraph('F_aero = C_d × A × ρ_air × velocity²', style='Intense Quote')
    
    doc.add_paragraph('Where:')
    doc.add_paragraph('C_d × A = drag coefficient × frontal area', style='List Bullet')
    doc.add_paragraph('ρ_air = air density', style='List Bullet')
    
    p = doc.add_paragraph()
    p.add_run('Note: ').bold = True
    p.add_run('The traditional factor of 0.5 in the drag equation is lumped into the coefficient.')
    
    # 5. Grade Resistance
    doc.add_heading('5. Grade Resistance (20G term)', 2)
    doc.add_paragraph().add_run('Physics: ').bold = True
    doc.add_paragraph('Gravitational force component pulling the train down (or up) a slope.')
    
    doc.add_paragraph().add_run('Code File: ').bold = True
    doc.add_paragraph('path_res.rs')
    
    doc.add_paragraph().add_run('Formula: ').bold = True
    doc.add_paragraph('F_grade = grade × weight', style='Intense Quote')
    
    doc.add_paragraph('Physics derivation:')
    doc.add_paragraph('F_G = W × sin(A) where A is slope angle', style='List Bullet')
    doc.add_paragraph('For small angles: sin(A) ≈ tan(A) = G (grade)', style='List Bullet')
    doc.add_paragraph('Result: F_G = W × G', style='List Bullet')
    doc.add_paragraph('For 1% grade: F_G = 0.01W = 20 lbs per ton', style='List Bullet')
    
    p = doc.add_paragraph()
    p.add_run('Key insight: ').bold = True
    p.add_run('The "20G" in the formula means 20 pounds per ton per percent grade.')
    
    # 6. Curve Resistance
    doc.add_heading('6. Curve Resistance (0.8c term)', 2)
    doc.add_paragraph().add_run('Physics: ').bold = True
    doc.add_paragraph('Additional resistance from wheel flanges rubbing against rails on curves.')
    
    doc.add_paragraph().add_run('Code File: ').bold = True
    doc.add_paragraph('path_res.rs (same as grade resistance)')
    
    doc.add_paragraph().add_run('Formula: ').bold = True
    doc.add_paragraph('F_curve = curve_coeff × weight', style='Intense Quote')
    
    p = doc.add_paragraph()
    p.add_run('Note: ').bold = True
    p.add_run('The "0.8c" means 0.8 pounds per ton per degree of curvature.')
    
    # How Resistances Are Combined
    doc.add_heading('How Resistances Are Combined', 1)
    doc.add_paragraph('All resistance forces are summed to get total net resistance:')
    
    doc.add_paragraph().add_run('Code File: ').bold = True
    doc.add_paragraph('train_state.rs (res_net function)')
    
    doc.add_paragraph('This matches the formula: R = A + BV + CV² + 20G + 0.8c', style='Intense Quote')
    
    doc.add_paragraph('Where:')
    doc.add_paragraph('A = res_rolling + res_bearing', style='List Bullet')
    doc.add_paragraph('BV = res_davis_b', style='List Bullet')
    doc.add_paragraph('CV² = res_aero', style='List Bullet')
    doc.add_paragraph('20G = res_grade', style='List Bullet')
    doc.add_paragraph('0.8c = res_curve', style='List Bullet')
    
    # Connection to Fuel Consumption
    doc.add_heading('Connection to Fuel Consumption', 1)
    doc.add_paragraph('The total resistance force determines the power required to maintain speed:')
    
    doc.add_paragraph('Power = Force × Velocity', style='Intense Quote')
    
    doc.add_paragraph('The locomotive must generate this power, which directly translates to fuel consumption:')
    doc.add_paragraph('Higher resistance → More power needed → More fuel burned', style='List Bullet')
    doc.add_paragraph('Grades and curves dramatically increase resistance', style='List Bullet')
    doc.add_paragraph('Speed affects aerodynamic (V²) and Davis B (V) terms significantly', style='List Bullet')
    
    # Example Calculation
    doc.add_heading('Example Calculation', 1)
    doc.add_paragraph().add_run('Scenario: ').bold = True
    doc.add_paragraph('100 loaded 110-ton cars (143 tons each loaded) at 10 mph on 0.76% grade and 6-degree curve')
    
    doc.add_paragraph().add_run('Calculation breakdown:').bold = True
    doc.add_paragraph('A term (rolling + bearing): ~18,700 lbs (from straight, level track)', style='List Bullet')
    doc.add_paragraph('BV term: Minimal at 10 mph', style='List Bullet')
    doc.add_paragraph('CV² term: Very small at 10 mph', style='List Bullet')
    doc.add_paragraph('20G term: 20 × 0.76 × 14,300 tons = ~217,000 lbs', style='List Bullet')
    doc.add_paragraph('0.8c term: 0.8 × 6 × 14,300 tons = ~68,600 lbs', style='List Bullet')
    
    p = doc.add_paragraph()
    p.add_run('Conclusion: ').bold = True
    p.add_run('The grade and curve terms dominate at low speeds on challenging terrain!')
    
    # Key Files Reference
    doc.add_heading('Key Files Reference', 1)
    
    table = doc.add_table(rows=8, cols=2)
    table.style = 'Light Grid Accent 1'
    
    # Header row
    header_cells = table.rows[0].cells
    header_cells[0].text = 'Component'
    header_cells[1].text = 'File'
    
    # Data rows
    data = [
        ('Rolling Resistance', 'rolling.rs'),
        ('Bearing Resistance', 'bearing.rs'),
        ('Davis B Term', 'davis_b.rs'),
        ('Aerodynamic', 'aerodynamic.rs'),
        ('Grade/Curve', 'path_res.rs'),
        ('Total Resistance', 'train_state.rs'),
        ('Orchestration', 'point.rs'),
    ]
    
    for i, (component, file) in enumerate(data, 1):
        row_cells = table.rows[i].cells
        row_cells[0].text = component
        row_cells[1].text = file
    
    # Summary
    doc.add_heading('Summary', 1)
    p = doc.add_paragraph()
    p.add_run('Altrios implements the complete Modified Davis Equation for train resistance. Each term is calculated separately and summed to get total resistance. This total resistance force determines the power requirement, which directly drives fuel consumption calculations. The modular design allows each resistance component to be independently configured and validated.')
    
    # Save the document
    output_path = '/Users/nakulvasani/altrios/Train_Resistance_Physics_Altrios.docx'
    doc.save(output_path)
    print(f"Document created successfully: {output_path}")
    return output_path

if __name__ == '__main__':
    create_resistance_physics_doc()
