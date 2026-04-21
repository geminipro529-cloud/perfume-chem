"""
Porcelaine Poudrée — Cosmetic Face-Powder Floral
Temporal evolution analysis using engine/temporal_graph.py

Powder character via heliotropin + coumarin + musk ketone (no iris/orris materials).

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
# Formula: percentage of 2450 µL concentrate
# ═══════════════════════════════════════════════════════════════════════════════

FORMULA_NAME = 'Porcelaine Poudrée — Cosmetic Face-Powder Floral (Iris-Free)'

TOTAL_CONC = 2450  # µL total concentrate

INGREDIENTS = {
    # ━━━ SOFT CITRUS-LAVENDER LIFT (250 µL / 10.2%) ━━━
    "Bergamot FCF oil Sicilian":  80 / TOTAL_CONC * 100,   # 3.27%  neat
    "Linalyl Acetate":           120 / TOTAL_CONC * 100,   # 4.90%  neat
    "Linalool":                   50 / TOTAL_CONC * 100,   # 2.04%  neat

    # ━━━ COSMETIC POWDER-FLORAL CORE (980 µL / 40.0%) ━━━
    "Dimethyl Benzyl Carbinyl Acetate": 130 / TOTAL_CONC * 100,  # 5.31%  neat (DBCA)
    "Hedione":                   250 / TOTAL_CONC * 100,   # 10.20% neat
    "Hexyl Salicylate":          180 / TOTAL_CONC * 100,   # 7.35%  neat
    "Alpha-Isomethyl Ionone":    120 / TOTAL_CONC * 100,   # 4.90%  neat (violet-powder, not iris in this context)
    "Methyl Ionone Pure":         80 / TOTAL_CONC * 100,   # 3.27%  neat (powder 6 > floral 5)
    "Heliotropin Fleuressence":  220 / TOTAL_CONC * 100,   # 8.98%  neat (STAR: almond-vanilla face-powder, increased)

    # ━━━ MUGUET CONNECTOR — MINIMIZED (100 µL / 4.1%) ━━━
    "Hydroxycitronellal":         60 / TOTAL_CONC * 100,   # 2.45%  neat (minimized, floral 7 drag)
    "Lilyreal ND":                40 / TOTAL_CONC * 100,   # 1.63%  neat (minimized, floral 7 drag)

    # ━━━ COUMARINIC POWDER-MUSK SKIN (1120 µL / 45.7%) ━━━
    "Coumarin":                  300 / TOTAL_CONC * 100,   # 12.24% (20% dilution → 2.45% active, increased for powder anchor)
    "Iso E Super":               200 / TOTAL_CONC * 100,   # 8.16%  neat
    "Cashmeran":                 150 / TOTAL_CONC * 100,   # 6.12%  (20% dilution → 1.22% active)
    "Musk Ketone":               100 / TOTAL_CONC * 100,   # 4.08%  (10% dilution → 0.41% active, vintage powder musk)
    "Tonka Bean FO":              90 / TOTAL_CONC * 100,   # 3.67%  neat (balsamic-coumarinic warmth)
    "Galaxolide":                100 / TOTAL_CONC * 100,   # 4.08%  (80% dilution → 3.27% active)
    "Habanolide":                 80 / TOTAL_CONC * 100,   # 3.27%  neat
    "Ethylene Brassylate":       100 / TOTAL_CONC * 100,   # 4.08%  neat (increased, powdery musk)
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

graph_path = output_dir / "Porcelaine_Poudree_temporal_graph.png"
report_path = output_dir / "Porcelaine_Poudree_temporal_report.txt"

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
