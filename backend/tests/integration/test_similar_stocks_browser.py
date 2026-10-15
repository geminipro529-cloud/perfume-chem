"""Similar you own at phone size: in Edit a formula a swap is previewed before it is made,
What can I make offers it beside a stock that runs short, and the Stock page draws the
shelf map. The page's requests are read with the endpoint's own request model."""

import json

import pytest

from app.api.v1.endpoints.lab_similar import SimilarStocksRequest
from tests.integration.lab_a11y import (
    contrast_failures,
    set_theme,
    sideways_scroll,
    small_targets,
    stop_smooth_scrolling,
)
from tests.integration.test_formula_editor_browser import INVENTORY, _open, _versions
from tests.integration.test_formula_editor_why_browser import _start

pytest.importorskip("playwright.sync_api")

EVIL = "<img src=x onerror=alert(1)>"
LIKE_ISO = {
    "schema_version": "similar-stocks-v1",
    "stock": {"stock_id": "s-iso", "identity_name": "Iso E Super", "stock_label": "Iso E Super neat", "note": "base",
              "profile_from_category": False},
    "same_material": [],
    "similar": [
        {"identity_name": "Hedione", "note": "heart", "shares": ["radiant", "transparent"], "differs": ["less woody", "more floral"],
         "closeness": "some", "profile_from_category": False, "stocks": [{"stock_id": "s-hed", "stock_label": "Hedione neat", "design_ready": True}]},
        {"identity_name": "Ambrox", "note": "base", "shares": ["warm", "transparent"], "differs": [], "closeness": "some",
         "profile_from_category": False, "stocks": [{"stock_id": "s-amb", "stock_label": "Ambrox crystals", "design_ready": True}]},
        {"identity_name": EVIL, "note": "base", "shares": [], "differs": [], "closeness": "some", "profile_from_category": True,
         "stocks": [{"stock_id": "s-evil", "stock_label": EVIL, "design_ready": False}]},
    ],
    "label": "similar, not the same",
    "basis": "Compared by the character scores and odor words written for each stock, not by smell. A swap still needs your nose.",
    "no_profile": False, "inventory_modified": False, "formula_modified": False,
}


def _similar(lab, asked):
    def answer(route, request):
        asked.append(SimilarStocksRequest.model_validate(json.loads(request.post_data)).model_dump())
        route.fulfill(status=200, content_type="application/json", body=json.dumps(LIKE_ISO))

    lab.on("POST", "/v2/workbench/similar-stocks", answer)


def test_similar_you_own_previews_a_swap_that_keeps_the_material_then_uses_or_keeps_it(lab):
    asked = []
    _start(lab)
    _similar(lab, asked)
    page = lab.page
    page.click("#editor-why")
    page.wait_for_function("document.querySelector('#editor-why-line').textContent.startsWith('The name asks for')")

    page.click("#editor-rows tr:nth-child(3) [data-action=similar]")
    drop = page.locator("#editor-drop")
    drop.locator(".similar-items").wait_for()
    assert asked == [{"stock_id": "s-iso", "material": "Iso E Super", "limit": 6}]
    assert drop.locator("h3").inner_text() == "Like Iso E Super"
    assert drop.locator("h4").first.inner_text() == "Similar, not the same"
    items = drop.locator(".similar-item")
    assert items.nth(0).locator(".similar-line").inner_text() == "Both radiant and transparent; less woody, more floral."
    # Only a liquid stock on the Stock page list can stand in for a poured row.
    assert items.nth(1).locator(".similar-stock").inner_text() == "Ambrox · Neat crystals, weighed in mg: a solid; this row is poured"
    assert items.nth(2).locator("strong").inner_text() == EVIL  # text, never markup
    assert page.locator("#editor-drop img").count() == 0
    assert items.nth(2).locator(".similar-stock").inner_text() == f"{EVIL}: not on your Stock page list"
    assert sideways_scroll(page) == 0
    assert small_targets(page, "#editor-drop") == []
    for theme in ("light", "dark"):
        set_theme(page, theme)
        assert contrast_failures(page, "#editor-drop") == [], theme
    set_theme(page, "light")

    drop.get_by_role("button", name="Preview Hedione · Neat").click()
    drop.locator("[data-drop=use]").wait_for()
    assert drop.locator("h3").inner_text() == "Iso E Super → Hedione"
    # 370 µL x 0.9612 g/mL of Iso E Super is 355.644 g/L; Hedione neat at 0.999 g/mL: 356 µL.
    assert drop.locator("p").nth(0).inner_text() == "370 µL of Iso E Super neat becomes 356 µL of Hedione neat: the same grams of material."
    assert drop.locator("p").nth(1).inner_text().startswith("Similar, not the same: Hedione will not smell the same and may not be as strong")
    smell = drop.locator("ul").nth(1).locator("li").all_inner_texts()
    assert any(line.startswith("With the swap, Hedione would be") for line in smell), smell
    assert small_targets(page, "#editor-drop") == []

    # Back to the list, then use it: one step, and Undo puts Iso E Super back.
    drop.locator("[data-drop=similar]").click()
    drop.get_by_role("button", name="Preview Hedione · Neat").click()
    drop.locator("[data-drop=use]").click()
    assert page.is_hidden("#editor-drop")
    assert page.input_value("#editor-rows tr:nth-child(3) [data-field=material]") == "Hedione · Neat"
    assert page.input_value("#editor-rows tr:nth-child(3) [data-field=amount]") == "356"
    page.click("#editor-undo")
    assert page.input_value("#editor-rows tr:nth-child(3) [data-field=material]") == "Iso E Super · Neat"
    assert page.input_value("#editor-rows tr:nth-child(3) [data-field=amount]") == "370"


def test_a_short_stock_on_what_can_i_make_lists_what_you_own_like_it_and_opens_the_swap(lab, monkeypatch, tmp_path):
    from app.services import formula_versions as versions

    asked = []
    _open(lab)
    _versions(lab, monkeypatch, tmp_path, [])
    rows = [{"material": "Hedione", "stock_id": "s-hed", "fraction": "1", "basis": "neat", "amount": "600"},
            {"material": "Iso E Super", "stock_id": "s-iso", "fraction": "1", "basis": "neat", "amount": "370"}]
    saved, _created = versions.save_version(versions.FormulaVersionSave.model_validate(
        {"name": "Iso Test", "bottle_ml": "30", "rows": rows, "card_text": "| Hedione | 600 |"}))
    on_hand = {"s-hed": {"stock_id": "s-hed", "amount_decimal": "50", "unit": "mL", "supplier": "", "note": "", "recorded_at": "x"},
               "s-iso": {"stock_id": "s-iso", "amount_decimal": "0.1", "unit": "mL", "supplier": "", "note": "", "recorded_at": "x"}}
    lab.respond("GET", "/v2/workbench/make-now", json={"formulas": [
        {key: saved[key] for key in ("formula_id", "version", "name", "bottle_ml", "saved_at", "rows")}], "on_hand": on_hand})
    lab.respond("GET", "/v2/workbench/current-inventory", json=INVENTORY)
    _similar(lab, asked)
    page = lab.page
    page.click('nav [data-view="make"]')
    card = page.locator(".make-card").first
    card.wait_for()
    card.get_by_role("button", name="Each stock").click()
    short = card.locator('.make-row[data-status="short"]')
    assert short.locator("span").first.inner_text() == "Iso E Super: needs 0.37 mL; 0.1 mL left, short by 0.27 mL."
    assert card.locator('.make-row[data-status="enough"] [aria-label^="Similar you own"]').count() == 0

    toggle = short.get_by_role("button", name="Similar you own to Iso E Super")
    toggle.click()
    short.locator(".similar-items").wait_for()
    assert toggle.get_attribute("aria-expanded") == "true"
    assert asked == [{"stock_id": "s-iso", "material": "Iso E Super", "limit": 4}]
    # Named here, not offered: the swap is previewed in Edit a formula.
    assert short.locator(".similar-pick").count() == 0
    assert short.locator(".similar-item strong").first.inner_text() == "Hedione"
    assert sideways_scroll(page) == 0
    assert small_targets(page, '[data-panel="make"]') == []
    for theme in ("light", "dark"):
        set_theme(page, theme)
        assert contrast_failures(page, '[data-panel="make"]') == [], theme
    set_theme(page, "light")

    short.get_by_role("button", name="See a swap in Edit a formula").click()
    page.locator("#editor-drop .similar-items").wait_for()
    assert page.locator("#editor-drop h3").inner_text() == "Like Iso E Super"
    assert page.input_value("#editor-name") == "Iso Test"
    assert asked[-1] == {"stock_id": "s-iso", "material": "Iso E Super", "limit": 6}
    assert page.get_by_role("button", name="Preview Hedione · Neat").is_visible()


def test_the_shelf_map_draws_each_material_as_a_named_dot_and_lists_thin_facets_and_pairs_written_alike(lab):
    answer = {
        "schema_version": "shelf-map-v1",
        "stocks": [
            {"identity_name": "Iso E Super", "note": "base", "x": 0.2, "y": 0.8, "leads_with": "woody", "leads_with_word": "woody",
             "profile_from_category": False, "stocks": [{"stock_id": "s-iso", "stock_label": "Iso E Super neat", "design_ready": True}]},
            {"identity_name": EVIL, "note": "heart", "x": 0.9, "y": 0.1, "leads_with": "", "leads_with_word": "",
             "profile_from_category": True, "stocks": []},
        ],
        "axes": {"x": {"low": "warm", "high": "fresh"}, "y": {"low": "woody", "high": "floral"}},
        "unplaced": ["Mystery Base"],
        "written_alike": [{"a": "Hedione", "b": "Hedione HC", "shares": ["floral", "fresh"]}],
        "facets": [{"facet": "woody", "word": "woody", "leaders": ["Iso E Super"] * 6, "count": 6},
                   {"facet": "powdery", "word": "powdery", "leaders": ["Orris Liquid"], "count": 1}],
        "label": "similar, not the same", "basis": "Placed by the character scores written for each stock, not by smell.",
        "inventory_modified": False,
    }
    lab.respond("GET", "/v2/workbench/shelf-map", json=answer)
    lab.page.set_viewport_size({"width": 390, "height": 844})
    lab.open("#materials")
    stop_smooth_scrolling(lab.page)
    page = lab.page
    assert "GET" not in {method for method, path in lab.requests if path == "/v2/workbench/shelf-map"}  # asked on a tap only

    toggle = page.locator("#shelf-map-toggle")
    toggle.click()
    page.locator("#shelf-map svg").wait_for()
    assert toggle.get_attribute("aria-expanded") == "true"
    assert toggle.inner_text() == "Hide the shelf map"
    titles = page.eval_on_selector_all("#shelf-map circle title", "(nodes) => nodes.map((node) => node.textContent)")
    assert titles == ["Iso E Super, leads with woody", EVIL]
    assert page.locator("#shelf-map img").count() == 0
    assert page.get_attribute("#shelf-map svg", "role") == "img"
    assert page.locator("#shelf-map .shelf-axes").inner_text() == (
        "Left to right: more warm to more fresh. Bottom to top: more woody to more floral.")
    page.get_by_label("Find a material on the map").fill("iso e super")
    assert page.locator("#shelf-map .shelf-found").inner_text() == "Iso E Super is the ringed dot; it leads with woody."
    assert page.locator("#shelf-map circle.is-found").count() == 1
    lists = page.locator("#shelf-map .shelf-list")
    assert lists.nth(0).locator("li").all_inner_texts() == ["powdery: only Orris Liquid."]
    alike = page.locator("#shelf-map details").nth(0)
    assert alike.locator("summary").inner_text() == "Written almost alike (1)"
    assert lists.nth(1).is_hidden()
    alike.locator("summary").click()
    assert lists.nth(1).locator("li").all_inner_texts() == ["Hedione and Hedione HC: both floral and fresh."]
    page.locator("#shelf-map details").nth(1).locator("summary").click()
    assert page.locator("#shelf-map .shelf-unplaced").inner_text() == "Mystery Base."
    assert sideways_scroll(page) == 0
    assert small_targets(page, ".shelf-map-panel") == []
    for theme in ("light", "dark"):
        set_theme(page, theme)
        assert contrast_failures(page, ".shelf-map-panel") == [], theme
    set_theme(page, "light")

    toggle.click()
    assert page.is_hidden("#shelf-map") and toggle.get_attribute("aria-expanded") == "false"
