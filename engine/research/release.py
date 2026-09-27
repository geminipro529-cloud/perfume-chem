"""Scenario-bound finite release trajectories with explicit mass compartments.

This is a composable research model, not a skin-performance certificate.  It
keeps interfacial equilibrium, finite transfer, substrate retention, local gas
concentration, and delivered mass separate.  Ideal-Raoult and Hansen-derived
activity inputs are always labelled sensitivity scenarios.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Literal, Mapping, Protocol, Sequence

from .contracts import FALSE_ACTION_AUTHORITY, ReleaseScenarioV1, decimal_text

R_GAS_J_MOL_K = 8.31446261815324

EquilibriumModel = Literal[
    "MEASURED_HEADSPACE",
    "EMPIRICAL_ACTIVITY",
    "NONIDEAL_PARAMETERIZED",
    "IDEAL_SENSITIVITY",
    "HANSEN_SENSITIVITY",
]


def _finite_decimal(
    value: object, name: str, *, nonnegative: bool = False, positive: bool = False
) -> str:
    return decimal_text(value, name, nonnegative=nonnegative, positive=positive)


def _fraction(value: object, name: str) -> str:
    normalized = _finite_decimal(value, name, nonnegative=True)
    if Decimal(normalized) > 1:
        raise ValueError(f"{name} must be between zero and one")
    return normalized


@dataclass(frozen=True, slots=True)
class ReleaseComponentV1:
    material_id: str
    initial_mass_g_decimal: str
    identity_state: Literal["EXACT", "UNKNOWN_NATURAL_REMAINDER"] = "EXACT"
    molecular_weight_g_mol: float | None = None
    vapor_pressure_pa: float | None = None
    activity_coefficient: float | None = None
    measured_interfacial_pressure_pa: float | None = None
    substrate_retained_fraction_decimal: str = "0"
    precipitated_fraction_decimal: str = "0"
    reacted_fraction_decimal: str = "0"
    desorption_rate_s_decimal: str = "0"
    permeation_rate_s_decimal: str = "0"
    reaction_rate_s_decimal: str = "0"

    def __post_init__(self) -> None:
        if not isinstance(self.material_id, str) or not self.material_id.strip():
            raise ValueError("material_id must be non-empty text")
        object.__setattr__(self, "material_id", self.material_id.strip())
        object.__setattr__(
            self,
            "initial_mass_g_decimal",
            _finite_decimal(
                self.initial_mass_g_decimal,
                "initial_mass_g_decimal",
                nonnegative=True,
            ),
        )
        for name in (
            "substrate_retained_fraction_decimal",
            "precipitated_fraction_decimal",
            "reacted_fraction_decimal",
        ):
            object.__setattr__(self, name, _fraction(getattr(self, name), name))
        if sum(
            Decimal(getattr(self, name))
            for name in (
                "substrate_retained_fraction_decimal",
                "precipitated_fraction_decimal",
                "reacted_fraction_decimal",
            )
        ) > 1:
            raise ValueError("initial compartment fractions cannot exceed one")
        for name in (
            "desorption_rate_s_decimal",
            "permeation_rate_s_decimal",
            "reaction_rate_s_decimal",
        ):
            object.__setattr__(
                self,
                name,
                _finite_decimal(getattr(self, name), name, nonnegative=True),
            )
        for name in (
            "molecular_weight_g_mol",
            "vapor_pressure_pa",
            "activity_coefficient",
            "measured_interfacial_pressure_pa",
        ):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) <= 0
            ):
                raise ValueError(f"{name} must be finite and positive when supplied")
            if value is not None:
                object.__setattr__(self, name, float(value))


@dataclass(frozen=True, slots=True)
class FiniteReleaseParametersV1:
    capability_id: str
    equilibrium_model: EquilibriumModel
    matrix_ids: tuple[str, ...]
    supported_substrates: tuple[str, ...]
    mass_transfer_coefficient_m_s_decimal: str
    air_exchange_rate_s_decimal: str
    delivered_capture_fraction_decimal: str
    maximum_step_seconds_decimal: str
    calibration_state: Literal[
        "HELD_OUT_VALIDATED", "CALIBRATED_NO_HELD_OUT", "UNCALIBRATED"
    ]

    def __post_init__(self) -> None:
        if not isinstance(self.capability_id, str) or not self.capability_id.strip():
            raise ValueError("capability_id must be non-empty text")
        object.__setattr__(self, "capability_id", self.capability_id.strip())
        matrix_ids = tuple(str(value).strip() for value in self.matrix_ids)
        substrates = tuple(str(value).strip() for value in self.supported_substrates)
        if not matrix_ids or any(not value for value in matrix_ids):
            raise ValueError("at least one explicit matrix_id is required")
        if not substrates or any(not value for value in substrates):
            raise ValueError("at least one explicit supported substrate is required")
        object.__setattr__(self, "matrix_ids", matrix_ids)
        object.__setattr__(self, "supported_substrates", substrates)
        for name in (
            "mass_transfer_coefficient_m_s_decimal",
            "maximum_step_seconds_decimal",
        ):
            object.__setattr__(
                self, name, _finite_decimal(getattr(self, name), name, positive=True)
            )
        object.__setattr__(
            self,
            "air_exchange_rate_s_decimal",
            _finite_decimal(
                self.air_exchange_rate_s_decimal,
                "air_exchange_rate_s_decimal",
                nonnegative=True,
            ),
        )
        object.__setattr__(
            self,
            "delivered_capture_fraction_decimal",
            _fraction(
                self.delivered_capture_fraction_decimal,
                "delivered_capture_fraction_decimal",
            ),
        )


@dataclass(frozen=True, slots=True)
class MaterialReleaseFrameV1:
    material_id: str
    available_g: float
    substrate_retained_g: float
    precipitated_g: float
    reacted_g: float
    permeated_g: float
    local_gas_g: float
    delivered_g: float
    vented_g: float
    unknown_remainder_g: float
    interfacial_pressure_pa: float | None
    local_gas_ug_l: float | None
    delivered_cumulative_ug_l: float | None
    delivered_increment_ug_l: float | None
    delivered_increment_g: float
    mass_balance_error_g: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReleaseTrajectoryFrameV1:
    time_seconds: float
    materials: tuple[MaterialReleaseFrameV1, ...]
    total_initial_g: float
    total_accounted_g: float
    mass_balance_error_g: float

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["materials"] = [item.as_dict() for item in self.materials]
        return value


ReleaseState = dict[str, dict[str, float]]


class CompositionResolver(Protocol):
    def resolve(
        self,
        components: Sequence[ReleaseComponentV1],
        initial_by_id: Mapping[str, float],
    ) -> ReleaseState: ...


class LiquidEquilibriumModel(Protocol):
    def pressures(
        self,
        components: Mapping[str, ReleaseComponentV1],
        state: ReleaseState,
        initial_by_id: Mapping[str, float],
        equilibrium_model: EquilibriumModel,
    ) -> dict[str, float | None]: ...


class SubstrateModel(Protocol):
    def advance(
        self,
        component: ReleaseComponentV1,
        compartment: dict[str, float],
        dt_seconds: float,
    ) -> None: ...


class FiniteTransferModel(Protocol):
    def advance(
        self,
        component: ReleaseComponentV1,
        compartment: dict[str, float],
        *,
        pressure_pa: float,
        dt_seconds: float,
        surface_area_m2: float,
        temperature_k: float,
        mass_transfer_coefficient_m_s: float,
    ) -> None: ...


class DeliveryModel(Protocol):
    def advance(
        self,
        compartment: dict[str, float],
        *,
        dt_seconds: float,
        air_exchange_rate_s: float,
        capture_fraction: float,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class DefaultCompositionResolver:
    def resolve(
        self,
        components: Sequence[ReleaseComponentV1],
        initial_by_id: Mapping[str, float],
    ) -> ReleaseState:
        state: ReleaseState = {}
        for row in components:
            initial = initial_by_id[row.material_id]
            if row.identity_state == "UNKNOWN_NATURAL_REMAINDER":
                state[row.material_id] = {
                    "available": 0.0,
                    "retained": 0.0,
                    "precipitated": 0.0,
                    "reacted": 0.0,
                    "permeated": 0.0,
                    "gas": 0.0,
                    "delivered": 0.0,
                    "vented": 0.0,
                    "unknown": initial,
                    "delivered_increment": 0.0,
                }
                continue
            retained = initial * float(Decimal(row.substrate_retained_fraction_decimal))
            precipitated = initial * float(Decimal(row.precipitated_fraction_decimal))
            reacted = initial * float(Decimal(row.reacted_fraction_decimal))
            state[row.material_id] = {
                "available": max(0.0, initial - retained - precipitated - reacted),
                "retained": retained,
                "precipitated": precipitated,
                "reacted": reacted,
                "permeated": 0.0,
                "gas": 0.0,
                "delivered": 0.0,
                "vented": 0.0,
                "unknown": 0.0,
                "delivered_increment": 0.0,
            }
        return state


@dataclass(frozen=True, slots=True)
class DefaultLiquidEquilibriumModel:
    def pressures(
        self,
        components: Mapping[str, ReleaseComponentV1],
        state: ReleaseState,
        initial_by_id: Mapping[str, float],
        equilibrium_model: EquilibriumModel,
    ) -> dict[str, float | None]:
        moles: dict[str, float] = {}
        for material_id, compartment in state.items():
            row = components[material_id]
            if (
                row.identity_state == "EXACT"
                and compartment["available"] > 0
                and row.molecular_weight_g_mol is not None
            ):
                moles[material_id] = (
                    compartment["available"] / row.molecular_weight_g_mol
                )
        total_moles = math.fsum(moles.values())
        pressures: dict[str, float | None] = {}
        for material_id, row in components.items():
            available = state[material_id]["available"]
            if row.identity_state != "EXACT" or available <= 0:
                pressures[material_id] = (
                    None if row.identity_state != "EXACT" else 0.0
                )
                continue
            if equilibrium_model == "MEASURED_HEADSPACE":
                assert row.measured_interfacial_pressure_pa is not None
                initial_available = initial_by_id[material_id] * (
                    1
                    - float(Decimal(row.substrate_retained_fraction_decimal))
                    - float(Decimal(row.precipitated_fraction_decimal))
                    - float(Decimal(row.reacted_fraction_decimal))
                )
                pressures[material_id] = row.measured_interfacial_pressure_pa * (
                    available / initial_available if initial_available > 0 else 0.0
                )
                continue
            assert row.vapor_pressure_pa is not None
            gamma = (
                1.0
                if equilibrium_model == "IDEAL_SENSITIVITY"
                else row.activity_coefficient
            )
            assert gamma is not None
            mole_fraction = (
                moles.get(material_id, 0.0) / total_moles
                if total_moles > 0
                else 0.0
            )
            pressures[material_id] = mole_fraction * gamma * row.vapor_pressure_pa
        return pressures


@dataclass(frozen=True, slots=True)
class DefaultSubstrateModel:
    def advance(
        self,
        component: ReleaseComponentV1,
        compartment: dict[str, float],
        dt_seconds: float,
    ) -> None:
        retained = compartment["retained"]
        if retained > 0:
            desorbed = retained * (
                1.0
                - math.exp(
                    -float(Decimal(component.desorption_rate_s_decimal))
                    * dt_seconds
                )
            )
            remaining_retained = retained - desorbed
            permeated = remaining_retained * (
                1.0
                - math.exp(
                    -float(Decimal(component.permeation_rate_s_decimal))
                    * dt_seconds
                )
            )
            compartment["retained"] = max(0.0, remaining_retained - permeated)
            compartment["available"] += desorbed
            compartment["permeated"] += permeated
        available = compartment["available"]
        if available > 0:
            reacted = available * (
                1.0
                - math.exp(
                    -float(Decimal(component.reaction_rate_s_decimal)) * dt_seconds
                )
            )
            compartment["available"] -= reacted
            compartment["reacted"] += reacted


@dataclass(frozen=True, slots=True)
class DefaultFiniteTransferModel:
    def advance(
        self,
        component: ReleaseComponentV1,
        compartment: dict[str, float],
        *,
        pressure_pa: float,
        dt_seconds: float,
        surface_area_m2: float,
        temperature_k: float,
        mass_transfer_coefficient_m_s: float,
    ) -> None:
        if pressure_pa <= 0 or compartment["available"] <= 0:
            return
        assert component.molecular_weight_g_mol is not None
        emitted_moles = (
            mass_transfer_coefficient_m_s
            * surface_area_m2
            * pressure_pa
            / (R_GAS_J_MOL_K * temperature_k)
            * dt_seconds
        )
        emitted_g = min(
            compartment["available"],
            emitted_moles * component.molecular_weight_g_mol,
        )
        compartment["available"] -= emitted_g
        compartment["gas"] += emitted_g


@dataclass(frozen=True, slots=True)
class DefaultDeliveryModel:
    def advance(
        self,
        compartment: dict[str, float],
        *,
        dt_seconds: float,
        air_exchange_rate_s: float,
        capture_fraction: float,
    ) -> None:
        if compartment["gas"] <= 0 or air_exchange_rate_s <= 0:
            return
        outgoing = compartment["gas"] * (
            1.0 - math.exp(-air_exchange_rate_s * dt_seconds)
        )
        delivered = outgoing * capture_fraction
        compartment["gas"] -= outgoing
        compartment["delivered"] += delivered
        compartment["vented"] += outgoing - delivered
        compartment["delivered_increment"] += delivered


@dataclass(frozen=True, slots=True)
class ReleaseModelPipelineV1:
    composition_resolver: CompositionResolver
    equilibrium_model: LiquidEquilibriumModel
    substrate_model: SubstrateModel
    transfer_model: FiniteTransferModel
    delivery_model: DeliveryModel


def default_release_pipeline() -> ReleaseModelPipelineV1:
    return ReleaseModelPipelineV1(
        composition_resolver=DefaultCompositionResolver(),
        equilibrium_model=DefaultLiquidEquilibriumModel(),
        substrate_model=DefaultSubstrateModel(),
        transfer_model=DefaultFiniteTransferModel(),
        delivery_model=DefaultDeliveryModel(),
    )


def _missing_physics(
    component: ReleaseComponentV1, model: EquilibriumModel
) -> list[str]:
    if Decimal(component.initial_mass_g_decimal) == 0:
        return []
    if component.identity_state == "UNKNOWN_NATURAL_REMAINDER":
        return []
    missing: list[str] = []
    if component.molecular_weight_g_mol is None:
        missing.append("MOLECULAR_WEIGHT_MISSING")
    if model == "MEASURED_HEADSPACE":
        if component.measured_interfacial_pressure_pa is None:
            missing.append("MEASURED_HEADSPACE_PRESSURE_MISSING")
    else:
        if component.vapor_pressure_pa is None:
            missing.append("VAPOR_PRESSURE_MISSING")
        if model == "IDEAL_SENSITIVITY":
            if component.activity_coefficient not in {None, 1.0}:
                missing.append("IDEAL_SCENARIO_ACTIVITY_MUST_EQUAL_ONE")
        elif component.activity_coefficient is None:
            missing.append("ACTIVITY_PARAMETER_MISSING")
    return missing


def _validation_result(
    *,
    state: str,
    applicability: str,
    reasons: Sequence[str],
    missing: Sequence[Mapping[str, Any]],
    scenario: ReleaseScenarioV1,
    parameters: FiniteReleaseParametersV1,
    coverage: float,
    frames: Sequence[ReleaseTrajectoryFrameV1] = (),
) -> dict[str, Any]:
    return {
        "schema_version": "finite-release-trajectory-v1",
        "validation_state": state,
        "applicability_state": applicability,
        "reason_codes": sorted(set(reasons)),
        "missing_requirements": list(missing),
        "positive_mass_coverage_decimal": decimal_text(
            coverage, "positive_mass_coverage", nonnegative=True
        ),
        "scenario": scenario.as_dict(),
        "scenario_sha256": scenario.sha256,
        "capability_id": parameters.capability_id,
        "equilibrium_model": parameters.equilibrium_model,
        "calibration_state": parameters.calibration_state,
        "frames": [frame.as_dict() for frame in frames],
        "prediction_certificate": False,
        "formula_action": "NO_CHANGE",
        **FALSE_ACTION_AUTHORITY,
    }


def simulate_finite_release(
    components: Sequence[ReleaseComponentV1],
    *,
    scenario: ReleaseScenarioV1,
    parameters: FiniteReleaseParametersV1,
    mass_balance_tolerance_g: float = 1e-10,
    pipeline: ReleaseModelPipelineV1 | None = None,
) -> dict[str, Any]:
    """Simulate one exact matrix/substrate scenario with finite depletion.

    Malformed numeric input raises ``ValueError``. Missing scientific inputs or
    a scenario mismatch return an explicit withheld result with no trajectory.
    """

    rows = tuple(components)
    if not rows:
        raise ValueError("at least one release component is required")
    if len({row.material_id for row in rows}) != len(rows):
        raise ValueError("release material identities must be unique")
    if (
        isinstance(mass_balance_tolerance_g, bool)
        or not math.isfinite(mass_balance_tolerance_g)
        or mass_balance_tolerance_g <= 0
    ):
        raise ValueError("mass_balance_tolerance_g must be finite and positive")

    scenario_reasons: list[str] = []
    if scenario.matrix_id not in parameters.matrix_ids:
        scenario_reasons.append("MATRIX_OUT_OF_DOMAIN")
    if scenario.substrate not in parameters.supported_substrates:
        scenario_reasons.append("SUBSTRATE_OUT_OF_DOMAIN")
    if scenario_reasons:
        return _validation_result(
            state="WITHHOLD_UNKNOWN",
            applicability="OUT_OF_DOMAIN",
            reasons=scenario_reasons,
            missing=(),
            scenario=scenario,
            parameters=parameters,
            coverage=0.0,
        )

    missing: list[dict[str, Any]] = []
    positive = [row for row in rows if Decimal(row.initial_mass_g_decimal) > 0]
    supported_positive = 0
    for row in positive:
        row_missing = _missing_physics(row, parameters.equilibrium_model)
        if row_missing:
            missing.append(
                {"material_id": row.material_id, "reason_codes": row_missing}
            )
        else:
            supported_positive += 1
    coverage = supported_positive / len(positive) if positive else 1.0
    if missing:
        return _validation_result(
            state="WITHHOLD_UNKNOWN",
            applicability="UNAVAILABLE",
            reasons=("RELEASE_PHYSICS_INCOMPLETE",),
            missing=missing,
            scenario=scenario,
            parameters=parameters,
            coverage=coverage,
        )

    initial_by_id = {
        row.material_id: float(Decimal(row.initial_mass_g_decimal)) for row in rows
    }
    total_initial = math.fsum(initial_by_id.values())
    declared_deposit = float(Decimal(scenario.deposit_mass_g_decimal))
    if not math.isclose(
        total_initial,
        declared_deposit,
        rel_tol=0.0,
        abs_tol=max(mass_balance_tolerance_g, 1e-12),
    ):
        return _validation_result(
            state="INVALID_INPUT",
            applicability="UNAVAILABLE",
            reasons=("DEPOSIT_MASS_DOES_NOT_MATCH_COMPONENT_MASS",),
            missing=(),
            scenario=scenario,
            parameters=parameters,
            coverage=coverage,
        )

    active_pipeline = pipeline or default_release_pipeline()
    state = active_pipeline.composition_resolver.resolve(rows, initial_by_id)
    if set(state) != set(initial_by_id):
        raise ArithmeticError("composition resolver changed material identities")

    row_by_id = {row.material_id: row for row in rows}
    area = float(Decimal(scenario.surface_area_m2_decimal))
    volume_m3 = float(Decimal(scenario.delivery_volume_m3_decimal))
    temperature = scenario.temperature_k
    transfer_coefficient = float(
        Decimal(parameters.mass_transfer_coefficient_m_s_decimal)
    )
    air_exchange = float(Decimal(parameters.air_exchange_rate_s_decimal))
    capture_fraction = float(
        Decimal(parameters.delivered_capture_fraction_decimal)
    )
    maximum_step = float(Decimal(parameters.maximum_step_seconds_decimal))

    def interfacial_pressures() -> dict[str, float | None]:
        pressures = active_pipeline.equilibrium_model.pressures(
            row_by_id,
            state,
            initial_by_id,
            parameters.equilibrium_model,
        )
        if set(pressures) != set(row_by_id):
            raise ArithmeticError("equilibrium model changed material identities")
        for material_id, pressure in pressures.items():
            row = row_by_id[material_id]
            if pressure is None:
                if row.identity_state != "UNKNOWN_NATURAL_REMAINDER":
                    raise ArithmeticError("equilibrium model omitted an exact identity")
            elif not math.isfinite(pressure) or pressure < 0:
                raise ArithmeticError("equilibrium model returned invalid pressure")
        return pressures

    def frame(time_seconds: float) -> ReleaseTrajectoryFrameV1:
        pressures = interfacial_pressures()
        material_frames: list[MaterialReleaseFrameV1] = []
        total_accounted = 0.0
        for material_id in sorted(state):
            item = state[material_id]
            accounted = math.fsum(item[key] for key in (
                "available", "retained", "precipitated", "reacted", "permeated",
                "gas", "delivered", "vented", "unknown"
            ))
            total_accounted += accounted
            local_concentration = (
                item["gas"] * 1000.0 / volume_m3
                if row_by_id[material_id].identity_state == "EXACT"
                else None
            )
            delivered_cumulative_concentration = (
                item["delivered"] * 1000.0 / volume_m3
                if row_by_id[material_id].identity_state == "EXACT"
                else None
            )
            delivered_increment_concentration = (
                item["delivered_increment"] * 1000.0 / volume_m3
                if row_by_id[material_id].identity_state == "EXACT"
                else None
            )
            material_frames.append(
                MaterialReleaseFrameV1(
                    material_id=material_id,
                    available_g=item["available"],
                    substrate_retained_g=item["retained"],
                    precipitated_g=item["precipitated"],
                    reacted_g=item["reacted"],
                    permeated_g=item["permeated"],
                    local_gas_g=item["gas"],
                    delivered_g=item["delivered"],
                    vented_g=item["vented"],
                    unknown_remainder_g=item["unknown"],
                    interfacial_pressure_pa=pressures[material_id],
                    local_gas_ug_l=local_concentration,
                    delivered_cumulative_ug_l=delivered_cumulative_concentration,
                    delivered_increment_ug_l=delivered_increment_concentration,
                    delivered_increment_g=item["delivered_increment"],
                    mass_balance_error_g=accounted - initial_by_id[material_id],
                )
            )
        return ReleaseTrajectoryFrameV1(
            time_seconds=time_seconds,
            materials=tuple(material_frames),
            total_initial_g=total_initial,
            total_accounted_g=total_accounted,
            mass_balance_error_g=total_accounted - total_initial,
        )

    frames: list[ReleaseTrajectoryFrameV1] = [frame(0.0)]
    current_time = 0.0
    for target_time in scenario.timepoints_seconds[1:]:
        while current_time < target_time:
            dt = min(maximum_step, target_time - current_time)
            pressures = interfacial_pressures()
            for material_id, row in row_by_id.items():
                item = state[material_id]
                item["delivered_increment"] = 0.0
                if row.identity_state != "EXACT":
                    continue
                active_pipeline.substrate_model.advance(row, item, dt)
                pressure = pressures[material_id] or 0.0
                active_pipeline.transfer_model.advance(
                    row,
                    item,
                    pressure_pa=pressure,
                    dt_seconds=dt,
                    surface_area_m2=area,
                    temperature_k=temperature,
                    mass_transfer_coefficient_m_s=transfer_coefficient,
                )
                active_pipeline.delivery_model.advance(
                    item,
                    dt_seconds=dt,
                    air_exchange_rate_s=air_exchange,
                    capture_fraction=capture_fraction,
                )
            current_time += dt
        current_frame = frame(target_time)
        if abs(current_frame.mass_balance_error_g) > mass_balance_tolerance_g:
            raise ArithmeticError("finite release mass conservation failed")
        frames.append(current_frame)

    has_unknown = any(row.identity_state == "UNKNOWN_NATURAL_REMAINDER" for row in rows)
    sensitivity = parameters.equilibrium_model in {
        "IDEAL_SENSITIVITY",
        "HANSEN_SENSITIVITY",
    }
    validated = parameters.calibration_state == "HELD_OUT_VALIDATED" and not sensitivity and not has_unknown
    reasons: list[str] = []
    if sensitivity:
        reasons.append("SENSITIVITY_SCENARIO_NOT_EMPIRICAL_PREDICTION")
    if parameters.calibration_state != "HELD_OUT_VALIDATED":
        reasons.append("HELD_OUT_SCENARIO_VALIDATION_MISSING")
    if has_unknown:
        reasons.append("UNKNOWN_NATURAL_REMAINDER_PRESERVED")
    return _validation_result(
        state="ADVISORY_COMPLETE" if validated else "ADVISORY_FINDINGS",
        applicability="APPLICABLE" if validated else "PARTIAL",
        reasons=reasons,
        missing=(),
        scenario=scenario,
        parameters=parameters,
        coverage=coverage,
        frames=frames,
    )


__all__ = [
    "CompositionResolver",
    "DefaultCompositionResolver",
    "DefaultDeliveryModel",
    "DefaultFiniteTransferModel",
    "DefaultLiquidEquilibriumModel",
    "DefaultSubstrateModel",
    "DeliveryModel",
    "FiniteReleaseParametersV1",
    "FiniteTransferModel",
    "LiquidEquilibriumModel",
    "MaterialReleaseFrameV1",
    "ReleaseComponentV1",
    "ReleaseModelPipelineV1",
    "ReleaseTrajectoryFrameV1",
    "SubstrateModel",
    "default_release_pipeline",
    "simulate_finite_release",
]
