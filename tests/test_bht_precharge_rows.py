"""House BHT pre-charge row in formula files, the release gate, the mixer and composer output.

BHT 5% w/v in ethanol (house dose 120 uL per 30 mL = 6 mg BHT) is a technical
antioxidant pre-charge, not an odour row (Rule 1: stock dose, concentration, ODT
and OAV stay separate). These tests hold the row out of every odour model, keep
it outside the liquid stock-charge total but inside the 30 mL make-up, check its
stock (RULE 0) and put it first on the bench card.

The stock record "BHT 5% w/v in ethanol" is being added by the stock thread; the
tests pass before and after it lands: the "recorded" case uses a patched
inventory row, and the live-inventory case accepts whichever state is current.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

import engine.pipeline.preflight as preflight
from engine.formula_metadata import is_ethanol_vehicle_name
from engine.inventory_parser import CURRENT_INVENTORY_AUTHORITY, InventoryMaterial
from engine.mixer.instructions import build_formula_compounding_protocol
from engine.name_utils import normalize_name
from engine.pipeline.antioxidant import (
    HOUSE_BHT_STOCK,
    formula_has_antioxidant,
    precharge_make_up,
    technical_precharge_gate,
)
from engine.units.concentration import classify_material_category, parse_concentration
from scripts.verify_formula_workflow import parse_formula_markdown

ODOUR_ROWS = """| 1 | B1 | Iso E Super | neat | 1200 | Halo |
| 2 | B1 | Hedione | neat | 600 | Radiant air |
| 3 | B6 | Habanolide | neat | 600 | Musk |
| 4 | B15 | Bergamot FCF Oil Sicilian | neat | 800 | Opening |
| 5 | B4 | Labdanum Absolute 10% | 10% w/w in DPG | 300 | Resin |
"""
BHT_ROW = "| 6 | Pre-charge | BHT 5% w/v in ethanol | 5% w/v in ethanol | 120 | Antioxidant, not an odour row |\n"


def _formula_text(*, bht_row: str = "", total: str = "3500") -> str:
    return f"""# Test Amber R1 30 mL EDP

- **Finished target:** 30.00 mL nominal, ethanol q.s.

## Formula

Liquid stock-charge target: {total} uL

| # | Basket | Ingredient | Dilution / owned stock | Amount (uL) | Note |
|---:|:---:|---|---|---:|---|
{ODOUR_ROWS}{bht_row}|  |  | **Liquid stock-charge total** |  | **{total}** |  |
"""


def _parse(tmp_path, text: str, name: str = "f.md") -> dict:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    records = parse_formula_markdown(path)
    assert len(records) == 1
    return records[0]


def _recorded_bht_stock() -> InventoryMaterial:
    """The stock thread's record, as parse_current_inventory() will return it."""
    return InventoryMaterial(
        name=HOUSE_BHT_STOCK,
        dilution=0.05,
        category="stabilizer",
        raw_name=HOUSE_BHT_STOCK,
        status="owned",
        fraction_basis="mass_per_volume",
        carrier="ethanol",
        physical_form="solution",
        identity_name=HOUSE_BHT_STOCK,
        stock_id="INV-TEST-FIXTURE-BHT",
        authority=CURRENT_INVENTORY_AUTHORITY,
        execution_ready=True,
    )


@pytest.fixture
def bht_recorded(monkeypatch):
    real = preflight.parse_current_inventory
    # The live record once the stock is loaded (STK-238); a fixture record before that.
    record = next(
        (r for r in real() if normalize_name(r.name) == normalize_name(HOUSE_BHT_STOCK)),
        _recorded_bht_stock(),
    )

    def with_bht(*args, **kwargs):
        rows = list(real(*args, **kwargs))
        if not any(normalize_name(r.name) == normalize_name(HOUSE_BHT_STOCK) for r in rows):
            rows.append(record)
        return rows

    monkeypatch.setattr(preflight, "parse_current_inventory", with_bht)
    return record


def _live_bht_recorded() -> bool:
    return any(
        normalize_name(stock.name) == normalize_name(HOUSE_BHT_STOCK) and stock.execution_ready
        for stock in preflight.parse_current_inventory()
    )


# ── Formula files ───────────────────────────────────────────────────────────


def test_bht_row_is_a_technical_precharge_not_an_odour_row(tmp_path):
    with_bht = _parse(tmp_path, _formula_text(bht_row=BHT_ROW), "with.md")
    without = _parse(tmp_path, _formula_text(), "without.md")

    # The odour rows, their strengths and stock specs are exactly the file without BHT,
    # so ODT, OAV, headspace, role and IFRA models never see it.
    assert with_bht["ingredients_ul"] == without["ingredients_ul"]
    assert with_bht["dilutions"] == without["dilutions"]
    assert with_bht["stock_specs"] == without["stock_specs"]
    assert HOUSE_BHT_STOCK not in with_bht["ingredients_ul"]
    assert sum(with_bht["ingredients_ul"].values()) == 3500.0
    assert without["technical_precharge_rows"] == []

    (row,) = with_bht["technical_precharge_rows"]
    assert row["material"] == HOUSE_BHT_STOCK
    assert row["raw_ul"] == 120.0
    # 5% w/v = 0.05 g per mL = 50 mg per mL, so 120 uL carries 6 mg BHT.
    assert row["fraction"] == pytest.approx(0.05)
    assert row["fraction_basis"] == "mass_per_volume"
    assert row["carrier"] == "ethanol"
    assert row["active_mg"] == pytest.approx(6.0)
    assert row["category"] == "technical"
    assert row["stock_component_role"] == "technical_active"
    assert row["operation"] == "PRECHARGE"
    assert row["odour_row"] is False
    assert formula_has_antioxidant(with_bht) and not formula_has_antioxidant(without)


def test_bht_solution_in_ethanol_is_not_the_ethanol_vehicle():
    assert is_ethanol_vehicle_name("Ethanol 96%")
    assert not is_ethanol_vehicle_name("BHT 5% w/v in ethanol")
    assert not is_ethanol_vehicle_name("BHT 5% in ethanol")


@pytest.mark.parametrize(
    "name", ["BHT", "BHT 5% w/v in ethanol", "BHT 5% in ethanol", "BHT 5% w/v EtOH", "alpha-Tocopherol"]
)
def test_antioxidant_rows_classify_as_technical(name):
    assert classify_material_category(name) == "technical"


def test_w_v_strength_reads_as_mass_per_volume():
    conc = parse_concentration("5% w/v in ethanol")
    assert conc.value == pytest.approx(0.05)
    assert conc.basis == "w/v"
    assert conc.carrier == "ethanol"


def test_precharge_row_and_total_row_in_the_physical_table(tmp_path):
    record = _parse(tmp_path, _formula_text(bht_row=BHT_ROW))
    rows = {row["material"]: row for row in record["compounding_rows"]}

    bht = rows[HOUSE_BHT_STOCK]
    assert bht["operation"] == "PRECHARGE"
    assert bht["basket"] is None
    assert bht["raw_ul"] == 120.0
    # The "Liquid stock-charge total" line sums the rows; it is not a transfer.
    assert not any("total" in name.casefold() for name in rows)
    blockers = record["compounding_row_blockers"]
    assert not any(b.startswith("INVALID_BASKET") for b in blockers)
    assert not any(b.startswith("PHYSICAL_ROW_NOT_IN_FORMULA") for b in blockers)
    assert record["compounding_row_status"] == "COMPLETE"


# ── Mixer ───────────────────────────────────────────────────────────────────


def _transfer_steps(protocol: dict) -> list[str]:
    return [
        line.strip()
        for phase in protocol["phases"]
        for line in phase["instructions"]
        if line.strip().startswith("Step ")
    ]


def test_mixer_puts_the_bht_precharge_first(tmp_path):
    record = _parse(tmp_path, _formula_text(bht_row=BHT_ROW))
    protocol = build_formula_compounding_protocol(record)

    first = _transfer_steps(protocol)[0]
    assert first.startswith("Step 1.") and HOUSE_BHT_STOCK in first and "120 µL" in first
    assert protocol["phases"][0]["phase"] == "precharge"
    assert "Antioxidant pre-charge" in first
    # The bench still moves every uL: odour stocks plus the pre-charge.
    assert protocol["raw_total_ul"] == pytest.approx(3620.0)
    assert protocol["ordered_raw_total_ul"] == pytest.approx(3620.0)


def test_mixer_adds_a_technical_row_missing_from_the_physical_table():
    record = {
        "name": "No baskets",
        "ingredients_ul": {"Iso E Super": 1200.0, "Hedione": 600.0},
        "technical_precharge_rows": [
            {"material": HOUSE_BHT_STOCK, "raw_ul": 120.0, "strength_text": "5% w/v in ethanol"}
        ],
    }
    protocol = build_formula_compounding_protocol(record)
    steps = _transfer_steps(protocol)
    assert HOUSE_BHT_STOCK in steps[0]
    assert len(steps) == 3


def test_bht_in_an_odour_basket_still_comes_out_as_a_precharge(tmp_path):
    text = _formula_text(bht_row=BHT_ROW.replace("| Pre-charge |", "| B6 |"))
    record = _parse(tmp_path, text)
    bht = next(r for r in record["compounding_rows"] if r["material"] == HOUSE_BHT_STOCK)
    assert bht["operation"] == "PRECHARGE"
    assert HOUSE_BHT_STOCK in _transfer_steps(build_formula_compounding_protocol(record))[0]


# ── Release gate entry ──────────────────────────────────────────────────────


class _Contract:
    def __init__(self, status, issues=(), matched=()):
        self.status = status
        self.data = {"issues": list(issues), "matched_stocks": list(matched)}


def _record_with_bht(raw_ul: float = 120.0) -> dict:
    return {
        "ingredients_ul": {"Iso E Super": 4000.0, "Hedione": 2000.0},
        "technical_precharge_rows": [
            {
                "material": HOUSE_BHT_STOCK,
                "amount": raw_ul,
                "amount_unit": "uL",
                "raw_ul": raw_ul,
                "fraction": 0.05,
                "fraction_basis": "mass_per_volume",
                "carrier": "ethanol",
                "declared": True,
                "strength_text": "5% w/v in ethanol",
                "active_mg": raw_ul * 0.05,
                "active_mg_basis": "w/v",
            }
        ],
    }


def test_gate_holds_in_plain_words_while_the_solution_is_not_recorded():
    gate = technical_precharge_gate(
        _record_with_bht(),
        batch_volume_ml=30.0,
        stock_contract=lambda f: _Contract(
            "FAIL", [{"material": HOUSE_BHT_STOCK, "reason": "not_in_inventory"}]
        ),
    )
    assert gate["gate"] == "technical_precharge"
    assert gate["status"] == "HOLD"
    assert "BHT 5% w/v in ethanol is not recorded as a stock yet" in gate["detail"]
    assert "about 100 mg BHT made up to 2.000 mL with ethanol" in gate["detail"]
    assert gate["data"]["rows"][0]["stock_recorded"] is False


def test_gate_passes_once_the_solution_is_recorded(bht_recorded):
    gate = technical_precharge_gate(_record_with_bht(), batch_volume_ml=30.0)
    assert gate["status"] == "PASS", gate["detail"]
    (row,) = gate["data"]["rows"]
    assert row["stock_recorded"] is True
    # The stock id comes from the inventory record, never from this module.
    assert row["stock_id"] == bht_recorded.stock_id
    assert row["finished_mg_per_ml"] == pytest.approx(0.2)


def test_gate_follows_the_live_inventory_before_and_after_the_record_lands():
    gate = technical_precharge_gate(_record_with_bht(), batch_volume_ml=30.0)
    assert gate["status"] == ("PASS" if _live_bht_recorded() else "HOLD")


def test_gate_warns_on_a_dose_off_the_house_dose():
    gate = technical_precharge_gate(
        _record_with_bht(100.0),
        batch_volume_ml=30.0,
        stock_contract=lambda f: _Contract("PASS", matched=[{"material": HOUSE_BHT_STOCK}]),
    )
    assert gate["status"] == "WARN"
    assert "house dose 120 uL for 30 mL" in gate["detail"]


def test_precharge_sits_outside_the_stock_charge_total_and_inside_the_make_up():
    make_up = precharge_make_up(6000.0, [{"raw_ul": 120.0}], 30.0)
    assert make_up["liquid_stock_charge_total_ul"] == 6000.0
    assert make_up["technical_precharge_ul"] == 120.0
    assert make_up["ethanol_qs_ul"] == 23880.0
    assert make_up["counted_in_liquid_stock_charge_total"] is False


def test_gate_with_no_technical_rows_adds_nothing():
    assert technical_precharge_gate({"ingredients_ul": {"Hedione": 100.0}}, batch_volume_ml=30.0) is None


def test_release_gate_adds_the_precharge_gate_and_leaves_every_odour_gate_alone(
    tmp_path, capsys
):
    import scripts.formula_release_gate as release_cli

    def run(text: str, name: str) -> dict:
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        release_cli.main(
            [
                "--formula-file", str(path),
                "--expected-concentrate-ul", "3500",
                "--brief", "woody_floral_musk",
                "--no-audit", "--json",
            ],
            repository_commit="test",
        )
        return json.loads(capsys.readouterr().out)["formulas"][0]

    without = run(_formula_text(), "Test_Amber_30mL_EDP.md")
    with_bht = run(_formula_text(bht_row=BHT_ROW), "Test_Amber_BHT_30mL_EDP.md")

    statuses = {g["gate"]: g["status"] for g in without["gates"]}
    statuses_bht = {g["gate"]: g["status"] for g in with_bht["gates"]}
    precharge = statuses_bht.pop("technical_precharge")
    assert statuses_bht == statuses
    assert "technical_precharge" not in statuses
    assert precharge == ("PASS" if _live_bht_recorded() else "HOLD")
    assert next(g for g in with_bht["gates"] if g["gate"] == "exact_subtotal")["detail"] == "3500.0 uL"
    assert with_bht["technical_precharge"]["make_up"]["ethanol_qs_ul"] == 30000.0 - 3500.0 - 120.0
    assert [row["name"] for row in with_bht["oav_table"]] == [
        row["name"] for row in without["oav_table"]
    ]
    assert HOUSE_BHT_STOCK not in {row["name"] for row in with_bht["oav_table"]}
    first = _transfer_steps(with_bht["compounding"])[0]
    assert HOUSE_BHT_STOCK in first


def test_older_total_that_counts_the_precharge_checks_the_odour_stocks_only(tmp_path, capsys):
    """A stated total of odour stocks + BHT (3620) checks the odour subtotal against 3500."""
    import scripts.formula_release_gate as release_cli

    path = tmp_path / "Test_Amber_Old_Total_30mL_EDP.md"
    path.write_text(_formula_text(bht_row=BHT_ROW, total="3620"), encoding="utf-8")
    release_cli.main(
        [
            "--formula-file", str(path),
            "--expected-concentrate-ul", "3620",
            "--brief", "woody_floral_musk",
            "--no-audit", "--json",
        ],
        repository_commit="test",
    )
    report = json.loads(capsys.readouterr().out)["formulas"][0]
    subtotal = next(g for g in report["gates"] if g["gate"] == "exact_subtotal")
    precharge = next(g for g in report["gates"] if g["gate"] == "technical_precharge")
    assert subtotal["status"] == "PASS"
    assert subtotal["detail"] == "3500.0 uL"
    assert report["technical_precharge"]["make_up"]["expected_counts_precharge"] is True
    assert "checked against 3500 uL" in precharge["detail"]


# ── Snapshot loader ─────────────────────────────────────────────────────────


def test_markdown_snapshot_keeps_bht_out_of_the_declared_stock_charge_total(tmp_path):
    from engine.research.snapshots import load_markdown_design_snapshot

    text = """# Snapshot With BHT

**Design identity:** `snapshot-bht-test`

Liquid stock-charge target: 1800 uL

| # | Basket | Ingredient | Dilution | Amount | Note |
|---:|---|---|---|---:|---|
| 1 | B1 | Iso E Super | neat | 1200 uL | Halo |
| 2 | B1 | Hedione | neat | 600 uL | Air |
| 3 | B1 | Ambrox Super | neat | 300 mg | Weighed |
| 4 | Pre-charge | BHT 5% w/v in ethanol | 5% w/v in ethanol | 120 uL | Antioxidant |
"""
    path = tmp_path / "snap.md"
    path.write_text(text, encoding="utf-8")
    loaded = load_markdown_design_snapshot(path)
    assert loaded.liquid_total_ul_decimal == "1800"
    assert loaded.solid_total_mg_decimal == "300"
    assert loaded.technical_precharge_ul_decimal == "120"
    bht = next(c for c in loaded.snapshot.components if c.source_material_label == HOUSE_BHT_STOCK)
    assert bht.operation == "PRECHARGE"


# ── Composer output ─────────────────────────────────────────────────────────


def _composer_result() -> dict:
    return {
        "optimized_formula": {
            "name": "Composer Test",
            "rows": [
                {"identity_name": "Iso E Super", "amount_decimal": "3000", "stock_fraction_decimal": "1"},
                {"identity_name": "Hedione", "amount_decimal": "2000", "stock_fraction_decimal": "1"},
                {"identity_name": "Habanolide", "amount_decimal": "1000", "stock_fraction_decimal": "1"},
            ],
        }
    }


@pytest.mark.parametrize(("batch_ml", "raw_ul"), [(30.0, 120.0), (50.0, 200.0)])
def test_composer_formula_carries_the_house_bht_row_apart_from_odour_rows(batch_ml, raw_ul):
    from engine.formulation_intelligence import yardstick as ys

    formula = ys.formula_from_composer(_composer_result(), batch_volume_ml=batch_ml)
    assert [row["material"] for row in formula["rows"]] == ["Iso E Super", "Hedione", "Habanolide"]
    (bht,) = formula["technical_rows"]
    assert bht["material"] == HOUSE_BHT_STOCK
    assert bht["raw_ul"] == raw_ul
    assert bht["operation"] == "PRECHARGE"
    assert bht["bht_mg"] == pytest.approx(raw_ul * 0.05)
    assert Decimal(bht["active_fraction"]) == Decimal("0.05")


def test_withheld_composer_result_gets_no_bht_row():
    from engine.formulation_intelligence import yardstick as ys

    withheld = ys.formula_from_composer({"optimized_formula": None, "initial_formula": None})
    assert withheld["technical_rows"] == []


def test_technical_rows_never_move_a_yardstick_score():
    from engine.formulation_intelligence import yardstick as ys

    formula = ys.formula_from_composer(_composer_result())
    brief = {
        "id": "bht-test",
        "named_notes": [{"name": "musk", "window": "drydown", "materials": ["habanolide"]}],
    }
    with_row = ys.score_formula(formula, brief)
    without_row = ys.score_formula({**formula, "technical_rows": []}, brief)
    assert json.dumps(with_row, sort_keys=True, default=str) == json.dumps(
        without_row, sort_keys=True, default=str
    )
    assert ys._gate_record(formula)["ingredients_ul"].keys() == {"Iso E Super", "Hedione", "Habanolide"}


def test_composer_bench_card_starts_with_the_bht_precharge():
    from engine.formulation_intelligence import yardstick as ys

    record = ys.bench_record(ys.formula_from_composer(_composer_result()))
    (row,) = record["technical_precharge_rows"]
    assert row["active_mg"] == pytest.approx(6.0)
    steps = _transfer_steps(build_formula_compounding_protocol(record))
    assert HOUSE_BHT_STOCK in steps[0]
    assert len(steps) == 4
