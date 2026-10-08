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
  3. Creed Aventus (2010, Hérault & Creed) — Dry-woods architecture with a
     bergamot/blackcurrant head and secondary pineapple heart accent
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
    materials: tuple[tuple[str, float | None, str], ...]  # (name, pct_in_conc, role)
    construction_method: str  # e.g., "platform-first", "dramatic arc", "abstract overlay"
    tropical_notes: str
    anosmia_warnings: str
    data_confidence: str = "_RECONSTRUCTED"


@dataclass(frozen=True, slots=True)
class ArchitectureLayer:
    """One evidence-bounded layer in a named-reference architecture."""

    layer: str
    prominence: str
    function: str
    markers: tuple[str, ...]
    evidence_class: str


@dataclass(frozen=True, slots=True)
class InventoryRoleMapping:
    """Map one ideal function to current stock without asserting equivalence."""

    target_function: str
    stock_materials: tuple[str, ...]
    status: str
    equivalence: bool
    note: str


@dataclass(frozen=True, slots=True)
class ArchitectureRelation:
    """A falsifiable relation between layers in the intended perfume."""

    relation: str
    target_link: str
    omission_loss: str
    failure_mode: str
    temporal_windows: tuple[str, ...]
    controlled_comparison: str


@dataclass(frozen=True, slots=True)
class AventusArchitectureModule:
    """Keep the Aventus target separate from a current-inventory projection."""

    target_ideal: tuple[ArchitectureLayer, ...]
    current_inventory_build: tuple[InventoryRoleMapping, ...]
    primary_rule: str
    head_priority: tuple[str, ...]
    secondary_fruit: tuple[str, ...]
    source_url: str
    build_status: str
    relations: tuple[ArchitectureRelation, ...]
    next_comparison: str
    component_count_used_as_complexity: bool = False
    predicted_oav_used_as_perception: bool = False
    composition_score_used_as_hedonic: bool = False
    quantitative_authority: str = "UNKNOWN"
    sensory_authority: str = "NOT_TESTED"
    formula_authority: bool = False
    physical_authority: bool = False
    safety_authority: bool = False
    release_authority: bool = False


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
        "VP rise is material-dependent in heat; amber projection in warmth depends "
        "on base support and logP-rich anchors more than a fixed multiplier."
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

AVENTUS_ARCHITECTURE = AventusArchitectureModule(
    target_ideal=(
        ArchitectureLayer(
            layer="cross_layer_spine",
            prominence="primary",
            function=(
                "Transparent diffusion, dry-wood continuity, and persistent musk carry the "
                "head through the smoky drydown; this is a design hypothesis, not an official formula."
            ),
            markers=(
                "transparent diffusion",
                "dry woody continuity",
                "persistent musk",
            ),
            evidence_class="SOURCE_DERIVED_DESIGN_HYPOTHESIS",
        ),
        ArchitectureLayer(
            layer="head",
            prominence="primary",
            function="Bergamot-led citrus with a distinct green-terpenic blackcurrant identity.",
            markers=(
                "Calabrian Bergamot",
                "Sicilian Lemon",
                "Blackcurrant Leaf Accord",
            ),
            evidence_class="OFFICIAL_BRAND_NOTE_ARCHITECTURE",
        ),
        ArchitectureLayer(
            layer="heart",
            prominence="secondary",
            function=(
                "A restrained pineapple accent crosses the bergamot/blackcurrant head into "
                "pink-pepper and jasmine radiance; fruit does not define the whole perfume."
            ),
            markers=("Pineapple Accord", "Pink Pepper", "Jasmine Accord"),
            evidence_class="OFFICIAL_BRAND_NOTE_ARCHITECTURE",
        ),
        ArchitectureLayer(
            layer="base",
            prominence="primary",
            function="Smoky-leathery birch, earthy patchouli, and musk form the lasting structure.",
            markers=("Birch", "Patchouli", "Musk Accord"),
            evidence_class="OFFICIAL_BRAND_NOTE_ARCHITECTURE",
        ),
    ),
    current_inventory_build=(
        InventoryRoleMapping(
            target_function="cross_layer_spine",
            stock_materials=(
                "Hedione",
                "Iso E Super",
                (
                    "Ambrox Super (25% w/w; 3.0 g Ambrox Super + 7.0 g DPG + "
                    "0.5 g IPM + 1.5 g ethanol; 12.0 g total; clear and homogeneous)"
                ),
            ),
            status="OWNED_FUNCTIONAL_MAPPING",
            equivalence=False,
            note=(
                "Candidate structural scaffold only; exact ratios and OAV-per-time remain uncalibrated."
            ),
        ),
        InventoryRoleMapping(
            target_function="bergamot_head",
            stock_materials=("Bergamot FCF oil Sicilian",),
            status="OWNED_FUNCTIONAL_PROXY",
            equivalence=False,
            note="Owned Sicilian FCF stock is not proven equivalent to Creed's Calabrian material.",
        ),
        InventoryRoleMapping(
            target_function="blackcurrant_head",
            stock_materials=("Blackcurrant Absolute (10% in DPG)",),
            status="OWNED_FUNCTIONAL_PROXY_COMPOSITE_OAV_REQUIRED",
            equivalence=False,
            note=(
                "The owned absolute is a rational cassis proxy, not Creed's proprietary leaf accord."
            ),
        ),
        InventoryRoleMapping(
            target_function="pineapple_heart_accent",
            stock_materials=("Allyl Amyl Glycolate (10%)",),
            status="OWNED_SECONDARY_ACCENT",
            equivalence=False,
            note=(
                "Use only after bergamot and blackcurrant are established; green-galbanum drift is the "
                "principal failure mode."
            ),
        ),
        InventoryRoleMapping(
            target_function="pink_pepper_bridge",
            stock_materials=("Pink Pepper EO (Schinus molle; neat / as supplied)",),
            status="OWNED_CURRENT_INVENTORY_EXECUTION_READY_RAW_VOLUME_ONLY",
            equivalence=False,
            note=(
                "User-confirmed neat Schinus molle EO is the authoritative physical stock and is "
                "now recorded in inventory.txt with a literature-partial natural-mixture composite. "
                "The pinned current-inventory overlay binds raw-stock volume transfer only. Keep the "
                "older Pink Pepper EO / CO2 requirement as a separate GAP; "
                "Black Pepper EO is not equivalent."
            ),
        ),
        InventoryRoleMapping(
            target_function="jasmine_radiance_bridge",
            stock_materials=("Hedione", "Dihydrojasmone"),
            status="OWNED_FUNCTIONAL_MAPPING",
            equivalence=False,
            note="Radiance support, not proof of Creed's jasmine accord composition.",
        ),
        InventoryRoleMapping(
            target_function="smoky_birch_effect",
            stock_materials=("Cade Oil Rectified (1% in DPG)", "Suederal (10%)"),
            status="OWNED_NON_EQUIVALENT_EFFECT_MAPPING",
            equivalence=False,
            note=(
                "Birch Tar Rectified is excluded from this current-stock projection because the live "
                "inventory marks it IFRA prohibited; smoke and suede remain separate functions."
            ),
        ),
        InventoryRoleMapping(
            target_function="patchouli_earth_wood_bridge",
            stock_materials=("Patchouli EO",),
            status="OWNED_DIRECT_ROLE",
            equivalence=False,
            note="Exact origin, batch, and reference equivalence remain unproven.",
        ),
        InventoryRoleMapping(
            target_function="persistent_musk_projection",
            stock_materials=("Romandolide",),
            status="OWNED_SINGLE_MUSK_MAPPING",
            equivalence=False,
            note=(
                "Chosen as a single outward-diffusion musk; it is not Helvetolide and does not prove "
                "reference equivalence."
            ),
        ),
    ),
    primary_rule=(
        "The perfume architecture is primary: dry woody-musk continuity, a bergamot/blackcurrant "
        "head, a controlled aromatic-floral bridge, and a smoky patchouli drydown. Pineapple and "
        "other fruit are secondary accents."
    ),
    head_priority=("Bergamot FCF oil Sicilian", "Blackcurrant Absolute (10% in DPG)"),
    secondary_fruit=("Allyl Amyl Glycolate (10%)",),
    source_url="https://creedboutique.com/products/aventus",
    build_status=(
        "DESIGN_MAPPING_ONLY_SCHINUS_PINNED_OVERLAY_AUTHORITY_HOLD_"
        "PPM_ODT_OAV_SAFETY_AND_SENSORY_GATES_NOT_RUN"
    ),
    relations=(
        ArchitectureRelation(
            relation=(
                "Bergamot brightness and blackcurrant's green-terpenic contrast state the "
                "opening before pineapple supplies a short secondary fruit flash."
            ),
            target_link=(
                "Preserves the official head-versus-heart order and the requested hierarchy."
            ),
            omission_loss=(
                "Without the bergamot/blackcurrant lead, the opening loses the named reference's "
                "citrus-cassis articulation; without the restrained pineapple accent, it loses a "
                "recognizable but non-dominant transition cue."
            ),
            failure_mode=(
                "Pineapple or generic fruit becomes the subject, or blackcurrant is mistaken for "
                "a pineapple substitute."
            ),
            temporal_windows=("opening", "opening_to_heart"),
            controlled_comparison=(
                "At formula stage, compare an architecture-first head with a pineapple-forward "
                "head at constant concentrate total and matched carrier, holding the structural "
                "spine and base fixed; calculate stock-specific ppm, ODT, composite-natural OAV, "
                "and OAV-per-time before compounding."
            ),
        ),
        ArchitectureRelation(
            relation=(
                "Transparent diffusion and dry-wood continuity carry the citrus-cassis opening "
                "through the pepper-jasmine heart without becoming a separate amberwood perfume."
            ),
            target_link=(
                "Makes architecture, continuity, and smell primary rather than a list of fruit notes."
            ),
            omission_loss=(
                "The top, heart, and base read as disconnected accords rather than one evolving object."
            ),
            failure_mode=(
                "The scaffold becomes a generic loud woody-amber cloud or masks the named head and base."
            ),
            temporal_windows=("opening", "heart", "late_heart", "drydown"),
            controlled_comparison=(
                "At formula stage, compare the smallest viable scaffold with a scaffold omission at "
                "constant total and matched carrier while preserving the same character-note active doses."
            ),
        ),
        ArchitectureRelation(
            relation=(
                "The pepper-jasmine bridge and restrained fruit hand off into smoky birch effect, "
                "patchouli earth, and persistent musk."
            ),
            target_link=(
                "Returns the perfume to its dry, smoky, earthy structure after the recognizable fruit cue."
            ),
            omission_loss=(
                "The perfume either collapses after the opening or dries down as an unrelated clean musk."
            ),
            failure_mode=(
                "Smoke/leather takes over, patchouli becomes muddy, or the base remains a generic musk-amber."
            ),
            temporal_windows=("heart", "late_heart", "drydown"),
            controlled_comparison=(
                "At formula stage, use separate constant-total, carrier-matched smoke-effect and "
                "patchouli-bridge omissions; do not infer their interaction from pairwise chemistry alone."
            ),
        ),
    ),
    next_comparison=(
        "Architecture-first versus pineapple-forward opening, constant concentrate total and matched "
        "carrier, with identical dry-wood/musk spine and birch/patchouli/musk base; evaluate blind at "
        "opening, 5 minutes, 30 minutes, 2 hours, and 4 hours only after ppm/ODT/OAV preflight."
    ),
)


AVENTUS_SKELETON = FormulaSkeleton(
    name="Aventus (Eau de Parfum)",
    house="Creed",
    year=2010,
    perfumers="Jean-Christophe Hérault & Erwin Creed",
    family=FragranceFamily.CHYPRE,  # Dry Woods / Fruity Chypre neighborhood
    concentration=ConcentrationBracket.EDP,
    structural_insight=(
        "Aventus is treated here as an architecture, not a pineapple accord: a transparent "
        "dry-wood/musk spine carries a bergamot-and-blackcurrant head through a restrained "
        "pineapple, pepper, and jasmine heart into smoky birch, patchouli, and musk."
    ),
    three_pillar_platform=None,
    materials=(
        (
            "Transparent diffusion platform",
            None,
            "Primary cross-layer function; a Helvetolide/Ambroxan-style platform is a hypothesis.",
        ),
        ("Dry woody continuity", None, "Primary cross-layer structural function."),
        ("Birch accord", None, "Primary smoky-leathery depth and transition into the base."),
        ("Patchouli", None, "Primary earthy wood bridge."),
        ("Musk accord", None, "Primary persistence and spatial continuity."),
        ("Bergamot", None, "Primary head material and citrus identity."),
        ("Blackcurrant leaf accord", None, "Primary head contrast; green-terpenic cassis identity."),
        ("Sicilian lemon", None, "Supporting head citrus."),
        ("Pink pepper", None, "Supporting aromatic-spice heart bridge."),
        ("Jasmine accord", None, "Supporting radiant heart bridge."),
        ("Pineapple accord", None, "Secondary heart-reaching fruit accent, never the architecture."),
    ),
    construction_method=(
        "architecture-first (cross-layer dry-wood/musk spine + bergamot/blackcurrant head + "
        "restrained pineapple heart accent + birch/patchouli/musk drydown)"
    ),
    tropical_notes=(
        "No fixed Bangkok rebasing is authorized from note architecture alone. A concrete build "
        "must be evaluated with stock-specific ppm, ODT, composite-natural OAV, and OAV-per-time "
        "at the requested temperature."
    ),
    anosmia_warnings=(
        "No exact commercial formula or OAV distribution is established, so population coverage "
        "cannot be inferred from this architecture record. Validate the chosen musk/amber/wood "
        "scaffold in controlled smelling rather than assuming universal perception."
    ),
    data_confidence=(
        "OFFICIAL_BRAND_NOTE_ARCHITECTURE_ONLY + SOURCE_DERIVED_PLATFORM_HYPOTHESIS; "
        "QUANTITATIVE_FORMULA_UNKNOWN; SENSORY_SIMILARITY_NOT_TESTED"
    ),
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
        "notes are high-VP and can be perceived faster in heat; apply only "
        "small base increases (roughly 1.5-2.5×) when needed for target retention. "
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


def get_aventus_architecture_module() -> AventusArchitectureModule:
    """Return the architecture-first Aventus target and stock projection."""

    return AVENTUS_ARCHITECTURE


# ---------------------------------------------------------------------------
# Construction wisdom distilled from the 6 formulas
# ---------------------------------------------------------------------------

FIVE_LUXURY_PRINCIPLES: tuple[tuple[str, str, str], ...] = (
    (
        "Platform thinking",
        "Great luxury formulas are built on a 3-material diffusion platform "
        "(Hedione + Iso E Super/Norlimbanol + Ambroxan/musk), not individual notes.",
        (
            "Sauvage: Ambroxan + Iso E Super + Hedione; Aventus: a source-derived "
            "Helvetolide/Ambroxan-style hypothesis carried below the official note architecture"
        ),
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


