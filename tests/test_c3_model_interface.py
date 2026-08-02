from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

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
    ModelEvidenceClass,
    ModelFamily,
    ModelInputReference,
    ModelInterfaceContractError,
    ModelOperation,
    ModelOutput,
    ModelRelease,
    ModelResultStatus,
    ModelSelector,
    VersionedModelRequest,
    VersionedModelResult,
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
) -> VersionedModelRequest:
    return VersionedModelRequest(
        request_id="request:c3:formula-17:ideal-raoult",
        operation=operation,
        requested_model=requested_model or selector(),
        context=matrix_context(),
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
