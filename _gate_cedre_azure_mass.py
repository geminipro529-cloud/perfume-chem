"""Gate-check the mass-market Cedre Azure variant (pre-optimizer)."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.pipeline.gates import gate_formula, ReleaseGateConfig
from _opt_cedre_azure_mass_market import MASS_MARKET_UL, MASS_MARKET_DILUTIONS

total_ul = sum(MASS_MARKET_UL.values())

gate_dilutions = {}
for mat, v in MASS_MARKET_DILUTIONS.items():
    if mat in MASS_MARKET_UL:
        gate_dilutions[mat] = v

formula = {
    "name": "Cedre Azure — Mass-Market",
    "number": 1,
    "body": (
        "Mass-market blue aromatic woody fougere targeting Sauvage/BdC territory. "
        "Bergamot + Black Pepper sparkle. Ambroxan projection. Simplified wood base "
        "(Polysantol/Azarbre/Vertofix removed). Trace Ethyl Maltol."
    ),
    "family_archetype": "aromatic_fougere.modern_mineral",
    "ingredients_ul": MASS_MARKET_UL,
    "dilutions": gate_dilutions,
}

config = ReleaseGateConfig(
    expected_concentrate_ul=total_ul,
    batch_volume_ml=30.0,
    brief="auto",
    family_archetype="aromatic_fougere.modern_mineral",
    allow_preblends=True,
    commercial_mode=False,
    audit_enabled=False,
)

print(f"\n{'='*70}")
print(f"  Cedre Azure — MASS-MARKET GATES")
print(f"  {len(MASS_MARKET_UL)} materials, {total_ul:.0f} uL concentrate")
print(f"{'='*70}\n")

report = gate_formula(formula, config)

print(f"Overall status: {report.status}")
print(f"Commercial readiness: {report.commercial_readiness}")
print(f"\n--- Gate Results ({len(report.gates)} gates) ---\n")

fail_count = warn_count = pass_count = 0
for gate in report.gates:
    label = f"[{gate.status}]"
    print(f"{label:<8} {gate.gate:<42} {gate.detail[:140]}")
    if gate.status == "FAIL":
        fail_count += 1
    elif gate.status == "WARN":
        warn_count += 1
    else:
        pass_count += 1

print(f"\n--- Summary: {pass_count} PASS, {warn_count} WARN, {fail_count} FAIL ---")

if fail_count > 0:
    print(f"\n=== FAIL DETAILS ===")
    for gate in report.gates:
        if gate.status == "FAIL":
            print(f"\nFAIL: {gate.gate}")
            print(gate.detail)
            if gate.data:
                import json
                print(json.dumps(gate.data, indent=2, default=str))
