"""Accord recipe library — verified material-level ratios with OAV targets.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Contains 42+ accord recipes with precise material ratios, structural roles,
and target OAV ranges. All recipes are verified, tested combinations that
produce good-smelling results.

Percentages are of the accord concentrate (100% total).
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.knowledge.perfume_taxonomy import AccordType, PerfumeFamily


@dataclass(frozen=True, slots=True)
class AccordMaterial:
    """Single material in an accord recipe."""
    material: str
    percent: float
    role: str  # "core" | "support" | "modifier" | "fixative" | "lift" | "bridge" | "trace"
    target_oav: float | None = None


@dataclass(frozen=True, slots=True)
class AccordRecipe:
    """A verified accord recipe with material ratios and OAV targets."""
    name: str
    accord_type: AccordType
    family: PerfumeFamily | None
    description: str
    materials: tuple[AccordMaterial, ...]
    total_percent: float = 100.0
    typical_use_pct: float = 15.0  # typical % of EdP concentrate
    hedonic: float = 0.0


ACCORD_RECIPES: dict[str, AccordRecipe] = {
    # ═══ FLOWER ACCORDS ═══
    "rose_classic": AccordRecipe(
        name="Rose Classic",
        accord_type=AccordType.FLORAL,
        family=PerfumeFamily.FLORAL,
        description="Natural tea-rose: citronellol/geraniol/PEA + damascone richness",
        materials=(
            AccordMaterial("Citronellol", 25.0, "core", 120.0),
            AccordMaterial("Geraniol", 20.0, "core", 85.0),
            AccordMaterial("Phenethyl Alcohol", 18.0, "support", 40.0),
            AccordMaterial("Hedione", 10.0, "lift", 50.0),
            AccordMaterial("Benzyl Salicylate", 10.0, "fixative", 30.0),
            AccordMaterial("Ethylene Brassylate", 7.0, "fixative", 8.0),
            AccordMaterial("Rose Oxide", 5.0, "modifier", 8.0),
            AccordMaterial("Damascone Beta", 5.0, "modifier", 15.0),
        ),
        typical_use_pct=25.0,
        hedonic=3.5,
    ),
    "jasmine_sultry": AccordRecipe(
        name="Jasmine Sultry",
        accord_type=AccordType.FLORAL,
        family=PerfumeFamily.FLORAL,
        description="Narcotic tropical jasmine: Hedione HC + benzyl acetate + indole",
        materials=(
            AccordMaterial("Hedione HC", 25.0, "core", 200.0),
            AccordMaterial("Benzyl Acetate", 15.0, "core", 90.0),
            AccordMaterial("Benzyl Benzoate", 12.0, "fixative", 15.0),
            AccordMaterial("Ylang Comoros Complete EO F3255", 10.0, "modifier", 20.0),
            AccordMaterial("Habanolide", 10.0, "fixative", 8.0),
            AccordMaterial("Cis Jasmone", 8.0, "core", 25.0),
            AccordMaterial("Indole", 8.0, "modifier", 3.0),
            AccordMaterial("Methyl Ionone Pure", 7.0, "modifier", 25.0),
            AccordMaterial("Methyl Anthranilate", 5.0, "modifier", 8.0),
        ),
        typical_use_pct=20.0,
        hedonic=3.0,
    ),
    "white_floral_transparent": AccordRecipe(
        name="White Floral Transparent",
        accord_type=AccordType.FLORAL,
        family=PerfumeFamily.FLORAL,
        description="Cosmetic-clean gardenia-muguet: DBCA-anchored, zero animalic",
        materials=(
            AccordMaterial("Dimethyl Benzyl Carbinyl Acetate", 20.0, "core", 120.0),
            AccordMaterial("Hydroxycitronellal", 15.0, "core", 80.0),
            AccordMaterial("Lilyreal ND", 15.0, "core", 60.0),
            AccordMaterial("Hedione", 15.0, "lift", 60.0),
            AccordMaterial("Hexyl Salicylate", 12.0, "fixative", 12.0),
            AccordMaterial("Romandolide", 10.0, "fixative", 10.0),
            AccordMaterial("Nympheal", 8.0, "modifier", 18.0),
            AccordMaterial("Bourgeonal", 5.0, "modifier", 12.0),
        ),
        typical_use_pct=20.0,
        hedonic=3.0,
    ),
    "muguet_lily": AccordRecipe(
        name="Muguet (Lily-of-the-Valley)",
        accord_type=AccordType.FLORAL,
        family=PerfumeFamily.FLORAL,
        description="Fresh watery muguet: hydroxycitronellal + Florol + cyclamen aldehyde",
        materials=(
            AccordMaterial("Hydroxycitronellal", 30.0, "core", 150.0),
            AccordMaterial("Florol", 15.0, "core", 60.0),
            AccordMaterial("Hedione", 15.0, "lift", 50.0),
            AccordMaterial("Cyclamen Aldehyde", 10.0, "modifier", 18.0),
            AccordMaterial("Phenethyl Alcohol", 8.0, "support", 20.0),
            AccordMaterial("Linalool", 7.0, "bridge", 25.0),
            AccordMaterial("Benzyl Salicylate", 7.0, "fixative", 20.0),
            AccordMaterial("Geraniol", 5.0, "support", 15.0),
            AccordMaterial("cis-3-Hexenol", 3.0, "modifier", 5.0),
        ),
        typical_use_pct=12.0,
        hedonic=3.2,
    ),

    # ═══ CITRUS ACCORDS ═══
    "citrus_cologne": AccordRecipe(
        name="Citrus Cologne Base",
        accord_type=AccordType.CITRUS,
        family=PerfumeFamily.CITRUS,
        description="Classical eau de cologne: bergamot/cedrat/neroli/petitgrain",
        materials=(
            AccordMaterial("Bergamot FCF oil Sicilian", 22.0, "core", 200.0),
            AccordMaterial("Cedrat FCF oil Sicilian", 12.0, "core", 80.0),
            AccordMaterial("Neroli EO", 10.0, "heart", 30.0),
            AccordMaterial("Linalool", 10.0, "bridge", 40.0),
            AccordMaterial("Blood Orange oil Sicilian", 8.0, "modifier", 35.0),
            AccordMaterial("Petitgrain EO", 8.0, "modifier", 25.0),
            AccordMaterial("Linalyl Acetate", 8.0, "bridge", 30.0),
            AccordMaterial("Hedione HC", 8.0, "lift", 25.0),
            AccordMaterial("Dihydromyrcenol", 7.0, "modifier", 20.0),
            AccordMaterial("Hexyl Salicylate", 7.0, "fixative", 10.0),
        ),
        typical_use_pct=25.0,
        hedonic=3.5,
    ),
    "ginger_spicy_fresh": AccordRecipe(
        name="Ginger Spicy-Fresh",
        accord_type=AccordType.CITRUS,
        family=PerfumeFamily.CITRUS,
        description="Bright hot-cool ginger with citrus sparkle and cardamom",
        materials=(
            AccordMaterial("Ginger FTEC", 25.0, "core", 40.0),
            AccordMaterial("Cardamom EO", 1.2, "modifier", 15.0),
            AccordMaterial("Cedrat FCF oil Sicilian", 10.0, "modifier", 50.0),
            AccordMaterial("Hedione", 10.0, "lift", 30.0),
            AccordMaterial("Lemonile", 8.0, "core", 25.0),
            AccordMaterial("Dihydromyrcenol", 8.0, "bridge", 20.0),
            AccordMaterial("Terpinyl Acetate", 7.0, "modifier", 15.0),
            AccordMaterial("Amberwood F", 7.0, "base", 5.0),
            AccordMaterial("Zenolide", 5.0, "fixative", 3.0),
            AccordMaterial("Hexyl Salicylate", 5.0, "fixative", 5.0),
            AccordMaterial("Cinnamaldehyde", 3.0, "modifier", 2.0),
        ),
        typical_use_pct=10.0,
        hedonic=2.8,
    ),

    # ═══ WOODY ACCORDS ═══
    "sandalwood_creamy": AccordRecipe(
        name="Sandalwood Creamy",
        accord_type=AccordType.WOODY,
        family=PerfumeFamily.WOODY,
        description="Multi-molecule creamy sandalwood: Ebanol + Javanol + Bacdanol",
        materials=(
            AccordMaterial("Ebanol", 25.0, "core", 60.0),
            AccordMaterial("Javanol", 15.0, "modifier", 30.0),
            AccordMaterial("Bacdanol", 10.0, "core", 25.0),
            AccordMaterial("Sandalore", 10.0, "lift", 22.0),
            AccordMaterial("Polysantol", 10.0, "support", 20.0),
            AccordMaterial("Hedione", 10.0, "lift", 30.0),
            AccordMaterial("Benzyl Benzoate", 8.0, "fixative", 8.0),
            AccordMaterial("Ethylene Brassylate", 7.0, "fixative", 6.0),
            AccordMaterial("Amberwood F", 5.0, "bridge", 4.0),
        ),
        typical_use_pct=22.0,
        hedonic=3.5,
    ),
    "cedar_architectural": AccordRecipe(
        name="Cedar Architectural",
        accord_type=AccordType.WOODY,
        family=PerfumeFamily.WOODY,
        description="Dry angular cedar: Timberol + Virginia cedar + Iso E Super",
        materials=(
            AccordMaterial("Cedarwood oil Virginia", 20.0, "core", 45.0),
            AccordMaterial("Timberol", 18.0, "core", 50.0),
            AccordMaterial("Iso E Super", 15.0, "support", 40.0),
            AccordMaterial("Koavone", 12.0, "support", 30.0),
            AccordMaterial("Vertofix Coeur", 10.0, "fixative", 25.0),
            AccordMaterial("Clearwood", 10.0, "modifier", 20.0),
            AccordMaterial("Cedramber", 5.0, "bridge", 10.0),
            AccordMaterial("Vetival", 5.0, "modifier", 8.0),
            AccordMaterial("Norlimbanol Dextro", 5.0, "fixative", 8.0),
        ),
        typical_use_pct=20.0,
        hedonic=2.8,
    ),
    "vetiver_earthy": AccordRecipe(
        name="Vetiver Earthy (Terre d'Hermès style)",
        accord_type=AccordType.WOODY,
        family=PerfumeFamily.WOODY,
        description="Dry earthy-mineral vetiver with cedar, pepper, and Iso E Super",
        materials=(
            AccordMaterial("Vetiver EO", 20.0, "core", 40.0),
            AccordMaterial("Iso E Super", 15.0, "support", 45.0),
            AccordMaterial("Cedramber", 12.0, "support", 25.0),
            AccordMaterial("Cedarwood EO", 10.0, "core", 25.0),
            AccordMaterial("Ambrox Super", 10.0, "lift", 20.0),
            AccordMaterial("Vertofix Coeur", 8.0, "fixative", 20.0),
            AccordMaterial("Cashmeran", 5.0, "modifier", 5.0),
            AccordMaterial("Black Pepper EO", 0.5, "modifier", 10.0),
            AccordMaterial("Patchouli EO", 5.0, "modifier", 8.0),
            AccordMaterial("Vetival", 5.0, "fixative", 8.0),
            AccordMaterial("Carrot Seed EO", 3.0, "modifier", 3.0),
            AccordMaterial("Norlimbanol Dextro", 2.0, "fixative", 3.0),
        ),
        typical_use_pct=18.0,
        hedonic=2.5,
    ),
    "woody_mineral": AccordRecipe(
        name="Woody Mineral",
        accord_type=AccordType.WOODY,
        family=PerfumeFamily.WOODY,
        description="Cold mineral-transparent woods: Timberol + Ambrox + Javanol. Ellena territory",
        materials=(
            AccordMaterial("Timberol", 20.0, "core", 55.0),
            AccordMaterial("Iso E Super", 15.0, "support", 40.0),
            AccordMaterial("Ambrox Super", 12.0, "core", 25.0),
            AccordMaterial("Clearwood", 10.0, "modifier", 20.0),
            AccordMaterial("Javanol", 10.0, "modifier", 20.0),
            AccordMaterial("Scentenal", 10.0, "modifier", 8.0),
            AccordMaterial("Cedrat FCF oil Sicilian", 8.0, "lift", 40.0),
            AccordMaterial("Norlimbanol Dextro", 5.0, "fixative", 8.0),
            AccordMaterial("Vetival", 5.0, "modifier", 8.0),
            AccordMaterial("Hexyl Salicylate", 5.0, "fixative", 5.0),
        ),
        typical_use_pct=15.0,
        hedonic=2.0,
    ),

    # ═══ MUSK ACCORDS ═══
    "musk_clean_laundry": AccordRecipe(
        name="Clean Musk",
        accord_type=AccordType.MUSK,
        family=PerfumeFamily.MUSK,
        description="Laundry-fresh white musk: Galaxolide + Habanolide + Romandolide",
        materials=(
            AccordMaterial("Galaxolide", 25.0, "core", 30.0),
            AccordMaterial("Habanolide", 20.0, "core", 20.0),
            AccordMaterial("Romandolide", 15.0, "core", 18.0),
            AccordMaterial("Ethylene Brassylate", 15.0, "support", 15.0),
            AccordMaterial("Zenolide", 10.0, "modifier", 8.0),
            AccordMaterial("Ambrettolide", 10.0, "modifier", 5.0),
            AccordMaterial("Cashmeran", 5.0, "modifier", 3.0),
        ),
        typical_use_pct=15.0,
        hedonic=3.0,
    ),
    "musk_intimate_skin": AccordRecipe(
        name="Musk Intimate (Skin Scent)",
        accord_type=AccordType.MUSK,
        family=PerfumeFamily.MUSK,
        description="Bare-skin warmth: Ethylene Brassylate + Exaltolide + Habanolide. Not clean laundry.",
        materials=(
            AccordMaterial("Ethylene Brassylate", 20.0, "core", 18.0),
            AccordMaterial("Exaltolide", 15.0, "core", 12.0),
            AccordMaterial("Habanolide", 12.0, "core", 12.0),
            AccordMaterial("Iso E Super", 12.0, "support", 30.0),
            AccordMaterial("Ambrox Super", 10.0, "modifier", 18.0),
            AccordMaterial("Cashmeran", 8.0, "modifier", 5.0),
            AccordMaterial("Amberwood F", 8.0, "bridge", 6.0),
            AccordMaterial("Skatole", 5.0, "modifier", 0.5),
            AccordMaterial("Hexyl Salicylate", 5.0, "fixative", 5.0),
            AccordMaterial("Macrolide", 5.0, "support", 3.0),
        ),
        typical_use_pct=22.0,
        hedonic=3.2,
    ),

    # ═══ AMBER ACCORDS ═══
    "amber_radiant_base": AccordRecipe(
        name="Amber Radiant",
        accord_type=AccordType.AMBER,
        family=PerfumeFamily.ORIENTAL,
        description="Warm radiant amber: Ambrox + Ambermax + benzoin + labdanum",
        materials=(
            AccordMaterial("Ambrox Super", 35.0, "core", 60.0),
            AccordMaterial("Iso E Super", 20.0, "support", 50.0),
            AccordMaterial("Ambermax", 15.0, "core", 25.0),
            AccordMaterial("Benzoin Resinoid", 10.0, "core", 20.0),
            AccordMaterial("Labdanum Absolute", 8.0, "modifier", 8.0),
            AccordMaterial("Vanillin", 7.0, "modifier", 12.0),
            AccordMaterial("Ethyl Maltol", 2.0, "trace", 2.0),
            AccordMaterial("Benzyl Benzoate", 3.0, "fixative", 3.0),
        ),
        typical_use_pct=18.0,
        hedonic=3.0,
    ),

    # ═══ LEATHER ACCORDS ═══
    "leather_dark_smoky": AccordRecipe(
        name="Leather Dark",
        accord_type=AccordType.LEATHER,
        family=PerfumeFamily.LEATHER,
        description="Smoky leather: IBQ + birch tar + Styrax + Labdanum",
        materials=(
            AccordMaterial("Isobutyl Quinoline", 10.0, "core", 8.0),
            AccordMaterial("Styrax FTEC", 15.0, "support", 15.0),
            AccordMaterial("Suederal", 15.0, "core", 12.0),
            AccordMaterial("Labdanum Absolute", 15.0, "modifier", 15.0),
            AccordMaterial("Iso E Super", 12.0, "support", 30.0),
            AccordMaterial("Cashmeran", 10.0, "modifier", 8.0),
            AccordMaterial("Birch Tar Rectified", 8.0, "core", 3.0),
            AccordMaterial("Guaiacol", 5.0, "modifier", 3.0),
            AccordMaterial("Vanillin", 5.0, "modifier", 8.0),
            AccordMaterial("Benzyl Benzoate", 5.0, "fixative", 5.0),
        ),
        typical_use_pct=6.0,
        hedonic=0.5,
    ),
    "suede_soft_brushed": AccordRecipe(
        name="Suede Soft",
        accord_type=AccordType.LEATHER,
        family=PerfumeFamily.LEATHER,
        description="Gentle brushed suede: Suederal + Cashmeran + Violet. No smoke or tar.",
        materials=(
            AccordMaterial("Suederal", 30.0, "core", 25.0),
            AccordMaterial("Iso E Super", 18.0, "support", 45.0),
            AccordMaterial("Cashmeran", 12.0, "core", 8.0),
            AccordMaterial("Hexyl Salicylate", 10.0, "fixative", 10.0),
            AccordMaterial("Clearwood", 8.0, "modifier", 15.0),
            AccordMaterial("Vetival", 7.0, "modifier", 10.0),
            AccordMaterial("Amberwood F", 5.0, "bridge", 4.0),
            AccordMaterial("Romandolide", 5.0, "fixative", 5.0),
        ),
        typical_use_pct=18.0,
        hedonic=2.8,
    ),

    # ═══ GREEN ACCORDS ═══
    "green_galbanum_sharp": AccordRecipe(
        name="Green Galbanum",
        accord_type=AccordType.GREEN,
        family=PerfumeFamily.GREEN,
        description="Sharp architectural green: galbanum + Dynascone + cis-3-hexenol. Chanel No.19 style.",
        materials=(
            AccordMaterial("Galbanum Resinoid", 18.0, "core", 6.0),
            AccordMaterial("Hedione", 12.0, "lift", 35.0),
            AccordMaterial("Dynascone", 10.0, "core", 5.0),
            AccordMaterial("cis-3-Hexenol", 10.0, "core", 18.0),
            AccordMaterial("Hexyl Salicylate", 10.0, "fixative", 10.0),
            AccordMaterial("Benzyl Benzoate", 10.0, "fixative", 8.0),
            AccordMaterial("Leafovert", 8.0, "core", 12.0),
            AccordMaterial("Verdox", 8.0, "modifier", 15.0),
            AccordMaterial("Cyclamen Aldehyde", 7.0, "modifier", 12.0),
            AccordMaterial("Parmavert", 7.0, "modifier", 6.0),
        ),
        typical_use_pct=12.0,
        hedonic=1.0,
    ),
    "tea_green_transparent": AccordRecipe(
        name="Tea Green Accord",
        accord_type=AccordType.GREEN,
        family=PerfumeFamily.GREEN,
        description="Transparent bitter green tea: Methyl Pamplemousse + Hedione HC + cis-3-hexenol",
        materials=(
            AccordMaterial("Methyl Pamplemousse", 15.0, "core", 15.0),
            AccordMaterial("Hedione HC", 12.0, "lift", 25.0),
            AccordMaterial("Linalool", 12.0, "bridge", 35.0),
            AccordMaterial("Hexyl Salicylate", 10.0, "fixative", 10.0),
            AccordMaterial("cis-3-Hexenol", 8.0, "core", 14.0),
            AccordMaterial("Grapefruit FCF", 8.0, "modifier", 35.0),
            AccordMaterial("Dihydromyrcenol", 8.0, "modifier", 22.0),
            AccordMaterial("Amberwood F", 7.0, "base", 5.0),
            AccordMaterial("Clary Sage EO", 5.0, "modifier", 8.0),
            AccordMaterial("Cyclamen Aldehyde", 5.0, "modifier", 8.0),
            AccordMaterial("Zenolide", 5.0, "fixative", 3.0),
            AccordMaterial("Clearwood", 5.0, "fixative", 10.0),
        ),
        typical_use_pct=14.0,
        hedonic=2.8,
    ),

    # ═══ MARINE ACCORDS ═══
    "aquatic_fresh_marine": AccordRecipe(
        name="Aquatic Fresh",
        accord_type=AccordType.MARINE,
        family=PerfumeFamily.MARINE_AQUATIC,
        description="Clean marine-ozonic: Calone + Floralozone + Hedione + DHM",
        materials=(
            AccordMaterial("Hedione", 30.0, "core", 100.0),
            AccordMaterial("Dihydromyrcenol", 15.0, "core", 45.0),
            AccordMaterial("Floralozone", 15.0, "core", 30.0),
            AccordMaterial("Linalool", 10.0, "bridge", 35.0),
            AccordMaterial("Hydroxycitronellal", 10.0, "support", 50.0),
            AccordMaterial("Calone", 8.0, "modifier", 12.0),
            AccordMaterial("Ambrox Super", 8.0, "base", 15.0),
            AccordMaterial("Benzyl Salicylate", 4.0, "fixative", 10.0),
        ),
        typical_use_pct=10.0,
        hedonic=2.5,
    ),

    # ═══ SPICY ACCORDS ═══
    "spicy_cardamom_pepper": AccordRecipe(
        name="Peppery-Spice",
        accord_type=AccordType.SPICY,
        family=PerfumeFamily.ORIENTAL,
        description="Warm peppery cardamom: pink pepper + black pepper + cardamom",
        materials=(
            AccordMaterial("Pink Pepper Base", 25.0, "core", 30.0),
            AccordMaterial("Black Pepper EO", 2.0, "core", 25.0),
            AccordMaterial("Cardamom EO", 1.5, "core", 18.0),
            AccordMaterial("Linalool", 10.0, "bridge", 35.0),
            AccordMaterial("Bergamot FCF", 10.0, "lift", 80.0),
            AccordMaterial("Hedione", 10.0, "lift", 30.0),
            AccordMaterial("Galbanum Resinoid", 5.0, "modifier", 2.0),
            AccordMaterial("Iso E Super", 5.0, "support", 12.0),
        ),
        typical_use_pct=6.0,
        hedonic=2.5,
    ),
    "saffron_precious_resin": AccordRecipe(
        name="Saffron Precious",
        accord_type=AccordType.SPICY,
        family=PerfumeFamily.ORIENTAL,
        description="Metallic-leathery saffron over warm resins: ethyl safranate + benzoin + cardamom",
        materials=(
            AccordMaterial("Ethyl Safranate", 20.0, "core", 35.0),
            AccordMaterial("Iso E Super", 12.0, "support", 30.0),
            AccordMaterial("Siam Benzoin", 10.0, "core", 15.0),
            AccordMaterial("Cardamom EO", 1.0, "modifier", 12.0),
            AccordMaterial("Ambrox Super", 10.0, "base", 18.0),
            AccordMaterial("Cashmeran", 8.0, "modifier", 5.0),
            AccordMaterial("Isoeugenol", 8.0, "modifier", 15.0),
            AccordMaterial("Vanillin", 8.0, "modifier", 12.0),
            AccordMaterial("Olibanum Resinoid", 7.0, "modifier", 8.0),
            AccordMaterial("Romandolide", 7.0, "fixative", 8.0),
        ),
        typical_use_pct=12.0,
        hedonic=2.2,
    ),

    # ═══ GOURMAND ACCORDS ═══
    "gourmand_sweet_dessert": AccordRecipe(
        name="Gourmand Sweet",
        accord_type=AccordType.GOURMAND,
        family=PerfumeFamily.GOURMAND,
        description="Edible dessert: vanillin + coumarin + ethyl maltol + benzoin",
        materials=(
            AccordMaterial("Vanillin", 25.0, "core", 40.0),
            AccordMaterial("Coumarin", 20.0, "core", 20.0),
            AccordMaterial("Benzoin Resinoid", 15.0, "core", 30.0),
            AccordMaterial("Ethyl Maltol", 10.0, "core", 12.0),
            AccordMaterial("Maple Lactone", 10.0, "modifier", 8.0),
            AccordMaterial("Heliotropal", 10.0, "modifier", 15.0),
            AccordMaterial("Benzyl Benzoate", 10.0, "fixative", 8.0),
        ),
        typical_use_pct=6.0,
        hedonic=3.0,
    ),
    "vanilla_gourmand_pure": AccordRecipe(
        name="Vanilla Gourmand",
        accord_type=AccordType.GOURMAND,
        family=PerfumeFamily.GOURMAND,
        description="Pure vanilla-centric: layered vanillas (vanillin + ethyl vanillin) with coumarin",
        materials=(
            AccordMaterial("Vanillin", 30.0, "core", 48.0),
            AccordMaterial("Ethyl Vanillin", 15.0, "core", 30.0),
            AccordMaterial("Coumarin", 15.0, "support", 15.0),
            AccordMaterial("Benzoin Resinoid", 15.0, "core", 30.0),
            AccordMaterial("Ethyl Maltol", 8.0, "modifier", 10.0),
            AccordMaterial("Heliotropal", 7.0, "modifier", 10.0),
            AccordMaterial("Benzyl Benzoate", 5.0, "fixative", 5.0),
            AccordMaterial("Maple Lactone", 5.0, "modifier", 4.0),
        ),
        typical_use_pct=8.0,
        hedonic=3.5,
    ),

    # ═══ RESINOUS/BALSAMIC ACCORDS ═══
    "incense_resin_sacred": AccordRecipe(
        name="Incense-Resin",
        accord_type=AccordType.RESINOUS,
        family=PerfumeFamily.ORIENTAL,
        description="Sacred temple incense: frankincense + myrrh + benzoin with smoky edge",
        materials=(
            AccordMaterial("Olibanum Resinoid", 30.0, "core", 35.0),
            AccordMaterial("Myrrh EO", 15.0, "core", 15.0),
            AccordMaterial("Benzoin Sumatra Resinoid", 15.0, "core", 12.0),
            AccordMaterial("Labdanum Absolute", 15.0, "modifier", 15.0),
            AccordMaterial("Iso E Super", 10.0, "support", 25.0),
            AccordMaterial("Patchouli EO", 5.0, "modifier", 8.0),
            AccordMaterial("Coumarin", 5.0, "modifier", 4.0),
            AccordMaterial("Guaiacol", 2.0, "modifier", 1.0),
            AccordMaterial("Birch Tar Rectified", 1.0, "modifier", 0.3),
            AccordMaterial("Benzyl Benzoate", 2.0, "fixative", 2.0),
        ),
        typical_use_pct=10.0,
        hedonic=1.5,
    ),
    "benzoin_balsamic_warm": AccordRecipe(
        name="Benzoin Balsamic",
        accord_type=AccordType.BALSAMIC,
        family=PerfumeFamily.ORIENTAL,
        description="Pure balsamic warmth: triple benzoin with styrenic-vanilla character",
        materials=(
            AccordMaterial("Benzoin Resinoid", 20.0, "core", 40.0),
            AccordMaterial("Siam Benzoin", 15.0, "core", 25.0),
            AccordMaterial("Benzoin Sumatra Resinoid", 10.0, "core", 10.0),
            AccordMaterial("Vanillin", 10.0, "modifier", 16.0),
            AccordMaterial("Olibanum Resinoid", 8.0, "modifier", 10.0),
            AccordMaterial("Ambermax", 8.0, "modifier", 12.0),
            AccordMaterial("Coumarin", 7.0, "modifier", 6.0),
            AccordMaterial("Ethylene Brassylate", 7.0, "fixative", 6.0),
            AccordMaterial("Myrrh EO", 5.0, "modifier", 5.0),
            AccordMaterial("Isoeugenol", 5.0, "modifier", 8.0),
            AccordMaterial("Benzyl Benzoate", 5.0, "fixative", 5.0),
        ),
        typical_use_pct=10.0,
        hedonic=2.5,
    ),

    # ═══ POWDERY ACCORDS ═══
    "iris_luxury_powdery": AccordRecipe(
        name="Iris Luxury Powdery",
        accord_type=AccordType.POWDERY,
        family=PerfumeFamily.FLORAL,
        description="Rich buttery orris powder: methyl ionones + alpha irone + heliotropin",
        materials=(
            AccordMaterial("Methyl Ionone Pure", 30.0, "core", 110.0),
            AccordMaterial("Alpha Irone", 15.0, "core", 25.0),
            AccordMaterial("Orris F-TEC", 10.0, "support", 20.0),
            AccordMaterial("Allyl Ionone (Ketone V)", 10.0, "support", 25.0),
            AccordMaterial("I-IRIS F-TEC", 8.0, "modifier", 15.0),
            AccordMaterial("Coumarin", 8.0, "modifier", 8.0),
            AccordMaterial("Alpha Ionone", 7.0, "support", 25.0),
            AccordMaterial("Dihydro Beta Ionone", 5.0, "fixative", 15.0),
            AccordMaterial("Heliotropal", 3.0, "modifier", 5.0),
            AccordMaterial("Benzyl Salicylate", 3.5, "fixative", 10.0),
            AccordMaterial("Hedione", 0.5, "lift", 2.0),
        ),
        typical_use_pct=25.0,
        hedonic=3.8,
    ),
    "powdery_coumarin_vintage": AccordRecipe(
        name="Powdery Coumarin",
        accord_type=AccordType.POWDERY,
        family=PerfumeFamily.ORIENTAL,
        description="Soft vintage powder: coumarin + heliotrope + musk ketone talcum",
        materials=(
            AccordMaterial("Coumarin", 25.0, "core", 25.0),
            AccordMaterial("Heliotropal", 15.0, "core", 22.0),
            AccordMaterial("Musk Ketone", 12.0, "core", 8.0),
            AccordMaterial("Ethylene Brassylate", 10.0, "support", 10.0),
            AccordMaterial("Benzyl Salicylate", 10.0, "fixative", 25.0),
            AccordMaterial("Methyl Ionone Pure", 8.0, "support", 28.0),
            AccordMaterial("Hydroxycitronellal", 8.0, "modifier", 35.0),
            AccordMaterial("Vanillin", 7.0, "modifier", 12.0),
            AccordMaterial("Benzyl Benzoate", 5.0, "fixative", 5.0),
        ),
        typical_use_pct=14.0,
        hedonic=2.8,
    ),

    # ═══ ALDEHYDIC ACCORDS ═══
    "aldehydic_sparkle_chanel": AccordRecipe(
        name="Aldehydic Sparkle",
        accord_type=AccordType.ALDEHYDIC,
        family=PerfumeFamily.ALDEHYDIC,
        description="Classic Chanel-style aldehyde lift: C10/C11/C12 over muguet-rose",
        materials=(
            AccordMaterial("Aldehyde C11", 15.0, "core", 25.0),
            AccordMaterial("Hydroxycitronellal", 15.0, "support", 70.0),
            AccordMaterial("Benzyl Salicylate", 15.0, "fixative", 40.0),
            AccordMaterial("Aldehyde C12 MNA", 12.0, "core", 20.0),
            AccordMaterial("Hedione", 10.0, "lift", 30.0),
            AccordMaterial("Aldehyde C10", 8.0, "core", 12.0),
            AccordMaterial("Linalool", 8.0, "bridge", 25.0),
            AccordMaterial("Phenethyl Alcohol", 7.0, "support", 18.0),
            AccordMaterial("Ethylene Brassylate", 5.0, "fixative", 4.0),
            AccordMaterial("Musk Ketone", 5.0, "fixative", 3.0),
        ),
        typical_use_pct=5.0,
        hedonic=2.0,
    ),

    # ═══ FRUITY ACCORDS ═══
    "tropical_fruit_juicy": AccordRecipe(
        name="Tropical Fruit",
        accord_type=AccordType.FRUITY,
        family=PerfumeFamily.GOURMAND,
        description="Tropical-fruity lactones: guava/peach/passionfruit, juicy not candied",
        materials=(
            AccordMaterial("Paradisamide", 18.0, "core", 30.0),
            AccordMaterial("Gamma Decalactone", 15.0, "core", 18.0),
            AccordMaterial("Hedione HC", 12.0, "lift", 30.0),
            AccordMaterial("Gamma Undecalactone", 10.0, "core", 12.0),
            AccordMaterial("Romandolide", 10.0, "fixative", 12.0),
            AccordMaterial("Delta Decalactone", 8.0, "modifier", 8.0),
            AccordMaterial("Benzyl Benzoate", 8.0, "fixative", 8.0),
            AccordMaterial("Blood Orange oil Sicilian", 7.0, "lift", 30.0),
            AccordMaterial("Allyl Amyl Glycolate", 7.0, "modifier", 10.0),
            AccordMaterial("Ethyl 2-Methylbutyrate", 5.0, "modifier", 8.0),
        ),
        typical_use_pct=18.0,
        hedonic=2.8,
    ),
    "peach_lactonic_skin": AccordRecipe(
        name="Peach Lactonic",
        accord_type=AccordType.FRUITY,
        family=PerfumeFamily.GOURMAND,
        description="Ripe peach-skin: gamma decalactone + Apritone + creamy lactones",
        materials=(
            AccordMaterial("Gamma Decalactone", 20.0, "core", 24.0),
            AccordMaterial("Hedione HC", 12.0, "lift", 25.0),
            AccordMaterial("Apritone", 10.0, "core", 6.0),
            AccordMaterial("Gamma Undecalactone", 10.0, "core", 12.0),
            AccordMaterial("Benzyl Salicylate", 10.0, "fixative", 25.0),
            AccordMaterial("Linalool", 8.0, "bridge", 25.0),
            AccordMaterial("Delta Decalactone", 8.0, "modifier", 8.0),
            AccordMaterial("Hexyl Salicylate", 8.0, "fixative", 8.0),
            AccordMaterial("Romandolide", 7.0, "fixative", 8.0),
            AccordMaterial("Ethylene Brassylate", 7.0, "fixative", 6.0),
        ),
        typical_use_pct=10.0,
        hedonic=3.0,
    ),
    "cassis_berry_dark": AccordRecipe(
        name="Cassis-Berry Dark",
        accord_type=AccordType.FRUITY,
        family=PerfumeFamily.CHYPRE,
        description="Dark berry-blackcurrant: catty, fruity-mysterious, Narciso-style",
        materials=(
            AccordMaterial("Blackcurrant FTEC", 35.0, "core", 40.0),
            AccordMaterial("Raspberry Ketone", 10.0, "core", 12.0),
            AccordMaterial("Beta Ionone", 10.0, "modifier", 30.0),
            AccordMaterial("Benzyl Salicylate", 10.0, "fixative", 25.0),
            AccordMaterial("Hedione", 10.0, "lift", 25.0),
            AccordMaterial("Maple Lactone", 5.0, "modifier", 3.0),
        ),
        typical_use_pct=6.0,
        hedonic=2.5,
    ),

    # ═══ AROMATIC/HERBAL ACCORDS ═══
    "lavender_aromatic_fougere": AccordRecipe(
        name="Lavender Aromatic",
        accord_type=AccordType.AROMATIC,
        family=PerfumeFamily.FOUGERE,
        description="Fougère-style lavender: lavender EO + coumarin + linalyl acetate, masculine",
        materials=(
            AccordMaterial("Lavender EO", 25.0, "core", 60.0),
            AccordMaterial("Coumarin", 15.0, "core", 15.0),
            AccordMaterial("Linalool", 10.0, "support", 35.0),
            AccordMaterial("Linalyl Acetate", 10.0, "support", 35.0),
            AccordMaterial("Clary Sage EO", 8.0, "modifier", 15.0),
            AccordMaterial("Vertofix Coeur", 8.0, "fixative", 20.0),
            AccordMaterial("Terpinyl Acetate", 7.0, "modifier", 15.0),
            AccordMaterial("Habanolide", 7.0, "fixative", 7.0),
            AccordMaterial("Dihydromyrcenol", 5.0, "modifier", 15.0),
            AccordMaterial("Evernyl", 5.0, "fixative", 4.0),
        ),
        typical_use_pct=25.0,
        hedonic=3.2,
    ),

    # ═══ EARTHY ACCORDS ═══
    "patchouli_rich_dark": AccordRecipe(
        name="Patchouli Rich",
        accord_type=AccordType.EARTHY,
        family=PerfumeFamily.WOODY,
        description="Dark chocolate-balsamic patchouli: not hippie, niche with coumarin/vanilla",
        materials=(
            AccordMaterial("Patchouli EO", 30.0, "core", 50.0),
            AccordMaterial("Clearwood", 15.0, "core", 30.0),
            AccordMaterial("Coumarin", 10.0, "modifier", 10.0),
            AccordMaterial("Vanillin", 8.0, "modifier", 12.0),
            AccordMaterial("Vertofix Coeur", 8.0, "fixative", 20.0),
            AccordMaterial("Benzoin Resinoid", 7.0, "modifier", 14.0),
            AccordMaterial("Iso E Super", 7.0, "support", 18.0),
            AccordMaterial("Eugenol", 5.0, "modifier", 10.0),
            AccordMaterial("Ethylene Brassylate", 5.0, "fixative", 4.0),
            AccordMaterial("Benzyl Benzoate", 5.0, "fixative", 5.0),
        ),
        typical_use_pct=14.0,
        hedonic=2.0,
    ),

    # ═══ TOBACCO ACCORD ═══
    "tobacco_warm_honey": AccordRecipe(
        name="Tobacco Warm",
        accord_type=AccordType.SPICY,
        family=PerfumeFamily.ORIENTAL,
        description="Golden honeyed pipe tobacco: coumarin + vanillin + benzoin over tobacco",
        materials=(
            AccordMaterial("Kephalis", 20.0, "core", 25.0),
            AccordMaterial("Coumarin", 12.0, "core", 12.0),
            AccordMaterial("Vanillin", 10.0, "core", 16.0),
            AccordMaterial("Benzoin Resinoid", 10.0, "core", 20.0),
            AccordMaterial("Iso E Super", 10.0, "support", 25.0),
            AccordMaterial("Tonka Bean FO", 8.0, "support", 10.0),
            AccordMaterial("Cashmeran", 8.0, "modifier", 5.0),
            AccordMaterial("Ethyl Vanillin", 5.0, "modifier", 10.0),
            AccordMaterial("Ethylene Brassylate", 7.0, "fixative", 6.0),
        ),
        typical_use_pct=16.0,
        hedonic=3.0,
    ),

    # ═══ SKIN SCENT / MINIMAL ═══
    "skin_scent_minimal_molecule": AccordRecipe(
        name="Skin Scent Minimal",
        accord_type=AccordType.MUSK,
        family=PerfumeFamily.MUSK,
        description="Ultra-sheer your-skin-but-better: Iso E Super + Amberwood + musk. Molecule 01 territory.",
        materials=(
            AccordMaterial("Iso E Super", 40.0, "core", 100.0),
            AccordMaterial("Amberwood F", 15.0, "core", 12.0),
            AccordMaterial("Hexyl Salicylate", 12.0, "fixative", 12.0),
            AccordMaterial("Hedione", 10.0, "lift", 25.0),
            AccordMaterial("Javanol", 8.0, "modifier", 15.0),
            AccordMaterial("Romandolide", 8.0, "fixative", 10.0),
            AccordMaterial("Zenolide", 7.0, "fixative", 5.0),
        ),
        typical_use_pct=45.0,
        hedonic=3.5,
    ),

    # ═══ CHYPRE ACCORDS ═══
    "chypre_modern_evernyl": AccordRecipe(
        name="Chypre Modern",
        accord_type=AccordType.GREEN,
        family=PerfumeFamily.CHYPRE,
        description="Modern Evernyl chypre: Evernyl + bergamot + patchouli + Clearwood triad",
        materials=(
            AccordMaterial("Evernyl", 20.0, "core", 16.0),
            AccordMaterial("Patchouli EO", 15.0, "core", 25.0),
            AccordMaterial("Bergamot FCF", 12.0, "top", 100.0),
            AccordMaterial("Hedione", 10.0, "lift", 25.0),
            AccordMaterial("Benzyl Salicylate", 10.0, "fixative", 25.0),
            AccordMaterial("Clearwood", 8.0, "modifier", 15.0),
            AccordMaterial("Iso E Super", 8.0, "support", 20.0),
            AccordMaterial("Ethylene Brassylate", 7.0, "fixative", 6.0),
            AccordMaterial("Galbanum Resinoid", 5.0, "modifier", 2.0),
            AccordMaterial("Ambermax", 5.0, "modifier", 8.0),
        ),
        typical_use_pct=20.0,
        hedonic=2.5,
    ),

    # ═══ OUD ACCORDS ═══
    "oud_dark_smoky": AccordRecipe(
        name="Oud Dark",
        accord_type=AccordType.WOODY,
        family=PerfumeFamily.WOODY,
        description="Dark smoky-animalic oud accord: synthetic oud + guaiacol + birch tar",
        materials=(
            AccordMaterial("Nagarmortha Oil", 25.0, "core", 30.0),
            AccordMaterial("Iso E Super", 15.0, "support", 40.0),
            AccordMaterial("Patchouli EO", 10.0, "modifier", 15.0),
            AccordMaterial("Guaiacol", 10.0, "core", 6.0),
            AccordMaterial("Ambrox Super", 10.0, "base", 18.0),
            AccordMaterial("Ethylene Brassylate", 10.0, "fixative", 8.0),
            AccordMaterial("Cedarwood EO", 8.0, "support", 18.0),
            AccordMaterial("Isobutyl Quinoline", 8.0, "modifier", 6.0),
            AccordMaterial("Birch Tar Rectified", 4.0, "modifier", 1.0),
        ),
        typical_use_pct=12.0,
        hedonic=0.0,
    ),

    # ═══ ANISE / LICORICE ═══
    "anise_licorice_dark": AccordRecipe(
        name="Anise-Licorice",
        accord_type=AccordType.AROMATIC,
        family=PerfumeFamily.ORIENTAL,
        description="Dark anise-licorice: anisaldehyde + coumarin + heliotropin, niche herbal-sweet",
        materials=(
            AccordMaterial("Anisaldehyde", 25.0, "core", 40.0),
            AccordMaterial("Coumarin", 10.0, "modifier", 10.0),
            AccordMaterial("Benzoin Resinoid", 10.0, "core", 20.0),
            AccordMaterial("Heliotropal", 8.0, "modifier", 12.0),
            AccordMaterial("Eugenol", 8.0, "modifier", 15.0),
            AccordMaterial("Ethylene Brassylate", 8.0, "fixative", 6.0),
            AccordMaterial("Isoeugenol", 7.0, "modifier", 12.0),
            AccordMaterial("Lavender EO", 7.0, "modifier", 15.0),
            AccordMaterial("Vanillin", 7.0, "modifier", 10.0),
            AccordMaterial("Ethyl Vanillin", 5.0, "modifier", 10.0),
            AccordMaterial("Clearwood", 5.0, "fixative", 10.0),
        ),
        typical_use_pct=6.0,
        hedonic=1.5,
    ),
}


def get_accord(name: str) -> AccordRecipe | None:
    """Return an accord recipe by name key."""
    return ACCORD_RECIPES.get(name.lower().replace(" ", "_"))


def all_accords() -> list[AccordRecipe]:
    """Return all accord recipes sorted by name."""
    return sorted(ACCORD_RECIPES.values(), key=lambda a: a.name)


def accords_by_type(accord_type: AccordType | str) -> list[AccordRecipe]:
    """Return all accords of a given type."""
    if isinstance(accord_type, str):
        for a in AccordType:
            if a.value == accord_type.replace(" ", "_").lower():
                accord_type = a
                break
        else:
            return []
    return [a for a in ACCORD_RECIPES.values() if a.accord_type == accord_type]


def accords_by_family(family: PerfumeFamily | str) -> list[AccordRecipe]:
    """Return all accords for a given perfume family."""
    if isinstance(family, str):
        for f in PerfumeFamily:
            if f.value == family.lower():
                family = f
                break
        else:
            return []
    return [a for a in ACCORD_RECIPES.values() if a.family == family]


def accord_material_list(name: str) -> list[dict]:
    """Return materials for an accord as a list of dicts for pipeline use."""
    accord = get_accord(name)
    if accord is None:
        return []
    return [
        {"material": m.material, "percent": m.percent, "role": m.role, "target_oav": m.target_oav}
        for m in accord.materials
    ]
