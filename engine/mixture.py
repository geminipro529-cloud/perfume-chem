"""Solvent-inclusive finished-mixture arithmetic without physical fallbacks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from engine.quantities import Density, Mass, MolarMass, Volume


class MixtureRole(str, Enum):
    """A component's role in the finished liquid."""

    ODORANT = "odorant"
    SOLVENT = "solvent"


@dataclass(frozen=True, slots=True)
class SolventPhysicalData:
    """Versioned built-in physical data for common finished-product solvents."""

    density: Density
    molar_mass: MolarMass
    temperature_k: float
    source: str


_KNOWN_SOLVENTS = {
    "ethanol": SolventPhysicalData(
        density=Density.from_g_ml(0.785),
        molar_mass=MolarMass.from_g_mol(46.0684),
        temperature_k=298.15,
        source="NIST Chemistry WebBook CAS 64-17-5; density rounded at 25 C",
    ),
    "ethyl alcohol": SolventPhysicalData(
        density=Density.from_g_ml(0.785),
        molar_mass=MolarMass.from_g_mol(46.0684),
        temperature_k=298.15,
        source="NIST Chemistry WebBook CAS 64-17-5; density rounded at 25 C",
    ),
    "water": SolventPhysicalData(
        density=Density.from_g_ml(0.9970),
        molar_mass=MolarMass.from_g_mol(18.01528),
        temperature_k=298.15,
        source="NIST Chemistry WebBook CAS 7732-18-5; density rounded at 25 C",
    ),
}


def known_solvent_physical_data(name: str) -> SolventPhysicalData | None:
    """Return built-in solvent data without guessing unknown identities."""

    return _KNOWN_SOLVENTS.get(name.strip().casefold())


@dataclass(frozen=True, slots=True)
class MixtureComponent:
    """One pure component amount in a finished mixture."""

    name: str
    role: MixtureRole
    volume: Volume
    density: Density | None
    molar_mass: MolarMass | None
    source: str = "user_supplied"
    density_source: str = "user_supplied"
    molar_mass_source: str = "user_supplied"

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("mixture component name must not be empty")
        if self.volume.ul <= 0:
            raise ValueError("mixture component volume must be greater than zero")
        object.__setattr__(self, "name", name)
        source = self.source.strip()
        if not source:
            raise ValueError("mixture component source must not be empty")
        object.__setattr__(self, "source", source)
        for field_name in ("density_source", "molar_mass_source"):
            field_value = getattr(self, field_name).strip()
            if not field_value:
                raise ValueError(f"mixture component {field_name} must not be empty")
            object.__setattr__(self, field_name, field_value)


@dataclass(frozen=True, slots=True)
class MixtureComponentState:
    """Calculated state for one component."""

    component: MixtureComponent
    mass: Mass | None
    moles: float | None
    mass_fraction_ppm: float | None
    amount_fraction: float | None

    @property
    def name(self) -> str:
        return self.component.name

    @property
    def role(self) -> MixtureRole:
        return self.component.role

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "role": self.role.value,
            "raw_volume_ul": self.component.volume.ul,
            "density_g_ml": (
                self.component.density.g_ml if self.component.density is not None else None
            ),
            "molar_mass_g_mol": (
                self.component.molar_mass.g_mol
                if self.component.molar_mass is not None
                else None
            ),
            "mass_g": self.mass.g if self.mass is not None else None,
            "moles": self.moles,
            "matrix_mass_fraction_ppm": self.mass_fraction_ppm,
            "amount_fraction": self.amount_fraction,
            "source": self.component.source,
            "density_source": self.component.density_source,
            "molar_mass_source": self.component.molar_mass_source,
        }


@dataclass(frozen=True, slots=True)
class MixtureState:
    """Exact finished-mixture totals when every required input is supplied."""

    components: tuple[MixtureComponentState, ...]
    total_volume: Volume
    total_mass: Mass | None
    total_moles: float | None
    complete: bool
    missing_inputs: tuple[str, ...]

    @classmethod
    def from_components(cls, components: tuple[MixtureComponent, ...]) -> MixtureState:
        if not components:
            raise ValueError("mixture must contain at least one component")

        normalized_names = [component.name.casefold() for component in components]
        if len(normalized_names) != len(set(normalized_names)):
            raise ValueError("mixture component names must be unique")

        total_volume = Volume.from_ul(sum(component.volume.ul for component in components))
        missing: list[str] = []
        masses: dict[str, Mass | None] = {}
        moles_by_name: dict[str, float | None] = {}
        for component in components:
            if component.density is None:
                missing.append(f"{component.name}.density_g_ml")
            if component.molar_mass is None:
                missing.append(f"{component.name}.molar_mass_g_mol")

            mass = (
                Mass.from_g(component.volume.ml * component.density.g_ml)
                if component.density is not None
                else None
            )
            masses[component.name] = mass
            moles_by_name[component.name] = (
                mass.g / component.molar_mass.g_mol
                if mass is not None and component.molar_mass is not None
                else None
            )

        complete = not missing
        total_mass = (
            Mass.from_g(sum(mass.g for mass in masses.values() if mass is not None))
            if complete
            else None
        )
        total_moles = (
            sum(moles for moles in moles_by_name.values() if moles is not None)
            if complete
            else None
        )

        states: list[MixtureComponentState] = []
        for component in components:
            mass = masses[component.name]
            moles = moles_by_name[component.name]
            states.append(
                MixtureComponentState(
                    component=component,
                    mass=mass,
                    moles=moles,
                    mass_fraction_ppm=(
                        1_000_000.0 * mass.g / total_mass.g
                        if complete and mass is not None and total_mass is not None
                        else None
                    ),
                    amount_fraction=(
                        moles / total_moles
                        if complete and moles is not None and total_moles
                        else None
                    ),
                )
            )

        return cls(
            components=tuple(states),
            total_volume=total_volume,
            total_mass=total_mass,
            total_moles=total_moles,
            complete=complete,
            missing_inputs=tuple(missing),
        )

    def component(self, name: str) -> MixtureComponentState:
        normalized = name.strip().casefold()
        for component in self.components:
            if component.name.casefold() == normalized:
                return component
        raise KeyError(name)

    def as_dict(self) -> dict[str, object]:
        return {
            "complete": self.complete,
            "total_volume_ul": self.total_volume.ul,
            "total_mass_g": self.total_mass.g if self.total_mass is not None else None,
            "total_moles": self.total_moles,
            "missing_inputs": list(self.missing_inputs),
            "components": [component.as_dict() for component in self.components],
        }


__all__ = [
    "MixtureComponent",
    "MixtureComponentState",
    "MixtureRole",
    "MixtureState",
    "SolventPhysicalData",
    "known_solvent_physical_data",
]
