"""The safety gate judges IFRA Category 4 by finished-product % w/w from the sourced table.

Hand-worked numbers use the gate's estimate: finished mass = active mass + carrier mass +
ethanol top-up x 0.789 g/mL. Every row below has an unknown density, so 1.0 g/mL is used.
"""

from dataclasses import replace

import pytest

from engine.ifra_standards import load_ifra_table
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig, _gate_safety

TABLE = load_ifra_table()


def _gate(ingredients, dilutions=None, **config):
    config.setdefault("batch_volume_source", "title")
    state = build_formula_state(
        ingredients,
        dilutions or {name: 1.0 for name in ingredients},
        batch_volume_ml=config.get("batch_volume_ml", 30.0),
    )
    return _gate_safety(state, ReleaseGateConfig(**config))


def _row(gate, material):
    return next(r for r in gate.data["rows"] if r["material"] == material)


def test_restricted_material_is_judged_by_weight_not_volume():
    bb = TABLE.lookup("Benzyl Benzoate")
    assert bb.status == "restricted" and bb.cat4_limit_pct == pytest.approx(4.8)
    # 1400 uL neat in a 30 mL bottle: 1.4 / 30 = 4.667 % v/v, under 4.8 %.
    # By weight: 1.4 g / (1.4 g + 28.6 mL x 0.789) = 1.4 / 23.9654 = 5.842 % w/w, over 4.8 %.
    gate = _gate({"Benzyl Benzoate": 1400.0})

    row = _row(gate, "Benzyl Benzoate")
    assert row["actual_pct"] == pytest.approx(1.4 / 23.9654 * 100, rel=1e-4)
    assert row["limit_pct"] == pytest.approx(4.8)
    assert gate.status == "FAIL"
    assert [v["material"] for v in gate.data["headroom_violations"]] == ["Benzyl Benzoate"]
    assert gate.data["concentration_basis"] == "finished_product_w_w_estimate"
    assert gate.data["finished_mass_g"] == pytest.approx(23.9654, rel=1e-5)
    assert any("Benzyl Benzoate" in a for a in gate.data["assumptions"])


def test_evernyl_at_one_percent_no_longer_fails():
    assert TABLE.lookup("Evernyl").status == "no_standard"
    # 240 uL neat: 0.24 / (0.24 + 29.76 x 0.789) = 0.24 / 23.72064 = 1.012 % w/w.
    gate = _gate({"Evernyl": 240.0})

    row = _row(gate, "Evernyl")
    assert row["actual_pct"] == pytest.approx(0.24 / 23.72064 * 100, rel=1e-4)
    assert row["verdict"] == "pass"
    assert gate.status != "FAIL"
    assert gate.data["headroom_violations"] == []


def test_oakmoss_and_treemoss_are_totalled_against_the_group_limit():
    rule = next(g for g in TABLE.group_rules if g.id == "oakmoss_treemoss_total")
    assert rule.limit_pct == pytest.approx(0.1)
    # 15 uL each, neat: finished mass 0.03 + 29.97 x 0.789 = 23.67633 g.
    # Each 0.015 / 23.67633 = 0.0634 % (63 % of 0.1, passes alone); together 0.1267 % > 0.1 %.
    gate = _gate({"Oakmoss Absolute": 15.0, "Treemoss Absolute": 15.0})

    each = 0.015 / 23.67633 * 100
    assert _row(gate, "Oakmoss Absolute")["verdict"] == "pass"
    assert _row(gate, "Treemoss Absolute")["verdict"] == "pass"
    group = next(g for g in gate.data["groups"] if g["group"] == "oakmoss_treemoss_total")
    assert group["actual_pct"] == pytest.approx(2 * each, rel=1e-4)
    assert group["verdict"] == "fail"
    assert gate.status == "FAIL"
    violation = next(
        v for v in gate.data["headroom_violations"] if v["material"] == "oakmoss_treemoss_total"
    )
    assert set(violation["members"]) == {"Oakmoss Absolute", "Treemoss Absolute"}


def test_overfilled_bottle_holds():
    # 1500 uL of stock cannot fit a 1 mL bottle; % w/w of the finished product is undefined.
    gate = _gate({"Hedione": 1500.0}, batch_volume_ml=1.0)

    assert gate.status == "HOLD"
    assert gate.data["overfilled"] is True


def test_default_bottle_size_warns_and_is_reported():
    # Hedione has no IFRA standard: 100 uL neat in 30 mL passes on its own.
    named = _gate({"Hedione": 100.0}, batch_volume_source="title")
    default = _gate({"Hedione": 100.0}, batch_volume_source="default")

    assert named.status == "PASS"
    assert default.status == "WARN"
    assert default.data["batch_volume_source"] == "default"
    assert "default" in default.detail


def test_row_with_dilution_suffix_matches_its_standard():
    benzyl = TABLE.lookup("Benzyl Benzoate")
    assert TABLE.lookup("Benzyl Benzoate (10% in DPG)") is benzyl
    # 1000 uL of a 10 % stock = 0.1 g active + 0.9 mL carrier (DPG not recorded: 1.0 g/mL)
    # + 29 mL ethanol x 0.789 = 22.881 g; 0.1 / 23.881 = 0.419 % w/w.
    gate = _gate({"Benzyl Benzoate (10% in DPG)": 1000.0}, {"Benzyl Benzoate (10% in DPG)": 0.1})

    row = _row(gate, "Benzyl Benzoate (10% in DPG)")
    assert row["standard"] == benzyl.standard
    assert row["limit_pct"] == pytest.approx(benzyl.cat4_limit_pct)
    assert row["actual_pct"] == pytest.approx(0.1 / 23.881 * 100, rel=1e-4)
    assert row["verdict"] == "pass"
    assert "Benzyl Benzoate (10% in DPG)" not in gate.data["unchecked"]


def test_exact_finished_product_ppm_is_used_when_available():
    state = build_formula_state({"Benzyl Benzoate": 1400.0}, {"Benzyl Benzoate": 1.0})
    # The estimate would give 5.842 % (fail); the exact chain says 40000 ppm = 4.0 % w/w,
    # 83 % of the 4.8 % limit: a warning, not a failure.
    exact = replace(
        state,
        materials=tuple(
            replace(m, active_finished_product_ppm_w_w=40000.0) for m in state.materials
        ),
    )
    assert exact.exact_finished_product_ppm_available

    gate = _gate_safety(exact, ReleaseGateConfig(batch_volume_source="title"))

    row = _row(gate, "Benzyl Benzoate")
    assert row["actual_pct"] == pytest.approx(4.0)
    assert row["verdict"] == "warn"
    assert gate.data["concentration_basis"] == "exact_finished_product_w_w"
    assert gate.status == "WARN"


def test_strength_suffix_in_the_row_name_does_not_hide_a_restricted_material():
    coumarin = TABLE.lookup("Coumarin")
    assert coumarin.cat4_limit_pct == pytest.approx(1.5)
    # 3000 uL of a 20 % stock = 0.6 g active + 2.4 mL carrier (not recorded: 1.0 g/mL)
    # + 27 mL ethanol x 0.789 = 21.303 g; 0.6 / 24.303 = 2.469 % w/w, over 1.5 %.
    gate = _gate({"Coumarin 20% EtOH": 3000.0}, {"Coumarin 20% EtOH": 0.2})

    row = _row(gate, "Coumarin 20% EtOH")
    assert row["standard"] == coumarin.standard
    assert row["actual_pct"] == pytest.approx(0.6 / 24.303 * 100, rel=1e-4)
    assert row["verdict"] == "fail"
    assert gate.status == "FAIL"
    assert "Coumarin 20% EtOH" not in gate.data["unchecked"]


def test_declared_volume_fraction_basis_reaches_the_finished_weight_estimate():
    # 3000 uL of 20 % Coumarin in DEP, declared v/v (formula_state basis "volume_fraction").
    # Active density is unknown (1.0 g/mL); DEP is 1.12 g/mL.
    # v/v: 0.6 g active + 2.4 mL x 1.12 = 2.688 g carrier + 27 mL ethanol x 0.789 = 21.303 g
    # -> 24.591 g finished, 0.6 / 24.591 = 2.4399 % w/w.
    # A w/w reading would be 0.65625 g active in 24.58425 g (2.6694 %), more than 0.5 % away.
    name = "Coumarin 20% DEP"
    state = build_formula_state(
        {name: 3000.0},
        {name: 0.2},
        batch_volume_ml=30.0,
        stock_specs={name: {"fraction_basis": "volume_fraction", "carrier": "DEP"}},
    )
    assert state.materials[0].stock_fraction_basis == "volume_fraction"
    gate = _gate_safety(state, ReleaseGateConfig(batch_volume_source="title"))

    by_volume = 0.6 / 24.591 * 100
    by_weight = 0.65625 / 24.58425 * 100
    assert abs(by_weight - by_volume) / by_volume > 0.005
    row = _row(gate, name)
    assert row["actual_pct"] == pytest.approx(by_volume, rel=1e-4)
    assert not any(
        name in a and "dilution basis not recorded" in a for a in gate.data["assumptions"]
    )
