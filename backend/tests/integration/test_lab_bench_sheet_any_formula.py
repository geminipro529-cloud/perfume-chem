"""Bench sheet for any formula: the pasted-text parser and the sheet logic (node)."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

BENCH_SHEET_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "bench-sheet.js"
FORMULAS = Path(__file__).resolve().parents[3] / "formulas"
LAVANDE = "Lavande_Ambre_Profond_Parallel_A_30mL_EDP.md"


def _bench(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the bench-sheet logic test needs it")
    program = f"const bench = require({json.dumps(str(BENCH_SHEET_JS))});\nprocess.stdout.write(JSON.stringify(({script})(bench)));"
    completed = subprocess.run([node, "-e", program], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(completed.stdout)


# ---- POST /v2/workbench/formula-text ---------------------------------------


@pytest.mark.asyncio
async def test_pasted_formula_text_parses_like_the_same_project_file(client):
    text = (FORMULAS / LAVANDE).read_bytes().decode("utf-8")
    pasted = await client.post("/api/v1/lab/v2/workbench/formula-text", json={"text": text})
    from_file = await client.get("/api/v1/lab/v2/workbench/formula-source", params={"source_path": LAVANDE})

    assert pasted.status_code == 200
    body = pasted.json()
    expected = from_file.json()
    assert body["schema_version"] == "workbench-formula-text-v1"
    assert body["source_path"] is None
    for key in ("formula_name", "warnings", "separate_totals"):
        assert body[key] == expected[key], key
    # Row ids carry the source hash; everything else matches the file's rows.
    assert [{**row, "row_id": None} for row in body["rows"]] == [{**row, "row_id": None} for row in expected["rows"]]
    # The request strips outer whitespace, so the hash is of the stripped text.
    assert body["source_sha256"] == hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
    assert body["separate_totals"] == {"liquid_total_ul": "5600", "mass_total_mg": "300"}
    assert body["inventory_modified"] is False
    assert body["compounding_authority"] is False


@pytest.mark.asyncio
async def test_pasted_table_without_a_heading_takes_the_given_name(client):
    text = "| Material | Dilution | µL |\n|---|---|---|\n| Hedione | neat | 120 |\n| Rose Oxide | 10% w/w in DPG | 6 |\n"
    response = await client.post(
        "/api/v1/lab/v2/workbench/formula-text", json={"text": text, "name": "Rose test 30 mL"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["formula_name"] == "Rose test 30 mL"
    assert [(row["material"], row["amount_decimal"], row["amount_unit"], row["concentration_basis"]) for row in body["rows"]] == [
        ("Hedione", "120", "uL", "NEAT"),
        ("Rose Oxide", "6", "uL", "W_W"),
    ]


@pytest.mark.asyncio
async def test_pasted_text_that_is_blank_or_not_a_formula_is_refused(client):
    blank = await client.post("/api/v1/lab/v2/workbench/formula-text", json={"text": "   "})
    prose = await client.post("/api/v1/lab/v2/workbench/formula-text", json={"text": "just some words"})
    extra = await client.post("/api/v1/lab/v2/workbench/formula-text", json={"text": "x", "path": "../inventory.txt"})

    assert blank.status_code == 422
    assert prose.status_code == 400
    assert prose.json()["error"]["code"] == "INVALID_LAB_COMMAND"
    assert extra.status_code == 422


# ---- bench-sheet.js ---------------------------------------------------------


def test_bottle_size_comes_from_the_name_or_path():
    result = _bench(
        "(b) => [b.benchBottleMl('Fougere_Herbier_30mL_EDP.md'), b.benchBottleMl('pilot 5 ml', 'x'),"
        " b.benchBottleMl('R7 card', 'Femme 50ML'), b.benchBottleMl('R7'), b.benchBottleMl('mlx 0mL 10.5mL')]"
    )

    assert result == ["30", "5", "50", None, "10.5"]


def test_scaling_is_exact_and_rounds_half_up():
    result = _bench(
        "(b) => [b.scaleDecimalText('120', '5', '30', 1), b.scaleDecimalText('13', '5', '30', 1),"
        " b.scaleDecimalText('0.35', '1', '1', 1), b.scaleDecimalText('0.25', '1', '2', 1), b.scaleDecimalText('1', '1', '3', 3),"
        " b.scaleDecimalText('24', '50', '30', 3), b.scaleDecimalText('5', '5', '0', 1), b.scaleDecimalText('a few', '1', '1', 1)]"
    )

    assert result == ["20", "2.2", "0.4", "0.1", "0.333", "40", None, None]


def test_rows_scale_by_unit_and_keep_tiny_rows_and_odd_amounts():
    rows = [
        {"material": "Iso E Super", "amount_decimal": "120", "amount_unit": "uL"},
        {"material": "Ethanol", "amount_decimal": "24", "amount_unit": "mL"},
        {"material": "Ambrox crystals", "amount_decimal": "300", "amount_unit": "mg"},
        {"material": "Coumarin", "amount_decimal": "0.3", "amount_unit": "g"},
        {"material": "Calone", "amount_decimal": "a few", "amount_unit": "uL"},
        {"material": "Damascone", "amount_decimal": "0.15", "amount_unit": "μL"},
    ]
    result = _bench(
        "(b) => { const s = b.benchScaleRows(ROWS, '30', '5'); return { amounts: s.rows.map((r) => r.amount_decimal),"
        " before: s.rows.map((r) => r.unscaled_amount_decimal ?? null), unscaled: s.unscaled, totals: b.benchSeparateTotals(s.rows),"
        " original: ROWS.map((r) => r.amount_decimal) }; }".replace("ROWS", json.dumps(rows))
    )

    assert result["amounts"] == ["20", "4", "50", "0.05", "a few", "0.025"]
    assert result["before"] == ["120", "24", "300", "0.3", None, "0.15"]
    assert result["unscaled"] == ["Calone"]
    assert result["totals"] == {"liquid_total_ul": "check by hand", "mass_total_mg": "100"}
    assert result["original"] == ["120", "24", "300", "0.3", "a few", "0.15"]


_INVENTORY = {
    "baskets": [{"number": 1, "name": "Always used"}, {"number": 10, "name": "Rose"}],
    "stocks": [
        {"stock_id": "s-ro10", "material": "Rose Oxide", "identity_name": "Rose Oxide", "stock_label": "Rose Oxide 10%",
         "fraction_decimal": "0.1", "fraction_basis": "mass_fraction", "carrier": "DPG", "status": "owned",
         "design_ready": True, "basket": 10, "basket_status": "confirmed"},
        {"stock_id": "s-ro1", "material": "Rose Oxide", "identity_name": "Rose Oxide", "stock_label": "Rose Oxide 1%",
         "fraction_decimal": "0.01", "fraction_basis": "volume_fraction", "carrier": "ethanol", "status": "owned",
         "design_ready": True, "basket": 10, "basket_status": "confirmed"},
        {"stock_id": "s-hed-a", "material": "Hedione", "identity_name": "Hedione", "stock_label": "Hedione",
         "fraction_decimal": "1", "fraction_basis": "neat", "carrier": None, "status": "owned", "design_ready": True,
         "basket": 1, "basket_status": "confirmed"},
        {"stock_id": "s-hed-b", "material": "Hedione", "identity_name": "Hedione", "stock_label": "Hedione",
         "fraction_decimal": "1", "fraction_basis": "neat", "carrier": None, "status": "owned", "design_ready": True,
         "basket": 1, "basket_status": "confirmed"},
        {"stock_id": "s-iso-a", "material": "Iso E Super", "stock_label": "Iso E Super (IFF)", "fraction_decimal": "1",
         "fraction_basis": "neat", "status": "owned", "design_ready": True},
        {"stock_id": "s-iso-b", "material": "Iso E Super", "stock_label": "Iso E Super (Shopee)", "fraction_decimal": "1",
         "fraction_basis": "neat", "status": "owned", "design_ready": True},
        {"stock_id": "s-orris", "material": "Orris Liquid", "stock_label": "Orris Liquid 9%", "fraction_decimal": "0.09",
         "fraction_basis": "mass_fraction", "carrier": "DEP", "status": "owned", "design_ready": False,
         "design_hold_reason": "USER_COMPOUNDING_HOLD"},
        {"stock_id": "s-gone", "material": "Romandolide", "stock_label": "Romandolide", "fraction_decimal": "1",
         "fraction_basis": "neat", "status": "depleted", "design_ready": True},
    ],
}


def _source_row(material, amount, fraction, basis, unit="uL"):
    return {"material": material, "amount_decimal": amount, "amount_unit": unit,
            "concentration_fraction_decimal": fraction, "concentration_basis": basis,
            "basket": None, "role": None, "operation": "MASS_ADD" if unit == "mg" else "DIRECT_ADD"}


def test_owned_stocks_fill_name_solvent_and_basket_by_name_and_strength():
    source = [
        _source_row("Rose Oxide", "6", "0.1", "W_W"),
        _source_row("rose  oxide", "30", "0.01", "UNKNOWN"),
        _source_row("Rose Oxide", "12", "0.1", "V_V"),
        _source_row("Hedione", "800", "1", "NEAT"),
        _source_row("Iso E Super", "400", "1", "NEAT"),
        _source_row("Orris Liquid", "50", "0.09", "W_W"),
        _source_row("Romandolide", "60", "1", "NEAT"),
        _source_row("Ambrette", "40", None, "UNKNOWN"),
    ]
    result = _bench(
        "(b) => { const rows = SOURCE.map(b.benchRowFromSource); const m = b.benchMatchStocks(rows, INV);"
        " return { m, lines: b.benchSheetLines(m.rows).lines.map((l) => [l.stockLabel, l.strength]),"
        " notes: b.benchSourceNotes({ scaledFrom: '30', scaledTo: '5', unscaled: ['Calone'], unmatched: m.unmatched,"
        " ambiguous: m.ambiguous, held: m.held, warnings: ['Row 4 repeats a material.'] }),"
        " html: b.benchSheetHtml({ formulaName: 'Rose <test>', dateText: 'd', totals: b.benchSeparateTotals(m.rows), rows: m.rows,"
        " critic: {}, basketLookup: b.benchBasketLookup(INV), notes: ['A <b>note</b>'] }) }; }"
        .replace("SOURCE", json.dumps(source)).replace("INV", json.dumps(_INVENTORY))
    )

    rows = result["m"]["rows"]
    assert [row.get("stock_id") for row in rows] == ["s-ro10", "s-ro1", None, "s-hed-a", None, "s-orris", None, None]
    assert result["lines"] == [
        ["Rose Oxide 10%", "10% w/w in DPG"],
        ["Rose Oxide 1%", "1% v/v in ethanol"],
        ["Rose Oxide", "10% v/v"],
        ["Hedione", "100% neat"],
        ["Iso E Super", "100% neat"],
        ["Orris Liquid 9%", "9% w/w in DEP"],
        ["Romandolide", "100% neat"],
        ["Ambrette", "strength not stated"],
    ]
    assert result["m"]["unmatched"] == ["Rose Oxide", "Romandolide", "Ambrette"]
    assert result["m"]["ambiguous"] == ["Iso E Super"]
    assert result["m"]["held"] == ["Orris Liquid 9% (user compounding hold)"]
    assert rows[5]["execution_ready"] is False

    assert result["notes"] == [
        "Scaled from the 30 mL formula to 5 mL; µL and mg rounded to one decimal.",
        "Not scaled, the amount is not a plain number: Calone.",
        "On hold in Stock: Orris Liquid 9% (user compounding hold).",
        "No owned stock with this name and strength, check the bottle: Rose Oxide, Romandolide, Ambrette.",
        "More than one owned stock fits, pick the bottle by hand: Iso E Super.",
        "From the file: Row 4 repeats a material.",
    ]

    html = result["html"]
    assert "Proposal · check hold" in html
    assert '<p class="bench-sheet-note">A &lt;b&gt;note&lt;/b&gt;</p>' in html
    assert "Rose &lt;test&gt;" in html
    # The 6 uL Rose Oxide row goes in from a DPG mix, under its basket heading.
    rose = html.split("Basket 10 · Rose", 1)[1]
    assert "first mix 20 uL of this stock with 20 uL DPG, then add 12 uL of the mix" in rose
    assert "1 row under 10 µL goes in from a mix; the mix adds 6 µL DPG to the bottle." in html


def test_name_lists_in_notes_are_short():
    result = _bench("(b) => b.benchSourceNotes({ unmatched: ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'A'] })")

    assert result == ["No owned stock with this name and strength, check the bottle: A, B, C, D, E, F and 2 more."]
