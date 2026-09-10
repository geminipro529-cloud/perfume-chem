"""Ratio-bound n-ary interaction design contract."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Iterable

from .canonical import canonical_decimal, parse_decimal, sha256_payload


class InteractionContractError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class EvidenceState(str, Enum):
    DESIGNED = "DESIGNED"
    SOURCE_SUPPORTED_DESIGN = "SOURCE_SUPPORTED_DESIGN"
    OBSERVED = "OBSERVED"


class PhysicalState(str, Enum):
    NOT_TESTED = "NOT_TESTED"
    OBSERVED = "OBSERVED"


class DerivationMethod(str, Enum):
    EXACT_FORMULA_PARTS = "EXACT_FORMULA_PARTS"
    PREREGISTERED_RATIO = "PREREGISTERED_RATIO"
    PAIR_SCORE_MULTIPLICATION = "PAIR_SCORE_MULTIPLICATION"


@dataclass(frozen=True)
class Participant:
    participant_id: str
    role: str
    member: str
    ratio: Decimal

    @classmethod
    def create(
        cls,
        *,
        participant_id: str,
        role: str,
        member: str,
        ratio: Decimal | str | int,
    ) -> "Participant":
        value = parse_decimal(ratio)
        if not participant_id.strip():
            raise InteractionContractError("MISSING_PARTICIPANT_ID", "participant ID is required")
        if not role.strip():
            raise InteractionContractError("MISSING_PARTICIPANT_ROLE", "participant role is required")
        if not member.strip():
            raise InteractionContractError("MISSING_PARTICIPANT_MEMBER", "participant member is required")
        if value <= 0:
            raise InteractionContractError("INVALID_RATIO", "participant ratio must be positive")
        return cls(participant_id=participant_id, role=role, member=member, ratio=value)


@dataclass(frozen=True)
class NaryInteraction:
    record_id: str
    participants: tuple[Participant, ...]
    matrix: str
    phase: str
    context: str
    evidence_state: EvidenceState
    physical_state: PhysicalState
    derivation_method: DerivationMethod
    source_formula_hash: str | None
    authority: str
    record_hash: str


def build_nary_interaction(
    *,
    record_id: str,
    participants: Iterable[Participant],
    matrix: str,
    phase: str,
    context: str,
    evidence_state: EvidenceState,
    physical_state: PhysicalState,
    derivation_method: DerivationMethod,
    source_formula_hash: str | None,
    authority: str = "FORMULA_SIGNATURE_SUPPORT_ONLY",
) -> NaryInteraction:
    members = tuple(participants)
    if not record_id.strip():
        raise InteractionContractError("MISSING_RECORD_ID", "record ID is required")
    if len(members) < 2:
        raise InteractionContractError("ARITY_BELOW_TWO", "n-ary record requires at least two participants")
    ids = [item.participant_id for item in members]
    if len(set(ids)) != len(ids):
        raise InteractionContractError("DUPLICATE_PARTICIPANT", "participant IDs must be unique")
    if not matrix.strip() or not phase.strip() or not context.strip():
        raise InteractionContractError(
            "MISSING_CONTEXT",
            "matrix, phase, and context are all required",
        )
    total = sum((item.ratio for item in members), Decimal("0"))
    if total != Decimal("1"):
        raise InteractionContractError(
            "NONCLOSING_RATIO_VECTOR",
            f"ratio vector must close exactly to 1, observed {canonical_decimal(total)}",
        )
    if derivation_method is DerivationMethod.PAIR_SCORE_MULTIPLICATION:
        raise InteractionContractError(
            "PAIR_SCORE_SYNTHESIS_PROHIBITED",
            "pair-score multiplication cannot create n-ary evidence authority",
        )
    if evidence_state in {EvidenceState.DESIGNED, EvidenceState.SOURCE_SUPPORTED_DESIGN}:
        if physical_state is not PhysicalState.NOT_TESTED:
            raise InteractionContractError(
                "DESIGNED_CANNOT_BE_OBSERVED",
                "designed interaction must remain NOT_TESTED until linked physical evidence exists",
            )
    if evidence_state is EvidenceState.OBSERVED and physical_state is not PhysicalState.OBSERVED:
        raise InteractionContractError(
            "OBSERVATION_STATE_MISMATCH",
            "observed evidence requires an observed physical state",
        )
    if derivation_method is DerivationMethod.EXACT_FORMULA_PARTS:
        if source_formula_hash is None or len(source_formula_hash) != 64:
            raise InteractionContractError(
                "MISSING_SOURCE_FORMULA_HASH",
                "exact-formula-parts derivation requires a source formula SHA-256",
            )

    payload = {
        "record_id": record_id,
        "participants": [
            {
                "participant_id": item.participant_id,
                "role": item.role,
                "member": item.member,
                "ratio": canonical_decimal(item.ratio),
            }
            for item in members
        ],
        "matrix": matrix,
        "phase": phase,
        "context": context,
        "evidence_state": evidence_state.value,
        "physical_state": physical_state.value,
        "derivation_method": derivation_method.value,
        "source_formula_hash": source_formula_hash,
        "authority": authority,
    }
    return NaryInteraction(
        record_id=record_id,
        participants=members,
        matrix=matrix,
        phase=phase,
        context=context,
        evidence_state=evidence_state,
        physical_state=physical_state,
        derivation_method=derivation_method,
        source_formula_hash=source_formula_hash,
        authority=authority,
        record_hash=sha256_payload(payload, domain="PERFUME_CHEM_NARY_INTERACTION_V20"),
    )
