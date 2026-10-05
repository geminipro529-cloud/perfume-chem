"""Checkpoint 16 planning-only measurement and sensory contracts."""

from __future__ import annotations

from dataclasses import replace

import pytest

from engine.research.protocols import (
    InstrumentalObservationContractV1,
    build_personal_sensory_protocol,
    build_reference_anchored_protocol,
)


def test_personal_paired_protocol_is_blinded_complete_and_not_authorized() -> None:
    candidates = {"R5": "1" * 64, "R6": "2" * 64, "NEW": "3" * 64}
    plan, blinding = build_personal_sensory_protocol(
        candidates,
        protocol_id="lavender-ambrox-personal-liking-v1",
        kind="PAIRED_LIKING",
        session_ids=("session-1", "session-2", "session-3"),
        seed=17,
    )
    assert plan["pair_coverage_complete"] is True
    assert plan["timepoints_seconds"] == [300, 1800, 7200, 14400]
    assert len(plan["schedule"]) == 9
    assert all(row["allow_tie"] for row in plan["schedule"])
    assert plan["physical_execution_authorized"] is False
    assert plan["compounding_authority"] is False
    public = blinding.public_manifest()
    assert "R5" not in str(public["sessions"])
    with pytest.raises(PermissionError, match="SEALED"):
        blinding.reveal_session("session-1")


def test_blinding_can_be_recovered_only_after_that_session_closes() -> None:
    _plan, blinding = build_personal_sensory_protocol(
        {"A": "a" * 64, "B": "b" * 64},
        protocol_id="paired-v1",
        kind="PAIRED_INTENSITY",
        session_ids=("s1", "s2", "s3"),
        seed=91,
    )
    closed = replace(blinding, closed_sessions=("s1",))
    assert set(closed.reveal_session("s1").values()) == {"A", "B"}
    with pytest.raises(PermissionError):
        closed.reveal_session("s2")


def test_protocol_refuses_too_few_sessions_or_nonstandard_timepoints() -> None:
    candidates = {"A": "a" * 64, "B": "b" * 64}
    with pytest.raises(ValueError, match="three"):
        build_personal_sensory_protocol(
            candidates,
            protocol_id="paired-v1",
            kind="PAIRED_LIKING",
            session_ids=("s1", "s2"),
            seed=1,
        )
    with pytest.raises(ValueError, match="fixed"):
        build_personal_sensory_protocol(
            candidates,
            protocol_id="paired-v1",
            kind="PAIRED_LIKING",
            session_ids=("s1", "s2", "s3"),
            seed=1,
            timepoints_seconds=(300, 1800),
        )


def test_instrumental_contract_binds_raw_and_processed_bytes_without_admission() -> None:
    record = InstrumentalObservationContractV1(
        observation_id="obs-1",
        formula_sha256="1" * 64,
        inventory_sha256="2" * 64,
        stock_lot_sha256="3" * 64,
        release_scenario_sha256="4" * 64,
        preparation_receipt_sha256="5" * 64,
        deposit_decimal="10",
        deposit_unit="mg",
        matrix_id="ethanol-water-80-20",
        substrate_id="controlled-glass",
        temperature_k_decimal="298.15",
        relative_humidity_decimal="0.5",
        airflow_m_s_decimal="0.1",
        surface_area_m2_decimal="0.0001",
        sampling_geometry_id="sealed-cell-v1",
        sampling_method_id="spme-gcms-v1",
        instrument_id="instrument-1",
        calibration_receipt_sha256="6" * 64,
        blank_receipt_sha256="7" * 64,
        timepoints_seconds=(0, 300, 1800, 7200, 14400),
        replicate_id="replicate-1",
        session_id="session-1",
        raw_data_sha256="8" * 64,
        processed_result_sha256="9" * 64,
    ).as_dict()
    assert record["observation_admitted"] is False
    assert record["release_authority"] is False
    assert record["safety_authority"] is False


def test_quick_reference_protocol_is_target_anchored_and_lightweight() -> None:
    plan, blinding = build_reference_anchored_protocol(
        {"target": "1" * 64, "libre": "2" * 64, "carbon": "3" * 64},
        target_candidate_id="target",
        protocol_id="quick-reference-v1",
        mode="QUICK_REFERENCE",
        session_ids=("s1",),
        seed=17,
        requested_descriptors=("clear lavender",),
    )
    assert plan["timepoints_seconds"] == [300, 7200]
    assert len(plan["schedule"]) == 2
    assert plan["reference_reference_comparisons_required"] is False
    assert plan["result_scope"] == "QUICK_PERSONAL_OBSERVATION"
    assert all(row["short_reason_required"] for row in plan["schedule"])
    public = blinding.public_manifest()
    assert public["mapping_withheld_until_session_close"] is True
    assert set(public["sessions"]["s1"]).isdisjoint({"target", "libre", "carbon"})


def test_controlled_reference_protocol_balances_order_and_keeps_endpoints_separate() -> None:
    plan, _blinding = build_reference_anchored_protocol(
        {"target": "1" * 64, "reference": "2" * 64},
        target_candidate_id="target",
        protocol_id="controlled-reference-v1",
        mode="CONTROLLED_REFERENCE",
        session_ids=("s1", "s2", "s3"),
        seed=22,
        requested_descriptors=("lavender clarity",),
        preserve_constraints=("dry amber",),
        avoid_constraints=("added sweetness",),
    )
    assert plan["timepoints_seconds"] == [300, 1800, 7200, 14400]
    assert len(plan["schedule"]) == 3
    assert plan["presentation_order_balanced"] is True
    assert plan["evaluation_endpoints"] == {
        "requested_descriptors": ["lavender clarity"],
        "preserve_constraints": ["dry amber"],
        "avoid_constraints": ["added sweetness"],
        "fixed": ["INTENSITY", "FAMILIARITY", "OVERALL_LIKING"],
    }
    assert plan["population_generalization_authorized"] is False
