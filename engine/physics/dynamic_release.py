"""Conservative, substrate-bound C6 physical release simulation.

This module implements a transparent compartment state machine behind the C3
versioned-model interface.  Every executable parameter set is explicitly
uncalibrated and simulation-only.  No legacy temporal, diffusion, skin, OAV, or
production runtime is imported or adapted here.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

from engine.calibration.hashing import stable_json_hash
from engine.physics.matrix_environment import (
    ApplicationEnvironment,
    ApplicationEnvironmentKind,
    CompositionCompleteness,
    MatrixComponentRole,
    MatrixComposition,
    MatrixQuantityBasis,
    MatrixStage,
)
from engine.physics.model_interface import (
    ApplicabilityDomain,
    ApplicabilityResult,
    ApplicabilityState,
    ModelAvailability,
    ModelComputation,
    ModelEvidenceClass,
    ModelFamily,
    ModelInputReference,
    ModelOperation,
    ModelOutput,
    ModelRelease,
    ModelSelector,
    VersionedModelRequest,
)
from engine.physics.properties import CanonicalScope, UncertaintyDescriptor

C6_INPUT_ROLE = "c6_dynamic_release_input_set"
C6_MODEL_VERSION = "c6-conservative-compartment-v1"
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_MAX_STEPS = 10_000
_MACHINE_NEGATIVE_TOLERANCE_MG = 1e-12
_OUTPUT_CLOSURE_TOLERANCE_MG = 1e-6
_SEALED_KIND = ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL
_OPEN_KIND = ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE
_FINITE_FILM_KINDS = tuple(kind for kind in ApplicationEnvironmentKind if kind is not _SEALED_KIND)
_SUBSTRATE_REQUIRED_KINDS = frozenset(kind for kind in _FINITE_FILM_KINDS if kind is not _OPEN_KIND)
_SOLVENT_ROLES = frozenset(
    {
        MatrixComponentRole.ETHANOL,
        MatrixComponentRole.WATER,
        MatrixComponentRole.DPG,
        MatrixComponentRole.DEP,
        MatrixComponentRole.TEC,
        MatrixComponentRole.IPM,
        MatrixComponentRole.OTHER_CARRIER,
        MatrixComponentRole.OTHER_PRODUCT_PHASE,
    }
)
_EnumT = TypeVar("_EnumT", bound=Enum)


class DynamicReleaseContractError(ValueError):
    """Malformed C6 input, context, state, or mass-accounting result."""


class PhysicalProcessLayer(str, Enum):
    EQUILIBRIUM_PARTITION = "EQUILIBRIUM_PARTITION"
    MASS_TRANSFER_AND_EVAPORATION = "MASS_TRANSFER_AND_EVAPORATION"
    SUBSTRATE_SORPTION = "SUBSTRATE_SORPTION"
    PHYSICAL_HEADSPACE_TRAJECTORY = "PHYSICAL_HEADSPACE_TRAJECTORY"
    OLFACTORY_ADAPTATION = "OLFACTORY_ADAPTATION"
    PERCEIVED_INTENSITY = "PERCEIVED_INTENSITY"
    TEMPORAL_ATTRIBUTE_PROFILE = "TEMPORAL_ATTRIBUTE_PROFILE"


class PhysicalTrajectoryLabel(str, Enum):
    PREDICTED_HEADSPACE_TRAJECTORY = "PREDICTED_HEADSPACE_TRAJECTORY"
    PREDICTED_RELEASE_TRAJECTORY = "PREDICTED_RELEASE_TRAJECTORY"
    ESTIMATED_PHYSICAL_PERSISTENCE = "ESTIMATED_PHYSICAL_PERSISTENCE"


PERMITTED_C6_OUTPUT_LABELS = tuple(PhysicalTrajectoryLabel)


class DynamicParameterAuthority(str, Enum):
    SIMULATION_ONLY_UNCALIBRATED = "SIMULATION_ONLY_UNCALIBRATED"


class RateScenario(str, Enum):
    LOWER_RATE = "LOWER_RATE"
    NOMINAL = "NOMINAL"
    UPPER_RATE = "UPPER_RATE"


def _mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DynamicReleaseContractError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise DynamicReleaseContractError(f"{field_name} keys must be strings")
    return dict(value)


def _exact_keys(
    payload: Mapping[str, Any],
    expected: set[str],
    field_name: str,
) -> None:
    missing = expected - set(payload)
    unknown = set(payload) - expected
    if missing:
        raise DynamicReleaseContractError(
            f"{field_name} missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise DynamicReleaseContractError(
            f"{field_name} contains unknown fields: {', '.join(sorted(unknown))}"
        )


def _nonblank(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DynamicReleaseContractError(f"{field_name} must not be blank")
    return value.strip()


def _finite(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise DynamicReleaseContractError(f"{field_name} must be finite")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise DynamicReleaseContractError(f"{field_name} must be finite") from exc
    if not math.isfinite(result):
        raise DynamicReleaseContractError(f"{field_name} must be finite")
    return result


def _nonnegative(value: object, field_name: str) -> float:
    result = _finite(value, field_name)
    if result < 0.0:
        raise DynamicReleaseContractError(f"{field_name} must be non-negative")
    return result


def _positive(value: object, field_name: str) -> float:
    result = _finite(value, field_name)
    if result <= 0.0:
        raise DynamicReleaseContractError(f"{field_name} must be positive")
    return result


def _fraction(value: object, field_name: str) -> float:
    result = _finite(value, field_name)
    if not 0.0 <= result <= 1.0:
        raise DynamicReleaseContractError(f"{field_name} must be between zero and one")
    return result


def _optional_nonnegative(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    return _nonnegative(value, field_name)


def _sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise DynamicReleaseContractError(f"{field_name} must be a lowercase 64-character SHA-256")
    return value


def _boolean(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise DynamicReleaseContractError(f"{field_name} must be boolean")
    return value


def _enum(enum_type: type[_EnumT], value: object, field_name: str) -> _EnumT:
    if not isinstance(value, enum_type):
        raise DynamicReleaseContractError(f"{field_name} must be a {enum_type.__name__}")
    return value


def _enum_value(
    enum_type: type[_EnumT],
    value: object,
    field_name: str,
) -> _EnumT:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise DynamicReleaseContractError(
            f"{field_name} is not a supported {enum_type.__name__}"
        ) from exc


@dataclass(frozen=True, slots=True)
class DynamicComponentParameters:
    """One explicit uncalibrated transport record for one component."""

    component_id: str
    equilibrium_release_factor: float
    activity_coefficient: float
    sealed_transfer_rate_s_minus_1: float | None
    diffusion_coefficient_m2_s: float | None
    mass_transfer_coefficient_m_s: float | None
    sorption_rate_s_minus_1: float
    desorption_rate_s_minus_1: float
    sink_rate_s_minus_1: float
    matrix_feedback_exponent: float
    relative_parameter_uncertainty: float
    parameter_source_id: str
    parameter_source_sha256: str
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_id", _nonblank(self.component_id, "component_id"))
        object.__setattr__(
            self,
            "equilibrium_release_factor",
            _fraction(self.equilibrium_release_factor, "equilibrium_release_factor"),
        )
        object.__setattr__(
            self,
            "activity_coefficient",
            _positive(self.activity_coefficient, "activity_coefficient"),
        )
        for field_name in (
            "sealed_transfer_rate_s_minus_1",
            "diffusion_coefficient_m2_s",
            "mass_transfer_coefficient_m_s",
        ):
            object.__setattr__(
                self,
                field_name,
                _optional_nonnegative(getattr(self, field_name), field_name),
            )
        for field_name in (
            "sorption_rate_s_minus_1",
            "desorption_rate_s_minus_1",
            "sink_rate_s_minus_1",
            "matrix_feedback_exponent",
        ):
            object.__setattr__(
                self,
                field_name,
                _nonnegative(getattr(self, field_name), field_name),
            )
        uncertainty = _finite(
            self.relative_parameter_uncertainty,
            "relative_parameter_uncertainty",
        )
        if not 0.0 <= uncertainty < 1.0:
            raise DynamicReleaseContractError(
                "relative_parameter_uncertainty must be non-negative and less than one"
            )
        object.__setattr__(self, "relative_parameter_uncertainty", uncertainty)
        object.__setattr__(
            self,
            "parameter_source_id",
            _nonblank(self.parameter_source_id, "parameter_source_id"),
        )
        object.__setattr__(
            self,
            "parameter_source_sha256",
            _sha256(self.parameter_source_sha256, "parameter_source_sha256"),
        )
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c6-dynamic-component-parameters-v1",
            "component_id": self.component_id,
            "equilibrium_release_factor": self.equilibrium_release_factor,
            "activity_coefficient": self.activity_coefficient,
            "sealed_transfer_rate_s_minus_1": self.sealed_transfer_rate_s_minus_1,
            "diffusion_coefficient_m2_s": self.diffusion_coefficient_m2_s,
            "mass_transfer_coefficient_m_s": self.mass_transfer_coefficient_m_s,
            "sorption_rate_s_minus_1": self.sorption_rate_s_minus_1,
            "desorption_rate_s_minus_1": self.desorption_rate_s_minus_1,
            "sink_rate_s_minus_1": self.sink_rate_s_minus_1,
            "matrix_feedback_exponent": self.matrix_feedback_exponent,
            "relative_parameter_uncertainty": self.relative_parameter_uncertainty,
            "parameter_source_id": self.parameter_source_id,
            "parameter_source_sha256": self.parameter_source_sha256,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> DynamicComponentParameters:
        normalized = _mapping(payload, "dynamic component parameters")
        _exact_keys(
            normalized,
            {
                "schema",
                "component_id",
                "equilibrium_release_factor",
                "activity_coefficient",
                "sealed_transfer_rate_s_minus_1",
                "diffusion_coefficient_m2_s",
                "mass_transfer_coefficient_m_s",
                "sorption_rate_s_minus_1",
                "desorption_rate_s_minus_1",
                "sink_rate_s_minus_1",
                "matrix_feedback_exponent",
                "relative_parameter_uncertainty",
                "parameter_source_id",
                "parameter_source_sha256",
                "content_sha256",
            },
            "dynamic component parameters",
        )
        if normalized["schema"] != "c6-dynamic-component-parameters-v1":
            raise DynamicReleaseContractError(
                "dynamic component schema must be c6-dynamic-component-parameters-v1"
            )
        result = cls(
            component_id=normalized["component_id"],
            equilibrium_release_factor=normalized["equilibrium_release_factor"],
            activity_coefficient=normalized["activity_coefficient"],
            sealed_transfer_rate_s_minus_1=normalized["sealed_transfer_rate_s_minus_1"],
            diffusion_coefficient_m2_s=normalized["diffusion_coefficient_m2_s"],
            mass_transfer_coefficient_m_s=normalized["mass_transfer_coefficient_m_s"],
            sorption_rate_s_minus_1=normalized["sorption_rate_s_minus_1"],
            desorption_rate_s_minus_1=normalized["desorption_rate_s_minus_1"],
            sink_rate_s_minus_1=normalized["sink_rate_s_minus_1"],
            matrix_feedback_exponent=normalized["matrix_feedback_exponent"],
            relative_parameter_uncertainty=normalized["relative_parameter_uncertainty"],
            parameter_source_id=normalized["parameter_source_id"],
            parameter_source_sha256=normalized["parameter_source_sha256"],
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise DynamicReleaseContractError(
                "dynamic component content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class SubstrateModelParameters:
    """One exact substrate-kind parameterization with no transfer authority."""

    model_id: str
    model_version: str
    substrate_kind: ApplicationEnvironmentKind
    authority: DynamicParameterAuthority
    calibration_receipt_sha256: str | None
    cross_substrate_transfer_allowed: bool
    reference_temperature_k: float
    reference_airflow_m_s: float
    reference_relative_humidity: float
    temperature_coefficient_per_k: float
    airflow_sensitivity_s_m: float
    humidity_sensitivity: float
    components: tuple[DynamicComponentParameters, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", _nonblank(self.model_id, "model_id"))
        object.__setattr__(
            self,
            "model_version",
            _nonblank(self.model_version, "model_version"),
        )
        _enum(ApplicationEnvironmentKind, self.substrate_kind, "substrate_kind")
        _enum(DynamicParameterAuthority, self.authority, "authority")
        if self.authority is not DynamicParameterAuthority.SIMULATION_ONLY_UNCALIBRATED:
            raise DynamicReleaseContractError(
                "C6 parameter authority must be SIMULATION_ONLY_UNCALIBRATED"
            )
        if self.calibration_receipt_sha256 is not None:
            raise DynamicReleaseContractError(
                "an uncalibrated C6 substrate model cannot carry a calibration receipt"
            )
        cross_transfer = _boolean(
            self.cross_substrate_transfer_allowed,
            "cross_substrate_transfer_allowed",
        )
        if cross_transfer:
            raise DynamicReleaseContractError("cross-substrate calibration transfer is forbidden")
        object.__setattr__(self, "cross_substrate_transfer_allowed", cross_transfer)
        object.__setattr__(
            self,
            "reference_temperature_k",
            _positive(self.reference_temperature_k, "reference_temperature_k"),
        )
        object.__setattr__(
            self,
            "reference_airflow_m_s",
            _nonnegative(self.reference_airflow_m_s, "reference_airflow_m_s"),
        )
        object.__setattr__(
            self,
            "reference_relative_humidity",
            _fraction(
                self.reference_relative_humidity,
                "reference_relative_humidity",
            ),
        )
        for field_name in (
            "temperature_coefficient_per_k",
            "airflow_sensitivity_s_m",
        ):
            object.__setattr__(
                self,
                field_name,
                _nonnegative(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "humidity_sensitivity",
            _fraction(self.humidity_sensitivity, "humidity_sensitivity"),
        )
        if isinstance(self.components, (str, bytes)) or not isinstance(self.components, Sequence):
            raise DynamicReleaseContractError("components must be a sequence")
        components = tuple(self.components)
        if not components:
            raise DynamicReleaseContractError("components must not be empty")
        if any(not isinstance(item, DynamicComponentParameters) for item in components):
            raise DynamicReleaseContractError("components must contain DynamicComponentParameters")
        ids = tuple(item.component_id for item in components)
        if len(ids) != len(set(ids)):
            raise DynamicReleaseContractError("components contains a duplicate component_id")
        components = tuple(
            sorted(components, key=lambda item: (item.component_id.casefold(), item.component_id))
        )
        self._validate_geometry(components)
        object.__setattr__(self, "components", components)
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    def _validate_geometry(
        self,
        components: tuple[DynamicComponentParameters, ...],
    ) -> None:
        if self.substrate_kind is _SEALED_KIND:
            for item in components:
                if item.sealed_transfer_rate_s_minus_1 is None:
                    raise DynamicReleaseContractError(
                        "sealed substrate parameters require a sealed transfer rate"
                    )
                if (
                    item.diffusion_coefficient_m2_s is not None
                    or item.mass_transfer_coefficient_m_s is not None
                ):
                    raise DynamicReleaseContractError(
                        "sealed substrate parameters cannot contain finite-film coefficients"
                    )
                if any(
                    value != 0.0
                    for value in (
                        item.sorption_rate_s_minus_1,
                        item.desorption_rate_s_minus_1,
                        item.sink_rate_s_minus_1,
                    )
                ):
                    raise DynamicReleaseContractError(
                        "sealed substrate parameters cannot contain sorption, desorption, or sink rates"
                    )
            return

        for item in components:
            if item.sealed_transfer_rate_s_minus_1 is not None:
                raise DynamicReleaseContractError(
                    "finite-film substrate parameters cannot contain a sealed transfer rate"
                )
            if (
                item.diffusion_coefficient_m2_s is None
                or item.mass_transfer_coefficient_m_s is None
            ):
                raise DynamicReleaseContractError(
                    "finite-film substrate parameters require diffusion and mass-transfer coefficients"
                )
            if self.substrate_kind is _OPEN_KIND and (
                item.sorption_rate_s_minus_1 != 0.0 or item.desorption_rate_s_minus_1 != 0.0
            ):
                raise DynamicReleaseContractError(
                    "open-surface parameters cannot contain substrate sorption"
                )

    @property
    def component_ids(self) -> tuple[str, ...]:
        return tuple(item.component_id for item in self.components)

    def component_for(self, component_id: str) -> DynamicComponentParameters:
        for item in self.components:
            if item.component_id == component_id:
                return item
        raise DynamicReleaseContractError(f"substrate model has no parameters for {component_id}")

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c6-substrate-model-parameters-v1",
            "model_id": self.model_id,
            "model_version": self.model_version,
            "substrate_kind": self.substrate_kind.value,
            "authority": self.authority.value,
            "calibration_receipt_sha256": self.calibration_receipt_sha256,
            "cross_substrate_transfer_allowed": self.cross_substrate_transfer_allowed,
            "reference_temperature_k": self.reference_temperature_k,
            "reference_airflow_m_s": self.reference_airflow_m_s,
            "reference_relative_humidity": self.reference_relative_humidity,
            "temperature_coefficient_per_k": self.temperature_coefficient_per_k,
            "airflow_sensitivity_s_m": self.airflow_sensitivity_s_m,
            "humidity_sensitivity": self.humidity_sensitivity,
            "components": [item.to_mapping() for item in self.components],
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> SubstrateModelParameters:
        normalized = _mapping(payload, "substrate model parameters")
        _exact_keys(
            normalized,
            {
                "schema",
                "model_id",
                "model_version",
                "substrate_kind",
                "authority",
                "calibration_receipt_sha256",
                "cross_substrate_transfer_allowed",
                "reference_temperature_k",
                "reference_airflow_m_s",
                "reference_relative_humidity",
                "temperature_coefficient_per_k",
                "airflow_sensitivity_s_m",
                "humidity_sensitivity",
                "components",
                "content_sha256",
            },
            "substrate model parameters",
        )
        if normalized["schema"] != "c6-substrate-model-parameters-v1":
            raise DynamicReleaseContractError(
                "substrate model schema must be c6-substrate-model-parameters-v1"
            )
        raw_components = normalized["components"]
        if not isinstance(raw_components, (list, tuple)):
            raise DynamicReleaseContractError("components must be a list")
        result = cls(
            model_id=normalized["model_id"],
            model_version=normalized["model_version"],
            substrate_kind=_enum_value(
                ApplicationEnvironmentKind,
                normalized["substrate_kind"],
                "substrate_kind",
            ),
            authority=_enum_value(
                DynamicParameterAuthority,
                normalized["authority"],
                "authority",
            ),
            calibration_receipt_sha256=normalized["calibration_receipt_sha256"],
            cross_substrate_transfer_allowed=normalized["cross_substrate_transfer_allowed"],
            reference_temperature_k=normalized["reference_temperature_k"],
            reference_airflow_m_s=normalized["reference_airflow_m_s"],
            reference_relative_humidity=normalized["reference_relative_humidity"],
            temperature_coefficient_per_k=normalized["temperature_coefficient_per_k"],
            airflow_sensitivity_s_m=normalized["airflow_sensitivity_s_m"],
            humidity_sensitivity=normalized["humidity_sensitivity"],
            components=tuple(
                DynamicComponentParameters.from_mapping(
                    _mapping(item, "dynamic component parameters")
                )
                for item in raw_components
            ),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise DynamicReleaseContractError(
                "substrate model content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class InitialCompartmentMass:
    component_id: str
    gas_mass_mg: float
    sorbed_mass_mg: float
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_id", _nonblank(self.component_id, "component_id"))
        object.__setattr__(
            self,
            "gas_mass_mg",
            _nonnegative(self.gas_mass_mg, "gas_mass_mg"),
        )
        object.__setattr__(
            self,
            "sorbed_mass_mg",
            _nonnegative(self.sorbed_mass_mg, "sorbed_mass_mg"),
        )
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c6-initial-compartment-mass-v1",
            "component_id": self.component_id,
            "gas_mass_mg": self.gas_mass_mg,
            "sorbed_mass_mg": self.sorbed_mass_mg,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> InitialCompartmentMass:
        normalized = _mapping(payload, "initial compartment mass")
        _exact_keys(
            normalized,
            {
                "schema",
                "component_id",
                "gas_mass_mg",
                "sorbed_mass_mg",
                "content_sha256",
            },
            "initial compartment mass",
        )
        if normalized["schema"] != "c6-initial-compartment-mass-v1":
            raise DynamicReleaseContractError(
                "initial mass schema must be c6-initial-compartment-mass-v1"
            )
        result = cls(
            component_id=normalized["component_id"],
            gas_mass_mg=normalized["gas_mass_mg"],
            sorbed_mass_mg=normalized["sorbed_mass_mg"],
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise DynamicReleaseContractError(
                "initial mass content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class DynamicReleaseInputSet:
    """Exact matrix/environment-bound state-machine input snapshot."""

    input_set_id: str
    matrix_sha256: str
    environment_sha256: str
    substrate_model: SubstrateModelParameters
    initial_masses: tuple[InitialCompartmentMass, ...]
    duration_s: float
    time_step_s: float
    mass_tolerance_mg: float
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "input_set_id",
            _nonblank(self.input_set_id, "input_set_id"),
        )
        object.__setattr__(
            self,
            "matrix_sha256",
            _sha256(self.matrix_sha256, "matrix_sha256"),
        )
        object.__setattr__(
            self,
            "environment_sha256",
            _sha256(self.environment_sha256, "environment_sha256"),
        )
        if not isinstance(self.substrate_model, SubstrateModelParameters):
            raise DynamicReleaseContractError("substrate_model must be SubstrateModelParameters")
        if isinstance(self.initial_masses, (str, bytes)) or not isinstance(
            self.initial_masses, Sequence
        ):
            raise DynamicReleaseContractError("initial_masses must be a sequence")
        initial_masses = tuple(self.initial_masses)
        if not initial_masses:
            raise DynamicReleaseContractError("initial_masses must not be empty")
        if any(not isinstance(item, InitialCompartmentMass) for item in initial_masses):
            raise DynamicReleaseContractError(
                "initial_masses must contain InitialCompartmentMass values"
            )
        ids = tuple(item.component_id for item in initial_masses)
        if len(ids) != len(set(ids)):
            raise DynamicReleaseContractError("initial_masses contains a duplicate component_id")
        if set(ids) != set(self.substrate_model.component_ids):
            raise DynamicReleaseContractError(
                "initial_masses component IDs must exactly match substrate parameters"
            )
        initial_masses = tuple(
            sorted(
                initial_masses,
                key=lambda item: (item.component_id.casefold(), item.component_id),
            )
        )
        object.__setattr__(self, "initial_masses", initial_masses)
        duration = _positive(self.duration_s, "duration_s")
        step = _positive(self.time_step_s, "time_step_s")
        raw_steps = duration / step
        rounded_steps = round(raw_steps)
        if not math.isclose(raw_steps, rounded_steps, rel_tol=0.0, abs_tol=1e-12):
            raise DynamicReleaseContractError(
                "duration_s must contain an integer number of time steps"
            )
        if rounded_steps > _MAX_STEPS:
            raise DynamicReleaseContractError("time grid must not exceed 10,000 steps")
        object.__setattr__(self, "duration_s", duration)
        object.__setattr__(self, "time_step_s", step)
        object.__setattr__(
            self,
            "mass_tolerance_mg",
            _nonnegative(self.mass_tolerance_mg, "mass_tolerance_mg"),
        )
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    @property
    def step_count(self) -> int:
        return round(self.duration_s / self.time_step_s)

    def initial_mass_for(self, component_id: str) -> InitialCompartmentMass:
        for item in self.initial_masses:
            if item.component_id == component_id:
                return item
        raise DynamicReleaseContractError(f"initial compartment mass is missing for {component_id}")

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c6-dynamic-release-input-set-v1",
            "input_set_id": self.input_set_id,
            "matrix_sha256": self.matrix_sha256,
            "environment_sha256": self.environment_sha256,
            "substrate_model": self.substrate_model.to_mapping(),
            "initial_masses": [item.to_mapping() for item in self.initial_masses],
            "duration_s": self.duration_s,
            "time_step_s": self.time_step_s,
            "mass_tolerance_mg": self.mass_tolerance_mg,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    def to_model_input_reference(self) -> ModelInputReference:
        return ModelInputReference(
            role=C6_INPUT_ROLE,
            input_id=self.input_set_id,
            content_sha256=self.content_sha256,
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> DynamicReleaseInputSet:
        normalized = _mapping(payload, "dynamic release input set")
        _exact_keys(
            normalized,
            {
                "schema",
                "input_set_id",
                "matrix_sha256",
                "environment_sha256",
                "substrate_model",
                "initial_masses",
                "duration_s",
                "time_step_s",
                "mass_tolerance_mg",
                "content_sha256",
            },
            "dynamic release input set",
        )
        if normalized["schema"] != "c6-dynamic-release-input-set-v1":
            raise DynamicReleaseContractError(
                "input-set schema must be c6-dynamic-release-input-set-v1"
            )
        raw_initial = normalized["initial_masses"]
        if not isinstance(raw_initial, (list, tuple)):
            raise DynamicReleaseContractError("initial_masses must be a list")
        result = cls(
            input_set_id=normalized["input_set_id"],
            matrix_sha256=normalized["matrix_sha256"],
            environment_sha256=normalized["environment_sha256"],
            substrate_model=SubstrateModelParameters.from_mapping(
                _mapping(normalized["substrate_model"], "substrate_model")
            ),
            initial_masses=tuple(
                InitialCompartmentMass.from_mapping(_mapping(item, "initial compartment mass"))
                for item in raw_initial
            ),
            duration_s=normalized["duration_s"],
            time_step_s=normalized["time_step_s"],
            mass_tolerance_mg=normalized["mass_tolerance_mg"],
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise DynamicReleaseContractError(
                "input-set content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class ComponentCompartmentState:
    """One component's fully accounted mass state at one time."""

    component_id: str
    condensed_mass_mg: float
    gas_mass_mg: float
    sorbed_mass_mg: float
    sink_mass_mg: float
    initial_total_mass_mg: float
    effective_condensed_to_gas_rate_s_minus_1: float
    mass_balance_abs_error_mg: float
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_id", _nonblank(self.component_id, "component_id"))
        for field_name in (
            "condensed_mass_mg",
            "gas_mass_mg",
            "sorbed_mass_mg",
            "sink_mass_mg",
            "initial_total_mass_mg",
            "effective_condensed_to_gas_rate_s_minus_1",
            "mass_balance_abs_error_mg",
        ):
            object.__setattr__(
                self,
                field_name,
                _nonnegative(getattr(self, field_name), field_name),
            )
        computed_error = abs(
            math.fsum(
                (
                    self.condensed_mass_mg,
                    self.gas_mass_mg,
                    self.sorbed_mass_mg,
                    self.sink_mass_mg,
                )
            )
            - self.initial_total_mass_mg
        )
        if not math.isclose(
            computed_error,
            self.mass_balance_abs_error_mg,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise DynamicReleaseContractError(
                "reported component mass balance error does not match compartments"
            )
        if computed_error > _OUTPUT_CLOSURE_TOLERANCE_MG:
            raise DynamicReleaseContractError("component mass balance does not close")
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    @property
    def total_mass_mg(self) -> float:
        return math.fsum(
            (
                self.condensed_mass_mg,
                self.gas_mass_mg,
                self.sorbed_mass_mg,
                self.sink_mass_mg,
            )
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c6-component-compartment-state-v1",
            "component_id": self.component_id,
            "condensed_mass_mg": self.condensed_mass_mg,
            "gas_mass_mg": self.gas_mass_mg,
            "sorbed_mass_mg": self.sorbed_mass_mg,
            "sink_mass_mg": self.sink_mass_mg,
            "initial_total_mass_mg": self.initial_total_mass_mg,
            "effective_condensed_to_gas_rate_s_minus_1": (
                self.effective_condensed_to_gas_rate_s_minus_1
            ),
            "mass_balance_abs_error_mg": self.mass_balance_abs_error_mg,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class DynamicTrajectoryFrame:
    """One conservative state snapshot and its physical summaries."""

    time_s: float
    matrix_solvent_fraction: float
    film_thickness_m: float | None
    gas_concentration_mg_m3: float | None
    components: tuple[ComponentCompartmentState, ...]
    max_abs_mass_error_mg: float
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "time_s", _nonnegative(self.time_s, "time_s"))
        object.__setattr__(
            self,
            "matrix_solvent_fraction",
            _fraction(self.matrix_solvent_fraction, "matrix_solvent_fraction"),
        )
        object.__setattr__(
            self,
            "film_thickness_m",
            _optional_nonnegative(self.film_thickness_m, "film_thickness_m"),
        )
        object.__setattr__(
            self,
            "gas_concentration_mg_m3",
            _optional_nonnegative(
                self.gas_concentration_mg_m3,
                "gas_concentration_mg_m3",
            ),
        )
        if isinstance(self.components, (str, bytes)) or not isinstance(self.components, Sequence):
            raise DynamicReleaseContractError("frame components must be a sequence")
        components = tuple(self.components)
        if not components or any(
            not isinstance(item, ComponentCompartmentState) for item in components
        ):
            raise DynamicReleaseContractError(
                "frame components must contain ComponentCompartmentState values"
            )
        ids = tuple(item.component_id for item in components)
        if len(ids) != len(set(ids)):
            raise DynamicReleaseContractError("frame components contains a duplicate component_id")
        components = tuple(
            sorted(components, key=lambda item: (item.component_id.casefold(), item.component_id))
        )
        object.__setattr__(self, "components", components)
        max_error = _nonnegative(
            self.max_abs_mass_error_mg,
            "max_abs_mass_error_mg",
        )
        observed_max = max(item.mass_balance_abs_error_mg for item in components)
        if not math.isclose(max_error, observed_max, rel_tol=0.0, abs_tol=1e-12):
            raise DynamicReleaseContractError(
                "frame max mass error does not match component states"
            )
        object.__setattr__(self, "max_abs_mass_error_mg", max_error)
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    @property
    def total_condensed_mass_mg(self) -> float:
        return math.fsum(item.condensed_mass_mg for item in self.components)

    @property
    def total_gas_mass_mg(self) -> float:
        return math.fsum(item.gas_mass_mg for item in self.components)

    @property
    def total_sorbed_mass_mg(self) -> float:
        return math.fsum(item.sorbed_mass_mg for item in self.components)

    @property
    def total_sink_mass_mg(self) -> float:
        return math.fsum(item.sink_mass_mg for item in self.components)

    @property
    def initial_total_mass_mg(self) -> float:
        return math.fsum(item.initial_total_mass_mg for item in self.components)

    @property
    def physical_persistence_fraction(self) -> float:
        if self.initial_total_mass_mg == 0.0:
            return 0.0
        return (
            self.total_condensed_mass_mg + self.total_sorbed_mass_mg
        ) / self.initial_total_mass_mg

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c6-dynamic-trajectory-frame-v1",
            "time_s": self.time_s,
            "matrix_solvent_fraction": self.matrix_solvent_fraction,
            "film_thickness_m": self.film_thickness_m,
            "gas_concentration_mg_m3": self.gas_concentration_mg_m3,
            "total_condensed_mass_mg": self.total_condensed_mass_mg,
            "total_gas_mass_mg": self.total_gas_mass_mg,
            "total_sorbed_mass_mg": self.total_sorbed_mass_mg,
            "total_sink_mass_mg": self.total_sink_mass_mg,
            "initial_total_mass_mg": self.initial_total_mass_mg,
            "physical_persistence_fraction": self.physical_persistence_fraction,
            "max_abs_mass_error_mg": self.max_abs_mass_error_mg,
            "components": [item.to_mapping() for item in self.components],
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class ScenarioTrajectory:
    scenario: RateScenario
    frames: tuple[DynamicTrajectoryFrame, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        _enum(RateScenario, self.scenario, "scenario")
        if isinstance(self.frames, (str, bytes)) or not isinstance(self.frames, Sequence):
            raise DynamicReleaseContractError("frames must be a sequence")
        frames = tuple(self.frames)
        if not frames or any(not isinstance(item, DynamicTrajectoryFrame) for item in frames):
            raise DynamicReleaseContractError("frames must contain DynamicTrajectoryFrame values")
        times = tuple(item.time_s for item in frames)
        if times[0] != 0.0 or any(later <= earlier for earlier, later in zip(times, times[1:])):
            raise DynamicReleaseContractError(
                "trajectory frame times must start at zero and strictly increase"
            )
        component_ids = tuple(item.component_id for item in frames[0].components)
        if any(
            tuple(item.component_id for item in frame.components) != component_ids
            for frame in frames
        ):
            raise DynamicReleaseContractError(
                "trajectory frames must retain an exact component set"
            )
        object.__setattr__(self, "frames", frames)
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    @property
    def max_abs_mass_error_mg(self) -> float:
        return max(item.max_abs_mass_error_mg for item in self.frames)

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c6-scenario-trajectory-v1",
            "scenario": self.scenario.value,
            "max_abs_mass_error_mg": self.max_abs_mass_error_mg,
            "frames": [item.to_mapping() for item in self.frames],
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}


@dataclass(frozen=True, slots=True)
class SensitivityEnvelopeFrame:
    time_s: float
    headspace_mass_min_mg: float
    headspace_mass_max_mg: float
    released_sink_min_mg: float
    released_sink_max_mg: float
    persistence_fraction_min: float
    persistence_fraction_max: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "time_s", _nonnegative(self.time_s, "time_s"))
        for field_name in (
            "headspace_mass_min_mg",
            "headspace_mass_max_mg",
            "released_sink_min_mg",
            "released_sink_max_mg",
        ):
            object.__setattr__(
                self,
                field_name,
                _nonnegative(getattr(self, field_name), field_name),
            )
        for field_name in (
            "persistence_fraction_min",
            "persistence_fraction_max",
        ):
            object.__setattr__(
                self,
                field_name,
                _fraction(getattr(self, field_name), field_name),
            )
        if self.headspace_mass_min_mg > self.headspace_mass_max_mg:
            raise DynamicReleaseContractError("headspace sensitivity bounds are reversed")
        if self.released_sink_min_mg > self.released_sink_max_mg:
            raise DynamicReleaseContractError("sink sensitivity bounds are reversed")
        if self.persistence_fraction_min > self.persistence_fraction_max:
            raise DynamicReleaseContractError("persistence sensitivity bounds are reversed")

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema": "c6-sensitivity-envelope-frame-v1",
            "time_s": self.time_s,
            "headspace_mass_min_mg": self.headspace_mass_min_mg,
            "headspace_mass_max_mg": self.headspace_mass_max_mg,
            "released_sink_min_mg": self.released_sink_min_mg,
            "released_sink_max_mg": self.released_sink_max_mg,
            "persistence_fraction_min": self.persistence_fraction_min,
            "persistence_fraction_max": self.persistence_fraction_max,
        }


@dataclass(frozen=True, slots=True)
class DynamicReleaseSimulation:
    substrate_kind: ApplicationEnvironmentKind
    authority: DynamicParameterAuthority
    modeled_layers: tuple[PhysicalProcessLayer, ...]
    excluded_sensory_layers: tuple[PhysicalProcessLayer, ...]
    output_labels: tuple[PhysicalTrajectoryLabel, ...]
    scenarios: tuple[ScenarioTrajectory, ...]
    sensitivity_envelope: tuple[SensitivityEnvelopeFrame, ...]
    uncertainty_interpretation: str
    empirical_metrics_present: bool
    empirical_promotion_allowed: bool
    assumptions: tuple[str, ...]
    input_set_sha256: str
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        _enum(ApplicationEnvironmentKind, self.substrate_kind, "substrate_kind")
        _enum(DynamicParameterAuthority, self.authority, "authority")
        if self.authority is not DynamicParameterAuthority.SIMULATION_ONLY_UNCALIBRATED:
            raise DynamicReleaseContractError("simulation authority must remain uncalibrated")
        expected_modeled = tuple(PhysicalProcessLayer)[:4]
        expected_excluded = tuple(PhysicalProcessLayer)[4:]
        if tuple(self.modeled_layers) != expected_modeled:
            raise DynamicReleaseContractError("modeled physical layers are not exact")
        if tuple(self.excluded_sensory_layers) != expected_excluded:
            raise DynamicReleaseContractError("excluded sensory layers are not exact")
        if tuple(self.output_labels) != PERMITTED_C6_OUTPUT_LABELS:
            raise DynamicReleaseContractError("C6 output labels are not exact")
        scenarios = tuple(self.scenarios)
        if {item.scenario for item in scenarios} != set(RateScenario) or len(scenarios) != 3:
            raise DynamicReleaseContractError(
                "simulation must contain exactly one trajectory per rate scenario"
            )
        scenarios = tuple(sorted(scenarios, key=lambda item: item.scenario.value))
        frame_counts = {len(item.frames) for item in scenarios}
        if len(frame_counts) != 1:
            raise DynamicReleaseContractError("scenario frame counts must match")
        object.__setattr__(self, "scenarios", scenarios)
        envelope = tuple(self.sensitivity_envelope)
        if len(envelope) != len(scenarios[0].frames):
            raise DynamicReleaseContractError(
                "sensitivity envelope must align with scenario frames"
            )
        object.__setattr__(self, "sensitivity_envelope", envelope)
        interpretation = _nonblank(
            self.uncertainty_interpretation,
            "uncertainty_interpretation",
        )
        if interpretation != "DETERMINISTIC_PARAMETER_SENSITIVITY_NOT_STATISTICAL_INTERVAL":
            raise DynamicReleaseContractError(
                "uncertainty interpretation must reject statistical coverage"
            )
        object.__setattr__(self, "uncertainty_interpretation", interpretation)
        if _boolean(self.empirical_metrics_present, "empirical_metrics_present"):
            raise DynamicReleaseContractError("C6 cannot report empirical metrics")
        if _boolean(self.empirical_promotion_allowed, "empirical_promotion_allowed"):
            raise DynamicReleaseContractError("C6 cannot permit empirical promotion")
        assumptions = tuple(_nonblank(item, "assumption") for item in self.assumptions)
        if not assumptions or len(assumptions) != len(set(assumptions)):
            raise DynamicReleaseContractError("assumptions must be nonempty and unique")
        object.__setattr__(self, "assumptions", assumptions)
        object.__setattr__(
            self,
            "input_set_sha256",
            _sha256(self.input_set_sha256, "input_set_sha256"),
        )
        object.__setattr__(self, "content_sha256", stable_json_hash(self._content_mapping()))

    def scenario(self, scenario: RateScenario) -> ScenarioTrajectory:
        for item in self.scenarios:
            if item.scenario is scenario:
                return item
        raise DynamicReleaseContractError(f"missing trajectory for {scenario.value}")

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c6-dynamic-release-simulation-v1",
            "substrate_kind": self.substrate_kind.value,
            "authority": self.authority.value,
            "modeled_layers": [item.value for item in self.modeled_layers],
            "excluded_sensory_layers": [item.value for item in self.excluded_sensory_layers],
            "output_labels": [item.value for item in self.output_labels],
            "scenarios": [item.to_mapping() for item in self.scenarios],
            "sensitivity_envelope": [item.to_mapping() for item in self.sensitivity_envelope],
            "uncertainty_interpretation": self.uncertainty_interpretation,
            "empirical_metrics_present": self.empirical_metrics_present,
            "empirical_promotion_allowed": self.empirical_promotion_allowed,
            "assumptions": list(self.assumptions),
            "input_set_sha256": self.input_set_sha256,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}


@dataclass(slots=True)
class _MutableComponentState:
    component_id: str
    condensed_mass_mg: float
    gas_mass_mg: float
    sorbed_mass_mg: float
    sink_mass_mg: float
    initial_total_mass_mg: float


def _scenario_multiplier(
    parameters: DynamicComponentParameters,
    scenario: RateScenario,
) -> float:
    if scenario is RateScenario.LOWER_RATE:
        return 1.0 - parameters.relative_parameter_uncertainty
    if scenario is RateScenario.UPPER_RATE:
        return 1.0 + parameters.relative_parameter_uncertainty
    return 1.0


def _hazard_fraction(rate_s_minus_1: float, time_step_s: float) -> float:
    rate = _nonnegative(rate_s_minus_1, "effective rate")
    step = _positive(time_step_s, "time_step_s")
    exponent = rate * step
    if not math.isfinite(exponent):
        return 1.0
    return -math.expm1(-exponent)


def _clean_mass(value: float, field_name: str) -> float:
    if not math.isfinite(value):
        raise DynamicReleaseContractError(f"{field_name} became non-finite")
    if value < -_MACHINE_NEGATIVE_TOLERANCE_MG:
        raise DynamicReleaseContractError(f"{field_name} became negative")
    return 0.0 if value < 0.0 else value


def _environment_values(
    environment: ApplicationEnvironment,
) -> tuple[float, float, float]:
    if environment.temperature is None:
        raise DynamicReleaseContractError("environment temperature is missing")
    if environment.airflow is None:
        raise DynamicReleaseContractError("environment airflow is missing")
    if environment.relative_humidity is None:
        raise DynamicReleaseContractError("environment relative humidity is missing")
    return (
        environment.temperature.value,
        environment.airflow.value,
        environment.relative_humidity.value,
    )


def _environment_factor(
    environment: ApplicationEnvironment,
    model: SubstrateModelParameters,
) -> float:
    temperature, airflow, humidity = _environment_values(environment)
    try:
        temperature_factor = math.exp(
            model.temperature_coefficient_per_k * (temperature - model.reference_temperature_k)
        )
    except OverflowError as exc:
        raise DynamicReleaseContractError(
            "temperature sensitivity produced a non-finite factor"
        ) from exc
    airflow_factor = 1.0 + model.airflow_sensitivity_s_m * (airflow - model.reference_airflow_m_s)
    humidity_factor = 1.0 - model.humidity_sensitivity * (
        humidity - model.reference_relative_humidity
    )
    result = temperature_factor * max(0.0, airflow_factor) * max(0.0, humidity_factor)
    if not math.isfinite(result):
        raise DynamicReleaseContractError("environment sensitivity produced a non-finite factor")
    return result


def _matrix_solvent_fraction(
    states: Mapping[str, _MutableComponentState],
    solvent_ids: frozenset[str],
) -> float:
    condensed_total = math.fsum(item.condensed_mass_mg for item in states.values())
    if condensed_total <= 0.0:
        return 0.0
    solvent_total = math.fsum(
        states[component_id].condensed_mass_mg for component_id in solvent_ids
    )
    return min(1.0, max(0.0, solvent_total / condensed_total))


def _film_thickness(
    environment: ApplicationEnvironment,
    states: Mapping[str, _MutableComponentState],
    initial_condensed_mass_mg: float,
) -> float | None:
    if environment.kind is _SEALED_KIND:
        return None
    if environment.film_thickness is None:
        raise DynamicReleaseContractError("finite-film thickness is missing")
    condensed_total = math.fsum(item.condensed_mass_mg for item in states.values())
    if initial_condensed_mass_mg <= 0.0:
        raise DynamicReleaseContractError("initial condensed mass must be positive")
    return environment.film_thickness.value * (condensed_total / initial_condensed_mass_mg)


def _effective_condensed_to_gas_rate(
    parameters: DynamicComponentParameters,
    model: SubstrateModelParameters,
    environment: ApplicationEnvironment,
    scenario: RateScenario,
    film_thickness_m: float | None,
    current_solvent_fraction: float,
    initial_solvent_fraction: float,
) -> float:
    multiplier = _scenario_multiplier(parameters, scenario)
    if environment.kind is _SEALED_KIND:
        if parameters.sealed_transfer_rate_s_minus_1 is None:
            raise DynamicReleaseContractError("sealed transfer rate is missing")
        transport_rate = parameters.sealed_transfer_rate_s_minus_1 * multiplier
    else:
        if film_thickness_m is None:
            raise DynamicReleaseContractError("finite-film thickness is missing")
        if film_thickness_m <= 0.0:
            return 0.0
        if (
            parameters.diffusion_coefficient_m2_s is None
            or parameters.mass_transfer_coefficient_m_s is None
        ):
            raise DynamicReleaseContractError("finite-film transport coefficients are missing")
        diffusion_rate = (
            parameters.diffusion_coefficient_m2_s
            * multiplier
            / (film_thickness_m * film_thickness_m)
        )
        boundary_rate = parameters.mass_transfer_coefficient_m_s * multiplier / film_thickness_m
        denominator = diffusion_rate + boundary_rate
        transport_rate = 0.0 if denominator <= 0.0 else diffusion_rate * boundary_rate / denominator
    feedback_ratio = (
        0.0
        if initial_solvent_fraction <= 0.0
        else current_solvent_fraction / initial_solvent_fraction
    )
    feedback = feedback_ratio**parameters.matrix_feedback_exponent
    result = (
        transport_rate
        * parameters.equilibrium_release_factor
        * parameters.activity_coefficient
        * feedback
        * _environment_factor(environment, model)
    )
    if not math.isfinite(result) or result < 0.0:
        raise DynamicReleaseContractError("effective condensed-to-gas rate became invalid")
    return result


def _context_findings(
    matrix: MatrixComposition,
    environment: ApplicationEnvironment,
    input_set: DynamicReleaseInputSet,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    missing: set[str] = set()
    outside: set[str] = set()

    if matrix.content_sha256 != input_set.matrix_sha256:
        missing.add("matrix:content_binding")
    if environment.content_sha256 != input_set.environment_sha256:
        missing.add("environment:content_binding")
    if environment.kind is not input_set.substrate_model.substrate_kind:
        missing.add("substrate_model:exact_kind_binding")
    if matrix.completeness is not CompositionCompleteness.EXACT or matrix.missing_fields:
        missing.add("matrix:exact_composition")
    if environment.missing_fields:
        missing.update(f"environment:{item.value}" for item in environment.missing_fields)

    matrix_ids = {item.component_id for item in matrix.components}
    if matrix_ids != set(input_set.substrate_model.component_ids):
        missing.add("substrate_model:component_binding")
    if matrix_ids != {item.component_id for item in input_set.initial_masses}:
        missing.add("initial_masses:component_binding")

    if matrix.stage not in {MatrixStage.FINISHED_PERFUME, MatrixStage.APPLICATION_FILM}:
        outside.add(f"matrix stage {matrix.stage.value} is unsupported")
    if environment.kind is _SEALED_KIND and matrix.stage is not MatrixStage.FINISHED_PERFUME:
        outside.add("sealed-vial simulation requires a FINISHED_PERFUME matrix")
    if environment.kind is not _SEALED_KIND and matrix.stage is not MatrixStage.APPLICATION_FILM:
        outside.add("finite-film simulation requires an APPLICATION_FILM matrix")

    bases = {item.basis for item in matrix.components}
    if bases != {MatrixQuantityBasis.MASS}:
        outside.add("matrix components must use absolute MASS basis")
    if {item.quantity.unit for item in matrix.components} != {"mg"}:
        outside.add("matrix component masses must use mg")
    if matrix.total_mass is None:
        missing.add("matrix:total_mass")
    elif matrix.total_mass.unit != "mg":
        outside.add("matrix total mass must use mg")
    else:
        component_total = math.fsum(item.quantity.value for item in matrix.components)
        if abs(component_total - matrix.total_mass.value) > input_set.mass_tolerance_mg:
            outside.add("matrix component masses do not close against total mass")

    if environment.dose is None:
        missing.add("environment:dose")
    elif environment.dose.unit != "mg":
        outside.add("environment dose must use mg")
    elif (
        matrix.total_mass is not None
        and matrix.total_mass.unit == "mg"
        and abs(environment.dose.value - matrix.total_mass.value) > input_set.mass_tolerance_mg
    ):
        outside.add("environment dose does not match matrix total mass")

    matrix_temperature = matrix.temperature
    if matrix_temperature is None:
        missing.add("matrix:temperature")
    elif matrix_temperature.unit != "K":
        outside.add("matrix temperature must use K")

    if environment.temperature is None:
        missing.add("environment:temperature")
    elif environment.temperature.unit != "K":
        outside.add("environment temperature must use K")
    elif (
        matrix_temperature is not None
        and matrix_temperature.unit == "K"
        and not math.isclose(
            matrix_temperature.value,
            environment.temperature.value,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    ):
        outside.add("matrix and environment temperatures must match in K")
    if environment.airflow is None:
        missing.add("environment:airflow")
    elif environment.airflow.unit != "m/s":
        outside.add("environment airflow must use m/s")
    if environment.relative_humidity is None:
        missing.add("environment:relative_humidity")
    elif environment.relative_humidity.unit != "1":
        outside.add("environment relative humidity must use fraction unit 1")

    if environment.kind is _SEALED_KIND:
        if environment.headspace_volume is None:
            missing.add("environment:headspace_volume")
        elif environment.headspace_volume.unit != "m3":
            outside.add("sealed headspace volume must use m3")
        elif environment.headspace_volume.value <= 0.0:
            outside.add("sealed headspace volume must be positive")
        if environment.vessel_volume is None:
            missing.add("environment:vessel_volume")
        elif environment.vessel_volume.unit != "m3":
            outside.add("sealed vessel volume must use m3")
        elif environment.vessel_volume.value <= 0.0:
            outside.add("sealed vessel volume must be positive")
        if (
            environment.headspace_volume is not None
            and environment.vessel_volume is not None
            and environment.headspace_volume.unit == "m3"
            and environment.vessel_volume.unit == "m3"
            and environment.headspace_volume.value > environment.vessel_volume.value
        ):
            outside.add("sealed headspace volume cannot exceed vessel volume")
        if environment.airflow is not None and environment.airflow.value != 0.0:
            outside.add("sealed-vial airflow must be zero")
    else:
        if environment.area is None:
            missing.add("environment:area")
        elif environment.area.unit != "m2":
            outside.add("finite-film area must use m2")
        elif environment.area.value <= 0.0:
            outside.add("finite-film area must be positive")
        if environment.film_thickness is None:
            missing.add("environment:film_thickness")
        elif environment.film_thickness.unit != "m":
            outside.add("finite-film thickness must use m")
        elif environment.film_thickness.value <= 0.0:
            outside.add("finite-film thickness must be positive")
        if environment.kind in _SUBSTRATE_REQUIRED_KINDS and environment.substrate is None:
            missing.add("environment:substrate")

    return tuple(sorted(missing)), tuple(sorted(outside))


def _initial_states(
    matrix: MatrixComposition,
    input_set: DynamicReleaseInputSet,
) -> dict[str, _MutableComponentState]:
    states: dict[str, _MutableComponentState] = {}
    for component in matrix.components:
        initial = input_set.initial_mass_for(component.component_id)
        initial_total = math.fsum(
            (component.quantity.value, initial.gas_mass_mg, initial.sorbed_mass_mg)
        )
        states[component.component_id] = _MutableComponentState(
            component_id=component.component_id,
            condensed_mass_mg=component.quantity.value,
            gas_mass_mg=initial.gas_mass_mg,
            sorbed_mass_mg=initial.sorbed_mass_mg,
            sink_mass_mg=0.0,
            initial_total_mass_mg=initial_total,
        )
    return states


def _component_rates(
    states: Mapping[str, _MutableComponentState],
    input_set: DynamicReleaseInputSet,
    environment: ApplicationEnvironment,
    scenario: RateScenario,
    solvent_ids: frozenset[str],
    initial_solvent_fraction: float,
    initial_condensed_mass_mg: float,
) -> tuple[dict[str, float], float, float | None]:
    solvent_fraction = _matrix_solvent_fraction(states, solvent_ids)
    thickness = _film_thickness(
        environment,
        states,
        initial_condensed_mass_mg,
    )
    rates = {
        component_id: _effective_condensed_to_gas_rate(
            input_set.substrate_model.component_for(component_id),
            input_set.substrate_model,
            environment,
            scenario,
            thickness,
            solvent_fraction,
            initial_solvent_fraction,
        )
        for component_id in states
    }
    return rates, solvent_fraction, thickness


def _frame_from_states(
    *,
    time_s: float,
    states: Mapping[str, _MutableComponentState],
    rates: Mapping[str, float],
    solvent_fraction: float,
    film_thickness_m: float | None,
    environment: ApplicationEnvironment,
    tolerance_mg: float,
) -> DynamicTrajectoryFrame:
    component_states: list[ComponentCompartmentState] = []
    for component_id in sorted(states, key=lambda item: (item.casefold(), item)):
        state = states[component_id]
        error = abs(
            math.fsum(
                (
                    state.condensed_mass_mg,
                    state.gas_mass_mg,
                    state.sorbed_mass_mg,
                    state.sink_mass_mg,
                )
            )
            - state.initial_total_mass_mg
        )
        if error > tolerance_mg:
            raise DynamicReleaseContractError(f"component mass balance failed for {component_id}")
        component_states.append(
            ComponentCompartmentState(
                component_id=component_id,
                condensed_mass_mg=state.condensed_mass_mg,
                gas_mass_mg=state.gas_mass_mg,
                sorbed_mass_mg=state.sorbed_mass_mg,
                sink_mass_mg=state.sink_mass_mg,
                initial_total_mass_mg=state.initial_total_mass_mg,
                effective_condensed_to_gas_rate_s_minus_1=rates[component_id],
                mass_balance_abs_error_mg=error,
            )
        )
    total_gas = math.fsum(item.gas_mass_mg for item in component_states)
    gas_concentration: float | None = None
    if environment.kind is _SEALED_KIND:
        if environment.headspace_volume is None or environment.headspace_volume.value <= 0.0:
            raise DynamicReleaseContractError("sealed headspace volume is unavailable")
        gas_concentration = total_gas / environment.headspace_volume.value
    return DynamicTrajectoryFrame(
        time_s=time_s,
        matrix_solvent_fraction=solvent_fraction,
        film_thickness_m=film_thickness_m,
        gas_concentration_mg_m3=gas_concentration,
        components=tuple(component_states),
        max_abs_mass_error_mg=max(item.mass_balance_abs_error_mg for item in component_states),
    )


def _advance_states(
    states: Mapping[str, _MutableComponentState],
    input_set: DynamicReleaseInputSet,
    scenario: RateScenario,
    rates: Mapping[str, float],
) -> None:
    step = input_set.time_step_s
    model = input_set.substrate_model
    for component_id in sorted(states, key=lambda item: (item.casefold(), item)):
        state = states[component_id]
        parameters = model.component_for(component_id)
        multiplier = _scenario_multiplier(parameters, scenario)
        condensed_to_gas = state.condensed_mass_mg * _hazard_fraction(rates[component_id], step)
        desorbed_to_gas = state.sorbed_mass_mg * _hazard_fraction(
            parameters.desorption_rate_s_minus_1 * multiplier,
            step,
        )
        condensed = state.condensed_mass_mg - condensed_to_gas
        sorbed = state.sorbed_mass_mg - desorbed_to_gas
        gas_available = state.gas_mass_mg + condensed_to_gas + desorbed_to_gas

        sorption_rate = parameters.sorption_rate_s_minus_1 * multiplier
        sink_rate = parameters.sink_rate_s_minus_1 * multiplier
        combined_out_rate = sorption_rate + sink_rate
        total_gas_out = gas_available * _hazard_fraction(combined_out_rate, step)
        if combined_out_rate > 0.0:
            sorbed_from_gas = total_gas_out * sorption_rate / combined_out_rate
            sink_from_gas = total_gas_out * sink_rate / combined_out_rate
        else:
            sorbed_from_gas = 0.0
            sink_from_gas = 0.0
        sorbed += sorbed_from_gas
        gas = gas_available - total_gas_out
        sink = state.sink_mass_mg + sink_from_gas

        state.condensed_mass_mg = _clean_mass(condensed, "condensed mass")
        state.gas_mass_mg = _clean_mass(gas, "gas mass")
        state.sorbed_mass_mg = _clean_mass(sorbed, "sorbed mass")
        state.sink_mass_mg = _clean_mass(sink, "sink mass")
        error = abs(
            math.fsum(
                (
                    state.condensed_mass_mg,
                    state.gas_mass_mg,
                    state.sorbed_mass_mg,
                    state.sink_mass_mg,
                )
            )
            - state.initial_total_mass_mg
        )
        if error > input_set.mass_tolerance_mg:
            raise DynamicReleaseContractError(
                f"component mass balance failed after transition for {component_id}"
            )


def _simulate_scenario(
    matrix: MatrixComposition,
    environment: ApplicationEnvironment,
    input_set: DynamicReleaseInputSet,
    scenario: RateScenario,
) -> ScenarioTrajectory:
    states = _initial_states(matrix, input_set)
    initial_condensed_mass = math.fsum(item.condensed_mass_mg for item in states.values())
    solvent_ids = frozenset(
        item.component_id for item in matrix.components if item.role in _SOLVENT_ROLES
    )
    initial_solvent_fraction = _matrix_solvent_fraction(states, solvent_ids)
    frames: list[DynamicTrajectoryFrame] = []
    for step_index in range(input_set.step_count + 1):
        rates, solvent_fraction, thickness = _component_rates(
            states,
            input_set,
            environment,
            scenario,
            solvent_ids,
            initial_solvent_fraction,
            initial_condensed_mass,
        )
        frames.append(
            _frame_from_states(
                time_s=step_index * input_set.time_step_s,
                states=states,
                rates=rates,
                solvent_fraction=solvent_fraction,
                film_thickness_m=thickness,
                environment=environment,
                tolerance_mg=input_set.mass_tolerance_mg,
            )
        )
        if step_index < input_set.step_count:
            _advance_states(states, input_set, scenario, rates)
    return ScenarioTrajectory(scenario=scenario, frames=tuple(frames))


def _sensitivity_envelope(
    trajectories: tuple[ScenarioTrajectory, ...],
) -> tuple[SensitivityEnvelopeFrame, ...]:
    frames: list[SensitivityEnvelopeFrame] = []
    for index in range(len(trajectories[0].frames)):
        aligned = tuple(item.frames[index] for item in trajectories)
        gas = tuple(item.total_gas_mass_mg for item in aligned)
        sink = tuple(item.total_sink_mass_mg for item in aligned)
        persistence = tuple(item.physical_persistence_fraction for item in aligned)
        frames.append(
            SensitivityEnvelopeFrame(
                time_s=aligned[0].time_s,
                headspace_mass_min_mg=min(gas),
                headspace_mass_max_mg=max(gas),
                released_sink_min_mg=min(sink),
                released_sink_max_mg=max(sink),
                persistence_fraction_min=min(persistence),
                persistence_fraction_max=max(persistence),
            )
        )
    return tuple(frames)


def simulate_dynamic_release(
    matrix: MatrixComposition,
    environment: ApplicationEnvironment,
    input_set: DynamicReleaseInputSet,
) -> DynamicReleaseSimulation:
    """Run three deterministic conservative parameter-sensitivity scenarios."""

    if not isinstance(matrix, MatrixComposition):
        raise DynamicReleaseContractError("matrix must be a MatrixComposition")
    if not isinstance(environment, ApplicationEnvironment):
        raise DynamicReleaseContractError("environment must be an ApplicationEnvironment")
    if not isinstance(input_set, DynamicReleaseInputSet):
        raise DynamicReleaseContractError("input_set must be a DynamicReleaseInputSet")
    if matrix.content_sha256 != input_set.matrix_sha256:
        raise DynamicReleaseContractError("matrix hash does not match the C6 input set")
    if environment.content_sha256 != input_set.environment_sha256:
        raise DynamicReleaseContractError("environment hash does not match the C6 input set")
    missing, outside = _context_findings(matrix, environment, input_set)
    if missing or outside:
        detail = "; ".join((*missing, *outside))
        raise DynamicReleaseContractError(f"dynamic release context is not executable: {detail}")
    trajectories = tuple(
        _simulate_scenario(matrix, environment, input_set, scenario) for scenario in RateScenario
    )
    return DynamicReleaseSimulation(
        substrate_kind=environment.kind,
        authority=DynamicParameterAuthority.SIMULATION_ONLY_UNCALIBRATED,
        modeled_layers=tuple(PhysicalProcessLayer)[:4],
        excluded_sensory_layers=tuple(PhysicalProcessLayer)[4:],
        output_labels=PERMITTED_C6_OUTPUT_LABELS,
        scenarios=trajectories,
        sensitivity_envelope=_sensitivity_envelope(trajectories),
        uncertainty_interpretation=("DETERMINISTIC_PARAMETER_SENSITIVITY_NOT_STATISTICAL_INTERVAL"),
        empirical_metrics_present=False,
        empirical_promotion_allowed=False,
        assumptions=(
            "declared coefficients are uncalibrated simulation inputs",
            "bounded exponential hazards preserve nonnegative transfers",
            "finite-film area and density remain constant while thickness follows condensed mass",
            "activity coefficients are declared inputs rather than fitted values",
            "the explicit sink remains inside mass accounting",
            "the sensitivity envelope is not a confidence or credible interval",
            "physical persistence is residual condensed-plus-sorbed mass, not perception",
        ),
        input_set_sha256=input_set.content_sha256,
    )


def _dynamic_domain(input_set: DynamicReleaseInputSet) -> ApplicabilityDomain:
    kind = input_set.substrate_model.substrate_kind
    supported_stages = (
        (MatrixStage.FINISHED_PERFUME,) if kind is _SEALED_KIND else (MatrixStage.APPLICATION_FILM,)
    )
    return ApplicabilityDomain(
        domain_id=(
            f"c6-domain:{kind.value.lower()}:{input_set.substrate_model.content_sha256[:16]}"
        ),
        domain_version="1",
        supported_identity_ids=(),
        supported_chemical_classes=(),
        supported_functional_groups=(),
        supported_matrix_stages=supported_stages,
        matrix_range=CanonicalScope.from_mapping(
            {
                "composition_completeness": "EXACT",
                "component_basis": "MASS",
                "mass_unit": "mg",
                "implicit_unit_conversion": False,
            }
        ),
        concentration_range=None,
        temperature_range=None,
        pressure_range=None,
        supported_phase_behaviors=("single_liquid_phase",),
        supported_environment_kinds=(kind,),
        required_properties=(),
        training_calibration_domain=CanonicalScope.from_mapping(
            {
                "authority": "SIMULATION_ONLY_UNCALIBRATED",
                "training_data_sha256": None,
                "calibration_receipt_sha256": None,
                "cross_substrate_transfer_allowed": False,
                "c5_empirical_status": "BLOCKED_PENDING_DATA",
            }
        ),
        known_failure_modes=(
            "declared coefficients are not empirically calibrated",
            "constant-area and constant-density finite-film approximation",
            "activity coefficients are declared rather than dynamically fitted",
            "parameter sensitivity is not a statistical interval",
            "no sensory mapping is implemented",
            "no cross-substrate calibration transfer is permitted",
        ),
    )


def _dynamic_release(
    input_set: DynamicReleaseInputSet,
    *,
    code_commit: str,
    implementation_sha256: str,
) -> ModelRelease:
    equation_declaration = {
        "schema": "c6-conservative-compartment-equations-v1",
        "implementation_prefix": C6_MODEL_VERSION,
        "state_compartments": ["condensed", "gas", "sorbed", "explicit_sink"],
        "hazard_fraction": "1 - exp(-k * dt)",
        "finite_film_resistance": ("harmonic combination of D / h^2 and k_g / h"),
        "matrix_feedback": ("declared exponent on current-to-initial solvent fraction"),
        "uncertainty": "three deterministic rate-sensitivity scenarios",
        "mass_tolerance_mg": input_set.mass_tolerance_mg,
    }
    selector_version = (
        f"{C6_MODEL_VERSION}:"
        f"{input_set.substrate_model.substrate_kind.value.lower()}:"
        f"{input_set.substrate_model.content_sha256[:16]}"
    )
    return ModelRelease(
        selector=ModelSelector(
            family=ModelFamily.DYNAMIC_SEMI_EMPIRICAL_MODEL,
            model_version=selector_version,
        ),
        parameter_set_version="c6-conservative-compartment-equations-v1",
        code_commit=code_commit,
        implementation_sha256=implementation_sha256,
        parameter_set_sha256=stable_json_hash(equation_declaration),
        coefficient_set_sha256=input_set.substrate_model.content_sha256,
        decomposition_sha256=None,
        training_data_sha256=None,
        applicability_domain=_dynamic_domain(input_set),
        supported_operations=(
            ModelOperation.PREDICT_DYNAMIC_RELEASE,
            ModelOperation.PROPAGATE_UNCERTAINTY,
        ),
        availability=ModelAvailability.AVAILABLE,
        unavailable_reason=None,
        evidence_class=ModelEvidenceClass.UNVALIDATED,
        may_feed_oav_screening=False,
        permitted_claim_wording=(
            "simulation-only physical trajectory",
            "predicted headspace trajectory under declared parameters",
            "predicted release trajectory under declared parameters",
            "estimated physical persistence as residual mass fraction",
        ),
        forbidden_claim_wording=(
            "exact longevity",
            "sillage",
            "projection distance",
            "perceived intensity",
            "measured headspace",
            "calibrated release",
        ),
    )


class DynamicReleaseAdapter:
    """Exact-input C3 adapter for one substrate-bound C6 simulation release."""

    __slots__ = ("_input_set", "_release")

    def __init__(
        self,
        *,
        input_set: DynamicReleaseInputSet,
        code_commit: str,
        implementation_sha256: str,
    ) -> None:
        if not isinstance(input_set, DynamicReleaseInputSet):
            raise DynamicReleaseContractError("input_set must be a DynamicReleaseInputSet")
        self._input_set = input_set
        self._release = _dynamic_release(
            input_set,
            code_commit=code_commit,
            implementation_sha256=implementation_sha256,
        )

    @property
    def input_set(self) -> DynamicReleaseInputSet:
        return self._input_set

    @property
    def release(self) -> ModelRelease:
        return self._release

    def _input_reference_is_exact(self, request: VersionedModelRequest) -> bool:
        return request.input_references == (self.input_set.to_model_input_reference(),)

    def evaluate_applicability(
        self,
        request: VersionedModelRequest,
    ) -> ApplicabilityResult:
        if not isinstance(request, VersionedModelRequest):
            raise DynamicReleaseContractError("request must be a VersionedModelRequest")
        if request.requested_model != self.release.selector:
            raise DynamicReleaseContractError("request selector does not match the dynamic release")
        if request.operation not in {
            ModelOperation.PREDICT_DYNAMIC_RELEASE,
            ModelOperation.PROPAGATE_UNCERTAINTY,
        }:
            raise DynamicReleaseContractError(
                "dynamic release supports only trajectory and uncertainty operations"
            )
        missing, outside = _context_findings(
            request.context.matrix,
            request.context.environment,
            self.input_set,
        )
        missing_set = set(missing)
        outside_set = set(outside)
        if not self._input_reference_is_exact(request):
            missing_set.add("input_reference:c6_dynamic_release_input_set")
        if request.applicability_context.phase_behavior != "single_liquid_phase":
            outside_set.add("phase behavior must be single_liquid_phase")
        if "simulation_only_uncalibrated" not in set(
            request.applicability_context.training_calibration_tags
        ):
            missing_set.add("authority:simulation_only_uncalibrated")

        warnings = (
            "SIMULATION_ONLY_UNCALIBRATED",
            "C5_EMPIRICAL_STATUS_BLOCKED_PENDING_DATA",
            "SENSITIVITY_ENVELOPE_NOT_STATISTICAL_INTERVAL",
            "NO_SENSORY_MAPPING",
        )
        if missing_set:
            state = ApplicabilityState.INSUFFICIENT_INPUT
            reasons: tuple[str, ...] = ()
        elif outside_set:
            state = ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN
            reasons = tuple(sorted(outside_set))
        else:
            state = ApplicabilityState.IN_DOMAIN
            reasons = ()
        return ApplicabilityResult(
            state=state,
            domain_sha256=self.release.applicability_domain.content_sha256,
            request_sha256=request.content_sha256,
            reasons=reasons,
            missing_inputs=tuple(sorted(missing_set)),
            warnings=warnings,
        )

    def compute(
        self,
        request: VersionedModelRequest,
        applicability: ApplicabilityResult,
    ) -> ModelComputation:
        if applicability.state is not ApplicabilityState.IN_DOMAIN:
            raise DynamicReleaseContractError(
                "dynamic release cannot compute outside exact applicability"
            )
        if applicability.request_sha256 != request.content_sha256:
            raise DynamicReleaseContractError(
                "applicability request hash does not match the request"
            )
        simulation = simulate_dynamic_release(
            request.context.matrix,
            request.context.environment,
            self.input_set,
        )
        return ModelComputation(
            output=ModelOutput(
                quantity="predicted_physical_trajectories",
                unit="simulation-only",
                payload=CanonicalScope.from_mapping(simulation.to_mapping()),
            ),
            uncertainty=UncertaintyDescriptor.unknown(
                "C6 reports deterministic parameter sensitivity without statistical coverage"
            ),
            warnings=applicability.warnings,
        )


__all__ = [
    "C6_INPUT_ROLE",
    "C6_MODEL_VERSION",
    "PERMITTED_C6_OUTPUT_LABELS",
    "ComponentCompartmentState",
    "DynamicComponentParameters",
    "DynamicParameterAuthority",
    "DynamicReleaseAdapter",
    "DynamicReleaseContractError",
    "DynamicReleaseInputSet",
    "DynamicReleaseSimulation",
    "DynamicTrajectoryFrame",
    "InitialCompartmentMass",
    "PhysicalProcessLayer",
    "PhysicalTrajectoryLabel",
    "RateScenario",
    "ScenarioTrajectory",
    "SensitivityEnvelopeFrame",
    "SubstrateModelParameters",
    "simulate_dynamic_release",
]
