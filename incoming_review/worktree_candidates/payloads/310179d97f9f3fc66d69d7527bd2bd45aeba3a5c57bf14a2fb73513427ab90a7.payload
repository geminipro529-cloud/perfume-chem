"""Compile a locked perfume target into one relational experiment design.

The compiler is intentionally conservative.  It validates function ownership,
layer coverage, transitions, strategy compatibility, and inventory projection;
then it delegates only zero-or-one intervention selection to Architectural
Delta.  It never predicts that the architecture will be perceived or liked.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.perception.architectural_delta import (
    ArchitecturalDeltaRequest,
    ArchitecturalDeltaResult,
    ArchitecturalDeltaState,
    evaluate_architectural_delta,
)
from engine.perception.architecture_contracts import (
    ArchitectureCompilationState,
    ArchitectureCompileRequest,
    ArchitectureMaterialHypothesis,
    ArchitectureStrategyAssignment,
    ArchitectureStrategyId,
)
from engine.perception.architecture_rule_registry import (
    ArchitectureStrategyRegistry,
    PerfumeryRuleRegistry,
    load_default_architecture_registries,
)

_REPOSITORY_ROOT = Path(__file__).parents[2]
_AUTHORITY_FLAGS = MappingProxyType(
    {
        "formula_mutation_authorized": False,
        "physical_execution_authorized": False,
        "compounding_authorized": False,
        "purchase_authority": False,
        "sensory_authority": False,
        "hedonic_authority": False,
        "similarity_authority": False,
        "safety_authority": False,
        "stability_authority": False,
        "release_authority": False,
        "model_retirement_authority": False,
    }
)


@dataclass(frozen=True, slots=True)
class ArchitectureMaterialBinding:
    material_name: str
    canonical_name: str
    function_id: str
    role: str
    ideal_status: str
    current_build_intent: bool
    inventory_state: str
    stock_fraction: str | None
    stock_fraction_basis: str | None
    stock_carrier: str | None
    exact_stock_ref: str | None
    physical_execution_ready: bool
    source_rows: tuple[int, ...]
    inventory_status: str
    inventory_note: str | None
    active_equivalence_ready: bool
    molecular_mechanism_authority: bool
    formula_rebase_authorized: bool
    general_substitution_authorized: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "material_name": self.material_name,
            "canonical_name": self.canonical_name,
            "function_id": self.function_id,
            "role": self.role,
            "ideal_status": self.ideal_status,
            "current_build_intent": self.current_build_intent,
            "inventory_state": self.inventory_state,
            "stock_fraction": self.stock_fraction,
            "stock_fraction_basis": self.stock_fraction_basis,
            "stock_carrier": self.stock_carrier,
            "exact_stock_ref": self.exact_stock_ref,
            "physical_execution_ready": self.physical_execution_ready,
            "source_rows": list(self.source_rows),
            "inventory_status": self.inventory_status,
            "inventory_note": self.inventory_note,
            "active_equivalence_ready": self.active_equivalence_ready,
            "molecular_mechanism_authority": self.molecular_mechanism_authority,
            "formula_rebase_authorized": self.formula_rebase_authorized,
            "general_substitution_authorized": self.general_substitution_authorized,
        }


@dataclass(frozen=True, slots=True)
class ArchitectureCompileResult:
    state: ArchitectureCompilationState
    target_identity: str
    target_reference: str
    target_lock_sha256: str
    formula_lineage_sha256: str
    family_adapter_id: str
    family_adapter_applied_after_target_lock: bool
    ideal_formula_ref: str
    current_inventory_build_ref: str
    primary_strategy: ArchitectureStrategyId
    secondary_strategies: tuple[ArchitectureStrategyId, ...]
    applied_strategy_ids: tuple[str, ...]
    function_ownership: Mapping[str, str]
    material_bindings: tuple[ArchitectureMaterialBinding, ...]
    delta_result: ArchitecturalDeltaResult | None
    blockers: tuple[str, ...]
    current_build_blockers: tuple[str, ...]
    next_action: str
    rule_registry_sha256: str
    strategy_registry_sha256: str
    inventory_workbook_sha256: str
    inventory_overlay_sha256: str | None
    inventory_workbook_record_count: int
    inventory_alias_record_count: int
    compilation_sha256: str
    claim_ceiling: str
    authority_flags: Mapping[str, bool]


def _strategy_assignments(
    request: ArchitectureCompileRequest,
) -> tuple[ArchitectureStrategyAssignment, ...]:
    return (request.primary_strategy, *request.secondary_strategies)


def _strategy_blockers(
    request: ArchitectureCompileRequest,
    registry: ArchitectureStrategyRegistry,
) -> tuple[str, ...]:
    blockers: list[str] = []
    assignments = _strategy_assignments(request)
    primary_definition = registry.get(request.primary_strategy.strategy_id)
    allowed_secondaries = set(primary_definition.compatible_secondaries)
    for secondary in request.secondary_strategies:
        registry.get(secondary.strategy_id)
        if secondary.strategy_id not in allowed_secondaries:
            blockers.append(
                f"secondary strategy {secondary.strategy_id.value} is not declared "
                f"compatible with primary {request.primary_strategy.strategy_id.value}"
            )

    function_ids = {item.function_id for item in request.functions}
    owners: dict[str, list[str]] = {function_id: [] for function_id in function_ids}
    for assignment in assignments:
        for function_id in assignment.owns_function_ids:
            if function_id not in function_ids:
                blockers.append(
                    f"strategy {assignment.strategy_id.value} owns unknown function "
                    f"{function_id}"
                )
                continue
            owners[function_id].append(assignment.strategy_id.value)
    for function_id in sorted(function_ids):
        assigned = owners[function_id]
        if not assigned:
            blockers.append(f"function {function_id} is not owned by any strategy")
        elif len(assigned) > 1:
            blockers.append(
                f"function {function_id} is owned by multiple strategies: "
                + ", ".join(assigned)
            )
    return tuple(blockers)


def _layer_and_transition_blockers(
    request: ArchitectureCompileRequest,
) -> tuple[str, ...]:
    blockers: list[str] = []
    function_ids = {item.function_id for item in request.functions}
    layer_ids = {item.layer_id for item in request.layers}
    placements: dict[str, list[str]] = {function_id: [] for function_id in function_ids}
    for layer in request.layers:
        for function_id in layer.function_ids:
            if function_id not in function_ids:
                blockers.append(
                    f"layer {layer.layer_id} references unknown function {function_id}"
                )
                continue
            placements[function_id].append(layer.layer_id)
    for function_id in sorted(function_ids):
        located = placements[function_id]
        if not located:
            blockers.append(f"function {function_id} is not placed in any layer")
        elif len(located) > 1:
            blockers.append(
                f"function {function_id} is placed in multiple layers: "
                + ", ".join(located)
            )
    for transition in request.transitions:
        if transition.from_layer_id not in layer_ids:
            blockers.append(
                f"transition {transition.transition_id} has unknown from-layer "
                f"{transition.from_layer_id}"
            )
        if transition.to_layer_id not in layer_ids:
            blockers.append(
                f"transition {transition.transition_id} has unknown to-layer "
                f"{transition.to_layer_id}"
            )
    return tuple(blockers)


def _material_blockers(
    request: ArchitectureCompileRequest,
) -> tuple[str, ...]:
    blockers: list[str] = []
    function_ids = {item.function_id for item in request.functions}
    seen: set[tuple[str, str]] = set()
    for hypothesis in request.material_hypotheses:
        if hypothesis.function_id not in function_ids:
            blockers.append(
                f"material {hypothesis.material_name} references unknown function "
                f"{hypothesis.function_id}"
            )
        key = (hypothesis.material_name.casefold(), hypothesis.function_id)
        if key in seen:
            blockers.append(
                f"duplicate material hypothesis for {hypothesis.material_name} and "
                f"{hypothesis.function_id}"
            )
        seen.add(key)
    return tuple(blockers)


def _shortcut_blockers(
    request: ArchitectureCompileRequest,
    rules: PerfumeryRuleRegistry,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if request.component_count_used_as_complexity:
        blockers.append(
            "component_count_used_as_complexity violates the ingredient-count firewall"
        )
    if request.predicted_oav_used_as_perception:
        blockers.append(
            "predicted_oav_used_as_perception violates the perceptual-evidence firewall"
        )
    if request.composition_score_used_as_hedonic:
        blockers.append(
            "composition_score_used_as_hedonic violates the hedonic-evidence firewall"
        )
    if rules.ingredient_count_is_complexity:
        blockers.append("rule registry illegally treats ingredient count as complexity")
    if rules.predicted_oav_has_perceptual_authority:
        blockers.append("rule registry illegally grants predicted OAV perception authority")
    if rules.composition_score_has_hedonic_authority:
        blockers.append("rule registry illegally grants composition hedonic authority")
    return tuple(blockers)


def _material_binding(
    hypothesis: ArchitectureMaterialHypothesis,
    inventory_projection: Any,
) -> ArchitectureMaterialBinding:
    stock = getattr(inventory_projection, "stock", None)
    fraction = getattr(stock, "fraction", None) if stock is not None else None
    fraction_basis = (
        getattr(stock, "fraction_basis", None) if stock is not None else None
    )
    if hasattr(fraction_basis, "value"):
        fraction_basis = fraction_basis.value
    state = getattr(inventory_projection, "state")
    if hasattr(state, "value"):
        state = state.value
    return ArchitectureMaterialBinding(
        material_name=hypothesis.material_name,
        canonical_name=str(getattr(inventory_projection, "canonical_name")),
        function_id=hypothesis.function_id,
        role=hypothesis.role,
        ideal_status=hypothesis.ideal_status,
        current_build_intent=hypothesis.current_build_intent,
        inventory_state=str(state),
        stock_fraction=str(fraction) if fraction is not None else None,
        stock_fraction_basis=(
            str(fraction_basis) if fraction_basis is not None else None
        ),
        stock_carrier=(
            getattr(stock, "carrier", None) if stock is not None else None
        ),
        exact_stock_ref=getattr(inventory_projection, "exact_stock_ref", None),
        physical_execution_ready=bool(
            getattr(inventory_projection, "physical_execution_ready", False)
        ),
        source_rows=tuple(getattr(inventory_projection, "source_rows", ())),
        inventory_status=str(getattr(inventory_projection, "status")),
        inventory_note=getattr(inventory_projection, "note", None),
        active_equivalence_ready=bool(
            getattr(inventory_projection, "active_equivalence_ready", False)
        ),
        molecular_mechanism_authority=bool(
            getattr(inventory_projection, "molecular_mechanism_authority", False)
        ),
        formula_rebase_authorized=bool(
            getattr(inventory_projection, "formula_rebase_authorized", False)
        ),
        general_substitution_authorized=bool(
            getattr(inventory_projection, "general_substitution_authorized", False)
        ),
    )


def _project_materials(
    request: ArchitectureCompileRequest,
    inventory_snapshot: Any,
) -> tuple[tuple[ArchitectureMaterialBinding, ...], tuple[str, ...]]:
    bindings: list[ArchitectureMaterialBinding] = []
    current_build_blockers: list[str] = []
    for hypothesis in request.material_hypotheses:
        projection = inventory_snapshot.project(hypothesis.material_name)
        binding = _material_binding(hypothesis, projection)
        bindings.append(binding)
        if hypothesis.current_build_intent and (
            not binding.exact_stock_ref or not binding.physical_execution_ready
        ):
            current_build_blockers.append(
                f"{hypothesis.material_name}: current build requires a matching "
                f"ExactStockRef; inventory state={binding.inventory_state}, "
                f"status={binding.inventory_status}"
            )
    return tuple(bindings), tuple(current_build_blockers)


def _function_ownership(
    request: ArchitectureCompileRequest,
) -> Mapping[str, str]:
    ownership: dict[str, str] = {}
    for assignment in _strategy_assignments(request):
        for function_id in assignment.owns_function_ids:
            ownership[function_id] = assignment.strategy_id.value
    return MappingProxyType(dict(sorted(ownership.items())))


def _delta_candidate_payload(candidate: Any) -> dict[str, object]:
    return {
        "candidate_id": candidate.candidate_id,
        "material": candidate.material,
        "family": candidate.family.value,
        "kind": candidate.kind.value,
        "priority_rank": candidate.priority_rank,
        "target_role": candidate.target_role,
        "nonredundancy_evidence": candidate.nonredundancy_evidence,
        "loss_if_omitted": candidate.loss_if_omitted,
        "failure_mode": candidate.failure_mode,
        "controlled_arms": list(candidate.controlled_arms),
        "evidence_refs": list(candidate.evidence_refs),
        "count_based": candidate.count_based,
        "redundant_with_current_build": candidate.redundant_with_current_build,
        "primary_role": candidate.primary_role,
        "target_explicitly_names_material": (
            candidate.target_explicitly_names_material
        ),
        "distinct_role_refs": list(candidate.distinct_role_refs),
        "pairwise_nonredundancy_refs": list(
            candidate.pairwise_nonredundancy_refs
        ),
        "exception_justification": candidate.exception_justification,
        "causal_design_sha256": candidate.causal_design_sha256,
        "uniqueness_evidence_refs": list(candidate.uniqueness_evidence_refs),
        "nary_candidate": (
            candidate.nary_candidate.as_dict()
            if candidate.nary_candidate is not None
            else None
        ),
        "comparison_closure": (
            candidate.comparison_closure.as_dict()
            if candidate.comparison_closure is not None
            else None
        ),
    }


def _compilation_sha256(
    request: ArchitectureCompileRequest,
    rules: PerfumeryRuleRegistry,
    strategies: ArchitectureStrategyRegistry,
    material_bindings: tuple[ArchitectureMaterialBinding, ...],
    blockers: tuple[str, ...],
    current_build_blockers: tuple[str, ...],
    inventory_workbook_sha256: str,
    inventory_overlay_sha256: str | None,
    inventory_workbook_record_count: int,
    inventory_alias_record_count: int,
) -> str:
    payload = request.as_dict()
    payload["delta_candidates"] = [
        _delta_candidate_payload(candidate) for candidate in request.delta_candidates
    ]
    payload["material_bindings"] = [
        binding.as_dict() for binding in material_bindings
    ]
    payload["blockers"] = list(blockers)
    payload["current_build_blockers"] = list(current_build_blockers)
    payload["rule_registry_sha256"] = rules.source_sha256
    payload["strategy_registry_sha256"] = strategies.source_sha256
    payload["inventory_workbook_sha256"] = inventory_workbook_sha256
    payload["inventory_overlay_sha256"] = inventory_overlay_sha256
    payload["inventory_workbook_record_count"] = inventory_workbook_record_count
    payload["inventory_alias_record_count"] = inventory_alias_record_count
    return sha256_hex(canonical_json_bytes(payload))


def _inventory_identity(
    inventory_snapshot: Any,
) -> tuple[str, str | None, int, int]:
    workbook_sha256 = str(getattr(inventory_snapshot, "workbook_sha256", "")).lower()
    if len(workbook_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in workbook_sha256
    ):
        raise ValueError("inventory_snapshot.workbook_sha256 must be a SHA-256 digest")
    raw_overlay_sha256 = getattr(inventory_snapshot, "overlay_sha256", None)
    overlay_sha256 = (
        str(raw_overlay_sha256).lower()
        if raw_overlay_sha256 is not None
        else None
    )
    if overlay_sha256 is not None and (
        len(overlay_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in overlay_sha256
        )
    ):
        raise ValueError("inventory_snapshot.overlay_sha256 must be a SHA-256 digest")
    workbook_record_count = getattr(
        inventory_snapshot,
        "workbook_record_count",
        None,
    )
    alias_record_count = getattr(inventory_snapshot, "alias_record_count", 0)
    for field_name, value in (
        ("workbook_record_count", workbook_record_count),
        ("alias_record_count", alias_record_count),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(
                f"inventory_snapshot.{field_name} must be a nonnegative integer"
            )
    return (
        workbook_sha256,
        overlay_sha256,
        workbook_record_count,
        alias_record_count,
    )


def _hold_result(
    request: ArchitectureCompileRequest,
    inventory_snapshot: Any,
    rules: PerfumeryRuleRegistry,
    strategies: ArchitectureStrategyRegistry,
    blockers: tuple[str, ...],
) -> ArchitectureCompileResult:
    target_lock_sha256 = sha256_hex(
        canonical_json_bytes(request.target_lock_payload())
    )
    (
        workbook_sha256,
        overlay_sha256,
        workbook_record_count,
        alias_record_count,
    ) = _inventory_identity(inventory_snapshot)
    compilation_sha256 = _compilation_sha256(
        request,
        rules,
        strategies,
        (),
        blockers,
        (),
        workbook_sha256,
        overlay_sha256,
        workbook_record_count,
        alias_record_count,
    )
    return ArchitectureCompileResult(
        state=ArchitectureCompilationState.HOLD,
        target_identity=request.target_identity,
        target_reference=request.target_reference,
        target_lock_sha256=target_lock_sha256,
        formula_lineage_sha256=request.formula_lineage_sha256,
        family_adapter_id=request.family_adapter_id,
        family_adapter_applied_after_target_lock=True,
        ideal_formula_ref=request.ideal_formula_ref,
        current_inventory_build_ref=request.current_inventory_build_ref,
        primary_strategy=request.primary_strategy.strategy_id,
        secondary_strategies=tuple(
            item.strategy_id for item in request.secondary_strategies
        ),
        applied_strategy_ids=tuple(
            item.strategy_id.value for item in _strategy_assignments(request)
        ),
        function_ownership=MappingProxyType({}),
        material_bindings=(),
        delta_result=None,
        blockers=blockers,
        current_build_blockers=(),
        next_action="HOLD",
        rule_registry_sha256=rules.source_sha256,
        strategy_registry_sha256=strategies.source_sha256,
        inventory_workbook_sha256=workbook_sha256,
        inventory_overlay_sha256=overlay_sha256,
        inventory_workbook_record_count=workbook_record_count,
        inventory_alias_record_count=alias_record_count,
        compilation_sha256=compilation_sha256,
        claim_ceiling=rules.claim_ceiling,
        authority_flags=_AUTHORITY_FLAGS,
    )


def compile_architecture(
    request: ArchitectureCompileRequest,
    inventory_snapshot: Any,
    *,
    repository_root: str | Path | None = None,
) -> ArchitectureCompileResult:
    """Validate and compile a target architecture into zero or one experiment."""

    if not isinstance(request, ArchitectureCompileRequest):
        raise TypeError("request must be an ArchitectureCompileRequest")
    if inventory_snapshot is None or not callable(
        getattr(inventory_snapshot, "project", None)
    ):
        raise TypeError("inventory_snapshot must provide project(material)")
    (
        workbook_sha256,
        overlay_sha256,
        workbook_record_count,
        alias_record_count,
    ) = _inventory_identity(inventory_snapshot)
    root = Path(repository_root) if repository_root is not None else _REPOSITORY_ROOT
    rules, strategies = load_default_architecture_registries(root)

    blockers = (
        *_shortcut_blockers(request, rules),
        *_strategy_blockers(request, strategies),
        *_layer_and_transition_blockers(request),
        *_material_blockers(request),
    )
    if blockers:
        return _hold_result(
            request,
            inventory_snapshot,
            rules,
            strategies,
            tuple(blockers),
        )

    target_lock_sha256 = sha256_hex(
        canonical_json_bytes(request.target_lock_payload())
    )
    material_bindings, current_build_blockers = _project_materials(
        request,
        inventory_snapshot,
    )
    delta_request = ArchitecturalDeltaRequest(
        target_identity=request.target_identity,
        ideal_formula_ref=request.ideal_formula_ref,
        current_build_ref=request.current_inventory_build_ref,
        formula_lineage_sha256=request.formula_lineage_sha256,
        candidates=request.delta_candidates,
        no_change_reason=request.no_change_reason,
    )
    delta_result = evaluate_architectural_delta(
        delta_request,
        inventory_snapshot=inventory_snapshot,
    )
    delta_blockers = (
        tuple(delta_result.blockers)
        if delta_result.state is ArchitecturalDeltaState.HOLD
        else ()
    )
    if delta_result.state is ArchitecturalDeltaState.HOLD:
        state = ArchitectureCompilationState.HOLD
        next_action = "HOLD"
    elif delta_result.state is ArchitecturalDeltaState.NO_CHANGE:
        state = ArchitectureCompilationState.NO_CHANGE
        next_action = "NO_CHANGE"
    else:
        state = ArchitectureCompilationState.EXPERIMENT_PROPOSED
        next_action = delta_result.next_comparison or "RUN_CONTROLLED_COMPARISON"

    compilation_sha256 = _compilation_sha256(
        request,
        rules,
        strategies,
        material_bindings,
        delta_blockers,
        current_build_blockers,
        workbook_sha256,
        overlay_sha256,
        workbook_record_count,
        alias_record_count,
    )
    return ArchitectureCompileResult(
        state=state,
        target_identity=request.target_identity,
        target_reference=request.target_reference,
        target_lock_sha256=target_lock_sha256,
        formula_lineage_sha256=request.formula_lineage_sha256,
        family_adapter_id=request.family_adapter_id,
        family_adapter_applied_after_target_lock=True,
        ideal_formula_ref=request.ideal_formula_ref,
        current_inventory_build_ref=request.current_inventory_build_ref,
        primary_strategy=request.primary_strategy.strategy_id,
        secondary_strategies=tuple(
            item.strategy_id for item in request.secondary_strategies
        ),
        applied_strategy_ids=tuple(
            item.strategy_id.value for item in _strategy_assignments(request)
        ),
        function_ownership=_function_ownership(request),
        material_bindings=material_bindings,
        delta_result=delta_result,
        blockers=delta_blockers,
        current_build_blockers=current_build_blockers,
        next_action=next_action,
        rule_registry_sha256=rules.source_sha256,
        strategy_registry_sha256=strategies.source_sha256,
        inventory_workbook_sha256=workbook_sha256,
        inventory_overlay_sha256=overlay_sha256,
        inventory_workbook_record_count=workbook_record_count,
        inventory_alias_record_count=alias_record_count,
        compilation_sha256=compilation_sha256,
        claim_ceiling=rules.claim_ceiling,
        authority_flags=_AUTHORITY_FLAGS,
    )


__all__ = [
    "ArchitectureCompileResult",
    "ArchitectureMaterialBinding",
    "compile_architecture",
]
