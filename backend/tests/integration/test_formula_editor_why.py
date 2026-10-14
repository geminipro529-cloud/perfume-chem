"""Why each row: the words under each editor row, and the smell leaders without one (node)."""

import json

from tests.integration.test_formula_editor import _editor
from tests.integration.test_lab_ui import SCENT_CHART_JS, _node_json


def _note(label, by="name", star=False, kind="note"):
    return {"id": label, "kind": kind, "label": label, "by": by, "star": star}


def test_a_row_says_which_of_the_names_notes_it_carries_and_how():
    rows = [
        {"found": True, "carries": [_note("spice", star=True)], "profile": ["spicy"]},
        {"found": True, "carries": [_note("dry wood", by="odor")], "profile": ["woody"]},
        {"found": True, "carries": [_note("spice"), _note("dry wood", by="odor")], "profile": []},
        {"found": True, "carries": [_note("Pink Pepper EO", kind="material"), _note("spice")], "profile": []},
        {"found": True, "carries": [], "profile": ["woody", "warmth", "transparency"]},
        {"found": True, "carries": [], "profile": []},
        {"found": False, "carries": [], "profile": []},
    ]

    result = _editor("() => rows.map((info) => editor.editorWhyText(info))", rows=rows)
    no_notes = _editor("() => [editor.editorWhyText(rows[4], false), editor.editorWhyText(rows[5], false)]", rows=rows)

    assert result == [
        "Carries the spice (the star).",
        "Carries the dry wood only by its odor words.",
        "Carries the spice; the dry wood only by its odor words.",
        "The name names it; carries the spice.",
        "None of the name's notes; its own profile: woody, warmth, transparency.",
        "None of the name's notes.",
        "Not in your stock list, so what it carries is not known.",
    ]
    assert no_notes == ["Its own profile: woody, warmth, transparency.", ""]


def test_the_line_above_the_rows_names_the_notes_or_says_there_are_none():
    result = _editor("""() => [
        editor.editorWhyNotesLine({ formula_name: "Baie Rose", notes: [{ label: "spice", star: true }, { label: "dry wood" }, { label: "rose" }] }),
        editor.editorWhyNotesLine({ formula_name: "CHIMIE Femme", notes: [] }),
        editor.editorWhyKey({ stockId: "s1", material: "Hedione" }),
        editor.editorWhyKey(editor.editorRow({ material: "Hedione" })),
    ]""")

    assert result == [
        "The name asks for spice (the star), dry wood and rose. Each row says which of these its stock carries: by its own name, or only by its odor words.",
        "The name “CHIMIE Femme” names no note the composer knows, so each row shows its own profile.",
        "s1|Hedione",
        "|Hedione",
    ]


def test_the_drop_preview_says_what_the_row_does_for_the_name():
    result = _editor("""() => [
        editor.editorWhyDropLine({ found: true, carries: [{ kind: "note", label: "spice" }, { kind: "note", label: "dry wood" }] }),
        editor.editorWhyDropLine({ found: true, carries: [{ kind: "material", label: "Pink Pepper EO" }] }),
        editor.editorWhyDropLine({ found: true, carries: [] }),
        editor.editorWhyDropLine({ found: false, carries: [] }),
        editor.editorWhyDropLine(null),
    ]""")

    assert result == [
        "It carries the spice and dry wood the name asks for.",
        "The name names this material.",
        "It carries none of the notes the name asks for.",
        "",
        "",
    ]


def test_the_smell_leaders_that_change_without_a_row_are_listed_by_stage():
    curve = {"windows": [
        {"label": "top", "top": ["Pink Pepper EO", "Hedione", "Ambrox"], "materials": [
            {"name": "Pink Pepper EO", "known": True, "share": 0.5}]},
        {"label": "heart", "top": ["Hedione", "Ambrox"], "materials": [{"name": "Pink Pepper EO", "known": True, "share": 0.004}]},
    ]}
    without = {"windows": [{"label": "top", "top": ["Hedione", "Ambrox", "Iso E Super"]}, {"label": "heart", "top": ["Hedione", "Ambrox"]}]}

    result = _node_json(SCENT_CHART_JS, "(m) => [m.scentLeaderChanges(%s, %s), m.scentLeaderChanges(%s, %s),"
                        " m.scentShareAt(%s, 'Pink Pepper EO', 'heart'), m.scentShareAt(%s, 'Hedione', 'heart')]"
                        % (_js(curve), _js(without), _js(without), _js(without), _js(curve), _js(curve)))

    assert result == [
        [{"stage": "5 minutes", "before": ["Pink Pepper EO", "Hedione", "Ambrox"], "after": ["Hedione", "Ambrox", "Iso E Super"]}],
        [],
        0.004,
        None,
    ]


def _js(value):
    return json.dumps(value)


def test_stages_whose_leaders_change_the_same_way_share_one_line():
    def curve(*tops):
        return {"windows": [{"label": label, "top": top} for label, top in zip(("opening", "top", "heart", "late_heart", "drydown"), tops)]}

    before = curve(["A", "B"], ["A", "B"], ["A", "B"], ["C"], ["A", "B"])
    after = curve(["B"], ["B"], ["B"], ["C"], ["B"])

    result = _node_json(SCENT_CHART_JS, "(m) => [m.scentLeaderLines(%s, %s), m.scentLeaderLines(%s, %s)]"
                        % (_js(before), _js(after), _js(after), _js(curve([], ["B"], ["B"], ["C"], ["B"]))))

    assert result == [
        ["Opening to 30 minutes: A, B → B", "4 hours: A, B → B"],
        ["Opening: B → nothing detectable"],
    ]
