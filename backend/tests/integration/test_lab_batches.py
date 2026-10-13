"""Production batches: scaling math, the batch record log and the batch routes.

The release gate itself is never run here: the subprocess call is replaced.
"""

import json
import time
from datetime import date
from decimal import Decimal

import pytest

from app.services import batch_production as batches
from app.services.formula_import import FormulaAnalysisImportParser

BASE = "/api/v1/lab/v2/batches"

CARD = """# Test Card 30mL EDP

| # | Ingredient | Dilution | µL |
|---|---|---|---:|
| 1 | Hedione | neat | 1000 |
| 2 | Ambrox | 10% w/w in DPG | 333 |
| 3 | Damascone | 1% | 1 |
| 4 | Ethanol | | 28666 |
"""

MG_CARD = """# Mass Card

| Ingredient | Dilution | mg |
|---|---|---:|
| Hedione | neat | 120 |
| Iso E Super | neat | 80 |
"""


def _rows(text, name="Card"):
    return FormulaAnalysisImportParser.parse_text(text, default_name=name, source_sha256="0" * 64).rows


@pytest.fixture(autouse=True)
def batch_files(tmp_path, monkeypatch):
    monkeypatch.setenv(batches.BATCH_RECORD_PATH_ENV, str(tmp_path / "batch_records.jsonl"))
    monkeypatch.setenv(batches.BATCH_DIR_ENV, str(tmp_path / "batches"))
    return tmp_path


# ---- scaling ---------------------------------------------------------------


def test_scaling_factor_includes_bottles_size_and_loss():
    plan = batches.scale_card(_rows(CARD), bottles=10, bottle_ml="30", card_total_ml="30", loss_percent="3")
    assert Decimal(plan["factor"]) == Decimal("10.3")
    assert plan["finished_volume_ml"] == "309"
    by_name = {row["material"]: row for row in plan["rows"]}
    # Ethanol is the final dilution, not a scaled stock row.
    assert set(by_name) == {"Hedione", "Ambrox", "Damascone"}
    assert by_name["Hedione"]["planned_amount"] == "10300"
    assert by_name["Ambrox"]["exact_amount"] == "3429.9"
    assert by_name["Ambrox"]["planned_amount"] == "3430"
    assert by_name["Damascone"]["exact_amount"] == "10.3"
    assert by_name["Damascone"]["planned_amount"] == "10"
    assert plan["totals"]["planned_ul"] == "13740"
    assert plan["totals"]["card_ul"] == "1334"
    assert plan["rounding"] == batches.ROUNDING_NOTE
    # Strengths are copied as written, carrier and basis included.
    assert by_name["Ambrox"]["strength"] == "10% w/w in DPG"


def test_scaling_without_loss_and_with_a_bigger_bottle():
    plan = batches.scale_card(_rows(CARD), bottles=4, bottle_ml="50", card_total_ml="30", loss_percent="0")
    # 4 x 50 / 30 = 20/3; exact Decimal division, then one rounding per row.
    hedione = plan["rows"][0]
    assert Decimal(hedione["exact_amount"]).quantize(Decimal("0.001")) == Decimal("6666.667")
    assert hedione["planned_amount"] == "6667"


def test_rounding_is_half_up_and_a_row_that_rounds_to_zero_is_flagged():
    card = "| Ingredient | Dilution | µL |\n|---|---|---|\n| A | neat | 0.05 |\n| B | neat | 0.04 |\n| C | neat | 100 |\n"
    plan = batches.scale_card(_rows(card), bottles=10, card_total_ml="30", bottle_ml="30", loss_percent="0")
    amounts = [row["planned_amount"] for row in plan["rows"]]
    assert amounts == ["1", "0", "1000"]
    assert len(plan["warnings"]) == 1 and plan["warnings"][0].startswith("B comes to 0.4")


def test_ml_rows_become_ul_and_mg_rows_stay_mg():
    card = "| Ingredient | Dilution | mL |\n|---|---|---|\n| A | neat | 1.5 |\n"
    plan = batches.scale_card(_rows(card), bottles=2, card_total_ml="30", bottle_ml="30", loss_percent="0")
    assert plan["rows"][0]["unit"] == "uL" and plan["rows"][0]["planned_amount"] == "3000"
    mass = batches.scale_card(_rows(MG_CARD), bottles=3, card_total_ml="10", bottle_ml="30", loss_percent="0")
    assert mass["units"] == ["mg"] and mass["totals"]["planned_mg"] == "1800"


@pytest.mark.parametrize(
    ("field", "value"),
    [("bottles", "0"), ("bottles", "2.5"), ("bottle_ml", "-30"), ("card_total_ml", "abc"), ("loss_percent", "-1")],
)
def test_bad_numbers_are_refused(field, value):
    kwargs = {"bottles": "10", "bottle_ml": "30", "card_total_ml": "30", "loss_percent": "3", field: value}
    with pytest.raises(batches.BatchError):
        batches.scale_card(_rows(CARD), **kwargs)


def test_card_total_comes_from_the_name_or_must_be_given():
    plan = batches.plan_batch(
        source_path=None, text=CARD, name=None, bottles="2", bottle_ml="30", card_total_ml=None, loss_percent="0"
    )
    assert plan["card_total_ml"] == "30" and plan["card_total_ml_source"] == "formula name"
    with pytest.raises(batches.BatchError, match="doesn't say how many mL"):
        batches.plan_batch(
            source_path=None, text=MG_CARD, name=None, bottles="2", bottle_ml="30", card_total_ml="", loss_percent="0"
        )


def test_scaled_card_reparses_to_the_planned_amounts():
    plan = batches.scale_card(_rows(CARD), bottles=10, bottle_ml="30", card_total_ml="30", loss_percent="3")
    text = batches.scaled_formula_text("Test | Card", "KS-20261013-01", plan)
    reparsed = _rows(text)
    assert [(row.material, row.amount_decimal, row.amount_unit) for row in reparsed] == [
        (row["material"], row["planned_amount"], "uL") for row in plan["rows"]
    ]
    assert [row.strength_text for row in reparsed] == ["neat", "10% w/w in DPG", "1%"]


def test_a_mixed_unit_card_has_no_gate_text():
    card = "| Ingredient | Dilution | µL | mg |\n|---|---|---|---|\n| A | neat | 10 | |\n| B | neat | | 20 |\n"
    plan = batches.scale_card(_rows(card), bottles=1, bottle_ml="30", card_total_ml="30", loss_percent="0")
    assert plan["mixed_units"] is True
    with pytest.raises(batches.BatchError, match="mixes"):
        batches.scaled_formula_text("Mixed", "LOT-1", plan)


def test_suggested_lot_skips_lots_already_used():
    day = date(2026, 10, 13)
    assert batches.suggest_lot("k.s.", day, set()) == "KS-20261013-01"
    assert batches.suggest_lot("ks", day, {"KS-20261013-01", "KS-20261013-02"}) == "KS-20261013-03"
    assert batches.suggest_lot("", day, set()) == "LOT-20261013-01"


# ---- record log ------------------------------------------------------------


def _plan(**overrides):
    values = {"source_path": None, "text": CARD, "name": None, "bottles": "10", "bottle_ml": "30", "card_total_ml": "30", "loss_percent": "3"}
    values.update(overrides)
    return batches.plan_batch(**values)


def test_record_log_is_append_only_and_hash_chained(batch_files):
    record = batches.record_batch(lot="KS-20261013-01", made_on="2026-10-13", made_by="Kenny", plan=_plan(), gate_run_id=None, notes="first")
    assert record["planned_rows"][1]["planned_amount"] == "3430"
    assert record["source_sha256"] and record["actuals"] == []
    updated = batches.record_actuals("KS-20261013-01", [{"line": 2, "actual_amount": "3428"}], "slightly under")
    assert updated["actuals"] == [{"line": 2, "material": "Ambrox", "unit": "uL", "actual_amount": "3428"}]

    lines = (batch_files / "batch_records.jsonl").read_bytes().splitlines()
    assert len(lines) == 2
    first, second = (json.loads(line) for line in lines)
    assert first["previous_line_sha256"] is None
    import hashlib

    assert second["previous_line_sha256"] == hashlib.sha256(lines[0]).hexdigest()

    with pytest.raises(batches.BatchError, match="already recorded"):
        batches.record_batch(lot="KS-20261013-01", made_on="2026-10-13", made_by="", plan=_plan(), gate_run_id=None, notes="")
    with pytest.raises(batches.BatchError, match="not on this batch"):
        batches.record_actuals("KS-20261013-01", [{"line": 99, "actual_amount": "1"}], "")


def test_an_edited_record_log_is_refused(batch_files):
    batches.record_batch(lot="A-1", made_on="2026-10-13", made_by="", plan=_plan(), gate_run_id=None, notes="")
    batches.record_batch(lot="A-2", made_on="2026-10-13", made_by="", plan=_plan(), gate_run_id=None, notes="")
    path = batch_files / "batch_records.jsonl"
    lines = path.read_bytes().splitlines()
    path.write_bytes(lines[0].replace(b'"made_by": ""', b'"made_by": "X"') + b"\n" + lines[1] + b"\n")
    with pytest.raises(batches.BatchError, match="broken at line 2"):
        batches.list_records()


def test_lot_numbers_must_be_path_safe():
    for bad in ("../x", "", "a/b", "x" * 65):
        with pytest.raises(batches.BatchError):
            batches.check_lot(bad)


# ---- gate summary ----------------------------------------------------------


GATE_JSON = {
    "overall": "WARN",
    "formulas": [
        {
            "status": "WARN",
            "gates": [
                {"gate": "exact_subtotal", "status": "PASS", "detail": "13740.0 uL"},
                {"gate": "safety_ifra_allergen", "status": "WARN", "detail": "allergen labelling", "data": {"x": 1}},
                {"gate": "formula_rows", "status": "FAIL", "message": "row unreadable"},
            ],
        }
    ],
}


def test_gate_summary_lists_gates_that_are_not_pass():
    assert batches.gate_summary(GATE_JSON) == {
        "status": "WARN",
        "not_pass": [
            {"gate": "safety_ifra_allergen", "status": "WARN", "detail": "allergen labelling"},
            {"gate": "formula_rows", "status": "FAIL", "detail": "row unreadable"},
        ],
    }


# ---- routes ----------------------------------------------------------------


def _body(**overrides):
    body = {"text": CARD, "bottles": "10", "bottle_ml": "30", "loss_percent": "3"}
    body.update(overrides)
    return body


async def _wait_for(client, run_id):
    for _ in range(200):
        status = (await client.get(f"{BASE}/gate-runs/{run_id}")).json()
        if status["state"] in {"FINISHED", "FAILED"}:
            return status
        time.sleep(0.02)
    raise AssertionError("gate run did not finish")


@pytest.mark.asyncio
async def test_plan_route_scales_a_project_formula(client):
    response = await client.post(f"{BASE}/plan", json={"source_path": "Vetiver_Moderne_30mL_EDP.md", "bottles": "20"})
    assert response.status_code == 200
    plan = response.json()
    assert plan["factor"] == "20.6" and plan["card_total_ml_source"] == "formula name"
    assert plan["totals"]["planned_ul"] == "123600"
    assert plan["inventory_modified"] is False

    missing = await client.post(f"{BASE}/plan", json={"source_path": "../secret.md", "bottles": "2"})
    assert missing.status_code == 400 and missing.json()["error"]["code"] == "INVALID_BATCH"


@pytest.mark.asyncio
async def test_gate_run_writes_gate_json_and_the_record_keeps_its_result(client, batch_files, monkeypatch):
    seen = {}

    def fake_gate(formula_file, expected_ul, batch_volume_ml, audit_path):
        seen.update(text=formula_file.read_text(encoding="utf-8"), expected=expected_ul, volume=batch_volume_ml, audit=audit_path)
        return GATE_JSON

    monkeypatch.setattr(batches, "_run_gate_command", fake_gate)
    started = await client.post(f"{BASE}/gate-runs", json=_body(lot="KS-20261013-01", card_total_ml="30"))
    assert started.status_code == 202
    status = await _wait_for(client, started.json()["run_id"])
    assert status["state"] == "FINISHED" and status["status"] == "WARN"
    assert [row["gate"] for row in status["not_pass"]] == ["safety_ifra_allergen", "formula_rows"]
    assert status["parent_formula_compared"] is False
    gate_json = batch_files / "batches" / "KS-20261013-01" / "gate.json"
    assert status["gate_json_path"] == str(gate_json)
    # The whole gate JSON is kept, IFRA gate data included.
    assert json.loads(gate_json.read_text())["formulas"][0]["gates"][1]["data"] == {"x": 1}
    assert seen["expected"] == "13740" and seen["volume"] == "309"
    assert "| 2 | Ambrox | 10% w/w in DPG | 3430 |" in seen["text"]
    # The gate's audit goes to a throwaway temp folder, never data/pipeline_audit.
    assert seen["audit"].parent.name.startswith("batch-gate-audit-")
    assert not seen["audit"].parent.exists()

    saved = await client.post(
        BASE,
        json=_body(lot="KS-20261013-01", card_total_ml="30", made_on="2026-10-13", made_by="Kenny", gate_run_id=status["run_id"], notes="n"),
    )
    assert saved.status_code == 201
    record = saved.json()
    assert record["gate"]["status"] == "WARN" and record["gate"]["gate_json_path"] == str(gate_json)

    listed = (await client.get(BASE)).json()["records"]
    assert [row["lot"] for row in listed] == ["KS-20261013-01"]
    one = await client.get(f"{BASE}/KS-20261013-01")
    assert one.status_code == 200 and one.json()["made_by"] == "Kenny"
    actuals = await client.post(f"{BASE}/KS-20261013-01/actuals", json={"actuals": [{"line": 1, "actual_amount": "10290"}]})
    assert actuals.status_code == 200 and actuals.json()["actuals"][0]["actual_amount"] == "10290"
    assert (await client.get(f"{BASE}/NOPE-1")).status_code == 404
    lot = await client.get(f"{BASE}/suggest-lot", params={"initials": "ks", "day": "2026-10-13"})
    assert lot.json() == {"lot": "KS-20261013-02"}


@pytest.mark.asyncio
async def test_a_failed_gate_run_says_why(client, monkeypatch):
    def broken(*args):
        raise batches.BatchError("The gate gave no result (exit 1).")

    monkeypatch.setattr(batches, "_run_gate_command", broken)
    started = await client.post(f"{BASE}/gate-runs", json=_body(lot="X-1"))
    status = await _wait_for(client, started.json()["run_id"])
    assert status["state"] == "FAILED" and "no result" in status["error"]


@pytest.mark.asyncio
async def test_gate_rerun_refuses_a_gram_card(client, monkeypatch):
    monkeypatch.setattr(batches, "_run_gate_command", lambda *a: pytest.fail("gate must not run"))
    response = await client.post(f"{BASE}/gate-runs", json=_body(text=MG_CARD, card_total_ml="10", lot="M-1"))
    assert response.status_code == 400 and "µL cards only" in response.json()["error"]["message"]
