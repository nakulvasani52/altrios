import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Aesthetcs (User Palette)
COLORS = ['#FF0000', '#0000FF', '#FF9900', '#24E780', '#00FFFF', '#FF00FF', '#993366', '#969696']
plt.rcParams.update({
    "font.family": "Arial",
    "figure.dpi": 150,
})

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [0.5, 1, 1]})
plt.subplots_adjust(hspace=0.5)

# --- PANEL 1: CONSOLIDATED TRAIN GEOMETRY ---
ax1.set_title("1. Train Geometry & Component Footprints", fontsize=16, fontweight='bold', pad=15)
# Locos
ax1.add_patch(plt.Rectangle((0, 0.4), 92, 0.4, color=COLORS[0], label='Locomotives (4 Units, 92m)'))
# Cars
ax1.add_patch(plt.Rectangle((92, 0.4), 1800, 0.35, color=COLORS[1], alpha=0.7, label='Freight Cars (100 Units, 1800m)'))
ax1.set_xlim(-100, 2000)
ax1.set_ylim(0, 1)
ax1.set_xlabel("Distance from Front (meters)", fontsize=12)
ax1.set_yticks([])

# --- PANEL 2: FORCE DISTRIBUTION LOGIC ---
ax2.set_title("2. Mechanistic Force Distribution", fontsize=16, fontweight='bold', pad=15)
x = np.linspace(-50, 2000, 500)
# Loco Force (Concentrated Traction/DB)
y_loco = np.where((x >= 0) & (x <= 92), 1000, 0)
# Car Force (Distributed Air Braking)
y_car = np.where((x > 92) & (x <= 1892), 50, 0)

ax2.fill_between(x, 0, y_loco, color=COLORS[0], alpha=0.9, label='Traction/Dynamic Braking (Loco Only)')
ax2.fill_between(x, 0, y_car, color=COLORS[1], alpha=0.4, label='Air Braking (Distributed to Consist)')
ax2.set_ylabel("Applied Load (kN)", fontsize=13, fontweight='bold')
ax2.set_xlabel("Internal Train Position (m)", fontsize=12)
ax2.grid(True, linestyle='--', alpha=0.3)

# --- PANEL 3: VELOCITY IMPACT (DWELL TIME) ---
ax3.set_title("3. Impact of Velocity on Cumulative Impulse (kN·s)", fontsize=16, fontweight='bold', pad=15)
# Assume a 0.05 mile (80m) track bin
# High Speed (60 mph = 27 m/s) -> Dwell = 3 seconds
# Low Speed (10 mph = 4.5 m/s)  -> Dwell = 18 seconds
speed_labels = ['High Speed (60 mph)', 'Low Speed (10 mph)']
dwell_times = [3, 18]
forces = [500, 500] # Same peak force

x_imp = np.arange(len(speed_labels))
impulses = np.array(dwell_times) * np.array(forces)

bars = ax3.bar(x_imp, impulses, color=[COLORS[2], COLORS[6]], alpha=0.8, width=0.6)
ax3.set_xticks(x_imp)
ax3.set_xticklabels(speed_labels, fontsize=12, fontweight='bold')
ax3.set_ylabel("Track Impulse (kN·s)", fontsize=13, fontweight='bold')

# Annotate with the math
for bar, dwell, imp in zip(bars, dwell_times, impulses):
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height + 100,
             f'Dwell Time: {dwell}s\nImpulse: {imp:,} kN·s',
             ha='center', va='bottom', fontsize=11, fontweight='bold',
             bbox=dict(facecolor='white', alpha=0.7, edgecolor='gray'))

ax3.set_ylim(0, 10500)
ax3.grid(axis='y', linestyle='--', alpha=0.3)

# Final Touches
plt.suptitle("How the Track Demand Algorithm Translates Force to Fatigue", fontsize=20, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig("track_demand_logic_schematic.png")
print("Saved: track_demand_logic_schematic.png")
