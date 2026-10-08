"""The Lab's Stock view shows and sets each material's basket, driven in a real browser."""

import json

import pytest

pytest.importorskip("playwright.sync_api")

INVENTORY_PATH = "/v2/workbench/current-inventory"
BASKET_PATH = "/v2/workbench/current-inventory/basket"

BASKET_NAMES = {
    1: "Always used", 2: "Citrus", 3: "Woods", 4: "Musks", 5: "Florals", 6: "Resins",
    7: "Spices", 8: "Ambers", 9: "Aldehydes", 10: "Fruits", 11: "Herbs", 12: "Leathers",
    13: "Gourmands", 14: "Marine", 15: "Powders", 16: "Solvents", 17: "Green things",
}
BASKETS = [{"number": number, "name": name} for number, name in BASKET_NAMES.items()]


def _stock(name, identity, *, percent="100", basis="neat", carrier=None,
           basket=None, status="none", suggestions=(), with_basket=True):
    row = {
        "stock_id": f"stock-{name.lower().replace(' ', '-')}-{percent}",
        "identity_name": name,
        "material": name,
        "normalized_identity": identity,
        "fraction_percent_decimal": percent,
        "fraction_basis": basis,
        "carrier": carrier,
        "design_ready": True,
        "missing_fields": [],
        "design_hold_reason": None,
        "completion_available": False,
    }
    if with_basket:
        row.update(basket=basket, basket_status=status, basket_suggestions=list(suggestions))
    return row


def _stocks(with_basket=True):
    kw = {"with_basket": with_basket}
    return [
        _stock("Ambrox", "ambrox", basket=8, status="confirmed", **kw),
        _stock("Cedar", "cedarwood", basket=3, status="confirmed", **kw),
        _stock("Hedione", "hedione", basket=1, status="from_past_cards", **kw),
        _stock("Hedione", "hedione", percent="10", basis="mass_fraction", carrier="DPG",
               basket=1, status="from_past_cards", **kw),
        _stock("Labdanum", "labdanum", status="conflicting", suggestions=[3, 6], **kw),
        _stock("Vetiver", "vetiver", **kw),
    ]


def _open(lab, *, with_basket=True):
    body = {"stocks": _stocks(with_basket), "counts": {}, "display_source": "Test inventory"}
    if with_basket:
        body["baskets"] = BASKETS
    lab.respond("GET", INVENTORY_PATH, json=body)
    lab.open("#materials")
    lab.page.locator("#project-inventory-list tbody tr").first.wait_for()
    return lab


@pytest.fixture
def stock(lab):
    return _open(lab)


def _rows(lab, name):
    return lab.page.locator("#project-inventory-list tbody tr", has=lab.page.locator("strong", has_text=name))


def _basket_text(row):
    return row.locator(".stock-basket-label").inner_text()


def _names(lab):
    return lab.page.locator("#project-inventory-list tbody tr strong").all_inner_texts()


def _capture_post(lab, *, status=200, reply=None):
    bodies = []

    def handler(route, request):
        payload = json.loads(request.post_data)
        bodies.append(payload)
        answer = reply if reply is not None else {**payload, "basket_status": "confirmed"}
        route.fulfill(status=status, content_type="application/json", body=json.dumps(answer))

    lab.on("POST", BASKET_PATH, handler)
    return bodies


def _clean(lab):
    assert lab.page_errors == []
    assert lab.unexpected == []


def test_basket_column_says_each_status_in_plain_words(stock):
    headers = stock.page.locator("#project-inventory-list thead th").all_inner_texts()
    assert "Basket" in headers
    assert _basket_text(_rows(stock, "Cedar")) == "3 · Woods"
    assert _rows(stock, "Cedar").locator(".stock-basket-check").count() == 0

    hedione = _rows(stock, "Hedione").first
    assert _basket_text(hedione) == "1 · Always used"
    assert hedione.locator(".stock-basket-check").inner_text() == "check it"
    assert hedione.get_by_role("button", name="Confirm 1").count() == 1

    labdanum = _rows(stock, "Labdanum")
    assert _basket_text(labdanum) == "3 or 6?"
    assert labdanum.locator(".stock-basket-check").inner_text() == "check it"
    assert labdanum.get_by_role("button").count() == 0

    assert _basket_text(_rows(stock, "Vetiver")) == "—"
    options = _rows(stock, "Vetiver").locator("select").locator("option").all_inner_texts()
    assert options[0] == "No basket"
    assert options[1] == "1 Always used"
    assert options[-1] == "17 Green things"
    assert len(options) == 18
    _clean(stock)


def test_confirming_a_past_card_basket_posts_it_and_updates_both_strengths(stock):
    bodies = _capture_post(stock)
    hedione = _rows(stock, "Hedione")
    assert hedione.count() == 2
    hedione.first.get_by_role("button", name="Confirm 1").click()
    stock.wait_for_status("Basket set: Hedione → 1 Always used")

    assert bodies == [{"normalized_identity": "hedione", "basket": 1}]
    assert stock.requests.count(("GET", INVENTORY_PATH)) == 1  # no reload
    for index in range(2):
        row = hedione.nth(index)
        assert _basket_text(row) == "1 · Always used"
        assert row.locator(".stock-basket-check").count() == 0
        assert row.get_by_role("button", name="Confirm 1").count() == 0
    _clean(stock)


def test_the_select_sets_a_basket(stock):
    bodies = _capture_post(stock)
    _rows(stock, "Vetiver").locator("select").select_option("17")
    stock.wait_for_status("Basket set: Vetiver → 17 Green things")

    assert bodies == [{"normalized_identity": "vetiver", "basket": 17}]
    row = _rows(stock, "Vetiver")
    assert _basket_text(row) == "17 · Green things"
    assert row.locator("select").input_value() == "17"

    _rows(stock, "Cedar").locator("select").select_option("")
    stock.wait_for_status("Basket cleared: Cedar")
    assert bodies[-1] == {"normalized_identity": "cedarwood", "basket": None}
    assert _basket_text(_rows(stock, "Cedar")) == "—"
    _clean(stock)


def test_a_refused_basket_keeps_the_old_value_and_says_why(stock):
    _capture_post(stock, status=422, reply={"detail": "That basket does not exist."})
    _rows(stock, "Cedar").locator("select").select_option("5")
    stock.wait_for_status("Basket not saved for Cedar: That basket does not exist.")

    row = _rows(stock, "Cedar")
    assert _basket_text(row) == "3 · Woods"
    assert row.locator("select").input_value() == "3"
    assert row.locator(".stock-basket-error").inner_text() == "Basket not saved: That basket does not exist."
    assert stock.page.locator("#status").get_attribute("class").split().count("is-error") == 1
    _clean(stock)


def test_basket_filter_and_sort_show_the_right_rows(stock):
    basket = stock.page.locator("#project-inventory-basket")
    assert stock.page.locator("#project-inventory-basket-filter").is_visible()
    options = basket.locator("option").all_inner_texts()
    assert options[:4] == ["All baskets", "No basket yet", "Check it", "1 Always used"]
    assert options[-1] == "17 Green things"

    basket.select_option("none")
    assert _names(stock) == ["Vetiver"]
    basket.select_option("check")
    assert sorted(_names(stock)) == ["Hedione", "Hedione", "Labdanum"]
    basket.select_option("3")
    assert _names(stock) == ["Cedar"]

    # Combined with the solvent filter: basket 1 holds both Hedione strengths, only one is neat.
    basket.select_option("1")
    assert _names(stock) == ["Hedione", "Hedione"]
    stock.page.locator("#project-inventory-solvent").select_option("neat")
    assert _rows(stock, "Hedione").count() == 1
    assert stock.page.locator("#project-inventory-live").inner_text() == "Showing 1 of 6"
    stock.page.locator("#project-inventory-solvent").select_option("")

    basket.select_option("")
    stock.page.locator("#project-inventory-sort").select_option("basket")
    assert _names(stock) == ["Hedione", "Hedione", "Cedar", "Ambrox", "Labdanum", "Vetiver"]
    stock.page.locator("#project-inventory-sort").select_option("name")
    assert _names(stock) == ["Ambrox", "Cedar", "Hedione", "Hedione", "Labdanum", "Vetiver"]
    _clean(stock)


def test_an_inventory_without_basket_fields_shows_no_basket_column(lab):
    _open(lab, with_basket=False)
    headers = lab.page.locator("#project-inventory-list thead th").all_inner_texts()
    assert "Basket" not in headers
    assert lab.page.locator(".stock-basket").count() == 0
    assert not lab.page.locator("#project-inventory-basket-filter").is_visible()
    assert lab.page.locator('#project-inventory-sort option[value="basket"]').get_attribute("hidden") is not None
    assert len(_names(lab)) == 6
    _clean(lab)
