#!/usr/bin/env python3
import pandas as pd
import numpy as np

print("Loading track demand distributions...")
demand = pd.read_csv("results/track_demand/demand_bins.csv")
demand = demand.sort_values('milepost')

print("Loading raw geometry data...")
geo = pd.read_csv("data/nvasani2_altrios_segments_henderson_sim_run")
geo = geo[geo['TrackNumber'].isin(['SG', '1', '2'])].copy()
geo = geo.sort_values(['beg_mp', 'TrackNumber']).drop_duplicates(subset=['beg_mp'], keep='first')
geo['milepost'] = (geo['beg_mp'] + geo['end_mp']) / 2.0
geo = geo.sort_values('milepost')

# Merge As Of
merged = pd.merge_asof(demand, geo[['milepost', 'curvature_deg', 'grade_to_next', 'speed']], on='milepost', direction='nearest')

top_pos_shear = merged.nlargest(10, 'total_shear_kNs')
# air braking is actually where we deposited F_air_brake_kN > 0.
# but 'total_shear_kNs' is loco_shear_kNs + car_shear_kNs.
# Wait, locos output Traction (>0) and Dyn Braaking (>0).
# Cars output Air Braking (>0). 
# Both are positive magnitudes in my script!
# Let me check analyze_track_demand.py to see if I made them all positive.

top_shear_kNs = merged.sort_values('total_shear_kNs', ascending=False)
top_vert_GNs  = merged.sort_values('total_vert_GNs', ascending=False)

print("\n" + "="*70)
print("TOP 10 HIGH-STRESS LONIGTUDINAL SHEAR ZONES (Traction/Braking)")
print("="*70)
for _, r in top_shear_kNs.head(10).iterrows():
    print(f"MP {r['milepost']:.2f} | Shear Demand: {r['total_shear_kNs']:>8.0f} kN·s | Grade: {r['grade_to_next']:>5.2f}% | Curve: {r['curvature_deg']:>5.2f}° | Speed: {r['speed']:>4.1f} mph")

print("\n" + "="*70)
print("TOP 10 HIGH-STRESS VERTICAL LOAD ZONES (Static Pass-over)")
print("="*70)
for _, r in top_vert_GNs.head(10).iterrows():
    print(f"MP {r['milepost']:.2f} | Vertical Demand: {r['total_vert_GNs']:>8.2f} GN·s | Grade: {r['grade_to_next']:>5.2f}% | Curve: {r['curvature_deg']:>5.2f}° | Speed: {r['speed']:>4.1f} mph")
