"""The composer builds on the grades Kenny owns, and weighs Ambrox Super crystals.

Role fit ignores stock strength, so a grade nobody owns used to win whenever
it scored a hundredth higher: the index's Ambrettolide 10% (he owns the neat
stock only) and neat Safraleine (he owns the 10% only).  A base, fixative or
structure role, or a note's lead, now takes the strongest owned grade.

The amber base used to carry its Ambrox Super as the 25% solution, with its
carrier solvent.  The owned crystals now stand in, weighed in mg: the
ambroxide the 25% solution would have carried in that role, so the whole
amber base keeps its balance and Ambrox never moves alone.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from types import SimpleNamespace

import pytest

from engine.formulation_intelligence import formula_solver as fs
from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)
from tests.reheld_overlay import neat_ambrettolide_owned


@pytest.fixture(scope="module", autouse=True)
def _neat_ambrettolide_owned(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    # The cached helpers below are built once, so the whole module sees the neat Ambrettolide.
    with neat_ambrettolide_owned(tmp_path_factory.mktemp("overlay")):
        yield

_CRYSTALS = "inventory:user-20260924:36e0e28366f34673a242"  # Ambrox Super Crystals, neat
_AMBROX_25 = "inventory:user-20260902:9e69f9db20c45cfe37e6"  # Ambrox Super 25% solution
_NEAT_AMBRETTOLIDE = "inventory:user-20261008:6d686e2d06cb826cc79f"
_EMPTY = fs._BeamState(assignments=(), used_identities=frozenset(), group_counts=(), objective=0.0)


def _cap(name, dilution, *, owned=True, vp=None):
    return SimpleNamespace(
        identity_name=name,
        stock_id=f"{name}@{dilution}",
        candidate=SimpleNamespace(
            stock=SimpleNamespace(dilution=dilution),
            profile=SimpleNamespace(synergies=(), vp=vp),
        ),
        character_map={},
        note="base",
        design_ready=True,
        execution_ready=owned,
    )


def _role(role_id, provenance, note, function):
    return SimpleNamespace(
        role_id=role_id, provenance=provenance, exact_material=None, note=note, function=function,
    )


_BASE_MUSK = _role("base_musk_layer", "LAYERED_BASE_ARCHITECTURE", "base", "structure")
_BASE_WOOD = _role("base_wood_contrast", "LAYERED_BASE_ARCHITECTURE", "base", "structure")
_HEART_BRIDGE = _role("top_to_heart_link", "FUNCTIONAL_COVERAGE", "heart", "bridge")
_ACCENT = _role("family_cashmeran_accent", "ACCENT_LAYER", "base", "modifier")
_AMBER_LEAD = _role("facet_amber_mineral", "PROMPT_DERIVED_FACET", "base", "structure")


def _grades(role, ranked, monkeypatch):
    monkeypatch.setattr(fs, "_allowed", lambda *_args, **_kwargs: True)
    out = fs._rank_for_state(ranked, role, _EMPTY, avoid=(), allow_multiple_musks=False)
    return [(capability.identity_name, capability.candidate.stock.dilution) for _score, capability in out]


def test_the_owned_neat_ambrettolide_replaces_the_unowned_ten_percent(monkeypatch):
    ranked = [(9.2, _cap("Ambrettolide", .1, owned=False)), (9.1, _cap("Ambrettolide", 1.0))]
    assert _grades(_BASE_MUSK, ranked, monkeypatch)[0] == ("Ambrettolide", 1.0)


@pytest.mark.parametrize("role", [_BASE_MUSK, _HEART_BRIDGE], ids=["base", "heart-bridge"])
def test_the_owned_safraleine_ten_percent_replaces_the_unowned_neat_stock(monkeypatch, role):
    # Every role: a grade nobody owns gives way to an owned grade of it.
    ranked = [(9.2, _cap("Safraleine", 1.0, owned=False)), (9.1, _cap("Safraleine", .1))]
    assert _grades(role, ranked, monkeypatch) == [("Safraleine", .1)]


def test_a_base_structure_role_takes_the_strongest_owned_grade(monkeypatch):
    ranked = [(9.2, _cap("Cashmeran", .2)), (9.1, _cap("Cashmeran", 1.0))]
    assert _grades(_BASE_WOOD, ranked, monkeypatch) == [("Cashmeran", 1.0)]


def test_guard_a_fast_top_keeps_its_weak_grade_in_a_base_role(monkeypatch):
    ranked = [(9.2, _cap("Hexyl Acetate", .01, vp=194.0)), (9.1, _cap("Hexyl Acetate", .1, vp=194.0))]
    assert _grades(_BASE_WOOD, ranked, monkeypatch) == [("Hexyl Acetate", .01), ("Hexyl Acetate", .1)]


def test_guard_an_accent_keeps_its_weak_grade(monkeypatch):
    ranked = [(9.2, _cap("Cashmeran", .2)), (9.1, _cap("Cashmeran", 1.0))]
    assert _grades(_ACCENT, ranked, monkeypatch) == [("Cashmeran", .2), ("Cashmeran", 1.0)]


def test_guard_an_amber_lead_is_not_switched_to_a_stronger_ambrox_grade(monkeypatch):
    # The amber base moves together, through the weighed crystals only.
    ranked = [(9.2, _cap("Ambrox Super", .1)), (9.1, _cap("Ambrox Super", .25))]
    assert _grades(_AMBER_LEAD, ranked, monkeypatch) == [("Ambrox Super", .1), ("Ambrox Super", .25)]


@lru_cache(maxsize=1)
def _capabilities():
    return {capability.stock_id: capability for capability in build_material_capability_index().capabilities}


def _formulas(result):
    formulas = [result["optimized_formula"]]
    formulas += [v["formula"] for v in result.get("design_variants") or () if v.get("formula")]
    return formulas


def _issues(result):
    critics = [result["critic"], *(v["critic"] for v in result.get("design_variants") or () if v.get("critic"))]
    return [str(issue) for critic in critics for issue in critic["issues"]]


def test_a_soft_woody_amber_weighs_ambrox_crystals_as_its_25pct_solution_active(monkeypatch):
    """The amber lead is the owned crystals, weighed in mg: the active a 25%
    row of Ambrox Super carries in that role of the same formula.  At this
    commit that row fills its role's 22% raw-share cap, 1320 uL, so the
    crystals are 330 mg."""

    solution = _capabilities()[_AMBROX_25].candidate
    weighed: list[tuple[str, str]] = []
    formula_rows = fs._formula_rows

    def compare(choices, *, liquid_total_ul, quantities):
        out = formula_rows(choices, liquid_total_ul=liquid_total_ul, quantities=quantities)
        for index, choice in enumerate(choices):
            if choice.candidate.stock.stock_id != _CRYSTALS:
                continue
            as_solution = list(choices)
            as_solution[index] = replace(choice, candidate=solution)
            rows, _totals, _holds = formula_rows(
                as_solution, liquid_total_ul=liquid_total_ul, quantities=quantities,
            )
            (row,) = [row for row in rows if row["slot"] == choice.role.role_id]
            active = (Decimal(row["amount_decimal"]) * Decimal("0.25")).to_integral_value(ROUND_HALF_UP)
            (crystal,) = [row for row in out[0] if row["slot"] == choice.role.role_id]
            weighed.append((crystal["amount_decimal"], str(max(10, int(active)))))
        return out

    monkeypatch.setattr(fs, "_formula_rows", compare)
    result = design_formula(idea="A soft woody amber", liquid_concentrate_ul_decimal="6000",
                            design_mode="FAST_SKETCH")
    assert weighed and all(mg == expected for mg, expected in weighed)
    for formula in _formulas(result):
        rows = formula["rows"]
        (amber,) = [row for row in rows if row["slot"] == "facet_amber_mineral"]
        assert amber["stock_id"] == _CRYSTALS
        assert (amber["amount_unit"], amber["operation"]) == ("mg", "MASS_ADD")
        assert amber["mass_basis"] == "AMBROX_CRYSTAL_AS_25PCT_SOLUTION_ACTIVE"
        assert amber["amount_decimal"] in {mg for mg, _expected in weighed}
        assert int(amber["amount_decimal"]) >= 10
        assert [row for row in rows if row["identity_name"] == "Ambrox Super"] == [amber]
        liquids = [row for row in rows if row["amount_unit"] == "uL"]
        assert sum(int(row["amount_decimal"]) for row in liquids) == 6000
        assert formula["separate_totals"] == {
            "liquid_total_ul": "6000", "mass_total_mg": amber["amount_decimal"],
        }
    assert not [issue for issue in _issues(result) if "SOLID_MASS" in issue]


def test_the_lavender_helper_and_the_amber_lead_share_one_weighed_ambrox_row():
    result = design_formula(idea="Lavender over a mineral ambergris amber.", formula_name="Accord Probe",
                            design_mode="FAST_SKETCH")
    variant = result["design_variants"][0]
    (ambrox,) = [row for row in variant["formula"]["rows"] if row["identity_name"] == "Ambrox Super"]
    assert (ambrox["stock_id"], ambrox["amount_unit"]) == (_CRYSTALS, "mg")
    assert ambrox["slot"] == "facet_amber_mineral"
    (helper,) = [
        entry for entry in variant["solver"]["unplaced_accord_helpers"]
        if entry["carried_by"] == "facet_amber_mineral"
    ]
    assert helper["reasons"] == [
        f"Ambrox Super at {fraction}: kept for the required role {ambrox['slot_label']}"
        for fraction in ("1", "0.25", "0.1")
    ]


@pytest.mark.parametrize("idea", ["A warm vanilla and benzoin resin", "An orange blossom cologne"])
def test_guard_no_brief_without_an_amber_base_gets_a_weighed_row(idea):
    result = design_formula(idea=idea, liquid_concentrate_ul_decimal="6000", design_mode="FAST_SKETCH")
    for formula in _formulas(result):
        assert [row["identity_name"] for row in formula["rows"] if row["amount_unit"] == "mg"] == []


def test_guard_tinctures_and_oranger_crystals_are_poured_not_weighed():
    # A solution is poured whatever its name says: Oranger Crystals 10% in DPG
    # and the resin tinctures ("dissolved-solids fraction") used to read as
    # solids, so no unnamed role could take them.
    poured = [
        capability for capability in _capabilities().values()
        if "tincture" in capability.identity_name.casefold() or capability.identity_name == "Oranger Crystals"
    ]
    assert len(poured) >= 5
    assert not [capability.identity_name for capability in poured if capability.candidate.solid]


def test_guard_a_brief_naming_the_ambrox_solution_keeps_its_liquid_row():
    result = design_formula(idea="A soft woody amber with the Ambrox Super 25% solution",
                            liquid_concentrate_ul_decimal="6000", design_mode="FAST_SKETCH")
    for formula in _formulas(result):
        ambrox = [row for row in formula["rows"] if row["identity_name"] == "Ambrox Super"]
        assert [(row["stock_id"], row["amount_unit"]) for row in ambrox] == [(_AMBROX_25, "uL")]


def test_guard_a_brief_without_ambrox_gets_no_ambrox_row():
    result = design_formula(idea="A soft woody amber without Ambrox",
                            liquid_concentrate_ul_decimal="6000", design_mode="FAST_SKETCH")
    for formula in _formulas(result):
        assert not [row for row in formula["rows"] if "ambrox" in row["identity_name"].casefold()]


def test_the_quiet_skin_capsule_takes_the_owned_neat_ambrettolide():
    # The intimate-skin capsule prefers "ambrettolide 10", a grade Kenny does
    # not own; its warm_skin row used to be that design-only 10% stock.  The
    # preference names the material, so his owned neat grade takes it.
    from engine.research.formula_design import design_inventory_formula

    result = design_inventory_formula(
        idea=(
            "Create a six-material intimate human skin scent with soft warmth and "
            "close diffusion, not detergent, shampoo or loud clean musk."
        ),
        formula_name="Quiet Human Six",
        max_materials=6,
    )
    (row,) = [row for row in result["optimized_formula"]["rows"] if row["slot"] == "warm_skin"]
    assert row["stock_id"] == _NEAT_AMBRETTOLIDE, row
    assert _capabilities()[_NEAT_AMBRETTOLIDE].execution_ready


def _planner_candidate(name, label, *, owned, explicit=False):
    stock = SimpleNamespace(
        stock_id=label, name=label, identity_name=name, raw_name=label, physical_form="",
        fraction_basis="", carrier="", execution_ready=owned,
    )
    return SimpleNamespace(stock=stock, explicit=explicit)


def test_a_capsule_preference_for_an_unowned_grade_passes_to_the_owned_grade():
    from engine.research import composition_planner as cp

    role = SimpleNamespace(preferred_materials=("ambrettolide 10", "romandolide"))
    ten = _planner_candidate("Ambrettolide", "Ambrettolide 10%", owned=False)
    neat = _planner_candidate("Ambrettolide", "Ambrettolide (neat)", owned=True)
    other = _planner_candidate("Romandolide", "Romandolide", owned=True)
    ranks = cp._owned_grade_ranks([ten, neat, other], role)
    assert ranks == {"Ambrettolide 10%": 0, "Ambrettolide (neat)": 0, "Romandolide": 1}
    ranked = [(20.0, ten), (19.9, neat), (18.0, other)]
    assert [c.stock.stock_id for _s, c in cp._without_unowned_grades(ranked)] == [
        "Ambrettolide (neat)", "Romandolide",
    ]


_OWNED_VETIKON = "inventory:v5:135f51f25d430bfd4f99"
_VETIKON_CAS_TWIN = "inventory:text-design-only:b2adf14551e32246c0e3"  # "Vetikon (7403-42-1)"


def test_a_brief_naming_vetikon_gets_the_owned_vetikon_once():
    # The design-only "Vetikon (7403-42-1)" stock is the owned Vetikon with
    # its CAS number in the name; keyed on the raw name it was a second
    # material, the brief's anchor, beside the owned Vetikon.
    from engine.research.formula_design import design_inventory_formula

    result = design_inventory_formula(idea="a vetiver with vetikon", max_materials=8)
    rows = [
        row for row in result["optimized_formula"]["rows"]
        if "vetikon" in row["identity_name"].casefold()
    ]
    assert [row["stock_id"] for row in rows] == [_OWNED_VETIKON], rows
    assert _capabilities()[_OWNED_VETIKON].execution_ready
    assert not _capabilities()[_VETIKON_CAS_TWIN].execution_ready


def test_the_planner_reads_a_cas_numbered_grade_as_its_material():
    from engine.research import composition_planner as cp

    twin = _planner_candidate("Vetikon (7403-42-1)", "Vetikon (7403-42-1) (neat)", owned=False, explicit=True)
    owned = _planner_candidate("Vetikon", "Vetikon (neat)", owned=True, explicit=True)
    assert cp._grade_identity(twin) == cp._grade_identity(owned)
    ranked = [(20.0, twin), (19.0, owned)]
    assert [c.stock.stock_id for _s, c in cp._without_unowned_grades(ranked)] == ["Vetikon (neat)"]
    # Only a CAS number goes: an origin in parentheses still names another stock.
    haiti = _planner_candidate("Vetiver EO (Haiti)", "Vetiver EO (Haiti)", owned=True)
    plain = _planner_candidate("Vetiver EO", "Vetiver EO", owned=False)
    assert cp._grade_identity(haiti) != cp._grade_identity(plain)


def test_guard_a_grade_the_brief_names_is_kept_beside_an_owned_grade_it_does_not():
    from engine.research import composition_planner as cp

    role = SimpleNamespace(preferred_materials=("ambrettolide 10",))
    ten = _planner_candidate("Ambrettolide", "Ambrettolide 10%", owned=False, explicit=True)
    neat = _planner_candidate("Ambrettolide", "Ambrettolide (neat)", owned=True)
    assert cp._owned_grade_ranks([ten, neat], role)["Ambrettolide (neat)"] is None
    ranked = [(20.0, ten), (1.0, neat)]
    assert cp._without_unowned_grades(ranked) == ranked


def test_a_deep_white_musk_laundry_uses_the_owned_neat_ambrettolide():
    # The stock-alternative variant used to step to the unowned 10% stock.
    result = design_formula(idea="a white musk laundry", liquid_concentrate_ul_decimal="6000",
                            design_mode="DEEP_COMPOSE")
    rows = [
        row for formula in _formulas(result) for row in formula["rows"]
        if row["identity_name"] == "Ambrettolide"
    ]
    assert len(rows) >= 4
    assert {row["stock_id"] for row in rows} == {_NEAT_AMBRETTOLIDE}
