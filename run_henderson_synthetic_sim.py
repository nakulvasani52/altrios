#!/usr/bin/env python3
"""
Run ALTRIOS Northbound and Southbound simulations on the Synthetic Optimal Henderson network.
"""
import altrios as alt
import pandas as pd
import numpy as np
import pathlib
import json
import time
import create_robust_loco

# Paths
NETWORK_FILE = pathlib.Path("data/henderson_synthetic_network.yaml")
SEGMENTS_CSV = pathlib.Path("data/nvasani2_altrios_segments_henderson_synthetic_top10.csv")
META_FILE = pathlib.Path("data/henderson_synthetic_meta.json")
OUTPUT_DIR = pathlib.Path("results/synthetic_sim")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with open(META_FILE, 'r') as f:
    meta = json.load(f)

MP_MIN = meta['mp_min']
MP_MAX = meta['mp_max']
MAIN_LENGTH = meta['main_length_m']
DUMMY_LENGTH = meta['dummy_length_m']
TOTAL_LENGTH = meta['total_length_m']

network = alt.Network.from_file(str(NETWORK_FILE))

def run_simulation(direction):
    print(f"\n--- Running {direction} Simulation (Synthetic Optimal) ---")
    link_idx = 1 if direction == "NB" else 2
    
    # ── 1. Generate speed trace from segment data ──────────────────────────────
    print(f"  [1/4] Generating speed trace for {direction}...")
    df_all = pd.read_csv(SEGMENTS_CSV)
    df = df_all[df_all['MP_ASC_DEC'] == ('A' if direction == "NB" else 'D')].copy()
    
    # Sort correctly (NB = original order, SB = reversed)
    if direction == "NB":
        df = df.sort_values('beg_mp')
    else:
        df = df.sort_values('beg_mp', ascending=False)
        
    df = df.reset_index(drop=True)
    
    seg_dists = np.concatenate(([0.0], np.cumsum(df['length_m'].to_numpy())))
    seg_speeds_mph = df['speed'].to_numpy()
    
    # Interpolate speed trace
    speed_func_dists = np.concatenate(([0.0], seg_dists[:-1] + np.diff(seg_dists)/2, [MAIN_LENGTH]))
    speed_func_vals = np.concatenate(([seg_speeds_mph[0]], seg_speeds_mph, [seg_speeds_mph[-1]])) * 0.44704
    
    SAFE_LENGTH = TOTAL_LENGTH - 5000.0
    dx = 1.0
    all_x = np.arange(0, SAFE_LENGTH, dx)
    all_v = np.full_like(all_x, seg_speeds_mph.mean() * 0.44704)
    
    buffer_start = all_x < DUMMY_LENGTH
    buffer_end = all_x >= (DUMMY_LENGTH + MAIN_LENGTH)
    main_m = ~buffer_start & ~buffer_end
    
    all_v[buffer_start] = seg_speeds_mph[0] * 0.44704
    all_v[buffer_end] = seg_speeds_mph[-1] * 0.44704
    all_v[main_m] = np.interp(all_x[main_m] - DUMMY_LENGTH, speed_func_dists, speed_func_vals)
    
    # Decel ramp at very end
    decel_zone = 3000.0
    decel_start = SAFE_LENGTH - decel_zone
    dm = all_x >= decel_start
    if dm.any():
        prog = (all_x[dm] - decel_start) / decel_zone
        all_v[dm] = all_v[dm] * (1.0 - prog * 0.95)
    
    all_v = np.maximum(all_v, 0.5)
    
    # Time trace
    dt_arr = np.diff(all_x) / ((all_v[:-1] + all_v[1:]) / 2.0)
    all_time = np.concatenate(([0.0], np.cumsum(dt_arr)))
    
    t_target = np.arange(0, all_time[-1], 1.0)
    v_i = np.interp(t_target, all_time, all_v)
    
    trace_df = pd.DataFrame({'time_seconds': t_target, 'speed_meters_per_second': v_i})
    trace_file = OUTPUT_DIR / f"speed_trace_{direction.lower()}.csv"
    trace_df.to_csv(trace_file, index=False)
    
    lp_file = OUTPUT_DIR / f"link_path_{direction.lower()}.csv"
    pd.DataFrame({'link_idx': [link_idx]}).to_csv(lp_file, index=False)
    
    speed_trace = alt.SpeedTrace.from_csv_file(str(trace_file))
    link_path = alt.LinkPath.from_csv_file(str(lp_file))
    
    # ── 2. Configure train ──────────────────────────────────────────────────────
    print("  [2/4] Configuring train consist...")
    rail_vehicle = alt.RailVehicle.from_file(
        alt.resources_root() / "rolling_stock/Manifest_Loaded.yaml"
    )
    train_config = alt.TrainConfig(
        rail_vehicles=[rail_vehicle],
        n_cars_by_type={"Manifest_Loaded": 100}
    )
    loco_unit = create_robust_loco.get_robust_loco()
    loco_con = alt.Consist([loco_unit] * 4, 1)
    
    # ── 3. Build and Run ────────────────────────────────────────────────────────
    print("  [3/4] Building and walking simulation...")
    tsb = alt.TrainSimBuilder(
        train_id=f"Henderson_Synthetic_{direction}",
        train_config=train_config,
        loco_con=loco_con
    )
    sim = tsb.make_set_speed_train_sim(
        network=network,
        link_path=link_path,
        speed_trace=speed_trace,
        save_interval=1
    )
    sim.walk()
    
    # ── 4. Extract and Save ─────────────────────────────────────────────────────
    print("  [4/4] Saving results...")
    df_res = pd.DataFrame(sim.to_pydict()['history'])
    df_res['dist_in_main'] = df_res['total_dist_meters'] - DUMMY_LENGTH
    if direction == "NB":
        df_res['milepost'] = MP_MIN + df_res['dist_in_main'] / 1609.34
    else:
        df_res['milepost'] = MP_MAX - df_res['dist_in_main'] / 1609.34
        
    out_csv = OUTPUT_DIR / f"{direction.lower()}_simulation.csv"
    df_res.to_csv(out_csv, index=False)
    print(f"  ✓ Saved to {out_csv}")

if __name__ == "__main__":
    run_simulation("NB")
    run_simulation("SB")
