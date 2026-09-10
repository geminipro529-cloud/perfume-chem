from __future__ import annotations

import math
import random

from engine.preference import PairwisePreference
from engine.preference_davidson import DavidsonFitConfig, fit_davidson
from engine.preference_validation import (
    ClusterBootstrapConfig,
    TransitivityConfig,
    assess_transitivity,
    cluster_bootstrap,
)


def _davidson_probabilities(left: float, right: float, tie: float) -> tuple[float, float, float]:
    left_strength = math.exp(left)
    right_strength = math.exp(right)
    tie_strength = tie * math.sqrt(left_strength * right_strength)
    total = left_strength + right_strength + tie_strength
    return left_strength / total, right_strength / total, tie_strength / total


def _synthetic_rows(seed: int) -> tuple[PairwisePreference, ...]:
    rng = random.Random(seed)
    utilities = {"A": 0.9, "B": 0.0, "C": -0.9}
    rows: list[PairwisePreference] = []
    index = 0
    for assessor in range(8):
        for left, right in (("A", "B"), ("A", "C"), ("B", "C")):
            for repeat in range(12):
                index += 1
                p_left, p_right, _ = _davidson_probabilities(
                    utilities[left], utilities[right], 0.8
                )
                draw = rng.random()
                preferred = left if draw < p_left else right if draw < p_left + p_right else None
                first = left if (assessor + repeat) % 2 == 0 else right
                rows.append(
                    PairwisePreference(
                        left,
                        right,
                        preferred,
                        comparison_id=f"cmp-{index:04d}",
                        assessor_id=f"p{assessor + 1}",
                        protocol_id="synthetic-davidson-v1",
                        criterion_id="LIKING",
                        time_seconds=300,
                        first_presented_item=first,
                        session_id=f"session-{assessor + 1}",
                        matrix_id="matrix-1",
                        time_window_id="heart",
                        position_in_session=repeat + 1,
                        protocol_sha256="a" * 64,
                        sample_sha256="b" * 64,
                        partition="TRAINING",
                    )
                )
    return tuple(rows)


def test_fixed_seed_recovers_order_and_ties_with_exact_repeatability() -> None:
    rows = _synthetic_rows(2026082601)
    config = DavidsonFitConfig(regularization=0.1, maximum_iterations=400)
    first = fit_davidson(items=("A", "B", "C"), comparisons=rows, config=config)
    second = fit_davidson(items=("A", "B", "C"), comparisons=rows, config=config)

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.converged
    assert first.utilities["A"] > first.utilities["B"] > first.utilities["C"]
    assert first.tie_parameter > 0


def test_assessor_cluster_uncertainty_is_repeatable_and_not_row_bootstrap() -> None:
    rows = _synthetic_rows(2026082602)
    config = ClusterBootstrapConfig(replicates=40, seed=2026082602)
    first = cluster_bootstrap(rows, config=config)
    second = cluster_bootstrap(rows, config=config)

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.interval_method == "ASSESSOR_CLUSTER_PERCENTILE"
    assert first.effective_unique_assessors == 8
    assert first.completed_replicates + first.failed_replicates == 40
    assert set(first.utility_intervals) == {"A", "B", "C"}


def test_null_preferences_do_not_create_a_large_false_winner() -> None:
    rng = random.Random(2026082603)
    rows = tuple(
        PairwisePreference("A", "B", "A" if rng.random() < 0.5 else "B")
        for _ in range(400)
    )
    fit = fit_davidson(
        items=("A", "B"),
        comparisons=rows,
        config=DavidsonFitConfig(regularization=0.1, maximum_iterations=300),
    )

    assert abs(fit.utilities["A"] - fit.utilities["B"]) < 0.35


def test_nontransitivity_and_temporal_reversal_withhold_global_winner() -> None:
    cycle = (
        PairwisePreference("A", "B", "A", time_window_id="heart"),
        PairwisePreference("B", "C", "B", time_window_id="heart"),
        PairwisePreference("A", "C", "C", time_window_id="heart"),
    )
    crossover = (
        PairwisePreference("A", "B", "A", time_window_id="opening"),
        PairwisePreference("A", "B", "A", time_window_id="opening"),
        PairwisePreference("A", "B", "B", time_window_id="drydown"),
        PairwisePreference("A", "B", "B", time_window_id="drydown"),
    )

    assert assess_transitivity(cycle, config=TransitivityConfig()).global_winner_withheld
    result = assess_transitivity(crossover, config=TransitivityConfig())
    assert result.temporal_crossovers == (("A", "B"),)
    assert result.global_winner_withheld
