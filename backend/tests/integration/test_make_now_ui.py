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


BUY_LIST = """
const offer = (sku, extra) => ({ offer_key: `pw:${sku}`, shop: "PW", sku, title: "Moonflower Abs", form: "neat",
  usd_per_g: "7.3", observed_on: "2026-04-11", observed_label: "11 Apr", match: "probable", tickable: true,
  upfront_usd: "37.40", upfront_thb: "1254.77", default_pack_g: "5", cost_per_bottle_thb: { min: "29.3898", max: "29.3898" },
  product_url: "https://www.perfumersworld.com/view.php?pro_id=" + sku, ...extra });
const unknown = offer("4JD02734", { match: "unknown", tickable: false, usd_per_g: null, upfront_usd: null, cost_per_bottle_thb: null });
const buyList = {
  buy_first: [
    { material_key: "moonflower", material: "Moon Flower", cards: [
        { formula_id: "other", material: "Moon Flower" }, { formula_id: "f1", material: "  MOONFLOWER " }],
      offers: [unknown, offer("7WX21054")] },
    { material_key: "orris", material: "Orris", cards: [{ formula_id: "f1", material: "Orris" }], offers: [unknown] },
  ],
  on_the_way: [{ shop: "PW", order_id: "PW-1", ordered_on: "2026-10-15", lines: [{ material_key: "ambrette", material: "Ambrette Seed" }] }],
};
"""


def test_a_not_owned_line_finds_its_buy_first_row_by_formula_and_its_own_row_text():
    result = _run(BUY_LIST + """
        const pick = (match) => match && (match.kind === "offer" ? [match.kind, match.offer.sku, match.material] : [match.kind, match.shop, match.orderedOn]);
        const notTickable = { ...buyList, buy_first: [{ ...buyList.buy_first[0], offers: [unknown, offer("2PR00002", { tickable: false }), offer("7WX21054")] }] };
        const firstPriced = { ...buyList, buy_first: [{ ...buyList.buy_first[0], offers: [unknown, offer("2PR00002", { tickable: false })] }] };
        return {
          own: pick(m.makeBuyMatch("Moonflower", ["f1"], buyList)),
          otherCard: pick(m.makeBuyMatch("moon flower", ["other"], buyList)),
          wrongCard: m.makeBuyMatch("Moonflower", ["f9"], buyList),
          wrongText: m.makeBuyMatch("Moon Flower", ["f1"], buyList),
          tickableFirst: pick(m.makeBuyMatch("Moonflower", ["f1"], notTickable)),
          pricedElse: pick(m.makeBuyMatch("Moonflower", ["f1"], firstPriced)),
          noPrice: m.makeBuyMatch("Orris", ["f1"], buyList),
          onTheWay: pick(m.makeBuyMatch("ambrette seed", [], buyList)),
          noList: m.makeBuyMatch("Moonflower", ["f1"], null),
        };
    """)

    assert result["own"] == ["offer", "7WX21054", "Moon Flower"]
    assert result["otherCard"] == ["offer", "7WX21054", "Moon Flower"]
    # Another card's spelling, or another card's need, is not this line's.
    assert result["wrongCard"] is None and result["wrongText"] is None
    assert result["tickableFirst"] == ["offer", "7WX21054", "Moon Flower"]
    assert result["pricedElse"] == ["offer", "2PR00002", "Moon Flower"]
    assert result["noPrice"] is None
    assert result["onTheWay"] == ["on_the_way", "PW", "2026-10-15"]
    assert result["noList"] is None


def test_the_buy_line_reads_like_the_buy_page_and_drops_baht_without_a_rate():
    result = _run(BUY_LIST + """
        const match = m.makeBuyMatch("Moonflower", ["f1"], buyList);
        const noRate = { ...match, offer: { ...match.offer, upfront_thb: null, cost_per_bottle_thb: null } };
        return [m.makeBuyLineText(match), m.makeBuyLineText(noRate),
                m.makeBuyLineText(m.makeBuyMatch("Ambrette Seed", [], buyList)), m.makeBuyLineText(null)];
    """)

    assert result == [
        "PW 7WX21054: US$7.30/g, 11 Apr, ฿29 a bottle",
        "PW 7WX21054: US$7.30/g, 11 Apr",
        "On the way (PW, ordered 15 Oct)",
        "",
    ]


def test_only_not_in_your_stock_yet_lines_carry_a_buy_match_and_on_the_way_is_never_stock():
    result = _run(BUY_LIST + """
        const ambrette = { ...formula, formula_id: "f2", rows: [{ material: "Ambrette Seed", amount: "20", fraction: "1" }] };
        const tag = (f) => m.makeCheck(m.makeNeeds(f, stocks, "30").needs, {}).map((i) => ({ ...i, formulaId: f.formula_id }));
        const items = [tag(formula), tag(ambrette)];
        const withList = m.makeShopping(items, { onHand: {}, prices: {}, densities: {}, buyList });
        const without = m.makeShopping(items, { onHand: {}, prices: {}, densities: {} });
        const lines = (list) => list.groups.flatMap((g) => g.items.map((l) => [g.supplier, l.material, l.buy && l.buy.kind]));
        return { withList: lines(withList), without: lines(without), ask: withList.ask.length };
    """)

    assert result["withList"] == [
        ["Not in your stock yet", "Ambrette Seed", "on_the_way"],
        ["Not in your stock yet", "Moonflower", "offer"],
    ]
    assert result["without"] == [
        ["Not in your stock yet", "Ambrette Seed", None],
        ["Not in your stock yet", "Moonflower", None],
    ]
    assert result["ask"] == 4
