"""Spare volume a hard cap frees stays on the named notes, not on bridges."""

from functools import lru_cache

import pytest

from engine.formulation_intelligence import formula_solver
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)
from engine.formulation_intelligence.semantic_brief_adapter import (
    ACCORD_SUPPORT_PROVENANCE,
    ACCORD_SUPPORT_SEPARATOR,
    SemanticRole,
)
from engine.research.composition_planner import Choice, _design_cap_ul, _formula_rows, _hard_cap_ul
from engine.research.formula_design import design_inventory_formula

# Roles the composer adds on its own to link the requested notes.
_BRIDGE_SLOTS = {
    "opening_articulation",
    "heart_continuity",
    "top_to_heart_link",
    "heart_to_base_link",
    "diffusion_texture",
}


@lru_cache(maxsize=None)
def _formula(idea: str, formula_name: str | None) -> dict:
    return design_inventory_formula(idea=idea, formula_name=formula_name)["optimized_formula"]


def _liquid(rows: list[dict]) -> dict[str, int]:
    return {row["slot"]: int(row["amount_decimal"]) for row in rows if row["amount_unit"] == "uL"}


_SPRING_ROSE = ("A rose perfume for spring", "Spring Rose")
_COLOGNE = ("A fresh citrus cologne with a soft musky drydown", None)


def test_capped_rose_lead_hands_its_volume_to_its_own_accord() -> None:
    formula = _formula(*_SPRING_ROSE)
    amounts = _liquid(formula["rows"])
    total = int(formula["separate_totals"]["liquid_total_ul"])

    rose_accord = sum(
        amount
        for slot, amount in amounts.items()
        if slot == "facet_rose" or slot.startswith("facet_rose__accord_")
    )
    bridges = {slot: amount for slot, amount in amounts.items() if slot in _BRIDGE_SLOTS}
    assert bridges, "expected generic bridge rows in the spring rose formula"
    assert rose_accord > max(bridges.values())
    assert all(amount <= total * 0.12 for amount in bridges.values()), bridges


def test_cologne_bridge_never_carries_the_formula() -> None:
    formula = _formula(*_COLOGNE)
    amounts = _liquid(formula["rows"])
    total = int(formula["separate_totals"]["liquid_total_ul"])

    bridges = {slot: amount for slot, amount in amounts.items() if slot in _BRIDGE_SLOTS}
    assert bridges, "expected generic bridge rows in the cologne formula"
    assert all(amount <= total * 0.12 for amount in bridges.values()), bridges


@pytest.mark.parametrize("brief", [_SPRING_ROSE, _COLOGNE], ids=["spring_rose", "cologne"])
def test_liquid_total_is_conserved(brief: tuple[str, str | None]) -> None:
    formula = _formula(*brief)

    assert int(formula["separate_totals"]["liquid_total_ul"]) == 6000
    assert sum(_liquid(formula["rows"]).values()) == 6000


_EXACT_COUNT_ROSE = "A rose perfume for spring with exactly 8 materials"


def test_exact_count_keeps_the_planner_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    routed = design_inventory_formula(idea=_EXACT_COUNT_ROSE)["optimized_formula"]["rows"]
    monkeypatch.setattr(
        formula_solver,
        "_allocation_choices",
        lambda assignments, choices, *args, **kwargs: tuple(choices),
    )
    unrouted = design_inventory_formula(idea=_EXACT_COUNT_ROSE)["optimized_formula"]["rows"]

    assert len(routed) == 8
    assert _liquid(routed) == _liquid(unrouted)


# Synthetic allocations over real stocks.  Shares and raw-share ceilings set
# each row's design cap directly, so the arithmetic below is exact.
_L = 6000


@lru_cache(maxsize=None)
def _capabilities() -> tuple:
    return build_material_capability_index().capabilities


def _stock(identity: str, dilution: float):
    for capability in _capabilities():
        if (
            capability.identity_name == identity
            and float(capability.candidate.stock.dilution) == dilution
            and not capability.candidate.solid
        ):
            return capability
    raise AssertionError(f"no {identity} {dilution} stock in inventory")


def _row(
    role_id: str,
    capability,
    *,
    provenance: str,
    function: str = "character",
    share: float = .2,
    cap_ul: int | None = None,
) -> formula_solver.SolvedAssignment:
    role = SemanticRole(
        role_id=role_id,
        label=role_id,
        note="heart",
        function=function,
        query_terms=(),
        character_weights=(),
        share=share,
        max_raw_share=None if cap_ul is None else (cap_ul + .5) / _L,
        provenance=provenance,
    )
    return formula_solver.SolvedAssignment(role, capability, 0.0, ())


def _choices(assignments: list) -> tuple[Choice, ...]:
    return tuple(
        Choice(formula_solver._role_spec(row.role), row.capability.candidate, 0.0, ())
        for row in assignments
    )


def _allocate(assignments: list) -> dict[str, int]:
    routed = formula_solver._allocation_choices(assignments, _choices(assignments), _L, ())
    rows, totals, _holds = _formula_rows(routed, liquid_total_ul=_L, quantities=())
    assert int(totals["liquid_total_ul"]) == _L
    return {row["slot"]: int(row["amount_decimal"]) for row in rows}


def test_relaxed_bridge_cap_counts_a_smaller_fixed_bridge_cap_first() -> None:
    plain = _stock("Iso E Super", 1.0)
    assignments = [
        _row("facet_a", plain, provenance="PROMPT_DERIVED_FACET", cap_ul=2000),
        _row("facet_b", plain, provenance="PROMPT_DERIVED_FACET", cap_ul=2000),
        # A modifier bridge's own design cap (10% for a neat stock) sits below
        # the relaxed bridge cap, so it can only ever hold 600 uL.
        _row("bridge_modifier", plain, provenance="FUNCTIONAL_COVERAGE", function="modifier"),
        _row("bridge_structure", plain, provenance="FUNCTIONAL_COVERAGE", function="structure"),
    ]
    caps = [_design_cap_ul(choice, _L) for choice in _choices(assignments)]
    assert caps == [2000, 2000, 600, 2100]

    amounts = _allocate(assignments)

    assert amounts == {"facet_a": 2000, "facet_b": 2000, "bridge_modifier": 600, "bridge_structure": 1400}


def test_hard_capped_bridge_is_held_to_the_bridge_cap() -> None:
    plain = _stock("Iso E Super", 1.0)
    lemonile = _stock("Lemonile", .01)
    assert _hard_cap_ul(lemonile.candidate, _L) > _L * .12
    assignments = [
        _row("facet_a", plain, provenance="PROMPT_DERIVED_FACET", function="structure"),
        _row("facet_b", plain, provenance="PROMPT_DERIVED_FACET", function="structure"),
        _row("facet_c", plain, provenance="PROMPT_DERIVED_FACET", function="structure"),
        _row("bridge_lemonile", lemonile, provenance="FUNCTIONAL_COVERAGE", function="bridge", share=.4),
    ]

    amounts = _allocate(assignments)

    assert 0 < amounts["bridge_lemonile"] <= _L * .12, amounts


def test_spare_volume_never_pushes_a_support_past_its_ifra_limit() -> None:
    rose_oxide = _stock("Rose Oxide", .1)
    citronellal = _stock("Citronellal", 1.0)
    plain = _stock("Iso E Super", 1.0)
    assert formula_solver._ifra_entry(citronellal.identity_name)[0] == "restricted"
    assignments = [
        _row("facet_rose", rose_oxide, provenance="PROMPT_DERIVED_FACET", share=.3),
        _row(f"facet_rose{ACCORD_SUPPORT_SEPARATOR}citronellal", citronellal,
             provenance=ACCORD_SUPPORT_PROVENANCE, share=.1, cap_ul=60),
        _row(f"facet_rose{ACCORD_SUPPORT_SEPARATOR}plain", plain,
             provenance=ACCORD_SUPPORT_PROVENANCE, share=.1, cap_ul=480),
        _row("facet_wood", plain, provenance="PROMPT_DERIVED_FACET", function="structure", share=.5),
    ]
    choices = _choices(assignments)

    routed = formula_solver._allocation_choices(assignments, choices, _L, ())

    assert routed[0].role.share < choices[0].role.share
    assert routed[1] == choices[1]
    assert routed[2].role.share > choices[2].role.share
