from __future__ import annotations

from engine.preference import (
    PairwisePreference,
    PreferenceFitRequest,
    PreferenceFitStatus,
    PreferenceModelFamily,
    PreferenceOutcome,
    _order_effect,
    fit_preference_model,
)


def test_pairwise_preference_preserves_legacy_constructor_and_round_trips_scope() -> None:
    legacy = PairwisePreference("A", "B", "A")
    scoped = PairwisePreference(
        "A",
        "B",
        "A",
        comparison_id="comparison-1",
        assessor_id="assessor-1",
        protocol_id="protocol-1",
        criterion_id="richness",
        time_seconds=300,
        first_presented_item="B",
    )

    assert legacy.left_item == "A"
    assert legacy.comparison_id is None
    assert PairwisePreference.from_dict(scoped.as_dict()) == scoped
    assert legacy.outcome is PreferenceOutcome.LEFT


def _scoped(
    comparison_id: str,
    assessor_id: str,
    left: str,
    right: str,
    preferred: str | None,
    *,
    first: str,
    criterion: str = "richness",
) -> PairwisePreference:
    return PairwisePreference(
        left,
        right,
        preferred,
        comparison_id=comparison_id,
        assessor_id=assessor_id,
        protocol_id="protocol-preference-v1",
        criterion_id=criterion,
        time_seconds=300,
        first_presented_item=first,
    )


def test_bootstrap_intervals_ties_heterogeneity_and_next_pair_are_deterministic() -> None:
    training = (
        _scoped("c1", "p1", "A", "B", "A", first="A"),
        _scoped("c2", "p1", "A", "C", "A", first="C"),
        _scoped("c3", "p1", "B", "C", "B", first="B"),
        _scoped("c4", "p2", "A", "B", "A", first="B"),
        _scoped("c5", "p2", "A", "C", "A", first="A"),
        _scoped("c6", "p2", "B", "C", "B", first="C"),
        _scoped("c7", "p2", "A", "B", None, first="A"),
    )
    request = PreferenceFitRequest(
        training=training,
        minimum_comparisons=6,
        criterion_id="richness",
        bootstrap_replicates=50,
        bootstrap_seed=17,
    )

    first = fit_preference_model(request)
    second = fit_preference_model(request)

    assert first.status is PreferenceFitStatus.DIAGNOSTIC
    assert first.utility_intervals == second.utility_intervals
    assert set(first.utility_intervals) == {"A", "B", "C"}
    assert first.tie_rate == 1 / 7
    assert set(first.assessor_heterogeneity) == {"p1", "p2"}
    assert first.next_comparison == second.next_comparison
    assert first.next_comparison is not None
    assert first.bootstrap_method == "ASSESSOR_CLUSTER"


def _balanced_training() -> tuple[PairwisePreference, ...]:
    return (
        _scoped("t1", "p1", "A", "B", "A", first="A"),
        _scoped("t2", "p1", "A", "C", "A", first="C"),
        _scoped("t3", "p1", "B", "C", "B", first="B"),
        _scoped("t4", "p2", "A", "B", "A", first="B"),
        _scoped("t5", "p2", "A", "C", "A", first="A"),
        _scoped("t6", "p2", "B", "C", "B", first="C"),
    )


def _heldout() -> tuple[PairwisePreference, ...]:
    return (
        _scoped("h1", "p3", "A", "B", "A", first="A"),
        _scoped("h2", "p3", "A", "C", "A", first="C"),
        _scoped("h3", "p3", "B", "C", "B", first="B"),
    )


def test_mixed_preference_criteria_are_withheld_instead_of_aggregated() -> None:
    mixed = _balanced_training()[:-1] + (
        _scoped("t6", "p2", "B", "C", "B", first="C", criterion="liking"),
    )

    result = fit_preference_model(
        PreferenceFitRequest(
            training=mixed,
            minimum_comparisons=6,
            criterion_id="richness",
        )
    )

    assert result.status is PreferenceFitStatus.WITHHELD
    assert result.utilities == {}
    assert any("criterion" in failure for failure in result.gate_failures)


def test_scoped_balanced_records_can_validate_but_unscoped_or_order_confounded_cannot() -> None:
    validated = fit_preference_model(
        PreferenceFitRequest(
            training=_balanced_training(),
            heldout=_heldout(),
            minimum_comparisons=6,
            minimum_heldout_comparisons=3,
            declared_baseline_accuracy=0.5,
            criterion_id="richness",
            require_scoped_validation=True,
        )
    )
    unscoped_training = tuple(
        PairwisePreference(item.left_item, item.right_item, item.preferred_item)
        for item in _balanced_training()
    )
    unscoped_heldout = tuple(
        PairwisePreference(item.left_item, item.right_item, item.preferred_item)
        for item in _heldout()
    )
    unscoped = fit_preference_model(
        PreferenceFitRequest(
            training=unscoped_training,
            heldout=unscoped_heldout,
            minimum_comparisons=6,
            minimum_heldout_comparisons=3,
            declared_baseline_accuracy=0.5,
            criterion_id="richness",
            require_scoped_validation=True,
        )
    )
    confounded_training = tuple(
        PairwisePreference(
            item.left_item,
            item.right_item,
            item.preferred_item,
            comparison_id=item.comparison_id,
            assessor_id=item.assessor_id,
            protocol_id=item.protocol_id,
            criterion_id=item.criterion_id,
            time_seconds=item.time_seconds,
            first_presented_item=item.left_item,
        )
        for item in _balanced_training()
    )
    confounded = fit_preference_model(
        PreferenceFitRequest(
            training=confounded_training,
            heldout=_heldout(),
            minimum_comparisons=6,
            minimum_heldout_comparisons=3,
            declared_baseline_accuracy=0.5,
            criterion_id="richness",
            require_scoped_validation=True,
        )
    )

    assert validated.status is PreferenceFitStatus.VALIDATED
    assert unscoped.status is PreferenceFitStatus.DIAGNOSTIC
    assert any("scoped metadata" in note for note in unscoped.validation_notes)
    assert confounded.status is PreferenceFitStatus.DIAGNOSTIC
    assert any("presentation order" in note for note in confounded.validation_notes)


def test_davidson_result_retains_ties_but_excludes_discrimination_only_rows() -> None:
    training = _balanced_training() + (
        _scoped("tie-1", "p1", "A", "B", None, first="A"),
        PairwisePreference(
            "A",
            "B",
            None,
            comparison_id="npd-1",
            assessor_id="p2",
            protocol_id="protocol-preference-v1",
            criterion_id="richness",
            time_seconds=300,
            first_presented_item="B",
            outcome=PreferenceOutcome.NO_PERCEPTIBLE_DIFFERENCE,
        ),
    )
    result = fit_preference_model(
        PreferenceFitRequest(
            training=training,
            minimum_comparisons=6,
            criterion_id="richness",
        )
    )

    assert result.model_family is PreferenceModelFamily.DAVIDSON_V1
    assert result.comparison_count == 6
    assert result.tie_rate == 1 / 7
    assert result.tie_parameter is not None and result.tie_parameter > 0
    assert result.converged is True
    assert set(result.pair_probabilities) == {"A|B", "A|C", "B|C"}
    assert all(
        abs(sum(probabilities) - 1.0) < 1e-12
        for probabilities in result.pair_probabilities.values()
    )


def test_ties_are_excluded_from_directional_order_effect() -> None:
    rows = (
        _scoped("o1", "p1", "A", "B", "A", first="A"),
        _scoped("o2", "p2", "A", "B", "B", first="B"),
        _scoped("tie", "p3", "A", "B", None, first="A"),
    )

    assert _order_effect(rows) == 0.5


def test_scoped_validation_rejects_legacy_bradley_terry_family() -> None:
    result = fit_preference_model(
        PreferenceFitRequest(
            training=_balanced_training(),
            heldout=_heldout(),
            minimum_comparisons=6,
            minimum_heldout_comparisons=3,
            declared_baseline_accuracy=0.5,
            criterion_id="richness",
            require_scoped_validation=True,
            model_family=PreferenceModelFamily.BRADLEY_TERRY_LEGACY,
        )
    )

    assert result.status is PreferenceFitStatus.WITHHELD
    assert any("legacy model family" in failure for failure in result.gate_failures)
