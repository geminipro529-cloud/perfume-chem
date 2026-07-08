"""Family-specific hedonic optimization — OAV targets, material recommendations, character zones.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the family-specific hedonic optimization rules from the Formulation
Intelligence Database (Part IV). Each fragrance family has:
  - Recommended construction methodology
  - Defining materials with OAV targets
  - Secret/amplifier materials
  - Common pitfalls and performance optimization
  - Post-IFRA reconstruction strategies
  - Character shift zones and cliff warnings

Integrates with the gate-first pipeline by providing OAV target ranges that
can be used as constraints in FormulaOptimizer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from ._shared_types import (
    ConcentrationBracket,
    FragranceFamily,
    HedonicCategory,
    MethodologyType,
    NoteTier,
    TextureLayer,
)


# ---------------------------------------------------------------------------
# Family-specific hedonic profiles
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FamilyMaterialTarget:
    """OAV target and role for a material within a specific fragrance family."""

    material: str
    target_oav_min: float
    target_oav_max: float
    role: str                    # character driver, modifier, fixative, bridge, etc.
    hedonic: float               # hedonic contribution in this family context
    note_tier: NoteTier | None = None
    is_secret: bool = False      # "secret" amplifier material
    cliff_oav: float | None = None       # OAV above which character flips
    cliff_description: str | None = None


@dataclass(frozen=True, slots=True)
class FamilyHedonicProfile:
    """Complete hedonic optimization profile for a fragrance family."""

    family: FragranceFamily
    description: str
    recommended_methods: tuple[MethodologyType, ...]
    primary_materials: tuple[FamilyMaterialTarget, ...]
    secret_materials: tuple[FamilyMaterialTarget, ...]
    pitfalls: tuple[str, ...]
    performance_tips: tuple[str, ...]
    market_notes: dict[str, str] = field(default_factory=dict)
    ifra_changes: tuple[str, ...] = ()
    reconstruction_notes: str = ""


# ---------------------------------------------------------------------------
# Family profiles
# ---------------------------------------------------------------------------

CITRUS_HESPERIDIC = FamilyHedonicProfile(
    family=FragranceFamily.CITRUS,
    description="Citrus is the highest-VP family — the problem is longevity, not character.",
    recommended_methods=(MethodologyType.PYRAMID, MethodologyType.PERFORMANCE_FIRST),
    primary_materials=(
        FamilyMaterialTarget("Bergamot FCF", 100, 200, "Hesperidic heart — linalool+linalyl acetate dominant", +3.5, NoteTier.TOP),
        FamilyMaterialTarget("Limonene", 30, 80, "Mass-dominant but NOT character-dominant; VP 190 Pa", +1.0, NoteTier.TOP),
        FamilyMaterialTarget("Linalool", 50, 120, "Character-dominant in bergamot despite not mass-dominant", +3.0, NoteTier.TOP),
        FamilyMaterialTarget("Dihydromyrcenol", 30, 80, "Transparent diffusion amplifier, long-lasting VP ~3 Pa", +2.5, NoteTier.HEART),
        FamilyMaterialTarget("Hedione", 20, 60, "Bridges citrus top with floral heart, radiance", +3.0, NoteTier.HEART),
        FamilyMaterialTarget("Lemon EO", 50, 120, "High-impact hesperidic brightness", +3.0, NoteTier.TOP),
        FamilyMaterialTarget("Orange Sweet EO", 30, 80, "Warm sweet citrus, bridges to floral", +2.5, NoteTier.TOP),
        FamilyMaterialTarget("Mandarin EO", 40, 100, "Creamy-citrus sweetness, softer than orange", +3.0, NoteTier.TOP),
        FamilyMaterialTarget("Petitgrain Bigarade", 10, 30, "Woody-green complexity sub-note", +2.0, NoteTier.HEART),
        FamilyMaterialTarget("Grapefruit EO", 20, 60, "Sulfurous grapefruit character (1-p-menthene-8-thiol)", +2.5, NoteTier.TOP),
    ),
    secret_materials=(
        FamilyMaterialTarget(
            "1-p-Menthene-8-thiol", 0.0001, 0.001 * 100,
            "Photorealistic grapefruit — lowest ODT of any food odorant (0.000034 ng/L air)",
            +4.0, NoteTier.TOP, is_secret=True,
        ),
        FamilyMaterialTarget(
            "Aldehyde C10", 20, 60, "Brightens citrus headspace at trace", +2.0, NoteTier.TOP, is_secret=True,
        ),
        FamilyMaterialTarget(
            "Aldehyde C11", 15, 40, "Adds sparkle-fresh dimension", +2.0, NoteTier.TOP, is_secret=True,
        ),
    ),
    pitfalls=(
        "Overdosing limonene (mass waste without character contribution)",
        "Under-loading base — EdC/EdT cannot project base notes; use 2-3x EdP base loading",
        "Ignoring tropical humidity — VP x2.8 at 35°C; Bangkok formulas need 2.5-3x base vs Paris",
        "Using phototoxic bergamot (use FCF only for leave-on)",
        "Synthetic citrus accord without any natural EO lacks depth and roundness",
    ),
    performance_tips=(
        "Dihydromyrcenol + Hedione + Iso E Super form a 'citrus fixation platform'",
        "Use Ambroxan at 0.5-1.5% for citrus skin-anchor",
        "Galaxolide 50% at 3-8% for powdery long-dry background",
        "BHT 0.01-0.05% to prevent limonene autoxidation",
    ),
    market_notes={
        "tropical": "Increase base loading 2.5-3x for Bangkok/HCMC/Singapore",
        "fresh_current": "Dihydromyrcenol-heavy is the modern transparent laundry-citrus signature",
    },
)

AROMATIC_FOUGERE_PROFILE = FamilyHedonicProfile(
    family=FragranceFamily.AROMATIC_FOUGERE,
    description="The fougère is architecturally the most structured family — a 3-accord formula defines it.",
    recommended_methods=(MethodologyType.ACCORD_BASED,),
    primary_materials=(
        FamilyMaterialTarget("Lavender EO (40/42)", 80, 150, "Aromatic top — linalool + linalyl acetate backbone", +3.5, NoteTier.TOP),
        FamilyMaterialTarget("Linalool", 40, 80, "Fresh floral-lavender heart of the accord", +3.0, NoteTier.TOP),
        FamilyMaterialTarget("Coumarin", 15, 40, "Hay-tonka base — the first synthetic in perfumery (1882)", +3.5, NoteTier.BASE, cliff_oav=60, cliff_description="Bitter-almond aggressive above OAV 60"),
        FamilyMaterialTarget("Bergamot FCF", 80, 150, "Hesperidic top note in the fougère triad", +3.0, NoteTier.TOP),
        FamilyMaterialTarget("Geranium EO", 30, 60, "Green-rosy heart complexity", +3.0, NoteTier.HEART),
        FamilyMaterialTarget("Oakmoss / Veramoss", 5, 20, "Mossy-earthy base (IFRA-limited to 0.1% finished)", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Iso E Super", 30, 80, "Woody-cedar modern amplifier", +2.5, NoteTier.BASE),
        FamilyMaterialTarget("Galaxolide 50%", 20, 50, "Powdery musk fixative", +3.0, NoteTier.BASE),
    ),
    secret_materials=(
        FamilyMaterialTarget("Tonka Bean Absolute", 5, 15, "Bridges coumarin-lavender with warm milky-sweet nuance", +3.5, NoteTier.BASE, is_secret=True),
        FamilyMaterialTarget("Clary Sage EO", 10, 25, "Ambra-lavender complexity with herbaceous depth", +2.5, NoteTier.HEART, is_secret=True),
        FamilyMaterialTarget("Ambroxan", 15, 50, "Modernizes the dry-down without defacing fougère identity", +3.0, NoteTier.BASE, is_secret=True),
        FamilyMaterialTarget("Dihydroabietic Acid", 3, 10, "Earthy-resinous oakmoss replacer (synthetic: Veramoss at 0.5%)", +2.0, NoteTier.BASE, is_secret=True),
    ),
    pitfalls=(
        "Oakmoss limited to 0.1% in finished product — classical fougère 2-5% oakmoss now impossible",
        "Under-estimating coumarin IFRA limit (max 1.5% in finished product)",
        "Niche fougère must emphasize herbal sharpness — smooth mainstream fougère loses genre identity",
        "Avoid amber overdose — fougère is aromatic, not oriental; labdanum above 0.5% shifts family",
    ),
    performance_tips=(
        "Post-IFRA: Replace oakmoss with Evernyl (Veramoss) + Cedramoss",
        "Coumarin at 0.5-1.0% (below IFRA limit); supplement with Tonka Bean Absolute",
        "Ambroxan at 0.5-1.0% modernizes without defacing",
        "Classic triad: Lavender 28%, Bergamot 16%, Coumarin 5% of concentrate",
    ),
    ifra_changes=(
        "Oakmoss Absolute: 2-5% in classical → 0.10% finished product (effectively 0.4% in concentrate)",
        "Coumarin: 1.50% max in finished product",
        "Supplement with Evernyl/Veramoss + Clearwood + Cedramoss",
    ),
)

FLORAL_JASMINE_PROFILE = FamilyHedonicProfile(
    family=FragranceFamily.FLORAL_JASMINE,
    description="Jasmine absolute GC analysis: benzyl acetate 23-27%, benzyl benzoate 18-21%, linalool 3-8%, indole 1.4-1.8%.",
    recommended_methods=(MethodologyType.ACCORD_BASED, MethodologyType.HEDONIC_OPTIMIZATION),
    primary_materials=(
        FamilyMaterialTarget("Benzyl Acetate", 20, 40, "Fresh-floral jasmine skeleton — ODT ethanol ~50 ppb", +3.5, NoteTier.HEART),
        FamilyMaterialTarget("Hedione", 40, 80, "Radiance + VN1R1 pheromone receptor activation", +4.0, NoteTier.HEART),
        FamilyMaterialTarget("Linalool", 10, 25, "Transparent floral bridge", +3.0, NoteTier.TOP),
        FamilyMaterialTarget("Benzyl Benzoate", 3, 8, "Fixative matrix (not character-dominant)", +1.5, NoteTier.BASE),
        FamilyMaterialTarget("Indole", 2, 5, "Animalic depth — sweet-spot at narcotic jasmine zone", +4.5, NoteTier.HEART, cliff_oav=15, cliff_description="OAV > 15 → fecal shift (sharp cliff, not gradual)"),
        FamilyMaterialTarget("Cis-Jasmone", 2, 4, "Photorealistic green-jasmine freshness", +3.0, NoteTier.HEART),
        FamilyMaterialTarget("Methyl Anthranilate", 1, 3, "Grape-orange blossom nuance", +2.5, NoteTier.HEART),
        FamilyMaterialTarget("Methyl Benzoate", 3, 8, "Orris-jasmine bridge, almond-floral", +2.5, NoteTier.HEART),
        FamilyMaterialTarget("Eugenol", 2, 6, "Spicy-warm depth from natural jasmine absolute", +2.0, NoteTier.HEART),
    ),
    secret_materials=(
        FamilyMaterialTarget("Jasmine Absolute (India)", 5, 15, "Luxury anchor — adds 1.4-1.8% indole contribution", +5.0, NoteTier.HEART, is_secret=True),
        FamilyMaterialTarget("Ylang Ylang EO Extra", 5, 15, "Adds narcotic-banana complexity to jasmine", +3.5, NoteTier.HEART, is_secret=True),
        FamilyMaterialTarget("Hedione HC", 30, 120, "High-cis isomer — VN1R1 activation at lower OAV", +4.5, NoteTier.HEART, is_secret=True),
        FamilyMaterialTarget("Ambrettolide", 5, 10, "Milky-musky softness beneath jasmine", +3.0, NoteTier.BASE, is_secret=True),
    ),
    pitfalls=(
        "Indole cliff: at 0.01-0.1% in concentrate → narcotic jasmine; at 1%+ → abruptly fecal — transition is not gradual",
        "Methyl anthranilate + aldehydes → Schiff base formation (brown-orange shift, avoid combining)",
        "Jasmine synthetic accord without Hedione lacks radiance (VN1R1 pathway inaccessible)",
        "Over-reliance on benzyl acetate — becomes thin and synthetic at high doses",
        "Natural jasmine absolute indole content (~1.4-1.8%) must be factored into total indole budget",
    ),
    performance_tips=(
        "Jasmine absolute contains ~1.4-1.8% indole — at 2% formula use = 0.028-0.036% effective indole (safe in jasmine zone)",
        "Hedione at OAV 40-80 activates VN1R1; Hedione HC requires lower concentration for same activation",
        "Benzyl Benzoate at 5-10% of concentrate functions as hydrogen-bonding fixative matrix",
        "Indole working dilution: 10% in DPG for precise dosing",
    ),
    market_notes={
        "indole_control": "Indole at 0.01-0.1% in concentrate = narcotic jasmine. At 1%+ = fecal. Sharp cliff.",
        "hedione_trade": "Hedione vs Hedione HC: HC activates VN1R1 at 1/3 the concentration",
    },
)

FLORAL_ROSE_PROFILE = FamilyHedonicProfile(
    family=FragranceFamily.FLORAL_ROSE,
    description="Rose accord: Phenethyl Alcohol + Geraniol + Citronellol backbone, Damascenone for radiance, Rose Oxide for metallic-green lift.",
    recommended_methods=(MethodologyType.ACCORD_BASED, MethodologyType.PYRAMID),
    primary_materials=(
        FamilyMaterialTarget("Phenethyl Alcohol", 40, 100, "Honeyed-rose heart — the dominant character of most rose synthetics", +3.5, NoteTier.HEART),
        FamilyMaterialTarget("Geraniol", 30, 80, "Fresh rosy-green top-heart — mass-dominant in rose absolute", +3.0, NoteTier.HEART),
        FamilyMaterialTarget("Citronellol", 20, 60, "Clean lemon-rose modifier — softens geraniol sharpness", +3.0, NoteTier.HEART),
        FamilyMaterialTarget("Rose Oxide", 2, 8, "Metallic-green rose lift — trace-level character driver", +3.5, NoteTier.HEART, cliff_oav=15, cliff_description="OAV > 15: metallic-coin off-note"),
        FamilyMaterialTarget("Damascenone", 1, 5, "Radiant fruity-floral rose top — ODT ~0.01 ppb", +4.0, NoteTier.HEART),
        FamilyMaterialTarget("Hedione", 15, 40, "Transparent radiance bridge between rose and woody base", +3.0, NoteTier.HEART),
        FamilyMaterialTarget("Iso E Super", 20, 50, "Woody-amber fixative — modern rose backbone", +2.5, NoteTier.BASE),
        FamilyMaterialTarget("Benzyl Benzoate", 5, 12, "Fixative matrix and solvent for rose crystals", +1.5, NoteTier.BASE),
    ),
    secret_materials=(
        FamilyMaterialTarget("Alpha Damascone", 2, 6, "Metallic-rose apple nuance — niche rose depth", +3.5, NoteTier.HEART, is_secret=True),
        FamilyMaterialTarget("Beta Damascone", 1, 4, "Fruity-plum rose undertone", +3.0, NoteTier.HEART, is_secret=True),
        FamilyMaterialTarget("Damascol", 2, 5, "Soft rounded plum-rose alcohol — modern rose alternative", +3.0, NoteTier.HEART, is_secret=True),
        FamilyMaterialTarget("PEA (Phenylethyl Alcohol)", 5, 15, "Traditional Bulgarian rose absolute anchor", +3.5, NoteTier.HEART, is_secret=True),
    ),
    pitfalls=(
        "Rose Oxide cliff: metallic-green rose at OAV 2-8; metallic-coin off-note above OAV 15",
        "Damascone overdose: fruity-metallic at low dose; cooked-apple off-note above OAV 10",
        "Synthetic rose accord without citronellol = sharp and geraniol-dominant (lacks roundness)",
        "PEA overdose: honeyed-rose becomes cloying and soapy above 5% in concentrate",
        "Natural rose absolute (Rosa damascena) at 2-5% provides irreplaceable complexity but is costly",
    ),
    performance_tips=(
        "Modern rose platform: PEA 40 + Geraniol 30 + Citronellol 20 + Rose Oxide 2 + Damascenone 1 + Hedione 20 + Iso E Super 30 parts",
        "For Thai market: increase Iso E Super and add Ambrox Super for skin-anchor in humidity",
        "Rose accord without fixative = 2-hour skin time; minimum 10% benzyl benzoate or equivalent fixative",
        "Damascone working dilution: 10% in DPG for precise trace dosing",
    ),
    ifra_changes=(
        "Rose materials generally unrestricted; Damascone Beta is IFRA-restricted (sensitization)",
        "Farnesol is a declared EU allergen — present in natural rose absolute",
    ),
)

CHYPRE_PROFILE = FamilyHedonicProfile(
    family=FragranceFamily.CHYPRE,
    description="The olfactory triptych: Bergamot (hesperidic top) + Labdanum (balsamic bridge) + Oakmoss/Patchouli (earthy base).",
    recommended_methods=(MethodologyType.PYRAMID, MethodologyType.ACCORD_BASED),
    primary_materials=(
        FamilyMaterialTarget("Bergamot FCF", 100, 200, "Hesperidic opening — MW 136-154 g/mol, brief", +3.0, NoteTier.TOP),
        FamilyMaterialTarget("Labdanum Absolute", 15, 30, "Balsamic-resinous bridge — unrestricted, essential for chypre identity", +3.5, NoteTier.BASE),
        FamilyMaterialTarget("Oakmoss Absolute", 5, 15, "Earthy-mossy base — restricted to 0.1% finished (max 0.4% in concentrate)", +3.5, NoteTier.BASE),
        FamilyMaterialTarget("Patchouli EO", 20, 50, "Earthy-camphoraceous base", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Rose Absolute", 10, 25, "Floral heart that bridges bergamot and moss", +4.0, NoteTier.HEART),
        FamilyMaterialTarget("Jasmine Absolute", 5, 15, "White floral complexity in chypre heart", +3.5, NoteTier.HEART),
        FamilyMaterialTarget("Vetiver EO", 10, 25, "Smoky-earthy green base", +2.5, NoteTier.BASE),
        FamilyMaterialTarget("Iso E Super", 30, 80, "Woody-cedar amplifier", +2.5, NoteTier.BASE),
        FamilyMaterialTarget("Sandalwood EO", 10, 25, "Creamy-woody dry-down", +4.0, NoteTier.BASE),
        FamilyMaterialTarget("Galaxolide 50%", 20, 50, "Powdery musk fixative", +3.0, NoteTier.BASE),
    ),
    secret_materials=(
        FamilyMaterialTarget("Birch Tar", 0.5, 2, "Smoky-medicinal contrast — the chypre 'flaw'", +2.0, NoteTier.BASE, is_secret=True, cliff_oav=8, cliff_description="OAV > 8: medicinal-barbecue off-note"),
        FamilyMaterialTarget("Evernyl (Veramoss)", 5, 15, "Post-IFRA oakmoss substitute — dry-earthy facet", +3.0, NoteTier.BASE, is_secret=True),
        FamilyMaterialTarget("Clearwood", 10, 25, "Fermentation-derived clean patchouli — DSM-Firmenich 2014", +2.5, NoteTier.BASE, is_secret=True),
        FamilyMaterialTarget("Akigalawood", 5, 15, "Earthy patchouli-oud character", +3.0, NoteTier.BASE, is_secret=True),
        FamilyMaterialTarget("Ambroxan", 15, 50, "Modern amber-skin replacing moss warmth", +3.0, NoteTier.BASE, is_secret=True),
    ),
    pitfalls=(
        "Oakmoss limited to 0.1% in finished product — classical chypre 2-5% oakmoss now structurally impossible",
        "Labdanum overdose → oriental shift (amber family); keep <30 parts in backbone",
        "Fruity chypre: gamma-undecalactone OAV 3-10 for peach (Mitsouko archetype)",
        "Modern chypre without labdanum: loses identity — labdanum is non-negotiable",
    ),
    performance_tips=(
        "Post-IFRA neo-chypre: Bergamot + Patchouli (clean) + Labdanum + Ambroxan + transparent musks",
        "Modern chypres replace oakmoss with patchouli (clean fraction), Ambroxan, and transparent musks",
        "Classical backbone (unrestricted): Bergamot 250, Oakmoss 30, Rose 20, Jasmine 50, Patchouli 30, Sandalwood 70, Vetiver 50, Labdanum 30 (parts)",
    ),
    ifra_changes=(
        "Oakmoss Cat4 limit = 0.10% finished product → max 0.4% in 25% EdP concentrate",
        "Treemoss similarly restricted to 0.10%",
        "Replacement: Evernyl/Veramoss, Clearwood, Cedramoss",
    ),
)

AMBER_ORIENTAL_PROFILE = FamilyHedonicProfile(
    family=FragranceFamily.AMBER_ORIENTAL,
    description="Amber accord: Labdanum 30-40 + Benzoin 20-30 + Vanillin 5-10 + Styrax 10-15 + Tolu Balsam 5-10 + Benzyl Benzoate 15-20 parts.",
    recommended_methods=(MethodologyType.PYRAMID, MethodologyType.HEDONIC_OPTIMIZATION),
    primary_materials=(
        FamilyMaterialTarget("Labdanum Absolute", 15, 30, "Balsamic-resinous amber core", +3.5, NoteTier.BASE),
        FamilyMaterialTarget("Benzoin Resinoid", 10, 25, "Smoky-sweet vanilla-balsamic depth", +3.5, NoteTier.BASE),
        FamilyMaterialTarget("Vanillin", 30, 100, "Sweet-creamy vanilla — ODT ethanol ~400-500 ppb", +3.5, NoteTier.BASE, cliff_oav=200, cliff_description="OAV > 200 → plasticky-artificial"),
        FamilyMaterialTarget("Benzyl Benzoate", 5, 12, "Fixative-diluent, hydrogen-bonding matrix (IFRA max 4.8% finished)", +1.5, NoteTier.BASE),
        FamilyMaterialTarget("Styrax EO", 5, 15, "Leathery-smoky balsamic resin", +2.5, NoteTier.BASE),
        FamilyMaterialTarget("Tolu Balsam", 5, 12, "Sweet-cinnamon balsamic warmth", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Coumarin", 10, 25, "Hay-tonka bridge in amber (IFRA max 1.5%)", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Ethyl Maltol", 10, 30, "Caramelized sweetness at low dose (ODT ~10 ppb)", +2.5, NoteTier.BASE, cliff_oav=150, cliff_description="OAV > 150 → burnt sugar-artificial"),
    ),
    secret_materials=(
        FamilyMaterialTarget("Indole", 0.5, 3, "Trace animalic = 'seasoning' for animalic oriental; never exceed OAV 5", +1.0, NoteTier.HEART, is_secret=True),
        FamilyMaterialTarget("Castoreum Absolute", 2, 6, "Leathery-animalic depth for animalic oriental", +2.0, NoteTier.BASE, is_secret=True),
        FamilyMaterialTarget("Ethylene Brassylate", 10, 25, "Cruelty-free muscone substitute — soft musk body", +3.0, NoteTier.BASE, is_secret=True),
        FamilyMaterialTarget("Gamma-Decalactone", 5, 15, "Peachy-creamy lactone that lifts heavy amber", +3.0, NoteTier.HEART, is_secret=True),
    ),
    pitfalls=(
        "Vanillin above 5% in concentrate → plasticky shift",
        "Amber/oriental without Labdanum → generic sweet base (labdanum is the amber)",
        "Animalic over-dose: indole OAV > 5 reads fecal in amber context",
        "Benzyl Benzoate above 4.8% finished → IFRA Cat4 violation",
    ),
    performance_tips=(
        "Amber/oriental most suited to tropical climates — heavy base survives high-T evaporation",
        "2.8x VP at 35°C increases sillage; base remains stable unlike citrus/floral families",
        "Animalic oriental: Muscone/Ethylene Brassylate + Indole 0.05% + Castoreum (not OAV > 5)",
        "Benzyl Benzoate at 5-10% of concentrate as molecular cohesive agent",
    ),
)

WOODY_SANDALWOOD_PROFILE = FamilyHedonicProfile(
    family=FragranceFamily.WOODY_AMBER,
    description="Modern sandalwood accord: Javanol 2-4 + Bacdanol 3-5 + Polysantol 2-3 + Sandela 2-3 + Norlimbanol 1-2 parts.",
    recommended_methods=(MethodologyType.SINGLE_MATERIAL, MethodologyType.MINIMAL_MATERIAL),
    primary_materials=(
        FamilyMaterialTarget("Javanol", 10, 40, "Creamy sandalwood-rose — VP 0.03 Pa, CAS 198404-98-7, MW 222.37", +4.5, NoteTier.HEART),
        FamilyMaterialTarget("Iso E Super", 40, 150, "Woody-cedar skin amplifier — logP 5.3", +2.5, NoteTier.BASE),
        FamilyMaterialTarget("Ambroxan", 20, 80, "Skin-amber grounding — OR7A17 receptor", +3.5, NoteTier.BASE),
        FamilyMaterialTarget("Bacdanol", 15, 40, "Creamy-floral sandalwood facet", +3.5, NoteTier.HEART),
        FamilyMaterialTarget("Polysantol", 10, 25, "Transparent woody", +3.0, NoteTier.HEART),
        FamilyMaterialTarget("Norlimbanol", 5, 15, "Earthy-woody fixative edge", +2.0, NoteTier.BASE),
        FamilyMaterialTarget("Vetiver EO (Haitian)", 5, 25, "Smoky-earthy complexity — anchor material", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Cedarwood EO (Atlas)", 10, 25, "Pencil-shavings woody warmth", +2.5, NoteTier.BASE),
    ),
    secret_materials=(
        FamilyMaterialTarget("Sandalwood EO (Mysore)", 5, 15, "Authentic sandalwood anchor (if budget allows)", +5.0, NoteTier.BASE, is_secret=True),
        FamilyMaterialTarget("Cashmeran", 10, 25, "Warm-woody mineral texture", +3.0, NoteTier.BASE, is_secret=True),
        FamilyMaterialTarget("Hedione", 10, 25, "Transparent radiance that lifts woody without floral character", +2.0, NoteTier.HEART, is_secret=True),
    ),
    pitfalls=(
        "Javanol at > 0.1% in formula → aggressive; effective at < 0.1%",
        "Ambroxan anosmia: ~20% East Asian populations cannot detect it (OR7A17 non-functional alleles)",
        "Iso E Super anosmia: ~20-25% general population — always use alongside other woody materials",
        "Bacdanol alone cannot replicate Mysore sandalwood creaminess — use with Javanol",
        "Synthetic sandalwood accord without natural EO reference may lack depth",
    ),
    performance_tips=(
        "Javanol has exceptional persistence due to low VP (0.03 Pa) + good logP",
        "Combine Ambroxan + Javanol + Iso E Super for the modern 'transparent woody skin' accord",
        "For Thai market: reduce Ambroxan, supplement with Habanolide + Ethylene Brassylate",
        "Javanol contains BHT antioxidant 0.05-0.1%",
    ),
    market_notes={
        "thai_market": "Reduce Ambroxan reliance (20% East Asian anosmia), supplement with Habanolide",
    },
)

MUSK_PROFILE = FamilyHedonicProfile(
    family=FragranceFamily.MUSK,
    description="Minimum 3 structural musk classes for anosmia coverage: polycyclic + macrocyclic + alicyclic/terpenic.",
    recommended_methods=(MethodologyType.MINIMAL_MATERIAL,),
    primary_materials=(
        FamilyMaterialTarget("Galaxolide 50%", 20, 60, "Polycyclic musk — OR4D6 receptor, unrestricted Cat4", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Habanolide", 10, 30, "Macrocyclic — transparent clean musk, anosmia ~5-10%", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Ambrettolide", 5, 15, "Macrocyclic — milky-musky softness, anosmia ~5%", +3.5, NoteTier.BASE),
        FamilyMaterialTarget("Ethylene Brassylate", 5, 15, "Alicyclic — cruelty-free muscone substitute", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Romandolide", 5, 15, "Macrocyclic — modern soft musk", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Ambroxan", 10, 30, "Terpenic amber-musk — OR7A17 receptor", +3.0, NoteTier.BASE),
    ),
    secret_materials=(
        FamilyMaterialTarget("Nirvanolide", 5, 15, "Soft musk — niche ingredient", +3.0, NoteTier.BASE, is_secret=True),
        FamilyMaterialTarget("Cashmeran", 10, 25, "Warm-woody musk texture", +3.0, NoteTier.BASE, is_secret=True),
    ),
    pitfalls=(
        "Single musk class = ~30% of population anosmic — minimum 3 classes required",
        "Galaxolide anosmia ~25-35% due to OR4D6 receptor variants (M263T, S151T)",
        "Ambroxan anosmia ~20% in East Asian populations (critical for Thai market)",
        "Musk accord without macrocyclic component feels 'synthetic' and 'monolithic'",
        "Androstenone: ~50% apparent anosmia; true non-detection ~2-6% (trainable)",
    ),
    performance_tips=(
        "For > 90% population coverage: polycyclic + macrocyclic + alicyclic minimum",
        "Thai market: reduce Ambroxan, supplement with Habanolide + Ethylene Brassylate",
        "Galaxolide at 10-30% of concentrate provides molecular cage fixative effect",
    ),
    market_notes={
        "anosmia_rule": "Never rely on a single musk class. 3 classes = > 90% coverage.",
        "thai_market": "Reduce Ambroxan to ≤ 5% of total musk OAV; use Habanolide + EB instead.",
    },
)

GOURMAND_PROFILE = FamilyHedonicProfile(
    family=FragranceFamily.GOURMAND,
    description="Edible-note fragrance family: vanilla, caramel, lactones, cocoa, honey.",
    recommended_methods=(MethodologyType.HEDONIC_OPTIMIZATION,),
    primary_materials=(
        FamilyMaterialTarget("Vanillin", 30, 100, "Sweet-creamy vanilla backbone", +3.5, NoteTier.BASE, cliff_oav=200, cliff_description=">200 OAV → plasticky-artificial"),
        FamilyMaterialTarget("Ethyl Maltol", 20, 80, "Caramel-cotton candy — ODT ~10 ppb", +3.0, NoteTier.BASE, cliff_oav=150, cliff_description=">150 OAV → burnt sugar-artificial"),
        FamilyMaterialTarget("Gamma-Decalactone", 10, 40, "Peachy-creamy lactone", +3.5, NoteTier.HEART),
        FamilyMaterialTarget("Gamma-Octalactone", 10, 30, "Coconut-creamy lactone", +3.0, NoteTier.HEART),
        FamilyMaterialTarget("Coumarin", 15, 40, "Hay-tonka, dried fruit sweetness (IFRA max 1.5% finished)", +3.5, NoteTier.BASE),
        FamilyMaterialTarget("Phenylacetic Acid", 2, 8, "Honey note — critical: OAV > 15 → rancid-sour", +2.5, NoteTier.HEART, cliff_oav=15, cliff_description="OAV > 15: rancid-sour off-note"),
        FamilyMaterialTarget("Ethyl Phenylacetate", 5, 15, "Cocoa-honey bridge", +3.0, NoteTier.HEART),
        FamilyMaterialTarget("Furaneol", 5, 15, "Strawberry-caramel depth", +3.0, NoteTier.HEART),
        FamilyMaterialTarget("Benzoin Resinoid", 10, 25, "Smoky-sweet balsamic vanilla", +3.5, NoteTier.BASE),
    ),
    secret_materials=(
        FamilyMaterialTarget("Methyl Laitone", 5, 15, "Milky-creamy lactonic — niche gourmand white-space", +3.5, NoteTier.BASE, is_secret=True),
        FamilyMaterialTarget("Delta-Decalactone", 5, 15, "Sweet-fruity delta-lactone", +3.0, NoteTier.HEART, is_secret=True),
    ),
    pitfalls=(
        "Vanillin + Ethyl Maltol both above sweet spots → artificial candy (not gourmand)",
        "Phenylacetic Acid: honey at OAV 2-8; rancid-sour at OAV > 15 — dosing is critical",
        "Gourmand without lactones feels flat — creamy texture requires gamma/delta lactones",
        "Coumarin above IFRA limit (1.5% finished) is common in amateur gourmands",
    ),
    performance_tips=(
        "2025 niche trends: dark gourmands (pistachio, sesame, smoked vanilla), matcha/tea accords",
        "Lactone cream accord: gamma-Octalactone 20 + gamma-Decalactone 25 + delta-Decalactone 15 + Coumarin 10 + Vanillin 8 + Ambrettolide 12 + Methyl Laitone 10 parts",
        "Rice milk and cereal notes emerging as 2025-2026 trend",
    ),
)

MARINE_AQUATIC_PROFILE = FamilyHedonicProfile(
    family=FragranceFamily.MARINE_AQUATIC,
    description="Marine/aquatic/ozonic: built around Calone and transparent materials.",
    recommended_methods=(MethodologyType.TEXTURE_FIRST,),
    primary_materials=(
        FamilyMaterialTarget("Calone", 5, 20, "Marine-watermelon character — ODT ~1 ppm ethanol", +3.0, NoteTier.HEART, cliff_oav=50, cliff_description="OAV > 50: metallic-ozonic, then pool cleaner at > 500"),
        FamilyMaterialTarget("Dihydromyrcenol", 30, 80, "Transparent fresh diffusion", +2.5, NoteTier.HEART),
        FamilyMaterialTarget("Hedione", 15, 40, "Transparent radiance — not identifiable as floral in marine context", +2.5, NoteTier.HEART),
        FamilyMaterialTarget("Aldehyde C12 MNA", 10, 25, "Sparkling-ozonic marine top with clean aldehydic character", +2.5, NoteTier.TOP),
        FamilyMaterialTarget("Ambroxan", 10, 30, "Skin-amber grounding for the marine accord", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Floralozone", 5, 15, "Transparent veil texture", +2.5, NoteTier.HEART),
        FamilyMaterialTarget("Iso E Super", 10, 30, "Woody transparency beneath marine freshness", +2.0, NoteTier.BASE),
        FamilyMaterialTarget("Habanolide", 5, 15, "Transparent clean musk", +3.0, NoteTier.BASE),
    ),
    secret_materials=(
        FamilyMaterialTarget("Seaweed Absolute", 2, 8, "Authentic marine if available — hard to source", +3.0, NoteTier.HEART, is_secret=True),
        FamilyMaterialTarget("Ultralia", 3, 10, "Veil texture — makes marine feel 'atmospheric' rather than 'synthetic'", +2.5, NoteTier.HEART, is_secret=True),
    ),
    pitfalls=(
        "Calone above 0.02% in concentrate → metallic-ozonic begins; above 0.5% → synthetic pool cleaner",
        "Marine + gourmand: fundamentally incompatible — aquatic sharpness destroys gourmand warmth",
        "Marine + amber/oriental: low compatibility — max 5% marine in oriental for coastal nuance",
        "Calone alone is not a marine accord — it needs DHMN, aldehydes, and transparent materials for depth",
        "Over-ozonic marine (excess Calone + Floralozone) reads as functional fragrance (air freshener)",
    ),
    performance_tips=(
        "Calone recommended working range: 0.005-0.015% in concentrate for subtle marine freshness",
        "Seawater accord: Calone 0.01 + DHMN 15 + Hedione 10 + Aldehyde C12 MNA 0.1 + Ambroxan 3 + Floralozone 2 parts",
        "Calone + DHMN synergy: ~3x — DHMN extends marine into fresh-clean without metallic flip",
        "10% Calone stock solution recommended for precise handling",
    ),
)

LEATHER_PROFILE = FamilyHedonicProfile(
    family=FragranceFamily.LEATHER,
    description="Leather: built around isobutyl quinoline, birch tar, and resinous-animalic materials.",
    recommended_methods=(MethodologyType.ACCORD_BASED,),
    primary_materials=(
        FamilyMaterialTarget("Isobutyl Quinoline (IBQ)", 0.5, 3, "Harsh tarry leather core — the leather 'flaw'", -3.0, NoteTier.BASE, cliff_oav=10, cliff_description="OAV > 10: medicinal-tar off-note; OAV > 5 in florals: destroys context"),
        FamilyMaterialTarget("Birch Tar", 0.5, 2, "Smoky-medicinal leather — similar to chypre flaw but leather-context", +2.0, NoteTier.BASE),
        FamilyMaterialTarget("Labdanum Absolute", 10, 25, "Balsamic-resinous leather body", +3.5, NoteTier.BASE),
        FamilyMaterialTarget("Benzoin Resinoid", 8, 20, "Smoky-sweet leather softener", +3.5, NoteTier.BASE),
        FamilyMaterialTarget("Castoreum Absolute", 3, 8, "Animalic-leather authenticity", +2.5, NoteTier.BASE),
        FamilyMaterialTarget("Patchouli EO", 8, 20, "Earthy depth beneath leather", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Coumarin", 10, 25, "Hay-tobacco leather companion", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Iso E Super", 15, 40, "Woody amplifier", +2.5, NoteTier.BASE),
    ),
    secret_materials=(
        FamilyMaterialTarget("Guaiacol (10% DPG)", 2, 8, "Smoky-phenolic depth; pure guaiacol at 0.5% effective", +2.0, NoteTier.BASE, is_secret=True),
        FamilyMaterialTarget("Skatole", 0.01, 0.1, "Fecal-floral tension at extreme dilution", +1.0, NoteTier.BASE, is_secret=True, cliff_oav=2, cliff_description="OAV > 2: fecal reading in any context"),
        FamilyMaterialTarget("Cade Oil", 0.5, 2, "Smoky-tarry leather edge (restricted in EU)", +2.0, NoteTier.BASE, is_secret=True),
    ),
    pitfalls=(
        "IBQ at > OAV 5 destroys floral context — never use IBQ in floral formulas",
        "IBQ + florals: max 0.01% IBQ in floral-dominant formulas before medicinal-tar note",
        "Birch Tar + IBQ combined above OAV 8 each = overwhelmingly smoky-chemist's bench",
        "Leather accord without Labdanum/Benzoin softness = harsh industrial",
        "Leather + citrus: generally incompatible; use only as top note contrast",
    ),
    performance_tips=(
        "Leather + Chypre: high compatibility; IBQ/birch tar enhances chypre depth",
        "Max 30% leather character in chypre before chypre identity dissolves",
        "IBQ at 1% stock solution in EtOH for precise handling",
        "Animalic leather: Castoreum + Indole trace + Labdanum core",
    ),
)


# ---------------------------------------------------------------------------
# Ecological niche categories
# ---------------------------------------------------------------------------

PETRICHOR_PROFILE = FamilyHedonicProfile(
    family=FragranceFamily.WOODY_AMBER,  # closest archetype
    description="Petrichor/geosmin accord: rain-on-earth, geological freshness. Geosmin ODT = 5 parts per trillion.",
    recommended_methods=(MethodologyType.SINGLE_MATERIAL,),
    primary_materials=(
        FamilyMaterialTarget("Geosmin (0.1% DPG)", 0.001, 0.01, "Rain-on-earth petrichor core — 5 ppt ODT", +2.0, NoteTier.BASE),
        FamilyMaterialTarget("Iso E Super", 20, 50, "Woody-earthy backbone beneath petrichor", +2.5, NoteTier.BASE),
        FamilyMaterialTarget("Ambroxan", 10, 30, "Skin-mineral grounding", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Ultralia", 3, 10, "Transparent atmospheric veil", +2.5, NoteTier.HEART),
        FamilyMaterialTarget("Vetiver EO (Haitian)", 5, 15, "Earthy-smoky complexity", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Cashmeran", 5, 15, "Warm mineral texture", +3.0, NoteTier.BASE),
    ),
    secret_materials=(),
    pitfalls=(
        "Geosmin above 0.001% in concentrate → beetroot-dirt off-note — extreme potency means extreme danger",
        "Geosmin at DPG 0.001% stock for handling; 0.1% stock for dosing into formula",
    ),
    performance_tips=(
        "Geosmin in water ODT: 0.006-0.01 µg/L = 5-10 ppt",
        "At 0.0001-0.001% in concentrate (0.1-1 ppm), OAV ~10-100",
        "Works in concert with Iso E Super + Ambroxan for mineral-earthy texture",
    ),
)

TRANSPARENT_SKIN_PROFILE = FamilyHedonicProfile(
    family=FragranceFamily.WOODY_AMBER,  # closest archetype
    description="Transparent skin scent (Ellena-style): no single material above OAV 80 — deliberately sub-threshold individual notes.",
    recommended_methods=(MethodologyType.TEXTURE_FIRST, MethodologyType.MINIMAL_MATERIAL),
    primary_materials=(
        FamilyMaterialTarget("Hedione HC", 15, 40, "VN1R1 radiance at sub-floral concentration", +4.0, NoteTier.HEART),
        FamilyMaterialTarget("Habanolide", 8, 20, "Transparent macrolide musk", +3.0, NoteTier.BASE),
        FamilyMaterialTarget("Ambroxan", 5, 15, "Skin-amber halo", +3.5, NoteTier.BASE),
        FamilyMaterialTarget("Ultralia", 3, 8, "Veil texture — spatial rather than character-based", +2.5, NoteTier.HEART),
        FamilyMaterialTarget("Linalool", 5, 15, "Transparent floral bridge", +2.5, NoteTier.TOP),
        FamilyMaterialTarget("Iso E Super", 10, 25, "Woody skin-halo", +2.5, NoteTier.BASE),
    ),
    secret_materials=(),
    pitfalls=(
        "Design principle: no single material above OAV 80 — the whole should feel textured, not identifiable",
        "If any single material becomes identifiable by a trained nose, the transparent skin effect is compromised",
    ),
    performance_tips=(
        "Deliberately sub-threshold individual notes — ensemble effect from receptor priming + cross-adaptation",
        "Works through ghost-note phenomenon (Part XII.5): sub-conscious texture, not conscious identification",
    ),
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

FAMILY_PROFILES: tuple[FamilyHedonicProfile, ...] = (
    CITRUS_HESPERIDIC,
    AROMATIC_FOUGERE_PROFILE,
    FLORAL_JASMINE_PROFILE,
    FLORAL_ROSE_PROFILE,
    CHYPRE_PROFILE,
    AMBER_ORIENTAL_PROFILE,
    WOODY_SANDALWOOD_PROFILE,
    MUSK_PROFILE,
    GOURMAND_PROFILE,
    MARINE_AQUATIC_PROFILE,
    LEATHER_PROFILE,
)


def get_family_profile(family: FragranceFamily) -> FamilyHedonicProfile | None:
    """Return the complete hedonic optimization profile for a fragrance family."""
    for profile in FAMILY_PROFILES:
        if profile.family == family:
            return profile
    return None


def get_oav_targets(
    family: FragranceFamily,
    material_name: str,
) -> tuple[float, float] | None:
    """Get the OAV target range for a material in a specific family context.

    Returns (min_oav, max_oav) or None if the material has no defined target.
    """
    profile = get_family_profile(family)
    if profile is None:
        return None

    for mt in profile.primary_materials:
        if mt.material.lower() == material_name.lower():
            return (mt.target_oav_min, mt.target_oav_max)
    for mt in profile.secret_materials:
        if mt.material.lower() == material_name.lower():
            return (mt.target_oav_min, mt.target_oav_max)
    return None


def get_cliff_oav(
    family: FragranceFamily,
    material_name: str,
) -> tuple[float, str] | None:
    """Get the hedonic cliff OAV and description for a material in a family.

    Returns (cliff_oav, description) or None if no cliff defined.
    """
    profile = get_family_profile(family)
    if profile is None:
        return None

    for mt in profile.primary_materials:
        if mt.material.lower() == material_name.lower() and mt.cliff_oav is not None:
            return (mt.cliff_oav, mt.cliff_description or "")
    for mt in profile.secret_materials:
        if mt.material.lower() == material_name.lower() and mt.cliff_oav is not None:
            return (mt.cliff_oav, mt.cliff_description or "")
    return None


def list_family_pitfalls(family: FragranceFamily) -> tuple[str, ...]:
    """Return known pitfalls for a fragrance family."""
    profile = get_family_profile(family)
    return profile.pitfalls if profile else ()


def list_family_performance_tips(family: FragranceFamily) -> tuple[str, ...]:
    """Return performance optimization tips for a fragrance family."""
    profile = get_family_profile(family)
    return profile.performance_tips if profile else ()


def get_ifra_changes(family: FragranceFamily) -> tuple[str, ...]:
    """Return post-IFRA changes affecting a fragrance family."""
    profile = get_family_profile(family)
    return profile.ifra_changes if profile else ()


def check_family_cliffs(
    family: FragranceFamily,
    material_oavs: Mapping[str, float],  # material_name → OAV
) -> dict[str, str]:
    """Check all materials in a formula for crossing hedonic cliffs in family context.

    Returns:
        dict mapping material_name → warning message for any exceeded cliffs
    """
    warnings: dict[str, str] = {}
    profile = get_family_profile(family)
    if profile is None:
        return warnings

    for mt in profile.primary_materials + profile.secret_materials:
        if mt.cliff_oav is not None:
            oav = material_oavs.get(mt.material.lower(), 0)
            if oav > mt.cliff_oav:
                warnings[mt.material] = (
                    f"OAV {oav:.1f} exceeds {mt.material} cliff at OAV {mt.cliff_oav}: "
                    f"{mt.cliff_description or 'hedonic flip risk'}"
                )

    return warnings
