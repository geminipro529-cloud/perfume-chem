"""Immutable predecessor, live successor and fail-closed audit boundaries."""

import copy
import hashlib
import json
from dataclasses import replace
from functools import lru_cache

import pytest

from engine.formulation_intelligence import architecture_bridge as bridge
from engine.formulation_intelligence.semantic_brief_adapter import compile_semantic_brief
from engine.research.subtype_benchmark import audit_architectures


def _brief(text="A lychee fruit perfume"):
    return compile_semantic_brief(
        formula_name="Successor test", request=text, max_materials=12,
        interpretation={"must_avoid": [], "must_preserve": []},
    )


def _plan(brief=None):
    return bridge.derive_architecture_briefs(
        control=brief or _brief(), interpretation={}, max_materials=12,
    )


@lru_cache(maxsize=1)
def _design():
    from engine.research.formula_design import design_inventory_formula

    return design_inventory_formula(idea="A juicy lychee perfume", design_mode="DEEP_COMPOSE", max_materials=12)


def test_v1_is_exactly_preserved_and_explicitly_replayable(monkeypatch):
    v1 = json.loads(bridge.V1_PATH.read_bytes())
    v2 = json.loads(bridge.V2_PATH.read_bytes())
    v3 = json.loads(bridge.V3_PATH.read_bytes())
    v4 = json.loads(bridge.V4_PATH.read_bytes())
    v5 = json.loads(bridge.V5_PATH.read_bytes())
    assert hashlib.sha256(bridge.V1_PATH.read_bytes()).hexdigest() == bridge._V1_SHA256
    assert v2["adapters"][:10] == v1["adapters"]
    assert v3["adapters"][:22] == v2["adapters"]
    assert v4["adapters"][:44] == v3["adapters"]
    assert v5["adapters"][:47] == v4["adapters"]
    assert len(v1["adapters"]) == 10
    assert bridge.ADAPTER_PATH == bridge.V5_PATH
    assert bridge.ADAPTER_SCHEMA == "source-bound-architecture-adapters-v5"
    current = _plan()
    assert current.receipt["predecessor_sha256"] == bridge._V4_SHA256
    monkeypatch.setattr(bridge, "ADAPTER_PATH", bridge.V1_PATH)
    monkeypatch.setattr(bridge, "ADAPTER_SCHEMA", "source-bound-architecture-adapters-v1")
    replay = _plan()
    assert "predecessor_sha256" not in replay.receipt
    assert [bridge.role_plan_signature(b.roles) for b in replay.briefs] == [
        bridge.role_plan_signature(b.roles) for b in current.briefs
    ]
    monkeypatch.setattr(bridge, "ADAPTER_PATH", bridge.V2_PATH)
    monkeypatch.setattr(bridge, "ADAPTER_SCHEMA", "source-bound-architecture-adapters-v2")
    assert _plan().receipt["predecessor_sha256"] == bridge._V1_SHA256
    monkeypatch.setattr(bridge, "ADAPTER_PATH", bridge.V3_PATH)
    monkeypatch.setattr(bridge, "ADAPTER_SCHEMA", "source-bound-architecture-adapters-v3")
    assert _plan().receipt["predecessor_sha256"] == bridge._V2_SHA256


@pytest.mark.parametrize("fault", ["hash", "delete", "reorder", "change", "unknown", "path"])
def test_successor_cannot_rewrite_predecessor_or_select_external_path(fault):
    manifest = json.loads(bridge.ADAPTER_PATH.read_bytes())
    if fault == "hash":
        manifest["predecessor_sha256"] = "0" * 64
    elif fault == "delete":
        manifest["adapters"].pop(0)
    elif fault == "reorder":
        manifest["adapters"][:2] = reversed(manifest["adapters"][:2])
    elif fault == "change":
        manifest["adapters"][0]["title"] += " revised"
    else:
        manifest["predecessor_path" if fault == "path" else "approval"] = "caller choice"
    with pytest.raises(ValueError):
        bridge.validate_adapter_manifest(manifest)


@pytest.mark.parametrize("version", [1, 2, 3, 4])
@pytest.mark.parametrize("state", ["missing", "drifted"])
def test_missing_or_changed_predecessor_keeps_control_only(monkeypatch, tmp_path, state, version):
    predecessor = tmp_path / "v1.json"
    if state == "drifted":
        predecessor.write_bytes(getattr(bridge, f"V{version}_PATH").read_bytes() + b" ")
    monkeypatch.setattr(bridge, f"V{version}_PATH", predecessor)
    control = _brief()
    plan = _plan(control)
    assert plan.briefs == (control,)
    assert plan.receipt["state"] == "WITHHOLD_UNKNOWN"


def test_new_dependency_failure_withholds_only_its_branches():
    control = _brief("transparent tuberose and champaca")
    context = copy.deepcopy(control.knowledge_context)
    review = next(r for r in context["source_reviews"] if r["source_id"] == "iff_tuberose_completion")
    review["allowed"] = False
    plan = _plan(replace(control, knowledge_context=context))
    assert len(plan.briefs) == 3
    assert all(b.architecture_plan["subtype_id"] == "TROP_CHAMPACA" for b in plan.briefs[1:])
    assert any(r["reason"] == "SOURCE_REVIEW_UNAVAILABLE" for r in plan.receipt["withheld_options"])


def test_descriptor_eligibility_participates_in_executable_signature():
    role = _brief().roles[0]
    assert bridge.role_plan_signature([role]) != bridge.role_plan_signature([
        replace(role, descriptor_requirement="another_requirement")
    ])


def test_active_successor_cannot_downgrade_its_own_schema(monkeypatch, tmp_path):
    downgraded = json.loads(bridge.ADAPTER_PATH.read_bytes())
    downgraded["schema_version"] = "source-bound-architecture-adapters-v1"
    downgraded.pop("predecessor_sha256")
    downgraded["adapters"][0]["options"][0]["query_terms"] = ["forged"]
    path = tmp_path / "successor.json"
    path.write_text(json.dumps(downgraded), encoding="utf-8")
    monkeypatch.setattr(bridge, "ADAPTER_PATH", path)
    control = _brief()
    plan = _plan(control)
    assert plan.briefs == (control,)
    assert plan.receipt["state"] == "WITHHOLD_UNKNOWN"


@pytest.mark.parametrize("fault", ["missing_authority", "numeric_false", "missing_role", "forged_hash", "unknown_authority"])
def test_benchmark_never_defaults_missing_or_forged_evidence_to_pass(fault):
    result = copy.deepcopy(_design())
    variant = next(v for v in result["design_variants"] if v["architecture"]["kind"] == "SOURCE_BOUND_ARCHITECTURE_COMPARISON")
    if fault == "missing_authority":
        variant["architecture"].pop("authority")
    elif fault == "numeric_false":
        variant["architecture"]["authority"]["release_authority"] = 0
    elif fault == "unknown_authority":
        variant["architecture"]["authority"]["new_authority"] = False
    elif fault == "missing_role":
        variant["role_plan"][0].pop("query_terms")
    else:
        variant["role_plan_sha256"] = "not-a-hash"
    audited = next(v for v in audit_architectures(result)["variants"] if v["variant_id"] == variant["variant_id"])
    assert not (audited["authority_safe"] and audited["role_plan_verified"])


@pytest.mark.parametrize("field", ["authority_safe", "sensory_scores_absent", "network_used", "role_plan_verified"])
def test_control_arm_failures_cannot_borrow_safe_comparison_receipt(field):
    from engine.research.subtype_benchmark import architecture_pair_is_safe

    comparison = audit_architectures(_design())
    control = copy.deepcopy(comparison)
    assert architecture_pair_is_safe(control, comparison)
    if field == "role_plan_verified":
        control["variants"][0][field] = False
    else:
        control[field] = field == "network_used"
    assert not architecture_pair_is_safe(control, comparison)


@pytest.mark.parametrize("fault", ["omitted_dependency", "truthy_review", "wrong_manifest", "wrong_card"])
def test_source_closure_requires_complete_exact_dependencies(fault):
    result = copy.deepcopy(_design())
    variant = result["design_variants"][1]
    if fault == "omitted_dependency":
        # The lychee adapter has multiple primary dependencies.
        assert len(variant["architecture"]["source_bindings"]) > 1
        variant["architecture"]["source_bindings"].pop()
    elif fault == "truthy_review":
        source = variant["architecture"]["source_bindings"][0]["source_id"]
        next(r for r in result["formulation_knowledge"]["source_reviews"] if r["source_id"] == source)["allowed"] = "true"
    elif fault == "wrong_manifest":
        variant["architecture"]["adapter_manifest_sha256"] = "0" * 64
    else:
        variant["architecture"]["subtype_card_sha256"] = "0" * 64
    audited = audit_architectures(result)
    assert audited["variants"][1]["source_closure"] is False
