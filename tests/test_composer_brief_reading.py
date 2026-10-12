"""The composer reads the notes a brief names (Phase 3, step 1).

French note words in a name are read as their English notes, a stock is found
by the name people say ("pink pepper" for Pink Pepper EO), and "no sweetness"
keeps the sweet-gourmand stocks out. These pin request reading only; they make
no sensory or quality claim.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.note_phrases import translate_note_phrases
from engine.research.composition_planner import _avoid_candidate, _load_candidates
from engine.research.request_interpretation import (
    _matched_names,
    _split_constraint_values,
    plain_stock_name,
)

_PINK_PEPPER = "Pink Pepper EO (Schinus molle; neat / as supplied)"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Baie Rose Homme", "pink pepper Homme"),
        ("Baies roses et poivre noir", "pink pepper et black pepper"),
        ("Lavande Ambrée", "lavender amber"),
        ("Fleur d'Oranger", "orange blossom"),
        ("Bois de Santal", "sandalwood"),
        # Citron is also an English word (the cedrat fruit): left alone.
        ("Citron Vert", "Citron Vert"),
        # Whole words only: "Rosewood" and "ambrette" are not French notes.
        ("Rosewood ambrette", "Rosewood ambrette"),
    ],
)
def test_french_note_phrases_read_as_english_notes(text: str, expected: str) -> None:
    assert translate_note_phrases(text) == expected


def test_baie_rose_name_does_not_call_up_rose() -> None:
    result = design_formula(
        formula_name="Baie Rose Homme",
        idea="Pink pepper over dry cedar and vetiver. No vanilla, no sweetness.",
    )

    facets = result["semantic_brief"]["facets"]
    assert "rose" not in facets, facets
    rows = [row["identity_name"].casefold() for row in result["initial_formula"]["rows"]]
    assert any("pink pepper" in name for name in rows), rows
    assert not any(word in name for name in rows for word in ("cocoa", "vanill", "maltol")), rows


@pytest.mark.parametrize(
    ("name", "plain"),
    [
        (_PINK_PEPPER, "pink pepper"),
        ("Black Pepper EO", "black pepper"),
        ("Violet Leaf Absolute 10% DPG", "violet leaf"),
        ("Tonka Bean Absolute", "tonka bean"),
        ("Cocoa CO2 Extract 7.7%", ""),  # one word left: notes go through facets
        ("Rose EO", ""),
        ("Iso E Super", ""),  # no form word to drop: the name is already plain
    ],
)
def test_plain_name_drops_form_words_and_strength(name: str, plain: str) -> None:
    assert plain_stock_name(name) == plain


def test_stock_is_found_by_its_plain_name() -> None:
    names = (_PINK_PEPPER, "Black Pepper EO", "Rose EO", "Cedarwood Virginia")

    matched = _matched_names("pink pepper over dry cedar, a little rose", names)

    assert _PINK_PEPPER in matched
    assert "Black Pepper EO" not in matched
    # A single note word keeps going through the brief's facets.
    assert "Rose EO" not in matched


def test_stock_named_as_its_note_keeps_the_note_support() -> None:
    # "pink pepper" leads with Pink Pepper EO; the spice facet its "pepper"
    # calls up still adds supporting spice, so one EO does not carry the note
    # (and the named-note floor) alone.
    result = design_formula(idea="pink pepper over dry cedar")

    role_ids = [role["role_id"] for role in result["semantic_brief"]["roles"]]
    assert "facet_spice" in role_ids, role_ids
    rows = [row["identity_name"].casefold() for row in result["initial_formula"]["rows"]]
    assert any("pink pepper" in name for name in rows), rows


def test_note_with_its_own_facet_stays_with_the_facet() -> None:
    # "violet leaf" calls up the violet-leaf facet, which places the note in
    # the top with its green support; it is not turned into an exact anchor.
    matched = _matched_names("violet leaf", ("Violet Leaf Absolute",))

    assert matched == ()


def test_each_no_in_an_avoid_list_is_dropped() -> None:
    assert _split_constraint_values("No vanilla, no sweetness") == ("vanilla", "sweetness")


@pytest.fixture(scope="module")
def candidates_by_name() -> dict:
    candidates, _inventory, _known = _load_candidates(())
    return {candidate.stock.name: candidate for candidate in candidates}


@pytest.mark.parametrize("stock", ["Cocoa Absolute", "Ethyl Maltol 10%"])
def test_no_sweetness_keeps_sweet_stocks_out(candidates_by_name: dict, stock: str) -> None:
    assert _avoid_candidate(candidates_by_name[stock], ("sweetness",)) is True


def test_no_sweetness_keeps_dry_stocks(candidates_by_name: dict) -> None:
    assert _avoid_candidate(candidates_by_name["Cedarwood Virginia"], ("sweetness",)) is False


def test_no_sweetness_never_removes_a_stock_the_brief_names(candidates_by_name: dict) -> None:
    named = replace(candidates_by_name["Cocoa Absolute"], explicit=True)

    assert _avoid_candidate(named, ("sweetness",)) is False
