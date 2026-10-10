"""Milky, lactonic and clean briefs must reach owned lactones and macrocyclic musks.

Pins request-word routing into the candidate pool only: the top-ranked stocks for
the lead role of the facet. It makes no sensory, quality or liking claim.
"""

from __future__ import annotations

import pytest

from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
    capability_role_score,
)
from engine.formulation_intelligence.semantic_brief_adapter import compile_semantic_brief

_LACTONES = ("gamma decalactone", "gamma undecalactone", "delta decalactone", "gamma nonalactone")
_MACROCYCLIC_MUSKS = ("ambrettolide", "habanolide", "exaltolide", "zenolide", "romandolide", "ethylene brassylate")


@pytest.fixture(scope="module")
def index():
    return build_material_capability_index()


def _pool(index, request: str, facet_id: str, size: int = 8) -> list[str]:
    brief = compile_semantic_brief(
        formula_name="Untitled", request=request, interpretation={}, max_materials=18,
    )
    assert facet_id in brief.facets, brief.facets
    role = next(r for r in brief.roles if r.role_id == f"facet_{facet_id}")
    scored = []
    for cap in index.capabilities:
        if not cap.design_ready:
            continue
        score = capability_role_score(
            cap, query_terms=role.query_terms, character_weights=role.character_weights,
            note=role.note, function=role.function, exact_material=None,
        )
        if score is not None:
            scored.append((score, cap.identity_name.casefold()))
    return [name for _, name in sorted(scored, reverse=True)[:size]]


@pytest.mark.parametrize("request_text", ["a milky scent", "a lactonic scent"])
def test_milky_and_lactonic_reach_an_owned_lactone(index, request_text) -> None:
    pool = _pool(index, request_text, "lactonic_milk")
    assert any(lactone in name for name in pool for lactone in _LACTONES), pool


@pytest.mark.parametrize("request_text", ["a clean soft scent", "a skin musk", "a white musk"])
def test_clean_and_musk_words_reach_two_macrocyclic_musks(index, request_text) -> None:
    pool = _pool(index, request_text, "skin_musk")
    hits = {m for name in pool for m in _MACROCYCLIC_MUSKS if m in name}
    assert len(hits) >= 2, pool
