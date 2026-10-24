"""The skin-musk accord may hold two musks in distinct roles (owner's change,
"Build a base as strong as your own formulas").

One musk stays valid on its own (AGENTS.md); a second one goes only into a
skin-musk accord's supporting place, in a profile role (role, texture)
distinct from the musk already placed, and never past the release gate's
two-musk limit.  A brief that asks for one musk keeps one.
"""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache

import pytest

from engine.formulation_intelligence import formula_solver as fs
from engine.formulation_intelligence import semantic_brief_adapter as adapter
from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)
from engine.pipeline import gates

IRIS_MUSK = (
    "A hedonic iris-orris-violet musk perfume, unmistakably violet-iris, luxurious, "
    "deep and layered, with strong projection: violet from the first spray, iris and "
    "violet leading, a generous musk."
)


@lru_cache(maxsize=None)
def _capabilities():
    return build_material_capability_index().capabilities


def _capability(name: str, fraction: float = 1.0):
    return next(
        cap for cap in _capabilities()
        if cap.identity_name == name and abs(cap.candidate.stock.dilution - fraction) < 1e-9
    )


@lru_cache(maxsize=None)
def _roles() -> dict[str, adapter.SemanticRole]:
    brief = adapter.compile_semantic_brief(
        formula_name="Musk Probe", request=IRIS_MUSK, interpretation={}, max_materials=30,
    )
    return {role.role_id: role for role in brief.roles}


def _placed(*pairs) -> "fs._BeamState":
    """A search state holding these (role id, capability) pairs, counted as the beam counts them."""

    groups: dict[str, int] = {}
    for _role_id, capability in pairs:
        fs._count_groups(groups, capability)
    return fs._BeamState(
        assignments=tuple((_roles()[role_id], capability, 1.0) for role_id, capability in pairs),
        used_identities=frozenset(fs._chemical_identity(capability) for _role_id, capability in pairs),
        group_counts=tuple(sorted(groups.items())),
        objective=0.0,
    )


def _reason(capability, role_id: str, state, **kwargs):
    return fs._block_reason(
        capability, _roles()[role_id], state, avoid=(), allow_multiple_musks=False, **kwargs,
    )


def _musk_rows(result) -> list[dict]:
    rows = (result["optimized_formula"] or result["initial_formula"])["rows"]
    musks = {cap.identity_name for cap in _capabilities() if cap.group == "musk"}
    return [row for row in rows if row["identity_name"] in musks]


def test_formula_musk_limit_is_the_release_gates():
    assert fs._MAX_FORMULA_MUSKS == gates._MUSK_COUNT_LIMIT


@lru_cache(maxsize=None)
def _fast_iris_musk_rows() -> tuple[dict, ...]:
    return tuple(_musk_rows(design_formula(idea=IRIS_MUSK, design_mode="FAST_SKETCH")))


def _row_musk_role(row: dict):
    return fs._musk_role(next(cap for cap in _capabilities() if cap.stock_id == row["stock_id"]))


def test_fast_iris_musk_brief_builds_a_two_musk_skin_accord():
    musk_rows = list(_fast_iris_musk_rows())
    assert sorted(row["slot"] for row in musk_rows) == [
        "facet_skin_musk", "facet_skin_musk__accord_1",
    ], musk_rows
    roles = {
        fs._musk_role(next(cap for cap in _capabilities() if cap.identity_name == row["identity_name"]))
        for row in musk_rows
    }
    assert None not in roles
    assert len(roles) == 2, musk_rows


def test_second_musk_needs_a_distinct_musk_role():
    habanolide = _capability("Habanolide")
    state = _placed(("facet_skin_musk", habanolide))
    brassylate = _capability("Ethylene Brassylate")
    # Both are fixative-role veil musks: the second adds nothing distinct.
    assert fs._musk_role(brassylate) == fs._musk_role(habanolide)
    assert _reason(brassylate, "facet_skin_musk__accord_1", state).startswith(
        "one-musk rule (same musk role"
    )
    ambrettolide = _capability("Ambrettolide", .1)
    assert fs._musk_role(ambrettolide) != fs._musk_role(habanolide)
    assert _reason(ambrettolide, "facet_skin_musk__accord_1", state) is None


def test_a_third_musk_is_refused_at_the_gates_limit():
    state = _placed(
        ("facet_skin_musk", _capability("Ambrettolide", .1)),
        ("facet_skin_musk__accord_1", _capability("Ethylene Brassylate")),
    )
    assert _reason(_capability("Habanolide"), "facet_skin_musk__accord_2", state) == (
        "musk limit (two musks already)"
    )


@pytest.mark.parametrize("role_id", ["base_wood_layer", "heart_to_base_link"])
def test_guard_a_second_musk_outside_the_musk_accord_keeps_the_one_musk_rule(role_id):
    # Habanolide's role differs from Ambrettolide's, and it carries both
    # roles' own descriptors: only the place refuses it.
    state = _placed(("facet_skin_musk", _capability("Ambrettolide", .1)))
    assert _reason(_capability("Habanolide"), role_id, state) == "one-musk rule"


def test_a_musk_with_no_recorded_role_is_refused_as_the_second_musk():
    state = _placed(("facet_skin_musk", _capability("Ambrettolide", .1)))
    brassylate = _capability("Ethylene Brassylate")
    assert _reason(brassylate, "facet_skin_musk__accord_1", state) is None
    unassigned = replace(brassylate, candidate=replace(
        brassylate.candidate, profile=replace(brassylate.candidate.profile, role="unassigned"),
    ))
    assert fs._musk_role(unassigned) is None
    assert _reason(unassigned, "facet_skin_musk__accord_1", state).startswith(
        "one-musk rule (same musk role"
    )


def test_single_musk_request_is_read_from_the_brief_and_its_avoid_list():
    assert fs._single_musk_requested("a violet iris perfume with only one musk", ())
    assert fs._single_musk_requested("a violet iris perfume", ("add another musk",))
    assert not fs._single_musk_requested("a violet iris musk perfume", ())
    assert not fs._single_musk_requested("a violet iris musk perfume", ("vanilla",))
    state = _placed(("facet_skin_musk", _capability("Ambrettolide", .1)))
    assert _reason(
        _capability("Ethylene Brassylate"), "facet_skin_musk__accord_1", state, single_musk=True,
    ) == "one-musk rule (the brief asks for one musk)"


def test_not_only_musk_is_not_a_request_for_one_musk():
    # "Not only musk but amber too" asks for more than musk; it used to read
    # as "only musk" and blocked the skin-musk accord's second musk.
    assert not fs._single_musk_requested("a skin scent, not only musk but amber too", ())
    assert not fs._single_musk_requested("not only one musk but two", ())
    # "Not the only musk" read as "the only musk" and gave one musk.
    assert not fs._single_musk_requested("a violet iris musk perfume, and not the only musk", ())
    assert not fs._single_musk_requested("ambrettolide, but not the only musk", ())
    assert fs._single_musk_requested("a skin scent with only one musk", ())
    assert fs._single_musk_requested("a skin scent where ambrettolide is the only musk", ())


def test_deep_compose_brief_asking_for_one_musk_keeps_one():
    two = _musk_rows(design_formula(idea="a violet iris musk perfume", design_mode="DEEP_COMPOSE"))
    one = _musk_rows(design_formula(
        idea="a violet iris musk perfume with only one musk", design_mode="DEEP_COMPOSE",
    ))
    assert len(two) == 2, two
    assert len(one) == 1, one


def test_fast_iris_musk_brief_leads_with_a_fixative_musk_over_the_character_musk():
    """The owner's pattern: the bulk musk is a fixative-role one (Habanolide,
    Ethylene Brassylate) and the character musk (Ambrettolide) sits below it."""

    by_slot = {row["slot"]: row for row in _fast_iris_musk_rows()}
    lead, support = by_slot["facet_skin_musk"], by_slot["facet_skin_musk__accord_1"]
    assert _row_musk_role(lead)[0] == "fixative", lead["identity_name"]
    assert _row_musk_role(support)[0] == "character", support["identity_name"]

    def active(row):
        return float(row["amount_decimal"]) * float(row["stock_fraction_decimal"])

    assert active(support) < active(lead)


def test_character_musk_is_held_under_a_fixative_lead():
    habanolide = _capability("Habanolide")
    ambrettolide = _capability("Ambrettolide", .1)
    lead_role, support_role = _roles()["facet_skin_musk"], _roles()["facet_skin_musk__accord_1"]
    ranked = [(15.0, ambrettolide), (12.0, habanolide)]
    # The lead of a musk note takes the fixative-role musk ...
    assert fs._fixative_musk_leads(ranked, lead_role, single_musk=False) == [(12.0, habanolide)]
    # ... unless the brief asks for one musk, which keeps the best-matched one.
    assert fs._fixative_musk_leads(ranked, lead_role, single_musk=True) == ranked
    # The better-matched character musk is then held at its lead's score, not dropped.
    state = _placed(("facet_skin_musk", habanolide))
    state = replace(state, assignments=((lead_role, habanolide, 12.0),))
    out = fs._rank_for_state([(15.0, ambrettolide)], support_role, state, avoid=(), allow_multiple_musks=False)
    assert out == [(12.0, ambrettolide)]
