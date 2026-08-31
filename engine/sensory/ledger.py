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
from typing import Any, ClassVar, Mapping

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


# ── V3 paired trajectories and realized order ──────────────────────────────────


TEMPORAL_V3_AUTHORITY_FLAGS = {
    "compounding": False,
    "formula": False,
    "hedonic": False,
    "physical_execution": False,
    "purchase": False,
    "release": False,
    "safety": False,
    "sensory": False,
}


class TemporalMeasurementMode(str, Enum):
    """Declared observation semantics; modes cannot be silently interchanged."""

    DISCRETE_RATING = "DISCRETE_RATING"
    TDS_DOMINANCE = "TDS_DOMINANCE"
    TCATA_ATTRIBUTE = "TCATA_ATTRIBUTE"


class TemporalContrastDirection(str, Enum):
    LEFT_GREATER = "LEFT_GREATER"
    RIGHT_GREATER = "RIGHT_GREATER"
    EITHER = "EITHER"


class TemporalContrastOutcome(str, Enum):
    SUPPORTED = "SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    INCOMPLETE = "INCOMPLETE"


class RealizedOrderState(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PASS = "PASS"
    HOLD = "HOLD"


def _v3_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be boolean")
    return value


def _v3_positive_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 1:
        raise ValueError(f"{field_name} must be positive")
    return value


def _v3_nonnegative(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric")
    result = float(value)
    if not isfinite(result) or result < 0:
        raise ValueError(f"{field_name} must be finite and nonnegative")
    return result


def _v3_fraction(value: object, field_name: str) -> float:
    result = _v3_nonnegative(value, field_name)
    if result < 0.5 or result > 1:
        raise ValueError(f"{field_name} must be from 0.5 through 1")
    return result


def _v3_text_tuple(
    value: object,
    field_name: str,
    *,
    minimum: int = 1,
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{field_name} must be a sequence")
    result = tuple(_required_text(item, field_name) for item in value)
    if len(result) < minimum:
        raise ValueError(f"{field_name} requires at least {minimum} values")
    if len(result) != len(set(result)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


@dataclass(frozen=True, slots=True)
class RealizedPresentationAssignment:
    """Observed assessor/repeat sequence, distinct from a planned schedule."""

    assessor_id: str
    repeat_id: str
    sequence_id: str
    ordered_sample_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("assessor_id", "repeat_id", "sequence_id"):
            object.__setattr__(
                self,
                name,
                _required_text(getattr(self, name), name),
            )
        object.__setattr__(
            self,
            "ordered_sample_ids",
            _v3_text_tuple(
                self.ordered_sample_ids,
                "ordered_sample_ids",
                minimum=2,
            ),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "assessor_id": self.assessor_id,
            "repeat_id": self.repeat_id,
            "sequence_id": self.sequence_id,
            "ordered_sample_ids": list(self.ordered_sample_ids),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> RealizedPresentationAssignment:
        if not isinstance(value, Mapping):
            raise TypeError("realized assignment must be a mapping")
        fields = {"assessor_id", "repeat_id", "sequence_id", "ordered_sample_ids"}
        if set(value) != fields:
            raise ValueError("realized assignment fields must match the closed schema")
        ordered = value["ordered_sample_ids"]
        if not isinstance(ordered, (list, tuple)):
            raise TypeError("ordered_sample_ids must be a sequence")
        return cls(
            assessor_id=_required_text(value["assessor_id"], "assessor_id"),
            repeat_id=_required_text(value["repeat_id"], "repeat_id"),
            sequence_id=_required_text(value["sequence_id"], "sequence_id"),
            ordered_sample_ids=tuple(ordered),
        )

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))


@dataclass(frozen=True, slots=True)
class TemporalContrastSpecV3:
    """One predeclared paired difference-in-change decision."""

    contrast_id: str
    left_sample_id: str
    right_sample_id: str
    endpoint_id: str
    from_time_seconds: float
    to_time_seconds: float
    direction: TemporalContrastDirection
    minimum_absolute_median_difference_in_change: float
    minimum_directional_agreement_fraction: float

    def __post_init__(self) -> None:
        for name in (
            "contrast_id",
            "left_sample_id",
            "right_sample_id",
            "endpoint_id",
        ):
            object.__setattr__(
                self,
                name,
                _required_text(getattr(self, name), name),
            )
        if self.left_sample_id == self.right_sample_id:
            raise ValueError("a temporal contrast requires two distinct samples")
        for name in ("from_time_seconds", "to_time_seconds"):
            value = _v3_nonnegative(getattr(self, name), name)
            object.__setattr__(self, name, value)
        if self.from_time_seconds >= self.to_time_seconds:
            raise ValueError("from_time_seconds must precede to_time_seconds")
        object.__setattr__(
            self,
            "direction",
            TemporalContrastDirection(self.direction),
        )
        object.__setattr__(
            self,
            "minimum_absolute_median_difference_in_change",
            _v3_nonnegative(
                self.minimum_absolute_median_difference_in_change,
                "minimum_absolute_median_difference_in_change",
            ),
        )
        object.__setattr__(
            self,
            "minimum_directional_agreement_fraction",
            _v3_fraction(
                self.minimum_directional_agreement_fraction,
                "minimum_directional_agreement_fraction",
            ),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "contrast_id": self.contrast_id,
            "left_sample_id": self.left_sample_id,
            "right_sample_id": self.right_sample_id,
            "endpoint_id": self.endpoint_id,
            "from_time_seconds": self.from_time_seconds,
            "to_time_seconds": self.to_time_seconds,
            "direction": self.direction.value,
            "minimum_absolute_median_difference_in_change": (
                self.minimum_absolute_median_difference_in_change
            ),
            "minimum_directional_agreement_fraction": (
                self.minimum_directional_agreement_fraction
            ),
        }


@dataclass(frozen=True, slots=True)
class TemporalAnalysisPlanV3:
    """Frozen temporal question; completeness alone cannot resolve it."""

    analysis_id: str
    criterion_id: str
    measurement_mode: TemporalMeasurementMode
    minimum_paired_trajectory_count: int
    require_realized_order: bool
    require_complete_grid: bool
    contrasts: tuple[TemporalContrastSpecV3, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "analysis_id",
            _required_text(self.analysis_id, "analysis_id"),
        )
        object.__setattr__(
            self,
            "criterion_id",
            _required_text(self.criterion_id, "criterion_id").upper(),
        )
        object.__setattr__(
            self,
            "measurement_mode",
            TemporalMeasurementMode(self.measurement_mode),
        )
        object.__setattr__(
            self,
            "minimum_paired_trajectory_count",
            _v3_positive_int(
                self.minimum_paired_trajectory_count,
                "minimum_paired_trajectory_count",
            ),
        )
        for name in ("require_realized_order", "require_complete_grid"):
            object.__setattr__(self, name, _v3_bool(getattr(self, name), name))
        contrasts = tuple(self.contrasts)
        if not contrasts or any(
            not isinstance(item, TemporalContrastSpecV3) for item in contrasts
        ):
            raise TypeError("contrasts must contain TemporalContrastSpecV3 records")
        contrast_ids = tuple(item.contrast_id for item in contrasts)
        if len(contrast_ids) != len(set(contrast_ids)):
            raise ValueError("contrast_id values must be unique")
        object.__setattr__(self, "contrasts", contrasts)
        object.__setattr__(
            self,
            "evidence_refs",
            _v3_text_tuple(self.evidence_refs, "evidence_refs"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": "temporal_analysis_plan_v3",
            "analysis_id": self.analysis_id,
            "criterion_id": self.criterion_id,
            "measurement_mode": self.measurement_mode.value,
            "minimum_paired_trajectory_count": self.minimum_paired_trajectory_count,
            "require_realized_order": self.require_realized_order,
            "require_complete_grid": self.require_complete_grid,
            "contrasts": [item.as_dict() for item in self.contrasts],
            "evidence_refs": list(self.evidence_refs),
            "authority_flags": dict(TEMPORAL_V3_AUTHORITY_FLAGS),
        }

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))


def _temporal_request_v3_parent_payload(
    parent: TemporalEvidenceRequest,
) -> dict[str, object]:
    return {
        "scope": _scope_payload(parent.scope),
        "schedule": parent.schedule.as_dict(),
        "cells": [
            cell.as_dict()
            for cell in sorted(
                parent.cells,
                key=lambda item: (
                    item.key,
                    item.observation_id,
                    item.presentation_sequence_id,
                ),
            )
        ],
        "safety_events": [
            event.as_dict()
            for event in sorted(parent.safety_events, key=lambda item: item.event_id)
        ],
    }


@dataclass(frozen=True, slots=True)
class TemporalEvidenceRequestV3:
    parent: TemporalEvidenceRequest
    analysis_plan: TemporalAnalysisPlanV3
    realized_assignments: tuple[RealizedPresentationAssignment, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.parent, TemporalEvidenceRequest):
            raise TypeError("parent must be a TemporalEvidenceRequest")
        if not isinstance(self.analysis_plan, TemporalAnalysisPlanV3):
            raise TypeError("analysis_plan must be a TemporalAnalysisPlanV3")
        assignments = tuple(self.realized_assignments)
        if any(
            not isinstance(item, RealizedPresentationAssignment)
            for item in assignments
        ):
            raise TypeError(
                "realized_assignments must contain RealizedPresentationAssignment records"
            )
        keys = tuple((item.assessor_id, item.repeat_id) for item in assignments)
        if len(keys) != len(set(keys)):
            raise ValueError("realized assignments must be unique by assessor and repeat")
        object.__setattr__(self, "realized_assignments", assignments)
        scope = self.parent.scope
        if self.analysis_plan.measurement_mode in {
            TemporalMeasurementMode.TDS_DOMINANCE,
            TemporalMeasurementMode.TCATA_ATTRIBUTE,
        } and len(scope.endpoint_ids) < 2:
            raise ValueError("TDS and TCATA require at least two declared attributes")
        for contrast in self.analysis_plan.contrasts:
            if not {contrast.left_sample_id, contrast.right_sample_id}.issubset(
                scope.sample_ids
            ):
                raise ValueError("temporal contrast sample is outside protocol scope")
            if contrast.endpoint_id not in scope.endpoint_ids:
                raise ValueError("temporal contrast endpoint is outside protocol scope")
            if contrast.from_time_seconds not in scope.timepoints_seconds or (
                contrast.to_time_seconds not in scope.timepoints_seconds
            ):
                raise ValueError("temporal contrast timepoint is outside protocol scope")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": "temporal_evidence_request_v3",
            "parent": _temporal_request_v3_parent_payload(self.parent),
            "analysis_plan": self.analysis_plan.as_dict(),
            "realized_assignments": [
                item.as_dict()
                for item in sorted(
                    self.realized_assignments,
                    key=lambda assignment: (
                        assignment.assessor_id,
                        assignment.repeat_id,
                    ),
                )
            ],
            "authority_flags": dict(TEMPORAL_V3_AUTHORITY_FLAGS),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())


@dataclass(frozen=True, slots=True)
class RealizedOrderDiagnosticV3:
    state: RealizedOrderState
    sequence_counts: tuple[tuple[str, int], ...]
    first_position_counts: tuple[tuple[str, int], ...]
    adjacent_pair_counts: tuple[tuple[str, int], ...]
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "sequence_counts": dict(self.sequence_counts),
            "first_position_counts": dict(self.first_position_counts),
            "adjacent_pair_counts": dict(self.adjacent_pair_counts),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True, slots=True)
class PairedTemporalTransitionV3:
    sample_id: str
    endpoint_id: str
    from_time_seconds: float
    to_time_seconds: float
    paired_count: int
    median_change: float
    first_quartile: float
    third_quartile: float
    median_absolute_deviation: float
    positive_count: int
    negative_count: int
    tie_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "sample_id": self.sample_id,
            "endpoint_id": self.endpoint_id,
            "from_time_seconds": self.from_time_seconds,
            "to_time_seconds": self.to_time_seconds,
            "paired_count": self.paired_count,
            "median_change": self.median_change,
            "first_quartile": self.first_quartile,
            "third_quartile": self.third_quartile,
            "median_absolute_deviation": self.median_absolute_deviation,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "tie_count": self.tie_count,
        }


@dataclass(frozen=True, slots=True)
class TemporalContrastResultV3:
    contrast_id: str
    outcome: TemporalContrastOutcome
    paired_count: int
    median_difference_in_change: float | None
    first_quartile: float | None
    third_quartile: float | None
    median_absolute_deviation: float | None
    positive_count: int
    negative_count: int
    tie_count: int
    directional_agreement_fraction: float | None
    from_time_median_left_minus_right: float | None
    to_time_median_left_minus_right: float | None
    crossover_observed: bool | None

    def as_dict(self) -> dict[str, object]:
        return {
            "contrast_id": self.contrast_id,
            "outcome": self.outcome.value,
            "paired_count": self.paired_count,
            "median_difference_in_change": self.median_difference_in_change,
            "first_quartile": self.first_quartile,
            "third_quartile": self.third_quartile,
            "median_absolute_deviation": self.median_absolute_deviation,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "tie_count": self.tie_count,
            "directional_agreement_fraction": self.directional_agreement_fraction,
            "from_time_median_left_minus_right": (
                self.from_time_median_left_minus_right
            ),
            "to_time_median_left_minus_right": self.to_time_median_left_minus_right,
            "crossover_observed": self.crossover_observed,
        }


@dataclass(frozen=True, slots=True)
class TemporalAttributeRateV3:
    sample_id: str
    endpoint_id: str
    time_seconds: float
    measurement_mode: TemporalMeasurementMode
    observed_count: int
    active_count: int
    activation_rate: float

    def as_dict(self) -> dict[str, object]:
        return {
            "sample_id": self.sample_id,
            "endpoint_id": self.endpoint_id,
            "time_seconds": self.time_seconds,
            "measurement_mode": self.measurement_mode.value,
            "observed_count": self.observed_count,
            "active_count": self.active_count,
            "activation_rate": self.activation_rate,
        }


@dataclass(frozen=True, slots=True)
class TemporalEvidenceResultV3:
    SCHEMA_VERSION: ClassVar[str] = "temporal_evidence_result_v3"

    state: TemporalEvidenceState
    request_sha256: str
    parent_v2: TemporalEvidenceAuditResultV2
    realized_order: RealizedOrderDiagnosticV3
    paired_transitions: tuple[PairedTemporalTransitionV3, ...]
    contrasts: tuple[TemporalContrastResultV3, ...]
    attribute_rates: tuple[TemporalAttributeRateV3, ...]
    blockers: tuple[str, ...]
    next_discriminator: str | None
    receipt: EvidenceDeltaReceiptV1
    interpolated_cell_count: int = field(default=0, init=False)

    @property
    def realized_order_state(self) -> RealizedOrderState:
        return self.realized_order.state

    @property
    def authority_flags(self) -> dict[str, bool]:
        return dict(TEMPORAL_V3_AUTHORITY_FLAGS)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "state": self.state.value,
            "request_sha256": self.request_sha256,
            "parent_v2": {
                "disposition": self.parent_v2.disposition.value,
                "receipt_sha256": self.parent_v2.receipt.receipt_sha256,
                "source_cell_count": self.parent_v2.source_cell_count,
                "excluded_duplicate_row_count": (
                    self.parent_v2.excluded_duplicate_row_count
                ),
                "missing_cells": [
                    _cell_key_payload(item) for item in self.parent_v2.missing_cells
                ],
                "duplicate_cells": [
                    _cell_key_payload(item) for item in self.parent_v2.duplicate_cells
                ],
            },
            "realized_order": self.realized_order.as_dict(),
            "paired_transitions": [
                item.as_dict() for item in self.paired_transitions
            ],
            "contrasts": [item.as_dict() for item in self.contrasts],
            "attribute_rates": [item.as_dict() for item in self.attribute_rates],
            "blockers": list(self.blockers),
            "next_discriminator": self.next_discriminator,
            "receipt": self.receipt.as_dict(),
            "interpolated_cell_count": self.interpolated_cell_count,
            "authority_flags": self.authority_flags,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())


def _v3_distribution(values: list[float]) -> tuple[float, float, float, float]:
    ordered = sorted(values)
    middle = float(median(ordered))
    lower = (
        float(median(ordered[: len(ordered) // 2]))
        if len(ordered) > 1
        else middle
    )
    upper_start = (len(ordered) + 1) // 2
    upper = (
        float(median(ordered[upper_start:]))
        if len(ordered) > 1
        else middle
    )
    mad = float(median([abs(value - middle) for value in ordered]))
    return middle, lower, upper, mad


def _v3_unique_cell_values(
    request: TemporalEvidenceRequest,
) -> dict[ObservationCellKey, float]:
    counts = Counter(cell.key for cell in request.cells)
    return {
        cell.key: cell.value
        for cell in request.cells
        if counts[cell.key] == 1
    }


def _v3_realized_order(
    request: TemporalEvidenceRequestV3,
) -> RealizedOrderDiagnosticV3:
    scope = request.parent.scope
    schedule = request.parent.schedule
    assignments = {
        (item.assessor_id, item.repeat_id): item
        for item in request.realized_assignments
    }
    expected_keys = {
        (assessor_id, repeat_id)
        for assessor_id in scope.assessor_ids
        for repeat_id in scope.repeat_ids
    }
    blockers: list[str] = []
    if request.analysis_plan.require_realized_order and set(assignments) != expected_keys:
        blockers.append("REALIZED_ASSIGNMENT_SET_INCOMPLETE")

    sequence_index = {
        tuple(sequence): f"SCHEDULE_SEQUENCE_{index:03d}"
        for index, sequence in enumerate(schedule.sequences, start=1)
    }
    sequence_counts = Counter({identifier: 0 for identifier in sequence_index.values()})
    first_counts = Counter({sample_id: 0 for sample_id in scope.sample_ids})
    adjacent_counts = Counter(
        {
            f"{left}->{right}": 0
            for left in scope.sample_ids
            for right in scope.sample_ids
            if left != right
        }
    )
    for assignment in request.realized_assignments:
        ordered = assignment.ordered_sample_ids
        if set(ordered) != set(scope.sample_ids) or len(ordered) != len(scope.sample_ids):
            blockers.append("REALIZED_SEQUENCE_SAMPLE_SET_MISMATCH")
            continue
        identifier = sequence_index.get(ordered)
        if identifier is None:
            blockers.append("REALIZED_SEQUENCE_NOT_IN_FROZEN_SCHEDULE")
            continue
        sequence_counts[identifier] += 1
        first_counts[ordered[0]] += 1
        adjacent_counts.update(
            f"{left}->{right}" for left, right in zip(ordered, ordered[1:])
        )

    if request.analysis_plan.require_realized_order and sequence_counts:
        values = tuple(sequence_counts.values())
        if max(values) - min(values) > 1:
            blockers.append("REALIZED_SEQUENCE_COUNTS_UNBALANCED")

    for cell in request.parent.cells:
        realized_assignment = assignments.get(
            (cell.key.assessor_id, cell.key.repeat_id)
        )
        if realized_assignment is None:
            if request.analysis_plan.require_realized_order:
                blockers.append("OBSERVATION_WITHOUT_REALIZED_ASSIGNMENT")
            continue
        if cell.presentation_sequence_id != realized_assignment.sequence_id:
            blockers.append("OBSERVATION_SEQUENCE_ID_MISMATCH")
        try:
            expected_position = (
                realized_assignment.ordered_sample_ids.index(cell.key.sample_id) + 1
            )
        except ValueError:
            blockers.append("OBSERVATION_SAMPLE_NOT_IN_REALIZED_SEQUENCE")
        else:
            if cell.presentation_position != expected_position:
                blockers.append("OBSERVATION_POSITION_MISMATCH")

    unique_blockers = tuple(sorted(set(blockers)))
    state = (
        RealizedOrderState.HOLD
        if unique_blockers
        else RealizedOrderState.PASS
        if request.analysis_plan.require_realized_order
        else RealizedOrderState.NOT_REQUIRED
    )
    return RealizedOrderDiagnosticV3(
        state=state,
        sequence_counts=tuple(sorted(sequence_counts.items())),
        first_position_counts=tuple(sorted(first_counts.items())),
        adjacent_pair_counts=tuple(sorted(adjacent_counts.items())),
        blockers=unique_blockers,
    )


def _v3_mode_audit(
    request: TemporalEvidenceRequestV3,
) -> tuple[tuple[TemporalAttributeRateV3, ...], tuple[str, ...]]:
    mode = request.analysis_plan.measurement_mode
    if mode is TemporalMeasurementMode.DISCRETE_RATING:
        return (), ()
    counts = Counter(cell.key for cell in request.parent.cells)
    safe_cells = tuple(
        cell for cell in request.parent.cells if counts[cell.key] == 1
    )
    blockers: list[str] = []
    if any(cell.value not in {0.0, 1.0} for cell in safe_cells):
        blockers.append("DYNAMIC_ATTRIBUTE_VALUES_MUST_BE_BINARY")
    grouped: dict[tuple[str, str, float, str], list[float]] = defaultdict(list)
    trajectory_groups: dict[tuple[str, str, str, float], dict[str, float]] = defaultdict(dict)
    for cell in safe_cells:
        grouped[
            (
                cell.key.sample_id,
                cell.key.endpoint_id,
                cell.key.time_seconds,
                mode.value,
            )
        ].append(cell.value)
        trajectory_groups[
            (
                cell.key.sample_id,
                cell.key.assessor_id,
                cell.key.repeat_id,
                cell.key.time_seconds,
            )
        ][cell.key.endpoint_id] = cell.value
    if mode is TemporalMeasurementMode.TDS_DOMINANCE:
        endpoint_set = set(request.parent.scope.endpoint_ids)
        for endpoint_values in trajectory_groups.values():
            if set(endpoint_values) == endpoint_set and sum(endpoint_values.values()) != 1:
                blockers.append("TDS_REQUIRES_EXACTLY_ONE_DOMINANT_ATTRIBUTE")
                break
    rates = tuple(
        TemporalAttributeRateV3(
            sample_id=key[0],
            endpoint_id=key[1],
            time_seconds=key[2],
            measurement_mode=TemporalMeasurementMode(key[3]),
            observed_count=len(values),
            active_count=sum(int(value == 1.0) for value in values),
            activation_rate=(
                sum(int(value == 1.0) for value in values) / len(values)
            ),
        )
        for key, values in sorted(grouped.items())
    )
    return rates, tuple(sorted(set(blockers)))


def _v3_paired_transitions(
    request: TemporalEvidenceRequestV3,
) -> tuple[PairedTemporalTransitionV3, ...]:
    scope = request.parent.scope
    values = _v3_unique_cell_values(request.parent)
    summaries: list[PairedTemporalTransitionV3] = []
    for sample_id in scope.sample_ids:
        for endpoint_id in scope.endpoint_ids:
            for left_time, right_time in zip(
                scope.timepoints_seconds,
                scope.timepoints_seconds[1:],
            ):
                deltas: list[float] = []
                for assessor_id in scope.assessor_ids:
                    for repeat_id in scope.repeat_ids:
                        left_key = ObservationCellKey(
                            scope.protocol_id,
                            sample_id,
                            assessor_id,
                            repeat_id,
                            left_time,
                            endpoint_id,
                        )
                        right_key = ObservationCellKey(
                            scope.protocol_id,
                            sample_id,
                            assessor_id,
                            repeat_id,
                            right_time,
                            endpoint_id,
                        )
                        if left_key in values and right_key in values:
                            deltas.append(values[right_key] - values[left_key])
                if deltas:
                    middle, lower, upper, mad = _v3_distribution(deltas)
                    summaries.append(
                        PairedTemporalTransitionV3(
                            sample_id=sample_id,
                            endpoint_id=endpoint_id,
                            from_time_seconds=left_time,
                            to_time_seconds=right_time,
                            paired_count=len(deltas),
                            median_change=middle,
                            first_quartile=lower,
                            third_quartile=upper,
                            median_absolute_deviation=mad,
                            positive_count=sum(value > 0 for value in deltas),
                            negative_count=sum(value < 0 for value in deltas),
                            tie_count=sum(value == 0 for value in deltas),
                        )
                    )
    return tuple(summaries)


def _v3_contrast_result(
    request: TemporalEvidenceRequestV3,
    spec: TemporalContrastSpecV3,
) -> TemporalContrastResultV3:
    scope = request.parent.scope
    values = _v3_unique_cell_values(request.parent)
    differences_in_change: list[float] = []
    from_differences: list[float] = []
    to_differences: list[float] = []
    for assessor_id in scope.assessor_ids:
        for repeat_id in scope.repeat_ids:
            keys = tuple(
                ObservationCellKey(
                    scope.protocol_id,
                    sample_id,
                    assessor_id,
                    repeat_id,
                    timepoint,
                    spec.endpoint_id,
                )
                for sample_id, timepoint in (
                    (spec.left_sample_id, spec.from_time_seconds),
                    (spec.left_sample_id, spec.to_time_seconds),
                    (spec.right_sample_id, spec.from_time_seconds),
                    (spec.right_sample_id, spec.to_time_seconds),
                )
            )
            if all(key in values for key in keys):
                left_from, left_to, right_from, right_to = (
                    values[key] for key in keys
                )
                from_difference = left_from - right_from
                to_difference = left_to - right_to
                from_differences.append(from_difference)
                to_differences.append(to_difference)
                differences_in_change.append(to_difference - from_difference)

    paired_count = len(differences_in_change)
    positive_count = sum(value > 0 for value in differences_in_change)
    negative_count = sum(value < 0 for value in differences_in_change)
    tie_count = sum(value == 0 for value in differences_in_change)
    if not differences_in_change:
        return TemporalContrastResultV3(
            contrast_id=spec.contrast_id,
            outcome=TemporalContrastOutcome.INCOMPLETE,
            paired_count=0,
            median_difference_in_change=None,
            first_quartile=None,
            third_quartile=None,
            median_absolute_deviation=None,
            positive_count=0,
            negative_count=0,
            tie_count=0,
            directional_agreement_fraction=None,
            from_time_median_left_minus_right=None,
            to_time_median_left_minus_right=None,
            crossover_observed=None,
        )

    middle, lower, upper, mad = _v3_distribution(differences_in_change)
    from_middle = float(median(from_differences))
    to_middle = float(median(to_differences))
    crossover = (from_middle < 0 < to_middle) or (from_middle > 0 > to_middle)
    if spec.direction is TemporalContrastDirection.LEFT_GREATER:
        direction_supported = middle >= (
            spec.minimum_absolute_median_difference_in_change
        )
        supporting_count = positive_count
    elif spec.direction is TemporalContrastDirection.RIGHT_GREATER:
        direction_supported = middle <= -(
            spec.minimum_absolute_median_difference_in_change
        )
        supporting_count = negative_count
    elif middle > 0:
        direction_supported = middle >= (
            spec.minimum_absolute_median_difference_in_change
        )
        supporting_count = positive_count
    elif middle < 0:
        direction_supported = middle <= -(
            spec.minimum_absolute_median_difference_in_change
        )
        supporting_count = negative_count
    else:
        direction_supported = (
            spec.minimum_absolute_median_difference_in_change == 0
        )
        supporting_count = tie_count
    agreement = supporting_count / paired_count
    if paired_count < request.analysis_plan.minimum_paired_trajectory_count:
        outcome = TemporalContrastOutcome.INCOMPLETE
    elif (
        direction_supported
        and agreement >= spec.minimum_directional_agreement_fraction
    ):
        outcome = TemporalContrastOutcome.SUPPORTED
    else:
        outcome = TemporalContrastOutcome.NOT_SUPPORTED
    return TemporalContrastResultV3(
        contrast_id=spec.contrast_id,
        outcome=outcome,
        paired_count=paired_count,
        median_difference_in_change=middle,
        first_quartile=lower,
        third_quartile=upper,
        median_absolute_deviation=mad,
        positive_count=positive_count,
        negative_count=negative_count,
        tie_count=tie_count,
        directional_agreement_fraction=agreement,
        from_time_median_left_minus_right=from_middle,
        to_time_median_left_minus_right=to_middle,
        crossover_observed=crossover,
    )


_TEMPORAL_V3_POLICY_SHA256 = sha256_hex(
    canonical_json_bytes(
        {
            "policy": "TEMPORAL_PAIRED_TRAJECTORY_REALIZED_ORDER_V3",
            "change": "WITHIN_ASSESSOR_REPEAT_PAIRED",
            "sample_contrast": "DIFFERENCE_IN_CHANGE",
            "order": "REALIZED_NOT_DESIGN_INFERRED",
            "dynamic_modes": ("TDS_DOMINANCE", "TCATA_ATTRIBUTE"),
            "missing": "NO_INTERPOLATION",
            "selection": "ZERO_OR_ONE_NEXT_ACTION",
        }
    )
)


def analyze_temporal_evidence_v3(
    request: TemporalEvidenceRequestV3,
) -> TemporalEvidenceResultV3:
    """Analyze paired observed trajectories and realized order without interpolation."""

    if not isinstance(request, TemporalEvidenceRequestV3):
        raise TypeError("request must be a TemporalEvidenceRequestV3")
    parent_v2 = audit_temporal_evidence(request.parent)
    realized = _v3_realized_order(request)
    attribute_rates, mode_blockers = _v3_mode_audit(request)
    paired_transitions = _v3_paired_transitions(request)
    contrasts = tuple(
        _v3_contrast_result(request, item)
        for item in request.analysis_plan.contrasts
    )
    blockers = tuple(sorted(set((*realized.blockers, *mode_blockers))))

    parent_hold = parent_v2.disposition in {
        TemporalEvidenceDisposition.CONFLICTED,
        TemporalEvidenceDisposition.PROTOCOL_HOLD,
    }
    parent_incomplete = parent_v2.disposition in {
        TemporalEvidenceDisposition.INCOMPLETE,
        TemporalEvidenceDisposition.INSUFFICIENT_SCOPE,
    }
    contrast_incomplete = any(
        item.outcome is TemporalContrastOutcome.INCOMPLETE for item in contrasts
    )
    if parent_hold or blockers:
        state = TemporalEvidenceState.HOLD
    elif parent_incomplete or (
        request.analysis_plan.require_complete_grid and parent_v2.missing_cells
    ) or contrast_incomplete:
        state = TemporalEvidenceState.INCOMPLETE
    else:
        state = TemporalEvidenceState.COMPLETE

    next_discriminator: str | None
    if state is TemporalEvidenceState.HOLD:
        if realized.blockers:
            next_discriminator = "REPAIR_REALIZED_PRESENTATION_ORDER"
        elif mode_blockers:
            next_discriminator = "CORRECT_TEMPORAL_MEASUREMENT_MODE"
        else:
            next_discriminator = parent_v2.next_discriminator
    elif state is TemporalEvidenceState.INCOMPLETE:
        if parent_v2.next_discriminator is not None:
            next_discriminator = parent_v2.next_discriminator
        else:
            incomplete = next(
                item
                for item in contrasts
                if item.outcome is TemporalContrastOutcome.INCOMPLETE
            )
            next_discriminator = (
                f"EXPAND_PAIRED_TRAJECTORY_SCOPE:{incomplete.contrast_id}"
            )
    else:
        next_discriminator = None

    realized_sha256 = sha256_hex(canonical_json_bytes(realized.as_dict()))
    source_bindings = tuple(
        sorted(
            {
                parent_v2.receipt.receipt_sha256,
                request.analysis_plan.record_sha256,
                realized_sha256,
                request.record_sha256,
            }
        )
    )
    reason_codes = {
        TemporalEvidenceState.COMPLETE: ("PAIRED_TEMPORAL_DECISION_COMPLETE",),
        TemporalEvidenceState.INCOMPLETE: ("PAIRED_TEMPORAL_EVIDENCE_INCOMPLETE",),
        TemporalEvidenceState.HOLD: ("PAIRED_TEMPORAL_PROTOCOL_HOLD",),
    }[state]
    receipt_blockers = tuple(
        dict.fromkeys(
            (
                *blockers,
                *parent_v2.receipt.blockers,
                *(
                    ("PAIRED_TRAJECTORY_COUNT_INSUFFICIENT",)
                    if contrast_incomplete
                    else ()
                ),
            )
        )
    )
    exact_scope = (
        f"{request.parent.scope.protocol_id}/TEMPORAL/"
        f"{request.analysis_plan.criterion_id}"
    )
    if state is TemporalEvidenceState.COMPLETE:
        delta = DecisionDeltaV1(
            delta_id=f"TEMPORAL-V3:{request.analysis_plan.analysis_id}",
            decision_effect=(
                "Use only the observed paired transition and contrast results at "
                "this exact protocol and criterion scope."
            ),
            observed_facts=(
                f"source_cells={len(request.parent.cells)}",
                f"paired_transitions={len(paired_transitions)}",
                f"declared_contrasts={len(contrasts)}",
                f"realized_order={realized.state.value}",
            ),
            derived_calculations=tuple(
                f"{item.contrast_id}={item.outcome.value};pairs={item.paired_count}"
                for item in contrasts
            ),
            hypotheses=(),
            forbidden_inferences=(
                "Observed trajectories do not establish formula-derived perception or liking.",
                "TDS and TCATA summaries remain method-specific and are not interchangeable.",
                "No missing observation was interpolated.",
            ),
        )
        receipt = EvidenceDeltaReceiptV1(
            module_id="temporal_sensory_ledger_v3",
            exact_scope=exact_scope,
            state=EvidenceAugmentationState.AUGMENT,
            input_sha256=request.record_sha256,
            evidence_sha256=parent_v2.receipt.evidence_sha256,
            policy_sha256=_TEMPORAL_V3_POLICY_SHA256,
            source_binding_sha256=source_bindings,
            reason_codes=reason_codes,
            delta=delta,
            blockers=(),
            next_action=None,
        )
    else:
        receipt = hold_receipt(
            module_id="temporal_sensory_ledger_v3",
            exact_scope=exact_scope,
            input_sha256=request.record_sha256,
            evidence_sha256=parent_v2.receipt.evidence_sha256,
            policy_sha256=_TEMPORAL_V3_POLICY_SHA256,
            source_binding_sha256=source_bindings,
            reasons=reason_codes,
            blockers=receipt_blockers,
            next_action=next_discriminator,
        )
    return TemporalEvidenceResultV3(
        state=state,
        request_sha256=request.record_sha256,
        parent_v2=parent_v2,
        realized_order=realized,
        paired_transitions=paired_transitions,
        contrasts=contrasts,
        attribute_rates=attribute_rates,
        blockers=tuple(dict.fromkeys((*blockers, *parent_v2.receipt.blockers))),
        next_discriminator=next_discriminator,
        receipt=receipt,
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
    "TEMPORAL_V3_AUTHORITY_FLAGS",
    "AssessorReliabilityState",
    "AssessorReliabilitySummary",
    "ObservationCellKey",
    "PairedTemporalTransitionV3",
    "RealizedOrderDiagnosticV3",
    "RealizedOrderState",
    "RealizedPresentationAssignment",
    "SensorySample",
    "SensoryObservation",
    "SensorySafetyEvent",
    "SensoryProtocolScope",
    "SensoryTrial",
    "TemporalAnalysisPlanV3",
    "TemporalAttributeRateV3",
    "TemporalContrastDirection",
    "TemporalContrastOutcome",
    "TemporalContrastResultV3",
    "TemporalContrastSpecV3",
    "TemporalEndpointSummary",
    "TemporalEvidenceAuditResultV2",
    "TemporalEvidenceDisposition",
    "TemporalEvidenceRequest",
    "TemporalEvidenceRequestV3",
    "TemporalEvidenceResult",
    "TemporalEvidenceResultV3",
    "TemporalEvidenceState",
    "TemporalMeasurementMode",
    "TemporalObservationCell",
    "TemporalTransition",
    "analyze_temporal_evidence",
    "analyze_temporal_evidence_v3",
    "audit_temporal_evidence",
    "generate_trial_codes",
]
