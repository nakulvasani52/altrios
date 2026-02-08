import altrios as alt
import pandas as pd
import numpy as np
import os
import yaml

# Configuration
input_csv = "data/henderson_segments.csv"
output_yaml = "data/henderson_network_altrios.yaml"

def build_network():
    print(f"Reading {input_csv}...")
    if not os.path.exists(input_csv):
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")
    
    df = pd.read_csv(input_csv)
    # CRITICAL FIX: Sort by milepost to ensure correct geographical ordering
    df = df.sort_values('beg_mp').reset_index(drop=True)
    
    main_length = float(df['length_m'].sum())
    # 50km buffers for "infinite track" robustness
    dummy_length = 50000.0
    total_len = main_length + 2 * dummy_length
    
    # 1. Prepare Main physics arrays
    main_dists = np.concatenate(([0.0], np.cumsum(df['length_m'].to_numpy())))
    main_elevs = np.concatenate(([0.0], np.cumsum((df['length_m'] * df['grade_to_next'] / 100.0).to_numpy())))
    
    deg_to_rad = np.pi / 180.0
    main_headings = np.concatenate(([0.0], np.cumsum((df['curvature_deg'] * deg_to_rad / 30.48 * df['length_m']).to_numpy())))
    
    # 2. Prepare Reverse Prepared Data
    df_rev = df.iloc[::-1].reset_index(drop=True)
    rev_main_dists = np.concatenate(([0.0], np.cumsum(df_rev['length_m'].to_numpy())))
    rev_main_elevs = np.concatenate(([0.0], np.cumsum((df_rev['length_m'] * df_rev['grade_to_next'] * -1.0 / 100.0).to_numpy())))
    # Facing South (PI)
    rev_main_headings = np.concatenate(([np.pi], np.pi + np.cumsum((df_rev['curvature_deg'] * deg_to_rad / 30.48 * df_rev['length_m'] * -1.0).to_numpy())))

    # 3. Interpolation Logic with smooth transitions for Ring topology
    ramp_length = 1000.0  # 1km smooth ramp at transitions
    
    def get_nb_physics(x):
        if x < dummy_length - ramp_length:
            return 0.0, 0.0  # Flat start buffer
        elif x < dummy_length:
            # Smooth ramp up to main track elevation
            progress = (x - (dummy_length - ramp_length)) / ramp_length
            target_elev = main_elevs[0]
            return progress * target_elev, 0.0
        elif x < dummy_length + main_length:
            return np.interp(x - dummy_length, main_dists, main_elevs), np.interp(x - dummy_length, main_dists, main_headings)
        elif x < dummy_length + main_length + ramp_length:
            # Smooth ramp down to flat end buffer
            progress = (x - (dummy_length + main_length)) / ramp_length
            start_elev = main_elevs[-1]
            return start_elev * (1 - progress), main_headings[-1]
        else:
            return 0.0, main_headings[-1]  # Flat end buffer (matches start for Ring)

    def get_sb_physics(x):
        if x < dummy_length - ramp_length:
            return 0.0, np.pi  # Flat start buffer
        elif x < dummy_length:
            # Smooth ramp up to main track elevation
            progress = (x - (dummy_length - ramp_length)) / ramp_length
            target_elev = rev_main_elevs[0]
            return progress * target_elev, np.pi
        elif x < dummy_length + main_length:
            return np.interp(x - dummy_length, rev_main_dists, rev_main_elevs), np.interp(x - dummy_length, rev_main_dists, rev_main_headings)
        elif x < dummy_length + main_length + ramp_length:
            # Smooth ramp down to flat end buffer
            progress = (x - (dummy_length + main_length)) / ramp_length
            start_elev = rev_main_elevs[-1]
            return start_elev * (1 - progress), rev_main_headings[-1]
        else:
            return 0.0, rev_main_headings[-1]  # Flat end buffer (matches start for Ring)

    # 4. Sampling onto 10m grid (lower res to speed up YAML writing/loading, but still very robust)
    grid_dx = 10.0 
    grid_offsets = np.arange(0, total_len + grid_dx, grid_dx)
    if grid_offsets[-1] > total_len: grid_offsets[-1] = total_len
    
    two_pi = 2.0 * np.pi

    # NB Link
    elevs_1 = [{'offset': float(x), 'elev': float(get_nb_physics(x)[0])} for x in grid_offsets]
    headings_1 = [{'offset': float(x), 'heading': float(get_nb_physics(x)[1] % two_pi)} for x in grid_offsets]
    speed_limits_1 = [{'offset_start_meters': 0.0, 'offset_end_meters': total_len, 'speed_meters_per_second': 45.0}] # Single limit for simplicity

    # SB Link
    elevs_2 = [{'offset': float(x), 'elev': float(get_sb_physics(x)[0])} for x in grid_offsets]
    headings_2 = [{'offset': float(x), 'heading': float(get_sb_physics(x)[1] % two_pi)} for x in grid_offsets]
    speed_limits_2 = [{'offset_start_meters': 0.0, 'offset_end_meters': total_len, 'speed_meters_per_second': 45.0}]

    # Link 0 (Null)
    l0 = {'idx_curr': 0, 'idx_flip': 0, 'idx_next': 0, 'idx_next_alt': 0, 'idx_prev': 0, 'idx_prev_alt': 0, 'osm_id': "0", 'length_meters': 0.0, 'elevs': [], 'headings': [], 'speed_set': None}
    
    # L1: Standard Linear Topology (No Ring)
    l1 = {'idx_curr': 1, 'idx_flip': 0, 'idx_next': 0, 'idx_next_alt': 0, 'idx_prev': 0, 'idx_prev_alt': 0, 'osm_id': "1", 'length_meters': total_len, 'elevs': elevs_1, 'headings': headings_1, 'speed_set': {'is_head_end': False, 'speed_limits': speed_limits_1}}
    
    l2 = {'idx_curr': 2, 'idx_flip': 0, 'idx_next': 0, 'idx_next_alt': 0, 'idx_prev': 0, 'idx_prev_alt': 0, 'osm_id': "2", 'length_meters': total_len, 'elevs': elevs_2, 'headings': headings_2, 'speed_set': {'is_head_end': False, 'speed_limits': speed_limits_2}}

    tolerances = {"max_grade": 0.25, "max_curv_radians_per_meter": 0.05, "max_heading_step_radians": 0.5, "max_elev_step_meters": 0.1}
    with open(output_yaml, 'w') as f:
        yaml.safe_dump([tolerances, [l0, l1, l2]], f, sort_keys=False)
    print(f"Network Saved with 50km buffers and {len(grid_offsets)} points per link.")

if __name__ == "__main__":
    build_network()
