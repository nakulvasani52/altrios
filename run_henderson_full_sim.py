#!/usr/bin/env python3
"""
Run complete ALTRIOS simulation on full Henderson subdivision (MP 176.9 - 317.5).

Pipeline:
  1. Loads the full Henderson network YAML
  2. Generates speed trace from per-segment speed limits (NB direction)
  3. Configures a heavy freight train (100 loaded manifest, 4 locos)
  4. Runs SetSpeedTrainSim
  5. Extracts results, maps distance -> Milepost, saves CSV
"""

import time
import json
import pandas as pd
import numpy as np
from pathlib import Path

import altrios as alt
import create_robust_loco

# ── Configuration ────────────────────────────────────────────────────────────
NETWORK_FILE   = Path("data/henderson_full_network.yaml")
SEGMENTS_CSV   = Path("data/nvasani2_altrios_segments_henderson_sim_run")
META_FILE      = Path("data/henderson_full_meta.json")
OUTPUT_DIR     = Path("results/henderson_full_sim")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SAVE_INTERVAL = 1

print("=" * 80)
print("ALTRIOS Full Henderson Subdivision Simulation (NB)")
print("=" * 80)

# ── 1. Load network ─────────────────────────────────────────────────────────
print("\n[1/6] Loading network...")
network = alt.Network.from_file(str(NETWORK_FILE))
print(f"  ✓ Network loaded successfully")

# Load route metadata
with open(META_FILE) as f:
    meta = json.load(f)
MP_MIN         = meta['mp_min']
MP_MAX         = meta['mp_max']
MAIN_LENGTH    = meta['main_length_m']
DUMMY_LENGTH   = meta['dummy_length_m']
TOTAL_LENGTH   = meta['total_length_m']
print(f"  MP range: {MP_MIN:.2f} – {MP_MAX:.2f}")
print(f"  Main length: {MAIN_LENGTH:.0f} m ({MAIN_LENGTH/1609.34:.1f} mi)")

# ── 2. Generate speed trace from segment data ───────────────────────────────
print("\n[2/6] Generating NB speed trace from segment data...")
seg = pd.read_csv(SEGMENTS_CSV)
seg = seg[seg['TrackNumber'] == 'SG'].copy()
seg = seg.sort_values('beg_mp').reset_index(drop=True)

# Build distance → speed mapping from the actual segment speed limits
seg_dists = np.concatenate(([0.0], np.cumsum(seg['length_m'].to_numpy())))
seg_speeds_mph = seg['speed'].to_numpy()

# Extend speed at boundaries
speed_func_dists = np.concatenate(([0.0], seg_dists[:-1] + np.diff(seg_dists) / 2, [MAIN_LENGTH]))
speed_func_vals  = np.concatenate(([seg_speeds_mph[0]], seg_speeds_mph, [seg_speeds_mph[-1]])) * 0.44704  # mph→m/s

# Build per-meter speed trace across full link (buffer + main + buffer)
# Leave 5 km margin at end so the train front doesn't overrun
SAFE_LENGTH = TOTAL_LENGTH - 5000.0
dx = 1.0
all_x = np.arange(0, SAFE_LENGTH, dx)

all_v = np.full_like(all_x, seg_speeds_mph.mean() * 0.44704)  # default = mean speed

# Buffer region: use first/last speed
buffer_mask_start = all_x < DUMMY_LENGTH
buffer_mask_end   = all_x >= (DUMMY_LENGTH + MAIN_LENGTH)
main_mask         = ~buffer_mask_start & ~buffer_mask_end

all_v[buffer_mask_start] = seg_speeds_mph[0] * 0.44704
all_v[buffer_mask_end]   = seg_speeds_mph[-1] * 0.44704
all_v[main_mask] = np.interp(all_x[main_mask] - DUMMY_LENGTH, speed_func_dists, speed_func_vals)

# Decelerate to near-zero in last 3 km to avoid overrun
DECEL_ZONE = 3000.0
decel_start = SAFE_LENGTH - DECEL_ZONE
decel_mask = all_x >= decel_start
if decel_mask.any():
    progress = (all_x[decel_mask] - decel_start) / DECEL_ZONE  # 0→1
    all_v[decel_mask] = all_v[decel_mask] * (1.0 - progress * 0.95)  # ramp down to 5%

# Ensure minimum speed
all_v = np.maximum(all_v, 0.5)

# Convert distance-speed to time-speed (ALTRIOS needs time-based trace)
d_dist = np.diff(all_x)
v_mid  = (all_v[:-1] + all_v[1:]) / 2.0
dt     = d_dist / v_mid
all_time = np.concatenate(([0.0], np.cumsum(dt)))

# Downsample to 1-second intervals
time_target = np.arange(0, all_time[-1], 1.0)
v_interp = np.interp(time_target, all_time, all_v)

trace_df = pd.DataFrame({
    'time_seconds': time_target,
    'speed_meters_per_second': v_interp
})

trace_file = OUTPUT_DIR / "speed_trace_nb.csv"
trace_df.to_csv(trace_file, index=False)
print(f"  ✓ Speed trace: {len(trace_df)} points, "
      f"{time_target[-1]/60:.0f} min total time")

# Link path (single link for NB)
lp_file = OUTPUT_DIR / "link_path_nb.csv"
pd.DataFrame({'link_idx': [1]}).to_csv(lp_file, index=False)

speed_trace = alt.SpeedTrace.from_csv_file(str(trace_file))
link_path   = alt.LinkPath.from_csv_file(str(lp_file))

# ── 3. Configure train consist ──────────────────────────────────────────────
print("\n[3/6] Configuring train consist...")

# Rail vehicle: loaded manifest car
rail_vehicle = alt.RailVehicle.from_file(
    alt.resources_root() / "rolling_stock/Manifest_Loaded.yaml"
)

train_config = alt.TrainConfig(
    rail_vehicles=[rail_vehicle],
    n_cars_by_type={"Manifest_Loaded": 100},
    train_length_meters=None,
    train_mass_kilograms=None,
)
print(f"  ✓ 100 loaded manifest cars")

# Locomotives: 4 robust 3.3 MW units
loco_unit = create_robust_loco.get_robust_loco()
loco_con  = alt.Consist([loco_unit] * 4, SAVE_INTERVAL)
print(f"  ✓ 4 × 3.3 MW locomotives")

# ── 4. Build simulation ─────────────────────────────────────────────────────
print("\n[4/6] Building SetSpeedTrainSim...")
tsb = alt.TrainSimBuilder(
    train_id="Henderson_Full_NB",
    train_config=train_config,
    loco_con=loco_con,
)

sim = tsb.make_set_speed_train_sim(
    network=network,
    link_path=link_path,
    speed_trace=speed_trace,
    save_interval=SAVE_INTERVAL,
)
print("  ✓ Simulation built")

# ── 5. Run simulation ───────────────────────────────────────────────────────
print("\n[5/6] Running simulation...")
t0 = time.perf_counter()
sim.walk()
t1 = time.perf_counter()
sim_time = t1 - t0
print(f"  ✓ Simulation completed in {sim_time:.1f} seconds")

# ── 6. Extract results ──────────────────────────────────────────────────────
print("\n[6/6] Extracting and saving results...")

sim_data = sim.to_pydict()
history  = sim_data.get('history', {})
df       = pd.DataFrame(history)

print(f"  Rows: {len(df)}")
print(f"  Columns: {sorted(df.columns.tolist())}")
print(f"  Distance range: {df['total_dist_meters'].min():.0f} – "
      f"{df['total_dist_meters'].max():.0f} m")
print(f"  Speed range: {df['speed_meters_per_second'].min()*2.237:.1f} – "
      f"{df['speed_meters_per_second'].max()*2.237:.1f} mph")

# ── Map simulation distance → Milepost ──────────────────────────────────────
# NB direction: MP increases with distance
# Distance in main track = total_dist - dummy_length
# Milepost = MP_MIN + (dist_in_main) / 1609.34
df['dist_in_main'] = df['total_dist_meters'] - DUMMY_LENGTH
df['milepost'] = MP_MIN + df['dist_in_main'] / 1609.34

# Save full results
output_csv = OUTPUT_DIR / "nb_simulation.csv"
df.to_csv(output_csv, index=False)
print(f"  ✓ Results saved to {output_csv} ({len(df)} rows)")

# ── Quick verification ───────────────────────────────────────────────────────
main_df = df[(df['total_dist_meters'] >= DUMMY_LENGTH) &
             (df['total_dist_meters'] <= DUMMY_LENGTH + MAIN_LENGTH)].copy()
print(f"\n  === MAIN CORRIDOR SUMMARY (MP {MP_MIN:.1f} – {MP_MAX:.1f}) ===")
print(f"  Timesteps in corridor: {len(main_df)}")
print(f"  Milepost range: {main_df['milepost'].min():.1f} – {main_df['milepost'].max():.1f}")
print(f"  Avg speed: {main_df['speed_meters_per_second'].mean()*2.237:.1f} mph")
print(f"  Max speed: {main_df['speed_meters_per_second'].max()*2.237:.1f} mph")

for col in ['res_grade_newtons', 'res_curve_newtons', 'res_rolling_newtons',
            'res_aero_newtons', 'res_bearing_newtons']:
    if col in main_df.columns:
        print(f"  {col}: mean={main_df[col].mean():.0f} N, max={main_df[col].max():.0f} N")

if 'pwr_whl_out_watts' in main_df.columns:
    print(f"  Wheel power: mean={main_df['pwr_whl_out_watts'].mean()/1e6:.2f} MW, "
          f"peak={main_df['pwr_whl_out_watts'].max()/1e6:.2f} MW")

print(f"\n  Simulation runtime: {sim_time:.1f} s")
print("✓ Done!")
