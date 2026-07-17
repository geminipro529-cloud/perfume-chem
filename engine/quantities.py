"""Strict scalar quantities used at application boundaries.

The engine stores canonical units and names the concentration basis explicitly.
This prevents a bare ``ppm`` value from being interpreted as mass, volume, or
gas amount fraction depending on the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite


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


__all__ = [
    "Concentration",
    "ConcentrationBasis",
    "Density",
    "Duration",
    "LiquidMassConcentration",
    "Mass",
    "MolarMass",
    "OdorActivityValue",
    "OdorThreshold",
    "QuantityError",
    "StandardUncertainty",
    "Temperature",
    "VaporPressure",
    "Volume",
]
