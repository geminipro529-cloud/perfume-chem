"""Historical diagnostic search; not admitted to select or write a formula."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import math

from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer

SOURCE_PATH = PROJECT_ROOT / "Orris_Damascone_10_Deep_Luxury_30mL.md"
OUTPUT_PATH = PROJECT_ROOT / "Orris_Damascone_10_Deep_Luxury_30mL_Optimized.md"

ACCORD_NAME = "Orris + Damascone Accord"
ACCORD_ML = 4.50
ADDITIONS_TOTAL_ML = 3.00
ETHANOL_ML = 22.50
CONCENTRATE_TOTAL_ML = ACCORD_ML + ADDITIONS_TOTAL_ML

STEP_OPTIONS = (0.10, 0.05)
MAX_DRIFT_ML = 1.20
MIN_AMOUNT_ML = 0.0
MIN_NONZERO_ML = 0.025
MAX_ITERATIONS = 12
FAST_AXES = (
    "longevity",
    "sillage",
    "balance",
    "synergy",
    "theory",
    "cost",
    "radiance",
    "texture",
    "complexity",
    "character_balance",
)

SCORER = FormulaScorer()


@dataclass
class Prototype:
    number: int
    name: str
    direction: str
    fit: float | None
    additions_ml: dict[str, float]


@dataclass
class OptimizationResult:
    prototype: Prototype
    original_scores: dict[str, float]
    optimized_scores: dict[str, float]
    optimized_additions_ml: dict[str, float]
    history: list[str]


def parse_prototypes(path: Path) -> list[Prototype]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^##\s+(\d+)\.\s+(.+?)\s*$", text, flags=re.MULTILINE)
    prototypes: list[Prototype] = []

    for idx in range(1, len(parts) - 2, 3):
        number = int(parts[idx])
        name = parts[idx + 1].strip()
        body = parts[idx + 2]

        direction_match = re.search(r"\*\*Direction:\*\*\s*(?:`([^`]+)`|([^\n]+))", body)
        fit_match = re.search(r"\*\*Estimated fit:\*\*\s*`([\d.]+)/10`", body)
        direction = ""
        if direction_match:
            direction = (direction_match.group(1) or direction_match.group(2) or "").strip()
        fit = float(fit_match.group(1)) if fit_match else None

        additions: dict[str, float] = {}
        for line in body.splitlines():
            match = re.match(r"\|\s*(.+?)\s*\|\s*([\d.]+)\s*\|", line)
            if not match:
                continue
            material = match.group(1).replace("**", "").strip()
            if material.lower() in {"material", "additions total"}:
                continue
            additions[material] = float(match.group(2))

        if not additions:
            continue

        prototypes.append(
            Prototype(
                number=number,
                name=name,
                direction=direction,
                fit=fit,
                additions_ml=normalize_amounts(additions),
            )
        )

    if not prototypes:
        raise ValueError(f"No prototypes found in {path}")

    return prototypes


def infer_dilution(name: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", name)
    if match:
        return float(match.group(1)) / 100.0
    return 1.0


def normalize_amounts(amounts: dict[str, float]) -> dict[str, float]:
    cleaned = {name: round(value, 3) for name, value in amounts.items() if value > 1e-9}
    total = round(sum(cleaned.values()), 3)
    drift = round(ADDITIONS_TOTAL_ML - total, 3)
    if abs(drift) > 1e-6 and cleaned:
        largest = max(cleaned, key=cleaned.get)
        cleaned[largest] = round(cleaned[largest] + drift, 3)
    return cleaned


def build_formula_vector(additions_ml: dict[str, float]) -> FormulaVector:
    ingredients = {ACCORD_NAME: round((ACCORD_ML / CONCENTRATE_TOTAL_ML) * 100.0, 4)}
    dilutions: dict[str, float] = {}

    for material, amount_ml in additions_ml.items():
        if amount_ml <= 1e-9:
            continue
        ingredients[material] = round((amount_ml / CONCENTRATE_TOTAL_ML) * 100.0, 4)
        dilution = infer_dilution(material)
        if dilution != 1.0:
            dilutions[material] = dilution

    return FormulaVector(ingredients=ingredients, dilutions=dilutions)


def drift_from_original(current: dict[str, float], original: dict[str, float]) -> float:
    keys = set(current) | set(original)
    return round(sum(abs(current.get(key, 0.0) - original.get(key, 0.0)) for key in keys), 3)


def additions_signature(additions_ml: dict[str, float]) -> tuple[tuple[str, float], ...]:
    return tuple(sorted((name, round(amount, 3)) for name, amount in additions_ml.items() if amount > 1e-9))


@lru_cache(maxsize=8192)
def _cached_score(signature: tuple[tuple[str, float], ...]) -> dict[str, float]:
    additions = {name: amount for name, amount in signature}
    fv = build_formula_vector(additions)
    detected_style = SCORER.detect_style(fv)
    scores = {
        "longevity": SCORER.score_longevity(fv),
        "sillage": SCORER.score_sillage(fv),
        "balance": SCORER.score_balance(fv, style=detected_style),
        "synergy": SCORER.score_synergy(fv),
        "theory": SCORER.score_theory(fv),
        "cost": SCORER.score_cost(fv),
        "radiance": SCORER.score_radiance(fv),
        "texture": SCORER.score_texture(fv),
        "complexity": SCORER.score_complexity(fv),
        "character_balance": SCORER.score_character_balance(fv),
    }

    weights = SCORER.weights.as_dict()
    total_weight = sum(weights.get(axis, 0.0) for axis in FAST_AXES) or 1.0
    weighted_sum = sum(scores[axis] * weights.get(axis, 0.0) for axis in FAST_AXES)
    log_sum = 0.0
    for axis in FAST_AXES:
        weight = weights.get(axis, 0.0)
        if weight <= 0:
            continue
        log_sum += (weight / total_weight) * math.log(max(scores[axis], 1.0))

    scores["arithmetic_total"] = round(weighted_sum / total_weight, 1)
    scores["geometric_total"] = round(math.exp(log_sum), 1)
    scores["total"] = scores["geometric_total"]
    return scores


def score_formula(additions_ml: dict[str, float]) -> dict[str, float]:
    return _cached_score(additions_signature(additions_ml))


def candidate_key(
    scores: dict[str, float],
    *,
    drift_ml: float,
) -> tuple[float, float, float, float, float, float]:
    return (
        round(scores["total"], 3),
        round(scores["texture"], 2),
        round(scores["theory"], 2),
        round(scores["balance"], 2),
        round(scores["synergy"], 2),
        -round(drift_ml, 3),
    )


def format_move(
    giver: str,
    receiver: str,
    delta_ml: float,
    before: dict[str, float],
    after: dict[str, float],
    before_scores: dict[str, float],
    after_scores: dict[str, float],
) -> str:
    return (
        f"Shifted {delta_ml:.3f} mL from {giver} to {receiver} "
        f"(total {before_scores['total']:.1f} -> {after_scores['total']:.1f}, "
        f"texture {before_scores['texture']:.1f} -> {after_scores['texture']:.1f}, "
        f"theory {before_scores['theory']:.1f} -> {after_scores['theory']:.1f})"
    )


def optimize_prototype(prototype: Prototype) -> OptimizationResult:
    original = dict(prototype.additions_ml)
    materials = list(original.keys())

    current = dict(original)
    current_scores = score_formula(current)
    history: list[str] = []

    for _ in range(MAX_ITERATIONS):
        best_candidate: dict[str, float] | None = None
        best_scores: dict[str, float] | None = None
        best_giver = ""
        best_receiver = ""
        best_delta = 0.0

        current_drift = drift_from_original(current, original)
        current_key = candidate_key(current_scores, drift_ml=current_drift)

        for giver in materials:
            giver_amount = current.get(giver, 0.0)
            if giver_amount <= MIN_AMOUNT_ML + 1e-9:
                continue

            for receiver in materials:
                if giver == receiver:
                    continue

                for delta in STEP_OPTIONS:
                    if giver_amount - delta < MIN_AMOUNT_ML - 1e-9:
                        continue

                    candidate = dict(current)
                    candidate[giver] = round(candidate.get(giver, 0.0) - delta, 3)
                    candidate[receiver] = round(candidate.get(receiver, 0.0) + delta, 3)

                    if 0.0 < candidate[giver] < MIN_NONZERO_ML:
                        continue

                    candidate = normalize_amounts(candidate)
                    candidate_drift = drift_from_original(candidate, original)
                    if candidate_drift > MAX_DRIFT_ML:
                        continue

                    scores = score_formula(candidate)
                    key = candidate_key(scores, drift_ml=candidate_drift)
                    if key <= current_key:
                        continue

                    if best_scores is None or key > candidate_key(
                        best_scores,
                        drift_ml=drift_from_original(best_candidate or {}, original),
                    ):
                        best_candidate = candidate
                        best_scores = scores
                        best_giver = giver
                        best_receiver = receiver
                        best_delta = delta

        if best_candidate is None or best_scores is None:
            break

        history.append(
            format_move(
                best_giver,
                best_receiver,
                best_delta,
                current,
                best_candidate,
                current_scores,
                best_scores,
            )
        )
        current = best_candidate
        current_scores = best_scores

    return OptimizationResult(
        prototype=prototype,
        original_scores=score_formula(original),
        optimized_scores=current_scores,
        optimized_additions_ml=normalize_amounts(current),
        history=history,
    )


def summarize_shift(original: dict[str, float], optimized: dict[str, float]) -> str:
    deltas = []
    for material in sorted(set(original) | set(optimized)):
        delta = round(optimized.get(material, 0.0) - original.get(material, 0.0), 3)
        if abs(delta) >= 0.024:
            deltas.append((abs(delta), material, delta))
    deltas.sort(reverse=True)
    parts = []
    for _, material, delta in deltas[:3]:
        sign = "+" if delta > 0 else ""
        parts.append(f"{material} {sign}{delta:.3f} mL")
    return "; ".join(parts) if parts else "No material shift"


def render_markdown(results: list[OptimizationResult]) -> str:
    lines: list[str] = []
    lines.append("# Orris + Damascone — 10 Deep Luxury Directions, Fixed-Accord Optimized")
    lines.append("")
    lines.append("**Date:** 2026-04-06  ")
    lines.append(
        "**Method:** constrained optimizer pass with the premade `orris + damascone accord` "
        "locked at `4.50 mL`, additions locked to their original material roster, and only "
        "the `3.00 mL` additions block rebalanced."
    )
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append("- `4.50 mL` accord stayed fixed in every build.")
    lines.append("- `3.00 mL` additions stayed fixed as a total.")
    lines.append("- No new materials were introduced, so the 10 directions stay different.")
    lines.append("- Diluted materials like `Cashmeran (20%)`, `Galaxolide (80%)`, and `Ambrox Super (30% w/v)` were scored with their dilution respected.")
    lines.append("- Limitation: the accord is still treated as an opaque fixed module because its internal raw-material breakdown is not defined in the repo.")
    lines.append("")
    lines.append("## Score Summary")
    lines.append("")
    lines.append("| # | Formula | Original | Optimized | Delta | Main Shift |")
    lines.append("|---|---|---:|---:|---:|---|")
    for result in results:
        delta = result.optimized_scores["total"] - result.original_scores["total"]
        lines.append(
            f"| {result.prototype.number} | {result.prototype.name} | "
            f"{result.original_scores['total']:.1f} | {result.optimized_scores['total']:.1f} | "
            f"{delta:+.1f} | {summarize_shift(result.prototype.additions_ml, result.optimized_additions_ml)} |"
        )

    for result in results:
        proto = result.prototype
        delta = result.optimized_scores["total"] - result.original_scores["total"]
        lines.append("")
        lines.append(f"## {proto.number}. {proto.name}")
        lines.append("")
        lines.append(f"**Direction:** `{proto.direction}`  ")
        if proto.fit is not None:
            lines.append(f"**Original hand score:** `{proto.fit:.1f}/10`  ")
        lines.append(
            f"**Optimizer score:** `{result.original_scores['total']:.1f} -> {result.optimized_scores['total']:.1f}` "
            f"(`{delta:+.1f}`)"
        )
        lines.append("")
        lines.append("| Material | Original mL | Optimized mL | Delta mL |")
        lines.append("|---|---:|---:|---:|")
        for material in proto.additions_ml:
            original_ml = proto.additions_ml.get(material, 0.0)
            optimized_ml = result.optimized_additions_ml.get(material, 0.0)
            delta_ml = optimized_ml - original_ml
            lines.append(
                f"| {material} | {original_ml:.3f} | {optimized_ml:.3f} | {delta_ml:+.3f} |"
            )
        lines.append(f"| **Your `{ACCORD_NAME}`** | **{ACCORD_ML:.2f}** | **{ACCORD_ML:.2f}** | **+0.00** |")
        lines.append(f"| **Ethanol 96%** | **{ETHANOL_ML:.2f}** | **{ETHANOL_ML:.2f}** | **+0.00** |")
        lines.append("")
        lines.append("**Axis Read**")
        lines.append("")
        lines.append(
            f"- `Texture:` `{result.original_scores['texture']:.1f} -> {result.optimized_scores['texture']:.1f}`"
        )
        lines.append(
            f"- `Theory:` `{result.original_scores['theory']:.1f} -> {result.optimized_scores['theory']:.1f}`"
        )
        lines.append(
            f"- `Balance:` `{result.original_scores['balance']:.1f} -> {result.optimized_scores['balance']:.1f}`"
        )
        lines.append(
            f"- `Synergy:` `{result.original_scores['synergy']:.1f} -> {result.optimized_scores['synergy']:.1f}`"
        )
        lines.append("")
        lines.append("**Optimizer Moves**")
        lines.append("")
        if result.history:
            for move in result.history[:6]:
                lines.append(f"- {move}")
        else:
            lines.append("- No constrained rebalance improved the score.")

    lines.append("")
    lines.append("## Build Rule")
    lines.append("")
    lines.append("For every optimized version:")
    lines.append("")
    lines.append("1. Blend the optimized `3.00 mL` additions first.")
    lines.append(f"2. Add `4.50 mL` of your fixed `{ACCORD_NAME}`.")
    lines.append("3. Add `22.50 mL` ethanol 96%.")
    lines.append("4. Rest `14-21 days` before serious judgement.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    raise SystemExit(
        "BLOCKED: legacy heuristic totals are diagnostic only and cannot select "
        "or write a recompounding formula. Use the evidence-bounded optimizer "
        "with an admitted endpoint and controlled-comparison review."
    )


if __name__ == "__main__":
    main()
