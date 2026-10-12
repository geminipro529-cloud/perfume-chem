"""Stress-test fixes: failed chat briefs, double-submitting forms, and the application ID path."""

import json

import pytest

pytest.importorskip("playwright.sync_api")

CHAT_PATH = "/v2/workbench/formula-chat"
APPLICATION_ID = "0b8f6a3e-5c1d-4e7a-9b2f-3d4c5e6f7a8b"


def _posts(lab, path):
    return [item for item in lab.requests if item == ("POST", path)]


def test_failed_brief_is_not_sent_as_context_with_the_next_one(lab):
    bodies = []
    answers = [(422, {"detail": "message: too long"}), (200, {"assistant_message": "Clarify, please."})]

    def handler(route, request):
        bodies.append(json.loads(request.post_data))
        status, body = answers[len(bodies) - 1]
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body))

    lab.on("POST", CHAT_PATH, handler)
    lab.open("#formulas")
    form = lab.page.locator("#formula-chat-form")
    message = form.locator('[name="message"]')
    submit = form.locator("#formula-chat-submit")

    message.fill("Brief A distinctive failing text")
    submit.click()
    lab.page.get_by_text("I could not create that draft").wait_for()
    form.locator("#formula-chat-submit:enabled").wait_for()
    message.fill("Brief B second try")
    submit.click()
    lab.page.locator("#formula-result-summary").get_by_text("Clarify, please.").wait_for()

    assert len(bodies) == 2
    assert bodies[1]["message"] == "Brief B second try"
    assert "Brief A" not in json.dumps(bodies[1]["conversation_context"])


def _triple_click_shows_one_post_and_inline_error(lab, hash_, form_id, path, fill, before=None):
    lab.respond("POST", path, status=500, json={"detail": "The disk is full."})
    lab.open(hash_)
    if before:
        lab.page.evaluate(before)
    form = lab.page.locator(f"#{form_id}")
    for name, value in fill.items():
        form.locator(f'[name="{name}"]').fill(value)
    form.locator('button[type="submit"]').click(click_count=3)
    box = lab.page.locator(f"#{form_id}-error")
    box.wait_for()
    form.locator('button[type="submit"]:enabled').wait_for(state="attached")
    lab.page.wait_for_timeout(300)

    assert len(_posts(lab, path)) == 1
    assert box.get_attribute("role") == "alert"
    assert box.inner_text().startswith("Not saved.")
    assert "The disk is full." in box.inner_text()


def test_stage_restore_triple_click_posts_once_and_shows_the_error_box(lab):
    _triple_click_shows_one_post_and_inline_error(
        lab, "#dashboard", "stage-restore-form", "/restores/stage", {"snapshot_path": "snap.zip"}
    )


def test_analysis_triple_click_posts_once_and_shows_the_error_box(lab):
    _triple_click_shows_one_post_and_inline_error(
        lab, "#formulas", "analysis-form", "/analysis", {},
        before="document.querySelectorAll('details').forEach((d) => { d.open = true; })",
    )


def _open_observation(lab):
    lab.respond("GET", "/experiments", json=[{"id": "e1", "name": "Trial"}])
    lab.open("#experiments")
    form = lab.page.locator("#observation-form")
    return form, form.locator('[name="application_id"]')


def test_malformed_application_id_sends_no_request(lab):
    form, field = _open_observation(lab)
    field.fill("a/b?c")
    form.locator('button[type="submit"]').click()
    lab.page.wait_for_timeout(300)

    assert not [item for item in lab.requests if "/observations" in item[1]]
    assert field.evaluate("(el) => el.validity.patternMismatch") is True


def test_valid_application_id_goes_in_the_path(lab):
    path = f"/applications/{APPLICATION_ID}/observations"
    lab.respond("POST", path, status=201, json={"id": "o1"})
    form, field = _open_observation(lab)
    field.fill(APPLICATION_ID)
    form.locator('button[type="submit"]').click()
    lab.page.wait_for_timeout(500)

    assert _posts(lab, path) == [("POST", path)]
