import altrios as alt
import pandas as pd
import numpy as np

# Load network
network_file = "data/henderson_network_altrios.yaml"
network = alt.Network.from_file(network_file)

# Load speed trace and link path for NORTHBOUND (Link 1)
import generate_speed_trace
# This uses the version with the injected Slow Order (for braking analysis)
speed_trace, link_path = generate_speed_trace.get_speed_trace("NB") 

# Load heavy rail vehicle (Loaded Manifest)
rail_vehicle_file = "python/altrios/resources/rolling_stock/Manifest_Loaded.yaml"
rail_vehicle = alt.RailVehicle.from_file(rail_vehicle_file)

import create_robust_loco
loco_unit = create_robust_loco.get_robust_loco()

# Train configuration: 50 LOADED cars, 2 locomotives (HEAVY TRAIN)
# Mass: ~7800 tonnes (vs ~840 tonnes for passenger)
train_config = alt.TrainConfig.from_pydict({
    "rail_vehicles": [rail_vehicle.to_pydict()] * 50,
    "n_cars_by_type": {"Manifest_Loaded": 50},
    "train_type": "Freight",
    "train_length_meters": 26.0 * 50 + 52.0, # ~1350m
    "train_mass_kilograms": 143000.0 * 50 + 120000.0 * 2
})

consist = alt.Consist([loco_unit] * 2)

# Create simulation builder
tsb = alt.TrainSimBuilder(
    train_id="Henderson_NB_Heavy_Freight",
    train_config=train_config,
    loco_con=consist,
)

# Create simulation
print("Creating Northbound HEAVY Simulation (Freight Consist)...")
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
# to_pydict returns nested structure, extract history
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
results_df.to_csv("results/henderson_nb_simulation_heavy.csv", index=False)

print("\n" + "="*60)
print("HEAVY FREIGHT SIMULATION COMPLETE")
print("="*60)
print(f"Total Time: {results_df['time_seconds'].iloc[-1]} seconds")
print(f"Total Distance: {results_df['total_dist_meters'].iloc[-1]/1000:.2f} km")
print(f"Max Speed: {results_df['speed_meters_per_second'].max() * 2.237:.1f} mph")
print("Results saved to: results/henderson_nb_simulation_heavy.csv")
print("="*60)
