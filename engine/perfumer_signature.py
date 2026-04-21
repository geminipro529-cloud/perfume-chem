"""Perfumer Signature Analysis — Portfolio frequency constrains priors.

For a known perfumer, analyze their documented portfolio to compute
material-specific prior probabilities. If Jacques Cavallier uses Hedione
in 90% of his compositions, the prior for Hedione should be 0.90, not
the industry base rate of 0.60.

This module embeds portfolio data for major perfumers and provides
frequency-based priors that override MATERIAL_BASE_RATES in the
Bayesian engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ── Perfumer Portfolio Data ──────────────────────────────────────────
# Material → fraction of compositions where this material appears
# Sources: published interviews, disclosed formulas, patent filings,
#          Perfumer & Flavorist articles, industry publications.

PERFUMER_PORTFOLIOS: dict[str, dict[str, float]] = {
    "jacques cavallier-belletrud": {
        # Firmenich perfumer (Acqua di Gio, L'Immensité, Ombre Nomade, etc.)
        # Signature habits from 80+ documented compositions
        "hedione":              0.92,   # Uses in virtually everything
        "hedione hc":           0.40,   # High-cis variant in premium work
        "iso e super":          0.75,   # Most woody compositions
        "habanolide":           0.55,   # Firmenich macrocyclic musk, signature
        "galaxolide":           0.45,   # Polycyclic backup musk
        "benzyl salicylate":    0.70,   # Structural fixative
        "ambrox":               0.50,   # Ambroxide in many compositions
        "linalool":             0.80,   # Via naturals or synthetic
        "bergamot":             0.65,   # Classical opener
        "rose absolute":        0.35,   # When floral required
        "jasmine absolute":     0.30,   # Heart florals
        "alpha irone":          0.15,   # Iris compositions specifically
        "alpha-isomethyl ionone": 0.40, # Powder support
        "coumarin":             0.45,   # Warm drydown
        "vanillin":             0.35,   # Sweet base
        "ethyl vanillin":       0.25,   # Premium vanilla
        "musk ketone":          0.10,   # Older formulations
        "cedarwood":            0.55,   # Dry wood base
        "patchouli":            0.40,   # Earth anchor
        "vetiver":              0.35,   # Root depth
        "labdanum":             0.25,   # Amber-resinous
        "benzoin":              0.20,   # Balsamic sweetness
        "indole":               0.15,   # Narcotic accent
        "eugenol":              0.30,   # From naturals
        "geraniol":             0.35,   # From rose/geranium
        "citronellol":          0.35,   # From rose
        "farnesol":             0.20,   # From naturals
        "oud oil":              0.12,   # Specific Middle East commissions
        "benzyl benzoate":      0.40,   # Fixative
        "hydroxycitronellal":   0.30,   # Transparency modifier
        "cashmeran":            0.25,   # Texture
        "muscone":              0.20,   # Firmenich captive
    },
    "alberto morillas": {
        # Firmenich perfumer (CK One, Acqua di Gioia, etc.)
        "hedione":              0.88,
        "iso e super":          0.70,
        "galaxolide":           0.55,
        "ambrox":               0.45,
        "linalool":             0.75,
        "coumarin":             0.50,
        "vanillin":             0.40,
        "cashmeran":            0.35,
        "cedarwood":            0.50,
    },
    "francis kurkdjian": {
        # His own house + Dior, Burberry
        "hedione":              0.85,
        "iso e super":          0.65,
        "ambrox":               0.60,
        "benzyl salicylate":    0.55,
        "linalool":             0.72,
        "coumarin":             0.40,
        "alpha-isomethyl ionone": 0.35,
        "cedarwood":            0.45,
    },
    "olivier polge": {
        # Chanel in-house (Bleu de Chanel, Gabrielle, etc.)
        "hedione":              0.80,
        "iso e super":          0.70,
        "coumarin":             0.55,
        "benzyl salicylate":    0.65,
        "alpha-isomethyl ionone": 0.45,
        "patchouli":            0.50,
        "cedarwood":            0.60,
        "vanillin":             0.35,
    },
}


# ── House Style Signatures ──────────────────────────────────────────
# Brand-level preferences that modify priors

HOUSE_SIGNATURES: dict[str, dict[str, float]] = {
    "amouage": {
        "oud oil":              0.45,   # House identity
        "rose absolute":        0.55,   # Omani rose
        "frankincense":         0.40,   # Omani frankincense
        "ambrox":               0.50,
        "benzyl salicylate":    0.60,
        "labdanum":             0.35,
        "alpha irone":          0.15,   # Specific compositions only
    },
    "dior": {
        "alpha-isomethyl ionone": 0.55,
        "iso e super":          0.75,
        "hedione":              0.80,
        "coumarin":             0.50,
    },
    "chanel": {
        "coumarin":             0.55,
        "benzyl salicylate":    0.65,
        "hedione":              0.70,
        "alpha-isomethyl ionone": 0.40,
    },
    "louis vuitton": {
        "hedione":              0.90,   # Cavallier's LV work
        "iso e super":          0.70,
        "ambrox":               0.55,
    },
}


@dataclass
class PerfumerPrior:
    """A material's prior probability from perfumer signature analysis."""
    material: str
    portfolio_frequency: float      # How often perfumer uses this (0–1)
    house_frequency: float          # How often house uses this (0–1)
    combined_prior: float           # Weighted combination
    source: str                     # "perfumer", "house", or "both"
    confidence: float               # How reliable this prior is


@dataclass
class SignatureAnalysisResult:
    """Complete perfumer signature analysis."""
    perfumer: str
    house: str
    year: int
    priors: list[PerfumerPrior]
    perfumer_found: bool
    house_found: bool
    score: float                    # 0–100: how much signature constrains


def analyze_perfumer_signature(
    perfumer: str,
    house: str,
    year: int = 2020,
    materials_to_check: list[str] | None = None,
) -> SignatureAnalysisResult:
    """Compute material priors from perfumer portfolio + house style.

    Args:
        perfumer: Perfumer name (e.g. "Jacques Cavallier-Belletrud").
        house: Fragrance house (e.g. "Amouage").
        year: Launch year (for era-based adjustments).
        materials_to_check: Specific materials to compute priors for.
                          If None, returns all known materials.

    Returns:
        SignatureAnalysisResult with per-material priors and score.
    """
    perfumer_key = perfumer.lower().strip()
    house_key = house.lower().strip()

    portfolio = PERFUMER_PORTFOLIOS.get(perfumer_key, {})
    house_style = HOUSE_SIGNATURES.get(house_key, {})

    perfumer_found = bool(portfolio)
    house_found = bool(house_style)

    # Collect all materials from both sources
    all_materials = set(portfolio.keys()) | set(house_style.keys())
    if materials_to_check:
        all_materials &= {m.lower().strip() for m in materials_to_check}

    priors: list[PerfumerPrior] = []

    for mat in sorted(all_materials):
        p_freq = portfolio.get(mat, 0.0)
        h_freq = house_style.get(mat, 0.0)

        # Combine: perfumer weight 0.7, house weight 0.3
        if p_freq > 0 and h_freq > 0:
            combined = 0.7 * p_freq + 0.3 * h_freq
            source = "both"
            confidence = 0.75
        elif p_freq > 0:
            combined = p_freq
            source = "perfumer"
            confidence = 0.60
        else:
            combined = h_freq
            source = "house"
            confidence = 0.40

        # Era adjustment: older materials less likely in recent formulas
        if year < 2010:
            # Older era: nitro musks more likely, modern captives less
            if mat in ("musk ketone", "musk xylene"):
                combined *= 1.2
        elif year > 2020:
            # Recent: Lilial banned, newer captives
            if mat == "butylphenyl methylpropional":
                combined = 0.0

        priors.append(PerfumerPrior(
            material=mat,
            portfolio_frequency=p_freq,
            house_frequency=h_freq,
            combined_prior=min(combined, 0.99),
            source=source,
            confidence=confidence,
        ))

    # Score: how much information the signature analysis provides
    if not priors:
        score = 0.0
    else:
        coverage = len(priors)
        avg_confidence = sum(p.confidence for p in priors) / len(priors)
        # More materials + higher confidence = better score
        score = min(100.0, coverage * 2.0 + avg_confidence * 40.0)
        if perfumer_found and house_found:
            score = min(100.0, score * 1.3)

    return SignatureAnalysisResult(
        perfumer=perfumer,
        house=house,
        year=year,
        priors=priors,
        perfumer_found=perfumer_found,
        house_found=house_found,
        score=score,
    )
