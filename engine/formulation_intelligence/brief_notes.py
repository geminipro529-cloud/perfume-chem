"""What the composer reads in a name and brief, and which formula rows carry it.

Two read-only views for the Lab (Phase 3 of the Lab plan):

* ``understood_notes`` lists the notes the composer would design for: the
  materials the brief names, the notes its words ask for (with their layer and
  whether the brief calls one "the star"), the words it read as notes but has no
  note for, what it avoids, and the structure the composer adds on its own. The
  Create page shows them as chips before composing.
* ``row_notes`` says, for each row of a formula, which of the name's notes the
  row's stock carries: by its own name, or only by its own odor words. A row
  that carries none shows its own profile words instead.

Both compile the brief exactly as the composer does (formula_design_runtime):
the same interpretation and the same semantic brief. "Carries" is the brief
self-check's test (a stock's name or odor words), so nothing here measures
strength, intensity, pleasantness or liking (AGENTS.md Rule 1), and nothing
changes a formula, a card or stock.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Mapping, Sequence
from typing import Any

from engine.formulation_intelligence.brief_self_check import _carries_note, _note_words
from engine.formulation_intelligence.material_capability_index import (
    MaterialCapability,
    MaterialCapabilityIndex,
    build_material_capability_index,
)
from engine.formulation_intelligence.note_phrases import translate_note_phrases
from engine.formulation_intelligence.semantic_brief_adapter import (
    _FACETS,
    _IRIS_TEXTURE,
    _LITERATURE_FACETS,
    FacetDefinition,
    SemanticBrief,
    SemanticRole,
    _key,
    _phrase_present,
    compile_semantic_brief,
)
from engine.research.request_interpretation import (
    RequestInterpretationInputV1,
    _constraints_overlap,
    interpret_request,
    plain_stock_name,
)

SCHEMA_VERSION = "brief-notes-v1"
BASIS = (
    "Read from the stocks' own names and odor words against the notes the name and "
    "brief ask for: not how strong anything smells, and not whether you will like it."
)
NOTE_PROVENANCE = "PROMPT_DERIVED_FACET"
MATERIAL_PROVENANCE = "EXPLICIT_REQUEST_MATERIAL"
# Roles the composer adds for the structure, not because a word asked for them.
_SUPPORT_PROVENANCE = "ACCORD_SUPPORT"
_PROFILE_WORDS = 3
_INDEX_TTL_SECONDS = 30.0
_INDEX_LOCK = threading.Lock()
_INDEX_CACHE: dict[str, Any] = {"at": 0.0, "index": None}

_FACETS_BY_ID: dict[str, FacetDefinition] = {
    facet.facet_id: facet
    for facet in (*_FACETS, *_LITERATURE_FACETS.values(), _IRIS_TEXTURE)
}

# The interpretation's reasons for asking before composing, in plain words.
_PROBLEM_WORDS = {
    "EXPLICIT_MATERIAL_IS_ALSO_PROHIBITED": "The brief names a material that Must avoid also lists. Take it out of one of them.",
    "REQUIRED_MATERIAL_IS_ALSO_PROHIBITED": "The brief requires a material that Must avoid also lists. Take it out of one of them.",
    "SAME_CONSTRAINT_PRESERVED_AND_AVOIDED": "Something is in both Must preserve and Must avoid.",
    "QUANTITY_WITHOUT_EXACT_MATERIAL_BINDING": "An amount in the brief is not tied to one material.",
    "CONTRADICTORY_EXACT_MATERIAL_COUNTS": "The brief gives two different material counts.",
    "MULTIPLE_APPEAL_MODES_NAMED": "The brief asks for more than one kind of appeal.",
}
_PROBLEM_DEFAULT = "The brief's instructions conflict, so the composer will ask before it composes."


def _index(index: MaterialCapabilityIndex | None) -> MaterialCapabilityIndex:
    """The given index, or one built at most every 30 seconds (the Create page asks
    again as he types; stock changes show up within that time)."""
    if index is not None:
        return index
    with _INDEX_LOCK:
        cached = _INDEX_CACHE["index"]
        if cached is None or time.monotonic() - _INDEX_CACHE["at"] > _INDEX_TTL_SECONDS:
            cached = build_material_capability_index()
            _INDEX_CACHE.update(at=time.monotonic(), index=cached)
        return cached


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def _compile(
    formula_name: str,
    request: str,
    must_avoid: Sequence[str],
    index: MaterialCapabilityIndex,
) -> tuple[dict[str, Any], SemanticBrief | None]:
    name = _clean(formula_name) or "Untitled Formula"
    text = _clean(request) or name
    interpretation = interpret_request(
        RequestInterpretationInputV1(
            original_request=text,
            known_materials=index.known_materials,
            desired_changes=(text,),
            must_avoid=tuple(item for item in (_clean(value) for value in must_avoid) if item),
        )
    )
    try:
        brief = compile_semantic_brief(
            formula_name=name,
            request=text,
            interpretation=interpretation,
            max_materials=60,
        )
    except ValueError:
        brief = None
    return interpretation, brief


def _present(text_key: str, words: Sequence[str]) -> list[str]:
    return [word for word in words if _phrase_present(text_key, word)]


def _note_chips(
    brief: SemanticBrief,
    interpretation: Mapping[str, Any],
    index: MaterialCapabilityIndex,
    name: str,
    request: str,
) -> list[dict[str, Any]]:
    """One chip per material the brief names and per note its words ask for; a fruit
    note gets a chip per named fruit, so each can be removed or starred alone."""
    request_key = f" {_key(translate_note_phrases(request))} "
    name_key = f" {_key(translate_note_phrases(name))} "
    all_key = f" {_key(translate_note_phrases(f'{name} {request}'))} "
    star = set(brief.star_role_ids)
    named = tuple(
        str(item) for item in (*interpretation.get("explicit_materials", ()), *interpretation.get("mandatory_materials", ()))
    )
    chips: list[dict[str, Any]] = []
    for role in brief.roles:
        if role.provenance == MATERIAL_PROVENANCE and role.exact_material is not None:
            material = role.exact_material
            plain = plain_stock_name(material)
            stock = next(iter(index.exact_matches(material)), None)
            phrases = [phrase for phrase in (material, plain) if phrase]
            chips.append({
                "id": role.role_id,
                "kind": "material",
                "label": stock.identity_name if stock is not None else material,
                "words": [],
                "layer": stock.note if stock is not None and stock.note in ("top", "heart", "base") else role.note,
                "star": role.role_id in star,
                "from_name": bool(_present(name_key, phrases)) and not _present(request_key, phrases),
                # A material the brief names leaves it when its words leave the brief:
                # listing it under Must avoid as well would contradict the brief.
                "remove_word": None,
                "tied_to": None,
                "star_phrase": plain or material,
            })
            continue
        if role.provenance != NOTE_PROVENANCE:
            continue
        facet_id = role.role_id.removeprefix("facet_")
        facet = _FACETS_BY_ID.get(facet_id)
        if facet_id == "fruit" and brief.requested_fruits:
            # The composer finds "the star" among the fruit note's own trigger words.
            fruit_triggers = {_key(trigger) for trigger in (facet.triggers if facet is not None else ())}
            for fruit in brief.requested_fruits:
                chips.append({
                    "id": f"{role.role_id}:{fruit}",
                    "kind": "note",
                    "label": fruit,
                    "words": [fruit],
                    "layer": role.note,
                    "star": role.role_id in star,
                    "from_name": not _phrase_present(request_key, fruit),
                    "remove_word": fruit,
                    "tied_to": None,
                    "star_phrase": fruit if _key(fruit) in fruit_triggers else None,
                })
            continue
        triggers = facet.triggers if facet is not None else role.query_terms
        fired = _present(all_key, triggers)
        word = fired[0] if fired else (triggers[0] if triggers else None)
        # Must avoid takes the word that brought the note in; a word a named
        # material answers to ("pepper" in Pink Pepper EO) would contradict the brief.
        tied = next((material for material in named if word and _constraints_overlap((material,), (word,))), None)
        tied_stock = next(iter(index.exact_matches(tied)), None) if tied else None
        chips.append({
            "id": role.role_id,
            "kind": "note",
            "label": facet_id.replace("_", " "),
            "words": list(_note_words(role, all_key)) or fired,
            "layer": role.note,
            "star": role.role_id in star,
            "from_name": not _present(request_key, triggers),
            "remove_word": None if tied else word,
            "tied_to": tied_stock.identity_name if tied_stock is not None else tied,
            "star_phrase": fired[0] if fired else None,
        })
    return chips


def _structure(brief: SemanticBrief) -> dict[str, Any]:
    family = brief.fragrance_family
    roles = []
    support = 0
    for role in brief.roles:
        if role.provenance in (NOTE_PROVENANCE, MATERIAL_PROVENANCE):
            continue
        if role.provenance == _SUPPORT_PROVENANCE:
            support += 1
            continue
        label = role.label
        if family and label.startswith(f"{family} "):
            label = label[len(family) + 1:]
        roles.append({"label": label[:1].upper() + label[1:], "layer": role.note})
    return {"family": family, "roles": roles, "supporting_materials": support}


def understood_notes(
    *,
    formula_name: str,
    message: str,
    must_avoid: Sequence[str] = (),
    conversation_context: Sequence[str] = (),
    index: MaterialCapabilityIndex | None = None,
) -> dict[str, Any]:
    """The notes the composer would design for, read from the name and brief."""
    name = _clean(formula_name)
    context = [_clean(item) for item in conversation_context if _clean(item)][-8:]
    request = " ".join((*context, _clean(message)))
    capabilities = _index(index)
    interpretation, brief = _compile(name, request, must_avoid, capabilities)
    problems = [
        _PROBLEM_WORDS.get(code, _PROBLEM_DEFAULT)
        for code in dict.fromkeys(interpretation.get("ambiguities", ()))
    ] if interpretation.get("confirmation_required") else []
    if interpretation.get("confirmation_required") and not problems:
        problems = [_PROBLEM_DEFAULT]
    return {
        "schema_version": SCHEMA_VERSION,
        "basis": BASIS,
        "notes": _note_chips(brief, interpretation, capabilities, name, request) if brief else [],
        "unmapped": list(brief.unmapped_requested_notes) if brief else [],
        "avoided": [str(item) for item in interpretation.get("must_avoid", ())],
        "structure": _structure(brief) if brief else {"family": None, "roles": [], "supporting_materials": 0},
        "star_marker": _phrase_present(f" {_key(request)} ", "the star"),
        "needs_confirmation": bool(interpretation.get("confirmation_required")),
        "problems": problems,
        "inventory_modified": False,
        "formula_modified": False,
    }


def _profile(capability: MaterialCapability) -> list[str]:
    ranked = sorted((item for item in capability.character if item[1] > 0), key=lambda item: (-item[1], item[0]))
    return [word for word, _weight in ranked[:_PROFILE_WORDS]]


def _capability_for(
    row: Mapping[str, Any],
    by_stock: Mapping[str, MaterialCapability],
    index: MaterialCapabilityIndex,
) -> MaterialCapability | None:
    stock_id = str(row.get("stock_id") or "")
    if stock_id in by_stock:
        return by_stock[stock_id]
    material = _clean(row.get("material"))
    if not material:
        return None
    matches = index.exact_matches(material)
    exact = [item for item in matches if item.identity_name.casefold() == material.casefold()]
    return (exact or list(matches) or [None])[0]


def _carried(
    capability: MaterialCapability,
    role: SemanticRole,
    chip: Mapping[str, Any],
    all_key: str,
    request: str,
    index: MaterialCapabilityIndex,
) -> str | None:
    if chip["kind"] == "material":
        stock_ids = {item.stock_id for item in index.exact_matches(str(role.exact_material))}
        return "identity" if capability.stock_id in stock_ids else None
    # A fruit chip is one named fruit; a note no word of the name asks for by its
    # query terms ("fougere" brings in lavender) is carried by any of its terms.
    words = chip["words"] if ":" in str(chip["id"]) else (list(_note_words(role, all_key)) or list(role.query_terms))
    return _carries_note(capability, role, request, words)


def row_notes(
    *,
    formula_name: str,
    rows: Sequence[Mapping[str, Any]],
    brief: str = "",
    index: MaterialCapabilityIndex | None = None,
) -> dict[str, Any]:
    """For each row, the name's notes its stock carries, or its own profile words."""
    capabilities = _index(index)
    name = _clean(formula_name)
    request = _clean(brief)
    interpretation, semantic = _compile(name, request, (), capabilities)
    chips = _note_chips(semantic, interpretation, capabilities, name, request) if semantic else []
    roles = {role.role_id: role for role in semantic.roles} if semantic else {}
    all_key = f" {_key(translate_note_phrases(f'{name} {request}'))} "
    reading = translate_note_phrases(f"{name} {request}")
    by_stock = {capability.stock_id: capability for capability in capabilities.capabilities}
    out_rows = []
    for row in rows:
        capability = _capability_for(row, by_stock, capabilities)
        carries: list[dict[str, Any]] = []
        if capability is not None:
            for chip in chips:
                role = roles[str(chip["id"]).split(":", 1)[0]]
                kind = _carried(capability, role, chip, all_key, reading, capabilities)
                if kind:
                    carries.append({
                        "id": chip["id"],
                        "kind": chip["kind"],
                        "label": chip["label"],
                        "by": "name" if kind == "identity" else "odor",
                        "star": chip["star"],
                    })
        out_rows.append({
            "material": _clean(row.get("material")),
            "stock_id": capability.stock_id if capability is not None else None,
            "found": capability is not None,
            "carries": carries,
            "profile": _profile(capability) if capability is not None else [],
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "basis": BASIS,
        "formula_name": name,
        "notes": chips,
        "rows": out_rows,
        "inventory_modified": False,
        "formula_modified": False,
    }


__all__ = ["BASIS", "SCHEMA_VERSION", "row_notes", "understood_notes"]
