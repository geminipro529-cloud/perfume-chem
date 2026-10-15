"""Smell strips on the phone, in a real browser at phone size: dip a strip, let
the page's clock run to each check, note what leads and what is weak, keep the
notes through a Wi-Fi drop, switch to Thai, and send what was kept once the PC
answers again. The page's clock is Playwright's, so ten minutes take no time."""

import datetime as dt
import json
import re

import pytest

pytest.importorskip("playwright.sync_api")

PHONE = {"width": 390, "height": 844}
T0 = dt.datetime(2026, 10, 15, 10, 0, 0, tzinfo=dt.UTC)
BOTTLES = [
    {"id": "b1", "label": "Vetiver Mineral R4", "status": "active", "batch_id": "batch-1"},
    {"id": "b2", "label": "Iris <i>trial</i>", "status": "active", "batch_id": None},
]
LOG = {
    "windows": [
        {"key": "strip_10m", "label": "Strip 10 min", "surface": "strip", "seconds": 600},
        {"key": "strip_1h", "label": "Strip 1 h", "surface": "strip", "seconds": 3600},
        {"key": "strip_3h", "label": "Strip 3 h", "surface": "strip", "seconds": 10800},
    ],
    "rows": ["Vetiver Bourbon", "Iso E Super", "Ambrox"],
    "entries": [],
}
CALIBRATION = {"calibrated": False, "n_bottles": 3, "min_bottles": 10, "held_out": [], "factors": []}
CLIENT_ID = re.compile(r"^strip\.[a-z0-9]+\.strip_(10m|1h|3h)$")


def _iso(moment):
    return moment.isoformat().replace("+00:00", "Z")


def _phone(lab, *, rows=LOG["rows"]):
    lab.page.set_viewport_size(PHONE)
    lab.page.clock.install(time=T0)
    lab.respond("GET", "/bottles", json=BOTTLES)
    lab.respond("GET", "/bottles/b1/smell-log", json={**LOG, "rows": rows})
    lab.respond("GET", "/bottles/b2/smell-log", json={**LOG, "rows": []})
    lab.respond("GET", "/smell-log/calibration", json=CALIBRATION)
    return _pc_takes_notes(lab)


def _pc_takes_notes(lab, bottle="b1"):
    posted = []

    def save(route, request):
        body = json.loads(request.post_data)
        posted.append(body)
        route.fulfill(status=201, content_type="application/json", body=json.dumps({"id": f"obs-{len(posted)}", **body}))

    lab.on("POST", f"/bottles/{bottle}/smell-log", save)
    return posted


def _sync(page):
    return page.locator(".phone-strips-sync p").first.inner_text()


def _wait_sync(page, start):
    page.wait_for_function(
        "(start) => document.querySelector('.phone-strips-sync p').textContent.startsWith(start)", arg=start
    )


def _open_strips(lab):
    page = lab.page
    page.locator("#phone-strips-root").get_by_role("button", name="Smell strips step by step").click()
    sheet = page.get_by_role("dialog")
    sheet.wait_for()
    return sheet


def _dip(lab, sheet, label="Vetiver Mineral R4"):
    sheet.get_by_role("button", name="Dip a strip").click()
    sheet.locator(".phone-strips-bottle", has_text=label).click()
    sheet.get_by_role("button", name="Dipped now").click()


def _fits_the_phone(page):
    width = page.evaluate("document.documentElement.scrollWidth")
    sheet = page.evaluate("(() => { const s = document.querySelector('.phone-strips'); return [s.scrollWidth, s.clientWidth]; })()")
    assert width <= PHONE["width"]
    assert sheet[0] <= sheet[1]


def _checks(sheet):
    return sheet.locator(".phone-strips-check").all_inner_texts()


def _focused_in_sheet(page):
    return page.evaluate(
        "(() => { const a = document.activeElement; const s = document.querySelector('.phone-strips');"
        " return Boolean(a && s.contains(a) && !a.closest('[hidden]')); })()"
    )


def test_dip_a_strip_and_note_each_check_through_a_wifi_drop_and_in_thai(lab):
    posted = _phone(lab)
    lab.open("#bottles")
    page = lab.page
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    assert sheet.locator("#phone-strips-heading").inner_text() == "Strips you dipped"
    page.wait_for_function("document.querySelector('.phone-strips-home .phone-strips-nose').textContent !== ''")
    assert sheet.locator(".phone-strips-home .phone-strips-nose").inner_text() == (
        "Your nose: 3 of 10 bottles logged. The Lab starts learning from your nose at 10."
    )
    assert "No strip dipped yet." in sheet.inner_text()

    _dip(lab, sheet)
    assert sheet.locator("#phone-strips-heading").inner_text() == "Vetiver Mineral R4"
    assert sheet.locator(".phone-strips-next").inner_text() == "Next: the 10 min check in 10:00"
    assert sheet.locator(".phone-strips-form").is_hidden()
    _fits_the_phone(page)

    # Ten minutes on, the 10 min check opens with the bottle's recipe names.
    page.clock.run_for("10:00")
    assert sheet.locator(".phone-strips-form-title").text_content() == "Smell now: the 10 min check"
    assert sheet.locator(".phone-bench-notice[role='status']").inner_text() == "Smell now: the 10 min check"
    assert _checks(sheet)[0] == "10 min: smell it now"
    sheet.get_by_role("button", name="Vetiver Bourbon").click()
    assert _focused_in_sheet(page)
    assert page.evaluate("document.activeElement.dataset.row") == "Vetiver Bourbon"
    sheet.get_by_role("button", name="Ambrox").click()
    sheet.get_by_role("button", name="Ambrox: leads").click()
    sheet.locator(".phone-strips-liking").get_by_role("button", name="8", exact=True).click()
    sheet.get_by_label("In a few words").fill("green, dry")
    _fits_the_phone(page)
    sheet.get_by_role("button", name="Save").click()
    _wait_sync(page, "Every note is on the PC.")
    assert len(posted) == 1
    first = posted[0]
    assert CLIENT_ID.match(first.pop("client_id"))
    assert first == {
        "window": "strip_10m", "leads": ["Vetiver Bourbon"], "weak": ["Ambrox"], "liking": 8, "words": "green, dry",
        "logged_at": _iso(T0 + dt.timedelta(minutes=11)).replace("Z", ".000Z"),
    }
    assert _checks(sheet)[0] == "10 min: noted"
    assert sheet.locator(".phone-strips-form").is_hidden()
    assert _focused_in_sheet(page)

    # The Wi-Fi drops before the 1 h check: the note is kept on the phone.
    lab.fail("POST", "/bottles/b1/smell-log")
    page.clock.fast_forward("50:00")
    assert _checks(sheet)[1] == "1 h: smell it now"
    sheet.locator(".phone-strips-liking").get_by_role("button", name="7", exact=True).click()
    sheet.get_by_role("button", name="Save").click()
    _wait_sync(page, "No connection to the PC. 1 kept on this phone")
    kept = page.evaluate("JSON.parse(localStorage.getItem('perfumechem.strips.v1.outbox'))")
    assert [note["window"] for note in kept.values()] == ["strip_1h"]
    kept_id = next(iter(kept))

    # Thai labels.
    sheet.get_by_role("button", name="Thai").click()
    assert _checks(sheet)[:2] == ["10 นาที: บันทึกแล้ว", "1 ชั่วโมง: บันทึกแล้ว"]
    assert sheet.locator(".phone-strips-next").inner_text().startswith("ครั้งต่อไป: รอบ 3 ชั่วโมง อีก")
    _fits_the_phone(page)

    # The PC answers again: the kept note goes, with the id it was kept under.
    resent = _pc_takes_notes(lab)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    _wait_sync(page, "บันทึกทั้งหมดอยู่ในคอมพิวเตอร์แล้ว")
    assert [body["client_id"] for body in resent] == [kept_id]
    assert resent[0]["window"] == "strip_1h" and resent[0]["liking"] == 7
    assert page.evaluate("JSON.parse(localStorage.getItem('perfumechem.strips.v1.outbox'))") == {}

    # Nobody smells the 3 h strip in time: it is missed, and the strip is done.
    page.clock.fast_forward("03:30:00")
    assert _checks(sheet)[2] == "3 ชั่วโมง: พลาดไปแล้ว"
    assert sheet.locator(".phone-strips-next").inner_text() == "เสร็จแล้ว: ทุกรอบบันทึกแล้วหรือพลาดไปแล้ว"
    # Back to English: the button reads "English" and is named in Thai, as on the phone bench.
    sheet.get_by_role("button", name="อังกฤษ").click()
    assert _checks(sheet) == ["10 min: noted", "1 h: noted", "3 h: missed"]
    assert page.evaluate("localStorage.getItem('perfumechem.bench.lang')") == "en"


def test_a_note_whose_answer_never_came_is_sent_again_with_the_same_id(lab):
    _phone(lab)
    page = lab.page
    tries = []

    def flaky(route, request):
        tries.append(json.loads(request.post_data))
        if len(tries) == 1:
            route.fulfill(status=503, content_type="application/json", body=json.dumps({"detail": "busy"}))
        else:
            route.fulfill(status=201, content_type="application/json", body=json.dumps({"id": "obs-1"}))

    lab.on("POST", "/bottles/b1/smell-log", flaky)
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    page.clock.run_for("10:00")
    sheet.locator(".phone-strips-liking").get_by_role("button", name="6", exact=True).click()
    sheet.get_by_role("button", name="Save").click()
    _wait_sync(page, "No connection to the PC. 1 kept on this phone")
    assert len(tries) == 1

    # Fifteen seconds later it is tried again: the same note, the same id.
    page.clock.run_for("00:15")
    _wait_sync(page, "Every note is on the PC.")
    assert len(tries) == 2
    assert tries[1] == tries[0]


def test_a_refused_note_waits_for_try_again_or_remove(lab):
    _phone(lab)
    page = lab.page
    lab.respond("POST", "/bottles/b1/smell-log", status=404, json={"detail": "Unknown bottle: b1"})
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    page.clock.run_for("10:00")
    sheet.get_by_label("In a few words").fill("smoky")
    sheet.get_by_role("button", name="Save").click()
    refused = sheet.locator(".phone-strips-sync .is-error")
    refused.wait_for()
    assert refused.inner_text() == "The PC refused a note for Vetiver Mineral R4: Unknown bottle: b1"
    posts = [key for key in lab.requests if key == ("POST", "/bottles/b1/smell-log")]

    # A refusal is not tried again on its own.
    page.clock.run_for("01:00")
    assert [key for key in lab.requests if key == ("POST", "/bottles/b1/smell-log")] == posts

    posted = _pc_takes_notes(lab)
    sheet.get_by_role("button", name="Try again").click()
    _wait_sync(page, "Every note is on the PC.")
    assert [body["words"] for body in posted] == ["smoky"]
    assert refused.is_hidden()


def test_remove_drops_a_refused_note_from_the_phone(lab):
    _phone(lab)
    page = lab.page
    lab.respond("POST", "/bottles/b1/smell-log", status=400, json={"detail": "client_id is already used by a different smell log entry"})
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    page.clock.run_for("10:00")
    sheet.locator(".phone-strips-liking").get_by_role("button", name="5", exact=True).click()
    sheet.get_by_role("button", name="Save").click()
    sheet.get_by_role("button", name="Remove it").click()
    assert page.evaluate("JSON.parse(localStorage.getItem('perfumechem.strips.v1.outbox'))") == {}
    assert _sync(page) == "Every note is on the PC."
    assert _focused_in_sheet(page)


def test_notes_kept_on_the_phone_go_when_the_page_opens_again(lab):
    lab.page.set_viewport_size(PHONE)
    lab.respond("GET", "/bottles", json=BOTTLES)
    posted = _pc_takes_notes(lab)
    note = {
        "clientId": "strip.kept0001.strip_1h", "bottleId": "b1", "label": "Vetiver Mineral R4", "window": "strip_1h",
        "leads": ["Iso E Super"], "weak": [], "liking": 9, "words": "", "loggedAt": "2026-10-15T09:00:00.000Z",
    }
    lab.page.add_init_script(
        f"localStorage.setItem('perfumechem.strips.v1.outbox', {json.dumps(json.dumps({note['clientId']: note}))})"
    )
    lab.open("#improve")
    lab.page.wait_for_function("document.querySelector('.phone-strips-panel-sync').textContent === 'Every note is on the PC.'")
    assert posted == [{
        "window": "strip_1h", "leads": ["Iso E Super"], "weak": [], "liking": 9, "words": "",
        "logged_at": "2026-10-15T09:00:00.000Z", "client_id": "strip.kept0001.strip_1h",
    }]


def test_a_strip_dipped_earlier_shows_what_is_due_when_the_page_opens(lab):
    _phone(lab)
    page = lab.page
    strip = {
        "b1": {"bottleId": "b1", "label": "Vetiver Mineral R4", "dippedAt": _iso(T0 - dt.timedelta(minutes=70)),
               "logged": {"strip_10m": "strip.old00001.strip_10m"}, "rows": ["Vetiver Bourbon"], "hasRecipe": True},
    }
    page.add_init_script(f"localStorage.setItem('perfumechem.strips.v1.active', {json.dumps(json.dumps(strip))})")
    lab.open("#bottles")
    panel = page.locator("#phone-strips-root")
    assert "Smell now: the 1 h check" in panel.inner_text()
    sheet = _open_strips(lab)
    sheet.locator(".phone-strips-line", has_text="Vetiver Mineral R4").click()
    assert _checks(sheet)[:2] == ["10 min: noted", "1 h: smell it now"]
    assert sheet.get_by_role("button", name="Vetiver Bourbon").is_visible()


def test_a_bottle_with_no_recipe_takes_typed_names_and_says_it_will_not_teach(lab):
    posted = _pc_takes_notes(lab, bottle="b2")
    _phone(lab)
    page = lab.page
    lab.on("POST", "/bottles/b2/smell-log", lambda route, request: (posted.append(json.loads(request.post_data)), route.fulfill(status=201, content_type="application/json", body="{}")))
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet, label="Iris <i>trial</i>")
    assert sheet.locator("#phone-strips-heading").inner_text() == "Iris <i>trial</i>"
    sheet.locator(".phone-strips-no-recipe").wait_for()
    assert "has no recipe in the Lab" in sheet.locator(".phone-strips-no-recipe").inner_text()
    page.clock.run_for("10:00")
    sheet.get_by_label("Leads (names, comma-separated)").fill("Orris, Ionone")
    sheet.get_by_label("Weak (names, comma-separated)").fill("Musk")
    sheet.get_by_role("button", name="Save").click()
    _wait_sync(page, "Every note is on the PC.")
    assert posted[-1]["leads"] == ["Orris", "Ionone"] and posted[-1]["weak"] == ["Musk"]


def test_ending_a_strip_with_checks_to_come_takes_a_second_tap_and_escape_closes(lab):
    _phone(lab)
    page = lab.page
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    opener = page.locator("#phone-strips-root").get_by_role("button", name="Smell strips step by step")
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    sheet.get_by_role("button", name="End this strip").click()
    assert sheet.get_by_role("button", name="Tap again to end it").is_visible()
    assert _focused_in_sheet(page)
    sheet.get_by_role("button", name="Tap again to end it").click()
    assert sheet.locator("#phone-strips-heading").inner_text() == "Strips you dipped"
    assert page.evaluate("JSON.parse(localStorage.getItem('perfumechem.strips.v1.active'))") == {}
    page.keyboard.press("Escape")
    assert sheet.is_hidden()
    assert opener.evaluate("(element) => element === document.activeElement")


def test_saving_a_check_with_nothing_marked_asks_for_something(lab):
    posted = _phone(lab)
    page = lab.page
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    page.clock.run_for("10:00")
    sheet.get_by_role("button", name="Save").click()
    assert sheet.locator(".phone-strips-form .phone-bench-check").inner_text() == (
        "Mark at least one name, a liking or a few words."
    )
    assert posted == []


# Records each buzz the page asks the phone for.
BUZZ = "window.__buzz = []; navigator.vibrate = (pattern) => { window.__buzz.push(pattern); return true; };"


def _notice(sheet):
    return sheet.locator(".phone-bench-notice[role='status']").inner_text()


def _outbox(page):
    return page.evaluate("JSON.parse(localStorage.getItem('perfumechem.strips.v1.outbox') || '{}')")


def test_the_panel_counts_down_and_the_phone_buzzes_while_the_view_is_closed(lab):
    _phone(lab)
    page = lab.page
    page.add_init_script(BUZZ)
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    sheet.get_by_role("button", name="Close").click()
    panel = page.locator("#phone-strips-root")
    assert "Next: the 10 min check in 10:00" in panel.inner_text()
    page.clock.run_for("01:00")
    assert "Next: the 10 min check in 9:00" in panel.inner_text()
    page.clock.run_for("09:00")
    assert "Smell now: the 10 min check" in panel.inner_text()
    assert page.evaluate("window.__buzz") == [[300, 150, 300]]


def test_a_check_due_on_another_strip_says_so_and_goes_there_in_one_tap(lab):
    _phone(lab)
    page = lab.page
    page.add_init_script(BUZZ)
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    page.clock.run_for("05:00")
    sheet.get_by_role("button", name="All strips").click()
    _dip(lab, sheet, label="Iris <i>trial</i>")
    assert sheet.locator("#phone-strips-heading").inner_text() == "Iris <i>trial</i>"
    go = sheet.get_by_role("button", name="Go to that strip")
    assert go.is_hidden()

    # The first strip's 10 min check opens while the second strip is on screen.
    page.clock.run_for("05:00")
    assert _notice(sheet) == "Smell now: Vetiver Mineral R4, the 10 min check"
    assert page.evaluate("window.__buzz") == [[300, 150, 300]]
    go.click()
    assert sheet.locator("#phone-strips-heading").inner_text() == "Vetiver Mineral R4"
    assert sheet.locator(".phone-strips-form-title").text_content() == "Smell now: the 10 min check"
    assert go.is_hidden()
    assert _notice(sheet) == ""


def test_a_half_written_note_stays_through_another_strip_and_closing_the_view(lab):
    posted = _phone(lab)
    page = lab.page
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    page.clock.run_for("10:00")
    sheet.get_by_role("button", name="Ambrox").click()
    sheet.locator(".phone-strips-liking").get_by_role("button", name="8", exact=True).click()
    sheet.get_by_label("In a few words").fill("dry cedar")

    sheet.get_by_role("button", name="All strips").click()
    sheet.locator(".phone-strips-line", has_text="Vetiver Mineral R4").click()
    assert sheet.get_by_role("button", name="Ambrox: leads").is_visible()
    assert sheet.get_by_label("In a few words").input_value() == "dry cedar"

    sheet.get_by_role("button", name="Close").click()
    sheet = _open_strips(lab)
    sheet.locator(".phone-strips-line", has_text="Vetiver Mineral R4").click()
    assert sheet.locator(".phone-strips-liking [aria-pressed='true']").inner_text() == "8"
    assert sheet.get_by_label("In a few words").input_value() == "dry cedar"
    sheet.get_by_role("button", name="Save").click()
    _wait_sync(page, "Every note is on the PC.")
    assert [(body["leads"], body["liking"], body["words"]) for body in posted] == [(["Ambrox"], 8, "dry cedar")]


@pytest.mark.parametrize(
    ("leads", "weak", "says"),
    [
        ("Orris, Musk", "orris", "Orris: marked both leading and weak. Pick one for each."),
        (", ".join(f"Name {index}" for index in range(13)), "", "Mark at most 12 names as leading, and 12 as weak."),
    ],
    ids=["both", "too-many"],
)
def test_a_note_the_pc_would_refuse_stays_on_screen_with_the_reason(lab, leads, weak, says):
    _phone(lab)
    posted = _pc_takes_notes(lab, bottle="b2")
    page = lab.page
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet, label="Iris <i>trial</i>")
    page.clock.run_for("10:00")
    sheet.get_by_label("Leads (names, comma-separated)").fill(leads)
    sheet.get_by_label("Weak (names, comma-separated)").fill(weak)
    sheet.get_by_role("button", name="Save").click()
    assert sheet.locator(".phone-strips-form .phone-bench-check").inner_text() == says
    assert _checks(sheet)[0] == "10 min: smell it now"
    assert sheet.get_by_label("Leads (names, comma-separated)").input_value() == leads
    assert _outbox(page) == {}
    assert posted == []


def test_removing_a_refused_note_shows_what_it_said_and_lets_the_check_be_noted_again(lab):
    _phone(lab)
    page = lab.page
    lab.respond("POST", "/bottles/b1/smell-log", status=404, json={"detail": "Unknown bottle: b1"})
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    page.clock.run_for("10:00")
    sheet.locator(".phone-strips-liking").get_by_role("button", name="5", exact=True).click()
    sheet.get_by_label("In a few words").fill("smoky")
    sheet.get_by_role("button", name="Save").click()
    sheet.locator(".phone-strips-sync .is-error").wait_for()
    assert sheet.locator(".phone-strips-refused-note").inner_text() == "The note: 10 min · 5/10 · “smoky”"
    assert _checks(sheet)[0] == "10 min: noted"

    sheet.get_by_role("button", name="Remove it").click()
    assert _checks(sheet)[0] == "10 min: smell it now"
    assert sheet.locator(".phone-strips-form").is_visible()
    assert sheet.locator(".phone-strips-refused-note").is_hidden()


def test_a_tap_that_leaves_the_focus_on_the_page_does_not_jump_the_view_to_the_top(lab):
    _phone(lab)
    page = lab.page
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    page.clock.run_for("10:00")
    # Safari on an iPhone leaves the focus on the page when a button is tapped.
    page.evaluate("document.activeElement.blur()")
    top = page.evaluate("(() => { const s = document.querySelector('.phone-strips'); s.scrollTop = s.scrollHeight; return s.scrollTop; })()")
    assert top > 0
    page.evaluate("document.querySelector('.phone-strips-liking [data-liking=\"8\"]').click()")
    assert sheet.locator(".phone-strips-liking [aria-pressed='true']").inner_text() == "8"
    assert page.evaluate("document.activeElement === document.body")
    assert page.evaluate("document.querySelector('.phone-strips').scrollTop") == top


def test_a_check_that_closes_while_the_note_is_written_keeps_it_to_save_at_its_start(lab):
    posted = _phone(lab)
    page = lab.page
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    page.clock.run_for("10:00")
    page.clock.run_for("01:00")
    sheet.get_by_label("In a few words").fill("resinous")
    page.clock.run_for("04:00")

    assert _checks(sheet)[0] == "10 min: missed"
    assert _notice(sheet) == "The 10 min check closed while you were writing. Your note is kept below."
    assert sheet.locator(".phone-strips-form-title").text_content().startswith("The 10 min check closed at ")
    assert sheet.get_by_label("In a few words").input_value() == "resinous"
    assert sheet.get_by_role("button", name="Drop this note").is_visible()
    sheet.get_by_role("button", name="Save").click()
    _wait_sync(page, "Every note is on the PC.")
    assert [(body["window"], body["words"], body["logged_at"]) for body in posted] == [
        ("strip_10m", "resinous", _iso(T0 + dt.timedelta(minutes=12)).replace("Z", ".000Z")),
    ]
    assert _checks(sheet)[0] == "10 min: noted"
    assert _notice(sheet) == "Noted."


def test_a_check_left_alone_clears_its_smell_now_and_a_dropped_note_is_gone(lab):
    posted = _phone(lab)
    page = lab.page
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    page.clock.run_for("10:00")
    assert _notice(sheet) == "Smell now: the 10 min check"
    page.clock.run_for("05:00")
    assert _checks(sheet)[0] == "10 min: missed"
    assert _notice(sheet) == ""
    assert sheet.locator(".phone-strips-form").is_hidden()

    # The 1 h check: a note started, the check closes, and the note is dropped.
    page.clock.fast_forward("45:00")
    assert _checks(sheet)[1] == "1 h: smell it now"
    sheet.get_by_label("In a few words").fill("thin")
    page.clock.fast_forward("30:00")
    assert _checks(sheet)[1] == "1 h: missed"
    sheet.get_by_role("button", name="Drop this note").click()
    assert sheet.locator(".phone-strips-form").is_hidden()
    assert _focused_in_sheet(page)
    assert posted == []
    assert _outbox(page) == {}


def test_recipe_names_come_once_the_pc_answers_after_a_strip_dipped_offline(lab):
    _phone(lab)
    page = lab.page
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    lab.fail("GET", "/bottles/b1/smell-log")
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    recipe = sheet.locator(".phone-strips-no-recipe")
    assert recipe.inner_text() == "The recipe names come when the PC answers. You can type names meanwhile."

    lab.respond("GET", "/bottles/b1/smell-log", json=LOG)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    page.clock.run_for("10:00")
    sheet.get_by_role("button", name="Vetiver Bourbon").wait_for()
    assert recipe.is_hidden()


def test_the_view_opens_in_the_language_last_picked_and_escape_closes_it_from_anywhere(lab):
    _phone(lab)
    page = lab.page
    lab.open("#bottles")
    # Thai was picked in phone bench mode after this page loaded.
    page.evaluate("localStorage.setItem('perfumechem.bench.lang', 'th')")
    sheet = _open_strips(lab)
    assert sheet.locator("#phone-strips-heading").inner_text() == "แถบที่จุ่มไว้"
    page.evaluate("document.activeElement.blur()")
    page.keyboard.press("Escape")
    assert sheet.is_hidden()


def test_a_note_the_phone_cannot_keep_is_not_called_noted(lab):
    posted = _phone(lab)
    page = lab.page
    lab.open("#bottles")
    page.clock.pause_at(T0 + dt.timedelta(minutes=1))
    sheet = _open_strips(lab)
    _dip(lab, sheet)
    page.clock.run_for("10:00")
    sheet.get_by_label("In a few words").fill("amber")
    page.evaluate(
        "(() => { const set = Storage.prototype.setItem; Storage.prototype.setItem = function (key, value) {"
        " if (key === 'perfumechem.strips.v1.outbox') throw new DOMException('full', 'QuotaExceededError');"
        " return set.call(this, key, value); }; })()"
    )
    sheet.get_by_role("button", name="Save").click()
    assert sheet.locator(".phone-strips-form .phone-bench-check").inner_text().startswith("This phone could not keep the note")
    assert _checks(sheet)[0] == "10 min: smell it now"
    assert sheet.get_by_label("In a few words").input_value() == "amber"
    assert _notice(sheet) != "Noted."
    assert posted == []


BENCH_RECORD = {
    "schema_version": "user-batch-record-v1", "lot": "KS-S1", "made_on": "2026-10-15", "made_by": "Kenny",
    "recorded_at": "2026-10-15T09:00:00+00:00", "formula_name": "Demo Cedar 30mL", "bottles": "1", "bottle_ml": "30",
    "planned_rows": [
        {"line": 1, "material": "Hedione", "strength": "neat", "concentration_fraction_decimal": None,
         "concentration_basis": "NEAT", "unit": "uL", "card_amount": "1000", "planned_amount": "1000"},
    ],
    "actuals": [], "actuals_recorded_at": None, "actuals_version": 0,
}


def _bench_answers(lab):
    lab.respond("GET", "/v2/batches", json={"schema_version": "batch-records-v1", "records": [BENCH_RECORD]})
    lab.respond("POST", "/v2/workbench/material-densities", json={"densities": {"Hedione": "0.998"}})


def test_a_weigh_sheet_answered_after_the_strips_view_opened_waits_behind_it(lab):
    _phone(lab)
    _bench_answers(lab)
    page = lab.page
    held = []
    lab.on("GET", f"/v2/batches/{BENCH_RECORD['lot']}", lambda route, _request: held.append(route))
    lab.open("#bottles")
    page.evaluate(f"openPhoneBench({json.dumps(BENCH_RECORD['lot'])})")
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(50)
    assert held
    sheet = _open_strips(lab)
    held[0].fulfill(status=200, content_type="application/json", body=json.dumps(BENCH_RECORD))
    page.evaluate("new Promise((resolve) => setTimeout(resolve, 300))")
    assert page.locator(".phone-bench:not(.phone-strips)").is_hidden()
    assert page.evaluate("document.querySelector('.phone-strips').inert") is False
    sheet.get_by_role("button", name="Dip a strip").click()
    assert sheet.locator("#phone-strips-heading").inner_text() == "Which bottle?"


def test_the_strips_view_does_not_open_over_the_weigh_sheet(lab):
    _phone(lab)
    _bench_answers(lab)
    lab.respond("GET", f"/v2/batches/{BENCH_RECORD['lot']}", json=BENCH_RECORD)
    page = lab.page
    lab.open("#bottles")
    # Thai was picked in the strips view after this page loaded: the weigh sheet opens in it.
    page.evaluate("localStorage.setItem('perfumechem.bench.lang', 'th')")
    page.evaluate(f"openPhoneBench({json.dumps(BENCH_RECORD['lot'])})")
    bench = page.locator(".phone-bench:not(.phone-strips)")
    bench.wait_for()
    assert bench.get_attribute("lang") == "th"
    page.evaluate("phoneStrips.open()")
    assert page.locator(".phone-strips").is_hidden()
    assert page.evaluate("document.querySelector('.phone-bench:not(.phone-strips)').inert") is False
