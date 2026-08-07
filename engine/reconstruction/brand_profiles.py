"""Brand/era adaptation profiles for perfume reconstruction.

Ports BRAND_ERA_ADAPTATION.md + brand_era_profiles.json.

Each profile encodes the reconstruction strategy for a specific brand or
era, capturing reformulation risk, captive-material priors, natural-
complexity expectations, and socket-strategy preferences.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# Data type
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class BrandProfile:
    """Adaptation profile for a brand or era.

    Parameters
    ----------
    profile_id : str
        Unique identifier for this profile.
    brands : tuple[str, ...]
        Brand names covered by this profile.
    reformulation_risk : str
        Qualitative risk level: ``"low"``, ``"medium"``, ``"high"``,
        ``"very_high"``, or ``"variable"``.
    unknown_captive_prior : float
        Prior probability (0-1) that a material in the formula is a
        captive (proprietary) molecule not available on the open market.
    natural_complexity_prior : float
        Prior probability (0-1) that a material is a complex natural
        extract (EO, absolute, resinoid) rather than a single
        aromachemical.
    negative_space_importance : float
        Importance (0-1) of negative-space reasoning — inferring what
        is *not* present from what *is* present.  High values mean the
        brand relies on omission and transparency.
    default_evaluation_hours : int
        Default number of hours to evaluate the reconstructed formula
        against the target (e.g. 4 for EDP, 8 for extrait).
    protected_blocks : tuple[str, ...]
        Structural blocks (accord names, material groups) that must be
        preserved intact during reconstruction.
    compression_traps : tuple[str, ...]
        Known compression pitfalls — materials or accords that are
        easily over-compressed during reconstruction.
    socket_strategy : str
        Strategy for the module socket: ``"tight"``, ``"loose"``,
        ``"balanced"``, ``"aggressive"``, or ``"conservative"``.
    """

    profile_id: str
    brands: tuple[str, ...]
    reformulation_risk: str  # FUTURE: used by authority vector for risk adjustment
    unknown_captive_prior: float
    natural_complexity_prior: float
    negative_space_importance: (
        float  # FUTURE: used by negative-space scoring in formulation recommendations
    )
    default_evaluation_hours: int  # FUTURE: used by sensory trial timer defaults
    protected_blocks: tuple[str, ...]  # FUTURE: used by structural chassis derivation
    compression_traps: tuple[
        str, ...
    ]  # FUTURE: used by anti-compression audit for brand-specific patterns
    socket_strategy: str  # FUTURE: used by chassis module envelope construction

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrandProfile:
        return cls(
            profile_id=str(data.get("profile_id", "")),
            brands=tuple(data.get("brands", ())),
            reformulation_risk=str(data.get("reformulation_risk", "")),
            unknown_captive_prior=float(data.get("unknown_captive_prior", 0.0)),
            natural_complexity_prior=float(data.get("natural_complexity_prior", 0.0)),
            negative_space_importance=float(data.get("negative_space_importance", 0.0)),
            default_evaluation_hours=int(data.get("default_evaluation_hours", 4)),
            protected_blocks=tuple(data.get("protected_blocks", ())),
            compression_traps=tuple(data.get("compression_traps", ())),
            socket_strategy=str(data.get("socket_strategy", "")),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "brands": list(self.brands),
            "reformulation_risk": self.reformulation_risk,
            "unknown_captive_prior": round(float(self.unknown_captive_prior), 4),
            "natural_complexity_prior": round(float(self.natural_complexity_prior), 4),
            "negative_space_importance": round(float(self.negative_space_importance), 4),
            "default_evaluation_hours": self.default_evaluation_hours,
            "protected_blocks": list(self.protected_blocks),
            "compression_traps": list(self.compression_traps),
            "socket_strategy": self.socket_strategy,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Pre-loaded profiles
# ═══════════════════════════════════════════════════════════════════════════════

PROFILES: dict[str, BrandProfile] = {
    "ysl_modern_masculine": BrandProfile(
        profile_id="ysl_modern_masculine",
        brands=("YSL", "Yves Saint Laurent"),
        reformulation_risk="high",
        unknown_captive_prior=0.40,
        natural_complexity_prior=0.35,
        negative_space_importance=0.5,
        default_evaluation_hours=4,
        protected_blocks=(
            "woody_amber_base",
            "aromatic_top",
            "signature_accord",
        ),
        compression_traps=(
            "ethyl_maltol_overdose",
            "hedione_crowding",
            "iso_e_super_flattening",
        ),
        socket_strategy="balanced",
    ),
    "prada_clean_iris": BrandProfile(
        profile_id="prada_clean_iris",
        brands=("Prada",),
        reformulation_risk="medium",
        unknown_captive_prior=0.25,
        natural_complexity_prior=0.30,
        negative_space_importance=0.7,
        default_evaluation_hours=4,
        protected_blocks=(
            "iris_accord",
            "clean_musk_base",
            "soapy_aldehydic_top",
        ),
        compression_traps=(
            "ionone_flattening",
            "musk_oversimplification",
        ),
        socket_strategy="tight",
    ),
    "dior_family_differential": BrandProfile(
        profile_id="dior_family_differential",
        brands=("Dior", "Christian Dior"),
        reformulation_risk="high",
        unknown_captive_prior=0.55,
        natural_complexity_prior=0.30,
        negative_space_importance=0.5,
        default_evaluation_hours=4,
        protected_blocks=(
            "family_dna_accord",
            "signature_base",
            "floral_heart",
        ),
        compression_traps=(
            "captive_misassignment",
            "over_compression_of_heart",
        ),
        socket_strategy="conservative",
    ),
    "chanel_era_strict": BrandProfile(
        profile_id="chanel_era_strict",
        brands=("Chanel",),
        reformulation_risk="very_high",
        unknown_captive_prior=0.50,
        natural_complexity_prior=0.35,
        negative_space_importance=0.6,
        default_evaluation_hours=4,
        protected_blocks=(
            "aldehyde_top",
            "iris_violet_accord",
            "chypre_base",
        ),
        compression_traps=(
            "aldehyde_leveling",
            "methyl_ionone_confusion",
            "musk_era_mismatch",
        ),
        socket_strategy="conservative",
    ),
    "amouage_resinous_longform": BrandProfile(
        profile_id="amouage_resinous_longform",
        brands=("Amouage",),
        reformulation_risk="medium",
        unknown_captive_prior=0.25,
        natural_complexity_prior=0.95,
        negative_space_importance=0.3,
        default_evaluation_hours=8,
        protected_blocks=(
            "resinous_incense_core",
            "oud_accord",
            "spice_complex",
        ),
        compression_traps=(
            "resinoid_overcompression",
            "oud_substitution_error",
        ),
        socket_strategy="loose",
    ),
    "guerlain_historical_base": BrandProfile(
        profile_id="guerlain_historical_base",
        brands=("Guerlain",),
        reformulation_risk="very_high",
        unknown_captive_prior=0.20,
        natural_complexity_prior=0.80,
        negative_space_importance=0.5,
        default_evaluation_hours=8,
        protected_blocks=(
            "guerlinade_base",
            "tonka_vanilla_accord",
            "jasmine_rose_heart",
        ),
        compression_traps=(
            "guerlinade_simplification",
            "natural_replacement_error",
        ),
        socket_strategy="conservative",
    ),
    "hermes_transparent_spacing": BrandProfile(
        profile_id="hermes_transparent_spacing",
        brands=("Hermes", "Hermès"),
        reformulation_risk="medium",
        unknown_captive_prior=0.30,
        natural_complexity_prior=0.55,
        negative_space_importance=0.95,
        default_evaluation_hours=4,
        protected_blocks=(
            "transparent_citrus_top",
            "mineral_accord",
            "sparse_heart",
        ),
        compression_traps=(
            "over_filling_negative_space",
            "citrus_over_complexity",
        ),
        socket_strategy="aggressive",
    ),
    "attars_oil_matrix": BrandProfile(
        profile_id="attars_oil_matrix",
        brands=("attar", "ittar", "traditional attar"),
        reformulation_risk="variable",
        unknown_captive_prior=0.15,
        natural_complexity_prior=0.90,
        negative_space_importance=0.4,
        default_evaluation_hours=8,
        protected_blocks=(
            "distillation_chain",
            "base_oil_matrix",
        ),
        compression_traps=(
            "natural_blending_loss",
            "distillation_profile_mismatch",
        ),
        socket_strategy="loose",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# Lookup
# ═══════════════════════════════════════════════════════════════════════════════


def get_profile(brand: str) -> BrandProfile | None:
    """Look up a brand profile by brand name (case-insensitive).

    Parameters
    ----------
    brand : str
        Brand name to search for (e.g. ``"chanel"``, ``"YSL"``,
        ``"Hermès"``).

    Returns
    -------
    BrandProfile | None
        The matching profile, or ``None`` if no profile covers this
        brand.
    """
    brand_lower = brand.lower().strip()
    for profile in PROFILES.values():
        for b in profile.brands:
            if b.lower() == brand_lower:
                return profile
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Prior adjustment
# ═══════════════════════════════════════════════════════════════════════════════


def apply_brand_priors(
    roster_weights: dict[str, float],
    profile: BrandProfile,
) -> dict[str, float]:
    """Adjust material weights based on a brand profile's priors.

    Adjustments
    -----------
    - If ``natural_complexity_prior > 0.7``, boost natural materials
      (those whose name contains common natural-extract keywords) by
      10 %.
    - If ``unknown_captive_prior > 0.4``, reduce dose certainty by
      5 % (multiply all weights by 0.95).

    Parameters
    ----------
    roster_weights : dict[str, float]
        Material name → weight (e.g. dose in µL, or a confidence score).
    profile : BrandProfile
        The brand profile whose priors to apply.

    Returns
    -------
    dict[str, float]
        Adjusted weights.  Keys are preserved; values are modified
        according to the profile's priors.
    """
    result: dict[str, float] = dict(roster_weights)

    # Natural-complexity boost.
    if profile.natural_complexity_prior > 0.7:
        _NATURAL_KEYWORDS = (
            " eo",
            " absolute",
            " resinoid",
            " co2",
            " extract",
            " oil",
            " concrete",
            " tincture",
        )
        for mat in list(result.keys()):
            mat_lower = mat.lower()
            if any(kw in mat_lower for kw in _NATURAL_KEYWORDS):
                result[mat] = round(result[mat] * 1.10, 4)

    # Captive-material uncertainty reduction.
    if profile.unknown_captive_prior > 0.4:
        for mat in list(result.keys()):
            result[mat] = round(result[mat] * 0.95, 4)

    return result


__all__ = [
    "BrandProfile",
    "PROFILES",
    "apply_brand_priors",
    "get_profile",
]
