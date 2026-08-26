from __future__ import annotations

from dataclasses import replace

import pytest

from engine.solforge.contracts import (
    SolForgeCaseState,
    SolForgeCaseV1,
    SolHypothesisSetV1,
    SolHypothesisV1,
)
from engine.solforge.hypotheses import (
    questions_for_unsupported_hypotheses,
    validate_hypothesis_set,
)

H = "a" * 64


def _case() -> SolForgeCaseV1:
    return SolForgeCaseV1(
        case_id="CASE",
        state=SolForgeCaseState.READY,
        target_identity="dry orange blossom with restrained citrus support",
        ideal_architecture={"heart": ["orange blossom"], "base": ["dry wood"]},
        current_inventory_build={"materials": ["Neroli EO 10%", "Habanolide"]},
        inventory_path="Inventory V5.xlsx",
        inventory_sha256=H,
        formula_sha256="b" * 64,
        dose_receipt_sha256="c" * 64,
        constraints=("one intervention",),
        criterion="DEPTH",
        forbidden_claims=("liking", "release"),
    )


def _hypothesis(**changes) -> SolHypothesisV1:
    values = {
        "hypothesis_id": "H1",
        "rank": 1,
        "claim": "Test Neroli EO 10% as a support bridge.",
        "target_function": "heart continuity",
        "material_names": ("Neroli EO 10%",),
        "intervention_kind": "ADDITION",
        "expected_behavior": "increase floral-citrus continuity at the heart transition",
        "rationale": "target-functional experiment",
        "uncertainty": 0.5,
        "evidence_refs": (),
        "nary_factors": (),
    }
    values.update(changes)
    return SolHypothesisV1(**values)


def _set(*hypotheses: SolHypothesisV1) -> SolHypothesisSetV1:
    return SolHypothesisSetV1(
        case_sha256=_case().record_sha256,
        model_identity="Sol 5.6 xhigh",
        reasoning_setting="xhigh",
        prompt_sha256=H,
        input_sha256="b" * 64,
        output_sha256="c" * 64,
        hypotheses=hypotheses,
        uncertainty="physical behavior is untested",
    )


@pytest.mark.parametrize(
    ("changes", "blocker"),
    [
        ({"claim": "Neroli is owned and in stock."}, "INVENTORY_FACT_UNBOUND"),
        ({"claim": "Replace the whole formula outside the case."}, "OUT_OF_SCOPE_MUTATION"),
        ({"rationale": "Inventory availability should redefine the target."}, "TARGET_REDEFINED_BY_INVENTORY"),
        ({"rationale": "More ingredients means more complexity."}, "INGREDIENT_COUNT_RATIONALE"),
        ({"claim": "This will be beautiful and universally liked."}, "HEDONIC_ASSERTION"),
        ({"claim": "The untested blend smells deeper at two hours."}, "SENSORY_FABRICATION"),
        ({"rationale": "A published DOI proves this.", "evidence_refs": ()}, "UNBOUND_CITATION"),
        (
            {
                "intervention_kind": "NARY_DESIGN",
                "nary_factors": ("Habanolide", "Romandolide"),
                "rationale": "A pairwise comparison proves synergy.",
            },
            "PAIRWISE_CANNOT_PROVE_NARY_INTERACTION",
        ),
    ],
)
def test_validation_rejects_unsupported_reasoning(changes, blocker: str) -> None:
    result = validate_hypothesis_set(_case(), _set(_hypothesis(**changes)))
    assert result.valid is False
    assert blocker in result.blocker_codes


def test_validation_rejects_case_hash_mismatch() -> None:
    packet = replace(_set(_hypothesis()), case_sha256="f" * 64)
    result = validate_hypothesis_set(_case(), packet)
    assert result.blocker_codes == ("CASE_HASH_MISMATCH",)


def test_empty_hypothesis_set_is_valid_no_change() -> None:
    result = validate_hypothesis_set(_case(), _set())
    assert result.valid is True
    assert result.no_change is True
    assert result.blocker_codes == ()


def test_unresolved_hypothesis_becomes_a_closed_evidence_question() -> None:
    questions = questions_for_unsupported_hypotheses(_case(), _set(_hypothesis()))
    assert len(questions) == 1
    question = questions[0]
    assert question.target_identity == _case().target_identity
    assert question.material_scope == ("Neroli EO 10%",)
    assert question.required_evidence_type == "BLINDED_TEMPORAL_COMPARISON"
    assert question.search_status == "UNSEARCHED"
    assert question.forbidden_authority == (
        "compounding",
        "hedonic",
        "purchase",
        "release",
        "safety",
        "sensory",
    )


def test_explicit_uncertainty_and_bound_evidence_are_accepted() -> None:
    hypothesis = _hypothesis(evidence_refs=("d" * 64,), uncertainty=0.7)
    result = validate_hypothesis_set(_case(), _set(hypothesis))
    assert result.valid is True
    assert result.selected_hypothesis_id == "H1"
