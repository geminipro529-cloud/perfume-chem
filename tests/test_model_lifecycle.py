from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from engine.physics.model_lifecycle import (
    ModelDriftObservation,
    ModelDriftState,
    ModelLifecycleCard,
    ModelLifecycleState,
    assess_model_drift,
)


def _card(state: ModelLifecycleState = ModelLifecycleState.ACTIVE) -> ModelLifecycleCard:
    return ModelLifecycleCard(
        model_id="OV-04",
        version="2.0.0",
        release_sha256="a" * 64,
        calibration_scope="INDIVIDUAL_BLOTTER_20PCT_DAY14",
        calibration_data_ids=("CAL-1", "CAL-2"),
        held_out_data_ids=("HOLD-1", "HOLD-2"),
        endpoint_ids=("C0-03",),
        abstention_rule="Abstain outside exact scope.",
        drift_tolerance=Decimal("0.75"),
        minimum_n=3,
        drift_action="Hold and recalibrate.",
        supersession_rule="New release requires a bound comparison.",
        retirement_rule="Retire after confirmed scope-breaking drift.",
        evidence_ceiling="CALIBRATED_SCREENING",
        claim_scopes=("INDIVIDUAL",),
        known_failure_modes=("matrix shift",),
        lifecycle_state=state,
        retirement_reason="scope closed" if state is ModelLifecycleState.RETIRED else None,
    )


def _observations(error: str) -> tuple[ModelDriftObservation, ...]:
    delta = Decimal(error)
    return tuple(
        ModelDriftObservation(
            observation_id=f"OBS-{index}",
            observed=Decimal(index) + delta,
            predicted=Decimal(index),
            evidence_sha256=f"{index + 1:x}" * 64,
        )
        for index in range(1, 4)
    )


def test_active_model_within_tolerance_can_compute_but_has_no_release_authority() -> None:
    result = assess_model_drift(
        _card(),
        _observations("0.2"),
        calibration_scope="INDIVIDUAL_BLOTTER_20PCT_DAY14",
    )
    assert result.state is ModelDriftState.WITHIN_DECLARED_TOLERANCE
    assert result.computation_allowed is True
    assert result.automatic_threshold_rewrite is False
    assert result.release_authority is False


def test_drift_alert_holds_computation_without_rewriting_threshold() -> None:
    result = assess_model_drift(
        _card(),
        _observations("1.0"),
        calibration_scope="INDIVIDUAL_BLOTTER_20PCT_DAY14",
    )
    assert result.state is ModelDriftState.DRIFT_ALERT
    assert result.computation_allowed is False
    assert result.blockers == ("Hold and recalibrate.",)


def test_retired_lifecycle_is_closed_even_when_numbers_fit() -> None:
    result = assess_model_drift(
        _card(ModelLifecycleState.RETIRED),
        _observations("0.1"),
        calibration_scope="INDIVIDUAL_BLOTTER_20PCT_DAY14",
    )
    assert result.state is ModelDriftState.LIFECYCLE_CLOSED
    assert result.computation_allowed is False


def test_calibration_and_held_out_ids_cannot_overlap() -> None:
    with pytest.raises(ValueError, match="overlap"):
        replace(_card(), held_out_data_ids=("CAL-1", "HOLD-2"))
