"""Unified release scoring shared by the canonical pipeline and optimizer surfaces."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Mapping

from engine.optimizer.models import FormulaVector, ObjectiveWeights
from engine.optimizer.scoring import FormulaScorer
from engine.science_audit import (
    build_science_audit_contract,
    coverage_confidence_penalty,
)

_DETERMINISTIC_REPAIRABLE_GATES = {
    "safety_ifra_allergen",
    "pipette_floor_neat_traces",
    "exact_subtotal",
    "robustness_perturbation",
}


@dataclass(frozen=True, slots=True)
class UnifiedScorePayload:
    scores: dict[str, Any]
    industry_10: dict[str, float]
    provenance: dict[str, Any]
    science_penalty: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "scores": dict(self.scores),
            "industry_10": dict(self.industry_10),
            "provenance": dict(self.provenance),
            "science_penalty": round(float(self.science_penalty), 3),
        }


def _extract_balance_fit(gate_report: Mapping[str, Any]) -> float:
    for gate in gate_report.get("gates", []):
        if gate.get("gate") != "perfume_knowledge":
            continue
        pyr = (gate.get("data") or {}).get("pyramid", {})
        fit = pyr.get("overall_fit")
        if fit is not None:
            return min(100.0, max(0.0, float(fit) * 100.0))
    return 50.0


def _numeric_scores_only(scores: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in scores.items()
        if isinstance(value, (int, float)) or key.startswith("_")
    }


def _build_formula_vector(
    formula: Mapping[str, Any], dilutions: Mapping[str, float]
) -> FormulaVector:
    total_ul = sum(float(v or 0.0) for v in formula["ingredients_ul"].values()) or 1.0
    pct_ings: dict[str, float] = {}
    for name, ul in formula["ingredients_ul"].items():
        dil = float(dilutions.get(name, 1.0) or 1.0)
        pct_ings[str(name)] = (float(ul or 0.0) * dil / total_ul) * 100.0
    return FormulaVector(ingredients=pct_ings)


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
    raw_scores = scorer.score(fv)
    scores = _numeric_scores_only(raw_scores)

    percept = [row for row in oav_result.material_rows if (row.oav or 0.0) >= 1.0]
    n_percept = len(percept)
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
    else:
        temporal_coherence = 50.0

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

    if oavs:
        oav_range = max(oavs) / max(min(oavs), 0.01)
        versatility = max(
            0.0, min(100.0, 100.0 - math.log10(max(oav_range, 1.0)) * 15.0)
        )
    else:
        versatility = 50.0

    cost_efficiency = 50.0
    try:
        price_data = {}
        from engine.data_spine.loader import data_spine as ds

        if ds:
            for entry in ds.values():
                if hasattr(entry, "perfumersworld_price_usd_per_g"):
                    price_data[entry.canonical_name] = getattr(
                        entry, "perfumersworld_price_usd_per_g", None
                    )
        if price_data:
            total_cost = sum(
                (price_data.get(str(row.name), 1.0) or 1.0) * row.active_ul / 1000.0
                for row in percept
            )
            efficiency = total_oav / max(total_cost, 0.01)
            cost_efficiency = min(100.0, efficiency * 10.0)
    except Exception as exc:  # pragma: no cover - cost data may be partial
        fallback_reasons.append(f"Cost efficiency fallback: {type(exc).__name__}")
        cost_efficiency = 50.0

    industry_10 = {
        "impact": round(impact, 1),
        "tenacity": round(tenacity, 1),
        "diffusion": round(diffusion, 1),
        "bloom": round(bloom, 1),
        "top_dominance": round(100.0 - lift, 1),
        "lift": round(lift, 1),  # deprecated: use top_dominance (inverted for clarity)
        "family_alignment": round(
            max(0.0, min(100.0, float(scores.get("photorealism", 50.0)))), 1
        ),
        "character": round(
            max(0.0, min(100.0, float(scores.get("photorealism", 50.0)))), 1
        ),  # deprecated: use family_alignment
        "balance": round(balance, 1),
        "temporal_coherence": round(temporal_coherence, 1),
        "data_quality": round(data_quality, 1),
        "oav_balance": round(versatility, 1),
        "versatility": round(versatility, 1),  # deprecated: use oav_balance
        "cost_efficiency": round(cost_efficiency, 1),
    }

    science_contract = build_science_audit_contract()
    science_penalty = coverage_confidence_penalty(science_contract)
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
        "repairability": {
            "failed_gates": failed_gates,
            "deterministic_repairable": repairable,
            "blocked_rerun_required": nonrepairable,
            "status": (
                "none_needed"
                if not failed_gates
                else "deterministic"
                if repairable and not nonrepairable
                else "mixed"
                if repairable and nonrepairable
                else "rerun_required"
            ),
        },
    }
    return UnifiedScorePayload(
        scores=scores,
        industry_10=industry_10,
        provenance=provenance,
        science_penalty=science_penalty,
    )
