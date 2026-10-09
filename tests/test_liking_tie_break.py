"""Liking breaks ties only between materials that fit a role equally (Rule 3: fit leads)."""

import json
from dataclasses import replace
from functools import lru_cache
from types import SimpleNamespace

import pytest

from engine.formulation_intelligence import formula_solver as solver
from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.liking_tie_break import Liking, LikingLookup
from engine.formulation_intelligence.material_capability_index import build_material_capability_index
from engine.formulation_intelligence.pleasantness_table import crowd_pleasantness, load_crowd_table
from engine.formulation_intelligence.semantic_brief_adapter import compile_semantic_brief

# Smallest positive gap between distinct role-fit scores measured over the
# five briefs below (FAST_SKETCH and DEEP_COMPOSE, before the hash tie).
SMALLEST_MEASURED_GAP = 8.620689655192137e-05
BRIEFS = ("rose chypre", "amber iris smoke", "citrus cologne", "white floral", "green fougere")


@lru_cache(maxsize=1)
def _index():
    return build_material_capability_index()


@lru_cache(maxsize=1)
def _brief():
    return compile_semantic_brief(
        formula_name="Tie-break regression", request="rose chypre", max_materials=12,
        interpretation={"explicit_materials": [], "must_avoid": [],
                        "must_preserve": [], "material_count_constraints": []},
    )


def _pair():
    """A non-exact role and two distinct capabilities the solver admits for it."""
    brief = _brief()
    role = next(r for r in brief.roles if r.exact_material is None)
    ranked = solver._unary_rank_for_role(
        _index(), role, avoid=(), previous_stock_ids=frozenset(),
        prior_variant_stock_ids=frozenset(), variant_index=0,
    )
    state = solver._BeamState((), frozenset(), (), 0.0)
    allowed = [cap for _score, cap in ranked
               if solver._allowed(cap, role, state, avoid=(), allow_multiple_musks=False)]
    first = allowed[0]
    second = next(cap for cap in allowed[1:]
                  if cap.identity_name.casefold() != first.identity_name.casefold())
    return brief, role, first, second


def _scored(monkeypatch, scores):
    by_stock = {cap.stock_id: score for cap, score in scores}
    monkeypatch.setattr(solver, "capability_role_score",
                        lambda capability, **_: by_stock.get(capability.stock_id))
    return SimpleNamespace(capabilities=[cap for cap, _ in scores])


def _liking(values):
    return lambda name: Liking(values.get(name, 0.0), "crowd")


def _solve(brief, role, index, liking):
    assignments, _missing = solver._solve_assignments(
        brief=replace(brief, roles=(role,)), index=index, avoid=(),
        previous_stock_ids=frozenset(), prior_variant_stock_ids=frozenset(),
        variant_index=0, beam_width=12, liking=liking,
    )
    return assignments[0].capability


def _hash_order(role, a, b):
    """The pair as the 1e-6 hash tie alone would order it (winner first)."""
    tie = solver._stable_tie
    return (a, b) if tie(role.role_id, a.stock_id, 0) > tie(role.role_id, b.stock_id, 0) else (b, a)


def test_equal_role_fit_the_more_liked_material_wins(monkeypatch):
    brief, role, a, b = _pair()
    hash_winner, hash_loser = _hash_order(role, a, b)
    index = _scored(monkeypatch, [(a, 3.0), (b, 3.0)])
    liking = _liking({hash_winner.identity_name: -0.2, hash_loser.identity_name: 0.6})

    assert _solve(brief, role, index, liking=None).stock_id == hash_winner.stock_id
    assert _solve(brief, role, index, liking=liking).stock_id == hash_loser.stock_id
    ranked = solver._unary_rank_for_role(
        index, role, avoid=(), previous_stock_ids=frozenset(),
        prior_variant_stock_ids=frozenset(), variant_index=0, liking=liking,
    )
    assert ranked[0][1].stock_id == hash_loser.stock_id


def test_a_real_fit_difference_beats_a_much_more_liked_material(monkeypatch):
    brief, role, a, b = _pair()
    index = _scored(monkeypatch, [(a, 3.0 + SMALLEST_MEASURED_GAP), (b, 3.0)])
    liking = _liking({a.identity_name: -1.0, b.identity_name: 1.0})

    assert _solve(brief, role, index, liking=liking).stock_id == a.stock_id


def test_exact_material_roles_ignore_liking(monkeypatch):
    brief, role, a, b = _pair()
    exact = replace(role, exact_material=a.identity_name)
    index = _scored(monkeypatch, [(a, 3.0), (b, 3.0)])
    common = dict(avoid=(), previous_stock_ids=frozenset(), prior_variant_stock_ids=frozenset(),
                  variant_index=0)
    for values in ({a.identity_name: 1.0, b.identity_name: -1.0},
                   {a.identity_name: -1.0, b.identity_name: 1.0}):
        liked = solver._unary_rank_for_role(index, exact, liking=_liking(values), **common)
        plain = solver._unary_rank_for_role(index, exact, **common)
        assert [c.stock_id for _, c in liked] == [c.stock_id for _, c in plain]


def _crowd_name():
    return next(name for name in load_crowd_table()["materials"] if crowd_pleasantness(name) is not None)


def _personal_file(tmp_path, name, *, personal, evidence):
    path = tmp_path / "personal_liking.json"
    path.write_text(json.dumps({
        "schema": "personal_liking_v1", "ratings_used": 7, "picks_used": 2,
        "materials": {name.upper(): {"personal": personal, "crowd": None, "deviation": 0.0,
                                     "evidence": evidence, "n": 3}},
    }), encoding="utf-8")
    return path


def test_personal_value_needs_evidence_of_at_least_one_half(tmp_path):
    name = _crowd_name()
    crowd = crowd_pleasantness(name).value
    personal = -0.9 if crowd > 0 else 0.9

    enough = LikingLookup(_personal_file(tmp_path, name, personal=personal, evidence=0.5))
    assert enough(name) == Liking(personal, "personal")
    assert enough.receipt() == {"method": "ROUNDED_FIT_6DP_THEN_LIKING_V1", "weight": None,
                                "personal_file": True, "personal_ratings_used": 7}

    thin = LikingLookup(_personal_file(tmp_path, name, personal=personal, evidence=0.49))
    assert thin(name) == Liking(crowd, "crowd")


@pytest.mark.parametrize("content", [None, "{not json", '{"schema": "other", "materials": {}}',
                                     '{"schema": "personal_liking_v1", "materials": []}', "[]"])
def test_missing_or_corrupt_personal_file_means_no_personal_data(tmp_path, content):
    path = tmp_path / "personal_liking.json"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    lookup = LikingLookup(path)
    name = _crowd_name()

    assert lookup.personal_file is False
    assert lookup.personal_ratings_used == 0
    assert lookup(name) == Liking(crowd_pleasantness(name).value, "crowd")
    assert lookup("Not A Material In Any Table 9z") == Liking(0.0, "none")


class _NoLiking(LikingLookup):
    def __call__(self, identity_name):
        return Liking(0.0, "none")


def _picks():
    picks = {}
    for idea in BRIEFS:
        report = design_formula(idea=idea, design_mode="DEEP_COMPOSE")
        for number, variant in enumerate(report["design_variants"]):
            receipt = variant["solver"]
            assert receipt["pleasantness_claimed"] is False
            assert set(receipt["liking_tie_break"]) == {
                "method", "weight", "personal_file", "personal_ratings_used"}
            for row in variant["formula"]["rows"]:
                assert row["liking_tie_break"]["source"] in {"personal", "crowd", "none"}
                picks[(idea, number, row["slot"])] = row["identity_name"]
    return picks


def test_five_briefs_change_only_a_few_picks(monkeypatch, tmp_path):
    monkeypatch.setenv("PERFUME_PERSONAL_LIKING_PATH", str(tmp_path / "absent.json"))
    with_tie_break = _picks()
    monkeypatch.setattr(solver, "_liking_lookup", _NoLiking)
    without = _picks()

    changed = sorted(
        (key, without.get(key), with_tie_break.get(key))
        for key in set(with_tie_break) | set(without)
        if with_tie_break.get(key) != without.get(key)
    )
    # Measured 2026-10-09: Clove EO (India) -> Eugenol in the third DEEP_COMPOSE
    # variant's heart_spice_accent of "amber iris smoke" and "white floral".
    assert len(changed) <= 4, changed
