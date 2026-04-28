import matplotlib; matplotlib.use("Agg")
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path
from scipy.ndimage import gaussian_filter1d

# ── CONFIG ───────────────────────────────────────────────────────────────────
COLORS = ["#FF0000", "#0000FF", "#FF9900", "#24E780", "#00FFFF", "#FF00FF", "#993366", "#969696"]
NB_CSV = Path("results/synthetic_sim/nb_simulation.csv")
SB_CSV = Path("results/synthetic_sim/sb_simulation.csv")
SEG_CSV = Path("data/nvasani2_altrios_segments_henderson_synthetic_top10.csv")
META_FILE = Path("data/henderson_synthetic_meta.json")
OUT_DIR = Path("/Users/nakulvasani/Desktop/Indp Study/08_Synthetic_Optimal_Run/Graphs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Henderson standard MP range
MP_MIN, MP_MAX = 176.0, 321.0

plt.rcParams.update({
    "savefig.dpi": 300, "font.family": "Arial", "axes.grid": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})
FS_TITLE, FS_LABEL, FS_TICK = 20, 16, 14

def load_and_bin(csv_path):
    df = pd.read_csv(csv_path)
    df['speed_mph'] = df['speed_meters_per_second'] * 2.23694
    df['f_whl_kn'] = df['pwr_whl_out_watts'] / np.maximum(df['speed_meters_per_second'], 0.1) / 1000.0
    df['f_res_grade_kn'] = df['res_grade_newtons'] / 1000.0
    df['f_res_curve_kn'] = df['res_curve_newtons'] / 1000.0
    df['f_res_total_kn'] = (df['res_grade_newtons'] + df['res_curve_newtons'] + df['res_rolling_newtons'] + df['res_aero_newtons'] + df['res_bearing_newtons']) / 1000.0
    df['track_long_kn'] = -df['f_whl_kn'] + df['f_res_total_kn']
    df['mp_group'] = (df['milepost'] * 2).round() / 2.0
    agg = df.groupby('mp_group').mean(numeric_only=True).reset_index()
    return agg, df

def load_geo():
    df = pd.read_csv(SEG_CSV)
    df = df[df['TrackNumber'] == 'SG'].copy()
    df['mp_group'] = ((df['beg_mp'] + df['end_mp'])/2.0 * 2).round() / 2.0
    geo = df.groupby(['mp_group', 'MP_ASC_DEC']).agg({'curvature_deg': lambda x: np.mean(np.abs(x)), 'grade_to_next': 'mean'}).reset_index()
    return geo

# ── STRIP CHARTS ─────────────────────────────────────────────────────────────
def plot_strip(direction):
    print(f"Generating Strip Chart for {direction}...")
    sim_agg, _ = load_and_bin(NB_CSV if direction == "NB" else SB_CSV)
    geo_all = load_geo()
    geo = geo_all[geo_all['MP_ASC_DEC'] == ('A' if direction == "NB" else 'D')]
    merged = sim_agg.merge(geo, on='mp_group', how='left').fillna(0).sort_values('mp_group')
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(20, 14), sharex=True)
    ax1.plot(merged['mp_group'], merged['curvature_deg'], color=COLORS[0]); ax1.set_ylabel("Curvature", color=COLORS[0], fontweight='bold')
    ax1b = ax1.twinx(); ax1b.step(merged['mp_group'], merged['grade_to_next'], color=COLORS[1], where='mid'); ax1b.set_ylabel("Grade (%)", color=COLORS[1], fontweight='bold')
    ax1.set_title(f"Synthetic Optimal {direction}: Strip Analysis", fontsize=FS_TITLE, fontweight='bold')
    ax2.fill_between(merged['mp_group'], merged['speed_mph'], color=COLORS[2], alpha=0.3); ax2.plot(merged['mp_group'], merged['speed_mph'], color=COLORS[2]); ax2.set_ylabel("Speed (mph)", fontweight='bold')
    ax3.plot(merged['mp_group'], merged['f_res_grade_kn'], color=COLORS[3], label="Grade"); ax3.plot(merged['mp_group'], merged['f_res_curve_kn'], color=COLORS[4], label="Curve"); ax3.set_ylabel("Force (kN)", fontweight='bold'); ax3.set_ylim(-2000, 3000)
    ax4.plot(merged['mp_group'], merged['track_long_kn'], color=COLORS[6]); ax4.axhline(0, color='gray', alpha=0.3, ls='--'); ax4.set_ylabel("Demand (kN)", fontweight='bold'); ax4.set_xlabel("Milepost", fontweight='bold'); ax4.set_ylim(-2500, 2500)
    ax4.set_xlim(MP_MIN, MP_MAX)
    plt.tight_layout(); fig.savefig(OUT_DIR / f"Synthetic_{direction}_4Panel_Strip.png"); plt.close()

# ── EDA: DISTRIBUTIONS ───────────────────────────────────────────────────────
def plot_eda(direction):
    print(f"Generating EDA for {direction}...")
    _, df = load_and_bin(NB_CSV if direction == "NB" else SB_CSV)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    sns.histplot(df['track_long_kn'], bins=100, color=COLORS[6], ax=ax1, kde=True); ax1.set_title("Longitudinal Demand Distribution", fontweight='bold')
    # Heatmap Wheel vs Resistance
    corr = df[['pwr_whl_out_watts', 'res_grade_newtons', 'speed_meters_per_second', 'res_curve_newtons']].corr()
    sns.heatmap(corr, annot=True, cmap="coolwarm", ax=ax2); ax2.set_title("Feature Correlation", fontweight='bold')
    plt.tight_layout(); fig.savefig(OUT_DIR / f"Synthetic_{direction}_EDA.png"); plt.close()

# ── BRAKING SPLIT ─────────────────────────────────────────────────────────────
def plot_braking(direction):
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
    valid = (dyn_kn + air_kn) <= 2200
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
    ax.set_ylim(0, 2000)
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
    valid = (dyn_kn + air_kn) <= 2200
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
        
        valid = (fl + fa) <= 2200
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
    ax1.set_ylim(0, 2000)
    
    ax2.stackplot(sb_mp, sb_dyn, sb_air, colors=[COLORS[0], COLORS[1]], alpha=0.5, labels=['Dyn', 'Air'])
    ax2.set_title("Southbound Braking Effort Split", fontsize=18, fontweight='bold')
    ax2.set_ylabel("Force (kN)", fontweight='bold'); ax2.legend(loc='upper right')
    ax2.set_ylim(0, 2000)
    
    ax3.fill_between(BC, 0, total_a, color=COLORS[1], alpha=0.35, label="Freight Consist (Air)")
    ax3.fill_between( BC, 0, total_l, color=COLORS[0], alpha=0.45, label="Loco Block (Dyn)")
    ax3.set_title("Resulting Spatial Track Demand (kN per 10ft Segment)", fontsize=18, fontweight='bold')
    ax3.set_ylabel("Demand (kN)", fontweight='bold'); ax3.set_xlabel("Milepost", fontweight='bold'); ax3.legend(loc='upper right')
    
    ax1.set_xlim(MP_MIN, MP_MAX)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "Synthetic_Composite_Braking_vs_Demand_10ft.png")
    plt.close()


# ── SPATIAL FORCE (10ft Peak Envelope) ───────────────────────────────────────
def plot_force_demand_10ft():
    print("Generating 10ft Peak Force Demand...")
    LO_L, CA_L = (23.0*4)/1609.34, (18.0*100)/1609.34
    BIN_S = 10.0/5280.0
    BC = np.arange(MP_MIN, MP_MAX + BIN_S, BIN_S); BC = BC[:-1] + BIN_S/2.0
    def get_p(csv, is_sb=False):
        d = pd.read_csv(csv); d = d[(d['milepost'] >= MP_MIN) & (d['milepost'] <= MP_MAX)].copy()
        fl = np.abs(d['pwr_whl_out_watts'].values) / np.maximum(d['speed_meters_per_second'].values, 0.5) / 1000.0
        acc = gaussian_filter1d(d['speed_meters_per_second'].diff().fillna(0).values / d['dt_seconds'].values, sigma=2)
        fa = np.maximum(0, -(d['mass_static_kilograms'].values*acc/1000.0 + (d['res_grade_newtons']+d['res_curve_newtons']).values/1000.0 + fl))
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
    total_l, total_a = gaussian_filter1d(np.maximum(ln, ls), sigma=5), gaussian_filter1d(np.maximum(an, as_), sigma=5)
    fig, ax = plt.subplots(figsize=(22, 10))
    ax.fill_between(BC, 0, total_a, color=COLORS[1], alpha=0.35, label="Air Brake Peak")
    ax.fill_between(BC, 0, total_l, color=COLORS[0], alpha=0.45, label="Loco Force Peak")
    ax.set_title("Synthetic Optimal: Peak Spatial Force Demand (10ft)", fontsize=22, fontweight='bold')
    ax.set_xlabel("Milepost"); ax.set_ylabel("Force (kN)"); ax.legend(); ax.set_xlim(MP_MIN, MP_MAX)
    plt.tight_layout(); fig.savefig(OUT_DIR / "Synthetic_Spatial_Force_Demand_10ft.png"); plt.close()

# ── CUMULATIVE ───────────────────────────────────────────────────────────────
def plot_cumulative():
    print("Generating Cumulative NB+SB Demand...")
    n_agg, _ = load_and_bin(NB_CSV); s_agg, _ = load_and_bin(SB_CSV)
    c = n_agg.merge(s_agg, on='mp_group', suffixes=('_nb','_sb'), how='outer').fillna(0)
    c['total'] = c['track_long_kn_nb'] + c['track_long_kn_sb']
    fig, ax = plt.subplots(figsize=(20, 6))
    ax.plot(c['mp_group'], c['total'], color=COLORS[6], linewidth=1.8); ax.axhline(0, color='gray', alpha=0.3, ls='--')
    ax.set_title("Synthetic Optimal: Cumulative Track Demand (NB+SB)", fontweight='bold')
    ax.set_ylabel("Demand (kN)", fontweight='bold', fontsize=FS_LABEL)
    ax.set_xlabel("Milepost", fontweight='bold', fontsize=FS_LABEL)
    ax.set_xlim(MP_MIN, MP_MAX)
    ax.set_ylim(-2500, 2500)
    plt.tight_layout(); fig.savefig(OUT_DIR / "Synthetic_Cumulative_NB_SB_Demand.png"); plt.close()

# ── RUN ──────────────────────────────────────────────────────────────────────
for d in ["NB", "SB"]:
    plot_strip(d)
    plot_eda(d)
    plot_braking(d)
plot_force_demand_10ft()
plot_cumulative()
plot_braking_composite()
print("✓ Synthetic visualization portfolio complete.")
