"""Diagnostic model lifecycle, drift, supersession, and retirement contracts.

This layer complements the immutable C3 model-release interface.  It can hold a
release out of computation when its declared scope drifts or its lifecycle is
closed, but it cannot rewrite thresholds, mutate formulas, or grant release
authority.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

from engine.calibration.hashing import stable_json_hash

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class ModelLifecycleState(str, Enum):
    CANDIDATE = "CANDIDATE"
    CALIBRATED = "CALIBRATED"
    ACTIVE = "ACTIVE"
    DRIFT_HOLD = "DRIFT_HOLD"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class ModelDriftState(str, Enum):
    INVALID_SCOPE = "INVALID_SCOPE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    WITHIN_DECLARED_TOLERANCE = "WITHIN_DECLARED_TOLERANCE"
    DRIFT_ALERT = "DRIFT_ALERT"
    LIFECYCLE_CLOSED = "LIFECYCLE_CLOSED"


def _text(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must not be blank")
    return text


def _sha256(value: object, field_name: str) -> str:
    text = _text(value, field_name).lower()
    if _SHA256_RE.fullmatch(text) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def _unique(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name) for value in values)
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return normalized


def _decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class ModelLifecycleCard:
    model_id: str
    version: str
    release_sha256: str
    calibration_scope: str
    calibration_data_ids: tuple[str, ...]
    held_out_data_ids: tuple[str, ...]
    endpoint_ids: tuple[str, ...]
    abstention_rule: str
    drift_tolerance: Decimal
    minimum_n: int
    drift_action: str
    supersession_rule: str
    retirement_rule: str
    evidence_ceiling: str
    claim_scopes: tuple[str, ...]
    known_failure_modes: tuple[str, ...]
    lifecycle_state: ModelLifecycleState = ModelLifecycleState.CANDIDATE
    superseded_by_release_sha256: str | None = None
    retirement_reason: str | None = None
    automatic_formula_mutation: bool = field(default=False, init=False)
    threshold_rewrite_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", _text(self.model_id, "model_id"))
        object.__setattr__(self, "version", _text(self.version, "version"))
        object.__setattr__(
            self, "release_sha256", _sha256(self.release_sha256, "release_sha256")
        )
        object.__setattr__(
            self,
            "calibration_scope",
            _text(self.calibration_scope, "calibration_scope"),
        )
        calibration = _unique(self.calibration_data_ids, "calibration_data_ids")
        held_out = _unique(self.held_out_data_ids, "held_out_data_ids")
        overlap = sorted(set(calibration) & set(held_out))
        if overlap:
            raise ValueError(
                "calibration and held-out data IDs overlap: " + ", ".join(overlap)
            )
        object.__setattr__(self, "calibration_data_ids", calibration)
        object.__setattr__(self, "held_out_data_ids", held_out)
        object.__setattr__(self, "endpoint_ids", _unique(self.endpoint_ids, "endpoint_ids"))
        object.__setattr__(self, "claim_scopes", _unique(self.claim_scopes, "claim_scopes"))
        object.__setattr__(
            self,
            "known_failure_modes",
            _unique(self.known_failure_modes, "known_failure_modes"),
        )
        for field_name in (
            "abstention_rule",
            "drift_action",
            "supersession_rule",
            "retirement_rule",
            "evidence_ceiling",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        tolerance = _decimal(self.drift_tolerance, "drift_tolerance")
        if tolerance < 0:
            raise ValueError("drift_tolerance must be non-negative")
        object.__setattr__(self, "drift_tolerance", tolerance)
        if isinstance(self.minimum_n, bool) or not isinstance(self.minimum_n, int):
            raise TypeError("minimum_n must be an integer")
        if self.minimum_n < 2:
            raise ValueError("minimum_n must be at least two")
        if not isinstance(self.lifecycle_state, ModelLifecycleState):
            raise TypeError("lifecycle_state must be a ModelLifecycleState")
        if self.superseded_by_release_sha256 is not None:
            object.__setattr__(
                self,
                "superseded_by_release_sha256",
                _sha256(
                    self.superseded_by_release_sha256,
                    "superseded_by_release_sha256",
                ),
            )
        if (
            self.lifecycle_state is ModelLifecycleState.SUPERSEDED
            and self.superseded_by_release_sha256 is None
        ):
            raise ValueError("SUPERSEDED requires superseded_by_release_sha256")
        if self.lifecycle_state is ModelLifecycleState.RETIRED:
            if self.retirement_reason is None:
                raise ValueError("RETIRED requires retirement_reason")
            object.__setattr__(
                self,
                "retirement_reason",
                _text(self.retirement_reason, "retirement_reason"),
            )
        elif self.retirement_reason is not None:
            object.__setattr__(
                self,
                "retirement_reason",
                _text(self.retirement_reason, "retirement_reason"),
            )

    @property
    def card_sha256(self) -> str:
        return stable_json_hash(self.as_dict(include_hash=False))

    def as_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "model_id": self.model_id,
            "version": self.version,
            "release_sha256": self.release_sha256,
            "calibration_scope": self.calibration_scope,
            "calibration_data_ids": list(self.calibration_data_ids),
            "held_out_data_ids": list(self.held_out_data_ids),
            "endpoint_ids": list(self.endpoint_ids),
            "abstention_rule": self.abstention_rule,
            "drift_tolerance": str(self.drift_tolerance),
            "minimum_n": self.minimum_n,
            "drift_action": self.drift_action,
            "supersession_rule": self.supersession_rule,
            "retirement_rule": self.retirement_rule,
            "evidence_ceiling": self.evidence_ceiling,
            "claim_scopes": list(self.claim_scopes),
            "known_failure_modes": list(self.known_failure_modes),
            "lifecycle_state": self.lifecycle_state.value,
            "superseded_by_release_sha256": self.superseded_by_release_sha256,
            "retirement_reason": self.retirement_reason,
            "automatic_formula_mutation": self.automatic_formula_mutation,
            "threshold_rewrite_authorized": self.threshold_rewrite_authorized,
            "release_authority": self.release_authority,
        }
        if include_hash:
            payload["card_sha256"] = stable_json_hash(payload)
        return payload


@dataclass(frozen=True, slots=True)
class ModelDriftObservation:
    observation_id: str
    observed: Decimal
    predicted: Decimal
    evidence_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "observation_id", _text(self.observation_id, "observation_id")
        )
        object.__setattr__(self, "observed", _decimal(self.observed, "observed"))
        object.__setattr__(self, "predicted", _decimal(self.predicted, "predicted"))
        object.__setattr__(
            self,
            "evidence_sha256",
            _sha256(self.evidence_sha256, "evidence_sha256"),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "observation_id": self.observation_id,
            "observed": str(self.observed),
            "predicted": str(self.predicted),
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class ModelDriftAssessment:
    state: ModelDriftState
    card_sha256: str
    calibration_scope: str
    observation_count: int
    mae: Decimal | None
    rmse: Decimal | None
    bias: Decimal | None
    max_abs_error: Decimal | None
    tolerance: Decimal
    blockers: tuple[str, ...]
    computation_allowed: bool
    automatic_threshold_rewrite: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "state": self.state.value,
            "card_sha256": self.card_sha256,
            "calibration_scope": self.calibration_scope,
            "observation_count": self.observation_count,
            "mae": str(self.mae) if self.mae is not None else None,
            "rmse": str(self.rmse) if self.rmse is not None else None,
            "bias": str(self.bias) if self.bias is not None else None,
            "max_abs_error": (
                str(self.max_abs_error) if self.max_abs_error is not None else None
            ),
            "tolerance": str(self.tolerance),
            "blockers": list(self.blockers),
            "computation_allowed": self.computation_allowed,
            "automatic_threshold_rewrite": self.automatic_threshold_rewrite,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "release_authority": self.release_authority,
        }
        payload["result_sha256"] = stable_json_hash(payload)
        return payload


def assess_model_drift(
    card: ModelLifecycleCard,
    observations: Sequence[ModelDriftObservation],
    *,
    calibration_scope: str,
) -> ModelDriftAssessment:
    """Assess current drift without rewriting a release or its thresholds."""

    if not isinstance(card, ModelLifecycleCard):
        raise TypeError("card must be a ModelLifecycleCard")
    if isinstance(observations, (str, bytes)) or not isinstance(observations, Sequence):
        raise TypeError("observations must be a sequence")
    if any(not isinstance(item, ModelDriftObservation) for item in observations):
        raise TypeError("observations must contain ModelDriftObservation values")
    ids = tuple(item.observation_id for item in observations)
    if len(ids) != len(set(ids)):
        raise ValueError("observation IDs must be unique")
    scope = _text(calibration_scope, "calibration_scope")
    blockers: list[str] = []
    errors = [item.observed - item.predicted for item in observations]
    mae: Decimal | None
    rmse: Decimal | None
    bias: Decimal | None
    max_abs: Decimal | None
    if errors:
        count = Decimal(len(errors))
        mae = sum(abs(value) for value in errors) / count
        bias = sum(errors) / count
        mean_square = sum(value * value for value in errors) / count
        rmse = mean_square.sqrt()
        max_abs = max(abs(value) for value in errors)
    else:
        mae = rmse = bias = max_abs = None

    if card.lifecycle_state in {
        ModelLifecycleState.SUPERSEDED,
        ModelLifecycleState.RETIRED,
    }:
        state = ModelDriftState.LIFECYCLE_CLOSED
        blockers.append(f"model lifecycle is {card.lifecycle_state.value}")
    elif scope != card.calibration_scope:
        state = ModelDriftState.INVALID_SCOPE
        blockers.append("drift scope does not match the model calibration scope")
    elif len(observations) < card.minimum_n:
        state = ModelDriftState.INSUFFICIENT_DATA
        blockers.append(
            f"at least {card.minimum_n} observations are required, got {len(observations)}"
        )
    elif mae is not None and mae > card.drift_tolerance:
        state = ModelDriftState.DRIFT_ALERT
        blockers.append(card.drift_action)
    else:
        state = ModelDriftState.WITHIN_DECLARED_TOLERANCE

    computation_allowed = (
        state is ModelDriftState.WITHIN_DECLARED_TOLERANCE
        and card.lifecycle_state is ModelLifecycleState.ACTIVE
    )
    if state is ModelDriftState.WITHIN_DECLARED_TOLERANCE and not computation_allowed:
        blockers.append(
            f"model lifecycle must be ACTIVE, got {card.lifecycle_state.value}"
        )
    return ModelDriftAssessment(
        state=state,
        card_sha256=card.card_sha256,
        calibration_scope=scope,
        observation_count=len(observations),
        mae=mae,
        rmse=rmse,
        bias=bias,
        max_abs_error=max_abs,
        tolerance=card.drift_tolerance,
        blockers=tuple(blockers),
        computation_allowed=computation_allowed,
    )


__all__ = [
    "ModelDriftAssessment",
    "ModelDriftObservation",
    "ModelDriftState",
    "ModelLifecycleCard",
    "ModelLifecycleState",
    "assess_model_drift",
]
