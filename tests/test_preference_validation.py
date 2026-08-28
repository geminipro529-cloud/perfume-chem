from __future__ import annotations

import pytest

from engine.preference import PairwisePreference
from engine.preference_davidson import DavidsonFitConfig, fit_davidson
from engine.preference_validation import (
    ClusterBootstrapConfig,
    HeldoutValidationConfig,
    NextPairConstraints,
    OrderCarryoverConfig,
    TransitivityConfig,
    assess_order_and_carryover,
    assess_transitivity,
    cluster_bootstrap,
    select_next_pair,
    validate_heldout,
)


def _row(
    comparison_id: str,
    assessor: str | None,
    left: str,
    right: str,
    preferred: str | None,
    *,
    session: str = "session-1",
    window: str = "heart",
    first: str | None = None,
    previous: str | None = None,
    partition: str = "TRAINING",
) -> PairwisePreference:
    return PairwisePreference(
        left,
        right,
        preferred,
        comparison_id=comparison_id,
        assessor_id=assessor,
        protocol_id="protocol-1",
        criterion_id="LIKING",
        time_seconds=300,
        first_presented_item=first or left,
        session_id=session,
        matrix_id="matrix-1",
        time_window_id=window,
        previous_presented_item=previous,
        position_in_session=1,
        protocol_sha256="a" * 64,
        sample_sha256="b" * 64,
        partition=partition,
    )


def _balanced_rows() -> tuple[PairwisePreference, ...]:
    rows: list[PairwisePreference] = []
    index = 0
    for assessor in ("p1", "p2", "p3"):
        for left, right, outcomes in (
            ("A", "B", ("A", "A", None)),
            ("A", "C", ("A", "A", "C")),
            ("B", "C", ("B", "B", None)),
        ):
            for outcome in outcomes:
                index += 1
                rows.append(
                    _row(
                        f"c{index}",
                        assessor,
                        left,
                        right,
                        outcome,
                        session=f"{assessor}-session",
                        first=left if index % 2 else right,
                    )
                )
    return tuple(rows)


def _fit(rows: tuple[PairwisePreference, ...]):
    items = tuple(sorted({row.left_item for row in rows} | {row.right_item for row in rows}))
    return fit_davidson(
        items=items,
        comparisons=rows,
        config=DavidsonFitConfig(regularization=0.1, maximum_iterations=300),
    )


def test_missing_assessor_ids_never_fall_back_to_row_bootstrap() -> None:
    rows = (_row("c1", None, "A", "B", "A"), _row("c2", "p2", "A", "B", "B"))

    with pytest.raises(ValueError, match="assessor identity"):
        cluster_bootstrap(rows, config=ClusterBootstrapConfig(replicates=10, seed=17))


def test_cluster_bootstrap_is_deterministic_and_records_influence() -> None:
    rows = _balanced_rows()
    config = ClusterBootstrapConfig(replicates=40, seed=17)

    first = cluster_bootstrap(rows, config=config)
    second = cluster_bootstrap(rows, config=config)

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.completed_replicates + first.failed_replicates == 40
    assert first.interval_method == "ASSESSOR_CLUSTER_PERCENTILE"
    assert first.effective_unique_assessors == 3
    assert first.leave_one_assessor_max_shift is not None
    assert set(first.utility_intervals) == {"A", "B", "C"}


def test_boundary_replicates_and_subgroup_reversal_are_not_hidden() -> None:
    rows = (
        _row("p1-1", "p1", "A", "B", "A"),
        _row("p1-2", "p1", "A", "B", "A"),
        _row("p2-1", "p2", "A", "B", "B"),
        _row("p2-2", "p2", "A", "B", "B"),
    )
    receipt = cluster_bootstrap(
        rows,
        config=ClusterBootstrapConfig(
            replicates=20,
            seed=3,
            regularization=0.0,
            maximum_failed_fraction=1.0,
        ),
    )

    assert receipt.boundary_replicates > 0
    assert receipt.subgroup_reversal is True
    assert receipt.stable is False


def test_grouped_heldout_uses_proper_scores_and_lower_bound_margin() -> None:
    training = tuple(
        _row(f"t{i}", "train", "A", "B", "A", session="train-session")
        for i in range(1, 13)
    ) + tuple(
        _row(f"tt{i}", "train", "A", "B", None, session="train-session")
        for i in range(1, 4)
    )
    heldout = tuple(
        _row(
            f"h{i}",
            "heldout",
            "A",
            "B",
            "A",
            session="heldout-session",
            partition="HELDOUT",
        )
        for i in range(1, 9)
    )
    receipt = validate_heldout(
        fitted=_fit(training),
        training=training,
        heldout=heldout,
        config=HeldoutValidationConfig(
            split_unit="ASSESSOR",
            practical_margin=0.01,
            bootstrap_replicates=30,
            seed=9,
        ),
    )

    assert receipt.heldout_count == 8
    assert receipt.multinomial_log_loss < receipt.baseline_log_loss
    assert receipt.brier_score >= 0
    assert receipt.paired_gain_interval[0] > 0.01
    assert receipt.passed is True
    assert receipt.leakage_codes == ()


def test_grouped_leakage_and_frozen_test_training_rows_fail_closed() -> None:
    training = (
        _row("t1", "p1", "A", "B", "A", partition="FROZEN_TEST"),
        _row("t2", "p1", "A", "B", "B"),
        _row("t3", "p1", "A", "B", None),
    )
    heldout = (
        _row("h1", "p1", "A", "B", "A", partition="HELDOUT"),
        _row("h2", "p1", "A", "B", "A", partition="HELDOUT"),
    )
    receipt = validate_heldout(
        fitted=_fit(training),
        training=training,
        heldout=heldout,
        config=HeldoutValidationConfig(split_unit="ASSESSOR"),
    )

    assert "GROUP_SPLIT_LEAKAGE" in receipt.leakage_codes
    assert "FROZEN_TEST_IN_TRAINING" in receipt.leakage_codes
    assert receipt.passed is False


def test_heldout_lower_gain_bound_must_exceed_practical_margin() -> None:
    training = tuple(
        _row(f"t{i}", "train", "A", "B", "A", session="train-session")
        for i in range(1, 9)
    ) + (
        _row("tt1", "train", "A", "B", None, session="train-session"),
    )
    heldout = tuple(
        _row(
            f"h{i}",
            "heldout",
            "A",
            "B",
            "B",
            session="heldout-session",
            partition="HELDOUT",
        )
        for i in range(1, 7)
    )
    receipt = validate_heldout(
        fitted=_fit(training),
        training=training,
        heldout=heldout,
        config=HeldoutValidationConfig(
            practical_margin=0.01,
            bootstrap_replicates=20,
            seed=4,
        ),
    )

    assert receipt.paired_gain_interval[0] < 0.01
    assert receipt.passed is False


def test_transitivity_cycles_and_temporal_crossovers_withhold_global_winner() -> None:
    cycle = (
        _row("c1", "p1", "A", "B", "A"),
        _row("c2", "p2", "B", "C", "B"),
        _row("c3", "p3", "A", "C", "C"),
    )
    crossover = (
        _row("o1", "p1", "A", "B", "A", window="opening"),
        _row("o2", "p2", "A", "B", "A", window="opening"),
        _row("d1", "p1", "A", "B", "B", window="drydown"),
        _row("d2", "p2", "A", "B", "B", window="drydown"),
    )

    cycle_receipt = assess_transitivity(cycle, config=TransitivityConfig())
    crossover_receipt = assess_transitivity(crossover, config=TransitivityConfig())

    assert cycle_receipt.state == "NONTRANSITIVE_OR_MISSPECIFIED"
    assert cycle_receipt.stable_cycles == (("A", "B", "C"),)
    assert cycle_receipt.global_winner_withheld is True
    assert crossover_receipt.temporal_crossovers == (("A", "B"),)
    assert crossover_receipt.global_winner_withheld is True


def test_disconnected_graph_selects_one_lexicographic_best_bridge() -> None:
    fitted = _fit(_balanced_rows())
    receipt = select_next_pair(
        fitted=fitted,
        eligible_pairs=(("A", "C"), ("A", "D"), ("B", "C"), ("B", "D")),
        constraints=NextPairConstraints(
            connected_components=(("A", "B"), ("C", "D")),
        ),
    )

    assert receipt.selected_pair == ("A", "C")
    assert receipt.reason_code == "CONNECTIVITY_FIRST"


def test_next_pair_respects_resolution_exposure_carryover_and_exploration() -> None:
    fitted = _fit(_balanced_rows())
    constrained = select_next_pair(
        fitted=fitted,
        eligible_pairs=(("A", "B"), ("A", "C"), ("B", "C")),
        constraints=NextPairConstraints(
            exposure_counts=(("A", 5), ("B", 1), ("C", 1)),
            maximum_exposure=5,
            forbidden_carryover_pairs=(("B", "C"),),
            exploration_quota_remaining=1,
        ),
    )
    resolved = select_next_pair(
        fitted=fitted,
        eligible_pairs=(("A", "B"),),
        constraints=NextPairConstraints(decision_resolved=True),
    )

    assert constrained.selected_pair is None
    assert constrained.reason_code == "NO_ELIGIBLE_PAIR"
    assert resolved.selected_pair is None
    assert resolved.reason_code == "DECISION_RESOLVED"


def test_exploration_pair_selection_is_deterministic_and_order_aware() -> None:
    fitted = _fit(_balanced_rows())
    first = select_next_pair(
        fitted=fitted,
        eligible_pairs=(("A", "B"), ("A", "C"), ("B", "C")),
        constraints=NextPairConstraints(
            exposure_counts=(("A", 2), ("B", 1), ("C", 1)),
            first_position_counts=(("A", 5), ("B", 2), ("C", 2)),
            pair_observation_counts=(("A", "B", 4), ("A", "C", 1)),
            exploration_quota_remaining=1,
        ),
    )
    second = select_next_pair(
        fitted=fitted,
        eligible_pairs=(("B", "C"), ("A", "C"), ("A", "B")),
        constraints=NextPairConstraints(
            exposure_counts=(("A", 2), ("B", 1), ("C", 1)),
            first_position_counts=(("A", 5), ("B", 2), ("C", 2)),
            pair_observation_counts=(("A", "B", 4), ("A", "C", 1)),
            exploration_quota_remaining=1,
        ),
    )

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.selected_pair is not None
    assert first.reason_code == "EXPLORATION_QUOTA"


def test_realized_sequence_requires_previous_item_sample_and_qualified_control() -> None:
    first = PairwisePreference(
        "A",
        "B",
        "A",
        comparison_id="s1",
        assessor_id="p1",
        session_id="session-sequence",
        criterion_id="LIKING",
        first_presented_item="A",
        position_in_session=1,
    )
    second = PairwisePreference(
        "A",
        "B",
        "A",
        comparison_id="s2",
        assessor_id="p1",
        session_id="session-sequence",
        criterion_id="LIKING",
        first_presented_item="B",
        previous_presented_item="B",
        position_in_session=2,
    )
    receipt = assess_order_and_carryover(
        (first, second),
        config=OrderCarryoverConfig(require_qualified_carryover=True),
        carryover_qualified=False,
    )

    assert receipt.passed is False
    assert set(receipt.sequence_failure_codes) >= {
        "PREVIOUS_PRESENTED_SAMPLE_MISSING",
        "CARRYOVER_CONTROL_NOT_QUALIFIED",
    }


def test_tie_is_indifference_evidence_not_a_directional_order_win() -> None:
    rows = (
        PairwisePreference(
            "A",
            "B",
            "A",
            comparison_id="d1",
            assessor_id="p1",
            session_id="session-d1",
            criterion_id="LIKING",
            first_presented_item="A",
            position_in_session=1,
        ),
        PairwisePreference(
            "A",
            "B",
            None,
            comparison_id="t1",
            assessor_id="p2",
            session_id="session-t1",
            criterion_id="LIKING",
            first_presented_item="B",
            position_in_session=1,
        ),
    )
    receipt = assess_order_and_carryover(
        rows,
        config=OrderCarryoverConfig(),
        carryover_qualified=True,
    )

    assert receipt.directional_comparison_count == 1
    assert receipt.tie_count == 1
    assert receipt.stratified_first_position_effect == 1.0


def test_aggregate_balance_cannot_hide_partition_order_confounding() -> None:
    rows = tuple(
        PairwisePreference(
            "A",
            "B",
            "A",
            comparison_id=f"{partition}-{index}",
            assessor_id=f"p-{partition}-{index}",
            session_id=f"s-{partition}-{index}",
            criterion_id="LIKING",
            first_presented_item=first,
            position_in_session=1,
            partition=partition,
        )
        for partition, first in (("TRAINING", "A"), ("HELDOUT", "B"))
        for index in range(2)
    )
    receipt = assess_order_and_carryover(
        rows,
        config=OrderCarryoverConfig(maximum_pair_order_count_difference=0),
        carryover_qualified=True,
    )

    assert receipt.pair_order_counts == (("A", "B", 2, 2),)
    assert receipt.order_imbalanced_pairs == ()
    assert receipt.order_confounding_pairs == (("A", "B"),)
    assert receipt.passed is False


def test_missing_first_presentation_is_an_explicit_order_failure() -> None:
    row = PairwisePreference(
        "A",
        "B",
        "A",
        comparison_id="missing-first",
        assessor_id="p1",
        session_id="s1",
        criterion_id="LIKING",
        position_in_session=1,
    )
    receipt = assess_order_and_carryover(
        (row,),
        config=OrderCarryoverConfig(),
        carryover_qualified=True,
    )

    assert "FIRST_PRESENTED_ITEM_MISSING" in receipt.sequence_failure_codes
    assert receipt.passed is False
