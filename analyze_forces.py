import pandas as pd
import numpy as np

# Load simulation results
df = pd.read_csv('results/henderson_altrios_simulation.csv')

# Constants
N_to_lbs = 0.224809
MPS_to_MPH = 2.23694

print("="*80)
print("ALTRIOS Force Balance Analysis: Traction vs Resistance")
print("="*80)

# 1. Calculate Total Resistance Force (The "Load")
# Note: ALTRIOS resistance columns usually store the force opposing motion.
# Grade resistance can be negative (downhill pushing).
# We want the MAGNITUDE of resistance to overcome.
# Standard Equation: F_res_total = F_rolling + F_bearing + F_aero + F_grade + F_curve
# (Subtract Grade if it's helping? Or just sum them algebraically)
# Let's sum them algebraically. If Result > 0, it's resistance. If < 0, it's assistance (gravity).

df['F_res_total_N'] = (
    df['history.res_rolling_newtons'] +
    df['history.res_bearing_newtons'] +
    df['history.res_aero_newtons'] +
    df['history.res_grade_newtons'] + 
    df['history.res_curve_newtons']
)

# 2. Calculate Net Force (F_net = m * a)
# We need acceleration. a = dv / dt
df['v_mps'] = df['history.speed_meters_per_second']
df['dt'] = df['history.dt_seconds']
df['a_mps2'] = df['v_mps'].diff() / df['dt']
# Fill NaN for first row
df.loc[0, 'a_mps2'] = 0.0

# Mass is dynamic (fuel burn?) but mostly static for this short trip.
# Use the mass column if available.
# 'history.mass_freight_kilograms' + 'history.mass_static_kilograms' (Wait, check columns)
# Columns: 'history.mass_static_kilograms', 'history.mass_rot_kilograms', 'history.mass_freight_kilograms'
# Total inertial mass = mass_static + mass_rot (rotational inertia equivalent) + mass_freight?
# Or is mass_static including freight?
# Let's check the values.
# Usually: m_effective = m_static + m_freight + m_rot
df['m_total_kg'] = (
    df['history.mass_static_kilograms'] + 
    df['history.mass_rot_kilograms']
    # Note: mass_static usually includes the car body. mass_freight is the payload.
    # We should verify if mass_static includes payload or not. 
    # In earlier scripts we defined: mass_static + mass_freight.
)
# Let's assume Total Inertial Mass = Static + Rotational (Rotational captures the effective mass increase)
# Actually, let's look at the sums. 
# Step 892 output: mass_static ~1.37e7, mass_freight ~9.97e6. mass_static might be Total Static?
# Let's check the RailVehicle config in Step 577.
# mass_static_base_kilograms: 30000. mass_freight: 99727.
# Total Car Mass = 130k.
# 100 cars = 13M kg.
# Simulation 'history.mass_static_kilograms' is 1.37e7. This looks like Total Static (Cars + Loco).
# So F_net = (mass_static + mass_rot) * a.

df['F_net_N'] = (df['history.mass_static_kilograms'] + df['history.mass_rot_kilograms']) * df['a_mps2']

# 3. Derive Tractive Effort (F_tractive)
# Newton's 2nd Law: F_net = F_tractive - F_res_total (algebraic sum)
# F_tractive = F_net + F_res_total
# Note: F_res_total contains Grade.
# If Grade is + (Uphill), it fights traction. F_tract must overcome it.
# If Grade is - (Downhill), it helps. F_res is negative. F_tract can be smaller.
# This logic holds.

df['F_tractive_N'] = df['F_net_N'] + df['F_res_total_N']

# Clip negative tractive effort (this acts as Braking Force or Dynamic Braking)
df['F_tractive_or_brake_N'] = df['F_tractive_N']

# Convert to lbs for reporting
df['F_tract_lbs'] = df['F_tractive_N'] * N_to_lbs
df['F_res_lbs'] = df['F_res_total_N'] * N_to_lbs
df['Speed_mph'] = df['v_mps'] * MPS_to_MPH

# ============================================================
# ANALYSIS 1: EQUILIBRIUM CHECK (Force = Resistance?)
# ============================================================
# "when force = resistance, speed is constant"
# Let's check correlation between (F_tract - F_res) and Acceleration.
# It should be perfect (by definition of our derivation), but serves as validation.

# Identify States
# 1. Acceleration: F_tract > F_res
# 2. Deceleration: F_tract < F_res
# 3. Cruising: F_tract ~ F_res (within tolerance)

tolerance_N = 1000 # 1 kN tolerance
conditions = [
    (df['F_tractive_N'] > df['F_res_total_N'] + tolerance_N),
    (df['F_tractive_N'] < df['F_res_total_N'] - tolerance_N),
    (abs(df['F_tractive_N'] - df['F_res_total_N']) <= tolerance_N)
]
choices = ['Accelerating', 'Decelerating', 'Constant Speed']
df['State'] = np.select(conditions, choices, default='Unknown')

print("\n--- 1. NEWTON'S LAW VALIDATION ---")
state_counts = df['State'].value_counts()
print(state_counts)
print("\nValidation of Dynamics:")
print(f"Accelerating: {state_counts.get('Accelerating',0)}s (F_tract > Resistance)")
print(f"Constant Speed: {state_counts.get('Constant Speed',0)}s (F_tract ≈ Resistance)")
print(f"Decelerating: {state_counts.get('Decelerating',0)}s (F_tract < Resistance)")

# ============================================================
# ANALYSIS 2: HIGH EFFORT SEGMENTS
# ============================================================
print("\n--- 2. HIGH EFFORT ZONES (Top 10 Seconds) ---")
# High Effort = Max Tractive Force
top_effort = df.nlargest(10, 'F_tractive_N')

print(f"{'Time(s)':<8} {'Dist(m)':<10} {'Speed(mph)':<10} {'Tractive(lbs)':<15} {'Resist(lbs)':<15} {'Limit(lbs)':<15} {'Reason'}")
print("-" * 90)
for idx, row in top_effort.iterrows():
    # Identify primary resistance component
    res_comps = {
        'Grade': row['history.res_grade_newtons'],
        'Curve': row['history.res_curve_newtons'],
        'Aero': row['history.res_aero_newtons'],
        'Rolling': row['history.res_rolling_newtons']
    }
    main_cause = max(res_comps, key=res_comps.get)
    
    # Check if traction limited (Power limited?)
    # P = F*v. Max Power ~12MW.
    # Check if F is near F_max_loco (adhesion limit)
    # 4 locos * ~135,000 lbs starting TE? Or 180k lbs per loco.
    # Let's just report the numbers.
    
    print(f"{row['history.time_seconds']:<8.0f} {row['history.total_dist_meters']:<10.0f} {row['Speed_mph']:<10.1f} {row['F_tract_lbs']:<15,.0f} {row['F_res_lbs']:<15,.0f} {main_cause}")

# ============================================================
# ANALYSIS 3: FORCE vs RESISTANCE CORRELATION
# ============================================================
# Group by Milepost (approx every 1609 meters)
df['Mile'] = (df['history.total_dist_meters'] / 1609.34).astype(int)
mile_stats = df.groupby('Mile')[['F_tract_lbs', 'F_res_lbs', 'Speed_mph', 'history.grade_front']].mean()

print("\n--- 3. AVERAGE EFFORT BY MILE ---")
print(f"{'Mile':<5} {'Avg Tract(lbs)':<15} {'Avg Res(lbs)':<15} {'Avg Speed':<10} {'Avg Grade(%)'}")
print("-" * 75)
for mile, row in mile_stats.iterrows():
    grade_pct = row['history.grade_front'] * 100
    print(f"{mile:<5} {row['F_tract_lbs']:<15,.0f} {row['F_res_lbs']:<15,.0f} {row['Speed_mph']:<10.1f} {grade_pct:+.2f}%")

print("\n" + "="*80)
