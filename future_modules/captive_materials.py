"""Captive materials intelligence — proprietary molecule libraries and independent strategies.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the captive materials intelligence from the Advanced Perfumery Supplement
(Gaps 10 + 11). The major fragrance houses maintain proprietary molecule libraries
not sold on the open market. This module catalogs:

  - IFF captives (Canthoxal, Koavone, Violiff, Heliotropex N, Fruit Sec, etc.)
  - Givaudan captives (Undecavertol, NeoFolione, Ebanol, etc.)
  - Firmenich captives (Helvetolide, Romandolide, Ambrox, Javanol, etc.)
  - Symrise captives
  - Independent perfumer strategies for working around captives
  - 15 additional key materials with profiles (Gap 10)
  - Cost tier per OAV delivery (Gap 13)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


# ---------------------------------------------------------------------------
# Captive materials by house
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CaptiveMaterial:
    """A proprietary molecule from a major fragrance house."""
    name: str
    house: str
    character: str
    substitute_strategy: str | None = None  # how independent perfumers can approximate
    now_available: bool = False              # whether this captive is now publicly available


IFF_CAPTIVES: tuple[CaptiveMaterial, ...] = (
    CaptiveMaterial("Canthoxal", "IFF", "Floral, fresh, aldehyde-adjacent, magnolia-like", "Use Magnolan + Cyclamen Aldehyde combination for similar floral-aldehydic effect"),
    CaptiveMaterial("Koavone", "IFF", "Violet-green muguet depth; bridges muguet + violet", "Use Methyl Ionone Gamma + Undecavertol combination for similar violet-green character"),
    CaptiveMaterial("Violiff", "IFF", "Proprietary violet enhancer with green-leather nuance", "Use Violet Leaf Absolute + Beta-Ionone + Parmavert for similar violet-green effect"),
    CaptiveMaterial("Heliotropex N", "IFF", "Powdery-almond-iris bridge, heliotrope character", "Use Heliotropin + Anisic Aldehyde for similar powdery-almond character"),
    CaptiveMaterial("Liffarome", "IFF", "Muguet/violet extension, fresh green", "Use cis-3-Hexenol + Hydroxycitronellal for similar fresh-green-floral"),
    CaptiveMaterial("Fruit Sec", "IFF", "Dried fruit character — used in Tom Ford Black Orchid for dark fruity depth", "Use Damascenone + Davana EO for dried-fruit complexity"),
    CaptiveMaterial("Florentione", "IFF", "Floral-green proprietary", "Use Floralozone + Undecavertol combination"),
)

GIVAUDAN_CAPTIVES: tuple[CaptiveMaterial, ...] = (
    CaptiveMaterial("Undecavertol", "Givaudan", "Green-watery, violet leaf analog; used in Black Orchid, No.5", "Available via Pell Wall / Fraterworks — semi-public", now_available=True),
    CaptiveMaterial("NeoFolione", "Givaudan", "'The photosynthesis molecule' — fresh, green, violet-leaf analog; used in Black Orchid", "Use Violet Leaf Absolute + cis-3-Hexenol for similar green-fresh effect"),
    CaptiveMaterial("Ebanol", "Givaudan", "Powerful sandalwood-cedar, creamy dry-woody; used in Black Orchid", "Use Bacdanol + Javanol for similar creamy sandalwood; Sandalore is Givaudan-licensed analog", now_available=True),
    CaptiveMaterial("Clearwood", "Givaudan", "Fermentation-derived clean patchouli; DSM-Firmenich 2014", "Now available via DSM-Firmenich — use as direct patchouli clean fraction", now_available=True),
)

FIRMENICH_CAPTIVES: tuple[CaptiveMaterial, ...] = (
    CaptiveMaterial("Helvetolide", "Firmenich", "Fruity pear/apple alicyclic musk, transparent", "Now available via DSM-Firmenich; previously strictly captive", now_available=True),
    CaptiveMaterial("Romandolide", "Firmenich", "Universal Galaxolide substitute, biodegradable", "Now available via DSM-Firmenich / Fraterworks", now_available=True),
    CaptiveMaterial("Javanol", "Firmenich", "Next-gen sandalwood molecule, creamy-rose", "Now available via DSM-Firmenich", now_available=True),
    CaptiveMaterial("Ambrox", "Firmenich", "Ambroxide — the 'real' Ambroxan; premium amber-skin", "Now partly available; Ambroxan is the genericized version", now_available=True),
)

SYMRISE_CAPTIVES: tuple[CaptiveMaterial, ...] = (
    CaptiveMaterial("Ambrocenide", "Symrise", "Amber-woody-oud depth; extremely potent (ODT ~0.1 ppb est.)", "Use Norlimbanol + Amber Xtreme for similar ultra-potent amber-woody"),
)


ALL_CAPTIVES: tuple[CaptiveMaterial, ...] = IFF_CAPTIVES + GIVAUDAN_CAPTIVES + FIRMENICH_CAPTIVES + SYMRISE_CAPTIVES


# ---------------------------------------------------------------------------
# Independent perfumer strategies
# ---------------------------------------------------------------------------

INDEPENDENT_STRATEGIES: tuple[tuple[str, str], ...] = (
    ("Use DSM-Firmenich public materials", "Javanol, Norlimbanol, Romandolide, Ambrox, Clearwood — former captives now semi-public"),
    ("Use Givaudan-licensed analogs", "Ebanol ≈ Sandalore analog; Undecavertol available via Pell Wall/Fraterworks"),
    ("Accept captive gaps", "Truly captive IFF materials (Canthoxal, Koavone, Heliotropex N) cannot be replicated exactly — use character-equivalent natural/synthetic combinations"),
    ("Natural isolate bridge", "Violet leaf absolute instead of Violiff; rose oxide instead of proprietary rose modifiers; natural agarwood instead of captive oud molecules"),
    ("Specialty supplier access", "Fraterworks, Pell Wall, Perfumer's Apprentice, Creating Perfume — best sources for semi-public captives"),
)


# ---------------------------------------------------------------------------
# 15 Additional key materials (Gap 10)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AdditionalMaterial:
    """A key material from Gap 10 not covered in the base database."""
    name: str
    cas: str
    vp_pa: float
    logp: float
    odt_ppb: float
    ifra_cat4_max: str
    character: str
    typical_dose_pct: tuple[float, float]  # (min, max) % in concentrate
    key_synergy: str
    thai_market_note: str


ADDITIONAL_MATERIALS: tuple[AdditionalMaterial, ...] = (
    AdditionalMaterial(
        "Cis-3-Hexenol", "928-96-1", 8.0, 1.6, 8.0,
        "Not limited", "Freshly cut grass, pure green. Emitted by crushed leaves.",
        (0.01, 0.1), "Galbanum (full green accord), Violet Leaf (metallic-green depth)",
        "Volatile — in tropical heat reduces to half-presence within 15 minutes. Dose 2× for Bangkok."
    ),
    AdditionalMaterial(
        "Helional", "1205-17-0", 0.1, 2.5, 5.0,
        "Not limited", "Marine, fresh, herbal, metallic sparkle. Bridges citrus and fresh.",
        (0.1, 1.0), "Marine-herbal modifier in Sauvage (0.73%), fresh masculines",
        "Moderate volatility — less climate-sensitive than Calone. Good tropical alternative to Calone."
    ),
    AdditionalMaterial(
        "Cyclamen Aldehyde", "103-95-7", 0.05, 3.5, 100.0,
        "Not limited", "Cyclamen-floral, diffusive, soapy. The 'diffusion amplifier.'",
        (0.1, 2.0), "Diffusion amplifier — critical in Aventus reconstruction for power and projection",
        "Moderate volatility — provides soapy-fresh projection in tropical heat."
    ),
    AdditionalMaterial(
        "Floralozone", "67634-15-5", 0.01, 3.0, 20.0,
        "Not limited", "Ozonic, transparent, floral, marine. NOT metallic like Calone.",
        (0.05, 1.0), "Transparent veil texture — less polarizing than Calone; works in floral and woody",
        "Excellent tropical performance — transparent atmospheric freshness without marine metallic."
    ),
    AdditionalMaterial(
        "Methyl Laitone", "N/A", 0.01, 3.5, 5.0,
        "Not limited", "Milky, creamy, lactonic, woody-velvety. The 'milk facet' material.",
        (0.1, 1.5), "Milky-creamy accords, rice/cereal notes, modern skin-close formulas",
        "Key for Thai 'soft' style — milky-creamy texture reads well in humid heat."
    ),
    AdditionalMaterial(
        "Ambrettolide", "123-69-3", 0.001, 4.5, 0.5,
        "Not limited", "Macrocyclic musk from ambrette seed. Clean, musky-floral, pear nuance.",
        (0.5, 5.0), "Fruity-musk base; combined with Helvetolide = 'ambrette duo' for pear-musky signatures",
        "Low anosmia risk — universally perceived. Excellent for Thai market musk base."
    ),
    AdditionalMaterial(
        "Florol (Floramol)", "5396-38-3", 0.05, 3.0, 20.0,
        "Not limited", "Transparent, watery, floral, slightly woody. Used in Black Orchid.",
        (0.5, 4.0), "Luxury floral transparency — creates 'sheer' quality of modern luxury fragrances",
        "Heart note — good tropical performance; 'watery floral' character persists in humidity."
    ),
    AdditionalMaterial(
        "Magnolan", "N/A (Givaudan)", 0.02, 3.5, 15.0,
        "Not limited", "Magnolia-floral, fresh, clean, slightly green. Used in Sauvage at ~1.76%.",
        (0.5, 2.0), "Softens Ambroxan dominance with fresh floral complexity — the 'Sauvage secret weapon'",
        "Givaudan captive — limited availability. Moderate tropical performance, heart-note persistence."
    ),
    AdditionalMaterial(
        "Rose Oxide (cis)", "16409-43-1", 0.1, 2.0, 0.5,
        "Not limited", "Metallic-rosy freshness. Only (-)-cis isomer contributes rose character.",
        (0.01, 0.2), "Rose-metallic freshness — photorealistic rose at 0.01%, harsh geranium at 0.2%",
        "Extreme potency — dose very carefully. ODT 0.5 ppb for cis-isomer."
    ),
)


# ---------------------------------------------------------------------------
# Cost Tiers vs OAV Delivery (Gap 13)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CostTier:
    """Cost tier classification for fragrance materials."""
    tier: str
    materials: tuple[str, ...]
    cost_per_kg: tuple[float, float]  # (low, high)
    oav_per_dollar: str
    strategy: str


COST_TIERS: tuple[CostTier, ...] = (
    CostTier(
        "High efficiency", ("Linalool", "Coumarin", "Hedione", "Iso E Super"),
        (5, 30), "Very high", "Build formula volume — these are the workhorse materials",
    ),
    CostTier(
        "Medium efficiency", ("Galaxolide", "Ambroxan", "Javanol"),
        (20, 200), "Medium-high", "Core platform materials — amortized across the whole formula",
    ),
    CostTier(
        "Low efficiency (luxury credibility)", ("Rose Absolute", "Jasmine Absolute", "Vetiver Haiti"),
        (3000, 8000), "Very low", "Authenticity anchors at 0.5-2% of concentrate — enough for olfactive complexity",
    ),
    CostTier(
        "Ultra-low (prestige)", ("Orris Butter", "Oud Oil (natural agarwood)"),
        (40000, 100000), "Extremely low", "0.1-0.3% maximum — prestige credibility signal only",
    ),
    CostTier(
        "Captive luxury", ("Ambrox", "Norlimbanol", "Romandolide"),
        (100, 500), "High (performance)", "Platform amplifiers — high OAV per dollar despite medium cost",
    ),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_captives_by_house(house: str) -> tuple[CaptiveMaterial, ...]:
    """Return captive materials for a specific fragrance house."""
    captives_map = {
        "iff": IFF_CAPTIVES, "givaudan": GIVAUDAN_CAPTIVES,
        "firmenich": FIRMENICH_CAPTIVES, "symrise": SYMRISE_CAPTIVES,
    }
    return captives_map.get(house.lower(), ())


def get_now_available_captives() -> tuple[CaptiveMaterial, ...]:
    """Return formerly-captive materials now publicly available."""
    return tuple(c for c in ALL_CAPTIVES if c.now_available)


def get_still_captive() -> tuple[CaptiveMaterial, ...]:
    """Return materials still strictly captive."""
    return tuple(c for c in ALL_CAPTIVES if not c.now_available)


def get_independent_strategies() -> tuple[tuple[str, str], ...]:
    """Return independent perfumer strategies for working around captives."""
    return INDEPENDENT_STRATEGIES


def get_substitute(material_name: str) -> str | None:
    """Return a substitute strategy for a captive material."""
    for c in ALL_CAPTIVES:
        if c.name.lower() == material_name.lower():
            return c.substitute_strategy
    return None


def get_additional_material(name: str) -> AdditionalMaterial | None:
    """Return a Gap-10 additional material profile."""
    for am in ADDITIONAL_MATERIALS:
        if am.name.lower() == name.lower():
            return am
    return None


def get_all_additional_materials() -> tuple[AdditionalMaterial, ...]:
    """Return all Gap-10 additional material profiles."""
    return ADDITIONAL_MATERIALS


def get_cost_tier(material_name: str) -> CostTier | None:
    """Return the cost tier for a material."""
    for ct in COST_TIERS:
        if material_name.lower() in (m.lower() for m in ct.materials):
            return ct
    return None


def get_all_cost_tiers() -> tuple[CostTier, ...]:
    """Return all cost tiers."""
    return COST_TIERS


def recommend_thai_captive_alternatives() -> dict[str, str]:
    """Recommend available alternatives for captives important to Thai market formulation."""
    return {
        "Canthoxal (IFF captive)": "Cyclamen Aldehyde 0.5-2.0% — similar floral-diffusive character, universally available",
        "Koavone (IFF captive)": "Methyl Ionone Gamma + Undecavertol 0.5% each — violet-green bridge effect",
        "Heliotropex N (IFF captive)": "Anisic Aldehyde 0.5-2.0% + Coumarin 1-3% — powdery-almond warmth",
        "Fruit Sec (IFF captive)": "Damascenone trace + Davana EO 0.5% — dried-fruit complexity",
        "NeoFolione (Givaudan captive)": "Cis-3-Hexenol 0.05-0.1% + Violet Leaf Absolute 0.1-0.5% — fresh-green photosynthesis",
        "Magnolan (Givaudan captive)": "Florol 1-3% + Linalool 2-5% — magnolia-floral transparency",
    }
