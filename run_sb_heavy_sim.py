import altrios as alt
import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.getcwd())

# Load network
network_file = "data/henderson_network_altrios.yaml"
network = alt.Network.from_file(network_file)

# Helper function to create Location objects
def create_location(loc_id, link_idx, offset, is_front=True):
    return alt.Location.from_pydict({
        "Location ID": loc_id,
        "Offset (m)": offset,
        "Link Index": link_idx,
        "Is Front End": is_front,
        "Grid Emissions Region": "US",
        "Electricity Price Region": "US",
        "Liquid Fuel Price Region": "US"
    })

# Southbound: Start at beginning of Link 2 (Reversed), End at End of Link 2
# Link 2 corresponds to MP 252 -> 242
origin = create_location("Origin_SB", 2, 0.0, is_front=False)
destination = create_location("Destination_SB", 2, 117703.4, is_front=True)

# Load heavy rail vehicle (Loaded Manifest)
rail_vehicle_file = "python/altrios/resources/rolling_stock/Manifest_Loaded.yaml"
rail_vehicle = alt.RailVehicle.from_file(rail_vehicle_file)

import create_robust_loco
loco_unit = create_robust_loco.get_robust_loco()

# Train configuration: 50 LOADED cars, 2 locomotives (Heavy Freight ~7800t)
# Matching Northbound configuration for consistency
train_config = alt.TrainConfig.from_pydict({
    "rail_vehicles": [rail_vehicle.to_pydict()] * 50,
    "n_cars_by_type": {"Manifest_Loaded": 50},
    "train_type": "Freight",
    "train_length_meters": 26.0 * 50 + 52.0, 
    "train_mass_kilograms": 143000.0 * 50 + 120000.0 * 2
})

consist = alt.Consist([loco_unit] * 2)

# Speed Trace and Link Path for SOUTHBOUND
import generate_speed_trace
speed_trace, link_path = generate_speed_trace.get_speed_trace("SB")

# Create simulation builder
tsb = alt.TrainSimBuilder(
    train_id="Henderson_SB_Heavy_Freight",
    train_config=train_config,
    loco_con=consist,
)

# Create simulation
print("Creating SOUTHBOUND HEAVY Simulation (Downhill)...")
print(f"Train Mass: {train_config.train_mass_kilograms/1000:.1f} tonnes")
sim = tsb.make_set_speed_train_sim(
    network=network,
    link_path=link_path,
    speed_trace=speed_trace,
    save_interval=1
)

# Run simulation
print("Running physics...")
sim.walk() 

# Get history
print("Processing simulation results...")
sim_data = sim.to_pydict()
history = sim_data.get('history', {})
df = pd.DataFrame(history)

# Save results with expanded fields matching analysis requirements
output_cols = [
    'time_seconds', 'dt_seconds', 'total_dist_meters', 
    'speed_meters_per_second', 'speed_limit_meters_per_second',
    'res_grade_newtons', 'res_curve_newtons', 'res_rolling_newtons', 'res_bearing_newtons',
    'res_aero_newtons', 'res_davis_b_newtons',
    'pwr_whl_out_watts', 
    'mass_static_kilograms', 'mass_freight_kilograms'
]

# Filter for available columns
available_cols = [col for col in output_cols if col in df.columns]
results_df = df[available_cols]
results_df.to_csv("results/henderson_sb_simulation_heavy.csv", index=False)

print("\n" + "="*60)
print("SOUTHBOUND HEAVY SIMULATION COMPLETE")
print("="*60)
print(f"Total Time: {results_df['time_seconds'].iloc[-1]} seconds")
if not results_df.empty:
    dist_km = results_df['total_dist_meters'].iloc[-1]/1000
    print(f"Total Distance: {dist_km:.2f} km")
    max_mph = results_df['speed_meters_per_second'].max() * 2.237
    print(f"Max Speed: {max_mph:.1f} mph")
else:
    print("Warning: Empty Results!")
print("Results saved to: results/henderson_sb_simulation_heavy.csv")
print("="*60)
