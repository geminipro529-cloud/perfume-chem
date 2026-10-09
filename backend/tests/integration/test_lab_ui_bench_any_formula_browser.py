"""The Bench sheet view prints any project or pasted formula in basket order."""

import json

import pytest

pytest.importorskip("playwright.sync_api")

LIBRARY = {"sources": [{"source_path": "Rose_Test_30mL_EDP.md", "display_name": "Rose Test 30mL EDP", "design_only": True}]}
SOURCE_PATH = "/v2/workbench/formula-source?source_path=Rose_Test_30mL_EDP.md"
INVENTORY = {
    "counts": {},
    "baskets": [{"number": number, "name": {1: "Always used", 10: "Rose"}.get(number, f"Basket {number}")} for number in range(1, 18)],
    "stocks": [
        {"stock_id": "s-hed", "material": "Hedione", "identity_name": "Hedione", "stock_label": "Hedione",
         "fraction_decimal": "1", "fraction_basis": "neat", "carrier": None, "status": "owned", "design_ready": True,
         "basket": 1, "basket_status": "confirmed"},
        {"stock_id": "s-ro", "material": "Rose Oxide", "identity_name": "Rose Oxide", "stock_label": "Rose Oxide 10%",
         "fraction_decimal": "0.1", "fraction_basis": "mass_fraction", "carrier": "DPG", "status": "owned",
         "design_ready": True, "basket": 10, "basket_status": "confirmed"},
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
        _row("Rose Oxide", "30", "0.1", "W_W"),
        _row("Hedione", "600", "1", "NEAT"),
        _row("Ambrox crystals", "120", "1", "NEAT", "mg"),
        _row("Velvet Musk", "60", "0.1", "W_W"),
    ],
    "warnings": [],
    "separate_totals": {"liquid_total_ul": "690", "mass_total_mg": "120"},
}


def _open(lab):
    lab.respond("GET", "/v2/workbench/formula-library", json=LIBRARY)
    lab.respond("GET", "/v2/workbench/current-inventory", json=INVENTORY)
    lab.open("#benchsheet")


def _pick_file(lab):
    path = lab.page.locator('#bench-source-form [name="project_formula_path"]')
    path.fill("Rose_Test_30mL_EDP.md")
    path.dispatch_event("change")


def test_a_project_formula_scaled_to_5_ml_prints_in_basket_order_with_mixes(lab):
    lab.respond("GET", SOURCE_PATH, json=SOURCE)
    lab.page.add_init_script("window.print = () => { window.__printed = (window.__printed || 0) + 1; };")
    _open(lab)
    _pick_file(lab)
    form = lab.page.locator("#bench-source-form")
    assert form.locator('[name="source_ml"]').input_value() == "30"
    assert lab.page.locator("#bench-source-print").is_disabled()

    form.locator('[name="target_ml"]').fill("5")
    form.locator('button[type="submit"]').click()
    preview = lab.page.locator("#bench-preview")
    preview.locator(".bench-sheet-table").wait_for()

    headings = preview.locator("tr.bench-basket-row th").all_inner_texts()
    assert headings == ["Basket 1 · Always used", "Basket 10 · Rose", "No basket yet"]
    materials = preview.locator("tbody td strong").all_inner_texts()
    assert materials == ["Hedione", "Rose Oxide", "Velvet Musk", "Ambrox crystals"]
    rose = preview.locator("tbody tr", has_text="Rose Oxide")
    # 30 uL at 30 mL is 5 uL at 5 mL: poured as 10 uL of a 1:1 DPG mix.
    assert "first mix 10 uL of this stock with 10 uL DPG, then add 10 uL of the mix (it carries the 5 uL)" in rose.inner_text()
    assert "Rose Oxide 10%" in rose.inner_text() and "10% w/w in DPG" in rose.inner_text()
    assert preview.locator("tbody tr", has_text="Hedione").locator(".bench-amount").first.inner_text() == "100 uL"
    assert preview.locator("tbody tr", has_text="Ambrox crystals").locator(".bench-amount").first.inner_text() == "20 mg"
    text = preview.inner_text()
    assert "Rose Test · 5 mL" in text
    assert "Scaled from the 30 mL formula to 5 mL; µL and mg rounded to one decimal." in text
    assert "No owned stock with this name and strength, check the bottle: Ambrox crystals, Velvet Musk." in text
    assert "115 µL liquid stock" in text

    lab.page.locator("#bench-source-print").click()
    assert lab.page.evaluate("window.__printed") == 1
    assert "Rose Test · 5 mL" in lab.page.locator("#bench-sheet").inner_html()
    assert lab.page.evaluate("document.body.classList.contains('printing-bench-sheet')")

    # Changing the form puts the preview away until it is shown again.
    form.locator('[name="target_ml"]').fill("10")
    assert lab.page.locator("#bench-preview-card").is_hidden()
    assert lab.page.locator("#bench-source-print").is_disabled()
    assert lab.page_errors == []
    assert lab.unexpected == []


def test_a_pasted_table_is_parsed_by_the_server_and_kept_at_its_size(lab):
    seen = []

    def parse(route, request):
        seen.append(json.loads(request.post_data))
        route.fulfill(status=200, content_type="application/json", body=json.dumps(dict(SOURCE, source_path=None, formula_name="Pasted formula")))

    lab.on("POST", "/v2/workbench/formula-text", parse)
    _open(lab)
    form = lab.page.locator("#bench-source-form")
    form.locator('[name="source_kind"]').select_option("PASTED")
    assert lab.page.locator("#bench-project-field").is_hidden()
    form.locator('[name="pasted_text"]').fill("| Material | Dilution | uL |\n|---|---|---|\n| Hedione | neat | 600 |")
    form.locator('button[type="submit"]').click()
    lab.page.locator("#bench-preview .bench-sheet-table").wait_for()

    assert seen == [{"text": "| Material | Dilution | uL |\n|---|---|---|\n| Hedione | neat | 600 |"}]
    text = lab.page.locator("#bench-preview").inner_text()
    assert "Scaled from" not in text
    assert "Pasted formula" in text
    rose = lab.page.locator("#bench-preview tbody tr", has_text="Rose Oxide")
    assert rose.locator(".bench-amount").first.inner_text() == "30 uL"
    assert "mix" not in rose.inner_text()
    assert lab.page_errors == []
    assert lab.unexpected == []


def test_bad_sizes_and_missing_sources_say_what_to_fix_without_calling_the_server(lab):
    _open(lab)
    form = lab.page.locator("#bench-source-form")
    form.locator('[name="project_formula_path"]').fill("Not_A_File.md")
    form.locator('button[type="submit"]').click()
    error = lab.page.locator("#bench-source-form-error")
    error.wait_for()
    assert " ".join(error.inner_text().split()) == "No sheet yet. Choose a project formula from the search list first."
    assert form.locator('[name="project_formula_path"]').get_attribute("aria-invalid") == "true"

    _pick_file(lab)
    form.locator('[name="target_ml"]').fill("5 mL")
    form.locator('button[type="submit"]').click()
    lab.page.wait_for_function("document.querySelector('#bench-source-form-error')?.textContent.includes('Bottle sizes')")
    assert " ".join(error.inner_text().split()) == "No sheet yet. Bottle sizes are plain numbers of mL, more than 0 and at most 1000."
    assert form.locator('[name="target_ml"]').get_attribute("aria-invalid") == "true"
    assert lab.page.locator("#bench-preview-card").is_hidden()

    form.locator('[name="target_ml"]').fill("")
    form.locator('[name="source_kind"]').select_option("PASTED")
    form.locator('button[type="submit"]').click()
    lab.page.wait_for_function("document.querySelector('#bench-source-form-error')?.textContent.includes('Paste')")
    assert form.locator('[name="pasted_text"]').get_attribute("aria-invalid") == "true"
    assert not [call for call in lab.requests if "formula-source" in call[1] or "formula-text" in call[1]]
    assert lab.page_errors == []
    assert lab.unexpected == []


def test_scaling_a_pasted_formula_with_no_size_in_its_name_asks_for_one(lab):
    lab.respond("POST", "/v2/workbench/formula-text", json=dict(SOURCE, source_path=None, formula_name="Pasted formula"))
    _open(lab)
    form = lab.page.locator("#bench-source-form")
    form.locator('[name="source_kind"]').select_option("PASTED")
    form.locator('[name="pasted_text"]').fill("| Material | uL |\n|---|---|\n| Hedione | 600 |")
    form.locator('[name="target_ml"]').fill("5")
    form.locator('button[type="submit"]').click()
    error = lab.page.locator("#bench-source-form-error")
    error.wait_for()

    assert " ".join(error.inner_text().split()) == "No sheet yet. Say what size the formula is for, so it can be scaled."
    assert form.locator('[name="source_ml"]').get_attribute("aria-invalid") == "true"
    assert lab.page_errors == []
    assert lab.unexpected == []
