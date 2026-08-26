"""Deterministic validation and evidence-question routing for Sol hypotheses."""

from __future__ import annotations

import re
from dataclasses import dataclass

from engine.solforge.contracts import (
    SolForgeCaseV1,
    SolHypothesisSetV1,
    SolHypothesisV1,
)

_INVENTORY_FACT = re.compile(r"\b(owned|in stock|out of stock|we have|inventory proves)\b", re.I)
_OUT_OF_SCOPE = re.compile(r"\b(replace|rewrite|mutate)\b.*\b(whole|entire|outside)\b", re.I)
_TARGET_REDEFINED = re.compile(r"\b(inventory|availability|stock)\b.*\b(redefine|dictate|control)\b.*\btarget\b", re.I)
_COUNT_RATIONALE = re.compile(r"\b(more|many|count|number of)\b.*\b(ingredient|material)s?\b.*\b(complex|complexity|rich)\b", re.I)
_HEDONIC_ASSERTION = re.compile(r"\b(beautiful|universally liked|will be liked|hedonic winner|more pleasurable)\b", re.I)
_SENSORY_FABRICATION = re.compile(r"\b(smells?|perceived|observed)\b.*\b(deeper|richer|longer|stronger|better)\b", re.I)
_CITATION = re.compile(r"\b(doi|published|paper|study|literature|https?://)\b", re.I)
_PAIRWISE_NARY = re.compile(r"\bpairwise\b.*\b(proves?|establishes?)\b.*\b(synergy|interaction)\b", re.I)


@dataclass(frozen=True, slots=True)
class EvidenceQuestionV1:
    """One exact unresolved claim routed to evidence acquisition."""

    hypothesis_id: str
    unresolved_claim: str
    target_identity: str
    target_function: str
    material_scope: tuple[str, ...]
    required_evidence_type: str
    preferred_design: str
    endpoint: str
    behavior_changing_result: str
    forbidden_authority: tuple[str, ...]
    search_status: str = "UNSEARCHED"

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": "evidence_question_v1",
            "hypothesis_id": self.hypothesis_id,
            "unresolved_claim": self.unresolved_claim,
            "target_identity": self.target_identity,
            "target_function": self.target_function,
            "material_scope": list(self.material_scope),
            "required_evidence_type": self.required_evidence_type,
            "preferred_design": self.preferred_design,
            "endpoint": self.endpoint,
            "behavior_changing_result": self.behavior_changing_result,
            "forbidden_authority": list(self.forbidden_authority),
            "search_status": self.search_status,
        }


@dataclass(frozen=True, slots=True)
class HypothesisValidationResult:
    valid: bool
    no_change: bool
    selected_hypothesis_id: str | None
    blocker_codes: tuple[str, ...]
    evidence_questions: tuple[EvidenceQuestionV1, ...]


def _blockers(hypothesis: SolHypothesisV1) -> tuple[str, ...]:
    combined = " ".join((hypothesis.claim, hypothesis.rationale))
    blockers: list[str] = []
    rules = (
        (_INVENTORY_FACT, "INVENTORY_FACT_UNBOUND"),
        (_OUT_OF_SCOPE, "OUT_OF_SCOPE_MUTATION"),
        (_TARGET_REDEFINED, "TARGET_REDEFINED_BY_INVENTORY"),
        (_COUNT_RATIONALE, "INGREDIENT_COUNT_RATIONALE"),
        (_HEDONIC_ASSERTION, "HEDONIC_ASSERTION"),
        (_SENSORY_FABRICATION, "SENSORY_FABRICATION"),
    )
    for pattern, code in rules:
        if pattern.search(combined):
            blockers.append(code)
    if _CITATION.search(combined) and not hypothesis.evidence_refs:
        blockers.append("UNBOUND_CITATION")
    if hypothesis.intervention_kind == "NARY_DESIGN":
        if len(hypothesis.nary_factors) < 2:
            blockers.append("INCOMPLETE_NARY_FACTORS")
        if _PAIRWISE_NARY.search(combined):
            blockers.append("PAIRWISE_CANNOT_PROVE_NARY_INTERACTION")
    elif hypothesis.nary_factors:
        blockers.append("NARY_FACTORS_WITH_NON_NARY_INTERVENTION")
    return tuple(blockers)


def questions_for_unsupported_hypotheses(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
) -> tuple[EvidenceQuestionV1, ...]:
    """Create closed evidence questions without performing a search."""

    questions: list[EvidenceQuestionV1] = []
    forbidden = ("compounding", "hedonic", "purchase", "release", "safety", "sensory")
    for hypothesis in sorted(hypotheses.hypotheses, key=lambda item: (item.rank, item.hypothesis_id)):
        if hypothesis.evidence_refs:
            continue
        nary = hypothesis.intervention_kind == "NARY_DESIGN"
        questions.append(
            EvidenceQuestionV1(
                hypothesis_id=hypothesis.hypothesis_id,
                unresolved_claim=hypothesis.claim,
                target_identity=case.target_identity,
                target_function=hypothesis.target_function,
                material_scope=hypothesis.material_names,
                required_evidence_type=(
                    "BLINDED_FACTORIAL_TEMPORAL_COMPARISON"
                    if nary
                    else "BLINDED_TEMPORAL_COMPARISON"
                ),
                preferred_design=(
                    "complete constant-total factorial arms"
                    if nary
                    else "constant-total control and one isolated intervention"
                ),
                endpoint=case.criterion,
                behavior_changing_result=(
                    "retain only if the scoped held-out criterion improves without a critical regression"
                ),
                forbidden_authority=forbidden,
            )
        )
    return tuple(questions)


def validate_hypothesis_set(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
) -> HypothesisValidationResult:
    """Validate packet scope and reasoning without inventory or model inference."""

    if hypotheses.case_sha256 != case.record_sha256:
        return HypothesisValidationResult(
            False, False, None, ("CASE_HASH_MISMATCH",), ()
        )
    blockers: list[str] = []
    for hypothesis in sorted(hypotheses.hypotheses, key=lambda item: (item.rank, item.hypothesis_id)):
        blockers.extend(_blockers(hypothesis))
    questions = questions_for_unsupported_hypotheses(case, hypotheses)
    selected = min(
        hypotheses.hypotheses,
        key=lambda item: (item.rank, item.hypothesis_id),
        default=None,
    )
    return HypothesisValidationResult(
        valid=not blockers,
        no_change=not hypotheses.hypotheses,
        selected_hypothesis_id=None if selected is None else selected.hypothesis_id,
        blocker_codes=tuple(dict.fromkeys(blockers)),
        evidence_questions=questions,
    )


__all__ = [
    "EvidenceQuestionV1",
    "HypothesisValidationResult",
    "questions_for_unsupported_hypotheses",
    "validate_hypothesis_set",
]
