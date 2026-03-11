import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy.ndimage import gaussian_filter1d

# Settings
INPUT_FILE = "results/henderson_full_sim/nb_simulation.csv"
OUTPUT_DIR = Path("results/henderson_full_sim/braking_analysis")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

sns.set_style("whitegrid")
plt.rcParams.update({
    'figure.dpi': 150,
    'font.size': 18,
    'axes.titlesize': 22,
    'axes.labelsize': 20,
    'xtick.labelsize': 16,
    'ytick.labelsize': 16,
    'legend.fontsize': 16
})

print(f"Loading {INPUT_FILE}...")
df = pd.read_csv(INPUT_FILE)

# Speed & Acceleration
df['speed_mps'] = df['speed_meters_per_second']
df['accel_ms2'] = df['speed_mps'].diff() / df['dt_seconds']
df['accel_ms2'] = gaussian_filter1d(df['accel_ms2'].fillna(0), sigma=3)

# Mass & Resistance
df['mass_kg'] = df['mass_static_kilograms']
df['F_resistance_N'] = (
    df['res_grade_newtons'] + 
    df['res_curve_newtons'] + 
    df['res_rolling_newtons'] + 
    df['res_aero_newtons'] + 
    df['res_bearing_newtons']
)

# Force Balance (F_net = ma + F_res)
df['F_net_required_N'] = df['mass_kg'] * df['accel_ms2'] + df['F_resistance_N']

# Dynamic Braking (Power < 0 means dynamic braking)
df['F_dynamic_braking_N'] = np.where(
    df['pwr_whl_out_watts'] < 0,
    np.abs(df['pwr_whl_out_watts']) / np.maximum(df['speed_mps'], 1.0),
    0
)

# Air Braking (Residual to achieve net force balance)
df['F_air_braking_N'] = np.maximum(0, -(df['F_net_required_N'] + df['F_dynamic_braking_N']))

# Smooth
df['F_dynamic_braking_N'] = gaussian_filter1d(df['F_dynamic_braking_N'], sigma=2)
df['F_air_braking_N'] = gaussian_filter1d(df['F_air_braking_N'], sigma=2)

# Convert to kN
df['F_dynamic_kN'] = df['F_dynamic_braking_N'] / 1000
df['F_air_kN'] = df['F_air_braking_N'] / 1000
df['F_total_brake_kN'] = (df['F_dynamic_braking_N'] + df['F_air_braking_N']) / 1000

import json
with open("data/henderson_full_meta.json") as f:
    meta = json.load(f)

# Filter out the dummy buffer (use main corridor)
df_main = df[(df['total_dist_meters'] >= meta['dummy_length_m']) & 
             (df['total_dist_meters'] <= meta['dummy_length_m'] + meta['main_length_m'])].copy()
if len(df_main) == 0:
    df_main = df
df_main = df_main.sort_values("milepost")

mp_min = meta['mp_min']
mp_max = min(meta['mp_max'], df_main['milepost'].max() + 0.5)

# Bin into 0.1 MP groups to remove high-frequency noise
df_main['mp_group'] = (df_main['milepost'] * 10).round() / 10.0
agg = df_main.groupby('mp_group').agg({
    'F_dynamic_kN': 'mean',
    'F_air_kN': 'mean',
    'F_total_brake_kN': 'mean'
}).reset_index()

# Plotting
fig, ax = plt.subplots(figsize=(20, 6))

ax.fill_between(agg['mp_group'], 0, agg['F_dynamic_kN'], 
                 alpha=0.4, color='#E63946', label='Dynamic Braking (Locomotives)', linewidth=0)
ax.plot(agg['mp_group'], agg['F_dynamic_kN'], 
        color='#E63946', linewidth=2, alpha=0.9)

ax.fill_between(agg['mp_group'], 0, agg['F_air_kN'], 
                 alpha=0.3, color='#1D3557', label='Air Braking (Distributed)', linewidth=0)
ax.plot(agg['mp_group'], agg['F_air_kN'], 
        color='#1D3557', linewidth=2, alpha=0.9)

ax.axhline(0, color='gray', linewidth=0.8, linestyle='-', alpha=0.4)

ax.set_xlabel('Milepost', fontsize=14, fontweight='bold')
ax.set_ylabel('Braking Force (kN)', fontsize=14, fontweight='bold')
ax.set_title('Henderson Full Run: Dynamic vs Air Braking Force Distribution', 
             fontsize=16, fontweight='bold', pad=20)

ax.legend(loc='upper right', fontsize=12, framealpha=0.98, edgecolor='gray')
ax.grid(True, alpha=0.3, linewidth=0.5)

ax.set_xlim(mp_min, mp_max)

plt.tight_layout()
out_file = OUTPUT_DIR / "dynamic_vs_air_braking.png"
plt.savefig(out_file, dpi=300, bbox_inches='tight')
print(f"Saved plot to: {out_file}")
