"""Lossless, non-runtime knowledge capsules for verified peer-worktree artifacts.

A capsule indexes complete source bytes and embeds complete typed assessments and
relation graphs.  It never replaces the source module, proves manifest
completeness, grants runtime admission, or creates formula, sensory, hedonic,
safety, stability, physical-execution, purchase, or release authority.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Any, ClassVar, Iterable, Mapping, TypeVar, cast

from engine.formulation_intelligence.accord_graph import (
    AccordRelationGraph,
    accord_graph_to_plane_assessment,
)
from engine.formulation_intelligence.admission import SourceIdentity
from engine.formulation_intelligence.contracts import (
    AuthorityCeiling,
    PlaneAssessment,
    ProvenanceRef,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_DRIVE_RE = re.compile(r"^[a-zA-Z]:")
_RecordT = TypeVar("_RecordT", bound="_CapsuleRecord")


MANDATORY_CAPSULE_EXCLUSIONS: tuple[str, ...] = (
    "compounding authority",
    "formula generation authority",
    "formula mutation authority",
    "inferred smell authority",
    "inventory mutation authority",
    "liking authority",
    "performance authority",
    "physical execution authority",
    "purchase authority",
    "release authority",
    "runtime admission authority",
    "safety authority",
    "similarity authority",
    "source replacement authority",
    "stability authority",
)


def _text(value: object, field_name: str, *, identifier: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} must be nonblank text")
    return normalized.casefold() if identifier else normalized


def _digest(value: object, field_name: str) -> str:
    normalized = _text(value, field_name).casefold()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized


def _optional_digest(value: object, field_name: str) -> str | None:
    return None if value is None else _digest(value, field_name)


def _relative_path(value: object, field_name: str) -> str:
    normalized = _text(value, field_name).replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        path.is_absolute()
        or _WINDOWS_DRIVE_RE.match(normalized)
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"{field_name} must be a traversal-free repository-relative path")
    return path.as_posix()


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, _CapsuleRecord):
        return value.as_dict()
    as_dict = getattr(value, "as_dict", None)
    if callable(as_dict):
        return as_dict()
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _to_primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {
            str(key): _to_primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_to_primitive(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON does not permit non-finite floats")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"{type(value).__name__} is not canonically serializable")


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _to_primitive(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class _CapsuleRecord:
    SCHEMA_VERSION: ClassVar[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{
                item.name: _to_primitive(getattr(self, item.name))
                for item in fields(cast(Any, self))
            },
        }

    @property
    def content_sha256(self) -> str:
        return sha256(_canonical_json_bytes(self.as_dict())).hexdigest()

    @classmethod
    def _payload(cls, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(payload, Mapping):
            raise TypeError("canonical payload must be a mapping")
        expected = {"schema_version", *(item.name for item in fields(cast(Any, cls)))}
        received = set(payload)
        if received != expected:
            raise ValueError(
                f"{cls.SCHEMA_VERSION} payload does not match the closed schema; "
                f"missing={sorted(expected - received)!r}, "
                f"extra={sorted(received - expected)!r}"
            )
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {cls.SCHEMA_VERSION!r}, "
                f"received {payload['schema_version']!r}"
            )
        return payload


class CapsuleArtifactRole(str, Enum):
    SOURCE = "source"
    CONFIG = "config"
    SCHEMA = "schema"
    TEST = "test"
    FIXTURE = "fixture"
    DOC = "doc"
    EVIDENCE = "evidence"
    PROVENANCE = "provenance"
    TOMBSTONE = "tombstone"
    MIGRATION = "migration"
    COMPATIBILITY = "compatibility"


class CapsuleArtifactDisposition(str, Enum):
    REFERENCE_ONLY = "reference_only"
    COPIED_BYTE_VERIFIED = "copied_byte_verified"
    EXCLUDED_EXPLICITLY = "excluded_explicitly"


@dataclass(frozen=True, slots=True)
class CapsuleArtifact(_CapsuleRecord):
    SCHEMA_VERSION: ClassVar[str] = "knowledge_capsule_artifact_v1"

    artifact_id: str
    role: CapsuleArtifactRole
    source_relative_path: str
    byte_size: int
    sha256: str
    disposition: CapsuleArtifactDisposition
    destination_relative_path: str | None = None
    exclusion_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", _text(self.artifact_id, "artifact_id", identifier=True))
        object.__setattr__(self, "role", CapsuleArtifactRole(self.role))
        object.__setattr__(
            self,
            "source_relative_path",
            _relative_path(self.source_relative_path, "source_relative_path"),
        )
        if isinstance(self.byte_size, bool) or not isinstance(self.byte_size, int):
            raise TypeError("byte_size must be an integer")
        if self.byte_size < 0:
            raise ValueError("byte_size must be nonnegative")
        object.__setattr__(self, "sha256", _digest(self.sha256, "sha256"))
        disposition = CapsuleArtifactDisposition(self.disposition)
        object.__setattr__(self, "disposition", disposition)
        destination = (
            None
            if self.destination_relative_path is None
            else _relative_path(
                self.destination_relative_path,
                "destination_relative_path",
            )
        )
        reason = (
            None
            if self.exclusion_reason is None
            else _text(self.exclusion_reason, "exclusion_reason")
        )
        if disposition is CapsuleArtifactDisposition.COPIED_BYTE_VERIFIED:
            if destination is None:
                raise ValueError("copied-byte-verified artifacts require a destination path")
            if reason is not None:
                raise ValueError("copied-byte-verified artifacts cannot carry an exclusion reason")
        else:
            if destination is not None:
                raise ValueError("non-copied artifacts cannot carry a destination path")
            if reason is None:
                raise ValueError("reference-only and excluded artifacts require a reason")
        object.__setattr__(self, "destination_relative_path", destination)
        object.__setattr__(self, "exclusion_reason", reason)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CapsuleArtifact:
        data = cls._payload(payload)
        return cls(
            artifact_id=data["artifact_id"],
            role=CapsuleArtifactRole(data["role"]),
            source_relative_path=data["source_relative_path"],
            byte_size=data["byte_size"],
            sha256=data["sha256"],
            disposition=CapsuleArtifactDisposition(data["disposition"]),
            destination_relative_path=data["destination_relative_path"],
            exclusion_reason=data["exclusion_reason"],
        )


class KnowledgeCapsuleState(str, Enum):
    HOLD = "hold"
    QUARANTINED = "quarantined"
    CAPTURED_READ_ONLY = "captured_read_only"


class CapsuleVerificationStatus(str, Enum):
    PASS = "pass"
    HOLD = "hold"


@dataclass(frozen=True, slots=True)
class CapsuleManifestVerificationReceipt(_CapsuleRecord):
    SCHEMA_VERSION: ClassVar[str] = "knowledge_capsule_manifest_receipt_v1"

    receipt_id: str
    verifier_id: str
    verifier_version: str
    source_identity_sha256: str
    artifact_manifest_sha256: str
    output_sha256: str
    verification_status: CapsuleVerificationStatus
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "receipt_id",
            _text(self.receipt_id, "receipt_id", identifier=True),
        )
        object.__setattr__(
            self,
            "verifier_id",
            _text(self.verifier_id, "verifier_id", identifier=True),
        )
        object.__setattr__(
            self,
            "verifier_version",
            _text(self.verifier_version, "verifier_version"),
        )
        for field_name in (
            "source_identity_sha256",
            "artifact_manifest_sha256",
            "output_sha256",
        ):
            object.__setattr__(self, field_name, _digest(getattr(self, field_name), field_name))
        status = CapsuleVerificationStatus(self.verification_status)
        object.__setattr__(self, "verification_status", status)
        blockers = tuple(sorted({_text(item, "blockers") for item in self.blockers}))
        if status is CapsuleVerificationStatus.PASS and blockers:
            raise ValueError("PASS manifest receipts cannot contain blockers")
        if status is CapsuleVerificationStatus.HOLD and not blockers:
            raise ValueError("HOLD manifest receipts require an explicit blocker")
        object.__setattr__(self, "blockers", blockers)

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> CapsuleManifestVerificationReceipt:
        data = cls._payload(payload)
        return cls(
            receipt_id=data["receipt_id"],
            verifier_id=data["verifier_id"],
            verifier_version=data["verifier_version"],
            source_identity_sha256=data["source_identity_sha256"],
            artifact_manifest_sha256=data["artifact_manifest_sha256"],
            output_sha256=data["output_sha256"],
            verification_status=CapsuleVerificationStatus(
                data["verification_status"]
            ),
            blockers=tuple(data["blockers"]),
        )


_AUTHORITY_FIELDS = (
    "runtime_admission_authorized",
    "source_replacement_authorized",
    "formula_authority",
    "inventory_mutation_authority",
    "physical_execution_authority",
    "purchase_authority",
    "sensory_authority",
    "liking_authority",
    "similarity_authority",
    "performance_authority",
    "safety_authority",
    "stability_authority",
    "release_authority",
)


def _canonical_assessments(values: Iterable[PlaneAssessment]) -> tuple[PlaneAssessment, ...]:
    by_hash: dict[str, PlaneAssessment] = {}
    by_id: dict[str, PlaneAssessment] = {}
    for value in values:
        if not isinstance(value, PlaneAssessment):
            raise TypeError("assessments must contain PlaneAssessment values")
        same_id = by_id.get(value.assessment_id)
        if same_id is not None and same_id != value:
            raise ValueError("assessment_id values must identify exact records")
        previous = by_hash.get(value.content_sha256)
        if previous is not None and previous != value:
            raise ValueError("assessment content hashes must identify exact records")
        by_id[value.assessment_id] = value
        by_hash[value.content_sha256] = value
    return tuple(by_hash[key] for key in sorted(by_hash))


def _canonical_graphs(values: Iterable[AccordRelationGraph]) -> tuple[AccordRelationGraph, ...]:
    by_hash: dict[str, AccordRelationGraph] = {}
    by_id: dict[str, AccordRelationGraph] = {}
    for value in values:
        if not isinstance(value, AccordRelationGraph):
            raise TypeError("relation_graphs must contain AccordRelationGraph values")
        same_id = by_id.get(value.graph_id)
        if same_id is not None and same_id != value:
            raise ValueError("graph_id values must identify exact records")
        previous = by_hash.get(value.content_sha256)
        if previous is not None and previous != value:
            raise ValueError("relation graph content hashes must identify exact records")
        by_id[value.graph_id] = value
        by_hash[value.content_sha256] = value
    return tuple(by_hash[key] for key in sorted(by_hash))


def _nested_provenance(value: Any) -> tuple[ProvenanceRef, ...]:
    found_by_hash: dict[str, ProvenanceRef] = {}
    found_by_id: dict[str, ProvenanceRef] = {}

    def visit(item: Any) -> None:
        if isinstance(item, ProvenanceRef):
            same_id = found_by_id.get(item.provenance_id)
            if same_id is not None and same_id != item:
                raise ValueError("provenance_id values must identify exact records")
            found_by_id[item.provenance_id] = item
            found_by_hash[item.content_sha256] = item
        elif isinstance(item, Mapping):
            for nested in item.values():
                visit(nested)
        elif isinstance(item, (tuple, list, set, frozenset)):
            for nested in item:
                visit(nested)
        elif is_dataclass(item) and not isinstance(item, type):
            for field_info in fields(item):
                visit(getattr(item, field_info.name))

    visit(value)
    return tuple(found_by_hash[key] for key in sorted(found_by_hash))


def capsule_artifact_manifest_sha256(
    source_identity: SourceIdentity,
    artifacts: Iterable[CapsuleArtifact],
) -> str:
    """Bind one exact source identity to a canonical complete artifact manifest."""

    if not isinstance(source_identity, SourceIdentity):
        raise TypeError("source_identity must be a SourceIdentity")
    by_id: dict[str, CapsuleArtifact] = {}
    for artifact in artifacts:
        if not isinstance(artifact, CapsuleArtifact):
            raise TypeError("artifacts must contain CapsuleArtifact values")
        previous = by_id.get(artifact.artifact_id)
        if previous is not None and previous != artifact:
            raise ValueError("artifact_id values must identify exact records")
        by_id[artifact.artifact_id] = artifact
    if not by_id:
        raise ValueError("artifact manifest must not be empty")
    return sha256(
        _canonical_json_bytes(
            {
                "schema_version": "knowledge_capsule_bound_artifact_manifest_v1",
                "source_identity": source_identity,
                "artifacts": tuple(by_id[key] for key in sorted(by_id)),
            }
        )
    ).hexdigest()


def _capsule_identifier(capsule: KnowledgeCapsule) -> str:
    payload = {
        item.name: _to_primitive(getattr(capsule, item.name))
        for item in fields(capsule)
        if item.name != "capsule_id"
    }
    digest = sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"knowledge-capsule/v{capsule.version}/{digest}"


@dataclass(frozen=True, slots=True)
class KnowledgeCapsule(_CapsuleRecord):
    SCHEMA_VERSION: ClassVar[str] = "knowledge_capsule_v1"

    capsule_id: str
    version: int
    predecessor_sha256: str | None
    source_identity: SourceIdentity
    source_module_id: str
    source_module_version: str
    source_root_artifact_id: str
    artifacts: tuple[CapsuleArtifact, ...]
    manifest_verification_receipt: CapsuleManifestVerificationReceipt | None
    state: KnowledgeCapsuleState
    assessments: tuple[PlaneAssessment, ...]
    relation_graphs: tuple[AccordRelationGraph, ...]
    authority_ceiling: AuthorityCeiling
    authority_exclusions: tuple[str, ...]
    runtime_admission_authorized: bool = False
    source_replacement_authorized: bool = False
    formula_authority: bool = False
    inventory_mutation_authority: bool = False
    physical_execution_authority: bool = False
    purchase_authority: bool = False
    sensory_authority: bool = False
    liking_authority: bool = False
    similarity_authority: bool = False
    performance_authority: bool = False
    safety_authority: bool = False
    stability_authority: bool = False
    release_authority: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise TypeError("version must be an integer")
        if self.version < 1:
            raise ValueError("version must be at least 1")
        predecessor = _optional_digest(self.predecessor_sha256, "predecessor_sha256")
        if self.version == 1 and predecessor is not None:
            raise ValueError("version 1 must not declare a predecessor")
        if self.version > 1 and predecessor is None:
            raise ValueError("version successors require predecessor_sha256")
        object.__setattr__(self, "predecessor_sha256", predecessor)
        if not isinstance(self.source_identity, SourceIdentity):
            raise TypeError("source_identity must be a SourceIdentity")
        object.__setattr__(
            self,
            "source_module_id",
            _text(self.source_module_id, "source_module_id", identifier=True),
        )
        object.__setattr__(
            self,
            "source_module_version",
            _text(self.source_module_version, "source_module_version"),
        )
        root_id = _text(
            self.source_root_artifact_id,
            "source_root_artifact_id",
            identifier=True,
        )
        object.__setattr__(self, "source_root_artifact_id", root_id)
        artifacts_by_id: dict[str, CapsuleArtifact] = {}
        paths: set[str] = set()
        destination_paths: set[str] = set()
        for artifact in self.artifacts:
            if not isinstance(artifact, CapsuleArtifact):
                raise TypeError("artifacts must contain CapsuleArtifact values")
            if artifact.artifact_id in artifacts_by_id:
                raise ValueError("artifacts must contain unique artifact_id values")
            source_path_key = artifact.source_relative_path.casefold()
            if source_path_key in paths:
                raise ValueError(
                    "artifacts must contain case-insensitively unique source paths"
                )
            if (
                artifact.destination_relative_path is not None
                and artifact.destination_relative_path.casefold() in destination_paths
            ):
                raise ValueError(
                    "copied artifacts must contain case-insensitively unique destination paths"
                )
            artifacts_by_id[artifact.artifact_id] = artifact
            paths.add(source_path_key)
            if artifact.destination_relative_path is not None:
                destination_paths.add(artifact.destination_relative_path.casefold())
        root = artifacts_by_id.get(root_id)
        if root is None or root.role is not CapsuleArtifactRole.SOURCE:
            raise ValueError("source_root_artifact_id must identify a SOURCE artifact")
        artifacts = tuple(artifacts_by_id[key] for key in sorted(artifacts_by_id))
        object.__setattr__(self, "artifacts", artifacts)
        receipt = self.manifest_verification_receipt
        if receipt is not None and not isinstance(
            receipt,
            CapsuleManifestVerificationReceipt,
        ):
            raise TypeError(
                "manifest_verification_receipt must be a "
                "CapsuleManifestVerificationReceipt or None"
            )
        if receipt is not None:
            if receipt.source_identity_sha256 != self.source_identity.content_sha256:
                raise ValueError("manifest receipt does not bind the exact source identity")
            expected_manifest_sha256 = capsule_artifact_manifest_sha256(
                self.source_identity,
                artifacts,
            )
            if receipt.artifact_manifest_sha256 != expected_manifest_sha256:
                raise ValueError("manifest receipt does not bind the exact artifact manifest")
        state = KnowledgeCapsuleState(self.state)
        object.__setattr__(self, "state", state)
        assessments = _canonical_assessments(self.assessments)
        graphs = _canonical_graphs(self.relation_graphs)
        if not assessments and not graphs:
            raise ValueError(
                "knowledge capsules require at least one typed assessment or relation graph"
            )
        for assessment in assessments:
            semantic_records = (
                *assessment.claims,
                *assessment.support_intervals,
                *assessment.conflicts,
                *assessment.unknowns,
                *assessment.native_criteria,
                *assessment.failure_modes,
                *assessment.proposed_experiments,
            )
            if not semantic_records:
                raise ValueError("knowledge capsules reject empty assessments")
            if not assessment.provenance_refs:
                raise ValueError("capsule assessments require bound provenance")
        for graph in graphs:
            semantic_records = (
                *graph.nodes,
                *graph.edges,
                *graph.alternative_sets,
                *graph.unknowns,
            )
            if not semantic_records:
                raise ValueError("knowledge capsules reject empty relation graphs")
        _canonical_assessments(
            (
                *assessments,
                *(accord_graph_to_plane_assessment(graph) for graph in graphs),
            )
        )
        object.__setattr__(self, "assessments", assessments)
        object.__setattr__(self, "relation_graphs", graphs)
        artifact_hashes = {item.sha256 for item in artifacts}
        for provenance in _nested_provenance((assessments, graphs)):
            if provenance.source_sha256 is None:
                raise ValueError("embedded provenance must bind an artifact SHA-256")
            if provenance.source_sha256 not in artifact_hashes:
                raise ValueError(
                    "embedded provenance source_sha256 is absent from the artifact manifest"
                )
        authority = AuthorityCeiling(self.authority_ceiling)
        if state is KnowledgeCapsuleState.CAPTURED_READ_ONLY and (
            receipt is None
            or receipt.verification_status is not CapsuleVerificationStatus.PASS
        ):
            raise ValueError("captured read-only capsules require a PASS manifest receipt")
        if state in {KnowledgeCapsuleState.HOLD, KnowledgeCapsuleState.QUARANTINED}:
            if authority is not AuthorityCeiling.WITHHELD:
                raise ValueError("HOLD or quarantined capsules require WITHHELD authority")
        elif receipt is None:
            if authority is not AuthorityCeiling.WITHHELD:
                raise ValueError("unverified manifests require WITHHELD authority")
        elif not authority.is_no_stronger_than(AuthorityCeiling.STRUCTURAL_ONLY):
            raise ValueError("captured read-only capsules cannot exceed STRUCTURAL_ONLY")
        for assessment in assessments:
            if not authority.is_no_stronger_than(assessment.authority_ceiling):
                raise ValueError("capsule authority exceeds an embedded source ceiling")
        for graph in graphs:
            if not authority.is_no_stronger_than(graph.authority_ceiling):
                raise ValueError("capsule authority exceeds an embedded source ceiling")
        object.__setattr__(self, "authority_ceiling", authority)
        exclusions = tuple(sorted({_text(item, "authority_exclusions") for item in self.authority_exclusions}))
        missing = sorted(set(MANDATORY_CAPSULE_EXCLUSIONS) - set(exclusions))
        if missing:
            raise ValueError("authority_exclusions omit mandatory boundaries: " + ", ".join(missing))
        object.__setattr__(self, "authority_exclusions", exclusions)
        for field_name in _AUTHORITY_FIELDS:
            value = getattr(self, field_name)
            if not isinstance(value, bool):
                raise TypeError(f"{field_name} must be bool")
            if value:
                raise ValueError(f"{field_name} cannot be granted by a knowledge capsule")
        expected = _capsule_identifier(self)
        supplied = self.capsule_id
        if supplied == "derive":
            supplied = expected
        else:
            supplied = _text(supplied, "capsule_id")
        if supplied != expected:
            raise ValueError("capsule_id does not match complete capsule content")
        object.__setattr__(self, "capsule_id", supplied)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> KnowledgeCapsule:
        data = cls._payload(payload)
        return cls(
            capsule_id=data["capsule_id"],
            version=data["version"],
            predecessor_sha256=data["predecessor_sha256"],
            source_identity=SourceIdentity.from_dict(data["source_identity"]),
            source_module_id=data["source_module_id"],
            source_module_version=data["source_module_version"],
            source_root_artifact_id=data["source_root_artifact_id"],
            artifacts=tuple(CapsuleArtifact.from_dict(item) for item in data["artifacts"]),
            manifest_verification_receipt=(
                CapsuleManifestVerificationReceipt.from_dict(
                    data["manifest_verification_receipt"]
                )
                if data["manifest_verification_receipt"] is not None
                else None
            ),
            state=KnowledgeCapsuleState(data["state"]),
            assessments=tuple(PlaneAssessment.from_dict(item) for item in data["assessments"]),
            relation_graphs=tuple(
                AccordRelationGraph.from_dict(item) for item in data["relation_graphs"]
            ),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            authority_exclusions=tuple(data["authority_exclusions"]),
            **{field_name: data[field_name] for field_name in _AUTHORITY_FIELDS},
        )


def _derived_projection_assessments(
    capsule: KnowledgeCapsule,
) -> tuple[PlaneAssessment, ...]:
    return _canonical_assessments(
        (
            *capsule.assessments,
            *(accord_graph_to_plane_assessment(graph) for graph in capsule.relation_graphs),
        )
    )


@dataclass(frozen=True, slots=True)
class KnowledgeCapsuleProjection(_CapsuleRecord):
    SCHEMA_VERSION: ClassVar[str] = "knowledge_capsule_projection_v1"

    capsule: KnowledgeCapsule
    assessments: tuple[PlaneAssessment, ...]
    effective_authority_ceiling: AuthorityCeiling
    condition_aware_synthesis_authorized: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.capsule, KnowledgeCapsule):
            raise TypeError("capsule must be a KnowledgeCapsule")
        expected_assessments = _derived_projection_assessments(self.capsule)
        supplied = _canonical_assessments(self.assessments)
        if supplied != expected_assessments:
            raise ValueError("projection assessments must be derived from the complete capsule")
        object.__setattr__(self, "assessments", supplied)
        expected_authority = AuthorityCeiling.minimum(
            (
                self.capsule.authority_ceiling,
                *(item.authority_ceiling for item in supplied),
            )
        )
        authority = AuthorityCeiling(self.effective_authority_ceiling)
        if authority is not expected_authority:
            raise ValueError("projection authority must equal the explicit source meet")
        object.__setattr__(self, "effective_authority_ceiling", authority)
        if not isinstance(self.condition_aware_synthesis_authorized, bool):
            raise TypeError("condition_aware_synthesis_authorized must be bool")
        if self.condition_aware_synthesis_authorized:
            raise ValueError(
                "condition-aware synthesis remains disabled until AssessmentScope "
                "represents graph condition_scope"
            )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> KnowledgeCapsuleProjection:
        data = cls._payload(payload)
        return cls(
            capsule=KnowledgeCapsule.from_dict(data["capsule"]),
            assessments=tuple(PlaneAssessment.from_dict(item) for item in data["assessments"]),
            effective_authority_ceiling=AuthorityCeiling(
                data["effective_authority_ceiling"]
            ),
            condition_aware_synthesis_authorized=data[
                "condition_aware_synthesis_authorized"
            ],
        )


def project_knowledge_capsule(capsule: KnowledgeCapsule) -> KnowledgeCapsuleProjection:
    """Project complete typed sources without summaries, voting, or scalarization."""

    if not isinstance(capsule, KnowledgeCapsule):
        raise TypeError("capsule must be a KnowledgeCapsule")
    assessments = _derived_projection_assessments(capsule)
    authority = AuthorityCeiling.minimum(
        (capsule.authority_ceiling, *(item.authority_ceiling for item in assessments))
    )
    return KnowledgeCapsuleProjection(
        capsule=capsule,
        assessments=assessments,
        effective_authority_ceiling=authority,
    )


__all__ = [
    "CapsuleArtifact",
    "CapsuleArtifactDisposition",
    "CapsuleArtifactRole",
    "CapsuleManifestVerificationReceipt",
    "CapsuleVerificationStatus",
    "KnowledgeCapsule",
    "KnowledgeCapsuleProjection",
    "KnowledgeCapsuleState",
    "MANDATORY_CAPSULE_EXCLUSIONS",
    "capsule_artifact_manifest_sha256",
    "project_knowledge_capsule",
]
