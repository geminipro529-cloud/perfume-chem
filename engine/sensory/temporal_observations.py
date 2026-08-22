"""Receipt-bound descriptive summaries for observed sensory time series."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

from engine.calibration.hashing import stable_json_hash
from engine.scientific_validation.complexity_model_admission import OAVGateBinding

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class TemporalSummaryState(str, Enum):
    REBUILD = "REBUILD"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    DESCRIPTIVE_ONLY = "DESCRIPTIVE_ONLY"


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
class TemporalObservation:
    observation_id: str
    dimension: str
    timepoint: str
    time_numeric: Decimal
    value: Decimal
    dominant_system: str | None
    evidence_sha256: str

    def __post_init__(self) -> None:
        for field_name in ("observation_id", "dimension", "timepoint"):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        time_numeric = _decimal(self.time_numeric, "time_numeric")
        if time_numeric < 0:
            raise ValueError("time_numeric must be non-negative")
        object.__setattr__(self, "time_numeric", time_numeric)
        object.__setattr__(self, "value", _decimal(self.value, "value"))
        if self.dominant_system is not None:
            object.__setattr__(
                self,
                "dominant_system",
                _text(self.dominant_system, "dominant_system"),
            )
        object.__setattr__(
            self,
            "evidence_sha256",
            _sha256(self.evidence_sha256, "evidence_sha256"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "dimension": self.dimension,
            "timepoint": self.timepoint,
            "time_numeric": str(self.time_numeric),
            "value": str(self.value),
            "dominant_system": self.dominant_system,
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class TemporalObservationSeries:
    series_id: str
    formula_sha256: str
    time_unit: str
    observations: tuple[TemporalObservation, ...]
    oav_binding: OAVGateBinding
    formula_mutation_authorized: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "series_id", _text(self.series_id, "series_id"))
        object.__setattr__(
            self,
            "formula_sha256",
            _sha256(self.formula_sha256, "formula_sha256"),
        )
        object.__setattr__(self, "time_unit", _text(self.time_unit, "time_unit"))
        if not self.observations:
            raise ValueError("observations must not be empty")
        if any(not isinstance(item, TemporalObservation) for item in self.observations):
            raise TypeError("observations must contain TemporalObservation values")
        ids = tuple(item.observation_id for item in self.observations)
        if len(ids) != len(set(ids)):
            raise ValueError("observation IDs must be unique")
        if not isinstance(self.oav_binding, OAVGateBinding):
            raise TypeError("oav_binding must be an OAVGateBinding")
        if self.oav_binding.formula_sha256 != self.formula_sha256:
            raise ValueError("OAV binding formula hash does not match the observation series")

    def as_dict(self) -> dict[str, Any]:
        return {
            "series_id": self.series_id,
            "formula_sha256": self.formula_sha256,
            "time_unit": self.time_unit,
            "observations": [item.as_dict() for item in self.observations],
            "oav_binding": self.oav_binding.as_dict(),
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "sensory_authority": self.sensory_authority,
            "release_authority": self.release_authority,
        }


@dataclass(frozen=True, slots=True)
class TemporalObservationSummary:
    state: TemporalSummaryState
    series_id: str
    dimension: str
    point_count: int
    peak_timepoint: str | None
    peak_value: Decimal | None
    switches: tuple[dict[str, str | None], ...]
    recurrence_events: tuple[dict[str, str], ...]
    blockers: tuple[str, ...]
    input_sha256: str
    claim_ceiling: str = field(
        default="OBSERVED_DESCRIPTIVE_WITHIN_RECORDED_SCOPE", init=False
    )
    inferential_authority: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "state": self.state.value,
            "series_id": self.series_id,
            "dimension": self.dimension,
            "point_count": self.point_count,
            "peak_timepoint": self.peak_timepoint,
            "peak_value": str(self.peak_value) if self.peak_value is not None else None,
            "switches": [dict(item) for item in self.switches],
            "recurrence_events": [dict(item) for item in self.recurrence_events],
            "blockers": list(self.blockers),
            "claim_ceiling": self.claim_ceiling,
            "input_sha256": self.input_sha256,
            "inferential_authority": self.inferential_authority,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "release_authority": self.release_authority,
        }
        payload["result_sha256"] = stable_json_hash(payload)
        return payload


def summarize_temporal_observations(
    series: TemporalObservationSeries,
    *,
    dimension: str,
) -> TemporalObservationSummary:
    """Summarize locked observations without fitting a model or making a causal claim."""

    if not isinstance(series, TemporalObservationSeries):
        raise TypeError("series must be a TemporalObservationSeries")
    selected_dimension = _text(dimension, "dimension")
    selected = tuple(
        sorted(
            (item for item in series.observations if item.dimension == selected_dimension),
            key=lambda item: (item.time_numeric, item.observation_id),
        )
    )
    blockers = tuple(series.oav_binding.screening_blockers)
    if blockers:
        state = TemporalSummaryState.REBUILD
    elif not selected:
        state = TemporalSummaryState.NOT_EVALUABLE
    else:
        state = TemporalSummaryState.DESCRIPTIVE_ONLY
    peak = max(selected, key=lambda item: item.value) if selected else None
    switches: list[dict[str, str | None]] = []
    for left, right in zip(selected, selected[1:]):
        if left.dominant_system != right.dominant_system:
            switches.append(
                {
                    "from": left.dominant_system,
                    "to": right.dominant_system,
                    "at": right.timepoint,
                }
            )
    recurrence: list[dict[str, str]] = []
    last_seen: dict[str, int] = {}
    for index, observation in enumerate(selected):
        dominant = observation.dominant_system
        if dominant is None:
            continue
        prior = last_seen.get(dominant)
        if prior is not None and index - prior > 1:
            intervening = {
                selected[position].dominant_system
                for position in range(prior + 1, index)
            }
            if any(item != dominant for item in intervening):
                recurrence.append({"system": dominant, "at": observation.timepoint})
        last_seen[dominant] = index
    return TemporalObservationSummary(
        state=state,
        series_id=series.series_id,
        dimension=selected_dimension,
        point_count=len(selected),
        peak_timepoint=peak.timepoint if peak else None,
        peak_value=peak.value if peak else None,
        switches=tuple(switches),
        recurrence_events=tuple(recurrence),
        blockers=blockers,
        input_sha256=stable_json_hash(
            {"series": series.as_dict(), "dimension": selected_dimension}
        ),
    )


__all__ = [
    "TemporalObservation",
    "TemporalObservationSeries",
    "TemporalObservationSummary",
    "TemporalSummaryState",
    "summarize_temporal_observations",
]
