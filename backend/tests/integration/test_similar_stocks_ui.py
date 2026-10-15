"""Similar you own and the shelf map (node): a swap keeps the material a row carries,
and the lists say "similar, not the same"."""

from pathlib import Path

from tests.integration.test_formula_editor import _editor
from tests.integration.test_lab_ui import _node_json

SIMILAR_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "similar-stocks.js"

STOCKS = """
const stock = (stock_id, material, fraction_decimal, fraction_basis, carrier = null, extra = {}) =>
  ({ stock_id, material, identity_name: material, fraction_decimal, fraction_basis, carrier, status: "owned", ...extra });
const hed = stock("s-hed", "Hedione", "1", "neat");
const iso = stock("s-iso", "Iso E Super", "1", "neat");
const ro10 = stock("s-ro10", "Rose Oxide", "0.1", "mass_fraction", "DPG");
const ro1 = stock("s-ro1", "Rose Oxide", "0.01", "mass_fraction", "DPG");
const cash20 = stock("s-c20", "Cashmeran", "0.2", "mass_fraction", "DPG");
const cash = stock("s-c", "Cashmeran", "1", "neat");
const amb = stock("s-amb", "Ambrox", "1", "neat", null, { physical_form: "crystals" });
const ambf = stock("s-ambf", "Ambrofix", "1", "neat", null, { physical_form: "crystals" });
const swap = (r, s, d) => { const out = editor.editorSwapRow(r, s, d); return out && { ...R([out.row])[0], byGrams: out.byGrams }; };
"""


def test_a_swap_keeps_the_grams_of_material_when_both_densities_are_known_else_the_written_strengths():
    result = _editor("""() => {
        """ + STOCKS + """
        const densities = { Hedione: "0.999", "Iso E Super": "0.9612", Cashmeran: "1.0", "Rose Oxide": null };
        const hedRow = editor.editorBindRow(row("Hedione", "600"), hed);
        const roRow = editor.editorBindRow(row("Rose Oxide", "30"), ro10);
        const cashRow = editor.editorBindRow(row("Cashmeran", "100"), cash20);
        const ambRow = editor.editorBindRow(row("Ambrox", "120", { solid: true }), amb);
        return {
          byDensity: swap(hedRow, iso, densities),
          byStrength: swap(roRow, ro1, densities),
          rebase: swap(cashRow, cash, densities),
          solid: swap(ambRow, ambf, densities),
          otherForm: swap(ambRow, iso, densities),
          liquidToSolid: swap(hedRow, ambf, densities),
          empty: swap(editor.editorBindRow(row("Hedione", null), hed), iso, densities),
        };
    }""")

    # 600 µL x 0.999 g/mL of Hedione = 599.4 g/L of material; Iso E Super neat at 0.9612 g/mL.
    assert result["byDensity"] == {"material": "Iso E Super", "amount": "55500/89", "solid": False, "grams": None,
                                   "fraction": "1", "stockId": "s-iso", "note": "", "byGrams": True}
    # Rose Oxide's density is not known: 30 µL of the 10% stock is 300 µL of the 1% one by the written strengths.
    assert (result["byStrength"]["amount"], result["byStrength"]["fraction"], result["byStrength"]["byGrams"]) == ("300/1", "0.01", False)
    # Cashmeran 20% w/w in DPG to neat: 100 µL x 1 / (0.2 / 1.0 + 0.8 / 1.023) g/mL x 0.2 = 20.37 µL of neat.
    assert (result["rebase"]["amount"], result["rebase"]["byGrams"]) == ("102300/5023", True)
    assert (result["solid"]["material"], result["solid"]["amount"], result["solid"]["solid"], result["solid"]["byGrams"]) == (
        "Ambrofix", "120/1", True, True)
    assert result["otherForm"] is None and result["liquidToSolid"] is None and result["empty"] is None


def test_the_list_says_what_each_material_shares_and_offers_only_the_stocks_that_fit():
    result = _node_json(SIMILAR_JS, """(m) => {
        const answer = { stock: { identity_name: "Iso E Super" }, label: "similar, not the same", basis: "By written profile.",
          same_material: [{ stock_id: "s-iso10", stock_label: "Iso E Super 10% in DPG" }],
          similar: [
            { identity_name: "Kephalis", closeness: "close", shares: ["woody", "transparent"], differs: ["less radiant", "more warm"],
              stocks: [{ stock_id: "s-kep", stock_label: "Kephalis neat" }] },
            { identity_name: "Woody Base", closeness: "some", shares: [], differs: [], profile_from_category: true,
              stocks: [{ stock_id: "s-wb", stock_label: "Woody Base" }, { stock_id: "s-gone", stock_label: "Old bottle" }] },
          ] };
        const choice = (line) => line.stock_id === "s-gone" ? null
          : line.stock_id === "s-wb" ? { label: "Woody Base · Neat solid", why: "weighed in mg, this row is poured" }
          : { label: line.stock_label, stockId: line.stock_id };
        return {
          view: m.similarView(answer, choice),
          named: m.similarView(answer).similar[1].stocks,
          blank: m.similarView({ stock: { identity_name: "Mystery" }, no_profile: true, similar: [] }).empty,
          none: m.similarView({ stock: { identity_name: "Hedione" }, similar: [] }).empty,
          join: [m.similarJoin([]), m.similarJoin(["a"]), m.similarJoin(["a", "b", "c"])],
        };
    }""")

    view = result["view"]
    assert view["label"] == "similar, not the same"
    assert view["same"] == [{"label": "Iso E Super 10% in DPG", "stockId": "s-iso10"}]
    assert view["similar"][0] == {"name": "Kephalis", "closeness": "Close", "line": "Both woody and transparent; less radiant, more warm.",
                                  "stocks": [{"label": "Kephalis neat", "stockId": "s-kep"}]}
    assert view["similar"][1]["line"] == "Its profile is only its category's."
    assert view["similar"][1]["stocks"] == [{"label": "Woody Base · Neat solid", "why": "weighed in mg, this row is poured"}]
    assert [stock["label"] for stock in result["named"]] == ["Woody Base", "Old bottle"]
    assert result["blank"] == "Mystery has no written character in the Lab yet, so nothing can be compared with it."
    assert result["none"] == "Nothing else on your shelf is written alike enough."
    assert result["join"] == ["", "a", "a, b and c"]


def test_the_shelf_map_lists_thin_facets_fewest_first_and_pairs_written_alike():
    result = _node_json(SIMILAR_JS, """(m) => {
        const answer = {
          stocks: [{ identity_name: "Iso E Super", x: 0, y: 1, leads_with: "woody", leads_with_word: "woody" },
                   { identity_name: "Hedione", x: 1, y: 0, leads_with: "", leads_with_word: "" }],
          facets: [{ facet: "woody", word: "woody", count: 9, leaders: [] }, { facet: "powdery", word: "powdery", count: 2, leaders: ["Irotyl", "Orris Liquid"] },
                   { facet: "radiance", word: "radiant", count: 0, leaders: [] }],
          written_alike: [{ a: "Hedione", b: "Hedione HC", shares: ["floral", "fresh"] }],
          unplaced: ["Mystery Base"], basis: "By written profile.",
          axes: { x: { low: "warm", high: "fresh" }, y: { low: "woody", high: "floral" } } };
        const view = m.shelfView(answer, 300);
        return { dots: view.dots.map((d) => [d.name, d.x, d.y]), thin: view.thin.map(m.shelfThinText),
                 alike: view.alike.map(m.shelfAlikeText), unplaced: view.unplaced, axes: view.axes,
                 noAxes: m.shelfAxesText({ x: { low: "warm" } }) };
    }""")

    # Dots sit inside a 12 px margin, the map's y running up.
    assert result["dots"] == [["Iso E Super", 12, 12], ["Hedione", 288, 288]]
    assert result["thin"] == ["radiant: none of your materials leads with it.", "powdery: only Irotyl and Orris Liquid."]
    assert result["alike"] == ["Hedione and Hedione HC: both floral and fresh."]
    assert result["unplaced"] == ["Mystery Base"]
    assert result["axes"] == "Left to right: more warm to more fresh. Bottom to top: more woody to more floral."
    assert result["noAxes"] == ""
