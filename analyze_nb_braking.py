import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy.ndimage import gaussian_filter1d

# Configuration
INPUT_FILE = "results/henderson_nb_simulation_heavy.csv"
OUTPUT_DIR = Path("results/braking_analysis")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Visualization style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.size'] = 11
plt.rcParams['font.family'] = 'sans-serif'

print("="*80)
print("NORTHBOUND BRAKING FORCE ANALYSIS")
print("="*80)
print(f"\nLoading simulation data from: {INPUT_FILE}")
df = pd.read_csv(INPUT_FILE)

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
# F = P / v (avoid division by very small speeds)
df['F_dynamic_braking_N'] = np.where(
    df['pwr_whl_out_watts'] < 0,
    np.abs(df['pwr_whl_out_watts']) / np.maximum(df['speed_mps'], 1.0),
    0
)

# Air braking force (residual from force balance)
# Total braking = Dynamic + Air
# So: Air = Total - Dynamic
df['F_air_braking_N'] = np.maximum(0, -(df['F_net_required_N'] + df['F_dynamic_braking_N']))

# Apply smoothing to remove calculation noise
df['F_dynamic_braking_N'] = gaussian_filter1d(df['F_dynamic_braking_N'], sigma=2)
df['F_air_braking_N'] = gaussian_filter1d(df['F_air_braking_N'], sigma=2)

# Convert to kN for readability
df['F_dynamic_kN'] = df['F_dynamic_braking_N'] / 1000
df['F_air_kN'] = df['F_air_braking_N'] / 1000
df['F_total_brake_kN'] = (df['F_dynamic_braking_N'] + df['F_air_braking_N']) / 1000
df['F_resistance_kN'] = df['F_resistance_N'] / 1000

# Milepost calculation - Account for 50km buffer zone
# The simulation starts 50km before the actual track (buffer zone)
BUFFER_OFFSET_M = 50000  # 50km buffer at start
df['milepost'] = (df['total_dist_meters'] - BUFFER_OFFSET_M) / 1609.34 + 242

# Filter to only the actual route segment (MP 242 to 252)
# Exclude buffer zones for clean visualization
df = df[(df['milepost'] >= 242) & (df['milepost'] <= 252.5)].copy()
df = df.reset_index(drop=True)

if len(df) == 0:
    print("\nERROR: No data in milepost range 242-252!")
    print("Please check buffer offset calculation.")
    exit(1)

# Summary statistics
print("\n" + "="*80)
print("BRAKING FORCE SUMMARY")
print("="*80)
print(f"Total Simulation Time: {df['time_seconds'].iloc[-1]:.1f} seconds ({df['time_seconds'].iloc[-1]/60:.1f} minutes)")
print(f"Total Distance: {df['total_dist_meters'].iloc[-1]/1000:.2f} km")
print(f"Max Speed: {df['speed_mps'].max() * 2.237:.1f} mph")
print(f"Train Mass: {df['mass_kg'].iloc[0]/1000:.1f} tonnes")
print(f"\nDynamic Braking (Locomotive-Applied):")
print(f"  Maximum Force: {df['F_dynamic_kN'].max():.1f} kN")
print(f"  Mean (when active > 5kN): {df[df['F_dynamic_kN'] > 5]['F_dynamic_kN'].mean():.1f} kN")
print(f"  Active for: {(df['F_dynamic_kN'] > 5).sum()} / {len(df)} timesteps ({100*(df['F_dynamic_kN'] > 5).sum()/len(df):.1f}%)")
print(f"\nAir Braking (Distributed):")
print(f"  Maximum Force: {df['F_air_kN'].max():.1f} kN")
print(f"  Mean (when active > 5kN): {df[df['F_air_kN'] > 5]['F_air_kN'].mean():.1f} kN")
print(f"  Active for: {(df['F_air_kN'] > 5).sum()} / {len(df)} timesteps ({100*(df['F_air_kN'] > 5).sum()/len(df):.1f}%)")
print("="*80)

# ============================================================================
# VISUALIZATION 1: Braking Forces vs Milepost (Clean, Professional)
# ============================================================================
print("\n[1/4] Generating: Braking Forces vs Milepost...")

fig, ax = plt.subplots(figsize=(16, 6))

# Plot with distinct colors and proper styling
ax.fill_between(df['milepost'], 0, df['F_dynamic_kN'], 
                 alpha=0.4, color='#E63946', label='Dynamic Braking (Locomotives)', linewidth=0)
ax.plot(df['milepost'], df['F_dynamic_kN'], 
        color='#E63946', linewidth=2, alpha=0.9)

ax.fill_between(df['milepost'], 0, df['F_air_kN'], 
                 alpha=0.3, color='#1D3557', label='Air Braking (Distributed)', linewidth=0)
ax.plot(df['milepost'], df['F_air_kN'], 
        color='#1D3557', linewidth=2, alpha=0.9)

ax.plot(df['milepost'], df['F_total_brake_kN'], 
        label='Total Braking', color='#000000', linewidth=2.5, linestyle='--', alpha=0.6)

# Mark MP 242 as route start
ax.axvline(242, color='#2A9D8F', linewidth=2, linestyle=':', alpha=0.7, 
           label='MP 242 (Route Start)')
ax.axhline(0, color='gray', linewidth=0.8, linestyle='-', alpha=0.4)

ax.set_xlabel('Milepost', fontsize=13, fontweight='bold')
ax.set_ylabel('Braking Force (kN)', fontsize=13, fontweight='bold')
ax.set_title('Northbound Braking Force Distribution: Dynamic vs Air', 
             fontsize=15, fontweight='bold', pad=20)

# Relocate legend to upper LEFT to avoid overlap
ax.legend(loc='upper left', fontsize=11, framealpha=0.98, edgecolor='gray')
ax.grid(True, alpha=0.25, linewidth=0.5)

# Force x-axis to start at MP 242
ax.set_xlim(242, df['milepost'].max())

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "01_braking_forces_vs_milepost.png", dpi=300, bbox_inches='tight')
print(f"   Saved: {OUTPUT_DIR / '01_braking_forces_vs_milepost.png'}")
plt.close()

# ============================================================================
# VISUALIZATION 2: Force Balance with Speed Profile
# ============================================================================
print("[2/4] Generating: Force Balance Analysis...")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 9), sharex=True, 
                                gridspec_kw={'height_ratios': [2, 1]})

# Top panel: Force balance
ax1.plot(df['milepost'], df['F_resistance_kN'], 
         label='Resistance Forces (Grade + Rolling + Aero + Curve)', 
         color='#2A9D8F', linewidth=2.5, alpha=0.9)
ax1.plot(df['milepost'], df['F_total_brake_kN'], 
         label='Total Braking Force', 
         color='#E63946', linewidth=2.5, alpha=0.9)
ax1.fill_between(df['milepost'], 0, df['F_resistance_kN'], 
                  alpha=0.2, color='#2A9D8F')
ax1.fill_between(df['milepost'], 0, df['F_total_brake_kN'], 
                  alpha=0.2, color='#E63946')

# Mark MP 242
ax1.axvline(242, color='#555555', linewidth=2, linestyle=':', alpha=0.6)
ax1.axhline(0, color='black', linewidth=1, linestyle='-', alpha=0.3)
ax1.set_ylabel('Force (kN)', fontsize=13, fontweight='bold')
ax1.set_title('Force Balance: Resistance vs Braking', fontsize=15, fontweight='bold', pad=15)
ax1.legend(loc='upper left', fontsize=11, framealpha=0.98)
ax1.grid(True, alpha=0.25)
ax1.set_xlim(242, df['milepost'].max())

# Bottom panel: Speed profile
ax2.plot(df['milepost'], df['speed_mps'] * 2.237, 
         color='#457B9D', linewidth=3, alpha=0.95)
ax2.fill_between(df['milepost'], 0, df['speed_mps'] * 2.237, 
                  alpha=0.35, color='#457B9D')

# Mark MP 242
ax2.axvline(242, color='#555555', linewidth=2, linestyle=':', alpha=0.6, 
            label='MP 242 (Start)')
ax2.set_xlabel('Milepost', fontsize=13, fontweight='bold')
ax2.set_ylabel('Speed (mph)', fontsize=13, fontweight='bold')
ax2.set_title('Train Speed Profile', fontsize=14, fontweight='bold', pad=12)
ax2.legend(loc='lower right', fontsize=10, framealpha=0.95)
ax2.grid(True, alpha=0.25)
ax2.set_xlim(242, df['milepost'].max())

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "02_force_balance_speed.png", dpi=300, bbox_inches='tight')
print(f"   Saved: {OUTPUT_DIR / '02_force_balance_speed.png'}")
plt.close()

# ============================================================================
# VISUALIZATION 3: Braking Event Breakdown (COMPLETE ROUTE - NO FILTER)
# ============================================================================
print("[3/4] Generating: Braking Event Breakdown...")

# Use ALL data from MP 242-252 (no threshold filter)
braking_df = df.copy()

fig, axes = plt.subplots(4, 1, figsize=(16, 12), sharex=True)

# Panel 1: Braking force breakdown
axes[0].plot(braking_df['milepost'], braking_df['F_dynamic_kN'], 
             label='Dynamic (Locomotive)', color='#E63946', linewidth=2.5)
axes[0].plot(braking_df['milepost'], braking_df['F_air_kN'], 
             label='Air (Distributed)', color='#1D3557', linewidth=2.5)
axes[0].set_ylabel('Force (kN)', fontweight='bold', fontsize=12)
axes[0].set_title('Braking Force Breakdown (Complete Route MP 242-252)', 
                  fontsize=14, fontweight='bold', pad=12)
axes[0].legend(loc='best', fontsize=10)
axes[0].grid(True, alpha=0.3)

# Panel 2: Wheel power
axes[1].plot(braking_df['milepost'], braking_df['pwr_whl_out_watts'] / 1e6, 
             color='#9B59B6', linewidth=2.5)
axes[1].axhline(0, color='black', linewidth=0.8, linestyle='--', alpha=0.5)
axes[1].set_ylabel('Power (MW)', fontweight='bold', fontsize=12)
axes[1].set_title('Locomotive Wheel Power (Negative = Regenerative Braking)', 
                  fontsize=13, fontweight='bold', pad=10)
axes[1].grid(True, alpha=0.3)

# Panel 3: Deceleration
axes[2].plot(braking_df['milepost'], braking_df['accel_ms2'], 
             color='#E74C3C', linewidth=2.5)
axes[2].axhline(0, color='black', linewidth=0.8, linestyle='--', alpha=0.5)
axes[2].set_ylabel('Accel (m/s²)', fontweight='bold', fontsize=12)
axes[2].set_title('Train Acceleration/Deceleration', fontsize=13, fontweight='bold', pad=10)
axes[2].grid(True, alpha=0.3)

# Panel 4: Speed during braking
axes[3].plot(braking_df['milepost'], braking_df['speed_mps'] * 2.237, 
             color='#27AE60', linewidth=2.5)
axes[3].fill_between(braking_df['milepost'], 0, braking_df['speed_mps'] * 2.237, 
                      alpha=0.3, color='#27AE60')
axes[3].set_xlabel('Milepost', fontweight='bold', fontsize=13)
axes[3].set_ylabel('Speed (mph)', fontweight='bold', fontsize=12)
axes[3].set_title('Speed Profile', fontsize=13, fontweight='bold', pad=10)
axes[3].grid(True, alpha=0.3)
axes[3].set_xlim(242, braking_df['milepost'].max())

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "03_braking_event_breakdown.png", dpi=300, bbox_inches='tight')
print(f"   Saved: {OUTPUT_DIR / '03_braking_event_breakdown.png'}")
plt.close()


# ============================================================================
# VISUALIZATION 4: Spatial Distribution (Train Diagram)
# ============================================================================
print("[4/4] Generating: Spatial Force Distribution...")

# Train parameters (from simulation config)
num_locos = 2
num_cars = 10
loco_length = 26.0  # meters each
car_length = 26.0  # meters each
train_length = (num_locos + num_cars) * 26.0  # Total ~312m

# Calculate average forces for spatial distribution
avg_dynamic = df['F_dynamic_kN'].mean()
avg_air = df['F_air_kN'].mean()

# Create spatial bins along train
n_bins = 100
positions = np.linspace(0, train_length, n_bins)

# Dynamic braking only at locomotives (front)
loco_section_end = num_locos * loco_length
dynamic_density = np.where(positions < loco_section_end, 
                            avg_dynamic / loco_section_end, 0)

# Air braking distributed uniformly
air_density = np.ones_like(positions) * (avg_air / train_length)

fig, ax = plt.subplots(figsize=(16, 6))

# Plot force densities
ax.fill_between(positions, 0, dynamic_density, 
                 alpha=0.6, color='#E63946', label='Dynamic Braking (Concentrated at Locomotives)')
ax.fill_between(positions, 0, air_density, 
                 alpha=0.5, color='#1D3557', label='Air Braking (Uniformly Distributed)')

# Mark locomotive section
ax.axvline(loco_section_end, color='#E63946', linestyle='--', linewidth=3, alpha=0.8, 
           label=f'Locomotive Section (0-{loco_section_end:.0f}m)')

# Annotations
ax.annotate('LOCOMOTIVES\n(Dynamic Braking Applied Here)', 
            xy=(loco_section_end/2, dynamic_density.max() * 0.7), 
            fontsize=12, ha='center', va='center', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.8', facecolor='#E63946', alpha=0.25, edgecolor='#E63946', linewidth=2))
ax.annotate('PASSENGER CARS\n(Air Braking Only)', 
            xy=((loco_section_end + train_length)/2, air_density.mean() * 1.5), 
            fontsize=12, ha='center', va='center', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.8', facecolor='#1D3557', alpha=0.25, edgecolor='#1D3557', linewidth=2))

ax.set_xlabel('Position Along Train (meters from front)', fontsize=13, fontweight='bold')
ax.set_ylabel('Force Density (kN/m)', fontsize=13, fontweight='bold')
ax.set_title('Spatial Distribution: Where Braking Forces Are Applied Along Train', 
             fontsize=15, fontweight='bold', pad=20)
ax.legend(loc='upper right', fontsize=11, framealpha=0.98)
ax.grid(True, alpha=0.25, axis='y')
ax.set_xlim(0, train_length)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "04_spatial_force_distribution.png", dpi=300, bbox_inches='tight')
print(f"   Saved: {OUTPUT_DIR / '04_spatial_force_distribution.png'}")
plt.close()

# ============================================================================
# Export analyzed data
# ============================================================================
print("\nExporting analyzed data...")
output_cols = [
    'time_seconds', 'milepost', 'speed_mps', 'accel_ms2',
    'F_dynamic_kN', 'F_air_kN', 'F_total_brake_kN', 'F_resistance_kN',
    'pwr_whl_out_watts', 'res_grade_newtons', 'res_curve_newtons',
    'res_rolling_newtons', 'res_aero_newtons'
]
df[output_cols].to_csv(OUTPUT_DIR / "braking_forces_data.csv", index=False)
print(f"   Saved: {OUTPUT_DIR / 'braking_forces_data.csv'}")

print("\n" + "="*80)
print("ANALYSIS COMPLETE!")
print("="*80)
print(f"Output Directory: {OUTPUT_DIR.absolute()}")
print("\nGenerated Visualizations:")
print("  [1] 01_braking_forces_vs_milepost.png - Main braking force distribution")
print("  [2] 02_force_balance_speed.png - Force balance with speed profile")
print("  [3] 03_braking_event_breakdown.png - Detailed breakdown of braking events")
print("  [4] 04_spatial_force_distribution.png - Where forces are applied on train")
print("\nData Export:")
print("  braking_forces_data.csv - Complete analysis dataset")
print("="*80)
