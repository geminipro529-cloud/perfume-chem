"""Iconic formula archaeology — structural analysis of luxury/niche fragrances.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Decodes the structural architecture of 6 landmark fragrances from the Advanced
Perfumery Supplement (Gap 1). Each formula is analyzed for:
  - Structural skeleton (materials + approximate parts by weight)
  - OAV role of key materials
  - Platform/architecture insight
  - Tropical (Bangkok) formulation notes
  - Anosmia risk and countermeasures

Formulas covered:
  1. Dior Sauvage (2015, François Demachy) — Ambroxan-dominant aromatic fougère
  2. Chanel No.5 (1921, Ernest Beaux) — Aldehydic floral, three-layer depth
  3. Creed Aventus (2010, Hérault & Creed) — Fruity chypre, Helvetolide platform
  4. PDM Layton — Ultra-high Iso E Super woody-amber gourmand
  5. Tom Ford Black Orchid (2006) — Negative-space oriental floral
  6. Amouage Interlude Man (2012) — Dramatic arc, incense platform

All structural data is reconstructed from community GCMS analysis, reverse-engineering,
and published sources. Values marked _RECONSTRUCTED where not officially confirmed.
"""

from __future__ import annotations

from dataclasses import dataclass

from ._shared_types import ConcentrationBracket, FragranceFamily

# ---------------------------------------------------------------------------
# Structural skeleton dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FormulaSkeleton:
    """Structural analysis of a known luxury/niche fragrance."""
    name: str
    house: str
    year: int
    perfumers: str
    family: FragranceFamily
    concentration: ConcentrationBracket
    structural_insight: str  # The one-sentence architectural takeaway
    three_pillar_platform: tuple[str, str, str] | None  # The 3-material diffusion core
    materials: tuple[tuple[str, float, str], ...]  # (name, pct_in_conc, role)
    construction_method: str  # e.g., "platform-first", "dramatic arc", "abstract overlay"
    tropical_notes: str
    anosmia_warnings: str
    data_confidence: str = "_RECONSTRUCTED"


# ---------------------------------------------------------------------------
# 1. Dior Sauvage
# ---------------------------------------------------------------------------

SAUVAGE_SKELETON = FormulaSkeleton(
    name="Sauvage (Eau de Toilette)",
    house="Dior",
    year=2015,
    perfumers="François Demachy (IFF)",
    family=FragranceFamily.AROMATIC_FOUGERE,
    concentration=ConcentrationBracket.EDT,
    structural_insight=(
        "Three-pillar formula: Ambroxan (14.7%) + Iso E Super (14.7%) + Hedione (14.7%) "
        "each creating OAV > 100 anchors simultaneously. Everything else modulates these three. "
        "The 'Sauvage sillage' is the Ambroxan + Iso E Super mid-VP platform projecting at sillage distance."
    ),
    three_pillar_platform=("Ambroxan", "Iso E Super", "Hedione"),
    materials=(
        ("Ambroxan", 14.7, "Character anchor — OAV ~735, OR7A17 activation, extreme longevity"),
        ("Iso E Super", 14.7, "Woody-cedar amplifier, sillage platform — OAV ~120"),
        ("Hedione", 14.7, "Radiance, jasmine diffusion, VN1R1 activation — OAV ~147"),
        ("Habanolide", 11.75, "Macrocyclic musk backbone, longevity — OAV ~35"),
        ("Dihydromyrcenol", 10.3, "Transparent diffusion, marine-citrus freshness — OAV ~80"),
        ("Linalyl Acetate", 7.0, "Lavender facet, bergamot feel — OAV ~70"),
        ("Linalool", 4.4, "Transparent floral bridge, lavender suggestion — OAV ~88"),
        ("Patchouli EO", 4.4, "Earthy depth anchor — OAV ~44"),
        ("Grapefruit EO", 4.4, "Bright top (character from mercaptan trace, not limonene) — OAV ~88"),
        ("Pink Pepper EO", 4.4, "Spicy lift, fresh contrast, somatosensory — OAV ~40"),
        ("Ambrettolide", 3.7, "Second macrolide musk layer — OAV ~18"),
        ("Cashmeran", 1.47, "Spicy-musk-amber texture — OAV ~7"),
        ("Helional", 0.73, "Marine-metallic shine — OAV ~15"),
        ("Coumarin", 0.59, "Hay-lavender warmth — OAV ~12"),
        ("Veramoss (Evernyl)", 0.44, "Post-IFRA mossy grounding — OAV ~4"),
        ("Javanol", 0.22, "Sandalwood whisper — OAV ~5"),
        ("Ambrocenide", 0.22, "Amber-woody depth — OAV ~5"),
        ("Alpha-Damascone", 0.02, "Subliminal rose-apple depth — OAV ~100"),
    ),
    construction_method="platform-first (three-pillar)",
    tropical_notes=(
        "Ambroxan at 14.7% → 3.7% in 25% EdP → very high OAV even at 35°C. "
        "VP ×2.8 actually improves Ambroxan in heat — amber blossoms with warmth. "
        "Sauvage is commonly perceived as stronger in Asian climates."
    ),
    anosmia_warnings=(
        "~20% East Asian (Thai) consumers may not perceive Ambroxan due to OR7A17 alleles. "
        "Habanolide + Ambrettolide provide built-in anosmia coverage. "
        "Iso E Super anosmia ~22% — the Hedione radiance provides alternative character."
    ),
    data_confidence="_RECONSTRUCTED from community DIY and Reddit r/PerfumeryFormulas",
)


# ---------------------------------------------------------------------------
# 2. Chanel No.5
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AldehydeQuartet:
    """The Chanel No.5 aldehyde quartet with individual OAV targets."""
    aldehyde_c10_pct: float = 0.15   # Decanal
    aldehyde_c11_pct: float = 0.15   # Undecylenic
    aldehyde_c12_lauric_pct: float = 0.15  # Lauric
    aldehyde_c12_mna_pct: float = 0.15     # Methylundecylic (MNA)
    total_complex_pct: float = 0.6
    total_oav_target: tuple[float, float] = (60, 200)  # After mixture suppression
    oav_too_high: float = 300  # Reads as "old soapy"
    oav_too_low: float = 20    # Aldehyde character disappears

    @property
    def acetal_compensation_factor(self) -> float:
        """Dose aldehydes 50-80% higher at T=0 to compensate for acetal formation."""
        return 1.65  # midpoint of 1.5-1.8


CHANEL_NO5_SKELETON = FormulaSkeleton(
    name="Chanel No.5 (Parfum)",
    house="Chanel",
    year=1921,
    perfumers="Ernest Beaux",
    family=FragranceFamily.FLORAL_ROSE,  # Floral Aldehyde, closest archetype
    concentration=ConcentrationBracket.EXTRAIT,
    structural_insight=(
        "Three-layer depth structure: abstract metallic (aldehydes) → sensual floral "
        "(jasmine-rose-ylang) → intimate skin (orris-sandalwood-musk-civet). "
        "Aldehydes 'make flowers sing' — they prevent the jasmine-rose from reading "
        "as realistic flowers, creating abstracted florality. Each layer distinct and legible."
    ),
    three_pillar_platform=None,  # Not platform-based — layer-based
    materials=(
        ("Benzyl Acetate", 15.0, "Jasmine-rosy skeleton — 150 parts/1000"),
        ("Benzyl Salicylate", 10.0, "Diffusion cushion — 100 parts/1000"),
        ("Musk complex (macrocyclic + polycyclic)", 8.0, "Fixation — 80 parts/1000"),
        ("Linalool", 5.0, "Floral-transparent bridge — 50 parts/1000"),
        ("PEA (Phenylethyl Alcohol)", 5.0, "Rosy heart — 50 parts/1000"),
        ("Methyl Ionone (gamma)", 5.0, "Violet-orris backbone — 50 parts/1000"),
        ("Coumarin", 5.0, "Tonka-hay fixation — 50 parts/1000"),
        ("Sandalwood / Javanol", 5.0, "Creamy base — 50 parts/1000"),
        ("Jasmine Absolute", 5.0, "Luxury anchor — 50 parts/1000"),
        ("Ambergris / Ambroxan 5%", 5.0, "Amber skin-bridge — 50 parts/1000"),
        ("Ylang Ylang EO", 3.5, "Tropical floral depth — 35 parts/1000"),
        ("Civet / Ethylene Brassylate", 2.5, "Animalic intimacy — 25 parts/1000"),
        ("Aldehyde C10 (10% dilution)", 2.0, "Fatty-orange aldehyde — 20 parts/1000"),
        ("Hydroxycitronellal", 2.0, "Muguet-lily facet — 20 parts/1000"),
        ("Oakmoss 10% / Evernyl substitute", 1.5, "Chypre grounding (IFRA limited) — 15 parts/1000"),
        ("Rose Absolute", 1.0, "Rose luxury anchor — 10 parts/1000"),
        ("Alpha Ionone", 1.0, "Violet nuance — 10 parts/1000"),
        ("Aldehyde C11 (10% dilution)", 1.0, "Soapy-coriander aldehyde — 10 parts/1000"),
        ("Aldehyde C12 MNA (10% dilution)", 1.0, "Cold-metallic-clean aldehyde — 10 parts/1000"),
        ("Orris Concrete 10%", 1.0, "Iris-cosmetic — 10 parts/1000"),
        ("Vetiver EO", 1.0, "Earthy depth — 10 parts/1000"),
    ),
    construction_method="three-layer depth (abstract → sensual → skin)",
    tropical_notes=(
        "Aldehydes: acetal formation is faster at 35°C. Dose 80% higher at T=0 for Bangkok. "
        "High-extrait concentration (20%+) means base notes survive tropical heat better than "
        "EdT formulas. The jasmine-rose-ylang heart benefits from °C warmth."
    ),
    anosmia_warnings=(
        "No significant single-material anosmia risk — the complexity (22+ materials) "
        "provides built-in coverage. Multiple musk classes used. Orris/ionone perception "
        "may vary (β-ionone ~20% anosmia) but γ-MIG at 5% is the dominant violet note."
    ),
    data_confidence="_PARTIALLY_RECONSTRUCTED from multiple sources (Beaux-era documents + modern GCMS)",
)


# ---------------------------------------------------------------------------
# 3. Creed Aventus
# ---------------------------------------------------------------------------

AVENTUS_SKELETON = FormulaSkeleton(
    name="Aventus (Eau de Parfum)",
    house="Creed",
    year=2010,
    perfumers="Jean-Christophe Hérault & Erwin Creed",
    family=FragranceFamily.CHYPRE,  # Chypre Fruity
    concentration=ConcentrationBracket.EDP,
    structural_insight=(
        "Helvetolide at ~14% is NOT perceived as 'musk' — it reads as a transparent "
        "fruity-amber atmospheric cloud in which pineapple and smoky notes float. "
        "This is the highest-concentration musk deployment of any famous fragrance. "
        "The diffusion platform (Hedione + Iso E Super + Helvetolide + Ambroxan) = 60% "
        "of formula weight — the identity of Aventus is its platform, not its notes."
    ),
    three_pillar_platform=("Helvetolide", "Hedione", "Iso E Super"),
    materials=(
        ("Hedione", 23.0, "Radiance platform — VN1R1 activation, transparent jasmine diffusion"),
        ("Iso E Super", 14.0, "Woody sillage platform"),
        ("Helvetolide", 14.0, "Transparent fruity-musk cloud — pear/apple/ambrette atmosphere"),
        ("Ambroxan", 10.0, "Amber-skin anchor, OR7A17 activation"),
        ("Allyl Amyl Glycolate", 1.4, "Green-tropical pineapple character (~14 parts)"),
        ("Bergamot FCF", 5.0, "Hesperidic top note"),
        ("Alpha-Damascone (10%)", 0.3, "Apple-rose depth that makes pineapple photorealistic (~3 parts 10%)"),
        ("Cypriol EO (Nagarmotha)", 0.5, "Woody-spicy-earthy-smoky — PRIMARY smoke source, not birch tar"),
        ("Butyl Quinoline Secondary (10%)", 0.6, "Leather-smoky edge (~6 parts 10%)"),
        ("Patchouli EO", 1.0, "Earthy grounding (~10 parts)"),
        ("Coranol", 2.0, "Rosy-woody nuance"),
        ("Evernyl (Veramoss)", 0.5, "Post-IFRA mossy element"),
        ("Ambrettolide", 2.0, "Second musk layer (~20 parts/1000)"),
        ("Birch Tar (10%)", 0.1, "Trace smoky accent — NOT the primary smoke source"),
        ("Octyl Salicylate", 0.2, "UV absorber / stabilizer"),
        ("Cyclamen Aldehyde", 0.5, "Diffusion amplifier, radiant soapy-fresh projection"),
    ),
    construction_method="platform-first (60% diffusion platform + 25% character + 15% accents)",
    tropical_notes=(
        "Helvetolide at 14% in concentrate → transparent fruity cloud. VP moderate (~0.003 Pa) "
        "but high loading compensates at 35°C. Ambroxan blossoms in heat. "
        "Cypriol (Nagarmotha) smoke character is climate-stable."
    ),
    anosmia_warnings=(
        "Helvetolide is universally perceived (<5% anosmia) — major advantage over Galaxolide. "
        "Ambroxan OR7A17 risk (~20% East Asian) partially compensated by Helvetolide + Hedione platform. "
        "Iso E Super anosmia (~22%) — but at 14% loading, even partial perception is significant."
    ),
    data_confidence="_RECONSTRUCTED from Basenotes community GCMS analysis and reverse-engineering",
)


# ---------------------------------------------------------------------------
# 4. PDM Layton
# ---------------------------------------------------------------------------

LAYTON_SKELETON = FormulaSkeleton(
    name="Layton (Eau de Parfum)",
    house="Parfums de Marly",
    year=2016,
    perfumers="Hamid Merati-Kashani",
    family=FragranceFamily.WOODY_AMBER,
    concentration=ConcentrationBracket.EDP,
    structural_insight=(
        "Ultra-high Iso E Super (22.4% of formula) approaches Escentric Molecules "
        "single-molecule territory, but is modulated by Ambroxan, Norlimbanol, and Cashmeran "
        "into a rich, spiced, masculine signature. The sweet elements (Ethyl Vanillin, Coumarin, "
        "Cashmeran) create the praline-apple accord distinguishing it within woody-amber."
    ),
    three_pillar_platform=("Iso E Super", "Ambroxan", "Norlimbanol"),
    materials=(
        ("Iso E Super", 22.4, "Dominant woody sillage anchor — 224 parts"),
        ("DPG (diluent)", 10.7, "Carrier — 107 parts"),
        ("Ambroxan", 10.0, "Amber-skin second anchor — 100 parts"),
        ("Norlimbanol", 8.5, "Dry woody depth amplifier — 85 parts"),
        ("Hedione", 8.0, "Radiance bridge — 80 parts"),
        ("Cashmeran", 6.0, "Spicy-musk-apple texture — 60 parts"),
        ("Patchouli EO", 4.8, "Earthy grounding — 48 parts"),
        ("Coranol", 3.0, "Rosy-woody nuance — 30 parts"),
        ("Ethyl Vanillin", 3.0, "Sweet gourmand warmth — 30 parts"),
        ("Lavender EO", 2.91, "Aromatic freshness, fougère suggestion — 29.1 parts"),
        ("Mandarin EO", 2.7, "Bright top — 27 parts"),
        ("Amberwood F", 1.6, "Amber woody synergy — 16 parts"),
        ("Guaiacwood", 1.57, "Smoky-woody base — 15.7 parts"),
        ("Coumarin", 1.5, "Hay-tonka bridge — 15 parts"),
        ("Vanillin", 1.5, "Sweet warmth — 15 parts"),
        ("Verdox", 1.1, "Green-woody extension — 11 parts"),
        ("Linalyl Acetate", 0.9, "Lavender-bergamot freshness — 9 parts"),
        ("Helional", 0.7, "Marine-metallic brightness — 7 parts"),
        ("Calone", 0.08, "Trace marine freshness (< cliff threshold) — 0.8 parts"),
        ("Beta-Damascenone", 0.05, "Subliminal rose-plum — 0.5 parts"),
    ),
    construction_method="platform-first (ultra-high anchor + woody-amber modulation)",
    tropical_notes=(
        "Norlimbanol VP ~0.00005 Pa — effectively climate-invariant even at 35°C. "
        "Iso E Super at 22.4% provides massive OAV buffer against heat-accelerated evaporation. "
        "Cashmeran + Ethyl Vanillin for the sweet layer survive tropical heat well."
    ),
    anosmia_warnings=(
        "Iso E Super at 22.4%: ~22% anosmia risk, but at this loading partial perception "
        "is still very significant. Norlimbanol + Ambroxan provide alternative woody-amber "
        "character for Iso E Super anosmics. Cashmeran is universally perceived (<5% anosmia)."
    ),
    data_confidence="_RECONSTRUCTED from AI analysis (AromatuneAI) confirmed by community testing",
)


# ---------------------------------------------------------------------------
# 5. Tom Ford Black Orchid
# ---------------------------------------------------------------------------

BLACK_ORCHID_SKELETON = FormulaSkeleton(
    name="Black Orchid (Eau de Parfum)",
    house="Tom Ford",
    year=2006,
    perfumers="David Apel & Pierre Negrin (Givaudan)",
    family=FragranceFamily.AMBER_ORIENTAL,
    concentration=ConcentrationBracket.EDP,
    structural_insight=(
        "The most explicit example of negative-space perfumery. Materials at OAV < 1 "
        "(Calone, Indole, NeoFolione) are deliberately kept sub-threshold so they are felt "
        "as texture, not identified as notes. The 'black orchid accord' is not orchid at all "
        "(orchids have no meaningful scent) — it is Ylang-Ylang + Jasmine Sambac + Beta-Ionone "
        "+ Florol + trace Calone creating narcotic tropical-dark floral. The truffle note is "
        "phantom-like — dark patchouli + cocoa absolute + guaiacol compounds."
    ),
    three_pillar_platform=("Iso E Super", "Hedione", "Ambrox Super"),
    materials=(
        ("Iso E Super", 10.0, "Transparent woody sillage platform"),
        ("Hedione", 8.0, "Radiance diffusion platform"),
        ("Ambrox Super / Ambroxan", 5.0, "Amber-skin platform"),
        ("Ethylene Brassylate", 8.0, "Invisible linear musk base"),
        ("Jasmine Sambac Absolute", 3.0, "Narcotic white floral anchor"),
        ("Ylang-Ylang EO Extra", 2.5, "Tropical-dark floral — part of orchid accord"),
        ("Florol", 2.0, "Transparent watery-floral veil"),
        ("Beta-Ionone", 1.5, "Violet-woody depth — part of orchid accord"),
        ("Canthoxal (IFF captive)", 2.0, "Luxury floral enhancer, magnolia-like"),
        ("Patchouli Oil", 3.0, "Dark earthy base"),
        ("Vertofix Coeur", 2.5, "Warm precious-wood musky amber"),
        ("Bacdanol", 1.5, "Creamy sandalwood modifier"),
        ("Sandalore", 1.0, "Sandalwood synthetic"),
        ("Guaiyl Acetate", 0.5, "Woody-green transparency"),
        ("Ebanol", 1.0, "Powerful sandalwood-cedar"),
        ("Cashmeran", 2.0, "Spicy-musk-earthy texture"),
        ("Olibanum Resinoid", 1.5, "Resinous frankincense depth"),
        ("Vanillin", 2.0, "Sweet vanilla warmth"),
        ("Ethyl Vanillin", 1.5, "Creamy-sweet extension"),
        ("Coumarin", 1.5, "Hay-tonka bridge"),
        ("Cocoa Absolute", 0.5, "Dark gourmand dimension"),
        ("Rum CO2 Extract", 0.3, "Boozy-warm complexity"),
        ("Cinnamyl Alcohol", 0.5, "Spice warmth"),
        ("Clove Bud Oil", 0.3, "Spicy-earthy depth"),
        ("Calone (10%)", 0.03, "Trace marine freshness (sub-threshold OAV < 1)"),
        ("NeoFolione", 0.3, "Photosynthesis-green sub-threshold contrast"),
        ("Indole (10%)", 0.05, "Narcotic white-floral sub-threshold depth"),
    ),
    construction_method="negative-space (sub-threshold texture materials create atmospheric depth)",
    tropical_notes=(
        "Cocoa Absolute + dark base notes survive tropical heat well. "
        "The sub-threshold Calone and Indole in a heavy base matrix won't spike OAV at 35°C. "
        "The gourmand-vanillic base is climate-stable. Top notes from Ylang and Jasmine Sambac "
        "may accelerate — consider +20% top loading for Bangkok."
    ),
    anosmia_warnings=(
        "Multiple musk layers (Ethylene Brassylate + Iso E Super woody-musk) provide coverage. "
        "Beta-Ionone ~20% anosmia — compensated by Florol and Canthoxal as alternative violet-floral. "
        "No single-material anosmia would destroy the complex dark character."
    ),
    data_confidence="_RECONSTRUCTED from GCMS analysis (Archives Bendoni, 70 materials confirmed)",
)


# ---------------------------------------------------------------------------
# 6. Amouage Interlude Man
# ---------------------------------------------------------------------------

INTERLUDE_SKELETON = FormulaSkeleton(
    name="Interlude Man (Eau de Parfum)",
    house="Amouage",
    year=2012,
    perfumers="Christophe Raynaud",
    family=FragranceFamily.AMBER_ORIENTAL,
    concentration=ConcentrationBracket.EDP,
    structural_insight=(
        "The 'dramatic arc' construction method: the opening (bergamot-oregano-pimento) "
        "is deliberately jarring and incongruent with the heart (frankincense-cistus-amber). "
        "This friction is intentional — chaos resolved into serenity over 2-4 hours. "
        "The fragrance is structurally an 'interrupted journey' that tells a story of tension "
        "→ resolution. 6 weeks aging (3 maceration + 3 maturation) at 29% oil concentration."
    ),
    three_pillar_platform=None,  # Not platform-based — narrative arc
    materials=(
        ("Olibanum EO", 3.0, "Fresh frankincense top — OAV ~30"),
        ("Olibanum Resinoid", 2.0, "Resinous-balsamic frankincense base — OAV ~20"),
        ("Cistus / Labdanum Absolute", 2.0, "Cistus resinous warmth — OAV ~15"),
        ("Opoponax Resinoid", 1.5, "Sweet myrrh — bridges frankincense + amber — OAV ~12"),
        ("Benzoin Resinoid", 1.0, "Sweet balsamic fixer — OAV ~8"),
        ("Elemi EO", 0.5, "Pepper-citrus frankincense facet — OAV ~5"),
        ("Myrrh EO", 0.5, "Earthy-medicinal myrrh accent — OAV ~4"),
        ("Bergamot FCF", 3.0, "Hesperidic top — brief, deliberately jarring with oregano"),
        ("Oregano EO", 1.5, "Herbal-medicinal tension in opening — OAV ~30"),
        ("Pimento Berry Oil (Allspice)", 1.0, "Spicy-peppery tension — OAV ~15"),
        ("Leather Accord (IBQ 10%)", 0.1, "Leather-smoky suggestion — OAV ~2 (pure IBQ)"),
        ("Birch Tar (10%)", 0.05, "Smoky camphoraceous depth — OAV ~3 (pure)"),
        ("Agarwood / Oud Accord", 2.0, "Smoky-woody oud character"),
        ("Patchouli EO", 1.5, "Earthy grounding"),
        ("Sandalwood EO / Javanol", 1.0, "Creamy woody base"),
        ("Ambroxan", 0.5, "Amber-skin grounding"),
        ("Galaxolide 50%", 3.0, "Powdery musk fixative"),
    ),
    construction_method="dramatic arc (tension → resolution over 2-4 hours)",
    tropical_notes=(
        "Heavy resinous base (olibanum, cistus, opoponax, benzoin) survives tropical heat "
        "exceptionally well. The incense platform is climate-stable. Oregano and pimento top "
        "notes are high-VP — may accelerate 2.8× at 35°C → increase by 2× for Bangkok parity. "
        "29% oil concentration provides built-in tropical heat buffer."
    ),
    anosmia_warnings=(
        "Galaxolide ~25-30% anosmia — supplement with macrocyclic musk (Ambrettolide/Habanolide) "
        "for broader coverage. Ambroxan at low dose (0.5%) minimizes OR7A17 East Asian risk. "
        "Incense platform (olibanum, cistus, opoponax) universally perceived."
    ),
    data_confidence="_RECONSTRUCTED from official notes + GCMS data + fragrance community analysis",
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_SKELETONS: tuple[FormulaSkeleton, ...] = (
    SAUVAGE_SKELETON,
    CHANEL_NO5_SKELETON,
    AVENTUS_SKELETON,
    LAYTON_SKELETON,
    BLACK_ORCHID_SKELETON,
    INTERLUDE_SKELETON,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_skeleton(name: str) -> FormulaSkeleton | None:
    """Return a formula skeleton by case-insensitive name match."""
    key = name.lower()
    for sk in ALL_SKELETONS:
        if key in sk.name.lower():
            return sk
    return None


def list_skeletons() -> tuple[str, ...]:
    """Return all analyzed formula names."""
    return tuple(s.name for s in ALL_SKELETONS)


def get_three_pillar_platforms() -> dict[str, tuple[str, str, str] | None]:
    """Return the 3-pillar diffusion platforms for each formula."""
    return {s.name: s.three_pillar_platform for s in ALL_SKELETONS}


def get_construction_methods() -> dict[str, str]:
    """Return the construction method used by each formula."""
    return {s.name: s.construction_method for s in ALL_SKELETONS}


def get_tropical_notes(name: str) -> str | None:
    """Return tropical (Bangkok) formulation notes for a formula."""
    sk = get_skeleton(name)
    return sk.tropical_notes if sk else None


def get_anosmia_warnings(name: str) -> str | None:
    """Return anosmia risk analysis for a formula."""
    sk = get_skeleton(name)
    return sk.anosmia_warnings if sk else None


def find_formulas_by_family(family: FragranceFamily) -> tuple[FormulaSkeleton, ...]:
    """Return all analyzed formulas in a family."""
    return tuple(s for s in ALL_SKELETONS if s.family == family)


def get_aldehyde_quartet() -> AldehydeQuartet:
    """Return the Chanel No.5 aldehyde quartet target specification."""
    return AldehydeQuartet()


# ---------------------------------------------------------------------------
# Construction wisdom distilled from the 6 formulas
# ---------------------------------------------------------------------------

FIVE_LUXURY_PRINCIPLES: tuple[tuple[str, str, str], ...] = (
    (
        "Platform thinking",
        "Great luxury formulas are built on a 3-material diffusion platform "
        "(Hedione + Iso E Super/Norlimbanol + Ambroxan/musk), not individual notes.",
        "Sauvage: Ambroxan + Iso E Super + Hedione; Aventus: Helvetolide + Hedione + Iso E Super",
    ),
    (
        "Temporal drama",
        "The formula must be designed as a narrative arc — tension and release over time. "
        "Uniformly pleasant formulas are forgettable.",
        "Interlude: oregano-pimento tension → incense resolution → intimate base",
    ),
    (
        "Somatosensory dimension",
        "Sichuan pepper, cooling materials add a tactile dimension that purely olfactory "
        "formulas cannot achieve. The 'electric' character is partly neurological.",
        "Sauvage: Sichuan pepper tingling creates the 'electric' opening",
    ),
    (
        "Specific anosmia as design variable",
        "For Thai/East Asian market: ~20% Ambroxan anosmia means every Ambroxan-anchor "
        "formula loses impact for 1 in 5 consumers. Multi-class musk coverage is not optional.",
        "Sauvage: Habanolide + Ambrettolide backup for Ambroxan anosmics",
    ),
    (
        "Invisible infrastructure",
        "Norlimbanol, Vertofix Coeur, Cashmeran, Helional, Florol — the 'infrastructure "
        "materials' that make a formula feel expensive and three-dimensional.",
        "Layton: Norlimbanol at 8.5% as the 'Hedione of wood materials'",
    ),
)
