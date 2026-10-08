import re

import pytest


@pytest.mark.asyncio
async def test_theme_stylesheet_is_served_after_lab_css_with_dark_mode_and_focus(client):
    page = await client.get("/app")
    theme = await client.get("/static/theme.css")

    assert page.status_code == 200
    assert theme.status_code == 200
    lab_link = '<link rel="stylesheet" href="/static/lab.css">'
    theme_link = '<link rel="stylesheet" href="/static/theme.css">'
    assert lab_link in page.text
    assert theme_link in page.text
    assert page.text.index(lab_link) < page.text.index(theme_link)
    assert '<meta name="color-scheme" content="light dark">' in page.text

    assert "prefers-color-scheme: dark" in theme.text
    assert ':root[data-theme="dark"]' in theme.text
    assert ':root:not([data-theme="light"])' in theme.text
    assert ":focus-visible" in theme.text
    assert ".paper-grid { display: none; }" in theme.text
    assert "http://" not in theme.text
    assert "https://" not in theme.text
    assert "@import" not in theme.text


@pytest.mark.asyncio
async def test_navigation_is_grouped_with_skip_link_and_theme_picker(client):
    page = await client.get("/app")
    html = page.text

    assert '<a class="skip-link" href="#main-content">Skip to content</a>' in html
    assert '<main id="main-content">' in html
    assert 'id="theme-select"' in html
    for value in ("system", "light", "dark"):
        assert f'<option value="{value}">' in html

    rail = html.split('<nav class="rail"', 1)[1].split("</nav>", 1)[0]
    groups = re.findall(r'<p class="nav-group">([^<]+)</p>', rail)
    assert groups == ["Bench", "Records", "Reference"]
    views = re.findall(r'data-view="([a-z]+)"', rail)
    assert views == [
        "improve", "formulas", "materials", "bottles",
        "experiments", "dashboard",
        "perfumery", "assistant", "science",
    ]
    assert '<button class="nav-item is-active" data-view="improve">' in rail
    assert "rail-note" not in rail


@pytest.mark.asyncio
async def test_navigation_marks_current_page_and_theme_choice_persists(client):
    javascript = await client.get("/static/lab.js")
    source = javascript.text

    navigate = source.split("function navigate(view) {", 1)[1].split("\n}\n", 1)[0]
    assert 'setAttribute("aria-current", "page")' in navigate
    assert 'removeAttribute("aria-current")' in navigate
    assert '"perfumechem.theme"' in source
    assert "localStorage.getItem(THEME_KEY)" in source
    assert "localStorage.setItem(THEME_KEY" in source
    assert 'meta[name="theme-color"]' in source
