from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from pathlib import Path

import pytest

import engine.physics.dynamic_release as dynamic_release_module
from engine.physics.dynamic_release import (
    C6_INPUT_ROLE,
    C6_MODEL_VERSION,
    PERMITTED_C6_OUTPUT_LABELS,
    ComponentCompartmentState,
    DynamicComponentParameters,
    DynamicParameterAuthority,
    DynamicReleaseAdapter,
    DynamicReleaseContractError,
    DynamicReleaseInputSet,
    InitialCompartmentMass,
    PhysicalProcessLayer,
    PhysicalTrajectoryLabel,
    RateScenario,
    SubstrateModelParameters,
    simulate_dynamic_release,
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
from engine.physics.properties import UncertaintyDescriptor, UncertaintyKind

CODE_COMMIT = "a" * 40
IMPLEMENTATION_SHA256 = "b" * 64
FORMULA_SHA256 = "c" * 64
SOURCE_SHA256 = "d" * 64
TEMPERATURE_K = 298.15
MASS_TOLERANCE_MG = 1e-9


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def unknown(reason: str = "not quantified") -> UncertaintyDescriptor:
    return UncertaintyDescriptor.unknown(reason)


def quantity(value: float, unit: str) -> DeclaredQuantity:
    return DeclaredQuantity(value=value, unit=unit)


def matrix(
    *,
    component_order: tuple[str, ...] = ("component:ethanol", "component:active"),
    basis: MatrixQuantityBasis = MatrixQuantityBasis.MASS,
    unit: str = "mg",
    stage: MatrixStage = MatrixStage.APPLICATION_FILM,
) -> MatrixComposition:
    component_values = (
        {"component:ethanol": 0.8, "component:active": 0.2}
        if basis is MatrixQuantityBasis.MASS_FRACTION
        else {"component:ethanol": 8.0, "component:active": 2.0}
    )
    definitions = {
        "component:ethanol": (
            "Ethanol",
            MatrixComponentRole.ETHANOL,
            component_values["component:ethanol"],
        ),
        "component:active": (
            "Active",
            MatrixComponentRole.ACTIVE_FRAGRANCE,
            component_values["component:active"],
        ),
    }
    components = tuple(
        MatrixComponent(
            component_id=component_id,
            name=definitions[component_id][0],
            role=definitions[component_id][1],
            basis=basis,
            quantity=quantity(definitions[component_id][2], unit),
            source_reference=f"formula-source:{component_id}",
            uncertainty=unknown(),
        )
        for component_id in component_order
    )
    total_mass = 10.0
    total_mass_unit = unit if basis is MatrixQuantityBasis.MASS else "mg"
    return MatrixComposition(
        matrix_id="matrix:c6:formula-17",
        matrix_version="1",
        stage=stage,
        components=components,
        temperature=quantity(TEMPERATURE_K, "K"),
        pressure=quantity(101_325.0, "Pa"),
        relative_humidity=quantity(0.50, "1"),
        gas_comparison=True,
        total_mass=quantity(total_mass, total_mass_unit),
        total_volume=quantity(0.012, "mL"),
        uncertainty=unknown("matrix uncertainty is explicit"),
        phase_assumptions=("single_liquid_phase",),
        completeness=CompositionCompleteness.EXACT,
        missing_fields=(),
    )


def environment(
    kind: ApplicationEnvironmentKind = ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE,
    *,
    film_thickness_m: float = 1e-4,
    area_m2: float = 0.01,
    airflow_m_s: float = 0.2,
    relative_humidity: float = 0.50,
    temperature_unit: str = "K",
    area_unit: str = "m2",
    film_unit: str = "m",
) -> ApplicationEnvironment:
    if kind is ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL:
        return ApplicationEnvironment(
            environment_id="environment:c6:sealed",
            environment_version="1",
            kind=kind,
            dose=quantity(10.0, "mg"),
            area=None,
            film_thickness=None,
            geometry="20 mL sealed vial",
            substrate="borosilicate glass lot V-1",
            temperature=quantity(TEMPERATURE_K, temperature_unit),
            relative_humidity=quantity(relative_humidity, "1"),
            airflow=quantity(0.0, "m/s"),
            equilibration_or_drying_time=quantity(0.0, "s"),
            sampling_time=quantity(10.0, "s"),
            sampling_method="modeled sealed headspace",
            vessel_volume=quantity(20e-6, "m3"),
            headspace_volume=quantity(10e-6, "m3"),
            uncertainty=unknown("sealed environment uncertainty"),
            missing_fields=(),
            not_applicable_fields=(
                EnvironmentField.AREA,
                EnvironmentField.FILM_THICKNESS,
            ),
        )

    substrate = (
        None
        if kind is ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE
        else f"declared substrate for {kind.value}"
    )
    not_applicable = [
        EnvironmentField.VESSEL_VOLUME,
        EnvironmentField.HEADSPACE_VOLUME,
    ]
    if substrate is None:
        not_applicable.append(EnvironmentField.SUBSTRATE)
    return ApplicationEnvironment(
        environment_id=f"environment:c6:{kind.value.lower()}",
        environment_version="1",
        kind=kind,
        dose=quantity(10.0, "mg"),
        area=quantity(area_m2, area_unit),
        film_thickness=quantity(film_thickness_m, film_unit),
        geometry="constant-area finite film",
        substrate=substrate,
        temperature=quantity(TEMPERATURE_K, temperature_unit),
        relative_humidity=quantity(relative_humidity, "1"),
        airflow=quantity(airflow_m_s, "m/s"),
        equilibration_or_drying_time=quantity(0.0, "s"),
        sampling_time=quantity(10.0, "s"),
        sampling_method="modeled physical trajectory",
        vessel_volume=None,
        headspace_volume=None,
        uncertainty=unknown("finite-film environment uncertainty"),
        missing_fields=(),
        not_applicable_fields=tuple(not_applicable),
    )


def component_parameters(
    component_id: str,
    kind: ApplicationEnvironmentKind,
    *,
    uncertainty: float = 0.20,
    equilibrium_release_factor: float | None = None,
    matrix_feedback_exponent: float | None = None,
) -> DynamicComponentParameters:
    active = component_id == "component:active"
    release_factor = (
        equilibrium_release_factor
        if equilibrium_release_factor is not None
        else (0.25 if active else 0.90)
    )
    feedback = (
        matrix_feedback_exponent
        if matrix_feedback_exponent is not None
        else (1.0 if active else 0.0)
    )
    sealed = kind is ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL
    open_surface = kind is ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE
    return DynamicComponentParameters(
        component_id=component_id,
        equilibrium_release_factor=release_factor,
        activity_coefficient=1.0 if active else 1.2,
        sealed_transfer_rate_s_minus_1=(0.08 if active else 0.20) if sealed else None,
        diffusion_coefficient_m2_s=None if sealed else (1e-12 if active else 4e-12),
        mass_transfer_coefficient_m_s=None if sealed else (1e-5 if active else 2e-5),
        sorption_rate_s_minus_1=(0.0 if sealed or open_surface else (0.04 if active else 0.01)),
        desorption_rate_s_minus_1=(0.0 if sealed or open_surface else (0.01 if active else 0.005)),
        sink_rate_s_minus_1=0.0 if sealed else (0.02 if active else 0.05),
        matrix_feedback_exponent=feedback,
        relative_parameter_uncertainty=uncertainty,
        parameter_source_id=f"declared-simulation-parameter:{kind.value}:{component_id}",
        parameter_source_sha256=digest(f"{kind.value}:{component_id}:v1"),
    )


def substrate_model(
    kind: ApplicationEnvironmentKind = ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE,
    *,
    components: tuple[DynamicComponentParameters, ...] | None = None,
) -> SubstrateModelParameters:
    resolved_components = components or tuple(
        component_parameters(component_id, kind)
        for component_id in ("component:ethanol", "component:active")
    )
    return SubstrateModelParameters(
        model_id=f"c6-substrate:{kind.value.lower()}",
        model_version="1",
        substrate_kind=kind,
        authority=DynamicParameterAuthority.SIMULATION_ONLY_UNCALIBRATED,
        calibration_receipt_sha256=None,
        cross_substrate_transfer_allowed=False,
        reference_temperature_k=TEMPERATURE_K,
        reference_airflow_m_s=(
            0.0 if kind is ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL else 0.2
        ),
        reference_relative_humidity=0.50,
        temperature_coefficient_per_k=0.01,
        airflow_sensitivity_s_m=0.50,
        humidity_sensitivity=0.20,
        components=resolved_components,
    )


def input_set(
    *,
    matrix_value: MatrixComposition | None = None,
    environment_value: ApplicationEnvironment | None = None,
    kind: ApplicationEnvironmentKind = ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE,
    model: SubstrateModelParameters | None = None,
    duration_s: float = 10.0,
    time_step_s: float = 1.0,
    initial_masses: tuple[InitialCompartmentMass, ...] | None = None,
) -> DynamicReleaseInputSet:
    resolved_matrix = matrix_value or matrix(
        stage=(
            MatrixStage.FINISHED_PERFUME
            if kind is ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL
            else MatrixStage.APPLICATION_FILM
        )
    )
    resolved_environment = environment_value or environment(kind)
    resolved_initial = initial_masses or (
        InitialCompartmentMass(
            component_id="component:active",
            gas_mass_mg=0.0,
            sorbed_mass_mg=0.0,
        ),
        InitialCompartmentMass(
            component_id="component:ethanol",
            gas_mass_mg=0.0,
            sorbed_mass_mg=0.0,
        ),
    )
    return DynamicReleaseInputSet(
        input_set_id=f"c6-input:formula-17:{kind.value.lower()}",
        matrix_sha256=resolved_matrix.content_sha256,
        environment_sha256=resolved_environment.content_sha256,
        substrate_model=model or substrate_model(kind),
        initial_masses=resolved_initial,
        duration_s=duration_s,
        time_step_s=time_step_s,
        mass_tolerance_mg=MASS_TOLERANCE_MG,
    )


def applicability_context() -> ApplicabilityContext:
    return ApplicabilityContext(
        identity_ids=("component:active", "component:ethanol"),
        chemical_classes=(),
        functional_groups=(),
        concentration=None,
        phase_behavior="single_liquid_phase",
        available_properties=(),
        training_calibration_tags=("simulation_only_uncalibrated",),
    )


def request_for(
    adapter: DynamicReleaseAdapter,
    inputs: DynamicReleaseInputSet,
    *,
    matrix_value: MatrixComposition,
    environment_value: ApplicationEnvironment,
    operation: ModelOperation = ModelOperation.PREDICT_DYNAMIC_RELEASE,
    input_references: tuple[ModelInputReference, ...] | None = None,
) -> VersionedModelRequest:
    return VersionedModelRequest(
        request_id=f"request:c6:{environment_value.kind.value.lower()}",
        operation=operation,
        requested_model=adapter.release.selector,
        context=MatrixAwareModelRequest(
            purpose="C6 simulation-only physical trajectory",
            formula_id="formula:17",
            formula_sha256=FORMULA_SHA256,
            matrix=matrix_value,
            environment=environment_value,
        ),
        applicability_context=applicability_context(),
        input_references=(inputs.to_model_input_reference(),)
        if input_references is None
        else input_references,
    )


def executable_case(
    kind: ApplicationEnvironmentKind = ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE,
    *,
    duration_s: float = 10.0,
    time_step_s: float = 1.0,
    model: SubstrateModelParameters | None = None,
) -> tuple[
    MatrixComposition,
    ApplicationEnvironment,
    DynamicReleaseInputSet,
    DynamicReleaseAdapter,
    VersionedModelRequest,
    VersionedModelRouter,
]:
    matrix_value = matrix(
        stage=(
            MatrixStage.FINISHED_PERFUME
            if kind is ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL
            else MatrixStage.APPLICATION_FILM
        )
    )
    environment_value = environment(kind)
    inputs = input_set(
        matrix_value=matrix_value,
        environment_value=environment_value,
        kind=kind,
        model=model,
        duration_s=duration_s,
        time_step_s=time_step_s,
    )
    adapter = DynamicReleaseAdapter(
        input_set=inputs,
        code_commit=CODE_COMMIT,
        implementation_sha256=IMPLEMENTATION_SHA256,
    )
    request = request_for(
        adapter,
        inputs,
        matrix_value=matrix_value,
        environment_value=environment_value,
    )
    return (
        matrix_value,
        environment_value,
        inputs,
        adapter,
        request,
        VersionedModelRouter((adapter,)),
    )


def test_process_layers_and_output_labels_are_closed_and_separate() -> None:
    assert [item.value for item in PhysicalProcessLayer] == [
        "EQUILIBRIUM_PARTITION",
        "MASS_TRANSFER_AND_EVAPORATION",
        "SUBSTRATE_SORPTION",
        "PHYSICAL_HEADSPACE_TRAJECTORY",
        "OLFACTORY_ADAPTATION",
        "PERCEIVED_INTENSITY",
        "TEMPORAL_ATTRIBUTE_PROFILE",
    ]
    assert tuple(item.value for item in PhysicalTrajectoryLabel) == (
        "PREDICTED_HEADSPACE_TRAJECTORY",
        "PREDICTED_RELEASE_TRAJECTORY",
        "ESTIMATED_PHYSICAL_PERSISTENCE",
    )
    assert PERMITTED_C6_OUTPUT_LABELS == tuple(PhysicalTrajectoryLabel)


def test_component_parameters_are_hash_bound_and_round_trip() -> None:
    value = component_parameters(
        "component:active",
        ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE,
    )
    restored = DynamicComponentParameters.from_mapping(value.to_mapping())
    assert restored == value
    assert restored.content_sha256 == value.content_sha256
    tampered = value.to_mapping()
    tampered["content_sha256"] = "f" * 64
    with pytest.raises(DynamicReleaseContractError, match="content_sha256"):
        DynamicComponentParameters.from_mapping(tampered)


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("equilibrium_release_factor", -0.1, "between zero and one"),
        ("activity_coefficient", 0.0, "positive"),
        ("diffusion_coefficient_m2_s", -1.0, "non-negative"),
        ("sink_rate_s_minus_1", -1.0, "non-negative"),
        ("matrix_feedback_exponent", -1.0, "non-negative"),
        ("relative_parameter_uncertainty", 1.0, "less than one"),
        ("parameter_source_sha256", "not-a-hash", "SHA-256"),
    ],
)
def test_component_parameters_fail_closed(field: str, value: object, match: str) -> None:
    baseline = component_parameters(
        "component:active",
        ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE,
    )
    payload = baseline.to_mapping()
    payload[field] = value
    with pytest.raises(DynamicReleaseContractError, match=match):
        DynamicComponentParameters.from_mapping(payload)


def test_substrate_model_enforces_geometry_specific_parameters() -> None:
    sealed_component = component_parameters(
        "component:active",
        ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL,
    )
    with pytest.raises(DynamicReleaseContractError, match="finite-film"):
        substrate_model(
            ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE,
            components=(sealed_component,),
        )

    film_component = component_parameters(
        "component:active",
        ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE,
    )
    with pytest.raises(DynamicReleaseContractError, match="sealed"):
        substrate_model(
            ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL,
            components=(film_component,),
        )


def test_substrate_model_cannot_claim_calibration_or_cross_transfer() -> None:
    baseline = substrate_model(ApplicationEnvironmentKind.BLOTTER)
    assert baseline.authority is DynamicParameterAuthority.SIMULATION_ONLY_UNCALIBRATED
    assert baseline.calibration_receipt_sha256 is None
    assert baseline.cross_substrate_transfer_allowed is False
    with pytest.raises(DynamicReleaseContractError, match="calibration receipt"):
        replace(baseline, calibration_receipt_sha256=SOURCE_SHA256)
    with pytest.raises(DynamicReleaseContractError, match="cross-substrate"):
        replace(baseline, cross_substrate_transfer_allowed=True)


def test_input_set_is_canonical_hash_bound_and_round_trips() -> None:
    matrix_value = matrix()
    environment_value = environment()
    first = input_set(
        matrix_value=matrix_value,
        environment_value=environment_value,
    )
    second = replace(
        first,
        substrate_model=replace(
            first.substrate_model,
            components=tuple(reversed(first.substrate_model.components)),
        ),
        initial_masses=tuple(reversed(first.initial_masses)),
    )
    assert first == second
    assert DynamicReleaseInputSet.from_mapping(first.to_mapping()) == first
    reference = first.to_model_input_reference()
    assert reference.role == C6_INPUT_ROLE
    assert reference.input_id == first.input_set_id
    assert reference.content_sha256 == first.content_sha256

    tampered = first.to_mapping()
    tampered["duration_s"] = 11.0
    with pytest.raises(DynamicReleaseContractError, match="content_sha256"):
        DynamicReleaseInputSet.from_mapping(tampered)


@pytest.mark.parametrize(
    "duration,time_step,match",
    [
        (0.0, 1.0, "positive"),
        (1.0, 0.0, "positive"),
        (10.0, 3.0, "integer number"),
        (10_001.0, 1.0, "10,000"),
    ],
)
def test_time_grid_fails_closed(duration: float, time_step: float, match: str) -> None:
    baseline = input_set()
    with pytest.raises(DynamicReleaseContractError, match=match):
        replace(baseline, duration_s=duration, time_step_s=time_step)


def test_initial_compartment_masses_are_explicit_and_nonnegative() -> None:
    with pytest.raises(DynamicReleaseContractError, match="non-negative"):
        InitialCompartmentMass(
            component_id="component:active",
            gas_mass_mg=-1.0,
            sorbed_mass_mg=0.0,
        )
    baseline = input_set()
    with pytest.raises(DynamicReleaseContractError, match="duplicate"):
        replace(baseline, initial_masses=(baseline.initial_masses[0],) * 2)


def test_release_is_unvalidated_simulation_only_and_never_oav_authority() -> None:
    *_, adapter, _, _ = executable_case()
    release = adapter.release
    assert release.selector.family is ModelFamily.DYNAMIC_SEMI_EMPIRICAL_MODEL
    assert release.selector.model_version.startswith(f"{C6_MODEL_VERSION}:open_liquid_surface:")
    assert adapter.input_set.substrate_model.content_sha256[:16] in (release.selector.model_version)
    assert release.availability is ModelAvailability.AVAILABLE
    assert release.evidence_class is ModelEvidenceClass.UNVALIDATED
    assert release.may_feed_oav_screening is False
    assert release.training_data_sha256 is None
    assert release.supported_operations == (
        ModelOperation.PREDICT_DYNAMIC_RELEASE,
        ModelOperation.PROPAGATE_UNCERTAINTY,
    )
    assert "simulation-only physical trajectory" in release.permitted_claim_wording
    for forbidden in (
        "exact longevity",
        "sillage",
        "projection distance",
        "perceived intensity",
        "measured headspace",
        "calibrated release",
    ):
        assert forbidden in release.forbidden_claim_wording


def test_sealed_analytic_transfer_conserves_mass_and_reports_concentration() -> None:
    matrix_value, environment_value, inputs, _, _, _ = executable_case(
        ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL,
        duration_s=1.0,
        time_step_s=1.0,
    )
    simulation = simulate_dynamic_release(matrix_value, environment_value, inputs)
    nominal = simulation.scenario(RateScenario.NOMINAL)
    assert len(nominal.frames) == 2
    final = nominal.frames[-1]
    by_id = {item.component_id: item for item in final.components}
    ethanol_rate = 0.20 * 0.90 * 1.2
    expected_ethanol_gas = 8.0 * (1.0 - math.exp(-ethanol_rate))
    assert by_id["component:ethanol"].gas_mass_mg == pytest.approx(expected_ethanol_gas)
    assert final.total_sink_mass_mg == 0.0
    assert final.gas_concentration_mg_m3 == pytest.approx(final.total_gas_mass_mg / 10e-6)
    assert final.max_abs_mass_error_mg <= MASS_TOLERANCE_MG


@pytest.mark.parametrize("scenario", tuple(RateScenario))
def test_every_frame_is_nonnegative_and_mass_conservative(scenario: RateScenario) -> None:
    matrix_value, environment_value, inputs, _, _, _ = executable_case(
        ApplicationEnvironmentKind.BLOTTER,
        duration_s=60.0,
        time_step_s=1.0,
    )
    simulation = simulate_dynamic_release(matrix_value, environment_value, inputs)
    trajectory = simulation.scenario(scenario)
    for frame in trajectory.frames:
        assert frame.max_abs_mass_error_mg <= MASS_TOLERANCE_MG
        assert 0.0 <= frame.matrix_solvent_fraction <= 1.0
        assert 0.0 <= frame.physical_persistence_fraction <= 1.0
        for component_state in frame.components:
            assert component_state.condensed_mass_mg >= 0.0
            assert component_state.gas_mass_mg >= 0.0
            assert component_state.sorbed_mass_mg >= 0.0
            assert component_state.sink_mass_mg >= 0.0
            assert component_state.mass_balance_abs_error_mg <= MASS_TOLERANCE_MG


def test_per_step_closure_guard_rejects_sub_output_tolerance_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matrix_value, environment_value, inputs, _, _, _ = executable_case(
        ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE,
        duration_s=1.0,
        time_step_s=1.0,
    )
    original_clean_mass = dynamic_release_module._clean_mass
    leak_applied = False

    def leaking_clean_mass(value: float, field_name: str) -> float:
        nonlocal leak_applied
        cleaned = original_clean_mass(value, field_name)
        if field_name == "condensed mass" and not leak_applied and cleaned > 1e-7:
            leak_applied = True
            return cleaned - 1e-7
        return cleaned

    monkeypatch.setattr(dynamic_release_module, "_clean_mass", leaking_clean_mass)

    with pytest.raises(DynamicReleaseContractError, match="failed after transition"):
        simulate_dynamic_release(matrix_value, environment_value, inputs)


def test_bounded_hazard_prevents_negative_mass_under_extreme_rates() -> None:
    kind = ApplicationEnvironmentKind.FABRIC
    extreme = tuple(
        replace(
            component_parameters(component_id, kind),
            diffusion_coefficient_m2_s=1e6,
            mass_transfer_coefficient_m_s=1e6,
            sorption_rate_s_minus_1=1e6,
            desorption_rate_s_minus_1=1e6,
            sink_rate_s_minus_1=1e6,
        )
        for component_id in ("component:ethanol", "component:active")
    )
    model = substrate_model(kind, components=extreme)
    matrix_value, environment_value, inputs, _, _, _ = executable_case(
        kind,
        duration_s=10.0,
        time_step_s=10.0,
        model=model,
    )
    simulation = simulate_dynamic_release(matrix_value, environment_value, inputs)
    for trajectory in simulation.scenarios:
        for frame in trajectory.frames:
            assert frame.max_abs_mass_error_mg <= MASS_TOLERANCE_MG
            assert all(
                value >= 0.0
                for state in frame.components
                for value in (
                    state.condensed_mass_mg,
                    state.gas_mass_mg,
                    state.sorbed_mass_mg,
                    state.sink_mass_mg,
                )
            )


def test_explicit_sink_and_substrate_compartments_are_accounted() -> None:
    matrix_value, environment_value, inputs, _, _, _ = executable_case(
        ApplicationEnvironmentKind.BLOTTER,
    )
    simulation = simulate_dynamic_release(matrix_value, environment_value, inputs)
    final = simulation.scenario(RateScenario.NOMINAL).frames[-1]
    assert final.total_sink_mass_mg > 0.0
    assert final.total_sorbed_mass_mg > 0.0
    assert (
        final.total_condensed_mass_mg
        + final.total_gas_mass_mg
        + final.total_sorbed_mass_mg
        + final.total_sink_mass_mg
        == pytest.approx(10.0)
    )


def test_solvent_loss_changes_film_matrix_and_later_release_rate() -> None:
    matrix_value, environment_value, inputs, _, _, _ = executable_case(
        ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE,
        duration_s=120.0,
        time_step_s=2.0,
    )
    simulation = simulate_dynamic_release(matrix_value, environment_value, inputs)
    frames = simulation.scenario(RateScenario.NOMINAL).frames
    assert frames[-1].film_thickness_m is not None
    assert frames[0].film_thickness_m is not None
    assert frames[-1].film_thickness_m < frames[0].film_thickness_m
    assert frames[-1].matrix_solvent_fraction < frames[0].matrix_solvent_fraction
    first_active = next(
        item for item in frames[0].components if item.component_id == "component:active"
    )
    last_active = next(
        item for item in frames[-1].components if item.component_id == "component:active"
    )
    assert (
        last_active.effective_condensed_to_gas_rate_s_minus_1
        != first_active.effective_condensed_to_gas_rate_s_minus_1
    )


def test_uncertainty_propagates_as_nonstatistical_sensitivity_envelope() -> None:
    matrix_value, environment_value, inputs, _, _, _ = executable_case(
        ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE,
    )
    simulation = simulate_dynamic_release(matrix_value, environment_value, inputs)
    assert {item.scenario for item in simulation.scenarios} == set(RateScenario)
    finals = {item.scenario: item.frames[-1].total_sink_mass_mg for item in simulation.scenarios}
    assert len(set(finals.values())) == 3
    assert len(simulation.sensitivity_envelope) == len(simulation.scenarios[0].frames)
    for envelope in simulation.sensitivity_envelope:
        assert envelope.headspace_mass_min_mg <= envelope.headspace_mass_max_mg
        assert envelope.released_sink_min_mg <= envelope.released_sink_max_mg
        assert envelope.persistence_fraction_min <= envelope.persistence_fraction_max
    assert simulation.uncertainty_interpretation == (
        "DETERMINISTIC_PARAMETER_SENSITIVITY_NOT_STATISTICAL_INTERVAL"
    )


def test_simulation_is_reproducible_and_canonical_under_input_order() -> None:
    matrix_value = matrix()
    environment_value = environment(ApplicationEnvironmentKind.BLOTTER)
    first = input_set(
        matrix_value=matrix_value,
        environment_value=environment_value,
        kind=ApplicationEnvironmentKind.BLOTTER,
    )
    second = replace(
        first,
        substrate_model=replace(
            first.substrate_model,
            components=tuple(reversed(first.substrate_model.components)),
        ),
        initial_masses=tuple(reversed(first.initial_masses)),
    )
    first_result = simulate_dynamic_release(matrix_value, environment_value, first)
    second_result = simulate_dynamic_release(matrix_value, environment_value, second)
    assert first.content_sha256 == second.content_sha256
    assert first_result == second_result
    assert first_result.content_sha256 == second_result.content_sha256


@pytest.mark.parametrize(
    "kind",
    (
        ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL,
        ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE,
        ApplicationEnvironmentKind.BLOTTER,
        ApplicationEnvironmentKind.SKIN,
        ApplicationEnvironmentKind.SKIN_SURROGATE,
        ApplicationEnvironmentKind.FABRIC,
        ApplicationEnvironmentKind.CREAM_OR_EMULSION,
        ApplicationEnvironmentKind.SOAP_OR_CLEANSER,
        ApplicationEnvironmentKind.OTHER_PRODUCT_MATRIX,
    ),
)
def test_each_substrate_kind_requires_its_own_exact_model(
    kind: ApplicationEnvironmentKind,
) -> None:
    *_, request, router = executable_case(kind)
    result = router.predict_dynamic_release(request)
    assert result.status is ModelResultStatus.COMPUTED
    assert result.applicability.state is ApplicabilityState.IN_DOMAIN
    assert result.output is not None
    assert result.output.payload.to_mapping()["substrate_kind"] == kind.value


def test_cross_substrate_request_abstains_before_compute() -> None:
    matrix_value, _, inputs, adapter, _, router = executable_case(
        ApplicationEnvironmentKind.BLOTTER
    )
    skin_environment = environment(ApplicationEnvironmentKind.SKIN)
    request = request_for(
        adapter,
        inputs,
        matrix_value=matrix_value,
        environment_value=skin_environment,
    )
    result = router.predict_dynamic_release(request)
    assert result.status is ModelResultStatus.ABSTAINED
    assert result.output is None
    assert result.applicability.state is ApplicabilityState.INSUFFICIENT_INPUT
    assert "environment:content_binding" in result.missing_inputs
    assert "substrate_model:exact_kind_binding" in result.missing_inputs


def test_tampered_or_extra_input_reference_abstains() -> None:
    matrix_value, environment_value, inputs, adapter, _, router = executable_case()
    wrong = ModelInputReference(
        role=C6_INPUT_ROLE,
        input_id=inputs.input_set_id,
        content_sha256="e" * 64,
    )
    extra = ModelInputReference(
        role="unrelated",
        input_id="unrelated:v1",
        content_sha256="f" * 64,
    )
    for references in ((wrong,), (inputs.to_model_input_reference(), extra)):
        request = request_for(
            adapter,
            inputs,
            matrix_value=matrix_value,
            environment_value=environment_value,
            input_references=references,
        )
        result = router.predict_dynamic_release(request)
        assert result.status is ModelResultStatus.ABSTAINED
        assert result.applicability.state is ApplicabilityState.INSUFFICIENT_INPUT
        assert "input_reference:c6_dynamic_release_input_set" in result.missing_inputs


@pytest.mark.parametrize(
    "case",
    ("basis", "mass_unit", "temperature_unit", "area_unit", "film_unit"),
)
def test_incompatible_context_abstains_fail_closed(case: str) -> None:
    kind = ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE
    matrix_value = matrix()
    environment_value = environment(kind)
    if case == "basis":
        matrix_value = matrix(basis=MatrixQuantityBasis.MASS_FRACTION, unit="1")
    elif case == "mass_unit":
        matrix_value = matrix(unit="g")
    elif case == "temperature_unit":
        environment_value = environment(kind, temperature_unit="degC")
    elif case == "area_unit":
        environment_value = environment(kind, area_unit="cm2")
    elif case == "film_unit":
        environment_value = environment(kind, film_unit="um")

    inputs = input_set(
        matrix_value=matrix_value,
        environment_value=environment_value,
        kind=kind,
    )
    adapter = DynamicReleaseAdapter(
        input_set=inputs,
        code_commit=CODE_COMMIT,
        implementation_sha256=IMPLEMENTATION_SHA256,
    )
    request = request_for(
        adapter,
        inputs,
        matrix_value=matrix_value,
        environment_value=environment_value,
    )
    result = VersionedModelRouter((adapter,)).predict_dynamic_release(request)
    assert result.status is ModelResultStatus.ABSTAINED
    assert result.output is None
    assert result.applicability.state is ApplicabilityState.OUTSIDE_APPLICABILITY_DOMAIN


def test_missing_matrix_temperature_abstains_fail_closed() -> None:
    kind = ApplicationEnvironmentKind.OPEN_LIQUID_SURFACE
    matrix_value = replace(
        matrix(),
        temperature=None,
        completeness=CompositionCompleteness.PARTIAL,
        missing_fields=(MatrixMissingField.TEMPERATURE,),
    )
    environment_value = environment(kind)
    inputs = input_set(
        matrix_value=matrix_value,
        environment_value=environment_value,
        kind=kind,
    )
    adapter = DynamicReleaseAdapter(
        input_set=inputs,
        code_commit=CODE_COMMIT,
        implementation_sha256=IMPLEMENTATION_SHA256,
    )
    request = request_for(
        adapter,
        inputs,
        matrix_value=matrix_value,
        environment_value=environment_value,
    )

    result = VersionedModelRouter((adapter,)).predict_dynamic_release(request)

    assert result.status is ModelResultStatus.ABSTAINED
    assert result.output is None
    assert result.applicability.state is ApplicabilityState.INSUFFICIENT_INPUT
    assert "matrix:temperature" in result.missing_inputs


def test_router_uncertainty_operation_returns_same_bound_simulation() -> None:
    matrix_value, environment_value, inputs, adapter, _, router = executable_case()
    request = request_for(
        adapter,
        inputs,
        matrix_value=matrix_value,
        environment_value=environment_value,
        operation=ModelOperation.PROPAGATE_UNCERTAINTY,
    )
    result = router.propagate_uncertainty(request)
    assert result.status is ModelResultStatus.COMPUTED
    assert result.uncertainty.kind is UncertaintyKind.UNKNOWN
    assert result.output is not None
    assert result.output.payload.to_mapping()["uncertainty_interpretation"] == (
        "DETERMINISTIC_PARAMETER_SENSITIVITY_NOT_STATISTICAL_INTERVAL"
    )


def test_output_uses_only_physical_labels_and_excludes_sensory_layers() -> None:
    *_, request, router = executable_case()
    result = router.predict_dynamic_release(request)
    assert result.output is not None
    assert result.output.quantity == "predicted_physical_trajectories"
    payload = result.output.payload.to_mapping()
    assert payload["output_labels"] == [item.value for item in PERMITTED_C6_OUTPUT_LABELS]
    assert payload["modeled_layers"] == [
        "EQUILIBRIUM_PARTITION",
        "MASS_TRANSFER_AND_EVAPORATION",
        "SUBSTRATE_SORPTION",
        "PHYSICAL_HEADSPACE_TRAJECTORY",
    ]
    assert payload["excluded_sensory_layers"] == [
        "OLFACTORY_ADAPTATION",
        "PERCEIVED_INTENSITY",
        "TEMPORAL_ATTRIBUTE_PROFILE",
    ]
    assert payload["authority"] == "SIMULATION_ONLY_UNCALIBRATED"
    assert payload["empirical_metrics_present"] is False
    assert payload["empirical_promotion_allowed"] is False
    forbidden_keys = {"longevity", "sillage", "projection", "perceived_intensity"}
    assert forbidden_keys.isdisjoint(payload)


def test_physical_persistence_is_residual_mass_not_sensory_duration() -> None:
    matrix_value, environment_value, inputs, _, _, _ = executable_case()
    simulation = simulate_dynamic_release(matrix_value, environment_value, inputs)
    for trajectory in simulation.scenarios:
        for frame in trajectory.frames:
            residual = frame.total_condensed_mass_mg + frame.total_sorbed_mass_mg
            assert frame.physical_persistence_fraction == pytest.approx(residual / 10.0)


def test_output_and_c3_result_round_trip_are_hash_stable() -> None:
    *_, request, router = executable_case()
    result = router.predict_dynamic_release(request)
    restored = VersionedModelResult.from_mapping(result.to_mapping())
    assert restored == result
    assert restored.content_sha256 == result.content_sha256


def test_compartment_state_rejects_negative_or_nonclosing_mass() -> None:
    with pytest.raises(DynamicReleaseContractError, match="non-negative"):
        ComponentCompartmentState(
            component_id="component:active",
            condensed_mass_mg=-1.0,
            gas_mass_mg=0.0,
            sorbed_mass_mg=0.0,
            sink_mass_mg=0.0,
            initial_total_mass_mg=1.0,
            effective_condensed_to_gas_rate_s_minus_1=0.0,
            mass_balance_abs_error_mg=0.0,
        )
    with pytest.raises(DynamicReleaseContractError, match="mass balance"):
        ComponentCompartmentState(
            component_id="component:active",
            condensed_mass_mg=0.5,
            gas_mass_mg=0.0,
            sorbed_mass_mg=0.0,
            sink_mass_mg=0.0,
            initial_total_mass_mg=1.0,
            effective_condensed_to_gas_rate_s_minus_1=0.0,
            mass_balance_abs_error_mg=0.5,
        )


def test_direct_simulation_rejects_context_hash_or_substrate_mismatch() -> None:
    matrix_value, environment_value, inputs, _, _, _ = executable_case(
        ApplicationEnvironmentKind.BLOTTER
    )
    with pytest.raises(DynamicReleaseContractError, match="environment hash"):
        simulate_dynamic_release(
            matrix_value,
            environment(ApplicationEnvironmentKind.SKIN),
            inputs,
        )
    with pytest.raises(DynamicReleaseContractError, match="matrix hash"):
        simulate_dynamic_release(
            replace(matrix_value, matrix_version="2"),
            environment_value,
            inputs,
        )


def test_c6_module_has_no_legacy_runtime_database_or_production_dependency() -> None:
    source = Path(dynamic_release_module.__file__).read_text(encoding="utf-8")
    forbidden = (
        "engine.pipeline.simulator",
        "engine.thermo.trajectory",
        "engine.temporal_graph",
        "engine.temporal_volatility",
        "engine.diffusion_model",
        "engine.skin_interaction",
        "engine.workbench",
        "engine.optimizer",
        "sqlalchemy",
        "sqlite3",
        "backend.",
    )
    assert not any(marker in source for marker in forbidden)


def test_c6_contracts_are_exported_and_registered_for_project_verification() -> None:
    import engine.physics as physics

    expected = {
        "C6_INPUT_ROLE",
        "C6_MODEL_VERSION",
        "PERMITTED_C6_OUTPUT_LABELS",
        "ComponentCompartmentState",
        "DynamicComponentParameters",
        "DynamicParameterAuthority",
        "DynamicReleaseAdapter",
        "DynamicReleaseContractError",
        "DynamicReleaseInputSet",
        "InitialCompartmentMass",
        "PhysicalProcessLayer",
        "PhysicalTrajectoryLabel",
        "RateScenario",
        "SubstrateModelParameters",
        "simulate_dynamic_release",
    }
    assert expected.issubset(set(physics.__all__))
    for name in expected:
        assert getattr(physics, name) is not None

    verifier = Path("engine/project_verification.py").read_text(encoding="utf-8")
    assert "engine/physics/dynamic_release.py" in verifier
    assert "tests/test_c6_dynamic_release.py" in verifier
