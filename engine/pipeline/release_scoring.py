"""Unified release scoring shared by the canonical pipeline and optimizer surfaces."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Mapping

from engine.optimizer.models import FormulaVector, ObjectiveWeights
from engine.optimizer.scoring import FormulaScorer

_DETERMINISTIC_REPAIRABLE_GATES = {
    "safety_ifra_allergen",
    "pipette_floor_neat_traces",
    "exact_subtotal",
    "robustness_perturbation",
}

_UNSUPPORTED_PERFORMANCE_AXES = {
    "longevity": "HEURISTIC_UNCALIBRATED_NOT_SKIN_LIFE",
    "sillage": "HEURISTIC_UNCALIBRATED_NOT_MEASURED_SILLAGE",
    "skin_performance": "HEURISTIC_UNVALIDATED_NOT_SKIN_OUTCOME",
}


@dataclass(frozen=True, slots=True)
class UnifiedScorePayload:
    scores: dict[str, Any]
    industry_10: dict[str, float | None]
    provenance: dict[str, Any]
    ranking: dict[str, Any]
    science_penalty: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "scores": dict(self.scores),
            "industry_10": dict(self.industry_10),
            "provenance": dict(self.provenance),
            "ranking": dict(self.ranking),
            "science_penalty": round(float(self.science_penalty), 3),
        }


def _extract_balance_fit(gate_report: Mapping[str, Any]) -> float | None:
    for gate in gate_report.get("gates", []):
        if gate.get("gate") != "perfume_knowledge":
            continue
        pyr = (gate.get("data") or {}).get("pyramid", {})
        fit = pyr.get("overall_fit")
        if fit is not None:
            if isinstance(fit, bool):
                return None
            try:
                parsed = float(fit)
            except (TypeError, ValueError):
                return None
            if math.isfinite(parsed):
                return min(100.0, max(0.0, parsed * 100.0))
            return None
    return None


def _numeric_scores_only(scores: Mapping[str, Any]) -> dict[str, Any]:
    bounded: dict[str, Any] = {}
    for key, value in scores.items():
        if key.startswith("_"):
            bounded[key] = value
        elif isinstance(value, (int, float)):
            bounded[key] = min(100.0, max(0.0, float(value)))
    return bounded


def _formula_science_preflight(
    gate_report: Mapping[str, Any],
) -> tuple[dict[str, Any], float]:
    """Reuse the formula-scoped preflight contract; never rescan the catalogue."""
    preflight = gate_report.get("preflight", {}) or {}
    for check in preflight.get("checks", []) or []:
        if check.get("check_name") != "science_coverage":
            continue
        data = dict(check.get("data", {}) or {})
        return data, float(data.get("confidence_penalty", 0.0) or 0.0)
    return {
        "scope": "formula_runtime",
        "status": "UNAVAILABLE",
        "confidence_penalty": 0.0,
        "limitation": "Formula science preflight was not supplied.",
    }, 0.0


def _build_formula_vector(
    formula: Mapping[str, Any], dilutions: Mapping[str, float]
) -> FormulaVector:
    total_ul = sum(float(v or 0.0) for v in formula["ingredients_ul"].values()) or 1.0
    raw_pct = {
        str(name): (float(ul or 0.0) / total_ul) * 100.0
        for name, ul in formula["ingredients_ul"].items()
    }
    return FormulaVector(
        ingredients=raw_pct,
        dilutions={
            str(name): float(value)
            for name, value in dilutions.items()
            if value is not None
        },
    )


def compute_unified_release_scores(
    formula: Mapping[str, Any],
    oav_result,
    gate_report: Mapping[str, Any],
    *,
    scorer: FormulaScorer | None = None,
) -> UnifiedScorePayload:
    scorer = scorer or FormulaScorer(ObjectiveWeights())
    fv = _build_formula_vector(formula, formula.get("dilutions", {}) or {})
    scorer._material_oavs = {
        row.name: (row.oav or 0.0) for row in oav_result.material_rows
    }
    raw_scores = scorer.score(fv, formula_state=oav_result.state)
    scores = _numeric_scores_only(raw_scores)

    percept = [row for row in oav_result.material_rows if (row.oav or 0.0) >= 1.0]
    len(percept)
    oavs = [float(row.oav or 0.0) for row in percept]
    total_oav = sum(oavs) or 1.0
    opening_oav = sum(float(row.oav or 0.0) for row in percept if row.note == "top")
    base_oav = sum(float(row.oav or 0.0) for row in percept if row.note == "base")
    top_oav = sum(float(row.oav or 0.0) for row in percept if row.note == "top")

    impact = min(100.0, math.log10(opening_oav + 1.0) * 12.0)
    tenacity = min(100.0, base_oav / total_oav * 130.0)
    diffusion = min(100.0, max(0.0, (total_oav / 1000.0) * 5.0))
    leaders = {
        leader["material"]
        for window in oav_result.time_windows
        for leader in window.dominant_oav[:1]
    }
    bloom = min(100.0, len(leaders) * 20.0)
    lift = min(100.0, top_oav / total_oav * 100.0)
    balance = _extract_balance_fit(gate_report)
    balance_reason = (
        None if balance is not None else "PYRAMID_OVERALL_FIT_UNAVAILABLE"
    )

    if len(oav_result.time_windows) >= 3:
        deltas = []
        windows = list(oav_result.time_windows)
        for idx in range(len(windows) - 1):
            f1 = windows[idx].family_envelope
            f2 = windows[idx + 1].family_envelope
            keys = set(f1) | set(f2)
            delta = sum(
                abs(float(f2.get(k, 0.0)) - float(f1.get(k, 0.0))) for k in keys
            ) / max(len(keys), 1)
            deltas.append(delta)
        mean_delta = statistics.mean(deltas) if deltas else 0.0
        std_delta = statistics.pstdev(deltas) if len(deltas) > 1 else 0.0
        if mean_delta < 0.05:
            temporal_coherence = 100.0  # intentionally linear: not penalized
        else:
            temporal_coherence = max(
                0.0, min(100.0, 100.0 - std_delta / max(mean_delta, 0.01) * 15.0)
            )
        temporal_reason = None
    else:
        temporal_coherence = None
        temporal_reason = "INSUFFICIENT_TEMPORAL_WINDOWS"

    data_quality = 100.0
    fallback_reasons: list[str] = []
    for row in oav_result.material_rows:
        source = str(row.odt_source or "").lower()
        if any(
            token in source
            for token in (
                "unverified:",
                "estimated:",
                "profile:",
                "registry:",
            )
        ):
            data_quality -= 2.0
            fallback_reasons.append(f"Low ODT authority: {row.name}")
        elif "derived:" in source:
            data_quality -= 0.5
            fallback_reasons.append(f"Derived ODT: {row.name}")
    data_quality = max(0.0, data_quality)

    active_rows = [
        row for row in oav_result.material_rows if float(row.active_ul or 0.0) > 0.0
    ]
    canonical_oav_rows: list[tuple[Any, float]] = []
    missing_canonical_oav_materials: list[str] = []
    for row in active_rows:
        canonical_oav = row.canonical_oav
        if isinstance(canonical_oav, bool) or canonical_oav is None:
            missing_canonical_oav_materials.append(row.name)
            continue
        parsed_oav = float(canonical_oav)
        if not math.isfinite(parsed_oav) or parsed_oav < 0.0:
            missing_canonical_oav_materials.append(row.name)
            continue
        canonical_oav_rows.append((row, parsed_oav))
    canonical_oav_count = len(canonical_oav_rows)
    canonical_perceptible_oavs = [
        value for _, value in canonical_oav_rows if value >= 1.0
    ]
    if (
        len(canonical_oav_rows) == len(active_rows)
        and len(canonical_perceptible_oavs) >= 2
    ):
        oav_range = max(canonical_perceptible_oavs) / max(
            min(canonical_perceptible_oavs), 0.01
        )
        oav_balance = max(
            0.0, min(100.0, 100.0 - math.log10(max(oav_range, 1.0)) * 15.0)
        )
        oav_balance_reason = None
    elif not canonical_oav_rows:
        oav_balance = None
        oav_balance_reason = "CANONICAL_OAV_COVERAGE_UNAVAILABLE"
    elif len(canonical_oav_rows) < len(active_rows):
        oav_balance = None
        oav_balance_reason = "CANONICAL_OAV_COVERAGE_INCOMPLETE"
    else:
        oav_balance = None
        oav_balance_reason = "INSUFFICIENT_PERCEPTIBLE_CANONICAL_OAV_VALUES"

    cost_efficiency: float | None = None
    cost_efficiency_reason = "SUPPLIER_PRICE_DATA_UNAVAILABLE"
    priced_material_count = 0
    required_price_count = len(active_rows)
    missing_price_materials: list[str] = []
    price_lookup_error_type: str | None = None
    try:
        from engine.data_spine.loader import load_registry

        registry = load_registry()
        priced_rows: list[tuple[Any, float]] = []
        for row in active_rows:
            lookup_name = str(getattr(row, "canonical_name", "") or row.name)
            entry = registry.get(lookup_name)
            supplier = getattr(entry, "supplier", None) if entry is not None else None
            price = getattr(supplier, "perfumersworld_price_usd_per_g", None)
            try:
                parsed_price = float(price)
            except (TypeError, ValueError):
                parsed_price = math.nan
            if math.isfinite(parsed_price) and parsed_price > 0.0:
                priced_rows.append((row, parsed_price))
            else:
                missing_price_materials.append(row.name)
        priced_material_count = len(priced_rows)
        if required_price_count > 0 and priced_material_count == required_price_count:
            total_cost = sum(
                price * float(row.active_ul or 0.0) / 1000.0
                for row, price in priced_rows
            )
            canonical_total_oav = sum(value for _, value in canonical_oav_rows)
            if (
                len(canonical_oav_rows) == len(active_rows)
                and canonical_total_oav > 0.0
            ):
                efficiency = canonical_total_oav / max(total_cost, 0.01)
                cost_efficiency = min(100.0, efficiency * 10.0)
                cost_efficiency_reason = None
            else:
                cost_efficiency_reason = (
                    "OAV_BASIS_FOR_COST_EFFICIENCY_UNAVAILABLE"
                )
        elif priced_material_count > 0:
            cost_efficiency_reason = "SUPPLIER_PRICE_COVERAGE_INCOMPLETE"
    except Exception as exc:  # pragma: no cover - cost data may be partial
        fallback_reasons.append(f"Cost efficiency unavailable: {type(exc).__name__}")
        cost_efficiency_reason = "SUPPLIER_PRICE_LOOKUP_ERROR"
        price_lookup_error_type = type(exc).__name__

    industry_10 = {
        "impact": round(impact, 1),
        "tenacity": round(tenacity, 1),
        "diffusion": round(diffusion, 1),
        "bloom": round(bloom, 1),
        "top_dominance": round(100.0 - lift, 1),
        "lift": round(lift, 1),  # deprecated: use top_dominance (inverted for clarity)
        "family_alignment": None,
        "character": None,  # deprecated: use family_alignment
        "balance": None if balance is None else round(balance, 1),
        "temporal_coherence": (
            None if temporal_coherence is None else round(temporal_coherence, 1)
        ),
        "data_quality": round(data_quality, 1),
        "oav_balance": None if oav_balance is None else round(oav_balance, 1),
        "versatility": (
            None if oav_balance is None else round(oav_balance, 1)
        ),  # deprecated: use oav_balance
        "cost_efficiency": (
            None if cost_efficiency is None else round(cost_efficiency, 1)
        ),
    }
    industry_10_availability = {
        key: {"available": value is not None, "reason_code": None}
        for key, value in industry_10.items()
    }
    industry_10_availability.update({
        "family_alignment": {
            "available": False,
            "reason_code": "INDEPENDENT_FAMILY_ALIGNMENT_EVIDENCE_UNAVAILABLE",
        },
        "character": {
            "available": False,
            "reason_code": "INDEPENDENT_CHARACTER_EVIDENCE_UNAVAILABLE",
            "deprecated": True,
            "replacement": "family_alignment",
        },
        "balance": {
            "available": balance is not None,
            "reason_code": balance_reason,
        },
        "temporal_coherence": {
            "available": temporal_coherence is not None,
            "reason_code": temporal_reason,
            "observed_windows": len(oav_result.time_windows),
            "required_windows": 3,
        },
        "oav_balance": {
            "available": oav_balance is not None,
            "reason_code": oav_balance_reason,
            "canonical_oav_materials": canonical_oav_count,
            "required_canonical_oav_materials": len(active_rows),
            "missing_canonical_oav_materials": sorted(
                set(missing_canonical_oav_materials)
            ),
            "perceptible_canonical_oav_materials": len(
                canonical_perceptible_oavs
            ),
        },
        "versatility": {
            "available": oav_balance is not None,
            "reason_code": oav_balance_reason,
            "canonical_oav_materials": canonical_oav_count,
            "required_canonical_oav_materials": len(active_rows),
            "missing_canonical_oav_materials": sorted(
                set(missing_canonical_oav_materials)
            ),
            "perceptible_canonical_oav_materials": len(
                canonical_perceptible_oavs
            ),
            "deprecated": True,
            "replacement": "oav_balance",
        },
        "cost_efficiency": {
            "available": cost_efficiency is not None,
            "reason_code": cost_efficiency_reason,
            "priced_materials": priced_material_count,
            "required_materials": required_price_count,
            "missing_price_materials": sorted(set(missing_price_materials)),
            "error_type": price_lookup_error_type,
        },
    })

    formula_science_coverage, science_penalty = _formula_science_preflight(
        gate_report
    )
    authoritative_inputs: list[str] = []
    heuristic_inputs: list[str] = []
    for row in oav_result.material_rows:
        odt_source = str(row.odt_source or "").lower()
        if any(token in odt_source for token in ("peer_reviewed", "literature:")):
            authoritative_inputs.append(f"odt:{row.name}")
        else:
            heuristic_inputs.append(f"odt:{row.name}")
        gamma_source = str(getattr(row, "gamma_source", "") or "").lower()
        if gamma_source.startswith("heuristic:") or gamma_source.startswith(
            "fallback:"
        ):
            heuristic_inputs.append(f"gamma:{row.name}")
        elif gamma_source:
            authoritative_inputs.append(f"gamma:{row.name}")
    failed_gates = [
        gate.get("gate")
        for gate in gate_report.get("gates", [])
        if gate.get("status") == "FAIL"
    ]
    # HOLD gates block release on missing data; no dose repair can supply it.
    held_gates = [
        gate.get("gate")
        for gate in gate_report.get("gates", [])
        if gate.get("status") == "HOLD"
    ]
    repairable = [
        gate for gate in failed_gates if gate in _DETERMINISTIC_REPAIRABLE_GATES
    ]
    nonrepairable = [
        gate for gate in failed_gates if gate not in _DETERMINISTIC_REPAIRABLE_GATES
    ]
    confidence_penalties = []
    if science_penalty > 0:
        confidence_penalties.append(
            {
                "source": "science_audit",
                "penalty": round(science_penalty, 3),
                "reason": "sparse_science_coverage",
            }
        )
    for reason in fallback_reasons[:20]:
        confidence_penalties.append(
            {"source": "release_scoring", "penalty": 0.5, "reason": reason}
        )
    provenance = {
        "deterministic_sources": [
            "engine.pipeline.formula_state",
            "engine.pipeline.oav_authority",
            "engine.pipeline.gates",
            "engine.optimizer.scoring",
        ],
        "advisory_sources": [
            "engine.science_audit",
            "engine.knowledge.literature_rules",
        ],
        "fallback_reasons": fallback_reasons,
        "science_penalty": round(science_penalty, 3),
        "formula_science_coverage": formula_science_coverage,
        "intelligence_status": getattr(oav_result, "intelligence_status", "UNKNOWN"),
        "intelligence_warning_reasons": list(
            getattr(oav_result, "intelligence_warning_reasons", ()) or ()
        ),
        "authority_rank_score": round(
            float(getattr(oav_result, "authority_rank_score", 0.0)), 3
        ),
        "authoritative_inputs_used": sorted(set(authoritative_inputs)),
        "heuristic_inputs_used": sorted(set(heuristic_inputs)),
        "confidence_penalties": confidence_penalties,
        "industry_10_availability": industry_10_availability,
        "repairability": {
            "failed_gates": failed_gates,
            "held_gates": held_gates,
            "deterministic_repairable": repairable,
            "blocked_rerun_required": nonrepairable,
            "status": (
                "data_required"
                if held_gates and not failed_gates
                else "none_needed"
                if not failed_gates
                else "deterministic"
                if repairable and not nonrepairable
                else "mixed"
                if repairable and nonrepairable
                else "rerun_required"
            ),
        },
        "score_contract": {
            "classification": "HEURISTIC_DIAGNOSTIC_INDICES",
            "scale": {"minimum": 0.0, "maximum": 100.0},
            "release_authority": False,
            "formula_optimization_authority": False,
            "eligible_as_optimizer_selection_evidence": False,
            "measured_search_feature_denylist": [
                "scores.total",
                "industry_10.*",
                "confidence_penalties",
                "oav_balance",
                "oav_derived_intensity",
                "semantic_distance",
                "descriptor_distance",
            ],
            "calibration_required_for_outcome_claims": True,
            "release_authorized_axes": [],
            "axis_authority": {
                key: (
                    _UNSUPPORTED_PERFORMANCE_AXES[key]
                    if key in _UNSUPPORTED_PERFORMANCE_AXES
                    else (
                        "DIAGNOSTIC_AGGREGATE_NOT_RELEASE_AUTHORITY"
                        if key
                        in {
                            "total",
                            "arithmetic_total",
                            "geometric_total",
                        }
                        else "HEURISTIC_DIAGNOSTIC_INDEX"
                    )
                )
                for key in sorted(
                    key for key in scores if not str(key).startswith("_")
                )
            },
            "unsupported_outcome_claims": [
                "estimated_longevity_hours",
                "measured_sillage_or_projection_distance",
                "skin_performance_outcome",
            ],
            "industry_10_authority": (
                "HEURISTIC_DIAGNOSTIC_INDICES_DESPITE_LEGACY_NAME"
            ),
        },
    }
    ranking = {
        "status": "WITHHELD",
        "value": None,
        "diagnostic_total": scores.get("total"),
        "formula_optimization_authority": False,
        "admitted_axes": [],
        "blockers": [
            "No held-out human formula-quality or pleasantness endpoint is admitted for this formula domain.",
            "Headspace/OAV and legacy performance axes are diagnostic screens, not a beauty objective.",
            "A finite diagnostic score must not select a formula or authorize recompounding.",
        ],
    }
    return UnifiedScorePayload(
        scores=scores,
        industry_10=industry_10,
        provenance=provenance,
        ranking=ranking,
        science_penalty=science_penalty,
    )
