"""Phone bench mode in a real browser at phone size: weigh a recorded batch line
by line, in grams, keep going when the Wi-Fi drops, switch to Thai, and send
what was kept once the PC answers again. The later tests answer the batch
routes with the app's own route functions over a throwaway record log, so the
phone and the PC's table save the same batch the way they do at the bench."""

import json

import pytest
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import lab_batches as routes
from app.services import batch_production as batches

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
    "actuals_version": 0,
}
BUILT_ON = {"based_on": 0, "batch_recorded_at": RECORD["recorded_at"]}


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
    assert sent == [{"actuals": [{"line": 1, "weighed_g": "10.31", "density_g_ml": "0.998"}], "notes": "", **BUILT_ON}]

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
    ], "notes": "", **BUILT_ON}]
    kept = page.evaluate(f"JSON.parse(localStorage.getItem('perfumechem.bench.v1.{RECORD['lot']}'))")
    assert kept["pending"] is False


def test_amounts_kept_on_the_phone_go_to_the_pc_when_the_page_opens_again(lab):
    sent = _phone(lab)
    kept = {
        "lot": RECORD["lot"], "batch": RECORD["recorded_at"], "formula": RECORD["formula_name"], "by": "g", "notes": "", "at": 1,
        "pending": True, "savedAt": None, "error": "", "conflict": None, "base": {"entries": {}, "notes": "", "version": 0},
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

    assert sent == [{"actuals": [{"line": 1, "weighed_g": "10.2", "density_g_ml": "0.998"}], "notes": "", **BUILT_ON}]


# ---- the phone and the PC save the same batch ------------------------------------

CARD = """# Bench Test 30mL

| Ingredient | Dilution | µL | mg |
|---|---|---|---|
| Hedione | neat | 1000 | |
| Ambrox | 10% w/w in DPG | 333 | |
| Resin | 50% | | 200 |
"""


class RealPc:
    """The PC's batch routes, answered by the app's route functions over a temp log."""

    def __init__(self, lab):
        self.lab = lab
        self.posts = []
        lab.on("GET", "/v2/batches", lambda route, _request: self.answer(route, routes.list_batches()))
        lab.respond("POST", "/v2/workbench/material-densities", json={"densities": {"Hedione": "0.998"}})

    def record(self, lot, plan=None):
        plan = plan or batches.plan_batch(
            source_path=None, text=CARD, name=None, bottles="1", bottle_ml="30", card_total_ml="30", loss_percent="0"
        )
        record = batches.record_batch(lot=lot, made_on="2026-10-15", made_by="Kenny", plan=plan, gate_run_id=None, notes="")
        self.serve(lot)
        return record

    def serve(self, lot):
        self.lab.on("GET", f"/v2/batches/{lot}", lambda route, _request: self.answer(route, routes.get_batch(lot)))

        def actuals(route, request):
            body = json.loads(request.post_data)
            self.posts.append(body)
            self.answer(route, routes.record_actuals(lot, routes.BatchActualsRequest(**body)))

        self.lab.on("POST", f"/v2/batches/{lot}/actuals", actuals)

    @staticmethod
    def answer(route, result):
        if isinstance(result, JSONResponse):
            route.fulfill(status=result.status_code, content_type="application/json", body=bytes(result.body))
        else:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(result))


@pytest.fixture
def pc(lab, tmp_path, monkeypatch):
    monkeypatch.setenv(batches.BATCH_RECORD_PATH_ENV, str(tmp_path / "batch_records.jsonl"))
    monkeypatch.setenv(batches.BATCH_DIR_ENV, str(tmp_path / "batches"))
    lab.page.set_viewport_size(PHONE)
    return RealPc(lab)


def _open_on_the_phone(lab):
    lab.page.locator("#phone-bench-root .phone-bench-open").first.click()
    sheet = lab.page.get_by_role("dialog")
    sheet.wait_for()
    return sheet


def _wait_for_sync(page, words):
    page.wait_for_function("(words) => document.querySelector('.phone-bench-sync').textContent.startsWith(words)", arg=words)


def _saved(lot):
    return [(row["line"], row["actual_amount"]) for row in batches.get_record(lot)["actuals"]]


def test_lines_the_pc_saved_after_the_phone_last_opened_the_batch_are_kept(lab, pc):
    record = pc.record("KS-A")
    lab.open("#batch")
    sheet = _open_on_the_phone(lab)
    # The page behind the full-screen view is out of reach of the keyboard; the bar is named.
    behind = "[...document.body.children].filter((element) => !element.classList.contains('phone-bench'))"
    assert lab.page.evaluate(f"{behind}.every((element) => element.inert)")
    assert sheet.get_by_role("progressbar", name="Lines weighed").is_visible()
    sheet.get_by_role("button", name="Close").click()
    assert lab.page.evaluate(f"{behind}.every((element) => !element.inert)")

    # The PC's table saves lines 2 and 3, with a note, while the phone is put down.
    batches.record_actuals(
        "KS-A", [{"line": 2, "actual_amount": "330"}, {"line": 3, "actual_amount": "201"}], "from the PC",
        based_on=0, batch_recorded_at=record["recorded_at"],
    )

    sheet = _open_on_the_phone(lab)
    assert sheet.locator(".phone-bench-where").inner_text() == "Line 1 of 3"
    sheet.locator(".phone-bench-input").fill("1.0")
    sheet.locator(".phone-bench-input").press("Enter")
    _wait_for_sync(lab.page, "On the PC, saved at")

    # 1.0 g of Hedione at 0.998 g/mL is 1002 µL; the PC's lines and note stay.
    assert _saved("KS-A") == [(1, "1002"), (2, "330"), (3, "201")]
    assert batches.get_record("KS-A")["actual_notes"] == "from the PC"
    assert pc.posts[-1]["based_on"] == 1
    assert sheet.locator("#phone-bench-done-title").inner_text() == "Every line is weighed"


def test_amounts_kept_through_a_wifi_drop_merge_with_lines_the_pc_saved_meanwhile(lab, pc):
    record = pc.record("KS-B")
    lab.open("#batch")
    sheet = _open_on_the_phone(lab)
    sheet.get_by_role("button", name="As planned").click()
    _wait_for_sync(lab.page, "On the PC, saved at")

    lab.fail("POST", "/v2/batches/KS-B/actuals")
    sheet.get_by_role("button", name="As planned").click()
    _wait_for_sync(lab.page, "No connection to the PC.")

    # Meanwhile the PC's table (loaded after the phone's first send) saves line 3.
    batches.record_actuals(
        "KS-B", [{"line": 1, "actual_amount": "1000"}, {"line": 3, "actual_amount": "201"}], "",
        based_on=1, batch_recorded_at=record["recorded_at"],
    )

    pc.serve("KS-B")
    lab.page.evaluate("window.dispatchEvent(new Event('online'))")
    _wait_for_sync(lab.page, "On the PC, saved at")

    # The phone's send built on the older set is refused, merged, and sent again.
    assert [post["based_on"] for post in pc.posts] == [0, 1, 2]
    assert _saved("KS-B") == [(1, "1000"), (2, "333"), (3, "201")]
    # Line 1 was sent back unchanged by the PC, so it keeps the grams weighed on the phone.
    assert batches.get_record("KS-B")["actuals"][0]["weighed_g"] == "0.998"


@pytest.mark.parametrize(("choice", "line_1"), [("Keep this phone's", "1012"), ("Use the PC's", "990")])
def test_a_line_changed_on_both_waits_for_a_choice(lab, pc, choice, line_1):
    record = pc.record("KS-C")
    lab.fail("POST", "/v2/batches/KS-C/actuals")
    lab.open("#batch")
    sheet = _open_on_the_phone(lab)
    sheet.locator(".phone-bench-input").fill("1.01")
    sheet.locator(".phone-bench-input").press("Enter")
    _wait_for_sync(lab.page, "No connection to the PC.")

    # The PC's table saves a different amount for line 1.
    batches.record_actuals("KS-C", [{"line": 1, "actual_amount": "990"}], "", based_on=0, batch_recorded_at=record["recorded_at"])

    pc.serve("KS-C")
    lab.page.evaluate("window.dispatchEvent(new Event('online'))")
    _wait_for_sync(lab.page, "The PC also changed line 1 since this phone last sent.")
    conflict = sheet.locator(".phone-bench-summary-line.is-conflict")
    assert conflict.count() == 1
    assert "PC: 990 µL" in conflict.inner_text() and "1.01 g" in conflict.inner_text()
    assert not sheet.get_by_role("button", name="Send now").is_visible()
    assert _saved("KS-C") == [(1, "990")]

    sends = len(pc.posts)
    sheet.get_by_role("button", name=choice).click()
    _wait_for_sync(lab.page, "On the PC, saved at")

    assert _saved("KS-C") == [(1, line_1)]
    if choice == "Use the PC's":
        assert len(pc.posts) == sends
        assert "990 µL" in sheet.locator(".phone-bench-summary-line").first.inner_text()
    else:
        assert pc.posts[-1]["based_on"] == 1


def test_notes_typed_after_the_last_send_still_reach_the_pc(lab, pc):
    pc.record("KS-D")
    lab.open("#batch")
    sheet = _open_on_the_phone(lab)
    for _ in range(3):
        sheet.get_by_role("button", name="As planned").click()
    _wait_for_sync(lab.page, "On the PC, saved at")
    sheet.locator("#phone-bench-done-title").wait_for()

    sheet.locator("#phone-bench-notes").fill("smells right")
    # Kept as not sent yet at once, so a page closed now still sends it next time.
    assert lab.page.evaluate("JSON.parse(localStorage.getItem('perfumechem.bench.v1.KS-D')).pending") is True
    lab.page.wait_for_function("JSON.parse(localStorage.getItem('perfumechem.bench.v1.KS-D')).pending === false")

    assert batches.get_record("KS-D")["actual_notes"] == "smells right"


def test_amounts_kept_for_an_earlier_batch_with_the_same_lot_are_not_sent(lab, pc):
    pc.record("KS-E")
    earlier = {
        "lot": "KS-E", "batch": "2026-10-01T09:00:00+00:00", "formula": "Older card", "by": "g", "notes": "", "at": 1,
        "pending": True, "savedAt": None, "error": "", "conflict": None, "base": {"entries": {}, "notes": "", "version": 0},
        "steps": [{"line": 1, "material": "Iso E Super", "strength": "neat", "unit": "µL", "planned": "500", "grams": None, "density": None}],
        "entries": {"1": {"line": 1, "typed": "480", "unit": "µL", "planned": "500", "density": None}},
    }
    lab.page.add_init_script(f"localStorage.setItem('perfumechem.bench.v1.KS-E', {json.dumps(json.dumps(earlier))})")
    lab.open("#batch")

    # Sent when the page opens: the PC refuses it, and it is not tried again.
    lab.page.wait_for_function("JSON.parse(localStorage.getItem('perfumechem.bench.v1.KS-E')).error !== ''")
    lab.page.evaluate("window.dispatchEvent(new Event('online'))")
    assert [post["batch_recorded_at"] for post in pc.posts] == ["2026-10-01T09:00:00+00:00"]
    assert _saved("KS-E") == []

    # Opening the lot shows the PC's batch; the earlier amounts are set aside.
    sheet = _open_on_the_phone(lab)
    assert sheet.locator(".phone-bench-notice").inner_text() == (
        "Amounts kept on this phone for an earlier batch with lot KS-E were set aside and not sent."
    )
    assert sheet.locator("#phone-bench-material").inner_text() == "Hedione"
    aside = lab.page.evaluate("JSON.parse(localStorage.getItem('perfumechem.bench.aside.v1.KS-E.2026-10-01T09:00:00+00:00'))")
    assert aside["entries"]["1"]["typed"] == "480"
    assert len(pc.posts) == 1


def test_a_send_that_lands_after_the_lot_was_reopened_keeps_what_was_weighed_since(lab, pc):
    pc.record("KS-F")
    held = []
    lab.on("POST", "/v2/batches/KS-F/actuals", lambda route, request: held.append((route, request)))
    lab.open("#batch")
    sheet = _open_on_the_phone(lab)
    sheet.get_by_role("button", name="As planned").click()
    lab.page.wait_for_function("document.querySelector('.phone-bench-sync').textContent.startsWith('Sending')")

    # Closed and reopened while line 1 is still on its way, then line 2 weighed.
    sheet.get_by_role("button", name="Close").click()
    sheet = _open_on_the_phone(lab)
    assert sheet.locator(".phone-bench-where").inner_text() == "Line 2 of 3"
    sheet.get_by_role("button", name="As planned").click()
    assert len(held) == 1

    pc.serve("KS-F")
    route, request = held[0]
    body = json.loads(request.post_data)
    pc.posts.append(body)
    pc.answer(route, routes.record_actuals("KS-F", routes.BatchActualsRequest(**body)))
    _wait_for_sync(lab.page, "On the PC, saved at")

    assert _saved("KS-F") == [(1, "1000"), (2, "333")]
    kept = lab.page.evaluate("JSON.parse(localStorage.getItem('perfumechem.bench.v1.KS-F'))")
    assert sorted(kept["entries"]) == ["1", "2"] and kept["pending"] is False


def test_the_lot_tapped_last_is_the_one_shown(lab, pc):
    pc.record("KS-G1")
    pc.record("KS-G2")
    held = []
    lab.on("GET", "/v2/batches/KS-G1", lambda route, request: held.append(route))
    lab.open("#batch")
    batch = lambda lot: lab.page.locator("#phone-bench-root .phone-bench-batch", has_text=lot)  # noqa: E731
    batch("KS-G1").locator(".phone-bench-open").click()
    batch("KS-G2").locator(".phone-bench-open").click()
    sheet = lab.page.get_by_role("dialog")
    sheet.wait_for()
    assert sheet.locator(".phone-bench-lot").inner_text().startswith("KS-G2")

    pc.answer(held[0], routes.get_batch("KS-G1"))
    lab.page.wait_for_function("document.querySelector('.phone-bench-lot').textContent.length > 0")
    lab.page.evaluate("new Promise((resolve) => setTimeout(resolve, 300))")
    assert sheet.locator(".phone-bench-lot").inner_text().startswith("KS-G2")


def test_the_pc_table_keeps_lines_the_phone_saved_after_it_was_filled_in(lab, pc):
    from tests.integration.test_batch_ui_browser import LIBRARY, PLAN

    lab.page.set_viewport_size({"width": 1280, "height": 900})
    lab.respond("GET", "/v2/workbench/formula-library", json=LIBRARY)
    lab.respond("GET", "/v2/workbench/stock-prices", json={"prices": {}})
    lab.respond("POST", "/v2/batches/plan", json=PLAN)

    def record(route, request):
        body = json.loads(request.post_data)
        pc.answer(route, pc.record(body["lot"], plan=PLAN))

    lab.on("POST", "/v2/batches", record)
    lab.open("#batch")
    page = lab.page
    form = page.locator("#batch-root .batch-plan-form")
    form.locator('[name="source_path"]').fill("demo/Demo_Cedar_30mL.md")
    form.get_by_role("button", name="Plan the batch").click()
    page.locator('#batch-root [name="lot"]').fill("KS-P")
    page.get_by_role("button", name="Save batch record").click()
    actuals = page.locator("#batch-root .batch-actuals-form")
    actuals.wait_for()
    recorded = batches.get_record("KS-P")

    # The phone saves lines 1 and 2 while the PC's table is still open.
    batches.record_actuals(
        "KS-P", [{"line": 1, "actual_amount": "2055"}, {"line": 2, "actual_amount": "410"}], "",
        based_on=0, batch_recorded_at=recorded["recorded_at"],
    )

    box = lambda line: actuals.get_by_label(f"Weighed, line {line}")  # noqa: E731
    box(2).fill("415")
    box(3).fill("3100")
    actuals.get_by_role("button", name="Save weighed amounts").click()
    status = actuals.locator(".batch-status")
    page.wait_for_function(
        "() => document.querySelector('#batch-root .batch-actuals-form .batch-status').textContent.startsWith('Another device')"
    )

    # Nothing was saved over the phone's lines; the table now shows them, with the boxes typed here kept.
    assert _saved("KS-P") == [(1, "2055"), (2, "410")]
    assert [box(line).input_value() for line in (1, 2, 3)] == ["2055", "415", "3100"]
    assert "line 2 (the other device saved 410)" in status.inner_text()

    actuals.get_by_role("button", name="Save weighed amounts").click()
    page.wait_for_function(
        "() => document.querySelector('#batch-root .batch-actuals-form .batch-status').textContent.startsWith('Saved 3')"
    )
    assert _saved("KS-P") == [(1, "2055"), (2, "415"), (3, "3100")]
