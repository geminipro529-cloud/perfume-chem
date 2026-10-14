"""A note the brief calls "the star" keeps the largest row (Phase 1, A5).

"Pink pepper the star ... over smooth woods": once "woods" calls up the wood
note, its stocks took more volume than the pink pepper (Vetiver EO 748 uL
against Pink Pepper EO 666 uL), and in "pink pepper the star ... over dry
vetiver and cedar woods" Patchouli EO (804 uL) out-poured it. The star rule in
the planner keeps every other free row at or below the star's largest row.
These pin allocation order only; they make no sensory or quality claim.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.semantic_brief_adapter import (
    FacetDefinition,
    SemanticRole,
    _matched_facets,
    _star_role_ids,
)


def _role(
    role_id: str, *, exact: str | None = None, provenance: str = "PROMPT_DERIVED_FACET"
) -> SemanticRole:
    return SemanticRole(
        role_id=role_id,
        label=role_id,
        note="heart",
        function="character",
        query_terms=(),
        character_weights=(),
        share=0.1,
        exact_material=exact,
        provenance="EXPLICIT_REQUEST_MATERIAL" if exact else provenance,
    )


_SPICE = FacetDefinition("spice", ("pepper", "spice"), ("pepper",), "top", "character", (), 0.1)
_WOOD = FacetDefinition(
    "dry_wood", ("wood", "woods", "cedar"), ("wood",), "base", "structure", (), 0.15
)
_OUD = FacetDefinition("oud_agarwood", ("oud",), ("oud",), "base", "character", (), 0.065)
_ROSE = FacetDefinition("rose", ("rose",), ("rose",), "heart", "character", (), 0.1)


def test_the_note_named_before_the_star_marker_is_the_star() -> None:
    roles = (
        _role("explicit_anchor_1", exact="Pink Pepper EO"),
        _role("facet_dry_wood"),
        _role("facet_dry_wood__accord_1", provenance="ACCORD_SUPPORT"),
        _role("facet_spice"),
    )
    star = _star_role_ids(
        roles,
        "Pink pepper the star of a deep, dry, radiant masculine, over smooth woods.",
        (_WOOD, _SPICE),
    )
    assert set(star) == {"explicit_anchor_1", "facet_spice"}


def test_the_star_is_names_the_note_after_the_marker_with_its_accord() -> None:
    roles = (
        _role("facet_rose"),
        _role("facet_oud_agarwood"),
        _role("facet_oud_agarwood__accord_1", provenance="ACCORD_SUPPORT"),
    )
    star = _star_role_ids(roles, "Rose and oud for evening; the star is oud.", (_ROSE, _OUD))
    assert set(star) == {"facet_oud_agarwood", "facet_oud_agarwood__accord_1"}


def test_no_marker_or_no_note_beside_it_names_no_star() -> None:
    roles = (_role("facet_rose"), _role("facet_oud_agarwood"))
    assert _star_role_ids(roles, "Rose and oud for evening.", (_ROSE, _OUD)) == ()
    assert _star_role_ids(roles, "The star of the evening: rose and oud.", (_ROSE, _OUD)) == ()


def test_smooth_woods_calls_up_the_wood_note() -> None:
    facets = _matched_facets("pink pepper over smooth woods and Ambrocenide", (), {})
    assert "dry_wood" in {facet.facet_id for facet in facets}


def _active_by_material(result: dict) -> dict[str, Decimal]:
    rows = (result.get("optimized_formula") or {}).get("rows", [])
    return {
        str(row["identity_name"]): Decimal(str(row["amount_decimal"]))
        * Decimal(str(row.get("stock_fraction_decimal") or "1"))
        for row in rows
    }


@pytest.mark.parametrize(
    "idea",
    [
        "A pink pepper signature perfume for a man: pink pepper the star, still there at hour six, "
        "over dry vetiver and cedar woods. No vanilla, no sweetness; dry, radiant, masculine.",
        "Pink pepper the star of a deep, dry, radiant masculine: rich pink-pepper character built "
        "from materials related to pink pepper, hedonic, over smooth woods and Ambrocenide. No vanilla.",
    ],
)
def test_the_star_keeps_the_largest_row(idea: str) -> None:
    result = design_formula(
        idea=idea, formula_name="Baie Rose Homme", liquid_concentrate_ul_decimal="6000"
    )
    brief = result.get("semantic_brief") or {}
    active = _active_by_material(result)

    assert brief.get("star_role_ids"), brief.get("roles")
    assert "Pink Pepper EO" in active, sorted(active)
    star = active["Pink Pepper EO"]
    above = {name: amount for name, amount in active.items() if amount > star}
    assert not above, (star, above)


def test_a_brief_without_a_star_keeps_its_payload_unchanged() -> None:
    result = design_formula(
        idea="A dry cedar and vetiver woody scent for a man, no vanilla.",
        formula_name="Cedar Vetiver",
        liquid_concentrate_ul_decimal="6000",
    )
    assert "star_role_ids" not in (result.get("semantic_brief") or {})
