"""The smell log on a phone-sized Bottles page, against fixture API answers."""

import json

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


def test_phone_user_taps_a_window_rows_and_liking_then_saves(lab):
    lab.page.set_viewport_size({"width": 390, "height": 844})
    lab.respond("GET", "/bottles", json=[{"id": "b1", "label": "Iris trial", "status": "active"}])
    lab.respond("GET", "/bottles/b1/smell-log", json=LOG)
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
