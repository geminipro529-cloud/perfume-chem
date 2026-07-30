from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.lab import APPEND_ONLY_TABLES, LAB_TABLE_NAMES
from app.models.lab_rules import (
    RULE_AUTHORITY_TABLE_NAMES,
    LabKnowledgeRule,
    LabRuleCompilationRun,
    LabRuleContradiction,
    LabRuleGroup,
    LabRuleGroupMember,
    LabRuleSupportEvidence,
)


def _constraint_names(model, constraint_type):
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, constraint_type)
    }


def _index_names(model):
    return {index.name for index in model.__table__.indexes}


def test_b4_tables_are_registered_and_append_only():
    expected = {
        "lab_rule_groups",
        "lab_rule_group_members",
        "lab_knowledge_rules",
        "lab_rule_contradictions",
        "lab_rule_support_evidence",
        "lab_rule_compilation_runs",
    }

    assert RULE_AUTHORITY_TABLE_NAMES == expected
    assert expected <= LAB_TABLE_NAMES
    assert expected <= APPEND_ONLY_TABLES


def test_group_and_member_shapes_are_versioned_and_exact():
    group_uniques = _constraint_names(LabRuleGroup, UniqueConstraint)
    group_checks = _constraint_names(LabRuleGroup, CheckConstraint)
    member_checks = _constraint_names(LabRuleGroupMember, CheckConstraint)

    assert {
        "uq_lab_rule_group_key_version",
        "uq_lab_rule_group_content_sha256",
    } <= group_uniques
    assert {
        "ck_lab_rule_group_version",
        "ck_lab_rule_group_status",
        "ck_lab_rule_group_authority",
        "ck_lab_rule_group_content_sha256",
    } <= group_checks
    assert {
        "ck_lab_rule_group_member_shape",
        "ck_lab_rule_group_member_identity_sha256",
    } <= member_checks
    assert "ix_lab_rule_group_members_group_id" in _index_names(LabRuleGroupMember)


def test_rule_schema_is_fail_closed_for_endpoint_and_authority_shape():
    checks = _constraint_names(LabKnowledgeRule, CheckConstraint)
    uniques = _constraint_names(LabKnowledgeRule, UniqueConstraint)

    assert {
        "ck_lab_knowledge_rule_subject_shape",
        "ck_lab_knowledge_rule_object_shape",
        "ck_lab_knowledge_rule_relation",
        "ck_lab_knowledge_rule_directionality",
        "ck_lab_knowledge_rule_status",
        "ck_lab_knowledge_rule_runtime_role",
        "ck_lab_knowledge_rule_blocking_authority",
        "ck_lab_knowledge_rule_generic_nonblocking",
        "ck_lab_knowledge_rule_authority_scope",
        "ck_lab_knowledge_rule_content_sha256",
        "ck_lab_knowledge_rule_payload_sha256",
    } <= checks
    assert {
        "uq_lab_knowledge_rule_key_version",
        "uq_lab_knowledge_rule_content_sha256",
    } <= uniques
    assert {
        "ix_lab_knowledge_rules_rule_key",
        "ix_lab_knowledge_rules_status",
        "ix_lab_knowledge_rules_subject_identity",
        "ix_lab_knowledge_rules_object_identity",
    } <= _index_names(LabKnowledgeRule)


def test_contradiction_support_and_compilation_shapes_are_constrained():
    contradiction_checks = _constraint_names(
        LabRuleContradiction,
        CheckConstraint,
    )
    support_checks = _constraint_names(
        LabRuleSupportEvidence,
        CheckConstraint,
    )
    compilation_checks = _constraint_names(
        LabRuleCompilationRun,
        CheckConstraint,
    )

    assert {
        "ck_lab_rule_contradiction_distinct",
        "ck_lab_rule_contradiction_ordered",
    } <= contradiction_checks
    assert {
        "ck_lab_rule_support_kind",
        "ck_lab_rule_support_reference",
        "ck_lab_rule_support_context_hashes",
    } <= support_checks
    assert {
        "ck_lab_rule_compilation_counts",
        "ck_lab_rule_compilation_baseline",
        "ck_lab_rule_compilation_hashes",
    } <= compilation_checks
