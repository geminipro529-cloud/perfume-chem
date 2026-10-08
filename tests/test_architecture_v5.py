"""Operation contracts, exact predicates and source-bound coverage; not scent tests."""

import copy
import hashlib
import json
from dataclasses import asdict, replace
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch

import pytest

from engine.formulation_intelligence import architecture_bridge as bridge
from engine.formulation_intelligence import architecture_rules_v5 as rules
from engine.formulation_intelligence import subtype_coverage as coverage
from engine.formulation_intelligence.semantic_brief_adapter import (
    SemanticRole,
    compile_semantic_brief,
)
from engine.research import subtype_benchmark as bench

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def staged_v5(monkeypatch):
    monkeypatch.setattr(bridge, "ADAPTER_PATH", bridge.V5_PATH)
    monkeypatch.setattr(bridge, "ADAPTER_SCHEMA", bridge._V5_SCHEMA)


def manifest():
    return json.loads(bridge.V5_PATH.read_bytes())


def option(key):
    value = manifest()
    adapter = next(a for a in value["adapters"] if a["adapter_id"] == key[0])
    return value, adapter, next(o for o in adapter["options"] if o["option_id"] == key[1])


def test_complete_source_census_and_frozen_prefix():
    value = manifest()
    bridge.validate_adapter_manifest(value)
    predecessor = json.loads(bridge.V4_PATH.read_bytes())
    assert value["adapters"][:47] == predecessor["adapters"]
    assert len(value["adapters"]) == 104
    assert sum(len(a["options"]) for a in value["adapters"]) == 168
    assert hashlib.sha256(bridge.V4_PATH.read_bytes()).hexdigest() == bridge._V4_SHA256
    cards = json.loads((ROOT / "data/formulation_knowledge/subtype_research_v4.json").read_bytes())["cards"]
    card_map = {c["subtype_id"]: c for c in cards}
    rows = coverage.load_dispositions()["dispositions"]
    old = {a["subtype_id"] for a in predecessor["adapters"]}
    assert {r["subtype_id"] for r in rows} == set(card_map) - old
    assert len(rows) == 132
    for row in rows:
        assert row["subtype_card_sha256"] == bridge._digest(card_map[row["subtype_id"]])
        assert row["source_bindings"] == card_map[row["subtype_id"]]["source_bindings"]
        assert row["sensory_validation"] == "NOT_TESTED"
        assert all(flag is False for flag in row["authority"].values())


@pytest.mark.parametrize("key", list(rules.OPTIONS))
def test_every_registered_operation_preserves_control_and_is_replayable(key):
    value, adapter, selected = option(key)
    anchor = SemanticRole("exact_anchor", "Protected", "heart", "character", ("anchor",), (), .2,
                          exact_material="Protected existing stock")
    optional = SemanticRole("optional", "Optional", "base", "bridge", ("wood",), (), .1,
                            provenance="MINIMUM_FUNCTIONAL_ARCHITECTURE")
    control = (anchor, optional)
    if selected["operation"] == "REFINE_ROLE":
        control = (anchor, bridge._canonical_refinement_role(selected["template_id"]), optional)
    original = copy.deepcopy(control)
    protected = bridge.protected_role_set(control, (), ())
    mapped = bridge.mapped_roles(control_roles=control, protected=protected, adapter=adapter,
                                 option=selected, max_materials=12, exact_count=False)
    assert mapped is not None
    roles, replaced = mapped
    binding = bridge.option_binding(manifest=value, manifest_hash="0" * 64, adapter=adapter,
                                    option=selected, roles=roles, control_roles=control,
                                    protected=protected, replaced_id=replaced)
    assert original == control and anchor in roles
    assert bridge.protected_roles_preserved(control, roles, protected, binding)
    assert binding["background_stock_doses_fixed"] is False
    assert binding["descriptor_absence_certified"] is False
    target = next(r for r in roles if r.role_id == binding["role_id"])
    assert target.descriptor_requirement == selected["descriptor_requirement"]
    if selected["operation"] == "REFINE_ROLE":
        assert len(control) == len(roles)
        assert binding["protected_and_prompt_roles_unchanged"] is False
        assert replace(target, descriptor_requirement=None) in control
        forged = {**binding, "operation_after_sha256": "a" * 64}
        assert not bridge.protected_roles_preserved(control, roles, protected, forged)


@pytest.mark.parametrize("field,value", [
    ("label", "Forged"), ("share", .8), ("required", False), ("exact_material", "Helvetolide"),
    ("query_terms", ("changed",)), ("character_weights", (("sweetness", 9),)),
    ("provenance", "UNTRUSTED"), ("descriptor_requirement", "fruit"),
    ("descriptor_requirement", "v5_helvetolide"), ("role_id", "fake"),
])
def test_refinement_rejects_forged_anchor_or_existing_predicate(field, value):
    _, adapter, selected = option(("hy_tea_musk_v5", "pear_musk"))
    canonical = bridge._canonical_refinement_role("skin_musk")
    forged = replace(canonical, **{field: value})
    assert bridge.mapped_roles(control_roles=(forged,), protected=(forged,), adapter=adapter,
                               option=selected, max_materials=12, exact_count=False) is None


@pytest.mark.parametrize("key", list(rules.REQUIREMENTS))
def test_all_predicate_conjuncts_are_required(key):
    groups = rules.REQUIREMENTS[key]
    vocabulary = frozenset(sorted(g)[0] for g in groups)
    identity = sorted(rules.EXACT_IDENTITIES.get(key, {"independently annotated stock"}))[0]
    assert rules.eligible(identity, vocabulary, key)
    for group in groups:
        assert not rules.eligible(identity, vocabulary - group, key)
    if key in rules.EXACT_IDENTITIES:
        assert not rules.eligible(identity + " unrelated grade", vocabulary, key)
    assert not rules.eligible(identity, vocabulary, "unknown")


@pytest.mark.parametrize("text", ["not smoky", "no jasmine", "without rose", "used in grape accords",
                                   "useful in pear perfumes", "Use: mango blends", "blends with apple",
                                   "useful as a floral modifier", "useful for fruit notes",
                                   "Keywords: milk fruit", "non-smoky wood", "smoke-free woody odor"])
def test_application_or_negated_clause_cannot_create_positive_odor(text):
    assert rules.positive_description(text) == ""


@pytest.mark.parametrize("fault", ["operation", "predicate", "target", "drop", "prefix", "authority", "extra"])
def test_v5_manifest_fails_closed(fault):
    value = manifest()
    selected = value["adapters"][-1]["options"][0]
    if fault == "operation":
        selected["operation"] = "RUN_FUNCTION"
    elif fault == "predicate":
        selected["descriptor_requirement"] = None
    elif fault == "target":
        selected["target_role_id"] = "exact_anchor"
    elif fault == "drop":
        value["adapters"].pop()
    elif fault == "prefix":
        value["adapters"][0]["options"][0]["label"] = "Changed"
    elif fault == "authority":
        value["authority"]["release_authority"] = True
    else:
        selected["mass"] = "10"
    with pytest.raises(ValueError):
        bridge.validate_adapter_manifest(value)


@pytest.mark.parametrize("brief_text,avoid,expected", [
    ("Lavender with crisp apple", [], ["crisp_apple", "ripe_apple"]),
    ("Lavender with apple, without cider", ["cider"], ["crisp_apple"]),
    ("A floral leather", [], ["floral_leather_bridge"]),
    ("Green tea and musk", [], ["powder_musk", "pear_musk"]),
    ("A smoky tobacco", [], ["smoky_wood"]),
    ("Creamy magnolia", [], ["musk_texture", "lactonic_texture"]),
])
def test_real_retrieval_and_planning(brief_text, avoid, expected):
    interpretation = {"must_avoid": avoid}
    control = compile_semantic_brief(formula_name="Neutral diagnostic", request=brief_text,
                                     interpretation=interpretation, max_materials=12)
    plan = bridge.derive_architecture_briefs(control=control, interpretation=interpretation, max_materials=12)
    assert [b.architecture_plan["option_id"] for b in plan.briefs[1:]] == expected
    assert plan.receipt["implementation_coverage"]["state"] == "ADVISORY_COVERAGE"
    assert plan.briefs[0] == control


def test_title_negation_cannot_swallow_the_separate_user_brief():
    control = compile_semantic_brief(
        formula_name="V5 acceptance - not a physical formula", request="mineral woody",
        interpretation={}, max_materials=12,
    )
    ids = {c["subtype_id"] for c in control.knowledge_context["subtype_context"]["cards"]}
    assert "WOOD_MINERAL" in ids


def test_explicit_avoid_still_applies_across_title_and_brief():
    control = compile_semantic_brief(
        formula_name="Smoky tobacco", request="A restrained musk, without tobacco",
        interpretation={"must_avoid": ["tobacco"]}, max_materials=12,
    )
    ids = {c["subtype_id"] for c in control.knowledge_context["subtype_context"]["cards"]}
    assert not any(i.startswith("TOBACCO_") for i in ids)


def test_v5_templates_do_not_rewrite_legacy_or_claim_smoke_absence():
    assert bridge._TEMPLATES["incense_resin"].character_weights == (("smoky", .75), ("woody", .5), ("warmth", .25))
    assert "smoky" not in dict(bridge._V5_TEMPLATES["v5_resin"].character_weights)
    assert rules.own_odor_avoid_conflict(frozenset({"resinous", "smoky"}), ["smoke"])
    assert not rules.own_odor_avoid_conflict(frozenset({"resinous"}), ["smoke"])
    assert bridge._digest({k: asdict(v) for k, v in bridge._TEMPLATES.items()}) != bridge._digest(
        {k: asdict(v) for k, v in bridge._V5_TEMPLATES.items()})


@lru_cache(maxsize=1)
def inventory_index():
    return bench.build_material_capability_index()


def test_actual_supplier_application_text_is_not_own_odor():
    from engine.ingredient_intelligence import _PROFILES

    text = rules.positive_description(_PROFILES["Ethyl Linalyl Acetate"]["character"])
    assert "bergamot" in text.casefold()
    assert "floral" not in text.casefold()
    text = rules.positive_description(_PROFILES["Acetoin"]["character"])
    assert "creamy" in text.casefold()
    assert "fruit" not in text.casefold() and "milk" not in text.casefold()


def test_exact_owned_dodecanal_label_is_not_mna_or_odor_evidence():
    vocab = frozenset({"waxy", "aldehydic"})
    assert rules.eligible("Aldehyde C-12 Lauric Dodecanal", vocab, "v5_dodecanal")
    assert not rules.eligible("Aldehyde C-12 MNA", vocab, "v5_dodecanal")
    assert not rules.eligible("Aldehyde C-12 Lauric Dodecanal", frozenset(), "v5_dodecanal")


def test_own_odor_avoid_reaches_unchanged_background_roles_in_v5():
    from engine.formulation_intelligence import formula_solver as solver
    from engine.formulation_intelligence.material_capability_index import (
        architecture_avoid_conflict,
    )

    cap = next(c for c in inventory_index().capabilities if c.identity_name == "Guaiacwood EO")
    role = SemanticRole("drydown_structure", "Base", "base", "structure", ("wood",), (), .2)
    state = solver._BeamState((), frozenset(), (), 0.0)
    assert "smoky" in cap.architecture_v5_vocabulary
    assert architecture_avoid_conflict(cap, None, ("smoke",), all_roles=True)
    assert not solver._allowed(cap, role, state, avoid=("smoke",),
                               allow_multiple_musks=False, enforce_own_odor_avoid=True)
    ranked = solver._unary_rank_for_role(
        replace(inventory_index(), capabilities=(cap,)), role, avoid=("smoke",),
        previous_stock_ids=frozenset(), prior_variant_stock_ids=frozenset(), variant_index=0,
        enforce_own_odor_avoid=True,
    )
    assert ranked == []


@pytest.mark.parametrize("fault", ["partial_review", "review_field", "manifest_hash"])
def test_source_reviews_revalidated_against_canonical_bytes(fault):
    control = compile_semantic_brief(formula_name="Neutral diagnostic", request="Lavender apple",
                                     interpretation={}, max_materials=12)
    context = copy.deepcopy(control.knowledge_context)
    adapter = next(a for a in manifest()["adapters"] if a["adapter_id"] == "lav_apple_v5")
    card = next(c for c in context["subtype_context"]["cards"] if c["subtype_id"] == adapter["subtype_id"])
    assert bridge._support_error(adapter, card, context) is None
    identity = adapter["source_bindings"][0]["source_id"]
    row = next(r for r in context["source_reviews"] if r["source_id"] == identity)
    if fault == "partial_review":
        row.clear()
        row.update(source_id=identity, allowed=True)
    elif fault == "review_field":
        row["review_scope"] = "FULL_TEXT"
    else:
        context["source_review_manifest_sha256"] = "0" * 64
    assert bridge._support_error(adapter, card, context) == "SOURCE_REVIEW_RECEIPT_DRIFT"


@pytest.mark.parametrize("case", json.loads(bench.ARCHITECTURE_CORPUS_V5.read_bytes())["cases"],
                         ids=lambda c: c["case_id"])
def test_frozen_v5_planner_covers_every_registered_operation(case):
    corpus = bench._validate_v5_corpus(bench.ARCHITECTURE_CORPUS_V5.read_bytes())
    it = {"must_avoid": case["must_avoid"], "must_preserve": case["must_preserve"]}
    control = compile_semantic_brief(formula_name=f"Architecture diagnostic {case['case_id']}",
                                     request=case["brief"], interpretation=it, max_materials=12)
    plan = bridge.derive_architecture_briefs(control=control, interpretation=it, max_materials=12)
    keys = [f"{b.architecture_plan['adapter_id']}:{b.architecture_plan['option_id']}" for b in plan.briefs[1:]]
    assert keys == corpus["option_expectations"][case["case_id"]]["planned_options"]
    assert plan.briefs[0] is control


@pytest.mark.parametrize("fault", ["bytes", "corpus", "options", "outcome_policy"])
def test_v5_protocol_mutation_fails_before_execution(monkeypatch, tmp_path, fault):
    value = json.loads(bench.ARCHITECTURE_CORPUS_V5.read_bytes())
    if fault in {"bytes", "corpus"}:
        value["configuration"]["ranking_allowed"] = True
    elif fault == "options":
        value["option_expectations"]["v5_01"]["planned_options"] = ["run:shell"]
    else:
        value["option_expectations"]["v5_01"]["allowed_verified_outcomes"].append("UNVERIFIED")
    raw = json.dumps(value).encode()
    if fault != "bytes":
        monkeypatch.setattr(bench, "_V5_CORPUS_SHA256", hashlib.sha256(raw).hexdigest())
    path = tmp_path / "v5.json"
    path.write_bytes(raw)
    monkeypatch.setattr(bench, "ARCHITECTURE_CORPUS_V5", path)
    monkeypatch.setattr(bench, "design_formula", lambda **kw: pytest.fail("executed invalid protocol"))
    monkeypatch.setattr(bench, "build_material_capability_index", lambda: pytest.fail("read inventory before preflight"))
    with pytest.raises(ValueError):
        bench.run_architecture_comparison(version=5)


@pytest.mark.parametrize("brief_text", [
    "Lavender with crisp apple", "A floral leather", "Green tea and musk",
    "A smoky tobacco", "Creamy magnolia", "Vanilla floral gourmand",
])
def test_current_inventory_execution_and_receipts(brief_text):
    with patch.object(bench.socket, "create_connection", bench._forbid_network), \
            patch.object(bench.socket.socket, "connect", bench._forbid_network), \
            patch.object(bench.socket, "getaddrinfo", bench._forbid_network):
        result = bench.design_formula(formula_name="Neutral diagnostic", idea=brief_text,
                                      design_mode="DEEP_COMPOSE", variant_count=3, max_materials=12,
                                      liquid_concentrate_ul_decimal="6000")
        audited = bench.audit_architectures(result, inventory_index=inventory_index())
    assert audited["planning_verified"]
    assert audited["attempts_verified"]
    assert audited["execution_verified"]
    assert audited["option_coverage_verified"]
    assert all(v["registered_option_verified"] and v["protected_roles_preserved"]
               for v in audited["variants"])
    print(brief_text, audited["viable_options"], audited["empty_role_pool_options"], flush=True)
