from __future__ import annotations

import pytest

from engine.preference import PairwisePreference
from engine.preference_davidson import DavidsonFitConfig, fit_davidson
from engine.preference_validation import (
    ClusterBootstrapConfig,
    HeldoutValidationConfig,
    NextPairConstraints,
    PreferenceDiagnosticsConfig,
    TransitivityConfig,
    assess_transitivity,
    cluster_bootstrap,
    diagnose_preference_scope,
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
    position: int = 1,
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
        position_in_session=position,
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


def test_scope_diagnostics_freeze_split_hashes_components_and_counting() -> None:
    training = _balanced_rows()
    heldout = tuple(
        _row(
            f"h{index}",
            "p4",
            left,
            right,
            preferred,
            session="p4-heldout",
            partition="HELDOUT",
        )
        for index, (left, right, preferred) in enumerate(
            (("A", "B", "A"), ("A", "C", "A"), ("B", "C", "B")),
            start=1,
        )
    )
    fitted = _fit(training)
    bootstrap = cluster_bootstrap(
        training,
        config=ClusterBootstrapConfig(replicates=20, seed=17),
    )
    validation = validate_heldout(
        fitted=fitted,
        training=training,
        heldout=heldout,
        config=HeldoutValidationConfig(bootstrap_replicates=10, seed=17),
    )
    transitivity = assess_transitivity(
        training + heldout,
        config=TransitivityConfig(),
    )
    config = PreferenceDiagnosticsConfig(
        cluster_unit="ASSESSOR",
        counting_resolution_margin=0.95,
    )
    first = diagnose_preference_scope(
        fitted=fitted,
        training=training,
        heldout=heldout,
        cluster_bootstrap_receipt=bootstrap,
        heldout_validation_receipt=validation,
        transitivity_receipt=transitivity,
        config=config,
    )
    reordered = diagnose_preference_scope(
        fitted=fitted,
        training=tuple(reversed(training)),
        heldout=tuple(reversed(heldout)),
        cluster_bootstrap_receipt=bootstrap,
        heldout_validation_receipt=validation,
        transitivity_receipt=transitivity,
        config=config,
    )

    assert first.canonical_bytes() == reordered.canonical_bytes()
    assert first.connected_components == (("A", "B", "C"),)
    assert first.training_sha256 != first.heldout_sha256
    assert first.split_sha256
    assert first.configuration_sha256
    assert first.as_dict()["configuration"]["cluster_unit"] == "ASSESSOR"
    assert first.as_dict()["configuration"]["counting_resolution_margin"] == 0.95
    assert first.blocker_codes == ()


def test_scope_diagnostics_detect_carryover_and_repeated_exposure_reversal() -> None:
    rows = (
        _row("c1", "p1", "A", "B", "A", previous="A", position=1),
        _row("c2", "p2", "A", "B", "A", previous="A", position=1),
        _row("c3", "p3", "A", "B", "B", previous="B", position=2),
        _row("c4", "p4", "A", "B", "B", previous="B", position=2),
    )
    fitted = _fit(rows)
    bootstrap = cluster_bootstrap(
        rows,
        config=ClusterBootstrapConfig(replicates=20, seed=5),
    )
    heldout = (
        _row(
            "h1",
            "p5",
            "A",
            "B",
            "A",
            session="p5-heldout",
            partition="HELDOUT",
        ),
    )
    validation = validate_heldout(
        fitted=fitted,
        training=rows,
        heldout=heldout,
        config=HeldoutValidationConfig(bootstrap_replicates=5, seed=5),
    )
    transitivity = assess_transitivity(rows, config=TransitivityConfig())
    diagnostics = diagnose_preference_scope(
        fitted=fitted,
        training=rows,
        heldout=heldout,
        cluster_bootstrap_receipt=bootstrap,
        heldout_validation_receipt=validation,
        transitivity_receipt=transitivity,
        config=PreferenceDiagnosticsConfig(
            maximum_carryover_effect=0.25,
            maximum_repeated_exposure_effect=0.25,
        ),
    )

    assert diagnostics.carryover_effect == 1.0
    assert diagnostics.repeated_exposure_effect == 1.0
    assert "CARRYOVER_CONFOUNDED" in diagnostics.blocker_codes
    assert "REPEATED_EXPOSURE_CONFOUNDED" in diagnostics.blocker_codes


def test_scope_diagnostics_detect_presentation_order_reversal() -> None:
    rows = (
        _row("o1", "p1", "A", "B", "A", first="A"),
        _row("o2", "p2", "A", "B", "A", first="A"),
        _row("o3", "p3", "A", "B", "B", first="B"),
        _row("o4", "p4", "A", "B", "B", first="B"),
    )
    fitted = _fit(rows)
    heldout = (
        _row(
            "oh1",
            "p5",
            "A",
            "B",
            "A",
            session="heldout-order",
            partition="HELDOUT",
        ),
    )
    diagnostics = diagnose_preference_scope(
        fitted=fitted,
        training=rows,
        heldout=heldout,
        cluster_bootstrap_receipt=cluster_bootstrap(
            rows,
            config=ClusterBootstrapConfig(replicates=20, seed=5),
        ),
        heldout_validation_receipt=validate_heldout(
            fitted=fitted,
            training=rows,
            heldout=heldout,
            config=HeldoutValidationConfig(bootstrap_replicates=5, seed=5),
        ),
        transitivity_receipt=assess_transitivity(
            rows,
            config=TransitivityConfig(),
        ),
        config=PreferenceDiagnosticsConfig(maximum_order_effect=0.25),
    )

    assert diagnostics.order_effect == 1.0
    assert "ORDER_CONFOUNDED" in diagnostics.blocker_codes


def test_scope_diagnostics_identify_one_assessor_dominance() -> None:
    rows = tuple(
        _row(
            f"dominant-{index}",
            "dominant",
            "A",
            "B",
            "A",
            session="dominant-session",
        )
        for index in range(10)
    ) + tuple(
        _row(
            f"minority-{assessor}-{index}",
            assessor,
            "A",
            "B",
            "B",
            session=f"{assessor}-session",
        )
        for assessor in ("minority-1", "minority-2")
        for index in range(2)
    )
    fitted = _fit(rows)
    heldout = (
        _row(
            "dominance-heldout",
            "heldout",
            "A",
            "B",
            "A",
            session="heldout-session",
            partition="HELDOUT",
        ),
    )
    diagnostics = diagnose_preference_scope(
        fitted=fitted,
        training=rows,
        heldout=heldout,
        cluster_bootstrap_receipt=cluster_bootstrap(
            rows,
            config=ClusterBootstrapConfig(replicates=20, seed=7),
        ),
        heldout_validation_receipt=validate_heldout(
            fitted=fitted,
            training=rows,
            heldout=heldout,
            config=HeldoutValidationConfig(bootstrap_replicates=5, seed=7),
        ),
        transitivity_receipt=assess_transitivity(
            rows,
            config=TransitivityConfig(),
        ),
        config=PreferenceDiagnosticsConfig(
            maximum_leave_one_cluster_shift=0.25
        ),
    )

    assert diagnostics.influential_cluster_id == "dominant"
    assert diagnostics.leave_one_cluster_max_shift is not None
    assert "INFLUENTIAL_CLUSTER" in diagnostics.blocker_codes


def test_heldout_duplicate_comparison_identity_is_leakage() -> None:
    training = (
        _row("same", "p1", "A", "B", "A"),
        _row("training-only", "p2", "B", "A", "A"),
    )
    heldout = (
        _row(
            "same",
            "p2",
            "A",
            "B",
            "A",
            session="heldout-session",
            partition="HELDOUT",
        ),
    )
    receipt = validate_heldout(
        fitted=_fit(training),
        training=training,
        heldout=heldout,
        config=HeldoutValidationConfig(bootstrap_replicates=5, seed=1),
    )

    assert "COMPARISON_ID_SPLIT_LEAKAGE" in receipt.leakage_codes
    assert receipt.passed is False


def test_owner_bootstrap_resamples_sessions_deterministically() -> None:
    rows = (
        _row("s1-a", "owner", "A", "B", "A", session="session-1"),
        _row("s1-b", "owner", "A", "C", "A", session="session-1"),
        _row("s2-a", "owner", "A", "B", "A", session="session-2"),
        _row("s2-b", "owner", "B", "C", "B", session="session-2"),
        _row("s3-a", "owner", "A", "C", "A", session="session-3"),
        _row("s3-b", "owner", "B", "C", "B", session="session-3"),
    )
    config = ClusterBootstrapConfig(
        replicates=20,
        seed=23,
        cluster_unit="SESSION",
    )

    first = cluster_bootstrap(rows, config=config)
    second = cluster_bootstrap(tuple(reversed(rows)), config=config)

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.interval_method == "SESSION_CLUSTER_PERCENTILE"
    assert first.effective_unique_assessors == 1
    assert first.cluster_unit == "SESSION"
    assert first.effective_unique_clusters == 3
    assert first.leave_one_cluster_max_shift is not None
    assert first.completed_replicates > 0
