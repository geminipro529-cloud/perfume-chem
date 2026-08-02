from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from pathlib import Path

import engine.physics.equilibrium as equilibrium_module
import pytest
from engine.physics.equilibrium import (
    C4_INPUT_ROLE,
    EquilibriumModelContractError,
    IdealRaoultAdapter,
    IdealRaoultInputSet,
    SelectedNumericPropertyInput,
    withheld_equilibrium_adapters,
)

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
    MatrixMissingField,
    MatrixQuantityBasis,
    MatrixStage,
)
from engine.physics.model_interface import (
    ApplicabilityContext,
    ApplicabilityState,
    ModelAvailability,
    ModelEvidenceClass,
    ModelFamily,
    ModelInputReference,
    ModelOperation,
    ModelResultStatus,
    VersionedModelRequest,
    VersionedModelResult,
    VersionedModelRouter,
)
from engine.physics.properties import (
    CanonicalScope,
    ClaimGrade,
    PropertyConditions,
    PropertyDatum,
    PropertyIdentity,
    PropertyValueKind,
    SelectionStatus,
    SourceReference,
    ThermophysicalProperty,
    UncertaintyDescriptor,
    UncertaintyKind,
)
from engine.physics.selection import (
    AuthorityState,
    InterpolationState,
    PropertyRequest,
    PropertySelectionResult,
)

CODE_COMMIT = "a" * 40
IMPLEMENTATION_SHA256 = "b" * 64
FORMULA_SHA256 = "c" * 64
TEMPERATURE_K = 298.15
SYSTEM_PRESSURE_PA = 101_325.0


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def unknown(reason: str = "not quantified") -> UncertaintyDescriptor:
    return UncertaintyDescriptor.unknown(reason)


def standard_uncertainty(unit: str) -> UncertaintyDescriptor:
    return UncertaintyDescriptor.from_mapping(
        {
            "schema": "c1-uncertainty-v1",
            "kind": "STANDARD_UNCERTAINTY",
            "value": 0.1,
            "unit": unit,
        }
    )


def quantity(value: float, unit: str) -> DeclaredQuantity:
    return DeclaredQuantity(value=value, unit=unit)


def identity(component_id: str) -> PropertyIdentity:
    return PropertyIdentity(
        identity_scope="CHEMICAL_ENTITY",
        subject=CanonicalScope.from_mapping({"component_id": component_id}),
    )


def property_request(
    component_id: str,
    property_type: ThermophysicalProperty,
    *,
    temperature_k: float = TEMPERATURE_K,
) -> PropertyRequest:
    conditions = (
        {"temperature_k": temperature_k, "phase": "liquid", "purity_fraction": 1.0}
        if property_type is ThermophysicalProperty.VAPOR_PRESSURE
        else {"phase": "liquid"}
    )
    return PropertyRequest(
        identity=identity(component_id),
        property_type=property_type,
        conditions=PropertyConditions.from_mapping(conditions),
        claim_grade=ClaimGrade.RELEASE_GRADE,
    )


def selected_result(
    request: PropertyRequest,
    value: float,
    unit: str,
) -> PropertySelectionResult:
    datum = PropertyDatum(
        value_kind=PropertyValueKind.NUMERIC,
        canonical_unit=unit,
        numeric_value=value,
    )
    source = SourceReference.from_b2_observation(
        {
            "source_version_id": f"source:{request.property_type.value}:v1",
            "extraction_record_id": f"extract:{request.identity.content_sha256[:12]}",
            "source_locator": {
                "record": request.identity.content_sha256,
                "property": request.property_type.value,
            },
        }
    )
    return PropertySelectionResult(
        status=SelectionStatus.SELECTED,
        datum=datum,
        model=None,
        canonical_unit=unit,
        source=source,
        conditions=request.conditions,
        uncertainty=standard_uncertainty(unit),
        interpolation_state=InterpolationState.EXACT,
        applicability=CanonicalScope.from_mapping({"applicable": True}),
        authority_state=AuthorityState.AUTHORIZED_FOR_SCOPED_PROPERTY,
        missing_reason=None,
        warnings=(),
        request_sha256=request.content_sha256,
        assertion_sha256=digest(f"{request.identity.content_sha256}:{request.property_type.value}"),
    )


def selected_input(
    component_id: str,
    property_type: ThermophysicalProperty,
    value: float,
    unit: str,
    *,
    temperature_k: float = TEMPERATURE_K,
) -> SelectedNumericPropertyInput:
    request = property_request(
        component_id,
        property_type,
        temperature_k=temperature_k,
    )
    return SelectedNumericPropertyInput.from_selection(
        component_id=component_id,
        request=request,
        selection=selected_result(request, value, unit),
    )


def component(
    component_id: str,
    name: str,
    role: MatrixComponentRole,
    value: float,
    basis: MatrixQuantityBasis,
    unit: str,
) -> MatrixComponent:
    return MatrixComponent(
        component_id=component_id,
        name=name,
        role=role,
        basis=basis,
        quantity=quantity(value, unit),
        source_reference=f"formula-declaration:{component_id}:v1",
        uncertainty=unknown(),
    )


def exact_matrix(
    *,
    basis: MatrixQuantityBasis = MatrixQuantityBasis.MOLE_FRACTION,
    values: tuple[float, ...] = (0.5, 0.5),
    unit: str | None = None,
    component_ids: tuple[str, ...] = ("component:a", "component:b"),
    pressure_pa: float = SYSTEM_PRESSURE_PA,
    pressure_unit: str = "Pa",
    temperature_k: float = TEMPERATURE_K,
    temperature_unit: str = "K",
    stage: MatrixStage = MatrixStage.FINISHED_PERFUME,
    phase_assumptions: tuple[str, ...] = ("single_liquid_phase",),
    total_mass: DeclaredQuantity | None = None,
) -> MatrixComposition:
    if unit is None:
        unit = "1" if basis.name.endswith("FRACTION") else "g"
        if basis is MatrixQuantityBasis.AMOUNT:
            unit = "mol"
    roles = (MatrixComponentRole.ETHANOL, MatrixComponentRole.ACTIVE_FRAGRANCE)
    names = ("component A", "component B")
    if len(values) == 1:
        roles = (MatrixComponentRole.ACTIVE_FRAGRANCE,)
        names = ("component A",)
    components = tuple(
        component(component_id, name, role, value, basis, unit)
        for component_id, name, role, value in zip(
            component_ids,
            names,
            roles,
            values,
            strict=True,
        )
    )
    declared_mass = total_mass
    if declared_mass is None:
        declared_mass = (
            quantity(math.fsum(values), unit)
            if basis is MatrixQuantityBasis.MASS
            else quantity(1.0, "g")
        )
    return MatrixComposition(
        matrix_id="matrix:c4:ideal-baseline",
        matrix_version="1",
        stage=stage,
        components=components,
        temperature=quantity(temperature_k, temperature_unit),
        pressure=quantity(pressure_pa, pressure_unit),
        relative_humidity=quantity(50.0, "%"),
        gas_comparison=True,
        total_mass=declared_mass,
        total_volume=quantity(1.0, "mL"),
        uncertainty=unknown("matrix uncertainty is not propagated in C4"),
        phase_assumptions=phase_assumptions,
        completeness=CompositionCompleteness.EXACT,
        missing_fields=(),
    )


def sealed_environment(
    *,
    temperature_k: float = TEMPERATURE_K,
    temperature_unit: str = "K",
    kind: ApplicationEnvironmentKind = ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL,
) -> ApplicationEnvironment:
    return ApplicationEnvironment(
        environment_id="environment:c4:sealed-vial",
        environment_version="1",
        kind=kind,
        dose=quantity(0.01, "mL"),
        area=quantity(1.0, "cm2"),
        film_thickness=None,
        geometry="2 mL equilibrium vial",
        substrate="borosilicate glass",
        temperature=quantity(temperature_k, temperature_unit),
        relative_humidity=quantity(50.0, "%"),
        airflow=quantity(0.0, "m/s"),
        equilibration_or_drying_time=quantity(3600.0, "s"),
        sampling_time=quantity(3600.0, "s"),
        sampling_method="equilibrium headspace",
        vessel_volume=quantity(2.0, "mL"),
        headspace_volume=quantity(1.0, "mL"),
        uncertainty=unknown("environment uncertainty is not propagated in C4"),
        missing_fields=(),
        not_applicable_fields=(EnvironmentField.FILM_THICKNESS,),
    )


def input_set(
    *,
    component_ids: tuple[str, ...] = ("component:a", "component:b"),
    vapor_pressures_pa: tuple[float, ...] = (100.0, 50.0),
    molecular_weights: tuple[float, ...] = (50.0, 100.0),
    vapor_pressure_temperature_k: float = TEMPERATURE_K,
) -> IdealRaoultInputSet:
    properties: list[SelectedNumericPropertyInput] = []
    for component_id, vapor_pressure, molecular_weight in zip(
        component_ids,
        vapor_pressures_pa,
        molecular_weights,
        strict=True,
    ):
        properties.extend(
            (
                selected_input(
                    component_id,
                    ThermophysicalProperty.VAPOR_PRESSURE,
                    vapor_pressure,
                    "Pa",
                    temperature_k=vapor_pressure_temperature_k,
                ),
                selected_input(
                    component_id,
                    ThermophysicalProperty.MOLECULAR_WEIGHT,
                    molecular_weight,
                    "g/mol",
                ),
            )
        )
    return IdealRaoultInputSet(
        input_set_id="c4-input-set:formula-17:v1",
        properties=tuple(reversed(properties)),
    )


def matrix_context(
    *,
    matrix: MatrixComposition | None = None,
    environment: ApplicationEnvironment | None = None,
) -> MatrixAwareModelRequest:
    return MatrixAwareModelRequest(
        purpose="C4 ideal equilibrium comparison baseline",
        formula_id="formula:17",
        formula_sha256=FORMULA_SHA256,
        matrix=matrix or exact_matrix(),
        environment=environment or sealed_environment(),
    )


def applicability_context(
    inputs: IdealRaoultInputSet,
    *,
    phase_behavior: str = "single_liquid_phase",
    available_properties: tuple[ThermophysicalProperty, ...] = (
        ThermophysicalProperty.VAPOR_PRESSURE,
        ThermophysicalProperty.MOLECULAR_WEIGHT,
    ),
    identity_ids: tuple[str, ...] | None = None,
) -> ApplicabilityContext:
    resolved_identity_ids = identity_ids or tuple(
        sorted({item.identity.content_sha256 for item in inputs.properties})
    )
    return ApplicabilityContext(
        identity_ids=resolved_identity_ids,
        chemical_classes=(),
        functional_groups=(),
        concentration=None,
        phase_behavior=phase_behavior,
        available_properties=available_properties,
        training_calibration_tags=("theoretical_baseline",),
    )


def request_for(
    adapter: IdealRaoultAdapter,
    inputs: IdealRaoultInputSet,
    *,
    matrix: MatrixComposition | None = None,
    environment: ApplicationEnvironment | None = None,
    input_references: tuple[ModelInputReference, ...] | None = None,
    phase_behavior: str = "single_liquid_phase",
    available_properties: tuple[ThermophysicalProperty, ...] = (
        ThermophysicalProperty.VAPOR_PRESSURE,
        ThermophysicalProperty.MOLECULAR_WEIGHT,
    ),
    identity_ids: tuple[str, ...] | None = None,
) -> VersionedModelRequest:
    return VersionedModelRequest(
        request_id="request:c4:formula-17:ideal-raoult",
        operation=ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE,
        requested_model=adapter.release.selector,
        context=matrix_context(matrix=matrix, environment=environment),
        applicability_context=applicability_context(
            inputs,
            phase_behavior=phase_behavior,
            available_properties=available_properties,
            identity_ids=identity_ids,
        ),
        input_references=(inputs.to_model_input_reference(),)
        if input_references is None
        else input_references,
    )


def executable_case(
    *,
    matrix: MatrixComposition | None = None,
    inputs: IdealRaoultInputSet | None = None,
    environment: ApplicationEnvironment | None = None,
) -> tuple[
    IdealRaoultInputSet,
    IdealRaoultAdapter,
    VersionedModelRequest,
    VersionedModelRouter,
]:
    resolved_inputs = inputs or input_set()
    adapter = IdealRaoultAdapter(
        input_set=resolved_inputs,
        code_commit=CODE_COMMIT,
        implementation_sha256=IMPLEMENTATION_SHA256,
    )
    request = request_for(
        adapter,
        resolved_inputs,
        matrix=matrix,
        environment=environment,
    )
    return resolved_inputs, adapter, request, VersionedModelRouter((adapter,))


@pytest.mark.parametrize(
    "mutator,match",
    [
        (
            lambda result: replace(result, status=SelectionStatus.ADVISORY),
            "selection status",
        ),
        (
            lambda result: replace(result, authority_state=AuthorityState.ADVISORY_ONLY),
            "authority",
        ),
        (lambda result: replace(result, source=None), "source"),
        (lambda result: replace(result, assertion_sha256=None), "assertion"),
        (lambda result: replace(result, request_sha256="d" * 64), "request hash"),
        (
            lambda result: replace(
                result,
                datum=PropertyDatum(
                    value_kind=PropertyValueKind.CATEGORICAL,
                    canonical_unit="Pa",
                    categorical_value="high",
                ),
            ),
            "numeric observation",
        ),
        (lambda result: replace(result, model=object()), "equation declarations"),
    ],
)
def test_selected_property_input_requires_authorized_numeric_observation(
    mutator,
    match: str,
) -> None:
    request = property_request(
        "component:a",
        ThermophysicalProperty.VAPOR_PRESSURE,
    )
    result = mutator(selected_result(request, 100.0, "Pa"))
    with pytest.raises(EquilibriumModelContractError, match=match):
        SelectedNumericPropertyInput.from_selection(
            component_id="component:a",
            request=request,
            selection=result,
        )


@pytest.mark.parametrize(
    "property_type,value,unit,match",
    [
        (ThermophysicalProperty.VAPOR_PRESSURE, 100.0, "kPa", "must use Pa"),
        (ThermophysicalProperty.VAPOR_PRESSURE, 0.0, "Pa", "positive"),
        (ThermophysicalProperty.MOLECULAR_WEIGHT, 50.0, "kg/mol", "must use g/mol"),
        (ThermophysicalProperty.MOLECULAR_WEIGHT, -1.0, "g/mol", "positive"),
        (ThermophysicalProperty.DENSITY, 1.0, "g/mL", "property type"),
    ],
)
def test_selected_property_input_enforces_c4_property_and_unit_contract(
    property_type: ThermophysicalProperty,
    value: float,
    unit: str,
    match: str,
) -> None:
    request = property_request("component:a", property_type)
    result = selected_result(request, value, unit)
    with pytest.raises(EquilibriumModelContractError, match=match):
        SelectedNumericPropertyInput.from_selection(
            component_id="component:a",
            request=request,
            selection=result,
        )


def test_input_set_is_canonical_hash_bound_and_round_trips() -> None:
    first = input_set()
    second = IdealRaoultInputSet(
        input_set_id=first.input_set_id,
        properties=tuple(reversed(first.properties)),
    )
    assert first == second
    assert first.content_sha256 == second.content_sha256
    assert IdealRaoultInputSet.from_mapping(first.to_mapping()) == first

    reference = first.to_model_input_reference()
    assert reference.role == C4_INPUT_ROLE
    assert reference.input_id == first.input_set_id
    assert reference.content_sha256 == first.content_sha256

    tampered = first.to_mapping()
    tampered["content_sha256"] = "f" * 64
    with pytest.raises(EquilibriumModelContractError, match="content_sha256"):
        IdealRaoultInputSet.from_mapping(tampered)


def test_input_set_requires_exactly_one_property_pair_per_component() -> None:
    properties = input_set().properties
    with pytest.raises(EquilibriumModelContractError, match="exactly one"):
        IdealRaoultInputSet(
            input_set_id="missing-molecular-weight",
            properties=tuple(
                item
                for item in properties
                if not (
                    item.component_id == "component:a"
                    and item.property_type is ThermophysicalProperty.MOLECULAR_WEIGHT
                )
            ),
        )
    with pytest.raises(EquilibriumModelContractError, match="duplicate"):
        IdealRaoultInputSet(
            input_set_id="duplicate-vapor-pressure",
            properties=properties + (properties[0],),
        )


def test_pure_component_analytic_raoult_benchmark() -> None:
    matrix = exact_matrix(
        values=(1.0,),
        component_ids=("component:a",),
    )
    inputs = input_set(
        component_ids=("component:a",),
        vapor_pressures_pa=(20_000.0,),
        molecular_weights=(46.0,),
    )
    _, adapter, request, router = executable_case(matrix=matrix, inputs=inputs)

    result = router.predict_equilibrium_headspace(request)
    assert result.status is ModelResultStatus.COMPUTED
    assert result.applicability.state is ApplicabilityState.IN_DOMAIN
    assert result.bound_model == adapter.release
    assert result.evidence_class is ModelEvidenceClass.THEORETICAL_BASELINE
    assert result.may_feed_oav_screening is False
    assert result.uncertainty.kind is UncertaintyKind.UNKNOWN
    assert "C5_UNCERTAINTY_PROPAGATION_REQUIRED" in result.warnings

    assert result.output is not None
    payload = result.output.payload.to_mapping()
    assert payload["schema"] == "c4-ideal-raoult-output-v1"
    assert payload["equation"] == "p_i = x_i * p_i_star"
    assert payload["activity_coefficient_model"] == "gamma_i = 1"
    assert payload["total_ideal_bubble_pressure_pa"] == 20_000.0
    assert payload["modeled_system_pressure_fraction"] == pytest.approx(
        20_000.0 / SYSTEM_PRESSURE_PA
    )
    assert payload["components"] == [
        {
            "activity_coefficient": 1.0,
            "component_id": "component:a",
            "identity_sha256": inputs.properties[0].identity.content_sha256,
            "liquid_mole_fraction": 1.0,
            "partial_pressure_pa": 20_000.0,
            "pure_vapor_pressure_pa": 20_000.0,
            "system_pressure_fraction": pytest.approx(20_000.0 / SYSTEM_PRESSURE_PA),
        }
    ]
    assert payload["closure_checks"]["liquid_mole_fraction_abs_error"] <= 1e-12
    assert payload["closure_checks"]["within_system_pressure"] is True


def test_binary_mass_fraction_analytic_raoult_benchmark_and_mass_closure() -> None:
    matrix = exact_matrix(
        basis=MatrixQuantityBasis.MASS_FRACTION,
        values=(0.5, 0.5),
    )
    inputs = input_set(
        vapor_pressures_pa=(100.0, 30.0),
        molecular_weights=(50.0, 100.0),
    )
    _, _, request, router = executable_case(matrix=matrix, inputs=inputs)

    result = router.predict_equilibrium_headspace(request)
    assert result.output is not None
    payload = result.output.payload.to_mapping()
    by_id = {item["component_id"]: item for item in payload["components"]}
    assert by_id["component:a"]["liquid_mole_fraction"] == pytest.approx(2.0 / 3.0)
    assert by_id["component:b"]["liquid_mole_fraction"] == pytest.approx(1.0 / 3.0)
    assert by_id["component:a"]["partial_pressure_pa"] == pytest.approx(200.0 / 3.0)
    assert by_id["component:b"]["partial_pressure_pa"] == pytest.approx(10.0)
    assert payload["total_ideal_bubble_pressure_pa"] == pytest.approx(230.0 / 3.0)
    checks = payload["closure_checks"]
    assert checks["input_basis_abs_error"] <= 1e-12
    assert checks["mass_round_trip_max_abs_error"] <= 1e-12
    assert checks["liquid_mole_fraction_abs_error"] <= 1e-12


@pytest.mark.parametrize(
    "basis,values,unit,total_mass,expected_x",
    [
        (
            MatrixQuantityBasis.MOLE_FRACTION,
            (0.25, 0.75),
            "1",
            quantity(1.0, "g"),
            (0.25, 0.75),
        ),
        (
            MatrixQuantityBasis.MASS_FRACTION,
            (0.5, 0.5),
            "1",
            quantity(1.0, "g"),
            (2.0 / 3.0, 1.0 / 3.0),
        ),
        (
            MatrixQuantityBasis.MASS,
            (1.0, 1.0),
            "g",
            quantity(2.0, "g"),
            (2.0 / 3.0, 1.0 / 3.0),
        ),
        (
            MatrixQuantityBasis.AMOUNT,
            (1.0, 3.0),
            "mol",
            quantity(250.0, "g"),
            (0.25, 0.75),
        ),
    ],
)
def test_supported_composition_bases_are_explicit_and_deterministic(
    basis: MatrixQuantityBasis,
    values: tuple[float, float],
    unit: str,
    total_mass: DeclaredQuantity,
    expected_x: tuple[float, float],
) -> None:
    matrix = exact_matrix(
        basis=basis,
        values=values,
        unit=unit,
        total_mass=total_mass,
    )
    _, _, request, router = executable_case(matrix=matrix)
    result = router.predict_equilibrium_headspace(request)
    assert result.status is ModelResultStatus.COMPUTED
    assert result.output is not None
    mole_fractions = tuple(
        item["liquid_mole_fraction"] for item in result.output.payload.to_mapping()["components"]
    )
    assert mole_fractions == pytest.approx(expected_x)


def test_router_abstains_on_tampered_or_extra_input_reference() -> None:
    inputs, adapter, _, router = executable_case()
    bad_reference = ModelInputReference(
        role=C4_INPUT_ROLE,
        input_id=inputs.input_set_id,
        content_sha256="d" * 64,
    )
    extra_reference = ModelInputReference(
        role="unrelated",
        input_id="unrelated:v1",
        content_sha256="e" * 64,
    )
    for references in ((bad_reference,), (inputs.to_model_input_reference(), extra_reference)):
        request = request_for(adapter, inputs, input_references=references)
        result = router.predict_equilibrium_headspace(request)
        assert result.status is ModelResultStatus.ABSTAINED
        assert result.output is None
        assert result.applicability.state is ApplicabilityState.INSUFFICIENT_INPUT
        assert "input_reference:c4_equilibrium_input_set" in result.missing_inputs


@pytest.mark.parametrize(
    "case,expected_state",
    [
        ("volume_fraction", ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN),
        ("mixed_basis", ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN),
        ("pressure_unit", ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN),
        ("temperature_unit", ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN),
        ("stage", ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN),
        ("environment", ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN),
        ("environment_temperature", ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN),
        ("phase", ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN),
        ("partial", ApplicabilityState.INSUFFICIENT_INPUT),
        ("property_temperature", ApplicabilityState.INSUFFICIENT_INPUT),
        ("available_properties", ApplicabilityState.INSUFFICIENT_INPUT),
        ("identity_binding", ApplicabilityState.INSUFFICIENT_INPUT),
        ("component_binding", ApplicabilityState.INSUFFICIENT_INPUT),
        ("mass_total", ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN),
    ],
)
def test_applicability_abstains_for_unsupported_or_insufficient_context(
    case: str,
    expected_state: ApplicabilityState,
) -> None:
    inputs = input_set()
    matrix = exact_matrix()
    environment = sealed_environment()
    phase_behavior = "single_liquid_phase"
    available_properties = (
        ThermophysicalProperty.VAPOR_PRESSURE,
        ThermophysicalProperty.MOLECULAR_WEIGHT,
    )
    identity_ids = None

    if case == "volume_fraction":
        matrix = exact_matrix(basis=MatrixQuantityBasis.VOLUME_FRACTION)
    elif case == "mixed_basis":
        base = exact_matrix()
        matrix = replace(
            base,
            components=(
                base.components[0],
                replace(
                    base.components[1],
                    basis=MatrixQuantityBasis.MASS_FRACTION,
                ),
            ),
        )
    elif case == "pressure_unit":
        matrix = exact_matrix(pressure_unit="kPa")
    elif case == "temperature_unit":
        matrix = exact_matrix(temperature_unit="degC")
    elif case == "stage":
        matrix = exact_matrix(stage=MatrixStage.SAMPLED_HEADSPACE)
    elif case == "environment":
        environment = sealed_environment(kind=ApplicationEnvironmentKind.BLOTTER)
    elif case == "environment_temperature":
        environment = sealed_environment(temperature_k=TEMPERATURE_K + 1.0)
    elif case == "phase":
        phase_behavior = "two_liquid_phases"
    elif case == "partial":
        base = exact_matrix()
        matrix = replace(
            base,
            total_volume=None,
            completeness=CompositionCompleteness.PARTIAL,
            missing_fields=(MatrixMissingField.TOTAL_VOLUME,),
        )
    elif case == "property_temperature":
        inputs = input_set(vapor_pressure_temperature_k=TEMPERATURE_K + 1.0)
    elif case == "available_properties":
        available_properties = (ThermophysicalProperty.VAPOR_PRESSURE,)
    elif case == "identity_binding":
        identity_ids = ("wrong-identity",)
    elif case == "component_binding":
        matrix = exact_matrix(component_ids=("component:a", "component:other"))
    elif case == "mass_total":
        matrix = exact_matrix(
            basis=MatrixQuantityBasis.MASS,
            values=(1.0, 1.0),
            unit="g",
            total_mass=quantity(3.0, "g"),
        )

    adapter = IdealRaoultAdapter(
        input_set=inputs,
        code_commit=CODE_COMMIT,
        implementation_sha256=IMPLEMENTATION_SHA256,
    )
    request = request_for(
        adapter,
        inputs,
        matrix=matrix,
        environment=environment,
        phase_behavior=phase_behavior,
        available_properties=available_properties,
        identity_ids=identity_ids,
    )
    result = VersionedModelRouter((adapter,)).predict_equilibrium_headspace(request)
    assert result.status is ModelResultStatus.ABSTAINED
    assert result.output is None
    assert result.applicability.state is expected_state


def test_bubble_pressure_above_system_pressure_abstains_before_compute() -> None:
    matrix = exact_matrix(pressure_pa=100.0)
    inputs = input_set(vapor_pressures_pa=(200.0, 200.0))
    _, _, request, router = executable_case(matrix=matrix, inputs=inputs)
    result = router.predict_equilibrium_headspace(request)
    assert result.status is ModelResultStatus.ABSTAINED
    assert result.output is None
    assert result.applicability.state is ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN
    assert any("bubble pressure" in reason for reason in result.applicability.reasons)


def test_available_release_authority_is_theoretical_and_never_oav_authority() -> None:
    _, adapter, _, _ = executable_case()
    release = adapter.release
    assert release.selector.family is ModelFamily.IDEAL_RAOULT_BASELINE
    assert release.selector.model_version == "c4-ideal-raoult-v1"
    assert release.availability is ModelAvailability.AVAILABLE
    assert release.evidence_class is ModelEvidenceClass.THEORETICAL_BASELINE
    assert release.may_feed_oav_screening is False
    assert release.coefficient_set_sha256 is None
    assert release.decomposition_sha256 is None
    assert release.training_data_sha256 is None
    assert release.supported_operations == (ModelOperation.PREDICT_EQUILIBRIUM_HEADSPACE,)
    assert "ideal-solution comparison baseline" in release.permitted_claim_wording
    assert "measured headspace" in release.forbidden_claim_wording


def test_henry_empirical_unifac_and_cosmo_rs_are_explicitly_unavailable() -> None:
    inputs = input_set()
    ideal = IdealRaoultAdapter(
        input_set=inputs,
        code_commit=CODE_COMMIT,
        implementation_sha256=IMPLEMENTATION_SHA256,
    )
    withheld = withheld_equilibrium_adapters(
        code_commit=CODE_COMMIT,
        implementation_sha256=IMPLEMENTATION_SHA256,
    )
    assert {adapter.release.selector.family for adapter in withheld} == {
        ModelFamily.HENRY_LAW_DILUTE_BASELINE,
        ModelFamily.EMPIRICAL_MATRIX_CORRECTION,
        ModelFamily.UNIFAC_OR_MODIFIED_UNIFAC,
        ModelFamily.IMPORTED_COSMO_RS,
    }

    router = VersionedModelRouter((ideal, *withheld))
    for adapter in withheld:
        release = adapter.release
        assert release.availability is ModelAvailability.UNAVAILABLE
        assert release.evidence_class is ModelEvidenceClass.UNVALIDATED
        assert release.may_feed_oav_screening is False
        assert release.unavailable_reason
        request = replace(
            request_for(ideal, inputs),
            requested_model=release.selector,
        )
        result = router.predict_equilibrium_headspace(request)
        assert result.status is ModelResultStatus.ABSTAINED
        assert result.applicability.state is ApplicabilityState.MODEL_NOT_VALIDATED
        assert result.output is None


def test_computed_result_is_c3_round_trip_stable_and_hash_bound() -> None:
    _, _, request, router = executable_case()
    result = router.predict_equilibrium_headspace(request)
    restored = VersionedModelResult.from_mapping(result.to_mapping())
    assert restored == result
    assert restored.content_sha256 == result.content_sha256


def test_c4_module_has_no_legacy_equation_runtime_or_persistence_dependency() -> None:
    source = Path(equilibrium_module.__file__).read_text(encoding="utf-8")
    forbidden = (
        "engine.thermo",
        "thermo.headspace",
        "thermo.activity",
        "sqlalchemy",
        "sqlite3",
        "backend.",
    )
    assert not any(marker in source for marker in forbidden)


def test_c4_contracts_are_explicitly_exported_from_engine_physics() -> None:
    import engine.physics as physics

    expected = {
        "C4_INPUT_ROLE",
        "EquilibriumModelContractError",
        "IdealRaoultAdapter",
        "IdealRaoultInputSet",
        "SelectedNumericPropertyInput",
        "UnavailableEquilibriumAdapter",
        "withheld_equilibrium_adapters",
    }
    assert expected.issubset(set(physics.__all__))
    for name in expected:
        assert getattr(physics, name) is not None
