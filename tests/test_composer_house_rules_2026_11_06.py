"""Kenny's house rules in the composer (engine fault hunt, 6 Nov 2026, fix 5).

Hedione at most the gate's share of the active oil (15%, 12% in a chypre);
no sweet or berry stock a brief does not ask for; never the Hexyl Acetate
with Ethyl 2-Methylbutyrate fruity top (an apple brief keeps the ester); and a vial test before the bottle
when two cineole or camphor oils share a formula.
"""

from __future__ import annotations

from decimal import Decimal
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


def _capability(identity: str, dilution: float = 1.0):
    return next(
        c for c in _index().capabilities
        if c.identity_name == identity and float(c.candidate.stock.dilution) == dilution
    )


@pytest.mark.parametrize(
    ("identity", "brief", "verdict"),
    [
        ("Raspberry Ketone", "a fruity floral femme", "berry"),
        ("Raspberry Ketone", "a raspberry and rose", None),
        ("Vanillin", "an aromatic fougere with lavender", "sweet"),
        ("Vanillin", "a vanilla amber", None),
        ("Coumarin", "an aromatic fougere with lavender", None),
        ("Coumarin", "a green tea cologne", "sweet"),
        ("Bergamot FCF Oil Sicilian", "a green tea cologne", None),
    ],
)
def test_sweet_and_berry_stocks_wait_for_the_brief(identity: str, brief: str, verdict: str | None) -> None:
    assert solver._unasked_sweet_or_berry(SimpleNamespace(identity_name=identity), brief) == verdict


def test_the_disliked_fruity_top_pair_is_blocked() -> None:
    hexyl = _capability("Hexyl Acetate", 0.1)
    e2mb = _capability("Ethyl 2-Methylbutyrate", 0.01)
    role = SimpleNamespace(
        exact_material=None, provenance="FUNCTIONAL_COVERAGE", knowledge_role_slot=None,
        descriptor_requirement=None,
    )
    state = SimpleNamespace(
        used_identities=frozenset({solver._chemical_identity(e2mb)}),
        assignments=((role, e2mb, 1.0),),
        lasting_spice_brief=False,
    )
    reason = solver._block_reason(hexyl, role, state, avoid=(), allow_multiple_musks=True)
    assert reason is not None and "fruity top" in reason


def _brief(text: str, *role_ids: str):
    roles = tuple(SimpleNamespace(role_id=r, exact_material=None) for r in role_ids)
    return SimpleNamespace(formula_name="Test", normalized_request=text, roles=roles)


def test_an_apple_brief_keeps_the_apple_ester_and_drops_hexyl_acetate() -> None:
    assert solver._apple_ester_planned(_brief("a pear and apple femme"))
    assert solver._apple_ester_planned(_brief("a fruity femme", "family_ethyl_2_methylbutyrate_layer"))
    assert not solver._apple_ester_planned(_brief("a pear and lychee femme", "facet_fruit"))
    assert not solver._apple_ester_planned(_brief("pineapple rum"))


def _rows(hedione_ul: int, others_ul: int):
    hedione = _capability("Hedione")
    iso = _capability("Iso E Super")
    choices = (
        Choice(role=SimpleNamespace(role_id="heart"), candidate=hedione.candidate, score=1.0, alternatives=()),
        Choice(role=SimpleNamespace(role_id="wood"), candidate=iso.candidate, score=1.0, alternatives=()),
    )
    rows = [
        {"slot": "heart", "amount_decimal": str(hedione_ul), "amount_unit": "uL", "stock_fraction_decimal": "1"},
        {"slot": "wood", "amount_decimal": str(others_ul), "amount_unit": "uL", "stock_fraction_decimal": "1"},
    ]
    return choices, rows


def test_hedione_comes_back_to_15_percent_of_the_active_oil() -> None:
    choices, rows = _rows(900, 2100)  # 30% of the active oil
    (pour,) = solver._hedione_pours(choices, rows, (), "a clean musky skin scent")
    # 15% of the active: 0.15 / 0.85 x 2100 = 370.6 uL
    assert pour["material"] == "Hedione" and pour["amount_decimal"] == "370"
    share = Decimal(pour["amount_decimal"]) / (Decimal(pour["amount_decimal"]) + 2100)
    assert share <= Decimal("0.15")


def test_a_chypre_takes_the_gate_chypre_cap() -> None:
    choices, rows = _rows(900, 2100)
    (pour,) = solver._hedione_pours(choices, rows, (), "a rose chypre")
    assert pour["amount_decimal"] == "286"  # 0.12 / 0.88 x 2100


def test_hedione_under_the_cap_or_named_by_the_brief_is_left_alone() -> None:
    choices, rows = _rows(300, 2700)
    assert solver._hedione_pours(choices, rows, (), "a clean musky skin scent") == ()
    choices, rows = _rows(900, 2100)
    assert solver._hedione_pours(choices, rows, (), "a Hedione overdose, airy jasmine") == ()


def test_two_cineole_oils_get_a_vial_test() -> None:
    def assignment(identity: str):
        return SimpleNamespace(capability=_capability(identity))

    step = solver._cineole_vial_step([assignment("Rosemary EO"), assignment("Lavender 40/42, Aroma&More")])
    assert step is not None and step["step"] == "VIAL_TEST_CINEOLE_STACK"
    assert step["materials"] == ["Lavender 40/42, Aroma&More", "Rosemary EO"]
    assert solver._cineole_vial_step([assignment("Rosemary EO"), assignment("Iso E Super")]) is None
