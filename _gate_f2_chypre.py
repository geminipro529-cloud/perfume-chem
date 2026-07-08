"""Gate-check F2 optimized formula — robust version."""
import json
import io
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.pipeline.gates import gate_formula, ReleaseGateConfig

# Fix stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Load optimized recipe
opt = json.loads(Path("_opt_f2_chypre_vert_out.json").read_text(encoding="utf-8"))
wt_pct = opt["optimized"]["recipe_wt_pct"]
CONCENTRATE_UL = 6000.0

# Material name fixups for registry matching
REGISTRY_NAMES = {
    "Phenethyl Alcohol (PEA)": "Phenethyl Alcohol",
    "p-Cresyl Methyl Ether (PCME)": "p-Cresyl Methyl Ether (PCME)",  # keep, handled by gate
}

ingredients_ul = {}
for mat, wt in wt_pct.items():
    canonical = REGISTRY_NAMES.get(mat, mat)
    ingredients_ul[canonical] = round(wt * CONCENTRATE_UL / 100.0, 1)

DILUTIONS = {
    "Ambrofix": 0.3,
    "Galaxolide": 0.8,
    "Coumarin": 0.2,
    "Ambrettolide": 0.1,
    "Damascol": 0.1,
    "p-Cresyl Methyl Ether (PCME)": 0.1,
    "Alpha Damascone": 0.1,
    "Galbanum Resinoid": 0.1,
    "Labdanum Absolute": 0.1,
    "Aldehyde C12 MNA": 0.01,
}
dilutions = {}
for mat in ingredients_ul:
    dilutions[mat] = DILUTIONS.get(mat, 1.0)

formula = {
    "name": "F2 — Le Chypre Vert · Green Chypre Luxury (Optimized)",
    "number": 2,
    "family_archetype": "Green Chypre",
    "ingredients_ul": ingredients_ul,
    "dilutions": dilutions,
}

config = ReleaseGateConfig(
    expected_concentrate_ul=CONCENTRATE_UL,
    batch_volume_ml=30.0,
    brief="Modern green chypre — luxury, depth, texture, performance, mass-market. Labdanum-warmed, galbanum-green axis through all stages. Cristalle / No.19 lineage.",
    family_archetype="Green Chypre",
    commercial_mode=False,
    min_confidence_score=25.0,
)

print("Running 22 release gates...")
try:
    report = gate_formula(formula, config)
except Exception as e:
    print(f"ERROR during gate_formula: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n{'='*60}")
print(f"GATE REPORT: {report.name}")
print(f"Status: {report.status}")
print(f"Commercial Readiness: {report.commercial_readiness}")
cf = report.confidence
if isinstance(cf, dict):
    print(f"Combined Confidence: {cf.get('combined_confidence', 'N/A'):.1f}  Grade: {cf.get('combined_grade', 'N/A')}")
print(f"{'='*60}")

fail_count = 0
warn_count = 0
pass_count = 0

for gate in report.gates:
    symbol = {"PASS": "  [PASS]", "WARN": "  [WARN]", "FAIL": "**[FAIL]**"}.get(gate.status, gate.status)
    # Truncate detail safely
    detail = str(gate.detail)
    if len(detail) > 250:
        detail = detail[:250] + "..."
    print(f"\n{symbol} {gate.gate}")
    if gate.status != "PASS":
        print(f"         {detail}")
    if gate.status == "FAIL":
        fail_count += 1
    elif gate.status == "WARN":
        warn_count += 1
    else:
        pass_count += 1

print(f"\n{'='*60}")
print(f"SUMMARY: {pass_count} PASS, {warn_count} WARN, {fail_count} FAIL")
print(f"Overall: {report.status}")
print(f"Commercial Tier: {report.commercial_readiness}")
