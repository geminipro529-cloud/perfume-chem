"""The Create table follows Kenny's basket order when the inventory carries baskets."""

import pytest

pytest.importorskip("playwright.sync_api")


STOCKS = [
    {"stock_id": "s-hed", "material": "Hedione", "basket": 1, "basket_status": "confirmed"},
    {"stock_id": "s-iso", "material": "Iso E Super", "basket": 1, "basket_status": "confirmed"},
    {"stock_id": "s-ced", "material": "Cedarwood Atlas", "basket": 3, "basket_status": "from_past_cards"},
    {"stock_id": "s-ros", "material": "Rose Oxide", "basket": 10, "basket_status": "confirmed"},
    {"stock_id": "s-cal", "material": "Calone", "basket": None, "basket_status": "none"},
]


def _baskets():
    names = {1: "Always used", 3: "Woods", 10: "Rose"}
    return [{"number": number, "name": names.get(number, f"Basket name {number}")} for number in range(1, 18)]


def _row(material, amount, stock_id):
    return {
        "material": material, "amount_decimal": amount, "amount_unit": "uL", "stock_id": stock_id,
        "stock_label": f"{material} 10%", "stock_fraction_decimal": "0.1", "fraction_basis": "mass_fraction",
        "carrier": "DPG", "operation": "DIRECT_ADD", "execution_ready": True, "slot_label": "slot",
        "role": "role", "note": "heart", "rationale": f"why {material}",
    }


ROWS = [
    _row("Rose Oxide", "30", "s-ros"),
    _row("Calone", "15", "s-cal"),
    _row("Hedione", "40", "s-hed"),
    _row("Cedarwood Atlas", "120", "s-ced"),
    _row("Iso E Super", "250", "s-iso"),
]

RESULT = {
    "formula_name": "Basket test",
    "assistant_message": "Here is a draft.",
    "optimized_formula": {"rows": ROWS, "separate_totals": {"liquid_total_ul": "455", "mass_total_mg": "0"}},
    "critic": {"state": "PASS", "issues": []},
}


def _create(lab, inventory):
    lab.respond("GET", "/v2/workbench/current-inventory", json=inventory)
    lab.respond("POST", "/v2/workbench/formula-chat", json=RESULT)
    lab.open("#formulas")
    lab.page.locator('#formula-chat-form textarea[name="message"]').fill("a rose and cedar test")
    lab.page.locator("#formula-chat-submit").click()
    lab.page.locator("#formula-chat-result").wait_for()
    return lab.page.locator("#formula-result-rows tr")


def test_create_table_groups_rows_by_basket_and_flags_small_pours(lab):
    rows = _create(lab, {"stocks": STOCKS, "counts": {}, "baskets": _baskets()})

    texts = [text.strip() for text in rows.all_inner_texts()]
    headings = [text for text, cls in zip(texts, [rows.nth(i).get_attribute("class") or "" for i in range(rows.count())]) if "formula-basket-row" in cls]
    assert headings == ["Basket 1 · Always used", "Basket 3 · Woods check it: from past cards", "Basket 10 · Rose", "No basket yet"]
    materials = lab.page.locator("#formula-result-rows td strong").all_inner_texts()
    assert materials == ["Iso E Super", "Hedione", "Cedarwood Atlas", "Rose Oxide", "Calone"]
    assert lab.page.locator("#formula-result-rows tr.formula-basket-row th").first.get_attribute("colspan") == "4"
    calone_dose = lab.page.locator("#formula-result-rows tr", has_text="Calone").locator(".formula-dose").inner_text()
    assert "Under 20 µL: dilute 1:1 in ethanol, pipette double" in calone_dose
    assert "Basket 1" in lab.page.locator("#formula-result-rows tr", has_text="Iso E Super").locator("td").first.inner_text()
    assert lab.page_errors == []
    assert lab.unexpected == []


def test_create_table_keeps_design_order_without_basket_data(lab):
    _create(lab, {"stocks": STOCKS, "counts": {}})

    assert lab.page.locator("#formula-result-rows tr.formula-basket-row").count() == 0
    materials = lab.page.locator("#formula-result-rows td strong").all_inner_texts()
    assert materials == [row["material"] for row in ROWS]
    assert lab.page_errors == []
