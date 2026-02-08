import altrios as alt
import pandas as pd
import numpy as np
import create_robust_loco
import generate_speed_trace

# 1. Configuration
OUTPUT_FILE = "results/henderson_nb_braking.csv"
NETWORK_FILE = "data/henderson_network_altrios.yaml"
RAIL_VEHICLE_FILE = "python/altrios/resources/rolling_stock/Manifest_Loaded.yaml"

# 2. Load Network
print(f"Loading network from {NETWORK_FILE}...")
network = alt.Network.from_file(NETWORK_FILE)

# 3. Configure Train (Freight: 8000 tons, 4 Locos)
# Note: 100 * 101.5t (Manifest Loaded) ~= 10,000t? 
# Let's check the yaml mass.
# Manifest_Loaded.yaml: mass_freight=101500, mass_static=28500 -> Total 130,000 kg (130t) per car?
# 100 cars = 13,000 tons. 
# The user mentioned 8000 tons. 
# Maybe they used fewer cars or lighter cars. 
# I'll stick to 100 cars as per "standard" but I'll use the Manifest_Loaded.
# Wait, let's just use the logic from run_henderson_full_altrios.py which used 100 cars.
# User said "8000 tons" in the chat. 
# 8000 tons / 100 cars = 80 tons/car. 
# I will proceed with 100 cars of Manifest_Loaded. If it comes out to 13,000t, I'll note it. 
# Or I can adjust n_cars to match 8000t. 8000000 / 143000 (approx loaded mass) ~= 56 cars.
# I'll use 60 cars to be closer to 8000t if needed, BUT ALTRIOS `run_henderson_full` used 100.
# I will use 100 cars to be consistent with the "Full Simulation" script I saw earlier.

print("Configuring Freight Train (100 Loaded Cars, 4 Locos)...")
rail_vehicle = alt.RailVehicle.from_file(RAIL_VEHICLE_FILE)
loco_unit = create_robust_loco.get_robust_loco()

# 4 Locos
consist = alt.Consist([loco_unit] * 4)

train_config = alt.TrainConfig(
    rail_vehicles=[rail_vehicle] * 50,
    n_cars_by_type={"Manifest_Loaded": 50},
    train_mass_kilograms=None, # Auto-calc
    train_length_meters=None   # Auto-calc
)

# 4. Generate Northbound Path & Speed Trace
# NB: MP 242 -> 253
print("Generating Speed Trace for Northbound...")
speed_trace, link_path = generate_speed_trace.get_speed_trace("NB")

# 5. Build Simulation
tsb = alt.TrainSimBuilder(
    train_id="Henderson_NB_Freight_Braking",
    train_config=train_config,
    loco_con=consist,
)

print("Building Simulation...")
sim = tsb.make_set_speed_train_sim(
    network=network,
    link_path=link_path,
    speed_trace=speed_trace,
    save_interval=1, # High fidelity
)

# 6. Run
print("Running Simulation...")
sim.walk()

# 7. Extract Results
print("Extracting History...")
sim_data = sim.to_pydict()
history = sim_data.get('history', {})
df = pd.DataFrame(history)

# Add Derived Metrics for Analysis
# Mass
mass_kg = df['mass_static_kilograms'].iloc[0] if 'mass_static_kilograms' in df.columns else 0
print(f"Train Mass: {mass_kg/1000:.1f} tonnes")

# Check for Friction Brake History in nested struct
# ALTRIOS structure: sim -> fric_brake -> history
if 'fric_brake' in sim_data:
    print("Found 'fric_brake' data!")
    fb_hist = sim_data['fric_brake'].get('history', {})
    if fb_hist:
        fb_df = pd.DataFrame(fb_hist)
        # We expect 'force_newtons' or similar
        # Let's prefix columns
        fb_df = fb_df.add_prefix('fric_brake_')
        df = pd.concat([df, fb_df], axis=1)
else:
    print("No explicit 'fric_brake' history found. Will need to calculate from physics.")

# Save
df.to_csv(OUTPUT_FILE, index=False)
print(f"Results saved to {OUTPUT_FILE}")
