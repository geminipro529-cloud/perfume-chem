"""The composer checks its own formula against its brief (Phase 3, step 5).

A note's lead should be that note: when a lead misses the specific note the brief names
and an owned, design-ready stock is named for it, the composer solves again with that role
asking for such a stock and keeps whichever candidate the check scores higher. The check
reads only the compiled brief and the stocks' own names and descriptors (no OAV or liking,
AGENTS.md Rule 1). These pin the mechanism; they make no sensory or quality claim.
"""

from __future__ import annotations

from types import SimpleNamespace

from engine.formulation_intelligence.brief_self_check import (
    best_of_solves,
    carries,
    check_solve,
    repair_targets,
)
from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.formula_solver import FormulaSolveResult, SolvedAssignment
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)
from engine.formulation_intelligence.semantic_brief_adapter import SemanticRole


def _facets(result: dict) -> dict[str, str]:
    return {
        row["slot"]: row["identity_name"]
        for row in result["optimized_formula"]["rows"]
        if row["slot"].startswith("facet_")
    }


def _self_check(result: dict) -> dict:
    return result["composition_plan"]["brief_self_check"]


def test_a_pepper_brief_leads_its_spice_with_a_pepper() -> None:
    result = design_formula(idea="A dry pepper and vetiver perfume for a man")

    assert "pepper" in _facets(result)["facet_spice"].casefold()
    check = _self_check(result)
    assert check["picked"] == "repair:facet_spice"
    assert check["candidates"][0]["label"] == "primary"
    assert check["candidates"][0]["score"] < check["check"]["score"]


def test_a_vanilla_balsam_lead_is_the_vanilla_molecule() -> None:
    result = design_formula(idea="a gourmand vanilla")

    assert _facets(result)["facet_vanilla_balsam"] == "Vanillin"
    # Since Siam Benzoin moved to the JECFA resin means (2026-10-25 naturals batch),
    # the first solve already leads with Vanillin and the check keeps it; the pepper
    # brief above still pins the repair path.
    assert _self_check(result)["picked"] == "primary"


def test_a_brief_whose_leads_carry_their_notes_keeps_its_first_solve() -> None:
    result = design_formula(idea="A rose and amber perfume")

    check = _self_check(result)
    assert check["picked"] == "primary"
    assert [c["label"] for c in check["candidates"]] == ["primary"]
    attempt = result["architecture_attempts"][0]["solver"]
    assert "identity_requirements" not in attempt


def test_an_uncovered_note_names_the_owned_stocks_waiting_for_details() -> None:
    # Lavandin: only the owned Lavandin Absolute carries it, and it waits for details.
    # (Frangipani was the example until Benzyl Salicylate's reviewed description named it;
    # Opoponax until Kenny let the composer design with Opoponax Resinoid, 14 Oct 2026.)
    result = design_formula(idea="Lavandin on skin with a soft vanilla trail")

    check = _self_check(result)
    assert "lavandin" in check["check"]["uncovered_words"]
    index = build_material_capability_index()
    held = sorted({
        c.identity_name for c in index.capabilities
        if not c.design_ready and "lavandin" in c.identity_vocabulary
    })
    assert held
    assert check["held_carriers"].get("lavandin", []) == held[:3]


def test_carries_reads_the_stock_name_before_its_descriptors() -> None:
    cedar = SimpleNamespace(identity_vocabulary=frozenset({"cedarwood", "virginia"}),
                            descriptor_vocabulary=frozenset({"woody", "dry"}))
    vanillin = SimpleNamespace(identity_vocabulary=frozenset({"vanillin"}),
                               descriptor_vocabulary=frozenset({"sweet", "vanilla"}))
    cardamom = SimpleNamespace(identity_vocabulary=frozenset({"cardamom"}),
                               descriptor_vocabulary=frozenset({"spicy", "pepper"}))

    assert carries(cedar, "cedar") == "identity"
    assert carries(vanillin, "vanilla") == "identity"
    assert carries(cardamom, "pepper") == "descriptor"
    assert carries(cardamom, "vanilla") is None
    assert carries(cedar, "pink pepper") is None


def _spice_case() -> tuple[SimpleNamespace, SemanticRole, dict, list]:
    index = build_material_capability_index()
    by_name = {c.identity_name: c for c in index.capabilities if c.design_ready}
    role = SemanticRole(
        role_id="facet_spice", label="Spice expression", note="heart", function="accord",
        query_terms=("pepper", "cardamom", "nutmeg"), character_weights=(("spicy", 1.0),),
        share=.1,
    )
    brief = SimpleNamespace(normalized_request="a pepper accord", roles=(role,),
                            requested_fruits=(), unmapped_requested_notes=())
    return brief, role, by_name, index


def _solved(role: SemanticRole, capability, status: str = "SOLVED") -> FormulaSolveResult:
    return FormulaSolveResult(
        status=status, variant_id="semantic-variant-1-test",
        assignments=(SolvedAssignment(role, capability, 1.0, ()),), missing_roles=(),
        rows=(), separate_totals={}, holds=(), solver_receipt={},
    )


def test_a_lead_missing_its_note_is_a_repair_target_when_a_named_stock_is_free() -> None:
    brief, role, by_name, index = _spice_case()
    primary = _solved(role, by_name["Cardamom EO"])

    check = check_solve(brief, primary)
    assert [d.role_id for d in check.lead_defects] == ["facet_spice"]
    assert repair_targets(brief, primary, check, index, avoid=()) == {"facet_spice": ("pepper",)}
    # Avoiding pepper leaves no stock the role could ask for.
    assert repair_targets(brief, primary, check, index, avoid=("pepper",)) == {}


def test_a_withheld_repair_is_never_picked() -> None:
    brief, role, by_name, index = _spice_case()
    primary = _solved(role, by_name["Cardamom EO"])
    withheld = _solved(role, by_name["Black Pepper EO"], status="WITHHELD_CONCEPT_COVERAGE_INCOMPLETE")

    chosen = best_of_solves(brief=brief, index=index, avoid=(),
                            solve=lambda words: primary if words is None else withheld)

    assert chosen.assignments == primary.assignments
    receipt = chosen.solver_receipt["self_check"]
    assert receipt["picked"] == "primary"
    assert receipt["repairs_withheld"] == ["repair:facet_spice"]


def test_the_higher_scoring_candidate_wins_and_a_tie_keeps_the_first_solve() -> None:
    brief, role, by_name, index = _spice_case()
    primary = _solved(role, by_name["Cardamom EO"])
    repaired = _solved(role, by_name["Black Pepper EO"])

    assert best_of_solves(
        brief=brief, index=index, avoid=(),
        solve=lambda words: primary if words is None else repaired,
    ).solver_receipt["self_check"]["picked"] == "repair:facet_spice"
    # The same formula again scores the same, and the first solve wins the tie.
    tie = best_of_solves(brief=brief, index=index, avoid=(), solve=lambda words: primary)
    assert tie.solver_receipt["self_check"]["picked"] == "primary"
