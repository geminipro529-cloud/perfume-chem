"""A named note's lead takes a grade that can carry the lead's share.

Role fit ignores stock strength, so grades of one material score within
hundredths of each other and the beam used to pick one by synergy credit
matched on name text: the aromatic fougere's lavender lead was the 1% dilution
("Lavender EO") although Kenny owns neat Lavender EO (BONTAUX SAS). A trace
stock (below 5%) keeps a trace-scaled raw volume, so it cannot carry a lead.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from engine.formulation_intelligence import formula_solver as fs
from engine.formulation_intelligence.formula_design_runtime import design_formula


def _cap(name, dilution, *, stock_id=None, design_ready=True):
    return SimpleNamespace(
        identity_name=name,
        stock_id=stock_id or f"{name}@{dilution}",
        candidate=SimpleNamespace(
            stock=SimpleNamespace(dilution=dilution),
            profile=SimpleNamespace(synergies=()),
        ),
        character_map={},
        note="heart",
        design_ready=design_ready,
        execution_ready=design_ready,
    )


def _role(role_id, *, provenance="PROMPT_DERIVED_FACET", exact_material=None):
    return SimpleNamespace(
        role_id=role_id, provenance=provenance, exact_material=exact_material,
    )


_EMPTY = fs._BeamState(assignments=(), used_identities=frozenset(), group_counts=(), objective=0.0)
_DILUTION = _cap("Lavender EO", .01)
_NEAT = _cap("Lavender EO (BONTAUX SAS)", 1.0)


def _ranked(role, ranked, monkeypatch, **kwargs):
    monkeypatch.setattr(fs, "_allowed", lambda *_args, **_kwargs: True)
    out = fs._rank_for_state(ranked, role, _EMPTY, avoid=(), allow_multiple_musks=False, **kwargs)
    return [capability for _score, capability in out]


def _top(role, ranked, monkeypatch):
    return [capability.identity_name for capability in _ranked(role, ranked, monkeypatch)]


def test_a_facet_lead_skips_a_trace_grade_when_a_stronger_grade_is_owned(monkeypatch):
    # The dilution ranks first, as the beam's synergy credit made it rank.
    ranked = [(15.2, _DILUTION), (15.1, _NEAT)]
    assert _top(_role("facet_aromatic_lavender"), ranked, monkeypatch) == [
        "Lavender EO (BONTAUX SAS)"
    ]


def test_an_explicit_anchor_skips_a_trace_grade_too(monkeypatch):
    ranked = [(15.2, _DILUTION), (15.1, _NEAT)]
    role = _role("explicit_anchor_1", provenance="EXPLICIT_REQUEST_MATERIAL",
                 exact_material="lavender")
    assert _top(role, ranked, monkeypatch) == ["Lavender EO (BONTAUX SAS)"]


def test_a_stronger_grade_another_named_stock_claims_does_not_count(monkeypatch):
    # "lavender eo" beside "Lavender EO (BONTAUX SAS)": the neat grade is the
    # other anchor's, so this anchor keeps the 1% grade.
    ranked = [(15.2, _DILUTION), (15.1, _NEAT)]
    role = _role("explicit_anchor_1", provenance="EXPLICIT_REQUEST_MATERIAL",
                 exact_material="lavender eo")
    out = _ranked(role, ranked, monkeypatch, reserved_identities=frozenset({"lavender eo bontaux sas"}))
    assert [c.identity_name for c in out] == ["Lavender EO", "Lavender EO (BONTAUX SAS)"]


def test_two_named_lavender_grades_each_keep_a_design_ready_stock():
    """The brief names "lavender eo" and the solver reads it as both the 1%
    stock and the neat BONTAUX oil: each anchor keeps a design-ready lavender,
    and no unready Spike Lavender stands in for the first."""

    result = design_formula(idea="A herbal cologne with lavender eo.", design_mode="FAST_SKETCH")
    rows = {row["slot"]: row for row in result["design_variants"][0]["formula"]["rows"]}
    anchors = [rows[slot] for slot in rows if slot.startswith("explicit_anchor_") and "__" not in slot]
    assert len(anchors) == 2
    assert all(row["design_ready"] and "spike" not in row["identity_name"].casefold() for row in anchors)


def test_a_same_name_stronger_grade_also_counts(monkeypatch):
    ranked = [(9.2, _cap("Hexyl Acetate", .01)), (9.1, _cap("Hexyl Acetate", .1))]
    out = _ranked(_role("facet_fruit"), ranked, monkeypatch)
    assert [(c.identity_name, c.candidate.stock.dilution) for c in out] == [("Hexyl Acetate", .1)]


def test_a_trace_role_keeps_its_dilution(monkeypatch):
    ranked = [(15.2, _DILUTION), (15.1, _NEAT)]
    for role in (
        _role("facet_aromatic_lavender__accord_1", provenance="ACCORD_SUPPORT"),
        _role("accent_detail", provenance="ACCENT_LAYER"),
        _role("heart_continuity", provenance="FUNCTIONAL_COVERAGE"),
    ):
        assert _top(role, ranked, monkeypatch) == ["Lavender EO", "Lavender EO (BONTAUX SAS)"]


def test_a_trace_lead_with_no_stronger_owned_grade_stays(monkeypatch):
    calone = _cap("Calone", .01)
    held_neat = _cap("Calone", 1.0, design_ready=False)
    other = _cap("Helional", 1.0)
    ranked = [(12.0, calone), (11.0, held_neat), (10.0, other)]
    assert _top(_role("facet_rain_water"), ranked, monkeypatch)[0] == "Calone"
    # A different material is not a grade of it, even when it is neat.
    assert _top(_role("facet_rain_water"), [(12.0, calone), (10.0, other)], monkeypatch) == [
        "Calone", "Helional",
    ]


@pytest.mark.parametrize("mode", ["FAST_SKETCH", "DEEP_COMPOSE"])
def test_the_fougere_lavender_lead_carries_its_share(mode):
    result = design_formula(idea="an aromatic fougere", liquid_concentrate_ul_decimal="6000",
                            design_mode=mode)
    formulas = [result["optimized_formula"]]
    formulas += [v["formula"] for v in result.get("design_variants") or [] if v.get("formula")]
    leads = [
        row for formula in formulas for row in formula["rows"]
        if row["slot"] == "facet_aromatic_lavender"
    ]
    assert leads
    for row in leads:
        assert "lavender" in row["identity_name"].casefold()
        assert float(row["stock_fraction_decimal"]) >= .05, row["identity_name"]
