"""Read-only Checkpoint 8 sensory-evidence intake for R6.

The evaluator verifies the Checkpoint 7 abstention, the governed human-data
scope boundaries, the empty exact-scope hedonic platform, and the unlocked C0
panel draft.  It does not authorize a study, recruit participants, create a
human observation, train or calibrate a model, rank a formula, compound a
sample, or grant safety or release authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from engine.calibration.hashing import stable_portable_file_hash
from engine.experiments.checkpoint7_readiness import (
    Checkpoint7ContractError,
    evaluate_r6_checkpoint7_readiness,
)
from engine.formulation_intelligence.contracts import AssessmentScope
from engine.formulation_intelligence.hedonic_platform import (
    HedonicEvidencePlatform,
    assess_hedonic_platform,
)
from engine.hedonic_model import score_hedonic
from engine.sensory.panel_contract import (
    REQUIRED_BINDING_IDS,
    BindingState,
    C0ExitDecision,
    GateAuthority,
    build_c0_construction_lexicon,
    build_c0_protocol_draft,
    evaluate_c0_exit,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r6_cp8_sensory_evidence_intake_20261009.json"
)

_SCHEMA_VERSION = "lavande-ambre-profond-r6-cp8-sensory-evidence-intake-v2"
_PROTOCOL_STATE = "FROZEN_NONEXECUTING_SENSORY_EVIDENCE_INTAKE_CONTRACT"
_SCIENTIFIC_SURFACE_KEYS = (
    "hedonic_platform",
    "formulation_intelligence_contracts",
    "panel_contract",
    "sensory_source_manifest",
    "ma_2021_benchmark",
    "panel_contract_review",
    "legacy_hedonic_implementation",
    "optimizer_scoring_implementation",
    "crowd_pleasantness_implementation",
    "crowd_pleasantness_table_loader",
    "crowd_pleasantness_table",
)
_CANONICAL_EVIDENCE_KEYS = {
    "physical_sample_receipts",
    "locked_protocol_receipts",
    "participant_qualification_receipts",
    "exact_condition_observations",
    "panel_performance_results",
    "criterion_preference_views",
    "population_preference_views",
    "pareto_decision_states",
}
_CHECKPOINT8_BLOCKERS = [
    "HOLD_CP8_CP7_RESEARCH_CHARACTERIZATION_INCOMPLETE",
    "HOLD_CP8_PHYSICAL_SENSORY_SAMPLES_UNAVAILABLE",
    "HOLD_CP8_SENSORY_PROTOCOL_BINDINGS_INCOMPLETE",
    "HOLD_CP8_EXACT_CONDITION_HUMAN_OBSERVATIONS_UNAVAILABLE",
    "PLEASANTNESS_NOT_ESTABLISHED",
    "PHYSICAL_LIKING_NOT_TESTED",
]
_AUTHORITY = {
    "checkpoint8_intake_contract_record_authorized": True,
    "evidence_admission_authorized": False,
    "human_study_authorized": False,
    "physical_experiment_authorized": False,
    "sensory_evaluation_authorized": False,
    "participant_recruitment_authorized": False,
    "model_training_authorized": False,
    "model_calibration_authorized": False,
    "formula_optimization_authorized": False,
    "compounding_authorized": False,
    "purchase_authorized": False,
    "inventory_mutation_authorized": False,
    "physical_formula_mutation_authorized": False,
    "safety_authorized": False,
    "release_authorized": False,
}
_SIDE_EFFECTS = {
    "backend_record_created": False,
    "physical_sample_created": False,
    "participant_contacted": False,
    "human_observation_created": False,
    "sensory_evaluation_executed": False,
    "model_trained": False,
    "model_calibrated": False,
    "formula_ranked": False,
    "inventory_modified": False,
    "physical_formula_modified": False,
}
_ENDPOINT_CONTRACT = {
    "construction_axes": [
        "airiness",
        "separability",
        "density",
        "coherence",
        "target_fidelity",
        "contrast",
        "emergence",
        "recognition",
    ],
    "pleasantness_endpoint": "pleasantness",
    "pairwise_liking_endpoint": "exact_condition_preference_outcome",
    "aversion_and_defect_endpoints_remain_separate": True,
    "blotter_and_skin_domains_remain_separate": True,
    "individual_and_population_liking_remain_separate": True,
    "unlike_endpoints_may_not_be_summed": True,
    "beauty_endpoint": "PROHIBITED_DERIVED_ENDPOINT",
    "pleasantness_state": "NOT_ESTABLISHED",
    "personal_liking_state": "NOT_TESTED",
    "population_liking_state": "NOT_TESTED",
}


class Checkpoint8ContractError(ValueError):
    """Raised when the Checkpoint 8 intake contract cannot be trusted."""


def _file_sha256(path: Path) -> str:
    return stable_portable_file_hash(path)


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Checkpoint8ContractError(f"{label} is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise Checkpoint8ContractError(f"{label} must be a JSON object")
    return value


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Checkpoint8ContractError(f"{label} must be an object")
    return value


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise Checkpoint8ContractError(f"{label} must be a list")
    return value


def _resolve_pinned_path(
    path_text: object,
    expected_sha256: object,
    *,
    label: str,
) -> Path:
    path = (REPOSITORY_ROOT / str(path_text or "")).resolve()
    if not path.is_relative_to(REPOSITORY_ROOT.resolve()):
        raise Checkpoint8ContractError(f"{label} escapes repository")
    if not path.is_file():
        raise Checkpoint8ContractError(f"{label} is unavailable: {path}")
    if _file_sha256(path) != expected_sha256:
        raise Checkpoint8ContractError(f"{label} hash drift")
    return path


def _expected_checkpoint8_contract() -> dict[str, object]:
    return {
        "state": "SOFTWARE_COMPLETE_SENSORY_EVIDENCE_INTAKE_HOLD",
        "hold_state": (
            "HOLD_CP8_PHYSICAL_STUDY_OR_EXACT_SCOPE_EVIDENCE_INCOMPLETE"
        ),
        "future_pass_state": (
            "PASS_CP8_R6_EXACT_SCOPE_SENSORY_EVIDENCE_RECORDED"
        ),
        "project_phase": (
            "SOFTWARE_CHECKPOINT_SEQUENCE_COMPLETE_EXTERNAL_VALIDATION_PENDING"
        ),
        "formula_action": "NO_CHANGE",
        "ranked_candidates": [],
        "best_observed_candidate": None,
        "experimental_recommendation": None,
        "shortlist_ordering": "UNORDERED_DIVERSE_SET",
        "formula_modified": False,
        "inventory_modified": False,
    }


def _validate_superseded_record(supersedes: object) -> None:
    if not isinstance(supersedes, Mapping):
        raise Checkpoint8ContractError("superseded record drift")
    path = (REPOSITORY_ROOT / str(supersedes.get("path") or "")).resolve()
    if (
        not path.is_relative_to(REPOSITORY_ROOT.resolve())
        or not path.is_file()
        or _file_sha256(path) != supersedes.get("sha256")
    ):
        raise Checkpoint8ContractError("superseded record drift")


def _validate_protocol_contract(protocol: Mapping[str, Any]) -> None:
    if protocol.get("schema_version") != _SCHEMA_VERSION:
        raise Checkpoint8ContractError("Checkpoint 8 schema drift")
    if protocol.get("state") != _PROTOCOL_STATE:
        raise Checkpoint8ContractError("Checkpoint 8 protocol state drift")
    if protocol.get("protocol_id") != (
        "lavande-ambre-profond-r6-cp8-sensory-evidence-intake-20261009"
    ):
        raise Checkpoint8ContractError("Checkpoint 8 protocol identity drift")
    _validate_superseded_record(protocol.get("supersedes"))

    prerequisite = _require_mapping(
        protocol.get("checkpoint7_prerequisite"), "Checkpoint 7 prerequisite"
    )
    if prerequisite != {
        "required_state": "PASS_CP7_R6_RESEARCH_SAMPLE_CHARACTERIZED",
        "observed_state": (
            "HOLD_CP7_BUILD_MEASUREMENT_OR_APPLICABILITY_INCOMPLETE"
        ),
        "satisfied": False,
        "bypass_allowed": False,
    }:
        raise Checkpoint8ContractError("Checkpoint 7 prerequisite drift")

    endpoint = _require_mapping(
        protocol.get("endpoint_contract"), "endpoint contract"
    )
    if endpoint != _ENDPOINT_CONTRACT:
        raise Checkpoint8ContractError("sensory endpoint authority drift")

    evidence = _require_mapping(
        protocol.get("canonical_current_evidence"), "canonical evidence"
    )
    if set(evidence) != _CANONICAL_EVIDENCE_KEYS:
        raise Checkpoint8ContractError("canonical evidence schema drift")
    if any(not isinstance(value, list) or value for value in evidence.values()):
        raise Checkpoint8ContractError(
            "Checkpoint 8 canonical evidence must remain empty"
        )

    blockers = _require_list(protocol.get("checkpoint8_blockers"), "blockers")
    if blockers != _CHECKPOINT8_BLOCKERS:
        raise Checkpoint8ContractError("Checkpoint 8 blocker drift")

    contract = _require_mapping(
        protocol.get("checkpoint8_contract"), "Checkpoint 8 contract"
    )
    if contract != _expected_checkpoint8_contract():
        raise Checkpoint8ContractError("Checkpoint 8 outcome contract drift")

    authority = _require_mapping(protocol.get("authority"), "authority")
    if authority != _AUTHORITY:
        raise Checkpoint8ContractError("Checkpoint 8 authority boundary drift")

    side_effects = _require_mapping(protocol.get("side_effects"), "side effects")
    if side_effects != _SIDE_EFFECTS:
        raise Checkpoint8ContractError("Checkpoint 8 side-effect boundary drift")


def _validate_bierling_boundary(
    source_manifest: Mapping[str, Any], declared: Mapping[str, Any]
) -> dict[str, object]:
    sources = _require_list(source_manifest.get("sources"), "sensory sources")
    matches = [
        _require_mapping(item, "sensory source")
        for item in sources
        if isinstance(item, Mapping) and item.get("id") == "bierling_2025"
    ]
    if len(matches) != 1:
        raise Checkpoint8ContractError("Bierling source identity drift")
    source = matches[0]
    inspection = _require_mapping(
        source.get("read_only_inspection"), "Bierling read-only inspection"
    )
    restrictions = _require_list(source.get("restrictions"), "Bierling restrictions")
    calculated: dict[str, object] = {
        "source_id": source.get("id"),
        "article_doi": source.get("article_doi"),
        "dataset_doi": source.get("doi"),
        "license": source.get("license"),
        "included_participant_codes": inspection.get("included_participant_codes"),
        "included_odor_codes": inspection.get("included_odor_codes"),
        "published_headline_odor_count": 74,
        "included_nonempty_numeric_pleasantness_rows": inspection.get(
            "included_nonempty_numeric_pleasantness_rows"
        ),
        "pleasantness_scale": inspection.get("pleasant_intensive_scale_per_dictionary"),
        "scope": "MONOMOLECULAR_ODORS_POPULATION_DATA",
        "mixture_level_liking_data": False,
        "systematic_multi_dose_response_data": False,
        "r6_formula_transfer_authorized": False,
        "r6_personal_liking_established": False,
    }
    required_restrictions = {
        "Not mixture-level liking data",
        "Main study is not a systematic multi-dose response study",
        (
            "Published 74-odor headline versus 73 included odor codes requires "
            "mapping reconciliation before modeling"
        ),
    }
    if not required_restrictions.issubset(set(str(item) for item in restrictions)):
        raise Checkpoint8ContractError("Bierling scope restriction drift")
    if dict(declared) != calculated:
        raise Checkpoint8ContractError("Bierling transfer boundary drift")
    return calculated


def _validate_ma_boundary(
    benchmark: Mapping[str, Any], declared: Mapping[str, Any]
) -> dict[str, object]:
    literature = _require_mapping(
        benchmark.get("literature_boundary"), "Ma literature boundary"
    )
    design = _require_mapping(benchmark.get("design"), "Ma design")
    metrics = _require_mapping(benchmark.get("baseline_metrics"), "Ma metrics")
    squared = _require_mapping(
        metrics.get("pleasantness_squared_intensity_weighted"),
        "Ma squared-intensity baseline",
    )
    authorizations = _require_mapping(
        benchmark.get("authorizations"), "Ma authorizations"
    )
    calculated: dict[str, object] = {
        "dataset_article_doi": literature.get("dataset_article_doi"),
        "same_source_intensity_doi": literature.get("same_source_intensity_doi"),
        "same_source_pleasantness_doi": literature.get(
            "same_source_pleasantness_doi"
        ),
        "claim": literature.get("claim"),
        "unique_mixture_groups": design.get("unique_mixture_groups"),
        "source_trial_rows": design.get("source_trial_rows"),
        "best_predefined_pleasantness_baseline": (
            "pleasantness_squared_intensity_weighted"
        ),
        "best_predefined_pleasantness_rmse": squared.get("rmse"),
        "formula_prediction_authorized": authorizations.get(
            "formula_prediction_authorized"
        ),
        "cross_study_generalization_authorized": authorizations.get(
            "cross_study_generalization_authorized"
        ),
        "participant_level_inference_authorized": authorizations.get(
            "participant_level_inference_authorized"
        ),
        "sensory_claim_authorized": authorizations.get(
            "sensory_claim_authorized"
        ),
        "r6_formula_transfer_authorized": False,
    }
    if (
        benchmark.get("schema_version")
        != "perfume-chem-ma2021-baseline-benchmark-v1"
        or literature.get("claim") != "SOURCE_INTERNAL_CALIBRATION_ONLY"
        or any(
            authorizations.get(key) is not False
            for key in (
                "formula_prediction_authorized",
                "cross_study_generalization_authorized",
                "participant_level_inference_authorized",
                "sensory_claim_authorized",
            )
        )
    ):
        raise Checkpoint8ContractError("Ma source authority drift")
    if dict(declared) != calculated:
        raise Checkpoint8ContractError("Ma transfer boundary drift")
    return calculated


def evaluate_r6_checkpoint8_readiness(
    *, protocol_path: Path = DEFAULT_PROTOCOL_PATH
) -> dict[str, object]:
    """Return a deterministic Checkpoint 8 sensory-evidence abstention."""

    protocol = _load_object(protocol_path, "Checkpoint 8 protocol")
    _validate_protocol_contract(protocol)
    inputs = _require_mapping(protocol.get("inputs"), "Checkpoint 8 inputs")
    cp7_protocol_path = _resolve_pinned_path(
        inputs.get("checkpoint7_protocol_path"),
        inputs.get("checkpoint7_protocol_sha256"),
        label="Checkpoint 7 protocol",
    )
    _resolve_pinned_path(
        inputs.get("checkpoint7_evaluator_path"),
        inputs.get("checkpoint7_evaluator_sha256"),
        label="Checkpoint 7 evaluator",
    )

    scientific_surface = _require_mapping(
        protocol.get("scientific_surface"), "scientific surface"
    )
    if tuple(scientific_surface) != _SCIENTIFIC_SURFACE_KEYS:
        raise Checkpoint8ContractError("scientific surface schema drift")
    scientific_fingerprints: dict[str, dict[str, str]] = {}
    scientific_paths: dict[str, Path] = {}
    for key in _SCIENTIFIC_SURFACE_KEYS:
        record = _require_mapping(scientific_surface.get(key), key)
        path = _resolve_pinned_path(
            record.get("path"), record.get("sha256"), label=key
        )
        scientific_paths[key] = path
        scientific_fingerprints[key] = {
            "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
            "sha256": _file_sha256(path),
        }

    try:
        checkpoint7 = evaluate_r6_checkpoint7_readiness(
            protocol_path=cp7_protocol_path
        )
    except Checkpoint7ContractError as exc:
        raise Checkpoint8ContractError(
            "Checkpoint 7 evaluation failed closed"
        ) from exc
    if checkpoint7.get("report_sha256") != inputs.get("checkpoint7_report_sha256"):
        raise Checkpoint8ContractError("Checkpoint 7 report hash drift")
    if (
        checkpoint7.get("input_integrity_state") != "VERIFIED"
        or checkpoint7.get("checkpoint7_state")
        != "SOFTWARE_COMPLETE_RESEARCH_APPLICABILITY_INTAKE_HOLD"
        or checkpoint7.get("research_applicability_state")
        != "HOLD_CP7_BUILD_MEASUREMENT_OR_APPLICABILITY_INCOMPLETE"
        or checkpoint7.get("research_sample_state") != "NOT_COMPOUNDED"
        or checkpoint7.get("measurement_execution_state") != "NOT_STARTED"
        or checkpoint7.get("exact_curve_applicability_state")
        != "HOLD_EXACT_CURVE_APPLICABILITY"
    ):
        raise Checkpoint8ContractError("Checkpoint 7 prerequisite report drift")

    external = _require_mapping(
        protocol.get("external_evidence_boundary"), "external evidence boundary"
    )
    if set(external) != {"bierling_2025", "ma_2021"}:
        raise Checkpoint8ContractError("external evidence boundary schema drift")
    source_manifest = _load_object(
        scientific_paths["sensory_source_manifest"], "sensory source manifest"
    )
    bierling = _validate_bierling_boundary(
        source_manifest,
        _require_mapping(external.get("bierling_2025"), "Bierling boundary"),
    )
    ma_benchmark = _load_object(
        scientific_paths["ma_2021_benchmark"], "Ma benchmark"
    )
    ma = _validate_ma_boundary(
        ma_benchmark,
        _require_mapping(external.get("ma_2021"), "Ma boundary"),
    )

    platform = HedonicEvidencePlatform()
    scope = AssessmentScope(
        target_scope="lavande-ambre-profond-r6",
        temporal_scope="unresolved",
        matrix_scope="unresolved",
    )
    assessment = assess_hedonic_platform(platform, scope=scope)
    criteria = tuple(assessment.native_criteria)
    all_criteria_unknown = bool(criteria) and all(
        criterion.value.state.value == "unknown"
        and criterion.value.value is None
        for criterion in criteria
    )
    calculated_platform = {
        "schema_version": platform.SCHEMA_VERSION,
        "target_scope": scope.target_scope,
        "temporal_scope": scope.temporal_scope,
        "matrix_scope": scope.matrix_scope,
        "platform_sha256": platform.content_sha256,
        "scope_sha256": scope.content_sha256,
        "assessment_sha256": assessment.content_sha256,
        "assessment_id": assessment.assessment_id,
        "authority_ceiling": assessment.authority_ceiling.value,
        "view_count": len(platform.all_views),
        "decision_count": len(platform.decision_states),
        "unknown_fact_count": len(assessment.unknowns),
        "native_criterion_count": len(criteria),
        "all_native_criteria_unknown": all_criteria_unknown,
        "ranked_winner_available": False,
    }
    declared_platform = _require_mapping(
        protocol.get("empty_hedonic_platform_contract"),
        "empty hedonic platform contract",
    )
    if dict(declared_platform) != calculated_platform:
        raise Checkpoint8ContractError("empty hedonic platform contract drift")

    lexicon = build_c0_construction_lexicon()
    panel_protocol = build_c0_protocol_draft(lexicon)
    exit_report = evaluate_c0_exit(panel_protocol, lexicon, ())
    calculated_panel = {
        "lexicon_sha256": lexicon.lexicon_sha256,
        "draft_protocol_sha256": panel_protocol.protocol_sha256,
        "empty_exit_report_sha256": _canonical_sha256(exit_report.as_dict()),
        "exit_decision": exit_report.decision.value,
        "protocol_locked": panel_protocol.protocol_locked,
        "required_binding_ids": list(REQUIRED_BINDING_IDS),
        "required_binding_count": len(panel_protocol.bindings),
        "bound_binding_count": sum(
            item.state is BindingState.BOUND for item in panel_protocol.bindings
        ),
        "panel_gate_ids": [item.kind.value for item in panel_protocol.panel_gate_specs],
        "locked_panel_gate_count": sum(
            item.authority is GateAuthority.PREREGISTERED_LOCKED
            for item in panel_protocol.panel_gate_specs
        ),
        "timepoints_seconds": list(panel_protocol.timepoints_seconds),
        "repeat_count": panel_protocol.repeat_count,
        "study_authorized": panel_protocol.study_authorized,
        "release_authority": panel_protocol.release_authority,
        "model_calibration_authority": panel_protocol.model_calibration_authority,
    }
    declared_panel = _require_mapping(
        protocol.get("panel_intake_contract"), "panel intake contract"
    )
    if (
        dict(declared_panel) != calculated_panel
        or exit_report.decision is not C0ExitDecision.HOLD
        or exit_report.c0_exit_satisfied
        or len(panel_protocol.bindings) != 9
        or panel_protocol.protocol_locked
    ):
        raise Checkpoint8ContractError("panel intake contract drift")

    legacy_report = score_hedonic({})
    legacy = asdict(legacy_report)
    calculated_legacy = {
        "empty_input_score": legacy["score"],
        "empty_input_class": legacy["pleasantness_class"],
        "coverage_status": legacy["coverage_status"],
        "classification": legacy["classification"],
        "ranking_status": legacy["ranking_status"],
        "formula_optimization_authority": legacy[
            "formula_optimization_authority"
        ],
        "sensory_validation_status": legacy["sensory_validation_status"],
        "full_formula_pleasantness_status": legacy[
            "full_formula_pleasantness_status"
        ],
        "pleasantness_class_scope": legacy["pleasantness_class_scope"],
        "may_populate_hedonic_platform_observations": False,
        "may_select_or_rank_r6": False,
    }
    declared_legacy = _require_mapping(
        protocol.get("legacy_heuristic_quarantine"),
        "legacy heuristic quarantine",
    )
    if dict(declared_legacy) != calculated_legacy:
        raise Checkpoint8ContractError("legacy heuristic authority drift")

    contract = _require_mapping(
        protocol.get("checkpoint8_contract"), "Checkpoint 8 contract"
    )
    evidence = _require_mapping(
        protocol.get("canonical_current_evidence"), "canonical evidence"
    )
    report: dict[str, object] = {
        "schema_version": "lavande-ambre-profond-r6-cp8-readiness-report-v1",
        "status": "HOLD",
        "checkpoint8_state": contract.get("state"),
        "sensory_evidence_state": contract.get("hold_state"),
        "project_phase": contract.get("project_phase"),
        "input_integrity_state": "VERIFIED",
        "checkpoint7_prerequisite": dict(
            _require_mapping(
                protocol.get("checkpoint7_prerequisite"),
                "Checkpoint 7 prerequisite",
            )
        ),
        "external_evidence_boundary": {
            "bierling_2025": bierling,
            "ma_2021": ma,
        },
        "hedonic_platform": {
            **calculated_platform,
            "native_criterion_ids": [
                criterion.criterion_id for criterion in criteria
            ],
            "claims_count": len(assessment.claims),
            "prohibition_claim_count": sum(
                claim.claim_kind.value == "prohibition"
                for claim in assessment.claims
            ),
        },
        "panel_intake": {
            **calculated_panel,
            "binding_states": [item.as_dict() for item in panel_protocol.bindings],
            "exit_blockers": list(exit_report.blockers),
            "c0_exit_satisfied": exit_report.c0_exit_satisfied,
        },
        "endpoint_contract": dict(_ENDPOINT_CONTRACT),
        "legacy_heuristic_quarantine": calculated_legacy,
        "canonical_current_evidence": dict(evidence),
        "evidence_census": {
            "physical_sample_receipt_count": 0,
            "locked_protocol_receipt_count": 0,
            "participant_qualification_receipt_count": 0,
            "exact_condition_observation_count": 0,
            "panel_performance_result_count": 0,
            "criterion_preference_view_count": 0,
            "population_preference_view_count": 0,
            "pareto_decision_state_count": 0,
            "ranked_candidate_count": 0,
        },
        "blockers": list(_CHECKPOINT8_BLOCKERS),
        "formula_action": contract.get("formula_action"),
        "ranked_candidates": contract.get("ranked_candidates"),
        "best_observed_candidate": contract.get("best_observed_candidate"),
        "experimental_recommendation": contract.get(
            "experimental_recommendation"
        ),
        "shortlist_ordering": contract.get("shortlist_ordering"),
        "formula_modified": contract.get("formula_modified"),
        "inventory_modified": contract.get("inventory_modified"),
        "authority": dict(_AUTHORITY),
        "side_effects": dict(_SIDE_EFFECTS),
        "fingerprints": {
            "checkpoint8_protocol_sha256": _file_sha256(protocol_path),
            "checkpoint7_protocol_sha256": _file_sha256(cp7_protocol_path),
            "checkpoint7_report_sha256": checkpoint7["report_sha256"],
            "scientific_surface": scientific_fingerprints,
        },
    }
    report["report_sha256"] = _canonical_sha256(report)
    return report


__all__ = [
    "Checkpoint8ContractError",
    "DEFAULT_PROTOCOL_PATH",
    "evaluate_r6_checkpoint8_readiness",
]
