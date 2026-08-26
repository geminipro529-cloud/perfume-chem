"""Fail-closed equilibrium baselines and explicit C4 model withholding.

The only executable family in this module is the ideal-solution Raoult
comparison baseline.  It does not import or adapt the legacy heuristic
headspace path, evaluate C1 vapor-pressure equations, propagate uncertainty,
or authorize production/OAV use.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from engine.calibration.hashing import stable_json_hash
from engine.physics.matrix_environment import (
    ApplicationEnvironmentKind,
    CompositionCompleteness,
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
from engine.physics.properties import (
    CanonicalScope,
    PropertyConditions,
    PropertyIdentity,
    PropertyValueKind,
    SelectionStatus,
    SourceReference,
    ThermophysicalProperty,
    UncertaintyDescriptor,
)
from engine.physics.selection import (
    AuthorityState,
    InterpolationState,
    PropertyRequest,
    PropertySelectionResult,
)

C4_INPUT_ROLE = "c4_equilibrium_input_set"
IDEAL_RAOULT_MODEL_VERSION = "c4-ideal-raoult-v1"
_CLOSURE_TOLERANCE = 1e-12
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_SUPPORTED_BASES = frozenset(
    {
        MatrixQuantityBasis.MOLE_FRACTION,
        MatrixQuantityBasis.MASS_FRACTION,
        MatrixQuantityBasis.MASS,
        MatrixQuantityBasis.AMOUNT,
    }
)
_SUPPORTED_STAGES = (
    MatrixStage.STOCK_SOLUTION,
    MatrixStage.CONCENTRATE,
    MatrixStage.FINISHED_PERFUME,
)
_SUPPORTED_ENVIRONMENTS = (
    ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL,
    ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE,
)
_REQUIRED_PROPERTIES = (
    ThermophysicalProperty.VAPOR_PRESSURE,
    ThermophysicalProperty.MOLECULAR_WEIGHT,
)
_SINGLE_LIQUID_PHASE = "single_liquid_phase"
_C5_WARNING = "C5_UNCERTAINTY_PROPAGATION_REQUIRED"
_IDEAL_WARNING = "IDEAL_SOLUTION_GAMMA_EQUALS_ONE"


class EquilibriumModelContractError(ValueError):
    """A malformed C4 input, unsupported direct computation, or tampered payload."""


def _mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise EquilibriumModelContractError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise EquilibriumModelContractError(f"{field_name} keys must be strings")
    return dict(value)


def _exact_keys(
    payload: Mapping[str, Any],
    expected: set[str],
    field_name: str,
) -> None:
    missing = expected - set(payload)
    unknown = set(payload) - expected
    if missing:
        raise EquilibriumModelContractError(
            f"{field_name} missing fields: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise EquilibriumModelContractError(
            f"{field_name} contains unknown fields: {', '.join(sorted(unknown))}"
        )


def _nonblank(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EquilibriumModelContractError(f"{field_name} must not be blank")
    return value.strip()


def _finite(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise EquilibriumModelContractError(f"{field_name} must be finite")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise EquilibriumModelContractError(f"{field_name} must be finite") from exc
    if not math.isfinite(normalized):
        raise EquilibriumModelContractError(f"{field_name} must be finite")
    return normalized


def _positive(value: object, field_name: str) -> float:
    normalized = _finite(value, field_name)
    if normalized <= 0.0:
        raise EquilibriumModelContractError(f"{field_name} must be positive")
    return normalized


def _sha256(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise EquilibriumModelContractError(
            f"{field_name} must be a lowercase 64-character SHA-256"
        )
    return value


def _source_from_mapping(payload: Mapping[str, Any]) -> SourceReference:
    normalized = _mapping(payload, "source")
    _exact_keys(
        normalized,
        {
            "schema",
            "source_kind",
            "source_version_id",
            "extraction_record_id",
            "model_source_id",
            "locator",
        },
        "source",
    )
    if normalized["schema"] != "c1-source-reference-v1":
        raise EquilibriumModelContractError("source schema must be c1-source-reference-v1")
    try:
        return SourceReference(
            source_kind=normalized["source_kind"],
            source_version_id=normalized["source_version_id"],
            extraction_record_id=normalized["extraction_record_id"],
            model_source_id=normalized["model_source_id"],
            locator=CanonicalScope.from_mapping(_mapping(normalized["locator"], "source locator")),
        )
    except ValueError as exc:
        raise EquilibriumModelContractError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class SelectedNumericPropertyInput:
    """A closed C4 scalar snapshot derived from one authorized C1 selection."""

    component_id: str
    identity: PropertyIdentity
    property_type: ThermophysicalProperty
    conditions: PropertyConditions
    value: float
    unit: str
    source: SourceReference
    uncertainty: UncertaintyDescriptor
    selection_status: SelectionStatus
    authority_state: AuthorityState
    interpolation_state: InterpolationState
    request_sha256: str
    assertion_sha256: str
    datum_sha256: str
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        component_id = _nonblank(self.component_id, "component_id")
        if not isinstance(self.identity, PropertyIdentity):
            raise EquilibriumModelContractError("identity must be a PropertyIdentity")
        if self.property_type not in _REQUIRED_PROPERTIES:
            raise EquilibriumModelContractError(
                "property type must be vapor pressure or molecular weight"
            )
        if not isinstance(self.conditions, PropertyConditions):
            raise EquilibriumModelContractError("conditions must be PropertyConditions")
        value = _positive(self.value, "selected numeric value")
        unit = _nonblank(self.unit, "unit")
        required_unit = (
            "Pa" if self.property_type is ThermophysicalProperty.VAPOR_PRESSURE else "g/mol"
        )
        if unit != required_unit:
            raise EquilibriumModelContractError(
                f"{self.property_type.value} must use {required_unit}"
            )
        if not isinstance(self.source, SourceReference):
            raise EquilibriumModelContractError("source must be a SourceReference")
        if self.source.source_kind != "B2_OBSERVATION":
            raise EquilibriumModelContractError(
                "selected numeric property source must be a B2 observation"
            )
        if not isinstance(self.uncertainty, UncertaintyDescriptor):
            raise EquilibriumModelContractError("uncertainty must be an UncertaintyDescriptor")
        if self.selection_status is not SelectionStatus.SELECTED:
            raise EquilibriumModelContractError("selection status must be SELECTED")
        if self.authority_state is not AuthorityState.AUTHORIZED_FOR_SCOPED_PROPERTY:
            raise EquilibriumModelContractError("authority must be AUTHORIZED_FOR_SCOPED_PROPERTY")
        if self.interpolation_state not in {
            InterpolationState.EXACT,
            InterpolationState.INTERPOLATED,
        }:
            raise EquilibriumModelContractError("interpolation state must be EXACT or INTERPOLATED")
        request_sha256 = _sha256(self.request_sha256, "request_sha256")
        assertion_sha256 = _sha256(self.assertion_sha256, "assertion_sha256")
        datum_sha256 = _sha256(self.datum_sha256, "datum_sha256")

        object.__setattr__(self, "component_id", component_id)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "request_sha256", request_sha256)
        object.__setattr__(self, "assertion_sha256", assertion_sha256)
        object.__setattr__(self, "datum_sha256", datum_sha256)
        object.__setattr__(
            self,
            "content_sha256",
            stable_json_hash(self._content_mapping()),
        )

    @classmethod
    def from_selection(
        cls,
        *,
        component_id: str,
        request: PropertyRequest,
        selection: PropertySelectionResult,
    ) -> SelectedNumericPropertyInput:
        if not isinstance(request, PropertyRequest):
            raise EquilibriumModelContractError("request must be a PropertyRequest")
        if not isinstance(selection, PropertySelectionResult):
            raise EquilibriumModelContractError("selection must be a PropertySelectionResult")
        if selection.status is not SelectionStatus.SELECTED:
            raise EquilibriumModelContractError("selection status must be SELECTED")
        if selection.authority_state is not AuthorityState.AUTHORIZED_FOR_SCOPED_PROPERTY:
            raise EquilibriumModelContractError(
                "selection authority is not authorized for the scoped property"
            )
        if selection.request_sha256 != request.content_sha256:
            raise EquilibriumModelContractError(
                "selection request hash does not match the property request"
            )
        if selection.conditions.scope != request.conditions.scope:
            raise EquilibriumModelContractError(
                "selection conditions do not match the property request"
            )
        if selection.missing_reason is not None:
            raise EquilibriumModelContractError(
                "selected property must not carry a missing-data reason"
            )
        if selection.model is not None:
            raise EquilibriumModelContractError(
                "C4 does not evaluate C1 vapor-pressure equation declarations"
            )
        datum = selection.datum
        if (
            datum is None
            or datum.value_kind is not PropertyValueKind.NUMERIC
            or datum.numeric_value is None
        ):
            raise EquilibriumModelContractError("selected property must be a numeric observation")
        if selection.canonical_unit != datum.canonical_unit:
            raise EquilibriumModelContractError(
                "selection canonical unit does not match the selected datum"
            )
        if selection.source is None:
            raise EquilibriumModelContractError("selected property source is required")
        if selection.assertion_sha256 is None:
            raise EquilibriumModelContractError("selected property assertion hash is required")
        if selection.interpolation_state is None:
            raise EquilibriumModelContractError("selected property interpolation state is required")
        return cls(
            component_id=component_id,
            identity=request.identity,
            property_type=request.property_type,
            conditions=selection.conditions,
            value=datum.numeric_value,
            unit=datum.canonical_unit,
            source=selection.source,
            uncertainty=selection.uncertainty,
            selection_status=selection.status,
            authority_state=selection.authority_state,
            interpolation_state=selection.interpolation_state,
            request_sha256=request.content_sha256,
            assertion_sha256=selection.assertion_sha256,
            datum_sha256=datum.content_sha256,
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c4-selected-numeric-property-input-v1",
            "component_id": self.component_id,
            "identity": self.identity.to_mapping(),
            "property_type": self.property_type.value,
            "conditions": self.conditions.to_mapping(),
            "value": self.value,
            "unit": self.unit,
            "source": self.source.to_mapping(),
            "uncertainty": self.uncertainty.payload.to_mapping(),
            "selection_status": self.selection_status.value,
            "authority_state": self.authority_state.value,
            "interpolation_state": self.interpolation_state.value,
            "request_sha256": self.request_sha256,
            "assertion_sha256": self.assertion_sha256,
            "datum_sha256": self.datum_sha256,
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> SelectedNumericPropertyInput:
        normalized = _mapping(payload, "selected numeric property input")
        _exact_keys(
            normalized,
            {
                "schema",
                "component_id",
                "identity",
                "property_type",
                "conditions",
                "value",
                "unit",
                "source",
                "uncertainty",
                "selection_status",
                "authority_state",
                "interpolation_state",
                "request_sha256",
                "assertion_sha256",
                "datum_sha256",
                "content_sha256",
            },
            "selected numeric property input",
        )
        if normalized["schema"] != "c4-selected-numeric-property-input-v1":
            raise EquilibriumModelContractError(
                "selected property schema must be c4-selected-numeric-property-input-v1"
            )
        try:
            result = cls(
                component_id=normalized["component_id"],
                identity=PropertyIdentity.from_mapping(
                    _mapping(normalized["identity"], "identity")
                ),
                property_type=ThermophysicalProperty(normalized["property_type"]),
                conditions=PropertyConditions.from_mapping(
                    _mapping(normalized["conditions"], "conditions")
                ),
                value=normalized["value"],
                unit=normalized["unit"],
                source=_source_from_mapping(_mapping(normalized["source"], "source")),
                uncertainty=UncertaintyDescriptor.from_mapping(
                    _mapping(normalized["uncertainty"], "uncertainty")
                ),
                selection_status=SelectionStatus(normalized["selection_status"]),
                authority_state=AuthorityState(normalized["authority_state"]),
                interpolation_state=InterpolationState(normalized["interpolation_state"]),
                request_sha256=normalized["request_sha256"],
                assertion_sha256=normalized["assertion_sha256"],
                datum_sha256=normalized["datum_sha256"],
            )
        except ValueError as exc:
            if isinstance(exc, EquilibriumModelContractError):
                raise
            raise EquilibriumModelContractError(str(exc)) from exc
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise EquilibriumModelContractError(
                "selected property content_sha256 does not match canonical content"
            )
        return result


@dataclass(frozen=True, slots=True)
class IdealRaoultInputSet:
    """One exact, tamper-evident set of C1 inputs for an ideal calculation."""

    input_set_id: str
    properties: tuple[SelectedNumericPropertyInput, ...]
    content_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        input_set_id = _nonblank(self.input_set_id, "input_set_id")
        if isinstance(self.properties, (str, bytes)) or not isinstance(self.properties, Sequence):
            raise EquilibriumModelContractError("properties must be a sequence")
        properties = tuple(self.properties)
        if not properties:
            raise EquilibriumModelContractError("properties must not be empty")
        if any(not isinstance(item, SelectedNumericPropertyInput) for item in properties):
            raise EquilibriumModelContractError(
                "properties must contain SelectedNumericPropertyInput values"
            )
        keys = tuple((item.component_id.casefold(), item.property_type) for item in properties)
        if len(keys) != len(set(keys)):
            raise EquilibriumModelContractError(
                "properties contains a duplicate component/property entry"
            )
        grouped: dict[str, list[SelectedNumericPropertyInput]] = defaultdict(list)
        for item in properties:
            grouped[item.component_id.casefold()].append(item)
        for component_properties in grouped.values():
            if {item.property_type for item in component_properties} != set(_REQUIRED_PROPERTIES):
                raise EquilibriumModelContractError(
                    "every component requires exactly one vapor-pressure and molecular-weight input"
                )
            if len({item.identity.content_sha256 for item in component_properties}) != 1:
                raise EquilibriumModelContractError(
                    "property identities for one component must match"
                )
        properties = tuple(
            sorted(
                properties,
                key=lambda item: (
                    item.component_id.casefold(),
                    item.component_id,
                    item.property_type.value,
                ),
            )
        )
        object.__setattr__(self, "input_set_id", input_set_id)
        object.__setattr__(self, "properties", properties)
        object.__setattr__(
            self,
            "content_sha256",
            stable_json_hash(self._content_mapping()),
        )

    def _content_mapping(self) -> dict[str, object]:
        return {
            "schema": "c4-ideal-raoult-input-set-v1",
            "input_set_id": self.input_set_id,
            "properties": [item.to_mapping() for item in self.properties],
        }

    def to_mapping(self) -> dict[str, object]:
        return {**self._content_mapping(), "content_sha256": self.content_sha256}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> IdealRaoultInputSet:
        normalized = _mapping(payload, "ideal Raoult input set")
        _exact_keys(
            normalized,
            {"schema", "input_set_id", "properties", "content_sha256"},
            "ideal Raoult input set",
        )
        if normalized["schema"] != "c4-ideal-raoult-input-set-v1":
            raise EquilibriumModelContractError(
                "input-set schema must be c4-ideal-raoult-input-set-v1"
            )
        raw_properties = normalized["properties"]
        if isinstance(raw_properties, (str, bytes)) or not isinstance(raw_properties, Sequence):
            raise EquilibriumModelContractError("properties must be a sequence")
        result = cls(
            input_set_id=normalized["input_set_id"],
            properties=tuple(
                SelectedNumericPropertyInput.from_mapping(_mapping(item, "selected property"))
                for item in raw_properties
            ),
        )
        if _sha256(normalized["content_sha256"], "content_sha256") != result.content_sha256:
            raise EquilibriumModelContractError(
                "input-set content_sha256 does not match canonical content"
            )
        return result

    def to_model_input_reference(self) -> ModelInputReference:
        return ModelInputReference(
            role=C4_INPUT_ROLE,
            input_id=self.input_set_id,
            content_sha256=self.content_sha256,
        )

    def property_for(
        self,
        component_id: str,
        property_type: ThermophysicalProperty,
    ) -> SelectedNumericPropertyInput:
        folded = component_id.casefold()
        for item in self.properties:
            if item.component_id.casefold() == folded and item.property_type is property_type:
                return item
        raise EquilibriumModelContractError(
            f"property input is absent for {component_id}:{property_type.value}"
        )

    @property
    def component_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {item.component_id for item in self.properties},
                key=lambda item: (item.casefold(), item),
            )
        )

    @property
    def identity_sha256s(self) -> tuple[str, ...]:
        return tuple(sorted({item.identity.content_sha256 for item in self.properties}))


@dataclass(frozen=True, slots=True)
class _CompositionTerm:
    component_id: str
    identity_sha256: str
    mole_fraction: float
    molecular_weight_g_mol: float
    pure_vapor_pressure_pa: float


@dataclass(frozen=True, slots=True)
class _CompositionCalculation:
    terms: tuple[_CompositionTerm, ...]
    input_basis_abs_error: float
    mass_round_trip_max_abs_error: float | None


def _ideal_domain() -> ApplicabilityDomain:
    return ApplicabilityDomain(
        domain_id="c4-domain:ideal-raoult-baseline",
        domain_version="1",
        supported_identity_ids=(),
        supported_chemical_classes=(),
        supported_functional_groups=(),
        supported_matrix_stages=_SUPPORTED_STAGES,
        matrix_range=CanonicalScope.from_mapping(
            {
                "composition_completeness": "EXACT",
                "supported_bases": [item.value for item in sorted(_SUPPORTED_BASES, key=str)],
                "implicit_unit_conversion": False,
            }
        ),
        concentration_range=None,
        temperature_range=None,
        pressure_range=None,
        supported_phase_behaviors=(_SINGLE_LIQUID_PHASE,),
        supported_environment_kinds=_SUPPORTED_ENVIRONMENTS,
        required_properties=_REQUIRED_PROPERTIES,
        training_calibration_domain=CanonicalScope.from_mapping(
            {
                "kind": "theoretical_baseline",
                "training_data": None,
                "calibration_data": None,
            }
        ),
        known_failure_modes=(
            "activity coefficients differ from one",
            "bubble pressure exceeds system pressure",
            "implicit unit conversion would be required",
            "multiple liquid phases or phase separation",
            "selected vapor pressure is unavailable at the exact temperature",
        ),
    )


def _ideal_release(
    *,
    code_commit: str,
    implementation_sha256: str,
) -> ModelRelease:
    parameter_declaration = {
        "schema": "c4-ideal-raoult-parameter-declaration-v1",
        "equation": "p_i = x_i * p_i_star",
        "activity_coefficient": 1.0,
        "closure_tolerance": _CLOSURE_TOLERANCE,
        "unit_contract": {"pressure": "Pa", "temperature": "K", "mw": "g/mol"},
    }
    return ModelRelease(
        selector=ModelSelector(
            family=ModelFamily.IDEAL_RAOULT_BASELINE,
            model_version=IDEAL_RAOULT_MODEL_VERSION,
        ),
        parameter_set_version="c4-ideal-raoult-parameters-v1",
        code_commit=code_commit,
        implementation_sha256=implementation_sha256,
        parameter_set_sha256=stable_json_hash(parameter_declaration),
        coefficient_set_sha256=None,
        decomposition_sha256=None,
        training_data_sha256=None,
        applicability_domain=_ideal_domain(),
        supported_operations=(ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE,),
        availability=ModelAvailability.AVAILABLE,
        unavailable_reason=None,
        evidence_class=ModelEvidenceClass.THEORETICAL_BASELINE,
        may_feed_oav_screening=False,
        permitted_claim_wording=(
            "ideal-solution comparison baseline",
            "Raoult-law partial-pressure calculation under declared assumptions",
        ),
        forbidden_claim_wording=(
            "COSMO-RS result",
            "UNIFAC result",
            "calibrated perfume release",
            "canonical production headspace",
            "measured headspace",
            "validated nonideal prediction",
        ),
    )


def _unavailable_domain(
    family: ModelFamily,
    requirements: Sequence[str],
) -> ApplicabilityDomain:
    required_properties: tuple[ThermophysicalProperty, ...]
    if family is ModelFamily.HENRY_LAW_DILUTE_BASELINE:
        required_properties = (ThermophysicalProperty.HENRY_CONSTANT,)
    elif family is ModelFamily.UNIFAC_OR_MODIFIED_UNIFAC:
        required_properties = (ThermophysicalProperty.ACTIVITY_COEFFICIENT_PARAMETERS,)
    elif family is ModelFamily.IMPORTED_COSMO_RS:
        required_properties = (ThermophysicalProperty.PHASE_DATA,)
    else:
        required_properties = _REQUIRED_PROPERTIES
    return ApplicabilityDomain(
        domain_id=f"c4-domain:withheld:{family.value.lower()}",
        domain_version="1",
        supported_identity_ids=(),
        supported_chemical_classes=(),
        supported_functional_groups=(),
        supported_matrix_stages=_SUPPORTED_STAGES,
        matrix_range=CanonicalScope.from_mapping({"status": "WITHHELD", "family": family.value}),
        concentration_range=None,
        temperature_range=None,
        pressure_range=None,
        supported_phase_behaviors=(_SINGLE_LIQUID_PHASE,),
        supported_environment_kinds=_SUPPORTED_ENVIRONMENTS,
        required_properties=required_properties,
        training_calibration_domain=CanonicalScope.from_mapping(
            {"status": "WITHHELD", "validated_training_data": None}
        ),
        known_failure_modes=tuple(requirements),
    )


_WITHHELD_DECLARATIONS: tuple[tuple[ModelFamily, str, str, tuple[str, ...]], ...] = (
    (
        ModelFamily.HENRY_LAW_DILUTE_BASELINE,
        "c4-henry-withheld-v1",
        "matrix-specific validated Henry assertions are not bound",
        (
            "matrix-specific Henry measurement is absent",
            "temperature and concentration validation are absent",
        ),
    ),
    (
        ModelFamily.EMPIRICAL_MATRIX_CORRECTION,
        "c4-empirical-matrix-withheld-v1",
        "validated Build B train and validation provenance are not bound",
        (
            "immutable training-data digest is absent",
            "held-out validation evidence is absent",
        ),
    ),
    (
        ModelFamily.UNIFAC_OR_MODIFIED_UNIFAC,
        "c4-unifac-withheld-v1",
        "versioned subgroup decomposition parameters coverage and benchmarks are absent",
        (
            "declared UNIFAC parameter version is absent",
            "molecular subgroup decomposition is absent",
            "interaction-parameter coverage is absent",
            "trusted reference benchmarks are absent",
            "naturals opaque bases and supplier blends cannot be decomposed as pure molecules",
        ),
    ),
    (
        ModelFamily.IMPORTED_COSMO_RS,
        "c4-cosmo-rs-withheld-v1",
        "versioned licensed COSMO-RS calculation provenance and import digest are absent",
        (
            "software and parameterization provenance are absent",
            "quantum chemistry conformer and sigma-profile provenance are absent",
            "temperature composition license and import digests are absent",
            "measured or simple-baseline comparison is absent",
        ),
    ),
)


def _withheld_release(
    *,
    family: ModelFamily,
    model_version: str,
    unavailable_reason: str,
    requirements: Sequence[str],
    code_commit: str,
    implementation_sha256: str,
) -> ModelRelease:
    declaration = {
        "schema": "c4-withheld-equilibrium-release-v1",
        "family": family.value,
        "model_version": model_version,
        "unavailable_reason": unavailable_reason,
        "requirements": list(requirements),
    }
    return ModelRelease(
        selector=ModelSelector(family=family, model_version=model_version),
        parameter_set_version="WITHHELD",
        code_commit=code_commit,
        implementation_sha256=implementation_sha256,
        parameter_set_sha256=stable_json_hash(declaration),
        coefficient_set_sha256=None,
        decomposition_sha256=None,
        training_data_sha256=None,
        applicability_domain=_unavailable_domain(family, requirements),
        supported_operations=(ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE,),
        availability=ModelAvailability.UNAVAILABLE,
        unavailable_reason=unavailable_reason,
        evidence_class=ModelEvidenceClass.UNVALIDATED,
        may_feed_oav_screening=False,
        permitted_claim_wording=(f"{family.value} is unavailable in Build C4",),
        forbidden_claim_wording=(
            "computed equilibrium result",
            "validated model",
        ),
    )


class UnavailableEquilibriumAdapter:
    """Protocol-complete adapter whose release is rejected by C3 before compute."""

    __slots__ = ("_release",)

    def __init__(self, release: ModelRelease) -> None:
        if release.availability is not ModelAvailability.UNAVAILABLE:
            raise EquilibriumModelContractError(
                "UnavailableEquilibriumAdapter requires an unavailable release"
            )
        self._release = release

    @property
    def release(self) -> ModelRelease:
        return self._release

    def evaluate_applicability(
        self,
        request: VersionedModelRequest,
    ) -> ApplicabilityResult:
        return ApplicabilityResult(
            state=ApplicabilityState.MODEL_NOT_VALIDATED,
            domain_sha256=self.release.applicability_domain.content_sha256,
            request_sha256=request.content_sha256,
            reasons=(self.release.unavailable_reason or "model is unavailable",),
            missing_inputs=(),
            warnings=(),
        )

    def compute(
        self,
        request: VersionedModelRequest,
        applicability: ApplicabilityResult,
    ) -> ModelComputation:
        del request, applicability
        raise EquilibriumModelContractError("an unavailable equilibrium model cannot compute")


def withheld_equilibrium_adapters(
    *,
    code_commit: str,
    implementation_sha256: str,
) -> tuple[UnavailableEquilibriumAdapter, ...]:
    return tuple(
        UnavailableEquilibriumAdapter(
            _withheld_release(
                family=family,
                model_version=model_version,
                unavailable_reason=reason,
                requirements=requirements,
                code_commit=code_commit,
                implementation_sha256=implementation_sha256,
            )
        )
        for family, model_version, reason, requirements in _WITHHELD_DECLARATIONS
    )


class IdealRaoultAdapter:
    """Exact-input C3 adapter for the transparent ideal Raoult baseline."""

    __slots__ = ("_input_set", "_release")

    def __init__(
        self,
        *,
        input_set: IdealRaoultInputSet,
        code_commit: str,
        implementation_sha256: str,
    ) -> None:
        if not isinstance(input_set, IdealRaoultInputSet):
            raise EquilibriumModelContractError("input_set must be an IdealRaoultInputSet")
        self._input_set = input_set
        self._release = _ideal_release(
            code_commit=code_commit,
            implementation_sha256=implementation_sha256,
        )

    @property
    def input_set(self) -> IdealRaoultInputSet:
        return self._input_set

    @property
    def release(self) -> ModelRelease:
        return self._release

    def _input_reference_is_exact(self, request: VersionedModelRequest) -> bool:
        return request.input_references == (self.input_set.to_model_input_reference(),)

    def _derive_composition(
        self,
        request: VersionedModelRequest,
    ) -> _CompositionCalculation:
        matrix = request.context.matrix
        bases = {component.basis for component in matrix.components}
        if len(bases) != 1:
            raise EquilibriumModelContractError("matrix component bases must be uniform")
        basis = next(iter(bases))
        if basis not in _SUPPORTED_BASES:
            raise EquilibriumModelContractError(f"matrix basis {basis.value} is unsupported")
        units = {component.quantity.unit for component in matrix.components}
        if len(units) != 1:
            raise EquilibriumModelContractError(
                "all absolute component quantities must use one exact unit"
            )
        unit = next(iter(units))
        if (
            basis
            in {
                MatrixQuantityBasis.MOLE_FRACTION,
                MatrixQuantityBasis.MASS_FRACTION,
            }
            and unit != "1"
        ):
            raise EquilibriumModelContractError("fraction basis must use unit 1")

        raw_amounts: list[float] = []
        molecular_weights: list[float] = []
        vapor_pressures: list[float] = []
        identity_sha256s: list[str] = []
        quantities: list[float] = []
        for component in matrix.components:
            vapor_pressure = self.input_set.property_for(
                component.component_id,
                ThermophysicalProperty.VAPOR_PRESSURE,
            )
            molecular_weight = self.input_set.property_for(
                component.component_id,
                ThermophysicalProperty.MOLECULAR_WEIGHT,
            )
            quantity_value = component.quantity.value
            quantities.append(quantity_value)
            molecular_weights.append(molecular_weight.value)
            vapor_pressures.append(vapor_pressure.value)
            identity_sha256s.append(vapor_pressure.identity.content_sha256)
            if basis in {
                MatrixQuantityBasis.MASS_FRACTION,
                MatrixQuantityBasis.MASS,
            }:
                raw_amounts.append(quantity_value / molecular_weight.value)
            else:
                raw_amounts.append(quantity_value)

        total_amount = math.fsum(raw_amounts)
        if total_amount <= 0.0:
            raise EquilibriumModelContractError("composition has a non-positive amount denominator")
        mole_fractions = tuple(value / total_amount for value in raw_amounts)
        mole_sum_error = abs(math.fsum(mole_fractions) - 1.0)
        if mole_sum_error > _CLOSURE_TOLERANCE:
            raise EquilibriumModelContractError("derived mole fractions do not close")

        if basis in {
            MatrixQuantityBasis.MOLE_FRACTION,
            MatrixQuantityBasis.MASS_FRACTION,
        }:
            input_basis_error = abs(math.fsum(quantities) - 1.0)
        elif basis is MatrixQuantityBasis.MASS:
            if matrix.total_mass is None:
                raise EquilibriumModelContractError("absolute mass requires total_mass")
            if matrix.total_mass.unit != unit:
                raise EquilibriumModelContractError("absolute mass and total_mass units must match")
            input_basis_error = abs(math.fsum(quantities) - matrix.total_mass.value)
        else:
            input_basis_error = 0.0
        if input_basis_error > _CLOSURE_TOLERANCE:
            raise EquilibriumModelContractError(
                "declared component basis does not close against its total"
            )

        mass_round_trip_error: float | None = None
        if basis in {
            MatrixQuantityBasis.MASS_FRACTION,
            MatrixQuantityBasis.MASS,
        }:
            original_mass_total = math.fsum(quantities)
            if original_mass_total <= 0.0:
                raise EquilibriumModelContractError(
                    "composition has a non-positive mass denominator"
                )
            original_mass_fractions = tuple(value / original_mass_total for value in quantities)
            recovered_masses = tuple(
                mole_fraction * molecular_weight
                for mole_fraction, molecular_weight in zip(
                    mole_fractions,
                    molecular_weights,
                    strict=True,
                )
            )
            recovered_total = math.fsum(recovered_masses)
            recovered_mass_fractions = tuple(value / recovered_total for value in recovered_masses)
            mass_round_trip_error = max(
                abs(expected - actual)
                for expected, actual in zip(
                    original_mass_fractions,
                    recovered_mass_fractions,
                    strict=True,
                )
            )
            if mass_round_trip_error > _CLOSURE_TOLERANCE:
                raise EquilibriumModelContractError(
                    "mass-to-mole conversion does not conserve mass fractions"
                )

        terms = tuple(
            _CompositionTerm(
                component_id=component.component_id,
                identity_sha256=identity_sha256,
                mole_fraction=mole_fraction,
                molecular_weight_g_mol=molecular_weight,
                pure_vapor_pressure_pa=vapor_pressure,
            )
            for component, identity_sha256, mole_fraction, molecular_weight, vapor_pressure in zip(
                matrix.components,
                identity_sha256s,
                mole_fractions,
                molecular_weights,
                vapor_pressures,
                strict=True,
            )
        )
        return _CompositionCalculation(
            terms=terms,
            input_basis_abs_error=input_basis_error,
            mass_round_trip_max_abs_error=mass_round_trip_error,
        )

    def evaluate_applicability(
        self,
        request: VersionedModelRequest,
    ) -> ApplicabilityResult:
        if not isinstance(request, VersionedModelRequest):
            raise EquilibriumModelContractError("request must be a VersionedModelRequest")
        if request.requested_model != self.release.selector:
            raise EquilibriumModelContractError(
                "request selector does not match the ideal adapter release"
            )
        if request.operation is not ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE:
            raise EquilibriumModelContractError(
                "ideal adapter supports only equilibrium-headspace prediction"
            )

        matrix = request.context.matrix
        environment = request.context.environment
        applicability = request.applicability_context
        missing: set[str] = set()
        outside: set[str] = set()

        if not self._input_reference_is_exact(request):
            missing.add("input_reference:c4_equilibrium_input_set")
        if matrix.completeness is not CompositionCompleteness.EXACT:
            missing.add("matrix:exact_composition")
        if matrix.missing_fields:
            missing.update(f"matrix:{item.value}" for item in matrix.missing_fields)
        if {component.component_id for component in matrix.components} != set(
            self.input_set.component_ids
        ):
            missing.add("property_inputs:component_binding")
        if set(applicability.identity_ids) != set(self.input_set.identity_sha256s):
            missing.add("property_inputs:identity_binding")
        if not set(_REQUIRED_PROPERTIES).issubset(applicability.available_properties):
            missing.add("property_inputs:available_properties")

        if matrix.stage not in _SUPPORTED_STAGES:
            outside.add(f"matrix stage {matrix.stage.value} is unsupported")
        if not matrix.gas_comparison:
            outside.add("matrix gas_comparison must be true")
        if environment.kind not in _SUPPORTED_ENVIRONMENTS:
            outside.add(f"environment {environment.kind.value} is unsupported")
        if applicability.phase_behavior != _SINGLE_LIQUID_PHASE:
            outside.add("applicability phase behavior must be single_liquid_phase")
        if _SINGLE_LIQUID_PHASE not in matrix.phase_assumptions:
            outside.add("matrix must declare single_liquid_phase")

        temperature = matrix.temperature
        pressure = matrix.pressure
        if temperature is None:
            missing.add("matrix:temperature")
        elif temperature.unit != "K":
            outside.add("matrix temperature unit must be K")
        if pressure is None:
            missing.add("matrix:pressure")
        elif pressure.unit != "Pa":
            outside.add("matrix pressure unit must be Pa")

        environment_temperature = environment.temperature
        if environment_temperature is None:
            missing.add("environment:temperature")
        elif environment_temperature.unit != "K":
            outside.add("environment temperature unit must be K")
        elif temperature is not None and environment_temperature.value != temperature.value:
            outside.add("environment temperature must match matrix temperature")

        bases = {component.basis for component in matrix.components}
        if len(bases) != 1:
            outside.add("matrix component bases must be uniform")
        elif next(iter(bases)) not in _SUPPORTED_BASES:
            outside.add(f"matrix basis {next(iter(bases)).value} is unsupported")

        if temperature is not None and temperature.unit == "K":
            for component_id in self.input_set.component_ids:
                vapor_pressure = self.input_set.property_for(
                    component_id,
                    ThermophysicalProperty.VAPOR_PRESSURE,
                )
                if vapor_pressure.conditions.temperature_k != temperature.value:
                    missing.add(f"property:vapor_pressure:{component_id}:exact_temperature")

        calculation: _CompositionCalculation | None = None
        if not missing and not outside:
            try:
                calculation = self._derive_composition(request)
            except EquilibriumModelContractError as exc:
                outside.add(str(exc))
        if calculation is not None and pressure is not None:
            bubble_pressure = math.fsum(
                term.mole_fraction * term.pure_vapor_pressure_pa for term in calculation.terms
            )
            if bubble_pressure - pressure.value > _CLOSURE_TOLERANCE:
                outside.add("ideal bubble pressure exceeds declared system pressure")

        reasons: tuple[str, ...]
        missing_inputs: tuple[str, ...]
        if missing:
            state = ApplicabilityState.INSUFFICIENT_INPUT
            reasons = ("required C4 input evidence is missing or unbound",)
            missing_inputs = tuple(sorted(missing, key=lambda item: (item.casefold(), item)))
        elif outside:
            state = ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN
            reasons = tuple(sorted(outside, key=lambda item: (item.casefold(), item)))
            missing_inputs = ()
        else:
            state = ApplicabilityState.IN_DOMAIN
            reasons = ("all ideal-baseline applicability checks passed",)
            missing_inputs = ()
        return ApplicabilityResult(
            state=state,
            domain_sha256=self.release.applicability_domain.content_sha256,
            request_sha256=request.content_sha256,
            reasons=reasons,
            missing_inputs=missing_inputs,
            warnings=(),
        )

    def compute(
        self,
        request: VersionedModelRequest,
        applicability: ApplicabilityResult,
    ) -> ModelComputation:
        if not isinstance(applicability, ApplicabilityResult):
            raise EquilibriumModelContractError("applicability must be an ApplicabilityResult")
        if applicability.state not in {
            ApplicabilityState.IN_DOMAIN,
            ApplicabilityState.NEAR_DOMAIN_WITH_WARNING,
        }:
            raise EquilibriumModelContractError("ideal computation requires an applicable request")
        if applicability.request_sha256 != request.content_sha256:
            raise EquilibriumModelContractError(
                "applicability request hash does not match the request"
            )
        if applicability.domain_sha256 != self.release.applicability_domain.content_sha256:
            raise EquilibriumModelContractError(
                "applicability domain hash does not match the release"
            )
        calculation = self._derive_composition(request)
        matrix = request.context.matrix
        if matrix.temperature is None or matrix.pressure is None:
            raise EquilibriumModelContractError(
                "applicable ideal computation requires temperature and pressure"
            )
        system_pressure = matrix.pressure.value
        component_payloads: list[dict[str, object]] = []
        partial_pressures: list[float] = []
        for term in calculation.terms:
            partial_pressure = term.mole_fraction * term.pure_vapor_pressure_pa
            partial_pressures.append(partial_pressure)
            component_payloads.append(
                {
                    "component_id": term.component_id,
                    "identity_sha256": term.identity_sha256,
                    "liquid_mole_fraction": term.mole_fraction,
                    "pure_vapor_pressure_pa": term.pure_vapor_pressure_pa,
                    "activity_coefficient": 1.0,
                    "partial_pressure_pa": partial_pressure,
                    "system_pressure_fraction": partial_pressure / system_pressure,
                }
            )
        bubble_pressure = math.fsum(partial_pressures)
        if bubble_pressure - system_pressure > _CLOSURE_TOLERANCE:
            raise EquilibriumModelContractError(
                "ideal bubble pressure exceeds declared system pressure"
            )
        liquid_sum_error = abs(math.fsum(term.mole_fraction for term in calculation.terms) - 1.0)
        reported_partial_sum = math.fsum(partial_pressures)
        payload = CanonicalScope.from_mapping(
            {
                "schema": "c4-ideal-raoult-output-v1",
                "equation": "p_i = x_i * p_i_star",
                "activity_coefficient_model": "gamma_i = 1",
                "temperature_k": matrix.temperature.value,
                "system_pressure_pa": system_pressure,
                "request_sha256": request.content_sha256,
                "formula_sha256": request.context.formula_sha256,
                "matrix_sha256": matrix.content_sha256,
                "environment_sha256": request.context.environment.content_sha256,
                "input_set_sha256": self.input_set.content_sha256,
                "model_release_sha256": self.release.content_sha256,
                "components": component_payloads,
                "total_ideal_bubble_pressure_pa": bubble_pressure,
                "modeled_system_pressure_fraction": bubble_pressure / system_pressure,
                "closure_checks": {
                    "input_basis_abs_error": calculation.input_basis_abs_error,
                    "liquid_mole_fraction_abs_error": liquid_sum_error,
                    "mass_round_trip_max_abs_error": (calculation.mass_round_trip_max_abs_error),
                    "partial_pressure_sum_abs_error": abs(reported_partial_sum - bubble_pressure),
                    "within_system_pressure": (
                        bubble_pressure - system_pressure <= _CLOSURE_TOLERANCE
                    ),
                },
                "assumptions": [
                    "ideal liquid solution",
                    "activity coefficients fixed at one",
                    "selected pure vapor pressures apply at the exact temperature",
                    "single liquid phase",
                    "inert or background gas is not modeled",
                    "reported gas fractions are not renormalized",
                ],
            }
        )
        return ModelComputation(
            output=ModelOutput(
                quantity="equilibrium_headspace_partial_pressures",
                unit="Pa",
                payload=payload,
            ),
            uncertainty=UncertaintyDescriptor.unknown(
                "C4 ideal baseline does not propagate selected-property uncertainty; C5 required"
            ),
            warnings=(_C5_WARNING, _IDEAL_WARNING),
        )


__all__ = [
    "C4_INPUT_ROLE",
    "EquilibriumModelContractError",
    "IDEAL_RAOULT_MODEL_VERSION",
    "IdealRaoultAdapter",
    "IdealRaoultInputSet",
    "SelectedNumericPropertyInput",
    "UnavailableEquilibriumAdapter",
    "withheld_equilibrium_adapters",
]
