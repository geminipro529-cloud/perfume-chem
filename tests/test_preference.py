from dataclasses import fields

from engine.preference import (
    PairwisePreference,
    PreferenceFitRequest,
    PreferenceFitStatus,
    fit_preference_model,
)


def test_directional_fit_contract_excludes_composition_and_marketing_features():
    field_names = {
        field.name
        for contract in (PairwisePreference, PreferenceFitRequest)
        for field in fields(contract)
    }

    assert field_names.isdisjoint(
        {
            "oav",
            "formula",
            "formula_composition",
            "luxury",
            "brand",
            "price",
            "perfume_identity",
        }
    )


def _comparison(left: str, right: str, winner: str) -> PairwisePreference:
    return PairwisePreference(left_item=left, right_item=right, preferred_item=winner)


def test_preference_fit_is_withheld_until_data_and_connectivity_gates_pass():
    insufficient = fit_preference_model(
        PreferenceFitRequest(
            training=(_comparison("A", "B", "A"),),
            minimum_comparisons=3,
        )
    )
    disconnected = fit_preference_model(
        PreferenceFitRequest(
            training=(
                _comparison("A", "B", "A"),
                _comparison("A", "B", "A"),
                _comparison("C", "D", "C"),
                _comparison("C", "D", "C"),
            ),
            minimum_comparisons=4,
        )
    )

    assert insufficient.status is PreferenceFitStatus.WITHHELD
    assert "minimum comparisons" in insufficient.gate_failures[0]
    assert insufficient.utilities == {}
    assert disconnected.status is PreferenceFitStatus.WITHHELD
    assert "connected" in disconnected.gate_failures[0]


def test_connected_bradley_terry_fit_is_diagnostic_without_heldout_validation():
    result = fit_preference_model(
        PreferenceFitRequest(
            training=(
                _comparison("A", "B", "A"),
                _comparison("A", "B", "A"),
                _comparison("A", "C", "A"),
                _comparison("B", "C", "B"),
                _comparison("B", "C", "B"),
            ),
            minimum_comparisons=5,
        )
    )

    assert result.status is PreferenceFitStatus.DIAGNOSTIC
    assert result.validated is False
    assert result.utilities["A"] > result.utilities["B"] > result.utilities["C"]
    assert result.regularization == 0.1
    assert result.evidence.classification.value == "UNKNOWN"


def test_preference_fit_is_validated_only_after_beating_declared_heldout_baseline():
    result = fit_preference_model(
        PreferenceFitRequest(
            training=(
                _comparison("A", "B", "A"),
                _comparison("A", "C", "A"),
                _comparison("B", "C", "B"),
                _comparison("A", "B", "A"),
                _comparison("B", "C", "B"),
            ),
            heldout=(
                _comparison("A", "C", "A"),
                _comparison("A", "B", "A"),
                _comparison("B", "C", "B"),
            ),
            minimum_comparisons=5,
            minimum_heldout_comparisons=3,
            declared_baseline_accuracy=0.50,
        )
    )

    assert result.status is PreferenceFitStatus.VALIDATED
    assert result.validated is True
    assert result.heldout_accuracy == 1.0
    assert result.baseline_accuracy == 0.5
    assert result.evidence.classification.value == "EMPIRICALLY_CALIBRATED"
