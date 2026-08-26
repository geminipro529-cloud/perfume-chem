"""One-way adapters between canonical laboratory rows and legacy projections.

This module never owns a database session and never calls a legacy ledger
mutator. Canonical rows may be projected for read-only engine calculations.
Legacy payloads may become deterministic import drafts, but a draft has no
persistence authority until an explicit :class:`LabService` command accepts it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
from math import isfinite
from typing import Any

from engine.analytical.ledger import (
    AnalyticalLedger,
    GCMSPeak,
    GCMSRun,
    GCOEvent,
    HSSPMERun,
)
from engine.bottle.events import (
    COMMITTED,
    CREATE_BATCH,
    DOSE_STOCK,
    REMOVE_SAMPLE,
    BottleBatch,
    BottleEvent,
)
from engine.evidence.ledger import EvidenceLedger
from engine.inventory.stock_model import StockItem
from engine.safety.regulatory import RegulatorySnapshot
from engine.sensory.ledger import SensoryObservation, SensorySample, SensoryTrial
from engine.versioning.formula_version import FormulaVersion

from app.models.lab import (
    LabApplication,
    LabBottle,
    LabBottleEvent,
    LabBottleEventEffect,
    LabEvidenceRecord,
    LabExperiment,
    LabFormulaVersion,
    LabObservation,
    LabSample,
    LabStockSolution,
)
from app.models.lab_science import (
    LabAnalyticalMethodVersion,
    LabAnalyticalPeak,
    LabAnalyticalRun,
    LabGCOEvent,
    LabRegulatoryAssessmentVersion,
)


class LegacyAdapterError(ValueError):
    """A compatibility projection would be lossy or scientifically ambiguous."""

    code = "LEGACY_ADAPTER_REJECTED"


@dataclass(frozen=True, slots=True)
class LegacyImportDraft:
    """Deterministic, non-persisting candidate for a canonical service command."""

    destination: str
    stable_key: str
    payload_json: str
    content_sha256: str
    warnings: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        destination: str,
        stable_key: str,
        payload: Mapping[str, Any],
        warnings: Sequence[str] = (),
    ) -> LegacyImportDraft:
        if not destination.startswith("lab_"):
            raise LegacyAdapterError("import destination must be a canonical lab_* table")
        if not stable_key.strip():
            raise LegacyAdapterError("import stable_key must not be empty")
        try:
            encoded = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise LegacyAdapterError("legacy import payload must be canonical JSON") from exc
        return cls(
            destination=destination,
            stable_key=stable_key,
            payload_json=encoded,
            content_sha256=sha256(encoded.encode("utf-8")).hexdigest(),
            warnings=tuple(str(warning) for warning in warnings),
        )

    def payload(self) -> dict[str, Any]:
        """Return a fresh payload copy suitable for explicit service review."""
        value = json.loads(self.payload_json)
        if not isinstance(value, dict):  # pragma: no cover - constructor invariant
            raise LegacyAdapterError("import payload is not an object")
        return value


def project_stock_solution(
    stock: LabStockSolution,
    *,
    material_name: str,
) -> StockItem:
    """Project one canonical stock row into a read-only legacy stock item."""
    density = _positive_float(stock.density_g_ml, field="density_g_ml")
    remaining_mass_g = (
        float(stock.remaining_mass_g)
        if stock.remaining_mass_g is not None
        else float(stock.initial_mass_g)
    )
    if remaining_mass_g < 0 or not isfinite(remaining_mass_g):
        raise LegacyAdapterError("remaining_mass_g must be finite and nonnegative")
    source = dict(stock.source_json or {})
    return StockItem(
        material_id=stock.id,
        label=_required_text(material_name, field="material_name"),
        grade=str(source.get("grade") or "trade_grade"),
        supplier=stock.supplier,
        lot=stock.lot_number,
        concentration=float(stock.active_fraction),
        concentration_basis=str(stock.fraction_basis),
        carrier=str(stock.solvent_name or ""),
        density_g_ml=density,
        amount_remaining_ml=remaining_mass_g / density,
        amount_unit="ml",
        date_opened=_optional_text(source.get("date_opened")),
        date_acquired=_optional_text(source.get("date_acquired")),
        stability_status=str(source.get("stability_status") or "unknown"),
        notes=str(source.get("notes") or ""),
    )


def project_bottle_batch(
    bottle: LabBottle,
    events: Sequence[LabBottleEvent],
    *,
    effects_by_event: Mapping[str, Sequence[LabBottleEventEffect]],
    stock_labels: Mapping[str, str] | None = None,
) -> BottleBatch:
    """Project a canonical event/effect stream into a read-only replay batch."""
    labels = stock_labels or {}
    projected: list[BottleEvent] = []
    ordered = sorted(events, key=lambda event: (event.stream_sequence, event.id))
    for event in ordered:
        if event.bottle_id != bottle.id:
            raise LegacyAdapterError("canonical event belongs to a different bottle")
        effects = tuple(effects_by_event.get(event.id, ()))
        nonzero = [effect for effect in effects if abs(float(effect.mass_delta_g)) > 1e-12]
        if nonzero:
            for index, effect in enumerate(nonzero, start=1):
                if effect.bottle_id != bottle.id or effect.event_id != event.id:
                    raise LegacyAdapterError("canonical event effect linkage is inconsistent")
                delta = float(effect.mass_delta_g)
                stock_key = effect.stock_solution_id or effect.material_id
                label = labels.get(str(stock_key), str(stock_key or "unassigned"))
                event_id = event.id if len(nonzero) == 1 else f"{event.id}:{effect.id}"
                projected.append(
                    BottleEvent(
                        event_id=event_id,
                        batch_id=bottle.id,
                        event_type=DOSE_STOCK if delta > 0 else REMOVE_SAMPLE,
                        timestamp=_iso(event.created_at),
                        stock_id=effect.stock_solution_id,
                        stock_label=label,
                        measured_mass_g=abs(delta),
                        volume_ul=effect.measured_volume_ul,
                        notes=(
                            f"canonical_event={event.id}; "
                            f"canonical_type={event.event_type}; effect={index}"
                        ),
                        confirmation=COMMITTED,
                    )
                )
            continue
        if event.event_type == "create":
            projected.append(
                BottleEvent(
                    event_id=event.id,
                    batch_id=bottle.id,
                    event_type=CREATE_BATCH,
                    timestamp=_iso(event.created_at),
                    notes="canonical_type=create",
                    confirmation=COMMITTED,
                )
            )
            continue
        raise LegacyAdapterError(
            f"canonical event {event.id!r} has no replayable effect"
        )
    return BottleBatch.from_events(
        bottle.id,
        projected,
        batch_name=bottle.label,
    )


def project_formula_version(
    version: LabFormulaVersion,
    *,
    parent_version_id: str | None,
) -> FormulaVersion:
    """Project an immutable canonical formula version into the engine DAG view."""
    source = dict(version.source_json or {})
    formula_hash = _required_sha256(source.get("formula_hash"), field="formula_hash")
    change_type = _required_text(source.get("change_type"), field="change_type")
    raw_changes = source.get("changes", [])
    if not isinstance(raw_changes, list):
        raise LegacyAdapterError("formula changes must be a list")
    return FormulaVersion.from_dict(
        {
            "version_id": version.id,
            "parent_version_id": parent_version_id,
            "timestamp": _iso(version.created_at),
            "formula_hash": formula_hash,
            "change_type": change_type,
            "changes": raw_changes,
            "description": str(source.get("description") or ""),
            "mode": str(source.get("mode") or "CREATIVE_FORMULATION"),
        }
    )


def project_analytical_ledger(
    *,
    methods_by_id: Mapping[str, LabAnalyticalMethodVersion],
    runs: Sequence[LabAnalyticalRun],
    peaks_by_run: Mapping[str, Sequence[LabAnalyticalPeak]],
    gco_events: Sequence[LabGCOEvent] = (),
) -> AnalyticalLedger:
    """Project canonical analytical rows into a read-only legacy ledger."""
    gcms_records: list[tuple[GCMSRun, list[GCMSPeak]]] = []
    hsspme_runs: list[HSSPMERun] = []
    for run in sorted(runs, key=lambda row: (row.acquired_at, row.id)):
        method = methods_by_id.get(run.method_version_id)
        if method is None:
            raise LegacyAdapterError(f"missing method version for analytical run {run.id}")
        params = {**dict(method.method_json or {}), **dict(run.parameters_json or {})}
        if run.run_kind == "GCMS":
            legacy_run = GCMSRun(
                run_id=run.id,
                instrument=run.instrument_identifier,
                column=_required_text(params.get("column"), field="column"),
                temperature_program=_required_text(
                    params.get("temperature_program"),
                    field="temperature_program",
                ),
                injection_mode=_required_text(
                    params.get("injection_mode"),
                    field="injection_mode",
                ),
                injection_volume_ul=_required_number(
                    params.get("injection_volume_ul"),
                    field="injection_volume_ul",
                ),
                carrier_gas=str(params.get("carrier_gas") or "Helium"),
                flow_rate_ml_min=float(params.get("flow_rate_ml_min") or 1.0),
                internal_standard=str(params.get("internal_standard") or ""),
                internal_standard_amount_ug=float(
                    params.get("internal_standard_amount_ug") or 0.0
                ),
                date_run=_iso(run.acquired_at),
            )
            legacy_peaks = [
                _project_peak(peak, run_id=run.id)
                for peak in sorted(
                    peaks_by_run.get(run.id, ()),
                    key=lambda row: (row.peak_key, row.id),
                )
            ]
            gcms_records.append((legacy_run, legacy_peaks))
        elif run.run_kind == "HS_SPME_GCMS":
            hsspme_runs.append(
                HSSPMERun(
                    run_id=run.id,
                    fiber=_required_text(params.get("fiber"), field="fiber"),
                    sample_mass_g=_required_number(
                        params.get("sample_mass_g"), field="sample_mass_g"
                    ),
                    vial_volume_ml=_required_number(
                        params.get("vial_volume_ml"), field="vial_volume_ml"
                    ),
                    incubation_temperature_c=_required_number(
                        params.get("incubation_temperature_c"),
                        field="incubation_temperature_c",
                    ),
                    incubation_time_min=_required_number(
                        params.get("incubation_time_min"),
                        field="incubation_time_min",
                    ),
                    extraction_time_min=_required_number(
                        params.get("extraction_time_min"),
                        field="extraction_time_min",
                    ),
                    agitation_rpm=int(
                        _required_number(
                            params.get("agitation_rpm"), field="agitation_rpm"
                        )
                    ),
                    substrate=_required_text(params.get("substrate"), field="substrate"),
                    application_age_min=_required_number(
                        params.get("application_age_min"),
                        field="application_age_min",
                    ),
                    date_run=_iso(run.acquired_at),
                )
            )
        else:
            raise LegacyAdapterError(
                f"run kind {run.run_kind!r} has no legacy analytical projection"
            )
    legacy_gco = [_project_gco(event) for event in sorted(gco_events, key=lambda row: row.id)]
    return AnalyticalLedger.from_records(
        gcms_records=gcms_records,
        hsspme_runs=hsspme_runs,
        gco_events=legacy_gco,
    )


def project_sensory_trial(
    *,
    experiment: LabExperiment,
    samples: Sequence[LabSample],
    applications_by_sample: Mapping[str, LabApplication],
    observations_by_application: Mapping[str, Sequence[LabObservation]],
    formula_ids_by_bottle: Mapping[str, str],
    reference_sample_id: str,
) -> SensoryTrial:
    """Project canonical experiment rows into a read-only sensory trial."""
    legacy_samples: list[SensorySample] = []
    legacy_observations: list[SensoryObservation] = []
    assessors: set[str] = set()
    for sample in sorted(samples, key=lambda row: row.id):
        if sample.experiment_id != experiment.id:
            raise LegacyAdapterError("sensory sample belongs to another experiment")
        application = applications_by_sample.get(sample.id)
        if application is None:
            raise LegacyAdapterError(f"missing application for sample {sample.id}")
        formula_id = formula_ids_by_bottle.get(sample.bottle_id)
        if formula_id is None:
            raise LegacyAdapterError(f"missing formula identity for bottle {sample.bottle_id}")
        dose = dict(application.dose_json or {})
        context = dict(application.context_json or {})
        legacy_samples.append(
            SensorySample(
                sample_id=sample.id,
                formula_id=formula_id,
                batch_id=sample.bottle_id,
                code=sample.blind_code,
                application_mass_g=_required_number(
                    dose.get("application_mass_g"),
                    field="application_mass_g",
                ),
                substrate=_required_text(context.get("substrate"), field="substrate"),
                room_temperature_c=_required_number(
                    context.get("room_temperature_c"),
                    field="room_temperature_c",
                ),
                room_humidity_pct=_required_number(
                    context.get("room_humidity_pct"),
                    field="room_humidity_pct",
                ),
                prepared_at=_iso(application.applied_at),
            )
        )
        for observation in sorted(
            observations_by_application.get(application.id, ()),
            key=lambda row: (row.elapsed_seconds, row.id),
        ):
            values = dict(observation.observations_json or {})
            assessor = _required_text(values.get("assessor"), field="assessor")
            assessors.add(assessor)
            legacy_observations.append(
                SensoryObservation(
                    observation_id=observation.id,
                    sample_id=sample.id,
                    assessor=assessor,
                    time_seconds=float(observation.elapsed_seconds),
                    opening_identity=_required_number(
                        values.get("opening_identity"), field="opening_identity"
                    ),
                    heart_identity=_required_number(
                        values.get("heart_identity"), field="heart_identity"
                    ),
                    drydown_identity=_required_number(
                        values.get("drydown_identity"), field="drydown_identity"
                    ),
                    transition_quality=_required_number(
                        values.get("transition_quality"), field="transition_quality"
                    ),
                    texture=_required_number(values.get("texture"), field="texture"),
                    diffusion=_required_number(
                        values.get("diffusion"), field="diffusion"
                    ),
                    longevity=_required_number(
                        values.get("longevity"), field="longevity"
                    ),
                    off_notes=str(values.get("off_notes") or ""),
                    overall_similarity=_required_number(
                        values.get("overall_similarity"),
                        field="overall_similarity",
                    ),
                    preference=_required_number(
                        values.get("preference"), field="preference"
                    ),
                    notes=str(values.get("notes") or ""),
                )
            )
    if reference_sample_id not in {sample.sample_id for sample in legacy_samples}:
        raise LegacyAdapterError("reference sample is not part of the experiment")
    return SensoryTrial.from_records(
        trial_name=experiment.name,
        reference_sample_id=reference_sample_id,
        assessors=sorted(assessors),
        samples=legacy_samples,
        observations=legacy_observations,
    )


def project_regulatory_snapshot(
    assessment: LabRegulatoryAssessmentVersion,
) -> RegulatorySnapshot:
    """Project one dated canonical assessment into an immutable snapshot view."""
    if assessment.effective_date is None:
        raise LegacyAdapterError("regulatory assessment has no effective date")
    amendment = f" {assessment.standard_amendment}" if assessment.standard_amendment else ""
    return RegulatorySnapshot(
        snapshot_id=assessment.id,
        jurisdiction=assessment.jurisdiction,
        product_category=assessment.product_category,
        rule_set=f"{assessment.standard_identifier}{amendment}".strip(),
        effective_date=assessment.effective_date.isoformat(),
        hash=assessment.content_sha256,
        notes=f"canonical_result_state={assessment.result_state}",
    )


def evidence_ledger_import_drafts(
    ledger: EvidenceLedger,
) -> tuple[LegacyImportDraft, ...]:
    """Convert a legacy evidence projection into deterministic review drafts."""
    payload = ledger.to_dict()
    sources = {
        str(source["source_id"]): source
        for source in payload.get("sources", [])
    }
    drafts: list[LegacyImportDraft] = []
    referenced: set[str] = set()
    for claim in payload.get("claims", []):
        source_id = str(claim["source_id"])
        source = sources.get(source_id)
        if source is None:
            raise LegacyAdapterError(f"claim references missing source {source_id!r}")
        referenced.add(source_id)
        drafts.append(
            LegacyImportDraft.create(
                destination=LabEvidenceRecord.__tablename__,
                stable_key=str(claim["claim_id"]),
                payload={
                    "claim_key": str(claim["claim_id"]),
                    "classification": str(source["source_class"]),
                    "source_locator": _source_locator(source),
                    "method": "legacy_evidence_ledger_import",
                    "assumptions": [],
                    "limitations": [
                        "legacy fields require explicit LabService validation before persistence"
                    ],
                    "legacy_source": source,
                    "legacy_claim": claim,
                },
            )
        )
    for source_id, source in sorted(sources.items()):
        if source_id in referenced:
            continue
        drafts.append(
            LegacyImportDraft.create(
                destination=LabEvidenceRecord.__tablename__,
                stable_key=f"source:{source_id}",
                payload={
                    "claim_key": f"source:{source_id}",
                    "classification": str(source["source_class"]),
                    "source_locator": _source_locator(source),
                    "method": "legacy_evidence_source_import",
                    "assumptions": [],
                    "limitations": ["source has no associated legacy claim"],
                    "legacy_source": source,
                },
            )
        )
    return tuple(sorted(drafts, key=lambda draft: draft.stable_key))


def analytical_ledger_import_drafts(
    ledger: AnalyticalLedger,
) -> tuple[LegacyImportDraft, ...]:
    """Create non-persisting analytical review drafts from a legacy ledger."""
    payload = ledger.to_dict()
    drafts: list[LegacyImportDraft] = []
    for entry in payload["gcms_runs"]:
        run = entry["run"]
        drafts.append(
            LegacyImportDraft.create(
                destination="lab_analytical_runs",
                stable_key=str(run["run_id"]),
                payload={"run_kind": "GCMS", **entry},
                warnings=("canonical method-version binding is required",),
            )
        )
    for run in payload["hsspme_runs"]:
        drafts.append(
            LegacyImportDraft.create(
                destination="lab_analytical_runs",
                stable_key=str(run["run_id"]),
                payload={"run_kind": "HS_SPME_GCMS", "run": run},
                warnings=("canonical method-version binding is required",),
            )
        )
    for event in payload["gco_events"]:
        drafts.append(
            LegacyImportDraft.create(
                destination="lab_gco_events",
                stable_key=str(event["event_id"]),
                payload=event,
                warnings=("canonical analytical-run binding must be verified",),
            )
        )
    return tuple(sorted(drafts, key=lambda draft: (draft.destination, draft.stable_key)))


def _project_peak(peak: LabAnalyticalPeak, *, run_id: str) -> GCMSPeak:
    if peak.analytical_run_id != run_id:
        raise LegacyAdapterError("analytical peak belongs to a different run")
    if peak.retention_time_minutes is None or peak.area is None:
        raise LegacyAdapterError("legacy GC-MS projection requires retention time and area")
    authority = {
        "CONFIRMED": "C",
        "TENTATIVE": "D",
        "UNASSIGNED": "UNCONFIRMED",
    }.get(peak.identity_state)
    if authority is None:
        raise LegacyAdapterError(f"unknown identity state {peak.identity_state!r}")
    return GCMSPeak(
        peak_id=peak.id,
        run_id=run_id,
        retention_time_min=float(peak.retention_time_minutes),
        retention_index=peak.retention_index,
        peak_area=float(peak.area),
        response_factor=float(peak.response_factor or 1.0),
        qualifier_ions=tuple(str(ion) for ion in peak.qualifier_ions_json),
        tentative_identity=str(peak.tentative_identity or ""),
        identity_authority=authority,
        match_score=float(peak.match_score or 0.0) * 100.0,
        notes=str(peak.notes or ""),
    )


def _project_gco(event: LabGCOEvent) -> GCOEvent:
    position = (
        event.retention_time_minutes
        if event.retention_time_minutes is not None
        else event.retention_index
    )
    if position is None:
        raise LegacyAdapterError("GC-O event has no retention position")
    intensity = event.intensity
    if intensity is None:
        legacy_intensity = "weak"
    elif intensity < 0.25:
        legacy_intensity = "weak"
    elif intensity < 0.5:
        legacy_intensity = "moderate"
    elif intensity < 0.75:
        legacy_intensity = "strong"
    else:
        legacy_intensity = "very_strong"
    repeatability = str(
        (event.repeatability_json or {}).get("legacy_label")
        or (event.repeatability_json or {}).get("label")
        or "once"
    )
    return GCOEvent(
        event_id=event.id,
        run_id=event.analytical_run_id,
        position=float(position),
        descriptor=event.descriptor,
        intensity=legacy_intensity,
        assessor=event.assessor_pseudonym,
        repeatability=repeatability,
        aligned_retention_index=event.retention_index,
    )


def _required_number(value: Any, *, field: str) -> float:
    if value is None:
        raise LegacyAdapterError(f"{field} is required for legacy projection")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise LegacyAdapterError(f"{field} must be numeric") from exc
    if not isfinite(number):
        raise LegacyAdapterError(f"{field} must be finite")
    return number


def _positive_float(value: Any, *, field: str) -> float:
    number = _required_number(value, field=field)
    if number <= 0:
        raise LegacyAdapterError(f"{field} must be greater than zero")
    return number


def _required_text(value: Any, *, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise LegacyAdapterError(f"{field} is required for legacy projection")
    return text


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _required_sha256(value: Any, *, field: str) -> str:
    digest = _required_text(value, field=field).lower()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise LegacyAdapterError(f"{field} must be a SHA-256 hex digest")
    return digest


def _iso(value: datetime | date) -> str:
    return value.isoformat()


def _source_locator(source: Mapping[str, Any]) -> str:
    for key in ("doi", "url", "source_id"):
        value = _optional_text(source.get(key))
        if value is not None:
            return value
    raise LegacyAdapterError("legacy evidence source has no locator")


__all__ = [
    "LegacyAdapterError",
    "LegacyImportDraft",
    "analytical_ledger_import_drafts",
    "evidence_ledger_import_drafts",
    "project_analytical_ledger",
    "project_bottle_batch",
    "project_formula_version",
    "project_regulatory_snapshot",
    "project_sensory_trial",
    "project_stock_solution",
]
