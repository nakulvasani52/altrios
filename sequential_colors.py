import re
import os

scripts = [
    'plot_henderson_full_strips.py',
    'plot_henderson_sb_strips.py',
    'eda_henderson_sim.py',
    'eda_henderson_sb.py',
    'plot_dynamic_vs_air.py',
    'plot_sb_dynamic_vs_air.py',
    'analyze_track_demand.py'
]

palette = "['#FF0000', '#0000FF', '#FF9900', '#24E780', '#00FFFF', '#FF00FF', '#993366', '#969696']"

for s in scripts:
    with open(s, 'r') as f:
        content = f.read()

    # Step 1: Inject the palette definition at the top if not present
    if "COLORS =" not in content:
        content = content.replace("import numpy as np", f"import numpy as np\nCOLORS = {palette}")
    
    # We want to replace all distinct plot colors with COLORS[i]
    import re
    
    # We will manually replace color kwargs in the scripts.
    # It might be easier to just do it via string replacement of known definitions in plot_henderson...
    # Let's do it file by file to be safe.
