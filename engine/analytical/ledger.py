"""Analytical instrument data ingestion ledger.

Stores GC-MS, HS-SPME-GC-MS, and GC-O results with quality control tracking.
Each run is traceable to instrument parameters, and peaks/events can be
searched by retention index or odor descriptor.

Usage::

    from engine.analytical.ledger import (
        AnalyticalLedger, GCMSRun, GCMSPeak, HSSPMERun, GCOEvent, QualityControls,
    )

    ledger = AnalyticalLedger()
    run = GCMSRun(
        run_id="550e8400-e29b-41d4-a716-446655440000",
        instrument="Agilent 7890B",
        column="DB-5MS 30m x 0.25mm x 0.25um",
        temperature_program="40C(1min)-8C/min-280C(5min)",
        injection_mode="splitless",
        injection_volume_ul=1.0,
    )
    peaks = [
        GCMSPeak(
            peak_id="660e8400-e29b-41d4-a716-446655440001",
            run_id=run.run_id,
            retention_time_min=12.34,
            retention_index=1350.0,
            peak_area=1.23e6,
            tentative_identity="Linalool",
            identity_authority="B",
            match_score=95.0,
        ),
    ]
    ledger.add_gcms_run(run, peaks)
    hits = ledger.search_by_retention_index(1350.0, tolerance=5)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from engine.domain_errors import LegacyWriteProhibitedError

# ── Dataclasses ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class GCMSRun:
    """A single GC-MS instrument run.

    Parameters
    ----------
    run_id:
        UUID string identifying this run.
    instrument:
        Instrument model or identifier (e.g. ``"Agilent 7890B"``).
    column:
        Column specification (e.g. ``"DB-5MS 30m x 0.25mm x 0.25um"``).
    temperature_program:
        Oven temperature program (e.g. ``"40C(1min)-8C/min-280C(5min)"``).
    injection_mode:
        Injection mode (``"split"`` or ``"splitless"``).
    injection_volume_ul:
        Injection volume in microlitres.
    carrier_gas:
        Carrier gas type (default ``"Helium"``).
    flow_rate_ml_min:
        Column flow rate in mL/min (default 1.0).
    internal_standard:
        Name of the internal standard, if used.
    internal_standard_amount_ug:
        Amount of internal standard in micrograms.
    date_run:
        ISO 8601 date string when the run was performed.
    """

    run_id: str
    instrument: str
    column: str
    temperature_program: str
    injection_mode: str
    injection_volume_ul: float
    carrier_gas: str = "Helium"
    flow_rate_ml_min: float = 1.0
    internal_standard: str = ""
    internal_standard_amount_ug: float = 0.0
    date_run: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "instrument": self.instrument,
            "column": self.column,
            "temperature_program": self.temperature_program,
            "injection_mode": self.injection_mode,
            "injection_volume_ul": self.injection_volume_ul,
            "carrier_gas": self.carrier_gas,
            "flow_rate_ml_min": self.flow_rate_ml_min,
            "internal_standard": self.internal_standard,
            "internal_standard_amount_ug": self.internal_standard_amount_ug,
            "date_run": self.date_run,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GCMSRun:
        return cls(
            run_id=str(data["run_id"]),
            instrument=str(data["instrument"]),
            column=str(data["column"]),
            temperature_program=str(data["temperature_program"]),
            injection_mode=str(data["injection_mode"]),
            injection_volume_ul=float(data["injection_volume_ul"]),
            carrier_gas=str(data.get("carrier_gas") or "Helium"),
            flow_rate_ml_min=float(data.get("flow_rate_ml_min") or 1.0),
            internal_standard=str(data.get("internal_standard") or ""),
            internal_standard_amount_ug=float(data.get("internal_standard_amount_ug") or 0.0),
            date_run=str(data.get("date_run") or ""),
        )


@dataclass(frozen=True, slots=True)
class GCMSPeak:
    """A single peak detected in a GC-MS run.

    Parameters
    ----------
    peak_id:
        UUID string identifying this peak.
    run_id:
        UUID string referencing the :class:`GCMSRun`.
    retention_time_min:
        Retention time in minutes.
    retention_index:
        Calculated or calibrated retention index (e.g. Kovats, linear).
        ``None`` if not calculated.
    peak_area:
        Integrated peak area (arbitrary units).
    response_factor:
        Response factor relative to internal standard (default 1.0).
    qualifier_ions:
        Tuple of qualifier ion m/z values used for identification.
    tentative_identity:
        Proposed compound name for this peak.
    identity_authority:
        Authority class for the identity assignment. One of ``"A"``–``"F"``
        (as per evidence classes) or ``"UNCONFIRMED"``.
    match_score:
        Library match score (0–100).
    notes:
        Free-text notes about this peak.
    """

    peak_id: str
    run_id: str
    retention_time_min: float
    retention_index: float | None
    peak_area: float
    response_factor: float = 1.0
    qualifier_ions: tuple[str, ...] = ()
    tentative_identity: str = ""
    identity_authority: str = "UNCONFIRMED"
    match_score: float = 0.0
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "peak_id": self.peak_id,
            "run_id": self.run_id,
            "retention_time_min": self.retention_time_min,
            "retention_index": self.retention_index,
            "peak_area": self.peak_area,
            "response_factor": self.response_factor,
            "qualifier_ions": list(self.qualifier_ions),
            "tentative_identity": self.tentative_identity,
            "identity_authority": self.identity_authority,
            "match_score": self.match_score,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GCMSPeak:
        return cls(
            peak_id=str(data["peak_id"]),
            run_id=str(data["run_id"]),
            retention_time_min=float(data["retention_time_min"]),
            retention_index=float(data["retention_index"])
            if data.get("retention_index") is not None
            else None,
            peak_area=float(data["peak_area"]),
            response_factor=float(data.get("response_factor") or 1.0),
            qualifier_ions=tuple(str(x) for x in data.get("qualifier_ions") or ()),
            tentative_identity=str(data.get("tentative_identity") or ""),
            identity_authority=str(data.get("identity_authority") or "UNCONFIRMED"),
            match_score=float(data.get("match_score") or 0.0),
            notes=str(data.get("notes") or ""),
        )


@dataclass(frozen=True, slots=True)
class HSSPMERun:
    """A headspace SPME-GC-MS run.

    Parameters
    ----------
    run_id:
        UUID string identifying this run.
    fiber:
        SPME fiber coating and film thickness
        (e.g. ``"DVB/CAR/PDMS 50/30um"``).
    sample_mass_g:
        Mass of sample in the vial, in grams.
    vial_volume_ml:
        Vial volume in millilitres.
    incubation_temperature_c:
        Incubation temperature in °C.
    incubation_time_min:
        Incubation time in minutes.
    extraction_time_min:
        Fiber exposure time in minutes.
    agitation_rpm:
        Agitation speed in RPM.
    substrate:
        Substrate the fragrance was applied to
        (``"skin"``, ``"blotter"``, ``"fabric"``, ``"concentrate"``).
    application_age_min:
        How long the fragrance was on the substrate before sampling,
        in minutes.
    date_run:
        ISO 8601 date string when the run was performed.
    """

    run_id: str
    fiber: str
    sample_mass_g: float
    vial_volume_ml: float
    incubation_temperature_c: float
    incubation_time_min: float
    extraction_time_min: float
    agitation_rpm: int
    substrate: str
    application_age_min: float
    date_run: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "fiber": self.fiber,
            "sample_mass_g": self.sample_mass_g,
            "vial_volume_ml": self.vial_volume_ml,
            "incubation_temperature_c": self.incubation_temperature_c,
            "incubation_time_min": self.incubation_time_min,
            "extraction_time_min": self.extraction_time_min,
            "agitation_rpm": self.agitation_rpm,
            "substrate": self.substrate,
            "application_age_min": self.application_age_min,
            "date_run": self.date_run,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HSSPMERun:
        return cls(
            run_id=str(data["run_id"]),
            fiber=str(data["fiber"]),
            sample_mass_g=float(data["sample_mass_g"]),
            vial_volume_ml=float(data["vial_volume_ml"]),
            incubation_temperature_c=float(data["incubation_temperature_c"]),
            incubation_time_min=float(data["incubation_time_min"]),
            extraction_time_min=float(data["extraction_time_min"]),
            agitation_rpm=int(data["agitation_rpm"]),
            substrate=str(data["substrate"]),
            application_age_min=float(data["application_age_min"]),
            date_run=str(data.get("date_run") or ""),
        )


@dataclass(frozen=True, slots=True)
class GCOEvent:
    """A single GC-O (olfactometry) detection event.

    Parameters
    ----------
    event_id:
        UUID string identifying this event.
    run_id:
        UUID string referencing the parent GC-MS or HS-SPME run.
    position:
        Retention time (minutes) or retention index position where the
        odour was detected.
    descriptor:
        Odour description (e.g. ``"citrus, bergamot-like"``).
    intensity:
        Perceived intensity. One of ``"weak"``, ``"moderate"``,
        ``"strong"``, ``"very_strong"``.
    assessor:
        Name or identifier of the sniffing assessor.
    repeatability:
        How often the odour was detected across replicate runs.
        One of ``"once"``, ``"2_of_3"``, ``"consistent"``.
    aligned_retention_index:
        Retention index after alignment to a standard, if available.
    notes:
        Free-text notes about this event.
    """

    event_id: str
    run_id: str
    position: float
    descriptor: str
    intensity: str
    assessor: str
    repeatability: str
    aligned_retention_index: float | None = None
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "position": self.position,
            "descriptor": self.descriptor,
            "intensity": self.intensity,
            "assessor": self.assessor,
            "repeatability": self.repeatability,
            "aligned_retention_index": self.aligned_retention_index,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GCOEvent:
        return cls(
            event_id=str(data["event_id"]),
            run_id=str(data["run_id"]),
            position=float(data["position"]),
            descriptor=str(data["descriptor"]),
            intensity=str(data["intensity"]),
            assessor=str(data["assessor"]),
            repeatability=str(data["repeatability"]),
            aligned_retention_index=float(data["aligned_retention_index"])
            if data.get("aligned_retention_index") is not None
            else None,
            notes=str(data.get("notes") or ""),
        )


@dataclass(frozen=True, slots=True)
class QualityControls:
    """Quality control flags for an analytical run.

    Parameters
    ----------
    solvent_blank:
        A solvent blank was run and showed no carryover.
    vial_blank:
        An empty vial blank was run and showed no contamination.
    matrix_blank:
        A matrix blank (substrate without fragrance) was run.
    internal_standard_present:
        Internal standard was added and detected.
    retention_index_standard:
        A retention index standard (e.g. alkane series) was run.
    duplicate_injections:
        Number of duplicate injections performed (0 if none).
    control_fragrance_included:
        A known control fragrance was included in the batch.
    """

    solvent_blank: bool = False
    vial_blank: bool = False
    matrix_blank: bool = False
    internal_standard_present: bool = False
    retention_index_standard: bool = False
    duplicate_injections: int = 0
    control_fragrance_included: bool = False

    def passed(self) -> bool:
        """Return ``True`` if at least 4 of the 7 QC items pass.

        ``duplicate_injections`` counts as passing if >= 1.
        """
        score = 0
        if self.solvent_blank:
            score += 1
        if self.vial_blank:
            score += 1
        if self.matrix_blank:
            score += 1
        if self.internal_standard_present:
            score += 1
        if self.retention_index_standard:
            score += 1
        if self.duplicate_injections >= 1:
            score += 1
        if self.control_fragrance_included:
            score += 1
        return score >= 4

    def as_dict(self) -> dict[str, Any]:
        return {
            "solvent_blank": self.solvent_blank,
            "vial_blank": self.vial_blank,
            "matrix_blank": self.matrix_blank,
            "internal_standard_present": self.internal_standard_present,
            "retention_index_standard": self.retention_index_standard,
            "duplicate_injections": self.duplicate_injections,
            "control_fragrance_included": self.control_fragrance_included,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityControls:
        return cls(
            solvent_blank=bool(data.get("solvent_blank") or False),
            vial_blank=bool(data.get("vial_blank") or False),
            matrix_blank=bool(data.get("matrix_blank") or False),
            internal_standard_present=bool(data.get("internal_standard_present") or False),
            retention_index_standard=bool(data.get("retention_index_standard") or False),
            duplicate_injections=int(data.get("duplicate_injections") or 0),
            control_fragrance_included=bool(data.get("control_fragrance_included") or False),
        )


# ── Ledger ──────────────────────────────────────────────────────────────────────


class AnalyticalLedger:
    """In-memory ledger for analytical instrument data.

    Stores GC-MS runs with their peaks, HS-SPME runs, and GC-O events.
    Provides search by retention index and odor descriptor.
    """

    def __init__(self) -> None:
        self._gcms_runs: dict[str, GCMSRun] = {}
        self._gcms_peaks: dict[str, list[GCMSPeak]] = {}
        self._hsspme_runs: dict[str, HSSPMERun] = {}
        self._gco_events: list[GCOEvent] = []

    # ── mutation ────────────────────────────────────────────────────────────

    def add_gcms_run(self, run: GCMSRun, peaks: list[GCMSPeak]) -> None:
        """Reject writes to the deprecated in-memory duplicate store."""
        del run, peaks
        raise LegacyWriteProhibitedError(
            "AnalyticalLedger is read-only; persist analytical runs through LabService"
        )

    def add_hsspme_run(self, run: HSSPMERun) -> None:
        """Reject writes to the deprecated in-memory duplicate store."""
        del run
        raise LegacyWriteProhibitedError(
            "AnalyticalLedger is read-only; persist analytical runs through LabService"
        )

    def add_gco_event(self, event: GCOEvent) -> None:
        """Reject writes to the deprecated in-memory duplicate store."""
        del event
        raise LegacyWriteProhibitedError(
            "AnalyticalLedger is read-only; persist GC-O events through LabService"
        )

    # ── queries ─────────────────────────────────────────────────────────────

    def get_identified_materials(self, run_id: str) -> list[str]:
        """Return tentative identities for peaks in a run that have a
        non-empty ``tentative_identity`` and a ``match_score`` >= 80.

        Returns an empty list if the run has no peaks or is unknown.
        """
        peaks = self._gcms_peaks.get(run_id, [])
        return [
            p.tentative_identity for p in peaks if p.tentative_identity and p.match_score >= 80.0
        ]

    def search_by_retention_index(
        self,
        ri: float,
        tolerance: float = 5.0,
    ) -> list[GCMSPeak]:
        """Return all peaks whose ``retention_index`` falls within
        ``ri +/- tolerance``.

        Peaks with ``None`` retention index are excluded.
        """
        lo = ri - tolerance
        hi = ri + tolerance
        results: list[GCMSPeak] = []
        for peaks in self._gcms_peaks.values():
            for p in peaks:
                if p.retention_index is not None and lo <= p.retention_index <= hi:
                    results.append(p)
        return results

    def search_by_odor_descriptor(self, text: str) -> list[GCOEvent]:
        """Return all GC-O events whose ``descriptor`` contains ``text``
        (case-insensitive substring match).
        """
        t = text.casefold()
        return [e for e in self._gco_events if t in e.descriptor.casefold()]

    # ── serialisation ───────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialise the entire ledger to a JSON-compatible dict."""
        return {
            "gcms_runs": [
                {
                    "run": r.as_dict(),
                    "peaks": [p.as_dict() for p in self._gcms_peaks.get(rid, [])],
                }
                for rid, r in self._gcms_runs.items()
            ],
            "hsspme_runs": [r.as_dict() for r in self._hsspme_runs.values()],
            "gco_events": [e.as_dict() for e in self._gco_events],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalyticalLedger:
        """Reconstruct a ledger from a dict produced by :meth:`to_dict`."""
        gcms_records: list[tuple[GCMSRun, list[GCMSPeak]]] = []
        for entry in data.get("gcms_runs", []):
            run = GCMSRun.from_dict(entry["run"])
            peaks = [GCMSPeak.from_dict(p) for p in entry.get("peaks", [])]
            gcms_records.append((run, peaks))
        return cls.from_records(
            gcms_records=gcms_records,
            hsspme_runs=[HSSPMERun.from_dict(r) for r in data.get("hsspme_runs", [])],
            gco_events=[GCOEvent.from_dict(e) for e in data.get("gco_events", [])],
        )

    @classmethod
    def from_records(
        cls,
        *,
        gcms_records: Sequence[tuple[GCMSRun, Sequence[GCMSPeak]]] = (),
        hsspme_runs: Sequence[HSSPMERun] = (),
        gco_events: Sequence[GCOEvent] = (),
    ) -> AnalyticalLedger:
        """Hydrate a read-only projection without invoking public mutators."""
        ledger = cls()
        for run, peaks in gcms_records:
            ledger._gcms_runs[run.run_id] = run
            ledger._gcms_peaks[run.run_id] = list(peaks)
        ledger._hsspme_runs = {run.run_id: run for run in hsspme_runs}
        ledger._gco_events = list(gco_events)
        return ledger


__all__ = [
    "GCMSRun",
    "GCMSPeak",
    "HSSPMERun",
    "GCOEvent",
    "QualityControls",
    "AnalyticalLedger",
]
