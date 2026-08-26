"""Coded sensory evaluation ledger.

Stores time-resolved blind evaluations with separate identity ratings per
phase (opening, heart, drydown). Each sample is assigned a random 3-letter
code for blinding, and observations are recorded against that code.

Usage::

    from engine.sensory.ledger import SensoryTrial, SensorySample, SensoryObservation

    trial = SensoryTrial("Iris v2 vs v3", "sample_ref_001", ["Alice", "Bob"])
    sample = SensorySample(
        sample_id="550e8400-e29b-41d4-a716-446655440000",
        formula_id="iris_v2",
        batch_id="batch_001",
        code="XQP",
    )
    trial.add_sample(sample)
    trial.record_observation(SensoryObservation(
        observation_id="660e8400-e29b-41d4-a716-446655440001",
        sample_id=sample.sample_id,
        assessor="Alice",
        time_seconds=300.0,
        opening_identity=4.0,
        heart_identity=3.5,
        drydown_identity=3.0,
        transition_quality=4.0,
        texture=3.5,
        diffusion=4.0,
        longevity=3.0,
        overall_similarity=3.5,
        preference=4.0,
    ))
    summary = trial.summarize(sample.sample_id)
    mismatches = trial.detect_mismatch("candidate_id", "reference_id")
"""

from __future__ import annotations

import random
import string
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from statistics import median
from typing import Any, Mapping

from engine.domain_errors import LegacyWriteProhibitedError
from engine.evidence.augmentation import (
    DecisionDeltaV1,
    EvidenceAugmentationState,
    EvidenceDeltaReceiptV1,
    hold_receipt,
)
from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.sensory.order_balance import (
    OrderBalanceState,
    PresentationSchedule,
    assess_order_balance,
)

# ── Constants ────────────────────────────────────────────────────────────────────

TIME_POINTS: list[float] = [0, 300, 1800, 7200, 14400, 28800, 86400]
"""Standard evaluation time points in seconds:

* 0 s      — opening / first blast
* 300 s    — 5 min  (top-note burn-off)
* 1800 s   — 30 min (early heart)
* 7200 s   — 2 hr   (heart)
* 14400 s  — 4 hr   (late heart / early drydown)
* 28800 s  — 8 hr   (drydown)
* 86400 s  — 24 hr  (extended drydown)
"""

_OFFENSIVE_CODES: frozenset[str] = frozenset(
    {
        "FUK",
        "DIK",
        "ASS",
        "CUM",
        "SEX",
        "SUK",
        "FAG",
        "KKK",
        "WTF",
        "STD",
        "POO",
        "PEE",
        "CRP",
        "BUM",
        "GAY",
        "NGR",
        "CNT",
        "CLT",
        "KNT",
        "DUM",
        "TWT",
        "FUC",
        "SHI",
        "BIT",
    }
)
"""Three-letter codes that are excluded from generation."""


# ── Dataclasses ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SensorySample:
    """A single blinded sample prepared for sensory evaluation.

    Parameters
    ----------
    sample_id:
        UUID string identifying this sample.
    formula_id:
        Identifier for the formula being evaluated.
    batch_id:
        Identifier for the physical batch.
    code:
        Random 3-letter uppercase blinding code.
    application_mass_g:
        Mass of fragrance applied to the substrate, in grams.
    substrate:
        Substrate type. One of ``"blotter"``, ``"skin_forearm"``,
        ``"skin_wrist"``, ``"mouillette"``.
    room_temperature_c:
        Room temperature at time of preparation, in °C.
    room_humidity_pct:
        Room relative humidity at time of preparation, in percent.
    prepared_at:
        ISO 8601 datetime string when the sample was prepared.
    """

    sample_id: str
    formula_id: str
    batch_id: str
    code: str
    application_mass_g: float = 0.01
    substrate: str = "blotter"
    room_temperature_c: float = 22.0
    room_humidity_pct: float = 50.0
    prepared_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "formula_id": self.formula_id,
            "batch_id": self.batch_id,
            "code": self.code,
            "application_mass_g": self.application_mass_g,
            "substrate": self.substrate,
            "room_temperature_c": self.room_temperature_c,
            "room_humidity_pct": self.room_humidity_pct,
            "prepared_at": self.prepared_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SensorySample:
        return cls(
            sample_id=str(data["sample_id"]),
            formula_id=str(data["formula_id"]),
            batch_id=str(data["batch_id"]),
            code=str(data["code"]),
            application_mass_g=float(data.get("application_mass_g") or 0.01),
            substrate=str(data.get("substrate") or "blotter"),
            room_temperature_c=float(data.get("room_temperature_c") or 22.0),
            room_humidity_pct=float(data.get("room_humidity_pct") or 50.0),
            prepared_at=str(data["prepared_at"]) if data.get("prepared_at") else None,
        )


@dataclass(frozen=True, slots=True)
class SensoryObservation:
    """A single time-resolved observation from one assessor.

    Parameters
    ----------
    observation_id:
        UUID string identifying this observation.
    sample_id:
        UUID string referencing the :class:`SensorySample`.
    assessor:
        Name or identifier of the assessor.
    time_seconds:
        Time elapsed since application, in seconds.
    opening_identity:
        How well the opening matches the reference (1–5).
    heart_identity:
        How well the heart matches the reference (1–5).
    drydown_identity:
        How well the drydown matches the reference (1–5).
    transition_quality:
        How smooth the phase transitions are (1–5).
    texture:
        How pleasing the tactile sensation is (1–5).
    diffusion:
        How well the fragrance projects (1–5).
    longevity:
        How long the fragrance lasts (1–5).
    off_notes:
        Description of any unpleasant notes. Empty string if none.
    overall_similarity:
        Overall similarity to the reference (1–5).
    preference:
        Personal liking (1–5).
    notes:
        Free-text notes from the assessor.
    """

    observation_id: str
    sample_id: str
    assessor: str
    time_seconds: float
    opening_identity: float
    heart_identity: float
    drydown_identity: float
    transition_quality: float
    texture: float
    diffusion: float
    longevity: float
    off_notes: str = ""
    overall_similarity: float = 3.0
    preference: float = 3.0
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "sample_id": self.sample_id,
            "assessor": self.assessor,
            "time_seconds": self.time_seconds,
            "opening_identity": self.opening_identity,
            "heart_identity": self.heart_identity,
            "drydown_identity": self.drydown_identity,
            "transition_quality": self.transition_quality,
            "texture": self.texture,
            "diffusion": self.diffusion,
            "longevity": self.longevity,
            "off_notes": self.off_notes,
            "overall_similarity": self.overall_similarity,
            "preference": self.preference,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SensoryObservation:
        return cls(
            observation_id=str(data["observation_id"]),
            sample_id=str(data["sample_id"]),
            assessor=str(data["assessor"]),
            time_seconds=float(data["time_seconds"]),
            opening_identity=float(data["opening_identity"]),
            heart_identity=float(data["heart_identity"]),
            drydown_identity=float(data["drydown_identity"]),
            transition_quality=float(data["transition_quality"]),
            texture=float(data["texture"]),
            diffusion=float(data["diffusion"]),
            longevity=float(data["longevity"]),
            off_notes=str(data.get("off_notes") or ""),
            overall_similarity=float(data.get("overall_similarity") or 3.0),
            preference=float(data.get("preference") or 3.0),
            notes=str(data.get("notes") or ""),
        )


class TemporalEvidenceState(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    HOLD = "HOLD"


class TemporalEvidenceDisposition(str, Enum):
    """V2 evidence-sufficiency state without changing historical V1 replay."""

    RESOLVED = "RESOLVED"
    INCOMPLETE = "INCOMPLETE"
    CONFLICTED = "CONFLICTED"
    PROTOCOL_HOLD = "PROTOCOL_HOLD"
    INSUFFICIENT_SCOPE = "INSUFFICIENT_SCOPE"


class AssessorReliabilityState(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    PASS = "PASS"
    HOLD = "HOLD"


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _unique_text(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_required_text(value, field_name) for value in values)
    if not normalized or len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique nonblank values")
    return normalized


@dataclass(frozen=True, slots=True, order=True)
class ObservationCellKey:
    protocol_id: str
    sample_id: str
    assessor_id: str
    repeat_id: str
    time_seconds: float
    endpoint_id: str

    def __post_init__(self) -> None:
        for name in (
            "protocol_id",
            "sample_id",
            "assessor_id",
            "repeat_id",
            "endpoint_id",
        ):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        if not isfinite(self.time_seconds) or self.time_seconds < 0:
            raise ValueError("time_seconds must be finite and nonnegative")


@dataclass(frozen=True, slots=True)
class TemporalObservationCell:
    key: ObservationCellKey
    observation_id: str
    value: float
    presentation_sequence_id: str
    presentation_position: int

    def __post_init__(self) -> None:
        if not isinstance(self.key, ObservationCellKey):
            raise TypeError("key must be an ObservationCellKey")
        object.__setattr__(
            self,
            "observation_id",
            _required_text(self.observation_id, "observation_id"),
        )
        object.__setattr__(
            self,
            "presentation_sequence_id",
            _required_text(
                self.presentation_sequence_id,
                "presentation_sequence_id",
            ),
        )
        if not isfinite(self.value):
            raise ValueError("value must be finite")
        if isinstance(self.presentation_position, bool) or self.presentation_position < 1:
            raise ValueError("presentation_position must be a positive integer")

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible shape suitable for existing context fields."""

        return {
            "protocol_id": self.key.protocol_id,
            "sample_id": self.key.sample_id,
            "assessor_id": self.key.assessor_id,
            "repeat_id": self.key.repeat_id,
            "time_seconds": self.key.time_seconds,
            "endpoint_id": self.key.endpoint_id,
            "observation_id": self.observation_id,
            "value": self.value,
            "presentation_sequence_id": self.presentation_sequence_id,
            "presentation_position": self.presentation_position,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> TemporalObservationCell:
        """Hydrate one cell from backend observation/comparison context JSON."""

        if not isinstance(value, Mapping):
            raise TypeError("temporal observation context must be a mapping")
        return cls(
            key=ObservationCellKey(
                protocol_id=str(value["protocol_id"]),
                sample_id=str(value["sample_id"]),
                assessor_id=str(value["assessor_id"]),
                repeat_id=str(value["repeat_id"]),
                time_seconds=float(value["time_seconds"]),
                endpoint_id=str(value["endpoint_id"]),
            ),
            observation_id=str(value["observation_id"]),
            value=float(value["value"]),
            presentation_sequence_id=str(value["presentation_sequence_id"]),
            presentation_position=int(value["presentation_position"]),
        )


@dataclass(frozen=True, slots=True)
class SensorySafetyEvent:
    """One assessor safety incident that stops evidentiary promotion."""

    event_id: str
    protocol_id: str
    assessor_id: str
    sample_id: str
    time_seconds: float
    event_code: str
    note: str

    def __post_init__(self) -> None:
        for name in (
            "event_id",
            "protocol_id",
            "assessor_id",
            "sample_id",
            "event_code",
            "note",
        ):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        if not isfinite(self.time_seconds) or self.time_seconds < 0:
            raise ValueError("time_seconds must be finite and nonnegative")

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "protocol_id": self.protocol_id,
            "assessor_id": self.assessor_id,
            "sample_id": self.sample_id,
            "time_seconds": self.time_seconds,
            "event_code": self.event_code,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> SensorySafetyEvent:
        if not isinstance(value, Mapping):
            raise TypeError("sensory safety event context must be a mapping")
        return cls(
            event_id=str(value["event_id"]),
            protocol_id=str(value["protocol_id"]),
            assessor_id=str(value["assessor_id"]),
            sample_id=str(value["sample_id"]),
            time_seconds=float(value["time_seconds"]),
            event_code=str(value["event_code"]),
            note=str(value["note"]),
        )


@dataclass(frozen=True, slots=True)
class SensoryProtocolScope:
    protocol_id: str
    sample_ids: tuple[str, ...]
    assessor_ids: tuple[str, ...]
    repeat_ids: tuple[str, ...]
    timepoints_seconds: tuple[float, ...]
    endpoint_ids: tuple[str, ...]
    schedule_sha256: str
    within_sniff: bool = False
    within_sniff_apparatus_qualified: bool = False
    within_sniff_timing_protocol_qualified: bool = False
    require_repeatability: bool = False
    maximum_within_assessor_repeat_spread: float | None = None
    within_sniff_apparatus_id: str | None = None
    within_sniff_clock_source: str | None = None
    within_sniff_timing_tolerance_ms: float | None = None
    within_sniff_qualification_sha256: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "protocol_id", _required_text(self.protocol_id, "protocol_id")
        )
        for name in ("sample_ids", "assessor_ids", "repeat_ids", "endpoint_ids"):
            object.__setattr__(
                self,
                name,
                _unique_text(tuple(getattr(self, name)), name),
            )
        timepoints = tuple(float(value) for value in self.timepoints_seconds)
        if (
            not timepoints
            or any(not isfinite(value) or value < 0 for value in timepoints)
            or tuple(sorted(set(timepoints))) != timepoints
        ):
            raise ValueError(
                "timepoints_seconds must be unique, increasing, finite, and nonnegative"
            )
        object.__setattr__(self, "timepoints_seconds", timepoints)
        digest = _required_text(self.schedule_sha256, "schedule_sha256").lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("schedule_sha256 must be a SHA-256 hex digest")
        object.__setattr__(self, "schedule_sha256", digest)
        for name in (
            "within_sniff",
            "within_sniff_apparatus_qualified",
            "within_sniff_timing_protocol_qualified",
            "require_repeatability",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be boolean")
        threshold = self.maximum_within_assessor_repeat_spread
        if threshold is not None and (not isfinite(threshold) or threshold < 0):
            raise ValueError(
                "maximum_within_assessor_repeat_spread must be finite and nonnegative"
            )
        for name in ("within_sniff_apparatus_id", "within_sniff_clock_source"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _required_text(value, name))
        tolerance = self.within_sniff_timing_tolerance_ms
        if tolerance is not None and (not isfinite(tolerance) or tolerance <= 0):
            raise ValueError(
                "within_sniff_timing_tolerance_ms must be finite and positive"
            )
        qualification = self.within_sniff_qualification_sha256
        if qualification is not None:
            digest = _required_text(
                qualification, "within_sniff_qualification_sha256"
            ).lower()
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError(
                    "within_sniff_qualification_sha256 must be a SHA-256 hex digest"
                )
            object.__setattr__(self, "within_sniff_qualification_sha256", digest)


@dataclass(frozen=True, slots=True)
class TemporalEvidenceRequest:
    scope: SensoryProtocolScope
    schedule: PresentationSchedule
    cells: tuple[TemporalObservationCell, ...]
    safety_events: tuple[SensorySafetyEvent, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.scope, SensoryProtocolScope):
            raise TypeError("scope must be a SensoryProtocolScope")
        if not isinstance(self.schedule, PresentationSchedule):
            raise TypeError("schedule must be a PresentationSchedule")
        cells = tuple(self.cells)
        if any(not isinstance(cell, TemporalObservationCell) for cell in cells):
            raise TypeError("cells must contain TemporalObservationCell values")
        object.__setattr__(self, "cells", cells)
        safety_events = tuple(self.safety_events)
        if any(not isinstance(event, SensorySafetyEvent) for event in safety_events):
            raise TypeError("safety_events must contain SensorySafetyEvent values")
        event_ids = tuple(event.event_id for event in safety_events)
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("sensory safety event IDs must be unique")
        object.__setattr__(self, "safety_events", safety_events)


@dataclass(frozen=True, slots=True)
class TemporalEndpointSummary:
    sample_id: str
    endpoint_id: str
    time_seconds: float
    observed_count: int
    median: float
    first_quartile: float
    third_quartile: float
    assessor_disagreement: float


@dataclass(frozen=True, slots=True)
class TemporalTransition:
    sample_id: str
    endpoint_id: str
    from_time_seconds: float
    to_time_seconds: float
    median_delta: float


@dataclass(frozen=True, slots=True)
class AssessorReliabilitySummary:
    assessor_id: str
    observed_repeat_groups: int
    maximum_repeat_spread: float | None


@dataclass(frozen=True, slots=True)
class TemporalEvidenceResult:
    state: TemporalEvidenceState
    protocol_id: str
    schedule_sha256: str
    expected_cell_count: int
    observed_cell_count: int
    missing_cells: tuple[ObservationCellKey, ...]
    duplicate_cells: tuple[ObservationCellKey, ...]
    summaries: tuple[TemporalEndpointSummary, ...]
    transitions: tuple[TemporalTransition, ...]
    order_balance_state: OrderBalanceState
    blockers: tuple[str, ...]
    next_discriminator: str | None
    safety_events: tuple[SensorySafetyEvent, ...]
    safety_stop_triggered: bool
    assessor_reliability_state: AssessorReliabilityState
    assessor_reliability: tuple[AssessorReliabilitySummary, ...]
    interpolated_cell_count: int = field(default=0, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)


@dataclass(frozen=True, slots=True)
class TemporalEvidenceAuditResultV2:
    """Observed-only audit that emits zero or one evidence action."""

    disposition: TemporalEvidenceDisposition
    protocol_id: str
    summaries: tuple[TemporalEndpointSummary, ...]
    transitions: tuple[TemporalTransition, ...]
    missing_cells: tuple[ObservationCellKey, ...]
    duplicate_cells: tuple[ObservationCellKey, ...]
    source_cell_count: int
    excluded_duplicate_row_count: int
    next_discriminator: str | None
    receipt: EvidenceDeltaReceiptV1
    legacy_result: TemporalEvidenceResult

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "disposition", TemporalEvidenceDisposition(self.disposition)
        )
        if not isinstance(self.receipt, EvidenceDeltaReceiptV1):
            raise TypeError("receipt must be an EvidenceDeltaReceiptV1")
        if not isinstance(self.legacy_result, TemporalEvidenceResult):
            raise TypeError("legacy_result must be a TemporalEvidenceResult")


def analyze_temporal_evidence(
    request: TemporalEvidenceRequest,
) -> TemporalEvidenceResult:
    """Summarize only canonical observed cells; never interpolate evidence."""

    if not isinstance(request, TemporalEvidenceRequest):
        raise TypeError("request must be a TemporalEvidenceRequest")
    scope = request.scope
    expected = tuple(
        ObservationCellKey(
            protocol_id=scope.protocol_id,
            sample_id=sample_id,
            assessor_id=assessor_id,
            repeat_id=repeat_id,
            time_seconds=timepoint,
            endpoint_id=endpoint_id,
        )
        for sample_id in scope.sample_ids
        for assessor_id in scope.assessor_ids
        for repeat_id in scope.repeat_ids
        for timepoint in scope.timepoints_seconds
        for endpoint_id in scope.endpoint_ids
    )
    counts = Counter(cell.key for cell in request.cells)
    expected_set = set(expected)
    missing = tuple(sorted(expected_set.difference(counts)))
    duplicates = tuple(sorted(key for key, count in counts.items() if count > 1))
    grouped: dict[tuple[str, str, float], list[float]] = defaultdict(list)
    for cell in request.cells:
        if cell.key in expected_set:
            grouped[
                (cell.key.sample_id, cell.key.endpoint_id, cell.key.time_seconds)
            ].append(cell.value)
    summaries = tuple(
        _endpoint_summary(key, values)
        for key, values in sorted(grouped.items())
    )
    transitions = _temporal_transitions(summaries)
    order = assess_order_balance(request.schedule)
    blockers: list[str] = []
    if request.schedule.schedule_sha256 != scope.schedule_sha256:
        blockers.append("presentation schedule hash does not match protocol scope")
    if order.state is OrderBalanceState.REBUILD:
        blockers.extend(order.failures)
    if duplicates:
        blockers.append("duplicate canonical observation cells are present")
    if scope.within_sniff:
        if not scope.within_sniff_apparatus_qualified:
            blockers.append("within-sniff observations require qualified timing apparatus")
        if not scope.within_sniff_timing_protocol_qualified:
            blockers.append("within-sniff observations require a qualified timing protocol")
    reliability = _assessor_reliability(scope, request.cells, expected_set)
    if not scope.require_repeatability:
        reliability_state = AssessorReliabilityState.NOT_REQUIRED
    elif len(scope.repeat_ids) < 2:
        reliability_state = AssessorReliabilityState.NOT_EVALUABLE
        blockers.append("repeatability requires at least two declared repeats")
    elif scope.maximum_within_assessor_repeat_spread is None:
        reliability_state = AssessorReliabilityState.NOT_EVALUABLE
        blockers.append("repeatability requires a declared maximum assessor spread")
    elif missing or duplicates:
        reliability_state = AssessorReliabilityState.NOT_EVALUABLE
    elif any(
        summary.maximum_repeat_spread is None
        for summary in reliability
    ):
        reliability_state = AssessorReliabilityState.NOT_EVALUABLE
        blockers.append("repeatability evidence is not evaluable for every assessor")
    elif any(
        (summary.maximum_repeat_spread or 0)
        > scope.maximum_within_assessor_repeat_spread
        for summary in reliability
    ):
        reliability_state = AssessorReliabilityState.HOLD
        for summary in reliability:
            if (
                summary.maximum_repeat_spread is not None
                and summary.maximum_repeat_spread
                > scope.maximum_within_assessor_repeat_spread
            ):
                blockers.append(
                    f"{summary.assessor_id} exceeds the declared repeatability "
                    f"threshold: {summary.maximum_repeat_spread:g} > "
                    f"{scope.maximum_within_assessor_repeat_spread:g}"
                )
    else:
        reliability_state = AssessorReliabilityState.PASS
    for event in request.safety_events:
        if event.protocol_id != scope.protocol_id:
            blockers.append(
                f"sensory safety event {event.event_id} does not match protocol scope"
            )
        if event.assessor_id not in scope.assessor_ids:
            blockers.append(
                f"sensory safety event {event.event_id} names an unknown assessor"
            )
        if event.sample_id not in scope.sample_ids:
            blockers.append(
                f"sensory safety event {event.event_id} names an unknown sample"
            )
        blockers.append(
            f"sensory safety stop triggered: {event.event_code} ({event.event_id})"
        )
    state = (
        TemporalEvidenceState.HOLD
        if blockers
        else TemporalEvidenceState.INCOMPLETE
        if missing
        else TemporalEvidenceState.COMPLETE
    )
    next_discriminator = None
    if missing:
        next_discriminator = f"Collect missing cell {missing[0]}."
    elif summaries:
        most_disputed = max(
            summaries,
            key=lambda item: (
                item.assessor_disagreement,
                item.sample_id,
                item.endpoint_id,
                item.time_seconds,
            ),
        )
        if most_disputed.assessor_disagreement > 0:
            next_discriminator = (
                f"Repeat {most_disputed.sample_id} {most_disputed.endpoint_id} at "
                f"{most_disputed.time_seconds:g}s to resolve assessor disagreement."
            )
    return TemporalEvidenceResult(
        state=state,
        protocol_id=scope.protocol_id,
        schedule_sha256=request.schedule.schedule_sha256,
        expected_cell_count=len(expected),
        observed_cell_count=len(counts),
        missing_cells=missing,
        duplicate_cells=duplicates,
        summaries=summaries,
        transitions=transitions,
        order_balance_state=order.state,
        blockers=tuple(blockers),
        next_discriminator=next_discriminator,
        safety_events=request.safety_events,
        safety_stop_triggered=bool(request.safety_events),
        assessor_reliability_state=reliability_state,
        assessor_reliability=reliability,
    )


def _assessor_reliability(
    scope: SensoryProtocolScope,
    cells: tuple[TemporalObservationCell, ...],
    expected: set[ObservationCellKey],
) -> tuple[AssessorReliabilitySummary, ...]:
    grouped: dict[tuple[str, str, float, str], list[float]] = defaultdict(list)
    for cell in cells:
        if cell.key in expected:
            grouped[
                (
                    cell.key.assessor_id,
                    cell.key.sample_id,
                    cell.key.time_seconds,
                    cell.key.endpoint_id,
                )
            ].append(cell.value)
    summaries: list[AssessorReliabilitySummary] = []
    for assessor_id in scope.assessor_ids:
        spreads = tuple(
            max(values) - min(values)
            for key, values in grouped.items()
            if key[0] == assessor_id and len(values) >= 2
        )
        summaries.append(
            AssessorReliabilitySummary(
                assessor_id=assessor_id,
                observed_repeat_groups=len(spreads),
                maximum_repeat_spread=max(spreads) if spreads else None,
            )
        )
    return tuple(summaries)


def _endpoint_summary(
    key: tuple[str, str, float],
    values: list[float],
) -> TemporalEndpointSummary:
    ordered = sorted(values)
    middle = median(ordered)
    lower = median(ordered[: len(ordered) // 2]) if len(ordered) > 1 else middle
    upper_start = (len(ordered) + 1) // 2
    upper = median(ordered[upper_start:]) if len(ordered) > 1 else middle
    return TemporalEndpointSummary(
        sample_id=key[0],
        endpoint_id=key[1],
        time_seconds=key[2],
        observed_count=len(ordered),
        median=float(middle),
        first_quartile=float(lower),
        third_quartile=float(upper),
        assessor_disagreement=float(ordered[-1] - ordered[0]),
    )


def _temporal_transitions(
    summaries: tuple[TemporalEndpointSummary, ...],
) -> tuple[TemporalTransition, ...]:
    grouped: dict[tuple[str, str], list[TemporalEndpointSummary]] = defaultdict(list)
    for summary in summaries:
        grouped[(summary.sample_id, summary.endpoint_id)].append(summary)
    transitions: list[TemporalTransition] = []
    for (sample_id, endpoint_id), values in sorted(grouped.items()):
        ordered = sorted(values, key=lambda item: item.time_seconds)
        for left, right in zip(ordered, ordered[1:]):
            transitions.append(
                TemporalTransition(
                    sample_id=sample_id,
                    endpoint_id=endpoint_id,
                    from_time_seconds=left.time_seconds,
                    to_time_seconds=right.time_seconds,
                    median_delta=right.median - left.median,
                )
            )
    return tuple(transitions)


_TEMPORAL_AUDIT_POLICY_SHA256 = sha256_hex(
    canonical_json_bytes(
        {
            "policy": "TEMPORAL_EVIDENCE_SUFFICIENCY_V2",
            "canonical_cell": (
                "protocol/sample/assessor/repeat/timepoint/endpoint"
            ),
            "duplicate_policy": "EXCLUDE_ALL_CONFLICTED_ROWS_FROM_SUMMARIES",
            "missing_policy": "NO_INTERPOLATION_ONE_NEXT_CELL",
            "disagreement_policy": "NO_RETEST_WITHOUT_DECLARED_THRESHOLD",
        }
    )
)


def _cell_key_payload(key: ObservationCellKey) -> dict[str, object]:
    return {
        "protocol_id": key.protocol_id,
        "sample_id": key.sample_id,
        "assessor_id": key.assessor_id,
        "repeat_id": key.repeat_id,
        "time_seconds": key.time_seconds,
        "endpoint_id": key.endpoint_id,
    }


def _scope_payload(scope: SensoryProtocolScope) -> dict[str, object]:
    return {
        "protocol_id": scope.protocol_id,
        "sample_ids": list(scope.sample_ids),
        "assessor_ids": list(scope.assessor_ids),
        "repeat_ids": list(scope.repeat_ids),
        "timepoints_seconds": list(scope.timepoints_seconds),
        "endpoint_ids": list(scope.endpoint_ids),
        "schedule_sha256": scope.schedule_sha256,
        "within_sniff": scope.within_sniff,
        "within_sniff_apparatus_qualified": (
            scope.within_sniff_apparatus_qualified
        ),
        "within_sniff_timing_protocol_qualified": (
            scope.within_sniff_timing_protocol_qualified
        ),
        "require_repeatability": scope.require_repeatability,
        "maximum_within_assessor_repeat_spread": (
            scope.maximum_within_assessor_repeat_spread
        ),
        "within_sniff_apparatus_id": scope.within_sniff_apparatus_id,
        "within_sniff_clock_source": scope.within_sniff_clock_source,
        "within_sniff_timing_tolerance_ms": (
            scope.within_sniff_timing_tolerance_ms
        ),
        "within_sniff_qualification_sha256": (
            scope.within_sniff_qualification_sha256
        ),
    }


def _safe_observed_summaries(
    request: TemporalEvidenceRequest,
    duplicate_keys: tuple[ObservationCellKey, ...],
) -> tuple[TemporalEndpointSummary, ...]:
    scope = request.scope
    expected = {
        ObservationCellKey(
            protocol_id=scope.protocol_id,
            sample_id=sample_id,
            assessor_id=assessor_id,
            repeat_id=repeat_id,
            time_seconds=timepoint,
            endpoint_id=endpoint_id,
        )
        for sample_id in scope.sample_ids
        for assessor_id in scope.assessor_ids
        for repeat_id in scope.repeat_ids
        for timepoint in scope.timepoints_seconds
        for endpoint_id in scope.endpoint_ids
    }
    conflicted = set(duplicate_keys)
    grouped: dict[tuple[str, str, float], list[float]] = defaultdict(list)
    for cell in request.cells:
        if cell.key in expected and cell.key not in conflicted:
            grouped[
                (cell.key.sample_id, cell.key.endpoint_id, cell.key.time_seconds)
            ].append(cell.value)
    return tuple(
        _endpoint_summary(key, values) for key, values in sorted(grouped.items())
    )


def _within_sniff_v2_blockers(scope: SensoryProtocolScope) -> tuple[str, ...]:
    if not scope.within_sniff:
        return ()
    blockers: list[str] = []
    if scope.within_sniff_apparatus_id is None:
        blockers.append("within-sniff observations require apparatus identity")
    if scope.within_sniff_clock_source is None:
        blockers.append("within-sniff observations require a bound clock source")
    if scope.within_sniff_timing_tolerance_ms is None:
        blockers.append("within-sniff observations require a timing tolerance")
    if scope.within_sniff_qualification_sha256 is None:
        blockers.append("within-sniff observations require qualification evidence")
    return tuple(blockers)


def audit_temporal_evidence(
    request: TemporalEvidenceRequest,
) -> TemporalEvidenceAuditResultV2:
    """Audit evidence sufficiency while preserving every source observation row."""

    if not isinstance(request, TemporalEvidenceRequest):
        raise TypeError("request must be a TemporalEvidenceRequest")
    legacy = analyze_temporal_evidence(request)
    scope = request.scope
    counts = Counter(cell.key for cell in request.cells)
    duplicates = tuple(sorted(key for key, count in counts.items() if count > 1))
    safe_summaries = _safe_observed_summaries(request, duplicates)
    safe_transitions = _temporal_transitions(safe_summaries)
    excluded_duplicate_row_count = sum(counts[key] for key in duplicates)

    protocol_blockers = [
        blocker
        for blocker in legacy.blockers
        if blocker != "duplicate canonical observation cells are present"
    ]
    protocol_blockers.extend(_within_sniff_v2_blockers(scope))
    expected = {
        ObservationCellKey(
            protocol_id=scope.protocol_id,
            sample_id=sample_id,
            assessor_id=assessor_id,
            repeat_id=repeat_id,
            time_seconds=timepoint,
            endpoint_id=endpoint_id,
        )
        for sample_id in scope.sample_ids
        for assessor_id in scope.assessor_ids
        for repeat_id in scope.repeat_ids
        for timepoint in scope.timepoints_seconds
        for endpoint_id in scope.endpoint_ids
    }
    if any(cell.key not in expected for cell in request.cells):
        protocol_blockers.append(
            "observation cell is outside the declared protocol scope"
        )

    if protocol_blockers:
        disposition = TemporalEvidenceDisposition.PROTOCOL_HOLD
        blockers = tuple(dict.fromkeys(protocol_blockers))
        next_discriminator = "CORRECT_PROTOCOL"
        reason_codes = ("PROTOCOL_INVALID",)
    elif duplicates:
        disposition = TemporalEvidenceDisposition.CONFLICTED
        blockers = ("duplicate canonical observation cells require provenance audit",)
        next_discriminator = (
            "AUDIT_PROVENANCE:protocol/sample/assessor/repeat/timepoint/endpoint"
        )
        reason_codes = ("CANONICAL_CELL_CONFLICT",)
    elif len(scope.timepoints_seconds) < 2:
        disposition = TemporalEvidenceDisposition.INSUFFICIENT_SCOPE
        blockers = ("temporal scope requires at least two declared timepoints",)
        next_discriminator = "EXPAND_TEMPORAL_SCOPE"
        reason_codes = ("TEMPORAL_SCOPE_INSUFFICIENT",)
    elif legacy.missing_cells:
        disposition = TemporalEvidenceDisposition.INCOMPLETE
        blockers = ("temporal evidence grid is incomplete",)
        cell_text = canonical_json_bytes(
            _cell_key_payload(legacy.missing_cells[0])
        ).decode("utf-8")
        next_discriminator = f"COLLECT_CELL:{cell_text}"
        reason_codes = ("ONE_MISSING_CELL_SELECTED",)
    else:
        disposition = TemporalEvidenceDisposition.RESOLVED
        blockers = ()
        next_discriminator = None
        reason_codes = ("OBSERVED_TEMPORAL_SUMMARY_RESOLVED",)

    evidence_payload = {
        "cells": [cell.as_dict() for cell in request.cells],
        "safety_events": [event.as_dict() for event in request.safety_events],
    }
    evidence_sha256 = sha256_hex(canonical_json_bytes(evidence_payload))
    input_sha256 = sha256_hex(
        canonical_json_bytes(
            {
                "scope": _scope_payload(scope),
                "schedule": request.schedule.as_dict(),
                "evidence_sha256": evidence_sha256,
            }
        )
    )
    source_bindings = tuple(sorted({scope.schedule_sha256, evidence_sha256}))
    exact_scope = f"{scope.protocol_id}/TEMPORAL"
    if disposition is TemporalEvidenceDisposition.RESOLVED:
        delta = DecisionDeltaV1(
            delta_id=f"TEMPORAL:{scope.protocol_id}",
            decision_effect=(
                "Use the observed temporal summaries and transitions at this exact "
                "protocol scope; request no additional temporal experiment."
            ),
            observed_facts=(
                f"observed_cells={len(counts)}",
                "missing_cells=0",
                "duplicate_cells=0",
                f"order_balance={legacy.order_balance_state.value}",
            ),
            derived_calculations=(
                f"endpoint_summaries={len(safe_summaries)}",
                f"paired_transitions={len(safe_transitions)}",
                f"assessor_reliability={legacy.assessor_reliability_state.value}",
            ),
            hypotheses=(),
            forbidden_inferences=(
                "Observed temporal behavior does not establish composition-derived liking.",
                "No missing cell was interpolated and no volatility prediction was treated as perception.",
            ),
        )
        receipt = EvidenceDeltaReceiptV1(
            module_id="temporal_sensory_ledger",
            exact_scope=exact_scope,
            state=EvidenceAugmentationState.AUGMENT,
            input_sha256=input_sha256,
            evidence_sha256=evidence_sha256,
            policy_sha256=_TEMPORAL_AUDIT_POLICY_SHA256,
            source_binding_sha256=source_bindings,
            reason_codes=reason_codes,
            delta=delta,
            blockers=(),
            next_action=None,
        )
    else:
        receipt = hold_receipt(
            module_id="temporal_sensory_ledger",
            exact_scope=exact_scope,
            input_sha256=input_sha256,
            evidence_sha256=evidence_sha256,
            policy_sha256=_TEMPORAL_AUDIT_POLICY_SHA256,
            source_binding_sha256=source_bindings,
            reasons=reason_codes,
            blockers=blockers,
            next_action=next_discriminator,
        )
    return TemporalEvidenceAuditResultV2(
        disposition=disposition,
        protocol_id=scope.protocol_id,
        summaries=safe_summaries,
        transitions=safe_transitions,
        missing_cells=legacy.missing_cells,
        duplicate_cells=duplicates,
        source_cell_count=len(request.cells),
        excluded_duplicate_row_count=excluded_duplicate_row_count,
        next_discriminator=next_discriminator,
        receipt=receipt,
        legacy_result=legacy,
    )


# ── Code generation ──────────────────────────────────────────────────────────────


def generate_trial_codes(count: int) -> list[str]:
    """Generate ``count`` random 3-letter uppercase blinding codes.

    No duplicates are produced, and offensive combinations (e.g. ``"FUK"``,
    ``"DIK"``) are excluded.

    Parameters
    ----------
    count:
        Number of codes to generate.

    Returns
    -------
    list[str]:
        A list of unique 3-letter uppercase codes.

    Raises
    ------
    ValueError:
        If ``count`` exceeds the number of possible non-offensive codes.
    """
    letters = string.ascii_uppercase
    all_possible = 26**3
    max_safe = all_possible - len(_OFFENSIVE_CODES)
    if count > max_safe:
        raise ValueError(
            f"Cannot generate {count} unique codes; "
            f"only {max_safe} non-offensive combinations available."
        )

    codes: set[str] = set()
    while len(codes) < count:
        code = "".join(random.choices(letters, k=3))
        if code not in _OFFENSIVE_CODES:
            codes.add(code)
    return list(codes)


# ── Trial ────────────────────────────────────────────────────────────────────────


class SensoryTrial:
    """A structured sensory trial comparing one or more samples.

    Manages blinded samples, time-resolved observations, summary statistics,
    and mismatch detection against a reference.

    Parameters
    ----------
    trial_name:
        Human-readable name for this trial (e.g. ``"Iris v2 vs v3"``).
    reference_sample_id:
        The ``sample_id`` of the reference sample that other samples are
        compared against.
    assessors:
        List of assessor names or identifiers participating in this trial.
    """

    def __init__(
        self,
        trial_name: str,
        reference_sample_id: str,
        assessors: list[str],
    ) -> None:
        self.trial_name: str = trial_name
        self.reference_sample_id: str = reference_sample_id
        self.assessors: list[str] = list(assessors)
        self._samples: dict[str, SensorySample] = {}
        self._observations: list[SensoryObservation] = []

    # ── mutation ────────────────────────────────────────────────────────────

    def add_sample(self, sample: SensorySample) -> None:
        """Reject writes to the deprecated in-memory duplicate store."""
        del sample
        raise LegacyWriteProhibitedError(
            "SensoryTrial is read-only; persist samples through LabService"
        )

    def record_observation(self, obs: SensoryObservation) -> None:
        """Reject writes to the deprecated in-memory duplicate store."""
        del obs
        raise LegacyWriteProhibitedError(
            "SensoryTrial is read-only; persist observations through LabService"
        )

    # ── queries ─────────────────────────────────────────────────────────────

    def get_observations_for_sample(self, sample_id: str) -> list[SensoryObservation]:
        """Return all observations for a given sample."""
        return [o for o in self._observations if o.sample_id == sample_id]

    def get_observations_at_time(self, time_seconds: float) -> list[SensoryObservation]:
        """Return all observations recorded at a specific time point."""
        return [o for o in self._observations if o.time_seconds == time_seconds]

    def summarize(self, sample_id: str) -> dict[str, float]:
        """Compute average identity and similarity scores for a sample.

        Returns a dict with keys ``avg_opening``, ``avg_heart``,
        ``avg_drydown``, ``avg_overall``. Returns 0.0 for any axis that
        has no observations.
        """
        obs = self.get_observations_for_sample(sample_id)
        if not obs:
            return {
                "avg_opening": 0.0,
                "avg_heart": 0.0,
                "avg_drydown": 0.0,
                "avg_overall": 0.0,
            }

        n = len(obs)
        return {
            "avg_opening": sum(o.opening_identity for o in obs) / n,
            "avg_heart": sum(o.heart_identity for o in obs) / n,
            "avg_drydown": sum(o.drydown_identity for o in obs) / n,
            "avg_overall": sum(o.overall_similarity for o in obs) / n,
        }

    def detect_mismatch(
        self,
        candidate_id: str,
        reference_id: str,
        threshold: float = 1.0,
    ) -> list[str]:
        """Detect time points where a candidate differs significantly from the
        reference.

        For each time point that has observations for *both* the candidate and
        the reference, the mean ``overall_similarity`` is compared. If the
        absolute difference exceeds ``threshold``, that time point is flagged.

        Parameters
        ----------
        candidate_id:
            ``sample_id`` of the candidate sample.
        reference_id:
            ``sample_id`` of the reference sample.
        threshold:
            Maximum allowed mean difference before a mismatch is reported.

        Returns
        -------
        list[str]:
            Human-readable descriptions of mismatched time points.
        """
        mismatches: list[str] = []

        for tp in TIME_POINTS:
            cand_obs = [
                o
                for o in self._observations
                if o.sample_id == candidate_id and o.time_seconds == tp
            ]
            ref_obs = [
                o
                for o in self._observations
                if o.sample_id == reference_id and o.time_seconds == tp
            ]
            if not cand_obs or not ref_obs:
                continue

            cand_mean = sum(o.overall_similarity for o in cand_obs) / len(cand_obs)
            ref_mean = sum(o.overall_similarity for o in ref_obs) / len(ref_obs)

            if abs(cand_mean - ref_mean) > threshold:
                mismatches.append(
                    f"t={tp:.0f}s: candidate={cand_mean:.2f} vs "
                    f"reference={ref_mean:.2f} (diff={abs(cand_mean - ref_mean):.2f})"
                )

        return mismatches

    # ── serialisation ───────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialise the entire trial to a JSON-compatible dict."""
        return {
            "trial_name": self.trial_name,
            "reference_sample_id": self.reference_sample_id,
            "assessors": self.assessors,
            "samples": [s.as_dict() for s in self._samples.values()],
            "observations": [o.as_dict() for o in self._observations],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SensoryTrial:
        """Reconstruct a trial from a dict produced by :meth:`to_dict`."""
        return cls.from_records(
            trial_name=str(data["trial_name"]),
            reference_sample_id=str(data["reference_sample_id"]),
            assessors=list(str(a) for a in data.get("assessors", [])),
            samples=[
                SensorySample.from_dict(sample)
                for sample in data.get("samples", [])
            ],
            observations=[
                SensoryObservation.from_dict(observation)
                for observation in data.get("observations", [])
            ],
        )

    @classmethod
    def from_records(
        cls,
        *,
        trial_name: str,
        reference_sample_id: str,
        assessors: list[str],
        samples: list[SensorySample],
        observations: list[SensoryObservation],
    ) -> SensoryTrial:
        """Hydrate a read-only projection without invoking public mutators."""
        trial = cls(trial_name, reference_sample_id, assessors)
        trial._samples = {sample.sample_id: sample for sample in samples}
        trial._observations = list(observations)
        return trial


__all__ = [
    "TIME_POINTS",
    "AssessorReliabilityState",
    "AssessorReliabilitySummary",
    "ObservationCellKey",
    "SensorySample",
    "SensoryObservation",
    "SensorySafetyEvent",
    "SensoryProtocolScope",
    "SensoryTrial",
    "TemporalEndpointSummary",
    "TemporalEvidenceAuditResultV2",
    "TemporalEvidenceDisposition",
    "TemporalEvidenceRequest",
    "TemporalEvidenceResult",
    "TemporalEvidenceState",
    "TemporalObservationCell",
    "TemporalTransition",
    "analyze_temporal_evidence",
    "audit_temporal_evidence",
    "generate_trial_codes",
]
