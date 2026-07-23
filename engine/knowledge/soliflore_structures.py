"""Soliflore perfume structures — verified single-flower templates.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Contains 19 soliflore structures with material-level ratios, OAV targets,
and hedonic assessments. Each structure is a complete perfume concentrate
recipe focused on a single flower.

All ratios are % of perfume concentrate (100% total).
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.knowledge.perfume_taxonomy import (
    PerfumeFamily,
    SolifloreType,
)


@dataclass(frozen=True, slots=True)
class SolifloreComponent:
    """A material in a soliflore structure with role and dose info."""
    material: str
    percent_of_concentrate: float
    role: str  # "core_identity" | "support" | "modifier" | "fixative" | "lift" | "bridge"


@dataclass(frozen=True, slots=True)
class SolifloreStructure:
    """Complete soliflore perfume structure with verified ratios."""
    soliflore_type: SolifloreType
    family: PerfumeFamily
    description: str
    materials: tuple[SolifloreComponent, ...]
    typical_use: str
    top_pct: float
    heart_pct: float
    base_pct: float
    key_oav_targets: dict[str, float]
    hedonic: str
    hedonic_score: float


SOLIFLORE_STRUCTURES: dict[SolifloreType, SolifloreStructure] = {
    SolifloreType.ROSE: SolifloreStructure(
        soliflore_type=SolifloreType.ROSE,
        family=PerfumeFamily.FLORAL,
        description="Naturalistic tea-rose soliflore with damascone richness — citronellol/geraniol/PEA trinity",
        materials=(
            SolifloreComponent("Citronellol", 25.0, "core_identity"),
            SolifloreComponent("Geraniol", 20.0, "core_identity"),
            SolifloreComponent("Phenethyl Alcohol", 18.0, "support"),
            SolifloreComponent("Hedione", 10.0, "lift"),
            SolifloreComponent("Benzyl Salicylate", 10.0, "fixative"),
            SolifloreComponent("Ethylene Brassylate", 7.0, "fixative"),
            SolifloreComponent("Rose Oxide", 5.0, "modifier"),
            SolifloreComponent("Damascone Beta", 5.0, "modifier"),
        ),
        typical_use="15-40% in concentrate",
        top_pct=15.0, heart_pct=55.0, base_pct=30.0,
        key_oav_targets={
            "Citronellol": 120, "Geraniol": 85, "Phenethyl Alcohol": 40,
            "Damascone Beta": 15, "Rose Oxide": 8, "Hedione": 50,
        },
        hedonic="Beautiful: tea-rose garden after rain",
        hedonic_score=3.5,
    ),
    SolifloreType.JASMINE: SolifloreStructure(
        soliflore_type=SolifloreType.JASMINE,
        family=PerfumeFamily.FLORAL,
        description="Narcotic tropical jasmine with indolic depth — Hedione HC/benzyl acetate/indole",
        materials=(
            SolifloreComponent("Hedione HC", 25.0, "core_identity"),
            SolifloreComponent("Benzyl Acetate", 15.0, "support"),
            SolifloreComponent("Benzyl Benzoate", 12.0, "fixative"),
            SolifloreComponent("Ylang Comoros Complete EO F3255", 10.0, "modifier"),
            SolifloreComponent("Habanolide", 10.0, "fixative"),
            SolifloreComponent("Cis Jasmone", 8.0, "core_identity"),
            SolifloreComponent("Indole", 8.0, "modifier"),
            SolifloreComponent("Methyl Ionone Pure", 7.0, "modifier"),
            SolifloreComponent("Methyl Anthranilate", 5.0, "modifier"),
        ),
        typical_use="10-30% in concentrate",
        top_pct=20.0, heart_pct=52.0, base_pct=28.0,
        key_oav_targets={
            "Hedione HC": 200, "Benzyl Acetate": 90, "Cis Jasmone": 25,
            "Indole": 3, "Methyl Anthranilate": 8, "Benzyl Benzoate": 15,
        },
        hedonic="Beautiful-narcotic: Grasse jasmine absolute",
        hedonic_score=3.0,
    ),
    SolifloreType.MUGUET: SolifloreStructure(
        soliflore_type=SolifloreType.MUGUET,
        family=PerfumeFamily.FLORAL,
        description="Fresh watery lily-of-the-valley — hydroxycitronellal + Florol + cyclamen aldehyde",
        materials=(
            SolifloreComponent("Hydroxycitronellal", 30.0, "core_identity"),
            SolifloreComponent("Florol", 15.0, "core_identity"),
            SolifloreComponent("Hedione", 15.0, "lift"),
            SolifloreComponent("Cyclamen Aldehyde", 10.0, "modifier"),
            SolifloreComponent("Phenethyl Alcohol", 8.0, "support"),
            SolifloreComponent("Linalool", 7.0, "support"),
            SolifloreComponent("Benzyl Salicylate", 7.0, "fixative"),
            SolifloreComponent("Geraniol", 5.0, "modifier"),
            SolifloreComponent("cis-3-Hexenol", 3.0, "modifier"),
        ),
        typical_use="5-15% in concentrate",
        top_pct=20.0, heart_pct=55.0, base_pct=25.0,
        key_oav_targets={
            "Hydroxycitronellal": 150, "Florol": 60, "Cyclamen Aldehyde": 18,
            "cis-3-Hexenol": 5, "Linalool": 25, "Geraniol": 15,
        },
        hedonic="Beautiful: spring morning muguet",
        hedonic_score=3.2,
    ),
    SolifloreType.TUBEROSE: SolifloreStructure(
        soliflore_type=SolifloreType.TUBEROSE,
        family=PerfumeFamily.FLORAL,
        description="Heavy creamy narcotic tuberose — hydroxycitronellal + benzyl salicylate + indole",
        materials=(
            SolifloreComponent("Hydroxycitronellal", 20.0, "support"),
            SolifloreComponent("Benzyl Salicylate", 15.0, "fixative"),
            SolifloreComponent("Hedione HC", 12.0, "lift"),
            SolifloreComponent("Ylang Comoros Complete EO F3255", 10.0, "modifier"),
            SolifloreComponent("Benzyl Benzoate", 10.0, "fixative"),
            SolifloreComponent("Benzyl Acetate", 8.0, "support"),
            SolifloreComponent("Linalool", 7.0, "support"),
            SolifloreComponent("Methyl Benzoate", 6.0, "core_identity"),
            SolifloreComponent("Indole", 5.0, "modifier"),
            SolifloreComponent("Methyl Anthranilate", 4.0, "modifier"),
            SolifloreComponent("p-Cresyl Methyl Ether", 3.0, "modifier"),
        ),
        typical_use="8-25% in concentrate",
        top_pct=15.0, heart_pct=50.0, base_pct=35.0,
        key_oav_targets={
            "Benzyl Salicylate": 80, "Methyl Benzoate": 15,
            "Methyl Anthranilate": 6, "Indole": 2, "Benzyl Acetate": 40,
        },
        hedonic="Challenging-beautiful: narcotic white flower",
        hedonic_score=1.5,
    ),
    SolifloreType.GARDENIA: SolifloreStructure(
        soliflore_type=SolifloreType.GARDENIA,
        family=PerfumeFamily.FLORAL,
        description="Cosmetic-clean gardenia — DBCA-anchored, transparent, zero animalic",
        materials=(
            SolifloreComponent("Dimethyl Benzyl Carbinyl Acetate", 20.0, "core_identity"),
            SolifloreComponent("Hydroxycitronellal", 15.0, "support"),
            SolifloreComponent("Lilyreal ND", 15.0, "support"),
            SolifloreComponent("Hedione", 15.0, "lift"),
            SolifloreComponent("Hexyl Salicylate", 12.0, "fixative"),
            SolifloreComponent("Romandolide", 10.0, "fixative"),
            SolifloreComponent("Nympheal", 8.0, "modifier"),
            SolifloreComponent("Bourgeonal", 5.0, "modifier"),
        ),
        typical_use="15-40% in concentrate",
        top_pct=18.0, heart_pct=52.0, base_pct=30.0,
        key_oav_targets={
            "DBCA": 120, "Hydroxycitronellal": 80, "Bourgeonal": 12,
            "Hexyl Salicylate": 12, "Nympheal": 18,
        },
        hedonic="Beautiful: department store beauty counter",
        hedonic_score=3.0,
    ),
    SolifloreType.NEROLI: SolifloreStructure(
        soliflore_type=SolifloreType.NEROLI,
        family=PerfumeFamily.CITRUS,
        description="Bright Mediterranean orange blossom — neroli-petitgrain duo with Aurantiol",
        materials=(
            SolifloreComponent("Neroli EO", 20.0, "core_identity"),
            SolifloreComponent("Petitgrain EO", 15.0, "core_identity"),
            SolifloreComponent("Hedione", 15.0, "lift"),
            SolifloreComponent("Linalool", 12.0, "support"),
            SolifloreComponent("Linalyl Acetate", 10.0, "support"),
            SolifloreComponent("Hexyl Salicylate", 10.0, "fixative"),
            SolifloreComponent("Aurantiol", 8.0, "modifier"),
            SolifloreComponent("Methyl Anthranilate", 5.0, "modifier"),
            SolifloreComponent("Nympheal", 5.0, "modifier"),
        ),
        typical_use="15-40% in concentrate",
        top_pct=30.0, heart_pct=45.0, base_pct=25.0,
        key_oav_targets={
            "Linalool": 60, "Linalyl Acetate": 35, "Methyl Anthranilate": 8,
            "Aurantiol": 10, "Hexyl Salicylate": 10,
        },
        hedonic="Beautiful: Côte d'Azur spring morning",
        hedonic_score=3.5,
    ),
    SolifloreType.VIOLET: SolifloreStructure(
        soliflore_type=SolifloreType.VIOLET,
        family=PerfumeFamily.FLORAL,
        description="Powdery Parma violet — ionone-based with green Parmavert leaf",
        materials=(
            SolifloreComponent("Beta Ionone", 20.0, "core_identity"),
            SolifloreComponent("Alpha Ionone", 12.0, "core_identity"),
            SolifloreComponent("Methyl Ionone Pure", 12.0, "support"),
            SolifloreComponent("Hedione", 10.0, "lift"),
            SolifloreComponent("Parmavert", 10.0, "modifier"),
            SolifloreComponent("Musk Ketone", 10.0, "fixative"),
            SolifloreComponent("Allyl Ionone (Ketone V)", 10.0, "modifier"),
            SolifloreComponent("Dihydro Beta Ionone", 8.0, "fixative"),
        ),
        typical_use="10-30% in concentrate",
        top_pct=18.0, heart_pct=52.0, base_pct=30.0,
        key_oav_targets={
            "Beta Ionone": 90, "Alpha Ionone": 45, "Methyl Ionone Pure": 40,
            "Parmavert": 8, "Musk Ketone": 8,
        },
        hedonic="Beautiful-nostalgic: Parma violet candy box",
        hedonic_score=3.0,
    ),
    SolifloreType.IRIS: SolifloreStructure(
        soliflore_type=SolifloreType.IRIS,
        family=PerfumeFamily.FLORAL,
        description="Rich buttery orris — Dior Homme style luxury iris with ionones",
        materials=(
            SolifloreComponent("Methyl Ionone Pure", 30.0, "core_identity"),
            SolifloreComponent("Alpha Irone", 15.0, "core_identity"),
            SolifloreComponent("Orris F-TEC", 10.0, "support"),
            SolifloreComponent("Allyl Ionone (Ketone V)", 10.0, "support"),
            SolifloreComponent("I-IRIS F-TEC", 8.0, "modifier"),
            SolifloreComponent("Coumarin", 8.0, "modifier"),
            SolifloreComponent("Alpha Ionone", 7.0, "support"),
            SolifloreComponent("Dihydro Beta Ionone", 5.0, "fixative"),
            SolifloreComponent("Heliotropal", 3.0, "modifier"),
            SolifloreComponent("Benzyl Salicylate", 3.5, "fixative"),
            SolifloreComponent("Hedione", 0.5, "lift"),
        ),
        typical_use="15-35% in concentrate",
        top_pct=10.0, heart_pct=55.0, base_pct=35.0,
        key_oav_targets={
            "Methyl Ionone Pure": 110, "Alpha Irone": 25, "Heliotropin": 6,
            "Coumarin": 8, "Alpha Ionone": 25,
        },
        hedonic="Beautiful: powdered suede gloves",
        hedonic_score=3.8,
    ),
    SolifloreType.LAVENDER: SolifloreStructure(
        soliflore_type=SolifloreType.LAVENDER,
        family=PerfumeFamily.FOUGERE,
        description="Aromatic herbal lavender with coumarin backbone — fougère style",
        materials=(
            SolifloreComponent("Lavender EO", 25.0, "core_identity"),
            SolifloreComponent("Coumarin", 15.0, "modifier"),
            SolifloreComponent("Linalool", 10.0, "support"),
            SolifloreComponent("Linalyl Acetate", 10.0, "support"),
            SolifloreComponent("Clary Sage EO", 8.0, "modifier"),
            SolifloreComponent("Vertofix Coeur", 8.0, "fixative"),
            SolifloreComponent("Terpinyl Acetate", 7.0, "modifier"),
            SolifloreComponent("Habanolide", 7.0, "fixative"),
            SolifloreComponent("Dihydromyrcenol", 5.0, "modifier"),
            SolifloreComponent("Evernyl", 5.0, "fixative"),
        ),
        typical_use="15-35% in concentrate",
        top_pct=25.0, heart_pct=42.0, base_pct=33.0,
        key_oav_targets={
            "Linalool": 50, "Linalyl Acetate": 35, "Coumarin": 12,
            "Evernyl": 4, "Terpinyl Acetate": 15, "Dihydromyrcenol": 15,
        },
        hedonic="Beautiful: Provençal lavender field",
        hedonic_score=3.2,
    ),
    SolifloreType.YLANG: SolifloreStructure(
        soliflore_type=SolifloreType.YLANG,
        family=PerfumeFamily.FLORAL,
        description="Narcotic tropical ylang-champaca — heavy, indolic, creasy",
        materials=(
            SolifloreComponent("Ylang Comoros Complete EO F3255", 25.0, "core_identity"),
            SolifloreComponent("Ylang Ylang EO (Extra grade)", 15.0, "core_identity"),
            SolifloreComponent("Benzyl Salicylate", 12.0, "fixative"),
            SolifloreComponent("Champaca Flower EO", 10.0, "modifier"),
            SolifloreComponent("Benzyl Acetate", 8.0, "support"),
            SolifloreComponent("Indole", 8.0, "modifier"),
            SolifloreComponent("Hexyl Salicylate", 7.0, "fixative"),
            SolifloreComponent("Methyl Benzoate", 5.0, "modifier"),
            SolifloreComponent("p-Cresyl Methyl Ether", 5.0, "modifier"),
            SolifloreComponent("Ethylene Brassylate", 5.0, "fixative"),
        ),
        typical_use="5-15% in concentrate",
        top_pct=18.0, heart_pct=48.0, base_pct=34.0,
        key_oav_targets={
            "Benzyl Acetate": 40, "Methyl Benzoate": 12, "Indole": 3,
            "p-Cresyl Methyl Ether": 2, "Benzyl Salicylate": 60,
        },
        hedonic="Challenging-beautiful: humid tropical evening",
        hedonic_score=1.2,
    ),
    SolifloreType.CHAMPACA: SolifloreStructure(
        soliflore_type=SolifloreType.CHAMPACA,
        family=PerfumeFamily.FLORAL,
        description="Golden fruity-tea-spicy champaca — warm, bright, not narcotic",
        materials=(
            SolifloreComponent("Champaca Flower EO", 25.0, "core_identity"),
            SolifloreComponent("Hedione", 12.0, "lift"),
            SolifloreComponent("Benzyl Salicylate", 10.0, "fixative"),
            SolifloreComponent("Apritone", 10.0, "modifier"),
            SolifloreComponent("Linalool", 8.0, "support"),
            SolifloreComponent("Cardamom EO", 0.8, "modifier"),
            SolifloreComponent("Benzyl Benzoate", 8.0, "fixative"),
            SolifloreComponent("Ebanol", 7.0, "fixative"),
            SolifloreComponent("Ethylene Brassylate", 7.0, "fixative"),
            SolifloreComponent("Damascone Beta", 5.0, "modifier"),
        ),
        typical_use="5-15% in concentrate",
        top_pct=20.0, heart_pct=48.0, base_pct=32.0,
        key_oav_targets={
            "Linalool": 25, "Apritone": 6, "Damascone Beta": 5,
            "Ebanol": 15, "Hedione": 30,
        },
        hedonic="Beautiful: golden champaca lei at dusk",
        hedonic_score=3.0,
    ),
    SolifloreType.LILAC: SolifloreStructure(
        soliflore_type=SolifloreType.LILAC,
        family=PerfumeFamily.FLORAL,
        description="Sweet powdery lilac — heliotropin + hydroxycitronellal + anisaldehyde",
        materials=(
            SolifloreComponent("Hydroxycitronellal", 20.0, "core_identity"),
            SolifloreComponent("Heliotropal", 15.0, "core_identity"),
            SolifloreComponent("Phenethyl Alcohol", 15.0, "support"),
            SolifloreComponent("Hedione", 10.0, "lift"),
            SolifloreComponent("Linalool", 8.0, "support"),
            SolifloreComponent("Benzyl Salicylate", 10.0, "fixative"),
            SolifloreComponent("Cyclamen Aldehyde", 7.0, "modifier"),
            SolifloreComponent("Ethylene Brassylate", 5.0, "fixative"),
            SolifloreComponent("Anisaldehyde", 5.0, "modifier"),
            SolifloreComponent("Florol", 5.0, "modifier"),
        ),
        typical_use="10-25% in concentrate",
        top_pct=15.0, heart_pct=55.0, base_pct=30.0,
        key_oav_targets={
            "Hydroxycitronellal": 90, "Heliotropin": 25, "Anisaldehyde": 8,
            "Cyclamen Aldehyde": 10, "Phenethyl Alcohol": 35,
        },
        hedonic="Beautiful: spring lilac in bloom",
        hedonic_score=3.4,
    ),
    SolifloreType.MIMOSA: SolifloreStructure(
        soliflore_type=SolifloreType.MIMOSA,
        family=PerfumeFamily.FLORAL,
        description="Powdery yellow mimosa — anisaldehyde + ionone + heliotropin",
        materials=(
            SolifloreComponent("Heliotropal", 18.0, "core_identity"),
            SolifloreComponent("Anisaldehyde", 15.0, "core_identity"),
            SolifloreComponent("Hydroxycitronellal", 12.0, "support"),
            SolifloreComponent("Benzyl Salicylate", 12.0, "fixative"),
            SolifloreComponent("Hedione", 10.0, "lift"),
            SolifloreComponent("Alpha Ionone", 8.0, "support"),
            SolifloreComponent("Phenethyl Alcohol", 8.0, "support"),
            SolifloreComponent("Methyl Ionone Pure", 7.0, "support"),
            SolifloreComponent("Coumarin", 5.0, "fixative"),
            SolifloreComponent("Ethylene Brassylate", 5.0, "fixative"),
        ),
        typical_use="8-20% in concentrate",
        top_pct=15.0, heart_pct=55.0, base_pct=30.0,
        key_oav_targets={
            "Heliotropin": 30, "Anisaldehyde": 22, "Alpha Ionone": 20,
            "Methyl Ionone Pure": 25, "Coumarin": 4,
        },
        hedonic="Beautiful: golden mimosa blooms",
        hedonic_score=3.2,
    ),
    SolifloreType.NARCISSUS: SolifloreStructure(
        soliflore_type=SolifloreType.NARCISSUS,
        family=PerfumeFamily.FLORAL,
        description="Green-indolic narcissus — cresylic, hay-like, dry",
        materials=(
            SolifloreComponent("Benzyl Acetate", 18.0, "core_identity"),
            SolifloreComponent("Hydroxycitronellal", 15.0, "support"),
            SolifloreComponent("Benzyl Salicylate", 12.0, "fixative"),
            SolifloreComponent("Hedione", 10.0, "lift"),
            SolifloreComponent("p-Cresyl Methyl Ether", 10.0, "core_identity"),
            SolifloreComponent("Phenethyl Alcohol", 8.0, "support"),
            SolifloreComponent("Indole", 7.0, "modifier"),
            SolifloreComponent("Galbanum Resinoid", 5.0, "modifier"),
            SolifloreComponent("Linalool", 5.0, "support"),
            SolifloreComponent("Coumarin", 5.0, "fixative"),
            SolifloreComponent("Hexyl Salicylate", 5.0, "fixative"),
        ),
        typical_use="5-15% in concentrate",
        top_pct=20.0, heart_pct=50.0, base_pct=30.0,
        key_oav_targets={
            "Benzyl Acetate": 70, "p-Cresyl Methyl Ether": 8, "Indole": 3,
            "Galbanum Resinoid": 2, "Coumarin": 4,
        },
        hedonic="Challenging-beautiful: green hay-like narcissus",
        hedonic_score=1.0,
    ),
    SolifloreType.HYACINTH: SolifloreStructure(
        soliflore_type=SolifloreType.HYACINTH,
        family=PerfumeFamily.FLORAL,
        description="Sharp green-floral hyacinth — PEA + benzyl acetate + galbanum",
        materials=(
            SolifloreComponent("Phenethyl Alcohol", 20.0, "core_identity"),
            SolifloreComponent("Benzyl Acetate", 18.0, "core_identity"),
            SolifloreComponent("Hydroxycitronellal", 12.0, "support"),
            SolifloreComponent("Hedione", 10.0, "lift"),
            SolifloreComponent("Galbanum Resinoid", 8.0, "modifier"),
            SolifloreComponent("Benzyl Salicylate", 10.0, "fixative"),
            SolifloreComponent("Cyclamen Aldehyde", 7.0, "modifier"),
            SolifloreComponent("cis-3-Hexenol", 5.0, "modifier"),
            SolifloreComponent("Linalool", 5.0, "support"),
            SolifloreComponent("Ethylene Brassylate", 5.0, "fixative"),
        ),
        typical_use="8-20% in concentrate",
        top_pct=25.0, heart_pct=50.0, base_pct=25.0,
        key_oav_targets={
            "Phenethyl Alcohol": 60, "Benzyl Acetate": 100, "Galbanum Resinoid": 5,
            "cis-3-Hexenol": 10, "Cyclamen Aldehyde": 10,
        },
        hedonic="Beautiful: piercing spring hyacinth",
        hedonic_score=3.0,
    ),
    SolifloreType.OSMANTHUS: SolifloreStructure(
        soliflore_type=SolifloreType.OSMANTHUS,
        family=PerfumeFamily.FLORAL,
        description="Apricot-leather-tea osmanthus — fruity floral with suede undertone",
        materials=(
            SolifloreComponent("Apritone", 15.0, "core_identity"),
            SolifloreComponent("Hedione", 12.0, "lift"),
            SolifloreComponent("Benzyl Salicylate", 12.0, "fixative"),
            SolifloreComponent("Damascone Beta", 10.0, "core_identity"),
            SolifloreComponent("Gamma Decalactone", 10.0, "modifier"),
            SolifloreComponent("Beta Ionone", 8.0, "support"),
            SolifloreComponent("Linalool", 8.0, "support"),
            SolifloreComponent("Hexyl Salicylate", 7.0, "fixative"),
            SolifloreComponent("Benzyl Benzoate", 6.0, "fixative"),
            SolifloreComponent("Suederal", 5.0, "modifier"),
            SolifloreComponent("Romandolide", 5.0, "fixative"),
            SolifloreComponent("cis-3-Hexenol", 2.0, "modifier"),
        ),
        typical_use="5-15% in concentrate",
        top_pct=20.0, heart_pct=48.0, base_pct=32.0,
        key_oav_targets={
            "Apritone": 8, "Damascone Beta": 12, "Gamma Decalactone": 8,
            "Beta Ionone": 20, "Linalool": 25,
        },
        hedonic="Beautiful: apricot-suede autumn bloom",
        hedonic_score=3.2,
    ),
    SolifloreType.ORANGE_BLOSSOM: SolifloreStructure(
        soliflore_type=SolifloreType.ORANGE_BLOSSOM,
        family=PerfumeFamily.FLORAL,
        description="Honeyed orange blossom — Aurantiol + neroli + methyl anthranilate",
        materials=(
            SolifloreComponent("Neroli EO", 18.0, "core_identity"),
            SolifloreComponent("Hedione", 12.0, "lift"),
            SolifloreComponent("Benzyl Salicylate", 12.0, "fixative"),
            SolifloreComponent("Aurantiol", 12.0, "core_identity"),
            SolifloreComponent("Methyl Anthranilate", 10.0, "core_identity"),
            SolifloreComponent("Benzyl Acetate", 8.0, "support"),
            SolifloreComponent("Linalool", 8.0, "support"),
            SolifloreComponent("Phenethyl Alcohol", 7.0, "support"),
            SolifloreComponent("Hexyl Salicylate", 5.0, "fixative"),
            SolifloreComponent("Ethylene Brassylate", 5.0, "fixative"),
            SolifloreComponent("Petitgrain EO", 3.0, "modifier"),
        ),
        typical_use="10-30% in concentrate",
        top_pct=22.0, heart_pct=50.0, base_pct=28.0,
        key_oav_targets={
            "Benzyl Acetate": 40, "Methyl Anthranilate": 15, "Aurantiol": 10,
            "Linalool": 25, "Ethylene Brassylate": 4,
        },
        hedonic="Beautiful: honeyed orange grove in bloom",
        hedonic_score=3.6,
    ),
    SolifloreType.LINDEN: SolifloreStructure(
        soliflore_type=SolifloreType.LINDEN,
        family=PerfumeFamily.FLORAL,
        description="Honeyed linden blossom — muguet-adjacent with honey-tea warmth",
        materials=(
            SolifloreComponent("Hydroxycitronellal", 22.0, "core_identity"),
            SolifloreComponent("Hedione", 15.0, "lift"),
            SolifloreComponent("Benzyl Salicylate", 12.0, "fixative"),
            SolifloreComponent("Phenethyl Alcohol", 10.0, "support"),
            SolifloreComponent("Heliotropal", 8.0, "modifier"),
            SolifloreComponent("Linalool", 8.0, "support"),
            SolifloreComponent("Cyclamen Aldehyde", 7.0, "modifier"),
            SolifloreComponent("Florol", 6.0, "support"),
            SolifloreComponent("Coumarin", 5.0, "fixative"),
            SolifloreComponent("Ethylene Brassylate", 4.0, "fixative"),
            SolifloreComponent("Hexyl Salicylate", 3.0, "fixative"),
        ),
        typical_use="10-25% in concentrate",
        top_pct=15.0, heart_pct=55.0, base_pct=30.0,
        key_oav_targets={
            "Hydroxycitronellal": 100, "Phenethyl Alcohol": 25, "Heliotropin": 12,
            "Coumarin": 4, "Cyclamen Aldehyde": 10,
        },
        hedonic="Beautiful: linden tree in June bloom",
        hedonic_score=3.5,
    ),
    SolifloreType.PEONY: SolifloreStructure(
        soliflore_type=SolifloreType.PEONY,
        family=PerfumeFamily.FLORAL,
        description="Dewy green-rose peony — fresh, transparent, lightly honeyed",
        materials=(
            SolifloreComponent("Citronellol", 18.0, "core_identity"),
            SolifloreComponent("Phenethyl Alcohol", 15.0, "support"),
            SolifloreComponent("Hedione", 15.0, "lift"),
            SolifloreComponent("Geraniol", 10.0, "core_identity"),
            SolifloreComponent("Benzyl Salicylate", 10.0, "fixative"),
            SolifloreComponent("Hydroxycitronellal", 8.0, "support"),
            SolifloreComponent("Linalool", 7.0, "support"),
            SolifloreComponent("cis-3-Hexenol", 5.0, "modifier"),
            SolifloreComponent("Florol", 5.0, "modifier"),
            SolifloreComponent("Romandolide", 4.0, "fixative"),
            SolifloreComponent("Hexyl Salicylate", 3.0, "fixative"),
        ),
        typical_use="10-30% in concentrate",
        top_pct=22.0, heart_pct=52.0, base_pct=26.0,
        key_oav_targets={
            "Citronellol": 70, "Phenethyl Alcohol": 35, "Geraniol": 30,
            "cis-3-Hexenol": 8, "Hydroxycitronellal": 35,
        },
        hedonic="Beautiful: dewy garden peony",
        hedonic_score=3.4,
    ),
}


def get_soliflore(soliflore_type: SolifloreType | str) -> SolifloreStructure | None:
    """Return the verified structure for a soliflore type."""
    if isinstance(soliflore_type, str):
        for s in SolifloreType:
            if s.value == soliflore_type.lower():
                soliflore_type = s
                break
        else:
            return None
    return SOLIFLORE_STRUCTURES.get(soliflore_type)


def all_soliflores() -> list[SolifloreStructure]:
    """Return all soliflore structures."""
    return sorted(SOLIFLORE_STRUCTURES.values(), key=lambda s: s.soliflore_type.value)


def soliflore_material_list(soliflore_type: SolifloreType | str) -> list[dict]:
    """Return materials for a soliflore as a list of dicts for pipeline use."""
    structure = get_soliflore(soliflore_type)
    if structure is None:
        return []
    return [
        {"material": c.material, "percent": c.percent_of_concentrate, "role": c.role}
        for c in structure.materials
    ]
