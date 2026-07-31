from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.schemas.lab_reporting import (
    SCIENCE_EVIDENCE_CLASSES,
    SCIENCE_SECTION_KEYS,
    ScienceView,
)
from app.services.lab_reporting import (
    REPORT_COLLECTION_KEYS,
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
    )
    assert tuple(section.key for section in report.sections) == SCIENCE_SECTION_KEYS
    assert report.schema_version == "lab-science-authority-report-v1"
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
