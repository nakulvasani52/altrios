import pandas as pd
import matplotlib.pyplot as plt
import os

def plot_forces():
    comparison_csv = "results/bidirectional_force_comparison.csv"
    if not os.path.exists(comparison_csv):
        return

    df = pd.read_csv(comparison_csv)
    # Convert distance to km for easier reading
    df['dist_km'] = (df['dist_bin'] - 50000) / 1000.0

    plt.figure(figsize=(10, 6))
    plt.plot(df['dist_km'], df['res_total_nb'] / 1000.0, label='NB Resistance (kN)', color='blue', alpha=0.7)
    plt.plot(df['dist_km'], df['res_total_sb'] / 1000.0, label='SB Resistance (kN)', color='red', alpha=0.7)
    
    plt.title('Henderson Corridor: Bidirectional Resistance (Passenger Train)')
    plt.xlabel('Distance from Henderson Start (km)')
    plt.ylabel('Force (kN)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plot_path = "results/force_comparison_plot.png"
    plt.savefig(plot_path)
    print(f"Plot saved to {plot_path}")

if __name__ == "__main__":
    plot_forces()
