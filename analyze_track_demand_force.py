"""
analyze_track_demand_force.py
----------------------------
Force-magnitude based spatial track demand (Peak Force Envelope).
Resolution: 10 foot bins.
FORCE DENSITY LOGIC: Distributes total train force across the footprint length.
"""
import matplotlib; matplotlib.use("Agg")
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.ndimage import gaussian_filter1d

# Styling
COLORS = ["#FF0000", "#0000FF", "#993366", "#24E780", "#00FFFF", "#FF00FF", "#969696"]
plt.rcParams.update({
    "figure.dpi": 200,
    "savefig.dpi": 300,
    "font.family": "Arial",
    "axes.grid": True,
    "grid.alpha": 0.2,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})
FS_TITLE, FS_LABEL, FS_TICK = 22, 18, 16

# ── Train Dimensions ─────────────────────────────────────────────────────────
LOCO_LEN_M = 23.0 * 4
CAR_LEN_M  = 18.0 * 100
LOCO_LEN_MI = LOCO_LEN_M / 1609.34
CAR_LEN_MI  = CAR_LEN_M / 1609.34

# ── Spatial Bins (10 feet) ───────────────────────────────────────────────────
FT_TO_MI = 1.0 / 5280.0
BIN_SIZE_MI = 10.0 * FT_TO_MI 

MP_MIN, MP_MAX = 176.9, 318.4
BINS = np.arange(MP_MIN, MP_MAX + BIN_SIZE_MI, BIN_SIZE_MI)
BIN_CENTERS = BINS[:-1] + BIN_SIZE_MI / 2.0

def generate_peak_envelope(csv_path, is_sb=False):
    print(f"Generating 10ft Peak Envelope (Force Density) for {'Southbound' if is_sb else 'Northbound'}...")
    df = pd.read_csv(csv_path)
    df = df[(df['milepost'] >= MP_MIN) & (df['milepost'] <= MP_MAX)].copy()

    speed_mps = df['speed_meters_per_second'].values
    F_total_loco_kN = np.abs(df['pwr_whl_out_watts'].values) / np.maximum(speed_mps, 0.5) / 1000.0
    
    accel = gaussian_filter1d(df['speed_meters_per_second'].diff().fillna(0).values / df['dt_seconds'].values, sigma=2)
    F_res_N = (df['res_grade_newtons'] + df['res_curve_newtons'] + 
               df['res_rolling_newtons'] + df['res_aero_newtons'] + df['res_bearing_newtons']).values
    F_net_req_N = df['mass_static_kilograms'].values * accel + F_res_N
    F_total_air_kN = np.maximum(0, -(F_net_req_N/1000.0 + F_total_loco_kN))

    mps = df['milepost'].values
    n_bins = len(BIN_CENTERS)
    peak_loco = np.zeros(n_bins)
    peak_air  = np.zeros(n_bins)

    for i in range(len(df)):
        mp = mps[i]
        # Calculate force density (kN per mile)
        rho_loco = F_total_loco_kN[i] / LOCO_LEN_MI
        rho_air  = F_total_air_kN[i] / CAR_LEN_MI
        
        # Local force per 10ft bin = rho * bin_size_mi
        f_loco_bin = rho_loco * BIN_SIZE_MI
        f_air_bin  = rho_air * BIN_SIZE_MI
        
        if is_sb:
            l_start, l_end = mp, mp + LOCO_LEN_MI
            c_start, c_end = mp + LOCO_LEN_MI, mp + LOCO_LEN_MI + CAR_LEN_MI
        else:
            l_start, l_end = mp - LOCO_LEN_MI, mp
            c_start, c_end = mp - LOCO_LEN_MI - CAR_LEN_MI, mp - LOCO_LEN_MI
            
        l_idx = np.where((BIN_CENTERS >= l_start) & (BIN_CENTERS <= l_end))[0]
        if len(l_idx) > 0:
            peak_loco[l_idx] = np.maximum(peak_loco[l_idx], f_loco_bin)
            
        c_idx = np.where((BIN_CENTERS >= c_start) & (BIN_CENTERS <= c_end))[0]
        if len(c_idx) > 0:
            peak_air[c_idx] = np.maximum(peak_air[c_idx], f_air_bin)
            
    return peak_loco, peak_air

nb_loco, nb_air = generate_peak_envelope("results/henderson_full_sim/nb_simulation.csv", is_sb=False)
sb_loco, sb_air = generate_peak_envelope("results/henderson_sb_sim/sb_simulation.csv", is_sb=True)

# Combine using maximum across both runs
total_loco = np.maximum(nb_loco, sb_loco)
total_air  = np.maximum(nb_air, sb_air)

total_loco = gaussian_filter1d(total_loco, sigma=5) # More smoothing for 10ft grit
total_air  = gaussian_filter1d(total_air, sigma=5)

fig, ax = plt.subplots(figsize=(22, 10))

ax.fill_between(BIN_CENTERS, 0, total_air, color=COLORS[1], alpha=0.35, label="Freight Consist (Air Braking Peak)")
ax.plot(BIN_CENTERS, total_air, color=COLORS[1], linewidth=1.0, alpha=0.5)

ax.fill_between(BIN_CENTERS, 0, total_loco, color=COLORS[0], alpha=0.45, label="Locomotive Block (Traction/DynBrake Peak)")
ax.plot(BIN_CENTERS, total_loco, color=COLORS[0], linewidth=1.0, alpha=0.6)

ax.set_title("Localized Force Demand: 10-Foot Bin High-Resolution Analysis", 
             fontsize=FS_TITLE, fontweight='bold', pad=20)
ax.set_xlabel("Milepost", fontsize=FS_LABEL, fontweight='bold')
ax.set_ylabel("Maximum Instantaneous Force per 10ft Segment (kN)", fontsize=FS_LABEL, fontweight='bold')
ax.legend(fontsize=16, frameon=True, loc='upper right')
ax.tick_params(labelsize=FS_TICK)
ax.set_xlim(MP_MIN, MP_MAX)
ax.set_ylim(0, max(max(total_loco), max(total_air))*1.25)

plt.tight_layout()
OUT_DIR = Path("/Users/nakulvasani/Desktop/Lunch Meeting")
OUT_DIR.mkdir(parents=True, exist_ok=True)
save_path = OUT_DIR / "Spatial_Force_Demand_10ft.png"
plt.savefig(save_path, bbox_inches='tight')
print(f"Generated 10ft peak-envelope visualization: {save_path}")

data_path = Path("results/track_demand/peak_force_demand_10ft.csv")
data_path.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame({
    'milepost': BIN_CENTERS,
    'peak_loco_kN_10ft': total_loco,
    'peak_air_kN_10ft': total_air
}).to_csv(data_path, index=False)
print("Done.")
