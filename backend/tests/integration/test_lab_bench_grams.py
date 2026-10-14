"""Bench sheet in grams: liquid rows weighed on a balance by each stock's density (node + endpoint)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

BENCH_SHEET_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "bench-sheet.js"


def _bench(script, rows=None, densities=None):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the bench-sheet logic test needs it")
    program = (
        f"const bench = require({json.dumps(str(BENCH_SHEET_JS))});\n"
        f"const ROWS = {json.dumps(rows or [])};\n"
        f"const DENSITIES = {json.dumps(densities or {})};\n"
        f"process.stdout.write(JSON.stringify(({script})(bench)));"
    )
    completed = subprocess.run([node, "-e", program], capture_output=True, text=True, encoding="utf-8", timeout=60, check=True)
    return json.loads(completed.stdout)


def _row(material, amount, fraction="1", unit="uL", basis="neat", carrier=None, **extra):
    return {"material": material, "amount_decimal": amount, "amount_unit": unit, "stock_fraction_decimal": fraction,
            "fraction_basis": basis, "carrier": carrier, "operation": "MASS_ADD" if unit == "mg" else "DIRECT_ADD", **extra}


DENSITIES = {"Hedione": "0.999", "Iso E Super": "0.9612", "Linalool": "0.858", "Rose Ketone": "0.9"}


def _grams(rows, densities=DENSITIES):
    return _bench("(b) => b.benchRowsInGrams(ROWS, DENSITIES)", rows, densities)


def test_a_neat_row_is_weighed_by_the_material_density():
    result = _grams([_row("Hedione", "1000")])
    row = result["rows"][0]
    assert (row["amount_decimal"], row["amount_unit"]) == ("0.999", "g")
    assert (row["weighed_from_ul"], row["stock_density_g_ml"]) == ("1000", "0.999")
    assert result["estimated"] == result["assumed"] == result["light"] == result["unknown"] == []


def test_a_dilution_mixes_the_material_and_carrier_densities_by_its_basis():
    rows = [
        # 10% w/w in DPG: 1 / (0.1/0.9 + 0.9/1.023) = 1.0092 g/mL
        _row("Rose Ketone", "1000", "0.1", basis="mass_fraction", carrier="DPG"),
        # 10% v/v in ethanol: 0.1 x 0.858 + 0.9 x 0.789 = 0.7959 g/mL
        _row("Linalool", "500", "0.1", basis="volume_fraction", carrier="ethanol"),
        # No recorded basis reads as w/w (Kenny's rule); "dpg w/w" is DPG.
        _row("Iso E Super", "300", "0.1", basis="unspecified", carrier="dpg w/w"),
    ]
    result = _grams(rows)
    assert [(r["amount_decimal"], r["amount_unit"], r["stock_density_g_ml"]) for r in result["rows"]] == [
        ("1.009", "g", "1.0092"), ("0.398", "g", "0.7959"), ("0.305", "g", "1.0165"),
    ]
    assert result["estimated"] == ["Rose Ketone", "Linalool", "Iso E Super"]


def test_an_unknown_material_density_is_assumed_only_in_a_weak_dilution():
    rows = [
        _row("Unlisted Musk", "200", "0.05", basis="mass_fraction", carrier="DPG"),
        _row("Unlisted Wood", "200", "0.2", basis="mass_fraction", carrier="DPG"),
        _row("Unlisted Neat", "200"),
        _row("Unlisted Dilution", "200", "0.1", basis="mass_fraction"),  # no carrier recorded
    ]
    result = _grams(rows)
    assert [(r["amount_decimal"], r["amount_unit"]) for r in result["rows"]] == [
        ("0.204", "g"), ("200", "uL"), ("200", "uL"), ("200", "uL"),
    ]
    assert result["assumed"] == ["Unlisted Musk"]
    assert result["unknown"] == ["Unlisted Wood", "Unlisted Neat", "Unlisted Dilution"]


def test_light_rows_mix_rows_and_solids_stay_as_they_are():
    rows = [
        _row("Hedione", "50"),  # 0.05 g: under the 0.1 g weighing floor
        _row("Linalool", "5", "0.01", basis="mass_fraction", carrier="DPG"),  # under 10 uL: a mix row
        _row("Ambrox crystals", "20", unit="mg"),
        _row("Ethanol", "2000", carrier=None),  # carrier row: its own density
    ]
    result = _grams(rows)
    assert [(r["amount_decimal"], r["amount_unit"]) for r in result["rows"]] == [
        ("50", "uL"), ("5", "uL"), ("20", "mg"), ("1.578", "g"),
    ]
    assert result["light"] == ["Hedione", "Linalool"]


def test_the_notes_say_what_was_weighed_and_what_stays_in_ul():
    rows = [
        _row("Hedione", "1000"),
        _row("Rose Ketone", "1000", "0.1", basis="mass_fraction", carrier="DPG"),
        _row("Unlisted Musk", "200", "0.05", basis="mass_fraction", carrier="DPG"),
        _row("Linalool", "50"),
        _row("Unlisted Neat", "200"),
    ]
    notes = _bench("(b) => b.benchGramsNotes(b.benchRowsInGrams(ROWS, DENSITIES))", rows, DENSITIES)
    assert notes[0].startswith("3 rows in grams for the balance: tare it before each weighed row.")
    assert "Rose Ketone" in notes[1] and "assuming the volumes add" in notes[1]
    assert "1 g/mL assumed" in notes[2] and "Unlisted Musk" in notes[2]
    assert "under 0.1 g" in notes[3] and "Linalool" in notes[3]
    assert notes[4] == "Still in µL, density not known: Unlisted Neat."


def test_the_header_totals_split_weighed_grams_from_pipetted_ul():
    rows = [
        _row("Hedione", "1000"),
        _row("Iso E Super", "2000"),
        _row("Linalool", "50"),
        _row("Ambrox crystals", "20", unit="mg"),
    ]
    script = """(b) => {
      const sheet = b.benchRowsInGrams(ROWS, DENSITIES);
      const totals = b.benchWeighedTotals(sheet.rows);
      const html = b.benchSheetHtml({ formulaName: 'T', variantLabel: '', dateText: 'today', totals, rows: sheet.rows, critic: {} });
      return { totals, html };
    }"""
    result = _bench(script, rows, DENSITIES)
    assert result["totals"] == {"liquid_total_ul": "50", "mass_total_mg": "20", "weighed_total_g": "2.921"}
    assert "2.921 g liquid weighed on the balance · 50 µL pipetted · 20 mg solids" in result["html"]


def test_a_pour_fix_on_a_weighed_row_works_in_grams():
    rows = [
        _row("Hedione", "1000"),
        _row("Iso E Super", "2000"),
        _row("Linalool", "50"),
    ]
    script = """(b) => {
      const start = b.benchPourStart(b.benchRowsInGrams(ROWS, DENSITIES).rows);
      const sheet = b.benchPourSheet(start);
      const fix = b.benchPourFix(start, sheet.rows, 0, '1.0989');
      return b.benchPourSheet(fix.state).rows.map((r) => [r.material, r.amount_decimal, r.amount_unit]);
    }"""
    # Hedione went in 10% over (1.0989 g for 0.999 g): the rest is scaled by 1.1.
    assert _bench(script, rows, DENSITIES) == [
        ["Iso E Super", "2.114", "g"], ["Linalool", "55", "uL"],
    ]


@pytest.mark.asyncio
async def test_the_density_endpoint_reads_the_material_data(client):
    response = await client.post(
        "/api/v1/lab/v2/workbench/material-densities",
        json={"names": ["Hedione", "Iso E Super", "Hedione", "Not a material 9f3c"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "workbench-material-densities-v1"
    assert body["densities"] == {"Hedione": "0.999", "Iso E Super": "0.9612", "Not a material 9f3c": None}
    assert body["inventory_modified"] is False
    assert body["compounding_authority"] is False


@pytest.mark.asyncio
async def test_the_density_endpoint_needs_at_least_one_name(client):
    response = await client.post("/api/v1/lab/v2/workbench/material-densities", json={"names": []})
    assert response.status_code == 422
