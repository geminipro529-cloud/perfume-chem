"""Runtime-safe adapter for the admitted Architectural Delta engine only."""

from __future__ import annotations

import hashlib
import itertools
from pathlib import Path

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.perception.architectural_delta import (
    ArchitecturalDeltaCandidate,
    ArchitecturalDeltaFamily,
    ArchitecturalDeltaKind,
    ArchitecturalDeltaRequest,
    ArchitecturalDeltaState,
    ComparisonClosureV1,
    _load_execution_inventory_catalog,
    evaluate_architectural_delta,
)
from engine.solforge.contracts import (
    CompilationState,
    CompiledArmV1,
    CompiledExperimentV1,
    SolForgeCaseState,
    SolForgeCaseV1,
    SolHypothesisSetV1,
    SolHypothesisV1,
)
from engine.solforge.hypotheses import validate_hypothesis_set

_EXCEPTION_MUSKS = ("tonalide", "macrolide", "musk ketone")
_MUSK_MARKERS = (
    "musk",
    "habanolide",
    "romandolide",
    "ambrettolide",
    "tonalide",
    "ethylene brassylate",
    "macrolide",
)
_CITRUS_MARKERS = (
    "citrus",
    "lemon",
    "lime",
    "orange",
    "bergamot",
    "grapefruit",
    "neroli",
    "mandarin",
    "citron",
)
_CRITERIA = ("TARGET_FIDELITY", "DEPTH", "RICHNESS", "LIKING")


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
    if not isinstance(materials, list):
        return frozenset()
    names = [
        item if isinstance(item, str) else item.get("name")
        for item in materials
        if isinstance(item, (str, dict))
    ]
    return frozenset(
        name.casefold() for name in names if isinstance(name, str)
    )


def _candidate(
    case: SolForgeCaseV1,
    hypothesis: SolHypothesisV1,
) -> ArchitecturalDeltaCandidate:
    family = _family(hypothesis.material_names)
    nary = hypothesis.intervention_kind == "NARY_DESIGN"
    material = " + ".join(hypothesis.material_names)
    if nary:
        factors = tuple(_arm_id(name) for name in hypothesis.material_names)
        arms = ("CONTROL", *factors, "_X_".join(factors))
        roles = tuple(
            role.strip()
            for role in hypothesis.target_function.split("|")
            if role.strip()
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
    if (
        exception
        and any(marker in target for marker in _EXCEPTION_MUSKS)
        and "exception" in hypothesis.rationale.casefold()
    ):
        exception_justification = hypothesis.rationale
    return ArchitecturalDeltaCandidate(
        candidate_id=hypothesis.hypothesis_id,
        material=material,
        family=family,
        kind=ArchitecturalDeltaKind(hypothesis.intervention_kind),
        priority_rank=hypothesis.rank,
        target_role=hypothesis.target_function,
        nonredundancy_evidence=hypothesis.rationale,
        loss_if_omitted=(
            f"The target loses the proposed {hypothesis.target_function} function."
        ),
        failure_mode=(
            "The intervention may blur or replace the declared target identity."
        ),
        controlled_arms=arms,
        evidence_refs=hypothesis.evidence_refs,
        redundant_with_current_build=any(
            name.casefold() in current for name in hypothesis.material_names
        ),
        primary_role="primary" in hypothesis.target_function.casefold(),
        target_explicitly_names_material=explicit_citrus,
        distinct_role_refs=roles,
        pairwise_nonredundancy_refs=(
            hypothesis.evidence_refs[:1]
            if len(roles) == 2
            else hypothesis.evidence_refs
        ),
        exception_justification=exception_justification,
        causal_design_sha256=(
            hypothesis.evidence_refs[0]
            if nary and hypothesis.evidence_refs
            else None
        ),
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
                {
                    "case_sha256": case.record_sha256,
                    "arm_id": arm_id,
                    "formula": formula,
                }
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
    """Compile zero or one target-faithful, inventory-bound experiment."""

    path = Path(case.inventory_path)
    if not path.is_file():
        return _hold(
            case,
            hypotheses,
            case.inventory_sha256,
            0,
            ("INVENTORY_PATH_MISSING",),
        )
    observed_sha256 = _file_sha256(path)
    if observed_sha256 != case.inventory_sha256:
        return _hold(
            case,
            hypotheses,
            observed_sha256,
            0,
            ("INVENTORY_HASH_MISMATCH",),
        )

    refresh_request = ArchitecturalDeltaRequest(
        target_identity=case.target_identity,
        ideal_formula_ref=f"case:{case.record_sha256}:ideal",
        current_build_ref=f"case:{case.record_sha256}:inventory-build",
        formula_lineage_sha256=case.formula_sha256,
        candidates=(),
        no_change_reason="No validated nonredundant intervention remains.",
    )
    refresh = evaluate_architectural_delta(
        refresh_request,
        inventory_workbook_path=str(path),
    )
    validation = validate_hypothesis_set(case, hypotheses)
    if case.state is not SolForgeCaseState.READY:
        return _hold(
            case,
            hypotheses,
            observed_sha256,
            refresh.inventory_source_row_count,
            ("CASE_NOT_READY",),
        )
    if not validation.valid:
        return _hold(
            case,
            hypotheses,
            observed_sha256,
            refresh.inventory_source_row_count,
            validation.blocker_codes,
        )
    if len(hypotheses.hypotheses) > 1:
        return _hold(
            case,
            hypotheses,
            observed_sha256,
            refresh.inventory_source_row_count,
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
            arms=(),
            blockers=(),
            inventory_statuses=(),
            omission_loss=None,
            failure_mode=None,
            next_comparison=None,
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
    delta = evaluate_architectural_delta(
        request,
        inventory_workbook_path=str(path),
    )
    if delta.state is not ArchitecturalDeltaState.PROPOSED:
        return _hold(
            case,
            hypotheses,
            observed_sha256,
            delta.inventory_source_row_count,
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
        arms=_compiled_arms(
            case,
            delta.controlled_arms,
            hypothesis.material_names,
        ),
        blockers=(),
        inventory_statuses=statuses,
        omission_loss=candidate.loss_if_omitted,
        failure_mode=candidate.failure_mode,
        next_comparison=delta.next_comparison,
    )


def export_backend_lab_payloads(
    experiment: CompiledExperimentV1,
) -> dict[str, object]:
    """Return deterministic drafts without API, database, or lab action."""

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


__all__ = ["compile_architectural_delta", "export_backend_lab_payloads"]
