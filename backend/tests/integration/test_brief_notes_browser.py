"""Create a formula at phone size: the chips of what the composer understood, before composing.

The page's requests go to the real brief reader (engine/formulation_intelligence/brief_notes.py)
through the endpoint's own request model, so a star sentence or a Must avoid word the page
writes is checked against what the composer actually reads.
"""

import json
import os

import pytest
from engine.formulation_intelligence.brief_notes import understood_notes

from app.api.v1.endpoints.lab_brief_notes import BriefNotesRequest
from tests.integration.lab_a11y import (
    contrast_failures,
    set_theme,
    sideways_scroll,
    small_targets,
    stop_smooth_scrolling,
)

pytest.importorskip("playwright.sync_api")

BRIEF = "A pink pepper and cedar fougere with vetiver"
EVIL = "<img src=x onerror=alert(1)>"


def _open(lab):
    asked = []

    def brief_notes(route, request):
        body = BriefNotesRequest.model_validate(json.loads(request.post_data))
        asked.append(body.model_dump())
        answer = understood_notes(formula_name=body.formula_name, message=body.message, must_avoid=body.must_avoid,
                                  conversation_context=body.conversation_context)
        route.fulfill(status=200, content_type="application/json", body=json.dumps(answer))

    lab.on("POST", "/v2/workbench/brief-notes", brief_notes)
    lab.page.set_viewport_size({"width": 390, "height": 844})
    lab.open("#formulas")
    stop_smooth_scrolling(lab.page)
    form = lab.page.locator("#formula-chat-form")
    form.locator('[name="formula_name"]').fill("Baie Rose Homme")
    form.locator('[name="message"]').fill(BRIEF)
    return asked


def _labels(page):
    return page.locator("#brief-notes .brief-chip-label").all_inner_texts()


def _chip(page, label):
    return page.locator("#brief-notes .brief-chip").filter(has=page.locator(".brief-chip-label", has_text=label)).first


def test_the_chips_show_what_it_read_and_a_star_or_leave_out_edits_the_brief_on_the_page(lab):
    asked = _open(lab)
    page = lab.page
    form = page.locator("#formula-chat-form")
    message = form.locator('[name="message"]')

    assert page.is_hidden("#brief-notes")
    assert asked == []
    page.click("#brief-notes-toggle")
    _chip(page, "Pink Pepper EO").wait_for()

    assert page.get_attribute("#brief-notes-toggle", "aria-expanded") == "true"
    assert asked == [{"formula_name": "Baie Rose Homme", "message": BRIEF, "must_avoid": [], "conversation_context": []}]
    labels = _labels(page)
    assert {"Pink Pepper EO", "fougere coumarin", "spice"} <= set(labels), labels
    spice = _chip(page, "spice")
    assert "comes with Pink Pepper EO" in spice.locator(".brief-chip-meta").inner_text()
    assert spice.locator(".brief-chip-remove").count() == 0
    assert page.locator("#brief-notes .brief-notes-status").inner_text().startswith("No star yet")
    assert any(line.startswith("For the structure it also adds:") for line in page.locator("#brief-notes .brief-notes-extra li").all_inner_texts())

    # Make the star: the sentence goes into the brief he can see, then the chip says so.
    _chip(page, "Pink Pepper EO").locator(".brief-chip-star").click()
    assert message.input_value() == f"{BRIEF}. The star is pink pepper."
    page.wait_for_function("document.querySelector('#brief-notes .brief-chip-star[aria-pressed=\"true\"]') !== null")
    assert page.locator("#brief-notes .brief-notes-status").inner_text().startswith("Pink Pepper EO is the star.")
    assert _chip(page, "Pink Pepper EO").locator(".brief-chip-star").inner_text() == "★ The star"

    # Leave out: the word goes in Must avoid, which opens so he sees it, and the note goes.
    word = _chip(page, "fougere coumarin").locator(".brief-chip-remove")
    word.click()
    assert form.locator('[name="must_avoid"]').input_value() == "fougere"
    assert form.locator(".optional-details").get_attribute("open") is not None
    page.wait_for_function("![...document.querySelectorAll('#brief-notes .brief-chip-label')].some((n) => n.textContent === 'fougere coumarin')")
    assert "Avoiding: fougere." in page.locator("#brief-notes .brief-notes-extra li").all_inner_texts()

    # A second star while the brief already names one is not written in.
    before = message.input_value()
    _chip(page, "dry wood").locator(".brief-chip-star").click()
    assert message.input_value() == before
    assert page.locator("#brief-notes .brief-notes-status").inner_text() == (
        "The brief already says what the star is. Change that sentence to move it.")

    # Add a note: "With …" goes into the brief.
    add = page.locator("#brief-notes .brief-notes-add input")
    add.fill("iris")
    add.press("Enter")
    assert message.input_value() == f"{BRIEF}. The star is pink pepper. With iris."
    page.wait_for_function("[...document.querySelectorAll('#brief-notes .brief-chip-label')].some((n) => n.textContent.includes('iris'))")
    assert asked[-1]["message"] == f"{BRIEF}. The star is pink pepper. With iris."
    assert asked[-1]["must_avoid"] == ["fougere"]

    assert sideways_scroll(page) == 0
    assert small_targets(page, "#brief-notes") == []
    for theme in ("light", "dark"):
        set_theme(page, theme)
        assert contrast_failures(page, "#brief-notes") == [], theme
        assert contrast_failures(page, ".brief-notes-bar") == [], theme
    set_theme(page, "light")
    shot = os.environ.get("BRIEF_NOTES_SCREENSHOT")
    if shot:
        page.screenshot(path=shot, full_page=True)


def test_closed_chips_ask_nothing_and_typed_words_stay_text(lab):
    asked = _open(lab)
    page = lab.page
    page.locator('#formula-chat-form [name="message"]').fill(f"A rose {EVIL}")
    page.wait_for_timeout(900)
    assert asked == []

    page.click("#brief-notes-toggle")
    _chip(page, "rose").wait_for()
    page.locator("#brief-notes .brief-notes-add input").fill(EVIL)
    page.locator("#brief-notes .brief-notes-add button").click()
    page.wait_for_function("document.querySelector('#formula-chat-form [name=message]').value.endsWith('With <img src=x onerror=alert(1)>.')")
    page.wait_for_timeout(900)

    assert page.locator("#brief-notes img").count() == 0
    page.click("#brief-notes-toggle")
    assert page.is_hidden("#brief-notes")
    count = len(asked)
    page.locator('#formula-chat-form [name="message"]').fill("A lavender")
    page.wait_for_timeout(900)
    assert len(asked) == count


def test_an_avoid_that_contradicts_the_brief_is_said_before_composing(lab):
    _open(lab)
    page = lab.page
    page.locator("#formula-chat-form .optional-details summary").click()
    page.locator('#formula-chat-form [name="must_avoid"]').fill("pepper")
    page.click("#brief-notes-toggle")
    page.wait_for_selector("#brief-notes .brief-notes-status.is-problem")

    assert page.locator("#brief-notes .brief-notes-status").inner_text() == (
        "The brief names a material that Must avoid also lists. Take it out of one of them.")
