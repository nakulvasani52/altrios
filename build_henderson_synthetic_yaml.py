#!/usr/bin/env python3
"""
Build ALTRIOS-compatible YAML network from synthetic Henderson CSV.
This file uses the 'MP_ASC_DEC' column to separate NB (A) and SB (D) geometry
and incorporates the 'speed' column as the speed limit.
"""
import altrios as alt
import pandas as pd
import numpy as np
import os
import yaml
import json

INPUT_CSV = "data/nvasani2_altrios_segments_henderson_synthetic_top10.csv"
OUTPUT_YAML = "data/henderson_synthetic_network.yaml"
OUTPUT_META = "data/henderson_synthetic_meta.json"

def build_network():
    print(f"Reading {INPUT_CSV}...")
    df_all = pd.read_csv(INPUT_CSV)
    
    # Northbound (Ascending)
    df_nb = df_all[df_all['MP_ASC_DEC'] == 'A'].copy().sort_values('beg_mp')
    # Southbound (Descending)
    df_sb = df_all[df_all['MP_ASC_DEC'] == 'D'].copy().sort_values('beg_mp', ascending=False)
    
    mp_min = df_all['beg_mp'].min()
    mp_max = df_all['end_mp'].max()
    main_length = df_nb['length_m'].sum() 
    
    dummy_length = 50000.0 # 50km buffers
    total_len = main_length + 2 * dummy_length
    
    deg_to_rad = np.pi / 180.0
    
    def process_direction(df, direction_name):
        print(f"  Processing {direction_name}...")
        dists = np.concatenate(([0.0], np.cumsum(df['length_m'].to_numpy())))
        
        sign = 1.0 if direction_name == "NB" else -1.0
        elevs_main = np.concatenate(([0.0], np.cumsum(
            (df['length_m'] * df['grade_to_next'] * sign / 100.0).to_numpy()
        )))
        
        headings_main = np.concatenate(([0.0 if sign==1.0 else np.pi], (0.0 if sign==1.0 else np.pi) + np.cumsum(
            (df['curvature_deg'] * sign * deg_to_rad / 30.48 * df['length_m']).to_numpy()
        )))
        
        grid_dx = 50.0
        grid_offsets = np.arange(0, total_len + grid_dx, grid_dx)
        if grid_offsets[-1] > total_len: grid_offsets[-1] = float(total_len)
        
        grid_elevs = []
        grid_headings = []
        
        for x in grid_offsets:
            if x < dummy_length - 1000.0:
                grid_elevs.append(0.0)
                grid_headings.append(float(headings_main[0]))
            elif x < dummy_length:
                prog = float((x - (dummy_length - 1000.0)) / 1000.0)
                grid_elevs.append(float(prog * elevs_main[0]))
                grid_headings.append(float(headings_main[0]))
            elif x < dummy_length + main_length:
                rel_x = float(x - dummy_length)
                grid_elevs.append(float(np.interp(rel_x, dists, elevs_main)))
                grid_headings.append(float(np.interp(rel_x, dists, headings_main)))
            else:
                prog = float((x - (dummy_length + main_length)) / dummy_length)
                grid_elevs.append(float(elevs_main[-1] * (1 - prog)))
                grid_headings.append(float(headings_main[-1]))
                
        # Speed Limits
        speed_limits = []
        # Buffer 1
        speed_limits.append({'offset_start_meters': 0.0, 'offset_end_meters': float(dummy_length), 'speed_meters_per_second': 40.0})
        # Main
        current_offset = dummy_length
        for i, row in df.iterrows():
            l = float(row['length_m'])
            speed_limits.append({
                'offset_start_meters': float(current_offset),
                'offset_end_meters': float(current_offset + l),
                'speed_meters_per_second': float(row['speed'] * 0.44704)
            })
            current_offset += l
        # Buffer 2
        speed_limits.append({'offset_start_meters': float(dummy_length + main_length), 'offset_end_meters': float(total_len), 'speed_meters_per_second': 40.0})
        
        return grid_offsets, grid_elevs, grid_headings, speed_limits

    # Process NB
    nb_x, nb_e, nb_h, nb_s = process_direction(df_nb, "NB")
    # Process SB
    sb_x, sb_e, sb_h, sb_s = process_direction(df_sb, "SB")
    
    # Build YAML
    two_pi = 2.0 * np.pi
    
    # Add representer for numpy types to handle any missed casts
    def numpy_representer(walker, data):
        return walker.represent_float(float(data))
    yaml.add_representer(np.float64, numpy_representer)
    yaml.add_representer(np.float32, numpy_representer)

    def fmt_link(idx, x, e, h, s, total_l):
        elevs = [{'offset': float(_x), 'elev': float(_e)} for _x, _e in zip(x, e)]
        heads = [{'offset': float(_x), 'heading': float(_h % two_pi)} for _x, _h in zip(x, h)]
        return {
            'idx_curr': idx, 'idx_flip': 0, 'idx_next': 0, 'idx_next_alt': 0, 'idx_prev': 0, 'idx_prev_alt': 0,
            'osm_id': str(idx), 'length_meters': float(total_l),
            'elevs': elevs, 'headings': heads,
            'speed_set': {'is_head_end': False, 'speed_limits': s}
        }

    l0 = {'idx_curr': 0, 'idx_flip': 0, 'idx_next': 0, 'idx_next_alt': 0,
          'idx_prev': 0, 'idx_prev_alt': 0, 'osm_id': "0",
          'length_meters': 0.0, 'elevs': [], 'headings': [],
          'speed_set': None}
    l1 = fmt_link(1, nb_x, nb_e, nb_h, nb_s, total_len)
    l2 = fmt_link(2, sb_x, sb_e, sb_h, sb_s, total_len)
    
    tolerances = {"max_grade": 0.25, "max_curv_radians_per_meter": 0.05, "max_heading_step_radians": 0.5, "max_elev_step_meters": 0.5}
    
    print(f"  Writing YAML to {OUTPUT_YAML}...")
    with open(OUTPUT_YAML, 'w') as f:
        yaml.safe_dump([tolerances, [l0, l1, l2]], f, sort_keys=False)
        
    meta = {
        'mp_min': float(mp_min), 'mp_max': float(mp_max),
        'main_length_m': float(main_length), 'dummy_length_m': float(dummy_length),
        'total_length_m': float(total_len), 'grid_dx_m': 50.0
    }
    with open(OUTPUT_META, 'w') as f:
        json.dump(meta, f, indent=2)
    
    print(f"✓ Synthetic network and meta saved to {OUTPUT_YAML}")

if __name__ == "__main__":
    build_network()
