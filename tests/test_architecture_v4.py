"""Frozen chypre/cologne extension, option accounting and honest stock-pool holds."""

import copy
import hashlib
import json
from dataclasses import replace
from functools import lru_cache
from unittest.mock import patch

import pytest

from engine.formulation_intelligence import architecture_bridge as bridge
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)
from engine.formulation_intelligence.semantic_brief_adapter import (
    SemanticRole,
    compile_semantic_brief,
)
from engine.research import subtype_benchmark as bench


@pytest.fixture(autouse=True)
def staged_v4(monkeypatch):
    monkeypatch.setattr(bridge, "ADAPTER_PATH", bridge.V4_PATH)
    monkeypatch.setattr(bridge, "ADAPTER_SCHEMA", "source-bound-architecture-adapters-v4")


def _corpus():
    return bench._validate_v4_corpus(bench.ARCHITECTURE_CORPUS_V4.read_bytes())


def _plan(case):
    interpretation = {"must_avoid": case["must_avoid"], "must_preserve": case["must_preserve"]}
    control = compile_semantic_brief(
        formula_name=f"Architecture diagnostic {case['case_id']}", request=case["brief"],
        interpretation=interpretation, max_materials=12,
    )
    return bridge.derive_architecture_briefs(control=control, interpretation=interpretation, max_materials=12)


@lru_cache(maxsize=1)
def _index():
    return build_material_capability_index()


@lru_cache(maxsize=3)
def _design(case_id):
    case = next(c for c in _corpus()["cases"] if c["case_id"] == case_id)
    with patch.object(bench.socket, "create_connection", bench._forbid_network), \
            patch.object(bench.socket.socket, "connect", bench._forbid_network), \
            patch.object(bench.socket, "getaddrinfo", bench._forbid_network):
        return bench.design_formula(
            formula_name=f"Architecture diagnostic {case_id}", idea=case["brief"],
            design_mode="DEEP_COMPOSE", variant_count=3, max_materials=12,
            liquid_concentrate_ul_decimal="6000", must_avoid=tuple(case["must_avoid"]),
            must_preserve=tuple(case["must_preserve"]),
        )


def _audit(result):
    return bench.audit_architectures(result, inventory_index=_index())


def test_manifest_preserves_all_prior_mappings_and_binds_new_predicates():
    manifest = json.loads(bridge.V4_PATH.read_bytes())
    bridge.validate_adapter_manifest(manifest)
    assert manifest["adapters"][:44] == json.loads(bridge.V3_PATH.read_bytes())["adapters"]
    assert len(manifest["adapters"]) == 47
    assert sum(len(a["options"]) for a in manifest["adapters"]) == 93
    assert manifest["predecessor_sha256"] == hashlib.sha256(bridge.V3_PATH.read_bytes()).hexdigest()
    assert {(a["adapter_id"], o["option_id"]): o["descriptor_requirement"]
            for a in manifest["adapters"][44:] for o in a["options"]} == bridge._V4_REQUIREMENTS


@pytest.mark.parametrize("fault", ["missing", "loose", "swap", "unknown", "older_mapping"])
def test_descriptor_registry_cannot_be_downgraded(fault):
    manifest = json.loads(bridge.V4_PATH.read_bytes())
    option = manifest["adapters"][44]["options"][0]
    if fault == "missing":
        option.pop("descriptor_requirement")
    elif fault == "older_mapping":
        manifest["adapters"][0]["options"][0]["descriptor_requirement"] = "rose"
    else:
        option["descriptor_requirement"] = {"loose": None, "swap": "jasmine", "unknown": "floral"}[fault]
    with pytest.raises(ValueError):
        bridge.validate_adapter_manifest(manifest)


@pytest.mark.parametrize("case_id", [f"v4_{i:02d}" for i in range(1, 13)])
def test_planner_matches_frozen_new_case_options_and_does_not_promote_holds(case_id):
    corpus = _corpus()
    case = next(c for c in corpus["cases"] if c["case_id"] == case_id)
    plan = _plan(case)
    actual = [f"{b.architecture_plan['adapter_id']}:{b.architecture_plan['option_id']}" for b in plan.briefs[1:]]
    assert actual == corpus["option_expectations"][case_id]["planned_options"]
    for brief in plan.briefs[1:]:
        binding = brief.architecture_plan
        role = next(r for r in brief.roles if r.role_id == binding["role_id"])
        assert role.descriptor_requirement == binding["descriptor_requirement"]
        assert all(flag is False for flag in binding["authority"].values())
    if case["expected_hold"]:
        assert plan.receipt["state"] == "HOLD_EXACT_BRIEF_OR_FORMULA_REQUIRED"


@pytest.mark.parametrize("brief,avoid,options", [
    ("Chypre with a floral heart", [], ["rose_petals", "jasmine_bridge"]),
    ("A leafy chypre structure", [], ["bitter_resin", "watery_leaf"]),
    ("Citrus above soft wood", [], ["leaf_bridge"]),
    ("A floral chypre", ["rose"], ["jasmine_bridge"]),
    ("A floral chypre", ["jasmine"], ["rose_petals"]),
    ("A green chypre", ["bitter", "resin"], ["watery_leaf"]),
    ("A green chypre", ["watery", "leaf"], ["bitter_resin"]),
    ("A woody cologne", ["leaf"], []),
])
def test_paraphrases_and_option_specific_negative_space(brief, avoid, options):
    plan = _plan({"case_id": "neutral", "brief": brief, "must_avoid": avoid, "must_preserve": []})
    assert [b.architecture_plan["option_id"] for b in plan.briefs[1:]] == options


@pytest.mark.parametrize("fault", ["unknown_root", "configuration", "bool_config", "prefix", "new_brief",
                                   "unknown_case", "duplicate_case", "unknown_options", "duplicate_option",
                                   "incomplete_expectation", "hash"])
def test_preflight_rejects_changed_corpus_before_any_design(monkeypatch, tmp_path, fault):
    corpus = json.loads(bench.ARCHITECTURE_CORPUS_V4.read_bytes())
    if fault == "unknown_root":
        corpus["approved"] = True
    elif fault == "configuration":
        corpus["configuration"]["max_materials"] = 13
    elif fault == "bool_config":
        corpus["configuration"]["control_variants"] = True
    elif fault in {"prefix", "new_brief"}:
        corpus["cases"][0 if fault == "prefix" else -1]["brief"] += " changed"
    elif fault == "unknown_case":
        corpus["cases"][-1]["extra"] = "not executed"
    elif fault == "duplicate_case":
        corpus["cases"][-1]["case_id"] = corpus["cases"][-2]["case_id"]
    elif fault == "unknown_options":
        corpus["option_expectations"]["v4_01"]["external_authority"] = True
    elif fault == "duplicate_option":
        corpus["option_expectations"]["v4_01"]["planned_options"] *= 2
    elif fault == "incomplete_expectation":
        corpus["option_expectations"]["v4_01"]["required_viable_options"] = []
    raw = json.dumps(corpus).encode()
    # Raw pin alone must catch arbitrary byte/brief drift. Other mutations also
    # exercise independent structural checks, without changing the real fixture.
    if fault not in {"hash", "new_brief"}:
        monkeypatch.setattr(bench, "_V4_CORPUS_SHA256", hashlib.sha256(raw).hexdigest())
    replacement = tmp_path / "v4.json"
    replacement.write_bytes(raw)
    monkeypatch.setattr(bench, "ARCHITECTURE_CORPUS_V4", replacement)
    monkeypatch.setattr(bench, "build_material_capability_index", lambda: pytest.fail("preflight read inventory"))
    monkeypatch.setattr(bench, "design_formula", lambda **kw: pytest.fail("preflight reached design"))
    with pytest.raises(ValueError):
        bench.run_architecture_comparison(version=4)


@pytest.mark.parametrize("case_id", ["v4_01", "v4_02", "v4_03"])
def test_new_option_execution_satisfies_predeclared_contract(case_id):
    receipt = _audit(_design(case_id))
    assert receipt["planning_verified"] and receipt["attempts_verified"] and receipt["execution_verified"]
    assert bench.option_contract_passes(receipt, _corpus()["option_expectations"][case_id]), receipt["option_outcomes"]
    for outcome in receipt["option_outcomes"]:
        if outcome["empty_role_pool_verified"]:
            assert not outcome["eligible_stock_ids"] and not outcome["returned"]
            assert outcome["effective_inventory_sha256"] == _index().effective_inventory_sha256


@pytest.mark.parametrize("fault", ["drop", "duplicate", "swap", "inventory", "missing_role", "requirement"])
def test_failed_option_receipts_cannot_claim_an_empty_pool(fault):
    result = copy.deepcopy(_design("v4_03"))
    attempts = result["architecture_attempts"]
    if fault == "drop":
        attempts.pop()
    elif fault == "duplicate":
        attempts.append(copy.deepcopy(attempts[-1]))
    elif fault == "swap":
        attempts.reverse()
    elif fault == "inventory":
        result["architecture_execution_inputs"]["effective_inventory_sha256"] = "0" * 64
    elif fault == "missing_role":
        attempts[-1]["missing_roles"] = []
    else:
        attempts[-1]["solver"]["architecture_plan"]["descriptor_requirement"] = "rose"
    receipt = _audit(result)
    assert not receipt["option_coverage_verified"]
    assert not bench.option_contract_passes(receipt, _corpus()["option_expectations"]["v4_03"])


def test_empty_pool_is_exhaustive_and_cannot_be_inferred_from_a_consumed_or_truncated_pool(monkeypatch):
    result = _design("v4_03")
    verified, briefs = bench._replay_planning(result)
    assert verified
    brief = briefs[1]
    role = next(r for r in brief.roles if r.role_id == brief.architecture_plan["role_id"])
    cap = next(c for c in _index().capabilities if c.identity_name == "Hedione")
    restored = replace(cap, descriptor_vocabulary=frozenset({"citrus", "leaf", "floral"}))
    extended = replace(_index(), capabilities=(*_index().capabilities, restored))
    monkeypatch.setattr(bench.solver, "_unary_rank_for_role", lambda *args, **kw: [])
    assert restored.stock_id in bench._admissible_role_pool(extended, role, brief, [])


def test_negative_case_cannot_pass_merely_because_all_planned_options_failed():
    receipt = _audit(_design("v4_03"))
    empty = {"planned_options": [], "required_viable_options": [], "allow_empty_role_pool_options": []}
    assert not receipt["returned_options"]
    assert not bench.option_contract_passes(receipt, empty)


def test_beam_reserves_scarce_future_descriptor_candidate_without_relaxing_identity(monkeypatch):
    scarce = next(c for c in _index().capabilities if c.identity_name == "Hedione")
    alternative = next(c for c in _index().capabilities if c.identity_name == "Florol")
    broad = SemanticRole("broad", "Broad connector", "heart", "bridge", ("floral",), (), .1)
    specific = replace(broad, role_id="specific", label="Jasmine connector",
                       descriptor_requirement="jasmine", provenance="SOURCE_BOUND_ARCHITECTURE_HEURISTIC")
    brief = replace(compile_semantic_brief(formula_name="Scarcity regression", request="floral", interpretation={}, max_materials=12),
                    roles=(broad, specific))
    monkeypatch.setattr(bench.solver, "_unary_rank_for_role", lambda index, role, **kw:
                        [(100.0, scarce), (1.0, alternative)] if role.role_id == "broad" else [(1.0, scarce)])
    assigned, missing = bench.solver._solve_assignments(
        brief=brief, index=_index(), avoid=(), previous_stock_ids=frozenset(),
        prior_variant_stock_ids=frozenset(), variant_index=0, beam_width=1,
    )
    assert not missing
    assert [(a.role.role_id, a.capability.stock_id) for a in assigned] == [
        ("broad", alternative.stock_id), ("specific", scarce.stock_id),
    ]


def test_generated_result_artifact_is_exact_and_cannot_overwrite_history(tmp_path):
    path = tmp_path / "result.json"
    result = {"status": "PASS", "case_count": 68, "design_calls": 272, "authority": bench.AUTHORITY}
    receipt = bench.write_result_artifact(result, path)
    original = path.read_bytes()
    assert json.loads(original) == result
    assert receipt["artifact_sha256"] == hashlib.sha256(original).hexdigest()
    with pytest.raises(FileExistsError):
        bench.write_result_artifact({**result, "status": "FAIL"}, path)
    assert path.read_bytes() == original
