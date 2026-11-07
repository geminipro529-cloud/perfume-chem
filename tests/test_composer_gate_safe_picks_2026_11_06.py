"""Composer picks the release gate can pass (engine fault hunt, 6 Nov 2026).

9 of 34 benchmark formulas failed the gate on a composer pick: a stock with
no odour threshold or physics data, an opaque pre-blend, two labels of one
vetiver oil, or a 5 uL neat Cade row while the 1% stock sat unused.
"""

from __future__ import annotations

from functools import lru_cache
from types import SimpleNamespace

import pytest

from engine.formulation_intelligence import formula_solver as solver
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)
from engine.research.composition_planner import Choice


@lru_cache(maxsize=1)
def _index():
    return build_material_capability_index()


def _capability(identity: str, dilution: float):
    for capability in _index().capabilities:
        if (
            capability.identity_name == identity
            and float(capability.candidate.stock.dilution) == dilution
            and capability.execution_ready
        ):
            return capability
    pytest.skip(f"{identity} at {dilution} is not in current stock")


@pytest.mark.parametrize(
    ("identity", "gate"),
    [
        # Ethyl Acetoacetate (no air ODT on 6 Nov) is scored since #187.
        ("Mate Absolute", "physics_data_coverage"),
        ("Iris Florentina Root Extract", "physics_data_coverage"),
        ("Cassis Base 345B", "opaque_preblends"),
        ("Lilyreal ND", "opaque_preblends"),
    ],
)
def test_composer_skips_a_stock_the_gate_fails_alone(identity: str, gate: str) -> None:
    rejected = solver._gate_rejects(identity)
    assert rejected, f"{identity} should be rejected"
    assert rejected == gate


@pytest.mark.parametrize("identity", ["Bergamot FCF Oil Sicilian", "Cedroxyde", "Hedione"])
def test_composer_keeps_stocks_the_gate_scores(identity: str) -> None:
    assert solver._gate_rejects(identity) == ""


def test_two_labels_of_one_vetiver_count_as_one_material() -> None:
    assert solver._gate_canonical("Haitian Vetiver EO") == solver._gate_canonical("Vetiver EO (Haiti)")
    owned = next(c for c in _index().capabilities if c.identity_name == "Vetiver EO (Haiti)")
    other = SimpleNamespace(identity_name="Haitian Vetiver EO")
    state = SimpleNamespace(assignments=((None, owned, 1.0),))
    assert solver._gate_duplicate(other, state) == "Vetiver EO (Haiti)"


def test_a_different_material_is_not_a_gate_duplicate() -> None:
    owned = next(c for c in _index().capabilities if c.identity_name == "Vetiver EO (Haiti)")
    state = SimpleNamespace(assignments=((None, owned, 1.0),))
    assert solver._gate_duplicate(SimpleNamespace(identity_name="Cedroxyde"), state) is None


def _short_cade(amount: str = "5"):
    neat = _capability("Cade Oil Rectified", 1.0)
    role = SimpleNamespace(role_id="facet_smoke_char")
    assignment = solver.SolvedAssignment(role=role, capability=neat, score=1.0, alternatives=())
    choice = Choice(role=role, candidate=neat.candidate, score=1.0, alternatives=())
    rows = [{
        "slot": "facet_smoke_char", "amount_decimal": amount, "amount_unit": "uL",
        "operation": "PREPARED_DILUTION_REQUIRED",
    }]
    return (assignment,), (choice,), rows


def test_a_neat_row_under_10_ul_pours_the_owned_1pct_stock() -> None:
    assignments, choices, rows = _short_cade()
    moved = solver._pour_sub_transfer_rows(assignments, choices, rows, _index(), ())
    assert moved is not None
    new_assignments, new_choices, pours = moved
    assert float(new_choices[0].candidate.stock.dilution) == 0.01
    assert new_assignments[0].capability.candidate is new_choices[0].candidate
    # Same active Cade: 5 uL neat = 500 uL of the 1% stock.
    assert pours == ({
        "scope": "MATERIAL_DOSE", "material": new_choices[0].candidate.stock.name,
        "amount_decimal": "500", "unit": "uL",
    },)


def test_a_requested_dose_stays_as_asked() -> None:
    assignments, choices, rows = _short_cade()
    asked = ({"scope": "MATERIAL_DOSE", "material": "Cade Oil Rectified", "amount_decimal": "5", "unit": "uL"},)
    assert solver._pour_sub_transfer_rows(assignments, choices, rows, _index(), asked) is None


def test_a_row_at_10_ul_or_more_is_left_alone() -> None:
    assignments, choices, rows = _short_cade()
    rows[0]["operation"] = "DIRECT_ADD"
    rows[0]["amount_decimal"] = "12"
    assert solver._pour_sub_transfer_rows(assignments, choices, rows, _index(), ()) is None


def test_a_brief_naming_one_oil_twice_gets_one_anchor() -> None:
    from engine.formulation_intelligence.semantic_brief_adapter import _one_anchor_per_material

    assert _one_anchor_per_material(("haitian vetiver eo", "Vetiver EO (Haiti)")) == ("Vetiver EO (Haiti)",)
    # The gate allows Hedione with Hedione HC, so both stay.
    assert _one_anchor_per_material(("Hedione", "Hedione HC")) == ("Hedione", "Hedione HC")
    assert _one_anchor_per_material(("Iso E Super", "Cedroxyde")) == ("Iso E Super", "Cedroxyde")
