from __future__ import annotations

from engine.evidence.augmentation import (
    EvidenceAugmentationState,
    EvidenceDeltaReceiptV1,
)
from engine.sensory.ledger import (
    AssessorReliabilityState,
    ObservationCellKey,
    SensoryProtocolScope,
    SensorySafetyEvent,
    TemporalEvidenceDisposition,
    TemporalEvidenceRequest,
    TemporalEvidenceState,
    TemporalObservationCell,
    analyze_temporal_evidence,
    audit_temporal_evidence,
)
from engine.sensory.order_balance import PresentationSchedule, generate_williams_schedule


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


def test_preregistered_repeat_cells_remain_missing_without_interpolation() -> None:
    schedule = generate_williams_schedule(("CONTROL", "TREATMENT"))
    scope = SensoryProtocolScope(
        protocol_id="protocol-preregistered-v2",
        sample_ids=("CONTROL", "TREATMENT"),
        assessor_ids=("OWNER-1",),
        repeat_ids=("R1", "R2"),
        timepoints_seconds=(0.0, 3600.0),
        endpoint_ids=("DEPTH", "RICHNESS"),
        schedule_sha256=schedule.schedule_sha256,
    )

    result = analyze_temporal_evidence(
        TemporalEvidenceRequest(scope=scope, schedule=schedule, cells=())
    )

    assert result.state is TemporalEvidenceState.INCOMPLETE
    assert result.expected_cell_count == 16
    assert result.observed_cell_count == 0
    assert len(result.missing_cells) == 16
    assert result.interpolated_cell_count == 0
