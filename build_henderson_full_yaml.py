#!/usr/bin/env python3
"""
Build ALTRIOS-compatible YAML network from full Henderson subdivision CSV.

Reads the nvasani2_altrios_segments_henderson_sim_run CSV (MP 176.9-318.4, ~141 miles),
filters to TrackNumber=='SG', and builds a 2-link YAML network
(NB link + SB link) with 50 km dummy buffers on each end.
"""

import altrios as alt
import pandas as pd
import numpy as np
import os
import yaml

# Configuration
INPUT_CSV = "data/nvasani2_altrios_segments_henderson_sim_run"
OUTPUT_YAML = "data/henderson_full_network.yaml"

def build_network():
    print(f"Reading {INPUT_CSV}...")
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)
    print(f"  Total rows: {len(df)}")
    print(f"  Track numbers: {df['TrackNumber'].unique()}")

    # Filter to single-track main (SG)
    df = df[df['TrackNumber'] == 'SG'].copy()
    print(f"  After SG filter: {len(df)} rows")

    # Sort by milepost for correct geographical ordering
    df = df.sort_values('beg_mp').reset_index(drop=True)

    mp_min = df['beg_mp'].min()
    mp_max = df['end_mp'].max()
    print(f"  Milepost range: {mp_min:.2f} - {mp_max:.2f}")

    main_length = float(df['length_m'].sum())
    print(f"  Main track length: {main_length:.1f} m ({main_length/1609.34:.2f} miles)")

    # 50 km buffers for "infinite track" robustness
    dummy_length = 50000.0
    total_len = main_length + 2 * dummy_length
    print(f"  Total link length (with buffers): {total_len:.1f} m")

    # ── 1. Prepare NB physics arrays ─────────────────────────────────────────
    main_dists = np.concatenate(([0.0], np.cumsum(df['length_m'].to_numpy())))
    main_elevs = np.concatenate(([0.0], np.cumsum(
        (df['length_m'] * df['grade_to_next'] / 100.0).to_numpy()
    )))

    deg_to_rad = np.pi / 180.0
    main_headings = np.concatenate(([0.0], np.cumsum(
        (df['curvature_deg'] * deg_to_rad / 30.48 * df['length_m']).to_numpy()
    )))

    # ── 2. Prepare SB (reverse) physics arrays ──────────────────────────────
    df_rev = df.iloc[::-1].reset_index(drop=True)
    rev_main_dists = np.concatenate(([0.0], np.cumsum(df_rev['length_m'].to_numpy())))
    rev_main_elevs = np.concatenate(([0.0], np.cumsum(
        (df_rev['length_m'] * df_rev['grade_to_next'] * -1.0 / 100.0).to_numpy()
    )))
    rev_main_headings = np.concatenate(([np.pi], np.pi + np.cumsum(
        (df_rev['curvature_deg'] * deg_to_rad / 30.48 * df_rev['length_m'] * -1.0).to_numpy()
    )))

    # ── 3. Interpolation with smooth transitions ────────────────────────────
    ramp_length = 1000.0  # 1 km smooth ramp at buffer-main transitions

    def get_nb_physics(x):
        if x < dummy_length - ramp_length:
            return 0.0, 0.0
        elif x < dummy_length:
            progress = (x - (dummy_length - ramp_length)) / ramp_length
            target_elev = main_elevs[0]
            return progress * target_elev, 0.0
        elif x < dummy_length + main_length:
            return (np.interp(x - dummy_length, main_dists, main_elevs),
                    np.interp(x - dummy_length, main_dists, main_headings))
        elif x < dummy_length + main_length + ramp_length:
            progress = (x - (dummy_length + main_length)) / ramp_length
            start_elev = main_elevs[-1]
            return start_elev * (1 - progress), main_headings[-1]
        else:
            return 0.0, main_headings[-1]

    def get_sb_physics(x):
        if x < dummy_length - ramp_length:
            return 0.0, np.pi
        elif x < dummy_length:
            progress = (x - (dummy_length - ramp_length)) / ramp_length
            target_elev = rev_main_elevs[0]
            return progress * target_elev, np.pi
        elif x < dummy_length + main_length:
            return (np.interp(x - dummy_length, rev_main_dists, rev_main_elevs),
                    np.interp(x - dummy_length, rev_main_dists, rev_main_headings))
        elif x < dummy_length + main_length + ramp_length:
            progress = (x - (dummy_length + main_length)) / ramp_length
            start_elev = rev_main_elevs[-1]
            return start_elev * (1 - progress), rev_main_headings[-1]
        else:
            return 0.0, rev_main_headings[-1]

    # ── 4. Sample onto 50 m grid (manageable for 141-mile route) ─────────────
    grid_dx = 50.0
    grid_offsets = np.arange(0, total_len + grid_dx, grid_dx)
    if grid_offsets[-1] > total_len:
        grid_offsets[-1] = total_len
    print(f"  Grid points per link: {len(grid_offsets)} (dx = {grid_dx} m)")

    two_pi = 2.0 * np.pi

    # NB Link
    print("  Building NB link elevations & headings...")
    elevs_1 = [{'offset': float(x), 'elev': float(get_nb_physics(x)[0])} for x in grid_offsets]
    headings_1 = [{'offset': float(x), 'heading': float(get_nb_physics(x)[1] % two_pi)} for x in grid_offsets]
    speed_limits_1 = [{'offset_start_meters': 0.0, 'offset_end_meters': total_len,
                       'speed_meters_per_second': 45.0}]

    # SB Link
    print("  Building SB link elevations & headings...")
    elevs_2 = [{'offset': float(x), 'elev': float(get_sb_physics(x)[0])} for x in grid_offsets]
    headings_2 = [{'offset': float(x), 'heading': float(get_sb_physics(x)[1] % two_pi)} for x in grid_offsets]
    speed_limits_2 = [{'offset_start_meters': 0.0, 'offset_end_meters': total_len,
                       'speed_meters_per_second': 45.0}]

    # ── 5. Assemble YAML structure ──────────────────────────────────────────
    l0 = {'idx_curr': 0, 'idx_flip': 0, 'idx_next': 0, 'idx_next_alt': 0,
          'idx_prev': 0, 'idx_prev_alt': 0, 'osm_id': "0",
          'length_meters': 0.0, 'elevs': [], 'headings': [],
          'speed_set': None}

    l1 = {'idx_curr': 1, 'idx_flip': 0, 'idx_next': 0, 'idx_next_alt': 0,
          'idx_prev': 0, 'idx_prev_alt': 0, 'osm_id': "1",
          'length_meters': total_len, 'elevs': elevs_1, 'headings': headings_1,
          'speed_set': {'is_head_end': False, 'speed_limits': speed_limits_1}}

    l2 = {'idx_curr': 2, 'idx_flip': 0, 'idx_next': 0, 'idx_next_alt': 0,
          'idx_prev': 0, 'idx_prev_alt': 0, 'osm_id': "2",
          'length_meters': total_len, 'elevs': elevs_2, 'headings': headings_2,
          'speed_set': {'is_head_end': False, 'speed_limits': speed_limits_2}}

    tolerances = {
        "max_grade": 0.25,
        "max_curv_radians_per_meter": 0.05,
        "max_heading_step_radians": 0.5,
        "max_elev_step_meters": 0.5   # Slightly higher than before for longer route
    }

    print(f"  Writing YAML to {OUTPUT_YAML}...")
    with open(OUTPUT_YAML, 'w') as f:
        yaml.safe_dump([tolerances, [l0, l1, l2]], f, sort_keys=False)

    file_size_mb = os.path.getsize(OUTPUT_YAML) / 1e6
    print(f"  ✓ Network saved: {file_size_mb:.1f} MB, {len(grid_offsets)} points/link")

    # Save metadata for downstream scripts
    meta = {
        'mp_min': float(mp_min),
        'mp_max': float(mp_max),
        'main_length_m': float(main_length),
        'dummy_length_m': float(dummy_length),
        'total_length_m': float(total_len),
        'grid_dx_m': float(grid_dx),
    }
    import json
    with open("data/henderson_full_meta.json", 'w') as f:
        json.dump(meta, f, indent=2)
    print(f"  ✓ Metadata saved to data/henderson_full_meta.json")


if __name__ == "__main__":
    build_network()
