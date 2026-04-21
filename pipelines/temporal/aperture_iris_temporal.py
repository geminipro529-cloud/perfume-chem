"""
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
Temporal Evolution Analysis — Aperture Iris (No Jasmine FO, Premiere Optimized)

Formula as-designed (optimized revision):
  - Crystal: standard 2400µL from prep guide (no spikes)
  - Musk stack: Habanolide + Zenolide + Exaltolide + Musk Ketone
  - Floral bridge: Hedione (trimmed) + PEA + Florol + Neroli + Cis Jasmone
  - Added: Cashmeran (20%) for frosty wood bridge
  - Total concentrate: 7500µL (25.0% in 30mL)

Full 4-panel temporal engine run:
  Panel 1 — Per-material perceived composition (stacked area)
  Panel 2 — Individual OAV lines per material (log scale)
  Panel 3 — Projection/sillage envelope
  Panel 4 — 12-dimension character evolution
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.temporal_graph import generate_temporal_graph, temporal_report
from engine.synergy_graph import SynergyGraph

# ── CONCENTRATE BREAKDOWN ──
# Standard crystal: 2400 µL (from prep guide, no spikes)
# Non-crystal materials: 5100 µL (from mixing guide)
# Total concentrate: 2400 + 5100 = 7500 µL

CRYSTAL_TOTAL = 2400.0

# Crystal composition — standard prep guide (µL)
crystal_ul = {
    "Alpha Irone":              696,    # 10% dilution
    "Orivone":                  120,
    "Orris F-TEC":              204,
    "Methyl Ionone":            288,
    "I-IRIS F-TEC":             156,
    "Alpha Ionone":             108,
    "Beta Ionone":              108,
    "Allyl Ionone":              36,
    "Dihydro Beta Ionone":      132,
    "Irotyl":                    48,
    "Ultralia":                  36,
    "Carrot Seed EO":            12,
    "Rose Oxide":                24,    # 1% dilution
    "Hedione":                  408,
    "Bacdanol":                  24,
}

# Non-crystal materials (µL values from optimized formula)
direct_ul = {
    "Bergamot FCF Sicilian":    360.0,
    "Cedrat FCF Sicilian":      160.0,
    "Red Mandarin EO":           30.0,
    "Linalool":                 130.0,
    "Pink Pepper Base":          25.0,
    "Aldehyde C12 MNA":          30.0,   # 1% dilution
    "Hedione":                 1020.0,   # trimmed from 1190 (diminishing returns)
    "Iso E Super":             1240.0,
    "Clearwood":                300.0,
    "Cedramber":                220.0,
    "Cashmeran":                 70.0,   # 20% dilution — frosty wood bridge
    "Habanolide":               370.0,
    "Zenolide":                 200.0,   # replaces subliminal Romandolide
    "Exaltolide":                80.0,   # 10% dilution — powdery musk depth
    "Musk Ketone":               60.0,   # 10% dilution — warm powdery nitro musk
    "Hexyl Salicylate":         400.0,
    "Bacdanol":                  80.0,   # additional Bacdanol beyond crystal
    "Phenethyl Alcohol":         35.0,
    "Florol":                    30.0,   # replaces subliminal Hydroxycitronellal
    "Neroli EO":                 40.0,   # boosted from 15 for naturality
    "Cis Jasmone":               25.0,   # boosted from 10
    "Indole":                     5.0,   # 10% dilution
    "Rose Oxide":                20.0,   # additional Rose Oxide beyond crystal
    "Ambrox Super":             170.0,   # 30% dilution
}

TOTAL_CONCENTRATE = CRYSTAL_TOTAL + sum(direct_ul.values())

# ── BUILD COMBINED INGREDIENT MAP (% of total concentrate) ──
ingredients: dict[str, float] = {}

# 1. Add crystal materials (convert µL → % of total concentrate)
for name, ul in crystal_ul.items():
    ingredients[name] = (ul / TOTAL_CONCENTRATE) * 100.0

# 2. Add direct materials (convert µL → % of total concentrate)
for name, ul in direct_ul.items():
    share = (ul / TOTAL_CONCENTRATE) * 100.0
    if name in ingredients:
        ingredients[name] += share
    else:
        ingredients[name] = share

# Verify total
total = sum(ingredients.values())
print(f"Total concentrate: {total:.2f}%  (should be ~100%)")
# Small rounding tolerance
assert abs(total - 100.0) < 1.0, f"Total is {total:.2f}, expected ~100.0"

# Normalize to exactly 100.0
scale = 100.0 / total
ingredients = {k: v * scale for k, v in ingredients.items()}

print(f"Normalized total: {sum(ingredients.values()):.2f}%")
print(f"\nSimulating {len(ingredients)} distinct materials...\n")

# Show ingredient breakdown
print("─── Ingredient Breakdown (% of concentrate) ───")
for name, pct in sorted(ingredients.items(), key=lambda x: -x[1]):
    print(f"  {name:30s}  {pct:6.2f}%")
print()

# ── OUTPUT ──
os.makedirs("output", exist_ok=True)
save_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "output", "Aperture_Iris_NoJasmineFO_temporal_graph.png"
)
report_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "output", "Aperture_Iris_NoJasmineFO_temporal_report.txt"
)

# ── BUILD SYNERGY DATA ──
print("Building synergy graph...")
sg = SynergyGraph()
sg.build(list(ingredients.keys()))
synergy_data = {k: e.weight for k, e in sg.edges.items()}
print(f"Synergy edges: {len(synergy_data)} pairwise interactions\n")

# ── RUN ──
profile, fig = generate_temporal_graph(
    formula_name="Aperture Iris — Premiere Optimized (No Jasmine FO)",
    ingredients=ingredients,
    save_path=save_path,
    show=False,
    synergy_data=synergy_data,
)

# Report
report = temporal_report(profile)
print(report)

with open(report_path, "w", encoding="utf-8") as f:
    f.write(report)

# Summary
print(f"\n{'═' * 60}")
print(f"✓ Temporal graph saved: {os.path.abspath(save_path)}")
print(f"✓ Text report saved:   {os.path.abspath(report_path)}")
print(f"✓ Perceptual half-life: {profile.perceptual_half_life_hr:.1f} hr")
print(f"✓ Longevity (OAV>2):    {profile.longevity_hr:.1f} hr")
print(f"✓ Materials simulated:  {len(ingredients)}")

# Perceptibility
perceptible = [m for m, mt in profile.materials.items()
               if max(mt.oav) >= 1.0]
subliminal = [m for m, mt in profile.materials.items()
              if max(mt.oav) < 1.0]

print(f"✓ Perceptible:          {len(perceptible)}/{len(ingredients)}")
if subliminal:
    print(f"  Subliminal: {', '.join(subliminal)}")

# OAV rankings
print(f"\n─── OAV Ranking at Opening ───")
opening_oavs = {m: mt.oav[0] for m, mt in profile.materials.items()}
for m, oav in sorted(opening_oavs.items(), key=lambda x: -x[1])[:15]:
    print(f"  {m:30s}  OAV={oav:>10.1f}")

# OAV at 8hr drydown
import numpy as np
t8_idx = np.searchsorted(profile.time_hours, 8.0)
print(f"\n─── OAV Ranking at 8hr Drydown ───")
drydown_oavs = {m: mt.oav[min(t8_idx, len(mt.oav)-1)]
                for m, mt in profile.materials.items()}
for m, oav in sorted(drydown_oavs.items(), key=lambda x: -x[1])[:15]:
    if oav >= 0.1:
        print(f"  {m:30s}  OAV={oav:>10.1f}")

# Character at key timepoints
print(f"\n─── Character Snapshots ───")
for label, hrs in [("Opening", 0), ("15min", 0.25), ("30min", 0.5),
                    ("1hr", 1), ("2hr", 2), ("4hr", 4), ("6hr", 6),
                    ("8hr", 8), ("12hr", 12), ("16hr", 16), ("24hr", 24)]:
    idx = np.searchsorted(profile.time_hours, hrs)
    idx = min(idx, len(profile.time_hours) - 1)
    snapshot = {}
    for dim, arr in profile.character_evolution.items():
        val = arr[idx]
        if val > 2.0:
            snapshot[dim] = val
    top_dims = sorted(snapshot.items(), key=lambda x: -x[1])[:5]
    dim_str = ", ".join(f"{d}={v:.0f}%" for d, v in top_dims)
    print(f"  {label:8s}: {dim_str}")

# ── EXTENDED ANALYSIS ──

# Note evolution at all timepoints
print(f"\n─── Note Balance Over Time ───")
print(f"  {'Time':8s}  {'Top':>6s}  {'Heart':>6s}  {'Base':>6s}  {'Dominant':>10s}")
for label, hrs in [("0min", 0), ("5min", 5/60), ("15min", 0.25), ("30min", 0.5),
                    ("1hr", 1), ("2hr", 2), ("3hr", 3), ("4hr", 4),
                    ("6hr", 6), ("8hr", 8), ("10hr", 10), ("12hr", 12),
                    ("16hr", 16), ("20hr", 20), ("24hr", 24)]:
    idx = np.searchsorted(profile.time_hours, hrs)
    idx = min(idx, len(profile.time_hours) - 1)
    t_val = profile.note_evolution["top"][idx]
    h_val = profile.note_evolution["heart"][idx]
    b_val = profile.note_evolution["base"][idx]
    dominant = max([("top", t_val), ("heart", h_val), ("base", b_val)],
                   key=lambda x: x[1])[0]
    print(f"  {label:8s}  {t_val:5.1f}%  {h_val:5.1f}%  {b_val:5.1f}%  {dominant:>10s}")

# Full OAV timeline for every material
print(f"\n─── Full OAV Timeline (all materials) ───")
timepoints = [("0min", 0), ("15min", 0.25), ("1hr", 1), ("2hr", 2),
              ("4hr", 4), ("8hr", 8), ("12hr", 12), ("24hr", 24)]
header = f"  {'Material':30s}"
for label, _ in timepoints:
    header += f"  {label:>7s}"
print(header)
print("  " + "─" * (30 + 9 * len(timepoints)))

# Sort materials by opening OAV
mat_by_oav = sorted(profile.materials.items(), key=lambda x: -x[1].oav[0])
for name, mt in mat_by_oav:
    row = f"  {name:30s}"
    for label, hrs in timepoints:
        idx = np.searchsorted(profile.time_hours, hrs)
        idx = min(idx, len(mt.oav) - 1)
        oav = mt.oav[idx]
        if oav >= 100:
            row += f"  {oav:7.0f}"
        elif oav >= 1:
            row += f"  {oav:7.1f}"
        elif oav >= 0.01:
            row += f"  {oav:7.2f}"
        else:
            row += f"  {oav:7.3f}"
    # Mark if subliminal
    peak = max(mt.oav)
    flag = " ◌" if peak < 1.0 else ""
    row += flag
    print(row)

# Perceived intensity (Stevens) at key times
print(f"\n─── Perceived Intensity (Stevens OAV^0.4) at 4hr ───")
t4_idx = np.searchsorted(profile.time_hours, 4.0)
t4_idx = min(t4_idx, len(profile.time_hours) - 1)
intensities = []
for name, mt in profile.materials.items():
    pi = mt.perceived_intensity[t4_idx]
    if pi > 0:
        intensities.append((name, pi, mt.oav[t4_idx]))
intensities.sort(key=lambda x: -x[1])
total_pi = sum(x[1] for x in intensities)
print(f"  {'Material':30s}  {'Intensity':>10s}  {'% of Total':>10s}  {'OAV':>8s}")
for name, pi, oav in intensities[:20]:
    pct = pi / total_pi * 100 if total_pi > 0 else 0
    print(f"  {name:30s}  {pi:10.2f}  {pct:9.1f}%  {oav:8.1f}")

# Projection timeline
print(f"\n─── Projection / Sillage Over Time ───")
for label, hrs in [("0min", 0), ("5min", 5/60), ("15min", 0.25), ("30min", 0.5),
                    ("1hr", 1), ("2hr", 2), ("4hr", 4), ("8hr", 8),
                    ("12hr", 12), ("24hr", 24)]:
    idx = np.searchsorted(profile.time_hours, hrs)
    idx = min(idx, len(profile.projection_cm) - 1)
    proj = profile.projection_cm[idx]
    bar = "█" * int(proj / 3)
    zone = "sillage cloud" if proj > 100 else "social" if proj > 65 else "intimate" if proj > 30 else "skin"
    print(f"  {label:8s}  {proj:5.0f} cm  {bar}  [{zone}]")

# Headspace ppb for top materials
print(f"\n─── Headspace Concentration (ppb) Over Time ───")
header2 = f"  {'Material':30s}"
for label, _ in timepoints:
    header2 += f"  {label:>8s}"
print(header2)
print("  " + "─" * (30 + 10 * len(timepoints)))
for name, mt in mat_by_oav[:20]:
    row = f"  {name:30s}"
    for label, hrs in timepoints:
        idx = np.searchsorted(profile.time_hours, hrs)
        idx = min(idx, len(mt.headspace_ppb) - 1)
        ppb = mt.headspace_ppb[idx]
        if ppb >= 100:
            row += f"  {ppb:8.0f}"
        elif ppb >= 1:
            row += f"  {ppb:8.1f}"
        else:
            row += f"  {ppb:8.3f}"
    print(row)