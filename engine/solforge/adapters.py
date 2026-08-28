"""Pure adapters between SolForge records and existing evidence engines."""

from __future__ import annotations

import hashlib
import itertools
from pathlib import Path
from typing import Any

from engine.evidence.augmentation import (
    DecisionDeltaV1,
    EvidenceAugmentationState,
    EvidenceDeltaReceiptV1,
    hold_receipt,
    no_augmentation_receipt,
)
from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.hedonic_evidence import (
    EvaluationSubstrate,
    HedonicEvidenceRequest,
    HedonicEvidenceState,
    HedonicScope,
    PreferenceEvidenceAdequacyContract,
    PreferenceItemEvidenceBinding,
    SensoryEvaluationContext,
    bind_preference_fit_evidence,
    bind_preference_fit_evidence_v2,
    bind_preference_fit_evidence_v3,
    evaluate_hedonic_evidence,
)
from engine.perception.architectural_delta import (
    ArchitecturalDeltaCandidate,
    ArchitecturalDeltaFamily,
    ArchitecturalDeltaKind,
    ArchitecturalDeltaRequest,
    ArchitecturalDeltaResult,
    ArchitecturalDeltaState,
    ArchitecturalEvidenceDeltaResultV2,
    ComparisonClosureV1,
    _load_execution_inventory_catalog,
    evaluate_architectural_delta,
    evaluate_architectural_evidence_delta,
)
from engine.preference import (
    PairwisePreference,
    PreferenceFitRequest,
    PreferenceFitStatus,
    fit_preference_model,
)
from engine.preference_davidson import DavidsonFitConfig, fit_davidson
from engine.preference_validation import (
    ClusterBootstrapConfig,
    HeldoutValidationConfig,
    NextPairConstraints,
    OrderCarryoverConfig,
    TransitivityConfig,
)
from engine.sensory.ledger import (
    SensoryProtocolScope,
    SensorySafetyEvent,
    TemporalEvidenceAuditResultV2,
    TemporalEvidenceRequest,
    TemporalEvidenceResult,
    TemporalEvidenceState,
    TemporalObservationCell,
    analyze_temporal_evidence,
    audit_temporal_evidence,
)
from engine.sensory.order_balance import PresentationSchedule
from engine.solforge.contracts import (
    CompilationState,
    CompiledArmV1,
    CompiledExperimentV1,
    CriterionFitPacketV1,
    CriterionFitPacketV2,
    CriterionFitPacketV3,
    ExecutionReceiptV1,
    SolForgeCaseState,
    SolForgeCaseV1,
    SolHypothesisSetV1,
    SolHypothesisV1,
    TemporalEvidencePacketV1,
)
from engine.solforge.hypotheses import validate_hypothesis_set

_EXCEPTION_MUSKS = ("tonalide", "macrolide", "musk ketone")
_MUSK_MARKERS = (
    "musk", "habanolide", "romandolide", "ambrettolide", "tonalide",
    "ethylene brassylate", "macrolide",
)
_CITRUS_MARKERS = (
    "citrus", "lemon", "lime", "orange", "bergamot", "grapefruit", "neroli",
    "mandarin", "citron",
)


def _strict_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{field} must be nonblank text")
    return value.strip()


def _strict_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field} must be boolean")
    return value


def _strict_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be an integer")
    return value


def _strict_real(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be a real number")
    return float(value)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _family(materials: tuple[str, ...]) -> ArchitecturalDeltaFamily:
    joined = " ".join(materials).casefold()
    if any(marker in joined for marker in _MUSK_MARKERS):
        return ArchitecturalDeltaFamily.MUSK
    if any(marker in joined for marker in _CITRUS_MARKERS):
        return ArchitecturalDeltaFamily.CITRUS
    return ArchitecturalDeltaFamily.GENERAL


def _arm_id(value: str) -> str:
    return "_".join(value.upper().replace("-", " ").split())


def _current_material_names(case: SolForgeCaseV1) -> frozenset[str]:
    build = case.as_dict()["current_inventory_build"]
    if not isinstance(build, dict):
        return frozenset()
    materials = build.get("materials")
    if isinstance(materials, dict):
        return frozenset(str(name).casefold() for name in materials)
    if isinstance(materials, list):
        names: list[str] = []
        for item in materials:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict) and isinstance(item.get("name"), str):
                names.append(item["name"])
        return frozenset(name.casefold() for name in names)
    return frozenset()


def _candidate(case: SolForgeCaseV1, hypothesis: SolHypothesisV1) -> ArchitecturalDeltaCandidate:
    family = _family(hypothesis.material_names)
    nary = hypothesis.intervention_kind == "NARY_DESIGN"
    material = " + ".join(hypothesis.material_names)
    if nary:
        factors = tuple(_arm_id(name) for name in hypothesis.material_names)
        arms = ("CONTROL", *factors, "_X_".join(factors))
        roles = tuple(
            role.strip() for role in hypothesis.target_function.split("|") if role.strip()
        )
    else:
        arms = ("CONTROL", _arm_id(hypothesis.hypothesis_id))
        roles = ()
    closure = ComparisonClosureV1(
        rejected_alternative=arms[0],
        compliant_treatment=arms[-1],
        primary_endpoints=(case.criterion,),
        failure_endpoints=("TARGET_IDENTITY_DRIFT",),
        changed_factor=(
            " + ".join(hypothesis.material_names)
            if not nary
            else "NARY_INTERACTION"
        ),
        constant_constraints=(
            tuple(case.constraints)
            if case.constraints
            else ("CONSTANT_TOTAL_ACTIVE_MASS",)
        ),
        blinding_rule="Freeze formula hashes before assigning opaque codes.",
        order_rule="Balance first presentation and record predecessor.",
        time_windows=("OPENING", "HEART", "DRYDOWN"),
        accept_rule=(
            f"Accept only if {case.criterion} improves without target-identity drift."
        ),
        reject_rule="Reject for no criterion gain, redundancy, or target drift.",
    )
    current = _current_material_names(case)
    target = case.target_identity.casefold()
    material_key = material.casefold()
    explicit_citrus = "neroli" in target or "orange blossom" in target
    exception = any(marker in material_key for marker in _EXCEPTION_MUSKS)
    exception_justification = None
    if exception and any(marker in target for marker in _EXCEPTION_MUSKS):
        if "exception" in hypothesis.rationale.casefold():
            exception_justification = hypothesis.rationale
    return ArchitecturalDeltaCandidate(
        candidate_id=hypothesis.hypothesis_id,
        material=material,
        family=family,
        kind=ArchitecturalDeltaKind(hypothesis.intervention_kind),
        priority_rank=hypothesis.rank,
        target_role=hypothesis.target_function,
        nonredundancy_evidence=hypothesis.rationale,
        loss_if_omitted=f"The target loses the proposed {hypothesis.target_function} function.",
        failure_mode="The intervention may blur or replace the declared target identity.",
        controlled_arms=arms,
        evidence_refs=hypothesis.evidence_refs,
        redundant_with_current_build=any(
            name.casefold() in current for name in hypothesis.material_names
        ),
        primary_role="primary" in hypothesis.target_function.casefold(),
        target_explicitly_names_material=explicit_citrus,
        distinct_role_refs=roles,
        pairwise_nonredundancy_refs=(
            hypothesis.evidence_refs[:1] if len(roles) == 2 else hypothesis.evidence_refs
        ),
        exception_justification=exception_justification,
        causal_design_sha256=(hypothesis.evidence_refs[0] if nary and hypothesis.evidence_refs else None),
        comparison_closure=closure,
    )


def _compiled_arms(
    case: SolForgeCaseV1,
    arm_ids: tuple[str, ...],
    materials: tuple[str, ...],
) -> tuple[CompiledArmV1, ...]:
    factor_ids = tuple(_arm_id(name) for name in materials)
    arms: list[CompiledArmV1] = []
    for arm_id in arm_ids:
        presence = {
            material: factor_id in arm_id.split("_X_") or arm_id == factor_id
            for material, factor_id in zip(materials, factor_ids, strict=True)
        }
        formula = {
            "base_build": case.as_dict()["current_inventory_build"],
            "factor_presence": presence,
            "constant_total_active_mass_g": 1.0,
            "compensation": "carrier",
        }
        sample_hash = sha256_hex(
            canonical_json_bytes(
                {"case_sha256": case.record_sha256, "arm_id": arm_id, "formula": formula}
            )
        )
        arms.append(
            CompiledArmV1(
                arm_id=arm_id,
                formula=formula,
                total_active_mass_g=1.0,
                blind_code=f"SF-{sample_hash[:8].upper()}",
                sample_sha256=sample_hash,
            )
        )
    return tuple(arms)


def _hold(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
    inventory_sha256: str,
    row_count: int,
    blockers: tuple[str, ...],
) -> CompiledExperimentV1:
    return CompiledExperimentV1(
        case_sha256=case.record_sha256,
        hypothesis_set_sha256=hypotheses.record_sha256,
        inventory_refresh_sha256=inventory_sha256,
        inventory_source_row_count=row_count,
        state=CompilationState.HOLD,
        delta_kind=None,
        selected_hypothesis_id=None,
        arms=(),
        blockers=blockers,
        inventory_statuses=(),
        omission_loss=None,
        failure_mode=None,
        next_comparison=None,
    )


def compile_architectural_delta(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
) -> CompiledExperimentV1:
    """Compile zero or one target-faithful, inventory-bound shadow experiment."""

    path = Path(case.inventory_path)
    if not path.is_file():
        return _hold(case, hypotheses, case.inventory_sha256, 0, ("INVENTORY_PATH_MISSING",))
    observed_sha256 = _file_sha256(path)
    if observed_sha256 != case.inventory_sha256:
        return _hold(case, hypotheses, observed_sha256, 0, ("INVENTORY_HASH_MISMATCH",))

    refresh_request = ArchitecturalDeltaRequest(
        target_identity=case.target_identity,
        ideal_formula_ref=f"case:{case.record_sha256}:ideal",
        current_build_ref=f"case:{case.record_sha256}:inventory-build",
        formula_lineage_sha256=case.formula_sha256,
        candidates=(),
        no_change_reason="No validated nonredundant intervention remains.",
    )
    refresh = evaluate_architectural_delta(
        refresh_request, inventory_workbook_path=str(path)
    )
    validation = validate_hypothesis_set(case, hypotheses)
    if case.state is not SolForgeCaseState.READY:
        return _hold(case, hypotheses, observed_sha256, refresh.inventory_source_row_count, ("CASE_NOT_READY",))
    if not validation.valid:
        return _hold(case, hypotheses, observed_sha256, refresh.inventory_source_row_count, validation.blocker_codes)
    if len(hypotheses.hypotheses) > 1:
        return _hold(
            case, hypotheses, observed_sha256, refresh.inventory_source_row_count,
            ("MULTIPLE_INDEPENDENT_INTERVENTIONS",),
        )
    if validation.no_change:
        return CompiledExperimentV1(
            case_sha256=case.record_sha256,
            hypothesis_set_sha256=hypotheses.record_sha256,
            inventory_refresh_sha256=observed_sha256,
            inventory_source_row_count=refresh.inventory_source_row_count,
            state=CompilationState.NO_CHANGE,
            delta_kind=None,
            selected_hypothesis_id=None,
            arms=(), blockers=(), inventory_statuses=(), omission_loss=None,
            failure_mode=None, next_comparison=None,
        )

    hypothesis = hypotheses.hypotheses[0]
    candidate = _candidate(case, hypothesis)
    request = ArchitecturalDeltaRequest(
        target_identity=case.target_identity,
        ideal_formula_ref=f"case:{case.record_sha256}:ideal",
        current_build_ref=f"case:{case.record_sha256}:inventory-build",
        formula_lineage_sha256=case.formula_sha256,
        candidates=(candidate,),
        no_change_reason="No validated nonredundant intervention remains.",
    )
    delta = evaluate_architectural_delta(request, inventory_workbook_path=str(path))
    if delta.state is not ArchitecturalDeltaState.PROPOSED:
        return _hold(
            case, hypotheses, observed_sha256, delta.inventory_source_row_count,
            delta.blockers or ("ARCHITECTURAL_DELTA_NOT_PROPOSED",),
        )
    catalog = _load_execution_inventory_catalog(None, str(path))
    statuses = tuple(
        (material, catalog.project(material).availability.value)
        for material in hypothesis.material_names
    )
    return CompiledExperimentV1(
        case_sha256=case.record_sha256,
        hypothesis_set_sha256=hypotheses.record_sha256,
        inventory_refresh_sha256=observed_sha256,
        inventory_source_row_count=delta.inventory_source_row_count,
        state=CompilationState.COMPILED,
        delta_kind=hypothesis.intervention_kind,
        selected_hypothesis_id=hypothesis.hypothesis_id,
        arms=_compiled_arms(case, delta.controlled_arms, hypothesis.material_names),
        blockers=(),
        inventory_statuses=statuses,
        omission_loss=candidate.loss_if_omitted,
        failure_mode=candidate.failure_mode,
        next_comparison=delta.next_comparison,
    )


def compile_architectural_delta_v2(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
) -> ArchitecturalEvidenceDeltaResultV2:
    """Compile a V2 conditional delta while preserving all V1 fail-closed gates."""

    legacy = compile_architectural_delta(case, hypotheses)
    candidates = tuple(_candidate(case, item) for item in hypotheses.hypotheses)
    request = ArchitecturalDeltaRequest(
        target_identity=case.target_identity,
        ideal_formula_ref=f"case:{case.record_sha256}:ideal",
        current_build_ref=f"case:{case.record_sha256}:inventory-build",
        formula_lineage_sha256=case.formula_sha256,
        candidates=candidates,
        no_change_reason="No validated nonredundant intervention remains.",
    )
    if legacy.state is CompilationState.HOLD and "INVENTORY_PATH_MISSING" in legacy.blockers:
        input_sha256 = sha256_hex(
            canonical_json_bytes(
                {
                    "case_sha256": case.record_sha256,
                    "hypothesis_set_sha256": hypotheses.record_sha256,
                }
            )
        )
        receipt = hold_receipt(
            module_id="architectural_delta",
            exact_scope=f"{case.case_id}/{case.target_identity}",
            input_sha256=input_sha256,
            evidence_sha256=hypotheses.record_sha256,
            policy_sha256=sha256_hex(
                canonical_json_bytes(
                    {"policy": "authoritative inventory required at execution"}
                )
            ),
            source_binding_sha256=tuple(
                sorted(
                    {
                        ref
                        for hypothesis in hypotheses.hypotheses
                        for ref in hypothesis.evidence_refs
                    }
                )
            ),
            reasons=("SOLFORGE_COMPILATION_HOLD",),
            blockers=legacy.blockers,
            next_action=None,
        )
        architectural = ArchitecturalDeltaResult(
            state=ArchitecturalDeltaState.HOLD,
            target_identity=case.target_identity,
            ideal_formula_ref=request.ideal_formula_ref,
            current_build_ref=request.current_build_ref,
            formula_lineage_sha256=case.formula_sha256,
            inventory_workbook_sha256=case.inventory_sha256,
            inventory_source_row_count=0,
            selected_candidate=None,
            inventory_projection=None,
            controlled_arms=(),
            blockers=legacy.blockers,
            next_comparison=None,
        )
        return ArchitecturalEvidenceDeltaResultV2(architectural, None, receipt)
    result = evaluate_architectural_evidence_delta(
        request,
        inventory_workbook_path=case.inventory_path,
    )
    if legacy.state is not CompilationState.HOLD:
        return result

    prior = result.receipt
    receipt = hold_receipt(
        module_id=prior.module_id,
        exact_scope=prior.exact_scope,
        input_sha256=prior.input_sha256,
        evidence_sha256=prior.evidence_sha256,
        policy_sha256=prior.policy_sha256,
        source_binding_sha256=prior.source_binding_sha256,
        reasons=("SOLFORGE_COMPILATION_HOLD",),
        blockers=legacy.blockers or ("Legacy compilation gate held.",),
        next_action=None,
    )
    return ArchitecturalEvidenceDeltaResultV2(
        architectural_result=result.architectural_result,
        comparison_closure=result.comparison_closure,
        receipt=receipt,
    )


_CRITERIA = ("TARGET_FIDELITY", "DEPTH", "RICHNESS", "LIKING")


def export_backend_lab_payloads(experiment: CompiledExperimentV1) -> dict[str, object]:
    """Return deterministic draft payloads; perform no API, database, or lab action."""

    if experiment.state is not CompilationState.COMPILED or len(experiment.arms) < 2:
        raise ValueError("backend export requires a compiled multi-arm experiment")
    experiment_sha256 = experiment.record_sha256
    arm_ids = tuple(arm.arm_id for arm in experiment.arms)
    schedule_sha256 = sha256_hex(
        canonical_json_bytes(
            {
                "compiled_experiment_sha256": experiment_sha256,
                "arm_ids": arm_ids,
                "criterion_ids": _CRITERIA,
                "presentation_order": arm_ids,
            }
        )
    )
    protocol = {
        "schema_version": "solforge_protocol_context_v1",
        "compiled_experiment_sha256": experiment_sha256,
        "schedule_sha256": schedule_sha256,
        "arm_ids": list(arm_ids),
        "criterion_ids": list(_CRITERIA),
        "test_only": True,
    }
    samples = [
        {
            "bottle_id": f"shadow-only:{arm.sample_sha256}",
            "blind_code": arm.blind_code,
        }
        for arm in experiment.arms
    ]
    applications = [
        {
            "sample_id": arm.arm_id,
            "applied_at": "1970-01-01T00:00:00Z",
            "dose": {"total_active_mass_g": arm.total_active_mass_g},
            "context": {
                "shadow_template": True,
                "test_only": True,
                "sample_sha256": arm.sample_sha256,
                "compiled_experiment_sha256": experiment_sha256,
            },
        }
        for arm in experiment.arms
    ]
    observations: list[dict[str, object]] = []
    for sequence, arm in enumerate(experiment.arms, start=1):
        for criterion in _CRITERIA:
            observations.append(
                {
                    "elapsed_seconds": 0.0,
                    "observations": {
                        "value": None,
                        "solforge": {
                            "schema_version": "solforge_observation_context_v1",
                            "compiled_experiment_sha256": experiment_sha256,
                            "schedule_sha256": schedule_sha256,
                            "sample_id": arm.arm_id,
                            "sample_sha256": arm.sample_sha256,
                            "assessor_id": "UNASSIGNED_TEST_TEMPLATE",
                            "repeat_index": 1,
                            "timepoint_seconds": 0.0,
                            "endpoint": criterion,
                            "presentation_sequence": sequence,
                            "test_only": True,
                        },
                    },
                }
            )
    comparisons: list[dict[str, object]] = []
    for left, right in itertools.combinations(experiment.arms, 2):
        for criterion in _CRITERIA:
            comparisons.append(
                {
                    "experiment_id": f"shadow-only:{experiment_sha256}",
                    "left_sample_id": left.arm_id,
                    "right_sample_id": right.arm_id,
                    "preferred_sample_id": None,
                    "context": {
                        "solforge": {
                            "schema_version": "solforge_comparison_context_v1",
                            "compiled_experiment_sha256": experiment_sha256,
                            "schedule_sha256": schedule_sha256,
                            "criterion": criterion,
                            "assessor_id": "UNASSIGNED_TEST_TEMPLATE",
                            "repeat_index": 1,
                            "timepoint_seconds": 0.0,
                            "left_sample_id": left.arm_id,
                            "right_sample_id": right.arm_id,
                            "first_presented_item": left.arm_id,
                            "test_only": True,
                        }
                    },
                }
            )
    return {
        "schema_version": "solforge_backend_lab_export_v1",
        "compiled_experiment_sha256": experiment_sha256,
        "schedule_sha256": schedule_sha256,
        "experiment": {
            "name": f"SolForge shadow {experiment_sha256[:12]}",
            "protocol": {"solforge": protocol},
            "status": "planned-shadow-only",
        },
        "samples": samples,
        "applications": applications,
        "observations": observations,
        "comparisons": comparisons,
        "publication_authorized": False,
        "database_write_authorized": False,
        "physical_execution_authorized": False,
    }


def _execution_context(execution: ExecutionReceiptV1) -> dict[str, Any]:
    context = execution.as_dict()["execution_context"]
    if not isinstance(context, dict):
        raise ValueError("execution_context must be a JSON object")
    return context


def _schedule_from_dict(value: object) -> PresentationSchedule:
    if not isinstance(value, dict):
        raise ValueError("execution schedule must be an object")
    return PresentationSchedule(
        labels=tuple(value["labels"]),
        sequences=tuple(tuple(sequence) for sequence in value["sequences"]),
        method=str(value.get("method") or "WILLIAMS_FIRST_ORDER_BALANCED"),
    )


def _scope_from_dict(value: object) -> SensoryProtocolScope:
    if not isinstance(value, dict):
        raise ValueError("protocol_scope must be an object")
    return SensoryProtocolScope(
        protocol_id=str(value["protocol_id"]),
        sample_ids=tuple(value["sample_ids"]),
        assessor_ids=tuple(value["assessor_ids"]),
        repeat_ids=tuple(value["repeat_ids"]),
        timepoints_seconds=tuple(value["timepoints_seconds"]),
        endpoint_ids=tuple(value["endpoint_ids"]),
        schedule_sha256=str(value["schedule_sha256"]),
        within_sniff=bool(value.get("within_sniff", False)),
        within_sniff_apparatus_qualified=bool(
            value.get("within_sniff_apparatus_qualified", False)
        ),
        within_sniff_timing_protocol_qualified=bool(
            value.get("within_sniff_timing_protocol_qualified", False)
        ),
        require_repeatability=bool(value.get("require_repeatability", False)),
        maximum_within_assessor_repeat_spread=value.get(
            "maximum_within_assessor_repeat_spread"
        ),
        within_sniff_apparatus_id=value.get("within_sniff_apparatus_id"),
        within_sniff_clock_source=value.get("within_sniff_clock_source"),
        within_sniff_timing_tolerance_ms=value.get(
            "within_sniff_timing_tolerance_ms"
        ),
        within_sniff_qualification_sha256=value.get(
            "within_sniff_qualification_sha256"
        ),
    )


def _temporal_request_from_execution(
    execution: ExecutionReceiptV1,
) -> TemporalEvidenceRequest:
    context = _execution_context(execution)
    scope = _scope_from_dict(context.get("protocol_scope"))
    schedule = _schedule_from_dict(context.get("schedule"))
    if set(scope.sample_ids) != {sample_id for sample_id, _ in execution.sample_sha256}:
        raise ValueError("protocol samples do not match the execution receipt")
    cells_raw = context.get("observations", [])
    safety_raw = context.get("safety_events", [])
    if not isinstance(cells_raw, list) or not isinstance(safety_raw, list):
        raise ValueError("observations and safety_events must be lists")
    return TemporalEvidenceRequest(
        scope=scope,
        schedule=schedule,
        cells=tuple(TemporalObservationCell.from_dict(item) for item in cells_raw),
        safety_events=tuple(SensorySafetyEvent.from_dict(item) for item in safety_raw),
    )


def analyze_execution_receipt(
    execution: ExecutionReceiptV1,
) -> TemporalEvidenceResult:
    """Analyze only observation cells explicitly bound into an execution receipt."""

    return analyze_temporal_evidence(_temporal_request_from_execution(execution))


def audit_execution_receipt_v2(
    execution: ExecutionReceiptV1,
) -> TemporalEvidenceAuditResultV2:
    """Run the five-state V2 sufficiency audit without changing V1 packets."""

    return audit_temporal_evidence(_temporal_request_from_execution(execution))


def _cell_text(key: object) -> str:
    return canonical_json_bytes(
        {
            "protocol_id": key.protocol_id,
            "sample_id": key.sample_id,
            "assessor_id": key.assessor_id,
            "repeat_id": key.repeat_id,
            "time_seconds": key.time_seconds,
            "endpoint_id": key.endpoint_id,
        }
    ).decode("utf-8")


def _temporal_payload(result: TemporalEvidenceResult) -> dict[str, object]:
    return {
        "state": result.state.value,
        "protocol_id": result.protocol_id,
        "schedule_sha256": result.schedule_sha256,
        "expected_cell_count": result.expected_cell_count,
        "observed_cell_count": result.observed_cell_count,
        "missing_cells": [_cell_text(key) for key in result.missing_cells],
        "duplicate_cells": [_cell_text(key) for key in result.duplicate_cells],
        "summaries": [
            {
                "sample_id": item.sample_id,
                "endpoint_id": item.endpoint_id,
                "time_seconds": item.time_seconds,
                "observed_count": item.observed_count,
                "median": item.median,
                "first_quartile": item.first_quartile,
                "third_quartile": item.third_quartile,
                "assessor_disagreement": item.assessor_disagreement,
            }
            for item in result.summaries
        ],
        "transitions": [
            {
                "sample_id": item.sample_id,
                "endpoint_id": item.endpoint_id,
                "from_time_seconds": item.from_time_seconds,
                "to_time_seconds": item.to_time_seconds,
                "median_delta": item.median_delta,
            }
            for item in result.transitions
        ],
        "order_balance_state": result.order_balance_state.value,
        "blockers": list(result.blockers),
        "next_discriminator": result.next_discriminator,
        "safety_event_ids": [item.event_id for item in result.safety_events],
        "safety_stop_triggered": result.safety_stop_triggered,
        "assessor_reliability_state": result.assessor_reliability_state.value,
    }


def build_temporal_packet(
    execution: ExecutionReceiptV1,
    result: TemporalEvidenceResult,
) -> TemporalEvidencePacketV1:
    """Bind one ledger result to its exact execution parent."""

    state = {
        TemporalEvidenceState.COMPLETE: "COMPLETE",
        TemporalEvidenceState.INCOMPLETE: "INSUFFICIENT",
        TemporalEvidenceState.HOLD: "HOLD",
    }[result.state]
    disagreement = {
        f"{item.sample_id}|{item.endpoint_id}|{item.time_seconds:g}": (
            item.assessor_disagreement
        )
        for item in result.summaries
    }
    return TemporalEvidencePacketV1(
        execution_receipt_sha256=execution.record_sha256,
        ledger_payload_sha256=sha256_hex(canonical_json_bytes(_temporal_payload(result))),
        state=state,
        observed_cell_count=result.observed_cell_count,
        missing_cells=tuple(_cell_text(key) for key in result.missing_cells),
        duplicate_cells=tuple(_cell_text(key) for key in result.duplicate_cells),
        disagreement=disagreement,
        safety_stop=result.safety_stop_triggered,
        next_discriminator=result.next_discriminator,
        test_only=execution.test_only,
    )


def _fit_result_payload(result: object) -> dict[str, object]:
    return {
        "status": result.status.value,
        "validated": result.validated,
        "utilities": result.utilities,
        "comparison_count": result.comparison_count,
        "connected": result.connected,
        "heldout_accuracy": result.heldout_accuracy,
        "baseline_accuracy": result.baseline_accuracy,
        "gate_failures": list(result.gate_failures),
        "validation_notes": list(result.validation_notes),
        "criterion_id": result.criterion_id,
        "utility_intervals": result.utility_intervals,
        "tie_rate": result.tie_rate,
        "assessor_heterogeneity": result.assessor_heterogeneity,
        "order_effect": result.order_effect,
        "next_comparison": result.next_comparison,
        "bootstrap_replicates": result.bootstrap_replicates,
        "bootstrap_seed": result.bootstrap_seed,
        "bootstrap_method": result.bootstrap_method,
        "model_family": result.model_family.value,
        "tie_parameter": result.tie_parameter,
        "converged": result.converged,
        "convergence_code": result.convergence_code,
        "pair_probabilities": result.pair_probabilities,
        "evidence": result.evidence.as_dict(),
    }


def build_criterion_fit_packet(
    execution: ExecutionReceiptV1,
    temporal: TemporalEvidencePacketV1,
    *,
    criterion: str,
) -> CriterionFitPacketV1:
    """Fit exactly one scoped criterion and bind diagnostics to temporal evidence."""

    if temporal.execution_receipt_sha256 != execution.record_sha256:
        raise ValueError("temporal packet does not bind the execution receipt")
    criterion = criterion.strip().upper()
    if criterion not in _CRITERIA:
        raise ValueError("criterion is not supported")
    context = _execution_context(execution)
    comparisons_raw = context.get("comparisons", [])
    if not isinstance(comparisons_raw, list):
        raise ValueError("comparisons must be a list")
    comparisons = tuple(PairwisePreference.from_dict(item) for item in comparisons_raw)
    training = tuple(
        comparison
        for comparison, raw in zip(comparisons, comparisons_raw, strict=True)
        if raw.get("partition", "training") == "training"
    )
    heldout = tuple(
        comparison
        for comparison, raw in zip(comparisons, comparisons_raw, strict=True)
        if raw.get("partition") == "heldout"
    )
    config = context.get("preference_fit", {})
    if not isinstance(config, dict):
        raise ValueError("preference_fit must be an object")
    request = PreferenceFitRequest(
        training=training,
        heldout=heldout,
        minimum_comparisons=int(config.get("minimum_comparisons", 10)),
        minimum_heldout_comparisons=int(
            config.get("minimum_heldout_comparisons", 5)
        ),
        declared_baseline_accuracy=config.get("declared_baseline_accuracy"),
        criterion_id=criterion,
        bootstrap_replicates=int(config.get("bootstrap_replicates", 0)),
        bootstrap_seed=int(config.get("bootstrap_seed", 0)),
        require_scoped_validation=_strict_bool(
            config.get("require_scoped_validation", True),
            "preference_fit.require_scoped_validation",
        ),
        model_family=str(config.get("model_family", "DAVIDSON_V1")),
    )
    fit = fit_preference_model(request)
    validation_state = (
        "WITHHELD"
        if fit.status is PreferenceFitStatus.WITHHELD
        else "FAILED_BASELINE"
        if any("baseline" in note.casefold() for note in fit.validation_notes)
        else "VALIDATED_EXACT_SCOPE"
        if fit.validated
        else "DIAGNOSTIC"
    )
    if temporal.state == "HOLD" or temporal.safety_stop:
        validation_state = "WITHHELD"

    result_hash_payload: object = _fit_result_payload(fit)
    if criterion == "LIKING" and fit.status is not PreferenceFitStatus.WITHHELD:
        assessor_ids = tuple(
            sorted({item.assessor_id for item in comparisons if item.assessor_id is not None})
        )
        repeat_map = {
            str(item["comparison_id"]): str(item.get("repeat_id") or "R1")
            for item in comparisons_raw
        }
        repeat_ids = tuple(sorted(set(repeat_map.values())))
        timepoints = {item.time_seconds for item in comparisons}
        if len(timepoints) != 1:
            validation_state = "INVALID"
        else:
            protocol_payload = context.get("protocol_scope", {})
            protocol_sha256 = sha256_hex(canonical_json_bytes(protocol_payload))
            receipt = bind_preference_fit_evidence(
                request,
                fit,
                scope=HedonicScope(str(context.get("hedonic_scope", "OWNER"))),
                formula_build_sha256=str(context["formula_build_sha256"]),
                sample_sha256=tuple(digest for _, digest in execution.sample_sha256),
                protocol_sha256=protocol_sha256,
                assessor_ids=assessor_ids,
                repeat_ids=repeat_ids,
                comparison_repeat_ids=repeat_map,
                time_seconds=float(next(iter(timepoints))),
                schedule_sha256=analyze_execution_receipt(execution).schedule_sha256,
            )
            safety_events = context.get("safety_events", [])
            hedonic = evaluate_hedonic_evidence(
                HedonicEvidenceRequest(
                    criterion_id="LIKING",
                    scope=receipt.scope,
                    formula_build_sha256=receipt.formula_build_sha256,
                    sample_sha256=receipt.sample_sha256,
                    protocol_sha256=receipt.protocol_sha256,
                    assessor_ids=receipt.assessor_ids,
                    repeat_ids=receipt.repeat_ids,
                    time_seconds=receipt.time_seconds,
                    schedule_sha256=receipt.schedule_sha256,
                    fit_receipt=receipt,
                    safety_event_ids=tuple(
                        str(item.get("event_id")) for item in safety_events
                    ),
                )
            )
            validation_state = {
                HedonicEvidenceState.VALIDATED_EXACT_SCOPE: "VALIDATED_EXACT_SCOPE",
                HedonicEvidenceState.FAILED_HELDOUT_BASELINE: "FAILED_BASELINE",
                HedonicEvidenceState.DIAGNOSTIC: "DIAGNOSTIC",
                HedonicEvidenceState.INSUFFICIENT_EVIDENCE: "WITHHELD",
                HedonicEvidenceState.NOT_TESTED: "NOT_TESTED",
                HedonicEvidenceState.INVALID_OR_CONFOUNDED: "INVALID",
            }[hedonic.state]
            result_hash_payload = {
                "preference": _fit_result_payload(fit),
                "hedonic": hedonic.as_dict(),
            }
    heterogeneity = (
        max(fit.assessor_heterogeneity.values())
        if fit.assessor_heterogeneity
        else None
    )
    return CriterionFitPacketV1(
        temporal_evidence_sha256=temporal.record_sha256,
        comparison_payload_sha256=sha256_hex(canonical_json_bytes(comparisons_raw)),
        criterion=criterion,
        preference_result_sha256=sha256_hex(canonical_json_bytes(result_hash_payload)),
        validation_state=validation_state,
        utility_intervals=fit.utility_intervals,
        tie_rate=fit.tie_rate,
        assessor_heterogeneity=heterogeneity,
        order_effect=abs(fit.order_effect) if fit.order_effect is not None else None,
        next_pair=fit.next_comparison,
        test_only=execution.test_only,
    )


_HEDONIC_V2_POLICY_SHA256 = sha256_hex(
    canonical_json_bytes(
        {
            "policy": "HEDONIC_PREFERENCE_EXACT_SCOPE_V2",
            "model": "DAVIDSON_V1",
            "uncertainty": "ASSESSOR_CLUSTER",
            "validation": "GROUPED_MULTINOMIAL_PROPER_SCORING",
            "selection": "ZERO_OR_ONE_CONSTRAINED_PAIR",
        }
    )
)

_HEDONIC_V3_POLICY_SHA256 = sha256_hex(
    canonical_json_bytes(
        {
            "policy": "HEDONIC_PREFERENCE_EXACT_SCOPE_V3",
            "model": "DAVIDSON_V1",
            "item_binding": "ITEM_TO_BUILD_TO_SAMPLE_EXACT",
            "context_binding": "SUBSTRATE_APPLICATION_ENVIRONMENT_WEAR",
            "order": "REALIZED_PAIR_ORDER_AND_SEQUENCE",
            "uncertainty": "ASSESSOR_CLUSTER",
            "validation": "GROUP_ISOLATED_MULTINOMIAL_PROPER_SCORING",
            "selection": "ZERO_OR_ONE_CONSTRAINED_PAIR",
        }
    )
)


def _criterion_v2_hold(
    *,
    parent: CriterionFitPacketV1,
    execution: ExecutionReceiptV1,
    criterion: str,
    blockers: tuple[str, ...],
) -> CriterionFitPacketV2:
    input_sha256 = sha256_hex(
        canonical_json_bytes(
            {
                "execution_sha256": execution.record_sha256,
                "criterion_parent_sha256": parent.record_sha256,
                "criterion": criterion,
            }
        )
    )
    receipt = hold_receipt(
        module_id="hedonic_preference",
        exact_scope=f"{execution.record_sha256}/{criterion}",
        input_sha256=input_sha256,
        evidence_sha256=parent.preference_result_sha256,
        policy_sha256=_HEDONIC_V2_POLICY_SHA256,
        reasons=("V2_EVIDENCE_INCOMPLETE",),
        blockers=blockers,
        next_action=None,
    )
    return CriterionFitPacketV2(
        parent_v1=parent,
        preference_fit_evidence_v2_sha256=None,
        hedonic_state="WITHHELD",
        cluster_bootstrap_sha256=None,
        heldout_validation_sha256=None,
        transitivity_sha256=None,
        next_pair_sha256=None,
        evidence_delta_receipt=receipt,
        test_only=execution.test_only,
    )


def build_criterion_fit_packet_v2(
    execution: ExecutionReceiptV1,
    temporal: TemporalEvidencePacketV1,
    *,
    criterion: str,
) -> CriterionFitPacketV2:
    """Build a V2 proper-scoring liking packet or one fail-closed receipt."""

    parent = build_criterion_fit_packet(execution, temporal, criterion=criterion)
    criterion = criterion.strip().upper()
    if criterion != "LIKING":
        input_sha256 = sha256_hex(
            canonical_json_bytes(
                {
                    "execution_sha256": execution.record_sha256,
                    "criterion_parent_sha256": parent.record_sha256,
                    "criterion": criterion,
                }
            )
        )
        receipt = no_augmentation_receipt(
            module_id="hedonic_preference",
            exact_scope=f"{execution.record_sha256}/{criterion}",
            input_sha256=input_sha256,
            evidence_sha256=parent.preference_result_sha256,
            policy_sha256=_HEDONIC_V2_POLICY_SHA256,
            reasons=("NON_HEDONIC_CRITERION",),
        )
        return CriterionFitPacketV2(
            parent_v1=parent,
            preference_fit_evidence_v2_sha256=None,
            hedonic_state="NOT_TESTED",
            cluster_bootstrap_sha256=None,
            heldout_validation_sha256=None,
            transitivity_sha256=None,
            next_pair_sha256=None,
            evidence_delta_receipt=receipt,
            test_only=execution.test_only,
        )

    try:
        context = _execution_context(execution)
        comparisons_raw = context.get("comparisons", [])
        if not isinstance(comparisons_raw, list):
            raise ValueError("comparisons must be a list")
        comparisons = tuple(
            PairwisePreference.from_dict(item) for item in comparisons_raw
        )
        training = tuple(
            row
            for row in comparisons
            if (row.partition or "TRAINING").strip().upper() == "TRAINING"
        )
        heldout = tuple(
            row
            for row in comparisons
            if (row.partition or "").strip().upper() == "HELDOUT"
        )
        config = context.get("preference_fit", {})
        config_v2 = context.get("preference_fit_v2", {})
        if not isinstance(config, dict) or not isinstance(config_v2, dict):
            raise ValueError("preference fit configurations must be objects")
        request = PreferenceFitRequest(
            training=training,
            heldout=heldout,
            minimum_comparisons=_strict_int(
                config.get("minimum_comparisons", 10),
                "preference_fit.minimum_comparisons",
            ),
            minimum_heldout_comparisons=_strict_int(
                config.get("minimum_heldout_comparisons", 5),
                "preference_fit.minimum_heldout_comparisons",
            ),
            declared_baseline_accuracy=(
                None
                if config.get("declared_baseline_accuracy") is None
                else _strict_real(
                    config["declared_baseline_accuracy"],
                    "preference_fit.declared_baseline_accuracy",
                )
            ),
            regularization=_strict_real(
                config.get("regularization", 0.1),
                "preference_fit.regularization",
            ),
            maximum_iterations=_strict_int(
                config.get("maximum_iterations", 2000),
                "preference_fit.maximum_iterations",
            ),
            criterion_id=criterion,
            bootstrap_replicates=_strict_int(
                config.get("bootstrap_replicates", 0),
                "preference_fit.bootstrap_replicates",
            ),
            bootstrap_seed=_strict_int(
                config.get("bootstrap_seed", 0),
                "preference_fit.bootstrap_seed",
            ),
            require_scoped_validation=_strict_bool(
                config.get("require_scoped_validation", True),
                "preference_fit.require_scoped_validation",
            ),
            model_family=_strict_text(
                config.get("model_family", "DAVIDSON_V1"),
                "preference_fit.model_family",
            ),
        )
        fit = fit_preference_model(request)
        protocol_payload = context.get("protocol_scope", {})
        protocol_sha256 = sha256_hex(canonical_json_bytes(protocol_payload))
        assessor_ids = tuple(
            sorted(
                {
                    item.assessor_id
                    for item in comparisons
                    if item.assessor_id is not None
                }
            )
        )
        repeat_map = {}
        for raw in comparisons_raw:
            comparison_id = _strict_text(
                raw.get("comparison_id"),
                "comparisons.comparison_id",
            )
            repeat_value = raw.get("repeat_id")
            repeat_map[comparison_id] = (
                "R1"
                if repeat_value is None
                else _strict_text(repeat_value, "comparisons.repeat_id")
            )
        repeat_ids = tuple(sorted(set(repeat_map.values())))
        timepoints = {item.time_seconds for item in comparisons}
        if len(timepoints) != 1:
            raise ValueError("V2 liking comparisons must isolate one timepoint")
        parent_evidence = bind_preference_fit_evidence(
            request,
            fit,
            scope=HedonicScope(
                _strict_text(
                    context.get("hedonic_scope", "OWNER"),
                    "hedonic_scope",
                )
            ),
            formula_build_sha256=context["formula_build_sha256"],
            sample_sha256=tuple(digest for _, digest in execution.sample_sha256),
            protocol_sha256=protocol_sha256,
            assessor_ids=assessor_ids,
            repeat_ids=repeat_ids,
            comparison_repeat_ids=repeat_map,
            time_seconds=float(next(iter(timepoints))),
            schedule_sha256=analyze_execution_receipt(execution).schedule_sha256,
        )
        items = tuple(
            sorted(
                {row.left_item for row in training}
                | {row.right_item for row in training}
            )
        )
        davidson = fit_davidson(
            items=items,
            comparisons=training,
            config=DavidsonFitConfig(
                regularization=request.regularization,
                maximum_iterations=request.maximum_iterations,
            ),
        )
        evidence_v2 = bind_preference_fit_evidence_v2(
            parent_evidence,
            davidson_fit=davidson,
            construct_registry_sha256=config_v2["construct_registry_sha256"],
            criterion_wording_sha256=config_v2["criterion_wording_sha256"],
            source_transfer_sha256=config_v2["source_transfer_sha256"],
            source_transfer_state=config_v2["source_transfer_state"],
            bootstrap_config=ClusterBootstrapConfig(
                replicates=_strict_int(
                    config_v2.get("bootstrap_replicates", 200),
                    "preference_fit_v2.bootstrap_replicates",
                ),
                seed=_strict_int(
                    config_v2.get("bootstrap_seed", 0),
                    "preference_fit_v2.bootstrap_seed",
                ),
                regularization=request.regularization,
                maximum_iterations=request.maximum_iterations,
            ),
            heldout_config=HeldoutValidationConfig(
                split_unit=_strict_text(
                    config_v2.get("split_unit", "ASSESSOR"),
                    "preference_fit_v2.split_unit",
                ),
                practical_margin=_strict_real(
                    config_v2.get("practical_margin", 0.0),
                    "preference_fit_v2.practical_margin",
                ),
                bootstrap_replicates=_strict_int(
                    config_v2.get("heldout_bootstrap_replicates", 200),
                    "preference_fit_v2.heldout_bootstrap_replicates",
                ),
                seed=_strict_int(
                    config_v2.get("heldout_seed", 0),
                    "preference_fit_v2.heldout_seed",
                ),
            ),
            transitivity_config=TransitivityConfig(),
            eligible_next_pairs=tuple(itertools.combinations(items, 2)),
            next_pair_constraints=NextPairConstraints(
                decision_resolved=_strict_bool(
                    config_v2.get("decision_resolved", False),
                    "preference_fit_v2.decision_resolved",
                )
            ),
        )
        safety_events = context.get("safety_events", [])
        if not isinstance(safety_events, list) or any(
            not isinstance(item, dict) for item in safety_events
        ):
            raise TypeError("safety_events must be a list of objects")
        safety_event_ids = tuple(
            _strict_text(item.get("event_id"), "safety_events.event_id")
            for item in safety_events
        )
        hedonic = evaluate_hedonic_evidence(
            HedonicEvidenceRequest(
                criterion_id="LIKING",
                scope=evidence_v2.scope,
                formula_build_sha256=evidence_v2.formula_build_sha256,
                sample_sha256=evidence_v2.sample_sha256,
                protocol_sha256=evidence_v2.protocol_sha256,
                assessor_ids=evidence_v2.assessor_ids,
                repeat_ids=evidence_v2.repeat_ids,
                time_seconds=evidence_v2.time_seconds,
                schedule_sha256=evidence_v2.schedule_sha256,
                fit_receipt=evidence_v2,
                safety_event_ids=safety_event_ids,
            )
        )
    except (KeyError, TypeError, ValueError) as exc:
        return _criterion_v2_hold(
            parent=parent,
            execution=execution,
            criterion=criterion,
            blockers=(f"V2 preference evidence could not be bound: {exc}",),
        )

    input_sha256 = sha256_hex(
        canonical_json_bytes(
            {
                "execution_sha256": execution.record_sha256,
                "temporal_sha256": temporal.record_sha256,
                "criterion": criterion,
            }
        )
    )
    source_bindings = tuple(
        sorted(
            {
                evidence_v2.record_sha256,
                evidence_v2.construct_registry_sha256,
                evidence_v2.source_transfer_sha256,
            }
        )
    )
    if hedonic.state is HedonicEvidenceState.VALIDATED_EXACT_SCOPE:
        delta = DecisionDeltaV1(
            delta_id=f"HEDONIC:{execution.record_sha256[:12]}",
            decision_effect=(
                "Use the scoped liking utilities and proper held-out validation only "
                "for the bound protocol population."
            ),
            observed_facts=(
                f"heldout_count={evidence_v2.heldout_validation.heldout_count}",
                f"tie_rate={fit.tie_rate:.12g}",
                f"split_unit={evidence_v2.heldout_validation.split_unit}",
            ),
            derived_calculations=(
                "model_family=DAVIDSON_V1",
                f"log_loss={evidence_v2.heldout_validation.multinomial_log_loss:.12g}",
                "cluster_method=ASSESSOR_CLUSTER_PERCENTILE",
            ),
            hypotheses=(),
            forbidden_inferences=(
                "The result is not a universal beauty or formula-composition score.",
                "The result grants no formula, safety, purchase, release, or runtime authority.",
            ),
        )
        delta_receipt = EvidenceDeltaReceiptV1(
            module_id="hedonic_preference",
            exact_scope=f"{execution.record_sha256}/LIKING",
            state=EvidenceAugmentationState.AUGMENT,
            input_sha256=input_sha256,
            evidence_sha256=evidence_v2.record_sha256,
            policy_sha256=_HEDONIC_V2_POLICY_SHA256,
            source_binding_sha256=source_bindings,
            reason_codes=("PROPER_SCOPED_LIKING_EVIDENCE",),
            delta=delta,
            blockers=(),
            next_action=(
                None
                if evidence_v2.next_pair.selected_pair is None
                else "COMPARE:" + ":".join(evidence_v2.next_pair.selected_pair)
            ),
        )
    elif (
        any("order" in value.casefold() for value in hedonic.blockers)
        and evidence_v2.next_pair.selected_pair is None
    ):
        delta_receipt = no_augmentation_receipt(
            module_id="hedonic_preference",
            exact_scope=f"{execution.record_sha256}/LIKING",
            input_sha256=input_sha256,
            evidence_sha256=evidence_v2.record_sha256,
            policy_sha256=_HEDONIC_V2_POLICY_SHA256,
            source_binding_sha256=source_bindings,
            reasons=("ORDER_CONFOUND_ALREADY_IDENTIFIED",),
        )
    else:
        blockers = hedonic.blockers or hedonic.limitations or (hedonic.state.value,)
        delta_receipt = hold_receipt(
            module_id="hedonic_preference",
            exact_scope=f"{execution.record_sha256}/LIKING",
            input_sha256=input_sha256,
            evidence_sha256=evidence_v2.record_sha256,
            policy_sha256=_HEDONIC_V2_POLICY_SHA256,
            source_binding_sha256=source_bindings,
            reasons=(hedonic.state.value,),
            blockers=tuple(blockers),
            next_action=(
                None
                if evidence_v2.next_pair.selected_pair is None
                else "COMPARE:" + ":".join(evidence_v2.next_pair.selected_pair)
            ),
        )
    state = {
        HedonicEvidenceState.VALIDATED_EXACT_SCOPE: "VALIDATED_EXACT_SCOPE",
        HedonicEvidenceState.FAILED_HELDOUT_BASELINE: "FAILED_BASELINE",
        HedonicEvidenceState.DIAGNOSTIC: "DIAGNOSTIC",
        HedonicEvidenceState.INSUFFICIENT_EVIDENCE: "WITHHELD",
        HedonicEvidenceState.NOT_TESTED: "NOT_TESTED",
        HedonicEvidenceState.INVALID_OR_CONFOUNDED: "INVALID",
    }[hedonic.state]
    return CriterionFitPacketV2(
        parent_v1=parent,
        preference_fit_evidence_v2_sha256=evidence_v2.record_sha256,
        hedonic_state=state,
        cluster_bootstrap_sha256=evidence_v2.cluster_bootstrap.receipt_sha256,
        heldout_validation_sha256=evidence_v2.heldout_validation.receipt_sha256,
        transitivity_sha256=sha256_hex(evidence_v2.transitivity.canonical_bytes()),
        next_pair_sha256=sha256_hex(evidence_v2.next_pair.canonical_bytes()),
        evidence_delta_receipt=delta_receipt,
        test_only=execution.test_only,
    )


def _criterion_v3_hold(
    *,
    parent: CriterionFitPacketV2,
    execution: ExecutionReceiptV1,
    criterion: str,
    blockers: tuple[str, ...],
) -> CriterionFitPacketV3:
    input_sha256 = sha256_hex(
        canonical_json_bytes(
            {
                "execution_sha256": execution.record_sha256,
                "criterion_parent_v2_sha256": parent.record_sha256,
                "criterion": criterion,
            }
        )
    )
    receipt = hold_receipt(
        module_id="hedonic_preference_v3",
        exact_scope=f"{execution.record_sha256}/{criterion}",
        input_sha256=input_sha256,
        evidence_sha256=(
            parent.preference_fit_evidence_v2_sha256
            or parent.parent_v1.preference_result_sha256
        ),
        policy_sha256=_HEDONIC_V3_POLICY_SHA256,
        reasons=("V3_EVIDENCE_INCOMPLETE",),
        blockers=blockers,
        next_action=None,
    )
    return CriterionFitPacketV3(
        parent_v2=parent,
        preference_fit_evidence_v3_sha256=None,
        evaluation_context_sha256=None,
        item_bindings_sha256=None,
        order_carryover_sha256=None,
        adequacy_contract_sha256=None,
        hedonic_state="WITHHELD",
        evidence_delta_receipt=receipt,
        test_only=execution.test_only,
    )


def build_criterion_fit_packet_v3(
    execution: ExecutionReceiptV1,
    temporal: TemporalEvidencePacketV1,
    *,
    criterion: str,
) -> CriterionFitPacketV3:
    """Build a promotion-capable V3 packet or one explicit fail-closed packet."""

    parent = build_criterion_fit_packet_v2(
        execution,
        temporal,
        criterion=criterion,
    )
    criterion = criterion.strip().upper()
    if criterion != "LIKING":
        input_sha256 = sha256_hex(
            canonical_json_bytes(
                {
                    "execution_sha256": execution.record_sha256,
                    "criterion_parent_v2_sha256": parent.record_sha256,
                    "criterion": criterion,
                }
            )
        )
        receipt = no_augmentation_receipt(
            module_id="hedonic_preference_v3",
            exact_scope=f"{execution.record_sha256}/{criterion}",
            input_sha256=input_sha256,
            evidence_sha256=parent.parent_v1.preference_result_sha256,
            policy_sha256=_HEDONIC_V3_POLICY_SHA256,
            reasons=("NON_HEDONIC_CRITERION",),
        )
        return CriterionFitPacketV3(
            parent_v2=parent,
            preference_fit_evidence_v3_sha256=None,
            evaluation_context_sha256=None,
            item_bindings_sha256=None,
            order_carryover_sha256=None,
            adequacy_contract_sha256=None,
            hedonic_state="NOT_TESTED",
            evidence_delta_receipt=receipt,
            test_only=execution.test_only,
        )

    try:
        context = _execution_context(execution)
        comparisons_raw = context.get("comparisons", [])
        if not isinstance(comparisons_raw, list):
            raise ValueError("comparisons must be a list")
        comparisons = tuple(
            PairwisePreference.from_dict(item) for item in comparisons_raw
        )
        training = tuple(
            row
            for row in comparisons
            if (row.partition or "TRAINING").strip().upper() == "TRAINING"
        )
        heldout = tuple(
            row
            for row in comparisons
            if (row.partition or "").strip().upper() == "HELDOUT"
        )
        config = context.get("preference_fit", {})
        config_v2 = context.get("preference_fit_v2", {})
        config_v3 = context.get("preference_fit_v3", {})
        if not all(
            isinstance(value, dict) for value in (config, config_v2, config_v3)
        ):
            raise ValueError("preference fit configurations must be objects")
        request = PreferenceFitRequest(
            training=training,
            heldout=heldout,
            minimum_comparisons=_strict_int(
                config.get("minimum_comparisons", 10),
                "preference_fit.minimum_comparisons",
            ),
            minimum_heldout_comparisons=_strict_int(
                config.get("minimum_heldout_comparisons", 5),
                "preference_fit.minimum_heldout_comparisons",
            ),
            declared_baseline_accuracy=(
                None
                if config.get("declared_baseline_accuracy") is None
                else _strict_real(
                    config["declared_baseline_accuracy"],
                    "preference_fit.declared_baseline_accuracy",
                )
            ),
            regularization=_strict_real(
                config.get("regularization", 0.1),
                "preference_fit.regularization",
            ),
            maximum_iterations=_strict_int(
                config.get("maximum_iterations", 2000),
                "preference_fit.maximum_iterations",
            ),
            criterion_id=criterion,
            bootstrap_replicates=_strict_int(
                config.get("bootstrap_replicates", 0),
                "preference_fit.bootstrap_replicates",
            ),
            bootstrap_seed=_strict_int(
                config.get("bootstrap_seed", 0),
                "preference_fit.bootstrap_seed",
            ),
            require_scoped_validation=_strict_bool(
                config.get("require_scoped_validation", True),
                "preference_fit.require_scoped_validation",
            ),
            model_family=_strict_text(
                config.get("model_family", "DAVIDSON_V1"),
                "preference_fit.model_family",
            ),
        )
        fit = fit_preference_model(request)
        protocol_payload = context.get("protocol_scope", {})
        protocol_sha256 = sha256_hex(canonical_json_bytes(protocol_payload))
        assessor_ids = tuple(
            sorted(
                {
                    row.assessor_id
                    for row in comparisons
                    if row.assessor_id is not None
                }
            )
        )
        repeat_map = {}
        for raw in comparisons_raw:
            comparison_id = _strict_text(
                raw.get("comparison_id"),
                "comparisons.comparison_id",
            )
            repeat_value = raw.get("repeat_id")
            repeat_map[comparison_id] = (
                "R1"
                if repeat_value is None
                else _strict_text(repeat_value, "comparisons.repeat_id")
            )
        repeat_ids = tuple(sorted(set(repeat_map.values())))
        timepoints = {row.time_seconds for row in comparisons}
        if len(timepoints) != 1:
            raise ValueError("V3 liking comparisons must isolate one timepoint")
        parent_evidence = bind_preference_fit_evidence(
            request,
            fit,
            scope=HedonicScope(
                _strict_text(
                    context.get("hedonic_scope", "OWNER"),
                    "hedonic_scope",
                )
            ),
            formula_build_sha256=context["formula_build_sha256"],
            sample_sha256=tuple(digest for _, digest in execution.sample_sha256),
            protocol_sha256=protocol_sha256,
            assessor_ids=assessor_ids,
            repeat_ids=repeat_ids,
            comparison_repeat_ids=repeat_map,
            time_seconds=float(next(iter(timepoints))),
            schedule_sha256=analyze_execution_receipt(execution).schedule_sha256,
        )
        items = tuple(
            sorted(
                {row.left_item for row in training}
                | {row.right_item for row in training}
            )
        )
        davidson = fit_davidson(
            items=items,
            comparisons=training,
            config=DavidsonFitConfig(
                regularization=request.regularization,
                maximum_iterations=request.maximum_iterations,
            ),
        )
        evidence_v2 = bind_preference_fit_evidence_v2(
            parent_evidence,
            davidson_fit=davidson,
            construct_registry_sha256=config_v2["construct_registry_sha256"],
            criterion_wording_sha256=config_v2["criterion_wording_sha256"],
            source_transfer_sha256=config_v2["source_transfer_sha256"],
            source_transfer_state=config_v2["source_transfer_state"],
            bootstrap_config=ClusterBootstrapConfig(
                replicates=_strict_int(
                    config_v2.get("bootstrap_replicates", 200),
                    "preference_fit_v2.bootstrap_replicates",
                ),
                seed=_strict_int(
                    config_v2.get("bootstrap_seed", 0),
                    "preference_fit_v2.bootstrap_seed",
                ),
                regularization=request.regularization,
                maximum_iterations=request.maximum_iterations,
            ),
            heldout_config=HeldoutValidationConfig(
                split_unit=_strict_text(
                    config_v2.get("split_unit", "ASSESSOR"),
                    "preference_fit_v2.split_unit",
                ),
                practical_margin=_strict_real(
                    config_v2.get("practical_margin", 0.0),
                    "preference_fit_v2.practical_margin",
                ),
                bootstrap_replicates=_strict_int(
                    config_v2.get("heldout_bootstrap_replicates", 200),
                    "preference_fit_v2.heldout_bootstrap_replicates",
                ),
                seed=_strict_int(
                    config_v2.get("heldout_seed", 0),
                    "preference_fit_v2.heldout_seed",
                ),
            ),
            transitivity_config=TransitivityConfig(),
            eligible_next_pairs=tuple(itertools.combinations(items, 2)),
            next_pair_constraints=NextPairConstraints(
                decision_resolved=_strict_bool(
                    config_v2.get("decision_resolved", False),
                    "preference_fit_v2.decision_resolved",
                )
            ),
        )
        if parent.preference_fit_evidence_v2_sha256 != evidence_v2.record_sha256:
            raise ValueError(
                "parent V2 packet does not match reconstructed V2 evidence"
            )

        raw_bindings = config_v3.get("item_bindings")
        raw_context = config_v3.get("evaluation_context")
        raw_adequacy = config_v3.get("adequacy_contract")
        raw_order = config_v3.get("order_carryover", {})
        if not isinstance(raw_bindings, list):
            raise ValueError("V3 item_bindings must be a list")
        if not all(
            isinstance(value, dict)
            for value in (raw_context, raw_adequacy, raw_order)
        ):
            raise ValueError(
                "V3 evaluation_context, adequacy_contract, and order_carryover "
                "must be objects"
            )
        item_bindings = tuple(
            PreferenceItemEvidenceBinding(
                item_id=value["item_id"],
                build_sha256=value["build_sha256"],
                sample_sha256=value["sample_sha256"],
                provenance_manifest_sha256=value["provenance_manifest_sha256"],
                sampling_or_dose_receipt_sha256=value[
                    "sampling_or_dose_receipt_sha256"
                ],
                batch_id=value["batch_id"],
            )
            for value in raw_bindings
        )
        evaluation_context = SensoryEvaluationContext(
            context_id=raw_context["context_id"],
            substrate=EvaluationSubstrate(raw_context["substrate"]),
            application_protocol_sha256=raw_context[
                "application_protocol_sha256"
            ],
            environment_sha256=raw_context["environment_sha256"],
            maturation_state_sha256=raw_context["maturation_state_sha256"],
            carryover_control_sha256=raw_context["carryover_control_sha256"],
            carryover_qualified=_strict_bool(
                raw_context["carryover_qualified"],
                "preference_fit_v3.evaluation_context.carryover_qualified",
            ),
            apparatus_sha256=(
                raw_context["apparatus_sha256"]
                if raw_context.get("apparatus_sha256") is not None
                else None
            ),
            wearer_id=(
                raw_context["wearer_id"]
                if raw_context.get("wearer_id") is not None
                else None
            ),
            body_odor_context_sha256=(
                raw_context["body_odor_context_sha256"]
                if raw_context.get("body_odor_context_sha256") is not None
                else None
            ),
        )
        adequacy_contract = PreferenceEvidenceAdequacyContract(
            analysis_plan_sha256=raw_adequacy["analysis_plan_sha256"],
            sampling_frame_sha256=raw_adequacy["sampling_frame_sha256"],
            minimum_assessors=_strict_int(
                raw_adequacy["minimum_assessors"],
                "preference_fit_v3.adequacy_contract.minimum_assessors",
            ),
            minimum_directional_training_comparisons=_strict_int(
                raw_adequacy["minimum_directional_training_comparisons"],
                "preference_fit_v3.adequacy_contract.minimum_directional_training_comparisons",
            ),
            minimum_heldout_groups=_strict_int(
                raw_adequacy["minimum_heldout_groups"],
                "preference_fit_v3.adequacy_contract.minimum_heldout_groups",
            ),
            minimum_heldout_comparisons=_strict_int(
                raw_adequacy["minimum_heldout_comparisons"],
                "preference_fit_v3.adequacy_contract.minimum_heldout_comparisons",
            ),
            minimum_cluster_bootstrap_replicates=_strict_int(
                raw_adequacy["minimum_cluster_bootstrap_replicates"],
                "preference_fit_v3.adequacy_contract.minimum_cluster_bootstrap_replicates",
            ),
            minimum_heldout_bootstrap_replicates=_strict_int(
                raw_adequacy["minimum_heldout_bootstrap_replicates"],
                "preference_fit_v3.adequacy_contract.minimum_heldout_bootstrap_replicates",
            ),
        )
        evidence_v3 = bind_preference_fit_evidence_v3(
            evidence_v2,
            focal_item_id=config_v3["focal_item_id"],
            item_bindings=item_bindings,
            evaluation_context=evaluation_context,
            adequacy_contract=adequacy_contract,
            order_carryover_config=OrderCarryoverConfig(
                maximum_pair_order_count_difference=_strict_int(
                    raw_order.get("maximum_pair_order_count_difference", 1),
                    "preference_fit_v3.order_carryover.maximum_pair_order_count_difference",
                ),
                maximum_absolute_first_position_effect=_strict_real(
                    raw_order.get(
                        "maximum_absolute_first_position_effect", 0.25
                    ),
                    "preference_fit_v3.order_carryover.maximum_absolute_first_position_effect",
                ),
                require_qualified_carryover=_strict_bool(
                    raw_order.get("require_qualified_carryover", True),
                    "preference_fit_v3.order_carryover.require_qualified_carryover",
                ),
            ),
        )
        safety_events = context.get("safety_events", [])
        if not isinstance(safety_events, list) or any(
            not isinstance(item, dict) for item in safety_events
        ):
            raise TypeError("safety_events must be a list of objects")
        safety_event_ids = tuple(
            _strict_text(item.get("event_id"), "safety_events.event_id")
            for item in safety_events
        )
        hedonic = evaluate_hedonic_evidence(
            HedonicEvidenceRequest(
                criterion_id="LIKING",
                scope=evidence_v3.scope,
                formula_build_sha256=evidence_v3.formula_build_sha256,
                sample_sha256=evidence_v3.sample_sha256,
                protocol_sha256=evidence_v3.protocol_sha256,
                assessor_ids=evidence_v3.assessor_ids,
                repeat_ids=evidence_v3.repeat_ids,
                time_seconds=evidence_v3.time_seconds,
                schedule_sha256=evidence_v3.schedule_sha256,
                fit_receipt=evidence_v3,
                safety_event_ids=safety_event_ids,
                focal_item_id=evidence_v3.focal_item_id,
                evaluation_context_sha256=evaluation_context.record_sha256,
            )
        )
    except (KeyError, TypeError, ValueError) as exc:
        return _criterion_v3_hold(
            parent=parent,
            execution=execution,
            criterion=criterion,
            blockers=(f"V3 preference evidence could not be bound: {exc}",),
        )

    input_sha256 = sha256_hex(
        canonical_json_bytes(
            {
                "execution_sha256": execution.record_sha256,
                "temporal_sha256": temporal.record_sha256,
                "criterion": criterion,
                "parent_v2_sha256": parent.record_sha256,
            }
        )
    )
    adequacy_sha256 = sha256_hex(
        canonical_json_bytes(evidence_v3.adequacy_contract.as_dict())
    )
    source_bindings = tuple(
        sorted(
            {
                evidence_v3.record_sha256,
                evidence_v3.parent_v2.record_sha256,
                evidence_v3.item_bindings_sha256,
                evidence_v3.evaluation_context.record_sha256,
                evidence_v3.order_carryover.receipt_sha256,
                adequacy_sha256,
            }
        )
    )
    if hedonic.state is HedonicEvidenceState.VALIDATED_EXACT_SCOPE:
        delta = DecisionDeltaV1(
            delta_id=f"HEDONIC-V3:{execution.record_sha256[:12]}",
            decision_effect=(
                "Use the exact-scope liking evidence only for the bound focal item, "
                "physical samples, context, assessors, and criterion."
            ),
            observed_facts=(
                f"heldout_count={evidence_v3.parent_v2.heldout_validation.heldout_count}",
                f"tie_rate={fit.tie_rate:.12g}",
                f"focal_item={evidence_v3.focal_item_id}",
                f"substrate={evidence_v3.evaluation_context.substrate.value}",
            ),
            derived_calculations=(
                "model_family=DAVIDSON_V1",
                "validation=GROUP_ISOLATED_MULTINOMIAL_PROPER_SCORING",
                "binding=ITEM_BUILD_SAMPLE_CONTEXT_V3",
            ),
            hypotheses=(),
            forbidden_inferences=(
                "The result is not universal beauty or a composition-derived score.",
                "It does not transfer across substrate, wearer, body odor, protocol, or time.",
                "It grants no formula, safety, purchase, compounding, release, or runtime authority.",
            ),
        )
        delta_receipt = EvidenceDeltaReceiptV1(
            module_id="hedonic_preference_v3",
            exact_scope=f"{execution.record_sha256}/LIKING",
            state=EvidenceAugmentationState.AUGMENT,
            input_sha256=input_sha256,
            evidence_sha256=evidence_v3.record_sha256,
            policy_sha256=_HEDONIC_V3_POLICY_SHA256,
            source_binding_sha256=source_bindings,
            reason_codes=("FULLY_BOUND_EXACT_SCOPE_LIKING_EVIDENCE",),
            delta=delta,
            blockers=(),
            next_action=(
                None
                if evidence_v3.parent_v2.next_pair.selected_pair is None
                else "COMPARE:"
                + ":".join(evidence_v3.parent_v2.next_pair.selected_pair)
            ),
        )
    else:
        blockers = hedonic.blockers or hedonic.limitations or (hedonic.state.value,)
        delta_receipt = hold_receipt(
            module_id="hedonic_preference_v3",
            exact_scope=f"{execution.record_sha256}/LIKING",
            input_sha256=input_sha256,
            evidence_sha256=evidence_v3.record_sha256,
            policy_sha256=_HEDONIC_V3_POLICY_SHA256,
            source_binding_sha256=source_bindings,
            reasons=(hedonic.state.value,),
            blockers=tuple(blockers),
            next_action=(
                None
                if evidence_v3.parent_v2.next_pair.selected_pair is None
                else "COMPARE:"
                + ":".join(evidence_v3.parent_v2.next_pair.selected_pair)
            ),
        )
    state = {
        HedonicEvidenceState.VALIDATED_EXACT_SCOPE: "VALIDATED_EXACT_SCOPE",
        HedonicEvidenceState.FAILED_HELDOUT_BASELINE: "FAILED_BASELINE",
        HedonicEvidenceState.DIAGNOSTIC: "DIAGNOSTIC",
        HedonicEvidenceState.INSUFFICIENT_EVIDENCE: "WITHHELD",
        HedonicEvidenceState.NOT_TESTED: "NOT_TESTED",
        HedonicEvidenceState.INVALID_OR_CONFOUNDED: "INVALID",
    }[hedonic.state]
    return CriterionFitPacketV3(
        parent_v2=parent,
        preference_fit_evidence_v3_sha256=evidence_v3.record_sha256,
        evaluation_context_sha256=evidence_v3.evaluation_context.record_sha256,
        item_bindings_sha256=evidence_v3.item_bindings_sha256,
        order_carryover_sha256=evidence_v3.order_carryover.receipt_sha256,
        adequacy_contract_sha256=adequacy_sha256,
        hedonic_state=state,
        evidence_delta_receipt=delta_receipt,
        test_only=execution.test_only,
    )


__all__ = [
    "analyze_execution_receipt",
    "audit_execution_receipt_v2",
    "build_criterion_fit_packet",
    "build_criterion_fit_packet_v2",
    "build_criterion_fit_packet_v3",
    "build_temporal_packet",
    "compile_architectural_delta",
    "compile_architectural_delta_v2",
    "export_backend_lab_payloads",
]
