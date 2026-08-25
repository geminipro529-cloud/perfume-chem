"""Pure adapters between SolForge records and existing evidence engines."""

from __future__ import annotations

import hashlib
import itertools
from pathlib import Path
from typing import Any

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.hedonic_evidence import (
    HedonicEvidenceRequest,
    HedonicEvidenceState,
    HedonicScope,
    bind_preference_fit_evidence,
    evaluate_hedonic_evidence,
)
from engine.perception.architectural_delta import (
    ArchitecturalDeltaCandidate,
    ArchitecturalDeltaFamily,
    ArchitecturalDeltaKind,
    ArchitecturalDeltaRequest,
    ArchitecturalDeltaState,
    _load_execution_inventory_catalog,
    evaluate_architectural_delta,
)
from engine.preference import (
    PairwisePreference,
    PreferenceFitRequest,
    PreferenceFitStatus,
    fit_preference_model,
)
from engine.sensory.ledger import (
    SensoryProtocolScope,
    SensorySafetyEvent,
    TemporalEvidenceRequest,
    TemporalEvidenceResult,
    TemporalEvidenceState,
    TemporalObservationCell,
    analyze_temporal_evidence,
)
from engine.sensory.order_balance import PresentationSchedule
from engine.solforge.contracts import (
    CompilationState,
    CompiledArmV1,
    CompiledExperimentV1,
    CriterionFitPacketV1,
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
    )


def analyze_execution_receipt(
    execution: ExecutionReceiptV1,
) -> TemporalEvidenceResult:
    """Analyze only observation cells explicitly bound into an execution receipt."""

    context = _execution_context(execution)
    scope = _scope_from_dict(context.get("protocol_scope"))
    schedule = _schedule_from_dict(context.get("schedule"))
    if set(scope.sample_ids) != {sample_id for sample_id, _ in execution.sample_sha256}:
        raise ValueError("protocol samples do not match the execution receipt")
    cells_raw = context.get("observations", [])
    safety_raw = context.get("safety_events", [])
    if not isinstance(cells_raw, list) or not isinstance(safety_raw, list):
        raise ValueError("observations and safety_events must be lists")
    return analyze_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=tuple(TemporalObservationCell.from_dict(item) for item in cells_raw),
            safety_events=tuple(SensorySafetyEvent.from_dict(item) for item in safety_raw),
        )
    )


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
        require_scoped_validation=bool(config.get("require_scoped_validation", True)),
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


__all__ = [
    "analyze_execution_receipt",
    "build_criterion_fit_packet",
    "build_temporal_packet",
    "compile_architectural_delta",
    "export_backend_lab_payloads",
]
