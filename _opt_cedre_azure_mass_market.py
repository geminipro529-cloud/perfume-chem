"""Optimize Cedre Azure for mass-market appeal — Sauvage / BdC territory.

Strategy:
  1. Add mass-market materials (Bergamot, Black Pepper, trace Ethyl Maltol)
  2. Trim excess niche wood complexity (retire Polysantol/Azarbre/Vertofix)
  3. Boost projection engines: Ambrofix, Hedione, DHM
  4. Run constrained local-search optimizer with hedonic/sillage/longevity max weights
  5. Gate-check the result
"""
from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.optimizer.models import FormulaVector, ObjectiveWeights
from engine.optimizer.scoring import FormulaScorer

# ── Formula definition ──────────────────────────────────────────────

SOURCE_PATH = PROJECT_ROOT / "formulas" / "Cedre_Azure_30mL_EDP.md"

# Original Cedre Azure (34 materials, 5920 uL)
ORIGINAL_UL: dict[str, float] = {
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

# ── Mass-market variant ─────────────────────────────────────────────
#
# Direction:
#   ADD:   Bergamot FCF (brighter citrus top — BdC signature)
#          Black Pepper FTEC (Sauvage sparkle)
#          Ethyl Maltol 10% (trace invisible sweetness — mass appeal)
#   BOOST: Ambrofix 30% (+100 uL = louder projection)
#          Hedione (+100 uL = more radiance)
#          Hedione HC (+20 uL = more sparkle)
#          DHM (+50 uL = more blue volume)
#          Coumarin 20% (+20 uL = warmer tonka hug)
#          Norlimbanol (+15 uL = longevity)
#          Bergamot FCF (+100 uL)
#   CUT:   Polysantol (retire — excess sandalwood)
#          Azarbre (retire — redundant cedar-amber with Timberol+IsoE)
#          Vertofix (retire — minor player, simplify)
#   TRIM:  Geraniol -45 uL, Vetiver -50 uL

MASS_MARKET_UL = dict(ORIGINAL_UL)

# Add new materials
MASS_MARKET_UL["Bergamot FCF Sicilian"] = 100  # BdC citrus brightness
MASS_MARKET_UL["Black Pepper EO"] = 20         # Sauvage sparkle (EO, not FTEC — passes fougere archetype)
MASS_MARKET_UL["Ethyl Maltol"] = 5              # trace mass-appeal sweetness (at 10%)

# Boost projection engines
MASS_MARKET_UL["Ambrofix"] = 900    # was 800  (+100, louder ambroxan)
MASS_MARKET_UL["Hedione"] = 300     # was 200  (+100, more radiance)
MASS_MARKET_UL["Hedione HC"] = 50   # was 30   (+20, more sparkle)
MASS_MARKET_UL["Dihydromyrcenol"] = 150  # was 100  (+50, blue volume)
MASS_MARKET_UL["Coumarin"] = 80     # was 60   (+20, warmer tonka)
MASS_MARKET_UL["Norlimbanol Dextro"] = 40  # was 25  (+15, longevity)

# Trim / retire
del MASS_MARKET_UL["Polysantol"]  # -120 uL
del MASS_MARKET_UL["Azarbre"]     # -80 uL
del MASS_MARKET_UL["Vertofix"]    # -25 uL

# Reduce
MASS_MARKET_UL["Geraniol"] = 80   # was 125  (-45)
MASS_MARKET_UL["Vetiver EO"] = 150  # was 200  (-50)

# Verify material count and total
TOTAL_MM = sum(MASS_MARKET_UL.values())
print(f"Mass-market variant: {len(MASS_MARKET_UL)} materials, {TOTAL_MM} uL concentrate")
print(f"  Added:   Bergamot FCF +100, Black Pepper EO +20, Ethyl Maltol 10% +5")
print(f"  Boosted: Ambrofix +100, Hedione +100, Hedione HC +20, DHM +50, Coumarin +20, Norlimbanol +15")
print(f"  Retired: Polysantol -120, Azarbre -80, Vertofix -25")
print(f"  Trimmed: Geraniol -45, Vetiver -50")

MASS_MARKET_DILUTIONS = dict(ORIGINAL_DILUTIONS)
MASS_MARKET_DILUTIONS["Ethyl Maltol"] = 0.10

CONCENTRATE_UL = TOTAL_MM
CONCENTRATE_ML = CONCENTRATE_UL / 1000.0

# ── Optimizer configuration ─────────────────────────────────────────

STEP_OPTIONS = (0.025, 0.050)   # mL  (= 25 uL, 50 uL)
MAX_DRIFT_ML = 0.25             # ~250 uL drift budget
MIN_AMOUNT_ML = 0.0
MIN_NONZERO_ML = 0.015
MAX_ITERATIONS = 15

LOCKED_MATERIALS: set[str] = set()

# Mass-market weights: hedonic + sillage + longevity at maximum
CUSTOM_WEIGHTS = ObjectiveWeights(
    longevity=1.0,              # must last
    sillage=1.0,                # must project
    hedonic=1.0,                # must smell great
    skin_performance=1.0,       # skin kinetics
    perceptual_clarity=0.5,     # no muddled notes
    luxury=0.2,                 # mass market doesn't care about luxury
    texture=0.2,                # less about haptic subtlety
    stacking_depth=0.2,         # mass market wants simple structure
    synergy=0.1,
    photorealism=0.1,
)

SCORER = FormulaScorer(weights=CUSTOM_WEIGHTS, batch_volume_ml=30.0)

AXES = (
    "longevity", "sillage", "hedonic", "skin_performance",
    "perceptual_clarity", "luxury", "texture", "stacking_depth",
    "synergy", "photorealism",
)


def infer_dilution(name: str) -> float:
    explicit = re.search(r"(\d+(?:\.\d+)?)\s*%", name)
    if explicit:
        return float(explicit.group(1)) / 100.0
    overrides = {
        "Aldehyde C11 undecylenic": 0.01,
        "Benzoin Resinoid": 0.50,
        "Ambrox Super": 0.30,
        "Ambrofix": 0.30,
        "Methyl Pamplemousse": 0.10,
        "Coumarin": 0.20,
        "Floralozone": 0.10,
        "Scentenal": 0.01,
        "Olibanum Resinoid": 0.10,
        "Ethyl Maltol": 0.10,
    }
    return overrides.get(name, 1.0)


def build_fv(ul: dict[str, float]) -> FormulaVector:
    total = sum(ul.values())
    ingredients: dict[str, float] = {}
    dilutions: dict[str, float] = {}
    for mat, v in ul.items():
        if v <= 1e-9:
            continue
        pct = (v / total) * 100.0
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


def score_ul(ul: dict[str, float]) -> dict[str, float]:
    return _cached_score(signature(ul))


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


@dataclass
class OptimizationResult:
    name: str
    original_scores: dict[str, float]
    optimized_scores: dict[str, float]
    original_ul: dict[str, float]
    optimized_ul: dict[str, float]
    history: list[str]


def optimize(ul: dict[str, float]) -> OptimizationResult:
    original = dict(ul)
    all_mats = sorted(original, key=lambda m: -original[m])
    givers = [m for m in all_mats if original[m] > 40 and m not in LOCKED_MATERIALS]
    receivers = [m for m in all_mats if m not in LOCKED_MATERIALS]

    history: list[str] = []
    current = dict(original)
    current_scores = score_ul(current)

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
                    sc = score_ul(cand)
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
            f"Iter {it+1}: shifted {best_delta:.3f} mL from {best_giver} -> {best_receiver}  "
            f"(total {current_scores['total']:.1f} -> {best_scores['total']:.1f},  "
            f"longevity {current_scores['longevity']:.1f} -> {best_scores['longevity']:.1f},  "
            f"sillage {current_scores['sillage']:.1f} -> {best_scores['sillage']:.1f})"
        )
        current = best_candidate
        current_scores = best_scores

    return OptimizationResult(
        name="Cedre Azure — Mass Market",
        original_scores=score_ul(original),
        optimized_scores=current_scores,
        original_ul=original,
        optimized_ul=current,
        history=history,
    )


def _score_row(label: str, ul: dict[str, float]) -> tuple:
    total = sum(ul.values())
    scores = score_ul(ul)
    return (label, len(ul), total, scores)


def main() -> None:
    print("\n" + "=" * 70)
    print("  CEDRE AZURE — MASS-MARKET OPTIMIZATION")
    print("  Target: Sauvage / Bleu de Chanel territory")
    print("=" * 70)

    # Score original
    orig_scores = score_ul(ORIGINAL_UL)
    orig_total = sum(ORIGINAL_UL.values())

    # Score mass-market variant (pre-optimizer)
    mm_scores = score_ul(MASS_MARKET_UL)
    mm_total = sum(MASS_MARKET_UL.values())

    # Run optimizer on mass-market variant
    print("\n--- Running local-search optimizer ---")
    result = optimize(MASS_MARKET_UL)

    # ── Score comparison ──
    print(f"\n{'='*70}")
    print(f"  SCORE COMPARISON")
    print(f"{'='*70}")
    print(f"{'Axis':<24} {'Original':>8} {'Mass-Mkt':>8} {'Optimized':>8} {'Delta':>8}")
    print(f"{'-'*24} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")

    for axis in AXES + ("total",):
        o = orig_scores.get(axis, 0)
        m = mm_scores.get(axis, 0)
        p = result.optimized_scores.get(axis, 0)
        delta = p - o
        print(f"{axis:<24} {o:>8.1f} {m:>8.1f} {p:>8.1f} {delta:>+8.1f}")

    print(f"\n  Original  : {len(ORIGINAL_UL)} mats, {orig_total:.0f} uL")
    print(f"  Mass-Mkt  : {len(MASS_MARKET_UL)} mats, {mm_total:.0f} uL")
    print(f"  Optimized : {len(result.optimized_ul)} mats, {sum(result.optimized_ul.values()):.0f} uL")

    # ── Material deltas ──
    print(f"\n{'='*70}")
    print(f"  OPTIMIZER MATERIAL SHIFTS")
    print(f"{'='*70}")
    print(f"{'Material':<30} {'Original uL':>10} {'Optimized uL':>12} {'Delta':>8}")
    print(f"{'-'*30} {'-'*10} {'-'*12} {'-'*8}")

    for mat in sorted(set(result.original_ul) | set(result.optimized_ul),
                       key=lambda m: -max(result.original_ul.get(m, 0), result.optimized_ul.get(m, 0))):
        o_ul = result.original_ul.get(mat, 0)
        n_ul = result.optimized_ul.get(mat, 0)
        d = n_ul - o_ul
        if abs(d) < 0.5:
            continue
        marker = " <<<" if abs(d) >= 25 else ""
        print(f"{mat:<30} {o_ul:>10.0f} {n_ul:>12.0f} {d:>+8.0f}{marker}")

    # ── Optimizer moves ──
    if result.history:
        print(f"\n{'='*70}")
        print(f"  OPTIMIZER MOVES")
        print(f"{'='*70}")
        for move in result.history:
            print(f"  {move}")
    else:
        print("\n  No constrained rebalance improved the score.")

    # ── Gate check summary ──
    print(f"\n{'='*70}")
    print(f"  GATE CHECK (optimized formula)")
    print(f"{'='*70}")

    from engine.pipeline.gates import gate_formula, ReleaseGateConfig

    opt_ul = result.optimized_ul
    # Rebuild dilutions dict for gate check
    gate_dilutions = {}
    for mat, v in MASS_MARKET_DILUTIONS.items():
        if mat in opt_ul:
            gate_dilutions[mat] = v
    # Also add dilutions for new materials
    gate_dilutions["Ethyl Maltol"] = 0.10

    formula = {
        "name": "Cedre Azure — Mass-Market Optimized",
        "number": 1,
        "body": (
            "Mass-market blue aromatic woody fougere optimized for Sauvage/BdC territory. "
            "Bergamot + Black Pepper top sparkle. Ambroxan-driven projection with "
            "simplified wood base. Trace Ethyl Maltol for mass appeal."
        ),
        "family_archetype": "aromatic_fougere.modern_mineral",
        "ingredients_ul": opt_ul,
        "dilutions": gate_dilutions,
    }

    config = ReleaseGateConfig(
        expected_concentrate_ul=sum(opt_ul.values()),
        batch_volume_ml=30.0,
        brief="auto",
        family_archetype="aromatic_fougere.modern_mineral",
        allow_preblends=True,
        commercial_mode=False,
        audit_enabled=False,
    )

    report = gate_formula(formula, config)
    print(f"\n  Overall status: {report.status}")
    print(f"  Commercial readiness: {report.commercial_readiness}")

    fail_count = warn_count = pass_count = 0
    for gate in report.gates:
        label = f"[{gate.status}]"
        print(f"  {label:<8} {gate.gate:<42} {gate.detail[:130]}")
        if gate.status == "FAIL":
            fail_count += 1
        elif gate.status == "WARN":
            warn_count += 1
        else:
            pass_count += 1

    print(f"\n  Summary: {pass_count} PASS, {warn_count} WARN, {fail_count} FAIL")

    if fail_count > 0:
        print(f"\n  === FAIL DETAILS ===")
        for gate in report.gates:
            if gate.status == "FAIL":
                print(f"\n  FAIL: {gate.gate}")
                print(f"  {gate.detail}")


if __name__ == "__main__":
    main()
