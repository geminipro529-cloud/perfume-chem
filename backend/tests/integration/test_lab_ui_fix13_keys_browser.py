"""Keyboard and status behaviour of the Lab page: first Tab, tab switches, and the basket picker keys."""

import json

import pytest

pytest.importorskip("playwright.sync_api")

from tests.integration.test_lab_ui_basket_stock_browser import (  # noqa: E402
    BASKET_PATH,
    _basket_text,
    _capture_post,
    _clean,
    _open,
    _rows,
)

STATUS = "#status"


def test_first_tab_reaches_the_skip_link(lab):
    lab.open("")
    lab.page.keyboard.press("Tab")
    assert "skip-link" in lab.page.evaluate("document.activeElement.className")
    _clean(lab)


def test_switching_views_still_focuses_the_heading(lab):
    lab.open("")
    lab.page.locator('.nav-item[data-view="materials"]').click()
    heading = lab.page.evaluate("""() => {
        const node = document.activeElement;
        return { tag: node.tagName, panel: node.closest('[data-panel]')?.dataset.panel };
    }""")
    assert heading == {"tag": "H1", "panel": "materials"}
    _clean(lab)


def test_switching_views_clears_the_routine_refreshed_line(lab):
    lab.open("")
    assert "refreshed" in lab.page.locator(STATUS).inner_text()
    lab.page.locator('.nav-item[data-view="materials"]').click()
    assert "refreshed" not in lab.page.locator(STATUS).inner_text()
    _clean(lab)


def test_switching_views_keeps_an_error_on_the_status_line(lab):
    lab.fail("GET", "/materials", "connectionrefused")
    lab.open("", wait_for_boot=False)
    lab.page.wait_for_function("document.getElementById('status').classList.contains('is-error')")
    message = lab.page.locator(STATUS).inner_text()
    assert message
    lab.page.locator('.nav-item[data-view="materials"]').click()
    assert lab.page.locator(STATUS).inner_text() == message
    assert "is-error" in lab.page.locator(STATUS).get_attribute("class")
    assert lab.page_errors == []


@pytest.fixture
def stock(lab):
    return _open(lab)


def _picker(lab, name="Vetiver"):
    return _rows(lab, name).locator("select")


def test_arrowing_moves_the_value_and_enter_saves_it_once(stock):
    bodies = _capture_post(stock)
    picker = _picker(stock)
    picker.focus()
    stock.page.keyboard.press("ArrowDown")
    stock.page.keyboard.press("ArrowDown")
    assert bodies == []
    assert picker.input_value() == "2"
    stock.page.keyboard.press("Enter")
    stock.wait_for_status("Basket set: Vetiver → 2 Citrus")
    assert bodies == [{"normalized_identity": "vetiver", "basket": 2}]
    _clean(stock)


def test_arrow_then_tab_away_saves_once(stock):
    bodies = _capture_post(stock)
    picker = _picker(stock)
    picker.focus()
    stock.page.keyboard.press("ArrowDown")
    assert bodies == []
    stock.page.keyboard.press("Tab")
    stock.wait_for_status("Basket set: Vetiver → 1 Always used")
    assert bodies == [{"normalized_identity": "vetiver", "basket": 1}]
    _clean(stock)


def test_escape_puts_back_the_saved_value_without_saving(stock):
    bodies = _capture_post(stock)
    picker = _picker(stock, "Cedar")
    picker.focus()
    stock.page.keyboard.press("ArrowDown")
    stock.page.keyboard.press("ArrowDown")
    assert picker.input_value() == "5"
    stock.page.keyboard.press("Escape")
    assert picker.input_value() == "3"
    stock.page.keyboard.press("Tab")
    stock.page.wait_for_timeout(200)
    assert bodies == []
    assert _basket_text(_rows(stock, "Cedar")) == "3 · Woods"
    _clean(stock)


def test_a_mouse_style_choice_still_saves_at_once(stock):
    bodies = _capture_post(stock)
    _picker(stock).select_option("4")
    stock.wait_for_status("Basket set: Vetiver → 4 Musks")
    assert bodies == [{"normalized_identity": "vetiver", "basket": 4}]
    _clean(stock)


def test_enter_on_the_saved_value_posts_nothing(stock):
    bodies = _capture_post(stock)
    picker = _picker(stock, "Cedar")
    picker.focus()
    stock.page.keyboard.press("Enter")
    stock.page.wait_for_timeout(200)
    assert bodies == []
    _clean(stock)


def test_the_one_tap_confirm_button_still_saves(stock):
    bodies = _capture_post(stock)
    _rows(stock, "Hedione").first.get_by_role("button", name="Confirm 1").click()
    stock.wait_for_status("Basket set: Hedione → 1 Always used")
    assert bodies == [{"normalized_identity": "hedione", "basket": 1}]
    _clean(stock)


def test_a_save_in_flight_still_disables_the_picker(stock):
    held = []
    stock.on("POST", BASKET_PATH, lambda route, request: held.append(route))
    _picker(stock).select_option("5")
    stock.page.wait_for_function("document.querySelectorAll('.stock-basket-select:disabled').length >= 1")
    assert len(held) == 1
    held[0].fulfill(status=200, content_type="application/json",
                    body=json.dumps({"normalized_identity": "vetiver", "basket": 5, "basket_status": "confirmed"}))
    stock.wait_for_status("Basket set: Vetiver → 5 Florals")
    _clean(stock)
