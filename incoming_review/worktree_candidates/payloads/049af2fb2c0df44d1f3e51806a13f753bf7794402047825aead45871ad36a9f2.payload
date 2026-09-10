"""Fail-closed evaluation for universal perfume-depth design profiles."""

from __future__ import annotations

from engine.perception.depth_contracts import (
    FORMULA_BOUND_REQUIRED_DIMENSIONS,
    DepthArchitectureProfileV1,
    DepthDesignState,
    DepthDimension,
    DepthEvaluationResultV1,
    DepthProbeType,
)

_ALLOWED_CLAIM_CEILINGS = frozenset(
    {
        "COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY",
        "COMPUTATIONAL_DESIGN_ONLY",
        "NOT_TESTED",
    }
)
_CONSTANT_TOTAL_PROBES = frozenset(
    {
        DepthProbeType.ABLATION,
        DepthProbeType.RATIO_SWEEP,
        DepthProbeType.RECOMBINATION,
        DepthProbeType.ANTI_COLLAPSE,
        DepthProbeType.HEDONIC_PREFERENCE,
        DepthProbeType.TEXTURE,
    }
)
_BLINDING_TOKENS = ("blind", "coded", "conceal", "three-digit", "3-digit")
_HEDONIC_VALENCE_ENDPOINT_TOKENS = ("liking", "preference", "pleasant")
_HEDONIC_ARCHITECTURE_ENDPOINT_TOKENS = (
    "re-smell",
    "resmell",
    "desire",
    "fascination",
    "tension",
    "relief",
    "comfort",
    "satiation",
    "fatigue",
    "novelty",
    "familiarity",
)
_MIN_TEMPORAL_WINDOWS = 5
_ADAPTATION_CONTROL_TOKENS = (
    "adaptation",
    "fresh coded application",
    "fresh application",
    "fresh blotter",
    "separate application",
    "washout",
    "sniff limit",
    "sniff-duration",
    "rest break",
    "independent window",
)
_MODELED_PERFORMANCE_PROMOTIONS = (
    "oav establishes",
    "oav proves",
    "headspace establishes",
    "headspace proves",
    "modeled projection confirms",
    "guaranteed performance",
    "guarantees performance",
    "performance confirmed by oav",
)


def _append_issue(
    reason_codes: list[str],
    blockers: list[str],
    code: str,
    detail: str,
) -> None:
    if code not in reason_codes:
        reason_codes.append(code)
    if detail not in blockers:
        blockers.append(detail)


def evaluate_depth_profile(profile: DepthArchitectureProfileV1) -> DepthEvaluationResultV1:
    """Evaluate experiment closure without creating sensory or formula authority."""

    if not isinstance(profile, DepthArchitectureProfileV1):
        raise TypeError("profile must be a DepthArchitectureProfileV1")

    reason_codes: list[str] = []
    blockers: list[str] = []
    uncovered_dimensions: list[DepthDimension] = []
    unbound_mechanism_ids: list[str] = []

    if profile.claim_ceiling not in _ALLOWED_CLAIM_CEILINGS:
        _append_issue(
            reason_codes,
            blockers,
            "HOLD_CLAIM_CEILING",
            f"claim ceiling {profile.claim_ceiling!r} exceeds computational experiment design",
        )

    required_dimensions = tuple(
        contract.dimension for contract in profile.dimension_contracts if contract.required
    )
    if not required_dimensions:
        _append_issue(
            reason_codes,
            blockers,
            "HOLD_NO_REQUIRED_DIMENSIONS",
            "the profile declares no required target-linked depth dimensions",
        )
    elif set(required_dimensions) == {DepthDimension.CONSTRUCTION_COMPLEXITY}:
        _append_issue(
            reason_codes,
            blockers,
            "HOLD_COUNT_ONLY_DEPTH",
            "construction complexity is the only required dimension",
        )

    if profile.formula_evidence is not None:
        missing_formula_dimensions = tuple(
            dimension
            for dimension in FORMULA_BOUND_REQUIRED_DIMENSIONS
            if dimension not in required_dimensions
        )
        for dimension in missing_formula_dimensions:
            uncovered_dimensions.append(dimension)
        if missing_formula_dimensions:
            _append_issue(
                reason_codes,
                blockers,
                "HOLD_FORMULA_DIMENSION_COVERAGE",
                (
                    "formula-bound depth evaluation is missing required dimensions: "
                    + ", ".join(item.value for item in missing_formula_dimensions)
                ),
            )
        if len(profile.formula_evidence.temporal_windows) < _MIN_TEMPORAL_WINDOWS:
            _append_issue(
                reason_codes,
                blockers,
                "HOLD_FORMULA_TEMPORAL_EVIDENCE",
                "formula-bound pipeline evidence requires at least five temporal windows",
            )
        sub_ten_roles = tuple(
            role.role_id
            for role in profile.formula_evidence.roles
            if role.raw_ul < 10.0
        )
        if sub_ten_roles:
            _append_issue(
                reason_codes,
                blockers,
                "HOLD_FORMULA_SUB_10_UL",
                (
                    "formula rows below the measurable 10 uL raw-transfer floor require "
                    "an explicit practical dilution: "
                    + ", ".join(sub_ten_roles)
                ),
            )

    mechanisms_by_id = {item.mechanism_id: item for item in profile.mechanisms}
    probes_by_id = {item.probe_id: item for item in profile.probes}
    referenced_mechanism_ids: set[str] = set()
    referenced_probe_ids: set[str] = set()

    for contract in profile.dimension_contracts:
        referenced_mechanism_ids.update(contract.mechanism_ids)
        referenced_probe_ids.update(contract.probe_ids)
        missing_mechanisms = tuple(
            mechanism_id
            for mechanism_id in contract.mechanism_ids
            if mechanism_id not in mechanisms_by_id
        )
        missing_probes = tuple(
            probe_id for probe_id in contract.probe_ids if probe_id not in probes_by_id
        )
        if contract.required and (
            not contract.mechanism_ids
            or not contract.probe_ids
            or missing_mechanisms
            or missing_probes
        ):
            uncovered_dimensions.append(contract.dimension)
            _append_issue(
                reason_codes,
                blockers,
                "HOLD_REQUIRED_DIMENSION",
                (
                    f"required dimension {contract.dimension.value} lacks closed mechanisms "
                    "or controlled probes"
                ),
            )
        for mechanism_id in contract.mechanism_ids:
            mechanism = mechanisms_by_id.get(mechanism_id)
            if mechanism is not None and mechanism.dimension is not contract.dimension:
                _append_issue(
                    reason_codes,
                    blockers,
                    "HOLD_DIMENSION_MISMATCH",
                    (
                        f"mechanism {mechanism_id} belongs to {mechanism.dimension.value}, "
                        f"not {contract.dimension.value}"
                    ),
                )

    for mechanism in profile.mechanisms:
        if (
            mechanism.falsification_probe_id not in probes_by_id
            or mechanism.mechanism_id not in referenced_mechanism_ids
        ):
            unbound_mechanism_ids.append(mechanism.mechanism_id)
            _append_issue(
                reason_codes,
                blockers,
                "HOLD_UNBOUND_MECHANISM",
                (
                    f"mechanism {mechanism.mechanism_id} is not bound to both a dimension "
                    "and an existing falsification probe"
                ),
            )

    for probe in profile.probes:
        if probe.probe_type in _CONSTANT_TOTAL_PROBES and not any(
            "constant total" in constraint.lower()
            for constraint in probe.constant_constraints
        ):
            _append_issue(
                reason_codes,
                blockers,
                "HOLD_CONSTANT_TOTAL",
                f"probe {probe.probe_id} lacks an explicit constant-total constraint",
            )
        if probe.probe_id not in referenced_probe_ids and not any(
            mechanism.falsification_probe_id == probe.probe_id
            for mechanism in profile.mechanisms
        ):
            _append_issue(
                reason_codes,
                blockers,
                "HOLD_UNBOUND_PROBE",
                f"probe {probe.probe_id} is not bound to a dimension or mechanism",
            )

    hedonic_contracts = tuple(
        contract
        for contract in profile.dimension_contracts
        if contract.required and contract.dimension is DepthDimension.HEDONIC_ARCHITECTURE
    )
    for contract in hedonic_contracts:
        hedonic_probes = tuple(
            probes_by_id[probe_id]
            for probe_id in contract.probe_ids
            if probe_id in probes_by_id
            and probes_by_id[probe_id].probe_type is DepthProbeType.HEDONIC_PREFERENCE
        )
        blinded = any(
            any(token in probe.blinding_rule.lower() for token in _BLINDING_TOKENS)
            for probe in hedonic_probes
        )
        valence_endpoint_bound = any(
            any(
                token in endpoint.lower()
                for token in _HEDONIC_VALENCE_ENDPOINT_TOKENS
            )
            for probe in hedonic_probes
            for endpoint in probe.primary_endpoints
        )
        architecture_endpoint_bound = any(
            any(
                token in endpoint.lower()
                for token in _HEDONIC_ARCHITECTURE_ENDPOINT_TOKENS
            )
            for probe in hedonic_probes
            for endpoint in probe.primary_endpoints
        )
        if not hedonic_probes or not blinded or not valence_endpoint_bound:
            _append_issue(
                reason_codes,
                blockers,
                "HOLD_HEDONIC_BLINDING",
                (
                    "hedonic architecture requires a blinded preference probe with a "
                    "liking, preference, or pleasantness endpoint"
                ),
            )
        elif not architecture_endpoint_bound:
            _append_issue(
                reason_codes,
                blockers,
                "HOLD_HEDONIC_ENDPOINT_SEPARATION",
                (
                    "hedonic architecture must measure valence separately from a "
                    "re-smelling, tension-relief, fascination, comfort, satiation, "
                    "fatigue, novelty, or familiarity endpoint"
                ),
            )

    temporal_contracts = tuple(
        contract
        for contract in profile.dimension_contracts
        if contract.required and contract.dimension is DepthDimension.TEMPORAL_ARCHITECTURE
    )
    for contract in temporal_contracts:
        mechanisms = tuple(
            mechanisms_by_id[mechanism_id]
            for mechanism_id in contract.mechanism_ids
            if mechanism_id in mechanisms_by_id
        )
        probes = tuple(
            probes_by_id[probe_id]
            for probe_id in contract.probe_ids
            if probe_id in probes_by_id
        )
        if (
            not mechanisms
            or any(
                len(mechanism.temporal_windows) < _MIN_TEMPORAL_WINDOWS
                for mechanism in mechanisms
            )
            or not probes
            or any(
                len(probe.time_windows) < _MIN_TEMPORAL_WINDOWS
                for probe in probes
            )
        ):
            _append_issue(
                reason_codes,
                blockers,
                "HOLD_TEMPORAL_WINDOWS",
                "temporal depth requires at least five declared observation windows",
            )
        if probes and any(
            not any(
                token in " ".join(
                    (
                        *probe.constant_constraints,
                        probe.blinding_rule,
                        probe.order_rule,
                    )
                ).lower()
                for token in _ADAPTATION_CONTROL_TOKENS
            )
            for probe in probes
        ):
            _append_issue(
                reason_codes,
                blockers,
                "HOLD_TEMPORAL_ADAPTATION_CONTROL",
                (
                    "temporal depth requires an explicit olfactory-adaptation, fresh-"
                    "application, washout, sniff-limit, rest-break, or independent-window control"
                ),
            )

    spatial_mechanisms = tuple(
        mechanism
        for mechanism in profile.mechanisms
        if mechanism.dimension is DepthDimension.SPATIAL_PERFORMANCE
    )
    for mechanism in spatial_mechanisms:
        language = " ".join(
            (
                mechanism.target_link,
                mechanism.causal_hypothesis,
                mechanism.expected_contribution,
                mechanism.failure_mode,
            )
        ).lower()
        if any(phrase in language for phrase in _MODELED_PERFORMANCE_PROMOTIONS):
            _append_issue(
                reason_codes,
                blockers,
                "HOLD_MODELED_PERFORMANCE_CLAIM",
                (
                    f"spatial mechanism {mechanism.mechanism_id} promotes modeled "
                    "OAV/headspace into physical performance truth"
                ),
            )

    if blockers:
        state = DepthDesignState.HOLD
    else:
        state = DepthDesignState.DESIGN_READY
        reason_codes.append("DESIGN_READY_EXPERIMENTS_SPECIFIED")

    return DepthEvaluationResultV1(
        state=state,
        profile_sha256=profile.profile_sha256,
        reason_codes=tuple(reason_codes),
        blockers=tuple(blockers),
        uncovered_dimensions=tuple(dict.fromkeys(uncovered_dimensions)),
        unbound_mechanism_ids=tuple(dict.fromkeys(unbound_mechanism_ids)),
    )


__all__ = ["evaluate_depth_profile"]
