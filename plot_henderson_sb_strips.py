#!/usr/bin/env python3
"""
Generate presentation-quality strip charts for the full Henderson subdivision
ALTRIOS simulation results.

x-axis: Milepost (MP 176.9 – 317.5)
Strips: Geometry, Speed, Resistance, Track Demand
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ── Styling ──────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.dpi": 140,
    "savefig.dpi": 300,
    "font.family": "Arial",
    "font.size": 18,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "legend.fontsize": 16,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "axes.grid": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

BLUE   = "#1f77b4"
ORANGE = "#ff7f0e"
GREEN  = "#2ca02c"
RED    = "#d62728"
PURPLE = "#9467bd"

SIM_CSV  = Path("results/henderson_sb_sim/sb_simulation.csv")
SEG_CSV  = Path("data/henderson_sb_segments.csv")
META_FILE = Path("data/henderson_sb_meta.json")
OUT_DIR  = Path("results/henderson_sb_sim")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Load metadata ────────────────────────────────────────────────────────────
with open(META_FILE) as f:
    meta = json.load(f)
MP_MIN       = meta['mp_min']
MP_MAX       = meta['mp_max']
DUMMY_LENGTH = meta['dummy_length_m']
MAIN_LENGTH  = meta['main_length_m']

def _sym_ylim(y, pad=1.15):
    y = np.asarray(y, float)
    if len(y) == 0 or np.all(np.isnan(y)):
        return (-1, 1)
    m = np.nanmax(np.abs(y))
    return (-pad * m, pad * m)

def pad_lim(v, pad=0.12):
    v = np.asarray(v, float)
    lo, hi = np.nanmin(v), np.nanmax(v)
    p = (hi - lo) * pad if hi != lo else 1
    return lo - p, hi + p


# ── Load & bin simulation data ───────────────────────────────────────────────
def load_sim_data():
    print("Loading simulation results...")
    df = pd.read_csv(SIM_CSV)

    # Filter to main corridor
    df = df[(df['total_dist_meters'] >= DUMMY_LENGTH) &
            (df['total_dist_meters'] <= DUMMY_LENGTH + MAIN_LENGTH)].copy()

    # Forces in kN
    df['f_grade_kn']  = df['res_grade_newtons'] / 1000.0
    df['f_curve_kn']  = df['res_curve_newtons'] / 1000.0
    df['f_roll_kn']   = df['res_rolling_newtons'] / 1000.0
    df['f_aero_kn']   = df['res_aero_newtons'] / 1000.0
    df['f_bearing_kn'] = df['res_bearing_newtons'] / 1000.0
    df['speed_mph']   = df['speed_meters_per_second'] * 2.23694

    # Wheel force (positive = traction, negative = braking)
    df['f_whl_kn'] = df['pwr_whl_out_watts'] / np.maximum(
        df['speed_meters_per_second'], 0.1) / 1000.0

    # Total resistance
    df['total_res_kn'] = (df['f_grade_kn'] + df['f_curve_kn'] +
                          df['f_roll_kn'] + df['f_aero_kn'] + df['f_bearing_kn'])

    # Track demand = -wheel + resistance
    df['track_long_kn'] = -df['f_whl_kn'] + df['total_res_kn']

    # Grade %
    df['grade_pct'] = df['grade_front'] * 100.0

    # Bin into 0.5 MP groups for a 140-mile route
    df['mp_group'] = (df['milepost'] * 2).round() / 2.0

    agg = df.groupby('mp_group').agg({
        'track_long_kn': 'mean',
        'grade_pct': 'mean',
        'f_grade_kn': 'mean',
        'f_curve_kn': 'mean',
        'f_roll_kn': 'mean',
        'f_aero_kn': 'mean',
        'f_bearing_kn': 'mean',
        'f_whl_kn': 'mean',
        'speed_mph': 'mean',
        'total_res_kn': 'mean',
    }).reset_index()

    print(f"  {len(df)} sim rows → {len(agg)} binned groups (0.5 MP)")
    return agg


def load_true_geometry():
    """Load curvature/grade from the raw segment CSV."""
    seg = pd.read_csv(SEG_CSV)
    seg = seg[seg['TrackNumber'] == 'SG'].copy()
    seg['mp_mid'] = (seg['beg_mp'] + seg['end_mp']) / 2.0
    seg['mp_group'] = (seg['mp_mid'] * 2).round() / 2.0

    geo = seg.groupby('mp_group').agg({
        'curvature_deg': 'mean',
        'grade_to_next': 'mean',
        'speed': 'mean',
    }).reset_index().rename(columns={
        'curvature_deg': 'true_curve_deg',
        'grade_to_next': 'true_grade_pct',
        'speed': 'true_speed_mph',
    })
    print(f"  True geometry: {len(geo)} bins")
    return geo


# ── Strip Chart 1: Stacked 4-panel ──────────────────────────────────────────
def plot_full_4panel(sim_df, geo_df, xlim, train_info):
    """4-panel strip chart:
       1. Infrastructure Geometry (curvature + grade)
       2. Speed Profile
       3. Resistance Breakdown
       4. Track Demand
    """
    merged = sim_df.merge(geo_df, on='mp_group', how='left').fillna(0)
    merged = merged.sort_values('mp_group')
    x = merged['mp_group'].values

    fig, (ax1, ax2, ax3, ax4) = plt.subplots(
        4, 1, figsize=(20, 14), sharex=True,
        gridspec_kw={"hspace": 0.35}
    )

    FS_TITLE, FS_LABEL, FS_TICK = 16, 14, 12
    C_CURVE = (1.0, 0.0, 0.0)
    C_GRADE = (0.0, 0.0, 1.0)
    C_SPEED = (1.0, 0.6, 0.0)

    # ── Panel 1: Geometry ────────────────────────────────────────────────────
    curve_abs = np.abs(merged['true_curve_deg'].values)
    ax1.plot(x, curve_abs, color=C_CURVE, linewidth=1.5, label="Curvature (|Deg|)")
    ax1.set_ylabel("Curvature (Deg)", fontweight="bold", fontsize=FS_LABEL, color=C_CURVE)
    ax1.set_ylim(0, max(float(np.nanmax(curve_abs)) * 1.25, 1.0))
    ax1.tick_params(axis="y", labelsize=FS_TICK, colors=C_CURVE)
    ax1.set_title(
        f"Henderson Subdivision SB: Infrastructure Geometry (MP {xlim[1]:.0f}–{xlim[0]:.0f}) | {train_info}",
        fontsize=FS_TITLE, fontweight="bold", pad=6)

    ax1b = ax1.twinx()
    ax1b.step(x, merged['true_grade_pct'].values, where="mid",
              color=C_GRADE, linewidth=1.5, label="Grade (%)")
    ax1b.set_ylabel("Grade (%)", fontweight="bold", fontsize=FS_LABEL, color=C_GRADE)
    ax1b.tick_params(axis="y", labelsize=FS_TICK, colors=C_GRADE)
    g = merged['true_grade_pct'].values
    g_range = max(abs(np.nanmin(g)), abs(np.nanmax(g))) * 1.3
    ax1b.set_ylim(-g_range, g_range)
    ax1.spines["top"].set_alpha(0.3)

    # ── Panel 2: Speed ───────────────────────────────────────────────────────
    ax2.fill_between(x, merged['speed_mph'].values, color=C_SPEED, alpha=0.35)
    ax2.plot(x, merged['speed_mph'].values, color=C_SPEED, linewidth=1.5)
    ax2.set_title("Speed Profile", fontsize=FS_TITLE, fontweight="bold", pad=6)
    ax2.set_ylabel("Speed (mph)", fontweight="bold", fontsize=FS_LABEL)
    ax2.set_ylim(0, max(float(np.nanmax(merged['speed_mph'])) * 1.15, 10.0))
    ax2.tick_params(axis="both", labelsize=FS_TICK)
    ax2.spines["top"].set_alpha(0.3)

    # ── Panel 3: Resistance Breakdown ────────────────────────────────────────
    ax3.plot(x, merged['f_grade_kn'],  color=BLUE,   linewidth=1.5, label="Grade")
    ax3.plot(x, merged['f_curve_kn'],  color=RED,    linewidth=1.5, label="Curve")
    f_roll_aero = merged['f_roll_kn'] + merged['f_aero_kn']
    ax3.plot(x, f_roll_aero,           color=GREEN,  linewidth=1.5, label="Rolling+Aero")
    ax3.set_title("Resistance Forces", fontsize=FS_TITLE, fontweight="bold", pad=6)
    ax3.set_ylabel("Force (kN)", fontweight="bold", fontsize=FS_LABEL)
    ax3.tick_params(axis="both", labelsize=FS_TICK)
    ax3.legend(loc="upper right", fontsize=10, ncol=3, frameon=True)
    ax3.spines["top"].set_alpha(0.3)

    # ── Panel 4: Track Demand ────────────────────────────────────────────────
    demand = merged['track_long_kn'].values
    ax4.plot(x, demand, color=PURPLE, linewidth=1.5, label="Track Demand")
    ax4.axhline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.4)
    ax4.set_title("Track Longitudinal Demand", fontsize=FS_TITLE, fontweight="bold", pad=6)
    ax4.set_ylabel("Demand (kN)", fontweight="bold", fontsize=FS_LABEL)
    ax4.set_ylim(*_sym_ylim(demand))
    ax4.set_xlabel("Milepost", fontweight="bold", fontsize=FS_LABEL)
    ax4.tick_params(axis="both", labelsize=FS_TICK)
    ax4.spines["top"].set_alpha(0.3)

    ax1.set_xlim(*xlim)
    ax1.invert_xaxis()

    fig.tight_layout()
    fname = OUT_DIR / "henderson_full_sb_4panel_strip.png"
    fig.savefig(fname, bbox_inches="tight")
    print(f"Saved: {fname}")
    return fig


# ── Strip Chart 2: Geometry + Speed (2-panel) ───────────────────────────────
def plot_geometry_speed(sim_df, geo_df, xlim, train_info):
    merged = sim_df.merge(geo_df, on='mp_group', how='left').fillna(0)
    merged = merged.sort_values('mp_group')
    x = merged['mp_group'].values

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(20, 6), sharex=True,
        gridspec_kw={"height_ratios": [1.4, 1], "hspace": 0.42}
    )

    C_CURVE = (1.0, 0.0, 0.0)
    C_GRADE = (0.0, 0.0, 1.0)
    C_SPEED = (1.0, 0.6, 0.0)
    FS_TITLE, FS_LABEL, FS_TICK = 16, 14, 12

    curve_abs = np.abs(merged['true_curve_deg'].values)
    ax_top.plot(x, curve_abs, color=C_CURVE, linewidth=1.8, label="Curvature (Deg)")
    ax_top.set_ylabel("Curvature (Deg)", fontweight="bold", fontsize=FS_LABEL, color=C_CURVE)
    ax_top.set_ylim(0, max(float(np.nanmax(curve_abs)) * 1.25, 1.0))
    ax_top.tick_params(axis="y", colors=C_CURVE)
    ax_top.set_title(
        f"Infrastructure Geometry (MP {xlim[1]:.0f}–{xlim[0]:.0f}) | {train_info}",
        fontsize=FS_TITLE, fontweight="bold")

    ax_top2 = ax_top.twinx()
    ax_top2.step(x, merged['true_grade_pct'].values, where="mid",
                 color=C_GRADE, linewidth=1.5)
    ax_top2.set_ylabel("Grade (%)", fontweight="bold", fontsize=FS_LABEL, color=C_GRADE)
    ax_top2.tick_params(axis="y", colors=C_GRADE)

    speed = merged['speed_mph'].values
    ax_bot.fill_between(x, speed, color=C_SPEED, alpha=0.35)
    ax_bot.plot(x, speed, color=C_SPEED, linewidth=1.5)
    ax_bot.set_title("Speed Profile", fontsize=FS_TITLE, fontweight="bold")
    ax_bot.set_ylabel("Speed (mph)", fontweight="bold", fontsize=FS_LABEL)
    ax_bot.set_xlabel("Milepost", fontweight="bold", fontsize=FS_LABEL)
    ax_bot.set_ylim(0, max(float(np.nanmax(speed)) * 1.18, 10.0))

    ax_top.set_xlim(*xlim)
    ax_top.invert_xaxis()
    fig.tight_layout()
    fname = OUT_DIR / "henderson_full_sb_geometry_speed.png"
    fig.savefig(fname, bbox_inches="tight")
    print(f"Saved: {fname}")


# ── Strip Chart 3: Resistance Analysis ───────────────────────────────────────
def plot_resistance_stacked(sim_df, xlim, train_info):
    d = sim_df.sort_values('mp_group')
    x = d['mp_group'].values

    fig, ax = plt.subplots(figsize=(20, 5))

    ax.stackplot(x,
                 d['f_grade_kn'], d['f_curve_kn'],
                 d['f_roll_kn'], d['f_aero_kn'],
                 labels=['Grade', 'Curve', 'Rolling', 'Aero'],
                 alpha=0.65, colors=[BLUE, RED, PURPLE, GREEN])
    ax.set_title(
        f"Henderson SB: Resistance Force Breakdown (MP {xlim[1]:.0f}–{xlim[0]:.0f}) | {train_info}",
        fontsize=16, fontweight="bold")
    ax.set_xlabel("Milepost", fontweight="bold", fontsize=14)
    ax.set_ylabel("Resistance Forces (kN)", fontweight="bold", fontsize=14)
    ax.set_xlim(*xlim)
    ax.invert_xaxis()
    ax.legend(loc="upper left", frameon=True, fontsize=11, ncol=2)

    fig.tight_layout()
    fname = OUT_DIR / "henderson_full_sb_resistance_stacked.png"
    fig.savefig(fname, bbox_inches="tight")
    print(f"Saved: {fname}")


# ── Strip Chart 4: Track Demand ──────────────────────────────────────────────
def plot_demand(sim_df, xlim, train_info):
    d = sim_df.sort_values('mp_group')
    x = d['mp_group'].values
    demand = d['track_long_kn'].values

    fig, ax = plt.subplots(figsize=(20, 5))
    ax.plot(x, demand, color=PURPLE, linewidth=1.8, label="Track Demand")
    ax.axhline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.4)

    # Annotate top-3 peaks
    top = d.nlargest(3, 'track_long_kn')[['mp_group', 'track_long_kn']]
    for _, r in top.iterrows():
        mp, val = float(r['mp_group']), float(r['track_long_kn'])
        ax.scatter([mp], [val], s=60, color=PURPLE, edgecolor='white', zorder=6)
        ax.text(mp + 0.5, val + 15, f"MP {mp:.1f}\n{val:.0f} kN",
                fontsize=9, ha="left",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="gray",
                          alpha=0.9, lw=0.5))

    ax.set_title(
        f"Henderson SB: Track Longitudinal Demand (MP {xlim[1]:.0f}–{xlim[0]:.0f}) | {train_info}",
        fontsize=16, fontweight="bold")
    ax.set_xlabel("Milepost", fontweight="bold", fontsize=14)
    ax.set_ylabel("Track Demand (kN)", fontweight="bold", fontsize=14)
    ax.set_xlim(*xlim)
    ax.invert_xaxis()
    ax.set_ylim(*_sym_ylim(demand))
    ax.legend(loc="upper right", frameon=True, fontsize=11)

    fig.tight_layout()
    fname = OUT_DIR / "henderson_full_sb_track_demand.png"
    fig.savefig(fname, bbox_inches="tight")
    print(f"Saved: {fname}")


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sim_df = load_sim_data()
    geo_df = load_true_geometry()

    # Update limits based on actual simulated data to remove whitespace
    sim_min_mp = sim_df['mp_group'].min()
    sim_max_mp = sim_df['mp_group'].max()
    xlim = (sim_min_mp - 0.5, sim_max_mp + 0.5)
    train_info = "Train: 100 Cars, 4 Locos (~15,190 Tons)"

    plot_full_4panel(sim_df, geo_df, xlim, train_info)
    plot_geometry_speed(sim_df, geo_df, xlim, train_info)
    plot_resistance_stacked(sim_df, xlim, train_info)
    plot_demand(sim_df, xlim, train_info)

    print("\n✓ All strip charts generated!")
