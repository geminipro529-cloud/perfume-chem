"""Intervention Simulator — what-if engine for formula changes.
Apply a delta to a formula, re-run the pipeline, return predicted scores."""

from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_formula(path: str) -> dict:
    """Load a formula markdown and return the parsed record."""
    from scripts.verify_formula_workflow import parse_formula_markdown

    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    formulas = parse_formula_markdown(p)
    if not formulas:
        raise ValueError(f"No formulas found in {path}")
    return formulas[0]


def apply_delta(formula: dict, deltas: dict[str, float]) -> dict:
    """Apply material deltas (in uL) to a formula record.

    deltas = {"Bergamot FCF": -120, "Kephalis": +240}
    Positive = add, Negative = remove/reduce.
    """
    f = copy.deepcopy(formula)
    ings = dict(f["ingredients_ul"])
    dils = dict(f.get("dilutions", {}))

    for mat, delta_ul in deltas.items():
        current = ings.get(mat, 0.0)
        new_val = max(0.0, current + delta_ul)
        if new_val > 0:
            ings[mat] = new_val
            if mat not in dils:
                dils[mat] = 1.0
        else:
            ings.pop(mat, None)
            dils.pop(mat, None)

    # Recalculate percentages
    total_ul = sum(ings.values()) or 1.0
    f["ingredients_ul"] = ings
    f["dilutions"] = dils
    f["ingredients_pct"] = {m: round(ul / total_ul * 100, 4) for m, ul in ings.items()}
    return f


def simulate(formula: dict, deltas: dict[str, float] = None) -> dict:
    """Run the full pipeline on a formula, optionally with deltas."""
    if deltas:
        formula = apply_delta(formula, deltas)

    from engine.optimizer.models import FormulaVector, ObjectiveWeights
    from engine.optimizer.scoring import FormulaScorer
    from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority

    ings = formula["ingredients_ul"]
    dils = formula.get("dilutions", {})

    # OAV
    req = OAVAuthorityRequest(
        formula_name=formula.get("name", "Simulation"),
        ingredients_ul=ings,
        dilutions=dils,
        batch_volume_ml=30.0,
        temperature_K=305.0,
    )
    oav = analyze_oav_authority(req)

    # Scoring
    total_ul = sum(ings.values()) or 1.0
    pct = {n: (ul * dils.get(n, 1.0) / total_ul) * 100 for n, ul in ings.items()}
    fv = FormulaVector(ingredients=pct)
    scorer = FormulaScorer(ObjectiveWeights())
    scorer._material_oavs = {m.name: (m.oav or 0) for m in oav.state.materials}
    scores = scorer.score(fv)

    # Industry scores

    percept = [m for m in oav.state.materials if (m.oav or 0) >= 1.0]
    total_oav = sum(m.oav or 0 for m in percept) or 1
    base_oav = sum(m.oav or 0 for m in percept if m.note in ("base", "heart"))
    top_oav = sum(m.oav or 0 for m in percept if m.note == "top")
    tenacity = min(100, base_oav / total_oav * 150)
    lift = min(100, top_oav / total_oav * 100)
    impact = min(100, math.log10(total_oav + 1) * 12)
    diffusion = min(100, len(percept) * 6 + 10)
    w = oav.time_windows
    leaders = set()
    for window in w:
        for leader in window.dominant_oav[:1]:
            leaders.add(leader["material"])
    bloom = min(100, len(leaders) * 20)

    return {
        "scores": {k: v for k, v in scores.items() if isinstance(v, (int, float))},
        "industry": {
            "impact": round(impact, 1),
            "tenacity": round(tenacity, 1),
            "diffusion": round(diffusion, 1),
            "bloom": round(bloom, 1),
            "lift": round(lift, 1),
        },
        "perceptible": len(percept),
        "total_vapor": round(oav.state.total_vapor_ppm, 1),
    }


def _feasibility(
    before: dict, after: dict, deltas: dict, raw_deltas: dict | None = None
) -> list[dict]:
    """Check if the predicted changes are physically feasible."""
    flags = []

    # Check tenacity improvement
    b_ten = before.get("industry", {}).get("tenacity", 0)
    a_ten = after.get("industry", {}).get("tenacity", 0)
    ten_delta = a_ten - b_ten

    if b_ten < 15 and ten_delta < 10:
        freed = 0
        added = 0
        if raw_deltas:
            for mat, ul in raw_deltas.items():
                if ul < 0:
                    freed += abs(ul)
                if ul > 0:
                    added += ul

        if freed > 0:
            flags.append(
                {
                    "feasibility": "INFO" if freed > 400 else "LOW",
                    "axis": "tenacity",
                    "message": f"Freed {freed:.0f} uL from top notes, added {added:.0f} uL to base",
                    "suggestion": f"Tenacity improved by {ten_delta:.1f} points. Need ~{max(0, 30 - b_ten):.0f} more points for target. {'Consider 2x more aggressive reduction' if freed < 500 else 'Good progress — continue iterating'}",
                }
            )

    # Check lift reduction
    b_lift = before.get("industry", {}).get("lift", 0)
    a_lift = after.get("industry", {}).get("lift", 0)
    lift_delta = b_lift - a_lift

    if b_lift > 80 and lift_delta < 10:
        flags.append(
            {
                "feasibility": "MEDIUM",
                "axis": "lift",
                "message": f"Lift dropped only {lift_delta:.1f} points (was {b_lift:.0f}, now {a_lift:.0f})",
                "suggestion": "Top notes OAV dominance is structural, not dose-based. Need fundamental rebalance",
            }
        )

    # Perceptibility change
    b_perc = before.get("perceptible", 0)
    a_perc = after.get("perceptible", 0)
    if a_perc > b_perc:
        flags.append(
            {
                "feasibility": "INFO",
                "axis": "perceptible",
                "message": f"Gained {a_perc - b_perc} new perceptible material(s) (now {a_perc})",
            }
        )

    return flags


def compare(before: dict, after: dict, raw_deltas: dict | None = None) -> dict:
    """Compare two simulation results with feasibility analysis."""
    deltas = {}
    for k in before.get("industry", {}):
        b = before["industry"].get(k, 0)
        a = after["industry"].get(k, 0)
        deltas[k] = round(a - b, 1)
    for k in ["total", "synergy", "sillage", "longevity", "texture", "stacking_depth"]:
        b = before.get("scores", {}).get(k, 0)
        a = after.get("scores", {}).get(k, 0)
        deltas[k] = round(a - b, 1)

    feasibility = _feasibility(before, after, deltas, raw_deltas)

    return {
        "before": before,
        "after": after,
        "deltas": deltas,
        "feasibility": feasibility,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scripts/formula_simulator.py <formula.md> [delta.json]")
        sys.exit(1)

    from engine.formula_metadata import parse_formula_metadata

    meta = parse_formula_metadata(sys.argv[1])
    if not meta.has_metadata() and not meta.is_unclaimed():
        print("ERROR: Formula missing metadata block.", file=sys.stderr)
        sys.exit(1)

    formula = load_formula(sys.argv[1])
    deltas = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}

    result = simulate(formula, deltas)
    if deltas:
        base = simulate(formula)
        result = compare(base, result, deltas)

    print(json.dumps(result, indent=2))
