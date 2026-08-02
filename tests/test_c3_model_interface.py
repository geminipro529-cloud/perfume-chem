from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from engine.physics.matrix_environment import (
    ApplicationEnvironment,
    ApplicationEnvironmentKind,
    CompositionCompleteness,
    DeclaredQuantity,
    EnvironmentField,
    MatrixAwareModelRequest,
    MatrixComponent,
    MatrixComponentRole,
    MatrixComposition,
    MatrixQuantityBasis,
    MatrixStage,
)
from engine.physics.model_interface import (
    ApplicabilityContext,
    ApplicabilityDomain,
    ApplicabilityResult,
    ApplicabilityState,
    DomainRange,
    FallbackDisclosure,
    ModelAvailability,
    ModelComparisonResult,
    ModelComputation,
    ModelEvidenceClass,
    ModelFamily,
    ModelInputReference,
    ModelInterfaceContractError,
    ModelOperation,
    ModelOutput,
    ModelRelease,
    ModelResultStatus,
    ModelSelector,
    VersionedModelAdapter,
    VersionedModelRequest,
    VersionedModelResult,
    VersionedModelRouter,
)
from engine.physics.properties import (
    CanonicalScope,
    ThermophysicalProperty,
    UncertaintyDescriptor,
)

REQUIRED_OPERATIONS = {
    "predict_equilibrium_headspace",
    "predict_dynamic_release",
    "estimate_partition_coefficient",
    "evaluate_applicability",
    "propagate_uncertainty",
    "compare_models",
}
REQUIRED_MODEL_FAMILIES = {
    "IDEAL_RAOULT_BASELINE",
    "HENRY_LAW_DILUTE_BASELINE",
    "MEASURED_LOOKUP_INTERPOLATION",
    "EMPIRICAL_MATRIX_CORRECTION",
    "UNIFAC_OR_MODIFIED_UNIFAC",
    "IMPORTED_COSMO_RS",
    "MEASURED_PARTITION_MODEL",
    "DYNAMIC_SEMI_EMPIRICAL_MODEL",
    "LEGACY_HEURISTIC_ADAPTER",
}
REQUIRED_APPLICABILITY_STATES = {
    "IN_DOMAIN",
    "NEAR_DOMAIN_WITH_WARNING",
    "OUTSIDE_APPLICABILITY_DOMAIN",
    "INSUFFICIENT_INPUT",
    "MODEL_NOT_VALIDATED",
}
REQUIRED_EVIDENCE_CLASSES = {
    "THEORETICAL_BASELINE",
    "MEASURED",
    "EMPIRICAL",
    "COMPUTATIONAL_IMPORT",
    "LITERATURE_DERIVED",
    "LEGACY_HEURISTIC",
    "UNVALIDATED",
}
ANSWER_PRODUCING_OPERATIONS = (
    ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE,
    ModelOperation.PREDICT_DYNAMIC_RELEASE,
    ModelOperation.ESTIMATE_PARTITION_COEFFICIENT,
    ModelOperation.PROPAGATE_UNCERTAINTY,
)
PUBLIC_C1_NAMES = {
    "AuthorityState",
    "CanonicalScope",
    "ClaimGrade",
    "ExtrapolationPolicy",
    "InterpolationState",
    "MissingDataReason",
    "PropertyConditions",
    "PropertyDatum",
    "PropertyIdentity",
    "PropertyRequest",
    "PropertySelectionResult",
    "PropertySelectionService",
    "PropertyValueKind",
    "SelectedPropertyAssertion",
    "SelectionKind",
    "SelectionStatus",
    "SourceReference",
    "TemperatureRange",
    "ThermophysicalContractError",
    "ThermophysicalProperty",
    "UncertaintyDescriptor",
    "UncertaintyKind",
    "VaporPressureCoefficient",
    "VaporPressureEquationType",
    "VaporPressurePoint",
    "VaporPressureRepresentation",
    "selected_assertion_from_b2_reconstruction",
}
PUBLIC_C2_NAMES = {
    "ApplicationEnvironment",
    "ApplicationEnvironmentKind",
    "CompositionCompleteness",
    "DeclaredQuantity",
    "EnvironmentField",
    "MatrixAwareModelRequest",
    "MatrixComponent",
    "MatrixComponentRole",
    "MatrixComposition",
    "MatrixEnvironmentContractError",
    "MatrixMissingField",
    "MatrixQuantityBasis",
    "MatrixStage",
}
PUBLIC_C3_NAMES = {
    "ApplicabilityContext",
    "ApplicabilityDomain",
    "ApplicabilityResult",
    "ApplicabilityState",
    "DomainRange",
    "FallbackDisclosure",
    "ModelAvailability",
    "ModelComparisonResult",
    "ModelComputation",
    "ModelEvidenceClass",
    "ModelFamily",
    "ModelInputReference",
    "ModelInterfaceContractError",
    "ModelOperation",
    "ModelOutput",
    "ModelRelease",
    "ModelResultStatus",
    "ModelSelector",
    "VersionedModelAdapter",
    "VersionedModelRequest",
    "VersionedModelResult",
    "VersionedModelRouter",
}
PUBLIC_C4_NAMES = {
    "C4_INPUT_ROLE",
    "EquilibriumModelContractError",
    "IdealRaoultAdapter",
    "IdealRaoultInputSet",
    "SelectedNumericPropertyInput",
    "UnavailableEquilibriumAdapter",
    "withheld_equilibrium_adapters",
}


def digest(character: str) -> str:
    return character * 64


def selector(*, version: str = "1.0.0") -> ModelSelector:
    return ModelSelector(
        family=ModelFamily.IDEAL_RAOULT_BASELINE,
        model_version=version,
    )


def domain() -> ApplicabilityDomain:
    return ApplicabilityDomain(
        domain_id="domain:ideal-raoult:ethanol-water",
        domain_version="1",
        supported_identity_ids=("material:water", "material:ethanol"),
        supported_chemical_classes=("alcohol", "water"),
        supported_functional_groups=("hydroxyl",),
        supported_matrix_stages=(
            MatrixStage.SAMPLED_HEADSPACE,
            MatrixStage.FINISHED_PERFUME,
        ),
        matrix_range=CanonicalScope.from_mapping(
            {
                "ethanol_mass_fraction": {"lower": 0.5, "upper": 0.95},
                "water_mass_fraction": {"lower": 0.0, "upper": 0.5},
            }
        ),
        concentration_range=DomainRange(
            lower=0.0,
            upper=1.0,
            unit="mole_fraction",
            lower_inclusive=True,
            upper_inclusive=True,
        ),
        temperature_range=DomainRange(
            lower=288.15,
            upper=313.15,
            unit="K",
            lower_inclusive=True,
            upper_inclusive=True,
        ),
        pressure_range=DomainRange(
            lower=90000.0,
            upper=110000.0,
            unit="Pa",
            lower_inclusive=True,
            upper_inclusive=True,
        ),
        supported_phase_behaviors=("single liquid phase",),
        supported_environment_kinds=(ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL,),
        required_properties=(
            ThermophysicalProperty.VAPOR_PRESSURE,
            ThermophysicalProperty.MOLECULAR_WEIGHT,
        ),
        training_calibration_domain=CanonicalScope.from_mapping(
            {
                "kind": "transparent theoretical baseline",
                "calibration_dataset": None,
            }
        ),
        known_failure_modes=(
            "nonideal activity coefficients are not represented",
            "phase separation invalidates the baseline",
        ),
    )


def release(
    *,
    model_selector: ModelSelector | None = None,
    applicability_domain: ApplicabilityDomain | None = None,
) -> ModelRelease:
    return ModelRelease(
        selector=model_selector or selector(),
        parameter_set_version="ideal-no-parameters-v1",
        code_commit="a" * 40,
        implementation_sha256=digest("b"),
        parameter_set_sha256=digest("c"),
        coefficient_set_sha256=digest("d"),
        decomposition_sha256=digest("e"),
        training_data_sha256=digest("f"),
        applicability_domain=applicability_domain or domain(),
        supported_operations=(
            ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE,
            ModelOperation.PROPAGATE_UNCERTAINTY,
        ),
        availability=ModelAvailability.AVAILABLE,
        unavailable_reason=None,
        evidence_class=ModelEvidenceClass.THEORETICAL_BASELINE,
        may_feed_oav_screening=True,
        permitted_claim_wording=(
            "Transparent ideal-baseline screening result under the stated context.",
        ),
        forbidden_claim_wording=(
            "Measured headspace concentration.",
            "Validated nonideal perfume prediction.",
        ),
    )


def unknown(reason: str = "not quantified") -> UncertaintyDescriptor:
    return UncertaintyDescriptor.unknown(reason)


def quantity(value: float, unit: str) -> DeclaredQuantity:
    return DeclaredQuantity(value=value, unit=unit)


def matrix_component(
    component_id: str,
    name: str,
    role: MatrixComponentRole,
    fraction: float,
) -> MatrixComponent:
    return MatrixComponent(
        component_id=component_id,
        name=name,
        role=role,
        basis=MatrixQuantityBasis.MASS_FRACTION,
        quantity=quantity(fraction, "1"),
        source_reference=f"formula-declaration:{component_id}:v1",
        uncertainty=unknown(),
    )


def exact_matrix() -> MatrixComposition:
    return MatrixComposition(
        matrix_id="matrix:formula-17:finished",
        matrix_version="1",
        stage=MatrixStage.FINISHED_PERFUME,
        components=(
            matrix_component(
                "cas:64-17-5",
                "ethanol",
                MatrixComponentRole.ETHANOL,
                0.8,
            ),
            matrix_component(
                "formula:active-fragrance",
                "active fragrance",
                MatrixComponentRole.ACTIVE_FRAGRANCE,
                0.2,
            ),
        ),
        temperature=quantity(298.15, "K"),
        pressure=quantity(101325.0, "Pa"),
        relative_humidity=None,
        gas_comparison=False,
        total_mass=quantity(25.0, "g"),
        total_volume=quantity(30.0, "mL"),
        uncertainty=unknown("matrix uncertainty not measured"),
        phase_assumptions=("single liquid phase",),
        completeness=CompositionCompleteness.EXACT,
        missing_fields=(),
    )


def sealed_vial_environment() -> ApplicationEnvironment:
    return ApplicationEnvironment(
        environment_id="environment:sealed-vial:spme-1",
        environment_version="1",
        kind=ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL,
        dose=quantity(0.01, "mL"),
        area=quantity(1.0, "cm2"),
        film_thickness=None,
        geometry="2 mL crimp vial with flat liquid surface",
        substrate="borosilicate glass vial lot V-4",
        temperature=quantity(298.15, "K"),
        relative_humidity=quantity(50.0, "%"),
        airflow=quantity(0.0, "m/s"),
        equilibration_or_drying_time=quantity(3600.0, "s"),
        sampling_time=quantity(3600.0, "s"),
        sampling_method="SPME fiber exposed in sealed headspace",
        vessel_volume=quantity(2.0, "mL"),
        headspace_volume=quantity(1.0, "mL"),
        uncertainty=unknown("environment uncertainty not measured"),
        missing_fields=(),
        not_applicable_fields=(EnvironmentField.FILM_THICKNESS,),
    )


def matrix_context() -> MatrixAwareModelRequest:
    return MatrixAwareModelRequest(
        purpose="c3 model-interface contract test",
        formula_id="formula:17",
        formula_sha256=digest("7"),
        matrix=exact_matrix(),
        environment=sealed_vial_environment(),
    )


def applicability_context() -> ApplicabilityContext:
    return ApplicabilityContext(
        identity_ids=("material:water", "material:ethanol"),
        chemical_classes=("water", "alcohol"),
        functional_groups=("hydroxyl",),
        concentration=quantity(0.1, "mole_fraction"),
        phase_behavior="single liquid phase",
        available_properties=(
            ThermophysicalProperty.MOLECULAR_WEIGHT,
            ThermophysicalProperty.VAPOR_PRESSURE,
        ),
        training_calibration_tags=("transparent-baseline",),
    )


def input_reference(
    *,
    role: str = "property_snapshot",
    input_id: str = "property-snapshot:formula-17:v1",
    content_sha256: str = digest("8"),
) -> ModelInputReference:
    return ModelInputReference(
        role=role,
        input_id=input_id,
        content_sha256=content_sha256,
    )


def versioned_request(
    *,
    operation: ModelOperation = ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE,
    requested_model: ModelSelector | None = None,
    request_id: str = "request:c3:formula-17:ideal-raoult",
    context: MatrixAwareModelRequest | None = None,
) -> VersionedModelRequest:
    return VersionedModelRequest(
        request_id=request_id,
        operation=operation,
        requested_model=requested_model or selector(),
        context=context or matrix_context(),
        applicability_context=applicability_context(),
        input_references=(
            input_reference(),
            input_reference(
                role="formula_state",
                input_id="formula-state:17:v1",
                content_sha256=digest("9"),
            ),
        ),
    )


def applicability_result(
    *,
    state: ApplicabilityState = ApplicabilityState.IN_DOMAIN,
    request: VersionedModelRequest | None = None,
    model_release: ModelRelease | None = None,
) -> ApplicabilityResult:
    resolved_request = request or versioned_request()
    resolved_release = model_release or release()
    reasons: tuple[str, ...] = ("all declared bounds satisfied",)
    missing_inputs: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    if state is ApplicabilityState.NEAR_DOMAIN_WITH_WARNING:
        reasons = ("temperature is within the declared warning margin",)
        warnings = ("NEAR_TEMPERATURE_BOUNDARY",)
    elif state is ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN:
        reasons = ("matrix stage is outside the declared domain",)
    elif state is ApplicabilityState.INSUFFICIENT_INPUT:
        reasons = ("a required property is absent",)
        missing_inputs = ("property:vapor_pressure",)
    elif state is ApplicabilityState.MODEL_NOT_VALIDATED:
        reasons = ("model has no applicable validation record",)
    return ApplicabilityResult(
        state=state,
        domain_sha256=resolved_release.applicability_domain.content_sha256,
        request_sha256=resolved_request.content_sha256,
        reasons=reasons,
        missing_inputs=missing_inputs,
        warnings=warnings,
    )


def interval_uncertainty() -> UncertaintyDescriptor:
    return UncertaintyDescriptor.from_mapping(
        {
            "schema": "c1-uncertainty-v1",
            "kind": "INTERVAL",
            "interval_type": "CONFIDENCE",
            "coverage_probability": 0.95,
            "lower": 9.0,
            "upper": 11.0,
            "unit": "Pa",
        }
    )


def model_output() -> ModelOutput:
    return ModelOutput(
        quantity="component partial pressure",
        unit="Pa",
        payload=CanonicalScope.from_mapping({"components": {"material:ethanol": 10.0}}),
    )


def versioned_result(
    *,
    status: ModelResultStatus = ModelResultStatus.COMPUTED,
    state: ApplicabilityState = ApplicabilityState.IN_DOMAIN,
    request: VersionedModelRequest | None = None,
    bound_model: ModelRelease | None = None,
    fallback: FallbackDisclosure | None = None,
) -> VersionedModelResult:
    resolved_request = request or versioned_request()
    resolved_model = bound_model or release(model_selector=resolved_request.requested_model)
    applicability = applicability_result(
        state=state,
        request=resolved_request,
        model_release=resolved_model,
    )
    return VersionedModelResult(
        status=status,
        operation=resolved_request.operation,
        requested_model=resolved_request.requested_model,
        bound_model=resolved_model,
        request=resolved_request,
        output=model_output() if status is ModelResultStatus.COMPUTED else None,
        uncertainty=interval_uncertainty(),
        applicability=applicability,
        missing_inputs=applicability.missing_inputs,
        warnings=applicability.warnings,
        evidence_class=resolved_model.evidence_class,
        may_feed_oav_screening=(
            resolved_model.may_feed_oav_screening if status is ModelResultStatus.COMPUTED else False
        ),
        permitted_claim_wording=resolved_model.permitted_claim_wording,
        forbidden_claim_wording=resolved_model.forbidden_claim_wording,
        fallback=fallback,
    )


def routing_release(
    *,
    version: str = "1.0.0",
    availability: ModelAvailability = ModelAvailability.AVAILABLE,
) -> ModelRelease:
    baseline = replace(
        release(model_selector=selector(version=version)),
        supported_operations=ANSWER_PRODUCING_OPERATIONS,
    )
    if availability is ModelAvailability.AVAILABLE:
        return baseline
    return replace(
        baseline,
        availability=ModelAvailability.UNAVAILABLE,
        unavailable_reason="implementation is not validated for execution",
        evidence_class=ModelEvidenceClass.UNVALIDATED,
        may_feed_oav_screening=False,
    )


class RecordingAdapter:
    """Deterministic call-counting adapter; never scientific evidence."""

    def __init__(
        self,
        model_release: ModelRelease,
        *,
        state: ApplicabilityState = ApplicabilityState.IN_DOMAIN,
        computation: ModelComputation | None = None,
    ) -> None:
        self._release = model_release
        self.state = state
        self.applicability_calls = 0
        self.compute_calls = 0
        self.computation = computation or ModelComputation(
            output=model_output(),
            uncertainty=interval_uncertainty(),
            warnings=("ADAPTER_COMPUTE_WARNING",),
        )

    @property
    def release(self) -> ModelRelease:
        return self._release

    def evaluate_applicability(
        self,
        request: VersionedModelRequest,
    ) -> ApplicabilityResult:
        self.applicability_calls += 1
        return applicability_result(
            state=self.state,
            request=request,
            model_release=self.release,
        )

    def compute(
        self,
        request: VersionedModelRequest,
        applicability: ApplicabilityResult,
    ) -> ModelComputation:
        del request, applicability
        self.compute_calls += 1
        return self.computation

    def simulate_release_drift(self, model_release: ModelRelease) -> None:
        self._release = model_release


def test_c3_closed_vocabularies_are_exact() -> None:
    assert {item.value for item in ModelOperation} == REQUIRED_OPERATIONS
    assert {item.value for item in ModelFamily} == REQUIRED_MODEL_FAMILIES
    assert {item.value for item in ApplicabilityState} == REQUIRED_APPLICABILITY_STATES
    assert {item.value for item in ModelAvailability} == {"AVAILABLE", "UNAVAILABLE"}
    assert {item.value for item in ModelResultStatus} == {"COMPUTED", "ABSTAINED"}
    assert {item.value for item in ModelEvidenceClass} == REQUIRED_EVIDENCE_CLASSES


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"lower": float("nan")}, "finite"),
        ({"upper": float("inf")}, "finite"),
        ({"lower": 2.0, "upper": 1.0}, "lower"),
        ({"unit": " "}, "unit"),
        ({"lower_inclusive": 1}, "lower_inclusive"),
        ({"upper_inclusive": 0}, "upper_inclusive"),
    ],
)
def test_domain_range_is_closed_and_finite(
    changes: dict[str, object],
    message: str,
) -> None:
    valid = DomainRange(
        lower=0.0,
        upper=1.0,
        unit="mole_fraction",
        lower_inclusive=True,
        upper_inclusive=True,
    )
    with pytest.raises(ModelInterfaceContractError, match=message):
        replace(valid, **changes)


def test_applicability_domain_canonicalizes_unordered_collections() -> None:
    baseline = domain()
    reordered = replace(
        baseline,
        supported_identity_ids=tuple(reversed(baseline.supported_identity_ids)),
        supported_chemical_classes=tuple(reversed(baseline.supported_chemical_classes)),
        supported_matrix_stages=tuple(reversed(baseline.supported_matrix_stages)),
        required_properties=tuple(reversed(baseline.required_properties)),
        known_failure_modes=tuple(reversed(baseline.known_failure_modes)),
    )
    assert reordered == baseline
    assert reordered.content_sha256 == baseline.content_sha256


@pytest.mark.parametrize(
    "changes",
    [
        {"domain_version": "2"},
        {"supported_identity_ids": ("material:ethanol",)},
        {"supported_chemical_classes": ("alcohol",)},
        {"supported_functional_groups": ("hydroxyl", "ether")},
        {"supported_matrix_stages": (MatrixStage.FINISHED_PERFUME,)},
        {
            "matrix_range": CanonicalScope.from_mapping(
                {"ethanol_mass_fraction": {"lower": 0.6, "upper": 0.9}}
            )
        },
        {"concentration_range": DomainRange(0.01, 0.9, "mole_fraction", True, True)},
        {"temperature_range": DomainRange(293.15, 303.15, "K", True, True)},
        {"pressure_range": DomainRange(95000.0, 105000.0, "Pa", True, True)},
        {"supported_phase_behaviors": ("single gas phase",)},
        {"supported_environment_kinds": (ApplicationEnvironmentKind.BLOTTER,)},
        {"required_properties": (ThermophysicalProperty.VAPOR_PRESSURE,)},
        {
            "training_calibration_domain": CanonicalScope.from_mapping(
                {"kind": "measured calibration", "dataset": "dataset:1"}
            )
        },
        {"known_failure_modes": ("phase separation",)},
    ],
)
def test_every_applicability_domain_field_changes_hash(
    changes: dict[str, object],
) -> None:
    baseline = domain()
    assert replace(baseline, **changes).content_sha256 != baseline.content_sha256


@pytest.mark.parametrize(
    "changes",
    [
        {"supported_identity_ids": ("material:ethanol", "material:ethanol")},
        {"supported_chemical_classes": ("alcohol", "alcohol")},
        {"supported_functional_groups": ("hydroxyl", "hydroxyl")},
        {
            "supported_matrix_stages": (
                MatrixStage.FINISHED_PERFUME,
                MatrixStage.FINISHED_PERFUME,
            )
        },
        {
            "supported_environment_kinds": (
                ApplicationEnvironmentKind.BLOTTER,
                ApplicationEnvironmentKind.BLOTTER,
            )
        },
        {
            "required_properties": (
                ThermophysicalProperty.VAPOR_PRESSURE,
                ThermophysicalProperty.VAPOR_PRESSURE,
            )
        },
        {"known_failure_modes": ("phase separation", "phase separation")},
    ],
)
def test_applicability_domain_rejects_duplicate_entries(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ModelInterfaceContractError, match="duplicate"):
        replace(domain(), **changes)


def test_applicability_domain_round_trip_and_tamper_detection() -> None:
    baseline = domain()
    payload = baseline.to_mapping()
    assert ApplicabilityDomain.from_mapping(payload) == baseline

    tampered = deepcopy(payload)
    temperature_range = tampered["temperature_range"]
    assert isinstance(temperature_range, dict)
    temperature_range["upper"] = 323.15
    with pytest.raises(ModelInterfaceContractError, match="content_sha256"):
        ApplicabilityDomain.from_mapping(tampered)

    with pytest.raises(ModelInterfaceContractError, match="unknown fields"):
        ApplicabilityDomain.from_mapping({**payload, "notes": []})
    with pytest.raises(ModelInterfaceContractError, match="schema"):
        ApplicabilityDomain.from_mapping({**payload, "schema": "c3-domain-v0"})


@pytest.mark.parametrize(
    "changes",
    [
        {"parameter_set_version": "ideal-no-parameters-v2"},
        {"code_commit": "1" * 40},
        {"implementation_sha256": digest("1")},
        {"parameter_set_sha256": digest("2")},
        {"coefficient_set_sha256": digest("3")},
        {"decomposition_sha256": digest("4")},
        {"training_data_sha256": digest("5")},
        {"applicability_domain": replace(domain(), domain_version="2")},
        {"supported_operations": (ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE,)},
        {"evidence_class": ModelEvidenceClass.LITERATURE_DERIVED},
        {"may_feed_oav_screening": False},
        {"permitted_claim_wording": ("Alternative permitted wording.",)},
        {"forbidden_claim_wording": ("Alternative forbidden wording.",)},
    ],
)
def test_every_model_release_version_input_changes_hash(
    changes: dict[str, object],
) -> None:
    baseline = release()
    assert replace(baseline, **changes).content_sha256 != baseline.content_sha256


def test_model_release_availability_is_fail_closed() -> None:
    baseline = release()
    with pytest.raises(ModelInterfaceContractError, match="unavailable_reason"):
        replace(baseline, unavailable_reason="should not exist")
    with pytest.raises(ModelInterfaceContractError, match="unavailable_reason"):
        replace(
            baseline,
            availability=ModelAvailability.UNAVAILABLE,
            unavailable_reason=None,
            evidence_class=ModelEvidenceClass.UNVALIDATED,
            may_feed_oav_screening=False,
        )
    with pytest.raises(ModelInterfaceContractError, match="UNVALIDATED"):
        replace(
            baseline,
            availability=ModelAvailability.UNAVAILABLE,
            unavailable_reason="implementation is absent",
            may_feed_oav_screening=False,
        )
    with pytest.raises(ModelInterfaceContractError, match="OAV"):
        replace(
            baseline,
            availability=ModelAvailability.UNAVAILABLE,
            unavailable_reason="implementation is absent",
            evidence_class=ModelEvidenceClass.UNVALIDATED,
        )

    unavailable = replace(
        baseline,
        availability=ModelAvailability.UNAVAILABLE,
        unavailable_reason="C0 records this family as unsupported",
        evidence_class=ModelEvidenceClass.UNVALIDATED,
        may_feed_oav_screening=False,
    )
    assert unavailable.availability is ModelAvailability.UNAVAILABLE


@pytest.mark.parametrize(
    "operation",
    [ModelOperation.EVALUATE_APPLICABILITY, ModelOperation.COMPARE_MODELS],
)
def test_model_release_rejects_router_only_supported_operations(
    operation: ModelOperation,
) -> None:
    with pytest.raises(ModelInterfaceContractError, match="supported_operations"):
        replace(release(), supported_operations=(operation,))


def test_model_release_round_trip_and_nested_tamper_detection() -> None:
    baseline = release()
    payload = baseline.to_mapping()
    assert ModelRelease.from_mapping(payload) == baseline

    tampered = deepcopy(payload)
    applicability = tampered["applicability_domain"]
    assert isinstance(applicability, dict)
    applicability["domain_version"] = "tampered"
    with pytest.raises(ModelInterfaceContractError, match="content_sha256"):
        ModelRelease.from_mapping(tampered)

    with pytest.raises(ModelInterfaceContractError, match="unknown fields"):
        ModelRelease.from_mapping({**payload, "mutable": True})
    with pytest.raises(ModelInterfaceContractError, match="schema"):
        ModelRelease.from_mapping({**payload, "schema": "c3-release-v0"})


@pytest.mark.parametrize(
    "changes",
    [
        {"model_version": " "},
        {"family": "IDEAL_RAOULT_BASELINE"},
    ],
)
def test_model_selector_requires_closed_typed_identity(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ModelInterfaceContractError):
        replace(selector(), **changes)


def test_applicability_context_is_canonical_and_hash_bound() -> None:
    baseline = applicability_context()
    reordered = replace(
        baseline,
        identity_ids=tuple(reversed(baseline.identity_ids)),
        chemical_classes=tuple(reversed(baseline.chemical_classes)),
        available_properties=tuple(reversed(baseline.available_properties)),
    )
    assert reordered == baseline
    assert ApplicabilityContext.from_mapping(baseline.to_mapping()) == baseline

    variants = (
        replace(baseline, identity_ids=("material:ethanol",)),
        replace(baseline, chemical_classes=("alcohol",)),
        replace(baseline, functional_groups=("hydroxyl", "ether")),
        replace(baseline, concentration=quantity(0.2, "mole_fraction")),
        replace(baseline, phase_behavior="two liquid phases"),
        replace(
            baseline,
            available_properties=(ThermophysicalProperty.VAPOR_PRESSURE,),
        ),
        replace(baseline, training_calibration_tags=("measured-domain",)),
    )
    assert all(item.content_sha256 != baseline.content_sha256 for item in variants)


@pytest.mark.parametrize(
    "changes",
    [
        {"identity_ids": ("material:ethanol", "material:ethanol")},
        {"chemical_classes": ("alcohol", "alcohol")},
        {"functional_groups": ("hydroxyl", "hydroxyl")},
        {
            "available_properties": (
                ThermophysicalProperty.VAPOR_PRESSURE,
                ThermophysicalProperty.VAPOR_PRESSURE,
            )
        },
        {"training_calibration_tags": ("baseline", "baseline")},
    ],
)
def test_applicability_context_rejects_duplicate_entries(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ModelInterfaceContractError, match="duplicate"):
        replace(applicability_context(), **changes)


@pytest.mark.parametrize(
    ("state", "changes", "message"),
    [
        (
            ApplicabilityState.NEAR_DOMAIN_WITH_WARNING,
            {"warnings": ()},
            "warning",
        ),
        (
            ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN,
            {"reasons": ()},
            "reason",
        ),
        (
            ApplicabilityState.INSUFFICIENT_INPUT,
            {"missing_inputs": ()},
            "missing_inputs",
        ),
        (
            ApplicabilityState.MODEL_NOT_VALIDATED,
            {"reasons": ()},
            "reason",
        ),
    ],
)
def test_applicability_result_enforces_state_shape(
    state: ApplicabilityState,
    changes: dict[str, object],
    message: str,
) -> None:
    baseline = applicability_result(state=state)
    with pytest.raises(ModelInterfaceContractError, match=message):
        replace(baseline, **changes)


def test_applicability_result_round_trip_rejects_tampering() -> None:
    baseline = applicability_result(state=ApplicabilityState.NEAR_DOMAIN_WITH_WARNING)
    payload = baseline.to_mapping()
    assert ApplicabilityResult.from_mapping(payload) == baseline
    with pytest.raises(ModelInterfaceContractError, match="content_sha256"):
        ApplicabilityResult.from_mapping({**payload, "reasons": ["tampered reason"]})
    with pytest.raises(ModelInterfaceContractError, match="unknown fields"):
        ApplicabilityResult.from_mapping({**payload, "score": 0.5})


def test_versioned_request_embeds_complete_c2_context_and_inputs() -> None:
    request = versioned_request()
    payload = request.to_mapping()
    context = payload["context"]
    assert isinstance(context, dict)
    assert context["formula_sha256"] == request.context.formula_sha256
    assert context["matrix_sha256"] == request.context.matrix.content_sha256
    assert context["environment_sha256"] == request.context.environment.content_sha256
    assert context["matrix"] == request.context.matrix.to_mapping()
    assert context["environment"] == request.context.environment.to_mapping()
    input_references = payload["input_references"]
    assert isinstance(input_references, list)
    input_pairs: list[tuple[object, object]] = []
    for item in input_references:
        assert isinstance(item, dict)
        input_pairs.append((item["role"], item["input_id"]))
    assert input_pairs == [
        ("formula_state", "formula-state:17:v1"),
        ("property_snapshot", "property-snapshot:formula-17:v1"),
    ]
    assert VersionedModelRequest.from_mapping(payload) == request


def test_versioned_request_rejects_duplicate_inputs_and_tampering() -> None:
    reference = input_reference()
    with pytest.raises(ModelInterfaceContractError, match="duplicate"):
        replace(
            versioned_request(),
            input_references=(reference, reference),
        )

    payload = deepcopy(versioned_request().to_mapping())
    references = payload["input_references"]
    assert isinstance(references, list)
    first_reference = references[0]
    assert isinstance(first_reference, dict)
    first_reference["content_sha256"] = digest("0")
    with pytest.raises(ModelInterfaceContractError, match="content_sha256"):
        VersionedModelRequest.from_mapping(payload)

    with pytest.raises(ModelInterfaceContractError, match="unknown fields"):
        VersionedModelRequest.from_mapping(
            {**versioned_request().to_mapping(), "default_model": True}
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"role": " "}, "role"),
        ({"input_id": " "}, "input_id"),
        ({"content_sha256": "A" * 64}, "content_sha256"),
    ],
)
def test_model_input_reference_is_strict(
    changes: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ModelInterfaceContractError, match=message):
        replace(input_reference(), **changes)


def test_model_output_is_explicit_and_tamper_evident() -> None:
    baseline = model_output()
    payload = baseline.to_mapping()
    assert payload["quantity"] == "component partial pressure"
    assert payload["unit"] == "Pa"
    assert ModelOutput.from_mapping(payload) == baseline
    assert replace(baseline, unit="kPa").content_sha256 != baseline.content_sha256
    assert (
        replace(
            baseline,
            payload=CanonicalScope.from_mapping({"components": {"material:ethanol": 11.0}}),
        ).content_sha256
        != baseline.content_sha256
    )
    with pytest.raises(ModelInterfaceContractError, match="content_sha256"):
        ModelOutput.from_mapping({**payload, "quantity": "tampered"})


def test_computed_result_exposes_every_authoritative_field() -> None:
    result = versioned_result()
    payload = result.to_mapping()
    assert payload["status"] == "COMPUTED"
    assert payload["operation"] == "predict_equilibrium_headspace"
    assert payload["requested_model"] == result.requested_model.to_mapping()
    assert payload["bound_model"] == result.bound_model.to_mapping()
    assert payload["request"] == result.request.to_mapping()
    assert result.output is not None
    assert payload["output"] == result.output.to_mapping()
    assert payload["uncertainty"] == result.uncertainty.payload.to_mapping()
    assert payload["applicability"] == result.applicability.to_mapping()
    assert payload["missing_inputs"] == []
    assert payload["evidence_class"] == "THEORETICAL_BASELINE"
    assert payload["may_feed_oav_screening"] is True
    assert payload["permitted_claim_wording"]
    assert payload["forbidden_claim_wording"]
    assert payload["fallback"] is None
    assert VersionedModelResult.from_mapping(payload) == result


@pytest.mark.parametrize(
    "state",
    [
        ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN,
        ApplicabilityState.INSUFFICIENT_INPUT,
        ApplicabilityState.MODEL_NOT_VALIDATED,
    ],
)
def test_non_applicable_states_reject_computed_results(
    state: ApplicabilityState,
) -> None:
    with pytest.raises(ModelInterfaceContractError, match="COMPUTED"):
        versioned_result(state=state)


def test_abstained_result_has_no_output_and_cannot_feed_oav() -> None:
    result = versioned_result(
        status=ModelResultStatus.ABSTAINED,
        state=ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN,
    )
    assert result.output is None
    assert result.may_feed_oav_screening is False
    payload = result.to_mapping()
    assert payload["output"] is None
    assert VersionedModelResult.from_mapping(payload) == result
    with pytest.raises(ModelInterfaceContractError, match="output"):
        replace(result, output=model_output())
    with pytest.raises(ModelInterfaceContractError, match="OAV"):
        replace(result, may_feed_oav_screening=True)


def test_result_rejects_request_model_or_domain_mismatch() -> None:
    result = versioned_result()
    with pytest.raises(ModelInterfaceContractError, match="operation"):
        replace(result, operation=ModelOperation.PREDICT_DYNAMIC_RELEASE)
    with pytest.raises(ModelInterfaceContractError, match="request"):
        replace(
            result,
            applicability=replace(
                result.applicability,
                request_sha256=digest("0"),
            ),
        )
    with pytest.raises(ModelInterfaceContractError, match="domain"):
        replace(
            result,
            applicability=replace(
                result.applicability,
                domain_sha256=digest("0"),
            ),
        )


def test_result_requires_complete_fallback_disclosure_for_model_change() -> None:
    request = versioned_request()
    fallback_selector = ModelSelector(
        family=ModelFamily.LEGACY_HEURISTIC_ADAPTER,
        model_version="legacy-1",
    )
    fallback_model = replace(
        release(model_selector=fallback_selector),
        evidence_class=ModelEvidenceClass.LEGACY_HEURISTIC,
        may_feed_oav_screening=False,
        permitted_claim_wording=("Legacy diagnostic comparison only.",),
        forbidden_claim_wording=("Canonical physical prediction.",),
    )
    with pytest.raises(ModelInterfaceContractError, match="fallback"):
        versioned_result(request=request, bound_model=fallback_model)

    disclosure = FallbackDisclosure(
        requested_model=request.requested_model,
        reason_unavailable="requested implementation unavailable",
        fallback_model=fallback_selector,
        authority_downgrade="canonical request downgraded to legacy diagnostic",
    )
    result = versioned_result(
        request=request,
        bound_model=fallback_model,
        fallback=disclosure,
    )
    assert result.bound_model.selector == fallback_selector
    assert VersionedModelResult.from_mapping(result.to_mapping()) == result
    with pytest.raises(ModelInterfaceContractError, match="requested"):
        replace(
            result,
            fallback=replace(disclosure, requested_model=fallback_selector),
        )
    with pytest.raises(ModelInterfaceContractError, match="fallback model"):
        replace(
            result,
            fallback=replace(disclosure, fallback_model=request.requested_model),
        )


def test_fallback_disclosure_rejects_same_selector_and_tampering() -> None:
    requested = selector()
    with pytest.raises(ModelInterfaceContractError, match="differ"):
        FallbackDisclosure(
            requested_model=requested,
            reason_unavailable="not available",
            fallback_model=requested,
            authority_downgrade="screening only",
        )
    disclosure = FallbackDisclosure(
        requested_model=requested,
        reason_unavailable="not available",
        fallback_model=ModelSelector(
            family=ModelFamily.LEGACY_HEURISTIC_ADAPTER,
            model_version="legacy-1",
        ),
        authority_downgrade="screening only",
    )
    payload = disclosure.to_mapping()
    assert FallbackDisclosure.from_mapping(payload) == disclosure
    with pytest.raises(ModelInterfaceContractError, match="content_sha256"):
        FallbackDisclosure.from_mapping({**payload, "authority_downgrade": "tampered"})


def test_result_parser_rejects_nested_and_top_level_tampering() -> None:
    payload = deepcopy(versioned_result().to_mapping())
    bound_model = payload["bound_model"]
    assert isinstance(bound_model, dict)
    bound_model["parameter_set_version"] = "tampered"
    with pytest.raises(ModelInterfaceContractError, match="content_sha256"):
        VersionedModelResult.from_mapping(payload)

    baseline = versioned_result().to_mapping()
    with pytest.raises(ModelInterfaceContractError, match="unknown fields"):
        VersionedModelResult.from_mapping({**baseline, "winner": "ideal"})
    with pytest.raises(ModelInterfaceContractError, match="schema"):
        VersionedModelResult.from_mapping({**baseline, "schema": "c3-model-result-v0"})


def route_request(
    router: VersionedModelRouter,
    request: VersionedModelRequest,
) -> VersionedModelResult:
    if request.operation is ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE:
        return router.predict_equilibrium_headspace(request)
    if request.operation is ModelOperation.PREDICT_DYNAMIC_RELEASE:
        return router.predict_dynamic_release(request)
    if request.operation is ModelOperation.ESTIMATE_PARTITION_COEFFICIENT:
        return router.estimate_partition_coefficient(request)
    if request.operation is ModelOperation.PROPAGATE_UNCERTAINTY:
        return router.propagate_uncertainty(request)
    raise AssertionError(f"unsupported test operation: {request.operation.value}")


def test_versioned_model_adapter_is_runtime_checkable() -> None:
    adapter = RecordingAdapter(routing_release())
    assert isinstance(adapter, VersionedModelAdapter)
    assert not isinstance(object(), VersionedModelAdapter)


@pytest.mark.parametrize(
    "changes",
    [
        {"coefficient_set_sha256": digest("1")},
        {"code_commit": "1" * 40},
        {"training_data_sha256": digest("2")},
        {"applicability_domain": replace(domain(), domain_version="2")},
    ],
)
def test_router_rejects_duplicate_selectors_despite_release_drift(
    changes: dict[str, object],
) -> None:
    baseline = routing_release()
    changed = replace(baseline, **changes)
    assert changed.selector == baseline.selector
    assert changed.content_sha256 != baseline.content_sha256
    with pytest.raises(ModelInterfaceContractError, match="duplicate.*selector"):
        VersionedModelRouter((RecordingAdapter(baseline), RecordingAdapter(changed)))


def test_router_accepts_same_family_with_new_explicit_version() -> None:
    first = RecordingAdapter(routing_release(version="1.0.0"))
    second = RecordingAdapter(routing_release(version="2.0.0"))
    router = VersionedModelRouter((first, second))

    request = versioned_request(requested_model=second.release.selector)
    result = router.evaluate_applicability(request)

    assert result.request_sha256 == request.content_sha256
    assert first.applicability_calls == 0
    assert second.applicability_calls == 1


def test_unknown_selector_fails_closed_without_silent_fallback() -> None:
    known = RecordingAdapter(routing_release())
    router = VersionedModelRouter((known,))
    request = versioned_request(requested_model=selector(version="99.0.0"))

    with pytest.raises(ModelInterfaceContractError, match="not registered"):
        router.predict_equilibrium_headspace(request)

    assert known.applicability_calls == 0
    assert known.compute_calls == 0


@pytest.mark.parametrize(
    ("method_name", "wrong_operation"),
    [
        ("predict_equilibrium_headspace", ModelOperation.PREDICT_DYNAMIC_RELEASE),
        ("predict_dynamic_release", ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE),
        (
            "estimate_partition_coefficient",
            ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE,
        ),
        ("propagate_uncertainty", ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE),
    ],
)
def test_answer_methods_reject_requests_for_other_operations(
    method_name: str,
    wrong_operation: ModelOperation,
) -> None:
    adapter = RecordingAdapter(routing_release())
    router = VersionedModelRouter((adapter,))
    request = versioned_request(
        operation=wrong_operation,
        requested_model=adapter.release.selector,
    )

    with pytest.raises(ModelInterfaceContractError, match="operation"):
        getattr(router, method_name)(request)

    assert adapter.applicability_calls == 0
    assert adapter.compute_calls == 0


def test_router_rejects_operation_not_supported_by_exact_release() -> None:
    adapter = RecordingAdapter(release())
    router = VersionedModelRouter((adapter,))
    request = versioned_request(
        operation=ModelOperation.PREDICT_DYNAMIC_RELEASE,
        requested_model=adapter.release.selector,
    )

    with pytest.raises(ModelInterfaceContractError, match="does not support"):
        router.predict_dynamic_release(request)

    assert adapter.applicability_calls == 0
    assert adapter.compute_calls == 0


def test_evaluate_applicability_resolves_only_exact_release() -> None:
    first = RecordingAdapter(
        routing_release(version="1.0.0"),
        state=ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN,
    )
    second = RecordingAdapter(
        routing_release(version="2.0.0"),
        state=ApplicabilityState.NEAR_DOMAIN_WITH_WARNING,
    )
    router = VersionedModelRouter((first, second))
    request = versioned_request(requested_model=second.release.selector)

    result = router.evaluate_applicability(request)

    assert result.state is ApplicabilityState.NEAR_DOMAIN_WITH_WARNING
    assert result.domain_sha256 == second.release.applicability_domain.content_sha256
    assert first.applicability_calls == 0
    assert second.applicability_calls == 1
    assert first.compute_calls == second.compute_calls == 0


@pytest.mark.parametrize(
    "state",
    [
        ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN,
        ApplicabilityState.INSUFFICIENT_INPUT,
        ApplicabilityState.MODEL_NOT_VALIDATED,
    ],
)
def test_router_abstains_without_compute_for_noncomputable_states(
    state: ApplicabilityState,
) -> None:
    adapter = RecordingAdapter(routing_release(), state=state)
    router = VersionedModelRouter((adapter,))
    request = versioned_request(requested_model=adapter.release.selector)

    try:
        result = router.predict_equilibrium_headspace(request)
    finally:
        assert adapter.applicability_calls == 1
        assert adapter.compute_calls == 0

    assert result.status is ModelResultStatus.ABSTAINED
    assert result.applicability.state is state
    assert result.output is None
    assert result.may_feed_oav_screening is False
    assert result.fallback is None


def test_unavailable_release_returns_not_validated_without_adapter_calls() -> None:
    adapter = RecordingAdapter(routing_release(availability=ModelAvailability.UNAVAILABLE))
    router = VersionedModelRouter((adapter,))
    request = versioned_request(requested_model=adapter.release.selector)

    result = router.predict_equilibrium_headspace(request)

    assert result.status is ModelResultStatus.ABSTAINED
    assert result.applicability.state is ApplicabilityState.MODEL_NOT_VALIDATED
    assert result.applicability.reasons == (adapter.release.unavailable_reason,)
    assert result.evidence_class is ModelEvidenceClass.UNVALIDATED
    assert adapter.applicability_calls == 0
    assert adapter.compute_calls == 0


def test_near_domain_computes_and_preserves_all_warnings() -> None:
    adapter = RecordingAdapter(
        routing_release(),
        state=ApplicabilityState.NEAR_DOMAIN_WITH_WARNING,
    )
    router = VersionedModelRouter((adapter,))
    request = versioned_request(requested_model=adapter.release.selector)

    result = router.predict_equilibrium_headspace(request)

    assert result.status is ModelResultStatus.COMPUTED
    assert result.warnings == (
        "ADAPTER_COMPUTE_WARNING",
        "NEAR_TEMPERATURE_BOUNDARY",
    )
    assert result.fallback is None
    assert adapter.applicability_calls == 1
    assert adapter.compute_calls == 1


def test_computed_result_carries_exact_immutable_release_snapshot() -> None:
    model_release = routing_release()
    adapter = RecordingAdapter(model_release)
    router = VersionedModelRouter((adapter,))
    request = versioned_request(requested_model=model_release.selector)

    result = router.predict_equilibrium_headspace(request)

    assert result.bound_model is model_release
    assert result.bound_model.content_sha256 == model_release.content_sha256
    assert result.to_mapping()["bound_model"] == model_release.to_mapping()


def test_adding_new_release_cannot_change_prior_result_mapping_or_hash() -> None:
    first_release = routing_release(version="1.0.0")
    request = versioned_request(requested_model=first_release.selector)
    initial = VersionedModelRouter(
        (RecordingAdapter(first_release),)
    ).predict_equilibrium_headspace(request)

    expanded = VersionedModelRouter(
        (
            RecordingAdapter(first_release),
            RecordingAdapter(routing_release(version="2.0.0")),
        )
    ).predict_equilibrium_headspace(request)

    assert expanded.to_mapping() == initial.to_mapping()
    assert expanded.content_sha256 == initial.content_sha256


@pytest.mark.parametrize(
    ("method_name", "operation"),
    [
        (
            "predict_equilibrium_headspace",
            ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE,
        ),
        ("predict_dynamic_release", ModelOperation.PREDICT_DYNAMIC_RELEASE),
        (
            "estimate_partition_coefficient",
            ModelOperation.ESTIMATE_PARTITION_COEFFICIENT,
        ),
        ("propagate_uncertainty", ModelOperation.PROPAGATE_UNCERTAINTY),
    ],
)
def test_no_answer_method_creates_fallback_disclosure(
    method_name: str,
    operation: ModelOperation,
) -> None:
    adapter = RecordingAdapter(routing_release())
    router = VersionedModelRouter((adapter,))
    request = versioned_request(
        operation=operation,
        requested_model=adapter.release.selector,
    )

    result = getattr(router, method_name)(request)

    assert result.fallback is None
    assert result.requested_model == result.bound_model.selector


def test_router_rejects_adapter_release_drift_after_registration() -> None:
    adapter = RecordingAdapter(routing_release())
    router = VersionedModelRouter((adapter,))
    request = versioned_request(requested_model=adapter.release.selector)
    adapter.simulate_release_drift(replace(adapter.release, coefficient_set_sha256=digest("1")))

    with pytest.raises(ModelInterfaceContractError, match="release drift"):
        router.predict_equilibrium_headspace(request)

    assert adapter.applicability_calls == 0
    assert adapter.compute_calls == 0


def test_compare_models_returns_complete_unranked_snapshots() -> None:
    first = RecordingAdapter(routing_release(version="1.0.0"))
    second = RecordingAdapter(routing_release(version="2.0.0"))
    router = VersionedModelRouter((first, second))
    context = matrix_context()
    first_result = router.predict_equilibrium_headspace(
        versioned_request(
            requested_model=first.release.selector,
            request_id="request:c3:comparison:first",
            context=context,
        )
    )
    second_result = router.predict_equilibrium_headspace(
        versioned_request(
            requested_model=second.release.selector,
            request_id="request:c3:comparison:second",
            context=context,
        )
    )

    comparison = router.compare_models(
        "comparison:c3:ideal-versions",
        (second_result, first_result),
    )
    payload = comparison.to_mapping()

    assert comparison.operation is ModelOperation.COMPARE_MODELS
    assert comparison.compared_operation is ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE
    assert comparison.results == (first_result, second_result)
    assert payload["results"] == [
        first_result.to_mapping(),
        second_result.to_mapping(),
    ]
    assert {"score", "rank", "winner", "default_model"}.isdisjoint(payload)
    assert ModelComparisonResult.from_mapping(payload) == comparison


def test_compare_models_rejects_incomplete_or_incompatible_sets() -> None:
    first = RecordingAdapter(routing_release(version="1.0.0"))
    second = RecordingAdapter(routing_release(version="2.0.0"))
    router = VersionedModelRouter((first, second))
    context = matrix_context()
    first_result = router.predict_equilibrium_headspace(
        versioned_request(
            requested_model=first.release.selector,
            request_id="request:c3:comparison:first",
            context=context,
        )
    )
    second_result = router.predict_equilibrium_headspace(
        versioned_request(
            requested_model=second.release.selector,
            request_id="request:c3:comparison:second",
            context=context,
        )
    )
    different_operation = router.propagate_uncertainty(
        versioned_request(
            operation=ModelOperation.PROPAGATE_UNCERTAINTY,
            requested_model=second.release.selector,
            request_id="request:c3:comparison:uncertainty",
            context=context,
        )
    )
    different_context = replace(
        context,
        formula_id="formula:18",
        formula_sha256=digest("1"),
    )
    mismatched_context_result = router.predict_equilibrium_headspace(
        versioned_request(
            requested_model=second.release.selector,
            request_id="request:c3:comparison:different-context",
            context=different_context,
        )
    )

    with pytest.raises(ModelInterfaceContractError, match="at least two"):
        router.compare_models("comparison:one", (first_result,))
    with pytest.raises(ModelInterfaceContractError, match="unique.*selector"):
        router.compare_models("comparison:duplicate", (first_result, first_result))
    with pytest.raises(ModelInterfaceContractError, match="same operation"):
        router.compare_models(
            "comparison:operation-mismatch",
            (first_result, different_operation),
        )
    with pytest.raises(ModelInterfaceContractError, match="context hash"):
        router.compare_models(
            "comparison:context-mismatch",
            (first_result, mismatched_context_result),
        )
    assert second_result.request.context.content_sha256 == context.content_sha256


def test_comparison_mapping_rejects_nested_and_top_level_tampering() -> None:
    first = RecordingAdapter(routing_release(version="1.0.0"))
    second = RecordingAdapter(routing_release(version="2.0.0"))
    router = VersionedModelRouter((first, second))
    first_result = router.predict_equilibrium_headspace(
        versioned_request(requested_model=first.release.selector)
    )
    second_result = router.predict_equilibrium_headspace(
        versioned_request(requested_model=second.release.selector)
    )
    payload = router.compare_models(
        "comparison:c3:tamper-check",
        (first_result, second_result),
    ).to_mapping()

    nested = deepcopy(payload)
    nested_results = nested["results"]
    assert isinstance(nested_results, list)
    first_payload = nested_results[0]
    assert isinstance(first_payload, dict)
    first_payload["status"] = "ABSTAINED"
    with pytest.raises(
        ModelInterfaceContractError,
        match="ABSTAINED|content_sha256",
    ):
        ModelComparisonResult.from_mapping(nested)

    with pytest.raises(ModelInterfaceContractError, match="unknown fields"):
        ModelComparisonResult.from_mapping({**payload, "winner": "1.0.0"})


def test_c3_types_are_explicitly_exported_from_engine_physics() -> None:
    import engine.physics as physics
    from engine.physics import ApplicabilityContext as PublicApplicabilityContext
    from engine.physics import ApplicabilityDomain as PublicApplicabilityDomain
    from engine.physics import ApplicabilityResult as PublicApplicabilityResult
    from engine.physics import ApplicabilityState as PublicApplicabilityState
    from engine.physics import DomainRange as PublicDomainRange
    from engine.physics import FallbackDisclosure as PublicFallbackDisclosure
    from engine.physics import ModelAvailability as PublicModelAvailability
    from engine.physics import ModelComparisonResult as PublicModelComparisonResult
    from engine.physics import ModelComputation as PublicModelComputation
    from engine.physics import ModelEvidenceClass as PublicModelEvidenceClass
    from engine.physics import ModelFamily as PublicModelFamily
    from engine.physics import ModelInputReference as PublicModelInputReference
    from engine.physics import (
        ModelInterfaceContractError as PublicModelInterfaceContractError,
    )
    from engine.physics import ModelOperation as PublicModelOperation
    from engine.physics import ModelOutput as PublicModelOutput
    from engine.physics import ModelRelease as PublicModelRelease
    from engine.physics import ModelResultStatus as PublicModelResultStatus
    from engine.physics import ModelSelector as PublicModelSelector
    from engine.physics import VersionedModelAdapter as PublicVersionedModelAdapter
    from engine.physics import VersionedModelRequest as PublicVersionedModelRequest
    from engine.physics import VersionedModelResult as PublicVersionedModelResult
    from engine.physics import VersionedModelRouter as PublicVersionedModelRouter

    public_bindings = {
        "ApplicabilityContext": PublicApplicabilityContext,
        "ApplicabilityDomain": PublicApplicabilityDomain,
        "ApplicabilityResult": PublicApplicabilityResult,
        "ApplicabilityState": PublicApplicabilityState,
        "DomainRange": PublicDomainRange,
        "FallbackDisclosure": PublicFallbackDisclosure,
        "ModelAvailability": PublicModelAvailability,
        "ModelComparisonResult": PublicModelComparisonResult,
        "ModelComputation": PublicModelComputation,
        "ModelEvidenceClass": PublicModelEvidenceClass,
        "ModelFamily": PublicModelFamily,
        "ModelInputReference": PublicModelInputReference,
        "ModelInterfaceContractError": PublicModelInterfaceContractError,
        "ModelOperation": PublicModelOperation,
        "ModelOutput": PublicModelOutput,
        "ModelRelease": PublicModelRelease,
        "ModelResultStatus": PublicModelResultStatus,
        "ModelSelector": PublicModelSelector,
        "VersionedModelAdapter": PublicVersionedModelAdapter,
        "VersionedModelRequest": PublicVersionedModelRequest,
        "VersionedModelResult": PublicVersionedModelResult,
        "VersionedModelRouter": PublicVersionedModelRouter,
    }
    direct_bindings = {
        "ApplicabilityContext": ApplicabilityContext,
        "ApplicabilityDomain": ApplicabilityDomain,
        "ApplicabilityResult": ApplicabilityResult,
        "ApplicabilityState": ApplicabilityState,
        "DomainRange": DomainRange,
        "FallbackDisclosure": FallbackDisclosure,
        "ModelAvailability": ModelAvailability,
        "ModelComparisonResult": ModelComparisonResult,
        "ModelComputation": ModelComputation,
        "ModelEvidenceClass": ModelEvidenceClass,
        "ModelFamily": ModelFamily,
        "ModelInputReference": ModelInputReference,
        "ModelInterfaceContractError": ModelInterfaceContractError,
        "ModelOperation": ModelOperation,
        "ModelOutput": ModelOutput,
        "ModelRelease": ModelRelease,
        "ModelResultStatus": ModelResultStatus,
        "ModelSelector": ModelSelector,
        "VersionedModelAdapter": VersionedModelAdapter,
        "VersionedModelRequest": VersionedModelRequest,
        "VersionedModelResult": VersionedModelResult,
        "VersionedModelRouter": VersionedModelRouter,
    }

    assert public_bindings == direct_bindings
    assert set(physics.__all__) == (
        PUBLIC_C1_NAMES | PUBLIC_C2_NAMES | PUBLIC_C3_NAMES | PUBLIC_C4_NAMES
    )
    assert len(physics.__all__) == len(set(physics.__all__))
    assert "does not evaluate" in (physics.__doc__ or "").lower()
    assert "does not authorize scientific release" in (physics.__doc__ or "").lower()


def test_c3_module_has_no_runtime_equation_or_persistence_dependency() -> None:
    source_path = Path(__file__).resolve().parents[1] / "engine" / "physics" / "model_interface.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    imported_modules: set[str] = set()
    prohibited_calls: set[str] = set()
    scientific_math_calls: set[str] = set()
    scientific_arithmetic: set[str] = set()
    numeric_coefficient_assignments: set[str] = set()

    forbidden_import_prefixes = (
        "backend",
        "sqlalchemy",
        "engine.persistence",
        "engine.database",
        "engine.repositories",
        "engine.workbench",
        "engine.optimizer",
        "engine.mixture",
        "engine.solvent_matrix",
        "engine.headspace",
        "engine.thermo",
        "engine.temporal",
        "engine.property_estimator",
        "engine.vapor_pressure_modeling",
        "engine.diffusion_model",
        "engine.hedonic_model",
        "future_modules",
    )
    forbidden_call_names = {
        "connect",
        "create_engine",
        "dump",
        "execute",
        "fit",
        "open",
        "read_sql",
        "save",
        "to_sql",
        "urlopen",
        "write",
        "write_bytes",
        "write_text",
        "writelines",
    }
    scientific_operator_types = (
        ast.Div,
        ast.FloorDiv,
        ast.MatMult,
        ast.Mod,
        ast.Mult,
        ast.Pow,
    )
    coefficient_tokens = (
        "activity",
        "antoine",
        "coefficient",
        "diffusion",
        "henry",
        "partition",
        "raoult",
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                call_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                call_name = node.func.attr
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "math":
                    if call_name != "isfinite":
                        scientific_math_calls.add(call_name)
            else:
                call_name = ""
            if call_name in forbidden_call_names:
                prohibited_calls.add(call_name)
        elif isinstance(node, ast.BinOp) and isinstance(
            node.op,
            scientific_operator_types,
        ):
            scientific_arithmetic.add(type(node.op).__name__)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if not isinstance(value, ast.Constant) or not isinstance(
                value.value,
                (int, float),
            ):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
            for target in targets:
                if isinstance(target, ast.Name) and any(
                    token in target.id.casefold() for token in coefficient_tokens
                ):
                    numeric_coefficient_assignments.add(target.id)

    assert not any(module.startswith(forbidden_import_prefixes) for module in imported_modules)
    assert prohibited_calls == set()
    assert scientific_math_calls == set()
    assert scientific_arithmetic == set()
    assert numeric_coefficient_assignments == set()
