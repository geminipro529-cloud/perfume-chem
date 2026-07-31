from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

import pytest

from app.models.lab import LabFormula, LabFormulaVersion
from app.models.lab_properties import (
    LabPropertyObservation,
    LabSelectedAssertion,
)
from app.models.lab_rules import LabKnowledgeRule
from app.models.lab_science import LabClaimAssessmentVersion
from app.models.lab_sources import (
    LabSourceDocumentVersion,
    LabSourceExtractionRecord,
)
from app.models.lab_thresholds import (
    LabOAVAssessment,
    LabThresholdObservationContext,
)
from app.services.lab_claims import (
    ClaimAuthorityConflictError,
    ClaimAuthorityEvaluationInput,
    ClaimAuthoritySupportInput,
    canonical_json_sha256,
)
from app.services.lab_service import LabService
from tests.unit.test_b5_analytical_service import (
    _claim_request,
    _complete_peak_authority_graph,
    _record_required_qc,
    _validation_input,
)
from tests.unit.test_b6_regulatory_service import (
    _composition_document_binding,
    _composition_profile_input,
    _evaluation_input,
    _evaluation_stock,
    _formula_version_for_stocks,
    _natural_stock,
    _regulatory_rule_graph,
    _required_supplier_bindings,
)

NOW = datetime(2026, 7, 31, 0, 0, tzinfo=timezone.utc)


def _digest(label: str) -> str:
    return sha256(label.encode("utf-8")).hexdigest()


async def _formula_subject(db_session, label: str):
    formula = LabFormula(name=f"B7 {label}")
    db_session.add(formula)
    await db_session.flush()
    version = LabFormulaVersion(
        formula_id=formula.id,
        version_number=1,
        brief_json={"fixture": label},
        constraints_json={},
        concentration_fraction=0.2,
        concentration_basis="MASS_FRACTION",
        source_json={},
    )
    db_session.add(version)
    await db_session.flush()
    return version


async def _legacy_claim(
    db_session,
    *,
    claim_type: str,
    subject_type: str,
    subject_id: str,
    label: str,
):
    record = LabClaimAssessmentVersion(
        claim_id=str(uuid4()),
        version_number=1,
        schema_version="a4-claim-v1",
        claim_type=claim_type,
        subject_type=subject_type,
        subject_id=subject_id,
        parent_version_id=None,
        policy_version="a4-policy-v1",
        decision="ALLOW_EXACT",
        authority_json={"all_caller_booleans": True},
        missing_evidence_json=[],
        conflicts_json=[],
        permitted_wording="Legacy historical wording.",
        forbidden_wording=None,
        human_review_state="APPROVED",
        reviewer_pseudonym="legacy-reviewer",
        reviewed_at=NOW,
        content_sha256=_digest(f"legacy:{label}"),
        parent_sha256=None,
    )
    db_session.add(record)
    await db_session.flush()
    return record


async def _legacy_claim_revision(
    db_session,
    parent,
    *,
    label: str,
    subject_type: str | None = None,
    subject_id: str | None = None,
):
    record = LabClaimAssessmentVersion(
        claim_id=parent.claim_id,
        version_number=parent.version_number + 1,
        schema_version=parent.schema_version,
        claim_type=parent.claim_type,
        subject_type=subject_type or parent.subject_type,
        subject_id=subject_id or parent.subject_id,
        parent_version_id=parent.id,
        policy_version=parent.policy_version,
        decision=parent.decision,
        authority_json=dict(parent.authority_json),
        missing_evidence_json=list(parent.missing_evidence_json),
        conflicts_json=list(parent.conflicts_json),
        permitted_wording=parent.permitted_wording,
        forbidden_wording=parent.forbidden_wording,
        human_review_state=parent.human_review_state,
        reviewer_pseudonym=parent.reviewer_pseudonym,
        reviewed_at=NOW,
        content_sha256=_digest(f"legacy-revision:{label}"),
        parent_sha256=parent.content_sha256,
    )
    db_session.add(record)
    await db_session.flush()
    return record


async def _source_graph(
    db_session,
    label: str,
    *,
    source_type: str = "PRIMARY_PEER_REVIEWED_PAPER",
):
    source = LabSourceDocumentVersion(
        source_id=str(uuid4()),
        version_number=1,
        schema_version="lab-source-document-v1",
        source_type=source_type,
        title=f"B7 source {label}",
        authors_json=["Test Author"],
        identifiers_json={"fixture": label},
        default_locator_json={"page": 1},
        artifact_sha256=_digest(f"artifact:{label}"),
        language="en",
        review_state="REVIEWED",
        independence_group=f"b7-independent:{label}",
        record_sha256=_digest(f"source:{label}"),
    )
    db_session.add(source)
    await db_session.flush()
    extraction = LabSourceExtractionRecord(
        source_version_id=source.id,
        locator_json={"page": 1, "fixture": label},
        structure_context_json={"section": "fixture"},
        original_wording=label,
        original_value_json={"fixture": label},
        parsed_value_json={"fixture": label},
        normalization_json={},
        parser_or_model_version="b7-fixture-v1",
        reviewer_pseudonym="b7-reviewer",
        uncertainty_json={"bounded": True},
        ambiguity_json=[],
        output_observation_id=None,
        input_sha256=_digest(f"input:{label}"),
        output_sha256=_digest(f"output:{label}"),
        record_sha256=_digest(f"extraction:{label}"),
    )
    db_session.add(extraction)
    await db_session.flush()
    return source, extraction


async def _property_assertion(
    db_session,
    *,
    label: str,
    identity_scope: dict,
    identity_scope_name: str,
    property_type: str,
    value,
    unit: str,
    conditions: dict,
    evidence_class: str,
    standard_uncertainty: float | None,
):
    source, extraction = await _source_graph(db_session, label)
    identity_sha256 = canonical_json_sha256(identity_scope)
    numeric = float(value) if isinstance(value, (int, float)) else None
    categorical = str(value) if isinstance(value, str) else None
    observation = LabPropertyObservation(
        schema_version="lab-property-observation-v1",
        identity_scope=identity_scope_name,
        subject_identity_json=identity_scope,
        subject_identity_sha256=identity_sha256,
        property_type=property_type,
        value_kind="NUMERIC" if numeric is not None else "CATEGORICAL",
        numeric_value=numeric,
        categorical_value=categorical,
        interval_lower=None,
        interval_upper=None,
        distribution_json=None,
        censoring_qualifier=None,
        censoring_limit=None,
        original_unit=unit,
        canonical_unit=unit,
        temperature_k=conditions.get("temperature_k"),
        pressure_pa=conditions.get("pressure_pa"),
        relative_humidity_percent=conditions.get(
            "relative_humidity_percent"
        ),
        matrix=conditions.get("matrix"),
        phase=conditions.get("phase"),
        purity_fraction=conditions.get("purity_fraction", 0.99),
        method="bounded B7 fixture",
        source_version_id=source.id,
        extraction_record_id=extraction.id,
        source_locator_json={"page": 1, "fixture": label},
        replicate_count=3,
        statistic="MEAN",
        standard_uncertainty=standard_uncertainty,
        uncertainty_interval_json={},
        evidence_class=evidence_class,
        review_state="ACCEPTED_FOR_SCOPED_USE",
        quality_flags_json=[],
        applicability_domain_json=conditions,
        provenance_activity_json={},
        supersedes_observation_id=None,
        content_sha256=_digest(f"observation:{label}"),
    )
    db_session.add(observation)
    await db_session.flush()
    relative_uncertainty = (
        standard_uncertainty / abs(numeric)
        if standard_uncertainty is not None
        and numeric is not None
        and numeric != 0
        else None
    )
    assertion = LabSelectedAssertion(
        schema_version="lab-selected-assertion-v1",
        requested_identity_json=identity_scope,
        requested_identity_sha256=identity_sha256,
        requested_property_type=property_type,
        requested_conditions_json=conditions,
        conflict_set_id=None,
        selection_policy_version="b2-selection-v1",
        selection_kind="OBSERVATION",
        selected_observation_id=observation.id,
        selected_model_json=None,
        interpolation_state="EXACT",
        propagated_uncertainty_json={
            "relative_standard_uncertainty": relative_uncertainty,
        },
        applicability_json=conditions,
        authority_state="AUTHORIZED_FOR_SCOPED_PROPERTY",
        permitted_claim_wording="Only for the declared scope.",
        content_sha256=_digest(f"assertion:{label}"),
    )
    db_session.add(assertion)
    await db_session.flush()
    return assertion, observation


def _command(
    legacy,
    *,
    payload: dict,
    identity_scope: dict,
    condition_scope: dict,
    supports: tuple[ClaimAuthoritySupportInput, ...],
):
    return ClaimAuthorityEvaluationInput(
        legacy_claim_assessment_version_id=legacy.id,
        claim_payload=payload,
        identity_scope=identity_scope,
        condition_scope=condition_scope,
        supports=supports,
        reviewer_pseudonym="b7-reviewer",
        reviewed_at=NOW,
    )


@pytest.mark.asyncio
async def test_exact_chemical_identity_requires_two_independent_b2_sources(
    db_session,
):
    subject = await _formula_subject(db_session, "exact identity")
    legacy = await _legacy_claim(
        db_session,
        claim_type="IDENTITY",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label="exact-identity",
    )
    identity = {
        "identity_scope": "CHEMICAL_ENTITY",
        "chemical_name": "Linalool",
        "identifier": "78-70-6",
    }
    first, _ = await _property_assertion(
        db_session,
        label="identity-source-a",
        identity_scope=identity,
        identity_scope_name="CHEMICAL_ENTITY",
        property_type="CHEMICAL_IDENTITY",
        value="Linalool",
        unit="dimensionless",
        conditions={},
        evidence_class="LITERATURE_DERIVED",
        standard_uncertainty=None,
    )
    second, _ = await _property_assertion(
        db_session,
        label="identity-source-b",
        identity_scope=identity,
        identity_scope_name="CHEMICAL_ENTITY",
        property_type="CHEMICAL_IDENTITY",
        value="Linalool",
        unit="dimensionless",
        conditions={},
        evidence_class="LITERATURE_DERIVED",
        standard_uncertainty=None,
    )
    service = LabService(db_session)
    authority = await service.create_claim_authority_version(
        _command(
            legacy,
            payload={
                "chemical_name": "Linalool",
                "identifier": "78-70-6",
            },
            identity_scope=identity,
            condition_scope={},
            supports=(
                ClaimAuthoritySupportInput(
                    "PROPERTY_ASSERTION",
                    first.id,
                ),
                ClaimAuthoritySupportInput(
                    "PROPERTY_ASSERTION",
                    second.id,
                ),
            ),
        )
    )

    assert authority.decision == "ALLOW_EXACT"
    assert authority.source_reference_count == 2


@pytest.mark.asyncio
async def test_grade_identity_is_exact_only_for_the_supplier_lot_scope(
    db_session,
):
    subject = await _formula_subject(db_session, "grade identity")
    legacy = await _legacy_claim(
        db_session,
        claim_type="GRADE_IDENTITY",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label="grade-identity",
    )
    identity = {
        "identity_scope": "SUPPLIER_LOT",
        "grade_name": "Natural FCF",
        "supplier_or_standard": "Supplier A",
        "lot_number": "LOT-42",
    }
    assertion, _ = await _property_assertion(
        db_session,
        label="grade-source",
        identity_scope=identity,
        identity_scope_name="SUPPLIER_LOT",
        property_type="GRADE_IDENTITY",
        value="Natural FCF",
        unit="dimensionless",
        conditions={},
        evidence_class="SUPPLIER_PROVIDED",
        standard_uncertainty=None,
    )
    authority = await LabService(
        db_session
    ).create_claim_authority_version(
        _command(
            legacy,
            payload={
                "grade_name": "Natural FCF",
                "supplier_or_standard": "Supplier A",
            },
            identity_scope=identity,
            condition_scope={},
            supports=(
                ClaimAuthoritySupportInput(
                    "PROPERTY_ASSERTION",
                    assertion.id,
                ),
            ),
        )
    )

    assert authority.decision == "ALLOW_EXACT"


@pytest.mark.asyncio
async def test_contextual_threshold_is_exact_only_for_its_b3_context(
    db_session,
):
    subject = await _formula_subject(db_session, "threshold")
    legacy = await _legacy_claim(
        db_session,
        claim_type="THRESHOLD",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label="threshold",
    )
    identity = {
        "identity_scope": "CHEMICAL_ENTITY",
        "chemical_name": "Linalool",
        "identifier": "78-70-6",
    }
    assertion, observation = await _property_assertion(
        db_session,
        label="threshold-source",
        identity_scope=identity,
        identity_scope_name="CHEMICAL_ENTITY",
        property_type="ODOR_THRESHOLD",
        value=0.001,
        unit="mg/m3",
        conditions={"temperature_k": 298.15},
        evidence_class="LITERATURE_DERIVED",
        standard_uncertainty=0.0001,
    )
    context = LabThresholdObservationContext(
        observation_id=observation.id,
        schema_version="lab-threshold-context-v1",
        endpoint="DETECTION",
        route="ORTHONASAL",
        medium="AIR",
        matrix_specification_state="SPECIFIED",
        matrix_composition_json={"carrier": "air"},
        concentration_basis="MASS_CONCENTRATION",
        apparatus_json={"method": "dynamic olfactometry"},
        population_json={"panel": "trained adults"},
        training_state="TRAINED",
        sample_size=24,
        psychophysical_procedure="ascending forced choice",
        content_sha256=_digest("threshold-context"),
    )
    db_session.add(context)
    await db_session.flush()
    condition_scope = {
        "endpoint": "DETECTION",
        "route": "ORTHONASAL",
        "medium": "AIR",
        "matrix_specification_state": "SPECIFIED",
        "matrix_composition": {"carrier": "air"},
        "concentration_basis": "MASS_CONCENTRATION",
        "temperature_k": 298.15,
        "pressure_pa": None,
        "relative_humidity_percent": None,
    }
    authority = await LabService(
        db_session
    ).create_claim_authority_version(
        _command(
            legacy,
            payload={
                "threshold_value": 0.001,
                "unit": "mg/m3",
                "endpoint": "DETECTION",
                "route": "ORTHONASAL",
                "medium": "AIR",
            },
            identity_scope=identity,
            condition_scope=condition_scope,
            supports=(
                ClaimAuthoritySupportInput(
                    "PROPERTY_ASSERTION",
                    assertion.id,
                ),
            ),
        )
    )

    assert authority.decision == "ALLOW_EXACT"


@pytest.mark.asyncio
async def test_strict_b3_oav_produces_scoped_screening_not_exactness(
    db_session,
):
    subject = await _formula_subject(db_session, "oav")
    legacy = await _legacy_claim(
        db_session,
        claim_type="ABOVE_THRESHOLD_LIKELIHOOD",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label="oav",
    )
    identity = {
        "identity_scope": "CHEMICAL_ENTITY",
        "chemical_name": "Linalool",
        "identifier": "78-70-6",
    }
    concentration_assertion, concentration = await _property_assertion(
        db_session,
        label="oav-concentration",
        identity_scope=identity,
        identity_scope_name="CHEMICAL_ENTITY",
        property_type="CONCENTRATION",
        value=0.005,
        unit="mg/m3",
        conditions={
            "concentration_basis": "MASS_CONCENTRATION",
            "medium": "AIR",
            "route": "ORTHONASAL",
        },
        evidence_class="MEASURED",
        standard_uncertainty=0.0002,
    )
    threshold_assertion, threshold = await _property_assertion(
        db_session,
        label="oav-threshold",
        identity_scope=identity,
        identity_scope_name="CHEMICAL_ENTITY",
        property_type="ODOR_THRESHOLD",
        value=0.001,
        unit="mg/m3",
        conditions={"temperature_k": 298.15},
        evidence_class="LITERATURE_DERIVED",
        standard_uncertainty=0.0001,
    )
    db_session.add(
        LabThresholdObservationContext(
            observation_id=threshold.id,
            schema_version="lab-threshold-context-v1",
            endpoint="DETECTION",
            route="ORTHONASAL",
            medium="AIR",
            matrix_specification_state="SPECIFIED",
            matrix_composition_json={"carrier": "air"},
            concentration_basis="MASS_CONCENTRATION",
            apparatus_json={"method": "dynamic olfactometry"},
            population_json={"panel": "trained adults"},
            training_state="TRAINED",
            sample_size=24,
            psychophysical_procedure="ascending forced choice",
            content_sha256=_digest("oav-threshold-context"),
        )
    )
    condition_scope = {
        "endpoint": "DETECTION",
        "route": "ORTHONASAL",
        "matrix": "air-screening",
    }
    oav = LabOAVAssessment(
        schema_version="lab-oav-assessment-v1",
        concentration_observation_id=concentration.id,
        threshold_assertion_id=threshold_assertion.id,
        requested_endpoint="DETECTION",
        requested_route="ORTHONASAL",
        strict_science_mode=True,
        status="COMPUTED",
        oav_value=5.0,
        mismatch_count=0,
        mismatch_codes_json=[],
        conversion_prerequisites_json={},
        input_snapshot_json={
            "condition_scope": condition_scope,
            "concentration": 0.005,
            "threshold": 0.001,
            "basis": "MASS_CONCENTRATION",
        },
        permitted_uses_json=["SCREENING"],
        prohibited_claims_json=["SENSORY_INTENSITY"],
        content_sha256=_digest("oav-assessment"),
    )
    db_session.add(oav)
    await db_session.flush()
    del concentration_assertion
    authority = await LabService(
        db_session
    ).create_claim_authority_version(
        _command(
            legacy,
            payload={
                "concentration": 0.005,
                "threshold": 0.001,
                "basis": "MASS_CONCENTRATION",
                "endpoint": "DETECTION",
                "route": "ORTHONASAL",
            },
            identity_scope=identity,
            condition_scope=condition_scope,
            supports=(
                ClaimAuthoritySupportInput("OAV_ASSESSMENT", oav.id),
            ),
        )
    )

    assert authority.decision == "ALLOW_SCOPED"
    assert authority.release_authority is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("claim_type", "b5_claim_type", "payload"),
    (
        (
            "ANALYTICAL_IDENTITY",
            "IDENTITY",
            {"analyte": "linalool", "identity_label": "linalool"},
        ),
        (
            "ANALYTICAL_QUANTITY",
            "QUANTITY",
            {"analyte": "linalool", "value": 0.2, "unit": "mg/mL"},
        ),
    ),
)
async def test_b5_validated_assessments_authorize_analytical_claims(
    db_session,
    claim_type,
    b5_claim_type,
    payload,
):
    service = LabService(db_session)
    graph = await _complete_peak_authority_graph(service)
    await _record_required_qc(
        service,
        graph["run"].id,
        graph["method"].evidence_record_id,
    )
    assessment = await service.assess_analytical_claim(
        _claim_request(graph, claim_type=b5_claim_type)
    )
    legacy = await _legacy_claim(
        db_session,
        claim_type=claim_type,
        subject_type="ANALYTICAL_RUN",
        subject_id=graph["run"].id,
        label=f"analytical:{b5_claim_type}",
    )
    identity_scope = {
        "analytical_run_id": graph["run"].id,
        "identity_label": "linalool",
    }
    authority = await service.create_claim_authority_version(
        _command(
            legacy,
            payload=payload,
            identity_scope=identity_scope,
            condition_scope={},
            supports=(
                ClaimAuthoritySupportInput(
                    "ANALYTICAL_ASSESSMENT",
                    assessment.id,
                ),
            ),
        )
    )

    assert authority.decision == "ALLOW_EXACT"


@pytest.mark.asyncio
async def test_complete_lot_specific_b6_profile_authorizes_natural_profile(
    db_session,
):
    service = LabService(db_session)
    stock = await _natural_stock(service)
    binding = await _composition_document_binding(service, stock.id)
    profile = await service.record_regulatory_composition_profile(
        _composition_profile_input(stock.id, binding.id)
    )
    subject = await _formula_version_for_stocks(
        service,
        (stock,),
        finished_concentration=0.1,
    )
    legacy = await _legacy_claim(
        db_session,
        claim_type="NATURAL_CONSTITUENT_PROFILE",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label="natural-profile",
    )
    identity_scope = {
        "stock_solution_id": stock.id,
        "supplier_identity_sha256": binding.supplier_identity_sha256,
    }
    condition_scope = {
        "stock_solution_id": stock.id,
        "scope": "SUPPLIER_LOT",
        "lot_number": "LOT-42",
    }
    authority = await service.create_claim_authority_version(
        _command(
            legacy,
            payload={
                "stock_solution_id": stock.id,
                "composition_basis": "LOT_SPECIFIC",
            },
            identity_scope=identity_scope,
            condition_scope=condition_scope,
            supports=(
                ClaimAuthoritySupportInput(
                    "COMPOSITION_PROFILE",
                    profile.id,
                ),
            ),
        )
    )

    assert authority.decision == "ALLOW_EXACT"


async def _knowledge_rule(
    db_session,
    *,
    label: str,
    source_label: str,
    model_ref: str | None = None,
    model_applicable: bool | None = None,
):
    source, extraction = await _source_graph(db_session, source_label)
    uncertainty = {
        "bounded": True,
        "relative_standard_uncertainty": 0.1,
    }
    if model_applicable is not None:
        uncertainty["applicable"] = model_applicable
    rule = LabKnowledgeRule(
        rule_key=label,
        version=1,
        subject_kind="EXACT_IDENTITY",
        subject_raw_label="left formula",
        subject_identity_scope_sha256="1" * 64,
        subject_group_id=None,
        relation="REINFORCES",
        object_kind="EXACT_IDENTITY",
        object_raw_label="right formula",
        object_identity_scope_sha256="2" * 64,
        object_group_id=None,
        directionality="DIRECTED",
        matrix_context_json={"medium": "ethanol"},
        dose_domain_json={"minimum": 0.01, "maximum": 0.1},
        temporal_domain_json={"phase": "heart"},
        expected_effect_json={"direction": "increase"},
        attribute="target_similarity",
        rationale="Bounded controlled comparison.",
        source_document_version_id=source.id,
        source_extraction_id=extraction.id,
        source_locator="page 1",
        evidence_class="EMPIRICALLY_CALIBRATED",
        uncertainty_json=uncertainty,
        review_state="APPROVED",
        status="AUTHORITATIVE",
        runtime_role="ADVISORY",
        numerical_model_ref=model_ref,
        supersedes_rule_id=None,
        raw_source_path=f"evidence/{label}.json",
        raw_json_pointer="/rule",
        raw_payload_sha256=_digest(f"raw:{label}"),
        compiler_diagnostics_json=[],
        content_sha256=_digest(f"rule:{label}"),
    )
    db_session.add(rule)
    await db_session.flush()
    return rule


@pytest.mark.asyncio
async def test_b4_rule_recommendation_is_scoped_and_not_release_authority(
    db_session,
):
    subject = await _formula_subject(db_session, "knowledge rule")
    legacy = await _legacy_claim(
        db_session,
        claim_type="KNOWLEDGE_RULE_RECOMMENDATION",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label="knowledge-rule",
    )
    rule = await _knowledge_rule(
        db_session,
        label="rule-recommendation",
        source_label="rule-source",
    )
    identity_scope = {
        "subject_identity_scope_sha256": "1" * 64,
        "object_identity_scope_sha256": "2" * 64,
    }
    condition_scope = {
        "matrix_context": {"medium": "ethanol"},
        "dose_domain": {"minimum": 0.01, "maximum": 0.1},
        "temporal_domain": {"phase": "heart"},
    }
    authority = await LabService(
        db_session
    ).create_claim_authority_version(
        _command(
            legacy,
            payload={
                "rule_key": "rule-recommendation",
                "recommendation": "REINFORCES",
            },
            identity_scope=identity_scope,
            condition_scope=condition_scope,
            supports=(
                ClaimAuthoritySupportInput("KNOWLEDGE_RULE", rule.id),
            ),
        )
    )

    assert authority.decision == "ALLOW_SCOPED"
    assert authority.release_authority is False


@pytest.mark.asyncio
async def test_formula_comparison_requires_two_independent_b4_sources(
    db_session,
):
    subject = await _formula_subject(db_session, "formula comparison")
    legacy = await _legacy_claim(
        db_session,
        claim_type="TARGET_SIMILARITY",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label="formula-comparison",
    )
    first = await _knowledge_rule(
        db_session,
        label="comparison-rule-a",
        source_label="comparison-source-a",
    )
    second = await _knowledge_rule(
        db_session,
        label="comparison-rule-b",
        source_label="comparison-source-b",
    )
    identity_scope = {
        "subject_identity_scope_sha256": "1" * 64,
        "object_identity_scope_sha256": "2" * 64,
    }
    condition_scope = {
        "matrix_context": {"medium": "ethanol"},
        "dose_domain": {"minimum": 0.01, "maximum": 0.1},
        "temporal_domain": {"phase": "heart"},
    }
    authority = await LabService(
        db_session
    ).create_claim_authority_version(
        _command(
            legacy,
            payload={
                "left_subject": "1" * 64,
                "right_subject": "2" * 64,
                "comparison_metric": "target_similarity",
            },
            identity_scope=identity_scope,
            condition_scope=condition_scope,
            supports=(
                ClaimAuthoritySupportInput("KNOWLEDGE_RULE", first.id),
                ClaimAuthoritySupportInput("KNOWLEDGE_RULE", second.id),
            ),
        )
    )

    assert authority.decision == "ALLOW_SCOPED"
    assert authority.source_reference_count == 2


@pytest.mark.asyncio
async def test_passing_b6_snapshot_authorizes_only_scoped_regulatory_screen(
    db_session,
):
    service = LabService(db_session)
    material, stock = await _evaluation_stock(
        service,
        name="B7 regulatory linalool",
        cas_number="78-70-6",
        active_fraction=0.2,
        origin="SYNTHETIC",
        lot_number="B7-REG-1",
    )
    formula = await _formula_version_for_stocks(
        service,
        (stock,),
        finished_concentration=0.1,
    )
    bindings = await _required_supplier_bindings(
        service,
        stock,
        digest_seed=10,
    )
    current, rule, watch, watch_rule = await _regulatory_rule_graph(
        service,
        maximum_fraction=0.03,
        material_id=material.id,
    )
    snapshot = await service.evaluate_regulatory_snapshot(
        _evaluation_input(
            "FORMULA_VERSION",
            formula.id,
            primary_source_version_id=current.id,
            current_source_ids=(current.id,),
            watch_source_ids=(watch.id,),
            rule_ids=(rule.id, watch_rule.id),
            supplier_binding_ids=tuple(
                binding.id for binding in bindings
            ),
        )
    )
    assert snapshot.result_state == "PASS_FOR_DECLARED_SCOPE"
    legacy = await _legacy_claim(
        db_session,
        claim_type="REGULATORY_SCREEN",
        subject_type="FORMULA_VERSION",
        subject_id=formula.id,
        label="regulatory-screen",
    )
    identity_scope = {
        "subject_type": "FORMULA_VERSION",
        "subject_id": formula.id,
    }
    condition_scope = {
        "jurisdiction": "GLOBAL",
        "product_category": "IFRA_CATEGORY_4",
        "use_classification": "LEAVE_ON",
        "finished_product_concentration": 0.1,
        "effective_on": "2023-06-30",
    }
    authority = await service.create_claim_authority_version(
        _command(
            legacy,
            payload={
                "jurisdiction": "GLOBAL",
                "product_category": "IFRA_CATEGORY_4",
                "effective_on": "2023-06-30",
            },
            identity_scope=identity_scope,
            condition_scope=condition_scope,
            supports=(
                ClaimAuthoritySupportInput(
                    "REGULATORY_SNAPSHOT",
                    snapshot.id,
                ),
            ),
        )
    )

    assert authority.decision == "ALLOW_SCOPED"
    assert authority.release_authority is False
    assert "release-grade" in authority.forbidden_wording.casefold()


@pytest.mark.asyncio
async def test_claim_payload_value_cannot_diverge_from_canonical_support(
    db_session,
):
    subject = await _formula_subject(db_session, "payload mismatch")
    legacy = await _legacy_claim(
        db_session,
        claim_type="PROPERTY_VALUE",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label="payload-mismatch",
    )
    identity = {
        "identity_scope": "CHEMICAL_ENTITY",
        "chemical_name": "Linalool",
        "identifier": "78-70-6",
    }
    conditions = {"temperature_k": 298.15, "phase": "LIQUID"}
    assertion, _ = await _property_assertion(
        db_session,
        label="payload-mismatch-source",
        identity_scope=identity,
        identity_scope_name="CHEMICAL_ENTITY",
        property_type="DENSITY",
        value=0.85,
        unit="g/mL",
        conditions=conditions,
        evidence_class="MEASURED",
        standard_uncertainty=0.05,
    )
    authority = await LabService(
        db_session
    ).create_claim_authority_version(
        _command(
            legacy,
            payload={
                "property_type": "DENSITY",
                "value": 9.99,
                "unit": "g/mL",
            },
            identity_scope=identity,
            condition_scope=conditions,
            supports=(
                ClaimAuthoritySupportInput(
                    "PROPERTY_ASSERTION",
                    assertion.id,
                ),
            ),
        )
    )

    assert authority.decision == "WITHHOLD_UNKNOWN"
    assert "CLAIM_PAYLOAD_MISMATCH:value" in (
        authority.missing_requirements_json
    )


async def _property_revision_chain(db_session):
    subject = await _formula_subject(db_session, "revision chain")
    legacy_v1 = await _legacy_claim(
        db_session,
        claim_type="PROPERTY_VALUE",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label="revision-v1",
    )
    identity = {
        "identity_scope": "CHEMICAL_ENTITY",
        "chemical_name": "Linalool",
        "identifier": "78-70-6",
    }
    conditions = {"temperature_k": 298.15, "phase": "LIQUID"}
    payload = {
        "property_type": "DENSITY",
        "value": 0.85,
        "unit": "g/mL",
    }
    heuristic, _ = await _property_assertion(
        db_session,
        label="revision-heuristic",
        identity_scope=identity,
        identity_scope_name="CHEMICAL_ENTITY",
        property_type="DENSITY",
        value=0.85,
        unit="g/mL",
        conditions=conditions,
        evidence_class="HEURISTIC",
        standard_uncertainty=0.05,
    )
    service = LabService(db_session)
    root = await service.create_claim_authority_version(
        _command(
            legacy_v1,
            payload=payload,
            identity_scope=identity,
            condition_scope=conditions,
            supports=(
                ClaimAuthoritySupportInput(
                    "PROPERTY_ASSERTION",
                    heuristic.id,
                ),
            ),
        )
    )

    legacy_v2 = await _legacy_claim_revision(
        db_session,
        legacy_v1,
        label="revision-v2",
    )
    measured, _ = await _property_assertion(
        db_session,
        label="revision-measured",
        identity_scope=identity,
        identity_scope_name="CHEMICAL_ENTITY",
        property_type="DENSITY",
        value=0.85,
        unit="g/mL",
        conditions=conditions,
        evidence_class="MEASURED",
        standard_uncertainty=0.05,
    )
    revision = await service.create_claim_authority_version(
        _command(
            legacy_v2,
            payload=payload,
            identity_scope=identity,
            condition_scope=conditions,
            supports=(
                ClaimAuthoritySupportInput(
                    "PROPERTY_ASSERTION",
                    measured.id,
                ),
            ),
        ),
        parent_version_id=root.id,
    )
    return {
        "service": service,
        "subject": subject,
        "legacy_v1": legacy_v1,
        "legacy_v2": legacy_v2,
        "identity": identity,
        "conditions": conditions,
        "payload": payload,
        "heuristic": heuristic,
        "measured": measured,
        "root": root,
        "revision": revision,
    }


@pytest.mark.asyncio
async def test_revision_promotes_only_with_new_canonical_support_and_reconstructs(
    db_session,
):
    case = await _property_revision_chain(db_session)
    root = case["root"]
    revision = case["revision"]

    assert root.decision == "ADVISORY_ONLY"
    assert revision.decision == "ALLOW_EXACT"
    assert revision.authority_id == root.authority_id
    assert revision.version_number == 2
    assert revision.parent_version_id == root.id
    assert revision.parent_sha256 == root.content_sha256

    reconstructed_root = await case[
        "service"
    ].reconstruct_claim_authority(root.id)
    reconstructed_revision = await case[
        "service"
    ].reconstruct_claim_authority(revision.id)

    assert reconstructed_root["integrity_verified"] is True
    assert reconstructed_root["content_sha256"] == root.content_sha256
    assert reconstructed_root["decision"] == "ADVISORY_ONLY"
    assert reconstructed_root["support_links"][0]["record_id"] == (
        case["heuristic"].id
    )
    assert reconstructed_revision["integrity_verified"] is True
    assert reconstructed_revision["content_sha256"] == (
        revision.content_sha256
    )
    assert reconstructed_revision["decision"] == "ALLOW_EXACT"
    assert reconstructed_revision["parent_sha256"] == root.content_sha256
    assert reconstructed_revision["support_links"][0]["record_id"] == (
        case["measured"].id
    )


@pytest.mark.asyncio
async def test_revision_rejects_scope_changes_stale_parent_and_stale_a2(
    db_session,
):
    case = await _property_revision_chain(db_session)
    service = case["service"]
    support = (
        ClaimAuthoritySupportInput(
            "PROPERTY_ASSERTION",
            case["measured"].id,
        ),
    )

    changed_commands = (
        _command(
            case["legacy_v2"],
            payload={**case["payload"], "value": 0.86},
            identity_scope=case["identity"],
            condition_scope=case["conditions"],
            supports=support,
        ),
        _command(
            case["legacy_v2"],
            payload=case["payload"],
            identity_scope={**case["identity"], "identifier": "DIFFERENT"},
            condition_scope=case["conditions"],
            supports=support,
        ),
        _command(
            case["legacy_v2"],
            payload=case["payload"],
            identity_scope=case["identity"],
            condition_scope={
                **case["conditions"],
                "temperature_k": 303.15,
            },
            supports=support,
        ),
    )
    for command in changed_commands:
        with pytest.raises(ClaimAuthorityConflictError) as exc_info:
            await service.create_claim_authority_version(
                command,
                parent_version_id=case["revision"].id,
            )
        assert exc_info.value.code == "CLAIM_AUTHORITY_SCOPE_CHANGED"

    with pytest.raises(ClaimAuthorityConflictError) as stale_parent:
        await service.create_claim_authority_version(
            _command(
                case["legacy_v2"],
                payload=case["payload"],
                identity_scope=case["identity"],
                condition_scope=case["conditions"],
                supports=support,
            ),
            parent_version_id=case["root"].id,
        )
    assert stale_parent.value.code == "CLAIM_AUTHORITY_PARENT_NOT_LATEST"

    with pytest.raises(ClaimAuthorityConflictError) as stale_a2:
        await service.create_claim_authority_version(
            _command(
                case["legacy_v1"],
                payload=case["payload"],
                identity_scope=case["identity"],
                condition_scope=case["conditions"],
                supports=support,
            ),
            parent_version_id=case["revision"].id,
        )
    assert stale_a2.value.code == "CLAIM_AUTHORITY_A2_VERSION_NOT_LATEST"

    changed_subject = await _formula_subject(db_session, "changed subject")
    legacy_v3 = await _legacy_claim_revision(
        db_session,
        case["legacy_v2"],
        label="revision-v3-changed-subject",
        subject_type="FORMULA_VERSION",
        subject_id=changed_subject.id,
    )
    with pytest.raises(ClaimAuthorityConflictError) as subject_change:
        await service.create_claim_authority_version(
            _command(
                legacy_v3,
                payload=case["payload"],
                identity_scope=case["identity"],
                condition_scope=case["conditions"],
                supports=support,
            ),
            parent_version_id=case["revision"].id,
        )
    assert subject_change.value.code == "CLAIM_AUTHORITY_SCOPE_CHANGED"


@pytest.mark.asyncio
async def test_exact_identity_with_one_source_is_withheld(db_session):
    subject = await _formula_subject(db_session, "one-source identity")
    legacy = await _legacy_claim(
        db_session,
        claim_type="IDENTITY",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label="one-source-identity",
    )
    identity = {
        "identity_scope": "CHEMICAL_ENTITY",
        "chemical_name": "Linalool",
        "identifier": "78-70-6",
    }
    assertion, _ = await _property_assertion(
        db_session,
        label="one-identity-source",
        identity_scope=identity,
        identity_scope_name="CHEMICAL_ENTITY",
        property_type="CHEMICAL_IDENTITY",
        value="Linalool",
        unit="dimensionless",
        conditions={},
        evidence_class="LITERATURE_DERIVED",
        standard_uncertainty=None,
    )

    authority = await LabService(
        db_session
    ).create_claim_authority_version(
        _command(
            legacy,
            payload={
                "chemical_name": "Linalool",
                "identifier": "78-70-6",
            },
            identity_scope=identity,
            condition_scope={},
            supports=(
                ClaimAuthoritySupportInput(
                    "PROPERTY_ASSERTION",
                    assertion.id,
                ),
            ),
        )
    )

    assert authority.decision == "WITHHOLD_UNKNOWN"
    assert "SOURCE_INDEPENDENCE_NOT_MET" in (
        authority.missing_requirements_json
    )


@pytest.mark.asyncio
async def test_grade_identity_with_a_different_lot_is_withheld(db_session):
    subject = await _formula_subject(db_session, "grade lot mismatch")
    legacy = await _legacy_claim(
        db_session,
        claim_type="GRADE_IDENTITY",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label="grade-lot-mismatch",
    )
    canonical_identity = {
        "identity_scope": "SUPPLIER_LOT",
        "grade_name": "Natural FCF",
        "supplier_or_standard": "Supplier A",
        "lot_number": "LOT-42",
    }
    assertion, _ = await _property_assertion(
        db_session,
        label="grade-lot-source",
        identity_scope=canonical_identity,
        identity_scope_name="SUPPLIER_LOT",
        property_type="GRADE_IDENTITY",
        value="Natural FCF",
        unit="dimensionless",
        conditions={},
        evidence_class="SUPPLIER_PROVIDED",
        standard_uncertainty=None,
    )

    authority = await LabService(
        db_session
    ).create_claim_authority_version(
        _command(
            legacy,
            payload={
                "grade_name": "Natural FCF",
                "supplier_or_standard": "Supplier A",
            },
            identity_scope={
                **canonical_identity,
                "lot_number": "LOT-DIFFERENT",
            },
            condition_scope={},
            supports=(
                ClaimAuthoritySupportInput(
                    "PROPERTY_ASSERTION",
                    assertion.id,
                ),
            ),
        )
    )

    assert authority.decision == "WITHHOLD_UNKNOWN"
    assert "IDENTITY_SCOPE_MISMATCH" in authority.missing_requirements_json


@pytest.mark.asyncio
async def test_model_backed_rule_outside_its_domain_is_withheld(db_session):
    subject = await _formula_subject(db_session, "model domain mismatch")
    legacy = await _legacy_claim(
        db_session,
        claim_type="KNOWLEDGE_RULE_RECOMMENDATION",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label="model-domain-mismatch",
    )
    rule = await _knowledge_rule(
        db_session,
        label="model-domain-rule",
        source_label="model-domain-source",
        model_ref="bounded-model-v1",
        model_applicable=False,
    )
    identity_scope = {
        "subject_identity_scope_sha256": "1" * 64,
        "object_identity_scope_sha256": "2" * 64,
    }
    condition_scope = {
        "matrix_context": {"medium": "ethanol"},
        "dose_domain": {"minimum": 0.01, "maximum": 0.1},
        "temporal_domain": {"phase": "heart"},
    }

    authority = await LabService(
        db_session
    ).create_claim_authority_version(
        _command(
            legacy,
            payload={
                "rule_key": "model-domain-rule",
                "recommendation": "REINFORCES",
            },
            identity_scope=identity_scope,
            condition_scope=condition_scope,
            supports=(
                ClaimAuthoritySupportInput(
                    "KNOWLEDGE_RULE",
                    rule.id,
                ),
            ),
        )
    )

    assert authority.decision == "WITHHOLD_UNKNOWN"
    assert "MODEL_APPLICABILITY_REQUIRED" in (
        authority.missing_requirements_json
    )


@pytest.mark.asyncio
async def test_unknown_and_partial_natural_profiles_are_withheld(db_session):
    service = LabService(db_session)
    stock = await _natural_stock(service)
    binding = await _composition_document_binding(service, stock.id)
    partial = await service.record_regulatory_composition_profile(
        _composition_profile_input(
            stock.id,
            binding.id,
            completeness="PARTIAL",
        )
    )
    unknown = await service.record_regulatory_composition_profile(
        _composition_profile_input(
            stock.id,
            None,
            composition_basis="UNKNOWN",
            completeness="UNKNOWN",
            entries=(),
            limitations=("composition not supplied",),
        )
    )
    subject = await _formula_version_for_stocks(
        service,
        (stock,),
        finished_concentration=0.1,
    )

    cases = (
        (
            "partial",
            partial,
            {
                "stock_solution_id": stock.id,
                "supplier_identity_sha256": (
                    binding.supplier_identity_sha256
                ),
            },
            {
                "stock_solution_id": stock.id,
                "scope": "SUPPLIER_LOT",
                "lot_number": "LOT-42",
            },
            "COMPOSITION_INCOMPLETE",
        ),
        (
            "unknown",
            unknown,
            {
                "stock_solution_id": stock.id,
                "supplier_identity_sha256": None,
            },
            {
                "stock_solution_id": stock.id,
                "scope": None,
                "lot_number": None,
            },
            "NATURAL_COMPOSITION_UNKNOWN",
        ),
    )
    for label, profile, identity_scope, condition_scope, missing_code in cases:
        legacy = await _legacy_claim(
            db_session,
            claim_type="NATURAL_CONSTITUENT_PROFILE",
            subject_type="FORMULA_VERSION",
            subject_id=subject.id,
            label=f"natural-profile-{label}",
        )
        authority = await service.create_claim_authority_version(
            _command(
                legacy,
                payload={
                    "stock_solution_id": stock.id,
                    "composition_basis": profile.composition_basis,
                },
                identity_scope=identity_scope,
                condition_scope=condition_scope,
                supports=(
                    ClaimAuthoritySupportInput(
                        "COMPOSITION_PROFILE",
                        profile.id,
                    ),
                ),
            )
        )

        assert authority.decision == "WITHHOLD_UNKNOWN"
        assert missing_code in authority.missing_requirements_json


async def _regulatory_snapshot_fixture(
    service,
    *,
    label: str,
    expected_state: str,
    digest_seed: int,
):
    if expected_state == "UNKNOWN":
        _, stock = await _evaluation_stock(
            service,
            name=f"B7 unknown regulatory {label}",
            cas_number="8000-00-9",
            active_fraction=1.0,
            origin="NATURAL",
            lot_number=f"B7-UNKNOWN-{digest_seed}",
        )
        formula = await _formula_version_for_stocks(
            service,
            (stock,),
            finished_concentration=0.1,
        )
        bindings = await _required_supplier_bindings(
            service,
            stock,
            digest_seed=digest_seed,
        )
        profile = await service.record_regulatory_composition_profile(
            _composition_profile_input(
                stock.id,
                None,
                composition_basis="UNKNOWN",
                completeness="UNKNOWN",
                entries=(),
                limitations=("composition not supplied",),
            )
        )
        current, rule, watch, watch_rule = await _regulatory_rule_graph(
            service,
            maximum_fraction=0.03,
            material_id=None,
        )
        composition_profile_ids = (profile.id,)
    else:
        material, stock = await _evaluation_stock(
            service,
            name=f"B7 regulatory {label}",
            cas_number="78-70-6",
            active_fraction=0.2,
            origin="SYNTHETIC",
            lot_number=f"B7-{expected_state}-{digest_seed}",
        )
        formula = await _formula_version_for_stocks(
            service,
            (stock,),
            finished_concentration=0.1,
        )
        bindings = await _required_supplier_bindings(
            service,
            stock,
            digest_seed=digest_seed,
        )
        current, rule, watch, watch_rule = await _regulatory_rule_graph(
            service,
            maximum_fraction=(
                0.01 if expected_state == "FAIL" else 0.03
            ),
            material_id=material.id,
        )
        composition_profile_ids = ()

    snapshot = await service.evaluate_regulatory_snapshot(
        _evaluation_input(
            "FORMULA_VERSION",
            formula.id,
            primary_source_version_id=current.id,
            current_source_ids=(current.id,),
            watch_source_ids=(watch.id,),
            rule_ids=(rule.id, watch_rule.id),
            supplier_binding_ids=tuple(
                binding.id for binding in bindings
            ),
            composition_profile_ids=composition_profile_ids,
        )
    )
    assert snapshot.result_state == expected_state
    return formula, snapshot


async def _claim_from_regulatory_snapshot(
    db_session,
    service,
    *,
    legacy_subject,
    snapshot,
    label: str,
    payload_overrides: dict | None = None,
    identity_overrides: dict | None = None,
    condition_overrides: dict | None = None,
):
    legacy = await _legacy_claim(
        db_session,
        claim_type="REGULATORY_SCREEN",
        subject_type="FORMULA_VERSION",
        subject_id=legacy_subject.id,
        label=label,
    )
    payload = {
        "jurisdiction": snapshot.jurisdiction,
        "product_category": snapshot.product_category,
        "effective_on": snapshot.effective_on.isoformat(),
    }
    identity_scope = {
        "subject_type": snapshot.subject_type,
        "subject_id": snapshot.subject_id,
    }
    condition_scope = {
        "jurisdiction": snapshot.jurisdiction,
        "product_category": snapshot.product_category,
        "use_classification": snapshot.use_classification,
        "finished_product_concentration": (
            snapshot.finished_product_concentration
        ),
        "effective_on": snapshot.effective_on.isoformat(),
    }
    return await service.create_claim_authority_version(
        _command(
            legacy,
            payload={**payload, **(payload_overrides or {})},
            identity_scope={
                **identity_scope,
                **(identity_overrides or {}),
            },
            condition_scope={
                **condition_scope,
                **(condition_overrides or {}),
            },
            supports=(
                ClaimAuthoritySupportInput(
                    "REGULATORY_SNAPSHOT",
                    snapshot.id,
                ),
            ),
        )
    )


@pytest.mark.asyncio
async def test_failed_and_unknown_regulatory_snapshots_fail_closed(db_session):
    service = LabService(db_session)
    failed_subject, failed_snapshot = await _regulatory_snapshot_fixture(
        service,
        label="failure",
        expected_state="FAIL",
        digest_seed=71,
    )
    failed = await _claim_from_regulatory_snapshot(
        db_session,
        service,
        legacy_subject=failed_subject,
        snapshot=failed_snapshot,
        label="regulatory-failure",
    )

    unknown_subject, unknown_snapshot = await _regulatory_snapshot_fixture(
        service,
        label="unknown",
        expected_state="UNKNOWN",
        digest_seed=72,
    )
    unknown = await _claim_from_regulatory_snapshot(
        db_session,
        service,
        legacy_subject=unknown_subject,
        snapshot=unknown_snapshot,
        label="regulatory-unknown",
    )

    assert failed.decision == "BLOCK"
    assert "REGULATORY_SCREEN_FAILED" in failed.conflicts_json
    assert unknown.decision == "WITHHOLD_UNKNOWN"
    assert "REGULATORY_STATE_UNKNOWN" in (
        unknown.missing_requirements_json
    )


@pytest.mark.asyncio
async def test_regulatory_subject_jurisdiction_and_date_mismatch_are_withheld(
    db_session,
):
    service = LabService(db_session)
    subject, snapshot = await _regulatory_snapshot_fixture(
        service,
        label="scope",
        expected_state="PASS_FOR_DECLARED_SCOPE",
        digest_seed=73,
    )
    different_subject = await _formula_subject(
        db_session,
        "regulatory different subject",
    )

    subject_mismatch = await _claim_from_regulatory_snapshot(
        db_session,
        service,
        legacy_subject=different_subject,
        snapshot=snapshot,
        label="regulatory-subject-mismatch",
    )
    jurisdiction_mismatch = await _claim_from_regulatory_snapshot(
        db_session,
        service,
        legacy_subject=subject,
        snapshot=snapshot,
        label="regulatory-jurisdiction-mismatch",
        payload_overrides={"jurisdiction": "EU"},
        condition_overrides={"jurisdiction": "EU"},
    )
    date_mismatch = await _claim_from_regulatory_snapshot(
        db_session,
        service,
        legacy_subject=subject,
        snapshot=snapshot,
        label="regulatory-date-mismatch",
        payload_overrides={"effective_on": "2024-01-01"},
        condition_overrides={"effective_on": "2024-01-01"},
    )

    assert subject_mismatch.decision == "WITHHOLD_UNKNOWN"
    assert "SUBJECT_SCOPE_MISMATCH" in (
        subject_mismatch.missing_requirements_json
    )
    assert jurisdiction_mismatch.decision == "WITHHOLD_UNKNOWN"
    assert "CONDITION_SCOPE_MISMATCH" in (
        jurisdiction_mismatch.missing_requirements_json
    )
    assert date_mismatch.decision == "WITHHOLD_UNKNOWN"
    assert "CONDITION_SCOPE_MISMATCH" in (
        date_mismatch.missing_requirements_json
    )


@pytest.mark.asyncio
async def test_failed_analytical_validation_blocks_a_prior_supported_claim(
    db_session,
):
    service = LabService(db_session)
    graph = await _complete_peak_authority_graph(service)
    await _record_required_qc(
        service,
        graph["run"].id,
        graph["method"].evidence_record_id,
    )
    assessment = await service.assess_analytical_claim(
        _claim_request(graph, claim_type="IDENTITY")
    )
    assert assessment.decision == "SUPPORTED_FOR_SCOPE"
    await service.record_method_validation(
        _validation_input(
            graph["method_authority"].id,
            graph["source"].id,
            intended_claim="linalool identity",
            result="FAIL",
            reviewed_at=datetime(
                2026,
                7,
                31,
                4,
                0,
                tzinfo=timezone.utc,
            ),
        )
    )
    legacy = await _legacy_claim(
        db_session,
        claim_type="ANALYTICAL_IDENTITY",
        subject_type="ANALYTICAL_RUN",
        subject_id=graph["run"].id,
        label="analytical-validation-failed",
    )

    authority = await service.create_claim_authority_version(
        _command(
            legacy,
            payload={
                "analyte": "linalool",
                "identity_label": "linalool",
            },
            identity_scope={
                "analytical_run_id": graph["run"].id,
                "identity_label": "linalool",
            },
            condition_scope={},
            supports=(
                ClaimAuthoritySupportInput(
                    "ANALYTICAL_ASSESSMENT",
                    assessment.id,
                ),
            ),
        )
    )

    assert authority.decision == "BLOCK"
    assert "METHOD_VALIDATION_FAILED" in authority.conflicts_json


@pytest.mark.asyncio
async def test_blocking_analytical_qc_failure_is_withheld(db_session):
    service = LabService(db_session)
    graph = await _complete_peak_authority_graph(service)
    await _record_required_qc(
        service,
        graph["run"].id,
        graph["method"].evidence_record_id,
        status_by_type={"BLANK": "FAIL"},
    )
    assessment = await service.assess_analytical_claim(
        _claim_request(graph, claim_type="QUANTITY")
    )
    assert assessment.decision == "WITHHELD"
    legacy = await _legacy_claim(
        db_session,
        claim_type="ANALYTICAL_QUANTITY",
        subject_type="ANALYTICAL_RUN",
        subject_id=graph["run"].id,
        label="analytical-qc-failed",
    )

    authority = await service.create_claim_authority_version(
        _command(
            legacy,
            payload={
                "analyte": "linalool",
                "value": 0.2,
                "unit": "mg/mL",
            },
            identity_scope={
                "analytical_run_id": graph["run"].id,
                "identity_label": "linalool",
            },
            condition_scope={},
            supports=(
                ClaimAuthoritySupportInput(
                    "ANALYTICAL_ASSESSMENT",
                    assessment.id,
                ),
            ),
        )
    )

    assert authority.decision == "WITHHOLD_UNKNOWN"
    assert "QC_FAILED_BLOCKING" in authority.missing_requirements_json


async def _property_evidence_authority(
    db_session,
    *,
    label: str,
    evidence_class: str,
    role: str = "SUPPORTING",
    payload: dict | None = None,
):
    subject = await _formula_subject(db_session, label)
    legacy = await _legacy_claim(
        db_session,
        claim_type="PROPERTY_VALUE",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label=label,
    )
    identity = {
        "identity_scope": "CHEMICAL_ENTITY",
        "chemical_name": "Linalool",
        "identifier": "78-70-6",
    }
    conditions = {"temperature_k": 298.15, "phase": "LIQUID"}
    assertion, _ = await _property_assertion(
        db_session,
        label=f"{label}-source",
        identity_scope=identity,
        identity_scope_name="CHEMICAL_ENTITY",
        property_type="DENSITY",
        value=0.85,
        unit="g/mL",
        conditions=conditions,
        evidence_class=evidence_class,
        standard_uncertainty=0.05,
    )
    return await LabService(db_session).create_claim_authority_version(
        _command(
            legacy,
            payload=payload
            or {
                "property_type": "DENSITY",
                "value": 0.85,
                "unit": "g/mL",
            },
            identity_scope=identity,
            condition_scope=conditions,
            supports=(
                ClaimAuthoritySupportInput(
                    "PROPERTY_ASSERTION",
                    assertion.id,
                    role=role,
                ),
            ),
        )
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("evidence_class", ("SPECULATIVE", "UNKNOWN"))
async def test_nonpromoting_property_evidence_never_authorizes_exactness(
    db_session,
    evidence_class,
):
    authority = await _property_evidence_authority(
        db_session,
        label=f"nonpromoting-{evidence_class.casefold()}",
        evidence_class=evidence_class,
    )

    assert authority.decision == "ADVISORY_ONLY"
    assert "EVIDENCE_CLASS_NOT_PROMOTING" in (
        authority.missing_requirements_json
    )
    assert authority.release_authority is False


@pytest.mark.asyncio
async def test_limitation_support_without_promoting_support_is_withheld(
    db_session,
):
    authority = await _property_evidence_authority(
        db_session,
        label="limitation-only",
        evidence_class="MEASURED",
        role="LIMITATION",
    )

    assert authority.decision == "WITHHOLD_UNKNOWN"
    assert "LIMITATION_SUPPORT" in authority.missing_requirements_json
    assert "SUPPORTING_OBSERVATION_MISSING" in (
        authority.missing_requirements_json
    )


@pytest.mark.asyncio
async def test_missing_required_property_field_is_withheld_end_to_end(
    db_session,
):
    authority = await _property_evidence_authority(
        db_session,
        label="missing-unit-integration",
        evidence_class="MEASURED",
        payload={"property_type": "DENSITY", "value": 0.85},
    )

    assert authority.decision == "WITHHOLD_UNKNOWN"
    assert "REQUIRED_FIELD_MISSING:unit" in (
        authority.missing_requirements_json
    )
