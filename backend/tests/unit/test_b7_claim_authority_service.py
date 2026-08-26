import json
from datetime import datetime, timezone
from hashlib import sha256

import pytest

from app.models.lab import LabFormula, LabFormulaVersion
from app.models.lab_claims import CLAIM_AUTHORITY_TYPES
from app.models.lab_properties import (
    LabPropertyObservation,
    LabSelectedAssertion,
)
from app.models.lab_science import LabClaimAssessmentVersion
from app.models.lab_sources import (
    LabSourceDocumentVersion,
    LabSourceExtractionRecord,
)
from app.services.lab_claims import (
    CLAIM_AUTHORITY_POLICIES,
    ClaimAuthorityConflictError,
    ClaimAuthorityEvaluationInput,
    ClaimAuthoritySupportInput,
    claim_policy_hash,
    normalize_claim_authority_type,
    policy_snapshot,
    wording_for_decision,
)
from app.services.lab_service import LabService

NOW = datetime(2026, 7, 31, 0, 0, tzinfo=timezone.utc)

POLICY_FIELDS = {
    "claim_type",
    "required_fields",
    "accepted_evidence_classes",
    "accepted_support_kinds",
    "identity_scope",
    "condition_match",
    "minimum_coverage",
    "minimum_independent_sources",
    "contradiction_handling",
    "uncertainty_limit",
    "method_validation_requirement",
    "model_applicability_requirement",
    "safety_requirement",
    "maximum_decision",
    "permitted_wording",
    "forbidden_wording",
}


def test_policy_registry_has_exactly_eleven_complete_claim_policies():
    assert tuple(CLAIM_AUTHORITY_POLICIES) == CLAIM_AUTHORITY_TYPES
    assert len(CLAIM_AUTHORITY_POLICIES) == 11
    for claim_type, policy in CLAIM_AUTHORITY_POLICIES.items():
        snapshot = policy_snapshot(policy)
        assert set(snapshot) == POLICY_FIELDS
        assert snapshot["claim_type"] == claim_type
        assert snapshot["required_fields"]
        assert snapshot["accepted_evidence_classes"]
        assert snapshot["accepted_support_kinds"]
        assert snapshot["identity_scope"]
        assert snapshot["condition_match"]
        assert 0 < snapshot["minimum_coverage"] <= 1
        assert snapshot["minimum_independent_sources"] >= 1
        assert snapshot["contradiction_handling"]
        assert snapshot["uncertainty_limit"]
        assert snapshot["method_validation_requirement"]
        assert snapshot["model_applicability_requirement"]
        assert snapshot["safety_requirement"]
        assert snapshot["maximum_decision"] in {
            "ALLOW_EXACT",
            "ALLOW_SCOPED",
        }
        assert set(snapshot["permitted_wording"]) == {
            "ALLOW_EXACT",
            "ALLOW_SCOPED",
            "ADVISORY_ONLY",
            "WITHHOLD_UNKNOWN",
            "BLOCK",
        }
        assert snapshot["forbidden_wording"]


def test_policy_snapshots_and_hashes_are_canonical_and_deterministic():
    for policy in CLAIM_AUTHORITY_POLICIES.values():
        first = policy_snapshot(policy)
        second = json.loads(
            json.dumps(first, sort_keys=True, separators=(",", ":"))
        )
        assert first == second
        assert claim_policy_hash(policy) == claim_policy_hash(policy)
        assert len(claim_policy_hash(policy)) == 64


def test_policy_permissions_never_convey_release_or_certification():
    forbidden_tokens = ("release-grade", "certified", "universally safe")
    for policy in CLAIM_AUTHORITY_POLICIES.values():
        snapshot = policy_snapshot(policy)
        permitted = " ".join(snapshot["permitted_wording"].values()).casefold()
        assert not any(token in permitted for token in forbidden_tokens)
        forbidden = " ".join(snapshot["forbidden_wording"]).casefold()
        assert all(token in forbidden for token in forbidden_tokens)


def test_exact_capable_and_scoped_only_claims_match_frozen_design():
    exact = {
        claim_type
        for claim_type, policy in CLAIM_AUTHORITY_POLICIES.items()
        if policy.maximum_decision == "ALLOW_EXACT"
    }
    assert exact == {
        "EXACT_CHEMICAL_IDENTITY",
        "GRADE_IDENTITY",
        "PROPERTY_VALUE",
        "THRESHOLD",
        "ANALYTICAL_IDENTIFICATION",
        "ANALYTICAL_QUANTITATION",
        "NATURAL_CONSTITUENT_PROFILE",
    }
    assert set(CLAIM_AUTHORITY_POLICIES) - exact == {
        "ABOVE_THRESHOLD_SCREENING",
        "KNOWLEDGE_RULE_RECOMMENDATION",
        "REGULATORY_SCREENING",
        "FORMULA_OR_MODEL_COMPARISON",
    }


@pytest.mark.parametrize(
    ("legacy", "expected"),
    (
        ("IDENTITY", "EXACT_CHEMICAL_IDENTITY"),
        ("ANALYTICAL_IDENTITY", "ANALYTICAL_IDENTIFICATION"),
        ("ANALYTICAL_QUANTITY", "ANALYTICAL_QUANTITATION"),
        ("ABOVE_THRESHOLD_LIKELIHOOD", "ABOVE_THRESHOLD_SCREENING"),
        ("REGULATORY_SCREEN", "REGULATORY_SCREENING"),
        ("TARGET_SIMILARITY", "FORMULA_OR_MODEL_COMPARISON"),
        ("FAMILY_PRESERVATION", "FORMULA_OR_MODEL_COMPARISON"),
    ),
)
def test_closed_legacy_alias_map_is_explicit(legacy, expected):
    assert normalize_claim_authority_type(legacy) == expected
    assert normalize_claim_authority_type(expected) == expected


def test_unknown_claim_type_is_not_guessed():
    with pytest.raises(ClaimAuthorityConflictError) as error:
        normalize_claim_authority_type("looks_about_right")
    assert error.value.code == "CLAIM_AUTHORITY_TYPE_UNKNOWN"


@pytest.mark.parametrize(
    "decision",
    (
        "ALLOW_EXACT",
        "ALLOW_SCOPED",
        "ADVISORY_ONLY",
        "WITHHOLD_UNKNOWN",
        "BLOCK",
    ),
)
def test_every_decision_has_permitted_and_forbidden_language(decision):
    permitted, forbidden = wording_for_decision(
        CLAIM_AUTHORITY_POLICIES["PROPERTY_VALUE"],
        decision,
    )
    assert permitted.strip()
    assert forbidden.strip()
    assert "release-grade" in forbidden.casefold()


def _digest(label: str) -> str:
    return sha256(label.encode("utf-8")).hexdigest()


async def _property_case(
    db_session,
    *,
    evidence_class: str = "MEASURED",
    legacy_conflicts: tuple[str, ...] = (),
):
    formula = LabFormula(name=f"B7 property fixture {_digest(evidence_class)[:8]}")
    db_session.add(formula)
    await db_session.flush()
    formula_version = LabFormulaVersion(
        formula_id=formula.id,
        version_number=1,
        brief_json={},
        constraints_json={},
        concentration_fraction=0.2,
        concentration_basis="MASS_FRACTION",
        source_json={},
    )
    db_session.add(formula_version)
    await db_session.flush()

    legacy = LabClaimAssessmentVersion(
        claim_id=_digest(f"legacy-chain:{evidence_class}")[:36],
        version_number=1,
        schema_version="a4-claim-v1",
        claim_type="PROPERTY_VALUE",
        subject_type="FORMULA_VERSION",
        subject_id=formula_version.id,
        parent_version_id=None,
        policy_version="a4-policy-v1",
        decision="ALLOW_EXACT",
        authority_json={
            "source_coverage_complete": True,
            "identity_resolved": True,
            "uncertainty_bounded": True,
            "exact_evidence": True,
        },
        missing_evidence_json=[],
        conflicts_json=list(legacy_conflicts),
        permitted_wording="Legacy caller asserted exactness.",
        forbidden_wording=None,
        human_review_state="APPROVED",
        reviewer_pseudonym="legacy-reviewer",
        reviewed_at=NOW,
        content_sha256=_digest(f"legacy:{evidence_class}:{legacy_conflicts}"),
        parent_sha256=None,
    )
    db_session.add(legacy)

    source = LabSourceDocumentVersion(
        source_id=_digest(f"source-chain:{evidence_class}")[:36],
        version_number=1,
        schema_version="lab-source-document-v1",
        source_type="PRIMARY_PEER_REVIEWED_PAPER",
        title=f"B7 property source {evidence_class}",
        authors_json=["Test Author"],
        identifiers_json={"fixture": evidence_class},
        default_locator_json={"page": 1},
        artifact_sha256=_digest(f"artifact:{evidence_class}"),
        language="en",
        review_state="REVIEWED",
        independence_group=f"b7-property-{evidence_class.casefold()}",
        record_sha256=_digest(f"source-record:{evidence_class}"),
    )
    db_session.add(source)
    await db_session.flush()
    extraction = LabSourceExtractionRecord(
        source_version_id=source.id,
        locator_json={"page": 1, "table": "density"},
        structure_context_json={"table": "physical properties"},
        original_wording="density at 298.15 K",
        original_value_json={"value": 0.85, "unit": "g/mL"},
        parsed_value_json={"value": 0.85, "unit": "g/mL"},
        normalization_json={"canonical_unit": "g/mL"},
        parser_or_model_version="b7-test-parser-v1",
        reviewer_pseudonym="b7-reviewer",
        uncertainty_json={"standard_uncertainty": 0.05},
        ambiguity_json=[],
        output_observation_id=None,
        input_sha256=_digest(f"input:{evidence_class}"),
        output_sha256=_digest(f"output:{evidence_class}"),
        record_sha256=_digest(f"extraction:{evidence_class}"),
    )
    db_session.add(extraction)
    await db_session.flush()

    identity_scope = {
        "identity_scope": "CHEMICAL_ENTITY",
        "material_key": "linalool",
        "cas_number": "78-70-6",
    }
    conditions = {"temperature_k": 298.15, "phase": "LIQUID"}
    identity_sha256 = _digest(
        json.dumps(identity_scope, sort_keys=True, separators=(",", ":"))
    )
    observation = LabPropertyObservation(
        schema_version="lab-property-observation-v1",
        identity_scope="CHEMICAL_ENTITY",
        subject_identity_json=identity_scope,
        subject_identity_sha256=identity_sha256,
        property_type="DENSITY",
        value_kind="NUMERIC",
        numeric_value=0.85,
        categorical_value=None,
        interval_lower=None,
        interval_upper=None,
        distribution_json=None,
        censoring_qualifier=None,
        censoring_limit=None,
        original_unit="g/mL",
        canonical_unit="g/mL",
        temperature_k=298.15,
        pressure_pa=None,
        relative_humidity_percent=None,
        matrix=None,
        phase="LIQUID",
        purity_fraction=0.99,
        method="oscillating U-tube",
        source_version_id=source.id,
        extraction_record_id=extraction.id,
        source_locator_json={"page": 1, "table": "density"},
        replicate_count=3,
        statistic="MEAN",
        standard_uncertainty=0.05,
        uncertainty_interval_json={},
        evidence_class=evidence_class,
        review_state="ACCEPTED_FOR_SCOPED_USE",
        quality_flags_json=[],
        applicability_domain_json=conditions,
        provenance_activity_json={},
        supersedes_observation_id=None,
        content_sha256=_digest(f"observation:{evidence_class}"),
    )
    db_session.add(observation)
    await db_session.flush()
    assertion = LabSelectedAssertion(
        schema_version="lab-selected-assertion-v1",
        requested_identity_json=identity_scope,
        requested_identity_sha256=identity_sha256,
        requested_property_type="DENSITY",
        requested_conditions_json=conditions,
        conflict_set_id=None,
        selection_policy_version="b2-selection-v1",
        selection_kind="OBSERVATION",
        selected_observation_id=observation.id,
        selected_model_json=None,
        interpolation_state="EXACT",
        propagated_uncertainty_json={
            "standard_uncertainty": 0.05,
            "relative_standard_uncertainty": 0.05 / 0.85,
        },
        applicability_json=conditions,
        authority_state="AUTHORIZED_FOR_SCOPED_PROPERTY",
        permitted_claim_wording="Density under declared conditions.",
        content_sha256=_digest(f"assertion:{evidence_class}"),
    )
    db_session.add(assertion)
    await db_session.flush()
    return (
        LabService(db_session),
        legacy,
        assertion,
        identity_scope,
        conditions,
    )


def _property_command(
    legacy,
    assertion,
    identity_scope,
    conditions,
    *,
    role: str = "SUPPORTING",
    claim_payload: dict | None = None,
) -> ClaimAuthorityEvaluationInput:
    return ClaimAuthorityEvaluationInput(
        legacy_claim_assessment_version_id=legacy.id,
        claim_payload=claim_payload
        or {
            "property_type": "DENSITY",
            "value": 0.85,
            "unit": "g/mL",
        },
        identity_scope=identity_scope,
        condition_scope=conditions,
        supports=(
            ClaimAuthoritySupportInput(
                support_kind="PROPERTY_ASSERTION",
                record_id=assertion.id,
                role=role,
            ),
        ),
        reviewer_pseudonym="b7-reviewer",
        reviewed_at=NOW,
    )


@pytest.mark.asyncio
async def test_property_claim_is_computed_from_canonical_b2_support(db_session):
    service, legacy, assertion, identity, conditions = await _property_case(
        db_session
    )
    authority = await service.create_claim_authority_version(
        _property_command(legacy, assertion, identity, conditions)
    )

    assert authority.claim_type == "PROPERTY_VALUE"
    assert authority.decision == "ALLOW_EXACT"
    assert authority.release_authority is False
    assert authority.blocker_count == 0
    assert authority.missing_requirement_count == 0
    assert set(authority.dimension_results_json.values()) <= {
        "PASS",
        "NOT_APPLICABLE",
    }
    links = await service.repository.claim_authority_support_links(
        authority.id
    )
    assert len(links) == 1
    assert links[0].property_assertion_id == assertion.id
    assert links[0].derived_facts_json["evidence_classes"] == ["MEASURED"]
    assert "source_coverage_complete" not in links[0].derived_facts_json


@pytest.mark.asyncio
async def test_caller_a2_booleans_cannot_promote_heuristic_support(db_session):
    service, legacy, assertion, identity, conditions = await _property_case(
        db_session,
        evidence_class="HEURISTIC",
    )
    authority = await service.create_claim_authority_version(
        _property_command(legacy, assertion, identity, conditions)
    )

    assert legacy.decision == "ALLOW_EXACT"
    assert authority.decision == "ADVISORY_ONLY"
    assert "EVIDENCE_CLASS_NOT_PROMOTING" in (
        authority.missing_requirements_json
    )


@pytest.mark.asyncio
async def test_context_mismatch_is_withheld_even_with_exact_a2_booleans(
    db_session,
):
    service, legacy, assertion, identity, conditions = await _property_case(
        db_session
    )
    mismatched = {**conditions, "temperature_k": 303.15}
    authority = await service.create_claim_authority_version(
        _property_command(legacy, assertion, identity, mismatched)
    )

    assert authority.decision == "WITHHOLD_UNKNOWN"
    assert "CONDITION_SCOPE_MISMATCH" in authority.missing_requirements_json
    assert authority.critical_unknown_count >= 1


@pytest.mark.asyncio
async def test_contradicting_canonical_support_blocks_the_claim(db_session):
    service, legacy, assertion, identity, conditions = await _property_case(
        db_session
    )
    authority = await service.create_claim_authority_version(
        _property_command(
            legacy,
            assertion,
            identity,
            conditions,
            role="CONTRADICTING",
        )
    )

    assert authority.decision == "BLOCK"
    assert authority.blocker_count >= 1
    assert "CONTRADICTING_SUPPORT" in authority.conflicts_json


@pytest.mark.asyncio
async def test_missing_required_claim_field_is_withheld(db_session):
    service, legacy, assertion, identity, conditions = await _property_case(
        db_session
    )
    authority = await service.create_claim_authority_version(
        _property_command(
            legacy,
            assertion,
            identity,
            conditions,
            claim_payload={"property_type": "DENSITY", "value": 0.85},
        )
    )

    assert authority.decision == "WITHHOLD_UNKNOWN"
    assert "REQUIRED_FIELD_MISSING:unit" in (
        authority.missing_requirements_json
    )
