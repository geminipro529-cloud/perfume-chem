from __future__ import annotations

import pytest

from engine.preference import PairwisePreference, PreferenceOutcome
from engine.preference_davidson import DavidsonFitConfig, fit_davidson


def _rows(
    left_wins: int,
    right_wins: int,
    ties: int,
) -> tuple[PairwisePreference, ...]:
    return (
        tuple(PairwisePreference("A", "B", "A") for _ in range(left_wins))
        + tuple(PairwisePreference("A", "B", "B") for _ in range(right_wins))
        + tuple(PairwisePreference("A", "B", None) for _ in range(ties))
    )


def test_three_argument_constructor_maps_none_to_legacy_no_preference() -> None:
    row = PairwisePreference("A", "B", None)

    assert row.outcome is PreferenceOutcome.NO_PREFERENCE
    assert row.legacy_outcome_semantics is True


def test_explicit_outcomes_round_trip_and_reject_contradictions() -> None:
    row = PairwisePreference(
        "A",
        "B",
        None,
        outcome=PreferenceOutcome.NO_PERCEPTIBLE_DIFFERENCE,
        session_id="session-1",
        matrix_id="matrix-1",
        time_window_id="heart",
        previous_presented_item="B",
        position_in_session=3,
        protocol_sha256="a" * 64,
        sample_sha256="b" * 64,
    )

    assert PairwisePreference.from_dict(row.as_dict()) == row
    assert row.legacy_outcome_semantics is False
    with pytest.raises(ValueError, match="contradicts"):
        PairwisePreference("A", "B", "A", outcome=PreferenceOutcome.RIGHT)


def test_ties_participate_in_davidson_likelihood() -> None:
    fit = fit_davidson(
        items=("A", "B"),
        comparisons=_rows(30, 10, 10),
        config=DavidsonFitConfig(regularization=0.1, maximum_iterations=200),
    )

    assert fit.tie_parameter > 0
    assert fit.utilities["A"] > fit.utilities["B"]
    assert abs(sum(fit.utilities.values())) < 1e-10
    assert fit.converged


def test_nonpreference_protocol_outcomes_do_not_enter_likelihood() -> None:
    included = _rows(12, 4, 4)
    excluded = (
        PairwisePreference(
            "A", "B", None, outcome=PreferenceOutcome.NO_PERCEPTIBLE_DIFFERENCE
        ),
        PairwisePreference("A", "B", None, outcome=PreferenceOutcome.CANNOT_JUDGE),
        PairwisePreference("A", "B", None, outcome=PreferenceOutcome.PROTOCOL_ABORT),
    )
    first = fit_davidson(
        items=("A", "B"),
        comparisons=included,
        config=DavidsonFitConfig(),
    )
    second = fit_davidson(
        items=("A", "B"),
        comparisons=included + excluded,
        config=DavidsonFitConfig(),
    )

    assert first.canonical_bytes() == second.canonical_bytes()


def test_davidson_fit_is_repeatable_for_three_items() -> None:
    rows = (
        _rows(18, 6, 6)
        + tuple(PairwisePreference("A", "C", "A") for _ in range(16))
        + tuple(PairwisePreference("A", "C", "C") for _ in range(4))
        + tuple(PairwisePreference("A", "C", None) for _ in range(5))
        + tuple(PairwisePreference("B", "C", "B") for _ in range(12))
        + tuple(PairwisePreference("B", "C", "C") for _ in range(8))
        + tuple(PairwisePreference("B", "C", None) for _ in range(5))
    )
    config = DavidsonFitConfig(regularization=0.1, maximum_iterations=300)

    first = fit_davidson(items=("A", "B", "C"), comparisons=rows, config=config)
    second = fit_davidson(items=("A", "B", "C"), comparisons=rows, config=config)

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.utilities["A"] > first.utilities["B"] > first.utilities["C"]
    assert first.parameter_order == ("A", "B", "C", "LOG_TIE_PARAMETER")


def test_insufficient_or_unregularized_boundary_data_fail_closed() -> None:
    with pytest.raises(ValueError, match="at least two likelihood rows"):
        fit_davidson(
            items=("A", "B"),
            comparisons=(PairwisePreference("A", "B", "A"),),
            config=DavidsonFitConfig(),
        )
    boundary = fit_davidson(
        items=("A", "B"),
        comparisons=_rows(20, 0, 0),
        config=DavidsonFitConfig(regularization=0.0, maximum_iterations=100),
    )
    assert boundary.converged is False
    assert boundary.convergence_code == "BOUNDARY_UNIDENTIFIED"
