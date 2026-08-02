"""Closed vapor-pressure representations without equation evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from engine.calibration.hashing import stable_json_hash
from engine.physics.properties import (
    CanonicalScope,
    PropertyIdentity,
    SourceReference,
    ThermophysicalContractError,
    UncertaintyDescriptor,
    _exact_keys,
    _finite,
    _mapping,
    _nonblank,
)


class VaporPressureEquationType(str, Enum):
    MEASURED_TABLE = "MEASURED_TABLE"
    ANTOINE = "ANTOINE"
    WAGNER = "WAGNER"
    DIPPR_STYLE = "DIPPR_STYLE"
    CLAUSIUS_CLAPEYRON = "CLAUSIUS_CLAPEYRON"
    OTHER_DECLARED_FORM = "OTHER_DECLARED_FORM"


class ExtrapolationPolicy(str, Enum):
    FORBID = "FORBID"
    ADVISORY_ONLY_WITH_WARNING = "ADVISORY_ONLY_WITH_WARNING"


@dataclass(frozen=True, slots=True)
class VaporPressureCoefficient:
    name: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _nonblank(self.name, "coefficient name"))
        object.__setattr__(
            self,
            "value",
            _finite(self.value, "coefficient value"),
        )
        object.__setattr__(self, "unit", _nonblank(self.unit, "coefficient unit"))

    @classmethod
    def from_mapping(
        cls, payload: Mapping[str, Any]
    ) -> VaporPressureCoefficient:
        normalized = _mapping(payload, "coefficient")
        _exact_keys(normalized, {"name", "value", "unit"}, "coefficient")
        return cls(
            name=normalized["name"],
            value=normalized["value"],
            unit=normalized["unit"],
        )

    def to_mapping(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value, "unit": self.unit}


@dataclass(frozen=True, slots=True)
class VaporPressurePoint:
    temperature_k: float
    pressure: float
    pressure_unit: str

    def __post_init__(self) -> None:
        temperature = _finite(self.temperature_k, "temperature_k")
        pressure = _finite(self.pressure, "pressure")
        if temperature <= 0:
            raise ThermophysicalContractError("temperature_k must be positive")
        if pressure <= 0:
            raise ThermophysicalContractError("pressure must be positive")
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "pressure", pressure)
        object.__setattr__(
            self,
            "pressure_unit",
            _nonblank(self.pressure_unit, "pressure_unit"),
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> VaporPressurePoint:
        normalized = _mapping(payload, "measured point")
        _exact_keys(
            normalized,
            {"temperature_k", "pressure", "pressure_unit"},
            "measured point",
        )
        return cls(
            temperature_k=normalized["temperature_k"],
            pressure=normalized["pressure"],
            pressure_unit=normalized["pressure_unit"],
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "temperature_k": self.temperature_k,
            "pressure": self.pressure,
            "pressure_unit": self.pressure_unit,
        }


@dataclass(frozen=True, slots=True)
class TemperatureRange:
    lower_k: float
    upper_k: float

    def __post_init__(self) -> None:
        lower = _finite(self.lower_k, "temperature range lower_k")
        upper = _finite(self.upper_k, "temperature range upper_k")
        if lower <= 0 or upper <= 0 or lower > upper:
            raise ThermophysicalContractError(
                "temperature range must have positive ordered bounds"
            )
        object.__setattr__(self, "lower_k", lower)
        object.__setattr__(self, "upper_k", upper)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> TemperatureRange:
        normalized = _mapping(payload, "valid_temperature_range")
        _exact_keys(
            normalized,
            {"lower_k", "upper_k"},
            "valid_temperature_range",
        )
        return cls(
            lower_k=normalized["lower_k"],
            upper_k=normalized["upper_k"],
        )

    def contains(self, temperature_k: float) -> bool:
        temperature = _finite(temperature_k, "temperature_k")
        return self.lower_k <= temperature <= self.upper_k

    def to_mapping(self) -> dict[str, float]:
        return {"lower_k": self.lower_k, "upper_k": self.upper_k}


@dataclass(frozen=True, slots=True)
class VaporPressureRepresentation:
    """A declared table or equation, never an equation evaluator."""

    model_id: str
    model_version: str
    identity: PropertyIdentity
    equation_type: VaporPressureEquationType
    equation_convention: str
    coefficients: tuple[VaporPressureCoefficient, ...]
    pressure_unit: str
    temperature_unit: str
    valid_temperature_range: TemperatureRange
    phase_assumption: str
    purity_assumption: CanonicalScope
    source: SourceReference
    measured_points: tuple[VaporPressurePoint, ...]
    fit_evidence: CanonicalScope | None
    uncertainty: UncertaintyDescriptor
    extrapolation_policy: ExtrapolationPolicy
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        model_id = _nonblank(self.model_id, "model_id")
        model_version = _nonblank(self.model_version, "model_version")
        convention = _nonblank(
            self.equation_convention, "equation_convention"
        )
        pressure_unit = _nonblank(self.pressure_unit, "pressure_unit")
        temperature_unit = _nonblank(
            self.temperature_unit, "temperature_unit"
        )
        if temperature_unit != "K":
            raise ThermophysicalContractError(
                "temperature_unit must be K because C1 has no conversion engine"
            )
        phase = _nonblank(self.phase_assumption, "phase_assumption")
        if not self.purity_assumption.to_mapping():
            raise ThermophysicalContractError(
                "purity_assumption must not be empty"
            )
        if self.source.source_kind != "MODEL_DECLARATION":
            raise ThermophysicalContractError(
                "vapor-pressure model source must be a model declaration"
            )

        coefficients = tuple(self.coefficients)
        measured_points = tuple(self.measured_points)
        coefficient_names = [item.name for item in coefficients]
        if len(coefficient_names) != len(set(coefficient_names)):
            raise ThermophysicalContractError(
                "coefficient names must be unique"
            )
        if self.equation_type is VaporPressureEquationType.MEASURED_TABLE:
            if coefficients:
                raise ThermophysicalContractError(
                    "MEASURED_TABLE forbids coefficients"
                )
            if not measured_points:
                raise ThermophysicalContractError(
                    "MEASURED_TABLE requires measured_points"
                )
        elif not coefficients:
            raise ThermophysicalContractError(
                f"{self.equation_type.value} requires coefficients"
            )
        for point in measured_points:
            if point.pressure_unit != pressure_unit:
                raise ThermophysicalContractError(
                    "measured point pressure_unit must match representation pressure_unit"
                )
            if not self.valid_temperature_range.contains(point.temperature_k):
                raise ThermophysicalContractError(
                    "measured point must be inside the valid temperature range"
                )

        object.__setattr__(self, "model_id", model_id)
        object.__setattr__(self, "model_version", model_version)
        object.__setattr__(self, "equation_convention", convention)
        object.__setattr__(self, "coefficients", coefficients)
        object.__setattr__(self, "pressure_unit", pressure_unit)
        object.__setattr__(self, "temperature_unit", temperature_unit)
        object.__setattr__(self, "phase_assumption", phase)
        object.__setattr__(self, "measured_points", measured_points)
        object.__setattr__(
            self,
            "content_sha256",
            stable_json_hash(self.to_mapping()),
        )

    @classmethod
    def from_mapping(
        cls, payload: Mapping[str, Any]
    ) -> VaporPressureRepresentation:
        normalized = _mapping(payload, "vapor-pressure representation")
        expected = {
            "schema",
            "model_id",
            "model_version",
            "identity",
            "equation_type",
            "equation_convention",
            "coefficients",
            "pressure_unit",
            "temperature_unit",
            "valid_temperature_range",
            "phase_assumption",
            "purity_assumption",
            "source",
            "measured_points",
            "fit_evidence",
            "uncertainty",
            "extrapolation_policy",
        }
        _exact_keys(normalized, expected, "vapor-pressure representation")
        if normalized["schema"] != "c1-vapor-pressure-representation-v1":
            raise ThermophysicalContractError(
                "vapor-pressure representation schema is not supported"
            )
        try:
            equation_type = VaporPressureEquationType(
                normalized["equation_type"]
            )
        except ValueError as exc:
            raise ThermophysicalContractError(
                "equation_type is not supported"
            ) from exc
        try:
            extrapolation_policy = ExtrapolationPolicy(
                normalized["extrapolation_policy"]
            )
        except ValueError as exc:
            raise ThermophysicalContractError(
                "extrapolation_policy is not supported"
            ) from exc
        raw_coefficients = normalized["coefficients"]
        if not isinstance(raw_coefficients, (list, tuple)):
            raise ThermophysicalContractError("coefficients must be a list")
        raw_points = normalized["measured_points"]
        if not isinstance(raw_points, (list, tuple)):
            raise ThermophysicalContractError(
                "measured_points must be a list"
            )
        raw_fit = normalized["fit_evidence"]
        fit_evidence = (
            None
            if raw_fit is None
            else CanonicalScope.from_mapping(
                _mapping(raw_fit, "fit_evidence")
            )
        )
        return cls(
            model_id=normalized["model_id"],
            model_version=normalized["model_version"],
            identity=PropertyIdentity.from_mapping(
                _mapping(normalized["identity"], "identity")
            ),
            equation_type=equation_type,
            equation_convention=normalized["equation_convention"],
            coefficients=tuple(
                VaporPressureCoefficient.from_mapping(
                    _mapping(item, "coefficient")
                )
                for item in raw_coefficients
            ),
            pressure_unit=normalized["pressure_unit"],
            temperature_unit=normalized["temperature_unit"],
            valid_temperature_range=TemperatureRange.from_mapping(
                _mapping(
                    normalized["valid_temperature_range"],
                    "valid_temperature_range",
                )
            ),
            phase_assumption=normalized["phase_assumption"],
            purity_assumption=CanonicalScope.from_mapping(
                _mapping(normalized["purity_assumption"], "purity_assumption")
            ),
            source=SourceReference.from_model_mapping(
                _mapping(normalized["source"], "source")
            ),
            measured_points=tuple(
                VaporPressurePoint.from_mapping(
                    _mapping(item, "measured point")
                )
                for item in raw_points
            ),
            fit_evidence=fit_evidence,
            uncertainty=UncertaintyDescriptor.from_mapping(
                _mapping(normalized["uncertainty"], "uncertainty")
            ),
            extrapolation_policy=extrapolation_policy,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema": "c1-vapor-pressure-representation-v1",
            "model_id": self.model_id,
            "model_version": self.model_version,
            "identity": self.identity.to_mapping(),
            "equation_type": self.equation_type.value,
            "equation_convention": self.equation_convention,
            "coefficients": [item.to_mapping() for item in self.coefficients],
            "pressure_unit": self.pressure_unit,
            "temperature_unit": self.temperature_unit,
            "valid_temperature_range": self.valid_temperature_range.to_mapping(),
            "phase_assumption": self.phase_assumption,
            "purity_assumption": self.purity_assumption.to_mapping(),
            "source": {
                "source_id": self.source.model_source_id,
                "locator": self.source.locator.to_mapping(),
            },
            "measured_points": [item.to_mapping() for item in self.measured_points],
            "fit_evidence": (
                None
                if self.fit_evidence is None
                else self.fit_evidence.to_mapping()
            ),
            "uncertainty": self.uncertainty.payload.to_mapping(),
            "extrapolation_policy": self.extrapolation_policy.value,
        }


__all__ = [
    "ExtrapolationPolicy",
    "TemperatureRange",
    "VaporPressureCoefficient",
    "VaporPressureEquationType",
    "VaporPressurePoint",
    "VaporPressureRepresentation",
]
