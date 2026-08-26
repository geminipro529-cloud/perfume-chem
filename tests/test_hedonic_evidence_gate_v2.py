from __future__ import annotations

from dataclasses import replace

import pytest

from engine.evidence.augmentation import EvidenceAugmentationState
from engine.hedonic_evidence import (
    HedonicEvidenceRequest,
    HedonicEvidenceState,
    HedonicScope,
    bind_preference_fit_evidence,
    bind_preference_fit_evidence_v2,
    evaluate_hedonic_augmentation,
    evaluate_hedonic_evidence,
)
from engine.preference import (
    PairwisePreference,
    PreferenceFitRequest,
    PreferenceFitStatus,
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

FORMULA_SHA = "a" * 64
PROTOCOL_SHA = "b" * 64
SCHEDULE_SHA = "c" * 64
SAMPLE_HASHES = ("d" * 64, "e" * 64, "f" * 64)


def _comparison(
    comparison_id: str,
    assessor_id: str,
    left: str,
    right: str,
    preferred: str | None,
    *,
    first: str,
    criterion: str = "LIKING",
    partition: str = "TRAINING",
) -> PairwisePreference:
    return PairwisePreference(
        left,
        right,
        preferred,
        comparison_id=comparison_id,
        assessor_id=assessor_id,
        protocol_id="protocol-liking-v1",
        criterion_id=criterion,
        time_seconds=300,
        first_presented_item=first,
        session_id=f"session-{assessor_id}",
        matrix_id="matrix-liking-v2",
        time_window_id="heart",
        position_in_session=1,
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
    return (
        _comparison("h1", "p3", "A", "B", winners[0], first="A", partition="HELDOUT"),
        _comparison("h2", "p3", "A", "C", winners[1], first="C", partition="HELDOUT"),
        _comparison("h3", "p3", "B", "C", winners[2], first="B", partition="HELDOUT"),
    )


def _fit_request(
    *,
    heldout: bool = True,
    opposite_heldout: bool = False,
    criterion: str = "LIKING",
    minimum_comparisons: int = 6,
    require_scoped_validation: bool = True,
) -> PreferenceFitRequest:
    training = tuple(
        replace(item, criterion_id=criterion) for item in _training()
    )
    heldout_rows = (
        tuple(
            replace(item, criterion_id=criterion)
            for item in _heldout(opposite=opposite_heldout)
        )
        if heldout
        else ()
    )
    return PreferenceFitRequest(
        training=training,
        heldout=heldout_rows,
        minimum_comparisons=minimum_comparisons,
        minimum_heldout_comparisons=3,
        declared_baseline_accuracy=0.5 if heldout else None,
        criterion_id=criterion,
        bootstrap_replicates=10,
        bootstrap_seed=17,
        require_scoped_validation=require_scoped_validation,
    )


def _repeat_bindings(request: PreferenceFitRequest) -> dict[str, str]:
    return {
        comparison.comparison_id or f"unscoped-{index}": "repeat-1"
        for index, comparison in enumerate(request.training + request.heldout)
    }


def _receipt(
    request: PreferenceFitRequest | None = None,
):
    fit_request = request or _fit_request()
    result = fit_preference_model(fit_request)
    assessor_ids = tuple(
        sorted(
            {
                comparison.assessor_id
                for comparison in fit_request.training + fit_request.heldout
                if comparison.assessor_id is not None
            }
        )
    )
    return bind_preference_fit_evidence(
        fit_request,
        result,
        scope=HedonicScope.TRAINED_PANEL,
        formula_build_sha256=FORMULA_SHA,
        sample_sha256=SAMPLE_HASHES,
        protocol_sha256=PROTOCOL_SHA,
        assessor_ids=assessor_ids,
        repeat_ids=("repeat-1",),
        comparison_repeat_ids=_repeat_bindings(fit_request),
        time_seconds=300,
        schedule_sha256=SCHEDULE_SHA,
    )


def _receipt_v2(
    request: PreferenceFitRequest | None = None,
    *,
    diagnostics: bool = True,
    diagnostics_config: PreferenceDiagnosticsConfig | None = None,
    next_pair_constraints: NextPairConstraints | None = None,
):
    parent = _receipt(request)
    fit_request = parent.fit_request
    items = tuple(
        sorted(
            {row.left_item for row in fit_request.training}
            | {row.right_item for row in fit_request.training}
        )
    )
    davidson = fit_davidson(
        items=items,
        comparisons=fit_request.training,
        config=DavidsonFitConfig(
            regularization=fit_request.regularization,
            maximum_iterations=fit_request.maximum_iterations,
        ),
    )
    return bind_preference_fit_evidence_v2(
        parent,
        davidson_fit=davidson,
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
        next_pair_constraints=(
            next_pair_constraints
            if next_pair_constraints is not None
            else NextPairConstraints(decision_resolved=True)
        ),
        diagnostics_config=(
            diagnostics_config or PreferenceDiagnosticsConfig()
            if diagnostics
            else None
        ),
    )


def _request(*, fit_receipt=None, **overrides: object) -> HedonicEvidenceRequest:
    payload: dict[str, object] = {
        "criterion_id": "LIKING",
        "scope": HedonicScope.TRAINED_PANEL,
        "formula_build_sha256": FORMULA_SHA,
        "sample_sha256": SAMPLE_HASHES,
        "protocol_sha256": PROTOCOL_SHA,
        "assessor_ids": ("p1", "p2", "p3"),
        "repeat_ids": ("repeat-1",),
        "time_seconds": 300,
        "schedule_sha256": SCHEDULE_SHA,
        "fit_receipt": fit_receipt,
    }
    payload.update(overrides)
    return HedonicEvidenceRequest(**payload)  # type: ignore[arg-type]


def test_missing_liking_evidence_is_not_tested_without_default_score() -> None:
    result = evaluate_hedonic_evidence(_request(fit_receipt=None))
    assert result.state is HedonicEvidenceState.NOT_TESTED
    assert result.utility_intervals == {}
    assert result.tie_rate is None
    assert not hasattr(result, "score")
    assert not hasattr(result, "beauty")


def test_only_liking_is_accepted_as_hedonic_evidence() -> None:
    richness = _receipt(_fit_request(criterion="RICHNESS"))
    result = evaluate_hedonic_evidence(
        _request(fit_receipt=richness, criterion_id="RICHNESS")
    )
    assert result.state is HedonicEvidenceState.INVALID_OR_CONFOUNDED
    assert "LIKING" in result.blockers[0]


def test_withheld_fit_is_insufficient_evidence() -> None:
    fit_request = _fit_request(minimum_comparisons=20)
    receipt = _receipt(fit_request)
    assert receipt.fit_result.status is PreferenceFitStatus.WITHHELD
    result = evaluate_hedonic_evidence(_request(fit_receipt=receipt))
    assert result.state is HedonicEvidenceState.INSUFFICIENT_EVIDENCE
    assert result.utility_intervals == {}


def test_exact_scope_fit_without_heldout_validation_is_diagnostic() -> None:
    receipt = _receipt(_fit_request(heldout=False))
    assert receipt.fit_result.status is PreferenceFitStatus.DIAGNOSTIC
    result = evaluate_hedonic_evidence(
        _request(
            fit_receipt=receipt,
            assessor_ids=("p1", "p2"),
        )
    )
    assert result.state is HedonicEvidenceState.DIAGNOSTIC
    assert result.utility_intervals


def test_heldout_baseline_failure_has_a_distinct_state() -> None:
    receipt = _receipt(_fit_request(opposite_heldout=True))
    assert receipt.fit_result.status is PreferenceFitStatus.DIAGNOSTIC
    assert any("baseline" in note for note in receipt.fit_result.validation_notes)
    result = evaluate_hedonic_evidence(_request(fit_receipt=receipt))
    assert result.state is HedonicEvidenceState.FAILED_HELDOUT_BASELINE


def test_accuracy_only_v1_fit_cannot_validate_liking() -> None:
    receipt = _receipt()
    result = evaluate_hedonic_evidence(_request(fit_receipt=receipt))
    assert result.state is HedonicEvidenceState.FAILED_HELDOUT_BASELINE
    assert "PROPER_SCORING_REQUIRED" in result.blockers


def test_validated_v2_liking_fit_is_exact_scope_only() -> None:
    receipt = _receipt_v2()
    result = evaluate_hedonic_evidence(_request(fit_receipt=receipt))
    assert result.state is HedonicEvidenceState.VALIDATED_EXACT_SCOPE
    assert result.utility_intervals == receipt.cluster_bootstrap.utility_intervals
    assert result.tie_rate == 1 / 7
    assert result.scope is HedonicScope.TRAINED_PANEL
    assert result.universal_preference_authority is False
    assert result.release_authority is False


def test_v2_diagnostics_are_required_for_validation() -> None:
    receipt = _receipt_v2(diagnostics=False)
    result = evaluate_hedonic_evidence(_request(fit_receipt=receipt))

    assert result.state is HedonicEvidenceState.INVALID_OR_CONFOUNDED
    assert "PREFERENCE_DIAGNOSTICS_REQUIRED" in result.blockers


def test_owner_scope_cannot_claim_a_multi_assessor_population() -> None:
    receipt = _receipt_v2()
    owner_receipt = replace(
        receipt,
        parent_v1=replace(receipt.parent_v1, scope=HedonicScope.OWNER),
    )
    result = evaluate_hedonic_evidence(
        _request(
            fit_receipt=owner_receipt,
            scope=HedonicScope.OWNER,
        )
    )

    assert result.state is HedonicEvidenceState.INVALID_OR_CONFOUNDED
    assert "OWNER_SCOPE_REQUIRES_ONE_ASSESSOR" in result.blockers


def _augmentation(receipt):
    request = _request(fit_receipt=receipt)
    result = evaluate_hedonic_evidence(request)
    return evaluate_hedonic_augmentation(
        request=request,
        result=result,
        input_sha256="7" * 64,
        policy_sha256="8" * 64,
        exact_scope="formula/LIKING",
        source_binding_sha256=(receipt.record_sha256,),
    )


def test_plain_counting_resolution_has_no_model_augmentation_value() -> None:
    receipt = _receipt_v2(
        diagnostics_config=PreferenceDiagnosticsConfig(
            counting_resolution_margin=0.5
        )
    )
    assert receipt.diagnostics is not None
    assert receipt.diagnostics.counting_winner == "A"

    augmentation = _augmentation(receipt)

    assert augmentation.state is EvidenceAugmentationState.NO_AUGMENTATION
    assert augmentation.reason_codes == ("PLAIN_COUNTING_RESOLVED",)


def test_declared_resolved_decision_has_no_model_augmentation_value() -> None:
    augmentation = _augmentation(_receipt_v2())

    assert augmentation.state is EvidenceAugmentationState.NO_AUGMENTATION
    assert augmentation.reason_codes == ("DECLARED_DECISION_ALREADY_RESOLVED",)


def test_validated_model_can_select_one_next_comparison() -> None:
    receipt = _receipt_v2(
        next_pair_constraints=NextPairConstraints(decision_resolved=False)
    )
    assert receipt.next_pair.selected_pair is not None

    augmentation = _augmentation(receipt)

    assert augmentation.state is EvidenceAugmentationState.AUGMENT
    assert augmentation.next_action == "COMPARE:" + ":".join(
        receipt.next_pair.selected_pair
    )


def test_no_admissible_pair_and_no_interval_winner_has_no_augmentation() -> None:
    receipt = _receipt_v2(
        next_pair_constraints=NextPairConstraints(
            maximum_exposure=1,
            exposure_counts=(("A", 1), ("B", 1), ("C", 1)),
        )
    )
    overlapping = replace(
        receipt,
        cluster_bootstrap=replace(
            receipt.cluster_bootstrap,
            utility_intervals={item: (-1.0, 1.0) for item in ("A", "B", "C")},
        ),
    )

    augmentation = _augmentation(overlapping)

    assert overlapping.next_pair.reason_code == "NO_ELIGIBLE_PAIR"
    assert augmentation.state is EvidenceAugmentationState.NO_AUGMENTATION
    assert augmentation.reason_codes == ("NO_ADMISSIBLE_NEXT_PAIR",)


def test_baseline_failure_holds_augmentation() -> None:
    augmentation = _augmentation(
        _receipt_v2(
            _fit_request(opposite_heldout=True),
            diagnostics_config=PreferenceDiagnosticsConfig(
                maximum_order_effect=1.0
            ),
        )
    )

    assert augmentation.state is EvidenceAugmentationState.HOLD
    assert "FAILED_HELDOUT_BASELINE" in augmentation.reason_codes


def test_augmentation_rejects_a_result_from_another_scope() -> None:
    receipt = _receipt_v2(
        next_pair_constraints=NextPairConstraints(decision_resolved=False)
    )
    request = _request(fit_receipt=receipt)
    result = replace(
        evaluate_hedonic_evidence(request),
        formula_build_sha256="9" * 64,
    )

    augmentation = evaluate_hedonic_augmentation(
        request=request,
        result=result,
        input_sha256="7" * 64,
        policy_sha256="8" * 64,
        exact_scope="formula/LIKING",
        source_binding_sha256=(receipt.record_sha256,),
    )

    assert augmentation.state is EvidenceAugmentationState.HOLD
    assert augmentation.reason_codes == ("RESULT_SCOPE_MISMATCH",)


def test_v2_failed_lower_bound_and_unstable_bootstrap_do_not_promote() -> None:
    failed_baseline = _receipt_v2(
        _fit_request(opposite_heldout=True),
        diagnostics_config=PreferenceDiagnosticsConfig(
            maximum_order_effect=1.0
        ),
    )
    baseline_result = evaluate_hedonic_evidence(
        _request(fit_receipt=failed_baseline)
    )
    unstable = replace(
        _receipt_v2(),
        cluster_bootstrap=replace(_receipt_v2().cluster_bootstrap, stable=False),
    )
    unstable_result = evaluate_hedonic_evidence(_request(fit_receipt=unstable))

    assert baseline_result.state is HedonicEvidenceState.FAILED_HELDOUT_BASELINE
    assert unstable_result.state is HedonicEvidenceState.INSUFFICIENT_EVIDENCE


def test_v2_temporal_crossover_and_failed_source_transfer_do_not_promote() -> None:
    receipt = _receipt_v2()
    crossover = replace(
        receipt,
        transitivity=replace(
            receipt.transitivity,
            state="TEMPORAL_CROSSOVER",
            temporal_crossovers=(("A", "B"),),
            global_winner_withheld=True,
        ),
    )
    source_failed = replace(receipt, source_transfer_state="FAILED")

    crossover_result = evaluate_hedonic_evidence(_request(fit_receipt=crossover))
    source_result = evaluate_hedonic_evidence(_request(fit_receipt=source_failed))

    assert crossover_result.state is HedonicEvidenceState.DIAGNOSTIC
    assert source_result.state is HedonicEvidenceState.INVALID_OR_CONFOUNDED
    assert "SOURCE_TRANSFER_INVALID" in source_result.blockers


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("formula_build_sha256", "1" * 64),
        ("sample_sha256", ("2" * 64, "3" * 64, "4" * 64)),
        ("protocol_sha256", "5" * 64),
        ("assessor_ids", ("p1", "p2")),
        ("repeat_ids", ("repeat-2",)),
        ("time_seconds", 600),
        ("schedule_sha256", "6" * 64),
        ("scope", HedonicScope.CONSUMER_POPULATION),
    ],
)
def test_scope_mismatch_invalidates_an_otherwise_valid_fit(
    field_name: str,
    replacement: object,
) -> None:
    result = evaluate_hedonic_evidence(
        _request(fit_receipt=_receipt(), **{field_name: replacement})
    )
    assert result.state is HedonicEvidenceState.INVALID_OR_CONFOUNDED
    assert any(field_name in blocker for blocker in result.blockers)


def test_safety_event_prevents_hedonic_validation() -> None:
    result = evaluate_hedonic_evidence(
        _request(fit_receipt=_receipt(), safety_event_ids=("event-1",))
    )
    assert result.state is HedonicEvidenceState.INVALID_OR_CONFOUNDED
    assert "safety" in result.blockers[0]


def test_order_effect_over_declared_limit_is_confounded() -> None:
    training = (
        _comparison("o1", "p1", "A", "B", "A", first="A"),
        _comparison("o2", "p2", "A", "B", "B", first="B"),
        _comparison("o3", "p1", "A", "C", "A", first="A"),
        _comparison("o4", "p2", "A", "C", "C", first="C"),
        _comparison("o5", "p1", "B", "C", "B", first="B"),
        _comparison("o6", "p2", "B", "C", "C", first="C"),
    )
    fit_request = PreferenceFitRequest(
        training=training,
        minimum_comparisons=6,
        criterion_id="LIKING",
        require_scoped_validation=True,
    )
    fit_result = fit_preference_model(fit_request)
    assert fit_result.order_effect == 0.5
    receipt = bind_preference_fit_evidence(
        fit_request,
        fit_result,
        scope=HedonicScope.TRAINED_PANEL,
        formula_build_sha256=FORMULA_SHA,
        sample_sha256=SAMPLE_HASHES,
        protocol_sha256=PROTOCOL_SHA,
        assessor_ids=("p1", "p2"),
        repeat_ids=("repeat-1",),
        comparison_repeat_ids=_repeat_bindings(fit_request),
        time_seconds=300,
        schedule_sha256=SCHEDULE_SHA,
    )
    result = evaluate_hedonic_evidence(
        _request(fit_receipt=receipt, assessor_ids=("p1", "p2"))
    )
    assert result.state is HedonicEvidenceState.INVALID_OR_CONFOUNDED
    assert any("order effect" in blocker for blocker in result.blockers)


def test_binding_rejects_a_result_from_a_different_fit_configuration() -> None:
    fit_request = _fit_request()
    different = fit_preference_model(replace(fit_request, bootstrap_seed=99))
    with pytest.raises(ValueError, match="fit result does not match"):
        bind_preference_fit_evidence(
            fit_request,
            different,
            scope=HedonicScope.TRAINED_PANEL,
            formula_build_sha256=FORMULA_SHA,
            sample_sha256=SAMPLE_HASHES,
            protocol_sha256=PROTOCOL_SHA,
            assessor_ids=("p1", "p2", "p3"),
            repeat_ids=("repeat-1",),
            comparison_repeat_ids=_repeat_bindings(fit_request),
            time_seconds=300,
            schedule_sha256=SCHEDULE_SHA,
        )


def test_ties_are_retained_as_indifference_evidence() -> None:
    receipt = _receipt()
    assert receipt.fit_result.comparison_count == 6
    assert receipt.fit_result.tie_rate == 1 / 7
    payload = evaluate_hedonic_evidence(
        _request(fit_receipt=receipt)
    ).as_dict()
    assert payload["tie_rate"] == 1 / 7
    assert payload["directional_comparison_count"] == 6


def test_receipt_hash_is_deterministic_and_binds_comparison_repeats() -> None:
    first = _receipt()
    second = _receipt()
    assert first.record_sha256 == second.record_sha256
    assert first.comparison_repeats_sha256 == second.comparison_repeats_sha256
    with pytest.raises(ValueError, match="comparison_repeat_ids"):
        bind_preference_fit_evidence(
            _fit_request(),
            fit_preference_model(_fit_request()),
            scope=HedonicScope.TRAINED_PANEL,
            formula_build_sha256=FORMULA_SHA,
            sample_sha256=SAMPLE_HASHES,
            protocol_sha256=PROTOCOL_SHA,
            assessor_ids=("p1", "p2", "p3"),
            repeat_ids=("repeat-1",),
            comparison_repeat_ids={"t1": "repeat-1"},
            time_seconds=300,
            schedule_sha256=SCHEDULE_SHA,
        )
