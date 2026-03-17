#!/usr/bin/env python3
"""
Exploratory Data Analysis (EDA) on the ALTRIOS simulation results.
Reads nb_simulation.csv and generates insightful statistical plots and summaries.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set plotting style
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    "font.family": "Arial",
    "figure.titlesize": 24,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 16
})

SIM_CSV = Path("results/henderson_sb_sim/sb_simulation.csv")
OUT_DIR = Path("results/henderson_sb_sim/EDA")
OUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Loading data from: {SIM_CSV}")
df = pd.read_csv(SIM_CSV)

# Basic cleaning/feature engineering
df['speed_mph'] = df['speed_meters_per_second'] * 2.23694
df['f_whl_kn'] = df['pwr_whl_out_watts'] / np.maximum(df['speed_meters_per_second'], 0.1) / 1000.0
df['grade_pct'] = df['grade_front'] * 100.0

# Remove dummy buffers to focus on main corridor (MP 176.9 to 317.5)
df_main = df[(df['milepost'] >= 176.9) & (df['milepost'] <= 317.5)].copy()
if len(df_main) == 0:
    df_main = df

print(f"\n--- BASIC STATISTICS ---")
print(f"Total timesteps: {len(df_main)}")
print(f"Milepost Range: {df_main['milepost'].min():.2f} to {df_main['milepost'].max():.2f}")
print(f"Average Speed: {df_main['speed_mph'].mean():.2f} mph")
print(f"Max Speed: {df_main['speed_mph'].max():.2f} mph")
print(f"Max Wheel Effort (Traction): {df_main['f_whl_kn'].max():.0f} kN")
print(f"Min Wheel Effort (Braking): {df_main['f_whl_kn'].min():.0f} kN")
print(f"Max Grade: {df_main['grade_pct'].max():.2f}%")
print(f"Min Grade: {df_main['grade_pct'].min():.2f}%")

# 1. Distibutions
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

sns.histplot(df_main['speed_mph'], bins=40, kde=True, ax=axes[0], color='orange')
axes[0].set_title('Speed Distribution (mph)')
axes[0].set_xlabel('Speed (mph)')

sns.histplot(df_main['f_whl_kn'], bins=40, kde=True, ax=axes[1], color='purple')
axes[1].set_title('Wheel Force Distribution (kN)\nPositive=Traction, Negative=Braking')
axes[1].set_xlabel('Wheel Force (kN)')

sns.histplot(df_main['grade_pct'], bins=40, kde=True, ax=axes[2], color='blue')
axes[2].set_title('Grade Distribution (%)')
axes[2].set_xlabel('Grade (%)')

plt.tight_layout()
dist_file = OUT_DIR / "distributions.png"
fig.savefig(dist_file, dpi=200)
print(f"Saved: {dist_file}")

# 2. Correlation Matrix
cols_of_interest = [
    'speed_mph', 'f_whl_kn', 'grade_pct', 'res_grade_newtons', 
    'res_curve_newtons', 'pwr_whl_out_watts'
]
corr = df_main[cols_of_interest].corr()

fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(corr, annot=True, cmap='coolwarm', vmin=-1, vmax=1, fmt=".2f", ax=ax,
            xticklabels=['Speed', 'Wheel Force', 'Grade %', 'Grade Res.', 'Curve Res.', 'Wheel Power'],
            yticklabels=['Speed', 'Wheel Force', 'Grade %', 'Grade Res.', 'Curve Res.', 'Wheel Power'])
ax.set_title('Correlation Matrix of Key Metrics')
plt.tight_layout()
corr_file = OUT_DIR / "correlation_matrix.png"
fig.savefig(corr_file, dpi=200)
print(f"Saved: {corr_file}")

# 3. Grade vs Speed Scatter
fig, ax = plt.subplots(figsize=(10, 6))
# Subsample for cleaner scatter if df is very large
df_sub = df_main.sample(n=min(5000, len(df_main)), random_state=42)
sns.scatterplot(data=df_sub, x='grade_pct', y='speed_mph', hue='f_whl_kn', palette='viridis', alpha=0.6, ax=ax)
ax.set_title('Speed vs Grade (Colored by Wheel Force)')
ax.set_xlabel('Grade (%)')
ax.set_ylabel('Speed (mph)')
ax.axvline(0, color='gray', linestyle='--', alpha=0.5)
plt.tight_layout()
scatter_file = OUT_DIR / "speed_vs_grade.png"
fig.savefig(scatter_file, dpi=200)
print(f"Saved: {scatter_file}")

# Generate text summary report
report_path = OUT_DIR / "eda_summary.txt"
with open(report_path, "w") as f:
    f.write(f"EDA Summary for ALTRIOS Simulation\n")
    f.write(f"==================================\n")
    f.write(f"Analyzed {len(df_main)} timesteps from MP {df_main['milepost'].min():.2f} to {df_main['milepost'].max():.2f}\n\n")
    
    f.write(f"Metrics Overview:\n")
    f.write(f"- Speed: Mean = {df_main['speed_mph'].mean():.1f} mph, Max = {df_main['speed_mph'].max():.1f} mph\n")
    f.write(f"- Grade: Range = {df_main['grade_pct'].min():.2f}% to {df_main['grade_pct'].max():.2f}%\n")
    f.write(f"- Wheel Force: Max Traction = {df_main['f_whl_kn'].max():.0f} kN, Max Braking = {df_main['f_whl_kn'].min():.0f} kN\n")
    
    f.write(f"\nTime Spent in Operations:\n")
    traction_pct = (df_main['f_whl_kn'] > 50).mean() * 100
    braking_pct = (df_main['f_whl_kn'] < -50).mean() * 100
    coast_pct = ((df_main['f_whl_kn'] >= -50) & (df_main['f_whl_kn'] <= 50)).mean() * 100
    
    f.write(f"- Power (Traction > 50kN): {traction_pct:.1f}%\n")
    f.write(f"- Braking (Demand < -50kN): {braking_pct:.1f}%\n")
    f.write(f"- Coasting (-50kN to 50kN): {coast_pct:.1f}%\n")

print(f"Saved EDA summary report to: {report_path}")
print("EDA Complete!")
