import matplotlib; matplotlib.use("Agg")
#!/usr/bin/env python3
"""
analyze_track_demand.py
Spatially maps dynamic and static forces exerted by a train onto 0.05-mile track segments.
"""

import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
import seaborn as sns
plt.rcParams['axes.prop_cycle'] = plt.cycler(color=['#FF0000', '#0000FF', '#FF9900', '#24E780', '#00FFFF', '#FF00FF', '#993366', '#969696'])
sns.set_palette(['#FF0000', '#0000FF', '#FF9900', '#24E780', '#00FFFF', '#FF00FF', '#993366', '#969696'])

import seaborn as sns
from pathlib import Path
from scipy.ndimage import gaussian_filter1d

# Train Dimensions
LOCO_LEN_M = 23.0 * 4
CAR_LEN_M = 18.0 * 100
LOCO_LEN_MI = LOCO_LEN_M / 1609.34
CAR_LEN_MI = CAR_LEN_M / 1609.34
LOCO_MASS_KG = 195000.0 * 4
CAR_MASS_KG = 131500.0 * 100
LOCO_VERT_KN = LOCO_MASS_KG * 9.81 / 1000.0
CAR_VERT_KN = CAR_MASS_KG * 9.81 / 1000.0

# Binning
BIN_SIZE_MI = 0.05
MP_MIN = 176.9
MP_MAX = 318.4
BINS = np.arange(MP_MIN, MP_MAX + BIN_SIZE_MI, BIN_SIZE_MI)
BIN_CENTERS = BINS[:-1] + BIN_SIZE_MI / 2.0

def process_simulation(csv_path, is_sb=False):
    print(f"Processing {'Southbound' if is_sb else 'Northbound'} simulation...")
    df = pd.read_csv(csv_path)
    df = df[(df['milepost'] >= MP_MIN) & (df['milepost'] <= MP_MAX)].copy()

    # Physics logic based on previous analysis
    df['speed_mps'] = df['speed_meters_per_second']
    df['accel_ms2'] = df['speed_mps'].diff().fillna(0) / df['dt_seconds']
    df['accel_ms2'] = gaussian_filter1d(df['accel_ms2'], sigma=3)
    
    df['F_resistance_N'] = (df['res_grade_newtons'] + df['res_curve_newtons'] + 
                            df['res_rolling_newtons'] + df['res_aero_newtons'] + df['res_bearing_newtons'])
    df['F_net_required_N'] = df['mass_static_kilograms'] * df['accel_ms2'] + df['F_resistance_N']
    
    df['F_dyn_brake_kN'] = np.where(df['pwr_whl_out_watts'] < 0, 
                                    np.abs(df['pwr_whl_out_watts']) / np.maximum(df['speed_mps'], 1.0), 0) / 1000.0
    df['F_traction_kN'] = np.where(df['pwr_whl_out_watts'] > 0, 
                                   df['pwr_whl_out_watts'] / np.maximum(df['speed_mps'], 1.0), 0) / 1000.0
    
    df['F_air_brake_kN'] = np.maximum(0, -(df['F_net_required_N'] / 1000.0 + df['F_dyn_brake_kN']))
    
    # Smoothing
    df['F_dyn_brake_kN'] = gaussian_filter1d(df['F_dyn_brake_kN'], sigma=2)
    df['F_air_brake_kN'] = gaussian_filter1d(df['F_air_brake_kN'], sigma=2)

    # Output arrays mapped to BIN_CENTERS
    n_bins = len(BIN_CENTERS)
    track_traction_kN = np.zeros(n_bins)
    track_dyn_brake_kN = np.zeros(n_bins)
    track_air_brake_kN = np.zeros(n_bins)
    track_vert_kN = np.zeros(n_bins)
    
    mps = df['milepost'].values
    trac = df['F_traction_kN'].values
    dyn = df['F_dyn_brake_kN'].values
    air = df['F_air_brake_kN'].values
    dts = df['dt_seconds'].values
    
    for i in range(len(df)):
        mp = mps[i]
        dt = dts[i]
        
        # Determine occupied span
        if is_sb:
            # Traveling south: front is at MP, rear is at MP + length
            loco_start, loco_end = mp, mp + LOCO_LEN_MI
            car_start, car_end = mp + LOCO_LEN_MI, mp + LOCO_LEN_MI + CAR_LEN_MI
        else:
            # Traveling north: front is at MP, rear is at MP - length
            loco_start, loco_end = mp - LOCO_LEN_MI, mp
            car_start, car_end = mp - LOCO_LEN_MI - CAR_LEN_MI, mp - LOCO_LEN_MI
            
        # Distribute forces per second over the footprint lengths
        # Note: integration over time gives cumulative Demand (kN*s), which is Impulse.
        # But we want total spatial concentration. Wait, total force applied or sum of forces 
        # observed at each bin per timestep?
        # Summing Force * dt gives kN*s (Impulse) deposited on the track.
        
        # Locomotives (Traction and Dynamic Braking)
        # Bins overlapping loco_start to loco_end
        loco_bins = np.where((BIN_CENTERS >= loco_start) & (BIN_CENTERS <= loco_end))[0]
        if len(loco_bins) > 0:
            track_traction_kN[loco_bins] += trac[i] * dt / len(loco_bins)
            track_dyn_brake_kN[loco_bins] += dyn[i] * dt / len(loco_bins)
            track_vert_kN[loco_bins] += LOCO_VERT_KN * dt / len(loco_bins)
            
        # Freight Cars (Air Braking)
        car_bins = np.where((BIN_CENTERS >= car_start) & (BIN_CENTERS <= car_end))[0]
        if len(car_bins) > 0:
            track_air_brake_kN[car_bins] += air[i] * dt / len(car_bins)
            track_vert_kN[car_bins] += CAR_VERT_KN * dt / len(car_bins)
            
    return track_traction_kN, track_dyn_brake_kN, track_air_brake_kN, track_vert_kN

# Process
nb_trac, nb_dyn, nb_air, nb_vert = process_simulation("results/henderson_full_sim/nb_simulation.csv", is_sb=False)
sb_trac, sb_dyn, sb_air, sb_vert = process_simulation("results/henderson_sb_sim/sb_simulation.csv", is_sb=True)

# Total Demand
total_loco_demand = nb_trac + nb_dyn + sb_trac + sb_dyn
total_car_demand = nb_air + sb_air
total_vert_demand = nb_vert + sb_vert

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

COLORS = ['#FF0000', '#0000FF', '#FF9900', '#24E780', '#00FFFF', '#FF00FF', '#993366', '#969696']
plt.rcParams['axes.prop_cycle'] = plt.cycler(color=COLORS)
sns.set_palette(COLORS)

plt.rcParams.update({'figure.dpi': 150, 'font.family': 'Arial'})
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 10), sharex=True, gridspec_kw={'height_ratios': [1.5, 1]})

# Top Plot: Longitudinal Shear
ax1.fill_between(BIN_CENTERS, 0, total_loco_demand, alpha=0.6, color=COLORS[0], label='Locomotive Demand (Traction + Dynamic Braking)')
ax1.fill_between(BIN_CENTERS, 0, total_car_demand, alpha=0.6, color=COLORS[1], label='Freight Car Demand (Air Braking)')

ax1.set_title("Cumulative Longitudinal Shear Demand (Northbound + Southbound)", fontsize=16, fontweight='bold', pad=15)
ax1.set_ylabel("Shear Impulse (kN·s)", fontsize=14, fontweight='bold')
ax1.grid(True, linestyle='--', alpha=0.5)

# Bottom Plot: Vertical Load
ax2.plot(BIN_CENTERS, total_vert_demand / 1e6, color=COLORS[2], linewidth=2, label='Total Vertical Impulse')
ax2.fill_between(BIN_CENTERS, 0, total_vert_demand / 1e6, alpha=0.3, color=COLORS[2])
ax2.set_title("Cumulative Vertical Track Demand (Northbound + Southbound)", fontsize=16, fontweight='bold', pad=10)
ax2.set_xlabel("Milepost", fontsize=14, fontweight='bold')
ax2.set_ylabel("Vertical Impulse (GN·s)", fontsize=14, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.5)

ax1.set_xlim(MP_MIN, MP_MAX)

out_dir = Path("results/track_demand")
out_dir.mkdir(exist_ok=True, parents=True)

import pandas as pd
demand_df = pd.DataFrame({
    'milepost': BIN_CENTERS,
    'loco_shear_kNs': total_loco_demand,
    'car_shear_kNs': total_car_demand,
    'total_shear_kNs': total_loco_demand + total_car_demand,
    'total_vert_GNs': total_vert_demand / 1e6
})
demand_df.to_csv(out_dir / "demand_bins.csv", index=False)
print(f"Saved: {out_dir / 'demand_bins.csv'}")

out_file = out_dir / "cumulative_track_demand.png"
plt.tight_layout()
plt.savefig(out_file)
print(f"Saved: {out_file}")
