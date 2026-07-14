"""Stage 6 — IEC (Interactive Evolutionary Computation) Iteration Loop.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
**RULE 3: Optimize for the name, not just the numbers.**

The IEC loop runs after Stage 5 produces a candidate formula. It optimizes the
material doses and selection using sequential Differential Evolution (Fukumoto
2014), with CMA-ES as a fallback if DE stalls.

**Two modes:**
  - Auto (default): pipeline scores candidates via the 10-axis scorer
  - Human-in-loop (--interactive): user scores 5-8 candidates per generation;
    DE operator uses those scores as fitness

**Algorithm:**
  - Population: 8 candidates
  - Generations: 10 (cap)
  - Operator: DE/rand/1/bin
  - Fitness: 0.6 * hedonic + 0.2 * oav_pyramid_match + 0.1 * novelty + 0.1 * ifra_clean
  - CMA-ES fallback: switch if no improvement in 3 generations
  - Roudnitska stop: when no improvement > 0.5% in 3 generations, or max gens reached

Re-exports the existing iteration-protocol logic from
`future_modules.iteration_protocol` so the pipeline can import from the
canonical `engine.orchestration` namespace. The DE algorithm itself is
implemented inline below (Phase 4 will be the production-grade version).

**Inspired by:**
- Fukumoto et al. (CEC 2010, 2014, 2015) — Interactive Differential Evolution
  for fragrance composition with Aromageur
- Bell 2024, Kumar 2024 — CMA-ES for OV-vector optimization
- Roudnitska Le Parfum (1980) — "fortunate proportions" + Roudnitska stop

**Reference:** docs/ATELIER_PIPELINE_PLAN.md, Stage 6.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Sequence

from future_modules.iteration_protocol import (  # type: ignore[import-not-found]
    EVALUATION_DISTANCES,
    ITERATION_PROTOCOL,
    OVERDOSE_STRATEGIES,
    OverdoseStrategy,
    accelerated_aging_equivalent,
    evaluate_stage_compliance,
    format_iteration_status,
    get_all_stages,
    get_evaluation_distances,
    get_maceration_milestone,
    get_next_stage,
    get_overdose_strategy,
    get_stage_by_day,
    get_stage_by_name,
    roudnitska_test,
)


@dataclass(frozen=True, slots=True)
class IECHyperparameters:
    """Hyperparameters for the sequential DE loop."""

    population_size: int = 8
    max_generations: int = 10
    crossover_rate: float = 0.9
    mutation_factor: float = 0.5
    stall_generations: int = 3
    roudnitska_min_improvement: float = 0.005
    novelty_weight: float = 0.10
    pyramid_weight: float = 0.20
    hedonic_weight: float = 0.60
    ifra_weight: float = 0.10
    seed: int = 0


@dataclass(slots=True)
class IECHistory:
    """Per-generation trace of the IEC run."""

    best_fitness_per_gen: list[float] = field(default_factory=list)
    best_candidate_per_gen: list[list[float]] = field(default_factory=list)
    stagnation_count: int = 0
    final_best_fitness: float = 0.0
    final_best_candidate: list[float] | None = None
    used_cma_es: bool = False


def de_rand_1_bin(
    population: list[list[float]],
    fitness: list[float],
    bounds: list[tuple[float, float]],
    crossover_rate: float,
    mutation_factor: float,
    rng: random.Random,
) -> list[list[float]]:
    """One iteration of DE/rand/1/bin (Storn & Price).

    Args:
        population: list of candidate vectors (each is a list of floats)
        fitness: parallel list of fitness values (higher = better)
        bounds: (lo, hi) per dimension
        crossover_rate: CR ∈ [0, 1]
        mutation_factor: F ∈ [0, 2]
        rng: random.Random for reproducibility

    Returns:
        trial population of the same shape
    """
    n = len(population)
    dim = len(population[0])
    trials: list[list[float]] = []
    for i in range(n):
        candidates = [j for j in range(n) if j != i]
        a, b, c = rng.sample(candidates, 3)
        j_rand = rng.randrange(dim)
        trial = []
        for j in range(dim):
            if rng.random() < crossover_rate or j == j_rand:
                val = population[a][j] + mutation_factor * (population[b][j] - population[c][j])
            else:
                val = population[i][j]
            lo, hi = bounds[j]
            val = max(lo, min(hi, val))
            trial.append(val)
        trials.append(trial)
    return trials


def cma_es_step(
    mean: list[float],
    sigma: float,
    bounds: list[tuple[float, float]],
    rng: random.Random,
    population_size: int = 8,
) -> list[list[float]]:
    """One CMA-ES sampling step (minimal implementation; full CMA-ES in Phase 4).

    Samples `population_size` candidates from N(mean, sigma*I) and clips to bounds.
    """
    candidates: list[list[float]] = []
    for _ in range(population_size):
        cand = [rng.gauss(mean[j], sigma) for j in range(len(mean))]
        for j, (lo, hi) in enumerate(bounds):
            cand[j] = max(lo, min(hi, cand[j]))
        candidates.append(cand)
    return candidates


def iec_optimize(
    initial_candidate: list[float],
    bounds: list[tuple[float, float]],
    fitness_fn: Callable[[list[float]], float],
    hyperparams: IECHyperparameters | None = None,
) -> IECHistory:
    """Run sequential DE (with CMA-ES fallback) to optimize a candidate.

    Args:
        initial_candidate: starting dose vector (centered on initial population)
        bounds: (lo, hi) per dimension
        fitness_fn: callable that scores a candidate (higher = better)
        hyperparams: optional override of DE/CMA-ES settings

    Returns:
        IECHistory with per-generation trace + final best candidate
    """
    hp = hyperparams or IECHyperparameters()
    rng = random.Random(hp.seed)
    dim = len(initial_candidate)
    lo, hi = zip(*bounds, strict=True)
    span = [(hi[j] - lo[j]) for j in range(dim)]

    # Initialize population: 1 = initial, others = uniform within bounds
    population: list[list[float]] = [list(initial_candidate)]
    for _ in range(hp.population_size - 1):
        population.append([rng.uniform(lo[j], hi[j]) for j in range(dim)])

    fitness = [fitness_fn(p) for p in population]
    history = IECHistory()

    for gen in range(hp.max_generations):
        trials = de_rand_1_bin(population, fitness, bounds, hp.crossover_rate, hp.mutation_factor, rng)
        trial_fitness = [fitness_fn(t) for t in trials]

        # Greedy selection
        for i in range(hp.population_size):
            if trial_fitness[i] > fitness[i]:
                population[i] = trials[i]
                fitness[i] = trial_fitness[i]

        best_idx = max(range(hp.population_size), key=lambda i: fitness[i])
        history.best_fitness_per_gen.append(fitness[best_idx])
        history.best_candidate_per_gen.append(list(population[best_idx]))

        # Stagnation check
        if gen > 0 and fitness[best_idx] <= history.best_fitness_per_gen[-2] + hp.roudnitska_min_improvement:
            history.stagnation_count += 1
        else:
            history.stagnation_count = 0

        if history.stagnation_count >= hp.stall_generations and not history.used_cma_es:
            # Fall back to CMA-ES for the remaining generations
            history.used_cma_es = True
            mean = list(population[best_idx])
            sigma = sum(span) / (10.0 * dim)
            cma_population = cma_es_step(mean, sigma, bounds, rng, hp.population_size)
            cma_fitness = [fitness_fn(c) for c in cma_population]
            for i in range(hp.population_size):
                if cma_fitness[i] > fitness[i]:
                    population[i] = cma_population[i]
                    fitness[i] = cma_fitness[i]
            best_idx = max(range(hp.population_size), key=lambda i: fitness[i])
            history.stagnation_count = 0

        if history.stagnation_count >= hp.stall_generations and history.used_cma_es:
            # Roudnitska stop: no improvement after CMA-ES fallback either
            break

    history.final_best_fitness = fitness[best_idx]
    history.final_best_candidate = list(population[best_idx])
    return history


__all__ = [
    "EVALUATION_DISTANCES",
    "ITERATION_PROTOCOL",
    "OVERDOSE_STRATEGIES",
    "OverdoseStrategy",
    "IECHyperparameters",
    "IECHistory",
    "accelerated_aging_equivalent",
    "cma_es_step",
    "de_rand_1_bin",
    "evaluate_stage_compliance",
    "format_iteration_status",
    "get_all_stages",
    "get_evaluation_distances",
    "get_maceration_milestone",
    "get_next_stage",
    "get_overdose_strategy",
    "get_stage_by_day",
    "get_stage_by_name",
    "iec_optimize",
    "roudnitska_test",
]
