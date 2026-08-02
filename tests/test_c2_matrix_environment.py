"""Build C2 matrix and application-environment contract tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from engine.physics.matrix_environment import (
    CompositionCompleteness,
    DeclaredQuantity,
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
