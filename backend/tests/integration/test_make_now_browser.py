"""What can I make at phone size: each saved formula against what is left, how much is left
asked only for stocks on the shopping list, and the list grouped by supplier with prices.
The page's save is read with the endpoint's own request model."""

import json

import pytest

from app.api.v1.endpoints.lab_make_now import StockOnHandCreate
from tests.integration.lab_a11y import contrast_failures, set_theme, sideways_scroll, small_targets, stop_smooth_scrolling

pytest.importorskip("playwright.sync_api")

EVIL = "<img src=x onerror=alert(1)>"


def _stock(stock_id, name, percent="100", basis="neat", carrier=None):
    return {"stock_id": stock_id, "identity_name": name, "material": name, "fraction_percent_decimal": percent,
            "fraction_basis": basis, "carrier": carrier, "design_ready": True, "missing_fields": [], "completion_available": False}


INVENTORY = {"stocks": [_stock("s-hed", "Hedione"), _stock("s-iso", "Iso E Super"), _stock("s-amb", "Ambrox")],
             "counts": {"stocks": 3, "design_ready": 3}}
FORMULAS = [
    {"formula_id": "a" * 32, "version": 3, "name": EVIL, "bottle_ml": "30", "saved_at": "2026-10-14T10:00:00Z", "rows": [
        {"material": "Hedione", "stock_id": "s-hed", "fraction": "1", "basis": "neat", "amount": "1500"},
        {"material": "Iso E Super", "stock_id": "s-iso", "fraction": "1", "basis": "neat", "amount": "3000"},
        {"material": "Ethanol", "stock_id": None, "fraction": "1", "basis": "", "amount": "24000"},
    ]},
    {"formula_id": "b" * 32, "version": 1, "name": "Ambre Simple", "bottle_ml": "30", "saved_at": "2026-10-13T10:00:00Z", "rows": [
        {"material": "Ambrox", "stock_id": "s-amb", "fraction": "1", "basis": "neat", "amount": "200", "solid": True},
    ]},
]
PRICES = {"schema_version": "workbench-stock-prices-v1", "cost_item_units": {"ethanol": "mL", "packaging_per_bottle": "bottle"},
          "prices": {"s-iso": {"stock_id": "s-iso", "price_decimal": "8", "per_unit": "mL", "currency": "THB",
                               "pack_price": None, "pack_size": None, "note": "", "recorded_at": "2026-10-13T00:00:00Z"}},
          "inventory_modified": False, "compounding_authority": False}


def _open(lab):
    on_hand = {"s-hed": {"stock_id": "s-hed", "amount_decimal": "20", "unit": "mL", "supplier": "", "note": "", "recorded_at": "x"},
               "s-amb": {"stock_id": "s-amb", "amount_decimal": "5", "unit": "g", "supplier": "", "note": "", "recorded_at": "x"}}
    saved = []

    def save(route, request):
        body = StockOnHandCreate.model_validate(json.loads(request.post_data))
        saved.append(body.model_dump())
        on_hand[body.stock_id] = {"stock_id": body.stock_id, "amount_decimal": body.amount_decimal, "unit": body.unit,
                                  "supplier": body.supplier, "note": "", "recorded_at": "y"}
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"on_hand": on_hand}))

    lab.respond("GET", "/v2/workbench/current-inventory", json=INVENTORY)
    lab.respond("GET", "/v2/workbench/stock-prices", json=PRICES)
    lab.on("GET", "/v2/workbench/make-now", lambda route, _request: route.fulfill(
        status=200, content_type="application/json", body=json.dumps({"formulas": FORMULAS, "on_hand": on_hand})))
    lab.on("POST", "/v2/workbench/stock-on-hand", save)
    lab.page.set_viewport_size({"width": 390, "height": 844})
    lab.open("#make")
    stop_smooth_scrolling(lab.page)
    lab.page.locator(".make-card").nth(1).wait_for()
    return saved


def test_each_formula_says_whether_it_can_be_mixed_and_the_shopping_list_asks_only_what_it_needs(lab):
    saved = _open(lab)
    page = lab.page
    cards = page.locator(".make-card")

    assert cards.nth(0).locator("h3").inner_text() == EVIL  # text, never markup
    assert page.locator(".make-card img").count() == 0
    assert cards.nth(0).locator(".make-verdict").inner_text() == "Type how much is left of 1 stock to know."
    assert cards.nth(1).locator(".make-verdict").inner_text() == "You can mix it at 30 mL."
    assert page.locator("#make-status").inner_text().startswith("2 saved formulas at 30 mL: 1 you can mix now, 0 short, 1 waiting")
    assert page.locator("#make-shopping").inner_text().startswith("Add formulas to the shopping list")
    assert page.locator(".make-left-form:visible").count() == 0  # nothing is asked until a list or a card needs it

    cards.nth(0).get_by_role("button", name="Add to shopping list").click()
    ask = page.locator("#make-shopping .make-ask")
    assert ask.locator(".make-row").all_inner_texts()[0].startswith("Iso E Super: needs 3 mL.")
    form = ask.locator(".make-left-form")
    form.get_by_label("mL left").fill("1.5")
    form.get_by_label("Bought from").fill("PerfumersWorld")
    form.get_by_role("button", name="Save").click()
    page.locator("#make-shopping .make-group").first.wait_for()

    assert saved == [{"stock_id": "s-iso", "amount_decimal": "1.5", "unit": "mL", "supplier": "PerfumersWorld", "note": "", "clear": False}]
    group = page.locator("#make-shopping .make-group").first
    assert group.locator("h3").inner_text() == "PerfumersWorld"
    assert group.locator(".make-row").inner_text() == "Iso E Super: 1.5 mL, 12.00 THB"
    assert page.locator("#make-shopping .make-total").inner_text() == "Total with your prices: 12.00 THB."
    assert cards.nth(0).locator(".make-verdict").inner_text() == "Short of 1 stock for 30 mL."

    assert sideways_scroll(page) == 0
    assert small_targets(page, '[data-panel="make"]') == []
    for theme in ("light", "dark"):
        set_theme(page, theme)
        assert contrast_failures(page, '[data-panel="make"]') == [], theme
    set_theme(page, "light")


def test_each_stock_line_opens_on_a_tap_and_a_bigger_bottle_rescales(lab):
    _open(lab)
    page = lab.page
    card = page.locator(".make-card").nth(1)
    toggle = card.get_by_role("button", name="Each stock")

    assert card.locator(".make-rows").is_hidden()
    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "true"
    assert card.locator(".make-row").inner_text() == "Ambrox: needs 0.2 g; 5 g left."

    page.fill("#make-bottle-ml", "1000")
    page.locator("#make-bottle-ml").dispatch_event("change")
    assert card.locator(".make-row > span").inner_text() == "Ambrox: needs 6.67 g; 5 g left, short by 1.67 g."
    # A stock that runs short offers what you own like it (tests/integration/test_similar_stocks_browser.py).
    assert card.locator(".make-row").get_by_role("button", name="Similar you own to Ambrox").is_visible()
    assert card.locator(".make-verdict").inner_text() == "Short of 1 stock for 1000 mL."
