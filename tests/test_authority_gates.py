from dataclasses import replace
from datetime import date

import pytest

from engine.authority_gates import (
    ActionState,
    ActorType,
    ClaimAuthorityInput,
    ClaimDecision,
    ClaimType,
    ConcentrationGateInput,
    FamilyEvaluationInput,
    GateReason,
    ModeAction,
    OperatingMode,
    PermissionContext,
    RegulatoryDecision,
    RegulatorySnapshot,
    evaluate_claim_authority,
    evaluate_concentration_gate,
    evaluate_family_gate,
    evaluate_mode_action,
    evaluate_regulatory_gate,
    evaluate_transition,
)
from engine.quantities import ConcentrationBasis


def _complete_claim(claim_type: ClaimType) -> ClaimAuthorityInput:
    return ClaimAuthorityInput(
        claim_type=claim_type,
        target_row_coverage_complete=True,
        source_coverage_complete=True,
        source_independence=True,
        identity_resolved=True,
        quantity_basis_complete=True,
        uncertainty_bounded=True,
        contradiction_present=False,
        method_validated=True,
        analytical_support=True,
        sensory_support=True,
        model_applicable=True,
        safety_complete=True,
        family_defined=True,
        family_evidence_complete=True,
        human_reviewed=True,
        scope_defined=True,
        exact_evidence=True,
        documentary_support=True,
    )


def test_actor_and_action_vocabularies_are_complete():
    assert {item.value for item in ActorType} == {
        "AI_ASSISTANT",
        "HUMAN_OPERATOR",
        "HUMAN_REVIEWER",
        "ADMINISTRATOR",
        "INSTRUMENT_IMPORT_SERVICE",
        "AUTOMATED_VERIFIER",
    }
    assert {item.value for item in ActionState} == {
        "PROPOSED",
        "REVIEWED",
        "CONFIRMED",
        "MEASURED",
        "COMMITTED",
        "CORRECTED",
        "CANCELLED",
        "FAILED",
    }


@pytest.mark.parametrize(
    ("mode", "allowed_action", "blocked_action"),
    [
        (
            OperatingMode.RECONSTRUCTION,
            ModeAction.EVIDENCE_CAPTURE,
            ModeAction.RESERVATION,
        ),
        (
            OperatingMode.CREATIVE_FORMULATION,
            ModeAction.CANDIDATE_GENERATION,
            ModeAction.ATOMIC_COMMIT,
        ),
        (
            OperatingMode.STRUCTURAL_CHASSIS,
            ModeAction.ANCHOR_FLOORS,
            ModeAction.SUBSTITUTION,
        ),
        (
            OperatingMode.FLANKER_MODULE,
            ModeAction.MODULE_ENVELOPE,
            ModeAction.ATOMIC_COMMIT,
        ),
        (
            OperatingMode.INVENTORY_MAPPING,
            ModeAction.LOT_MATCHING,
            ModeAction.TARGET_REWRITE,
        ),
        (
            OperatingMode.LIVE_BATCH,
            ModeAction.ATOMIC_COMMIT,
            ModeAction.CANDIDATE_GENERATION,
        ),
        (
            OperatingMode.BATCH_RESCUE,
            ModeAction.RESCUE_PROPOSAL,
            ModeAction.TARGET_REWRITE,
        ),
        (
            OperatingMode.SENSORY_EXPERIMENT,
            ModeAction.RANDOMIZATION,
            ModeAction.FORMULA_MUTATION,
        ),
        (
            OperatingMode.ANALYTICAL_INTERPRETATION,
            ModeAction.PEAK_RECORD,
            ModeAction.TARGET_REWRITE,
        ),
        (
            OperatingMode.COMPLIANCE_BUILD,
            ModeAction.CONSTITUENT_AGGREGATION,
            ModeAction.CERTIFICATION,
        ),
        (
            OperatingMode.RELEASE_REVIEW,
            ModeAction.READ_ONLY_REVIEW,
            ModeAction.ATOMIC_COMMIT,
        ),
    ],
)
def test_all_eleven_modes_allow_only_their_declared_actions(
    mode,
    allowed_action,
    blocked_action,
):
    allowed = evaluate_mode_action(mode, allowed_action)
    blocked = evaluate_mode_action(mode, blocked_action)

    assert allowed.allowed is True
    assert allowed.reasons == ()
    assert blocked.allowed is False
    assert blocked.reasons == (GateReason.ACTION_NOT_ALLOWED_IN_MODE,)


def test_ai_cannot_confirm_commit_or_self_release():
    confirmation = evaluate_transition(
        PermissionContext(
            actor=ActorType.AI_ASSISTANT,
            mode=OperatingMode.LIVE_BATCH,
            current_state=ActionState.REVIEWED,
            requested_state=ActionState.CONFIRMED,
            evidence_complete=True,
            safety_clear=True,
            human_confirmed=True,
        )
    )
    release = evaluate_transition(
        PermissionContext(
            actor=ActorType.AI_ASSISTANT,
            mode=OperatingMode.RELEASE_REVIEW,
            current_state=ActionState.REVIEWED,
            requested_state=ActionState.CONFIRMED,
            evidence_complete=True,
            safety_clear=True,
            human_confirmed=True,
        )
    )

    assert GateReason.ACTOR_NOT_AUTHORIZED in confirmation.reasons
    assert GateReason.AI_SELF_RELEASE_BLOCKED in release.reasons


def test_commit_requires_valid_sequence_evidence_safety_and_confirmation():
    baseline = PermissionContext(
        actor=ActorType.HUMAN_OPERATOR,
        mode=OperatingMode.LIVE_BATCH,
        current_state=ActionState.MEASURED,
        requested_state=ActionState.COMMITTED,
        evidence_complete=True,
        safety_clear=True,
        human_confirmed=True,
    )
    assert evaluate_transition(baseline).allowed is True
    assert evaluate_transition(
        replace(baseline, current_state=ActionState.PROPOSED)
    ).reasons == (GateReason.INVALID_STATE_TRANSITION,)
    assert GateReason.EVIDENCE_INCOMPLETE in evaluate_transition(
        replace(baseline, evidence_complete=False)
    ).reasons
    assert GateReason.SAFETY_NOT_CLEARED in evaluate_transition(
        replace(baseline, safety_clear=False)
    ).reasons
    assert GateReason.HUMAN_CONFIRMATION_REQUIRED in evaluate_transition(
        replace(baseline, human_confirmed=False)
    ).reasons


@pytest.mark.parametrize(
    ("claim_type", "field_name", "reason"),
    [
        (
            ClaimType.EXACT_MASS_BALANCE,
            "target_row_coverage_complete",
            GateReason.TARGET_ROW_COVERAGE_INCOMPLETE,
        ),
        (
            ClaimType.IDENTITY,
            "identity_resolved",
            GateReason.IDENTITY_UNRESOLVED,
        ),
        (
            ClaimType.ACTIVE_CONCENTRATION,
            "quantity_basis_complete",
            GateReason.QUANTITY_BASIS_INCOMPLETE,
        ),
        (
            ClaimType.ABOVE_THRESHOLD_LIKELIHOOD,
            "model_applicable",
            GateReason.MODEL_NOT_APPLICABLE,
        ),
        (
            ClaimType.SENSORY_INTENSITY,
            "sensory_support",
            GateReason.SENSORY_SUPPORT_MISSING,
        ),
        (
            ClaimType.TARGET_SIMILARITY,
            "source_independence",
            GateReason.SOURCE_INDEPENDENCE_MISSING,
        ),
        (
            ClaimType.FAMILY_PRESERVATION,
            "family_defined",
            GateReason.FAMILY_UNDEFINED,
        ),
        (
            ClaimType.REGULATORY_SCREEN,
            "safety_complete",
            GateReason.SAFETY_INCOMPLETE,
        ),
        (
            ClaimType.RELEASE,
            "human_reviewed",
            GateReason.HUMAN_REVIEW_REQUIRED,
        ),
    ],
)
def test_each_claim_withholds_when_its_own_required_dimension_is_missing(
    claim_type,
    field_name,
    reason,
):
    result = evaluate_claim_authority(
        replace(_complete_claim(claim_type), **{field_name: False})
    )

    assert result.decision is ClaimDecision.WITHHOLD_UNKNOWN
    assert reason in result.reasons


def test_contradiction_blocks_and_complete_evidence_allows_exact():
    complete = _complete_claim(ClaimType.IDENTITY)
    assert (
        evaluate_claim_authority(complete).decision
        is ClaimDecision.ALLOW_EXACT
    )

    contradicted = evaluate_claim_authority(
        replace(complete, contradiction_present=True)
    )
    assert contradicted.decision is ClaimDecision.BLOCK
    assert contradicted.reasons == (GateReason.CONTRADICTION_PRESENT,)


def test_undefined_family_withholds_only_family_specific_claim():
    family = evaluate_family_gate(
        FamilyEvaluationInput(
            archetype_version=None,
            protected_anchors=(),
            allowed_uncertainty=0.1,
            genre_shifting_materials=(),
            target_values={},
            current_values={},
            unknowns=("family archetype",),
            evidence_complete=False,
        )
    )
    identity = evaluate_claim_authority(
        replace(
            _complete_claim(ClaimType.IDENTITY),
            family_defined=False,
            family_evidence_complete=False,
        )
    )

    assert family.decision is ClaimDecision.WITHHOLD_UNKNOWN
    assert family.reasons == (GateReason.FAMILY_UNDEFINED,)
    assert identity.decision is ClaimDecision.ALLOW_EXACT


def test_family_gate_blocks_drift_and_genre_shift():
    result = evaluate_family_gate(
        FamilyEvaluationInput(
            archetype_version="fougere-v1",
            protected_anchors=("lavender",),
            allowed_uncertainty=0.1,
            genre_shifting_materials=("calone",),
            target_values={"lavender": 0.3},
            current_values={"lavender": 0.1, "calone": 0.2},
            unknowns=(),
            evidence_complete=True,
        )
    )

    assert result.decision is ClaimDecision.BLOCK
    assert GateReason.FAMILY_DRIFT_EXCEEDED in result.reasons
    assert GateReason.GENRE_SHIFT in result.reasons


def test_concentration_gate_blocks_missing_basis_not_carrier_presence():
    missing = evaluate_concentration_gate(
        ConcentrationGateInput(
            active_fraction=0.1,
            basis=None,
            density_required=False,
            density_present=False,
            carrier_present=True,
        )
    )
    carrier = evaluate_concentration_gate(
        ConcentrationGateInput(
            active_fraction=0.1,
            basis=ConcentrationBasis.MASS_FRACTION,
            density_required=False,
            density_present=False,
            carrier_present=True,
        )
    )

    assert missing.decision is ClaimDecision.WITHHOLD_UNKNOWN
    assert missing.reasons == (GateReason.QUANTITY_BASIS_INCOMPLETE,)
    assert carrier.decision is ClaimDecision.ALLOW_SCOPED
    assert carrier.reasons == ()


def _regulatory_snapshot(**overrides) -> RegulatorySnapshot:
    values = {
        "standard_identifier": "IFRA-style-test-snapshot",
        "amendment": "2026-01",
        "source_digest": "a" * 64,
        "standard_state": "EFFECTIVE",
        "product_category": "fine-fragrance",
        "jurisdiction": "TEST",
        "formula_version": "formula-v1",
        "constituent_basis": "mass_fraction",
        "natural_assumptions": (),
        "evaluation_date": date(2026, 7, 30),
        "evaluator_version": "reg-gate-v1",
        "unresolved_items": (),
        "has_violation": False,
    }
    values.update(overrides)
    return RegulatorySnapshot(**values)


def test_only_complete_effective_regulatory_snapshot_passes_declared_scope():
    assert (
        evaluate_regulatory_gate(_regulatory_snapshot()).decision
        is RegulatoryDecision.PASS_FOR_DECLARED_SCOPE
    )
    assert (
        evaluate_regulatory_gate(
            _regulatory_snapshot(standard_state="DRAFT")
        ).decision
        is RegulatoryDecision.NOT_EVALUATED
    )
    assert (
        evaluate_regulatory_gate(
            _regulatory_snapshot(unresolved_items=("unknown natural",))
        ).decision
        is RegulatoryDecision.UNKNOWN
    )
    assert (
        evaluate_regulatory_gate(
            _regulatory_snapshot(has_violation=True)
        ).decision
        is RegulatoryDecision.FAIL
    )
