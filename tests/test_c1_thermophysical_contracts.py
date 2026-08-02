from __future__ import annotations

import math

import pytest

from engine.physics.properties import (
    CanonicalScope,
    ClaimGrade,
    PropertyConditions,
    PropertyDatum,
    PropertyIdentity,
    PropertyValueKind,
    SelectionStatus,
    SourceReference,
    ThermophysicalContractError,
    ThermophysicalProperty,
    UncertaintyDescriptor,
    UncertaintyKind,
)
from engine.physics.vapor_pressure import (
    ExtrapolationPolicy,
    TemperatureRange,
    VaporPressureEquationType,
    VaporPressureRepresentation,
)

REQUIRED_PROPERTIES = {
    "vapor_pressure",
    "molecular_weight",
    "density",
    "boiling_point",
    "enthalpy_of_vaporization",
    "water_solubility",
    "solvent_solubility",
    "logp",
    "logkow",
    "henry_constant",
    "activity_coefficient_parameters",
    "diffusion_coefficient",
    "mass_transfer_parameters",
    "substrate_sorption_parameters",
    "heat_capacity",
    "phase_data",
}

REQUIRED_UNCERTAINTY_KINDS = {
    "STANDARD_UNCERTAINTY",
    "INTERVAL",
    "EMPIRICAL_DISTRIBUTION",
    "PARAMETER_COVARIANCE",
    "BOUNDED_RANGE",
    "UNKNOWN",
}


def test_c1_property_and_uncertainty_vocabulary_is_closed() -> None:
    assert {item.value for item in ThermophysicalProperty} == REQUIRED_PROPERTIES
    assert {item.value for item in UncertaintyKind} == REQUIRED_UNCERTAINTY_KINDS
    assert {item.value for item in PropertyValueKind} == {
        "NUMERIC",
        "CATEGORICAL",
        "INTERVAL",
        "DISTRIBUTION",
        "CENSORED",
    }
    assert {item.value for item in ClaimGrade} == {
        "RELEASE_GRADE",
        "EXPLORATORY",
    }
    assert {item.value for item in SelectionStatus} == {
        "SELECTED",
        "ADVISORY",
        "WITHHELD",
    }


def test_canonical_scope_hash_is_mapping_order_independent() -> None:
    left = CanonicalScope.from_mapping(
        {"temperature_k": 298.15, "matrix": "air"}
    )
    right = CanonicalScope.from_mapping(
        {"matrix": "air", "temperature_k": 298.15}
    )

    assert left == right
    assert left.sha256 == right.sha256
    assert left.to_mapping() == {
        "matrix": "air",
        "temperature_k": 298.15,
    }
    returned = left.to_mapping()
    returned["matrix"] = "water"
    assert left.to_mapping()["matrix"] == "air"


@pytest.mark.parametrize(
    "payload,match",
    (
        (["not", "a", "mapping"], "mapping"),
        ({1: "non-string key"}, "keys must be strings"),
        ({"value": math.nan}, "NaN or Infinity"),
    ),
)
def test_canonical_scope_rejects_noncanonical_payloads(payload, match) -> None:
    with pytest.raises((ThermophysicalContractError, TypeError), match=match):
        CanonicalScope.from_mapping(payload)


def test_identity_conditions_and_subset_support_are_explicit() -> None:
    identity = PropertyIdentity.from_mapping(
        {
            "identity_scope": "CHEMICAL_ENTITY",
            "subject_identity": {
                "chemical_name": "Linalool",
                "cas": "78-70-6",
            },
        }
    )
    request = PropertyConditions.from_mapping(
        {"temperature_k": 298.15, "matrix": "air"}
    )
    observation = PropertyConditions.from_mapping(
        {
            "temperature_k": 298.15,
            "pressure_pa": 101325.0,
            "relative_humidity_percent": 50.0,
            "matrix": "air",
            "phase": "gas",
            "purity_fraction": 0.99,
        }
    )

    assert len(identity.content_sha256) == 64
    assert observation.supports(request)
    assert request != observation
    assert not observation.supports(
        PropertyConditions.from_mapping(
            {"temperature_k": 300.0, "matrix": "air"}
        )
    )


@pytest.mark.parametrize(
    "payload,match",
    (
        (
            {"identity_scope": " ", "subject_identity": {"cas": "78-70-6"}},
            "identity_scope",
        ),
        ({"identity_scope": "CHEMICAL_ENTITY"}, "subject_identity"),
        ({"temperature_k": 0.0}, "temperature_k"),
        ({"pressure_pa": -1.0}, "pressure_pa"),
        ({"relative_humidity_percent": 101.0}, "relative_humidity_percent"),
        ({"purity_fraction": 1.1}, "purity_fraction"),
        ({"matrix": " "}, "matrix"),
    ),
)
def test_identity_and_conditions_reject_invalid_scope(payload, match) -> None:
    constructor = (
        PropertyIdentity.from_mapping
        if "identity_scope" in payload
        else PropertyConditions.from_mapping
    )
    with pytest.raises(ThermophysicalContractError, match=match):
        constructor(payload)


@pytest.mark.parametrize(
    "payload,kind",
    (
        (
            {
                "value_kind": "NUMERIC",
                "numeric_value": 7.0,
                "categorical_value": None,
                "interval_lower": None,
                "interval_upper": None,
                "distribution": None,
                "censoring_qualifier": None,
                "censoring_limit": None,
                "canonical_unit": "Pa",
            },
            PropertyValueKind.NUMERIC,
        ),
        (
            {
                "value_kind": "CATEGORICAL",
                "numeric_value": None,
                "categorical_value": "solid",
                "interval_lower": None,
                "interval_upper": None,
                "distribution": None,
                "censoring_qualifier": None,
                "censoring_limit": None,
                "canonical_unit": "category",
            },
            PropertyValueKind.CATEGORICAL,
        ),
        (
            {
                "value_kind": "INTERVAL",
                "numeric_value": None,
                "categorical_value": None,
                "interval_lower": 6.0,
                "interval_upper": 8.0,
                "distribution": None,
                "censoring_qualifier": None,
                "censoring_limit": None,
                "canonical_unit": "Pa",
            },
            PropertyValueKind.INTERVAL,
        ),
        (
            {
                "value_kind": "DISTRIBUTION",
                "numeric_value": None,
                "categorical_value": None,
                "interval_lower": None,
                "interval_upper": None,
                "distribution": {"values": [6.8, 7.0, 7.2]},
                "censoring_qualifier": None,
                "censoring_limit": None,
                "canonical_unit": "Pa",
            },
            PropertyValueKind.DISTRIBUTION,
        ),
        (
            {
                "value_kind": "CENSORED",
                "numeric_value": None,
                "categorical_value": None,
                "interval_lower": None,
                "interval_upper": None,
                "distribution": None,
                "censoring_qualifier": "LT_LOQ",
                "censoring_limit": 0.1,
                "canonical_unit": "Pa",
            },
            PropertyValueKind.CENSORED,
        ),
    ),
)
def test_property_datum_preserves_all_b2_value_shapes(payload, kind) -> None:
    datum = PropertyDatum.from_b2(payload)
    assert datum.value_kind is kind
    assert len(datum.content_sha256) == 64


@pytest.mark.parametrize(
    "overrides,match",
    (
        ({"canonical_unit": " "}, "canonical_unit"),
        ({"numeric_value": math.inf}, "finite"),
        ({"categorical_value": "also set"}, "NUMERIC"),
        ({"value_kind": "INTERVAL", "numeric_value": None}, "INTERVAL"),
        (
            {
                "value_kind": "CENSORED",
                "numeric_value": None,
                "censoring_qualifier": "LT_LOQ",
            },
            "censoring_limit",
        ),
    ),
)
def test_property_datum_rejects_invalid_or_mixed_shapes(overrides, match) -> None:
    payload = {
        "value_kind": "NUMERIC",
        "numeric_value": 7.0,
        "categorical_value": None,
        "interval_lower": None,
        "interval_upper": None,
        "distribution": None,
        "censoring_qualifier": None,
        "censoring_limit": None,
        "canonical_unit": "Pa",
    }
    payload.update(overrides)
    with pytest.raises(ThermophysicalContractError, match=match):
        PropertyDatum.from_b2(payload)


def test_source_reference_requires_one_complete_source_form() -> None:
    b2 = SourceReference.from_b2_observation(
        {
            "source_version_id": "source-version-1",
            "extraction_record_id": "extraction-1",
            "source_locator": {"page": 12, "table": "2"},
        }
    )
    model = SourceReference.from_model_mapping(
        {
            "source_id": "NIST-WEBBOOK-78-70-6",
            "locator": {"table": "Antoine Equation Parameters"},
        }
    )

    assert b2.source_kind == "B2_OBSERVATION"
    assert model.source_kind == "MODEL_DECLARATION"
    assert b2.content_sha256 != model.content_sha256


@pytest.mark.parametrize(
    "constructor,payload,match",
    (
        (
            SourceReference.from_b2_observation,
            {"source_version_id": "source-only", "source_locator": {}},
            "extraction_record_id",
        ),
        (
            SourceReference.from_model_mapping,
            {"source_id": " ", "locator": {}},
            "source_id",
        ),
    ),
)
def test_source_reference_rejects_incomplete_source_forms(
    constructor, payload, match
) -> None:
    with pytest.raises(ThermophysicalContractError, match=match):
        constructor(payload)


@pytest.mark.parametrize(
    "payload",
    (
        {
            "schema": "c1-uncertainty-v1",
            "kind": "STANDARD_UNCERTAINTY",
            "value": 0.5,
            "unit": "Pa",
        },
        {
            "schema": "c1-uncertainty-v1",
            "kind": "INTERVAL",
            "interval_type": "CONFIDENCE",
            "coverage_probability": 0.95,
            "lower": 6.0,
            "upper": 8.0,
            "unit": "Pa",
        },
        {
            "schema": "c1-uncertainty-v1",
            "kind": "EMPIRICAL_DISTRIBUTION",
            "values": [6.8, 7.0, 7.2],
            "unit": "Pa",
        },
        {
            "schema": "c1-uncertainty-v1",
            "kind": "PARAMETER_COVARIANCE",
            "parameter_names": ["A", "B"],
            "matrix": [[1.0, 0.2], [0.2, 2.0]],
            "parameter_units": {"A": "1", "B": "K"},
        },
        {
            "schema": "c1-uncertainty-v1",
            "kind": "BOUNDED_RANGE",
            "lower": 5.0,
            "upper": 9.0,
            "unit": "Pa",
        },
        {
            "schema": "c1-uncertainty-v1",
            "kind": "UNKNOWN",
            "reason": "not reported",
        },
    ),
)
def test_all_six_uncertainty_shapes_validate(payload) -> None:
    uncertainty = UncertaintyDescriptor.from_mapping(payload)
    assert uncertainty.kind.value == payload["kind"]
    assert len(uncertainty.content_sha256) == 64


@pytest.mark.parametrize(
    "payload,match",
    (
        (
            {
                "schema": "future",
                "kind": "UNKNOWN",
                "reason": "not reported",
            },
            "schema",
        ),
        (
            {
                "schema": "c1-uncertainty-v1",
                "kind": "STANDARD_UNCERTAINTY",
                "value": -0.1,
                "unit": "Pa",
            },
            "non-negative",
        ),
        (
            {
                "schema": "c1-uncertainty-v1",
                "kind": "INTERVAL",
                "interval_type": "CONFIDENCE",
                "coverage_probability": 1.0,
                "lower": 6.0,
                "upper": 8.0,
                "unit": "Pa",
            },
            "coverage_probability",
        ),
        (
            {
                "schema": "c1-uncertainty-v1",
                "kind": "INTERVAL",
                "interval_type": "CREDIBLE",
                "coverage_probability": 0.95,
                "lower": 9.0,
                "upper": 8.0,
                "unit": "Pa",
            },
            "lower",
        ),
        (
            {
                "schema": "c1-uncertainty-v1",
                "kind": "EMPIRICAL_DISTRIBUTION",
                "values": [],
                "unit": "Pa",
            },
            "values",
        ),
        (
            {
                "schema": "c1-uncertainty-v1",
                "kind": "PARAMETER_COVARIANCE",
                "parameter_names": ["A", "A"],
                "matrix": [[1.0, 0.0], [0.0, 1.0]],
                "parameter_units": {"A": "1"},
            },
            "unique",
        ),
        (
            {
                "schema": "c1-uncertainty-v1",
                "kind": "PARAMETER_COVARIANCE",
                "parameter_names": ["A", "B"],
                "matrix": [[1.0, 0.2], [0.1, 1.0]],
                "parameter_units": {"A": "1", "B": "K"},
            },
            "symmetric",
        ),
        (
            {
                "schema": "c1-uncertainty-v1",
                "kind": "PARAMETER_COVARIANCE",
                "parameter_names": ["A", "B"],
                "matrix": [[1.0, 0.0], [0.0, 1.0]],
                "parameter_units": {"A": "1"},
            },
            "parameter_units",
        ),
        (
            {
                "schema": "c1-uncertainty-v1",
                "kind": "BOUNDED_RANGE",
                "lower": 9.0,
                "upper": 5.0,
                "unit": "Pa",
            },
            "lower",
        ),
        (
            {
                "schema": "c1-uncertainty-v1",
                "kind": "UNKNOWN",
                "reason": "not reported",
                "value": 1.0,
            },
            "unknown fields",
        ),
    ),
)
def test_uncertainty_rejects_false_precision_and_malformed_shapes(
    payload, match
) -> None:
    with pytest.raises(ThermophysicalContractError, match=match):
        UncertaintyDescriptor.from_mapping(payload)


def test_unknown_uncertainty_factory_never_invents_a_number() -> None:
    uncertainty = UncertaintyDescriptor.unknown("measurement uncertainty absent")
    assert uncertainty.kind is UncertaintyKind.UNKNOWN
    assert uncertainty.payload.to_mapping() == {
        "schema": "c1-uncertainty-v1",
        "kind": "UNKNOWN",
        "reason": "measurement uncertainty absent",
    }


REQUIRED_VAPOR_EQUATION_TYPES = {
    "MEASURED_TABLE",
    "ANTOINE",
    "WAGNER",
    "DIPPR_STYLE",
    "CLAUSIUS_CLAPEYRON",
    "OTHER_DECLARED_FORM",
}


def _identity_payload() -> dict:
    return {
        "identity_scope": "CHEMICAL_ENTITY",
        "subject_identity": {
            "chemical_name": "Linalool",
            "cas": "78-70-6",
        },
    }


def _standard_uncertainty_payload() -> dict:
    return {
        "schema": "c1-uncertainty-v1",
        "kind": "STANDARD_UNCERTAINTY",
        "value": 0.5,
        "unit": "Pa",
    }


def _model_source_payload() -> dict:
    return {
        "source_id": "NIST-WEBBOOK-78-70-6",
        "locator": {
            "table": "Antoine Equation Parameters",
            "retrieved": "2026-08-02",
        },
    }


def _antoine_payload() -> dict:
    return {
        "schema": "c1-vapor-pressure-representation-v1",
        "model_id": "linalool-antoine-nist",
        "model_version": "1",
        "identity": _identity_payload(),
        "equation_type": "ANTOINE",
        "equation_convention": "log10(P/bar) = A - B / (T/K + C)",
        "coefficients": [
            {"name": "A", "value": 4.11, "unit": "1"},
            {"name": "B", "value": 1500.0, "unit": "K"},
            {"name": "C", "value": -50.0, "unit": "K"},
        ],
        "pressure_unit": "bar",
        "temperature_unit": "K",
        "valid_temperature_range": {"lower_k": 350.0, "upper_k": 500.0},
        "phase_assumption": "liquid-vapor equilibrium",
        "purity_assumption": {"minimum_fraction": 0.99},
        "source": _model_source_payload(),
        "measured_points": [],
        "fit_evidence": {
            "fit_data": "source table",
            "residuals_reported": False,
        },
        "uncertainty": _standard_uncertainty_payload(),
        "extrapolation_policy": "FORBID",
    }


def _measured_table_payload() -> dict:
    payload = _antoine_payload()
    payload.update(
        {
            "model_id": "linalool-measured-table",
            "equation_type": "MEASURED_TABLE",
            "equation_convention": "tabulated pressure at declared temperature",
            "coefficients": [],
            "pressure_unit": "Pa",
            "valid_temperature_range": {
                "lower_k": 298.15,
                "upper_k": 308.15,
            },
            "measured_points": [
                {
                    "temperature_k": 298.15,
                    "pressure": 7.0,
                    "pressure_unit": "Pa",
                },
                {
                    "temperature_k": 308.15,
                    "pressure": 12.0,
                    "pressure_unit": "Pa",
                },
            ],
            "fit_evidence": None,
            "extrapolation_policy": "ADVISORY_ONLY_WITH_WARNING",
        }
    )
    return payload


def test_vapor_pressure_equation_vocabulary_is_exact() -> None:
    assert {
        item.value for item in VaporPressureEquationType
    } == REQUIRED_VAPOR_EQUATION_TYPES
    assert {item.value for item in ExtrapolationPolicy} == {
        "FORBID",
        "ADVISORY_ONLY_WITH_WARNING",
    }


def test_vapor_pressure_equation_model_preserves_every_declared_field() -> None:
    representation = VaporPressureRepresentation.from_mapping(_antoine_payload())

    assert representation.model_id == "linalool-antoine-nist"
    assert representation.model_version == "1"
    assert representation.identity.identity_scope == "CHEMICAL_ENTITY"
    assert representation.equation_type is VaporPressureEquationType.ANTOINE
    assert representation.equation_convention.startswith("log10")
    assert [coefficient.name for coefficient in representation.coefficients] == [
        "A",
        "B",
        "C",
    ]
    assert representation.pressure_unit == "bar"
    assert representation.temperature_unit == "K"
    assert representation.valid_temperature_range.contains(350.0)
    assert representation.valid_temperature_range.contains(500.0)
    assert not representation.valid_temperature_range.contains(349.99)
    assert representation.phase_assumption == "liquid-vapor equilibrium"
    assert representation.purity_assumption.to_mapping() == {
        "minimum_fraction": 0.99
    }
    assert representation.source.model_source_id == "NIST-WEBBOOK-78-70-6"
    assert representation.fit_evidence is not None
    assert representation.uncertainty.kind is UncertaintyKind.STANDARD_UNCERTAINTY
    assert representation.extrapolation_policy is ExtrapolationPolicy.FORBID
    assert len(representation.content_sha256) == 64


def test_vapor_pressure_representation_hash_is_mapping_order_independent() -> None:
    payload = _antoine_payload()
    reversed_payload = dict(reversed(tuple(payload.items())))

    left = VaporPressureRepresentation.from_mapping(payload)
    right = VaporPressureRepresentation.from_mapping(reversed_payload)

    assert left.content_sha256 == right.content_sha256
    assert left.to_mapping() == right.to_mapping()


def test_measured_table_requires_points_and_forbids_coefficients() -> None:
    representation = VaporPressureRepresentation.from_mapping(
        _measured_table_payload()
    )

    assert representation.equation_type is VaporPressureEquationType.MEASURED_TABLE
    assert representation.coefficients == ()
    assert len(representation.measured_points) == 2
    assert representation.fit_evidence is None


@pytest.mark.parametrize(
    "mutator,match",
    (
        (lambda payload: payload.update(coefficients=[]), "coefficients"),
        (
            lambda payload: payload.update(
                coefficients=[
                    {"name": "A", "value": 4.1, "unit": "1"},
                    {"name": "A", "value": 4.2, "unit": "1"},
                ]
            ),
            "unique",
        ),
        (
            lambda payload: payload["coefficients"][0].update(unit=" "),
            "unit",
        ),
        (
            lambda payload: payload["coefficients"][0].update(value=math.nan),
            "finite",
        ),
        (
            lambda payload: payload.update(temperature_unit="degC"),
            "temperature_unit",
        ),
        (
            lambda payload: payload.update(equation_convention=" "),
            "equation_convention",
        ),
        (
            lambda payload: payload.update(phase_assumption=" "),
            "phase_assumption",
        ),
        (
            lambda payload: payload.update(purity_assumption={}),
            "purity_assumption",
        ),
        (
            lambda payload: payload["valid_temperature_range"].update(
                lower_k=500.0, upper_k=350.0
            ),
            "temperature range",
        ),
        (lambda payload: payload.update(unexpected=True), "unknown fields"),
    ),
)
def test_equation_representations_reject_ambiguous_or_invalid_shapes(
    mutator, match
) -> None:
    payload = _antoine_payload()
    mutator(payload)
    with pytest.raises(ThermophysicalContractError, match=match):
        VaporPressureRepresentation.from_mapping(payload)


@pytest.mark.parametrize(
    "mutator,match",
    (
        (lambda payload: payload.update(measured_points=[]), "measured_points"),
        (
            lambda payload: payload.update(
                coefficients=[{"name": "A", "value": 1.0, "unit": "1"}]
            ),
            "forbids coefficients",
        ),
        (
            lambda payload: payload["measured_points"][0].update(pressure=0.0),
            "pressure",
        ),
        (
            lambda payload: payload["measured_points"][0].update(
                pressure_unit="bar"
            ),
            "pressure_unit",
        ),
    ),
)
def test_measured_tables_reject_missing_or_inconsistent_points(mutator, match) -> None:
    payload = _measured_table_payload()
    mutator(payload)
    with pytest.raises(ThermophysicalContractError, match=match):
        VaporPressureRepresentation.from_mapping(payload)


def test_temperature_range_rejects_nonphysical_bounds() -> None:
    with pytest.raises(ThermophysicalContractError, match="temperature range"):
        TemperatureRange(lower_k=0.0, upper_k=300.0)
