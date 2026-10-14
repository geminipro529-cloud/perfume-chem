"""Edit a formula at phone size: why each row is there, and what changes without it."""

import json
import os

import pytest

from tests.integration.lab_a11y import (
    contrast_failures,
    set_theme,
    sideways_scroll,
    small_targets,
    stop_smooth_scrolling,
)
from tests.integration.test_formula_editor_browser import _load_card, _open

pytest.importorskip("playwright.sync_api")

ROSE = {"id": "facet_rose", "kind": "note", "label": "rose", "star": False}
INFOS = {
    "Hedione": ([], ["radiance", "transparency", "floral"]),
    "Rose Oxide": ([{**ROSE, "by": "name"}], ["floral"]),
    "Iso E Super": ([], ["woody", "transparency", "radiance"]),
    "Ambrox": ([], ["warmth", "transparency", "radiance"]),
}
STAGES = ("opening", "top", "heart", "late_heart", "drydown")


def _roles(body):
    rows = []
    for row in body["rows"]:
        carries, profile = INFOS.get(row["material"], ([], []))
        rows.append({"material": row["material"], "stock_id": row["stock_id"], "found": row["material"] in INFOS,
                     "carries": carries, "profile": profile})
    return {"schema_version": "brief-notes-v1", "formula_name": body["formula_name"], "rows": rows,
            "notes": [{**ROSE, "words": ["rose"], "layer": "heart"}]}


def _curve(rows):
    """A curve led by the largest active amounts, so leaving a row out changes the leaders."""
    active = {row["identity_name"]: row["amount_ul"] * row["stock_fraction"] for row in rows}
    total = sum(active.values())
    names = sorted(active, key=lambda name: -active[name])
    window = lambda label: {"label": label, "effective_voices": len(names), "top": names[:3], "materials": [  # noqa: E731
        {"name": name, "known": True, "oav": 1.0, "share": active[name] / total, "note": "heart"} for name in names]}
    return {"schema_version": "scent-curve-v1", "windows": [window(label) for label in STAGES]}


def _start(lab):
    asked = []

    def roles(route, request):
        body = json.loads(request.post_data)
        asked.append(body)
        route.fulfill(status=200, content_type="application/json", body=json.dumps(_roles(body)))

    def scent(route, request):
        route.fulfill(status=200, content_type="application/json", body=json.dumps(_curve(json.loads(request.post_data)["rows"])))

    lab.page.set_viewport_size({"width": 390, "height": 844})
    _open(lab)
    lab.on("POST", "/v2/workbench/formula-roles", roles)
    lab.on("POST", "/v2/workbench/scent-curve", scent)
    stop_smooth_scrolling(lab.page)
    _load_card(lab)
    return asked


def _why(lab):
    return lab.page.eval_on_selector_all(
        "#editor-rows .editor-why", "(nodes) => nodes.map((node) => node.hidden ? null : node.querySelector('.editor-why-text').textContent)")


def test_each_row_says_which_of_the_names_notes_its_stock_carries(lab):
    asked = _start(lab)
    page = lab.page
    assert _why(lab) == [None] * 5
    assert asked == []

    page.click("#editor-why")
    page.wait_for_function("document.querySelector('#editor-why-line').textContent.startsWith('The name asks for')")

    assert page.get_attribute("#editor-why", "aria-pressed") == "true"
    assert asked == [{"formula_name": "Rose Test", "rows": [
        {"material": "Hedione", "stock_id": "s-hed"}, {"material": "Rose Oxide", "stock_id": "s-ro10"},
        {"material": "Iso E Super", "stock_id": "s-iso"}, {"material": "Ambrox", "stock_id": "s-amb"},
        {"material": "Velvet Musk", "stock_id": None},
    ]}]
    assert page.text_content("#editor-why-line") == (
        "The name asks for rose. Each row says which of these its stock carries: by its own name, or only by its odor words.")
    assert _why(lab) == [
        "None of the name's notes; its own profile: radiance, transparency, floral.",
        "Carries the rose.",
        "None of the name's notes; its own profile: woody, transparency, radiance.",
        "None of the name's notes; its own profile: warmth, transparency, radiance.",
        "Not in your stock list, so what it carries is not known.",
    ]
    assert page.get_attribute("#editor-rows tr:nth-child(2) [data-action=without]", "aria-label") == "What changes without Rose Oxide"
    assert page.evaluate("localStorage.getItem('lab.editor.why')") == "on"
    assert sideways_scroll(page) == 0
    assert small_targets(page, "#editor-rows") == []
    for theme in ("light", "dark"):
        set_theme(page, theme)
        assert contrast_failures(page, "#editor-rows") == [], theme
        assert contrast_failures(page, ".editor-tools") == [], theme
    set_theme(page, "light")

    # A new name is read again; the same rows and name are not asked twice.
    page.fill("#editor-name", "Rose Musk")
    page.press("#editor-name", "Tab")
    page.wait_for_function("document.querySelector('#editor-why-line').textContent.startsWith('The name asks for')")
    page.wait_for_timeout(700)
    assert [body["formula_name"] for body in asked] == ["Rose Test", "Rose Musk"]

    page.click("#editor-why")
    assert page.get_attribute("#editor-why", "aria-pressed") == "false"
    assert page.is_hidden("#editor-why-line")
    assert _why(lab) == [None] * 5


def test_without_it_previews_the_checks_and_the_smell_then_removes_or_keeps_the_row(lab):
    _start(lab)
    page = lab.page
    page.click("#editor-why")
    page.wait_for_function("document.querySelector('#editor-why-line').textContent.startsWith('The name asks for')")

    page.click("#editor-rows tr:nth-child(1) [data-action=without]")
    page.wait_for_selector("#editor-drop .editor-drop-actions")

    drop = page.locator("#editor-drop")
    assert page.evaluate("document.activeElement.id") == "editor-drop"
    assert drop.locator("h3").inner_text() == "Without Hedione"
    assert drop.locator("p").first.inner_text() == "It carries none of the notes the name asks for."
    lists = drop.locator("ul")
    checks = lists.nth(0).locator("li").all_inner_texts()
    assert any(text.startswith("Oil: 3.5% → ") for text in checks), checks
    smell = lists.nth(1).locator("li").all_inner_texts()
    assert smell == [
        "Opening to 4 hours: Hedione, Iso E Super, Velvet Musk → Iso E Super, Velvet Musk, Rose Oxide",
        "With it, Hedione is 61% of what the model can detect at 30 minutes and 61% at 4 hours.",
    ]
    assert "not by strength or pleasantness" in drop.inner_text()
    assert sideways_scroll(page) == 0
    assert small_targets(page, "#editor-drop") == []
    for theme in ("light", "dark"):
        set_theme(page, theme)
        assert contrast_failures(page, "#editor-drop") == [], theme
    set_theme(page, "light")
    shot = os.environ.get("EDITOR_WHY_SCREENSHOT")
    if shot:
        page.screenshot(path=shot, full_page=True)

    # Keep it: the preview goes and focus goes back to the row's button.
    drop.locator("[data-drop=keep]").click()
    assert page.is_hidden("#editor-drop")
    assert page.evaluate("document.activeElement.getAttribute('aria-label')") == "What changes without Hedione"
    assert page.input_value("#editor-rows tr:nth-child(1) [data-field=material]") == "Hedione · Neat"

    # Remove the row: one step, and Undo puts it back.
    page.click("#editor-rows tr:nth-child(2) [data-action=without]")
    page.wait_for_selector("#editor-drop .editor-drop-actions")
    assert drop.locator("p").first.inner_text() == "It carries the rose the name asks for."
    drop.locator("[data-drop=remove]").click()
    assert page.is_hidden("#editor-drop")
    assert page.locator("#editor-rows tr[data-key]").count() == 4
    page.click("#editor-undo")
    assert page.locator("#editor-rows tr[data-key]").count() == 5
    assert page.input_value("#editor-rows tr:nth-child(2) [data-field=material]") == "Rose Oxide · 10% w/w in DPG"


def test_a_preview_closes_when_the_rows_change_under_it(lab):
    _start(lab)
    page = lab.page
    page.click("#editor-why")
    page.wait_for_function("document.querySelector('#editor-why-line').textContent.startsWith('The name asks for')")
    page.click("#editor-rows tr:nth-child(3) [data-action=without]")
    page.wait_for_selector("#editor-drop .editor-drop-actions")

    page.fill("#editor-rows tr:nth-child(1) [data-field=amount]", "500")
    page.press("#editor-rows tr:nth-child(1) [data-field=amount]", "Enter")

    assert page.is_hidden("#editor-drop")
