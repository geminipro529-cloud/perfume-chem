"""Authority-aware Pareto and acquisition selection for C10 proposals."""

from __future__ import annotations

from collections.abc import Sequence

from engine.evidence.unsupported_science import (
    C9_LEGACY_SURFACES,
    C9AssessmentStatus,
    C10Use,
    UnsupportedOutcome,
    assess_unsupported_outcome,
)

from .contracts import (
    AcquisitionPolicy,
    AuthorizedExperimentSet,
    C10ContractError,
    CampaignState,
    CandidateEvaluation,
    CandidateRejection,
    CandidateRole,
    CandidateUtility,
    ExperimentProposal,
    GateStatus,
    HumanReviewReceipt,
    MixtureCandidate,
    MixtureDomain,
    ObjectiveAuthority,
    ObjectiveAuthorityAssessment,
    ObjectiveDirection,
    ObjectiveEstimate,
    SelectionStatus,
    StopPolicy,
    StopReason,
    UtilityContribution,
)
from .mixture_design import assess_candidate, candidate_formula_state_sha256

_C9_SURFACES = {record.surface_id: record for record in C9_LEGACY_SURFACES}


def assess_objective_authority(
    estimate: ObjectiveEstimate,
) -> ObjectiveAuthorityAssessment:
    """Reject legacy or unsupported numerical authority before ranking."""

    reasons: list[str] = []
    for source_id in estimate.source_ids:
        record = _C9_SURFACES.get(source_id)
        if record is None:
            continue
        if record.c10_use is C10Use.CALIBRATED_MODEL_REQUIRED:
            if (
                estimate.authority is not ObjectiveAuthority.CALIBRATED_HELD_OUT
                or not estimate.model_release_id
                or not estimate.held_out_receipt_sha256
            ):
                reasons.append("CALIBRATED_MODEL_AND_HELD_OUT_RECEIPT_REQUIRED")
        elif record.c10_use is C10Use.CAPABILITY_BOUNDARY_ONLY:
            reasons.append("CAPABILITY_BOUNDARY_IS_NOT_NUMERIC_AUTHORITY")
        elif record.c10_use is C10Use.ABSTENTION_ONLY:
            reasons.append("ABSTENTION_SURFACE_CANNOT_SUPPLY_NUMERIC_AUTHORITY")
        else:
            reasons.append("LEGACY_NUMERIC_AUTHORITY_FORBIDDEN")

    if estimate.authority is ObjectiveAuthority.CALIBRATED_HELD_OUT and (
        not estimate.model_release_id or not estimate.held_out_receipt_sha256
    ):
        reasons.append("CALIBRATED_MODEL_AND_HELD_OUT_RECEIPT_REQUIRED")

    try:
        unsupported = UnsupportedOutcome(estimate.name.strip().upper())
    except ValueError:
        unsupported = None
    if unsupported is not None:
        decision = assess_unsupported_outcome(
            unsupported,
            receipt=estimate.build_d_receipt,
            requested_scope=estimate.applicability_scope,
        )
        if decision.status is not C9AssessmentStatus.SUPPORTED_NARROW_SCOPE:
            reasons.append("BUILD_D_RECEIPT_REQUIRED")

    return ObjectiveAuthorityAssessment(
        accepted=not reasons,
        reason_codes=tuple(dict.fromkeys(reasons)),
    )


def _conservative_value(estimate: ObjectiveEstimate) -> float:
    if estimate.direction is ObjectiveDirection.MAXIMIZE:
        return estimate.value - estimate.standard_uncertainty
    return estimate.value + estimate.standard_uncertainty


def _dominates(left: CandidateEvaluation, right: CandidateEvaluation) -> bool:
    left_values = {item.name: item for item in left.objectives}
    right_values = {item.name: item for item in right.objectives}
    no_worse = True
    strictly_better = False
    for name in sorted(left_values):
        left_estimate = left_values[name]
        right_estimate = right_values[name]
        left_value = _conservative_value(left_estimate)
        right_value = _conservative_value(right_estimate)
        if left_estimate.direction is ObjectiveDirection.MAXIMIZE:
            if left_value < right_value:
                no_worse = False
            if left_value > right_value:
                strictly_better = True
        else:
            if left_value > right_value:
                no_worse = False
            if left_value < right_value:
                strictly_better = True
    return no_worse and strictly_better


def _objective_schema(evaluation: CandidateEvaluation) -> tuple[tuple[str, str, str], ...]:
    return tuple((item.name, item.direction.value, item.unit) for item in evaluation.objectives)


def _proposal(
    *,
    status: SelectionStatus,
    domain: MixtureDomain,
    acquisition_policy: AcquisitionPolicy,
    selected: tuple[str, ...] = (),
    pareto: tuple[str, ...] = (),
    rejections: Sequence[CandidateRejection] = (),
    stop_reasons: Sequence[StopReason] = (),
    blocker_codes: Sequence[str] = (),
    utilities: Sequence[CandidateUtility] = (),
) -> ExperimentProposal:
    return ExperimentProposal(
        status=status,
        selected_candidate_ids=tuple(selected),
        pareto_candidate_ids=tuple(pareto),
        rejections=tuple(sorted(rejections, key=lambda item: item.candidate_id)),
        stop_reasons=tuple(dict.fromkeys(stop_reasons)),
        blocker_codes=tuple(dict.fromkeys(blocker_codes)),
        utilities=tuple(sorted(utilities, key=lambda item: item.candidate_id)),
        domain_sha256=domain.content_sha256,
        acquisition_policy_sha256=acquisition_policy.content_sha256,
    )


def score_candidate_utility(
    evaluation: CandidateEvaluation,
    policy: AcquisitionPolicy,
) -> CandidateUtility:
    """Compute transparent utility from declared terms and conservative values."""

    estimates = {item.name: item for item in evaluation.acquisition_estimates}
    policy_names = {item.name for item in policy.terms}
    if set(estimates) != policy_names:
        raise C10ContractError("acquisition estimate schema does not match policy terms")
    contributions: list[UtilityContribution] = []
    for term in policy.terms:
        estimate = estimates[term.name]
        if estimate.direction is not term.direction:
            raise C10ContractError(f"acquisition direction mismatch for {term.name}")
        conservative = _conservative_value(estimate)
        span = term.maximum - term.minimum
        if term.direction is ObjectiveDirection.MAXIMIZE:
            normalized = (conservative - term.minimum) / span
        else:
            normalized = (term.maximum - conservative) / span
        normalized = min(1.0, max(0.0, normalized))
        contributions.append(
            UtilityContribution(
                name=term.name,
                conservative_value=conservative,
                normalized_value=normalized,
                weight=term.weight,
                weighted_contribution=normalized * term.weight,
            )
        )
    total_weight = sum(item.weight for item in contributions)
    score = sum(item.weighted_contribution for item in contributions) / total_weight
    return CandidateUtility(
        candidate_id=evaluation.candidate_id,
        score=score,
        contributions=tuple(contributions),
    )


def _campaign_stop_reasons(
    *,
    evaluations: Sequence[CandidateEvaluation],
    stop_policy: StopPolicy,
    campaign_state: CampaignState,
) -> tuple[StopReason, ...]:
    reasons: list[StopReason] = []
    if campaign_state.spent_budget >= stop_policy.budget_limit:
        reasons.append(StopReason.BUDGET_EXHAUSTED)
    if campaign_state.unavailable_data_dominates:
        reasons.append(StopReason.UNAVAILABLE_DATA_DOMINATES)
    if campaign_state.protected_attribute_risk > stop_policy.maximum_protected_attribute_risk:
        reasons.append(StopReason.PROTECTED_ATTRIBUTE_RISK)
    if campaign_state.sensory_plateau:
        reasons.append(StopReason.SENSORY_PLATEAU)

    acquisition_by_candidate = [
        {estimate.name: estimate for estimate in evaluation.acquisition_estimates}
        for evaluation in evaluations
    ]
    information = [
        _conservative_value(values["expected_information_gain"])
        for values in acquisition_by_candidate
        if "expected_information_gain" in values
    ]
    improvements = [
        _conservative_value(values["expected_improvement"])
        for values in acquisition_by_candidate
        if "expected_improvement" in values
    ]
    if information and max(information) < stop_policy.minimum_expected_information_gain:
        reasons.append(StopReason.INFORMATION_GAIN_BELOW_THRESHOLD)
    if improvements and max(improvements) < stop_policy.minimum_expected_improvement:
        reasons.append(StopReason.NO_FEASIBLE_IMPROVEMENT)
    return tuple(reasons)


def _validate_evaluation(
    domain: MixtureDomain,
    evaluation: CandidateEvaluation,
    policy: AcquisitionPolicy,
) -> tuple[str, ...]:
    reasons: list[str] = []
    for estimate in (*evaluation.objectives, *evaluation.acquisition_estimates):
        if estimate.applicability_scope != domain.domain_id:
            reasons.append("OBJECTIVE_SCOPE_MISMATCH")
        authority = assess_objective_authority(estimate)
        reasons.extend(authority.reason_codes)
    policy_names = {term.name for term in policy.terms}
    acquisition_names = {item.name for item in evaluation.acquisition_estimates}
    if acquisition_names != policy_names:
        reasons.append("ACQUISITION_SCHEMA_MISMATCH")
    else:
        term_by_name = {term.name: term for term in policy.terms}
        if any(
            item.direction is not term_by_name[item.name].direction
            for item in evaluation.acquisition_estimates
        ):
            reasons.append("ACQUISITION_DIRECTION_MISMATCH")
    return tuple(dict.fromkeys(reasons))


def select_experiments(
    *,
    domain: MixtureDomain,
    candidates: Sequence[MixtureCandidate],
    evaluations: Sequence[CandidateEvaluation],
    acquisition_policy: AcquisitionPolicy,
    stop_policy: StopPolicy,
    campaign_state: CampaignState,
) -> ExperimentProposal:
    """Filter hard gates, retain Pareto candidates, then rank experiments."""

    candidate_tuple = tuple(candidates)
    evaluation_tuple = tuple(evaluations)
    candidate_by_id = {item.candidate_id: item for item in candidate_tuple}
    evaluation_by_id = {item.candidate_id: item for item in evaluation_tuple}
    if len(candidate_by_id) != len(candidate_tuple):
        raise C10ContractError("candidate IDs must be unique")
    if len(evaluation_by_id) != len(evaluation_tuple):
        raise C10ContractError("evaluation candidate IDs must be unique")
    if any(candidate_id not in candidate_by_id for candidate_id in evaluation_by_id):
        raise C10ContractError("evaluation references an unknown candidate")

    feasible: dict[str, MixtureCandidate] = {}
    rejections: list[CandidateRejection] = []
    for candidate in candidate_tuple:
        assessment = assess_candidate(domain, candidate)
        if assessment.feasible:
            feasible[candidate.candidate_id] = candidate
        else:
            rejections.append(
                CandidateRejection(
                    candidate_id=candidate.candidate_id,
                    reason_codes=tuple(dict.fromkeys(item.code for item in assessment.violations)),
                )
            )

    new_feasible = {
        candidate_id: candidate
        for candidate_id, candidate in feasible.items()
        if candidate.role in {CandidateRole.SCREENING, CandidateRole.OPTIMIZATION}
    }
    if not new_feasible:
        return _proposal(
            status=SelectionStatus.STOPPED,
            domain=domain,
            acquisition_policy=acquisition_policy,
            rejections=rejections,
            stop_reasons=(StopReason.NO_FEASIBLE_CANDIDATE,),
        )

    controls = tuple(
        sorted(
            (item for item in feasible.values() if item.role is CandidateRole.CONTROL),
            key=lambda item: item.candidate_id,
        )
    )
    replicates = tuple(
        sorted(
            (item for item in feasible.values() if item.role is CandidateRole.REPLICATE),
            key=lambda item: item.candidate_id,
        )
    )
    blockers: list[str] = []
    if not controls:
        blockers.append("MISSING_CONTROL")
    if not replicates:
        blockers.append("MISSING_REPLICATE")
    for replicate in replicates:
        target = feasible.get(replicate.replicate_of or "")
        if target is None:
            blockers.append("REPLICATE_TARGET_MISSING_OR_INFEASIBLE")
            continue
        if candidate_formula_state_sha256(domain, replicate) != candidate_formula_state_sha256(
            domain, target
        ):
            blockers.append("REPLICATE_COMPOSITION_MISMATCH")
    if blockers:
        return _proposal(
            status=SelectionStatus.BLOCKED,
            domain=domain,
            acquisition_policy=acquisition_policy,
            rejections=rejections,
            blocker_codes=blockers,
        )

    valid_evaluations: list[CandidateEvaluation] = []
    schema: tuple[tuple[str, str, str], ...] | None = None
    for candidate_id in sorted(new_feasible):
        evaluation = evaluation_by_id.get(candidate_id)
        if evaluation is None:
            rejections.append(CandidateRejection(candidate_id, ("MISSING_EVALUATION",)))
            continue
        reasons = list(_validate_evaluation(domain, evaluation, acquisition_policy))
        candidate_schema = _objective_schema(evaluation)
        if schema is None and not reasons:
            schema = candidate_schema
        elif schema is not None and candidate_schema != schema:
            reasons.append("OBJECTIVE_SCHEMA_MISMATCH")
        if reasons:
            rejections.append(CandidateRejection(candidate_id, tuple(dict.fromkeys(reasons))))
        else:
            valid_evaluations.append(evaluation)

    if not valid_evaluations:
        return _proposal(
            status=SelectionStatus.STOPPED,
            domain=domain,
            acquisition_policy=acquisition_policy,
            rejections=rejections,
            stop_reasons=(StopReason.NO_FEASIBLE_CANDIDATE,),
        )

    stop_reasons = _campaign_stop_reasons(
        evaluations=valid_evaluations,
        stop_policy=stop_policy,
        campaign_state=campaign_state,
    )
    if stop_reasons:
        return _proposal(
            status=SelectionStatus.STOPPED,
            domain=domain,
            acquisition_policy=acquisition_policy,
            rejections=rejections,
            stop_reasons=stop_reasons,
        )

    pareto: list[CandidateEvaluation] = []
    for evaluation in valid_evaluations:
        if any(
            other is not evaluation and _dominates(other, evaluation) for other in valid_evaluations
        ):
            rejections.append(CandidateRejection(evaluation.candidate_id, ("PARETO_DOMINATED",)))
        else:
            pareto.append(evaluation)
    pareto.sort(key=lambda item: item.candidate_id)
    utilities = [score_candidate_utility(item, acquisition_policy) for item in pareto]
    ranked = sorted(utilities, key=lambda item: (-item.score, item.candidate_id))
    chosen = ranked[: acquisition_policy.maximum_new_candidates]
    selected = (
        tuple(item.candidate_id for item in controls)
        + tuple(item.candidate_id for item in replicates)
        + tuple(item.candidate_id for item in chosen)
    )
    return _proposal(
        status=SelectionStatus.PROPOSED,
        domain=domain,
        acquisition_policy=acquisition_policy,
        selected=selected,
        pareto=tuple(item.candidate_id for item in pareto),
        rejections=rejections,
        utilities=utilities,
    )


def authorize_proposal(
    proposal: ExperimentProposal,
    receipt: HumanReviewReceipt,
) -> AuthorizedExperimentSet:
    """Require an exact-hash PASS human review before experiment execution."""

    if proposal.status is not SelectionStatus.PROPOSED:
        raise C10ContractError("only a proposed experiment set can be authorized")
    if receipt.status is not GateStatus.PASS:
        raise C10ContractError("human review receipt must pass")
    if receipt.subject_sha256 != proposal.content_sha256:
        raise C10ContractError("human review receipt is not bound to this proposal")
    return AuthorizedExperimentSet(
        proposal_sha256=proposal.content_sha256,
        selected_candidate_ids=proposal.selected_candidate_ids,
        human_review_evidence_sha256=receipt.evidence_sha256,
    )


__all__ = [
    "assess_objective_authority",
    "authorize_proposal",
    "score_candidate_utility",
    "select_experiments",
]
