"""science_audit — print known weaknesses, missing data, validation status.

Run:
    python -m engine.science_audit
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "materials"


def _gather_data_coverage() -> dict[str, float]:
    """Mirror engine.data_spine.audit using the live Material schema."""
    try:
        from engine.data_spine.loader import load_materials
    except Exception:
        return {}

    materials = load_materials(DATA)
    if not materials:
        return {}

    fields = [
        "mw", "logp", "vp_25c", "antoine", "dhvap", "hsp",
        "odt_air", "or_targets", "ifra", "hedonic", "trp", "smiles", "cas",
    ]
    counts = {field: 0 for field in fields}
    for material in materials:
        completeness = material.completeness()
        for field in fields:
            if completeness.get(field):
                counts[field] += 1

    total = len(materials)
    return {field: 100.0 * count / total for field, count in counts.items()}


def build_science_audit_contract() -> dict:
    """Return the machine-readable science audit contract."""
    cov = _gather_data_coverage()
    return {
        "data_coverage_pct": cov,
        "weaknesses": [{"title": t, "body": b} for t, b in KNOWN_WEAKNESSES],
        "open_questions": OPEN_QUESTIONS,
    }


def coverage_confidence_penalty(contract: dict | None = None) -> float:
    """Convert sparse science coverage into a bounded confidence penalty.

    This is intentionally conservative. It should lower trust, not fabricate
    a hard-fail from incomplete auxiliary science fields.
    """
    contract = contract or build_science_audit_contract()
    coverage = contract.get("data_coverage_pct", {}) or {}
    penalty = 0.0
    targets = {
        "antoine": 20.0,
        "hsp": 40.0,
        "ifra": 50.0,
        "or_targets": 10.0,
    }
    for field, target in targets.items():
        actual = float(coverage.get(field, 0.0) or 0.0)
        if actual < target:
            penalty += min(3.0, (target - actual) / max(target, 1.0) * 3.0)
    return round(min(12.0, penalty), 3)


KNOWN_WEAKNESSES = [
    ("Antoine constants",
     "0% of materials have Antoine A/B/C. Phase 1 falls back to single-point VP_25 → "
     "VP(T) extrapolation is wrong above 40 °C and at the cold-tail."),
    ("UNIFAC γ",
     "thermo.unifac integration is stubbed. Activity coefficients use a Hansen-distance "
     "regular-solution heuristic calibrated only to limonene-in-EtOH."),
    ("OR targets",
     "0% of materials have published EC50/Hill coefficients. Receptor occupancy uses a "
     "family→OR-affinity prior. Mainland 2014 dataset not yet ingested."),
    ("Hedonic / TRP / IFRA",
     "Coverage <10%. Ferreira mixture-shift β=0.3 is hard-coded, not fitted."),
    ("Adaptation timescales",
     "τ_fast / τ_med / τ_slow values from rat single-cell studies. Human bulb-level "
     "feedback may differ by 2-3×."),
    ("Maturation kinetics",
     "Arrhenius A/Ea per reaction class are order-of-magnitude calibrated to one Blakeway "
     "1987 reference. Per-aldehyde overrides not yet supplied."),
    ("Spray atomisation",
     "Log-normal Dv50=30 µm σ_g=1.5 is the typical perfume-atomiser literature value, "
     "not measured for any specific bottle."),
    ("OR polymorphism coverage",
     "Only OR7D4 / OR5A1 / OR11H7 SNPs encoded. ~400 ORs × 3 variants = ~1200 alleles "
     "remain unmodeled."),
]

OPEN_QUESTIONS = [
    "Should mixture-shift β be material-pair-specific?",
    "Is Stevens' law (per-OR exponent) or Weber–Fechner (log) the better default for "
    "supra-threshold perception?",
    "How to weight retronasal vs orthonasal in the optimizer when the brief is for skin "
    "fragrance, not flavour?",
    "Lateral-inhibition kernel: ring-uniform vs structural-similarity-weighted?",
    "Granularity of OR families: 8 abstract groups (current) vs full 396-locus model?",
]


def main():
    cov = _gather_data_coverage()
    print("=" * 60)
    print("perfume-chem science audit")
    print("=" * 60)
    print("\nData coverage (% of materials with field filled):")
    for k, v in sorted(cov.items()):
        print(f"  {k:14s} {v:6.1f}%")
    print("\nKnown weaknesses:")
    for title, body in KNOWN_WEAKNESSES:
        print(f"\n  • {title}")
        print(f"    {body}")
    print("\nOpen questions:")
    for q in OPEN_QUESTIONS:
        print(f"  ? {q}")
    print()
    # External-AI feedback contract
    contract = build_science_audit_contract()
    out_path = ROOT / "verification_runs" / "science_audit.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    print(f"Wrote machine-readable contract → {out_path}")


if __name__ == "__main__":
    main()
