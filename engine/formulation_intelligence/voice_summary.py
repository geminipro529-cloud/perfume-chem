"""Compact construction-complexity summary for composed formulas.

Diagnostics only: it simulates the composed rows, runs the existing
``analyze_construction_complexity`` profile and condenses the modeled
headspace distribution into per-window detectable components and effective
voices, plus ``one_note`` / ``crowded`` / ``similar_to_variant_<n>`` smell-check
flags.  Nothing here changes a formula row.

AGENTS.md Rule 1: OAV is a detection-related diagnostic, never perceived
contribution, intensity, pleasantness, beauty or an optimizer objective.  The
summary therefore carries no overall score and a fixed note saying so.

(The file name avoids the complexity census discovery terms on purpose: this
is a reporting adapter over ``engine.perception.construction_complexity``, not
a new complexity module.)
"""

from __future__ import annotations

from math import isfinite
from typing import Any, Mapping, Sequence

from engine.perception.construction_complexity import (
    ConstructionComplexityInputs,
    _dominant_name,
    _jensen_shannon_distance,
    _perceptible_distribution,
    analyze_construction_complexity,
)

SUMMARY_SCHEMA = "complexity_summary_v1"
WINDOW_ORDER = ("opening", "top", "heart", "late_heart", "drydown")
# one_note and crowded look at the windows a wearer lives with longest.
LATE_WINDOWS = ("heart", "late_heart", "drydown")

# Fewer than 2.5 equal-weight modeled voices: at most two things plus a trace.
ONE_NOTE_MAX_EFFECTIVE_VOICES = 2.5
# One material holding 60%+ of the summed OAV (OAV >= 1) outweighs all other detectable rows combined.
ONE_NOTE_MIN_TOP_SHARE = 0.60
# Weiss 2012 "olfactory white" converged at roughly 30 intensity-equated components;
# 10+ near-equal modeled voices is the screening floor for that risk, not the effect itself.
CROWDED_MIN_EFFECTIVE_VOICES = 10.0
# Near-equal: Shannon evenness this high means no voice stands clearly above the rest.
CROWDED_MIN_EVENNESS = 0.90
# No foreground: the loudest modeled voice holds under a fifth of the activity.
CROWDED_MAX_TOP_SHARE = 0.20
# Jensen-Shannon distance (base 2, 0..1) below 0.15 on average across windows = nearly the same profile.
SIMILAR_MAX_MEAN_JS_DISTANCE = 0.15
# Rows that the summary rounds for display.
_DIGITS = 2

SCREENING_NOTE = (
    "Model screening numbers for a smell check, not a beauty or quality score. "
    "Voices are modeled from odour-threshold arithmetic; only smelling the blend tells you what you get."
)
_WEISS_2012 = (
    "Weiss et al. 2012, PNAS, 'Perceptual convergence of multi-component mixtures "
    "in olfaction implies an olfactory white'"
)


def _round(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    return round(number, _DIGITS) if isfinite(number) else None


def _formula_inputs(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, float], dict[str, float], list[str], list[dict[str, str]]]:
    """Collapse rows into simulator inputs keyed by identity name.

    Two rows of one identity at different stock strengths are merged at the
    combined volume with the volume-weighted fraction, so the active amount is
    unchanged.  Weighed (mg) rows have no liquid volume and are skipped.
    """

    volumes: dict[str, float] = {}
    actives: dict[str, float] = {}
    character: list[str] = []
    skipped: list[dict[str, str]] = []
    for row in rows:
        name = str(row.get("identity_name") or row.get("material") or "").strip()
        if not name:
            continue
        if str(row.get("amount_unit") or "") != "uL":
            skipped.append({
                "material": name,
                "reason": f"weighed {row.get('amount_unit') or 'unknown'} row has no liquid volume to simulate",
            })
            continue
        volume = float(row.get("amount_decimal") or 0)
        fraction = float(row.get("stock_fraction_decimal") or 1)
        if volume <= 0:
            continue
        volumes[name] = volumes.get(name, 0.0) + volume
        actives[name] = actives.get(name, 0.0) + volume * fraction
        if str(row.get("role") or "") == "character" and name not in character:
            character.append(name)
    dilutions = {name: actives[name] / volumes[name] for name in volumes}
    return volumes, dilutions, character, skipped


def simulate_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[Any, tuple[Any, ...]]:
    """Build ``(state, frames)`` for composed rows the way ``engine.workbench`` does."""

    from engine.pipeline.formula_state import build_formula_state
    from engine.pipeline.simulator import simulate_formula

    volumes, dilutions, _, _ = _formula_inputs(rows)
    state = build_formula_state(volumes, dilutions)
    frames = tuple(simulate_formula(volumes, dilutions, initial_state=state))
    return state, frames


def _odour_activity_lead(materials: Sequence[Any]) -> tuple[str | None, float | None]:
    """Largest share of the summed OAV over rows at OAV >= 1 (a detection-side ratio)."""

    values = {}
    for material in materials:
        value = material.oav
        if value is not None and isfinite(float(value)) and float(value) >= 1.0:
            values[str(material.name)] = float(value)
    total = sum(values.values())
    if total <= 0:
        return None, None
    name = max(values, key=lambda key: (values[key], key))
    return name, values[name] / total


def _window_entry(
    summary: Mapping[str, Any],
    dominant: str | None,
    lead: tuple[str | None, float | None],
) -> dict[str, Any]:
    return {
        "label": str(summary.get("label")),
        "detectable_components": int(summary.get("modeled_perceptible_count") or 0),
        "of_materials": int(summary.get("material_count") or 0),
        "effective_voices": _round(summary.get("effective_component_count")),
        "evenness": _round(summary.get("evenness")),
        "top_share": _round(summary.get("top1_share")),
        "top_material": dominant,
        "odour_activity_lead": lead[0],
        "odour_activity_lead_share": _round(lead[1]),
    }


def complexity_summary(
    rows: Sequence[Mapping[str, Any]],
    *,
    simulation: tuple[Any, Sequence[Any]] | None = None,
) -> dict[str, Any]:
    """Return the compact ``complexity_summary`` for one formula's rows.

    ``simulation`` is an optional precomputed ``(state, frames)`` pair for the
    same rows, so a caller that already simulated them need not do it twice.
    """

    return _summarize(rows, simulation)[0]


def _summarize(
    rows: Sequence[Mapping[str, Any]],
    simulation: tuple[Any, Sequence[Any]] | None,
) -> tuple[dict[str, Any], dict[str, dict[str, float]]]:
    volumes, _, character, skipped = _formula_inputs(rows)
    result: dict[str, Any] = {
        "schema": SUMMARY_SCHEMA,
        "status": "AVAILABLE",
        "note": SCREENING_NOTE,
        "windows": [],
        "opening_to_drydown_change": None,
        "foreground_materials": [],
        "foreground_background": [],
        "flags": [],
        "skipped_rows": skipped,
        "limitations": [],
        "forbidden_claims": [],
        "overall_score": None,
    }
    if not volumes:
        result["status"] = "UNAVAILABLE"
        result["reason"] = "no liquid rows to simulate"
        return result, {}
    try:
        state, frame_seq = simulation if simulation is not None else simulate_rows(rows)
        frames = tuple(frame_seq)
        state_names = {str(material.name) for material in state.materials}
        foreground = tuple(name for name in character if name in state_names)
        background = tuple(sorted(state_names.difference(foreground)))
        inputs = (
            ConstructionComplexityInputs(
                foreground_materials=foreground,
                background_materials=background,
            )
            if foreground and background
            else None
        )
        profile = analyze_construction_complexity(state, frames, inputs=inputs).as_dict()
    except Exception as error:  # advisory: a model failure must not fail the design
        result["status"] = "ERROR"
        result["reason"] = f"summary could not run: {type(error).__name__}: {error}"
        return result, {}

    axes = profile["axes"]
    distributions = {
        str(frame.label): _perceptible_distribution(frame.state.materials) for frame in frames
    }
    leads = {str(frame.label): _odour_activity_lead(frame.state.materials) for frame in frames}
    windows = [
        _window_entry(
            summary,
            _dominant_name(distributions.get(str(summary["label"])) or {}),
            leads.get(str(summary["label"]), (None, None)),
        )
        for summary in axes["modeled_headspace_distribution"]["metrics"]["windows"]
    ]
    result["windows"] = windows
    first, last = distributions.get(WINDOW_ORDER[0]), distributions.get(WINDOW_ORDER[-1])
    if first is not None and last is not None:
        result["opening_to_drydown_change"] = _round(_jensen_shannon_distance(first, last))
    foreground_axis = axes["foreground_background"]
    if foreground_axis["status"] == "AVAILABLE":
        result["foreground_materials"] = list(foreground)
        result["foreground_background"] = [
            {
                "label": window["label"],
                "foreground_share": _round(window["foreground_share"]),
                "background_share": _round(window["background_share"]),
            }
            for window in foreground_axis["metrics"]["windows"]
        ]
    result["flags"] = _flags(windows)
    result["limitations"] = list(profile["limitations"])
    result["forbidden_claims"] = list(profile["forbidden_claims"])
    return result, distributions


def _flags(windows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    late = [window for window in windows if window["label"] in LATE_WINDOWS]
    flags: list[dict[str, Any]] = []
    few_voices = bool(late) and all(
        (window["effective_voices"] or 0.0) < ONE_NOTE_MAX_EFFECTIVE_VOICES for window in late
    )
    leads = {window["odour_activity_lead"] for window in late}
    one_lead = (
        bool(late)
        and len(leads) == 1
        and None not in leads
        and all((window["odour_activity_lead_share"] or 0.0) >= ONE_NOTE_MIN_TOP_SHARE for window in late)
    )
    if few_voices or one_lead:
        reasons = []
        if few_voices:
            reasons.append(f"fewer than {ONE_NOTE_MAX_EFFECTIVE_VOICES:g} effective voices")
        if one_lead:
            lowest = min(window["odour_activity_lead_share"] or 0.0 for window in late)
            reasons.append(
                f"{next(iter(leads))} holds at least {int(lowest * 100)}% of the modeled odour activity"
            )
        flags.append({
            "flag": "one_note",
            "material": next(iter(leads)) if one_lead else None,
            "message": "one-note risk: smell-check. Through heart and drydown " + " and ".join(reasons) + ".",
        })
    if late and all(
        (window["effective_voices"] or 0.0) >= CROWDED_MIN_EFFECTIVE_VOICES
        and (window["evenness"] or 0.0) >= CROWDED_MIN_EVENNESS
        and (window["top_share"] or 1.0) < CROWDED_MAX_TOP_SHARE
        for window in late
    ):
        flags.append({
            "flag": "crowded",
            "message": (
                "crowded: smell-check. Through heart and drydown the model has "
                f"{CROWDED_MIN_EFFECTIVE_VOICES:g}+ near-equal voices and none in front; "
                "many intensity-matched components can blur into one indistinct smell."
            ),
            "source": _WEISS_2012,
        })
    return flags


def _mean_profile_distance(
    first: Mapping[str, Mapping[str, float]],
    second: Mapping[str, Mapping[str, float]],
) -> float | None:
    distances = []
    for label in WINDOW_ORDER:
        if label not in first or label not in second:
            continue
        distance = _jensen_shannon_distance(first[label], second[label])
        if distance is not None:
            distances.append(distance)
    return sum(distances) / len(distances) if distances else None


def _mark_similar_variants(
    summaries: Sequence[tuple[dict[str, Any], Mapping[str, Mapping[str, float]]] | None],
) -> None:
    for index, entry in enumerate(summaries):
        if entry is None or entry[0].get("status") != "AVAILABLE":
            continue
        for other_index, other in enumerate(summaries):
            if other_index == index or other is None or other[0].get("status") != "AVAILABLE":
                continue
            distance = _mean_profile_distance(entry[1], other[1])
            if distance is not None and distance < SIMILAR_MAX_MEAN_JS_DISTANCE:
                entry[0]["flags"].append({
                    "flag": f"similar_to_variant_{other_index + 1}",
                    "variant": other_index + 1,
                    "mean_profile_distance": _round(distance),
                    "message": f"close to variant {other_index + 1}: the modeled profiles are nearly the same.",
                })


def attach_complexity_summary(
    report: dict[str, Any],
    *,
    simulations: Mapping[int, tuple[Any, Sequence[Any]]] | None = None,
) -> dict[str, Any]:
    """Add ``complexity_summary`` to a design report and each of its variants.

    ``simulations`` maps ``id(formula)`` to a precomputed ``(state, frames)``
    pair for that formula mapping; formulas without one are simulated here.
    Formula rows are never changed.
    """

    from engine.research.contracts import stable_payload_hash

    precomputed = dict(simulations or {})
    computed: dict[int, tuple[dict[str, Any], dict[str, dict[str, float]]]] = {}

    def summary_for(formula: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, float]]]:
        key = id(formula)
        if key not in computed:
            computed[key] = _summarize(formula["rows"], precomputed.get(key))
        return computed[key]

    enhanced = dict(report)
    main = enhanced.get("optimized_formula") or enhanced.get("initial_formula")
    if isinstance(main, Mapping) and main.get("rows"):
        enhanced["complexity_summary"] = summary_for(main)[0]
    variants: list[Any] = []
    variant_summaries: list[tuple[dict[str, Any], dict[str, dict[str, float]]] | None] = []
    for variant in enhanced.get("design_variants") or []:
        formula = variant.get("formula") if isinstance(variant, Mapping) else None
        if isinstance(formula, Mapping) and formula.get("rows"):
            shared, distributions = summary_for(formula)
            summary = {**shared, "flags": list(shared["flags"])}
            variant = {**variant, "complexity_summary": summary}
            variant_summaries.append((summary, distributions))
        else:
            variant_summaries.append(None)
        variants.append(variant)
    if sum(item is not None for item in variant_summaries) > 1:
        _mark_similar_variants(variant_summaries)
    if "design_variants" in enhanced:
        enhanced["design_variants"] = variants
    if "design_sha256" in enhanced:
        enhanced["design_sha256"] = stable_payload_hash(
            {key: value for key, value in enhanced.items() if key != "design_sha256"}
        )
    return enhanced
