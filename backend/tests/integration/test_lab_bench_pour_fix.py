"""Pour fix on the bench sheet: what to do after a row went in over or under (node)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

BENCH_SHEET_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "bench-sheet.js"


def _bench(script, rows=None):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the bench-sheet logic test needs it")
    program = (
        f"const bench = require({json.dumps(str(BENCH_SHEET_JS))});\n"
        f"const ROWS = {json.dumps(rows or [])};\n"
        f"process.stdout.write(JSON.stringify(({script})(bench)));"
    )
    completed = subprocess.run([node, "-e", program], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(completed.stdout)


def _row(material, amount, fraction="1", unit="uL", **extra):
    return {"material": material, "amount_decimal": amount, "amount_unit": unit, "stock_fraction_decimal": fraction,
            "operation": "MASS_ADD" if unit == "mg" else "DIRECT_ADD", **extra}


# Sheet order: Hedione and Iso E Super are poured first, then the Rose Oxide
# mix (5 uL of stock poured as 10 uL of a 1:1 DPG mix), Musk, Ambrox crystals.
ROWS = [
    _row("Hedione", "100", stock_id="s-hed"),
    _row("Iso E Super", "50"),
    _row("Rose Oxide", "5", "0.1"),
    _row("Velvet Musk", "40"),
    _row("Ambrox crystals", "20", unit="mg"),
]


def test_an_overshoot_tops_up_the_rows_already_in_and_scales_the_rest():
    result = _bench("(b) => { const fix = b.benchPourFix(ROWS, 1, '60'); return { fix, text: b.benchPourFixText(fix, '5') }; }", ROWS)
    fix = result["fix"]

    assert fix["kind"] == "over"
    assert (fix["factor"], fix["percent"], fix["topUps"]) == ("1.2", "20", 1)
    # Iso E Super is done; Hedione (already in) gets 20% more; the rest pour at 1.2 x.
    assert [(row["material"], row["amount_decimal"], row.get("pour_fix")) for row in fix["rows"]] == [
        ("Hedione", "20", "top-up"),
        ("Rose Oxide", "6", None),
        ("Velvet Musk", "48", None),
        ("Ambrox crystals", "24", None),
    ]
    assert fix["rows"][0]["stock_id"] == "s-hed"
    text = result["text"]
    assert text["sizeMl"] == "6"
    assert text["notes"][:3] == [
        "Pour fix: Iso E Super went in at 60 µL instead of 50 (20% over). To keep every ratio, this sheet lists only what still"
        " goes in: top-ups for the 1 row already in, then the rest at 1.2 times.",
        "The batch becomes 6 mL instead of 5 mL.",
        "Or leave it: Iso E Super stays 20% over and the rest pours as first printed; check its IFRA limit if it is restricted.",
    ]


def test_an_overshot_mix_is_measured_in_the_mix_it_was_poured_from():
    # The Rose Oxide row pours 10 uL of the mix; 12 uL went in, 1.2 x.
    fix = _bench("(b) => b.benchPourFix(ROWS, 2, '12')", ROWS)

    assert (fix["planned"], fix["mix"], fix["factor"]) == ("10", True, "1.2")
    assert [(row["material"], row["amount_decimal"], row.get("pour_fix")) for row in fix["rows"]] == [
        ("Hedione", "20", "top-up"),
        ("Iso E Super", "10", "top-up"),
        ("Velvet Musk", "48", None),
        ("Ambrox crystals", "24", None),
    ]


def test_the_fixed_sheet_marks_top_ups_and_gives_mixes_for_small_ones():
    html = _bench(
        "(b) => { const fix = b.benchPourFix(ROWS, 3, '42'); return b.benchSheetHtml({ formulaName: 'R', dateText: 'd',"
        " totals: b.benchSeparateTotals(fix.rows), rows: fix.rows, critic: {} }); }",
        ROWS,
    )

    # Velvet Musk 42 for 40 is 5% over: Hedione +5, Iso E Super +2.5, Rose Oxide +0.25.
    hedione = html.split("Hedione", 1)[1].split("</tr>", 1)[0]
    assert "Top-up" in hedione and "first mix 10 uL of this stock with 10 uL DPG, then add 10 uL of the mix (it carries the 5 uL)" in hedione
    assert "Top-up" in html.split("Iso E Super", 1)[1].split("</tr>", 1)[0]
    assert "Top-up" not in html.split("Ambrox crystals", 1)[1].split("</tr>", 1)[0]


def test_top_ups_too_small_to_show_are_left_out_and_listed():
    # Hedione 1 uL (poured from a mix) would need a 0.0001 uL top-up.
    rows = [_row("Hedione", "1"), _row("Iso E Super", "100"), _row("Calone", "a few drops")]
    result = _bench("(b) => { const fix = b.benchPourFix(ROWS, 1, '100.01'); return { fix, text: b.benchPourFixText(fix) }; }", rows)

    assert result["fix"]["skipped"] == ["Hedione"]
    assert [row["amount_decimal"] for row in result["fix"]["rows"]] == ["a few drops"]
    assert "Top-ups too small to matter are left out: Hedione." in result["text"]["notes"]
    assert "Not rescaled, the amount is not a plain number: Calone." in result["text"]["notes"]


def test_a_short_pour_says_what_is_missing_and_how_to_add_it():
    result = _bench(
        "(b) => [['1', '45'], ['1', '48'], ['2', '9'], ['3', '40'], ['3', 'lots'], ['5', '1']]"
        ".map(([i, v]) => b.benchPourFixText(b.benchPourFix(ROWS, Number(i), v)).message)",
        ROWS,
    )

    assert result == [
        "Iso E Super went in 5 µL short (10% under). Under 10 µL: first mix 10 µL of this stock with 10 µL DPG,"
        " then add 10 µL of the mix (it carries the 5 µL).",
        "Iso E Super went in 2 µL short (4% under). Under 10 µL: first mix 10 µL of this stock with 40 µL DPG,"
        " then add 10 µL of the mix (it carries the 2 µL).",
        "Rose Oxide went in 1 µL of the mix short (10% under). Add 1 µL of the mix more, or leave it: under 10 µL is hard to pipette.",
        "Velvet Musk went in as planned; nothing to fix.",
        "Type what went in as a plain number, more than 0.",
        "Pick a row the sheet pours as written.",
    ]


def test_subtracting_decimals_is_exact():
    assert _bench("(b) => [['1.2', '0.9'], ['10', '9.95'], ['3', '3'], ['1', '2'], ['x', '1']].map(([a, c]) => b.subtractDecimalText(a, c))") == [
        "0.3", "0.05", "0", None, None,
    ]
