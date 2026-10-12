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
from engine.formulation_intelligence.formula_solver import _backs_natural_lead
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)
from engine.formulation_intelligence.note_phrases import translate_note_phrases
from engine.formulation_intelligence.semantic_brief_adapter import (
    ACCORD_SUPPORT_PROVENANCE,
    SemanticRole,
    role_identity_requirement,
)
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


# Phase 3, step 2: notes the composer had words for but lost.


def test_iris_named_beside_violet_keeps_an_irone_or_orris_row() -> None:
    # A violet profile used to replace the iris umbrella, and the umbrella
    # cannot layer a second iris-family stock beside the violet's ionone.
    result = design_formula(idea="iris and violet")

    assert result["status"].startswith("INVENTORY_GROUNDED_DESIGN_READY"), result["reason_codes"]
    role_ids = [role["role_id"] for role in result["semantic_brief"]["roles"]]
    assert "facet_violet_petals" in role_ids and "facet_iris_root" in role_ids, role_ids
    rows = [row["identity_name"].casefold() for row in result["initial_formula"]["rows"]]
    assert any("irone" in name or "orris" in name for name in rows), rows


def test_laundry_reads_as_clean_aldehydes() -> None:
    result = design_formula(idea="a white musk laundry")

    assert "aldehydic" in result["semantic_brief"]["facets"]


def test_fougere_is_lavender_over_coumarin_and_moss() -> None:
    result = design_formula(idea="an aromatic fougere")

    facets = result["semantic_brief"]["facets"]
    assert {"aromatic_lavender", "fougere_coumarin", "moss_chypre"} <= set(facets), facets
    rows = {row["slot"]: row["identity_name"].casefold() for row in result["initial_formula"]["rows"]}
    assert "lavender" in rows["facet_aromatic_lavender"], rows
    assert "coumarin" in rows["facet_fougere_coumarin"], rows


@pytest.mark.parametrize(
    ("request_text", "required"),
    [
        ("an aromatic fougere", ("lavender", "lavandin")),
        ("lavender and amber", ("lavender", "lavandin")),
        ("herbal and green", ()),
    ],
)
def test_lavender_role_names_lavender_only_when_asked(request_text: str, required: tuple) -> None:
    assert role_identity_requirement("facet_aromatic_lavender", request_text) == required


def test_lavender_named_in_a_fougere_is_the_anchor_not_a_second_lavender() -> None:
    # "lavender" anchors Lavender EO; the fougere's lavender role would need a
    # second lavender stock, which the family rule never places beside it, so
    # the anchor is the fougere's lavender.
    result = design_formula(idea="a lavender fougere with moss")

    role_ids = [role["role_id"] for role in result["semantic_brief"]["roles"]]
    assert "facet_aromatic_lavender" not in role_ids, role_ids
    assert {"facet_fougere_coumarin", "facet_moss_chypre"} <= set(role_ids), role_ids
    rows = [row["identity_name"].casefold() for row in result["initial_formula"]["rows"]]
    assert sum("lavender" in name or "lavandin" in name for name in rows) == 1, rows


# Phase 3, step 3: a natural lead keeps one of its own key aroma chemicals.

_SANDALWOOD_MOLECULES = ("javanol", "ebanol", "sandalore", "bacdanol")


def _rows_by_slot(result: dict) -> dict[str, str]:
    return {row["slot"]: row["identity_name"] for row in result["initial_formula"]["rows"]}


def test_anchored_lavender_is_backed_by_its_own_constituent() -> None:
    # "lavender" anchors Lavender EO; its note keeps one support, and that
    # support is a major constituent of the oil, not any heart material.
    rows = _rows_by_slot(design_formula(idea="a fresh lavender cologne"))

    assert rows["explicit_anchor_1"].startswith("Lavender EO"), rows
    assert rows.get("explicit_anchor_1__accord_1") in {"Linalyl Acetate", "Linalool"}, rows


def test_vetiver_oils_the_user_names_are_backed_by_a_vetiver_molecule() -> None:
    # Two vetiver oils are named; the composer still adds one vetiver molecule.
    rows = _rows_by_slot(design_formula(idea="a vetiver centred scent built on Haitian Vetiver EO"))

    support = rows.get("explicit_anchor_1__accord_1", "").casefold()
    assert "vetikon" in support or "vetiveryl" in support, rows


def test_sandalwood_oil_lead_is_backed_by_a_sandalwood_molecule() -> None:
    rows = _rows_by_slot(design_formula(idea="creamy sandalwood with real orris"))

    assert rows["facet_creamy_wood"] == "Sandalwood EO", rows
    supports = [rows.get(f"facet_creamy_wood__accord_{n}", "").casefold() for n in (1, 2)]
    assert any(word in name for name in supports for word in _SANDALWOOD_MOLECULES), rows


@pytest.fixture(scope="module")
def capabilities() -> dict:
    return {cap.identity_name: cap for cap in build_material_capability_index().capabilities}


def _support(note: str, weights: tuple[tuple[str, float], ...]) -> SemanticRole:
    return SemanticRole(
        role_id="facet_x__accord_1", label="support", note=note, function="character",
        query_terms=(), character_weights=weights, share=.04, required=False,
        provenance=ACCORD_SUPPORT_PROVENANCE,
    )


def test_a_solvent_in_a_resinoid_never_backs_it(capabilities: dict) -> None:
    # Benzyl benzoate is listed at 30% of Olibanum Resinoid (its solvent) but
    # carries no incense: it must not back the resinoid.
    role = _support("base", (("smoky", .75), ("woody", .5)))

    assert not _backs_natural_lead(capabilities["Benzyl Benzoate"], role, capabilities["Olibanum Resinoid"])


def test_only_a_natural_lead_is_backed(capabilities: dict) -> None:
    role = _support("base", (("woody", .85), ("creamy", .65)))

    assert _backs_natural_lead(capabilities["Javanol"], role, capabilities["Sandalwood EO"])
    # A molecule lead already has its own detection basis.
    assert not _backs_natural_lead(capabilities["Javanol"], role, capabilities["Sandalore"])
    # A natural is never a backer.
    assert not _backs_natural_lead(capabilities["Patchouli EO"], role, capabilities["Sandalwood EO"])
