"""Performance as a composer goal (engine fault hunt, 6 Nov 2026, fix 2).

25 of 34 test formulas ended under 60 uL of long-lasting material per mL
(Violette 20 against Kenny's 58): the planner's floor only moves volume
between rows.  A formula short of it is solved once more with its functional
heart and base roles preferring long-lasting stocks, and long-lasting rows
pour their strongest owned liquid grade.
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
from engine.formulation_intelligence.semantic_brief_adapter import SemanticRole
from engine.research.composition_planner import Choice


@lru_cache(maxsize=1)
def _index():
    return build_material_capability_index()


def _capability(identity: str, dilution: float):
    return next(
        c for c in _index().capabilities
        if c.identity_name == identity and float(c.candidate.stock.dilution) == dilution
    )


def _role(provenance: str = "FUNCTIONAL_COVERAGE", note: str = "base") -> SemanticRole:
    return SemanticRole(
        role_id="persistent_identity", label="test", note=note, function="fixative",
        query_terms=("musk",), character_weights=(("musk", 1.0),), share=0.1,
        provenance=provenance,
    )


def test_the_floor_hold_reports_how_far_the_formula_reached() -> None:
    assert solver._long_lasting_reached(("X", "LONG_LASTING_FLOOR_SHORT:45.4")) == Decimal("45.4")
    assert solver._long_lasting_reached(("ACTIVE_SHARE_FLOOR_SHORT:40.0",)) is None


def test_only_functional_heart_and_base_roles_are_steered() -> None:
    assert solver._performance_role(_role())
    assert solver._performance_role(_role("LAYERED_BASE_ARCHITECTURE"))
    # The brief's own facets keep their stocks, and top roles stay light.
    assert not solver._performance_role(_role("PROMPT_DERIVED_FACET"))
    assert not solver._performance_role(_role(note="top"))


def _scores(role: SemanticRole) -> dict[tuple[str, float], float]:
    ranked = solver._unary_rank_for_role(
        _index(), role, avoid=(), previous_stock_ids=frozenset(),
        prior_variant_stock_ids=frozenset(), variant_index=0, frontier=None,
    )
    return {(c.identity_name, float(c.candidate.stock.dilution)): score for score, c in ranked}


def test_the_performance_pass_lifts_long_lasting_stocks_by_the_bonus() -> None:
    role = _role()
    plain = _scores(role)
    token = solver._PERFORMANCE_PASS.set(True)
    try:
        steered = _scores(role)
    finally:
        solver._PERFORMANCE_PASS.reset(token)
    # Habanolide is long-lasting (the gate's VP under 0.1 Pa); Linalool is not.
    habanolide = ("Habanolide", 1.0)
    assert steered[habanolide] - plain[habanolide] == pytest.approx(solver._PERFORMANCE_BONUS)
    linalool = next((key for key in plain if key[0] == "Linalool"), None)
    if linalool is not None and linalool in steered:
        assert steered[linalool] == plain[linalool]


def test_a_long_lasting_row_pours_its_strongest_owned_grade() -> None:
    weak = _capability("Exaltolide", 0.1)
    role = SimpleNamespace(role_id="facet_skin_musk", exact_material=None)
    assignment = solver.SolvedAssignment(role=role, capability=weak, score=1.0, alternatives=())
    choice = Choice(role=role, candidate=weak.candidate, score=1.0, alternatives=())
    moved = solver._strengthen_long_lasting_rows((assignment,), (choice,), _index(), ())
    assert moved is not None
    assert float(moved[1][0].candidate.stock.dilution) == 1.0
    assert moved[0][0].capability.candidate is moved[1][0].candidate


def test_a_requested_dose_keeps_its_grade() -> None:
    weak = _capability("Exaltolide", 0.1)
    role = SimpleNamespace(role_id="facet_skin_musk", exact_material=None)
    assignment = solver.SolvedAssignment(role=role, capability=weak, score=1.0, alternatives=())
    choice = Choice(role=role, candidate=weak.candidate, score=1.0, alternatives=())
    asked = ({"scope": "MATERIAL_DOSE", "material": "Exaltolide 10% in DPG", "amount_decimal": "300", "unit": "uL"},)
    assert solver._strengthen_long_lasting_rows((assignment,), (choice,), _index(), asked) is None
