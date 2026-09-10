from __future__ import annotations

from dataclasses import replace

import pytest

from engine.evidence.augmentation import (
    EvidenceAugmentationState,
    EvidenceDeltaReceiptV1,
)
from engine.sensory.ledger import (
    AssessorReliabilityState,
    ObservationCellKey,
    RealizedOrderState,
    RealizedPresentationAssignment,
    SensoryProtocolScope,
    SensorySafetyEvent,
    TemporalAnalysisPlanV3,
    TemporalContrastDirection,
    TemporalContrastOutcome,
    TemporalContrastSpecV3,
    TemporalEvidenceDisposition,
    TemporalEvidenceRequest,
    TemporalEvidenceRequestV3,
    TemporalEvidenceState,
    TemporalMeasurementMode,
    TemporalObservationCell,
    analyze_temporal_evidence,
    analyze_temporal_evidence_v3,
    audit_temporal_evidence,
)
from engine.sensory.order_balance import (
    OrderBalanceState,
    PresentationSchedule,
    generate_williams_schedule,
)


def _scope(
    *,
    within_sniff: bool = False,
    apparatus_qualified: bool = False,
    timing_protocol_qualified: bool = False,
):
    schedule = generate_williams_schedule(("sample-a", "sample-b"))
    return (
        SensoryProtocolScope(
            protocol_id="protocol-depth-v1",
            sample_ids=("sample-a", "sample-b"),
            assessor_ids=("assessor-1",),
            repeat_ids=("repeat-1",),
            timepoints_seconds=(0.0, 300.0),
            endpoint_ids=("depth",),
            schedule_sha256=schedule.schedule_sha256,
            within_sniff=within_sniff,
            within_sniff_apparatus_qualified=apparatus_qualified,
            within_sniff_timing_protocol_qualified=timing_protocol_qualified,
        ),
        schedule,
    )


def _cell(sample_id: str, time_seconds: float, value: float, *, suffix: str = ""):
    return TemporalObservationCell(
        key=ObservationCellKey(
            protocol_id="protocol-depth-v1",
            sample_id=sample_id,
            assessor_id="assessor-1",
            repeat_id="repeat-1",
            time_seconds=time_seconds,
            endpoint_id="depth",
        ),
        observation_id=f"obs-{sample_id}-{time_seconds:g}{suffix}",
        value=value,
        presentation_sequence_id="sequence-1",
        presentation_position=1 if sample_id == "sample-a" else 2,
    )


def test_complete_balanced_grid_summarizes_observed_cells_and_transitions() -> None:
    scope, schedule = _scope()
    result = analyze_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=(
                _cell("sample-a", 0, 2.0),
                _cell("sample-a", 300, 4.0),
                _cell("sample-b", 0, 3.0),
                _cell("sample-b", 300, 3.5),
            ),
        )
    )

    assert result.state is TemporalEvidenceState.COMPLETE
    assert result.expected_cell_count == 4
    assert result.observed_cell_count == 4
    assert result.missing_cells == ()
    assert result.duplicate_cells == ()
    assert [summary.median for summary in result.summaries] == [2.0, 4.0, 3.0, 3.5]
    assert [transition.median_delta for transition in result.transitions] == [2.0, 0.5]
    assert result.interpolated_cell_count == 0
    assert result.physical_execution_authorized is False
    assert result.sensory_authority is False
    assert result.release_authority is False


def test_missing_cells_remain_missing_and_name_the_next_collection() -> None:
    scope, schedule = _scope()
    result = analyze_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=(_cell("sample-a", 0, 2.0),),
        )
    )

    assert result.state is TemporalEvidenceState.INCOMPLETE
    assert len(result.missing_cells) == 3
    assert result.interpolated_cell_count == 0
    assert "Collect missing cell" in (result.next_discriminator or "")


def test_duplicate_canonical_cell_holds_even_when_the_grid_is_otherwise_complete() -> None:
    scope, schedule = _scope()
    duplicate = _cell("sample-a", 0, 2.5, suffix="-duplicate")
    result = analyze_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=(
                _cell("sample-a", 0, 2.0),
                duplicate,
                _cell("sample-a", 300, 4.0),
                _cell("sample-b", 0, 3.0),
                _cell("sample-b", 300, 3.5),
            ),
        )
    )

    assert result.state is TemporalEvidenceState.HOLD
    assert result.duplicate_cells == (duplicate.key,)
    assert any("duplicate canonical" in blocker for blocker in result.blockers)


def test_unbalanced_order_and_unqualified_within_sniff_data_hold() -> None:
    unbalanced = PresentationSchedule(
        labels=("sample-a", "sample-b"),
        sequences=(
            ("sample-a", "sample-b"),
            ("sample-a", "sample-b"),
            ("sample-a", "sample-b"),
            ("sample-b", "sample-a"),
        ),
    )
    scope, _ = _scope(within_sniff=True, apparatus_qualified=False)
    scope = SensoryProtocolScope(
        protocol_id=scope.protocol_id,
        sample_ids=scope.sample_ids,
        assessor_ids=scope.assessor_ids,
        repeat_ids=scope.repeat_ids,
        timepoints_seconds=scope.timepoints_seconds,
        endpoint_ids=scope.endpoint_ids,
        schedule_sha256=unbalanced.schedule_sha256,
        within_sniff=True,
        within_sniff_apparatus_qualified=False,
        within_sniff_timing_protocol_qualified=False,
    )
    result = analyze_temporal_evidence(
        TemporalEvidenceRequest(scope=scope, schedule=unbalanced, cells=())
    )

    assert result.state is TemporalEvidenceState.HOLD
    assert any("first-position" in blocker for blocker in result.blockers)
    assert any("qualified timing apparatus" in blocker for blocker in result.blockers)


def test_within_sniff_requires_both_apparatus_and_timing_protocol_qualification() -> None:
    scope, schedule = _scope(
        within_sniff=True,
        apparatus_qualified=True,
        timing_protocol_qualified=False,
    )

    result = analyze_temporal_evidence(
        TemporalEvidenceRequest(scope=scope, schedule=schedule, cells=())
    )

    assert result.state is TemporalEvidenceState.HOLD
    assert any("timing protocol" in blocker for blocker in result.blockers)


def test_disagreement_selects_a_deterministic_next_discriminator() -> None:
    schedule = generate_williams_schedule(("sample-a", "sample-b"))
    scope = SensoryProtocolScope(
        protocol_id="protocol-depth-v1",
        sample_ids=("sample-a", "sample-b"),
        assessor_ids=("assessor-1", "assessor-2"),
        repeat_ids=("repeat-1",),
        timepoints_seconds=(0.0,),
        endpoint_ids=("depth",),
        schedule_sha256=schedule.schedule_sha256,
    )

    def assessor_cell(sample: str, assessor: str, value: float) -> TemporalObservationCell:
        return TemporalObservationCell(
            key=ObservationCellKey(
                protocol_id=scope.protocol_id,
                sample_id=sample,
                assessor_id=assessor,
                repeat_id="repeat-1",
                time_seconds=0,
                endpoint_id="depth",
            ),
            observation_id=f"obs-{sample}-{assessor}",
            value=value,
            presentation_sequence_id="sequence-1",
            presentation_position=1 if sample == "sample-a" else 2,
        )

    request = TemporalEvidenceRequest(
        scope=scope,
        schedule=schedule,
        cells=(
            assessor_cell("sample-a", "assessor-1", 1.0),
            assessor_cell("sample-a", "assessor-2", 5.0),
            assessor_cell("sample-b", "assessor-1", 3.0),
            assessor_cell("sample-b", "assessor-2", 3.5),
        ),
    )

    first = analyze_temporal_evidence(request)
    second = analyze_temporal_evidence(request)

    assert first.next_discriminator == second.next_discriminator
    assert first.next_discriminator == (
        "Repeat sample-a depth at 0s to resolve assessor disagreement."
    )


def test_temporal_cell_round_trips_through_existing_context_json_shape() -> None:
    original = _cell("sample-a", 300, 4.25)

    restored = TemporalObservationCell.from_dict(original.as_dict())

    assert restored == original


def test_adverse_sensory_event_triggers_a_fail_closed_protocol_stop() -> None:
    scope, schedule = _scope()
    event = SensorySafetyEvent(
        event_id="safety-1",
        protocol_id=scope.protocol_id,
        assessor_id="assessor-1",
        sample_id="sample-a",
        time_seconds=45.0,
        event_code="HEADACHE",
        note="Assessor reported an immediate headache.",
    )

    result = analyze_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=(
                _cell("sample-a", 0, 2.0),
                _cell("sample-a", 300, 4.0),
                _cell("sample-b", 0, 3.0),
                _cell("sample-b", 300, 3.5),
            ),
            safety_events=(event,),
        )
    )

    assert result.state is TemporalEvidenceState.HOLD
    assert result.safety_stop_triggered is True
    assert result.safety_events == (event,)
    assert any("HEADACHE" in blocker for blocker in result.blockers)
    assert SensorySafetyEvent.from_dict(event.as_dict()) == event


def test_declared_repeatability_gate_holds_unreliable_assessor_evidence() -> None:
    schedule = generate_williams_schedule(("sample-a", "sample-b"))
    scope = SensoryProtocolScope(
        protocol_id="protocol-repeatability-v1",
        sample_ids=("sample-a", "sample-b"),
        assessor_ids=("assessor-1",),
        repeat_ids=("repeat-1", "repeat-2"),
        timepoints_seconds=(0.0,),
        endpoint_ids=("depth",),
        schedule_sha256=schedule.schedule_sha256,
        require_repeatability=True,
        maximum_within_assessor_repeat_spread=0.5,
    )

    def repeated_cell(sample: str, repeat: str, value: float) -> TemporalObservationCell:
        return TemporalObservationCell(
            key=ObservationCellKey(
                protocol_id=scope.protocol_id,
                sample_id=sample,
                assessor_id="assessor-1",
                repeat_id=repeat,
                time_seconds=0,
                endpoint_id="depth",
            ),
            observation_id=f"obs-{sample}-{repeat}",
            value=value,
            presentation_sequence_id="sequence-1",
            presentation_position=1 if sample == "sample-a" else 2,
        )

    result = analyze_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=(
                repeated_cell("sample-a", "repeat-1", 2.0),
                repeated_cell("sample-a", "repeat-2", 4.0),
                repeated_cell("sample-b", "repeat-1", 3.0),
                repeated_cell("sample-b", "repeat-2", 3.2),
            ),
        )
    )

    assert result.state is TemporalEvidenceState.HOLD
    assert result.assessor_reliability_state is AssessorReliabilityState.HOLD
    assert result.assessor_reliability[0].assessor_id == "assessor-1"
    assert result.assessor_reliability[0].maximum_repeat_spread == 2.0
    assert any("repeatability threshold" in blocker for blocker in result.blockers)


def test_complete_matched_timepoints_are_resolved_without_new_test() -> None:
    scope, schedule = _scope()
    audit = audit_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=(
                _cell("sample-a", 0, 2.0),
                _cell("sample-a", 300, 4.0),
                _cell("sample-b", 0, 3.0),
                _cell("sample-b", 300, 3.5),
            ),
        )
    )

    assert audit.disposition is TemporalEvidenceDisposition.RESOLVED
    assert audit.receipt.state is EvidenceAugmentationState.AUGMENT
    assert audit.receipt.next_action is None
    assert audit.next_discriminator is None
    assert set(audit.receipt.authority.values()) == {False}


def test_duplicate_cell_audits_provenance_before_remeasurement() -> None:
    scope, schedule = _scope()
    audit = audit_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=(
                _cell("sample-a", 0, 2.0),
                _cell("sample-a", 0, 4.5, suffix="-duplicate"),
                _cell("sample-a", 300, 4.0),
                _cell("sample-b", 0, 3.0),
                _cell("sample-b", 300, 3.5),
            ),
        )
    )

    assert audit.disposition is TemporalEvidenceDisposition.CONFLICTED
    assert audit.receipt.state is EvidenceAugmentationState.HOLD
    assert audit.next_discriminator == (
        "AUDIT_PROVENANCE:protocol/sample/assessor/repeat/timepoint/endpoint"
    )
    assert audit.excluded_duplicate_row_count == 2
    assert not any(
        summary.sample_id == "sample-a" and summary.time_seconds == 0
        for summary in audit.summaries
    )


def test_v2_missing_grid_selects_exactly_one_cell() -> None:
    scope, schedule = _scope()
    audit = audit_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=(_cell("sample-a", 0, 2.0),),
        )
    )

    assert audit.disposition is TemporalEvidenceDisposition.INCOMPLETE
    assert audit.receipt.state is EvidenceAugmentationState.HOLD
    assert audit.next_discriminator is not None
    assert audit.next_discriminator.startswith("COLLECT_CELL:")
    assert audit.next_discriminator.count("COLLECT_CELL:") == 1


def test_v2_disagreement_alone_does_not_force_remeasurement() -> None:
    schedule = generate_williams_schedule(("sample-a", "sample-b"))
    scope = SensoryProtocolScope(
        protocol_id="protocol-depth-v1",
        sample_ids=("sample-a", "sample-b"),
        assessor_ids=("assessor-1", "assessor-2"),
        repeat_ids=("repeat-1",),
        timepoints_seconds=(0.0, 300.0),
        endpoint_ids=("depth",),
        schedule_sha256=schedule.schedule_sha256,
    )

    def observed(sample: str, assessor: str, timepoint: float, value: float):
        return TemporalObservationCell(
            key=ObservationCellKey(
                protocol_id=scope.protocol_id,
                sample_id=sample,
                assessor_id=assessor,
                repeat_id="repeat-1",
                time_seconds=timepoint,
                endpoint_id="depth",
            ),
            observation_id=f"obs-{sample}-{assessor}-{timepoint:g}",
            value=value,
            presentation_sequence_id="sequence-1",
            presentation_position=1 if sample == "sample-a" else 2,
        )

    audit = audit_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=(
                observed("sample-a", "assessor-1", 0, 1.0),
                observed("sample-a", "assessor-2", 0, 5.0),
                observed("sample-a", "assessor-1", 300, 2.0),
                observed("sample-a", "assessor-2", 300, 5.0),
                observed("sample-b", "assessor-1", 0, 3.0),
                observed("sample-b", "assessor-2", 0, 3.5),
                observed("sample-b", "assessor-1", 300, 3.2),
                observed("sample-b", "assessor-2", 300, 3.6),
            ),
        )
    )

    assert audit.disposition is TemporalEvidenceDisposition.RESOLVED
    assert audit.next_discriminator is None


def test_v2_within_sniff_requires_full_apparatus_binding() -> None:
    schedule = generate_williams_schedule(("sample-a", "sample-b"))
    incomplete_scope = SensoryProtocolScope(
        protocol_id="protocol-within-sniff-v2",
        sample_ids=("sample-a", "sample-b"),
        assessor_ids=("assessor-1",),
        repeat_ids=("repeat-1",),
        timepoints_seconds=(0.0, 5.0),
        endpoint_ids=("depth",),
        schedule_sha256=schedule.schedule_sha256,
        within_sniff=True,
        within_sniff_apparatus_qualified=True,
        within_sniff_timing_protocol_qualified=True,
    )
    complete_scope = SensoryProtocolScope(
        protocol_id="protocol-within-sniff-v2",
        sample_ids=("sample-a", "sample-b"),
        assessor_ids=("assessor-1",),
        repeat_ids=("repeat-1",),
        timepoints_seconds=(0.0, 5.0),
        endpoint_ids=("depth",),
        schedule_sha256=schedule.schedule_sha256,
        within_sniff=True,
        within_sniff_apparatus_qualified=True,
        within_sniff_timing_protocol_qualified=True,
        within_sniff_apparatus_id="olfactometer-1",
        within_sniff_clock_source="monotonic-hardware-clock",
        within_sniff_timing_tolerance_ms=20.0,
        within_sniff_qualification_sha256="a" * 64,
    )

    held = audit_temporal_evidence(
        TemporalEvidenceRequest(scope=incomplete_scope, schedule=schedule, cells=())
    )
    admitted_protocol = audit_temporal_evidence(
        TemporalEvidenceRequest(scope=complete_scope, schedule=schedule, cells=())
    )

    assert held.disposition is TemporalEvidenceDisposition.PROTOCOL_HOLD
    assert any("apparatus identity" in blocker for blocker in held.receipt.blockers)
    assert admitted_protocol.disposition is TemporalEvidenceDisposition.INCOMPLETE


def test_v2_one_timepoint_is_insufficient_temporal_scope_and_round_trips() -> None:
    schedule = generate_williams_schedule(("sample-a", "sample-b"))
    scope = SensoryProtocolScope(
        protocol_id="protocol-static-v2",
        sample_ids=("sample-a", "sample-b"),
        assessor_ids=("assessor-1",),
        repeat_ids=("repeat-1",),
        timepoints_seconds=(0.0,),
        endpoint_ids=("depth",),
        schedule_sha256=schedule.schedule_sha256,
    )
    audit = audit_temporal_evidence(
        TemporalEvidenceRequest(scope=scope, schedule=schedule, cells=())
    )

    assert audit.disposition is TemporalEvidenceDisposition.INSUFFICIENT_SCOPE
    assert audit.receipt.state is EvidenceAugmentationState.HOLD
    assert EvidenceDeltaReceiptV1.from_dict(audit.receipt.as_dict()) == audit.receipt


def test_v2_schedule_order_safety_and_repeatability_fail_closed() -> None:
    unbalanced = PresentationSchedule(
        labels=("sample-a", "sample-b"),
        sequences=(("sample-a", "sample-b"), ("sample-a", "sample-b")),
    )
    scope = SensoryProtocolScope(
        protocol_id="protocol-protected-v2",
        sample_ids=("sample-a", "sample-b"),
        assessor_ids=("assessor-1",),
        repeat_ids=("repeat-1", "repeat-2"),
        timepoints_seconds=(0.0, 300.0),
        endpoint_ids=("depth",),
        schedule_sha256="b" * 64,
        require_repeatability=True,
        maximum_within_assessor_repeat_spread=0.5,
    )
    event = SensorySafetyEvent(
        event_id="safety-v2",
        protocol_id=scope.protocol_id,
        assessor_id="assessor-1",
        sample_id="sample-a",
        time_seconds=0,
        event_code="HEADACHE",
        note="stop",
    )

    def repeated_cell(
        sample: str, repeat: str, timepoint: float, value: float
    ) -> TemporalObservationCell:
        return TemporalObservationCell(
            key=ObservationCellKey(
                protocol_id=scope.protocol_id,
                sample_id=sample,
                assessor_id="assessor-1",
                repeat_id=repeat,
                time_seconds=timepoint,
                endpoint_id="depth",
            ),
            observation_id=f"obs-{sample}-{repeat}-{timepoint:g}",
            value=value,
            presentation_sequence_id="sequence-1",
            presentation_position=1 if sample == "sample-a" else 2,
        )

    cells = tuple(
        repeated_cell(
            sample,
            repeat,
            timepoint,
            1.0 if repeat == "repeat-1" else 4.0,
        )
        for sample in scope.sample_ids
        for repeat in scope.repeat_ids
        for timepoint in scope.timepoints_seconds
    )
    audit = audit_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=unbalanced,
            cells=cells,
            safety_events=(event,),
        )
    )

    assert audit.disposition is TemporalEvidenceDisposition.PROTOCOL_HOLD
    assert audit.receipt.state is EvidenceAugmentationState.HOLD
    assert audit.next_discriminator == "CORRECT_PROTOCOL"
    assert any("schedule hash" in blocker for blocker in audit.receipt.blockers)
    assert any("balanced" in blocker for blocker in audit.receipt.blockers)
    assert any("repeatability" in blocker for blocker in audit.receipt.blockers)
    assert any("HEADACHE" in blocker for blocker in audit.receipt.blockers)


def _v3_scope(
    *,
    endpoint_ids: tuple[str, ...] = ("depth",),
) -> tuple[SensoryProtocolScope, PresentationSchedule]:
    schedule = generate_williams_schedule(("sample-a", "sample-b"))
    return (
        SensoryProtocolScope(
            protocol_id="protocol-temporal-v3",
            sample_ids=("sample-a", "sample-b"),
            assessor_ids=("assessor-1", "assessor-2"),
            repeat_ids=("repeat-1",),
            timepoints_seconds=(0.0, 300.0),
            endpoint_ids=endpoint_ids,
            schedule_sha256=schedule.schedule_sha256,
        ),
        schedule,
    )


def _v3_assignments(
    schedule: PresentationSchedule,
) -> tuple[RealizedPresentationAssignment, ...]:
    return (
        RealizedPresentationAssignment(
            assessor_id="assessor-1",
            repeat_id="repeat-1",
            sequence_id="realized-sequence-1",
            ordered_sample_ids=schedule.sequences[0],
        ),
        RealizedPresentationAssignment(
            assessor_id="assessor-2",
            repeat_id="repeat-1",
            sequence_id="realized-sequence-2",
            ordered_sample_ids=schedule.sequences[1],
        ),
    )


def _v3_cells(
    scope: SensoryProtocolScope,
    assignments: tuple[RealizedPresentationAssignment, ...],
    values: dict[tuple[str, str, float, str], float],
) -> tuple[TemporalObservationCell, ...]:
    by_assessor = {item.assessor_id: item for item in assignments}
    cells: list[TemporalObservationCell] = []
    for assessor_id in scope.assessor_ids:
        assignment = by_assessor[assessor_id]
        for sample_id in scope.sample_ids:
            for timepoint in scope.timepoints_seconds:
                for endpoint_id in scope.endpoint_ids:
                    cells.append(
                        TemporalObservationCell(
                            key=ObservationCellKey(
                                protocol_id=scope.protocol_id,
                                sample_id=sample_id,
                                assessor_id=assessor_id,
                                repeat_id="repeat-1",
                                time_seconds=timepoint,
                                endpoint_id=endpoint_id,
                            ),
                            observation_id=(
                                f"obs-{assessor_id}-{sample_id}-{timepoint:g}-"
                                f"{endpoint_id}"
                            ),
                            value=values[(assessor_id, sample_id, timepoint, endpoint_id)],
                            presentation_sequence_id=assignment.sequence_id,
                            presentation_position=(
                                assignment.ordered_sample_ids.index(sample_id) + 1
                            ),
                        )
                    )
    return tuple(cells)


def _v3_plan(
    *,
    mode: TemporalMeasurementMode = TemporalMeasurementMode.DISCRETE_RATING,
    minimum_pairs: int = 2,
    endpoint_id: str = "depth",
) -> TemporalAnalysisPlanV3:
    return TemporalAnalysisPlanV3(
        analysis_id="temporal-depth-decision-v3",
        criterion_id="DEPTH",
        measurement_mode=mode,
        minimum_paired_trajectory_count=minimum_pairs,
        require_realized_order=True,
        require_complete_grid=True,
        contrasts=(
            TemporalContrastSpecV3(
                contrast_id="depth-change-a-vs-b",
                left_sample_id="sample-a",
                right_sample_id="sample-b",
                endpoint_id=endpoint_id,
                from_time_seconds=0.0,
                to_time_seconds=300.0,
                direction=TemporalContrastDirection.LEFT_GREATER,
                minimum_absolute_median_difference_in_change=0.5,
                minimum_directional_agreement_fraction=0.5,
            ),
        ),
        evidence_refs=("MEYNERS-PINEAU-2010", "MACFIE-1989"),
    )


def _v3_rating_values() -> dict[tuple[str, str, float, str], float]:
    return {
        ("assessor-1", "sample-a", 0.0, "depth"): 2.0,
        ("assessor-1", "sample-a", 300.0, "depth"): 5.0,
        ("assessor-1", "sample-b", 0.0, "depth"): 3.0,
        ("assessor-1", "sample-b", 300.0, "depth"): 3.0,
        ("assessor-2", "sample-a", 0.0, "depth"): 3.0,
        ("assessor-2", "sample-a", 300.0, "depth"): 5.0,
        ("assessor-2", "sample-b", 0.0, "depth"): 4.0,
        ("assessor-2", "sample-b", 300.0, "depth"): 4.0,
    }


def _v3_rating_request(
    *,
    assignments: tuple[RealizedPresentationAssignment, ...] | None = None,
    plan: TemporalAnalysisPlanV3 | None = None,
) -> TemporalEvidenceRequestV3:
    scope, schedule = _v3_scope()
    realized = assignments or _v3_assignments(schedule)
    cells = _v3_cells(scope, realized, _v3_rating_values())
    return TemporalEvidenceRequestV3(
        parent=TemporalEvidenceRequest(scope=scope, schedule=schedule, cells=cells),
        analysis_plan=plan or _v3_plan(),
        realized_assignments=realized,
    )


def test_v3_uses_paired_difference_in_change_and_reports_crossover() -> None:
    result = analyze_temporal_evidence_v3(_v3_rating_request())

    assert result.state is TemporalEvidenceState.COMPLETE
    assert result.realized_order_state is RealizedOrderState.PASS
    assert len(result.paired_transitions) == 2
    assert result.paired_transitions[0].paired_count == 2
    contrast = result.contrasts[0]
    assert contrast.outcome is TemporalContrastOutcome.SUPPORTED
    assert contrast.paired_count == 2
    assert contrast.median_difference_in_change == 2.5
    assert contrast.first_quartile == 2.0
    assert contrast.third_quartile == 3.0
    assert contrast.median_absolute_deviation == 0.5
    assert contrast.directional_agreement_fraction == 1.0
    assert contrast.crossover_observed is True
    assert contrast.from_time_median_left_minus_right == -1.0
    assert contrast.to_time_median_left_minus_right == 1.5
    assert result.next_discriminator is None


def test_v3_complete_grid_does_not_fake_resolution_when_pair_scope_is_too_small() -> None:
    result = analyze_temporal_evidence_v3(
        _v3_rating_request(plan=_v3_plan(minimum_pairs=3))
    )

    assert result.state is TemporalEvidenceState.INCOMPLETE
    assert result.contrasts[0].outcome is TemporalContrastOutcome.INCOMPLETE
    assert result.next_discriminator == (
        "EXPAND_PAIRED_TRAJECTORY_SCOPE:depth-change-a-vs-b"
    )
    assert result.receipt.state is EvidenceAugmentationState.HOLD


def test_v3_realized_order_is_observed_not_inferred_from_balanced_design() -> None:
    _, schedule = _v3_scope()
    imbalanced = (
        RealizedPresentationAssignment(
            assessor_id="assessor-1",
            repeat_id="repeat-1",
            sequence_id="same-1",
            ordered_sample_ids=schedule.sequences[0],
        ),
        RealizedPresentationAssignment(
            assessor_id="assessor-2",
            repeat_id="repeat-1",
            sequence_id="same-2",
            ordered_sample_ids=schedule.sequences[0],
        ),
    )

    result = analyze_temporal_evidence_v3(_v3_rating_request(assignments=imbalanced))

    assert result.parent_v2.legacy_result.order_balance_state is (
        OrderBalanceState.PASS_FOR_DESIGN
    )
    assert result.state is TemporalEvidenceState.HOLD
    assert result.realized_order_state is RealizedOrderState.HOLD
    assert "REALIZED_SEQUENCE_COUNTS_UNBALANCED" in result.blockers
    assert result.next_discriminator == "REPAIR_REALIZED_PRESENTATION_ORDER"


def test_v3_cell_position_and_sequence_must_match_realized_assignment() -> None:
    request = _v3_rating_request()
    bad_cell = replace(request.parent.cells[0], presentation_position=2)
    parent = replace(request.parent, cells=(bad_cell, *request.parent.cells[1:]))
    result = analyze_temporal_evidence_v3(replace(request, parent=parent))

    assert result.state is TemporalEvidenceState.HOLD
    assert "OBSERVATION_POSITION_MISMATCH" in result.blockers


def _dynamic_values(
    *,
    both_active: bool,
) -> dict[tuple[str, str, float, str], float]:
    values: dict[tuple[str, str, float, str], float] = {}
    for assessor in ("assessor-1", "assessor-2"):
        for sample in ("sample-a", "sample-b"):
            for timepoint in (0.0, 300.0):
                values[(assessor, sample, timepoint, "woody")] = 1.0
                values[(assessor, sample, timepoint, "floral")] = (
                    1.0 if both_active else 0.0
                )
    return values


def _dynamic_request(mode: TemporalMeasurementMode, *, both_active: bool):
    scope, schedule = _v3_scope(endpoint_ids=("woody", "floral"))
    assignments = _v3_assignments(schedule)
    cells = _v3_cells(scope, assignments, _dynamic_values(both_active=both_active))
    return TemporalEvidenceRequestV3(
        parent=TemporalEvidenceRequest(scope=scope, schedule=schedule, cells=cells),
        analysis_plan=_v3_plan(mode=mode, endpoint_id="woody"),
        realized_assignments=assignments,
    )


def test_v3_tds_requires_exactly_one_dominant_attribute_per_trajectory_cell() -> None:
    valid = analyze_temporal_evidence_v3(
        _dynamic_request(TemporalMeasurementMode.TDS_DOMINANCE, both_active=False)
    )
    invalid = analyze_temporal_evidence_v3(
        _dynamic_request(TemporalMeasurementMode.TDS_DOMINANCE, both_active=True)
    )

    assert valid.state is TemporalEvidenceState.COMPLETE
    assert {item.activation_rate for item in valid.attribute_rates} == {0.0, 1.0}
    assert invalid.state is TemporalEvidenceState.HOLD
    assert "TDS_REQUIRES_EXACTLY_ONE_DOMINANT_ATTRIBUTE" in invalid.blockers


def test_v3_tcata_allows_concurrent_attributes_but_does_not_call_them_dominant() -> None:
    result = analyze_temporal_evidence_v3(
        _dynamic_request(TemporalMeasurementMode.TCATA_ATTRIBUTE, both_active=True)
    )

    assert result.state is TemporalEvidenceState.COMPLETE
    assert all(item.activation_rate == 1.0 for item in result.attribute_rates)
    assert all(item.measurement_mode is TemporalMeasurementMode.TCATA_ATTRIBUTE for item in result.attribute_rates)


def test_v3_duplicate_and_missing_cells_preserve_v2_holds_without_interpolation() -> None:
    complete = _v3_rating_request()
    duplicate_parent = replace(
        complete.parent,
        cells=(complete.parent.cells[0], *complete.parent.cells),
    )
    duplicate = analyze_temporal_evidence_v3(replace(complete, parent=duplicate_parent))
    missing_parent = replace(complete.parent, cells=complete.parent.cells[:-1])
    missing = analyze_temporal_evidence_v3(replace(complete, parent=missing_parent))

    assert duplicate.state is TemporalEvidenceState.HOLD
    assert duplicate.parent_v2.excluded_duplicate_row_count == 2
    assert missing.state is TemporalEvidenceState.INCOMPLETE
    assert missing.parent_v2.missing_cells
    assert missing.interpolated_cell_count == 0


def test_v3_receipt_hashes_all_inputs_and_grants_no_authority() -> None:
    request = _v3_rating_request()
    first = analyze_temporal_evidence_v3(request)
    second = analyze_temporal_evidence_v3(request)

    assert first.request_sha256 == request.record_sha256
    assert first.record_sha256 == second.record_sha256
    assert first.canonical_bytes() == second.canonical_bytes()
    assert set(first.authority_flags.values()) == {False}
    assert set(first.receipt.authority.values()) == {False}
    assert first.interpolated_cell_count == 0


def test_v3_realized_assignment_round_trip_is_strict() -> None:
    _, schedule = _v3_scope()
    assignment = _v3_assignments(schedule)[0]
    assert RealizedPresentationAssignment.from_dict(assignment.as_dict()) == assignment
    bad = assignment.as_dict()
    bad["ordered_sample_ids"] = "sample-a,sample-b"
    with pytest.raises(TypeError, match="ordered_sample_ids"):
        RealizedPresentationAssignment.from_dict(bad)
