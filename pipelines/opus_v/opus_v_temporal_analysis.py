"""
Opus V "Woods Symphony" — Definitive Reconstruction v3
Temporal evolution analysis using engine/temporal_graph.py

Runs the full simulation and generates:
 - 4-panel temporal graph PNG
 - Text report to console and file
"""

import sys
from pathlib import Path

# Ensure engine is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engine.temporal_graph import generate_temporal_graph, temporal_report

# ═══════════════════════════════════════════════════════════════════════════════
# Formula: percentage of 2500 µL concentrate
# The temporal engine handles dilution internally via profile.dilution
# ═══════════════════════════════════════════════════════════════════════════════

FORMULA_NAME = 'Amouage Opus V — "Woods Symphony" — Reconstruction v3'

# All values = (volume_µL / 2500) × 100 = percentage of concentrate
INGREDIENTS = {
    # ━━━ IRIS CORE (41.0%) ━━━
    "Alpha Irone":              370 / 2500 * 100,   # 14.80%  (10% dilution → 1.48% active)
    "Orivone":                  110 / 2500 * 100,   # 4.40%   neat
    "Methyl Ionone":            100 / 2500 * 100,   # 4.00%   neat (alias: Methyl Ionone Pure)
    "Orris F-TEC":              110 / 2500 * 100,   # 4.40%   neat
    "I-IRIS F-TEC":              65 / 2500 * 100,   # 2.60%   neat
    "Alpha Ionone":              55 / 2500 * 100,   # 2.20%   neat
    "Beta Ionone":               45 / 2500 * 100,   # 1.80%   neat
    "Irotyl":                    35 / 2500 * 100,   # 1.40%   neat
    "Dihydro Beta Ionone":       30 / 2500 * 100,   # 1.20%   neat
    "Allyl Ionone":              30 / 2500 * 100,   # 1.20%   neat
    "Ultralia":                  18 / 2500 * 100,   # 0.72%   neat
    "Carrot Seed EO":            15 / 2500 * 100,   # 0.60%   neat
    "Alpha-Isomethyl Ionone":    15 / 2500 * 100,   # 0.60%   neat
    "Rose Oxide":                12 / 2500 * 100,   # 0.48%   (profile dil 0.1 → ~0.048% active)
    "Heliotropin Fleuressence":  15 / 2500 * 100,   # 0.60%   neat

    # ━━━ RHUM ACCORD (7.4%) ━━━
    "Ethyl Vanillin":            28 / 2500 * 100,   # 1.12%   neat
    "Maple Lactone":             55 / 2500 * 100,   # 2.20%   (20% dilution → 0.44% active)
    "Labdanum":                  45 / 2500 * 100,   # 1.80%   neat
    "Benzoin Resinoid":          45 / 2500 * 100,   # 1.80%   (50% DPG → 0.90% active)
    "Eugenol":                   12 / 2500 * 100,   # 0.48%   neat

    # ━━━ JASMINE·ROSE (11.8%) ━━━
    "Hedione":                  185 / 2500 * 100,   # 7.40%   neat
    "Jasmine FO":                40 / 2500 * 100,   # 1.60%   neat
    "Phenethyl Alcohol":         35 / 2500 * 100,   # 1.40%   neat
    "Citronellol":               25 / 2500 * 100,   # 1.00%   neat
    "Indole":                    10 / 2500 * 100,   # 0.40%   (10% dilution → 0.04% active)

    # ━━━ OUD·CIVET·LEATHER (8.2%) ━━━
    "Guaiacol":                  12 / 2500 * 100,   # 0.48%   neat
    "Patchouli EO":              50 / 2500 * 100,   # 2.00%   neat
    "Myrrh EO":                  28 / 2500 * 100,   # 1.12%   neat
    "Cedarwood oil Virginia":    45 / 2500 * 100,   # 1.80%   neat
    "Vetiver EO":                25 / 2500 * 100,   # 1.00%   neat
    "Isobutyl Quinoline":        25 / 2500 * 100,   # 1.00%   (10% dilution → 0.10% active)
    "Suederal":                  20 / 2500 * 100,   # 0.80%   (10% dilution → 0.08% active)

    # ━━━ WOODS SYMPHONY (19.6%) ━━━
    "Iso E Super":              190 / 2500 * 100,   # 7.60%   neat
    "Ambrox Super":             120 / 2500 * 100,   # 4.80%   (30% dilution → 1.44% active)
    "Vertofix":                  60 / 2500 * 100,   # 2.40%   neat
    "Clearwood":                 50 / 2500 * 100,   # 2.00%   neat
    "Evernyl":                   25 / 2500 * 100,   # 1.00%   neat
    "Bacdanol":                  25 / 2500 * 100,   # 1.00%   neat
    "Vetival":                   20 / 2500 * 100,   # 0.80%   neat

    # ━━━ MUSK BED (7.0%) ━━━
    "Galaxolide":                65 / 2500 * 100,   # 2.60%   (80% dilution → 2.08% active)
    "Habanolide":                45 / 2500 * 100,   # 1.80%   neat
    "Ethylene Brassylate":       35 / 2500 * 100,   # 1.40%   neat
    "Romandolide":               30 / 2500 * 100,   # 1.20%   neat

    # ━━━ STRUCTURAL (5.0%) ━━━
    "Benzyl Salicylate":         65 / 2500 * 100,   # 2.60%   neat
    "Coumarin":                  35 / 2500 * 100,   # 1.40%   (20% dilution → 0.28% active)
    "Cashmeran":                 25 / 2500 * 100,   # 1.00%   (20% dilution → 0.20% active)
}

# Verify total
total_pct = sum(INGREDIENTS.values())
print(f"Total concentrate: {total_pct:.1f}%  (should be 100.0%)")
assert abs(total_pct - 100.0) < 0.5, f"Total is {total_pct:.2f}%, expected ~100%"

# ═══════════════════════════════════════════════════════════════════════════════
# Run temporal simulation
# ═══════════════════════════════════════════════════════════════════════════════

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

graph_path = output_dir / "Opus_V_v3_temporal_graph.png"
report_path = output_dir / "Opus_V_v3_temporal_report.txt"

print(f"\nSimulating {len(INGREDIENTS)} materials...")
profile, fig = generate_temporal_graph(
    formula_name=FORMULA_NAME,
    ingredients=INGREDIENTS,
    save_path=str(graph_path),
    show=False,
)

# Generate text report
report = temporal_report(profile)
print("\n" + report)

# Save report
report_path.write_text(report, encoding="utf-8")
print(f"\n✓ Temporal graph saved: {graph_path}")
print(f"✓ Text report saved:   {report_path}")
print(f"✓ Perceptual half-life: {profile.perceptual_half_life_hr:.1f} hr")
print(f"✓ Longevity (OAV>2):    {profile.longevity_hr:.1f} hr")
print(f"✓ Materials simulated:  {len(profile.materials)}")

# Count perceptible materials
perceptible = [m for m in profile.materials.values() if max(m.oav) >= 1.0]
subliminal = [m for m in profile.materials.values() if max(m.oav) < 1.0]
print(f"✓ Perceptible:          {len(perceptible)}/{len(profile.materials)}")
if subliminal:
    print(f"  Subliminal: {', '.join(m.name for m in subliminal)}")
