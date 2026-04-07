import matplotlib; matplotlib.use("Agg")
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ── Styling ──────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.dpi": 200,
    "savefig.dpi": 300,
    "font.family": "Arial",
    "font.size": 18,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "axes.grid": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white"
})

COLORS = ["#FF0000", "#0000FF", "#FF9900", "#24E780", "#00FFFF", "#FF00FF", "#993366", "#969696"]
C_CURVE, C_GRADE, C_SPEED, F_GRADE, F_CURVE, F_ROLL, C_DEMAND = COLORS[0:7]

DEST_DIR = Path("/Users/nakulvasani/Desktop/Lunch Meeting")
DEST_DIR.mkdir(parents=True, exist_ok=True)

def _sym_ylim(y, pad=1.15):
    y = np.asarray(y, float)
    if len(y) == 0 or np.all(np.isnan(y)): return (-1, 1)
    m = np.nanmax(np.abs(y))
    return (-pad * m, pad * m)

def load_all_data(sim_path, geo_path, meta_path):
    with open(meta_path) as f: m = json.load(f)
    dummy, main = m['dummy_length_m'], m['main_length_m']
    
    # Load Sim
    df = pd.read_csv(sim_path)
    df = df[(df['total_dist_meters'] >= dummy) & (df['total_dist_meters'] <= dummy + main)].copy()
    df['f_grade_kn'] = df['res_grade_newtons'] / 1000.0
    df['f_curve_kn'] = df['res_curve_newtons'] / 1000.0
    df['f_roll_kn'] = (df['res_rolling_newtons'] + df['res_aero_newtons']) / 1000.0
    df['speed_mph'] = df['speed_meters_per_second'] * 2.23694
    df['f_whl_kn'] = df['pwr_whl_out_watts'] / np.maximum(df['speed_meters_per_second'], 0.1) / 1000.0
    df['total_res_kn'] = (df['res_grade_newtons'] + df['res_curve_newtons'] + df['res_rolling_newtons'] + df['res_aero_newtons'] + df['res_bearing_newtons'])/1000.0
    df['track_long_kn'] = -df['f_whl_kn'] + df['total_res_kn']
    df['mp_group'] = (df['milepost'] * 2).round() / 2.0
    agg = df.groupby('mp_group').mean(numeric_only=True).reset_index()

    # Load Geo
    geo = pd.read_csv(geo_path)
    if 'beg_mp' in geo.columns:
        geo['mp_mid'] = (geo['beg_mp'] + geo['end_mp']) / 2.0
        geo['mp_group'] = (geo['mp_mid'] * 2).round() / 2.0
        geo_agg = geo.groupby('mp_group').mean(numeric_only=True).reset_index()
    else: # Fallback for different CSV format
        geo['mp_group'] = (geo['milepost'] * 2).round() / 2.0
        geo_agg = geo.groupby('mp_group').mean(numeric_only=True).reset_index()
    
    return agg.merge(geo_agg, on='mp_group', how='left').fillna(0).sort_values('mp_group')

def save_panel(x, y, color, title, ylabel, filename, xlim, invert=False, is_step=False, y2=None, c2=None, y2label=None):
    fig, ax = plt.subplots(figsize=(18, 5))
    if is_step:
        ax.step(x, y, where='mid', color=color, linewidth=2)
    else:
        ax.plot(x, y, color=color, linewidth=2)
        if "Speed" in title:
            ax.fill_between(x, y, color=color, alpha=0.3)

    if y2 is not None:
        ax2 = ax.twinx()
        ax2.step(x, y2, where='mid', color=c2, linewidth=1.5)
        ax2.set_ylabel(y2label, fontweight='bold', color=c2)
        ax2.tick_params(axis='y', colors=c2)
        m = max(abs(np.nanmin(y2)), abs(np.nanmax(y2))) * 1.3
        ax2.set_ylim(-m, m)

    ax.set_title(title, fontweight='bold', pad=10)
    ax.set_ylabel(ylabel, fontweight='bold', color=color if y2 is not None else 'black')
    ax.set_xlabel("Milepost", fontweight='bold')
    ax.set_xlim(*xlim)
    if invert: ax.invert_xaxis()
    if "Demand" in title: ax.axhline(0, color='gray', lw=0.8, ls='--', alpha=0.4); ax.set_ylim(*_sym_ylim(y))
    fig.tight_layout()
    fig.savefig(DEST_DIR / filename, bbox_inches='tight')
    plt.close(fig)

def save_resistance_panel(x, df, title, filename, xlim, invert=False):
    fig, ax = plt.subplots(figsize=(18, 5))
    ax.plot(x, df['f_grade_kn'], color=F_GRADE, lw=2)
    ax.plot(x, df['f_curve_kn'], color=F_CURVE, lw=2)
    ax.plot(x, df['f_roll_kn'], color=F_ROLL, lw=2)
    ax.set_title(title, fontweight='bold')
    ax.set_ylabel("Force (kN)", fontweight='bold')
    ax.set_xlabel("Milepost", fontweight='bold')
    ax.set_xlim(*xlim)
    if invert: ax.invert_xaxis()
    fig.tight_layout()
    fig.savefig(DEST_DIR / filename, bbox_inches='tight')
    plt.close(fig)

# ── RUN NB ───────────────────────────────────────────────────────────────────
nb = load_all_data("results/henderson_full_sim/nb_simulation.csv", 
                   "data/nvasani2_altrios_segments_henderson_sim_run", 
                   "data/henderson_full_meta.json")
xl = (nb['mp_group'].min(), nb['mp_group'].max())

save_panel(nb['mp_group'], np.abs(nb['curvature_deg'] if 'curvature_deg' in nb.columns else nb['true_curve_deg']), 
           C_CURVE, "NB: Infrastructure Geometry (Curvature & Grade)", "Curvature (Deg)", "NB_1_Geometry.png", xl, 
           y2=nb['grade_to_next'] if 'grade_to_next' in nb.columns else nb['true_grade_pct'], c2=C_GRADE, y2label="Grade (%)")

save_panel(nb['mp_group'], nb['speed_mph'], C_SPEED, "NB: Speed Profile", "Speed (mph)", "NB_2_Speed.png", xl)

save_resistance_panel(nb['mp_group'], nb, "NB: Resistance Forces (Grade, Curve, Rolling+Aero)", "NB_3_Resistance.png", xl)

save_panel(nb['mp_group'], nb['track_long_kn'], C_DEMAND, "NB: Track Longitudinal Demand", "Demand (kN)", "NB_4_Demand.png", xl)

# ── RUN SB ───────────────────────────────────────────────────────────────────
sb = load_all_data("results/henderson_sb_sim/sb_simulation.csv", 
                   "data/henderson_sb_segments.csv", 
                   "data/henderson_sb_meta.json")
xl_sb = (sb['mp_group'].min(), sb['mp_group'].max())

save_panel(sb['mp_group'], np.abs(sb['curvature_deg'] if 'curvature_deg' in sb.columns else sb['true_curve_deg']), 
           C_CURVE, "SB: Infrastructure Geometry (Curvature & Grade)", "Curvature (Deg)", "SB_1_Geometry.png", xl_sb, invert=True,
           y2=sb['grade_to_next'] if 'grade_to_next' in sb.columns else sb['true_grade_pct'], c2=C_GRADE, y2label="Grade (%)")

save_panel(sb['mp_group'], sb['speed_mph'], C_SPEED, "SB: Speed Profile", "Speed (mph)", "SB_2_Speed.png", xl_sb, invert=True)

save_resistance_panel(sb['mp_group'], sb, "SB: Resistance Forces (Grade, Curve, Rolling+Aero)", "SB_3_Resistance.png", xl_sb, invert=True)

save_panel(sb['mp_group'], sb['track_long_kn'], C_DEMAND, "SB: Track Longitudinal Demand", "Demand (kN)", "SB_4_Demand.png", xl_sb, invert=True)

print("Done generating individual panels.")
