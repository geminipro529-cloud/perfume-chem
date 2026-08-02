"""Immutable Build C2 matrix and application-environment contracts.

This module represents declared physical context. It does not evaluate physical
equations, infer solvent loss, or authorize scientific release.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

from engine.calibration.hashing import stable_json_hash
from engine.physics.properties import UncertaintyDescriptor


class MatrixEnvironmentContractError(ValueError):
    """A malformed or tampered Build C2 contract."""


class MatrixStage(str, Enum):
    STOCK_SOLUTION = "STOCK_SOLUTION"
    CONCENTRATE = "CONCENTRATE"
    FINISHED_PERFUME = "FINISHED_PERFUME"
    APPLICATION_FILM = "APPLICATION_FILM"
    SAMPLED_HEADSPACE = "SAMPLED_HEADSPACE"


class MatrixComponentRole(str, Enum):
    ETHANOL = "ETHANOL"
    WATER = "WATER"
    DPG = "DPG"
    DEP = "DEP"
    TEC = "TEC"
    IPM = "IPM"
    OTHER_CARRIER = "OTHER_CARRIER"
    ACTIVE_FRAGRANCE = "ACTIVE_FRAGRANCE"
    DISSOLVED_SOLID = "DISSOLVED_SOLID"
    OTHER_PRODUCT_PHASE = "OTHER_PRODUCT_PHASE"


class MatrixQuantityBasis(str, Enum):
    MASS_FRACTION = "MASS_FRACTION"
    VOLUME_FRACTION = "VOLUME_FRACTION"
    MOLE_FRACTION = "MOLE_FRACTION"
    MASS = "MASS"
    VOLUME = "VOLUME"
    AMOUNT = "AMOUNT"


class CompositionCompleteness(str, Enum):
    EXACT = "EXACT"
    PARTIAL = "PARTIAL"
    UNRESOLVED = "UNRESOLVED"


class MatrixMissingField(str, Enum):
    COMPONENT_COMPOSITION = "component_composition"
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    RELATIVE_HUMIDITY = "relative_humidity"
    TOTAL_MASS = "total_mass"
    TOTAL_VOLUME = "total_volume"


_FRACTION_BASES = {
    MatrixQuantityBasis.MASS_FRACTION,
    MatrixQuantityBasis.VOLUME_FRACTION,
    MatrixQuantityBasis.MOLE_FRACTION,
}
_EnumT = TypeVar("_EnumT", bound=Enum)


def _mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MatrixEnvironmentContractError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise MatrixEnvironmentContractError(f"{field_name} keys must be strings")
    return dict(value)


def _exact_keys(
    payload: Mapping[str, Any],
    expected: set[str],
    field_name: str,
) -> None:
    actual = set(payload)
    missing = expected - actual
    unknown = actual - expected
    if missing:
        raise MatrixEnvironmentContractError(
            f"{field_name} missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise MatrixEnvironmentContractError(
            f"{field_name} contains unknown fields: {', '.join(sorted(unknown))}"
        )


def _nonblank(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MatrixEnvironmentContractError(f"{field_name} must not be blank")
    return value.strip()


def _finite(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise MatrixEnvironmentContractError(f"{field_name} must be finite")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise MatrixEnvironmentContractError(f"{field_name} must be finite") from exc
    if not math.isfinite(normalized):
        raise MatrixEnvironmentContractError(f"{field_name} must be finite")
    return normalized


def _enum_from_value(
    enum_type: type[_EnumT],
    value: object,
    field_name: str,
) -> _EnumT:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise MatrixEnvironmentContractError(f"{field_name} is not a supported value") from exc


def _sha256(value: object, field_name: str) -> str:
    normalized = _nonblank(value, field_name)
    if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
        raise MatrixEnvironmentContractError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized


def _uncertainty_mapping(value: UncertaintyDescriptor) -> dict[str, Any]:
    if not isinstance(value, UncertaintyDescriptor):
        raise MatrixEnvironmentContractError("uncertainty must be an UncertaintyDescriptor")
    return value.payload.to_mapping()


def _optional_quantity_mapping(
    value: DeclaredQuantity | None,
) -> dict[str, object] | None:
    return None if value is None else value.to_mapping()


def _optional_quantity_from_mapping(
    value: object,
    field_name: str,
) -> DeclaredQuantity | None:
    if value is None:
        return None
    return DeclaredQuantity.from_mapping(_mapping(value, field_name))


@dataclass(frozen=True, slots=True)
class DeclaredQuantity:
    """A finite declared value with an explicit unit and no conversion."""

    value: float
    unit: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _finite(self.value, "value"))
        object.__setattr__(self, "unit", _nonblank(self.unit, "unit"))

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> DeclaredQuantity:
        normalized = _mapping(payload, "declared quantity")
        _exact_keys(
            normalized,
            {"schema", "value", "unit"},
            "declared quantity",
        )
        if normalized["schema"] != "c2-declared-quantity-v1":
            raise MatrixEnvironmentContractError(
                "declared quantity schema must be c2-declared-quantity-v1"
            )
        return cls(value=normalized["value"], unit=normalized["unit"])

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema": "c2-declared-quantity-v1",
            "value": self.value,
            "unit": self.unit,
        }


@dataclass(frozen=True, slots=True)
class MatrixComponent:
    """One explicitly identified component and its declared quantity basis."""

    component_id: str
    name: str
    role: MatrixComponentRole
    basis: MatrixQuantityBasis
    quantity: DeclaredQuantity
    source_reference: str
    uncertainty: UncertaintyDescriptor
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "component_id",
            _nonblank(self.component_id, "component_id"),
        )
        object.__setattr__(self, "name", _nonblank(self.name, "name"))
        object.__setattr__(
            self,
            "source_reference",
            _nonblank(self.source_reference, "source_reference"),
        )
        if not isinstance(self.role, MatrixComponentRole):
            raise MatrixEnvironmentContractError("role must be a MatrixComponentRole")
        if not isinstance(self.basis, MatrixQuantityBasis):
            raise MatrixEnvironmentContractError("basis must be a MatrixQuantityBasis")
        if not isinstance(self.quantity, DeclaredQuantity):
            raise MatrixEnvironmentContractError("quantity must be a DeclaredQuantity")
        _uncertainty_mapping(self.uncertainty)
        if self.basis in _FRACTION_BASES:
            if self.quantity.unit != "1":
                raise MatrixEnvironmentContractError("fraction quantities must use unit 1")
            if not 0.0 <= self.quantity.value <= 1.0:
                raise MatrixEnvironmentContractError("fraction quantity must be between 0 and 1")
        elif self.quantity.value < 0.0:
            raise MatrixEnvironmentContractError("absolute component quantity must be non-negative")
        object.__setattr__(
            self,
            "content_sha256",
            stable_json_hash(self._content_mapping()),
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c2-matrix-component-v1",
            "component_id": self.component_id,
            "name": self.name,
            "role": self.role.value,
            "basis": self.basis.value,
            "quantity": self.quantity.to_mapping(),
            "source_reference": self.source_reference,
            "uncertainty": _uncertainty_mapping(self.uncertainty),
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> MatrixComponent:
        normalized = _mapping(payload, "matrix component")
        _exact_keys(
            normalized,
            {
                "schema",
                "component_id",
                "name",
                "role",
                "basis",
                "quantity",
                "source_reference",
                "uncertainty",
                "content_sha256",
            },
            "matrix component",
        )
        if normalized["schema"] != "c2-matrix-component-v1":
            raise MatrixEnvironmentContractError(
                "matrix component schema must be c2-matrix-component-v1"
            )
        try:
            uncertainty = UncertaintyDescriptor.from_mapping(
                _mapping(normalized["uncertainty"], "uncertainty")
            )
        except ValueError as exc:
            raise MatrixEnvironmentContractError(str(exc)) from exc
        component = cls(
            component_id=normalized["component_id"],
            name=normalized["name"],
            role=_enum_from_value(
                MatrixComponentRole,
                normalized["role"],
                "role",
            ),
            basis=_enum_from_value(
                MatrixQuantityBasis,
                normalized["basis"],
                "basis",
            ),
            quantity=DeclaredQuantity.from_mapping(_mapping(normalized["quantity"], "quantity")),
            source_reference=normalized["source_reference"],
            uncertainty=uncertainty,
        )
        expected_hash = _sha256(normalized["content_sha256"], "content_sha256")
        if expected_hash != component.content_sha256:
            raise MatrixEnvironmentContractError(
                "matrix component content_sha256 does not match canonical content"
            )
        return component


@dataclass(frozen=True, slots=True)
class MatrixComposition:
    """One versioned matrix snapshot with explicit completeness and conditions."""

    matrix_id: str
    matrix_version: str
    stage: MatrixStage
    components: tuple[MatrixComponent, ...]
    temperature: DeclaredQuantity | None
    pressure: DeclaredQuantity | None
    relative_humidity: DeclaredQuantity | None
    gas_comparison: bool
    total_mass: DeclaredQuantity | None
    total_volume: DeclaredQuantity | None
    uncertainty: UncertaintyDescriptor
    phase_assumptions: tuple[str, ...]
    completeness: CompositionCompleteness
    missing_fields: tuple[MatrixMissingField, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "matrix_id",
            _nonblank(self.matrix_id, "matrix_id"),
        )
        object.__setattr__(
            self,
            "matrix_version",
            _nonblank(self.matrix_version, "matrix_version"),
        )
        if not isinstance(self.stage, MatrixStage):
            raise MatrixEnvironmentContractError("stage must be a MatrixStage")
        components = tuple(self.components)
        if not components:
            raise MatrixEnvironmentContractError("components must not be empty")
        if any(not isinstance(item, MatrixComponent) for item in components):
            raise MatrixEnvironmentContractError("components must contain MatrixComponent values")
        components = tuple(
            sorted(
                components,
                key=lambda item: (item.component_id.casefold(), item.component_id),
            )
        )
        component_keys = [item.component_id.casefold() for item in components]
        if len(component_keys) != len(set(component_keys)):
            raise MatrixEnvironmentContractError("component IDs must be unique case-insensitively")
        object.__setattr__(self, "components", components)

        for field_name in (
            "temperature",
            "pressure",
            "relative_humidity",
            "total_mass",
            "total_volume",
        ):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, DeclaredQuantity):
                raise MatrixEnvironmentContractError(
                    f"{field_name} must be a DeclaredQuantity or null"
                )
        if not isinstance(self.gas_comparison, bool):
            raise MatrixEnvironmentContractError("gas_comparison must be boolean")
        if self.pressure is not None and self.pressure.value <= 0.0:
            raise MatrixEnvironmentContractError("pressure must be greater than zero")
        for field_name in ("total_mass", "total_volume"):
            value = getattr(self, field_name)
            if value is not None and value.value < 0.0:
                raise MatrixEnvironmentContractError(f"{field_name} must be non-negative")
        if self.relative_humidity is not None:
            _validate_relative_humidity(self.relative_humidity)
        _uncertainty_mapping(self.uncertainty)

        if not isinstance(self.completeness, CompositionCompleteness):
            raise MatrixEnvironmentContractError("completeness must be a CompositionCompleteness")
        missing_fields = tuple(self.missing_fields)
        if any(not isinstance(item, MatrixMissingField) for item in missing_fields):
            raise MatrixEnvironmentContractError(
                "missing_fields must contain MatrixMissingField values"
            )
        if len(missing_fields) != len(set(missing_fields)):
            raise MatrixEnvironmentContractError("missing_fields must not contain duplicates")
        missing_fields = tuple(sorted(missing_fields, key=lambda item: item.value))
        object.__setattr__(self, "missing_fields", missing_fields)

        raw_assumptions = tuple(self.phase_assumptions)
        if not raw_assumptions:
            raise MatrixEnvironmentContractError("phase_assumptions must not be empty")
        assumptions = tuple(
            sorted(
                (_nonblank(item, "phase_assumptions") for item in raw_assumptions),
                key=str.casefold,
            )
        )
        if len(assumptions) != len({item.casefold() for item in assumptions}):
            raise MatrixEnvironmentContractError("phase_assumptions must be unique")
        object.__setattr__(self, "phase_assumptions", assumptions)

        self._validate_completeness()
        self._validate_fraction_closure()
        object.__setattr__(
            self,
            "content_sha256",
            stable_json_hash(self._content_mapping()),
        )

    def _validate_completeness(self) -> None:
        missing = set(self.missing_fields)
        if self.completeness is CompositionCompleteness.EXACT:
            if missing:
                raise MatrixEnvironmentContractError("EXACT matrix missing_fields must be empty")
        elif not missing:
            raise MatrixEnvironmentContractError(
                "PARTIAL or UNRESOLVED matrix missing_fields must not be empty"
            )

        required_values = {
            MatrixMissingField.TEMPERATURE: self.temperature,
            MatrixMissingField.PRESSURE: self.pressure,
            MatrixMissingField.TOTAL_MASS: self.total_mass,
            MatrixMissingField.TOTAL_VOLUME: self.total_volume,
        }
        for missing_field, value in required_values.items():
            if value is None and missing_field not in missing:
                raise MatrixEnvironmentContractError(
                    f"{missing_field.value} is absent but not declared missing"
                )
            if value is not None and missing_field in missing:
                raise MatrixEnvironmentContractError(
                    f"{missing_field.value} has a value and cannot be declared missing"
                )

        humidity_missing = MatrixMissingField.RELATIVE_HUMIDITY in missing
        if self.gas_comparison:
            if self.relative_humidity is None and not humidity_missing:
                raise MatrixEnvironmentContractError(
                    "relative_humidity is required for gas comparison"
                )
            if self.relative_humidity is not None and humidity_missing:
                raise MatrixEnvironmentContractError(
                    "relative_humidity has a value and cannot be declared missing"
                )
        elif humidity_missing:
            raise MatrixEnvironmentContractError(
                "relative_humidity cannot be declared missing when gas_comparison is false"
            )

    def _validate_fraction_closure(self) -> None:
        if MatrixMissingField.COMPONENT_COMPOSITION in self.missing_fields:
            return
        bases = {item.basis for item in self.components}
        if len(bases) != 1 or next(iter(bases)) not in _FRACTION_BASES:
            return
        total = sum(item.quantity.value for item in self.components)
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise MatrixEnvironmentContractError(
                "fraction components must sum to 1 without normalization"
            )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c2-matrix-composition-v1",
            "matrix_id": self.matrix_id,
            "matrix_version": self.matrix_version,
            "stage": self.stage.value,
            "components": [item.to_mapping() for item in self.components],
            "temperature": _optional_quantity_mapping(self.temperature),
            "pressure": _optional_quantity_mapping(self.pressure),
            "relative_humidity": _optional_quantity_mapping(self.relative_humidity),
            "gas_comparison": self.gas_comparison,
            "total_mass": _optional_quantity_mapping(self.total_mass),
            "total_volume": _optional_quantity_mapping(self.total_volume),
            "uncertainty": _uncertainty_mapping(self.uncertainty),
            "phase_assumptions": list(self.phase_assumptions),
            "completeness": self.completeness.value,
            "missing_fields": [item.value for item in self.missing_fields],
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> MatrixComposition:
        normalized = _mapping(payload, "matrix composition")
        _exact_keys(
            normalized,
            {
                "schema",
                "matrix_id",
                "matrix_version",
                "stage",
                "components",
                "temperature",
                "pressure",
                "relative_humidity",
                "gas_comparison",
                "total_mass",
                "total_volume",
                "uncertainty",
                "phase_assumptions",
                "completeness",
                "missing_fields",
                "content_sha256",
            },
            "matrix composition",
        )
        if normalized["schema"] != "c2-matrix-composition-v1":
            raise MatrixEnvironmentContractError(
                "matrix composition schema must be c2-matrix-composition-v1"
            )
        raw_components = normalized["components"]
        if not isinstance(raw_components, (list, tuple)):
            raise MatrixEnvironmentContractError("components must be a list")
        raw_assumptions = normalized["phase_assumptions"]
        if not isinstance(raw_assumptions, (list, tuple)):
            raise MatrixEnvironmentContractError("phase_assumptions must be a list")
        raw_missing = normalized["missing_fields"]
        if not isinstance(raw_missing, (list, tuple)):
            raise MatrixEnvironmentContractError("missing_fields must be a list")
        try:
            uncertainty = UncertaintyDescriptor.from_mapping(
                _mapping(normalized["uncertainty"], "uncertainty")
            )
        except ValueError as exc:
            raise MatrixEnvironmentContractError(str(exc)) from exc
        matrix = cls(
            matrix_id=normalized["matrix_id"],
            matrix_version=normalized["matrix_version"],
            stage=_enum_from_value(MatrixStage, normalized["stage"], "stage"),
            components=tuple(
                MatrixComponent.from_mapping(_mapping(item, "component")) for item in raw_components
            ),
            temperature=_optional_quantity_from_mapping(normalized["temperature"], "temperature"),
            pressure=_optional_quantity_from_mapping(normalized["pressure"], "pressure"),
            relative_humidity=_optional_quantity_from_mapping(
                normalized["relative_humidity"],
                "relative_humidity",
            ),
            gas_comparison=normalized["gas_comparison"],
            total_mass=_optional_quantity_from_mapping(normalized["total_mass"], "total_mass"),
            total_volume=_optional_quantity_from_mapping(
                normalized["total_volume"], "total_volume"
            ),
            uncertainty=uncertainty,
            phase_assumptions=tuple(raw_assumptions),
            completeness=_enum_from_value(
                CompositionCompleteness,
                normalized["completeness"],
                "completeness",
            ),
            missing_fields=tuple(
                _enum_from_value(MatrixMissingField, item, "missing_fields") for item in raw_missing
            ),
        )
        expected_hash = _sha256(normalized["content_sha256"], "content_sha256")
        if expected_hash != matrix.content_sha256:
            raise MatrixEnvironmentContractError(
                "matrix composition content_sha256 does not match canonical content"
            )
        return matrix


def _validate_relative_humidity(quantity: DeclaredQuantity) -> None:
    if quantity.value < 0.0:
        raise MatrixEnvironmentContractError("relative_humidity must be non-negative")
    if quantity.unit == "%" and quantity.value > 100.0:
        raise MatrixEnvironmentContractError("relative_humidity percent must not exceed 100")
    if quantity.unit == "1" and quantity.value > 1.0:
        raise MatrixEnvironmentContractError("relative_humidity fraction must not exceed 1")


__all__ = [
    "CompositionCompleteness",
    "DeclaredQuantity",
    "MatrixComponent",
    "MatrixComponentRole",
    "MatrixComposition",
    "MatrixEnvironmentContractError",
    "MatrixMissingField",
    "MatrixQuantityBasis",
    "MatrixStage",
]
