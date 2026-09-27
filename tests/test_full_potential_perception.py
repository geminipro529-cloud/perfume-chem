"""Checkpoint 15 endpoint separation and concentration-aware baselines."""

from __future__ import annotations

import pytest

from engine.preference import PairwisePreference
from engine.research.perception import (
    CharacterComponentV1,
    compute_detection_diagnostic,
    linear_intensity_weighted_character,
    unavailable_hedonic_endpoints,
)
from engine.research.preference import (
    DavidsonFitConfigV1,
    fit_davidson_personal_preference,
)


def _oav(**changes):
    values = {
        "material_id": "limonene",
        "delivered_gas_ug_l": 2.0,
        "threshold_gas_ug_l": 0.5,
        "concentration_identity_id": "cas:138-86-3",
        "threshold_identity_id": "cas:138-86-3",
        "concentration_phase": "AIR",
        "threshold_phase": "AIR",
        "concentration_unit": "ug/L_air",
        "threshold_unit": "ug/L_air",
        "concentration_protocol_id": "gas-threshold-protocol",
        "threshold_protocol_id": "gas-threshold-protocol",
        "concentration_temperature_k": 298.15,
        "threshold_temperature_k": 298.15,
    }
    values.update(changes)
    return compute_detection_diagnostic(**values)


def test_oav_requires_compatible_delivered_gas_identity_units_and_protocol() -> None:
    result = _oav()
    assert result["oav"] == 4.0
    assert result["optimizer_selection_usable"] is False
    assert result["intensity_authorized"] is False
    for changes, reason in (
        ({"threshold_identity_id": "different"}, "IDENTITY_MISMATCH"),
        ({"threshold_unit": "ppm_liquid"}, "UNIT_MISMATCH"),
        ({"threshold_protocol_id": "other"}, "PROTOCOL_MISMATCH"),
        ({"threshold_gas_ug_l": None}, "COMPATIBLE_GAS_THRESHOLD_UNAVAILABLE"),
    ):
        held = _oav(**changes)
        assert held["oav"] is None
        assert reason in held["reason_codes"]


def test_missing_odt_does_not_create_neutral_intensity_or_pleasantness() -> None:
    result = _oav(threshold_gas_ug_l=None)
    assert result["oav"] is None
    assert result["intensity_authorized"] is False
    hedonic = unavailable_hedonic_endpoints()
    assert hedonic["population_pleasantness"] is None
    assert hedonic["personal_liking"] is None
    assert hedonic["neutral_midpoint_imputed"] is False


def test_linear_character_baseline_is_intensity_weighted_not_hedonic() -> None:
    result = linear_intensity_weighted_character(
        (
            CharacterComponentV1("a", True, 3.0, {"lavender": 1.0, "amber": 0.0}),
            CharacterComponentV1("b", True, 1.0, {"lavender": 0.0, "amber": 1.0}),
        )
    )
    assert result["descriptor_profile"] == {"amber": 0.25, "lavender": 0.75}
    assert result["pleasantness"] is None
    assert result["liking"] is None
    assert result["beauty"] is None


def test_missing_character_component_withholds_or_returns_explicit_partial() -> None:
    rows = (
        CharacterComponentV1("a", True, 3.0, {"lavender": 1.0}),
        CharacterComponentV1("missing", True, None, None),
    )
    withheld = linear_intensity_weighted_character(rows)
    assert withheld["descriptor_profile"] is None
    assert withheld["validation_state"] == "WITHHOLD_UNKNOWN"
    partial = linear_intensity_weighted_character(rows, incomplete_policy="PARTIAL")
    assert partial["descriptor_profile"] == {"lavender": 1.0}
    assert partial["applicability_state"] == "PARTIAL"
    assert partial["positive_dose_coverage"] == 0.5


def _comparison(
    session: int, index: int, left: str, right: str, preferred: str | None
) -> PairwisePreference:
    return PairwisePreference(
        left,
        right,
        preferred,
        comparison_id=f"session-{session}:{index}",
        assessor_id="one-user",
        protocol_id="blind-paired-liking-v1",
        criterion_id="personal-liking",
        time_seconds=1800.0,
        first_presented_item=left,
    )


def test_davidson_model_preserves_ties_and_personal_scope() -> None:
    rows = []
    for session in (1, 2, 3):
        rows.extend(
            (
                _comparison(session, 1, "A", "B", "A"),
                _comparison(session, 2, "A", "C", None),
                _comparison(session, 3, "B", "C", "C"),
                _comparison(session, 4, "A", "B", None),
            )
        )
    result = fit_davidson_personal_preference(
        rows,
        criterion_id="personal-liking",
        config=DavidsonFitConfigV1(
            bootstrap_replicates=20,
            maximum_iterations=1000,
        ),
    )
    assert result["status"] == "DIAGNOSTIC_PERSONAL_EVIDENCE"
    assert result["tie_rate"] == pytest.approx(0.5)
    assert result["tie_parameter"] > 0
    assert set(result["utilities"]) == {"A", "B", "C"}
    assert result["population_claim_authorized"] is False
    assert result["formula_action"] == "NO_CHANGE"


def test_personal_model_withholds_insufficient_sessions_and_disconnected_graph() -> None:
    rows = (
        _comparison(1, 1, "A", "B", "A"),
        _comparison(1, 2, "C", "D", "C"),
    )
    result = fit_davidson_personal_preference(
        rows,
        criterion_id="personal-liking",
        config=DavidsonFitConfigV1(minimum_comparisons=2, minimum_sessions=3),
    )
    assert result["status"] == "WITHHELD"
    assert "MINIMUM_SESSIONS_NOT_MET" in result["reason_codes"]
    assert "COMPARISON_GRAPH_DISCONNECTED" in result["reason_codes"]
