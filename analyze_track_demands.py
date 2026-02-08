import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def analyze_and_plot():
    nb_csv = "results/henderson_nb_simulation.csv"
    sb_csv = "results/henderson_sb_simulation.csv"
    
    if not os.path.exists(nb_csv) or not os.path.exists(sb_csv):
        print("Missing simulation results.")
        return

    df_nb = pd.read_csv(nb_csv)
    df_sb = pd.read_csv(sb_csv)

    # Filter for the Henderson Corridor (MP 242 - 253)
    # Start offset is 50km
    nb_main = df_nb[(df_nb['total_dist_meters'] >= 50000) & (df_nb['total_dist_meters'] <= 67703.4)].copy()
    sb_main = df_sb[(df_sb['total_dist_meters'] >= 50000) & (df_sb['total_dist_meters'] <= 67703.4)].copy()

    # Constants
    MPS_TO_MPH = 2.23694
    M_TO_MILE = 1/1609.34
    NB_START_MP = 242.0
    SB_START_MP = 252.99
    
    # Mapping to Milepost
    nb_main['mp'] = NB_START_MP + (nb_main['total_dist_meters'] - 50000) * M_TO_MILE
    sb_main['mp'] = SB_START_MP - (sb_main['total_dist_meters'] - 50000) * M_TO_MILE

    # Calculate Force Components (kN)
    def calc_forces(df):
        # Tractive effort and Dynamic Braking
        df['f_whl_kn'] = df['pwr_whl_out_watts'] / np.maximum(df['speed_meters_per_second'], 0.1) / 1000.0
        # Friction braking
        df['f_fric_kn'] = df.get('fric_brake_force_newtons', 0.0) / 1000.0
        # Resistance components
        df['f_grade_kn'] = df['res_grade_newtons'] / 1000.0
        df['f_curve_kn'] = df['res_curve_newtons'] / 1000.0
        df['f_roll_kn'] = df['res_rolling_newtons'] / 1000.0
        df['f_aero_kn'] = df['res_aero_newtons'] / 1000.0
        
        # Net Longitudinal Force on TRACK (FORWARD FORCE)
        # Traction pushes rail BACK (Negative if we define forward as positive)
        # Braking pushes rail FORWARD (Positive)
        # Resistance (Rolling/Curve) push rail FORWARD as train fights it (Positive)
        # Define: Forward Force on Rail (FFOR)
        # F_whl: + is traction (pushing rail back), - is dynamic braking (pushing rail forward)
        df['track_long_kn'] = -df['f_whl_kn'] + df['f_fric_kn'] + df['f_roll_kn'] + df['f_curve_kn']
        return df

    nb_main = calc_forces(nb_main)
    sb_main = calc_forces(sb_main)

    # Style Configuration
    plt.style.use('bmh')
    
    # Identify Hotspots (Threshold: |Force| > 300 kN or specific risk areas)
    def identify_hotspots(df):
        peaks = df[np.abs(df['track_long_kn']) > 320].copy()
        # Group by MP to avoid individual points
        peaks['mp_group'] = (peaks['mp'] * 10).astype(int) / 10
        hotspots = peaks.groupby('mp_group').agg({'track_long_kn': 'mean', 'grade_front': 'mean', 'f_curve_kn': 'mean'}).reset_index()
        return hotspots

    nb_hotspots = identify_hotspots(nb_main)
    sb_hotspots = identify_hotspots(sb_main)

    # 5-Panel Stack Plot (Premium Styling)
    def create_stacked_plot(df, title, filename, hotspots):
        fig, axes = plt.subplots(5, 1, figsize=(14, 20), sharex=True)
        plt.subplots_adjust(hspace=0.15)
        
        mps = df['mp']
        
        # Hazard Overlay Helper
        def add_hazards(ax, y_vals, threshold=300):
            mask = np.abs(y_vals) > threshold
            ax.fill_between(mps, ax.get_ylim()[0], ax.get_ylim()[1], where=mask, color='salmon', alpha=0.3, label='High Stress Zone')

        # Panel 1: Elevation & Profile
        ax1 = axes[0]
        ax1.fill_between(mps, df['elev_front_meters'], color='saddlebrown', alpha=0.3)
        ax1.plot(mps, df['elev_front_meters'], color='saddlebrown', lw=3, label='Elevation Profile')
        ax1.set_ylabel('Elevation (m)', fontweight='bold')
        ax1.set_title(title, fontsize=16, fontweight='bold', pad=20)
        
        ax_g = ax1.twinx()
        ax_g.plot(mps, df['grade_front'], color='darkorange', lw=1.5, alpha=0.7, label='Grade (%)')
        ax_g.set_ylabel('Grade (%)', color='darkorange', fontweight='bold')
        ax_g.grid(False)

        # Panel 2: Speed Adherence
        axes[1].plot(mps, df['speed_limit_meters_per_second'] * MPS_TO_MPH, color='black', alpha=0.3, lw=4, label='Civil Speed Limit')
        axes[1].plot(mps, df['speed_meters_per_second'] * MPS_TO_MPH, color='navy', lw=2, label='Actual Speed (mph)')
        axes[1].set_ylabel('Speed (mph)', fontweight='bold')
        axes[1].legend(loc='lower right')

        # Panel 3: Wheel Output (Traction vs DB)
        ax3 = axes[2]
        ax3.plot(mps, df['f_whl_kn'], color='seagreen', lw=2, label='Wheel Force (kN)')
        ax3.fill_between(mps, df['f_whl_kn'], 0, where=df['f_whl_kn']>0, color='green', alpha=0.2, label='Traction')
        ax3.fill_between(mps, df['f_whl_kn'], 0, where=df['f_whl_kn']<0, color='blue', alpha=0.2, label='Dynamic Brake')
        ax3.set_ylabel('Wheel Force (kN)', fontweight='bold')
        ax3.axhline(0, color='black', lw=1)
        ax3.legend(loc='upper right')

        # Panel 4: Force Components Breakdown
        axes[3].stackplot(mps, df['f_grade_kn'], df['f_curve_kn'], df['f_roll_kn'], df['f_aero_kn'], 
                         labels=['Grade', 'Curve', 'Rolling', 'Aero'], alpha=0.6)
        axes[3].set_ylabel('Force Components (kN)', fontweight='bold')
        axes[3].legend(loc='upper left')

        # Panel 5: Net Longitudinal Track Demand (The "Hazard" View)
        axes[4].plot(mps, df['track_long_kn'], color='crimson', lw=2.5, label='Net Longitudinal Rail stress')
        axes[4].fill_between(mps, df['track_long_kn'], 0, color='crimson', alpha=0.1)
        
        # Highlight Extreme Stress Zones
        threshold = 320
        axes[4].axhline(threshold, color='darkred', linestyle='--', alpha=0.5, label='Stress Threshold (320kN)')
        axes[4].axhline(-threshold, color='darkred', linestyle='--', alpha=0.5)
        
        y_min, y_max = axes[4].get_ylim()
        axes[4].fill_between(mps, y_min, y_max, where=np.abs(df['track_long_kn']) > threshold, 
                             color='red', alpha=0.15, label='CRITICAL HAZARD')

        axes[4].set_ylabel('Rail Stress (kN)\n(+ Forward)', fontweight='bold')
        axes[4].set_xlabel('Milepost', fontweight='bold', fontsize=12)
        axes[4].legend(loc='upper right')

        plt.savefig(filename, bbox_inches='tight')
        print(f"Saved Improved Viz: {filename}")

    create_stacked_plot(nb_main, "HENDERSON CORRIDOR: NORTHBOUND TRACK DEMAND ANALYSIS", "results/track_demand_nb_stacked.png", nb_hotspots)
    create_stacked_plot(sb_main, "HENDERSON CORRIDOR: SOUTHBOUND TRACK DEMAND ANALYSIS", "results/track_demand_sb_stacked.png", sb_hotspots)

    # Hotspot Export for Report
    nb_hotspots['direction'] = 'NB'
    sb_hotspots['direction'] = 'SB'
    pd.concat([nb_hotspots, sb_hotspots]).to_csv("results/track_demand_hotspots.csv", index=False)

if __name__ == "__main__":
    analyze_and_plot()
