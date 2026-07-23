"""Validate Bleu Carbon Final — run through full pipeline, then propose additions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import re

from engine.family_scorer import FamilyAwareScorer
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import gate_formula

# Parse formula
path = Path("formulas/complete/Bleu_Carbon_Final_2026-05-08.md")
text = path.read_text(encoding="utf-8")

# Parse from the summary table (lines 112-179)
ingredients_ul: dict[str, float] = {}
dilutions: dict[str, float] = {}
concentrate_total = 0.0

# Parse the summary table
in_table = False
for line in text.split("\n"):
    if "Summary Table" in line:
        in_table = True
        continue
    if "**Total concentrate:**" in line:
        m = re.search(r"([\d,.]+)\s*µL", line)
        if m:
            concentrate_total = float(m.group(1).replace(",", ""))
        in_table = False
        continue
    if not in_table:
        continue
    m = re.match(r"\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*([\d,.]+)\s*\|", line)
    if m:
        name = m.group(2).strip().replace("**", "")
        dil_raw = m.group(3).strip().lower()
        amount = float(m.group(4).replace(",", ""))
        if any(x in name.lower() for x in ("ethanol", "total", "dilution", "material")):
            continue
        ingredients_ul[name] = amount
        dm = re.match(r"(\d+(?:\.\d+)?)\s*%", dil_raw)
        dilutions[name] = float(dm.group(1)) / 100.0 if dm else 1.0

total_ul = concentrate_total or sum(ingredients_ul.values())
pct = {n: (v / total_ul) * 100 for n, v in ingredients_ul.items()}

SEP = "=" * 70
DIV = "-" * 70

print(SEP)
print("  BLEU CARBON FINAL — BASELINE VALIDATION")
print(SEP)
print(f"  Parsed {len(ingredients_ul)} materials, {total_ul:.0f} uL concentrate\n")

# 1. GATES
print(DIV)
print("  1. GATE REPORT")
print(DIV)

fv = FormulaVector(ingredients=pct, dilutions=dilutions)

try:
    formula_dict = {
        "ingredients_ul": ingredients_ul,
        "dilutions": dilutions,
        "family_archetype": "aromatic_fougere.modern_mineral",
    }
    report = gate_formula(formula_dict)
    failures = [g for g in report.gates if g.status == "FAIL"]
    warnings = [g for g in report.gates if g.status == "WARN"]
    passes = [g for g in report.gates if g.status == "PASS"]
    print(f"  STATUS: {report.status} ({len(passes)}P / {len(warnings)}W / {len(failures)}F)")
    if failures:
        print("\n  FAILURES:")
        for g in failures:
            print(f"    [{g.status}] {g.gate:<30} {str(g.detail)[:100]}")
    if warnings:
        print("\n  WARNINGS:")
        for g in warnings:
            print(f"    [{g.status}] {g.gate:<30} {str(g.detail)[:100]}")
except Exception as e:
    print(f"  [ERROR] {e}")

# 2. SCORING
print(f"\n{DIV}")
print("  2. 10-AXIS SCORING (generic + aromatic_fougere)")
print(DIV)

axes = [
    "longevity",
    "sillage",
    "synergy",
    "luxury",
    "texture",
    "stacking_depth",
    "skin_performance",
    "hedonic",
    "perceptual_clarity",
    "photorealism",
]

try:
    scorer = FormulaScorer()
    scores = scorer.score(fv)
    print(f"\n  {'Axis':<22} {'Generic':>10}")
    print(f"  {'-' * 22} {'-' * 10}")
    for ax in axes:
        print(f"  {ax:<22} {scores.get(ax, 0):>10.1f}")
    geo = scores.get("geometric_total", 0)
    print(f"\n  Geometric composite: {geo:.1f}")
except Exception as e:
    print(f"  [ERROR] {e}")

# 3. FAMILY-AWARE
print(f"\n{DIV}")
print("  3. FAMILY-AWARE SCORING (aromatic_fougere)")
print(DIV)

# Get fougere weights from family_scorer
FOUGERE_WEIGHTS = {
    "longevity": 0.9,
    "sillage": 0.9,
    "synergy": 1.0,
    "luxury": 0.6,
    "texture": 0.5,
    "stacking_depth": 1.0,
    "skin_performance": 0.5,
    "hedonic": 0.6,
    "perceptual_clarity": 0.8,
    "photorealism": 0.4,
}

try:
    fam = FamilyAwareScorer()
    fam_scores = fam.score(fv, family="fougere")
    print(f"\n  {'Axis':<22} {'Score':>8} {'Weight':>8} {'Contrib':>10}")
    print(f"  {'-' * 22} {'-' * 8} {'-' * 8} {'-' * 10}")
    for ax in axes:
        val = fam_scores.get(ax, 0)
        w = FOUGERE_WEIGHTS.get(ax, 1.0)
        contrib = val * w
        print(f"  {ax:<22} {val:>8.1f} {w:>8.1f} {contrib:>10.1f}")
    geo_fam = fam_scores.get("geometric_total", 0)
    print(f"\n  Fougere-weighted geometric: {geo_fam:.1f}")
except Exception as e:
    print(f"  [ERROR] {e}")

# 4. PHYSICAL OAV QUICK SCAN
print(f"\n{DIV}")
print("  4. HEADSPACE OAV — TOP 15 + KEY WEAK SPOTS")
print(DIV)

try:
    state = build_formula_state(
        ingredients_ul=ingredients_ul,
        dilutions=dilutions,
        temperature_K=298.15,
        batch_volume_ml=30.0,
    )

    ranked = sorted(
        [(ms.name, (ms.oav or 0)) for ms in state.materials if (ms.oav or 0) > 0],
        key=lambda x: -x[1],
    )

    print("\n  Top 15 headspace OAV:")
    for i, (nm, ov) in enumerate(ranked[:15], 1):
        print(f"  {i:>2}. {nm:<35} {ov:>8.1f}")

    # Find below-threshold character materials
    print("\n  Subliminal character materials (OAV < 1) — missed opportunities:")
    for ms in state.materials:
        o = ms.oav or 0
        if 0 < o < 1:
            print(f"      {ms.name:<35} OAV={o:.3f}")

except Exception as e:
    print(f"  [ERROR] {e}")

# 5. INVENTORY CHECK FOR POSSIBLE ADDITIONS
print(f"\n{DIV}")
print("  5. INVENTORY CHECK — AVAILABLE ADDITIONS FOR LUXURY/PLEASURE")
print(DIV)

# Check what luxury materials are in inventory but NOT in formula
inventory_materials = set()
with open("inventory.txt", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("- "):
            name = line[2:].split("(")[0].strip()
            inventory_materials.add(name.lower())

formula_lower = {n.lower().replace(" (extra)", "").strip() for n in ingredients_ul}

# Luxury/pleasure candidate categories
luxury_adds = {
    "Incense depth": ["cardamom eo", "black pepper ftec", "cardamom ftec"],
    "Aromatic complexity": ["beta-pinene", "pine eo", "farnesol"],
    "Radiance/transparency": ["floralozone", "nympheal", "helional", "cyclamen aldehyde"],
    "Woody warmth": ["cashmeran", "amberwood f", "azarbre", "cedramber", "koavone"],
    "Sandalwood richness": ["polysantol", "bacdanol"],
    "Fixative depth": ["benzyl salicylate", "hexyl salicylate", "benzyl benzoate"],
    "Musk luxury": ["exaltolide", "musk ketone", "galaxolide", "macrolide"],
    "Gourmand whisper": ["ethyl maltol", "vanillin", "ethyl vanillin", "maple lactone"],
    "Smoky/mineral edge": ["birch tar rectified", "guaiacol", "isobutyl quinoline"],
    "Floral luxury": ["freesia hdi", "lilyreal nd", "mayol", "peonile", "bourgeonal"],
}

available_adds = {}
for cat, candidates in luxury_adds.items():
    available = [c for c in candidates if c in inventory_materials and c not in formula_lower]
    if available:
        available_adds[cat] = available

for cat, adds in available_adds.items():
    print(f"  {cat}:")
    for a in adds:
        print(f"    + {a.title()}")

print(SEP)
print("  BASELINE COMPLETE — ready for optimization proposals")
print(SEP)
