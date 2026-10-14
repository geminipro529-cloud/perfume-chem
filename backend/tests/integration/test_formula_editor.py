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


def test_the_check_and_chart_rows_carry_each_stock_and_leave_out_what_does_not_belong():
    result = _editor("""() => {
        const rows = [
            row("Hedione", "600", { fraction: "1", basis: "neat" }),
            row("Rose Oxide", "1000/3", { fraction: "0.1", basis: "W_W", carrier: "dpg" }),
            row("Ambrox", "120", { fraction: "1", solid: true }),
            row("Velvet Musk", "60", { fraction: "", basis: "unspecified" }),
            row("Ethanol", "24000"),
            row("", "5"), row("Linalool", null),
        ];
        rows[1] = { ...rows[1], amount: { n: 1000n, d: 3n } };
        return { checks: editor.editorCheckRows(rows), chart: editor.editorChartRows(rows) };
    }""")
    assert result["checks"] == [
        {"material": "Hedione", "amount_ul": "600", "stock_fraction": "1", "fraction_basis": "neat", "carrier": None},
        # A third of a µL is sent to six places; the check is a screen.
        {"material": "Rose Oxide", "amount_ul": "333.333333", "stock_fraction": "0.1", "fraction_basis": "w/w", "carrier": "dpg"},
        {"material": "Ambrox", "amount_mg": "120", "stock_fraction": "1", "fraction_basis": None, "carrier": None},
        {"material": "Velvet Musk", "amount_ul": "60", "stock_fraction": "1", "fraction_basis": None, "carrier": None},
        # The server reads ethanol rows as the bottle's own ethanol.
        {"material": "Ethanol", "amount_ul": "24000", "stock_fraction": "1", "fraction_basis": None, "carrier": None},
    ]
    assert [r["identity_name"] for r in result["chart"]] == ["Hedione", "Rose Oxide", "Velvet Musk"]
    assert result["chart"][1] == {"identity_name": "Rose Oxide", "amount_decimal": "333.333333", "amount_unit": "uL", "stock_fraction_decimal": "0.1"}


def test_cost_rows_weigh_a_liquid_priced_per_gram_when_its_density_is_known():
    prices = {"s-hed": {"per_unit": "mL"}, "s-iso": {"per_unit": "g"}, "s-musk": {"per_unit": "g"}}
    result = _editor("""() => editor.editorCostRows([
        row("Hedione", "600", { fraction: "1", stockId: "s-hed" }),
        row("Iso E Super", "370", { fraction: "1", stockId: "s-iso" }),
        row("Velvet Musk", "60", { fraction: "0.1", basis: "W_W", stockId: "s-musk" }),
        row("Ambrox", "120", { fraction: "1", solid: true, stockId: "s-amb" }),
    ], DENSITIES, PRICES)""", DENSITIES=DENSITIES, PRICES=prices)
    assert [(r["material"], r["stock_id"], r["amount_decimal"], r["amount_unit"]) for r in result] == [
        ("Hedione", "s-hed", "600", "µL"),
        ("Iso E Super", "s-iso", "0.355644", "g"),  # 370 µL x 0.9612 g/mL
        ("Velvet Musk", "s-musk", "60", "µL"),  # no density: left in µL, so the cost says why
        ("Ambrox", "s-amb", "120", "mg"),
    ]


def test_stock_left_counts_down_the_weighed_lab_bottles_of_each_row():
    stocks = [
        {"id": "lab-hed-1", "material_id": "m-hed", "active_fraction": 1, "density_g_ml": 0.999},
        {"id": "lab-hed-2", "material_id": "m-hed", "active_fraction": 1, "density_g_ml": None},
        {"id": "lab-ro", "material_id": "m-ro", "active_fraction": 0.01},
        {"id": "lab-amb", "material_id": "m-amb", "active_fraction": 1},
    ]
    materials = [{"id": "m-hed", "canonical_name": "Hedione"}, {"id": "m-ro", "canonical_name": "Rose Oxide"},
                 {"id": "m-amb", "canonical_name": "Ambrox"}]
    result = _editor("""() => editor.editorStockLeft([
        row("hedione", "600", { fraction: "1" }),
        row("Rose Oxide", "30", { fraction: "0.1" }),
        row("Ambrox", "120", { fraction: "1", solid: true }),
        row("Iso E Super", "370", { fraction: "1" }),
        row("Mystery", "10", { fraction: "1" }),
        row("Ethanol", "24000"),
    ], STOCKS, MATERIALS, { "lab-hed-1": 6, "lab-hed-2": 4.5, "lab-amb": null }, DENSITIES, "10")""",
        STOCKS=stocks, MATERIALS=materials, DENSITIES=DENSITIES)
    hedione, ambrox = result["lines"]
    # Two Hedione bottles add up; ten bottles of 600 µL at 0.999 g/mL use 5.994 g.
    assert hedione == {"material": "hedione", "stockIds": ["lab-hed-1", "lab-hed-2"], "nowG": 10.5, "useG": 5.994,
                       "afterG": pytest.approx(4.506), "short": False}
    # A bottle still being asked about has no level yet.
    assert ambrox == {"material": "Ambrox", "stockIds": ["lab-amb"], "nowG": None, "useG": 1.2, "afterG": None, "short": False}
    # Rose Oxide is weighed in only at 1%, not the 10% the row pours.
    assert result["unweighed"] == ["Rose Oxide", "Iso E Super", "Mystery"]
    assert result["noDensity"] == []


def test_a_version_keeps_every_amount_exactly_and_reads_back_the_same_rows():
    result = _editor("""() => {
        const rows = [
            row("Hedione", "600", { fraction: "1", basis: "neat", note: "heart", stockId: "s-hed" }),
            { ...row("Rose Oxide", "1", { fraction: "0.01", basis: "W_W", carrier: "dpg" }), amount: { n: 2000n, d: 6n } },
            row("Ambrox", "120", { fraction: "1", solid: true }),
            row("Velvet Musk", null), row("", "5"),
        ];
        const saved = editor.editorSavedRows(rows);
        const back = editor.editorRowsFromSaved(saved.rows);
        return { saved, back: R(back), sameKey: editor.editorContentKey("Rose", rows, "30") === editor.editorContentKey("Rose", back, "30"),
            renamed: editor.editorContentKey("Rose", rows, "30") === editor.editorContentKey("Rose 2", rows, "30"),
            rebottled: editor.editorContentKey("Rose", rows, "30") === editor.editorContentKey("Rose", rows, "50"),
            bad: ["0", "1.5", "-1", "1/0", "01", ""].map((text) => editor.editorAmountOf(text)) };
    }""")
    assert result["saved"]["rows"] == [
        {"material": "Hedione", "stock_id": "s-hed", "fraction": "1", "basis": "neat", "carrier": None, "solid": False, "amount": "600", "note": "heart"},
        {"material": "Rose Oxide", "stock_id": None, "fraction": "0.01", "basis": "W_W", "carrier": "dpg", "solid": False, "amount": "1000/3", "note": ""},
        {"material": "Ambrox", "stock_id": None, "fraction": "1", "basis": "", "carrier": None, "solid": True, "amount": "120", "note": ""},
    ]
    assert result["saved"]["leftOut"] == ["Velvet Musk"]
    assert [r["amount"] for r in result["back"]] == ["600/1", "1000/3", "120/1"]
    assert result["sameKey"] is True
    assert (result["renamed"], result["rebottled"]) == (False, False)
    assert result["bad"] == [None] * 6


def test_comparing_versions_lists_changed_added_and_removed_rows_by_material_and_strength():
    result = _editor("""() => editor.editorCompare([
        row("Hedione", "600", { fraction: "1" }),
        row("Iso E Super", "300", { fraction: "1" }),
        row("Rose Oxide", "30", { fraction: "0.1" }),
        row("Ambrox", "100", { fraction: "1", solid: true }),
        row("Ethanol", "100"),
    ], [
        row("Hedione", "650", { fraction: "1" }),
        row("Iso E Super", "300", { fraction: "1" }),
        row("Rose Oxide", "3", { fraction: "0.01" }),
        row("Ambrox", "80", { fraction: "1", solid: true }),
        row("Ethanol", "40"), row("Ethanol", "60"),
        row("Cashmeran", "50", { fraction: "1" }),
    ])""")
    lines = {(line["material"], line["strength"]): line for line in result["lines"]}
    assert result["same"] == 2  # Iso E Super, and Ethanol listed twice summing to the same 100 µL
    # 600 of 1030 µL of liquid, then 650 of 1103 (the Ambrox crystals are not liquid).
    assert lines[("Hedione", "neat")] == {"material": "Hedione", "strength": "neat", "unit": "µL", "kind": "changed",
                                          "a": "600", "b": "650", "change": "+50", "aPct": "58.25%", "bPct": "58.93%"}
    # One material at two strengths is two different rows.
    assert lines[("Rose Oxide", "10%")]["kind"] == "removed" and lines[("Rose Oxide", "10%")]["b"] == ""
    assert lines[("Rose Oxide", "1%")]["kind"] == "added" and lines[("Rose Oxide", "1%")]["a"] == ""
    assert lines[("Ambrox", "neat")]["change"] == "−20" and lines[("Ambrox", "neat")]["unit"] == "mg"
    assert lines[("Ambrox", "neat")]["aPct"] == ""
    assert [line["material"] for line in result["lines"]][-1] == "Cashmeran"
    assert result["liquid"] == ["1030", "1103"]


def test_check_changes_name_the_verdict_the_rows_the_allergens_and_the_oil_that_changed():
    def answer(verdict, rows, declare, oil):
        return {"ifra": {"verdict": verdict, "rows": rows}, "allergens": {"declare": [{"allergen": name} for name in declare]}, "oil_pct": oil}

    cinnamic_ok = {"material": "Cinnamic Aldehyde", "verdict": "pass", "ifra_status": "restricted", "actual_pct": 0.1, "limit_pct": 0.25, "usage_pct": 40.0}
    cinnamic_over = dict(cinnamic_ok, verdict="fail", actual_pct=0.31, usage_pct=124.0)
    iso = {"material": "Iso E Super", "verdict": "pass", "ifra_status": "restricted", "actual_pct": 2, "limit_pct": 20, "usage_pct": 10.0}
    new_pass = {"material": "Hedione", "verdict": "pass", "ifra_status": "not_restricted", "actual_pct": 1, "limit_pct": None, "usage_pct": None}
    before = answer("PASS", [cinnamic_ok, iso], ["Linalool", "Limonene"], 20.04)
    after = answer("FAIL", [cinnamic_over, dict(iso, usage_pct=12.0), new_pass], ["Linalool", "Citral"], 21.5)
    result = _editor("() => ({ changed: editor.editorCheckChanges(BEFORE, AFTER), none: editor.editorCheckChanges(BEFORE, BEFORE) })",
                     BEFORE=before, AFTER=after)
    assert result["changed"] == [
        {"text": "IFRA: within the limits → over an IFRA limit", "problem": True},
        {"text": "Cinnamic Aldehyde: 40% of its limit → 0.31% of the bottle, over its 0.25% limit", "problem": True},
        {"text": "Now declared on the label: Citral"},
        {"text": "No longer declared: Limonene"},
        {"text": "Oil: 20.0% → 21.5%"},
    ]
    assert result["none"] == []


def test_a_card_makes_its_rows_when_they_list_ethanol_and_one_bottle_otherwise():
    result = _editor("""() => ({
        concentrate: editor.editorCardMakesMl([row("Hedione", "600"), row("Ambrox", "120", { solid: true })], "30"),
        withEthanol: editor.editorCardMakesMl([row("Hedione", "6000"), row("Ethanol", "23500"), row("Ambrox", "120", { solid: true })], "50"),
        noBottle: editor.editorCardMakesMl([row("Hedione", "600")], ""),
    })""")
    # Solids are weighed into the bottle and take no volume on the card.
    assert result == {"concentrate": "30", "withEthanol": "29.5", "noBottle": ""}
