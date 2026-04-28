import re

with open('plot_synthetic_all.py', 'r') as f:
    content = f.read()

new_plot_braking = """def plot_braking(direction):
    print(f"Generating Premium Braking Split for {direction}...")
    _, df = load_and_bin(NB_CSV if direction == "NB" else SB_CSV)
    df = df[(df['milepost'] >= MP_MIN) & (df['milepost'] <= MP_MAX)].copy()
    
    accel = gaussian_filter1d(df['speed_meters_per_second'].diff().fillna(0).values / df['dt_seconds'].values, sigma=4)
    f_total_res = (df['res_grade_newtons'] + df['res_curve_newtons']).values
    f_dyn = np.abs(df['pwr_whl_out_watts'].values) / np.maximum(df['speed_meters_per_second'].values, 0.5)
    f_air = np.maximum(0, -(df['mass_static_kilograms'].values * accel + f_total_res + f_dyn))
    
    dyn_kn = f_dyn / 1000.0
    air_kn = f_air / 1000.0
    
    # EXTREME FILTER: Drop any points > 1500 kN to prevent plotting anomalies
    valid = (dyn_kn + air_kn) <= 1500
    mp = df['milepost'].values[valid]
    dyn_kn = dyn_kn[valid]
    air_kn = air_kn[valid]
    
    fig, ax = plt.subplots(figsize=(20, 7))
    ax.stackplot(mp, dyn_kn, air_kn, labels=['Dynamic Braking', 'Air Braking'], 
                 colors=[COLORS[0], COLORS[1]], alpha=0.5, edgecolor='gray', linewidth=0.5)
    ax.set_title(f"Synthetic Optimal {direction}: Braking Force Distribution (Premium)", fontsize=FS_TITLE, fontweight='bold', pad=15)
    ax.set_ylabel("Braking Force (kN)", fontsize=FS_LABEL, fontweight='bold')
    ax.set_xlabel("Milepost", fontsize=FS_LABEL, fontweight='bold')
    ax.legend(loc='upper right', fontsize=16, frameon=True, facecolor='white', framealpha=0.9)
    ax.set_xlim(MP_MIN, MP_MAX)
    ax.set_ylim(0, 1500)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    fig.savefig(OUT_DIR / f"Synthetic_{direction}_Braking_Breakdown.png")
    plt.close()

def get_braking_data(csv):
    d = pd.read_csv(csv)
    d = d[(d['milepost'] >= MP_MIN) & (d['milepost'] <= MP_MAX)].copy()
    accel = gaussian_filter1d(d['speed_meters_per_second'].diff().fillna(0).values / d['dt_seconds'].values, sigma=4)
    f_res = (d['res_grade_newtons'] + d['res_curve_newtons']).values
    f_dyn = np.abs(d['pwr_whl_out_watts'].values) / np.maximum(d['speed_meters_per_second'].values, 0.5)
    f_air = np.maximum(0, -(d['mass_static_kilograms'].values * accel + f_res + f_dyn))
    
    dyn_kn = f_dyn / 1000.0
    air_kn = f_air / 1000.0
    
    # EXTREME FILTER
    valid = (dyn_kn + air_kn) <= 1500
    return d['milepost'].values[valid], dyn_kn[valid], air_kn[valid]

def plot_braking_composite():
    print("Generating Composite Braking vs. Demand Stack...")
    nb_mp, nb_dyn, nb_air = get_braking_data(NB_CSV)
    sb_mp, sb_dyn, sb_air = get_braking_data(SB_CSV)
    
    LO_L, CA_L = (23.0*4)/1609.34, (18.0*100)/1609.34
    BIN_S = 10.0/5280.0
    BC = np.arange(MP_MIN, MP_MAX + BIN_S, BIN_S); BC = BC[:-1] + BIN_S/2.0
    
    def get_p(csv, is_sb=False):
        d = pd.read_csv(csv); d = d[(d['milepost'] >= MP_MIN) & (d['milepost'] <= MP_MAX)].copy()
        fl = np.abs(d['pwr_whl_out_watts'].values) / np.maximum(d['speed_meters_per_second'].values, 0.5) / 1000.0
        acc = gaussian_filter1d(d['speed_meters_per_second'].diff().fillna(0).values / d['dt_seconds'].values, sigma=2)
        fa = np.maximum(0, -(d['mass_static_kilograms'].values*acc/1000.0 + (d['res_grade_newtons']+d['res_curve_newtons']).values/1000.0 + fl))
        
        valid = (fl + fa) <= 1500
        fl = np.where(valid, fl, 0)
        fa = np.where(valid, fa, 0)
        
        pl, pa = np.zeros(len(BC)), np.zeros(len(BC))
        mps = d['milepost'].values
        for i in range(len(d)):
            mp = mps[i]; flb, fab = (fl[i]/LO_L)*BIN_S, (fa[i]/CA_L)*BIN_S
            if is_sb: ls, le, cs, ce = mp, mp + LO_L, mp + LO_L, mp + LO_L + CA_L
            else: ls, le, cs, ce = mp - LO_L, mp, mp - LO_L - CA_L, mp - LO_L
            li = np.where((BC >= ls) & (BC <= le))[0]; ci = np.where((BC >= cs) & (BC <= ce))[0]
            if len(li)>0: pl[li] = np.maximum(pl[li], flb)
            if len(ci)>0: pa[ci] = np.maximum(pa[ci], fab)
        return pl, pa

    ln, an = get_p(NB_CSV, False); ls, as_ = get_p(SB_CSV, True)
    
    total_l = gaussian_filter1d(np.maximum(ln, ls), sigma=5)
    total_a = gaussian_filter1d(np.maximum(an, as_), sigma=5)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(18, 15), sharex=True)
    
    ax1.stackplot(nb_mp, nb_dyn, nb_air, colors=[COLORS[0], COLORS[1]], alpha=0.5, labels=['Dyn', 'Air'])
    ax1.set_title("Northbound Braking Effort Split", fontsize=18, fontweight='bold')
    ax1.set_ylabel("Force (kN)", fontweight='bold'); ax1.legend(loc='upper right')
    ax1.set_ylim(0, 1500)
    
    ax2.stackplot(sb_mp, sb_dyn, sb_air, colors=[COLORS[0], COLORS[1]], alpha=0.5, labels=['Dyn', 'Air'])
    ax2.set_title("Southbound Braking Effort Split", fontsize=18, fontweight='bold')
    ax2.set_ylabel("Force (kN)", fontweight='bold'); ax2.legend(loc='upper right')
    ax2.set_ylim(0, 1500)
    
    ax3.fill_between(BC, 0, total_a, color=COLORS[1], alpha=0.35, label="Freight Consist (Air)")
    ax3.fill_between( BC, 0, total_l, color=COLORS[0], alpha=0.45, label="Loco Block (Dyn)")
    ax3.set_title("Resulting Spatial Track Demand (kN per 10ft Segment)", fontsize=18, fontweight='bold')
    ax3.set_ylabel("Demand (kN)", fontweight='bold'); ax3.set_xlabel("Milepost", fontweight='bold'); ax3.legend(loc='upper right')
    
    ax1.set_xlim(MP_MIN, MP_MAX)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "Synthetic_Composite_Braking_vs_Demand_10ft.png")
    plt.close()
"""

# RegEx replace from "def plot_braking" down to right before "def plot_force_demand_10ft"
pattern = re.compile(r'def plot_braking\(direction\):.*?def plot_force_demand_10ft\(\):', re.DOTALL)
new_content = pattern.sub(new_plot_braking + '\n\n# ── SPATIAL FORCE (10ft Peak Envelope) ───────────────────────────────────────\ndef plot_force_demand_10ft():', content)

with open('plot_synthetic_all.py', 'w') as f:
    f.write(new_content)
