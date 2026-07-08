"""Somatosensory effects in perfumery — the tactile dimension beyond olfaction.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the sensory physiology intelligence from the Advanced Perfumery Supplement
(Gap 4). Several fragrance materials activate non-olfactory nerve channels (TRP
receptors), adding a tactile/somatosensory dimension that pure olfaction cannot
achieve. This is the "electric" quality in Dior Sauvage's opening.

Key materials and their channels:
  - Sichuan Pepper (hydroxy-alpha-sanshool) — TRPV1 + TRPA1 + KCNK channels
  - Menthol — TRPM8 (cold receptor)
  - Camphor — TRPV1 + TRPM8
  - Black Pepper — TRPV1 (capsaicin analog)
  - Eucalyptus — TRPM8
  - Ginger — TRPV1 + others

Design principle: the tactile layer is perceived simultaneously but independently
from the olfactory layer, creating a depth that purely olfactory formulas cannot
achieve.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


# ---------------------------------------------------------------------------
# Somatosensory material profiles
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SomatosensoryMaterial:
    """A fragrance material with documented somatosensory (non-olfactory) effects."""
    material: str
    effect: str                      # subjective description
    receptor_channels: tuple[str, ...]  # TRP and K+ channels activated
    mechanism: str
    usage_pct_range: tuple[float, float]  # % in concentrate
    context: str                     # fragrance families where used
    overdose_effect: str
    design_principle: str            # how to use in formulation


SOMATOSENSORY_MATERIALS: tuple[SomatosensoryMaterial, ...] = (
    SomatosensoryMaterial(
        "Sichuan Pepper EO",
        "Tingling, numbing, electric, vibrating sensation on skin",
        ("TRPV1", "TRPA1", "KCNK3", "KCNK9", "KCNK18", "D-hair fibers"),
        (
            "Hydroxy-alpha-sanshool (C22H35NO3) activates TRPV1/TRPA1 pain/heat "
            "receptors (same as capsaicin) AND KCNK tandem pore K+ channels "
            "(primary numbing mechanism) AND D-hair afferent touch fibers. "
            "Sanshool concentration in peppercorns: 0.8–4.2% dry weight."
        ),
        (0.5, 3.0),
        "Masculine fresh, spicy, designer fresh",
        "At > 5%: overwhelming tingling, unpleasant",
        "Use at 0.5–3% for numbing-tingling 'electricity' in the opening. "
        "At < 0.5%: subliminal tactile texture. "
        "This is the 'Sauvage electric' quality — cannot be replicated olfactorily."
    ),
    SomatosensoryMaterial(
        "Menthol (natural or synthetic)",
        "Cooling illusion — feels cold on skin without temperature change",
        ("TRPM8",),
        (
            "TRPM8 is the primary cold receptor in sensory neurons. "
            "Menthol lowers the activation threshold of TRPM8, creating "
            "a cooling sensation at normal skin temperature."
        ),
        (0.01, 0.5),
        "Aquatic, fresh, fougère, sport",
        "At > 1%: overwhelming cold, medicinal, anesthetic",
        "Use 0.01–0.1% for subtle cooling in aquatic/fresh formulas. "
        "At 0.1–0.5%: pronounced cooling for sport/summer fragrances."
    ),
    SomatosensoryMaterial(
        "Camphor",
        "Cool-medicinal sensation, slight numbing",
        ("TRPV1", "TRPM8"),
        (
            "Dual TRPV1 + TRPM8 activation produces a complex cool-warm sensation "
            "with medicinal character. Less purely 'cold' than menthol."
        ),
        (0.01, 0.1),
        "Forest, fougère accent, medicinal",
        "At > 0.3%: overwhelmingly medicinal, vapor-rub character",
        "Use 0.01–0.1% as accent in forest/mossy formulas. "
        "The camphor + eucalyptus + menthol triad creates a complex cooling matrix."
    ),
    SomatosensoryMaterial(
        "Black Pepper EO",
        "Mild warmth, slight bite, tingle",
        ("TRPV1",),
        (
            "Piperine and related alkaloids activate TRPV1 (capsaicin receptor) "
            "at lower potency than capsaicin itself, producing a mild warm-tingle "
            "without the burning sensation of chili."
        ),
        (0.5, 3.0),
        "Spicy, masculine, oriental, fougère",
        "At > 5%: irritant, sneeze-inducing",
        "Use 0.5–3% for warm spicy lift without chile-heat. "
        "Combine with pink pepper for complex pepper dimension."
    ),
    SomatosensoryMaterial(
        "Eucalyptus EO",
        "Strong cooling, clean-medicinal, respiratory-opening",
        ("TRPM8",),
        (
            "Eucalyptol (1,8-cineole) is the primary TRPM8 agonist in eucalyptus. "
            "Produces a strong, clean cooling sensation with respiratory tract effects."
        ),
        (0.1, 1.0),
        "Aquatic, marine, clean, sport",
        "At > 2%: overwhelming medicinal, too strong for fine fragrance",
        "Use 0.1–0.5% for aquatic freshness with cooling dimension. "
        "At 0.5–1.0% for pronounced 'spa/marine' character."
    ),
    SomatosensoryMaterial(
        "Ginger EO",
        "Warm bite, slight heat, spicy-zing",
        ("TRPV1", "others"),
        (
            "Gingerols and shogaols activate TRPV1 at moderate potency. "
            "Produces a warm, zingy sensation distinct from pepper's dry warmth."
        ),
        (0.5, 2.0),
        "Oriental, spicy warm, gourmand, fresh-spicy",
        "At > 3%: harsh, irritant zing",
        "Use 0.5–2.0% for warm spicy dimension with tactile bite. "
        "Ginger + Sichuan pepper = dual-mechanism warm-numbing complexity."
    ),
)


# ---------------------------------------------------------------------------
# TRP channel reference
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TrpChannel:
    """A thermosensory/chemosensory TRP channel involved in fragrance perception."""
    channel: str
    full_name: str
    activated_by: str
    sensation: str
    fragrance_materials: tuple[str, ...]


TRP_CHANNELS: tuple[TrpChannel, ...] = (
    TrpChannel(
        "TRPV1", "Transient Receptor Potential Vanilloid 1",
        "Heat (> 43°C), capsaicin, low pH, sanshool, piperine, gingerols",
        "Burning pain, warmth, heat",
        ("Sichuan Pepper", "Black Pepper", "Ginger", "Camphor (secondary)"),
    ),
    TrpChannel(
        "TRPA1", "Transient Receptor Potential Ankyrin 1",
        "Cold (< 17°C), mustard oil, wasabi, cinnamaldehyde, sanshool",
        "Pungent irritant, cold pain",
        ("Sichuan Pepper", "Cinnamon (cinnamaldehyde)"),
    ),
    TrpChannel(
        "TRPM8", "Transient Receptor Potential Melastatin 8",
        "Cold (< 25°C), menthol, eucalyptol, camphor",
        "Cooling, cold sensation",
        ("Menthol", "Eucalyptus", "Camphor"),
    ),
    TrpChannel(
        "TRPV3", "Transient Receptor Potential Vanilloid 3",
        "Warm (31–39°C), camphor, carvacrol, thymol",
        "Warmth, moderate heat",
        ("Camphor (secondary)", "Thyme (thymol)", "Oregano (carvacrol)"),
    ),
)


# ---------------------------------------------------------------------------
# Somatosensory design patterns
# ---------------------------------------------------------------------------

SOMATOSENSORY_DESIGN_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "Electric fresh (Sauvage-style)",
        "Sichuan Pepper 1-3% + Dihydromyrcenol 8-12% + Ambroxan 8-15% + Hedione 8-15%",
        "The Sichuan pepper provides tingling-numbing that makes the DHMN-Ambroxan freshness read as 'electric' rather than 'functional'",
    ),
    (
        "Cool aquatic (sport fresh)",
        "Menthol 0.05-0.2% + Eucalyptus 0.1-0.5% + Calone 0.005-0.015% + Hedione 8-12%",
        "The menthol+eucalyptus provide a cooling matrix that Calone's marine character rides on, creating a 'cold water' freshness",
    ),
    (
        "Warm spicy oriental",
        "Black Pepper 1-3% + Ginger 0.5-2% + Vanillin 1-5% + Labdanum 1-5%",
        "The dual TRPV1 activation from pepper+ginger creates a warm-tactile base that vanillin and labdanum ride on",
    ),
    (
        "Complex nose-tingle (niche fresh)",
        "Sichuan Pepper 0.5-1.5% + Pink Pepper 1-3% + Cassis (blackcurrant) 0.5-1% + green accord 2-5%",
        "Multiple somatosensory channels (TRPV1+TRPA1+KCNK from Sichuan + TRPV1 from pink pepper + thiolic bite from cassis) create a non-replicable fresh-spicy tingle",
    ),
    (
        "Forest-medicinal (fougère accent)",
        "Camphor 0.01-0.05% + Eucalyptus 0.05-0.2% + Lavender 5-10% + Coumarin 1-3%",
        "Camphor+eucalyptus cooling gives the aromatic fougère a medicinal-forest depth beyond pure olfaction; coumarin and lavender provide the pleasant background",
    ),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_somatosensory_material(name: str) -> SomatosensoryMaterial | None:
    """Return a somatosensory material profile."""
    for sm in SOMATOSENSORY_MATERIALS:
        if sm.material.lower() == name.lower():
            return sm
    return None


def get_all_somatosensory_materials() -> tuple[SomatosensoryMaterial, ...]:
    """Return all somatosensory material profiles."""
    return SOMATOSENSORY_MATERIALS


def get_materials_by_channel(channel: str) -> tuple[SomatosensoryMaterial, ...]:
    """Return materials activating a specific TRP channel."""
    return tuple(
        sm for sm in SOMATOSENSORY_MATERIALS
        if any(channel.upper() in ch.upper() for ch in sm.receptor_channels)
    )


def get_trp_channel(channel: str) -> TrpChannel | None:
    """Return TRP channel profile."""
    for tc in TRP_CHANNELS:
        if tc.channel == channel.upper():
            return tc
    return None


def get_all_trp_channels() -> tuple[TrpChannel, ...]:
    """Return all TRP channel profiles."""
    return TRP_CHANNELS


def get_design_pattern(pattern_name: str) -> tuple[str, str, str] | None:
    """Return a somatosensory design pattern."""
    for name, materials, effect in SOMATOSENSORY_DESIGN_PATTERNS:
        if pattern_name.lower() in name.lower():
            return (name, materials, effect)
    return None


def get_all_design_patterns() -> tuple[tuple[str, str, str], ...]:
    """Return all somatosensory design patterns."""
    return SOMATOSENSORY_DESIGN_PATTERNS


def classify_somatosensory_effect(material_name: str) -> str | None:
    """Classify the primary somatosensory effect of a material (cool, warm, numbing, etc.)."""
    classifications = {
        "sichuan pepper eo": "numbing-tingling",
        "menthol": "cooling",
        "camphor": "cooling-medicinal",
        "black pepper eo": "warming-mild",
        "eucalyptus eo": "cooling-strong",
        "ginger eo": "warming-zingy",
    }
    return classifications.get(material_name.lower())


def recommend_somatosensory_for_context(context: str) -> list[str]:
    """Recommend somatosensory materials for a desired sensory context."""
    recommendations: dict[str, list[str]] = {
        "electric_fresh": ["Sichuan Pepper EO", "Black Pepper EO"],
        "cooling_sport": ["Menthol", "Eucalyptus EO", "Camphor"],
        "warm_spicy": ["Black Pepper EO", "Ginger EO"],
        "complex_tingle": ["Sichuan Pepper EO"],
        "medicinal_forest": ["Camphor", "Eucalyptus EO"],
    }
    return recommendations.get(context, [])
