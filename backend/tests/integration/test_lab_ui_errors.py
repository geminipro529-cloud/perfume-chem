"""The Lab page shows errors next to the button that caused them."""

import re

from fastapi.testclient import TestClient

from app.main import app


def _js() -> str:
    response = TestClient(app).get("/static/lab.js")
    assert response.status_code == 200
    return response.text


def test_form_errors_are_placed_next_to_the_button_and_accessible():
    js = _js()
    assert 'box.className = "form-error"' in js
    assert 'setAttribute("role", "alert")' in js
    assert 'setAttribute("aria-invalid", "true")' in js
    assert 'setAttribute("aria-describedby", id)' in js
    assert 'strong.textContent = "Not saved."' in js
    assert "innerHTML" not in js[js.index("function showFormError"): js.index("function bindForm")]


def test_request_translates_failures_into_plain_words():
    js = _js()
    assert "AbortController" in js
    assert "Can't reach the app on this PC. Is it still running?" in js
    assert "The app didn't answer within 30 seconds." in js
    assert "That already exists." in js
    assert "The server returned ${response.status}." in js
    assert "error.fields" in js
    # Engine polling keeps its own timeout.
    assert "{ timeoutMs: ENGINE_POLL_REQUEST_TIMEOUT_MS }" in js


def test_routine_refresh_does_not_overwrite_an_error():
    js = _js()
    assert "function notifyRoutine" in js
    assert 'notifyRoutine("Inventory and ledger refreshed.")' in js
    assert 'notify("Inventory and ledger refreshed.")' not in js


def test_no_direct_random_uuid_outside_request_id_helper():
    js = _js()
    helper = js.index("const newRequestId")
    helper_end = js.index(";", js.index("Math.random", helper))
    outside = js[:helper] + js[helper_end:]
    assert "crypto.randomUUID" not in outside
    assert len(re.findall(r"newRequestId\(", js)) >= 7
