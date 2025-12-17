#!/usr/bin/env python3
"""
Create ALTRIOS link_path.csv from Henderson segment data.

This script transforms the Henderson segments into the format required by ALTRIOS:
- Samples the route at regular intervals (100m)
- Interpolates elevation, grade, curvature, and speed
- Outputs in ALTRIOS link_path format
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Configuration
INPUT_FILE = Path("results/henderson_analysis/henderson_segments_transformed.csv")
OUTPUT_FILE = Path("data/henderson_link_path.csv")
SAMPLE_INTERVAL_M = 100.0  # Sample every 100 meters

print("="*80)
print("Creating ALTRIOS Link Path from Henderson Data")
print("="*80)

# Load the transformed data
print(f"\n[1/4] Loading transformed data from {INPUT_FILE}...")
df = pd.read_csv(INPUT_FILE)
print(f"   Loaded {len(df)} segments")
print(f"   Total distance: {df['cumulative_distance_m'].max():.0f} meters")

# Create sample points at regular intervals
print(f"\n[2/4] Creating sample points every {SAMPLE_INTERVAL_M}m...")
max_distance = df['cumulative_distance_m'].max()
sample_distances = np.arange(0, max_distance + SAMPLE_INTERVAL_M, SAMPLE_INTERVAL_M)
print(f"   Generated {len(sample_distances)} sample points")

# Interpolate values at sample points
print(f"\n[3/4] Interpolating track geometry...")

# For each sample point, find the corresponding values by interpolation
link_path_data = []

for distance in sample_distances:
    # Find the segment containing this distance
    # Use linear interpolation for all values
    elevation = np.interp(distance, df['cumulative_distance_m'], df['elevation_m'])
    grade = np.interp(distance, df['cumulative_distance_m'], df['road_grade_pct'])
    curvature = np.interp(distance, df['cumulative_distance_m'], df['curvature_deg'])
    speed_kph = np.interp(distance, df['cumulative_distance_m'], df['speed_kph'])
    
    # Convert speed from kph to m/s for ALTRIOS
    speed_mps = speed_kph / 3.6
    
    link_path_data.append({
        'link_idx': 0,  # Single link
        'offset_meters': distance,
        'elevation_meters': elevation,
        'grade_percent': grade,
        'curvature_degrees': curvature,
        'speed_limit_mps': speed_mps
    })

# Create DataFrame
link_path_df = pd.DataFrame(link_path_data)

# Save to CSV
print(f"\n[4/4] Saving link path to {OUTPUT_FILE}...")
link_path_df.to_csv(OUTPUT_FILE, index=False)
print(f"   Saved {len(link_path_df)} points")

# Print summary
print(f"\n{'='*80}")
print("Link Path Summary:")
print(f"{'='*80}")
print(f"Total distance:        {link_path_df['offset_meters'].max():.0f} m")
print(f"Number of points:      {len(link_path_df)}")
print(f"Sample interval:       {SAMPLE_INTERVAL_M:.0f} m")
print(f"\nElevation range:       {link_path_df['elevation_meters'].min():.1f} to {link_path_df['elevation_meters'].max():.1f} m")
print(f"Grade range:           {link_path_df['grade_percent'].min():.2f}% to {link_path_df['grade_percent'].max():.2f}%")
print(f"Curvature range:       {link_path_df['curvature_degrees'].min():.2f}° to {link_path_df['curvature_degrees'].max():.2f}°")
print(f"Speed limit range:     {link_path_df['speed_limit_mps'].min():.1f} to {link_path_df['speed_limit_mps'].max():.1f} m/s")
print(f"                       ({link_path_df['speed_limit_mps'].min()*2.23694:.1f} to {link_path_df['speed_limit_mps'].max()*2.23694:.1f} mph)")
print(f"\n✓ Link path file created successfully!")
print(f"  Ready for ALTRIOS simulation")
