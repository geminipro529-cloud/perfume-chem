"""A brief that names a spice gets one spice that lasts.

The spice facet's own stock is a visible pepper (Pink Pepper EO 0.505 Pa,
Black Pepper EO 0.375 Pa) that is gone by the drydown.  The owner's pepper
formulas carry Safraleine 10% at 1.9-2.8% of raw; the composer now adds one
owned spice below the release gate's long-lasting vapour pressure.  These pin
role building and stock choice only; they make no sensory or quality claim.

The composer's new names are imported inside the tests, so the guard at the
end also runs on the code before this change.
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Any

from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.material_capability_index import (
    MaterialCapability,
    build_material_capability_index,
)
from engine.formulation_intelligence.semantic_brief_adapter import SemanticRole

# The idea text of the baie-rose-homme-r1 duel brief, copied as written.
_BAIE_ROSE_R1 = (
    "A pink pepper signature perfume for a man: pink pepper the star, still there at hour six, "
    "over dry vetiver and cedar woods. No vanilla, no sweetness; dry, radiant, masculine."
)


@lru_cache(maxsize=1)
def _capabilities() -> dict[str, MaterialCapability]:
    return {capability.stock_id: capability for capability in build_material_capability_index().capabilities}


def _stock(identity: str, dilution: float) -> MaterialCapability:
    return next(
        capability for capability in _capabilities().values()
        if capability.identity_name == identity and abs(capability.candidate.stock.dilution - dilution) < 1e-9
    )


def _rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return list((result.get("optimized_formula") or {}).get("rows", []))


def _lasting_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    from engine.formulation_intelligence.formula_solver import _is_lasting_spice

    return [row for row in _rows(result) if _is_lasting_spice(_capabilities()[row["stock_id"]])]


def _role_ids(result: dict[str, Any]) -> list[str]:
    return [role["role_id"] for role in (result.get("semantic_brief") or {}).get("roles", [])]


def _lasting_role() -> SemanticRole:
    from engine.formulation_intelligence.semantic_brief_adapter import LASTING_SPICE_PROVENANCE

    return SemanticRole(
        role_id="lasting_spice", label="Lasting spice", note="base", function="modifier",
        query_terms=("pink pepper", "spice", "spicy"), character_weights=(("spicy", 1.0), ("warmth", .35)),
        share=.025, required=False, max_raw_share=.03, provenance=LASTING_SPICE_PROVENANCE,
        descriptor_requirement="heart_spice",
    )


def _state(*assignments: tuple[SemanticRole, MaterialCapability], lasting_spice_brief: bool = False):
    from engine.formulation_intelligence.formula_solver import _BeamState, _chemical_identity

    return _BeamState(
        assignments=tuple((role, capability, 0.0) for role, capability in assignments),
        used_identities=frozenset(_chemical_identity(capability) for _role, capability in assignments),
        group_counts=(),
        objective=0.0,
        lasting_spice_brief=lasting_spice_brief,
    )


def test_the_pink_pepper_brief_gets_one_lasting_spice_beside_its_pepper() -> None:
    result = design_formula(
        idea=_BAIE_ROSE_R1, formula_name="Baie Rose Homme R1", liquid_concentrate_ul_decimal="5160",
    )
    lasting = _lasting_rows(result)
    assert len(lasting) == 1, [(row["slot"], row["identity_name"]) for row in lasting]
    row = lasting[0]
    assert row["slot"] == "lasting_spice", row
    assert _capabilities()[row["stock_id"]].execution_ready, row
    assert Decimal(str(row["stock_fraction_decimal"])) == Decimal("0.1"), row
    share = Decimal(str(row["amount_decimal"])) / Decimal(5160)
    assert Decimal("0.015") <= share <= Decimal("0.03"), share
    spice = next(row for row in _rows(result) if row["slot"] == "facet_spice")
    assert "pepper" in spice["identity_name"].casefold(), spice


def test_a_second_lasting_spice_is_refused_beside_the_first() -> None:
    from engine.formulation_intelligence.formula_solver import _block_reason

    coverage = SemanticRole(
        role_id="heart_continuity", label="Heart continuity", note="heart", function="bridge",
        query_terms=("spice",), character_weights=(("spicy", .5),), share=.12,
        provenance="FUNCTIONAL_COVERAGE",
    )
    safraleine, safranate = _stock("Safraleine", .1), _stock("Ethyl Safranate", .1)
    held = _state((_lasting_role(), safraleine))
    assert _block_reason(
        safranate, coverage, held, avoid=(), allow_multiple_musks=False,
    ) == "one lasting spice already"
    # A brief with no lasting spice role keeps its old choices.
    facet = SemanticRole(
        role_id="facet_leather_suede", label="Leather", note="base", function="character",
        query_terms=("saffron",), character_weights=(), share=.065,
    )
    assert _block_reason(
        safranate, coverage, _state((facet, safraleine)), avoid=(), allow_multiple_musks=False,
    ) is None


def test_a_lasting_spice_the_brief_names_is_its_one_lasting_spice() -> None:
    result = design_formula(
        idea="A spicy woody scent built on Ethyl Safranate and cedar.",
        formula_name="Safranate Cedar",
        liquid_concentrate_ul_decimal="6000",
    )
    assert "lasting_spice" in _role_ids(result), _role_ids(result)
    lasting = _lasting_rows(result)
    assert [row["identity_name"] for row in lasting] == ["Ethyl Safranate"], lasting
    assert lasting[0]["slot"] != "lasting_spice", lasting


def test_the_lasting_role_takes_only_an_owned_lasting_spice() -> None:
    from engine.formulation_intelligence.formula_solver import _block_reason, _is_lasting_spice

    role, empty = _lasting_role(), _state(lasting_spice_brief=True)
    allowed = [
        capability for capability in _capabilities().values()
        if _block_reason(capability, role, empty, avoid=(), allow_multiple_musks=False) is None
    ]
    assert allowed
    assert all(capability.execution_ready and _is_lasting_spice(capability) for capability in allowed), [
        (capability.identity_name, capability.stock_label) for capability in allowed
    ]
    neat = _stock("Safraleine", 1.0)
    assert not neat.execution_ready
    assert _block_reason(neat, role, empty, avoid=(), allow_multiple_musks=False) is not None


def test_a_brief_that_avoids_leather_gets_no_safraleine() -> None:
    result = design_formula(
        idea="A ginger and vetiver scent, no leather", liquid_concentrate_ul_decimal="6000",
    )
    lasting = _lasting_rows(result)
    assert [row["slot"] for row in lasting] == ["lasting_spice"], lasting
    assert lasting[0]["identity_name"] != "Safraleine", lasting


def test_owned_lasting_spices_the_avoid_list_refuses_leave_the_role_empty_and_say_why() -> None:
    # Both owned lasting spices exist and the avoid list turns each down by
    # its own descriptor.  The receipt used to say none was owned.
    result = design_formula(
        idea="A pink pepper perfume",
        liquid_concentrate_ul_decimal="6000",
        must_avoid=("leather", "sweetness"),
    )
    assert "lasting_spice" in _role_ids(result), _role_ids(result)
    assert not _lasting_rows(result)
    attempt = result["architecture_attempts"][0]
    assert attempt["state"] == "SOLVED", attempt["state"]
    assert "Lasting spice" not in attempt["missing_roles"]
    assert _rows(result)
    expected = [
        "LASTING_SPICE_REFUSED:Ethyl Safranate at 0.1: the brief's avoid list (its own descriptor)",
        "LASTING_SPICE_REFUSED:Safraleine at 0.1: the brief's avoid list (its own descriptor)",
    ]
    assert attempt["solver"].get("limitations") == expected, attempt["solver"].get("limitations")
    # The owner-facing critic carries the solver's limitations too.
    assert set(expected) <= set(result["critic"]["limitations"]), result["critic"]["limitations"]


def test_an_index_without_an_owned_lasting_spice_says_none_is_owned() -> None:
    from dataclasses import replace

    from engine.formulation_intelligence.formula_solver import _is_lasting_spice, solve_formula
    from engine.formulation_intelligence.semantic_brief_adapter import compile_semantic_brief

    index = build_material_capability_index()
    owned = {
        capability.stock_id for capability in index.capabilities
        if capability.execution_ready and _is_lasting_spice(capability)
    }
    assert owned
    without = replace(index, capabilities=tuple(
        capability for capability in index.capabilities if capability.stock_id not in owned
    ))
    brief = compile_semantic_brief(
        formula_name="Pink Pepper", request="A pink pepper perfume", interpretation={}, max_materials=60,
    )
    assert "lasting_spice" in [role.role_id for role in brief.roles]
    solve = solve_formula(brief=brief, index=without, liquid_total_ul=6000, explicit_quantities=(), avoid=())
    assert solve.status == "SOLVED", solve.status
    assert solve.solver_receipt.get("limitations") == [
        "LASTING_SPICE_NOT_OWNED: no owned spice stock below 0.1 Pa (pink pepper)"
    ], solve.solver_receipt.get("limitations")


def test_a_spiced_or_peppered_brief_gets_a_lasting_spice() -> None:
    # "spiced" and "peppered" name a spice; the role used to take only a
    # plural or adjective ending.
    for idea in ("A spiced amber with vetiver", "A peppered vetiver"):
        result = design_formula(idea=idea, liquid_concentrate_ul_decimal="6000")
        assert "lasting_spice" in _role_ids(result), (idea, _role_ids(result))
        lasting = _lasting_rows(result)
        limitations = result["architecture_attempts"][0]["solver"].get("limitations", [])
        assert [row["slot"] for row in lasting] == ["lasting_spice"] or any(
            line.startswith("LASTING_SPICE_") for line in limitations
        ), (idea, lasting, limitations)


def test_a_spice_the_brief_turns_down_names_no_lasting_spice() -> None:
    # "spiced" names a spice; "not spiced" turns it down, as "not citrusy"
    # turns down a citrus.  It used to get a lasting Safraleine row.
    from engine.formulation_intelligence.semantic_brief_adapter import _lasting_spice_role

    turned_down = ("a warm amber, not spiced", "a warm amber, never spiced", "a warm amber, not spicy")
    for idea in turned_down:
        assert _lasting_spice_role(idea, ()) is None, idea
        result = design_formula(idea=idea, liquid_concentrate_ul_decimal="6000")
        assert "lasting_spice" not in _role_ids(result), (idea, _role_ids(result))
        assert not _lasting_rows(result), (idea, _lasting_rows(result))
    result = design_formula(idea="a spiced amber", liquid_concentrate_ul_decimal="6000")
    assert "lasting_spice" in _role_ids(result), _role_ids(result)
    assert [row["slot"] for row in _lasting_rows(result)] == ["lasting_spice"]


def _owned_lasting_spice_lines(reason: str) -> list[str]:
    from engine.formulation_intelligence.formula_solver import _is_lasting_spice

    owned = [
        capability for capability in build_material_capability_index().capabilities
        if capability.execution_ready and _is_lasting_spice(capability)
    ]
    assert owned
    return [
        f"LASTING_SPICE_REFUSED:{capability.identity_name} at "
        f"{float(capability.candidate.stock.dilution):g}: {reason}"
        for capability in owned
    ]


def test_a_material_limit_without_room_for_the_lasting_spice_says_so() -> None:
    # Four materials leave no room for the role; the brief used to end with
    # no lasting spice and no word of why.
    result = design_formula(
        idea="A pink pepper perfume using at most 4 materials", liquid_concentrate_ul_decimal="6000",
    )
    assert "lasting_spice" not in _role_ids(result), _role_ids(result)
    assert not _lasting_rows(result)
    expected = _owned_lasting_spice_lines("the material limit")
    attempt = result["architecture_attempts"][0]
    assert attempt["solver"].get("limitations") == expected, attempt["solver"].get("limitations")
    assert set(expected) <= set(result["critic"]["limitations"]), result["critic"]["limitations"]
    # The brief carries the left-out role to the solver, not into its payload.
    assert "lasting_spice_over_limit" not in result["semantic_brief"]


def test_a_curated_capsule_without_a_spice_role_says_so() -> None:
    # The intimate-skin capsule fills its own roles, none of them a lasting
    # spice; the brief's cardamom used to end with no lasting spice and no
    # word of why.
    result = design_formula(
        idea="a quiet skin scent with cardamom", liquid_concentrate_ul_decimal="6000",
    )
    assert result["concept_family"] == "intimate_skin", result["concept_family"]
    assert "architecture_attempts" not in result
    assert not _lasting_rows(result)
    expected = _owned_lasting_spice_lines("the curated capsule has no spice role")
    lines = [line for line in result["critic"]["limitations"] if line.startswith("LASTING_SPICE_")]
    assert lines == expected, result["critic"]["limitations"]


def test_guard_a_curated_capsule_brief_without_a_spice_gets_no_spice_line() -> None:
    result = design_formula(idea="a quiet skin scent", liquid_concentrate_ul_decimal="6000")
    assert result["concept_family"] == "intimate_skin", result["concept_family"]
    assert not [line for line in result["critic"]["limitations"] if "LASTING_SPICE" in line]


def test_guard_an_avoided_spiced_phrase_names_no_lasting_spice() -> None:
    from engine.formulation_intelligence.semantic_brief_adapter import _lasting_spice_role

    assert _lasting_spice_role("A warm amber with vetiver, no spiced notes", ("no spiced notes",)) is None
    assert _lasting_spice_role("A vetiver, no spiced rum", ("spiced rum",)) is None
    assert _lasting_spice_role("A peppered vetiver", ("spiced notes",)) is None
    result = design_formula(
        idea="A warm amber with vetiver, no spiced notes", liquid_concentrate_ul_decimal="6000",
    )
    assert "lasting_spice" not in _role_ids(result), _role_ids(result)


def test_the_lasting_vapour_pressure_is_the_release_gates() -> None:
    from engine.formulation_intelligence import formula_solver
    from engine.pipeline import gates

    assert formula_solver._LASTING_VP_PA == gates.TENACITY_LONG_LASTING_VP_25C_PA


def test_an_exact_material_count_keeps_the_lasting_spice_only_where_it_fits() -> None:
    from engine.formulation_intelligence.semantic_brief_adapter import compile_semantic_brief

    def roles(count: int) -> list[str]:
        brief = compile_semantic_brief(
            formula_name="Pepper Cedar", request="A pink pepper and cedar perfume.",
            interpretation={}, max_materials=60, target_material_count=count,
        )
        return [role.role_id for role in brief.roles]

    # The brief's two notes and the three coverage roles take five places.
    tight = roles(5)
    assert "lasting_spice" not in tight and len(tight) == 5, tight
    for count in (6, 10):
        roomy = roles(count)
        assert "lasting_spice" in roomy and len(roomy) == count, roomy


def test_guard_a_brief_without_a_spice_it_wants_gets_no_lasting_spice() -> None:
    for idea in ("a warm woody amber", "A warm woody amber for evening, no spice"):
        result = design_formula(idea=idea, liquid_concentrate_ul_decimal="6000")
        assert "lasting_spice" not in _role_ids(result), (idea, _role_ids(result))
