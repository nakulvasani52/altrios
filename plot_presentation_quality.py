import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ---------- Styling (presentation-ready) ----------
plt.rcParams.update({
    "figure.dpi": 140,
    "savefig.dpi": 300,
    "font.family": "Arial",
    "font.size": 12,
    "axes.titlesize": 15,
    "axes.labelsize": 13,
    "legend.fontsize": 11,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "axes.grid": False,
    "grid.alpha": 0.0,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

BLUE   = "#1f77b4"
ORANGE = "#ff7f0e"
GREEN  = "#2ca02c"
RED    = "#d62728"
PURPLE = "#9467bd"

OUT_DIR = Path("results/presentation")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MP_MIN, MP_MAX = 242.0, 252.9

def _nice_sym_ylim(y, pad=1.12):
    y = np.asarray(y, dtype=float)
    if len(y) == 0 or np.all(np.isnan(y)): return (-1, 1)
    m = np.nanmax(np.abs(y))
    return (-pad*m, pad*m)

def pad_lim(v, pad=0.12):
    v = np.asarray(v, float)
    if len(v) == 0 or np.all(np.isnan(v)): return (-1, 1)
    lo, hi = np.nanmin(v), np.nanmax(v)
    if np.isfinite(lo) and np.isfinite(hi) and lo != hi:
        p = (hi - lo) * pad
        return lo - p, hi + p
    return lo - 1, hi + 1

def load_and_bin_data():
    nb_csv = "results/henderson_nb_simulation.csv"
    sb_csv = "results/henderson_sb_simulation.csv"
    
    dfs = []
    for csv_path, direction in [(nb_csv, "NB"), (sb_csv, "SB")]:
        df = pd.read_csv(csv_path)
        # Filter to corridor 242-253
        df = df[(df['total_dist_meters'] >= 50000) & (df['total_dist_meters'] <= 67703.4)].copy()
        
        # Mapping to Milepost
        m_to_mile = 1/1609.34
        if direction == "NB":
            df['mp'] = 242.0 + (df['total_dist_meters'] - 50000) * m_to_mile
        else:
            df['mp'] = 252.99 - (df['total_dist_meters'] - 50000) * m_to_mile
            
        # Forces in kN
        df['f_grade_kn'] = df['res_grade_newtons'] / 1000.0
        df['f_curve_kn'] = df['res_curve_newtons'] / 1000.0
        df['f_roll_kn'] = df['res_rolling_newtons'] / 1000.0
        df['f_aero_kn'] = df['res_aero_newtons'] / 1000.0
        df['speed_mph'] = df['speed_meters_per_second'] * 2.23694
        
        # Track props from hotspot logic (clean signals)
        df['hs_curve_kn'] = df['f_curve_kn']
        df['hs_grade_pct'] = df['grade_front'] * 100.0
        
        # Wheel Force (Positive = Traction, Negative = Braking)
        df['f_whl_kn'] = df['pwr_whl_out_watts'] / np.maximum(df['speed_meters_per_second'], 0.1) / 1000.0
        
        # Total Resistance (Sum of all components)
        df['total_res_kn'] = (df['f_grade_kn'] + df['f_curve_kn'] + df['f_roll_kn'] + df['f_aero_kn'])
        
        # Track Demand = -Wheel Force + Total Resistance
        # Under this convention (Matching user's preferred visuals):
        # Positive (+) = Braking/Resistance Demand (Train shoving rail forward)
        # Negative (-) = Tractive Demand (Loco pulling rail backward)
        df['track_long_kn'] = -df['f_whl_kn'] + df['total_res_kn']
        
        # Bin into 0.1 MP groups
        df['mp_group'] = (df['mp'] * 10).round() / 10.0
        
        agg_df = df.groupby('mp_group').agg({
            'track_long_kn': 'mean',
            'hs_grade_pct': 'mean',
            'hs_curve_kn': 'mean',
            'f_grade_kn': 'mean',
            'f_roll_kn': 'mean',
            'f_aero_kn': 'mean',
            'f_whl_kn': 'mean',
            'speed_mph': 'mean'
        }).reset_index()
        
        agg_df['abs_demand'] = agg_df['track_long_kn'].abs()
        agg_df['direction'] = direction
        dfs.append(agg_df)
        
    full_df = pd.concat(dfs)
    
    # Load True Geometry Ground Truth
    seg = pd.read_csv("data/henderson_segments.csv")
    seg['mp_mid'] = (seg['beg_mp'] + seg['end_mp']) / 2
    seg['mp_group'] = (seg['mp_mid'] * 10).round() / 10.0
    true_geo = seg.groupby('mp_group').agg({
        'curvature_deg': 'mean', # Signed degree of curvature (Left/Right)
        'grade_to_next': 'mean' # True grade
    }).reset_index().rename(columns={
        'curvature_deg': 'true_curve_deg',
        'grade_to_next': 'true_grade_pct'
    })
    
    # Merge True Geo into the binned results
    full_df = full_df.merge(true_geo, on='mp_group', how='left').fillna(0)
    
    return full_df

def _nice_sym_ylim(data):
    M = np.max(np.abs(data))
    if M == 0: return -1, 1
    return -M * 1.15, M * 1.15

def plot_demand_directional(meeting_df, direction="NB", top_annotate=3, save=True):
    d = meeting_df[meeting_df["direction"] == direction].copy()
    color = BLUE if direction == "NB" else ORANGE
    name  = "Northbound" if direction == "NB" else "Southbound"

    # Annotations only for top peaks
    top = d.nlargest(top_annotate, "abs_demand")[["mp_group","track_long_kn"]].copy()

    # Longer width to accommodate legend/details
    fig, ax = plt.subplots(figsize=(14.5, 4.8))

    # main line - NO MARKERS as requested
    ax.plot(d["mp_group"], d["track_long_kn"], color=color, linewidth=2.6, label=f"{name} Demand")

    # annotate top few
    for _, r in top.iterrows():
        mp = float(r["mp_group"])
        val = float(r["track_long_kn"])
        ax.scatter([mp], [val], s=70, color=color, edgecolor="white", linewidth=1.0, zorder=6)
        ax.text(
            mp + (0.08 if direction=="NB" else -0.08),
            val + (22 if val >= 0 else -22),
            f"MP {mp:.1f}\n{val:.0f} kN",
            fontsize=10,
            ha="left" if direction=="NB" else "right",
            va="bottom" if val >= 0 else "top",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="gray", alpha=0.9, lw=0.5)
        )

    ax.set_title(f"Henderson Corridor (MP {MP_MIN:.1f}\u2013{MP_MAX:.1f}): {name} Track Demand")
    ax.set_xlabel("Milepost (0.1 bins)")
    ax.set_ylabel("Track Demand (kN)")

    # Axis direction: SB reversed
    if direction == "SB":
        ax.set_xlim(MP_MAX, MP_MIN)
    else:
        ax.set_xlim(MP_MIN, MP_MAX)

    ax.set_ylim(*_nice_sym_ylim(d["track_long_kn"].values))
    ax.legend(loc="upper right", frameon=True)
    ax.spines["top"].set_alpha(0.4)
    ax.spines["right"].set_alpha(0.4)

    fig.tight_layout()
    if save:
        fname = OUT_DIR / f"henderson_{direction.lower()}_track_demand_directional.png"
        fig.savefig(fname, bbox_inches="tight")
        print("Saved:", fname)

def plot_curve_grade_single(meeting_df, save=True):
    # Canonical ordering (NB)
    d = meeting_df[meeting_df["direction"]=="NB"].sort_values("mp_group").copy()
    x = d["mp_group"].values
    # USE TRUE GEOMETRY FIELDS
    curve = d["true_curve_deg"].astype(float).values
    grade = d["true_grade_pct"].astype(float).values
    
    # Clip grade for cleaner visualization if needed, but here we show true
    
    fig, ax = plt.subplots(figsize=(14.5, 4.2))

    # Curve on primary axis
    ax.plot(x, curve, color=BLUE, linewidth=2.4, label="Curvature (Deg)")
    ax.set_ylabel("Curvature (Deg)", fontweight='bold')
    ax.set_xlabel("Milepost (0.1 bins)", fontweight='bold')
    ax.set_xlim(MP_MIN, MP_MAX)
    ax.set_ylim(*_nice_sym_ylim(curve)) # Symmetrical view for L/R curves
    
    # Grade on secondary axis
    ax2 = ax.twinx()
    ax2.step(x, grade, where="mid", color=ORANGE, linewidth=2.4, label="Grade (%)")
    ax2.set_ylabel("Grade (%)", fontweight='bold')
    ax2.set_ylim(grade.min() * 1.2, grade.max() * 1.5)

    ax.set_title(f"Henderson Corridor (MP {MP_MIN:.1f}\u2013{MP_MAX:.1f}): Infrastructure Geometry")
    
    # Combined legend
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="upper right", frameon=True)

    ax.grid(True, alpha=0.15)
    ax.spines["top"].set_alpha(0.3)
    ax.spines["right"].set_alpha(0.3)
    ax2.spines["top"].set_alpha(0.3)

    fig.tight_layout()
    if save:
        fname = OUT_DIR / "henderson_geometry_presentation.png"
        fig.savefig(fname, bbox_inches="tight")
        print("Saved:", fname)

def plot_resistance_grouped(meeting_df, direction="NB", save=True):
    d = meeting_df[meeting_df["direction"]==direction].sort_values("mp_group").copy()
    x = d["mp_group"].values
    
    roll_aero = d['f_roll_kn'] + d['f_aero_kn']
    
    fig, ax = plt.subplots(figsize=(14.5, 4.5))
    ax.plot(x, roll_aero, color=GREEN, linewidth=2.5, label="Rolling + Aero (Standard Resistance)", alpha=0.9)
    ax.plot(x, d['hs_curve_kn'], color=RED, linewidth=2.5, label="Curve Resistance (Geometry-driven)", alpha=0.9)
    
    ax.set_title(f"Henderson Corridor: {direction} Resistance Drivers (Friction vs. Geometry)")
    ax.set_xlabel("Milepost (0.1 bins)", fontweight='bold')
    ax.set_ylabel("Resistive Force (kN)", fontweight='bold')
    
    if direction == "SB": ax.set_xlim(MP_MAX, MP_MIN)
    else: ax.set_xlim(MP_MIN, MP_MAX)
    
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True, alpha=0.15)
    
    fig.tight_layout()
    if save:
        fname = OUT_DIR / f"henderson_{direction.lower()}_resistance_grouped.png"
        fig.savefig(fname, bbox_inches="tight")
        print("Saved:", fname)

def plot_rolling_aero_stylized(meeting_df, direction="NB", save=True):
    d = meeting_df[meeting_df["direction"]==direction].sort_values("mp_group").copy()
    x = d["mp_group"].values
    
    roll_aero = d['f_roll_kn'] + d['f_aero_kn']
    
    fig, ax = plt.subplots(figsize=(14.5, 4.5))
    ax.plot(x, roll_aero, color=GREEN, linewidth=2.5, label="Rolling + Aero (Standard Resistance)")
    
    ax.set_title(f"Henderson Corridor: {direction} Resistance Drivers (Standard Friction)")
    ax.set_xlabel("Milepost (0.1 bins)", fontweight='bold')
    ax.set_ylabel("Resistive Force (kN)", fontweight='bold')
    
    if direction == "SB": ax.set_xlim(MP_MAX, MP_MIN)
    else: ax.set_xlim(MP_MIN, MP_MAX)
    
    ax.set_ylim(0, 200) # Match the scale of the user's reference
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True, alpha=0.15)
    
    fig.tight_layout()
    if save:
        fname = OUT_DIR / f"henderson_{direction.lower()}_rolling_aero_stylized.png"
        fig.savefig(fname, bbox_inches="tight")
        print("Saved:", fname)

def plot_grade_resistance(meeting_df, direction="NB", save=True):
    d = meeting_df[meeting_df["direction"]==direction].sort_values("mp_group").copy()
    x = d["mp_group"].values
    
    fig, ax = plt.subplots(figsize=(14.5, 4.0))
    ax.fill_between(x, d['f_grade_kn'], color=ORANGE, alpha=0.3, label="Grade Resistance (kN)")
    ax.plot(x, d['f_grade_kn'], color=ORANGE, linewidth=2.5)
    
    ax.set_title(f"Henderson Corridor: {direction} Grade Resistance Profile")
    ax.set_xlabel("Milepost (0.1 bins)", fontweight='bold')
    ax.set_ylabel("Force (kN)", fontweight='bold')
    
    if direction == "SB": ax.set_xlim(MP_MAX, MP_MIN)
    else: ax.set_xlim(MP_MIN, MP_MAX)
    
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True, alpha=0.15)
    
    fig.tight_layout()
    if save:
        fname = OUT_DIR / f"henderson_{direction.lower()}_grade_resistance.png"
        fig.savefig(fname, bbox_inches="tight")
        print("Saved:", fname)

def plot_speed_trace(meeting_df, direction="NB", save=True):
    d = meeting_df[meeting_df["direction"]==direction].sort_values("mp_group").copy()
    x = d["mp_group"].values
    
    fig, ax = plt.subplots(figsize=(14.5, 3.5))
    ax.plot(x, d['speed_mph'], color=GREEN, linewidth=2.5, label="Actual Speed (mph)")
    ax.axhline(45, color='gray', linestyle='--', alpha=0.5, label="Corridor Limit (45 mph)")
    
    ax.set_title(f"Henderson Corridor: {direction} Speed Profile")
    ax.set_xlabel("Milepost (0.1 bins)", fontweight='bold')
    ax.set_ylabel("Speed (mph)", fontweight='bold')
    
    if direction == "SB": ax.set_xlim(MP_MAX, MP_MIN)
    else: ax.set_xlim(MP_MIN, MP_MAX)
    
    ax.set_ylim(0, 55)
    ax.legend(loc="lower right", frameon=True)
    ax.grid(True, alpha=0.15)
    
    fig.tight_layout()
    if save:
        fname = OUT_DIR / f"henderson_{direction.lower()}_speed_profile.png"
        fig.savefig(fname, bbox_inches="tight")
        print("Saved:", fname)

def plot_railtec_integration_v2(meeting_df, direction="NB", save=True):
    d = meeting_df[meeting_df["direction"]==direction].sort_values("mp_group").copy()
    x = d["mp_group"].values
    
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(15, 12), sharex=True)
    
    # 1. Geometry
    ax1.plot(x, d["true_curve_deg"], color=BLUE, label="Curve (Deg)")
    ax1b = ax1.twinx()
    ax1b.step(x, d["true_grade_pct"], where="mid", color=ORANGE, label="Grade (%)")
    ax1.set_ylabel("Curvature (Deg)")
    ax1b.set_ylabel("Grade (%)")
    ax1.set_title(f"Integrated Analysis: {direction} Direction")
    
    # 2. Speed
    ax2.plot(x, d["speed_mph"], color=GREEN, label="Speed (mph)")
    ax2.set_ylabel("Speed (mph)")
    ax2.set_ylim(0, 60)
    
    # 3. Resistance
    ax3.plot(x, d["f_grade_kn"], color=BLUE, label="Grade Res")
    ax3.plot(x, d["hs_curve_kn"], color=RED, label="Curve Res")
    ax3.set_ylabel("Resistance (kN)")
    
    # 4. Demand
    ax4.plot(x, d["track_long_kn"], color=PURPLE if direction=="NB" else ORANGE, label="Track Demand")
    ax4.set_ylabel("Demand (kN)")
    ax4.set_ylim(*_nice_sym_ylim(d["track_long_kn"]))
    
    for ax in [ax1, ax2, ax3, ax4]:
        ax.grid(True, alpha=0.1)
        ax.legend(loc="upper right", fontsize=8)

    if direction == "SB": ax1.set_xlim(MP_MAX, MP_MIN)
    else: ax1.set_xlim(MP_MIN, MP_MAX)
    
    ax4.set_xlabel("Milepost (0.1 bins)", fontweight='bold')
    
    plt.tight_layout()
    if save:
        fname = OUT_DIR / f"henderson_{direction.lower()}_integration_v2.png"
        fig.savefig(fname, bbox_inches="tight")
        print("Saved:", fname)

def plot_resistance_analysis(meeting_df, direction="NB", save=True):
    d = meeting_df[meeting_df["direction"]==direction].sort_values("mp_group").copy()
    x = d["mp_group"].values
    
    # Resistance components
    f_grade = d['f_grade_kn'].values
    f_curve = d['hs_curve_kn'].values
    f_roll = d['f_roll_kn'].values
    f_aero = d['f_aero_kn'].values
    
    # Use longer aspect ratio as requested
    fig, ax = plt.subplots(figsize=(15, 4.2))
    
    # Stacked Area for resistance
    ax.stackplot(x, f_grade, f_curve, f_roll, f_aero,
                 labels=['Grade', 'Curve', 'Rolling', 'Aero'],
                 alpha=0.65, colors=[BLUE, RED, PURPLE, GREEN])
    
    name = "Northbound" if direction == "NB" else "Southbound"
    ax.set_title(f"Henderson Corridor: {name} Resistance Force Breakdown")
    ax.set_xlabel("Milepost (0.1 bins)", fontweight='bold')
    ax.set_ylabel("Resistance Forces (kN)", fontweight='bold')
    
    if direction == "SB": ax.set_xlim(MP_MAX, MP_MIN)
    else: ax.set_xlim(MP_MIN, MP_MAX)
        
    ax.legend(loc="upper left", frameon=True, fontsize=10, ncol=2)
    ax.grid(True, alpha=0.15)
    
    fig.tight_layout()
    if save:
        fname = OUT_DIR / f"henderson_{direction.lower()}_resistance_analysis.png"
        fig.savefig(fname, bbox_inches="tight")
        print("Saved:", fname)

def plot_cumulative_work(meeting_df, direction="NB", save=True):
    d = meeting_df[meeting_df["direction"]==direction].sort_values("mp_group").copy()
    # Handle reversed SB order for cumulative calculation
    if direction == "SB":
        d = d.sort_values("mp_group", ascending=False)
        
    x = d["mp_group"].values
    # Work = Force * Distance. (0.1 mile = 160.9 meters)
    work = (d['abs_demand'] * 160.9).cumsum() / 1000.0 # MJ
    
    fig, ax = plt.subplots(figsize=(14.5, 3.5))
    ax.fill_between(x, work, color=BLUE, alpha=0.2)
    ax.plot(x, work, color=BLUE, linewidth=2.5, label="Cumulative Work (MJ)")
    
    ax.set_title(f"Henderson Corridor: {direction} Cumulative Track Work (Energy Expended)")
    ax.set_xlabel("Milepost (0.1 bins)", fontweight='bold')
    ax.set_ylabel("Energy (MJ)", fontweight='bold')
    
    if direction == "SB": ax.set_xlim(MP_MAX, MP_MIN)
    else: ax.set_xlim(MP_MIN, MP_MAX)
    
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True, alpha=0.15)
    
    fig.tight_layout()
    if save:
        fname = OUT_DIR / f"henderson_{direction.lower()}_cumulative_work.png"
        fig.savefig(fname, bbox_inches="tight")
        print("Saved:", fname)

def plot_demand_purple_style(meeting_df, direction="NB", save=True):
    d = meeting_df[meeting_df["direction"]==direction].sort_values("mp_group").copy()
    x = d["mp_group"].values
    # Apply a 3-point moving average to match the "Purple" style's smoothness
    demand_smooth = d["track_long_kn"].rolling(window=3, center=True).mean().fillna(d["track_long_kn"])
    
    fig, ax = plt.subplots(figsize=(14.5, 3.5))
    ax.plot(x, demand_smooth, color=PURPLE, linewidth=2.0, label="Track Demand")
    
    ax.set_title(f"Henderson Corridor (MP 242.0\u2013252.9): {direction} Maintenance Index")
    ax.set_xlabel("Milepost (0.1 bins)", fontweight='bold')
    ax.set_ylabel("Demand (kN)", fontweight='bold')
    
    if direction == "SB": ax.set_xlim(MP_MAX, MP_MIN)
    else: ax.set_xlim(MP_MIN, MP_MAX)
    
    ax.set_ylim(-300, 300) # Use the scale from the user's purple reference
    ax.legend(loc="upper right", frameon=True, fontsize=9)
    ax.grid(True, alpha=0.15)
    
    fig.tight_layout()
    if save:
        fname = OUT_DIR / f"henderson_{direction.lower()}_track_demand_purple.png"
        fig.savefig(fname, bbox_inches="tight")
        print("Saved:", fname)

def plot_stacked_geometry_speed(meeting_df, direction="NB", save=True):
    """Stacked 2-panel chart: Infrastructure Geometry (curve + grade) on top,
    Speed Profile (filled area) on bottom. Mirrors the reference image."""
    d = meeting_df[meeting_df["direction"] == direction].sort_values("mp_group").copy()
    x = d["mp_group"].values
    curve = d["true_curve_deg"].astype(float).values
    grade = d["true_grade_pct"].astype(float).values
    speed = d["speed_mph"].astype(float).values

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1,
        figsize=(13, 5.2),
        sharex=True,
        gridspec_kw={"height_ratios": [1.4, 1], "hspace": 0.42}
    )

    FS_TITLE  = 16
    FS_LABEL  = 14
    FS_TICK   = 12
    FS_LEGEND = 12

    C_CURVE = (1.0, 0.0, 0.0)          # RGB 255,0,0   — Curvature
    C_GRADE = (0.0, 0.0, 1.0)          # RGB 0,0,255   — Grade
    C_SPEED = (1.0, 0.6, 0.0)          # RGB 255,153,0 — Speed

    # ── Top panel: Curvature (left axis) + Grade (right axis) ────────────────
    curve_abs = np.abs(curve)
    ax_top.plot(x, curve_abs, color=C_CURVE, linewidth=2.2, label="Curvature (Deg)")
    ax_top.set_ylabel("Curvature (Deg)", fontweight="bold", fontsize=FS_LABEL, color=C_CURVE)
    ax_top.set_ylim(0, max(float(np.nanmax(curve_abs)) * 1.25, 1.0))
    ax_top.tick_params(axis="y", labelsize=FS_TICK, colors=C_CURVE)
    ax_top.tick_params(axis="x", labelsize=FS_TICK)
    ax_top.spines["left"].set_color(C_CURVE)
    ax_top.set_title(
        f"Infrastructure Geometry (MP {MP_MIN:.0f}\u2013{MP_MAX:.0f})",
        fontsize=FS_TITLE, fontweight="bold", pad=6
    )

    ax_top2 = ax_top.twinx()
    ax_top2.step(x, grade, where="mid", color=C_GRADE, linewidth=2.0, label="Grade (%)")
    ax_top2.set_ylabel("Grade (%)", fontweight="bold", fontsize=FS_LABEL, color=C_GRADE)
    ax_top2.tick_params(axis="y", labelsize=FS_TICK, colors=C_GRADE)
    ax_top2.spines["right"].set_color(C_GRADE)
    g_min = float(np.nanmin(grade))
    g_max = float(np.nanmax(grade))
    pad = max(abs(g_min), abs(g_max)) * 0.25
    ax_top2.set_ylim(g_min - pad, g_max + pad)

    ax_top.spines["top"].set_alpha(0.3)
    ax_top.grid(False)



    # ── Bottom panel: Speed filled area ──────────────────────────────────────
    ax_bot.fill_between(x, speed, color=C_SPEED, alpha=0.35)
    ax_bot.plot(x, speed, color=C_SPEED, linewidth=2.0)
    ax_bot.set_title("Speed Profile", fontsize=FS_TITLE, fontweight="bold", pad=6)
    ax_bot.set_ylabel("Speed (mph)", fontweight="bold", fontsize=FS_LABEL)
    ax_bot.set_xlabel("Milepost", fontweight="bold", fontsize=FS_LABEL)
    ax_bot.set_ylim(0, max(float(np.nanmax(speed)) * 1.18, 10.0))
    ax_bot.tick_params(axis="both", labelsize=FS_TICK)
    ax_bot.spines["top"].set_alpha(0.3)
    ax_bot.grid(False)

    # Shared x limits
    if direction == "SB":
        ax_top.set_xlim(MP_MAX, MP_MIN)
    else:
        ax_top.set_xlim(MP_MIN, MP_MAX)

    fig.tight_layout()
    if save:
        fname = OUT_DIR / f"henderson_{direction.lower()}_stacked_geometry_speed.png"
        fig.savefig(fname, bbox_inches="tight")
        print("Saved:", fname)
    return fig


def plot_final_4_panel_stack(meeting_df, save=True):
    nb = meeting_df[meeting_df["direction"]=="NB"].sort_values("mp_group").copy()
    sb = meeting_df[meeting_df["direction"]=="SB"].sort_values("mp_group").copy()
    x = nb["mp_group"].values
    
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(15, 14), sharex=True)
    
    # 1. Infrastructure Geometry
    ax1.plot(x, nb["true_curve_deg"], color=BLUE, label="Curvature (Deg)")
    ax1b = ax1.twinx()
    ax1b.step(x, nb["true_grade_pct"], where="mid", color=ORANGE, label="Grade (%)")
    ax1.set_ylabel("Curvature (Deg)")
    ax1b.set_ylabel("Grade (%)")
    ax1.set_title("Master Analysis: Henderson Corridor Infrastructure Geometry")
    
    # 2. SB Demand (ORANGE)
    ax2.plot(x, sb["track_long_kn"], color=ORANGE, linewidth=1.5, label="Southbound Demand")
    ax2.set_ylabel("SB Demand (kN)")
    ax2.set_xlim(MP_MIN, MP_MAX) # Horizontal alignment
    
    # 3. NB Demand (BLUE)
    ax3.plot(x, nb["track_long_kn"], color=BLUE, linewidth=1.5, label="Northbound Demand")
    ax3.set_ylabel("NB Demand (kN)")
    
    # 4. Stylized Maintenance Demand (PURPLE)
    smooth_nb = nb["track_long_kn"].rolling(window=3, center=True).mean().fillna(nb["track_long_kn"])
    ax4.plot(x, smooth_nb, color=PURPLE, linewidth=2.0, label="Consolidated Demand (Smoothed)")
    ax4.set_ylabel("Demand (kN)")
    ax4.set_ylim(-350, 350)
    
    for ax in [ax1, ax2, ax3, ax4]:
        ax.grid(True, alpha=0.1)
        ax.legend(loc="upper right", fontsize=8)

    ax4.set_xlabel("Milepost (0.1 bins)", fontweight='bold')
    plt.tight_layout()
    
    if save:
        fname = OUT_DIR / "henderson_master_4_panel_presentation.png"
        fig.savefig(fname, bbox_inches="tight")
        print("Saved:", fname)

def plot_braking_and_wheel_power(save=True):
    """2-panel slide chart: Braking Force Breakdown (top) + Loco Wheel Power (bottom).
    Loads the heavy NB simulation CSV directly."""
    from scipy.ndimage import gaussian_filter1d

    CSV = "results/henderson_nb_braking.csv"
    df = pd.read_csv(CSV)

    # ── Derived quantities (same methodology as analyze_nb_braking.py) ────────
    BUFFER_M = 50_000
    df["milepost"] = (df["total_dist_meters"] - BUFFER_M) / 1609.34 + 242
    df = df[(df["milepost"] >= 242) & (df["milepost"] <= 252.5)].copy().reset_index(drop=True)

    df["speed_mps"] = df["speed_meters_per_second"]
    df["accel_ms2"] = gaussian_filter1d(
        (df["speed_mps"].diff() / df["dt_seconds"]).fillna(0).values, sigma=3
    )
    df["F_res_N"] = (
        df["res_grade_newtons"] + df["res_curve_newtons"] +
        df["res_rolling_newtons"] + df["res_aero_newtons"] + df["res_bearing_newtons"]
    )
    df["F_net_N"] = df["mass_static_kilograms"] * df["accel_ms2"] + df["F_res_N"]
    df["F_dyn_N"] = np.where(
        df["pwr_whl_out_watts"] < 0,
        np.abs(df["pwr_whl_out_watts"]) / np.maximum(df["speed_mps"], 1.0),
        0.0
    )
    df["F_air_N"] = np.maximum(0, -(df["F_net_N"] + df["F_dyn_N"]))
    df["F_dyn_kN"] = gaussian_filter1d(df["F_dyn_N"].values, sigma=2) / 1000
    df["F_air_kN"] = gaussian_filter1d(df["F_air_N"].values, sigma=2) / 1000
    df["pwr_MW"]   = df["pwr_whl_out_watts"] / 1e6

    x = df["milepost"].values

    # ── Colors ────────────────────────────────────────────────────────────────
    C_DYN   = (1.0, 0.0, 0.0)          # red   — Dynamic
    C_AIR   = (0.0, 0.0, 1.0)          # blue  — Air
    C_PWR   = (0.8, 0.6, 0.0)          # mustard — Wheel power

    FS_TITLE  = 16
    FS_LABEL  = 14
    FS_TICK   = 12
    FS_LBL    = 12

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(13, 5.2), sharex=True,
        gridspec_kw={"height_ratios": [1.2, 1], "hspace": 0.42}
    )

    # ── Top: Braking Force Breakdown ──────────────────────────────────────────
    ax1.plot(x, df["F_dyn_kN"], color=C_DYN, linewidth=2.0, label="Dynamic")
    ax1.fill_between(x, 0, df["F_dyn_kN"], color=C_DYN, alpha=0.18)
    ax1.plot(x, df["F_air_kN"], color=C_AIR, linewidth=2.0, label="Air")
    ax1.fill_between(x, 0, df["F_air_kN"], color=C_AIR, alpha=0.18)
    ax1.set_title(f"Braking Force Breakdown (MP {MP_MIN:.0f}\u2013{MP_MAX:.0f})",
                  fontsize=FS_TITLE, fontweight="bold", pad=6)
    ax1.set_ylabel("Force (kN)", fontweight="bold", fontsize=FS_LABEL)
    ax1.tick_params(axis="both", labelsize=FS_TICK)
    ax1.set_ylim(bottom=0)
    ax1.set_ylim(bottom=0)
    ax1.grid(False)
    ax1.spines["top"].set_alpha(0.3)

    # Inline labels — Dynamic near left peak, Air near right
    d_idx = int(np.argmax(df["F_dyn_kN"].values[:len(x)//3]))  # first big dynamic peak
    ax1.text(x[d_idx], df["F_dyn_kN"].iloc[d_idx] + df["F_dyn_kN"].max() * 0.07,
             "Dynamic", color=C_DYN, fontsize=FS_LBL, fontweight="bold",
             ha="center", va="bottom",
             bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75))
    a_idx = int(len(x) * 0.82)
    ax1.text(x[a_idx], df["F_air_kN"].iloc[a_idx] + df["F_air_kN"].max() * 0.07,
             "Air", color=C_AIR, fontsize=FS_LBL, fontweight="bold",
             ha="center", va="bottom",
             bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75))

    # ── Bottom: Loco Wheel Power ───────────────────────────────────────────────
    ax2.plot(x, df["pwr_MW"], color=C_PWR, linewidth=1.8)
    ax2.fill_between(x, 0, df["pwr_MW"], where=(df["pwr_MW"] >= 0),
                     color=C_PWR, alpha=0.35)
    ax2.fill_between(x, 0, df["pwr_MW"], where=(df["pwr_MW"] < 0),
                     color=C_PWR, alpha=0.55)
    ax2.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.4)
    ax2.set_title("Locomotive Wheel Power (Negative = Regenerative Braking)",
                  fontsize=FS_TITLE, fontweight="bold", pad=6)
    ax2.set_ylabel("Power (MW)", fontweight="bold", fontsize=FS_LABEL)
    ax2.set_xlabel("Milepost", fontweight="bold", fontsize=FS_LABEL)
    ax2.tick_params(axis="both", labelsize=FS_TICK)
    ax2.tick_params(axis="both", labelsize=FS_TICK)
    ax2.grid(False)
    ax2.spines["top"].set_alpha(0.3)

    ax1.set_xlim(MP_MIN, MP_MAX)

    fig.tight_layout()
    if save:
        fname = OUT_DIR / "henderson_nb_braking_wheel_power.png"
        fig.savefig(fname, bbox_inches="tight")
        print("Saved:", fname)
    return fig


if __name__ == "__main__":
    df = load_and_bin_data()
    plot_stacked_geometry_speed(df)          # NEW: stacked geometry + speed
    plot_curve_grade_single(df)
    plot_final_4_panel_stack(df)
    
    for dir_ in ["NB"]:
        plot_demand_directional(df, dir_)
        plot_demand_purple_style(df, dir_)
        plot_grade_resistance(df, dir_)
        plot_rolling_aero_stylized(df, dir_)
        plot_resistance_analysis(df, dir_)
        plot_resistance_grouped(df, dir_)
        plot_speed_trace(df, dir_)
        plot_cumulative_work(df, dir_)
        plot_railtec_integration_v2(df, dir_)
        
    for dir_ in ["SB"]:
        plot_demand_directional(df, dir_)
        plot_grade_resistance(df, dir_)
        plot_rolling_aero_stylized(df, dir_)
        plot_resistance_analysis(df, dir_)
        plot_resistance_grouped(df, dir_)
        plot_speed_trace(df, dir_)

    print("\nDefinitive Presentation Package Generated.")
