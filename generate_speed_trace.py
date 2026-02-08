import pandas as pd
import numpy as np
import altrios as alt

def get_speed_trace(direction="NB"):
    """
    Generates a time-based SpeedTrace for ALTRIOS.
    Oscillates speed to force braking demo across the entire route.
    """
    df = pd.read_csv("data/henderson_segments.csv")
    df = df.sort_values('beg_mp').reset_index(drop=True)
    
    if direction == "SB":
        df = df.iloc[::-1].reset_index(drop=True)
    
    v_start = df.loc[0, 'speed'] * 0.44704
    a_limit = 0.05
    dummy_length = 50000.0
    dx = 1.0 
    
    dist_ramp = []
    v_ramp = []
    curr_x = 0.0
    while curr_x < dummy_length:
        v = min(np.sqrt(2 * a_limit * curr_x + 0.1), v_start)
        dist_ramp.append(curr_x)
        v_ramp.append(v)
        curr_x += dx
        
    dist_main = []
    v_main = []
    curr_x_abs = dummy_length
    
    for i, row in df.iterrows():
        # OSCILLATING SPEED LOGIC:
        # Every 3 miles (~4800m), drop speed to 20mph, then back to track speed.
        # This forces the train to brake repeatedly "along the entire stretch"
        cycle_pos = (curr_x_abs - dummy_length) % 6000.0 # 6km cycle
        if cycle_pos < 2000.0:
            target_v = 20.0 * 0.44704 # 20 mph slow zone
        else:
            target_v = row['speed'] * 0.44704
            
        L = row['length_m']
        steps = int(L / dx) + 1
        for s in range(steps):
            dist_main.append(curr_x_abs + s * (L/steps))
            v_main.append(target_v)
        curr_x_abs += L
        
    v_end = df.iloc[-1]['speed'] * 0.44704
    dist_end = []
    v_end_buffer = []
    for s in range(10000):
        dist_end.append(curr_x_abs + float(s))
        v_end_buffer.append(v_end)
        
    all_dist = np.array(dist_ramp + dist_main + dist_end)
    all_v = np.array(v_ramp + v_main + v_end_buffer)
    
    max_track_len = dummy_length + df['length_m'].sum() + dummy_length
    valid_mask = all_dist < (max_track_len - 100.0)
    all_dist = all_dist[valid_mask]
    all_v = all_v[valid_mask]
    
    all_v = np.maximum(all_v, 0.1)
    d_dist = np.diff(all_dist)
    v_mid = (all_v[:-1] + all_v[1:]) / 2.0
    dt = d_dist / v_mid
    all_time = np.concatenate(([0.0], np.cumsum(dt)))
    
    time_target = np.arange(0, all_time[-1], 1.0)
    v_interp = np.interp(time_target, all_time, all_v)
    
    trace_df = pd.DataFrame({
        'time_seconds': time_target,
        'speed_meters_per_second': v_interp
    })
    
    trace_file = f"data/speed_trace_{direction.lower()}.csv"
    trace_df.to_csv(trace_file, index=False)
    
    link_path_file = f"data/link_path_{direction.lower()}.csv"
    lp_df = pd.DataFrame({'link_idx': [1 if direction=="NB" else 2]})
    lp_df.to_csv(link_path_file, index=False)
    
    return alt.SpeedTrace.from_csv_file(trace_file), alt.LinkPath.from_csv_file(link_path_file)

if __name__ == "__main__":
    get_speed_trace("NB")
    get_speed_trace("SB")
