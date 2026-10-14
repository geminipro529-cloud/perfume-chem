"""The Lab's main flows at phone and desktop size, driven from the keyboard.

Compose, edit, the bench sheet with a pour fix, a batch and a smell log each run to
their result with the main action pressed from the keyboard. Then the page is
checked as it stands: no sideways scrolling, text contrast in the light and dark
themes (WCAG AA), a visible focus on every Tab stop, and on a phone, buttons and
fields at least 24 px each way. Smooth scrolling is off, so each check measures
where a scroll ends.
"""

import json

import pytest

from tests.integration.lab_a11y import (
    contrast_failures,
    set_theme,
    sideways_scroll,
    small_targets,
    stop_smooth_scrolling,
    tab_through,
    wait_until_still,
)

pytest.importorskip("playwright.sync_api")

SIZES = [pytest.param((1280, 900), id="desktop"), pytest.param((390, 844), id="phone")]
TAB_STOPS = 12


def _size(lab, size):
    lab.page.set_viewport_size({"width": size[0], "height": size[1]})


def _tab_to(lab, selector, limit=25):
    """Press Tab until ``selector`` has focus; every stop on the way must show its focus."""
    page = lab.page
    for _ in range(limit):
        if page.evaluate("(selector) => document.activeElement?.matches(selector)", selector):
            return
        stop = tab_through(page, 1)[0]
        assert stop.get("visible"), stop
    raise AssertionError(f"Tab never reached {selector}")


def _check_view(lab, panel, size, start):
    """The view as it stands after the flow: fits, reads, and shows its focus."""
    page = lab.page
    wait_until_still(page)
    assert sideways_scroll(page) == 0
    for theme in ("light", "dark"):
        set_theme(page, theme)
        failures = contrast_failures(page, "body")
        assert failures == [], (theme, json.dumps(failures[:6]), len(failures))
    set_theme(page, "light")
    if size[0] < 760:
        assert small_targets(page, panel) == []
    page.focus(start)
    hidden = [stop for stop in tab_through(page, TAB_STOPS) if not stop.get("visible")]
    assert hidden == [], json.dumps(hidden)


@pytest.mark.parametrize("size", SIZES)
def test_compose_a_formula_from_the_keyboard(lab, size):
    from tests.integration.test_lab_ui_basket_create_browser import RESULT, STOCKS, _baskets

    _size(lab, size)
    lab.respond("GET", "/v2/workbench/current-inventory", json={"stocks": STOCKS, "counts": {}, "baskets": _baskets()})
    lab.respond("POST", "/v2/workbench/formula-chat", json=RESULT)
    lab.open("#formulas")
    page = lab.page
    stop_smooth_scrolling(page)
    page.focus('#formula-chat-form textarea[name="message"]')
    page.keyboard.type("a rose and cedar test")
    _tab_to(lab, "#formula-chat-submit")
    page.keyboard.press("Enter")
    page.locator("#formula-chat-result").wait_for()
    assert page.locator("#formula-result-rows td strong").count() == 5
    _check_view(lab, '[data-panel="formulas"]', size, '#formula-chat-form textarea[name="message"]')


@pytest.mark.parametrize("size", SIZES)
def test_edit_a_formula_from_the_keyboard(lab, size):
    from tests.integration.test_formula_editor_browser import _cells, _load_card, _open

    _size(lab, size)
    _open(lab)
    page = lab.page
    stop_smooth_scrolling(page)
    _load_card(lab)
    page.focus('#editor-rows tr:nth-child(1) [data-field="amount"]')
    page.keyboard.press("Control+a")
    page.keyboard.type("650")
    page.keyboard.press("Enter")
    page.keyboard.type("45")
    page.keyboard.press("Enter")
    assert _cells(lab, "amount")[:2] == ["650", "45"]
    page.keyboard.press("Control+z")
    assert _cells(lab, "amount")[:2] == ["650", "30"]
    page.wait_for_function("document.querySelector('#editor-ifra-verdict').textContent.includes('IFRA 51')")
    _check_view(lab, '[data-panel="editor"]', size, "#editor-name")


@pytest.mark.parametrize("size", SIZES)
def test_bench_sheet_and_a_pour_fix_from_the_keyboard(lab, size):
    from tests.integration.test_lab_ui_bench_any_formula_browser import (
        SOURCE,
        SOURCE_PATH,
        _open,
        _pick_file,
    )

    _size(lab, size)
    lab.respond("GET", SOURCE_PATH, json=SOURCE)
    _open(lab)
    page = lab.page
    stop_smooth_scrolling(page)
    _pick_file(lab)
    page.focus('#bench-source-form [name="project_formula_path"]')
    _tab_to(lab, '#bench-source-form button[type="submit"]')
    page.keyboard.press("Enter")
    page.locator("#bench-preview .bench-sheet-table").wait_for()
    pour = page.locator("#bench-pour-form")
    pour.locator('[name="pour_row"]').select_option("1")
    pour.locator('[name="pour_actual"]').focus()
    page.keyboard.type("36")
    page.keyboard.press("Enter")
    page.wait_for_function("document.querySelector('#bench-preview h1').textContent.includes('still to add')")
    assert page.locator("#bench-pour-result").inner_text() == "Fixed: the sheet now shows what still goes in after Rose Oxide."
    _check_view(lab, '[data-panel="benchsheet"]', size, '#bench-source-form [name="source_kind"]')


@pytest.mark.parametrize("size", SIZES)
def test_plan_a_batch_from_the_keyboard(lab, size):
    from tests.integration.test_batch_ui_browser import LIBRARY, PLAN

    _size(lab, size)
    lab.respond("GET", "/v2/workbench/formula-library", json=LIBRARY)
    lab.respond("GET", "/v2/workbench/stock-prices", json={"prices": {}})
    sent = []

    def plan(route, request):
        sent.append(json.loads(request.post_data))
        route.fulfill(status=200, content_type="application/json", body=json.dumps(PLAN))

    lab.on("POST", "/v2/batches/plan", plan)
    lab.open("#batch")
    page = lab.page
    stop_smooth_scrolling(page)
    form = "#batch-root .batch-plan-form"
    page.focus(f'{form} [name="source_path"]')
    page.keyboard.type("demo/Demo_Cedar_30mL.md")
    _tab_to(lab, f'{form} [name="bottles"]')
    page.keyboard.press("Control+a")
    page.keyboard.type("2")
    page.keyboard.press("Enter")
    page.locator("#batch-root .batch-plan table").wait_for()
    assert sent == [{"bottles": "2", "bottle_ml": "30", "source_path": "demo/Demo_Cedar_30mL.md"}]
    _check_view(lab, '[data-panel="batch"]', size, f'{form} [name="source_kind"]')


@pytest.mark.parametrize("size", SIZES)
def test_log_a_smell_from_the_keyboard(lab, size):
    from tests.integration.test_smell_log_ui_browser import CALIBRATION, COMPARISON, LOG

    _size(lab, size)
    lab.respond("GET", "/bottles", json=[{"id": "b1", "label": "Iris trial", "status": "active"}])
    lab.respond("GET", "/bottles/b1/smell-log", json=LOG)
    lab.respond("GET", "/smell-log/calibration", json=CALIBRATION)
    lab.respond("GET", "/bottles/b1/smell-log/comparison", json=COMPARISON)
    posted = []

    def save(route, request):
        posted.append(json.loads(request.post_data))
        route.fulfill(status=201, content_type="application/json", body=json.dumps({
            "id": "o2", "window": "strip_1h", "surface": "strip", "leads": ["Orris Butter"],
            "weak": [], "liking": 8, "words": "powdery", "logged_at": "2026-10-12T11:00:00+00:00",
        }))

    lab.on("POST", "/bottles/b1/smell-log", save)
    lab.open("#bottles")
    page = lab.page
    stop_smooth_scrolling(page)
    page.select_option("#smell-log-bottle", "b1")
    form = page.locator(".smell-log-form")
    form.wait_for()
    for target in ('[data-window="strip_1h"]', '[data-row="Orris Butter"]', '[data-liking="8"]'):
        form.locator(target).focus()
        page.keyboard.press("Enter")
    form.locator('input[name="words"]').focus()
    page.keyboard.type("powdery")
    _tab_to(lab, '.smell-log-form button[type="submit"]', limit=40)
    page.keyboard.press("Enter")
    page.locator(".smell-log-form .status-line", has_text="Saved.").wait_for()
    assert posted == [{"window": "strip_1h", "leads": ["Orris Butter"], "weak": [], "liking": 8, "words": "powdery"}]
    page.locator(".smell-log-compare h3").first.wait_for()
    _check_view(lab, '[data-panel="bottles"]', size, "#smell-log-bottle")
