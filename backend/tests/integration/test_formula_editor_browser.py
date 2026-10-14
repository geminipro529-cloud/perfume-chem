"""Edit a formula: load a card, edit it from the keyboard, switch units, paste, undo."""

import json

import pytest

pytest.importorskip("playwright.sync_api")

LIBRARY = {"sources": [{"source_path": "Rose_Test_30mL_EDP.md", "display_name": "Rose Test 30mL EDP", "design_only": True}]}
SOURCE_PATH = "/v2/workbench/formula-source?source_path=Rose_Test_30mL_EDP.md"


def _stock(stock_id, material, fraction, basis, carrier=None, **extra):
    return {"stock_id": stock_id, "material": material, "identity_name": material, "stock_label": material,
            "fraction_decimal": fraction, "fraction_percent_decimal": str(float(fraction) * 100),
            "fraction_basis": basis, "carrier": carrier, "status": "owned", "design_ready": True, **extra}


INVENTORY = {
    "counts": {},
    "stocks": [
        _stock("s-hed", "Hedione", "1", "neat"),
        _stock("s-iso", "Iso E Super", "1", "neat"),
        _stock("s-ro10", "Rose Oxide", "0.1", "mass_fraction", "dpg"),
        _stock("s-ro1", "Rose Oxide", "0.01", "mass_fraction", "dpg"),
        _stock("s-amb", "Ambrox", "1", "neat", physical_form="crystals"),
    ],
}


def _row(material, amount, fraction, basis, unit="uL"):
    return {"row_id": material, "material": material, "amount_decimal": amount, "amount_unit": unit,
            "concentration_fraction_decimal": fraction, "concentration_basis": basis, "basket": None,
            "role": None, "operation": "MASS_ADD" if unit == "mg" else "DIRECT_ADD"}


SOURCE = {
    "schema_version": "workbench-formula-source-v1",
    "source_path": "Rose_Test_30mL_EDP.md",
    "formula_name": "Rose Test",
    "rows": [
        _row("Hedione", "600", "1", "NEAT"),
        _row("Rose Oxide", "30", "0.1", "W_W"),
        _row("Iso E Super", "370", "1", "NEAT"),
        _row("Ambrox", "120", "1", "NEAT", "mg"),
        _row("Velvet Musk", "60", "0.1", "W_W"),
    ],
    "warnings": [],
    "separate_totals": {"liquid_total_ul": "1060", "mass_total_mg": "120"},
}

DENSITIES = {"Hedione": "0.999", "Iso E Super": "0.9612", "Rose Oxide": None, "Ambrox": None, "Velvet Musk": None}


def _open(lab):
    lab.respond("GET", "/v2/workbench/formula-library", json=LIBRARY)
    lab.respond("GET", "/v2/workbench/current-inventory", json=INVENTORY)
    lab.respond("GET", SOURCE_PATH, json=SOURCE)

    def densities(route, request):
        names = json.loads(request.post_data)["names"]
        body = {"schema_version": "workbench-material-densities-v1", "densities": {name: DENSITIES.get(name) for name in names},
                "inventory_modified": False, "compounding_authority": False}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

    lab.on("POST", "/v2/workbench/material-densities", densities)
    lab.open("#editor")


def _load_card(lab):
    page = lab.page
    page.select_option('#editor-source-form [name="source_kind"]', "PROJECT_FILE")
    page.fill('#editor-source-form [name="project_formula_path"]', "Rose_Test_30mL_EDP.md")
    page.click("#editor-source-form button[type=submit]")
    page.wait_for_function("document.querySelectorAll('#editor-rows tr[data-key]').length === 5")


def _cells(lab, field):
    return lab.page.eval_on_selector_all(f'#editor-rows [data-field="{field}"]', "(nodes) => nodes.map((node) => node.value)")


def _stock_cells(lab):
    return lab.page.eval_on_selector_all("#editor-rows .editor-stock", "(nodes) => nodes.map((node) => node.textContent)")


def test_a_loaded_card_binds_owned_stocks_and_shows_it_in_every_unit_without_changing_it(lab):
    _open(lab)
    _load_card(lab)
    page = lab.page

    assert page.input_value("#editor-name") == "Rose Test"
    assert _cells(lab, "material") == [
        "Hedione · Neat", "Rose Oxide · 10% w/w in DPG", "Iso E Super · Neat", "Ambrox · Neat crystals, weighed in mg", "Velvet Musk",
    ]
    assert _stock_cells(lab)[4] == "Not in your stock"
    assert _cells(lab, "amount") == ["600", "30", "370", "120", "60"]
    assert page.text_content("#editor-totals") == "5 rows · 1060 µL liquid · 120 mg solids"
    notes = page.text_content("#editor-notes")
    assert "Not in your stock at that strength: Velvet Musk." in notes

    page.select_option("#editor-unit", "pct")
    # Shares of the liquid; the solid stays in mg.
    assert _cells(lab, "amount") == ["56.6", "2.83", "34.91", "120", "5.66"]
    page.select_option("#editor-unit", "parts")
    assert _cells(lab, "amount") == ["566", "28.3", "349.1", "120", "56.6"]
    page.select_option("#editor-unit", "g")
    page.wait_for_function("document.querySelector('#editor-rows [data-field=amount]').value === '0.599'")
    # Rose Oxide 10% w/w in DPG takes 1 g/mL for the unknown material; Velvet Musk has no stock.
    assert _cells(lab, "amount") == ["0.599", "0.031", "0.356", "0.12", ""]
    assert page.get_attribute('#editor-rows tr:nth-child(5) [data-field="amount"]', "placeholder") == "density not known"
    page.select_option("#editor-unit", "uL")
    assert _cells(lab, "amount") == ["600", "30", "370", "120", "60"]
    assert page.is_disabled("#editor-undo") is False  # the load itself can be undone


def test_rows_are_typed_from_the_keyboard_and_undo_and_redo_step_through_them(lab):
    _open(lab)
    page = lab.page
    material = '#editor-rows tr:nth-child(1) [data-field="material"]'
    page.click(material)
    page.keyboard.type("hedione")
    page.keyboard.press("Enter")
    # Enter saves the cell, binds the only Hedione stock and opens a new row below.
    page.wait_for_function("document.querySelectorAll('#editor-rows tr[data-key]').length === 2")
    assert _cells(lab, "material") == ["Hedione · Neat", ""]
    assert page.evaluate("document.activeElement.dataset.field") == "material"
    page.keyboard.type("Iso E Super")
    page.keyboard.press("Tab")
    page.keyboard.type("400")
    page.keyboard.press("ArrowUp")
    assert page.evaluate("document.activeElement.closest('tr').querySelector('td').textContent") == "1"
    page.keyboard.type("600")
    page.keyboard.press("Enter")
    assert _cells(lab, "amount") == ["600", "400"]
    assert page.text_content("#editor-totals") == "2 rows · 1000 µL liquid"

    page.keyboard.press("Control+z")
    assert _cells(lab, "amount") == ["", "400"]
    page.keyboard.press("Control+y")
    assert _cells(lab, "amount") == ["600", "400"]

    # In the % view a typed share sets that row; the other rows keep their µL.
    page.select_option("#editor-unit", "pct")
    first = '#editor-rows tr:nth-child(1) [data-field="amount"]'
    page.fill(first, "75")
    page.press(first, "Enter")
    page.select_option("#editor-unit", "uL")
    assert _cells(lab, "amount") == ["1200", "400"]

    # Ctrl+Enter adds a row below; Ctrl+Delete removes the row it is in.
    page.focus(first)
    page.keyboard.press("Control+Enter")
    assert len(_cells(lab, "material")) == 3
    assert page.evaluate("document.activeElement.closest('tr').querySelector('td').textContent") == "2"
    page.keyboard.press("Control+Delete")
    assert _cells(lab, "amount") == ["1200", "400"]


def test_a_bad_amount_is_named_and_not_saved(lab):
    _open(lab)
    _load_card(lab)
    page = lab.page
    cell = '#editor-rows tr:nth-child(2) [data-field="amount"]'
    page.fill(cell, "abc")
    page.press(cell, "Enter")
    assert page.is_visible("#editor-error")
    assert page.text_content("#editor-error") == '"abc" is not an amount. Type a number such as 120 or 0.5.'
    assert page.get_attribute(cell, "aria-invalid") == "true"
    page.fill(cell, "45")
    page.press(cell, "Enter")
    assert page.is_hidden("#editor-error")
    assert _cells(lab, "amount")[1] == "45"


def test_rows_pasted_from_a_spreadsheet_go_in_below_and_are_bound(lab):
    _open(lab)
    _load_card(lab)
    page = lab.page
    cell = '#editor-rows tr:nth-child(3) [data-field="material"]'
    page.focus(cell)
    page.evaluate(
        """(text) => {
          const data = new DataTransfer();
          data.setData("text/plain", text);
          document.activeElement.dispatchEvent(new ClipboardEvent("paste", { clipboardData: data, bubbles: true, cancelable: true }));
        }""",
        "Material\tStrength\tAmount\nRose Oxide\t1%\t15\nCashmeran\tneat\t40 µL\n",
    )
    page.wait_for_function("document.querySelectorAll('#editor-rows tr[data-key]').length === 7")
    assert _cells(lab, "material")[3:5] == ["Rose Oxide · 1% w/w in DPG", "Cashmeran"]
    assert _cells(lab, "amount")[3:5] == ["15", "40"]
    assert "Pasted 2 rows." in page.text_content("#editor-notes")
    page.click("#editor-undo")
    assert len(_cells(lab, "material")) == 5


def test_sorting_and_scaling_keep_every_share(lab):
    _open(lab)
    _load_card(lab)
    page = lab.page
    page.click("#editor-sort-amount")
    assert _cells(lab, "amount") == ["600", "370", "60", "30", "120"]
    page.select_option('#editor-rows tr:nth-child(5) [data-field="note"]', "base")
    page.select_option('#editor-rows tr:nth-child(4) [data-field="note"]', "top")
    page.click("#editor-sort-note")
    assert _cells(lab, "material")[:2] == ["Rose Oxide · 10% w/w in DPG", "Ambrox · Neat crystals, weighed in mg"]
    page.fill("#editor-scale-to", "2120")
    page.click("#editor-scale")
    assert page.text_content("#editor-totals") == "5 rows · 2120 µL liquid · 240 mg solids"


def test_open_on_the_bench_sheet_hands_over_the_rows_as_a_card_table(lab):
    _open(lab)
    _load_card(lab)
    page = lab.page
    posted = []

    def formula_text(route, request):
        posted.append(json.loads(request.post_data)["text"])
        body = {**SOURCE, "schema_version": "workbench-formula-text-v1", "source_path": None}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

    lab.on("POST", "/v2/workbench/formula-text", formula_text)
    page.click("#editor-to-bench")
    page.wait_for_function("!document.getElementById('bench-preview-card').hidden")
    assert page.evaluate("location.hash") == "#benchsheet"
    assert posted == [
        "# Rose Test\n\n| Material | Dilution | Amount (µL) |\n|---|---|---:|\n"
        "| Hedione | neat | 600 |\n| Rose Oxide | 10% w/w in DPG | 30 |\n| Iso E Super | neat | 370 |\n"
        "| Ambrox | neat | 120 mg |\n| Velvet Musk | 10% w/w | 60 |\n"
    ]
