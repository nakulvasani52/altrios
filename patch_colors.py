import os
import re

files_to_patch = [
    'plot_henderson_full_strips.py',
    'plot_henderson_sb_strips.py',
    'eda_henderson_sim.py',
    'eda_henderson_sb.py',
    'plot_dynamic_vs_air.py',
    'plot_sb_dynamic_vs_air.py',
    'analyze_track_demand.py'
]

pal = {
    'red': '#FF0000',
    'blue': '#0000FF',
    'orange': '#FF9900',
    'green': '#24E780',
    'cyan': '#00FFFF',
    'magenta': '#FF00FF',
    'maroon': '#993366',
    'gray': '#969696'
}

for f in files_to_patch:
    with open(f, 'r') as file:
        content = file.read()

    # Generic
    content = content.replace("color='red'", f"color='{pal['red']}'")
    content = content.replace("color='blue'", f"color='{pal['blue']}'")
    content = content.replace("color='green'", f"color='{pal['green']}'")
    content = content.replace("color='orange'", f"color='{pal['orange']}'")
    content = content.replace("color='purple'", f"color='{pal['magenta']}'")
    content = content.replace("color='gray'", f"color='{pal['gray']}'")

    # Seaborn
    content = content.replace("palette='coolwarm'", f"palette=['{pal['blue']}', '{pal['red']}']")
    
    # Specifics in strips
    content = content.replace("C_GRADE = '#d62728'", f"C_GRADE = '{pal['red']}'")
    content = content.replace("C_CURVE = '#1f77b4'", f"C_CURVE = '{pal['blue']}'")
    content = content.replace("C_SPEED = '#ff7f0e'", f"C_SPEED = '{pal['orange']}'")
    content = content.replace("PURPLE = '#9467bd'", f"PURPLE = '{pal['magenta']}'")
    content = content.replace("RED    = '#d62728'", f"RED    = '{pal['red']}'")
    content = content.replace("BLUE   = '#1f77b4'", f"BLUE   = '{pal['blue']}'")
    content = content.replace("GREEN  = '#2ca02c'", f"GREEN  = '{pal['green']}'")

    # Specifics in dynamic_vs_air
    content = content.replace("color='#E63946'", f"color='{pal['red']}'")
    content = content.replace("color='#1D3557'", f"color='{pal['blue']}'")

    # Specifics in analyze_track_demand
    content = content.replace("color='#D62728'", f"color='{pal['cyan']}'") # locomotive (was red, but red is grade. let's use cyan)
    content = content.replace("color='#1F77B4'", f"color='{pal['magenta']}'") # car (was blue, but blue is curve. let's use magenta)
    content = content.replace("color='#2CA02C'", f"color='{pal['green']}'") # vertical
    
    # Let's check heatmap in eda
    content = content.replace(", cmap='coolwarm'", f", cmap='coolwarm'") # Keep correlation matrix colormap or change it?
    
    with open(f, 'w') as file:
        file.write(content)
print("Color patching applied.")
