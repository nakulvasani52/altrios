import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Use Agg backend for stability
import matplotlib
matplotlib.use("Agg")

def load_and_bin(csv_path):
    df = pd.read_csv(csv_path)
    
    # Calculate forces from raw ALTRIOS output
    speed_mps = df['speed_meters_per_second']
    f_whl_kn = df['pwr_whl_out_watts'] / np.maximum(speed_mps, 0.1) / 1000.0
    
    f_res_kn = (df['res_grade_newtons'] + df['res_curve_newtons'] + 
                df['res_rolling_newtons'] + df['res_aero_newtons'] + 
                df['res_bearing_newtons']) / 1000.0
                
    # Track demand = -wheel + resistance
    df['track_long_kn'] = -f_whl_kn + f_res_kn
    
    # Bin by 0.5 milepost
    df['mp_group'] = (df['milepost'] * 2).round() / 2.0
    agg = df.groupby('mp_group').mean(numeric_only=True).reset_index()
    return agg.sort_values('mp_group')

# Setup
NB_PATH = "results/henderson_full_sim/nb_simulation.csv"
SB_PATH = "results/henderson_sb_sim/sb_simulation.csv"
OUT_DIR = Path("/Users/nakulvasani/Desktop/Lunch Meeting")
COLORS = ["#FF0000", "#0000FF"] # Red for NB, Blue for SB

# Load data
print("Loading and binning data...")
nb_agg = load_and_bin(NB_PATH)
sb_agg = load_and_bin(SB_PATH)

# Plotting
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica"],
    "axes.labelsize": 16,
    "axes.titlesize": 20,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "axes.grid": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white"
})

fig, ax = plt.subplots(figsize=(20, 8))

# Plot NB (Red)
ax.plot(nb_agg['mp_group'], nb_agg['track_long_kn'], color=COLORS[0], linewidth=1.5, alpha=0.7, label="Northbound")

# Plot SB (Blue) - plotted on same MP axis
ax.plot(sb_agg['mp_group'], sb_agg['track_long_kn'], color=COLORS[1], linewidth=1.5, alpha=0.7, label="Southbound")

ax.axhline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.4)

ax.set_title("Track Longitudinal Demand Comparison: Northbound vs. Southbound", fontweight="bold", pad=15)
ax.set_xlabel("Milepost", fontweight="bold")
ax.set_ylabel("Demand (kN)", fontweight="bold")
ax.set_xlim(176, 319)
ax.set_ylim(-2500, 2500)

# Arthur mentioned legends are cool for folks here, but user previously wanted no legends.
# Given Arthur's comment "highlights why simulation is a helpful tool", 
# I'll include a small legend or label manually if needed. 
# Actually, I'll stick to NO LEGEND as per user's earlier constraint "no legends for any graphs - I can label it later"
# BUT Arthur's comment specific for this "NB and SB lines" visual might imply it's better to have one.
# User said "make the viz such that there are no legends for any graphs - I can label it later"
# I'll respect the user's explicit rule.

plt.tight_layout()
save_path = OUT_DIR / "NB_SB_Demand_Comparison.png"
plt.savefig(save_path, dpi=300, bbox_inches='tight')
print(f"Comparison chart saved to: {save_path}")
