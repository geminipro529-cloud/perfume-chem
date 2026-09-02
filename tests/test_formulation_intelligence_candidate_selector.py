from __future__ import annotations

from dataclasses import replace

import pytest

from engine.formulation_intelligence.candidate_selector import (
    CandidateAssessment,
    CandidateDisposition,
    CandidateRequirement,
    CandidateSelectionReport,
    InventoryState,
    MaterialCapabilityDeclaration,
    SelectionView,
    select_candidates,
    selection_to_function_plane_assessment,
)
from engine.formulation_intelligence.contracts import (
    AuthorityCeiling,
    ClaimCardinality,
    PlaneAssessment,
    PlaneId,
)
from engine.formulation_intelligence.plane_synthesis import (
    synthesize_plane_assessments,
)


def _requirement() -> CandidateRequirement:
    return CandidateRequirement(
        target_id="target:iris-cathedral",
        target_name="Iris Cathedral",
        required_recognizers=("rooty iris", "cold incense"),
        exclusions=("tropical fruit", "laundry musk"),
        required_temporal_roles=("opening lift", "drydown persistence"),
        required_spatial_roles=("heart halo", "close-skin anchor"),
        required_functional_roles=("iris recognizer", "incense bridge"),
        minimum_authority=AuthorityCeiling.HYPOTHESIS_ONLY,
    )


def _candidate(
    candidate_id: str,
    *,
    recognizers: tuple[str, ...] = (),
    temporal: tuple[str, ...] = (),
    spatial: tuple[str, ...] = (),
    functional: tuple[str, ...] = (),
    exclusion_tags: tuple[str, ...] = (),
    authority: AuthorityCeiling = AuthorityCeiling.DESIGN_ONLY,
    complete: bool = True,
    missing: tuple[str, ...] = (),
    inventory_state: InventoryState = InventoryState.OWNED,
    exact_stock_ref: str | None = None,
    execution_ready: bool | None = True,
    exact_identity_ref: str | None = None,
) -> MaterialCapabilityDeclaration:
    return MaterialCapabilityDeclaration(
        candidate_id=candidate_id,
        material_name=candidate_id.replace("candidate:", ""),
        exact_identity_ref=exact_identity_ref or f"identity:{candidate_id}",
        target_recognizers=recognizers,
        exclusion_tags=exclusion_tags,
        temporal_roles=temporal,
        spatial_roles=spatial,
        functional_roles=functional,
        authority_ceiling=authority,
        provenance_refs=(f"declaration:{candidate_id}",),
        declaration_complete=complete,
        missing_data=missing,
        inventory_state=inventory_state,
        exact_stock_ref=(exact_stock_ref or f"stock:{candidate_id}")
        if inventory_state is InventoryState.OWNED
        else exact_stock_ref,
        execution_ready=execution_ready,
    )


def _by_id(
    report: CandidateSelectionReport, view: SelectionView
) -> dict[str, CandidateAssessment]:
    assessments = (
        report.ideal_assessments
        if view is SelectionView.IDEAL
        else report.current_inventory_assessments
    )
    return {assessment.candidate_id: assessment for assessment in assessments}


def test_setwise_pareto_retains_tradeoffs_and_marks_strict_dominance() -> None:
    requirement = _requirement()
    recognizer_temporal = _candidate(
        "candidate:alpha",
        recognizers=("rooty iris",),
        temporal=("opening lift",),
    )
    functional_spatial = _candidate(
        "candidate:beta",
        spatial=("heart halo",),
        functional=("incense bridge",),
    )
    strict_subset = _candidate(
        "candidate:gamma",
        recognizers=("rooty iris",),
    )

    report = select_candidates(
        requirement, (strict_subset, functional_spatial, recognizer_temporal)
    )
    ideal = _by_id(report, SelectionView.IDEAL)

    assert report.ideal_frontier_ids == ("candidate:alpha", "candidate:beta")
    assert ideal["candidate:alpha"].disposition is CandidateDisposition.FRONTIER
    assert ideal["candidate:beta"].disposition is CandidateDisposition.FRONTIER
    assert ideal["candidate:gamma"].disposition is CandidateDisposition.DOMINATED
    assert ideal["candidate:gamma"].dominated_by == ("candidate:alpha",)
    assert report.scalar_utility_used is False


def test_inventory_unknown_holds_build_without_rewriting_ideal() -> None:
    candidate = _candidate(
        "candidate:unbound-stock",
        functional=("iris recognizer",),
        inventory_state=InventoryState.UNKNOWN,
        exact_stock_ref=None,
        execution_ready=None,
    )

    report = select_candidates(_requirement(), (candidate,))
    ideal = _by_id(report, SelectionView.IDEAL)[candidate.candidate_id]
    current = _by_id(report, SelectionView.CURRENT_INVENTORY_BUILD)[
        candidate.candidate_id
    ]

    assert ideal.disposition is CandidateDisposition.FRONTIER
    assert current.disposition is CandidateDisposition.HOLD
    assert current.hold_reasons == ("INVENTORY_STATE_UNKNOWN",)
    assert report.ideal_frontier_ids == (candidate.candidate_id,)
    assert report.current_inventory_frontier_ids == ()


@pytest.mark.parametrize(
    ("candidate", "ideal_disposition", "current_disposition", "reason"),
    [
        (
            _candidate(
                "candidate:missing-identity",
                functional=("iris recognizer",),
                exact_identity_ref="identity:temporary",
            ),
            CandidateDisposition.HOLD,
            CandidateDisposition.HOLD,
            "EXACT_IDENTITY_UNRESOLVED",
        ),
        (
            _candidate(
                "candidate:incomplete",
                functional=("iris recognizer",),
                complete=False,
                missing=("functional evidence scope",),
            ),
            CandidateDisposition.HOLD,
            CandidateDisposition.HOLD,
            "DECLARATION_INCOMPLETE",
        ),
        (
            _candidate(
                "candidate:not-owned",
                functional=("iris recognizer",),
                inventory_state=InventoryState.NOT_OWNED,
                exact_stock_ref=None,
                execution_ready=False,
            ),
            CandidateDisposition.FRONTIER,
            CandidateDisposition.UNAVAILABLE,
            "NO_CURRENT_OWNED_STOCK",
        ),
        (
            _candidate(
                "candidate:not-ready",
                functional=("iris recognizer",),
                execution_ready=False,
            ),
            CandidateDisposition.FRONTIER,
            CandidateDisposition.HOLD,
            "EXECUTION_NOT_READY",
        ),
    ],
)
def test_exact_identity_stock_and_completeness_fail_closed(
    candidate: MaterialCapabilityDeclaration,
    ideal_disposition: CandidateDisposition,
    current_disposition: CandidateDisposition,
    reason: str,
) -> None:
    if candidate.candidate_id == "candidate:missing-identity":
        candidate = replace(candidate, exact_identity_ref=None)
    report = select_candidates(_requirement(), (candidate,))
    ideal = _by_id(report, SelectionView.IDEAL)[candidate.candidate_id]
    current = _by_id(report, SelectionView.CURRENT_INVENTORY_BUILD)[
        candidate.candidate_id
    ]

    assert ideal.disposition is ideal_disposition
    assert current.disposition is current_disposition
    relevant = ideal if reason in ideal.hold_reasons else current
    assert reason in relevant.hold_reasons


def test_exclusion_authority_and_no_target_fit_are_not_numeric_penalties() -> None:
    excluded = _candidate(
        "candidate:excluded",
        functional=("iris recognizer",),
        exclusion_tags=("tropical fruit",),
    )
    weak = _candidate(
        "candidate:weak",
        functional=("iris recognizer",),
        authority=AuthorityCeiling.STRUCTURAL_ONLY,
    )
    unrelated = _candidate("candidate:unrelated", functional=("sweetener",))

    report = select_candidates(_requirement(), (unrelated, weak, excluded))
    ideal = _by_id(report, SelectionView.IDEAL)

    assert ideal[excluded.candidate_id].disposition is CandidateDisposition.EXCLUDED
    assert ideal[excluded.candidate_id].exclusion_hits == ("tropical fruit",)
    assert ideal[weak.candidate_id].disposition is CandidateDisposition.INSUFFICIENT_AUTHORITY
    assert ideal[unrelated.candidate_id].disposition is CandidateDisposition.NO_TARGET_FIT
    assert report.ideal_frontier_ids == ()


def test_omission_alternatives_and_unique_nonredundancy_are_structural_only() -> None:
    first = _candidate(
        "candidate:first",
        recognizers=("rooty iris",),
        functional=("iris recognizer",),
    )
    equivalent = _candidate(
        "candidate:equivalent",
        recognizers=("rooty iris",),
        functional=("iris recognizer",),
    )
    unique = _candidate(
        "candidate:unique",
        functional=("incense bridge",),
    )

    report = select_candidates(_requirement(), (unique, equivalent, first))
    ideal = _by_id(report, SelectionView.IDEAL)

    assert ideal[first.candidate_id].omission_alternatives == (equivalent.candidate_id,)
    assert ideal[equivalent.candidate_id].omission_alternatives == (first.candidate_id,)
    assert ideal[first.candidate_id].nonredundant_features == ()
    assert ideal[unique.candidate_id].nonredundant_features == (
        "functional:incense bridge",
    )
    assert report.structural_alternatives_are_sensory_equivalence is False


def test_round_trip_is_closed_deterministic_and_grants_no_execution_or_claim_authority() -> None:
    requirement = _requirement()
    candidates = (
        _candidate("candidate:b", spatial=("heart halo",)),
        _candidate("candidate:a", temporal=("opening lift",)),
    )
    left = select_candidates(requirement, candidates)
    right = select_candidates(requirement, tuple(reversed(candidates)))

    assert left == right
    assert left.content_sha256 == right.content_sha256
    assert CandidateRequirement.from_dict(requirement.as_dict()) == requirement
    assert all(
        MaterialCapabilityDeclaration.from_dict(candidate.as_dict()) == candidate
        for candidate in candidates
    )
    assert CandidateSelectionReport.from_dict(left.as_dict()) == left
    assert left.execution_authorized is False
    assert left.sensory_claims_authorized is False
    assert left.liking_claims_authorized is False
    assert left.safety_claims_authorized is False
    assert left.release_authorized is False

    payload = left.as_dict()
    payload["invented_field"] = True
    with pytest.raises(ValueError, match="closed schema"):
        CandidateSelectionReport.from_dict(payload)

    serialized_keys = set(str(left.as_dict()).casefold().split())
    assert not {"dose", "ppm", "oav", "fraction", "carrier"}.intersection(serialized_keys)


def test_duplicate_candidate_ids_and_incoherent_inventory_claims_are_rejected() -> None:
    candidate = _candidate("candidate:duplicate", functional=("iris recognizer",))
    with pytest.raises(ValueError, match="unique candidate_id"):
        select_candidates(_requirement(), (candidate, candidate))

    with pytest.raises(ValueError, match="owned inventory"):
        replace(
            candidate,
            inventory_state=InventoryState.NOT_OWNED,
            exact_stock_ref="stock:impossible",
            execution_ready=True,
        )


def test_function_plane_adapter_preserves_semantic_target_and_dual_view_members() -> None:
    requirement = _requirement()
    ready = _candidate(
        "candidate:ready",
        recognizers=("rooty iris",),
        temporal=("opening lift",),
        functional=("iris recognizer",),
    )
    build_hold = _candidate(
        "candidate:build-hold",
        recognizers=("rooty iris",),
        spatial=("heart halo",),
        functional=("iris recognizer",),
        inventory_state=InventoryState.UNKNOWN,
        exact_stock_ref=None,
        execution_ready=None,
    )
    result = select_candidates(requirement, (ready, build_hold))

    assessment = selection_to_function_plane_assessment(
        requirement, result, (build_hold, ready)
    )

    assert assessment.plane_id is PlaneId.FUNCTION
    assert assessment.target_scope == requirement.target_id
    assert assessment.matrix_scope == "ideal-and-current-inventory-views"
    assert PlaneAssessment.from_dict(assessment.as_dict()) == assessment
    synthesis = synthesize_plane_assessments((assessment,))
    assert synthesis.conflicts == ()
    assert len(synthesis.harmonized_claims) == len(assessment.claims)

    ideal_decisions = tuple(
        claim
        for claim in assessment.claims
        if claim.claim_key == "ideal_candidate_disposition"
    )
    current_decisions = tuple(
        claim
        for claim in assessment.claims
        if claim.claim_key == "current_inventory_candidate_disposition"
    )
    assert {claim.member_id for claim in ideal_decisions} == {
        ready.candidate_id,
        build_hold.candidate_id,
    }
    assert {claim.member_id for claim in current_decisions} == {
        ready.candidate_id,
        build_hold.candidate_id,
    }
    assert all(claim.cardinality is ClaimCardinality.SET_MEMBER for claim in ideal_decisions)
    assert next(
        claim for claim in ideal_decisions if claim.member_id == build_hold.candidate_id
    ).claim_value.endswith("disposition=frontier")
    assert "disposition=hold" in next(
        claim for claim in current_decisions if claim.member_id == build_hold.candidate_id
    ).claim_value
    assert any(
        unknown.field_key == f"current_inventory_build.{build_hold.candidate_id}"
        and "inventory_state_unknown" in unknown.reason.casefold()
        for unknown in assessment.unknowns
    )


def test_function_plane_preserves_roles_alternatives_ids_provenance_and_authority() -> None:
    requirement = _requirement()
    first = _candidate(
        "candidate:first-adapter",
        recognizers=("rooty iris",),
        temporal=("opening lift",),
        spatial=("heart halo",),
        functional=("iris recognizer",),
        authority=AuthorityCeiling.DESIGN_ONLY,
    )
    equivalent = _candidate(
        "candidate:equivalent-adapter",
        recognizers=("rooty iris",),
        temporal=("opening lift",),
        spatial=("heart halo",),
        functional=("iris recognizer",),
        authority=AuthorityCeiling.DESIGN_ONLY,
    )
    result = select_candidates(requirement, (first, equivalent))

    left = selection_to_function_plane_assessment(
        requirement, result, (first, equivalent)
    )
    right = selection_to_function_plane_assessment(
        requirement, result, (equivalent, first)
    )

    assert left == right
    assert left.content_sha256 == right.content_sha256
    first_status = next(
        claim
        for claim in left.claims
        if claim.claim_key == "ideal_candidate_disposition"
        and claim.member_id == first.candidate_id
    )
    assert first_status.authority_ceiling is first.authority_ceiling
    assert {ref.source_ref for ref in first_status.provenance_refs} == set(
        first.provenance_refs
    )
    assert {ref.source_sha256 for ref in first_status.provenance_refs} == {
        first.content_sha256
    }
    assert any(
        claim.claim_key == "candidate_matched_recognizer"
        and first.candidate_id in claim.claim_value
        and "rooty iris" in claim.claim_value
        for claim in left.claims
    )
    assert any(
        claim.claim_key == "candidate_matched_temporal_role"
        and "opening lift" in claim.claim_value
        for claim in left.claims
    )
    assert any(
        claim.claim_key == "candidate_matched_spatial_role"
        and "heart halo" in claim.claim_value
        for claim in left.claims
    )
    assert any(
        claim.claim_key == "candidate_matched_functional_role"
        and "iris recognizer" in claim.claim_value
        for claim in left.claims
    )
    assert any(
        claim.claim_key == "candidate_omission_alternative"
        and first.candidate_id in claim.claim_value
        and equivalent.candidate_id in claim.claim_value
        and "sensory_equivalence=false" in claim.claim_value
        for claim in left.claims
    )


def test_function_plane_adapter_rejects_stale_or_mismatched_result() -> None:
    requirement = _requirement()
    candidate = _candidate(
        "candidate:bound",
        functional=("iris recognizer",),
    )
    result = select_candidates(requirement, (candidate,))
    changed = replace(candidate, functional_roles=("incense bridge",))

    with pytest.raises(ValueError, match="exact requirement and declarations"):
        selection_to_function_plane_assessment(requirement, result, (changed,))
