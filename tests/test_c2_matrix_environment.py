"""Build C2 matrix and application-environment contract tests."""

from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
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
    MatrixEnvironmentContractError,
    MatrixMissingField,
    MatrixQuantityBasis,
    MatrixStage,
)
from engine.physics.properties import UncertaintyDescriptor

REQUIRED_MATRIX_STAGES = {
    "STOCK_SOLUTION",
    "CONCENTRATE",
    "FINISHED_PERFUME",
    "APPLICATION_FILM",
    "SAMPLED_HEADSPACE",
}
REQUIRED_COMPONENT_ROLES = {
    "ETHANOL",
    "WATER",
    "DPG",
    "DEP",
    "TEC",
    "IPM",
    "OTHER_CARRIER",
    "ACTIVE_FRAGRANCE",
    "DISSOLVED_SOLID",
    "OTHER_PRODUCT_PHASE",
}
REQUIRED_QUANTITY_BASES = {
    "MASS_FRACTION",
    "VOLUME_FRACTION",
    "MOLE_FRACTION",
    "MASS",
    "VOLUME",
    "AMOUNT",
}
REQUIRED_COMPLETENESS = {"EXACT", "PARTIAL", "UNRESOLVED"}
REQUIRED_MATRIX_MISSING_FIELDS = {
    "component_composition",
    "temperature",
    "pressure",
    "relative_humidity",
    "total_mass",
    "total_volume",
}
REQUIRED_ENVIRONMENT_KINDS = {
    "SEALED_EQUILIBRIUM_VIAL",
    "OPEN_LIQUID_SURFACE",
    "BLOTTER",
    "SKIN",
    "SKIN_SURROGATE",
    "FABRIC",
    "CREAM_OR_EMULSION",
    "SOAP_OR_CLEANSER",
    "OTHER_PRODUCT_MATRIX",
}
REQUIRED_ENVIRONMENT_FIELDS = {
    "dose",
    "area",
    "film_thickness",
    "geometry",
    "substrate",
    "temperature",
    "relative_humidity",
    "airflow",
    "equilibration_or_drying_time",
    "sampling_time",
    "sampling_method",
    "vessel_volume",
    "headspace_volume",
}
FORMULA_SHA256 = "a" * 64
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


def unknown(reason: str = "not quantified") -> UncertaintyDescriptor:
    return UncertaintyDescriptor.unknown(reason)


def q(value: float, unit: str) -> DeclaredQuantity:
    return DeclaredQuantity(value=value, unit=unit)


def component(
    component_id: str,
    name: str,
    role: MatrixComponentRole,
    value: float,
    basis: MatrixQuantityBasis = MatrixQuantityBasis.MASS_FRACTION,
    unit: str = "1",
) -> MatrixComponent:
    return MatrixComponent(
        component_id=component_id,
        name=name,
        role=role,
        basis=basis,
        quantity=q(value, unit),
        source_reference=f"formula-declaration:{component_id}:v1",
        uncertainty=unknown(),
    )


def exact_matrix(
    *,
    stage: MatrixStage = MatrixStage.FINISHED_PERFUME,
    ethanol_fraction: float = 0.8,
    gas_comparison: bool = False,
) -> MatrixComposition:
    return MatrixComposition(
        matrix_id="matrix:formula-17:finished",
        matrix_version="1",
        stage=stage,
        components=(
            component(
                "cas:64-17-5",
                "ethanol",
                MatrixComponentRole.ETHANOL,
                ethanol_fraction,
            ),
            component(
                "formula:active-fragrance",
                "active fragrance",
                MatrixComponentRole.ACTIVE_FRAGRANCE,
                1.0 - ethanol_fraction,
            ),
        ),
        temperature=q(298.15, "K"),
        pressure=q(101325.0, "Pa"),
        relative_humidity=q(50.0, "%") if gas_comparison else None,
        gas_comparison=gas_comparison,
        total_mass=q(25.0, "g"),
        total_volume=q(30.0, "mL"),
        uncertainty=unknown("matrix uncertainty not measured"),
        phase_assumptions=("single liquid phase",),
        completeness=CompositionCompleteness.EXACT,
        missing_fields=(),
    )


def blotter_environment() -> ApplicationEnvironment:
    return ApplicationEnvironment(
        environment_id="environment:blotter:standard-1",
        environment_version="1",
        kind=ApplicationEnvironmentKind.BLOTTER,
        dose=q(0.05, "mL"),
        area=q(5.0, "cm2"),
        film_thickness=None,
        geometry="1 cm application line on paper blotter",
        substrate="cellulose fragrance blotter lot B-17",
        temperature=q(298.15, "K"),
        relative_humidity=q(50.0, "%"),
        airflow=q(0.1, "m/s"),
        equilibration_or_drying_time=q(60.0, "s"),
        sampling_time=q(300.0, "s"),
        sampling_method="dynamic headspace at blotter centerline",
        vessel_volume=None,
        headspace_volume=None,
        uncertainty=unknown("environment uncertainty not measured"),
        missing_fields=(),
        not_applicable_fields=(
            EnvironmentField.FILM_THICKNESS,
            EnvironmentField.VESSEL_VOLUME,
            EnvironmentField.HEADSPACE_VOLUME,
        ),
    )


def sealed_vial_environment() -> ApplicationEnvironment:
    return ApplicationEnvironment(
        environment_id="environment:sealed-vial:spme-1",
        environment_version="1",
        kind=ApplicationEnvironmentKind.SEALED_EQUILIBRIUM_VIAL,
        dose=q(0.01, "mL"),
        area=q(1.0, "cm2"),
        film_thickness=None,
        geometry="2 mL crimp vial with flat liquid surface",
        substrate="borosilicate glass vial lot V-4",
        temperature=q(298.15, "K"),
        relative_humidity=q(50.0, "%"),
        airflow=q(0.0, "m/s"),
        equilibration_or_drying_time=q(3600.0, "s"),
        sampling_time=q(3600.0, "s"),
        sampling_method="SPME fiber exposed in sealed headspace",
        vessel_volume=q(2.0, "mL"),
        headspace_volume=q(1.0, "mL"),
        uncertainty=unknown("environment uncertainty not measured"),
        missing_fields=(),
        not_applicable_fields=(EnvironmentField.FILM_THICKNESS,),
    )


def model_request(
    *,
    matrix: MatrixComposition | None = None,
    environment: ApplicationEnvironment | None = None,
) -> MatrixAwareModelRequest:
    return MatrixAwareModelRequest(
        purpose="c2 distinguishability contract test",
        formula_id="formula:17",
        formula_sha256=FORMULA_SHA256,
        matrix=matrix or exact_matrix(),
        environment=environment or blotter_environment(),
    )


def test_c2_matrix_vocabulary_is_closed() -> None:
    assert {item.value for item in MatrixStage} == REQUIRED_MATRIX_STAGES
    assert {item.value for item in MatrixComponentRole} == REQUIRED_COMPONENT_ROLES
    assert {item.value for item in MatrixQuantityBasis} == REQUIRED_QUANTITY_BASES
    assert {item.value for item in CompositionCompleteness} == REQUIRED_COMPLETENESS
    assert {item.value for item in MatrixMissingField} == REQUIRED_MATRIX_MISSING_FIELDS


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True])
def test_declared_quantity_rejects_non_finite_or_boolean(value: object) -> None:
    with pytest.raises(MatrixEnvironmentContractError):
        DeclaredQuantity(value=value, unit="g")  # type: ignore[arg-type]


def test_declared_quantity_requires_explicit_unit_and_is_frozen() -> None:
    with pytest.raises(MatrixEnvironmentContractError, match="unit"):
        q(1.0, " ")
    quantity = q(1.0, "g")
    with pytest.raises(FrozenInstanceError):
        quantity.value = 2.0  # type: ignore[misc]


def test_declared_quantity_round_trip_is_closed() -> None:
    quantity = q(1.25, "g")
    payload = quantity.to_mapping()
    assert payload == {
        "schema": "c2-declared-quantity-v1",
        "value": 1.25,
        "unit": "g",
    }
    assert DeclaredQuantity.from_mapping(payload) == quantity
    with pytest.raises(MatrixEnvironmentContractError, match="unknown fields"):
        DeclaredQuantity.from_mapping({**payload, "comment": "not canonical"})


def test_fraction_component_requires_unit_one_and_closed_range() -> None:
    with pytest.raises(MatrixEnvironmentContractError, match="unit 1"):
        component(
            "cas:64-17-5",
            "ethanol",
            MatrixComponentRole.ETHANOL,
            0.8,
            unit="%",
        )
    with pytest.raises(MatrixEnvironmentContractError, match="between 0 and 1"):
        component(
            "cas:64-17-5",
            "ethanol",
            MatrixComponentRole.ETHANOL,
            1.1,
        )


def test_absolute_component_quantity_must_be_non_negative() -> None:
    with pytest.raises(MatrixEnvironmentContractError, match="non-negative"):
        component(
            "cas:64-17-5",
            "ethanol",
            MatrixComponentRole.ETHANOL,
            -0.1,
            basis=MatrixQuantityBasis.MASS,
            unit="g",
        )


@pytest.mark.parametrize("field_name", ["component_id", "name", "source_reference"])
def test_component_requires_nonblank_identity_and_source(field_name: str) -> None:
    original = component(
        "cas:64-17-5",
        "ethanol",
        MatrixComponentRole.ETHANOL,
        0.8,
    )
    with pytest.raises(MatrixEnvironmentContractError, match=field_name):
        replace(original, **{field_name: " "})


def test_component_requires_closed_types_and_uncertainty() -> None:
    original = component(
        "cas:64-17-5",
        "ethanol",
        MatrixComponentRole.ETHANOL,
        0.8,
    )
    with pytest.raises(MatrixEnvironmentContractError, match="role"):
        replace(original, role="ETHANOL")  # type: ignore[arg-type]
    with pytest.raises(MatrixEnvironmentContractError, match="basis"):
        replace(original, basis="MASS_FRACTION")  # type: ignore[arg-type]
    with pytest.raises(MatrixEnvironmentContractError, match="uncertainty"):
        replace(original, uncertainty="unknown")  # type: ignore[arg-type]


def test_component_round_trip_detects_tampering() -> None:
    original = component(
        "cas:64-17-5",
        "ethanol",
        MatrixComponentRole.ETHANOL,
        0.8,
    )
    payload = original.to_mapping()
    assert MatrixComponent.from_mapping(payload) == original
    tampered = dict(payload)
    tampered["quantity"] = q(0.7, "1").to_mapping()
    with pytest.raises(MatrixEnvironmentContractError, match="content_sha256"):
        MatrixComponent.from_mapping(tampered)


def test_exact_fraction_matrix_requires_fraction_closure() -> None:
    matrix = exact_matrix()
    assert sum(item.quantity.value for item in matrix.components) == 1.0
    with pytest.raises(MatrixEnvironmentContractError, match="sum to 1"):
        replace(
            matrix,
            components=(
                component("ethanol", "ethanol", MatrixComponentRole.ETHANOL, 0.7),
                component(
                    "active",
                    "active fragrance",
                    MatrixComponentRole.ACTIVE_FRAGRANCE,
                    0.2,
                ),
            ),
        )


def test_component_order_does_not_change_matrix_identity() -> None:
    matrix = exact_matrix()
    reversed_matrix = replace(matrix, components=tuple(reversed(matrix.components)))
    assert reversed_matrix.components == matrix.components
    assert reversed_matrix.content_sha256 == matrix.content_sha256


def test_matrix_stage_and_composition_change_identity() -> None:
    finished = exact_matrix()
    film = replace(finished, stage=MatrixStage.APPLICATION_FILM)
    wetter = exact_matrix(ethanol_fraction=0.75)
    assert len({finished.content_sha256, film.content_sha256, wetter.content_sha256}) == 3


def test_matrix_conditions_totals_and_phase_change_identity() -> None:
    baseline = exact_matrix()
    warmer = replace(baseline, temperature=q(303.15, "K"))
    larger = replace(baseline, total_volume=q(50.0, "mL"))
    multiphase = replace(baseline, phase_assumptions=("two liquid phases",))
    assert (
        len(
            {
                baseline.content_sha256,
                warmer.content_sha256,
                larger.content_sha256,
                multiphase.content_sha256,
            }
        )
        == 4
    )


def test_matrix_rejects_empty_or_duplicate_components() -> None:
    matrix = exact_matrix()
    with pytest.raises(MatrixEnvironmentContractError, match="components"):
        replace(matrix, components=())
    duplicate = replace(matrix.components[0], component_id="CAS:64-17-5")
    with pytest.raises(MatrixEnvironmentContractError, match="unique"):
        replace(matrix, components=(*matrix.components, duplicate))


@pytest.mark.parametrize("field_name", ["matrix_id", "matrix_version"])
def test_matrix_requires_nonblank_identity_and_version(field_name: str) -> None:
    with pytest.raises(MatrixEnvironmentContractError, match=field_name):
        replace(exact_matrix(), **{field_name: " "})


def test_matrix_rejects_invalid_phase_conditions_totals_and_types() -> None:
    matrix = exact_matrix()
    with pytest.raises(MatrixEnvironmentContractError, match="phase_assumptions"):
        replace(matrix, phase_assumptions=(" ",))
    with pytest.raises(MatrixEnvironmentContractError, match="pressure"):
        replace(matrix, pressure=q(0.0, "Pa"))
    with pytest.raises(MatrixEnvironmentContractError, match="total_mass"):
        replace(matrix, total_mass=q(-1.0, "g"))
    with pytest.raises(MatrixEnvironmentContractError, match="stage"):
        replace(matrix, stage="FINISHED_PERFUME")  # type: ignore[arg-type]
    with pytest.raises(MatrixEnvironmentContractError, match="uncertainty"):
        replace(matrix, uncertainty="unknown")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field_name", "missing_field"),
    [
        ("temperature", MatrixMissingField.TEMPERATURE),
        ("pressure", MatrixMissingField.PRESSURE),
        ("total_mass", MatrixMissingField.TOTAL_MASS),
        ("total_volume", MatrixMissingField.TOTAL_VOLUME),
    ],
)
def test_exact_matrix_rejects_absent_required_fields(
    field_name: str,
    missing_field: MatrixMissingField,
) -> None:
    matrix = exact_matrix()
    with pytest.raises(MatrixEnvironmentContractError, match=field_name):
        replace(matrix, **{field_name: None})
    with pytest.raises(MatrixEnvironmentContractError, match="missing_fields"):
        replace(matrix, missing_fields=(missing_field,))


def test_partial_matrix_requires_and_matches_missing_fields() -> None:
    matrix = exact_matrix()
    with pytest.raises(MatrixEnvironmentContractError, match="missing_fields"):
        replace(matrix, completeness=CompositionCompleteness.PARTIAL)
    partial = replace(
        matrix,
        completeness=CompositionCompleteness.PARTIAL,
        temperature=None,
        missing_fields=(MatrixMissingField.TEMPERATURE,),
    )
    assert partial.temperature is None
    with pytest.raises(MatrixEnvironmentContractError, match="temperature"):
        replace(
            matrix,
            completeness=CompositionCompleteness.PARTIAL,
            temperature=None,
            missing_fields=(MatrixMissingField.PRESSURE,),
        )


def test_unresolved_matrix_requires_missing_fields() -> None:
    with pytest.raises(MatrixEnvironmentContractError, match="missing_fields"):
        replace(exact_matrix(), completeness=CompositionCompleteness.UNRESOLVED)


def test_gas_comparison_requires_declared_or_explicitly_missing_humidity() -> None:
    with pytest.raises(MatrixEnvironmentContractError, match="relative_humidity"):
        replace(exact_matrix(), gas_comparison=True)
    partial = replace(
        exact_matrix(),
        gas_comparison=True,
        completeness=CompositionCompleteness.PARTIAL,
        missing_fields=(MatrixMissingField.RELATIVE_HUMIDITY,),
    )
    assert partial.relative_humidity is None
    assert exact_matrix().relative_humidity is None


def test_partial_component_composition_does_not_claim_fraction_closure() -> None:
    matrix = exact_matrix()
    partial = replace(
        matrix,
        components=(
            component("ethanol", "ethanol", MatrixComponentRole.ETHANOL, 0.7),
            component(
                "active",
                "active fragrance",
                MatrixComponentRole.ACTIVE_FRAGRANCE,
                0.2,
            ),
        ),
        completeness=CompositionCompleteness.PARTIAL,
        missing_fields=(MatrixMissingField.COMPONENT_COMPOSITION,),
    )
    assert partial.completeness is CompositionCompleteness.PARTIAL


def test_matrix_round_trip_is_stable_and_detects_tampering() -> None:
    matrix = exact_matrix(gas_comparison=True)
    payload = matrix.to_mapping()
    assert MatrixComposition.from_mapping(payload) == matrix
    reordered = dict(payload)
    serialized_components = payload["components"]
    assert isinstance(serialized_components, list)
    reordered["components"] = list(reversed(serialized_components))
    assert MatrixComposition.from_mapping(reordered) == matrix
    tampered = dict(payload)
    tampered["matrix_version"] = "2"
    with pytest.raises(MatrixEnvironmentContractError, match="content_sha256"):
        MatrixComposition.from_mapping(tampered)


def test_matrix_parser_rejects_unknown_fields() -> None:
    payload = exact_matrix().to_mapping()
    with pytest.raises(MatrixEnvironmentContractError, match="unknown fields"):
        MatrixComposition.from_mapping({**payload, "label": "ethanol solution"})


def test_c2_environment_vocabulary_is_closed() -> None:
    assert {item.value for item in ApplicationEnvironmentKind} == REQUIRED_ENVIRONMENT_KINDS
    assert {item.value for item in EnvironmentField} == REQUIRED_ENVIRONMENT_FIELDS


def test_environment_requires_every_absent_field_to_be_classified() -> None:
    environment = blotter_environment()
    with pytest.raises(MatrixEnvironmentContractError, match="classified"):
        replace(
            environment,
            not_applicable_fields=(EnvironmentField.FILM_THICKNESS,),
        )


def test_environment_absence_classifications_are_disjoint() -> None:
    environment = blotter_environment()
    with pytest.raises(MatrixEnvironmentContractError, match="overlap"):
        replace(
            environment,
            missing_fields=(EnvironmentField.HEADSPACE_VOLUME,),
        )


def test_present_environment_field_cannot_be_classified_absent() -> None:
    environment = blotter_environment()
    with pytest.raises(MatrixEnvironmentContractError, match="present"):
        replace(
            environment,
            not_applicable_fields=(
                *environment.not_applicable_fields,
                EnvironmentField.DOSE,
            ),
        )


def test_environment_rejects_unknown_classification_type() -> None:
    with pytest.raises(MatrixEnvironmentContractError, match="EnvironmentField"):
        replace(
            blotter_environment(),
            missing_fields=("headspace_volume",),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "dose",
        "area",
        "film_thickness",
        "relative_humidity",
        "airflow",
        "equilibration_or_drying_time",
        "sampling_time",
        "vessel_volume",
        "headspace_volume",
    ],
)
def test_environment_rejects_negative_physical_quantities(field_name: str) -> None:
    environment = sealed_vial_environment()
    with pytest.raises(MatrixEnvironmentContractError, match=field_name):
        replace(environment, **{field_name: q(-1.0, "declared-unit")})


@pytest.mark.parametrize("field_name", ["geometry", "substrate", "sampling_method"])
def test_environment_rejects_blank_present_text(field_name: str) -> None:
    with pytest.raises(MatrixEnvironmentContractError, match=field_name):
        replace(blotter_environment(), **{field_name: " "})


@pytest.mark.parametrize("field_name", ["environment_id", "environment_version"])
def test_environment_requires_nonblank_identity_and_version(field_name: str) -> None:
    with pytest.raises(MatrixEnvironmentContractError, match=field_name):
        replace(blotter_environment(), **{field_name: " "})


def test_environment_requires_closed_kind_and_uncertainty() -> None:
    with pytest.raises(MatrixEnvironmentContractError, match="kind"):
        replace(blotter_environment(), kind="BLOTTER")  # type: ignore[arg-type]
    with pytest.raises(MatrixEnvironmentContractError, match="uncertainty"):
        replace(
            blotter_environment(),
            uncertainty="unknown",  # type: ignore[arg-type]
        )


def test_environment_context_changes_identity() -> None:
    baseline = blotter_environment()
    variants = (
        replace(baseline, kind=ApplicationEnvironmentKind.FABRIC),
        replace(baseline, substrate="cotton fabric lot C-2"),
        replace(baseline, dose=q(0.1, "mL")),
        replace(baseline, relative_humidity=q(65.0, "%")),
        replace(baseline, airflow=q(0.2, "m/s")),
        replace(baseline, sampling_time=q(600.0, "s")),
        replace(baseline, sampling_method="static headspace sample"),
        replace(sealed_vial_environment(), vessel_volume=q(5.0, "mL")),
        replace(sealed_vial_environment(), headspace_volume=q(3.0, "mL")),
    )
    hashes = {baseline.content_sha256, *(item.content_sha256 for item in variants)}
    assert len(hashes) == 1 + len(variants)


def test_environment_classification_order_does_not_change_identity() -> None:
    baseline = blotter_environment()
    reordered = replace(
        baseline,
        not_applicable_fields=tuple(reversed(baseline.not_applicable_fields)),
    )
    assert reordered.not_applicable_fields == baseline.not_applicable_fields
    assert reordered.content_sha256 == baseline.content_sha256


@pytest.mark.parametrize(
    ("field_name", "environment_field"),
    [
        ("vessel_volume", EnvironmentField.VESSEL_VOLUME),
        ("headspace_volume", EnvironmentField.HEADSPACE_VOLUME),
        ("sampling_time", EnvironmentField.SAMPLING_TIME),
        ("sampling_method", EnvironmentField.SAMPLING_METHOD),
    ],
)
@pytest.mark.parametrize("classification", ["missing", "not_applicable"])
def test_sealed_vial_requires_apparatus_and_sampling_fields(
    field_name: str,
    environment_field: EnvironmentField,
    classification: str,
) -> None:
    environment = sealed_vial_environment()
    changes: dict[str, object] = {field_name: None}
    if classification == "missing":
        changes["missing_fields"] = (environment_field,)
    else:
        changes["not_applicable_fields"] = (
            *environment.not_applicable_fields,
            environment_field,
        )
    with pytest.raises(MatrixEnvironmentContractError, match="sealed"):
        replace(environment, **changes)


def test_environment_round_trip_is_stable_and_detects_tampering() -> None:
    environment = blotter_environment()
    payload = environment.to_mapping()
    assert ApplicationEnvironment.from_mapping(payload) == environment
    reordered = dict(payload)
    classifications = payload["not_applicable_fields"]
    assert isinstance(classifications, list)
    reordered["not_applicable_fields"] = list(reversed(classifications))
    assert ApplicationEnvironment.from_mapping(reordered) == environment
    tampered = dict(payload)
    tampered["substrate"] = "untested substrate"
    with pytest.raises(MatrixEnvironmentContractError, match="content_sha256"):
        ApplicationEnvironment.from_mapping(tampered)


def test_environment_parser_rejects_unknown_fields() -> None:
    payload = blotter_environment().to_mapping()
    with pytest.raises(MatrixEnvironmentContractError, match="unknown fields"):
        ApplicationEnvironment.from_mapping({**payload, "apparatus_note": "vial"})


def test_same_formula_in_different_matrix_or_environment_changes_request() -> None:
    baseline = model_request()
    changed_matrix = model_request(matrix=exact_matrix(ethanol_fraction=0.75))
    changed_environment = model_request(
        environment=replace(
            blotter_environment(),
            substrate="cotton fabric lot C-2",
        )
    )
    assert (
        len(
            {
                baseline.content_sha256,
                changed_matrix.content_sha256,
                changed_environment.content_sha256,
            }
        )
        == 3
    )


def test_request_serialization_embeds_both_snapshots_and_hashes() -> None:
    request = model_request()
    payload = request.to_mapping()
    matrix_payload = payload["matrix"]
    environment_payload = payload["environment"]
    assert isinstance(matrix_payload, dict)
    assert isinstance(environment_payload, dict)
    assert payload["matrix_sha256"] == request.matrix.content_sha256
    assert payload["environment_sha256"] == request.environment.content_sha256
    assert matrix_payload["content_sha256"] == request.matrix.content_sha256
    assert environment_payload["content_sha256"] == request.environment.content_sha256
    assert MatrixAwareModelRequest.from_mapping(payload) == request


@pytest.mark.parametrize("field_name", ["purpose", "formula_id"])
def test_request_requires_nonblank_purpose_and_formula_id(field_name: str) -> None:
    with pytest.raises(MatrixEnvironmentContractError, match=field_name):
        replace(model_request(), **{field_name: " "})


@pytest.mark.parametrize(
    "digest",
    ["A" * 64, "a" * 63, "g" * 64, "sha256:" + "a" * 64],
)
def test_request_requires_lowercase_sha256_formula_hash(digest: str) -> None:
    with pytest.raises(MatrixEnvironmentContractError, match="formula_sha256"):
        replace(model_request(), formula_sha256=digest)


def test_request_requires_typed_matrix_and_environment() -> None:
    with pytest.raises(MatrixEnvironmentContractError, match="matrix"):
        replace(model_request(), matrix="matrix")  # type: ignore[arg-type]
    with pytest.raises(MatrixEnvironmentContractError, match="environment"):
        replace(
            model_request(),
            environment="environment",  # type: ignore[arg-type]
        )


def test_request_parser_rejects_mismatched_repeated_context_hashes() -> None:
    payload = model_request().to_mapping()
    with pytest.raises(MatrixEnvironmentContractError, match="matrix_sha256"):
        MatrixAwareModelRequest.from_mapping({**payload, "matrix_sha256": "b" * 64})
    with pytest.raises(MatrixEnvironmentContractError, match="environment_sha256"):
        MatrixAwareModelRequest.from_mapping({**payload, "environment_sha256": "b" * 64})


def test_request_parser_rejects_nested_tampering() -> None:
    payload = deepcopy(model_request().to_mapping())
    matrix_payload = payload["matrix"]
    assert isinstance(matrix_payload, dict)
    components = matrix_payload["components"]
    assert isinstance(components, list)
    first_component = components[0]
    assert isinstance(first_component, dict)
    quantity = first_component["quantity"]
    assert isinstance(quantity, dict)
    quantity["value"] = 0.7
    with pytest.raises(MatrixEnvironmentContractError, match="content_sha256"):
        MatrixAwareModelRequest.from_mapping(payload)


def test_request_parser_rejects_schema_key_and_hash_tampering() -> None:
    payload = model_request().to_mapping()
    with pytest.raises(MatrixEnvironmentContractError, match="schema"):
        MatrixAwareModelRequest.from_mapping({**payload, "schema": "c2-request-v0"})
    missing = dict(payload)
    del missing["purpose"]
    with pytest.raises(MatrixEnvironmentContractError, match="missing fields"):
        MatrixAwareModelRequest.from_mapping(missing)
    with pytest.raises(MatrixEnvironmentContractError, match="unknown fields"):
        MatrixAwareModelRequest.from_mapping({**payload, "timestamp": "now"})
    with pytest.raises(MatrixEnvironmentContractError, match="content_sha256"):
        MatrixAwareModelRequest.from_mapping({**payload, "purpose": "tampered"})


def test_request_round_trip_hash_is_reproducible() -> None:
    request = model_request()
    restored = MatrixAwareModelRequest.from_mapping(request.to_mapping())
    assert restored == request
    assert restored.content_sha256 == request.content_sha256


def test_c2_types_are_explicitly_exported_from_engine_physics() -> None:
    import engine.physics as physics
    from engine.physics import (
        ApplicationEnvironment as PublicApplicationEnvironment,
    )
    from engine.physics import (
        ApplicationEnvironmentKind as PublicApplicationEnvironmentKind,
    )
    from engine.physics import (
        CompositionCompleteness as PublicCompositionCompleteness,
    )
    from engine.physics import (
        DeclaredQuantity as PublicDeclaredQuantity,
    )
    from engine.physics import (
        EnvironmentField as PublicEnvironmentField,
    )
    from engine.physics import (
        MatrixAwareModelRequest as PublicMatrixAwareModelRequest,
    )
    from engine.physics import (
        MatrixComponent as PublicMatrixComponent,
    )
    from engine.physics import (
        MatrixComponentRole as PublicMatrixComponentRole,
    )
    from engine.physics import (
        MatrixComposition as PublicMatrixComposition,
    )
    from engine.physics import (
        MatrixEnvironmentContractError as PublicMatrixEnvironmentContractError,
    )
    from engine.physics import (
        MatrixMissingField as PublicMatrixMissingField,
    )
    from engine.physics import (
        MatrixQuantityBasis as PublicMatrixQuantityBasis,
    )
    from engine.physics import (
        MatrixStage as PublicMatrixStage,
    )

    assert PublicApplicationEnvironment is ApplicationEnvironment
    assert PublicApplicationEnvironmentKind is ApplicationEnvironmentKind
    assert PublicCompositionCompleteness is CompositionCompleteness
    assert PublicDeclaredQuantity is DeclaredQuantity
    assert PublicEnvironmentField is EnvironmentField
    assert PublicMatrixAwareModelRequest is MatrixAwareModelRequest
    assert PublicMatrixComponent is MatrixComponent
    assert PublicMatrixComponentRole is MatrixComponentRole
    assert PublicMatrixComposition is MatrixComposition
    assert PublicMatrixEnvironmentContractError is MatrixEnvironmentContractError
    assert PublicMatrixMissingField is MatrixMissingField
    assert PublicMatrixQuantityBasis is MatrixQuantityBasis
    assert PublicMatrixStage is MatrixStage
    assert set(physics.__all__) == PUBLIC_C1_NAMES | PUBLIC_C2_NAMES
    assert len(physics.__all__) == len(set(physics.__all__))


def test_c2_module_has_no_runtime_or_estimator_dependency() -> None:
    source_path = Path("engine/physics/matrix_environment.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    public_functions: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                public_functions.add(node.name)

    forbidden_prefixes = (
        "backend",
        "sqlalchemy",
        "engine.mixture",
        "engine.solvent_matrix",
        "engine.workbench",
        "engine.headspace",
        "engine.property_estimator",
    )
    assert not any(module.startswith(forbidden_prefixes) for module in imported_modules)
    assert not {
        name
        for name in public_functions
        if any(token in name for token in ("evaluate", "predict", "estimate"))
    }
