"""Formula editor maths: units are views of exact amounts, pasting, binding stocks, undo (node)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

FORMULA_EDITOR_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "formula-editor.js"

# Exact fractions come back as "n/d" text (reduced), so a test can't pass on a rounded value.
_PRELUDE = """
const F = (value) => (value ? `${value.n}/${value.d}` : null);
const R = (rows) => rows.map((row) => ({ material: row.material, amount: F(row.amount), solid: row.solid,
  grams: F(row.grams), fraction: row.fraction, stockId: row.stockId, note: row.note }));
const row = (material, amount, extra = {}) => editor.editorRow({ material, amount: amount === null ? null : editor.editorNumber(amount), ...extra });
const error = (call) => { try { call(); return null; } catch (failure) { return failure.message; } };
"""

DENSITIES = {"Hedione": "0.999", "Iso E Super": "0.9612"}


def _editor(script, **values):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the formula editor logic test needs it")
    constants = "".join(f"const {name} = {json.dumps(value)};\n" for name, value in values.items())
    program = (
        f"const editor = require({json.dumps(str(FORMULA_EDITOR_JS))});\n{_PRELUDE}{constants}"
        f"process.stdout.write(JSON.stringify(({script})()));"
    )
    completed = subprocess.run([node, "-e", program], capture_output=True, text=True, encoding="utf-8", timeout=60, check=True)
    return json.loads(completed.stdout)


def _stock(stock_id, material, fraction, basis="neat", carrier=None, status="owned", **extra):
    return {"stock_id": stock_id, "material": material, "identity_name": material, "fraction_decimal": fraction,
            "fraction_basis": basis, "carrier": carrier, "status": status, **extra}


def test_numbers_are_read_exactly_and_anything_else_is_not_a_number():
    result = _editor("""() => ["1200", "1,200", "1 200", "1,200.5", ".5", "0.125", "abc", "1,2", "", "-3"]
        .map((text) => F(editor.editorNumber(text)))""")
    assert result == ["1200/1", "1200/1", "1200/1", "2401/2", "1/2", "1/8", None, None, None, None]


def test_a_share_typed_in_percent_sets_that_row_and_the_others_keep_their_microlitres():
    result = _editor("""() => {
        const rows = [row("Hedione", "600"), row("Iso E Super", "400")];
        const pct = editor.editorSetAmount(rows, 0, "75", "pct", {});
        const parts = editor.editorSetAmount(rows, 1, "200", "parts", {});
        return { pct: R(pct).map((r) => r.amount), parts: R(parts).map((r) => r.amount),
                 shown: pct.map((r) => editor.editorShown(r, editor.editorTotals(pct), "pct", {}).text) };
    }""")
    # 75% of the liquid with 400 µL left in the others: x / (x + 400) = 0.75, so x = 1200.
    assert result["pct"] == ["1200/1", "400/1"]
    # 200 parts per 1000 with 600 µL in the others: x = 200 x 600 / 800 = 150.
    assert result["parts"] == ["600/1", "150/1"]
    assert result["shown"] == ["75", "25"]


def test_thirds_stay_exact_however_often_the_view_changes():
    result = _editor("""() => {
        let rows = [row("A", "100"), row("B", "100"), row("C", "100")];
        rows = editor.editorSetAmount(rows, 0, "50", "pct", {});
        const totals = editor.editorTotals(rows);
        return { amounts: R(rows).map((r) => r.amount), total: F(totals.liquidUl),
                 pct: rows.map((r) => editor.editorShown(r, totals, "pct", {}).text),
                 parts: rows.map((r) => editor.editorShown(r, totals, "parts", {}).text),
                 ul: rows.map((r) => editor.editorShown(r, totals, "uL", {}).text) };
    }""")
    assert result["amounts"] == ["200/1", "100/1", "100/1"]
    assert result["total"] == "400/1"
    assert result["pct"] == ["50", "25", "25"]
    assert result["parts"] == ["500", "250", "250"]
    assert result["ul"] == ["200", "100", "100"]


def test_shares_that_cannot_be_typed_say_what_to_type_instead():
    result = _editor("""() => {
        const rows = [row("Hedione", "600"), row("Iso E Super", "400"), row("Ambrox", "120", { solid: true })];
        const only = [row("Hedione", "600")];
        return [
            error(() => editor.editorSetAmount(rows, 0, "100", "pct", {})),
            error(() => editor.editorSetAmount(rows, 0, "1000", "parts", {})),
            error(() => editor.editorSetAmount(only, 0, "50", "pct", {})),
            error(() => editor.editorSetAmount(rows, 0, "abc", "uL", {})),
            error(() => editor.editorSetAmount(rows, 0, "0", "uL", {})),
            R(editor.editorSetAmount(rows, 2, "250", "pct", {}))[2].amount,
        ];
    }""")
    assert result == [
        "A row's share must be under 100%.",
        "A row's share must be under 1000 parts.",
        "This is the only liquid, so it is all of it. Type its amount in µL or g instead.",
        '"abc" is not an amount. Type a number such as 120 or 0.5.',
        "Type an amount above 0, or remove the row.",
        # A solid has no share of the liquid: what is typed is its mg.
        "250/1",
    ]


def test_grams_go_through_the_stock_density_and_an_unknown_density_is_named():
    result = _editor("""() => {
        const rows = [row("Hedione", "600", { fraction: "1" }), row("Velvet Musk", "60", { fraction: "0.1", basis: "W_W" }),
                      row("Ambrox", "120", { solid: true })];
        const typed = editor.editorSetAmount(rows, 0, "0.999", "g", DENSITIES);
        const solid = editor.editorSetAmount(rows, 2, "0.25", "g", DENSITIES);
        const totals = editor.editorTotals(rows);
        return { typed: R(typed)[0].amount, solid: R(solid)[2].amount,
                 shown: rows.map((r) => editor.editorShown(r, totals, "g", DENSITIES)),
                 unknown: error(() => editor.editorSetAmount(rows, 1, "1", "g", DENSITIES)) };
    }""", DENSITIES=DENSITIES)
    assert result["typed"] == "1000/1"  # 0.999 g at 0.999 g/mL is 1000 µL
    assert result["solid"] == "250/1"  # 0.25 g of a solid is 250 mg
    assert result["shown"][0] == {"text": "0.599", "unit": "g"}
    assert result["shown"][2] == {"text": "0.12", "unit": "g"}
    # Velvet Musk 10% w/w with no carrier and no material density: nothing to weigh by.
    assert result["shown"][1] == {"text": "", "unit": "g", "why": "density not known"}
    assert result["unknown"] == "Velvet Musk has no known density, so it can't be typed in grams. Switch to µL for this row."


def test_rows_read_in_grams_wait_for_a_density_and_solids_become_milligrams():
    result = _editor("""() => {
        // Hedione is bound neat; Mystery has no stock, so no strength and no density.
        const rows = [editor.editorRow({ material: "Hedione", fraction: "1", grams: editor.editorNumber("1.998") }),
                      editor.editorRow({ material: "Mystery", grams: editor.editorNumber("1") }),
                      editor.editorRow({ material: "Ambrox", grams: editor.editorNumber("0.5"), stockId: "s-amb" })];
        const stocks = [{ stock_id: "s-amb", material: "Ambrox", status: "owned", physical_form: "crystals" }];
        const resolved = editor.editorResolveGrams(rows, DENSITIES, stocks);
        return { rows: R(resolved.rows), waiting: resolved.waiting };
    }""", DENSITIES=DENSITIES)
    assert [(r["amount"], r["grams"], r["solid"]) for r in result["rows"]] == [
        ("2000/1", None, False), (None, "1/1", False), ("500/1", None, True),
    ]
    assert result["waiting"] == ["Mystery"]


def test_spreadsheet_rows_and_plain_lines_are_read_and_a_markdown_table_is_left_to_the_server():
    result = _editor("""() => [
        editor.editorParsePlain("Material\\tStrength\\tAmount\\nRose Oxide\\t1%\\t15\\nCashmeran\\tneat\\t40 µL\\nAmbrox\\t120\\tmg\\nno number here\\n"),
        editor.editorParsePlain("Hedione 1,200 µL\\nIso E Super 0.4 g\\nEthyl Maltol 5 mg\\nLinalool 30"),
        editor.editorParsePlain("Hedione;600;uL"),
        editor.editorParsePlain("| Material | Amount |\\n|---|---|\\n| Hedione | 600 |"),
    ]""")
    tsv, plain, semicolon, markdown = result
    assert tsv["rows"] == [
        {"material": "Rose Oxide", "amountText": "15", "unit": None, "fraction": "0.01"},
        {"material": "Cashmeran", "amountText": "40", "unit": "uL", "fraction": "1"},
        {"material": "Ambrox", "amountText": "120", "unit": "mg", "fraction": ""},
    ]
    assert tsv["skipped"] == ["no number here"]
    assert [(r["material"], r["amountText"], r["unit"]) for r in plain["rows"]] == [
        ("Hedione", "1,200", "uL"), ("Iso E Super", "0.4", "g"), ("Ethyl Maltol", "5", "mg"), ("Linalool", "30", None),
    ]
    assert semicolon["rows"] == [{"material": "Hedione", "amountText": "600", "unit": "uL", "fraction": ""}]
    assert markdown is None


def test_bare_pasted_numbers_are_read_in_the_unit_on_screen():
    result = _editor("""() => {
        const parsed = editor.editorParsePlain("Hedione\\t60\\nIso E Super\\t40\\nAmbrox\\t2 mg");
        const asShares = editor.editorRowsFromPlain(parsed, "pct", []);
        const asGrams = editor.editorRowsFromPlain(parsed, "g", []);
        return { shares: R(asShares.rows), grams: R(asGrams.rows),
                 refused: error(() => editor.editorRowsFromPlain(parsed, "pct", [row("Linalool", "100")])) };
    }""")
    # In % a bare number is a share of a 1000 µL formula; a number with its unit keeps it.
    assert [(r["amount"], r["solid"]) for r in result["shares"]] == [("600/1", False), ("400/1", False), ("2/1", True)]
    assert [(r["grams"], r["amount"]) for r in result["grams"]][:2] == [("60/1", None), ("40/1", None)]
    assert result["refused"].startswith("Numbers without a unit are read in the unit on screen.")


def test_a_name_with_its_strength_binds_the_one_owned_stock_at_that_strength():
    stocks = [
        _stock("s-ro10", "Rose Oxide", "0.1", "mass_fraction", "dpg"),
        _stock("s-ro1", "Rose Oxide", "0.01", "mass_fraction", "dpg"),
        _stock("s-hed", "Hedione", "1"),
        _stock("s-old", "Iso E Super", "1", status="used_up"),
        _stock("s-amb", "Ambrox", "1", physical_form="crystals"),
    ]
    result = _editor("""() => {
        const names = ["Rose Oxide 1% DPG", "Rose Oxide (10% w/w in DPG)", "Iso E Super (neat)", "Vanillin 10% in DPG"]
            .map(editor.editorNameStrength);
        const bound = editor.editorBindRows([
            row("Rose Oxide 1% DPG", "15"), row("Rose Oxide", "30"), row("hedione", "600"),
            row("Iso E Super", "400"), row("Ambrox", null), row("", null),
        ], STOCKS);
        return { names, rows: R(bound.rows), unmatched: bound.unmatched, ambiguous: bound.ambiguous };
    }""", STOCKS=stocks)
    assert result["names"] == [
        {"name": "Rose Oxide", "fraction": "0.01"}, {"name": "Rose Oxide", "fraction": "0.1"},
        {"name": "Iso E Super", "fraction": "1"}, {"name": "Vanillin", "fraction": "0.1"},
    ]
    assert [(r["material"], r["stockId"], r["fraction"], r["solid"]) for r in result["rows"]] == [
        ("Rose Oxide", "s-ro1", "0.01", False),
        ("Rose Oxide", None, "", False),  # two strengths owned: Kenny picks one
        ("Hedione", "s-hed", "1", False),
        ("Iso E Super", None, "", False),  # used up is not owned
        ("Ambrox", "s-amb", "1", True),  # an empty row takes the stock's form
        ("", None, "", False),
    ]
    assert result["ambiguous"] == ["Rose Oxide"]
    assert result["unmatched"] == ["Iso E Super"]


def test_scaling_keeps_every_share_and_sorting_puts_liquids_then_solids_then_empty_rows():
    result = _editor("""() => {
        const rows = [row("A", "30", { note: "base" }), row("B", null), row("C", "600", { note: "top" }),
                      row("D", "120", { solid: true, note: "top" }), row("E", "370", { note: "heart" }), row("F", "60")];
        const scaled = editor.editorScaleTo(rows, "2120");
        return {
            scaled: R(scaled).map((r) => r.amount),
            byAmount: editor.editorSorted(rows, "amount").map((r) => r.material),
            byNote: editor.editorSorted(rows, "note").map((r) => r.material),
            errors: [error(() => editor.editorScaleTo(rows, "0")), error(() => editor.editorScaleTo([row("D", "5", { solid: true })], "100"))],
        };
    }""")
    # Liquid 1060 µL to 2120 µL doubles every row, the solid too.
    assert result["scaled"] == ["60/1", None, "1200/1", "240/1", "740/1", "120/1"]
    assert result["byAmount"] == ["C", "E", "F", "A", "D", "B"]
    assert result["byNote"] == ["C", "D", "E", "A", "F", "B"]
    assert result["errors"] == ["Type the liquid total in µL, such as 6000.", "There is no liquid to scale yet."]


def test_undo_and_redo_step_through_commits_and_a_new_edit_drops_the_redo():
    result = _editor("""() => {
        const a = [row("A", "1")], b = [row("B", "2")], c = [row("C", "3")], d = [row("D", "4")];
        let history = editor.editorHistory(a);
        history = editor.editorCommit(history, b);
        history = editor.editorCommit(history, b);  // the same rows again change nothing
        history = editor.editorCommit(history, c);
        const steps = [];
        history = editor.editorUndo(history); steps.push(history.present[0].material);
        history = editor.editorUndo(history); steps.push(history.present[0].material);
        history = editor.editorUndo(history); steps.push(history.present[0].material);
        history = editor.editorRedo(history); steps.push(history.present[0].material);
        history = editor.editorCommit(history, d);
        const redoAfterEdit = editor.editorRedo(history).present[0].material;
        let long = editor.editorHistory(a);
        for (let i = 0; i < 250; i += 1) long = editor.editorCommit(long, [row(String(i), "1")]);
        return { steps, redoAfterEdit, kept: long.past.length };
    }""")
    assert result["steps"] == ["B", "A", "A", "B"]
    assert result["redoAfterEdit"] == "D"
    assert result["kept"] == 200


def test_the_bench_table_keeps_each_strength_and_names_the_rows_left_out():
    result = _editor("""() => editor.editorBenchTable("", [
        row("Hedione", "600", { fraction: "1", basis: "neat" }),
        row("Rose Oxide", "30", { fraction: "0.1", basis: "mass_fraction", carrier: "dpg" }),
        row("Linalool | natural", "12.5", { fraction: "0.1", basis: "volume_fraction", carrier: "ethanol" }),
        row("Ambrox", "120", { fraction: "1", solid: true }),
        row("Velvet Musk", null, { fraction: "0.1", basis: "W_W" }),
        row("", "5"),
    ])""")
    assert result["text"] == (
        "# Edited formula\n\n| Material | Dilution | Amount (µL) |\n|---|---|---:|\n"
        "| Hedione | neat | 600 |\n| Rose Oxide | 10% w/w in DPG | 30 |\n"
        "| Linalool / natural | 10% v/v in ethanol | 12.5 |\n| Ambrox | neat | 120 mg |\n"
    )
    assert result["leftOut"] == ["Velvet Musk"]
