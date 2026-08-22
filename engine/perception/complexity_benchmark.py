"""Deterministic gates and decisions for the complexity xhigh benchmark."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from engine.perception.complexity_ensemble import ComplexityCasePacket
from engine.perception.complexity_xhigh import (
    DEPTH_FIELD_KEYS,
    RESPONSE_TOP_LEVEL_KEYS,
)

CRITICAL_CODES = frozenset(
    {
        "INVENTED_INVENTORY_OR_STOCK",
        "INVENTED_PHYSICAL_ADDITION",
        "TARGET_BUILD_COLLAPSE",
        "TARGET_CHANGED_TO_FIT_INVENTORY",
        "COMPLICATION_AS_COMPLEXITY",
        "UNSUPPORTED_HEDONIC_RESULT",
        "MUSK_COUNT_PROXY",
        "MUSK_EXCEPTION_REQUIRED",
        "MUSK_BUILD_INVENTORY_PROMOTION",
        "UNBOUND_OR_MONOMOLECULAR_NATURAL_OAV",
        "UNSUPPORTED_TESTED_STATUS",
        "SILENT_SOURCE_CONFLICT_RESOLUTION",
        "QUARANTINED_CONTENT_PROMOTED",
        "MISSING_CHEMICAL_IMPACT_OMITTED",
        "UNSUPPORTED_EVIDENCE_CITATION",
        "INVALID_STRUCTURED_RESPONSE",
    }
)

DIMENSION_MAXIMA: Mapping[str, int] = MappingProxyType(
    {
        "target_architecture": 20,
        "integrated_depth_richness": 20,
        "factual_provenance": 20,
        "missing_chemical_impact": 15,
        "controlled_test_quality": 15,
        "uncertainty_conflict_actionability": 10,
    }
)

_TESTED_STATES = frozenset(
    {"TESTED", "MEASURED", "PHYSICAL", "PASS_EMPIRICAL", "RELEASED"}
)
_COMPLICATION_PROXIES = (
    "more ingredient",
    "ingredient count",
    "more module",
    "module count",
    "interaction count",
    "more descriptor",
    "descriptor count",
    "novelty",
    "response length",
    "jargon",
    "technical density",
    "more complex because",
)
_PROOF_WORDS = ("richer", "richness", "depth", "quality", "beauty", "hedonic")


@dataclass(frozen=True, slots=True)
class HardGateViolation:
    code: str
    message: str
    critical: bool = True

    def __post_init__(self) -> None:
        if self.code not in CRITICAL_CODES:
            raise ValueError(f"unknown hard-gate code: {self.code}")


@dataclass(frozen=True, slots=True)
class RubricScore:
    case_id: str
    dimension_scores: Mapping[str, int]
    diagnostic_total: int
    total: int
    violations: tuple[HardGateViolation, ...]


@dataclass(frozen=True, slots=True)
class PairScore:
    case_id: str
    control: RubricScore
    treatment: RubricScore

    @property
    def paired_delta(self) -> int:
        return self.treatment.total - self.control.total

    @property
    def treatment_won(self) -> bool:
        return self.treatment.total > self.control.total


class BenchmarkState(str, Enum):
    OUTPERFORMS = "OUTPERFORMS"
    INCONCLUSIVE = "INCONCLUSIVE"
    NO_DEMONSTRATED_OUTPERFORMANCE = "NO_DEMONSTRATED_OUTPERFORMANCE"
    QUALITY_OUTPERFORMER_COST_REVIEW_REQUIRED = (
        "QUALITY_OUTPERFORMER_COST_REVIEW_REQUIRED"
    )
    BENCHMARK_BLOCKED = "BENCHMARK_BLOCKED"


@dataclass(frozen=True, slots=True)
class BenchmarkEvidence:
    pair_count: int
    treatment_wins: int
    median_delta: Decimal
    new_treatment_critical_failures: int
    category_median_deltas: Mapping[str, Decimal]
    receipts_valid: bool


@dataclass(frozen=True, slots=True)
class TelemetrySummary:
    state: str
    median_control_price_usd: Decimal | None
    median_treatment_price_usd: Decimal | None


@dataclass(frozen=True, slots=True)
class BenchmarkDecision:
    state: BenchmarkState
    reasons: tuple[str, ...]
    quality_thresholds_passed: bool
    cost_ratio: Decimal | None


def _as_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False).casefold()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    return ()


def _nonempty(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (str, bytes, Mapping, Sequence)):
        return bool(value)
    return True


def _schema_error(
    case: ComplexityCasePacket, response: Mapping[str, Any]
) -> str | None:
    if set(response) != set(RESPONSE_TOP_LEVEL_KEYS):
        return "response top-level keys do not match the sealed output contract"
    depth = response.get("depth_and_richness_analysis")
    if not isinstance(depth, Mapping) or not set(DEPTH_FIELD_KEYS).issubset(depth):
        return "depth and richness fields are missing"
    claims = response.get("claims")
    if not isinstance(claims, list) or not claims:
        return "claims must be a nonempty list"
    claim_keys = {"claim", "state", "evidence_refs", "authority_ceiling"}
    if any(not isinstance(item, Mapping) or not claim_keys.issubset(item) for item in claims):
        return "claim records do not match the sealed contract"
    required_states = set(case.expected_invariants["required_claim_states"])
    actual_states = {str(item["state"]) for item in claims}
    if not required_states.issubset(actual_states):
        return "required claim states are missing"
    hypotheses = depth.get("hedonic_potential_hypotheses")
    hypothesis_keys = {
        "state",
        "target_linked_mechanism",
        "controlled_sensory_comparison",
        "evidence_refs",
    }
    if not isinstance(hypotheses, list) or not hypotheses:
        return "at least one hedonic-potential hypothesis is required"
    if any(
        not isinstance(item, Mapping) or not hypothesis_keys.issubset(item)
        for item in hypotheses
    ):
        return "hedonic-potential hypotheses do not match the sealed contract"
    formula_fields = ("target_ideal_formula", "current_inventory_build")
    if any(
        response[field] is not None and not isinstance(response[field], Mapping)
        for field in formula_fields
    ):
        return "formula fields must be objects or null"
    if not isinstance(response["missing_chemical_impact"], Mapping):
        return "missing-chemical impact must be an object"
    if not isinstance(response["controlled_test_plan"], Mapping):
        return "controlled test plan must be an object"
    return None


def _add_violation(
    rows: list[HardGateViolation], code: str, message: str
) -> None:
    if all(item.code != code for item in rows):
        rows.append(HardGateViolation(code, message))


def _materials(formula: Any) -> tuple[str, ...]:
    value = _mapping(formula).get("materials", ())
    rows: list[str] = []
    for item in _sequence(value):
        if isinstance(item, Mapping):
            name = item.get("material") or item.get("name")
        else:
            name = item
        if name is not None:
            rows.append(str(name))
    return tuple(rows)


def _exception_complete(formula: Any, material: str, required: set[str]) -> bool:
    calls = _mapping(formula).get("exception_calls", {})
    call = _mapping(_mapping(calls).get(material))
    return required.issubset(call) and all(_nonempty(call[key]) for key in required)


def _critical_violations(
    case: ComplexityCasePacket, response: Mapping[str, Any]
) -> tuple[HardGateViolation, ...]:
    violations: list[HardGateViolation] = []
    target = _mapping(response["target_identity"])
    if str(target.get("identity", "")).strip() != case.target_identity:
        _add_violation(
            violations,
            "TARGET_CHANGED_TO_FIT_INVENTORY",
            "response does not preserve the frozen target identity",
        )

    ideal = response["target_ideal_formula"]
    build = response["current_inventory_build"]
    ideal_materials = _materials(ideal)
    build_materials = _materials(build)
    if ideal is not None and build is not None and ideal_materials == build_materials:
        _add_violation(
            violations,
            "TARGET_BUILD_COLLAPSE",
            "target/ideal and current-inventory build are conflated",
        )

    claims = _sequence(response["claims"])
    for claim in claims:
        claim_map = _mapping(claim)
        text = str(claim_map.get("claim", "")).casefold()
        state = str(claim_map.get("state", "")).upper()
        refs = set(str(item) for item in _sequence(claim_map.get("evidence_refs")))
        if "physically added" in text or "was physically compounded" in text:
            _add_violation(
                violations,
                "INVENTED_PHYSICAL_ADDITION",
                "physical addition is asserted without a bound compounding receipt",
            )
        if (
            any(term in text for term in ("owned stock", "exactstockref", "in stock"))
            and not refs
        ):
            _add_violation(
                violations,
                "INVENTED_INVENTORY_OR_STOCK",
                "inventory or exact stock is asserted without evidence",
            )
        if state in _TESTED_STATES and not refs:
            _add_violation(
                violations,
                "UNSUPPORTED_TESTED_STATUS",
                "tested status lacks claim-linked evidence",
            )
        if refs.difference(case.evidence_refs):
            _add_violation(
                violations,
                "UNSUPPORTED_EVIDENCE_CITATION",
                "claim cites evidence outside the frozen case packet",
            )
        if "strict oav" in text and state in _TESTED_STATES and not refs:
            _add_violation(
                violations,
                "UNBOUND_OR_MONOMOLECULAR_NATURAL_OAV",
                "strict OAV status is not bound to admitted analytical evidence",
            )
        if "quarantined" in text and any(
            term in text for term in ("admitted", "installed", "authoritative")
        ):
            _add_violation(
                violations,
                "QUARANTINED_CONTENT_PROMOTED",
                "quarantined content is promoted as admitted authority",
            )

    depth = _mapping(response["depth_and_richness_analysis"])
    positive_depth_text = _as_text(
        {
            "identity_linked_facets": depth.get("identity_linked_facets"),
            "coherent_richness": depth.get("coherent_richness"),
            "hedonic_potential_hypotheses": depth.get(
                "hedonic_potential_hypotheses"
            ),
        }
    )
    if any(proxy in positive_depth_text for proxy in _COMPLICATION_PROXIES) and any(
        proof in positive_depth_text for proof in _PROOF_WORDS
    ):
        _add_violation(
            violations,
            "COMPLICATION_AS_COMPLEXITY",
            "raw count, novelty, verbosity, or jargon is offered as proof of depth",
        )
    if (
        "musk" in positive_depth_text
        and any(term in positive_depth_text for term in ("three-musk", "fixed-count"))
        and any(proof in positive_depth_text for proof in _PROOF_WORDS)
    ):
        _add_violation(
            violations,
            "MUSK_COUNT_PROXY",
            "musk chord size is offered as proof of richness",
        )
    for hypothesis in _sequence(depth.get("hedonic_potential_hypotheses")):
        if _mapping(hypothesis).get("state") != "DESIGN_HYPOTHESIS_NOT_TESTED":
            _add_violation(
                violations,
                "UNSUPPORTED_HEDONIC_RESULT",
                "hedonic potential is promoted beyond an untested design hypothesis",
            )

    musk_policy = _mapping(case.expected_invariants["complexity_definition"])[
        "musk_policy"
    ]
    exceptions = tuple(str(item) for item in musk_policy["exception_only_materials"])
    required = set(str(item) for item in musk_policy["exception_fields"])
    for material in exceptions:
        if material in ideal_materials or material in build_materials:
            if not _exception_complete(ideal, material, required):
                _add_violation(
                    violations,
                    "MUSK_EXCEPTION_REQUIRED",
                    f"{material} appears without the complete exception design call",
                )
        if material in build_materials:
            _add_violation(
                violations,
                "MUSK_BUILD_INVENTORY_PROMOTION",
                f"depleted exception-only musk {material} enters the current build",
            )

    if not response["missing_chemical_impact"]:
        _add_violation(
            violations,
            "MISSING_CHEMICAL_IMPACT_OMITTED",
            "required missing-chemical impact gate is absent",
        )
    if (
        "C08_CONFLICT" in case.expected_invariants.get("critical_traps", ())
        and not response["conflicts_and_holds"]
    ):
        _add_violation(
            violations,
            "SILENT_SOURCE_CONFLICT_RESOLUTION",
            "same-scope conflict is not preserved as a hold",
        )
    return tuple(violations)


def _score_dimensions(
    case: ComplexityCasePacket, response: Mapping[str, Any]
) -> dict[str, int]:
    target = _mapping(response["target_identity"])
    architecture = _mapping(response["functional_architecture"])
    depth = _mapping(response["depth_and_richness_analysis"])
    claims = tuple(_mapping(item) for item in _sequence(response["claims"]))
    ideal = _mapping(response["target_ideal_formula"])
    build = _mapping(response["current_inventory_build"])
    impact = _mapping(response["missing_chemical_impact"])
    test = _mapping(response["controlled_test_plan"])
    holds = _sequence(response["conflicts_and_holds"])
    known_refs = set(case.evidence_refs)

    target_score = 0
    target_score += 5 if target.get("identity") == case.target_identity else 0
    target_score += 5 if _nonempty(architecture.get("roles")) else 0
    target_score += 5 if _nonempty(architecture.get("temporal_handoffs")) else 0
    target_score += 5 if _nonempty(architecture.get("failure_boundaries")) else 0

    hypotheses = tuple(
        _mapping(item)
        for item in _sequence(depth.get("hedonic_potential_hypotheses"))
    )
    valid_hypothesis = any(
        item.get("state") == "DESIGN_HYPOTHESIS_NOT_TESTED"
        and _nonempty(item.get("target_linked_mechanism"))
        and _nonempty(item.get("controlled_sensory_comparison"))
        for item in hypotheses
    )
    depth_score = 0
    depth_score += 5 if _nonempty(depth.get("identity_linked_facets")) else 0
    depth_score += 5 if _nonempty(depth.get("coherent_richness")) else 0
    depth_score += 5 if _nonempty(depth.get("temporal_unfolding")) and _nonempty(
        depth.get("restraint_or_subtraction")
    ) else 0
    depth_score += 5 if valid_hypothesis else 0

    factual_score = 0
    factual_score += 5 if set(_sequence(target.get("evidence_refs"))).issubset(
        known_refs
    ) and _nonempty(target.get("evidence_refs")) else 0
    factual_score += 5 if claims and all(
        set(_sequence(item.get("evidence_refs"))).issubset(known_refs)
        and _nonempty(item.get("evidence_refs"))
        for item in claims
    ) else 0
    factual_score += 5 if set(
        case.expected_invariants["required_claim_states"]
    ).issubset({str(item.get("state")) for item in claims}) else 0
    factual_score += 5 if holds and all(
        item.get("authority_ceiling") == case.permitted_claim_ceiling
        for item in claims
    ) else 0

    missing_score = 0
    missing_score += 5 if ideal.get("inventory_independent") is True and _materials(
        ideal
    ) != _materials(build) else 0
    missing_score += 5 if all(
        key in impact
        for key in ("strongly_covered", "weakly_covered", "genuinely_missing")
    ) else 0
    missing_score += 5 if _nonempty(impact.get("controlled_comparison")) else 0

    test_score = 0
    test_score += 5 if _nonempty(test.get("isolation")) and _nonempty(
        test.get("controls")
    ) else 0
    test_score += 5 if _nonempty(test.get("dose_time_substrate")) else 0
    test_score += 5 if all(
        _nonempty(test.get(key)) for key in ("blinding", "endpoints", "decision_rule")
    ) else 0

    uncertainty_score = 0
    uncertainty_score += 5 if holds and all(
        _nonempty(_mapping(item).get("next_action")) for item in holds
    ) else 0
    answer = str(response["answer_markdown"])
    uncertainty_score += 5 if "NOT TESTED" in answer and len(answer) <= 2000 else 0
    return {
        "target_architecture": target_score,
        "integrated_depth_richness": depth_score,
        "factual_provenance": factual_score,
        "missing_chemical_impact": missing_score,
        "controlled_test_quality": test_score,
        "uncertainty_conflict_actionability": uncertainty_score,
    }


def score_structured_response(
    case: ComplexityCasePacket, response: Mapping[str, Any]
) -> RubricScore:
    if not isinstance(response, Mapping):
        violation = HardGateViolation(
            "INVALID_STRUCTURED_RESPONSE", "response is not a JSON object"
        )
        scores = {key: 0 for key in DIMENSION_MAXIMA}
        return RubricScore(case.case_id, scores, 0, 0, (violation,))
    schema_error = _schema_error(case, response)
    if schema_error is not None:
        violation = HardGateViolation("INVALID_STRUCTURED_RESPONSE", schema_error)
        scores = {key: 0 for key in DIMENSION_MAXIMA}
        return RubricScore(case.case_id, scores, 0, 0, (violation,))
    scores = _score_dimensions(case, response)
    diagnostics = sum(scores.values())
    violations = _critical_violations(case, response)
    return RubricScore(
        case_id=case.case_id,
        dimension_scores=MappingProxyType(scores),
        diagnostic_total=diagnostics,
        total=0 if violations else diagnostics,
        violations=violations,
    )


def decide_paired_benchmark(
    evidence: BenchmarkEvidence, *, telemetry: TelemetrySummary
) -> BenchmarkDecision:
    if evidence.pair_count != 16 or not evidence.receipts_valid:
        return BenchmarkDecision(
            BenchmarkState.BENCHMARK_BLOCKED,
            ("sixteen valid paired receipts are required",),
            False,
            None,
        )
    if evidence.new_treatment_critical_failures:
        return BenchmarkDecision(
            BenchmarkState.NO_DEMONSTRATED_OUTPERFORMANCE,
            ("treatment introduced a new critical failure",),
            False,
            None,
        )
    if any(delta < Decimal("-2") for delta in evidence.category_median_deltas.values()):
        return BenchmarkDecision(
            BenchmarkState.NO_DEMONSTRATED_OUTPERFORMANCE,
            ("a category median regressed by more than two points",),
            False,
            None,
        )

    quality_passed = (
        evidence.treatment_wins >= 12 and evidence.median_delta >= Decimal("5")
    )
    if quality_passed:
        cost_ratio = None
        if telemetry.state == "EXPOSED":
            control_price = telemetry.median_control_price_usd
            treatment_price = telemetry.median_treatment_price_usd
            if control_price is None or treatment_price is None or control_price <= 0:
                return BenchmarkDecision(
                    BenchmarkState.BENCHMARK_BLOCKED,
                    ("exposed price telemetry is incomplete or invalid",),
                    True,
                    None,
                )
            cost_ratio = treatment_price / control_price
            if cost_ratio > Decimal("2"):
                return BenchmarkDecision(
                    BenchmarkState.QUALITY_OUTPERFORMER_COST_REVIEW_REQUIRED,
                    ("quality passed but median treatment price exceeds 2x control",),
                    True,
                    cost_ratio,
                )
        return BenchmarkDecision(
            BenchmarkState.OUTPERFORMS,
            ("all frozen quality thresholds passed",),
            True,
            cost_ratio,
        )

    if 9 <= evidence.treatment_wins <= 11 or Decimal("2") <= evidence.median_delta <= Decimal("4"):
        return BenchmarkDecision(
            BenchmarkState.INCONCLUSIVE,
            ("result falls in the frozen repeat band",),
            False,
            None,
        )
    return BenchmarkDecision(
        BenchmarkState.NO_DEMONSTRATED_OUTPERFORMANCE,
        ("frozen quality thresholds were not met",),
        False,
        None,
    )
