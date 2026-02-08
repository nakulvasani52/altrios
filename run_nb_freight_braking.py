import altrios as alt
import pandas as pd
import numpy as np

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

# Northbound: Start at beginning of Link 1, End at Link 1
origin = create_location("Origin_NB", 1, 0.0, is_front=False)
destination = create_location("Destination_NB", 1, 117703.4, is_front=True)

# Load FREIGHT rail vehicle and locomotive config
rail_vehicle_file = "python/altrios/resources/rolling_stock/Manifest_Loaded.yaml"
rail_vehicle = alt.RailVehicle.from_file(rail_vehicle_file)

import create_robust_loco
loco_unit = create_robust_loco.get_robust_loco()


# Train configuration: 50 LOADED manifest cars, 4 locomotives (Heavy Freight)
train_config = alt.TrainConfig.from_pydict({
    "rail_vehicles": [rail_vehicle.to_pydict()] * 50,
    "n_cars_by_type": {"Manifest_Loaded": 50},
    "train_type": "Freight",
    "train_length_meters": None,  # Auto-calculate
    "train_mass_kilograms": None  # Auto-calculate
})

consist = alt.Consist([loco_unit] * 4)

# Speed Trace and Link Path for SetSpeedTrainSim
import generate_speed_trace
speed_trace, link_path = generate_speed_trace.get_speed_trace("NB")

# Create simulation builder
tsb = alt.TrainSimBuilder(
    train_id="Henderson_NB_Freight",
    train_config=train_config,
    loco_con=consist,
)

# Build SetSpeedTrainSim (not SpeedLimitTrainSim)
print("Building Simulation...")
sim = tsb.make_set_speed_train_sim(
    network=network,
    link_path=link_path,
    speed_trace=speed_trace,
    save_interval=1  # Save every timestep for detailed analysis
)

print("="*70)
print("NORTHBOUND FREIGHT BRAKING SIMULATION")
print("="*70)
print(f"Train: 50 Loaded Manifest Cars + 4 Locomotives")
print(f"Route: Link 1 (Northbound Henderson Subdivision)")
print(f"Save Interval: Every timestep (High Fidelity)")
print("="*70)

# Run simulation
print("\nRunning simulation...")
sim.walk()

# Extract history
print("Extracting history...")
history = sim.history

# Convert to DataFrame
data = {
    'time_seconds': np.array(history.time_seconds),
    'dt_seconds': np.array(history.dt),
    'speed_meters_per_second': np.array(history.speed),
    'total_dist_meters': np.array(history.total_dist),
    'pwr_whl_out_watts': np.array(history.pwr_whl_out),
    'res_grade_newtons': np.array(history.res_grade),
    'res_curve_newtons': np.array(history.res_curve),
    'res_rolling_newtons': np.array(history.res_rolling),
    'res_aero_newtons': np.array(history.res_aero),
    'res_bearing_newtons': np.array(history.res_bearing),
    'mass_static_kilograms': np.array(history.mass_static)
}

df = pd.DataFrame(data)

# Save to CSV
output_file = "results/henderson_nb_freight_braking.csv"
df.to_csv(output_file, index=False)

print(f"\nTrain Mass: {df['mass_static_kilograms'].iloc[0]/1000:.1f} tonnes")
print(f"Results saved to {output_file}")
print("="*70)
