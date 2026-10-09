"""Requested notes must reach the composed formula (audit findings COMP-01, COMP-05).

COMP-01: "rose and oud" silently dropped the oud.  COMP-05: an iris brief led
with Carrot Seed EO although irone and orris stocks are owned.  These pin the
request-to-stock routing only; they make no sensory or quality claim.
"""

from __future__ import annotations

import pytest

import engine.inventory_parser as inventory_parser
import engine.research.composition_planner as composition_planner
from engine.formulation_intelligence.architecture_bridge import role_plan_signature
from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.semantic_brief_adapter import SemanticRole

_IRIS_NAME_WORDS = ("irone", "orris")
# role_plan_signature of the "violet leaf" brief on origin/master 6f9b1a3a.
_VIOLET_LEAF_SIGNATURE_ON_MASTER = "5c157beaecdfffb1a6b964e233f5d985336ed8af31666eec9b38eb6e85b8bb53"


def _clear_inventory_caches() -> None:
    inventory_parser._cached_current_inventory_materialization.cache_clear()
    composition_planner._cached_legacy_inventory.cache_clear()


def _rows_for_role(result: dict, role_id: str) -> list[dict]:
    return [row for row in result["initial_formula"]["rows"] if row["slot"] == role_id]


def test_rose_and_oud_keeps_the_oud_as_an_agarwood_row() -> None:
    result = design_formula(idea="rose and oud")

    assert "oud_agarwood" in result["semantic_brief"]["facets"]
    identities = [row["identity_name"].casefold() for row in result["initial_formula"]["rows"]]
    assert any("agarwood" in name for name in identities), identities


def test_iris_brief_leads_with_an_owned_irone_or_orris_stock() -> None:
    result = design_formula(idea="iris")

    lead = _rows_for_role(result, "facet_iris_violet")
    assert lead, result["initial_formula"]["rows"]
    name = lead[0]["identity_name"].casefold()
    assert any(word in name for word in _IRIS_NAME_WORDS), name


def test_iris_brief_falls_back_when_irone_and_orris_are_held(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    labels, digest = inventory_parser.load_user_compounding_holds()
    held = frozenset({*labels, "alpha irone", "orris liquid"})
    monkeypatch.setattr(inventory_parser, "load_user_compounding_holds", lambda: (held, digest))
    monkeypatch.setattr(composition_planner, "_CANDIDATE_BASE_CACHE", {})
    # Inventories with holds applied are memoized by file fingerprint/hash.
    _clear_inventory_caches()
    try:
        result = design_formula(idea="iris")
    finally:
        monkeypatch.undo()
        _clear_inventory_caches()

    lead = _rows_for_role(result, "facet_iris_violet")
    assert lead, result["initial_formula"]["rows"]
    selected = {row["identity_name"].casefold() for row in result["initial_formula"]["rows"]}
    assert not selected & {"alpha irone", "orris liquid"}, selected
    assert lead[0]["design_ready"] is True


def test_violet_leaf_brief_role_plan_is_unchanged() -> None:
    result = design_formula(idea="violet leaf")

    roles = [SemanticRole(**role) for role in result["semantic_brief"]["roles"]]
    assert role_plan_signature(roles) == _VIOLET_LEAF_SIGNATURE_ON_MASTER
