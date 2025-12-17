#!/usr/bin/env python3
"""
Simplified ALTRIOS simulation for Henderson route.

This uses SetSpeedTrainSim directly with the link path,
avoiding the complexity of full network setup.
"""

import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Import ALTRIOS
import altrios as alt

sns.set_theme()

# Configuration
LINK_PATH_FILE = Path("data/henderson_link_path.csv")
OUTPUT_DIR = Path("results/henderson_full_simulation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SAVE_INTERVAL = 1

print("="*80)
print("ALTRIOS Simplified Train Simulation: Henderson Route")
print("="*80)

# ============================================================================
# STEP 1: Load Link Path
# ============================================================================
print("\n[1/5] Loading link path...")
link_path = alt.LinkPath.from_csv_file(LINK_PATH_FILE)
print(f"   ✓ Link path loaded: {len(link_path.link_idxs)} points")
print(f"     Total distance: {max(link_path.offset_meters):.0f} meters")

# ============================================================================
# STEP 2: Configure Train
# ============================================================================
print("\n[2/5] Configuring train...")

# Load rail car
rail_vehicle = alt.RailVehicle.from_file(
    alt.resources_root() / "rolling_stock/Manifest_Loaded.yaml"
)

train_config = alt.TrainConfig(
    rail_vehicles=[rail_vehicle],
    n_cars_by_type={"Manifest_Loaded": 100},
    train_length_meters=None,
    train_mass_kilograms=None,
)
print(f"   ✓ Train: 100 loaded manifest cars")

# ============================================================================
# STEP 3: Configure Locomotives
# ============================================================================
print("\n[3/5] Configuring locomotives...")
loco_vec = [alt.Locomotive.default() for _ in range(3)]
loco_con = alt.Consist(loco_vec, SAVE_INTERVAL)
print(f"   ✓ Consist: {len(loco_vec)} diesel locomotives")

# ============================================================================
# STEP 4: Create and Run Simulation
# ============================================================================
print("\n[4/5] Running simulation...")

# Use the demo network as a template
network = alt.Network.from_file(
    alt.resources_root() / "networks/Taconite-NoBalloon.yaml"
)

# Create speed trace
speed_trace_data = []
time_sec = 0.0
for i in range(len(link_path.link_idxs)):
    speed_trace_data.append({
        'time_seconds': time_sec,
        'speed_meters_per_second': link_path.speed_limit_meters_per_second[i]
    })
    time_sec += 10.0

speed_trace_df = pd.DataFrame(speed_trace_data)
speed_trace_df.to_csv(OUTPUT_DIR / "speed_trace.csv", index=False)
speed_trace = alt.SpeedTrace.from_csv_file(OUTPUT_DIR / "speed_trace.csv")

# Build simulation
tsb = alt.TrainSimBuilder(
    train_id="henderson_001",
    train_config=train_config,
    loco_con=loco_con,
)

train_sim = tsb.make_set_speed_train_sim(
    network=network,
    link_path=link_path,
    speed_trace=speed_trace,
    save_interval=SAVE_INTERVAL,
)

t0 = time.perf_counter()
train_sim.walk()
t1 = time.perf_counter()
sim_time = t1 - t0

print(f"   ✓ Simulation completed in {sim_time:.2f} seconds")

# ============================================================================
# STEP 5: Extract and Visualize Results
# ============================================================================
print("\n[5/5] Extracting results and creating visualizations...")

df_list = train_sim.to_dataframe()
df = df_list[-1] if isinstance(df_list, list) else df_list
df_pd = df.to_pandas()

# Save results
df_pd.to_csv(OUTPUT_DIR / "simulation_results.csv", index=False)
print(f"   ✓ Saved {len(df_pd)} timesteps to simulation_results.csv")

# Calculate fuel consumption
try:
    total_fuel_joules = train_sim.get_energy_fuel_joules(annualize=False)
    total_fuel_gj = total_fuel_joules / 1e9
    total_fuel_gallons = (
        total_fuel_joules / 1e3 /
        alt.defaults.LHV_DIESEL_KJ_PER_KG /
        alt.defaults.RHO_DIESEL_KG_PER_M3 *
        alt.utilities.LITER_PER_M3 *
        alt.utilities.GALLONS_PER_LITER
    )
    print(f"\n   Fuel Consumption:")
    print(f"   - Total energy: {total_fuel_gj:.2f} GJ")
    print(f"   - Total volume: {total_fuel_gallons:.1f} gallons")
    print(f"   - Efficiency: {total_fuel_gallons/(df_pd['offset_meters'].max()/1609.34):.2f} gal/mile")
except Exception as e:
    print(f"   Note: Could not calculate fuel consumption: {e}")
    total_fuel_gj = 0
    total_fuel_gallons = 0

# Create visualization
fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)

# Speed
axes[0].plot(df_pd['offset_meters']/1000, df_pd['speed_meters_per_second']*2.23694, 'b-', linewidth=1)
axes[0].set_ylabel('Speed (mph)', fontsize=10)
axes[0].set_title('ALTRIOS Simulation: Henderson Route', fontsize=12, fontweight='bold')
axes[0].grid(True, alpha=0.3)

# Power
if 'pwr_whl_out_watts' in df_pd.columns:
    axes[1].plot(df_pd['offset_meters']/1000, df_pd['pwr_whl_out_watts']/1e6, 'g-', linewidth=1)
    axes[1].set_ylabel('Power (MW)', fontsize=10)
    axes[1].grid(True, alpha=0.3)

# Grade
axes[2].plot(df_pd['offset_meters']/1000, df_pd['grade']*100, 'r-', linewidth=1)
axes[2].axhline(y=0, color='k', linestyle='--', alpha=0.3)
axes[2].set_ylabel('Grade (%)', fontsize=10)
axes[2].grid(True, alpha=0.3)

# Elevation
axes[3].fill_between(df_pd['offset_meters']/1000, df_pd['elevation_meters'], alpha=0.3, color='brown')
axes[3].plot(df_pd['offset_meters']/1000, df_pd['elevation_meters'], 'brown', linewidth=1)
axes[3].set_ylabel('Elevation (m)', fontsize=10)
axes[3].set_xlabel('Distance (km)', fontsize=10)
axes[3].grid(True, alpha=0.3)

plt.tight_layout()
plot_file = OUTPUT_DIR / "simulation_profile.png"
plt.savefig(plot_file, dpi=150, bbox_inches='tight')
print(f"   ✓ Saved visualization to {plot_file.name}")
plt.close()

# Summary
summary = f"""
ALTRIOS Simulation Summary: Henderson Route
{'='*80}

CONFIGURATION:
- Train: 100 loaded manifest cars
- Locomotives: 3 diesel units
- Route Distance: {df_pd['offset_meters'].max()/1000:.2f} km ({df_pd['offset_meters'].max()/1609.34:.2f} miles)

RESULTS:
- Simulation Time: {df_pd['time_seconds'].max():.0f} seconds ({df_pd['time_seconds'].max()/60:.1f} minutes)
- Average Speed: {df_pd['speed_meters_per_second'].mean()*2.23694:.1f} mph
- Fuel Consumed: {total_fuel_gallons:.1f} gallons ({total_fuel_gj:.2f} GJ)
- Fuel Efficiency: {total_fuel_gallons/(df_pd['offset_meters'].max()/1609.34) if total_fuel_gallons > 0 else 0:.2f} gal/mile

COMPUTATION:
- Runtime: {sim_time:.2f} seconds
- Timesteps: {len(df_pd)}

FILES GENERATED:
- simulation_results.csv
- simulation_profile.png
- summary_report.txt

{'='*80}
"""

with open(OUTPUT_DIR / "summary_report.txt", 'w') as f:
    f.write(summary)

print(summary)
print(f"\n✓ Simulation complete! Results in: {OUTPUT_DIR}")
