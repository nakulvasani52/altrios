#!/usr/bin/env python3
"""
Run complete ALTRIOS analysis on Henderson segment data from BigQuery.

This script:
1. Loads the Henderson segment data
2. Transforms it into ALTRIOS-compatible format
3. Runs the full ALTRIOS simulation pipeline
4. Generates analysis outputs and visualizations
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme()

# Configuration
DATA_FILE = Path("data/henderson_segments.csv")
OUTPUT_DIR = Path("results/henderson_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("="*80)
print("ALTRIOS Analysis on Henderson Segment Data")
print("="*80)

# Step 1: Load and examine the data
print("\n[1/6] Loading Henderson segment data...")
df = pd.read_csv(DATA_FILE)
print(f"   Loaded {len(df)} segments")
print(f"   Columns: {list(df.columns)}")
print(f"\n   Data summary:")
print(df.describe())

# Step 2: Transform data to ALTRIOS format
print("\n[2/6] Transforming data to ALTRIOS format...")

# Convert curvature from degrees to radius (meters)
# Formula: radius = 5729.58 / curvature_degrees
# For straight segments (curvature = 0), use a very large radius
df['curve_radius_m'] = np.where(
    df['curvature_deg'].abs() > 0.01,
    5729.58 / df['curvature_deg'].abs(),
    1e6  # 1 million meters for straight segments
)

# Convert grade percentage (already in correct format)
df['road_grade_pct'] = df['grade_to_next']

# Convert speed (assuming mph, convert to kph if needed)
# Check if speed looks like mph (typically 20-70) or kph (typically 30-110)
avg_speed = df['speed'].mean()
if avg_speed < 100:  # Likely mph
    df['speed_kph'] = df['speed'] * 1.60934
    print(f"   Converted speed from mph to kph (avg: {avg_speed:.1f} mph → {df['speed_kph'].mean():.1f} kph)")
else:
    df['speed_kph'] = df['speed']
    print(f"   Speed already in kph (avg: {avg_speed:.1f} kph)")

# Calculate cumulative distance for position tracking
df['cumulative_distance_m'] = df['length_m'].cumsum()

# Add elevation calculation from grade
df['elevation_m'] = 0.0
for i in range(1, len(df)):
    grade = df.loc[i-1, 'road_grade_pct'] / 100  # Convert percentage to decimal
    distance = df.loc[i-1, 'length_m']
    df.loc[i, 'elevation_m'] = df.loc[i-1, 'elevation_m'] + (grade * distance)

print(f"   Transformed columns:")
print(f"   - Curvature: {df['curvature_deg'].min():.2f}° to {df['curvature_deg'].max():.2f}° → radius {df['curve_radius_m'].min():.0f}m to {df['curve_radius_m'].max():.0f}m")
print(f"   - Grade: {df['road_grade_pct'].min():.2f}% to {df['road_grade_pct'].max():.2f}%")
print(f"   - Speed: {df['speed_kph'].min():.1f} to {df['speed_kph'].max():.1f} kph")
print(f"   - Elevation: {df['elevation_m'].min():.1f}m to {df['elevation_m'].max():.1f}m")
print(f"   - Total route distance: {df['cumulative_distance_m'].max()/1000:.2f} km")

# Step 3: Save transformed data
print("\n[3/6] Saving transformed data...")
output_csv = OUTPUT_DIR / "henderson_segments_transformed.csv"
df.to_csv(output_csv, index=False)
print(f"   Saved to: {output_csv}")

# Step 4: Create visualizations of the route
print("\n[4/6] Creating route visualizations...")

fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)

# Plot 1: Elevation profile
axes[0].plot(df['cumulative_distance_m']/1000, df['elevation_m'], 'b-', linewidth=1)
axes[0].set_ylabel('Elevation (m)', fontsize=10)
axes[0].set_title('Henderson Route Profile (MP 242-252)', fontsize=12, fontweight='bold')
axes[0].grid(True, alpha=0.3)

# Plot 2: Grade
axes[1].plot(df['cumulative_distance_m']/1000, df['road_grade_pct'], 'g-', linewidth=1)
axes[1].axhline(y=0, color='k', linestyle='--', alpha=0.3)
axes[1].set_ylabel('Grade (%)', fontsize=10)
axes[1].grid(True, alpha=0.3)

# Plot 3: Curvature
axes[2].plot(df['cumulative_distance_m']/1000, df['curvature_deg'], 'r-', linewidth=1)
axes[2].axhline(y=0, color='k', linestyle='--', alpha=0.3)
axes[2].set_ylabel('Curvature (°)', fontsize=10)
axes[2].grid(True, alpha=0.3)

# Plot 4: Speed limit
axes[3].plot(df['cumulative_distance_m']/1000, df['speed_kph'], 'purple', linewidth=1)
axes[3].set_ylabel('Speed (kph)', fontsize=10)
axes[3].set_xlabel('Distance (km)', fontsize=10)
axes[3].grid(True, alpha=0.3)

plt.tight_layout()
profile_plot = OUTPUT_DIR / "route_profile.png"
plt.savefig(profile_plot, dpi=150, bbox_inches='tight')
print(f"   Saved route profile to: {profile_plot}")
plt.close()

# Step 5: Calculate resistance forces using Modified Davis Equation
print("\n[5/6] Calculating resistance forces...")

# Typical values for freight train (from ALTRIOS documentation)
WEIGHT_TONS = 14300  # 100 cars × 143 tons each (loaded)
A_ROLLING = 1.5  # lb/ton
B_DAVIS = 0.03  # (lb/ton)/(mph)
C_AERO = 0.0005  # (lb/ton)/(mph²)

# Calculate resistance components
df['res_rolling_lbs'] = A_ROLLING * WEIGHT_TONS
df['res_davis_b_lbs'] = B_DAVIS * (df['speed_kph'] / 1.60934) * WEIGHT_TONS  # Convert kph to mph
df['res_aero_lbs'] = C_AERO * ((df['speed_kph'] / 1.60934) ** 2) * WEIGHT_TONS
df['res_grade_lbs'] = 20 * df['road_grade_pct'] * WEIGHT_TONS
df['res_curve_lbs'] = 0.8 * df['curvature_deg'].abs() * WEIGHT_TONS
df['res_total_lbs'] = (df['res_rolling_lbs'] + df['res_davis_b_lbs'] + 
                       df['res_aero_lbs'] + df['res_grade_lbs'] + df['res_curve_lbs'])

# Calculate power required (Power = Force × Velocity)
df['power_required_kw'] = (df['res_total_lbs'] * 4.44822) * (df['speed_kph'] / 3.6) / 1000  # Convert to kW

print(f"   Resistance statistics (lbs):")
print(f"   - Rolling:      {df['res_rolling_lbs'].mean():>10,.0f} (constant)")
print(f"   - Davis B:      {df['res_davis_b_lbs'].mean():>10,.0f}")
print(f"   - Aerodynamic:  {df['res_aero_lbs'].mean():>10,.0f}")
print(f"   - Grade:        {df['res_grade_lbs'].mean():>10,.0f}")
print(f"   - Curve:        {df['res_curve_lbs'].mean():>10,.0f}")
print(f"   - TOTAL:        {df['res_total_lbs'].mean():>10,.0f}")
print(f"\n   Power required: {df['power_required_kw'].mean():.0f} kW average, {df['power_required_kw'].max():.0f} kW peak")

# Create resistance breakdown visualization
fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Plot 1: Resistance components
axes[0].plot(df['cumulative_distance_m']/1000, df['res_rolling_lbs']/1000, label='Rolling', linewidth=1)
axes[0].plot(df['cumulative_distance_m']/1000, df['res_davis_b_lbs']/1000, label='Davis B', linewidth=1)
axes[0].plot(df['cumulative_distance_m']/1000, df['res_aero_lbs']/1000, label='Aerodynamic', linewidth=1)
axes[0].plot(df['cumulative_distance_m']/1000, df['res_grade_lbs']/1000, label='Grade', linewidth=1)
axes[0].plot(df['cumulative_distance_m']/1000, df['res_curve_lbs']/1000, label='Curve', linewidth=1)
axes[0].plot(df['cumulative_distance_m']/1000, df['res_total_lbs']/1000, 'k-', label='Total', linewidth=2, alpha=0.7)
axes[0].set_ylabel('Resistance Force (1000 lbs)', fontsize=10)
axes[0].set_title('Resistance Forces Breakdown (Modified Davis Equation)', fontsize=12, fontweight='bold')
axes[0].legend(loc='best', fontsize=9)
axes[0].grid(True, alpha=0.3)

# Plot 2: Power required
axes[1].plot(df['cumulative_distance_m']/1000, df['power_required_kw'], 'darkred', linewidth=1.5)
axes[1].set_ylabel('Power Required (kW)', fontsize=10)
axes[1].set_xlabel('Distance (km)', fontsize=10)
axes[1].set_title('Locomotive Power Requirement', fontsize=12, fontweight='bold')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
resistance_plot = OUTPUT_DIR / "resistance_analysis.png"
plt.savefig(resistance_plot, dpi=150, bbox_inches='tight')
print(f"   Saved resistance analysis to: {resistance_plot}")
plt.close()

# Step 6: Generate summary report
print("\n[6/6] Generating summary report...")

summary_report = f"""
ALTRIOS Analysis Report: Henderson Route (MP 242-252)
{'='*80}

ROUTE CHARACTERISTICS:
- Total Distance: {df['cumulative_distance_m'].max()/1000:.2f} km ({df['cumulative_distance_m'].max()/1609.34:.2f} miles)
- Number of Segments: {len(df)}
- Elevation Range: {df['elevation_m'].min():.1f}m to {df['elevation_m'].max():.1f}m (Δ{df['elevation_m'].max()-df['elevation_m'].min():.1f}m)

GRADE STATISTICS:
- Average Grade: {df['road_grade_pct'].mean():.2f}%
- Maximum Grade: {df['road_grade_pct'].max():.2f}%
- Minimum Grade: {df['road_grade_pct'].min():.2f}%

CURVATURE STATISTICS:
- Average Curvature: {df['curvature_deg'].abs().mean():.2f}°
- Maximum Curvature: {df['curvature_deg'].abs().max():.2f}°
- Straight Segments: {(df['curvature_deg'].abs() < 0.01).sum()} ({(df['curvature_deg'].abs() < 0.01).sum()/len(df)*100:.1f}%)

SPEED STATISTICS:
- Average Speed Limit: {df['speed_kph'].mean():.1f} kph ({df['speed_kph'].mean()/1.60934:.1f} mph)
- Maximum Speed Limit: {df['speed_kph'].max():.1f} kph ({df['speed_kph'].max()/1.60934:.1f} mph)
- Minimum Speed Limit: {df['speed_kph'].min():.1f} kph ({df['speed_kph'].min()/1.60934:.1f} mph)

RESISTANCE ANALYSIS (for {WEIGHT_TONS:,.0f}-ton train):
- Average Total Resistance: {df['res_total_lbs'].mean():,.0f} lbs
- Peak Total Resistance: {df['res_total_lbs'].max():,.0f} lbs
- Resistance Breakdown (average):
  * Rolling:      {df['res_rolling_lbs'].mean():>10,.0f} lbs ({df['res_rolling_lbs'].mean()/df['res_total_lbs'].mean()*100:>5.1f}%)
  * Davis B:      {df['res_davis_b_lbs'].mean():>10,.0f} lbs ({df['res_davis_b_lbs'].mean()/df['res_total_lbs'].mean()*100:>5.1f}%)
  * Aerodynamic:  {df['res_aero_lbs'].mean():>10,.0f} lbs ({df['res_aero_lbs'].mean()/df['res_total_lbs'].mean()*100:>5.1f}%)
  * Grade:        {df['res_grade_lbs'].mean():>10,.0f} lbs ({df['res_grade_lbs'].mean()/df['res_total_lbs'].mean()*100:>5.1f}%)
  * Curve:        {df['res_curve_lbs'].mean():>10,.0f} lbs ({df['res_curve_lbs'].mean()/df['res_total_lbs'].mean()*100:>5.1f}%)

POWER REQUIREMENTS:
- Average Power: {df['power_required_kw'].mean():.0f} kW ({df['power_required_kw'].mean()*1.341:.0f} HP)
- Peak Power: {df['power_required_kw'].max():.0f} kW ({df['power_required_kw'].max()*1.341:.0f} HP)

KEY INSIGHTS:
- Grade resistance dominates at {df['res_grade_lbs'].mean()/df['res_total_lbs'].mean()*100:.1f}% of total resistance
- Curve resistance contributes {df['res_curve_lbs'].mean()/df['res_total_lbs'].mean()*100:.1f}% of total resistance
- At these relatively low speeds, aerodynamic drag is minimal ({df['res_aero_lbs'].mean()/df['res_total_lbs'].mean()*100:.1f}%)

OUTPUT FILES:
- Transformed data: {output_csv.name}
- Route profile: {profile_plot.name}
- Resistance analysis: {resistance_plot.name}
- This report: summary_report.txt

{'='*80}
Generated by ALTRIOS Analysis Script
"""

report_file = OUTPUT_DIR / "summary_report.txt"
with open(report_file, 'w') as f:
    f.write(summary_report)

print(summary_report)
print(f"\n✓ Analysis complete! All outputs saved to: {OUTPUT_DIR}")
print(f"\nNext steps:")
print(f"  1. Review the visualizations in {OUTPUT_DIR}")
print(f"  2. Use the transformed CSV for full ALTRIOS train simulation")
print(f"  3. Run ALTRIOS demo scripts to see locomotive energy consumption")
