from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from engine.scientific_validation.complexity_model_admission import OAVGateBinding
from engine.sensory.temporal_observations import (
    TemporalObservation,
    TemporalObservationSeries,
    TemporalSummaryState,
    summarize_temporal_observations,
)

FORMULA_SHA = "a" * 64


def _binding(*, composite: str = "PASS") -> OAVGateBinding:
    return OAVGateBinding(
        formula_sha256=FORMULA_SHA,
        dose_receipt_sha256="b" * 64,
        oav_result_sha256="c" * 64,
        quantitative_ppm_status="PASS",
        odt_authority_status="PASS",
        odt_coverage_status="PASS",
        natural_composite_coverage_status=composite,
        headspace_scope_status="PASS",
        receipt_binding_status="BOUND_GATE_RECEIPT",
        strict_oav_status="ABSTAINED",
        pre_mix_gate_status="PASS",
        planned_active_equivalence_status="NOT_APPLICABLE_NEW_FORMULA",
        formula_is_revision=False,
    )


def _observation(index: int, value: str, dominant: str) -> TemporalObservation:
    return TemporalObservation(
        observation_id=f"OBS-{index}",
        dimension="iris",
        timepoint=f"T{index}",
        time_numeric=Decimal(index),
        value=Decimal(value),
        dominant_system=dominant,
        evidence_sha256=f"{index + 1:x}" * 64,
    )


def _series() -> TemporalObservationSeries:
    return TemporalObservationSeries(
        series_id="TS-01",
        formula_sha256=FORMULA_SHA,
        time_unit="minutes",
        observations=(
            _observation(0, "1", "A"),
            _observation(1, "3", "B"),
            _observation(2, "2", "A"),
        ),
        oav_binding=_binding(),
    )


def test_temporal_summary_is_descriptive_and_detects_recurrence() -> None:
    result = summarize_temporal_observations(_series(), dimension="iris")
    assert result.state is TemporalSummaryState.DESCRIPTIVE_ONLY
    assert result.peak_timepoint == "T1"
    assert result.recurrence_events == ({"system": "A", "at": "T2"},)
    assert result.inferential_authority is False
    assert result.release_authority is False


def test_temporal_summary_fails_closed_on_oav_gate() -> None:
    result = summarize_temporal_observations(
        replace(_series(), oav_binding=_binding(composite="FAIL")),
        dimension="iris",
    )
    assert result.state is TemporalSummaryState.REBUILD
    assert any("natural_composite" in item for item in result.blockers)


def test_temporal_series_rejects_formula_oav_mismatch() -> None:
    with pytest.raises(ValueError, match="formula hash"):
        replace(_series(), formula_sha256="d" * 64)
