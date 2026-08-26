from __future__ import annotations

import hashlib
import json
from pathlib import Path

from engine.evidence.augmentation import EvidenceAugmentationState
from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.hedonic_evidence import (
    HedonicEvidenceRequest,
    HedonicScope,
    bind_preference_fit_evidence,
    bind_preference_fit_evidence_v2,
    evaluate_hedonic_augmentation,
    evaluate_hedonic_evidence,
)
from engine.preference import (
    PairwisePreference,
    PreferenceFitRequest,
    fit_preference_model,
)
from engine.preference_davidson import DavidsonFitConfig, fit_davidson
from engine.preference_validation import (
    ClusterBootstrapConfig,
    HeldoutValidationConfig,
    NextPairConstraints,
    PreferenceDiagnosticsConfig,
    TransitivityConfig,
)
from engine.sensory.ledger import (
    ObservationCellKey,
    SensoryProtocolScope,
    SensorySafetyEvent,
    TemporalEvidenceRequest,
    TemporalObservationCell,
    audit_temporal_evidence,
)
from engine.sensory.order_balance import generate_williams_schedule

ROOT = Path(__file__).resolve().parents[2]
RECOVERY = (
    ROOT
    / "data"
    / "benchmarks"
    / "solforge"
    / "evidence_foundation_recovery_v1"
)
MANIFEST = RECOVERY / "manifest.json"
SIDECAR = RECOVERY / "manifest.sha256"
FORMULA_SHA = "a" * 64
PROTOCOL_SHA = "b" * 64
SCHEDULE_SHA = "c" * 64
SAMPLE_HASHES = ("d" * 64, "e" * 64, "f" * 64)


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_and_sidecar_bind_all_provider_free_components() -> None:
    payload = _manifest()
    observed = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()

    assert payload["schema_version"] == "evidence_foundation_recovery_v1"
    assert SIDECAR.read_text(encoding="ascii") == f"{observed}  manifest.json\n"
    for binding in payload["component_bindings"]:
        path = ROOT / binding["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding["sha256"]
    assert set(payload["authority"].values()) == {False}


def _sensory_scope(*, within_sniff: bool = False):
    schedule = generate_williams_schedule(("CONTROL", "CANDIDATE"))
    scope = SensoryProtocolScope(
        protocol_id="falsification-temporal-v1",
        sample_ids=("CONTROL", "CANDIDATE"),
        assessor_ids=("p1",),
        repeat_ids=("r1",),
        timepoints_seconds=(0.0, 300.0),
        endpoint_ids=("DEPTH",),
        schedule_sha256=schedule.schedule_sha256,
        within_sniff=within_sniff,
        within_sniff_apparatus_qualified=False,
        within_sniff_timing_protocol_qualified=False,
    )
    return scope, schedule


def _sensory_cell(
    sample: str,
    timepoint: float,
    value: float,
    *,
    suffix: str = "",
) -> TemporalObservationCell:
    return TemporalObservationCell(
        key=ObservationCellKey(
            protocol_id="falsification-temporal-v1",
            sample_id=sample,
            assessor_id="p1",
            repeat_id="r1",
            time_seconds=timepoint,
            endpoint_id="DEPTH",
        ),
        observation_id=f"obs-{sample}-{timepoint:g}{suffix}",
        value=value,
        presentation_sequence_id="sequence-1",
        presentation_position=1 if sample == "CONTROL" else 2,
    )


def test_temporal_critical_cases_have_zero_false_promotions() -> None:
    scope, schedule = _sensory_scope()
    complete = (
        _sensory_cell("CONTROL", 0, 2.0),
        _sensory_cell("CONTROL", 300, 2.0),
        _sensory_cell("CANDIDATE", 0, 3.0),
        _sensory_cell("CANDIDATE", 300, 3.0),
    )
    missing = audit_temporal_evidence(
        TemporalEvidenceRequest(scope=scope, schedule=schedule, cells=complete[:1])
    )
    duplicate = audit_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=complete
            + (_sensory_cell("CONTROL", 0, 5.0, suffix="-duplicate"),),
        )
    )
    unsafe = audit_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=complete,
            safety_events=(
                SensorySafetyEvent(
                    event_id="event-1",
                    protocol_id=scope.protocol_id,
                    assessor_id="p1",
                    sample_id="CANDIDATE",
                    time_seconds=30,
                    event_code="HEADACHE",
                    note="Immediate headache.",
                ),
            ),
        )
    )
    within_scope, within_schedule = _sensory_scope(within_sniff=True)
    unqualified = audit_temporal_evidence(
        TemporalEvidenceRequest(
            scope=within_scope,
            schedule=within_schedule,
            cells=(),
        )
    )

    for audit in (missing, duplicate, unsafe, unqualified):
        assert audit.receipt.state is EvidenceAugmentationState.HOLD
        assert audit.receipt.delta is None
        assert set(audit.receipt.authority.values()) == {False}
    assert missing.next_discriminator is not None
    assert duplicate.excluded_duplicate_row_count == 2


def _comparison(
    comparison_id: str,
    assessor: str,
    left: str,
    right: str,
    preferred: str | None,
    *,
    first: str,
    partition: str = "TRAINING",
    previous: str | None = None,
    position: int = 1,
) -> PairwisePreference:
    return PairwisePreference(
        left,
        right,
        preferred,
        comparison_id=comparison_id,
        assessor_id=assessor,
        protocol_id="falsification-liking-v1",
        criterion_id="LIKING",
        time_seconds=300,
        first_presented_item=first,
        session_id=f"session-{assessor}",
        matrix_id="matrix-1",
        time_window_id="heart",
        previous_presented_item=previous,
        position_in_session=position,
        protocol_sha256=PROTOCOL_SHA,
        sample_sha256=SAMPLE_HASHES[0],
        partition=partition,
    )


def _training() -> tuple[PairwisePreference, ...]:
    return (
        _comparison("t1", "p1", "A", "B", "A", first="A"),
        _comparison("t2", "p1", "A", "C", "A", first="C"),
        _comparison("t3", "p1", "B", "C", "B", first="B"),
        _comparison("t4", "p2", "A", "B", "A", first="B"),
        _comparison("t5", "p2", "A", "C", "A", first="A"),
        _comparison("t6", "p2", "B", "C", "B", first="C"),
        _comparison("t7", "p2", "A", "B", None, first="A"),
    )


def _heldout(*, opposite: bool = False) -> tuple[PairwisePreference, ...]:
    winners = ("B", "C", "C") if opposite else ("A", "A", "B")
    return tuple(
        _comparison(
            f"h{index}",
            "p3",
            left,
            right,
            preferred,
            first=first,
            partition="HELDOUT",
        )
        for index, (left, right, preferred, first) in enumerate(
            (
                ("A", "B", winners[0], "A"),
                ("A", "C", winners[1], "C"),
                ("B", "C", winners[2], "B"),
            ),
            start=1,
        )
    )


def _hedonic_augmentation(
    *,
    training: tuple[PairwisePreference, ...] | None = None,
    heldout: tuple[PairwisePreference, ...] | None = None,
    diagnostics_config: PreferenceDiagnosticsConfig | None = None,
):
    training = training or _training()
    heldout = heldout or _heldout()
    fit_request = PreferenceFitRequest(
        training=training,
        heldout=heldout,
        minimum_comparisons=6,
        minimum_heldout_comparisons=3,
        declared_baseline_accuracy=0.5,
        criterion_id="LIKING",
        bootstrap_replicates=10,
        bootstrap_seed=17,
        require_scoped_validation=True,
    )
    fit_result = fit_preference_model(fit_request)
    assessor_ids = tuple(
        sorted({row.assessor_id for row in training + heldout if row.assessor_id})
    )
    parent = bind_preference_fit_evidence(
        fit_request,
        fit_result,
        scope=HedonicScope.TRAINED_PANEL,
        formula_build_sha256=FORMULA_SHA,
        sample_sha256=SAMPLE_HASHES,
        protocol_sha256=PROTOCOL_SHA,
        assessor_ids=assessor_ids,
        repeat_ids=("r1",),
        comparison_repeat_ids={
            row.comparison_id or "": "r1" for row in training + heldout
        },
        time_seconds=300,
        schedule_sha256=SCHEDULE_SHA,
    )
    fitted = fit_davidson(
        items=("A", "B", "C"),
        comparisons=training,
        config=DavidsonFitConfig(regularization=0.1, maximum_iterations=400),
    )
    receipt = bind_preference_fit_evidence_v2(
        parent,
        davidson_fit=fitted,
        construct_registry_sha256="1" * 64,
        criterion_wording_sha256="2" * 64,
        source_transfer_sha256="3" * 64,
        source_transfer_state="NARROWER_SCOPE",
        bootstrap_config=ClusterBootstrapConfig(replicates=20, seed=17),
        heldout_config=HeldoutValidationConfig(
            split_unit="ASSESSOR",
            practical_margin=0.0,
            bootstrap_replicates=20,
            seed=17,
        ),
        transitivity_config=TransitivityConfig(),
        eligible_next_pairs=(("A", "B"), ("A", "C"), ("B", "C")),
        next_pair_constraints=NextPairConstraints(decision_resolved=True),
        diagnostics_config=diagnostics_config or PreferenceDiagnosticsConfig(),
    )
    request = HedonicEvidenceRequest(
        criterion_id="LIKING",
        scope=receipt.scope,
        formula_build_sha256=receipt.formula_build_sha256,
        sample_sha256=receipt.sample_sha256,
        protocol_sha256=receipt.protocol_sha256,
        assessor_ids=receipt.assessor_ids,
        repeat_ids=receipt.repeat_ids,
        time_seconds=receipt.time_seconds,
        schedule_sha256=receipt.schedule_sha256,
        fit_receipt=receipt,
    )
    result = evaluate_hedonic_evidence(request)
    input_sha256 = sha256_hex(
        canonical_json_bytes(
            {"fit_receipt_sha256": receipt.record_sha256, "criterion": "LIKING"}
        )
    )
    return result, evaluate_hedonic_augmentation(
        request=request,
        result=result,
        input_sha256=input_sha256,
        policy_sha256="4" * 64,
        exact_scope="falsification/LIKING",
        source_binding_sha256=(receipt.record_sha256,),
    )


def test_hedonic_baseline_and_order_failures_have_zero_false_promotions() -> None:
    baseline_result, baseline_augmentation = _hedonic_augmentation(
        heldout=_heldout(opposite=True),
        diagnostics_config=PreferenceDiagnosticsConfig(maximum_order_effect=1.0),
    )
    order_rows = (
        _comparison("o1", "p1", "A", "B", "A", first="A"),
        _comparison("o2", "p2", "A", "B", "A", first="A"),
        _comparison("o3", "p3", "A", "B", "B", first="B"),
        _comparison("o4", "p4", "A", "B", "B", first="B"),
        _comparison("o5", "p1", "A", "C", "A", first="A"),
        _comparison("o6", "p2", "B", "C", "B", first="B"),
    )
    order_result, order_augmentation = _hedonic_augmentation(
        training=order_rows,
    )

    assert baseline_result.state.value == "FAILED_HELDOUT_BASELINE"
    assert order_result.state.value != "VALIDATED_EXACT_SCOPE"
    for receipt in (baseline_augmentation, order_augmentation):
        assert receipt.state is EvidenceAugmentationState.HOLD
        assert receipt.delta is None
        assert set(receipt.authority.values()) == {False}


def test_already_resolved_valid_hedonic_question_is_silent() -> None:
    result, augmentation = _hedonic_augmentation()

    assert result.state.value == "VALIDATED_EXACT_SCOPE"
    assert augmentation.state is EvidenceAugmentationState.NO_AUGMENTATION
    assert augmentation.reason_codes == ("DECLARED_DECISION_ALREADY_RESOLVED",)
    assert augmentation.delta is None


def test_manifest_declares_every_required_adversarial_stratum() -> None:
    strata = _manifest()["required_falsifications"]

    assert {
        "stock_strength_substitution",
        "active_dose_rebase",
        "unit_mismatch",
        "matrix_mismatch",
        "threshold_cancellation",
        "missing_timepoint",
        "duplicate_timepoint",
        "measured_modeled_mixture",
        "interval_inversion",
        "natural_constituent_ambiguity",
        "context_hash_drift",
        "null_change",
    }.issubset(strata["oav"])
    assert {
        "missing_cell",
        "discordant_duplicate",
        "order_carryover",
        "unsafe_exposure",
        "unqualified_within_sniff",
        "assessor_disagreement",
        "temporal_crossover",
        "no_transition",
        "resolved_next_discriminator",
    }.issubset(strata["temporal"])
    assert {
        "disconnected_graph",
        "cluster_row_reversal",
        "order_bias",
        "carryover",
        "repeated_exposure",
        "subgroup_reversal",
        "criterion_leakage",
        "train_test_leakage",
        "null_winner",
        "calibration_failure",
        "baseline_failure",
        "deterministic_next_pair",
    }.issubset(strata["preference"])
