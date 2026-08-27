"""Immutable, condition-aware thermophysical property contracts for Build C1."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from engine.calibration.hashing import canonical_json_bytes, stable_json_hash


class ThermophysicalContractError(ValueError):
    """A malformed C1 contract or unsupported closed-schema payload."""


class ThermophysicalProperty(str, Enum):
    VAPOR_PRESSURE = "vapor_pressure"
    MOLECULAR_WEIGHT = "molecular_weight"
    DENSITY = "density"
    BOILING_POINT = "boiling_point"
    ENTHALPY_OF_VAPORIZATION = "enthalpy_of_vaporization"
    WATER_SOLUBILITY = "water_solubility"
    SOLVENT_SOLUBILITY = "solvent_solubility"
    LOGP = "logp"
    LOGKOW = "logkow"
    HENRY_CONSTANT = "henry_constant"
    ACTIVITY_COEFFICIENT_PARAMETERS = "activity_coefficient_parameters"
    DIFFUSION_COEFFICIENT = "diffusion_coefficient"
    MASS_TRANSFER_PARAMETERS = "mass_transfer_parameters"
    SUBSTRATE_SORPTION_PARAMETERS = "substrate_sorption_parameters"
    HEAT_CAPACITY = "heat_capacity"
    PHASE_DATA = "phase_data"


class PropertyValueKind(str, Enum):
    NUMERIC = "NUMERIC"
    CATEGORICAL = "CATEGORICAL"
    INTERVAL = "INTERVAL"
    DISTRIBUTION = "DISTRIBUTION"
    CENSORED = "CENSORED"


class UncertaintyKind(str, Enum):
    STANDARD_UNCERTAINTY = "STANDARD_UNCERTAINTY"
    INTERVAL = "INTERVAL"
    EMPIRICAL_DISTRIBUTION = "EMPIRICAL_DISTRIBUTION"
    PARAMETER_COVARIANCE = "PARAMETER_COVARIANCE"
    BOUNDED_RANGE = "BOUNDED_RANGE"
    UNKNOWN = "UNKNOWN"


class ClaimGrade(str, Enum):
    RELEASE_GRADE = "RELEASE_GRADE"
    EXPLORATORY = "EXPLORATORY"


class SelectionStatus(str, Enum):
    SELECTED = "SELECTED"
    ADVISORY = "ADVISORY"
    WITHHELD = "WITHHELD"


def _mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ThermophysicalContractError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise ThermophysicalContractError(f"{field_name} keys must be strings")
    return dict(value)


def _nonblank(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ThermophysicalContractError(f"{field_name} must not be blank")
    return value.strip()


def _finite(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise ThermophysicalContractError(f"{field_name} must be finite")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise ThermophysicalContractError(
            f"{field_name} must be finite"
        ) from exc
    if not math.isfinite(normalized):
        raise ThermophysicalContractError(f"{field_name} must be finite")
    return normalized


def _optional_finite(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    return _finite(value, field_name)


def _exact_keys(
    payload: Mapping[str, Any],
    expected: set[str],
    field_name: str,
) -> None:
    actual = set(payload)
    missing = expected - actual
    unknown = actual - expected
    if missing:
        raise ThermophysicalContractError(
            f"{field_name} missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise ThermophysicalContractError(
            f"{field_name} contains unknown fields: {', '.join(sorted(unknown))}"
        )


@dataclass(frozen=True, slots=True)
class CanonicalScope:
    """Canonical immutable JSON mapping and its stable SHA-256."""

    canonical_json: str
    sha256: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> CanonicalScope:
        normalized = _mapping(payload, "canonical scope")
        try:
            encoded = canonical_json_bytes(normalized)
        except (TypeError, ValueError) as exc:
            raise ThermophysicalContractError(str(exc)) from exc
        return cls(
            canonical_json=encoded.decode("utf-8"),
            sha256=stable_json_hash(normalized),
        )

    def to_mapping(self) -> dict[str, Any]:
        decoded = json.loads(self.canonical_json)
        if not isinstance(decoded, dict):
            raise ThermophysicalContractError(
                "canonical scope did not decode to a mapping"
            )
        return dict(decoded)


@dataclass(frozen=True, slots=True)
class PropertyIdentity:
    """A Build B identity scope plus its canonical subject mapping."""

    identity_scope: str
    subject: CanonicalScope
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        scope = _nonblank(self.identity_scope, "identity_scope")
        if not self.subject.to_mapping():
            raise ThermophysicalContractError(
                "subject_identity must not be empty"
            )
        object.__setattr__(self, "identity_scope", scope)
        object.__setattr__(
            self,
            "content_sha256",
            stable_json_hash(
                {
                    "schema": "c1-property-identity-v1",
                    "identity_scope": scope,
                    "subject_identity": self.subject.to_mapping(),
                }
            ),
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> PropertyIdentity:
        normalized = _mapping(payload, "property identity")
        _exact_keys(
            normalized,
            {"identity_scope", "subject_identity"},
            "property identity",
        )
        return cls(
            identity_scope=_nonblank(
                normalized["identity_scope"], "identity_scope"
            ),
            subject=CanonicalScope.from_mapping(
                _mapping(normalized["subject_identity"], "subject_identity")
            ),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "identity_scope": self.identity_scope,
            "subject_identity": self.subject.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class PropertyConditions:
    """Canonical request or observation conditions with validated common fields."""

    scope: CanonicalScope
    temperature_k: float | None
    pressure_pa: float | None
    relative_humidity_percent: float | None
    matrix: str | None
    phase: str | None
    purity_fraction: float | None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> PropertyConditions:
        normalized = _mapping(payload, "property conditions")
        temperature = _optional_finite(
            normalized.get("temperature_k"), "temperature_k"
        )
        pressure = _optional_finite(
            normalized.get("pressure_pa"), "pressure_pa"
        )
        humidity = _optional_finite(
            normalized.get("relative_humidity_percent"),
            "relative_humidity_percent",
        )
        purity = _optional_finite(
            normalized.get("purity_fraction"), "purity_fraction"
        )
        if temperature is not None and temperature <= 0:
            raise ThermophysicalContractError("temperature_k must be positive")
        if pressure is not None and pressure <= 0:
            raise ThermophysicalContractError("pressure_pa must be positive")
        if humidity is not None and not 0 <= humidity <= 100:
            raise ThermophysicalContractError(
                "relative_humidity_percent must be between 0 and 100"
            )
        if purity is not None and not 0 <= purity <= 1:
            raise ThermophysicalContractError(
                "purity_fraction must be between 0 and 1"
            )
        texts: dict[str, str | None] = {}
        for name in ("matrix", "phase"):
            value = normalized.get(name)
            texts[name] = None if value is None else _nonblank(value, name)
        canonical_payload = dict(normalized)
        for name, value in (
            ("temperature_k", temperature),
            ("pressure_pa", pressure),
            ("relative_humidity_percent", humidity),
            ("purity_fraction", purity),
            ("matrix", texts["matrix"]),
            ("phase", texts["phase"]),
        ):
            if name in canonical_payload:
                canonical_payload[name] = value
        return cls(
            scope=CanonicalScope.from_mapping(canonical_payload),
            temperature_k=temperature,
            pressure_pa=pressure,
            relative_humidity_percent=humidity,
            matrix=texts["matrix"],
            phase=texts["phase"],
            purity_fraction=purity,
        )

    def supports(self, requested: PropertyConditions) -> bool:
        available = self.scope.to_mapping()
        return all(
            key in available and available[key] == value
            for key, value in requested.scope.to_mapping().items()
        )

    def to_mapping(self) -> dict[str, Any]:
        return self.scope.to_mapping()


@dataclass(frozen=True, slots=True)
class PropertyDatum:
    """One typed B2 observation value with no implicit unit conversion."""

    value_kind: PropertyValueKind
    canonical_unit: str
    numeric_value: float | None = None
    categorical_value: str | None = None
    interval_lower: float | None = None
    interval_upper: float | None = None
    distribution: CanonicalScope | None = None
    censoring_qualifier: str | None = None
    censoring_limit: float | None = None
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        unit = _nonblank(self.canonical_unit, "canonical_unit")
        numeric = _optional_finite(self.numeric_value, "numeric_value")
        lower = _optional_finite(self.interval_lower, "interval_lower")
        upper = _optional_finite(self.interval_upper, "interval_upper")
        limit = _optional_finite(self.censoring_limit, "censoring_limit")
        categorical = self.categorical_value
        qualifier = self.censoring_qualifier

        if self.value_kind is PropertyValueKind.NUMERIC:
            valid = (
                numeric is not None
                and categorical is None
                and lower is None
                and upper is None
                and self.distribution is None
                and qualifier is None
                and limit is None
            )
            message = "NUMERIC requires only numeric_value"
        elif self.value_kind is PropertyValueKind.CATEGORICAL:
            if categorical is not None:
                categorical = _nonblank(categorical, "categorical_value")
            valid = (
                numeric is None
                and categorical is not None
                and lower is None
                and upper is None
                and self.distribution is None
                and qualifier is None
                and limit is None
            )
            message = "CATEGORICAL requires only categorical_value"
        elif self.value_kind is PropertyValueKind.INTERVAL:
            valid = (
                numeric is None
                and categorical is None
                and lower is not None
                and upper is not None
                and lower <= upper
                and self.distribution is None
                and qualifier is None
                and limit is None
            )
            message = "INTERVAL requires ordered lower and upper values"
        elif self.value_kind is PropertyValueKind.DISTRIBUTION:
            valid = (
                numeric is None
                and categorical is None
                and lower is None
                and upper is None
                and self.distribution is not None
                and qualifier is None
                and limit is None
            )
            message = "DISTRIBUTION requires only a distribution mapping"
        else:
            allowed_qualifiers = {
                "LT_LOD",
                "LT_LOQ",
                "GT_UPPER_RANGE",
                "NOT_DETECTED",
                "TRACE",
            }
            if qualifier is not None:
                qualifier = _nonblank(qualifier, "censoring_qualifier")
            requires_limit = qualifier in {"LT_LOD", "LT_LOQ", "GT_UPPER_RANGE"}
            valid = (
                numeric is None
                and categorical is None
                and lower is None
                and upper is None
                and self.distribution is None
                and qualifier in allowed_qualifiers
                and ((requires_limit and limit is not None) or (not requires_limit and limit is None))
            )
            message = (
                "CENSORED requires a valid qualifier and censoring_limit when bounded"
            )
        if not valid:
            raise ThermophysicalContractError(message)

        object.__setattr__(self, "canonical_unit", unit)
        object.__setattr__(self, "numeric_value", numeric)
        object.__setattr__(self, "categorical_value", categorical)
        object.__setattr__(self, "interval_lower", lower)
        object.__setattr__(self, "interval_upper", upper)
        object.__setattr__(self, "censoring_qualifier", qualifier)
        object.__setattr__(self, "censoring_limit", limit)
        object.__setattr__(self, "content_sha256", stable_json_hash(self.to_mapping()))

    @classmethod
    def from_b2(cls, payload: Mapping[str, Any]) -> PropertyDatum:
        normalized = _mapping(payload, "property datum")
        try:
            kind = PropertyValueKind(normalized.get("value_kind"))
        except ValueError as exc:
            raise ThermophysicalContractError(
                "value_kind is not supported"
            ) from exc
        distribution_value = normalized.get("distribution")
        distribution = (
            None
            if distribution_value is None
            else CanonicalScope.from_mapping(
                _mapping(distribution_value, "distribution")
            )
        )
        return cls(
            value_kind=kind,
            canonical_unit=_nonblank(
                normalized.get("canonical_unit"), "canonical_unit"
            ),
            numeric_value=normalized.get("numeric_value"),
            categorical_value=normalized.get("categorical_value"),
            interval_lower=normalized.get("interval_lower"),
            interval_upper=normalized.get("interval_upper"),
            distribution=distribution,
            censoring_qualifier=normalized.get("censoring_qualifier"),
            censoring_limit=normalized.get("censoring_limit"),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema": "c1-property-datum-v1",
            "value_kind": self.value_kind.value,
            "canonical_unit": self.canonical_unit,
            "numeric_value": self.numeric_value,
            "categorical_value": self.categorical_value,
            "interval_lower": self.interval_lower,
            "interval_upper": self.interval_upper,
            "distribution": (
                None if self.distribution is None else self.distribution.to_mapping()
            ),
            "censoring_qualifier": self.censoring_qualifier,
            "censoring_limit": self.censoring_limit,
        }


@dataclass(frozen=True, slots=True)
class SourceReference:
    """A complete B2 observation source or a declared model source."""

    source_kind: str
    source_version_id: str | None
    extraction_record_id: str | None
    model_source_id: str | None
    locator: CanonicalScope
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if self.source_kind == "B2_OBSERVATION":
            source_version_id = _nonblank(
                self.source_version_id, "source_version_id"
            )
            extraction_record_id = _nonblank(
                self.extraction_record_id, "extraction_record_id"
            )
            if self.model_source_id is not None:
                raise ThermophysicalContractError(
                    "B2 source must not contain model_source_id"
                )
            model_source_id = None
        elif self.source_kind == "MODEL_DECLARATION":
            model_source_id = _nonblank(self.model_source_id, "source_id")
            if self.source_version_id is not None or self.extraction_record_id is not None:
                raise ThermophysicalContractError(
                    "model source must not contain B2 source identifiers"
                )
            source_version_id = None
            extraction_record_id = None
        else:
            raise ThermophysicalContractError("source_kind is not supported")
        object.__setattr__(self, "source_version_id", source_version_id)
        object.__setattr__(self, "extraction_record_id", extraction_record_id)
        object.__setattr__(self, "model_source_id", model_source_id)
        object.__setattr__(
            self,
            "content_sha256",
            stable_json_hash(self.to_mapping()),
        )

    @classmethod
    def from_b2_observation(cls, payload: Mapping[str, Any]) -> SourceReference:
        normalized = _mapping(payload, "B2 source")
        return cls(
            source_kind="B2_OBSERVATION",
            source_version_id=_nonblank(
                normalized.get("source_version_id"), "source_version_id"
            ),
            extraction_record_id=_nonblank(
                normalized.get("extraction_record_id"),
                "extraction_record_id",
            ),
            model_source_id=None,
            locator=CanonicalScope.from_mapping(
                _mapping(normalized.get("source_locator", {}), "source_locator")
            ),
        )

    @classmethod
    def from_model_mapping(cls, payload: Mapping[str, Any]) -> SourceReference:
        normalized = _mapping(payload, "model source")
        _exact_keys(normalized, {"source_id", "locator"}, "model source")
        return cls(
            source_kind="MODEL_DECLARATION",
            source_version_id=None,
            extraction_record_id=None,
            model_source_id=_nonblank(normalized.get("source_id"), "source_id"),
            locator=CanonicalScope.from_mapping(
                _mapping(normalized.get("locator"), "locator")
            ),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema": "c1-source-reference-v1",
            "source_kind": self.source_kind,
            "source_version_id": self.source_version_id,
            "extraction_record_id": self.extraction_record_id,
            "model_source_id": self.model_source_id,
            "locator": self.locator.to_mapping(),
        }


@dataclass(frozen=True, slots=True)
class UncertaintyDescriptor:
    """A closed uncertainty shape that never invents numeric precision."""

    kind: UncertaintyKind
    payload: CanonicalScope
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "content_sha256",
            stable_json_hash(self.payload.to_mapping()),
        )

    @classmethod
    def from_mapping(
        cls, payload: Mapping[str, Any]
    ) -> UncertaintyDescriptor:
        normalized = _mapping(payload, "uncertainty")
        if normalized.get("schema") != "c1-uncertainty-v1":
            raise ThermophysicalContractError(
                "uncertainty schema must be c1-uncertainty-v1"
            )
        try:
            kind = UncertaintyKind(normalized.get("kind"))
        except ValueError as exc:
            raise ThermophysicalContractError(
                "uncertainty kind is not supported"
            ) from exc

        if kind is UncertaintyKind.STANDARD_UNCERTAINTY:
            _exact_keys(
                normalized,
                {"schema", "kind", "value", "unit"},
                "uncertainty",
            )
            value = _finite(normalized["value"], "standard uncertainty")
            if value < 0:
                raise ThermophysicalContractError(
                    "standard uncertainty must be non-negative"
                )
            canonical = {
                "schema": "c1-uncertainty-v1",
                "kind": kind.value,
                "value": value,
                "unit": _nonblank(normalized["unit"], "unit"),
            }
        elif kind is UncertaintyKind.INTERVAL:
            _exact_keys(
                normalized,
                {
                    "schema",
                    "kind",
                    "interval_type",
                    "coverage_probability",
                    "lower",
                    "upper",
                    "unit",
                },
                "uncertainty",
            )
            interval_type = _nonblank(
                normalized["interval_type"], "interval_type"
            )
            if interval_type not in {"CONFIDENCE", "CREDIBLE"}:
                raise ThermophysicalContractError(
                    "interval_type must be CONFIDENCE or CREDIBLE"
                )
            coverage = _finite(
                normalized["coverage_probability"], "coverage_probability"
            )
            if not 0 < coverage < 1:
                raise ThermophysicalContractError(
                    "coverage_probability must be between 0 and 1"
                )
            lower = _finite(normalized["lower"], "lower")
            upper = _finite(normalized["upper"], "upper")
            if lower > upper:
                raise ThermophysicalContractError(
                    "interval lower must not exceed upper"
                )
            canonical = {
                "schema": "c1-uncertainty-v1",
                "kind": kind.value,
                "interval_type": interval_type,
                "coverage_probability": coverage,
                "lower": lower,
                "upper": upper,
                "unit": _nonblank(normalized["unit"], "unit"),
            }
        elif kind is UncertaintyKind.EMPIRICAL_DISTRIBUTION:
            _exact_keys(
                normalized,
                {"schema", "kind", "values", "unit"},
                "uncertainty",
            )
            raw_values = normalized["values"]
            if not isinstance(raw_values, (list, tuple)) or not raw_values:
                raise ThermophysicalContractError(
                    "empirical distribution values must not be empty"
                )
            canonical = {
                "schema": "c1-uncertainty-v1",
                "kind": kind.value,
                "values": [
                    _finite(value, "empirical distribution value")
                    for value in raw_values
                ],
                "unit": _nonblank(normalized["unit"], "unit"),
            }
        elif kind is UncertaintyKind.PARAMETER_COVARIANCE:
            _exact_keys(
                normalized,
                {
                    "schema",
                    "kind",
                    "parameter_names",
                    "matrix",
                    "parameter_units",
                },
                "uncertainty",
            )
            raw_names = normalized["parameter_names"]
            if not isinstance(raw_names, (list, tuple)) or not raw_names:
                raise ThermophysicalContractError(
                    "parameter_names must not be empty"
                )
            names = [_nonblank(name, "parameter name") for name in raw_names]
            if len(names) != len(set(names)):
                raise ThermophysicalContractError(
                    "parameter_names must be unique"
                )
            raw_matrix = normalized["matrix"]
            if not isinstance(raw_matrix, (list, tuple)) or len(raw_matrix) != len(names):
                raise ThermophysicalContractError(
                    "covariance matrix must be square"
                )
            matrix: list[list[float]] = []
            for row in raw_matrix:
                if not isinstance(row, (list, tuple)) or len(row) != len(names):
                    raise ThermophysicalContractError(
                        "covariance matrix must be square"
                    )
                matrix.append(
                    [_finite(value, "covariance value") for value in row]
                )
            for row_index in range(len(names)):
                for column_index in range(len(names)):
                    if not math.isclose(
                        matrix[row_index][column_index],
                        matrix[column_index][row_index],
                        rel_tol=1e-12,
                        abs_tol=1e-12,
                    ):
                        raise ThermophysicalContractError(
                            "covariance matrix must be symmetric"
                        )
            raw_units = _mapping(
                normalized["parameter_units"], "parameter_units"
            )
            if set(raw_units) != set(names):
                raise ThermophysicalContractError(
                    "parameter_units keys must match parameter_names"
                )
            canonical = {
                "schema": "c1-uncertainty-v1",
                "kind": kind.value,
                "parameter_names": names,
                "matrix": matrix,
                "parameter_units": {
                    name: _nonblank(raw_units[name], f"parameter_units.{name}")
                    for name in names
                },
            }
        elif kind is UncertaintyKind.BOUNDED_RANGE:
            _exact_keys(
                normalized,
                {"schema", "kind", "lower", "upper", "unit"},
                "uncertainty",
            )
            lower = _finite(normalized["lower"], "lower")
            upper = _finite(normalized["upper"], "upper")
            if lower > upper:
                raise ThermophysicalContractError(
                    "bounded range lower must not exceed upper"
                )
            canonical = {
                "schema": "c1-uncertainty-v1",
                "kind": kind.value,
                "lower": lower,
                "upper": upper,
                "unit": _nonblank(normalized["unit"], "unit"),
            }
        else:
            _exact_keys(
                normalized,
                {"schema", "kind", "reason"},
                "uncertainty",
            )
            canonical = {
                "schema": "c1-uncertainty-v1",
                "kind": kind.value,
                "reason": _nonblank(normalized["reason"], "reason"),
            }
        return cls(kind=kind, payload=CanonicalScope.from_mapping(canonical))

    @classmethod
    def unknown(cls, reason: str) -> UncertaintyDescriptor:
        return cls.from_mapping(
            {
                "schema": "c1-uncertainty-v1",
                "kind": "UNKNOWN",
                "reason": reason,
            }
        )


__all__ = [
    "CanonicalScope",
    "ClaimGrade",
    "PropertyConditions",
    "PropertyDatum",
    "PropertyIdentity",
    "PropertyValueKind",
    "SelectionStatus",
    "SourceReference",
    "ThermophysicalContractError",
    "ThermophysicalProperty",
    "UncertaintyDescriptor",
    "UncertaintyKind",
]
