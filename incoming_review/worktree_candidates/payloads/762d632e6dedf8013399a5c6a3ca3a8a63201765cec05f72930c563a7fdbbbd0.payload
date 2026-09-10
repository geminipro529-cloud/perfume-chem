from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from engine.families.registry import evaluate_family_archetype
from engine.knowledge.perfume_knowledge import resolve_family_key
from engine.perception.dhi_2011_architecture import (
    DHI2011AuthorityVectorV1,
    DHI2011Criterion,
    DHI2011DepthDimension,
    DHI2011EvidenceTier,
    DHI2011ProgramState,
    build_default_dhi_2011_architecture,
)
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig, _check_skeleton
from engine.pipeline.oav_intelligence import _map_family
from engine.reference_contracts import (
    ARCHITECTURE,
    REFERENCE_CONTRACTS,
    detect_reference_claim,
    evaluate_reference_contract,
)
from scripts.verify_formula_workflow import parse_formula_markdown

ROOT = Path(__file__).resolve().parents[1]
FORMULA_PATH = (
    ROOT
    / "formulas"
    / "DHI-11_Velours_d_Iris_05443A_30mL_20pct_V3_Smooth.md"
)
CONTRACT_ID = "dior_homme_intense_2011_05443a_architecture_v1"


@pytest.fixture(scope="module")
def architecture():
    return build_default_dhi_2011_architecture()


@pytest.fixture(scope="module")
def formula():
    parsed = parse_formula_markdown(FORMULA_PATH)
    assert len(parsed) == 1
    return parsed[0]


@pytest.fixture(scope="module")
def formula_state(formula):
    return build_formula_state(
        formula["ingredients_ul"],
        formula["dilutions"],
        batch_volume_ml=30.0,
        temperature_K=305.0,
    )


def test_target_is_exactly_version_locked_and_never_quantitative_truth(architecture):
    request, result = architecture
    target = request.target

    assert target.target_id == "dhi-2011-05443a-v1"
    assert target.formula_code_scope == "05443/A"
    assert target.edition_window == "2011-2014 collector-associated package lineage"
    assert "UNKNOWN" in target.exact_formula_status
    assert "authenticated public quantitative" in target.exact_formula_status
    assert target.claim_ceiling == "COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY"
    assert result.claim_ceiling == target.claim_ceiling
    assert "REFERENCE_SAMPLE_REQUIRED_FOR_SIMILARITY" in result.reason_codes


def test_evidence_graph_keeps_fact_inference_and_unknown_separate(architecture):
    request, _result = architecture
    evidence = {item.claim_id: item for item in request.evidence_claims}

    assert evidence["evidence:dhi2011:house"].tier is DHI2011EvidenceTier.PERSISTENT_HOUSE_DESCRIPTION
    assert evidence["evidence:dhi2011:launch"].tier is DHI2011EvidenceTier.CONTEMPORANEOUS_LAUNCH_REPORT
    assert evidence["evidence:dhi2011:version"].tier is DHI2011EvidenceTier.COLLECTOR_VERSION_EVIDENCE
    assert evidence["evidence:dhi2011:cocoa"].tier is DHI2011EvidenceTier.PERFUMER_INFERENCE
    assert "unconfirmed" in evidence["evidence:dhi2011:cocoa"].uncertainty.lower()
    assert evidence["evidence:dhi2011:quantitative-gap"].tier is DHI2011EvidenceTier.REFERENCE_SAMPLE_TEST_REQUIRED
    assert all(item.source_refs for item in evidence.values())


def test_selected_architecture_is_pareto_not_scalar_or_count_based(architecture):
    request, result = architecture

    assert result.state is DHI2011ProgramState.THEORY_SELECTED
    assert result.selected_candidate_id == "candidate:ambrette-orris-velvet"
    assert result.frontier_candidate_ids == ("candidate:ambrette-orris-velvet",)
    assert request.component_count_used_as_complexity is False
    assert request.predicted_oav_used_as_perception is False
    assert request.composition_score_used_as_hedonic is False
    assert len(result.dominance_records) >= len(request.candidates) - 1
    assert all(record.stronger_criteria for record in result.dominance_records)
    assert "PARETO_SELECTION_NO_SCALAR_BEAUTY_SCORE" in result.reason_codes


def test_every_candidate_covers_every_noncollapsible_criterion(architecture):
    request, _result = architecture
    expected = set(DHI2011Criterion)

    assert set(request.criteria_priority) == expected
    for candidate in request.candidates:
        assessments = {item.criterion: item for item in candidate.assessments}
        assert set(assessments) == expected
        assert all(item.rationale for item in assessments.values())
        assert all(item.uncertainty for item in assessments.values())
        assert all(item.falsifiable_failure for item in assessments.values())


def test_every_required_depth_dimension_has_a_bound_falsification(architecture):
    request, result = architecture
    probe_ids = {probe.probe_id for probe in request.controlled_probes}
    covered = {
        dimension for mechanism in request.mechanisms for dimension in mechanism.dimensions
    }
    required = set(DHI2011DepthDimension) - {
        DHI2011DepthDimension.CONSTRUCTION_COMPLEXITY_DIAGNOSTIC
    }

    assert set(result.required_dimensions) == required
    assert required.issubset(covered)
    assert result.uncovered_dimensions == ()
    assert all(mechanism.falsification_probe_id in probe_ids for mechanism in request.mechanisms)
    assert all(mechanism.participant_intent_ids for mechanism in request.mechanisms)
    assert all(mechanism.omission_loss for mechanism in request.mechanisms)
    assert all(mechanism.failure_mode for mechanism in request.mechanisms)


def test_layers_and_transitions_form_a_closed_temporal_relational_graph(architecture):
    request, _result = architecture
    layer_ids = {layer.layer_id for layer in request.layers}
    function_ids = {function.function_id for function in request.functions}

    assert request.time_windows == (
        "opening_0s",
        "top_5min",
        "heart_30min",
        "late_heart_2h",
        "drydown_4h",
    )
    assert {layer.layer_id for layer in request.layers} == {
        "layer:lavender-veil",
        "layer:ambrette-pear-talc-membrane",
        "layer:orris-body",
        "layer:amber-vanillic-shadow",
        "layer:cedar-vetiver-counterform",
        "layer:musky-skin-echo",
    }
    assert {transition.transition_id for transition in request.transitions} == {
        "transition:aromatic-fold",
        "transition:membrane-wrap",
        "transition:warmth-underlay",
        "transition:dry-wood-reveal",
        "transition:talc-musk-recurrence",
        "transition:wood-fibre-settling",
    }
    assert all(set(layer.owned_function_ids).issubset(function_ids) for layer in request.layers)
    assert all(transition.source_layer_id in layer_ids for transition in request.transitions)
    assert all(transition.target_layer_id in layer_ids for transition in request.transitions)
    assert all(transition.source_layer_id != transition.target_layer_id for transition in request.transitions)
    assert any("membrane" in transition.relational_mechanism for transition in request.transitions)
    skin_inputs = {
        transition.source_layer_id
        for transition in request.transitions
        if transition.target_layer_id == "layer:musky-skin-echo"
    }
    assert skin_inputs == {
        "layer:ambrette-pear-talc-membrane",
        "layer:cedar-vetiver-counterform",
    }


def test_causal_handoffs_remain_perfumer_inference(architecture):
    request, _result = architecture
    mechanisms = {item.mechanism_id: item for item in request.mechanisms}

    for mechanism_id in {
        "mechanism:ambrette-membrane",
        "mechanism:negative-space",
        "mechanism:temporal-tailoring",
        "mechanism:warmth-under-iris",
        "mechanism:wood-counterform",
        "mechanism:skin-recurrence",
        "mechanism:pear-liquor-continuum",
        "mechanism:powder-textile-cushion",
        "mechanism:seam-continuity",
    }:
        assert mechanisms[mechanism_id].evidence_tier is DHI2011EvidenceTier.PERFUMER_INFERENCE


def test_material_intents_separate_ideal_effect_from_current_proxy(architecture, formula):
    request, _result = architecture
    intents = {intent.intent_id: intent for intent in request.material_intents}
    current_materials = {intent.current_material for intent in intents.values()}

    assert current_materials == set(formula["ingredients_ul"])
    assert len(intents) == 30
    assert len(request.functions) == 18
    assert len(request.mechanisms) == 12
    assert request.formula_binding_ref.endswith("_V3_Smooth.md")
    assert intents["intent:ambrettolide"].ideal_material_or_effect.startswith(
        "Ecuadorian ambrette seed absolute"
    )
    assert intents["intent:ambrettolide"].current_material == "Ambrettolide"
    assert "not ambrette seed absolute" in intents["intent:ambrettolide"].uncertainty
    assert "intent:cocoa" not in intents
    cocoa_arms = {
        arm
        for probe in request.controlled_probes
        if probe.probe_id == "probe:dhi2011:cocoa-shadow"
        for arm in probe.arms
    }
    assert any(arm.startswith("selected zero: 0 uL Cocoa") for arm in cocoa_arms)
    assert "Cocoa Absolute" not in formula["ingredients_ul"]
    assert all(intent.exact_reference_formula_claim is False for intent in intents.values())


def test_every_authority_is_hard_false_and_hashes_are_deterministic(architecture):
    request, result = architecture
    second_request, second_result = build_default_dhi_2011_architecture()

    assert request.record_sha256 == second_request.record_sha256
    assert result.record_sha256 == second_result.record_sha256
    assert result.request_sha256 == request.record_sha256
    for item in fields(DHI2011AuthorityVectorV1):
        assert getattr(request.target.authorities, item.name) is False
        assert getattr(result.authorities, item.name) is False


def test_dhi_named_reference_contract_is_explicit_and_architecture_only(formula, formula_state):
    contract = REFERENCE_CONTRACTS[CONTRACT_ID]
    detection = detect_reference_claim(formula)
    evaluation = evaluate_reference_contract(formula, formula_state)

    assert contract.allowed_scopes == (ARCHITECTURE,)
    assert detection.status == "PASS"
    assert detection.contract_ids == (CONTRACT_ID,)
    assert detection.scope == ARCHITECTURE
    assert evaluation["status"] == "PASS"
    contract_evaluation = evaluation["data"]["evaluations"][0]
    assert contract_evaluation["missing_groups"] == []
    assert set(contract_evaluation["group_metadata"]) == {
        "lavender_opening",
        "iris_or_orris_heart",
        "ambrette_musk_mediator",
        "pear_liqueur_facet",
        "talc_textile_cushion",
        "coumarinic_tonka_shadow",
        "vanillic_amber_shadow",
        "virginia_cedar",
        "vetiver",
    }

    sensory_formula = dict(formula)
    sensory_formula["body"] = formula["body"].replace(
        "**Reference scope:** architecture", "**Reference scope:** sensory_similarity"
    )
    rejected = evaluate_reference_contract(sensory_formula, formula_state)
    assert rejected["status"] == "FAIL"
    assert "cannot authorize sensory_similarity" in rejected["detail"]


def test_each_reference_marker_group_is_individually_required(formula):
    omissions = {
        "lavender_opening": {"Lavender EO High Altitude", "Linalyl Acetate", "Linalool"},
        "iris_or_orris_heart": {
            "Alpha Isomethyl Ionone (Methyl Ionone Pure)",
            "Alpha Ionone",
            "Alpha Irone",
            "Orivone",
            "Dihydro Beta Ionone",
            "Irotyl",
            "Ultralia",
        },
        "ambrette_musk_mediator": {"Ambrettolide"},
        "pear_liqueur_facet": {
            "Ethyl 2-Methylbutyrate",
            "Verdox",
            "Benzyl Acetate",
            "Osmanthus Absolute",
        },
        "talc_textile_cushion": {
            "Ethylene Brassylate",
            "Benzyl Salicylate",
            "Mimosa Absolute",
        },
        "coumarinic_tonka_shadow": {"Tonkarome"},
        "vanillic_amber_shadow": {"Isobutavan"},
        "virginia_cedar": {"Cedarwood oil Virginia"},
        "vetiver": {"Vetiver EO (India)", "Vetival"},
    }
    for expected_missing, removed in omissions.items():
        ingredients = {
            name: amount
            for name, amount in formula["ingredients_ul"].items()
            if name not in removed
        }
        dilutions = {
            name: dilution
            for name, dilution in formula["dilutions"].items()
            if name in ingredients
        }
        state = build_formula_state(ingredients, dilutions, batch_volume_ml=30.0)
        evaluation = evaluate_reference_contract(formula, state)
        assert evaluation["status"] == "FAIL"
        assert expected_missing in evaluation["detail"]


def test_dhi_family_routes_to_iris_woody_knowledge_and_active_archetype(formula):
    assert resolve_family_key("iris_coumarin_amber.dhi2011") == "iris_amber_woody"
    mapped = _map_family("iris_coumarin_amber.dhi2011")
    assert mapped is not None
    assert mapped.value == "woody_amber"

    evaluation = evaluate_family_archetype(formula, "iris_coumarin_amber.dhi2011")
    assert evaluation.status == "PASS"
    assert all(check.status == "PASS" for check in evaluation.checks)


def test_dhi_skeleton_is_exercised_for_the_dotted_archetype(formula_state):
    result = _check_skeleton(
        "dior_homme_intense",
        formula_state,
        ReleaseGateConfig(
            brief="dhi_2011",
            family_archetype="iris_coumarin_amber.dhi2011",
        ),
    )

    assert result.status == "PASS"
    assert result.detail != "not applicable"
    assert (
        "iris + lavender + ambrette_proxy + pear_body + talc_cushion + "
        "coumarinic_shadow + vanillic_shadow + virginia_cedar + vetiver"
        in result.detail
    )
