"""Source-internal closed-form baselines for the exact Ma et al. 2021 V2 data.

Data source: DOI 10.15454/51OVY6, file PID 10.15454/51OVY6/COAY4H.
Processing: collapse only the 24 source-declared repeat pairs by immutable
mixture key, evaluate preregistered closed-form baselines, and quantify source
repeat disagreement with a deterministic group bootstrap.
Scientific purpose: decide whether a costlier nonlinear residual model is
justified. The result cannot authorize perfume formulation, physical execution,
generalization, publication claims, or release decisions.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from statistics import fmean
from typing import Callable, Iterable, Mapping, Sequence

from app.adapters.ma_2021 import (
    MA2021_ARTIFACT_SHA256,
    MA2021_ARTIFACT_SIZE,
    MA2021_DATASET_DOI,
    MA2021_ENDPOINTS,
    MA2021_FILE_PID,
    Ma2021AggregateTrial,
    Ma2021Dataset,
)

MA2021_BASELINE_DECISION = (
    "DATA_AMBER_MA2021_SOURCE_INTERNAL_BASELINES_QUANTIFIED_NONLINEAR_ESCALATION_NOT_AUTHORIZED"
)
_BOOTSTRAP_ITERATIONS = 20_000
_BOOTSTRAP_SEED = 20_260_812
_ZERO = "0.000000000000"


def _number(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("benchmark values must be finite")
    rendered = f"{value:.12f}"
    return _ZERO if rendered == "-0.000000000000" else rendered


def _pearson(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("Pearson correlation requires equal nontrivial vectors")
    left_mean = fmean(left)
    right_mean = fmean(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    denominator = math.sqrt(
        sum(value * value for value in left_centered)
        * sum(value * value for value in right_centered)
    )
    if denominator == 0:
        raise ValueError("Pearson correlation is undefined for a constant vector")
    return (
        sum(
            left_value * right_value
            for left_value, right_value in zip(
                left_centered,
                right_centered,
                strict=True,
            )
        )
        / denominator
    )


def _metric(predicted: Sequence[float], observed: Sequence[float]) -> dict[str, object]:
    errors = [
        prediction - observation
        for prediction, observation in zip(predicted, observed, strict=True)
    ]
    return {
        "n": len(errors),
        "mae": _number(fmean(abs(error) for error in errors)),
        "rmse": _number(math.sqrt(fmean(error * error for error in errors))),
        "pearson_r": _number(_pearson(predicted, observed)),
        "bias_prediction_minus_observed": _number(fmean(errors)),
    }


def _rmse(errors: Sequence[float]) -> float:
    return math.sqrt(fmean(error * error for error in errors))


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    location = (len(ordered) - 1) * probability
    lower = math.floor(location)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = location - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _paired_rmse_bootstrap(
    reference_errors: Sequence[float],
    candidate_errors: Sequence[float],
    *,
    random_source: random.Random,
    iterations: int,
) -> dict[str, object]:
    if len(reference_errors) != len(candidate_errors):
        raise ValueError("paired bootstrap vectors must have equal length")
    count = len(reference_errors)
    draws: list[float] = []
    for _ in range(iterations):
        indices = [random_source.randrange(count) for _ in range(count)]
        draws.append(
            _rmse([reference_errors[index] for index in indices])
            - _rmse([candidate_errors[index] for index in indices])
        )
    observed = _rmse(reference_errors) - _rmse(candidate_errors)
    return {
        "definition": "RMSE_REFERENCE_MINUS_CANDIDATE",
        "observed_delta": _number(observed),
        "ci95_percentile": [
            _number(_percentile(draws, 0.025)),
            _number(_percentile(draws, 0.975)),
        ],
        "bootstrap_probability_delta_le_zero": _number(
            sum(value <= 0 for value in draws) / iterations
        ),
    }


def _bootstrap_rmse(
    errors: Sequence[float],
    *,
    random_source: random.Random,
    iterations: int,
) -> list[str]:
    count = len(errors)
    draws: list[float] = []
    for _ in range(iterations):
        indices = [random_source.randrange(count) for _ in range(count)]
        draws.append(_rmse([errors[index] for index in indices]))
    return [
        _number(_percentile(draws, 0.025)),
        _number(_percentile(draws, 0.975)),
    ]


def _mean_endpoint(
    rows: Iterable[Ma2021AggregateTrial],
    endpoint: str,
) -> float:
    return fmean(float(row.values[endpoint]) for row in rows)


def _mixture_level_rows(dataset: Ma2021Dataset) -> list[dict[str, float]]:
    grouped: dict[int, list[Ma2021AggregateTrial]] = defaultdict(list)
    for row in dataset.aggregate_trials:
        grouped[row.mixture_key].append(row)
    return [
        {endpoint: _mean_endpoint(grouped[mixture_key], endpoint) for endpoint in MA2021_ENDPOINTS}
        for mixture_key in sorted(grouped)
    ]


def _prediction_errors(
    rows: Sequence[Mapping[str, float]],
    predictor: Callable[[Mapping[str, float]], float],
    target: str,
) -> list[float]:
    return [predictor(row) - row[target] for row in rows]


def _repeat_pairs(dataset: Ma2021Dataset) -> list[tuple[Ma2021AggregateTrial, ...]]:
    grouped: dict[int, list[Ma2021AggregateTrial]] = defaultdict(list)
    for row in dataset.aggregate_trials:
        if row.reference_trial is not None:
            grouped[row.reference_trial].append(row)
    return [
        tuple(sorted(grouped[key], key=lambda row: int(row.repeat_index or 0)))
        for key in sorted(grouped)
    ]


def _repeatability(
    dataset: Ma2021Dataset,
    *,
    bootstrap_iterations: int,
    seed: int,
) -> dict[str, dict[str, object]]:
    pairs = _repeat_pairs(dataset)
    result: dict[str, dict[str, object]] = {}
    for ordinal, endpoint in enumerate(MA2021_ENDPOINTS):
        first = [float(pair[0].values[endpoint]) for pair in pairs]
        second = [float(pair[1].values[endpoint]) for pair in pairs]
        differences = [left - right for left, right in zip(first, second, strict=True)]
        result[endpoint] = {
            "n_repeat_groups": len(pairs),
            "pearson_r": _number(_pearson(first, second)),
            "mae": _number(fmean(abs(value) for value in differences)),
            "rmse": _number(_rmse(differences)),
            "rmse_ci95_percentile": _bootstrap_rmse(
                differences,
                random_source=random.Random(seed + 100 + ordinal),
                iterations=bootstrap_iterations,
            ),
        }
    return result


def ma2021_baseline_payload_sha256(report: Mapping[str, object]) -> str:
    """Hash the canonical report excluding its self-referential hash field."""

    payload = dict(report)
    payload.pop("scientific_payload_sha256", None)
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_ma2021_baseline_benchmark(
    dataset: Ma2021Dataset,
    *,
    bootstrap_iterations: int = _BOOTSTRAP_ITERATIONS,
    seed: int = _BOOTSTRAP_SEED,
) -> dict[str, object]:
    """Build a deterministic, authority-false source-internal benchmark."""

    if dataset.artifact_sha256 != MA2021_ARTIFACT_SHA256:
        raise ValueError("Ma 2021 benchmark requires the exact pinned artifact")
    if bootstrap_iterations < 1:
        raise ValueError("bootstrap_iterations must be positive")

    rows = _mixture_level_rows(dataset)
    observed_intensity = [row["IAB"] for row in rows]
    observed_pleasantness = [row["PAB"] for row in rows]

    intensity_strongest = [max(row["IA"], row["IB"]) for row in rows]
    pleasantness_arithmetic = [(row["PA"] + row["PB"]) / 2 for row in rows]
    pleasantness_intensity_weighted = [
        (row["IA"] * row["PA"] + row["IB"] * row["PB"]) / (row["IA"] + row["IB"]) for row in rows
    ]
    pleasantness_squared_weighted = [
        (row["IA"] ** 2 * row["PA"] + row["IB"] ** 2 * row["PB"])
        / (row["IA"] ** 2 + row["IB"] ** 2)
        for row in rows
    ]

    arithmetic_errors = _prediction_errors(
        rows,
        lambda row: (row["PA"] + row["PB"]) / 2,
        "PAB",
    )
    intensity_weighted_errors = _prediction_errors(
        rows,
        lambda row: (row["IA"] * row["PA"] + row["IB"] * row["PB"]) / (row["IA"] + row["IB"]),
        "PAB",
    )
    squared_weighted_errors = _prediction_errors(
        rows,
        lambda row: (
            (row["IA"] ** 2 * row["PA"] + row["IB"] ** 2 * row["PB"])
            / (row["IA"] ** 2 + row["IB"] ** 2)
        ),
        "PAB",
    )

    repeatability = _repeatability(
        dataset,
        bootstrap_iterations=bootstrap_iterations,
        seed=seed,
    )
    intensity_rmse = _rmse(
        [
            prediction - observation
            for prediction, observation in zip(
                intensity_strongest,
                observed_intensity,
                strict=True,
            )
        ]
    )
    repeat_iab_rmse_value = repeatability["IAB"]["rmse"]
    if not isinstance(repeat_iab_rmse_value, (int, float, str)):
        raise TypeError("repeat IAB RMSE must be numeric")
    repeat_iab_rmse = float(repeat_iab_rmse_value)

    report: dict[str, object] = {
        "schema_version": "perfume-chem-ma2021-baseline-benchmark-v1",
        "evidence_id": "ma_2021_binary_mixture_baseline_benchmark",
        "decision": MA2021_BASELINE_DECISION,
        "source_binding": {
            "dataset_doi": MA2021_DATASET_DOI,
            "file_pid": MA2021_FILE_PID,
            "artifact_bytes": MA2021_ARTIFACT_SIZE,
            "artifact_sha256": MA2021_ARTIFACT_SHA256,
            "source_family_count": 1,
        },
        "design": {
            "source_trial_rows": len(dataset.aggregate_trials),
            "unique_mixture_groups": len(rows),
            "duplicated_mixture_groups": len(_repeat_pairs(dataset)),
            "participant_trial_rows": len(dataset.participant_trials),
            "participant_rows_used_for_benchmark": 0,
            "unit_of_analysis": "UNIQUE_MIXTURE_KEY",
            "duplicate_policy": ("AVERAGE_SOURCE_AGGREGATE_REPEAT_ROWS_WITHIN_MIXTURE_KEY"),
            "source_aggregate_recomputed": False,
            "bootstrap_unit": "UNIQUE_MIXTURE_KEY",
            "bootstrap_iterations": bootstrap_iterations,
            "bootstrap_seed": seed,
            "model_fitting_performed": False,
        },
        "predefined_baselines": {
            "intensity_strongest_component": "max(IA, IB) predicts IAB",
            "pleasantness_arithmetic": "(PA + PB) / 2 predicts PAB",
            "pleasantness_intensity_weighted": ("(IA*PA + IB*PB) / (IA + IB) predicts PAB"),
            "pleasantness_squared_intensity_weighted": (
                "(IA^2*PA + IB^2*PB) / (IA^2 + IB^2) predicts PAB"
            ),
        },
        "baseline_metrics": {
            "intensity_strongest_component": _metric(
                intensity_strongest,
                observed_intensity,
            ),
            "pleasantness_arithmetic": _metric(
                pleasantness_arithmetic,
                observed_pleasantness,
            ),
            "pleasantness_intensity_weighted": _metric(
                pleasantness_intensity_weighted,
                observed_pleasantness,
            ),
            "pleasantness_squared_intensity_weighted": _metric(
                pleasantness_squared_weighted,
                observed_pleasantness,
            ),
        },
        "paired_bootstrap_comparisons": {
            "pleasantness_arithmetic_minus_squared_rmse": _paired_rmse_bootstrap(
                arithmetic_errors,
                squared_weighted_errors,
                random_source=random.Random(seed),
                iterations=bootstrap_iterations,
            ),
            "pleasantness_intensity_weighted_minus_squared_rmse": (
                _paired_rmse_bootstrap(
                    intensity_weighted_errors,
                    squared_weighted_errors,
                    random_source=random.Random(seed + 1),
                    iterations=bootstrap_iterations,
                )
            ),
        },
        "repeatability": repeatability,
        "interpretation": {
            "intensity_sc_to_repeat_rmse_ratio": _number(intensity_rmse / repeat_iab_rmse),
            "intensity_baseline_status": (
                "SOURCE_INTERNAL_ERROR_APPROXIMATES_IAB_REPEAT_DISAGREEMENT"
            ),
            "pleasantness_baseline_status": (
                "SQUARED_INTENSITY_WEIGHTING_DESCRIPTIVELY_BEST_OF_PREDEFINED_SET"
            ),
            "same_source_reproduction_not_novel": True,
            "cross_study_transportability_tested": False,
            "nonlinear_residual_model_authorized": False,
            "recommended_next_step": (
                "SEEK_INDEPENDENT_SOURCE_TRANSPORTABILITY_OR_CLOSE_PHYSICAL_"
                "STOCK_GATES_BEFORE_PREREGISTERED_LOCAL_REPLICATION"
            ),
        },
        "literature_boundary": {
            "dataset_article_doi": "10.1016/j.dib.2021.107143",
            "same_source_pleasantness_doi": "10.1093/chemse/bjaa020",
            "same_source_intensity_doi": "10.1016/j.foodchem.2021.129483",
            "independent_baseline_context_doi": "10.1093/chemse/bjn026",
            "recent_intensity_preprint_doi": "10.1101/2025.08.08.668954",
            "claim": "SOURCE_INTERNAL_CALIBRATION_ONLY",
        },
        "authorizations": {
            "database_admission_authorized": False,
            "participant_level_inference_authorized": False,
            "nonlinear_model_training_authorized": False,
            "cross_study_generalization_authorized": False,
            "universal_mixture_law_authorized": False,
            "quality_endpoint_claim_authorized": False,
            "formula_prediction_authorized": False,
            "physical_experiment_authorized": False,
            "stock_closure_authorized": False,
            "inventory_mutation_authorized": False,
            "sensory_claim_authorized": False,
            "safety_claim_authorized": False,
            "novelty_claim_authorized": False,
            "publication_claim_authorized": False,
            "release_authorized": False,
        },
    }
    report["scientific_payload_sha256"] = ma2021_baseline_payload_sha256(report)
    return report


__all__ = [
    "MA2021_BASELINE_DECISION",
    "build_ma2021_baseline_benchmark",
    "ma2021_baseline_payload_sha256",
]
