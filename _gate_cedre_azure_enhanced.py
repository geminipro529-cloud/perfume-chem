"""Gate-check original Cedre Azure + proposed enhancement additions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.pipeline.gates import gate_formula, ReleaseGateConfig

# --- Original Cedre Azure (34 materials, 5920 uL) ---
ORIGINAL_INGREDIENTS: dict[str, float] = {
    "Iso E Super": 850,
    "Ambrofix": 800,
    "Cedarwood Virginia": 400,
    "Galaxolide": 380,
    "Sandalore": 350,
    "Ethylene Brassylate": 230,
    "Habanolide": 220,
    "Ebanol": 210,
    "Cashmeran": 200,
    "Benzoin Resinoid": 200,
    "Vetiver EO": 200,
    "Polysantol": 120,
    "Patchouli EO": 30,
    "Vertofix": 25,
    "Azarbre": 80,
    "Timberol": 80,
    "Olibanum Resinoid": 50,
    "Norlimbanol Dextro": 25,
    "Evernyl": 15,
    "Nagarmotha Oil": 15,
    "Hedione": 200,
    "Hedione HC": 30,
    "Lavender EO": 100,
    "Geraniol": 125,
    "Coumarin": 60,
    "Cedrat FCF Sicilian": 380,
    "Lime Distilled EO": 145,
    "Dihydromyrcenol": 100,
    "Beta-Pinene": 90,
    "Floralozone": 80,
    "Linalyl Acetate": 50,
    "Aldehyde C11 undecylenic": 40,
    "Methyl Pamplemousse": 30,
    "Scentenal": 10,
}

ORIGINAL_DILUTIONS: dict[str, float] = {
    "Benzoin Resinoid": 0.50,
    "Ambrofix": 0.30,
    "Coumarin": 0.20,
    "Olibanum Resinoid": 0.10,
    "Methyl Pamplemousse": 0.10,
    "Floralozone": 0.10,
    "Aldehyde C11 undecylenic": 0.01,
    "Scentenal": 0.01,
}

# --- Enhanced Cedre Azure (+ Javanol, Damascenone, Ambrettolide, Clary Sage, Kephalis) ---
ENHANCED_INGREDIENTS = dict(ORIGINAL_INGREDIENTS)
ENHANCED_INGREDIENTS.update({
    "Javanol": 40,
    "Damascenone": 15,
    "Ambrettolide": 40,
    "Clary Sage EO": 60,
    "Kephalis": 50,
    # Reduce Geraniol slightly to make room
    "Geraniol": 100,  # was 125
    # Bump Coumarin to keep active > 0.200% threshold (12/6100 = 0.197% -> fail)
    "Coumarin": 62,  # was 60; 12.4/6102 = 0.203%
})

ENHANCED_DILUTIONS = dict(ORIGINAL_DILUTIONS)
ENHANCED_DILUTIONS.update({
    "Damascenone": 0.01,
    "Ambrettolide": 0.10,
})


def run_gates(name: str, ingredients: dict, dilutions: dict, conc_ul: float) -> None:
    formula = {
        "name": name,
        "number": 1,
        "body": (
            "Blue-family aromatic woody fougere. "
            "Citrus-zest top, creamy sandalwood heart, incense-amber depth, "
            "Ambroxan-driven projection."
        ),
        "family_archetype": "aromatic_fougere.modern_mineral",
        "ingredients_ul": ingredients,
        "dilutions": dilutions,
    }

    config = ReleaseGateConfig(
        expected_concentrate_ul=conc_ul,
        batch_volume_ml=30.0,
        brief="auto",
        family_archetype="aromatic_fougere.modern_mineral",
        allow_preblends=True,
        commercial_mode=False,
        audit_enabled=False,
    )

    print(f"\n{'='*70}")
    print(f"  {name}")
    print(f"  Materials: {len(ingredients)} | Concentrate: {conc_ul} µL")
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
    print(f"\n--- Confidence ---")
    print(json.dumps(report.confidence, indent=2))

    if fail_count > 0:
        print(f"\n=== FAIL DETAILS ===")
        for gate in report.gates:
            if gate.status == "FAIL":
                print(f"\nFAIL: {gate.gate}")
                print(gate.detail)
                if gate.data:
                    print(json.dumps(gate.data, indent=2, default=str))


def main() -> None:
    # Gate the original
    run_gates(
        "Cedre Azure — ORIGINAL (34 materials, 5920 µL)",
        ORIGINAL_INGREDIENTS,
        ORIGINAL_DILUTIONS,
        5920.0,
    )

    # Gate the enhanced version
    run_gates(
        "Cedre Azure — ENHANCED (39 materials, 6102 µL)",
        ENHANCED_INGREDIENTS,
        ENHANCED_DILUTIONS,
        6102.0,
    )

    print(f"\n{'='*70}")
    print("  COMPARISON SUMMARY")
    print(f"{'='*70}")
    print(f"  Original:  34 mats, 5,920 µL concentrate")
    print(f"  Enhanced:  39 mats, 6,102 µL concentrate")
    print(f"  Added:      Javanol 40, Damascenone 1% 15, Ambrettolide 10% 40,")
    print(f"              Clary Sage EO 60, Kephalis 50")
    print(f"  Changed:    Geraniol 125 -> 100 uL (-25), Coumarin 20% 60 -> 62 uL (+2)")
    print(f"  Net delta:  +182 uL (+3.1% of concentrate)")


if __name__ == "__main__":
    main()
