"""Versioned, JSON-safe contracts for perfume research and execution evidence."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any, Literal, Mapping

FALSE_ACTION_AUTHORITY: dict[str, bool] = {
    "release_authority": False,
    "safety_authority": False,
    "compounding_authority": False,
    "evidence_admission_authorized": False,
}

ValidationState = Literal[
    "INVALID_INPUT",
    "WITHHOLD_UNKNOWN",
    "ADVISORY_FINDINGS",
    "ADVISORY_COMPLETE",
]
ApplicabilityState = Literal[
    "APPLICABLE", "PARTIAL", "OUT_OF_DOMAIN", "UNAVAILABLE"
]


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def decimal_text(
    value: object,
    name: str,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> str:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a decimal, not a boolean")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite decimal") from exc
    if not parsed.is_finite():
        raise ValueError(f"{name} must be a finite decimal")
    if positive and parsed <= 0:
        raise ValueError(f"{name} must be greater than zero")
    if nonnegative and parsed < 0:
        raise ValueError(f"{name} must be non-negative")
    if parsed == 0:
        return "0"
    rendered = format(parsed, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _finite(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric, not boolean")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(parsed) or (positive and parsed <= 0):
        raise ValueError(f"{name} must be {'positive and ' if positive else ''}finite")
    return parsed


def stable_payload_hash(payload: Mapping[str, Any]) -> str:
    return sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class MaterialIdentityV1:
    material_id: str
    canonical_name: str
    identity_kind: Literal[
        "CHEMICAL", "COMMERCIAL_PRODUCT", "NATURAL_MIXTURE", "UNKNOWN"
    ]
    adjudication_state: Literal[
        "EXACT_IDENTITY_BOUND",
        "PRODUCT_OR_GRADE_AMBIGUOUS",
        "CAS_NAME_CONFLICT",
        "NO_LOCAL_IDENTITY",
        "WITHHELD_LICENSE_OR_SOURCE",
        "NOT_APPLICABLE",
    ]
    cas: str | None = None
    aliases: tuple[str, ...] = ()
    identity_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "material_id", _text(self.material_id, "material_id"))
        object.__setattr__(
            self, "canonical_name", _text(self.canonical_name, "canonical_name")
        )
        if self.cas is not None:
            object.__setattr__(self, "cas", _text(self.cas, "cas"))
        aliases = tuple(_text(value, "alias") for value in self.aliases)
        if len({value.casefold() for value in aliases}) != len(aliases):
            raise ValueError("aliases must be unique")
        object.__setattr__(self, "aliases", aliases)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProductIdentityV1:
    product_id: str
    material_id: str
    product_name: str
    supplier: str | None = None
    grade: str | None = None
    constituent_material_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("product_id", "material_id", "product_name"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        values = tuple(
            _text(value, "constituent_material_id")
            for value in self.constituent_material_ids
        )
        if len(values) != len(set(values)):
            raise ValueError("constituent material identities must be unique")
        object.__setattr__(self, "constituent_material_ids", values)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class StockLotV1:
    stock_id: str
    product_id: str
    fraction_decimal: str
    basis: Literal["W_W", "V_V", "W_V", "NEAT", "UNKNOWN"]
    carrier_product_id: str | None = None
    density_g_ml_decimal: str | None = None
    density_provenance: str | None = None
    lot_id: str | None = None
    bottle_id: str | None = None
    prepared_stock_receipt_id: str | None = None
    homogeneity_state: Literal["CONFIRMED", "UNCONFIRMED", "NOT_APPLICABLE"] = (
        "UNCONFIRMED"
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "stock_id", _text(self.stock_id, "stock_id"))
        object.__setattr__(self, "product_id", _text(self.product_id, "product_id"))
        fraction = decimal_text(
            self.fraction_decimal, "fraction_decimal", nonnegative=True
        )
        if Decimal(fraction) > 1:
            raise ValueError("fraction_decimal cannot exceed one")
        if self.basis == "NEAT" and Decimal(fraction) != 1:
            raise ValueError("NEAT stock must have fraction one")
        if self.basis == "UNKNOWN" and Decimal(fraction) != 0:
            raise ValueError("UNKNOWN basis cannot assert an active fraction")
        object.__setattr__(self, "fraction_decimal", fraction)
        if self.density_g_ml_decimal is not None:
            density = decimal_text(
                self.density_g_ml_decimal, "density_g_ml_decimal", positive=True
            )
            if not self.density_provenance:
                raise ValueError("density provenance is required with density")
            object.__setattr__(self, "density_g_ml_decimal", density)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FormulaComponentV1:
    row_id: str
    product_id: str
    stock_id: str | None
    amount_decimal: str
    amount_unit: Literal["uL", "mL", "mg", "g"]
    basket: str | None = None
    operation: Literal["PRECHARGE", "DIRECT_ADD", "POSTCHARGE", "MASS_ADD"] = (
        "DIRECT_ADD"
    )
    source_row: int | None = None
    source_material_label: str | None = None
    required_stock_description: str | None = None
    source_evidence_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "row_id", _text(self.row_id, "row_id"))
        object.__setattr__(self, "product_id", _text(self.product_id, "product_id"))
        object.__setattr__(
            self,
            "amount_decimal",
            decimal_text(self.amount_decimal, "amount_decimal", positive=True),
        )
        if self.source_row is not None and (
            isinstance(self.source_row, bool)
            or not isinstance(self.source_row, int)
            or self.source_row < 1
        ):
            raise ValueError("source_row must be a positive integer")
        for name in (
            "source_material_label",
            "required_stock_description",
            "source_evidence_id",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _text(value, name))

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FormulaSnapshotV1:
    formula_id: str
    formula_name: str
    components: tuple[FormulaComponentV1, ...]
    parent_formula_sha256: str | None = None
    design_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "formula_id", _text(self.formula_id, "formula_id"))
        object.__setattr__(
            self, "formula_name", _text(self.formula_name, "formula_name")
        )
        components = tuple(self.components)
        if not components:
            raise ValueError("formula requires at least one component")
        row_ids = [row.row_id for row in components]
        if len(row_ids) != len(set(row_ids)):
            raise ValueError("formula row identities must be unique")
        object.__setattr__(self, "components", components)
        if not isinstance(self.design_only, bool):
            raise TypeError("design_only must be boolean")
        if self.parent_formula_sha256 is not None and (
            len(self.parent_formula_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.parent_formula_sha256)
        ):
            raise ValueError("parent formula hash must be lowercase SHA-256")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "formula-snapshot-v1",
            "formula_id": self.formula_id,
            "formula_name": self.formula_name,
            "components": [row.as_dict() for row in self.components],
            "parent_formula_sha256": self.parent_formula_sha256,
            "design_only": self.design_only,
        }

    @property
    def sha256(self) -> str:
        return stable_payload_hash(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class ReleaseScenarioV1:
    scenario_id: str
    matrix_id: str
    substrate: Literal["GLASS", "BLOTTER", "SKIN_SURROGATE", "SKIN"]
    deposit_mass_g_decimal: str
    surface_area_m2_decimal: str
    temperature_k: float
    relative_humidity_decimal: str
    airflow_m_s_decimal: str
    delivery_volume_m3_decimal: str
    sampling_geometry: str
    timepoints_seconds: tuple[float, ...]

    def __post_init__(self) -> None:
        for name in ("scenario_id", "matrix_id", "sampling_geometry"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "deposit_mass_g_decimal",
            "surface_area_m2_decimal",
            "delivery_volume_m3_decimal",
        ):
            object.__setattr__(
                self, name, decimal_text(getattr(self, name), name, positive=True)
            )
        for name in ("relative_humidity_decimal", "airflow_m_s_decimal"):
            object.__setattr__(
                self, name, decimal_text(getattr(self, name), name, nonnegative=True)
            )
        humidity = Decimal(self.relative_humidity_decimal)
        if humidity > 1:
            raise ValueError("relative humidity must be a fraction from zero to one")
        object.__setattr__(
            self, "temperature_k", _finite(self.temperature_k, "temperature_k", positive=True)
        )
        points = tuple(_finite(value, "timepoint") for value in self.timepoints_seconds)
        if not points or points[0] != 0 or any(value < 0 for value in points):
            raise ValueError("timepoints must begin at zero and be non-negative")
        if tuple(sorted(set(points))) != points:
            raise ValueError("timepoints must be unique and increasing")
        object.__setattr__(self, "timepoints_seconds", points)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def sha256(self) -> str:
        return stable_payload_hash(self.as_dict())


@dataclass(frozen=True, slots=True)
class CapabilityManifestV1:
    capability_id: str
    endpoint: str
    source_sha256: str
    transcription_sha256: str
    implementation_sha256: str
    license_id: str
    permitted_use: str
    identity_scope: tuple[str, ...]
    input_quantity: str
    input_unit: str
    phase: str
    applicability: Mapping[str, Any]
    uncertainty_method: str
    admission_state: str
    action_authority: Mapping[str, bool] = field(
        default_factory=lambda: dict(FALSE_ACTION_AUTHORITY)
    )

    def __post_init__(self) -> None:
        for name in (
            "capability_id",
            "endpoint",
            "license_id",
            "permitted_use",
            "input_quantity",
            "input_unit",
            "phase",
            "uncertainty_method",
            "admission_state",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in ("source_sha256", "transcription_sha256", "implementation_sha256"):
            value = getattr(self, name)
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ValueError(f"{name} must be lowercase SHA-256")
        if any(bool(self.action_authority.get(key)) for key in FALSE_ACTION_AUTHORITY):
            raise ValueError("research capabilities cannot grant action authority")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EndpointEstimateV1:
    endpoint: str
    value: float | None
    unit: str | None
    coverage_decimal: str
    applicability_state: ApplicabilityState
    uncertainty_interval: tuple[float, float] | None
    provenance_ids: tuple[str, ...]
    reason_codes: tuple[str, ...] = ()
    authority: Mapping[str, bool] = field(
        default_factory=lambda: dict(FALSE_ACTION_AUTHORITY)
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "endpoint", _text(self.endpoint, "endpoint"))
        coverage = decimal_text(
            self.coverage_decimal, "coverage_decimal", nonnegative=True
        )
        if Decimal(coverage) > 1:
            raise ValueError("coverage must be a fraction from zero to one")
        object.__setattr__(self, "coverage_decimal", coverage)
        if self.value is not None:
            object.__setattr__(self, "value", _finite(self.value, "value"))
        if self.uncertainty_interval is not None:
            low, high = (
                _finite(self.uncertainty_interval[0], "uncertainty lower"),
                _finite(self.uncertainty_interval[1], "uncertainty upper"),
            )
            if low > high:
                raise ValueError("uncertainty interval is reversed")
            object.__setattr__(self, "uncertainty_interval", (low, high))
        if any(bool(self.authority.get(key)) for key in FALSE_ACTION_AUTHORITY):
            raise ValueError("endpoint estimates cannot grant action authority")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SensoryObservationV1:
    observation_id: str
    protocol_id: str
    session_id: str
    blinded_sample_code: str
    endpoint: Literal[
        "CHARACTER", "INTENSITY", "DISCRIMINATION", "THRESHOLD", "LIKING"
    ]
    value: float | str | None
    scale_id: str
    time_seconds: float
    assessor_scope: Literal["PERSONAL", "TRAINED_PANEL", "CONSUMER_PANEL"]
    tie: bool = False
    cannot_determine: bool = False

    def __post_init__(self) -> None:
        for name in (
            "observation_id",
            "protocol_id",
            "session_id",
            "blinded_sample_code",
            "scale_id",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(
            self, "time_seconds", _finite(self.time_seconds, "time_seconds")
        )
        if self.time_seconds < 0:
            raise ValueError("time_seconds must be non-negative")
        if self.tie and self.value is not None:
            raise ValueError("a tie cannot also assert a scalar preference value")
        if self.cannot_determine and self.value is not None:
            raise ValueError("cannot-determine cannot also assert a value")
        if self.tie and self.cannot_determine:
            raise ValueError("tie and cannot-determine are distinct outcomes")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CandidateEvaluationV1:
    candidate_id: str
    formula_sha256: str
    endpoint_estimates: tuple[EndpointEstimateV1, ...]
    selection_status: Literal[
        "RANKED",
        "UNORDERED_DIVERSE_SET",
        "WITHHELD_NONDISCRIMINATING_EVIDENCE",
        "NO_CHANGE",
    ]
    reason_codes: tuple[str, ...] = ()
    formula_action: Literal["NO_CHANGE", "PROPOSE_ONLY"] = "NO_CHANGE"

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _text(self.candidate_id, "candidate_id"))
        if len(self.formula_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.formula_sha256
        ):
            raise ValueError("formula_sha256 must be lowercase SHA-256")
        estimates = tuple(self.endpoint_estimates)
        endpoints = [estimate.endpoint for estimate in estimates]
        if len(endpoints) != len(set(endpoints)):
            raise ValueError("candidate endpoints must be unique")
        object.__setattr__(self, "endpoint_estimates", estimates)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ValidationEnvelopeV2:
    state: ValidationState
    applicability_state: ApplicabilityState
    findings: tuple[Mapping[str, Any], ...] = ()
    missing_requirements: tuple[str, ...] = ()
    processing_allowed: bool = False
    reference_hashes: tuple[str, ...] = ()
    positive_dose_coverage_decimal: str = "0"
    authority: Mapping[str, bool] = field(
        default_factory=lambda: dict(FALSE_ACTION_AUTHORITY)
    )

    def __post_init__(self) -> None:
        coverage = decimal_text(
            self.positive_dose_coverage_decimal,
            "positive_dose_coverage_decimal",
            nonnegative=True,
        )
        if Decimal(coverage) > 1:
            raise ValueError("positive-dose coverage cannot exceed one")
        object.__setattr__(self, "positive_dose_coverage_decimal", coverage)
        if self.state in {"INVALID_INPUT", "WITHHOLD_UNKNOWN"} and self.processing_allowed:
            raise ValueError("invalid or withheld input cannot be processing-allowed")
        if any(bool(self.authority.get(key)) for key in FALSE_ACTION_AUTHORITY):
            raise ValueError("validation envelopes cannot grant action authority")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


__all__ = [
    "FALSE_ACTION_AUTHORITY",
    "CandidateEvaluationV1",
    "CapabilityManifestV1",
    "EndpointEstimateV1",
    "FormulaComponentV1",
    "FormulaSnapshotV1",
    "MaterialIdentityV1",
    "ProductIdentityV1",
    "ReleaseScenarioV1",
    "SensoryObservationV1",
    "StockLotV1",
    "ValidationEnvelopeV2",
    "decimal_text",
    "stable_payload_hash",
]
