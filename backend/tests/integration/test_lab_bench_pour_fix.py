"""Pour fix on the bench sheet: what still goes in after a row went in over or under (node)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

BENCH_SHEET_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "bench-sheet.js"

# Helpers the scripts below share: the first sheet, a fix on a sheet's printed
# rows (no basket data, so the order is the batch order), and a compact view.
PRELUDE = """
const first = (rows) => { const state = bench.benchPourStart(rows); return { state, sheet: bench.benchPourSheet(state) }; };
const fix = (on, index, actual) => { const f = bench.benchPourFix(on.state, on.sheet.rows, index, actual);
  const sheet = f.state && f.kind !== 'same' ? bench.benchPourSheet(f.state) : on.sheet;
  const { state, ...plain } = f;
  return { f: plain, state, sheet, text: bench.benchPourFixText(f, sheet, '5') }; };
const view = (sheet) => sheet.rows.map((r) => [r.material, r.amount_decimal, r.amount_unit, r.pour_fix || '']);
"""


def _bench(script, rows=None):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the bench-sheet logic test needs it")
    program = (
        f"const bench = require({json.dumps(str(BENCH_SHEET_JS))});\n{PRELUDE}\n"
        f"const ROWS = {json.dumps(rows or [])};\n"
        f"process.stdout.write(JSON.stringify(({script})(bench)));"
    )
    completed = subprocess.run([node, "-e", program], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(completed.stdout)


def _row(material, amount, fraction="1", unit="uL", **extra):
    return {"material": material, "amount_decimal": amount, "amount_unit": unit, "stock_fraction_decimal": fraction,
            "operation": "MASS_ADD" if unit == "mg" else "DIRECT_ADD", **extra}


# Printed order: Hedione, Iso E Super, the Rose Oxide mix (5 uL of stock poured
# as 10 uL of a 1:1 DPG mix), Velvet Musk, then Ambrox crystals weighed in mg.
ROWS = [
    _row("Hedione", "100", stock_id="s-hed"),
    _row("Iso E Super", "50"),
    _row("Rose Oxide", "5", "0.1"),
    _row("Velvet Musk", "40"),
    _row("Ambrox crystals", "20", unit="mg"),
]


def test_the_first_sheet_is_the_formula_as_written():
    assert _bench("(b) => view(first(ROWS).sheet)", ROWS) == [
        ["Hedione", "100", "uL", ""], ["Iso E Super", "50", "uL", ""], ["Rose Oxide", "5", "uL", ""],
        ["Velvet Musk", "40", "uL", ""], ["Ambrox crystals", "20", "mg", ""],
    ]


def test_an_overshoot_tops_up_the_rows_already_in_and_scales_the_rest():
    result = _bench("(b) => { const r = fix(first(ROWS), 1, '60'); return { f: r.f, rows: view(r.sheet), sheet: r.sheet, text: r.text }; }", ROWS)

    assert (result["f"]["kind"], result["f"]["factor"], result["f"]["percent"]) == ("over", "1.2", "20")
    # Iso E Super is done; Hedione (already in) gets 20 uL more; the rest pour at 1.2 x.
    assert result["rows"] == [
        ["Hedione", "20", "uL", "top-up"], ["Rose Oxide", "6", "uL", ""],
        ["Velvet Musk", "48", "uL", ""], ["Ambrox crystals", "24", "mg", ""],
    ]
    assert result["sheet"]["rows"][0]["stock_id"] == "s-hed"
    text = result["text"]
    assert text["sizeMl"] == "6"
    assert text["notes"] == [
        "Pour fix: Iso E Super went in at 60 µL instead of 50 (20% over). To keep every ratio, the whole batch is now 1.2"
        " times the first sheet: 6 mL instead of 5 mL.",
        "Or leave it: undo this fix, and Iso E Super stays 20% over while the rest pours as before; check its IFRA limit"
        " if it is restricted.",
        "This sheet lists only what still goes in, in basket order, and its totals count only that. Rows marked Top-up"
        " are already partly in.",
    ]


def test_an_overshot_mix_is_measured_in_the_mix_it_was_poured_from():
    # The Rose Oxide row pours 10 uL of the mix; 12 uL went in, 1.2 x.
    result = _bench("(b) => { const r = fix(first(ROWS), 2, '12'); return { f: r.f, rows: view(r.sheet) }; }", ROWS)

    assert (result["f"]["planned"], result["f"]["mix"], result["f"]["factor"]) == ("10", True, "1.2")
    assert result["rows"] == [
        ["Hedione", "20", "uL", "top-up"], ["Iso E Super", "10", "uL", "top-up"],
        ["Velvet Musk", "48", "uL", ""], ["Ambrox crystals", "24", "mg", ""],
    ]


def test_a_second_fix_works_on_the_fixed_sheet_and_keeps_the_whole_batch():
    result = _bench(
        "(b) => { const one = fix(first(ROWS), 1, '60');"
        # On the fixed sheet: Hedione +20 (row 0), Rose 6 (row 1), Musk 48 (row 2), Ambrox 24 mg (row 3).
        " const short = fix(one, 3, '20'); const over = fix(one, 2, '54');"
        " return { short: [short.f.kind, short.f.difference, view(short.sheet), short.text.message],"
        " over: [over.f.factor, view(over.sheet), over.text.sizeMl] }; }",
        ROWS,
    )

    # Ambrox went in at 20 mg of the 24 the fixed sheet asked for: 4 mg missing,
    # and nothing already in is listed again.
    kind, difference, rows, message = result["short"]
    assert (kind, difference) == ("under", "4")
    assert rows == [["Ambrox crystals", "4", "mg", "top-up"]]
    assert message == "Ambrox crystals went in 4 mg short (16.7% under). The sheet now lists the missing amount as a top-up, with what still goes in."

    # Velvet Musk at 54 for 48: the batch becomes 54 / 40 = 1.35 x the first
    # sheet; everything already in is topped up to 1.35 x, nothing twice
    # (Rose Oxide 6.75 - 6 = 0.75 uL, shown to 0.1 uL).
    factor, rows, size = result["over"]
    assert (factor, size) == ("1.35", "6.75")
    assert rows == [
        ["Hedione", "15", "uL", "top-up"], ["Iso E Super", "7.5", "uL", "top-up"],
        ["Rose Oxide", "0.8", "uL", "top-up"], ["Ambrox crystals", "27", "mg", ""],
    ]


def test_a_short_mix_row_gets_the_missing_stock_through_a_new_mix():
    # Rose Oxide pours 10 uL of the mix (5 uL stock); 8 uL went in, so 1 uL of stock is missing.
    result = _bench(
        "(b) => { const r = fix(first(ROWS), 2, '8'); return { message: r.text.message, rows: view(r.sheet),"
        " html: b.benchSheetHtml({ formulaName: 'R', dateText: 'd', totals: b.benchSeparateTotals(r.sheet.rows), rows: r.sheet.rows, critic: {} }) }; }",
        ROWS,
    )

    assert result["message"] == ("Rose Oxide went in 2 µL of the mix short (20% under). The sheet now lists the missing"
                                 " amount as a top-up, with what still goes in.")
    assert result["rows"][0] == ["Rose Oxide", "1", "uL", "top-up"]
    rose = result["html"].split("Rose Oxide", 1)[1].split("</tr>", 1)[0]
    assert "Top-up" in rose
    assert "first mix 10 uL of this stock with 90 uL DPG, then add 10 uL of the mix (it carries the 1 uL)" in rose


def test_small_ml_top_ups_are_shown_in_ul_so_the_mix_rule_applies():
    rows = [_row("Ethanol", "1.5", unit="mL", operation="PRECHARGE"), _row("Bergamot EO", "1.5", unit="mL"), _row("Iso E Super", "200")]
    script = (
        "(b) => { const r = fix(first(ROWS), 2, '201'); return { rows: view(r.sheet), notes: r.text.notes,"
        " html: b.benchSheetHtml({ formulaName: 'R', dateText: 'd', totals: b.benchSeparateTotals(r.sheet.rows), rows: r.sheet.rows, critic: {} }) }; }"
    )
    result = _bench(script, rows)

    # 1.5 mL x 1 / 200 = 0.0075 mL, rounded to 0.008 mL, shown as 8 uL and
    # poured from a mix. A few uL of ethanol is not worth adding.
    assert result["rows"] == [["Bergamot EO", "8", "µL", "top-up"]]
    assert "first mix 20 µL of this stock with 20 µL DPG, then add 16 µL of the mix (it carries the 8 µL)" in result["html"]
    assert "Top-ups too small to add, leave them: Ethanol." in result["notes"]


def test_a_tiny_overshoot_is_not_printed_as_zero_and_tiny_top_ups_are_left_out():
    rows = [_row("Hedione", "4"), _row("Iso E Super", "100"), _row("Calone", "a few drops")]
    result = _bench("(b) => { const r = fix(first(ROWS), 1, '100.04'); return { f: r.f, rows: view(r.sheet), notes: r.text.notes }; }", rows)

    assert (result["f"]["percent"], result["f"]["factor"]) == ("0.04", "1.0004")
    # Hedione would need 0.0016 uL: too small to mix, so it is left out and named.
    assert result["rows"] == [["Calone", "a few drops", "uL", ""]]
    assert "Top-ups too small to add, leave them: Hedione." in result["notes"]
    assert "Not rescaled, the amount is not a plain number: Calone." in result["notes"]


def test_what_cannot_be_fixed_says_why():
    result = _bench(
        "(b) => [['3', '40'], ['3', 'lots'], ['9', '1']]"
        ".map(([i, v]) => { const r = fix(first(ROWS), Number(i), v); return [r.f.kind, r.text.message]; })",
        ROWS,
    )

    assert result == [
        ["same", "Velvet Musk went in as planned; nothing to fix."],
        ["invalid", "Type what went in as a plain number, more than 0."],
        ["invalid", "Pick a row the sheet pours as written."],
    ]


def test_subtracting_decimals_is_exact():
    assert _bench("(b) => [['1.2', '0.9'], ['10', '9.95'], ['3', '3'], ['1', '2'], ['x', '1']].map(([a, c]) => b.subtractDecimalText(a, c))") == [
        "0.3", "0.05", "0", None, None,
    ]
