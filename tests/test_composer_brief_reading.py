"""The composer reads the notes a brief names (Phase 3, step 1).

French note words in a name are read as their English notes, a stock is found
by the name people say ("pink pepper" for Pink Pepper EO), and "no sweetness"
keeps the sweet-gourmand stocks out. These pin request reading only; they make
no sensory or quality claim.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from engine.formulation_intelligence.family_structure import names_family_words
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
        # The reading drops accented letters: "fougère" read as no family.
        ("Fougère Agrumes", "fougere citrus"),
        ("Hespéridé, cédrat", "citrus, cedrat"),
        ("Clémentine, pomélo, zeste", "clementine, pomelo, zest"),
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


def test_a_creamy_wood_that_does_not_name_sandalwood_keeps_todays_supports() -> None:
    result = design_formula(idea="a soft creamy wood")
    rows = _rows_by_slot(result)

    assert rows["facet_creamy_wood"] == "Sandalwood EO", rows
    supports = [rows.get(f"facet_creamy_wood__accord_{n}", "").casefold() for n in (1, 2)]
    assert any(word in name for name in supports for word in _SANDALWOOD_MOLECULES), rows
    assert not any(
        row.get("accord") for row in result["initial_formula"]["rows"]
        if str(row.get("slot", "")).startswith("facet_creamy_wood")
    )


def test_a_named_sandalwood_takes_only_its_cited_helper() -> None:
    # Naming sandalwood builds the cited sandalwood accord (note_accord_specs):
    # support place 1 keeps today's same-query support, with no job, and the
    # helper in place 2 takes only the spec's stock; when that cannot go in,
    # the receipt says why and the place holds today's second support, with
    # no job, or stays empty.  No uncited molecule carries the helper's job.
    from engine.formulation_intelligence.note_accord_specs import accord_spec_for

    result = design_formula(idea="creamy sandalwood with real orris")
    rows = _rows_by_slot(result)
    assert rows["facet_creamy_wood"] == "Sandalwood EO", rows
    (helper,) = accord_spec_for("creamy_wood").helpers
    cited = {stock.name for stock in helper.stocks}
    unplaced = {
        entry["role_id"]
        for variant in result["design_variants"]
        for entry in variant["solver"].get("unplaced_accord_helpers", ())
    }
    jobs = {
        row["slot"]: row.get("accord")
        for row in result["initial_formula"]["rows"]
        if str(row.get("slot", "")).startswith("facet_creamy_wood__accord_")
    }
    first, slot = "facet_creamy_wood__accord_1", "facet_creamy_wood__accord_2"
    assert rows.get(first) not in cited and jobs.get(first) is None, (rows, jobs)
    if slot in unplaced:
        assert rows.get(slot) not in cited and jobs.get(slot) is None, (rows, jobs)
    else:
        assert rows[slot] in cited, rows
        assert jobs[slot]["job"] == helper.job, jobs


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


# Phase 3, step 4: the fragrance family's structure shapes the supporting layers.


def _brief(**kwargs: object) -> dict:
    return design_formula(**kwargs)["semantic_brief"]


@pytest.mark.parametrize(
    ("idea", "family"),
    [
        ("an aromatic fougere", "FOUGÈRE (AROMATIC FOUGÈRE)"),
        ("a fresh lavender cologne", "CITRUS / COLOGNE"),
        ("iris and violet", "IRIS / POWDERY / VIOLET"),
        ("creamy sandalwood with real orris", "WOODS (TRANSPARENT / CLEAN WOODS)"),
        # Amber leads and a flower is named: a floral amber, as on the wheel.
        ("an ambery trail of ambergris and benzoin under frangipani", "FLORAL AMBER (FLORAL ORIENTAL)"),
    ],
)
def test_brief_family_is_read_from_the_brief(idea: str, family: str) -> None:
    assert _brief(idea=idea).get("fragrance_family") == family


def test_a_brief_with_no_family_note_has_no_family() -> None:
    assert "fragrance_family" not in _brief(idea="a clean musky skin scent")


def test_a_fougere_gets_no_layer_its_structure_has_no_place_for() -> None:
    roles = {role["role_id"]: role for role in _brief(idea="an aromatic fougere")["roles"]}

    assert "heart_creamy_texture" not in roles and "heart_powder_layer" not in roles, sorted(roles)
    # Layers it keeps look first for the family's own materials.
    assert tuple(roles["top_citrus_layer"]["query_terms"][:2]) == ("bergamot", "lemon"), roles["top_citrus_layer"]


@pytest.mark.parametrize(
    ("idea", "has_citrus"),
    [
        # Given to every brief, the citrus layer put Red Mandarin EO in 26 of
        # the 34 duel and benchmark formulas (21 Oct 2026).
        ("a warm woody amber for evening", False),
        ("a clean musky skin scent", False),
        ("iris and violet", False),
        # A chypre and a fougere are built on bergamot; a cologne is citrus.
        ("rose chypre with patchouli and oakmoss depth", True),
        ("an aromatic fougere", True),
        ("an aromatic fougère", True),
        # A green opens on bergamot too; an aromatic is "often accompanied by
        # a citrus top" (docs/fragrance_families_reference.md).
        ("a green tea", True),
        ("a lavender and sage aromatic", True),
        ("a woody amber cologne for evening", True),
        ("a tangerine dream woody amber", True),
        ("a zesty woody amber", True),
        ("a warm woody amber with limes", True),
        # A citrus the brief names opens it in a family with no citrus word.
        ("a juicy pear fruit with clementine", True),
        ("a rose and jasmine bouquet with tangerine", True),
    ],
)
def test_a_citrus_top_layer_only_where_citrus_belongs(idea: str, has_citrus: bool) -> None:
    roles = {role["role_id"] for role in _brief(idea=idea)["roles"]}

    assert ("top_citrus_layer" in roles) is has_citrus, sorted(roles)
    if not has_citrus:
        # The layer's lead word does not come back as a family role instead.
        assert "family_bergamot_layer" not in roles, sorted(roles)


@pytest.mark.parametrize(
    "kwargs",
    [
        # A word the brief rejects calls for no citrus, whatever its ending,
        # accent or wording.
        {"idea": "a warm woody amber, the opposite of an eau de cologne", "must_avoid": ("eau de cologne",)},
        {"idea": "a warm woody amber, the opposite of the colognes my dad wore", "must_avoid": ("cologne",)},
        {"idea": "a warm woody amber, the opposite of a clémentine", "must_avoid": ("clémentine",)},
        {"idea": "a white musk laundry, not citrusy"},
        {"idea": "a warm woody amber for evening, nothing like a cologne"},
        # Whole words only: a limestone is no lime.
        {"idea": "a warm woody amber for evening", "formula_name": "Limestone"},
    ],
)
def test_no_citrus_layer_from_a_rejected_or_partial_word(kwargs: dict) -> None:
    roles = {role["role_id"] for role in _brief(**kwargs)["roles"]}

    assert "top_citrus_layer" not in roles, sorted(roles)


def test_a_brief_without_its_citrus_layer_still_builds() -> None:
    # Filtering the family's bergamot out of the opening bridge as well left
    # this brief with no diffusion role in Quick compose (21 Oct 2026).
    result = design_formula(idea="a powdery orris root")

    assert "top_citrus_layer" not in {role["role_id"] for role in result["semantic_brief"]["roles"]}
    assert result["status"].startswith("INVENTORY_GROUNDED_DESIGN_READY"), result["reason_codes"]


def test_family_materials_get_roles_of_their_own() -> None:
    result = design_formula(idea="a leather")
    roles = {role["role_id"]: role for role in result["semantic_brief"]["roles"]}
    rows = _rows_by_slot(result)

    # Isobutyl Quinoline leads the leather accord since Kenny's IBQ 1% in DPG became a
    # usable stock (21 Oct 2026, "IBQ 1% DPG"; Leather FO left on 16 Oct, "Just remove it"),
    # so Castoreum keeps its own accent role instead of leading.
    assert rows.get("facet_leather_suede") == "Isobutyl Quinoline", rows
    assert rows.get("family_castoreum_accent") == "Castoreum Synthetic", rows
    assert "Leather FO" not in rows.values(), rows
    # Suederal carries its own suede and leather notes (step 6), so the leather
    # accord takes it and its family layer has nothing left to place.
    assert "Suederal" in rows.values() and "family_suederal_layer" not in rows, rows
    # Castoreum is a shadow nuance: an accent, not a layer.
    assert roles["family_castoreum_accent"]["provenance"] == "ACCENT_LAYER", roles["family_castoreum_accent"]
    # The leather family's peach word places a stock only when one is named for it:
    # none was until Kenny's MySkinRecipes Peach Ketone arrived (20 Oct 2026).
    assert "family_peach_layer" in roles and rows.get("family_peach_layer") == "Peach Ketone", rows


def test_a_register_the_brief_names_keeps_its_own_notes_first() -> None:
    roles = {role["role_id"]: role for role in _brief(idea="a leather")["roles"]}

    # The base holds the requested leather: its bridge looks for leather first.
    assert roles["heart_to_base_link"]["query_terms"][0] == "leather", roles["heart_to_base_link"]
    # The heart is left open: its bridge looks first for the family's heart.
    assert roles["heart_continuity"]["query_terms"][0] == "rose", roles["heart_continuity"]


def test_an_avoided_odor_keeps_the_family_words_for_it_out_of_every_role() -> None:
    # A woody amber's heart is rose and its top cardamom; "no floral, no
    # spice" keeps them out of the bridges too, not only out of the layers.
    roles = _brief(idea="A warm woody amber for evening", must_avoid=("floral", "spice"))["roles"]

    terms = {term for role in roles for term in role["query_terms"]}
    assert not terms & {"rose", "cardamom"}, sorted(terms)


def test_a_contrasting_wood_looks_past_the_woods_the_brief_already_has() -> None:
    roles = {role["role_id"]: role for role in _brief(idea="A warm woody amber for evening")["roles"]}

    # The requested wood asks for vetiver and patchouli; the contrasting wood
    # looks for the woody amber's other woods, by the names stocks carry.
    terms = tuple(roles["base_wood_contrast"]["query_terms"])
    assert terms[:2] == ("sandalwood", "cedarwood"), terms
    assert not {"vetiver", "patchouli"} & set(terms), terms


@pytest.mark.parametrize(
    ("words", "vocabulary", "named"),
    [
        (("cedar",), {"cedarwood", "virginia"}, True),
        (("iso", "e", "super"), {"iso", "super", "neat"}, True),
        (("birch", "tar"), {"birch", "tar", "rectified"}, True),
        (("birch", "tar"), {"birch", "bud"}, False),
        (("rose",), {"rosemary", "eo"}, False),
    ],
)
def test_a_family_role_takes_a_stock_named_for_its_word(words: tuple, vocabulary: set, named: bool) -> None:
    assert names_family_words(frozenset(vocabulary), words) is named
