"""
plot_cumulative_demand_strip.py
Generates a single strip chart of NB + SB summed Track Longitudinal Demand.
"""
import matplotlib; matplotlib.use("Agg")
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

COLORS = ["#FF0000","#0000FF","#FF9900","#24E780","#00FFFF","#FF00FF","#993366","#969696"]
C_DEMAND = COLORS[6]  # (#993366) purple-maroon

plt.rcParams.update({
    "savefig.dpi": 300,
    "font.family": "Arial",
    "axes.grid": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

FS_TITLE, FS_LABEL, FS_TICK = 20, 16, 14

def load_and_bin(csv_path):
    df = pd.read_csv(csv_path)
    speed_mps = df['speed_meters_per_second']
    f_whl_kn  = df['pwr_whl_out_watts'] / np.maximum(speed_mps, 0.1) / 1000.0
    f_res_kn  = (df['res_grade_newtons'] + df['res_curve_newtons'] +
                 df['res_rolling_newtons'] + df['res_aero_newtons'] +
                 df['res_bearing_newtons']) / 1000.0
    df['track_long_kn'] = -f_whl_kn + f_res_kn
    df['mp_group'] = (df['milepost'] * 2).round() / 2.0
    return df.groupby('mp_group')['track_long_kn'].mean().reset_index().sort_values('mp_group')

print("Loading NB + SB simulation data...")
nb = load_and_bin("results/henderson_full_sim/nb_simulation.csv")
sb = load_and_bin("results/henderson_sb_sim/sb_simulation.csv")

combined = nb.merge(sb, on='mp_group', suffixes=('_nb','_sb'), how='outer').fillna(0)
combined['track_long_kn'] = combined['track_long_kn_nb'] + combined['track_long_kn_sb']
combined = combined.sort_values('mp_group')

x = combined['mp_group'].values
demand = combined['track_long_kn'].values

fig, ax = plt.subplots(figsize=(20, 6))
ax.plot(x, demand, color=C_DEMAND, linewidth=1.8)
ax.axhline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.4)
ax.set_title("Cumulative Track Longitudinal Demand (NB + SB)", fontsize=FS_TITLE, fontweight='bold')
ax.set_xlabel("Milepost", fontweight='bold', fontsize=FS_LABEL)
ax.set_ylabel("Demand (kN)", fontweight='bold', fontsize=FS_LABEL)
ax.tick_params(labelsize=FS_TICK)
ax.set_xlim(176, 319)
ax.set_ylim(-2500, 2500)
ax.spines['top'].set_alpha(0.3)
ax.spines['right'].set_alpha(0.3)

plt.tight_layout()
OUT = Path("/Users/nakulvasani/Desktop/Lunch Meeting")
OUT.mkdir(exist_ok=True, parents=True)
out_path = OUT / "Cumulative_NB_SB_Demand_Strip.png"
plt.savefig(out_path, bbox_inches='tight')
print(f"Saved: {out_path}")
