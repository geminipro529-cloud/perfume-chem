"""Search (Ctrl+K) across cards, saved formulas, stock and bottles, and the downloads.

Each result opens where it lives: a card in the editor or on the bench sheet, a
stock on the Stock page, a bottle in its smell log. A card, a saved formula or
the whole stock list downloads as a CSV file that a spreadsheet opens.
"""

import csv
import io
import json

import pytest

from app.services.formula_checks import FormulaChecksRequest, compute_formula_checks
from tests.integration.lab_a11y import (
    contrast_failures,
    set_theme,
    sideways_scroll,
    small_targets,
    stop_smooth_scrolling,
)

pytest.importorskip("playwright.sync_api")

SIZES = [pytest.param((1280, 900), id="desktop"), pytest.param((390, 844), id="phone")]
CARD_PATH = "studio/Rose_Framboise_R3.md"
SOURCE_PATH = "/v2/workbench/formula-source?source_path=studio%2FRose_Framboise_R3.md"
VERSIONS_PATH = "/v2/workbench/formula-versions"

LIBRARY = {"sources": [
    {"source_path": CARD_PATH, "display_name": "studio › Rose Framboise R3", "design_only": True},
    {"source_path": "Rose_Test_30mL_EDP.md", "display_name": "Rose Test 30mL EDP", "design_only": True},
    {"source_path": "studio/Vetiver_Mineral_R4.md", "display_name": "studio › Vetiver Mineral R4", "design_only": True},
]}


def _stock(stock_id, name, fraction, basis, carrier=None, **extra):
    return {"stock_id": stock_id, "material": name, "identity_name": name, "stock_label": name,
            "fraction_decimal": fraction, "fraction_percent_decimal": str(round(float(fraction) * 100, 6)).rstrip("0").rstrip("."),
            "fraction_basis": basis, "carrier": carrier, "status": "owned", "design_ready": True, "missing_fields": [], **extra}


INVENTORY = {
    "counts": {},
    "baskets": [{"number": 10, "name": "Rose"}],
    "stocks": [
        _stock("s-ro", "Rose Oxide", "0.1", "mass_fraction", "dpg", basket=10, basket_status="confirmed"),
        _stock("s-rdm", "Rose de Mai Absolute", "0.1", "unknown", None, design_ready=False,
               missing_fields=["carrier", "fraction_basis"], source_class="PERSONAL_ADDITION"),
        _stock("s-hed", "Hedione", "1", "neat"),
        _stock("s-jav", "Javanol", "1", "neat"),
        _stock("s-jav20", "Javanol", "0.2", "mass_fraction", "dpg", source_class="PREPARED_DILUTION"),
    ],
}
BOTTLES = [{"id": "b1", "label": "Rose Framboise R3 bottle 1", "status": "active"}]
SAVED = {"formulas": [{"formula_id": "f1", "name": "Rose Framboise R3.1", "latest": 2,
                       "updated_at": "2026-10-15T10:00:00+00:00", "versions": []}]}


def _row(material, amount, fraction, basis, unit="uL", role=None):
    return {"row_id": material, "material": material, "amount_decimal": amount, "amount_unit": unit,
            "concentration_fraction_decimal": fraction, "concentration_basis": basis, "basket": None,
            "role": role, "operation": "MASS_ADD" if unit == "mg" else "DIRECT_ADD"}


SOURCE = {
    "schema_version": "workbench-formula-source-v1",
    "source_path": CARD_PATH,
    "formula_name": "Rose Framboise R3",
    "rows": [
        _row("Hedione", "600", "1", "NEAT", role="heart"),
        _row("Rose Oxide", "30", "0.1", "W_W", role="top"),
        _row("กุหลาบ accord", "370", None, "UNKNOWN"),
        _row("Ambrox", "120", "1", "NEAT", "mg", role="base"),
    ],
    "warnings": [],
    "separate_totals": {"liquid_total_ul": "1000", "mass_total_mg": "120"},
}
SCENT = {"schema_version": "scent-curve-v1", "windows": [
    {"label": label, "effective_voices": 1, "top": ["Hedione"],
     "materials": [{"name": "Hedione", "known": True, "oav": 10.0, "share": 1.0, "note": "heart"}]}
    for label in ("opening", "top", "heart", "late_heart", "drydown")
]}


def _open(lab, size=(1280, 900), *, library=LIBRARY, saved=SAVED, hash_="#improve"):
    lab.page.set_viewport_size({"width": size[0], "height": size[1]})
    lab.respond("GET", "/v2/workbench/formula-library", json=library)
    lab.respond("GET", "/v2/workbench/current-inventory", json=INVENTORY)
    lab.respond("GET", "/bottles", json=BOTTLES)
    if saved is not None:
        lab.respond("GET", VERSIONS_PATH, json=saved)
    lab.open(hash_)
    stop_smooth_scrolling(lab.page)


def _editor_answers(lab):
    def formula_checks(route, request):
        answer = compute_formula_checks(FormulaChecksRequest.model_validate(json.loads(request.post_data)))
        route.fulfill(status=200, content_type="application/json", body=json.dumps(answer))

    def densities(route, request):
        names = json.loads(request.post_data)["names"]
        body = {"densities": {name: None for name in names}, "inventory_modified": False, "compounding_authority": False}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

    lab.on("POST", "/v2/workbench/formula-checks", formula_checks)
    lab.on("POST", "/v2/workbench/material-densities", densities)
    lab.respond("POST", "/v2/workbench/scent-curve", json=SCENT)
    lab.respond("GET", SOURCE_PATH, json=SOURCE)


def _search(lab, text):
    page = lab.page
    page.keyboard.press("Control+k")
    page.locator("#lab-search[open]").wait_for()
    page.fill("#lab-search-input", text)


def _status(lab):
    return lab.page.locator("#lab-search-status").inner_text()


def _headings(lab):
    return lab.page.locator("#lab-search .lab-search-group h3").all_inner_texts()


def _names(lab):
    return lab.page.locator("#lab-search .lab-search-name").all_inner_texts()


def _csv(download):
    data = open(download.path(), "rb").read()
    assert data.startswith(b"\xef\xbb\xbf"), "Excel needs the UTF-8 byte order mark to show Thai"
    return list(csv.reader(io.StringIO(data.decode("utf-8-sig"), newline="")))


@pytest.mark.parametrize("size", SIZES)
def test_ctrl_k_finds_cards_saved_formulas_stock_and_bottles_by_part_of_a_name(lab, size):
    _open(lab, size)
    page = lab.page
    _search(lab, "rose")
    assert page.evaluate("document.activeElement.id") == "lab-search-input"
    page.wait_for_function("document.querySelector('#lab-search-status').textContent.startsWith('2 cards, 1 saved formula')")
    assert _status(lab) == "2 cards, 1 saved formula, 2 stocks and 1 bottle match."
    assert _headings(lab) == ["CARDS", "SAVED FORMULAS", "STOCK", "BOTTLES"]
    assert _names(lab) == ["studio › Rose Framboise R3", "Rose Test 30mL EDP", "Rose Framboise R3.1",
                           "Rose de Mai Absolute", "Rose Oxide", "Rose Framboise R3 bottle 1"]
    # Each stock says its strength in the Stock page's words, and what a tap does.
    details = page.locator("#lab-search .lab-search-detail").all_inner_texts()
    assert details[2] == "Saved here, version 2 · Open in the editor"
    assert details[4] == "10% w/w in DPG · Show on the Stock page"
    # Two words in any order, a part of a word, and accents all find it.
    page.fill("#lab-search-input", "frambo rôse")
    assert _names(lab)[:2] == ["studio › Rose Framboise R3", "Rose Framboise R3.1"]
    page.fill("#lab-search-input", "javanol")
    assert page.locator("#lab-search .lab-search-detail").all_inner_texts() == [
        "Neat · Show on the Stock page", "20% w/w in DPG · Show on the Stock page"]
    page.fill("#lab-search-input", "zzz")
    assert _status(lab) == "Nothing matches. Try fewer letters, or another part of the name."

    page.fill("#lab-search-input", "rose")
    assert sideways_scroll(page) == 0
    box = page.locator("#lab-search").bounding_box()
    assert box["x"] >= 15 and box["x"] + box["width"] <= size[0] - 15
    if size[0] < 760:
        assert small_targets(page, "#lab-search", minimum=44) == []
        assert page.locator("#lab-search-open").bounding_box()["height"] >= 44
    for theme in ("light", "dark"):
        set_theme(page, theme)
        failures = contrast_failures(page, "#lab-search")
        assert failures == [], (theme, failures[:4])
    set_theme(page, "light")

    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('#lab-search').open")
    assert lab.unexpected == []


def test_the_search_button_and_slash_open_it_and_escape_gives_the_focus_back(lab):
    _open(lab, (390, 844))
    page = lab.page
    page.click("#lab-search-open")
    page.locator("#lab-search[open]").wait_for()
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('#lab-search').open")
    assert page.evaluate("document.activeElement.id") == "lab-search-open"

    # Ctrl+K with the Thai keyboard layout on: the K key types "า".
    page.evaluate("""document.activeElement.dispatchEvent(new KeyboardEvent("keydown",
        { key: "า", code: "KeyK", ctrlKey: true, bubbles: true, cancelable: true }))""")
    page.locator("#lab-search[open]").wait_for()
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('#lab-search').open")

    # "/" opens it from anywhere but a field; typed into a field it stays a slash.
    page.evaluate("document.activeElement.blur()")
    page.keyboard.press("/")
    page.locator("#lab-search[open]").wait_for()
    assert page.input_value("#lab-search-input") == ""
    page.keyboard.press("Escape")
    page.click(".nav-item[data-view='materials']")
    page.focus("#project-inventory-search")
    page.keyboard.type("10/")
    assert page.input_value("#project-inventory-search") == "10/"
    assert not page.evaluate("document.querySelector('#lab-search').open")


def test_enter_opens_the_best_card_in_the_editor(lab):
    _editor_answers(lab)
    _open(lab)
    page = lab.page
    _search(lab, "framboise r3")
    page.keyboard.press("Enter")
    page.wait_for_function("document.querySelectorAll('#editor-rows tr[data-key]').length === 4")
    assert page.locator('[data-panel="editor"]').is_visible()
    assert not page.evaluate("document.querySelector('#lab-search').open")
    assert page.input_value("#editor-name") == "Rose Framboise R3"
    assert page.input_value('#editor-source-form [name="project_formula_path"]') == CARD_PATH
    # The keyboard lands on the first row, ready to edit.
    assert page.evaluate("document.activeElement.closest('#editor-rows') !== null")


def test_arrow_keys_move_through_results_and_a_stock_opens_on_the_stock_page_with_its_row_focused(lab):
    _open(lab)
    page = lab.page
    page.click(".nav-item[data-view='materials']")
    page.click("[data-stock-filter='ready']")
    assert page.locator('tr[data-stock-id="s-rdm"]').count() == 0
    _search(lab, "rose")
    page.keyboard.press("ArrowDown")
    assert page.evaluate("document.activeElement.textContent").startswith("studio › Rose Framboise R3")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    assert page.evaluate("document.activeElement.textContent").startswith("Rose de Mai Absolute")
    page.keyboard.press("ArrowUp")
    assert page.evaluate("document.activeElement.textContent").startswith("Rose Framboise R3.1")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")

    row = page.locator('tr[data-stock-id="s-rdm"]')
    row.wait_for()
    assert page.locator('[data-panel="materials"]').is_visible()
    assert page.input_value("#project-inventory-search") == "Rose de Mai Absolute"
    assert page.get_attribute("[data-stock-filter='all']", "aria-pressed") == "true"
    assert "is-found" in row.get_attribute("class")
    assert page.evaluate("document.activeElement.dataset.stockId") == "s-rdm"
    # Showing a stock opens nothing on its own.
    assert page.locator("#inventory-completion-panel").is_hidden()


def test_a_bottle_opens_its_smell_log(lab):
    from tests.integration.test_smell_log_ui_browser import CALIBRATION, COMPARISON, LOG

    lab.respond("GET", "/bottles/b1/smell-log", json=LOG)
    lab.respond("GET", "/smell-log/calibration", json=CALIBRATION)
    lab.respond("GET", "/bottles/b1/smell-log/comparison", json=COMPARISON)
    _open(lab)
    page = lab.page
    _search(lab, "bottle 1")
    assert _names(lab) == ["Rose Framboise R3 bottle 1"]
    page.keyboard.press("Enter")
    page.locator(".smell-log-form").wait_for()
    assert page.locator('[data-panel="bottles"]').is_visible()
    assert page.input_value("#smell-log-bottle") == "b1"
    assert page.evaluate("document.activeElement.id") == "smell-log-bottle"
    assert ("GET", "/bottles/b1/smell-log") in lab.requests


def test_a_card_downloads_from_its_result_as_a_spreadsheet_and_the_box_stays_open(lab):
    lab.respond("GET", SOURCE_PATH, json=SOURCE)
    _open(lab)
    page = lab.page
    _search(lab, "framboise")
    with page.expect_download() as info:
        page.click('#lab-search button[aria-label="Download: studio › Rose Framboise R3"]')
    download = info.value
    assert download.suggested_filename == "Rose Framboise R3.csv"
    assert _csv(download) == [
        ["Material", "Strength", "Amount", "Unit", "% of the liquid", "Note"],
        ["Hedione", "neat", "600", "µL", "60", "heart"],
        ["Rose Oxide", "10% w/w", "30", "µL", "3", "top"],
        ["กุหลาบ accord", "", "370", "µL", "37", ""],
        ["Ambrox", "neat", "120", "mg", "", "base"],
    ]
    assert page.evaluate("document.querySelector('#lab-search').open")
    page.wait_for_function("document.querySelector('#lab-search-status').textContent.includes('Downloaded Rose Framboise R3.csv.')")


def test_a_saved_formula_downloads_its_latest_version(lab):
    version = {"formula_id": "f1", "version": 2, "name": "Rose Framboise R3.1", "rows": [
        {"material": "Hedione", "stock_id": "s-hed", "fraction": "1", "basis": "neat", "carrier": None,
         "solid": False, "amount": "750", "note": "heart"},
        {"material": "Rose Oxide", "stock_id": "s-ro", "fraction": "0.1", "basis": "mass_fraction", "carrier": "dpg",
         "solid": False, "amount": "250", "note": "top"},
    ]}
    lab.respond("GET", f"{VERSIONS_PATH}/f1/2", json=version)
    _open(lab)
    page = lab.page
    _search(lab, "r3.1")
    with page.expect_download() as info:
        page.click('#lab-search button[aria-label="Download: Rose Framboise R3.1"]')
    download = info.value
    assert download.suggested_filename == "Rose Framboise R3.1 v2.csv"
    assert _csv(download) == [
        ["Material", "Strength", "Amount", "Unit", "% of the liquid", "Note"],
        ["Hedione", "neat", "750", "µL", "75", "heart"],
        ["Rose Oxide", "10% w/w in DPG", "250", "µL", "25", "top"],
    ]


def test_a_card_opens_on_the_bench_sheet_from_its_result(lab):
    lab.respond("GET", SOURCE_PATH, json=SOURCE)
    _open(lab)
    page = lab.page
    _search(lab, "framboise")
    page.click('#lab-search button[aria-label="Bench sheet: studio › Rose Framboise R3"]')
    page.locator("#bench-preview .bench-sheet-table").wait_for()
    assert page.locator('[data-panel="benchsheet"]').is_visible()
    assert page.input_value('#bench-source-form [name="project_formula_path"]') == CARD_PATH


def test_saved_formulas_that_cannot_be_read_are_said_and_the_rest_still_shows(lab):
    lab.respond("GET", VERSIONS_PATH, status=500, json={"error": {"code": "BROKEN", "message": "The saved formula log is damaged."}})
    _open(lab, saved=None)
    page = lab.page
    _search(lab, "rose")
    page.wait_for_function("document.querySelector('#lab-search-status').textContent.includes('could not be read')")
    assert "Your saved formulas could not be read: The saved formula log is damaged." in _status(lab)
    assert _headings(lab) == ["CARDS", "STOCK", "BOTTLES"]


def test_a_long_list_says_how_many_more_match(lab):
    library = {"sources": [{"source_path": f"Rose_{n:02}.md", "display_name": f"Rose {n:02}"} for n in range(1, 13)]}
    _open(lab, library=library)
    _search(lab, "rose")
    assert _headings(lab)[0] == "CARDS · 8 OF 12"
    assert lab.page.locator("#lab-search .lab-search-group").first.inner_text().endswith("Type more of the name to see the other 4.")


def test_the_stock_page_downloads_every_stock_whatever_the_filter(lab):
    prices = {"prices": {"s-ro": {"stock_id": "s-ro", "per_unit": "g", "price_decimal": "12.5", "currency": "THB"}},
              "cost_item_units": {}}
    lab.respond("GET", "/v2/workbench/stock-prices", json=prices)
    _open(lab, hash_="#materials")
    page = lab.page
    page.click("[data-stock-filter='needs']")
    with page.expect_download() as info:
        page.click("#inventory-download")
    download = info.value
    assert download.suggested_filename.startswith("Stock list 20") and download.suggested_filename.endswith(".csv")
    rows = _csv(download)
    assert rows[0] == ["Material", "Stock", "Strength %", "Carrier", "Form", "Category", "Status", "What is missing",
                       "Basket", "Price", "Note"]
    assert [row[0] for row in rows[1:]] == ["Hedione", "Javanol", "Javanol", "Rose de Mai Absolute", "Rose Oxide"]
    by_name = {(row[0], row[1]): row for row in rows[1:]}
    assert by_name[("Rose Oxide", "10% w/w in DPG")][6:] == ["Ready", "", "10 · Rose", "12.5 THB per g", ""]
    assert by_name[("Rose de Mai Absolute", "10%, w/w or v/v not stated")][6:] == [
        "Needs details", "Say which solvent it is in. Say whether the strength is w/w or v/v", "", "", "Added by you"]
    assert by_name[("Javanol", "20% w/w in DPG")][10] == "Your dilution"
    assert "Downloaded Stock list" in page.locator("#status").inner_text()
    assert "all 5 stocks" in page.locator("#status").inner_text()


def test_the_editor_downloads_its_rows_as_a_spreadsheet(lab):
    _editor_answers(lab)
    _open(lab, hash_="#editor")
    page = lab.page
    page.select_option('#editor-source-form [name="source_kind"]', "PROJECT_FILE")
    page.fill('#editor-source-form [name="project_formula_path"]', CARD_PATH)
    page.click("#editor-source-form button[type=submit]")
    page.wait_for_function("document.querySelectorAll('#editor-rows tr[data-key]').length === 4")
    # The unit on screen does not change the file: it keeps µL and mg, as the formula does.
    page.select_option("#editor-unit", "pct")
    with page.expect_download() as info:
        page.click("#editor-download")
    download = info.value
    assert download.suggested_filename == "Rose Framboise R3.csv"
    rows = _csv(download)
    assert rows[0] == ["Material", "Strength", "Amount", "Unit", "% of the liquid", "Note"]
    assert rows[1] == ["Hedione", "neat", "600", "µL", "60", "heart"]
    assert rows[3][0] == "กุหลาบ accord" and rows[3][2:5] == ["370", "µL", "37"]
    assert rows[4][:4] == ["Ambrox", "neat", "120", "mg"]
    page.wait_for_function("document.querySelector('#status').textContent.startsWith('Downloaded Rose Framboise R3.csv')")
