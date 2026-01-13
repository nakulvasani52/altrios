import time
import altrios as alt
import numpy as np
import pandas as pd
import yaml
import os

# Configuration
network_file = "data/henderson_network_altrios.yaml"

# Helper for object creation
def create_location(loc_id, link_idx, offset):
    return alt.Location.from_pydict({
        "Location ID": loc_id,
        "Offset (m)": offset,
        "Link Index": link_idx,
        "Is Front End": False,
        "Grid Emissions Region": "US",
        "Electricity Price Region": "US", 
        "Liquid Fuel Price Region": "US"
    })

def create_rail_vehicle(car_type="286k"):
    # Using keys from Manifest_Loaded.yaml
    return alt.RailVehicle.from_pydict({
        "car_type": car_type,
        "freight_type": "Manifest",
        "axle_count": 4,
        "brake_count": 1,
        "length_meters": 20.0,
        "mass_static_base_kilograms": 30000.0, # Updated from empty/loaded mix
        "mass_freight_kilograms": 99727.0, # 143 total - 30 empty
        "mass_rot_per_axle_kilograms": 1000.0,
        "bearing_res_per_axle_newtons": 80.0,
        "davis_b_seconds_per_meter": 0.0,
        "rolling_ratio": 0.001,
        "braking_ratio": 0.1, # YAML has just braking_ratio
        "cd_area_square_meters": 10.0, # YAML has single area
        "speed_max_meters_per_second": 35.0, # YAML has single speed max
        "curve_coeff_0": 0.056,
        "curve_coeff_1": 0.438,
        "curve_coeff_2": 0.010
    })

def run_simulation():
    print(f"Loading network: {network_file}")
    network = alt.Network.from_file(network_file)
    print("Network loaded successfully.")

    locations = {
        "Origin": [create_location("Origin", 1, 0.0)],
        "Destination": [create_location("Destination", 3, 1000.0)],
        "Origin_Rev": [create_location("Origin_Rev", 4, 0.0)],
        "Destination_Rev": [create_location("Destination_Rev", 6, 1000.0)]
    }

    # Loco
    loco = alt.Locomotive.default()
    loco_con = alt.Consist([loco] * 4) 

    rail_vehicle = create_rail_vehicle("286k")

    train_config = alt.TrainConfig.from_pydict({
        "rail_vehicles": [rail_vehicle.to_pydict()],
        "n_cars_by_type": {"286k": 100},
        "rail_vehicle_type": "286k",
        "train_type": "Freight",
        "train_length_meters": 2000.0,
        "train_mass_kilograms": 100 * 129727.0,
        # "cd_area_vec": optional
    })
    
    tsb = alt.TrainSimBuilder(
        train_id="HendersonRun",
        origin_id="Origin",
        destination_id="Destination",
        train_config=train_config,
        loco_con=loco_con,
        init_train_state=None
    )

    print("Building SpeedLimitTrainSim...")
    train_sim = tsb.make_speed_limit_train_sim(
        location_map=locations,
        save_interval=1,
        simulation_days=1,
        scenario_year=2024
    )

    print("Running Dispatch...")
    est_time_net, _ = alt.make_est_times(train_sim, network)
    
    path_bundle = alt.run_dispatch(
        network,
        alt.SpeedLimitTrainSimVec([train_sim]),
        [est_time_net],
        False, 
        False
    )
    
    if not path_bundle:
        print("Dispatch failed: No path found.")
        return

    timed_path = path_bundle[0]
    # print(f"Path found with {len(timed_path)} points.") # No len support
    
    print("Simulating physics...")
    t0 = time.time()
    train_sim.walk_timed_path(network, timed_path)
    dt = time.time() - t0
    
    print(f"Simulation Complete in {dt:.3f}s")
    
    # Results
    try:
        df_hist = train_sim.to_dataframe(pandas=True)
        print("Columns available:", sorted(df_hist.columns.tolist()))
        
        # Check distance
        if 'history.total_dist_meters' in df_hist.columns:
            total_dist = df_hist['history.total_dist_meters'].iloc[-1]
            print(f"Total Distance Traveled: {total_dist:.2f} meters")
        
        # Use direct method for energy if column missing
        total_energy = train_sim.get_energy_fuel_joules(False) / 3.6e9
        
        max_speed = df_hist['history.speed_meters_per_second'].max() * 2.23694
        
        print(f"Total Fuel Energy: {total_energy:.4f} MWh")
        print(f"Max Speed Achieved: {max_speed:.2f} mph")
        
        df_hist.to_csv("results/henderson_altrios_simulation.csv", index=False)
        print("Results saved to results/henderson_altrios_simulation.csv")
        
    except Exception as e:
        print(f"Error processing results: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_simulation()
