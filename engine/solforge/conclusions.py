"""Monotonic, evidence-gated scientific conclusions for SolForge programs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from engine.evidence_contracts import canonical_json_bytes, sha256_hex

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

CONCLUSION_AUTHORITY_FLAGS = {
    "formula": False,
    "hedonic": False,
    "physical": False,
    "release": False,
    "safety": False,
    "sensory": False,
}


class ConclusionLevel(str, Enum):
    RESEARCH_MAPPED = "RESEARCH_MAPPED"
    HYPOTHESIS_OPERATIONALIZED = "HYPOTHESIS_OPERATIONALIZED"
    PROTOCOL_VALIDATED = "PROTOCOL_VALIDATED"
    OBSERVED_EFFECT = "OBSERVED_EFFECT"
    REPLICATED_EXACT_SCOPE = "REPLICATED_EXACT_SCOPE"
    HEDONIC_PREDICTIVE_VALIDATED = "HEDONIC_PREDICTIVE_VALIDATED"
    GENERALIZATION_TESTED = "GENERALIZATION_TESTED"


class ConclusionDisposition(str, Enum):
    ADVANCE = "ADVANCE"
    HOLD = "HOLD"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    DIAGNOSTIC_ONLY = "DIAGNOSTIC_ONLY"
    PROVENANCE_TOMBSTONE = "PROVENANCE_TOMBSTONE"


_LEVELS = tuple(ConclusionLevel)
_PHYSICAL_LEVEL = _LEVELS.index(ConclusionLevel.OBSERVED_EFFECT)
_HEDONIC_LEVEL = _LEVELS.index(ConclusionLevel.HEDONIC_PREDICTIVE_VALIDATED)


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonblank text")
    return " ".join(value.split())


def _texts(
    value: object, name: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or (not value and not allow_empty):
        qualifier = "a sequence" if allow_empty else "a nonempty sequence"
        raise ValueError(f"{name} must be {qualifier}")
    return tuple(_text(item, name) for item in value)


def _hashes(
    value: object, name: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    values = _texts(value, name, allow_empty=allow_empty)
    if any(_SHA_RE.fullmatch(item) is None for item in values):
        raise ValueError(f"{name} values must be lower-case SHA-256 digests")
    if len(values) != len(set(values)):
        raise ValueError(f"{name} contains duplicate hashes")
    return values


@dataclass(frozen=True, slots=True)
class ScientificConclusionReceiptV1:
    SCHEMA_VERSION: ClassVar[str] = "scientific_conclusion_receipt_v1"
    conclusion_id: str
    claim: str
    exact_scope: str
    level: ConclusionLevel
    disposition: ConclusionDisposition
    criterion: str
    direct_evidence_sha256: tuple[str, ...]
    contrary_evidence_sha256: tuple[str, ...]
    contrary_evidence_reviewed: bool
    evidence_kinds: tuple[str, ...]
    physical_evidence_valid: bool
    heldout_baseline_passed: bool
    generalization_scope_declared: bool
    inference: str
    uncertainty: str
    failed_tests: tuple[str, ...]
    permitted_use: tuple[str, ...]
    forbidden_extrapolations: tuple[str, ...]
    prior_receipt_sha256: str | None

    def __post_init__(self) -> None:
        for name in (
            "conclusion_id",
            "claim",
            "exact_scope",
            "criterion",
            "inference",
            "uncertainty",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "level", ConclusionLevel(self.level))
        object.__setattr__(self, "disposition", ConclusionDisposition(self.disposition))
        criterion = self.criterion.upper()
        if criterion not in {
            "TARGET_FIDELITY",
            "DEPTH",
            "RICHNESS",
            "LIKING",
            "SOFTWARE_DECISION_YIELD",
        }:
            raise ValueError("criterion is invalid")
        object.__setattr__(self, "criterion", criterion)
        object.__setattr__(
            self,
            "direct_evidence_sha256",
            _hashes(self.direct_evidence_sha256, "direct_evidence_sha256"),
        )
        object.__setattr__(
            self,
            "contrary_evidence_sha256",
            _hashes(
                self.contrary_evidence_sha256,
                "contrary_evidence_sha256",
                allow_empty=True,
            ),
        )
        object.__setattr__(
            self, "evidence_kinds", _texts(self.evidence_kinds, "evidence_kinds")
        )
        object.__setattr__(
            self, "failed_tests", _texts(self.failed_tests, "failed_tests", allow_empty=True)
        )
        object.__setattr__(
            self, "permitted_use", _texts(self.permitted_use, "permitted_use")
        )
        object.__setattr__(
            self,
            "forbidden_extrapolations",
            _texts(self.forbidden_extrapolations, "forbidden_extrapolations"),
        )
        for name in (
            "contrary_evidence_reviewed",
            "physical_evidence_valid",
            "heldout_baseline_passed",
            "generalization_scope_declared",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be boolean")
        if self.prior_receipt_sha256 is not None and _SHA_RE.fullmatch(
            self.prior_receipt_sha256
        ) is None:
            raise ValueError("prior_receipt_sha256 must be a lower-case SHA-256 digest")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "conclusion_id": self.conclusion_id,
            "claim": self.claim,
            "exact_scope": self.exact_scope,
            "level": self.level.value,
            "disposition": self.disposition.value,
            "criterion": self.criterion,
            "direct_evidence_sha256": list(self.direct_evidence_sha256),
            "contrary_evidence_sha256": list(self.contrary_evidence_sha256),
            "contrary_evidence_reviewed": self.contrary_evidence_reviewed,
            "evidence_kinds": list(self.evidence_kinds),
            "physical_evidence_valid": self.physical_evidence_valid,
            "heldout_baseline_passed": self.heldout_baseline_passed,
            "generalization_scope_declared": self.generalization_scope_declared,
            "inference": self.inference,
            "uncertainty": self.uncertainty,
            "failed_tests": list(self.failed_tests),
            "permitted_use": list(self.permitted_use),
            "forbidden_extrapolations": list(self.forbidden_extrapolations),
            "prior_receipt_sha256": self.prior_receipt_sha256,
            "authority_flags": dict(CONCLUSION_AUTHORITY_FLAGS),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())

    @classmethod
    def from_dict(cls, payload: object) -> ScientificConclusionReceiptV1:
        if not isinstance(payload, dict):
            raise TypeError("conclusion payload must be an object")
        fields = {
            "conclusion_id",
            "claim",
            "exact_scope",
            "level",
            "disposition",
            "criterion",
            "direct_evidence_sha256",
            "contrary_evidence_sha256",
            "contrary_evidence_reviewed",
            "evidence_kinds",
            "physical_evidence_valid",
            "heldout_baseline_passed",
            "generalization_scope_declared",
            "inference",
            "uncertainty",
            "failed_tests",
            "permitted_use",
            "forbidden_extrapolations",
            "prior_receipt_sha256",
        }
        if set(payload) != fields | {"schema_version", "authority_flags"}:
            raise ValueError("conclusion fields do not match the closed schema")
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError("schema_version is invalid")
        if payload["authority_flags"] != CONCLUSION_AUTHORITY_FLAGS:
            raise ValueError("authority_flags must be the exact all-false mapping")
        values = {name: payload[name] for name in fields}
        for name in (
            "direct_evidence_sha256",
            "contrary_evidence_sha256",
            "evidence_kinds",
            "failed_tests",
            "permitted_use",
            "forbidden_extrapolations",
        ):
            values[name] = tuple(values[name])
        return cls(**values)


def evaluate_conclusion_transition(
    prior: ScientificConclusionReceiptV1 | None,
    proposed: ScientificConclusionReceiptV1,
) -> tuple[str, ...]:
    """Reject skipped, unbound, unscoped, or nonphysical claim promotion."""

    if not isinstance(proposed, ScientificConclusionReceiptV1):
        raise TypeError("proposed must be a ScientificConclusionReceiptV1")
    issues: list[str] = []
    proposed_index = _LEVELS.index(proposed.level)
    advancing = proposed.disposition is ConclusionDisposition.ADVANCE
    if prior is None:
        if proposed.level is not ConclusionLevel.RESEARCH_MAPPED:
            issues.append("first conclusion must start at RESEARCH_MAPPED")
        if proposed.prior_receipt_sha256 is not None:
            issues.append("first conclusion cannot name a parent receipt")
    else:
        if proposed.prior_receipt_sha256 != prior.record_sha256:
            issues.append("parent receipt hash mismatch")
        prior_index = _LEVELS.index(prior.level)
        if advancing and proposed_index != prior_index + 1:
            issues.append("conclusion levels cannot skip or repeat during advancement")
        if not advancing and proposed_index > prior_index:
            issues.append("negative disposition cannot advance a conclusion level")
        if (
            proposed.level is not ConclusionLevel.GENERALIZATION_TESTED
            and proposed.exact_scope != prior.exact_scope
        ):
            issues.append("exact scope changed before a generalization test")
    if not proposed.contrary_evidence_reviewed:
        issues.append("contrary evidence review is required")
    if advancing and proposed.failed_tests:
        issues.append("an advancing conclusion cannot retain failed required tests")
    if proposed_index >= _PHYSICAL_LEVEL and (
        not proposed.physical_evidence_valid
        or "PHYSICAL_OBSERVATION" not in proposed.evidence_kinds
    ):
        issues.append("observed and later levels require valid physical evidence")
    if proposed_index >= _HEDONIC_LEVEL:
        if proposed.criterion != "LIKING":
            issues.append("hedonic predictive validation requires the LIKING criterion")
        if not proposed.heldout_baseline_passed:
            issues.append("hedonic predictive validation requires a held-out baseline pass")
    if proposed.level is ConclusionLevel.GENERALIZATION_TESTED and (
        not proposed.generalization_scope_declared
        or "GENERALIZATION_TEST" not in proposed.evidence_kinds
    ):
        issues.append("generalization requires a declared scope and direct generalization test")
    return tuple(issues)


def next_required_evidence(receipt: ScientificConclusionReceiptV1) -> str:
    """Describe the next lawful evidence step without implying promotion."""

    return {
        ConclusionLevel.RESEARCH_MAPPED: "Operationalize one measurable hypothesis with controls and failure criteria.",
        ConclusionLevel.HYPOTHESIS_OPERATIONALIZED: "Validate a preregistered exact-scope protocol without outcome editing.",
        ConclusionLevel.PROTOCOL_VALIDATED: "Collect prospective physical observations under the frozen protocol.",
        ConclusionLevel.OBSERVED_EFFECT: "Replicate the physical effect at the identical declared scope.",
        ConclusionLevel.REPLICATED_EXACT_SCOPE: "For LIKING only, test held-out predictive performance above baseline.",
        ConclusionLevel.HEDONIC_PREDICTIVE_VALIDATED: "Run an explicit prospective generalization test at the new scope.",
        ConclusionLevel.GENERALIZATION_TESTED: "No automatic next level; preserve the tested scope and limitations.",
    }[receipt.level]


__all__ = [
    "CONCLUSION_AUTHORITY_FLAGS",
    "ConclusionDisposition",
    "ConclusionLevel",
    "ScientificConclusionReceiptV1",
    "evaluate_conclusion_transition",
    "next_required_evidence",
]
