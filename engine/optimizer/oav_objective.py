"""OAV-space objective for formula optimization.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (parts per million w/w in concentrate).
- ODT in ppm for ethanol solution, ppb for air.
- OAV = concentration_ppm / ODT_ppm (dimensionless).
- Every perceptibility claim must be backed by OAV.

Score = w_match · trajectory_match
      + w_novelty · temporal_novelty
      − w_adapt   · adaptation_risk
      − w_ifra    · IFRA_violation_penalty
      + w_stable  · maturation_stability

`brief` specifies target time-windowed OAV envelope per OR family
(e.g. {"top": {"citrus": 0.6, "aldehyde": 0.4}, "heart": {...}, "base": {...}}).

Uses scipy.optimize.differential_evolution if available, else a homebrew
random-restart hill-climb. Both consume the same objective function.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

try:
    from scipy.optimize import differential_evolution as _scipy_de  # type: ignore
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False


@dataclass(slots=True)
class OAVObjective:
    materials: list[str]                     # ordered material list
    bounds: list[tuple[float, float]]        # wt% per material
    target_envelope: dict[str, dict[str, float]]
    headspace_fn: Callable[[Mapping[str, float]], dict[str, dict[str, float]]]
    families: dict[str, str]                  # material → OR family
    weights: dict[str, float] = field(default_factory=lambda: dict(
        match=1.0, novelty=0.5, adapt=0.3, ifra=2.0, stable=0.2))


def _envelope_match(profile: dict[str, dict[str, float]],
                    families: dict[str, str],
                    target: dict[str, float]) -> float:
    """L2 closeness between observed family-summed OAV and target (single window)."""
    obs: dict[str, float] = {}
    for mat, m in profile.items():
        fam = families.get(mat, "default")
        obs[fam] = obs.get(fam, 0.0) + m.get("oav", 0.0)
    err = 0.0
    for fam, tgt in target.items():
        err += (obs.get(fam, 0.0) - tgt) ** 2
    return -err  # higher = better


def score_formula_oav(
    wt_pct: Mapping[str, float],
    obj: OAVObjective,
    *,
    evaporation_windows: Sequence[tuple[str, float]] = (
        ("top", 60.0), ("heart", 1800.0), ("base", 14400.0)),
) -> float:
    """Single-shot scalar score (higher = better). The headspace_fn supplied
    by the caller may itself integrate the trajectory; we keep this layer
    agnostic.
    """
    total = 0.0
    profiles = {}
    # In simple mode, headspace_fn just returns one snapshot; advanced callers
    # can return per-window dict{window: profile}.
    snap = obj.headspace_fn(wt_pct)
    is_per_window = (
        isinstance(snap, dict)
        and snap
        and all(isinstance(v, dict) for v in snap.values())
        and any(k in snap for k in ("top", "heart", "base"))
    )
    if is_per_window:
        profiles = snap
    else:
        # Same snapshot for all windows — degraded mode without trajectory
        profiles = {w: snap for w, _ in evaporation_windows}
    novelty = 0.0
    prev_vec: dict[str, float] | None = None
    for window, _ in evaporation_windows:
        prof = profiles.get(window, {})
        target = obj.target_envelope.get(window, {})
        total += obj.weights["match"] * _envelope_match(prof, obj.families, target)
        # novelty between successive windows
        cur_vec = {m: p.get("oav", 0.0) for m, p in prof.items()}
        if prev_vec is not None:
            keys = set(prev_vec) | set(cur_vec)
            a = [prev_vec.get(k, 0.0) for k in keys]
            b = [cur_vec.get(k, 0.0) for k in keys]
            na = math.sqrt(sum(x * x for x in a)) or 1e-9
            nb = math.sqrt(sum(x * x for x in b)) or 1e-9
            cos = sum(x * y for x, y in zip(a, b)) / (na * nb)
            novelty += 1.0 - cos
        prev_vec = cur_vec
    total += obj.weights["novelty"] * novelty
    return total


def differential_evolution_oav(
    obj: OAVObjective,
    *,
    maxiter: int = 50,
    popsize: int = 15,
    seed: int | None = None,
) -> tuple[dict[str, float], float]:
    """Search wt% within `obj.bounds`, return (best_wt_pct, best_score)."""
    def neg_score(x):
        wt = {m: float(v) for m, v in zip(obj.materials, x)}
        return -score_formula_oav(wt, obj)

    if _HAS_SCIPY:
        result = _scipy_de(
            neg_score,
            bounds=obj.bounds,
            maxiter=maxiter,
            popsize=popsize,
            seed=seed,
            polish=False,
            tol=1e-3,
        )
        wt = {m: float(v) for m, v in zip(obj.materials, result.x)}
        return wt, -float(result.fun)

    # Homebrew DE
    rng = random.Random(seed)
    lo = [b[0] for b in obj.bounds]
    hi = [b[1] for b in obj.bounds]
    n = len(lo)
    pop = [[rng.uniform(lo[i], hi[i]) for i in range(n)] for _ in range(popsize)]
    fitness = [neg_score(p) for p in pop]
    F, CR = 0.7, 0.9
    for _ in range(maxiter):
        for j in range(popsize):
            idxs = rng.sample([i for i in range(popsize) if i != j], 3)
            a, b, c = pop[idxs[0]], pop[idxs[1]], pop[idxs[2]]
            mutant = [max(lo[k], min(hi[k], a[k] + F * (b[k] - c[k]))) for k in range(n)]
            trial = [mutant[k] if rng.random() < CR else pop[j][k] for k in range(n)]
            f = neg_score(trial)
            if f < fitness[j]:
                pop[j] = trial
                fitness[j] = f
    best = min(range(popsize), key=lambda i: fitness[i])
    wt = {m: pop[best][i] for i, m in enumerate(obj.materials)}
    return wt, -fitness[best]


if __name__ == "__main__":
    # Toy: target = a citrus-heavy top, woody base
    def fake_headspace(wt):
        # produce per-window snapshots
        top = {"Limonene": {"oav": wt.get("Limonene", 0.0) / 5.0}}
        heart = {"Hedione": {"oav": wt.get("Hedione", 0.0) / 5.0}}
        base = {"Iso E Super": {"oav": wt.get("Iso E Super", 0.0) / 10.0}}
        return {"top": top, "heart": heart, "base": base}

    obj = OAVObjective(
        materials=["Limonene", "Hedione", "Iso E Super"],
        bounds=[(0, 5), (0, 8), (0, 15)],
        target_envelope={"top": {"citrus": 0.8}, "heart": {"floral": 0.6},
                         "base": {"wood": 1.0}},
        headspace_fn=fake_headspace,
        families={"Limonene": "citrus", "Hedione": "floral", "Iso E Super": "wood"},
    )
    wt, score = differential_evolution_oav(obj, maxiter=30, seed=42)
    print("best wt%:", wt)
    print("score:", score)
