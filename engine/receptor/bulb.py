"""Olfactory bulb / glomerular layer.

Inputs : per-OR activation vector  R = {OR_gene: R_k ∈ [0,1]}
Outputs: glomerular vector after lateral inhibition + scalar metrics
         (novelty score across time, configural-blur flag for >3 dominant
         streams per Laing's analytic limit).
"""
from __future__ import annotations

import math
from typing import Mapping, Sequence

from .binding import ORArray


def glomerular_vector(
    occupancy: Mapping[str, float],
    array: ORArray | None = None,
    *,
    inhibition_strength: float = 0.15,
) -> dict[str, float]:
    """Apply lateral inhibition: each OR is suppressed by the mean of its peers.
    Simple ring-uniform kernel (more sophisticated kernels can key off
    structural similarity once OR data is filled in)."""
    arr = array or ORArray()
    n = len(arr.or_genes)
    if n == 0:
        return {}
    raw = [max(0.0, occupancy.get(g, 0.0)) for g in arr.or_genes]
    mean = sum(raw) / n
    out = {}
    for g, v in zip(arr.or_genes, raw):
        out[g] = max(0.0, v - inhibition_strength * mean)
    return out


def novelty_score(prev: Mapping[str, float], cur: Mapping[str, float]) -> float:
    """Cosine distance between successive glomerular vectors ∈ [0, 2].

    1 = orthogonal, 0 = identical, 2 = anti-correlated (rare).
    """
    keys = set(prev) | set(cur)
    pa = [prev.get(k, 0.0) for k in keys]
    pb = [cur.get(k, 0.0) for k in keys]
    na = math.sqrt(sum(x * x for x in pa))
    nb = math.sqrt(sum(x * x for x in pb))
    if na <= 0 or nb <= 0:
        return 0.0
    dot = sum(a * b for a, b in zip(pa, pb))
    return 1.0 - dot / (na * nb)


def configural_blur(occupancy: Mapping[str, float],
                    threshold: float = 0.4,
                    laing_limit: int = 3) -> bool:
    """Returns True when more than `laing_limit` ORs are simultaneously
    above `threshold` — the Laing analytic limit, signalling gestalt mode.
    """
    n_dom = sum(1 for v in occupancy.values() if v >= threshold)
    return n_dom > laing_limit


def temporal_novelty(traj: Sequence[Mapping[str, float]]) -> list[float]:
    """Frame-by-frame novelty for a list of glomerular vectors."""
    if len(traj) < 2:
        return [0.0] * len(traj)
    out = [0.0]
    for i in range(1, len(traj)):
        out.append(novelty_score(traj[i - 1], traj[i]))
    return out


if __name__ == "__main__":
    arr = ORArray()
    R1 = {g: 0.1 for g in arr.or_genes}
    R1["OR1A1"] = 0.9   # bright citrus dominant
    g1 = glomerular_vector(R1, arr)
    R2 = {g: 0.3 for g in arr.or_genes}
    R2["OR_WD"] = 0.85  # wood now dominant
    g2 = glomerular_vector(R2, arr)
    print("novelty t1→t2:", novelty_score(g1, g2))
    print("blur t1:", configural_blur(R1))
    print("blur t2 (everything 0.3+):", configural_blur(R2, threshold=0.25))
