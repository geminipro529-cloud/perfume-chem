"""Power-law rank prior generator for perfume reconstruction.

Ports PROTOCOL.md Part III — soft rank priors.

Core formula:  q_r = B * r^(-p) / Σ(k^(-p) for k=1..N)

where:
    r  = rank (1-indexed)
    N  = number of materials
    B  = total active budget (µL)
    p  = exponent controlling steepness
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from engine.domain_errors import ReconstructionInputError

# ═══════════════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class RankPriorConfig:
    """Configuration for a power-law rank prior.

    Parameters
    ----------
    N : int
        Number of materials (default 70).
    B : float
        Total active budget in µL (default 4500.0).
    p : float
        Power-law exponent (default 0.70).
    label : str
        Human-readable label for this preset.
    """

    N: int = 70
    B: float = 4500.0
    p: float = 0.70
    label: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RankPriorConfig:
        return cls(
            N=int(data.get("N", 70)),
            B=float(data.get("B", 4500.0)),
            p=float(data.get("p", 0.70)),
            label=str(data.get("label", "")),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "N": self.N,
            "B": round(float(self.B), 2),
            "p": round(float(self.p), 4),
            "label": self.label,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Result
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class RankPriorResult:
    """Result of applying a rank prior to an ordered material list.

    Parameters
    ----------
    config : RankPriorConfig
        The configuration used.
    prior : dict[str, float]
        Mapping from material name to allocated dose (µL).
    total : float
        Sum of all prior doses — should match config.B within floating
        tolerance.
    """

    config: RankPriorConfig
    prior: dict[str, float] = field(default_factory=dict)
    total: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RankPriorResult:
        raw_config = data.get("config")
        if isinstance(raw_config, dict):
            config: RankPriorConfig = RankPriorConfig.from_dict(raw_config)
        elif isinstance(raw_config, RankPriorConfig):
            config = raw_config
        else:
            config = RankPriorConfig()
        return cls(
            config=config,
            prior=dict(data.get("prior", {})),
            total=float(data.get("total", 0.0)),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.as_dict(),
            "prior": dict(self.prior),
            "total": round(float(self.total), 4),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Presets
# ═══════════════════════════════════════════════════════════════════════════════

PRESETS: dict[str, RankPriorConfig] = {
    "FLAT": RankPriorConfig(N=70, B=4500.0, p=0.40, label="FLAT"),
    "MEDIUM": RankPriorConfig(N=70, B=4500.0, p=0.70, label="MEDIUM"),
    "STEEP": RankPriorConfig(N=70, B=4500.0, p=1.00, label="STEEP"),
    "GREEN_HIGH": RankPriorConfig(N=70, B=4500.0, p=0.65, label="GREEN_HIGH"),
    "MUSK_HIGH": RankPriorConfig(N=70, B=4500.0, p=0.65, label="MUSK_HIGH"),
    "SIGNATURE_HIGH": RankPriorConfig(N=70, B=4500.0, p=0.80, label="SIGNATURE_HIGH"),
}


# ═══════════════════════════════════════════════════════════════════════════════
# Core generator
# ═══════════════════════════════════════════════════════════════════════════════


def generate_soft_rank_prior(
    material_names: list[str],
    config: RankPriorConfig,
) -> RankPriorResult:
    """Compute a power-law rank prior for an ordered list of materials.

    Parameters
    ----------
    material_names : list[str]
        Ordered material names — rank 1 first, rank N last.
    config : RankPriorConfig
        Configuration (N, B, p).

    Returns
    -------
    RankPriorResult
        Prior with per-material doses and verified total.
    """
    if config.N <= 0:
        raise ReconstructionInputError(f"N must be positive, got {config.N}")
    if not material_names:
        raise ReconstructionInputError("material_names cannot be empty")
    if not math.isfinite(config.B) or config.B <= 0:
        raise ReconstructionInputError(
            f"total budget must be finite and positive, got {config.B}"
        )

    N = config.N
    B = config.B
    p = config.p

    # Compute normalisation denominator Σ(k^(-p) for k=1..N)
    denom = sum(math.pow(float(k), -p) for k in range(1, N + 1))
    if not math.isfinite(denom) or denom <= 0:
        raise ReconstructionInputError(
            f"normalization denominator must be finite and positive, got {denom}"
        )

    prior: dict[str, float] = {}
    for rank, name in enumerate(material_names, start=1):
        if rank > N:
            break
        q_r = B * math.pow(float(rank), -p) / denom
        prior[name] = round(q_r, 4)

    total = sum(prior.values())

    return RankPriorResult(config=config, prior=prior, total=round(total, 4))


# ═══════════════════════════════════════════════════════════════════════════════
# Multi-preset generator
# ═══════════════════════════════════════════════════════════════════════════════


def generate_candidate_families(
    material_names: list[str],
) -> list[RankPriorResult]:
    """Apply every preset to the same ordered material list.

    Parameters
    ----------
    material_names : list[str]
        Ordered material names — rank 1 first, rank N last.

    Returns
    -------
    list[RankPriorResult]
        One result per preset, in PRESETS insertion order.
    """
    if not material_names:
        raise ReconstructionInputError("candidate roster cannot be empty")

    results: list[RankPriorResult] = []
    N = len(material_names)
    for config in PRESETS.values():
        adapted = RankPriorConfig(N=N, B=config.B, p=config.p, label=config.label)
        results.append(generate_soft_rank_prior(material_names, adapted))
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════════════════


def validate_prior_monotonicity(result: RankPriorResult) -> bool:
    """Check that higher-ranked materials have >= amounts than lower-ranked.

    The power-law prior is strictly decreasing in rank, so this should
    always return True for a correctly computed prior.  Returns False if
    any adjacent pair violates non-increasing order.

    Parameters
    ----------
    result : RankPriorResult
        The prior result to validate.

    Returns
    -------
    bool
        True if the prior is non-increasing (monotonic decreasing).
    """
    amounts = list(result.prior.values())
    for i in range(len(amounts) - 1):
        if amounts[i] < amounts[i + 1] - 1e-9:
            return False
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# Reordering
# ═══════════════════════════════════════════════════════════════════════════════


def reorder_prior_by_oav(
    prior: dict[str, float],
    oav_map: dict[str, float],
) -> list[tuple[str, float, float]]:
    """Reorder a prior by OAV descending.

    Parameters
    ----------
    prior : dict[str, float]
        Material name → allocated dose (µL).
    oav_map : dict[str, float]
        Material name → OAV value.

    Returns
    -------
    list[tuple[str, float, float]]
        List of (name, prior_dose, oav) sorted by OAV descending.
        Materials not found in *oav_map* are assigned OAV = 0.0.
    """
    items: list[tuple[str, float, float]] = []
    for name, dose in prior.items():
        oav = oav_map.get(name, 0.0)
        items.append((name, dose, oav))
    items.sort(key=lambda x: x[2], reverse=True)
    return items
