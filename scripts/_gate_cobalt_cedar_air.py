"""Run release gates on optimized Cobalt Cedar Air formula."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.pipeline.gates import ReleaseGateConfig, gate_formula

INGREDIENTS_UL: dict[str, float] = {
    "Iso E Super": 850,
    "Ambrofix": 800,
    "Cedarwood Virginia": 400,
    "Cedrat FCF Sicilian": 380,
    "Galaxolide": 380,
    "Sandalore": 350,
    "Ethylene Brassylate": 230,
    "Habanolide": 220,
    "Ebanol": 210,
    "Hedione": 200,
    "Vetiver EO": 200,
    "Cashmeran": 200,
    "Benzoin Resinoid": 200,
    "Patchouli EO": 30,
    "Lime Distilled EO": 145,
    "Polysantol": 120,
    "Geraniol": 125,
    "Dihydromyrcenol": 100,
    "Lavender EO": 100,
    "Beta-Pinene": 90,
    "Floralozone": 80,
    "Timberol": 80,
    "Azarbre": 80,
    "Coumarin": 60,
    "Linalyl Acetate": 50,
    "Olibanum Resinoid": 50,
    "Aldehyde C11 undecylenic": 40,
    "Methyl Pamplemousse": 30,
    "Hedione HC": 30,
    "Norlimbanol Dextro": 25,
    "Vertofix": 25,
    "Evernyl": 15,
    "Nagarmotha Oil": 15,
    "Scentenal": 10,
}

DILUTIONS: dict[str, float] = {
    "Benzoin Resinoid": 0.50,
    "Ambrofix": 0.30,
    "Coumarin": 0.20,
    "Olibanum Resinoid": 0.10,
    "Methyl Pamplemousse": 0.10,
    "Floralozone": 0.10,
    "Aldehyde C11 undecylenic": 0.01,
    "Scentenal": 0.01,
}

def main() -> None:
    formula = {
        "name": "Cobalt Cedar Air - Optimized v2",
        "number": 1,
        "body": "Blue-family aromatic woody fougere. Citrus-zest top, creamy sandalwood heart, incense-amber depth, Ambroxan-driven projection. Re-optimized after Aliztar preblend removal. Added Beta-Pinene and Vertofix for subtle pine-woody distinction.",
        "family_archetype": "aromatic_fougere.modern_mineral",
        "ingredients_ul": INGREDIENTS_UL,
        "dilutions": DILUTIONS,
    }

    config = ReleaseGateConfig(
        expected_concentrate_ul=5920.0,
        batch_volume_ml=30.0,
        brief="auto",
        family_archetype="aromatic_fougere.modern_mineral",
        allow_preblends=True,
        commercial_mode=False,
        audit_enabled=False,
    )

    print("Running formula through release gates...\n")
    report = gate_formula(formula, config)

    print(f"Overall status: {report.status}")
    print(f"Formula hash: {report.formula_hash}")
    print(f"Commercial readiness: {report.commercial_readiness}")
    print(f"\n--- Gate Results ({len(report.gates)} gates) ---\n")

    fail_count = 0
    warn_count = 0
    pass_count = 0

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
    print("\n--- Confidence ---")
    print(json.dumps(report.confidence, indent=2))

    for gate in report.gates:
        if gate.status == "FAIL":
            print(f"\nFAIL detail for '{gate.gate}':")
            print(gate.detail)
            if gate.data:
                print(json.dumps(gate.data, indent=2, default=str))

if __name__ == "__main__":
    main()
