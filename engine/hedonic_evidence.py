"""Exact-scope evidence gate for observed perfume liking."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.preference import (
    PairwisePreference,
    PreferenceFitRequest,
    PreferenceFitResult,
    PreferenceFitStatus,
    fit_preference_model,
)


class HedonicScope(str, Enum):
    """Population to which a liking comparison is allowed to apply."""

    OWNER = "OWNER"
    TRAINED_PANEL = "TRAINED_PANEL"
    CONSUMER_POPULATION = "CONSUMER_POPULATION"


class HedonicEvidenceState(str, Enum):
    """Evidence posture for an exact-scope liking result."""

    NOT_TESTED = "NOT_TESTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    DIAGNOSTIC = "DIAGNOSTIC"
    VALIDATED_EXACT_SCOPE = "VALIDATED_EXACT_SCOPE"
    FAILED_HELDOUT_BASELINE = "FAILED_HELDOUT_BASELINE"
    INVALID_OR_CONFOUNDED = "INVALID_OR_CONFOUNDED"


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _sha256(value: object, field_name: str) -> str:
    normalized = _required_text(value, field_name).lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{field_name} must be a SHA-256 hex digest")
    return normalized


def _unique_text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise TypeError(f"{field_name} must be a sequence of text values")
    normalized = tuple(_required_text(value, field_name) for value in values)  # type: ignore[union-attr]
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return normalized


def _comparison_payload(comparison: PairwisePreference) -> dict[str, Any]:
    return comparison.as_dict()


def _fit_request_payload(request: PreferenceFitRequest) -> dict[str, Any]:
    return {
        "training": [_comparison_payload(value) for value in request.training],
        "heldout": [_comparison_payload(value) for value in request.heldout],
        "minimum_comparisons": request.minimum_comparisons,
        "minimum_heldout_comparisons": request.minimum_heldout_comparisons,
        "declared_baseline_accuracy": request.declared_baseline_accuracy,
        "regularization": request.regularization,
        "learning_rate": request.learning_rate,
        "maximum_iterations": request.maximum_iterations,
        "criterion_id": request.criterion_id,
        "bootstrap_replicates": request.bootstrap_replicates,
        "bootstrap_seed": request.bootstrap_seed,
        "require_scoped_validation": request.require_scoped_validation,
    }


def _fit_result_payload(result: PreferenceFitResult) -> dict[str, Any]:
    return {
        "status": result.status.value,
        "validated": result.validated,
        "utilities": result.utilities,
        "comparison_count": result.comparison_count,
        "connected": result.connected,
        "regularization": result.regularization,
        "heldout_accuracy": result.heldout_accuracy,
        "baseline_accuracy": result.baseline_accuracy,
        "gate_failures": result.gate_failures,
        "validation_notes": result.validation_notes,
        "criterion_id": result.criterion_id,
        "utility_intervals": result.utility_intervals,
        "tie_rate": result.tie_rate,
        "assessor_heterogeneity": result.assessor_heterogeneity,
        "order_effect": result.order_effect,
        "next_comparison": result.next_comparison,
        "bootstrap_replicates": result.bootstrap_replicates,
        "bootstrap_seed": result.bootstrap_seed,
        "bootstrap_method": result.bootstrap_method,
        "evidence": result.evidence.as_dict(),
    }


@dataclass(frozen=True, slots=True)
class PreferenceFitEvidenceReceiptV1:
    """Hash-bound fit, observations, repeat map, and exact sensory scope."""

    criterion_id: str
    scope: HedonicScope
    formula_build_sha256: str
    sample_sha256: tuple[str, ...]
    protocol_sha256: str
    assessor_ids: tuple[str, ...]
    repeat_ids: tuple[str, ...]
    comparison_repeat_ids: tuple[tuple[str, str], ...]
    time_seconds: float
    schedule_sha256: str
    fit_request: PreferenceFitRequest
    fit_result: PreferenceFitResult
    training_comparisons_sha256: str = field(init=False)
    heldout_comparisons_sha256: str = field(init=False)
    fit_request_sha256: str = field(init=False)
    fit_result_sha256: str = field(init=False)
    model_configuration_sha256: str = field(init=False)
    comparison_repeats_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "criterion_id", _required_text(self.criterion_id, "criterion_id")
        )
        object.__setattr__(self, "scope", HedonicScope(self.scope))
        for name in (
            "formula_build_sha256",
            "protocol_sha256",
            "schedule_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        samples = tuple(_sha256(value, "sample_sha256") for value in self.sample_sha256)
        if not samples or len(samples) != len(set(samples)):
            raise ValueError("sample_sha256 must contain unique sample hashes")
        object.__setattr__(self, "sample_sha256", samples)
        object.__setattr__(
            self,
            "assessor_ids",
            _unique_text_tuple(self.assessor_ids, "assessor_ids"),
        )
        object.__setattr__(
            self, "repeat_ids", _unique_text_tuple(self.repeat_ids, "repeat_ids")
        )
        if isinstance(self.time_seconds, bool) or not isinstance(
            self.time_seconds, (int, float)
        ):
            raise TypeError("time_seconds must be a real number")
        time_seconds = float(self.time_seconds)
        if not isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("time_seconds must be finite and nonnegative")
        object.__setattr__(self, "time_seconds", time_seconds)

        repeats = tuple(
            sorted(
                (
                    _required_text(comparison_id, "comparison_repeat_ids key"),
                    _required_text(repeat_id, "comparison_repeat_ids value"),
                )
                for comparison_id, repeat_id in self.comparison_repeat_ids
            )
        )
        if len(repeats) != len({comparison_id for comparison_id, _ in repeats}):
            raise ValueError("comparison_repeat_ids must have unique comparison IDs")
        object.__setattr__(self, "comparison_repeat_ids", repeats)

        comparisons = self.fit_request.training + self.fit_request.heldout
        comparison_ids = tuple(comparison.comparison_id for comparison in comparisons)
        if any(value is None for value in comparison_ids) or set(comparison_ids) != {
            comparison_id for comparison_id, _ in repeats
        }:
            raise ValueError(
                "comparison_repeat_ids must cover every fit comparison exactly"
            )
        if any(repeat_id not in self.repeat_ids for _, repeat_id in repeats):
            raise ValueError("comparison_repeat_ids contains an undeclared repeat")
        observed_assessors = {
            comparison.assessor_id
            for comparison in comparisons
            if comparison.assessor_id is not None
        }
        if observed_assessors != set(self.assessor_ids):
            raise ValueError("assessor_ids must exactly match fit comparisons")
        if any(
            comparison.criterion_id != self.criterion_id for comparison in comparisons
        ) or self.fit_request.criterion_id != self.criterion_id:
            raise ValueError("criterion_id must exactly match the fit request")
        if any(
            comparison.time_seconds != self.time_seconds for comparison in comparisons
        ):
            raise ValueError("time_seconds must exactly match fit comparisons")

        expected = fit_preference_model(self.fit_request)
        expected_bytes = canonical_json_bytes(_fit_result_payload(expected))
        result_bytes = canonical_json_bytes(_fit_result_payload(self.fit_result))
        if expected_bytes != result_bytes:
            raise ValueError("fit result does not match the bound fit request")

        request_payload = _fit_request_payload(self.fit_request)
        model_payload = {
            key: value
            for key, value in request_payload.items()
            if key not in {"training", "heldout"}
        }
        derived = {
            "training_comparisons_sha256": sha256_hex(
                canonical_json_bytes(request_payload["training"])
            ),
            "heldout_comparisons_sha256": sha256_hex(
                canonical_json_bytes(request_payload["heldout"])
            ),
            "fit_request_sha256": sha256_hex(canonical_json_bytes(request_payload)),
            "fit_result_sha256": sha256_hex(result_bytes),
            "model_configuration_sha256": sha256_hex(
                canonical_json_bytes(model_payload)
            ),
            "comparison_repeats_sha256": sha256_hex(canonical_json_bytes(repeats)),
        }
        for name, value in derived.items():
            object.__setattr__(self, name, value)

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "preference_fit_evidence_v1",
            "criterion_id": self.criterion_id,
            "scope": self.scope.value,
            "formula_build_sha256": self.formula_build_sha256,
            "sample_sha256": self.sample_sha256,
            "protocol_sha256": self.protocol_sha256,
            "assessor_ids": self.assessor_ids,
            "repeat_ids": self.repeat_ids,
            "comparison_repeat_ids": self.comparison_repeat_ids,
            "time_seconds": self.time_seconds,
            "schedule_sha256": self.schedule_sha256,
            "training_comparisons_sha256": self.training_comparisons_sha256,
            "heldout_comparisons_sha256": self.heldout_comparisons_sha256,
            "fit_request_sha256": self.fit_request_sha256,
            "fit_result_sha256": self.fit_result_sha256,
            "model_configuration_sha256": self.model_configuration_sha256,
            "comparison_repeats_sha256": self.comparison_repeats_sha256,
            "fit_request": _fit_request_payload(self.fit_request),
            "fit_result": _fit_result_payload(self.fit_result),
        }


def bind_preference_fit_evidence(
    fit_request: PreferenceFitRequest,
    fit_result: PreferenceFitResult,
    *,
    scope: HedonicScope,
    formula_build_sha256: str,
    sample_sha256: tuple[str, ...],
    protocol_sha256: str,
    assessor_ids: tuple[str, ...],
    repeat_ids: tuple[str, ...],
    comparison_repeat_ids: Mapping[str, str],
    time_seconds: float,
    schedule_sha256: str,
) -> PreferenceFitEvidenceReceiptV1:
    """Bind a deterministic preference fit to its exact sensory evidence scope."""

    return PreferenceFitEvidenceReceiptV1(
        criterion_id=fit_request.criterion_id or "",
        scope=scope,
        formula_build_sha256=formula_build_sha256,
        sample_sha256=sample_sha256,
        protocol_sha256=protocol_sha256,
        assessor_ids=assessor_ids,
        repeat_ids=repeat_ids,
        comparison_repeat_ids=tuple(comparison_repeat_ids.items()),
        time_seconds=time_seconds,
        schedule_sha256=schedule_sha256,
        fit_request=fit_request,
        fit_result=fit_result,
    )


@dataclass(frozen=True, slots=True)
class HedonicEvidenceRequest:
    """Exact scope against which one liking fit may be evaluated."""

    criterion_id: str
    scope: HedonicScope
    formula_build_sha256: str
    sample_sha256: tuple[str, ...]
    protocol_sha256: str
    assessor_ids: tuple[str, ...]
    repeat_ids: tuple[str, ...]
    time_seconds: float
    schedule_sha256: str
    fit_receipt: PreferenceFitEvidenceReceiptV1 | None = None
    safety_event_ids: tuple[str, ...] = ()
    maximum_absolute_order_effect: float = 0.25

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "criterion_id", _required_text(self.criterion_id, "criterion_id")
        )
        object.__setattr__(self, "scope", HedonicScope(self.scope))
        for name in (
            "formula_build_sha256",
            "protocol_sha256",
            "schedule_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        samples = tuple(_sha256(value, "sample_sha256") for value in self.sample_sha256)
        if not samples or len(samples) != len(set(samples)):
            raise ValueError("sample_sha256 must contain unique sample hashes")
        object.__setattr__(self, "sample_sha256", samples)
        object.__setattr__(
            self,
            "assessor_ids",
            _unique_text_tuple(self.assessor_ids, "assessor_ids"),
        )
        object.__setattr__(
            self, "repeat_ids", _unique_text_tuple(self.repeat_ids, "repeat_ids")
        )
        object.__setattr__(
            self,
            "safety_event_ids",
            tuple(
                _required_text(value, "safety_event_ids")
                for value in self.safety_event_ids
            ),
        )
        if isinstance(self.time_seconds, bool) or not isinstance(
            self.time_seconds, (int, float)
        ):
            raise TypeError("time_seconds must be a real number")
        seconds = float(self.time_seconds)
        if not isfinite(seconds) or seconds < 0:
            raise ValueError("time_seconds must be finite and nonnegative")
        object.__setattr__(self, "time_seconds", seconds)
        limit = self.maximum_absolute_order_effect
        if isinstance(limit, bool) or not isinstance(limit, (int, float)):
            raise TypeError("maximum_absolute_order_effect must be a real number")
        limit = float(limit)
        if not isfinite(limit) or not 0 <= limit <= 0.5:
            raise ValueError(
                "maximum_absolute_order_effect must be between zero and 0.5"
            )
        object.__setattr__(self, "maximum_absolute_order_effect", limit)


@dataclass(frozen=True, slots=True)
class HedonicEvidenceResult:
    state: HedonicEvidenceState
    criterion_id: str
    scope: HedonicScope
    formula_build_sha256: str
    fit_receipt_sha256: str | None
    utility_intervals: dict[str, tuple[float, float]]
    tie_rate: float | None
    directional_comparison_count: int
    assessor_heterogeneity: dict[str, float]
    order_effect: float | None
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    universal_preference_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "hedonic_evidence_v2",
            "state": self.state.value,
            "criterion_id": self.criterion_id,
            "scope": self.scope.value,
            "formula_build_sha256": self.formula_build_sha256,
            "fit_receipt_sha256": self.fit_receipt_sha256,
            "utility_intervals": self.utility_intervals,
            "tie_rate": self.tie_rate,
            "directional_comparison_count": self.directional_comparison_count,
            "assessor_heterogeneity": self.assessor_heterogeneity,
            "order_effect": self.order_effect,
            "blockers": self.blockers,
            "limitations": self.limitations,
            "universal_preference_authority": self.universal_preference_authority,
            "release_authority": self.release_authority,
        }


def evaluate_hedonic_evidence(
    request: HedonicEvidenceRequest,
) -> HedonicEvidenceResult:
    """Evaluate one fit without converting formulation features into liking."""

    if request.criterion_id != "LIKING":
        return _result(
            request,
            HedonicEvidenceState.INVALID_OR_CONFOUNDED,
            blockers=("criterion_id must be LIKING for hedonic evidence",),
        )
    receipt = request.fit_receipt
    if receipt is None:
        return _result(
            request,
            HedonicEvidenceState.NOT_TESTED,
            limitations=("No blinded exact-scope liking fit was supplied.",),
        )

    blockers: list[str] = []
    exact_fields = (
        "criterion_id",
        "scope",
        "formula_build_sha256",
        "sample_sha256",
        "protocol_sha256",
        "assessor_ids",
        "repeat_ids",
        "time_seconds",
        "schedule_sha256",
    )
    for field_name in exact_fields:
        if getattr(request, field_name) != getattr(receipt, field_name):
            blockers.append(f"{field_name} does not match the fit receipt")
    if request.safety_event_ids:
        blockers.append("unresolved sensory safety event is present")
    if not receipt.fit_request.require_scoped_validation:
        blockers.append("fit request did not require scoped validation")
    if (
        receipt.fit_result.order_effect is not None
        and abs(receipt.fit_result.order_effect)
        > request.maximum_absolute_order_effect
    ):
        blockers.append("observed order effect exceeds the declared limit")
    if blockers:
        return _result(
            request,
            HedonicEvidenceState.INVALID_OR_CONFOUNDED,
            receipt=receipt,
            blockers=tuple(blockers),
        )

    fit = receipt.fit_result
    if fit.status is PreferenceFitStatus.WITHHELD:
        return _result(
            request,
            HedonicEvidenceState.INSUFFICIENT_EVIDENCE,
            receipt=receipt,
            limitations=fit.gate_failures,
            include_fit=False,
        )
    if any("baseline" in note.lower() for note in fit.validation_notes):
        return _result(
            request,
            HedonicEvidenceState.FAILED_HELDOUT_BASELINE,
            receipt=receipt,
            limitations=fit.validation_notes,
        )
    if fit.status is PreferenceFitStatus.DIAGNOSTIC:
        return _result(
            request,
            HedonicEvidenceState.DIAGNOSTIC,
            receipt=receipt,
            limitations=fit.validation_notes,
        )
    valid = (
        fit.status is PreferenceFitStatus.VALIDATED
        and fit.validated
        and fit.connected
        and fit.criterion_id == "LIKING"
        and fit.heldout_accuracy is not None
        and fit.baseline_accuracy is not None
        and fit.heldout_accuracy > fit.baseline_accuracy
    )
    if not valid:
        return _result(
            request,
            HedonicEvidenceState.INVALID_OR_CONFOUNDED,
            receipt=receipt,
            blockers=("fit validation contract is internally inconsistent",),
        )
    return _result(
        request,
        HedonicEvidenceState.VALIDATED_EXACT_SCOPE,
        receipt=receipt,
        limitations=(
            "Validated only for the bound formula, samples, protocol, assessors, "
            "repeats, timepoint, schedule, and population scope.",
        ),
    )


def _result(
    request: HedonicEvidenceRequest,
    state: HedonicEvidenceState,
    *,
    receipt: PreferenceFitEvidenceReceiptV1 | None = None,
    blockers: tuple[str, ...] = (),
    limitations: tuple[str, ...] = (),
    include_fit: bool = True,
) -> HedonicEvidenceResult:
    fit = receipt.fit_result if receipt is not None and include_fit else None
    return HedonicEvidenceResult(
        state=state,
        criterion_id=request.criterion_id,
        scope=request.scope,
        formula_build_sha256=request.formula_build_sha256,
        fit_receipt_sha256=receipt.record_sha256 if receipt is not None else None,
        utility_intervals=dict(fit.utility_intervals) if fit is not None else {},
        tie_rate=fit.tie_rate if fit is not None else None,
        directional_comparison_count=fit.comparison_count if fit is not None else 0,
        assessor_heterogeneity=(
            dict(fit.assessor_heterogeneity) if fit is not None else {}
        ),
        order_effect=fit.order_effect if fit is not None else None,
        blockers=blockers,
        limitations=limitations,
    )


__all__ = [
    "HedonicEvidenceRequest",
    "HedonicEvidenceResult",
    "HedonicEvidenceState",
    "HedonicScope",
    "PreferenceFitEvidenceReceiptV1",
    "bind_preference_fit_evidence",
    "evaluate_hedonic_evidence",
]
