from __future__ import annotations

from dataclasses import replace

import pytest

from engine.hedonic_evidence import (
    HedonicEvidenceRequest,
    HedonicEvidenceState,
    HedonicScope,
    bind_preference_fit_evidence,
    evaluate_hedonic_evidence,
)
from engine.preference import (
    PairwisePreference,
    PreferenceFitRequest,
    PreferenceFitStatus,
    fit_preference_model,
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
        _comparison("h1", "p3", "A", "B", winners[0], first="A"),
        _comparison("h2", "p3", "A", "C", winners[1], first="C"),
        _comparison("h3", "p3", "B", "C", winners[2], first="B"),
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


def test_validated_liking_fit_is_exact_scope_only() -> None:
    receipt = _receipt()
    result = evaluate_hedonic_evidence(_request(fit_receipt=receipt))
    assert result.state is HedonicEvidenceState.VALIDATED_EXACT_SCOPE
    assert result.utility_intervals == receipt.fit_result.utility_intervals
    assert result.tie_rate == 1 / 7
    assert result.scope is HedonicScope.TRAINED_PANEL
    assert result.universal_preference_authority is False
    assert result.release_authority is False


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
