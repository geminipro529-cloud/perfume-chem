"""Switching Deep Compose variants keeps unsaved rating and pick input on the Lab card."""

import pytest

from tests.integration.test_lab_ui_liking import (
    _open,
    _result,
    _writes,
    lab_browser,  # noqa: F401  (module fixture)
)

pytest.importorskip("playwright.sync_api")


def _switch(lab, label):
    lab.page.locator("#formula-variant-picker button", has_text=label).click()
    lab.page.locator("#formula-result-variant", has_text=label).wait_for(state="attached")
    lab.page.locator("#formula-result-liking .liking-row").first.wait_for()


def test_typed_rating_and_pick_survive_a_variant_switch_until_saved(lab):
    feedback = _open(lab, _result(variants=True))
    page = lab.page
    row = page.locator('#formula-result-liking .liking-row[data-window="opening"]')
    row.locator('[data-liking="6"]').click()
    row.locator('input[name="note"]').fill("soft start")
    row.locator('select[name="complexity"]').select_option("4")
    row.locator('input[name="too_loud"]').fill("the top")
    pick = page.locator("#formula-result-liking .liking-pick")
    pick.locator('select[name="window"]').select_option("4h")
    pick.locator('input[name="note"]').fill("B felt flatter")

    _switch(lab, "Variant two")
    other = page.locator('#formula-result-liking .liking-row[data-window="opening"]')
    assert other.locator('input[name="note"]').input_value() == ""
    assert other.locator('[aria-pressed="true"]').count() == 0
    other.locator('input[name="note"]').fill("other draft")

    _switch(lab, "Variant one")
    row = page.locator('#formula-result-liking .liking-row[data-window="opening"]')
    page.wait_for_function(
        "document.querySelector('#formula-result-liking .liking-row[data-window=\"opening\"] input[name=note]').value === 'soft start'"
    )
    assert row.locator('[aria-pressed="true"]').get_attribute("data-liking") == "6"
    assert row.locator('select[name="complexity"]').input_value() == "4"
    assert row.locator('input[name="too_loud"]').input_value() == "the top"
    assert row.locator(".liking-save").is_enabled()
    pick = page.locator("#formula-result-liking .liking-pick")
    assert pick.locator('select[name="window"]').input_value() == "4h"
    assert pick.locator('input[name="note"]').input_value() == "B felt flatter"
    assert _writes(feedback) == []

    row.locator(".liking-save").click()
    row.locator(".liking-status", has_text="Saved").wait_for()
    assert [call[:2] for call in _writes(feedback)] == [("POST", "/liking/ratings")]
    assert _writes(feedback)[0][2]["note"] == "soft start"

    _switch(lab, "Variant two")
    _switch(lab, "Variant one")
    row = page.locator('#formula-result-liking .liking-row[data-window="opening"]')
    page.wait_for_timeout(300)
    assert row.locator('input[name="note"]').input_value() == ""
    assert row.locator('[aria-pressed="true"]').count() == 0
    assert row.locator(".liking-status").text_content() == ""
