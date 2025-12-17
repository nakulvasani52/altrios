#!/usr/bin/env python3
"""
Run complete ALTRIOS train simulation on Henderson route.

This script:
1. Loads the Henderson network and link path
2. Configures a freight train (100 loaded cars + locomotives)
3. Runs the simulation following track speed limits
4. Generates comprehensive output reports and visualizations
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
NETWORK_FILE = Path("data/henderson_network.yaml")
LOCATIONS_FILE = Path("data/henderson_locations.csv")
LINK_PATH_FILE = Path("data/henderson_link_path.csv")
OUTPUT_DIR = Path("results/henderson_full_simulation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SAVE_INTERVAL = 1  # Save every timestep for detailed analysis

print("="*80)
print("ALTRIOS Full Train Simulation: Henderson Route (MP 242-252)")
print("="*80)

# ============================================================================
# STEP 1: Load Network and Path
# ============================================================================
print("\n[1/7] Loading network configuration...")
network = alt.Network.from_file(NETWORK_FILE)
print(f"   ✓ Network loaded: {len(network.links)} links")

location_map = alt.import_locations(LOCATIONS_FILE)
print(f"   ✓ Locations loaded: {len(location_map)} locations")

link_path = alt.LinkPath.from_csv_file(LINK_PATH_FILE)
print(f"   ✓ Link path loaded: {len(link_path.link_idxs)} points")
print(f"     Total distance: {max(link_path.offset_meters):.0f} meters")

# ============================================================================
# STEP 2: Configure Train Consist
# ============================================================================
print("\n[2/7] Configuring train consist...")

# Load rail car types (loaded manifest cars)
rail_vehicle_loaded = alt.RailVehicle.from_file(
    alt.resources_root() / "rolling_stock/Manifest_Loaded.yaml"
)
print(f"   ✓ Loaded car type: {rail_vehicle_loaded.car_type}")

# Train configuration: 100 loaded cars
train_config = alt.TrainConfig(
    rail_vehicles=[rail_vehicle_loaded],
    n_cars_by_type={"Manifest_Loaded": 100},
    train_length_meters=None,  # Auto-calculate
    train_mass_kilograms=None,  # Auto-calculate
)
print(f"   ✓ Train config: 100 loaded manifest cars")

# ============================================================================
# STEP 3: Configure Locomotive Consist
# ============================================================================
print("\n[3/7] Configuring locomotive consist...")

# Use default diesel locomotives (3 units for this heavy train)
loco_vec = [alt.Locomotive.default() for _ in range(3)]
loco_con = alt.Consist(loco_vec, SAVE_INTERVAL)
print(f"   ✓ Locomotive consist: {len(loco_vec)} diesel locomotives")

# ============================================================================
# STEP 4: Build Train Simulation
# ============================================================================
print("\n[4/7] Building train simulation...")

# Create train simulation builder
tsb = alt.TrainSimBuilder(
    train_id="henderson_001",
    train_config=train_config,
    loco_con=loco_con,
)

# Create speed trace from link path (follow track speed limits)
# Sample at regular intervals
speed_trace_data = []
for i in range(len(link_path.link_idxs)):
    speed_trace_data.append({
        'time_seconds': i * 10.0,  # Sample every 10 seconds
        'speed_meters_per_second': link_path.speed_limit_meters_per_second[i]
    })

speed_trace_df = pd.DataFrame(speed_trace_data)
speed_trace_df.to_csv(OUTPUT_DIR / "speed_trace_input.csv", index=False)

# Load speed trace
speed_trace = alt.SpeedTrace.from_csv_file(OUTPUT_DIR / "speed_trace_input.csv")
print(f"   ✓ Speed trace created: {len(speed_trace_df)} points")

# Create the train simulation
train_sim = tsb.make_set_speed_train_sim(
    network=network,
    link_path=link_path,
    speed_trace=speed_trace,
    save_interval=SAVE_INTERVAL,
)
print(f"   ✓ Train simulation built successfully")

# ============================================================================
# STEP 5: Run Simulation
# ============================================================================
print("\n[5/7] Running simulation...")
t0 = time.perf_counter()
train_sim.walk()
t1 = time.perf_counter()
sim_time = t1 - t0
print(f"   ✓ Simulation completed in {sim_time:.2f} seconds")

# ============================================================================
# STEP 6: Extract Results
# ============================================================================
print("\n[6/7] Extracting results...")

# Convert to DataFrame
df_list = train_sim.to_dataframe()
df = df_list[-1] if isinstance(df_list, list) else df_list
print(f"   ✓ Extracted {len(df)} timesteps")

# Convert to pandas for easier analysis
df_pd = df.to_pandas()

# Calculate total fuel consumption
total_fuel_joules = train_sim.get_energy_fuel_joules(annualize=False)
total_fuel_gj = total_fuel_joules / 1e9
total_fuel_gallons = (
    total_fuel_joules / 1e3 / 
    alt.defaults.LHV_DIESEL_KJ_PER_KG /
    alt.defaults.RHO_DIESEL_KG_PER_M3 *
    alt.utilities.LITER_PER_M3 *
    alt.utilities.GALLONS_PER_LITER
)

print(f"\n   Simulation Results:")
print(f"   - Total fuel energy: {total_fuel_gj:.2f} GJ")
print(f"   - Total fuel volume: {total_fuel_gallons:.1f} gallons")
print(f"   - Simulation time: {df_pd['time_seconds'].max():.0f} seconds ({df_pd['time_seconds'].max()/60:.1f} minutes)")
print(f"   - Distance traveled: {df_pd['offset_meters'].max():.0f} meters ({df_pd['offset_meters'].max()/1609.34:.2f} miles)")

# Save results to CSV
df_pd.to_csv(OUTPUT_DIR / "simulation_results.csv", index=False)
print(f"   ✓ Results saved to simulation_results.csv")

# ============================================================================
# STEP 7: Generate Visualizations
# ============================================================================
print("\n[7/7] Generating visualizations...")

# Create comprehensive plots
fig, axes = plt.subplots(5, 1, figsize=(14, 16), sharex=True)

# Plot 1: Speed profile
axes[0].plot(df_pd['offset_meters']/1000, df_pd['speed_meters_per_second']*2.23694, 'b-', linewidth=1, label='Actual')
axes[0].plot(df_pd['offset_meters']/1000, df_pd['speed_limit_meters_per_second']*2.23694, 'r--', linewidth=1, alpha=0.7, label='Limit')
axes[0].set_ylabel('Speed (mph)', fontsize=10)
axes[0].set_title('Henderson Route Full ALTRIOS Simulation', fontsize=12, fontweight='bold')
axes[0].legend(loc='best', fontsize=9)
axes[0].grid(True, alpha=0.3)

# Plot 2: Tractive effort / resistance
if 'pwr_whl_out_watts' in df_pd.columns:
    # Calculate force from power and speed
    df_pd['force_newtons'] = df_pd['pwr_whl_out_watts'] / (df_pd['speed_meters_per_second'] + 0.1)  # Avoid div by zero
    axes[1].plot(df_pd['offset_meters']/1000, df_pd['force_newtons']/1000, 'g-', linewidth=1)
    axes[1].set_ylabel('Tractive Force (kN)', fontsize=10)
    axes[1].grid(True, alpha=0.3)

# Plot 3: Power
if 'pwr_whl_out_watts' in df_pd.columns:
    axes[2].plot(df_pd['offset_meters']/1000, df_pd['pwr_whl_out_watts']/1e6, 'purple', linewidth=1)
    axes[2].set_ylabel('Power (MW)', fontsize=10)
    axes[2].grid(True, alpha=0.3)

# Plot 4: Fuel power (if available)
loco_data_available = False
try:
    # Try to access locomotive data
    if hasattr(train_sim, 'loco_con'):
        loco_0 = train_sim.loco_con.loco_vec[0]
        if hasattr(loco_0, 'loco_type') and 'fc' in str(type(loco_0.loco_type)):
            loco_data_available = True
except:
    pass

if loco_data_available:
    axes[3].plot(df_pd['offset_meters']/1000, df_pd.get('pwr_fuel_watts', [0]*len(df_pd))/1e6, 'darkred', linewidth=1)
    axes[3].set_ylabel('Fuel Power (MW)', fontsize=10)
    axes[3].grid(True, alpha=0.3)

# Plot 5: Elevation profile
axes[4].fill_between(df_pd['offset_meters']/1000, df_pd['elevation_meters'], alpha=0.3, color='brown')
axes[4].plot(df_pd['offset_meters']/1000, df_pd['elevation_meters'], 'brown', linewidth=1)
axes[4].set_ylabel('Elevation (m)', fontsize=10)
axes[4].set_xlabel('Distance (km)', fontsize=10)
axes[4].grid(True, alpha=0.3)

plt.tight_layout()
plot_file = OUTPUT_DIR / "simulation_profile.png"
plt.savefig(plot_file, dpi=150, bbox_inches='tight')
print(f"   ✓ Saved simulation profile to {plot_file.name}")
plt.close()

# Create fuel consumption plot
fig, ax = plt.subplots(1, 1, figsize=(10, 6))
cumulative_fuel = np.cumsum(df_pd.get('pwr_fuel_watts', [0]*len(df_pd))) * (df_pd['time_seconds'].diff().fillna(0)) / 1e9  # GJ
ax.plot(df_pd['offset_meters']/1000, cumulative_fuel, 'darkred', linewidth=2)
ax.set_xlabel('Distance (km)', fontsize=11)
ax.set_ylabel('Cumulative Fuel Energy (GJ)', fontsize=11)
ax.set_title('Fuel Consumption Along Route', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3)
plt.tight_layout()
fuel_plot = OUTPUT_DIR / "fuel_consumption.png"
plt.savefig(fuel_plot, dpi=150, bbox_inches='tight')
print(f"   ✓ Saved fuel consumption plot to {fuel_plot.name}")
plt.close()

# ============================================================================
# Summary Report
# ============================================================================
summary = f"""
ALTRIOS Full Simulation Report: Henderson Route (MP 242-252)
{'='*80}

SIMULATION PARAMETERS:
- Train ID: henderson_001
- Number of Cars: 100 loaded manifest cars
- Number of Locomotives: 3 diesel units
- Route Distance: {df_pd['offset_meters'].max()/1000:.2f} km ({df_pd['offset_meters'].max()/1609.34:.2f} miles)

PERFORMANCE RESULTS:
- Total Simulation Time: {df_pd['time_seconds'].max():.0f} seconds ({df_pd['time_seconds'].max()/60:.1f} minutes)
- Average Speed: {df_pd['speed_meters_per_second'].mean()*2.23694:.1f} mph
- Maximum Speed: {df_pd['speed_meters_per_second'].max()*2.23694:.1f} mph

ENERGY CONSUMPTION:
- Total Fuel Energy: {total_fuel_gj:.2f} GJ
- Total Fuel Volume: {total_fuel_gallons:.1f} gallons
- Fuel Efficiency: {total_fuel_gallons/(df_pd['offset_meters'].max()/1609.34):.2f} gallons/mile

COMPUTATIONAL PERFORMANCE:
- Simulation Runtime: {sim_time:.2f} seconds
- Timesteps Computed: {len(df_pd)}
- Computation Speed: {len(df_pd)/sim_time:.0f} timesteps/second

OUTPUT FILES:
- Simulation results: simulation_results.csv
- Simulation profile: simulation_profile.png
- Fuel consumption: fuel_consumption.png
- This report: summary_report.txt

{'='*80}
Generated by ALTRIOS Full Simulation
"""

report_file = OUTPUT_DIR / "summary_report.txt"
with open(report_file, 'w') as f:
    f.write(summary)

print(summary)
print(f"\n✓ Full ALTRIOS simulation complete!")
print(f"  All outputs saved to: {OUTPUT_DIR}")
