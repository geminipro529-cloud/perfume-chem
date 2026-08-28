from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.inventory.authority import (
    InventoryAuthorityProjection,
    InventoryAvailabilityState,
    StockDefinition,
    StockFractionBasis,
)
from engine.perception.architectural_delta import (
    ArchitecturalDeltaCandidate,
    ArchitecturalDeltaFamily,
    ArchitecturalDeltaKind,
    ArchitecturalDeltaRequest,
    ArchitecturalDeltaState,
    evaluate_architectural_delta,
)
from engine.perception.architecture_compiler import compile_architecture
from engine.perception.architecture_contracts import (
    ArchitectureCompilationState,
    ArchitectureCompileRequest,
    ArchitectureLayerContract,
    ArchitectureMaterialHypothesis,
    ArchitectureStrategyAssignment,
    ArchitectureStrategyId,
    ArchitectureTransitionContract,
    TargetFunctionContract,
)
from engine.perception.architecture_rule_registry import (
    load_default_architecture_registries,
)
from engine.perception.complexity_inventory import (
    InventoryAvailability,
    StockReadiness,
)

ROOT = Path(__file__).parents[1]


class _InventorySnapshot:
    workbook_sha256 = "a" * 64
    overlay_sha256 = "b" * 64
    workbook_record_count = 280
    alias_record_count = 45

    def __init__(self, *, exact_stock: bool = True) -> None:
        self.exact_stock = exact_stock

    def project(self, material: str) -> InventoryAuthorityProjection:
        if material == "Missing Specialist":
            return InventoryAuthorityProjection(
                requested_name=material,
                canonical_name=material,
                state=InventoryAvailabilityState.UNLISTED,
                stock=None,
                exact_stock_ref=None,
                physical_execution_ready=False,
                active_equivalence_ready=False,
                molecular_mechanism_authority=False,
                formula_rebase_authorized=False,
                general_substitution_authorized=False,
                source_rows=(),
                status="UNLISTED",
                note=None,
            )
        stock = StockDefinition(
            fraction=Decimal("1"),
            fraction_basis=StockFractionBasis.NEAT,
            carrier=None,
            fraction_authority="TEST EXACT STOCK",
            execution_ready=True,
        )
        return InventoryAuthorityProjection(
            requested_name=material,
            canonical_name=material,
            state=InventoryAvailabilityState.OWNED,
            stock=stock,
            exact_stock_ref=(
                f"stock:{material.casefold().replace(' ', '-')}:lot-1"
                if self.exact_stock
                else None
            ),
            physical_execution_ready=self.exact_stock,
            active_equivalence_ready=self.exact_stock,
            molecular_mechanism_authority=False,
            formula_rebase_authorized=False,
            general_substitution_authorized=False,
            source_rows=(100,),
            status="HAVE - NEAT",
            note="Synthetic exact-stock fixture.",
        )


def _function(
    function_id: str,
    description: str,
    omission_loss: str,
) -> TargetFunctionContract:
    return TargetFunctionContract(
        function_id=function_id,
        description=description,
        target_link=f"Required by the target's {description}.",
        omission_loss=omission_loss,
        success_observable=f"Blinded assessors identify {description} without identity drift.",
        failure_observable=f"The {description} collapses or masks the recognizer.",
        evidence_refs=(f"target:{function_id}",),
    )


def _candidate(material: str = "Habanolide") -> ArchitecturalDeltaCandidate:
    return ArchitecturalDeltaCandidate(
        candidate_id="DELTA-DEPTH-BRIDGE",
        material=material,
        family=ArchitecturalDeltaFamily.MUSK,
        kind=ArchitecturalDeltaKind.RATIO,
        priority_rank=1,
        target_role="test whether the bridge preserves dark-to-radiant depth",
        nonredundancy_evidence="The bridge owns the transition, not either endpoint.",
        loss_if_omitted="The dark and radiant states become adjacent rather than connected.",
        failure_mode="Too much bridge turns the contrast into a clean musk cloud.",
        controlled_arms=("baseline-constant-total", "bridge-ratio-constant-total"),
        evidence_refs=("target:transition", "design:isolated-ratio"),
    )


def _request(
    *,
    primary: ArchitectureStrategyId = ArchitectureStrategyId.CHIAROSCURO_DUAL_STATE,
    secondary: tuple[ArchitectureStrategyAssignment, ...] | None = None,
    candidates: tuple[ArchitecturalDeltaCandidate, ...] | None = None,
    component_count_used_as_complexity: bool = False,
    predicted_oav_used_as_perception: bool = False,
    composition_score_used_as_hedonic: bool = False,
) -> ArchitectureCompileRequest:
    functions = (
        _function("DARK_CORE", "dense shadowed core", "The target loses its dark gravity."),
        _function(
            "RADIANT_COUNTERFORM",
            "radiant counterform",
            "The target becomes a monolithic dark block.",
        ),
        _function(
            "TACTILE_BRIDGE",
            "tactile transition",
            "The two states no longer read as one architecture.",
        ),
    )
    primary_assignment = ArchitectureStrategyAssignment(
        strategy_id=primary,
        owns_function_ids=("DARK_CORE", "RADIANT_COUNTERFORM"),
        rationale="The target is defined by simultaneous shadow and radiance.",
    )
    if secondary is None:
        secondary = (
            ArchitectureStrategyAssignment(
                strategy_id=ArchitectureStrategyId.MATERIAL_TEXTURE,
                owns_function_ids=("TACTILE_BRIDGE",),
                rationale="Texture connects the two states without adding another subject.",
            ),
        )
    return ArchitectureCompileRequest(
        target_identity="Iris leather chiaroscuro with carved woody depth",
        target_reference="DHP-STRUCTURAL-GRAMMAR-NOT-A-CLONE",
        family_adapter_id="IRIS_WOODY_LEATHER",
        target_recognizers=("orris silhouette", "leather shadow", "carved wood"),
        target_invariants=(
            "orris remains the recognizer",
            "darkness remains textural rather than sugary",
        ),
        forbidden_drift=("generic amberwood wall", "laundry musk takeover"),
        ideal_formula_ref="formula:dhp-grammar:ideal:v1",
        current_inventory_build_ref="formula:dhp-grammar:current:v1",
        formula_lineage_sha256="1" * 64,
        primary_strategy=primary_assignment,
        secondary_strategies=secondary,
        functions=functions,
        layers=(
            ArchitectureLayerContract(
                layer_id="SHADOW",
                temporal_position="opening through drydown",
                spatial_position="near-field core",
                texture="dense, matte, carved",
                function_ids=("DARK_CORE",),
            ),
            ArchitectureLayerContract(
                layer_id="COUNTERFORM",
                temporal_position="heart through drydown",
                spatial_position="radiant field around core",
                texture="luminous and dry",
                function_ids=("RADIANT_COUNTERFORM",),
            ),
            ArchitectureLayerContract(
                layer_id="BRIDGE",
                temporal_position="heart transition",
                spatial_position="between core and field",
                texture="tactile continuity",
                function_ids=("TACTILE_BRIDGE",),
            ),
        ),
        transitions=(
            ArchitectureTransitionContract(
                transition_id="SHADOW-TO-FIELD",
                from_layer_id="SHADOW",
                to_layer_id="COUNTERFORM",
                relation="controlled simultaneous contrast",
                intended_effect="The radiant state reveals the depth of the shadow.",
                failure_mode="Either side masks the other or they separate into two perfumes.",
                evidence_refs=("target:transition",),
            ),
        ),
        material_hypotheses=(
            ArchitectureMaterialHypothesis(
                material_name="Habanolide",
                function_id="TACTILE_BRIDGE",
                role="radiant dry bridge candidate",
                ideal_status="OPTIONAL_TEST_CANDIDATE",
                current_build_intent=True,
                evidence_refs=("inventory:v5", "target:transition"),
            ),
        ),
        delta_candidates=candidates if candidates is not None else (_candidate(),),
        no_change_reason="No target-linked delta remains after isolated comparisons.",
        evidence_refs=("brief:locked", "protocol:constant-total"),
        component_count_used_as_complexity=component_count_used_as_complexity,
        predicted_oav_used_as_perception=predicted_oav_used_as_perception,
        composition_score_used_as_hedonic=composition_score_used_as_hedonic,
    )


def test_registry_contains_eight_nonranked_architectural_strategies() -> None:
    rules, strategies = load_default_architecture_registries(ROOT)

    assert set(strategies.strategy_ids) == {item.value for item in ArchitectureStrategyId}
    assert len(strategies.strategy_ids) == 8
    assert rules.ingredient_count_is_complexity is False
    assert rules.composition_score_has_hedonic_authority is False
    for strategy_id in strategies.strategy_ids:
        strategy = strategies.get(strategy_id)
        assert strategy.perceptual_depth_mechanisms
        assert strategy.failure_modes
        assert strategy.causal_probe_types
        assert strategy.strategy_score is None


def test_compiler_treats_dhp_chiaroscuro_as_one_strategy_and_proposes_one_delta() -> None:
    result = compile_architecture(_request(), _InventorySnapshot())

    assert result.state is ArchitectureCompilationState.EXPERIMENT_PROPOSED
    assert result.primary_strategy is ArchitectureStrategyId.CHIAROSCURO_DUAL_STATE
    assert result.secondary_strategies == (ArchitectureStrategyId.MATERIAL_TEXTURE,)
    assert result.delta_result.state is ArchitecturalDeltaState.PROPOSED
    assert result.delta_result.selected_candidate.candidate_id == "DELTA-DEPTH-BRIDGE"
    assert len(result.material_bindings) == 1
    assert result.material_bindings[0].exact_stock_ref.endswith(":lot-1")
    assert result.blockers == ()
    assert all(value is False for value in result.authority_flags.values())


def test_non_dhp_spatial_architecture_is_not_forced_into_chiaroscuro() -> None:
    spatial_primary = ArchitectureStrategyAssignment(
        strategy_id=ArchitectureStrategyId.SPATIAL_FIELD,
        owns_function_ids=("DARK_CORE", "RADIANT_COUNTERFORM"),
        rationale="The target is a near/far field, not a dark/light opposition.",
    )
    request = replace(
        _request(primary=ArchitectureStrategyId.SPATIAL_FIELD),
        target_identity="Transparent mineral air with a remote floral horizon",
        primary_strategy=spatial_primary,
    )

    result = compile_architecture(request, _InventorySnapshot())

    assert result.state is ArchitectureCompilationState.EXPERIMENT_PROPOSED
    assert result.primary_strategy is ArchitectureStrategyId.SPATIAL_FIELD
    assert "CHIAROSCURO" not in result.applied_strategy_ids


def test_secondary_strategy_overlap_holds_instead_of_double_counting_depth() -> None:
    overlapping = (
        ArchitectureStrategyAssignment(
            strategy_id=ArchitectureStrategyId.MATERIAL_TEXTURE,
            owns_function_ids=("TACTILE_BRIDGE",),
            rationale="Texture owns the bridge.",
        ),
        ArchitectureStrategyAssignment(
            strategy_id=ArchitectureStrategyId.TEMPORAL_METAMORPHOSIS,
            owns_function_ids=("TACTILE_BRIDGE",),
            rationale="Temporal change also claims the same bridge.",
        ),
    )

    result = compile_architecture(
        _request(secondary=overlapping),
        _InventorySnapshot(),
    )

    assert result.state is ArchitectureCompilationState.HOLD
    assert any("owned by multiple strategies" in blocker for blocker in result.blockers)
    assert result.delta_result is None


@pytest.mark.parametrize(
    "field_name",
    (
        "component_count_used_as_complexity",
        "predicted_oav_used_as_perception",
        "composition_score_used_as_hedonic",
    ),
)
def test_false_complexity_or_hedonic_shortcuts_hold(field_name: str) -> None:
    result = compile_architecture(
        _request(**{field_name: True}),
        _InventorySnapshot(),
    )

    assert result.state is ArchitectureCompilationState.HOLD
    assert result.delta_result is None
    assert any(field_name in blocker for blocker in result.blockers)


def test_missing_exact_stock_holds_physical_build_without_changing_ideal() -> None:
    request = _request()
    result = compile_architecture(request, _InventorySnapshot(exact_stock=False))

    assert result.state is ArchitectureCompilationState.EXPERIMENT_PROPOSED
    assert result.ideal_formula_ref == request.ideal_formula_ref
    assert result.current_inventory_build_ref == request.current_inventory_build_ref
    assert any("ExactStockRef" in blocker for blocker in result.current_build_blockers)
    assert result.delta_result.physical_execution_authorized is False


def test_minimal_precision_can_emit_no_change_without_material_count_reward() -> None:
    request = _request(
        primary=ArchitectureStrategyId.MINIMAL_PRECISION,
        secondary=(),
        candidates=(),
    )
    request = replace(
        request,
        primary_strategy=ArchitectureStrategyAssignment(
            strategy_id=ArchitectureStrategyId.MINIMAL_PRECISION,
            owns_function_ids=("DARK_CORE", "RADIANT_COUNTERFORM", "TACTILE_BRIDGE"),
            rationale="Every function is already carried by the smallest exact structure.",
        ),
    )

    result = compile_architecture(request, _InventorySnapshot())

    assert result.state is ArchitectureCompilationState.NO_CHANGE
    assert result.delta_result.state is ArchitecturalDeltaState.NO_CHANGE
    assert result.next_action == "NO_CHANGE"


def test_target_lock_and_compilation_hashes_are_repeatable() -> None:
    request = _request()

    first = compile_architecture(request, _InventorySnapshot())
    second = compile_architecture(request, _InventorySnapshot())

    assert first.target_lock_sha256 == sha256_hex(
        canonical_json_bytes(request.target_lock_payload())
    )
    assert first.compilation_sha256 == second.compilation_sha256
    assert first.rule_registry_sha256 == second.rule_registry_sha256
    assert first.strategy_registry_sha256 == second.strategy_registry_sha256
    assert first.family_adapter_applied_after_target_lock is True
    assert first.inventory_workbook_record_count == 280
    assert first.inventory_alias_record_count == 45


def test_incomplete_function_ownership_holds() -> None:
    request = replace(
        _request(secondary=()),
        primary_strategy=ArchitectureStrategyAssignment(
            strategy_id=ArchitectureStrategyId.CHIAROSCURO_DUAL_STATE,
            owns_function_ids=("DARK_CORE", "RADIANT_COUNTERFORM"),
            rationale="The bridge was accidentally left unowned.",
        ),
    )

    result = compile_architecture(request, _InventorySnapshot())

    assert result.state is ArchitectureCompilationState.HOLD
    assert any(
        "function TACTILE_BRIDGE is not owned" in blocker
        for blocker in result.blockers
    )


def test_duplicate_layer_placement_and_unknown_transition_hold() -> None:
    request = _request()
    duplicate_layer = ArchitectureLayerContract(
        layer_id="DUPLICATE-BRIDGE",
        temporal_position="heart",
        spatial_position="near-field core",
        texture="duplicate placement",
        function_ids=("TACTILE_BRIDGE",),
    )
    bad_transition = ArchitectureTransitionContract(
        transition_id="UNKNOWN-DESTINATION",
        from_layer_id="SHADOW",
        to_layer_id="NOT-A-LAYER",
        relation="invalid edge",
        intended_effect="This should never compile.",
        failure_mode="The graph contains an unbound endpoint.",
        evidence_refs=("test:invalid-transition",),
    )
    request = replace(
        request,
        layers=(*request.layers, duplicate_layer),
        transitions=(*request.transitions, bad_transition),
    )

    result = compile_architecture(request, _InventorySnapshot())

    assert result.state is ArchitectureCompilationState.HOLD
    assert any("placed in multiple layers" in blocker for blocker in result.blockers)
    assert any("unknown to-layer" in blocker for blocker in result.blockers)


def test_incompatible_secondary_strategy_holds() -> None:
    request = _request(
        secondary=(
            ArchitectureStrategyAssignment(
                strategy_id=ArchitectureStrategyId.POLYPHONIC_COUNTERPOINT,
                owns_function_ids=("TACTILE_BRIDGE",),
                rationale="An independent voice is not part of this target.",
            ),
        )
    )

    result = compile_architecture(request, _InventorySnapshot())

    assert result.state is ArchitectureCompilationState.HOLD
    assert any("not declared compatible" in blocker for blocker in result.blockers)


@pytest.mark.parametrize(
    ("state", "expected_availability", "expected_readiness"),
    (
        (
            InventoryAvailabilityState.OWNED,
            InventoryAvailability.OWNED,
            StockReadiness.STOCK_DETAIL_OPEN,
        ),
        (
            InventoryAvailabilityState.UNAVAILABLE,
            InventoryAvailability.OUT_OF_STOCK,
            StockReadiness.NOT_BUILDABLE,
        ),
        (
            InventoryAvailabilityState.PLANNED_ACQUISITION,
            InventoryAvailability.PLANNED_ACQUISITION,
            StockReadiness.PROCUREMENT_PENDING,
        ),
        (
            InventoryAvailabilityState.PREPARABLE,
            InventoryAvailability.PREPARABLE_NOT_MIXED,
            StockReadiness.PREPARATION_REQUIRED,
        ),
        (
            InventoryAvailabilityState.VERIFY,
            InventoryAvailability.VERIFY_FIRST,
            StockReadiness.STOCK_DETAIL_OPEN,
        ),
        (
            InventoryAvailabilityState.FORBIDDEN,
            InventoryAvailability.FORBIDDEN,
            StockReadiness.NOT_BUILDABLE,
        ),
        (
            InventoryAvailabilityState.UNLISTED,
            InventoryAvailability.UNLISTED,
            StockReadiness.NOT_BUILDABLE,
        ),
    ),
)
def test_architectural_delta_maps_every_joined_inventory_state_without_authority(
    state: InventoryAvailabilityState,
    expected_availability: InventoryAvailability,
    expected_readiness: StockReadiness,
) -> None:
    class _StateSnapshot:
        workbook_sha256 = "a" * 64
        overlay_sha256 = "b" * 64
        workbook_record_count = 280

        def project(self, material: str) -> InventoryAuthorityProjection:
            return InventoryAuthorityProjection(
                requested_name=material,
                canonical_name=material,
                state=state,
                stock=None,
                exact_stock_ref=None,
                physical_execution_ready=False,
                active_equivalence_ready=False,
                molecular_mechanism_authority=False,
                formula_rebase_authorized=False,
                general_substitution_authorized=False,
                source_rows=(88,),
                status=state.value,
                note="Joined-authority mapping fixture.",
            )

    request = ArchitecturalDeltaRequest(
        target_identity="Joined inventory projection test",
        ideal_formula_ref="formula:test:ideal",
        current_build_ref="formula:test:current",
        formula_lineage_sha256="4" * 64,
        candidates=(_candidate(),),
        no_change_reason="The fixture always has a candidate.",
    )

    result = evaluate_architectural_delta(
        request,
        inventory_snapshot=_StateSnapshot(),
    )

    assert result.state is ArchitecturalDeltaState.PROPOSED
    assert result.inventory_projection.availability is expected_availability
    assert result.inventory_projection.stock_readiness is expected_readiness
    assert result.physical_execution_authorized is False
