"""The Batch view in a real browser: pick a library formula, plan 2 bottles, see the scaled rows."""

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

LIBRARY = {"sources": [{"source_path": "demo/Demo_Cedar_30mL.md", "display_name": "demo › Demo Cedar 30mL"}]}
PLAN = {
    "schema_version": "batch-plan-v1",
    "source_path": "demo/Demo_Cedar_30mL.md",
    "source_sha256": "0" * 64,
    "formula_name": "Demo Cedar 30mL",
    "card_total_ml_source": "formula name",
    "parse_warnings": [],
    "factor": "2.06",
    "bottles": "2",
    "bottle_ml": "30",
    "card_total_ml": "30",
    "loss_percent": "3",
    "finished_volume_ml": "61.8",
    "rows": [
        {"line": 1, "material": "Cedarwood <i>Atlas</i>", "strength": "10% w/w", "concentration_fraction_decimal": "0.1",
         "concentration_basis": "W_W", "unit": "uL", "card_amount": "1000", "exact_amount": "2060", "planned_amount": "2060"},
        {"line": 2, "material": "Ambroxide", "strength": "neat", "concentration_fraction_decimal": None,
         "concentration_basis": "NEAT", "unit": "uL", "card_amount": "200", "exact_amount": "412", "planned_amount": "412"},
        {"line": 3, "material": "Bergamot", "strength": "20% w/w", "concentration_fraction_decimal": "0.2",
         "concentration_basis": "W_W", "unit": "uL", "card_amount": "1500", "exact_amount": "3090", "planned_amount": "3090"},
    ],
    "totals": {"planned_ul": "5562", "planned_mg": "0", "card_ul": "2700", "card_mg": "0"},
    "units": ["uL"],
    "mixed_units": False,
    "rounding": "Scaled amounts are rounded to the nearest whole µL or whole mg.",
    "proportionality": {"strengths_unchanged": True, "largest_rounding_change_percent": "0"},
    "warnings": [],
    "inventory_modified": False,
}


def test_pick_a_library_formula_plan_two_bottles_and_see_the_scaled_rows(lab):
    lab.respond("GET", "/v2/workbench/formula-library", json=LIBRARY)
    lab.respond("GET", "/v2/workbench/stock-prices", json={"prices": {}})
    sent = []

    def plan(route, request):
        sent.append(json.loads(request.post_data))
        route.fulfill(status=200, content_type="application/json", body=json.dumps(PLAN))

    lab.on("POST", "/v2/batches/plan", plan)
    lab.open("#batch")
    page = lab.page
    assert page.locator('[data-panel="batch"]').is_visible()
    form = page.locator("#batch-root .batch-plan-form")
    form.locator('[name="source_path"]').fill("demo/Demo_Cedar_30mL.md")
    form.locator('[name="bottles"]').fill("2")
    form.get_by_role("button", name="Plan the batch").click()
    table = page.locator("#batch-root .batch-plan table")
    table.wait_for()

    assert sent == [{"bottles": "2", "bottle_ml": "30", "source_path": "demo/Demo_Cedar_30mL.md"}]
    rows = table.locator("tbody tr")
    assert rows.count() == 3
    assert rows.nth(0).locator("td").all_inner_texts() == ["1", "Cedarwood <i>Atlas</i>", "10% w/w", "1000 µL", "2060 µL"]
    summary = page.locator("#batch-root .batch-summary").inner_text()
    assert "2 × 30 mL with 3% loss allowance makes 61.8 mL" in summary
    assert "(from the formula name)" in summary
    assert page.get_by_role("button", name="Rerun the gate").is_visible()
    assert page.locator("#batch-label-area").get_by_role("button", name="Make label").is_visible()

    shots = os.environ.get("BATCH_SCREENSHOT_DIR")
    if shots:
        folder = Path(shots)
        folder.mkdir(parents=True, exist_ok=True)
        from app.services.commercial_label import build_label

        def label(route, request):
            body = json.loads(request.post_data)
            route.fulfill(status=200, content_type="application/json", body=json.dumps(build_label(body["fields"], body["rows"])))

        lab.on("POST", "/commercial-pack/label", label)
        area = page.locator("#batch-label-area")
        area.locator("[name=lot]").fill("DEMO-20261013-01")
        area.locator("[name=mfg]").fill("10/2026")
        area.get_by_role("button", name="Make label").click()
        area.locator(".batch-label-box").wait_for()
        page.set_viewport_size({"width": 1280, "height": 900})
        page.screenshot(path=str(folder / "batch-desktop-1280.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(folder / "batch-phone-390.png"), full_page=True)
