from __future__ import annotations

from dataclasses import replace

import pytest

from engine.solforge.conclusions import (
    CONCLUSION_AUTHORITY_FLAGS,
    ConclusionDisposition,
    ConclusionLevel,
    ScientificConclusionReceiptV1,
    evaluate_conclusion_transition,
    next_required_evidence,
)


def _receipt(**changes) -> ScientificConclusionReceiptV1:
    values = {
        "conclusion_id": "C-1",
        "claim": "A matched-total omission protocol operationalizes a target-linked question.",
        "exact_scope": "program=architectural-delta;criterion=TARGET_FIDELITY;population=software",
        "level": ConclusionLevel.RESEARCH_MAPPED,
        "disposition": ConclusionDisposition.ADVANCE,
        "criterion": "TARGET_FIDELITY",
        "direct_evidence_sha256": ("a" * 64,),
        "contrary_evidence_sha256": (),
        "contrary_evidence_reviewed": True,
        "evidence_kinds": ("LITERATURE",),
        "physical_evidence_valid": False,
        "heldout_baseline_passed": False,
        "generalization_scope_declared": False,
        "inference": "The literature maps a testable question only.",
        "uncertainty": "Transfer to finished perfume is unknown.",
        "failed_tests": (),
        "permitted_use": ("protocol design",),
        "forbidden_extrapolations": ("formula-specific sensory effect", "liking"),
        "prior_receipt_sha256": None,
    }
    values.update(changes)
    return ScientificConclusionReceiptV1(**values)


def test_receipt_round_trips_with_false_authority() -> None:
    receipt = _receipt()
    assert ScientificConclusionReceiptV1.from_dict(receipt.as_dict()) == receipt
    assert receipt.as_dict()["authority_flags"] == CONCLUSION_AUTHORITY_FLAGS


def test_first_conclusion_must_start_at_research_mapped() -> None:
    proposed = _receipt(level=ConclusionLevel.HYPOTHESIS_OPERATIONALIZED)
    assert "first conclusion" in evaluate_conclusion_transition(None, proposed)[0]


def test_levels_are_monotonic_and_cannot_skip() -> None:
    prior = _receipt()
    skipped = _receipt(
        conclusion_id="C-2",
        level=ConclusionLevel.PROTOCOL_VALIDATED,
        prior_receipt_sha256=prior.record_sha256,
    )
    assert "skip" in evaluate_conclusion_transition(prior, skipped)[0]
    valid = replace(skipped, level=ConclusionLevel.HYPOTHESIS_OPERATIONALIZED)
    assert evaluate_conclusion_transition(prior, valid) == ()


@pytest.mark.parametrize("kind", ["LITERATURE", "MODEL_OUTPUT", "SYNTHETIC_TEST"])
def test_nonphysical_evidence_cannot_promote_observed_effect(kind: str) -> None:
    prior = _receipt(
        level=ConclusionLevel.PROTOCOL_VALIDATED,
        disposition=ConclusionDisposition.ADVANCE,
    )
    proposed = _receipt(
        conclusion_id="C-2",
        level=ConclusionLevel.OBSERVED_EFFECT,
        evidence_kinds=(kind,),
        prior_receipt_sha256=prior.record_sha256,
    )
    assert "physical evidence" in " ".join(
        evaluate_conclusion_transition(prior, proposed)
    )


def test_hedonic_stage_requires_liking_and_heldout_baseline() -> None:
    prior = _receipt(level=ConclusionLevel.REPLICATED_EXACT_SCOPE)
    proposed = _receipt(
        conclusion_id="C-H",
        level=ConclusionLevel.HEDONIC_PREDICTIVE_VALIDATED,
        criterion="DEPTH",
        evidence_kinds=("PHYSICAL_OBSERVATION",),
        physical_evidence_valid=True,
        heldout_baseline_passed=False,
        prior_receipt_sha256=prior.record_sha256,
    )
    issues = " ".join(evaluate_conclusion_transition(prior, proposed))
    assert "LIKING" in issues
    assert "held-out baseline" in issues


def test_owner_scope_cannot_become_population_scope_without_generalization() -> None:
    prior = _receipt(
        level=ConclusionLevel.HEDONIC_PREDICTIVE_VALIDATED,
        criterion="LIKING",
        exact_scope="population=OWNER;criterion=LIKING",
    )
    proposed = _receipt(
        conclusion_id="C-G",
        level=ConclusionLevel.GENERALIZATION_TESTED,
        criterion="LIKING",
        exact_scope="population=CONSUMER;criterion=LIKING",
        evidence_kinds=("PHYSICAL_OBSERVATION",),
        physical_evidence_valid=True,
        heldout_baseline_passed=True,
        prior_receipt_sha256=prior.record_sha256,
    )
    assert "generalization" in " ".join(
        evaluate_conclusion_transition(prior, proposed)
    ).casefold()


def test_scope_change_and_missing_contrary_review_fail_closed() -> None:
    prior = _receipt()
    proposed = _receipt(
        conclusion_id="C-2",
        level=ConclusionLevel.HYPOTHESIS_OPERATIONALIZED,
        exact_scope="different scope",
        contrary_evidence_reviewed=False,
        prior_receipt_sha256=prior.record_sha256,
    )
    issues = " ".join(evaluate_conclusion_transition(prior, proposed))
    assert "scope" in issues
    assert "contrary" in issues


def test_unhashed_parent_or_evidence_is_rejected() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        _receipt(direct_evidence_sha256=("not-hashed",))
    prior = _receipt()
    with pytest.raises(ValueError, match="prior_receipt_sha256"):
        _receipt(prior_receipt_sha256="bad")
    mismatch = _receipt(
        conclusion_id="C-2",
        level=ConclusionLevel.HYPOTHESIS_OPERATIONALIZED,
        prior_receipt_sha256="f" * 64,
    )
    assert "parent" in evaluate_conclusion_transition(prior, mismatch)[0]


def test_negative_dispositions_do_not_falsely_advance() -> None:
    prior = _receipt()
    for disposition in (
        ConclusionDisposition.RESEARCH_ONLY,
        ConclusionDisposition.PROVENANCE_TOMBSTONE,
        ConclusionDisposition.DIAGNOSTIC_ONLY,
    ):
        proposed = _receipt(
            conclusion_id=f"C-{disposition.value}",
            disposition=disposition,
            level=ConclusionLevel.RESEARCH_MAPPED,
            prior_receipt_sha256=prior.record_sha256,
            failed_tests=("failed exact-scope benchmark",),
        )
        assert evaluate_conclusion_transition(prior, proposed) == ()


def test_next_required_evidence_is_stage_specific() -> None:
    assert "operational" in next_required_evidence(_receipt()).casefold()
    protocol = _receipt(level=ConclusionLevel.PROTOCOL_VALIDATED)
    assert "physical" in next_required_evidence(protocol).casefold()
