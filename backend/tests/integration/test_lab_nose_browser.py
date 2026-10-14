"""The Your nose page at phone size: what the model learned, and a blind test run to its reveal."""

import json
import os

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
from tests.integration.test_formula_editor_browser import SOURCE

pytest.importorskip("playwright.sync_api")

EVIL = "<img src=x onerror=alert(1)>"
FORMULA_ID = "a" * 32
TEST_ID = "c" * 32

CALIBRATION = {
    "schema": "smell-log-calibration-v1", "evidence_class": "UNKNOWN", "calibrated": False,
    "reason": "3 of 10 bottles logged", "min_bottles": 10, "n_bottles": 3, "n_bottles_skipped": 0,
    "baseline_score": -2, "corrected_score": 1, "best_score": 6,
    "basis": "A ranking adjustment learned from your smell log: not how strong anything smells.",
    "rule": {"min_bottles_per_material": 3},
    "held_out": [
        {"bottle_id": "b1", "label": f"Rose {EVIL}", "windows": ["strip_10m", "strip_1h"],
         "baseline_score": -1, "corrected_score": 1, "best_score": 3},
        {"bottle_id": "b2", "label": "Iris R2", "windows": ["strip_3h"], "baseline_score": -1, "corrected_score": 0, "best_score": 3},
    ],
    "factors": [
        {"name": "Ambrox", "factor": 2.0, "label": "×2.0", "n_seen": 3, "n_bottles": 3, "status": "fitted"},
        {"name": "Hedione", "factor": 1.0, "label": "×1.0", "n_seen": 3, "n_bottles": 3, "status": "fitted"},
        {"name": "Iris", "factor": 1.0, "label": "×1.0", "n_seen": 1, "n_bottles": 1, "status": "too few bottles"},
    ],
}

VERSIONS = {"formulas": [{"formula_id": FORMULA_ID, "name": "Rose Test", "latest": 2, "versions": [
    {"version": 1, "row_count": 1}, {"version": 2, "row_count": 1}]}]}


def _row(amount):
    return {"material": "Hedione", "stock_id": None, "fraction": "1", "basis": "neat", "carrier": None,
            "solid": False, "amount": amount, "note": ""}


TEST = {
    "test_id": TEST_ID, "title": f"Rose {EVIL}", "brief": "A fresh rose", "created_at": "2026-10-14T13:00:00+00:00",
    "times": ["5 min", "1 h", "4 h"],
    "vials": [{"letter": "A", "rows": [_row("600")]}, {"letter": "B", "rows": [_row("1000/3")]}],
    "picks": [], "revealed": False, "revealed_at": None, "key": None, "outcome": None,
}
PICK = {"time": "1 h", "choice": "B", "name_a": 4, "name_b": None, "note": "B rounder", "at": "2026-10-14T14:00:00+00:00"}
KEY = {
    "A": {"formula_id": FORMULA_ID, "version": 1, "name": "Rose Test", "label": "Composer"},
    "B": {"formula_id": FORMULA_ID, "version": 2, "name": "Rose Test", "label": "Opus card"},
}
TALLY = [{"label": "Opus card", "picks": 1, "preferred": 1, "name_mean": None},
         {"label": "Composer", "picks": 1, "preferred": 0, "name_mean": 4.0}]


def _answer(route, body, status=200):
    route.fulfill(status=status, content_type="application/json", body=json.dumps(body))


def _open(lab, posted):
    listed = []

    def blind_tests(route, _request):
        listed.append(1)
        _answer(route, {"tests": [TEST], "tally": TALLY if len(listed) > 1 else []})

    def pick(route, request):
        posted.append(("pick", json.loads(request.post_data)))
        _answer(route, {**TEST, "picks": [PICK]})

    def reveal(route, _request):
        posted.append(("reveal", None))
        _answer(route, {**TEST, "picks": [PICK], "revealed": True, "key": KEY,
                        "outcome": [{"time": "1 h", "preferred": "Opus card"}]})

    def create(route, request):
        posted.append(("create", json.loads(request.post_data)))
        _answer(route, {**TEST, "test_id": "d" * 32, "title": "Second"}, 201)

    lab.respond("GET", "/smell-log/calibration", json=CALIBRATION)
    lab.respond("GET", "/v2/workbench/formula-versions", json=VERSIONS)
    lab.on("GET", "/v2/workbench/blind-tests", blind_tests)
    lab.on("POST", f"/v2/workbench/blind-tests/{TEST_ID}/picks", pick)
    lab.on("POST", f"/v2/workbench/blind-tests/{TEST_ID}/reveal", reveal)
    lab.on("POST", "/v2/workbench/blind-tests", create)
    lab.page.set_viewport_size({"width": 390, "height": 844})
    lab.open("#nose")
    stop_smooth_scrolling(lab.page)
    lab.page.locator(".blind-test h3").first.wait_for()
    return listed


def test_the_page_says_the_correction_is_off_and_shows_each_bottle_it_had_not_seen(lab):
    _open(lab, [])
    page = lab.page

    status = page.locator("#nose-learning .nose-status")
    assert status.inner_text() == (
        "Off: 3 of 10 bottles have strip logs. It turns on only if it beats the plain model on bottles it has not seen.")
    held = page.locator("table.nose-held-out")
    assert held.locator("caption").inner_text() == "2 bottles; best possible 6"
    assert held.locator("tbody tr").first.locator("th, td").all_inner_texts() == [f"Rose {EVIL}", "10 min, 1 h", "-1 → 1", "3"]
    factors = page.locator("table.nose-factors tbody tr")
    assert [row.locator("th, td").all_inner_texts() for row in factors.all()] == [
        ["Ambrox", "×2.0, not used yet", "3"], ["Iris", "needs 3 bottles", "1"]]
    assert page.locator("#nose-learning").inner_text().count("1 more material with no change yet.") == 1
    assert page.locator("#nose-learning img, #blind-test img").count() == 0
    assert sideways_scroll(page) == 0
    for theme in ("light", "dark"):
        set_theme(page, theme)
        assert contrast_failures(page, '[data-panel="nose"]') == [], theme
    set_theme(page, "light")
    assert small_targets(page, '[data-panel="nose"]') == []
    page.focus('.blind-new input[name="title"]')
    wait_until_still(page)
    hidden = [stop for stop in tab_through(page, 12) if not stop.get("visible")]
    assert hidden == [], json.dumps(hidden)
    shot = os.environ.get("NOSE_SCREENSHOT")
    if shot:
        page.screenshot(path=shot.replace(".png", "-before.png"), full_page=True)


def test_a_blind_pick_is_saved_then_the_reveal_shows_which_vial_was_which(lab):
    posted = []
    listed = _open(lab, posted)
    page = lab.page
    card = page.locator(f'.blind-test[data-test="{TEST_ID}"]')

    assert card.locator("h3").inner_text() == f"Rose {EVIL}"
    assert card.locator(".blind-vial summary").all_inner_texts() == ["1 row", "1 row"]
    card.locator(".blind-vial summary").last.click()
    assert card.locator(".blind-vial li").last.inner_text() == "Hedione · neat · 333.3 µL"
    assert card.locator(".blind-reveal").is_disabled()
    assert "Composer" not in page.locator('[data-panel="nose"]').inner_text()

    card.locator(".blind-pick button[type=submit]").click()
    assert card.locator(".blind-pick .status-line").inner_text() == "Pick the strip time you are smelling."
    card.locator('[data-time="1 h"]').click()
    card.locator('[data-choice="B"]').click()
    card.locator('select[name="name_a"]').select_option("4")
    card.locator('input[name="note"]').fill("B rounder")
    card.locator(".blind-pick button[type=submit]").click()
    card.locator(".blind-picks li").wait_for()

    assert posted == [("pick", {"time": "1 h", "choice": "B", "name_a": 4, "name_b": None, "note": "B rounder"})]
    assert card.locator(".blind-picks li").inner_text() == "1 h: you picked B · smells like its name: A 4/5 · “B rounder”"
    reveal = card.locator(".blind-reveal")
    assert reveal.is_enabled()
    reveal.click()
    outcome = card.locator(".blind-outcome")
    outcome.wait_for()

    assert posted[-1] == ("reveal", None)
    assert outcome.locator("p").all_inner_texts() == [
        "A was Composer (Rose Test v1); B was Opus card (Rose Test v2).", "1 h: you preferred Opus card."]
    assert page.evaluate("document.activeElement.classList.contains('blind-outcome')")
    assert card.locator(".blind-pick").count() == 0
    page.locator(".blind-tally li").first.wait_for()
    assert len(listed) == 2
    assert page.locator(".blind-tally li").all_inner_texts() == [
        "Opus card: preferred in 1 of 1 pick", "Composer: preferred in 0 of 1 pick · smells like its name 4/5 on average"]
    assert sideways_scroll(page) == 0
    shot = os.environ.get("NOSE_SCREENSHOT")
    if shot:
        page.screenshot(path=shot, full_page=True)


def test_a_new_test_is_made_from_two_saved_versions_and_a_vial_goes_to_the_bench_sheet(lab):
    posted = []
    _open(lab, posted)
    page = lab.page
    form = page.locator(".blind-new")
    assert form.locator('select[name="version_1"] option').all_inner_texts() == [
        "Choose a version", "Rose Test v2 (1 row)", "Rose Test v1 (1 row)"]

    form.locator('input[name="title"]').fill("Second")
    form.locator('select[name="version_1"]').select_option(f"{FORMULA_ID}:2")
    form.locator('input[name="label_1"]').fill("Composer")
    form.locator('select[name="version_2"]').select_option(f"{FORMULA_ID}:1")
    form.locator('input[name="label_2"]').fill("Opus card")
    form.locator("button[type=submit]").click()
    page.locator(f'.blind-test[data-test="{"d" * 32}"]').wait_for()

    assert posted == [("create", {
        "title": "Second", "brief": "",
        "first": {"formula_id": FORMULA_ID, "version": 2, "label": "Composer"},
        "second": {"formula_id": FORMULA_ID, "version": 1, "label": "Opus card"},
    })]
    assert form.locator(".status-line").inner_text() == "Made. Mix vial A and vial B from their sheets below."

    texts = []

    def formula_text(route, request):
        texts.append(json.loads(request.post_data)["text"])
        _answer(route, {**SOURCE, "schema_version": "workbench-formula-text-v1", "source_path": None})

    lab.on("POST", "/v2/workbench/formula-text", formula_text)
    page.locator(f'.blind-test[data-test="{TEST_ID}"] [data-bench="A"]').click()
    page.wait_for_function("!document.getElementById('bench-preview-card').hidden")
    assert page.evaluate("location.hash") == "#benchsheet"
    assert texts == ["# Vial A\n\n| Material | Dilution | Amount (µL) |\n|---|---|---:|\n| Hedione | neat | 600 |\n"]
