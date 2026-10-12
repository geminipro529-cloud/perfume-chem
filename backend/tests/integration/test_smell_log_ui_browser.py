"""The smell log on a phone-sized Bottles page, against fixture API answers."""

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

LOG = {
    "windows": [
        {"key": "strip_10m", "label": "Strip 10 min", "surface": "strip", "seconds": 600},
        {"key": "strip_1h", "label": "Strip 1 h", "surface": "strip", "seconds": 3600},
        {"key": "strip_3h", "label": "Strip 3 h", "surface": "strip", "seconds": 10800},
        {"key": "skin_day1", "label": "Skin day 1", "surface": "skin", "seconds": 86400},
        {"key": "skin_day7", "label": "Skin day 7", "surface": "skin", "seconds": 604800},
    ],
    "rows": ["Orris Butter", "Hedione", "<img src=x onerror=alert(1)>"],
    "entries": [{
        "id": "o1", "window": "strip_10m", "surface": "strip", "leads": ["Hedione"], "weak": [],
        "liking": 6, "words": "bright", "logged_at": "2026-10-12T10:00:00+00:00",
    }],
}

COMPARISON = {
    "basis": "Model's leaders (detection screen)", "available": True, "reason": None,
    "not_modelled": [{"name": "Orris Butter", "reason": "no volume, and no stock density to convert its mass"}],
    "windows": [
        {
            "window": "strip_10m", "label": "Strip 10 min", "surface": "strip", "seconds": 600, "n_entries": 1,
            "liking_mean": 6, "you_leads": [{"name": "Hedione", "count": 1}], "you_weak": [],
            "model_in_range": True, "model_time_label": "10 min", "model_note": None,
            "model_top": ["Linalool", "Lavender EO", "<img src=x onerror=alert(1)>"],
            "agreement": {
                "leads_the_model_also_had_on_top": [],
                "model_top_you_did_not_mark_leading": ["Linalool", "Lavender EO", "<img src=x onerror=alert(1)>"],
                "you_marked_weak_but_model_had_on_top": [],
                "leads_the_model_did_not_have_on_top": ["Hedione"],
            },
        },
        {
            "window": "skin_day1", "label": "Skin day 1", "surface": "skin", "seconds": 86400, "n_entries": 1,
            "liking_mean": 8, "you_leads": [{"name": "Orris Butter", "count": 1}], "you_weak": [],
            "model_in_range": False, "model_time_label": None, "model_top": [], "agreement": None,
            "model_note": "Beyond the model's range: its time curve stops at 4 h, so it says nothing about skin day 1.",
        },
    ],
}


def test_phone_user_taps_a_window_rows_and_liking_then_saves(lab):
    lab.page.set_viewport_size({"width": 390, "height": 844})
    lab.respond("GET", "/bottles", json=[{"id": "b1", "label": "Iris trial", "status": "active"}])
    lab.respond("GET", "/bottles/b1/smell-log", json=LOG)
    compared = []

    def comparison(route, _request):
        compared.append(1)
        route.fulfill(status=200, content_type="application/json", body=json.dumps(COMPARISON))

    lab.on("GET", "/bottles/b1/smell-log/comparison", comparison)
    posted = []

    def save(route, request):
        posted.append(json.loads(request.post_data))
        route.fulfill(status=201, content_type="application/json", body=json.dumps({
            "id": "o2", "window": "strip_1h", "surface": "strip", "leads": ["Orris Butter"],
            "weak": ["Hedione"], "liking": 8, "words": "powdery", "logged_at": "2026-10-12T11:00:00+00:00",
        }))

    lab.on("POST", "/bottles/b1/smell-log", save)
    lab.open("#bottles")
    lab.page.select_option("#smell-log-bottle", "b1")
    form = lab.page.locator(".smell-log-form")
    form.wait_for()

    form.locator('[data-window="strip_1h"]').click()
    form.locator('[data-row="Orris Butter"]').click()
    hedione = form.locator('[data-row="Hedione"]')
    hedione.click()
    hedione.click()
    form.locator('[data-liking="8"]').click()
    form.locator('input[name="words"]').fill("powdery")

    assert form.locator('[data-row="Orris Butter"]').inner_text() == "Orris Butter: leads"
    assert hedione.inner_text() == "Hedione: weak"
    assert form.locator('input[name="leads_text"]').is_hidden()
    assert lab.page.evaluate("document.documentElement.scrollWidth") <= 390

    form.locator('button[type="submit"]').click()
    lab.page.locator(".smell-log-form .status-line", has_text="Saved.").wait_for()

    assert posted == [{
        "window": "strip_1h", "leads": ["Orris Butter"], "weak": ["Hedione"], "liking": 8, "words": "powdery",
    }]
    past = lab.page.locator(".smell-log-past li")
    assert past.count() == 2
    assert past.first.inner_text().startswith("Strip 1 h · ")
    assert form.locator('[aria-pressed="true"]').count() == 0

    compare = lab.page.locator(".smell-log-compare")
    compare.locator("h3", has_text="Model said / you smelled").wait_for()
    assert len(compared) == 2
    blocks = compare.locator(".smell-log-compare-block")
    assert blocks.count() == 2
    first = blocks.first.inner_text()
    assert "Model, 10 min: Linalool, Lavender EO, <img src=x onerror=alert(1)>" in first
    assert "You: leads Hedione" in first
    assert "You smelled Hedione leading; the model didn't have it on top." in first
    assert "Beyond the model's range" in blocks.nth(1).inner_text()
    assert "Not in the model: Orris Butter" in compare.inner_text()
    assert lab.page.evaluate("document.documentElement.scrollWidth") <= 390
    shot = os.environ.get("SMELL_LOG_COMPARE_SCREENSHOT")
    if shot:
        Path(shot).parent.mkdir(parents=True, exist_ok=True)
        compare.scroll_into_view_if_needed()
        lab.page.screenshot(path=shot)
