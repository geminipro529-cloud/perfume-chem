"""What's missing at phone size: a Create several card that holds lists what each stock or
IFRA check lacks, opens that stock on the Stock page, and the studio and the editor offer
the same list. The page's request is read with the endpoint's own request model.
"""

import json

import pytest

from app.api.v1.endpoints.lab_holds import FormulaHoldsRequest
from tests.integration.lab_a11y import contrast_failures, set_theme, sideways_scroll, small_targets, stop_smooth_scrolling
from tests.integration.test_formula_editor_browser import _load_card
from tests.integration.test_formula_editor_browser import _open as _open_editor

pytest.importorskip("playwright.sync_api")

EVIL = "<img src=x onerror=alert(1)>"
BRIEF = "A sweet pipe tobacco"
INVENTORY = {
    "stocks": [
        {"stock_id": "stock-tonka", "identity_name": "Tonka Bean Absolute", "material": "Tonka Bean Absolute",
         "fraction_percent_decimal": "10", "fraction_basis": "mass_fraction", "carrier": "DPG", "design_ready": False,
         "missing_fields": ["homogeneity_confirmation"], "design_hold_reason": None, "completion_available": True},
        {"stock_id": "stock-hedione", "identity_name": "Hedione", "material": "Hedione", "fraction_percent_decimal": "100",
         "fraction_basis": "neat", "carrier": None, "design_ready": True, "missing_fields": [], "design_hold_reason": None,
         "completion_available": False},
    ],
    "counts": {"stocks": 2, "design_ready": 1},
}


def _row(material, stock_id, amount, fraction="1", basis="neat", carrier=None):
    return {
        "material": material, "identity_name": material, "stock_id": stock_id, "amount_decimal": amount, "amount_unit": "uL",
        "stock_label": material, "stock_fraction_decimal": fraction, "fraction_basis": basis, "carrier": carrier,
        "operation": "DIRECT_ADD", "execution_ready": True, "slot_label": "slot", "role": "role", "note": "heart", "rationale": "why",
    }


ROWS = [_row("Tonka Bean Absolute", "stock-tonka", "400", "0.1", "mass_fraction", "DPG"), _row("Hedione", "stock-hedione", "1500")]
DESIGN = {
    "formula_name": "Tabac Doux",
    "assistant_message": "Tabac Doux draft.",
    "design_variants": [{
        "variant_id": "First", "label": "First", "critic": {"state": "PASS", "issues": []},
        "formula": {"rows": ROWS, "separate_totals": {"liquid_total_ul": "1900", "mass_total_mg": "0"}},
    }],
    "critic": {"state": "PASS", "issues": []},
    "scorecards": [{"variant_id": "First", "floors": {
        "F1_owned_stock": {"status": "HOLD", "detail": "Stock: 1 stock is not confirmed for mixing."},
        "F2_ifra": {"status": "PASS", "detail": "IFRA: within the limits."},
    }}],
}
ANSWER = {
    "schema_version": "formula-holds-v1",
    "summary": "1 stock to sort out on the Stock page or the bench and 1 material IFRA cannot fully check yet. Each says what to do.",
    "basis": "From the release gate's stock and IFRA checks on this formula as written. It says what data is missing, not how the formula smells.",
    "items": [
        {"id": "hold-1", "material": "Tonka Bean Absolute", "check": "stock", "code": "inventory_stock_non_executable",
         "reason": "Its details are not complete: confirm the solution is fully mixed.",
         "action": "Open it on the Stock page and fill those in.", "open": {"kind": "stock_page", "stock_id": "stock-tonka"}},
        {"id": "hold-2", "material": EVIL, "check": "ifra", "code": "ifra_natural_composition_unknown",
         "reason": "The Lab has no make-up for this natural, so IFRA-restricted substances inside it are not counted.",
         "action": "Ask the supplier for its IFRA certificate and send it to Claude.", "open": None},
    ],
    "inventory_modified": False,
    "formula_modified": False,
}


def _open_card(lab):
    asked = []

    def holds(route, request):
        asked.append(FormulaHoldsRequest.model_validate(json.loads(request.post_data)).model_dump())
        route.fulfill(status=200, content_type="application/json", body=json.dumps(ANSWER))

    def submit(route, _request):
        route.fulfill(status=202, content_type="application/json", body=json.dumps({"id": "job-1", "state": "QUEUED"}))

    lab.on("POST", "/v2/workbench/formula-holds", holds)
    lab.on("POST", "/v2/engine-jobs", submit)
    lab.respond("GET", "/v2/engine-jobs/job-1", json={
        "id": "job-1", "state": "SUCCEEDED", "timeout_seconds": 300, "events": [],
        "result": {"result": {"result": {"formula_design": DESIGN}}},
    })
    lab.respond("GET", "/v2/workbench/current-inventory", json=INVENTORY)
    lab.page.route("**/api/v1/feedback/**", lambda route, _request: route.fulfill(
        status=200, content_type="application/json", body=json.dumps({"ratings_used": 0, "picks_used": 0})))
    lab.page.set_viewport_size({"width": 390, "height": 844})
    lab.open("#formulas")
    stop_smooth_scrolling(lab.page)
    lab.page.fill('#several-form textarea[name="briefs"]', BRIEF)
    lab.page.click("#several-submit")
    lab.page.locator("#several-status", has_text="Composed 1 perfume").wait_for()
    return lab.page.locator(".several-card", has_text=BRIEF), asked


def test_a_holding_card_lists_whats_missing_and_opens_the_stock_on_the_stock_page(lab):
    card, asked = _open_card(lab)
    page = lab.page
    toggle = card.get_by_role("button", name="What's missing")

    assert asked == []  # nothing is asked until the tap
    toggle.click()
    card.locator(".hold-item").first.wait_for()

    assert toggle.get_attribute("aria-expanded") == "true"
    assert asked == [{"rows": [
        {"material": "Tonka Bean Absolute", "stock_id": "stock-tonka", "amount": "400", "unit": "uL", "fraction": "0.1",
         "basis": "mass_fraction", "carrier": "DPG"},
        {"material": "Hedione", "stock_id": "stock-hedione", "amount": "1500", "unit": "uL", "fraction": "1", "basis": "neat", "carrier": ""},
    ], "bottle_ml": 30.0}]
    assert card.locator(".hold-list-summary").inner_text().startswith("1 stock to sort out")
    items = card.locator(".hold-item")
    assert items.nth(1).locator("strong").inner_text() == EVIL  # shown as text, never as markup
    assert card.locator(".hold-list img").count() == 0
    assert items.nth(0).get_by_role("button", name="Open on the Stock page").count() == 1
    assert items.nth(1).get_by_role("button").count() == 0

    assert sideways_scroll(page) == 0
    assert small_targets(page, ".several-card") == []
    for theme in ("light", "dark"):
        set_theme(page, theme)
        assert contrast_failures(page, ".several-card .hold-list") == [], theme
    set_theme(page, "light")

    # Closing and opening again does not ask twice for the same formula.
    toggle.click()
    assert card.locator(".hold-list").is_hidden()
    toggle.click()
    card.locator(".hold-item").first.wait_for()
    assert len(asked) == 1

    items.nth(0).get_by_role("button", name="Open on the Stock page").click()
    assert page.locator('[data-panel="materials"]').is_visible()
    assert page.locator("#inventory-completion-panel").is_visible()
    assert page.locator("#inventory-completion-name").inner_text() == "Tonka Bean Absolute"
    assert page.locator("#project-inventory-search").input_value() == "Tonka Bean Absolute"
    assert page.locator("#project-inventory-list tbody tr strong").all_inner_texts() == ["Tonka Bean Absolute"]
    assert lab.requests.count(("POST", "/v2/workbench/formula-holds")) == 1


def test_the_studio_offers_the_same_list_for_the_formula_it_shows(lab):
    card, asked = _open_card(lab)
    lab.respond("POST", "/v2/workbench/scent-curve", json={"schema_version": "scent-curve-v1", "windows": []})
    card.get_by_role("button", name="Open in the studio").click()
    page = lab.page
    toggle = page.locator("#formula-holds-toggle")

    assert toggle.is_visible() and page.locator("#formula-holds").is_hidden()
    toggle.click()
    page.locator("#formula-holds .hold-item").first.wait_for()
    assert [row["material"] for row in asked[0]["rows"]] == ["Tonka Bean Absolute", "Hedione"]
    assert page.locator("#formula-holds .hold-list-basis").inner_text().endswith("not how the formula smells.")
    assert small_targets(page, "#formula-chat-result") == []
    for theme in ("light", "dark"):
        set_theme(page, theme)
        assert contrast_failures(page, "#formula-holds") == [], theme
    set_theme(page, "light")


def test_the_editor_sends_its_bound_rows_and_bottle_and_a_failed_check_says_so(lab):
    asked = []

    def holds(route, request):
        asked.append(FormulaHoldsRequest.model_validate(json.loads(request.post_data)).model_dump())
        route.fulfill(status=503, content_type="application/json", body=json.dumps({"detail": "The engine is busy."}))

    lab.page.set_viewport_size({"width": 390, "height": 844})
    _open_editor(lab)
    lab.on("POST", "/v2/workbench/formula-holds", holds)
    stop_smooth_scrolling(lab.page)
    page = lab.page
    assert page.locator("#editor-holds-bar").is_hidden()
    _load_card(lab)
    page.locator("#editor-holds-toggle").wait_for()

    assert asked == []
    page.click("#editor-holds-toggle")
    problem = page.locator("#editor-holds .hold-list-summary.is-problem")
    problem.wait_for()
    assert problem.inner_text().startswith("Could not check what is missing:")
    (body,) = asked
    assert body["bottle_ml"] == 30.0
    hedione = next(row for row in body["rows"] if row["material"] == "Hedione")
    assert (hedione["stock_id"], hedione["unit"], hedione["fraction"]) == ("s-hed", "uL", "1")
    assert small_targets(page, "#editor-side") == []
    assert sideways_scroll(page) == 0
