"""Two rows of one material at two strengths are two stock lines.

GATE-17 / GATE-02: the formula parser once merged same-name rows and read the
whole summed volume at the diluted row's strength, so a neat row counted at
10% and the IFRA check could pass a bottle over its limit.
"""

from pathlib import Path

import pytest

from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from scripts.verify_formula_workflow import parse_formula_markdown

CONFIG = ReleaseGateConfig(batch_volume_ml=30.0, audit_enabled=False)


def _formula(tmp_path: Path, rows: list[tuple[str, str, float]]) -> dict:
    lines = "".join(
        f"| {i} | {name} | {strength} | {amount:g} |\n"
        for i, (name, strength, amount) in enumerate(rows, 1)
    )
    path = tmp_path / "two_strength_30mL_EDP.md"
    path.write_text(
        "# Two strength 30 mL EDP\n\n| # | Ingredient | Dilution | uL |\n"
        "|---|---|---|---|\n" + lines,
        encoding="utf-8",
    )
    [formula] = parse_formula_markdown(path)
    return formula


def _gate(report, name: str):
    return next(gate for gate in report.gates if gate.gate == name)


@pytest.mark.parametrize("neat_first", [True, False], ids=["neat_first", "diluted_first"])
def test_neat_plus_diluted_isoeugenol_is_not_an_ifra_pass(tmp_path, neat_first):
    pair = [("Isoeugenol", "Neat", 30), ("Isoeugenol", "10% w/w in DPG", 30)]
    if not neat_first:
        pair.reverse()
    formula = _formula(
        tmp_path, [("Iso E Super", "Neat", 3000), ("Hedione", "Neat", 2940), *pair]
    )

    safety = _gate(gate_formula(formula, CONFIG), "safety_ifra_allergen")

    assert safety.status != "PASS"
    [row] = [r for r in safety.data["rows"] if r["material"] == "Isoeugenol"]
    # 30 uL neat + 3 uL active from the 10% row = 33 uL x 1.08 g/mL in ~24.9 g.
    assert row["actual_pct"] == pytest.approx(0.143, rel=0.02)


@pytest.mark.parametrize("neat_first", [True, False], ids=["neat_first", "diluted_first"])
def test_neat_plus_diluted_hedione_keeps_each_rows_active_volume(tmp_path, neat_first):
    pair = [("Hedione", "Neat", 3000), ("Hedione", "10% w/w in DPG", 1000)]
    if not neat_first:
        pair.reverse()
    formula = _formula(tmp_path, [("Iso E Super", "Neat", 1000), *pair])

    state = gate_formula(formula, CONFIG).formula_state

    [hedione] = [m for m in state.materials if m.name == "Hedione"]
    assert hedione.raw_ul == pytest.approx(4000.0)
    assert hedione.active_ul == pytest.approx(3100.0)


def test_two_strength_rows_under_the_limit_hold_the_ifra_check(tmp_path):
    formula = _formula(
        tmp_path,
        [
            ("Iso E Super", "Neat", 3000),
            ("Hedione", "Neat", 2940),
            ("Isoeugenol", "Neat", 2),
            ("Isoeugenol", "10% w/w in DPG", 10),
        ],
    )

    safety = _gate(gate_formula(formula, CONFIG), "safety_ifra_allergen")

    assert safety.status == "HOLD"
    assert "Isoeugenol" in safety.detail
    assert safety.data["stock_conflicts"] == ["Isoeugenol"]


def test_a_row_with_no_strength_takes_the_written_dilution_and_holds(tmp_path):
    formula = _formula(
        tmp_path,
        [
            ("Iso E Super", "Neat", 3000),
            ("Hedione", "Neat", 2940),
            ("Vanillin", "10% w/w in DPG", 388),
            ("Vanillin", "", 388),
        ],
    )

    report = gate_formula(formula, CONFIG)

    [vanillin] = [m for m in report.formula_state.materials if m.name == "Vanillin"]
    assert vanillin.raw_ul == pytest.approx(776.0)
    assert vanillin.active_ul == pytest.approx(77.6)
    safety = _gate(report, "safety_ifra_allergen")
    assert safety.status == "HOLD"
    reason = "Vanillin: one row gives no strength, another gives 10%; confirm which bottle"
    assert reason in safety.detail
    assert safety.data["unwritten_strengths"] == [reason]
    assert "stock_conflicts" not in safety.data


def test_a_neat_row_and_a_row_with_no_strength_are_one_neat_stock(tmp_path):
    formula = _formula(
        tmp_path,
        [
            ("Iso E Super", "Neat", 3000),
            ("Hedione", "Neat", 2940),
            ("Benzyl Acetate", "Neat", 40),
            ("Benzyl Acetate", "", 20),
        ],
    )

    report = gate_formula(formula, CONFIG)

    [acetate] = [m for m in report.formula_state.materials if m.name == "Benzyl Acetate"]
    assert acetate.active_ul == pytest.approx(60.0)
    safety = _gate(report, "safety_ifra_allergen")
    assert "Benzyl Acetate" not in safety.detail
    assert "unwritten_strengths" not in safety.data
    assert "stock_conflicts" not in safety.data


def _composer_row(material: str, amount: str, fraction: str, basis: str, carrier: str) -> dict:
    return {
        "material": material,
        "amount_decimal": amount,
        "amount_unit": "uL",
        "stock_fraction_decimal": fraction,
        "fraction_basis": basis,
        "carrier": carrier,
    }


def test_the_composer_path_holds_a_material_written_at_two_strengths():
    from engine.formulation_intelligence.composition_checks import _gate_formula_record
    from engine.pipeline.gates import run_composition_gates

    record, unchecked = _gate_formula_record(
        "Two strength draft",
        [
            _composer_row("Iso E Super", "3000", "1", "neat", ""),
            _composer_row("Hedione", "2940", "1", "neat", ""),
            _composer_row("Isoeugenol", "2", "1", "neat", ""),
            _composer_row("Isoeugenol", "10", "0.1", "mass_fraction", "DPG"),
        ],
    )

    assert unchecked == []
    spec = record["stock_specs"]["Isoeugenol"]
    assert spec["conflict"] is True
    # Never one row's strength with another row's basis or carrier.
    assert (spec["fraction_basis"], spec["carrier"]) == ("unspecified", "")
    active = record["ingredients_ul"]["Isoeugenol"] * record["dilutions"]["Isoeugenol"]
    assert active == pytest.approx(3.0)
    gates = run_composition_gates(record, CONFIG)
    [safety] = [g for g in gates if g.gate == "safety_ifra_allergen"]
    assert safety.status == "HOLD"
    assert safety.data["stock_conflicts"] == ["Isoeugenol"]
