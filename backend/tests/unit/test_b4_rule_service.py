from dataclasses import replace

import pytest

from app.services.lab_rules import (
    RULE_DIAGNOSTIC_CODES,
    RuleAuthorityError,
    RuleCandidateInput,
    RuleCompilationInput,
    RuleContradictionInput,
    RuleEndpointInput,
    RuleGroupInput,
    RuleGroupMemberInput,
    RuleSupportInput,
    canonical_json_sha256,
    compile_rule,
    compile_rule_batch,
    recommendation_projection,
)
from app.services.lab_service import LabService

MATRIX_CONTEXT = {"medium": "ethanol", "product": "fine fragrance"}
DOSE_DOMAIN = {"basis": "mass_fraction", "minimum": 0.001, "maximum": 0.05}


def _endpoint(
    *,
    label: str,
    kind: str = "EXACT_IDENTITY",
    identity: str | None = None,
    group_id: str | None = None,
) -> RuleEndpointInput:
    return RuleEndpointInput(
        kind=kind,
        raw_label=label,
        identity_scope_sha256=identity or ("a" * 64 if kind == "EXACT_IDENTITY" else None),
        group_id=group_id,
    )


def _support(**overrides) -> RuleSupportInput:
    values = {
        "kind": "LAB_EXPERIMENT",
        "reference_id": "experiment-1",
        "controlled": True,
        "matrix_context_sha256": canonical_json_sha256(MATRIX_CONTEXT),
        "dose_domain_sha256": canonical_json_sha256(DOSE_DOMAIN),
        "uncertainty_json": {"kind": "standard_error", "value": 0.1},
        "review_state": "APPROVED",
    }
    values.update(overrides)
    return RuleSupportInput(**values)


def _candidate(**overrides) -> RuleCandidateInput:
    values = {
        "rule_key": "linalool-reinforces-hedione",
        "version": 1,
        "subject": _endpoint(label="Linalool"),
        "relation": "REINFORCES",
        "object": _endpoint(label="Hedione", identity="d" * 64),
        "directionality": "DIRECTED",
        "matrix_context": MATRIX_CONTEXT,
        "dose_domain": DOSE_DOMAIN,
        "temporal_domain": {"phase": "heart"},
        "expected_effect": {"direction": "increase"},
        "attribute": "floral_radiance",
        "rationale": "Controlled pair comparison.",
        "source_document_version_id": "source-version-1",
        "source_extraction_id": "extraction-1",
        "source_locator": "table 2, row 4",
        "evidence_class": "CONTROLLED_EXPERIMENT",
        "uncertainty": {"kind": "standard_error", "value": 0.1},
        "review_state": "APPROVED",
        "status": "AUTHORITATIVE",
        "runtime_role": "BLOCKING",
        "raw_source_path": "evidence/pairs.json",
        "raw_json_pointer": "/rows/0",
        "raw_payload_sha256": "e" * 64,
        "numerical_model_ref": None,
    }
    values.update(overrides)
    return RuleCandidateInput(**values)


def test_authoritative_blocking_rule_requires_full_scope_and_support():
    result = compile_rule(_candidate(), supports=(_support(),))

    assert result.status == "AUTHORITATIVE"
    assert result.runtime_role == "BLOCKING"
    assert result.diagnostics == ()
    assert result.active is True


def test_generic_prose_can_only_be_advisory_or_explanatory():
    generic = _endpoint(label="rose", kind="GENERIC_PROSE")
    candidate = _candidate(
        subject=generic,
        status="ADVISORY",
        runtime_role="EXPLANATORY",
        source_document_version_id=None,
        source_extraction_id=None,
        evidence_class="LEGACY_PROSE",
    )

    result = compile_rule(candidate)
    projection = recommendation_projection(result)

    assert result.active is True
    assert result.status == "ADVISORY"
    assert result.runtime_role == "EXPLANATORY"
    assert result.numerical_model_ref is None
    assert projection["mutation_command"] is None
    assert projection["status"] == "ADVISORY"
    assert projection["source"]["path"] == "evidence/pairs.json"
    assert projection["matrix_context"] == candidate.matrix_context
    assert projection["dose_domain"] == candidate.dose_domain
    assert projection["uncertainty"] == candidate.uncertainty
    assert projection["contradictions"] == []


@pytest.mark.parametrize(
    ("status", "role"),
    [
        ("SUPPORTED", "BLOCKING"),
        ("ADVISORY", "BLOCKING"),
        ("SPECULATIVE", "BLOCKING"),
        ("INVALID", "BLOCKING"),
        ("SUPERSEDED", "BLOCKING"),
    ],
)
def test_only_authoritative_rules_may_be_blocking(status, role):
    with pytest.raises(RuleAuthorityError, match="only authoritative"):
        compile_rule(
            _candidate(status=status, runtime_role=role),
            supports=(_support(),),
        )


def test_generic_prose_cannot_be_blocking_or_numerical():
    generic = _endpoint(label="musks", kind="GENERIC_PROSE")

    with pytest.raises(RuleAuthorityError, match="generic prose"):
        compile_rule(
            _candidate(
                subject=generic,
                status="AUTHORITATIVE",
                runtime_role="BLOCKING",
                numerical_model_ref="model-1",
            ),
            supports=(_support(),),
        )


def test_numerical_model_requires_controlled_matching_support():
    candidate = _candidate(
        numerical_model_ref="model-1",
        runtime_role="ADVISORY",
    )

    with pytest.raises(RuleAuthorityError, match="controlled support"):
        compile_rule(candidate, supports=(_support(controlled=False),))

    with pytest.raises(RuleAuthorityError, match="matrix and dose"):
        compile_rule(
            candidate,
            supports=(
                _support(
                    matrix_context_sha256="f" * 64,
                    dose_domain_sha256="0" * 64,
                ),
            ),
        )


def test_missing_source_scope_withholds_authority_without_fallback():
    candidate = _candidate(
        source_document_version_id=None,
        source_extraction_id=None,
        source_locator="",
    )

    with pytest.raises(RuleAuthorityError, match="exact B1 source"):
        compile_rule(candidate, supports=(_support(),))


def test_batch_diagnostics_are_stable_and_duplicates_do_not_stay_active():
    first = _candidate(status="ADVISORY", runtime_role="ADVISORY")
    duplicate = replace(first, raw_json_pointer="/rows/1")
    result = compile_rule_batch((duplicate, first))

    assert result.diagnostic_codes == tuple(
        code for code in RULE_DIAGNOSTIC_CODES if code in result.diagnostic_codes
    )
    assert "DUPLICATE_RULE" in result.diagnostic_codes
    assert sum(rule.active for rule in result.rules) == 1
    assert result.rules[0].content_sha256 == result.rules[1].content_sha256


def test_directed_cycle_is_visible_and_cannot_be_blocking():
    first = _candidate(
        status="ADVISORY",
        runtime_role="ADVISORY",
        subject=_endpoint(label="A", identity="1" * 64),
        object=_endpoint(label="B", identity="2" * 64),
    )
    second = replace(
        first,
        rule_key="b-reinforces-a",
        subject=first.object,
        object=first.subject,
        raw_json_pointer="/rows/1",
        raw_payload_sha256="f" * 64,
    )

    result = compile_rule_batch((first, second))

    assert "DIRECTED_CYCLE" in result.diagnostic_codes
    assert all(rule.runtime_role != "BLOCKING" for rule in result.rules)


def test_directed_cycle_diagnostic_marks_only_rules_in_the_cycle():
    first = _candidate(
        status="ADVISORY",
        runtime_role="ADVISORY",
        subject=_endpoint(label="A", identity="1" * 64),
        object=_endpoint(label="B", identity="2" * 64),
    )
    second = replace(
        first,
        rule_key="b-reinforces-a",
        subject=first.object,
        object=first.subject,
        raw_json_pointer="/rows/1",
        raw_payload_sha256="f" * 64,
    )
    independent = replace(
        first,
        rule_key="c-reinforces-d",
        subject=_endpoint(label="C", identity="3" * 64),
        object=_endpoint(label="D", identity="4" * 64),
        raw_json_pointer="/rows/2",
        raw_payload_sha256="0" * 64,
    )

    result = compile_rule_batch((first, second, independent))
    diagnostics_by_key = {
        rule.candidate.rule_key: rule.diagnostics for rule in result.rules
    }

    assert diagnostics_by_key[first.rule_key] == ("DIRECTED_CYCLE",)
    assert diagnostics_by_key[second.rule_key] == ("DIRECTED_CYCLE",)
    assert diagnostics_by_key[independent.rule_key] == ()


def test_required_compilation_and_payload_digests_reject_none():
    with pytest.raises(RuleAuthorityError, match="required SHA-256"):
        _candidate(raw_payload_sha256=None)

    with pytest.raises(RuleAuthorityError, match="required SHA-256"):
        RuleCompilationInput(
            compiler_version="b4-rule-compiler-v1",
            source_manifest={
                "data/knowledge_graph/pairing_rules.json": None,
            },
            source_corpus_sha256="a" * 64,
            source_record_count=0,
            compiled_rule_count=0,
            invalid_exact_count=0,
            duplicate_count=0,
            contradiction_count=0,
            cycle_count=0,
            orphan_count=0,
            generic_count=0,
            baseline_invalid_exact_count=0,
            passed=True,
            report_sha256="b" * 64,
        )


@pytest.mark.asyncio
async def test_rule_group_and_members_are_versioned_append_only_and_idempotent(
    db_session,
):
    service = LabService(db_session)
    group_input = RuleGroupInput(
        group_key="white-musks",
        version=1,
        label="White musks",
        definition="Explicitly reviewed white-musk identity set.",
        source_document_version_id=None,
        source_extraction_id=None,
        source_locator="",
        review_state="UNREVIEWED",
        status="ADVISORY",
    )
    members = (
        RuleGroupMemberInput(
            position=1,
            identity_scope_sha256="1" * 64,
            member_role="primary member",
        ),
        RuleGroupMemberInput(
            position=2,
            identity_scope_sha256="2" * 64,
            member_role="secondary member",
        ),
    )

    first = await service.create_rule_group(group_input, members=members)
    second = await service.create_rule_group(group_input, members=members)
    persisted_members = await service.repository.rule_group_members(first.id)

    assert first.id == second.id
    assert (first.group_key, first.version, first.status) == (
        "white-musks",
        1,
        "ADVISORY",
    )
    assert [member.position for member in persisted_members] == [1, 2]
    assert all(member.group_id == first.id for member in persisted_members)
    assert not hasattr(service.repository, "latest_rule_group")


@pytest.mark.asyncio
async def test_compiled_rule_persistence_links_controlled_support_and_is_idempotent(
    db_session,
):
    service = LabService(db_session)
    support = _support()
    candidate = _candidate(
        status="ADVISORY",
        runtime_role="ADVISORY",
        numerical_model_ref="bounded-model-v1",
        source_document_version_id=None,
        source_extraction_id=None,
    )
    compiled = compile_rule(candidate, supports=(support,))

    first = await service.persist_compiled_rule(compiled, supports=(support,))
    second = await service.persist_compiled_rule(compiled, supports=(support,))
    persisted_supports = await service.repository.supports_for_rule(first.id)

    assert first.id == second.id
    assert first.content_sha256 == compiled.content_sha256
    assert first.runtime_role == "ADVISORY"
    assert len(persisted_supports) == 1
    assert persisted_supports[0].controlled is True
    assert persisted_supports[0].matrix_context_sha256 == canonical_json_sha256(
        MATRIX_CONTEXT
    )
    assert not hasattr(service.repository, "latest_knowledge_rule")


@pytest.mark.asyncio
async def test_group_endpoint_requires_an_existing_explicit_group(db_session):
    service = LabService(db_session)
    candidate = _candidate(
        status="ADVISORY",
        runtime_role="ADVISORY",
        subject=_endpoint(
            label="White musks",
            kind="GROUP",
            group_id="missing-group",
        ),
        source_document_version_id=None,
        source_extraction_id=None,
    )

    with pytest.raises(RuleAuthorityError, match="group endpoint"):
        await service.persist_compiled_rule(compile_rule(candidate))


@pytest.mark.asyncio
async def test_contradictions_are_ordered_and_compilation_baseline_fails_closed(
    db_session,
):
    service = LabService(db_session)
    first = await service.persist_compiled_rule(
        compile_rule(
            _candidate(
                rule_key="rule-a",
                status="ADVISORY",
                runtime_role="ADVISORY",
                source_document_version_id=None,
                source_extraction_id=None,
            )
        )
    )
    second = await service.persist_compiled_rule(
        compile_rule(
            _candidate(
                rule_key="rule-b",
                subject=_endpoint(label="B", identity="2" * 64),
                object=_endpoint(label="A", identity="1" * 64),
                raw_json_pointer="/rows/1",
                raw_payload_sha256="f" * 64,
                status="ADVISORY",
                runtime_role="ADVISORY",
                source_document_version_id=None,
                source_extraction_id=None,
            )
        )
    )
    contradiction = await service.record_rule_contradiction(
        second.id,
        first.id,
        RuleContradictionInput(
            reason_code="OPPOSING_EFFECT",
            rationale="The reviewed effects point in opposite directions.",
            blocking=False,
        ),
    )
    compilation_input = RuleCompilationInput(
        compiler_version="b4-rule-compiler-v1",
        source_manifest={
            "data/knowledge_graph/pairing_rules.json": "a" * 64,
        },
        source_corpus_sha256="b" * 64,
        source_record_count=3381,
        compiled_rule_count=3381,
        invalid_exact_count=137,
        duplicate_count=68,
        contradiction_count=1,
        cycle_count=1,
        orphan_count=137,
        generic_count=5,
        baseline_invalid_exact_count=137,
        passed=True,
        report_sha256="c" * 64,
    )
    compilation = await service.record_rule_compilation(compilation_input)
    duplicate = await service.record_rule_compilation(compilation_input)

    assert contradiction.rule_id < contradiction.contradictory_rule_id
    assert compilation.id == duplicate.id
    assert compilation.passed is True
    with pytest.raises(RuleAuthorityError, match="baseline"):
        replace(compilation_input, invalid_exact_count=138)
