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
