from __future__ import annotations

from dataclasses import replace

import pytest

from engine.perception.experiment_value import (
    EVIDENCE_VALUE_AUTHORITY_FLAGS,
    DecisionImpact,
    EvidenceValueCandidate,
    EvidenceValueRequest,
    EvidenceValueState,
    ExperimentBurden,
    ExperimentDomain,
    ExperimentOutcome,
    select_evidence_value_experiment,
)

SCOPE_SHA = "1" * 64
PLAN_SHA = "2" * 64
SOURCE_SHA = "3" * 64


def _outcome(
    outcome_id: str,
    *eliminated: str,
    resolves_decision: bool = False,
) -> ExperimentOutcome:
    return ExperimentOutcome(
        outcome_id=outcome_id,
        eliminated_hypothesis_ids=tuple(eliminated),
        resolves_decision=resolves_decision,
    )


def _candidate(
    candidate_id: str,
    *,
    domain: ExperimentDomain = ExperimentDomain.FORMULA_DELTA,
    outcomes: tuple[ExperimentOutcome, ...] | None = None,
    physical_required: bool = True,
    burden: ExperimentBurden | None = None,
    **overrides: object,
) -> EvidenceValueCandidate:
    values: dict[str, object] = {
        "candidate_id": candidate_id,
        "source_receipt_sha256": SOURCE_SHA,
        "exact_scope_sha256": SCOPE_SHA,
        "criterion_id": "DEPTH",
        "domain": domain,
        "decision_impact": DecisionImpact.PRIMARY,
        "outcomes": outcomes
        or (
            _outcome("TARGET_GAIN", "H1", resolves_decision=True),
            _outcome("NO_TARGET_GAIN", "H2", resolves_decision=True),
        ),
        "protocol_qualified": True,
        "lineage_complete": True,
        "inventory_executable": True,
        "constant_total": True,
        "blinded": True,
        "isolated_arms_complete": True,
        "physical_required": physical_required,
        "burden": burden or ExperimentBurden(physical_sample_count=2),
        "safety_review_required": physical_required,
        "safety_review_complete": physical_required,
        "blockers": (),
    }
    values.update(overrides)
    return EvidenceValueCandidate(**values)


def _request(*candidates: EvidenceValueCandidate, decision_resolved: bool = False) -> EvidenceValueRequest:
    return EvidenceValueRequest(
        decision_id="DHP-DEPTH-NEXT-001",
        exact_scope_sha256=SCOPE_SHA,
        criterion_id="DEPTH",
        unresolved_hypothesis_ids=("H1", "H2", "H3"),
        predeclared_plan_sha256=PLAN_SHA,
        candidates=candidates,
        decision_resolved=decision_resolved,
    )


def test_resolved_decision_returns_no_change_without_selecting_work() -> None:
    result = select_evidence_value_experiment(
        _request(_candidate("otherwise-admissible"), decision_resolved=True)
    )

    assert result.state is EvidenceValueState.NO_CHANGE
    assert result.selected_candidate is None
    assert result.next_action == "No experiment: the scoped decision is already resolved."
    assert result.authority_flags == EVIDENCE_VALUE_AUTHORITY_FLAGS


def test_zero_material_evidence_audit_wins_when_discrimination_is_equal() -> None:
    common_outcomes = (
        _outcome("CONFIRMS_LINEAGE", "H1", resolves_decision=True),
        _outcome("REFUTES_LINEAGE", "H2", resolves_decision=True),
    )
    audit = _candidate(
        "audit-first",
        domain=ExperimentDomain.EVIDENCE_AUDIT,
        outcomes=common_outcomes,
        physical_required=False,
        burden=ExperimentBurden(),
        safety_review_required=False,
        safety_review_complete=False,
    )
    physical = _candidate(
        "compound-first",
        outcomes=common_outcomes,
        burden=ExperimentBurden(
            physical_sample_count=4,
            scarce_material_mg=6.0,
            total_active_material_mg=120.0,
            assessor_sessions=8,
        ),
    )

    result = select_evidence_value_experiment(_request(physical, audit))

    assert result.state is EvidenceValueState.SELECTED
    assert result.selected_candidate is not None
    assert result.selected_candidate.candidate_id == "audit-first"
    assert result.selected_candidate.physical_required is False
    assert result.ranked_candidate_ids == ("audit-first", "compound-first")


def test_worst_case_discrimination_outranks_speed_and_material_burden() -> None:
    cheap_weak = _candidate(
        "cheap-weak",
        outcomes=(
            _outcome("A", "H1"),
            _outcome("B", "H2"),
        ),
        burden=ExperimentBurden(physical_sample_count=2, total_active_material_mg=20),
    )
    expensive_strong = _candidate(
        "expensive-strong",
        outcomes=(
            _outcome("A", "H1", "H2", resolves_decision=True),
            _outcome("B", "H2", "H3", resolves_decision=True),
        ),
        burden=ExperimentBurden(
            physical_sample_count=8,
            scarce_material_mg=50,
            total_active_material_mg=500,
            assessor_sessions=24,
            instrument_minutes=180,
        ),
    )

    result = select_evidence_value_experiment(_request(cheap_weak, expensive_strong))

    assert result.selected_candidate is not None
    assert result.selected_candidate.candidate_id == "expensive-strong"
    selected_score = result.candidate_scores[0]
    assert selected_score.candidate_id == "expensive-strong"
    assert selected_score.worst_case_hypotheses_eliminated == 2


@pytest.mark.parametrize(
    "broken_candidate",
    (
        _candidate("wrong-scope", exact_scope_sha256="4" * 64),
        _candidate("wrong-criterion", criterion_id="LIKING"),
        _candidate(
            "unknown-hypothesis",
            outcomes=(
                _outcome("A", "H1"),
                _outcome("B", "H999"),
            ),
        ),
    ),
)
def test_scope_criterion_and_hypothesis_mismatch_fail_closed(
    broken_candidate: EvidenceValueCandidate,
) -> None:
    result = select_evidence_value_experiment(_request(broken_candidate))

    assert result.state is EvidenceValueState.HOLD
    assert result.selected_candidate is None
    assert result.rejections


@pytest.mark.parametrize(
    "broken_candidate",
    (
        _candidate("unqualified", protocol_qualified=False),
        _candidate("lineage-gap", lineage_complete=False),
        _candidate("inventory-gap", inventory_executable=False),
        _candidate("not-blinded", blinded=False),
        _candidate("not-constant", constant_total=False),
        _candidate("open-safety", safety_review_complete=False),
        _candidate("explicit-blocker", blockers=("MISSING_SAMPLE_LINEAGE",)),
        _candidate(
            "nary-incomplete",
            domain=ExperimentDomain.NARY_INTERACTION,
            isolated_arms_complete=False,
        ),
    ),
)
def test_design_blockers_and_incomplete_nary_arms_cannot_be_selected(
    broken_candidate: EvidenceValueCandidate,
) -> None:
    result = select_evidence_value_experiment(_request(broken_candidate))

    assert result.state is EvidenceValueState.HOLD
    assert result.selected_candidate is None
    assert broken_candidate.candidate_id in {
        rejection.candidate_id for rejection in result.rejections
    }


def test_non_discriminating_outcome_is_rejected_instead_of_assigned_fake_value() -> None:
    candidate = _candidate(
        "nondiscriminating",
        outcomes=(
            _outcome("GAIN", "H1"),
            _outcome("AMBIGUOUS"),
        ),
    )

    result = select_evidence_value_experiment(_request(candidate))

    assert result.state is EvidenceValueState.HOLD
    assert "NON_DISCRIMINATING_OUTCOME" in result.rejections[0].reasons


def test_selection_is_single_deterministic_and_never_encodes_a_beauty_or_count_proxy() -> None:
    first = _candidate("A-identical")
    second = replace(first, candidate_id="B-identical")

    result_a = select_evidence_value_experiment(_request(second, first))
    result_b = select_evidence_value_experiment(_request(first, second))

    assert result_a.selected_candidate is not None
    assert result_a.selected_candidate.candidate_id == "A-identical"
    assert result_a.request_sha256 == _request(first, second).record_sha256
    assert result_a.record_sha256 == result_b.record_sha256
    assert result_a.canonical_bytes() == result_b.canonical_bytes()
    assert len(result_a.ranked_candidate_ids) == 2
    assert result_a.authority_flags == EVIDENCE_VALUE_AUTHORITY_FLAGS
    serialized = result_a.canonical_bytes().lower()
    assert b"beauty" not in serialized
    assert b"ingredient_count" not in serialized
    assert b"hedonic_score" not in serialized


def test_result_hash_binds_every_candidate_not_only_the_selected_candidate() -> None:
    selected = _candidate("A-selected")
    unselected = _candidate(
        "B-unselected",
        burden=ExperimentBurden(physical_sample_count=8),
    )
    first = select_evidence_value_experiment(_request(selected, unselected))
    changed_unselected = replace(unselected, source_receipt_sha256="8" * 64)
    second = select_evidence_value_experiment(_request(selected, changed_unselected))

    assert first.selected_candidate is not None
    assert second.selected_candidate is not None
    assert first.selected_candidate.candidate_id == second.selected_candidate.candidate_id
    assert first.request_sha256 != second.request_sha256
    assert first.record_sha256 != second.record_sha256
    assert first.candidate_scores[1].candidate_record_sha256 != (
        second.candidate_scores[1].candidate_record_sha256
    )


def test_invalid_burden_types_do_not_coerce_booleans_or_negative_values() -> None:
    with pytest.raises(TypeError, match="physical_sample_count"):
        ExperimentBurden(physical_sample_count=True)
    with pytest.raises(ValueError, match="scarce_material_mg"):
        ExperimentBurden(scarce_material_mg=-0.1)
