"""Complete perfume taxonomy — families, subfamilies, hierarchy mappings.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (ppm w/w in concentrate).
- ODT in ppm (ethanol) or ppb (air).
- OAV = concentration_ppm / ODT_ppm.
- Every perceptibility claim must be backed by OAV.

Codifies the complete fragrance classification from soliflores through
classical families to modern hybrid subcategories. All ratios based on
verified perfumery practice and OAV analysis.

Coverage:
  - 13 root families → 77 subfamilies
  - 19 soliflore types
  - 18 accord types
  - Full hierarchy mappings
"""

from __future__ import annotations

from enum import StrEnum

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS — Complete taxonomy
# ═══════════════════════════════════════════════════════════════════════════════


class PerfumeFamily(StrEnum):
    """Root fragrance families — 7 classical + 6 modern additions."""
    CITRUS = "citrus"
    FOUGERE = "fougere"
    FLORAL = "floral"
    CHYPRE = "chypre"
    ORIENTAL = "oriental"
    WOODY = "woody"
    LEATHER = "leather"
    AROMATIC = "aromatic"
    GREEN = "green"
    MARINE_AQUATIC = "marine_aquatic"
    GOURMAND = "gourmand"
    ALDEHYDIC = "aldehydic"
    MUSK = "musk"


class PerfumeSubfamily(StrEnum):
    """Refined subfamilies within each root family — 71 total."""

    # ── Citrus subfamilies (6) ──
    CITRUS_CLASSICAL = "citrus_classical"      # eau de cologne: neroli/petitgrain/bergamot
    CITRUS_AROMATIC = "citrus_aromatic"         # citrus + lavender/rosemary/thyme
    CITRUS_FLORAL = "citrus_floral"             # citrus + white flowers
    CITRUS_WOODY = "citrus_woody"               # citrus + vetiver/cedar/sandalwood
    CITRUS_GREEN = "citrus_green"               # citrus + galbanum/violet leaf/cis-3-hexenol
    CITRUS_SPICY = "citrus_spicy"               # citrus + ginger/cardamom/cinnamon

    # ── Fougère subfamilies (6) ──
    FOUGERE_CLASSICAL = "fougere_classical"     # lavender/coumarin/oakmoss trinity (Jicky)
    FOUGERE_AROMATIC = "fougere_aromatic"       # aromatic fougère: lavender+citrus over coumarin
    FOUGERE_MODERN_MINERAL = "fougere_modern_mineral"  # mineral/cold-stone fougère
    FOUGERE_MODERN_TONKA = "fougere_modern_tonka"      # tonka mass-appeal (fruit+vanilla hook)
    FOUGERE_GREEN = "fougere_green"             # galbanum-green fougère
    FOUGERE_LEATHERY = "fougere_leathery"       # leather-fougère hybrid (IBQ + coumarin)

    # ── Floral subfamilies (9) ──
    FLORAL_SOLIFLORE = "floral_soliflore"       # single-flower focus
    FLORAL_WHITE = "floral_white"               # jasmine/gardenia/tuberose white bouquet
    FLORAL_ROSE = "floral_rose"                 # rose-centric — citronellol/geraniol/PEA
    FLORAL_MUGUET = "floral_muguet"             # lily-of-the-valley — hydroxycitronellal
    FLORAL_ALDEHYDIC = "floral_aldehydic"       # aldehydes + rose/jasmine (Chanel No.5 style)
    FLORAL_GREEN = "floral_green"               # green-floral: galbanum + hyacinth/narcissus
    FLORAL_FRUITY = "floral_fruity"             # fruity-floral: peach/apricot + rose/jasmine
    FLORAL_POWDERY = "floral_powdery"           # orris/ionone powdery floral
    FLORAL_ORIENTAL = "floral_oriental"         # floral + amber/vanilla/resin

    # ── Chypre subfamilies (6) ──
    CHYPRE_CLASSICAL = "chypre_classical"       # bergamot/labdanum/oakmoss triad (Coty Chypre)
    CHYPRE_FLORAL = "chypre_floral"             # rose/jasmine over chypre base
    CHYPRE_FRUITY = "chypre_fruity"            # peach/mirabelle lactones (Mitsouko style)
    CHYPRE_GREEN = "chypre_green"              # galbanum-green chypre (Chanel No.19)
    CHYPRE_LEATHERY = "chypre_leathery"        # leather + chypre (Bandit style)
    CHYPRE_MODERN = "chypre_modern"            # Evernyl + Clearwood + bergamot triad

    # ── Oriental subfamilies (7) ──
    ORIENTAL_CLASSICAL = "oriental_classical"   # vanilla/resin/spice triad (Shalimar)
    ORIENTAL_AMBER = "oriental_amber"           # amber-forward: benzoin/labdanum/vanillin
    ORIENTAL_SPICY = "oriental_spicy"           # cinnamon/clove/carnation heavy (Opium style)
    ORIENTAL_WOODY = "oriental_woody"           # sandalwood/oud/cedar oriental
    ORIENTAL_GOURMAND = "oriental_gourmand"     # edible: ethyl maltol/vanilla/tonka
    ORIENTAL_FLORAL = "oriental_floral"         # floral + oriental base
    ORIENTAL_FRESH = "oriental_fresh"           # modern "fresh oriental": citrus/hedione + amber

    # ── Woody subfamilies (9) ──
    WOODY_CLASSICAL = "woody_classical"         # sandalwood/cedar/vetiver traditional
    WOODY_AMBER = "woody_amber"                 # Ambrox/Iso E Super based (MFK/Molecule style)
    WOODY_AROMATIC = "woody_aromatic"           # woody + herbs: lavender/clary sage + cedar
    WOODY_CITRUS = "woody_citrus"              # woody + citrus: vetiver/cedar + bergamot
    WOODY_FLORAL = "woody_floral"              # woody + floral: cedar + rose/jasmine
    WOODY_LEATHERY = "woody_leathery"          # woody + leather: cedar + IBQ/suederal
    WOODY_MINERAL = "woody_mineral"            # cold/mineral woods: Timberol + Ambrox (Ellena)
    WOODY_SMOKY = "woody_smoky"                # birch tar/guaiac/cypriol smoky woods
    WOODY_ORIENTAL = "woody_oriental"          # oud/woody + amber/resin

    # ── Leather subfamilies (5) ──
    LEATHER_CLASSICAL = "leather_classical"     # IBQ/birch tar traditional leather (Knize Ten)
    LEATHER_FLORAL = "leather_floral"           # leather + rose/jasmine (Cuir de Russie)
    LEATHER_SMOKY = "leather_smoky"             # birch tar/guaiacol heavy
    LEATHER_SUEDE = "leather_suede"             # soft suede: Suederal + Cashmeran + Violet
    LEATHER_ORIENTAL = "leather_oriental"       # leather + amber/vanilla/benzoin

    # ── Marine/Aquatic subfamilies (4) ──
    MARINE_OZONIC = "marine_ozonic"             # calone/floralozone heavy (New West)
    MARINE_FLORAL = "marine_floral"             # aquatic + rose/lily/muguet
    MARINE_WOODY = "marine_woody"               # aquatic + driftwood/cedar (Bulgari Aqva)
    MARINE_AROMATIC = "marine_aromatic"         # aquatic + lavender/rosemary (Cool Water)

    # ── Gourmand subfamilies (5) ──
    GOURMAND_VANILLA = "gourmand_vanilla"       # vanilla-centric — vanillin/ethyl vanillin
    GOURMAND_CHOCOLATE = "gourmand_chocolate"   # cocoa/patchouli/vanillin dark gourmand
    GOURMAND_FRUITY = "gourmand_fruity"         # fruit + caramel: peach lactone + ethyl maltol
    GOURMAND_COFFEE = "gourmand_coffee"         # coffee/tonka/vanilla
    GOURMAND_NUTTY = "gourmand_nutty"           # almond/heliotropin/coumarin

    # ── Musk subfamilies (5) ──
    MUSK_CLEAN = "musk_clean"                   # laundry/white musk: Galaxolide + Habanolide
    MUSK_SKIN = "musk_skin"                     # intimate skin: Exaltolide + Ethylene Brassylate
    MUSK_ANIMALIC = "musk_animalic"             # civet/castoreum/costus replacement
    MUSK_FLORAL = "musk_floral"                 # musk + rose/jasmine transparency
    MUSK_WOODY = "musk_woody"                   # musk + Iso E Super/Ambrox/Sandalore

    # ── Green subfamilies (3) ──
    GREEN_FRESH = "green_fresh"                 # sharp green: cis-3-hexenol/galbanum/leafovert
    GREEN_FLORAL = "green_floral"               # green-floral: Chanel No.19 style
    GREEN_AROMATIC = "green_aromatic"           # green + herbs: galbanum + clary sage

    # ── Aldehydic subfamilies (3) ──
    ALDEHYDIC_CLASSICAL = "aldehydic_classical" # C10/C11/C12 + rose/jasmine (Chanel No.5)
    ALDEHYDIC_FLORAL = "aldehydic_floral"       # aldehydes + white florals
    ALDEHYDIC_WOODY = "aldehydic_woody"         # aldehydes + woods/musk

    # ── Aromatic subfamilies (3) ──
    AROMATIC_HERBAL = "aromatic_herbal"         # lavender/clary sage/rosemary/thyme
    AROMATIC_SPICY = "aromatic_spicy"           # cardamom/ginger/black pepper/cinnamon
    AROMATIC_GREEN = "aromatic_green"           # galbanum + clary sage + petitgrain


class AccordType(StrEnum):
    """Accord types by structural function — 18 types."""
    FLORAL = "floral_accord"
    CITRUS = "citrus_accord"
    WOODY = "woody_accord"
    MUSK = "musk_accord"
    AMBER = "amber_accord"
    LEATHER = "leather_accord"
    GREEN = "green_accord"
    MARINE = "marine_accord"
    SPICY = "spicy_accord"
    GOURMAND = "gourmand_accord"
    FRUITY = "fruity_accord"
    RESINOUS = "resinous_accord"
    ALDEHYDIC = "aldehydic_accord"
    POWDERY = "powdery_accord"
    EARTHY = "earthy_accord"
    SMOKY = "smoky_accord"
    AROMATIC = "aromatic_accord"
    BALSAMIC = "balsamic_accord"


class SolifloreType(StrEnum):
    """Single-flower perfume types with verified structures — 19 types."""
    ROSE = "rose"
    JASMINE = "jasmine"
    MUGUET = "muguet"
    TUBEROSE = "tuberose"
    GARDENIA = "gardenia"
    NEROLI = "neroli"
    VIOLET = "violet"
    IRIS = "iris"
    LAVENDER = "lavender"
    YLANG = "ylang"
    CHAMPACA = "champaca"
    LILAC = "lilac"
    MIMOSA = "mimosa"
    NARCISSUS = "narcissus"
    HYACINTH = "hyacinth"
    OSMANTHUS = "osmanthus"
    ORANGE_BLOSSOM = "orange_blossom"
    LINDEN = "linden"
    PEONY = "peony"


class ConcentrationBracket(StrEnum):
    """Fine fragrance concentration brackets (% w/w in ethanol)."""
    EDC = "EdC"        # 3-5%
    EDT = "EdT"        # 8-12%
    EDP = "EdP"        # 15-20%
    EXTRAIT = "Extrait"  # 20%+
    BODY_SPRAY = "Body Spray"  # ~3%


# ═══════════════════════════════════════════════════════════════════════════════
# HIERARCHY MAPPINGS
# ═══════════════════════════════════════════════════════════════════════════════

FAMILY_SUBFAMILY_MAP: dict[PerfumeFamily, tuple[PerfumeSubfamily, ...]] = {
    PerfumeFamily.CITRUS: (
        PerfumeSubfamily.CITRUS_CLASSICAL,
        PerfumeSubfamily.CITRUS_AROMATIC,
        PerfumeSubfamily.CITRUS_FLORAL,
        PerfumeSubfamily.CITRUS_WOODY,
        PerfumeSubfamily.CITRUS_GREEN,
        PerfumeSubfamily.CITRUS_SPICY,
    ),
    PerfumeFamily.FOUGERE: (
        PerfumeSubfamily.FOUGERE_CLASSICAL,
        PerfumeSubfamily.FOUGERE_AROMATIC,
        PerfumeSubfamily.FOUGERE_MODERN_MINERAL,
        PerfumeSubfamily.FOUGERE_MODERN_TONKA,
        PerfumeSubfamily.FOUGERE_GREEN,
        PerfumeSubfamily.FOUGERE_LEATHERY,
    ),
    PerfumeFamily.FLORAL: (
        PerfumeSubfamily.FLORAL_SOLIFLORE,
        PerfumeSubfamily.FLORAL_WHITE,
        PerfumeSubfamily.FLORAL_ROSE,
        PerfumeSubfamily.FLORAL_MUGUET,
        PerfumeSubfamily.FLORAL_ALDEHYDIC,
        PerfumeSubfamily.FLORAL_GREEN,
        PerfumeSubfamily.FLORAL_FRUITY,
        PerfumeSubfamily.FLORAL_POWDERY,
        PerfumeSubfamily.FLORAL_ORIENTAL,
    ),
    PerfumeFamily.CHYPRE: (
        PerfumeSubfamily.CHYPRE_CLASSICAL,
        PerfumeSubfamily.CHYPRE_FLORAL,
        PerfumeSubfamily.CHYPRE_FRUITY,
        PerfumeSubfamily.CHYPRE_GREEN,
        PerfumeSubfamily.CHYPRE_LEATHERY,
        PerfumeSubfamily.CHYPRE_MODERN,
    ),
    PerfumeFamily.ORIENTAL: (
        PerfumeSubfamily.ORIENTAL_CLASSICAL,
        PerfumeSubfamily.ORIENTAL_AMBER,
        PerfumeSubfamily.ORIENTAL_SPICY,
        PerfumeSubfamily.ORIENTAL_WOODY,
        PerfumeSubfamily.ORIENTAL_GOURMAND,
        PerfumeSubfamily.ORIENTAL_FLORAL,
        PerfumeSubfamily.ORIENTAL_FRESH,
    ),
    PerfumeFamily.WOODY: (
        PerfumeSubfamily.WOODY_CLASSICAL,
        PerfumeSubfamily.WOODY_AMBER,
        PerfumeSubfamily.WOODY_AROMATIC,
        PerfumeSubfamily.WOODY_CITRUS,
        PerfumeSubfamily.WOODY_FLORAL,
        PerfumeSubfamily.WOODY_LEATHERY,
        PerfumeSubfamily.WOODY_MINERAL,
        PerfumeSubfamily.WOODY_SMOKY,
        PerfumeSubfamily.WOODY_ORIENTAL,
    ),
    PerfumeFamily.LEATHER: (
        PerfumeSubfamily.LEATHER_CLASSICAL,
        PerfumeSubfamily.LEATHER_FLORAL,
        PerfumeSubfamily.LEATHER_SMOKY,
        PerfumeSubfamily.LEATHER_SUEDE,
        PerfumeSubfamily.LEATHER_ORIENTAL,
    ),
    PerfumeFamily.MARINE_AQUATIC: (
        PerfumeSubfamily.MARINE_OZONIC,
        PerfumeSubfamily.MARINE_FLORAL,
        PerfumeSubfamily.MARINE_WOODY,
        PerfumeSubfamily.MARINE_AROMATIC,
    ),
    PerfumeFamily.GOURMAND: (
        PerfumeSubfamily.GOURMAND_VANILLA,
        PerfumeSubfamily.GOURMAND_CHOCOLATE,
        PerfumeSubfamily.GOURMAND_FRUITY,
        PerfumeSubfamily.GOURMAND_COFFEE,
        PerfumeSubfamily.GOURMAND_NUTTY,
    ),
    PerfumeFamily.MUSK: (
        PerfumeSubfamily.MUSK_CLEAN,
        PerfumeSubfamily.MUSK_SKIN,
        PerfumeSubfamily.MUSK_ANIMALIC,
        PerfumeSubfamily.MUSK_FLORAL,
        PerfumeSubfamily.MUSK_WOODY,
    ),
    PerfumeFamily.GREEN: (
        PerfumeSubfamily.GREEN_FRESH,
        PerfumeSubfamily.GREEN_FLORAL,
        PerfumeSubfamily.GREEN_AROMATIC,
    ),
    PerfumeFamily.ALDEHYDIC: (
        PerfumeSubfamily.ALDEHYDIC_CLASSICAL,
        PerfumeSubfamily.ALDEHYDIC_FLORAL,
        PerfumeSubfamily.ALDEHYDIC_WOODY,
    ),
    PerfumeFamily.AROMATIC: (
        PerfumeSubfamily.AROMATIC_HERBAL,
        PerfumeSubfamily.AROMATIC_SPICY,
        PerfumeSubfamily.AROMATIC_GREEN,
    ),
}

SUBFAMILY_FAMILY_MAP: dict[PerfumeSubfamily, PerfumeFamily] = {
    sub: family
    for family, subs in FAMILY_SUBFAMILY_MAP.items()
    for sub in subs
}

# ── Family descriptions ──

FAMILY_DESCRIPTIONS: dict[PerfumeFamily, str] = {
    PerfumeFamily.CITRUS: "Hesperidic — bergamot, lemon, orange, neroli. Fresh, bright, ephemeral. The original cologne family rooted in 14th-century Italy.",
    PerfumeFamily.FOUGERE: "Lavender + coumarin + oakmoss triad. Barbershop-aromatic, green-fresh. Created by Houbigant in 1882 (Fougère Royale).",
    PerfumeFamily.FLORAL: "Single or bouquet of flower notes — rose, jasmine, muguet, tuberose. The largest family, 60%+ of feminine market.",
    PerfumeFamily.CHYPRE: "Bergamot + labdanum + oakmoss triad. Mossy-woody with citrus sparkle. Created by Coty in 1917.",
    PerfumeFamily.ORIENTAL: "Resins, vanilla, spices, balsams. Warm, exotic, opulent. Rooted in Middle Eastern attar tradition. Shalimar (1925) is the archetype.",
    PerfumeFamily.WOODY: "Sandalwood, cedar, vetiver, patchouli. Dry, warm, sophisticated. Subdivided by wood species: sandalwood, cedar, oud.",
    PerfumeFamily.LEATHER: "Birch tar, isobutyl quinoline, styrax. Smoky, animalic dryness. The 1920s Russian leather tradition.",
    PerfumeFamily.AROMATIC: "Herbal-camphoraceous: lavender, sage, rosemary, thyme. Fresh-medicinal character crossing fougère and citrus.",
    PerfumeFamily.GREEN: "Crushed leaf, cut grass, galbanum, violet leaf. Sharp, bitter, chlorophyll-rich. Chanel No.19 (1970) is the archetype.",
    PerfumeFamily.MARINE_AQUATIC: "Ozone, sea spray, calone, watermelon ketone. Born 1990s with New West and Cool Water. Transparent, modern, clean.",
    PerfumeFamily.GOURMAND: "Edible: vanilla, caramel, chocolate, coffee. Food-adjacent comfort. Angel (1992) launched the category. BR540 modernized it.",
    PerfumeFamily.ALDEHYDIC: "Fatty aldehydes C8-C12. Waxy, soapy, sparkling. Chanel No.5 (1921) defined the category.",
    PerfumeFamily.MUSK: "Macrocyclic and polycyclic musks. Clean laundry, intimate skin, or animalic warmth. Usually low-volatility and highly substantive.",
}

SUBFAMILY_DESCRIPTIONS: dict[PerfumeSubfamily, str] = {
    # Citrus
    PerfumeSubfamily.CITRUS_CLASSICAL: "Traditional eau de cologne: neroli, petitgrain, bergamot, lemon. 4711, Acqua di Parma. 50/35/15 pyramid.",
    PerfumeSubfamily.CITRUS_AROMATIC: "Citrus + lavender/rosemary/thyme. Eau Sauvage territory. Herbs bridge citrus to wood base.",
    PerfumeSubfamily.CITRUS_FLORAL: "Citrus top over white floral heart: neroli/jasmine/orange blossom. Mediterranean feminines.",
    PerfumeSubfamily.CITRUS_WOODY: "Citrus + vetiver/cedar/sandalwood. Terre d'Hermès style. Mineral-earthy citrus.",
    PerfumeSubfamily.CITRUS_GREEN: "Citrus + galbanum/violet leaf. Bitter-green opening. Chanel No.19 meets bergamot.",
    PerfumeSubfamily.CITRUS_SPICY: "Citrus + ginger/cardamom. Hot-cool spice over hesperidic brightness. Energetic, modern.",
    # Fougère
    PerfumeSubfamily.FOUGERE_CLASSICAL: "Lavender + coumarin + oakmoss. Jicky, Fougère Royale. 25/40/35 pyramid. Barbershop-aromatic.",
    PerfumeSubfamily.FOUGERE_AROMATIC: "Aromatic fougère: lavender+citrus over coumarin/moss. Modernized classical with hedione radiance.",
    PerfumeSubfamily.FOUGERE_MODERN_MINERAL: "Mineral/cold-stone fougère. DHM + Calone + Floralozone + lavender. Metallic freshness.",
    PerfumeSubfamily.FOUGERE_MODERN_TONKA: "Tonka mass-appeal: coumarin + apple/fruit hook + vanilla warmth. Commercial masculine.",
    PerfumeSubfamily.FOUGERE_GREEN: "Galbanum-green fougère. Bitter herbal + coumarin. Niche, less sweet than classical.",
    PerfumeSubfamily.FOUGERE_LEATHERY: "IBQ/suederal + coumarin hybrid. Smoky leather meets barbershop. Dark, masculine.",
    # Floral
    PerfumeSubfamily.FLORAL_SOLIFLORE: "Single flower focus: 60% heart, minimal top/base. Purity of one floral note.",
    PerfumeSubfamily.FLORAL_WHITE: "Jasmine + gardenia + tuberose + orange blossom. Heavy, narcotic, night-blooming. Fracas style.",
    PerfumeSubfamily.FLORAL_ROSE: "Citronellol + geraniol + PEA trinity. Damascone richness. Tea-rose or dark crimson varieties.",
    PerfumeSubfamily.FLORAL_MUGUET: "Hydroxycitronellal + Florol + cyclamen aldehyde. Watery, transparent, Diorissimo style.",
    PerfumeSubfamily.FLORAL_ALDEHYDIC: "Aldehydes C10-C12 + rose/jasmine. Waxy, sparkling, Chanel No.5. Soapy-clean florals.",
    PerfumeSubfamily.FLORAL_GREEN: "Galbanum + hyacinth + narcissus. Sharp green florals. Bitter-stem character.",
    PerfumeSubfamily.FLORAL_FRUITY: "Peach lactone + apricot + rose/jasmine. Fruity-juicy florals. Modern feminines.",
    PerfumeSubfamily.FLORAL_POWDERY: "Ionones + heliotropin + coumarin. Vintage powder. Orris butter character.",
    PerfumeSubfamily.FLORAL_ORIENTAL: "Floral heart over amber/vanilla/resin base. Narciso Rodriguez style.",
    # Chypre
    PerfumeSubfamily.CHYPRE_CLASSICAL: "Bergamot + labdanum + oakmoss. Coty Chypre, Mitsouko. Mossy-woody drydown.",
    PerfumeSubfamily.CHYPRE_FLORAL: "Rose/jasmine over chypre base. Miss Dior. Floral brightness over moss.",
    PerfumeSubfamily.CHYPRE_FRUITY: "Peach/mirabelle + mossy base. Mitsouko, Femme Rochas. Lactone fruits.",
    PerfumeSubfamily.CHYPRE_GREEN: "Galbanum + bitter herbs over mossy base. Chanel No.19. Bitter-green chypre.",
    PerfumeSubfamily.CHYPRE_LEATHERY: "IBQ + styrax over mossy base. Bandit, Cabochard. Smoky leather chypre.",
    PerfumeSubfamily.CHYPRE_MODERN: "Evernyl + Clearwood + bergamot. IFRA-compliant modern chypre. No real oakmoss.",
    # Oriental
    PerfumeSubfamily.ORIENTAL_CLASSICAL: "Vanilla + resin + spice. Shalimar. Balsamic warmth, amber drydown.",
    PerfumeSubfamily.ORIENTAL_AMBER: "Benzoin + labdanum + vanillin trinity. Warm amber skin. MFK Grand Soir style.",
    PerfumeSubfamily.ORIENTAL_SPICY: "Cinnamon + clove + carnation. Opium, Coco. Hot spice over vanilla/resin.",
    PerfumeSubfamily.ORIENTAL_WOODY: "Sandalwood/oud + amber/vanilla. Santal Majuscule, Oud Satin Mood.",
    PerfumeSubfamily.ORIENTAL_GOURMAND: "Vanilla + caramel + tonka. Angel, BR540. Edible-sweet comfort.",
    PerfumeSubfamily.ORIENTAL_FLORAL: "Rose/jasmine over vanilla/resin base. L'Heure Bleue. Floral-oriental hybrid.",
    PerfumeSubfamily.ORIENTAL_FRESH: "Citrus + hedione opening over amber base. Light Blue, modern orientals.",
    # Woody
    PerfumeSubfamily.WOODY_CLASSICAL: "Sandalwood + cedar + vetiver. Santal 33, Tam Dao. Pure wood character.",
    PerfumeSubfamily.WOODY_AMBER: "Ambrox + Iso E Super + Sandalore. MFK/Molecule style. Transparent radiance.",
    PerfumeSubfamily.WOODY_AROMATIC: "Cedar + vetiver + clary sage/lavender. Aromatic woody masculines.",
    PerfumeSubfamily.WOODY_CITRUS: "Vetiver/cedar + bergamot/grapefruit. Terre d'Hermès. Mineral-earthy citrus-wood.",
    PerfumeSubfamily.WOODY_FLORAL: "Cedar/sandalwood + rose/jasmine. Woody-rose. Portrait of a Lady style.",
    PerfumeSubfamily.WOODY_LEATHERY: "Cedar + IBQ/suederal. Dry leather-wood. Tuscan Leather style.",
    PerfumeSubfamily.WOODY_MINERAL: "Timberol + Ambrox + Javanol. Cold mineral woods. Ellena transparency.",
    PerfumeSubfamily.WOODY_SMOKY: "Birch tar + guaiacol + cedar. Campfire woods. A City On Fire style.",
    PerfumeSubfamily.WOODY_ORIENTAL: "Oud + rose + amber/vanilla. Oud Satin Mood, Oud Wood.",
    # Leather
    PerfumeSubfamily.LEATHER_CLASSICAL: "IBQ + birch tar. Knize Ten, Bandit. Harsh smoky leather.",
    PerfumeSubfamily.LEATHER_FLORAL: "Leather + rose/jasmine. Cuir de Russie. Floral-softened leather.",
    PerfumeSubfamily.LEATHER_SMOKY: "Birch tar + guaiacol heavy. Campfire leather. Dark, bitter.",
    PerfumeSubfamily.LEATHER_SUEDE: "Suederal + Cashmeran + Violet. Soft brushed suede. No smoke, no tar.",
    PerfumeSubfamily.LEATHER_ORIENTAL: "Leather + amber/benzoin/vanilla. Daim Blond. Sweetened, warm leather.",
    # Marine
    PerfumeSubfamily.MARINE_OZONIC: "Calone + Floralozone + DHM. Ozonic-seaweed. New West, L'Eau d'Issey.",
    PerfumeSubfamily.MARINE_FLORAL: "Aquatic + rose/lily/muguet. Sailing Day. Ocean breeze through flowers.",
    PerfumeSubfamily.MARINE_WOODY: "Aquatic + driftwood/cedar. Bulgari Aqva, Sel Marin. Sea-soaked wood.",
    PerfumeSubfamily.MARINE_AROMATIC: "Aquatic + lavender/rosemary. Cool Water, GIT. Aromatic freshness.",
    # Gourmand
    PerfumeSubfamily.GOURMAND_VANILLA: "Vanillin + ethyl vanillin + coumarin. Pure vanilla comfort. Tihota style.",
    PerfumeSubfamily.GOURMAND_CHOCOLATE: "Cocoa absolute + patchouli + vanillin. Dark chocolate. Angel Muse style.",
    PerfumeSubfamily.GOURMAND_FRUITY: "Peach lactone + ethyl maltol + strawberry. Fruity-dessert. La Vie Est Belle.",
    PerfumeSubfamily.GOURMAND_COFFEE: "Coffee absolute + tonka + vanilla. Roasted gourmand. Intoxicated style.",
    PerfumeSubfamily.GOURMAND_NUTTY: "Heliotropin + coumarin + almond. Marzipan-almond. Lolita Lempicka style.",
    # Musk
    PerfumeSubfamily.MUSK_CLEAN: "Diffusive clean white-musk chord with a soft structural musk underneath. Laundry-clean, Byredo Blanche territory.",
    PerfumeSubfamily.MUSK_SKIN: "Macrocyclic skin musks over Ethylene Brassylate-style depth. Intimate warmth, Musc Ravageur drydown territory.",
    PerfumeSubfamily.MUSK_ANIMALIC: "Civet/castoreum replacers + costus. Dirty warmth. Kiehl's Musk style.",
    PerfumeSubfamily.MUSK_FLORAL: "Musk + rose/jasmine transparency. Musc Rose. Airy, clean floral.",
    PerfumeSubfamily.MUSK_WOODY: "Musk + Iso E Super/Ambrox/Sandalore. Molecule-style woody-musk.",
    # Green
    PerfumeSubfamily.GREEN_FRESH: "cis-3-Hexenol + Galbanum + Leafovert. Sharp crushed leaf. Cut-grass realism.",
    PerfumeSubfamily.GREEN_FLORAL: "Green + hyacinth/narcissus/lily. Chanel No.19, Cristalle. Green-floral elegance.",
    PerfumeSubfamily.GREEN_AROMATIC: "Green + clary sage/rosemary/basil. Aromatic-green. Herb garden freshness.",
    # Aldehydic
    PerfumeSubfamily.ALDEHYDIC_CLASSICAL: "C10/C11/C12 + rose/jasmine. Chanel No.5, Arpège. Waxy-sparkling florals.",
    PerfumeSubfamily.ALDEHYDIC_FLORAL: "Aldehydes + white florals. Madame Rochas. Aldehydic gardenia/tuberose.",
    PerfumeSubfamily.ALDEHYDIC_WOODY: "Aldehydes + sandalwood/cedar/musk. Clean aldehydic woods. Soapy-woody.",
    # Aromatic
    PerfumeSubfamily.AROMATIC_HERBAL: "Lavender + clary sage + rosemary + thyme. Herbal medley. Provençal garden.",
    PerfumeSubfamily.AROMATIC_SPICY: "Cardamom + ginger + black pepper + cinnamon. Hot spice blend. Spice market.",
    PerfumeSubfamily.AROMATIC_GREEN: "Galbanum + clary sage + petitgrain. Bitter-aromatic green. Complex herbs.",
}


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def get_subfamilies(family: PerfumeFamily | str) -> tuple[PerfumeSubfamily, ...]:
    """Return all subfamilies for a given root family."""
    if isinstance(family, str):
        for f in PerfumeFamily:
            if f.value.replace("_", "").replace("-", "") == family.lower().replace("_", "").replace("-", ""):
                family = f
                break
        else:
            return ()
    return FAMILY_SUBFAMILY_MAP.get(family, ())


def get_parent_family(subfamily: PerfumeSubfamily | str) -> PerfumeFamily | None:
    """Return the root family for a given subfamily."""
    if isinstance(subfamily, str):
        for s in PerfumeSubfamily:
            if s.value == subfamily:
                subfamily = s
                break
        else:
            return None
    return SUBFAMILY_FAMILY_MAP.get(subfamily)


def get_family_description(family: PerfumeFamily | str) -> str:
    """Return the description for a family."""
    if isinstance(family, str):
        for f in PerfumeFamily:
            if f.value == family:
                family = f
                break
        else:
            return ""
    return FAMILY_DESCRIPTIONS.get(family, "")


def get_subfamily_description(subfamily: PerfumeSubfamily | str) -> str:
    """Return the description for a subfamily."""
    if isinstance(subfamily, str):
        for s in PerfumeSubfamily:
            if s.value == subfamily:
                subfamily = s
                break
        else:
            return ""
    return SUBFAMILY_DESCRIPTIONS.get(subfamily, "")


def all_families() -> list[PerfumeFamily]:
    """Return all root families sorted alphabetically."""
    return sorted(PerfumeFamily.__members__.values(), key=lambda f: f.value)


def all_subfamilies() -> list[PerfumeSubfamily]:
    """Return all subfamilies sorted alphabetically."""
    return sorted(PerfumeSubfamily.__members__.values(), key=lambda s: s.value)


def taxonomy_tree() -> dict[str, list[str]]:
    """Return the full family→subfamily tree as a dict."""
    return {
        family.value: [sub.value for sub in subs]
        for family, subs in FAMILY_SUBFAMILY_MAP.items()
    }
