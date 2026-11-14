"""The same backbone no longer wins every brief (engine fault hunt, 6 Nov 2026, fix 3).

Ambrox Super was in 19 of 34 test formulas, Bergamot 18, Cedarwood Virginia
16 (any cedarwood oil pays), Cedroxyde 13, and Safraleine in every Baie Rose card.  Unless a brief
names one, it gives up some fit so a stock that fits nearly as well wins.
"""

from __future__ import annotations

from functools import lru_cache
from types import SimpleNamespace

import pytest

from engine.formulation_intelligence import formula_solver as solver
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)
from engine.formulation_intelligence.semantic_brief_adapter import SemanticRole


@lru_cache(maxsize=1)
def _index():
    return build_material_capability_index()


@pytest.mark.parametrize(
    ("identity", "brief", "unasked"),
    [
        ("Bergamot FCF Oil Sicilian", "a dark rose with oud", True),
        ("Bergamot FCF Oil Sicilian", "a fresh citrus cologne", False),
        ("Cedarwood Virginia", "soft woody amber", True),
        ("Cedarwood Virginia", "pencil shavings and cedar", False),
        ("Cedarwood Himalayan EO", "soft woody amber", True),
        ("Cedarwood Himalayan EO", "a cedarwood and incense", False),
        ("Ambrox Super", "a rose amber", False),
        ("Safraleine", "Baie Rose: pink pepper and leather", True),
        ("Safraleine", "saffron leather", False),
        ("Hedione", "a dark rose with oud", False),
    ],
)
def test_backbone_stocks_pay_unless_the_brief_names_them(identity: str, brief: str, unasked: bool) -> None:
    assert solver._unasked_backbone(SimpleNamespace(identity_name=identity), brief) is unasked


def test_the_penalty_is_applied_in_the_ranking() -> None:
    role = SemanticRole(
        role_id="opening_articulation", label="test", note="top", function="bridge",
        query_terms=("citrus", "fresh"), character_weights=(("citrus", 1.0),), share=0.1,
        provenance="FUNCTIONAL_COVERAGE",
    )

    def scores(text: str | None) -> dict[str, float]:
        ranked = solver._unary_rank_for_role(
            _index(), role, avoid=(), previous_stock_ids=frozenset(),
            prior_variant_stock_ids=frozenset(), variant_index=0, frontier=None, brief_text=text,
        )
        return {c.stock_id: score for score, c in ranked if c.identity_name == "Bergamot FCF Oil Sicilian"}

    plain, rose, cologne = scores(None), scores("a dark rose with oud"), scores("a citrus cologne")
    assert plain
    for stock_id, score in plain.items():
        assert rose[stock_id] == pytest.approx(score - solver._BACKBONE_PENALTY)
        assert cologne[stock_id] == pytest.approx(score)
