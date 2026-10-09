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
from typing import Any, Iterable, Mapping, Sequence

from engine.formulation_intelligence.contracts import EvidenceClass, ProvenanceRef
from engine.formulation_intelligence.literature_knowledge import retrieve_formulation_knowledge
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

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


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
    FacetDefinition("rain_water", ("rain", "wet pavement", "petrichor", "water", "aquatic", "marine", "ocean", "sea air"), ("rain", "wet", "petrichor", "marine", "aquatic", "ozone", "calone"), "top", "character", (("freshness", .9), ("transparency", .65), ("green", .25)), .07, .12),
    FacetDefinition("dry_wood", ("wood", "woody", "cedar", "driftwood", "pencil", "timber", "oak"), ("wood", "cedar", "vetiver", "patchouli", "clearwood", "timber"), "base", "structure", (("woody", 1.0), ("transparency", .2)), .15, .28),
    FacetDefinition("creamy_wood", ("sandalwood", "creamy wood", "milky wood", "soft wood"), ("sandalwood", "sandalore", "javanol", "creamy", "wood"), "base", "structure", (("woody", .85), ("creamy", .65), ("warmth", .25)), .15, .27),
    FacetDefinition("vetiver_root", ("vetiver", "rooty", "roots", "earthy root"), ("vetiver", "root", "earthy", "vetiveryl"), "base", "character", (("woody", .75), ("green", .35), ("smoky", .2)), .11, .20),
    FacetDefinition("patchouli_earth", ("patchouli", "earthy", "forest floor", "soil"), ("patchouli", "earth", "soil", "moss", "clearwood"), "base", "character", (("woody", .65), ("green", .25), ("smoky", .2)), .09, .16),
    FacetDefinition("amber_mineral", ("amber", "ambrox", "ambergris", "mineral amber", "dry amber"), ("ambrox", "ambergris", "amber", "mineral", "woody amber"), "base", "structure", (("woody", .65), ("warmth", .35), ("radiance", .25)), .12, .22),
    FacetDefinition("skin_musk", ("musk", "musky", "skin scent", "human skin", "body warmth", "warm skin"), ("musk", "skin", "ambrettolide", "brassylate", "habanolide", "exaltolide"), "base", "texture", (("creamy", .45), ("warmth", .35), ("transparency", .35)), .09, .16),
    FacetDefinition("animalic_fur", ("animalic", "clean fur", "warm fur", "fur accord", "civet", "castoreum"), ("animalic", "fur", "civet", "castoreum", "costus", "indole"), "base", "modifier", (("animalic", 1.0), ("warmth", .3), ("smoky", .15)), .035, .07),
    FacetDefinition("incense_resin", ("incense", "frankincense", "olibanum", "myrrh", "opoponax", "church", "cathedral", "resin"), ("incense", "olibanum", "frankincense", "myrrh", "opoponax", "resin"), "base", "character", (("smoky", .75), ("woody", .5), ("warmth", .25)), .09, .16),
    FacetDefinition("smoke_char", ("smoke", "smoky", "charred", "ember", "burnt", "ash"), ("smoke", "cade", "birch tar", "guaiacol", "char", "tobacco"), "base", "modifier", (("smoky", 1.0), ("woody", .35)), .035, .07),
    FacetDefinition("leather_suede", ("leather", "suede", "saddle", "book leather"), ("leather", "suede", "isobutyl quinoline", "birch tar", "saffron"), "base", "character", (("woody", .55), ("smoky", .45), ("animalic", .25)), .065, .12),
    FacetDefinition("moss_chypre", ("moss", "mossy", "chypre", "forest moss"), ("moss", "evernyl", "oakmoss", "patchouli", "labdanum"), "base", "structure", (("green", .5), ("woody", .5), ("smoky", .15)), .07, .13),
    FacetDefinition("vanilla_balsam", ("vanilla", "vanillic", "balsamic", "benzoin", "tonka"), ("vanilla", "vanillin", "benzoin", "tonka", "coumarin", "balsam"), "base", "character", (("sweetness", .9), ("warmth", .55), ("creamy", .35)), .075, .14),
    FacetDefinition("coffee_cocoa", ("coffee", "cocoa", "chocolate", "roasted"), ("coffee", "cocoa", "roast", "pyrazine", "chocolate"), "heart", "character", (("warmth", .5), ("smoky", .4), ("sweetness", .25)), .06, .11),
    FacetDefinition("tobacco_hay", ("tobacco", "hay", "straw", "dry grass"), ("tobacco", "hay", "coumarin", "immortelle", "tea"), "base", "character", (("warmth", .45), ("woody", .35), ("smoky", .3)), .065, .12),
    FacetDefinition("spice", ("spice", "spicy", "pepper", "cardamom", "nutmeg", "cinnamon", "clove", "saffron", "ginger"), ("pepper", "cardamom", "nutmeg", "cinnamon", "clove", "saffron", "ginger", "spice"), "heart", "modifier", (("spicy", 1.0), ("warmth", .35)), .045, .09),
    FacetDefinition("fruit", ("fruit", "fruity", "pear", "apple", "peach", "plum", "berry", "mango", "pineapple"), ("fruit", "pear", "apple", "peach", "plum", "berry", "mango", "pineapple", "ester"), "top", "character", (("freshness", .45), ("sweetness", .4), ("radiance", .25)), .065, .12),
    FacetDefinition("aldehydic", ("aldehydic", "sparkling aldehyde", "champagne", "soapy aldehyde"), ("aldehyde", "sparkling", "wax", "linen"), "top", "modifier", (("radiance", .8), ("freshness", .4), ("transparency", .25)), .025, .06),
    FacetDefinition("powder", ("powder", "powdery", "cosmetic", "makeup"), ("powder", "iris", "ionone", "heliotropin", "musk"), "heart", "texture", (("powdery", 1.0), ("floral", .25)), .055, .11),
    FacetDefinition("almond_nut", ("almond", "marzipan", "biscuit", "nutty", "toasted nut"), ("almond", "benzaldehyde", "heliotropin", "tonka", "pyrazine", "biscuit"), "heart", "character", (("warmth", .55), ("sweetness", .35), ("powdery", .25)), .06, .11),
    FacetDefinition("floral_bouquet", ("floral", "flowers", "flower", "petal", "petals", "blossom", "bloom"), ("floral", "petal", "hedione", "phenethyl", "linalool", "blossom"), "heart", "character", (("floral", .9), ("radiance", .35)), .10, .18),
)

# Shares and character weights remain structural design heuristics, not values
# measured by the literature pack. Its role distinctions replace the umbrella
# only when the request actually calls for that profile.
_LITERATURE_FACETS = {
    "iris_root": FacetDefinition("iris_root", ("iris", "orris"), ("iris recognizer", "alpha irone", "alpha isomethyl ionone", "iris", "orris"), "heart", "character", (("powdery", .35), ("woody", .35)), .10, .18, "iris recognizer"),
    "iris_butter": FacetDefinition("iris_butter", ("iris", "orris"), ("iris recognizer", "alpha irone", "orris", "waxy"), "heart", "character", (("powdery", .6), ("creamy", .4)), .10, .18, "iris recognizer"),
    "iris_cosmetic": FacetDefinition("iris_cosmetic", ("iris", "orris", "lipstick"), ("iris recognizer", "methyl ionone gamma coeur", "alpha isomethyl ionone", "iris", "cosmetic"), "heart", "character", (("powdery", .8), ("floral", .3)), .10, .18, "iris recognizer"),
    "iris_transparent": FacetDefinition("iris_transparent", ("iris", "orris"), ("iris recognizer", "alpha irone", "alpha isomethyl ionone", "iris"), "heart", "character", (("powdery", .3), ("transparency", .65)), .10, .18, "iris recognizer"),
    "iris_woody": FacetDefinition("iris_woody", ("iris", "orris"), ("iris recognizer", "methyl ionone gamma coeur", "alpha isomethyl ionone", "iris", "woody"), "heart", "character", (("powdery", .4), ("woody", .6)), .10, .18, "iris recognizer"),
    "violet_petals": FacetDefinition("violet_petals", ("violet",), ("violet petal recognizer", "beta ionone", "alpha ionone", "violet", "petal"), "heart", "character", (("floral", .7), ("powdery", .25)), .10, .18, "violet petal recognizer"),
    "violet_powder": FacetDefinition("violet_powder", ("violet",), ("violet petal recognizer", "beta ionone", "alpha ionone", "violet", "powder"), "heart", "character", (("powdery", .8), ("floral", .4)), .10, .18, "violet petal recognizer"),
    "violet_leaf": FacetDefinition("violet_leaf", ("violet leaf", "violet leaves"), ("violet leaf absolute", "parmavert", "violet leaf", "leaf"), "top", "character", (("green", .8), ("freshness", .3)), .04, .10),
}
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
    return tuple(result)


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
# How strongly each layer leans toward the requested notes' character.
_BRIEF_ECHO = .35
# Layers together never outweigh the brief: past this share of the formula
# they are scaled down together.
_LAYER_SHARE_BUDGET = .30
_LIGHT_BRIEF = re.compile(
    r"\b(?:fresh|cologne|aquatic|citrus|light|transparent|clean|airy|sheer|spring|summer|dewy|delicate)\b"
)
_WARM_BRIEF = re.compile(r"\b(?:warm|dark|deep|resin|resinous|amber|incense|balsam|balsamic|vanilla|oriental|evening|rich|leather|smoky|tobacco)\b")


def _note_layers(
    *,
    complexity_text: str,
    roles: Sequence["SemanticRole"],
    avoid: Sequence[str],
    qualifier_weights: tuple[tuple[str, float], ...] = (),
) -> tuple["SemanticRole", ...]:
    """Supporting top, heart and base layers the prompt-derived roles leave open.

    Layers are optional roles: a layer with no eligible owned stock is simply
    left out.  They never replace a requested facet and carry modest shares so
    the requested character still leads.  Returned in priority order.
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
    layers: list[SemanticRole] = []
    for role_id, label, note, requirement, share, terms, weights, markers, kind, skip in _NOTE_LAYERS:
        if is_avoided(markers):
            continue
        if (
            (skip == "light" and light)
            or (skip == "not_warm" and not warm)
            or (skip == "not_light" and not light)
        ):
            continue
        covered = any(marker in text for text in note_terms[note] for marker in markers)
        if covered and requirement != "base_wood":
            continue
        if covered:
            # A wood-led brief gets a second, contrasting wood family; the
            # solver's family buckets keep it from repeating the first one.
            role_id, label = "base_wood_contrast", "Contrasting base wood"
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
        layers.append(
            SemanticRole(
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
        )
    return tuple(layers)


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
    for facet in facets:
        if len(roles) >= maximum:
            break
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
                descriptor_requirement="fruit" if facet.facet_id == "fruit" else None,
            )
        )

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
        return _dedupe(
            (
                *(
                    term
                    for facet in supporting_facets[:3]
                    for term in facet.query_terms[:5]
                ),
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

    # The count built without layers; layers and accords never shrink a
    # formula below it.
    base_target = role_target
    if layers:
        # Each requested note keeps room for its first accord material, and
        # Deep Compose keeps its two places, before a generic layer takes one.
        reserve = _DEEP_COMPOSE_RESERVE + len(_accord_leads(roles))
        placed = list(layers[:max(0, maximum - len(roles) - reserve)])
        layer_share = sum(layer.share for layer in placed)
        if layer_share > _LAYER_SHARE_BUDGET:
            scale = _LAYER_SHARE_BUDGET / layer_share
            placed = [replace(layer, share=layer.share * scale) for layer in placed]
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
        roles = _with_accords(roles, maximum)
        # Layers and accords add to the formula the composer built before
        # layering; at a tight ceiling they never leave it smaller.  The
        # Deep Compose places are only kept free from layers and accords.
        if len(roles) < base_target:
            roles = fill(roles, base_target)
    return tuple(roles)


# Each requested note is built as a small accord: the lead stock keeps its
# role unchanged (so Deep Compose can still refine that exact role) and up to
# two supporting stocks of the same note, with their own matching odor and a
# different family, are added beside it in a 62/23/15 proportion.
ACCORD_SUPPORT_PROVENANCE = "ACCORD_SUPPORT"
ACCORD_SUPPORT_SEPARATOR = "__accord_"
_ACCORD_SPLIT = (.62, .23, .15)
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


def _with_accords(roles: list[SemanticRole], maximum: int) -> list[SemanticRole]:
    leads = _accord_leads(roles)
    budget = maximum - len(roles) - _DEEP_COMPOSE_RESERVE
    supports: dict[str, int] = {}
    # One support per requested note first, then a second, so a tight
    # material limit spreads depth across notes instead of piling on one.
    for depth in (1, 2):
        for lead in leads:
            if budget <= 0:
                break
            supports[lead.role_id] = depth
            budget -= 1
    expanded: list[SemanticRole] = []
    for role in roles:
        count = supports.get(role.role_id, 0)
        if not count:
            expanded.append(role)
            continue
        expanded.append(role)
        for index in range(1, count + 1):
            # Relative to the lead, which keeps its full share.
            fraction = _ACCORD_SPLIT[index] / _ACCORD_SPLIT[0]
            expanded.append(SemanticRole(
                role_id=f"{role.role_id}{ACCORD_SUPPORT_SEPARATOR}{index}",
                label=f"{role.label}: supporting accord material {index}",
                note=role.note,
                function=role.function,
                query_terms=role.query_terms,
                character_weights=role.character_weights,
                share=role.share * fraction,
                required=False,
                max_raw_share=(role.max_raw_share or .28) * fraction,
                provenance=ACCORD_SUPPORT_PROVENANCE,
                descriptor_requirement=role.descriptor_requirement,
            ))
    return expanded


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
    positive_semantic_text = _mask_avoided_phrases(f"{name} {raw}", avoid)
    requested_fruits = _requested_fruits(positive_semantic_text)
    # Separate fields are separate clauses. A negation in a diagnostic title
    # must not consume the user's entire following brief. Explicit avoid terms
    # still mask both fields in the shared retrieval function.
    knowledge_context = retrieve_formulation_knowledge(f"{name}; {raw}", avoid=avoid)
    facets = _matched_facets(positive_semantic_text, avoid, knowledge_context)
    qualifiers = _qualifier_weights(positive_semantic_text, avoid)
    expression_terms = _dedupe(
        [*requested_fruits, *(facet.facet_id.replace("_", " ") for facet in facets), *preserve]
        or _source_tokens(f"{name} {raw}")[:6]
    )
    family_neighborhoods = _dedupe(
        f"{facet.note} {facet.facet_id.replace('_', ' ')}"
        for facet in facets[:4]
    ) or ("request-defined perfume architecture",)
    protected = _dedupe((*preserve, *explicit, *requested_fruits, *expression_terms[:2]))
    forbidden = _dedupe((*avoid, "anonymous generic perfume drift"))
    roles = _roles(
        formula_name=name,
        request=raw,
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
    )


__all__ = [
    "ACCENT_MAX_RAW_SHARE",
    "ACCENT_PROVENANCE",
    "LAYER_MAX_RAW_SHARE",
    "LAYER_PROVENANCE",
    "FacetDefinition",
    "SemanticBrief",
    "SemanticRole",
    "accord_lead_role_id",
    "compile_semantic_brief",
]
