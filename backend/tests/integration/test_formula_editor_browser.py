"""Edit a formula: load a card, edit it from the keyboard, switch units, paste, undo."""

import json

import pytest

from app.services.formula_checks import FormulaChecksRequest, compute_formula_checks

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


def _window(label, shares):
    return {"label": label, "effective_voices": len(shares), "top": list(shares)[:3],
            "materials": [{"name": name, "known": True, "oav": 10.0, "share": share, "note": "heart"} for name, share in shares.items()]}


SCENT = {"schema_version": "scent-curve-v1", "windows": [
    _window(label, {"Hedione": 0.6, "Iso E Super": 0.4}) for label in ("opening", "top", "heart", "late_heart", "drydown")
]}


def _open(lab, checks=None, charts=None):
    def formula_checks(route, request):
        # The real check, so the page's request must pass the server's validation.
        body = json.loads(request.post_data)
        if checks is not None:
            checks.append(body)
        answer = compute_formula_checks(FormulaChecksRequest.model_validate(body))
        route.fulfill(status=200, content_type="application/json", body=json.dumps(answer))

    def scent_curve(route, request):
        if charts is not None:
            charts.append(json.loads(request.post_data)["rows"])
        route.fulfill(status=200, content_type="application/json", body=json.dumps(SCENT))

    lab.on("POST", "/v2/workbench/formula-checks", formula_checks)
    lab.on("POST", "/v2/workbench/scent-curve", scent_curve)
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


PRICES = {
    "schema_version": "workbench-stock-prices-v1",
    "prices": {
        "s-hed": {"stock_id": "s-hed", "per_unit": "mL", "price_decimal": "2", "currency": "THB"},
        # Priced per g: the editor weighs the row by its density so it is costed.
        "s-iso": {"stock_id": "s-iso", "per_unit": "g", "price_decimal": "1.5", "currency": "THB"},
        "ethanol": {"stock_id": "ethanol", "per_unit": "mL", "price_decimal": "0.1", "currency": "THB"},
        "packaging_per_bottle": {"stock_id": "packaging_per_bottle", "per_unit": "bottle", "price_decimal": "50", "currency": "THB"},
    },
    "cost_item_units": {"ethanol": "mL", "packaging_per_bottle": "bottle"},
    "price_source": "typed by you on the Stock page",
    "inventory_modified": False,
    "compounding_authority": False,
}


def _text(lab, selector):
    return lab.page.text_content(selector)


def _list(lab, selector):
    return lab.page.eval_on_selector_all(f"{selector} li", "(nodes) => nodes.map((node) => node.textContent)")


def _wait_text(lab, selector, text):
    lab.page.wait_for_function(
        "([selector, text]) => document.querySelector(selector).textContent.includes(text)", arg=[selector, text]
    )


def test_the_side_panel_checks_ifra_allergens_cost_and_stock_as_the_formula_changes(lab):
    lab.respond("GET", "/v2/workbench/stock-prices", json=PRICES)
    lab.respond("GET", "/materials", json=[{"id": "m-hed", "canonical_name": "Hedione"}])
    lab.respond("GET", "/stocks", json=[{"id": "lab-hed", "material_id": "m-hed", "active_fraction": 1, "fraction_basis": "neat",
                                         "initial_mass_g": 50, "density_g_ml": 0.999}])
    lab.respond("GET", "/stocks/lab-hed", json={"id": "lab-hed", "remaining_mass_g": 10.5})
    checks, charts = [], []
    _open(lab, checks, charts)
    _load_card(lab)
    page = lab.page

    # IFRA: Velvet Musk is not in the table, so the check holds, as the release gate does.
    _wait_text(lab, "#editor-ifra-verdict", "IFRA 51")
    assert _text(lab, "#editor-ifra-verdict") == "Not fully checked · IFRA 51, Category 4 (fine fragrance)"
    assert "is-hold" in page.get_attribute("#editor-ifra-verdict", "class")
    assert "Not in the IFRA table, so not checked: Velvet Musk" in _list(lab, "#editor-ifra-list")
    assert _text(lab, "#editor-side-oil") == "3.5% oil in a 30 mL bottle, topped up with 28.9 mL ethanol."
    assert _text(lab, "#editor-allergen-summary").startswith("None over the label line (0.001% for leave-on).")
    assert checks[-1]["rows"][3] == {"material": "Ambrox", "amount_mg": "120", "stock_fraction": "1", "fraction_basis": "neat", "carrier": None}

    # Cost: Hedione 0.6 mL x 2, Iso E Super 0.355644 g x 1.5, ethanol 28.94 mL x 0.1, packaging 50.
    _wait_text(lab, "#editor-cost-summary", "54.63 THB per bottle")
    assert _text(lab, "#editor-cost-summary") == "54.63 THB per bottle, not counting what is listed below."
    assert _list(lab, "#editor-cost-list") == [
        "Rose Oxide: no price yet", "Ambrox: no price yet", "Velvet Musk: no price: not matched to a stock",
    ]

    # Stock left: the weighed Hedione bottle in the Lab, less 600 µL at 0.999 g/mL.
    _wait_text(lab, "#editor-stock-list", "10.50 g now")
    assert _list(lab, "#editor-stock-list") == [
        "Hedione: 10.50 g now, 9.90 g after 1 bottle",
        "No weighed bottle in the Lab: Rose Oxide, Iso E Super, Ambrox, Velvet Musk",
    ]
    page.fill("#editor-bottles", "20")
    assert _text(lab, "#editor-stock-summary") == "Not enough for 20 bottles: Hedione."
    assert _list(lab, "#editor-stock-list")[0] == "Hedione: needs 11.99 g, 10.50 g left"
    assert _text(lab, "#editor-cost-summary") == "54.63 THB per bottle, 1092.55 THB for 20, not counting what is listed below."

    # A row over its IFRA limit turns the check red: 0.1 g in 24.0 g of perfume is 0.416%.
    redrawn = lambda request: "scent-curve" in request.url and "Cinnamic Aldehyde" in (request.post_data or "")  # noqa: E731
    with page.expect_request(redrawn):
        page.click("#editor-add-row")
        page.keyboard.type("Cinnamic Aldehyde")
        page.keyboard.press("Tab")
        page.keyboard.type("100")
        page.keyboard.press("Enter")
    _wait_text(lab, "#editor-ifra-verdict", "Over an IFRA limit")
    assert "is-fail" in page.get_attribute("#editor-ifra-verdict", "class")
    assert "Cinnamic Aldehyde: 0.42% of the bottle, limit 0.25%" in _list(lab, "#editor-ifra-list")

    # The smell chart is drawn from the liquid rows (Ambrox is weighed in mg).
    page.wait_for_function("!document.getElementById('editor-scent').hidden && document.querySelector('#editor-scent svg')")
    assert [row["identity_name"] for row in charts[-1]] == ["Hedione", "Rose Oxide", "Iso E Super", "Velvet Musk", "Cinnamic Aldehyde"]
    # Typing pauses are what ask the server: one check per saved edit, not one per key.
    assert len(checks) <= 4


def _versions(lab, monkeypatch, tmp_path, saves):
    """Answer the versions routes with the real service, on a log in tmp_path."""
    from app.services import batch_production as batches
    from app.services import formula_versions as versions

    monkeypatch.setenv(versions.VERSION_LOG_PATH_ENV, str(tmp_path / "formula_versions.jsonl"))
    monkeypatch.setenv(batches.BATCH_RECORD_PATH_ENV, str(tmp_path / "batch_records.jsonl"))
    monkeypatch.setenv(batches.BATCH_DIR_ENV, str(tmp_path / "batches"))
    base = "/v2/workbench/formula-versions"

    def register(formula_id, number):
        lab.respond("GET", f"{base}/{formula_id}/{number}", json=versions.get_version(formula_id, number))

    def save(route, request):
        body = json.loads(request.post_data)
        saves.append(body)
        record, created = versions.save_version(versions.FormulaVersionSave.model_validate(body))
        register(record["formula_id"], record["version"])
        route.fulfill(status=201 if created else 200, content_type="application/json", body=json.dumps({**record, "created": created}))

    def listing(route, _request):
        answer = versions.list_formulas()
        for formula in answer["formulas"]:
            for version in formula["versions"]:
                register(formula["formula_id"], version["version"])
        route.fulfill(status=200, content_type="application/json", body=json.dumps(answer))

    lab.on("POST", base, save)
    lab.on("GET", base, listing)
    return batches


def test_every_save_is_a_version_you_can_reopen_compare_and_see_locked_by_a_batch(lab, monkeypatch, tmp_path):
    saves = []
    _open(lab)
    batches = _versions(lab, monkeypatch, tmp_path, saves)
    _load_card(lab)
    page = lab.page
    state = "#editor-version-state"
    assert page.text_content(state).startswith("Not saved yet.")
    assert page.is_hidden("#editor-versions")

    # Ctrl+S from any field saves the first version, rows exactly as on screen.
    page.focus("#editor-name")
    page.keyboard.press("Control+s")
    lab.wait_for_status("Saved as version 1.")
    first = saves[0]
    assert "formula_id" not in first and first["name"] == "Rose Test" and first["bottle_ml"] == "30"
    assert [(row["material"], row["amount"], row["stock_id"]) for row in first["rows"]] == [
        ("Hedione", "600", "s-hed"), ("Rose Oxide", "30", "s-ro10"), ("Iso E Super", "370", "s-iso"),
        ("Ambrox", "120", "s-amb"), ("Velvet Musk", "60", None),
    ]
    assert "| Rose Oxide | 10% w/w in DPG | 30 |" in first["card_text"]
    page.wait_for_function("!document.querySelector('#editor-versions').hidden")
    assert "No changes since." in page.text_content(state)
    assert page.text_content("#editor-versions-title") == "Versions of Rose Test"

    cell = '#editor-rows tr:nth-child(1) [data-field="amount"]'
    page.fill(cell, "650")
    page.press(cell, "Enter")
    assert page.text_content(state) == "Changed since version 1 of Rose Test. Saving makes version 2."
    page.fill("#editor-version-note", "more Hedione")
    page.click("#editor-save-version")
    lab.wait_for_status("Saved as version 2.")
    formula_id = json.loads((tmp_path / "formula_versions.jsonl").read_text().splitlines()[0])["version"]["formula_id"]
    assert (saves[1]["formula_id"], saves[1]["parent_version"], saves[1]["note"]) == (formula_id, 1, "more Hedione")
    assert page.input_value("#editor-version-note") == ""

    # Saving again with nothing changed sends nothing.
    page.focus(cell)
    page.keyboard.press("Control+s")
    lab.wait_for_status("No changes since version 2, so nothing new was saved.")
    assert len(saves) == 2

    # The comparison opens on the version before and this one.
    page.wait_for_function("document.querySelectorAll('#editor-version-list li').length === 2")
    assert page.input_value("#editor-compare-a") == "1" and page.input_value("#editor-compare-b") == "2"
    page.click("#editor-compare-form button[type=submit]")
    page.wait_for_selector(".editor-compare-table")
    cells = page.eval_on_selector_all(".editor-compare-table tbody td", "(nodes) => nodes.map((node) => node.textContent)")
    # 600 of 1060 µL of liquid, then 650 of 1110: the Ambrox crystals are weighed, not liquid.
    assert cells == ["Hedione", "neat", "600 µL", "650 µL", "+50 µL", "56.6% → 58.56%"]
    compare = page.text_content("#editor-compare")
    assert "4 rows unchanged. Liquid: 1060 µL → 1110 µL." in compare
    assert "Oil: 3.5% → 3.7%" in compare

    # Opening version 1 puts its rows back; Undo returns to what was there.
    page.click("#editor-version-list button[data-version='1']")
    page.wait_for_function("document.querySelector('#editor-rows [data-field=amount]').value === '600'")
    assert page.text_content(state).startswith("Version 1 of Rose Test, saved ")
    page.click("#editor-undo")
    assert _cells(lab, "amount")[0] == "650"

    # A batch made from version 1's card locks it; a reload finds the saved formula.
    plan = batches.plan_batch(source_path=None, text=first["card_text"], name=None, bottles="2", bottle_ml="30", card_total_ml="30", loss_percent="3")
    batches.record_batch(lot="KS-20261014-01", made_on="2026-10-14", made_by="", plan=plan, gate_run_id=None, notes="")
    lab.reload()
    page.select_option('#editor-source-form [name="source_kind"]', "SAVED")
    page.wait_for_function("document.querySelector('#editor-source-form [name=saved_formula]').options[0]?.value.length === 32")
    assert page.eval_on_selector('#editor-source-form [name="saved_formula"]', "(node) => node.options[0].textContent").startswith("Rose Test · 2 versions, last saved ")
    page.click("#editor-source-form button[type=submit]")
    page.wait_for_function("document.querySelector('#editor-rows [data-field=amount]')?.value === '650'")
    assert page.text_content(state).startswith("Version 2 of Rose Test, saved ")
    items = page.eval_on_selector_all("#editor-version-list li", "(nodes) => nodes.map((node) => node.textContent)")
    assert "locked: batch KS-20261014-01" in items[1] and "locked" not in items[0]
    assert "“more Hedione”" in items[0]
