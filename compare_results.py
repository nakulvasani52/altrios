import pandas as pd
import numpy as np

# Load simulation results
df = pd.read_csv('results/henderson_altrios_simulation.csv')

# Conversions
N_to_lbs = 0.224809
Watts_to_kW = 0.001
J_to_kWh = 1 / 3.6e6
J_to_MWh = 1 / 3.6e9
MPS_to_MPH = 2.23694

# ALTRIOS Diesel Constants (from altrios.defaults)
LHV_DIESEL_KJ_PER_KG = 42.6e3  # Lower Heating Value
RHO_DIESEL_KG_PER_M3 = 850     # Density
LITERS_PER_M3 = 1000
GALLONS_PER_LITER = 0.264172

print("=" * 60)
print("ALTRIOS Henderson Simulation: Extended Analysis")
print("=" * 60)

# ============================================================
# BASIC METRICS
# ============================================================
print("\n--- 1. BASIC METRICS ---")
total_time = df['history.time_seconds'].iloc[-1]
total_dist = df['history.total_dist_meters'].iloc[-1]
avg_speed = total_dist / total_time if total_time > 0 else 0
max_speed = df['history.speed_meters_per_second'].max()

print(f"Total Time: {total_time:.0f} seconds ({total_time/60:.1f} minutes)")
print(f"Total Distance: {total_dist/1000:.2f} km ({total_dist/1609.34:.2f} miles)")
print(f"Average Speed: {avg_speed * MPS_to_MPH:.1f} mph")
print(f"Max Speed: {max_speed * MPS_to_MPH:.1f} mph")

# ============================================================
# POWER METRICS
# ============================================================
print("\n--- 2. POWER METRICS ---")
avg_power_kw = df[df['history.pwr_whl_out_watts'] > 0]['history.pwr_whl_out_watts'].mean() * Watts_to_kW
peak_power_kw = df['history.pwr_whl_out_watts'].max() * Watts_to_kW
min_power_kw = df['history.pwr_whl_out_watts'].min() * Watts_to_kW  # Negative = regen

print(f"Average Traction Power: {avg_power_kw/1000:.2f} MW")
print(f"Peak Traction Power: {peak_power_kw/1000:.2f} MW")
print(f"Peak Regen/Braking Power: {abs(min_power_kw)/1000:.2f} MW")

# ============================================================
# ENERGY METRICS
# ============================================================
print("\n--- 3. ENERGY METRICS ---")
total_energy_pos = df['history.energy_whl_out_pos_joules'].iloc[-1]  # Energy consumed
total_energy_neg = df['history.energy_whl_out_neg_joules'].iloc[-1]  # Energy recovered (regen)
net_energy = df['history.energy_whl_out_joules'].iloc[-1]

print(f"Total Energy Consumed (Traction): {total_energy_pos * J_to_MWh:.3f} MWh")
print(f"Total Energy Recovered (Regen): {total_energy_neg * J_to_MWh:.3f} MWh")
print(f"Net Energy at Wheel: {net_energy * J_to_MWh:.3f} MWh")
print(f"Regen Recovery Rate: {(total_energy_neg / total_energy_pos * 100) if total_energy_pos > 0 else 0:.1f}%")

# ============================================================
# FUEL CONSUMPTION (Estimate for Diesel)
# ============================================================
print("\n--- 4. FUEL CONSUMPTION (Diesel Estimate) ---")
# Assume ~40% thermal efficiency for diesel locomotive
thermal_efficiency = 0.40
fuel_energy_joules = net_energy / thermal_efficiency
fuel_mass_kg = fuel_energy_joules / (LHV_DIESEL_KJ_PER_KG * 1000)  # J to kJ
fuel_volume_m3 = fuel_mass_kg / RHO_DIESEL_KG_PER_M3
fuel_liters = fuel_volume_m3 * LITERS_PER_M3
fuel_gallons = fuel_liters * GALLONS_PER_LITER

print(f"Estimated Fuel Used: {fuel_gallons:.1f} gallons ({fuel_liters:.1f} liters)")
print(f"Fuel Efficiency: {fuel_gallons / (total_dist/1609.34):.2f} gal/mile")
print(f"  (assuming {thermal_efficiency*100:.0f}% thermal efficiency)")

# ============================================================
# ELEVATION PROFILE
# ============================================================
print("\n--- 5. ELEVATION PROFILE ---")
elev_front_max = df['history.elev_front_meters'].max()
elev_front_min = df['history.elev_front_meters'].min()
elev_range = elev_front_max - elev_front_min
elev_start = df['history.elev_front_meters'].iloc[0]
elev_end = df['history.elev_front_meters'].iloc[-1]

print(f"Starting Elevation: {elev_start:.1f} m")
print(f"Ending Elevation: {elev_end:.1f} m")
print(f"Net Elevation Change: {elev_end - elev_start:.1f} m")
print(f"Max Elevation: {elev_front_max:.1f} m")
print(f"Min Elevation: {elev_front_min:.1f} m")
print(f"Total Elevation Range: {elev_range:.1f} m")

# ============================================================
# GRADE ANALYSIS
# ============================================================
print("\n--- 6. GRADE ANALYSIS ---")
grade_front = df['history.grade_front'] * 100  # Convert to %
grade_max = grade_front.max()
grade_min = grade_front.min()
grade_avg = grade_front.abs().mean()

print(f"Average Absolute Grade: {grade_avg:.2f}%")
print(f"Steepest Uphill: +{grade_max:.2f}%")
print(f"Steepest Downhill: {grade_min:.2f}%")

# Time spent on grades
time_uphill = len(df[grade_front > 0.1]) / len(df) * 100
time_downhill = len(df[grade_front < -0.1]) / len(df) * 100
time_flat = 100 - time_uphill - time_downhill

print(f"Time Uphill (>0.1%): {time_uphill:.1f}%")
print(f"Time Downhill (<-0.1%): {time_downhill:.1f}%")
print(f"Time Flat: {time_flat:.1f}%")

# ============================================================
# RESISTANCE BREAKDOWN
# ============================================================
print("\n--- 7. RESISTANCE BREAKDOWN ---")
res_cols = {
    'Rolling': 'history.res_rolling_newtons',
    'Bearing': 'history.res_bearing_newtons',
    'Davis B': 'history.res_davis_b_newtons',
    'Aero': 'history.res_aero_newtons',
    'Grade': 'history.res_grade_newtons',
    'Curve': 'history.res_curve_newtons'
}

total_res = 0
breakdown = {}
for name, col in res_cols.items():
    val = df[col].abs().mean() * N_to_lbs
    breakdown[name] = val
    total_res += val

print(f"{'Component':<12} {'Avg (lbs)':<12} {'% of Total':<10}")
print("-" * 35)
for name, val in sorted(breakdown.items(), key=lambda x: -x[1]):
    pct = (val / total_res) * 100 if total_res > 0 else 0
    print(f"{name:<12} {val:>10,.0f} {pct:>9.1f}%")
print("-" * 35)
print(f"{'TOTAL':<12} {total_res:>10,.0f}")

print("\n" + "=" * 60)
print("Analysis Complete")
print("=" * 60)
