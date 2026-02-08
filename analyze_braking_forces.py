import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Configuration
INPUT_FILE = "results/henderson_nb_simulation.csv"
OUTPUT_DIR = Path("results/presentation")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Visualization style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.size'] = 10

print("Loading simulation data...")
df = pd.read_csv(INPUT_FILE)

# Calculate derived metrics
print("Calculating braking forces...")

# Speed in m/s
df['speed_mps'] = df['speed_meters_per_second']

# Calculate acceleration (m/s²)
df['accel_ms2'] = df['speed_mps'].diff() / df['dt_seconds']
df['accel_ms2'] = df['accel_ms2'].fillna(0)

# Total mass (kg)
df['mass_kg'] = df['mass_static_kilograms']

# Total resistance force (N)
df['F_resistance_N'] = (
    df['res_grade_newtons'] + 
    df['res_curve_newtons'] + 
    df['res_rolling_newtons'] + 
    df['res_aero_newtons'] + 
    df['res_bearing_newtons'] + 
    df.get('res_davis_b_newtons', 0)
)

# Net force required to achieve observed acceleration (Newton's 2nd Law)
df['F_net_required_N'] = df['mass_kg'] * df['accel_ms2'] + df['F_resistance_N']

# Dynamic braking force (from locomotive wheel power)
# Negative pwr_whl_out means braking (regenerative)
df['F_dynamic_braking_N'] = np.where(
    df['pwr_whl_out_watts'] < 0,
    np.abs(df['pwr_whl_out_watts']) / np.maximum(df['speed_mps'], 0.1),  # Avoid div by zero
    0
)

# Air braking force (residual)
# F_air = F_net_required - (-F_dynamic)
# Note: Both braking forces resist motion (negative in our convention)
df['F_air_braking_N'] = df['F_net_required_N'] - (-df['F_dynamic_braking_N'])

# Convert to kN for readability
df['F_dynamic_kN'] = df['F_dynamic_braking_N'] / 1000
df['F_air_kN'] = df['F_air_braking_N'] / 1000
df['F_total_brake_kN'] = (df['F_dynamic_braking_N'] + df['F_air_braking_N']) / 1000
df['F_resistance_kN'] = df['F_resistance_N'] / 1000

# Milepost
df['milepost'] = df['total_dist_meters'] / 1609.34 + 242  # Start at MP 242

# Summary statistics
print("\n" + "="*60)
print("BRAKING FORCE ANALYSIS SUMMARY")
print("="*60)
print(f"Total Time: {df['time_seconds'].iloc[-1]:.1f} seconds")
print(f"Distance: {df['total_dist_meters'].iloc[-1]/1000:.2f} km")
print(f"Max Speed: {df['speed_mps'].max() * 2.237:.1f} mph")
print(f"\nBraking Force Statistics (kN):")
print(f"  Dynamic Braking:")
print(f"    Max: {df['F_dynamic_kN'].max():.1f} kN")
print(f"    Mean (when active): {df[df['F_dynamic_kN'] > 1]['F_dynamic_kN'].mean():.1f} kN")
print(f"  Air Braking:")
print(f"    Max: {df['F_air_kN'].max():.1f} kN")
print(f"    Mean (when active): {df[df['F_air_kN'] > 1]['F_air_kN'].mean():.1f} kN")
print("="*60)

# ============================================================================
# VISUALIZATION 1: Braking Forces vs Milepost
# ============================================================================
print("\nGenerating Visualization 1: Braking Forces vs Milepost...")

fig, ax = plt.subplots(figsize=(14, 5))

# Plot braking forces
ax.plot(df['milepost'], df['F_dynamic_kN'], 
        label='Dynamic Braking (Locomotive)', color='#FF6B35', linewidth=1.5, alpha=0.9)
ax.plot(df['milepost'], df['F_air_kN'], 
        label='Air Braking (Distributed)', color='#004E89', linewidth=1.5, alpha=0.9)
ax.plot(df['milepost'], df['F_total_brake_kN'], 
        label='Total Braking', color='#1A1A1A', linewidth=2, linestyle='--', alpha=0.7)

ax.axhline(0, color='gray', linewidth=0.5, linestyle=':')
ax.set_xlabel('Milepost', fontsize=11, fontweight='bold')
ax.set_ylabel('Braking Force (kN)', fontsize=11, fontweight='bold')
ax.set_title('Northbound Braking Force Distribution: Dynamic vs Air', 
             fontsize=13, fontweight='bold', pad=15)
ax.legend(loc='upper right', fontsize=9, framealpha=0.95)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "nb_braking_forces_vs_milepost.png", dpi=300, bbox_inches='tight')
print(f"  Saved: {OUTPUT_DIR / 'nb_braking_forces_vs_milepost.png'}")
plt.close()

# ============================================================================
# VISUALIZATION 2: Force Balance (Resistance vs Braking vs Speed)
# ============================================================================
print("\nGenerating Visualization 2: Force Balance Analysis...")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

# Top panel: Forces
ax1.plot(df['milepost'], df['F_resistance_kN'], 
         label='Total Resistance', color='#6A994E', linewidth=1.5, alpha=0.8)
ax1.plot(df['milepost'], -df['F_total_brake_kN'], 
         label='Total Braking (inverted)', color='#BC4749', linewidth=1.5, alpha=0.8)
ax1.fill_between(df['milepost'], 0, df['F_resistance_kN'], 
                  alpha=0.2, color='#6A994E', label='Resistance Area')
ax1.fill_between(df['milepost'], 0, -df['F_total_brake_kN'], 
                  alpha=0.2, color='#BC4749', label='Braking Area')

ax1.axhline(0, color='black', linewidth=1, linestyle='-', alpha=0.3)
ax1.set_ylabel('Force (kN)', fontsize=11, fontweight='bold')
ax1.set_title('Force Balance: Resistance vs Braking', fontsize=13, fontweight='bold', pad=10)
ax1.legend(loc='upper left', fontsize=9)
ax1.grid(True, alpha=0.3)

# Bottom panel: Speed
ax2.plot(df['milepost'], df['speed_mps'] * 2.237, 
         color='#4361EE', linewidth=2, alpha=0.9)
ax2.fill_between(df['milepost'], 0, df['speed_mps'] * 2.237, 
                  alpha=0.3, color='#4361EE')
ax2.set_xlabel('Milepost', fontsize=11, fontweight='bold')
ax2.set_ylabel('Speed (mph)', fontsize=11, fontweight='bold')
ax2.set_title('Train Speed Profile', fontsize=12, fontweight='bold', pad=10)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "nb_force_balance_analysis.png", dpi=300, bbox_inches='tight')
print(f"  Saved: {OUTPUT_DIR / 'nb_force_balance_analysis.png'}")
plt.close()

# ============================================================================
# VISUALIZATION 3: Braking Force Breakdown (Detailed)
# ============================================================================
print("\nGenerating Visualization 3: Detailed Braking Breakdown...")

# Create detailed view focusing on braking events
braking_threshold = 5  # kN
braking_events = df[df['F_total_brake_kN'] > braking_threshold].copy()

if len(braking_events) > 0:
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    
    # Panel 1: Braking force types
    axes[0].plot(braking_events['milepost'], braking_events['F_dynamic_kN'], 
                 label='Dynamic (Loco)', color='#FF6B35', linewidth=2, marker='o', markersize=3)
    axes[0].plot(braking_events['milepost'], braking_events['F_air_kN'], 
                 label='Air (Distributed)', color='#004E89', linewidth=2, marker='s', markersize=3)
    axes[0].set_ylabel('Braking Force (kN)', fontweight='bold')
    axes[0].set_title('Braking Force Breakdown (Events > 5 kN)', fontsize=13, fontweight='bold', pad=10)
    axes[0].legend(loc='best')
    axes[0].grid(True, alpha=0.3)
    
    # Panel 2: Wheel power
    axes[1].plot(braking_events['milepost'], braking_events['pwr_whl_out_watts'] / 1e6, 
                 color='#9D4EDD', linewidth=2)
    axes[1].axhline(0, color='black', linewidth=0.5, linestyle='--')
    axes[1].set_ylabel('Wheel Power (MW)', fontweight='bold')
    axes[1].set_title('Locomotive Wheel Power (Negative = Braking)', fontsize=12, fontweight='bold', pad=10)
    axes[1].grid(True, alpha=0.3)
    
    # Panel 3: Deceleration
    axes[2].plot(braking_events['milepost'], braking_events['accel_ms2'], 
                 color='#F72585', linewidth=2)
    axes[2].axhline(0, color='black', linewidth=0.5, linestyle='--')
    axes[2].set_xlabel('Milepost', fontweight='bold')
    axes[2].set_ylabel('Acceleration (m/s²)', fontweight='bold')
    axes[2].set_title('Train Deceleration', fontsize=12, fontweight='bold', pad=10)
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "nb_braking_detailed_breakdown.png", dpi=300, bbox_inches='tight')
    print(f"  Saved: {OUTPUT_DIR / 'nb_braking_detailed_breakdown.png'}")
    plt.close()
else:
    print("  No significant braking events detected (threshold: 5 kN)")

# ============================================================================
# VISUALIZATION 4: Spatial Distribution (Where forces are applied)
# ============================================================================
print("\nGenerating Visualization 4: Spatial Force Distribution...")

# Simplified spatial model
num_locos = 2  # From simulation config (Passenger_Car simulation)
num_cars = 10   # From simulation config
train_length_m = 260.0  # From simulation config

# Create spatial bins
spatial_bins = np.linspace(0, train_length_m, 50)
bin_centers = (spatial_bins[:-1] + spatial_bins[1:]) / 2

# Dynamic braking concentrated at front (locomotives)
loco_length = train_length_m * (num_locos / (num_locos + num_cars))
dynamic_spatial = np.where(bin_centers < loco_length, 
                            df['F_dynamic_kN'].mean() / loco_length, 0)

# Air braking distributed uniformly
air_spatial = np.ones_like(bin_centers) * (df['F_air_kN'].mean() / train_length_m)

fig, ax = plt.subplots(figsize=(14, 5))

ax.fill_between(bin_centers, 0, dynamic_spatial, 
                 alpha=0.6, color='#FF6B35', label='Dynamic Braking (Concentrated at Locos)')
ax.fill_between(bin_centers, 0, air_spatial, 
                 alpha=0.6, color='#004E89', label='Air Braking (Distributed)')

# Mark locomotive section
ax.axvline(loco_length, color='red', linestyle='--', linewidth=2, alpha=0.7, 
           label=f'Loco Section ({loco_length:.1f}m)')

ax.set_xlabel('Position Along Train (meters from front)', fontsize=11, fontweight='bold')
ax.set_ylabel('Force Density (kN/m)', fontsize=11, fontweight='bold')
ax.set_title('Spatial Distribution: Where Braking Forces are Applied', 
             fontsize=13, fontweight='bold', pad=15)
ax.legend(loc='upper right', fontsize=9)
ax.grid(True, alpha=0.3, axis='y')

# Add annotations
ax.annotate('Locomotives\n(Dynamic Braking)', 
            xy=(loco_length/2, dynamic_spatial.max()), 
            fontsize=9, ha='center', va='bottom', 
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FF6B35', alpha=0.3))
ax.annotate('Rail Cars\n(Air Braking Only)', 
            xy=((loco_length + train_length_m)/2, air_spatial.mean()), 
            fontsize=9, ha='center', va='bottom',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#004E89', alpha=0.3))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "nb_spatial_force_distribution.png", dpi=300, bbox_inches='tight')
print(f"  Saved: {OUTPUT_DIR / 'nb_spatial_force_distribution.png'}")
plt.close()

# ============================================================================
# Export analyzed data
# ============================================================================
print("\nExporting analyzed data...")
output_cols = [
    'time_seconds', 'milepost', 'speed_mps', 'accel_ms2',
    'F_dynamic_kN', 'F_air_kN', 'F_total_brake_kN', 'F_resistance_kN',
    'pwr_whl_out_watts', 'res_grade_newtons', 'res_curve_newtons'
]
df[output_cols].to_csv(OUTPUT_DIR / "nb_braking_analysis_data.csv", index=False)
print(f"  Saved: {OUTPUT_DIR / 'nb_braking_analysis_data.csv'}")

print("\n" + "="*60)
print("ANALYSIS COMPLETE!")
print("="*60)
print(f"Output directory: {OUTPUT_DIR.absolute()}")
print("\nGenerated files:")
print("  1. nb_braking_forces_vs_milepost.png")
print("  2. nb_force_balance_analysis.png") 
print("  3. nb_braking_detailed_breakdown.png")
print("  4. nb_spatial_force_distribution.png")
print("  5. nb_braking_analysis_data.csv")
print("="*60)
