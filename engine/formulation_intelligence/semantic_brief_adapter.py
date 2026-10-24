"""Compile free-form perfume ideas into reviewable structural design intent.

This module deliberately stops before material selection.  It translates a
plain-language request into sensory facets and functional roles while keeping
the original text, hard constraints, and authority ceiling visible.  The
facet ontology is a vocabulary bridge, not a collection of finished formulas:
it never assigns a stock dose and never claims that a descriptor will be
perceived in the finished perfume.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass, field, replace
from functools import lru_cache
from typing import Any, Iterable, Mapping, Sequence

from engine.formulation_intelligence import note_accord_specs
from engine.formulation_intelligence.contracts import EvidenceClass, ProvenanceRef
from engine.formulation_intelligence.family_structure import (
    FAMILY_ROLE_PREFIX,
    FamilyStructure,
    brief_family,
    family_role_id,
    family_words_for,
)
from engine.formulation_intelligence.literature_knowledge import retrieve_formulation_knowledge
from engine.formulation_intelligence.note_phrases import translate_note_phrases
from engine.formulation_intelligence.target_compiler import (
    AbstractionLevel,
    TargetAcceptance,
    TargetAcceptanceState,
    TargetBranch,
    TargetBrief,
    TargetMode,
    TargetRequestSource,
    TargetSourceSpan,
    TemporalTransformation,
    compile_target_intent,
)
from engine.research.composition_planner import ACCORD_SUPPORT_SEPARATOR, AccordPart
from engine.research.request_interpretation import plain_stock_name


def _clean(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(value).casefold()).strip()


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean(value)
        normalized = _key(text)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(text)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class FacetDefinition:
    facet_id: str
    triggers: tuple[str, ...]
    query_terms: tuple[str, ...]
    note: str
    function: str
    character_weights: tuple[tuple[str, float], ...]
    default_share: float
    max_raw_share: float | None = None
    knowledge_role_slot: str | None = None


@dataclass(frozen=True, slots=True)
class SemanticRole:
    role_id: str
    label: str
    note: str
    function: str
    query_terms: tuple[str, ...]
    character_weights: tuple[tuple[str, float], ...]
    share: float
    required: bool = True
    exact_material: str | None = None
    max_raw_share: float | None = None
    provenance: str = "PROMPT_DERIVED_FACET"
    knowledge_role_slot: str | None = None
    descriptor_requirement: str | None = None
    # The role's part in a cited note accord (note_accord_specs.py), or None.
    # Left out of the brief payload while None, so other briefs keep their
    # hashes. Not compared: a cited lead stays equal to the canonical facet
    # role a v5 Deep Compose refinement must find unchanged.
    accord: AccordPart | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        # A role read back from a JSON role plan carries its accord as a mapping.
        if isinstance(self.accord, Mapping):
            raw = self.accord
            object.__setattr__(self, "accord", AccordPart(
                note=raw["note"], part=raw["part"], job=raw.get("job"), function=raw["function"],
                source_ids=tuple(raw["source_ids"]),
                stocks=tuple((str(name), float(fraction)) for name, fraction in raw["stocks"]),
            ))


@dataclass(frozen=True, slots=True)
class SemanticBrief:
    schema_version: str
    request_sha256: str
    formula_name: str
    normalized_request: str
    family_neighborhoods: tuple[str, ...]
    facets: tuple[str, ...]
    expression_terms: tuple[str, ...]
    protected_recognizers: tuple[str, ...]
    forbidden_drift: tuple[str, ...]
    roles: tuple[SemanticRole, ...]
    target_intent: dict[str, Any]
    authority: str = "STRUCTURAL_DESIGN_ONLY"
    knowledge_context: dict[str, Any] = field(default_factory=dict)
    architecture_plan: dict[str, Any] = field(default_factory=dict)
    requested_fruits: tuple[str, ...] = ()
    # Natural-material note words in the request that no facet, fruit or named
    # material placed. Omitted from as_dict() while empty so existing briefs
    # keep their payload and design hashes.
    unmapped_requested_notes: tuple[str, ...] = ()
    # The fragrance family whose structure shaped the supporting layers
    # (docs/fragrance_families_reference.md heading), when the brief has one.
    fragrance_family: str | None = None
    # Roles of the note the brief calls "the star" (its lead stock, facet and
    # accord supports). Omitted from as_dict() while empty, like the fields
    # above, so briefs without a star keep their payload and design hashes.
    star_role_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for role in payload["roles"]:
            if role["accord"] is None:
                del role["accord"]
        if not self.unmapped_requested_notes:
            del payload["unmapped_requested_notes"]
        if self.fragrance_family is None:
            del payload["fragrance_family"]
        if not self.star_role_ids:
            del payload["star_role_ids"]
        return payload


# The entries below are descriptor-to-capability vocabulary.  They specify no
# complete formula and no preferred product.  Material selection remains a
# separate inventory-constrained optimization problem.
_FACETS: tuple[FacetDefinition, ...] = (
    FacetDefinition("citrus_peel", ("citrus", "bergamot", "lemon", "grapefruit", "mandarin", "orange peel", "yuzu"), ("citrus", "bergamot", "lemon", "grapefruit", "mandarin", "peel", "pith"), "top", "character", (("freshness", 1.0), ("radiance", .35)), .075, .16),
    FacetDefinition("aromatic_lavender", ("lavender", "fougere", "fougère", "aromatic herb", "herbal"), ("lavender", "aromatic", "herbal", "coumarin", "hay"), "heart", "character", (("freshness", .55), ("green", .45), ("floral", .35)), .13, .22),
    FacetDefinition("aromatic_herbs", ("herbs", "basil", "coriander", "rosemary", "minty", "mint", "sage", "thyme"), ("herbal", "basil", "coriander", "rosemary", "mint", "sage", "thyme"), "top", "character", (("green", .8), ("freshness", .65), ("spicy", .2)), .08, .14),
    FacetDefinition("rose", ("rose", "rosy"), ("rose", "geranium", "phenethyl", "damascone", "citronellol", "geraniol"), "heart", "character", (("floral", 1.0), ("radiance", .2)), .12, .20),
    FacetDefinition("white_floral", ("jasmine", "tuberose", "gardenia", "orange blossom", "neroli", "white floral"), ("jasmine", "tuberose", "gardenia", "orange blossom", "neroli", "indole", "hedione"), "heart", "character", (("floral", 1.0), ("radiance", .45), ("creamy", .2)), .13, .22),
    FacetDefinition("iris_violet", ("iris", "orris", "violet", "lipstick"), ("iris", "orris", "irone", "ionone", "violet", "carrot"), "heart", "character", (("powdery", 1.0), ("floral", .45), ("woody", .15)), .10, .18),
    FacetDefinition("muguet_air", ("muguet", "lily of the valley", "dewy floral", "watery floral"), ("muguet", "lily", "cyclamen", "floral air", "dewy"), "heart", "character", (("floral", .8), ("freshness", .55), ("transparency", .55)), .10, .18),
    FacetDefinition("green_leaf", ("green", "leaf", "leafy", "stem", "grass", "galbanum", "tomato leaf"), ("green", "leaf", "stem", "grass", "galbanum", "violet leaf"), "top", "character", (("green", 1.0), ("freshness", .45)), .075, .13),
    FacetDefinition("tea", ("tea", "matcha", "oolong", "earl grey"), ("tea", "tannin", "mate", "osmanthus", "leaf"), "heart", "character", (("green", .55), ("woody", .3), ("freshness", .25)), .085, .15),
    FacetDefinition("fig", ("fig", "fig leaf", "fig milk", "sap"), ("fig", "leaf", "sap", "milky", "lactone"), "heart", "character", (("green", .65), ("creamy", .55)), .105, .18),
    FacetDefinition("mineral_salt", ("mineral", "salt", "salty", "stone", "concrete", "metallic", "flint"), ("mineral", "salt", "stone", "ozone", "ambergris", "ambrox", "metallic"), "heart", "texture", (("transparency", .7), ("freshness", .45), ("woody", .2)), .075, .14),
    FacetDefinition("rain_water", ("rain", "wet pavement", "petrichor", "water", "aquatic", "marine", "ocean", "sea air", "sea spray", "sea breeze", "seaside", "sea"), ("rain", "wet", "petrichor", "marine", "aquatic", "ozone", "calone"), "top", "character", (("freshness", .9), ("transparency", .65), ("green", .25)), .07, .12),
    FacetDefinition("dry_wood", ("wood", "woods", "woody", "cedar", "driftwood", "pencil", "timber", "oak"), ("wood", "cedar", "vetiver", "patchouli", "clearwood", "timber"), "base", "structure", (("woody", 1.0), ("transparency", .2)), .15, .28),
    FacetDefinition("creamy_wood", ("sandalwood", "creamy wood", "milky wood", "soft wood"), ("sandalwood", "sandalore", "javanol", "creamy", "wood"), "base", "structure", (("woody", .85), ("creamy", .65), ("warmth", .25)), .15, .27),
    FacetDefinition("vetiver_root", ("vetiver", "rooty", "roots", "earthy root"), ("vetiver", "root", "earthy", "vetiveryl"), "base", "character", (("woody", .75), ("green", .35), ("smoky", .2)), .11, .20),
    FacetDefinition("patchouli_earth", ("patchouli", "earthy", "forest floor", "soil"), ("patchouli", "earth", "soil", "moss", "clearwood"), "base", "character", (("woody", .65), ("green", .25), ("smoky", .2)), .09, .16),
    FacetDefinition("amber_mineral", ("amber", "ambrox", "ambergris", "mineral amber", "dry amber"), ("ambrox", "ambergris", "amber", "mineral", "woody amber"), "base", "structure", (("woody", .65), ("warmth", .35), ("radiance", .25)), .12, .22),
    FacetDefinition("skin_musk", ("musk", "musky", "skin scent", "human skin", "body warmth", "warm skin"), ("musk", "skin", "ambrettolide", "brassylate", "habanolide", "exaltolide"), "base", "texture", (("creamy", .45), ("warmth", .35), ("transparency", .35)), .09, .16),
    FacetDefinition("animalic_fur", ("animalic", "clean fur", "warm fur", "fur accord", "civet", "castoreum"), ("animalic", "fur", "civet", "castoreum", "costus", "indole"), "base", "modifier", (("animalic", 1.0), ("warmth", .3), ("smoky", .15)), .035, .07),
    FacetDefinition("incense_resin", ("incense", "frankincense", "olibanum", "myrrh", "church", "cathedral", "resin"), ("incense", "olibanum", "frankincense", "myrrh", "opoponax", "resin"), "base", "character", (("smoky", .75), ("woody", .5), ("warmth", .25)), .09, .16),
    # Opoponax is a sweet balsamic resin, not a smoky incense: the incense role asks
    # for smoke, so an opoponax brief could never lead with the owned Opoponax
    # Resinoid. Character weights mirror that stock's own descriptors; share and cap
    # copy incense_resin so no new dose is introduced.
    FacetDefinition("opoponax_balsam", ("opoponax",), ("opoponax", "balsam", "resin"), "base", "character", (("warmth", .55), ("balsamic", .45), ("sweetness", .45), ("animalic", .2)), .09, .16),
    FacetDefinition("smoke_char", ("smoke", "smoky", "charred", "ember", "burnt", "ash"), ("smoke", "cade", "birch tar", "guaiacol", "char", "tobacco"), "base", "modifier", (("smoky", 1.0), ("woody", .35)), .035, .07),
    # Character weights mirror the owned agarwood stock's own descriptors;
    # share and cap copy leather_suede so no new dose is introduced.
    FacetDefinition("oud_agarwood", ("oud", "oudh", "aoud", "agarwood"), ("agarwood", "oud"), "base", "character", (("woody", .6), ("smoky", .45), ("animalic", .3), ("warmth", .3)), .065, .12),
    FacetDefinition("leather_suede", ("leather", "suede", "saddle", "book leather"), ("leather", "suede", "isobutyl quinoline", "birch tar", "saffron"), "base", "character", (("woody", .55), ("smoky", .45), ("animalic", .25)), .065, .12),
    # A fougere is lavender over coumarin and oakmoss: the family word asks for
    # the coumarin here and the moss through moss_chypre.
    FacetDefinition("fougere_coumarin", ("fougere", "fougère"), ("coumarin", "tonka"), "base", "structure", (("warmth", .45), ("sweetness", .25), ("powdery", .2)), .08, .14),
    FacetDefinition("moss_chypre", ("moss", "mossy", "oakmoss", "oak moss", "treemoss", "tree moss", "chypre", "forest moss", "fougere", "fougère"), ("moss", "evernyl", "oakmoss", "patchouli", "labdanum"), "base", "structure", (("green", .5), ("woody", .5), ("smoky", .15)), .07, .13),
    FacetDefinition("vanilla_balsam", ("vanilla", "vanillic", "balsamic", "benzoin", "tonka"), ("vanilla", "vanillin", "benzoin", "tonka", "coumarin", "balsam"), "base", "character", (("sweetness", .9), ("warmth", .55), ("creamy", .35)), .075, .14),
    FacetDefinition("coffee_cocoa", ("coffee", "cocoa", "chocolate", "roasted"), ("coffee", "cocoa", "roast", "pyrazine", "chocolate"), "heart", "character", (("warmth", .5), ("smoky", .4), ("sweetness", .25)), .06, .11),
    FacetDefinition("tobacco_hay", ("tobacco", "hay", "straw", "dry grass"), ("tobacco", "hay", "coumarin", "immortelle", "tea"), "base", "character", (("warmth", .45), ("woody", .35), ("smoky", .3)), .065, .12),
    FacetDefinition("spice", ("spice", "spicy", "pepper", "cardamom", "nutmeg", "cinnamon", "clove", "saffron", "ginger"), ("pepper", "cardamom", "nutmeg", "cinnamon", "clove", "saffron", "ginger", "spice"), "heart", "modifier", (("spicy", 1.0), ("warmth", .35)), .045, .09),
    FacetDefinition("fruit", ("fruit", "fruity", "pear", "apple", "peach", "plum", "berry", "mango", "pineapple"), ("fruit", "pear", "apple", "peach", "plum", "berry", "mango", "pineapple", "ester"), "top", "character", (("freshness", .45), ("sweetness", .4), ("radiance", .25)), .065, .12),
    # Coconut and apricot are notes of their own, not any fruit: only a stock whose
    # own description names the note may lead it (_FACET_DESCRIPTOR_REQUIREMENTS).
    # Shares and caps copy the fruit facet, so no new dose is introduced.
    FacetDefinition("coconut", ("coconut", "coconut milk", "coconut cream"), ("coconut", "lactone", "creamy", "milky"), "heart", "character", (("creamy", .7), ("sweetness", .4)), .065, .12),
    FacetDefinition("apricot", ("apricot", "apricots"), ("apricot", "peach", "lactone"), "heart", "character", (("sweetness", .45), ("freshness", .35), ("creamy", .25)), .065, .12),
    # Frangipani is a white flower with no owned stock design-ready under its own name:
    # only a stock whose own description names it may lead it.  Shares and weights copy
    # the white floral facet, so no new dose is introduced.
    FacetDefinition("frangipani", ("frangipani", "plumeria"), ("frangipani", "plumeria", "salicylate"), "heart", "character", (("floral", 1.0), ("radiance", .45), ("creamy", .2)), .13, .22),
    FacetDefinition("aldehydic", ("aldehydic", "sparkling aldehyde", "champagne", "soapy aldehyde", "laundry", "linen", "clean linen"), ("aldehyde", "sparkling", "wax", "linen"), "top", "modifier", (("radiance", .8), ("freshness", .4), ("transparency", .25)), .025, .06),
    FacetDefinition("powder", ("powder", "powdery", "cosmetic", "makeup"), ("powder", "iris", "ionone", "heliotropin", "musk"), "heart", "texture", (("powdery", 1.0), ("floral", .25)), .055, .11),
    FacetDefinition("almond_nut", ("almond", "marzipan", "biscuit", "nutty", "toasted nut"), ("almond", "benzaldehyde", "heliotropin", "tonka", "pyrazine", "biscuit"), "heart", "character", (("warmth", .55), ("sweetness", .35), ("powdery", .25)), .06, .11),
    FacetDefinition("floral_bouquet", ("floral", "flowers", "flower", "petal", "petals", "blossom", "bloom"), ("floral", "petal", "hedione", "phenethyl", "linalool", "blossom"), "heart", "character", (("floral", .9), ("radiance", .35)), .10, .18),
)

# Shares and character weights remain structural design heuristics, not values
# measured by the literature pack. Its role distinctions replace the umbrella
# only when the request actually calls for that profile.
_LITERATURE_FACETS = {
    "iris_root": FacetDefinition("iris_root", ("iris", "orris"), ("alpha irone", "irone", "orris", "iris recognizer", "alpha isomethyl ionone", "iris"), "heart", "character", (("powdery", .35), ("woody", .35)), .10, .18, "iris recognizer"),
    # "orris butter" is a note phrase, not a call for one bottle: it stays with
    # this facet instead of claiming the "Orris Butter 50% in EtOH" stock.
    "iris_butter": FacetDefinition("iris_butter", ("iris", "orris", "orris butter"), ("alpha irone", "irone", "orris", "iris recognizer", "waxy"), "heart", "character", (("powdery", .6), ("creamy", .4)), .10, .18, "iris recognizer"),
    "iris_cosmetic": FacetDefinition("iris_cosmetic", ("iris", "orris", "lipstick"), ("alpha irone", "irone", "orris", "iris recognizer", "methyl ionone gamma coeur", "alpha isomethyl ionone", "iris", "cosmetic"), "heart", "character", (("powdery", .8), ("floral", .3)), .10, .18, "iris recognizer"),
    "iris_transparent": FacetDefinition("iris_transparent", ("iris", "orris"), ("alpha irone", "irone", "orris", "iris recognizer", "alpha isomethyl ionone", "iris"), "heart", "character", (("powdery", .3), ("transparency", .65)), .10, .18, "iris recognizer"),
    "iris_woody": FacetDefinition("iris_woody", ("iris", "orris"), ("alpha irone", "irone", "orris", "iris recognizer", "methyl ionone gamma coeur", "alpha isomethyl ionone", "iris", "woody"), "heart", "character", (("powdery", .4), ("woody", .6)), .10, .18, "iris recognizer"),
    "violet_petals": FacetDefinition("violet_petals", ("violet",), ("violet petal recognizer", "beta ionone", "alpha ionone", "violet", "petal"), "heart", "character", (("floral", .7), ("powdery", .25)), .10, .18, "violet petal recognizer"),
    "violet_powder": FacetDefinition("violet_powder", ("violet",), ("violet petal recognizer", "beta ionone", "alpha ionone", "violet", "powder"), "heart", "character", (("powdery", .8), ("floral", .4)), .10, .18, "violet petal recognizer"),
    "violet_leaf": FacetDefinition("violet_leaf", ("violet leaf", "violet leaves"), ("violet leaf absolute", "parmavert", "violet leaf", "leaf"), "top", "character", (("green", .8), ("freshness", .3)), .04, .10),
}


# Facets only a stock whose own descriptors name the note may fill
# (material_capability_index._DESCRIPTOR_REQUIREMENTS).
_FACET_DESCRIPTOR_REQUIREMENTS = {
    "fruit": "fruit", "coconut": "coconut", "apricot": "apricot", "frangipani": "frangipani",
}

# A note the brief asks for as a nuance ("a hint of apricot", "a little apricot",
# "barely smoky") is a modifier: no accord of its own, at the share the smoke
# and animalic modifiers use.  One describing word may sit between the two.
_NUANCE_BEFORE = re.compile(
    r"(?:^| )(?:hint of|touch of|a little|whisper of|trace of|dash of|barely|slightly|faintly)"
    r"(?: [a-z]+)? $"
)
_NUANCE_SHARE, _NUANCE_MAX_RAW_SHARE = .035, .07


def _asked_as_nuance(facet: FacetDefinition, text_key: str, words: Sequence[str]) -> bool:
    """Whether every place the brief names this facet calls it a nuance."""
    seen = False
    for word in dict.fromkeys(_key(item) for item in words):
        if not word:
            continue
        for match in re.finditer(rf"(?:^| ){re.escape(word)}(?= |$)", text_key):
            seen = True
            start = match.start() + (text_key[match.start()] == " ")
            if not _NUANCE_BEFORE.search(text_key[:start]):
                return False
    return seen


def _as_asked(facet: FacetDefinition, text_key: str) -> FacetDefinition:
    if facet.function == "modifier":
        return facet
    words = (*facet.triggers, *(facet.query_terms if facet.facet_id == "fruit" else ()))
    if not _asked_as_nuance(facet, text_key, words):
        return facet
    return replace(
        facet,
        function="modifier",
        default_share=min(facet.default_share, _NUANCE_SHARE),
        max_raw_share=min(facet.max_raw_share or _NUANCE_MAX_RAW_SHARE, _NUANCE_MAX_RAW_SHARE),
    )


def facet_trigger_phrases() -> frozenset[str]:
    """Every phrase that calls up a brief facet of its own, lower-cased."""
    return frozenset(
        trigger.casefold()
        for facet in (*_FACETS, *_LITERATURE_FACETS.values(), _IRIS_TEXTURE)
        for trigger in facet.triggers
    )


# Requested identities that descriptor words cannot separate: AIMI and orris
# both carry "iris", so these name words come from the stock's own identity.
# "ionone" is a different word, so ionones stay distinct from irone/orris.
_IRIS_IDENTITY_WORDS = ("irone", "orris")
FACET_IDENTITY_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "oud_agarwood": ("agarwood",),
    "opoponax_balsam": ("opoponax",),
    **{facet_id: _IRIS_IDENTITY_WORDS for facet_id in _LITERATURE_FACETS if facet_id.startswith("iris_")},
    # The umbrella also answers violet-only briefs; see role_identity_requirement.
    "iris_violet": _IRIS_IDENTITY_WORDS,
}
_LAVENDER_IDENTITY_WORDS = ("lavender", "lavandin")
_IRIS_UMBRELLA_QUERY_TERMS = ("alpha irone", "irone", "orris", "iris", "ionone", "violet", "carrot")
_IRIS_TEXTURE = FacetDefinition("iris_root_texture", ("rooty iris",), ("root texture", "orivone", "earthy orris"), "heart", "texture", (("woody", .25),), .025, .06, "root texture")


_QUALIFIER_WEIGHTS: tuple[tuple[tuple[str, ...], tuple[tuple[str, float], ...]], ...] = (
    (("fresh", "bright", "brisk", "cool"), (("freshness", .9), ("radiance", .35))),
    (("transparent", "airy", "weightless", "sheer"), (("transparency", 1.0), ("radiance", .25))),
    (("warm", "sunlit", "golden"), (("warmth", .9),)),
    (("dry", "austere", "severe"), (("sweetness", -.75), ("woody", .35))),
    (("creamy", "milky", "soft"), (("creamy", .85), ("warmth", .25))),
    (("dark", "shadow", "nocturnal"), (("smoky", .45), ("woody", .35))),
    (("green", "verdant", "leafy"), (("green", .85), ("freshness", .25))),
    (("radiant", "luminous", "glowing"), (("radiance", .9), ("transparency", .3))),
)


_STOPWORDS = {
    "a", "an", "and", "as", "at", "be", "but", "by", "create", "for",
    "formula", "fragrance", "from", "in", "into", "is", "it", "make",
    "my", "new", "no", "not", "of", "on", "or", "perfume", "scent",
    "that", "the", "this", "to", "use", "with", "without",
}


def _phrase_present(text_key: str, phrase: str) -> bool:
    phrase_key = _key(phrase)
    return bool(phrase_key and re.search(rf"(?:^| ){re.escape(phrase_key)}(?: |$)", text_key))


def _facet_is_avoided(facet: FacetDefinition, avoid: Sequence[str]) -> bool:
    wrappers = ("any ", "all ", "the ")
    suffixes = (" material", " materials", " note", " notes", " accord")
    for raw in avoid:
        avoided = _key(raw)
        if not avoided:
            continue
        candidates = {avoided}
        for prefix in wrappers:
            if avoided.startswith(prefix):
                candidates.add(avoided[len(prefix) :])
        candidates.update(
            value[: -len(suffix)]
            for value in tuple(candidates)
            for suffix in suffixes
            if value.endswith(suffix)
        )
        if any(_key(trigger) in candidates for trigger in facet.triggers):
            return True
    return False


def _matched_facets(
    text: str, avoid: Sequence[str], knowledge_context: Mapping[str, Any],
) -> tuple[FacetDefinition, ...]:
    text_key = f" {_key(text)} "
    result: list[FacetDefinition] = []
    refined = [
        _LITERATURE_FACETS[profile]
        for profile in knowledge_context.get("profile_ids", ())
        if profile in _LITERATURE_FACETS
    ]
    iris_context = any(_phrase_present(text_key, term) for term in ("iris", "orris"))
    for facet in _FACETS:
        if facet.facet_id == "fruit":
            # A named fruit is not interchangeable with every other fruit in
            # the umbrella vocabulary. This is request parsing, not a chemical
            # alias or evidence that a stock reproduces the requested fruit.
            named = _requested_fruits(text)
            generic = replace(facet, triggers=("fruit", "fruity"))
            if _facet_is_avoided(generic, avoid):
                continue
            if named or any(_phrase_present(text_key, t) for t in generic.triggers):
                result.append(replace(facet, query_terms=(*named, "fruit", "fruity")))
            continue
        if _facet_is_avoided(facet, avoid):
            continue
        if any(_phrase_present(text_key, trigger) for trigger in facet.triggers):
            if facet.facet_id == "iris_violet" and refined:
                result.extend(item for item in refined if not _facet_is_avoided(item, avoid))
                # A violet profile answers the violet; iris named beside it
                # still needs its own recognizer role (the umbrella cannot
                # layer a second iris-family stock beside the violet's).
                iris_root = _LITERATURE_FACETS["iris_root"]
                if (
                    iris_context
                    and not any(item.facet_id.startswith("iris_") for item in refined)
                    and not _facet_is_avoided(iris_root, avoid)
                ):
                    result.append(iris_root)
                wants_root_texture = any(
                    _phrase_present(text_key, term) for term in ("root", "rooty", "roots", "earthy")
                )
                avoids_root_texture = any(
                    _phrase_present(str(item), term)
                    for item in avoid
                    for term in ("root", "rooty", "earthy", "camphor", "camphoraceous")
                )
                if "iris_root" in knowledge_context.get("profile_ids", ()) and wants_root_texture and not avoids_root_texture:
                    result.append(_IRIS_TEXTURE)
                continue
            if facet.facet_id == "iris_violet" and iris_context:
                result.append(replace(facet, query_terms=_IRIS_UMBRELLA_QUERY_TERMS))
                continue
            if facet.facet_id == "vetiver_root" and iris_context and not _phrase_present(text_key, "vetiver"):
                continue
            if facet.facet_id == "green_leaf" and any(item.facet_id == "violet_leaf" for item in result):
                continue
            if facet.facet_id == "floral_bouquet" and any(
                item.facet_id
                in {"rose", "white_floral", "iris_violet", "muguet_air", *_LITERATURE_FACETS}
                for item in result
            ):
                continue
            result.append(facet)
    return tuple(_as_asked(_focus_query_terms(facet, text_key, result), text_key) for facet in result)


# Facets whose vocabulary names several distinct flowers.  Each group is one
# material named two ways; when a brief names one group, the others are a
# different flower the brief did not ask for.
_NAMED_TERM_GROUPS: dict[str, tuple[tuple[str, ...], ...]] = {
    # Hedione is a material name, not a white-flower word: it never leads a
    # named flower's role.
    "white_floral": (("neroli", "orange blossom"), ("jasmine",), ("tuberose",), ("gardenia",), ("hedione",)),
    "iris_violet": (("iris", "orris"), ("violet",)),
}


def _focus_query_terms(
    facet: FacetDefinition, text_key: str, matched: Sequence[FacetDefinition],
) -> FacetDefinition:
    """Lead a facet's search with the words the brief actually used.

    This is request parsing only.  Literature profiles and the fruit facet keep
    their own ordering, and violet vocabulary stays as it was whenever the brief
    names violet, so violet petals, powder and leaf remain distinct.
    """

    if facet.facet_id == "fruit" or facet.knowledge_role_slot or facet in _LITERATURE_FACETS.values():
        return facet
    if _phrase_present(text_key, "violet") and any(
        "violet" in term for term in (*facet.triggers, *facet.query_terms)
    ):
        return facet
    # A word that calls up another requested facet belongs to that facet.
    foreign = {
        _key(trigger)
        for other in matched
        if other.facet_id != facet.facet_id
        for trigger in other.triggers
        if _phrase_present(text_key, trigger)
    }
    groups = _NAMED_TERM_GROUPS.get(facet.facet_id, ())
    named_groups = [group for group in groups if any(_phrase_present(text_key, term) for term in group)]
    unrequested = {term for group in groups if group not in named_groups for term in group} if named_groups else set()
    lead: list[str] = []
    for term in facet.query_terms:
        if _key(term) in foreign or not _phrase_present(text_key, term):
            continue
        lead.append(term)
        lead.extend(next((group for group in named_groups if term in group), ()))
    lead_terms = _dedupe(lead)
    rest = tuple(term for term in facet.query_terms if term not in lead_terms and term not in unrequested)
    query_terms = (*lead_terms, *rest)
    return facet if query_terms == facet.query_terms else replace(facet, query_terms=query_terms)


def role_identity_requirement(role_id: str, request: str = "") -> tuple[str, ...]:
    """Name words a requested-identity role's stock should carry, if any.

    The umbrella iris/violet facet carries the iris requirement only when the
    request literally names iris or orris, so violet-only briefs are unchanged.
    """
    if not role_id.startswith("facet_"):
        return ()
    facet_id = role_id[len("facet_") :]
    request_key = f" {_key(request)} "
    if facet_id == "iris_violet" and not any(
        _phrase_present(request_key, term) for term in ("iris", "orris")
    ):
        return ()
    # The lavender of a lavender or fougere brief is a stock that is lavender,
    # not any herbal material; an "herbal" brief keeps the open search.
    if facet_id == "aromatic_lavender":
        named = any(_phrase_present(request_key, term) for term in ("lavender", "fougere", "fougère"))
        return _LAVENDER_IDENTITY_WORDS if named else ()
    return FACET_IDENTITY_REQUIREMENTS.get(facet_id, ())


_FRUIT_NAMES = (
    "pear", "apple", "peach", "plum", "berry", "mango", "pineapple", "lychee",
    "raspberry", "cassis", "rhubarb", "grape", "passionfruit", "melon", "banana",
    "cherry", "quince",
)


def _requested_fruits(text: str) -> tuple[str, ...]:
    normalized = _key(text)
    normalized = re.sub(r"\blitchi\b", "lychee", normalized)
    # Juniper Berry is a botanical material name, not a berry-fruit request.
    normalized = re.sub(r"\bjuniper berr(?:y|ies)\b", "juniper", normalized)
    return tuple(name for name in _FRUIT_NAMES if _phrase_present(normalized, name))


def _mask_avoided_phrases(text: str, avoid: Sequence[str]) -> str:
    # Positive and negative request vocabulary share lexical aliases, never
    # stock aliases. A banned apple must not erase pineapple or a word fragment.
    masked = re.sub(r"\blitchi\b", "lychee", _key(text))
    rejected = (re.sub(r"\blitchi\b", "lychee", _key(item)) for item in avoid)
    for raw in sorted(rejected, key=len, reverse=True):
        if not raw:
            continue
        masked = re.sub(rf"(?<!\w){re.escape(raw)}(?!\w)", " ", masked)
    return _clean(masked)


_NATURAL_NAME_ENDING = re.compile(
    r"^(.*?) (?:eo|oil|absolute|abs|resinoid|concrete|co2|tincture|extract)(?: |$)"
)
_GRADE_WORDS = re.compile(r"\b(?:distilled|terpeneless|fcf|essential|expressed)\b")


@lru_cache(maxsize=1)
def _natural_note_vocabulary() -> tuple[str, ...]:
    """Natural-material name stems, longest first ("Vetiver EO" -> "vetiver").

    Request-word vocabulary only: a stem here says a user may name this note,
    not that any stock reproduces it.
    """
    from engine.ingredient_intelligence import _PROFILES
    from engine.name_utils import _ALIASES

    names = {*map(str, _PROFILES), *map(str, _ALIASES), *map(str, _ALIASES.values())}
    stems: set[str] = set()
    for name in names:
        text = _key(re.sub(r"\([^)]*\)", " ", name))
        text = " ".join(_GRADE_WORDS.sub(" ", text).split())
        match = _NATURAL_NAME_ENDING.match(text)
        if match and match.group(1).strip():
            stems.add(match.group(1).strip())
    return tuple(sorted(stems, key=lambda stem: (-len(stem), stem)))


def _unmapped_requested_notes(
    text: str,
    facets: Sequence[FacetDefinition],
    requested_fruits: Sequence[str],
    explicit_materials: Sequence[str],
) -> tuple[str, ...]:
    """Name natural-note words the request holds that no placed term covers.

    Every facet trigger is masked, matched or not: a trigger absent from the
    result was either covered by a more specific facet or avoided, and the
    text here is already avoid-masked.
    """
    masked = f" {_key(text)} "
    covered = [
        *(trigger for facet in (*_FACETS, *_LITERATURE_FACETS.values(), _IRIS_TEXTURE) for trigger in facet.triggers),
        *(term for facet in facets for term in facet.query_terms),
        *requested_fruits,
        *explicit_materials,
        *(trigger for triggers, _ in _QUALIFIER_WEIGHTS for trigger in triggers),
    ]
    for phrase in sorted({_key(item) for item in covered if _key(item)}, key=len, reverse=True):
        masked = re.sub(rf"(?<= ){re.escape(phrase)}(?= )", " ", masked)
    found: list[str] = []
    for stem in _natural_note_vocabulary():
        if _phrase_present(masked, stem):
            found.append(stem)
            masked = re.sub(rf"(?<= ){re.escape(stem)}(?= )", " ", masked)
    return tuple(found)


def _qualifier_weights(text: str, avoid: Sequence[str]) -> tuple[tuple[str, float], ...]:
    text_key = f" {_key(text)} "
    avoided = f" {' '.join(_key(item) for item in avoid)} "
    totals: dict[str, float] = {}
    for triggers, weights in _QUALIFIER_WEIGHTS:
        matched = any(_phrase_present(text_key, trigger) for trigger in triggers)
        rejected = any(_phrase_present(avoided, trigger) for trigger in triggers)
        if not matched or rejected:
            continue
        for dimension, weight in weights:
            totals[dimension] = totals.get(dimension, 0.0) + weight
    return tuple(sorted(totals.items()))


def _source_tokens(text: str) -> tuple[str, ...]:
    return _dedupe(
        token
        for token in _key(text).split()
        if len(token) >= 4 and token not in _STOPWORDS and not token.isdigit()
    )


# A perfumer builds every register from several materials in supporting
# roles, not one stock per note.  Each layer names a family and the own-odor
# descriptors a stock must carry to fill it (see
# ``material_capability_index._DESCRIPTOR_REQUIREMENTS``).  Query terms stay to
# one family word so the brief's qualities, not a stock's name, pick the
# material.  The family markers decide whether a prompt-derived role already
# covers that layer.  Accents are small modifiers: they may use a diluted
# trace material but never carry volume, and their own odor alone picks the
# stock (no query word that a stock's name could match).
#
# Order is priority: under a tight material limit the earlier layers stay.
_LayerSpec = tuple[
    str, str, str, str, float,
    tuple[str, ...], tuple[tuple[str, float], ...], tuple[str, ...], str, str | None,
]
_LAYER = "layer"
_ACCENT = "accent"
_NOTE_LAYERS: tuple[_LayerSpec, ...] = (
    (
        "base_wood_layer", "Base wood layer", "base", "base_wood", .07,
        ("wood",),
        (("woody", .8), ("creamy", .2)),
        ("wood", "cedar", "sandal", "vetiver", "patchouli", "timber", "guaiac"),
        _LAYER, None,
    ),
    (
        "heart_floral_layer", "Heart floral layer", "heart", "heart_floral", .045,
        ("floral",),
        (("floral", .75), ("radiance", .25)),
        ("floral", "flower", "rose", "jasmine", "muguet", "petal", "blossom", "neroli",
         "tuberose", "gardenia", "geranium", "hedione", "lily"),
        _LAYER, None,
    ),
    (
        "top_citrus_layer", "Top citrus layer", "top", "top_citrus", .035,
        ("citrus",),
        (("freshness", .65), ("radiance", .35)),
        ("citrus", "bergamot", "lemon", "mandarin", "grapefruit", "orange", "lime", "yuzu",
         "petitgrain"),
        _LAYER, None,
    ),
    (
        "base_musk_layer", "Base musk layer", "base", "base_musk", .06,
        ("musk",),
        (("creamy", .4), ("warmth", .3), ("transparency", .3)),
        ("musk", "ambrettolide", "habanolide", "exaltolide", "brassylate", "galaxolide"),
        _LAYER, None,
    ),
    (
        "base_amber_layer", "Base amber layer", "base", "base_amber", .05,
        ("amber",),
        (("warmth", .45), ("woody", .35), ("radiance", .2)),
        ("amber", "ambrox", "ambergris", "labdanum"),
        # A fresh or light brief keeps its warmth out of the drydown.
        _LAYER, "light",
    ),
    (
        "top_green_layer", "Top green aromatic layer", "top", "top_green", .025,
        ("green",),
        (("green", .6), ("freshness", .4)),
        ("green", "leaf", "herb", "herbal", "aromatic", "basil", "mint", "galbanum",
         "rosemary", "sage", "thyme", "lavender"),
        _LAYER, None,
    ),
    (
        "heart_powder_layer", "Heart powder texture", "heart", "heart_powder", .025,
        ("powder",),
        (("powdery", .7), ("creamy", .15), ("floral", .15)),
        ("powder", "iris", "orris", "violet", "ionone", "irone", "heliotropin"),
        _LAYER, "light",
    ),
    (
        "base_resin_layer", "Base balsamic resin layer", "base", "base_resin", .045,
        ("balsam", "resin"),
        (("warmth", .55), ("sweetness", .35), ("smoky", .1)),
        ("resin", "balsam", "benzoin", "labdanum", "opoponax", "olibanum", "incense", "myrrh",
         "vanilla", "tonka"),
        _LAYER, "light",
    ),
    (
        "heart_creamy_texture", "Heart creamy texture", "heart", "heart_creamy", .02,
        ("creamy",),
        (("creamy", .7), ("sweetness", .15), ("warmth", .15)),
        ("creamy", "milky", "lactone", "lactonic", "coconut", "fig milk"),
        _LAYER, "light",
    ),
    (
        "heart_spice_accent", "Heart spice accent", "heart", "heart_spice", .012,
        (),
        (("spicy", .7), ("warmth", .3)),
        ("spice", "spicy", "pepper", "cardamom", "nutmeg", "cinnamon", "clove", "saffron",
         "ginger"),
        _ACCENT, "light",
    ),
    (
        "top_sparkle_accent", "Top sparkle accent", "top", "top_sparkle", .012,
        (),
        (("radiance", .6), ("freshness", .4)),
        ("aldehyde", "aldehydic", "sparkling", "fruit", "fruity", "ester", "pear", "apple",
         "berry", "cassis"),
        _ACCENT, None,
    ),
    (
        "base_shadow_accent", "Base shadow accent", "base", "base_shadow", .012,
        (),
        (("smoky", .6), ("animalic", .2), ("woody", .2)),
        ("smoke", "smoky", "leather", "suede", "animalic", "tar", "cade", "birch", "fur",
         "castoreum", "civet", "guaiacol"),
        _ACCENT, "not_warm",
    ),
    (
        "heart_watery_accent", "Heart watery accent", "heart", "heart_watery", .012,
        (),
        (("freshness", .5), ("transparency", .5)),
        ("aquatic", "marine", "water", "watery", "rain", "ozone", "ozonic", "calone", "sea"),
        _ACCENT, "not_light",
    ),
)
LAYER_PROVENANCE = {
    "base": "LAYERED_BASE_ARCHITECTURE",
    "top": "LAYERED_TOP_ARCHITECTURE",
    "heart": "LAYERED_HEART_ARCHITECTURE",
}
ACCENT_PROVENANCE = "ACCENT_LAYER"
# Supporting, never dominant: a layer may not take spare volume that capped
# rows leave behind, and an accent stays a nuance.
LAYER_MAX_RAW_SHARE = .08
ACCENT_MAX_RAW_SHARE = .025
# On a fresh or light brief the base layers only underline the opening: at
# 8% each a cologne's wood and musk outweighed its citrus.
LIGHT_BASE_LAYER_MAX_RAW_SHARE = .03
# A family material's own role: smaller than a generic layer, since a family
# usually places several in one register.
_FAMILY_LAYER_SHARE = .03
_FAMILY_ACCENT_SHARE = .012
# How strongly each layer leans toward the requested notes' character.
_BRIEF_ECHO = .35
# Layers together never outweigh the brief: past this share of the formula
# they are scaled down together.
_LAYER_SHARE_BUDGET = .30
_LIGHT_BRIEF = re.compile(
    r"\b(?:fresh|cologne|aquatic|citrus|light|transparent|clean|airy|sheer|spring|summer|dewy|delicate)\b"
)
# The citrus top layer opens a formula only where citrus belongs: the brief
# names a citrus or a cologne, or its family is built on one.  Per
# docs/fragrance_families_reference.md, those families are the chypre (bergamot
# is the first of its three pillars), the citrus family, the green (its summary
# table names bergamot as a core material; "a lighter, more modern
# interpretation of the Chypre structure"), the fougere (its core accord opens
# on bergamot and lemon) and the aromatic ("often accompanied by a citrus
# top").  Given to every brief, one citrus stock opened nearly every formula:
# Red Mandarin EO was in 26 of the 34 duel and benchmark formulas.  Without the
# layer, the family's other top words (pepper, cardamom, galbanum) open it.
_CITRUS_BRIEF_WORDS = (
    "neroli", "cologne", "tangerine", "clementine", "kumquat", "citron", "cedrat",
    "pomelo", "bigarade", "zest", "hesperidic", "lemonade", "lemongrass",
)
_CITRUS_LED_FAMILIES = frozenset({"chypre", "citrus", "green", "fougere", "aromatic"})
_CITRUS_LAYER_MARKERS: tuple[str, ...] = next(
    spec[7] for spec in _NOTE_LAYERS if spec[0] == "top_citrus_layer"
)
# A citrus the brief names: whole words, with a plural or adjective ending
# ("limes", "zesty"), so "limestone" and "citronellol" name none.
_CITRUS_WORD = re.compile(
    r"(?<![a-z0-9])("
    + "|".join(re.escape(word) for word in (*_CITRUS_LAYER_MARKERS, *_CITRUS_BRIEF_WORDS))
    + r")(?:s|es|y)?(?![a-z0-9])"
)
_WARM_BRIEF = re.compile(r"\b(?:warm|dark|deep|resin|resinous|amber|incense|balsam|balsamic|vanilla|oriental|evening|rich|leather|smoky|tobacco)\b")

# A brief that names a spice gets one spice that lasts.  The spice facet's
# stock is a visible pepper or cardamom, gone by the drydown (Pink Pepper EO
# 0.505 Pa, Black Pepper EO 0.375 Pa); this role takes only an owned spice
# below the release gate's long-lasting vapour pressure, which the solver
# checks (formula_solver._is_lasting_spice).  Whole words, with a plural,
# adjective or past-participle ending ("cloves", "gingery", "spiced",
# "peppered"), so "allspice" is its own word.
LASTING_SPICE_PROVENANCE = "LASTING_SPICE"
_LASTING_SPICE_WORDS = (
    "spice", "spicy", "pepper", "peppery", "peppercorn", "pink pepper", "black pepper",
    "saffron", "cardamom", "cinnamon", "clove", "nutmeg", "mace", "ginger", "cumin",
    "coriander", "allspice", "pimento", "cassia", "caraway", "star anise",
)
_LASTING_SPICE_WORD = re.compile(
    r"(?<![a-z0-9])("
    + "|".join(re.escape(word) for word in sorted(_LASTING_SPICE_WORDS, key=len, reverse=True))
    + r")(?:s|es|y|ed|d)?(?![a-z0-9])"
)
# Kenny's four pepper references carry Safraleine 10% at 1.9-2.8% of raw.
_LASTING_SPICE_SHARE, _LASTING_SPICE_MAX_RAW_SHARE = .025, .03


def _lasting_spice_role(text: str, avoid: Sequence[str]) -> SemanticRole | None:
    """The brief's one lasting spice role, or None when it names no spice it wants.

    A brief whose must_avoid turns spice down ("no spice", "spicy notes")
    gets none, and an avoided phrase ("pink pepper") names no spice.
    """

    for raw in avoid:
        item = _key(raw)
        for prefix in ("any ", "all ", "the ", "no "):
            item = item.removeprefix(prefix)
        for suffix in (" materials", " material", " notes", " note", " accord"):
            item = item.removesuffix(suffix)
        if item in {"spice", "spices", "spicy", "spiced"}:
            return None
    words = tuple(dict.fromkeys(
        match.group(1) for match in _LASTING_SPICE_WORD.finditer(_mask_avoided_phrases(text, avoid))
    ))
    if not words:
        return None
    return SemanticRole(
        role_id="lasting_spice",
        label="Lasting spice",
        note="base",
        function="modifier",
        query_terms=_dedupe((*words, "spice", "spicy")),
        character_weights=(("spicy", 1.0), ("warmth", .35)),
        share=_LASTING_SPICE_SHARE,
        required=False,
        max_raw_share=_LASTING_SPICE_MAX_RAW_SHARE,
        provenance=LASTING_SPICE_PROVENANCE,
        descriptor_requirement="heart_spice",
    )


def _names_marker(text: str, markers: Sequence[str]) -> bool:
    """True when a word of the text starts with one of the markers ("resinous")."""

    words = _key(text).split()
    return any(word.startswith(marker) for word in words for marker in markers if " " not in marker)


# A citrus word the brief turns down in its own words ("not citrusy",
# "nothing like a cologne") names no citrus.
_NEGATED_BEFORE = re.compile(
    r"(?:^| )(?:not|non|no|nor|never|without|unlike|nothing like|anything but)"
    r"(?: (?:a|an|the|any|too|so|very|overly))* $"
)


def _avoided_citrus(avoid: Sequence[str]) -> set[str]:
    """The citrus words must_avoid names, whatever their wrapper or ending ("any colognes")."""

    words: set[str] = set()
    for raw in avoid:
        item = _key(translate_note_phrases(raw))
        for prefix in ("any ", "all ", "the ", "no "):
            item = item.removeprefix(prefix)
        for suffix in (" materials", " material", " notes", " note", " accord"):
            item = item.removesuffix(suffix)
        if match := _CITRUS_WORD.fullmatch(item):
            words.add(match.group(1))
    return words


def _citrus_belongs(text: str, avoid: Sequence[str], family: FamilyStructure | None) -> bool:
    """True when a citrus opens this brief: its family is built on one, or it names one.

    A citrus word counts only where the brief wants it: not one must_avoid
    rejects ("cologne" also rejects "colognes"), and not one the brief turns
    down itself ("not citrusy").
    """

    if family is not None and family.family_id in _CITRUS_LED_FAMILIES:
        return True
    rejected = _avoided_citrus(avoid)
    text = _mask_avoided_phrases(text, avoid)
    return any(
        match.group(1) not in rejected and not _NEGATED_BEFORE.search(text[: match.start()])
        for match in _CITRUS_WORD.finditer(text)
    )


def _family_word_layer(family: FamilyStructure, note: str, word: str) -> tuple[Any, ...] | None:
    """The layer or accent whose odor a family word names ("cardamom": spice)."""

    return next((spec for spec in _NOTE_LAYERS if word in family_words_for(family, note, spec[7])), None)


def _family_word_avoided(family: FamilyStructure, note: str, word: str, avoid: Sequence[str]) -> bool:
    """A family word is avoided by name or with its layer's odor ("spice" keeps cardamom out)."""

    spec = _family_word_layer(family, note, word)
    markers = (word, *(spec[7] if spec is not None else ()))
    return any(marker in _key(item) for item in avoid for marker in markers)


def _note_layers(
    *,
    complexity_text: str,
    roles: Sequence["SemanticRole"],
    avoid: Sequence[str],
    qualifier_weights: tuple[tuple[str, float], ...] = (),
    family: FamilyStructure | None = None,
) -> tuple["SemanticRole", ...]:
    """Supporting top, heart and base layers the prompt-derived roles leave open.

    Layers are optional roles: a layer with no eligible owned stock is simply
    left out.  They never replace a requested facet and carry modest shares so
    the requested character still leads.  Returned in priority order.

    With a fragrance family, a layer looks first for the family's own
    materials (a fougere's citrus layer for bergamot and lemon), and a layer
    the family's structure has no place for is left out unless the brief
    names its odor: a fougere gets no creamy lactone or powder layer.  Each
    family material no role or layer already looks for first gets a role of
    its own, sized like the layer or accent its odor belongs to (an aldehyde
    stays an accent), so the family's structure replaces the generic layers
    rather than shrinking the formula.
    """

    avoided = {_key(item) for item in avoid}

    def is_avoided(markers: Sequence[str]) -> bool:
        return any(
            marker in value
            for value in avoided
            for marker in markers
        )

    def role_text(role: "SemanticRole") -> str:
        return " ".join((role.role_id, *role.query_terms, role.exact_material or "")).casefold()

    # A named stock can sit in any register, so it counts for every note.
    # Top and heart families are checked against every requested note (a
    # requested rain note already gives the heart its water); base families
    # only against base notes, since heart facets borrow base words such as
    # "musk" for powder.
    anchor_terms = [role_text(role) for role in roles if role.exact_material is not None]
    every_note = [role_text(role) for role in roles]
    note_terms = {
        "top": every_note,
        "heart": every_note,
        "base": [role_text(role) for role in roles if role.note == "base"] + anchor_terms,
    }
    warm = bool(_WARM_BRIEF.search(complexity_text))
    light = bool(_LIGHT_BRIEF.search(complexity_text)) and not warm
    # The requested notes' own character, so a rose brief's citrus layer
    # leans floral and a smoky brief's leans dry: layers echo the brief.
    brief_vector: dict[str, float] = {}
    for role in roles:
        if role.provenance != "PROMPT_DERIVED_FACET":
            continue
        for dimension, weight in role.character_weights:
            if weight > 0:
                brief_vector[dimension] = brief_vector.get(dimension, 0.0) + weight
    strongest = max(brief_vector.values(), default=0.0)

    def skipped(skip: str | None) -> bool:
        return (
            (skip == "light" and light)
            or (skip == "not_warm" and not warm)
            or (skip == "not_light" and not light)
        )

    def layer_role(
        role_id: str, label: str, note: str, terms: tuple[str, ...],
        weights: tuple[tuple[str, float], ...], share: float, kind: str,
        requirement: str | None,
    ) -> SemanticRole:
        merged = dict(weights)
        for dimension, weight in qualifier_weights:
            # The brief's qualities (dry, dark, creamy, clean) steer which
            # stock fills each layer, so every register follows the brief.
            merged[dimension] = merged.get(dimension, 0.0) + weight * .5
        for dimension, weight in brief_vector.items():
            merged[dimension] = merged.get(dimension, 0.0) + weight / strongest * _BRIEF_ECHO
        accent = kind == _ACCENT
        light_base = light and note == "base" and not accent
        if light_base:
            # A light brief's base leans sheer, not heavy.
            merged["transparency"] = merged.get("transparency", 0.0) + .4
        return SemanticRole(
            role_id=role_id,
            label=label,
            note=note,
            function="modifier" if accent else ("structure" if note == "base" else "texture"),
            query_terms=terms,
            character_weights=tuple(sorted(merged.items())),
            share=share,
            required=False,
            max_raw_share=(
                ACCENT_MAX_RAW_SHARE if accent
                else LIGHT_BASE_LAYER_MAX_RAW_SHARE if light_base
                else LAYER_MAX_RAW_SHARE
            ),
            provenance=ACCENT_PROVENANCE if accent else LAYER_PROVENANCE[note],
            descriptor_requirement=requirement,
        )

    citrus_belongs = _citrus_belongs(complexity_text, avoid, family)
    # The lead words of layers left out for that reason: they get no family
    # role either, so the family's bergamot does not come back as a role of
    # its own and take the citrus layer's place.
    withheld: set[str] = set()
    layers: list[SemanticRole] = []
    for role_id, label, note, requirement, share, terms, weights, markers, kind, skip in _NOTE_LAYERS:
        if is_avoided(markers) or skipped(skip):
            continue
        covered = any(marker in text for text in note_terms[note] for marker in markers)
        if covered and requirement != "base_wood":
            continue
        family_terms = family_words_for(family, note, markers) if family is not None else ()
        if (
            family is not None and not family_terms and not _names_marker(complexity_text, markers)
            # A citrus the brief names opens it in any family ("a pear with clementine").
            and not (role_id == "top_citrus_layer" and citrus_belongs)
        ):
            continue
        if family_terms and kind == _ACCENT:
            # The family's own materials for this nuance get accent roles below.
            continue
        if covered:
            # A contrasting wood looks for the family's other woods, not the
            # ones the brief's own wood already asks for.
            family_terms = tuple(
                word for word in family_terms
                if not any(_phrase_present(_key(text), word) for text in note_terms[note])
            )
        if family_terms:
            terms = tuple(dict.fromkeys((*family_terms, *terms)))
        if covered:
            # A wood-led brief gets a second, contrasting wood family; the
            # solver's family buckets keep it from repeating the first one.
            role_id, label = "base_wood_contrast", "Contrasting base wood"
        if role_id == "top_citrus_layer" and not citrus_belongs:
            withheld.add(terms[0])
            continue
        layers.append(layer_role(role_id, label, note, terms, weights, share, kind, requirement))
    if family is None:
        return tuple(layers)

    # The family's materials no role asks for and no layer looks for first.
    asked = " ".join(_key(text) for text in every_note)
    first_terms = {layer.query_terms[0] for layer in layers if layer.query_terms} | withheld
    placed: set[str] = set()
    for note in ("top", "heart", "base"):
        for word in family.tier(note):
            if (
                word in placed or word in first_terms or _phrase_present(asked, word)
                or _family_word_avoided(family, note, word, avoid)
            ):
                continue
            # Sized like the layer or accent whose odor the word names, and
            # avoided or skipped with it; a word no layer names is a layer.
            spec = _family_word_layer(family, note, word)
            if spec is not None:
                *_, weights, _markers, kind, skip = spec
                if skipped(skip):
                    continue
            else:
                weights, kind = (), _LAYER
            placed.add(word)
            accent = kind == _ACCENT
            layers.append(layer_role(
                family_role_id(word, accent=accent), f"{family.heading} {note}: {word}", note, (word,),
                weights, _FAMILY_ACCENT_SHARE if accent else _FAMILY_LAYER_SHARE, kind, None,
            ))
    return tuple(layers)


def _named_as_note_only(material: str, request_key: str) -> bool:
    plain = plain_stock_name(material)
    return bool(plain) and _phrase_present(request_key, plain) and not _phrase_present(request_key, material)


# "Pink pepper the star of ...", "Pink pepper signature for a man, the star
# from opening ...": the note named last before the marker is the star.
# "The star is oud" names it after the marker instead.
_STAR_MARKER = re.compile(r" the star(?: is)? ")


def _star_role_ids(
    roles: Sequence[SemanticRole],
    request: str,
    facets: Sequence[FacetDefinition],
) -> tuple[str, ...]:
    """Role ids of the note a brief calls "the star", or () when it names none.

    A note is a stock the brief names (by its own or its plain name) or the
    trigger of a requested facet.  When nothing the brief requests sits next
    to the marker, no note is the star: the composer never guesses one.
    """

    key = f" {_key(request)} "
    marker = _STAR_MARKER.search(key)
    if marker is None:
        return ()
    after = marker.group(0).endswith(" is ")
    triggers = {f"facet_{facet.facet_id}": facet.triggers for facet in facets}
    found: list[tuple[int, str]] = []
    for role in roles:
        if role.exact_material is not None:
            phrases: tuple[str, ...] = (role.exact_material, plain_stock_name(role.exact_material))
        elif role.provenance == "PROMPT_DERIVED_FACET":
            phrases = triggers.get(role.role_id, ())
        else:
            continue
        for phrase in phrases:
            phrase_key = _key(phrase or "")
            if not phrase_key:
                continue
            for match in re.finditer(rf"(?<= ){re.escape(phrase_key)}(?= )", key):
                if after and match.start() >= marker.end() - 1:
                    found.append((-match.start(), role.role_id))
                elif not after and match.end() <= marker.start():
                    found.append((match.end(), role.role_id))
    if not found:
        return ()
    nearest = max(position for position, _ in found)
    star = {role_id for position, role_id in found if position == nearest}
    return tuple(
        role.role_id
        for role in roles
        if role.role_id in star or accord_lead_role_id(role) in star
    )


def _roles(
    *,
    formula_name: str,
    request: str,
    facets: Sequence[FacetDefinition],
    explicit_materials: Sequence[str],
    qualifier_weights: tuple[tuple[str, float], ...],
    maximum: int,
    target_count: int | None,
    avoid: Sequence[str] = (),
    family: FamilyStructure | None = None,
) -> tuple[SemanticRole, ...]:
    complexity_text = _key(f"{formula_name} {request}")
    ordinary_target = max(6, len(facets) + 5)
    if re.search(r"\b(?:exceptionally detailed|panoramic|high definition)\b", complexity_text):
        ordinary_target = max(ordinary_target, 16)
    elif re.search(r"\b(?:expanded|complex|detailed|layered|multi floral|broad)\b", complexity_text):
        ordinary_target = max(ordinary_target, 12)
    role_target = min(
        maximum,
        target_count if target_count is not None else ordinary_target,
    )
    roles: list[SemanticRole] = []
    for index, material in enumerate(_dedupe(explicit_materials), start=1):
        roles.append(
            SemanticRole(
                role_id=f"explicit_anchor_{index}",
                label=f"Explicit brief anchor: {material}",
                note="heart",
                function="character",
                query_terms=(material,),
                character_weights=(),
                share=.12,
                exact_material=material,
                provenance="EXPLICIT_REQUEST_MATERIAL",
            )
        )

    filled_knowledge_slots: set[str] = set()
    request_key = f" {_key(f'{formula_name} {request}')} "
    # A stock the brief names only as its note ("pink pepper" for Pink Pepper
    # EO) is the note's lead, not the whole note: its facet still adds support.
    explicit_keys = tuple(
        f" {_key(material)} "
        for material in explicit_materials
        if not _named_as_note_only(material, request_key)
    )
    anchors = {f" {_key(role.exact_material or '')} ": role for role in roles}
    supported_anchors: set[str] = set()
    # The note each supported anchor leads, for its cited accord.
    anchor_facets: dict[str, FacetDefinition] = {}
    for facet in facets:
        if len(roles) >= maximum:
            break
        # A facet called up only by the name of an explicit anchor would fill
        # the same note twice.  Recognizer slots and fruit keep their roles.
        if not facet.knowledge_role_slot and facet.facet_id != "fruit":
            matched_triggers = [t for t in facet.triggers if _phrase_present(request_key, t)]
            # An anchor that already carries the identity the facet must name
            # (Lavender EO for the lavender of a fougere) is that note: a second
            # stock of the same identity could never be placed beside it.
            identity = role_identity_requirement(f"facet_{facet.facet_id}", request_key)
            if matched_triggers and (
                any(_phrase_present(name, word) for name in explicit_keys for word in identity)
                or all(
                    any(_phrase_present(name, t) for name in explicit_keys) for t in matched_triggers
                )
            ):
                # The anchor leads this note; like every requested note it
                # keeps one supporting material of the note's own odor.
                anchor = next((
                    anchors[name] for name in explicit_keys
                    if any(_phrase_present(name, t) for t in (*identity, *matched_triggers))
                ), None)
                if (
                    anchor is not None
                    and target_count is None
                    and facet.function in _ACCORD_FUNCTIONS
                    and anchor.role_id not in supported_anchors
                    and len(roles) < maximum - _DEEP_COMPOSE_RESERVE
                ):
                    supported_anchors.add(anchor.role_id)
                    anchor_facets[anchor.role_id] = facet
                    roles.append(_anchor_support(anchor, facet))
                continue
        # A rooty-and-transparent iris has one recognizer with two requested
        # qualities, not two mandatory copies of the same recognizer role.
        if facet.knowledge_role_slot in filled_knowledge_slots:
            continue
        if facet.knowledge_role_slot:
            filled_knowledge_slots.add(facet.knowledge_role_slot)
        roles.append(
            SemanticRole(
                role_id=f"facet_{facet.facet_id}",
                label=f"{facet.facet_id.replace('_', ' ').title()} expression",
                note=facet.note,
                function=facet.function,
                query_terms=facet.query_terms,
                character_weights=facet.character_weights,
                share=facet.default_share,
                max_raw_share=facet.max_raw_share,
                knowledge_role_slot=facet.knowledge_role_slot,
                descriptor_requirement=_FACET_DESCRIPTOR_REQUIREMENTS.get(facet.facet_id),
            )
        )
    lasting_spice = _lasting_spice_role(f"{formula_name} {request}", avoid)
    lasting_spice_at = len(roles)

    # Functional coverage is a hard architecture requirement, not a beauty
    # score.  These roles inherit the prompt's character vector and therefore
    # select different stocks for different requests instead of a fixed capsule.
    coverage = {role.note for role in roles}
    structural = (
        ("opening_articulation", "Opening articulation", "top", "bridge", .075, (("freshness", .35), ("transparency", .3))),
        ("heart_continuity", "Heart continuity", "heart", "bridge", .12, (("radiance", .35), ("floral", .15))),
        ("drydown_structure", "Drydown structure", "base", "structure", .18, (("woody", .45), ("warmth", .15))),
    )
    prompt_terms = _source_tokens(f"{formula_name} {request}")

    def support_query(note: str, label: str, function: str) -> tuple[str, ...]:
        supporting_facets = [
            facet
            for facet in facets
            if facet.note == note and facet.function != "modifier"
        ]
        own_register = bool(supporting_facets)
        if not supporting_facets:
            # Opening and heart bridges borrow only from facets that are not
            # base notes; borrowing wood or amber terms here turned the whole
            # formula into the same few woods and ambers.
            supporting_facets = [
                facet
                for facet in facets
                if facet.function != "modifier"
                and (note == "base" or facet.note != "base")
            ]
        facet_terms = tuple(
            term
            for facet in supporting_facets[:3]
            for term in facet.query_terms[:5]
        )
        family_terms = (
            tuple(word for word in family.tier(note) if not _family_word_avoided(family, note, word, avoid))
            if family is not None else ()
        )
        return _dedupe(
            (
                # A register the brief names keeps its own notes first; one it
                # leaves open looks first for the family's materials.
                *((*facet_terms, *family_terms) if own_register else (*family_terms, *facet_terms)),
                *_source_tokens(f"{label} {function} {note}"),
            )
        )[:16]

    # An exact material count is the user's architecture; layering only
    # applies when the count is left to the composer.
    layers = (
        _note_layers(
            complexity_text=complexity_text,
            roles=roles,
            avoid=avoid,
            qualifier_weights=qualifier_weights,
            family=family,
        )
        if target_count is None
        else ()
    )
    base_layered = any(layer.note == "base" for layer in layers)
    deferred_drydown: SemanticRole | None = None
    for role_id, label, note, function, share, base_weights in structural:
        if len(roles) >= maximum:
            break
        if note in coverage and len(roles) >= 6:
            continue
        merged: dict[str, float] = dict(base_weights)
        for dimension, weight in qualifier_weights:
            merged[dimension] = merged.get(dimension, 0.0) + weight * .45
        role = SemanticRole(
            role_id=role_id,
            label=label,
            note=note,
            function=function,
            query_terms=support_query(note, label, function),
            character_weights=tuple(sorted(merged.items())),
            share=share,
            provenance="FUNCTIONAL_COVERAGE",
        )
        if role_id == "drydown_structure" and base_layered:
            # The base layers below are the drydown structure.
            deferred_drydown = role
            continue
        roles.append(role)
        coverage.add(note)

    # The lasting spice follows the brief's own notes, so the search fills it
    # before a bridge or layer can take its stock, yet it covers no register
    # (a 3% spice is not the drydown structure) and leaves the layers as they
    # were.  It adds a material to the formula; an exact material count keeps
    # it only where the count has room.
    if lasting_spice is not None and len(roles) < (maximum if target_count is None else role_target):
        roles.insert(lasting_spice_at, lasting_spice)
        if target_count is None:
            role_target = min(maximum, role_target + 1)

    # The count built without layers; layers and accords never shrink a
    # formula below it.
    base_target = role_target
    family_placed: list[SemanticRole] = []
    if layers:
        # Each requested note keeps room for its first accord material, and
        # Deep Compose keeps its two places, before a generic layer takes one.
        reserve = _DEEP_COMPOSE_RESERVE + len(_accord_leads(roles))
        placed = list(layers[:max(0, maximum - len(roles) - reserve)])
        layer_share = sum(layer.share for layer in placed)
        if layer_share > _LAYER_SHARE_BUDGET:
            scale = _LAYER_SHARE_BUDGET / layer_share
            placed = [replace(layer, share=layer.share * scale) for layer in placed]
        # A family material's role comes last: it takes a stock named for it
        # only after the brief's notes and the required roles have theirs.
        family_placed = [layer for layer in placed if layer.role_id.startswith(FAMILY_ROLE_PREFIX)]
        placed = [layer for layer in placed if not layer.role_id.startswith(FAMILY_ROLE_PREFIX)]
        roles.extend(placed)
        if (
            deferred_drydown is not None
            and not any(layer.note == "base" for layer in placed)
            and len(roles) < maximum
        ):
            roles.append(deferred_drydown)
        role_target = min(maximum - reserve, role_target + len(placed))

    optional_structural = (
        ("top_to_heart_link", "Top-to-heart link", "heart", "bridge", .075, (("transparency", .35), ("radiance", .3))),
        ("heart_to_base_link", "Heart-to-base link", "base", "bridge", .09, (("woody", .25), ("creamy", .15))),
        ("diffusion_texture", "Diffusion and spatial texture", "heart", "volume", .11, (("radiance", .45), ("transparency", .4))),
        ("persistent_identity", "Persistent identity echo", "base", "fixative", .10, (("woody", .25), ("warmth", .15))),
    )

    # A brief that explicitly asks for an expanded or highly detailed
    # architecture receives additional *named functions*, never anonymous
    # count filler.  The requested maximum is still only a ceiling.
    expanded_functions = (
        ("opening_lift", "Secondary opening lift", "top", "radiance", .04, (("freshness", .4), ("radiance", .25))),
        ("opening_contrast", "Opening contrast", "top", "modifier", .035, (("green", .25), ("spicy", .2))),
        ("opening_transition", "Opening transition", "top", "bridge", .045, (("transparency", .35), ("freshness", .2))),
        ("heart_body", "Secondary heart body", "heart", "volume", .065, (("floral", .35), ("radiance", .15))),
        ("heart_contour", "Heart contour", "heart", "character", .05, (("green", .2), ("floral", .2))),
        ("heart_contrast", "Heart contrast", "heart", "modifier", .035, (("spicy", .25), ("freshness", .15))),
        ("heart_nuance", "Heart nuance", "heart", "character", .04, (("warmth", .15), ("green", .15))),
        ("base_body", "Secondary base body", "base", "volume", .075, (("woody", .4), ("warmth", .2))),
        ("base_diffusion", "Base diffusion", "base", "volume", .055, (("radiance", .2), ("woody", .2))),
        ("base_contour", "Base contour", "base", "character", .05, (("woody", .3), ("smoky", .15))),
        ("base_shadow", "Base shadow", "base", "modifier", .035, (("smoky", .3), ("animalic", .1))),
        ("drydown_nuance", "Drydown nuance", "base", "modifier", .04, (("warmth", .15), ("green", .1))),
        ("drydown_anchor", "Drydown anchor", "base", "fixative", .065, (("woody", .35), ("creamy", .1))),
    )

    # Very short briefs still receive enough distinct structural functions for
    # a small perfume.  A user-supplied exact/minimum count may raise this
    # target, but the ordinary maximum remains a ceiling rather than a request
    # to pad a formula.
    fillers = (
        ("contrast_detail", "Controlled contrast detail", "heart", "modifier", .045),
        ("texture_support", "Texture support", "base", "texture", .065),
        ("recognizer_restatement", "Recognizer restatement", "heart", "character", .085),
    )

    def fill(roles: list[SemanticRole], target: int) -> list[SemanticRole]:
        present = {role.role_id for role in roles}
        for role_id, label, note, function, share, base_weights in optional_structural:
            if len(roles) >= target:
                break
            if role_id in present:
                continue
            merged = dict(base_weights)
            for dimension, weight in qualifier_weights:
                merged[dimension] = merged.get(dimension, 0.0) + weight * .3
            roles.append(
                SemanticRole(
                    role_id=role_id,
                    label=label,
                    note=note,
                    function=function,
                    query_terms=support_query(note, label, function),
                    character_weights=tuple(sorted(merged.items())),
                    share=share,
                    provenance="FUNCTIONAL_COVERAGE",
                )
            )
        for role_id, label, note, function, share, base_weights in expanded_functions:
            if len(roles) >= target:
                break
            if role_id in present:
                continue
            merged = dict(base_weights)
            for dimension, weight in qualifier_weights:
                merged[dimension] = merged.get(dimension, 0.0) + weight * .2
            roles.append(
                SemanticRole(
                    role_id=role_id,
                    label=label,
                    note=note,
                    function=function,
                    query_terms=support_query(note, label, function),
                    character_weights=tuple(sorted(merged.items())),
                    share=share,
                    provenance="PROMPT_REQUESTED_EXPANDED_ARCHITECTURE",
                )
            )
        for role_id, label, note, function, share in fillers:
            if len(roles) >= target:
                break
            if role_id in present:
                continue
            roles.append(
                SemanticRole(
                    role_id=role_id,
                    label=label,
                    note=note,
                    function=function,
                    query_terms=prompt_terms,
                    character_weights=qualifier_weights,
                    share=share,
                    provenance="MINIMUM_FUNCTIONAL_ARCHITECTURE",
                )
            )
        return roles

    roles = fill(roles, role_target)
    roles = roles[:maximum]
    if target_count is None:
        roles = _with_accords(roles, maximum, request_key, anchor_facets)
        # Layers and accords add to the formula the composer built before
        # layering; at a tight ceiling they never leave it smaller.  The
        # Deep Compose places are only kept free from layers and accords.
        if len(roles) < base_target:
            roles = fill(roles, base_target)
        roles.extend(family_placed[:max(0, maximum - _DEEP_COMPOSE_RESERVE - len(roles))])
    return tuple(roles)


# Each requested note is built as a small accord: the lead stock keeps its
# role unchanged (so Deep Compose can still refine that exact role) and up to
# two supporting stocks of the same note, with their own matching odor and a
# different family, are added beside it in a 62/23/15 proportion.
ACCORD_SUPPORT_PROVENANCE = "ACCORD_SUPPORT"
_ACCORD_SPLIT = (.62, .23, .15)
# The same-query supports a note gets today; a cited helper placed beyond
# them has no same-query support to fall back to.
TODAY_SUPPORT_PLACES = len(_ACCORD_SPLIT) - 1
_ACCORD_FUNCTIONS = frozenset({"character", "structure", "texture"})


def accord_lead_role_id(role: SemanticRole) -> str | None:
    """The lead role a support role belongs to, or None for any other role."""

    if role.provenance != ACCORD_SUPPORT_PROVENANCE:
        return None
    return role.role_id.split(ACCORD_SUPPORT_SEPARATOR, 1)[0]


# Places kept free so a Deep Compose comparison can still add its own role
# without displacing the requested notes.
_DEEP_COMPOSE_RESERVE = 2


def _accord_leads(roles: Sequence[SemanticRole]) -> list[SemanticRole]:
    anchored_words = {
        word
        for role in roles
        if role.exact_material is not None
        for word in _key(role.exact_material).split()
    }
    return [
        role
        for role in roles
        if role.provenance == "PROMPT_DERIVED_FACET"
        and role.exact_material is None
        and role.function in _ACCORD_FUNCTIONS
        # A note the user already anchored with a named stock has its second
        # material; adding more of it would crowd the other notes.
        and not anchored_words & {
            word for term in role.query_terms for word in _key(term).split()
        }
    ]


def _anchor_support(anchor: SemanticRole, facet: FacetDefinition) -> SemanticRole:
    """One supporting accord material for a note a named stock leads.

    It takes the note's facet query, odor and place, at the first support's
    proportion of the anchor.
    """

    fraction = _ACCORD_SPLIT[1] / _ACCORD_SPLIT[0]
    return SemanticRole(
        role_id=f"{anchor.role_id}{ACCORD_SUPPORT_SEPARATOR}1",
        label=f"{anchor.label}: supporting accord material 1",
        note=facet.note,
        function=facet.function,
        query_terms=facet.query_terms,
        character_weights=facet.character_weights,
        share=anchor.share * fraction,
        required=False,
        max_raw_share=(facet.max_raw_share or .28) * fraction,
        provenance=ACCORD_SUPPORT_PROVENANCE,
    )


def _cited_accords(
    leads: Sequence[tuple[SemanticRole, str]],
    request_key: str,
) -> dict[str, note_accord_specs.AccordSpec]:
    """Each lead, with the facet id of the note it leads, whose note has a
    cited accord spec the brief names.

    A spec applies once per note, to its first lead in brief order: the
    iris facets share one spec, so only the first iris lead builds it; a
    later one is left out and keeps today's same-query supports.
    """

    cited: dict[str, note_accord_specs.AccordSpec] = {}
    seen: set[str] = set()
    for lead, facet_id in leads:
        spec = note_accord_specs.accord_spec_for(facet_id)
        if spec is None or not any(_phrase_present(request_key, word) for word in spec.named_by):
            continue
        if spec.note not in seen:
            cited[lead.role_id] = spec
        seen.add(spec.note)
    return cited


def _accord_part(
    spec: note_accord_specs.AccordSpec,
    node: note_accord_specs.NodeRef,
    stocks: Sequence[note_accord_specs.StockRef],
    job: str | None = None,
) -> AccordPart:
    return AccordPart(
        note=spec.note,
        part="lead" if job is None else "helper",
        job=job,
        function=node.function,
        source_ids=node.source_ids,
        stocks=tuple((stock.name, stock.fraction) for stock in stocks),
    )


def _cited_lead(lead: SemanticRole, spec: note_accord_specs.AccordSpec) -> SemanticRole:
    """The lead, carrying the spec's lead part.

    Its query words stay the facet's own, so the role still equals the
    canonical facet role a v5 Deep Compose refinement looks for; the solver
    puts the cited lead stocks first when it scores the role.
    """

    return replace(lead, accord=_accord_part(spec, spec.lead, spec.lead_stocks))


def _cited_helper(
    lead: SemanticRole,
    spec: note_accord_specs.AccordSpec,
    number: int,
    place: int,
) -> SemanticRole:
    """Helper ``number`` of a cited accord, in support place ``place``: it
    may take only the spec's own stocks."""

    helper = spec.helpers[number - 1]
    return SemanticRole(
        role_id=f"{lead.role_id}{ACCORD_SUPPORT_SEPARATOR}{place}",
        label=f"{lead.label}: {spec.note} accord helper {number} ({helper.job})",
        note=lead.note,
        function=lead.function,
        query_terms=_dedupe(stock.name for stock in helper.stocks),
        character_weights=lead.character_weights,
        share=lead.share * helper.share_of_lead,
        required=False,
        max_raw_share=(lead.max_raw_share or .28) * helper.share_of_lead,
        provenance=ACCORD_SUPPORT_PROVENANCE,
        accord=_accord_part(spec, helper.node, helper.stocks, helper.job),
    )


def _anchor_helper_lead(anchor: SemanticRole, facet: FacetDefinition) -> SemanticRole:
    """The anchor as a cited helper's lead: its id, label and share, with
    the note, function, odor and cap of the facet it leads, as its own
    support takes them."""

    return replace(
        anchor, note=facet.note, function=facet.function,
        character_weights=facet.character_weights, max_raw_share=facet.max_raw_share,
    )


def _with_accords(
    roles: list[SemanticRole],
    maximum: int,
    request_key: str = "",
    anchor_facets: Mapping[str, FacetDefinition] | None = None,
) -> list[SemanticRole]:
    anchor_facets = anchor_facets or {}
    leads = _accord_leads(roles)
    lead_ids = {lead.role_id for lead in leads}
    # A note with a cited spec the brief names keeps today's first same-query
    # support in its first place (it often carries the note's key odorant,
    # such as an irone beside a weak orris lead) and gets the spec's helpers
    # in the places after it.  A stock the brief names that leads a covered
    # note (Lavender EO for "lavender") builds the note's accord the same
    # way: its own support stays in place 1.
    cited = _cited_accords(
        [
            (role, anchor_facets[role.role_id].facet_id if role.role_id in anchor_facets
             else role.role_id[len("facet_"):])
            for role in roles
            if role.role_id in anchor_facets
            or (role.role_id in lead_ids and role.role_id.startswith("facet_"))
        ],
        request_key,
    )
    owners = [role for role in roles if role.role_id in lead_ids or role.role_id in cited]
    places = {
        owner.role_id: TODAY_SUPPORT_PLACES if owner.role_id not in cited
        else 1 + len(cited[owner.role_id].helpers)
        for owner in owners
    }
    budget = maximum - len(roles) - _DEEP_COMPOSE_RESERVE
    supports: dict[str, int] = {owner.role_id: 1 for owner in owners if owner.role_id in anchor_facets}
    # One support per requested note first, then a second, so a tight
    # material limit spreads depth across notes instead of piling on one.
    # An anchor's first support is already in the brief.
    for depth in range(1, max(places.values(), default=0) + 1):
        for owner in owners:
            if budget <= 0:
                break
            if depth > places[owner.role_id] or depth <= supports.get(owner.role_id, 0):
                continue
            supports[owner.role_id] = depth
            budget -= 1
    expanded: list[SemanticRole] = []
    for role in roles:
        anchor_id = accord_lead_role_id(role)
        if anchor_id in anchor_facets and anchor_id in cited and role.role_id.endswith(
            f"{ACCORD_SUPPORT_SEPARATOR}1"
        ):
            anchor = next(item for item in roles if item.role_id == anchor_id)
            expanded.append(role)
            expanded.extend(
                _cited_helper(_anchor_helper_lead(anchor, anchor_facets[anchor_id]), cited[anchor_id],
                              place - 1, place)
                for place in range(2, supports[anchor_id] + 1)
            )
            continue
        if role.role_id in anchor_facets and role.role_id in cited:
            expanded.append(_cited_lead(role, cited[role.role_id]))
            continue
        count = supports.get(role.role_id, 0)
        spec = cited.get(role.role_id)
        if spec is not None:
            expanded.append(_cited_lead(role, spec))
            expanded.extend(
                accord_support_clone(role, 1) if place == 1
                else _cited_helper(role, spec, place - 1, place)
                for place in range(1, count + 1)
            )
            continue
        if not count:
            expanded.append(role)
            continue
        expanded.append(role)
        expanded.extend(accord_support_clone(role, index) for index in range(1, count + 1))
    return expanded


def accord_support_clone(lead: SemanticRole, index: int) -> SemanticRole:
    """Today's same-query support ``index`` of ``lead``: the note's query,
    odor and descriptor requirement, at the 62/23/15 proportion.

    The formula solver fills a cited helper's slot with this role when none
    of the helper's own stocks can go in and ``index`` is one of today's
    ``TODAY_SUPPORT_PLACES``.
    """

    # Relative to the lead, which keeps its full share.
    fraction = _ACCORD_SPLIT[index] / _ACCORD_SPLIT[0]
    return SemanticRole(
        role_id=f"{lead.role_id}{ACCORD_SUPPORT_SEPARATOR}{index}",
        label=f"{lead.label}: supporting accord material {index}",
        note=lead.note,
        function=lead.function,
        query_terms=lead.query_terms,
        character_weights=lead.character_weights,
        share=lead.share * fraction,
        required=False,
        max_raw_share=(lead.max_raw_share or .28) * fraction,
        provenance=ACCORD_SUPPORT_PROVENANCE,
        descriptor_requirement=lead.descriptor_requirement,
    )


def compile_semantic_brief(
    *,
    formula_name: str,
    request: str,
    interpretation: Mapping[str, Any],
    max_materials: int,
    target_material_count: int | None = None,
) -> SemanticBrief:
    """Compile one accepted direct user request into structural target roles."""

    name = _clean(formula_name) or "Untitled Formula"
    raw = _clean(request)
    if not raw:
        raise ValueError("request must be non-empty text")
    if not 1 <= int(max_materials) <= 60:
        raise ValueError("max_materials must be between 1 and 60")
    if target_material_count is not None and not 1 <= int(target_material_count) <= int(max_materials):
        raise ValueError("target_material_count must fit within max_materials")
    avoid = tuple(str(item) for item in interpretation.get("must_avoid", ()))
    preserve = tuple(str(item) for item in interpretation.get("must_preserve", ()))
    explicit = tuple(str(item) for item in interpretation.get("explicit_materials", ()))
    # French note words in the name or brief are read as their English notes
    # ("Baie Rose" is pink pepper, not rose); the user's text is kept as written.
    reading_name, reading_raw = translate_note_phrases(name), translate_note_phrases(raw)
    positive_semantic_text = _mask_avoided_phrases(f"{reading_name} {reading_raw}", avoid)
    requested_fruits = _requested_fruits(positive_semantic_text)
    # Separate fields are separate clauses. A negation in a diagnostic title
    # must not consume the user's entire following brief. Explicit avoid terms
    # still mask both fields in the shared retrieval function.
    knowledge_context = retrieve_formulation_knowledge(
        f"{reading_name}; {reading_raw}", avoid=avoid
    )
    facets = _matched_facets(positive_semantic_text, avoid, knowledge_context)
    qualifiers = _qualifier_weights(positive_semantic_text, avoid)
    expression_terms = _dedupe(
        [*requested_fruits, *(facet.facet_id.replace("_", " ") for facet in facets), *preserve]
        or _source_tokens(f"{reading_name} {reading_raw}")[:6]
    )
    family_neighborhoods = _dedupe(
        f"{facet.note} {facet.facet_id.replace('_', ' ')}"
        for facet in facets[:4]
    ) or ("request-defined perfume architecture",)
    protected = _dedupe((*preserve, *explicit, *requested_fruits, *expression_terms[:2]))
    forbidden = _dedupe((*avoid, "anonymous generic perfume drift"))
    family = brief_family(positive_semantic_text, facets)
    roles = _roles(
        formula_name=reading_name,
        request=reading_raw,
        facets=facets,
        explicit_materials=explicit,
        qualifier_weights=qualifiers,
        maximum=int(max_materials),
        target_count=(
            int(target_material_count)
            if target_material_count is not None
            else None
        ),
        avoid=avoid,
        family=family,
    )

    request_digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    provenance = ProvenanceRef(
        provenance_id=f"direct-user-request-{request_digest[:16]}",
        source_ref=f"request://formula-studio/{request_digest}",
        evidence_class=EvidenceClass.USER_REPORT,
        independence_key=f"request-{request_digest[:16]}",
        source_sha256=request_digest,
    )
    branch = TargetBranch(
        branch_id=f"intended-branch-{request_digest[:16]}",
        interpretation="; ".join(expression_terms) or raw,
        claim_keys=("target_identity", "expression"),
        evidence_ids=(),
    )
    brief = TargetBrief(
        request_id=f"formula-studio-{request_digest[:20]}",
        mode=TargetMode.CONCEPT_ONLY,
        subject=name,
        named_references=tuple(
            str(item)
            for item in interpretation.get("reference_scope", {}).get("named_references", ())
        ),
        family_neighborhoods=family_neighborhoods,
        abstraction_level=AbstractionLevel.RECOGNIZABLE_ABSTRACTION,
        expression_terms=expression_terms,
        exclusions=_dedupe(avoid) or ("unrequested identity drift",),
        protected_recognizers=protected or (name,),
        forbidden_drift=forbidden,
        transformations=(
            TemporalTransformation(
                transformation_id="opening-to-heart",
                source_state="opening articulation",
                destination_state="heart identity",
                temporal_window="opening to heart",
                continuity_requirement="retain at least one target recognizer",
            ),
            TemporalTransformation(
                transformation_id="heart-to-drydown",
                source_state="heart identity",
                destination_state="drydown structure",
                temporal_window="heart to drydown",
                continuity_requirement="retain target identity without generic base drift",
            ),
        ),
        temporal_requests=tuple(
            str(row.get("label"))
            for row in interpretation.get("evaluation_windows", ())
            if row.get("label")
        ) or ("opening", "heart", "drydown"),
        matrix_context="ethanol fragrance design; exact release scenario unresolved",
        criterion_vocabulary=(
            "recognizer integrity",
            "functional role coverage",
            "transition continuity",
            "constraint compliance",
        ),
        reference_evidence=(),
        provenance_refs=(provenance,),
        request_source=TargetRequestSource(
            raw_request=raw,
            source_ref=provenance.source_ref,
            source_sha256=request_digest,
            span=TargetSourceSpan(start_char=0, end_char=len(raw)),
            origin="direct Formula Studio request",
        ),
        branches=(branch,),
        conflicts=(),
        unknowns=(),
        acceptance=TargetAcceptance(
            acceptance_id=f"direct-request-acceptance-{request_digest[:16]}",
            state=TargetAcceptanceState.ACCEPTED,
            accepted_branch_ids=(branch.branch_id,),
            decision_basis="The direct user request is accepted for advisory structural design only.",
            provenance_refs=(provenance,),
        ),
    )
    target_intent = compile_target_intent(brief)
    return SemanticBrief(
        schema_version="semantic-perfume-brief-v1",
        request_sha256=request_digest,
        formula_name=name,
        normalized_request=raw,
        family_neighborhoods=family_neighborhoods,
        facets=tuple(facet.facet_id for facet in facets),
        expression_terms=expression_terms,
        protected_recognizers=protected or (name,),
        forbidden_drift=forbidden,
        roles=roles,
        target_intent=target_intent.as_dict(),
        knowledge_context=knowledge_context,
        requested_fruits=requested_fruits,
        unmapped_requested_notes=_unmapped_requested_notes(
            positive_semantic_text, facets, requested_fruits, explicit
        ),
        fragrance_family=family.heading if family is not None else None,
        star_role_ids=_star_role_ids(roles, reading_raw, facets),
    )


__all__ = [
    "ACCENT_MAX_RAW_SHARE",
    "ACCENT_PROVENANCE",
    "FACET_IDENTITY_REQUIREMENTS",
    "LASTING_SPICE_PROVENANCE",
    "LAYER_MAX_RAW_SHARE",
    "LAYER_PROVENANCE",
    "FacetDefinition",
    "SemanticBrief",
    "SemanticRole",
    "TODAY_SUPPORT_PLACES",
    "accord_lead_role_id",
    "accord_support_clone",
    "compile_semantic_brief",
    "role_identity_requirement",
]
