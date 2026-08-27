from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from engine.perception.complexity_registry import ModuleState, load_complexity_registry
from engine.perception.construction_complexity import analyze_construction_complexity
from engine.perception.perceptual_topology import (
    PerceptualFunction,
    TopologyCoreRequest,
    TopologyLayerContract,
    TopologyMaterialBinding,
    TopologyPortfolioRequest,
    TopologyState,
    evaluate_perceptual_topology,
    evaluate_topology_portfolio,
    project_current_inventory_build,
)
from engine.perception.perfumery_art_topology import (
    ArtEvidenceState,
    ArtShapeWindow,
    ArtTopologyRequest,
    CompositionOperator,
    HierarchyEntry,
    HierarchyRole,
    RatioHypothesis,
    bind_art_temporal_evidence,
    build_art_experiment_plan,
    evaluate_art_topology,
)
from engine.perception.wood_depth import (
    WoodConfiguration,
    WoodDepthRequest,
    WoodFunctionAssignment,
    WoodGroup,
    WoodProhibitedInference,
    evaluate_wood_depth,
)
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.preflight import FormulaDoseLineReceipt, FormulaDoseReceipt
from engine.pipeline.simulator import SimulationFrame
from engine.scientific_contract import EvidenceDescriptor, ScientificClass
from engine.scientific_validation.complexity_model_admission import OAVGateBinding
from engine.sensory.ledger import (
    ObservationCellKey,
    SensoryProtocolScope,
    TemporalEvidenceRequest,
    TemporalEvidenceState,
    TemporalObservationCell,
    analyze_temporal_evidence,
)


@dataclass(frozen=True)
class _Material:
    name: str
    oav: float | None = 1.0
    intensity: float | None = 1.0
    is_known: bool = True
    is_opaque_preblend: bool = False
    functional_groups: tuple[str, ...] = ()


@dataclass(frozen=True)
class _State:
    materials: tuple[_Material, ...]


@dataclass(frozen=True)
class _Frame:
    label: str
    t_seconds: float
    state: _State


def _evidence() -> EvidenceDescriptor:
    return EvidenceDescriptor(
        classification=ScientificClass.HEURISTIC,
        basis="target-linked design hypothesis pending controlled comparison",
        sources=("complex-perfumery:approved-topology-contract",),
        limitations=("no physical sensory observation",),
    )


def _function(
    function_id: str,
    material: str,
    target_function: str,
    *windows: str,
) -> PerceptualFunction:
    return PerceptualFunction(
        function_id=function_id,
        system_or_material=material,
        target_function=target_function,
        loss_if_omitted=f"loss of {target_function}",
        temporal_windows=windows or ("heart", "drydown"),
        texture_axes=("dry", "polished"),
        nonredundancy_evidence=f"{function_id} has a distinct target role",
        evidence=_evidence(),
    )


def _core_request(
    *,
    oav_binding: OAVGateBinding | None = None,
    component_count_used_as_depth: bool = False,
    current_inventory_build_ref: str = "CURRENT-INVENTORY:wood-study-v2",
    target_identity: str = "transparent cedar grain over a creamy root shadow",
) -> TopologyCoreRequest:
    wood = TopologyLayerContract(
        layer_id="wood",
        target_function="dry grain opening into a creamy root residue",
        native_dimensions=("grain", "cream", "root", "air", "shadow"),
        texture_contrasts=("dry:creamy", "rough:polished"),
        failure_modes=("generic woody cloud", "amberwood wall"),
        functions=(
            _function("grain", "Cedarwood EO", "exposed cedar grain", "opening", "heart"),
            _function("cream", "Sandalwood Base", "rounded fiber underside", "heart", "drydown"),
            _function("air", "Iso E Super", "transparent relief", "opening", "heart"),
        ),
    )
    return TopologyCoreRequest(
        target_identity=target_identity,
        ideal_topology_ref="TARGET/IDEAL:wood-study-v2",
        current_inventory_build_ref=current_inventory_build_ref,
        target_recognizers=("cedar grain", "creamy root residue"),
        layers=(wood,),
        oav_binding=oav_binding,
        component_count_used_as_depth=component_count_used_as_depth,
    )


def _construction_profile():
    state = _State(
        (_Material("Cedarwood EO"), _Material("Sandalwood Base"), _Material("Iso E Super"))
    )
    return analyze_construction_complexity(
        state,
        (_Frame("opening", 0.0, state), _Frame("drydown", 28_800.0, state)),
    )


def _shape() -> tuple[ArtShapeWindow, ...]:
    return tuple(
        ArtShapeWindow(
            timepoint=timepoint,
            focus=focus,
            width="narrow" if timepoint in {"0m", "24h"} else "broad",
            density="open",
            edge="crisp" if timepoint == "0m" else "rounded",
            texture=("dry grain", "cream"),
            contrast="dry over creamy",
            shadow="root shadow",
            air="clear relief around cedar",
            tail="recognizable dry cedar residue",
        )
        for timepoint, focus in (
            ("0m", "cedar aperture"),
            ("5m", "cedar recognizer"),
            ("30m", "grain and air"),
            ("2h", "cream enters"),
            ("8h", "root and mineral skeleton"),
            ("24h", "target-specific residue"),
        )
    )


def _art_request(
    *,
    oav_binding: OAVGateBinding | None = None,
    core_request: TopologyCoreRequest | None = None,
) -> ArtTopologyRequest:
    return ArtTopologyRequest(
        core_request=core_request or _core_request(oav_binding=oav_binding),
        construction_profile=_construction_profile(),
        target_shape=_shape(),
        hierarchy=(
            HierarchyEntry("grain", HierarchyRole.SUBJECT),
            HierarchyEntry("air", HierarchyRole.SUPPORT),
            HierarchyEntry("cream", HierarchyRole.RESIDUE),
        ),
        ratio_hypotheses=(
            RatioHypothesis(
                function_a="grain",
                function_b="cream",
                total_active_load_ref="wood-block-active-load-v1",
                evidence=_evidence(),
            ),
        ),
        operators=(
            CompositionOperator.RATIO_SWEEP,
            CompositionOperator.REGISTER_SEPARATION,
            CompositionOperator.TEMPORAL_RELAY,
        ),
    )


def _oav_binding(
    *,
    natural_status: str,
    formula_sha256: str = "a" * 64,
    dose_receipt_sha256: str = "b" * 64,
) -> OAVGateBinding:
    return OAVGateBinding(
        formula_sha256=formula_sha256,
        dose_receipt_sha256=dose_receipt_sha256,
        oav_result_sha256="c" * 64,
        quantitative_ppm_status="PASS",
        odt_authority_status="PASS",
        odt_coverage_status="PASS",
        natural_composite_coverage_status=natural_status,
        headspace_scope_status="PASS",
        receipt_binding_status="BOUND_GATE_RECEIPT",
        strict_oav_status="NOT_COMPUTED",
        pre_mix_gate_status="PASS",
        planned_active_equivalence_status="NOT_APPLICABLE_NEW_FORMULA",
        formula_is_revision=False,
    )


def _dose_receipt(
    amounts: dict[str, float],
    *,
    inventory_bound: bool = True,
) -> FormulaDoseReceipt:
    lines = tuple(
        FormulaDoseLineReceipt(
            material_name=name,
            raw_ul=amount,
            active_ul=amount,
            stock_fraction=1.0,
            fraction_basis="volume_fraction",
            carrier="NEAT",
            stock_id=f"TEST-STOCK-{index}",
            stock_authority="TEST_EXACT_STOCK_FIXTURE",
            inventory_authority="TEST_INVENTORY_SNAPSHOT",
            source_rows=(index,),
            status="BOUND",
        )
        for index, (name, amount) in enumerate(amounts.items(), start=1)
    )
    formula_digest = hashlib.sha256(
        json.dumps(amounts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return FormulaDoseReceipt(
        formula_name="Topology Wood Study",
        formula_input_sha256=formula_digest,
        legacy_formula_hash=formula_digest,
        inventory_snapshot_sha256=hashlib.sha256(b"inventory-snapshot").hexdigest(),
        inventory_source_workbook_sha256=hashlib.sha256(b"inventory-workbook").hexdigest(),
        inventory_authority_sheet="TEST_AUTHORITY_SHEET",
        lines=lines,
        status="BOUND" if inventory_bound else "ABSTAINED",
        reasons=() if inventory_bound else ("inventory authority unresolved",),
    )


def _canonical_current_build(
    amounts: dict[str, float] | None = None,
    *,
    target_identity: str = "transparent cedar grain over a creamy root shadow",
    natural_status: str = "PASS",
    inventory_bound: bool = True,
):
    amounts = amounts or {
        "Cedarwood EO": 34.0,
        "Sandalwood Base": 33.0,
        "Iso E Super": 33.0,
    }
    receipt = _dose_receipt(amounts, inventory_bound=inventory_bound)
    oav_binding = _oav_binding(
        natural_status=natural_status,
        formula_sha256=receipt.formula_input_sha256,
        dose_receipt_sha256=receipt.receipt_sha256,
    )
    core = _core_request(
        oav_binding=oav_binding,
        current_inventory_build_ref=f"CURRENT-INVENTORY:{receipt.receipt_sha256}",
        target_identity=target_identity,
    )
    current_state = build_formula_state(amounts, {name: 1.0 for name in amounts})
    drydown_amounts = {
        "Cedarwood EO": max(amounts["Cedarwood EO"] * 0.20, 0.001),
        "Sandalwood Base": max(amounts["Sandalwood Base"] * 0.70, 0.001),
        "Iso E Super": max(amounts["Iso E Super"] * 0.40, 0.001),
    }
    drydown_state = build_formula_state(
        drydown_amounts,
        {name: 1.0 for name in drydown_amounts},
    )
    projection = project_current_inventory_build(
        core_request=core,
        dose_receipt=receipt,
        formula_state=current_state,
        temporal_frames=(
            SimulationFrame(label="opening", t_seconds=0.0, state=current_state),
            SimulationFrame(label="drydown", t_seconds=14_400.0, state=drydown_state),
        ),
        bindings=(
            TopologyMaterialBinding("Cedarwood EO", "wood", "grain", _evidence()),
            TopologyMaterialBinding("Sandalwood Base", "wood", "cream", _evidence()),
            TopologyMaterialBinding("Iso E Super", "wood", "air", _evidence()),
        ),
    )
    return receipt, core, projection


def test_universal_core_is_target_first_sparse_and_nonempirical() -> None:
    result = evaluate_perceptual_topology(_core_request())
    payload = result.as_dict()

    assert result.state is TopologyState.DESIGN_READY_NOT_EMPIRICAL
    assert payload["target_identity"].startswith("transparent cedar")
    assert payload["ideal_topology_ref"].startswith("TARGET/IDEAL:")
    assert payload["current_inventory_build_ref"].startswith("CURRENT-INVENTORY:")
    assert payload["contract"]["complexity_rule"]["component_count_is_depth"] is False
    assert payload["contract"]["spatial_boundary"]["literal_3d_internal_space"] == (
        "CREATIVE_SHORTHAND_ONLY"
    )
    assert payload["empirical_pass"] is False
    assert payload["formula_mutation_authorized"] is False
    assert payload["final_integrator"] == (
        "SOL_5_6_XHIGH_UNTIL_BLINDED_BENCHMARK_PROVES_REPLACEMENT"
    )
    assert "overall_score" not in json.dumps(payload, sort_keys=True)


def test_universal_core_holds_count_based_complexity_without_collapsing_layers() -> None:
    result = evaluate_perceptual_topology(_core_request(component_count_used_as_depth=True))

    assert result.state is TopologyState.HOLD
    assert "component count" in " ".join(result.blockers).lower()
    assert result.layer_ids == ("wood",)


def test_art_topology_composes_existing_profile_and_keeps_sol_final() -> None:
    result = evaluate_art_topology(_art_request())
    payload = result.as_dict()

    assert result.state is TopologyState.DESIGN_READY_NOT_EMPIRICAL
    assert payload["construction_profile_schema_version"] == ("construction_complexity_profile_v1")
    assert payload["final_integrator"] == (
        "SOL_5_6_XHIGH_UNTIL_BLINDED_BENCHMARK_PROVES_REPLACEMENT"
    )
    assert payload["mandatory_tests"]["binary_ratio"]["ratios"] == [
        "9:1",
        "7:3",
        "5:5",
        "3:7",
        "1:9",
    ]
    assert payload["physical_truth"] == "NOT_TESTED"
    assert payload["sensory_similarity_authority"] is False
    assert payload["final_acceptance_authority"] is False
    assert payload["final_formula_authority"] is False
    serialized = json.dumps(payload, sort_keys=True)
    assert "overall_beauty_score" not in serialized
    assert "percent_perceived_contribution" not in serialized


def test_oav_natural_composite_gate_is_diagnostic_not_art_authority() -> None:
    held = evaluate_art_topology(
        _art_request(oav_binding=_oav_binding(natural_status="HOLD_MONOMOLECULAR_NATURAL"))
    ).as_dict()
    ready = evaluate_art_topology(
        _art_request(oav_binding=_oav_binding(natural_status="PASS"))
    ).as_dict()

    assert held["state"] == "DESIGN_READY_NOT_EMPIRICAL"
    assert held["oav_firewall"]["state"] == "HOLD"
    assert held["oav_firewall"]["experiment_selection_authorized"] is False
    assert ready["oav_firewall"]["state"] == "SCREEN_READY"
    assert ready["oav_firewall"]["experiment_selection_authorized"] is True
    for payload in (held, ready):
        assert payload["oav_firewall"]["beauty_authority"] is False
        assert payload["oav_firewall"]["sensory_contribution_authority"] is False
        assert payload["empirical_pass"] is False


def test_current_build_projection_is_receipt_bound_and_uses_canonical_active_amounts() -> None:
    receipt, _core, projection = _canonical_current_build()
    payload = projection.as_dict()

    assert projection.state is TopologyState.DESIGN_READY_NOT_EMPIRICAL
    assert payload["dose_receipt_sha256"] == receipt.receipt_sha256
    assert payload["inventory_authority"]["status"] == "BOUND"
    assert payload["material_active_ul"] == {
        "Cedarwood EO": 34.0,
        "Iso E Super": 33.0,
        "Sandalwood Base": 33.0,
    }
    assert payload["function_active_ul"] == {
        "air": 33.0,
        "cream": 33.0,
        "grain": 34.0,
    }
    assert payload["layer_active_ul"] == {"wood": 100.0}
    assert payload["formula_identity_policy"] == (
        "ONE_CANONICAL_RECEIPT_ROW_PER_MATERIAL_NO_NATURAL_CONSTITUENT_EXPANSION"
    )
    assert payload["perceptual_contribution_authority"] is False
    assert payload["physical_execution_authorized"] is False
    serialized = json.dumps(payload, sort_keys=True)
    assert "percent_perceived_contribution" not in serialized
    assert "overall_score" not in serialized


def test_current_build_projection_fails_closed_without_inventory_authority() -> None:
    _receipt, _core, projection = _canonical_current_build(inventory_bound=False)

    assert projection.state is TopologyState.HOLD
    assert "inventory" in " ".join(projection.blockers).lower()
    assert projection.as_dict()["formula_mutation_authorized"] is False


def test_portfolio_diagnostic_detects_concentration_only_target_collapse() -> None:
    _receipt_a, _core_a, projection_a = _canonical_current_build(
        target_identity="transparent cedar grain over a creamy root shadow"
    )
    _receipt_b, _core_b, projection_b = _canonical_current_build(
        {
            "Cedarwood EO": 68.0,
            "Sandalwood Base": 66.0,
            "Iso E Super": 66.0,
        },
        target_identity="mineral vetiver roots under cold smoke",
    )
    result = evaluate_topology_portfolio(
        TopologyPortfolioRequest((projection_a, projection_b))
    )
    payload = result.as_dict()

    assert result.state is TopologyState.HOLD
    diagnostic = payload["pair_diagnostics"][0]
    assert "CONCENTRATION_ONLY_SIBLINGS" in diagnostic["flags"]
    assert "TARGET_IDENTITY_COLLAPSE" in diagnostic["flags"]
    assert diagnostic["full_formula_cosine_similarity"] == 1.0
    assert payload["diagnostic_only"] is True
    assert payload["empirical_pass"] is False
    assert payload["sensory_similarity_authority"] is False
    assert "overall_score" not in json.dumps(payload, sort_keys=True)


def test_art_experiment_plan_emits_numeric_matched_load_arms_and_reuses_order_balance() -> None:
    _receipt, core, projection = _canonical_current_build()
    art = evaluate_art_topology(_art_request(core_request=core))
    plan = build_art_experiment_plan(
        art_topology=art,
        current_build=projection,
        protocol_id="wood-topology-controlled-comparison-v1",
    )
    payload = plan.as_dict()

    assert plan.state is TopologyState.DESIGN_READY_NOT_EMPIRICAL
    ratio_block = plan.block_by_id("ratio:grain:cream")
    assert len(ratio_block.arms) == 5
    nine_to_one = ratio_block.arms[0]
    amounts = dict(nine_to_one.function_active_ul)
    assert amounts["grain"] == 60.3
    assert amounts["cream"] == 6.7
    assert sum(amounts.values()) == 100.0
    assert ratio_block.schedule.method == "WILLIAMS_FIRST_ORDER_BALANCED"
    assert ratio_block.schedule.random_assignment_authorized is False

    ablation = plan.block_by_id("ablation:all-functions")
    minus_grain = next(arm for arm in ablation.arms if arm.arm_id.endswith("minus:grain"))
    assert dict(minus_grain.function_active_ul)["grain"] == 0.0
    assert minus_grain.neutral_carrier_replacement_ul == 34.0

    perturb = plan.block_by_id("perturbation:grain")
    assert [arm.perturbation_percent for arm in perturb.arms] == [
        -30,
        -20,
        -10,
        0,
        10,
        20,
        30,
    ]
    assert all(sum(dict(arm.function_active_ul).values()) == 100.0 for arm in perturb.arms)
    assert payload["oav_role"] == "EXPERIMENT_SELECTION_FIREWALL_ONLY"
    assert payload["formula_mutation_authorized"] is False
    assert payload["physical_execution_authorized"] is False
    assert payload["sensory_authority"] is False


def test_art_experiment_plan_holds_when_natural_oav_firewall_is_not_ready() -> None:
    _receipt, core, projection = _canonical_current_build(
        natural_status="HOLD_MONOMOLECULAR_NATURAL"
    )
    art = evaluate_art_topology(_art_request(core_request=core))
    plan = build_art_experiment_plan(
        art_topology=art,
        current_build=projection,
        protocol_id="wood-topology-controlled-comparison-v1",
    )

    assert plan.state is TopologyState.HOLD
    assert plan.blocks == ()
    assert "natural_composite_coverage_status" in " ".join(plan.blockers)


def test_art_observations_bind_to_existing_temporal_ledger_without_creating_a_pass() -> None:
    _receipt, core, projection = _canonical_current_build()
    art = evaluate_art_topology(_art_request(core_request=core))
    plan = build_art_experiment_plan(
        art_topology=art,
        current_build=projection,
        protocol_id="wood-topology-controlled-comparison-v1",
    )
    block = plan.block_by_id("ratio:grain:cream")
    sample_ids = tuple(arm.arm_id for arm in block.arms)
    timepoints = (0.0, 300.0, 1_800.0, 7_200.0, 28_800.0, 86_400.0)
    assessor_ids = tuple(
        f"assessor-{index}"
        for index in range(1, len(block.schedule.sequences) + 1)
    )
    scope = SensoryProtocolScope(
        protocol_id=block.protocol_id,
        sample_ids=sample_ids,
        assessor_ids=assessor_ids,
        repeat_ids=("repeat-1",),
        timepoints_seconds=timepoints,
        endpoint_ids=("target_fidelity",),
        schedule_sha256=block.schedule.schedule_sha256,
    )
    cells = tuple(
        TemporalObservationCell(
            key=ObservationCellKey(
                protocol_id=block.protocol_id,
                sample_id=sample_id,
                assessor_id=assessor_id,
                repeat_id="repeat-1",
                time_seconds=timepoint,
                endpoint_id="target_fidelity",
            ),
            observation_id=(
                f"obs-{assessor_index}-{sample_index}-{time_index}"
            ),
            value=float(sample_index),
            presentation_sequence_id=f"sequence-{assessor_index}",
            presentation_position=sequence.index(sample_id) + 1,
        )
        for assessor_index, (assessor_id, sequence) in enumerate(
            zip(assessor_ids, block.schedule.sequences, strict=True),
            start=1,
        )
        for sample_index, sample_id in enumerate(sample_ids, start=1)
        for time_index, timepoint in enumerate(timepoints, start=1)
    )
    temporal = analyze_temporal_evidence(
        TemporalEvidenceRequest(scope=scope, schedule=block.schedule, cells=cells)
    )
    bound = bind_art_temporal_evidence(
        plan=plan,
        block_id=block.block_id,
        evidence=temporal,
    )
    payload = bound.as_dict()

    assert temporal.state is TemporalEvidenceState.COMPLETE
    assert bound.state is ArtEvidenceState.OBSERVATIONS_BOUND_NOT_ACCEPTED
    assert payload["empirical_pass"] is False
    assert payload["final_formula_authority"] is False
    assert payload["sensory_authority"] is False
    assert payload["final_integrator"] == (
        "SOL_5_6_XHIGH_UNTIL_BLINDED_BENCHMARK_PROVES_REPLACEMENT"
    )


def _wood_request(
    *,
    prohibited: tuple[WoodProhibitedInference, ...] = (),
    amounts: dict[str, float] | None = None,
    dominance_evidence: bool = False,
) -> WoodDepthRequest:
    _receipt, core, projection = _canonical_current_build(amounts)
    art = evaluate_art_topology(_art_request(core_request=core))
    return WoodDepthRequest(
        art_topology=art,
        current_build=projection,
        wood_layer_id="wood",
        target_configuration=WoodConfiguration.TRANSFORMS_OVER_TIME,
        assignments=(
            WoodFunctionAssignment(
                function_id="grain",
                group=WoodGroup.G16_GRAIN_ROOT,
                target_evidence_for_dominance=(
                    _evidence() if dominance_evidence else None
                ),
            ),
            WoodFunctionAssignment(
                function_id="cream",
                group=WoodGroup.G17_CREAMY_WOODS,
            ),
            WoodFunctionAssignment(
                function_id="air",
                group=WoodGroup.G18_TRANSPARENT_WOODS,
            ),
        ),
        prohibited_inferences=prohibited,
    )


def test_wood_depth_v2_uses_art_core_and_emits_no_sensory_pass() -> None:
    result = evaluate_wood_depth(_wood_request())
    payload = result.as_dict()

    assert result.state is TopologyState.DESIGN_READY_NOT_EMPIRICAL
    assert payload["inherits"] == [
        "UNIVERSAL_PERCEPTUAL_TOPOLOGY_CORE",
        "PERFUMERY_ART_COMPOSITION_TOPOLOGY_V1",
        "CONSTRUCTION_COMPLEXITY_PROFILE_V1",
    ]
    assert list(payload["dimensions"]) == [
        "grain_integrity",
        "texture_contrast",
        "configural_balance",
        "salience_depth",
        "temporal_transformation",
        "structural_air_shadow",
        "late_identity",
        "wood_cloud_collapse_risk",
    ]
    assert payload["causal_tests"]["temporal_profile"]["minimum_times"] == [
        "0m",
        "5m",
        "30m",
        "2h",
        "8h",
        "24h",
    ]
    assert payload["empirical_pass"] is False
    assert payload["physical_depth_authority"] is False
    assert payload["predicted_liking_authority"] is False
    assert payload["assignments"][0]["computed_wood_block_fraction"] == 0.34
    assert payload["assignments"][0]["fraction_source"] == (
        "CANONICAL_FORMULA_STATE_BOUND_TO_DOSE_RECEIPT"
    )
    assert payload["dominance_review_threshold"]["authority"].endswith("NOT_SENSORY")


def test_wood_depth_rejects_headspace_as_depth_and_computed_unsupported_dominance() -> None:
    headspace = evaluate_wood_depth(
        _wood_request(prohibited=(WoodProhibitedInference.COMPUTED_HEADSPACE_AS_PERCEIVED_DEPTH,))
    )
    dominated = evaluate_wood_depth(
        _wood_request(
            amounts={
                "Cedarwood EO": 60.0,
                "Sandalwood Base": 20.0,
                "Iso E Super": 20.0,
            }
        )
    )
    supported = evaluate_wood_depth(
        _wood_request(
            amounts={
                "Cedarwood EO": 60.0,
                "Sandalwood Base": 20.0,
                "Iso E Super": 20.0,
            },
            dominance_evidence=True,
        )
    )

    assert headspace.state is TopologyState.HOLD
    assert "headspace" in " ".join(headspace.blockers).lower()
    assert dominated.state is TopologyState.HOLD
    assert "computed wood-block dominance" in " ".join(dominated.blockers).lower()
    assert supported.state is TopologyState.DESIGN_READY_NOT_EMPIRICAL


def test_topology_modules_are_hash_bound_and_nonruntime_until_benchmark() -> None:
    root = Path(__file__).resolve().parents[1]
    registry = load_complexity_registry(
        root,
        root / "configs/complexity/complexity_module_registry_v2.json",
    )
    expected = {
        "universal-perceptual-topology-core": Path("engine/perception/perceptual_topology.py"),
        "perfumery-art-composition-topology-v1": Path(
            "engine/perception/perfumery_art_topology.py"
        ),
        "wood-depth-model-v2": Path("engine/perception/wood_depth.py"),
    }

    for module_id, relative_path in expected.items():
        module = registry.module_by_id(module_id)
        assert module.state is ModuleState.FUTURE_CANDIDATE_NOT_VALIDATED
        assert module.import_path is None
        assert module.runtime_eligible is False
        assert module.sha256 == hashlib.sha256((root / relative_path).read_bytes()).hexdigest()

    assert {module.module_id for module in registry.modules if module.runtime_eligible} == {
        "complexity-experimental-design"
    }
