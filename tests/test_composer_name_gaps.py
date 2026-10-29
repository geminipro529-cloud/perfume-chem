"""The composer keeps the words a brief names (Phase 5 re-test findings 1-3).

A curated capsule ("skin scent") keeps the notes the brief names and says when one
has no usable stock, "no X" keeps every stock named for X out, a stated material
ceiling holds inside a capsule, and "oakmoss" and "sea spray" call up their notes.
These pin request reading only; they make no sensory or quality claim.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.semantic_brief_adapter import _matched_facets
from engine.research.composition_planner import (
    NoteAnchor,
    _avoid_candidate,
    _load_candidates,
    _note_anchor_message,
)
from engine.research.request_interpretation import (
    RequestInterpretationInputV1,
    interpret_request,
)
from tests.reheld_overlay import (  # noqa: F401 (fixture)
    neat_ambrettolide_owned,
    neat_ambrettolide_still_owned,
)


def _rows(result: dict) -> list[dict]:
    return (result.get("optimized_formula") or {}).get("rows", [])


def _materials(result: dict) -> list[str]:
    return [str(row["material"]).casefold() for row in _rows(result)]


# Finding 1: a skin scent dropped every note the brief named.


@pytest.mark.usefixtures("neat_ambrettolide_still_owned")
def test_a_skin_scent_keeps_the_notes_the_brief_names() -> None:
    result = design_formula(idea="a transparent oud and incense skin scent")

    assert result["concept_family"] == "intimate_skin"
    materials = _materials(result)
    assert any("agarwood" in name for name in materials)
    assert any(word in name for name in materials for word in ("olibanum", "frankincense", "myrrh"))
    # The capsule is still the skin scent around them.
    assert any("ambrettolide" in name for name in materials)
    assert "oud (" in result["assistant_message"]
    assert "incense (" in result["assistant_message"]


def test_a_skin_scent_that_names_no_note_is_the_capsule_alone() -> None:
    result = design_formula(idea="a quiet skin scent")

    assert result["concept_family"] == "intimate_skin"
    assert not any(str(row["slot"]).startswith("named_note_") for row in _rows(result))
    assert "you named" not in result["assistant_message"]


def test_a_named_note_without_usable_stock_is_said_not_dropped() -> None:
    anchors = (
        NoteAnchor("oud", ("Black Agarwood Artificial",), "base", "character", .065, .12),
        NoteAnchor("tea", (), "heart", "character", .085, .15, held=("Black Tea Base",)),
    )
    rows = [{"slot": "named_note_1", "material": "Black Agarwood Artificial"}]

    message, issues = _note_anchor_message(anchors, rows)

    assert "oud (Black Agarwood Artificial)" in message
    assert "I could not place tea" in message
    assert "Black Tea Base would once its details are filled in on the Stock page" in message
    assert issues == ["UNPLACED_REQUESTED_NOTE:tea"]


def test_a_skin_scent_keeps_the_stated_material_ceiling() -> None:
    result = design_formula(
        idea="a rich vetiver and lavender skin scent for winter, without musky using at most 10 materials",
    )

    assert result["concept_family"] == "intimate_skin"
    assert 0 < len(_rows(result)) <= 10


# Finding 2: an excluded note word let stocks named for it through.


@pytest.fixture(scope="module")
def candidates_by_name(tmp_path_factory: pytest.TempPathFactory) -> dict:
    with neat_ambrettolide_owned(tmp_path_factory.mktemp("overlay")):
        candidates, _inventory, _known = _load_candidates(())
    return {candidate.stock.name: candidate for candidate in candidates}


@pytest.mark.parametrize(
    ("stock", "avoid"),
    [
        ("Black Agarwood Artificial", "oud"),
        ("Sandalore", "sandalwood"),
        ("Javanol", "sandalwood"),
        ("Oakmoss Absolute", "mossy"),
        ("Evernyl 10%", "mossy"),
        ("Oakmoss Absolute", "oakmoss"),
        # Kenny's neat Ambrettolide (his 2026-10-08 word) shows beside the 10%
        # since the Stock page stopped hiding his own records; both are named.
        ("Ambrettolide (neat)", "musky"),
        ("Ambrettolide 10%", "musky"),
        # One bottle since 2026-10-14; the bracketed stock text no longer splits
        # it into "Olibanum Resinoid 50%" and "Olibanum Resinoid (viscous, 50%".
        ("Olibanum Resinoid", "incense"),
        ("Myrrh EO", "incense"),
        ("Coumarin 10%", "tonka"),
    ],
)
def test_an_excluded_note_keeps_its_stocks_out(candidates_by_name: dict, stock: str, avoid: str) -> None:
    assert _avoid_candidate(candidates_by_name[stock], (avoid,)) is True


@pytest.mark.parametrize(
    ("stock", "avoid"),
    [
        # An ionone is a violet-woody molecule, not orris.
        ("Dihydro Beta Ionone", "iris"),
        ("Cedarwood Virginia", "sandalwood"),
        ("Evernyl 10%", "oud"),
    ],
)
def test_an_excluded_note_keeps_other_stocks(candidates_by_name: dict, stock: str, avoid: str) -> None:
    assert _avoid_candidate(candidates_by_name[stock], (avoid,)) is False


def test_an_excluded_note_never_removes_a_stock_the_brief_names(candidates_by_name: dict) -> None:
    named = replace(candidates_by_name["Sandalore"], explicit=True)

    assert _avoid_candidate(named, ("sandalwood",)) is False


def test_a_count_clause_after_an_exclusion_is_the_count_not_the_note() -> None:
    result = interpret_request(RequestInterpretationInputV1(
        original_request="a vetiver skin scent, without musky using at most 10 materials",
        desired_changes=("a vetiver skin scent, without musky using at most 10 materials",),
    ))

    assert result["must_avoid"] == ["musky"]
    assert {(row["kind"], row["count"]) for row in result["material_count_constraints"]} == {("MAXIMUM", 10)}


_MUSK_NAMES = ("musk", "ambrettolide", "brassylate", "exaltolide", "galaxolide", "habanolide",
               "helvetolide", "romandolide", "zenolide")


@pytest.mark.parametrize(
    ("idea", "kept_out"),
    [
        (
            "a smoky vanilla and patchouli eau de parfum on a bed of cedar for the office, no oud",
            ("agarwood", "oud"),
        ),
        (
            "a dry green and leather skin scent for evening, without sandalwood",
            ("sandal", "javanol", "ebanol", "bacdanol"),
        ),
        (
            "a rich vetiver and lavender skin scent for winter, without musky using at most 10 materials",
            _MUSK_NAMES,
        ),
        ("a transparent leather and oud cologne drying down to sea spray, no mossy", ("moss", "evernyl")),
    ],
)
def test_an_excluded_note_stays_out_of_the_formula(idea: str, kept_out: tuple[str, ...]) -> None:
    materials = _materials(design_formula(idea=idea))

    assert materials
    assert not [name for name in materials if any(word in name for word in kept_out)]


# Finding 3: "oakmoss" and "sea spray" called up no note.


@pytest.mark.parametrize(
    ("text", "facet_id"),
    [
        ("an oakmoss cologne", "moss_chypre"),
        ("an oak moss cologne", "moss_chypre"),
        ("a citrus cologne drying down to sea spray", "rain_water"),
        ("a sea breeze cologne", "rain_water"),
    ],
)
def test_everyday_note_words_call_up_their_facet(text: str, facet_id: str) -> None:
    assert facet_id in {facet.facet_id for facet in _matched_facets(text, (), {})}


def test_an_oakmoss_brief_gets_a_moss_stock() -> None:
    result = design_formula(idea="an elegant oakmoss and lavender cologne")

    assert any(word in name for name in _materials(result) for word in ("oakmoss", "evernyl"))
