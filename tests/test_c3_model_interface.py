from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from engine.physics.matrix_environment import (
    ApplicationEnvironmentKind,
    MatrixStage,
)
from engine.physics.model_interface import (
    ApplicabilityDomain,
    ApplicabilityState,
    DomainRange,
    ModelAvailability,
    ModelEvidenceClass,
    ModelFamily,
    ModelInterfaceContractError,
    ModelOperation,
    ModelRelease,
    ModelResultStatus,
    ModelSelector,
)
from engine.physics.properties import CanonicalScope, ThermophysicalProperty

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
