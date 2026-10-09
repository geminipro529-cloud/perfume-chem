"""Inventory-bound material capabilities for structural formula design.

The index is intentionally assembled from the current materialized inventory
and existing annotated material profiles at runtime.  It exposes design
vocabulary and provenance without treating legacy hedonic fields, OAV, sales,
or ingredient count as an aesthetic objective.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from typing import Iterable, Sequence

from engine.formulation_intelligence import architecture_rules_v5 as rules_v5
from engine.formulation_intelligence.literature_knowledge import material_knowledge
from engine.research.composition_planner import (
    Candidate,
    _candidate_group,
    _candidate_identity_probe,
    _candidate_matches_text,
    _candidate_probe,
    _load_candidates,
)


def _key(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _tokens(values: Iterable[object]) -> frozenset[str]:
    result: set[str] = set()
    for value in values:
        for token in _key(value).split():
            if len(token) >= 3:
                result.add(token)
    return frozenset(result)


def _usable_odor_description(description: str) -> str:
    """Stock-intake identity placeholders are not own-material odor evidence.

    This rejects the intake's explicit unreviewed sentinels, not the stock or
    other independently annotated fields. It does not promote the remaining
    supplier/profile text into a sensory measurement.
    """
    normalized = _key(description)
    if (
        not normalized
        or normalized.startswith(("supplier labelled ", "supplier labeled "))
        or "detailed odor profile not reviewed" in normalized
        or "detailed odour profile not reviewed" in normalized
    ):
        return ""
    return description


# Conjunction across groups, alternatives within a group. Whole own-descriptor
# tokens only: neither a product name nor generic freshness proves a facet.
# These are eligibility heuristics, not sensory-recognition calibrations.
_DESCRIPTOR_REQUIREMENTS: dict[str, tuple[frozenset[str], ...]] = {
    "fruit": (frozenset({
        "fruit", "fruity", "pear", "apple", "peach", "plum", "berry", "mango",
        "pineapple", "lychee", "litchi", "apricot", "guava", "melon", "cassis",
    }),),
    "rose": (frozenset({"rose", "rosy"}),),
    "jasmine": (frozenset({"jasmine", "jasmin", "jasminic"}),),
    "bitter_resin_green": (
        frozenset({"green"}), frozenset({"bitter"}), frozenset({"resin", "resinous"}),
    ),
    "watery_leaf": (frozenset({"leaf", "leafy"}), frozenset({"watery", "aquatic"})),
    "citrus_leaf_floral": (
        frozenset({"leaf", "leafy"}), frozenset({"citrus"}), frozenset({"floral"}),
    ),
    # Layer and accent families (semantic_brief_adapter._NOTE_LAYERS).
    "top_citrus": (frozenset({
        "citrus", "lemon", "bergamot", "orange", "mandarin", "grapefruit", "lime", "yuzu",
    }),),
    "top_green": (frozenset({"green", "leaf", "leafy", "herbal", "aromatic"}),),
    "top_sparkle": (frozenset({"aldehydic", "aldehyde", "sparkling", "fruit", "fruity"}),),
    "heart_floral": (frozenset({
        "floral", "rose", "rosy", "jasmine", "muguet", "petal", "blossom",
    }),),
    "heart_powder": (frozenset({"powdery", "powder", "iris", "orris", "violet", "velvety"}),),
    "heart_spice": (frozenset({"spicy", "spice"}),),
    "base_shadow": (frozenset({"smoky", "smoke", "leather", "animalic"}),),
    "base_wood": (frozenset({"woody", "wood", "cedar", "sandalwood", "vetiver"}),),
    "base_amber": (frozenset({"amber", "ambery", "ambergris"}),),
    "base_musk": (frozenset({"musk", "musky"}),),
    "base_resin": (frozenset({
        "balsamic", "balsam", "resin", "resinous", "benzoin", "labdanum", "incense", "cocoon",
    }),),
}


@dataclass(frozen=True, slots=True)
class MaterialCapability:
    candidate: Candidate
    stock_id: str
    identity_name: str
    stock_label: str
    note: str
    function_terms: frozenset[str]
    vocabulary: frozenset[str]
    identity_vocabulary: frozenset[str]
    character: tuple[tuple[str, float], ...]
    group: str
    profile_source: str
    design_ready: bool
    execution_ready: bool
    knowledge_claim_ids: tuple[str, ...] = ()
    knowledge_role_slots: tuple[str, ...] = ()
    descriptor_vocabulary: frozenset[str] = frozenset()
    architecture_v5_vocabulary: frozenset[str] = frozenset()

    @property
    def character_map(self) -> dict[str, float]:
        return dict(self.character)


@dataclass(frozen=True, slots=True)
class MaterialCapabilityIndex:
    capabilities: tuple[MaterialCapability, ...]
    inventory_snapshot_sha256: str
    inventory_overlay_sha256: str
    inventory_completion_sha256: str
    effective_inventory_sha256: str
    known_materials: tuple[str, ...]

    def with_explicit_materials(self, materials: Sequence[str]) -> MaterialCapabilityIndex:
        """Rebind only request flags on this snapshot; never reuse across calls.

        The candidate loader changes only ``explicit`` for this argument. Keep
        the same matcher, capabilities, stock hashes and ordering, without a
        second inventory materialization or source review within one request.
        """
        if not materials and not any(c.candidate.explicit for c in self.capabilities):
            return self
        return replace(self, capabilities=tuple(
            replace(c, candidate=replace(c.candidate, explicit=any(
                _candidate_matches_text(c.candidate, value) for value in materials
            ))) for c in self.capabilities
        ))

    def exact_matches(self, material: str) -> tuple[MaterialCapability, ...]:
        return tuple(
            capability
            for capability in self.capabilities
            if _candidate_matches_text(capability.candidate, material)
        )


def _capability(candidate: Candidate) -> MaterialCapability:
    profile = candidate.profile
    stock = candidate.stock
    identity = stock.identity_name or stock.name
    reviewed = material_knowledge(identity)
    identity_words = _tokens(
        (
            identity,
            stock.name,
            re.sub(r"\s*#.*$", "", stock.raw_name),
        )
    )
    # Own-material annotations only. Names, stock categories/comments, carriers
    # and synergy partners are context, not evidence of an odor descriptor.
    # A category proxy cannot turn freshness + sweetness into a fruit label.
    own_descriptors = () if candidate.profile_source == "HEURISTIC_CATEGORY_PROXY" else (
        _usable_odor_description(profile.odor_description), profile.texture, profile.or_family or "",
        *profile.formulation_roles,
        *(key for key, value in profile.character.items() if float(value) > 0),
    )
    descriptor_vocabulary = _tokens((*own_descriptors, *(reviewed["vocabulary"] if reviewed else ())))
    # v5 does not use role/application lists or numeric character dimensions as
    # own-odor evidence. Keep the historical vocabulary unchanged for replay.
    v5_descriptors = () if candidate.profile_source == "HEURISTIC_CATEGORY_PROXY" else (
        rules_v5.positive_description(_usable_odor_description(profile.odor_description)),
        rules_v5.positive_description(profile.texture),
    )
    v5_vocabulary = _tokens((*v5_descriptors, *(reviewed["vocabulary"] if reviewed else ())))
    if "fruit" in descriptor_vocabulary or "fruity" in descriptor_vocabulary:
        descriptor_vocabulary |= frozenset(("fruit", "fruity"))
    vocabulary = _tokens(
        (
            identity,
            stock.name,
            stock.raw_name,
            stock.category,
            profile.name,
            profile.note,
            profile.role,
            profile.texture,
            profile.odor_description,
            profile.or_family or "",
            *profile.formulation_roles,
            *profile.synergies,
            *(reviewed["vocabulary"] if reviewed else ()),
        )
    )
    vocabulary |= descriptor_vocabulary & {"fruit", "fruity"}
    functions = _tokens(
        (
            profile.role,
            profile.texture,
            profile.note,
            *profile.formulation_roles,
            *(reviewed["role_slots"] if reviewed else ()),
        )
    )
    return MaterialCapability(
        candidate=candidate,
        stock_id=stock.stock_id,
        identity_name=identity,
        stock_label=stock.raw_name or stock.name,
        note=profile.note.casefold(),
        function_terms=functions,
        vocabulary=vocabulary,
        identity_vocabulary=identity_words,
        character=tuple(sorted((key, float(value)) for key, value in profile.character.items())),
        group=_candidate_group(candidate),
        profile_source=candidate.profile_source,
        design_ready=bool(stock.design_ready if stock.design_ready is not None else stock.execution_ready),
        execution_ready=bool(stock.execution_ready),
        knowledge_claim_ids=tuple(reviewed["claim_ids"]) if reviewed else (),
        knowledge_role_slots=tuple(reviewed["role_slots"]) if reviewed else (),
        descriptor_vocabulary=descriptor_vocabulary,
        architecture_v5_vocabulary=v5_vocabulary,
    )


def supports_descriptor_requirement(capability: MaterialCapability, requirement: str | None) -> bool:
    """Closed own-descriptor eligibility; never sensory equivalence or calibration."""
    if requirement is None:
        return True
    if not isinstance(requirement, str):
        return False
    if requirement.startswith("v5_"):
        return rules_v5.eligible(capability.identity_name, capability.architecture_v5_vocabulary, requirement)
    groups = _DESCRIPTOR_REQUIREMENTS.get(requirement)
    return groups is not None and all(capability.descriptor_vocabulary & group for group in groups)


def architecture_avoid_conflict(
    capability: MaterialCapability, requirement: str | None, avoid: Sequence[str],
    *, all_roles: bool = False,
) -> bool:
    return bool((all_roles or (requirement and requirement.startswith("v5_"))) and
                rules_v5.own_odor_avoid_conflict(capability.architecture_v5_vocabulary, avoid))


def build_material_capability_index(
    explicit_materials: Sequence[str] = (),
) -> MaterialCapabilityIndex:
    candidates, inventory, known = _load_candidates(explicit_materials)
    capabilities = tuple(
        sorted(
            (_capability(candidate) for candidate in candidates),
            key=lambda item: (
                not item.design_ready,
                item.identity_name.casefold(),
                item.stock_id,
            ),
        )
    )
    return MaterialCapabilityIndex(
        capabilities=capabilities,
        inventory_snapshot_sha256=inventory.snapshot_sha256,
        inventory_overlay_sha256=inventory.overlay_sha256,
        inventory_completion_sha256=inventory.completion_sha256,
        effective_inventory_sha256=inventory.effective_inventory_sha256,
        known_materials=known,
    )


def _term_score(capability: MaterialCapability, query_terms: Sequence[str]) -> float:
    identity_text = _candidate_identity_probe(capability.candidate)
    all_text = _candidate_probe(capability.candidate)
    score = 0.0
    for rank, term in enumerate(query_terms):
        normalized = _key(term)
        if not normalized:
            continue
        weight = max(.25, 1.0 - rank * .045)
        words = set(normalized.split())
        exact_identity_match = (
            normalized in identity_text
            if " " in normalized
            else normalized in capability.identity_vocabulary
        )
        exact_capability_match = (
            normalized in all_text
            if " " in normalized
            else normalized in capability.vocabulary
        )
        if exact_identity_match:
            score += 5.0 * weight
        elif exact_capability_match:
            score += 3.0 * weight
        elif words and words <= capability.vocabulary:
            score += 2.2 * weight
        else:
            overlap = len(words & capability.vocabulary)
            score += min(1.4, overlap * .35) * weight
    return score


def capability_role_score(
    capability: MaterialCapability,
    *,
    query_terms: Sequence[str],
    character_weights: Sequence[tuple[str, float]],
    note: str,
    function: str,
    exact_material: str | None,
    selected: Sequence[MaterialCapability] = (),
    previous_stock_ids: frozenset[str] = frozenset(),
) -> float | None:
    """Return a structural fit score, or ``None`` for an exact mismatch.

    The number is used only to solve a material-role assignment.  It is never
    exposed as pleasantness, quality, contribution, or sensory confidence.
    """

    if exact_material is not None:
        if not _candidate_matches_text(capability.candidate, exact_material):
            return None
        exact_bonus = 100.0
    else:
        exact_bonus = 0.0

    score = exact_bonus + _term_score(capability, query_terms)
    character = capability.character_map
    for dimension, weight in character_weights:
        # Signed weights express direction only.  Negative sweetness, for
        # example, rewards low annotated sweetness without claiming liking.
        value = max(0.0, min(10.0, character.get(dimension, 0.0))) / 10.0
        score += (value if weight >= 0 else 1.0 - value) * abs(weight) * 3.0

    if capability.note == note.casefold():
        score += 1.25
    elif note.casefold() == "heart" and capability.note in {"top", "base"}:
        score -= .35
    else:
        score -= .8

    function_key = _key(function)
    if function_key in capability.function_terms:
        score += 1.0
    if capability.design_ready:
        score += .35
    if capability.execution_ready:
        score += .12
    if capability.profile_source == "HEURISTIC_CATEGORY_PROXY":
        score -= .35
    if capability.stock_id in previous_stock_ids:
        score += .28

    selected_names = {_key(item.identity_name) for item in selected}
    synergy_words = _tokens(capability.candidate.profile.synergies)
    for selected_name in selected_names:
        selected_tokens = set(selected_name.split())
        if selected_tokens & synergy_words:
            score += .35

    # Discourage near-duplicate rows without claiming perceptual redundancy.
    if selected:
        vector = character
        for other in selected:
            other_vector = other.character_map
            populated = set(vector) | set(other_vector)
            if not populated:
                continue
            mean_difference = sum(
                abs(vector.get(key, 0.0) - other_vector.get(key, 0.0))
                for key in populated
            ) / len(populated)
            if mean_difference < .75 and capability.note == other.note:
                score -= .55
    return score


__all__ = [
    "MaterialCapability",
    "MaterialCapabilityIndex",
    "build_material_capability_index",
    "capability_role_score",
]
