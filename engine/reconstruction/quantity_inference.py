"""Dose inference from rank prior + functional constraints + potency evidence.

Ports PROTOCOL.md Part IV — quantity inference module for perfume
reconstruction.  Converts a ranked material prior into physically plausible
dose ranges by applying perfumer-role corrections, potency-based scaling,
functional clamping, and total reconciliation.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from engine.domain_errors import ReconstructionInputError

# ── Data types ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PotencyCorrection:
    """A multiplicative correction to a material's prior dose based on its
    measured or estimated potency (ODT)."""

    material: str
    factor: float
    justification: str
    source: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PotencyCorrection:
        return cls(
            material=str(data.get("material", "")),
            factor=float(data.get("factor", 1.0)),
            justification=str(data.get("justification", "")),
            source=str(data.get("source", "")),
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FunctionalConstraint:
    """Upper / lower dose bounds and a required OAV floor for a material
    playing a specific functional role in the composition."""

    material: str
    role: str
    min_dose: float = 0.0
    max_dose: float = 0.0
    required_oav: float = 0.0
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FunctionalConstraint:
        return cls(
            material=str(data.get("material", "")),
            role=str(data.get("role", "")),
            min_dose=float(data.get("min_dose", 0.0)),
            max_dose=float(data.get("max_dose", 0.0)),
            required_oav=float(data.get("required_oav", 0.0)),
            notes=str(data.get("notes", "")),
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DoseRange:
    """A dose estimate expressed as a median with 5th and 95th percentiles."""

    median: float
    p05: float
    p95: float
    unit: str = "uL"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DoseRange:
        return cls(
            median=float(data.get("median", 0.0)),
            p05=float(data.get("p05", 0.0)),
            p95=float(data.get("p95", 0.0)),
            unit=str(data.get("unit", "uL")),
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Core functions ──────────────────────────────────────────────────────────────


def override_rank_prior(
    prior: dict[str, float],
    constraints: list[FunctionalConstraint],
    corrections: list[PotencyCorrection],
) -> dict[str, float]:
    """Apply potency corrections then functional constraints to a rank prior.

    Parameters
    ----------
    prior:
        Material → dose (µL) mapping from the rank-prior step.
    constraints:
        Functional bounds to clamp doses into.
    corrections:
        Potency multipliers applied *before* clamping.

    Returns
    -------
    Adjusted dose dict with the same keys as *prior*.
    """
    result: dict[str, float] = {}

    # 1. Build lookup maps for O(1) access.
    correction_map: dict[str, float] = {}
    for c in corrections:
        correction_map[c.material] = c.factor

    constraint_map: dict[str, FunctionalConstraint] = {}
    for c in constraints:
        constraint_map[c.material] = c

    # 2. Apply corrections then constraints.
    for mat, dose in prior.items():
        adjusted = dose

        # Potency correction (multiplicative).
        factor = correction_map.get(mat)
        if factor is not None:
            adjusted *= factor

        # Functional constraint (clamp).
        fc = constraint_map.get(mat)
        if fc is not None:
            if fc.min_dose > 0.0 and adjusted < fc.min_dose:
                adjusted = fc.min_dose
            if fc.max_dose > 0.0 and adjusted > fc.max_dose:
                adjusted = fc.max_dose

        result[mat] = adjusted

    return result


def functional_correction(
    material: str,
    role: str,
    sensory_context: str,  # noqa: ARG001
) -> float:
    """Return a dose adjustment factor based on the material's perfumer role.

    Parameters
    ----------
    material:
        Material name (informational, not used in the lookup).
    role:
        Perfumer-function label (see mapping below).
    sensory_context:
        Free-text sensory context (reserved for future ML use).

    Returns
    -------
    Multiplicative factor to apply to the prior dose.
    """
    _ROLE_FACTORS: dict[str, float] = {
        "radiance amplifier": 1.3,
        "projection musk": 1.2,
        "structural fixative": 0.9,
        "character note": 1.1,
        "trace accent": 0.3,
        "bridge": 0.7,
        "volume builder": 1.0,
        "skin effect": 0.5,
        "diffusion anchor": 0.8,
    }
    return _ROLE_FACTORS.get(role, 1.0)


def potency_correction(material: str, odt_air_ppm: float) -> float:
    """Return a dose-reduction factor based on air-phase ODT.

    More potent materials (lower ODT) need less material to achieve the
    same perceptual effect.

    Parameters
    ----------
    material:
        Material name (informational, not used in the lookup).
    odt_air_ppm:
        Odor detection threshold in ppm (v/v in air).

    Returns
    -------
    Multiplicative factor: lower ODT → smaller factor → lower dose.
    """
    if odt_air_ppm < 0.001:
        return 0.05
    if odt_air_ppm < 0.01:
        return 0.1
    if odt_air_ppm < 0.1:
        return 0.3
    if odt_air_ppm < 1.0:
        return 0.5
    if odt_air_ppm < 10.0:
        return 0.8
    if odt_air_ppm < 100.0:
        return 1.0
    return 1.5


def reconcile_total(
    rows: dict[str, float],
    target_total: float,
) -> dict[str, float]:
    """Scale all doses proportionally to hit an exact target total.

    Parameters
    ----------
    rows:
        Material → dose (µL) mapping.
    target_total:
        Desired sum of all doses after scaling (µL).

    Returns
    -------
    New dict with the same keys, each dose scaled by
    ``target_total / current_total``.
    """
    if not rows:
        raise ReconstructionInputError("reconciliation target cannot be empty")
    if not math.isfinite(target_total) or target_total <= 0.0:
        raise ReconstructionInputError(
            f"target total must be finite and positive, got {target_total}"
        )

    current = sum(rows.values())
    if not math.isfinite(current) or current <= 0.0:
        raise ReconstructionInputError(
            f"normalization denominator must be finite and positive, got {current}"
        )

    ratio = target_total / current
    return {mat: dose * ratio for mat, dose in rows.items()}


def mass_balance_track(
    materials: dict[str, tuple[float, str]],
) -> dict[str, float]:
    """Classify each material dose into a mass-balance bucket.

    Parameters
    ----------
    materials:
        Mapping ``{name: (dose_ul, category)}`` where *category* is one of:
        ``"known_quantified"``, ``"semiquantified"``, ``"unidentified"``,
        ``"nonvolatile"``, ``"solvent"``, or ``"unresolved"``.

    Returns
    -------
    Summed dose per category.  Every category present in the input is
    guaranteed to appear in the output (categories absent from input
    default to 0.0).
    """
    buckets: dict[str, float] = {
        "known_quantified": 0.0,
        "semiquantified": 0.0,
        "unidentified": 0.0,
        "nonvolatile": 0.0,
        "solvent": 0.0,
        "unresolved": 0.0,
    }

    for dose, category in materials.values():
        if category in buckets:
            buckets[category] += dose
        else:
            buckets["unresolved"] += dose

    return buckets


__all__ = [
    "DoseRange",
    "FunctionalConstraint",
    "PotencyCorrection",
    "functional_correction",
    "mass_balance_track",
    "override_rank_prior",
    "potency_correction",
    "reconcile_total",
]
