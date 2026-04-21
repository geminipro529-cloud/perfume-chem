"""
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
Temporal Evolution Analysis — Opus V Crystallized Iris/Orris Accord v2

Runs the 16-material accord through the temporal engine to validate:
- OAV hierarchy (does Alpha Irone lead perceptually?)
- Perceptibility (how many of 16 materials are above threshold?)
- Longevity projection for the standalone accord
- Character evolution over time

Note: This is an accord module, not a finished perfume. Longevity and
projection numbers reflect the accord IN ISOLATION — when used at 10-20%
in a destination formula, the accord's temporal profile integrates with
the surrounding materials.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.temporal_graph import generate_temporal_graph, temporal_report

# ─── FORMULA: Opus V Crystallized Iris/Orris v2 (1000 µL) ───
# All values as percentage of accord concentrate

ingredients = {
    # IRIS IDENTITY (85.7%)
    "Alpha Irone":              30.0,   # 300 µL at 10%
    "Orivone":                  10.0,   # 100 µL neat
    "Methyl Ionone":            11.0,   # 110 µL neat (engine canonical name)
    "Orris F-TEC":               9.5,   # 95 µL neat
    "I-IRIS F-TEC":              5.5,   # 55 µL neat
    "Alpha Ionone":              4.5,   # 45 µL neat
    "Beta Ionone":               3.5,   # 35 µL neat
    "Dihydro Beta Ionone":       4.0,   # 40 µL neat
    "Irotyl":                    2.5,   # 25 µL neat
    "Allyl Ionone":              2.0,   # 20 µL neat (engine: Allyl Ionone)
    "Alpha-Isomethyl Ionone":    1.5,   # 15 µL neat
    "Ultralia":                  1.2,   # 12 µL neat

    # ROOT REALISM (1.8%)
    "Carrot Seed EO":            0.8,   # 8 µL neat
    "Rose Oxide":                1.0,   # 10 µL at 1%

    # ACCORD SUPPORT (13.0%)
    "Hedione":                  12.0,   # 120 µL neat
    "Bacdanol":                  1.0,   # 10 µL neat
}

# Verify total
total = sum(ingredients.values())
print(f"Total concentrate: {total:.1f}%  (should be 100.0%)")
assert abs(total - 100.0) < 0.1, f"Total is {total}, expected 100.0"

print(f"\nSimulating {len(ingredients)} materials...\n")

# Output paths
os.makedirs("output", exist_ok=True)
save_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "output", "Opus_V_Crystal_Iris_v2_temporal_graph.png"
)
report_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "output", "Opus_V_Crystal_Iris_v2_temporal_report.txt"
)

# Run simulation
profile, fig = generate_temporal_graph(
    formula_name='Opus V Crystallized Iris/Orris — Accord v2',
    ingredients=ingredients,
    save_path=save_path,
    show=False,
)

# Generate text report
report = temporal_report(profile)
print(report)

# Save text report
with open(report_path, "w", encoding="utf-8") as f:
    f.write(report)

# Summary
print(f"\n✓ Temporal graph saved: {os.path.abspath(save_path)}")
print(f"✓ Text report saved:   {os.path.abspath(report_path)}")
print(f"✓ Perceptual half-life: {profile.perceptual_half_life_hr:.1f} hr")
print(f"✓ Longevity (OAV>2):    {profile.longevity_hr:.1f} hr")
print(f"✓ Materials simulated:  {len(ingredients)}")

# Perceptibility analysis
perceptible = [m for m, mt in profile.materials.items()
               if max(mt.oav) >= 1.0]
subliminal = [m for m, mt in profile.materials.items()
              if max(mt.oav) < 1.0]

print(f"✓ Perceptible:          {len(perceptible)}/{len(ingredients)}")
if subliminal:
    print(f"  Subliminal: {', '.join(subliminal)}")

# OAV ranking at opening
print(f"\n─── OAV Ranking at Opening ───")
opening_oavs = {m: mt.oav[0] for m, mt in profile.materials.items()}
for m, oav in sorted(opening_oavs.items(), key=lambda x: -x[1])[:10]:
    print(f"  {m:30s}  OAV={oav:>8.1f}")