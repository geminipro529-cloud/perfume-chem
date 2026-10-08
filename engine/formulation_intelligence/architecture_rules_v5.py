"""Closed own-odor rules for v5 architectural hypotheses, never dose evidence.

Kept separate from control facets so old plans/template fingerprints are stable.
Exact identities are conjuncts, not substring aliases or stock availability.
"""

from __future__ import annotations

import re
from typing import Iterable


def _groups(*values: str) -> tuple[frozenset[str], ...]:
    return tuple(frozenset(value.split()) for value in values)


REQUIREMENTS = {
    "v5_leather_spice": _groups("leather leathery suede", "spicy spice saffron"),
    "v5_resin": _groups("resin resinous balsam balsamic"),
    "v5_resin_leather": _groups("resin resinous balsamic", "leather leathery"),
    "v5_vanillic_balsam": _groups("vanilla vanillic", "balsam balsamic"),
    "v5_smoky_wood": _groups("smoky smoke", "wood woody"),
    "v5_smoke": _groups("smoky smoke"),
    "v5_green_resin": _groups("green", "resin resinous balsamic"),
    "v5_floral_leather": _groups("floral flower", "leathery leather"),
    "v5_citrus_pepper_resin": _groups("citrus", "pepper peppery", "resin resinous"),
    "v5_hay": _groups("hay", "almond tonka tobacco coumarinic"),
    "v5_floral_hay": _groups("floral", "hay"),
    "v5_creamy_wood": _groups("creamy", "wood woody"),
    "v5_warm_wood": _groups("warm warmth", "wood woody", "resin resinous leathery"),
    "v5_dry_wood": _groups("dry", "wood woody"),
    "v5_bitter_green_floral": _groups("bitter", "green", "floral", "citrus orange"),
    "v5_mineral_resin": _groups("mineral", "resin resinous"),
    "v5_marine": _groups("marine ozonic"),
    "v5_wet_floral": _groups("green fresh freshness", "muguet hyacinth"),
    "v5_solar_floral": _groups("solar", "floral flower"),
    "v5_green_floral": _groups("green", "floral flower"),
    "v5_cream": _groups("creamy milky dairy lactonic"),
    "v5_terpenic_floral": _groups("terpenic terpene", "floral"),
    "v5_aromatic_floral": _groups("aromatic", "floral"),
    "v5_earthy_green": _groups("earthy", "green"),
    "v5_sweet_aromatic": _groups("sweet sweetness", "aromatic spicy"),
    "v5_green_aromatic": _groups("green", "aromatic"),
    "v5_transparent_floral": _groups("floral", "transparent transparency sheer airy"),
    "v5_apricot_floral": _groups("floral", "apricot"),
    "v5_crisp_pineapple": _groups("pineapple", "green fresh freshness crisp"),
    "v5_sweet_fruit": _groups("fruit fruity", "sweet sweetness caramel"),
    "v5_crisp_apple": _groups("apple", "green fresh freshness crisp"),
    "v5_ripe_apple": _groups("apple", "ripe cider"),
    "v5_rhubarb": _groups("rhubarb", "green tart zesty"),
    "v5_grape_floral": _groups("grape", "floral"),
    "v5_rose": _groups("rose rosy"),
    "v5_tropical_fruit": _groups("fruit fruity", "tropical"),
    "v5_wet_green": _groups("green", "watery aqueous"),
    "v5_toast": _groups("toasted roasted toast roast"),
    "v5_floral": _groups("floral"),
    "v5_maple": _groups("maple"),
    "v5_gamma_powder": _groups("powder powdery", "orris violet iris"),
    "v5_helvetolide": _groups("musk musky", "pear"),
    "v5_exaltolide": _groups("musk musky", "powder powdery woody"),
    "v5_decanal": _groups("citrus", "aldehydic aldehyde"),
    "v5_dodecanal": _groups("waxy wax", "aldehydic aldehyde"),
}

# Exact closed operations for the reviewed v5 tranche. Values are template,
# predicate, operation, canonical refinement target (or None for role addition).
OPTIONS = {
    ("musk_powder_v5", "ionone_powder"): ("powder", "v5_gamma_powder", "ADD_ROLE", None),
    ("fougere_leather_v5", "leather_edge"): ("v5_leather", "v5_leather_spice", "ADD_ROLE", None),
    ("fougere_leather_v5", "resin_edge"): ("v5_resin", "v5_resin_leather", "ADD_ROLE", None),
    ("wood_mineral_v5", "smooth_wood"): ("dry_wood", "v5_dry_wood", "ADD_ROLE", None),
    ("cedar_guaiac_v5", "smoky_wood"): ("v5_smoke", "v5_smoky_wood", "ADD_ROLE", None),
    ("vetiver_smoky_v5", "smoky_wood"): ("v5_smoke", "v5_smoky_wood", "ADD_ROLE", None),
    ("oud_rose_amber_v5", "resin_leather"): ("v5_resin", "v5_resin_leather", "ADD_ROLE", None),
    ("oud_rose_amber_v5", "vanillic_balsam"): ("v5_resin", "v5_vanillic_balsam", "ADD_ROLE", None),
    ("resin_styrax_v5", "leathery_resin"): ("v5_resin", "v5_resin_leather", "ADD_ROLE", None),
    ("resin_animalic_v5", "leathery_resin"): ("v5_resin", "v5_resin_leather", "ADD_ROLE", None),
    ("leather_smoky_v5", "smoky_wood"): ("v5_smoke", "v5_smoky_wood", "ADD_ROLE", None),
    ("leather_green_v5", "green_resin"): ("green_leaf", "v5_green_resin", "ADD_ROLE", None),
    ("leather_floral_v5", "floral_leather_bridge"): ("v5_flower", "v5_floral_leather", "ADD_ROLE", None),
    ("incense_elemi_v5", "citrus_pepper_resin"): ("v5_terpenic", "v5_citrus_pepper_resin", "ADD_ROLE", None),
    ("incense_church_v5", "smoky_wood"): ("v5_smoke", "v5_smoky_wood", "ADD_ROLE", None),
    ("tobacco_dry_v5", "hay_support"): ("v5_hay", "v5_hay", "ADD_ROLE", None),
    ("tobacco_dry_v5", "floral_hay"): ("v5_flower", "v5_floral_hay", "ADD_ROLE", None),
    ("tobacco_pipe_v5", "hay_support"): ("v5_hay", "v5_hay", "ADD_ROLE", None),
    ("tobacco_pipe_v5", "balsamic_support"): ("v5_resin", "v5_vanillic_balsam", "ADD_ROLE", None),
    ("tobacco_smoky_v5", "smoky_wood"): ("v5_smoke", "v5_smoky_wood", "ADD_ROLE", None),
    ("soft_coumarin_v5", "hay_support"): ("v5_hay", "v5_hay", "ADD_ROLE", None),
    ("soft_vanilla_v5", "balsamic_support"): ("v5_resin", "v5_vanillic_balsam", "ADD_ROLE", None),
    ("floral_amber_white_v5", "resin_support"): ("v5_resin", "v5_resin", "ADD_ROLE", None),
    ("floral_amber_balsam_v5", "vanillic_balsam"): ("v5_resin", "v5_vanillic_balsam", "ADD_ROLE", None),
    ("floral_amber_balsam_v5", "leathery_resin"): ("v5_resin", "v5_resin_leather", "ADD_ROLE", None),
    ("wood_sandal_cedar_v5", "creamy_wood"): ("creamy_wood", "v5_creamy_wood", "ADD_ROLE", None),
    ("wood_sandal_cedar_v5", "warm_wood"): ("dry_wood", "v5_warm_wood", "ADD_ROLE", None),
    ("cit_cedrat_v5", "green_flower_bridge"): ("v5_terpenic", "v5_bitter_green_floral", "ADD_ROLE", None),
    ("cologne_neroli_v5", "green_flower_bridge"): ("v5_terpenic", "v5_bitter_green_floral", "ADD_ROLE", None),
    ("green_conifer_v5", "dry_wood"): ("dry_wood", "v5_dry_wood", "ADD_ROLE", None),
    ("aqua_melon_v5", "marine"): ("rain_water", "v5_marine", "ADD_ROLE", None),
    ("aqua_melon_v5", "wet_floral"): ("v5_flower", "v5_wet_floral", "ADD_ROLE", None),
    ("aqua_airy_mineral_v5", "mineral_resin"): ("v5_resin", "v5_mineral_resin", "ADD_ROLE", None),
    ("aqua_solar_v5", "solar_floral"): ("v5_flower", "v5_solar_floral", "ADD_ROLE", None),
    ("aqua_solar_v5", "green_floral"): ("v5_flower", "v5_green_floral", "ADD_ROLE", None),
    ("ab_waxy_v5", "waxy_aldehyde"): ("aldehydic", "v5_dodecanal", "ADD_ROLE", None),
    ("ab_citrus_v5", "citrus_aldehyde"): ("aldehydic", "v5_decanal", "ADD_ROLE", None),
    ("hy_incense_floral_v5", "bright_resin"): ("v5_terpenic", "v5_citrus_pepper_resin", "ADD_ROLE", None),
    ("hy_incense_floral_v5", "mineral_resin"): ("v5_resin", "v5_mineral_resin", "ADD_ROLE", None),
    ("hy_rose_mineral_v5", "mineral_resin"): ("v5_resin", "v5_mineral_resin", "ADD_ROLE", None),
    ("magnolia_cream_v5", "musk_texture"): ("skin_musk", "v5_exaltolide", "ADD_ROLE", None),
    ("magnolia_cream_v5", "lactonic_texture"): ("v5_cream", "v5_cream", "ADD_ROLE", None),
    ("light_sweet_pea_v5", "terpenic_flower"): ("v5_terpenic", "v5_terpenic_floral", "ADD_ROLE", None),
    ("trop_alba_v5", "aromatic_flower"): ("v5_flower", "v5_aromatic_floral", "ADD_ROLE", None),
    ("lav_coffee_milk_v5", "milk_texture"): ("v5_cream", "v5_cream", "ADD_ROLE", None),
    ("green_hyacinth_white_v5", "earthy_green"): ("green_leaf", "v5_earthy_green", "ADD_ROLE", None),
    ("aquatic_nelumbo_v5", "aromatic_flower"): ("v5_flower", "v5_aromatic_floral", "ADD_ROLE", None),
    ("aquatic_nymphaea_prolifera_v5", "sweet_aromatic"): ("v5_flower", "v5_sweet_aromatic", "ADD_ROLE", None),
    ("orchid_cymbidium_sunny_v5", "green_aromatic"): ("v5_terpenic", "v5_green_aromatic", "ADD_ROLE", None),
    ("orchard_heart_v5", "transparent_flower"): ("v5_flower", "v5_transparent_floral", "ADD_ROLE", None),
    ("orchard_heart_v5", "apricot_flower"): ("v5_flower", "v5_apricot_floral", "ADD_ROLE", None),
    ("pineapple_woody_v5", "crisp_fruit"): ("fruit", "v5_crisp_pineapple", "ADD_ROLE", None),
    ("pineapple_woody_v5", "sweet_fruit_body"): ("fruit", "v5_sweet_fruit", "ADD_ROLE", None),
    ("lav_apple_v5", "crisp_apple"): ("fruit", "v5_crisp_apple", "ADD_ROLE", None),
    ("lav_apple_v5", "ripe_apple"): ("fruit", "v5_ripe_apple", "ADD_ROLE", None),
    ("berry_rhubarb_v5", "rhubarb_contour"): ("fruit", "v5_rhubarb", "ADD_ROLE", None),
    ("berry_grape_v5", "grape_flower"): ("v5_flower", "v5_grape_floral", "ADD_ROLE", None),
    ("berry_floral_bridge_v5", "transparent_flower"): ("v5_flower", "v5_transparent_floral", "ADD_ROLE", None),
    ("berry_floral_bridge_v5", "rose_petals"): ("v5_flower", "v5_rose", "ADD_ROLE", None),
    ("trop_passionfruit_v5", "tropical_body"): ("fruit", "v5_tropical_fruit", "ADD_ROLE", None),
    ("trop_melon_v5", "rind_green"): ("green_leaf", "v5_wet_green", "ADD_ROLE", None),
    ("trop_melon_v5", "marine"): ("rain_water", "v5_marine", "ADD_ROLE", None),
    ("trop_banana_v5", "cream_texture"): ("v5_cream", "v5_cream", "ADD_ROLE", None),
    ("stone_peach_skin_v5", "dry_frame"): ("dry_wood", "v5_dry_wood", "ADD_ROLE", None),
    ("van_caramel_toast_v5", "toast"): ("v5_toast", "v5_toast", "ADD_ROLE", None),
    ("van_floral_gourmand_v5", "balsamic_link"): ("v5_resin", "v5_resin", "ADD_ROLE", None),
    ("roast_coffee_v5", "roast"): ("v5_toast", "v5_toast", "ADD_ROLE", None),
    ("roast_cacao_v5", "cream_texture"): ("v5_cream", "v5_cream", "ADD_ROLE", None),
    ("roast_cacao_v5", "floral_texture"): ("v5_flower", "v5_floral", "ADD_ROLE", None),
    ("dairy_maple_v5", "maple_accent"): ("v5_toast", "v5_maple", "ADD_ROLE", None),
    ("tea_smoked_v5", "smoke"): ("v5_smoke", "v5_smoke", "ADD_ROLE", None),
    ("hy_tea_musk_v5", "powder_musk"): ("skin_musk", "v5_exaltolide", "REFINE_ROLE", "facet_skin_musk"),
    ("hy_tea_musk_v5", "pear_musk"): ("skin_musk", "v5_helvetolide", "REFINE_ROLE", "facet_skin_musk"),
    ("lav_iris_v5", "woody_iris_grade"): ("iris_woody", "v5_gamma_powder", "REFINE_ROLE", "facet_iris_woody"),
    ("lav_iris_v5", "cosmetic_iris_grade"): ("iris_cosmetic", "v5_gamma_powder", "REFINE_ROLE", "facet_iris_cosmetic"),
}

EXACT_IDENTITIES = {
    "v5_gamma_powder": frozenset({"methyl ionone gamma coeur", "meth ionone gamma coeur"}),
    "v5_helvetolide": frozenset({"helvetolide"}),
    "v5_exaltolide": frozenset({"exaltolide"}),
    "v5_decanal": frozenset({"decanal", "aldehyde c 10 decanal"}),
    "v5_dodecanal": frozenset({"n dodecanal", "dodecanal", "aldehyde c 12 lauryl",
                               "aldehyde c 12 lauric dodecanal"}),
}

# Absence from this partial vocabulary is NOT a certified absence of an odor.
_AVOID_GROUPS = (
    frozenset({"smoke", "smoky", "smokiness"}),
    frozenset({"sweet", "sweetness", "sugary"}),
    frozenset({"coconut"}), frozenset({"peach"}),
    frozenset({"leather", "leathery", "suede"}),
    frozenset({"animalic"}), frozenset({"vanilla", "vanillic"}),
    frozenset({"rose", "rosy"}), frozenset({"jasmine", "jasmin"}),
    frozenset({"marine", "oceanic"}),
)


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def positive_description(value: str) -> str:
    """Conservative clause filter, not an NLP assertion of negative odor absence.

    Ambiguous negated/application clauses supply no positive eligibility. Source
    prose must still be reviewed; a sentence splitter cannot establish truth.
    """
    # Application/keyword suffixes never describe the material's own odor.
    # Preserve only the preceding description; do not mine later sentences.
    value = re.split(
        r"\b(?:used (?:in|as|for)|useful (?:in|as|for)|for use|blends? with|"
        r"pairs? with|reconstitutions?|applications?|synerg\w*|keywords?)\b|\buse\s*:",
        value, maxsplit=1, flags=re.I,
    )[0]
    clauses = re.split(r"[.;\n]", value)
    rejected = r"\b(?:no|not|without|unlike|free of)\b|\bnon[-\s]+\w+|\b\w+[-\s]+free\b"
    return " ".join(c for c in clauses if not re.search(rejected, c, re.I))


def eligible(identity: str, vocabulary: frozenset[str], requirement: str) -> bool:
    groups = REQUIREMENTS.get(requirement)
    identities = EXACT_IDENTITIES.get(requirement)
    return (groups is not None and all(vocabulary & group for group in groups)
            and (identities is None or _key(identity) in identities))


def own_odor_avoid_conflict(vocabulary: frozenset[str], avoid: Iterable[str]) -> bool:
    # Whole single-facet constraints only. "Heavy vanilla" is not "no vanilla".
    rejected = {_key(value) for value in avoid}
    return any(rejected & group and vocabulary & group for group in _AVOID_GROUPS)
