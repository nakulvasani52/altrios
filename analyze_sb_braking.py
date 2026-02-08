import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy.ndimage import gaussian_filter1d

# Configuration
INPUT_FILE = "results/henderson_sb_simulation_heavy.csv"
OUTPUT_DIR = Path("results/braking_analysis_sb")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Visualization style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.size'] = 11
plt.rcParams['font.family'] = 'sans-serif'

print("="*80)
print("SOUTHBOUND BRAKING FORCE ANALYSIS")
print("="*80)
print(f"\nLoading simulation data from: {INPUT_FILE}")
try:
    df = pd.read_csv(INPUT_FILE)
except FileNotFoundError:
    print("Error: Input file not found. Run simulation first.")
    exit(1)

# Calculate derived metrics
print("Calculating braking forces using Steven's methodology...")

# Speed in m/s
df['speed_mps'] = df['speed_meters_per_second']

# Calculate acceleration (m/s²) with smoothing
df['accel_ms2'] = df['speed_mps'].diff() / df['dt_seconds']
df['accel_ms2'] = gaussian_filter1d(df['accel_ms2'].fillna(0), sigma=3)  # Smooth noise

# Total mass (kg)
df['mass_kg'] = df['mass_static_kilograms']

# Total resistance force (N)
df['F_resistance_N'] = (
    df['res_grade_newtons'] + 
    df['res_curve_newtons'] + 
    df['res_rolling_newtons'] + 
    df['res_aero_newtons'] + 
    df['res_bearing_newtons']
)

# Net force required (Newton's 2nd Law: F = ma + F_resistance)
df['F_net_required_N'] = df['mass_kg'] * df['accel_ms2'] + df['F_resistance_N']

# Dynamic braking force (from locomotive wheel power)
# When pwr_whl_out < 0, locomotive is in regenerative braking mode
df['F_dynamic_braking_N'] = np.where(
    df['pwr_whl_out_watts'] < 0,
    np.abs(df['pwr_whl_out_watts']) / np.maximum(df['speed_mps'], 1.0),
    0
)

# Air braking force (residual from force balance)
df['F_air_braking_N'] = np.maximum(0, -(df['F_net_required_N'] + df['F_dynamic_braking_N']))

# Apply smoothing
df['F_dynamic_braking_N'] = gaussian_filter1d(df['F_dynamic_braking_N'], sigma=2)
df['F_air_braking_N'] = gaussian_filter1d(df['F_air_braking_N'], sigma=2)

# Convert to kN
df['F_dynamic_kN'] = df['F_dynamic_braking_N'] / 1000
df['F_air_kN'] = df['F_air_braking_N'] / 1000
df['F_total_brake_kN'] = (df['F_dynamic_braking_N'] + df['F_air_braking_N']) / 1000
df['F_resistance_kN'] = df['F_resistance_N'] / 1000

# Milepost calculation - Southbound travel (MP 252 -> 242)
BUFFER_OFFSET_M = 50000 
# SP direction travels from MP 252.7 downwards
df['milepost'] = 252.7 - (df['total_dist_meters'] - BUFFER_OFFSET_M) / 1609.34

# Filter to actual route
df = df[(df['milepost'] >= 241.5) & (df['milepost'] <= 253.5)].copy()
df = df.reset_index(drop=True)

if len(df) == 0:
    print("\nERROR: No data in milepost range 242-252!")
    exit(1)

# Summary statistics
print("\n" + "="*80)
print("BRAKING FORCE SUMMARY (Southbound)")
print("="*80)
print(f"Total Simulation Time: {df['time_seconds'].max() - df['time_seconds'].min():.1f} seconds")
print(f"Max Speed: {df['speed_mps'].max() * 2.237:.1f} mph")
print(f"Train Mass: {df['mass_kg'].iloc[0]/1000:.1f} tonnes")
print(f"\nDynamic Braking (Locomotive-Applied):")
print(f"  Maximum Force: {df['F_dynamic_kN'].max():.1f} kN")
print(f"\nAir Braking (Distributed):")
print(f"  Maximum Force: {df['F_air_kN'].max():.1f} kN")
print("="*80)

# Visualizations (matching NB format)
print("\n[1/4] Generating: Braking Forces vs Milepost...")
fig, ax = plt.subplots(figsize=(16, 6))
ax.fill_between(df['milepost'], 0, df['F_dynamic_kN'], alpha=0.4, color='#E63946', label='Dynamic Braking')
ax.fill_between(df['milepost'], 0, df['F_air_kN'], alpha=0.3, color='#1D3557', label='Air Braking')
ax.plot(df['milepost'], df['F_total_brake_kN'], label='Total Braking', color='black', linestyle='--')
ax.set_xlabel('Milepost', fontweight='bold')
ax.set_ylabel('Force (kN)', fontweight='bold')
ax.set_title('Southbound Braking Force Distribution', fontweight='bold')
ax.legend()
ax.invert_xaxis() # Southbound travel: left (252) to right (242)
plt.savefig(OUTPUT_DIR / "01_sb_braking_forces_vs_milepost.png", dpi=300)
plt.close()

print("[2/4] Generating: Force Balance Analysis...")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 9), sharex=True)
ax1.plot(df['milepost'], df['F_resistance_kN'], color='#2A9D8F', label='Resistance')
ax1.plot(df['milepost'], df['F_total_brake_kN'], color='#E63946', label='Braking')
ax1.set_ylabel('Force (kN)')
ax1.legend()
ax2.plot(df['milepost'], df['speed_mps'] * 2.237, color='#457B9D')
ax2.set_ylabel('Speed (mph)')
ax2.set_xlabel('Milepost')
ax1.invert_xaxis()
plt.savefig(OUTPUT_DIR / "02_sb_force_balance_speed.png", dpi=300)
plt.close()

print("[3/4] Generating: Braking Event Breakdown...")
fig, axes = plt.subplots(4, 1, figsize=(16, 12), sharex=True)
axes[0].plot(df['milepost'], df['F_dynamic_kN'], color='#E63946', label='Dynamic')
axes[0].plot(df['milepost'], df['F_air_kN'], color='#1D3557', label='Air')
axes[1].plot(df['milepost'], df['pwr_whl_out_watts'] / 1e6, color='#9B59B6')
axes[2].plot(df['milepost'], df['accel_ms2'], color='#E74C3C')
axes[3].plot(df['milepost'], df['speed_mps'] * 2.237, color='#27AE60')
axes[3].invert_xaxis()
plt.savefig(OUTPUT_DIR / "03_sb_braking_event_breakdown.png", dpi=300)
plt.close()

print("[4/4] Generating: Spatial Force Distribution...")
num_locos = 2; num_cars = 50; train_length = (num_locos + num_cars) * 26.0
avg_dynamic = df['F_dynamic_kN'].mean(); avg_air = df['F_air_kN'].mean()
positions = np.linspace(0, train_length, 100)
loco_section_end = num_locos * 26.0
dynamic_density = np.where(positions < loco_section_end, avg_dynamic / loco_section_end, 0)
air_density = np.ones_like(positions) * (avg_air / train_length)
fig, ax = plt.subplots(figsize=(16, 6))
ax.fill_between(positions, 0, dynamic_density, color='#E63946', label='Dynamic')
ax.fill_between(positions, 0, air_density, color='#1D3557', alpha=0.5, label='Air')
ax.set_xlabel('Position Along Train (m)')
ax.set_ylabel('Force Density (kN/m)')
ax.set_title('Southbound Spatial Distribution')
plt.savefig(OUTPUT_DIR / "04_sb_spatial_force_distribution.png", dpi=300)
plt.close()

print("\nAnalysis Complete.")
