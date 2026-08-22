from __future__ import annotations

import hashlib

import pytest

from engine.perception.complexity_decision_cards import (
    DecisionCard,
    DecisionCardState,
)


def valid_card(**overrides: object) -> DecisionCard:
    values: dict[str, object] = {
        "module_id": "construction_profile",
        "decision_kind": "TARGET_DEFINING_RELATION",
        "state": DecisionCardState.DECIDE,
        "decision_question": "Which relation creates the target's depth?",
        "decisive_evidence": ("foreground ownership changes at drydown",),
        "preserve": "recognizable iris",
        "reject": "ingredient-count reasoning",
        "controlled_comparison": "full design versus relation omission",
        "claim_ceiling": "COMPUTATIONAL_DESIGN_ONLY",
        "source_result_sha256": "a" * 64,
    }
    values.update(overrides)
    return DecisionCard(**values)  # type: ignore[arg-type]


def test_decision_card_is_hash_bound_closed_and_bounded() -> None:
    card = valid_card()

    assert card.as_dict()["schema_version"] == "complexity_decision_card_v1"
    assert len(card.to_json_bytes()) <= 1600
    assert card.card_sha256 == hashlib.sha256(card.to_json_bytes()).hexdigest()
    assert set(card.as_dict()) == {
        "schema_version",
        "module_id",
        "decision_kind",
        "state",
        "decision_question",
        "decisive_evidence",
        "preserve",
        "reject",
        "controlled_comparison",
        "claim_ceiling",
        "source_result_sha256",
    }


def test_decision_card_rejects_more_than_three_evidence_facts() -> None:
    with pytest.raises(ValueError, match="at most three"):
        valid_card(decisive_evidence=("a", "b", "c", "d"))


@pytest.mark.parametrize(
    "field_name",
    (
        "module_id",
        "decision_kind",
        "decision_question",
        "preserve",
        "reject",
        "controlled_comparison",
        "claim_ceiling",
    ),
)
def test_decision_card_rejects_blank_contract_text(field_name: str) -> None:
    with pytest.raises(ValueError, match=field_name):
        valid_card(**{field_name: "  "})


def test_decision_card_rejects_invalid_source_hash() -> None:
    with pytest.raises(ValueError, match="source_result_sha256"):
        valid_card(source_result_sha256="not-a-hash")


def test_decision_card_rejects_empty_or_blank_evidence() -> None:
    with pytest.raises(ValueError, match="one to three"):
        valid_card(decisive_evidence=())
    with pytest.raises(ValueError, match="decisive_evidence"):
        valid_card(decisive_evidence=("valid", " "))


def test_decision_card_rejects_payload_over_byte_limit() -> None:
    card = valid_card(reject="x" * 1600)

    with pytest.raises(ValueError, match="exceeds 1600"):
        card.to_json_bytes()


def test_decision_card_requires_enum_state() -> None:
    with pytest.raises(TypeError, match="DecisionCardState"):
        valid_card(state="DECIDE")
