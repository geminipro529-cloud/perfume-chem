"""Fast, constraint-first perfume composition planning.

The planner is intentionally deterministic.  It combines a versioned set of
perfumery architecture capsules with the current inventory and a hard request
compiler.  It does *not* turn descriptor fit, OAV, sales, ingredient count, or
legacy valence into a beauty score.  Returned formulas are bench hypotheses;
sensory quality remains untested until the user smells a controlled trial.

The architecture is deliberately hybrid:

1. exact request and stock-form constraints;
2. concept-specific, nonredundant functional roles;
3. inventory-bound material selection with explicit alternatives;
4. separate liquid and solid arithmetic;
5. a deterministic post-plan critic and truthful execution holds.

This gives the fast UI more perfume-specific reasoning than generic slot
filling while staying below the authority of a human sensory result.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_FLOOR, Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

from engine.ifra_standards import single_material_limit_pct
from engine.ingredient_intelligence import MaterialProfile, get_profile
from engine.inventory_completions import effective_design_ready
from engine.inventory_parser import (
    InventoryMaterial,
    is_user_compounding_held,
    parse_inventory,
)
from engine.name_utils import normalize_name
from engine.personal_inventory import (
    DESIGN_ONLY_AUTHORITY,
    LIVE_TEXT_AUTHORITY,
    materialize_personal_inventory,
    personal_inventory_identity_key,
)
from engine.research.commercial_references import (
    DEFAULT_REGISTRY_PATH,
    build_commercial_reference_panel,
    load_commercial_reference_registry,
    resolve_documentary_references,
)
from engine.research.contracts import FALSE_ACTION_AUTHORITY, stable_payload_hash
from engine.research.normal_use_ceilings import (
    NormalUseCeiling,
    match_normal_use_ceiling,
    match_screening_default,
)
from engine.research.request_interpretation import (
    RequestInterpretationInputV1,
    interpret_request,
    positive_reference_text,
)

_ROOT = Path(__file__).resolve().parents[2]
_INVENTORY_PATH = _ROOT / "inventory.txt"
_MIN_RAW_TRANSFER_UL = 10
_SOLID_MARKERS = ("crystal", "powder", "solid", "flakes")
_EXCLUDED_CATEGORIES = ("technical", "solvent", "carrier", "stabilizer")
_DESIGN_FUNCTIONAL_CARRIERS = {
    "benzyl benzoate",
    "diethyl phthalate",
    "dipropylene glycol",
    "triethyl citrate",
}
_CANDIDATE_BASE_CACHE: dict[
    tuple[str, str],
    tuple[tuple[Candidate, ...], tuple[str, ...]],
] = {}


def _inventory_text_sha256() -> str:
    return hashlib.sha256(_INVENTORY_PATH.read_bytes()).hexdigest()


def _reference_registry_sha256() -> str:
    return hashlib.sha256(DEFAULT_REGISTRY_PATH.read_bytes()).hexdigest()


@lru_cache(maxsize=8)
def _cached_legacy_inventory(
    inventory_text_sha256: str,
    include_unavailable: bool,
) -> tuple[InventoryMaterial, ...]:
    del inventory_text_sha256  # cache invalidation key; parser reads the canonical path
    # Keep distinct working strengths.  Collapsing to the highest dilution is
    # useful for old name-only callers, but it destroys the exact stock choice
    # needed by the composition planner (for example 0.1% and 1% Geosmin).
    return tuple(
        parse_inventory(
            unique=False,
            include_unavailable=include_unavailable,
        )
    )


@lru_cache(maxsize=4)
def _cached_reference_registry(registry_sha256: str):
    del registry_sha256
    return load_commercial_reference_registry()


@dataclass(frozen=True, slots=True)
class RoleSpec:
    role_id: str
    label: str
    note: str
    function: str
    share: float
    preferred_materials: tuple[str, ...]
    descriptor_weights: tuple[tuple[str, float], ...] = ()
    exact_preference_required: bool = False
    max_raw_share: float | None = None
    # The row carries a note the brief names (a requested facet, its accord
    # support, or an exact material); such rows never get a screening default.
    serves_requested_facet: bool = False
    # A generic bridge, volume, layer or accent slot the composer adds around
    # the named notes; it may never carry more active volume than the lead.
    generic_slot: bool = False


@dataclass(frozen=True, slots=True)
class ConceptSpec:
    concept_id: str
    triggers: tuple[str, ...]
    roles: tuple[RoleSpec, ...]
    core_count: int
    complex_count: int
    construction_note: str


@dataclass(frozen=True, slots=True)
class Candidate:
    stock: InventoryMaterial
    profile: MaterialProfile
    profile_source: str
    explicit: bool
    legacy_text_only: bool
    solid: bool


@dataclass(frozen=True, slots=True)
class Choice:
    role: RoleSpec
    candidate: Candidate
    score: float
    alternatives: tuple[str, ...]


def _r(
    role_id: str,
    label: str,
    note: str,
    function: str,
    share: float,
    *preferred: str,
    weights: tuple[tuple[str, float], ...] = (),
    required: bool = False,
    cap: float | None = None,
) -> RoleSpec:
    return RoleSpec(
        role_id=role_id,
        label=label,
        note=note,
        function=function,
        share=share,
        preferred_materials=tuple(preferred),
        descriptor_weights=weights,
        exact_preference_required=required,
        max_raw_share=cap,
        # A slot that requires its exact material is part of the capsule's
        # identity, not a generic slot, so the named lead never trims it.
        generic_slot=function in {"bridge", "volume"} and not required,
    )


# These are architecture capsules, not proprietary formulas.  Ordered
# preferences express distinct functions and allow a current-inventory
# alternative; the selected material still has to pass every hard constraint.
_CONCEPTS: tuple[ConceptSpec, ...] = (
    ConceptSpec(
        "bitter_grapefruit_tea",
        ("black tea", "tea cologne", "grapefruit and tea", "grapefruit, dry black-tea"),
        (
            _r("grapefruit_peel", "Bitter grapefruit peel", "top", "character", .17, "grapefruit fcf oil sicilian", required=True),
            _r("grapefruit_pith", "Dry grapefruit pith", "top", "modifier", .08, "methyl pamplemousse", required=True),
            _r("tea_leaf", "Tannic leaf illusion", "heart", "character", .14, "violet leaf absolute", "tobacco absolute"),
            _r(
                "tea_air",
                "Tea floral air",
                "heart",
                "bridge",
                .08,
                "cis jasmone",
                "jasmine sambac absolute",
                "jasmine absolute",
                cap=.08,
            ),
            _r("dry_cedar", "Transparent dry cedar", "base", "structure", .27, "cedarwood virginia", "azarbre", "cedramber"),
            _r("moss_tail", "Tailored moss tail", "base", "fixative", .08, "evernyl 10", "oakmoss absolute"),
            _r("tannin_shadow", "Leaf tannin shadow", "heart", "modifier", .035, "beta ionone", "alpha ionone"),
            _r("peel_bridge", "Peel-to-leaf bridge", "top", "bridge", .055, "petitgrain", "coriander essential oil"),
            _r("root_dryness", "Root dryness", "base", "modifier", .045, "vetiveryl acetate", "vetiver eo"),
            _r("quiet_diffusion", "Quiet diffusion", "heart", "volume", .21, "hedione", "iso e super"),
        ),
        6,
        10,
        "A bitter peel is bridged into a tannic floral-leaf illusion, then resolved through transparent cedar and moss.",
    ),
    ConceptSpec(
        "dry_lavender_fougere",
        ("lavender fougere", "lavender fougère", "contemporary fougere", "dry lavender"),
        (
            _r("lavender_core", "Floral-herbal lavender core", "heart", "character", .22, "lavender eo bontaux", "lavender 40 42", required=True),
            _r("aromatic_edge", "Dry aromatic edge", "top", "character", .08, "rosemary eo", "clary sage eo", required=True),
            _r("moss_hinge", "Dry moss hinge", "base", "structure", .09, "evernyl 10", "oakmoss absolute", required=True),
            _r("coumarin_hinge", "Restrained coumarin hinge", "base", "bridge", .07, "coumarin 10", required=True),
            _r("vetiver_root", "Rooty drydown", "base", "character", .22, "vetiver eo haiti", "vetiveryl acetate", required=True),
            _r(
                "architectural_wood",
                "Open architectural wood",
                "base",
                "volume",
                .22,
                "cedarwood virginia",
                "azarbre",
                "iso e super",
                cap=.25,
            ),
            _r("second_lavender", "Camphoraceous lavender register", "top", "contrast", .055, "spike lavender eo"),
            _r("culinary_herb", "Culinary herb register", "top", "modifier", .035, "basil eo", "cardamom eo", "coriander essential oil"),
            _r("green_collar", "Open green collar", "top", "bridge", .035, "petitgrain", "beta pinene", "juniper berry eo"),
            _r("geranium_link", "Lavender-moss link", "heart", "bridge", .08, "geraniol", "citronellol", "phenethyl alcohol"),
            _r("dry_amber_trace", "Dry mineral amber trace", "base", "modifier", .04, "ambrox super crystals", "ambrox super"),
            _r("root_detail", "Root detail", "base", "modifier", .035, "carrot seed eo", "vetikon"),
        ),
        6,
        12,
        "Lavender and culinary herbs stay legible above a restrained coumarin-moss hinge and dry roots.",
    ),
    ConceptSpec(
        "rose_suede_chypre",
        ("rose-suede chypre", "rose suede chypre", "suede chypre", "rose, dry patchouli"),
        (
            _r("rose_outline", "Recognizable rose outline", "heart", "character", .18, "rose essential oil", "rose de mai absolute", required=True, cap=.25),
            _r("dry_patchouli", "Dry patchouli axis", "base", "structure", .15, "patchouli eo", required=True, cap=.15),
            _r("moss_axis", "Moss axis", "base", "structure", .12, "evernyl 10", "oakmoss absolute", required=True),
            _r("pale_suede", "Pale suede plane", "base", "character", .11, "suederal 10", "isobutyl quinoline", required=True, cap=.20),
            _r("pepper_lift", "Peppered opening", "top", "contrast", .045, "pink pepper eo", "black pepper eo", cap=.12),
            _r("dry_wood", "Tailored dry wood", "base", "volume", .15, "vetiveryl acetate", "cedarwood virginia", "azarbre", cap=.18),
            _r("rose_body", "Molecular rose body", "heart", "volume", .14, "phenethyl alcohol", "pedmc", cap=.20),
            _r("metallic_rose", "Metallic rose edge", "heart", "modifier", .025, "rose oxide 1", "damascone beta 10"),
            _r("chypre_resin", "Unsweet resin seam", "base", "bridge", .055, "labdanum resinoid", "olibanum resinoid"),
            _r("root_bridge", "Rose-to-moss root bridge", "heart", "bridge", .06, "carrot seed eo", "beta ionone"),
            _r("clean_leather", "Clean leather contour", "base", "modifier", .04, "castoreum synthetic 10", "costus olifac 10"),
        ),
        6,
        11,
        "Rose is held against patchouli and moss by a pale-suede plane rather than romantic sweetness.",
    ),
    ConceptSpec(
        "green_fig_cardamom",
        (
            "green fig",
            "fig-grove",
            "fig perfume",
            "fig leaf",
            "crushed fig leaf",
            "cardamom-milky fig",
            "milky cardamom fig",
        ),
        (
            _r(
                "crushed_leaf",
                "Crushed fig leaf",
                "top",
                "character",
                .04,
                "cis 3 hexenol 1",
                "leafovert",
                required=True,
                cap=.12,
            ),
            _r(
                "fig_flesh",
                "Dry waxy fig flesh",
                "heart",
                "volume",
                .22,
                "dihydrojasmone",
                "florhydral",
                "cyclamen aldehyde",
                cap=.28,
            ),
            _r(
                "green_cardamom",
                "Green cardamom",
                "top",
                "contrast",
                .03,
                "cardamom eo",
                required=True,
                cap=.03,
            ),
            _r(
                "creamy_sandalwood",
                "Creamy sandalwood body",
                "base",
                "volume",
                .25,
                "ebanol",
                "sandalore",
                "bacdanol",
                "sandalwood base 3x",
                "sandalwood eo",
                required=True,
                cap=.25,
            ),
            _r(
                "leaf_body",
                "Bitter leafy body",
                "heart",
                "character",
                .10,
                "violet leaf absolute",
                "verdox",
                cap=.15,
            ),
            _r(
                "milky_sap",
                "Milky sap bridge",
                "heart",
                "bridge",
                .13,
                "dihydrojasmone",
                "florhydral",
                "cyclamen aldehyde",
                "benzyl salicylate",
                "methyl laitone",
                "gamma nonalactone",
                cap=.20,
            ),
            _r(
                "fig_skin",
                "Restrained fig skin",
                "heart",
                "modifier",
                .035,
                "gamma undecalactone",
                "delta decalactone",
                "beta ionone",
                cap=.01,
            ),
            _r("soft_diffusion", "Soft diffusion", "heart", "volume", .16, "hedione", "iso e super"),
            _r("bark", "Dry bark", "base", "structure", .13, "cedarwood virginia", "guaiacwood eo"),
            _r("green_air", "Green air", "top", "bridge", .07, "undecavertol 1", "cyclamen aldehyde"),
            _r("root_shadow", "Root shadow", "base", "modifier", .045, "vetiveryl acetate", "carrot seed eo"),
        ),
        6,
        11,
        "A crushed-leaf opening moves through cardamom and a restrained milky-sap accord into creamy dry wood.",
    ),
    ConceptSpec(
        "green_tuberose",
        ("tuberose", "white floral"),
        (
            _r(
                "tuberose_outline",
                "Tuberose outline",
                "heart",
                "character",
                .22,
                "tuberose base",
                "tuberlia base",
                "tuberose absolute 10",
                required=True,
            ),
            _r("natural_tuberose", "Natural floral detail", "heart", "character", .09, "tuberose absolute 10"),
            _r("green_stem", "Green stem", "top", "contrast", .08, "cis 3 hexenol 1", "undecavertol 1", "triplal", required=True, cap=.16),
            _r("jasmine_air", "Jasmine air", "heart", "bridge", .22, "hedione hc", "hedione", "jasmine sambac absolute"),
            _r("dry_skin", "Quiet dry skin", "base", "structure", .20, "ambrettolide 10", "sandalore", "ethylene brassylate"),
            _r("petal_lift", "Petal lift", "top", "modifier", .045, "linalool", "ethyl linalool"),
            _r("muguet_space", "Muguet space", "heart", "bridge", .09, "mayol", "florhydral", "cyclamen aldehyde"),
            _r("floral_shadow", "Natural floral shadow", "heart", "modifier", .025, "cis jasmone", "jasmine absolute"),
            _r("pale_wood", "Pale wood footing", "base", "volume", .12, "sandalore", "ebanol", "cedarwood virginia", "sandalwood base 3x"),
            # Explicit multi-form briefs can still bind this role through the
            # full role list, but ordinary minimal/expanded tuberose designs do
            # not receive a third opaque tuberose source automatically.
            _r("tuberose_volume", "Tuberose volume layer", "heart", "volume", .16, "tuberose absolute volume", "tuberose eo volume"),
        ),
        6,
        9,
        "A green-stem contrast outlines tuberose while jasmine/muguet air prevents a dense tropical bouquet.",
    ),
    ConceptSpec(
        "iris_incense_cathedral",
        ("iris-incense", "iris incense", "iris cathedral", "cool iris"),
        (
            _r("iris_root", "Cool iris root", "heart", "character", .12, "alpha irone 10", "orris liquid", required=True),
            _r("violet_plane", "Violet mineral plane", "heart", "character", .10, "beta ionone", "alpha ionone"),
            _r("pale_incense", "Pale frankincense", "heart", "character", .12, "olibanum resinoid", "myrrh eo", required=True),
            _r("old_cedar", "Old timber", "base", "structure", .27, "cedarwood virginia", "cedarwood himalayan", required=True),
            _r("candle_smoke", "Distant candle smoke", "base", "contrast", .025, "guaiacol 10", "cade oil rectified 1"),
            _r("empty_air", "Empty-air plane", "heart", "volume", .26, "hedione", "iso e super"),
            _r("root_detail", "Carrot-root detail", "heart", "modifier", .035, "carrot seed eo", "irotyl"),
            _r("stone", "Cold stone", "heart", "contrast", .065, "helional 10", "adoxal 10"),
            _r("resin_seam", "Resin seam", "base", "bridge", .055, "opoponax resinoid", "labdanum resinoid"),
            _r("dry_floor", "Dry wooden floor", "base", "volume", .11, "vetiveryl acetate", "azarbre"),
            _r("violet_air", "Violet air", "top", "bridge", .045, "violet leaf absolute", "dihydro beta ionone"),
        ),
        6,
        11,
        "Cool iris, pale resin, old timber, a trace of wick smoke, and empty air remain separate spatial planes.",
    ),
    ConceptSpec(
        "dry_coffee_cocoa",
        ("coffee", "cocoa", "roasted bean"),
        (
            _r("roasted_bean", "Roasted coffee bean", "top", "character", .11, "coffee absolute grasse", required=True),
            _r("bitter_cocoa", "Bitter cocoa husk", "heart", "character", .09, "cocoa absolute", "cocoa co2 extract", required=True),
            _r(
                "roast_accent",
                "Dry roast accent",
                "top",
                "modifier",
                .015,
                "guaiacol 10",
                "black pepper eo",
                "2 acetyl pyrazine 1",
                "2 acetyl pyrazine",
            ),
            _r("charred_wood", "Charred dry wood", "base", "structure", .25, "guaiacwood eo", "cedarwood virginia", required=True),
            _r("dark_root", "Dark root", "base", "character", .17, "patchouli eo", "vetiver eo haiti"),
            _r("cool_air", "Cool atmospheric air", "heart", "bridge", .22, "iso e super", "hedione"),
            _r("ember", "Wood ember trace", "base", "contrast", .02, "cade oil rectified 1", "guaiacol 10"),
            _r("dust", "Dry dust texture", "heart", "modifier", .055, "orris liquid", "beta ionone"),
            _r("quiet_skin", "Quiet skin finish", "base", "fixative", .10, "ambrettolide 10", "ethylene brassylate"),
            _r("bitter_spice", "Bitter spice contour", "top", "contrast", .035, "black pepper eo", "cardamom eo"),
        ),
        6,
        10,
        "Coffee and cocoa are framed as roast, husk, dust, and charred wood rather than dessert.",
    ),
    ConceptSpec(
        "mineral_coast",
        ("mineral coastal", "salt air", "wet stone", "mineral fresh", "storm-air", "mineral, bitter-citrus"),
        (
            _r("bitter_peel", "Bitter citrus peel", "top", "character", .12, "grapefruit fcf oil sicilian", "methyl pamplemousse", required=True),
            _r("cold_wind", "Cold wind", "top", "volume", .18, "helional", "floralozone 10", "dihydromyrcenol", cap=.22),
            _r("wet_stone", "Wet mineral stone", "heart", "character", .08, "adoxal 10", "helional 10", required=True),
            _r(
                "salt_air",
                "Saline air",
                "heart",
                "bridge",
                .11,
                "undecavertol 1",
                "cyclamen aldehyde",
                "floralozone 10",
                "calone 1",
                cap=.15,
            ),
            _r("driftwood", "Cold driftwood", "base", "structure", .28, "vetiveryl acetate", "cedarwood virginia", "cedramber", required=True),
            _r("mineral_trail", "Transparent mineral trail", "base", "volume", .21, "ambrox super", "iso e super", "sandalore"),
            _r(
                "storm_ozone",
                "Storm-air ozone",
                "top",
                "contrast",
                .035,
                "floralozone 10",
                "triplal",
                "adoxal 10",
            ),
            _r("saline_skin", "Saline skin", "base", "modifier", .07, "ambrettolide 10", "ethylene brassylate"),
            _r("shore_herb", "Shore herb", "heart", "contrast", .04, "clary sage eo", "juniper berry eo"),
            _r("stone_shadow", "Stone shadow", "base", "modifier", .04, "cashmeran 20", "vetikon"),
        ),
        6,
        10,
        "Bitter peel and cold wind pass through wet stone and saline air into transparent driftwood.",
    ),
    ConceptSpec(
        "intimate_skin",
        ("skin scent", "skin perfume", "human skin", "warm-skin", "warm skin"),
        (
            _r(
                "warm_skin",
                "Warm skin oil",
                "heart",
                "character",
                .08,
                "ambrettolide 10",
                "romandolide",
                "ethylene brassylate",
                "sandalore",
                "orris liquid",
                required=True,
                cap=.12,
            ),
            _r("clean_paper", "Clean paper", "heart", "texture", .12, "orris liquid", "beta ionone", cap=.15),
            _r("pale_wood", "Pale wood", "base", "structure", .12, "sandalore", "sandalwood eo", "cedarwood virginia", cap=.15),
            _r("quiet_diffusion", "Close diffusion", "heart", "volume", .15, "phenethyl alcohol", "hedione", "iso e super", cap=.20),
            _r("book_leather", "Old-book leather trace", "base", "contrast", .02, "suederal 10", "isobutyl quinoline 10", cap=.025),
            _r(
                "quiet_carrier",
                "Quiet carrier and fixation",
                "base",
                "fixative",
                .51,
                "triethyl citrate",
                "dipropylene glycol",
                "benzyl benzoate",
                "benzyl salicylate",
                cap=.60,
            ),
            _r("linen_air", "Soft linen air", "top", "bridge", .06, "ethyl linalool", "linalool oxide"),
            _r("warm_wood", "Warm pale wood", "base", "modifier", .10, "cashmeran 20", "azarbre"),
        ),
        6,
        8,
        "Warm skin, pale wood, and close diffusion are carried quietly; paper, leather, or musk facets appear only when the brief or selected rows support them.",
    ),
    ConceptSpec(
        "monsoon_market",
        ("monsoon", "after rain", "wet pavement", "night-market", "night market"),
        (
            _r("rain_pavement", "Wet pavement", "top", "character", .012, "geosmin 0 1", "adoxal 10", "violet leaf absolute", "vetiveryl acetate", "patchouli eo", required=True),
            _r("storm_air", "Storm air", "top", "volume", .09, "helional 10", "floralozone 10", "triplal"),
            _r("citrus_peel", "Crushed citrus peel", "top", "character", .08, "lime eo", "grapefruit fcf oil sicilian", "petitgrain"),
            _r("thai_herbs", "Crushed aromatic herbs", "top", "character", .065, "basil eo", "coriander essential oil", "lemongrass eo", required=True),
            _r("humid_jasmine", "Humid jasmine", "heart", "character", .12, "jasmine sambac absolute", "jasmine absolute", required=True),
            _r("jasmine_tea", "Jasmine tea air", "heart", "bridge", .13, "cis jasmone", "hedione"),
            _r("incense_smoke", "Market incense", "base", "character", .075, "olibanum resinoid", "elemi eo", required=True),
            _r("warm_wood", "Rain-warmed wood", "base", "structure", .21, "cedarwood virginia", "guaiacwood eo", required=True),
            _r("warm_skin", "Warm human trace", "base", "fixative", .12, "ambrettolide 10", "ethylene brassylate"),
            _r("tea_leaf", "Dark tea leaf", "heart", "modifier", .075, "violet leaf absolute", "tobacco absolute"),
            _r("wet_concrete", "Wet concrete mineral", "heart", "contrast", .045, "adoxal 10", "helional", "vetiveryl acetate", "patchouli eo", "undecavertol 1"),
            _r("flower_stall", "Flower-stall detail", "heart", "character", .08, "tuberose absolute 10", "rose de mai absolute"),
            _r("spice_stall", "Spice-stall detail", "heart", "contrast", .035, "cardamom eo", "black pepper eo"),
            _r("smoke_trace", "Distant smoke", "base", "modifier", .012, "guaiacol 10", "cade oil rectified 1"),
            _r("humid_green", "Humid green transition", "top", "bridge", .035, "cis 3 hexenol 1", "undecavertol 1"),
        ),
        10,
        15,
        "Rain, herbs, flowers, tea, incense, wood, and warm skin are represented as a sequence of nonredundant scene planes.",
    ),
)

_GENERIC_ROLES: tuple[RoleSpec, ...] = (
    _r("opening_signature", "Opening signature", "top", "character", .12, "bergamot", "grapefruit", weights=(("freshness", 1.0),)),
    _r("heart_signature", "Heart signature", "heart", "character", .18, "hedione", "phenethyl alcohol", weights=(("floral", 1.0),)),
    _r("base_signature", "Base signature", "base", "structure", .22, "cedarwood", "sandalore", weights=(("woody", 1.0),)),
    _r("opening_bridge", "Opening bridge", "top", "bridge", .08, "petitgrain", "linalool", weights=(("freshness", .7), ("transparency", .5))),
    _r("heart_bridge", "Heart bridge", "heart", "bridge", .16, "hedione", "cis jasmone", weights=(("radiance", 1.0),)),
    _r("base_body", "Base body", "base", "volume", .18, "iso e super", "sandalwood base", weights=(("woody", .7),)),
    _r("character_accent", "Character accent", "heart", "modifier", .06, "cardamom", "beta ionone"),
    _r("drydown_link", "Drydown link", "base", "bridge", .10, "vetiveryl acetate", "azarbre"),
)


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(value).casefold()).strip()


def _decimal_text(value: object) -> str:
    parsed = Decimal(str(value))
    rendered = format(parsed, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _positive_decimal(value: object, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"{field} must be a finite positive decimal") from error
    if not parsed.is_finite() or parsed <= 0:
        raise ValueError(f"{field} must be a finite positive decimal")
    return parsed


def _is_solid(stock: InventoryMaterial) -> bool:
    probe = _key(f"{stock.physical_form} {stock.raw_name} {stock.name} {stock.identity_name}")
    return any(marker in probe for marker in _SOLID_MARKERS)


def _candidate_probe(candidate: Candidate) -> str:
    stock = candidate.stock
    return _key(
        f"{stock.name} {stock.identity_name} {stock.raw_name} {stock.category} "
        f"{stock.physical_form} {stock.fraction_basis} {stock.carrier}"
    )


def _candidate_identity_probe(candidate: Candidate) -> str:
    """Return exact identity/stock wording without category or prose comments."""

    stock = candidate.stock
    raw_label = re.sub(r"\s*#.*$", "", stock.raw_name).strip()
    return _key(
        f"{stock.name} {stock.identity_name} {raw_label} {stock.physical_form} "
        f"{stock.fraction_basis} {stock.carrier}"
    )


def _proxy_profile(stock: InventoryMaterial) -> MaterialProfile:
    category = _key(stock.category)
    character = {
        "warmth": 0.0,
        "sweetness": 0.0,
        "freshness": 0.0,
        "powdery": 0.0,
        "green": 0.0,
        "animalic": 0.0,
        "radiance": 0.0,
        "woody": 0.0,
        "spicy": 0.0,
        "floral": 0.0,
        "smoky": 0.0,
        "creamy": 0.0,
        "transparency": 0.0,
    }
    note, role, texture = "heart", "modifier", "category proxy"
    if any(word in category for word in ("citrus", "top", "aromatic")):
        character.update(freshness=8.0, green=3.0, transparency=4.0)
        note, role, texture = "top", "character", "lift"
    elif any(word in category for word in ("green", "marine", "fresh")):
        character.update(freshness=6.0, green=6.0, transparency=5.0)
        note, role, texture = "top", "character", "air"
    elif any(word in category for word in ("floral", "rose", "orris", "violet")):
        character.update(floral=7.0, radiance=4.0, powdery=2.0)
        note, role, texture = "heart", "character", "floral body"
    elif any(word in category for word in ("wood", "amber", "moss")):
        character.update(woody=8.0, warmth=4.0, transparency=2.0)
        note, role, texture = "base", "character", "structure"
    elif any(word in category for word in ("resin", "incense", "smok", "leather")):
        character.update(smoky=6.0, woody=5.0, warmth=4.0)
        note, role, texture = "base", "character", "shadow"
    elif "musk" in category:
        character.update(creamy=5.0, warmth=3.0, transparency=5.0)
        note, role, texture = "base", "fixative", "skin"
    elif any(word in category for word in ("sweet", "gourmand", "lactone")):
        character.update(sweetness=7.0, creamy=5.0, warmth=4.0)
        note, role, texture = "base", "character", "sweet body"
    elif any(word in category for word in ("spice", "coffee", "roast")):
        character.update(spicy=6.0, warmth=4.0, smoky=2.0)
        note, role, texture = "heart", "character", "accent"
    return MaterialProfile(
        name=stock.identity_name or stock.name,
        character=character,
        note=note,
        role=role,
        texture=texture,
        dilution=stock.dilution,
        evidence={"character": {"status": "HEURISTIC_INVENTORY_CATEGORY_PROXY"}},
    )


def _candidate_matches_text(candidate: Candidate, value: str) -> bool:
    wanted = _key(value)
    probe = _candidate_identity_probe(candidate)
    if not wanted:
        return False
    stock = candidate.stock
    wanted_alias = normalize_name(value)
    if wanted_alias in {
        normalize_name(stock.identity_name),
        normalize_name(stock.name),
        normalize_name(re.sub(r"\s*#.*$", "", stock.raw_name).strip()),
    }:
        return True
    if wanted in probe or probe in wanted:
        return True
    ignored = {"in", "of", "the", "stock", "owned", "form", "w", "v", "as", "supplied"}
    wanted_tokens = {token for token in wanted.split() if token not in ignored}
    probe_tokens = set(probe.split())
    return bool(wanted_tokens) and wanted_tokens <= probe_tokens


_LABEL_STRENGTH_RE = re.compile(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*%")


def _label_names_several_strengths(stock: InventoryMaterial) -> bool:
    """True when a stock label names more than one bottle strength.

    Such a label (e.g. "Birch Tar 1% and Birch Tar 10%") cannot say which
    bottle a row means, so binding it risks a tenfold dosing error.
    """

    label = re.sub(r"\s*#.*$", "", stock.raw_name or stock.name)  # drop free-text comments
    label = re.sub(r"\[[^\]]*\]", " ", label)  # drop the parser's "[0.1]" fraction tag
    strengths = {
        float(value.replace(",", ".")) for value in _LABEL_STRENGTH_RE.findall(label)
    }
    if re.search(r"\bneat\b", label, re.IGNORECASE):
        strengths.add(100.0)
    return len(strengths) > 1


def _unconfirmed_two_strength_label(
    stock: InventoryMaterial, live_identities: frozenset[str]
) -> bool:
    """True for a two-strength label that inventory.txt does not back up.

    The personal projection already drops a governed stock whose strength
    contradicts inventory.txt's own line for that material, so a two-strength
    stock that survives beside an inventory.txt line is a confirmed bottle
    (Cashmeran neat and 20%). With no inventory.txt line for the material the
    label cannot say which bottle a row means (Birch Tar 1% and 10%, while
    inventory.txt lists Birch Tar Rectified 10% in DPG), so the composer
    refuses it and uses inventory.txt's own stock instead.
    """

    return _label_names_several_strengths(stock) and (
        personal_inventory_identity_key(stock) not in live_identities
    )


def _load_candidates(explicit_materials: Sequence[str]) -> tuple[list[Candidate], Any, tuple[str, ...]]:
    inventory = materialize_personal_inventory()
    inventory_text_sha = _inventory_text_sha256()
    cache_key = (inventory.effective_inventory_sha256, inventory_text_sha)
    cached = _CANDIDATE_BASE_CACHE.get(cache_key)
    if cached is not None:
        base_candidates, cached_known = cached
        return (
            [
                replace(
                    candidate,
                    explicit=any(
                        _candidate_matches_text(candidate, value)
                        for value in explicit_materials
                    ),
                )
                for candidate in base_candidates
            ],
            inventory,
            cached_known,
        )

    live_identities = frozenset(
        personal_inventory_identity_key(stock)
        for stock in parse_inventory(unique=False, include_unavailable=False)
        if stock.status.casefold() == "owned"
    )
    candidates: list[Candidate] = []
    for stock in inventory.stocks:
        if (
            stock.status.casefold() != "owned"
            or stock.dilution <= 0
            or is_user_compounding_held(stock)
            or _unconfirmed_two_strength_label(stock, live_identities)
        ):
            continue
        identity_key = _key(stock.identity_name or stock.name)
        functional_carrier = identity_key in _DESIGN_FUNCTIONAL_CARRIERS
        if (
            any(token in stock.category.casefold() for token in _EXCLUDED_CATEGORIES)
            and not functional_carrier
        ):
            continue
        profile = get_profile(stock.identity_name) or get_profile(stock.name)
        profile_source = "DECLARED_MATERIAL_PROFILE"
        if profile is None:
            profile = _proxy_profile(stock)
            profile_source = "HEURISTIC_CATEGORY_PROXY"
        if profile.role.casefold() in {"solvent", "stabilizer"} and not functional_carrier:
            continue
        candidate = Candidate(
            stock=stock,
            profile=profile,
            profile_source=profile_source,
            explicit=False,
            legacy_text_only=stock.authority in {
                LIVE_TEXT_AUTHORITY,
                DESIGN_ONLY_AUTHORITY,
            },
            solid=_is_solid(stock),
        )
        candidates.append(candidate)

    known = {
        value
        for stock in _cached_legacy_inventory(inventory_text_sha, True)
        if not any(token in stock.category.casefold() for token in _EXCLUDED_CATEGORIES)
        for value in (
            stock.name,
            stock.identity_name,
            normalize_name(stock.name),
            normalize_name(stock.identity_name),
        )
        if _clean(value)
    }
    for stock in inventory.stocks:
        if any(token in stock.category.casefold() for token in _EXCLUDED_CATEGORIES):
            continue
        known.update(
            value
            for value in (
                stock.name,
                stock.identity_name,
                normalize_name(stock.name),
                normalize_name(stock.identity_name),
            )
            if _clean(value)
        )
    known_tuple = tuple(sorted(known, key=lambda value: (-len(value), value.casefold())))
    if len(_CANDIDATE_BASE_CACHE) >= 8:
        _CANDIDATE_BASE_CACHE.pop(next(iter(_CANDIDATE_BASE_CACHE)))
    _CANDIDATE_BASE_CACHE[cache_key] = (tuple(candidates), known_tuple)
    return (
        [
            replace(
                candidate,
                explicit=any(
                    _candidate_matches_text(candidate, value)
                    for value in explicit_materials
                ),
            )
            for candidate in candidates
        ],
        inventory,
        known_tuple,
    )


def _avoid_candidate(candidate: Candidate, avoid: Sequence[str]) -> bool:
    probe = _candidate_probe(candidate)
    identity_probe = _candidate_identity_probe(candidate)
    for raw in avoid:
        item = _key(raw)
        if not item:
            continue
        if item == identity_probe or item in identity_probe or identity_probe in item:
            return True
        if item in {
            "citrus essential oil",
            "any citrus essential oil",
            "citrus oil",
            "any citrus oil",
        }:
            category = _key(candidate.stock.category)
            natural_citrus = re.search(
                r"(?:^| )(?:cedrat|bergamot|grapefruit|mandarin|lime|lemon|"
                r"orange peel|neroli|petitgrain|yuzu)(?: |$)",
                probe,
            )
            if "citrus" in category and (
                re.search(r"(?:^| )(?:eo|oil|essential oil)(?: |$)", probe)
                or natural_citrus
            ):
                return True
        if item in {"vanilla", "any vanilla", "vanilla material", "any vanilla material"}:
            if any(
                marker in probe
                for marker in ("vanilla", "vanillin", "ethyl vanillin", "isobutavan")
            ):
                return True
        if item in {"suede", "any suede", "suede material", "any suede material"}:
            if "suede" in probe:
                return True
        if "ambrox" in item and "ambrox" in probe:
            if "solution" in item and candidate.solid:
                continue
            if "crystal" in item and not candidate.solid:
                continue
            return True
        # A named anchor can coexist with a request to control one of its
        # facets (for example dry coffee while avoiding sweet gourmand style,
        # or patchouli without patchouli domination).  Exact identity/form
        # bans above still win.
        if candidate.explicit:
            continue
        if (
            item in {"musk", "musk material", "all musk", "all musk material"}
            and _candidate_group(candidate) == "musk"
        ):
            return True
        if (
            "material" in item
            and any(
                word in item
                for word in ("gourmand", "sugary", "sweet smelling", "sweet")
            )
        ):
            if any(word in probe for word in ("vanill", "maltol", "lactone", "tonka", "benzoin", "balsam", "maple", "gourmand")):
                return True
        if "lactone" in item and "lactone" in probe:
            return True
        if "fruity ester" in item and any(word in probe for word in ("acetate", "propionate", "butyrate", "fruit")):
            return True
        if "laundry musk" in item and any(word in probe for word in ("galaxolide", "habanolide", "laundry")):
            return True
        if (
            "coconut" in item
            and "lactone" in item
            and any(word in probe for word in ("nonalactone", "methyl laitone", "lactone", "coconut"))
        ):
            return True
        if "coconut" in item and any(
            word in probe for word in ("nonalactone", "aldehyde c 18", "coconut")
        ):
            return True
        if "banana" in item and any(word in probe for word in ("amyl acetate", "isoamyl", "banana")):
            return True
        if "shaving foam" in item and any(word in probe for word in ("dihydromyrcenol", "galaxolide")):
            return True
        if any(
            phrase in item
            for phrase in ("blue shower gel", "generic blue", "wet laundry")
        ) and any(
            word in probe
            for word in ("dihydromyrcenol", "galaxolide", "calone")
        ):
            return True
        if "melon" in item and "calone" in probe:
            return True
    return False


def _concept(text: str) -> ConceptSpec | None:
    normalized = _key(text)
    scored: list[tuple[int, int, ConceptSpec]] = []
    for concept in _CONCEPTS:
        hits = [trigger for trigger in concept.triggers if _key(trigger) in normalized]
        if hits:
            scored.append((len(hits), max(len(trigger) for trigger in hits), concept))
    if not scored:
        return None
    scored.sort(key=lambda row: (-row[0], -row[1], row[2].concept_id))
    return scored[0][2]


_COUNT_WORDS = {
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def _explicit_count(text: str) -> int | None:
    match = re.search(r"\b(?P<count>\d+|six|seven|eight|nine|ten|eleven|twelve)[ -]material", text, re.I)
    if not match:
        match = re.search(r"\bin\s+(?P<count>\d+|six|seven|eight|nine|ten|eleven|twelve)\s+materials\b", text, re.I)
    if not match:
        return None
    token = match.group("count").casefold()
    return int(token) if token.isdigit() else _COUNT_WORDS[token]


def _role_count(text: str, concept: ConceptSpec | None, maximum: int, explicit_anchors: int) -> int:
    exact = _explicit_count(text)
    if exact is not None:
        return min(maximum, max(exact, explicit_anchors))
    if concept is None:
        base = len(_GENERIC_ROLES)
    elif re.search(
        r"\b(?:complex|layered|detailed|architectural|high-definition|nuanced|sequential|"
        r"every\s+necessary\s+scene|transitions?|distinct\s+non-food\s+facet)\b",
        text,
        re.I,
    ) or re.search(
        r"\b(?:stages?|facets?|planes?)\b.{0,35}\b(?:distinct|separate|legible|readable)\b|"
        r"\b(?:open(?:ing|s)?|5|five)[- ]*(?:minutes?)?\b.{0,140}"
        r"\b(?:30|thirty|2|two|4|four)[- ]*(?:minutes?|hours?)\b|"
        r"\b(?:30|thirty)[- ]*(?:minutes?)\b.{0,140}"
        r"\b(?:4|four)[- ]*(?:hours?|drydown)\b|"
        r"\b(?:at|after)\s+(?:5|five|30|thirty|2|two|4|four)\s+"
        r"(?:minutes?|hours?)\b|"
        r"\b(?:global(?:ly)?|mass[- ]market|commercial|prestige|crowd[- ]pleasing)\b.{0,70}"
        r"\b(?:wear|wearable|wearability|appeal|comparison|perfumes?)\b|"
        r"\b(?:wear|wearable|wearability)\b.{0,70}\b(?:global|mass[- ]market|commercial|prestige|perfumes?)\b|"
        r"\bup\s+to\s+(?:\d+|[a-z-]+)\s+materials?\b",
        text,
        re.I,
    ) or (
        concept is not None
        and concept.concept_id == "intimate_skin"
        and re.search(r"\b(?:clean paper|old book|book leather|textural)\b", text, re.I)
    ):
        base = concept.complex_count
    else:
        base = concept.core_count
    if re.search(r"\bminimal\b", text, re.I):
        base = min(base, 6)
    return min(maximum, max(6, explicit_anchors, base))


_WEARABILITY_RE = re.compile(
    r"\b(?:wearable|wearability|easier\s+to\s+wear|mass[- ]?market|"
    r"crowd[- ]?pleasing|successful\s+(?:prestige\s+)?perfumes?|"
    r"global\s+(?:market|appeal|comparison))\b",
    re.I,
)


def _request_specific_roles(
    text: str,
    concept: ConceptSpec | None,
    *,
    evaluation_windows: Sequence[dict[str, Any]],
) -> tuple[list[RoleSpec], list[RoleSpec], list[str]]:
    """Return core roles plus bounded adaptations demanded by the brief.

    This is a visible design pass, not a hidden hedonic objective.  It prevents
    the same static capsule from answering materially different minimal,
    temporal, and wearability requests.
    """

    if concept is None:
        return list(_GENERIC_ROLES), [], []

    core = list(concept.roles)
    variants: list[RoleSpec] = []
    repairs: list[str] = []
    normalized = _key(text)

    if concept.concept_id == "intimate_skin" and not any(
        token in normalized for token in ("paper", "book", "leather", "suede")
    ):
        core = [
            role
            for role in core
            if role.role_id not in {"clean_paper", "book_leather"}
        ]
        repairs.append("OMITTED_UNREQUESTED_PAPER_AND_LEATHER_SCENE_ROLES")

    if concept.concept_id == "intimate_skin" and any(
        token in normalized
        for token in ("detergent", "laundry", "shampoo", "fabric softener")
    ):
        core = [role for role in core if role.role_id != "linen_air"]
        repairs.append("OMITTED_LINEN_AIR_WHEN_CLEANING_PRODUCT_DIRECTION_WAS_REJECTED")

    if _WEARABILITY_RE.search(text):
        if concept.concept_id == "rose_suede_chypre":
            variants.extend(
                (
                    _r(
                        "wearable_entry",
                        "Dry bright entry for easier wear",
                        "top",
                        "bridge",
                        .06,
                        "bergamot fcf oil sicilian",
                        "petitgrain",
                        cap=.10,
                    ),
                    _r(
                        "wearable_transition",
                        "Clear rose-to-suede transition",
                        "heart",
                        "bridge",
                        .10,
                        "hedione hc",
                        "hedione",
                        "hexyl salicylate",
                        cap=.16,
                    ),
                )
            )
        elif concept.concept_id == "iris_incense_cathedral":
            variants.extend(
                (
                    _r(
                        "wearable_entry",
                        "Dry luminous entry",
                        "top",
                        "bridge",
                        .065,
                        "bergamot fcf oil sicilian",
                        "petitgrain",
                        cap=.10,
                    ),
                    _r(
                        "soft_cathedral_exit",
                        "Quiet skin-scale exit",
                        "base",
                        "fixative",
                        .075,
                        "ambrettolide 10",
                        "ethylene brassylate",
                        cap=.12,
                    ),
                )
            )
        elif concept.concept_id == "mineral_coast":
            variants.extend(
                (
                    _r(
                        "aromatic_market_bridge",
                        "Aromatic mineral bridge",
                        "heart",
                        "bridge",
                        .065,
                        "lavender eo bontaux",
                        "geraniol",
                        "clary sage eo",
                        cap=.10,
                    ),
                    _r(
                        "pepper_lift",
                        "Dry pepper lift",
                        "top",
                        "contrast",
                        .025,
                        "black pepper eo",
                        "pink pepper eo",
                        cap=.05,
                    ),
                )
            )
        if variants:
            repairs.append("ADDED_REQUESTED_WEARABILITY_ADAPTATION_ROLES")

    window_labels = {
        str(window.get("window") or window.get("label") or "")
        for window in evaluation_windows
    }
    if concept.concept_id == "green_tuberose" and {
        "THIRTY_MINUTES",
        "FOUR_HOURS",
    } <= window_labels:
        variants.extend(
            (
                _r(
                    "green_heart_support",
                    "Green-heart continuation",
                    "heart",
                    "bridge",
                    .06,
                    "undecavertol 1",
                    "triplal",
                    cap=.10,
                ),
                _r(
                    "quiet_floral_trace",
                    "Quiet floral-trace fixation",
                    "base",
                    "fixative",
                    .08,
                    "benzyl salicylate",
                    "cedarwood virginia",
                    cap=.14,
                ),
            )
        )
        repairs.append("ADDED_SEPARATE_GREEN_HEART_AND_FLORAL_TRACE_ROLES")

    if concept.concept_id == "bitter_grapefruit_tea" and "FOUR_HOURS" in window_labels:
        variants.append(
            _r(
                "persistent_signature",
                "Persistent citrus-tea echo",
                "base",
                "bridge",
                .06,
                "lemonile",
                "methyl pamplemousse",
                "vetiveryl acetate",
                cap=.10,
            )
        )
        repairs.append("ADDED_EXPLICIT_PERSISTENT_SIGNATURE_ROLE")

    return core, variants, repairs


def _profile_axis(profile: MaterialProfile, name: str) -> float:
    try:
        value = float(profile.character.get(name, 0.0))
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, value / 10.0))


def _preference_rank(candidate: Candidate, role: RoleSpec) -> int | None:
    probe = _candidate_identity_probe(candidate)
    for index, preferred in enumerate(role.preferred_materials):
        if _key(preferred) in probe:
            return index
    return None


def _candidate_group(candidate: Candidate) -> str:
    probe = _candidate_probe(candidate)
    if "musk" in probe or any(
        marker in probe
        for marker in (
            "ambrettolide",
            "brassylate",
            "exaltolide",
            "galaxolide",
            "habanolide",
            "romandolide",
            "zenolide",
        )
    ):
        return "musk"
    if "citrus" in probe:
        return "citrus"
    return "other"


def _selection_identity(candidate: Candidate) -> str:
    # An explicitly requested product/form remains distinct; generic selection
    # aggregates duplicate stock solutions by chemical/product identity.
    probe = _candidate_probe(candidate)
    if "hedione" in probe:
        return "family:hedione"
    if "tuberlia base" in probe or "tuberose base" in probe:
        return "product:tuberose_base"
    if candidate.explicit:
        return candidate.stock.stock_id
    return _key(candidate.stock.identity_name or candidate.stock.name)


def _score_candidate(
    candidate: Candidate,
    role: RoleSpec,
    *,
    previous_stock_ids: set[str],
    selected_names: Sequence[str],
) -> float:
    score = 0.0
    rank = _preference_rank(candidate, role)
    if rank is not None:
        # Preference order is deliberate accord logic.  Secondary metadata
        # bonuses must not silently promote a lower-ranked substitute above a
        # clearly preferred material.
        # Keep adjacent preferences more than one full metadata-bonus budget
        # apart.  Otherwise an execution flag can silently make the second
        # material replace the deliberately chosen first accord voice.
        score += 20.0 - min(rank, 20) * 2.0
    note = candidate.profile.note.casefold()
    if role.note in note:
        score += 0.55
    profile_role = candidate.profile.role.casefold()
    if role.function in profile_role or any(
        token in profile_role for token in ("character", "modifier", "bridge", "volume", "fixative")
    ):
        score += 0.20
    for axis, weight in role.descriptor_weights:
        score += abs(weight) * (
            _profile_axis(candidate.profile, axis)
            if weight >= 0
            else 1.0 - _profile_axis(candidate.profile, axis)
        )
    if candidate.stock.execution_ready:
        score += 0.25
    elif effective_design_ready(candidate.stock):
        score += 0.08
    if (
        role.function in {"modifier", "contrast"}
        and 0.001 <= candidate.stock.dilution <= 0.20
    ):
        # A usable dilution is a small bench advantage, not permission to
        # outrank an execution-bound exact stock of the same identity.
        score += 0.08
    if candidate.legacy_text_only:
        score -= 0.15
    if candidate.stock.stock_id in previous_stock_ids:
        score += 0.35
    synergy_probe = _key(" ".join(candidate.profile.synergies))
    if any(_key(name) and _key(name) in synergy_probe for name in selected_names):
        score += 0.12
    if candidate.solid and role.note != "base":
        score -= 1.5
    return score


def _matched_anchor_roles(
    explicit_materials: Sequence[str],
    concept: ConceptSpec | None,
) -> list[RoleSpec | None]:
    """Assign explicit materials to distinct concept roles when possible."""

    matched_roles: list[RoleSpec | None] = []
    used_role_ids: set[str] = set()
    for material in explicit_materials:
        matches: list[tuple[int, int, RoleSpec]] = []
        for role_index, role in enumerate(concept.roles if concept else ()):
            if role.role_id in used_role_ids:
                continue
            for preference_index, preferred in enumerate(role.preferred_materials):
                if (
                    _key(material) in _key(preferred)
                    or _key(preferred) in _key(material)
                ):
                    matches.append((preference_index, role_index, role))
                    break
        matched = min(matches, default=None, key=lambda item: (item[0], item[1]))
        matched_role = matched[2] if matched is not None else None
        if matched_role is not None:
            used_role_ids.add(matched_role.role_id)
        matched_roles.append(matched_role)
    return matched_roles


def _anchor_roles(
    explicit_materials: Sequence[str],
    concept: ConceptSpec | None,
) -> list[RoleSpec]:
    roles: list[RoleSpec] = []
    matched_roles = _matched_anchor_roles(explicit_materials, concept)
    for index, (material, matched_role) in enumerate(
        zip(explicit_materials, matched_roles, strict=True)
    ):
        roles.append(replace(
            _r(
                f"explicit_anchor_{index + 1}",
                (
                    f"Explicit {matched_role.label.casefold()}: {material}"
                    if matched_role
                    else f"Explicit brief anchor: {material}"
                ),
                matched_role.note if matched_role else "heart",
                matched_role.function if matched_role else "character",
                matched_role.share if matched_role else .12,
                material,
                required=True,
                cap=matched_role.max_raw_share if matched_role else None,
            ),
            # A material the brief names is a named note, never a generic slot.
            serves_requested_facet=True,
            generic_slot=False,
        ))
    return roles


def _select_choices(
    candidates: Sequence[Candidate],
    roles: Sequence[RoleSpec],
    *,
    avoid: Sequence[str],
    previous_stock_ids: set[str],
) -> tuple[tuple[Choice, ...], tuple[str, ...]]:
    choices: list[Choice] = []
    missing: list[str] = []
    used: set[str] = set()
    group_counts: dict[str, int] = {}
    for role in roles:
        ranked: list[tuple[float, Candidate]] = []
        for candidate in candidates:
            identity = _selection_identity(candidate)
            if identity in used or _avoid_candidate(candidate, avoid):
                continue
            rank = _preference_rank(candidate, role)
            if role.exact_preference_required and rank is None:
                continue
            if role.preferred_materials and rank is None and not role.descriptor_weights:
                continue
            group = _candidate_group(candidate)
            if group == "musk" and group_counts.get(group, 0) >= 1 and not candidate.explicit:
                continue
            if (
                group == "citrus"
                and group_counts.get(group, 0) >= 2
                and role.role_id != "persistent_signature"
                and not candidate.explicit
            ):
                continue
            score = _score_candidate(
                candidate,
                role,
                previous_stock_ids=previous_stock_ids,
                selected_names=[choice.candidate.stock.identity_name or choice.candidate.stock.name for choice in choices],
            )
            ranked.append((score, candidate))
        ranked.sort(
            key=lambda row: (
                -row[0],
                not row[1].stock.execution_ready,
                row[1].legacy_text_only,
                row[1].stock.identity_name.casefold(),
                row[1].stock.stock_id,
            )
        )
        if not ranked:
            if role.exact_preference_required:
                missing.append(role.label)
            continue
        score, candidate = ranked[0]
        alternatives = tuple(
            item.stock.name or item.stock.identity_name
            for _alt_score, item in ranked[1:3]
        )
        choices.append(Choice(role, candidate, score, alternatives))
        used.add(_selection_identity(candidate))
        group = _candidate_group(candidate)
        group_counts[group] = group_counts.get(group, 0) + 1
    return tuple(choices), tuple(missing)


def _quantity_for_candidate(candidate: Candidate, quantities: Sequence[dict[str, Any]]) -> tuple[Decimal, str] | None:
    for row in quantities:
        if row.get("scope") != "MATERIAL_DOSE" or not row.get("material"):
            continue
        if _candidate_matches_text(candidate, str(row["material"])):
            return Decimal(str(row["amount_decimal"])), str(row["unit"])
    return None


def _solid_default_mg(candidate: Candidate, liquid_total_ul: int) -> int | None:
    probe = _candidate_probe(candidate)
    if "ambrox" in probe:
        return max(10, int(round(liquid_total_ul * 0.03)))
    if "evernyl" in probe:
        return max(10, int(round(liquid_total_ul * 0.005)))
    return None


def _hard_cap_ul(candidate: Candidate, liquid_total_ul: int) -> int | None:
    # Dose caps are identity-specific.  Profile character and synergy words
    # must never make (for example) Pink Pepper inherit Rose Oxide's cap.
    probe = _candidate_identity_probe(candidate)
    active_cap_fraction: Decimal | None = None
    if "geosmin" in probe:
        active_cap_fraction = Decimal("0.0000005")  # 3 uL of a 0.1% stock in 6 mL
    elif "floralozone" in probe:
        active_cap_fraction = Decimal("0.002")
    elif "triplal" in probe:
        active_cap_fraction = Decimal("0.0005")
    elif "skatole" in probe:
        active_cap_fraction = Decimal("0.00005")
    elif "indole" in probe:
        active_cap_fraction = Decimal("0.0005")
    elif "birch tar" in probe or "cade oil" in probe:
        active_cap_fraction = Decimal("0.0005")
    elif "guaiacol" in probe:
        active_cap_fraction = Decimal("0.001")
    elif "2 acetyl pyrazine" in probe:
        active_cap_fraction = Decimal("0.0002")
    elif "lemonile" in probe:
        active_cap_fraction = Decimal("0.005")
    elif "rose oxide" in probe:
        active_cap_fraction = Decimal("0.001")
    elif "cis jasmone" in probe:
        active_cap_fraction = Decimal("0.03")
    elif "gamma undecalactone" in probe or "delta decalactone" in probe:
        active_cap_fraction = Decimal("0.005")
    elif "methyl laitone" in probe:
        active_cap_fraction = Decimal("0.01")
    elif "gamma nonalactone" in probe or "aldehyde c 18" in probe:
        active_cap_fraction = Decimal("0.005")
    elif "blue chamomile" in probe:
        active_cap_fraction = Decimal("0.02")
    elif "coumarin" in probe:
        active_cap_fraction = Decimal("0.005")
    elif "evernyl" in probe:
        active_cap_fraction = Decimal("0.01")
    if active_cap_fraction is None:
        return None
    return _active_fraction_cap_ul(candidate, active_cap_fraction, liquid_total_ul)


def _active_fraction_cap_ul(candidate: Candidate, active_cap_fraction: Decimal, liquid_total_ul: int) -> int:
    fraction = max(Decimal("0.000001"), Decimal(str(candidate.stock.dilution)))
    raw_fraction = active_cap_fraction / fraction
    return max(1, int((Decimal(liquid_total_ul) * raw_fraction).to_integral_value(rounding=ROUND_FLOOR)))


def _normal_use_ceiling(candidate: Candidate) -> NormalUseCeiling | None:
    # Same identity-only probe as the hard caps: profile, character and
    # synergy words never select a ceiling.
    return match_normal_use_ceiling(_candidate_identity_probe(candidate))


def _normal_use_ceiling_cap_ul(candidate: Candidate, liquid_total_ul: int) -> int | None:
    ceiling = _normal_use_ceiling(candidate)
    if ceiling is None:
        return None
    return _active_fraction_cap_ul(candidate, ceiling.max_active_fraction, liquid_total_ul)


# IFRA dose caps assume the worst case the composer's IFRA screen also uses:
# the concentrate is up to 30% of the finished perfume.  The standard design
# (6,000 uL in a 30 mL bottle) is 20%, which leaves room for the gate weighing
# w/w where the composer doses by volume.
IFRA_CAP_FINISHED_FRACTION = Decimal("0.30")


def _ifra_cap_ul(candidate: Candidate, liquid_total_ul: int) -> int | None:
    """The most stock volume that keeps this stock alone inside IFRA Category 4.

    The limit comes from the gate's own evaluation
    (``engine.ifra_standards.single_material_limit_pct``), so a natural's
    Annex I constituents count: rose oil is held by its methyl eugenol.  This
    is a safety cap.  No allocation, top-up or named-note reallocation passes
    it.  Prohibited stocks are left to the composer's IFRA screen and the gate.
    """

    entry = single_material_limit_pct(candidate.stock.identity_name or candidate.stock.name)
    if entry is None:
        return None
    status, limit = entry
    dilution = Decimal(str(candidate.stock.dilution))
    if status == "prohibited" or limit is None or dilution <= 0:
        return None
    raw_fraction = Decimal(str(limit)) / (IFRA_CAP_FINISHED_FRACTION * dilution * 100)
    return max(
        1,
        int((Decimal(liquid_total_ul) * raw_fraction).to_integral_value(rounding=ROUND_FLOOR)),
    )


def _with_ifra_cap(cap: int | None, candidate: Candidate, liquid_total_ul: int) -> int | None:
    """``cap`` lowered to the stock's IFRA cap; None (no cap) becomes the IFRA cap."""

    ifra = _ifra_cap_ul(candidate, liquid_total_ul)
    if ifra is None:
        return cap
    return ifra if cap is None else min(cap, ifra)


def _screening_default(choice: Choice, liquid_total_ul: int) -> NormalUseCeiling | None:
    """The project screening default for a row nobody has researched.

    Only a row with no ceiling row and no identity hard cap gets one, and
    never a row that carries a note the brief names (the name leads) or a
    functional carrier such as Benzyl Benzoate (a carrier, not an odorant dose).
    """

    role = choice.role
    if role.serves_requested_facet or role.exact_preference_required:
        return None
    candidate = choice.candidate
    if _key(candidate.stock.identity_name or candidate.stock.name) in _DESIGN_FUNCTIONAL_CARRIERS:
        return None
    if _normal_use_ceiling(candidate) is not None or _hard_cap_ul(candidate, liquid_total_ul) is not None:
        return None
    return match_screening_default(_candidate_identity_probe(candidate))


def _screening_default_cap_ul(choice: Choice, liquid_total_ul: int) -> int | None:
    default = _screening_default(choice, liquid_total_ul)
    if default is None:
        return None
    return _active_fraction_cap_ul(choice.candidate, default.max_active_fraction, liquid_total_ul)


def _design_cap_ul(
    choice: Choice, liquid_total_ul: int, *, screening_default: bool = True
) -> int | None:
    """Return a conservative bench-design cap.

    The cap is the lower of the identity hard cap (or, without one, the role
    cap and any screening default) and the material's normal-use ceiling,
    and never above the stock's IFRA cap (``_ifra_cap_ul``), the one safety
    limit here.  ``screening_default=False`` leaves the soft screening default
    out, for callers that plan around the caps the planner never releases.
    """

    hard = _hard_cap_ul(choice.candidate, liquid_total_ul)
    base = hard if hard is not None else _role_cap_ul(choice, liquid_total_ul)
    default = _screening_default_cap_ul(choice, liquid_total_ul) if screening_default else None
    if default is not None:
        base = min(base, default)
    ceiling = _normal_use_ceiling_cap_ul(choice.candidate, liquid_total_ul)
    base = base if ceiling is None else min(base, ceiling)
    return _with_ifra_cap(base, choice.candidate, liquid_total_ul)


def _role_cap_ul(choice: Choice, liquid_total_ul: int) -> int:
    if choice.role.max_raw_share is not None:
        return max(1, int(liquid_total_ul * choice.role.max_raw_share))
    candidate = choice.candidate
    probe = _candidate_identity_probe(candidate)
    fraction = float(candidate.stock.dilution)
    if choice.role.function in {"modifier", "contrast"}:
        fraction_cap = 0.25 if fraction <= 0.1 else 0.10
    elif any(
        word in probe
        for word in (
            " absolute",
            " eo ",
            " oil ",
            "resinoid",
            "tincture",
            "cedarwood",
            "vetiver",
            "patchouli",
            "lavender",
            "rosemary",
            "basil",
            "cardamom",
            "chamomile",
        )
    ) and fraction >= 0.99:
        fraction_cap = 0.25
    elif choice.role.function in {"volume", "structure"}:
        fraction_cap = 0.35
    else:
        fraction_cap = 0.30
    return max(1, int(liquid_total_ul * fraction_cap))


def _allocation_weight(choice: Choice) -> float:
    """Adjust a role's raw-stock weight without claiming exact active mass.

    A 10% stock and a neat stock should not receive the same raw volume merely
    because their conceptual role shares match.  Moderate dilutions are
    compensated conservatively by the square root of stock strength.  Very
    dilute trace stocks remain trace-scaled, and all hard/design caps still
    apply.  This is a formulation heuristic; density-dependent mass remains
    withheld in the returned row contract.
    """

    weight = max(choice.role.share, 0.000001)
    fraction = max(float(choice.candidate.stock.dilution), 0.000001)
    if (
        0.05 <= fraction < 0.999
        and choice.role.function
        in {"character", "structure", "volume", "bridge", "fixative", "texture"}
    ):
        return weight * min(3.0, fraction ** -0.5)
    return weight


def _allocate_with_bulk_fallback(
    total: int,
    free_rows: Sequence[tuple[int, float, int | None]],
    choices: Sequence[Choice],
    liquid_total_ul: int,
    holds: list[str],
) -> dict[int, int]:
    """Allocate within every cap; if that cannot fill the total, release soft role caps.

    Normal-use ceilings, trace caps and screening defaults can leave too
    little room.  The spare space goes first to the rows that carry a note the
    brief names (the name leads), then to volume and structure rows, then to
    other rows whose role has no explicit restraint share (such as a 3%
    contrast accent).  A ceiling, trace cap or IFRA cap is never exceeded; if no row can
    take the space this still raises ValueError and the design is withheld.
    Each row pushed past its role cap is named in a
    ROLE_CAP_EXCEEDED_TO_FILL_TOTAL hold.

    A screening default is soft like a role cap and released with the volume
    and structure stages.  If the rows are still short, a last stage drops the
    screening defaults of the remaining rows, so a design that fills without
    them is never withheld because of them.  Each row pushed past its
    screening default is named in a SCREENING_DEFAULT_EXCEEDED_TO_FILL_TOTAL
    hold instead of the role-cap one.
    """

    try:
        return _allocate_capped(total, free_rows)
    except ValueError:
        pass
    firm = {
        index
        for index, _weight, _cap in free_rows
        if _hard_cap_ul(choices[index].candidate, liquid_total_ul) is not None
        or _normal_use_ceiling_cap_ul(choices[index].candidate, liquid_total_ul) is not None
    }

    named = {
        index
        for index, _weight, _cap in free_rows
        if index not in firm and choices[index].role.serves_requested_facet
    }

    def releasable(index: int, stage: int) -> bool:
        role = choices[index].role
        if index in firm:
            return False
        if index in named:
            return True
        if stage == 0:
            return False
        if role.function in {"volume", "structure"}:
            return True
        return stage == 2 and role.max_raw_share is None

    defaults = {
        index: default
        for index, _weight, _cap in free_rows
        if index not in firm
        and (default := _screening_default_cap_ul(choices[index], liquid_total_ul)) is not None
    }

    def without_default(index: int, cap: int | None) -> int | None:
        # The cap the row would have had without its screening default.
        if index not in defaults:
            return cap
        return _with_ifra_cap(
            _role_cap_ul(choices[index], liquid_total_ul), choices[index].candidate, liquid_total_ul
        )

    def released(index: int) -> int | None:
        # A released row loses its soft caps but never its IFRA cap.
        return _ifra_cap_ul(choices[index].candidate, liquid_total_ul)

    stages = ((0,) if named else ()) + (1, 2) + ((3,) if defaults else ())
    allocated: dict[int, int] = {}
    for stage in stages:
        relaxed = [
            (
                index,
                weight,
                released(index)
                if releasable(index, min(stage, 2))
                else (without_default(index, cap) if stage == 3 else cap),
            )
            for index, weight, cap in free_rows
        ]
        try:
            allocated = _allocate_capped(total, relaxed)
            break
        except ValueError:
            if stage == stages[-1]:
                raise
    for index, _weight, cap in free_rows:
        amount = allocated.get(index, 0)
        stock_id = choices[index].candidate.stock.stock_id
        if index in defaults and amount > defaults[index]:
            holds.append(f"SCREENING_DEFAULT_EXCEEDED_TO_FILL_TOTAL:{stock_id}")
        elif index not in firm and cap is not None and amount > cap:
            holds.append(f"ROLE_CAP_EXCEEDED_TO_FILL_TOTAL:{stock_id}")
    return allocated


# The rows that carry the notes a brief names together hold at least this
# share of the formula's fragrance-active volume (AGENTS.md Rule 3).
NAMED_NOTE_FLOOR_SHARE = Decimal("0.40")


def _firm_cap_ul(choice: Choice, liquid_total_ul: int) -> int | None:
    """The cap no reallocation may pass: identity hard (trace) cap, normal-use ceiling or IFRA cap."""

    caps = [
        cap
        for cap in (
            _hard_cap_ul(choice.candidate, liquid_total_ul),
            _normal_use_ceiling_cap_ul(choice.candidate, liquid_total_ul),
            _ifra_cap_ul(choice.candidate, liquid_total_ul),
        )
        if cap is not None
    ]
    return min(caps) if caps else None


def _active_ul(choice: Choice, amount: int) -> Decimal:
    """Fragrance-active volume of a liquid row: stock volume times stock strength."""

    stock = choice.candidate.stock
    if _key(stock.identity_name or stock.name) in _DESIGN_FUNCTIONAL_CARRIERS:
        return Decimal(0)
    return Decimal(amount) * Decimal(str(stock.dilution))


def _lead_with_named_notes(
    allocated: dict[int, int],
    free_rows: Sequence[tuple[int, float, int | None]],
    fixed_liquid: dict[int, int],
    choices: Sequence[Choice],
    liquid_total_ul: int,
    holds: list[str],
) -> dict[int, int]:
    """Make the notes a brief names lead the formula it composes.

    Two rules, applied to the free rows only (a requested quantity is never
    moved, and neither is a row that must use an exact preferred material):

    1. Floor: the rows that serve a requested facet together hold at least
       NAMED_NOTE_FLOOR_SHARE of the fragrance-active volume.  Volume is taken
       proportionally from the other free rows (each keeps at least the
       10 uL transfer floor) and given to the named rows.
    2. Lead: no generic bridge, volume, layer or accent slot carries more
       active volume than the largest named row; its excess goes to the
       named rows.

    The named rows never pass a firm cap (identity hard cap, trace cap,
    normal-use ceiling or IFRA cap); their role caps may be passed, and each row that is
    is named in a ROLE_CAP_EXCEEDED_TO_FILL_TOTAL hold.  When firm caps stop
    the floor short, the design is kept with a NAMED_NOTE_FLOOR_SHORT hold
    giving the share reached; a generic slot the named rows cannot outgrow
    keeps its volume under a GENERIC_SLOT_ABOVE_NAMED_LEAD hold.
    """

    amounts = {**fixed_liquid, **allocated}
    named_all = [index for index in amounts if choices[index].role.serves_requested_facet]
    if not named_all or not allocated:
        return allocated
    named = [index for index in allocated if index in named_all]
    donors = [
        index
        for index in allocated
        if index not in named_all and not choices[index].role.exact_preference_required
    ]
    firm = {index: _firm_cap_ul(choices[index], liquid_total_ul) for index in named}

    def active(state: dict[int, int], index: int) -> Decimal:
        return _active_ul(choices[index], state[index])

    def named_share(state: dict[int, int]) -> Decimal:
        total = sum(active(state, index) for index in state)
        if total <= 0:
            return Decimal(0)
        return sum(active(state, index) for index in named_all) / total

    def move(state: dict[int, int], take: dict[int, int]) -> dict[int, int] | None:
        freed = sum(take.values())
        if freed == 0:
            return state
        room = [
            (
                index,
                _allocation_weight(choices[index]),
                None if firm[index] is None else max(0, firm[index] - state[index]),
            )
            for index in named
        ]
        try:
            placed = _allocate_capped(freed, room)
        except ValueError:
            return None
        moved = dict(state)
        for index, amount in take.items():
            moved[index] -= amount
        for index, amount in placed.items():
            moved[index] += amount
        return moved

    def floor_take(fraction: float) -> dict[int, int]:
        return {
            index: amounts[index]
            - max(min(amounts[index], _MIN_RAW_TRANSFER_UL), int(amounts[index] * (1 - fraction)))
            for index in donors
        }

    state = amounts
    if named_share(state) < NAMED_NOTE_FLOOR_SHARE:
        # Share and freed volume both grow with the fraction taken, so the
        # largest placeable fraction and the smallest sufficient one are
        # found by bisection.
        low, high = 0.0, 1.0
        if move(amounts, floor_take(high)) is None:
            for _ in range(40):
                middle = (low + high) / 2
                if move(amounts, floor_take(middle)) is None:
                    high = middle
                else:
                    low = middle
            high = low
        reachable = move(amounts, floor_take(high)) or amounts
        if named_share(reachable) < NAMED_NOTE_FLOOR_SHARE:
            state = reachable
            percent = (named_share(state) * 100).quantize(Decimal("0.1"))
            holds.append(f"NAMED_NOTE_FLOOR_SHORT:{percent}")
        else:
            low = 0.0
            for _ in range(40):
                middle = (low + high) / 2
                candidate = move(amounts, floor_take(middle))
                if candidate is not None and named_share(candidate) >= NAMED_NOTE_FLOOR_SHARE:
                    high = middle
                else:
                    low = middle
            state = move(amounts, floor_take(high)) or amounts

    lead = max(active(state, index) for index in named_all)
    over = sorted(
        (
            index
            for index in allocated
            if choices[index].role.generic_slot
            and index not in named_all
            and active(state, index) > lead
        ),
        key=lambda index: -active(state, index),
    )
    for index in over:
        lead = max(active(state, row) for row in named_all)
        strength = Decimal(str(choices[index].candidate.stock.dilution))
        keep = int(lead / strength) if strength > 0 else state[index]
        moved = move(state, {index: max(0, state[index] - keep)})
        if moved is None:
            holds.append(f"GENERIC_SLOT_ABOVE_NAMED_LEAD:{choices[index].candidate.stock.stock_id}")
            continue
        state = moved

    caps = {index: cap for index, _weight, cap in free_rows}
    for index in named:
        cap = caps.get(index)
        if cap is not None and state[index] > cap:
            holds.append(
                f"ROLE_CAP_EXCEEDED_TO_FILL_TOTAL:{choices[index].candidate.stock.stock_id}"
            )
    return {index: state[index] for index in allocated}


def _allocate_capped(total: int, weighted: Sequence[tuple[int, float, int | None]]) -> dict[int, int]:
    result = {index: 0 for index, _weight, _cap in weighted}
    remaining = total
    open_rows = list(weighted)
    while remaining > 0 and open_rows:
        weight_total = sum(max(weight, 0.000001) for _index, weight, _cap in open_rows)
        exact = {
            index: Decimal(remaining) * Decimal(str(max(weight, 0.000001) / weight_total))
            for index, weight, _cap in open_rows
        }
        tentative = {
            index: int(value.to_integral_value(rounding=ROUND_FLOOR))
            for index, value in exact.items()
        }
        remainder = remaining - sum(tentative.values())
        order = sorted(
            exact,
            key=lambda index: (-(exact[index] - tentative[index]), index),
        )
        for index in order[:remainder]:
            tentative[index] += 1

        capped_any = False
        next_open: list[tuple[int, float, int | None]] = []
        assigned_this_round = 0
        for index, weight, cap in open_rows:
            proposed = tentative[index]
            room = None if cap is None else max(0, cap - result[index])
            if room is not None and proposed >= room:
                result[index] += room
                assigned_this_round += room
                capped_any = True
            else:
                next_open.append((index, weight, cap))
        if not capped_any:
            for index, amount in tentative.items():
                result[index] += amount
            remaining = 0
            break
        remaining -= assigned_this_round
        open_rows = next_open

    if remaining > 0:
        # Every remaining row was trace-capped.  Fail rather than silently
        # violating the cap; callers surface a design hold.
        raise ValueError("trace-dose caps leave no material able to carry the requested liquid total")
    return result


def _active_quantity_state(stock: InventoryMaterial, unit: str) -> str:
    basis = stock.fraction_basis.casefold()
    if unit == "mg":
        if stock.dilution >= 0.999999:
            return "EXACT_ACTIVE_MASS_FROM_NEAT_SOLID"
        if basis == "mass_fraction":
            return "ACTIVE_MASS_COMPUTABLE_FROM_TRANSFERRED_STOCK_MASS"
        return "ACTIVE_MASS_WITHHELD_FRACTION_BASIS_UNRESOLVED"
    if basis == "mass_fraction":
        return "EXACT_ACTIVE_MASS_WITHHELD_DENSITY_REQUIRED"
    if basis == "mass_per_volume":
        return "ACTIVE_MASS_COMPUTABLE_FROM_DECLARED_MASS_PER_VOLUME"
    if basis == "volume_fraction":
        return "ACTIVE_VOLUME_COMPUTABLE_FROM_DECLARED_VOLUME_FRACTION"
    if basis == "neat" or stock.dilution >= 0.999999:
        return "NEAT_STOCK_VOLUME_RECORDED_ACTIVE_MASS_WITHHELD_DENSITY_REQUIRED"
    return "STOCK_VOLUME_ONLY_FRACTION_BASIS_UNRESOLVED"


_ROLE_RELATIONSHIP_RATIONALE = {
    "geranium_link": "links the lavender heart to the moss hinge without adding a separate soapy chassis",
    "dry_amber_trace": "adds a narrow mineral gap between aromatic herbs and wood rather than a sweet amber base",
    "root_detail": "adds earthy root detail distinct from the drier vertical vetiver axis",
    "persistent_signature": "restates the citrus-and-leaf signature in a less volatile material rather than labeling an unrelated fixative as persistence",
    "fig_flesh": "supplies the dry waxy body between torn leaf and sandalwood so the lactone can remain a trace",
    "milky_sap": "bridges green fig flesh into creamy wood without making a standalone dessert accord",
    "tuberose_volume": "is admitted only when a multi-form brief explicitly justifies a separate structural tuberose source",
    "wearable_entry": "makes first contact more legible while leaving the named heart and base recognizers intact",
    "wearable_transition": "reduces the abruptness between the named character block and its dry structure",
    "soft_cathedral_exit": "reduces late-stage severity at skin scale without turning the concept into sweet amber",
    "aromatic_market_bridge": "connects mineral freshness to a familiar aromatic register without supplying a clone target",
    "pepper_lift": "adds dry first-contact definition without introducing a sweet or shower-gel accord",
}


def _role_rationale(role: RoleSpec) -> str:
    relationship = _ROLE_RELATIONSHIP_RATIONALE.get(role.role_id)
    if relationship:
        return f"{role.label}: {relationship}."
    return (
        f"{role.label}: selected as the nonredundant {role.function} for this concept "
        "after hard exclusions and stock form were applied."
    )


def _formula_rows(
    choices: Sequence[Choice],
    *,
    liquid_total_ul: int,
    quantities: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    fixed_liquid: dict[int, int] = {}
    solid_amounts: dict[int, int] = {}
    holds: list[str] = []
    amount: Decimal | int
    for index, choice in enumerate(choices):
        explicit = _quantity_for_candidate(choice.candidate, quantities)
        if choice.candidate.solid:
            if explicit is not None:
                amount, unit = explicit
                if unit == "g":
                    amount *= 1000
                elif unit != "mg":
                    holds.append(f"SOLID_QUANTITY_UNIT_MISMATCH:{choice.candidate.stock.stock_id}")
                    continue
                solid_amounts[index] = int(amount.to_integral_value())
            else:
                default = _solid_default_mg(choice.candidate, liquid_total_ul)
                if default is None:
                    holds.append(f"SOLID_MASS_REQUIRED:{choice.candidate.stock.stock_id}")
                else:
                    solid_amounts[index] = default
                    holds.append(f"SOLID_MASS_IS_DESIGN_HEURISTIC:{choice.candidate.stock.stock_id}")
            continue
        if explicit is None:
            continue
        amount, unit = explicit
        if unit == "mL":
            amount *= 1000
        elif unit != "uL":
            holds.append(f"LIQUID_QUANTITY_UNIT_MISMATCH:{choice.candidate.stock.stock_id}")
            continue
        if amount != amount.to_integral_value():
            holds.append(f"SUB_MICROLITRE_QUANTITY_UNSUPPORTED:{choice.candidate.stock.stock_id}")
            continue
        fixed_liquid[index] = int(amount)

    fixed_total = sum(fixed_liquid.values())
    if fixed_total > liquid_total_ul:
        raise ValueError("explicit liquid material doses exceed the requested liquid total")
    free_rows = [
        (index, _allocation_weight(choice), _design_cap_ul(choice, liquid_total_ul))
        for index, choice in enumerate(choices)
        if not choice.candidate.solid and index not in fixed_liquid
    ]
    if not free_rows and fixed_total != liquid_total_ul:
        raise ValueError("explicit liquid doses do not fill the requested liquid total")
    allocated = (
        _allocate_with_bulk_fallback(
            liquid_total_ul - fixed_total, free_rows, choices, liquid_total_ul, holds
        )
        if free_rows
        else {}
    )
    allocated = _lead_with_named_notes(
        allocated, free_rows, fixed_liquid, choices, liquid_total_ul, holds
    )

    rows: list[dict[str, Any]] = []
    liquid_sum = 0
    mass_sum = Decimal(0)
    total_role_share = sum(choice.role.share for choice in choices) or 1.0
    for index, choice in enumerate(choices):
        candidate = choice.candidate
        stock = candidate.stock
        if candidate.solid:
            if index not in solid_amounts:
                continue
            amount = solid_amounts[index]
            unit = "mg"
            operation = "MASS_ADD"
            mass_sum += amount
        else:
            amount = fixed_liquid.get(index, allocated.get(index, 0))
            unit = "uL"
            liquid_sum += amount
            operation = "DIRECT_ADD"
            if 0 < amount < _MIN_RAW_TRANSFER_UL:
                operation = "PREPARED_DILUTION_REQUIRED"
                holds.append(f"SUB_10_UL_RAW_TRANSFER:{stock.stock_id}")
        row_execution_ready = bool(stock.execution_ready and operation != "PREPARED_DILUTION_REQUIRED")
        if not row_execution_ready:
            holds.append(f"STOCK_EXECUTION_BINDING_REQUIRED:{stock.stock_id}")
        display_material = (
            re.sub(r"\s*#.*$", "", stock.raw_name).strip()
            if candidate.legacy_text_only
            else (stock.identity_name or stock.name)
        )
        rows.append(
            {
                "row_id": f"design-v2-{index + 1:02d}-{stable_payload_hash({'stock': stock.stock_id, 'role': choice.role.role_id})[:10]}",
                "slot": choice.role.role_id,
                "slot_label": choice.role.label,
                "material": display_material,
                "identity_name": stock.identity_name or stock.name,
                "stock_label": stock.raw_name or stock.name,
                "stock_id": stock.stock_id,
                "stock_authority": stock.authority,
                "stock_source_ref": stock.source_ref,
                "stock_fraction_decimal": _decimal_text(stock.dilution),
                "fraction_basis": stock.fraction_basis,
                "carrier": stock.carrier or None,
                "amount_decimal": str(amount),
                "amount_unit": unit,
                "operation": operation,
                "stock_binding_state": (
                    "EXECUTION_BOUND"
                    if row_execution_ready
                    else "DESIGN_ONLY_EXECUTION_BINDING_UNRESOLVED"
                ),
                "active_quantity_state": _active_quantity_state(stock, unit),
                "note": choice.role.note,
                "role": choice.role.function,
                "profile_source": candidate.profile_source,
                "design_share_decimal": _decimal_text(Decimal(str(choice.role.share)) / Decimal(str(total_role_share))),
                "allocation_weight_decimal": _decimal_text(_allocation_weight(choice)),
                "allocation_basis": (
                    "STOCK_STRENGTH_COMPENSATED_HEURISTIC_NOT_ACTIVE_MASS"
                    if _allocation_weight(choice) != choice.role.share
                    else "CONCEPT_ROLE_SHARE_WITH_CAPS"
                ),
                "rationale": _role_rationale(choice.role),
                "alternatives_considered": [
                    {
                        "material": material,
                        "reason_not_selected": "Lower exact role or stock-readiness fit; retain as a controlled alternative.",
                    }
                    for material in choice.alternatives
                ],
                "design_ready": effective_design_ready(stock),
                "execution_ready": row_execution_ready,
                "execution_hold_reason": (
                    stock.execution_hold_reason
                    if not stock.execution_ready
                    else (
                        "PREPARED_DILUTION_REQUIRED_BELOW_TRANSFER_FLOOR"
                        if operation == "PREPARED_DILUTION_REQUIRED"
                        else ""
                    )
                ),
                "source_ref": stock.source_ref,
                "authority": "DESIGN_HYPOTHESIS_ONLY",
            }
        )
        ceiling = _normal_use_ceiling(candidate)
        if ceiling is None and not candidate.solid:
            ceiling = _screening_default(choice, liquid_total_ul)
        if ceiling is not None:
            rows[-1]["normal_use_ceiling_pct_of_concentrate"] = ceiling.max_active_pct_of_concentrate
            rows[-1]["normal_use_ceiling_kind"] = ceiling.kind
            if ceiling.label:
                rows[-1]["normal_use_ceiling_label"] = ceiling.label
    if liquid_sum != liquid_total_ul:
        raise AssertionError("liquid allocation failed exact conservation")
    return rows, {"liquid_total_ul": str(liquid_sum), "mass_total_mg": str(mass_sum)}, sorted(set(holds))


_TEMPORAL_CONTEXT_PATTERNS = {
    "OPENING": r"\b(?:opening|opens?|first blast)\b",
    "FIVE_MINUTES": r"\b(?:at\s+)?(?:5|five)[- ]*minutes?\b",
    "THIRTY_MINUTES": r"\b(?:at\s+)?(?:30|thirty)[- ]*minutes?\b",
    "TWO_HOURS": r"\b(?:at\s+)?(?:2|two)[- ]*hours?\b",
    "FOUR_HOURS": r"\b(?:at\s+)?(?:4|four)[- ]*hours?\b",
    "HEART": r"\bheart\b",
    "DRYDOWN": r"\bdrydown\b",
}

_TEMPORAL_ROLE_EXPANSIONS = {
    "citrus": ("grapefruit", "peel", "pith"),
    "tea": ("tea", "leaf", "tannin"),
    "lavender": ("lavender", "aromatic"),
    "green": ("green", "stem", "leaf"),
    "milky": ("milky", "sap", "laitone"),
    "fig": ("fig", "skin", "sap"),
    "leafy": ("leaf", "green", "crushed", "bitter"),
    "sandalwood": ("sandalwood", "creamy", "wood"),
    "rose": ("rose", "floral"),
    "suede": ("suede", "leather"),
    "coffee": ("coffee", "roast", "bean"),
    "roasted": ("coffee", "roast", "bean"),
    "cocoa": ("cocoa", "husk"),
    "ember": ("ember", "charred", "smoke", "wood"),
    "embers": ("ember", "charred", "smoke", "wood"),
    "wet": ("wet", "stone", "mineral"),
    "mineral": ("mineral", "stone"),
    "storm": ("storm", "ozone", "wind"),
    "driftwood": ("driftwood", "wood"),
    "tuberose": ("tuberose", "floral"),
    "skin": ("skin", "dry", "fixation"),
    "luminous": ("petal", "lift", "jasmine", "air"),
    "incense": ("incense", "resin", "smoke"),
    "iris": ("iris", "violet", "root"),
    "echo": ("persistent", "signature", "citrus", "tea"),
}

_TEMPORAL_STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "be",
    "becomes",
    "design",
    "hour",
    "hours",
    "in",
    "is",
    "leaves",
    "minute",
    "minutes",
    "recognizable",
    "recognizably",
    "remains",
    "the",
    "then",
    "to",
    "with",
}


def _temporal_request_context(text: str, label: str) -> str:
    pattern = _TEMPORAL_CONTEXT_PATTERNS.get(label)
    if pattern is None:
        return ""
    matches = tuple(re.finditer(pattern, text, re.I))
    if not matches:
        return ""
    match = matches[-1]
    left_window = text[max(0, match.start() - 160) : match.start()]
    left_delimiters = [
        left_window.rfind(token)
        for token in (",", ";", ".", " and ")
    ]
    left = max(left_delimiters)
    prefix = left_window[left + (5 if left_window[left:].casefold().startswith(" and ") else 1) :] if left >= 0 else left_window

    right_window = text[match.end() : match.end() + 160]
    right_positions = [
        position
        for token in (",", ";", ".", " and ")
        if (position := right_window.casefold().find(token)) >= 0
    ]
    right = min(right_positions) if right_positions else len(right_window)
    suffix = right_window[:right]
    context = _clean(f"{prefix} {suffix}")
    context = re.split(
        r"\b(?:instead\s+of|rather\s+than|without)\b",
        context,
        maxsplit=1,
        flags=re.I,
    )[0]
    if label == "OPENING":
        with_match = tuple(re.finditer(r"\bwith\b", context, re.I))
        if with_match:
            context = context[with_match[-1].end() :]
    return _clean(context)


def _temporal_role_matches(
    rows: Sequence[dict[str, Any]],
    context: str,
    fallback_tier: str,
) -> list[dict[str, str]]:
    context_tokens = {
        token
        for token in _key(context).split()
        if len(token) > 2 and token not in _TEMPORAL_STOPWORDS
    }
    expanded = set(context_tokens)
    for token in tuple(context_tokens):
        expanded.update(_TEMPORAL_ROLE_EXPANSIONS.get(token, ()))
    # A character-word match must not move a heart or base row into the
    # opening (or a volatile top row into a four-hour promise).  The temporal
    # object is a role-placement hypothesis, not a release simulation.
    tier_rows = [row for row in rows if row["note"] == fallback_tier]
    eligible_rows = tier_rows or list(rows)
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, row in enumerate(eligible_rows):
        probe = set(
            _key(
                f"{row['slot']} {row['slot_label']} {row['material']} "
                f"{row['note']} {row['role']}"
            ).split()
        )
        score = len(expanded & probe)
        if score:
            scored.append((-score, index, row))
    selected = [row for _score, _index, row in sorted(scored)[:3]]
    if not selected:
        selected = eligible_rows
    return [
        {"material": row["material"], "role": row["slot_label"]}
        for row in selected[:3]
    ]


def _temporal_hypothesis(
    rows: Sequence[dict[str, Any]],
    windows: Sequence[dict[str, Any]],
    request_text: str,
) -> dict[str, Any] | None:
    if not windows:
        return None
    stages: list[dict[str, Any]] = []
    seen: set[str] = set()
    labels = {
        str(window.get("window") or window.get("label") or "UNSPECIFIED")
        for window in windows
    }
    for window in windows:
        label = str(window.get("window") or window.get("label") or "UNSPECIFIED")
        if label == "HEART" and labels & {"THIRTY_MINUTES", "TWO_HOURS"}:
            continue
        if label == "DRYDOWN" and "FOUR_HOURS" in labels:
            continue
        if label in seen:
            continue
        seen.add(label)
        if label in {"OPENING", "FIVE_MINUTES"}:
            tier = "top"
        elif label in {"THIRTY_MINUTES", "HEART", "TWO_HOURS"}:
            tier = "heart"
        else:
            tier = "base"
        requested_context = _temporal_request_context(request_text, label)
        intended = _temporal_role_matches(rows, requested_context, tier)
        stages.append(
            {
                "window": label,
                "time_seconds": window.get("time_seconds"),
                "intended_tier": tier,
                "requested_context": requested_context or None,
                "intended_roles": intended,
            }
        )
    return {
        "status": "TEMPORAL_DESIGN_HYPOTHESIS_NOT_VALIDATED",
        "sequence": stages,
        "release_model_used": False,
        "physical_timing_established": False,
        "alignment_basis": "BRIEF_TO_ROLE_HYPOTHESIS_ONLY",
        "required_validation": "Smell or measure the exact pilot at the requested windows.",
    }


_REFERENCE_FACET_EXPANSIONS = {
    "ambroxan": ("ambrox", "mineral", "amber"),
    "bergamot": ("citrus", "peel", "grapefruit"),
    "geranium": ("aromatic", "herb", "rose"),
    "lavender": ("lavender", "aromatic"),
    "mineral": ("mineral", "stone", "ambrox"),
    "pepper": ("pepper", "spice"),
    "sandalwood": ("sandalwood", "creamy", "wood"),
    "vanilla": ("vanilla", "sweet", "gourmand"),
}


def _reference_row_links(
    rows: Sequence[dict[str, Any]],
    facets: Sequence[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    links: list[dict[str, Any]] = []
    linked_slots: set[str] = set()
    for facet in facets:
        tokens = set(_key(facet).split())
        for token in tuple(tokens):
            tokens.update(_REFERENCE_FACET_EXPANSIONS.get(token, ()))
        matches = []
        for row in rows:
            probe = set(
                _key(
                    f"{row['slot']} {row['slot_label']} {row['material']} "
                    f"{row['note']} {row['role']}"
                ).split()
            )
            if tokens & probe:
                matches.append(
                    {
                        "slot": row["slot"],
                        "material": row["material"],
                        "role": row["slot_label"],
                    }
                )
                linked_slots.add(str(row["slot"]))
        links.append(
            {
                "marketed_facet": facet,
                "selected_rows": matches,
                "state": "DESIGN_LINK_ONLY" if matches else "NO_SELECTED_ROW_LINK",
            }
        )
    target_only = [
        str(row["slot_label"])
        for row in rows
        if str(row["slot"]) not in linked_slots
    ]
    return links, target_only


def _reference_context(
    text: str,
    *,
    appeal_mode: str,
    concept: ConceptSpec | None,
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any] | None:
    registry = _cached_reference_registry(_reference_registry_sha256())
    resolved = resolve_documentary_references(text, as_of_date=date.today().isoformat(), registry=registry)
    if resolved["unresolved"]:
        return {
            "status": "WITHHELD_NAMED_REFERENCE_APPLICABILITY",
            "named_products": [],
            "unresolved_references": resolved["unresolved"],
            "formula_inference_used": False,
            "registry_sha256": registry.registry_sha256,
            **FALSE_ACTION_AUTHORITY,
        }
    named = []
    for product in resolved["products"]:
        target_role_probe = _key(
            " ".join(role.label for role in (concept.roles if concept else ()))
        )
        overlap = [
            facet
            for facet in product.marketed_facets
            if any(token in target_role_probe for token in _key(facet).split())
        ]
        links, target_only = _reference_row_links(rows, product.marketed_facets)
        named.append(
            {
                "product_id": product.product_id,
                "display_name": product.display_name,
                "marketed_family": product.marketed_family,
                "marketed_facets": list(product.marketed_facets),
                "marketed_note_architecture": {
                    stage: list(notes)
                    for stage, notes in product.marketed_note_architecture.items()
                },
                "official_architecture_authority": product.official_architecture_authority,
                "formula_composition_known": product.formula_composition_known,
                "liking_authority": product.liking_authority,
                "target_overlap_facets": overlap,
                "selected_architecture_links": links,
                "target_specific_selected_roles": target_only,
            }
        )
    if named:
        return {
            "status": "DOCUMENTARY_ARCHITECTURE_CLUES_ONLY",
            "named_products": named,
            "comparison_use": (
                "Use marketed facets only as diagnostic contrasts; preserve the target's "
                "own concept and do not infer formula ratios, sensory similarity, or liking."
            ),
            "target_signature_roles": [
                role.label
                for role in (concept.roles[: concept.complex_count] if concept else ())
            ],
            "design_guidance": (
                "Retain target-specific roles that are absent from the marketed overlap; "
                "use shared facets only to ask whether the pilot is legible and wearable."
            ),
            "formula_inference_used": False,
            "proprietary_composition_state": "PROPRIETARY_COMPOSITION_UNKNOWN",
            "population_liking_state": "POPULATION_LIKING_NOT_ESTABLISHED",
            "registry_sha256": registry.registry_sha256,
        }
    if appeal_mode != "GLOBAL_CROWD_PLEASING":
        return None
    tags = [
        token
        for token in _key(
            f"{concept.concept_id if concept else ''} {positive_reference_text(text)}"
        ).split()
        if len(token) >= 4
    ]
    try:
        panel = build_commercial_reference_panel(
            tags,
            as_of_date=date.today().isoformat(),
            registry=registry,
        )
    except (KeyError, ValueError):
        return {
            "status": "DOCUMENTARY_PRESTIGE_DESIGN_CRITERIA_ONLY",
            "named_products": [],
            "comparison_use": (
                "No unrelated bestseller panel was silently borrowed.  The prestige "
                "comparison is limited to request-derived design criteria: first-contact "
                "legibility, transition clarity, controlled diffusion, wearability, and "
                "retention of the named identity."
            ),
            "design_criteria": [
                "first-contact legibility",
                "transition clarity",
                "controlled diffusion",
                "wearability",
                "retention of the named identity",
            ],
            "target_signature_roles": [
                role.label
                for role in (concept.roles[: concept.complex_count] if concept else ())
            ],
            "design_guidance": (
                "Evaluate the added entry and exit roles against those criteria while "
                "preserving the target signature. No commercial product contributes a "
                "formula row or liking label."
            ),
            "formula_inference_used": False,
            "proprietary_composition_state": "PROPRIETARY_COMPOSITION_UNKNOWN",
            "population_liking_state": "POPULATION_LIKING_NOT_ESTABLISHED",
            "registry_sha256": registry.registry_sha256,
        }
    panel_products = [
        registry.products[str(member["product_id"])]
        for member in (
            *panel["panel"]["active_members"],
        )
        if str(member["product_id"]) in registry.products
    ]
    panel_facets = tuple(
        dict.fromkeys(
            facet
            for product in panel_products
            for facet in product.marketed_facets
        )
    )
    links, target_only = _reference_row_links(rows, panel_facets)
    return {
        "status": panel["status"],
        "panel_id": panel["panel"]["panel_id"],
        "panel_sha256": panel["panel_sha256"],
        "active_members": list(panel["panel"]["active_members"]),
        "comparison_use": panel["selection_scope"],
        "target_signature_roles": [
            role.label
            for role in (concept.roles[: concept.complex_count] if concept else ())
        ],
        "design_guidance": (
            "Use the panel as a documentary contrast after preserving the target's named "
            "roles; no panel product contributes a formula row or liking label."
        ),
        "selected_architecture_links": links,
        "target_specific_selected_roles": target_only,
        "formula_inference_used": False,
        "proprietary_composition_state": panel["proprietary_composition_state"],
        "population_liking_state": panel["population_liking_state"],
        "registry_sha256": panel["registry_sha256"],
    }


def _opaque_composition_limitations(
    rows: Sequence[dict[str, Any]],
    avoid: Sequence[str],
) -> list[str]:
    molecular_bans = {
        marker
        for raw in avoid
        for marker in ("indole", "lactone", "vanillin", "coumarin", "eugenol")
        if marker in _key(raw)
    }
    facet_markers = {
        marker
        for raw in avoid
        for marker in ("banana", "bubblegum", "coconut", "sunscreen", "solvent")
        if marker in _key(raw)
    }
    if not molecular_bans and not facet_markers:
        return []
    opaque_products = [
        row["material"]
        for row in rows
        if any(
            marker in _key(f"{row['material']} {row['stock_label']}")
            for marker in (" absolute", " eo", " oil", "base", "resinoid", "accord")
        )
    ]
    if not opaque_products:
        return []
    limitations = [
        f"OPAQUE_PRODUCT_CONSTITUENT_ABSENCE_NOT_ESTABLISHED:{marker}"
        for marker in sorted(molecular_bans)
    ]
    limitations.extend(
        f"OPAQUE_PRODUCT_AVOID_FACET_ABSENCE_NOT_ESTABLISHED:{marker}"
        for marker in sorted(facet_markers)
    )
    return limitations


def _withheld(
    *,
    status: str,
    name: str,
    interpretation: dict[str, Any],
    message: str,
    reason_codes: Sequence[str],
) -> dict[str, Any]:
    report = {
        "schema_version": "inventory-grounded-formula-design-v2",
        "status": status,
        "formula_name": name,
        "request_interpretation": interpretation,
        "assistant_message": message,
        "initial_formula": None,
        "optimized_formula": None,
        "composition_plan": None,
        "constraint_audit": {
            "state": "WITHHELD",
            "reason_codes": list(reason_codes),
        },
        "critic": {
            "state": "WITHHELD",
            "issues": list(reason_codes),
            "stop_reason": "HARD_CONSTRAINT_NOT_SATISFIED",
        },
        "formula_action": "NO_CHANGE",
        "inventory_modified": False,
        "formula_modified": False,
        "physical_compounding_performed": False,
        "pleasantness": None,
        "personal_liking": None,
        "population_liking": None,
        "beauty_score": None,
        "prohibited_objectives_used": [],
        **FALSE_ACTION_AUTHORITY,
    }
    return {**report, "design_sha256": stable_payload_hash(report)}


def compose_inventory_formula(
    *,
    idea: str,
    formula_name: str | None = None,
    liquid_concentrate_ul_decimal: str = "6000",
    max_materials: int = 8,
    must_preserve: Sequence[str] = (),
    must_avoid: Sequence[str] = (),
    previous_stock_ids: Sequence[str] = (),
    conversation_context: Sequence[str] = (),
    execution_strategy: str | None = None,
    appeal_mode: str | None = None,
    comparison_evidence: str = "DOCUMENT_ONLY",
    active_bottle_id: str | None = None,
) -> dict[str, Any]:
    """Compile one fast, inventory-grounded perfume design hypothesis."""

    clean_idea = _clean(idea)
    if not clean_idea:
        raise ValueError("idea must be non-empty text")
    if not 6 <= int(max_materials) <= 60:
        raise ValueError("max_materials must be between 6 and 60")
    liquid_total = _positive_decimal(liquid_concentrate_ul_decimal, "liquid_concentrate_ul_decimal")
    if liquid_total != liquid_total.to_integral_value() or liquid_total > 100_000:
        raise ValueError("liquid concentrate must be a whole number of uL no greater than 100000")
    name = _clean(formula_name) or " ".join(re.findall(r"[A-Za-z0-9'-]+", clean_idea)[:4]).title()

    # First load only to establish the complete known-name set; after request
    # interpretation we reload with exact positive product/form mentions so
    # duplicate stock identities can be retained correctly.
    preliminary, inventory, known_materials = _load_candidates(())
    interpretation = interpret_request(
        RequestInterpretationInputV1(
            original_request=clean_idea,
            known_materials=known_materials,
            desired_changes=(clean_idea,),
            must_preserve=tuple(must_preserve),
            must_avoid=tuple(must_avoid),
            execution_strategy=execution_strategy,
            appeal_mode=appeal_mode,
            comparison_evidence=comparison_evidence,
            active_bottle_id=active_bottle_id,
        )
    )
    if interpretation["confirmation_required"]:
        return _withheld(
            status="WITHHELD_REQUEST_AMBIGUOUS",
            name=name,
            interpretation=interpretation,
            message="The brief contains a hard contradiction or an unbound quantity, so I did not invent a formula.",
            reason_codes=interpretation["ambiguities"],
        )
    if interpretation["execution_strategy"] == "EVOLVING_BOTTLE" and not active_bottle_id:
        return _withheld(
            status="WITHHELD_ACTIVE_BOTTLE_STATE_REQUIRED",
            name=name,
            interpretation=interpretation,
            message="This is a same-bottle delta request, but no current bottle state was supplied. I will not invent the existing contents or total.",
            reason_codes=("ACTIVE_BOTTLE_STATE_REQUIRED",),
        )
    if interpretation["execution_strategy"] == "EVOLVING_BOTTLE":
        return _withheld(
            status="WITHHELD_USE_EVOLVING_BOTTLE_WORKFLOW",
            name=name,
            interpretation=interpretation,
            message="This request belongs in the existing bottle ledger so the program can replay the current state and propose one nonnegative delta.",
            reason_codes=("FORMULA_DESIGN_ROUTE_DOES_NOT_MUTATE_ACTIVE_BOTTLES",),
        )

    explicit_materials = tuple(interpretation["explicit_materials"])
    candidates = [
        replace(
            candidate,
            explicit=any(
                _candidate_matches_text(candidate, value)
                for value in explicit_materials
            ),
        )
        for candidate in preliminary
        if not candidate.solid
        or any(
            _candidate_matches_text(candidate, value)
            for value in explicit_materials
        )
    ]
    # Keep the original constraint phrases so form-specific bans such as
    # "Ambrox solution" do not broaden into a ban on Ambrox crystals.
    avoid = tuple(dict.fromkeys((*must_avoid, *interpretation["must_avoid"])))
    mandatory = tuple(interpretation["mandatory_materials"])
    missing_mandatory = [
        material
        for material in mandatory
        if not any(
            _candidate_matches_text(candidate, material)
            and not _avoid_candidate(candidate, avoid)
            for candidate in candidates
        )
    ]
    if missing_mandatory:
        return _withheld(
            status="WITHHELD_MANDATORY_MATERIAL_UNAVAILABLE",
            name=name,
            interpretation=interpretation,
            message="A mandatory material or exact stock form is not available in the current design inventory, so no substitute was silently used.",
            reason_codes=tuple(f"MANDATORY_MATERIAL_UNAVAILABLE:{item}" for item in missing_mandatory),
        )

    design_text = " ".join((name, *conversation_context, clean_idea))
    concept = _concept(design_text)
    anchor_roles = _anchor_roles(explicit_materials, concept)
    target_count = _role_count(design_text, concept, int(max_materials), 0)
    if concept is not None:
        core_roles = concept.roles[: concept.core_count]
        uncovered_anchors = sum(
            not any(
                any(
                    _key(anchor) in _key(preferred)
                    or _key(preferred) in _key(anchor)
                    for preferred in role.preferred_materials
                )
                for role in core_roles
            )
            for anchor in explicit_materials
        )
        target_count = min(int(max_materials), target_count + uncovered_anchors)
    target_count = max(target_count, len(anchor_roles))
    base_roles, variant_roles, repair_actions = _request_specific_roles(
        design_text,
        concept,
        evaluation_windows=interpretation["evaluation_windows"],
    )
    if variant_roles and _explicit_count(design_text) is None:
        target_count = min(int(max_materials), target_count + len(variant_roles))
    if concept is not None and variant_roles:
        base_roles = [
            *base_roles[: concept.core_count],
            *variant_roles,
            *base_roles[concept.core_count :],
        ]
    else:
        base_roles.extend(variant_roles)
    # Explicit anchors are placed first.  Concept roles already covered by an
    # exact anchor are omitted rather than selecting a redundant second row.
    roles: list[RoleSpec] = list(anchor_roles)
    covered_concept_role_ids = {
        role.role_id
        for role in _matched_anchor_roles(explicit_materials, concept)
        if role is not None
    }
    for role in base_roles:
        if len(roles) >= target_count:
            break
        # One explicit row covers one best-matching concept role.  Do not let a
        # material that appears in several preference lists erase every one of
        # those independent functions (for example Ambrettolide as both a skin
        # accent and one possible fixative).
        if role.role_id in covered_concept_role_ids:
            continue
        roles.append(role)
    if len(roles) < target_count:
        for role in _GENERIC_ROLES:
            if len(roles) >= target_count:
                break
            if any(existing.role_id == role.role_id for existing in roles):
                continue
            roles.append(role)

    choices, missing_roles = _select_choices(
        candidates,
        roles,
        avoid=avoid,
        previous_stock_ids=set(previous_stock_ids),
    )
    if missing_roles or len(choices) < min(6, target_count):
        reasons = [*(f"UNFILLED_REQUIRED_ROLE:{role}" for role in missing_roles)]
        if len(choices) < min(6, target_count):
            reasons.append("TOO_FEW_NONREDUNDANT_ELIGIBLE_ROLES")
        return _withheld(
            status="WITHHELD_CONCEPT_COVERAGE_INCOMPLETE",
            name=name,
            interpretation=interpretation,
            message="The current inventory and exclusions cannot cover the concept without filler or a silent substitution.",
            reason_codes=reasons,
        )

    try:
        rows, totals, holds = _formula_rows(
            choices,
            liquid_total_ul=int(liquid_total),
            quantities=interpretation["explicit_quantities"],
        )
    except ValueError as exc:
        return _withheld(
            status="WITHHELD_DOSE_ALLOCATION_INFEASIBLE",
            name=name,
            interpretation=interpretation,
            message=(
                "The requested fixed doses and conservative design caps cannot fill "
                "the requested liquid total without violating a bounded dose."
            ),
            reason_codes=(f"DOSE_ALLOCATION_INFEASIBLE:{exc}",),
        )
    temporal_hypothesis = _temporal_hypothesis(
        rows,
        interpretation["evaluation_windows"],
        design_text,
    )
    reference_context = _reference_context(
        design_text,
        appeal_mode=interpretation["appeal_mode"],
        concept=concept,
        rows=rows,
    )
    selected_count = len(rows)
    coverage = min(1.0, selected_count / max(1, len(roles)))
    selected_role_ids = {str(row["slot"]) for row in rows}
    if concept is None:
        construction_note = "A request-specific top, heart, base, bridge, and texture structure was assembled without a beauty objective."
    elif concept.concept_id == "intimate_skin":
        parts = ["warm skin", "pale wood", "close diffusion"]
        if "clean_paper" in selected_role_ids:
            parts.append("clean paper")
        if "book_leather" in selected_role_ids:
            parts.append("book leather")
        musk_selected = any(
            _candidate_group(choice.candidate) == "musk"
            for choice in choices
        )
        construction_note = (
            f"{', '.join(parts[:-1])}, and {parts[-1]} are kept close by a quiet carrier; "
            + (
                "one restrained musk stock supplies the skin halo."
                if musk_selected
                else "no musk material is used."
            )
        )
    else:
        construction_note = concept.construction_note
    if variant_roles:
        variant_labels = [
            row["slot_label"]
            for row in rows
            if row["slot"] in {role.role_id for role in variant_roles}
        ]
        if variant_labels:
            construction_note += " Request-specific adaptation: " + "; ".join(variant_labels) + "."
    request_payload = {
        "idea": clean_idea,
        "formula_name": name,
        "liquid_concentrate_ul_decimal": _decimal_text(liquid_total),
        "max_materials": int(max_materials),
        "must_preserve": list(must_preserve),
        "must_avoid": list(must_avoid),
        "previous_stock_ids": list(previous_stock_ids),
        "conversation_context": list(conversation_context)[-8:],
        "execution_strategy": interpretation["execution_strategy"],
        "appeal_mode": interpretation["appeal_mode"],
        "inventory_sha256": inventory.effective_inventory_sha256,
        "commercial_reference_registry_sha256": _reference_registry_sha256(),
    }
    formula = {
        "rows": rows,
        "separate_totals": totals,
        "active_mass_basis_state": "PARTIAL_OR_WITHHELD_PER_ROW",
        "exact_active_mass_established": False,
        "request_alignment_decimal": _decimal_text(round(coverage, 6)),
        "basis_state": (
            "SEPARATE_LIQUID_AND_SOLID_TOTALS"
            if int(totals["mass_total_mg"]) > 0
            else "LIQUID_STOCK_VOLUME_ONLY"
        ),
    }
    issues = list(holds)
    composition_limitations = _opaque_composition_limitations(rows, avoid)
    limitations = list(composition_limitations)
    if temporal_hypothesis is not None:
        limitations.append("TEMPORAL_BEHAVIOR_NOT_PHYSICALLY_VALIDATED")
    if interpretation["appeal_mode"] == "GLOBAL_CROWD_PLEASING":
        limitations.append("POPULATION_LIKING_NOT_ESTABLISHED")
    if reference_context is not None:
        if reference_context["status"] == "WITHHELD_NO_APPLICABLE_CURRENT_PANEL":
            limitations.append("NO_APPLICABLE_CURRENT_COMMERCIAL_REFERENCE_PANEL")
        else:
            limitations.append("DOCUMENTARY_REFERENCE_COMPARISON_ONLY")
    if any(not row["execution_ready"] for row in rows):
        issues.append("ONE_OR_MORE_ROWS_REQUIRE_STOCK_OR_DILUTION_BINDING")
    status = (
        "INVENTORY_GROUNDED_DESIGN_READY_WITH_HOLDS"
        if issues
        else "INVENTORY_GROUNDED_DESIGN_READY"
    )
    report = {
        "schema_version": "inventory-grounded-formula-design-v2",
        "status": status,
        "request_sha256": stable_payload_hash(request_payload),
        "formula_name": name,
        "concept_family": concept.concept_id if concept else "request_specific_abstract",
        "matched_descriptors": [concept.concept_id] if concept else [],
        "request_interpretation": interpretation,
        "inventory": {
            "snapshot_sha256": inventory.snapshot_sha256,
            "overlay_sha256": inventory.overlay_sha256,
            "completion_sha256": inventory.completion_sha256,
            "effective_inventory_sha256": inventory.effective_inventory_sha256,
            "inventory_text_sha256": _inventory_text_sha256(),
            "eligible_design_stock_count": len(candidates),
            "legacy_text_only_candidate_count": sum(candidate.legacy_text_only for candidate in candidates),
        },
        "composition_plan": {
            "method": "CONCEPT_ROLE_COMPILER_V3_CRITIC_REPAIR",
            "concept_id": concept.concept_id if concept else "request_specific_abstract",
            "construction": construction_note,
            "roles_requested": [role.role_id for role in roles],
            "roles_filled": [choice.role.role_id for choice in choices],
            "request_specific_repairs": repair_actions,
            "stop_rule": "STOP_WHEN_ALL_JUSTIFIED_ROLES_ARE_FILLED",
            "ingredient_count_is_objective": False,
            "character_basis": "COMPONENT_PROFILE_HYPOTHESIS_NOT_SENSORY_MEASUREMENT",
            "temporal_hypothesis": temporal_hypothesis,
            "commercial_reference_context": reference_context,
            "composition_uncertainty": {
                "requested_constituent_absence_state": (
                    "WITHHELD_OPAQUE_PRODUCTS"
                    if composition_limitations
                    else "NOT_REQUESTED_OR_NO_OPAQUE_CONFLICT"
                ),
                "limitations": composition_limitations,
                "meaning": (
                    "Row-level exclusions do not prove molecular absence inside selected "
                    "natural materials or proprietary bases."
                ),
            },
        },
        "initial_formula": formula,
        "optimized_formula": formula,
        "optimization": {
            "status": "STRUCTURAL_PLAN_COMPILED_AND_CRITIC_REPAIRED",
            "objective": "REQUEST_CONSTRAINT_AND_NONREDUNDANT_ROLE_FULFILMENT",
            "architecture_preserved": True,
            "iterations": 1,
            "initial_alignment_decimal": _decimal_text(round(coverage, 6)),
            "optimized_alignment_decimal": _decimal_text(round(coverage, 6)),
            "meaning": "The program compiled the brief into hard constraints and nonredundant functional roles; it did not optimize a beauty proxy.",
            "not_established": [
                "measured mixture character",
                "pleasantness",
                "personal liking",
                "population liking",
                "beauty",
                "sensory superiority",
            ],
        },
        "design_reasoning": [
            {
                "pass": "REQUEST_COMPILE",
                "result": "Hard quantities, units, exclusions, preservation goals, timing, and reference intent were compiled before selection.",
            },
            {
                "pass": "ROLE_PLAN",
                "result": (
                    f"{len(roles)} bounded roles were requested; optional adaptations were "
                    "added only for explicit temporal, wearability, or scene requirements."
                ),
            },
            {
                "pass": "INVENTORY_SELECTION",
                "result": (
                    f"{selected_count} unique current-inventory stocks were selected with "
                    "exact stock labels and alternatives retained."
                ),
            },
            {
                "pass": "DOSE_RECONCILIATION",
                "result": (
                    "Liquid stock volume was conserved exactly; solids remain separate; "
                    "moderate stock-strength compensation is heuristic and exact active mass is withheld where density is missing."
                ),
            },
            {
                "pass": "CRITIC_AND_AUTHORITY",
                "result": (
                    f"The critic found {len(set(issues))} execution issue(s) and "
                    f"{len(set(limitations))} evidence limitation(s); no sensory result or action authority was inferred."
                ),
            },
        ],
        "constraint_audit": {
            "state": "PASS_WITH_HOLDS" if issues else "PASS",
            "explicit_materials": list(explicit_materials),
            "mandatory_materials": list(mandatory),
            "prohibited_materials": list(interpretation["prohibited_materials"]),
            "avoid_constraints": list(avoid),
            "liquid_total_conserved": totals["liquid_total_ul"] == str(int(liquid_total)),
            "solid_mass_kept_separate": True,
            "material_limit_respected": selected_count <= int(max_materials),
            "holds": sorted(set(issues)),
            "limitations": sorted(set(limitations)),
        },
        "critic": {
            "state": "ACCEPTED_WITH_HOLDS" if issues else "ACCEPTED_AS_DESIGN_HYPOTHESIS",
            "issues": sorted(set(issues)),
            "limitations": sorted(set(limitations)),
            "stop_reason": "ALL_JUSTIFIED_ROLES_COVERED",
            "filler_rows_added": 0,
            "sensory_validation_required": True,
            "strongest_clue": construction_note,
        },
        "temporal_hypothesis": temporal_hypothesis,
        "commercial_reference_context": reference_context,
        "composition_uncertainty": {
            "requested_constituent_absence_state": (
                "WITHHELD_OPAQUE_PRODUCTS"
                if composition_limitations
                else "NOT_REQUESTED_OR_NO_OPAQUE_CONFLICT"
            ),
            "limitations": composition_limitations,
        },
        "requested_material_limit": int(max_materials),
        "selected_material_count": selected_count,
        "assistant_message": (
            f"I interpreted {name} as {concept.concept_id.replace('_', ' ') if concept else 'a request-specific perfume'} "
            f"and stopped at {selected_count} nonredundant materials (ceiling {max_materials}). "
            f"{construction_note} "
            "The formula is an inventory-grounded bench hypothesis; smell it before accepting any claimed improvement."
        ),
        "formula_action": "PROPOSAL_ONLY",
        "next_step": "Review the concise holds, then make the smallest practical pilot if you choose to compound it.",
        "inventory_modified": False,
        "formula_modified": False,
        "physical_compounding_performed": False,
        "pleasantness": None,
        "personal_liking": None,
        "population_liking": None,
        "beauty_score": None,
        "prohibited_objectives_used": [],
        **FALSE_ACTION_AUTHORITY,
    }
    return {**report, "design_sha256": stable_payload_hash(report)}


__all__ = ["compose_inventory_formula"]
