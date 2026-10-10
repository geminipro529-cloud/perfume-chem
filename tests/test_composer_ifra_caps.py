"""The composer keeps every dose inside IFRA Category 4, naturals' constituents included.

The limits come from the gate's own evaluation (engine/ifra_standards.py), so a
natural with no IFRA entry of its own is held by its Annex I constituents: rose
oil by its methyl eugenol.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from engine.ifra_standards import single_material_limit_pct

ROSE_EO = "Rose Essential Oil (Rosa Damascena, India)"


def _candidate(name: str, dilution: float = 1.0) -> SimpleNamespace:
    stock = SimpleNamespace(stock_id=name, identity_name=name, name=name, dilution=dilution)
    return SimpleNamespace(stock=stock)


def test_a_natural_without_its_own_entry_is_limited_by_its_constituents() -> None:
    status, limit = single_material_limit_pct(ROSE_EO)

    assert status == "restricted"
    assert limit == pytest.approx(0.55, abs=0.01)


def test_single_material_limits_follow_the_gate() -> None:
    assert single_material_limit_pct("Oakmoss Absolute") == ("restricted", pytest.approx(0.1))
    assert single_material_limit_pct("Lyral") == ("prohibited", 0.0)
    assert single_material_limit_pct("Hedione")[1] is None


def test_the_ifra_cap_is_the_volume_that_keeps_the_stock_inside_its_limit() -> None:
    from engine.research.composition_planner import _ifra_cap_ul

    # 0.1% finished at a 30% concentrate is 0.333% of the concentrate: 20 uL of
    # active in 6,000 uL, so 200 uL of a 10% stock.
    assert _ifra_cap_ul(_candidate("Oakmoss Absolute", 0.1), 6000) == 200
    assert _ifra_cap_ul(_candidate(ROSE_EO), 6000) == 109
    assert _ifra_cap_ul(_candidate("Hedione"), 6000) is None
    # A prohibited stock is the composer screen's and the gate's to refuse.
    assert _ifra_cap_ul(_candidate("Lyral"), 6000) is None


def test_no_design_firm_or_released_cap_passes_the_ifra_cap(monkeypatch) -> None:
    import engine.research.composition_planner as planner

    for name in ("_hard_cap_ul", "_normal_use_ceiling_cap_ul", "_screening_default_cap_ul"):
        monkeypatch.setattr(planner, name, lambda *_args, **_kwargs: None)
    monkeypatch.setattr(planner, "_role_cap_ul", lambda _choice, total: total)
    oakmoss = SimpleNamespace(candidate=_candidate("Oakmoss Absolute", 0.1))

    assert planner._design_cap_ul(oakmoss, 6000) == 200
    assert planner._firm_cap_ul(oakmoss, 6000) == 200


def test_the_bulk_fallback_never_releases_a_row_past_its_ifra_cap(monkeypatch) -> None:
    import engine.research.composition_planner as planner

    monkeypatch.setattr(planner, "_allocation_weight", lambda _choice: 1.0)
    for name in ("_hard_cap_ul", "_normal_use_ceiling_cap_ul", "_screening_default_cap_ul"):
        monkeypatch.setattr(planner, name, lambda *_args, **_kwargs: None)
    role = SimpleNamespace(serves_requested_facet=True, explicit_restraint=False, function="character")
    choices = [
        SimpleNamespace(role=role, candidate=_candidate("Oakmoss Absolute", 0.1)),
        SimpleNamespace(role=role, candidate=_candidate("Hedione")),
    ]
    # Both role caps are too small to fill the total, so the fallback releases them.
    holds: list[str] = []
    allocated = planner._allocate_with_bulk_fallback(
        6000, [(0, 1.0, 100), (1, 1.0, 100)], choices, 6000, holds
    )

    assert allocated[0] <= 200
    assert sum(allocated.values()) == 6000


def test_the_solver_screen_counts_a_naturals_constituents() -> None:
    from engine.formulation_intelligence.formula_solver import _ifra_admits_raw_share

    rose = SimpleNamespace(identity_name=ROSE_EO, candidate=_candidate(ROSE_EO))

    # 2% of a concentrate that is up to 30% of the perfume: 0.6% > 0.55%.
    assert not _ifra_admits_raw_share(rose, 0.02)
    assert _ifra_admits_raw_share(rose, 0.015)


@pytest.mark.parametrize("idea", ["a soft woody amber", "a fresh lavender cologne"])
def test_briefs_that_failed_ifra_on_master_now_compose_inside_it(idea: str) -> None:
    # Both failed IFRA Cat 4 in the #78 benchmark baseline (master 8e9cedd).
    from engine.formulation_intelligence.formula_design_runtime import design_formula

    checks = (design_formula(idea=idea).get("composition_checks") or {}).get("checks") or []
    ifra = [check for check in checks if check.get("check") == "ifra"]

    assert ifra
    assert not [check for check in ifra if check.get("status") == "FAIL"]


def test_the_layer_screen_counts_a_naturals_constituents() -> None:
    from engine.formulation_intelligence.formula_solver import _ifra_binds_layer

    rose = SimpleNamespace(identity_name=ROSE_EO, candidate=_candidate(ROSE_EO))
    layer = SimpleNamespace(provenance="LAYERED_HEART_ARCHITECTURE", max_raw_share=None)

    assert _ifra_binds_layer(rose, layer)
    hedione = SimpleNamespace(identity_name="Hedione", candidate=_candidate("Hedione"))
    assert not _ifra_binds_layer(hedione, layer)
