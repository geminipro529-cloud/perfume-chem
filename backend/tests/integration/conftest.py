"""Shared fixtures for integration tests."""

import pytest


@pytest.fixture(scope="module")
def lab_browser():
    """One headless Chromium per test module; skips when Playwright is not installed.

    Module scope, not session: Playwright's sync API keeps its event loop marked as
    running until it stops, which breaks async fixtures in later test modules."""
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.integration.lab_browser import chromium_executable

    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chromium_executable(playwright))
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def lab(lab_browser):
    """A fresh Lab page (``tests.integration.lab_browser.LabPage``), not yet opened."""
    from tests.integration.lab_browser import LabPage

    context = lab_browser.new_context()
    page = LabPage(context.new_page())
    try:
        yield page
        # Every test fails on a JS error or an API call with no fixture; a test that
        # expects one clears the list itself.
        assert not page.page_errors, f"JS errors on the Lab page: {page.page_errors}"
        assert not page.unexpected, f"API calls with no fixture: {page.unexpected}"
    finally:
        context.close()
