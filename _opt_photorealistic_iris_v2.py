"""Photorealistic Iris v2 optimizer.

Purpose:
  1. Build a better 30 mL remake formula for Photorealistic Iris using a
     photoreal-iris-specific objective rather than the generic scorer alone.
  2. Derive an add-only booster from the current 30 mL optimized batch
     ([formulas/collections/Photorealistic_Iris_30mL_optimized.md]).
  3. Emit refill / replacement mini-batches that match the new v2 profile.

Inventory assumption:
  - Hedione HC is not currently available, so the v2 target uses Hedione only.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from engine.formula_analyzer import FormulaInfo, formula_to_vector
from engine.optimizer.oav_guard import check_batch_scaling, check_proportional_scaling
from engine.optimizer.scoring import FormulaScorer
from engine.synergy_graph import SynergyGraph

BATCH_ML = 30.0
BATCH_UL = int(BATCH_ML * 1000)
DROP_UL = 20.0

CURRENT_LABEL = "Photorealistic Iris"
OUTPUT_MD = Path("formulas/collections/Photorealistic_Iris_30mL_optimized_v2.md")
BOOSTER_MD = Path("formulas/collections/Photorealistic_Iris_CURRENT_BATCH_BOOSTER_v2.md")
REFILL_MD = Path("formulas/collections/Photorealistic_Iris_REPLACEMENT_v2.md")
OUTPUT_JSON = Path("_opt_photorealistic_iris_v2_out.json")

AXIS_WEIGHTS = {
    "longevity": 1.00,
    "sillage": 0.80,
    "luxury": 1.00,
    "texture": 1.15,
    "stacking_depth": 0.90,
    "photorealism": 1.40,
    "perceptual_clarity": 1.00,
    "skin_performance": 0.90,
    "synergy": 0.45,
    "hedonic": 0.35,
}
AXIS_WEIGHT_SUM = sum(AXIS_WEIGHTS.values())

# Current 30 mL batch from formulas/collections/Photorealistic_Iris_30mL_optimized.md
CURRENT_30 = {
    "Myristic Acid": 750.0,
    "Alpha Irone": 730.0,
    "Iso E Super": 365.0,
    "Hedione": 355.0,
    "Habanolide": 335.0,
    "IPM": 250.0,
    "Ethylene Brassylate": 190.0,
    "Dihydromyrcenol": 170.0,
    "Exaltolide": 150.0,
    "Ambrettolide": 140.0,
    "Ebanol": 115.0,
    "Bergamot FCF oil Sicilian": 100.0,
    "Musk Ketone": 100.0,
    "Koavone": 100.0,
    "Hedione HC": 85.0,
    "Ethyl Linalool": 70.0,
    "Orivone": 60.0,
    "Paradisamide": 60.0,
    "Azarbre": 50.0,
    "Ambrox Super": 50.0,
    "Alpha Ionone": 40.0,
    "Ultralia": 40.0,
    "Heliotropal": 40.0,
    "Carrot Seed EO": 30.0,
    "Cashmeran": 30.0,
    "Beta Ionone": 25.0,
    "Dihydro Beta Ionone": 20.0,
    "Cyclamen Aldehyde": 15.0,
    "Scentenal": 12.0,
    "Allyl Amyl Glycolate": 10.0,
    "Cis Jasmone": 10.0,
    "Farnesol": 5.0,
    "Leafovert": 4.0,
}

DILUTIONS = {
    "Alpha Irone": 0.30,
    "Myristic Acid": 0.20,
    "Musk Ketone": 0.10,
    "Exaltolide": 0.10,
    "Ambrettolide": 0.10,
    "Ambrox Super": 0.30,
    "Scentenal": 0.01,
    "Paradisamide": 0.10,
    "Cashmeran": 0.20,
}

# Manual photoreal seed for the dedicated optimizer. No Hedione HC.
SEED_V2 = {
    "Bergamot FCF oil Sicilian": 80.0,
    "Grapefruit FCF": 24.0,
    "Leafovert": 5.0,
    "Ethyl Linalool": 82.0,
    "Dihydromyrcenol": 110.0,
    "Allyl Amyl Glycolate": 10.0,
    "Scentenal": 12.0,
    "Alpha Irone": 840.0,
    "Myristic Acid": 800.0,
    "Alpha Ionone": 46.0,
    "Beta Ionone": 30.0,
    "Alpha Isomethyl Ionone": 75.0,
    "Dihydro Beta Ionone": 24.0,
    "Irotyl": 18.0,
    "Orivone": 82.0,
    "Hedione": 450.0,
    "Cis Jasmone": 10.0,
    "Carrot Seed EO": 35.0,
    "Ultralia": 50.0,
    "Cyclamen Aldehyde": 15.0,
    "Farnesol": 5.0,
    "Violet Fleuressence": 12.0,
    "Heliotropal": 52.0,
    "Musk Ketone": 100.0,
    "Koavone": 120.0,
    "Azarbre": 45.0,
    "Ebanol": 110.0,
    "Iso E Super": 320.0,
    "Habanolide": 260.0,
    "Ethylene Brassylate": 230.0,
    "Exaltolide": 145.0,
    "Ambrettolide": 125.0,
    "Romandolide": 40.0,
    "Ambrox Super": 30.0,
    "IPM": 320.0,
    "Paradisamide": 20.0,
    "Cashmeran": 15.0,
}

# Alternate seed based on current formula with HC folded into Hedione and
# realism traces reintroduced.
CURRENT_NO_HC_SEED = dict(CURRENT_30)
CURRENT_NO_HC_SEED["Hedione"] = CURRENT_NO_HC_SEED.get("Hedione", 0.0) + CURRENT_NO_HC_SEED.pop("Hedione HC")
CURRENT_NO_HC_SEED.update({
    "Grapefruit FCF": 18.0,
    "Alpha Isomethyl Ionone": 60.0,
    "Irotyl": 15.0,
    "Violet Fleuressence": 10.0,
})

BOUNDS = {
    "Bergamot FCF oil Sicilian": (60.0, 110.0),
    "Grapefruit FCF": (0.0, 35.0),
    "Leafovert": (3.0, 8.0),
    "Ethyl Linalool": (60.0, 95.0),
    "Dihydromyrcenol": (80.0, 135.0),
    "Allyl Amyl Glycolate": (6.0, 16.0),
    "Scentenal": (8.0, 16.0),
    "Alpha Irone": (760.0, 920.0),
    "Myristic Acid": (730.0, 900.0),
    "Alpha Ionone": (35.0, 60.0),
    "Beta Ionone": (20.0, 40.0),
    "Alpha Isomethyl Ionone": (40.0, 100.0),
    "Dihydro Beta Ionone": (16.0, 32.0),
    "Irotyl": (10.0, 28.0),
    "Orivone": (55.0, 95.0),
    "Hedione": (400.0, 520.0),
    "Cis Jasmone": (8.0, 16.0),
    "Carrot Seed EO": (24.0, 45.0),
    "Ultralia": (35.0, 65.0),
    "Cyclamen Aldehyde": (10.0, 20.0),
    "Farnesol": (3.0, 8.0),
    "Violet Fleuressence": (0.0, 20.0),
    "Heliotropal": (40.0, 65.0),
    "Musk Ketone": (90.0, 125.0),
    "Koavone": (90.0, 140.0),
    "Azarbre": (35.0, 60.0),
    "Ebanol": (90.0, 125.0),
    "Iso E Super": (270.0, 340.0),
    "Habanolide": (220.0, 290.0),
    "Ethylene Brassylate": (180.0, 260.0),
    "Exaltolide": (120.0, 170.0),
    "Ambrettolide": (105.0, 145.0),
    "Romandolide": (0.0, 70.0),
    "Ambrox Super": (15.0, 40.0),
    "IPM": (260.0, 360.0),
    "Paradisamide": (0.0, 30.0),
    "Cashmeran": (0.0, 20.0),
}

STEP_SERIES = (40.0, 20.0, 10.0, 5.0)


def geo_composite(detail: dict) -> float:
    log_sum = 0.0
    for axis, weight in AXIS_WEIGHTS.items():
        value = max(float(detail.get(axis, 5.0)), 5.0)
        log_sum += (weight / AXIS_WEIGHT_SUM) * math.log(value)
    return math.exp(log_sum)


def scorer_and_detail(ing: dict[str, float], scorer: FormulaScorer) -> tuple[float, dict]:
    total_ul = sum(ing.values())
    formula = FormulaInfo(
        number=0,
        name="Photorealistic Iris v2",
        ingredients=ing,
        dilutions=DILUTIONS,
        concentrate_ml=total_ul / 1000.0,
        description="",
    )
    vector = formula_to_vector(formula)
    detail = scorer.score(vector)
    return geo_composite(detail), detail


def smooth_center_bonus(value: float, center: float, tolerance: float, gain: float) -> float:
    return gain * max(0.0, 1.0 - abs(value - center) / tolerance)


def high_penalty(value: float, cutoff: float, slope: float) -> float:
    return max(0.0, value - cutoff) * slope


def low_penalty(value: float, cutoff: float, slope: float) -> float:
    return max(0.0, cutoff - value) * slope


def photoreal_objective(ing: dict[str, float], scorer: FormulaScorer) -> tuple[float, float, dict]:
    geo, detail = scorer_and_detail(ing, scorer)
    amt = lambda name: float(ing.get(name, 0.0))

    realism = 0.0
    realism += smooth_center_bonus(amt("Alpha Irone"), 840.0, 120.0, 1.40)
    realism += smooth_center_bonus(amt("Myristic Acid"), 800.0, 110.0, 1.15)
    realism += smooth_center_bonus(amt("Hedione"), 450.0, 80.0, 0.95)
    realism += smooth_center_bonus(amt("Koavone"), 118.0, 35.0, 0.75)
    realism += smooth_center_bonus(amt("Orivone"), 80.0, 25.0, 0.60)
    realism += smooth_center_bonus(amt("Carrot Seed EO"), 34.0, 12.0, 0.45)
    realism += smooth_center_bonus(amt("Alpha Isomethyl Ionone"), 72.0, 40.0, 0.55)
    realism += smooth_center_bonus(amt("Irotyl"), 18.0, 10.0, 0.45)
    realism += smooth_center_bonus(amt("Grapefruit FCF"), 22.0, 14.0, 0.30)
    realism += smooth_center_bonus(amt("Violet Fleuressence"), 10.0, 8.0, 0.25)

    support_penalty = 0.0
    support_penalty += high_penalty(amt("Dihydromyrcenol"), 125.0, 0.020)
    support_penalty += high_penalty(amt("Habanolide"), 285.0, 0.018)
    support_penalty += high_penalty(amt("Iso E Super"), 335.0, 0.015)
    support_penalty += high_penalty(amt("Ambrox Super"), 35.0, 0.060)
    support_penalty += high_penalty(amt("Cashmeran"), 16.0, 0.050)
    support_penalty += high_penalty(amt("Paradisamide"), 20.0, 0.030)

    floor_penalty = 0.0
    floor_penalty += low_penalty(amt("Leafovert"), 4.0, 0.12)
    floor_penalty += low_penalty(amt("Cyclamen Aldehyde"), 12.0, 0.07)
    floor_penalty += low_penalty(amt("Heliotropal"), 46.0, 0.03)
    floor_penalty += low_penalty(amt("Ethylene Brassylate"), 200.0, 0.006)
    floor_penalty += low_penalty(amt("IPM"), 280.0, 0.006)

    # Keep generic support from swamping the iris core.
    iris_core = (
        amt("Alpha Irone") + amt("Alpha Ionone") + amt("Beta Ionone") +
        amt("Alpha Isomethyl Ionone") + amt("Dihydro Beta Ionone") +
        amt("Irotyl") + amt("Orivone") + amt("Ultralia") + amt("Koavone")
    )
    support_core = (
        amt("Iso E Super") + amt("Habanolide") + amt("Dihydromyrcenol") +
        amt("Romandolide") + amt("Ambrox Super")
    )
    ratio = iris_core / max(support_core, 1.0)
    ratio_bonus = smooth_center_bonus(ratio, 2.0, 0.9, 1.0)

    score = geo + realism + ratio_bonus - support_penalty - floor_penalty
    return score, geo, detail


def oav_safe(ing: dict[str, float]) -> bool:
    prop = check_proportional_scaling(ing, DILUTIONS, BATCH_ML, 15.0)
    if any(c.severity == "error" for c in prop):
        return False
    same = check_batch_scaling(ing, DILUTIONS, BATCH_ML, BATCH_ML)
    if any(c.severity == "error" for c in same):
        return False
    return True


def normalize_seed(seed: dict[str, float]) -> dict[str, float]:
    out = {}
    for material, (lo, hi) in BOUNDS.items():
        value = float(seed.get(material, lo))
        value = min(max(value, lo), hi)
        if value > 0:
            out[material] = value
    return out


def optimize_seed(seed: dict[str, float], scorer: FormulaScorer, label: str) -> tuple[dict[str, float], float, float, dict]:
    ing = normalize_seed(seed)
    best_score, best_geo, best_detail = photoreal_objective(ing, scorer)
    print(f"[{label}] start geo={best_geo:.3f} objective={best_score:.3f} concentrate={sum(ing.values()):.0f} µL")

    for step in STEP_SERIES:
        improved = True
        while improved:
            improved = False
            best_move = None
            for material, (lo, hi) in BOUNDS.items():
                current = ing.get(material, 0.0)
                for delta in (-step, step):
                    new_value = current + delta
                    if new_value < lo - 0.1 or new_value > hi + 0.1:
                        continue
                    trial = dict(ing)
                    if new_value <= 0.0:
                        trial.pop(material, None)
                    else:
                        trial[material] = round(new_value, 3)
                    total = sum(trial.values())
                    if total < 4300.0 or total > 5200.0:
                        continue
                    if not oav_safe(trial):
                        continue
                    trial_score, trial_geo, trial_detail = photoreal_objective(trial, scorer)
                    if trial_score > best_score + 0.005:
                        if best_move is None or trial_score > best_move[0]:
                            best_move = (trial_score, trial_geo, material, delta, trial, trial_detail)
            if best_move is None:
                break
            best_score, best_geo, material, delta, ing, best_detail = best_move
            improved = True
            print(
                f"  step {step:>4.0f}: {material} {delta:+.0f} -> "
                f"geo={best_geo:.3f} objective={best_score:.3f} total={sum(ing.values()):.0f} µL"
            )
    return ing, best_score, best_geo, best_detail


def format_dilution(material: str) -> str:
    d = DILUTIONS.get(material, 1.0)
    return f"{int(d * 100)}%" if d < 1.0 else "neat"


def render_new_batch_md(
    ing: dict[str, float],
    geo: float,
    detail: dict,
    current_geo: float,
    current_objective: float,
    target_objective: float,
) -> str:
    total_ul = sum(ing.values())
    ethanol_ul = BATCH_UL - total_ul
    current_total = sum(CURRENT_30.values())
    no_hc_note = (
        "This v2 build is optimized without `Hedione HC`; its radiance budget is folded into "
        "`Hedione` and kept inside a tighter iris-specific structure."
    )
    lines = [
        "# Photorealistic Iris — optimized 30 mL v2",
        "",
        "**Status:** dedicated Photorealistic Iris optimizer, no-Hedione-HC inventory mode, 30 mL fresh-batch remake.",
        f"**Geometric composite score:** {geo:.2f}",
        f"**Iris-specific objective:** {target_objective:.2f} ({target_objective - current_objective:+.2f} vs no-HC current baseline)",
        f"**Generic composite change vs no-HC current baseline:** {geo - current_geo:+.2f}",
        "",
        no_hc_note,
        "",
        "> The old published `83.63` score used `Hedione HC` and the generic optimizer. The relevant direct comparison for this run is the no-HC normalized baseline above.",
        "",
        f"**Batch:** {BATCH_ML:.2f} mL · concentrate {total_ul:.0f} µL · {total_ul / BATCH_UL * 100:.1f}% concentrate",
        "",
        "## Axis scores",
        "",
        "| Axis | Score |",
        "|---|---:|",
    ]
    for axis in AXIS_WEIGHTS:
        lines.append(f"| {axis} | {float(detail.get(axis, 0.0)):.1f} |")
    lines += [
        "",
        "## Formula",
        "",
        "| # | Material | Dilution | Amount (µL) | Amount (mL) |",
        "|--:|---|---|---:|---:|",
    ]
    for idx, (material, amount) in enumerate(sorted(ing.items(), key=lambda kv: (-kv[1], kv[0])), start=1):
        lines.append(f"| {idx} | {material} | {format_dilution(material)} | {amount:.0f} | {amount/1000.0:.3f} |")
    lines += [
        f"| — | Ethanol 96% | — | {ethanol_ul:.0f} | {ethanol_ul/1000.0:.3f} |",
        f"| — | **TOTAL** | — | **{BATCH_UL}** | **{BATCH_ML:.3f}** |",
        "",
        "## Why this is better than the old generic pass",
        "",
        "- `Alpha Irone`, `Myristic Acid`, `Hedione`, `Koavone`, and `Orivone` were protected as iris identity materials.",
        "- `Habanolide`, `Iso E Super`, `Dihydromyrcenol`, and `Ambrox Super` were capped so support materials could not flatten the accord into generic clean-woody musk.",
        "- Small realism traces were restored: `Grapefruit FCF`, `Alpha Isomethyl Ionone`, `Irotyl`, and `Violet Fleuressence`.",
        "- `Hedione HC` was removed and its role reallocated into `Hedione`, since you said you do not currently have HC.",
        "",
        "## Mixing note",
        "",
        "Build base first, then heart, then top. Let the concentrate marry 48 h before bottling, then macerate the finished EDP 2–4 weeks.",
        "",
        "## Current 30 mL comparison",
        "",
        f"- Current concentrate: `{current_total:.0f} µL` ({current_total / BATCH_UL * 100:.1f}%)",
        f"- New v2 concentrate: `{total_ul:.0f} µL` ({total_ul / BATCH_UL * 100:.1f}%)",
        f"- No-HC current baseline objective: `{current_objective:.2f}`",
        f"- New v2 objective: `{target_objective:.2f}`",
        "- The new build is slightly richer and more iris-specific, but it is still inside a realistic EDP range.",
    ]
    return "\n".join(lines)


def render_booster_md(target: dict[str, float]) -> str:
    additions = []
    overshoots = []
    alpha_irone_missing = 0.0
    for material in sorted(set(CURRENT_30) | set(target)):
        cur = CURRENT_30.get(material, 0.0)
        tgt = target.get(material, 0.0)
        if tgt > cur + 0.5:
            if material == "Alpha Irone":
                alpha_irone_missing = tgt - cur
                continue
            additions.append((material, tgt - cur, cur, tgt))
        elif cur > tgt + 0.5:
            overshoots.append((material, cur - tgt, cur, tgt))

    if alpha_irone_missing > 0:
        compensation = {
            "Orivone": 50.0,
            "Koavone": 30.0,
            "Heliotropal": 15.0,
            "Beta Ionone": 10.0,
            "Carrot Seed EO": 5.0,
        }
        index = {material: i for i, (material, *_rest) in enumerate(additions)}
        for material, extra in compensation.items():
            if material in index:
                i = index[material]
                m, delta, cur, tgt = additions[i]
                additions[i] = (m, delta + extra, cur, tgt)
            else:
                additions.append((material, extra, CURRENT_30.get(material, 0.0), target.get(material, 0.0)))

    add_total = sum(delta for _, delta, _, _ in additions)
    final_total = 30000.0 + add_total
    target_total = sum(target.values())
    lines = [
        "# Photorealistic Iris — current batch booster v2",
        "",
        "**Assumption:** your current bottle matches `Photorealistic_Iris_30mL_optimized.md`.",
        "**Goal:** shift that bottle toward the dedicated v2 profile using additions only.",
        "**Stock note:** this add-only path has been adjusted for your current inventory: **no `Alpha Irone` assumed in stock**. The fresh-remake / replacement formulas still keep `Alpha Irone`.",
        "",
        f"**Aroma-chem to add:** {add_total:.0f} µL ({add_total/1000.0:.3f} mL)",
        f"**Estimated final bottle volume after booster:** {final_total:.0f} µL ({final_total/1000.0:.3f} mL)",
        "",
        "> This path cannot subtract materials. It corrects deficits only. Materials that the old batch already carries in excess remain overshot.",
        "> You need at least this much headspace, or the equivalent amount already sprayed/decanted from the bottle.",
        "> Because `Alpha Irone` is not available, this booster uses the best available iris-shape compensation instead: more `Orivone`, `Koavone`, `Alpha Isomethyl Ionone`, `Heliotropal`, and supporting ionones. It will move the bottle in the right direction, but it is not a true 1:1 irone restoration.",
        "",
        "## Add these to the current batch",
        "",
        "| # | Material | Dilution | Add (µL) | Current (µL) | Reference v2 target (µL) |",
        "|--:|---|---|---:|---:|---:|",
    ]
    for idx, (material, delta, cur, tgt) in enumerate(sorted(additions, key=lambda row: (-row[1], row[0])), start=1):
        lines.append(f"| {idx} | {material} | {format_dilution(material)} | {delta:.0f} | {cur:.0f} | {tgt:.0f} |")

    lines += [
        "",
        "## Materials that remain high in the current bottle",
        "",
        "| Material | Current (µL) | v2 target (µL) | Overshoot (µL) |",
        "|---|---:|---:|---:|",
    ]
    for material, delta, cur, tgt in sorted(overshoots, key=lambda row: (-row[1], row[0])):
        lines.append(f"| {material} | {cur:.0f} | {tgt:.0f} | {delta:.0f} |")

    lines += [
        "",
        "## Read of the booster",
        "",
        "- It pushes more iris identity, more fatty texture, and more floral-violet realism.",
        "- It does not try to fight the old batch by piling on amber or musk.",
        "- It is the right move if the current bottle feels too clean-woody, too fresh, or not rooty enough.",
        "- Without `Alpha Irone`, the correction is more buttery-powdery / violet-rooty than truly irone-realistic. The remake formula is still the more correct path.",
        "",
        "## Procedure",
        "",
        "1. Add the materials in descending volume order.",
        "2. Swirl gently after every 3–4 additions.",
        "3. Rest 72 h minimum before judging.",
        "4. Judge on skin, not just blotter. This accord changes materially after a few days.",
        "",
        "## Better option if you have no headspace",
        "",
        f"Use `{REFILL_MD.name}` and make a replacement mini-batch in the amount of perfume already missing from the bottle.",
    ]
    return "\n".join(lines)


def render_refill_md(target: dict[str, float]) -> str:
    total_ul = sum(target.values())
    lines = [
        "# Photorealistic Iris — replacement mini-batches v2",
        "",
        "**Use this if some perfume is already gone from the bottle and you want a refill that matches the new v2 profile.**",
        "",
        f"**30 mL parent formula concentrate:** {total_ul:.0f} µL ({total_ul / BATCH_UL * 100:.2f}%)",
        "",
        "| # | Material | Dilution | 5 mL refill (µL) | 7 mL refill (µL) | 10 mL refill (µL) |",
        "|--:|---|---|---:|---:|---:|",
    ]
    for idx, (material, amount) in enumerate(sorted(target.items(), key=lambda kv: (-kv[1], kv[0])), start=1):
        lines.append(
            f"| {idx} | {material} | {format_dilution(material)} | "
            f"{amount * 5 / 30:.1f} | {amount * 7 / 30:.1f} | {amount * 10 / 30:.1f} |"
        )
    conc_5 = total_ul * 5 / 30
    conc_7 = total_ul * 7 / 30
    conc_10 = total_ul * 10 / 30
    lines += [
        f"| — | **Concentrate total** | — | **{conc_5:.1f}** | **{conc_7:.1f}** | **{conc_10:.1f}** |",
        f"| — | Ethanol 96% | — | **{5000-conc_5:.1f}** | **{7000-conc_7:.1f}** | **{10000-conc_10:.1f}** |",
        "",
        "## Notes",
        "",
        "- Amounts below 1 µL should be pre-diluted or ignored; they are trace-shape materials.",
        "- These refill batches are cleaner than the add-only booster because they match the v2 profile directly instead of correcting an older bottle in place.",
    ]
    return "\n".join(lines)


def main() -> None:
    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)

    current_no_hc_eval = dict(CURRENT_30)
    current_no_hc_eval["Hedione"] = current_no_hc_eval.get("Hedione", 0.0) + current_no_hc_eval.pop("Hedione HC")
    current_score, current_geo, current_detail = photoreal_objective(normalize_seed(current_no_hc_eval), scorer)
    print(f"Current normalized/no-HC baseline: geo={current_geo:.3f} objective={current_score:.3f}")

    seed_results = []
    for label, seed in (
        ("current_no_hc_seed", CURRENT_NO_HC_SEED),
        ("manual_photoreal_seed", SEED_V2),
    ):
        best_ing, best_score, best_geo, best_detail = optimize_seed(seed, scorer, label)
        seed_results.append((best_score, label, best_ing, best_geo, best_detail))

    best_score, best_label, best_ing, best_geo, best_detail = max(seed_results, key=lambda row: row[0])
    print(f"Selected seed: {best_label} -> geo={best_geo:.3f} objective={best_score:.3f}")

    OUTPUT_MD.write_text(
        render_new_batch_md(best_ing, best_geo, best_detail, current_geo, current_score, best_score),
        encoding="utf-8",
    )
    BOOSTER_MD.write_text(render_booster_md(best_ing), encoding="utf-8")
    REFILL_MD.write_text(render_refill_md(best_ing), encoding="utf-8")

    payload = {
        "current_baseline": {
            "objective": current_score,
            "geo": current_geo,
            "detail": current_detail,
            "concentrate_ul": sum(normalize_seed(current_no_hc_eval).values()),
        },
        "selected_seed": best_label,
        "objective": best_score,
        "geo": best_geo,
        "detail": best_detail,
        "ingredients": best_ing,
        "dilutions": DILUTIONS,
        "current_30_formula": CURRENT_30,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Wrote {OUTPUT_MD}")
    print(f"Wrote {BOOSTER_MD}")
    print(f"Wrote {REFILL_MD}")
    print(f"Wrote {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
