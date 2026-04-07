import os
import re

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
rc_inject = f"""\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nplt.rcParams['axes.prop_cycle'] = plt.cycler(color={palette})\nsns.set_palette({palette})\n"""

for s in scripts:
    with open(s, 'r') as f:
        content = f.read()

    # 1. Clean out existing color kwargs
    # regex to eliminate `, color=...` or `color=..., `
    content = re.sub(r',\s*color\s*=\s*[A-Z_a-z0-9"\'#]+', '', content)
    content = re.sub(r'color\s*=\s*[A-Z_a-z0-9"\'#]+\s*,', '', content)
    # also handle `color=...` right before closing paren
    content = re.sub(r',\s*color\s*=\s*[A-Z_a-z0-9"\'#]+(?=\))', '', content)
    content = re.sub(r'colors\s*=\s*\[[^\]]+\]', '', content) # strip stackplot colors list too
    
    # seaborn palette kwarg
    content = re.sub(r',\s*palette\s*=\s*\[[^\]]+\]', '', content)
    content = re.sub(r',\s*palette\s*=\s*[A-Z_a-z0-9"\'#]+', '', content)

    # 2. Inject the global property cycle
    if "plt.rcParams['axes.prop_cycle']" not in content:
        # find where matplotlib is imported
        if "import matplotlib.pyplot as plt" in content:
            content = content.replace("import matplotlib.pyplot as plt", rc_inject, 1)
        else:
            # prepend
            content = rc_inject + content

    with open(s, 'w') as f:
        f.write(content)

print("Cyclers injected!")
