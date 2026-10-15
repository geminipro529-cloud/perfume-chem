"""Search (lab-search.js) and downloads (lab-export.js): page wiring and the pure rules, run in Node."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.lab_page_scripts import get_lab_script

STATIC = Path(__file__).resolve().parents[2] / "app" / "static"
SEARCH_JS = STATIC / "lab-search.js"
EXPORT_JS = STATIC / "lab-export.js"


@pytest.mark.asyncio
async def test_the_page_loads_search_and_downloads_after_the_editor_rules_and_before_the_lab_scripts(client):
    page = (await client.get("/app")).text
    javascript = (await get_lab_script(client)).text
    for path in ("/static/lab-search.js", "/static/lab-export.js", "/static/lab-search.css"):
        assert (await client.get(path)).status_code == 200, path

    assert page.index('src="/static/formula-editor.js"') < page.index('src="/static/lab-export.js"')
    assert page.index('src="/static/lab-export.js"') < page.index('src="/static/lab-search.js"') < page.index('src="/static/lab/core.js"')
    assert page.index('href="/static/lab-search.css"') < page.index("</head>")
    # The Search button heads the views; the box is one empty dialog the script fills.
    rail = page[page.index('<nav class="rail"'):page.index("</nav>")]
    assert rail.index('id="lab-search-open"') < rail.index('class="nav-item')
    assert '<dialog id="lab-search" class="lab-search"></dialog>' in page
    assert 'id="inventory-download"' in page and 'id="editor-download"' in page
    assert "attachLabSearch({" in javascript
    for path in (SEARCH_JS, EXPORT_JS, STATIC / "lab" / "search.js"):
        assert ".innerHTML" not in path.read_text(encoding="utf-8"), path


def _node(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the search and download logic test needs it")
    program = (
        f"const s = require({json.dumps(str(SEARCH_JS))});\n"
        f"const x = require({json.dumps(str(EXPORT_JS))});\n{script}"
    )
    completed = subprocess.run(
        [node, "-e", program], capture_output=True, text=True, encoding="utf-8", timeout=60, check=True
    )
    return json.loads(completed.stdout)


def test_search_folds_accents_and_case_keeps_thai_and_ranks_names_that_start_with_the_query_first():
    result = _node("""
      const items = [
        { kind: "card", id: "a", title: "studio › Iris Cathedral", extra: [] },
        { kind: "card", id: "b", title: "Orris and Iris", extra: [] },
        { kind: "card", id: "c", title: "Crème de Cassis", extra: [] },
        { kind: "stock", id: "d", title: "Ambroxan", extra: ["amber crystals"] },
        { kind: "stock", id: "e", title: "กุหลาบ มอญ", extra: [] },
        { kind: "bottle", id: "f", title: "Iris trial", extra: [] },
      ];
      const names = (query) => s.labSearchGroups(items, query).map((g) => [g.kind, g.total, g.shown.map((i) => i.id)]);
      console.log(JSON.stringify({
        iris: names("iris"),
        creme: names("CREME cass"),
        amber: names("amber"),
        thai: names("กุหลาบ"),
        none: names("zzz"),
        empty: names("  "),
        fold: s.labSearchFold("  Rose-de-Mai (10%) "),
        scores: [s.labSearchScore(items[0], "iris"), s.labSearchScore(items[1], "iris"), s.labSearchScore(items[3], "amber")],
      }));
    """)
    # A card's name counts from after its folder, so "studio › Iris Cathedral" starts with "iris".
    assert result["iris"] == [["card", 2, ["a", "b"]], ["bottle", 1, ["f"]]]
    assert result["creme"] == [["card", 1, ["c"]]]
    assert result["amber"] == [["stock", 1, ["d"]]]
    assert result["thai"] == [["stock", 1, ["e"]]]
    assert result["none"] == [] and result["empty"] == []
    assert result["fold"] == "rose de mai 10"
    assert result["scores"] == [0, 1, 3]


def test_search_lists_what_the_page_holds_cuts_each_group_and_says_how_many_matched():
    result = _node("""
      const items = s.labSearchItems({
        cards: Array.from({ length: 11 }, (_, n) => ({ source_path: `Rose_${n}.md`, display_name: `Rose ${n}` })),
        saved: [{ formula_id: "f1", name: "Rose D2.2", versions: [{ version: 1 }, { version: 4 }] }, { name: "no id" }],
        stocks: [{ stock_id: "s1", identity_name: "Rose Oxide", stock_label: "Rose Oxide 10%" }],
        bottles: [{ id: "b1", label: "", status: "active" }],
      }, (stock) => `${stock.stock_label} strength`);
      const groups = s.labSearchGroups(items, "rose");
      console.log(JSON.stringify({
        saved: items.find((i) => i.kind === "saved"),
        stock: items.find((i) => i.kind === "stock").detail,
        bottle: items.find((i) => i.kind === "bottle").title,
        groups: groups.map((g) => [g.label, g.total, g.shown.length]),
        summary: s.labSearchSummary(groups, "rose"),
        one: s.labSearchSummary(s.labSearchGroups(items, "oxide"), "oxide"),
      }));
    """)
    assert result["saved"]["latest"] == 4 and result["saved"]["detail"] == "Saved here, version 4"
    assert result["stock"] == "Rose Oxide 10% strength"
    assert result["bottle"] == "b1"
    assert result["groups"] == [["Cards", 11, 8], ["Saved formulas", 1, 1], ["Stock", 1, 1]]
    assert result["summary"] == "11 cards, 1 saved formula and 1 stock match."
    assert result["one"] == "1 stock matches."


def test_csv_cells_are_quoted_and_text_a_spreadsheet_would_run_stays_text():
    result = _node("""
      console.log(JSON.stringify({
        csv: x.exportCsv([["a,b", 'say "hi"', "line\\nbreak", "-12", "1.5", "=SUM(A1)", "+1 cell", "@x", "-x", "กุหลาบ", null]]),
      }));
    """)
    assert result["csv"] == "\"a,b\",\"say \"\"hi\"\"\",\"line\nbreak\",-12,1.5,'=SUM(A1),'+1 cell,'@x,'-x,กุหลาบ,\r\n"


def test_file_names_keep_thai_and_drop_what_a_file_system_refuses():
    result = _node("""
      console.log(JSON.stringify([
        x.exportFileName("studio › Rose Framboise R3", "Card"),
        x.exportFileName('a/b\\\\c:d*e?"f<g>h|', "Card"),
        x.exportFileName("  ...  ", "Card", "2026-10-15"),
        x.exportFileName("น้ำหอม กุหลาบ", "Card"),
        x.exportFileName("Stock list", "Stock list", x.exportToday(new Date(2026, 0, 5))),
        x.exportFileName("x".repeat(200), "Card").length,
      ]));
    """)
    assert result[:5] == [
        "studio - Rose Framboise R3.csv",
        "a-b-c-d-e-f-g-h.csv",
        "Card 2026-10-15.csv",
        "น้ำหอม กุหลาบ.csv",
        "Stock list 2026-01-05.csv",
    ]
    assert result[5] == 84


def test_a_card_sheet_keeps_each_amount_as_written_and_shares_only_the_liquid():
    result = _node("""
      const row = (material, amount, unit, fraction, basis, role) => ({ material, amount_decimal: amount, amount_unit: unit,
        concentration_fraction_decimal: fraction, concentration_basis: basis, role });
      console.log(JSON.stringify(x.exportSourceSheet([
        row("Hedione", "1.5", "mL", "1", "NEAT", "heart"),
        row("Damascone", "100", "uL", "0.1", "W_W", "top note"),
        row("Ambrox", "40", "mg", "1", "NEAT", "base"),
        row("Benzoin", "2", "g", "0.4", "W_W", null),
        row("", "5", "uL", null, null, null),
        row("No amount", "", "uL", null, null, null),
      ])));
    """)
    assert result == [
        ["Material", "Strength", "Amount", "Unit", "% of the liquid", "Note"],
        ["Hedione", "neat", "1.5", "mL", "93.75", "heart"],
        ["Damascone", "10% w/w", "100", "µL", "6.25", "top"],
        ["Ambrox", "neat", "40", "mg", "", "base"],
        ["Benzoin", "40% w/w", "2", "g", "", ""],
        ["No amount", "", "", "µL", "", ""],
    ]


def test_an_editor_or_saved_sheet_keeps_ul_and_mg_and_a_row_waiting_for_its_density_keeps_its_grams():
    result = _node("""
      const e = require(%s);
      const rows = [
        e.editorRow({ material: "Hedione", fraction: "1", basis: "neat", amount: e.editorNumber("750"), note: "heart" }),
        e.editorRow({ material: "Rose Oxide", fraction: "0.1", basis: "mass_fraction", carrier: "dpg", amount: e.editorNumber("250") }),
        e.editorRow({ material: "Ambrox", fraction: "1", basis: "neat", solid: true, amount: e.editorNumber("12.5") }),
        e.editorRow({ material: "Benzoin", grams: e.editorNumber("0.25") }),
        e.editorRow({ material: "" }),
      ];
      console.log(JSON.stringify({
        editor: x.exportEditorSheet(rows),
        saved: x.exportSavedSheet([{ material: "Iso E Super", fraction: "1", basis: "neat", solid: false, amount: "300", note: "base" }]),
      }));
    """ % json.dumps(str(STATIC / "formula-editor.js")))
    assert result["editor"] == [
        ["Material", "Strength", "Amount", "Unit", "% of the liquid", "Note"],
        ["Hedione", "neat", "750", "µL", "75", "heart"],
        ["Rose Oxide", "10% w/w in DPG", "250", "µL", "25", ""],
        ["Ambrox", "neat", "12.5", "mg", "", ""],
        ["Benzoin", "", "0.25", "g", "", ""],
    ]
    assert result["saved"] == [
        ["Material", "Strength", "Amount", "Unit", "% of the liquid", "Note"],
        ["Iso E Super", "neat", "300", "µL", "100", "base"],
    ]
