"""A named note with a cited accord spec is built as that accord.

The lead prefers the spec's recognizer stocks; each helper row takes one of its
spec helper's own stocks, says its job, node function and sources, and is an
untested design idea. A helper whose stocks cannot be placed stays empty, with
the reason in the solver receipt. Briefs naming no covered note are unchanged.
Expectations come from accord_spec_for, never hard-coded stock names.
"""

from __future__ import annotations

from functools import lru_cache

import pytest

from engine.formulation_intelligence import formula_solver as fs
from engine.formulation_intelligence import note_accord_specs
from engine.formulation_intelligence import semantic_brief_adapter as adapter
from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)

# Short local briefs, one per covered note.
_LAVENDER = "An aromatic fougere with oakmoss and tonka."
_IRIS = "Orris and soft woods."
_ROSE = "A fresh rose with green leaves and a clean musk."
# Briefs that name no covered note.
_UNCOVERED = ("A bright citrus cologne with neroli and petitgrain.", "A warm vanilla amber with benzoin.")


@lru_cache(maxsize=None)
def _design(idea: str, avoid: tuple[str, ...] = ()) -> dict:
    return design_formula(idea=idea, formula_name="Accord Probe", design_mode="FAST_SKETCH",
                          must_avoid=avoid)


def _primary(result: dict) -> tuple[list[dict], dict]:
    variant = result["design_variants"][0]
    return variant["formula"]["rows"], variant["solver"]


def _helper_slots(facet_id: str) -> dict[str, note_accord_specs.Helper]:
    spec = note_accord_specs.accord_spec_for(facet_id)
    lead = f"facet_{facet_id}"
    return {
        f"{lead}{adapter.ACCORD_SUPPORT_SEPARATOR}{index}": helper
        for index, helper in enumerate(spec.helpers, start=1)
    }


def _cited(stocks, row: dict) -> bool:
    return any(
        stock.name == row["identity_name"] and abs(stock.fraction - float(row["stock_fraction_decimal"])) < 1e-9
        for stock in stocks
    )


def _check_accord(result: dict, facet_id: str) -> tuple[list[dict], list[str]]:
    """Assert the accord's rows and receipt; return its helper rows and empty helper slots."""

    spec = note_accord_specs.accord_spec_for(facet_id)
    rows, receipt = _primary(result)
    by_slot = {row["slot"]: row for row in rows}
    lead = by_slot[f"facet_{facet_id}"]
    if _cited(spec.lead_stocks, lead):
        assert lead["rationale"] == (
            f"{spec.note.capitalize()} accord, lead ({spec.lead.function}), "
            f"source {', '.join(spec.lead.source_ids)}, untested design idea."
        )
        assert lead["accord"] == {
            "note": spec.note, "part": "lead", "job": None,
            "function": spec.lead.function, "source_ids": list(spec.lead.source_ids),
        }
    else:
        assert "accord" not in lead and "accord, lead" not in lead["rationale"]
    unplaced = {entry["role_id"]: entry for entry in receipt.get("unplaced_accord_helpers", ())}
    helper_rows, empty = [], []
    for slot, helper in _helper_slots(facet_id).items():
        row = by_slot.get(slot)
        if row is None:
            # No helper row for a part none of whose stocks could be placed,
            # and the receipt says why for each cited stock.
            assert slot in unplaced, slot
            assert len(unplaced[slot]["reasons"]) == len(helper.stocks)
            empty.append(slot)
            continue
        assert slot not in unplaced
        assert _cited(helper.stocks, row), (row["identity_name"], row["stock_fraction_decimal"])
        assert helper.job in row["rationale"] and helper.node.function in row["rationale"]
        assert all(source in row["rationale"] for source in helper.node.source_ids)
        assert row["rationale"] == (
            f"{spec.note.capitalize()} accord, helper: {helper.job} ({helper.node.function}), "
            f"source {', '.join(helper.node.source_ids)}, untested design idea."
        )
        assert row["accord"] == {
            "note": spec.note, "part": "helper", "job": helper.job,
            "function": helper.node.function, "source_ids": list(helper.node.source_ids),
        }
        helper_rows.append(row)
    return helper_rows, empty


def test_a_fougere_builds_the_cited_lavender_accord():
    helper_rows, empty = _check_accord(_design(_LAVENDER), "aromatic_lavender")
    assert helper_rows and not empty


def test_a_rose_builds_the_cited_rose_accord():
    helper_rows, empty = _check_accord(_design(_ROSE), "rose")
    assert helper_rows and not empty


def test_an_iris_helper_that_cannot_be_placed_stays_empty():
    _helper_rows, empty = _check_accord(_design(_IRIS), "iris_violet")
    # Orris names the iris spec; its one cited helper stock cannot be placed
    # here (the receipt gives the rule), so no row stands in for it.
    assert empty
    _rows, receipt = _primary(_design(_IRIS))
    assert receipt["missing_roles"] == []


def test_the_brief_exclusions_win_over_a_cited_helper():
    stocks = _helper_slots("aromatic_lavender")
    (slot, helper), = stocks.items()
    result = _design(_LAVENDER, (helper.stocks[0].name,))
    rows, receipt = _primary(result)
    assert slot not in {row["slot"] for row in rows}
    (entry,) = [e for e in receipt["unplaced_accord_helpers"] if e["role_id"] == slot]
    assert all(reason.endswith("the brief's avoid list") for reason in entry["reasons"])


def test_a_cited_helper_need_not_carry_the_lead_odor():
    """The lavender helper's stock fails the support odor-match rule, yet is placed."""

    rows, _receipt = _primary(_design(_LAVENDER))
    by_slot = {row["slot"]: row for row in rows}
    (slot, _helper), = _helper_slots("aromatic_lavender").items()
    helper_row, lead_row = by_slot[slot], by_slot["facet_aromatic_lavender"]
    index = build_material_capability_index()
    helper_cap, lead_cap = (
        next(cap for cap in index.capabilities if cap.stock_id == row["stock_id"])
        for row in (helper_row, lead_row)
    )
    plan = next(
        item for item in _design(_LAVENDER)["design_variants"][0]["role_plan"] if item["role_id"] == slot
    )
    brief_role = adapter.SemanticRole(**{
        **plan, "query_terms": tuple(plan["query_terms"]),
        "character_weights": tuple(tuple(w) for w in plan["character_weights"]),
    })
    assert brief_role.accord is not None
    # As an ordinary accord support this stock would be refused.
    assert not fs._supports_accord(helper_cap, brief_role, lead_cap)
    assert helper_row["accord"]["part"] == "helper"


def test_one_spec_builds_its_helpers_once_per_note():
    """Two iris facet roles share one spec: only the first gets the helpers."""

    def facet_role(facet_id: str) -> adapter.SemanticRole:
        return adapter.SemanticRole(
            role_id=f"facet_{facet_id}", label=facet_id, note="heart", function="character",
            query_terms=("iris",), character_weights=(("powdery", 1.0),), share=.1,
        )

    roles = [facet_role("iris_violet"), facet_role("iris_root")]
    spec = note_accord_specs.accord_spec_for("iris_violet")
    assert note_accord_specs.accord_spec_for("iris_root") is spec
    built = adapter._with_accords(roles, 20, " iris root ")
    assert [role.role_id for role in built] == [
        "facet_iris_violet",
        *(f"facet_iris_violet{adapter.ACCORD_SUPPORT_SEPARATOR}{i}" for i in range(1, len(spec.helpers) + 1)),
        "facet_iris_root",
    ]
    assert built[0].accord.part == "lead"
    assert built[0].accord.stocks == tuple((stock.name, stock.fraction) for stock in spec.lead_stocks)
    # The lead keeps its own query words (and equality), so a v5 refinement still finds it.
    assert built[0] == roles[0] and built[0].query_terms == roles[0].query_terms
    assert built[-1] == roles[1]
    helper = built[1]
    assert helper.share == pytest.approx(roles[0].share * spec.helpers[0].share_of_lead)
    assert helper.max_raw_share == pytest.approx(.28 * spec.helpers[0].share_of_lead)


@pytest.mark.parametrize("idea", [_LAVENDER, _IRIS, _ROSE])
def test_a_cited_lead_prefers_its_spec_lead_stocks(idea):
    """The spec's lead stocks gain on every other stock when the lead is scored."""

    from dataclasses import replace

    brief = adapter.compile_semantic_brief(formula_name="Accord Probe", request=idea,
                                           interpretation={}, max_materials=30)
    lead = next(role for role in brief.roles if role.accord is not None and role.accord.part == "lead")
    index = build_material_capability_index()

    def margin(role) -> float:
        ranked = fs._unary_rank_for_role(index, role, avoid=(), previous_stock_ids=frozenset(),
                                         prior_variant_stock_ids=frozenset(), variant_index=0,
                                         request=idea)
        cited = [s for s, cap in ranked if lead.accord.cites(cap.identity_name, cap.candidate.stock.dilution)]
        other = [s for s, cap in ranked if not lead.accord.cites(cap.identity_name, cap.candidate.stock.dilution)]
        return max(cited) - max(other)

    assert margin(lead) > margin(replace(lead, accord=None)) + 1.0


def test_a_covered_facet_the_brief_does_not_name_keeps_todays_supports():
    """A violet-only brief reaches the iris facet without naming iris or orris."""

    role = adapter.SemanticRole(
        role_id="facet_iris_violet", label="violet", note="heart", function="character",
        query_terms=("violet",), character_weights=(), share=.1,
    )
    built = adapter._with_accords([role], 20, " violet ")
    assert all(item.accord is None for item in built)
    assert len(built) == 3 and built[1].query_terms == role.query_terms


@pytest.mark.parametrize("idea", _UNCOVERED)
def test_a_brief_naming_no_covered_note_is_unchanged(idea, monkeypatch):
    with_specs = design_formula(idea=idea, formula_name="Accord Probe", design_mode="FAST_SKETCH")
    monkeypatch.setattr(note_accord_specs, "accord_spec_for", lambda _facet_id: None)
    without = design_formula(idea=idea, formula_name="Accord Probe", design_mode="FAST_SKETCH")
    # The forced-empty lookup does reach the composer: a rose loses its accord.
    rose_rows, _receipt = _primary(design_formula(idea=_ROSE, formula_name="Accord Probe",
                                                  design_mode="FAST_SKETCH"))
    assert not any("accord" in row for row in rose_rows)
    for key in ("optimized_formula", "semantic_brief"):
        assert with_specs[key] == without[key]
    assert [v["formula"]["rows"] for v in with_specs["design_variants"]] == [
        v["formula"]["rows"] for v in without["design_variants"]
    ]
    assert [v["role_plan_sha256"] for v in with_specs["design_variants"]] == [
        v["role_plan_sha256"] for v in without["design_variants"]
    ]
    assert not any("accord" in row for row in with_specs["optimized_formula"]["rows"])
