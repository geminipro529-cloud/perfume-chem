"""Closed scientific-source, construct, and transfer contracts for SolForge."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from math import isfinite
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from engine.evidence_contracts import (
    EvidenceBasis,
    EvidenceSourceRef,
    QuantitativeEvidence,
    canonical_json_bytes,
    sha256_hex,
)

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(
    r"^(doi|pmid|pmcid|iso|astm):\S+$", re.IGNORECASE
)
_RIGHTS = frozenset(
    {
        "METADATA_AND_DERIVED_SUMMARY_ONLY",
        "OPEN_ACCESS_METADATA_AND_DERIVED_SUMMARY_ONLY",
        "OPEN_ACCESS_RETAINED_BYTES",
        "PUBLIC_STANDARD_METADATA_ONLY",
    }
)

EVIDENCE_REVIEW_AUTHORITY_FLAGS = {
    "formula": False,
    "inventory_mutation": False,
    "liking": False,
    "physical_execution": False,
    "publication": False,
    "purchase": False,
    "release": False,
    "runtime": False,
    "safety": False,
    "scientific_claim": False,
    "sensory": False,
}

_CONSTRUCT_IDS = (
    "LIKING",
    "PERCEIVED_RICHNESS",
    "PERCEIVED_DEPTH",
    "CONFIGURATIONAL_INTEGRATION",
    "HIERARCHY_CONTRAST",
    "TEMPORAL_DIFFERENTIATION",
    "TARGET_FIDELITY",
    "INTENSITY",
    "FAMILIARITY",
    "DETECTABILITY",
)

_OAV_MODEL_TIERS = (
    "T0_UNKNOWN",
    "T1_TRANSFERRED",
    "T2_MODELED",
    "T3_CALIBRATED_MODELED",
    "T4_MEASURED",
)
_OAV_CELL_KEY_FIELDS = (
    "protocol_sha256",
    "sample_id",
    "material_id",
    "time_seconds",
    "endpoint",
)
_OAV_COMPATIBILITY_FIELDS = (
    "material_identity",
    "threshold_source",
    "matrix",
    "method",
    "temperature",
    "application",
    "endpoint",
    "unit",
)
_OAV_FORBIDDEN_INFERENCES = (
    "LIKING_FROM_OAV",
    "MIXTURE_RECOGNITION_FROM_OAV",
    "PERCEIVED_DEPTH_FROM_OAV",
    "PERCEIVED_RICHNESS_FROM_OAV",
    "SAFETY_FROM_OAV",
    "RELEASE_FROM_OAV",
    "INTERPOLATED_OBSERVATION",
    "MODEL_TIER_AS_CONFIDENCE_PERCENTAGE",
)
_HEDONIC_CRITERIA = (
    "TARGET_FIDELITY",
    "DEPTH",
    "RICHNESS",
    "LIKING",
)
_HEDONIC_SCOPES = (
    "OWNER",
    "TRAINED_PANEL",
    "CONSUMER_POPULATION",
)
_HEDONIC_PREOBSERVATION_FIELDS = (
    "protocol_sha256",
    "comparison_id",
    "assessor_id",
    "sample_codes",
    "criterion",
    "time_seconds",
    "first_presented_item",
    "predecessor_item",
    "repeat_id",
    "session_id",
    "schedule_sha256",
    "washout_seconds",
    "cluster_unit",
    "heldout_unit",
    "baseline",
    "seed",
    "stopping_rule",
    "safety_stop",
)
_HEDONIC_FORBIDDEN_FEATURES = (
    "OAV",
    "FORMULA_COMPOSITION",
    "INGREDIENT_COUNT",
    "BRAND",
    "PRICE",
    "PRESTIGE",
    "LUXURY_LANGUAGE",
    "PERFUME_IDENTITY",
)

TEMPORAL_OAV_INTERFACE_FIELDS = {
    "OAVTimepointKey": list(_OAV_CELL_KEY_FIELDS),
    "OAVIntervalEvidence": ["p05", "p50", "p95"],
    "OAVTimepointEvidenceInput": [
        "key",
        "exact_stock_ref",
        "active_mass_g",
        "headspace_interval",
        "threshold_interval",
        "model_tier",
        "context_sha256",
    ],
    "TemporalOAVEvidenceRequest": [
        "formula_sha256",
        "dose_receipt_sha256",
        "protocol_sha256",
        "measurement_context_sha256",
        "cells",
    ],
}

INTERFACE_FREEZE_POLICY_DECISIONS = (
    "CANONICAL_TIME_INTEGER_SECONDS",
    "PROTOCOL_DECLARED_TIMEPOINTS",
    "P05_P50_P95_ORDERED_INTERVALS",
    "EXACT_SCOPE_THRESHOLD_CANCELLATION",
    "NATURAL_PREBLEND_NO_SILENT_SUM",
    "MISSING_DATA_NO_INTERPOLATION",
    "MODEL_TIERS_ARE_EVIDENCE_STATES",
    "HEDONIC_CRITERIA_SEPARATE",
    "HEDONIC_SCOPES_SEPARATE",
    "TIES_RETAINED_AS_INDIFFERENCE",
    "NO_SYNTHETIC_BEAUTY_SCORE",
    "NO_PROXY_FEATURES_FOR_DIRECTIONAL_FIT",
    "HELDOUT_BASELINE_REQUIRED",
)


class EvidenceSourceTier(str, Enum):
    DIRECT_FINE_FRAGRANCE = "DIRECT_FINE_FRAGRANCE"
    DIRECT_HUMAN_OLFACTION = "DIRECT_HUMAN_OLFACTION"
    ANALYTICAL_METHOD = "ANALYTICAL_METHOD"
    SYSTEMATIC_SYNTHESIS = "SYSTEMATIC_SYNTHESIS"
    TRANSFERABLE_SENSORY_METHOD = "TRANSFERABLE_SENSORY_METHOD"
    STATISTICAL_FOUNDATION = "STATISTICAL_FOUNDATION"
    HYPOTHESIS_ONLY = "HYPOTHESIS_ONLY"


class TransferDisposition(str, Enum):
    DIRECT = "DIRECT"
    METHOD_ONLY = "METHOD_ONLY"
    NARROWER_SCOPE = "NARROWER_SCOPE"
    HOLD = "HOLD"


class OAVModelTier(str, Enum):
    """Evidence provenance tier; never a confidence or authority score."""

    T0_UNKNOWN = "T0_UNKNOWN"
    T1_TRANSFERRED = "T1_TRANSFERRED"
    T2_MODELED = "T2_MODELED"
    T3_CALIBRATED_MODELED = "T3_CALIBRATED_MODELED"
    T4_MEASURED = "T4_MEASURED"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _texts(value: object, field_name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{field_name} must be a sequence")
    result = tuple(_text(item, field_name) for item in value)
    if not allow_empty and not result:
        raise ValueError(f"{field_name} must be nonempty")
    if len(result) != len(set(result)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


def _sha(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def _boolean(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be bool")
    return value


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _text(value, field_name)


def _nonnegative_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric")
    number = float(value)
    if not isfinite(number) or number < 0:
        raise ValueError(f"{field_name} must be finite and nonnegative")
    return number


def _quantitative_from_dict(payload: object) -> QuantitativeEvidence:
    if not isinstance(payload, dict) or set(payload) != {
        "value",
        "unit",
        "context",
        "method",
        "basis",
        "source",
        "uncertainty",
    }:
        raise ValueError("quantitative evidence does not match the closed schema")
    source_payload = payload["source"]
    source = None
    if source_payload is not None:
        if not isinstance(source_payload, dict) or set(source_payload) != {
            "source_id",
            "source_uri",
            "retrieved_on",
            "source_sha256",
        }:
            raise ValueError("evidence source reference does not match the closed schema")
        source = EvidenceSourceRef(**source_payload)
    return QuantitativeEvidence(
        value=payload["value"],
        unit=payload["unit"],
        context=payload["context"],
        method=payload["method"],
        basis=EvidenceBasis(payload["basis"]),
        source=source,
        uncertainty=payload["uncertainty"],
    )


def _closed_payload(
    payload: object,
    *,
    schema_version: str,
    fields: frozenset[str],
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise TypeError("payload must be an object")
    expected = fields | {"schema_version", "authority_flags"}
    if set(payload) != expected:
        raise ValueError("payload does not match the closed schema")
    if payload["schema_version"] != schema_version:
        raise ValueError(f"schema_version must be {schema_version}")
    if payload["authority_flags"] != EVIDENCE_REVIEW_AUTHORITY_FLAGS:
        raise ValueError("authority_flags must be the exact all-false mapping")
    return {field: payload[field] for field in fields}


class _Record:
    SCHEMA_VERSION: ClassVar[str]

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())

    def _envelope(self, values: dict[str, object]) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **values,
            "authority_flags": dict(EVIDENCE_REVIEW_AUTHORITY_FLAGS),
        }


@dataclass(frozen=True, slots=True)
class OAVTimepointKey:
    """Canonical identity for one declared temporal OAV evidence cell."""

    protocol_sha256: str
    sample_id: str
    material_id: str
    time_seconds: int
    endpoint: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "protocol_sha256", _sha(self.protocol_sha256, "protocol_sha256")
        )
        for field_name in ("sample_id", "material_id", "endpoint"):
            object.__setattr__(
                self, field_name, _text(getattr(self, field_name), field_name)
            )
        if (
            isinstance(self.time_seconds, bool)
            or not isinstance(self.time_seconds, int)
            or self.time_seconds < 0
        ):
            raise ValueError("time_seconds must use nonnegative integer seconds")

    def as_dict(self) -> dict[str, object]:
        return {
            "protocol_sha256": self.protocol_sha256,
            "sample_id": self.sample_id,
            "material_id": self.material_id,
            "time_seconds": self.time_seconds,
            "endpoint": self.endpoint,
        }

    @classmethod
    def from_dict(cls, payload: object) -> OAVTimepointKey:
        if not isinstance(payload, dict) or set(payload) != set(_OAV_CELL_KEY_FIELDS):
            raise ValueError("OAV timepoint key does not match the frozen interface")
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class OAVIntervalEvidence:
    """Ordered P05/P50/P95 evidence from one compatible quantitative scope."""

    p05: QuantitativeEvidence
    p50: QuantitativeEvidence
    p95: QuantitativeEvidence

    def __post_init__(self) -> None:
        evidence = (self.p05, self.p50, self.p95)
        if any(not isinstance(item, QuantitativeEvidence) for item in evidence):
            raise TypeError("OAV interval members must be QuantitativeEvidence")
        bases = {item.basis for item in evidence}
        if bases == {EvidenceBasis.UNKNOWN}:
            return
        if EvidenceBasis.UNKNOWN in bases:
            raise ValueError("OAV interval cannot mix known and unknown evidence")
        scopes = {(item.unit, item.context, item.method, item.basis) for item in evidence}
        if len(scopes) != 1:
            raise ValueError("OAV interval evidence scope and units must match")
        values = tuple(item.value for item in evidence)
        if any(value is None or value <= 0 for value in values):
            raise ValueError("OAV interval values must be positive")
        if not values[0] <= values[1] <= values[2]:
            raise ValueError("OAV interval must satisfy P05 <= P50 <= P95")

    def as_dict(self) -> dict[str, object]:
        return {
            "p05": self.p05.as_dict(),
            "p50": self.p50.as_dict(),
            "p95": self.p95.as_dict(),
        }

    @classmethod
    def from_dict(cls, payload: object) -> OAVIntervalEvidence:
        if not isinstance(payload, dict) or set(payload) != {"p05", "p50", "p95"}:
            raise ValueError("OAV interval does not match the frozen interface")
        return cls(
            p05=_quantitative_from_dict(payload["p05"]),
            p50=_quantitative_from_dict(payload["p50"]),
            p95=_quantitative_from_dict(payload["p95"]),
        )


@dataclass(frozen=True, slots=True)
class OAVTimepointEvidenceInput:
    """One measured, modeled, transferred, or explicitly missing OAV cell."""

    key: OAVTimepointKey
    exact_stock_ref: str | None
    active_mass_g: float | None
    headspace_interval: OAVIntervalEvidence
    threshold_interval: OAVIntervalEvidence
    model_tier: OAVModelTier
    context_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, OAVTimepointKey):
            raise TypeError("key must be OAVTimepointKey")
        object.__setattr__(
            self,
            "exact_stock_ref",
            _optional_text(self.exact_stock_ref, "exact_stock_ref"),
        )
        if self.active_mass_g is not None:
            object.__setattr__(
                self,
                "active_mass_g",
                _nonnegative_number(self.active_mass_g, "active_mass_g"),
            )
        for field_name in ("headspace_interval", "threshold_interval"):
            if not isinstance(getattr(self, field_name), OAVIntervalEvidence):
                raise TypeError(f"{field_name} must be OAVIntervalEvidence")
        object.__setattr__(self, "model_tier", OAVModelTier(self.model_tier))
        object.__setattr__(
            self, "context_sha256", _sha(self.context_sha256, "context_sha256")
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key.as_dict(),
            "exact_stock_ref": self.exact_stock_ref,
            "active_mass_g": self.active_mass_g,
            "headspace_interval": self.headspace_interval.as_dict(),
            "threshold_interval": self.threshold_interval.as_dict(),
            "model_tier": self.model_tier.value,
            "context_sha256": self.context_sha256,
        }

    @classmethod
    def from_dict(cls, payload: object) -> OAVTimepointEvidenceInput:
        fields = tuple(TEMPORAL_OAV_INTERFACE_FIELDS["OAVTimepointEvidenceInput"])
        if not isinstance(payload, dict) or set(payload) != set(fields):
            raise ValueError("OAV timepoint input does not match the frozen interface")
        return cls(
            key=OAVTimepointKey.from_dict(payload["key"]),
            exact_stock_ref=payload["exact_stock_ref"],
            active_mass_g=payload["active_mass_g"],
            headspace_interval=OAVIntervalEvidence.from_dict(
                payload["headspace_interval"]
            ),
            threshold_interval=OAVIntervalEvidence.from_dict(
                payload["threshold_interval"]
            ),
            model_tier=OAVModelTier(payload["model_tier"]),
            context_sha256=payload["context_sha256"],
        )


@dataclass(frozen=True, slots=True)
class TemporalOAVEvidenceRequest:
    """Hash-bound temporal OAV request with no perceptual authority."""

    formula_sha256: str
    dose_receipt_sha256: str
    protocol_sha256: str
    measurement_context_sha256: str
    cells: tuple[OAVTimepointEvidenceInput, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "formula_sha256",
            "dose_receipt_sha256",
            "protocol_sha256",
            "measurement_context_sha256",
        ):
            object.__setattr__(
                self, field_name, _sha(getattr(self, field_name), field_name)
            )
        cells = tuple(self.cells)
        if any(not isinstance(item, OAVTimepointEvidenceInput) for item in cells):
            raise TypeError("cells must contain OAVTimepointEvidenceInput values")
        if any(item.key.protocol_sha256 != self.protocol_sha256 for item in cells):
            raise ValueError("cell protocol_sha256 does not match request protocol_sha256")
        if any(item.context_sha256 != self.measurement_context_sha256 for item in cells):
            raise ValueError(
                "cell context_sha256 does not match measurement_context_sha256"
            )
        object.__setattr__(self, "cells", cells)

    def as_dict(self) -> dict[str, object]:
        return {
            "formula_sha256": self.formula_sha256,
            "dose_receipt_sha256": self.dose_receipt_sha256,
            "protocol_sha256": self.protocol_sha256,
            "measurement_context_sha256": self.measurement_context_sha256,
            "cells": [item.as_dict() for item in self.cells],
        }

    @classmethod
    def from_dict(cls, payload: object) -> TemporalOAVEvidenceRequest:
        fields = tuple(TEMPORAL_OAV_INTERFACE_FIELDS["TemporalOAVEvidenceRequest"])
        if not isinstance(payload, dict) or set(payload) != set(fields):
            raise ValueError("temporal OAV request does not match the frozen interface")
        return cls(
            formula_sha256=payload["formula_sha256"],
            dose_receipt_sha256=payload["dose_receipt_sha256"],
            protocol_sha256=payload["protocol_sha256"],
            measurement_context_sha256=payload["measurement_context_sha256"],
            cells=tuple(
                OAVTimepointEvidenceInput.from_dict(item) for item in payload["cells"]
            ),
        )


@dataclass(frozen=True, slots=True)
class EvidenceSourceRecordV2(_Record):
    """One metadata/derived-summary source record with explicit transfer scope."""

    SCHEMA_VERSION: ClassVar[str] = "evidence_source_record_v2"
    source_id: str
    stable_identifier: str
    uri: str
    title: str
    publication_year: int
    retrieved_on: str
    source_kind: str
    study_design: str
    population: str
    matrix: str
    exposure: str
    endpoints: tuple[str, ...]
    result_used: str
    limitations: tuple[str, ...]
    source_tier: EvidenceSourceTier
    transfer_disposition: TransferDisposition
    rights: str
    code_requirements: tuple[str, ...]
    primary_source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "source_id",
            "stable_identifier",
            "uri",
            "title",
            "retrieved_on",
            "source_kind",
            "study_design",
            "population",
            "matrix",
            "exposure",
            "result_used",
            "rights",
        ):
            object.__setattr__(
                self, field_name, _text(getattr(self, field_name), field_name)
            )
        if _IDENTIFIER_RE.fullmatch(self.stable_identifier) is None:
            raise ValueError("stable_identifier must use a supported stable prefix")
        parsed = urlparse(self.uri)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("uri must be an absolute HTTP(S) URI")
        if isinstance(self.publication_year, bool) or not isinstance(
            self.publication_year, int
        ):
            raise TypeError("publication_year must be an integer")
        if not 1800 <= self.publication_year <= 2100:
            raise ValueError("publication_year is invalid")
        try:
            date.fromisoformat(self.retrieved_on)
        except ValueError as exc:
            raise ValueError("retrieved_on must be an ISO date") from exc
        object.__setattr__(self, "endpoints", _texts(self.endpoints, "endpoints"))
        object.__setattr__(
            self, "limitations", _texts(self.limitations, "limitations")
        )
        object.__setattr__(
            self,
            "code_requirements",
            _texts(self.code_requirements, "code_requirements"),
        )
        object.__setattr__(
            self,
            "primary_source_ids",
            _texts(self.primary_source_ids, "primary_source_ids", allow_empty=True),
        )
        object.__setattr__(self, "source_tier", EvidenceSourceTier(self.source_tier))
        object.__setattr__(
            self,
            "transfer_disposition",
            TransferDisposition(self.transfer_disposition),
        )
        rights = self.rights.upper()
        if rights not in _RIGHTS:
            raise ValueError("rights is not an allowed evidence-rights state")
        object.__setattr__(self, "rights", rights)
        if (
            self.source_tier is EvidenceSourceTier.SYSTEMATIC_SYNTHESIS
            and not self.primary_source_ids
        ):
            raise ValueError("systematic synthesis requires primary source traceability")

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "source_id": self.source_id,
                "stable_identifier": self.stable_identifier,
                "uri": self.uri,
                "title": self.title,
                "publication_year": self.publication_year,
                "retrieved_on": self.retrieved_on,
                "source_kind": self.source_kind,
                "study_design": self.study_design,
                "population": self.population,
                "matrix": self.matrix,
                "exposure": self.exposure,
                "endpoints": list(self.endpoints),
                "result_used": self.result_used,
                "limitations": list(self.limitations),
                "source_tier": self.source_tier.value,
                "transfer_disposition": self.transfer_disposition.value,
                "rights": self.rights,
                "code_requirements": list(self.code_requirements),
                "primary_source_ids": list(self.primary_source_ids),
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> EvidenceSourceRecordV2:
        fields = frozenset(
            {
                "source_id",
                "stable_identifier",
                "uri",
                "title",
                "publication_year",
                "retrieved_on",
                "source_kind",
                "study_design",
                "population",
                "matrix",
                "exposure",
                "endpoints",
                "result_used",
                "limitations",
                "source_tier",
                "transfer_disposition",
                "rights",
                "code_requirements",
                "primary_source_ids",
            }
        )
        values = _closed_payload(
            payload, schema_version=cls.SCHEMA_VERSION, fields=fields
        )
        for field_name in (
            "endpoints",
            "limitations",
            "code_requirements",
            "primary_source_ids",
        ):
            values[field_name] = tuple(values[field_name])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class SourceQualityAssessmentV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "source_quality_assessment_v1"
    source_id: str
    source_record_sha256: str
    tier: EvidenceSourceTier
    primary_source_ids: tuple[str, ...]
    population_declared: bool
    matrix_declared: bool
    endpoint_declared: bool
    order_control_reported: bool
    assessor_dependence_reported: bool
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _text(self.source_id, "source_id"))
        object.__setattr__(
            self,
            "source_record_sha256",
            _sha(self.source_record_sha256, "source_record_sha256"),
        )
        object.__setattr__(self, "tier", EvidenceSourceTier(self.tier))
        object.__setattr__(
            self,
            "primary_source_ids",
            _texts(self.primary_source_ids, "primary_source_ids", allow_empty=True),
        )
        for field_name in (
            "population_declared",
            "matrix_declared",
            "endpoint_declared",
            "order_control_reported",
            "assessor_dependence_reported",
        ):
            object.__setattr__(
                self, field_name, _boolean(getattr(self, field_name), field_name)
            )
        object.__setattr__(
            self, "limitations", _texts(self.limitations, "limitations")
        )

    @property
    def failures(self) -> tuple[str, ...]:
        failures: list[str] = []
        if (
            self.tier is EvidenceSourceTier.SYSTEMATIC_SYNTHESIS
            and not self.primary_source_ids
        ):
            failures.append("PRIMARY_TRACE_MISSING")
        if not self.population_declared:
            failures.append("POPULATION_MISSING")
        if not self.matrix_declared:
            failures.append("MATRIX_MISSING")
        if not self.endpoint_declared:
            failures.append("ENDPOINT_MISSING")
        return tuple(failures)

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "source_id": self.source_id,
                "source_record_sha256": self.source_record_sha256,
                "tier": self.tier.value,
                "primary_source_ids": list(self.primary_source_ids),
                "population_declared": self.population_declared,
                "matrix_declared": self.matrix_declared,
                "endpoint_declared": self.endpoint_declared,
                "order_control_reported": self.order_control_reported,
                "assessor_dependence_reported": self.assessor_dependence_reported,
                "limitations": list(self.limitations),
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> SourceQualityAssessmentV1:
        fields = frozenset(
            {
                "source_id",
                "source_record_sha256",
                "tier",
                "primary_source_ids",
                "population_declared",
                "matrix_declared",
                "endpoint_declared",
                "order_control_reported",
                "assessor_dependence_reported",
                "limitations",
            }
        )
        values = _closed_payload(
            payload, schema_version=cls.SCHEMA_VERSION, fields=fields
        )
        values["primary_source_ids"] = tuple(values["primary_source_ids"])
        values["limitations"] = tuple(values["limitations"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class OperativeEvidenceBindingV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "operative_evidence_binding_v1"
    requirement_id: str
    source_record_sha256: str
    source_tier: EvidenceSourceTier
    requested_claim: str
    demonstrated_scope: str
    transfer_disposition: TransferDisposition
    limitations: tuple[str, ...]
    population_match: bool
    matrix_match: bool
    endpoint_match: bool
    time_match: bool

    def __post_init__(self) -> None:
        for field_name in ("requirement_id", "requested_claim", "demonstrated_scope"):
            object.__setattr__(
                self, field_name, _text(getattr(self, field_name), field_name)
            )
        object.__setattr__(
            self,
            "source_record_sha256",
            _sha(self.source_record_sha256, "source_record_sha256"),
        )
        object.__setattr__(
            self, "source_tier", EvidenceSourceTier(self.source_tier)
        )
        object.__setattr__(
            self,
            "transfer_disposition",
            TransferDisposition(self.transfer_disposition),
        )
        object.__setattr__(
            self, "limitations", _texts(self.limitations, "limitations")
        )
        for field_name in (
            "population_match",
            "matrix_match",
            "endpoint_match",
            "time_match",
        ):
            object.__setattr__(
                self, field_name, _boolean(getattr(self, field_name), field_name)
            )
        if self.transfer_disposition is TransferDisposition.DIRECT:
            direct_tiers = {
                EvidenceSourceTier.DIRECT_FINE_FRAGRANCE,
                EvidenceSourceTier.DIRECT_HUMAN_OLFACTION,
            }
            scope = (
                self.population_match,
                self.matrix_match,
                self.endpoint_match,
                self.time_match,
            )
            if self.source_tier not in direct_tiers or not all(scope):
                raise ValueError("DIRECT transfer requires exact scope and a direct tier")

    @property
    def failures(self) -> tuple[str, ...]:
        if self.transfer_disposition is TransferDisposition.HOLD:
            return ("TRANSFER_HOLD",)
        return ()

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "requirement_id": self.requirement_id,
                "source_record_sha256": self.source_record_sha256,
                "source_tier": self.source_tier.value,
                "requested_claim": self.requested_claim,
                "demonstrated_scope": self.demonstrated_scope,
                "transfer_disposition": self.transfer_disposition.value,
                "limitations": list(self.limitations),
                "population_match": self.population_match,
                "matrix_match": self.matrix_match,
                "endpoint_match": self.endpoint_match,
                "time_match": self.time_match,
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> OperativeEvidenceBindingV1:
        fields = frozenset(
            {
                "requirement_id",
                "source_record_sha256",
                "source_tier",
                "requested_claim",
                "demonstrated_scope",
                "transfer_disposition",
                "limitations",
                "population_match",
                "matrix_match",
                "endpoint_match",
                "time_match",
            }
        )
        values = _closed_payload(
            payload, schema_version=cls.SCHEMA_VERSION, fields=fields
        )
        values["limitations"] = tuple(values["limitations"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class EvidenceReviewLedgerV1(_Record):
    SCHEMA_VERSION: ClassVar[str] = "evidence_review_ledger_v1"
    source_seed_manifest_sha256: str
    construct_registry_sha256: str
    assessments: tuple[SourceQualityAssessmentV1, ...]
    operative_bindings: tuple[OperativeEvidenceBindingV1, ...]
    unresolved_questions: tuple[str, ...]
    source_records: tuple[EvidenceSourceRecordV2, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_seed_manifest_sha256",
            _sha(self.source_seed_manifest_sha256, "source_seed_manifest_sha256"),
        )
        object.__setattr__(
            self,
            "construct_registry_sha256",
            _sha(self.construct_registry_sha256, "construct_registry_sha256"),
        )
        assessments = tuple(self.assessments)
        bindings = tuple(self.operative_bindings)
        records = tuple(self.source_records)
        if not assessments or any(
            not isinstance(item, SourceQualityAssessmentV1) for item in assessments
        ):
            raise TypeError("assessments must contain SourceQualityAssessmentV1 values")
        if not bindings or any(
            not isinstance(item, OperativeEvidenceBindingV1) for item in bindings
        ):
            raise TypeError("operative_bindings must contain OperativeEvidenceBindingV1 values")
        if any(not isinstance(item, EvidenceSourceRecordV2) for item in records):
            raise TypeError("source_records must contain EvidenceSourceRecordV2 values")
        object.__setattr__(self, "assessments", assessments)
        object.__setattr__(self, "operative_bindings", bindings)
        object.__setattr__(self, "source_records", records)
        object.__setattr__(
            self,
            "unresolved_questions",
            _texts(self.unresolved_questions, "unresolved_questions"),
        )

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "source_seed_manifest_sha256": self.source_seed_manifest_sha256,
                "construct_registry_sha256": self.construct_registry_sha256,
                "assessments": [item.as_dict() for item in self.assessments],
                "operative_bindings": [
                    item.as_dict() for item in self.operative_bindings
                ],
                "unresolved_questions": list(self.unresolved_questions),
                "source_records": [item.as_dict() for item in self.source_records],
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> EvidenceReviewLedgerV1:
        fields = frozenset(
            {
                "source_seed_manifest_sha256",
                "construct_registry_sha256",
                "assessments",
                "operative_bindings",
                "unresolved_questions",
                "source_records",
            }
        )
        values = _closed_payload(
            payload, schema_version=cls.SCHEMA_VERSION, fields=fields
        )
        values["assessments"] = tuple(
            SourceQualityAssessmentV1.from_dict(item)
            for item in values["assessments"]
        )
        values["operative_bindings"] = tuple(
            OperativeEvidenceBindingV1.from_dict(item)
            for item in values["operative_bindings"]
        )
        values["unresolved_questions"] = tuple(values["unresolved_questions"])
        values["source_records"] = tuple(
            EvidenceSourceRecordV2.from_dict(item) for item in values["source_records"]
        )
        return cls(**values)


@dataclass(frozen=True, slots=True)
class EvidenceReviewLedgerV2(_Record):
    """Hash-bound additive overlay; predecessor V2 evidence remains immutable."""

    SCHEMA_VERSION: ClassVar[str] = "evidence_review_ledger_v2"
    predecessor_ledger_sha256: str
    source_seed_manifest_sha256: str
    construct_registry_sha256: str
    oav_temporal_policy_sha256: str
    hedonic_protocol_policy_sha256: str
    added_assessments: tuple[SourceQualityAssessmentV1, ...]
    added_operative_bindings: tuple[OperativeEvidenceBindingV1, ...]
    unresolved_questions: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "predecessor_ledger_sha256",
            "source_seed_manifest_sha256",
            "construct_registry_sha256",
            "oav_temporal_policy_sha256",
            "hedonic_protocol_policy_sha256",
        ):
            object.__setattr__(
                self, field_name, _sha(getattr(self, field_name), field_name)
            )
        assessments = tuple(self.added_assessments)
        bindings = tuple(self.added_operative_bindings)
        if not assessments or any(
            not isinstance(item, SourceQualityAssessmentV1) for item in assessments
        ):
            raise TypeError(
                "added_assessments must contain SourceQualityAssessmentV1 values"
            )
        if not bindings or any(
            not isinstance(item, OperativeEvidenceBindingV1) for item in bindings
        ):
            raise TypeError(
                "added_operative_bindings must contain OperativeEvidenceBindingV1 values"
            )
        object.__setattr__(self, "added_assessments", assessments)
        object.__setattr__(self, "added_operative_bindings", bindings)
        object.__setattr__(
            self,
            "unresolved_questions",
            _texts(self.unresolved_questions, "unresolved_questions"),
        )

    def as_dict(self) -> dict[str, object]:
        return self._envelope(
            {
                "predecessor_ledger_sha256": self.predecessor_ledger_sha256,
                "source_seed_manifest_sha256": self.source_seed_manifest_sha256,
                "construct_registry_sha256": self.construct_registry_sha256,
                "oav_temporal_policy_sha256": self.oav_temporal_policy_sha256,
                "hedonic_protocol_policy_sha256": self.hedonic_protocol_policy_sha256,
                "added_assessments": [
                    item.as_dict() for item in self.added_assessments
                ],
                "added_operative_bindings": [
                    item.as_dict() for item in self.added_operative_bindings
                ],
                "unresolved_questions": list(self.unresolved_questions),
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> EvidenceReviewLedgerV2:
        fields = frozenset(
            {
                "predecessor_ledger_sha256",
                "source_seed_manifest_sha256",
                "construct_registry_sha256",
                "oav_temporal_policy_sha256",
                "hedonic_protocol_policy_sha256",
                "added_assessments",
                "added_operative_bindings",
                "unresolved_questions",
            }
        )
        values = _closed_payload(
            payload, schema_version=cls.SCHEMA_VERSION, fields=fields
        )
        values["added_assessments"] = tuple(
            SourceQualityAssessmentV1.from_dict(item)
            for item in values["added_assessments"]
        )
        values["added_operative_bindings"] = tuple(
            OperativeEvidenceBindingV1.from_dict(item)
            for item in values["added_operative_bindings"]
        )
        values["unresolved_questions"] = tuple(values["unresolved_questions"])
        return cls(**values)


def validate_evidence_review(ledger: EvidenceReviewLedgerV1) -> tuple[str, ...]:
    """Return all cross-record failures without promoting any scientific claim."""

    if not isinstance(ledger, EvidenceReviewLedgerV1):
        raise TypeError("ledger must be an EvidenceReviewLedgerV1")
    issues: list[str] = []
    source_ids = [item.source_id for item in ledger.assessments]
    if len(source_ids) != len(set(source_ids)):
        issues.append("duplicate source_id")
    hashes = [item.source_record_sha256 for item in ledger.assessments]
    if len(hashes) != len(set(hashes)):
        issues.append("duplicate source_record_sha256")
    requirement_ids = [item.requirement_id for item in ledger.operative_bindings]
    if len(requirement_ids) != len(set(requirement_ids)):
        issues.append("duplicate requirement_id")
    known_hashes = set(hashes)
    for binding in ledger.operative_bindings:
        if binding.source_record_sha256 not in known_hashes:
            issues.append(
                f"binding {binding.requirement_id} references an unknown source record"
            )
    if ledger.source_records:
        record_hashes = {item.record_sha256: item for item in ledger.source_records}
        stable_ids = [item.stable_identifier.casefold() for item in ledger.source_records]
        if len(stable_ids) != len(set(stable_ids)):
            issues.append("duplicate stable_identifier")
        for assessment in ledger.assessments:
            source = record_hashes.get(assessment.source_record_sha256)
            if source is None:
                issues.append(
                    f"assessment {assessment.source_id} references an unknown source record"
                )
            elif source.source_id != assessment.source_id:
                issues.append(
                    f"assessment {assessment.source_id} source identity mismatch"
                )
            elif source.source_tier is not assessment.tier:
                issues.append(
                    f"assessment {assessment.source_id} source tier mismatch"
                )
        for binding in ledger.operative_bindings:
            source = record_hashes.get(binding.source_record_sha256)
            if source is not None and source.source_tier is not binding.source_tier:
                issues.append(
                    f"binding {binding.requirement_id} source tier mismatch"
                )
    return tuple(issues)


def validate_evidence_review_v3(
    ledger: EvidenceReviewLedgerV2,
    predecessor: EvidenceReviewLedgerV1,
    merged_source_records: tuple[EvidenceSourceRecordV2, ...],
) -> tuple[str, ...]:
    """Validate an additive V3 overlay without granting scientific authority."""

    if not isinstance(ledger, EvidenceReviewLedgerV2):
        raise TypeError("ledger must be an EvidenceReviewLedgerV2")
    if not isinstance(predecessor, EvidenceReviewLedgerV1):
        raise TypeError("predecessor must be an EvidenceReviewLedgerV1")
    issues: list[str] = []
    predecessor_ids = {item.source_id for item in predecessor.source_records}
    predecessor_stable = {
        item.stable_identifier.casefold() for item in predecessor.source_records
    }
    added_source_records = tuple(
        item for item in merged_source_records if item.source_id not in predecessor_ids
    )
    added_ids = [item.source_id for item in added_source_records]
    added_stable = [
        item.stable_identifier.casefold() for item in added_source_records
    ]
    if len(added_ids) != len(set(added_ids)):
        issues.append("duplicate added source_id")
    if len(added_stable) != len(set(added_stable)):
        issues.append("duplicate added stable_identifier")
    if predecessor_ids.intersection(added_ids):
        issues.append("added source_id overlaps predecessor")
    if predecessor_stable.intersection(added_stable):
        issues.append("added stable_identifier overlaps predecessor")

    assessment_ids = [item.source_id for item in ledger.added_assessments]
    if len(assessment_ids) != len(set(assessment_ids)):
        issues.append("duplicate added assessment source_id")
    if set(assessment_ids) != set(added_ids):
        issues.append("added assessments must exactly cover added source records")
    by_hash = {item.record_sha256: item for item in added_source_records}
    for assessment in ledger.added_assessments:
        source = by_hash.get(assessment.source_record_sha256)
        if source is None:
            issues.append(
                f"added assessment {assessment.source_id} references an unknown source"
            )
        elif source.source_id != assessment.source_id:
            issues.append(
                f"added assessment {assessment.source_id} source identity mismatch"
            )

    predecessor_requirements = {
        item.requirement_id for item in predecessor.operative_bindings
    }
    added_requirements = [
        item.requirement_id for item in ledger.added_operative_bindings
    ]
    if len(added_requirements) != len(set(added_requirements)):
        issues.append("duplicate added requirement_id")
    if predecessor_requirements.intersection(added_requirements):
        issues.append("added requirement_id overlaps predecessor")

    merged_ids = [item.source_id for item in merged_source_records]
    expected_ids = sorted((*predecessor_ids, *added_ids))
    if merged_ids != expected_ids:
        issues.append("merged source registry does not match predecessor plus overlay")
    combined = EvidenceReviewLedgerV1(
        source_seed_manifest_sha256=ledger.source_seed_manifest_sha256,
        construct_registry_sha256=ledger.construct_registry_sha256,
        assessments=tuple(
            sorted(
                (*predecessor.assessments, *ledger.added_assessments),
                key=lambda item: item.source_id,
            )
        ),
        operative_bindings=tuple(
            sorted(
                (*predecessor.operative_bindings, *ledger.added_operative_bindings),
                key=lambda item: item.requirement_id,
            )
        ),
        unresolved_questions=ledger.unresolved_questions,
        source_records=merged_source_records,
    )
    issues.extend(validate_evidence_review(combined))
    if not set(predecessor.unresolved_questions).issubset(ledger.unresolved_questions):
        issues.append("predecessor unresolved questions must remain explicit")
    return tuple(dict.fromkeys(issues))


def _expected_oav_temporal_policy() -> dict[str, object]:
    return {
        "schema_version": "oav_temporal_policy_v1",
        "canonical_time": {
            "unit": "SECOND",
            "minimum": 0,
            "integer_required": True,
            "display_aliases_only": True,
            "timepoints_declared_by": "PROTOCOL",
            "universal_timepoints": [],
        },
        "canonical_cell_key": list(_OAV_CELL_KEY_FIELDS),
        "interval_quantiles": ["P05", "P50", "P95"],
        "interval_requirements": {
            "order": "P05 <= P50 <= P95",
            "values": "POSITIVE_FINITE",
            "units": "EXACT_COMPATIBLE_CONCENTRATION_OR_THRESHOLD_UNITS",
        },
        "oav_interval_calculation": {
            "p05": "headspace_p05 / threshold_p95",
            "p50": "headspace_p50 / threshold_p50",
            "p95": "headspace_p95 / threshold_p05",
        },
        "threshold_cancellation": {
            "required_exact_matches": list(_OAV_COMPATIBILITY_FIELDS),
            "incompatible_state": "THRESHOLD_CANCELLATION_INCOMPATIBLE",
        },
        "model_tiers": list(_OAV_MODEL_TIERS),
        "missing_data": {
            "missing_stays_missing": True,
            "interpolation_allowed": False,
            "predicted_volatility_is_observation": False,
        },
        "natural_preblend": {
            "whole_material_screening_allowed": True,
            "constituent_specific_evidence_required": True,
            "silent_constituent_sum_allowed": False,
        },
        "forbidden_inferences": list(_OAV_FORBIDDEN_INFERENCES),
        "authority_flags": dict(EVIDENCE_REVIEW_AUTHORITY_FLAGS),
    }


def _expected_hedonic_protocol_policy() -> dict[str, object]:
    return {
        "schema_version": "hedonic_protocol_policy_v1",
        "criteria": list(_HEDONIC_CRITERIA),
        "protocol_scopes": list(_HEDONIC_SCOPES),
        "outcomes": ["LEFT", "RIGHT", "TIE"],
        "required_preobservation_fields": list(_HEDONIC_PREOBSERVATION_FIELDS),
        "criterion_policy": {
            "fit_separately": True,
            "cross_criterion_substitution": False,
            "synthetic_beauty_score": False,
        },
        "scope_policy": {
            "exact_scope_only": True,
            "owner_implies_panel": False,
            "panel_implies_consumer": False,
        },
        "tie_policy": {
            "directional_fit": "EXCLUDE",
            "indifference_evidence": "RETAIN",
        },
        "validation_policy": {
            "heldout_required": True,
            "declared_baseline_required": True,
            "baseline_gain_required": True,
            "assessor_cluster_bootstrap_when_identified": True,
            "deterministic_seed_required": True,
        },
        "forbidden_directional_features": list(_HEDONIC_FORBIDDEN_FEATURES),
        "authority_flags": dict(EVIDENCE_REVIEW_AUTHORITY_FLAGS),
    }


def _load_exact_policy(path: Path, expected: dict[str, object], label: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload != expected:
        raise ValueError(f"{label} does not match frozen decisions")
    return payload


def load_oav_temporal_policy(path: Path) -> dict[str, object]:
    """Load the exact temporal OAV policy; no policy relaxation is accepted."""

    return _load_exact_policy(
        path, _expected_oav_temporal_policy(), "OAV temporal policy"
    )


def load_hedonic_protocol_policy(path: Path) -> dict[str, object]:
    """Load the exact scoped hedonic policy; criteria remain separate."""

    return _load_exact_policy(
        path, _expected_hedonic_protocol_policy(), "hedonic protocol policy"
    )


def load_construct_registry(path: Path) -> dict[str, object]:
    """Load and validate the closed complexity-construct registry."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "constructs",
        "authority_flags",
    }:
        raise ValueError("construct registry does not match the closed schema")
    if payload["schema_version"] != "complexity_construct_registry_v1":
        raise ValueError("construct registry schema_version is invalid")
    if payload["authority_flags"] != EVIDENCE_REVIEW_AUTHORITY_FLAGS:
        raise ValueError("construct registry authority_flags are invalid")
    constructs = payload["constructs"]
    if not isinstance(constructs, list):
        raise TypeError("constructs must be a list")
    fields = {
        "construct_id",
        "definition",
        "anchors",
        "outcome_vocabulary",
        "required_scope_fields",
        "forbidden_inferences",
    }
    for construct in constructs:
        if not isinstance(construct, dict) or set(construct) != fields:
            raise ValueError("construct entry does not match the closed schema")
        _text(construct["definition"], "definition")
        for field_name in fields - {"construct_id", "definition"}:
            _texts(construct[field_name], field_name)
    observed = tuple(construct["construct_id"] for construct in constructs)
    if observed != _CONSTRUCT_IDS:
        raise ValueError("construct identifiers or order are invalid")
    return payload


def load_evidence_source_registry(path: Path) -> tuple[EvidenceSourceRecordV2, ...]:
    """Load the closed, source-sorted V2 literature and standards registry."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "sources",
        "authority_flags",
    }:
        raise ValueError("evidence source registry does not match the closed schema")
    if payload["schema_version"] != "complexity_evidence_sources_v2":
        raise ValueError("evidence source registry schema_version is invalid")
    if payload["authority_flags"] != EVIDENCE_REVIEW_AUTHORITY_FLAGS:
        raise ValueError("evidence source registry authority_flags are invalid")
    if not isinstance(payload["sources"], list) or not payload["sources"]:
        raise ValueError("evidence source registry requires sources")
    records = tuple(EvidenceSourceRecordV2.from_dict(item) for item in payload["sources"])
    source_ids = tuple(item.source_id for item in records)
    if source_ids != tuple(sorted(source_ids)):
        raise ValueError("evidence sources must be sorted by source_id")
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("evidence sources contain duplicate source_id")
    stable_ids = tuple(item.stable_identifier.casefold() for item in records)
    if len(stable_ids) != len(set(stable_ids)):
        raise ValueError("evidence sources contain duplicate stable_identifier")
    return records


def load_evidence_source_registry_v3_additions(
    path: Path,
    predecessor_path: Path,
) -> tuple[EvidenceSourceRecordV2, ...]:
    """Load a closed additive V3 source overlay and verify predecessor bytes."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "predecessor_sha256",
        "added_sources",
        "authority_flags",
    }:
        raise ValueError("V3 evidence source overlay does not match the closed schema")
    if payload["schema_version"] != "complexity_evidence_sources_v3":
        raise ValueError("V3 evidence source overlay schema_version is invalid")
    if payload["authority_flags"] != EVIDENCE_REVIEW_AUTHORITY_FLAGS:
        raise ValueError("V3 evidence source overlay authority_flags are invalid")
    predecessor_sha256 = _sha(payload["predecessor_sha256"], "predecessor_sha256")
    observed_predecessor_sha256 = sha256_hex(Path(predecessor_path).read_bytes())
    if predecessor_sha256 != observed_predecessor_sha256:
        raise ValueError("predecessor source registry SHA-256 mismatch")
    predecessor = load_evidence_source_registry(predecessor_path)
    additions_payload = payload["added_sources"]
    if not isinstance(additions_payload, list) or not additions_payload:
        raise ValueError("V3 evidence source overlay requires added_sources")
    additions = tuple(
        EvidenceSourceRecordV2.from_dict(item) for item in additions_payload
    )
    added_ids = tuple(item.source_id for item in additions)
    if added_ids != tuple(sorted(added_ids)):
        raise ValueError("V3 added evidence sources must be sorted by source_id")
    if len(added_ids) != len(set(added_ids)):
        raise ValueError("V3 added evidence sources contain duplicate source_id")
    predecessor_ids = {item.source_id for item in predecessor}
    if predecessor_ids.intersection(added_ids):
        raise ValueError("V3 added evidence source_id overlaps predecessor")
    added_stable = tuple(item.stable_identifier.casefold() for item in additions)
    if len(added_stable) != len(set(added_stable)):
        raise ValueError("V3 added evidence sources contain duplicate stable_identifier")
    predecessor_stable = {
        item.stable_identifier.casefold() for item in predecessor
    }
    if predecessor_stable.intersection(added_stable):
        raise ValueError("V3 added stable_identifier overlaps predecessor")
    return additions


def load_evidence_source_registry_v3(
    path: Path,
    predecessor_path: Path,
) -> tuple[EvidenceSourceRecordV2, ...]:
    """Materialize V3 by exact additive overlay over immutable V2 records."""

    predecessor = load_evidence_source_registry(predecessor_path)
    additions = load_evidence_source_registry_v3_additions(path, predecessor_path)
    return tuple(sorted((*predecessor, *additions), key=lambda item: item.source_id))


__all__ = [
    "EVIDENCE_REVIEW_AUTHORITY_FLAGS",
    "EvidenceReviewLedgerV1",
    "EvidenceReviewLedgerV2",
    "EvidenceSourceRecordV2",
    "EvidenceSourceTier",
    "INTERFACE_FREEZE_POLICY_DECISIONS",
    "OAVIntervalEvidence",
    "OAVModelTier",
    "OAVTimepointEvidenceInput",
    "OAVTimepointKey",
    "OperativeEvidenceBindingV1",
    "SourceQualityAssessmentV1",
    "TEMPORAL_OAV_INTERFACE_FIELDS",
    "TemporalOAVEvidenceRequest",
    "TransferDisposition",
    "load_construct_registry",
    "load_evidence_source_registry",
    "load_evidence_source_registry_v3",
    "load_evidence_source_registry_v3_additions",
    "load_hedonic_protocol_policy",
    "load_oav_temporal_policy",
    "validate_evidence_review",
    "validate_evidence_review_v3",
]
