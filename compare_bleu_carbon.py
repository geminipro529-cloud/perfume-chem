"""Validate Bleu Carbon v2 — compare against v1 baseline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import re

from engine.family_scorer import FamilyAwareScorer
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer
from engine.pipeline.gates import gate_formula


def parse_formula(path_str):
    path = Path(path_str)
    text = path.read_text(encoding="utf-8")
    ingredients_ul = {}
    dilutions = {}

    # Parse all table rows — skip summary tables (look for "Role" column or section headers)
    in_summary = False
    for line in text.split("\n"):
        if "Summary Table" in line:
            in_summary = True
            continue
        if "Total concentrate" in line or "Total volume" in line:
            in_summary = False
            continue
        if "Layer A" in line or "Layer B" in line or "Layer C" in line or "TOP" in line or "HEART" in line or "BASE" in line:
            continue
        if "Dilution" in line and "Ethanol" in line:
            continue

        # Skip summary table rows (4-column format without Active/Role)
        if in_summary:
            continue

        # Match 6-column with optional bold on amount: **700**
        m = re.match(r'\|\s*(\d+|[A-Z]\d+)\s*\|\s*\*?\*?(.+?)\*?\*?\s*\|\s*(.+?)\s*\|\s*\*?\*?([\d,.]+)\*?\*?\s*\|\s*([\d,.]+)\s*\|', line)
        if m:
            name = m.group(2).strip().replace("**", "").replace("*", "")
            dil_raw = m.group(3).strip().lower()
            try:
                amount = float(m.group(4).replace(",", ""))
            except ValueError:
                continue
            skip_words = ["ethanol", "total", "dilution", "subtotal", "material", "role", "---"]
            if any(x in name.lower() for x in skip_words):
                continue
            if not name or name in ("#", ""):
                continue
            # Remove parenthetical markers like **(v2: NEW)**
            name = re.sub(r'\s*\(v2:.*?\)', '', name).strip()
            ingredients_ul[name] = amount
            dm = re.match(r"(\d+(?:\.\d+)?)\s*%", dil_raw)
            dilutions[name] = float(dm.group(1)) / 100.0 if dm else 1.0

    total_ul = sum(ingredients_ul.values())
    pct = {n: (v / total_ul) * 100 for n, v in ingredients_ul.items()}
    return ingredients_ul, dilutions, total_ul, pct

SEP = "=" * 80
DIV = "-" * 80

# Parse both formulas
v1_ing, v1_dil, v1_total, v1_pct = parse_formula("formulas/complete/Bleu_Carbon_Final_2026-05-08.md")
v2_ing, v2_dil, v2_total, v2_pct = parse_formula("formulas/complete/Bleu_Carbon_v2_Optimized_30mL_EDP.md")

print(SEP)
print("  BLEU CARBON — v1 vs v2 COMPARISON")
print(SEP)
print(f"  v1: {len(v1_ing)} materials, {v1_total:.0f} uL ({v1_total/30000*100:.1f}%)")
print(f"  v2: {len(v2_ing)} materials, {v2_total:.0f} uL ({v2_total/30000*100:.1f}%)")

# New materials in v2
new_in_v2 = {n for n in v2_ing if n not in v1_ing}
boosted = {n for n in v2_ing if n in v1_ing and v2_ing[n] > v1_ing[n]}
unchanged = {n for n in v2_ing if n in v1_ing and v2_ing[n] == v1_ing[n]}

print(f"  New in v2: {len(new_in_v2)} — {', '.join(sorted(new_in_v2))}")
print(f"  Boosted in v2: {len(boosted)}")
print(f"  Unchanged: {len(unchanged)}")

# Score both
axes = ["longevity", "sillage", "synergy", "luxury", "texture",
        "stacking_depth", "skin_performance", "hedonic", "perceptual_clarity", "photorealism"]

scorer = FormulaScorer()
fam = FamilyAwareScorer()

v1_fv = FormulaVector(ingredients=v1_pct, dilutions=v1_dil)
v2_fv = FormulaVector(ingredients=v2_pct, dilutions=v2_dil)

v1_scores = scorer.score(v1_fv)
v2_scores = scorer.score(v2_fv)

v1_fam = fam.score(v1_fv, family="fougere")
v2_fam = fam.score(v2_fv, family="fougere")

print(f"\n{DIV}")
print(f"  {'Axis':<22} {'v1 Generic':>12} {'v2 Generic':>12} {'Delta':>10} {'v1 Fougere':>12} {'v2 Fougere':>12} {'Delta':>10}")
print(f"  {'-'*22} {'-'*12} {'-'*12} {'-'*10} {'-'*12} {'-'*12} {'-'*10}")

for ax in axes:
    g1 = v1_scores.get(ax, 0)
    g2 = v2_scores.get(ax, 0)
    f1 = v1_fam.get(ax, 0)
    f2 = v2_fam.get(ax, 0)
    dg = g2 - g1
    df = f2 - f1
    gsign = "+" if dg > 0 else ""
    fsign = "+" if df > 0 else ""
    print(f"  {ax:<22} {g1:>12.1f} {g2:>12.1f} {gsign}{dg:>9.1f} {f1:>12.1f} {f2:>12.1f} {fsign}{df:>9.1f}")

geo1 = v1_scores.get("geometric_total", 0)
geo2 = v2_scores.get("geometric_total", 0)
geo1f = v1_fam.get("geometric_total", 0)
geo2f = v2_fam.get("geometric_total", 0)

print(f"\n  {'Geometric composite':<22} {geo1:>12.1f} {geo2:>12.1f} {'+' if geo2>geo1 else ''}{geo2-geo1:>9.1f} {geo1f:>12.1f} {geo2f:>12.1f} {'+' if geo2f>geo1f else ''}{geo2f-geo1f:>9.1f}")

# Gates for v2
print(f"\n{DIV}")
print("  v2 GATE REPORT")
print(DIV)

try:
    formula_dict = {
        "ingredients_ul": v2_ing,
        "dilutions": v2_dil,
        "family_archetype": "aromatic_fougere.modern_mineral",
    }
    report = gate_formula(formula_dict)
    failures = [g for g in report.gates if g.status == "FAIL"]
    warnings = [g for g in report.gates if g.status == "WARN"]
    passes = [g for g in report.gates if g.status == "PASS"]
    print(f"  STATUS: {report.status} ({len(passes)}P / {len(warnings)}W / {len(failures)}F)")
    if failures:
        print("  FAILURES:")
        for g in failures:
            print(f"    [{g.status}] {g.gate:<30} {str(g.detail)[:100]}")
    if warnings:
        print("  WARNINGS:")
        for g in warnings:
            print(f"    [{g.status}] {g.gate:<30} {str(g.detail)[:100]}")
except Exception as e:
    print(f"  [ERROR] {e}")

print(f"\n{SEP}")
print("  COMPARISON COMPLETE")
print(SEP)
