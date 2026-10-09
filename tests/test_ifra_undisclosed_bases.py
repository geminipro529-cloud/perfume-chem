"""Supplier bases with no published composition, and Aurantiol's hydroxycitronellal.

Kenny (2026-10-09): a formula using a supplier base whose composition is not published
gets a named warning, never a block. Aurantiol is the Schiff base of hydroxycitronellal and
methyl anthranilate; 56.4 % of its mass is hydroxycitronellal, counted toward that total.
"""

import pytest

from engine.ifra_standards import evaluate_ifra, load_natural_constituents
from engine.pipeline import gates
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig, _gate_safety

HC_LIMIT = 2.1  # IFRA_STD_043 Category 4


def _gate(ingredients):
    state = build_formula_state(
        ingredients, {name: 1.0 for name in ingredients}, batch_volume_ml=30.0
    )
    return _gate_safety(state, ReleaseGateConfig(batch_volume_source="title"))


# --------------------------------------------------------------------------- bases


def test_tonkarome_warns_by_name_and_without_it_the_verdict_is_unchanged():
    without = _gate({"Evernyl": 240.0})
    gate = _gate({"Evernyl": 240.0, "Tonkarome": 10.0})

    assert without.status == "PASS"
    assert without.data["undisclosed_bases"] == []
    assert gate.status == "WARN"
    assert "Tonkarome" in gate.detail
    assert "composition not published" in gate.detail
    assert "not counted" in gate.detail
    assert gate.data["holds"] == []
    (flag,) = gate.data["undisclosed_bases"]
    assert flag["material"] == "Tonkarome"
    assert flag["base"] == "Tonkarome"
    assert "composition is not published" in flag["message"]
    assert "not counted" in flag["message"]


def test_a_diluted_stock_name_is_flagged_as_its_base():
    gate = _gate({"Evernyl": 240.0, "Suederal 10%": 10.0})
    assert gate.status == "WARN"
    assert [u["base"] for u in gate.data["undisclosed_bases"]] == ["Suederal"]
    assert "Suederal 10%" in gate.detail


def test_a_base_never_lowers_a_hold_or_a_fail():
    held = _gate({"Evernyl": 240.0, "Vertofix": 20.0, "Tonkarome": 10.0})
    assert held.status == "HOLD"
    assert "Vertofix" in held.detail and "Tonkarome" in held.detail

    failed = _gate({"Hydroxycitronellal": 2000.0, "Tonkarome": 10.0})
    assert failed.status == "FAIL"
    assert "Tonkarome" in failed.detail


@pytest.mark.parametrize(
    "ingredients",
    [
        {"Evernyl": 240.0},
        {"Evernyl": 240.0, "Vertofix": 20.0},
        {"Hydroxycitronellal": 2000.0},
        {"Hydroxycitronellal": 450.0, "Evernyl": 240.0},
    ],
)
def test_a_formula_with_no_base_is_unchanged(monkeypatch, ingredients):
    gate = _gate(ingredients)
    monkeypatch.setattr(gates, "load_undisclosed_bases", lambda: ())
    before = _gate(ingredients)
    assert gate.data["undisclosed_bases"] == []
    assert (gate.status, gate.detail) == (before.status, before.detail)


# --------------------------------------------------------------------------- Aurantiol


def test_aurantiol_share_is_56_4_percent_hydroxycitronellal():
    schiff = load_natural_constituents().schiff_bases["Aurantiol"]
    assert schiff.standard == "IFRA_STD_043"
    assert schiff.share_pct == pytest.approx(172.27 / 305.41 * 100, abs=0.05)
    assert "IFRA text not read" in schiff.source


def test_aurantiol_and_hydroxycitronellal_fail_together_but_not_alone():
    alone_a = evaluate_ifra({"Aurantiol 10% in DPG": 3.0})
    alone_h = evaluate_ifra({"Hydroxycitronellal": 1.5})
    both = evaluate_ifra({"Aurantiol 10% in DPG": 3.0, "Hydroxycitronellal": 1.5})

    assert not alone_a.failures and not alone_h.failures
    group = next(g for g in both.group_checks if g.id == "IFRA_STD_043_constituents")
    assert group.verdict == "fail"
    assert group.total == pytest.approx(1.5 + 3.0 * 0.564)
    assert set(group.member_pcts) == {"Aurantiol", "Hydroxycitronellal"}
    assert "Schiff base" in group.message
    (total,) = both.constituent_totals
    kinds = {c.material: c.kind for c in total.contributors}
    assert kinds == {"Aurantiol": "schiff_base", "Hydroxycitronellal": "synthetic"}
    row = next(c for c in both.checks if c.material == "Aurantiol 10% in DPG")
    assert row.verdict == "pass" and row.ifra_name == "Aurantiol"


def test_gate_fails_naming_both():
    gate = _gate({"Hydroxycitronellal": 450.0, "Aurantiol": 600.0})
    rows = {r["material"]: r["actual_pct"] for r in gate.data["rows"]}
    assert rows["Hydroxycitronellal"] < HC_LIMIT
    assert rows["Aurantiol"] * 0.564 < HC_LIMIT
    assert rows["Hydroxycitronellal"] + rows["Aurantiol"] * 0.564 > HC_LIMIT
    assert gate.status == "FAIL"
    assert "Aurantiol" in gate.detail and "Hydroxycitronellal" in gate.detail
    (total,) = gate.data["constituent_totals"]
    assert {c["kind"] for c in total["contributors"]} == {"schiff_base", "synthetic"}
