from __future__ import annotations

import hashlib
from dataclasses import replace
from decimal import Decimal

import pytest

from engine.sensory.panel_contract import (
    C0ExitDecision,
    EvidenceBinding,
    ExpertiseStratum,
    GateAuthority,
    GateDirection,
    GateKind,
    GateOutcome,
    PanelAttributeRating,
    PanelGateSpecification,
    PanelObservation,
    PanelPerformanceResult,
    ParticipantQualificationReceipt,
    StudyPartition,
    build_c0_construction_lexicon,
    build_c0_protocol_draft,
    evaluate_c0_exit,
    validate_panel_observation,
)


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _locked_protocol():
    lexicon = build_c0_construction_lexicon()
    draft = build_c0_protocol_draft(lexicon)
    bindings = tuple(
        EvidenceBinding.bound(item.binding_id, _sha(item.binding_id))
        for item in draft.bindings
    )
    gate_specs = tuple(
        PanelGateSpecification.locked(
            gate_id=f"c0-{item.kind.value}-v1",
            kind=item.kind,
            metric=f"locked_{item.kind.value}_metric",
            unit="analysis_plan_unit",
            direction=GateDirection.AT_LEAST,
            threshold=Decimal("0.70"),
            success_rule=f"Pass the preregistered {item.kind.value} criterion.",
            failure_rule=f"Fail the preregistered {item.kind.value} criterion.",
            inconclusive_rule=(
                f"Hold when {item.kind.value} evidence is incomplete or unstable."
            ),
        )
        for item in draft.panel_gate_specs
    )
    protocol = replace(
        draft,
        bindings=bindings,
        panel_gate_specs=gate_specs,
        timepoints_seconds=(0, 300, 1800),
        repeat_count=2,
        protocol_locked=True,
    )
    return lexicon, protocol


def _passing_results(protocol):
    analysis_plan_sha256 = next(
        item.sha256
        for item in protocol.bindings
        if item.binding_id == "analysis_plan"
    )
    assert analysis_plan_sha256 is not None
    return tuple(
        PanelPerformanceResult(
            gate_kind=spec.kind,
            gate_spec_sha256=spec.spec_sha256,
            outcome=GateOutcome.PASS,
            observed_value=Decimal("0.80"),
            result_receipt_sha256=_sha(f"result:{spec.kind.value}"),
            participant_set_sha256=_sha("participant-set"),
            analysis_plan_sha256=analysis_plan_sha256,
            study_partition=StudyPartition.PILOT,
        )
        for spec in protocol.panel_gate_specs
    )


def test_c0_lexicon_freezes_eight_construction_axes_and_separate_hedonics() -> None:
    lexicon = build_c0_construction_lexicon()

    construction_ids = tuple(
        item.attribute_id for item in lexicon.attributes if not item.is_hedonic
    )
    assert construction_ids == (
        "airiness",
        "separability",
        "density",
        "coherence",
        "target_fidelity",
        "contrast",
        "emergence",
        "recognition",
    )
    assert tuple(
        item.attribute_id for item in lexicon.attributes if item.is_hedonic
    ) == ("pleasantness",)
    assert all(
        (item.low_anchor.value, item.mid_anchor.value, item.high_anchor.value)
        == (Decimal("0"), Decimal("5"), Decimal("10"))
        for item in lexicon.attributes
    )
    assert lexicon.claims_iso_compliance is False
    assert lexicon.lexicon_sha256 == build_c0_construction_lexicon().lexicon_sha256


def test_draft_is_hold_and_cannot_claim_authority() -> None:
    lexicon = build_c0_construction_lexicon()
    protocol = build_c0_protocol_draft(lexicon)

    report = evaluate_c0_exit(protocol, lexicon, ())

    assert report.decision is C0ExitDecision.HOLD
    assert report.c0_exit_satisfied is False
    assert report.study_authorized is False
    assert report.release_authority is False
    assert report.model_calibration_authority is False
    assert any("required evidence binding" in item for item in report.blockers)
    assert any("gate threshold" in item for item in report.blockers)


def test_locked_protocol_rejects_unbound_evidence_and_unlocked_gates() -> None:
    lexicon = build_c0_construction_lexicon()
    draft = build_c0_protocol_draft(lexicon)

    with pytest.raises(ValueError, match="cannot be locked"):
        replace(draft, protocol_locked=True)


def test_all_three_panel_performance_dimensions_are_independent() -> None:
    _, protocol = _locked_protocol()

    assert tuple(item.kind for item in protocol.panel_gate_specs) == (
        GateKind.DISCRIMINATION,
        GateKind.AGREEMENT,
        GateKind.REPEATABILITY,
    )
    assert all(
        item.authority is GateAuthority.PREREGISTERED_LOCKED
        for item in protocol.panel_gate_specs
    )
    assert len({item.spec_sha256 for item in protocol.panel_gate_specs}) == 3


def test_passed_c0_exit_is_not_study_release_or_model_authority() -> None:
    lexicon, protocol = _locked_protocol()

    report = evaluate_c0_exit(protocol, lexicon, _passing_results(protocol))

    assert report.decision is C0ExitDecision.GO
    assert report.c0_exit_satisfied is True
    assert report.study_authorized is False
    assert report.release_authority is False
    assert report.model_calibration_authority is False
    assert report.blockers == ()


def test_failed_panel_gate_stops_exact_c0_protocol() -> None:
    lexicon, protocol = _locked_protocol()
    results = list(_passing_results(protocol))
    results[1] = replace(results[1], outcome=GateOutcome.FAIL)

    report = evaluate_c0_exit(protocol, lexicon, tuple(results))

    assert report.decision is C0ExitDecision.STOP
    assert report.failed_gates == (GateKind.AGREEMENT,)
    assert report.c0_exit_satisfied is False


def test_failure_cannot_stop_an_unlocked_protocol() -> None:
    lexicon = build_c0_construction_lexicon()
    protocol = build_c0_protocol_draft(lexicon)
    results = tuple(
        PanelPerformanceResult(
            gate_kind=spec.kind,
            gate_spec_sha256=spec.spec_sha256,
            outcome=GateOutcome.FAIL,
            observed_value=Decimal("0.10"),
            result_receipt_sha256=_sha(f"draft-result:{spec.kind.value}"),
            participant_set_sha256=_sha("draft-participant-set"),
            analysis_plan_sha256=_sha("draft-analysis-plan"),
            study_partition=StudyPartition.PILOT,
        )
        for spec in protocol.panel_gate_specs
    )

    report = evaluate_c0_exit(protocol, lexicon, results)

    assert report.decision is C0ExitDecision.HOLD
    assert report.failed_gates == ()


def test_failure_cannot_stop_when_lexicon_identity_mismatches() -> None:
    lexicon, protocol = _locked_protocol()
    mismatched_lexicon = replace(
        lexicon,
        evidence_basis=(*lexicon.evidence_basis, "Deliberate hash-mismatch fixture"),
    )
    results = list(_passing_results(protocol))
    results[0] = replace(results[0], outcome=GateOutcome.FAIL)

    report = evaluate_c0_exit(protocol, mismatched_lexicon, tuple(results))

    assert report.decision is C0ExitDecision.HOLD
    assert report.failed_gates == ()
    assert any("lexicon hash" in item for item in report.blockers)


def test_confirmatory_result_cannot_satisfy_pilot_exit_gate() -> None:
    lexicon, protocol = _locked_protocol()
    results = list(_passing_results(protocol))
    results[0] = replace(
        results[0], study_partition=StudyPartition.CONFIRMATORY
    )

    report = evaluate_c0_exit(protocol, lexicon, tuple(results))

    assert report.decision is C0ExitDecision.HOLD
    assert any("partition" in item for item in report.blockers)


def test_trained_participant_requires_hashed_training_receipt() -> None:
    _, protocol = _locked_protocol()

    with pytest.raises(ValueError, match="training receipt"):
        ParticipantQualificationReceipt(
            participant_token_sha256=_sha("participant"),
            expertise_stratum=ExpertiseStratum.TRAINED_DESCRIPTIVE,
            protocol_sha256=protocol.protocol_sha256,
            consent_receipt_sha256=_sha("consent"),
            privacy_notice_sha256=_sha("privacy"),
            eligibility_receipt_sha256=_sha("eligibility"),
            olfactory_screening_receipt_sha256=_sha("screening"),
            specific_anosmia_screen_receipt_sha256=None,
            training_receipt_sha256=None,
        )


def test_observation_is_blind_code_only_and_requires_complete_lexicon() -> None:
    lexicon, protocol = _locked_protocol()
    receipt = ParticipantQualificationReceipt(
        participant_token_sha256=_sha("participant"),
        expertise_stratum=ExpertiseStratum.TRAINED_DESCRIPTIVE,
        protocol_sha256=protocol.protocol_sha256,
        consent_receipt_sha256=_sha("consent"),
        privacy_notice_sha256=_sha("privacy"),
        eligibility_receipt_sha256=_sha("eligibility"),
        olfactory_screening_receipt_sha256=_sha("screening"),
        specific_anosmia_screen_receipt_sha256=_sha("anosmia"),
        training_receipt_sha256=_sha("training"),
    )
    ratings = tuple(
        PanelAttributeRating(attribute_id=item.attribute_id, value=Decimal("5"))
        for item in lexicon.attributes
    )
    observation = PanelObservation(
        observation_token_sha256=_sha("observation"),
        blind_code="K7Q",
        participant_token_sha256=receipt.participant_token_sha256,
        qualification_receipt_sha256=receipt.receipt_sha256,
        protocol_sha256=protocol.protocol_sha256,
        lexicon_sha256=lexicon.lexicon_sha256,
        session_token_sha256=_sha("session"),
        repeat_index=1,
        sniff_time_seconds=300,
        ratings=ratings,
        target_choice_id="declared-target-a",
    )

    validate_panel_observation(observation, protocol, lexicon, receipt)
    payload = observation.as_dict()
    assert "formula_id" not in payload
    assert "batch_id" not in payload
    assert "assessor" not in payload
    assert payload["blind_code"] == "K7Q"

    incomplete = replace(observation, ratings=ratings[:-1])
    with pytest.raises(ValueError, match="exactly one rating"):
        validate_panel_observation(incomplete, protocol, lexicon, receipt)


def test_rating_missingness_is_explicit_and_range_is_strict() -> None:
    with pytest.raises(ValueError, match="between 0 and 10"):
        PanelAttributeRating(attribute_id="airiness", value=Decimal("10.1"))

    with pytest.raises(ValueError, match="not_applicable_reason"):
        PanelAttributeRating(attribute_id="airiness", value=None)

    rating = PanelAttributeRating(
        attribute_id="target_fidelity",
        value=None,
        not_applicable_reason="No target reference was presented in this task.",
    )
    assert rating.value is None
