"""Crowd-guess pleasantness of a composed formula, window by window.

Source rule: Ma, Tang, Thomas-Danguin & Xu (2020), Chemical Senses -- the
pleasantness of an odour mixture follows the pleasantness of its components
weighted by their intensity.  Here each window's weights are the drydown
model's strength estimate (``intensity``, a Stevens power law of each material's
odour activity value) of the materials it can detect (OAV >= 1 and
intensity > 0, the same filter the construction-complexity profile uses).  Component values come from the crowd
table (``pleasantness_table.crowd_pleasantness``), with the material's share of
the window's modelled strength as its dose.

AGENTS.md Rule 1: the weights are a model's strength estimate (a power law of
OAV), not measured intensity, and OAV is not perceived contribution.  The result is a
crowd guess, not measured pleasantness, intensity or liking; it never ranks or
optimizes a formula (``optimization_authority`` is always false) and nothing
here changes a formula row.  Unrated materials are left out of the mean, never
counted as neutral, and coverage says how much of the modelled strength was
rated.  There is no contrast penalty.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from engine.formulation_intelligence.pleasantness_table import SCHEMA as TABLE_SCHEMA
from engine.formulation_intelligence.pleasantness_table import (
    _resolve,
    crowd_pleasantness,
    load_crowd_table,
)
from engine.hedonic_model import HedonicReport
from engine.perception.construction_complexity import _perceptible_distribution

ESTIMATE_SCHEMA = "pleasantness_estimate_v1"
MIN_COVERAGE = 0.5
DOSE_ADJUST_MIN = 0.05  # smallest dose-driven change in a material's value worth listing
LABEL = (
    "Crowd guess: panel averages and hand estimates, weighted by the drydown model's "
    "strength estimate for each material in each window (a power law of its odour "
    "activity value, not measured intensity). Not a measurement; your own ratings decide."
)
METHOD = (
    "Ma, Tang, Thomas-Danguin & Xu (2020) Chemical Senses: mixture pleasantness follows "
    "component pleasantness weighted by component intensity. Weights are the drydown "
    "model's strength estimate, a power law of each material's odour activity value "
    "(OAV). That is a model, not measured intensity; materials below OAV 1 are left out. "
    "P = sum(share * value) / rated share; unrated materials are excluded, not neutral; "
    "no contrast penalty."
)
# Rating card: the 1 h mix averages the two windows that bracket it.
RATING_WINDOWS = (("opening", ("opening",)), ("1h", ("heart", "late_heart")), ("4h", ("drydown",)))


def _rounded_shares(shares: Mapping[str, float], digits: int = 3) -> dict[str, float]:
    """Round shares so the shown values still sum to exactly 1 (largest remainder)."""

    if not shares:
        return {}
    scale = 10 ** digits
    scaled = {name: share * scale for name, share in shares.items()}
    floors = {name: math.floor(value) for name, value in scaled.items()}
    left = round(scale - sum(floors.values()))
    for name in sorted(scaled, key=lambda n: (floors[n] - scaled[n], n))[: max(0, left)]:
        floors[name] += 1
    return {name: floors[name] / scale for name in sorted(shares, key=lambda n: (-shares[n], n))}


def _dose_source(name: str) -> str | None:
    key = _resolve(name)
    return load_crowd_table()["materials"][key].get("dose_source") if key else None


def _score_mix(shares: Mapping[str, float]) -> dict[str, Any]:
    """Strength-weighted crowd pleasantness of one mix of detectable shares."""

    rated: dict[str, tuple[float, Any]] = {}
    unrated: list[str] = []
    dose_adjusted: list[dict[str, Any]] = []
    for name, share in shares.items():
        crowd = crowd_pleasantness(name, strength_share=share)
        if crowd is None:
            unrated.append(name)
            continue
        rated[name] = (share, crowd)
        base = crowd_pleasantness(name)
        if base is not None and abs(crowd.value - base.value) >= DOSE_ADJUST_MIN:
            dose_adjusted.append(
                {
                    "material": name,
                    "base": round(base.value, 3),
                    "used": round(crowd.value, 3),
                    "dose_source": _dose_source(name),
                }
            )
    coverage = sum(share for share, _ in rated.values())
    value = (
        sum(share * crowd.value for share, crowd in rated.values()) / coverage
        if coverage > 0
        else None
    )
    if not shares:
        status = "NO_DETECTABLE_MATERIALS"
    elif coverage <= 0:
        status = "NO_RATED_MATERIALS"
    elif coverage >= MIN_COVERAGE:
        status = "CROWD_GUESS"
    else:
        status = "LOW_COVERAGE"
    contributors = sorted(rated.items(), key=lambda kv: (-kv[1][0] * abs(kv[1][1].value), kv[0]))[:3]
    return {
        "value": value,
        "coverage": coverage,
        "status": status,
        "contributors": [
            {
                "material": name,
                "share": round(share, 3),
                "value": round(crowd.value, 3),
                "source": crowd.source,
            }
            for name, (share, crowd) in contributors
        ],
        "unrated": sorted(unrated),
        "dose_adjusted": sorted(dose_adjusted, key=lambda item: item["material"]),
    }


def _window_entry(label: str, t_seconds: float, shares: Mapping[str, float]) -> dict[str, Any]:
    mix = _score_mix(shares)
    value = mix["value"]
    return {
        "window": label,
        "t_seconds": t_seconds,
        "pleasantness": None if value is None else round(value, 3),
        "score_0_100": None if value is None else round((value + 1.0) * 50),
        "coverage": round(mix["coverage"], 2),
        "status": mix["status"],
        "strength_shares": _rounded_shares(shares),
        "contributors": mix["contributors"],
        "unrated": mix["unrated"],
        "dose_adjusted": mix["dose_adjusted"],
    }


def _mean_shares(mixes: Sequence[Mapping[str, float]]) -> dict[str, float]:
    present = [mix for mix in mixes if mix]
    if not present:
        return {}
    totals: dict[str, float] = {}
    for mix in present:
        for name, share in mix.items():
            totals[name] = totals.get(name, 0.0) + share / len(present)
    total = sum(totals.values())
    return {name: value / total for name, value in totals.items()} if total > 0 else {}


def score_pleasantness(
    rows: Sequence[Mapping[str, Any]],
    simulation: tuple[Any, Sequence[Any]] | None = None,
) -> dict[str, Any]:
    """Crowd-guess pleasantness per modelled window for composed formula rows.

    ``simulation`` is an optional precomputed ``(state, frames)`` pair for the
    same rows (see ``voice_summary.simulate_rows``).
    """

    if simulation is None:
        from engine.formulation_intelligence.voice_summary import simulate_rows

        simulation = simulate_rows(rows)
    _, frames = simulation
    shares_by_window: dict[str, dict[str, float]] = {}
    windows: list[dict[str, Any]] = []
    for frame in frames:
        label = str(frame.label)
        shares = _perceptible_distribution(frame.state.materials)
        shares_by_window[label] = shares
        windows.append(_window_entry(label, float(frame.t_seconds), shares))

    guesses = [w["pleasantness"] for w in windows if w["status"] == "CROWD_GUESS"]
    statuses = {w["status"] for w in windows}
    state = (
        "CROWD_GUESS" if "CROWD_GUESS" in statuses
        else "LOW_COVERAGE" if "LOW_COVERAGE" in statuses
        else "NOT_ESTABLISHED"
    )
    rating_windows: dict[str, dict[str, Any]] = {}
    for key, labels in RATING_WINDOWS:
        shares = _mean_shares([shares_by_window.get(label, {}) for label in labels])
        mix = _score_mix(shares)
        rating_windows[key] = {
            "material_shares": _rounded_shares(shares),
            "crowd_guess": None if mix["value"] is None else round(mix["value"], 3),
            "coverage": round(mix["coverage"], 2),
        }
    return {
        "schema": ESTIMATE_SCHEMA,
        "state": state,
        "label": LABEL,
        "method": METHOD,
        "windows": windows,
        "overall": round(sum(guesses) / len(guesses), 3) if guesses else None,
        "rating_windows": rating_windows,
        "optimization_authority": False,
        "table_schema": TABLE_SCHEMA,
    }


def simulate_report_formulas(report: Mapping[str, Any]) -> dict[int, tuple[Any, tuple[Any, ...]]]:
    """Simulate each distinct formula of a design report once, keyed by ``id(formula)``.

    Shared by the voice summary and the pleasantness estimate so neither has
    to simulate again.  A formula whose simulation fails is left out; each
    consumer then reports its own error.
    """

    from engine.formulation_intelligence.voice_summary import simulate_rows

    formulas = [report.get("optimized_formula") or report.get("initial_formula")]
    formulas += [
        variant.get("formula")
        for variant in report.get("design_variants") or []
        if isinstance(variant, Mapping)
    ]
    simulations: dict[int, tuple[Any, tuple[Any, ...]]] = {}
    for formula in formulas:
        if not isinstance(formula, Mapping) or not formula.get("rows") or id(formula) in simulations:
            continue
        try:
            simulations[id(formula)] = simulate_rows(formula["rows"])
        except Exception:  # advisory: the consumers record the failure themselves
            continue
    return simulations


def attach_pleasantness_estimate(
    report: dict[str, Any],
    *,
    simulations: Mapping[int, tuple[Any, Sequence[Any]]] | None = None,
) -> dict[str, Any]:
    """Fill ``scientific_overlays.pleasantness`` on a design report and its variants.

    ``simulations`` maps ``id(formula)`` to a precomputed ``(state, frames)``
    pair; formulas without one are simulated here, once each.  Formula rows
    are never changed.
    """

    from engine.research.contracts import stable_payload_hash

    precomputed = dict(simulations or {})
    computed: dict[int, dict[str, Any]] = {}

    def estimate_for(formula: Mapping[str, Any]) -> dict[str, Any]:
        key = id(formula)
        if key not in computed:
            try:
                computed[key] = score_pleasantness(formula["rows"], precomputed.get(key))
            except Exception as error:  # advisory: a model failure must not fail the design
                computed[key] = {
                    "schema": ESTIMATE_SCHEMA,
                    "state": "ERROR",
                    "label": LABEL,
                    "reason": f"estimate could not run: {type(error).__name__}: {error}",
                    "optimization_authority": False,
                }
        return computed[key]

    def with_overlay(holder: Mapping[str, Any], formula: Mapping[str, Any]) -> dict[str, Any]:
        overlays = dict(holder.get("scientific_overlays") or {})
        overlays["pleasantness"] = estimate_for(formula)
        return {**holder, "scientific_overlays": overlays}

    enhanced = dict(report)
    main = enhanced.get("optimized_formula") or enhanced.get("initial_formula")
    if isinstance(main, Mapping) and main.get("rows"):
        enhanced = with_overlay(enhanced, main)
    if "design_variants" in enhanced:
        variants = []
        for variant in enhanced.get("design_variants") or []:
            formula = variant.get("formula") if isinstance(variant, Mapping) else None
            if isinstance(formula, Mapping) and formula.get("rows"):
                variant = with_overlay(variant, formula)
            variants.append(variant)
        enhanced["design_variants"] = variants
    if "design_sha256" in enhanced:
        enhanced["design_sha256"] = stable_payload_hash(
            {key: value for key, value in enhanced.items() if key != "design_sha256"}
        )
    return enhanced


def score_hedonic_crowd(
    ingredients: dict[str, float],
    dilutions: dict[str, float] | None = None,
) -> HedonicReport:
    """Compute the crowd-value diagnostic (successor to the legacy ``score_hedonic``) for a formula.

    Each material's value is its crowd-table value
    (``crowd_pleasantness``, no dose adjustment); materials
    without one are excluded, not counted as neutral.  The values are weighted
    by liquid active uL, so this is not the strength-weighted crowd guess in
    ``engine.formulation_intelligence.pleasantness``.

    score = (active-weighted mean value + 1) / 2 * 100.  Contrast between
    pleasant and unpleasant materials is a legitimate construction (chypre,
    leather, animalic accords), so ``hedonic_contrast`` is reported for
    information only and does not change the score.
    """
    dilutions = dilutions or {}
    total_active = 0.0
    rated_active = 0.0
    weighted_sum = 0.0
    valence_list: list[float] = []
    weight_list: list[float] = []
    pleasant_mass = 0.0
    unpleasant_mats: list[dict] = []
    material_scores: list[dict] = []
    diagnostics: list[str] = []
    rated_materials: list[str] = []
    unrated_materials: list[str] = []

    for name, amount in ingredients.items():
        dil = dilutions.get(name, 1.0)
        active = amount * dil
        total_active += active

        crowd = crowd_pleasantness(name)
        valence = None if crowd is None else crowd.value
        if valence is None:
            if active > 0:
                unrated_materials.append(name)
            continue

        if active > 0:
            rated_materials.append(name)
        rated_active += active
        weighted_sum += valence * active
        valence_list.append(valence)
        weight_list.append(active)

        material_scores.append({
            "material": name,
            "valence": valence,
            "amount_uL": round(active, 1),
            "hedonic_contribution": round(valence * active, 1),
        })

        if valence >= 0.3:
            pleasant_mass += active
        elif valence < 0.0:
            unpleasant_mats.append({
                "material": name,
                "valence": valence,
                "amount_uL": round(active, 1),
            })

    rated_active_fraction = rated_active / total_active if total_active > 0 else 0.0
    unrated_active_fraction = (
        (total_active - rated_active) / total_active if total_active > 0 else 0.0
    )
    if total_active <= 0:
        coverage_status = "NO_ACTIVE_MATERIALS"
    elif rated_active <= 0:
        coverage_status = "ZERO_TABLE_COVERAGE"
    elif math.isclose(rated_active, total_active, rel_tol=1e-12, abs_tol=1e-12):
        coverage_status = "FULL_TABLE_COVERAGE"
    else:
        coverage_status = "PARTIAL_TABLE_COVERAGE"

    if total_active <= 0 or rated_active <= 0:
        missing = ", ".join(unrated_materials) if unrated_materials else "none"
        return HedonicReport(
            score=50, weighted_valence=0, pleasantness_class="unknown",
            hedonic_contrast=0, pleasant_fraction=0,
            unpleasant_materials=[], most_pleasant=[],
            diagnostics=[
                "No hedonic data",
                f"Hedonic table coverage: {coverage_status}; unrated labels: {missing}",
                "HEURISTIC_DIAGNOSTIC_INDEX only: the legacy score=50 fallback is not measured full-formula pleasantness or liking.",
            ],
            rated_active_fraction=rated_active_fraction,
            unrated_active_fraction=unrated_active_fraction,
            rated_materials=rated_materials,
            unrated_materials=unrated_materials,
            coverage_status=coverage_status,
        )

    # Weighted mean valence (over rated materials only — unrated are excluded,
    # not penalised as valence=0)
    mean_valence = weighted_sum / rated_active

    # Hedonic contrast: weighted standard deviation
    var_sum = sum(w * (v - mean_valence) ** 2
                  for v, w in zip(valence_list, weight_list))
    contrast = math.sqrt(var_sum / rated_active)

    # Pleasant fraction (of rated mass)
    pleas_frac = pleasant_mass / rated_active

    # Classification
    if mean_valence > 0.7:
        pclass = "highly_pleasant"
    elif mean_valence > 0.5:
        pclass = "pleasant"
    elif mean_valence > 0.3:
        pclass = "moderately_pleasant"
    elif mean_valence > 0.0:
        pclass = "neutral"
    elif mean_valence > -0.2:
        pclass = "challenging"
    else:
        pclass = "discordant"

    # Score: map mean_valence from [-1, 1] to [0, 100]; contrast is not penalised.
    score = (mean_valence + 1.0) / 2.0 * 100
    score = max(0, min(100, score))

    # Sort for top 5
    material_scores.sort(key=lambda x: x["hedonic_contribution"], reverse=True)

    # Diagnostics
    diagnostics.append(f"Hedonic class: {pclass} (mean valence {mean_valence:+.2f})")
    diagnostics.append(
        f"Hedonic contrast {contrast:.2f} (spread of rated values; informational, not scored)"
    )
    if unpleasant_mats:
        names = [f"{m['material']} ({m['valence']:+.2f})" for m in unpleasant_mats]
        diagnostics.append(f"Hedonically negative: {', '.join(names)}")
    if pleas_frac > 0.8:
        diagnostics.append("✓ >80% of rated active mass has positive table valence")
    if coverage_status == "PARTIAL_TABLE_COVERAGE":
        diagnostics.append(
            "Hedonic table coverage is partial: score, class, and pleasant fraction apply only to rated labels; full-formula pleasantness is NOT_ESTABLISHED."
        )
    diagnostics.append(
        "HEURISTIC_DIAGNOSTIC_INDEX only: crowd-table values (panel averages and hand estimates) are not measured full-formula pleasantness or liking."
    )

    return HedonicReport(
        score=round(score, 1),
        weighted_valence=round(mean_valence, 3),
        pleasantness_class=pclass,
        hedonic_contrast=round(contrast, 3),
        pleasant_fraction=round(pleas_frac, 3),
        unpleasant_materials=unpleasant_mats,
        most_pleasant=material_scores[:5],
        diagnostics=diagnostics,
        rated_active_fraction=rated_active_fraction,
        unrated_active_fraction=unrated_active_fraction,
        rated_materials=rated_materials,
        unrated_materials=unrated_materials,
        coverage_status=coverage_status,
    )
