"""Lab messages read as plain words: no stale offline notice, no raw server wording, 422 items kept apart."""

import re

import pytest

pytest.importorskip("playwright.sync_api")

from tests.integration.test_lab_ui_basket_stock_browser import (  # noqa: E402
    BASKET_PATH,
    _capture_post,
    _clean,
    _open,
    _rows,
)

OFFLINE = "Can't reach the app on this PC. Is it still running?"


def _text(box):
    return re.sub(r"\s+", " ", box.inner_text()).strip()


def _status(lab):
    node = lab.page.locator("#status")
    return node.inner_text().strip(), "is-error" in (node.get_attribute("class") or "").split()


def _refresh(lab):
    """Press Refresh ledger and wait for the page to say it finished."""
    count = sum(1 for entry in lab.status_history() if entry["text"] == "Inventory and ledger refreshed.")
    lab.page.evaluate("document.getElementById('refresh-all').click()")
    lab.page.wait_for_function(
        "(count) => window.__statusHistory.filter((e) => e.text === 'Inventory and ledger refreshed.').length > count",
        arg=count,
        timeout=3000,
    )


def _submit_bottle(lab, label="Test bottle"):
    form = lab.page.locator("#bottle-form")
    form.locator('input[name="label"]').fill(label)
    form.locator('button[type="submit"]').click()


def _bottle_error(lab, status, body):
    lab.respond("POST", "/bottles", status=status, json=body)
    _submit_bottle(lab)
    box = lab.page.locator("#bottle-form-error")
    box.wait_for()
    return box


# -- Fix 1 ---------------------------------------------------------------------------------------
def test_offline_message_is_cleared_on_status_and_basket_row_by_a_later_success(lab):
    _open(lab)
    lab.fail("POST", BASKET_PATH)
    _rows(lab, "Cedar").locator("select").select_option("5")
    row = _rows(lab, "Cedar")
    row.locator(".stock-basket-error").wait_for()
    assert row.locator(".stock-basket-error").inner_text() == f"Basket not saved: {OFFLINE}"
    assert _status(lab) == (f"Basket not saved for Cedar: {OFFLINE}", True)

    _refresh(lab)  # the server is back

    assert _rows(lab, "Cedar").locator(".stock-basket-error").count() == 0
    assert _status(lab) == ("Inventory and ledger refreshed.", False)
    _clean(lab)


def test_offline_message_in_the_form_box_is_cleared_too(lab):
    lab.open("#bottles")
    lab.fail("POST", "/bottles")
    _submit_bottle(lab)
    lab.page.locator("#bottle-form-error").wait_for()
    assert OFFLINE in lab.page.locator("#bottle-form-error").inner_text()

    _refresh(lab)

    assert lab.page.locator("#bottle-form-error").count() == 0
    assert _status(lab) == ("Inventory and ledger refreshed.", False)


def test_another_error_message_survives_a_later_success(lab):
    _open(lab)
    _capture_post(lab, status=422, reply={"detail": "That basket does not exist."})
    _rows(lab, "Cedar").locator("select").select_option("5")
    _rows(lab, "Cedar").locator(".stock-basket-error").wait_for()

    lab.page.evaluate("document.getElementById('refresh-all').click()")
    lab.page.wait_for_timeout(500)  # the refresh has answered; its routine message must not replace the error

    assert _rows(lab, "Cedar").locator(".stock-basket-error").inner_text() == "Basket not saved: That basket does not exist."
    assert _status(lab) == ("Basket not saved for Cedar: That basket does not exist.", True)
    _clean(lab)


# -- Fix 2 ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("detail, shown", [
    ("'Unknown sample: abc'", "Unknown sample: abc"),
    ('"Unknown sample: abc"', "Unknown sample: abc"),
    ("'Unmatched", "'Unmatched"),
])
def test_quotes_around_server_text_are_stripped(lab, detail, shown):
    lab.open("#bottles")
    box = _bottle_error(lab, 404, {"detail": detail})
    assert _text(box) == f"Not saved. {shown}"
    assert _status(lab) == (shown, True)


def test_long_server_text_is_capped_at_200_characters(lab):
    lab.open("#bottles")
    box = _bottle_error(lab, 400, {"detail": "x" * 5000})
    text, is_error = _status(lab)
    assert is_error and len(text) == 200 and text.endswith("…") and set(text[:-1]) == {"x"}
    assert _text(box) == f"Not saved. {text}"


def test_conflict_text_is_capped_at_200_characters_with_its_prefix(lab):
    lab.open("#bottles")
    _bottle_error(lab, 409, {"detail": "y" * 5000})
    text, is_error = _status(lab)
    assert is_error and len(text) == 200 and text.startswith("That already exists. ") and text.endswith("…")


@pytest.mark.parametrize("raw, plain", [
    ("Field required", "required"),
    ("String should have at least 1 character", "required"),
    ("String should have at most 2000 characters", "too long (at most 2000 characters)"),
    ("Input should be greater than or equal to 0", "must be 0 or more"),
    ("Input should be greater than 0.5", "must be more than 0.5"),
    ("Input should be less than or equal to 10", "must be 10 or less"),
    ("Input should be less than 10", "must be less than 10"),
    ("Input should be a valid number, unable to parse string as a number", "must be a number"),
    ("Input should be a finite number", "must be a number"),
    ("Value error, something odd", "Value error, something odd"),
])
def test_pydantic_wording_becomes_plain_words(lab, raw, plain):
    lab.open("#bottles")
    box = _bottle_error(lab, 422, {"detail": [{"loc": ["body", "label"], "msg": raw, "type": "x"}]})
    text = _text(box)
    assert text.startswith("Not saved. ")
    assert text.endswith(f": {plain}")
    assert _status(lab) == (text[len("Not saved. "):], True)


# -- Fix 3 ---------------------------------------------------------------------------------------
def _add_inputs(lab, names):
    lab.page.evaluate("""(names) => {
      const form = document.getElementById('bottle-form');
      for (const name of names) {
        const input = document.createElement('input');
        input.name = name;
        form.prepend(input);
      }
    }""", names)


def test_two_422_items_are_joined_with_a_semicolon(lab):
    lab.open("#bottles")
    _add_inputs(lab, ["note", "experiment_id"])
    detail = [
        {"loc": ["body", "note"], "msg": "String should have at most 2000 characters", "type": "x"},
        {"loc": ["body", "experiment_id"], "msg": "Field required", "type": "x"},
    ]
    box = _bottle_error(lab, 422, {"detail": detail})
    text = _text(box)
    assert text.startswith("Not saved. ")
    sentences = text[len("Not saved. "):].split("; ")
    assert len(sentences) == 2
    assert sentences[0].endswith(": too long (at most 2000 characters)")
    assert sentences[1].endswith(": required")
    assert _status(lab) == (text[len("Not saved. "):], True)
    assert box.locator("br").count() == 0


@pytest.mark.parametrize("names, marked", [
    (["outcome.note", "note"], "outcome.note"),
    (["note"], "note"),
])
def test_nested_location_marks_the_matching_field(lab, names, marked):
    lab.open("#bottles")
    _add_inputs(lab, names)
    _bottle_error(lab, 422, {"detail": [{"loc": ["body", "outcome", "note"], "msg": "Field required", "type": "x"}]})
    flagged = lab.page.eval_on_selector_all(
        "#bottle-form [aria-invalid]", "(nodes) => nodes.map((node) => node.name)"
    )
    assert flagged == [marked]
    assert lab.page.locator(f'#bottle-form [name="{marked}"]').get_attribute("aria-describedby") == "bottle-form-error"
