"""Research may change a comparison plan, never stock truth or empirical authority."""

from __future__ import annotations

import copy
import hashlib
import json
import socket
from dataclasses import replace
from functools import lru_cache

import pytest

from engine.formulation_intelligence import architecture_bridge as bridge
from engine.formulation_intelligence import formula_design_runtime as runtime
from engine.formulation_intelligence import subtype_research
from engine.formulation_intelligence.semantic_brief_adapter import compile_semantic_brief
from engine.research.contracts import FALSE_ACTION_AUTHORITY
from engine.research.formula_design import design_inventory_formula


@pytest.fixture(autouse=True)
def historical_v3(monkeypatch):
    # This suite freezes the 44-mapping v3 contract. Successor suites check
    # newer registries; a moving active path must not rewrite historical tests.
    monkeypatch.setattr(bridge, "ADAPTER_PATH", bridge.V3_PATH)
    monkeypatch.setattr(bridge, "ADAPTER_SCHEMA", "source-bound-architecture-adapters-v3")


def _interpretation(**overrides):
    return {
        "interpretation_sha256": "a" * 64,
        "must_preserve": [],
        "must_avoid": [],
        "explicit_materials": [],
        "material_count_constraints": [],
        **overrides,
    }


def _brief(prompt="A juicy lychee fruit perfume", interpretation=None, maximum=12):
    return compile_semantic_brief(
        formula_name="Architecture contract",
        request=prompt,
        interpretation=interpretation or _interpretation(),
        max_materials=maximum,
    )


def _plan(control=None, interpretation=None, **options):
    return bridge.derive_architecture_briefs(
        control=control or _brief(),
        interpretation=interpretation or _interpretation(),
        max_materials=options.pop("max_materials", 12),
        **options,
    )


def _manifest(*, v1=False):
    return json.loads((bridge.V1_PATH if v1 else bridge.V3_PATH).read_bytes())


def _replace_manifest(monkeypatch, tmp_path, payload, *, legacy=False):
    path = tmp_path / "architecture.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(bridge, "ADAPTER_PATH", path)
    if legacy:
        monkeypatch.setattr(bridge, "ADAPTER_SCHEMA", "source-bound-architecture-adapters-v1")


ADAPTERS = _manifest()["adapters"]
CARDS = {row["subtype_id"]: row for row in subtype_research.load_subtype_research()["cards"]}


def test_manifest_has_bounded_exact_source_mappings_not_formulas():
    manifest = _manifest()
    bridge.validate_adapter_manifest(manifest)
    assert len(manifest["adapters"]) == 44
    assert sum(len(row["options"]) for row in manifest["adapters"]) == 88
    assert manifest["authority"] == FALSE_ACTION_AUTHORITY
    for adapter in manifest["adapters"]:
        assert bridge._digest(CARDS[adapter["subtype_id"]]) == adapter["subtype_card_sha256"]
        assert adapter["source_bindings"] == CARDS[adapter["subtype_id"]]["source_bindings"]


@pytest.mark.parametrize("adapter", ADAPTERS, ids=[a["adapter_id"] for a in ADAPTERS])
def test_each_adapter_changes_executable_roles_and_retains_control(adapter):
    prompt = " ".join(group[0] for group in CARDS[adapter["subtype_id"]]["match_groups"])
    control = _brief(prompt)
    before = copy.deepcopy(control.as_dict())
    planned = _plan(control)
    assert planned.briefs[0] is control
    assert control.as_dict() == before
    assert planned.receipt["state"] == "SOURCE_BOUND_COMPARISON_READY"
    assert len(planned.briefs) == 3
    assert len({bridge.role_plan_signature(item.roles) for item in planned.briefs}) == 3
    assert planned.receipt["numeric_calibrations_admitted"] == []
    assert planned.receipt["authority"] == FALSE_ACTION_AUTHORITY
    assert planned.receipt["network_used"] is False
    assert planned.receipt["formula_action"] == "NO_CHANGE"
    protected = {
        role.role_id: role
        for role in control.roles
        if (
            role.exact_material
            or role.provenance not in bridge._OPTIONAL_PROVENANCE
            or role.role_id in bridge._CORE
        )
    }
    for candidate in planned.briefs[1:]:
        binding = candidate.architecture_plan
        assert binding["adapter_id"] == adapter["adapter_id"]
        assert binding["source_bindings"] == adapter["source_bindings"]
        assert binding["dose_evidence_class"] == "LOCAL_HEURISTIC"
        assert binding["sensory_preservation_measured"] is False
        assert binding["stock_aliases_inferred"] is False
        assert binding["authority"] == FALSE_ACTION_AUTHORITY
        roles = {r.role_id: r for r in candidate.roles}
        assert all(roles.get(key) == value for key, value in protected.items())
        added = roles[binding["role_id"]]
        template = bridge._TEMPLATES[binding["template_id"]]
        assert added.share == template.default_share
        assert added.max_raw_share == template.max_raw_share
        assert added.character_weights == template.character_weights
        assert added.exact_material is None
        assert added.provenance == "SOURCE_BOUND_ARCHITECTURE_HEURISTIC"
        assert candidate.target_intent == control.target_intent
        assert candidate.request_sha256 == control.request_sha256


@pytest.mark.parametrize(
    "mutation",
    [
        "authority",
        "numeric",
        "empty",
        "duplicate_adapter",
        "duplicate_option",
        "duplicate_source",
        "source_hash",
        "unknown_template",
        "unhashable_template",
        "calibrated_status",
        "duplicate_vocabulary",
        "unknown_policy",
    ],
)
def test_malformed_and_authoritative_adapters_fail_closed(mutation):
    manifest = _manifest()
    adapter = manifest["adapters"][0]
    option = adapter["options"][0]
    if mutation == "authority":
        manifest["authority"]["compounding_authority"] = True
    elif mutation == "numeric":
        option["dose_ul"] = 500
    elif mutation == "empty":
        manifest["adapters"] = []
    elif mutation == "duplicate_adapter":
        manifest["adapters"].append(copy.deepcopy(adapter))
    elif mutation == "duplicate_option":
        adapter["options"].append(copy.deepcopy(option))
    elif mutation == "duplicate_source":
        adapter["source_bindings"].append(copy.deepcopy(adapter["source_bindings"][0]))
    elif mutation == "source_hash":
        adapter["source_bindings"][0]["source_record_sha256"] = "unknown"
    elif mutation == "unknown_template":
        option["template_id"] = "autonomous_beauty"
    elif mutation == "unhashable_template":
        option["template_id"] = []
    elif mutation == "calibrated_status":
        option["status"] = "EMPIRICALLY_VALIDATED"
    elif mutation == "duplicate_vocabulary":
        option["query_terms"].append(option["query_terms"][0].upper())
    elif mutation == "unknown_policy":
        manifest["allocation_policy"] = "RAW_OAV"
    with pytest.raises(ValueError):
        bridge.validate_adapter_manifest(manifest)


def test_avoid_removes_conflicting_branch_without_erasing_independent_comparison():
    control = _brief()
    planned = _plan(control, _interpretation(must_avoid=["floral"]))
    assert len(planned.briefs) == 2
    assert planned.briefs[1].architecture_plan["option_id"] == "green_juice"
    assert any(
        row["reason"] == "EXPLICIT_AVOID_CONFLICT" for row in planned.receipt["withheld_options"]
    )


def test_preserve_and_count_ceiling_prevent_replacing_protected_optional_roles():
    control = _brief()
    interpretation = _interpretation(must_preserve=[r.label for r in control.roles])
    plan = _plan(control, interpretation, max_materials=len(control.roles))
    assert plan.briefs == (control,)
    assert {r["reason"] for r in plan.receipt["withheld_options"]} == {
        "NO_UNPROTECTED_ROLE_CAPACITY"
    }
    exact = {
        **interpretation,
        "material_count_constraints": [{"kind": "EXACT", "count": len(control.roles)}],
    }
    assert _plan(control, exact, max_materials=60).briefs == (control,)


def test_spare_capacity_can_add_role_but_never_truncate_protected_roles():
    control = _brief()
    protected = replace(
        control, roles=tuple(replace(r, provenance="PROMPT_DERIVED_FACET") for r in control.roles)
    )
    plan = _plan(protected, max_materials=len(control.roles) + 1)
    assert len(plan.briefs) == 3
    assert all(b.roles[:-1] == protected.roles for b in plan.briefs[1:])
    assert all(b.architecture_plan["replaced_optional_role_id"] is None for b in plan.briefs[1:])


def test_exact_stock_anchor_is_never_replaced():
    interpretation = _interpretation(explicit_materials=["Hedione"])
    control = _brief("A lychee perfume with Hedione", interpretation)
    anchors = tuple(role for role in control.roles if role.exact_material)
    assert anchors
    for candidate in _plan(control, interpretation).briefs:
        assert tuple(role for role in candidate.roles if role.exact_material) == anchors


@pytest.mark.parametrize(
    "fault,reason",
    [
        ("card", "SUBTYPE_CARD_DRIFT"),
        ("review", "SOURCE_REVIEW_UNAVAILABLE"),
        ("source", "SOURCE_RECORD_DRIFT"),
        ("binding", "SOURCE_BINDING_MISMATCH"),
    ],
)
def test_source_failure_is_isolated_to_dependent_branches(fault, reason):
    control = _brief("A lychee perfume with peppery freesia")
    context = copy.deepcopy(control.knowledge_context)
    card = next(
        c
        for c in context["subtype_context"]["cards"]
        if c["subtype_id"] == "ORCHARD_LYCHEE_CULTIVARS"
    )
    source_id = card["source_bindings"][0]["source_id"]
    if fault == "card":
        card["title"] += " changed"
    elif fault == "review":
        next(r for r in context["source_reviews"] if r["source_id"] == source_id)["allowed"] = False
    elif fault == "source":
        next(r for r in context["sources"] if r["source_id"] == source_id)["title"] += " changed"
    elif fault == "binding":
        card["source_bindings"] = []
    plan = _plan(replace(control, knowledge_context=context))
    assert len(plan.briefs) == 3
    assert all(b.architecture_plan["subtype_id"] == "FREESIA_PEPPER" for b in plan.briefs[1:])
    assert any(row["reason"] == reason for row in plan.receipt["withheld_options"])


def test_unavailable_addendum_does_not_clear_base_binding_or_enter_role_plan():
    control = _brief("A peppery freesia perfume")
    context = copy.deepcopy(control.knowledge_context)
    card = next(
        c for c in context["subtype_context"]["cards"] if c["subtype_id"] == "FREESIA_PEPPER"
    )
    original = next(a for a in ADAPTERS if a["subtype_id"] == "FREESIA_PEPPER")
    assert card["review_addenda"]
    base_ids = {b["source_id"] for b in original["source_bindings"]}
    for review in context["source_reviews"]:
        if review["source_id"] not in base_ids:
            review["allowed"] = False
    plan = _plan(replace(control, knowledge_context=context))
    assert len(plan.briefs) == 3
    assert all(
        b.architecture_plan["source_bindings"] == original["source_bindings"]
        for b in plan.briefs[1:]
    )


def test_extra_base_source_is_not_stripped_as_if_it_were_a_review_addendum():
    control = _brief()
    context = copy.deepcopy(control.knowledge_context)
    card = next(
        c
        for c in context["subtype_context"]["cards"]
        if c["subtype_id"] == "ORCHARD_LYCHEE_CULTIVARS"
    )
    card["source_bindings"].append(
        {"source_id": "new_unavailable_dependency", "source_record_sha256": "b" * 64}
    )
    plan = _plan(replace(control, knowledge_context=context))
    assert len(plan.briefs) == 1
    assert plan.receipt["withheld_options"][0]["reason"] == "SOURCE_BINDING_MISMATCH"


def test_control_protected_recognizers_are_constraints_independently_of_interpretation():
    control = _brief()
    protected = replace(control, protected_recognizers=tuple(r.label for r in control.roles))
    plan = _plan(protected, max_materials=len(protected.roles))
    assert plan.briefs == (protected,)
    assert plan.receipt["protected_recognizers"] == list(protected.protected_recognizers)
    assert {r["reason"] for r in plan.receipt["withheld_options"]} == {
        "NO_UNPROTECTED_ROLE_CAPACITY"
    }


def test_signature_ignores_cosmetic_relabeling_order_but_keeps_executable_policy():
    roles = _brief().roles
    relabeled = tuple(
        replace(r, role_id="changed_" + r.role_id, label="changed") for r in reversed(roles)
    )
    assert bridge.role_plan_signature(roles) == bridge.role_plan_signature(relabeled)
    changed = (replace(roles[0], share=roles[0].share + 0.01), *roles[1:])
    assert bridge.role_plan_signature(roles) != bridge.role_plan_signature(changed)
    changed_provenance = (
        replace(roles[0], provenance="SOURCE_BOUND_ARCHITECTURE_HEURISTIC"),
        *roles[1:],
    )
    assert bridge.role_plan_signature(roles) != bridge.role_plan_signature(changed_provenance)


def test_duplicate_plan_is_not_counted_as_architectural_diversity(monkeypatch, tmp_path):
    manifest = _manifest(v1=True)
    first = manifest["adapters"][0]["options"][0]
    duplicate = {
        **copy.deepcopy(first),
        "option_id": "cosmetic_alternative",
        "label": "Different words only",
    }
    manifest["adapters"][0]["options"] = [first, duplicate]
    _replace_manifest(monkeypatch, tmp_path, manifest, legacy=True)
    plan = _plan()
    assert len(plan.briefs) == 2
    assert plan.receipt["withheld_options"][0]["reason"] == "DUPLICATE_EXECUTABLE_ARCHITECTURE"


def test_prose_digits_do_not_become_quantities(monkeypatch, tmp_path):
    monkeypatch.setattr(bridge, "ADAPTER_PATH", bridge.V1_PATH)
    monkeypatch.setattr(bridge, "ADAPTER_SCHEMA", "source-bound-architecture-adapters-v1")
    before = _plan()
    manifest = _manifest(v1=True)
    for option in manifest["adapters"][0]["options"]:
        option["comparison_question"] = (
            "Would 97.7 percent imaginary fruit improve 500 minute perception?"
        )
    _replace_manifest(monkeypatch, tmp_path, manifest)
    after = _plan()
    assert [bridge.role_plan_signature(b.roles) for b in before.briefs] == [
        bridge.role_plan_signature(b.roles) for b in after.briefs
    ]
    assert before.receipt["plan_sha256"] != after.receipt["plan_sha256"]


def test_budget_and_offline_determinism(monkeypatch):
    def network_forbidden(*args, **kwargs):
        raise AssertionError("architecture planning must remain offline")

    monkeypatch.setattr(socket, "socket", network_forbidden)
    before = hashlib.sha256(bridge.ADAPTER_PATH.read_bytes()).hexdigest()
    first = _plan(max_architectures=1)
    assert first == _plan(max_architectures=1)
    assert len(first.briefs) == 2 and len(first.receipt["deferred_options"]) == 1
    assert _plan(max_architectures=0).briefs == (_brief(),)
    assert hashlib.sha256(bridge.ADAPTER_PATH.read_bytes()).hexdigest() == before


@pytest.mark.parametrize("budget", [True, -1, 3, 1.0, "2"])
def test_invalid_budget_is_not_coerced(budget):
    with pytest.raises(ValueError):
        _plan(max_architectures=budget)


def test_missing_adapter_is_reported_and_fast_mode_remains_independent(monkeypatch, tmp_path):
    before = design_inventory_formula(idea="A peppery freesia perfume", max_materials=12)
    monkeypatch.setattr(bridge, "ADAPTER_PATH", tmp_path / "absent.json")
    plan = _plan()
    assert plan.receipt["state"] == "WITHHOLD_UNKNOWN"
    assert plan.receipt["reason_codes"] == ["ARCHITECTURE_ADAPTER_UNAVAILABLE_OR_INVALID"]
    assert len(plan.briefs) == 1
    after = design_inventory_formula(idea="A peppery freesia perfume", max_materials=12)
    assert before == after


@pytest.mark.parametrize("mode", ["FAST_SKETCH", "DEEP_COMPOSE"])
def test_unrecovered_chimie_campaign_cannot_generate_adjacent_formula(mode):
    result = design_inventory_formula(idea="CHIMIE LHOMME, lavender incense", design_mode=mode)
    assert result["status"] == "WITHHELD_CAMPAIGN_IDENTITY"
    assert result["formula_action"] == "NO_CHANGE"
    assert result["initial_formula"] is result["optimized_formula"] is None
    assert result["design_variants"] == []
    assert result["formulation_knowledge"]["subtype_context"]["campaign_identity_holds"]


@pytest.mark.parametrize("mode", ["FAST_SKETCH", "DEEP_COMPOSE"])
def test_missing_campaign_governance_cannot_clear_a_campaign_hold(monkeypatch, tmp_path, mode):
    monkeypatch.setattr(subtype_research, "SUBTYPE_PATH", tmp_path / "missing.json")
    result = design_inventory_formula(idea="CHIMIE LHOMME, lavender incense", design_mode=mode)
    assert result["status"] == "WITHHELD_GOVERNANCE_UNAVAILABLE"
    assert result["optimized_formula"] is result["initial_formula"] is None
    assert result["design_variants"] == []
    assert result["formula_action"] == "NO_CHANGE"
    assert result["reason_codes"] == ["CAMPAIGN_GOVERNANCE_UNAVAILABLE"]


@lru_cache(maxsize=8)
def _design(prompt):
    return design_inventory_formula(idea=prompt, design_mode="DEEP_COMPOSE", max_materials=12)


@pytest.mark.parametrize(
    "prompt",
    [
        "A peppery freesia perfume",
        "A juicy lychee fruit perfume",
        "Lavender incense without Ambroxan",
    ],
)
def test_live_design_changes_roles_and_physical_rows_not_only_labels(prompt):
    result = _design(prompt)
    variants = result["design_variants"]
    assert len(variants) == 3
    assert variants[0]["architecture"]["kind"] == "UNCHANGED_CONTROL"
    assert len({v["role_plan_sha256"] for v in variants}) == 3
    physical = {
        tuple(
            sorted(
                (r["stock_id"], r["amount_decimal"], r["amount_unit"]) for r in v["formula"]["rows"]
            )
        )
        for v in variants
    }
    assert len(physical) == 3
    assert result["architecture_planning"]["state"] == "SOURCE_BOUND_COMPARISON_READY"
    assert result["optimization"]["architecture_preserved"] is False
    assert result["optimization"]["target_request_preserved"] is True
    for variant in variants:
        assert variant["ordering"] == "UNORDERED_UNTIL_SENSORY_COMPARISON"
        assert variant["formula"]["separate_totals"]["liquid_total_ul"] == "6000"
        assert variant["formula"]["request_alignment_decimal"] == "1.0"
        assert set(variant["roles_requested"]) == {r["role_id"] for r in variant["role_plan"]}
        assert variant["solver"]["prohibited_objectives_used"] == []
        assert variant["critic"]["filler_rows_added"] == 0
        # The Orris Liquid exclusion this used to check was lifted on Kenny's
        # request (ac32ee9); layered roles may now pick it.
        own_materials = {r["material"] for r in variant["formula"]["rows"]}
        for frame in (variant["temporal_hypothesis"] or {}).get("sequence", []):
            assert {r["material"] for r in frame["intended_roles"]} <= own_materials
    assert result["pleasantness"] is result["beauty_score"] is None
    assert all(result[key] is False for key in FALSE_ACTION_AUTHORITY)


def test_every_comparison_preserves_explicit_microlitres_and_crystal_mass():
    result = _design("A lychee perfume with exactly 15 uL of Hedione and crystal Ambrox")
    assert len(result["design_variants"]) == 3
    for variant in result["design_variants"]:
        rows = variant["formula"]["rows"]
        hedione = next(r for r in rows if r["identity_name"] == "Hedione")
        ambrox = next(r for r in rows if r["identity_name"] == "Ambrox Super")
        assert (hedione["amount_decimal"], hedione["amount_unit"]) == ("15", "uL")
        assert ambrox["amount_unit"] == "mg" and ambrox["operation"] == "MASS_ADD"
        assert variant["formula"]["basis_state"] == "SEPARATE_LIQUID_AND_SOLID_TOTALS"


def test_time_specific_comparisons_report_only_their_own_materials():
    result = _design("A peppery freesia perfume at 30 minutes with dry woods at 4 hours")
    assert len(result["design_variants"]) == 3
    for variant in result["design_variants"]:
        temporal = variant["temporal_hypothesis"]
        assert temporal and temporal["sequence"]
        own_materials = {r["material"] for r in variant["formula"]["rows"]}
        for frame in temporal["sequence"]:
            assert {r["material"] for r in frame["intended_roles"]} <= own_materials


@pytest.mark.parametrize("separator", ["_", "-", "/", " "])
def test_title_punctuation_cannot_reactivate_an_explicitly_avoided_subtype(separator):
    from engine.formulation_intelligence.literature_knowledge import retrieve_formulation_knowledge

    result = retrieve_formulation_knowledge(
        f"Diagnostic negated{separator}incense Lavender, without incense", avoid=("incense",),
    )
    assert "LAV_INCENSE" not in {c["subtype_id"] for c in result["subtype_context"]["cards"]}
    assert "lavender_incense" not in result["profile_ids"]


def test_negative_request_remains_negative_in_live_architecture_planning():
    result = design_inventory_formula(
        idea="Lavender, without incense", formula_name="Diagnostic negated_incense",
        must_avoid=("incense",), design_mode="DEEP_COMPOSE",
    )
    assert result["architecture_planning"]["state"] == "NO_APPLICABLE_ADAPTER"
    assert not result["architecture_planning"]["candidates"]
    assert all(v["architecture"]["kind"] != "SOURCE_BOUND_ARCHITECTURE_COMPARISON" for v in result["design_variants"])


def test_each_solve_is_criticized_against_its_own_role_plan(monkeypatch):
    actual = runtime.critique_formula
    inspected = []

    def check(**kwargs):
        brief, solve = kwargs["brief"], kwargs["solve"]
        assert {a.role.role_id for a in solve.assignments} == {r.role_id for r in brief.roles}
        inspected.append(bridge.role_plan_signature(brief.roles))
        return actual(**kwargs)

    monkeypatch.setattr(runtime, "critique_formula", check)
    result = design_inventory_formula(idea="A peppery freesia perfume", design_mode="DEEP_COMPOSE")
    assert len(inspected) == len(result["design_variants"]) == 3
    assert inspected == [v["role_plan_sha256"] for v in result["design_variants"]]


def test_failed_control_is_retained_and_not_relabelled_as_successful_stock_alternative(monkeypatch):
    actual = runtime.solve_formula

    def fail_first(**kwargs):
        result = actual(**kwargs)
        if kwargs["variant_index"] == 0:
            return replace(result, rows=(), status="WITHHELD_TEST_CONTROL")
        return result

    monkeypatch.setattr(runtime, "solve_formula", fail_first)
    result = design_inventory_formula(idea="A dry woody perfume", design_mode="DEEP_COMPOSE")
    assert result["architecture_attempts"][0]["state"] == "WITHHELD_TEST_CONTROL"
    assert len(result["design_variants"]) == 2
    for variant in result["design_variants"]:
        assert variant["label"] != "Unchanged structural control"
        assert variant["architecture"]["kind"] == "STOCK_ALTERNATIVE_SAME_ROLE_PLAN"


def test_hard_failed_variant_is_not_an_actionable_proposal(monkeypatch):
    actual = runtime.critique_formula

    def reject_source_branch(**kwargs):
        result = actual(**kwargs)
        if kwargs["brief"].architecture_plan:
            return replace(result, state="WITHHELD", issues=("TEST_HARD_FAILURE",))
        return result

    monkeypatch.setattr(runtime, "critique_formula", reject_source_branch)
    result = design_inventory_formula(idea="A peppery freesia perfume", design_mode="DEEP_COMPOSE")
    assert result["design_variants"][0]["formula_action"] == "PROPOSAL_ONLY"
    assert all(v["formula_action"] == "NO_CHANGE" for v in result["design_variants"][1:])


def test_architecture_benchmark_distinguishes_composition_from_roles():
    from engine.research.subtype_benchmark import audit_architectures

    result = copy.deepcopy(_design("A peppery freesia perfume"))
    before = audit_architectures(result)
    for variant in result["design_variants"]:
        variant["role_plan_sha256"] = "e" * 64
        for row in variant["formula"]["rows"]:
            row["row_id"] = "another_label"
            row["slot"] = "another_role"
            row["rationale"] = "Different prose"
    after = audit_architectures(result)
    assert [v["physical_composition_sha256"] for v in before["variants"]] == [
        v["physical_composition_sha256"] for v in after["variants"]
    ]
    assert [v["role_plan_sha256"] for v in before["variants"]] == [
        v["role_plan_sha256"] for v in after["variants"]
    ]
    assert all(v["role_plan_verified"] is False for v in after["variants"])
    result["design_variants"][0]["formula"]["rows"][0]["amount_decimal"] = "999"
    changed = audit_architectures(result)
    assert (
        changed["variants"][0]["physical_composition_sha256"]
        != before["variants"][0]["physical_composition_sha256"]
    )
