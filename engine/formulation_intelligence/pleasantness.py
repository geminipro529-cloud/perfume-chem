"""Crowd-guess pleasantness of a composed formula, window by window.

Source rule: Ma, Tang, Thomas-Danguin & Xu (2020), Chemical Senses -- the
pleasantness of an odour mixture follows the pleasantness of its components
weighted by their intensity.  Here each window's weights are the drydown
model's modelled strength (``intensity``, a Stevens power law of OAV) of the
materials it can detect (OAV >= 1 and intensity > 0, the same filter the
construction-complexity profile uses).  Component values come from the crowd
table (``pleasantness_table.crowd_pleasantness``), with the material's share of
the window's modelled strength as its dose.

AGENTS.md Rule 1: OAV is used only as the detection floor.  The result is a
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
from engine.formulation_intelligence.pleasantness_table import crowd_pleasantness
from engine.perception.construction_complexity import _perceptible_distribution

ESTIMATE_SCHEMA = "pleasantness_estimate_v1"
MIN_COVERAGE = 0.5
LABEL = (
    "Crowd guess: panel averages and hand estimates, weighted by how strongly each "
    "material is modelled to smell in each window. Not a measurement; your own "
    "ratings decide."
)
METHOD = (
    "Ma, Tang, Thomas-Danguin & Xu (2020) Chemical Senses: mixture pleasantness follows "
    "component pleasantness weighted by component intensity. Weights are modelled "
    "strength (intensity) from the drydown model, detectable materials only "
    "(OAV >= 1, intensity > 0); OAV is used only as that detection floor. "
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


def _score_mix(shares: Mapping[str, float]) -> dict[str, Any]:
    """Strength-weighted crowd pleasantness of one mix of detectable shares."""

    rated: dict[str, tuple[float, Any]] = {}
    unrated: list[str] = []
    dose_adjusted: list[str] = []
    for name, share in shares.items():
        crowd = crowd_pleasantness(name, strength_share=share)
        if crowd is None:
            unrated.append(name)
            continue
        rated[name] = (share, crowd)
        base = crowd_pleasantness(name)
        if base is not None and not math.isclose(crowd.value, base.value, abs_tol=1e-9):
            dose_adjusted.append(name)
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
        "dose_adjusted": sorted(dose_adjusted),
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
