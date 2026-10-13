"""Thai label and IFRA Category 4 self-declaration, from synthetic gate results only."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app.services.commercial_label import (
    LABEL_DRAFT_BANNER,
    STATEMENT_DRAFT_BANNER,
    TO_FILL,
    CommercialPackError,
    build_ifra_statement,
    build_label,
)

BATCH_LABEL_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "batch-label.js"

COMPLETE_FIELDS = {
    "name": "Test Bloom",
    "type": "eau_de_parfum",
    "thai_name": "เทสต์ บลูม",
    "manufacturer_name": "Example Maker",
    "manufacturer_address": "1 Example Road, Bangkok 10100",
    "lot": "TB-001",
    "mfg": "10/2026",
    "notification_no": "10-1-0000000000",
}


def _row(material, limit, actual, status="restricted", verdict="pass"):
    return {
        "material": material, "ifra_status": status, "standard": "IFRA_STD_900",
        "actual_pct": actual, "limit_pct": limit, "effective_limit_pct": limit,
        "usage_pct": None if limit is None else round(actual / limit * 100, 1),
        "verdict": verdict, "message": f"{material} message",
    }


def _gate(status, **data):
    base = {
        "violations": [], "headroom_violations": [], "warnings": [], "holds": [],
        "undisclosed_bases": [], "banned": [], "allergen_declarations": [],
        "rows": [_row("Alpha Ketone", 0.5, 0.1), _row("Plain Musk", None, 1.0, "no_standard")],
        "groups": [{
            "material": "IFRA_STD_901_constituents", "group": "IFRA_STD_901_constituents",
            "standard": "IFRA_STD_901", "members": {"Example Absolute": 0.002},
            "actual_pct": 0.002, "limit_pct": 0.1, "verdict": "pass",
        }],
        "constituent_totals": [{"substance": "Examplol", "standard": "IFRA_STD_901"}],
        "batch_volume_ml": 30.0, "batch_volume_source": "formula_title",
        "concentration_basis": "finished_product_w_w_estimate",
        "ifra_table": {"amendment_in_force": 51, "category": "4", "verified_on": "2026-10-08"},
    }
    base.update(data)
    return {"formulas": [{
        "name": "Synthetic formula",
        "formula_state": {"total_raw_ul": 4500.0, "batch_volume_ml": 30.0},
        "gates": [
            {"gate": "other_gate", "status": "FAIL", "data": {}},
            {"gate": "safety_ifra_allergen", "status": status, "detail": "d", "data": base},
        ],
    }]}


META = {"lot": "TB-001", "date": "13/10/2026", "manufacturer_name": "Example Maker"}


def test_pass_gate_conforms_with_every_limited_row_and_group():
    statement = build_ifra_statement(_gate("PASS"), META)

    assert statement["verdict"] == "Conforms"
    assert statement["draft"] is False and statement["draft_banner"] is None
    assert statement["title"] == (
        "IFRA Conformity Certificate — 51st Amendment, Category 4 (fine fragrance)"
    )
    assert "not a certificate issued by IFRA" in statement["declaration"]
    names = [row["name"] for row in statement["rows"]]
    assert names == ["Alpha Ketone", "Examplol (constituents of naturals)"]
    assert statement["rows"][0]["pct_of_limit"] == 20.0
    assert statement["rows"][1]["detail"] == "Example Absolute 0.002 %"
    assert statement["fragrance_concentration_pct"] == 15.0
    assert "ifra_cat4_51.json" in statement["limits_source"]


def test_hold_gate_is_draft_listing_unrecognised_material_and_undisclosed_base():
    gate = _gate(
        "HOLD",
        holds=[_row("Lemon Oil X", None, 0.07, status=None, verdict="unchecked")],
        undisclosed_bases=[{"material": "Captive Wood", "actual_pct": 0.7}],
        warnings=[_row("Rose Abs X", None, 0.1, status="natural_no_own_standard", verdict="warn")],
    )

    statement = build_ifra_statement(gate, META)

    assert statement["verdict"] == "Not yet determined"
    assert statement["draft"] is True
    assert statement["draft_banner"] == STATEMENT_DRAFT_BANNER
    kinds = {(item["kind"], item["material"]) for item in statement["open_items"]}
    assert kinds == {
        ("not_in_table", "Lemon Oil X"),
        ("base_composition_unknown", "Captive Wood"),
        ("natural_constituents", "Rose Abs X"),
    }
    assert all("supplier's IFRA certificate" in item["text"] for item in statement["open_items"])


def test_warn_gate_alone_is_still_a_draft():
    statement = build_ifra_statement(
        _gate("WARN", allergen_declarations=["Linalool"]), META
    )
    assert statement["verdict"] != "Conforms" and statement["draft"] is True
    assert [item["kind"] for item in statement["open_items"]] == ["allergen_declarations"]


def test_fail_gate_lists_violations_and_never_conforms():
    over = _row("Alpha Ketone", 0.5, 0.8, verdict="fail")
    over["message"] = "Alpha Ketone at 0.8 % is over the IFRA Category 4 limit of 0.5 %."
    statement = build_ifra_statement(
        _gate("FAIL", violations=[over], headroom_violations=[over], banned=["Banned Thing"]),
        META,
    )
    assert statement["verdict"] == "Does not conform"
    assert statement["draft"] is True
    assert [f["material"] for f in statement["failures"]] == ["Alpha Ketone", "Banned Thing"]


def test_pass_status_with_a_violation_does_not_conform():
    over = _row("Alpha Ketone", 0.5, 0.8, verdict="fail")
    statement = build_ifra_statement(_gate("PASS", violations=[over]), META)
    assert statement["verdict"] == "Does not conform"


def test_statement_missing_lot_and_date_is_a_draft_even_when_passing():
    statement = build_ifra_statement(_gate("PASS"), {"manufacturer_name": "M"})
    assert statement["verdict"] == "Conforms"
    assert statement["draft"] is True
    assert statement["lot"] == TO_FILL and statement["date"] == TO_FILL


def test_other_amendment_is_an_open_item():
    gate = _gate("PASS", ifra_table={"amendment_in_force": 50, "category": "4"})
    statement = build_ifra_statement(gate, META)
    assert statement["verdict"] == "Not yet determined"
    assert statement["open_items"][0]["kind"] == "table_mismatch"


@pytest.mark.parametrize("status", ["SKIP", "ERROR", ""])
def test_a_gate_that_did_not_pass_never_conforms_even_with_nothing_listed(status):
    statement = build_ifra_statement(_gate(status), META)
    assert statement["verdict"] == "Not yet determined"
    assert statement["draft"] is True
    assert [item["kind"] for item in statement["open_items"]] == ["gate_status"]


@pytest.mark.parametrize("bad", [{}, {"formulas": []}, {"formulas": [{"gates": []}]}, []])
def test_statement_refuses_gate_results_without_the_ifra_gate(bad):
    with pytest.raises(CommercialPackError):
        build_ifra_statement(bad, META)


def test_statement_refuses_unknown_meta():
    with pytest.raises(CommercialPackError):
        build_ifra_statement(_gate("PASS"), {"lot": "L", "colour": "red"})


def test_complete_label_is_not_a_draft_and_carries_the_thai_lines():
    label = build_label(COMPLETE_FIELDS, [{"material": "Iso E Super", "volume_ul": 4500}])

    assert label["draft"] is False and label["draft_banner"] is None
    assert label["front"] == ["Test Bloom", "Eau de Parfum", "น้ำหอม", "30 มล. / 30 mL"]
    thai = {line["label"]: line["text"] for line in label["thai"]}
    assert thai["ชื่อเครื่องสำอาง"] == "Test Bloom Eau de Parfum (เทสต์ บลูม)"
    assert thai["ส่วนประกอบ"] == "Alcohol, Parfum (Fragrance)"
    assert thai["ผลิตโดย"] == "Example Maker 1 Example Road, Bangkok 10100 ประเทศไทย"
    assert "วันหมดอายุ" not in thai
    assert label["english"][-1] == "Thai FDA notification no.: 10-1-0000000000"
    assert label["type"]["concentration_pct"] == 15.0
    assert "No law sets a percentage" in label["type"]["note"]
    assert TO_FILL not in json.dumps(label, ensure_ascii=False)


@pytest.mark.parametrize("field", ["notification_no", "manufacturer_name", "lot", "mfg",
                                   "manufacturer_address"])
def test_each_print_field_missing_makes_a_draft_with_a_visible_marker(field):
    fields = {key: value for key, value in COMPLETE_FIELDS.items() if key != field}
    label = build_label(fields, [])
    assert label["draft"] is True and label["draft_banner"] == LABEL_DRAFT_BANNER
    assert field in {item["field"] for item in label["missing"]}
    assert TO_FILL in json.dumps(label["thai"], ensure_ascii=False)


def test_short_shelf_life_needs_an_expiry_date():
    label = build_label({**COMPLETE_FIELDS, "shelf_life_months": 24}, [])
    assert label["draft"] is True
    assert {"label": "วันหมดอายุ", "text": TO_FILL} in label["thai"]
    dated = build_label({**COMPLETE_FIELDS, "shelf_life_months": 24, "exp": "10/2028"}, [])
    assert dated["draft"] is False
    assert "EXP: 10/2028" in dated["english"][-2]


def test_declared_carriers_come_from_the_rows_in_order_of_volume():
    rows = [
        {"identity_name": "Hedione", "amount_decimal": "2", "amount_unit": "mL",
         "stock_fraction_decimal": "0.1", "carrier": "DPG"},
        {"material": "Iso E Super", "volume_ul": 1000},
        {"material": "Ambrox", "volume_ul": 100, "dilution": 0.5, "carrier": "IPM 10% w/w"},
        {"material": "Citral", "volume_ul": 50, "dilution": 0.1, "carrier": "ethanol"},
    ]
    label = build_label({**COMPLETE_FIELDS, "declare_carriers": True, "alcohol_denat": True}, rows)

    assert label["ingredients"]["items"] == [
        "Alcohol Denat.", "Dipropylene Glycol", "Parfum (Fragrance)", "Isopropyl Myristate",
    ]
    assert label["draft"] is False
    off = build_label(COMPLETE_FIELDS, rows)
    assert off["ingredients"]["line"] == "Alcohol, Parfum (Fragrance)"


def test_unknown_carrier_is_listed_for_the_user_to_name():
    rows = [{"material": "Oud", "volume_ul": 100, "dilution": 0.1, "carrier": "Mystery Oil"}]
    fields = {**COMPLETE_FIELDS, "declare_carriers": True}

    label = build_label(fields, rows)
    assert label["ingredients"]["unknown_carriers"] == ["mystery oil"]
    assert label["draft"] is True
    assert TO_FILL in label["ingredients"]["line"]

    named = build_label({**fields, "carrier_names": {"Mystery Oil": "Caprylic/Capric Triglyceride"}}, rows)
    assert named["ingredients"]["unknown_carriers"] == []
    assert "Caprylic/Capric Triglyceride" in named["ingredients"]["items"]
    assert named["draft"] is False


@pytest.mark.parametrize("fields", [
    {"name": 5},
    {"type": "body_mist"},
    {"mfg": "2026-10"},
    {"mfg": "10/2026", "exp": "09/2026"},
    {"net_ml": 0},
    {"declare_carriers": "yes"},
    {"surprise": "x"},
    {"name": "bad\x00name"},
])
def test_label_refuses_bad_fields(fields):
    with pytest.raises(CommercialPackError):
        build_label(fields, [])


def test_label_refuses_bad_rows():
    with pytest.raises(CommercialPackError):
        build_label(COMPLETE_FIELDS, [{"material": "X", "amount_decimal": "1", "amount_unit": "g"}])
    with pytest.raises(CommercialPackError):
        build_label(COMPLETE_FIELDS, [{"material": "X", "volume_ul": 1, "dilution": 10}])


def _node(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the batch label view test needs it")
    program = f"const m = require({json.dumps(str(BATCH_LABEL_JS))});\n{script}"
    completed = subprocess.run(
        [node, "-e", program], capture_output=True, text=True, encoding="utf-8", timeout=60,
        check=True,
    )
    return json.loads(completed.stdout)


def test_views_render_with_text_nodes_and_mark_every_gap():
    label = build_label({"name": "<b>Bloom</b>"}, [])
    statement = build_ifra_statement(_gate("HOLD", holds=[_row("X", None, 0.1, None, "unchecked")]), {})
    script = """
const fake = () => {
  const make = (tag) => ({ tag, children: [], className: "", textContent: "", lang: "",
    append(...kids) { this.children.push(...kids); } });
  return { createElement: make, createTextNode: (text) => ({ tag: "#text", text }) };
};
const walk = (n, out) => { if (n.tag === "#text") out.text.push(n.text); if (n.tag === "mark") out.marks += 1;
  if (n.textContent) out.text.push(n.textContent); out.tags.add(n.tag); (n.children || []).forEach((c) => walk(c, out)); return out; };
const label = walk(m.renderView(fake(), m.labelView(LABEL)), { text: [], tags: new Set(), marks: 0 });
const statement = walk(m.renderView(fake(), m.statementView(STATEMENT)), { text: [], tags: new Set(), marks: 0 });
console.log(JSON.stringify({ label: { text: label.text, marks: label.marks }, statement: { text: statement.text, marks: statement.marks, table: statement.tags.has("table") },
  parts: m.fillParts("a [ to fill ] b"), body: m.batchLabelBody({ name: " N ", net_ml: "", carrier_names: { x: " Y " } }, []) }));
""".replace("LABEL", json.dumps(label)).replace("STATEMENT", json.dumps(statement))
    result = _node(script)

    assert result["parts"] == [
        {"text": "a ", "fill": False}, {"text": TO_FILL, "fill": True}, {"text": " b", "fill": False},
    ]
    assert LABEL_DRAFT_BANNER in result["label"]["text"]
    assert "<b>Bloom</b>" in result["label"]["text"]  # plain text, never markup
    assert result["label"]["marks"] >= 5
    assert STATEMENT_DRAFT_BANNER in result["statement"]["text"]
    assert result["statement"]["table"] is True and result["statement"]["marks"] >= 2
    assert result["body"]["fields"] == {
        "type": "eau_de_parfum", "alcohol_denat": False, "declare_carriers": False,
        "include_english": True, "name": "N", "net_ml": 30, "carrier_names": {"x": "Y"},
    }
    assert ".innerHTML" not in BATCH_LABEL_JS.read_text(encoding="utf-8")
