"""Strict scalar quantities used at application boundaries.

The engine stores canonical units and names the concentration basis explicitly.
This prevents a bare ``ppm`` value from being interpreted as mass, volume, or
gas amount fraction depending on the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Generic, Mapping, TypeVar


class QuantityError(ValueError):
    """Raised when a physical quantity is invalid or incompatible."""


def _finite(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise QuantityError(f"{name} must be finite")
    return value


def _nonnegative(name: str, value: float) -> float:
    value = _finite(name, value)
    if value < 0:
        raise QuantityError(f"{name} must be nonnegative")
    return value


def _positive(name: str, value: float) -> float:
    value = _finite(name, value)
    if value <= 0:
        raise QuantityError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True, slots=True)
class Volume:
    """Volume stored canonically in microlitres."""

    ul: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "ul", _nonnegative("volume_ul", self.ul))

    @classmethod
    def from_ul(cls, value: float) -> Volume:
        return cls(value)

    @classmethod
    def from_ml(cls, value: float) -> Volume:
        return cls(_nonnegative("volume_ml", value) * 1000.0)

    @property
    def ml(self) -> float:
        return self.ul / 1000.0


@dataclass(frozen=True, slots=True)
class Mass:
    """Mass stored canonically in grams."""

    g: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "g", _nonnegative("mass_g", self.g))

    @classmethod
    def from_g(cls, value: float) -> Mass:
        return cls(value)

    @classmethod
    def from_mg(cls, value: float) -> Mass:
        return cls(_nonnegative("mass_mg", value) / 1000.0)


@dataclass(frozen=True, slots=True)
class Density:
    """Mass density stored in grams per millilitre."""

    g_ml: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "g_ml", _positive("density_g_ml", self.g_ml))

    @classmethod
    def from_g_ml(cls, value: float) -> Density:
        return cls(value)


@dataclass(frozen=True, slots=True)
class LiquidMassConcentration:
    """Constituent mass per mixture volume, stored canonically in g/L."""

    g_l: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "g_l",
            _nonnegative("liquid_mass_concentration_g_l", self.g_l),
        )

    @classmethod
    def from_g_l(cls, value: float) -> LiquidMassConcentration:
        return cls(value)

    @classmethod
    def from_mg_l(cls, value: float) -> LiquidMassConcentration:
        return cls(_nonnegative("liquid_mass_concentration_mg_l", value) / 1000.0)

    @property
    def mg_l(self) -> float:
        return self.g_l * 1000.0


@dataclass(frozen=True, slots=True)
class Temperature:
    """Thermodynamic temperature stored in kelvin."""

    kelvin: float

    def __post_init__(self) -> None:
        value = _finite("temperature_kelvin", self.kelvin)
        if value < 0:
            raise QuantityError("temperature cannot be below absolute zero")
        object.__setattr__(self, "kelvin", value)

    @classmethod
    def from_kelvin(cls, value: float) -> Temperature:
        return cls(value)

    @classmethod
    def from_celsius(cls, value: float) -> Temperature:
        return cls(_finite("temperature_celsius", value) + 273.15)

    @property
    def celsius(self) -> float:
        return self.kelvin - 273.15


@dataclass(frozen=True, slots=True)
class Duration:
    """Duration stored in seconds."""

    seconds: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "seconds", _nonnegative("duration_seconds", self.seconds))

    @classmethod
    def from_seconds(cls, value: float) -> Duration:
        return cls(value)


@dataclass(frozen=True, slots=True)
class MolarMass:
    """Molar mass stored in grams per mole."""

    g_mol: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "g_mol", _positive("molar_mass_g_mol", self.g_mol))

    @classmethod
    def from_g_mol(cls, value: float) -> MolarMass:
        return cls(value)


@dataclass(frozen=True, slots=True)
class VaporPressure:
    """Vapor pressure stored in pascals."""

    pa: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "pa", _nonnegative("vapor_pressure_pa", self.pa))

    @classmethod
    def from_pa(cls, value: float) -> VaporPressure:
        return cls(value)


class ConcentrationBasis(str, Enum):
    """The physical fraction represented by a dimensionless concentration."""

    MASS_FRACTION = "mass_fraction"
    VOLUME_FRACTION = "volume_fraction"
    AMOUNT_FRACTION = "amount_fraction"
    GAS_AMOUNT_FRACTION = "gas_amount_fraction"


@dataclass(frozen=True, slots=True)
class Concentration:
    """Dimensionless concentration with an explicit fraction basis and medium."""

    fraction: float
    basis: ConcentrationBasis
    medium: str

    def __post_init__(self) -> None:
        value = _nonnegative("concentration_fraction", self.fraction)
        if value > 1:
            raise QuantityError("concentration_fraction must be at most one")
        medium = self.medium.strip()
        if not medium:
            raise QuantityError("concentration medium must not be empty")
        try:
            basis = ConcentrationBasis(self.basis)
        except ValueError as exc:
            raise QuantityError("concentration basis is not recognized") from exc
        object.__setattr__(self, "fraction", value)
        object.__setattr__(self, "basis", basis)
        object.__setattr__(self, "medium", medium)

    @classmethod
    def from_ppm(
        cls,
        value: float,
        *,
        basis: ConcentrationBasis,
        medium: str,
    ) -> Concentration:
        return cls(_nonnegative("concentration_ppm", value) / 1_000_000.0, basis, medium)

    @property
    def ppm(self) -> float:
        return self.fraction * 1_000_000.0


@dataclass(frozen=True, slots=True)
class OdorThreshold:
    """Detection threshold represented by a fully qualified concentration."""

    concentration: Concentration

    def __post_init__(self) -> None:
        if self.concentration.fraction <= 0:
            raise QuantityError("odor threshold must be greater than zero")

    @classmethod
    def from_ppm(
        cls,
        value: float,
        *,
        basis: ConcentrationBasis,
        medium: str,
    ) -> OdorThreshold:
        return cls(Concentration.from_ppm(value, basis=basis, medium=medium))

    @property
    def ppm(self) -> float:
        return self.concentration.ppm


@dataclass(frozen=True, slots=True)
class OdorActivityValue:
    """Dimensionless concentration-to-threshold screening ratio."""

    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _nonnegative("oav", self.value))

    @classmethod
    def from_ratio(
        cls,
        concentration: Concentration,
        threshold: OdorThreshold,
    ) -> OdorActivityValue:
        threshold_concentration = threshold.concentration
        if (
            concentration.basis is not threshold_concentration.basis
            or concentration.medium != threshold_concentration.medium
        ):
            raise QuantityError("OAV concentration and threshold basis and medium must match")
        return cls(concentration.fraction / threshold_concentration.fraction)


@dataclass(frozen=True, slots=True)
class StandardUncertainty:
    """A measured value with a declared standard uncertainty and unit."""

    value: float
    standard_uncertainty: float
    unit: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _finite("measurement value", self.value))
        object.__setattr__(
            self,
            "standard_uncertainty",
            _nonnegative("standard_uncertainty", self.standard_uncertainty),
        )
        unit = self.unit.strip()
        if not unit:
            raise QuantityError("measurement unit must not be empty")
        object.__setattr__(self, "unit", unit)

    def as_dict(self) -> dict[str, float | str]:
        return {
            "value": self.value,
            "standard_uncertainty": self.standard_uncertainty,
            "unit": self.unit,
        }


class IncomparabilityReason(str, Enum):
    """Stable fail-closed reason codes for unsafe quantity comparisons."""

    MISSING_DENSITY = "MISSING_DENSITY"
    DENSITY_OUTSIDE_VALID_RANGE = "DENSITY_OUTSIDE_VALID_RANGE"
    UNSPECIFIED_CONCENTRATION_BASIS = "UNSPECIFIED_CONCENTRATION_BASIS"
    MISSING_ACTIVE_FRACTION = "MISSING_ACTIVE_FRACTION"
    UNIT_NOT_CONVERTIBLE = "UNIT_NOT_CONVERTIBLE"
    UNKNOWN_DILUENT = "UNKNOWN_DILUENT"
    UNCERTAINTY_TOO_LARGE = "UNCERTAINTY_TOO_LARGE"


@dataclass(frozen=True, slots=True)
class DensityConditions:
    """Temperature applicability range for a measured density."""

    measured_temperature_c: float
    minimum_temperature_c: float
    maximum_temperature_c: float

    def __post_init__(self) -> None:
        measured = _finite(
            "measured_temperature_c", self.measured_temperature_c
        )
        minimum = _finite(
            "minimum_temperature_c", self.minimum_temperature_c
        )
        maximum = _finite(
            "maximum_temperature_c", self.maximum_temperature_c
        )
        if minimum > maximum:
            raise QuantityError(
                "minimum density temperature must not exceed maximum"
            )
        if not minimum <= measured <= maximum:
            raise QuantityError(
                "measured density temperature is outside its valid range"
            )
        object.__setattr__(self, "measured_temperature_c", measured)
        object.__setattr__(self, "minimum_temperature_c", minimum)
        object.__setattr__(self, "maximum_temperature_c", maximum)


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ConversionResult(Generic[T]):
    """A value or one stable reason why conversion is not defensible."""

    value: T | None
    reason: IncomparabilityReason | None

    def __post_init__(self) -> None:
        if (self.value is None) == (self.reason is None):
            raise QuantityError(
                "conversion result requires exactly one of value or reason"
            )


@dataclass(frozen=True, slots=True)
class CompositionBalance:
    """Mass accounting for a supplied technical material or stock."""

    raw_mass_g: float
    technical_active_mass_g: float
    active_mass_g: float
    carrier_mass_g: float
    ethanol_mass_g: float
    water_mass_g: float
    other_solvent_mass_g: float
    unallocated_mass_g: float

    def __post_init__(self) -> None:
        for field_name in (
            "raw_mass_g",
            "technical_active_mass_g",
            "active_mass_g",
            "carrier_mass_g",
            "ethanol_mass_g",
            "water_mass_g",
            "other_solvent_mass_g",
            "unallocated_mass_g",
        ):
            object.__setattr__(
                self,
                field_name,
                _nonnegative(field_name, getattr(self, field_name)),
            )


@dataclass(frozen=True, slots=True)
class VolumeBalance:
    """Explicit raw, active, carrier, and solvent volume roles."""

    raw_volume: Volume
    active_volume: Volume
    carrier_volume: Volume
    solvent_volume: Volume


@dataclass(frozen=True, slots=True)
class MeasurementResolution:
    """Smallest reported increment for a measurement and its unit."""

    value: float
    unit: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", _positive("measurement resolution", self.value)
        )
        unit = str(self.unit).strip()
        if not unit:
            raise QuantityError("measurement resolution unit must not be empty")
        object.__setattr__(self, "unit", unit)


def convert_mass_to_volume(
    mass: Mass,
    *,
    density: Density | None,
    conditions: DensityConditions | None = None,
    requested_temperature_c: float | None = None,
) -> ConversionResult[Volume]:
    """Convert mass only when density exists and applies at the requested T."""

    if density is None:
        return ConversionResult(
            None, IncomparabilityReason.MISSING_DENSITY
        )
    if requested_temperature_c is not None:
        requested = _finite(
            "requested_temperature_c", requested_temperature_c
        )
        if conditions is not None and not (
            conditions.minimum_temperature_c
            <= requested
            <= conditions.maximum_temperature_c
        ):
            return ConversionResult(
                None,
                IncomparabilityReason.DENSITY_OUTSIDE_VALID_RANGE,
            )
    return ConversionResult(
        Volume.from_ml(mass.g / density.g_ml),
        None,
    )


def convert_raw_to_active_mass(
    raw_mass: Mass,
    *,
    active_fraction: float | None,
    basis: ConcentrationBasis | None,
    uncertainty: StandardUncertainty | None = None,
    maximum_relative_uncertainty: float = 0.5,
) -> ConversionResult[Mass]:
    """Convert supplied mass to active mass only for a supported mass basis."""

    if basis is None:
        return ConversionResult(
            None,
            IncomparabilityReason.UNSPECIFIED_CONCENTRATION_BASIS,
        )
    if active_fraction is None:
        return ConversionResult(
            None,
            IncomparabilityReason.MISSING_ACTIVE_FRACTION,
        )
    if basis is not ConcentrationBasis.MASS_FRACTION:
        return ConversionResult(
            None,
            IncomparabilityReason.UNIT_NOT_CONVERTIBLE,
        )
    fraction = _nonnegative("active_fraction", active_fraction)
    if fraction > 1:
        raise QuantityError("active_fraction must be at most one")
    maximum = _nonnegative(
        "maximum_relative_uncertainty", maximum_relative_uncertainty
    )
    if uncertainty is not None:
        if uncertainty.unit != "g":
            return ConversionResult(
                None,
                IncomparabilityReason.UNIT_NOT_CONVERTIBLE,
            )
        scale = abs(uncertainty.value)
        relative = (
            float("inf")
            if scale == 0 and uncertainty.standard_uncertainty > 0
            else uncertainty.standard_uncertainty / max(scale, 1.0e-300)
        )
        if relative > maximum:
            return ConversionResult(
                None,
                IncomparabilityReason.UNCERTAINTY_TOO_LARGE,
            )
    return ConversionResult(Mass.from_g(raw_mass.g * fraction), None)


def partition_raw_mass(
    raw_mass: Mass,
    *,
    active_fraction: float | None,
    basis: ConcentrationBasis | None,
    diluent_fractions: Mapping[str, float] | None,
    technical_active_fraction: float | None = None,
) -> ConversionResult[CompositionBalance]:
    """Partition raw stock into active material and named carrier classes."""

    active_result = convert_raw_to_active_mass(
        raw_mass,
        active_fraction=active_fraction,
        basis=basis,
    )
    if active_result.reason is not None:
        return ConversionResult(None, active_result.reason)
    if diluent_fractions is None:
        return ConversionResult(
            None,
            IncomparabilityReason.UNKNOWN_DILUENT,
        )
    active_mass = active_result.value
    if active_mass is None:  # pragma: no cover - ConversionResult invariant
        raise AssertionError("successful active conversion has no value")
    technical_fraction = (
        active_fraction
        if technical_active_fraction is None
        else technical_active_fraction
    )
    if technical_fraction is None:  # guarded by conversion above
        raise AssertionError("active fraction unexpectedly missing")
    technical_fraction = _nonnegative(
        "technical_active_fraction", technical_fraction
    )
    if technical_fraction > 1:
        raise QuantityError("technical_active_fraction must be at most one")
    carrier_mass = raw_mass.g - active_mass.g
    normalized: dict[str, float] = {}
    for raw_name, raw_fraction in diluent_fractions.items():
        name = str(raw_name).strip().casefold().replace("_", "-")
        fraction = _nonnegative(f"diluent fraction {name}", raw_fraction)
        normalized[name] = normalized.get(name, 0.0) + fraction
    allocated_fraction = sum(normalized.values())
    if allocated_fraction > 1 + 1.0e-12:
        raise QuantityError("diluent fractions must sum to at most one")
    ethanol_fraction = normalized.pop("ethanol", 0.0)
    water_fraction = normalized.pop("water", 0.0)
    explicit_other_fraction = normalized.pop("other-solvent", 0.0)
    other_fraction = explicit_other_fraction + sum(normalized.values())
    unallocated_fraction = max(
        0.0,
        1.0 - ethanol_fraction - water_fraction - other_fraction,
    )
    return ConversionResult(
        CompositionBalance(
            raw_mass_g=raw_mass.g,
            technical_active_mass_g=raw_mass.g * technical_fraction,
            active_mass_g=active_mass.g,
            carrier_mass_g=carrier_mass,
            ethanol_mass_g=carrier_mass * ethanol_fraction,
            water_mass_g=carrier_mass * water_fraction,
            other_solvent_mass_g=carrier_mass * other_fraction,
            unallocated_mass_g=carrier_mass * unallocated_fraction,
        ),
        None,
    )


__all__ = [
    "Concentration",
    "ConcentrationBasis",
    "CompositionBalance",
    "ConversionResult",
    "Density",
    "DensityConditions",
    "Duration",
    "IncomparabilityReason",
    "LiquidMassConcentration",
    "Mass",
    "MeasurementResolution",
    "MolarMass",
    "OdorActivityValue",
    "OdorThreshold",
    "QuantityError",
    "StandardUncertainty",
    "Temperature",
    "VaporPressure",
    "Volume",
    "VolumeBalance",
    "convert_mass_to_volume",
    "convert_raw_to_active_mass",
    "partition_raw_mass",
]
