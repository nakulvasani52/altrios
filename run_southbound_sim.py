import altrios as alt
import pandas as pd
import numpy as np

# Load network
network_file = "data/henderson_network_altrios.yaml"
network = alt.Network.from_file(network_file)

# Helper function to create Location objects with Title Case keys
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

# Southbound: Start at beginning of Link 2 (Consolidated), End at Link 2 (Consolidated)
origin = create_location("Origin_SB", 2, 0.0, is_front=False)
destination = create_location("Destination_SB", 2, 117703.4, is_front=True)

# Load rail vehicle and locomotive config
rail_vehicle_file = "python/altrios/resources/rolling_stock/Passenger_Car.yaml"
rail_vehicle = alt.RailVehicle.from_file(rail_vehicle_file)

import create_robust_loco

# Define Robust Locomotive (4400 HP / 3.3 MW)
loco_unit = create_robust_loco.get_robust_loco()

# Train configuration: 10 cars, 2 locomotives (Amtrak Floridian)
train_config = alt.TrainConfig.from_pydict({
    "rail_vehicles": [rail_vehicle.to_pydict()] * 10,
    "n_cars_by_type": {"Passenger_Car": 10},
    "train_type": "Passenger",
    "train_length_meters": 260.0,
    "train_mass_kilograms": 1000000.0
})

consist = alt.Consist([loco_unit] * 2)

# Speed Trace and Link Path
import generate_speed_trace
speed_trace, link_path = generate_speed_trace.get_speed_trace("SB")

# Create simulation builder
tsb = alt.TrainSimBuilder(
    train_id="Henderson_SB_Passenger",
    train_config=train_config,
    loco_con=consist,
)

# Create simulation
print("Creating Southbound Passenger Simulation (252 -> 242)...")
sim = tsb.make_set_speed_train_sim(
    network=network,
    link_path=link_path,
    speed_trace=speed_trace,
    save_interval=1,
)

# Run simulation
print("Running physics...")
sim.walk()

# Get history
print("Processing simulation results...")
sim_data = sim.to_pydict()
history = sim_data.get('history', {})
df = pd.DataFrame(history)

# Save results with expanded fields
output_cols = [
    'time_seconds', 'dt_seconds', 'i', 'total_dist_meters', 'offset_meters', 'offset_back_meters',
    'link_idx_front', 'link_idx_back', 'offset_in_link_meters',
    'speed_meters_per_second', 'speed_limit_meters_per_second', 'speed_target_meters_per_second',
    'res_grade_newtons', 'res_curve_newtons', 'res_rolling_newtons', 'res_bearing_newtons',
    'res_aero_newtons', 'res_davis_b_newtons',
    'pwr_whl_out_watts', 'pwr_res_watts', 'pwr_accel_watts',
    'energy_whl_out_joules', 'energy_whl_out_pos_joules', 'energy_whl_out_neg_joules',
    'mass_static_kilograms', 'mass_freight_kilograms', 'mass_rot_kilograms', 'weight_static_newtons',
    'grade_front', 'grade_back', 'elev_front_meters', 'elev_back_meters', 'length_meters'
]

# Handle friction brake history if available
if 'fric_brake' in sim_data:
    fb_history = sim_data['fric_brake'].get('history', {})
    if fb_history:
        fb_df = pd.DataFrame(fb_history)
        # Rename columns to match user request
        fb_df = fb_df.rename(columns={
            'force_newtons': 'fric_brake_force_newtons',
            'force_max_curr_newtons': 'fric_brake_force_max_curr_newtons'
        })
        # Add to main list
        output_cols.extend(['fric_brake_force_newtons', 'fric_brake_force_max_curr_newtons'])
        # Concatenate (assuming same length and order)
        df = pd.concat([df, fb_df[['fric_brake_force_newtons', 'fric_brake_force_max_curr_newtons']]], axis=1)

# Filter for available columns
available_cols = [col for col in output_cols if col in df.columns]
df_focused = df[available_cols]

output_file = "results/henderson_sb_simulation.csv"
df_focused.to_csv(output_file, index=False)

# Summary stats
print("\n" + "="*60)
print("SOUTHBOUND PASSENGER SIMULATION COMPLETE")
print("="*60)
print(f"Total Time: {df['time_seconds'].iloc[-1]:.1f} seconds")
print(f"Total Distance: {df['total_dist_meters'].iloc[-1]/1000:.2f} km")
print(f"Max Speed: {df['speed_meters_per_second'].max() * 2.237:.1f} mph")
print(f"Results saved to: {output_file}")
print("="*60)
