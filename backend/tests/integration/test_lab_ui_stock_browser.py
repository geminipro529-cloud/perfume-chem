"""The Lab's Stock view, driven in a real browser against a fixture inventory."""

import pytest

pytest.importorskip("playwright.sync_api")

INVENTORY_PATH = "/v2/workbench/current-inventory"


def _stock(name, *, percent="100", basis="neat", carrier=None, ready=True, missing=(), hold=None, completion=False):
    return {
        "stock_id": f"stock-{name.lower()}",
        "identity_name": name,
        "material": name,
        "fraction_percent_decimal": percent,
        "fraction_basis": basis,
        "carrier": carrier,
        "design_ready": ready,
        "missing_fields": list(missing),
        "design_hold_reason": hold,
        "completion_available": completion,
    }


STOCKS = [
    _stock("Ambrox"),
    _stock("Bergamot", percent="10", basis="mass_fraction", carrier="DPG"),
    _stock("Cedar", percent="10", basis="mass_fraction", carrier="ethanol"),
    _stock("Dihydromyrcenol", percent="20", basis="mass_fraction", carrier="DPG", ready=False,
           missing=["fraction_basis"], completion=True),
    _stock("Eugenol", percent="50", basis="mass_fraction", carrier="DPG", ready=False,
           missing=["physical_form", "carrier"], completion=True),
    _stock("Orris", percent="9", basis="mass_fraction", carrier="DEP", ready=False,
           missing=["USER_COMPOUNDING_HOLD", "homogeneity_confirmation"],
           hold="USER_COMPOUNDING_HOLD", completion=True),
    _stock("Galbanum", percent="5", basis="mass_fraction", carrier=None, ready=False,
           missing=["carrier"], completion=True),
    _stock("Hedione"),
]
ALL = sorted(s["identity_name"] for s in STOCKS)
READY = ["Ambrox", "Bergamot", "Cedar", "Hedione"]
NEEDS = ["Dihydromyrcenol", "Eugenol", "Galbanum"]
HOLD = ["Orris"]


@pytest.fixture
def stock(lab):
    lab.respond("GET", INVENTORY_PATH, json={
        "stocks": STOCKS,
        "counts": {"stocks": len(STOCKS), "design_ready": len(READY)},
        "display_source": "Test inventory",
    })
    lab.open("#materials")
    lab.page.locator("#project-inventory-list tbody tr").first.wait_for()
    return lab


def _names(lab):
    return lab.page.locator("#project-inventory-list tbody tr strong").all_inner_texts()


def _row(lab, name):
    return lab.page.locator("#project-inventory-list tbody tr", has=lab.page.locator("strong", has_text=name))


def _filter(lab, key):
    lab.page.locator(f'[data-stock-filter="{key}"]').click()


def _count_line(lab):
    return lab.page.locator("#project-inventory-live").inner_text()


def _clean(lab):
    assert lab.page_errors == []
    assert lab.unexpected == []


def test_filters_show_exactly_their_rows_and_the_count_line_agrees(stock):
    names = _names(stock)
    assert sorted(names) == ALL
    assert len(names) == len(set(names)) == len(STOCKS)
    assert _count_line(stock) == f"Showing {len(STOCKS)} of {len(STOCKS)}"

    for key, expected in (("ready", READY), ("needs", NEEDS), ("hold", HOLD)):
        _filter(stock, key)
        assert stock.page.locator(f'[data-stock-filter="{key}"]').get_attribute("aria-pressed") == "true"
        assert sorted(_names(stock)) == sorted(expected)
        assert _count_line(stock) == f"Showing {len(expected)} of {len(STOCKS)}"

    _filter(stock, "all")
    assert sorted(_names(stock)) == ALL
    assert _count_line(stock) == f"Showing {len(STOCKS)} of {len(STOCKS)}"
    _clean(stock)


def test_held_row_says_on_hold_lists_other_details_and_offers_completion(stock):
    row = _row(stock, "Orris")
    assert row.locator(".stock-chip").inner_text() == "On hold"
    text = row.inner_text()
    assert "Kept out of new formulas until you clear it" in text
    assert "Confirm the solution is fully mixed" in text
    assert "USER_COMPOUNDING_HOLD" not in text
    assert "User Compounding Hold" not in text
    assert row.get_by_role("button", name="Complete details").count() == 1
    _clean(stock)


def test_show_only_details_to_finish_lists_needs_and_held_rows_not_ready(stock):
    stock.page.locator("#project-inventory-incomplete-only").check()
    assert sorted(_names(stock)) == sorted(NEEDS + HOLD)
    assert _count_line(stock) == f"Showing {len(NEEDS + HOLD)} of {len(STOCKS)}"
    for name in READY:
        assert _row(stock, name).count() == 0

    stock.page.locator("#project-inventory-incomplete-only").uncheck()
    assert sorted(_names(stock)) == ALL
    _clean(stock)


def test_neat_solvent_filter_excludes_the_diluted_stock_with_no_carrier(stock):
    select = stock.page.locator("#project-inventory-solvent")
    options = select.locator("option").all_inner_texts()
    assert "Neat" in options
    assert "Solvent not recorded" in options

    select.select_option("neat")
    assert sorted(_names(stock)) == ["Ambrox", "Hedione"]
    assert _row(stock, "Galbanum").count() == 0

    select.select_option("unrecorded")
    assert _names(stock) == ["Galbanum"]
    assert _count_line(stock) == f"Showing 1 of {len(STOCKS)}"
    _clean(stock)


def test_sort_reorders_rows_without_dropping_any(stock):
    assert _names(stock) == ALL

    stock.page.locator("#project-inventory-sort").select_option("needs")
    by_needs = _names(stock)
    assert by_needs == NEEDS + HOLD + READY
    assert sorted(by_needs) == ALL

    stock.page.locator("#project-inventory-sort").select_option("strength")
    by_strength = _names(stock)
    assert sorted(by_strength) == ALL
    assert by_strength[:2] == ["Ambrox", "Hedione"]
    assert by_strength[2:4] == ["Eugenol", "Dihydromyrcenol"]
    assert by_strength[-1] == "Galbanum"
    _clean(stock)


def test_table_rows_show_dilutions_gate_holds_and_workbook_differences(lab):
    # The Stock page entries (PR #43) inside the redesigned table (PR #24).
    parent = dict(_stock("Iso E Super"), dilution_available=True)
    made = dict(
        _stock("Iso E Super 10% w/w in DPG", percent="10", basis="mass_fraction", carrier="DPG"),
        source_class="PREPARED_DILUTION",
        gate_hold_text="Held at the gate: its parent bottle changed after this dilution",
    )
    differs = dict(
        _stock("Hedione", percent="50", basis="mass_fraction", carrier="DPG"),
        authority_disagreement={"text": "Differs from the workbook: workbook says neat"},
    )
    lab.respond("GET", INVENTORY_PATH, json={
        "stocks": [parent, made, differs],
        "counts": {"stocks": 3, "design_ready": 3, "prepared_dilutions": 1},
        "display_source": "Test inventory",
    })
    lab.open("#materials")
    lab.page.locator("#project-inventory-list tbody tr").first.wait_for()

    assert lab.page.locator("#project-inventory-ready").inner_text() == (
        "3 ready to use · 1 dilutions you made"
    )
    made_row = _row(lab, "Iso E Super 10% w/w in DPG").inner_text()
    assert "Your dilution" in made_row
    assert "Held at the gate: its parent bottle changed after this dilution" in made_row
    assert "Differs from the workbook: workbook says neat" in _row(lab, "Hedione").inner_text()
    assert lab.page.get_by_role("button", name="Add a dilution").count() == 1

    lab.page.get_by_role("button", name="Add a dilution").click()
    panel = lab.page.locator("#stock-dilution-panel")
    panel.wait_for()
    assert "Iso E Super" in panel.inner_text()
    _clean(lab)
