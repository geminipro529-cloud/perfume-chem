"""What the composer reads in a name and brief, and which rows carry it (Lab Phase 3, F3 and F7).

The chips on Create a formula and the "why" line on each editor row come from the
same compiled brief the composer designs from. These pin the contracts the page
relies on: a chip's remove word really takes that note out without contradicting the
brief, its star phrase really makes it the star, and a row carries a note only by its
stock's own name or odor words. No sensory or quality claim (AGENTS.md Rule 1).
"""

from __future__ import annotations

import pytest

from engine.formulation_intelligence.brief_notes import row_notes, understood_notes
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)

BAIE_ROSE = "A pink pepper and cedar fougere with vetiver"
RASPBERRY = "A raspberry rose with lychee and a little oud"


@pytest.fixture(scope="module")
def index():
    return build_material_capability_index()


def _chips(result: dict) -> dict[str, dict]:
    return {chip["label"]: chip for chip in result["notes"]}


def test_the_chips_are_the_materials_and_notes_the_composer_designs_for(index) -> None:
    result = understood_notes(formula_name="Baie Rose Homme", message=BAIE_ROSE, must_avoid=["lavender"], index=index)
    chips = _chips(result)

    assert chips["Pink Pepper EO"]["kind"] == "material"
    assert chips["Pink Pepper EO"]["layer"] == "top"
    assert chips["fougere coumarin"]["kind"] == "note"
    assert chips["fougere coumarin"]["words"] == ["fougere"]
    # "pepper" brought the spice in, and the brief names Pink Pepper EO: avoiding
    # "pepper" would contradict the brief, so the spice can't be removed on its own.
    assert (chips["spice"]["remove_word"], chips["spice"]["tied_to"]) == (None, "Pink Pepper EO")
    assert "aromatic lavender" not in chips
    assert result["avoided"] == ["lavender"]
    assert result["structure"]["family"]
    assert result["structure"]["roles"]
    assert (result["needs_confirmation"], result["problems"], result["star_marker"]) == (False, [], False)


def test_each_remove_word_takes_its_note_out_without_contradicting_the_brief(index) -> None:
    for name, brief in (("Baie Rose Homme", BAIE_ROSE), ("Rose Framboise", RASPBERRY)):
        before = understood_notes(formula_name=name, message=brief, index=index)
        removable = [chip for chip in before["notes"] if chip["remove_word"]]
        assert removable, name
        for chip in removable:
            after = understood_notes(formula_name=name, message=brief, must_avoid=[chip["remove_word"]], index=index)
            assert after["needs_confirmation"] is False, (name, chip["label"])
            assert chip["id"] not in {item["id"] for item in after["notes"]}, (name, chip["label"])
            assert chip["remove_word"] in after["avoided"]


def test_each_star_phrase_makes_its_chip_the_star(index) -> None:
    for name, brief in (("Baie Rose Homme", BAIE_ROSE), ("Rose Framboise", RASPBERRY)):
        before = understood_notes(formula_name=name, message=brief, index=index)
        assert not any(chip["star"] for chip in before["notes"])
        for chip in before["notes"]:
            if not chip["star_phrase"]:
                continue
            after = understood_notes(formula_name=name, message=f"{brief}. The star is {chip['star_phrase']}.", index=index)
            assert after["star_marker"] is True
            assert _chips(after)[chip["label"]]["star"] is True, (name, chip["label"])


def test_each_named_fruit_is_its_own_chip(index) -> None:
    chips = _chips(understood_notes(formula_name="Rose Framboise", message=RASPBERRY, index=index))

    assert {label for label, chip in chips.items() if chip["id"].startswith("facet_fruit")} == {"raspberry", "lychee"}
    assert chips["raspberry"]["remove_word"] == "raspberry"
    assert chips["oud agarwood"]["layer"] == "base"


def test_an_avoid_that_contradicts_the_brief_is_said_in_plain_words(index) -> None:
    result = understood_notes(formula_name="", message=BAIE_ROSE, must_avoid=["pepper"], index=index)

    assert result["needs_confirmation"] is True
    assert result["problems"] == ["The brief names a material that Must avoid also lists. Take it out of one of them."]


def test_a_refinement_reads_the_earlier_turns_as_the_composer_does(index) -> None:
    result = understood_notes(formula_name="", message="Make it drier", conversation_context=[RASPBERRY], index=index)

    assert {"rose", "raspberry"} <= set(_chips(result))


def test_a_row_carries_the_names_note_by_its_stock_name_or_shows_its_own_profile(index) -> None:
    rows = [
        {"material": "Pink Pepper EO", "stock_id": None},
        {"material": "Hedione", "stock_id": None},
        {"material": "Not A Stock Anyone Owns", "stock_id": None},
    ]

    result = row_notes(formula_name="Baie Rose Homme", rows=rows, index=index)
    pepper, hedione, unknown = result["rows"]

    # "Baie Rose" is read as pink pepper, so the name asks for the spice.
    assert [chip["label"] for chip in result["notes"]] == ["spice"]
    assert [(item["label"], item["by"]) for item in pepper["carries"]] == [("spice", "name")]
    assert pepper["stock_id"]
    assert hedione["carries"] == []
    assert len(hedione["profile"]) == 3
    assert (unknown["found"], unknown["carries"], unknown["profile"]) == (False, [], [])


def test_a_row_is_found_by_its_stock_id_first(index) -> None:
    hedione = next(capability for capability in index.exact_matches("Hedione") if capability.identity_name == "Hedione")

    result = row_notes(formula_name="Jasmine Tea", rows=[{"material": "typed name", "stock_id": hedione.stock_id}], index=index)

    assert result["rows"][0]["stock_id"] == hedione.stock_id
    assert result["rows"][0]["found"] is True
