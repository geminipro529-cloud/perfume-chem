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
    TopologyState,
    evaluate_perceptual_topology,
)
from engine.perception.perfumery_art_topology import (
    ArtShapeWindow,
    ArtTopologyRequest,
    CompositionOperator,
    HierarchyEntry,
    HierarchyRole,
    RatioHypothesis,
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
from engine.scientific_contract import EvidenceDescriptor, ScientificClass
from engine.scientific_validation.complexity_model_admission import OAVGateBinding


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
        target_identity="transparent cedar grain over a creamy root shadow",
        ideal_topology_ref="TARGET/IDEAL:wood-study-v2",
        current_inventory_build_ref="CURRENT-INVENTORY:wood-study-v2",
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


def _art_request(*, oav_binding: OAVGateBinding | None = None) -> ArtTopologyRequest:
    return ArtTopologyRequest(
        core_request=_core_request(oav_binding=oav_binding),
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


def _oav_binding(*, natural_status: str) -> OAVGateBinding:
    return OAVGateBinding(
        formula_sha256="a" * 64,
        dose_receipt_sha256="b" * 64,
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


def _wood_request(
    *,
    prohibited: tuple[WoodProhibitedInference, ...] = (),
    expand_natural: bool = False,
) -> WoodDepthRequest:
    art = evaluate_art_topology(_art_request())
    return WoodDepthRequest(
        art_topology=art,
        wood_layer_id="wood",
        target_configuration=WoodConfiguration.TRANSFORMS_OVER_TIME,
        assignments=(
            WoodFunctionAssignment(
                function_id="grain",
                group=WoodGroup.G16_GRAIN_ROOT,
                is_natural_mixture=True,
                formula_constituent_expansion=expand_natural,
                wood_block_fraction=0.34,
            ),
            WoodFunctionAssignment(
                function_id="cream",
                group=WoodGroup.G17_CREAMY_WOODS,
                wood_block_fraction=0.33,
            ),
            WoodFunctionAssignment(
                function_id="air",
                group=WoodGroup.G18_TRANSPARENT_WOODS,
                wood_block_fraction=0.33,
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


def test_wood_depth_rejects_natural_expansion_and_headspace_as_depth() -> None:
    expanded = evaluate_wood_depth(_wood_request(expand_natural=True))
    headspace = evaluate_wood_depth(
        _wood_request(prohibited=(WoodProhibitedInference.COMPUTED_HEADSPACE_AS_PERCEIVED_DEPTH,))
    )

    assert expanded.state is TopologyState.HOLD
    assert "invented constituent rows" in " ".join(expanded.blockers).lower()
    assert headspace.state is TopologyState.HOLD
    assert "headspace" in " ".join(headspace.blockers).lower()


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
