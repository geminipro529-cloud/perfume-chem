"""The Lab page, driven in a real browser against fixture API answers."""

import pytest

pytest.importorskip("playwright.sync_api")


def test_page_boots_on_the_default_fixtures(lab):
    lab.open()
    assert lab.page_errors == []
    assert lab.unexpected == []
    assert not any(entry["error"] for entry in lab.status_history())


def _submit_bottle(lab, label="Test bottle"):
    form = lab.page.locator("#bottle-form")
    form.locator('input[name="label"]').fill(label)
    form.locator('button[type="submit"]').click()


def test_saved_bottle_is_not_reported_as_not_saved_when_the_refresh_fails(lab):
    lab.open("#bottles")
    lab.respond("POST", "/bottles", status=201, json={"id": "b1", "label": "Test bottle", "status": "open"})
    lab.fail("GET", "/bottles")

    _submit_bottle(lab)
    lab.page.wait_for_function(
        "() => window.__statusHistory.some((entry) => entry.text.startsWith(\"Saved, but the lists didn't refresh\"))"
    )
    lab.page.locator('#bottle-form button[type="submit"]:enabled').wait_for()

    assert ("POST", "/bottles") in lab.requests
    texts = [entry["text"] for entry in lab.status_history()]
    assert "Record committed." in texts
    assert lab.page.locator("#bottle-form-error").count() == 0
    assert "Not saved." not in lab.page.locator("#bottle-form").inner_text()
    assert lab.page.locator("#bottle-form [aria-invalid]").count() == 0
    # The refresh failure is still reported, just not as a failed save.
    last = lab.status_history()[-1]
    assert last["error"] is True
    assert last["text"].startswith("Saved, but the lists didn't refresh")


def test_rejected_bottle_still_shows_the_inline_error_box(lab):
    lab.open("#bottles")
    lab.respond(
        "POST",
        "/bottles",
        status=422,
        json={"detail": [{"loc": ["body", "label"], "msg": "Field required", "type": "missing"}]},
    )

    _submit_bottle(lab)
    box = lab.page.locator("#bottle-form-error")
    box.wait_for()

    assert box.get_attribute("role") == "alert"
    assert box.inner_text().startswith("Not saved.")
    assert "Label: required" in box.inner_text()
    assert lab.page.locator('#bottle-form input[name="label"]').get_attribute("aria-invalid") == "true"
    assert "Record committed." not in [entry["text"] for entry in lab.status_history()]


def _assert_view_shown(lab, view):
    assert lab.page.locator(f'[data-panel="{view}"]').is_visible()
    assert lab.page.locator(f'.nav-item[data-view="{view}"]').get_attribute("aria-current") == "page"


def test_loading_with_the_skip_link_hash_shows_the_improve_view(lab):
    lab.open("#main-content")

    _assert_view_shown(lab, "improve")
    assert lab.page.locator(".view.is-visible").count() == 1
    assert lab.page_errors == []


def test_skip_link_focuses_main_without_changing_the_hash(lab):
    lab.open("#bottles")

    lab.page.locator(".skip-link").focus()
    lab.page.keyboard.press("Enter")

    assert lab.page.evaluate("document.activeElement.id") == "main-content"
    assert lab.page.evaluate("location.hash") == "#bottles"
    _assert_view_shown(lab, "bottles")
