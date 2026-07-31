"""Read-only B9 projection and rendering for canonical science authority."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256

from app.schemas.lab_reporting import (
    SCIENCE_EVIDENCE_CLASSES,
    SCIENCE_SECTION_KEYS,
    EvidenceClass,
    ScienceAuthorityReport,
    ScienceRecord,
    ScienceReportPolicy,
    ScienceReportTotals,
    ScienceSection,
    ScienceView,
)

REPORT_COLLECTION_KEYS = (
    *SCIENCE_SECTION_KEYS,
    "source_workflow_events",
    "property_conflict_members",
    "selected_assertion_candidates",
    "rule_support_evidence",
    "analytical_sequence_entries",
)

_SECTION_LABELS: dict[str, str] = {
    "source_documents": "Source documents",
    "source_extractions": "Source extractions and exact locators",
    "property_observations": "Property observations",
    "selected_assertions": "Selected assertions",
    "property_conflict_sets": "Property conflict sets",
    "contextual_thresholds": "Contextual thresholds",
    "oav_assessments": "OAV assessments",
    "knowledge_rules": "Knowledge rules",
    "rule_contradictions": "Rule contradictions",
    "analytical_methods": "Analytical methods",
    "analytical_method_validation": "Analytical method validation and QC",
    "analytical_sequences": "Analytical sequences",
    "analytical_runs": "Analytical runs",
    "analytical_peaks": "Analytical peaks",
    "gc_o_events": "GC-O events",
    "analytical_claim_assessments": "Analytical claim assessments",
    "regulatory_snapshots": "Regulatory snapshots",
    "regulatory_findings": "Regulatory findings",
    "claim_authority_decisions": "Claim-authority decisions",
    "claim_authority_support": "Claim-authority support",
}

_BLOCKED_OUTPUT_KEYS = {
    "preserved_artifact_path",
    "raw_source_path",
    "database_path",
    "database_url",
    "environment",
    "password",
    "secret",
    "api_key",
    "access_token",
}
_BANNED_AGGREGATE_KEYS = {
    "confidence",
    "confidence_percent",
    "confidence_percentage",
    "coverage",
    "coverage_score",
    "overall_score",
}
_NONAUTHORITATIVE_CLASSES = {"HEURISTIC", "SPECULATIVE", "UNKNOWN"}
_STRICT_CLAIM_DECISIONS = {"ALLOW_EXACT", "ALLOW_SCOPED", "BLOCK"}
_STRICT_REGULATORY_RESULTS = {"PASS_FOR_DECLARED_SCOPE", "FAIL"}
_STRICT_ANALYTICAL_IDENTITIES = {
    "CONFIRMED_AUTHENTIC_STANDARD",
    "STRONGLY_SUPPORTED_RI_PLUS_SPECTRUM",
}

_SOURCE_FACTS = (
    "source_id",
    "version_number",
    "schema_version",
    "source_type",
    "title",
    "authors_json",
    "issuing_organization",
    "container_title",
    "publisher_or_authority",
    "publication_date",
    "revision_date",
    "effective_date",
    "retrieval_date",
    "edition_or_amendment",
    "language",
    "original_unit",
    "original_terminology",
    "independence_group",
)
_SOURCE_PROVENANCE = (
    "identifiers_json",
    "default_locator_json",
    "artifact_sha256",
    "license_or_reuse_restriction",
    "reviewer_pseudonym",
    "supersedes_version_id",
    "parent_record_sha256",
    "record_sha256",
)
_SOURCE_AUTHORITY = ("review_state",)

_EXTRACTION_FACTS = (
    "structure_context_json",
    "original_value_json",
    "parsed_value_json",
    "normalization_json",
    "parser_or_model_version",
    "uncertainty_json",
    "ambiguity_json",
    "output_observation_id",
)
_EXTRACTION_PROVENANCE = (
    "source_version_id",
    "locator_json",
    "reviewer_pseudonym",
    "input_sha256",
    "output_sha256",
    "record_sha256",
)

_OBSERVATION_FACTS = (
    "schema_version",
    "identity_scope",
    "subject_identity_json",
    "property_type",
    "value_kind",
    "numeric_value",
    "categorical_value",
    "interval_lower",
    "interval_upper",
    "distribution_json",
    "censoring_qualifier",
    "censoring_limit",
    "original_unit",
    "canonical_unit",
    "temperature_k",
    "pressure_pa",
    "relative_humidity_percent",
    "matrix",
    "phase",
    "purity_fraction",
    "method",
    "replicate_count",
    "statistic",
    "standard_uncertainty",
    "uncertainty_interval_json",
    "quality_flags_json",
    "applicability_domain_json",
)
_OBSERVATION_PROVENANCE = (
    "subject_identity_sha256",
    "source_version_id",
    "extraction_record_id",
    "source_locator_json",
    "provenance_activity_json",
    "supersedes_observation_id",
    "content_sha256",
)
_OBSERVATION_AUTHORITY = ("review_state",)

_ASSERTION_FACTS = (
    "schema_version",
    "requested_identity_json",
    "requested_property_type",
    "requested_conditions_json",
    "selection_policy_version",
    "selection_kind",
    "selected_observation_id",
    "selected_model_json",
    "interpolation_state",
    "propagated_uncertainty_json",
    "applicability_json",
    "permitted_claim_wording",
)
_ASSERTION_PROVENANCE = (
    "requested_identity_sha256",
    "conflict_set_id",
    "content_sha256",
)
_ASSERTION_AUTHORITY = ("authority_state",)

_CONFLICT_FACTS = (
    "schema_version",
    "requested_identity_json",
    "property_type",
    "requested_conditions_json",
    "materiality",
    "difference_dimensions_json",
    "explanation",
)
_CONFLICT_PROVENANCE = (
    "requested_identity_sha256",
    "content_sha256",
)
_CONFLICT_AUTHORITY = ("state",)

_THRESHOLD_FACTS = (
    "schema_version",
    "endpoint",
    "route",
    "medium",
    "matrix_specification_state",
    "matrix_composition_json",
    "concentration_basis",
    "apparatus_json",
    "population_json",
    "training_state",
    "sample_size",
    "psychophysical_procedure",
)
_THRESHOLD_PROVENANCE = ("observation_id", "content_sha256")

_OAV_FACTS = (
    "schema_version",
    "requested_endpoint",
    "requested_route",
    "oav_value",
    "mismatch_count",
    "mismatch_codes_json",
    "conversion_prerequisites_json",
    "input_snapshot_json",
    "permitted_uses_json",
    "prohibited_claims_json",
)
_OAV_PROVENANCE = (
    "concentration_observation_id",
    "threshold_assertion_id",
    "content_sha256",
)
_OAV_AUTHORITY = ("strict_science_mode", "status")

_RULE_FACTS = (
    "rule_key",
    "version",
    "subject_kind",
    "subject_raw_label",
    "relation",
    "object_kind",
    "object_raw_label",
    "directionality",
    "matrix_context_json",
    "dose_domain_json",
    "temporal_domain_json",
    "expected_effect_json",
    "attribute",
    "rationale",
    "uncertainty_json",
    "runtime_role",
    "numerical_model_ref",
    "compiler_diagnostics_json",
)
_RULE_PROVENANCE = (
    "subject_identity_scope_sha256",
    "subject_group_id",
    "object_identity_scope_sha256",
    "object_group_id",
    "source_document_version_id",
    "source_extraction_id",
    "source_locator",
    "raw_json_pointer",
    "raw_payload_sha256",
    "supersedes_rule_id",
    "content_sha256",
)
_RULE_AUTHORITY = ("review_state", "status")

_RULE_CONTRADICTION_FACTS = (
    "rule_id",
    "contradictory_rule_id",
    "reason_code",
    "rationale",
    "blocking",
)
_RULE_CONTRADICTION_PROVENANCE = ("content_sha256",)

_METHOD_FACTS = (
    "method_version_id",
    "schema_version",
    "analyte_scope_json",
    "instrument_json",
    "detector_json",
    "software_json",
    "separation_json",
    "acquisition_json",
    "sample_preparation_json",
    "hs_spme_json",
    "standards_json",
    "calibration_json",
    "response_factors_json",
    "identity_criteria_json",
    "integration_policy_json",
    "qc_plan_json",
    "raw_data_policy_json",
)
_METHOD_PROVENANCE = (
    "source_document_version_id",
    "source_locator_json",
    "source_artifact_sha256",
    "content_sha256",
)
_METHOD_AUTHORITY = ("status",)

_VALIDATION_FACTS = (
    "intended_claim",
    "matrix_scope_json",
    "characteristics_json",
    "acceptance_criteria_json",
    "limitations_json",
    "measurement_uncertainty_json",
)
_VALIDATION_PROVENANCE = (
    "method_authority_id",
    "scope_sha256",
    "reviewer_pseudonym",
    "reviewed_at",
    "source_document_version_id",
    "source_locator_json",
    "source_artifact_sha256",
    "content_sha256",
)
_VALIDATION_AUTHORITY = ("result",)

_SEQUENCE_FACTS = (
    "sequence_key",
    "method_authority_id",
    "instrument_identifier",
    "entry_count",
    "acquired_at",
)
_SEQUENCE_PROVENANCE = ("entries_sha256", "content_sha256")
_SEQUENCE_AUTHORITY = ("status",)

_RUN_FACTS = (
    "analytical_run_id",
    "subject_type",
    "subject_id",
    "subject_stream_sequence",
    "matrix_scope_json",
    "applicability_json",
    "instrument_state_json",
    "processing_details_json",
    "deviation_assessment_json",
)
_RUN_PROVENANCE = (
    "method_authority_id",
    "sequence_id",
    "sequence_entry_id",
    "reviewer_pseudonym",
    "reviewed_at",
    "raw_vendor_attachment_id",
    "open_export_attachment_id",
    "content_sha256",
)
_RUN_AUTHORITY = ("disposition",)

_PEAK_FACTS = (
    "analytical_peak_id",
    "identity_label",
    "stationary_phase",
    "spectrum_json",
    "deconvolution_json",
    "library_candidates_json",
    "exact_mass_json",
    "authentic_standard_state",
    "co_injection_state",
    "quantifier_ions_json",
    "coelution_json",
    "manual_review_json",
    "identity_decision_json",
    "quantitation_state",
    "quantitation_json",
    "applicability_json",
)
_PEAK_PROVENANCE = (
    "analytical_run_authority_id",
    "reviewer_pseudonym",
    "reviewed_at",
    "content_sha256",
)
_PEAK_AUTHORITY = ("identity_state",)

_GCO_FACTS = (
    "gco_event_id",
    "window_basis",
    "window_start",
    "window_end",
    "detection_method",
    "replicate_index",
    "replicate_count",
    "detection_frequency",
    "repeatability_json",
    "aligned_peak_ids_json",
    "unknown_event",
    "exact_identity_claim",
)
_GCO_PROVENANCE = ("analytical_run_authority_id", "content_sha256")
_GCO_AUTHORITY = ("assessor_training_state",)

_ANALYTICAL_ASSESSMENT_FACTS = (
    "analytical_run_id",
    "claim_type",
    "scope_json",
    "missing_requirements_json",
    "qualifications_json",
    "details_json",
    "result_json",
)
_ANALYTICAL_ASSESSMENT_PROVENANCE = (
    "run_authority_id",
    "peak_authority_id",
    "policy_version",
    "upstream_hashes_json",
    "reviewer_pseudonym",
    "reviewed_at",
    "evidence_record_id",
    "content_sha256",
)
_ANALYTICAL_ASSESSMENT_AUTHORITY = ("decision",)

_REGULATORY_SNAPSHOT_FACTS = (
    "snapshot_id",
    "version_number",
    "schema_version",
    "subject_type",
    "subject_id",
    "standard_identifier",
    "standard_version",
    "jurisdiction",
    "product_category",
    "use_classification",
    "finished_product_concentration",
    "constituent_basis",
    "natural_material_assumptions_json",
    "effective_on",
    "evaluated_at",
    "evaluator_software_version",
    "market_action",
    "market_action_on",
    "unresolved_items_json",
    "result_reasons_json",
    "permitted_wording",
)
_REGULATORY_SNAPSHOT_PROVENANCE = (
    "parent_version_id",
    "legacy_assessment_version_id",
    "primary_source_version_id",
    "official_source_sha256",
    "current_state_source_ids_json",
    "watch_source_ids_json",
    "rule_version_ids_json",
    "supplier_binding_ids_json",
    "composition_profile_ids_json",
    "upstream_hashes_json",
    "reviewer_pseudonym",
    "reviewed_at",
    "content_sha256",
    "parent_sha256",
)
_REGULATORY_SNAPSHOT_AUTHORITY = ("result_state",)

_REGULATORY_FINDING_FACTS = (
    "substance_name",
    "cas_number",
    "observed_fraction",
    "limit_fraction",
    "concentration_basis",
    "source_status",
    "enforced",
    "contribution_lineage_json",
    "reason_codes_json",
    "detail_json",
)
_REGULATORY_FINDING_PROVENANCE = (
    "snapshot_version_id",
    "rule_version_id",
    "content_sha256",
)
_REGULATORY_FINDING_AUTHORITY = ("result_state",)

_CLAIM_FACTS = (
    "authority_id",
    "version_number",
    "schema_version",
    "claim_type",
    "subject_type",
    "subject_id",
    "claim_payload_json",
    "identity_scope_json",
    "condition_scope_json",
    "dimension_results_json",
    "supporting_observations_json",
    "conflicts_json",
    "missing_requirements_json",
    "source_references_json",
    "uncertainty_json",
    "permitted_wording",
    "forbidden_wording",
    "blocker_count",
    "conflict_count",
    "missing_requirement_count",
    "critical_unknown_count",
    "support_count",
    "source_reference_count",
    "release_authority",
)
_CLAIM_PROVENANCE = (
    "parent_version_id",
    "legacy_claim_assessment_version_id",
    "policy_version",
    "policy_sha256",
    "policy_json",
    "identity_scope_sha256",
    "condition_scope_sha256",
    "claim_scope_sha256",
    "upstream_hashes_json",
    "reviewer_pseudonym",
    "reviewed_at",
    "content_sha256",
    "parent_sha256",
)
_CLAIM_AUTHORITY = ("decision",)

_CLAIM_SUPPORT_FACTS = (
    "claim_authority_version_id",
    "support_kind",
    "role",
    "derived_facts_json",
    "source_references_json",
)
_CLAIM_SUPPORT_PROVENANCE = (
    "property_assertion_id",
    "oav_assessment_id",
    "knowledge_rule_id",
    "analytical_assessment_id",
    "composition_profile_id",
    "regulatory_snapshot_version_id",
    "upstream_content_sha256",
    "content_sha256",
)

_SECTION_FIELDS: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    "source_documents": (_SOURCE_FACTS, _SOURCE_PROVENANCE, _SOURCE_AUTHORITY),
    "source_extractions": (_EXTRACTION_FACTS, _EXTRACTION_PROVENANCE, ()),
    "property_observations": (
        _OBSERVATION_FACTS,
        _OBSERVATION_PROVENANCE,
        _OBSERVATION_AUTHORITY,
    ),
    "selected_assertions": (
        _ASSERTION_FACTS,
        _ASSERTION_PROVENANCE,
        _ASSERTION_AUTHORITY,
    ),
    "property_conflict_sets": (
        _CONFLICT_FACTS,
        _CONFLICT_PROVENANCE,
        _CONFLICT_AUTHORITY,
    ),
    "contextual_thresholds": (_THRESHOLD_FACTS, _THRESHOLD_PROVENANCE, ()),
    "oav_assessments": (_OAV_FACTS, _OAV_PROVENANCE, _OAV_AUTHORITY),
    "knowledge_rules": (_RULE_FACTS, _RULE_PROVENANCE, _RULE_AUTHORITY),
    "rule_contradictions": (
        _RULE_CONTRADICTION_FACTS,
        _RULE_CONTRADICTION_PROVENANCE,
        (),
    ),
    "analytical_methods": (_METHOD_FACTS, _METHOD_PROVENANCE, _METHOD_AUTHORITY),
    "analytical_method_validation": (
        _VALIDATION_FACTS,
        _VALIDATION_PROVENANCE,
        _VALIDATION_AUTHORITY,
    ),
    "analytical_sequences": (
        _SEQUENCE_FACTS,
        _SEQUENCE_PROVENANCE,
        _SEQUENCE_AUTHORITY,
    ),
    "analytical_runs": (_RUN_FACTS, _RUN_PROVENANCE, _RUN_AUTHORITY),
    "analytical_peaks": (_PEAK_FACTS, _PEAK_PROVENANCE, _PEAK_AUTHORITY),
    "gc_o_events": (_GCO_FACTS, _GCO_PROVENANCE, _GCO_AUTHORITY),
    "analytical_claim_assessments": (
        _ANALYTICAL_ASSESSMENT_FACTS,
        _ANALYTICAL_ASSESSMENT_PROVENANCE,
        _ANALYTICAL_ASSESSMENT_AUTHORITY,
    ),
    "regulatory_snapshots": (
        _REGULATORY_SNAPSHOT_FACTS,
        _REGULATORY_SNAPSHOT_PROVENANCE,
        _REGULATORY_SNAPSHOT_AUTHORITY,
    ),
    "regulatory_findings": (
        _REGULATORY_FINDING_FACTS,
        _REGULATORY_FINDING_PROVENANCE,
        _REGULATORY_FINDING_AUTHORITY,
    ),
    "claim_authority_decisions": (
        _CLAIM_FACTS,
        _CLAIM_PROVENANCE,
        _CLAIM_AUTHORITY,
    ),
    "claim_authority_support": (
        _CLAIM_SUPPORT_FACTS,
        _CLAIM_SUPPORT_PROVENANCE,
        (),
    ),
}


@dataclass(frozen=True)
class _ProjectionContext:
    source_by_id: dict[str, object]
    workflow_state_by_subject: dict[str, str]
    observation_by_id: dict[str, object]
    assertion_by_id: dict[str, object]
    conflict_members: dict[str, tuple[str, ...]]
    assertion_candidates: dict[str, tuple[str, ...]]
    rule_by_id: dict[str, object]
    blocking_rule_ids: set[str]
    rule_support: dict[str, tuple[str, ...]]
    sequence_entries: dict[str, tuple[dict[str, object], ...]]
    regulatory_snapshot_by_id: dict[str, object]
    claim_by_id: dict[str, object]


def _record_id(row: object) -> str:
    return str(getattr(row, "id"))


def _row_sort_key(row: object) -> tuple[str, str]:
    created_at = _json_safe(getattr(row, "created_at", ""))
    return (str(created_at), _record_id(row))


def _json_safe(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    return str(value)


def _output_name(field: str) -> str:
    if field.endswith("_json"):
        return field[: -len("_json")]
    return field


def _fields(row: object, names: Sequence[str]) -> dict[str, object]:
    projected: dict[str, object] = {}
    for name in names:
        value = getattr(row, name, None)
        if value is not None:
            projected[_output_name(name)] = _json_safe(value)
    return projected


def _identifier_map(rows: Sequence[object]) -> dict[str, object]:
    return {_record_id(row): row for row in rows}


def _projection_context(
    snapshot: Mapping[str, Sequence[object]],
) -> _ProjectionContext:
    workflow: dict[str, tuple[int, str]] = {}
    for event in snapshot.get("source_workflow_events", ()):
        subject_id = str(getattr(event, "subject_id", ""))
        sequence = int(getattr(event, "sequence_number", 0))
        state = str(getattr(event, "to_state", ""))
        previous = workflow.get(subject_id)
        if previous is None or sequence > previous[0]:
            workflow[subject_id] = (sequence, state)

    conflict_members: dict[str, list[str]] = {}
    for member in snapshot.get("property_conflict_members", ()):
        conflict_members.setdefault(
            str(getattr(member, "conflict_set_id", "")),
            [],
        ).append(str(getattr(member, "observation_id", "")))

    assertion_candidates: dict[str, list[str]] = {}
    for candidate in snapshot.get("selected_assertion_candidates", ()):
        assertion_candidates.setdefault(
            str(getattr(candidate, "selected_assertion_id", "")),
            [],
        ).append(str(getattr(candidate, "observation_id", "")))

    blocking_rule_ids: set[str] = set()
    for contradiction in snapshot.get("rule_contradictions", ()):
        if bool(getattr(contradiction, "blocking", False)):
            blocking_rule_ids.add(str(getattr(contradiction, "rule_id", "")))
            blocking_rule_ids.add(
                str(getattr(contradiction, "contradictory_rule_id", ""))
            )

    rule_support: dict[str, list[str]] = {}
    for support in snapshot.get("rule_support_evidence", ()):
        rule_support.setdefault(str(getattr(support, "rule_id", "")), []).append(
            _record_id(support)
        )

    sequence_entries: dict[str, list[dict[str, object]]] = {}
    for entry in snapshot.get("analytical_sequence_entries", ()):
        sequence_entries.setdefault(
            str(getattr(entry, "sequence_id", "")),
            [],
        ).append(
            _fields(
                entry,
                (
                    "injection_order",
                    "role",
                    "reference",
                    "level_json",
                    "content_sha256",
                ),
            )
        )
    for entries in sequence_entries.values():
        entries.sort(
            key=lambda item: int(str(item.get("injection_order", 0) or 0))
        )

    return _ProjectionContext(
        source_by_id=_identifier_map(snapshot.get("source_documents", ())),
        workflow_state_by_subject={
            subject_id: value[1] for subject_id, value in workflow.items()
        },
        observation_by_id=_identifier_map(
            snapshot.get("property_observations", ())
        ),
        assertion_by_id=_identifier_map(snapshot.get("selected_assertions", ())),
        conflict_members={
            key: tuple(sorted(value)) for key, value in conflict_members.items()
        },
        assertion_candidates={
            key: tuple(sorted(value)) for key, value in assertion_candidates.items()
        },
        rule_by_id=_identifier_map(snapshot.get("knowledge_rules", ())),
        blocking_rule_ids=blocking_rule_ids,
        rule_support={
            key: tuple(sorted(value)) for key, value in rule_support.items()
        },
        sequence_entries={
            key: tuple(value) for key, value in sequence_entries.items()
        },
        regulatory_snapshot_by_id=_identifier_map(
            snapshot.get("regulatory_snapshots", ())
        ),
        claim_by_id=_identifier_map(
            snapshot.get("claim_authority_decisions", ())
        ),
    )


def _mapped_evidence_class(value: object) -> EvidenceClass:
    normalized = str(value or "").strip().upper()
    if normalized in SCIENCE_EVIDENCE_CLASSES:
        return normalized  # type: ignore[return-value]
    if any(token in normalized for token in ("CONTROLLED", "MEASURED", "EXPERIMENT")):
        return "MEASURED"
    if "CALIBRAT" in normalized:
        return "EMPIRICALLY_CALIBRATED"
    if "SUPPLIER" in normalized:
        return "SUPPLIER_PROVIDED"
    if any(token in normalized for token in ("LITERATURE", "PEER", "STANDARD")):
        return "LITERATURE_DERIVED"
    if any(token in normalized for token in ("MODEL", "NUMERICAL")):
        return "MODEL_ESTIMATED"
    if any(
        token in normalized
        for token in ("HEURISTIC", "LEGACY", "PROSE", "EXPERT", "COMMUNITY")
    ):
        return "HEURISTIC"
    if any(token in normalized for token in ("SPECULATIVE", "HYPOTHESIS", "AI_")):
        return "SPECULATIVE"
    return "UNKNOWN"


def _source_evidence_class(row: object) -> EvidenceClass:
    source_type = str(getattr(row, "source_type", ""))
    if source_type in {"LOCAL_ANALYTICAL_EXPERIMENT", "LOCAL_SENSORY_EXPERIMENT"}:
        return "MEASURED"
    if source_type.startswith("SUPPLIER_"):
        return "SUPPLIER_PROVIDED"
    if source_type == "AI_GENERATED_HYPOTHESIS":
        return "SPECULATIVE"
    if source_type in {
        "EXPERT_NOTE",
        "SECONDARY_RECONSTRUCTION",
        "COMMUNITY_OBSERVATION",
    }:
        return "HEURISTIC"
    if source_type in {
        "AUTHENTICATED_FORMULA_OR_DOSSIER",
        "PRIMARY_PEER_REVIEWED_PAPER",
        "REVIEW_PAPER",
        "STANDARD",
        "REGULATION_OR_OFFICIAL_GUIDANCE",
        "AUTHORITATIVE_DATABASE_RECORD",
        "PATENT",
    }:
        return "LITERATURE_DERIVED"
    return "UNKNOWN"


def _evidence_class(
    section: str,
    row: object,
    context: _ProjectionContext,
) -> EvidenceClass:
    if section == "source_documents":
        return _source_evidence_class(row)
    if section == "source_extractions":
        source = context.source_by_id.get(
            str(getattr(row, "source_version_id", ""))
        )
        return _source_evidence_class(source) if source is not None else "UNKNOWN"
    if section == "property_observations":
        return _mapped_evidence_class(getattr(row, "evidence_class", None))
    if section == "selected_assertions":
        selection_kind = str(getattr(row, "selection_kind", ""))
        if selection_kind == "MODEL":
            return "MODEL_ESTIMATED"
        observation = context.observation_by_id.get(
            str(getattr(row, "selected_observation_id", ""))
        )
        return (
            _mapped_evidence_class(getattr(observation, "evidence_class", None))
            if observation is not None
            else "UNKNOWN"
        )
    if section == "contextual_thresholds":
        observation = context.observation_by_id.get(
            str(getattr(row, "observation_id", ""))
        )
        return (
            _mapped_evidence_class(getattr(observation, "evidence_class", None))
            if observation is not None
            else "UNKNOWN"
        )
    if section == "oav_assessments":
        assertion = context.assertion_by_id.get(
            str(getattr(row, "threshold_assertion_id", ""))
        )
        if assertion is not None:
            return _evidence_class("selected_assertions", assertion, context)
        observation = context.observation_by_id.get(
            str(getattr(row, "concentration_observation_id", ""))
        )
        return (
            _mapped_evidence_class(getattr(observation, "evidence_class", None))
            if observation is not None
            else "UNKNOWN"
        )
    if section == "knowledge_rules":
        return _mapped_evidence_class(getattr(row, "evidence_class", None))
    if section == "rule_contradictions":
        rule = context.rule_by_id.get(str(getattr(row, "rule_id", "")))
        return (
            _mapped_evidence_class(getattr(rule, "evidence_class", None))
            if rule is not None
            else "UNKNOWN"
        )
    if section == "analytical_methods":
        source = context.source_by_id.get(
            str(getattr(row, "source_document_version_id", ""))
        )
        return _source_evidence_class(source) if source is not None else "UNKNOWN"
    if section == "analytical_method_validation":
        return (
            "EMPIRICALLY_CALIBRATED"
            if str(getattr(row, "result", "")) == "PASS"
            else "UNKNOWN"
        )
    if section in {
        "analytical_runs",
        "analytical_peaks",
        "gc_o_events",
        "analytical_claim_assessments",
    }:
        return "MEASURED"
    if section in {"regulatory_snapshots", "regulatory_findings"}:
        return "LITERATURE_DERIVED"
    if section == "claim_authority_support":
        support_kind = str(getattr(row, "support_kind", ""))
        if support_kind == "PROPERTY_ASSERTION":
            assertion = context.assertion_by_id.get(
                str(getattr(row, "property_assertion_id", ""))
            )
            return (
                _evidence_class("selected_assertions", assertion, context)
                if assertion is not None
                else "UNKNOWN"
            )
        if support_kind == "KNOWLEDGE_RULE":
            rule = context.rule_by_id.get(
                str(getattr(row, "knowledge_rule_id", ""))
            )
            return (
                _evidence_class("knowledge_rules", rule, context)
                if rule is not None
                else "UNKNOWN"
            )
        if support_kind == "ANALYTICAL_ASSESSMENT":
            return "MEASURED"
        if support_kind == "REGULATORY_SNAPSHOT":
            return "LITERATURE_DERIVED"
    return "UNKNOWN"


def _has_locator(value: object) -> bool:
    if isinstance(value, Mapping):
        return bool(value)
    return bool(str(value or "").strip())


def _strict_reasons(
    section: str,
    row: object,
    context: _ProjectionContext,
    evidence_class: EvidenceClass,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if section == "source_documents":
        if str(getattr(row, "review_state", "")) != "REVIEWED":
            reasons.append("SOURCE_NOT_REVIEWED")
        if not _has_locator(getattr(row, "default_locator_json", None)):
            reasons.append("MISSING_EXACT_LOCATOR")
    elif section == "source_extractions":
        source = context.source_by_id.get(
            str(getattr(row, "source_version_id", ""))
        )
        if source is None:
            reasons.append("SOURCE_LINK_MISSING")
        elif str(getattr(source, "review_state", "")) != "REVIEWED":
            reasons.append("SOURCE_NOT_REVIEWED")
        if (
            context.workflow_state_by_subject.get(_record_id(row))
            != "ACCEPTED_FOR_SCOPED_USE"
        ):
            reasons.append("EXTRACTION_SCOPE_NOT_ACCEPTED")
        if not _has_locator(getattr(row, "locator_json", None)):
            reasons.append("MISSING_EXACT_LOCATOR")
    elif section == "property_observations":
        if str(getattr(row, "review_state", "")) != "ACCEPTED_FOR_SCOPED_USE":
            reasons.append("OBSERVATION_NOT_ACCEPTED")
        if evidence_class in _NONAUTHORITATIVE_CLASSES:
            reasons.append("NON_AUTHORITATIVE_EVIDENCE_CLASS")
        if not _has_locator(getattr(row, "source_locator_json", None)):
            reasons.append("MISSING_EXACT_LOCATOR")
    elif section == "selected_assertions":
        if (
            str(getattr(row, "authority_state", ""))
            != "AUTHORIZED_FOR_SCOPED_PROPERTY"
        ):
            reasons.append("ASSERTION_NOT_AUTHORIZED")
    elif section == "property_conflict_sets":
        if str(getattr(row, "state", "")) != "RESOLVED_FOR_SCOPE":
            reasons.append("CONFLICT_UNRESOLVED")
    elif section == "contextual_thresholds":
        observation = context.observation_by_id.get(
            str(getattr(row, "observation_id", ""))
        )
        if observation is None:
            reasons.append("THRESHOLD_OBSERVATION_MISSING")
        elif _strict_reasons(
            "property_observations",
            observation,
            context,
            _evidence_class("property_observations", observation, context),
        ):
            reasons.append("THRESHOLD_OBSERVATION_NOT_STRICT")
        if str(getattr(row, "matrix_specification_state", "")) != "SPECIFIED":
            reasons.append("THRESHOLD_MATRIX_UNSPECIFIED")
    elif section == "oav_assessments":
        if bool(getattr(row, "strict_science_mode", False)) is not True:
            reasons.append("OAV_NOT_STRICT_MODE")
        if str(getattr(row, "status", "")) != "COMPUTED":
            reasons.append("OAV_WITHHELD")
    elif section == "knowledge_rules":
        if str(getattr(row, "review_state", "")) != "APPROVED":
            reasons.append("RULE_NOT_APPROVED")
        if str(getattr(row, "status", "")) not in {"AUTHORITATIVE", "SUPPORTED"}:
            reasons.append("RULE_NOT_AUTHORITATIVE")
        if evidence_class in _NONAUTHORITATIVE_CLASSES:
            reasons.append("NON_AUTHORITATIVE_EVIDENCE_CLASS")
        if str(getattr(row, "subject_kind", "")) == "UNRESOLVED" or str(
            getattr(row, "object_kind", "")
        ) == "UNRESOLVED":
            reasons.append("RULE_ENDPOINT_UNRESOLVED")
        if _record_id(row) in context.blocking_rule_ids:
            reasons.append("RULE_BLOCKING_CONTRADICTION")
        if not _has_locator(getattr(row, "source_locator", None)):
            reasons.append("MISSING_EXACT_LOCATOR")
    elif section == "rule_contradictions":
        if not bool(getattr(row, "blocking", False)):
            reasons.append("CONTRADICTION_NON_BLOCKING")
        if str(getattr(row, "rule_id", "")) not in context.rule_by_id or str(
            getattr(row, "contradictory_rule_id", "")
        ) not in context.rule_by_id:
            reasons.append("CONTRADICTION_RULE_LINK_MISSING")
    elif section == "analytical_methods":
        if str(getattr(row, "status", "")) != "VALIDATED_FOR_SCOPE":
            reasons.append("METHOD_NOT_VALIDATED_FOR_SCOPE")
        if not _has_locator(getattr(row, "source_locator_json", None)):
            reasons.append("MISSING_EXACT_LOCATOR")
    elif section == "analytical_method_validation":
        if str(getattr(row, "result", "")) != "PASS":
            reasons.append("METHOD_VALIDATION_NOT_PASS")
        if not _has_locator(getattr(row, "source_locator_json", None)):
            reasons.append("MISSING_EXACT_LOCATOR")
    elif section == "analytical_sequences":
        if str(getattr(row, "status", "")) != "ACQUIRED":
            reasons.append("SEQUENCE_NOT_ACQUIRED")
    elif section == "analytical_runs":
        if str(getattr(row, "disposition", "")) not in {"ACCEPTED", "QUALIFIED"}:
            reasons.append("RUN_NOT_ACCEPTED")
    elif section == "analytical_peaks":
        if str(getattr(row, "identity_state", "")) not in _STRICT_ANALYTICAL_IDENTITIES:
            reasons.append("PEAK_IDENTITY_NOT_STRICT")
    elif section == "gc_o_events":
        if str(getattr(row, "assessor_training_state", "")) != "QUALIFIED":
            reasons.append("GCO_ASSESSOR_NOT_QUALIFIED")
    elif section == "analytical_claim_assessments":
        if str(getattr(row, "decision", "")) != "SUPPORTED_FOR_SCOPE":
            reasons.append("ANALYTICAL_CLAIM_NOT_SUPPORTED")
    elif section == "regulatory_snapshots":
        if str(getattr(row, "result_state", "")) not in _STRICT_REGULATORY_RESULTS:
            reasons.append("REGULATORY_RESULT_NOT_STRICT")
    elif section == "regulatory_findings":
        snapshot = context.regulatory_snapshot_by_id.get(
            str(getattr(row, "snapshot_version_id", ""))
        )
        if snapshot is None:
            reasons.append("REGULATORY_SNAPSHOT_MISSING")
        elif str(getattr(snapshot, "result_state", "")) not in (
            _STRICT_REGULATORY_RESULTS
        ):
            reasons.append("REGULATORY_SNAPSHOT_NOT_STRICT")
    elif section == "claim_authority_decisions":
        if str(getattr(row, "decision", "")) not in _STRICT_CLAIM_DECISIONS:
            reasons.append("CLAIM_DECISION_NOT_STRICT")
    elif section == "claim_authority_support":
        claim = context.claim_by_id.get(
            str(getattr(row, "claim_authority_version_id", ""))
        )
        if claim is None:
            reasons.append("CLAIM_PARENT_MISSING")
        elif str(getattr(claim, "decision", "")) not in _STRICT_CLAIM_DECISIONS:
            reasons.append("CLAIM_PARENT_NOT_STRICT")
    else:
        reasons.append("NO_STRICT_AUTHORITY_RULE")
    return tuple(reasons)


def _augment_fields(
    section: str,
    row: object,
    facts: dict[str, object],
    authority: dict[str, object],
    context: _ProjectionContext,
) -> None:
    record_id = _record_id(row)
    if section == "source_extractions":
        authority["workflow_state"] = context.workflow_state_by_subject.get(
            record_id,
            "UNKNOWN",
        )
    elif section == "selected_assertions":
        facts["candidate_observation_ids"] = list(
            context.assertion_candidates.get(record_id, ())
        )
    elif section == "property_conflict_sets":
        facts["member_observation_ids"] = list(
            context.conflict_members.get(record_id, ())
        )
    elif section == "knowledge_rules":
        facts["support_evidence_ids"] = list(
            context.rule_support.get(record_id, ())
        )
        authority["blocking_contradiction"] = (
            record_id in context.blocking_rule_ids
        )
    elif section == "analytical_sequences":
        facts["entries"] = list(context.sequence_entries.get(record_id, ()))


def _project_record(
    section: str,
    row: object,
    context: _ProjectionContext,
) -> ScienceRecord:
    fact_names, provenance_names, authority_names = _SECTION_FIELDS[section]
    facts = _fields(row, fact_names)
    provenance = _fields(row, provenance_names)
    authority = _fields(row, authority_names)
    _augment_fields(section, row, facts, authority, context)
    evidence_class = _evidence_class(section, row, context)
    reasons = _strict_reasons(section, row, context, evidence_class)
    return ScienceRecord(
        id=_record_id(row),
        created_at=str(_json_safe(getattr(row, "created_at", ""))),
        evidence_class=evidence_class,
        strict_eligible=not reasons,
        strict_reason_codes=reasons,
        authority=authority,
        provenance=provenance,
        facts=facts,
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _walk_keys(value: object) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key).casefold() for key in value}
        for item in value.values():
            keys.update(_walk_keys(item))
        return keys
    if isinstance(value, (list, tuple)):
        nested_keys: set[str] = set()
        for item in value:
            nested_keys.update(_walk_keys(item))
        return nested_keys
    return set()


def _assert_safe_payload(payload: Mapping[str, object]) -> None:
    keys = _walk_keys(payload)
    blocked = keys & (_BLOCKED_OUTPUT_KEYS | _BANNED_AGGREGATE_KEYS)
    if blocked:
        raise ValueError(
            "B9 report contains blocked fields: " + ", ".join(sorted(blocked))
        )


def build_science_report(
    snapshot: Mapping[str, Sequence[object]],
    view: ScienceView,
) -> ScienceAuthorityReport:
    """Build one deterministic, non-promoting report from canonical rows."""

    context = _projection_context(snapshot)
    sections: list[ScienceSection] = []
    for key in SCIENCE_SECTION_KEYS:
        rows = sorted(snapshot.get(key, ()), key=_row_sort_key)
        projected = tuple(_project_record(key, row, context) for row in rows)
        if view is ScienceView.STRICT:
            included = tuple(record for record in projected if record.strict_eligible)
            withheld = tuple(
                record for record in projected if not record.strict_eligible
            )
        else:
            included = projected
            withheld = ()
        sections.append(
            ScienceSection(
                key=key,  # type: ignore[arg-type]
                label=_SECTION_LABELS[key],
                included=included,
                withheld=withheld,
                total_count=len(projected),
                included_count=len(included),
                withheld_count=len(withheld),
            )
        )

    totals = ScienceReportTotals(
        section_count=len(sections),
        total_records=sum(section.total_count for section in sections),
        included_records=sum(section.included_count for section in sections),
        withheld_records=sum(section.withheld_count for section in sections),
    )
    unsigned = ScienceAuthorityReport(
        schema_version="lab-science-authority-report-v1",
        view=view,
        authority_state="READ_ONLY_NON_PROMOTING",
        evidence_classes=SCIENCE_EVIDENCE_CLASSES,  # type: ignore[arg-type]
        policy=ScienceReportPolicy(),
        sections=tuple(sections),
        totals=totals,
        report_sha256="0" * 64,
    )
    unsigned_payload = unsigned.model_dump(
        mode="json",
        exclude={"report_sha256"},
    )
    _assert_safe_payload(unsigned_payload)
    digest = sha256(_canonical_json(unsigned_payload).encode("utf-8")).hexdigest()
    return unsigned.model_copy(update={"report_sha256": digest})


def _locator_summary(record: ScienceRecord) -> str | None:
    for key in (
        "default_locator",
        "locator",
        "source_locator",
        "source_references",
    ):
        value = record.provenance.get(key)
        if value:
            return _canonical_json(value)
    return None


def render_science_report_markdown(report: ScienceAuthorityReport) -> str:
    """Render deterministic Markdown from the canonical B9 response."""

    lines = [
        "# Science authority report",
        "",
        f"View: `{report.view.value}`",
        "",
        "Authority: `READ_ONLY_NON_PROMOTING`",
        "",
        "Evidence classes:",
        "",
    ]
    lines.extend(f"- `{label}`" for label in report.evidence_classes)
    lines.extend(
        [
            "",
            "Strict mode keeps non-eligible records visible under withheld.",
            "Evidence classes are never combined into a numeric score.",
            "",
        ]
    )

    for section in report.sections:
        lines.extend(
            [
                f"## {section.label}",
                "",
                (
                    f"Records: `{section.total_count}`; included: "
                    f"`{section.included_count}`; withheld: "
                    f"`{section.withheld_count}`."
                ),
                "",
            ]
        )
        for disposition, records in (
            ("included", section.included),
            ("withheld", section.withheld),
        ):
            if not records:
                continue
            lines.extend([f"### {disposition.title()}", ""])
            for record in records:
                lines.append(
                    f"- `{record.id}` — `{record.evidence_class}` — "
                    f"strict eligible: `{str(record.strict_eligible).lower()}`"
                )
                if record.strict_reason_codes:
                    lines.append(
                        "  - reasons: "
                        + ", ".join(f"`{code}`" for code in record.strict_reason_codes)
                    )
                if record.authority:
                    lines.append(
                        "  - authority: `" + _canonical_json(record.authority) + "`"
                    )
                locator = _locator_summary(record)
                if locator is not None:
                    lines.append(f"  - locator: `{locator}`")
                digest = record.provenance.get("content_sha256") or record.provenance.get(
                    "record_sha256"
                )
                if digest:
                    lines.append(f"  - digest: `{digest}`")
            lines.append("")

    lines.extend(
        [
            "## Report identity",
            "",
            f"SHA-256: `{report.report_sha256}`",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "REPORT_COLLECTION_KEYS",
    "build_science_report",
    "render_science_report_markdown",
]
