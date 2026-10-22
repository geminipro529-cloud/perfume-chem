"""A named note with a cited accord spec is built as that accord.

The lead prefers the spec's recognizer stocks; each helper row takes one of its
spec helper's own stocks, says its job, node function and sources, and is an
untested design idea. A helper IFRA limits below its share is placed with its
dose held inside the limit. A helper whose stocks cannot be placed keeps
today's same-query support in its slot, with the reason in the solver receipt.
Briefs naming no covered note are unchanged. Expectations come from
accord_spec_for, never hard-coded stock names.
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
from engine.ifra_standards import single_material_limit_pct

# Short local briefs, one per covered note.
_LAVENDER = "An aromatic fougere with oakmoss and tonka."
_IRIS = "Orris and soft woods."
_ROSE = "A fresh rose with green leaves and a clean musk."
_SANDALWOOD = "Sandalwood and soft woods."
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
        if row is None or slot in unplaced:
            # A part none of whose stocks could be placed: the receipt says
            # why for each cited stock, and the slot is empty or holds
            # today's same-query support with today's text.
            assert slot in unplaced, slot
            assert len(unplaced[slot]["reasons"]) == len(helper.stocks)
            if row is not None:
                index = int(slot.rsplit(adapter.ACCORD_SUPPORT_SEPARATOR, 1)[1])
                assert "accord" not in row and not _cited(helper.stocks, row)
                assert row["slot_label"] == f"{lead['slot_label']}: supporting accord material {index}"
                assert row["rationale"] == (
                    f"{row['slot_label']}: selected as the nonredundant {row['role']} for this concept "
                    "after hard exclusions and stock form were applied."
                )
            empty.append(slot)
            continue
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


def _brief_role(result: dict, role_id: str) -> adapter.SemanticRole:
    plan = next(item for item in result["design_variants"][0]["role_plan"] if item["role_id"] == role_id)
    return adapter.SemanticRole(**{
        **plan, "query_terms": tuple(plan["query_terms"]),
        "character_weights": tuple(tuple(w) for w in plan["character_weights"]),
    })


@pytest.mark.parametrize(("idea", "facet_id"), [(_IRIS, "iris_violet"), (_SANDALWOOD, "creamy_wood")])
def test_an_ifra_limited_cited_helper_is_placed_inside_its_limit(idea, facet_id):
    """Orivone (iris) and Sandalore (sandalwood): IFRA limits each below its
    helper's share, so the planner's IFRA cap holds the dose inside the limit."""

    result = _design(idea)
    helper_rows, empty = _check_accord(result, facet_id)
    assert helper_rows and not empty
    rows, receipt = _primary(result)
    assert receipt["missing_roles"] == []
    total = sum(float(row["amount_decimal"]) for row in rows if row["amount_unit"] == "uL")
    index = build_material_capability_index()
    for row in helper_rows:
        status, limit = single_material_limit_pct(row["identity_name"])
        assert status == "restricted" and limit is not None
        capability = next(cap for cap in index.capabilities if cap.stock_id == row["stock_id"])
        # The limit is below the helper's share: today's supporting-role
        # IFRA screen would refuse this stock.
        assert fs._ifra_binds_layer(capability, _brief_role(result, row["slot"]))
        amount = float(row["amount_decimal"])
        assert row["operation"] == "DIRECT_ADD" and amount >= 10
        # The solver's own worst case: the concentrate is 30% of the perfume.
        finished_pct = (amount / total * fs._CONCENTRATE_FINISHED_FRACTION
                        * float(row["stock_fraction_decimal"]) * 100)
        assert finished_pct <= limit + 1e-9, (row["identity_name"], finished_pct, limit)


def test_the_brief_exclusions_win_over_a_cited_helper_and_its_slot_keeps_todays_support(monkeypatch):
    """Every cited stock is on the avoid list: the slot is solved as today's
    clone (same stock and text, no accord key), and the receipt still lists
    the cited helper as unplaced."""

    stocks = _helper_slots("aromatic_lavender")
    (slot, helper), = stocks.items()
    avoid = tuple(dict.fromkeys(stock.name for stock in helper.stocks))
    result = _design(_LAVENDER, avoid)
    helper_rows, empty = _check_accord(result, "aromatic_lavender")
    assert not helper_rows and empty == [slot]
    rows, receipt = _primary(result)
    assert slot in {row["slot"] for row in rows}
    row = next(row for row in rows if row["slot"] == slot)
    assert not any(row["identity_name"] == name for name in avoid)
    (entry,) = [e for e in receipt["unplaced_accord_helpers"] if e["role_id"] == slot]
    assert all(reason.endswith("the brief's avoid list") for reason in entry["reasons"])
    # The stock is one today's clone admits: it carries the lead's note and
    # odor, or is the natural lead's one backing molecule.
    lead_row = next(item for item in rows if item["slot"] == "facet_aromatic_lavender")
    index = build_material_capability_index()
    stock, lead_stock = (
        next(cap for cap in index.capabilities if cap.stock_id == item["stock_id"]) for item in (row, lead_row)
    )
    clone = adapter.accord_support_clone(_brief_role(result, "facet_aromatic_lavender"), 1)
    assert fs._supports_accord(stock, clone, lead_stock) or fs._backs_natural_lead(stock, clone, lead_stock)
    # Today's composer, with no cited specs, writes the same text in that slot.
    monkeypatch.setattr(note_accord_specs, "accord_spec_for", lambda _facet_id: None)
    today_rows, _today = _primary(design_formula(
        idea=_LAVENDER, formula_name="Accord Probe", design_mode="FAST_SKETCH", must_avoid=avoid,
    ))
    today = next(item for item in today_rows if item["slot"] == slot)
    assert "accord" not in today
    for key in ("slot_label", "rationale", "note", "role"):
        assert row[key] == today[key], key


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
    """Two iris facet roles share one spec: only the first gets the cited
    helpers; the second keeps today's same-query supports."""

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
        *(f"facet_iris_root{adapter.ACCORD_SUPPORT_SEPARATOR}{i}" for i in (1, 2)),
    ]
    assert built[0].accord.part == "lead"
    assert built[0].accord.stocks == tuple((stock.name, stock.fraction) for stock in spec.lead_stocks)
    # The lead keeps its own query words (and equality), so a v5 refinement still finds it.
    assert built[0] == roles[0] and built[0].query_terms == roles[0].query_terms
    second = len(spec.helpers) + 1
    assert built[second] == roles[1] and built[second].accord is None
    for index, clone in enumerate(built[second + 1:], start=1):
        assert clone.accord is None and clone.provenance == adapter.ACCORD_SUPPORT_PROVENANCE
        assert clone.query_terms == roles[1].query_terms
        assert clone.label == f"{roles[1].label}: supporting accord material {index}"
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


def _capability(name: str, fraction: float):
    return next(
        cap for cap in build_material_capability_index().capabilities
        if cap.identity_name == name and abs(cap.candidate.stock.dilution - fraction) < 1e-9
    )


def _placed(*pairs) -> "fs._BeamState":
    """A search state holding these (role, capability) pairs, counted as the beam counts them."""

    groups: dict[str, int] = {}
    for _role, capability in pairs:
        fs._count_groups(groups, capability)
    return fs._BeamState(
        assignments=tuple((role, capability, 1.0) for role, capability in pairs),
        used_identities=frozenset(fs._chemical_identity(capability) for _role, capability in pairs),
        group_counts=tuple(sorted(groups.items())),
        objective=0.0,
    )


def _cited_roles(idea: str, facet_id: str) -> tuple[adapter.SemanticRole, adapter.SemanticRole]:
    brief = adapter.compile_semantic_brief(formula_name="Accord Probe", request=idea,
                                           interpretation={}, max_materials=30)
    by_id = {role.role_id: role for role in brief.roles}
    lead = by_id[f"facet_{facet_id}"]
    return lead, by_id[f"{lead.role_id}{adapter.ACCORD_SUPPORT_SEPARATOR}1"]


def _other_role(role_id: str, word: str) -> adapter.SemanticRole:
    return adapter.SemanticRole(role_id=role_id, label=word, note="heart", function="character",
                                query_terms=(word,), character_weights=(), share=.1)


def test_a_cited_helper_shares_its_own_leads_family_bucket():
    """Another iris stock is already in the formula beside the orris lead:
    the iris helper still goes in, as the cited pairing puts them together."""

    lead, helper = _cited_roles(_IRIS, "iris_violet")
    (stock,) = _helper_slots("iris_violet")[helper.role_id].stocks
    lead_stock = note_accord_specs.accord_spec_for("iris_violet").lead_stocks[0]
    capability = _capability(stock.name, stock.fraction)
    irone = _capability("Alpha Irone", .1)
    state = _placed((lead, _capability(lead_stock.name, lead_stock.fraction)),
                    (_other_role("facet_iris_root", "irone"), irone))
    assert fs._family_bucket(capability) == fs._family_bucket(irone) == "iris"
    assert dict(state.group_counts)["family:iris"] == 2
    assert fs._block_reason(capability, helper, state, avoid=(), allow_multiple_musks=False) is None
    # An ordinary support of the same note is still refused there.
    clone = adapter.accord_support_clone(lead, 1)
    assert fs._block_reason(capability, clone, state, avoid=(), allow_multiple_musks=False).startswith(
        "family-bucket rule (iris"
    )


def test_a_cited_helper_in_another_full_bucket_is_refused():
    """The rose helper's stock is in the jasmine bucket, which a jasmine
    stock already fills: the exemption covers only its lead's bucket."""

    lead, helper = _cited_roles(_ROSE, "rose")
    (stock,) = _helper_slots("rose")[helper.role_id].stocks
    lead_stock = note_accord_specs.accord_spec_for("rose").lead_stocks[0]
    capability = _capability(stock.name, stock.fraction)
    lead_capability = _capability(lead_stock.name, lead_stock.fraction)
    jasmine = _capability("Jasmine Absolute", .1)
    assert fs._family_bucket(capability) == fs._family_bucket(jasmine) == "jasmine"
    assert fs._family_bucket(lead_capability) == "rose"
    alone = _placed((lead, lead_capability))
    assert fs._block_reason(capability, helper, alone, avoid=(), allow_multiple_musks=False) is None
    state = _placed((lead, lead_capability), (_other_role("facet_jasmine", "jasmine"), jasmine))
    assert fs._block_reason(capability, helper, state, avoid=(), allow_multiple_musks=False) == (
        "family-bucket rule (jasmine already in the formula)"
    )


def test_a_cited_helper_ifra_leaves_under_one_transfer_is_refused():
    """The planner's IFRA cap would leave the helper less than 10 uL raw."""

    from engine.research.composition_planner import _ifra_cap_ul

    lead, helper = _cited_roles(_IRIS, "iris_violet")
    (stock,) = _helper_slots("iris_violet")[helper.role_id].stocks
    capability = _capability(stock.name, stock.fraction)
    lead_stock = note_accord_specs.accord_spec_for("iris_violet").lead_stocks[0]
    state = _placed((lead, _capability(lead_stock.name, lead_stock.fraction)))
    kwargs = dict(avoid=(), allow_multiple_musks=False)
    assert _ifra_cap_ul(capability.candidate, 6000) >= 10
    assert fs._block_reason(capability, helper, state, **kwargs, liquid_total_ul=6000) is None
    small = next(total for total in range(6000, 0, -100) if _ifra_cap_ul(capability.candidate, total) < 10)
    assert fs._block_reason(capability, helper, state, **kwargs, liquid_total_ul=small) == (
        "IFRA limit leaves under 10 uL raw"
    )


def test_a_cited_helper_ifra_limits_is_refused_where_the_ifra_cap_cannot_hold_it():
    """The planner's IFRA cap assumes the concentrate is at most 30% of the
    finished perfume; above that in the default 30 mL bottle (9,000 uL) it
    cannot hold the helper inside its limit, so the helper is refused."""

    from engine.research.composition_planner import IFRA_CAP_FINISHED_FRACTION

    lead, helper = _cited_roles(_IRIS, "iris_violet")
    (stock,) = _helper_slots("iris_violet")[helper.role_id].stocks
    capability = _capability(stock.name, stock.fraction)
    lead_stock = note_accord_specs.accord_spec_for("iris_violet").lead_stocks[0]
    state = _placed((lead, _capability(lead_stock.name, lead_stock.fraction)))
    held = int(IFRA_CAP_FINISHED_FRACTION * 30 * 1000)
    kwargs = dict(avoid=(), allow_multiple_musks=False)
    assert fs._block_reason(capability, helper, state, **kwargs, liquid_total_ul=held) is None
    assert fs._block_reason(capability, helper, state, **kwargs, liquid_total_ul=held + 1) == (
        f"IFRA limit, and the IFRA cap holds it only up to {held} uL of concentrate"
    )


def test_a_cited_helper_never_takes_the_one_stock_a_later_required_role_needs():
    """The iris root texture slot only one reviewed stock fills, and the iris
    helper cites that stock: the helper's slot keeps today's support and the
    formula is not withheld."""

    result = _design("Orris butter, iris root and violet leaf.")
    rows, receipt = _primary(result)
    assert receipt["missing_roles"] == []
    helper_slot = f"facet_iris_root{adapter.ACCORD_SUPPORT_SEPARATOR}1"
    (stock,) = _helper_slots("iris_root")[helper_slot].stocks
    by_slot = {row["slot"]: row for row in rows}
    assert by_slot["facet_iris_root_texture"]["identity_name"] == stock.name
    (entry,) = [e for e in receipt["unplaced_accord_helpers"] if e["role_id"] == helper_slot]
    assert entry["reasons"] == [
        f"{stock.name} at {stock.fraction:g}: kept for the required role "
        f"{by_slot['facet_iris_root_texture']['slot_label']}"
    ]
    assert "accord" not in by_slot[helper_slot]
