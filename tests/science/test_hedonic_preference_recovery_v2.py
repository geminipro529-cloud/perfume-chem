from __future__ import annotations

import json
import math
import random
from dataclasses import replace
from pathlib import Path

from engine.preference import (
    PairwisePreference,
    PreferenceFitRequest,
    PreferenceFitStatus,
    fit_preference_model,
)
from engine.preference_davidson import DavidsonFitConfig, fit_davidson
from engine.preference_validation import ClusterBootstrapConfig, cluster_bootstrap

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = (
    ROOT
    / "data"
    / "benchmarks"
    / "solforge"
    / "evidence_foundation_recovery_v1"
    / "manifest.json"
)
TRUE_UTILITIES = {"A": 0.9, "B": 0.0, "C": -0.9}
TRUE_TIE_PARAMETER = 0.8


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _probabilities(left: float, right: float, tie: float) -> tuple[float, ...]:
    left_strength = math.exp(left)
    right_strength = math.exp(right)
    tie_strength = tie * math.sqrt(left_strength * right_strength)
    total = left_strength + right_strength + tie_strength
    return (
        left_strength / total,
        right_strength / total,
        tie_strength / total,
    )


def synthetic_rows(
    seed: int,
    *,
    assessor_count: int = 8,
    repeats_per_pair: int = 12,
    utilities: dict[str, float] | None = None,
    tie_parameter: float = TRUE_TIE_PARAMETER,
) -> tuple[PairwisePreference, ...]:
    utility = utilities or TRUE_UTILITIES
    rng = random.Random(seed)
    rows: list[PairwisePreference] = []
    index = 0
    for assessor_index in range(assessor_count):
        assessor = f"p{assessor_index + 1:02d}"
        for left, right in (("A", "B"), ("A", "C"), ("B", "C")):
            for repeat in range(repeats_per_pair):
                index += 1
                p_left, p_right, _ = _probabilities(
                    utility[left], utility[right], tie_parameter
                )
                draw = rng.random()
                preferred = (
                    left
                    if draw < p_left
                    else right
                    if draw < p_left + p_right
                    else None
                )
                first = left if (assessor_index + repeat) % 2 == 0 else right
                rows.append(
                    PairwisePreference(
                        left,
                        right,
                        preferred,
                        comparison_id=f"cmp-{index:05d}",
                        assessor_id=assessor,
                        protocol_id="recovery-davidson-v2",
                        criterion_id="LIKING",
                        time_seconds=300,
                        first_presented_item=first,
                        session_id=f"session-{assessor}",
                        matrix_id="matrix-recovery-1",
                        time_window_id="heart",
                        position_in_session=repeat + 1,
                        protocol_sha256="a" * 64,
                        sample_sha256="b" * 64,
                        partition="TRAINING",
                    )
                )
    return tuple(rows)


def _fit(rows: tuple[PairwisePreference, ...]):
    return fit_davidson(
        items=("A", "B", "C"),
        comparisons=rows,
        config=DavidsonFitConfig(regularization=0.1, maximum_iterations=400),
    )


def test_fixed_seed_recovers_utilities_ties_and_exact_bytes() -> None:
    config = _manifest()["hedonic_recovery"]
    rows = synthetic_rows(
        int(config["recovery_seed"]),
        assessor_count=int(config["recovery_assessors"]),
        repeats_per_pair=int(config["recovery_repeats_per_pair"]),
    )
    fitted = _fit(rows)
    bootstrap = cluster_bootstrap(
        rows,
        config=ClusterBootstrapConfig(
            replicates=int(config["bootstrap_replicates"]),
            seed=int(config["bootstrap_seed"]),
            maximum_iterations=400,
        ),
    )

    assert fitted.receipt_sha256 == config["fit_receipt_sha256"]
    assert bootstrap.receipt_sha256 == config["bootstrap_receipt_sha256"]
    assert fitted.utilities["A"] > fitted.utilities["B"] > fitted.utilities["C"]
    assert max(
        abs(fitted.utilities[item] - TRUE_UTILITIES[item])
        for item in TRUE_UTILITIES
    ) <= float(config["maximum_absolute_utility_error"])
    assert abs(fitted.tie_parameter - TRUE_TIE_PARAMETER) <= float(
        config["maximum_absolute_tie_error"]
    )
    assert bootstrap.interval_method == "ASSESSOR_CLUSTER_PERCENTILE"


def test_cluster_interval_coverage_meets_the_frozen_floor() -> None:
    config = _manifest()["hedonic_recovery"]
    covered = 0
    evaluated = 0
    for seed in config["coverage_seeds"]:
        rows = synthetic_rows(
            int(seed),
            assessor_count=int(config["coverage_assessors"]),
            repeats_per_pair=int(config["coverage_repeats_per_pair"]),
        )
        receipt = cluster_bootstrap(
            rows,
            config=ClusterBootstrapConfig(
                replicates=int(config["coverage_bootstrap_replicates"]),
                seed=int(seed) + 10_000,
                maximum_iterations=400,
            ),
        )
        for item, truth in TRUE_UTILITIES.items():
            lower, upper = receipt.utility_intervals[item]
            covered += lower <= truth <= upper
            evaluated += 1

    coverage = covered / evaluated
    assert coverage == float(config["expected_interval_coverage"])
    assert coverage >= float(config["minimum_interval_coverage"])
    assert coverage <= float(config["maximum_interval_coverage"])


def test_null_data_do_not_create_false_interval_winners() -> None:
    config = _manifest()["hedonic_recovery"]
    false_winners = 0
    seeds = tuple(int(seed) for seed in config["null_seeds"])
    for seed in seeds:
        rows = synthetic_rows(
            seed,
            assessor_count=int(config["null_assessors"]),
            repeats_per_pair=int(config["null_repeats_per_pair"]),
            utilities={"A": 0.0, "B": 0.0, "C": 0.0},
        )
        receipt = cluster_bootstrap(
            rows,
            config=ClusterBootstrapConfig(
                replicates=int(config["null_bootstrap_replicates"]),
                seed=seed + 20_000,
                maximum_iterations=400,
            ),
        )
        intervals = receipt.utility_intervals
        winner = any(
            intervals[item][0]
            > max(intervals[other][1] for other in intervals if other != item)
            for item in intervals
        )
        false_winners += winner

    false_winner_rate = false_winners / len(seeds)
    assert false_winner_rate == float(config["expected_false_winner_rate"])
    assert false_winner_rate <= float(config["maximum_false_winner_rate"])


def test_row_order_and_blind_label_permutation_preserve_recovery() -> None:
    config = _manifest()["hedonic_recovery"]
    rows = synthetic_rows(
        int(config["recovery_seed"]),
        assessor_count=int(config["recovery_assessors"]),
        repeats_per_pair=int(config["recovery_repeats_per_pair"]),
    )
    fitted = _fit(rows)
    reversed_fit = _fit(tuple(reversed(rows)))
    label_map = {"A": "X-17", "B": "X-03", "C": "X-92"}
    relabeled = tuple(
        replace(
            row,
            left_item=label_map[row.left_item],
            right_item=label_map[row.right_item],
            preferred_item=(
                None if row.preferred_item is None else label_map[row.preferred_item]
            ),
            first_presented_item=label_map[row.first_presented_item or row.left_item],
            previous_presented_item=(
                None
                if row.previous_presented_item is None
                else label_map[row.previous_presented_item]
            ),
        )
        for row in rows
    )
    relabeled_fit = fit_davidson(
        items=tuple(label_map.values()),
        comparisons=relabeled,
        config=DavidsonFitConfig(regularization=0.1, maximum_iterations=400),
    )

    assert fitted.canonical_bytes() == reversed_fit.canonical_bytes()
    assert {
        item: fitted.utilities[item] for item in ("A", "B", "C")
    } == {
        item: relabeled_fit.utilities[label_map[item]]
        for item in ("A", "B", "C")
    }
    assert fitted.tie_parameter == relabeled_fit.tie_parameter


def test_sparse_disconnected_or_criterion_leaking_inputs_never_validate() -> None:
    disconnected = fit_preference_model(
        PreferenceFitRequest(
            training=(
                PairwisePreference("A", "B", "A"),
                PairwisePreference("A", "B", "A"),
                PairwisePreference("C", "D", "C"),
                PairwisePreference("C", "D", "C"),
            ),
            minimum_comparisons=4,
            criterion_id="LIKING",
        )
    )
    scoped = synthetic_rows(2026082699, assessor_count=2, repeats_per_pair=2)
    leaking = scoped[:-1] + (replace(scoped[-1], criterion_id="RICHNESS"),)
    criterion_leak = fit_preference_model(
        PreferenceFitRequest(
            training=leaking,
            minimum_comparisons=6,
            criterion_id="LIKING",
            require_scoped_validation=True,
        )
    )

    assert disconnected.status is PreferenceFitStatus.WITHHELD
    assert criterion_leak.status is PreferenceFitStatus.WITHHELD
