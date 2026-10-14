"""Brief chips on Create a formula: the words they write into the brief, and how they load (node)."""

from pathlib import Path

import pytest

from tests.integration.test_lab_ui import _node_json

STATIC = Path(__file__).resolve().parents[2] / "app" / "static"
BRIEF_NOTES_JS = STATIC / "brief-notes.js"


def test_a_star_or_a_note_is_one_sentence_after_the_brief():
    result = _node_json(BRIEF_NOTES_JS, """(m) => [
        m.briefStarText("A pink pepper fougere", "pink pepper"),
        m.briefStarText("A pink pepper fougere.  ", "pink pepper"),
        m.briefStarText("", "rose"),
        m.briefWithText("A rose!", " iris "),
        m.briefAvoidText("vanilla, laundry musk", "fougere"),
        m.briefAvoidText("vanilla, Fougere", "fougere"),
        m.briefAvoidText("", "lavender"),
    ]""")

    assert result == [
        "A pink pepper fougere. The star is pink pepper.",
        "A pink pepper fougere. The star is pink pepper.",
        "The star is rose.",
        "A rose! With iris.",
        "vanilla, laundry musk, fougere",
        "vanilla, Fougere",
        "lavender",
    ]


def test_each_chip_says_its_layer_and_where_it_came_from():
    result = _node_json(BRIEF_NOTES_JS, """(m) => [
        m.briefChipMeta({ kind: "material", label: "Pink Pepper EO", layer: "top", words: [], from_name: false, tied_to: null }),
        m.briefChipMeta({ kind: "note", label: "spice", layer: "heart", words: ["pepper"], from_name: false, tied_to: "Pink Pepper EO" }),
        m.briefChipMeta({ kind: "note", label: "raspberry", layer: "top", words: ["raspberry"], from_name: true, tied_to: null }),
        m.briefChipMeta({ kind: "note", label: "dry wood", layer: "base", words: ["cedar", "vetiver"], from_name: false, tied_to: null }),
    ]""")

    assert result == [
        "material you named, top note",
        "heart note · from “pepper” · comes with Pink Pepper EO",
        "top note · from the name",
        "base note · from “cedar”, “vetiver”",
    ]


def test_the_lines_around_the_chips_name_the_star_problems_and_structure():
    result = _node_json(BRIEF_NOTES_JS, """(m) => {
        const base = { notes: [{ label: "spice", star: false }], needs_confirmation: false, problems: [], unmapped: [], avoided: [],
                       structure: { family: null, roles: [], supporting_materials: 0 } };
        return [
            m.briefStatusLine(base),
            m.briefStatusLine({ ...base, notes: [{ label: "spice", star: true }] }),
            m.briefStatusLine({ ...base, notes: [] }),
            m.briefStatusLine({ ...base, needs_confirmation: true, problems: ["One.", "Two."] }),
            m.briefExtraLines(base),
            m.briefExtraLines({ ...base, unmapped: ["yuzu"], avoided: ["lavender"],
                structure: { family: "FOUGÈRE (AROMATIC FOUGÈRE)", roles: [{ label: "Opening articulation" }, { label: "Top: lemon" }], supporting_materials: 1 } }),
        ];
    }""")

    assert result == [
        "No star yet: make one the star if it must lead. Leave out a note to put its word in Must avoid.",
        "spice is the star. Leave out a note to put its word in Must avoid.",
        "No note or material it knows is in this brief yet. Add one below.",
        "One. Two.",
        [],
        [
            "Read as notes, but no stock note for them yet: yuzu.",
            "Avoiding: lavender.",
            "Family: Fougère (aromatic fougère).",
            "For the structure it also adds: opening articulation, top: lemon, and 1 supporting material for the notes.",
        ],
    ]


@pytest.mark.asyncio
async def test_the_chips_load_before_the_lab_page_and_write_no_html(client):
    page = (await client.get("/app")).text
    source = BRIEF_NOTES_JS.read_text(encoding="utf-8")

    assert page.index('src="/static/brief-notes.js"') < page.index('src="/static/lab/core.js"')
    assert 'id="brief-notes-toggle"' in page and 'aria-controls="brief-notes"' in page
    assert "innerHTML" not in source and "insertAdjacentHTML" not in source
    assert (await client.get("/static/brief-notes.js")).status_code == 200
