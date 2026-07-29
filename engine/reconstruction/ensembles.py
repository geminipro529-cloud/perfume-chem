"""Candidate ensemble generation for perfume reconstruction.

Ports FROM_SCRATCH_RECONSTRUCTION_ADDENDUM.md.  Generates multiple formula
candidates from the same evidence, varying parameters to produce an ensemble
that spans the uncertainty space.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from engine.domain_errors import ReconstructionInputError

# ---------------------------------------------------------------------------
# Authority label constants — mirrors engine/target/formula.py
# ---------------------------------------------------------------------------

TIER_0_NOTE_INSPIRED = "note-inspired reconstruction"
TIER_1_DOCUMENTARY_FUNCTIONAL_HYPOTHESIS = "documentary functional hypothesis"
TIER_2_ENSEMBLE_CENTER = "sensory recombination hypothesis"
TIER_3_ANALYTICALLY_CONSTRAINED = "analytically constrained"
TIER_4_QUANTITATIVELY_CALIBRATED = "quantitatively calibrated"
TIER_5_BLIND_SENSORY_VALIDATED = "blind sensory validated"
TIER_6_AUTHENTICATED_FORMULA = "authenticated formula"

# ---------------------------------------------------------------------------
# Rank prior import — fall back to inline if unavailable
# ---------------------------------------------------------------------------

try:
    from engine.reconstruction.rank_prior import (
        PRESETS,  # noqa: F401 — availability check
        RankPriorConfig,
        generate_soft_rank_prior,
    )

    _HAS_RANK_PRIOR = True
except ImportError:  # pragma: no cover
    _HAS_RANK_PRIOR = False


def _inline_rank_prior(
    ordered_materials: list[str],
    total_budget: float,
    p: float,
    material_count: int,
) -> dict[str, float]:
    """Inline power-law rank prior when ``rank_prior`` module is unavailable.

    ``q_r = B * pow(r, -p) / sum(pow(i, -p) for i in range(1, N+1))``
    """
    if material_count <= 0:
        raise ReconstructionInputError(
            f"N must be positive, got {material_count}"
        )
    if not ordered_materials:
        raise ReconstructionInputError("ordered_materials cannot be empty")
    if not math.isfinite(total_budget) or total_budget <= 0:
        raise ReconstructionInputError(
            f"total budget must be finite and positive, got {total_budget}"
        )

    denom = sum(
        math.pow(float(k), -p) for k in range(1, material_count + 1)
    )
    if not math.isfinite(denom) or denom <= 0:
        raise ReconstructionInputError(
            f"normalization denominator must be finite and positive, got {denom}"
        )
    prior: dict[str, float] = {}
    for rank, name in enumerate(ordered_materials, start=1):
        if rank > material_count:
            break
        q_r = total_budget * math.pow(float(rank), -p) / denom
        prior[name] = round(q_r, 4)
    return prior


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CandidateFamily:
    """One candidate formula in the ensemble.

    Parameters
    ----------
    name : str
        Human-readable name for this candidate (e.g. the perfume name).
    variant : str
        Ensemble variant key — one of ``flat``, ``medium``, ``steep``,
        ``green_high``, ``musk_high``, ``signature_high``.
    rank_prior : dict[str, float]
        Material name → allocated dose (µL) from the rank prior.
    adjusted_doses : dict[str, float]
        Material name → final adjusted dose (µL) after any post-processing.
    authority_label : str
        Authority tier constant.
    scores : dict[str, float]
        Scoring axes (e.g. ``{"balance": 0.85, "projection": 0.72}``).
    """

    name: str
    variant: str
    rank_prior: dict[str, float] = field(default_factory=dict)
    adjusted_doses: dict[str, float] = field(
        default_factory=dict
    )  # NOTE: Always initialized as rank_prior copy — post-processing expected by consumer
    authority_label: str = TIER_2_ENSEMBLE_CENTER
    scores: dict[str, float] = field(default_factory=dict)  # FUTURE: scoring engine integration

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CandidateFamily:
        return cls(
            name=str(data.get("name", "")),
            variant=str(data.get("variant", "")),
            rank_prior=dict(data.get("rank_prior", {})),
            adjusted_doses=dict(data.get("adjusted_doses", {})),
            authority_label=str(data.get("authority_label", TIER_2_ENSEMBLE_CENTER)),
            scores=dict(data.get("scores", {})),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "variant": self.variant,
            "rank_prior": dict(self.rank_prior),
            "adjusted_doses": dict(self.adjusted_doses),
            "authority_label": self.authority_label,
            "scores": dict(self.scores),
        }


@dataclass(frozen=True, slots=True)
class AuthorityVector:
    # NOTE: Redundant with engine.target.formula.AuthorityVector — prefer that import.
    """Tracks authority per dimension — NEVER averaged into one number.

    Parameters
    ----------
    identity : float
        Confidence in material identity (0.0–1.0).
    quantity : float
        Confidence in material quantity (0.0–1.0).
    grade : float
        Confidence in material grade / quality (0.0–1.0).
    natural_lot : float
        Confidence in natural lot traceability (0.0–1.0).
    matrix : float
        Confidence in matrix / formulation context (0.0–1.0).
    headspace : float
        Confidence in headspace / GC-MS evidence (0.0–1.0).
    sensory : float
        Confidence in sensory validation (0.0–1.0).
    inventory : float
        Confidence in inventory match (0.0–1.0).
    safety : float
        Confidence in safety / IFRA compliance (0.0–1.0).
    release : float
        Confidence in release / production readiness (0.0–1.0).
    """

    identity: float = 0.0
    quantity: float = 0.0
    grade: float = 0.0
    natural_lot: float = 0.0
    matrix: float = 0.0
    headspace: float = 0.0
    sensory: float = 0.0
    inventory: float = 0.0
    safety: float = 0.0
    release: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuthorityVector:
        return cls(
            identity=float(data.get("identity", 0.0)),
            quantity=float(data.get("quantity", 0.0)),
            grade=float(data.get("grade", 0.0)),
            natural_lot=float(data.get("natural_lot", 0.0)),
            matrix=float(data.get("matrix", 0.0)),
            headspace=float(data.get("headspace", 0.0)),
            sensory=float(data.get("sensory", 0.0)),
            inventory=float(data.get("inventory", 0.0)),
            safety=float(data.get("safety", 0.0)),
            release=float(data.get("release", 0.0)),
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Ensemble generation
# ---------------------------------------------------------------------------

# Variant definitions: (variant_key, exponent_p)
_VARIANT_SPECS: list[tuple[str, float]] = [
    ("flat", 0.40),
    ("medium", 0.70),
    ("steep", 1.00),
    ("green_high", 0.65),
    ("musk_high", 0.65),
    ("signature_high", 0.80),
]


def generate_ensemble(
    ordered_materials: list[str],
    total_budget: float = 4500.0,
    N: int = 70,  # noqa: N803 - public mathematical compatibility
    authority_label: str = TIER_2_ENSEMBLE_CENTER,
) -> list[CandidateFamily]:
    """Generate 6 candidate families from the same ordered material list.

    Each family uses a different power-law exponent to produce a distinct
    dose distribution across the ranked materials.

    Parameters
    ----------
    ordered_materials : list[str]
        Materials ordered by importance (rank 1 = most important).
    total_budget : float
        Total active budget in µL (default 4500.0).
    N : int
        Number of materials to allocate (default 70).
    authority_label : str
        Authority tier for all generated candidates.

    Returns
    -------
    list[CandidateFamily]
        Six ``CandidateFamily`` objects, one per variant.
    """
    if not ordered_materials:
        raise ReconstructionInputError("ordered_materials cannot be empty")
    if N <= 0:
        raise ReconstructionInputError(f"N must be positive, got {N}")
    if not math.isfinite(total_budget) or total_budget <= 0:
        raise ReconstructionInputError(
            f"total budget must be finite and positive, got {total_budget}"
        )

    families: list[CandidateFamily] = []

    for variant_key, p in _VARIANT_SPECS:
        if _HAS_RANK_PRIOR:
            config = RankPriorConfig(N=N, B=total_budget, p=p, label=variant_key)
            result = generate_soft_rank_prior(ordered_materials, config)
            prior = result.prior
        else:
            prior = _inline_rank_prior(ordered_materials, total_budget, p, N)

        family = CandidateFamily(
            name="",
            variant=variant_key,
            rank_prior=prior,
            adjusted_doses=dict(prior),
            authority_label=authority_label,
        )
        families.append(family)

    return families


# ---------------------------------------------------------------------------
# Sensory test plan
# ---------------------------------------------------------------------------


def recombination_test(
    center: CandidateFamily,
    low_variants: list[CandidateFamily],
    high_variants: list[CandidateFamily],
) -> list[str]:
    """Return a sensory test plan as a list of instructions.

    Parameters
    ----------
    center : CandidateFamily
        The center / reference candidate.
    low_variants : list[CandidateFamily]
        Variants dosed below the center (e.g. 50 %).
    high_variants : list[CandidateFamily]
        Variants dosed above the center (e.g. 150 %).

    Returns
    -------
    list[str]
        Ordered list of test instructions.
    """
    plan: list[str] = []

    plan.append(f"Prepare center formula: {center.name or center.variant}")

    for lv in low_variants:
        plan.append(f"Prepare low variant {lv.variant} at 50 % dose of center")

    for hv in high_variants:
        plan.append(f"Prepare high variant {hv.variant} at 150 % dose of center")

    plan.append("Code all samples with random 3-letter codes")
    plan.append("Evaluate at 0min, 5min, 30min, 2hr, 4hr")

    return plan


# ---------------------------------------------------------------------------
# Uncertainty scaling
# ---------------------------------------------------------------------------


def scale_uncertainty_to_ensemble(
    base_doses: dict[str, float],
    parameter_uncertainties: dict[str, tuple[float, float]],
) -> list[dict[str, float]]:
    """Create low/high dose variants from per-material uncertainty intervals.

    For each material with a ``(p05, p95)`` uncertainty tuple, the low
    variant uses the 5th-percentile dose and the high variant uses the
    95th-percentile dose.  Materials without an uncertainty entry keep their
    base dose unchanged.

    Parameters
    ----------
    base_doses : dict[str, float]
        Material name → base dose (µL).
    parameter_uncertainties : dict[str, tuple[float, float]]
        Material name → ``(p05, p95)`` dose bounds.

    Returns
    -------
    list[dict[str, float]]
        Two dicts: ``[low_variant, high_variant]``.
    """
    low: dict[str, float] = {}
    high: dict[str, float] = {}

    for material, base in base_doses.items():
        if material in parameter_uncertainties:
            p05, p95 = parameter_uncertainties[material]
            low[material] = p05
            high[material] = p95
        else:
            low[material] = base
            high[material] = base

    return [low, high]


__all__ = [
    "AuthorityVector",
    "CandidateFamily",
    "TIER_0_NOTE_INSPIRED",
    "TIER_1_DOCUMENTARY_FUNCTIONAL_HYPOTHESIS",
    "TIER_2_ENSEMBLE_CENTER",
    "TIER_3_ANALYTICALLY_CONSTRAINED",
    "TIER_4_QUANTITATIVELY_CALIBRATED",
    "TIER_5_BLIND_SENSORY_VALIDATED",
    "TIER_6_AUTHENTICATED_FORMULA",
    "generate_ensemble",
    "recombination_test",
    "scale_uncertainty_to_ensemble",
]
