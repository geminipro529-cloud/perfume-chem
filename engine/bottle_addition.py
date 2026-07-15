"""Exact additive mass balance with explicit measurement constraints."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, hypot, isfinite
from typing import Any

from engine.scientific_contract import EvidenceDescriptor, ScientificClass


class AdditionCalculationError(ValueError):
    """Raised when an addition request is physically or numerically invalid."""


def _require_finite(name: str, value: float) -> None:
    if not isfinite(value):
        raise AdditionCalculationError(f"{name} must be finite")


def _require_nonnegative(name: str, value: float) -> None:
    _require_finite(name, value)
    if value < 0:
        raise AdditionCalculationError(f"{name} must be nonnegative")


@dataclass(frozen=True, slots=True)
class BottleSnapshot:
    """Measured bottle state before a stock solution is added."""

    total_mass_g: float
    active_material_mass_g: float
    total_mass_standard_uncertainty_g: float = 0.0
    active_mass_standard_uncertainty_g: float = 0.0

    def __post_init__(self) -> None:
        _require_finite("total_mass_g", self.total_mass_g)
        if self.total_mass_g <= 0:
            raise AdditionCalculationError("total_mass_g must be greater than zero")
        _require_nonnegative("active_material_mass_g", self.active_material_mass_g)
        if self.active_material_mass_g > self.total_mass_g:
            raise AdditionCalculationError(
                "active_material_mass_g cannot exceed total_mass_g"
            )
        _require_nonnegative(
            "total_mass_standard_uncertainty_g",
            self.total_mass_standard_uncertainty_g,
        )
        _require_nonnegative(
            "active_mass_standard_uncertainty_g",
            self.active_mass_standard_uncertainty_g,
        )


@dataclass(frozen=True, slots=True)
class StockSolution:
    """Stock composition and optional measured density."""

    active_mass_fraction: float
    density_g_ml: float | None = None
    active_fraction_standard_uncertainty: float = 0.0
    density_standard_uncertainty_g_ml: float = 0.0

    def __post_init__(self) -> None:
        _require_finite("active_mass_fraction", self.active_mass_fraction)
        if not 0 < self.active_mass_fraction <= 1:
            raise AdditionCalculationError(
                "active_mass_fraction must be greater than zero and at most one"
            )
        if self.density_g_ml is not None:
            _require_finite("density_g_ml", self.density_g_ml)
            if self.density_g_ml <= 0:
                raise AdditionCalculationError("density_g_ml must be greater than zero")
        _require_nonnegative(
            "active_fraction_standard_uncertainty",
            self.active_fraction_standard_uncertainty,
        )
        _require_nonnegative(
            "density_standard_uncertainty_g_ml",
            self.density_standard_uncertainty_g_ml,
        )
        if self.density_g_ml is None and self.density_standard_uncertainty_g_ml:
            raise AdditionCalculationError(
                "density_standard_uncertainty_g_ml requires density_g_ml"
            )


@dataclass(frozen=True, slots=True)
class PipetteProfile:
    """Declared delivery range and resolution for a pipette."""

    minimum_ul: float
    increment_ul: float
    maximum_single_step_ul: float | None = None
    standard_uncertainty_ul: float = 0.0

    def __post_init__(self) -> None:
        _require_finite("minimum_ul", self.minimum_ul)
        if self.minimum_ul <= 0:
            raise AdditionCalculationError("minimum_ul must be greater than zero")
        _require_finite("increment_ul", self.increment_ul)
        if self.increment_ul <= 0:
            raise AdditionCalculationError("increment_ul must be greater than zero")
        if self.maximum_single_step_ul is not None:
            _require_finite(
                "maximum_single_step_ul", self.maximum_single_step_ul
            )
            if self.maximum_single_step_ul < self.minimum_ul:
                raise AdditionCalculationError(
                    "maximum_single_step_ul must be at least minimum_ul"
                )
        _require_nonnegative("standard_uncertainty_ul", self.standard_uncertainty_ul)


@dataclass(frozen=True, slots=True)
class AdditionRequest:
    """Target for an additive bottle correction."""

    bottle: BottleSnapshot
    stock: StockSolution
    target_active_mass_fraction: float
    pipette: PipetteProfile | None = None

    def __post_init__(self) -> None:
        _require_nonnegative(
            "target_active_mass_fraction", self.target_active_mass_fraction
        )


@dataclass(frozen=True, slots=True)
class AdditionResult:
    """Calculated addition and, when possible, a rounded delivery plan."""

    exact_stock_mass_g: float
    exact_stock_mass_standard_uncertainty_g: float
    exact_stock_volume_ul: float | None
    exact_stock_volume_standard_uncertainty_ul: float | None
    rounded_stock_volume_ul: float | None
    rounded_stock_mass_g: float | None
    resulting_active_mass_fraction: float
    target_error_ppm: float
    pipette_feasible: bool
    staged_additions_ul: tuple[float, ...]
    pipette_standard_uncertainty_ul: float | None
    mass_ledger: dict[str, Any]
    evidence: EvidenceDescriptor
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "exact_stock_mass_g": self.exact_stock_mass_g,
            "exact_stock_mass_standard_uncertainty_g": (
                self.exact_stock_mass_standard_uncertainty_g
            ),
            "exact_stock_volume_ul": self.exact_stock_volume_ul,
            "exact_stock_volume_standard_uncertainty_ul": (
                self.exact_stock_volume_standard_uncertainty_ul
            ),
            "rounded_stock_volume_ul": self.rounded_stock_volume_ul,
            "rounded_stock_mass_g": self.rounded_stock_mass_g,
            "resulting_active_mass_fraction": self.resulting_active_mass_fraction,
            "target_error_ppm": self.target_error_ppm,
            "pipette_feasible": self.pipette_feasible,
            "staged_additions_ul": list(self.staged_additions_ul),
            "pipette_standard_uncertainty_ul": self.pipette_standard_uncertainty_ul,
            "mass_ledger": self.mass_ledger,
            "evidence": self.evidence.as_dict(),
            "warnings": list(self.warnings),
        }


class AdditionSolver:
    """Solve one-stock additions without silently inventing physical data."""

    _EVIDENCE = EvidenceDescriptor(
        classification=ScientificClass.EXACT,
        basis=(
            "closed-form conservation of total mass and active-material mass; "
            "standard uncertainty propagated by first-order sensitivity coefficients"
        ),
        sources=(
            "https://goldbook.iupac.org/terms/view/M03722",
            "https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf",
            "https://www.iso.org/standard/68797.html",
        ),
        assumptions=(
            "target mass fraction is an exact setpoint",
            "declared input standard uncertainties are uncorrelated",
            "no material is lost during transfer or mixing",
        ),
        limitations=(
            "EXACT classifies the algebra, not the accuracy of measured inputs",
            "volume output requires a user-supplied stock density",
            "pipette feasibility uses the declared range and increment only",
        ),
    )

    def reach_target_active_fraction(self, request: AdditionRequest) -> AdditionResult:
        bottle = request.bottle
        stock = request.stock
        target = request.target_active_mass_fraction
        current = bottle.active_material_mass_g / bottle.total_mass_g

        if target >= stock.active_mass_fraction:
            raise AdditionCalculationError(
                "target_active_mass_fraction must be lower than the stock active mass fraction"
            )
        if target < current and not _same_fraction(target, current):
            raise AdditionCalculationError(
                "target_active_mass_fraction is below current bottle fraction; "
                "an additive operation cannot lower concentration"
            )

        if _same_fraction(target, current):
            return self._zero_addition(request, current)

        denominator = stock.active_mass_fraction - target
        stock_mass_g = (
            target * bottle.total_mass_g - bottle.active_material_mass_g
        ) / denominator
        mass_uncertainty_g = _stock_mass_uncertainty(
            stock_mass_g=stock_mass_g,
            target=target,
            denominator=denominator,
            bottle=bottle,
            stock=stock,
        )

        exact_volume_ul: float | None = None
        volume_uncertainty_ul: float | None = None
        if stock.density_g_ml is not None:
            exact_volume_ul = 1000.0 * stock_mass_g / stock.density_g_ml
            volume_uncertainty_ul = hypot(
                1000.0 * mass_uncertainty_g / stock.density_g_ml,
                1000.0
                * stock_mass_g
                * stock.density_standard_uncertainty_g_ml
                / stock.density_g_ml**2,
            )

        rounded_volume_ul: float | None = None
        rounded_mass_g: float | None = None
        stages: tuple[float, ...] = ()
        pipette_feasible = False
        warnings: list[str] = []

        if exact_volume_ul is None:
            warnings.append(
                "Stock density was not supplied; volume and pipette plan are unavailable."
            )
        elif request.pipette is None:
            warnings.append(
                "No pipette profile was supplied; exact volume is reported without a delivery plan."
            )
        else:
            rounded_volume_ul, stages, warning = _pipette_plan(
                exact_volume_ul, request.pipette
            )
            if warning is not None:
                warnings.append(warning)
            else:
                pipette_feasible = True
                rounded_mass_g = rounded_volume_ul * stock.density_g_ml / 1000.0

        calculated_ledger = _mass_ledger(request, stock_mass_g)
        rounded_ledger = (
            _mass_ledger(request, rounded_mass_g)
            if rounded_mass_g is not None
            else None
        )
        resulting_ledger = rounded_ledger or calculated_ledger
        resulting_fraction = resulting_ledger["after"]["active_mass_fraction"]

        return AdditionResult(
            exact_stock_mass_g=stock_mass_g,
            exact_stock_mass_standard_uncertainty_g=mass_uncertainty_g,
            exact_stock_volume_ul=exact_volume_ul,
            exact_stock_volume_standard_uncertainty_ul=volume_uncertainty_ul,
            rounded_stock_volume_ul=rounded_volume_ul,
            rounded_stock_mass_g=rounded_mass_g,
            resulting_active_mass_fraction=resulting_fraction,
            target_error_ppm=(resulting_fraction - target) * 1_000_000.0,
            pipette_feasible=pipette_feasible,
            staged_additions_ul=stages,
            pipette_standard_uncertainty_ul=(
                request.pipette.standard_uncertainty_ul
                if pipette_feasible and request.pipette is not None
                else None
            ),
            mass_ledger={
                "calculated": calculated_ledger,
                "pipette_rounded": rounded_ledger,
            },
            evidence=self._EVIDENCE,
            warnings=tuple(warnings),
        )

    def _zero_addition(
        self, request: AdditionRequest, current_fraction: float
    ) -> AdditionResult:
        exact_volume_ul = 0.0 if request.stock.density_g_ml is not None else None
        has_volume = exact_volume_ul is not None
        has_pipette = request.pipette is not None
        warnings: tuple[str, ...] = ()
        if not has_volume:
            warnings = (
                "Stock density was not supplied; volume and pipette plan are unavailable.",
            )
        ledger = _mass_ledger(request, 0.0)
        return AdditionResult(
            exact_stock_mass_g=0.0,
            exact_stock_mass_standard_uncertainty_g=0.0,
            exact_stock_volume_ul=exact_volume_ul,
            exact_stock_volume_standard_uncertainty_ul=(0.0 if has_volume else None),
            rounded_stock_volume_ul=(0.0 if has_volume and has_pipette else None),
            rounded_stock_mass_g=(0.0 if has_volume and has_pipette else None),
            resulting_active_mass_fraction=current_fraction,
            target_error_ppm=(
                current_fraction - request.target_active_mass_fraction
            )
            * 1_000_000.0,
            pipette_feasible=has_volume and has_pipette,
            staged_additions_ul=(),
            pipette_standard_uncertainty_ul=(
                request.pipette.standard_uncertainty_ul
                if has_volume and has_pipette and request.pipette is not None
                else None
            ),
            mass_ledger={
                "calculated": ledger,
                "pipette_rounded": ledger if has_volume and has_pipette else None,
            },
            evidence=self._EVIDENCE,
            warnings=warnings,
        )


def _same_fraction(left: float, right: float) -> bool:
    return abs(left - right) <= 1e-15


def _stock_mass_uncertainty(
    *,
    stock_mass_g: float,
    target: float,
    denominator: float,
    bottle: BottleSnapshot,
    stock: StockSolution,
) -> float:
    total_mass_component = (
        target / denominator * bottle.total_mass_standard_uncertainty_g
    )
    active_mass_component = (
        bottle.active_mass_standard_uncertainty_g / denominator
    )
    stock_fraction_component = (
        stock_mass_g
        / denominator
        * stock.active_fraction_standard_uncertainty
    )
    return hypot(
        total_mass_component,
        active_mass_component,
        stock_fraction_component,
    )


def _pipette_plan(
    exact_volume_ul: float, pipette: PipetteProfile
) -> tuple[float | None, tuple[float, ...], str | None]:
    rounded_units = floor(exact_volume_ul / pipette.increment_ul + 0.5)
    rounded_volume_ul = rounded_units * pipette.increment_ul
    if rounded_volume_ul < pipette.minimum_ul:
        return (
            None,
            (),
            "Calculated volume is below the pipette minimum; no rounded-up dose was created.",
        )

    if pipette.maximum_single_step_ul is None:
        return rounded_volume_ul, (rounded_volume_ul,), None

    maximum_units = floor(
        pipette.maximum_single_step_ul / pipette.increment_ul
    )
    minimum_units = ceil(pipette.minimum_ul / pipette.increment_ul)
    if maximum_units <= 0:
        return None, (), "Pipette range contains no deliverable increment."

    step_count = ceil(rounded_units / maximum_units)
    base_units, remainder = divmod(rounded_units, step_count)
    step_units = tuple(
        base_units + (1 if index < remainder else 0)
        for index in range(step_count)
    )
    if any(units < minimum_units or units > maximum_units for units in step_units):
        return (
            None,
            (),
            "Rounded volume cannot be staged within the declared pipette range.",
        )
    return (
        rounded_volume_ul,
        tuple(units * pipette.increment_ul for units in step_units),
        None,
    )


def _mass_ledger(request: AdditionRequest, stock_mass_g: float) -> dict[str, Any]:
    active_added_g = stock_mass_g * request.stock.active_mass_fraction
    after_total_g = request.bottle.total_mass_g + stock_mass_g
    after_active_g = request.bottle.active_material_mass_g + active_added_g
    return {
        "before": {
            "total_mass_g": request.bottle.total_mass_g,
            "active_material_mass_g": request.bottle.active_material_mass_g,
        },
        "addition": {
            "stock_mass_g": stock_mass_g,
            "active_material_mass_g": active_added_g,
        },
        "after": {
            "total_mass_g": after_total_g,
            "active_material_mass_g": after_active_g,
            "active_mass_fraction": after_active_g / after_total_g,
        },
    }


__all__ = [
    "AdditionCalculationError",
    "AdditionRequest",
    "AdditionResult",
    "AdditionSolver",
    "BottleSnapshot",
    "PipetteProfile",
    "StockSolution",
]
