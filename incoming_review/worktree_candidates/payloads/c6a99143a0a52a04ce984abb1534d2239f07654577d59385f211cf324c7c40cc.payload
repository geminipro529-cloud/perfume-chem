from __future__ import annotations

from dataclasses import replace

import pytest

from engine.evidence.augmentation import (
    AUGMENTATION_AUTHORITY_FALSE,
    DecisionDeltaV1,
    EvidenceAugmentationState,
    EvidenceDeltaReceiptV1,
    hold_receipt,
    no_augmentation_receipt,
)


def _delta() -> DecisionDeltaV1:
    return DecisionDeltaV1(
        delta_id="DELTA-1",
        decision_effect="Request one constant-total citrus role comparison.",
        observed_facts=("Neroli is support-only in the frozen target.",),
        derived_calculations=("changed_factors=1",),
        hypotheses=("Primary Neroli may drift toward orange blossom.",),
        forbidden_inferences=("No sensory or liking result exists.",),
    )


def _receipt(**changes: object) -> EvidenceDeltaReceiptV1:
    values: dict[str, object] = {
        "module_id": "architectural_delta",
        "exact_scope": "TARGET-1/CITRUS_ROLE",
        "state": EvidenceAugmentationState.AUGMENT,
        "input_sha256": "a" * 64,
        "evidence_sha256": "b" * 64,
        "policy_sha256": "c" * 64,
        "source_binding_sha256": ("d" * 64,),
        "reason_codes": ("ONE_FACTOR_UNRESOLVED",),
        "delta": _delta(),
        "blockers": (),
        "next_action": "COMPARE:NEROLI_PRIMARY:NEROLI_SUPPORT_ONLY",
    }
    values.update(changes)
    return EvidenceDeltaReceiptV1(**values)


def test_no_augmentation_is_successful_and_grants_no_authority() -> None:
    receipt = no_augmentation_receipt(
        module_id="temporal_sensory_ledger",
        exact_scope="P1/BLIND-A/DEPTH/60-1800s",
        input_sha256="a" * 64,
        evidence_sha256="b" * 64,
        policy_sha256="c" * 64,
        reasons=("QUESTION_ALREADY_RESOLVED",),
    )
    assert receipt.state is EvidenceAugmentationState.NO_AUGMENTATION
    assert receipt.next_action is None
    assert set(receipt.authority.values()) == {False}
    restored = EvidenceDeltaReceiptV1.from_dict(receipt.as_dict())
    assert restored.receipt_sha256 == receipt.receipt_sha256


def test_augment_requires_exactly_one_delta_and_source_binding() -> None:
    receipt = _receipt()
    assert receipt.delta == _delta()
    assert DecisionDeltaV1.from_dict(receipt.delta.as_dict()) == receipt.delta
    with pytest.raises(ValueError, match="AUGMENT requires one decision delta"):
        _receipt(delta=None)
    with pytest.raises(ValueError, match="AUGMENT requires source bindings"):
        _receipt(source_binding_sha256=())


def test_nonaugment_states_forbid_delta_and_no_augmentation_forbids_action() -> None:
    with pytest.raises(ValueError, match="only AUGMENT may contain a decision delta"):
        _receipt(state=EvidenceAugmentationState.HOLD)
    with pytest.raises(ValueError, match="NO_AUGMENTATION cannot request an action"):
        _receipt(
            state=EvidenceAugmentationState.NO_AUGMENTATION,
            delta=None,
            source_binding_sha256=(),
        )


def test_hold_requires_blockers_and_round_trips() -> None:
    receipt = hold_receipt(
        module_id="hedonic_preference",
        exact_scope="P1/LIKING/DRYDOWN",
        input_sha256="a" * 64,
        evidence_sha256="b" * 64,
        policy_sha256="c" * 64,
        reasons=("ORDER_CONFOUNDED",),
        blockers=("First-presented item is completely confounded with sample.",),
        next_action="BALANCE_ORDER",
    )
    assert receipt.state is EvidenceAugmentationState.HOLD
    assert EvidenceDeltaReceiptV1.from_dict(receipt.as_dict()) == receipt


def test_closed_schema_duplicates_nonfinite_values_and_true_authority_fail() -> None:
    with pytest.raises(ValueError, match="duplicate reason_codes"):
        _receipt(reason_codes=("ONE_FACTOR_UNRESOLVED", "one_factor_unresolved"))
    with pytest.raises((TypeError, ValueError), match="derived_calculations"):
        replace(_delta(), derived_calculations=(float("nan"),))

    payload = _receipt().as_dict()
    payload["unknown"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        EvidenceDeltaReceiptV1.from_dict(payload)

    payload = _receipt().as_dict()
    payload["delta"] = [payload["delta"], payload["delta"]]
    with pytest.raises(TypeError, match="delta"):
        EvidenceDeltaReceiptV1.from_dict(payload)

    payload = _receipt().as_dict()
    payload["authority"] = {**AUGMENTATION_AUTHORITY_FALSE, "release": True}
    with pytest.raises(ValueError, match="all-false"):
        EvidenceDeltaReceiptV1.from_dict(payload)
