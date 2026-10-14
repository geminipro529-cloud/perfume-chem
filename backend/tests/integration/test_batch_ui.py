"""The Batch view: page wiring, the commercial-pack routes on the app, and batch.js's pure rules."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.lab_page_scripts import get_lab_script

BATCH_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "batch.js"


@pytest.mark.asyncio
async def test_batch_view_has_nav_section_scripts_styles_and_a_bottles_page_hook(client):
    page = await client.get("/app")
    javascript = await get_lab_script(client)
    batch = await client.get("/static/batch.js")
    for asset in ("/static/batch.css", "/static/batch-label.css", "/static/batch-label.js"):
        assert (await client.get(asset)).status_code == 200

    assert batch.status_code == 200
    assert '<button class="nav-item" data-view="batch">Batch</button>' in page.text
    panel = page.text[page.text.index('data-panel="batch"'):]
    assert panel.index('id="batch-root"') < panel.index('id="batch-label-area"') < panel.index("</section>")
    assert 'id="batch-sheet"' in page.text
    for script in ("batch-label.js", "batch.js"):
        assert page.text.index(f'src="/static/{script}"') < page.text.index('src="/static/lab/core.js"')
    for sheet in ("batch-label.css", "batch.css"):
        assert page.text.index(f'href="/static/{sheet}"') < page.text.index("</head>")
    assert 'attachBatch({ doc: document, request, root: $("#batch-root") })' in javascript.text
    assert ".innerHTML" not in batch.text
    for path in ("/v2/batches/plan", "/v2/batches/suggest-lot", "/v2/batches/gate-runs", "/actuals`"):
        assert path in batch.text


@pytest.mark.asyncio
async def test_commercial_pack_routes_answer_where_batch_label_js_calls_them(client):
    """batch-label.js posts /commercial-pack/... under lab/core.js's base /api/v1/lab."""
    label = await client.post(
        "/api/v1/lab/commercial-pack/label",
        json={"fields": {"name": "Demo Cedar", "net_ml": 30}, "rows": [{"material": "Cedar", "volume_ul": 100}]},
    )
    assert label.status_code == 200, label.text
    assert "front" in label.json()

    statement = await client.post("/api/v1/lab/commercial-pack/ifra-statement", json={"meta": {}})
    assert statement.status_code == 400
    assert statement.json()["error"]["code"] == "invalid_request"


def _node(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the batch view logic test needs it")
    program = f"const m = require({json.dumps(str(BATCH_JS))});\n{script}"
    completed = subprocess.run(
        [node, "-e", program], capture_output=True, text=True, encoding="utf-8", timeout=60, check=True
    )
    return json.loads(completed.stdout)


PLAN = {
    "formula_name": "Demo Cedar 30mL",
    "bottles": "2",
    "bottle_ml": "30",
    "loss_percent": "3",
    "finished_volume_ml": "61.8",
    "card_total_ml": "30",
    "card_total_ml_source": "formula name",
    "factor": "2.06",
    "totals": {"planned_ul": "2472", "planned_mg": "0", "card_ul": "1200", "card_mg": "0"},
    "rounding": "Scaled amounts are rounded to the nearest whole µL or whole mg.",
    "proportionality": {"strengths_unchanged": True, "largest_rounding_change_percent": "0.162"},
    "rows": [
        {"line": 1, "material": "Cedar <b>", "strength": "10% w/w", "concentration_fraction_decimal": "0.1",
         "unit": "uL", "card_amount": "1000", "planned_amount": "2060"},
        {"line": 2, "material": "Ambrox", "strength": "neat", "concentration_fraction_decimal": None,
         "unit": "uL", "card_amount": "200", "planned_amount": "412"},
        {"line": 3, "material": "Resin", "strength": "50%", "concentration_fraction_decimal": "0.5",
         "unit": "mg", "card_amount": "10", "planned_amount": "21"},
    ],
}


def test_plan_body_sends_a_project_path_or_pasted_text_and_leaves_blanks_to_the_server():
    result = _node(
        """
console.log(JSON.stringify({
  project: m.batchPlanBody({ source_kind: "PROJECT_FILE", source_path: " formulas/A_30mL.md ", bottles: "2", bottle_ml: "", loss_percent: " ", card_total_ml: "" }),
  pasted: m.batchPlanBody({ source_kind: "PASTED", pasted_text: "| a |", name: " Demo ", bottles: "", bottle_ml: "50", loss_percent: "5", card_total_ml: "100" }),
}));
"""
    )
    assert result["project"] == {"bottles": "2", "bottle_ml": "30", "source_path": "formulas/A_30mL.md"}
    assert result["pasted"] == {
        "bottles": "1", "bottle_ml": "50", "text": "| a |", "name": "Demo", "loss_percent": "5", "card_total_ml": "100",
    }


def test_label_rows_gate_path_month_and_actuals_body():
    result = _node(
        f"""
const plan = {json.dumps(PLAN)};
console.log(JSON.stringify({{
  rows: m.batchLabelRows(plan),
  path: m.batchGatePath(" KS-20261013-01 "),
  month: m.batchMonthYear("2026-10-13"),
  badMonth: m.batchMonthYear("13/10/2026"),
  actuals: m.batchActualsBody([[1, " 2061 "], [2, ""], [3, "0"]], "  spilled a drop "),
}}));
"""
    )
    assert result["rows"] == [
        {"material": "Cedar <b>", "volume_ul": 2060, "stock_fraction_decimal": 0.1},
        {"material": "Ambrox", "volume_ul": 412},
    ]
    assert result["path"] == "data/user/batches/KS-20261013-01/gate.json"
    assert result["month"] == "10/2026"
    assert result["badMonth"] == ""
    assert result["actuals"] == {
        "actuals": [{"line": 1, "actual_amount": "2061"}, {"line": 3, "actual_amount": "0"}],
        "notes": "spilled a drop",
    }


def test_gate_words_name_every_non_pass_gate_and_say_no_parent_is_compared():
    result = _node(
        """
console.log(JSON.stringify({
  running: m.batchGateWords({ state: "RUNNING" }),
  finished: m.batchGateWords({ state: "FINISHED", status: "HOLD", not_pass: [
    { gate: "IFRA", status: "FAIL", detail: "Citral over the Category 4 limit" },
    { gate: "Stock", status: "HOLD", detail: "" },
  ] }),
  clean: m.batchGateWords({ state: "FINISHED", status: "PASS", not_pass: [] }),
  failed: m.batchGateWords({ state: "FAILED", error: "timeout" }),
  noParent: m.BATCH_NO_PARENT,
}));
"""
    )
    assert result["running"]["done"] is False
    assert result["noParent"] in result["running"]["lines"]
    finished = result["finished"]
    assert finished["done"] is True and finished["failed"] is False
    assert finished["lines"][0] == "Gate result: HOLD."
    assert "IFRA: FAIL — Citral over the Category 4 limit" in finished["lines"]
    assert "Stock: HOLD" in finished["lines"]
    assert result["noParent"] in finished["lines"]
    assert "scaling keeps every stock and strength" in result["noParent"]
    assert "Every gate passed." in result["clean"]["lines"]
    assert result["failed"] == {"done": True, "failed": True, "lines": ["The gate could not finish: timeout."]}


def test_plan_summary_and_print_sheet_keep_units_and_leave_a_blank_weighed_column():
    result = _node(
        f"""
const plan = {json.dumps(PLAN)};
console.log(JSON.stringify({{
  summary: m.batchPlanSummary(plan),
  sheet: m.batchSheetView(plan, {{ lot: "KS-20261013-01", made_on: "2026-10-13", made_by: "" }}),
}}));
"""
    )
    summary = result["summary"]
    assert summary[0] == "Demo Cedar 30mL: 2 × 30 mL with 3% loss allowance makes 61.8 mL."
    assert summary[1] == "The card makes 30 mL (from the formula name); every row is multiplied by 2.06."
    assert summary[2].startswith("Stocks in total: 2472 µL.")
    assert PLAN["rounding"] in summary
    assert "at most 0.162%" in summary[-1]
    sheet = result["sheet"]
    assert sheet["head"] == ["#", "Material", "Strength", "Planned", "Weighed"]
    assert sheet["rows"][0] == ["1", "Cedar <b>", "10% w/w", "2060 µL", ""]
    assert sheet["rows"][2] == ["3", "Resin", "50%", "21 mg", ""]
    assert ["Lot", "KS-20261013-01"] in sheet["facts"]
    assert ["Made by", "________"] in sheet["facts"]
    assert sheet["signature"] == ["Weighed by", "Checked by"]
