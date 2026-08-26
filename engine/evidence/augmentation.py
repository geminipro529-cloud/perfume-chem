"""Canonical conditional evidence-augmentation receipts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from engine.evidence_contracts import canonical_json_bytes, sha256_hex

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

AUGMENTATION_AUTHORITY_FALSE = {
    "compounding": False,
    "formula": False,
    "inventory_mutation": False,
    "liking": False,
    "physical_execution": False,
    "publication": False,
    "purchase": False,
    "release": False,
    "runtime": False,
    "safety": False,
    "scientific_claim": False,
    "sensory": False,
}


class EvidenceAugmentationState(str, Enum):
    AUGMENT = "AUGMENT"
    NO_AUGMENTATION = "NO_AUGMENTATION"
    HOLD = "HOLD"


def _text(value: object, field_name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _texts(
    values: object,
    field_name: str,
    *,
    allow_empty: bool = True,
    uppercase: bool = False,
) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{field_name} must be a sequence")
    result = tuple(str(_text(value, field_name)) for value in values)
    if uppercase:
        result = tuple(value.upper() for value in result)
    if not allow_empty and not result:
        raise ValueError(f"{field_name} must be nonempty")
    if len(result) != len(set(result)):
        raise ValueError(f"duplicate {field_name}")
    return result


def _sha(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class DecisionDeltaV1:
    SCHEMA_VERSION: ClassVar[str] = "decision_delta_v1"
    delta_id: str
    decision_effect: str
    observed_facts: tuple[str, ...]
    derived_calculations: tuple[str, ...]
    hypotheses: tuple[str, ...]
    forbidden_inferences: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "delta_id", _text(self.delta_id, "delta_id"))
        object.__setattr__(
            self,
            "decision_effect",
            _text(self.decision_effect, "decision_effect"),
        )
        object.__setattr__(
            self,
            "observed_facts",
            _texts(self.observed_facts, "observed_facts", allow_empty=False),
        )
        object.__setattr__(
            self,
            "derived_calculations",
            _texts(self.derived_calculations, "derived_calculations"),
        )
        object.__setattr__(
            self, "hypotheses", _texts(self.hypotheses, "hypotheses")
        )
        object.__setattr__(
            self,
            "forbidden_inferences",
            _texts(
                self.forbidden_inferences,
                "forbidden_inferences",
                allow_empty=False,
            ),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "delta_id": self.delta_id,
            "decision_effect": self.decision_effect,
            "observed_facts": list(self.observed_facts),
            "derived_calculations": list(self.derived_calculations),
            "hypotheses": list(self.hypotheses),
            "forbidden_inferences": list(self.forbidden_inferences),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def delta_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())

    @classmethod
    def from_dict(cls, payload: object) -> DecisionDeltaV1:
        if not isinstance(payload, dict):
            raise TypeError("delta must be an object")
        fields = {
            "schema_version",
            "delta_id",
            "decision_effect",
            "observed_facts",
            "derived_calculations",
            "hypotheses",
            "forbidden_inferences",
        }
        unknown = set(payload).difference(fields)
        missing = fields.difference(payload)
        if unknown:
            raise ValueError("unknown fields: " + ", ".join(sorted(unknown)))
        if missing:
            raise ValueError("missing fields: " + ", ".join(sorted(missing)))
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {cls.SCHEMA_VERSION}")
        return cls(
            delta_id=payload["delta_id"],
            decision_effect=payload["decision_effect"],
            observed_facts=tuple(payload["observed_facts"]),
            derived_calculations=tuple(payload["derived_calculations"]),
            hypotheses=tuple(payload["hypotheses"]),
            forbidden_inferences=tuple(payload["forbidden_inferences"]),
        )


@dataclass(frozen=True, slots=True)
class EvidenceDeltaReceiptV1:
    SCHEMA_VERSION: ClassVar[str] = "evidence_delta_receipt_v1"
    module_id: str
    exact_scope: str
    state: EvidenceAugmentationState
    input_sha256: str
    evidence_sha256: str
    policy_sha256: str
    source_binding_sha256: tuple[str, ...]
    reason_codes: tuple[str, ...]
    delta: DecisionDeltaV1 | None
    blockers: tuple[str, ...]
    next_action: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "module_id", _text(self.module_id, "module_id"))
        object.__setattr__(self, "exact_scope", _text(self.exact_scope, "exact_scope"))
        object.__setattr__(self, "state", EvidenceAugmentationState(self.state))
        for field_name in ("input_sha256", "evidence_sha256", "policy_sha256"):
            object.__setattr__(
                self, field_name, _sha(getattr(self, field_name), field_name)
            )
        source_hashes = tuple(
            sorted(
                _sha(value, "source_binding_sha256")
                for value in self.source_binding_sha256
            )
        )
        if len(source_hashes) != len(set(source_hashes)):
            raise ValueError("duplicate source_binding_sha256")
        object.__setattr__(self, "source_binding_sha256", source_hashes)
        object.__setattr__(
            self,
            "reason_codes",
            _texts(
                self.reason_codes,
                "reason_codes",
                allow_empty=False,
                uppercase=True,
            ),
        )
        object.__setattr__(
            self, "blockers", _texts(self.blockers, "blockers")
        )
        object.__setattr__(
            self,
            "next_action",
            _text(self.next_action, "next_action", optional=True),
        )
        if self.delta is not None and not isinstance(self.delta, DecisionDeltaV1):
            raise TypeError("delta must be a DecisionDeltaV1 or None")
        if self.state is EvidenceAugmentationState.AUGMENT:
            if self.delta is None:
                raise ValueError("AUGMENT requires one decision delta")
            if not self.source_binding_sha256:
                raise ValueError("AUGMENT requires source bindings")
            if self.blockers:
                raise ValueError("AUGMENT cannot contain blockers")
        elif self.delta is not None:
            raise ValueError("only AUGMENT may contain a decision delta")
        if self.state is EvidenceAugmentationState.NO_AUGMENTATION:
            if self.next_action is not None:
                raise ValueError("NO_AUGMENTATION cannot request an action")
            if self.blockers:
                raise ValueError("NO_AUGMENTATION cannot contain blockers")
        if self.state is EvidenceAugmentationState.HOLD and not self.blockers:
            raise ValueError("HOLD requires blockers")

    @property
    def authority(self) -> dict[str, bool]:
        return dict(AUGMENTATION_AUTHORITY_FALSE)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "module_id": self.module_id,
            "exact_scope": self.exact_scope,
            "state": self.state.value,
            "input_sha256": self.input_sha256,
            "evidence_sha256": self.evidence_sha256,
            "policy_sha256": self.policy_sha256,
            "source_binding_sha256": list(self.source_binding_sha256),
            "reason_codes": list(self.reason_codes),
            "delta": None if self.delta is None else self.delta.as_dict(),
            "blockers": list(self.blockers),
            "next_action": self.next_action,
            "authority": self.authority,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def receipt_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())

    @classmethod
    def from_dict(cls, payload: object) -> EvidenceDeltaReceiptV1:
        if not isinstance(payload, dict):
            raise TypeError("receipt payload must be an object")
        fields = {
            "schema_version",
            "module_id",
            "exact_scope",
            "state",
            "input_sha256",
            "evidence_sha256",
            "policy_sha256",
            "source_binding_sha256",
            "reason_codes",
            "delta",
            "blockers",
            "next_action",
            "authority",
        }
        unknown = set(payload).difference(fields)
        missing = fields.difference(payload)
        if unknown:
            raise ValueError("unknown fields: " + ", ".join(sorted(unknown)))
        if missing:
            raise ValueError("missing fields: " + ", ".join(sorted(missing)))
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {cls.SCHEMA_VERSION}")
        if payload["authority"] != AUGMENTATION_AUTHORITY_FALSE:
            raise ValueError("authority must be the exact all-false mapping")
        delta_payload = payload["delta"]
        if delta_payload is None:
            delta = None
        elif isinstance(delta_payload, dict):
            delta = DecisionDeltaV1.from_dict(delta_payload)
        else:
            raise TypeError("delta must be an object or null")
        return cls(
            module_id=payload["module_id"],
            exact_scope=payload["exact_scope"],
            state=payload["state"],
            input_sha256=payload["input_sha256"],
            evidence_sha256=payload["evidence_sha256"],
            policy_sha256=payload["policy_sha256"],
            source_binding_sha256=tuple(payload["source_binding_sha256"]),
            reason_codes=tuple(payload["reason_codes"]),
            delta=delta,
            blockers=tuple(payload["blockers"]),
            next_action=payload["next_action"],
        )


def no_augmentation_receipt(
    *,
    module_id: str,
    exact_scope: str,
    input_sha256: str,
    evidence_sha256: str,
    policy_sha256: str,
    reasons: tuple[str, ...],
    source_binding_sha256: tuple[str, ...] = (),
) -> EvidenceDeltaReceiptV1:
    return EvidenceDeltaReceiptV1(
        module_id=module_id,
        exact_scope=exact_scope,
        state=EvidenceAugmentationState.NO_AUGMENTATION,
        input_sha256=input_sha256,
        evidence_sha256=evidence_sha256,
        policy_sha256=policy_sha256,
        source_binding_sha256=source_binding_sha256,
        reason_codes=reasons,
        delta=None,
        blockers=(),
        next_action=None,
    )


def hold_receipt(
    *,
    module_id: str,
    exact_scope: str,
    input_sha256: str,
    evidence_sha256: str,
    policy_sha256: str,
    reasons: tuple[str, ...],
    blockers: tuple[str, ...],
    next_action: str | None,
    source_binding_sha256: tuple[str, ...] = (),
) -> EvidenceDeltaReceiptV1:
    return EvidenceDeltaReceiptV1(
        module_id=module_id,
        exact_scope=exact_scope,
        state=EvidenceAugmentationState.HOLD,
        input_sha256=input_sha256,
        evidence_sha256=evidence_sha256,
        policy_sha256=policy_sha256,
        source_binding_sha256=source_binding_sha256,
        reason_codes=reasons,
        delta=None,
        blockers=blockers,
        next_action=next_action,
    )


__all__ = [
    "AUGMENTATION_AUTHORITY_FALSE",
    "DecisionDeltaV1",
    "EvidenceAugmentationState",
    "EvidenceDeltaReceiptV1",
    "hold_receipt",
    "no_augmentation_receipt",
]
