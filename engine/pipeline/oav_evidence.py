"""Evidence-state OAV gate without aggregate perceptual authority."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, ClassVar, Iterable, Mapping

from engine.calibration.hashing import stable_json_hash
from engine.evidence_contracts import (
    EvidenceBasis,
    EvidenceSourceRef,
    QuantitativeEvidence,
    canonical_json_bytes,
    sha256_hex,
)
from engine.pipeline.formula_state import FormulaState
from engine.solforge.evidence_review import (
    EVIDENCE_REVIEW_AUTHORITY_FLAGS,
    OAVIntervalEvidence,
    OAVModelTier,
    OAVTimepointEvidenceInput,
    OAVTimepointKey,
    TemporalOAVEvidenceRequest,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

TEMPORAL_OAV_AUTHORITY_FLAGS = {
    **EVIDENCE_REVIEW_AUTHORITY_FLAGS,
    "compounding": False,
    "hedonic": False,
    "stability": False,
}


class OAVEvidenceState(str, Enum):
    STRICT_MEASURED = "STRICT_MEASURED"
    MODELED_SCREEN = "MODELED_SCREEN"
    PARTIAL = "PARTIAL"
    ABSTAINED = "ABSTAINED"
    INVALID = "INVALID"


class TemporalOAVEvidenceState(str, Enum):
    """Versioned temporal evidence state, separate from the V2 row gate."""

    STRICT_MEASURED_TIME_SERIES = "STRICT_MEASURED_TIME_SERIES"
    MODELED_SCREEN = "MODELED_SCREEN"
    PARTIAL = "PARTIAL"
    ABSTAINED = "ABSTAINED"
    INVALID = "INVALID"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _text(value, field_name)


def _sha256(value: object, field_name: str) -> str:
    digest = _text(value, field_name).lower()
    if not _SHA256_RE.fullmatch(digest):
        raise ValueError(f"{field_name} must be a SHA-256 hex digest")
    return digest


def _same_text(left: str, right: str) -> bool:
    return " ".join(left.split()).casefold() == " ".join(right.split()).casefold()


@dataclass(frozen=True, slots=True)
class OAVMaterialEvidenceInput:
    material_name: str
    canonical_name: str
    exact_stock_ref: str | None
    supplied_strength_fraction: float | None
    carrier: str | None
    active_mass_g: float | None
    formula_matrix: str
    headspace: QuantitativeEvidence
    threshold: QuantitativeEvidence
    natural_or_preblend: bool = False
    constituent_evidence: tuple[QuantitativeEvidence, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "material_name", _text(self.material_name, "material_name")
        )
        object.__setattr__(
            self, "canonical_name", _text(self.canonical_name, "canonical_name")
        )
        object.__setattr__(
            self,
            "exact_stock_ref",
            _optional_text(self.exact_stock_ref, "exact_stock_ref"),
        )
        object.__setattr__(self, "carrier", _optional_text(self.carrier, "carrier"))
        object.__setattr__(
            self, "formula_matrix", _text(self.formula_matrix, "formula_matrix")
        )
        if self.supplied_strength_fraction is not None:
            value = self.supplied_strength_fraction
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("supplied_strength_fraction must be numeric")
            strength = float(value)
            if not isfinite(strength) or strength <= 0 or strength > 1:
                raise ValueError(
                    "supplied_strength_fraction must be finite and in (0, 1]"
                )
            object.__setattr__(self, "supplied_strength_fraction", strength)
        if self.active_mass_g is not None:
            value = self.active_mass_g
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("active_mass_g must be numeric")
            mass = float(value)
            if not isfinite(mass) or mass < 0:
                raise ValueError("active_mass_g must be finite and nonnegative")
            object.__setattr__(self, "active_mass_g", mass)
        if not isinstance(self.headspace, QuantitativeEvidence):
            raise TypeError("headspace must be QuantitativeEvidence")
        if not isinstance(self.threshold, QuantitativeEvidence):
            raise TypeError("threshold must be QuantitativeEvidence")
        if not isinstance(self.natural_or_preblend, bool):
            raise TypeError("natural_or_preblend must be boolean")
        constituents = tuple(self.constituent_evidence)
        if any(not isinstance(item, QuantitativeEvidence) for item in constituents):
            raise TypeError("constituent_evidence must contain QuantitativeEvidence")
        object.__setattr__(self, "constituent_evidence", constituents)


@dataclass(frozen=True, slots=True)
class OAVEvidenceRequest:
    formula_sha256: str
    dose_receipt_sha256: str
    measurement_context: str
    rows: tuple[OAVMaterialEvidenceInput, ...]
    dose_receipt: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "formula_sha256", _sha256(self.formula_sha256, "formula_sha256")
        )
        object.__setattr__(
            self,
            "dose_receipt_sha256",
            _sha256(self.dose_receipt_sha256, "dose_receipt_sha256"),
        )
        object.__setattr__(
            self,
            "measurement_context",
            _text(self.measurement_context, "measurement_context"),
        )
        rows = tuple(self.rows)
        if any(not isinstance(row, OAVMaterialEvidenceInput) for row in rows):
            raise TypeError("rows must contain OAVMaterialEvidenceInput")
        object.__setattr__(self, "rows", rows)
        if self.dose_receipt is not None:
            if not isinstance(self.dose_receipt, Mapping):
                raise TypeError("dose_receipt must be a mapping or None")
            receipt = dict(self.dose_receipt)
            canonical_json_bytes(receipt)
            object.__setattr__(self, "dose_receipt", receipt)


@dataclass(frozen=True, slots=True)
class OAVMaterialEvidenceResult:
    material_name: str
    canonical_name: str
    state: OAVEvidenceState
    headspace_basis: EvidenceBasis
    threshold_basis: EvidenceBasis
    oav: float | None
    threshold_screening: str
    recognizable_in_mixture: None
    constituent_evidence_count: int
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "material_name": self.material_name,
            "canonical_name": self.canonical_name,
            "state": self.state.value,
            "headspace_basis": self.headspace_basis.value,
            "threshold_basis": self.threshold_basis.value,
            "oav": self.oav,
            "threshold_screening": self.threshold_screening,
            "recognizable_in_mixture": None,
            "constituent_evidence_count": self.constituent_evidence_count,
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class OAVEvidenceResult:
    state: OAVEvidenceState
    formula_sha256: str
    dose_receipt_sha256: str
    measurement_context: str
    rows: tuple[OAVMaterialEvidenceResult, ...]
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    sensory_authority: bool = field(default=False, init=False)
    hedonic_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "oav_evidence_v2",
            "state": self.state.value,
            "formula_sha256": self.formula_sha256,
            "dose_receipt_sha256": self.dose_receipt_sha256,
            "measurement_context": self.measurement_context,
            "rows": [row.as_dict() for row in self.rows],
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
            "authority": {
                "sensory": self.sensory_authority,
                "hedonic": self.hedonic_authority,
                "release": self.release_authority,
            },
        }


def _timepoint_sort_key(key: OAVTimepointKey) -> tuple[str, str, str, int, str]:
    return (
        key.protocol_sha256,
        key.sample_id.casefold(),
        key.material_id.casefold(),
        key.time_seconds,
        key.endpoint.casefold(),
    )


def _timepoint_token(key: OAVTimepointKey) -> str:
    return (
        f"{key.protocol_sha256}:{key.sample_id}:{key.material_id}:"
        f"{key.time_seconds}:{key.endpoint}"
    )


def _normalized_strings(values: Iterable[str], field_name: str) -> frozenset[str]:
    normalized: set[str] = set()
    for value in values:
        normalized.add(_text(value, field_name).casefold())
    return frozenset(normalized)


def _interval_is_unknown(interval: OAVIntervalEvidence) -> bool:
    return interval.p05.basis is EvidenceBasis.UNKNOWN


def _source_signature(evidence: QuantitativeEvidence) -> bytes | None:
    if evidence.source is None:
        return None
    return canonical_json_bytes(evidence.source.as_dict())


def _interval_source_signature(interval: OAVIntervalEvidence) -> bytes | None:
    signatures = {
        _source_signature(item) for item in (interval.p05, interval.p50, interval.p95)
    }
    if len(signatures) != 1:
        return b"INCONSISTENT"
    return signatures.pop()


@dataclass(frozen=True, slots=True)
class TemporalOAVCellResult:
    """One raw temporal input plus its bounded OAV interval calculation."""

    evidence: OAVTimepointEvidenceInput
    oav_interval: tuple[float, float, float] | None
    threshold_screening: str
    whole_material_screen: bool
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, OAVTimepointEvidenceInput):
            raise TypeError("evidence must be OAVTimepointEvidenceInput")
        if self.oav_interval is not None:
            values = tuple(float(value) for value in self.oav_interval)
            if len(values) != 3 or any(not isfinite(value) or value <= 0 for value in values):
                raise ValueError("oav_interval must contain three positive finite values")
            if not values[0] <= values[1] <= values[2]:
                raise ValueError("oav_interval must be ordered")
            object.__setattr__(self, "oav_interval", values)
        object.__setattr__(
            self,
            "threshold_screening",
            _text(self.threshold_screening, "threshold_screening"),
        )
        if not isinstance(self.whole_material_screen, bool):
            raise TypeError("whole_material_screen must be boolean")
        object.__setattr__(self, "blockers", tuple(self.blockers))
        object.__setattr__(self, "limitations", tuple(self.limitations))

    @property
    def key(self) -> OAVTimepointKey:
        return self.evidence.key

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence": self.evidence.as_dict(),
            "oav_interval": (
                None if self.oav_interval is None else list(self.oav_interval)
            ),
            "threshold_screening": self.threshold_screening,
            "whole_material_screen": self.whole_material_screen,
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, payload: object) -> TemporalOAVCellResult:
        fields = {
            "evidence",
            "oav_interval",
            "threshold_screening",
            "whole_material_screen",
            "blockers",
            "limitations",
        }
        if not isinstance(payload, dict) or set(payload) != fields:
            raise ValueError("temporal OAV cell result does not match the closed schema")
        raw_interval = payload["oav_interval"]
        interval = None if raw_interval is None else tuple(raw_interval)
        return cls(
            evidence=OAVTimepointEvidenceInput.from_dict(payload["evidence"]),
            oav_interval=interval,
            threshold_screening=payload["threshold_screening"],
            whole_material_screen=payload["whole_material_screen"],
            blockers=tuple(payload["blockers"]),
            limitations=tuple(payload["limitations"]),
        )


@dataclass(frozen=True, slots=True)
class TemporalOAVEvidenceResult:
    """Canonical temporal OAV receipt with no sensory or hedonic authority."""

    SCHEMA_VERSION: ClassVar[str] = "temporal_oav_evidence_v1"

    state: TemporalOAVEvidenceState
    formula_sha256: str
    dose_receipt_sha256: str
    protocol_sha256: str
    measurement_context_sha256: str
    declared_cells: tuple[OAVTimepointKey, ...]
    measured_cells: tuple[TemporalOAVCellResult, ...]
    modeled_cells: tuple[TemporalOAVCellResult, ...]
    missing_cells: tuple[OAVTimepointKey, ...]
    invalid_cells: tuple[TemporalOAVCellResult, ...]
    lineage_hashes: tuple[str, ...]
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", TemporalOAVEvidenceState(self.state))
        for field_name in (
            "formula_sha256",
            "dose_receipt_sha256",
            "protocol_sha256",
            "measurement_context_sha256",
        ):
            object.__setattr__(
                self, field_name, _sha256(getattr(self, field_name), field_name)
            )
        for field_name in ("declared_cells", "missing_cells"):
            values = tuple(getattr(self, field_name))
            if any(not isinstance(item, OAVTimepointKey) for item in values):
                raise TypeError(f"{field_name} must contain OAVTimepointKey")
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must not contain duplicates")
            object.__setattr__(
                self, field_name, tuple(sorted(values, key=_timepoint_sort_key))
            )
        for field_name in ("measured_cells", "modeled_cells", "invalid_cells"):
            values = tuple(getattr(self, field_name))
            if any(not isinstance(item, TemporalOAVCellResult) for item in values):
                raise TypeError(f"{field_name} must contain TemporalOAVCellResult")
            object.__setattr__(
                self,
                field_name,
                tuple(
                    sorted(
                        values,
                        key=lambda item: (
                            _timepoint_sort_key(item.key),
                            canonical_json_bytes(item.as_dict()),
                        ),
                    )
                ),
            )
        hashes = tuple(sorted(_sha256(value, "lineage_hashes") for value in self.lineage_hashes))
        if len(hashes) != len(set(hashes)):
            raise ValueError("lineage_hashes must not contain duplicates")
        object.__setattr__(self, "lineage_hashes", hashes)
        object.__setattr__(self, "blockers", tuple(sorted(set(self.blockers))))
        object.__setattr__(self, "limitations", tuple(sorted(set(self.limitations))))

    @property
    def authority(self) -> dict[str, bool]:
        return dict(TEMPORAL_OAV_AUTHORITY_FLAGS)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "state": self.state.value,
            "formula_sha256": self.formula_sha256,
            "dose_receipt_sha256": self.dose_receipt_sha256,
            "protocol_sha256": self.protocol_sha256,
            "measurement_context_sha256": self.measurement_context_sha256,
            "declared_cells": [item.as_dict() for item in self.declared_cells],
            "measured_cells": [item.as_dict() for item in self.measured_cells],
            "modeled_cells": [item.as_dict() for item in self.modeled_cells],
            "missing_cells": [item.as_dict() for item in self.missing_cells],
            "invalid_cells": [item.as_dict() for item in self.invalid_cells],
            "lineage_hashes": list(self.lineage_hashes),
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
            "authority": self.authority,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def result_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())

    @classmethod
    def from_dict(cls, payload: object) -> TemporalOAVEvidenceResult:
        fields = {
            "schema_version",
            "state",
            "formula_sha256",
            "dose_receipt_sha256",
            "protocol_sha256",
            "measurement_context_sha256",
            "declared_cells",
            "measured_cells",
            "modeled_cells",
            "missing_cells",
            "invalid_cells",
            "lineage_hashes",
            "blockers",
            "limitations",
            "authority",
        }
        if not isinstance(payload, dict) or set(payload) != fields:
            raise ValueError("temporal OAV result does not match the closed schema")
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {cls.SCHEMA_VERSION}")
        if payload["authority"] != TEMPORAL_OAV_AUTHORITY_FLAGS:
            raise ValueError("authority must be the exact all-false mapping")
        return cls(
            state=TemporalOAVEvidenceState(payload["state"]),
            formula_sha256=payload["formula_sha256"],
            dose_receipt_sha256=payload["dose_receipt_sha256"],
            protocol_sha256=payload["protocol_sha256"],
            measurement_context_sha256=payload["measurement_context_sha256"],
            declared_cells=tuple(
                OAVTimepointKey.from_dict(item) for item in payload["declared_cells"]
            ),
            measured_cells=tuple(
                TemporalOAVCellResult.from_dict(item)
                for item in payload["measured_cells"]
            ),
            modeled_cells=tuple(
                TemporalOAVCellResult.from_dict(item)
                for item in payload["modeled_cells"]
            ),
            missing_cells=tuple(
                OAVTimepointKey.from_dict(item) for item in payload["missing_cells"]
            ),
            invalid_cells=tuple(
                TemporalOAVCellResult.from_dict(item)
                for item in payload["invalid_cells"]
            ),
            lineage_hashes=tuple(payload["lineage_hashes"]),
            blockers=tuple(payload["blockers"]),
            limitations=tuple(payload["limitations"]),
        )


def _invalid_row(
    row: OAVMaterialEvidenceInput,
    blockers: list[str],
    limitations: list[str],
) -> OAVMaterialEvidenceResult:
    return OAVMaterialEvidenceResult(
        material_name=row.material_name,
        canonical_name=row.canonical_name,
        state=OAVEvidenceState.INVALID,
        headspace_basis=row.headspace.basis,
        threshold_basis=row.threshold.basis,
        oav=None,
        threshold_screening="NOT_COMPUTABLE",
        recognizable_in_mixture=None,
        constituent_evidence_count=len(row.constituent_evidence),
        blockers=tuple(blockers),
        limitations=tuple(limitations),
    )


def _evaluate_row(
    row: OAVMaterialEvidenceInput,
    measurement_context: str,
) -> OAVMaterialEvidenceResult:
    blockers: list[str] = []
    limitations = [
        "OAV is a threshold-screening ratio only and does not establish mixture recognition."
    ]
    if row.constituent_evidence and not row.natural_or_preblend:
        blockers.append("constituent evidence is attached to a monomolecular row")
    for label, evidence in (("headspace", row.headspace), ("threshold", row.threshold)):
        if evidence.basis is not EvidenceBasis.UNKNOWN:
            if not _same_text(evidence.context, measurement_context):
                blockers.append(f"{label} context does not match request context")
    if (
        row.headspace.basis is not EvidenceBasis.UNKNOWN
        and row.threshold.basis is not EvidenceBasis.UNKNOWN
        and not _same_text(row.headspace.unit, row.threshold.unit)
    ):
        blockers.append("headspace and threshold units are incompatible")
    if row.threshold.value is not None and row.threshold.value <= 0:
        blockers.append("threshold must be greater than zero")
    if blockers:
        return _invalid_row(row, blockers, limitations)

    if (
        row.headspace.basis is EvidenceBasis.UNKNOWN
        or row.threshold.basis is EvidenceBasis.UNKNOWN
    ):
        limitations.append("An unknown quantitative field prevents OAV calculation.")
        return OAVMaterialEvidenceResult(
            material_name=row.material_name,
            canonical_name=row.canonical_name,
            state=OAVEvidenceState.ABSTAINED,
            headspace_basis=row.headspace.basis,
            threshold_basis=row.threshold.basis,
            oav=None,
            threshold_screening="NOT_COMPUTABLE",
            recognizable_in_mixture=None,
            constituent_evidence_count=len(row.constituent_evidence),
            blockers=(),
            limitations=tuple(limitations),
        )

    oav_value = float(row.headspace.value or 0.0) / float(row.threshold.value or 1.0)
    threshold_screening = (
        "ABOVE_OR_AT_THRESHOLD" if oav_value >= 1 else "BELOW_THRESHOLD"
    )
    incomplete_lineage = (
        row.exact_stock_ref is None
        or row.supplied_strength_fraction is None
        or row.active_mass_g is None
        or (
            row.supplied_strength_fraction is not None
            and row.supplied_strength_fraction < 1
            and row.carrier is None
        )
    )
    transferred = EvidenceBasis.TRANSFERRED in {
        row.headspace.basis,
        row.threshold.basis,
    }
    natural_uncertainty = row.natural_or_preblend
    if incomplete_lineage:
        limitations.append("Exact stock or active-dose lineage is incomplete.")
    if transferred:
        limitations.append("At least one quantitative value is transferred evidence.")
    if natural_uncertainty:
        limitations.append(
            "The natural or preblend remains one formula row with constituent uncertainty."
        )
    if incomplete_lineage or transferred or natural_uncertainty:
        state = OAVEvidenceState.PARTIAL
    elif EvidenceBasis.MODELED in {row.headspace.basis, row.threshold.basis}:
        state = OAVEvidenceState.MODELED_SCREEN
        limitations.insert(
            0,
            "Modeled headspace or threshold is a prediction screen, not observed behavior.",
        )
    else:
        state = OAVEvidenceState.STRICT_MEASURED
    return OAVMaterialEvidenceResult(
        material_name=row.material_name,
        canonical_name=row.canonical_name,
        state=state,
        headspace_basis=row.headspace.basis,
        threshold_basis=row.threshold.basis,
        oav=oav_value,
        threshold_screening=threshold_screening,
        recognizable_in_mixture=None,
        constituent_evidence_count=len(row.constituent_evidence),
        blockers=(),
        limitations=tuple(limitations),
    )


def evaluate_oav_evidence(request: OAVEvidenceRequest) -> OAVEvidenceResult:
    """Evaluate row-level OAV evidence without aggregate sensory authority."""

    if not isinstance(request, OAVEvidenceRequest):
        raise TypeError("request must be an OAVEvidenceRequest")
    blockers: list[str] = []
    blockers.extend(_dose_receipt_blockers(request))
    names = [row.material_name.casefold() for row in request.rows]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        blockers.append("duplicate material row: " + ", ".join(duplicates))
    rows = tuple(
        _evaluate_row(row, request.measurement_context) for row in request.rows
    )
    blockers.extend(
        f"{row.material_name}: {blocker}"
        for row in rows
        for blocker in row.blockers
    )
    row_states = {row.state for row in rows}
    if blockers or OAVEvidenceState.INVALID in row_states:
        state = OAVEvidenceState.INVALID
    elif not rows or row_states == {OAVEvidenceState.ABSTAINED}:
        state = OAVEvidenceState.ABSTAINED
    elif OAVEvidenceState.ABSTAINED in row_states or OAVEvidenceState.PARTIAL in row_states:
        state = OAVEvidenceState.PARTIAL
    elif row_states == {OAVEvidenceState.STRICT_MEASURED}:
        state = OAVEvidenceState.STRICT_MEASURED
    else:
        state = OAVEvidenceState.MODELED_SCREEN
    limitations = (
        "OAV rows cannot establish odor contribution, balance, diffusion, liking, beauty, synergy, similarity, or release readiness.",
        "Perceptible-material count cannot increase evidence authority.",
    )
    return OAVEvidenceResult(
        state=state,
        formula_sha256=request.formula_sha256,
        dose_receipt_sha256=request.dose_receipt_sha256,
        measurement_context=request.measurement_context,
        rows=rows,
        blockers=tuple(blockers),
        limitations=limitations,
    )


def _temporal_cell_result(
    cell: OAVTimepointEvidenceInput,
    *,
    blocker_codes: Iterable[str] = (),
    whole_material_screen: bool = False,
) -> TemporalOAVCellResult:
    blockers = tuple(blocker_codes)
    limitations = (
        "OAV is a diagnostic threshold ratio and does not establish perceived odor contribution.",
    )
    if blockers or _interval_is_unknown(cell.headspace_interval) or _interval_is_unknown(
        cell.threshold_interval
    ):
        return TemporalOAVCellResult(
            evidence=cell,
            oav_interval=None,
            threshold_screening="NOT_COMPUTABLE",
            whole_material_screen=whole_material_screen,
            blockers=blockers,
            limitations=limitations,
        )
    oav_interval = (
        float(cell.headspace_interval.p05.value)
        / float(cell.threshold_interval.p95.value),
        float(cell.headspace_interval.p50.value)
        / float(cell.threshold_interval.p50.value),
        float(cell.headspace_interval.p95.value)
        / float(cell.threshold_interval.p05.value),
    )
    screening = (
        "ABOVE_OR_AT_THRESHOLD"
        if oav_interval[1] >= 1
        else "BELOW_THRESHOLD"
    )
    return TemporalOAVCellResult(
        evidence=cell,
        oav_interval=oav_interval,
        threshold_screening=screening,
        whole_material_screen=whole_material_screen,
        blockers=(),
        limitations=limitations,
    )


def _tier_blocker(cell: OAVTimepointEvidenceInput) -> str | None:
    bases = {
        cell.headspace_interval.p05.basis,
        cell.threshold_interval.p05.basis,
    }
    if cell.model_tier is OAVModelTier.T0_UNKNOWN:
        return None if bases == {EvidenceBasis.UNKNOWN} else "MODEL_TIER_BASIS_MISMATCH"
    if EvidenceBasis.UNKNOWN in bases:
        return "MODEL_TIER_BASIS_MISMATCH"
    if cell.model_tier is OAVModelTier.T4_MEASURED:
        return None if bases == {EvidenceBasis.MEASURED} else "MODEL_TIER_BASIS_MISMATCH"
    if cell.model_tier is OAVModelTier.T1_TRANSFERRED:
        return (
            None
            if EvidenceBasis.TRANSFERRED in bases and EvidenceBasis.MODELED not in bases
            else "MODEL_TIER_BASIS_MISMATCH"
        )
    if cell.model_tier in {
        OAVModelTier.T2_MODELED,
        OAVModelTier.T3_CALIBRATED_MODELED,
    }:
        return (
            None
            if EvidenceBasis.MODELED in bases
            else "MODEL_TIER_BASIS_MISMATCH"
        )
    return "MODEL_TIER_BASIS_MISMATCH"


def _cell_compatibility_blockers(cell: OAVTimepointEvidenceInput) -> tuple[str, ...]:
    blockers: list[str] = []
    tier_blocker = _tier_blocker(cell)
    if tier_blocker is not None:
        blockers.append(tier_blocker)
    if cell.model_tier is OAVModelTier.T0_UNKNOWN:
        return tuple(blockers)
    headspace = cell.headspace_interval.p50
    threshold = cell.threshold_interval.p50
    if not _same_text(headspace.unit, threshold.unit):
        blockers.append("INCOMPATIBLE_UNITS")
    if not _same_text(headspace.context, threshold.context):
        blockers.append("INCOMPATIBLE_CONTEXT")
    if _interval_source_signature(cell.headspace_interval) == b"INCONSISTENT":
        blockers.append("INCONSISTENT_HEADSPACE_SOURCE")
    if _interval_source_signature(cell.threshold_interval) == b"INCONSISTENT":
        blockers.append("INCONSISTENT_THRESHOLD_SOURCE")
    return tuple(blockers)


def _threshold_signature(cell: OAVTimepointEvidenceInput) -> bytes:
    threshold = cell.threshold_interval.p50
    return canonical_json_bytes(
        {
            "material_id": cell.key.material_id,
            "endpoint": cell.key.endpoint,
            "unit": threshold.unit,
            "context": threshold.context,
            "method": threshold.method,
            "basis": threshold.basis.value,
            "source": (
                None if threshold.source is None else threshold.source.as_dict()
            ),
        }
    )


def _temporal_source_hashes(
    cells: Iterable[OAVTimepointEvidenceInput],
) -> tuple[str, ...]:
    hashes: set[str] = set()
    for cell in cells:
        for interval in (cell.headspace_interval, cell.threshold_interval):
            for evidence in (interval.p05, interval.p50, interval.p95):
                if evidence.source is not None and evidence.source.source_sha256 is not None:
                    hashes.add(evidence.source.source_sha256)
    return tuple(sorted(hashes))


def evaluate_temporal_oav_evidence(
    request: TemporalOAVEvidenceRequest,
    *,
    declared_cells: Iterable[OAVTimepointKey] | None = None,
    natural_or_preblend_material_ids: Iterable[str] = (),
    constituent_specific_material_ids: Iterable[str] = (),
) -> TemporalOAVEvidenceResult:
    """Evaluate typed temporal OAV cells without filling or merging evidence series."""

    if not isinstance(request, TemporalOAVEvidenceRequest):
        raise TypeError("request must be a TemporalOAVEvidenceRequest")
    observed_cells = tuple(request.cells)
    if declared_cells is None:
        declared_input = tuple(dict.fromkeys(cell.key for cell in observed_cells))
    else:
        declared_input = tuple(declared_cells)
    if any(not isinstance(key, OAVTimepointKey) for key in declared_input):
        raise TypeError("declared_cells must contain OAVTimepointKey")
    if any(key.protocol_sha256 != request.protocol_sha256 for key in declared_input):
        raise ValueError("declared cell protocol does not match request protocol")

    blockers: list[str] = []
    declared_counts = Counter(declared_input)
    duplicate_declared = {
        key for key, count in declared_counts.items() if count > 1
    }
    blockers.extend(
        f"DUPLICATE_DECLARED_CELL:{_timepoint_token(key)}"
        for key in sorted(duplicate_declared, key=_timepoint_sort_key)
    )
    declared = tuple(sorted(set(declared_input), key=_timepoint_sort_key))
    declared_set = set(declared)

    observed_counts = Counter(cell.key for cell in observed_cells)
    duplicate_observed = {
        key for key, count in observed_counts.items() if count > 1
    }
    undeclared = {cell.key for cell in observed_cells if cell.key not in declared_set}
    blockers.extend(
        f"DUPLICATE_CELL:{_timepoint_token(key)}"
        for key in sorted(duplicate_observed, key=_timepoint_sort_key)
    )
    blockers.extend(
        f"UNDECLARED_CELL:{_timepoint_token(key)}"
        for key in sorted(undeclared, key=_timepoint_sort_key)
    )

    missing_set = declared_set.difference(observed_counts)
    natural_ids = _normalized_strings(
        natural_or_preblend_material_ids, "natural_or_preblend_material_ids"
    )
    constituent_ids = _normalized_strings(
        constituent_specific_material_ids, "constituent_specific_material_ids"
    )
    measured: list[TemporalOAVCellResult] = []
    modeled: list[TemporalOAVCellResult] = []
    invalid: list[TemporalOAVCellResult] = []
    valid_cells: list[OAVTimepointEvidenceInput] = []

    for cell in sorted(
        observed_cells,
        key=lambda item: (
            _timepoint_sort_key(item.key),
            canonical_json_bytes(item.as_dict()),
        ),
    ):
        key = cell.key
        critical_codes: list[str] = []
        if key in duplicate_observed:
            critical_codes.append("DUPLICATE_CELL")
        if key in undeclared:
            critical_codes.append("UNDECLARED_CELL")
        critical_codes.extend(_cell_compatibility_blockers(cell))
        whole_material = (
            key.material_id.casefold() in natural_ids
            and key.material_id.casefold() not in constituent_ids
        )
        if critical_codes:
            invalid.append(
                _temporal_cell_result(
                    cell,
                    blocker_codes=tuple(
                        f"{code}:{_timepoint_token(key)}" for code in critical_codes
                    ),
                    whole_material_screen=whole_material,
                )
            )
            blockers.extend(
                f"{code}:{_timepoint_token(key)}" for code in critical_codes
            )
            continue
        if cell.model_tier is OAVModelTier.T0_UNKNOWN:
            missing_set.add(key)
            continue
        result = _temporal_cell_result(
            cell, whole_material_screen=whole_material
        )
        valid_cells.append(cell)
        if cell.model_tier is OAVModelTier.T4_MEASURED:
            measured.append(result)
        else:
            modeled.append(result)
        if cell.exact_stock_ref is None or cell.active_mass_g is None:
            blockers.append(f"MISSING_STOCK_LINEAGE:{_timepoint_token(key)}")
        if whole_material:
            blockers.append(
                f"NATURAL_PREBLEND_WHOLE_MATERIAL_ONLY:{_timepoint_token(key)}"
            )

    missing = tuple(sorted(missing_set, key=_timepoint_sort_key))
    blockers.extend(
        f"MISSING_DECLARED_CELL:{_timepoint_token(key)}"
        for key in missing
        if key not in observed_counts
    )

    threshold_groups: dict[
        tuple[str, str, str, str], set[bytes]
    ] = defaultdict(set)
    for cell in valid_cells:
        threshold_groups[
            (
                cell.key.protocol_sha256,
                cell.key.sample_id.casefold(),
                cell.key.material_id.casefold(),
                cell.key.endpoint.casefold(),
            )
        ].add(_threshold_signature(cell))
    for group, signatures in sorted(threshold_groups.items()):
        if len(signatures) > 1:
            blockers.append(
                "THRESHOLD_CANCELLATION_INCOMPATIBLE:" + ":".join(group)
            )
    if measured and modeled:
        blockers.append("MIXED_MEASURED_MODELED_SERIES")

    critical = bool(invalid or duplicate_declared)
    if critical:
        state = TemporalOAVEvidenceState.INVALID
    elif not measured and not modeled:
        state = TemporalOAVEvidenceState.ABSTAINED
    elif blockers:
        state = TemporalOAVEvidenceState.PARTIAL
    elif measured and not modeled:
        state = TemporalOAVEvidenceState.STRICT_MEASURED_TIME_SERIES
    elif modeled and not measured:
        state = TemporalOAVEvidenceState.MODELED_SCREEN
    else:
        state = TemporalOAVEvidenceState.PARTIAL

    declared_sha256 = sha256_hex(
        canonical_json_bytes([key.as_dict() for key in declared])
    )
    lineage_hashes = {
        request.formula_sha256,
        request.dose_receipt_sha256,
        request.protocol_sha256,
        request.measurement_context_sha256,
        declared_sha256,
        *_temporal_source_hashes(observed_cells),
    }
    limitations = (
        "OAV intervals are diagnostic calculations, not perceived depth, richness, liking, beauty, or mixture recognition.",
        "Measured and modeled cells remain separate and are never substituted for one another.",
        "Missing cells remain missing and are never interpolated.",
        "No result grants formula, compounding, sensory, safety, purchase, runtime, release, or publication authority.",
    )
    return TemporalOAVEvidenceResult(
        state=state,
        formula_sha256=request.formula_sha256,
        dose_receipt_sha256=request.dose_receipt_sha256,
        protocol_sha256=request.protocol_sha256,
        measurement_context_sha256=request.measurement_context_sha256,
        declared_cells=declared,
        measured_cells=tuple(measured),
        modeled_cells=tuple(modeled),
        missing_cells=missing,
        invalid_cells=tuple(invalid),
        lineage_hashes=tuple(lineage_hashes),
        blockers=tuple(blockers),
        limitations=limitations,
    )


def _dose_receipt_blockers(request: OAVEvidenceRequest) -> tuple[str, ...]:
    receipt = request.dose_receipt
    if receipt is None:
        return ()
    core = dict(receipt)
    claimed = core.pop("receipt_sha256", None)
    observed = stable_json_hash(core)
    blockers: list[str] = []
    if claimed != request.dose_receipt_sha256 or observed != request.dose_receipt_sha256:
        blockers.append("dose receipt hash does not match supplied receipt bytes")
        return tuple(blockers)
    raw_lines = core.get("lines")
    if not isinstance(raw_lines, list):
        return ("dose receipt lines are missing or malformed",)
    lines = {
        str(line.get("material_name", "")).strip().casefold(): line
        for line in raw_lines
        if isinstance(line, Mapping)
    }
    for row in request.rows:
        line = lines.get(row.material_name.casefold())
        if line is None:
            blockers.append(f"{row.material_name}: dose receipt line is missing")
            continue
        if line.get("stock_id") != row.exact_stock_ref:
            blockers.append(f"{row.material_name}: exact stock reference mismatch")
        expected_strength = line.get("stock_fraction")
        if expected_strength is None or row.supplied_strength_fraction is None:
            if expected_strength != row.supplied_strength_fraction:
                blockers.append(f"{row.material_name}: stock strength mismatch")
        elif abs(float(expected_strength) - row.supplied_strength_fraction) > 1e-12:
            blockers.append(f"{row.material_name}: stock strength mismatch")
        expected_carrier = str(line.get("carrier") or "").strip().casefold()
        observed_carrier = str(row.carrier or "").strip().casefold()
        if expected_carrier != observed_carrier:
            blockers.append(f"{row.material_name}: carrier mismatch")
    return tuple(blockers)


def _lookup(mapping: Mapping[str, Any], name: str, canonical_name: str) -> Any:
    if name in mapping:
        return mapping[name]
    return mapping.get(canonical_name)


def oav_evidence_request_from_formula_state(
    state: FormulaState,
    *,
    formula_sha256: str,
    dose_receipt_sha256: str,
    exact_stock_refs: Mapping[str, str],
    model_source: EvidenceSourceRef,
    threshold_sources: Mapping[str, EvidenceSourceRef],
    dose_receipt: Mapping[str, Any] | None = None,
) -> OAVEvidenceRequest:
    """Adapt modeled FormulaState values without upgrading their evidence basis."""

    if not isinstance(state, FormulaState):
        raise TypeError("state must be a FormulaState")
    if not isinstance(model_source, EvidenceSourceRef):
        raise TypeError("model_source must be an EvidenceSourceRef")
    rows: list[OAVMaterialEvidenceInput] = []
    for material in state.materials:
        threshold_source = _lookup(
            threshold_sources, material.name, material.canonical_name
        )
        if material.odt_air_ppm is None or threshold_source is None:
            threshold = QuantitativeEvidence(
                value=None,
                unit="",
                context="",
                method="",
                basis=EvidenceBasis.UNKNOWN,
                source=None,
            )
        else:
            threshold = QuantitativeEvidence(
                value=float(material.odt_air_ppm),
                unit="ppm",
                context=state.context,
                method=str(material.sources.get("odt", "formula-state ODT lookup")),
                basis=EvidenceBasis.TRANSFERRED,
                source=threshold_source,
            )
        rows.append(
            OAVMaterialEvidenceInput(
                material_name=material.name,
                canonical_name=material.canonical_name,
                exact_stock_ref=_lookup(
                    exact_stock_refs, material.name, material.canonical_name
                ),
                supplied_strength_fraction=(
                    float(material.dilution) if material.stock_declared else None
                ),
                carrier=material.stock_carrier or None,
                active_mass_g=material.authoritative_active_g,
                formula_matrix=state.headspace_basis,
                headspace=QuantitativeEvidence(
                    value=float(material.vapor_ppm),
                    unit="ppm",
                    context=state.context,
                    method=state.headspace_basis,
                    basis=EvidenceBasis.MODELED,
                    source=model_source,
                ),
                threshold=threshold,
                natural_or_preblend=(
                    material.is_opaque_preblend
                    or "natural_composite" in material.sources
                ),
                constituent_evidence=(),
            )
        )
    return OAVEvidenceRequest(
        formula_sha256=formula_sha256,
        dose_receipt_sha256=dose_receipt_sha256,
        measurement_context=state.context,
        rows=tuple(rows),
        dose_receipt=dose_receipt,
    )


__all__ = [
    "OAVIntervalEvidence",
    "OAVModelTier",
    "OAVEvidenceRequest",
    "OAVEvidenceResult",
    "OAVEvidenceState",
    "OAVMaterialEvidenceInput",
    "OAVMaterialEvidenceResult",
    "OAVTimepointEvidenceInput",
    "OAVTimepointKey",
    "TemporalOAVCellResult",
    "TemporalOAVEvidenceRequest",
    "TemporalOAVEvidenceResult",
    "TemporalOAVEvidenceState",
    "evaluate_oav_evidence",
    "evaluate_temporal_oav_evidence",
    "oav_evidence_request_from_formula_state",
]
