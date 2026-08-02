"""Fail-closed C8 headspace OAV and sensory-authority contracts.

This module compares an admissible gas-phase concentration with a compatible
detection threshold for screening only.  It records, but never applies,
context-calibrated interaction effects and keeps sensomics evidence separate
from unsupported sensory claims.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

from engine.calibration.hashing import stable_json_hash

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_EnumT = TypeVar("_EnumT", bound=Enum)


class HeadspaceOAVContractError(ValueError):
    """Malformed, ambiguous, or authority-ineligible C8 record."""


class GasConcentrationOrigin(str, Enum):
    MEASURED = "MEASURED"
    PREDICTED = "PREDICTED"


class ThresholdKind(str, Enum):
    DETECTION = "DETECTION"
    RECOGNITION = "RECOGNITION"


class ThresholdAuthority(str, Enum):
    DIRECT_CONTEXT_MEASUREMENT = "DIRECT_CONTEXT_MEASUREMENT"
    PEER_REVIEWED_CONTEXT_MATCHED = "PEER_REVIEWED_CONTEXT_MATCHED"
    CONTEXT_MISMATCHED = "CONTEXT_MISMATCHED"
    PROXY = "PROXY"
    UNKNOWN = "UNKNOWN"


class OAVAssessmentStatus(str, Enum):
    COMPUTED = "COMPUTED"
    ABSTAINED = "ABSTAINED"


class OAVScreeningClass(str, Enum):
    ABOVE_THRESHOLD = "ABOVE_THRESHOLD"
    BELOW_THRESHOLD = "BELOW_THRESHOLD"
    STRADDLES_THRESHOLD = "STRADDLES_THRESHOLD"
    UNKNOWN = "UNKNOWN"


class InteractionKind(str, Enum):
    ADDITIVE = "ADDITIVE"
    SYNERGISTIC = "SYNERGISTIC"
    MASKING = "MASKING"
    SUPPRESSIVE = "SUPPRESSIVE"
    QUALITATIVE_TRANSFORMATION = "QUALITATIVE_TRANSFORMATION"
    UNKNOWN = "UNKNOWN"


class InteractionEvidenceKind(str, Enum):
    OBSERVATION = "OBSERVATION"
    MODEL = "MODEL"


class InteractionCalibrationState(str, Enum):
    CONTEXT_CALIBRATED = "CONTEXT_CALIBRATED"
    OBSERVED_ONLY = "OBSERVED_ONLY"
    UNCALIBRATED_GENERIC = "UNCALIBRATED_GENERIC"


class InteractionAdjustmentTarget(str, Enum):
    HEADSPACE_CONCENTRATION = "HEADSPACE_CONCENTRATION"
    PERCEIVED_INTENSITY = "PERCEIVED_INTENSITY"


class InteractionAdjustmentStatus(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    WITHHELD = "WITHHELD"


class SensomicsStage(str, Enum):
    REPRESENTATIVE_SAMPLING_EXTRACTION = "REPRESENTATIVE_SAMPLING_EXTRACTION"
    ODOR_ACTIVE_SCREENING = "ODOR_ACTIVE_SCREENING"
    IDENTITY_CONFIRMATION = "IDENTITY_CONFIRMATION"
    QUANTITATIVE_MEASUREMENT = "QUANTITATIVE_MEASUREMENT"
    CONTEXT_MATCHED_OAV_PRIORITIZATION = "CONTEXT_MATCHED_OAV_PRIORITIZATION"
    FULL_RECOMBINATION = "FULL_RECOMBINATION"
    OMISSION_ADDITION_EXPERIMENTS = "OMISSION_ADDITION_EXPERIMENTS"
    SENSORY_COMPARISON = "SENSORY_COMPARISON"


class SensomicsStageStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NOT_PERFORMED = "NOT_PERFORMED"


class SensomicsClaim(str, Enum):
    CANDIDATE_ODORANT_PRIORITIZATION = "CANDIDATE_ODORANT_PRIORITIZATION"
    RECOMBINATION_MATCH_IN_TESTED_CONTEXT = "RECOMBINATION_MATCH_IN_TESTED_CONTEXT"
    MATERIAL_EFFECT_IN_TESTED_CONTEXT = "MATERIAL_EFFECT_IN_TESTED_CONTEXT"


class C8Claim(str, Enum):
    PREDICTED_EQUILIBRIUM_HEADSPACE = "PREDICTED_EQUILIBRIUM_HEADSPACE"
    PREDICTED_PHYSICAL_RELEASE = "PREDICTED_PHYSICAL_RELEASE"
    ABOVE_THRESHOLD_SCREENING = "ABOVE_THRESHOLD_SCREENING"
    CANDIDATE_ODORANT_PRIORITIZATION = "CANDIDATE_ODORANT_PRIORITIZATION"
    EXPERIMENT_SELECTION = "EXPERIMENT_SELECTION"
    EXACT_PERCEIVED_INTENSITY = "EXACT_PERCEIVED_INTENSITY"
    PERCENT_MIXTURE_CONTRIBUTION = "PERCENT_MIXTURE_CONTRIBUTION"
    PLEASANTNESS = "PLEASANTNESS"
    TARGET_SIMILARITY = "TARGET_SIMILARITY"
    FAMILY_IDENTITY = "FAMILY_IDENTITY"
    LONGEVITY = "LONGEVITY"
    SILLAGE = "SILLAGE"
    CONSUMER_PREFERENCE = "CONSUMER_PREFERENCE"


class C8ClaimStatus(str, Enum):
    PERMITTED_WITH_EVIDENCE = "PERMITTED_WITH_EVIDENCE"
    WITHHELD = "WITHHELD"


C8_SENSOMICS_SEQUENCE = (
    SensomicsStage.REPRESENTATIVE_SAMPLING_EXTRACTION,
    SensomicsStage.ODOR_ACTIVE_SCREENING,
    SensomicsStage.IDENTITY_CONFIRMATION,
    SensomicsStage.QUANTITATIVE_MEASUREMENT,
    SensomicsStage.CONTEXT_MATCHED_OAV_PRIORITIZATION,
    SensomicsStage.FULL_RECOMBINATION,
    SensomicsStage.OMISSION_ADDITION_EXPERIMENTS,
    SensomicsStage.SENSORY_COMPARISON,
)

PERMITTED_C8_CLAIMS = (
    C8Claim.PREDICTED_EQUILIBRIUM_HEADSPACE,
    C8Claim.PREDICTED_PHYSICAL_RELEASE,
    C8Claim.ABOVE_THRESHOLD_SCREENING,
    C8Claim.CANDIDATE_ODORANT_PRIORITIZATION,
    C8Claim.EXPERIMENT_SELECTION,
)

WITHHELD_C8_CLAIMS = (
    C8Claim.EXACT_PERCEIVED_INTENSITY,
    C8Claim.PERCENT_MIXTURE_CONTRIBUTION,
    C8Claim.PLEASANTNESS,
    C8Claim.TARGET_SIMILARITY,
    C8Claim.FAMILY_IDENTITY,
    C8Claim.LONGEVITY,
    C8Claim.SILLAGE,
    C8Claim.CONSUMER_PREFERENCE,
)

_ADMISSIBLE_THRESHOLD_AUTHORITIES = frozenset(
    {
        ThresholdAuthority.DIRECT_CONTEXT_MEASUREMENT,
        ThresholdAuthority.PEER_REVIEWED_CONTEXT_MATCHED,
    }
)

_OAV_LIMITATIONS = (
    "OAV is an above-threshold screening ratio only.",
    "It is not exact perceived intensity.",
    "It is not percent mixture contribution.",
    "It is not target similarity.",
    "It is not consumer preference.",
)


def _mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise HeadspaceOAVContractError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise HeadspaceOAVContractError(f"{field_name} keys must be strings")
    return dict(value)


def _sequence(value: object, field_name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise HeadspaceOAVContractError(f"{field_name} must be a sequence")
    return tuple(value)


def _exact_keys(
    payload: Mapping[str, Any],
    expected: set[str],
    field_name: str,
) -> None:
    missing = expected - set(payload)
    unknown = set(payload) - expected
    if missing:
        raise HeadspaceOAVContractError(
            f"{field_name} missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise HeadspaceOAVContractError(
            f"{field_name} contains unknown fields: {', '.join(sorted(unknown))}"
        )


def _exact_keys_with_optional_hash(
    payload: Mapping[str, Any],
    expected: set[str],
    field_name: str,
) -> None:
    required = expected - {"content_sha256"}
    missing = required - set(payload)
    unknown = set(payload) - expected
    if missing:
        raise HeadspaceOAVContractError(
            f"{field_name} missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise HeadspaceOAVContractError(
            f"{field_name} contains unknown fields: {', '.join(sorted(unknown))}"
        )


def _schema(payload: Mapping[str, Any], expected: str, field_name: str) -> None:
    if payload["schema"] != expected:
        raise HeadspaceOAVContractError(f"{field_name} schema must be {expected}")


def _nonblank(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HeadspaceOAVContractError(f"{field_name} must not be blank")
    return value.strip()


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _nonblank(value, field_name)


def _finite(value: object, field_name: str) -> float:
    if isinstance(value, bool):
        raise HeadspaceOAVContractError(f"{field_name} must be finite")
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise HeadspaceOAVContractError(f"{field_name} must be finite") from exc
    if not math.isfinite(result):
        raise HeadspaceOAVContractError(f"{field_name} must be finite")
    return result


def _positive(value: object, field_name: str) -> float:
    result = _finite(value, field_name)
    if result <= 0.0:
        raise HeadspaceOAVContractError(f"{field_name} must be positive")
    return result


def _optional_finite(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    return _finite(value, field_name)


def _optional_fraction(value: object, field_name: str) -> float | None:
    result = _optional_finite(value, field_name)
    if result is not None and not 0.0 <= result <= 1.0:
        raise HeadspaceOAVContractError(f"{field_name} humidity must be between 0 and 1")
    return result


def _positive_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise HeadspaceOAVContractError(f"{field_name} must be a positive integer")
    return value


def _sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise HeadspaceOAVContractError(f"{field_name} must be a lowercase 64-character SHA-256")
    return value


def _optional_sha256(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _sha256(value, field_name)


def _direct_enum(
    enum_type: type[_EnumT],
    value: object,
    field_name: str,
) -> _EnumT:
    if not isinstance(value, enum_type):
        raise HeadspaceOAVContractError(f"{field_name} must be a {enum_type.__name__}")
    return value


def _enum_value(
    enum_type: type[_EnumT],
    value: object,
    field_name: str,
) -> _EnumT:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise HeadspaceOAVContractError(
            f"{field_name} is not a supported {enum_type.__name__}"
        ) from exc


def _bool_or_none(value: object, field_name: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise HeadspaceOAVContractError(f"{field_name} must be a boolean or null")
    return value


def _strings(
    value: object,
    field_name: str,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    result = tuple(_nonblank(item, field_name) for item in _sequence(value, field_name))
    if not allow_empty and not result:
        raise HeadspaceOAVContractError(f"{field_name} must not be empty")
    if len(result) != len(set(result)):
        raise HeadspaceOAVContractError(f"{field_name} contains duplicate values")
    return result


def _canonical_strings(value: object, field_name: str) -> tuple[str, ...]:
    return tuple(sorted(_strings(value, field_name), key=lambda item: (item.casefold(), item)))


def _hash(payload: Mapping[str, object]) -> str:
    return stable_json_hash(dict(payload))


def _verify_content_hash(expected: object, actual: str) -> None:
    if _sha256(expected, "content_sha256") != actual:
        raise HeadspaceOAVContractError("content_sha256 does not match canonical content")


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    source_id: str
    source_kind: str
    citation: str
    version: str
    source_sha256: str
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-evidence-reference-v1"

    def __post_init__(self) -> None:
        for field_name in ("source_id", "source_kind", "citation", "version"):
            object.__setattr__(self, field_name, _nonblank(getattr(self, field_name), field_name))
        object.__setattr__(self, "source_sha256", _sha256(self.source_sha256, "source_sha256"))
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "source_id": self.source_id,
            "source_kind": self.source_kind,
            "citation": self.citation,
            "version": self.version,
            "source_sha256": self.source_sha256,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> EvidenceReference:
        payload = _mapping(value, "evidence reference")
        _exact_keys(
            payload,
            {
                "schema",
                "source_id",
                "source_kind",
                "citation",
                "version",
                "source_sha256",
                "content_sha256",
            },
            "evidence reference",
        )
        _schema(payload, cls._SCHEMA, "evidence reference")
        result = cls(
            source_id=payload["source_id"],
            source_kind=payload["source_kind"],
            citation=payload["citation"],
            version=payload["version"],
            source_sha256=payload["source_sha256"],
        )
        _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


@dataclass(frozen=True, slots=True)
class GasPhaseContext:
    context_id: str
    phase_or_sampling_regime: str
    matrix_id: str
    temperature_k: float
    pressure_pa: float
    relative_humidity_fraction: float | None
    exposure_route: str
    substrate_or_apparatus_id: str | None
    content_sha256: str = field(init=False)
    compatibility_sha256: str = field(init=False)

    _SCHEMA = "c8-gas-phase-context-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "context_id", _nonblank(self.context_id, "context_id"))
        object.__setattr__(
            self,
            "phase_or_sampling_regime",
            _nonblank(self.phase_or_sampling_regime, "phase_or_sampling_regime"),
        )
        object.__setattr__(self, "matrix_id", _nonblank(self.matrix_id, "matrix_id"))
        object.__setattr__(self, "temperature_k", _positive(self.temperature_k, "temperature_k"))
        object.__setattr__(self, "pressure_pa", _positive(self.pressure_pa, "pressure_pa"))
        object.__setattr__(
            self,
            "relative_humidity_fraction",
            _optional_fraction(self.relative_humidity_fraction, "relative_humidity_fraction"),
        )
        object.__setattr__(
            self,
            "exposure_route",
            _nonblank(self.exposure_route, "exposure_route"),
        )
        object.__setattr__(
            self,
            "substrate_or_apparatus_id",
            _optional_text(self.substrate_or_apparatus_id, "substrate_or_apparatus_id"),
        )
        object.__setattr__(self, "compatibility_sha256", _hash(self._conditions()))
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _conditions(self) -> dict[str, object]:
        return {
            "phase_or_sampling_regime": self.phase_or_sampling_regime,
            "matrix_id": self.matrix_id,
            "temperature_k": self.temperature_k,
            "pressure_pa": self.pressure_pa,
            "relative_humidity_fraction": self.relative_humidity_fraction,
            "exposure_route": self.exposure_route,
            "substrate_or_apparatus_id": self.substrate_or_apparatus_id,
        }

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "context_id": self.context_id,
            **self._conditions(),
            "compatibility_sha256": self.compatibility_sha256,
        }

    def is_compatible_with(self, other: GasPhaseContext) -> bool:
        return self.compatibility_sha256 == other.compatibility_sha256

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> GasPhaseContext:
        payload = _mapping(value, "gas phase context")
        _exact_keys(
            payload,
            {
                "schema",
                "context_id",
                "phase_or_sampling_regime",
                "matrix_id",
                "temperature_k",
                "pressure_pa",
                "relative_humidity_fraction",
                "exposure_route",
                "substrate_or_apparatus_id",
                "compatibility_sha256",
                "content_sha256",
            },
            "gas phase context",
        )
        _schema(payload, cls._SCHEMA, "gas phase context")
        result = cls(
            context_id=payload["context_id"],
            phase_or_sampling_regime=payload["phase_or_sampling_regime"],
            matrix_id=payload["matrix_id"],
            temperature_k=payload["temperature_k"],
            pressure_pa=payload["pressure_pa"],
            relative_humidity_fraction=payload["relative_humidity_fraction"],
            exposure_route=payload["exposure_route"],
            substrate_or_apparatus_id=payload["substrate_or_apparatus_id"],
        )
        if _sha256(payload["compatibility_sha256"], "compatibility_sha256") != (
            result.compatibility_sha256
        ):
            raise HeadspaceOAVContractError(
                "compatibility_sha256 does not match canonical conditions"
            )
        _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


@dataclass(frozen=True, slots=True)
class BoundedQuantity:
    value: float
    unit: str
    lower_bound: float | None
    upper_bound: float | None
    uncertainty_basis: str
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-bounded-quantity-v1"

    def __post_init__(self) -> None:
        point = _positive(self.value, "value")
        lower = None if self.lower_bound is None else _positive(self.lower_bound, "lower_bound")
        upper = None if self.upper_bound is None else _positive(self.upper_bound, "upper_bound")
        if (lower is None) != (upper is None):
            raise HeadspaceOAVContractError(
                "lower_bound and upper_bound must both be present or absent"
            )
        if lower is not None and upper is not None:
            if lower > upper:
                raise HeadspaceOAVContractError("lower_bound must not exceed upper_bound")
            if not lower <= point <= upper:
                raise HeadspaceOAVContractError("value must lie within its uncertainty bounds")
        object.__setattr__(self, "value", point)
        object.__setattr__(self, "unit", _nonblank(self.unit, "unit"))
        object.__setattr__(self, "lower_bound", lower)
        object.__setattr__(self, "upper_bound", upper)
        object.__setattr__(
            self,
            "uncertainty_basis",
            _nonblank(self.uncertainty_basis, "uncertainty_basis"),
        )
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    @property
    def has_numeric_bounds(self) -> bool:
        return self.lower_bound is not None and self.upper_bound is not None

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "value": self.value,
            "unit": self.unit,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "uncertainty_basis": self.uncertainty_basis,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> BoundedQuantity:
        payload = _mapping(value, "bounded quantity")
        _exact_keys(
            payload,
            {
                "schema",
                "value",
                "unit",
                "lower_bound",
                "upper_bound",
                "uncertainty_basis",
                "content_sha256",
            },
            "bounded quantity",
        )
        _schema(payload, cls._SCHEMA, "bounded quantity")
        result = cls(
            value=payload["value"],
            unit=payload["unit"],
            lower_bound=payload["lower_bound"],
            upper_bound=payload["upper_bound"],
            uncertainty_basis=payload["uncertainty_basis"],
        )
        _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


@dataclass(frozen=True, slots=True)
class GasConcentrationEvidence:
    evidence_id: str
    analyte_id: str
    quantity: BoundedQuantity
    origin: GasConcentrationOrigin
    context: GasPhaseContext
    source: EvidenceReference
    model_id: str | None
    model_version: str | None
    model_release_sha256: str | None
    within_model_domain: bool | None
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-gas-concentration-evidence-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", _nonblank(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "analyte_id", _nonblank(self.analyte_id, "analyte_id"))
        if not isinstance(self.quantity, BoundedQuantity):
            raise HeadspaceOAVContractError("quantity must be a BoundedQuantity")
        object.__setattr__(
            self,
            "origin",
            _direct_enum(GasConcentrationOrigin, self.origin, "origin"),
        )
        if not isinstance(self.context, GasPhaseContext):
            raise HeadspaceOAVContractError("context must be a GasPhaseContext")
        if not isinstance(self.source, EvidenceReference):
            raise HeadspaceOAVContractError("source must be an EvidenceReference")

        model_id = _optional_text(self.model_id, "model_id")
        model_version = _optional_text(self.model_version, "model_version")
        model_release_sha256 = _optional_sha256(
            self.model_release_sha256,
            "model_release_sha256",
        )
        within_model_domain = _bool_or_none(
            self.within_model_domain,
            "within_model_domain",
        )
        model_fields = (
            model_id,
            model_version,
            model_release_sha256,
            within_model_domain,
        )
        if self.origin is GasConcentrationOrigin.MEASURED and any(
            item is not None for item in model_fields
        ):
            raise HeadspaceOAVContractError("measured gas evidence must not contain model metadata")
        if self.origin is GasConcentrationOrigin.PREDICTED and any(
            item is None for item in model_fields
        ):
            raise HeadspaceOAVContractError(
                "predicted gas evidence requires complete model and domain metadata"
            )
        object.__setattr__(self, "model_id", model_id)
        object.__setattr__(self, "model_version", model_version)
        object.__setattr__(self, "model_release_sha256", model_release_sha256)
        object.__setattr__(self, "within_model_domain", within_model_domain)
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "evidence_id": self.evidence_id,
            "analyte_id": self.analyte_id,
            "quantity": self.quantity.to_mapping(),
            "origin": self.origin.value,
            "context": self.context.to_mapping(),
            "source": self.source.to_mapping(),
            "model_id": self.model_id,
            "model_version": self.model_version,
            "model_release_sha256": self.model_release_sha256,
            "within_model_domain": self.within_model_domain,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> GasConcentrationEvidence:
        payload = _mapping(value, "gas concentration evidence")
        _exact_keys(
            payload,
            {
                "schema",
                "evidence_id",
                "analyte_id",
                "quantity",
                "origin",
                "context",
                "source",
                "model_id",
                "model_version",
                "model_release_sha256",
                "within_model_domain",
                "content_sha256",
            },
            "gas concentration evidence",
        )
        _schema(payload, cls._SCHEMA, "gas concentration evidence")
        result = cls(
            evidence_id=payload["evidence_id"],
            analyte_id=payload["analyte_id"],
            quantity=BoundedQuantity.from_mapping(payload["quantity"]),
            origin=_enum_value(GasConcentrationOrigin, payload["origin"], "origin"),
            context=GasPhaseContext.from_mapping(payload["context"]),
            source=EvidenceReference.from_mapping(payload["source"]),
            model_id=payload["model_id"],
            model_version=payload["model_version"],
            model_release_sha256=payload["model_release_sha256"],
            within_model_domain=payload["within_model_domain"],
        )
        _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


@dataclass(frozen=True, slots=True)
class OdorThresholdEvidence:
    threshold_id: str
    analyte_id: str
    quantity: BoundedQuantity
    kind: ThresholdKind
    authority: ThresholdAuthority
    context: GasPhaseContext
    method: str
    assessor_population: str
    assessor_count: int
    source: EvidenceReference
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-odor-threshold-evidence-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "threshold_id", _nonblank(self.threshold_id, "threshold_id"))
        object.__setattr__(self, "analyte_id", _nonblank(self.analyte_id, "analyte_id"))
        if not isinstance(self.quantity, BoundedQuantity):
            raise HeadspaceOAVContractError("quantity must be a BoundedQuantity")
        object.__setattr__(self, "kind", _direct_enum(ThresholdKind, self.kind, "kind"))
        object.__setattr__(
            self,
            "authority",
            _direct_enum(ThresholdAuthority, self.authority, "authority"),
        )
        if not isinstance(self.context, GasPhaseContext):
            raise HeadspaceOAVContractError("context must be a GasPhaseContext")
        object.__setattr__(self, "method", _nonblank(self.method, "method"))
        object.__setattr__(
            self,
            "assessor_population",
            _nonblank(self.assessor_population, "assessor_population"),
        )
        object.__setattr__(
            self,
            "assessor_count",
            _positive_integer(self.assessor_count, "assessor_count"),
        )
        if not isinstance(self.source, EvidenceReference):
            raise HeadspaceOAVContractError("source must be an EvidenceReference")
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "threshold_id": self.threshold_id,
            "analyte_id": self.analyte_id,
            "quantity": self.quantity.to_mapping(),
            "kind": self.kind.value,
            "authority": self.authority.value,
            "context": self.context.to_mapping(),
            "method": self.method,
            "assessor_population": self.assessor_population,
            "assessor_count": self.assessor_count,
            "source": self.source.to_mapping(),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> OdorThresholdEvidence:
        payload = _mapping(value, "odor threshold evidence")
        _exact_keys(
            payload,
            {
                "schema",
                "threshold_id",
                "analyte_id",
                "quantity",
                "kind",
                "authority",
                "context",
                "method",
                "assessor_population",
                "assessor_count",
                "source",
                "content_sha256",
            },
            "odor threshold evidence",
        )
        _schema(payload, cls._SCHEMA, "odor threshold evidence")
        result = cls(
            threshold_id=payload["threshold_id"],
            analyte_id=payload["analyte_id"],
            quantity=BoundedQuantity.from_mapping(payload["quantity"]),
            kind=_enum_value(ThresholdKind, payload["kind"], "kind"),
            authority=_enum_value(
                ThresholdAuthority,
                payload["authority"],
                "authority",
            ),
            context=GasPhaseContext.from_mapping(payload["context"]),
            method=payload["method"],
            assessor_population=payload["assessor_population"],
            assessor_count=payload["assessor_count"],
            source=EvidenceReference.from_mapping(payload["source"]),
        )
        _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


@dataclass(frozen=True, slots=True)
class HeadspaceOAVAssessment:
    status: OAVAssessmentStatus
    claim: C8Claim
    analyte_id: str
    gas_evidence_sha256: str
    threshold_evidence_sha256: str
    oav_point: float | None
    oav_lower: float | None
    oav_upper: float | None
    screening_class: OAVScreeningClass
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-headspace-oav-assessment-v1"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "status",
            _direct_enum(OAVAssessmentStatus, self.status, "status"),
        )
        object.__setattr__(self, "claim", _direct_enum(C8Claim, self.claim, "claim"))
        object.__setattr__(self, "analyte_id", _nonblank(self.analyte_id, "analyte_id"))
        object.__setattr__(
            self,
            "gas_evidence_sha256",
            _sha256(self.gas_evidence_sha256, "gas_evidence_sha256"),
        )
        object.__setattr__(
            self,
            "threshold_evidence_sha256",
            _sha256(self.threshold_evidence_sha256, "threshold_evidence_sha256"),
        )
        point = _optional_finite(self.oav_point, "oav_point")
        lower = _optional_finite(self.oav_lower, "oav_lower")
        upper = _optional_finite(self.oav_upper, "oav_upper")
        object.__setattr__(
            self,
            "screening_class",
            _direct_enum(OAVScreeningClass, self.screening_class, "screening_class"),
        )
        reasons = _canonical_strings(self.reasons, "reasons")
        limitations = _strings(self.limitations, "limitations", allow_empty=False)
        if self.status is OAVAssessmentStatus.ABSTAINED:
            if any(value is not None for value in (point, lower, upper)):
                raise HeadspaceOAVContractError("abstained OAV assessment must be answerless")
            if self.screening_class is not OAVScreeningClass.UNKNOWN:
                raise HeadspaceOAVContractError("abstained OAV screening class must be UNKNOWN")
            if not reasons:
                raise HeadspaceOAVContractError("abstained OAV assessment requires reasons")
        else:
            if self.claim is not C8Claim.ABOVE_THRESHOLD_SCREENING:
                raise HeadspaceOAVContractError("computed OAV supports screening claim only")
            if any(value is None or value <= 0.0 for value in (point, lower, upper)):
                raise HeadspaceOAVContractError("computed OAV requires positive values and bounds")
            if lower is not None and point is not None and upper is not None:
                if not lower <= point <= upper:
                    raise HeadspaceOAVContractError("computed OAV point must lie within bounds")
            if self.screening_class is OAVScreeningClass.UNKNOWN:
                raise HeadspaceOAVContractError("computed OAV requires a screening class")
            if reasons:
                raise HeadspaceOAVContractError("computed OAV must not contain abstention reasons")
        object.__setattr__(self, "oav_point", point)
        object.__setattr__(self, "oav_lower", lower)
        object.__setattr__(self, "oav_upper", upper)
        object.__setattr__(self, "reasons", reasons)
        object.__setattr__(self, "limitations", limitations)
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "status": self.status.value,
            "claim": self.claim.value,
            "analyte_id": self.analyte_id,
            "gas_evidence_sha256": self.gas_evidence_sha256,
            "threshold_evidence_sha256": self.threshold_evidence_sha256,
            "oav_point": self.oav_point,
            "oav_lower": self.oav_lower,
            "oav_upper": self.oav_upper,
            "screening_class": self.screening_class.value,
            "reasons": list(self.reasons),
            "limitations": list(self.limitations),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> HeadspaceOAVAssessment:
        payload = _mapping(value, "headspace OAV assessment")
        _exact_keys_with_optional_hash(
            payload,
            {
                "schema",
                "status",
                "claim",
                "analyte_id",
                "gas_evidence_sha256",
                "threshold_evidence_sha256",
                "oav_point",
                "oav_lower",
                "oav_upper",
                "screening_class",
                "reasons",
                "limitations",
                "content_sha256",
            },
            "headspace OAV assessment",
        )
        _schema(payload, cls._SCHEMA, "headspace OAV assessment")
        result = cls(
            status=_enum_value(OAVAssessmentStatus, payload["status"], "status"),
            claim=_enum_value(C8Claim, payload["claim"], "claim"),
            analyte_id=payload["analyte_id"],
            gas_evidence_sha256=payload["gas_evidence_sha256"],
            threshold_evidence_sha256=payload["threshold_evidence_sha256"],
            oav_point=payload["oav_point"],
            oav_lower=payload["oav_lower"],
            oav_upper=payload["oav_upper"],
            screening_class=_enum_value(
                OAVScreeningClass,
                payload["screening_class"],
                "screening_class",
            ),
            reasons=_strings(payload["reasons"], "reasons"),
            limitations=_strings(payload["limitations"], "limitations"),
        )
        if "content_sha256" in payload:
            _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


def calculate_headspace_oav(
    gas: GasConcentrationEvidence,
    threshold: OdorThresholdEvidence,
    *,
    claim: C8Claim = C8Claim.ABOVE_THRESHOLD_SCREENING,
) -> HeadspaceOAVAssessment:
    if not isinstance(gas, GasConcentrationEvidence):
        raise HeadspaceOAVContractError("gas must be GasConcentrationEvidence")
    if not isinstance(threshold, OdorThresholdEvidence):
        raise HeadspaceOAVContractError("threshold must be OdorThresholdEvidence")
    claim = _direct_enum(C8Claim, claim, "claim")
    reasons: list[str] = []
    if claim is not C8Claim.ABOVE_THRESHOLD_SCREENING:
        reasons.append("requested claim is outside the OAV screening boundary")
    if gas.analyte_id != threshold.analyte_id:
        reasons.append("gas and threshold analyte identities do not match")
    if gas.origin is GasConcentrationOrigin.PREDICTED and gas.within_model_domain is not True:
        reasons.append("predicted gas concentration is outside model domain")
    if threshold.kind is not ThresholdKind.DETECTION:
        reasons.append("threshold is not a detection threshold")
    if threshold.authority not in _ADMISSIBLE_THRESHOLD_AUTHORITIES:
        reasons.append("threshold authority is not admissible for screening")
    if not gas.context.is_compatible_with(threshold.context):
        reasons.append("gas and threshold contexts are not compatible")
    if gas.quantity.unit != threshold.quantity.unit:
        reasons.append("gas and threshold units do not match")
    if not gas.quantity.has_numeric_bounds or not threshold.quantity.has_numeric_bounds:
        reasons.append("numeric uncertainty bounds are required for OAV screening")

    if reasons:
        return HeadspaceOAVAssessment(
            status=OAVAssessmentStatus.ABSTAINED,
            claim=claim,
            analyte_id=gas.analyte_id,
            gas_evidence_sha256=gas.content_sha256,
            threshold_evidence_sha256=threshold.content_sha256,
            oav_point=None,
            oav_lower=None,
            oav_upper=None,
            screening_class=OAVScreeningClass.UNKNOWN,
            reasons=tuple(reasons),
            limitations=_OAV_LIMITATIONS,
        )

    gas_lower = gas.quantity.lower_bound
    gas_upper = gas.quantity.upper_bound
    threshold_lower = threshold.quantity.lower_bound
    threshold_upper = threshold.quantity.upper_bound
    if gas_lower is None or gas_upper is None or threshold_lower is None or threshold_upper is None:
        raise HeadspaceOAVContractError("bounded OAV precondition was not enforced")
    point = gas.quantity.value / threshold.quantity.value
    lower = gas_lower / threshold_upper
    upper = gas_upper / threshold_lower
    if lower >= 1.0:
        screening_class = OAVScreeningClass.ABOVE_THRESHOLD
    elif upper < 1.0:
        screening_class = OAVScreeningClass.BELOW_THRESHOLD
    else:
        screening_class = OAVScreeningClass.STRADDLES_THRESHOLD
    return HeadspaceOAVAssessment(
        status=OAVAssessmentStatus.COMPUTED,
        claim=claim,
        analyte_id=gas.analyte_id,
        gas_evidence_sha256=gas.content_sha256,
        threshold_evidence_sha256=threshold.content_sha256,
        oav_point=point,
        oav_lower=lower,
        oav_upper=upper,
        screening_class=screening_class,
        reasons=(),
        limitations=_OAV_LIMITATIONS,
    )


@dataclass(frozen=True, slots=True)
class InteractionConcentration:
    identity_id: str
    quantity: BoundedQuantity
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-interaction-concentration-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity_id", _nonblank(self.identity_id, "identity_id"))
        if not isinstance(self.quantity, BoundedQuantity):
            raise HeadspaceOAVContractError("quantity must be a BoundedQuantity")
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "identity_id": self.identity_id,
            "quantity": self.quantity.to_mapping(),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> InteractionConcentration:
        payload = _mapping(value, "interaction concentration")
        _exact_keys(
            payload,
            {"schema", "identity_id", "quantity", "content_sha256"},
            "interaction concentration",
        )
        _schema(payload, cls._SCHEMA, "interaction concentration")
        result = cls(
            identity_id=payload["identity_id"],
            quantity=BoundedQuantity.from_mapping(payload["quantity"]),
        )
        _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


@dataclass(frozen=True, slots=True)
class InteractionApplicableRange:
    identity_id: str
    lower_bound: float
    upper_bound: float
    unit: str
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-interaction-applicable-range-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity_id", _nonblank(self.identity_id, "identity_id"))
        lower = _positive(self.lower_bound, "lower_bound")
        upper = _positive(self.upper_bound, "upper_bound")
        if lower > upper:
            raise HeadspaceOAVContractError("applicable lower_bound must not exceed upper_bound")
        object.__setattr__(self, "lower_bound", lower)
        object.__setattr__(self, "upper_bound", upper)
        object.__setattr__(self, "unit", _nonblank(self.unit, "unit"))
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "identity_id": self.identity_id,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "unit": self.unit,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> InteractionApplicableRange:
        payload = _mapping(value, "interaction applicable range")
        _exact_keys(
            payload,
            {
                "schema",
                "identity_id",
                "lower_bound",
                "upper_bound",
                "unit",
                "content_sha256",
            },
            "interaction applicable range",
        )
        _schema(payload, cls._SCHEMA, "interaction applicable range")
        result = cls(
            identity_id=payload["identity_id"],
            lower_bound=payload["lower_bound"],
            upper_bound=payload["upper_bound"],
            unit=payload["unit"],
        )
        _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


@dataclass(frozen=True, slots=True)
class InteractionNumericalEffect:
    target: InteractionAdjustmentTarget
    multiplier: BoundedQuantity
    formula: str
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-interaction-numerical-effect-v1"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target",
            _direct_enum(InteractionAdjustmentTarget, self.target, "target"),
        )
        if not isinstance(self.multiplier, BoundedQuantity):
            raise HeadspaceOAVContractError("multiplier must be a BoundedQuantity")
        if self.multiplier.unit != "1":
            raise HeadspaceOAVContractError("interaction multiplier must be dimensionless")
        if not self.multiplier.has_numeric_bounds:
            raise HeadspaceOAVContractError("interaction multiplier must have bounded uncertainty")
        object.__setattr__(self, "formula", _nonblank(self.formula, "formula"))
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "target": self.target.value,
            "multiplier": self.multiplier.to_mapping(),
            "formula": self.formula,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> InteractionNumericalEffect:
        payload = _mapping(value, "interaction numerical effect")
        _exact_keys(
            payload,
            {"schema", "target", "multiplier", "formula", "content_sha256"},
            "interaction numerical effect",
        )
        _schema(payload, cls._SCHEMA, "interaction numerical effect")
        result = cls(
            target=_enum_value(
                InteractionAdjustmentTarget,
                payload["target"],
                "target",
            ),
            multiplier=BoundedQuantity.from_mapping(payload["multiplier"]),
            formula=payload["formula"],
        )
        _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


@dataclass(frozen=True, slots=True)
class InteractionEvidence:
    interaction_id: str
    kind: InteractionKind
    evidence_kind: InteractionEvidenceKind
    identities: tuple[str, ...]
    concentrations: tuple[InteractionConcentration, ...]
    context: GasPhaseContext
    attribute: str
    sensory_method: str
    assessor_population: str
    assessor_count: int
    model_or_formula: str | None
    source: EvidenceReference
    uncertainty_statement: str
    applicable_ranges: tuple[InteractionApplicableRange, ...]
    calibration_state: InteractionCalibrationState
    numerical_effect: InteractionNumericalEffect | None
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-interaction-evidence-v1"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "interaction_id",
            _nonblank(self.interaction_id, "interaction_id"),
        )
        object.__setattr__(self, "kind", _direct_enum(InteractionKind, self.kind, "kind"))
        object.__setattr__(
            self,
            "evidence_kind",
            _direct_enum(InteractionEvidenceKind, self.evidence_kind, "evidence_kind"),
        )
        identities = _strings(self.identities, "identities", allow_empty=False)
        if len(identities) < 2:
            raise HeadspaceOAVContractError("interaction identities require at least two values")
        concentrations = tuple(self.concentrations)
        if any(not isinstance(item, InteractionConcentration) for item in concentrations):
            raise HeadspaceOAVContractError(
                "concentrations must contain InteractionConcentration records"
            )
        if tuple(item.identity_id for item in concentrations) != identities:
            raise HeadspaceOAVContractError(
                "interaction concentration coverage must exactly match identities"
            )
        ranges = tuple(self.applicable_ranges)
        if any(not isinstance(item, InteractionApplicableRange) for item in ranges):
            raise HeadspaceOAVContractError(
                "applicable_ranges must contain InteractionApplicableRange records"
            )
        if tuple(item.identity_id for item in ranges) != identities:
            raise HeadspaceOAVContractError(
                "interaction applicable range coverage must exactly match identities"
            )
        if not isinstance(self.context, GasPhaseContext):
            raise HeadspaceOAVContractError("context must be a GasPhaseContext")
        object.__setattr__(self, "attribute", _nonblank(self.attribute, "attribute"))
        object.__setattr__(
            self,
            "sensory_method",
            _nonblank(self.sensory_method, "sensory_method"),
        )
        object.__setattr__(
            self,
            "assessor_population",
            _nonblank(self.assessor_population, "assessor_population"),
        )
        object.__setattr__(
            self,
            "assessor_count",
            _positive_integer(self.assessor_count, "assessor_count"),
        )
        model_or_formula = _optional_text(self.model_or_formula, "model_or_formula")
        if not isinstance(self.source, EvidenceReference):
            raise HeadspaceOAVContractError("source must be an EvidenceReference")
        object.__setattr__(
            self,
            "uncertainty_statement",
            _nonblank(self.uncertainty_statement, "uncertainty_statement"),
        )
        object.__setattr__(
            self,
            "calibration_state",
            _direct_enum(
                InteractionCalibrationState,
                self.calibration_state,
                "calibration_state",
            ),
        )
        effect = self.numerical_effect
        if effect is not None and not isinstance(effect, InteractionNumericalEffect):
            raise HeadspaceOAVContractError(
                "numerical_effect must be an InteractionNumericalEffect or null"
            )
        if self.evidence_kind is InteractionEvidenceKind.OBSERVATION:
            if effect is not None:
                raise HeadspaceOAVContractError(
                    "observation-only interaction cannot contain a numerical effect"
                )
            if self.calibration_state is not InteractionCalibrationState.OBSERVED_ONLY:
                raise HeadspaceOAVContractError(
                    "observation evidence requires OBSERVED_ONLY calibration state"
                )
            if model_or_formula is not None:
                raise HeadspaceOAVContractError(
                    "observation evidence must not claim a model_or_formula"
                )
        elif self.calibration_state is InteractionCalibrationState.OBSERVED_ONLY:
            raise HeadspaceOAVContractError(
                "model evidence cannot use OBSERVED_ONLY calibration state"
            )
        if self.calibration_state is InteractionCalibrationState.UNCALIBRATED_GENERIC:
            if effect is not None:
                raise HeadspaceOAVContractError(
                    "uncalibrated interaction cannot contain a numerical effect"
                )
        if self.calibration_state is InteractionCalibrationState.CONTEXT_CALIBRATED:
            if self.evidence_kind is not InteractionEvidenceKind.MODEL:
                raise HeadspaceOAVContractError(
                    "context-calibrated interaction requires model evidence"
                )
            if model_or_formula is None:
                raise HeadspaceOAVContractError(
                    "context-calibrated interaction requires model_or_formula"
                )
            if effect is None:
                raise HeadspaceOAVContractError(
                    "context-calibrated interaction requires a bounded numerical effect"
                )
        object.__setattr__(self, "identities", identities)
        object.__setattr__(self, "concentrations", concentrations)
        object.__setattr__(self, "applicable_ranges", ranges)
        object.__setattr__(self, "model_or_formula", model_or_formula)
        object.__setattr__(self, "numerical_effect", effect)
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "interaction_id": self.interaction_id,
            "kind": self.kind.value,
            "evidence_kind": self.evidence_kind.value,
            "identities": list(self.identities),
            "concentrations": [item.to_mapping() for item in self.concentrations],
            "context": self.context.to_mapping(),
            "attribute": self.attribute,
            "sensory_method": self.sensory_method,
            "assessor_population": self.assessor_population,
            "assessor_count": self.assessor_count,
            "model_or_formula": self.model_or_formula,
            "source": self.source.to_mapping(),
            "uncertainty_statement": self.uncertainty_statement,
            "applicable_ranges": [item.to_mapping() for item in self.applicable_ranges],
            "calibration_state": self.calibration_state.value,
            "numerical_effect": (
                None if self.numerical_effect is None else self.numerical_effect.to_mapping()
            ),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> InteractionEvidence:
        payload = _mapping(value, "interaction evidence")
        _exact_keys_with_optional_hash(
            payload,
            {
                "schema",
                "interaction_id",
                "kind",
                "evidence_kind",
                "identities",
                "concentrations",
                "context",
                "attribute",
                "sensory_method",
                "assessor_population",
                "assessor_count",
                "model_or_formula",
                "source",
                "uncertainty_statement",
                "applicable_ranges",
                "calibration_state",
                "numerical_effect",
                "content_sha256",
            },
            "interaction evidence",
        )
        _schema(payload, cls._SCHEMA, "interaction evidence")
        effect_payload = payload["numerical_effect"]
        result = cls(
            interaction_id=payload["interaction_id"],
            kind=_enum_value(InteractionKind, payload["kind"], "kind"),
            evidence_kind=_enum_value(
                InteractionEvidenceKind,
                payload["evidence_kind"],
                "evidence_kind",
            ),
            identities=_strings(payload["identities"], "identities"),
            concentrations=tuple(
                InteractionConcentration.from_mapping(item)
                for item in _sequence(payload["concentrations"], "concentrations")
            ),
            context=GasPhaseContext.from_mapping(payload["context"]),
            attribute=payload["attribute"],
            sensory_method=payload["sensory_method"],
            assessor_population=payload["assessor_population"],
            assessor_count=payload["assessor_count"],
            model_or_formula=payload["model_or_formula"],
            source=EvidenceReference.from_mapping(payload["source"]),
            uncertainty_statement=payload["uncertainty_statement"],
            applicable_ranges=tuple(
                InteractionApplicableRange.from_mapping(item)
                for item in _sequence(payload["applicable_ranges"], "applicable_ranges")
            ),
            calibration_state=_enum_value(
                InteractionCalibrationState,
                payload["calibration_state"],
                "calibration_state",
            ),
            numerical_effect=(
                None
                if effect_payload is None
                else InteractionNumericalEffect.from_mapping(effect_payload)
            ),
        )
        if "content_sha256" in payload:
            _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


@dataclass(frozen=True, slots=True)
class InteractionAdjustmentRequest:
    request_id: str
    identities: tuple[str, ...]
    concentrations: tuple[InteractionConcentration, ...]
    context: GasPhaseContext
    target: InteractionAdjustmentTarget
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-interaction-adjustment-request-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _nonblank(self.request_id, "request_id"))
        identities = _strings(self.identities, "identities", allow_empty=False)
        if len(identities) < 2:
            raise HeadspaceOAVContractError("adjustment identities require at least two values")
        concentrations = tuple(self.concentrations)
        if any(not isinstance(item, InteractionConcentration) for item in concentrations):
            raise HeadspaceOAVContractError(
                "concentrations must contain InteractionConcentration records"
            )
        if tuple(item.identity_id for item in concentrations) != identities:
            raise HeadspaceOAVContractError(
                "adjustment concentration coverage must exactly match identities"
            )
        if not isinstance(self.context, GasPhaseContext):
            raise HeadspaceOAVContractError("context must be a GasPhaseContext")
        object.__setattr__(
            self,
            "target",
            _direct_enum(InteractionAdjustmentTarget, self.target, "target"),
        )
        object.__setattr__(self, "identities", identities)
        object.__setattr__(self, "concentrations", concentrations)
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "request_id": self.request_id,
            "identities": list(self.identities),
            "concentrations": [item.to_mapping() for item in self.concentrations],
            "context": self.context.to_mapping(),
            "target": self.target.value,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> InteractionAdjustmentRequest:
        payload = _mapping(value, "interaction adjustment request")
        _exact_keys(
            payload,
            {
                "schema",
                "request_id",
                "identities",
                "concentrations",
                "context",
                "target",
                "content_sha256",
            },
            "interaction adjustment request",
        )
        _schema(payload, cls._SCHEMA, "interaction adjustment request")
        result = cls(
            request_id=payload["request_id"],
            identities=_strings(payload["identities"], "identities"),
            concentrations=tuple(
                InteractionConcentration.from_mapping(item)
                for item in _sequence(payload["concentrations"], "concentrations")
            ),
            context=GasPhaseContext.from_mapping(payload["context"]),
            target=_enum_value(
                InteractionAdjustmentTarget,
                payload["target"],
                "target",
            ),
        )
        _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


@dataclass(frozen=True, slots=True)
class InteractionAdjustmentDecision:
    status: InteractionAdjustmentStatus
    interaction_evidence_sha256: str
    request_sha256: str
    numerical_effect: InteractionNumericalEffect | None
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-interaction-adjustment-decision-v1"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "status",
            _direct_enum(InteractionAdjustmentStatus, self.status, "status"),
        )
        object.__setattr__(
            self,
            "interaction_evidence_sha256",
            _sha256(self.interaction_evidence_sha256, "interaction_evidence_sha256"),
        )
        object.__setattr__(self, "request_sha256", _sha256(self.request_sha256, "request_sha256"))
        if self.numerical_effect is not None and not isinstance(
            self.numerical_effect,
            InteractionNumericalEffect,
        ):
            raise HeadspaceOAVContractError(
                "numerical_effect must be an InteractionNumericalEffect or null"
            )
        reasons = _canonical_strings(self.reasons, "reasons")
        limitations = _strings(self.limitations, "limitations", allow_empty=False)
        if self.status is InteractionAdjustmentStatus.WITHHELD:
            if self.numerical_effect is not None:
                raise HeadspaceOAVContractError(
                    "withheld interaction adjustment must be answerless"
                )
            if not reasons:
                raise HeadspaceOAVContractError("withheld interaction adjustment requires reasons")
        else:
            if self.numerical_effect is None:
                raise HeadspaceOAVContractError(
                    "authorized interaction adjustment requires a numerical effect"
                )
            if reasons:
                raise HeadspaceOAVContractError(
                    "authorized interaction adjustment must not contain reasons"
                )
        object.__setattr__(self, "reasons", reasons)
        object.__setattr__(self, "limitations", limitations)
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "status": self.status.value,
            "interaction_evidence_sha256": self.interaction_evidence_sha256,
            "request_sha256": self.request_sha256,
            "numerical_effect": (
                None if self.numerical_effect is None else self.numerical_effect.to_mapping()
            ),
            "reasons": list(self.reasons),
            "limitations": list(self.limitations),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> InteractionAdjustmentDecision:
        payload = _mapping(value, "interaction adjustment decision")
        _exact_keys(
            payload,
            {
                "schema",
                "status",
                "interaction_evidence_sha256",
                "request_sha256",
                "numerical_effect",
                "reasons",
                "limitations",
                "content_sha256",
            },
            "interaction adjustment decision",
        )
        _schema(payload, cls._SCHEMA, "interaction adjustment decision")
        effect_payload = payload["numerical_effect"]
        result = cls(
            status=_enum_value(
                InteractionAdjustmentStatus,
                payload["status"],
                "status",
            ),
            interaction_evidence_sha256=payload["interaction_evidence_sha256"],
            request_sha256=payload["request_sha256"],
            numerical_effect=(
                None
                if effect_payload is None
                else InteractionNumericalEffect.from_mapping(effect_payload)
            ),
            reasons=_strings(payload["reasons"], "reasons"),
            limitations=_strings(payload["limitations"], "limitations"),
        )
        _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


def authorize_interaction_adjustment(
    evidence: InteractionEvidence,
    request: InteractionAdjustmentRequest,
) -> InteractionAdjustmentDecision:
    if not isinstance(evidence, InteractionEvidence):
        raise HeadspaceOAVContractError("evidence must be InteractionEvidence")
    if not isinstance(request, InteractionAdjustmentRequest):
        raise HeadspaceOAVContractError("request must be InteractionAdjustmentRequest")
    reasons: list[str] = []
    effect = evidence.numerical_effect
    if (
        evidence.calibration_state is not InteractionCalibrationState.CONTEXT_CALIBRATED
        or effect is None
    ):
        reasons.append("interaction calibration does not authorize a numerical effect")
    if evidence.identities != request.identities:
        reasons.append("interaction identities do not match the request")
    if not evidence.context.is_compatible_with(request.context):
        reasons.append("interaction context does not match the request")
    if effect is not None and effect.target is not request.target:
        reasons.append("interaction adjustment target does not match the request")

    if evidence.identities == request.identities:
        for concentration, allowed in zip(
            request.concentrations,
            evidence.applicable_ranges,
            strict=True,
        ):
            if concentration.quantity.unit != allowed.unit:
                reasons.append(
                    f"interaction concentration unit mismatch for {concentration.identity_id}"
                )
                continue
            lower = concentration.quantity.lower_bound
            upper = concentration.quantity.upper_bound
            if lower is None or upper is None:
                reasons.append(
                    f"interaction concentration range is unknown for {concentration.identity_id}"
                )
            elif lower < allowed.lower_bound or upper > allowed.upper_bound:
                reasons.append(
                    f"interaction concentration is outside calibrated range for {concentration.identity_id}"
                )

    limitations = (
        "Authorization exposes a bounded effect but does not apply it.",
        "Authority is limited to the recorded identities, concentrations, and context.",
    )
    if reasons:
        return InteractionAdjustmentDecision(
            status=InteractionAdjustmentStatus.WITHHELD,
            interaction_evidence_sha256=evidence.content_sha256,
            request_sha256=request.content_sha256,
            numerical_effect=None,
            reasons=tuple(reasons),
            limitations=limitations,
        )
    return InteractionAdjustmentDecision(
        status=InteractionAdjustmentStatus.AUTHORIZED,
        interaction_evidence_sha256=evidence.content_sha256,
        request_sha256=request.content_sha256,
        numerical_effect=effect,
        reasons=(),
        limitations=limitations,
    )


@dataclass(frozen=True, slots=True)
class SensomicsStageRecord:
    stage: SensomicsStage
    status: SensomicsStageStatus
    evidence: tuple[EvidenceReference, ...]
    notes: tuple[str, ...]
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-sensomics-stage-record-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage", _direct_enum(SensomicsStage, self.stage, "stage"))
        object.__setattr__(
            self,
            "status",
            _direct_enum(SensomicsStageStatus, self.status, "status"),
        )
        evidence = tuple(self.evidence)
        if any(not isinstance(item, EvidenceReference) for item in evidence):
            raise HeadspaceOAVContractError(
                "sensomics evidence must contain EvidenceReference records"
            )
        evidence_hashes = tuple(item.content_sha256 for item in evidence)
        if len(evidence_hashes) != len(set(evidence_hashes)):
            raise HeadspaceOAVContractError("sensomics evidence contains duplicate references")
        if self.status is SensomicsStageStatus.COMPLETED and not evidence:
            raise HeadspaceOAVContractError("completed sensomics stage requires immutable evidence")
        notes = _strings(self.notes, "notes")
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "notes", notes)
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "stage": self.stage.value,
            "status": self.status.value,
            "evidence": [item.to_mapping() for item in self.evidence],
            "notes": list(self.notes),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> SensomicsStageRecord:
        payload = _mapping(value, "sensomics stage record")
        _exact_keys(
            payload,
            {"schema", "stage", "status", "evidence", "notes", "content_sha256"},
            "sensomics stage record",
        )
        _schema(payload, cls._SCHEMA, "sensomics stage record")
        result = cls(
            stage=_enum_value(SensomicsStage, payload["stage"], "stage"),
            status=_enum_value(SensomicsStageStatus, payload["status"], "status"),
            evidence=tuple(
                EvidenceReference.from_mapping(item)
                for item in _sequence(payload["evidence"], "evidence")
            ),
            notes=_strings(payload["notes"], "notes"),
        )
        _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


@dataclass(frozen=True, slots=True)
class SensomicsProgram:
    program_id: str
    context: GasPhaseContext
    stages: tuple[SensomicsStageRecord, ...]
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-sensomics-program-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "program_id", _nonblank(self.program_id, "program_id"))
        if not isinstance(self.context, GasPhaseContext):
            raise HeadspaceOAVContractError("context must be a GasPhaseContext")
        stages = tuple(self.stages)
        if any(not isinstance(item, SensomicsStageRecord) for item in stages):
            raise HeadspaceOAVContractError("stages must contain SensomicsStageRecord records")
        if tuple(item.stage for item in stages) != C8_SENSOMICS_SEQUENCE:
            raise HeadspaceOAVContractError(
                "sensomics stages must contain every stage in exact order"
            )
        incomplete_seen = False
        for record in stages:
            if record.status is SensomicsStageStatus.COMPLETED:
                if incomplete_seen:
                    raise HeadspaceOAVContractError(
                        "completed sensomics stages must form a contiguous prefix"
                    )
            else:
                incomplete_seen = True
        object.__setattr__(self, "stages", stages)
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    @property
    def completed_prefix_length(self) -> int:
        count = 0
        for record in self.stages:
            if record.status is not SensomicsStageStatus.COMPLETED:
                break
            count += 1
        return count

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "program_id": self.program_id,
            "context": self.context.to_mapping(),
            "stages": [item.to_mapping() for item in self.stages],
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> SensomicsProgram:
        payload = _mapping(value, "sensomics program")
        _exact_keys(
            payload,
            {"schema", "program_id", "context", "stages", "content_sha256"},
            "sensomics program",
        )
        _schema(payload, cls._SCHEMA, "sensomics program")
        result = cls(
            program_id=payload["program_id"],
            context=GasPhaseContext.from_mapping(payload["context"]),
            stages=tuple(
                SensomicsStageRecord.from_mapping(item)
                for item in _sequence(payload["stages"], "stages")
            ),
        )
        _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


@dataclass(frozen=True, slots=True)
class SensomicsAssessment:
    claim: SensomicsClaim
    status: C8ClaimStatus
    program_sha256: str
    evidence_sha256: tuple[str, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-sensomics-assessment-v1"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "claim",
            _direct_enum(SensomicsClaim, self.claim, "claim"),
        )
        object.__setattr__(
            self,
            "status",
            _direct_enum(C8ClaimStatus, self.status, "status"),
        )
        object.__setattr__(
            self,
            "program_sha256",
            _sha256(self.program_sha256, "program_sha256"),
        )
        evidence_sha256 = tuple(
            sorted(
                (
                    _sha256(item, "evidence_sha256")
                    for item in _sequence(self.evidence_sha256, "evidence_sha256")
                )
            )
        )
        if len(evidence_sha256) != len(set(evidence_sha256)):
            raise HeadspaceOAVContractError("evidence_sha256 contains duplicate values")
        reasons = _canonical_strings(self.reasons, "reasons")
        limitations = _strings(self.limitations, "limitations", allow_empty=False)
        if self.status is C8ClaimStatus.WITHHELD:
            if evidence_sha256:
                raise HeadspaceOAVContractError("withheld sensomics assessment must be answerless")
            if not reasons:
                raise HeadspaceOAVContractError("withheld sensomics assessment requires reasons")
        else:
            if not evidence_sha256:
                raise HeadspaceOAVContractError(
                    "permitted sensomics assessment requires immutable evidence"
                )
            if reasons:
                raise HeadspaceOAVContractError(
                    "permitted sensomics assessment must not contain reasons"
                )
        object.__setattr__(self, "evidence_sha256", evidence_sha256)
        object.__setattr__(self, "reasons", reasons)
        object.__setattr__(self, "limitations", limitations)
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "claim": self.claim.value,
            "status": self.status.value,
            "program_sha256": self.program_sha256,
            "evidence_sha256": list(self.evidence_sha256),
            "reasons": list(self.reasons),
            "limitations": list(self.limitations),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> SensomicsAssessment:
        payload = _mapping(value, "sensomics assessment")
        _exact_keys(
            payload,
            {
                "schema",
                "claim",
                "status",
                "program_sha256",
                "evidence_sha256",
                "reasons",
                "limitations",
                "content_sha256",
            },
            "sensomics assessment",
        )
        _schema(payload, cls._SCHEMA, "sensomics assessment")
        result = cls(
            claim=_enum_value(SensomicsClaim, payload["claim"], "claim"),
            status=_enum_value(C8ClaimStatus, payload["status"], "status"),
            program_sha256=payload["program_sha256"],
            evidence_sha256=tuple(
                _sha256(item, "evidence_sha256")
                for item in _sequence(payload["evidence_sha256"], "evidence_sha256")
            ),
            reasons=_strings(payload["reasons"], "reasons"),
            limitations=_strings(payload["limitations"], "limitations"),
        )
        _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


def _program_evidence_hashes(program: SensomicsProgram) -> tuple[str, ...]:
    hashes = {
        reference.content_sha256
        for record in program.stages
        if record.status is SensomicsStageStatus.COMPLETED
        for reference in record.evidence
    }
    return tuple(sorted(hashes))


def evaluate_sensomics_claim(
    program: SensomicsProgram,
    claim: SensomicsClaim,
) -> SensomicsAssessment:
    if not isinstance(program, SensomicsProgram):
        raise HeadspaceOAVContractError("program must be a SensomicsProgram")
    claim = _direct_enum(SensomicsClaim, claim, "claim")
    required = (
        5
        if claim is SensomicsClaim.CANDIDATE_ODORANT_PRIORITIZATION
        else len(C8_SENSOMICS_SEQUENCE)
    )
    limitations: tuple[str, ...] = (
        "The decision is limited to the recorded tested context.",
        "Candidate prioritization is a screening result, not a causal mixture claim.",
    )
    if claim is SensomicsClaim.MATERIAL_EFFECT_IN_TESTED_CONTEXT:
        limitations += (
            "An omission or addition effect does not mean the material resembles the mixture.",
        )
    if program.completed_prefix_length < required:
        return SensomicsAssessment(
            claim=claim,
            status=C8ClaimStatus.WITHHELD,
            program_sha256=program.content_sha256,
            evidence_sha256=(),
            reasons=(f"claim requires {required} completed contiguous sensomics stages",),
            limitations=limitations,
        )
    return SensomicsAssessment(
        claim=claim,
        status=C8ClaimStatus.PERMITTED_WITH_EVIDENCE,
        program_sha256=program.content_sha256,
        evidence_sha256=_program_evidence_hashes(program),
        reasons=(),
        limitations=limitations,
    )


@dataclass(frozen=True, slots=True)
class C8ClaimDecision:
    claim: C8Claim
    status: C8ClaimStatus
    evidence_sha256: tuple[str, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]
    content_sha256: str = field(init=False)

    _SCHEMA = "c8-claim-decision-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim", _direct_enum(C8Claim, self.claim, "claim"))
        object.__setattr__(
            self,
            "status",
            _direct_enum(C8ClaimStatus, self.status, "status"),
        )
        evidence_sha256 = tuple(
            sorted(
                (
                    _sha256(item, "evidence_sha256")
                    for item in _sequence(self.evidence_sha256, "evidence_sha256")
                )
            )
        )
        if len(evidence_sha256) != len(set(evidence_sha256)):
            raise HeadspaceOAVContractError("evidence_sha256 contains duplicate values")
        reasons = _canonical_strings(self.reasons, "reasons")
        limitations = _strings(self.limitations, "limitations", allow_empty=False)
        if self.status is C8ClaimStatus.WITHHELD:
            if evidence_sha256:
                raise HeadspaceOAVContractError("withheld C8 claim decision must be answerless")
            if not reasons:
                raise HeadspaceOAVContractError("withheld C8 claim decision requires reasons")
        else:
            if self.claim not in PERMITTED_C8_CLAIMS:
                raise HeadspaceOAVContractError("unsupported C8 claim cannot be permitted")
            if not evidence_sha256:
                raise HeadspaceOAVContractError("permitted C8 claim requires immutable evidence")
            if reasons:
                raise HeadspaceOAVContractError(
                    "permitted C8 claim decision must not contain reasons"
                )
        object.__setattr__(self, "evidence_sha256", evidence_sha256)
        object.__setattr__(self, "reasons", reasons)
        object.__setattr__(self, "limitations", limitations)
        object.__setattr__(self, "content_sha256", _hash(self._payload()))

    def _payload(self) -> dict[str, object]:
        return {
            "schema": self._SCHEMA,
            "claim": self.claim.value,
            "status": self.status.value,
            "evidence_sha256": list(self.evidence_sha256),
            "reasons": list(self.reasons),
            "limitations": list(self.limitations),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._payload(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, value: object) -> C8ClaimDecision:
        payload = _mapping(value, "C8 claim decision")
        _exact_keys_with_optional_hash(
            payload,
            {
                "schema",
                "claim",
                "status",
                "evidence_sha256",
                "reasons",
                "limitations",
                "content_sha256",
            },
            "C8 claim decision",
        )
        _schema(payload, cls._SCHEMA, "C8 claim decision")
        result = cls(
            claim=_enum_value(C8Claim, payload["claim"], "claim"),
            status=_enum_value(C8ClaimStatus, payload["status"], "status"),
            evidence_sha256=tuple(
                _sha256(item, "evidence_sha256")
                for item in _sequence(payload["evidence_sha256"], "evidence_sha256")
            ),
            reasons=_strings(payload["reasons"], "reasons"),
            limitations=_strings(payload["limitations"], "limitations"),
        )
        if "content_sha256" in payload:
            _verify_content_hash(payload["content_sha256"], result.content_sha256)
        return result


def evaluate_c8_claim(
    claim: C8Claim,
    *,
    evidence: tuple[EvidenceReference, ...],
) -> C8ClaimDecision:
    claim = _direct_enum(C8Claim, claim, "claim")
    references = tuple(evidence)
    if any(not isinstance(item, EvidenceReference) for item in references):
        raise HeadspaceOAVContractError("evidence must contain EvidenceReference records")
    evidence_hashes = tuple(sorted({item.content_sha256 for item in references}))
    limitations = (
        "C8 enforces a claim boundary; evidence existence does not validate an upstream model.",
        "Every permitted claim remains limited to its recorded evidence and context.",
    )
    if claim in WITHHELD_C8_CLAIMS:
        return C8ClaimDecision(
            claim=claim,
            status=C8ClaimStatus.WITHHELD,
            evidence_sha256=(),
            reasons=("claim is outside Build C8 authority",),
            limitations=limitations,
        )
    if not evidence_hashes:
        return C8ClaimDecision(
            claim=claim,
            status=C8ClaimStatus.WITHHELD,
            evidence_sha256=(),
            reasons=("permitted C8 claim requires immutable supporting evidence",),
            limitations=limitations,
        )
    return C8ClaimDecision(
        claim=claim,
        status=C8ClaimStatus.PERMITTED_WITH_EVIDENCE,
        evidence_sha256=evidence_hashes,
        reasons=(),
        limitations=limitations,
    )


__all__ = [
    "C8_SENSOMICS_SEQUENCE",
    "PERMITTED_C8_CLAIMS",
    "WITHHELD_C8_CLAIMS",
    "BoundedQuantity",
    "C8Claim",
    "C8ClaimDecision",
    "C8ClaimStatus",
    "EvidenceReference",
    "GasConcentrationEvidence",
    "GasConcentrationOrigin",
    "GasPhaseContext",
    "HeadspaceOAVAssessment",
    "HeadspaceOAVContractError",
    "InteractionAdjustmentDecision",
    "InteractionAdjustmentRequest",
    "InteractionAdjustmentStatus",
    "InteractionAdjustmentTarget",
    "InteractionApplicableRange",
    "InteractionCalibrationState",
    "InteractionConcentration",
    "InteractionEvidence",
    "InteractionEvidenceKind",
    "InteractionKind",
    "InteractionNumericalEffect",
    "OAVAssessmentStatus",
    "OAVScreeningClass",
    "OdorThresholdEvidence",
    "SensomicsAssessment",
    "SensomicsClaim",
    "SensomicsProgram",
    "SensomicsStage",
    "SensomicsStageRecord",
    "SensomicsStageStatus",
    "ThresholdAuthority",
    "ThresholdKind",
    "authorize_interaction_adjustment",
    "calculate_headspace_oav",
    "evaluate_c8_claim",
    "evaluate_sensomics_claim",
]
