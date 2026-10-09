"""Inventory-grounded, request-first perfume concept design.

This module powers the lightweight formulation conversation in the personal
workbench.  It deliberately produces *design proposals*, not sensory winners
or compounding instructions.  Selection is constrained to the materialized
current inventory, evaluates the eligible catalogue for every functional slot,
and keeps the formula name and user brief as the creative objective.

The bounded refinement step only improves a declared descriptor-alignment
diagnostic while preserving the initial top/heart/base architecture.  It does
not use OAV, legacy hedonic values, sales rank, ingredient count, or a generic
valence table as an objective.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal, InvalidOperation
from typing import Any, Iterable, Sequence

from engine.ingredient_intelligence import DIMENSIONS, MaterialProfile, get_profile
from engine.inventory_completions import effective_design_ready
from engine.inventory_parser import InventoryMaterial, materialize_current_inventory
from engine.research.contracts import FALSE_ACTION_AUTHORITY, stable_payload_hash
from engine.research.request_interpretation import (
    RequestInterpretationInputV1,
    interpret_request,
)

_SOLID_MARKERS = ("crystal", "powder", "solid", "flakes")
_EXCLUDED_CATEGORIES = ("technical", "solvent", "stabilizer")
_EXCLUDED_ROLES = ("stabilizer", "solvent")
_TRACE_ROLES = ("trace",)
_GROUP_LIMITS = {"musk": 1, "citrus": 2}
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "but",
    "for",
    "from",
    "in",
    "make",
    "me",
    "new",
    "not",
    "of",
    "perfume",
    "scent",
    "the",
    "that",
    "to",
    "with",
}


@dataclass(frozen=True, slots=True)
class DescriptorRule:
    phrases: tuple[str, ...]
    weights: dict[str, float]
    family: str


@dataclass(frozen=True, slots=True)
class DesignSlot:
    slot_id: str
    label: str
    note: str
    preferred_roles: tuple[str, ...]
    share: float
    extra_weights: dict[str, float]


@dataclass(frozen=True, slots=True)
class StockCandidate:
    stock: InventoryMaterial
    profile: MaterialProfile
    profile_source: str
    solid: bool
    explicit: bool


@dataclass(frozen=True, slots=True)
class SlotChoice:
    slot: DesignSlot
    candidate: StockCandidate
    score: float
    descriptor_fit: float
    alternatives: tuple[tuple[str, float], ...]


_DESCRIPTOR_RULES: tuple[DescriptorRule, ...] = (
    DescriptorRule(("fresh", "bright", "sparkling", "crisp", "uplifting"), {"freshness": 1.0, "transparency": 0.45, "green": 0.15}, "fresh"),
    DescriptorRule(("citrus", "bergamot", "grapefruit", "lemon", "mandarin", "orange"), {"freshness": 1.0, "green": 0.2, "sweetness": 0.1}, "citrus"),
    DescriptorRule(("lavender", "aromatic", "fougere", "fougère", "herbal"), {"freshness": 0.55, "floral": 0.45, "green": 0.35, "woody": 0.15}, "aromatic"),
    DescriptorRule(("floral", "flower", "bouquet"), {"floral": 1.0, "radiance": 0.35, "freshness": 0.15}, "floral"),
    DescriptorRule(("rose", "rosy"), {"floral": 1.0, "freshness": 0.2, "sweetness": 0.15}, "rose"),
    DescriptorRule(("jasmine", "white floral", "tuberose", "gardenia", "orange blossom"), {"floral": 1.0, "radiance": 0.45, "creamy": 0.2}, "white_floral"),
    DescriptorRule(("iris", "orris", "violet", "powdery", "cosmetic"), {"powdery": 1.0, "floral": 0.4, "woody": 0.2, "transparency": 0.15}, "iris"),
    DescriptorRule(("green", "leafy", "grass", "galbanum"), {"green": 1.0, "freshness": 0.35, "transparency": 0.2}, "green"),
    DescriptorRule(("fruit", "fruity", "berry", "peach", "pear", "apple"), {"sweetness": 0.45, "freshness": 0.35, "radiance": 0.2}, "fruity"),
    DescriptorRule(("marine", "aquatic", "watery", "ocean", "ozonic"), {"freshness": 0.9, "transparency": 0.7, "green": 0.15}, "aquatic"),
    DescriptorRule(("mineral", "stone", "metallic", "cold"), {"transparency": 0.75, "freshness": 0.35, "woody": 0.2}, "mineral"),
    DescriptorRule(("woody", "wood", "cedar", "vetiver", "sandalwood"), {"woody": 1.0, "warmth": 0.25, "spicy": 0.1}, "woody"),
    DescriptorRule(("amber", "ambery", "resinous", "balsamic"), {"warmth": 0.85, "woody": 0.45, "sweetness": 0.2}, "amber"),
    DescriptorRule(("incense", "frankincense", "myrrh", "church"), {"smoky": 0.75, "warmth": 0.55, "woody": 0.35}, "incense"),
    DescriptorRule(("dark", "mysterious", "shadow", "gothic"), {"smoky": 0.65, "woody": 0.45, "warmth": 0.25, "freshness": -0.1}, "dark"),
    DescriptorRule(("smoky", "smoke", "burnt"), {"smoky": 1.0, "woody": 0.35}, "smoky"),
    DescriptorRule(("leather", "suede"), {"animalic": 0.55, "smoky": 0.45, "woody": 0.4}, "leather"),
    DescriptorRule(("spicy", "pepper", "cardamom", "saffron", "cinnamon"), {"spicy": 1.0, "warmth": 0.3}, "spicy"),
    DescriptorRule(("sweet", "gourmand", "vanilla", "caramel", "edible"), {"sweetness": 1.0, "warmth": 0.4, "creamy": 0.25}, "gourmand"),
    DescriptorRule(("creamy", "milky", "soft", "smooth"), {"creamy": 0.85, "warmth": 0.3, "powdery": 0.2}, "soft"),
    DescriptorRule(("clean", "transparent", "sheer", "airy"), {"transparency": 1.0, "freshness": 0.45, "radiance": 0.25}, "transparent"),
    DescriptorRule(("radiant", "diffusive", "blooming", "projecting", "sillage"), {"radiance": 1.0, "transparency": 0.35, "freshness": 0.15}, "radiant"),
    DescriptorRule(("skin", "intimate", "quiet", "close"), {"transparency": 0.55, "creamy": 0.3, "warmth": 0.2, "animalic": 0.1}, "skin_scent"),
    DescriptorRule(("dry", "dryness", "austere"), {"woody": 0.5, "green": 0.2, "sweetness": -0.7, "creamy": -0.2}, "dry"),
)


_SLOTS: tuple[DesignSlot, ...] = (
    DesignSlot("opening_signature", "Opening signature", "top", ("character", "modifier", "bridge"), 0.10, {"freshness": 0.35, "green": 0.1}),
    DesignSlot("heart_signature", "Heart signature", "heart", ("character", "modifier"), 0.18, {"floral": 0.2, "radiance": 0.1}),
    DesignSlot("base_signature", "Base signature", "base", ("character", "modifier"), 0.17, {"woody": 0.25, "warmth": 0.1}),
    DesignSlot("opening_bridge", "Opening bridge", "top", ("bridge", "modifier", "radiance"), 0.08, {"freshness": 0.25, "transparency": 0.3}),
    DesignSlot("heart_bridge", "Heart bridge", "heart", ("bridge", "radiance", "volume"), 0.14, {"radiance": 0.35, "transparency": 0.25}),
    DesignSlot("base_structure", "Base structure", "base", ("fixative", "character", "bridge"), 0.14, {"woody": 0.35, "warmth": 0.2}),
    DesignSlot("heart_texture", "Heart texture", "heart", ("volume", "modifier", "bridge"), 0.10, {"radiance": 0.2, "creamy": 0.15, "transparency": 0.15}),
    DesignSlot("base_fixation", "Base fixation", "base", ("fixative", "volume", "bridge"), 0.09, {"woody": 0.2, "creamy": 0.1}),
    DesignSlot("accent", "Character accent", "heart", ("character", "modifier"), 0.05, {"spicy": 0.1, "green": 0.1}),
    DesignSlot("drydown_bridge", "Drydown bridge", "base", ("bridge", "fixative", "modifier"), 0.05, {"woody": 0.2, "transparency": 0.1}),
)

# Large formulas use additional request-linked functions instead of repeating a
# generic "filler" slot.  The patterns cycle with diminishing initial shares;
# selection still compares the complete eligible inventory for every slot and
# never treats a larger ingredient count as an optimization objective.
_EXTENSION_SLOT_PATTERNS: tuple[
    tuple[str, str, str, tuple[str, ...], dict[str, float]], ...
] = (
    ("opening_lift", "Opening lift", "top", ("radiance", "bridge", "modifier"), {"freshness": 0.45, "radiance": 0.2}),
    ("opening_contour", "Opening contour", "top", ("character", "modifier"), {"freshness": 0.25, "green": 0.2}),
    ("opening_air", "Opening air", "top", ("radiance", "bridge"), {"transparency": 0.45, "freshness": 0.2}),
    ("opening_contrast", "Opening contrast", "top", ("modifier", "character"), {"spicy": 0.2, "green": 0.15}),
    ("opening_transition", "Opening transition", "top", ("bridge", "modifier"), {"transparency": 0.25, "radiance": 0.15}),
    ("heart_body", "Heart body", "heart", ("character", "volume"), {"floral": 0.35, "radiance": 0.1}),
    ("heart_lift", "Heart lift", "heart", ("radiance", "bridge"), {"radiance": 0.45, "transparency": 0.2}),
    ("heart_contour", "Heart contour", "heart", ("character", "modifier"), {"floral": 0.2, "green": 0.15}),
    ("heart_texture_support", "Heart texture support", "heart", ("volume", "modifier"), {"creamy": 0.2, "powdery": 0.15}),
    ("heart_contrast", "Heart contrast", "heart", ("modifier", "character"), {"spicy": 0.2, "freshness": 0.1}),
    ("heart_continuity", "Heart continuity", "heart", ("bridge", "volume"), {"transparency": 0.2, "woody": 0.1}),
    ("heart_nuance", "Heart nuance", "heart", ("modifier", "character"), {"green": 0.15, "warmth": 0.1}),
    ("base_body", "Base body", "base", ("character", "volume"), {"woody": 0.4, "warmth": 0.2}),
    ("base_diffusion", "Base diffusion", "base", ("bridge", "volume", "fixative"), {"radiance": 0.2, "woody": 0.2}),
    ("base_contour", "Base contour", "base", ("character", "modifier"), {"woody": 0.25, "smoky": 0.12}),
    ("base_texture_support", "Base texture support", "base", ("modifier", "fixative"), {"creamy": 0.2, "warmth": 0.15}),
    ("base_shadow", "Base shadow", "base", ("character", "modifier"), {"smoky": 0.25, "animalic": 0.1}),
    ("base_continuity", "Base continuity", "base", ("bridge", "fixative"), {"transparency": 0.15, "woody": 0.2}),
    ("drydown_nuance", "Drydown nuance", "base", ("modifier", "character"), {"warmth": 0.15, "green": 0.08}),
    ("drydown_anchor", "Drydown anchor", "base", ("fixative", "volume"), {"woody": 0.3, "creamy": 0.1}),
)


def _slots_for_limit(limit: int) -> tuple[DesignSlot, ...]:
    if limit <= len(_SLOTS):
        return _SLOTS[:limit]
    slots = list(_SLOTS)
    cycle = 1
    while len(slots) < limit:
        for slot_id, label, note, roles, weights in _EXTENSION_SLOT_PATTERNS:
            if len(slots) >= limit:
                break
            slots.append(
                DesignSlot(
                    slot_id=f"{slot_id}_{cycle}",
                    label=f"{label} {cycle}",
                    note=note,
                    preferred_roles=roles,
                    share=max(0.012, 0.042 / (cycle**0.5)),
                    extra_weights=weights,
                )
            )
        cycle += 1
    return tuple(slots)


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(value).casefold()).strip()


def _decimal_text(value: Decimal | float | int | str) -> str:
    decimal_value = Decimal(str(value))
    rendered = format(decimal_value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _parse_positive_decimal(value: object, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"{field} must be a finite positive decimal string") from error
    if not parsed.is_finite() or parsed <= 0:
        raise ValueError(f"{field} must be a finite positive decimal string")
    return parsed


def _dedupe_text(values: Iterable[object]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean(value)
        normalized = text.casefold()
        if text and normalized not in seen:
            seen.add(normalized)
            result.append(text)
    return tuple(result)


def _is_solid(stock: InventoryMaterial) -> bool:
    probe = " ".join((stock.physical_form, stock.raw_name, stock.identity_name, stock.name)).casefold()
    return stock.physical_form.casefold() in {"crystals", "powder", "solid"} or any(
        marker in probe for marker in _SOLID_MARKERS
    )


def _explicit_material_requested(text: str, stock: InventoryMaterial) -> bool:
    haystack = _key(text)
    candidates = {_key(stock.name), _key(stock.identity_name)}
    if any(candidate and candidate in haystack for candidate in candidates):
        return True
    distinctive = [
        token
        for token in _key(stock.identity_name or stock.name).split()
        if len(token) >= 5
        and token
        not in {
            "absolute",
            "acetate",
            "alcohol",
            "essential",
            "methyl",
            "ethyl",
            "resinoid",
            "super",
        }
    ]
    if not distinctive:
        return False
    if "ambrox" in distinctive and "ambrox" in haystack:
        return True
    return any(re.search(rf"(?<!\w){re.escape(token)}(?!\w)", haystack) for token in distinctive)


def _material_avoided(candidate: StockCandidate, avoid: Sequence[str]) -> bool:
    probe = _key(" ".join((candidate.stock.name, candidate.stock.identity_name)))
    for item in avoid:
        avoided = _key(item)
        if avoided and (avoided in probe or probe in avoided):
            return True
    return False


def _descriptor_direction(text: str, start: int) -> float:
    prefix = text[max(0, start - 30) : start].casefold()
    if re.search(r"(?:less|avoid|without|no|not|reduce|remove|never)\s+(?:very\s+)?$", prefix):
        return -1.0
    if re.search(r"(?:more|very|stronger|clearer|extra|increase|boost)\s+(?:very\s+)?$", prefix):
        return 1.25
    return 1.0


def _descriptor_target(
    *,
    formula_name: str,
    idea: str,
    preserve: Sequence[str],
    avoid: Sequence[str],
) -> tuple[dict[str, float], list[str], str]:
    target = {dimension: 0.0 for dimension in DIMENSIONS}
    family_scores: dict[str, float] = {}
    matched: list[str] = []

    inputs = (
        (formula_name, 1.35),
        (idea, 1.0),
        (" ".join(preserve), 0.75),
        (" ".join(avoid), -0.9),
    )
    for source, source_weight in inputs:
        lowered = source.casefold()
        for rule in _DESCRIPTOR_RULES:
            rule_hit = False
            for phrase in rule.phrases:
                for match in re.finditer(rf"(?<!\w){re.escape(phrase.casefold())}(?!\w)", lowered):
                    direction = _descriptor_direction(lowered, match.start())
                    effective = source_weight * direction
                    for dimension, weight in rule.weights.items():
                        target[dimension] += effective * weight
                    family_scores[rule.family] = family_scores.get(rule.family, 0.0) + abs(effective)
                    matched.append(phrase)
                    rule_hit = True
            if rule_hit:
                continue

    if not any(abs(value) > 1e-12 for value in target.values()):
        target.update({"transparency": 0.45, "freshness": 0.3, "woody": 0.25, "floral": 0.2})
        family_scores["abstract"] = 1.0
        matched.append("balanced abstract structure")

    scale = max(1.0, max(abs(value) for value in target.values()))
    target = {key: round(value / scale, 6) for key, value in target.items()}
    family = max(family_scores.items(), key=lambda item: (item[1], item[0]))[0]
    return target, sorted(set(matched)), family


def _stock_preference_key(stock: InventoryMaterial) -> tuple[int, int, float, str]:
    return (
        int(effective_design_ready(stock)),
        int(bool(stock.fraction_basis and stock.fraction_basis != "unspecified")),
        float(stock.dilution),
        stock.stock_id,
    )


def _category_proxy_profile(stock: InventoryMaterial) -> MaterialProfile:
    """Return an explicitly heuristic profile when no identity profile exists.

    Category proxies are sufficient for a reversible design hypothesis, never
    for a measured character, intensity, pleasantness, or liking claim.
    """

    category = _key(stock.category)
    character: dict[str, float] = {dimension: 0.0 for dimension in DIMENSIONS}
    note = "heart"
    role = "modifier"
    texture = "category proxy"
    if "citrus" in category or "top" in category:
        character.update({"freshness": 8.0, "green": 2.0, "transparency": 4.0})
        note, role, texture = "top", "character", "lift"
    elif "aromatic" in category or "mint" in category:
        character.update({"freshness": 6.0, "green": 5.0, "floral": 2.0})
        note, role, texture = "top", "character", "aromatic lift"
    elif "green" in category or "fruit" in category:
        character.update({"green": 6.0, "freshness": 5.0, "sweetness": 3.0})
        note, role, texture = "heart", "character", "fresh accent"
    elif "floral" in category or "orris" in category or "violet" in category:
        character.update({"floral": 7.0, "radiance": 4.0, "powdery": 3.0})
        note, role, texture = "heart", "character", "floral body"
    elif "spice" in category:
        character.update({"spicy": 8.0, "warmth": 4.0, "freshness": 2.0})
        note, role, texture = "heart", "character", "spiced accent"
    elif "leather" in category or "smoke" in category:
        character.update({"smoky": 7.0, "animalic": 4.0, "woody": 5.0})
        note, role, texture = "base", "character", "dark structure"
    elif "resin" in category or "incense" in category or "balsamic" in category:
        character.update({"warmth": 7.0, "smoky": 4.0, "sweetness": 3.0, "woody": 4.0})
        note, role, texture = "base", "fixative", "resinous depth"
    elif "musk" in category:
        character.update({"creamy": 5.0, "transparency": 5.0, "warmth": 3.0})
        note, role, texture = "base", "fixative", "musk texture"
    elif "wood" in category or "amber" in category or "moss" in category:
        character.update({"woody": 8.0, "warmth": 5.0, "smoky": 2.0})
        note, role, texture = "base", "character", "structural depth"
    elif "sweet" in category or "gourmand" in category or "nutty" in category:
        character.update({"sweetness": 8.0, "warmth": 6.0, "creamy": 4.0})
        note, role, texture = "base", "character", "sweet body"
    else:
        character.update({"transparency": 3.0, "freshness": 2.0, "woody": 2.0})
    return MaterialProfile(
        name=stock.identity_name or stock.name,
        character=character,
        note=note,
        role=role,
        texture=texture,
        dilution=stock.dilution,
        evidence={
            "character": {
                "class": "HEURISTIC",
                "source": "inventory category proxy",
            }
        },
    )


def _candidate_catalogue(text: str) -> tuple[list[StockCandidate], Any]:
    inventory = materialize_current_inventory()
    by_identity: dict[str, StockCandidate] = {}
    for stock in inventory.stocks:
        category = stock.category.casefold()
        if (
            stock.status.casefold() != "owned"
            or not effective_design_ready(stock)
            or stock.dilution <= 0
        ):
            continue
        if any(token in category for token in _EXCLUDED_CATEGORIES):
            continue
        profile = get_profile(stock.identity_name) or get_profile(stock.name)
        profile_source = "DECLARED_MATERIAL_PROFILE"
        if profile is None:
            profile = _category_proxy_profile(stock)
            profile_source = "HEURISTIC_CATEGORY_PROXY"
        if profile.role.casefold() in _EXCLUDED_ROLES:
            continue
        explicit = _explicit_material_requested(text, stock)
        solid = _is_solid(stock)
        if solid and not explicit:
            continue
        if profile.role.casefold() in _TRACE_ROLES and not explicit:
            continue
        identity = _key(stock.identity_name or stock.name)
        candidate = StockCandidate(
            stock=stock,
            profile=profile,
            profile_source=profile_source,
            solid=solid,
            explicit=explicit,
        )
        existing = by_identity.get(identity)
        if existing is None or _stock_preference_key(stock) > _stock_preference_key(existing.stock):
            by_identity[identity] = candidate
    return list(by_identity.values()), inventory


def _group(candidate: StockCandidate) -> str:
    probe = f"{candidate.stock.category} {candidate.profile.role}".casefold()
    if "musk" in probe:
        return "musk"
    if "citrus" in probe:
        return "citrus"
    return "other"


def _profile_axis(profile: MaterialProfile, dimension: str) -> float:
    value = profile.character.get(dimension, 0.0)
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(10.0, max(0.0, numeric)) / 10.0


def _descriptor_fit(profile: MaterialProfile, weights: dict[str, float]) -> float:
    denominator = sum(abs(value) for value in weights.values() if value)
    if denominator <= 0:
        return 0.5
    total = 0.0
    for dimension, weight in weights.items():
        if not weight:
            continue
        axis = _profile_axis(profile, dimension)
        total += abs(weight) * (axis if weight > 0 else 1.0 - axis)
    return min(1.0, max(0.0, total / denominator))


def _choice_score(
    candidate: StockCandidate,
    slot: DesignSlot,
    target: dict[str, float],
    family: str,
    seed_stock_ids: set[str],
) -> tuple[float, float]:
    combined = dict(target)
    for dimension, value in slot.extra_weights.items():
        combined[dimension] = combined.get(dimension, 0.0) + value
    fit = _descriptor_fit(candidate.profile, combined)
    score = fit
    note = candidate.profile.note.casefold()
    if slot.note in note:
        score += 0.28
    elif slot.note == "heart" and note in {"top/heart", "heart/base"}:
        score += 0.16
    role = candidate.profile.role.casefold()
    if any(preferred in role for preferred in slot.preferred_roles):
        score += 0.18
    family_probe = _key(f"{candidate.stock.category} {candidate.stock.identity_name}")
    if family and _key(family) in family_probe:
        score += 0.12
    if candidate.explicit:
        score += 1.2
    if candidate.stock.stock_id in seed_stock_ids:
        score += 0.22
    if candidate.solid and slot.note != "base":
        score -= 0.8
    return score, fit


def _select_slots(
    candidates: Sequence[StockCandidate],
    *,
    slots: Sequence[DesignSlot],
    target: dict[str, float],
    family: str,
    avoid: Sequence[str],
    seed_stock_ids: set[str],
) -> tuple[SlotChoice, ...]:
    selected: list[SlotChoice] = []
    used: set[str] = set()
    group_counts: dict[str, int] = {}
    for slot in slots:
        ranked: list[tuple[float, float, StockCandidate]] = []
        for candidate in candidates:
            identity = _key(candidate.stock.identity_name or candidate.stock.name)
            if identity in used or _material_avoided(candidate, avoid):
                continue
            group = _group(candidate)
            if group in _GROUP_LIMITS and group_counts.get(group, 0) >= _GROUP_LIMITS[group]:
                continue
            score, fit = _choice_score(candidate, slot, target, family, seed_stock_ids)
            ranked.append((score, fit, candidate))
        ranked.sort(
            key=lambda item: (
                -item[0],
                -item[1],
                item[2].stock.identity_name.casefold(),
                item[2].stock.stock_id,
            )
        )
        if not ranked:
            continue
        score, fit, candidate = ranked[0]
        alternatives = tuple(
            (alternative.stock.identity_name or alternative.stock.name, round(alt_score, 6))
            for alt_score, _alt_fit, alternative in ranked[1:3]
        )
        selected.append(
            SlotChoice(
                slot=slot,
                candidate=candidate,
                score=score,
                descriptor_fit=fit,
                alternatives=alternatives,
            )
        )
        identity = _key(candidate.stock.identity_name or candidate.stock.name)
        used.add(identity)
        group = _group(candidate)
        group_counts[group] = group_counts.get(group, 0) + 1
    return tuple(selected)


def _normalize_weights(values: Sequence[float]) -> list[float]:
    total = sum(values)
    if total <= 0:
        raise ValueError("formula design weights must have a positive total")
    return [value / total for value in values]


def _refine_weights(choices: Sequence[SlotChoice]) -> tuple[list[float], list[float]]:
    initial = _normalize_weights([choice.slot.share for choice in choices])
    optimized = list(initial)
    note_indices: dict[str, list[int]] = {}
    for index, choice in enumerate(choices):
        note_indices.setdefault(choice.slot.note, []).append(index)

    for _ in range(12):
        proposal = [
            optimized[index] * (0.82 + 0.36 * choice.descriptor_fit)
            for index, choice in enumerate(choices)
        ]
        for note, indices in note_indices.items():
            del note
            original_total = sum(initial[index] for index in indices)
            proposed_total = sum(proposal[index] for index in indices)
            if proposed_total <= 0:
                continue
            for index in indices:
                lower = initial[index] * (0.65 if not choices[index].candidate.explicit else 0.85)
                upper = initial[index] * 1.35
                proposal[index] = min(upper, max(lower, proposal[index] * original_total / proposed_total))
        optimized = _normalize_weights(proposal)
    return initial, optimized


def _formula_alignment(choices: Sequence[SlotChoice], weights: Sequence[float]) -> float:
    return round(sum(weight * choice.descriptor_fit for choice, weight in zip(choices, weights)), 6)


def _integer_allocation(total: int, weights: Sequence[float]) -> list[int]:
    exact = [Decimal(total) * Decimal(str(weight)) for weight in weights]
    floor_values = [int(value.to_integral_value(rounding=ROUND_FLOOR)) for value in exact]
    remainder = total - sum(floor_values)
    order = sorted(
        range(len(exact)),
        key=lambda index: (-(exact[index] - floor_values[index]), index),
    )
    for index in order[:remainder]:
        floor_values[index] += 1
    return floor_values


def _dominant_profile_terms(profile: MaterialProfile) -> list[str]:
    return [
        dimension
        for dimension, _value in sorted(
            profile.character.items(),
            key=lambda item: (-float(item[1]), item[0]),
        )[:3]
        if float(_value) > 0
    ]


def _formula_rows(
    choices: Sequence[SlotChoice],
    weights: Sequence[float],
    liquid_total_ul: int,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    liquid_indices = [index for index, choice in enumerate(choices) if not choice.candidate.solid]
    solid_indices = [index for index, choice in enumerate(choices) if choice.candidate.solid]
    liquid_weights = _normalize_weights([weights[index] for index in liquid_indices])
    liquid_amounts = _integer_allocation(liquid_total_ul, liquid_weights)
    liquid_by_index = dict(zip(liquid_indices, liquid_amounts))

    rows: list[dict[str, Any]] = []
    solid_total = 0
    for index, (choice, weight) in enumerate(zip(choices, weights), start=0):
        stock = choice.candidate.stock
        profile = choice.candidate.profile
        if index in solid_indices:
            amount = max(10, int(round(weight * 2000)))
            unit = "mg"
            solid_total += amount
        else:
            amount = liquid_by_index[index]
            unit = "uL"
        alternatives = [
            {
                "material": name,
                "reason_not_selected": "Lower request-and-slot fit for this exact role; retain as a controlled alternative.",
            }
            for name, _score in choice.alternatives
        ]
        dominant = _dominant_profile_terms(profile)
        rows.append(
            {
                "row_id": f"design-{index + 1:02d}-{stable_payload_hash({'stock_id': stock.stock_id, 'slot': choice.slot.slot_id})[:10]}",
                "slot": choice.slot.slot_id,
                "slot_label": choice.slot.label,
                "material": stock.identity_name or stock.name,
                "stock_label": stock.raw_name or stock.name,
                "stock_id": stock.stock_id,
                "stock_fraction_decimal": _decimal_text(stock.dilution),
                "fraction_basis": stock.fraction_basis,
                "carrier": stock.carrier or None,
                "amount_decimal": str(amount),
                "amount_unit": unit,
                "operation": "MASS_ADD" if unit == "mg" else "DIRECT_ADD",
                "note": profile.note,
                "role": profile.role,
                "profile_source": choice.candidate.profile_source,
                "design_share_decimal": _decimal_text(round(weight, 8)),
                "rationale": (
                    f"Selected for {choice.slot.label.casefold()} after comparing the eligible live inventory; "
                    f"its {choice.candidate.profile_source.lower().replace('_', ' ')} is "
                    f"{profile.note}/{profile.role} with emphasis on "
                    f"{', '.join(dominant) if dominant else 'the requested structure'}."
                ),
                "alternatives_considered": alternatives,
                "design_ready": effective_design_ready(stock),
                "execution_ready": stock.execution_ready,
                "source_ref": stock.source_ref,
            }
        )
    return rows, {
        "liquid_total_ul": str(sum(liquid_by_index.values())),
        "mass_total_mg": str(solid_total),
    }


def _derive_name(idea: str) -> str:
    words = [
        word
        for word in re.findall(r"[A-Za-zÀ-ÿ0-9'-]+", idea)
        if word.casefold() not in _STOP_WORDS
    ][:4]
    return " ".join(word[:1].upper() + word[1:] for word in words) or "Untitled Formula"


def design_inventory_formula(
    *,
    idea: str,
    formula_name: str | None = None,
    liquid_concentrate_ul_decimal: str = "6000",
    max_materials: int = 30,
    must_preserve: Sequence[str] = (),
    must_avoid: Sequence[str] = (),
    previous_stock_ids: Sequence[str] = (),
    conversation_context: Sequence[str] = (),
) -> dict[str, Any]:
    """Create and boundedly refine one read-only inventory-grounded formula.

    The result is intentionally suitable for a conversational UI: it includes
    a short answer, a reviewable interpretation, initial and refined rows,
    considered alternatives, and explicit authority limits.
    """

    clean_idea = _clean(idea)
    if not clean_idea:
        raise ValueError("idea must be non-empty text")
    if not 6 <= int(max_materials) <= 60:
        raise ValueError("max_materials must be between 6 and 60")
    liquid_total = _parse_positive_decimal(
        liquid_concentrate_ul_decimal,
        "liquid_concentrate_ul_decimal",
    )
    if liquid_total != liquid_total.to_integral_value() or liquid_total > 100_000:
        raise ValueError("liquid concentrate must be a whole number of uL no greater than 100000")

    name = _clean(formula_name) or _derive_name(clean_idea)
    preserve = _dedupe_text(must_preserve)
    avoid = _dedupe_text(must_avoid)
    context = _dedupe_text(conversation_context)[-8:]
    design_text = " ".join((name, *context, clean_idea))
    candidates, inventory = _candidate_catalogue(design_text)
    if len(candidates) < 6:
        raise ValueError("insufficient design-ready inventory for concept design")

    known_materials = tuple(
        sorted(
            {candidate.stock.identity_name or candidate.stock.name for candidate in candidates},
            key=lambda value: (value.casefold(), value),
        )
    )
    interpretation = interpret_request(
        RequestInterpretationInputV1(
            original_request=clean_idea,
            known_materials=known_materials,
            desired_changes=(clean_idea,),
            must_preserve=preserve,
            must_avoid=avoid,
            execution_strategy="NEW_FORMULA",
            appeal_mode="IDENTITY_FIRST",
            comparison_evidence="DOCUMENT_ONLY",
        )
    )
    if interpretation["confirmation_required"]:
        report = {
            "schema_version": "inventory-grounded-formula-design-v1",
            "status": "WITHHELD_REQUEST_AMBIGUOUS",
            "formula_name": name,
            "request_interpretation": interpretation,
            "assistant_message": "I need the brief clarified before creating a formula because its explicit instructions conflict or leave a quantity unbound.",
            "initial_formula": None,
            "optimized_formula": None,
            "formula_action": "NO_CHANGE",
            "inventory_modified": False,
            "formula_modified": False,
            "prohibited_objectives_used": [],
            **FALSE_ACTION_AUTHORITY,
        }
        return {**report, "design_sha256": stable_payload_hash(report)}

    target, matched_descriptors, family = _descriptor_target(
        formula_name=name,
        idea=" ".join((*context, clean_idea)),
        preserve=preserve,
        avoid=avoid,
    )
    target_count = min(max_materials, len(candidates))
    choices = _select_slots(
        candidates,
        slots=_slots_for_limit(target_count),
        target=target,
        family=family,
        avoid=avoid,
        seed_stock_ids=set(previous_stock_ids),
    )
    if len(choices) < 6:
        raise ValueError("the requested constraints leave too few distinct eligible formula roles")

    initial_weights, optimized_weights = _refine_weights(choices)
    initial_alignment = _formula_alignment(choices, initial_weights)
    optimized_alignment = _formula_alignment(choices, optimized_weights)
    if optimized_alignment + 1e-12 < initial_alignment:
        optimized_weights = initial_weights
        optimized_alignment = initial_alignment
    initial_rows, initial_totals = _formula_rows(choices, initial_weights, int(liquid_total))
    optimized_rows, optimized_totals = _formula_rows(choices, optimized_weights, int(liquid_total))
    selected_names = [row["material"] for row in optimized_rows]

    optimization_status = (
        "REQUEST_ALIGNMENT_REFINED"
        if optimized_alignment > initial_alignment + 1e-6
        else "NO_NUMERIC_CHANGE_NEEDED"
    )
    request_payload = {
        "idea": clean_idea,
        "formula_name": name,
        "liquid_concentrate_ul_decimal": _decimal_text(liquid_total),
        "max_materials": max_materials,
        "must_preserve": list(preserve),
        "must_avoid": list(avoid),
        "previous_stock_ids": list(previous_stock_ids),
        "conversation_context": list(context),
        "inventory_snapshot_sha256": inventory.snapshot_sha256,
        "inventory_overlay_sha256": inventory.overlay_sha256,
        "inventory_completion_sha256": inventory.completion_sha256,
        "effective_inventory_sha256": inventory.effective_inventory_sha256,
    }
    initial_formula = {
        "rows": initial_rows,
        "separate_totals": initial_totals,
        "request_alignment_decimal": _decimal_text(initial_alignment),
    }
    optimized_formula = {
        "rows": optimized_rows,
        "separate_totals": optimized_totals,
        "request_alignment_decimal": _decimal_text(optimized_alignment),
        "basis_state": (
            "SEPARATE_LIQUID_AND_SOLID_TOTALS"
            if int(optimized_totals["mass_total_mg"]) > 0
            else "LIQUID_STOCK_VOLUME_ONLY"
        ),
    }
    report = {
        "schema_version": "inventory-grounded-formula-design-v1",
        "status": "INVENTORY_GROUNDED_DESIGN_READY",
        "request_sha256": stable_payload_hash(request_payload),
        "formula_name": name,
        "concept_family": family,
        "matched_descriptors": matched_descriptors,
        "request_interpretation": interpretation,
        "inventory": {
            "snapshot_sha256": inventory.snapshot_sha256,
            "overlay_sha256": inventory.overlay_sha256,
            "completion_sha256": inventory.completion_sha256,
            "effective_inventory_sha256": inventory.effective_inventory_sha256,
            "materialized_stock_count": len(inventory.stocks),
            "eligible_design_stock_count": len(candidates),
            "declared_profile_count": sum(
                candidate.profile_source == "DECLARED_MATERIAL_PROFILE"
                for candidate in candidates
            ),
            "category_proxy_count": sum(
                candidate.profile_source == "HEURISTIC_CATEGORY_PROXY"
                for candidate in candidates
            ),
        },
        "initial_formula": initial_formula,
        "optimized_formula": optimized_formula,
        "optimization": {
            "status": optimization_status,
            "objective": "REQUEST_DESCRIPTOR_ALIGNMENT_DIAGNOSTIC",
            "architecture_preserved": True,
            "iterations": 12,
            "initial_alignment_decimal": _decimal_text(initial_alignment),
            "optimized_alignment_decimal": _decimal_text(optimized_alignment),
            "meaning": "Relative stock shares were refined toward the named concept while preserving top, heart, and base totals.",
            "not_established": [
                "pleasantness",
                "personal liking",
                "population liking",
                "beauty",
                "sensory superiority",
            ],
        },
        "requested_material_limit": max_materials,
        "selected_material_count": len(selected_names),
        "assistant_message": (
            f"I built {name} as a {family.replace('_', ' ')} concept from {len(selected_names)} "
            f"current-inventory materials, then refined the relative shares toward "
            f"{', '.join(matched_descriptors[:4]) or 'the stated brief'}. "
            "This is a smellable design proposal, not a predicted winner; make a small pilot before accepting it."
        ),
        "formula_action": "PROPOSAL_ONLY",
        "next_step": "Review the material choices, then make a small controlled pilot only if you choose to compound it.",
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


_design_inventory_formula_v1 = design_inventory_formula


def design_inventory_formula(
    *,
    idea: str,
    formula_name: str | None = None,
    liquid_concentrate_ul_decimal: str = "6000",
    max_materials: int = 60,
    must_preserve: Sequence[str] = (),
    must_avoid: Sequence[str] = (),
    previous_stock_ids: Sequence[str] = (),
    conversation_context: Sequence[str] = (),
    execution_strategy: str | None = None,
    appeal_mode: str | None = None,
    comparison_evidence: str = "DOCUMENT_ONLY",
    active_bottle_id: str | None = None,
    design_mode: str = "FAST_SKETCH",
    variant_count: int | None = None,
) -> dict[str, Any]:
    """Use the verified semantic compiler behind the stable public import.

    The original implementation remains named above solely so historical
    artifacts can identify the implementation that produced them.  New calls
    compile a target, bind current inventory, solve role assignment globally,
    reconcile exact units, and run an independent deterministic critic.
    """

    from engine.formulation_intelligence.formula_design_runtime import design_formula

    return design_formula(
        idea=idea,
        formula_name=formula_name,
        liquid_concentrate_ul_decimal=liquid_concentrate_ul_decimal,
        max_materials=max_materials,
        must_preserve=must_preserve,
        must_avoid=must_avoid,
        previous_stock_ids=previous_stock_ids,
        conversation_context=conversation_context,
        execution_strategy=execution_strategy,
        appeal_mode=appeal_mode,
        comparison_evidence=comparison_evidence,
        active_bottle_id=active_bottle_id,
        design_mode=design_mode,
        variant_count=variant_count,
    )


__all__ = ["design_inventory_formula"]
