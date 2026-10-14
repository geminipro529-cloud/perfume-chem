"""Fragrance family structure for the composer's supporting layers.

Each family's top, heart and base words are transcribed from the Core Accord
sections of ``docs/fragrance_families_reference.md`` (line ranges below).  They
name the materials a perfumer reaches for in that family; they set no dose,
claim no odor intensity and never replace a note the brief asks for.  The
composer uses them only to choose which supporting layers a brief gets and
which materials those layers look for first.

The family is read from the brief: a family word it names ("fougere",
"chypre", "cologne"), otherwise the family of the first requested note in the
name and brief that belongs to one.  A brief with neither has no family, and
its layers stay as they were.

Words are written as owned stocks are named, so a layer's query finds them:
the reference's "Cedar" is "cedarwood" and "Guaiac wood" is "guaiacwood".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from engine.formulation_intelligence.floral_lattice import FloralSubtype


@dataclass(frozen=True, slots=True)
class FamilyStructure:
    family_id: str
    heading: str
    source_lines: str
    top: tuple[str, ...]
    heart: tuple[str, ...]
    base: tuple[str, ...]

    @property
    def words(self) -> tuple[str, ...]:
        return (*self.top, *self.heart, *self.base)

    def tier(self, note: str) -> tuple[str, ...]:
        return {"top": self.top, "heart": self.heart, "base": self.base}.get(note, ())


_SOURCE = "docs/fragrance_families_reference.md"

FAMILY_STRUCTURES: dict[str, FamilyStructure] = {
    family.family_id: family
    for family in (
        FamilyStructure(
            "floral_bouquet", "FLORAL BOUQUET (BRIGHT FLORAL / MULTI-FLORAL)", f"{_SOURCE}:95-97",
            ("aldehyde",), ("rose", "jasmine", "peony", "lily", "orchid"),
            ("musk", "sandalwood", "cedarwood"),
        ),
        FamilyStructure(
            "soft_floral", "SOFT FLORAL (ALDEHYDIC / POWDERY FLORAL)", f"{_SOURCE}:117-119",
            ("aldehyde", "bergamot", "neroli"), ("rose", "iris", "ionone", "jasmine", "ylang"),
            ("sandalwood", "musk", "vetiver", "amber"),
        ),
        FamilyStructure(
            "floral_amber", "FLORAL AMBER (FLORAL ORIENTAL)", f"{_SOURCE}:143-145",
            ("bergamot",), ("rose", "jasmine", "iris"),
            ("labdanum", "vanillin", "benzoin", "sandalwood", "musk"),
        ),
        FamilyStructure(
            "soft_amber", "SOFT AMBER (SOFT ORIENTAL)", f"{_SOURCE}:170-172",
            ("bergamot", "spice"), ("rose", "iris", "jasmine"),
            ("benzoin", "labdanum", "vanillin", "sandalwood", "musk"),
        ),
        FamilyStructure(
            "amber", "AMBER / ORIENTAL", f"{_SOURCE}:195-197",
            ("bergamot", "cinnamon", "cardamom", "pepper"), ("labdanum", "rose", "jasmine", "incense"),
            ("benzoin", "vanillin", "sandalwood", "patchouli", "musk"),
        ),
        FamilyStructure(
            "woody_amber", "WOODY AMBER (WOODY ORIENTAL)", f"{_SOURCE}:223-225",
            ("bergamot", "cardamom"), ("amber", "rose", "incense"),
            ("sandalwood", "cedarwood", "patchouli", "ambrox", "vetiver"),
        ),
        FamilyStructure(
            "woods", "WOODS (TRANSPARENT / CLEAN WOODS)", f"{_SOURCE}:250-252",
            ("bergamot", "pepper"), ("guaiacwood", "sandalwood", "cedarwood"),
            ("ambrox", "iso e super", "musk"),
        ),
        FamilyStructure(
            "chypre", "MOSSY WOODS (CHYPRE FAMILY)", f"{_SOURCE}:288-290",
            ("bergamot", "petitgrain"), ("oakmoss", "evernyl", "orris", "iris", "rose", "jasmine"),
            ("labdanum", "patchouli", "musk", "vetiver"),
        ),
        FamilyStructure(
            "dry_woods", "DRY WOODS (LEATHER / SMOKY)", f"{_SOURCE}:326-328",
            ("bergamot", "pepper"), ("cedarwood", "cypriol", "nagarmotha"),
            ("vetiver", "birch tar", "guaiacol", "patchouli", "amber"),
        ),
        # The reference gives two leather accords, traditional and modern
        # suede; a brief that names neither gets both.
        FamilyStructure(
            "leather", "LEATHER", f"{_SOURCE}:353-362",
            ("bergamot", "aldehyde", "citrus"), ("rose", "iris", "castoreum", "peach", "lactone"),
            ("birch tar", "labdanum", "oakmoss", "isobutyl quinoline", "suederal", "leather",
             "cedarwood", "musk"),
        ),
        FamilyStructure(
            "fougere", "FOUGÈRE (AROMATIC FOUGÈRE)", f"{_SOURCE}:400-402",
            ("bergamot", "lemon", "lavender", "geranium"), ("oakmoss", "evernyl", "geraniol", "hedione"),
            ("coumarin", "tonka", "musk", "vetiver", "cedarwood"),
        ),
        FamilyStructure(
            "citrus", "CITRUS / COLOGNE", f"{_SOURCE}:438-440",
            ("bergamot", "lemon", "lime", "grapefruit"), ("neroli", "petitgrain", "lavender"),
            ("musk", "cedarwood", "amber"),
        ),
        FamilyStructure(
            "green", "GREEN", f"{_SOURCE}:461-463",
            ("hexenol", "bergamot", "galbanum"), ("cyclamen", "violet leaf"),
            ("oakmoss", "evernyl", "cedarwood", "musk", "vetiver"),
        ),
        FamilyStructure(
            "aquatic", "WATER / AQUATIC / OCEANIC / OZONIC", f"{_SOURCE}:489-491",
            ("dihydromyrcenol", "calone", "bergamot"), ("cyclamen", "hedione", "helional"),
            ("ambrox", "cedarwood", "musk", "floralozone"),
        ),
        FamilyStructure(
            "fruity", "FRUITY", f"{_SOURCE}:517-519",
            ("ethyl 2-methylbutyrate", "hexyl acetate"), ("decalactone", "raspberry"),
            ("vanilla", "musk", "sandalwood"),
        ),
        FamilyStructure(
            "aromatic", "AROMATIC (HERBAL / SPICE AROMATIC)", f"{_SOURCE}:549-551",
            ("bergamot", "lavender", "sage", "rosemary"), ("geranium", "hedione", "cardamom"),
            ("cedarwood", "vetiver", "musk", "coumarin"),
        ),
        FamilyStructure(
            "gourmand", "GOURMAND", f"{_SOURCE}:580-582",
            ("ethyl maltol", "bergamot", "grapefruit"), ("heliotropin", "raspberry", "peach", "anisaldehyde"),
            ("patchouli", "vanillin", "coumarin", "tonka", "musk"),
        ),
        FamilyStructure(
            "iris", "IRIS / POWDERY / VIOLET", f"{_SOURCE}:610-612",
            ("bergamot", "galbanum"), ("irone", "irotyl", "iris"),
            ("sandalwood", "musk", "ambrette"),
        ),
        FamilyStructure(
            "incense", "INCENSE / RESINOUS / SPIRITUAL", f"{_SOURCE}:638-640",
            ("bergamot", "pepper", "cardamom"), ("olibanum", "myrrh"),
            ("labdanum", "benzoin", "guaiacol", "cashmeran", "cedarwood"),
        ),
        FamilyStructure(
            "tobacco", "TOBACCO / HAY / COUMARINIC", f"{_SOURCE}:660-662",
            ("bergamot", "rum"), ("rose", "geranium", "tobacco"),
            ("coumarin", "tonka", "safranate", "labdanum", "cedarwood", "musk"),
        ),
        FamilyStructure(
            "animalic", "ANIMALIC", f"{_SOURCE}:685",
            (), ("indole",), ("musk", "quinoline", "labdanum", "lactone"),
        ),
    )
}

# A family the brief names outright.  Note words that are also families
# ("leather", "amber") are read through the notes below instead, so a suede
# leather accent never turns a whole brief into a leather.
_FAMILY_WORDS: tuple[tuple[str, str], ...] = (
    ("fougere", "fougere"),
    ("fougère", "fougere"),
    ("chypre", "chypre"),
    ("eau de cologne", "citrus"),
    ("cologne", "citrus"),
    ("gourmand", "gourmand"),
    ("oriental", "amber"),
    ("woody amber", "woody_amber"),
    ("floral amber", "floral_amber"),
    ("soft amber", "soft_amber"),
    ("aquatic", "aquatic"),
    ("oceanic", "aquatic"),
    ("ozonic", "aquatic"),
)

# The family a requested note belongs to.  Notes that sit in many families
# (musk, spice, tea, fig, salt) name none.
_FACET_FAMILIES: Mapping[str, str] = {
    "citrus_peel": "citrus",
    "aromatic_lavender": "aromatic",
    "aromatic_herbs": "aromatic",
    "rose": "floral_bouquet",
    "white_floral": "floral_bouquet",
    "muguet_air": "floral_bouquet",
    "floral_bouquet": "floral_bouquet",
    "iris_violet": "iris",
    "iris_root": "iris",
    "iris_butter": "iris",
    "iris_cosmetic": "iris",
    "iris_transparent": "iris",
    "iris_woody": "iris",
    "violet_petals": "iris",
    "violet_powder": "iris",
    "powder": "iris",
    "green_leaf": "green",
    "violet_leaf": "green",
    "rain_water": "aquatic",
    "dry_wood": "woods",
    "creamy_wood": "woods",
    "vetiver_root": "woods",
    "patchouli_earth": "woods",
    "amber_mineral": "woody_amber",
    "oud_agarwood": "woody_amber",
    "animalic_fur": "animalic",
    "incense_resin": "incense",
    "opoponax_balsam": "amber",
    "smoke_char": "dry_woods",
    "leather_suede": "leather",
    "fougere_coumarin": "fougere",
    "moss_chypre": "chypre",
    "vanilla_balsam": "amber",
    "coffee_cocoa": "gourmand",
    "almond_nut": "gourmand",
    "tobacco_hay": "tobacco",
    "fruit": "fruity",
    "aldehydic": "soft_floral",
}


def _key(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9èé]+", " ", text.casefold()).split())


def _first_position(text: str, phrases: Sequence[str]) -> int | None:
    positions = [
        hit.start()
        for phrase in phrases
        for hit in [re.search(rf"(?<![a-z0-9]){re.escape(_key(phrase))}(?![a-z0-9])", text)]
        if hit is not None
    ]
    return min(positions, default=None)


# Flowers by name (the floral lattice's subtypes), for briefs whose flower has
# no facet of its own ("frangipani").  Iris and violet have their own family.
_FLOWER_WORDS = tuple(sorted(
    subtype.value.replace("_", " ")
    for subtype in FloralSubtype
    if subtype not in {FloralSubtype.IRIS, FloralSubtype.ORRIS, FloralSubtype.VIOLET}
))
_FLORAL_FAMILIES = frozenset({"floral_bouquet", "soft_floral"})
# Amber as a base accord (ambergris, amber, vanilla-balsam), not oud.
_AMBER_FACETS = frozenset({"amber_mineral", "vanilla_balsam"})


def brief_family(text: str, facets: Sequence[object]) -> FamilyStructure | None:
    """The family a brief's name and text call up, or None.

    ``facets`` are the brief's matched facet definitions (anything with
    ``facet_id`` and ``triggers``); ``text`` is the name and request as read
    (French note words already in English).  An amber-led brief that names a
    flower reads as a floral amber, as on the fragrance wheel.
    """

    key = _key(text)
    named = [
        (position, family_id)
        for word, family_id in _FAMILY_WORDS
        if (position := _first_position(key, (word,))) is not None
    ]
    if named:
        return FAMILY_STRUCTURES[min(named)[1]]
    placed = [
        (position, index, _FACET_FAMILIES[facet.facet_id])
        for index, facet in enumerate(facets)
        if facet.facet_id in _FACET_FAMILIES
        and (position := _first_position(key, facet.triggers)) is not None
    ]
    if not placed:
        return None
    _position, lead_index, family_id = min(placed)
    flowers = (
        any(_FACET_FAMILIES.get(facet.facet_id) in _FLORAL_FAMILIES for facet in facets)
        or _first_position(key, _FLOWER_WORDS) is not None
    )
    if facets[lead_index].facet_id in _AMBER_FACETS and flowers:
        return FAMILY_STRUCTURES["floral_amber"]
    return FAMILY_STRUCTURES[family_id]


# Words that also name the longer words they begin ("sandalwood").
_STEM_MARKERS = frozenset({"sandal", "cedar"})


def family_words_for(family: FamilyStructure, note: str, markers: Sequence[str]) -> tuple[str, ...]:
    """The family's words a layer with these markers looks for, own tier first."""

    def matches(word: str) -> bool:
        # Whole words only ("rain" is not in "petitgrain"); a marker that is
        # a word stem ("sandal") also matches the words it begins.
        return any(
            token == marker or token.rstrip("s") == marker
            or (marker in _STEM_MARKERS and token.startswith(marker))
            for token in word.split()
            for marker in markers
        )

    ordered = (*family.tier(note), *family.words)
    return tuple(dict.fromkeys(word for word in ordered if matches(word)))


# A family word no other role covers gets a small layer or accent of its own,
# filled only by a stock whose name carries that word ("family_birch_tar_layer"
# by Birch Tar Rectified); with no such stock the role is left out.
FAMILY_ROLE_PREFIX = "family_"
_FAMILY_ROLE_KINDS = ("_layer", "_accent")


def family_role_id(word: str, *, accent: bool = False) -> str:
    return FAMILY_ROLE_PREFIX + "_".join(_key(word).split()) + _FAMILY_ROLE_KINDS[accent]


def family_role_words(role_id: str) -> tuple[str, ...]:
    """The words a family role's stock must carry; empty for any other role."""

    if not role_id.startswith(FAMILY_ROLE_PREFIX) or not role_id.endswith(_FAMILY_ROLE_KINDS):
        return ()
    body = role_id[len(FAMILY_ROLE_PREFIX):].rsplit("_", 1)[0]
    return tuple(word for word in body.split("_") if word)


def names_family_words(vocabulary: frozenset[str], words: Sequence[str]) -> bool:
    """True when a stock's name words carry every word ("cedar" in Cedarwood).

    Single letters ("Iso E Super") are not name words.
    """

    words = [word for word in words if len(word) > 1]
    return bool(words) and all(
        any(token == word or (word in _STEM_MARKERS and token.startswith(word)) for token in vocabulary)
        for word in words
    )


__all__ = [
    "FAMILY_ROLE_PREFIX",
    "FAMILY_STRUCTURES",
    "FamilyStructure",
    "brief_family",
    "family_role_id",
    "family_role_words",
    "family_words_for",
    "names_family_words",
]
