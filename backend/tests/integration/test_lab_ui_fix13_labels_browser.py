"""Phone tap targets are at least 44 px tall, and every dose row shows its basket label."""

import re

import pytest

pytest.importorskip("playwright.sync_api")

INVENTORY_PATH = "/v2/workbench/current-inventory"
VIEWS = ["improve", "formulas", "materials", "bottles", "experiments", "dashboard", "perfumery", "assistant", "science"]

# Deliberately not measured: the skip link (only on screen while focused), the
# screen-reader-only class, and anything the page itself hides (zero size,
# visibility:hidden, [hidden]).
MEASURE = """
() => {
  const out = [];
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && el.closest("[hidden]") === null;
  };
  const note = (kind, box) => {
    if (!visible(box) || box.closest(".skip-link") || box.classList.contains("skip-link") || box.classList.contains("sr-only")) return;
    out.push({ kind, text: (box.textContent || box.name || box.id || "").trim().slice(0, 40), height: box.getBoundingClientRect().height });
  };
  document.querySelectorAll("button, select, summary").forEach((el) => note(el.tagName.toLowerCase(), el));
  document.querySelectorAll("[data-stock-filter]").forEach((el) => note("chip", el));
  document.querySelectorAll("input[type=checkbox], input[type=radio]").forEach((el) => {
    const label = el.closest("label") || (el.id && document.querySelector(`label[for="${el.id}"]`));
    if (!label) { out.push({ kind: "unlabelled-" + el.type, text: el.name || el.id, height: 0 }); return; }
    note(el.type + "-label", label);
  });
  return out;
}
"""

DESKTOP_PROBE = """
() => {
  const h = (sel) => { const el = document.querySelector(sel); return el ? el.getBoundingClientRect().height : null; };
  return {
    theme: h("#theme-select"), chip: h("[data-stock-filter]"),
    complete: h(".inventory-complete-button"), summary: h(".optional-details summary"),
  };
}
"""

OPEN_ALL_DETAILS = "document.querySelectorAll('details').forEach((d) => { d.open = true; })"


def _stock(name, complete=True):
    return {
        "stock_id": f"stock-{name.lower()}", "identity_name": name, "material": name,
        "fraction_percent_decimal": "10", "fraction_basis": "mass_fraction", "carrier": "DPG",
        "design_ready": not complete, "missing_fields": ["carrier"] if complete else [],
        "design_hold_reason": None, "completion_available": complete, "basket": None, "basket_status": "none",
    }


def _open_stock(lab):
    stocks = [_stock("Ambrox", False), _stock("Bergamot"), _stock("Cedar")]
    lab.respond("GET", INVENTORY_PATH, json={"stocks": stocks, "counts": {"stocks": 3}, "display_source": "Test"})
    lab.open("#materials")
    lab.page.locator("#project-inventory-list tbody tr").first.wait_for()


SCIENCE = {
    "totals": {"section_count": 1, "total_records": 1, "included_records": 1, "withheld_records": 0},
    "sections": [{
        "label": "Facts", "total_count": 1, "withheld": [],
        "included": [{
            "id": "rec-1", "evidence_class": "MEASURED", "strict_eligible": True, "strict_reason_codes": [],
            "created_at": "2026-01-01", "authority": {}, "provenance": {}, "facts": {},
        }],
    }],
}


def test_phone_controls_are_at_least_44px_tall_on_every_view(lab):
    lab.page.set_viewport_size({"width": 390, "height": 844})
    lab.respond("GET", "/science/authority?view=strict", json=SCIENCE)
    _open_stock(lab)
    too_small = []
    seen = 0
    for view in VIEWS:
        lab.page.evaluate(f"location.hash = '#{view}'")
        lab.page.wait_for_function(f"document.querySelector('[data-view={view}]').getAttribute('aria-current') === 'page'")
        lab.page.evaluate(OPEN_ALL_DETAILS)
        for item in lab.page.evaluate(MEASURE):
            seen += 1
            if item["height"] < 43.99:
                too_small.append((view, item["kind"], item["text"], round(item["height"], 1)))
    assert seen > 40
    assert too_small == []
    lab.page.evaluate("location.hash = '#materials'")
    assert lab.page.locator(".inventory-complete-button").count() >= 2
    assert lab.page.locator("#project-inventory-incomplete-only").count() == 1


def test_clicking_anywhere_in_a_phone_checkbox_or_radio_label_toggles_it(lab):
    lab.page.set_viewport_size({"width": 390, "height": 844})
    _open_stock(lab)
    box = lab.page.locator("label", has=lab.page.locator("#project-inventory-incomplete-only"))
    rect = box.bounding_box()
    box.click(position={"x": rect["width"] - 4, "y": rect["height"] - 4})
    assert lab.page.locator("#project-inventory-incomplete-only").is_checked()

    lab.page.evaluate("location.hash = '#experiments'")
    lab.page.evaluate(OPEN_ALL_DETAILS)
    radio = lab.page.locator('label:has(input[name="change_kind"][value="ADDITION"])')
    rect = radio.bounding_box()
    radio.click(position={"x": rect["width"] - 4, "y": rect["height"] - 4})
    assert lab.page.locator('input[name="change_kind"][value="ADDITION"]').is_checked()


def test_desktop_control_sizes_are_unchanged(lab):
    lab.page.set_viewport_size({"width": 1280, "height": 900})
    _open_stock(lab)
    lab.page.evaluate("location.hash = '#improve'")
    lab.page.evaluate(OPEN_ALL_DETAILS)
    summary = lab.page.evaluate(DESKTOP_PROBE)["summary"]
    lab.page.evaluate("location.hash = '#materials'")
    sizes = lab.page.evaluate(DESKTOP_PROBE)
    assert sizes["theme"] == 36
    assert sizes["chip"] == 40
    assert sizes["complete"] == 40
    assert round(summary) == 21


# -- Fix 2 ---------------------------------------------------------------------

STOCKS = [
    {"stock_id": "s-hed", "material": "Hedione", "basket": 1, "basket_status": "confirmed"},
    {"stock_id": "s-ced", "material": "Cedarwood Atlas", "basket": 3, "basket_status": "from_past_cards"},
    {"stock_id": "s-cal", "material": "Calone", "basket": None, "basket_status": "none"},
    {"stock_id": "s-mus", "material": "Muscenone", "basket": None, "basket_status": "none"},
]
NAMES = {1: "Always used", 3: "Woods"}


def _row(material, amount, stock_id, operation="DIRECT_ADD"):
    return {
        "material": material, "amount_decimal": amount, "amount_unit": "uL", "stock_id": stock_id,
        "stock_label": f"{material} 10%", "stock_fraction_decimal": "0.1", "fraction_basis": "mass_fraction",
        "carrier": "DPG", "operation": operation, "execution_ready": True, "slot_label": "slot",
        "role": "role", "note": "heart", "rationale": f"why {material}",
    }


# 12 rows: assigned, unassigned and one carrier pre-charge.
ROWS = [_row("Calone", "15", "s-cal"), _row("Hedione", "40", "s-hed"), _row("Cedarwood Atlas", "120", "s-ced"),
        _row("Muscenone", "25", "s-mus"), _row("Ethanol", "300", "s-eth", "PRECHARGE")]
ROWS += [_row(f"Pad {i}", str(10 + i), "s-hed" if i % 2 else "s-cal") for i in range(7)]
RESULT = {
    "formula_name": "Label test", "assistant_message": "Draft.",
    "optimized_formula": {"rows": ROWS, "separate_totals": {"liquid_total_ul": "900", "mass_total_mg": "0"}},
    "critic": {"state": "PASS", "issues": []},
}


def _create(lab):
    baskets = [{"number": n, "name": NAMES.get(n, f"Basket name {n}")} for n in range(1, 18)]
    lab.respond("GET", INVENTORY_PATH, json={"stocks": STOCKS, "counts": {}, "baskets": baskets})
    lab.respond("POST", "/v2/workbench/formula-chat", json=RESULT)
    lab.open("#formulas")
    lab.page.locator('#formula-chat-form textarea[name="message"]').fill("a label test")
    lab.page.locator("#formula-chat-submit").click()
    lab.page.locator("#formula-chat-result").wait_for()


def test_create_table_labels_unassigned_rows_with_no_basket(lab):
    _create(lab)
    rows = lab.page.locator("#formula-result-rows tr:not(.formula-basket-row)")
    seen = {}
    for i in range(rows.count()):
        row = rows.nth(i)
        material = row.locator("td strong").inner_text()
        tags = row.locator("td").first.locator("small.formula-basket-tag").all_inner_texts()
        seen[material] = (tags, row.locator(".formula-dose").inner_text())
    assert seen["Hedione"][0] == ["Basket 1"]
    assert seen["Cedarwood Atlas"][0] == ["Basket 3"]
    assert seen["Calone"][0] == ["No basket"]
    assert seen["Muscenone"][0] == ["No basket"]
    assert seen["Pad 0"][0] == ["No basket"]
    assert seen["Ethanol"][0] == []  # carrier pre-charge rows keep their treatment
    assert "120 uL" in seen["Cedarwood Atlas"][1] and "15 uL" in seen["Calone"][1]
    headings = lab.page.locator("#formula-result-rows tr.formula-basket-row th").all_inner_texts()
    assert [h.split(" check")[0].strip() for h in headings] == [
        "Carriers and solvents · pre-charge", "Basket 1 · Always used", "Basket 3 · Woods", "No basket yet"]
    order = lab.page.locator("#formula-result-rows tr:not(.formula-basket-row) td strong").all_inner_texts()
    assert order.index("Hedione") < order.index("Cedarwood Atlas") < order.index("Calone")


def test_bench_sheet_labels_unassigned_rows_and_still_prints_on_one_a4_page(lab):
    lab.page.add_init_script("window.print = () => {};")
    _create(lab)
    lab.page.locator("#formula-print-bench").click()
    tags = {}
    for tr in lab.page.locator("#bench-sheet tbody tr:not(.bench-basket-row)").all():
        tags[tr.locator("td strong").inner_text()] = tr.locator("small.bench-basket-tag").all_inner_texts()
    assert tags["Hedione"] == ["Basket 1"]
    assert tags["Calone"] == ["No basket"]
    assert tags["Muscenone"] == ["No basket"]
    assert tags["Ethanol"] == []
    assert len(tags) == 12
    sheet_headings = lab.page.locator("#bench-sheet tr.bench-basket-row th").all_inner_texts()
    assert sheet_headings[-1].split(" · check")[0] == "No basket yet"
    amounts = lab.page.locator("#bench-sheet tbody tr:not(.bench-basket-row) td.bench-amount:nth-child(5)").all_inner_texts()
    assert "120 uL" in [a.strip() for a in amounts]

    lab.page.emulate_media(media="print")
    pdf = lab.page.pdf(format="A4", prefer_css_page_size=True)
    assert len(re.findall(rb"/Type\s*/Page[^s]", pdf)) == 1
