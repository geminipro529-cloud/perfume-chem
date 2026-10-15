"""Phone bench mode in a real browser at phone size: weigh a recorded batch line
by line, in grams, keep going when the Wi-Fi drops, switch to Thai, and send
what was kept once the PC answers again."""

import json

import pytest

pytest.importorskip("playwright.sync_api")

PHONE = {"width": 390, "height": 844}
RECORD = {
    "schema_version": "user-batch-record-v1",
    "lot": "KS-20261015-01",
    "made_on": "2026-10-15",
    "made_by": "Kenny",
    "recorded_at": "2026-10-15T09:00:00+00:00",
    "formula_name": "Demo Cedar 30mL",
    "bottles": "10",
    "bottle_ml": "30",
    "planned_rows": [
        {"line": 1, "material": "Hedione", "strength": "neat", "concentration_fraction_decimal": None,
         "concentration_basis": "NEAT", "unit": "uL", "card_amount": "1000", "planned_amount": "10290"},
        {"line": 2, "material": "Resin <b>", "strength": "50%", "concentration_fraction_decimal": "0.5",
         "concentration_basis": "W_W", "unit": "mg", "card_amount": "20", "planned_amount": "206"},
        {"line": 3, "material": "Damascone", "strength": "1%", "concentration_fraction_decimal": "0.01",
         "concentration_basis": "UNKNOWN", "unit": "uL", "card_amount": "1", "planned_amount": "10"},
    ],
    "actuals": [],
    "actuals_recorded_at": None,
}


def _phone(lab):
    lab.page.set_viewport_size(PHONE)
    lab.respond("GET", "/v2/batches", json={"schema_version": "batch-records-v1", "records": [RECORD]})
    lab.respond("GET", f"/v2/batches/{RECORD['lot']}", json=RECORD)
    lab.respond("POST", "/v2/workbench/material-densities", json={"densities": {"Hedione": "0.998"}})
    sent = []

    def actuals(route, request):
        body = json.loads(request.post_data)
        sent.append(body)
        route.fulfill(status=200, content_type="application/json", body=json.dumps({**RECORD, "actuals": body["actuals"]}))

    lab.on("POST", f"/v2/batches/{RECORD['lot']}/actuals", actuals)
    return sent


def _fits_the_phone(page):
    width = page.evaluate("document.documentElement.scrollWidth")
    sheet = page.evaluate("(() => { const s = document.querySelector('.phone-bench'); return [s.scrollWidth, s.clientWidth]; })()")
    assert width <= PHONE["width"]
    assert sheet[0] <= sheet[1]


def test_weigh_a_batch_on_the_phone_through_a_wifi_drop_and_in_thai(lab):
    sent = _phone(lab)
    lab.open("#batch")
    page = lab.page
    panel = page.locator("#phone-bench-root")
    assert panel.get_by_text("KS-20261015-01").is_visible()
    assert "0 of 3 weighed" in panel.inner_text()
    panel.get_by_role("button", name="Weigh step by step").click()

    sheet = page.get_by_role("dialog")
    sheet.wait_for()
    assert sheet.locator(".phone-bench-where").inner_text() == "Line 1 of 3"
    assert sheet.locator("#phone-bench-material").inner_text() == "Hedione"
    # 10290 µL of neat Hedione at 0.998 g/mL, on the balance.
    assert sheet.locator(".phone-bench-amount").inner_text() == "10.269 g"
    assert "0.998 g/mL" in sheet.locator(".phone-bench-density").inner_text()
    _fits_the_phone(page)

    entry = sheet.locator(".phone-bench-input")
    assert entry.evaluate("(element) => element === document.activeElement")
    entry.fill("10,31")
    assert sheet.locator(".phone-bench-check").inner_text() == "0.4% over the plan"
    entry.press("Enter")
    page.wait_for_function("document.querySelector('.phone-bench-sync').textContent.startsWith('On the PC, saved at')")
    assert sent == [{"actuals": [{"line": 1, "weighed_g": "10.31", "density_g_ml": "0.998"}], "notes": ""}]

    # Line 2 is a solid in mg, read in grams; the name stays text.
    assert sheet.locator("#phone-bench-material").inner_text() == "Resin <b>"
    assert sheet.locator(".phone-bench-amount").inner_text() == "0.206 g"

    # The Wi-Fi drops: the line is kept on the phone and the next one comes up.
    lab.fail("POST", f"/v2/batches/{RECORD['lot']}/actuals")
    sheet.get_by_role("button", name="As planned").click()
    page.wait_for_function("document.querySelector('.phone-bench-sync').textContent.startsWith('No connection to the PC. 2 kept')")
    kept = page.evaluate(f"JSON.parse(localStorage.getItem('perfumechem.bench.v1.{RECORD['lot']}'))")
    assert kept["pending"] is True and sorted(kept["entries"]) == ["1", "2"]

    # Thai labels; line 3 is under 0.1 g, so it stays in µL for the pipette.
    sheet.get_by_role("button", name="Thai").click()
    assert sheet.locator(".phone-bench-where").inner_text() == "รายการที่ 3 จาก 3"
    assert sheet.locator(".phone-bench-amount").inner_text() == "10 µL"
    assert sheet.locator(".phone-bench-label").inner_text() == "ตวงได้"
    assert sheet.get_by_role("button", name="ตามสูตร").is_visible()
    _fits_the_phone(page)
    sheet.locator(".phone-bench-input").fill("11")
    assert sheet.locator(".phone-bench-check").inner_text() == "เกินสูตร 10%"
    sheet.get_by_role("button", name="บันทึก ไปต่อ").click()
    assert sheet.locator("#phone-bench-done-title").inner_text() == "ชั่งครบทุกรายการแล้ว"

    # The PC answers again: everything kept goes in one request.
    resent = _phone(lab)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    page.wait_for_function("document.querySelector('.phone-bench-sync').textContent.startsWith('บันทึกลงคอมพิวเตอร์แล้ว')")
    assert resent == [{"actuals": [
        {"line": 1, "weighed_g": "10.31", "density_g_ml": "0.998"},
        {"line": 2, "weighed_g": "0.206"},
        {"line": 3, "actual_amount": "11"},
    ], "notes": ""}]
    kept = page.evaluate(f"JSON.parse(localStorage.getItem('perfumechem.bench.v1.{RECORD['lot']}'))")
    assert kept["pending"] is False


def test_amounts_kept_on_the_phone_go_to_the_pc_when_the_page_opens_again(lab):
    sent = _phone(lab)
    kept = {
        "lot": RECORD["lot"], "formula": RECORD["formula_name"], "by": "g", "notes": "", "at": 1, "pending": True,
        "savedAt": None, "error": "",
        "steps": [{"line": 1, "material": "Hedione", "strength": "neat", "unit": "µL", "planned": "10290", "grams": "10.269", "density": "0.998"}],
        "entries": {"1": {"line": 1, "typed": "10.2", "unit": "g", "planned": "10.269", "density": "0.998"}},
    }
    lab.page.add_init_script(
        f"localStorage.setItem('perfumechem.bench.v1.{RECORD['lot']}', {json.dumps(json.dumps(kept))})"
    )
    lab.open("#improve")
    lab.page.wait_for_function(
        f"JSON.parse(localStorage.getItem('perfumechem.bench.v1.{RECORD['lot']}')).pending === false"
    )

    assert sent == [{"actuals": [{"line": 1, "weighed_g": "10.2", "density_g_ml": "0.998"}], "notes": ""}]
