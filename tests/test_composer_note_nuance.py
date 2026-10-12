"""Coconut and apricot are notes of their own, and a hint stays a hint (Phase 3, step 7).

A brief that asked for "coconut cream" placed no coconut at all, and "a hint of apricot"
was not read. Coconut and apricot now each call up a role that only a stock whose own
description names the note may fill (the signature notes of step 6). A note asked for as
a nuance ("hint of", "a little", "barely") becomes a modifier with no accord of its own.
These pin request reading and stock eligibility only; they make no sensory, dose or
quality claim.
"""

from __future__ import annotations

from functools import lru_cache

import pytest

from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)
from engine.formulation_intelligence.semantic_brief_adapter import (
    ACCORD_SUPPORT_SEPARATOR,
    compile_semantic_brief,
)


def _brief(text: str, max_materials: int = 30):
    return compile_semantic_brief(
        formula_name="Nuance regression", request=text, max_materials=max_materials,
        interpretation={"explicit_materials": [], "must_avoid": [],
                        "must_preserve": [], "material_count_constraints": []},
    )


def _roles(text: str) -> dict:
    return {role.role_id: role for role in _brief(text).roles}


@lru_cache(maxsize=1)
def _smelling_of() -> dict[str, frozenset[str]]:
    index = build_material_capability_index()
    return {
        note: frozenset(c.identity_name for c in index.capabilities if note in c.descriptor_vocabulary)
        for note in ("coconut", "apricot")
    }


def _facet_rows(idea: str) -> dict[str, str]:
    result = design_formula(idea=idea)
    return {
        row["slot"]: row["identity_name"]
        for row in result["optimized_formula"]["rows"]
        if row["slot"].startswith("facet_")
    }


@pytest.mark.parametrize("note", ["coconut", "apricot"])
def test_coconut_and_apricot_are_notes_of_their_own(note: str) -> None:
    roles = _roles(f"A {note} and vanilla perfume")

    assert roles[f"facet_{note}"].descriptor_requirement == note
    assert roles[f"facet_{note}"].function == "character"
    # Not any fruit: the umbrella fruit role (and its esters) is not called up.
    assert "facet_fruit" not in roles


@pytest.mark.parametrize(
    "text",
    [
        "Fresh frangipani, creamy, hint of apricot, soft vanilla",
        "Fresh frangipani, creamy and a little apricot, then amber",
        "A frangipani with a touch of ripe apricot",
    ],
)
def test_a_note_asked_for_as_a_hint_is_a_modifier_without_an_accord(text: str) -> None:
    roles = _roles(text)
    apricot = roles["facet_apricot"]

    assert apricot.function == "modifier"
    # The share and ceiling the smoke and animalic modifiers already use.
    assert (apricot.share, apricot.max_raw_share) == (.035, .07)
    assert not any(role_id.startswith(f"facet_apricot{ACCORD_SUPPORT_SEPARATOR}") for role_id in roles)


def test_a_note_named_in_full_anywhere_keeps_its_full_role() -> None:
    full = _roles("An apricot and vanilla perfume")["facet_apricot"]
    both = _roles("Apricot jam over vanilla, with a hint of apricot skin")["facet_apricot"]
    other = _roles("A hint of vanilla over a ripe apricot")["facet_apricot"]

    for role in (full, both, other):
        assert role.function == "character"
        assert (role.share, role.max_raw_share) == (.065, .12)


def test_coconut_cream_is_led_by_a_stock_that_smells_of_coconut() -> None:
    facets = _facet_rows("Ripe pineapple over coconut cream and dark vanilla")

    assert facets["facet_coconut"] in _smelling_of()["coconut"]
    # Pineapple still has its own fruit role beside the coconut.
    assert "facet_fruit" in facets


def test_a_hint_of_apricot_is_one_stock_that_smells_of_apricot() -> None:
    facets = _facet_rows(
        "One flower in full: fresh frangipani petals on skin, creamy, hint of apricot, "
        "deepened with orris butter, sandalwood and soft vanilla."
    )

    assert facets["facet_apricot"] in _smelling_of()["apricot"]
    assert not any(slot.startswith(("facet_apricot__", "facet_fruit")) for slot in facets)
