"""Constrained optimizer for Cobalt Cedar Air (Bleu de Chanel-class).

Optimizes along 6 user-requested axes — mass-market (hedonic proxy), luxury,
depth (stacking_depth), texture, longevity, projection (sillage) — while
keeping total drift < 0.25 mL so the smell character is preserved.
"""
from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.optimizer.models import FormulaVector, ObjectiveWeights
from engine.optimizer.scoring import FormulaScorer

SOURCE_PATH = PROJECT_ROOT / "formulas" / "Cobalt_Cedar_Air_30mL_EDP.md"
OUTPUT_PATH = PROJECT_ROOT / "formulas" / "Cobalt_Cedar_Air_30mL_EDP_Optimized.md"

CONCENTRATE_UL = 5920          # total concentrate µL (post Black Pepper FTEC removal, coumarin/floralozone additions)
CONCENTRATE_ML = CONCENTRATE_UL / 1000.0
ETHANOL_ML = 30.0 - CONCENTRATE_ML

STEP_OPTIONS = (0.025, 0.050)   # mL  (= 25 µL, 50 µL)
MAX_DRIFT_ML = 0.25              # ~4.2 % of concentrate — smell-preservation guardrail
MIN_AMOUNT_ML = 0.0
MIN_NONZERO_ML = 0.015
MAX_ITERATIONS = 15

# Locked materials: neither give nor receive during optimization
LOCKED_MATERIALS = {
    "Dihydromyrcenol",    # user saving for sport cologne project
    "Methyl Salicylate",  # already removed, just in case
}

# Custom weights: longevity, projection, smell
CUSTOM_WEIGHTS = ObjectiveWeights(
    longevity=1.0,              # core target
    sillage=1.0,                # projection = core target
    luxury=0.3,
    texture=0.3,
    stacking_depth=0.3,
    hedonic=1.0,                # smell / crowd-pleasing appeal
    synergy=0.2,
    skin_performance=1.0,       # skin kinetics = longevity contributor
    perceptual_clarity=0.5,     # smell clarity / no muddled notes
    photorealism=0.2,
)

SCORER = FormulaScorer(weights=CUSTOM_WEIGHTS, batch_volume_ml=30.0)

AXES = (
    "longevity",
    "sillage",
    "luxury",
    "texture",
    "stacking_depth",
    "hedonic",
    "synergy",
    "skin_performance",
    "perceptual_clarity",
    "photorealism",
)


@dataclass
class OptimizationResult:
    name: str
    original_scores: dict[str, float]
    optimized_scores: dict[str, float]
    original_ml: dict[str, float]
    optimized_ml: dict[str, float]
    history: list[str]


def parse_formula(path: Path) -> dict[str, float]:
    """Extract {material: mL} from the formula reference table."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Find the "Formula Table (Reference)" header, then parse every |...| line after it
    in_table = False
    amounts: dict[str, float] = {}
    for line in lines:
        if "Formula Table (Reference)" in line:
            in_table = True
            continue
        if not in_table:
            continue
        if not line.strip():
            continue  # skip blank lines between header and table
        if not line.strip().startswith("|"):
            break  # end of table
        parts = [p.strip() for p in line.split("|")]
        # Typical row: ['', 'Layer', '#', 'Material', 'Dilution', 'µL', '']
        if len(parts) < 6:
            continue
        material = parts[3].replace("**", "").strip()
        if not material or material.lower() in {"material", "total"}:
            continue
        try:
            ul = int(parts[5].replace(",", "").replace("**", "").replace(" ", "").strip())
        except ValueError:
            continue
        # Merge Iso E Super (heart) and (base)
        if material.lower().startswith("iso e super"):
            key = "Iso E Super"
        else:
            key = material
        amounts[key] = amounts.get(key, 0.0) + ul / 1000.0

    if not amounts:
        raise ValueError("Could not find formula table")
    return amounts


def infer_dilution(name: str) -> float:
    """Infer stock dilution from name or known catalog."""
    explicit = re.search(r"(\d+(?:\.\d+)?)\s*%", name)
    if explicit:
        return float(explicit.group(1)) / 100.0
    # Hard-coded overrides for materials whose names don't carry %
    if name == "Aldehyde C11 undecylenic":
        return 0.01
    if name == "Benzoin Resinoid":
        return 0.50
    if name == "Ambrox Super":
        return 0.30
    if name == "Ambrofix":
        return 0.30
    if name == "Methyl Pamplemousse":
        return 0.10
    if name == "Coumarin":
        return 0.20
    if name == "Floralozone":
        return 0.10
    if name == "Scentenal":
        return 0.01
    if name == "Olibanum Resinoid":
        return 0.10
    return 1.0


def build_fv(amounts_ml: dict[str, float]) -> FormulaVector:
    ingredients: dict[str, float] = {}
    dilutions: dict[str, float] = {}
    for mat, ml in amounts_ml.items():
        if ml <= 1e-9:
            continue
        pct = (ml / CONCENTRATE_ML) * 100.0
        ingredients[mat] = round(pct, 4)
        dil = infer_dilution(mat)
        if dil != 1.0:
            dilutions[mat] = dil
    return FormulaVector(ingredients=ingredients, dilutions=dilutions)


def drift_from_original(current: dict[str, float], original: dict[str, float]) -> float:
    keys = set(current) | set(original)
    return round(sum(abs(current.get(k, 0.0) - original.get(k, 0.0)) for k in keys), 3)


def signature(amounts: dict[str, float]) -> tuple[tuple[str, float], ...]:
    return tuple(sorted((n, round(v, 4)) for n, v in amounts.items() if v > 1e-9))


@lru_cache(maxsize=8192)
def _cached_score(sig: tuple[tuple[str, float], ...]) -> dict[str, float]:
    amounts = {n: v for n, v in sig}
    fv = build_fv(amounts)
    scores: dict[str, float] = {}
    for axis in AXES:
        scores[axis] = SCORER.score_axis(fv, axis)

    weights = SCORER.weights.as_dict()
    total_w = sum(weights.get(a, 0.0) for a in AXES) or 1.0
    log_sum = 0.0
    for a in AXES:
        w = weights.get(a, 0.0)
        if w <= 0:
            continue
        log_sum += (w / total_w) * math.log(max(scores[a], 1.0))

    scores["geometric_total"] = round(math.exp(log_sum), 1)
    scores["arithmetic_total"] = round(
        sum(scores[a] * weights.get(a, 0.0) for a in AXES) / total_w, 1
    )
    scores["total"] = scores["geometric_total"]
    return scores


def score_amounts(amounts: dict[str, float]) -> dict[str, float]:
    return _cached_score(signature(amounts))


def candidate_key(scores: dict[str, float], *, drift: float) -> tuple:
    return (
        round(scores["total"], 3),
        round(scores["longevity"], 2),
        round(scores["sillage"], 2),
        round(scores["hedonic"], 2),
        round(scores["skin_performance"], 2),
        round(scores["perceptual_clarity"], 2),
        -round(drift, 3),
    )


def optimize(amounts: dict[str, float]) -> OptimizationResult:
    original = dict(amounts)
    # Only consider materials with meaningful mass for shifting
    all_mats = sorted(original, key=lambda m: -original[m])
    # Givers: large materials only (>40 µL), exclude locked
    givers = [m for m in all_mats if original[m] > 0.040 and m not in LOCKED_MATERIALS]
    # Receivers: all materials, exclude locked
    receivers = [m for m in all_mats if m not in LOCKED_MATERIALS]
    mats = all_mats  # for iteration display

    history: list[str] = []

    # Try each of the top candidate starting states from previous runs
    current = dict(original)
    current_scores = score_amounts(current)

    for it in range(MAX_ITERATIONS):
        best_candidate: dict[str, float] | None = None
        best_scores: dict[str, float] | None = None
        best_giver = ""
        best_receiver = ""
        best_delta = 0.0

        drift = drift_from_original(current, original)
        curr_key = candidate_key(current_scores, drift=drift)

        for giver in givers:
            giver_amt = current.get(giver, 0.0)
            if giver_amt <= MIN_AMOUNT_ML + 1e-9:
                continue
            for receiver in receivers:
                if giver == receiver:
                    continue
                for delta in STEP_OPTIONS:
                    if giver_amt - delta < MIN_AMOUNT_ML - 1e-9:
                        continue
                    cand = dict(current)
                    cand[giver] = round(cand.get(giver, 0.0) - delta, 4)
                    cand[receiver] = round(cand.get(receiver, 0.0) + delta, 4)
                    if 0.0 < cand[giver] < MIN_NONZERO_ML:
                        continue
                    cand = {k: round(v, 4) for k, v in cand.items() if v > 1e-9}
                    cand_drift = drift_from_original(cand, original)
                    if cand_drift > MAX_DRIFT_ML:
                        continue
                    sc = score_amounts(cand)
                    key = candidate_key(sc, drift=cand_drift)
                    if key <= curr_key:
                        continue
                    if best_scores is None or key > candidate_key(
                        best_scores, drift=drift_from_original(best_candidate or {}, original)
                    ):
                        best_candidate = cand
                        best_scores = sc
                        best_giver = giver
                        best_receiver = receiver
                        best_delta = delta

        if best_candidate is None or best_scores is None:
            break

        history.append(
            f"Iter {it+1}: shifted {best_delta:.3f} mL from {best_giver} → {best_receiver}  "
            f"(total {current_scores['total']:.1f} → {best_scores['total']:.1f},  "
            f"longevity {current_scores['longevity']:.1f} → {best_scores['longevity']:.1f},  "
            f"sillage {current_scores['sillage']:.1f} → {best_scores['sillage']:.1f})"
        )
        current = best_candidate
        current_scores = best_scores

    return OptimizationResult(
        name="Cobalt Cedar Air",
        original_scores=score_amounts(original),
        optimized_scores=current_scores,
        original_ml=original,
        optimized_ml=current,
        history=history,
    )


def summarize_shift(original: dict[str, float], optimized: dict[str, float]) -> str:
    deltas = []
    for mat in sorted(set(original) | set(optimized)):
        d = round(optimized.get(mat, 0.0) - original.get(mat, 0.0), 3)
        if abs(d) >= 0.015:
            deltas.append((abs(d), mat, d))
    deltas.sort(reverse=True)
    parts = []
    for _, mat, d in deltas[:5]:
        sign = "+" if d > 0 else ""
        parts.append(f"{mat} {sign}{d:.3f} mL")
    return "; ".join(parts) if parts else "No material shift"


def render_markdown(result: OptimizationResult) -> str:
    lines: list[str] = []
    lines.append("# Cobalt Cedar Air — Optimized (Longevity + Projection + Smell, Cedar-First, No DHM Boost)")
    lines.append("")
    lines.append("**Date:** 2026-05-03  ")
    lines.append(
        "**Method:** constrained local-search optimizer with smell-preservation guardrail  "
        f"(max drift {MAX_DRIFT_ML*1000:.0f} µL, step sizes 25 µL / 50 µL)."
    )
    lines.append("**DHM directive:** locked at original dose — user saving DHM for sport cologne project.")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append(f"- Total concentrate locked at `{CONCENTRATE_ML:.3f} mL`.")
    lines.append(f"- No new materials introduced; original roster of {len(result.original_ml)} materials kept.")
    lines.append(f"- Max drift from original: `{MAX_DRIFT_ML*1000:.0f} µL` (~{MAX_DRIFT_ML/CONCENTRATE_ML*100:.1f} % of concentrate).")
    lines.append("- Key character materials (Ambrox Super, Iso E Super, Sandalore, Ginger, Pink Pepper) protected by tight drift.")
    lines.append("")
    lines.append("## Weighted Axes")
    lines.append("")
    lines.append("| Axis | Weight | Maps to |")
    lines.append("|---|---|---|")
    lines.append("| longevity | 1.0 | MW + fixative load — core target |")
    lines.append("| projection (sillage) | 1.0 | VP + boosters — core target |")
    lines.append("| smell (hedonic) | 1.0 | intrinsic pleasantness — core target |")
    lines.append("| skin performance | 1.0 | reservoir kinetics — longevity contributor |")
    lines.append("| perceptual clarity | 0.5 | mixture suppression — smell clarity |")
    lines.append("| luxury | 0.3 | ingredient quality |")
    lines.append("| texture | 0.3 | haptic / creamy / silky |")
    lines.append("| depth (stacking) | 0.3 | structural layering |")
    lines.append("| synergy | 0.2 | pairing-rule hits |")
    lines.append("| photorealism | 0.2 | glass-like definition |")
    lines.append("")
    lines.append("## Score Summary")
    lines.append("")
    delta = result.optimized_scores["total"] - result.original_scores["total"]
    lines.append(f"**Geometric total:** `{result.original_scores['total']:.1f}` → `{result.optimized_scores['total']:.1f}` (`{delta:+.1f}`)")
    lines.append("")
    lines.append("| Axis | Original | Optimized | Delta |")
    lines.append("|---|---|---|---|")
    for axis in AXES:
        ov = result.original_scores[axis]
        nv = result.optimized_scores[axis]
        dv = nv - ov
        lines.append(f"| {axis} | {ov:.1f} | {nv:.1f} | {dv:+.1f} |")
    lines.append("")
    lines.append(f"**Main shifts:** {summarize_shift(result.original_ml, result.optimized_ml)}")
    lines.append("")
    lines.append("## Optimized Formula")
    lines.append("")
    lines.append("| Material | Original µL | Optimized µL | Delta µL |")
    lines.append("|---|---:|---:|---:|")
    for mat in sorted(result.original_ml.keys(), key=lambda m: -result.original_ml[m]):
        o_ul = round(result.original_ml[mat] * 1000)
        n_ul = round(result.optimized_ml.get(mat, 0.0) * 1000)
        d_ul = n_ul - o_ul
        lines.append(f"| {mat} | {o_ul} | {n_ul} | {d_ul:+d} |")
    lines.append(f"| **Ethanol 96 %** | **{ETHANOL_ML*1000:.0f}** | **{ETHANOL_ML*1000:.0f}** | **0** |")
    lines.append("")
    lines.append("## Optimizer Moves")
    lines.append("")
    if result.history:
        for move in result.history:
            lines.append(f"- {move}")
    else:
        lines.append("- No constrained rebalance improved the score.")
    lines.append("")
    lines.append("## Build Rule")
    lines.append("")
    lines.append("1. Blend the optimized concentrate first (base → heart → top).")
    lines.append(f"2. Add `{ETHANOL_ML:.2f} mL` ethanol 96 %.")
    lines.append("3. Rest 4 weeks before serious judgement.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    amounts = parse_formula(SOURCE_PATH)
    print(f"Parsed {len(amounts)} materials, total {sum(amounts.values())*1000:.0f} µL")
    result = optimize(amounts)
    md = render_markdown(result)
    OUTPUT_PATH.write_text(md, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Original total: {result.original_scores['total']:.1f}")
    print(f"Optimized total: {result.optimized_scores['total']:.1f}")


if __name__ == "__main__":
    main()
