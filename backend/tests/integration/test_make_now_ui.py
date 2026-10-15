"""What can I make: the needs per bottle, what is short, and the shopping list (node)."""

from pathlib import Path

from tests.integration.test_lab_ui import _node_json

MAKE_NOW_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "make-now.js"

SETUP = """
const stocks = [
  { stock_id: "s-hed", identity_name: "Hedione", material: "Hedione", fraction_percent_decimal: "100", fraction_basis: "neat", carrier: null },
  { stock_id: "s-ro10", identity_name: "Rose Oxide", material: "Rose Oxide", fraction_percent_decimal: "10", fraction_basis: "mass_fraction", carrier: "DPG" },
  { stock_id: "s-ro1", identity_name: "Rose Oxide", material: "Rose Oxide", fraction_percent_decimal: "1", fraction_basis: "mass_fraction", carrier: "DPG" },
  { stock_id: "s-amb", identity_name: "Ambrox", material: "Ambrox", fraction_percent_decimal: "100", fraction_basis: "neat", carrier: null },
  { stock_id: "s-iso10", identity_name: "Iso E Super", material: "Iso E Super", fraction_percent_decimal: "10", fraction_basis: "mass_fraction",
    carrier: "DPG", source_class: "PREPARED_DILUTION" },
];
const formula = { formula_id: "f1", name: "Rose Test", version: 2, bottle_ml: "15", rows: [
  { material: "Hedione", stock_id: "s-hed", amount: "600", fraction: "1" },
  { material: "Hedione", stock_id: "s-hed", amount: "1000/3", fraction: "1" },
  { material: "Rose Oxide", stock_id: null, amount: "50", fraction: "0.1", basis: "mass_fraction", carrier: "DPG" },
  { material: "Ambrox", stock_id: "s-amb", amount: "120", fraction: "1", solid: true },
  { material: "Ethanol", amount: "10000" },
  { material: "Moonflower", amount: "30", fraction: "1" },
  { material: "Iso E Super", stock_id: "s-iso10", amount: "500", fraction: "0.1" },
]};
"""


def _run(body):
    return _node_json(MAKE_NOW_JS, f"(m) => {{ {SETUP} {body} }}")


def test_each_formula_is_scaled_to_the_bottle_and_summed_per_stock_without_ethanol():
    result = _run("""
        const needs = m.makeNeeds(formula, stocks, "30");
        const asWritten = m.makeNeeds({ ...formula, bottle_ml: "" }, stocks, "30");
        return {
          scaled: needs.scaled,
          needs: needs.needs.map((n) => [n.material, n.stockId, m.makeAmountText(n.need, n.unit)]),
          asWritten: [asWritten.scaled, m.makeAmountText(asWritten.needs[0].need, "mL")],
        };
    """)

    assert result["scaled"] is True
    # Hedione (600 + 1000/3) µL x 2; Rose Oxide matched by name at the row's 10%; Ambrox in g.
    assert result["needs"] == [
        ["Hedione", "s-hed", "1.87 mL"],
        ["Rose Oxide", "s-ro10", "0.1 mL"],
        ["Ambrox", "s-amb", "0.24 g"],
        ["Moonflower", None, "0.06 mL"],
        ["Iso E Super", "s-iso10", "1 mL"],
    ]
    assert result["asWritten"] == [False, "0.93 mL"]


def test_each_stock_is_enough_short_unknown_or_missing_and_the_formula_says_which():
    result = _run("""
        const onHand = { "s-hed": { amount_decimal: "1", unit: "mL" }, "s-ro10": { amount_decimal: "5", unit: "mL" },
                         "s-amb": { amount_decimal: "2", unit: "mL" } };
        const items = m.makeCheck(m.makeNeeds(formula, stocks, "30").needs, onHand);
        const enough = m.makeCheck(m.makeNeeds({ ...formula, rows: formula.rows.slice(2, 3) }, stocks, "30").needs, onHand);
        return { lines: items.map((i) => [i.status, m.makeLineText(i)]), verdict: m.makeVerdict(items, "30"),
                 ok: m.makeVerdict(enough, "30"), unknown: m.makeVerdict(items.filter((i) => i.status === "unknown"), "30") };
    """)

    assert result["lines"] == [
        ["short", "Hedione: needs 1.87 mL; 1 mL left, short by 0.87 mL."],
        ["enough", "Rose Oxide: needs 0.1 mL; 5 mL left."],
        ["unknown", "Ambrox: needs 0.24 g; you typed how much is left in mL."],
        ["missing", "Moonflower: needs 0.06 mL; not in your stock."],
        ["unknown", "Iso E Super: needs 1 mL; how much is left?"],
    ]
    assert result["verdict"] == {"status": "short", "text": "Short of 2 stocks for 30 mL, and 2 stocks still need how much is left."}
    assert result["ok"] == {"status": "ok", "text": "You can mix it at 30 mL."}
    assert result["unknown"] == {"status": "unknown", "text": "Type how much is left of 2 stocks to know."}


def test_the_shopping_list_sums_formulas_groups_by_supplier_and_prices_with_your_prices():
    result = _run("""
        const onHand = { "s-hed": { amount_decimal: "1", unit: "mL", supplier: "PerfumersWorld" },
                         "s-ro10": { amount_decimal: "0.05", unit: "mL", supplier: "Aroma & More" },
                         "s-amb": { amount_decimal: "0", unit: "g" }, "s-iso10": { amount_decimal: "0", unit: "mL" } };
        const prices = { "s-hed": { per_unit: "mL", price_decimal: "10", currency: "THB" },
                         "s-ro10": { per_unit: "g", pack_price: "120", pack_size: "10", price_decimal: "12", currency: "THB" } };
        const items = m.makeCheck(m.makeNeeds(formula, stocks, "30").needs, onHand);
        return { list: m.makeShopping([items, items], { onHand, prices, densities: {} }),
                 densityNames: m.makeDensityNames([items], prices) };
    """)

    shopping = result["list"]
    assert shopping["ask"] == []
    assert [(g["supplier"], g["subtotalText"]) for g in shopping["groups"]] == [
        ("Aroma & More", "1.84 THB"),
        ("PerfumersWorld", "27.33 THB"),
        ("Not in your stock yet", ""),
        ("Supplier not set", ""),
        ("Make yourself", ""),
    ]
    lines = {line["material"]: line for group in shopping["groups"] for line in group["items"]}
    # Two bottles of Hedione: 3.73 mL less 1 mL left, at 10 THB per mL.
    assert (lines["Hedione"]["buyText"], lines["Hedione"]["costText"]) == ("2.73 mL", "27.33 THB")
    # Rose Oxide 10% w/w in DPG priced per g (120 THB for 10 g): 0.15 mL weighed with the
    # dilution's density estimate, 1 / (0.1 / 1 + 0.9 / 1.023) g/mL, is 0.153 g, so 1.84 THB.
    assert (lines["Rose Oxide"]["buyText"], lines["Rose Oxide"]["costText"]) == ("0.15 mL", "1.84 THB")
    assert lines["Ambrox"]["buyText"] == "0.48 g" and lines["Ambrox"]["reason"] == "no price yet"
    assert lines["Iso E Super"]["reason"] == "your own dilution: make more"
    assert lines["Moonflower"]["costText"] == ""
    assert shopping["totalText"] == "29.17 THB"
    assert shopping["unpriced"] == 2
    assert result["densityNames"] == ["Rose Oxide"]


def test_a_stock_whose_amount_is_unknown_is_asked_for_before_it_is_bought():
    result = _run("""
        const items = m.makeCheck(m.makeNeeds(formula, stocks, "30").needs, {});
        return m.makeShopping([items], { onHand: {}, prices: {}, densities: {} });
    """)

    assert [(item["material"], item["needText"]) for item in result["ask"]] == [
        ("Hedione", "1.87 mL"), ("Rose Oxide", "0.1 mL"), ("Ambrox", "0.24 g"), ("Iso E Super", "1 mL"),
    ]
    assert [g["supplier"] for g in result["groups"]] == ["Not in your stock yet"]
    assert result["totalText"] == ""
