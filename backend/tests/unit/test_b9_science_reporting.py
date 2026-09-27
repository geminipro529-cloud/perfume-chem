from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from types import SimpleNamespace

import pytest

from app.repositories.lab_reporting import (
    REPORT_MODEL_COLLECTIONS,
    ScienceReportRepository,
)
from app.schemas.lab_reporting import (
    SCIENCE_EVIDENCE_CLASSES,
    SCIENCE_SECTION_KEYS,
    ScienceView,
)
from app.services.lab_reporting import (
    REPORT_COLLECTION_KEYS,
    ScienceReportingService,
    build_science_report,
    render_science_report_markdown,
)

NOW = datetime(2026, 7, 31, 3, 0, tzinfo=timezone.utc)


def _row(record_id: str, **values: object) -> SimpleNamespace:
    return SimpleNamespace(id=record_id, created_at=NOW, **values)


def _clone(
    record: SimpleNamespace,
    record_id: str,
    **overrides: object,
) -> SimpleNamespace:
    values = {
        key: value
        for key, value in vars(record).items()
        if key not in {"id", "created_at"}
    }
    values.update(overrides)
    return _row(record_id, **values)


def _snapshot(**collections: tuple[SimpleNamespace, ...]):
    payload = {key: () for key in REPORT_COLLECTION_KEYS}
    payload.update(collections)
    return payload


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        found = {str(key).casefold() for key in value}
        for item in value.values():
            found.update(_keys(item))
        return found
    if isinstance(value, (list, tuple)):
        found: set[str] = set()
        for item in value:
            found.update(_keys(item))
        return found
    return set()


def _section(report, key: str):
    return next(section for section in report.sections if section.key == key)


def test_b9_empty_report_has_exact_vocabulary_and_no_aggregate_score():
    report = build_science_report(_snapshot(), ScienceView.STRICT)
    payload = report.model_dump(mode="json")

    assert SCIENCE_EVIDENCE_CLASSES == (
        "MEASURED",
        "LITERATURE_DERIVED",
        "SUPPLIER_PROVIDED",
        "EMPIRICALLY_CALIBRATED",
        "MODEL_ESTIMATED",
        "HEURISTIC",
        "SPECULATIVE",
        "UNKNOWN",
    )
    assert SCIENCE_SECTION_KEYS == (
        "source_documents",
        "source_use_constraints",
        "source_extractions",
        "property_observations",
        "selected_assertions",
        "property_conflict_sets",
        "contextual_thresholds",
        "oav_assessments",
        "knowledge_rules",
        "rule_contradictions",
        "analytical_methods",
        "analytical_method_validation",
        "analytical_sequences",
        "analytical_runs",
        "analytical_peaks",
        "gc_o_events",
        "analytical_claim_assessments",
        "regulatory_snapshots",
        "regulatory_findings",
        "claim_authority_decisions",
        "claim_authority_support",
        "external_study_versions",
    )
    assert tuple(section.key for section in report.sections) == SCIENCE_SECTION_KEYS
    assert report.schema_version == "lab-science-authority-report-v2"
    assert report.authority_state == "READ_ONLY_NON_PROMOTING"
    assert report.policy.numeric_aggregation_forbidden is True
    assert report.policy.strict_unknowns_visible is True
    assert report.policy.release_authority is False
    assert report.totals.total_records == 0
    assert report.totals.included_records == 0
    assert report.totals.withheld_records == 0
    assert len(report.report_sha256) == 64

    banned = {
        "confidence",
        "confidence_percent",
        "confidence_percentage",
        "coverage",
        "coverage_score",
        "overall_score",
    }
    assert _keys(payload).isdisjoint(banned)


def test_b9_external_study_summary_is_source_only_and_excludes_private_rows():
    source = _row(
        "source-v1",
        source_type="PRIMARY_RESEARCH_DATASET",
        review_state="REVIEWED",
        default_locator_json={"dataset": "V2"},
    )
    extraction = _row("extraction-v1", source_version_id=source.id)
    study = _row(
        "study-v1",
        study_id="ma-2021",
        version_number=1,
        source_version_id=source.id,
        source_extraction_id=extraction.id,
        source_family="MA_2021_V2",
        study_key="ma-2021-v2",
        title="Odor mixture study",
        study_domain="OLFACTION_PSYCHOPHYSICS",
        source_use_request_sha256="a" * 64,
        source_use_assessment_sha256="b" * 64,
        source_use_constraint_version_ids_json=["constraint-v1"],
        source_use_constraint_record_sha256s_json=["c" * 64],
        adapter_name="ma_2021",
        adapter_version="1",
        adapter_config_json={"sheet": "participants"},
        authority_state="SOURCE_REPORTED_ONLY",
        supersedes_version_id=None,
        parent_record_sha256=None,
        record_sha256="d" * 64,
    )
    stimulus = _row("stimulus-v1", study_version_id=study.id)
    component = _row("component-v1", stimulus_version_id=stimulus.id)
    condition = _row("condition-v1", study_version_id=study.id)
    unit = _row(
        "unit-v1",
        study_version_id=study.id,
        unit_grain="PARTICIPANT",
        pseudonymous_token="PRIVATE-SUBJECT-47",
    )
    observation = _row(
        "observation-v1",
        study_version_id=study.id,
        observation_grain="INDIVIDUAL",
        endpoint_key="MA2021_PARTICIPANT_TRIAL_VECTOR",
        missingness="OBSERVED",
        aggregation_statistic="RAW",
        trial_key="trial-1",
        session_key="session-private",
        presentation_json=[{"blind_label": "A"}],
        value_json={"IA": "5.0"},
    )
    crosswalk = _row(
        "crosswalk-v1",
        component_id=component.id,
        resolution_status="CONFLICT",
    )
    conflict = _row(
        "conflict-v1",
        study_version_id=study.id,
        conflict_state="OPEN",
    )
    snapshot = _snapshot(
        source_documents=(source,),
        source_extractions=(extraction,),
        external_study_versions=(study,),
        external_stimuli=(stimulus,),
        external_stimulus_components=(component,),
        external_conditions=(condition,),
        external_experimental_units=(unit,),
        external_observations=(observation,),
        external_identity_crosswalks=(crosswalk,),
        external_study_conflicts=(conflict,),
    )

    strict = build_science_report(snapshot, ScienceView.STRICT)
    exploratory = build_science_report(snapshot, ScienceView.EXPLORATORY)
    strict_section = _section(strict, "external_study_versions")
    exploratory_record = _section(
        exploratory, "external_study_versions"
    ).included[0]

    assert strict_section.included == ()
    assert strict_section.withheld[0].strict_reason_codes == (
        "SOURCE_REPORTED_ONLY",
    )
    assert exploratory_record.evidence_class == "LITERATURE_DERIVED"
    assert exploratory_record.facts["child_counts"] == {
        "conditions": 1,
        "conflicts": 1,
        "experimental_units": 1,
        "identity_crosswalks": 1,
        "observations": 1,
        "stimuli": 1,
        "stimulus_components": 1,
    }
    assert exploratory_record.facts["unit_grains"] == ["PARTICIPANT"]
    assert exploratory_record.facts["observation_grains"] == ["INDIVIDUAL"]
    assert exploratory_record.facts["missingness_counts"] == {"OBSERVED": 1}
    assert exploratory_record.facts["crosswalk_status_counts"] == {
        "CONFLICT": 1
    }
    assert exploratory_record.facts["conflict_state_counts"] == {"OPEN": 1}
    assert exploratory_record.facts["adapter_config_sha256"] == sha256(
        b'{"sheet":"participants"}'
    ).hexdigest()
    assert exploratory_record.authority == {
        "authority_state": "SOURCE_REPORTED_ONLY",
        "execution_authorized": False,
        "promotion_authorized": False,
        "release_authority": False,
    }
    serialized = exploratory.model_dump_json()
    for private_value in (
        "PRIVATE-SUBJECT-47",
        "trial-1",
        "session-private",
        '"blind_label"',
        '"IA"',
    ):
        assert private_value not in serialized


def test_b9_strict_separates_unknowns_but_exploratory_preserves_labels():
    reviewed = _row(
        "source-reviewed",
        source_id="source-a",
        version_number=1,
        schema_version="lab-source-document-v1",
        source_type="PRIMARY_PEER_REVIEWED_PAPER",
        title="Measured threshold study",
        authors_json=["Researcher"],
        issuing_organization=None,
        container_title="Journal",
        publisher_or_authority="Publisher",
        identifiers_json={"doi": "10.1000/example"},
        publication_date=None,
        revision_date=None,
        effective_date=None,
        retrieval_date=None,
        edition_or_amendment=None,
        default_locator_json={"page": 12, "table": "2"},
        artifact_sha256="a" * 64,
        license_or_reuse_restriction="metadata-only",
        language="en",
        original_unit=None,
        original_terminology=None,
        reviewer_pseudonym="reviewer-a",
        review_state="REVIEWED",
        supersedes_version_id=None,
        independence_group="doi-example",
        preserved_artifact_path="private/source.pdf",
        parent_record_sha256=None,
        record_sha256="b" * 64,
    )
    speculative = _row(
        "source-speculative",
        source_id="source-b",
        version_number=1,
        schema_version="lab-source-document-v1",
        source_type="AI_GENERATED_HYPOTHESIS",
        title="Unreviewed hypothesis",
        authors_json=[],
        issuing_organization="Local model",
        container_title=None,
        publisher_or_authority=None,
        identifiers_json={},
        publication_date=None,
        revision_date=None,
        effective_date=None,
        retrieval_date=None,
        edition_or_amendment=None,
        default_locator_json={},
        artifact_sha256="c" * 64,
        license_or_reuse_restriction=None,
        language="en",
        original_unit=None,
        original_terminology=None,
        reviewer_pseudonym=None,
        review_state="UNREVIEWED",
        supersedes_version_id=None,
        independence_group="hypothesis",
        preserved_artifact_path="private/hypothesis.json",
        parent_record_sha256=None,
        record_sha256="d" * 64,
    )

    strict = build_science_report(
        _snapshot(source_documents=(speculative, reviewed)),
        ScienceView.STRICT,
    )
    exploratory = build_science_report(
        _snapshot(source_documents=(speculative, reviewed)),
        ScienceView.EXPLORATORY,
    )

    strict_sources = _section(strict, "source_documents")
    exploratory_sources = _section(exploratory, "source_documents")
    assert [record.id for record in strict_sources.included] == ["source-reviewed"]
    assert [record.id for record in strict_sources.withheld] == [
        "source-speculative"
    ]
    assert strict_sources.withheld[0].evidence_class == "SPECULATIVE"
    assert set(strict_sources.withheld[0].strict_reason_codes) == {
        "MISSING_EXACT_LOCATOR",
        "SOURCE_NOT_REVIEWED",
    }
    assert [record.id for record in exploratory_sources.included] == [
        "source-reviewed",
        "source-speculative",
    ]
    assert exploratory_sources.included[1].evidence_class == "SPECULATIVE"
    assert exploratory_sources.included[1].strict_eligible is False
    assert exploratory_sources.withheld == ()

    serialized = exploratory.model_dump(mode="json")
    assert "preserved_artifact_path" not in _keys(serialized)
    assert "raw_source_path" not in _keys(serialized)


def test_b9_strict_policy_keeps_negative_authority_and_withholds_weak_evidence():
    measured = _row(
        "observation-measured",
        schema_version="lab-property-observation-v1",
        identity_scope="CHEMICAL_ENTITY",
        subject_identity_json={"chemical_name": "Linalool", "cas": "78-70-6"},
        subject_identity_sha256="1" * 64,
        property_type="vapor_pressure",
        value_kind="NUMERIC",
        numeric_value=7.0,
        categorical_value=None,
        interval_lower=None,
        interval_upper=None,
        distribution_json=None,
        censoring_qualifier=None,
        censoring_limit=None,
        original_unit="Pa",
        canonical_unit="Pa",
        temperature_k=298.15,
        pressure_pa=101325.0,
        relative_humidity_percent=None,
        matrix="air",
        phase="gas",
        purity_fraction=0.99,
        method="published measurement",
        source_version_id="source-reviewed",
        extraction_record_id="extraction-a",
        source_locator_json={"page": 12, "table": "2"},
        replicate_count=3,
        statistic="mean",
        standard_uncertainty=0.5,
        uncertainty_interval_json={},
        evidence_class="MEASURED",
        review_state="ACCEPTED_FOR_SCOPED_USE",
        quality_flags_json=[],
        applicability_domain_json={"matrix": "air"},
        provenance_activity_json={"actor": "reviewer-a"},
        supersedes_observation_id=None,
        content_sha256="2" * 64,
    )
    heuristic = _clone(
        measured,
        "observation-heuristic",
        evidence_class="HEURISTIC",
        source_locator_json={"note": "estimated"},
        content_sha256="3" * 64,
    )
    conflict = _row(
        "conflict-open",
        schema_version="lab-property-conflict-v1",
        requested_identity_json={"chemical_name": "Linalool"},
        requested_identity_sha256="4" * 64,
        property_type="vapor_pressure",
        requested_conditions_json={"temperature_k": 298.15},
        state="UNRESOLVED",
        materiality="BLOCKING",
        difference_dimensions_json=["value"],
        explanation="Two accepted measurements disagree.",
        content_sha256="5" * 64,
    )
    blocked_claim = _row(
        "claim-blocked",
        authority_id="authority-a",
        version_number=1,
        parent_version_id=None,
        legacy_claim_assessment_version_id="legacy-a",
        schema_version="lab-claim-authority-v1",
        policy_version="b7-v1",
        policy_sha256="6" * 64,
        policy_json={},
        claim_type="PROPERTY_VALUE",
        subject_type="MATERIAL",
        subject_id="material-a",
        claim_payload_json={"property_type": "vapor_pressure"},
        identity_scope_json={"material_id": "material-a"},
        identity_scope_sha256="7" * 64,
        condition_scope_json={"temperature_k": 298.15},
        condition_scope_sha256="8" * 64,
        claim_scope_sha256="9" * 64,
        decision="BLOCK",
        dimension_results_json={"evidence": "FAIL"},
        supporting_observations_json=[],
        conflicts_json=["conflict-open"],
        missing_requirements_json=[],
        source_references_json=[],
        uncertainty_json={},
        permitted_wording="The scoped claim is blocked.",
        forbidden_wording="Exact value established.",
        blocker_count=1,
        conflict_count=1,
        missing_requirement_count=0,
        critical_unknown_count=0,
        support_count=0,
        source_reference_count=0,
        release_authority=False,
        upstream_hashes_json={},
        reviewer_pseudonym="reviewer-b",
        reviewed_at=NOW,
        content_sha256="a" * 64,
        parent_sha256=None,
    )

    report = build_science_report(
        _snapshot(
            property_observations=(heuristic, measured),
            property_conflict_sets=(conflict,),
            claim_authority_decisions=(blocked_claim,),
        ),
        ScienceView.STRICT,
    )

    observations = _section(report, "property_observations")
    conflicts = _section(report, "property_conflict_sets")
    claims = _section(report, "claim_authority_decisions")
    assert [record.id for record in observations.included] == [
        "observation-measured"
    ]
    assert [record.id for record in observations.withheld] == [
        "observation-heuristic"
    ]
    assert observations.withheld[0].evidence_class == "HEURISTIC"
    assert "NON_AUTHORITATIVE_EVIDENCE_CLASS" in (
        observations.withheld[0].strict_reason_codes
    )
    assert conflicts.included == ()
    assert conflicts.withheld[0].strict_reason_codes == (
        "CONFLICT_UNRESOLVED",
    )
    assert [record.id for record in claims.included] == ["claim-blocked"]
    assert claims.included[0].authority["decision"] == "BLOCK"
    assert claims.included[0].evidence_class == "UNKNOWN"
    assert claims.included[0].strict_eligible is True


def test_b9_report_and_markdown_are_deterministic_and_preserve_locators():
    first = _row(
        "source-z",
        source_id="source-z",
        version_number=1,
        schema_version="lab-source-document-v1",
        source_type="SUPPLIER_COA",
        title="Supplier COA",
        authors_json=[],
        issuing_organization="Supplier",
        container_title=None,
        publisher_or_authority="Supplier",
        identifiers_json={"document": "COA-1"},
        publication_date=None,
        revision_date=None,
        effective_date=None,
        retrieval_date=None,
        edition_or_amendment="1",
        default_locator_json={"page": 2, "section": "Specification"},
        artifact_sha256="e" * 64,
        license_or_reuse_restriction="metadata-only",
        language="en",
        original_unit=None,
        original_terminology=None,
        reviewer_pseudonym="reviewer",
        review_state="REVIEWED",
        supersedes_version_id=None,
        independence_group="supplier-coa",
        preserved_artifact_path="local/private.pdf",
        parent_record_sha256=None,
        record_sha256="f" * 64,
    )
    second = _clone(
        first,
        "source-a",
        source_id="source-a",
        title="Earlier source",
        source_type="LOCAL_ANALYTICAL_EXPERIMENT",
        record_sha256="0" * 64,
    )

    report_a = build_science_report(
        _snapshot(source_documents=(first, second)),
        ScienceView.STRICT,
    )
    report_b = build_science_report(
        _snapshot(source_documents=(second, first)),
        ScienceView.STRICT,
    )
    markdown_a = render_science_report_markdown(report_a)
    markdown_b = render_science_report_markdown(report_b)

    assert report_a.model_dump(mode="json") == report_b.model_dump(mode="json")
    assert report_a.report_sha256 == report_b.report_sha256
    assert markdown_a == markdown_b
    assert [record.id for record in _section(report_a, "source_documents").included] == [
        "source-a",
        "source-z",
    ]
    assert "SUPPLIER_PROVIDED" in markdown_a
    assert "MEASURED" in markdown_a
    assert "page" in markdown_a
    assert "Specification" in markdown_a
    assert "confidence percentage" not in markdown_a.casefold()
    assert "%" not in markdown_a


def test_b9_source_use_constraints_are_explicit_and_nonpromoting():
    subject = _row(
        "source-subject",
        source_id="subject",
        version_number=1,
        schema_version="lab-source-document-v2",
        source_type="PRIMARY_RESEARCH_DATASET",
        title="Study dataset",
        authors_json=["Researcher"],
        issuing_organization=None,
        container_title=None,
        publisher_or_authority="Repository",
        identifiers_json={"doi": "10.1000/dataset"},
        publication_date=None,
        revision_date=None,
        effective_date=None,
        retrieval_date=None,
        edition_or_amendment=None,
        default_locator_json={"artifact_id": "dataset-v2"},
        artifact_sha256="1" * 64,
        license_or_reuse_restriction="dataset terms",
        rights_json={},
        language="en",
        original_unit=None,
        original_terminology=None,
        reviewer_pseudonym="reviewer",
        review_state="REVIEWED",
        supersedes_version_id=None,
        independence_group="dataset",
        parent_record_sha256=None,
        record_sha256="2" * 64,
    )
    terms = _clone(
        subject,
        "source-terms",
        source_id="terms",
        source_type="REGULATION_OR_OFFICIAL_GUIDANCE",
        title="Dataset terms",
        identifiers_json={"url": "https://example.test/terms"},
        default_locator_json={"section": "reuse"},
        artifact_sha256="3" * 64,
        independence_group="terms",
        record_sha256="4" * 64,
    )
    allowed = _row(
        "source-use-allowed",
        constraint_id="constraint-allowed",
        version_number=1,
        subject_source_version_id=subject.id,
        terms_source_version_id=terms.id,
        artifact_scope="DATASET",
        artifact_locator_json={"artifact_id": "dataset-v2"},
        channel="official-data-repository",
        intended_action="INTERNAL_ANALYSIS",
        purpose_context="method-development",
        decision="DECLARED_ALLOWED",
        constraints_json={"attribution_required": True},
        terms_effective_date=None,
        terms_retrieval_date=None,
        reviewer_pseudonym="rights-reviewer",
        review_state="REVIEWED",
        legal_review_required=False,
        supersedes_version_id=None,
        parent_record_sha256=None,
        record_sha256="5" * 64,
    )
    held = _clone(
        allowed,
        "source-use-held",
        constraint_id="constraint-held",
        decision="UNRESOLVED",
        legal_review_required=True,
        record_sha256="6" * 64,
    )

    report = build_science_report(
        _snapshot(
            source_documents=(subject, terms),
            source_use_constraints=(held, allowed),
        ),
        ScienceView.STRICT,
    )
    section = _section(report, "source_use_constraints")
    assert [record.id for record in section.included] == [allowed.id]
    assert [record.id for record in section.withheld] == [held.id]
    projected = section.included[0]
    assert projected.evidence_class == "LITERATURE_DERIVED"
    assert projected.authority == {
        "decision": "DECLARED_ALLOWED",
        "review_state": "REVIEWED",
        "legal_review_required": False,
        "authority_state": (
            "SOURCE_DECLARATION_ONLY_NOT_LEGAL_CONCLUSION"
        ),
    }
    assert projected.facts["intended_action"] == "INTERNAL_ANALYSIS"
    assert projected.provenance["artifact_locator"] == {
        "artifact_id": "dataset-v2"
    }
    assert set(section.withheld[0].strict_reason_codes) == {
        "LEGAL_REVIEW_REQUIRED",
        "SOURCE_USE_DECISION_UNRESOLVED",
    }
    assert "integration_allowed" not in _keys(report.model_dump(mode="json"))


def test_b9_repository_has_exact_read_only_collection_map():
    assert tuple(REPORT_MODEL_COLLECTIONS) == REPORT_COLLECTION_KEYS
    assert len(REPORT_MODEL_COLLECTIONS) == 34
    assert not hasattr(ScienceReportRepository, "add")
    assert not hasattr(ScienceReportRepository, "delete")
    assert not hasattr(ScienceReportRepository, "commit")


@pytest.mark.asyncio
async def test_b9_service_reads_one_snapshot_and_uses_exact_parent_links():
    source = _row(
        "source-a",
        source_id="source-a",
        version_number=1,
        schema_version="lab-source-document-v1",
        source_type="PRIMARY_PEER_REVIEWED_PAPER",
        title="Canonical source",
        authors_json=["Researcher"],
        issuing_organization=None,
        container_title="Journal",
        publisher_or_authority="Publisher",
        identifiers_json={"doi": "10.1000/a"},
        publication_date=None,
        revision_date=None,
        effective_date=None,
        retrieval_date=None,
        edition_or_amendment=None,
        default_locator_json={"page": 4},
        artifact_sha256="1" * 64,
        license_or_reuse_restriction=None,
        language="en",
        original_unit=None,
        original_terminology=None,
        reviewer_pseudonym="reviewer",
        review_state="REVIEWED",
        supersedes_version_id=None,
        independence_group="source-a",
        parent_record_sha256=None,
        record_sha256="2" * 64,
    )
    extraction = _row(
        "extraction-a",
        source_version_id=source.id,
        locator_json={"page": 4, "row": "Linalool"},
        structure_context_json={},
        original_value_json={"value": 7.0, "unit": "Pa"},
        parsed_value_json={"value": 7.0, "unit": "Pa"},
        normalization_json={},
        parser_or_model_version="manual-v1",
        reviewer_pseudonym="reviewer",
        uncertainty_json={},
        ambiguity_json=[],
        output_observation_id="observation-a",
        input_sha256="3" * 64,
        output_sha256="4" * 64,
        record_sha256="5" * 64,
    )
    staged = _row(
        "event-1",
        subject_id=extraction.id,
        sequence_number=1,
        to_state="STAGED",
    )
    accepted = _row(
        "event-2",
        subject_id=extraction.id,
        sequence_number=2,
        to_state="ACCEPTED_FOR_SCOPED_USE",
    )
    rule_a = _row(
        "rule-a",
        rule_key="rule-a",
        version=1,
        subject_kind="EXACT_IDENTITY",
        subject_raw_label="Linalool",
        relation="REINFORCES",
        object_kind="EXACT_IDENTITY",
        object_raw_label="Lavender",
        directionality="DIRECTED",
        matrix_context_json={},
        dose_domain_json={},
        temporal_domain_json={},
        expected_effect_json={},
        attribute="floral lift",
        rationale="Controlled comparison",
        source_document_version_id=source.id,
        source_extraction_id=extraction.id,
        source_locator="page 4",
        evidence_class="CONTROLLED_EXPERIMENT",
        uncertainty_json={},
        review_state="APPROVED",
        status="SUPPORTED",
        runtime_role="ADVISORY",
        numerical_model_ref=None,
        supersedes_rule_id=None,
        raw_json_pointer="/rules/0",
        raw_payload_sha256="6" * 64,
        compiler_diagnostics_json=[],
        subject_identity_scope_sha256="7" * 64,
        subject_group_id=None,
        object_identity_scope_sha256="8" * 64,
        object_group_id=None,
        content_sha256="9" * 64,
    )
    rule_b = _clone(
        rule_a,
        "rule-b",
        rule_key="rule-b",
        relation="MASKS",
        raw_json_pointer="/rules/1",
        raw_payload_sha256="a" * 64,
        content_sha256="b" * 64,
    )
    contradiction = _row(
        "contradiction-a",
        rule_id=rule_a.id,
        contradictory_rule_id=rule_b.id,
        reason_code="OPPOSITE_DIRECTION",
        rationale="The scoped effects conflict.",
        blocking=True,
        content_sha256="c" * 64,
    )
    support = _row(
        "rule-support-a",
        rule_id=rule_a.id,
        support_kind="TEST_ARTIFACT",
        reference_id="test-a",
        controlled=True,
        matrix_context_sha256=None,
        dose_domain_sha256=None,
        uncertainty_json={},
        review_state="APPROVED",
        content_sha256="d" * 64,
    )
    claim = _row(
        "claim-a",
        authority_id="authority-a",
        version_number=1,
        parent_version_id=None,
        legacy_claim_assessment_version_id="legacy-a",
        schema_version="lab-claim-authority-v1",
        policy_version="b7-v1",
        policy_sha256="e" * 64,
        policy_json={},
        claim_type="KNOWLEDGE_RULE_RECOMMENDATION",
        subject_type="MATERIAL",
        subject_id="material-a",
        claim_payload_json={"rule_id": rule_a.id},
        identity_scope_json={"material_id": "material-a"},
        identity_scope_sha256="f" * 64,
        condition_scope_json={},
        condition_scope_sha256="0" * 64,
        claim_scope_sha256="1" * 64,
        decision="ALLOW_SCOPED",
        dimension_results_json={},
        supporting_observations_json=[],
        conflicts_json=[],
        missing_requirements_json=[],
        source_references_json=[{"source_version_id": source.id}],
        uncertainty_json={},
        permitted_wording="Supported for the declared scope.",
        forbidden_wording="Universal recommendation.",
        blocker_count=0,
        conflict_count=0,
        missing_requirement_count=0,
        critical_unknown_count=0,
        support_count=1,
        source_reference_count=1,
        release_authority=False,
        upstream_hashes_json={},
        reviewer_pseudonym="reviewer",
        reviewed_at=NOW,
        content_sha256="2" * 64,
        parent_sha256=None,
    )
    claim_support = _row(
        "claim-support-a",
        claim_authority_version_id=claim.id,
        support_kind="KNOWLEDGE_RULE",
        role="SUPPORTING",
        property_assertion_id=None,
        oav_assessment_id=None,
        knowledge_rule_id=rule_a.id,
        analytical_assessment_id=None,
        composition_profile_id=None,
        regulatory_snapshot_version_id=None,
        upstream_content_sha256=rule_a.content_sha256,
        derived_facts_json={},
        source_references_json=[{"source_version_id": source.id}],
        content_sha256="3" * 64,
    )
    orphan_support = _clone(
        claim_support,
        "claim-support-orphan",
        claim_authority_version_id="missing-claim",
        content_sha256="4" * 64,
    )

    class FakeRepository:
        calls = 0

        async def snapshot(self):
            self.calls += 1
            return _snapshot(
                source_documents=(source,),
                source_extractions=(extraction,),
                source_workflow_events=(accepted, staged),
                knowledge_rules=(rule_b, rule_a),
                rule_contradictions=(contradiction,),
                rule_support_evidence=(support,),
                claim_authority_decisions=(claim,),
                claim_authority_support=(orphan_support, claim_support),
            )

    repository = FakeRepository()
    service = ScienceReportingService(repository)
    report = await service.authority_report(ScienceView.STRICT)

    assert repository.calls == 1
    assert [
        record.id for record in _section(report, "source_extractions").included
    ] == [extraction.id]
    rule_records = _section(report, "knowledge_rules")
    assert rule_records.included == ()
    assert {record.id for record in rule_records.withheld} == {
        rule_a.id,
        rule_b.id,
    }
    projected_rule_a = next(
        record for record in rule_records.withheld if record.id == rule_a.id
    )
    assert projected_rule_a.evidence_class == "MEASURED"
    assert projected_rule_a.facts["support_evidence_ids"] == [support.id]
    assert "RULE_BLOCKING_CONTRADICTION" in projected_rule_a.strict_reason_codes
    support_records = _section(report, "claim_authority_support")
    assert [record.id for record in support_records.included] == [
        claim_support.id
    ]
    assert [record.id for record in support_records.withheld] == [
        orphan_support.id
    ]
    assert support_records.withheld[0].strict_reason_codes == (
        "CLAIM_PARENT_MISSING",
    )
