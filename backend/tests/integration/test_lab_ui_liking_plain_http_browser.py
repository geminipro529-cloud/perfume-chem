"""A rating saves on a page the browser doesn't treat as secure.

Browsers give crypto.subtle only to https and localhost pages: the Lab opened
over Wi-Fi on a phone has none, and Playwright's headless shell (the default on
Windows) ignores the flag that makes the test origin secure. This module uses the
shared plain-http browser on purpose, so the page has to make the key itself.
"""

import hashlib
import re

import pytest

from tests.integration.test_lab_ui_liking import ROWS, _canonical, _open, _result, _writes

pytest.importorskip("playwright.sync_api")


def test_rating_saves_with_the_same_key_where_the_browser_has_no_crypto_subtle(lab):
    feedback = _open(lab, _result())
    assert lab.page.evaluate("Boolean(globalThis.crypto && globalThis.crypto.subtle)") is False
    row = lab.page.locator('#formula-result-liking .liking-row[data-window="opening"]')
    row.locator('[data-liking="7"]').click()
    row.locator(".liking-save").click()
    row.locator(".liking-status", has_text=re.compile(r"^Saved$")).wait_for()
    method, path, body = _writes(feedback)[-1]
    assert (method, path) == ("POST", "/liking/ratings")
    assert body["liking"] == 7
    assert body["formula_key"] == hashlib.sha256(_canonical(ROWS).encode()).hexdigest()
