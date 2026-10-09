"""The Stock view is one filterable table written in bottle-label words."""

import re

import pytest


@pytest.mark.asyncio
async def test_stock_view_is_a_filterable_label_table(client):
    page = (await client.get("/app")).text
    script = (await client.get("/static/lab.js")).text

    for needle in (
        'id="project-inventory-solvent"',
        'id="project-inventory-sort"',
        'class="stock-filters" role="group" aria-label="Show"',
        'data-stock-filter="all"',
        'data-stock-filter="ready"',
        'data-stock-filter="needs"',
        'data-stock-filter="hold"',
        'id="project-inventory-incomplete-only"',
        'id="project-inventory-live"',
        "Source details",
    ):
        assert needle in page, needle

    list_tag = re.search(r'<div id="project-inventory-list"[^>]*>', page).group(0)
    assert "aria-live" not in list_tag
    live_tag = re.search(r'<p id="project-inventory-live"[^>]*>', page).group(0)
    assert 'aria-live="polite"' in live_tag

    for needle in (
        '"stock-table"',
        '"stock-table-wrap"',
        "dataset.stockStatus",
        "stock-chip stock-chip-",
        "stock-row-note",
        '"w/w"',
        '"v/v"',
        "w/w or v/v not stated",
        "Neat crystals, weighed in mg",
        "Added by you",
        "Kept out of new formulas until you clear it",
        "Confirm you own it",
        "Add the bottle lot and label",
        "dataset.completeStock",
    ):
        assert needle in script, needle
    # The table is built from DOM nodes, never from HTML strings of data.
    body = script[script.index("function renderProjectInventory") :]
    body = body[: body.index("async function refresh")]
    assert "innerHTML" not in body
