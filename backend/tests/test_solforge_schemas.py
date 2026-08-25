from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.lab import (
    ExperimentCreate,
    ObservationCreate,
    PairwiseComparisonCreate,
)
from app.schemas.solforge import (
    SolForgeComparisonContextV1,
    SolForgeObservationContextV1,
    SolForgeProtocolContextV1,
)

H = "a" * 64


def _protocol() -> dict:
    return {
        "schema_version": "solforge_protocol_context_v1",
        "compiled_experiment_sha256": H,
        "schedule_sha256": "b" * 64,
        "arm_ids": ["CONTROL", "TREATMENT"],
        "criterion_ids": ["DEPTH"],
        "test_only": True,
    }


def _observation() -> dict:
    return {
        "schema_version": "solforge_observation_context_v1",
        "compiled_experiment_sha256": H,
        "schedule_sha256": "b" * 64,
        "sample_id": "CONTROL",
        "sample_sha256": "c" * 64,
        "assessor_id": "ASSESSOR-1",
        "repeat_index": 1,
        "timepoint_seconds": 0.0,
        "endpoint": "DEPTH",
        "presentation_sequence": 1,
        "test_only": True,
    }


def _comparison() -> dict:
    return {
        "schema_version": "solforge_comparison_context_v1",
        "compiled_experiment_sha256": H,
        "schedule_sha256": "b" * 64,
        "criterion": "DEPTH",
        "assessor_id": "ASSESSOR-1",
        "repeat_index": 1,
        "timepoint_seconds": 0.0,
        "left_sample_id": "CONTROL",
        "right_sample_id": "TREATMENT",
        "first_presented_item": "CONTROL",
        "test_only": True,
    }


def test_closed_solforge_contexts_validate() -> None:
    assert SolForgeProtocolContextV1.model_validate(_protocol()).arm_ids == (
        "CONTROL", "TREATMENT"
    )
    assert SolForgeObservationContextV1.model_validate(_observation()).repeat_index == 1
    assert SolForgeComparisonContextV1.model_validate(_comparison()).criterion == "DEPTH"


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (SolForgeProtocolContextV1, {**_protocol(), "schema_version": "future"}),
        (SolForgeObservationContextV1, {**_observation(), "extra": True}),
        (SolForgeComparisonContextV1, {**_comparison(), "first_presented_item": "OTHER"}),
    ],
)
def test_contexts_reject_unknown_versions_fields_and_positions(model, payload) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_existing_lab_dict_fields_validate_solforge_when_present() -> None:
    experiment = ExperimentCreate(
        name="shadow", protocol={"solforge": _protocol()}, status="planned"
    )
    observation = ObservationCreate(
        elapsed_seconds=0, observations={"value": None, "solforge": _observation()}
    )
    comparison = PairwiseComparisonCreate(
        experiment_id="EXP", left_sample_id="CONTROL", right_sample_id="TREATMENT",
        context={"solforge": _comparison()},
    )
    assert experiment.protocol["solforge"]["schema_version"] == "solforge_protocol_context_v1"
    assert observation.observations["solforge"]["sample_id"] == "CONTROL"
    assert comparison.context["solforge"]["first_presented_item"] == "CONTROL"


def test_legacy_unrelated_context_dictionaries_remain_accepted() -> None:
    assert ExperimentCreate(name="legacy", protocol={"free": "form"}).protocol == {
        "free": "form"
    }


def test_lab_schema_rejects_invalid_nested_solforge_context() -> None:
    with pytest.raises(ValidationError):
        ObservationCreate(
            elapsed_seconds=0,
            observations={"solforge": {**_observation(), "sample_sha256": "bad"}},
        )
