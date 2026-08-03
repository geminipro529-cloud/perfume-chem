"""Fail-closed evidence boundary for the reported historical search."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from .contracts import C10ContractError, canonical_sha256, is_sha256


class HistoricalRegressionStatus(str, Enum):
    REPORTED_UNVERIFIED = "REPORTED_UNVERIFIED"
    BLOCKED_MISSING_ARTIFACTS = "BLOCKED_MISSING_ARTIFACTS"
    MISMATCH = "MISMATCH"
    RECEIPT_MATCHES_REPORTED_RESULT = "RECEIPT_MATCHES_REPORTED_RESULT"


@dataclass(frozen=True, slots=True)
class HistoricalSearchClaim:
    fragrance_family: str
    approximate_candidate_count: int
    guardrail_count: int
    dna_threshold: float
    reported_guardrails_passed: int
    reported_winner_dna_score: float
    status: HistoricalRegressionStatus


HISTORICAL_SEARCH_CLAIM = HistoricalSearchClaim(
    fragrance_family="La Nuit de L'Homme",
    approximate_candidate_count=30_000,
    guardrail_count=35,
    dna_threshold=97.5,
    reported_guardrails_passed=35,
    reported_winner_dna_score=97.76,
    status=HistoricalRegressionStatus.REPORTED_UNVERIFIED,
)


def _hash(value: str, name: str) -> str:
    normalized = str(value).strip().casefold()
    if not is_sha256(normalized):
        raise C10ContractError(f"{name} must be a lowercase SHA-256 digest")
    return normalized


@dataclass(frozen=True, slots=True)
class HistoricalRegressionReceipt:
    implementation_sha256: str
    input_sha256: str
    result_sha256: str
    verifier_sha256: str
    replay_command: tuple[str, ...]
    replay_exit_code: int
    candidate_count: int
    guardrail_count: int
    guardrails_passed: int
    dna_threshold: float
    winner_dna_score: float
    fragrance_family: str

    def __post_init__(self) -> None:
        for field_name in (
            "implementation_sha256",
            "input_sha256",
            "result_sha256",
            "verifier_sha256",
        ):
            object.__setattr__(self, field_name, _hash(getattr(self, field_name), field_name))
        command = tuple(str(item).strip() for item in self.replay_command)
        if not command or any(not item for item in command):
            raise C10ContractError("replay_command must contain nonempty arguments")
        candidate_count = int(self.candidate_count)
        guardrail_count = int(self.guardrail_count)
        guardrails_passed = int(self.guardrails_passed)
        if candidate_count <= 0 or guardrail_count <= 0 or guardrails_passed < 0:
            raise C10ContractError("historical counts must be positive and coherent")
        if guardrails_passed > guardrail_count:
            raise C10ContractError("guardrails_passed must not exceed guardrail_count")
        threshold = float(self.dna_threshold)
        score = float(self.winner_dna_score)
        if not isfinite(threshold) or not isfinite(score):
            raise C10ContractError("historical DNA values must be finite")
        family = str(self.fragrance_family).strip()
        if not family:
            raise C10ContractError("fragrance_family must not be empty")
        object.__setattr__(self, "replay_command", command)
        object.__setattr__(self, "replay_exit_code", int(self.replay_exit_code))
        object.__setattr__(self, "candidate_count", candidate_count)
        object.__setattr__(self, "guardrail_count", guardrail_count)
        object.__setattr__(self, "guardrails_passed", guardrails_passed)
        object.__setattr__(self, "dna_threshold", threshold)
        object.__setattr__(self, "winner_dna_score", score)
        object.__setattr__(self, "fragrance_family", family)

    @property
    def content_sha256(self) -> str:
        return canonical_sha256(self)


@dataclass(frozen=True, slots=True)
class HistoricalRegressionAssessment:
    status: HistoricalRegressionStatus
    canonical: bool
    reason_codes: tuple[str, ...]
    receipt_sha256: str | None


def assess_historical_regression(
    receipt: HistoricalRegressionReceipt | None,
) -> HistoricalRegressionAssessment:
    """Assess a receipt without pretending it replaces C11's artifact replay."""

    if receipt is None:
        return HistoricalRegressionAssessment(
            status=HistoricalRegressionStatus.BLOCKED_MISSING_ARTIFACTS,
            canonical=False,
            reason_codes=("MISSING_REPRODUCIBLE_ARTIFACT_BUNDLE",),
            receipt_sha256=None,
        )
    if not isinstance(receipt, HistoricalRegressionReceipt):
        raise C10ContractError("receipt must be HistoricalRegressionReceipt or None")

    claim = HISTORICAL_SEARCH_CLAIM
    reasons: list[str] = []
    if receipt.replay_exit_code != 0:
        reasons.append("REPLAY_EXIT_NONZERO")
    if receipt.candidate_count != claim.approximate_candidate_count:
        reasons.append("CANDIDATE_COUNT_MISMATCH")
    if receipt.guardrail_count != claim.guardrail_count:
        reasons.append("GUARDRAIL_COUNT_MISMATCH")
    if receipt.guardrails_passed != claim.reported_guardrails_passed:
        reasons.append("PASSED_GUARDRAIL_COUNT_MISMATCH")
    if receipt.dna_threshold != claim.dna_threshold:
        reasons.append("DNA_THRESHOLD_MISMATCH")
    if receipt.winner_dna_score != claim.reported_winner_dna_score:
        reasons.append("WINNER_DNA_SCORE_MISMATCH")
    if receipt.fragrance_family.casefold() != claim.fragrance_family.casefold():
        reasons.append("FRAGRANCE_FAMILY_MISMATCH")
    if reasons:
        return HistoricalRegressionAssessment(
            status=HistoricalRegressionStatus.MISMATCH,
            canonical=False,
            reason_codes=tuple(reasons),
            receipt_sha256=receipt.content_sha256,
        )
    return HistoricalRegressionAssessment(
        status=HistoricalRegressionStatus.RECEIPT_MATCHES_REPORTED_RESULT,
        canonical=False,
        reason_codes=("C11_INDEPENDENT_REPLAY_REQUIRED",),
        receipt_sha256=receipt.content_sha256,
    )


__all__ = [
    "HISTORICAL_SEARCH_CLAIM",
    "HistoricalRegressionAssessment",
    "HistoricalRegressionReceipt",
    "HistoricalRegressionStatus",
    "HistoricalSearchClaim",
    "assess_historical_regression",
]
