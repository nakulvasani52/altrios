import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def analyze():
    nb_csv = "results/henderson_nb_simulation.csv"
    sb_csv = "results/henderson_sb_simulation.csv"
    
    if not os.path.exists(nb_csv) or not os.path.exists(sb_csv):
        print("Missing simulation results.")
        return

    df_nb = pd.read_csv(nb_csv)
    df_sb = pd.read_csv(sb_csv)

    # Filter for the "Main" part (Henderson corridor)
    # Buffers are 50km. Main length is ~17.7km.
    # NB Main: 50,000m to 67,703.4m
    # SB Main: 50,000m to 67,703.4m
    
    # We'll use a slightly tighter filter to avoid buffer ramp artifacts
    nb_main = df_nb[(df_nb['total_dist_meters'] >= 50000) & (df_nb['total_dist_meters'] <= 67703.4)].copy()
    sb_main = df_sb[(df_sb['total_dist_meters'] >= 50000) & (df_sb['total_dist_meters'] <= 67703.4)].copy()

    # Calculate Total Resistance (Newtons)
    nb_main['res_total'] = nb_main['res_grade_newtons'] + nb_main['res_curve_newtons'] + \
                         nb_main['res_rolling_newtons'] + nb_main['res_aero_newtons'] + \
                         nb_main['res_bearing_newtons']
    
    sb_main['res_total'] = sb_main['res_grade_newtons'] + sb_main['res_curve_newtons'] + \
                         sb_main['res_rolling_newtons'] + sb_main['res_aero_newtons'] + \
                         sb_main['res_bearing_newtons']

    # Calculate Tractive Effort (TE) in Newtons
    # For SetSpeedTrainSim, TE = Res_Total + m*a
    # We can also get it from pwr_whl_out / speed
    nb_main['te_newtons'] = np.where(nb_main['speed_meters_per_second'] > 0.1, 
                                     nb_main['pwr_whl_out_watts'] / nb_main['speed_meters_per_second'], 
                                     0.0)
    sb_main['te_newtons'] = np.where(sb_main['speed_meters_per_second'] > 0.1, 
                                     sb_main['pwr_whl_out_watts'] / sb_main['speed_meters_per_second'], 
                                     0.0)

    # Translate SB Distance to NB Relative Coordinate
    # 50,000m (SB) -> 67,703.4m (NB)
    # 67,703.4m (SB) -> 50,000m (NB)
    # x_nb_equiv = 117703.4 - x_sb
    sb_main['dist_nb_equiv'] = 117703.4 - sb_main['total_dist_meters']

    # Summary Statistics
    print("=== FORCE ANALYSIS: HENDERSON CORRIDOR (PASSENGER) ===")
    print(f"Northbound Mean Resistance: {nb_main['res_total'].mean():.2f} N")
    print(f"Southbound Mean Resistance: {sb_main['res_total'].mean():.2f} N")
    print(f"Northbound Max TE: {nb_main['te_newtons'].max():.2f} N")
    print(f"Southbound Max TE: {sb_main['te_newtons'].max():.2f} N")
    
    # Calculate Energy in kWh
    nb_energy = (nb_main['pwr_whl_out_watts'].sum() / 3600.0) / 1000.0
    sb_energy = (sb_main['pwr_whl_out_watts'].sum() / 3600.0) / 1000.0
    print(f"Northbound Wheel Energy: {nb_energy:.2f} kWh")
    print(f"Southbound Wheel Energy: {sb_energy:.2f} kWh")
    
    # Save a comparison CSV
    nb_summary = nb_main[['total_dist_meters', 'res_grade_newtons', 'res_curve_newtons', 'res_total', 'te_newtons']].rename(columns={'total_dist_meters': 'dist_nb'})
    sb_summary = sb_main[['dist_nb_equiv', 'res_grade_newtons', 'res_curve_newtons', 'res_total', 'te_newtons']].rename(columns={'dist_nb_equiv': 'dist_nb'})
    
    # Merge on distance (binned to 10m for clean comparison)
    nb_summary['dist_bin'] = (nb_summary['dist_nb'] // 10) * 10
    sb_summary['dist_bin'] = (sb_summary['dist_nb'] // 10) * 10
    
    nb_avg = nb_summary.groupby('dist_bin').mean().reset_index()
    sb_avg = sb_summary.groupby('dist_bin').mean().reset_index()
    
    combined = pd.merge(nb_avg, sb_avg, on='dist_bin', suffixes=('_nb', '_sb'))
    combined.to_csv("results/bidirectional_force_comparison.csv", index=False)
    print("Comparison saved to results/bidirectional_force_comparison.csv")

if __name__ == "__main__":
    analyze()
