import pandas as pd
import numpy as np

# Load simulation results
df = pd.read_csv('results/henderson_altrios_simulation.csv')

# Conversions
N_to_lbs = 0.224809
Watts_to_kW = 0.001

# Calculate Power Metrics
# pwr_whl_out_watts is positive for traction, negative for braking (if regenerative)
avg_power_kw = df[df['history.pwr_whl_out_watts'] > 0]['history.pwr_whl_out_watts'].mean() * Watts_to_kW
peak_power_kw = df['history.pwr_whl_out_watts'].max() * Watts_to_kW

# Calculate Resistance Metrics (Average Force in lbs)
# Note: ALTRIOS resistance is often negative if opposing motion? Or positive magnitude?
# Usually resistance opposes motion. Let's check mean absolute values or raw means.
# Based on summary report, Grade Res > 0 (Uphill) dominated.
# Let's take the mean of the *magnitude* or just the mean if the sign convention is consistent.
# Resistance forces in ALTRIOS: Positive = Opposing motion (usually). Grade can be negative (downhill).
# BigQuery likely summed absolute resistance or net? 
# "Resistance Analysis (for 14,300-ton train): ... Average Total Resistance: 94,634 lbs"
# This implies a mean tractive effort required or sum of forces.
# Let's compute mean of the force columns (converted to lbs).

res_cols = {
    'Rolling': 'history.res_rolling_newtons',
    'Bearing': 'history.res_bearing_newtons',
    'Davis B': 'history.res_davis_b_newtons',
    'Aero': 'history.res_aero_newtons',
    'Grade': 'history.res_grade_newtons',
    'Curve': 'history.res_curve_newtons'
}

print("--- ALTRIOS vs BigQuery Comparison ---")
print(f"Average Traction Power (kW): {avg_power_kw:.2f}")
print(f"Peak Power (kW): {peak_power_kw:.2f}")

print("\n--- Resistance Breakdown (Average lbs) ---")
total_res_sum = 0
for name, col in res_cols.items():
    # Grade resistance can be negative (propulsive). BigQuery likely reported the "Resistance" (load) 
    # part, possibly segregating uphill vs downhill. 
    # "Grade resistance dominates at 32.5%". This suggests they looked at the magnitude 
    # or the positive component. 
    # Let's look at the mean of the column.
    mean_n = df[col].mean()
    mean_lbs = mean_n * N_to_lbs
    print(f"{name}: {mean_lbs:.0f} lbs")
    total_res_sum += mean_lbs

print(f"Total Sum of Means: {total_res_sum:.0f} lbs")

# Percentage Calculation based on Absolute Means (to catch magnitude of impact)
print("\n--- Resistance Magnitude (Impact) Comparison ---")
abs_sum = 0
breakdown = {}
for name, col in res_cols.items():
    val = df[col].abs().mean() * N_to_lbs
    breakdown[name] = val
    abs_sum += val

for name, val in breakdown.items():
    pct = (val / abs_sum) * 100
    print(f"{name}: {pct:.1f}%")
