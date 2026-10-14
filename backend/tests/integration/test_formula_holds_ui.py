"""What's missing under a HOLD: the rows the page sends and what it shows (node)."""

from pathlib import Path

from tests.integration.test_formula_editor import _editor
from tests.integration.test_lab_ui import _node_json

STATIC = Path(__file__).resolve().parents[2] / "app" / "static"
HOLD_LIST_JS = STATIC / "hold-list.js"


def test_the_composers_rows_are_sent_with_their_stock_strength_and_unit():
    result = _node_json(HOLD_LIST_JS, """(m) => m.holdRowsFromDesign([
        { material: "Hedione", stock_id: "s-1", amount_decimal: "1200", amount_unit: "uL",
          stock_fraction_decimal: "1", fraction_basis: "neat", carrier: "None" },
        { material: "Cashmeran", stock_id: "s-2", amount_decimal: "150.5", amount_unit: "uL",
          stock_fraction_decimal: "0.2", fraction_basis: "mass_fraction", carrier: "DPG" },
        { material: "Ambrofix Crystals", stock_id: null, amount_decimal: "40", amount_unit: "mg",
          stock_fraction_decimal: null, fraction_basis: "", carrier: null },
        { material: "Nothing", amount_decimal: "0", amount_unit: "uL" },
        { material: "In grams", amount_decimal: "2", amount_unit: "g" },
        { material: "", amount_decimal: "50", amount_unit: "uL" },
    ])""")

    assert result == [
        {"material": "Hedione", "stock_id": "s-1", "amount": "1200", "unit": "uL", "fraction": "1", "basis": "neat", "carrier": ""},
        {"material": "Cashmeran", "stock_id": "s-2", "amount": "150.5", "unit": "uL", "fraction": "0.2",
         "basis": "mass_fraction", "carrier": "DPG"},
        {"material": "Ambrofix Crystals", "stock_id": None, "amount": "40", "unit": "mg", "fraction": "1", "basis": "", "carrier": ""},
    ]


def test_each_item_keeps_its_words_and_only_a_stock_page_item_gets_the_button():
    result = _node_json(HOLD_LIST_JS, """(m) => m.holdListView({
        summary: "1 stock to sort out.", basis: "From the checks.",
        items: [
            { id: "hold-1", check: "stock", material: "Hedione HC", reason: "Its details are not complete: confirm you own it.",
              action: "Open it on the Stock page and fill those in.", open: { kind: "stock_page", stock_id: "s-9" } },
            { id: "hold-2", check: "ifra", material: "Clearwood", reason: "Not counted.", action: "Ask the supplier.", open: null,
              owner: "claude" },
            { id: "hold-3", check: "ifra", material: "", reason: "The IFRA check could not run.", action: "Send it.", open: { kind: "elsewhere" },
              owner: "someone else" },
        ],
    })""")

    assert result["summary"] == "1 stock to sort out."
    assert [(i["check"], i["material"], i["stockId"]) for i in result["items"]] == [
        ("Stock", "Hedione HC", "s-9"), ("IFRA", "Clearwood", ""), ("IFRA", "The formula", ""),
    ]
    # Whose move it is: only "claude" marks Claude's part; anything else, or nothing, is Kenny's.
    assert [(i["owner"], i["ownerText"]) for i in result["items"]] == [
        ("you", "For you"), ("claude", "Claude's part"), ("you", "For you"),
    ]


def test_the_editor_sends_each_row_with_its_bound_stock_and_leaves_ethanol_out():
    result = _editor("""() => {
        const rows = [
            { ...row("Hedione", "600", { fraction: "1", basis: "neat" }), stockId: "s-1" },
            row("Iso E Super", "1000/3", { fraction: "0.1", basis: "mass_fraction", carrier: "DPG" }),
            { ...row("Ambrofix", "25", { fraction: "", solid: true }), stockId: "s-3" },
            row("Ethanol", "24000"),
            row("", "10"), row("Linalool", null),
        ];
        rows[1] = { ...rows[1], amount: { n: 1000n, d: 3n } };
        return editor.editorHoldRows(rows);
    }""")

    assert result == [
        {"material": "Hedione", "stock_id": "s-1", "amount": "600", "unit": "uL", "fraction": "1", "basis": "neat", "carrier": ""},
        {"material": "Iso E Super", "stock_id": None, "amount": "333.333333", "unit": "uL", "fraction": "0.1",
         "basis": "mass_fraction", "carrier": "DPG"},
        {"material": "Ambrofix", "stock_id": "s-3", "amount": "25", "unit": "mg", "fraction": "1", "basis": "", "carrier": ""},
    ]
