"""Fail-closed B4 knowledge-rule compilation and transparent projections."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Sequence

from app.models.lab_rules import (
    RULE_DIRECTIONALITIES,
    RULE_ENDPOINT_KINDS,
    RULE_RELATIONS,
    RULE_REVIEW_STATES,
    RULE_RUNTIME_ROLES,
    RULE_STATUSES,
    RULE_SUPPORT_KINDS,
    LabKnowledgeRule,
    LabRuleCompilationRun,
    LabRuleContradiction,
    LabRuleGroup,
    LabRuleGroupMember,
    LabRuleSupportEvidence,
)

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from app.repositories.lab import LabRepository

RULE_DIAGNOSTIC_CODES = (
    "MALFORMED_RECORD",
    "MISSING_SOURCE",
    "MISSING_EXACT_LOCATOR",
    "UNRESOLVED_EXACT_IDENTITY",
    "GENERIC_PROSE",
    "MISSING_GROUP_DEFINITION",
    "UNSUPPORTED_RELATION",
    "UNSUPPORTED_GENERALIZATION",
    "INVALID_UNIT_OR_DOSE_DOMAIN",
    "MISSING_MATRIX",
    "DUPLICATE_RULE",
    "CONTRADICTION",
    "DIRECTED_CYCLE",
    "ORPHAN_REFERENCE",
    "NUMERICAL_CLAIM_WITHOUT_CONTROLLED_EVIDENCE",
    "AUTHORITY_PROMOTION_REJECTED",
)


class RuleAuthorityError(ValueError):
    """Raised when a rule attempts to exceed its evidence and scope."""


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_json_sha256(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _nonempty(value: str, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise RuleAuthorityError(f"{label} must not be empty")
    return normalized


def _sha_or_none(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if len(normalized) != 64 or any(ch not in "0123456789abcdef" for ch in normalized):
        raise RuleAuthorityError(f"{label} must be a 64-character SHA-256")
    return normalized


def _sha_required(value: str | None, label: str) -> str:
    digest = _sha_or_none(value, label)
    if digest is None:
        raise RuleAuthorityError(f"{label} is a required SHA-256")
    return digest


@dataclass(frozen=True, slots=True)
class RuleEndpointInput:
    kind: str
    raw_label: str
    identity_scope_sha256: str | None = None
    group_id: str | None = None

    def __post_init__(self) -> None:
        kind = str(self.kind).strip().upper()
        label = _nonempty(self.raw_label, "endpoint raw_label")
        identity = _sha_or_none(
            self.identity_scope_sha256,
            "endpoint identity_scope_sha256",
        )
        group_id = str(self.group_id).strip() if self.group_id else None
        if kind not in RULE_ENDPOINT_KINDS:
            raise RuleAuthorityError(f"unsupported endpoint kind: {kind}")
        if kind == "EXACT_IDENTITY" and (identity is None or group_id is not None):
            raise RuleAuthorityError("exact endpoint requires only identity digest")
        if kind == "GROUP" and (group_id is None or identity is not None):
            raise RuleAuthorityError("group endpoint requires only explicit group ID")
        if kind in {"GENERIC_PROSE", "UNRESOLVED"} and (
            identity is not None or group_id is not None
        ):
            raise RuleAuthorityError("generic or unresolved endpoint cannot claim identity")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "raw_label", label)
        object.__setattr__(self, "identity_scope_sha256", identity)
        object.__setattr__(self, "group_id", group_id)

    @property
    def token(self) -> str:
        if self.kind == "EXACT_IDENTITY":
            return f"identity:{self.identity_scope_sha256}"
        if self.kind == "GROUP":
            return f"group:{self.group_id}"
        return f"{self.kind.lower()}:{self.raw_label.casefold()}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "raw_label": self.raw_label,
            "identity_scope_sha256": self.identity_scope_sha256,
            "group_id": self.group_id,
        }


@dataclass(frozen=True, slots=True)
class RuleSupportInput:
    kind: str
    reference_id: str
    controlled: bool
    matrix_context_sha256: str | None
    dose_domain_sha256: str | None
    uncertainty_json: Mapping[str, Any]
    review_state: str

    def __post_init__(self) -> None:
        kind = str(self.kind).strip().upper()
        review = str(self.review_state).strip().upper()
        if kind not in RULE_SUPPORT_KINDS:
            raise RuleAuthorityError(f"unsupported support kind: {kind}")
        if review not in RULE_REVIEW_STATES:
            raise RuleAuthorityError(f"unsupported support review state: {review}")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(
            self,
            "reference_id",
            _nonempty(self.reference_id, "support reference_id"),
        )
        object.__setattr__(
            self,
            "matrix_context_sha256",
            _sha_or_none(self.matrix_context_sha256, "support matrix hash"),
        )
        object.__setattr__(
            self,
            "dose_domain_sha256",
            _sha_or_none(self.dose_domain_sha256, "support dose hash"),
        )
        if (self.matrix_context_sha256 is None) != (
            self.dose_domain_sha256 is None
        ):
            raise RuleAuthorityError(
                "support matrix and dose hashes must both be present or absent"
            )
        object.__setattr__(self, "review_state", review)
        canonical_json_sha256(dict(self.uncertainty_json))

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "reference_id": self.reference_id,
            "controlled": self.controlled,
            "matrix_context_sha256": self.matrix_context_sha256,
            "dose_domain_sha256": self.dose_domain_sha256,
            "uncertainty_json": dict(self.uncertainty_json),
            "review_state": self.review_state,
        }


@dataclass(frozen=True, slots=True)
class RuleGroupInput:
    group_key: str
    version: int
    label: str
    definition: str
    source_document_version_id: str | None
    source_extraction_id: str | None
    source_locator: str
    review_state: str
    status: str
    supersedes_group_id: str | None = None

    def __post_init__(self) -> None:
        review = str(self.review_state).strip().upper()
        status = str(self.status).strip().upper()
        source_document_version_id = (
            str(self.source_document_version_id).strip()
            if self.source_document_version_id
            else None
        )
        source_extraction_id = (
            str(self.source_extraction_id).strip()
            if self.source_extraction_id
            else None
        )
        source_locator = str(self.source_locator or "").strip()
        if int(self.version) < 1:
            raise RuleAuthorityError("group version must be at least one")
        if review not in RULE_REVIEW_STATES:
            raise RuleAuthorityError(f"unsupported group review state: {review}")
        if status not in RULE_STATUSES:
            raise RuleAuthorityError(f"unsupported group status: {status}")
        if status == "AUTHORITATIVE" and (
            not source_document_version_id
            or not source_extraction_id
            or not source_locator
            or review != "APPROVED"
        ):
            raise RuleAuthorityError(
                "authoritative group requires exact source, locator, and approval"
            )
        object.__setattr__(self, "group_key", _nonempty(self.group_key, "group_key"))
        object.__setattr__(self, "version", int(self.version))
        object.__setattr__(self, "label", _nonempty(self.label, "group label"))
        object.__setattr__(
            self,
            "definition",
            _nonempty(self.definition, "group definition"),
        )
        object.__setattr__(
            self,
            "source_document_version_id",
            source_document_version_id,
        )
        object.__setattr__(self, "source_extraction_id", source_extraction_id)
        object.__setattr__(self, "source_locator", source_locator)
        object.__setattr__(self, "review_state", review)
        object.__setattr__(self, "status", status)
        object.__setattr__(
            self,
            "supersedes_group_id",
            str(self.supersedes_group_id).strip()
            if self.supersedes_group_id
            else None,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "group_key": self.group_key,
            "version": self.version,
            "label": self.label,
            "definition": self.definition,
            "source_document_version_id": self.source_document_version_id,
            "source_extraction_id": self.source_extraction_id,
            "source_locator": self.source_locator,
            "review_state": self.review_state,
            "status": self.status,
            "supersedes_group_id": self.supersedes_group_id,
        }


@dataclass(frozen=True, slots=True)
class RuleGroupMemberInput:
    position: int
    identity_scope_sha256: str | None = None
    nested_group_id: str | None = None
    member_role: str | None = None

    def __post_init__(self) -> None:
        identity = _sha_or_none(
            self.identity_scope_sha256,
            "group member identity_scope_sha256",
        )
        nested_group_id = (
            str(self.nested_group_id).strip() if self.nested_group_id else None
        )
        if int(self.position) < 1:
            raise RuleAuthorityError("group member position must be at least one")
        if (identity is None) == (nested_group_id is None):
            raise RuleAuthorityError(
                "group member requires exactly one identity or nested group"
            )
        object.__setattr__(self, "position", int(self.position))
        object.__setattr__(self, "identity_scope_sha256", identity)
        object.__setattr__(self, "nested_group_id", nested_group_id)
        object.__setattr__(
            self,
            "member_role",
            str(self.member_role).strip() if self.member_role else None,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "identity_scope_sha256": self.identity_scope_sha256,
            "nested_group_id": self.nested_group_id,
            "member_role": self.member_role,
        }


@dataclass(frozen=True, slots=True)
class RuleContradictionInput:
    reason_code: str
    rationale: str
    blocking: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reason_code",
            _nonempty(self.reason_code, "contradiction reason_code").upper(),
        )
        object.__setattr__(
            self,
            "rationale",
            _nonempty(self.rationale, "contradiction rationale"),
        )
        object.__setattr__(self, "blocking", bool(self.blocking))

    def as_dict(self) -> dict[str, Any]:
        return {
            "reason_code": self.reason_code,
            "rationale": self.rationale,
            "blocking": self.blocking,
        }


@dataclass(frozen=True, slots=True)
class RuleCompilationInput:
    compiler_version: str
    source_manifest: Mapping[str, str]
    source_corpus_sha256: str
    source_record_count: int
    compiled_rule_count: int
    invalid_exact_count: int
    duplicate_count: int
    contradiction_count: int
    cycle_count: int
    orphan_count: int
    generic_count: int
    baseline_invalid_exact_count: int
    passed: bool
    report_sha256: str

    def __post_init__(self) -> None:
        manifest = {
            _nonempty(path, "source manifest path"): _sha_required(
                digest,
                f"source manifest digest for {path}",
            )
            for path, digest in self.source_manifest.items()
        }
        if not manifest:
            raise RuleAuthorityError("source manifest must not be empty")
        count_names = (
            "source_record_count",
            "compiled_rule_count",
            "invalid_exact_count",
            "duplicate_count",
            "contradiction_count",
            "cycle_count",
            "orphan_count",
            "generic_count",
            "baseline_invalid_exact_count",
        )
        for name in count_names:
            value = int(getattr(self, name))
            if value < 0:
                raise RuleAuthorityError(f"{name} must not be negative")
            object.__setattr__(self, name, value)
        if self.passed and (
            self.invalid_exact_count > self.baseline_invalid_exact_count
        ):
            raise RuleAuthorityError(
                "passing compilation cannot exceed the invalid-exact baseline"
            )
        object.__setattr__(
            self,
            "compiler_version",
            _nonempty(self.compiler_version, "compiler_version"),
        )
        object.__setattr__(self, "source_manifest", dict(sorted(manifest.items())))
        object.__setattr__(
            self,
            "source_corpus_sha256",
            _sha_required(self.source_corpus_sha256, "source corpus SHA-256"),
        )
        object.__setattr__(
            self,
            "report_sha256",
            _sha_required(self.report_sha256, "compilation report SHA-256"),
        )
        object.__setattr__(self, "passed", bool(self.passed))

    def as_dict(self) -> dict[str, Any]:
        return {
            "compiler_version": self.compiler_version,
            "source_manifest": dict(self.source_manifest),
            "source_corpus_sha256": self.source_corpus_sha256,
            "source_record_count": self.source_record_count,
            "compiled_rule_count": self.compiled_rule_count,
            "invalid_exact_count": self.invalid_exact_count,
            "duplicate_count": self.duplicate_count,
            "contradiction_count": self.contradiction_count,
            "cycle_count": self.cycle_count,
            "orphan_count": self.orphan_count,
            "generic_count": self.generic_count,
            "baseline_invalid_exact_count": self.baseline_invalid_exact_count,
            "passed": self.passed,
            "report_sha256": self.report_sha256,
        }


@dataclass(frozen=True, slots=True)
class RuleCandidateInput:
    rule_key: str
    version: int
    subject: RuleEndpointInput
    relation: str
    object: RuleEndpointInput
    directionality: str
    matrix_context: Mapping[str, Any]
    dose_domain: Mapping[str, Any]
    temporal_domain: Mapping[str, Any]
    expected_effect: Mapping[str, Any]
    attribute: str
    rationale: str
    source_document_version_id: str | None
    source_extraction_id: str | None
    source_locator: str
    evidence_class: str
    uncertainty: Mapping[str, Any]
    review_state: str
    status: str
    runtime_role: str
    raw_source_path: str
    raw_json_pointer: str
    raw_payload_sha256: str
    numerical_model_ref: str | None = None
    supersedes_rule_id: str | None = None

    def __post_init__(self) -> None:
        relation = str(self.relation).strip().upper()
        directionality = str(self.directionality).strip().upper()
        review = str(self.review_state).strip().upper()
        status = str(self.status).strip().upper()
        runtime_role = str(self.runtime_role).strip().upper()
        if int(self.version) < 1:
            raise RuleAuthorityError("rule version must be at least one")
        if relation not in RULE_RELATIONS:
            raise RuleAuthorityError(f"unsupported relation: {relation}")
        if directionality not in RULE_DIRECTIONALITIES:
            raise RuleAuthorityError(f"unsupported directionality: {directionality}")
        if review not in RULE_REVIEW_STATES:
            raise RuleAuthorityError(f"unsupported review state: {review}")
        if status not in RULE_STATUSES:
            raise RuleAuthorityError(f"unsupported status: {status}")
        if runtime_role not in RULE_RUNTIME_ROLES:
            raise RuleAuthorityError(f"unsupported runtime role: {runtime_role}")
        object.__setattr__(self, "rule_key", _nonempty(self.rule_key, "rule_key"))
        object.__setattr__(self, "version", int(self.version))
        object.__setattr__(self, "relation", relation)
        object.__setattr__(self, "directionality", directionality)
        object.__setattr__(self, "review_state", review)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "runtime_role", runtime_role)
        object.__setattr__(self, "attribute", str(self.attribute or "").strip())
        object.__setattr__(self, "rationale", str(self.rationale or "").strip())
        object.__setattr__(
            self,
            "source_locator",
            str(self.source_locator or "").strip(),
        )
        object.__setattr__(
            self,
            "evidence_class",
            _nonempty(self.evidence_class, "evidence_class"),
        )
        object.__setattr__(
            self,
            "raw_source_path",
            _nonempty(self.raw_source_path, "raw_source_path"),
        )
        object.__setattr__(
            self,
            "raw_json_pointer",
            _nonempty(self.raw_json_pointer, "raw_json_pointer"),
        )
        object.__setattr__(
            self,
            "raw_payload_sha256",
            _sha_required(self.raw_payload_sha256, "raw_payload_sha256"),
        )
        for value in (
            self.matrix_context,
            self.dose_domain,
            self.temporal_domain,
            self.expected_effect,
            self.uncertainty,
        ):
            canonical_json_sha256(dict(value))

    def semantic_payload(self) -> dict[str, Any]:
        return {
            "rule_key": self.rule_key,
            "version": self.version,
            "subject": self.subject.as_dict(),
            "relation": self.relation,
            "object": self.object.as_dict(),
            "directionality": self.directionality,
            "matrix_context": dict(self.matrix_context),
            "dose_domain": dict(self.dose_domain),
            "temporal_domain": dict(self.temporal_domain),
            "expected_effect": dict(self.expected_effect),
            "attribute": self.attribute,
            "rationale": self.rationale,
            "source_document_version_id": self.source_document_version_id,
            "source_extraction_id": self.source_extraction_id,
            "source_locator": self.source_locator,
            "evidence_class": self.evidence_class,
            "uncertainty": dict(self.uncertainty),
            "review_state": self.review_state,
            "status": self.status,
            "runtime_role": self.runtime_role,
            "numerical_model_ref": self.numerical_model_ref,
            "supersedes_rule_id": self.supersedes_rule_id,
        }


@dataclass(frozen=True, slots=True)
class CompiledRule:
    candidate: RuleCandidateInput
    status: str
    runtime_role: str
    numerical_model_ref: str | None
    diagnostics: tuple[str, ...]
    contradictions: tuple[dict[str, Any], ...]
    content_sha256: str
    active: bool

    @property
    def subject(self) -> RuleEndpointInput:
        return self.candidate.subject

    @property
    def object(self) -> RuleEndpointInput:
        return self.candidate.object


@dataclass(frozen=True, slots=True)
class RuleBatchResult:
    rules: tuple[CompiledRule, ...]
    diagnostic_codes: tuple[str, ...]
    report_sha256: str


def _stable_codes(codes: Iterable[str]) -> tuple[str, ...]:
    seen = set(codes)
    return tuple(code for code in RULE_DIAGNOSTIC_CODES if code in seen)


def _has_generic_endpoint(candidate: RuleCandidateInput) -> bool:
    return any(
        endpoint.kind in {"GENERIC_PROSE", "UNRESOLVED"}
        for endpoint in (candidate.subject, candidate.object)
    )


def _matching_controlled_support(
    candidate: RuleCandidateInput,
    supports: Sequence[RuleSupportInput],
) -> bool:
    matrix_hash = canonical_json_sha256(dict(candidate.matrix_context))
    dose_hash = canonical_json_sha256(dict(candidate.dose_domain))
    return any(
        support.controlled
        and support.review_state == "APPROVED"
        and support.matrix_context_sha256 == matrix_hash
        and support.dose_domain_sha256 == dose_hash
        for support in supports
    )


def compile_rule(
    candidate: RuleCandidateInput,
    *,
    supports: Sequence[RuleSupportInput] = (),
    contradictions: Sequence[Mapping[str, Any]] = (),
) -> CompiledRule:
    if candidate.runtime_role == "BLOCKING" and candidate.status != "AUTHORITATIVE":
        raise RuleAuthorityError("only authoritative rules may be blocking")
    if _has_generic_endpoint(candidate) and (
        candidate.status == "AUTHORITATIVE"
        or candidate.runtime_role == "BLOCKING"
        or candidate.numerical_model_ref is not None
    ):
        raise RuleAuthorityError(
            "generic prose or unresolved identity cannot be blocking or numerical"
        )
    if candidate.status == "AUTHORITATIVE":
        if (
            not candidate.source_document_version_id
            or not candidate.source_extraction_id
            or not candidate.source_locator
        ):
            raise RuleAuthorityError(
                "authoritative rule requires exact B1 source and locator"
            )
        if (
            not candidate.matrix_context
            or not candidate.dose_domain
            or not candidate.temporal_domain
            or not candidate.uncertainty
            or candidate.review_state != "APPROVED"
        ):
            raise RuleAuthorityError(
                "authoritative rule requires matrix, dose, temporal, uncertainty, and review"
            )
        if candidate.runtime_role == "BLOCKING" and not any(
            support.controlled and support.review_state == "APPROVED"
            for support in supports
        ):
            raise RuleAuthorityError(
                "blocking authority requires approved controlled support"
            )
    if candidate.numerical_model_ref is not None:
        if not any(support.controlled for support in supports):
            raise RuleAuthorityError(
                "numerical model requires controlled support"
            )
        if not _matching_controlled_support(candidate, supports):
            raise RuleAuthorityError(
                "numerical support must match matrix and dose domain"
            )
    content_sha256 = canonical_json_sha256(candidate.semantic_payload())
    contradiction_rows = tuple(
        sorted(
            (dict(row) for row in contradictions),
            key=lambda row: _canonical(row),
        )
    )
    active = candidate.status not in {"INVALID", "SUPERSEDED"}
    return CompiledRule(
        candidate=candidate,
        status=candidate.status,
        runtime_role=candidate.runtime_role,
        numerical_model_ref=candidate.numerical_model_ref,
        diagnostics=(),
        contradictions=contradiction_rows,
        content_sha256=content_sha256,
        active=active,
    )


def _directed_cycle_rule_indexes(rules: Sequence[CompiledRule]) -> set[int]:
    graph: dict[str, set[str]] = {}
    reverse_graph: dict[str, set[str]] = {}
    directed_edges: list[tuple[int, str, str]] = []
    nodes: set[str] = set()
    for index, rule in enumerate(rules):
        if not rule.active or rule.candidate.directionality != "DIRECTED":
            continue
        subject = rule.subject.token
        object_ = rule.object.token
        graph.setdefault(subject, set()).add(object_)
        reverse_graph.setdefault(object_, set()).add(subject)
        directed_edges.append((index, subject, object_))
        nodes.update((subject, object_))

    visited: set[str] = set()
    finish_order: list[str] = []
    for start in sorted(nodes):
        if start in visited:
            continue
        stack: list[tuple[str, bool]] = [(start, False)]
        while stack:
            node, expanded = stack.pop()
            if expanded:
                finish_order.append(node)
                continue
            if node in visited:
                continue
            visited.add(node)
            stack.append((node, True))
            for target in sorted(graph.get(node, ()), reverse=True):
                if target not in visited:
                    stack.append((target, False))

    component_by_node: dict[str, int] = {}
    component_sizes: dict[int, int] = {}
    for start in reversed(finish_order):
        if start in component_by_node:
            continue
        component_id = len(component_sizes)
        component_nodes: set[str] = set()
        reverse_stack = [start]
        while reverse_stack:
            node = reverse_stack.pop()
            if node in component_by_node:
                continue
            component_by_node[node] = component_id
            component_nodes.add(node)
            for target in sorted(reverse_graph.get(node, ()), reverse=True):
                if target not in component_by_node:
                    reverse_stack.append(target)
        component_sizes[component_id] = len(component_nodes)

    cycle_indexes: set[int] = set()
    for index, subject, object_ in directed_edges:
        component_id = component_by_node[subject]
        if component_id != component_by_node[object_]:
            continue
        if component_sizes[component_id] > 1 or subject == object_:
            cycle_indexes.add(index)
    return cycle_indexes


def _duplicate_signature(candidate: RuleCandidateInput) -> str:
    payload = candidate.semantic_payload()
    payload.pop("rule_key", None)
    payload.pop("version", None)
    payload.pop("supersedes_rule_id", None)
    return canonical_json_sha256(payload)


def compile_rule_batch(
    candidates: Sequence[RuleCandidateInput],
) -> RuleBatchResult:
    ordered = sorted(
        candidates,
        key=lambda item: (
            item.raw_source_path,
            item.raw_json_pointer,
            item.rule_key,
            item.version,
        ),
    )
    rules: list[CompiledRule] = [compile_rule(candidate) for candidate in ordered]
    diagnostics: set[str] = set()
    seen: dict[str, int] = {}
    for index, rule in enumerate(rules):
        signature = _duplicate_signature(rule.candidate)
        if signature in seen:
            diagnostics.add("DUPLICATE_RULE")
            rules[index] = replace(
                rule,
                diagnostics=("DUPLICATE_RULE",),
                active=False,
            )
        else:
            seen[signature] = index
    cycle_indexes = _directed_cycle_rule_indexes(rules)
    if cycle_indexes:
        diagnostics.add("DIRECTED_CYCLE")
        rules = [
            replace(
                rule,
                status="INVALID" if rule.runtime_role == "BLOCKING" else rule.status,
                runtime_role="ADVISORY"
                if rule.runtime_role == "BLOCKING"
                else rule.runtime_role,
                diagnostics=_stable_codes((*rule.diagnostics, "DIRECTED_CYCLE")),
                active=False if rule.runtime_role == "BLOCKING" else rule.active,
            )
            if index in cycle_indexes
            else rule
            for index, rule in enumerate(rules)
        ]
    stable = _stable_codes(diagnostics)
    report_sha256 = canonical_json_sha256(
        {
            "rules": [
                {
                    "content_sha256": rule.content_sha256,
                    "active": rule.active,
                    "status": rule.status,
                    "runtime_role": rule.runtime_role,
                    "diagnostics": rule.diagnostics,
                }
                for rule in rules
            ],
            "diagnostics": stable,
        }
    )
    return RuleBatchResult(
        rules=tuple(rules),
        diagnostic_codes=stable,
        report_sha256=report_sha256,
    )


def recommendation_projection(rule: CompiledRule) -> dict[str, Any]:
    candidate = rule.candidate
    return {
        "rule_key": candidate.rule_key,
        "version": candidate.version,
        "status": rule.status,
        "runtime_role": rule.runtime_role,
        "source": {
            "document_version_id": candidate.source_document_version_id,
            "extraction_id": candidate.source_extraction_id,
            "locator": candidate.source_locator,
            "path": candidate.raw_source_path,
            "json_pointer": candidate.raw_json_pointer,
        },
        "matrix_context": dict(candidate.matrix_context),
        "dose_domain": dict(candidate.dose_domain),
        "temporal_domain": dict(candidate.temporal_domain),
        "uncertainty": dict(candidate.uncertainty),
        "contradictions": [dict(row) for row in rule.contradictions],
        "diagnostics": list(rule.diagnostics),
        "numerical_model_ref": rule.numerical_model_ref,
        "mutation_command": None,
    }


class LabRuleServiceMixin:
    """Append-only persistence after pure compilation succeeds."""

    if TYPE_CHECKING:
        repository: LabRepository

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

    async def _validate_source_lineage(
        self,
        source_document_version_id: str | None,
        source_extraction_id: str | None,
    ) -> None:
        if (source_document_version_id is None) != (source_extraction_id is None):
            raise RuleAuthorityError(
                "source version and extraction must both be present or absent"
            )
        if source_document_version_id is None:
            return
        if source_extraction_id is None:
            raise RuleAuthorityError(
                "source version and extraction must both be present or absent"
            )
        source = await self.repository.get_source_document_version(
            source_document_version_id
        )
        extraction = await self.repository.get_source_extraction(
            source_extraction_id
        )
        if source is None or extraction is None:
            raise RuleAuthorityError("rule source lineage does not exist")
        if extraction.source_version_id != source.id:
            raise RuleAuthorityError(
                "rule extraction does not belong to the declared source version"
            )

    async def create_rule_group(
        self,
        group_input: RuleGroupInput,
        *,
        members: Sequence[RuleGroupMemberInput] = (),
    ) -> LabRuleGroup:
        ordered_members = tuple(sorted(members, key=lambda item: item.position))
        if len({member.position for member in ordered_members}) != len(
            ordered_members
        ):
            raise RuleAuthorityError("group member positions must be unique")
        group_content_sha256 = canonical_json_sha256(
            {
                "group": group_input.as_dict(),
                "members": [member.as_dict() for member in ordered_members],
            }
        )
        async with self._transaction():
            existing = await self.repository.rule_group_by_key_version(
                group_input.group_key,
                group_input.version,
            )
            if existing is not None:
                if existing.content_sha256 != group_content_sha256:
                    raise RuleAuthorityError(
                        "group key and version already contain different content"
                    )
                return existing
            same_hash = await self.repository.rule_group_by_hash(
                group_content_sha256
            )
            if same_hash is not None:
                raise RuleAuthorityError(
                    "group content hash is already bound to another key or version"
                )
            await self._validate_source_lineage(
                group_input.source_document_version_id,
                group_input.source_extraction_id,
            )
            if group_input.supersedes_group_id is not None:
                superseded = await self.repository.get_rule_group(
                    group_input.supersedes_group_id
                )
                if superseded is None:
                    raise RuleAuthorityError("superseded rule group does not exist")
                if (
                    superseded.group_key != group_input.group_key
                    or superseded.version >= group_input.version
                ):
                    raise RuleAuthorityError(
                        "superseded group must be an earlier version of the same key"
                    )
            for member in ordered_members:
                if member.nested_group_id is None:
                    continue
                nested = await self.repository.get_rule_group(
                    member.nested_group_id
                )
                if nested is None:
                    raise RuleAuthorityError("nested rule group does not exist")
            group = await self.repository.add(
                LabRuleGroup(
                    group_key=group_input.group_key,
                    version=group_input.version,
                    label=group_input.label,
                    definition=group_input.definition,
                    source_document_version_id=(
                        group_input.source_document_version_id
                    ),
                    source_extraction_id=group_input.source_extraction_id,
                    source_locator=group_input.source_locator or None,
                    review_state=group_input.review_state,
                    status=group_input.status,
                    supersedes_group_id=group_input.supersedes_group_id,
                    content_sha256=group_content_sha256,
                )
            )
            for member in ordered_members:
                member_content_sha256 = canonical_json_sha256(
                    {
                        "group_content_sha256": group_content_sha256,
                        **member.as_dict(),
                    }
                )
                await self.repository.add(
                    LabRuleGroupMember(
                        group_id=group.id,
                        position=member.position,
                        identity_scope_sha256=member.identity_scope_sha256,
                        nested_group_id=member.nested_group_id,
                        member_role=member.member_role,
                        content_sha256=member_content_sha256,
                    )
                )
            return group

    async def _persist_rule_supports(
        self,
        rule_id: str,
        supports: Sequence[RuleSupportInput],
    ) -> None:
        ordered = sorted(supports, key=lambda item: _canonical(item.as_dict()))
        for support in ordered:
            content_sha256 = canonical_json_sha256(
                {"rule_id": rule_id, **support.as_dict()}
            )
            existing = await self.repository.rule_support_by_hash(content_sha256)
            if existing is not None:
                if existing.rule_id != rule_id:
                    raise RuleAuthorityError(
                        "support content hash belongs to another rule"
                    )
                continue
            await self.repository.add(
                LabRuleSupportEvidence(
                    rule_id=rule_id,
                    support_kind=support.kind,
                    reference_id=support.reference_id,
                    controlled=support.controlled,
                    matrix_context_sha256=support.matrix_context_sha256,
                    dose_domain_sha256=support.dose_domain_sha256,
                    uncertainty_json=dict(support.uncertainty_json),
                    review_state=support.review_state,
                    content_sha256=content_sha256,
                )
            )

    async def persist_compiled_rule(
        self,
        compiled: CompiledRule,
        *,
        supports: Sequence[RuleSupportInput] = (),
    ) -> LabKnowledgeRule:
        verified = compile_rule(
            compiled.candidate,
            supports=supports,
            contradictions=compiled.contradictions,
        )
        if (
            verified.content_sha256 != compiled.content_sha256
            or verified.status != compiled.status
            or verified.runtime_role != compiled.runtime_role
            or verified.numerical_model_ref != compiled.numerical_model_ref
        ):
            raise RuleAuthorityError(
                "compiled rule does not match deterministic recompilation"
            )
        if not compiled.active and compiled.status not in {
            "INVALID",
            "SUPERSEDED",
        }:
            raise RuleAuthorityError(
                "inactive compiled rule must be explicitly invalid or superseded"
            )
        candidate = compiled.candidate
        async with self._transaction():
            existing = await self.repository.knowledge_rule_by_key_version(
                candidate.rule_key,
                candidate.version,
            )
            if existing is not None:
                if existing.content_sha256 != compiled.content_sha256:
                    raise RuleAuthorityError(
                        "rule key and version already contain different content"
                    )
                await self._persist_rule_supports(existing.id, supports)
                return existing
            same_hash = await self.repository.knowledge_rule_by_hash(
                compiled.content_sha256
            )
            if same_hash is not None:
                raise RuleAuthorityError(
                    "rule content hash is already bound to another key or version"
                )
            await self._validate_source_lineage(
                candidate.source_document_version_id,
                candidate.source_extraction_id,
            )
            for endpoint in (candidate.subject, candidate.object):
                if endpoint.kind != "GROUP":
                    continue
                if endpoint.group_id is None:
                    raise RuleAuthorityError(
                        "group endpoint must declare an explicit group ID"
                    )
                group = await self.repository.get_rule_group(endpoint.group_id)
                if group is None:
                    raise RuleAuthorityError(
                        "group endpoint must reference an existing explicit group"
                    )
            if candidate.supersedes_rule_id is not None:
                superseded = await self.repository.get_knowledge_rule(
                    candidate.supersedes_rule_id
                )
                if superseded is None:
                    raise RuleAuthorityError("superseded rule does not exist")
                if (
                    superseded.rule_key != candidate.rule_key
                    or superseded.version >= candidate.version
                ):
                    raise RuleAuthorityError(
                        "superseded rule must be an earlier version of the same key"
                    )
            rule = await self.repository.add(
                LabKnowledgeRule(
                    rule_key=candidate.rule_key,
                    version=candidate.version,
                    subject_kind=candidate.subject.kind,
                    subject_raw_label=candidate.subject.raw_label,
                    subject_identity_scope_sha256=(
                        candidate.subject.identity_scope_sha256
                    ),
                    subject_group_id=candidate.subject.group_id,
                    relation=candidate.relation,
                    object_kind=candidate.object.kind,
                    object_raw_label=candidate.object.raw_label,
                    object_identity_scope_sha256=(
                        candidate.object.identity_scope_sha256
                    ),
                    object_group_id=candidate.object.group_id,
                    directionality=candidate.directionality,
                    matrix_context_json=dict(candidate.matrix_context),
                    dose_domain_json=dict(candidate.dose_domain),
                    temporal_domain_json=dict(candidate.temporal_domain),
                    expected_effect_json=dict(candidate.expected_effect),
                    attribute=candidate.attribute,
                    rationale=candidate.rationale,
                    source_document_version_id=(
                        candidate.source_document_version_id
                    ),
                    source_extraction_id=candidate.source_extraction_id,
                    source_locator=candidate.source_locator,
                    evidence_class=candidate.evidence_class,
                    uncertainty_json=dict(candidate.uncertainty),
                    review_state=candidate.review_state,
                    status=compiled.status,
                    runtime_role=compiled.runtime_role,
                    numerical_model_ref=compiled.numerical_model_ref,
                    supersedes_rule_id=candidate.supersedes_rule_id,
                    raw_source_path=candidate.raw_source_path,
                    raw_json_pointer=candidate.raw_json_pointer,
                    raw_payload_sha256=candidate.raw_payload_sha256,
                    compiler_diagnostics_json=list(compiled.diagnostics),
                    content_sha256=compiled.content_sha256,
                )
            )
            await self._persist_rule_supports(rule.id, supports)
            return rule

    async def record_rule_contradiction(
        self,
        rule_id: str,
        contradictory_rule_id: str,
        contradiction_input: RuleContradictionInput,
    ) -> LabRuleContradiction:
        first_id, second_id = sorted(
            (
                _nonempty(rule_id, "rule_id"),
                _nonempty(contradictory_rule_id, "contradictory_rule_id"),
            )
        )
        if first_id == second_id:
            raise RuleAuthorityError("a rule cannot contradict itself")
        content_sha256 = canonical_json_sha256(
            {
                "rule_id": first_id,
                "contradictory_rule_id": second_id,
                **contradiction_input.as_dict(),
            }
        )
        async with self._transaction():
            for candidate_id in (first_id, second_id):
                if await self.repository.get_knowledge_rule(candidate_id) is None:
                    raise RuleAuthorityError(
                        "contradiction must reference two existing rules"
                    )
            existing = await self.repository.rule_contradiction_by_pair_reason(
                first_id,
                second_id,
                contradiction_input.reason_code,
            )
            if existing is not None:
                if existing.content_sha256 != content_sha256:
                    raise RuleAuthorityError(
                        "contradiction pair and reason already contain different content"
                    )
                return existing
            same_hash = await self.repository.rule_contradiction_by_hash(
                content_sha256
            )
            if same_hash is not None:
                return same_hash
            return await self.repository.add(
                LabRuleContradiction(
                    rule_id=first_id,
                    contradictory_rule_id=second_id,
                    reason_code=contradiction_input.reason_code,
                    rationale=contradiction_input.rationale,
                    blocking=contradiction_input.blocking,
                    content_sha256=content_sha256,
                )
            )

    async def record_rule_compilation(
        self,
        compilation_input: RuleCompilationInput,
    ) -> LabRuleCompilationRun:
        content_sha256 = canonical_json_sha256(compilation_input.as_dict())
        async with self._transaction():
            existing = await self.repository.rule_compilation_by_hash(
                content_sha256
            )
            if existing is not None:
                return existing
            return await self.repository.add(
                LabRuleCompilationRun(
                    compiler_version=compilation_input.compiler_version,
                    source_manifest_json=dict(compilation_input.source_manifest),
                    source_corpus_sha256=(
                        compilation_input.source_corpus_sha256
                    ),
                    source_record_count=compilation_input.source_record_count,
                    compiled_rule_count=compilation_input.compiled_rule_count,
                    invalid_exact_count=compilation_input.invalid_exact_count,
                    duplicate_count=compilation_input.duplicate_count,
                    contradiction_count=compilation_input.contradiction_count,
                    cycle_count=compilation_input.cycle_count,
                    orphan_count=compilation_input.orphan_count,
                    generic_count=compilation_input.generic_count,
                    baseline_invalid_exact_count=(
                        compilation_input.baseline_invalid_exact_count
                    ),
                    passed=compilation_input.passed,
                    report_sha256=compilation_input.report_sha256,
                    content_sha256=content_sha256,
                )
            )


__all__ = [
    "RULE_DIAGNOSTIC_CODES",
    "CompiledRule",
    "LabRuleServiceMixin",
    "RuleAuthorityError",
    "RuleBatchResult",
    "RuleCandidateInput",
    "RuleCompilationInput",
    "RuleContradictionInput",
    "RuleEndpointInput",
    "RuleGroupInput",
    "RuleGroupMemberInput",
    "RuleSupportInput",
    "canonical_json_sha256",
    "compile_rule",
    "compile_rule_batch",
    "recommendation_projection",
]
