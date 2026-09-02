"""Fail-closed runtime admission receipts for formulation-intelligence modules.

This module validates evidence *about* code artifacts.  It does not execute a
benchmark, import an admitted module, formulate a perfume, or grant sensory,
liking, safety, stability, physical-execution, or release authority.  Admission
is all-or-nothing for the exact source identity and exact manifest set named by
the request.
"""

from __future__ import annotations

import json
import math
import os
import re
import stat
import unicodedata
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, ClassVar, Iterable, Mapping, TypeVar, cast

from engine.formulation_intelligence.benchmark import validate_corpus_coverage
from engine.formulation_intelligence.benchmark_result import (
    BenchmarkEvaluationStatus,
    BenchmarkVerifierIdentity,
    CampaignArtifactAudience,
    FrozenBenchmarkEvaluation,
    FrozenBenchmarkVerificationBundle,
    FrozenCampaignManifest,
)
from engine.formulation_intelligence.contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimCardinality,
    ClaimKind,
    EvidenceClass,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    UnknownFact,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_RecordT = TypeVar("_RecordT", bound="_AdmissionRecord")

MANDATORY_AUTHORITY_EXCLUSIONS: tuple[str, ...] = (
    "benchmark execution",
    "compounding authority",
    "empirical authority",
    "formula generation",
    "liking authority",
    "physical execution",
    "purchase authority",
    "release authority",
    "safety authority",
    "sensory authority",
    "stability authority",
)

TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER = (
    "trusted_benchmark_result_packet_missing"
)
PRODUCTION_BENCHMARK_VERIFICATION_BUNDLE_SCHEMA_VERSION = (
    "formulation_intelligence_frozen_benchmark_verification_bundle_v2"
)
MINIMUM_PRODUCTION_BENCHMARK_CASES = 22
MINIMUM_PRODUCTION_BENCHMARK_ARMS = 5
MINIMUM_PRODUCTION_GENERATION_GROUPS = 220


def _text(value: object, field_name: str, *, identifier: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    if not normalized:
        raise ValueError(f"{field_name} must be nonblank text")
    return normalized.casefold() if identifier else normalized


def _text_tuple(
    values: Iterable[str],
    field_name: str,
    *,
    allow_empty: bool = True,
    identifiers: bool = False,
) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name, identifier=identifiers) for value in values)
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized, key=lambda value: (value.casefold(), value)))


def _digest(value: object, field_name: str) -> str:
    normalized = _text(value, field_name).casefold()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized


def _optional_digest(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _digest(value, field_name)


def _commit(value: object) -> str:
    normalized = _text(value, "head_commit").casefold()
    if not _GIT_COMMIT_RE.fullmatch(normalized):
        raise ValueError("head_commit must be a lowercase 40-character Git commit")
    return normalized


def _timestamp(value: object, field_name: str) -> str:
    normalized = _text(value, field_name)
    parseable = normalized[:-1] + "+00:00" if normalized.endswith("Z") else normalized
    try:
        parsed = datetime.fromisoformat(parseable)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a UTC offset")
    utc_value = parsed.astimezone(UTC)
    if utc_value.microsecond:
        return utc_value.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return utc_value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _parsed_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, _AdmissionRecord):
        return value.as_dict()
    if isinstance(
        value,
        (
            BenchmarkVerifierIdentity,
            FrozenBenchmarkEvaluation,
            FrozenBenchmarkVerificationBundle,
            FrozenCampaignManifest,
        ),
    ):
        return value.as_dict()
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


class _AdmissionRecord:
    SCHEMA_VERSION: ClassVar[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{
                item.name: _to_primitive(getattr(self, item.name))
                for item in fields(cast(Any, self))
            },
        }

    def constructor_values(self) -> dict[str, Any]:
        """Return exact typed field values for explicit immutable replacement."""

        return {item.name: getattr(self, item.name) for item in fields(cast(Any, self))}

    @property
    def content_sha256(self) -> str:
        return sha256(_canonical_json_bytes(self.as_dict())).hexdigest()

    @classmethod
    def _payload(cls, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(payload, Mapping):
            raise TypeError("canonical payload must be a mapping")
        expected = {
            "schema_version",
            *(item.name for item in fields(cast(Any, cls))),
        }
        received = set(payload)
        if received != expected:
            missing = sorted(expected - received)
            extra = sorted(received - expected)
            raise ValueError(
                f"{cls.SCHEMA_VERSION} payload does not match the closed schema; "
                f"missing={missing!r}, extra={extra!r}"
            )
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {cls.SCHEMA_VERSION!r}, "
                f"received {payload['schema_version']!r}"
            )
        return payload


class AdmissionStatus(str, Enum):
    ADMITTED = "admitted"
    PRE_ADMISSION_VERIFIED = "pre_admission_verified"
    HOLD = "hold"


class VerificationKind(str, Enum):
    TEST = "test"
    LINT = "lint"
    TYPECHECK = "typecheck"
    FROZEN_BENCHMARK = "frozen_benchmark"
    PERFORMANCE_RESOURCE = "performance_resource"


class VerificationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class CampaignArtifactResolutionReceipt(_AdmissionRecord):
    """Result of reading and hashing every artifact in one frozen manifest."""

    SCHEMA_VERSION = "campaign_artifact_resolution_receipt_v1"

    receipt_id: str
    campaign_manifest_sha256: str
    resolved_artifact_tree_sha256: str
    resolved_artifact_count: int
    resolved_total_bytes: int
    resolved_at_utc: str
    benchmark_execution_authorized: bool
    admission_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "receipt_id", _text(self.receipt_id, "receipt_id", identifier=True)
        )
        for field_name in (
            "campaign_manifest_sha256",
            "resolved_artifact_tree_sha256",
        ):
            object.__setattr__(
                self, field_name, _digest(getattr(self, field_name), field_name)
            )
        for field_name in ("resolved_artifact_count", "resolved_total_bytes"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        object.__setattr__(
            self,
            "resolved_at_utc",
            _timestamp(self.resolved_at_utc, "resolved_at_utc"),
        )
        if self.benchmark_execution_authorized is not False:
            raise ValueError("artifact resolution cannot authorize benchmark execution")
        if self.admission_authorized is not False:
            raise ValueError("artifact resolution cannot authorize admission")

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> CampaignArtifactResolutionReceipt:
        data = cls._payload(payload)
        return cls(
            receipt_id=data["receipt_id"],
            campaign_manifest_sha256=data["campaign_manifest_sha256"],
            resolved_artifact_tree_sha256=data[
                "resolved_artifact_tree_sha256"
            ],
            resolved_artifact_count=data["resolved_artifact_count"],
            resolved_total_bytes=data["resolved_total_bytes"],
            resolved_at_utc=data["resolved_at_utc"],
            benchmark_execution_authorized=data[
                "benchmark_execution_authorized"
            ],
            admission_authorized=data["admission_authorized"],
        )


def verify_frozen_campaign_artifact_bytes(
    manifest: FrozenCampaignManifest,
    *,
    workspace_root: Path,
    resolved_at_utc: str,
) -> CampaignArtifactResolutionReceipt:
    """Resolve, stably hash, and byte-check one complete campaign manifest."""

    if not isinstance(manifest, FrozenCampaignManifest):
        raise TypeError("manifest must be a FrozenCampaignManifest")
    if not isinstance(workspace_root, Path):
        raise TypeError("workspace_root must be a pathlib.Path")
    root = workspace_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace_root must be a directory")

    resolved_records: list[dict[str, object]] = []
    total_bytes = 0
    is_junction = getattr(os.path, "isjunction", lambda _path: False)
    for binding in manifest.artifacts:
        candidate = root.joinpath(*PurePosixPath(binding.relative_path).parts)
        if candidate.is_symlink() or is_junction(candidate):
            raise ValueError(
                f"campaign artifact may not be a symlink or junction: "
                f"{binding.relative_path}"
            )
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(root):
            raise ValueError(
                f"campaign artifact escapes workspace root: {binding.relative_path}"
            )
        if not candidate.is_file():
            raise ValueError(
                f"campaign artifact does not exist: {binding.relative_path}"
            )

        before = candidate.stat()
        with candidate.open("rb") as handle:
            payload = handle.read()
            during = os.fstat(handle.fileno())
        after = candidate.stat()
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        during_identity = (
            during.st_dev,
            during.st_ino,
            during.st_size,
            during.st_mtime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if before_identity != during_identity or before_identity != after_identity:
            raise ValueError(
                f"campaign artifact changed while hashing: {binding.relative_path}"
            )
        actual_sha256 = sha256(payload).hexdigest()
        if len(payload) != binding.byte_length:
            raise ValueError(
                f"campaign artifact byte length mismatch: {binding.relative_path}"
            )
        if actual_sha256 != binding.artifact_sha256:
            raise ValueError(
                f"campaign artifact SHA-256 mismatch: {binding.relative_path}"
            )
        total_bytes += len(payload)
        resolved_records.append(
            {
                "artifact_id": binding.artifact_id,
                "relative_path": binding.relative_path,
                "byte_length": len(payload),
                "artifact_sha256": actual_sha256,
            }
        )

    tree_sha256 = sha256(_canonical_json_bytes(resolved_records)).hexdigest()
    return CampaignArtifactResolutionReceipt(
        receipt_id=f"campaign-artifacts:{manifest.content_sha256[:24]}",
        campaign_manifest_sha256=manifest.content_sha256,
        resolved_artifact_tree_sha256=tree_sha256,
        resolved_artifact_count=len(resolved_records),
        resolved_total_bytes=total_bytes,
        resolved_at_utc=resolved_at_utc,
        benchmark_execution_authorized=False,
        admission_authorized=False,
    )


@dataclass(frozen=True, slots=True)
class PreexecutionCampaignReceipt(_AdmissionRecord):
    """Exact frozen campaign state issued before the first provider request."""

    SCHEMA_VERSION = "preexecution_campaign_receipt_v1"

    receipt_id: str
    campaign_manifest: FrozenCampaignManifest
    artifact_resolution: CampaignArtifactResolutionReceipt
    challenge_nonce: str
    execution_ledger_genesis_sha256: str
    issuer_principal_id: str
    trust_anchor_id: str
    trust_anchor_receipt_sha256: str
    issued_at_utc: str
    expires_at_utc: str
    campaign_execution_permitted: bool
    admission_authorized: bool
    empirical_authority: bool
    formula_authority: bool
    physical_execution_authority: bool
    compounding_authority: bool
    sensory_authority: bool
    liking_authority: bool
    safety_authority: bool
    stability_authority: bool
    purchase_authority: bool
    release_authority: bool

    def __post_init__(self) -> None:
        for field_name in (
            "receipt_id",
            "issuer_principal_id",
            "trust_anchor_id",
        ):
            object.__setattr__(
                self, field_name, _text(getattr(self, field_name), field_name, identifier=True)
            )
        if not isinstance(self.campaign_manifest, FrozenCampaignManifest):
            raise TypeError("campaign_manifest must be a FrozenCampaignManifest")
        if not isinstance(
            self.artifact_resolution, CampaignArtifactResolutionReceipt
        ):
            raise TypeError(
                "artifact_resolution must be a CampaignArtifactResolutionReceipt"
            )
        if (
            self.artifact_resolution.campaign_manifest_sha256
            != self.campaign_manifest.content_sha256
        ):
            raise ValueError(
                "artifact resolution does not bind the supplied campaign manifest"
            )
        for field_name in (
            "challenge_nonce",
            "execution_ledger_genesis_sha256",
            "trust_anchor_receipt_sha256",
        ):
            object.__setattr__(
                self, field_name, _digest(getattr(self, field_name), field_name)
            )
        issued = _timestamp(self.issued_at_utc, "issued_at_utc")
        expires = _timestamp(self.expires_at_utc, "expires_at_utc")
        if _parsed_timestamp(expires) <= _parsed_timestamp(issued):
            raise ValueError("expires_at_utc must be after issued_at_utc")
        if _parsed_timestamp(self.artifact_resolution.resolved_at_utc) > (
            _parsed_timestamp(issued)
        ):
            raise ValueError("artifact resolution must not occur after receipt issue")
        object.__setattr__(self, "issued_at_utc", issued)
        object.__setattr__(self, "expires_at_utc", expires)
        if self.campaign_execution_permitted is not True:
            raise ValueError(
                "a preexecution receipt must explicitly permit its exact campaign"
            )
        for field_name in (
            "admission_authorized",
            "empirical_authority",
            "formula_authority",
            "physical_execution_authority",
            "compounding_authority",
            "sensory_authority",
            "liking_authority",
            "safety_authority",
            "stability_authority",
            "purchase_authority",
            "release_authority",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"preexecution receipts cannot grant {field_name}")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PreexecutionCampaignReceipt:
        data = cls._payload(payload)
        return cls(
            receipt_id=data["receipt_id"],
            campaign_manifest=FrozenCampaignManifest.from_dict(
                data["campaign_manifest"]
            ),
            artifact_resolution=CampaignArtifactResolutionReceipt.from_dict(
                data["artifact_resolution"]
            ),
            challenge_nonce=data["challenge_nonce"],
            execution_ledger_genesis_sha256=data[
                "execution_ledger_genesis_sha256"
            ],
            issuer_principal_id=data["issuer_principal_id"],
            trust_anchor_id=data["trust_anchor_id"],
            trust_anchor_receipt_sha256=data["trust_anchor_receipt_sha256"],
            issued_at_utc=data["issued_at_utc"],
            expires_at_utc=data["expires_at_utc"],
            campaign_execution_permitted=data["campaign_execution_permitted"],
            admission_authorized=data["admission_authorized"],
            empirical_authority=data["empirical_authority"],
            formula_authority=data["formula_authority"],
            physical_execution_authority=data["physical_execution_authority"],
            compounding_authority=data["compounding_authority"],
            sensory_authority=data["sensory_authority"],
            liking_authority=data["liking_authority"],
            safety_authority=data["safety_authority"],
            stability_authority=data["stability_authority"],
            purchase_authority=data["purchase_authority"],
            release_authority=data["release_authority"],
        )


class ProductionArtifactKind(str, Enum):
    """Dynamic evidence that can exist only after campaign execution starts."""

    RENDERED_PROMPT = "rendered_prompt"
    PROVIDER_REQUEST = "provider_request"
    PROVIDER_RAW_RESPONSE = "provider_raw_response"
    PROVIDER_TRANSPORT_ERROR = "provider_transport_error"
    GENERATION_OUTPUT = "generation_output"
    BLINDED_SCORER_INPUT = "blinded_scorer_input"
    SCORER_REQUEST = "scorer_request"
    SCORER_RAW_RESPONSE = "scorer_raw_response"
    SCORER_TRANSPORT_ERROR = "scorer_transport_error"
    SCORE_ARTIFACT = "score_artifact"
    OBSERVATION_PACKET = "observation_packet"
    SEMANTIC_VERIFICATION_BUNDLE = "semantic_verification_bundle"
    VERIFIER_EVALUATION = "verifier_evaluation"
    EXECUTION_EVENT_LEDGER = "execution_event_ledger"
    RETRY_LOG = "retry_log"
    PROTOCOL_DEVIATION_LOG = "protocol_deviation_log"
    RUNTIME_CLOSURE_MANIFEST = "runtime_closure_manifest"


class ProductionEventKind(str, Enum):
    GENERATION_ATTEMPT = "generation_attempt"
    SCORING_ATTEMPT = "scoring_attempt"
    OBSERVATION_SEAL = "observation_seal"
    UNBLINDING = "unblinding"
    VERIFICATION = "verification"


class ProductionEventStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


_PRODUCTION_REQUIRED_SINGLETON_KINDS = frozenset(
    {
        ProductionArtifactKind.OBSERVATION_PACKET,
        ProductionArtifactKind.SEMANTIC_VERIFICATION_BUNDLE,
        ProductionArtifactKind.VERIFIER_EVALUATION,
        ProductionArtifactKind.EXECUTION_EVENT_LEDGER,
        ProductionArtifactKind.RETRY_LOG,
        ProductionArtifactKind.PROTOCOL_DEVIATION_LOG,
        ProductionArtifactKind.RUNTIME_CLOSURE_MANIFEST,
    }
)
_PRODUCTION_REQUIRED_MULTIPLE_KINDS = frozenset(
    {
        ProductionArtifactKind.RENDERED_PROMPT,
        ProductionArtifactKind.PROVIDER_REQUEST,
        ProductionArtifactKind.PROVIDER_RAW_RESPONSE,
        ProductionArtifactKind.GENERATION_OUTPUT,
        ProductionArtifactKind.BLINDED_SCORER_INPUT,
        ProductionArtifactKind.SCORER_REQUEST,
        ProductionArtifactKind.SCORER_RAW_RESPONSE,
        ProductionArtifactKind.SCORE_ARTIFACT,
    }
)
_WINDOWS_DEVICE_STEMS = frozenset(
    {"con", "prn", "aux", "nul", "clock$"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
)
_PORTABLE_ARTIFACT_COMPONENT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _portable_production_path(value: object) -> str:
    """Return one literal, lower-case, cross-platform artifact path."""

    if not isinstance(value, str):
        raise TypeError("relative_path must be text")
    if not value or value != value.strip() or "\\" in value:
        raise ValueError("relative_path must be canonical POSIX-relative text")
    if len(value) > 240:
        raise ValueError("relative_path exceeds the portable length limit")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ValueError("relative_path must be canonical POSIX-relative text")
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("relative_path must stay within the sealed artifact root")
    for component in path.parts:
        if len(component) > 80 or component.endswith((".", " ")):
            raise ValueError("relative_path contains a nonportable component")
        if ":" in component or not _PORTABLE_ARTIFACT_COMPONENT_RE.fullmatch(
            component
        ):
            raise ValueError("relative_path must use lower-case portable ASCII")
        if component.split(".", 1)[0].casefold() in _WINDOWS_DEVICE_STEMS:
            raise ValueError("relative_path contains a reserved Windows name")
    return value


@dataclass(frozen=True, slots=True)
class ProductionArtifactBinding(_AdmissionRecord):
    """One exact post-execution byte artifact and its typed claimants."""

    SCHEMA_VERSION = "production_benchmark_artifact_binding_v1"

    artifact_id: str
    artifact_kind: ProductionArtifactKind
    relative_path: str
    media_type: str
    byte_length: int
    artifact_sha256: str
    canonical_content_sha256: str | None
    claimant_record_sha256s: tuple[str, ...]
    audience: CampaignArtifactAudience
    dependency_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "artifact_id",
            _text(self.artifact_id, "artifact_id", identifier=True),
        )
        object.__setattr__(
            self, "artifact_kind", ProductionArtifactKind(self.artifact_kind)
        )
        object.__setattr__(
            self, "relative_path", _portable_production_path(self.relative_path)
        )
        object.__setattr__(
            self, "media_type", _text(self.media_type, "media_type", identifier=True)
        )
        if (
            isinstance(self.byte_length, bool)
            or not isinstance(self.byte_length, int)
            or self.byte_length < 0
        ):
            raise ValueError("byte_length must be a nonnegative integer")
        if (
            self.byte_length == 0
            and self.artifact_kind
            not in {
                ProductionArtifactKind.RETRY_LOG,
                ProductionArtifactKind.PROTOCOL_DEVIATION_LOG,
            }
        ):
            raise ValueError(f"{self.artifact_kind.value} may not be empty")
        object.__setattr__(
            self,
            "artifact_sha256",
            _digest(self.artifact_sha256, "artifact_sha256"),
        )
        object.__setattr__(
            self,
            "canonical_content_sha256",
            _optional_digest(
                self.canonical_content_sha256, "canonical_content_sha256"
            ),
        )
        object.__setattr__(
            self,
            "claimant_record_sha256s",
            tuple(
                sorted(
                    {
                        _digest(item, "claimant_record_sha256s")
                        for item in self.claimant_record_sha256s
                    }
                )
            ),
        )
        if not self.claimant_record_sha256s:
            raise ValueError("claimant_record_sha256s must be nonempty")
        object.__setattr__(self, "audience", CampaignArtifactAudience(self.audience))
        dependencies = _text_tuple(
            self.dependency_ids,
            "dependency_ids",
            identifiers=True,
        )
        if self.artifact_id in dependencies:
            raise ValueError("production artifacts cannot depend on themselves")
        object.__setattr__(self, "dependency_ids", dependencies)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProductionArtifactBinding:
        data = cls._payload(payload)
        return cls(
            artifact_id=data["artifact_id"],
            artifact_kind=ProductionArtifactKind(data["artifact_kind"]),
            relative_path=data["relative_path"],
            media_type=data["media_type"],
            byte_length=data["byte_length"],
            artifact_sha256=data["artifact_sha256"],
            canonical_content_sha256=data["canonical_content_sha256"],
            claimant_record_sha256s=tuple(data["claimant_record_sha256s"]),
            audience=CampaignArtifactAudience(data["audience"]),
            dependency_ids=tuple(data["dependency_ids"]),
        )


@dataclass(frozen=True, slots=True)
class CampaignExecutionEvent(_AdmissionRecord):
    """One append-only event descended from the preexecution ledger genesis."""

    SCHEMA_VERSION = "production_campaign_execution_event_v1"

    event_id: str
    campaign_id: str
    sequence_number: int
    previous_event_sha256: str
    event_kind: ProductionEventKind
    event_status: ProductionEventStatus
    subject_record_sha256: str
    producer_principal_id: str
    provider_request_id: str | None
    provider_response_id: str | None
    idempotency_key_sha256: str | None
    input_artifact_ids: tuple[str, ...]
    output_artifact_ids: tuple[str, ...]
    started_at_utc: str
    finished_at_utc: str
    error_code: str | None
    retry_of_event_sha256: str | None

    def __post_init__(self) -> None:
        for field_name in ("event_id", "campaign_id", "producer_principal_id"):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name, identifier=True),
            )
        if (
            isinstance(self.sequence_number, bool)
            or not isinstance(self.sequence_number, int)
            or self.sequence_number < 0
        ):
            raise ValueError("sequence_number must be a nonnegative integer")
        object.__setattr__(
            self,
            "previous_event_sha256",
            _digest(self.previous_event_sha256, "previous_event_sha256"),
        )
        object.__setattr__(self, "event_kind", ProductionEventKind(self.event_kind))
        status = ProductionEventStatus(self.event_status)
        object.__setattr__(self, "event_status", status)
        object.__setattr__(
            self,
            "subject_record_sha256",
            _digest(self.subject_record_sha256, "subject_record_sha256"),
        )
        for field_name in ("provider_request_id", "provider_response_id"):
            value = getattr(self, field_name)
            object.__setattr__(
                self,
                field_name,
                None if value is None else _text(value, field_name),
            )
        for field_name in ("idempotency_key_sha256", "retry_of_event_sha256"):
            object.__setattr__(
                self,
                field_name,
                _optional_digest(getattr(self, field_name), field_name),
            )
        for field_name in ("input_artifact_ids", "output_artifact_ids"):
            values = _text_tuple(
                getattr(self, field_name),
                field_name,
                identifiers=True,
            )
            object.__setattr__(self, field_name, values)
        if not self.input_artifact_ids and not self.output_artifact_ids:
            raise ValueError("events must bind at least one artifact")
        started = _timestamp(self.started_at_utc, "started_at_utc")
        finished = _timestamp(self.finished_at_utc, "finished_at_utc")
        if _parsed_timestamp(finished) < _parsed_timestamp(started):
            raise ValueError("finished_at_utc must not precede started_at_utc")
        object.__setattr__(self, "started_at_utc", started)
        object.__setattr__(self, "finished_at_utc", finished)
        object.__setattr__(
            self,
            "error_code",
            (
                None
                if self.error_code is None
                else _text(self.error_code, "error_code", identifier=True)
            ),
        )
        provider_event = self.event_kind in {
            ProductionEventKind.GENERATION_ATTEMPT,
            ProductionEventKind.SCORING_ATTEMPT,
        }
        if provider_event and (
            self.provider_request_id is None or self.idempotency_key_sha256 is None
        ):
            raise ValueError("provider attempt events require request and idempotency IDs")
        if not provider_event and any(
            value is not None
            for value in (
                self.provider_request_id,
                self.provider_response_id,
                self.idempotency_key_sha256,
                self.retry_of_event_sha256,
            )
        ):
            raise ValueError("non-provider events cannot carry provider attempt fields")
        if status is ProductionEventStatus.COMPLETED:
            if provider_event and self.provider_response_id is None:
                raise ValueError("completed provider attempts require a response ID")
            if self.error_code is not None:
                raise ValueError("completed events cannot carry an error code")
        elif self.error_code is None:
            raise ValueError("failed events require an error code")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CampaignExecutionEvent:
        data = cls._payload(payload)
        return cls(
            event_id=data["event_id"],
            campaign_id=data["campaign_id"],
            sequence_number=data["sequence_number"],
            previous_event_sha256=data["previous_event_sha256"],
            event_kind=ProductionEventKind(data["event_kind"]),
            event_status=ProductionEventStatus(data["event_status"]),
            subject_record_sha256=data["subject_record_sha256"],
            producer_principal_id=data["producer_principal_id"],
            provider_request_id=data["provider_request_id"],
            provider_response_id=data["provider_response_id"],
            idempotency_key_sha256=data["idempotency_key_sha256"],
            input_artifact_ids=tuple(data["input_artifact_ids"]),
            output_artifact_ids=tuple(data["output_artifact_ids"]),
            started_at_utc=data["started_at_utc"],
            finished_at_utc=data["finished_at_utc"],
            error_code=data["error_code"],
            retry_of_event_sha256=data["retry_of_event_sha256"],
        )


def _assert_closed_production_artifact_graph(
    artifacts: tuple[ProductionArtifactBinding, ...],
) -> None:
    by_id = {item.artifact_id: item for item in artifacts}
    missing = {
        dependency
        for item in artifacts
        for dependency in item.dependency_ids
        if dependency not in by_id
    }
    if missing:
        raise ValueError(
            f"production artifact dependencies do not resolve: {sorted(missing)!r}"
        )
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(artifact_id: str) -> None:
        if artifact_id in visited:
            return
        if artifact_id in visiting:
            raise ValueError("production artifact dependency graph must be acyclic")
        visiting.add(artifact_id)
        for dependency_id in by_id[artifact_id].dependency_ids:
            visit(dependency_id)
        visiting.remove(artifact_id)
        visited.add(artifact_id)

    for artifact_id in by_id:
        visit(artifact_id)


@dataclass(frozen=True, slots=True)
class PostexecutionCampaignReceipt(_AdmissionRecord):
    """Sealed produced-byte tree and replayed terminal ledger head."""

    SCHEMA_VERSION = "postexecution_campaign_receipt_v1"

    receipt_id: str
    campaign_id: str
    campaign_manifest_sha256: str
    preexecution_campaign_receipt_sha256: str
    resolved_artifact_tree_sha256: str
    resolved_artifact_count: int
    resolved_total_bytes: int
    execution_ledger_genesis_sha256: str
    execution_ledger_head_sha256: str
    execution_event_count: int
    completed_at_utc: str
    closure_complete: bool
    benchmark_execution_authorized: bool
    admission_authorized: bool
    empirical_authority: bool
    formula_authority: bool
    physical_execution_authority: bool
    compounding_authority: bool
    sensory_authority: bool
    liking_authority: bool
    safety_authority: bool
    stability_authority: bool
    purchase_authority: bool
    release_authority: bool

    def __post_init__(self) -> None:
        for field_name in ("receipt_id", "campaign_id"):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name, identifier=True),
            )
        for field_name in (
            "campaign_manifest_sha256",
            "preexecution_campaign_receipt_sha256",
            "resolved_artifact_tree_sha256",
            "execution_ledger_genesis_sha256",
            "execution_ledger_head_sha256",
        ):
            object.__setattr__(
                self, field_name, _digest(getattr(self, field_name), field_name)
            )
        for field_name in (
            "resolved_artifact_count",
            "execution_event_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        if (
            isinstance(self.resolved_total_bytes, bool)
            or not isinstance(self.resolved_total_bytes, int)
            or self.resolved_total_bytes < 0
        ):
            raise ValueError("resolved_total_bytes must be nonnegative")
        object.__setattr__(
            self,
            "completed_at_utc",
            _timestamp(self.completed_at_utc, "completed_at_utc"),
        )
        if self.closure_complete is not True:
            raise ValueError("postexecution campaign closure must be complete")
        for field_name in (
            "benchmark_execution_authorized",
            "admission_authorized",
            "empirical_authority",
            "formula_authority",
            "physical_execution_authority",
            "compounding_authority",
            "sensory_authority",
            "liking_authority",
            "safety_authority",
            "stability_authority",
            "purchase_authority",
            "release_authority",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"postexecution receipts cannot grant {field_name}")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PostexecutionCampaignReceipt:
        data = cls._payload(payload)
        return cls(**{item: data[item] for item in data if item != "schema_version"})


@dataclass(frozen=True, slots=True)
class ProductionBenchmarkVerificationBundle(_AdmissionRecord):
    """Production-v2 wrapper around the replayable v1 semantic evaluator."""

    SCHEMA_VERSION = PRODUCTION_BENCHMARK_VERIFICATION_BUNDLE_SCHEMA_VERSION

    campaign_manifest: FrozenCampaignManifest
    preexecution_campaign_receipt: PreexecutionCampaignReceipt
    semantic_bundle: FrozenBenchmarkVerificationBundle
    artifact_root_relative_path: str
    produced_artifacts: tuple[ProductionArtifactBinding, ...]
    execution_events: tuple[CampaignExecutionEvent, ...]
    postexecution_campaign_receipt: PostexecutionCampaignReceipt
    submitted_evaluation: FrozenBenchmarkEvaluation
    authority_exclusions: tuple[str, ...]
    benchmark_execution_authorized: bool
    runtime_admission_authorized: bool
    empirical_authority: bool
    formula_authority: bool
    physical_execution_authority: bool
    compounding_authority: bool
    sensory_authority: bool
    liking_authority: bool
    safety_authority: bool
    stability_authority: bool
    purchase_authority: bool
    release_authority: bool

    def __post_init__(self) -> None:
        if not isinstance(self.campaign_manifest, FrozenCampaignManifest):
            raise TypeError("campaign_manifest must be FrozenCampaignManifest")
        if not isinstance(
            self.preexecution_campaign_receipt, PreexecutionCampaignReceipt
        ):
            raise TypeError(
                "preexecution_campaign_receipt must be PreexecutionCampaignReceipt"
            )
        if self.preexecution_campaign_receipt.campaign_manifest != self.campaign_manifest:
            raise ValueError("preexecution receipt does not embed the campaign manifest")
        if not isinstance(self.semantic_bundle, FrozenBenchmarkVerificationBundle):
            raise TypeError("semantic_bundle must be FrozenBenchmarkVerificationBundle")
        if not isinstance(self.submitted_evaluation, FrozenBenchmarkEvaluation):
            raise TypeError("submitted_evaluation must be FrozenBenchmarkEvaluation")
        if self.semantic_bundle.recompute() != self.submitted_evaluation:
            raise ValueError("submitted evaluation must equal independent recomputation")
        object.__setattr__(
            self,
            "artifact_root_relative_path",
            _portable_production_path(self.artifact_root_relative_path),
        )

        artifacts = tuple(sorted(self.produced_artifacts, key=lambda item: item.artifact_id))
        if not artifacts or any(
            not isinstance(item, ProductionArtifactBinding) for item in artifacts
        ):
            raise TypeError("produced_artifacts must contain ProductionArtifactBinding")
        artifact_ids = tuple(item.artifact_id for item in artifacts)
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("production artifact IDs must be unique")
        portable_paths = tuple(item.relative_path.casefold() for item in artifacts)
        if len(portable_paths) != len(set(portable_paths)):
            raise ValueError("production artifact paths must be portably unique")
        kinds = {item.artifact_kind for item in artifacts}
        missing = (
            _PRODUCTION_REQUIRED_SINGLETON_KINDS
            | _PRODUCTION_REQUIRED_MULTIPLE_KINDS
        ) - kinds
        if missing:
            raise ValueError(
                "production bundle is missing required artifact kinds: "
                f"{sorted(item.value for item in missing)!r}"
            )
        for singleton in _PRODUCTION_REQUIRED_SINGLETON_KINDS:
            if sum(item.artifact_kind is singleton for item in artifacts) != 1:
                raise ValueError(
                    f"production artifact kind {singleton.value} must occur exactly once"
                )
        _assert_closed_production_artifact_graph(artifacts)
        object.__setattr__(self, "produced_artifacts", artifacts)

        events = tuple(sorted(self.execution_events, key=lambda item: item.sequence_number))
        if not events or any(not isinstance(item, CampaignExecutionEvent) for item in events):
            raise TypeError("execution_events must contain CampaignExecutionEvent")
        if tuple(item.sequence_number for item in events) != tuple(range(len(events))):
            raise ValueError("execution event sequence must be contiguous from zero")
        if len({item.event_id for item in events}) != len(events):
            raise ValueError("execution event IDs must be unique")
        if any(item.campaign_id != self.campaign_manifest.campaign_id for item in events):
            raise ValueError("every execution event must bind the frozen campaign")
        expected_previous = (
            self.preexecution_campaign_receipt.execution_ledger_genesis_sha256
        )
        for event in events:
            if event.previous_event_sha256 != expected_previous:
                raise ValueError("execution event ledger chain is broken")
            expected_previous = event.content_sha256
        object.__setattr__(self, "execution_events", events)

        artifact_id_set = set(artifact_ids)
        referenced_artifact_ids = {
            artifact_id
            for event in events
            for artifact_id in event.input_artifact_ids + event.output_artifact_ids
        }
        if not referenced_artifact_ids <= artifact_id_set:
            raise ValueError("execution events reference unknown production artifacts")
        dynamic_kinds = _PRODUCTION_REQUIRED_MULTIPLE_KINDS | {
            ProductionArtifactKind.PROVIDER_TRANSPORT_ERROR,
            ProductionArtifactKind.SCORER_TRANSPORT_ERROR,
        }
        dynamic_ids = {
            item.artifact_id for item in artifacts if item.artifact_kind in dynamic_kinds
        }
        if not dynamic_ids <= referenced_artifact_ids:
            raise ValueError("dynamic production artifacts must appear in the event ledger")

        request_ids = [
            item.provider_request_id
            for item in events
            if item.provider_request_id is not None
        ]
        response_ids = [
            item.provider_response_id
            for item in events
            if item.provider_response_id is not None
        ]
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("provider request IDs must be unique")
        if len(response_ids) != len(set(response_ids)):
            raise ValueError("provider response IDs must be unique")
        by_hash = {item.content_sha256: item for item in events}
        for event in events:
            predecessor_hash = event.retry_of_event_sha256
            if predecessor_hash is None:
                continue
            predecessor = by_hash.get(predecessor_hash)
            if predecessor is None:
                raise ValueError("retry events must reference an earlier event")
            if predecessor.sequence_number >= event.sequence_number:
                raise ValueError("retry events must reference an earlier event")
            if predecessor.subject_record_sha256 != event.subject_record_sha256:
                raise ValueError("retry events cannot cross logical subjects")
            if predecessor.event_status is not ProductionEventStatus.FAILED:
                raise ValueError("only failed attempts may be retried")

        unblinding_events = [
            item for item in events if item.event_kind is ProductionEventKind.UNBLINDING
        ]
        verification_events = [
            item for item in events if item.event_kind is ProductionEventKind.VERIFICATION
        ]
        observation_seals = [
            item
            for item in events
            if item.event_kind is ProductionEventKind.OBSERVATION_SEAL
        ]
        if len(unblinding_events) != 1 or len(verification_events) != 1:
            raise ValueError("production ledger requires one unblinding and verification")
        if len(observation_seals) != 1:
            raise ValueError("production ledger requires one observation seal")
        unblinding = unblinding_events[0]
        verification = verification_events[0]
        seal = observation_seals[0]
        scoring_events = [
            item for item in events if item.event_kind is ProductionEventKind.SCORING_ATTEMPT
        ]
        generation_events = [
            item
            for item in events
            if item.event_kind is ProductionEventKind.GENERATION_ATTEMPT
        ]
        completed_generation_events = [
            item
            for item in generation_events
            if item.event_status is ProductionEventStatus.COMPLETED
        ]
        completed_scoring_events = [
            item
            for item in scoring_events
            if item.event_status is ProductionEventStatus.COMPLETED
        ]
        if not generation_events:
            raise ValueError("production ledger requires generation events")
        if not scoring_events or any(
            _parsed_timestamp(item.finished_at_utc)
            > _parsed_timestamp(unblinding.started_at_utc)
            for item in scoring_events
        ):
            raise ValueError("all scoring must finish before unblinding")
        if max(
            _parsed_timestamp(item.finished_at_utc) for item in generation_events
        ) > min(_parsed_timestamp(item.started_at_utc) for item in scoring_events):
            raise ValueError("scoring cannot start before generation is complete")
        if max(
            _parsed_timestamp(item.finished_at_utc) for item in scoring_events
        ) > _parsed_timestamp(seal.started_at_utc):
            raise ValueError("the observation seal must follow scoring")
        if _parsed_timestamp(seal.finished_at_utc) > _parsed_timestamp(
            unblinding.started_at_utc
        ):
            raise ValueError("the observation packet must be sealed before unblinding")
        if _parsed_timestamp(unblinding.finished_at_utc) > _parsed_timestamp(
            verification.started_at_utc
        ):
            raise ValueError("verification must follow unblinding")
        if verification is not events[-1]:
            raise ValueError("verification must be the terminal execution event")
        issued = _parsed_timestamp(
            self.preexecution_campaign_receipt.issued_at_utc
        )
        expires = _parsed_timestamp(
            self.preexecution_campaign_receipt.expires_at_utc
        )
        for event in generation_events + scoring_events:
            started = _parsed_timestamp(event.started_at_utc)
            if started <= issued or started > expires:
                raise ValueError(
                    "provider attempts must start within the preexecution window"
                )

        generation_subjects = {
            item.content_sha256 for item in self.semantic_bundle.run_receipts
        }
        scoring_subjects = {
            item.content_sha256 for item in self.semantic_bundle.judge_receipts
        }
        if {item.subject_record_sha256 for item in completed_generation_events} != (
            generation_subjects
        ):
            raise ValueError("completed generation events must cover every run receipt")
        if {item.subject_record_sha256 for item in completed_scoring_events} != (
            scoring_subjects
        ):
            raise ValueError("completed scoring events must cover every judge receipt")
        if len(completed_generation_events) != len(generation_subjects):
            raise ValueError("each run receipt requires exactly one completed event")
        if len(completed_scoring_events) != len(scoring_subjects):
            raise ValueError("each judge receipt requires exactly one completed event")
        producer_principals = {
            item.producer_principal_id for item in generation_events
        }
        scorer_principals = {item.producer_principal_id for item in scoring_events}
        if len(producer_principals) != 1 or len(scorer_principals) < 2:
            raise ValueError(
                "production requires one producer and two structural scorer principals"
            )
        unblinder_principal = unblinding.producer_principal_id
        verifier_principal = verification.producer_principal_id
        role_principals = (
            producer_principals | scorer_principals | {unblinder_principal, verifier_principal}
        )
        if len(role_principals) != (
            len(producer_principals) + len(scorer_principals) + 2
        ):
            raise ValueError("producer, scorers, unblinder, and verifier must be disjoint")

        semantic = self.semantic_bundle
        corpus = semantic.corpus
        matrix = semantic.execution_matrix
        if self.campaign_manifest.benchmark_id != semantic.definition.benchmark_id:
            raise ValueError("campaign and semantic benchmark IDs differ")
        if (
            self.campaign_manifest.benchmark_definition_sha256
            != semantic.definition.content_sha256
        ):
            raise ValueError("campaign and semantic definition hashes differ")
        if self.campaign_manifest.case_ids != tuple(item.case_id for item in corpus.cases):
            raise ValueError("campaign case IDs do not match the semantic corpus")
        if self.campaign_manifest.arm_ids != tuple(item.arm_id for item in corpus.anonymized_arms):
            raise ValueError("campaign arm IDs do not match the semantic corpus")
        expected_generation_count = (
            len(matrix.case_ids)
            * len(matrix.arm_ids)
            * len(matrix.seeds)
            * matrix.repeat_count
        )
        if (
            self.campaign_manifest.independent_generation_count_per_case_arm
            != len(matrix.seeds) * matrix.repeat_count
            or self.campaign_manifest.unique_generation_group_count
            != expected_generation_count
            or self.campaign_manifest.presentation_cell_count != len(matrix.cells)
        ):
            raise ValueError("campaign and execution-matrix topology differ")

        artifact_by_kind = {
            kind: tuple(item for item in artifacts if item.artifact_kind is kind)
            for kind in ProductionArtifactKind
        }
        prompt_claims = {
            claim
            for item in artifact_by_kind[ProductionArtifactKind.RENDERED_PROMPT]
            for claim in item.claimant_record_sha256s
        }
        run_claims = {
            claim
            for item in artifact_by_kind[ProductionArtifactKind.GENERATION_OUTPUT]
            for claim in item.claimant_record_sha256s
        }
        score_claims = {
            claim
            for item in artifact_by_kind[ProductionArtifactKind.SCORE_ARTIFACT]
            for claim in item.claimant_record_sha256s
        }
        if prompt_claims != {item.content_sha256 for item in semantic.prompt_receipts}:
            raise ValueError("rendered prompt artifacts do not cover prompt receipts")
        if run_claims != {item.content_sha256 for item in semantic.run_receipts}:
            raise ValueError("generation output artifacts do not cover run receipts")
        if score_claims != {item.content_sha256 for item in semantic.judge_receipts}:
            raise ValueError("score artifacts do not cover judge receipts")
        prompt_by_hash = {
            item.content_sha256: item for item in semantic.prompt_receipts
        }
        for artifact in artifact_by_kind[ProductionArtifactKind.RENDERED_PROMPT]:
            if len(artifact.claimant_record_sha256s) != 1:
                raise ValueError("rendered prompts require one prompt-receipt claimant")
            prompt = prompt_by_hash.get(artifact.claimant_record_sha256s[0])
            if prompt is None or artifact.artifact_sha256 != prompt.rendered_prompt_sha256:
                raise ValueError("rendered prompt bytes do not match their receipt")
        run_by_hash = {item.content_sha256: item for item in semantic.run_receipts}
        for artifact in artifact_by_kind[ProductionArtifactKind.GENERATION_OUTPUT]:
            if len(artifact.claimant_record_sha256s) != 1:
                raise ValueError("generation outputs require one run-receipt claimant")
            run = run_by_hash.get(artifact.claimant_record_sha256s[0])
            if run is None or artifact.artifact_sha256 != run.output_sha256:
                raise ValueError("generation output bytes do not match their receipt")
        judge_by_hash = {
            item.content_sha256: item for item in semantic.judge_receipts
        }
        for artifact in artifact_by_kind[ProductionArtifactKind.SCORE_ARTIFACT]:
            if len(artifact.claimant_record_sha256s) != 1:
                raise ValueError("score artifacts require one judge-receipt claimant")
            judge = judge_by_hash.get(artifact.claimant_record_sha256s[0])
            if judge is None or artifact.artifact_sha256 != judge.score_artifact_sha256:
                raise ValueError("score artifact bytes do not match their receipt")
        blind_claimants: set[str] = set()
        for artifact in artifact_by_kind[
            ProductionArtifactKind.BLINDED_SCORER_INPUT
        ]:
            for claimant in artifact.claimant_record_sha256s:
                judge = judge_by_hash.get(claimant)
                if judge is None or artifact.artifact_sha256 != judge.blinded_bundle_sha256:
                    raise ValueError("blinded scorer input does not match its judge receipt")
                blind_claimants.add(claimant)
        if blind_claimants != set(judge_by_hash):
            raise ValueError("blinded scorer inputs do not cover every judge receipt")

        singleton_by_kind = {
            kind: artifact_by_kind[kind][0]
            for kind in _PRODUCTION_REQUIRED_SINGLETON_KINDS
        }
        packet_artifact = singleton_by_kind[ProductionArtifactKind.OBSERVATION_PACKET]
        bundle_artifact = singleton_by_kind[
            ProductionArtifactKind.SEMANTIC_VERIFICATION_BUNDLE
        ]
        evaluation_artifact = singleton_by_kind[
            ProductionArtifactKind.VERIFIER_EVALUATION
        ]
        closure_artifact = singleton_by_kind[
            ProductionArtifactKind.RUNTIME_CLOSURE_MANIFEST
        ]
        if packet_artifact.canonical_content_sha256 != semantic.observation_packet.content_sha256:
            raise ValueError("observation packet artifact is not canonically bound")
        if bundle_artifact.canonical_content_sha256 != semantic.content_sha256:
            raise ValueError("semantic bundle artifact is not canonically bound")
        if evaluation_artifact.canonical_content_sha256 != self.submitted_evaluation.content_sha256:
            raise ValueError("evaluation artifact is not canonically bound")
        if closure_artifact.artifact_sha256 != semantic.observation_packet.recursive_closure.closure_manifest_sha256:
            raise ValueError("runtime closure manifest artifact is not bound")

        if not isinstance(
            self.postexecution_campaign_receipt, PostexecutionCampaignReceipt
        ):
            raise TypeError(
                "postexecution_campaign_receipt must be PostexecutionCampaignReceipt"
            )
        receipt = self.postexecution_campaign_receipt
        if receipt.campaign_id != self.campaign_manifest.campaign_id:
            raise ValueError("postexecution receipt campaign mismatch")
        if receipt.campaign_manifest_sha256 != self.campaign_manifest.content_sha256:
            raise ValueError("postexecution receipt manifest mismatch")
        if (
            receipt.preexecution_campaign_receipt_sha256
            != self.preexecution_campaign_receipt.content_sha256
        ):
            raise ValueError("postexecution receipt preexecution mismatch")
        if receipt.execution_ledger_genesis_sha256 != (
            self.preexecution_campaign_receipt.execution_ledger_genesis_sha256
        ):
            raise ValueError("postexecution receipt ledger genesis mismatch")
        if receipt.execution_ledger_head_sha256 != events[-1].content_sha256:
            raise ValueError("postexecution receipt ledger head mismatch")
        if receipt.execution_event_count != len(events):
            raise ValueError("postexecution receipt event count mismatch")
        if receipt.resolved_artifact_count != len(artifacts):
            raise ValueError("postexecution receipt artifact count mismatch")
        if receipt.resolved_total_bytes != sum(item.byte_length for item in artifacts):
            raise ValueError("postexecution receipt byte total mismatch")
        if _parsed_timestamp(receipt.completed_at_utc) < _parsed_timestamp(
            events[-1].finished_at_utc
        ):
            raise ValueError("postexecution receipt predates the terminal event")

        exclusions = _text_tuple(
            self.authority_exclusions,
            "authority_exclusions",
            identifiers=True,
        )
        if exclusions != MANDATORY_AUTHORITY_EXCLUSIONS:
            raise ValueError("production bundle authority exclusions are incomplete")
        object.__setattr__(self, "authority_exclusions", exclusions)
        for field_name in (
            "benchmark_execution_authorized",
            "runtime_admission_authorized",
            "empirical_authority",
            "formula_authority",
            "physical_execution_authority",
            "compounding_authority",
            "sensory_authority",
            "liking_authority",
            "safety_authority",
            "stability_authority",
            "purchase_authority",
            "release_authority",
        ):
            if getattr(self, field_name) is not False:
                raise ValueError(f"production benchmark bundles cannot grant {field_name}")

    def recompute(self) -> FrozenBenchmarkEvaluation:
        return self.semantic_bundle.recompute()

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> ProductionBenchmarkVerificationBundle:
        data = cls._payload(payload)
        return cls(
            campaign_manifest=FrozenCampaignManifest.from_dict(
                data["campaign_manifest"]
            ),
            preexecution_campaign_receipt=PreexecutionCampaignReceipt.from_dict(
                data["preexecution_campaign_receipt"]
            ),
            semantic_bundle=FrozenBenchmarkVerificationBundle.from_dict(
                data["semantic_bundle"]
            ),
            artifact_root_relative_path=data["artifact_root_relative_path"],
            produced_artifacts=tuple(
                ProductionArtifactBinding.from_dict(item)
                for item in data["produced_artifacts"]
            ),
            execution_events=tuple(
                CampaignExecutionEvent.from_dict(item)
                for item in data["execution_events"]
            ),
            postexecution_campaign_receipt=PostexecutionCampaignReceipt.from_dict(
                data["postexecution_campaign_receipt"]
            ),
            submitted_evaluation=FrozenBenchmarkEvaluation.from_dict(
                data["submitted_evaluation"]
            ),
            authority_exclusions=tuple(data["authority_exclusions"]),
            benchmark_execution_authorized=data["benchmark_execution_authorized"],
            runtime_admission_authorized=data["runtime_admission_authorized"],
            empirical_authority=data["empirical_authority"],
            formula_authority=data["formula_authority"],
            physical_execution_authority=data["physical_execution_authority"],
            compounding_authority=data["compounding_authority"],
            sensory_authority=data["sensory_authority"],
            liking_authority=data["liking_authority"],
            safety_authority=data["safety_authority"],
            stability_authority=data["stability_authority"],
            purchase_authority=data["purchase_authority"],
            release_authority=data["release_authority"],
        )


@dataclass(frozen=True, slots=True)
class ProductionArtifactResolutionReceipt(_AdmissionRecord):
    """Fresh local resolution of a production bundle's sealed output tree."""

    SCHEMA_VERSION = "production_artifact_resolution_receipt_v1"

    receipt_id: str
    production_bundle_sha256: str
    resolved_artifact_tree_sha256: str
    resolved_artifact_count: int
    resolved_total_bytes: int
    resolved_at_utc: str
    admission_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "receipt_id", _text(self.receipt_id, "receipt_id", identifier=True)
        )
        for field_name in (
            "production_bundle_sha256",
            "resolved_artifact_tree_sha256",
        ):
            object.__setattr__(
                self, field_name, _digest(getattr(self, field_name), field_name)
            )
        if (
            isinstance(self.resolved_artifact_count, bool)
            or not isinstance(self.resolved_artifact_count, int)
            or self.resolved_artifact_count <= 0
        ):
            raise ValueError("resolved_artifact_count must be positive")
        if (
            isinstance(self.resolved_total_bytes, bool)
            or not isinstance(self.resolved_total_bytes, int)
            or self.resolved_total_bytes < 0
        ):
            raise ValueError("resolved_total_bytes must be nonnegative")
        object.__setattr__(
            self,
            "resolved_at_utc",
            _timestamp(self.resolved_at_utc, "resolved_at_utc"),
        )
        if self.admission_authorized is not False:
            raise ValueError("artifact resolution cannot authorize admission")

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> ProductionArtifactResolutionReceipt:
        data = cls._payload(payload)
        return cls(
            receipt_id=data["receipt_id"],
            production_bundle_sha256=data["production_bundle_sha256"],
            resolved_artifact_tree_sha256=data[
                "resolved_artifact_tree_sha256"
            ],
            resolved_artifact_count=data["resolved_artifact_count"],
            resolved_total_bytes=data["resolved_total_bytes"],
            resolved_at_utc=data["resolved_at_utc"],
            admission_authorized=data["admission_authorized"],
        )


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _strict_canonical_json(payload: bytes, *, field_name: str) -> Any:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"{field_name} must not contain a UTF-8 BOM")
    try:
        text = payload.decode("utf-8", errors="strict")
        decoded = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON value: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{field_name} must be strict UTF-8 JSON") from error
    if _canonical_json_bytes(decoded) != payload:
        raise ValueError(f"{field_name} must use exact canonical JSON bytes")
    return decoded


def _path_is_reparse(path: Path) -> bool:
    is_junction = getattr(os.path, "isjunction", lambda _path: False)
    try:
        attributes = path.lstat().st_file_attributes
    except AttributeError:
        attributes = 0
    return path.is_symlink() or bool(is_junction(path)) or bool(attributes & 0x400)


def _assert_no_reparse_components(root: Path, candidate: Path) -> None:
    if _path_is_reparse(root):
        raise ValueError("artifact workspace root may not be a reparse point")
    relative = candidate.relative_to(root)
    current = root
    for component in relative.parts:
        current = current / component
        if current.exists() and _path_is_reparse(current):
            raise ValueError(
                f"artifact path contains a reparse point: {relative.as_posix()}"
            )


def verify_production_artifact_bytes(
    bundle: ProductionBenchmarkVerificationBundle,
    *,
    workspace_root: Path,
    resolved_at_utc: str,
) -> ProductionArtifactResolutionReceipt:
    """Re-read the exact closed output tree and validate semantic singleton bytes."""

    if not isinstance(bundle, ProductionBenchmarkVerificationBundle):
        raise TypeError("bundle must be a ProductionBenchmarkVerificationBundle")
    if not isinstance(workspace_root, Path):
        raise TypeError("workspace_root must be a pathlib.Path")
    root = workspace_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace_root must be a directory")
    artifact_root_candidate = root.joinpath(
        *PurePosixPath(bundle.artifact_root_relative_path).parts
    )
    _assert_no_reparse_components(root, artifact_root_candidate)
    artifact_root = artifact_root_candidate.resolve(strict=True)
    if not artifact_root.is_relative_to(root) or not artifact_root.is_dir():
        raise ValueError("production artifact root must be an in-workspace directory")

    expected_paths = {item.relative_path for item in bundle.produced_artifacts}
    actual_paths: set[str] = set()
    actual_directories: set[str] = set()
    for path in artifact_root.rglob("*"):
        _assert_no_reparse_components(artifact_root, path)
        relative_path = path.relative_to(artifact_root).as_posix()
        if path.is_dir():
            actual_directories.add(relative_path)
        elif path.is_file():
            actual_paths.add(relative_path)
        else:
            raise ValueError(f"production artifact tree contains a special file: {relative_path}")
    expected_directories = {
        parent.as_posix()
        for relative_path in expected_paths
        for parent in PurePosixPath(relative_path).parents
        if parent.as_posix() != "."
    }
    if actual_paths != expected_paths:
        raise ValueError("production artifact root is not a closed manifested file set")
    if actual_directories != expected_directories:
        raise ValueError("production artifact root has unexpected or missing directories")

    resolved_records: list[dict[str, object]] = []
    payload_by_id: dict[str, bytes] = {}
    filesystem_identities: set[tuple[int, int]] = set()
    total_bytes = 0
    for binding in bundle.produced_artifacts:
        candidate = artifact_root.joinpath(
            *PurePosixPath(binding.relative_path).parts
        )
        _assert_no_reparse_components(artifact_root, candidate)
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(artifact_root):
            raise ValueError(f"production artifact escapes root: {binding.relative_path}")
        before = candidate.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"production artifact is not regular: {binding.relative_path}")
        if before.st_nlink != 1:
            raise ValueError(f"production artifact may not be hardlinked: {binding.relative_path}")
        identity = (before.st_dev, before.st_ino)
        if identity in filesystem_identities:
            raise ValueError("production artifacts must have unique filesystem identities")
        filesystem_identities.add(identity)
        with candidate.open("rb") as handle:
            payload = handle.read()
            during = os.fstat(handle.fileno())
        after = candidate.lstat()
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_nlink,
        )
        identity_during = (
            during.st_dev,
            during.st_ino,
            during.st_size,
            during.st_mtime_ns,
            during.st_nlink,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_nlink,
        )
        if identity_before != identity_during or identity_before != identity_after:
            raise ValueError(
                f"production artifact changed while hashing: {binding.relative_path}"
            )
        actual_sha256 = sha256(payload).hexdigest()
        if len(payload) != binding.byte_length:
            raise ValueError(
                f"production artifact byte length mismatch: {binding.relative_path}"
            )
        if actual_sha256 != binding.artifact_sha256:
            raise ValueError(
                f"production artifact SHA-256 mismatch: {binding.relative_path}"
            )
        if binding.canonical_content_sha256 is not None:
            _strict_canonical_json(payload, field_name=binding.relative_path)
            if actual_sha256 != binding.canonical_content_sha256:
                raise ValueError(
                    f"production artifact canonical hash mismatch: {binding.relative_path}"
                )
        payload_by_id[binding.artifact_id] = payload
        total_bytes += len(payload)
        resolved_records.append(
            {
                "schema_version": "production_artifact_tree_leaf_v1",
                "binding": binding.as_dict(),
                "actual_byte_length": len(payload),
                "actual_sha256": actual_sha256,
            }
        )

    by_kind = {
        kind: next(
            item for item in bundle.produced_artifacts if item.artifact_kind is kind
        )
        for kind in _PRODUCTION_REQUIRED_SINGLETON_KINDS
    }
    exact_singleton_payloads = {
        ProductionArtifactKind.OBSERVATION_PACKET: _canonical_json_bytes(
            bundle.semantic_bundle.observation_packet.as_dict()
        ),
        ProductionArtifactKind.SEMANTIC_VERIFICATION_BUNDLE: _canonical_json_bytes(
            bundle.semantic_bundle.as_dict()
        ),
        ProductionArtifactKind.VERIFIER_EVALUATION: _canonical_json_bytes(
            bundle.submitted_evaluation.as_dict()
        ),
        ProductionArtifactKind.EXECUTION_EVENT_LEDGER: _canonical_json_bytes(
            [item.as_dict() for item in bundle.execution_events]
        ),
        ProductionArtifactKind.RETRY_LOG: _canonical_json_bytes(
            [
                item.as_dict()
                for item in bundle.execution_events
                if item.retry_of_event_sha256 is not None
            ]
        ),
        ProductionArtifactKind.PROTOCOL_DEVIATION_LOG: _canonical_json_bytes(
            [
                item.as_dict()
                for item in bundle.execution_events
                if item.event_status is ProductionEventStatus.FAILED
            ]
        ),
    }
    for kind, expected_payload in exact_singleton_payloads.items():
        binding = by_kind[kind]
        if payload_by_id[binding.artifact_id] != expected_payload:
            raise ValueError(f"{kind.value} bytes do not match the typed bundle")

    tree_sha256 = sha256(
        _canonical_json_bytes(
            {
                "schema_version": "production_artifact_tree_v1",
                "campaign_id": bundle.campaign_manifest.campaign_id,
                "preexecution_campaign_receipt_sha256": (
                    bundle.preexecution_campaign_receipt.content_sha256
                ),
                "artifact_root_relative_path": bundle.artifact_root_relative_path,
                "leaves": resolved_records,
            }
        )
    ).hexdigest()
    return ProductionArtifactResolutionReceipt(
        receipt_id=f"production-artifacts:{bundle.content_sha256[:24]}",
        production_bundle_sha256=bundle.content_sha256,
        resolved_artifact_tree_sha256=tree_sha256,
        resolved_artifact_count=len(resolved_records),
        resolved_total_bytes=total_bytes,
        resolved_at_utc=resolved_at_utc,
        admission_authorized=False,
    )


@dataclass(frozen=True, slots=True)
class TrustedBenchmarkAdmissionPolicy(_AdmissionRecord):
    """Out-of-band trust anchor supplied by the local admission caller.

    The preregistration fields must come from a verifier-controlled freeze
    receipt created before model execution.  A timestamp supplied inside an
    untrusted benchmark bundle is not a trust anchor.
    """

    SCHEMA_VERSION = "trusted_benchmark_admission_policy_v3"

    policy_id: str
    benchmark_id: str
    benchmark_definition_sha256: str
    admission_challenge_nonce: str
    admission_request_scope_sha256: str
    authorized_verification_bundle_sha256: str
    preexecution_freeze_receipt_sha256: str
    preexecution_campaign_receipt: PreexecutionCampaignReceipt
    benchmark_preregistered_at_utc: str
    verifier_identity: BenchmarkVerifierIdentity
    maximum_receipt_age_seconds: int
    live_workspace_bytes_verified: bool
    benchmark_artifact_bytes_verified: bool
    preexecution_definition_bytes_verified: bool
    recursive_closure_verified: bool
    admission_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _text(self.policy_id, "policy_id", identifier=True))
        object.__setattr__(
            self,
            "benchmark_id",
            _text(self.benchmark_id, "benchmark_id", identifier=True),
        )
        object.__setattr__(
            self,
            "benchmark_definition_sha256",
            _digest(self.benchmark_definition_sha256, "benchmark_definition_sha256"),
        )
        for field_name in (
            "admission_challenge_nonce",
            "admission_request_scope_sha256",
            "authorized_verification_bundle_sha256",
            "preexecution_freeze_receipt_sha256",
        ):
            object.__setattr__(
                self,
                field_name,
                _digest(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "benchmark_preregistered_at_utc",
            _timestamp(
                self.benchmark_preregistered_at_utc,
                "benchmark_preregistered_at_utc",
            ),
        )
        if not isinstance(
            self.preexecution_campaign_receipt, PreexecutionCampaignReceipt
        ):
            raise TypeError(
                "preexecution_campaign_receipt must be a "
                "PreexecutionCampaignReceipt"
            )
        preexecution = self.preexecution_campaign_receipt
        if preexecution.content_sha256 != self.preexecution_freeze_receipt_sha256:
            raise ValueError(
                "preexecution_freeze_receipt_sha256 must bind the complete receipt"
            )
        if preexecution.campaign_manifest.benchmark_id != self.benchmark_id:
            raise ValueError("preexecution receipt benchmark_id does not match policy")
        if (
            preexecution.campaign_manifest.benchmark_definition_sha256
            != self.benchmark_definition_sha256
        ):
            raise ValueError(
                "preexecution receipt benchmark definition does not match policy"
            )
        if preexecution.challenge_nonce != self.admission_challenge_nonce:
            raise ValueError("preexecution receipt challenge does not match policy")
        if preexecution.issued_at_utc != self.benchmark_preregistered_at_utc:
            raise ValueError(
                "benchmark_preregistered_at_utc must equal the preexecution issue time"
            )
        if not isinstance(self.verifier_identity, BenchmarkVerifierIdentity):
            raise TypeError("verifier_identity must be a BenchmarkVerifierIdentity")
        if (
            isinstance(self.maximum_receipt_age_seconds, bool)
            or not isinstance(self.maximum_receipt_age_seconds, int)
            or self.maximum_receipt_age_seconds <= 0
        ):
            raise ValueError("maximum_receipt_age_seconds must be a positive integer")
        for field_name in (
            "live_workspace_bytes_verified",
            "benchmark_artifact_bytes_verified",
            "preexecution_definition_bytes_verified",
            "recursive_closure_verified",
        ):
            if getattr(self, field_name) is not True:
                raise ValueError(f"trusted benchmark policy requires {field_name}")
        if self.admission_authorized is not False:
            raise ValueError("trusted benchmark policy cannot itself authorize admission")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TrustedBenchmarkAdmissionPolicy:
        data = cls._payload(payload)
        return cls(
            policy_id=data["policy_id"],
            benchmark_id=data["benchmark_id"],
            benchmark_definition_sha256=data["benchmark_definition_sha256"],
            admission_challenge_nonce=data["admission_challenge_nonce"],
            admission_request_scope_sha256=data["admission_request_scope_sha256"],
            authorized_verification_bundle_sha256=(
                data["authorized_verification_bundle_sha256"]
            ),
            preexecution_freeze_receipt_sha256=data[
                "preexecution_freeze_receipt_sha256"
            ],
            preexecution_campaign_receipt=PreexecutionCampaignReceipt.from_dict(
                data["preexecution_campaign_receipt"]
            ),
            benchmark_preregistered_at_utc=data[
                "benchmark_preregistered_at_utc"
            ],
            verifier_identity=BenchmarkVerifierIdentity.from_dict(data["verifier_identity"]),
            maximum_receipt_age_seconds=data["maximum_receipt_age_seconds"],
            live_workspace_bytes_verified=data["live_workspace_bytes_verified"],
            benchmark_artifact_bytes_verified=data[
                "benchmark_artifact_bytes_verified"
            ],
            preexecution_definition_bytes_verified=data[
                "preexecution_definition_bytes_verified"
            ],
            recursive_closure_verified=data["recursive_closure_verified"],
            admission_authorized=data["admission_authorized"],
        )


_EXPECTED_TOOL: dict[VerificationKind, str] = {
    VerificationKind.TEST: "pytest",
    VerificationKind.LINT: "ruff",
    VerificationKind.TYPECHECK: "mypy",
    VerificationKind.FROZEN_BENCHMARK: "frozen-benchmark-harness",
    VerificationKind.PERFORMANCE_RESOURCE: "performance-resource-harness",
}

_STATIC_VERIFICATION_KINDS = frozenset(
    {
        VerificationKind.TEST,
        VerificationKind.LINT,
        VerificationKind.TYPECHECK,
    }
)
_ADMISSION_VERIFICATION_KINDS = frozenset(
    {
        VerificationKind.FROZEN_BENCHMARK,
        VerificationKind.PERFORMANCE_RESOURCE,
    }
)
_EXPECTED_ADMISSION_DIMENSIONS: dict[VerificationKind, tuple[str, ...]] = {
    VerificationKind.FROZEN_BENCHMARK: ("frozen benchmark",),
    VerificationKind.PERFORMANCE_RESOURCE: (
        "latency",
        "memory",
        "throughput",
    ),
}


class ArtifactKind(str, Enum):
    SOURCE = "source"
    CONFIG = "config"
    SCHEMA = "schema"
    DATA = "data"


@dataclass(frozen=True, slots=True)
class SourceIdentity(_AdmissionRecord):
    """Exact repository/worktree state to which verification receipts bind."""

    SCHEMA_VERSION = "runtime_admission_source_identity_v1"

    repository_id: str
    source_task_id: str
    worktree_path: str
    branch_ref: str
    head_commit: str
    workspace_state_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "repository_id", _text(self.repository_id, "repository_id", identifier=True)
        )
        object.__setattr__(
            self,
            "source_task_id",
            _text(self.source_task_id, "source_task_id", identifier=True),
        )
        object.__setattr__(self, "worktree_path", _text(self.worktree_path, "worktree_path"))
        object.__setattr__(self, "branch_ref", _text(self.branch_ref, "branch_ref"))
        object.__setattr__(self, "head_commit", _commit(self.head_commit))
        object.__setattr__(
            self,
            "workspace_state_sha256",
            _digest(self.workspace_state_sha256, "workspace_state_sha256"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SourceIdentity:
        data = cls._payload(payload)
        return cls(
            repository_id=data["repository_id"],
            source_task_id=data["source_task_id"],
            worktree_path=data["worktree_path"],
            branch_ref=data["branch_ref"],
            head_commit=data["head_commit"],
            workspace_state_sha256=data["workspace_state_sha256"],
        )


@dataclass(frozen=True, slots=True)
class CapabilityBinding(_AdmissionRecord):
    SCHEMA_VERSION = "runtime_admission_capability_binding_v1"

    capability_id: str
    capability_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "capability_id", _text(self.capability_id, "capability_id", identifier=True)
        )
        object.__setattr__(
            self,
            "capability_sha256",
            _digest(self.capability_sha256, "capability_sha256"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CapabilityBinding:
        data = cls._payload(payload)
        return cls(data["capability_id"], data["capability_sha256"])


@dataclass(frozen=True, slots=True)
class SchemaBinding(_AdmissionRecord):
    SCHEMA_VERSION = "runtime_admission_schema_binding_v1"

    schema_id: str
    schema_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_id", _text(self.schema_id, "schema_id", identifier=True))
        object.__setattr__(
            self,
            "schema_sha256",
            _digest(self.schema_sha256, "schema_sha256"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SchemaBinding:
        data = cls._payload(payload)
        return cls(data["schema_id"], data["schema_sha256"])


@dataclass(frozen=True, slots=True)
class ArtifactBinding(_AdmissionRecord):
    """One immutable file in the declared transitive runtime closure."""

    SCHEMA_VERSION = "runtime_admission_artifact_binding_v1"

    artifact_id: str
    artifact_kind: ArtifactKind
    artifact_path: str
    artifact_sha256: str
    dependency_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "artifact_id",
            _text(self.artifact_id, "artifact_id", identifier=True),
        )
        object.__setattr__(self, "artifact_kind", ArtifactKind(self.artifact_kind))
        object.__setattr__(
            self,
            "artifact_path",
            _text(self.artifact_path, "artifact_path"),
        )
        object.__setattr__(
            self,
            "artifact_sha256",
            _digest(self.artifact_sha256, "artifact_sha256"),
        )
        dependencies = _text_tuple(
            self.dependency_ids,
            "dependency_ids",
            identifiers=True,
        )
        if self.artifact_id in dependencies:
            raise ValueError("an artifact cannot depend directly on itself")
        object.__setattr__(self, "dependency_ids", dependencies)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ArtifactBinding:
        data = cls._payload(payload)
        return cls(
            artifact_id=data["artifact_id"],
            artifact_kind=ArtifactKind(data["artifact_kind"]),
            artifact_path=data["artifact_path"],
            artifact_sha256=data["artifact_sha256"],
            dependency_ids=tuple(data["dependency_ids"]),
        )


def _unique_records(
    values: Iterable[_RecordT],
    *,
    record_type: type[_RecordT],
    identifier_field: str,
    field_name: str,
    allow_empty: bool = False,
) -> tuple[_RecordT, ...]:
    by_id: dict[str, _RecordT] = {}
    for value in values:
        if not isinstance(value, record_type):
            raise TypeError(f"{field_name} must contain {record_type.__name__} records")
        identifier = cast(str, getattr(value, identifier_field))
        if identifier in by_id:
            raise ValueError(f"{field_name} must contain unique {identifier_field} values")
        by_id[identifier] = value
    if not allow_empty and not by_id:
        raise ValueError(f"{field_name} must not be empty")
    return tuple(sorted(by_id.values(), key=lambda item: item.content_sha256))


@dataclass(frozen=True, slots=True)
class ArtifactClosure(_AdmissionRecord):
    """Hash-bound source/config/schema/data graph proposed for runtime use."""

    SCHEMA_VERSION = "runtime_admission_artifact_closure_v1"

    closure_id: str
    artifacts: tuple[ArtifactBinding, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "closure_id",
            _text(self.closure_id, "closure_id", identifier=True),
        )
        artifacts = _unique_records(
            self.artifacts,
            record_type=ArtifactBinding,
            identifier_field="artifact_id",
            field_name="artifacts",
        )
        paths = tuple(item.artifact_path for item in artifacts)
        if len(paths) != len(set(paths)):
            raise ValueError("artifacts must contain unique artifact_path values")
        object.__setattr__(self, "artifacts", artifacts)

    @property
    def artifact_ids(self) -> tuple[str, ...]:
        return tuple(sorted(item.artifact_id for item in self.artifacts))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ArtifactClosure:
        data = cls._payload(payload)
        return cls(
            closure_id=data["closure_id"],
            artifacts=tuple(ArtifactBinding.from_dict(item) for item in data["artifacts"]),
        )


@dataclass(frozen=True, slots=True)
class ModuleAdmissionManifest(_AdmissionRecord):
    """Exact module artifact plus its declared interface identities."""

    SCHEMA_VERSION = "runtime_admission_module_manifest_v2"

    module_id: str
    module_path: str
    source_sha256: str
    source_artifact_id: str
    capabilities: tuple[CapabilityBinding, ...]
    schemas: tuple[SchemaBinding, ...]
    authority_ceiling: AuthorityCeiling
    exclusions: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "module_id", _text(self.module_id, "module_id", identifier=True))
        object.__setattr__(self, "module_path", _text(self.module_path, "module_path"))
        object.__setattr__(self, "source_sha256", _digest(self.source_sha256, "source_sha256"))
        object.__setattr__(
            self,
            "source_artifact_id",
            _text(self.source_artifact_id, "source_artifact_id", identifier=True),
        )
        object.__setattr__(
            self,
            "capabilities",
            _unique_records(
                self.capabilities,
                record_type=CapabilityBinding,
                identifier_field="capability_id",
                field_name="capabilities",
            ),
        )
        object.__setattr__(
            self,
            "schemas",
            _unique_records(
                self.schemas,
                record_type=SchemaBinding,
                identifier_field="schema_id",
                field_name="schemas",
            ),
        )
        object.__setattr__(self, "authority_ceiling", AuthorityCeiling(self.authority_ceiling))
        object.__setattr__(
            self,
            "exclusions",
            _text_tuple(self.exclusions, "exclusions", identifiers=True),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ModuleAdmissionManifest:
        data = cls._payload(payload)
        return cls(
            module_id=data["module_id"],
            module_path=data["module_path"],
            source_sha256=data["source_sha256"],
            source_artifact_id=data["source_artifact_id"],
            capabilities=tuple(CapabilityBinding.from_dict(item) for item in data["capabilities"]),
            schemas=tuple(SchemaBinding.from_dict(item) for item in data["schemas"]),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            exclusions=tuple(data["exclusions"]),
        )


@dataclass(frozen=True, slots=True)
class VerificationReceipt(_AdmissionRecord):
    """One externally produced, exact-scope verification receipt.

    For ``FROZEN_BENCHMARK``, ``evidence_input_sha256`` is the canonical
    ``FrozenBenchmarkVerificationBundle.content_sha256`` and ``output_sha256``
    is the locally recomputed canonical
    ``FrozenBenchmarkEvaluation.content_sha256``.  Neither field means pretty
    JSON, stdout, or a wrapper-envelope byte hash.
    """

    SCHEMA_VERSION = "runtime_admission_verification_receipt_v2"

    receipt_id: str
    verification_kind: VerificationKind
    verification_status: VerificationStatus
    tool_id: str
    tool_version: str
    command: str
    command_sha256: str
    evidence_set_id: str
    evidence_input_sha256: str
    evidence_dimensions: tuple[str, ...]
    observed_at_utc: str
    source_identity_sha256: str
    module_manifest_sha256s: tuple[str, ...]
    covered_module_ids: tuple[str, ...]
    covered_capability_ids: tuple[str, ...]
    covered_schema_ids: tuple[str, ...]
    artifact_closure_sha256: str | None
    covered_artifact_ids: tuple[str, ...]
    exit_code: int
    output_sha256: str
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "receipt_id", _text(self.receipt_id, "receipt_id", identifier=True)
        )
        kind = VerificationKind(self.verification_kind)
        status = VerificationStatus(self.verification_status)
        object.__setattr__(self, "verification_kind", kind)
        object.__setattr__(self, "verification_status", status)
        tool_id = _text(self.tool_id, "tool_id", identifier=True)
        if tool_id != _EXPECTED_TOOL[kind]:
            raise ValueError(f"{kind.value} receipts must be produced by {_EXPECTED_TOOL[kind]}")
        object.__setattr__(self, "tool_id", tool_id)
        object.__setattr__(self, "tool_version", _text(self.tool_version, "tool_version"))
        command = _text(self.command, "command")
        object.__setattr__(self, "command", command)
        command_sha256 = _digest(self.command_sha256, "command_sha256")
        if sha256(command.encode("utf-8")).hexdigest() != command_sha256:
            raise ValueError("command_sha256 does not match command bytes")
        object.__setattr__(self, "command_sha256", command_sha256)
        object.__setattr__(
            self,
            "evidence_set_id",
            _text(self.evidence_set_id, "evidence_set_id", identifier=True),
        )
        object.__setattr__(
            self,
            "evidence_input_sha256",
            _digest(self.evidence_input_sha256, "evidence_input_sha256"),
        )
        object.__setattr__(
            self,
            "evidence_dimensions",
            _text_tuple(
                self.evidence_dimensions,
                "evidence_dimensions",
                allow_empty=False,
                identifiers=True,
            ),
        )
        object.__setattr__(
            self, "observed_at_utc", _timestamp(self.observed_at_utc, "observed_at_utc")
        )
        object.__setattr__(
            self,
            "source_identity_sha256",
            _digest(self.source_identity_sha256, "source_identity_sha256"),
        )
        manifest_hashes = tuple(
            _digest(value, "module_manifest_sha256s") for value in self.module_manifest_sha256s
        )
        if len(manifest_hashes) != len(set(manifest_hashes)):
            raise ValueError("module_manifest_sha256s must contain unique values")
        object.__setattr__(
            self,
            "module_manifest_sha256s",
            tuple(sorted(manifest_hashes)),
        )
        object.__setattr__(
            self,
            "covered_module_ids",
            _text_tuple(self.covered_module_ids, "covered_module_ids", identifiers=True),
        )
        object.__setattr__(
            self,
            "covered_capability_ids",
            _text_tuple(self.covered_capability_ids, "covered_capability_ids", identifiers=True),
        )
        object.__setattr__(
            self,
            "covered_schema_ids",
            _text_tuple(self.covered_schema_ids, "covered_schema_ids", identifiers=True),
        )
        object.__setattr__(
            self,
            "artifact_closure_sha256",
            _optional_digest(
                self.artifact_closure_sha256,
                "artifact_closure_sha256",
            ),
        )
        object.__setattr__(
            self,
            "covered_artifact_ids",
            _text_tuple(
                self.covered_artifact_ids,
                "covered_artifact_ids",
                identifiers=True,
            ),
        )
        if isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int):
            raise TypeError("exit_code must be an integer")
        object.__setattr__(self, "output_sha256", _digest(self.output_sha256, "output_sha256"))
        blockers = _text_tuple(self.blockers, "blockers")
        if status is VerificationStatus.PASS and (self.exit_code != 0 or blockers):
            raise ValueError("PASS receipts require exit_code 0 and no blockers")
        if status is VerificationStatus.FAIL and self.exit_code == 0 and not blockers:
            raise ValueError("FAIL receipts require a nonzero exit or an explicit blocker")
        object.__setattr__(self, "blockers", blockers)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> VerificationReceipt:
        data = cls._payload(payload)
        return cls(
            receipt_id=data["receipt_id"],
            verification_kind=VerificationKind(data["verification_kind"]),
            verification_status=VerificationStatus(data["verification_status"]),
            tool_id=data["tool_id"],
            tool_version=data["tool_version"],
            command=data["command"],
            command_sha256=data["command_sha256"],
            evidence_set_id=data["evidence_set_id"],
            evidence_input_sha256=data["evidence_input_sha256"],
            evidence_dimensions=tuple(data["evidence_dimensions"]),
            observed_at_utc=data["observed_at_utc"],
            source_identity_sha256=data["source_identity_sha256"],
            module_manifest_sha256s=tuple(data["module_manifest_sha256s"]),
            covered_module_ids=tuple(data["covered_module_ids"]),
            covered_capability_ids=tuple(data["covered_capability_ids"]),
            covered_schema_ids=tuple(data["covered_schema_ids"]),
            artifact_closure_sha256=data["artifact_closure_sha256"],
            covered_artifact_ids=tuple(data["covered_artifact_ids"]),
            exit_code=data["exit_code"],
            output_sha256=data["output_sha256"],
            blockers=tuple(data["blockers"]),
        )


@dataclass(frozen=True, slots=True)
class AdmissionRequest(_AdmissionRecord):
    """Exact, versioned set of modules proposed for all-or-nothing admission."""

    SCHEMA_VERSION = "runtime_admission_request_v3"

    request_id: str
    source_identity: SourceIdentity
    module_manifests: tuple[ModuleAdmissionManifest, ...]
    artifact_closure: ArtifactClosure | None
    verification_receipts: tuple[VerificationReceipt, ...]
    required_verification_kinds: tuple[VerificationKind, ...]
    required_exclusions: tuple[str, ...]
    maximum_authority_ceiling: AuthorityCeiling
    frozen_benchmark_id: str
    frozen_benchmark_sha256: str
    benchmark_challenge_nonce: str
    frozen_benchmark_verification_bundle: (
        FrozenBenchmarkVerificationBundle
        | ProductionBenchmarkVerificationBundle
        | None
    )
    frozen_benchmark_evaluation: FrozenBenchmarkEvaluation | None
    required_benchmark_verifier_identity_sha256: str
    performance_resource_policy_id: str
    performance_resource_policy_sha256: str
    as_of_utc: str
    max_receipt_age_seconds: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "request_id", _text(self.request_id, "request_id", identifier=True)
        )
        if not isinstance(self.source_identity, SourceIdentity):
            raise TypeError("source_identity must be a SourceIdentity")
        manifests = _unique_records(
            self.module_manifests,
            record_type=ModuleAdmissionManifest,
            identifier_field="module_id",
            field_name="module_manifests",
        )
        module_paths = tuple(item.module_path for item in manifests)
        if len(module_paths) != len(set(module_paths)):
            raise ValueError("module_manifests must contain unique module_path values")
        source_artifact_ids = tuple(item.source_artifact_id for item in manifests)
        if len(source_artifact_ids) != len(set(source_artifact_ids)):
            raise ValueError("module_manifests must contain unique source_artifact_id values")
        capability_ids = tuple(
            capability.capability_id
            for manifest in manifests
            for capability in manifest.capabilities
        )
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("module_manifests must contain globally unique capability_id values")
        # Schema contracts are intentionally shareable across modules.  Cross-
        # consumer hash consistency is adjudicated by the evaluator so one bad
        # binding blocks every consumer instead of failing during construction.
        object.__setattr__(self, "module_manifests", manifests)
        if self.artifact_closure is not None and not isinstance(
            self.artifact_closure, ArtifactClosure
        ):
            raise TypeError("artifact_closure must be an ArtifactClosure or None")

        receipts = _unique_records(
            self.verification_receipts,
            record_type=VerificationReceipt,
            identifier_field="receipt_id",
            field_name="verification_receipts",
            allow_empty=True,
        )
        object.__setattr__(self, "verification_receipts", receipts)
        declared_required = tuple(
            VerificationKind(value) for value in self.required_verification_kinds
        )
        if len(declared_required) != len(set(declared_required)):
            raise ValueError("required_verification_kinds must contain unique values")
        required = tuple(sorted(declared_required, key=lambda item: item.value))
        if set(required) != set(VerificationKind):
            raise ValueError(
                "required_verification_kinds must require test, lint, typecheck, "
                "frozen_benchmark, and performance_resource"
            )
        object.__setattr__(self, "required_verification_kinds", required)
        object.__setattr__(
            self,
            "required_exclusions",
            _text_tuple(self.required_exclusions, "required_exclusions", identifiers=True),
        )
        ceiling = AuthorityCeiling(self.maximum_authority_ceiling)
        if not ceiling.is_no_stronger_than(AuthorityCeiling.STRUCTURAL_ONLY):
            raise ValueError("runtime admission cannot exceed structural_only authority")
        object.__setattr__(self, "maximum_authority_ceiling", ceiling)
        object.__setattr__(
            self,
            "frozen_benchmark_id",
            _text(self.frozen_benchmark_id, "frozen_benchmark_id", identifier=True),
        )
        object.__setattr__(
            self,
            "frozen_benchmark_sha256",
            _digest(self.frozen_benchmark_sha256, "frozen_benchmark_sha256"),
        )
        object.__setattr__(
            self,
            "benchmark_challenge_nonce",
            _digest(self.benchmark_challenge_nonce, "benchmark_challenge_nonce"),
        )
        if self.frozen_benchmark_verification_bundle is not None and not isinstance(
            self.frozen_benchmark_verification_bundle,
            (
                FrozenBenchmarkVerificationBundle,
                ProductionBenchmarkVerificationBundle,
            ),
        ):
            raise TypeError(
                "frozen_benchmark_verification_bundle must be a "
                "FrozenBenchmarkVerificationBundle, "
                "ProductionBenchmarkVerificationBundle, or None"
            )
        if self.frozen_benchmark_evaluation is not None and not isinstance(
            self.frozen_benchmark_evaluation, FrozenBenchmarkEvaluation
        ):
            raise TypeError(
                "frozen_benchmark_evaluation must be a FrozenBenchmarkEvaluation or None"
            )
        object.__setattr__(
            self,
            "required_benchmark_verifier_identity_sha256",
            _digest(
                self.required_benchmark_verifier_identity_sha256,
                "required_benchmark_verifier_identity_sha256",
            ),
        )
        object.__setattr__(
            self,
            "performance_resource_policy_id",
            _text(
                self.performance_resource_policy_id,
                "performance_resource_policy_id",
                identifier=True,
            ),
        )
        object.__setattr__(
            self,
            "performance_resource_policy_sha256",
            _digest(
                self.performance_resource_policy_sha256,
                "performance_resource_policy_sha256",
            ),
        )
        object.__setattr__(self, "as_of_utc", _timestamp(self.as_of_utc, "as_of_utc"))
        if (
            isinstance(self.max_receipt_age_seconds, bool)
            or not isinstance(self.max_receipt_age_seconds, int)
            or self.max_receipt_age_seconds <= 0
        ):
            raise ValueError("max_receipt_age_seconds must be a positive integer")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> AdmissionRequest:
        data = cls._payload(payload)
        return cls(
            request_id=data["request_id"],
            source_identity=SourceIdentity.from_dict(data["source_identity"]),
            module_manifests=tuple(
                ModuleAdmissionManifest.from_dict(item) for item in data["module_manifests"]
            ),
            artifact_closure=(
                ArtifactClosure.from_dict(data["artifact_closure"])
                if data["artifact_closure"] is not None
                else None
            ),
            verification_receipts=tuple(
                VerificationReceipt.from_dict(item) for item in data["verification_receipts"]
            ),
            required_verification_kinds=tuple(
                VerificationKind(item) for item in data["required_verification_kinds"]
            ),
            required_exclusions=tuple(data["required_exclusions"]),
            maximum_authority_ceiling=AuthorityCeiling(data["maximum_authority_ceiling"]),
            frozen_benchmark_id=data["frozen_benchmark_id"],
            frozen_benchmark_sha256=data["frozen_benchmark_sha256"],
            benchmark_challenge_nonce=data["benchmark_challenge_nonce"],
            frozen_benchmark_verification_bundle=(
                (
                    ProductionBenchmarkVerificationBundle.from_dict(
                        data["frozen_benchmark_verification_bundle"]
                    )
                    if data["frozen_benchmark_verification_bundle"].get(
                        "schema_version"
                    )
                    == ProductionBenchmarkVerificationBundle.SCHEMA_VERSION
                    else FrozenBenchmarkVerificationBundle.from_dict(
                        data["frozen_benchmark_verification_bundle"]
                    )
                )
                if data["frozen_benchmark_verification_bundle"] is not None
                else None
            ),
            frozen_benchmark_evaluation=(
                FrozenBenchmarkEvaluation.from_dict(data["frozen_benchmark_evaluation"])
                if data["frozen_benchmark_evaluation"] is not None
                else None
            ),
            required_benchmark_verifier_identity_sha256=(
                data["required_benchmark_verifier_identity_sha256"]
            ),
            performance_resource_policy_id=data["performance_resource_policy_id"],
            performance_resource_policy_sha256=data["performance_resource_policy_sha256"],
            as_of_utc=data["as_of_utc"],
            max_receipt_age_seconds=data["max_receipt_age_seconds"],
        )


@dataclass(frozen=True, slots=True)
class AdmissionDecision(_AdmissionRecord):
    """Deterministic decision; non-runtime authorities are permanently false."""

    SCHEMA_VERSION = "runtime_admission_decision_v3"

    decision_id: str
    request_sha256: str
    status: AdmissionStatus
    admitted_module_ids: tuple[str, ...]
    pre_admission_verified_module_ids: tuple[str, ...]
    considered_receipt_ids: tuple[str, ...]
    blockers: tuple[str, ...]
    evaluated_at_utc: str
    verified_benchmark_evaluation_sha256: str | None
    benchmark_verifier_identity_sha256: str | None
    trusted_benchmark_policy_sha256: str | None
    authority_ceiling: AuthorityCeiling
    exclusions: tuple[str, ...]
    benchmark_execution_authorized: bool
    empirical_authority: bool
    formula_generation_authorized: bool
    physical_execution_authorized: bool
    compounding_authority: bool
    sensory_authority: bool
    liking_authority: bool
    safety_authority: bool
    stability_authority: bool
    purchase_authority: bool
    release_authority: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "decision_id", _text(self.decision_id, "decision_id", identifier=True)
        )
        object.__setattr__(self, "request_sha256", _digest(self.request_sha256, "request_sha256"))
        status = AdmissionStatus(self.status)
        object.__setattr__(self, "status", status)
        admitted = _text_tuple(self.admitted_module_ids, "admitted_module_ids", identifiers=True)
        pre_verified = _text_tuple(
            self.pre_admission_verified_module_ids,
            "pre_admission_verified_module_ids",
            identifiers=True,
        )
        receipts = _text_tuple(
            self.considered_receipt_ids, "considered_receipt_ids", identifiers=True
        )
        blockers = _text_tuple(self.blockers, "blockers")
        if status is AdmissionStatus.ADMITTED and blockers:
            raise ValueError("ADMITTED decisions cannot contain blockers")
        if status is AdmissionStatus.ADMITTED and not admitted:
            raise ValueError("ADMITTED decisions must name admitted modules")
        if status is AdmissionStatus.ADMITTED and pre_verified != admitted:
            raise ValueError("ADMITTED decisions require the same statically verified modules")
        if status is AdmissionStatus.PRE_ADMISSION_VERIFIED and admitted:
            raise ValueError("PRE_ADMISSION_VERIFIED cannot admit modules")
        if status is AdmissionStatus.PRE_ADMISSION_VERIFIED and not pre_verified:
            raise ValueError("PRE_ADMISSION_VERIFIED must name statically verified modules")
        if status is AdmissionStatus.PRE_ADMISSION_VERIFIED and not blockers:
            raise ValueError("PRE_ADMISSION_VERIFIED must name admission blockers")
        if status is AdmissionStatus.HOLD and (admitted or pre_verified):
            raise ValueError("HOLD decisions cannot verify or admit modules")
        if status is AdmissionStatus.HOLD and not blockers:
            raise ValueError("HOLD decisions must name at least one blocker")
        object.__setattr__(self, "admitted_module_ids", admitted)
        object.__setattr__(
            self,
            "pre_admission_verified_module_ids",
            pre_verified,
        )
        object.__setattr__(self, "considered_receipt_ids", receipts)
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(
            self, "evaluated_at_utc", _timestamp(self.evaluated_at_utc, "evaluated_at_utc")
        )
        verified_evaluation = _optional_digest(
            self.verified_benchmark_evaluation_sha256,
            "verified_benchmark_evaluation_sha256",
        )
        verifier_identity = _optional_digest(
            self.benchmark_verifier_identity_sha256,
            "benchmark_verifier_identity_sha256",
        )
        trusted_policy = _optional_digest(
            self.trusted_benchmark_policy_sha256,
            "trusted_benchmark_policy_sha256",
        )
        if len(
            {
                verified_evaluation is None,
                verifier_identity is None,
                trusted_policy is None,
            }
        ) != 1:
            raise ValueError(
                "verified benchmark evaluation, verifier identity, and trusted policy "
                "must be present together"
            )
        if status is AdmissionStatus.ADMITTED and verified_evaluation is None:
            raise ValueError("ADMITTED decisions require a verified benchmark evaluation")
        object.__setattr__(
            self, "verified_benchmark_evaluation_sha256", verified_evaluation
        )
        object.__setattr__(
            self, "benchmark_verifier_identity_sha256", verifier_identity
        )
        object.__setattr__(self, "trusted_benchmark_policy_sha256", trusted_policy)
        ceiling = AuthorityCeiling(self.authority_ceiling)
        if not ceiling.is_no_stronger_than(AuthorityCeiling.STRUCTURAL_ONLY):
            raise ValueError("admission decisions cannot exceed structural_only authority")
        object.__setattr__(self, "authority_ceiling", ceiling)
        exclusions = _text_tuple(self.exclusions, "exclusions", identifiers=True)
        missing = sorted(set(MANDATORY_AUTHORITY_EXCLUSIONS) - set(exclusions))
        if missing:
            raise ValueError(f"admission decision is missing mandatory exclusions: {missing!r}")
        object.__setattr__(self, "exclusions", exclusions)
        authority_fields = (
            "benchmark_execution_authorized",
            "empirical_authority",
            "formula_generation_authorized",
            "physical_execution_authorized",
            "compounding_authority",
            "sensory_authority",
            "liking_authority",
            "safety_authority",
            "stability_authority",
            "purchase_authority",
            "release_authority",
        )
        for field_name in authority_fields:
            value = getattr(self, field_name)
            if not isinstance(value, bool):
                raise TypeError(f"{field_name} must be bool")
            if value:
                raise ValueError(f"{field_name} is outside runtime admission authority")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> AdmissionDecision:
        data = cls._payload(payload)
        return cls(
            decision_id=data["decision_id"],
            request_sha256=data["request_sha256"],
            status=AdmissionStatus(data["status"]),
            admitted_module_ids=tuple(data["admitted_module_ids"]),
            pre_admission_verified_module_ids=tuple(data["pre_admission_verified_module_ids"]),
            considered_receipt_ids=tuple(data["considered_receipt_ids"]),
            blockers=tuple(data["blockers"]),
            evaluated_at_utc=data["evaluated_at_utc"],
            verified_benchmark_evaluation_sha256=(
                data["verified_benchmark_evaluation_sha256"]
            ),
            benchmark_verifier_identity_sha256=(
                data["benchmark_verifier_identity_sha256"]
            ),
            trusted_benchmark_policy_sha256=data["trusted_benchmark_policy_sha256"],
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            exclusions=tuple(data["exclusions"]),
            benchmark_execution_authorized=data["benchmark_execution_authorized"],
            empirical_authority=data["empirical_authority"],
            formula_generation_authorized=data["formula_generation_authorized"],
            physical_execution_authorized=data["physical_execution_authorized"],
            compounding_authority=data["compounding_authority"],
            sensory_authority=data["sensory_authority"],
            liking_authority=data["liking_authority"],
            safety_authority=data["safety_authority"],
            stability_authority=data["stability_authority"],
            purchase_authority=data["purchase_authority"],
            release_authority=data["release_authority"],
        )


def _artifact_closure_blockers(request: AdmissionRequest) -> set[str]:
    closure = request.artifact_closure
    if closure is None:
        return {"missing_artifact_closure"}

    blockers: set[str] = set()
    by_id = {item.artifact_id: item for item in closure.artifacts}
    present_kinds = {item.artifact_kind for item in closure.artifacts}
    blockers.update(
        f"closure_missing_artifact_kind:{kind.value}"
        for kind in ArtifactKind
        if kind not in present_kinds
    )

    for artifact in closure.artifacts:
        blockers.update(
            f"closure_missing_dependency:{dependency_id}"
            for dependency_id in artifact.dependency_ids
            if dependency_id not in by_id
        )

    source_roots: list[str] = []
    for manifest in request.module_manifests:
        source_roots.append(manifest.source_artifact_id)
        source_artifact = by_id.get(manifest.source_artifact_id)
        if source_artifact is None:
            blockers.add(f"closure_missing_module_source:{manifest.module_id}")
        else:
            if source_artifact.artifact_kind is not ArtifactKind.SOURCE:
                blockers.add(f"closure_module_source_kind_mismatch:{manifest.module_id}")
            if source_artifact.artifact_path != manifest.module_path:
                blockers.add(f"closure_module_source_path_mismatch:{manifest.module_id}")
            if source_artifact.artifact_sha256 != manifest.source_sha256:
                blockers.add(f"closure_module_source_hash_mismatch:{manifest.module_id}")

        for schema in manifest.schemas:
            schema_artifact = by_id.get(schema.schema_id)
            if schema_artifact is None:
                blockers.add(f"closure_missing_schema:{schema.schema_id}")
            else:
                if schema_artifact.artifact_kind is not ArtifactKind.SCHEMA:
                    blockers.add(
                        f"closure_schema_kind_mismatch:{schema.schema_id}:"
                        f"consumer:{manifest.module_id}"
                    )
                if schema_artifact.artifact_sha256 != schema.schema_sha256:
                    blockers.add(
                        f"closure_schema_hash_mismatch:{schema.schema_id}:"
                        f"consumer:{manifest.module_id}"
                    )

    reachable: set[str] = set()
    pending = list(source_roots)
    while pending:
        artifact_id = pending.pop()
        if artifact_id in reachable or artifact_id not in by_id:
            continue
        reachable.add(artifact_id)
        pending.extend(by_id[artifact_id].dependency_ids)
    blockers.update(
        f"closure_unreachable_artifact:{artifact_id}" for artifact_id in set(by_id) - reachable
    )

    states: dict[str, int] = {}

    def visit(artifact_id: str) -> None:
        state = states.get(artifact_id, 0)
        if state == 1:
            blockers.add(f"closure_cycle_detected:{artifact_id}")
            return
        if state == 2:
            return
        states[artifact_id] = 1
        for dependency_id in by_id[artifact_id].dependency_ids:
            if dependency_id in by_id:
                visit(dependency_id)
        states[artifact_id] = 2

    for artifact_id in by_id:
        visit(artifact_id)
    return blockers


def benchmark_request_scope_sha256(request: AdmissionRequest) -> str:
    """Hash the pre-benchmark request scope without creating a hash cycle."""

    if not isinstance(request, AdmissionRequest):
        raise TypeError("request must be an AdmissionRequest")
    expected_manifest_hashes = tuple(
        sorted(item.content_sha256 for item in request.module_manifests)
    )
    expected_module_ids = tuple(sorted(item.module_id for item in request.module_manifests))
    expected_capability_ids = tuple(
        sorted(
            capability.capability_id
            for manifest in request.module_manifests
            for capability in manifest.capabilities
        )
    )
    expected_schema_ids = tuple(
        sorted(
            {
                schema.schema_id
                for manifest in request.module_manifests
                for schema in manifest.schemas
            }
        )
    )
    closure = request.artifact_closure
    expected_closure_sha256 = closure.content_sha256 if closure is not None else None
    expected_artifact_ids = closure.artifact_ids if closure is not None else ()

    return sha256(
        _canonical_json_bytes(
            {
                "schema_version": "runtime_admission_benchmark_scope_v1",
                "request_id": request.request_id,
                "source_identity_sha256": request.source_identity.content_sha256,
                "workspace_state_sha256": request.source_identity.workspace_state_sha256,
                "module_manifest_sha256s": expected_manifest_hashes,
                "covered_module_ids": expected_module_ids,
                "covered_capability_ids": expected_capability_ids,
                "covered_schema_ids": expected_schema_ids,
                "artifact_closure_sha256": expected_closure_sha256,
                "covered_artifact_ids": expected_artifact_ids,
                "benchmark_id": request.frozen_benchmark_id,
                "benchmark_definition_sha256": request.frozen_benchmark_sha256,
                "benchmark_challenge_nonce": request.benchmark_challenge_nonce,
                "required_benchmark_verifier_identity_sha256": (
                    request.required_benchmark_verifier_identity_sha256
                ),
            }
        )
    ).hexdigest()


def _evaluate_benchmark_result_bridge(
    request: AdmissionRequest,
    *,
    trusted_policy: TrustedBenchmarkAdmissionPolicy | None,
    trusted_clock_supplied: bool,
    frozen_benchmark_receipt: VerificationReceipt | None,
    expected_manifest_hashes: tuple[str, ...],
    expected_module_ids: tuple[str, ...],
    expected_capability_ids: tuple[str, ...],
    expected_schema_ids: tuple[str, ...],
    expected_closure_sha256: str | None,
    expected_artifact_ids: tuple[str, ...],
    as_of: datetime,
) -> tuple[str | None, str | None, set[str], set[str]]:
    """Bind one typed benchmark evaluation to one exact verifier receipt.

    Integrity blockers mean the packet is not trusted at all.  Outcome blockers
    mean the packet is exact and traceable but its derived benchmark result is
    not PASS.  The distinction lets a verified failing result retain provenance
    without granting runtime admission.
    """

    submitted_evaluation = request.frozen_benchmark_evaluation
    bundle = request.frozen_benchmark_verification_bundle
    production_bundle = (
        bundle if isinstance(bundle, ProductionBenchmarkVerificationBundle) else None
    )
    semantic_bundle = (
        production_bundle.semantic_bundle
        if production_bundle is not None
        else bundle
    )
    if submitted_evaluation is None and bundle is None:
        return None, None, {TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER}, set()

    integrity_blockers: set[str] = set()
    outcome_blockers: set[str] = set()

    if not trusted_clock_supplied:
        integrity_blockers.add("benchmark_result_trusted_clock_missing")
    if trusted_policy is None:
        integrity_blockers.add("benchmark_result_verifier_policy_untrusted")
    if bundle is None:
        integrity_blockers.add("benchmark_evidence_bundle_missing")
    if submitted_evaluation is None:
        integrity_blockers.add("benchmark_evaluation_missing")

    recomputed_evaluation: FrozenBenchmarkEvaluation | None = None
    if bundle is not None:
        if production_bundle is None:
            integrity_blockers.add("legacy_benchmark_case_contract_nonadmissible")
        if semantic_bundle is None:
            integrity_blockers.add("benchmark_evidence_bundle_invalid")
        else:
            try:
                validate_corpus_coverage(semantic_bundle.corpus)
            except (TypeError, ValueError):
                integrity_blockers.add("production_benchmark_corpus_coverage_invalid")
            if len(semantic_bundle.corpus.cases) < MINIMUM_PRODUCTION_BENCHMARK_CASES:
                integrity_blockers.add("production_benchmark_case_minimum_not_met")
            if len(semantic_bundle.corpus.anonymized_arms) < MINIMUM_PRODUCTION_BENCHMARK_ARMS:
                integrity_blockers.add("production_benchmark_arm_minimum_not_met")
            generation_groups = {
                (cell.case_id, cell.arm_id, cell.seed, cell.repeat_index)
                for cell in semantic_bundle.execution_matrix.cells
            }
            if len(generation_groups) < MINIMUM_PRODUCTION_GENERATION_GROUPS:
                integrity_blockers.add("production_generation_minimum_not_met")
            try:
                recomputed_evaluation = semantic_bundle.recompute()
            except (TypeError, ValueError):
                integrity_blockers.add("benchmark_evidence_bundle_invalid")

    production_resolution: ProductionArtifactResolutionReceipt | None = None
    if production_bundle is not None:
        try:
            production_resolution = verify_production_artifact_bytes(
                production_bundle,
                workspace_root=Path(request.source_identity.worktree_path),
                resolved_at_utc=as_of.isoformat().replace("+00:00", "Z"),
            )
        except (OSError, TypeError, ValueError):
            integrity_blockers.add("production_benchmark_artifact_reverification_failed")
        else:
            postexecution = production_bundle.postexecution_campaign_receipt
            if (
                production_resolution.resolved_artifact_tree_sha256
                != postexecution.resolved_artifact_tree_sha256
                or production_resolution.resolved_artifact_count
                != postexecution.resolved_artifact_count
                or production_resolution.resolved_total_bytes
                != postexecution.resolved_total_bytes
            ):
                integrity_blockers.add("production_benchmark_artifact_tree_drift")
        if (
            submitted_evaluation is not None
            and production_bundle.submitted_evaluation.content_sha256
            != submitted_evaluation.content_sha256
        ):
            integrity_blockers.add("production_submitted_evaluation_mismatch")

    if recomputed_evaluation is not None and submitted_evaluation is not None:
        if recomputed_evaluation.content_sha256 != submitted_evaluation.content_sha256:
            integrity_blockers.add("benchmark_evaluation_hash_mismatch")

    evaluation = recomputed_evaluation or submitted_evaluation
    if evaluation is None:
        integrity_blockers.add(TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER)
        return None, None, integrity_blockers, outcome_blockers

    expected_request_scope_sha256 = benchmark_request_scope_sha256(request)

    if evaluation.benchmark_id != request.frozen_benchmark_id:
        integrity_blockers.add("benchmark_result_id_mismatch")
    if evaluation.benchmark_definition_sha256 != request.frozen_benchmark_sha256:
        integrity_blockers.add("benchmark_definition_hash_mismatch")
    if evaluation.source_identity_sha256 != request.source_identity.content_sha256:
        integrity_blockers.add("benchmark_result_source_identity_mismatch")
    if evaluation.workspace_state_sha256 != request.source_identity.workspace_state_sha256:
        integrity_blockers.add("benchmark_result_workspace_state_mismatch")
    if evaluation.admission_challenge_nonce != request.benchmark_challenge_nonce:
        integrity_blockers.add("benchmark_result_challenge_mismatch")
    if evaluation.admission_request_scope_sha256 != expected_request_scope_sha256:
        integrity_blockers.add("benchmark_result_request_binding_mismatch")
    if evaluation.module_manifest_sha256s != expected_manifest_hashes:
        integrity_blockers.add("benchmark_result_manifest_hash_mismatch")
    if evaluation.covered_module_ids != expected_module_ids:
        integrity_blockers.add("benchmark_result_module_coverage_mismatch")
    if evaluation.covered_capability_ids != expected_capability_ids:
        integrity_blockers.add("benchmark_result_capability_coverage_mismatch")
    if evaluation.covered_schema_ids != expected_schema_ids:
        integrity_blockers.add("benchmark_result_schema_coverage_mismatch")
    if evaluation.artifact_closure_sha256 != expected_closure_sha256:
        integrity_blockers.add("benchmark_result_artifact_closure_hash_mismatch")
    if evaluation.covered_artifact_ids != expected_artifact_ids:
        integrity_blockers.add("benchmark_result_artifact_coverage_mismatch")

    verifier_identity_sha256 = evaluation.verifier_identity.content_sha256
    if trusted_policy is not None:
        trusted_verifier_sha256 = trusted_policy.verifier_identity.content_sha256
        preexecution_receipt = trusted_policy.preexecution_campaign_receipt
        preexecution_manifest = preexecution_receipt.campaign_manifest
        if request.frozen_benchmark_id != trusted_policy.benchmark_id:
            integrity_blockers.add("benchmark_result_policy_id_mismatch")
        if (
            request.frozen_benchmark_sha256
            != trusted_policy.benchmark_definition_sha256
        ):
            integrity_blockers.add("benchmark_result_policy_definition_mismatch")
        if request.benchmark_challenge_nonce != trusted_policy.admission_challenge_nonce:
            integrity_blockers.add("benchmark_result_policy_challenge_mismatch")
        if (
            expected_request_scope_sha256
            != trusted_policy.admission_request_scope_sha256
        ):
            integrity_blockers.add("benchmark_result_policy_scope_mismatch")
        if (
            bundle is None
            or bundle.content_sha256
            != trusted_policy.authorized_verification_bundle_sha256
        ):
            integrity_blockers.add("benchmark_result_policy_bundle_mismatch")
        if (
            request.required_benchmark_verifier_identity_sha256
            != trusted_verifier_sha256
        ):
            integrity_blockers.add("benchmark_result_verifier_policy_pin_mismatch")
        if verifier_identity_sha256 != trusted_verifier_sha256:
            integrity_blockers.add("benchmark_result_verifier_identity_mismatch")
        if (
            semantic_bundle is not None
            and semantic_bundle.verifier_identity != trusted_policy.verifier_identity
        ):
            integrity_blockers.add("benchmark_result_verifier_implementation_mismatch")
        if (
            preexecution_manifest.source_identity_sha256
            != request.source_identity.content_sha256
        ):
            integrity_blockers.add("preexecution_campaign_source_identity_mismatch")
        if (
            preexecution_manifest.workspace_state_sha256
            != request.source_identity.workspace_state_sha256
        ):
            integrity_blockers.add("preexecution_campaign_workspace_state_mismatch")
        if semantic_bundle is not None:
            if preexecution_manifest.case_ids != tuple(
                item.case_id for item in semantic_bundle.corpus.cases
            ):
                integrity_blockers.add(
                    "preexecution_campaign_case_coverage_mismatch"
                )
            if preexecution_manifest.arm_ids != tuple(
                item.arm_id for item in semantic_bundle.corpus.anonymized_arms
            ):
                integrity_blockers.add(
                    "preexecution_campaign_arm_coverage_mismatch"
                )
        if production_bundle is not None:
            if (
                production_bundle.preexecution_campaign_receipt.content_sha256
                != preexecution_receipt.content_sha256
            ):
                integrity_blockers.add(
                    "production_preexecution_campaign_receipt_mismatch"
                )
            if production_bundle.campaign_manifest != preexecution_manifest:
                integrity_blockers.add("production_campaign_manifest_mismatch")
        try:
            live_resolution = verify_frozen_campaign_artifact_bytes(
                preexecution_manifest,
                workspace_root=Path(request.source_identity.worktree_path),
                resolved_at_utc=as_of.isoformat().replace("+00:00", "Z"),
            )
        except (OSError, TypeError, ValueError):
            integrity_blockers.add(
                "preexecution_campaign_artifact_reverification_failed"
            )
        else:
            frozen_resolution = preexecution_receipt.artifact_resolution
            if (
                live_resolution.resolved_artifact_tree_sha256
                != frozen_resolution.resolved_artifact_tree_sha256
                or live_resolution.resolved_artifact_count
                != frozen_resolution.resolved_artifact_count
                or live_resolution.resolved_total_bytes
                != frozen_resolution.resolved_total_bytes
            ):
                integrity_blockers.add(
                    "preexecution_campaign_artifact_tree_drift"
                )
    elif verifier_identity_sha256 != request.required_benchmark_verifier_identity_sha256:
        integrity_blockers.add("benchmark_result_verifier_identity_mismatch")
    if (
        evaluation.verifier_identity.independence_key
        == evaluation.producer_independence_key
        or evaluation.verifier_identity.independence_key
        in evaluation.scorer_independence_keys
    ):
        integrity_blockers.add("benchmark_result_verifier_not_independent")

    evaluated = _parsed_timestamp(evaluation.evaluated_at_utc)
    if trusted_policy is not None and semantic_bundle is not None:
        preregistered = _parsed_timestamp(
            trusted_policy.benchmark_preregistered_at_utc
        )
        run_started_times = tuple(
            _parsed_timestamp(receipt.started_at_utc)
            for receipt in semantic_bundle.run_receipts
        )
        if not run_started_times:
            integrity_blockers.add("benchmark_result_run_receipts_missing")
        elif preregistered >= min(run_started_times):
            integrity_blockers.add(
                "benchmark_definition_not_preregistered_before_execution"
            )
    allowed_age_seconds = request.max_receipt_age_seconds
    if trusted_policy is not None:
        allowed_age_seconds = min(
            allowed_age_seconds,
            trusted_policy.maximum_receipt_age_seconds,
        )
    evaluation_age_seconds = (as_of - evaluated).total_seconds()
    if evaluation_age_seconds < 0:
        integrity_blockers.add("benchmark_result_future")
    elif evaluation_age_seconds > allowed_age_seconds:
        integrity_blockers.add("benchmark_result_stale")

    if frozen_benchmark_receipt is None:
        integrity_blockers.add("benchmark_result_receipt_missing_or_ambiguous")
    else:
        receipt = frozen_benchmark_receipt
        observed = _parsed_timestamp(receipt.observed_at_utc)
        if receipt.verification_status is not VerificationStatus.PASS:
            integrity_blockers.add("benchmark_result_receipt_not_pass")
        if receipt.output_sha256 != evaluation.content_sha256:
            integrity_blockers.add("benchmark_result_receipt_evaluation_hash_mismatch")
        if receipt.evidence_set_id != request.frozen_benchmark_id:
            integrity_blockers.add("benchmark_result_receipt_id_mismatch")
        expected_bundle_sha256 = bundle.content_sha256 if bundle is not None else None
        if receipt.evidence_input_sha256 != expected_bundle_sha256:
            integrity_blockers.add("benchmark_result_receipt_evidence_bundle_mismatch")
        if receipt.evidence_dimensions != _EXPECTED_ADMISSION_DIMENSIONS[
            VerificationKind.FROZEN_BENCHMARK
        ]:
            integrity_blockers.add("benchmark_result_receipt_dimensions_mismatch")
        if receipt.source_identity_sha256 != request.source_identity.content_sha256:
            integrity_blockers.add("benchmark_result_receipt_source_mismatch")
        if receipt.module_manifest_sha256s != expected_manifest_hashes:
            integrity_blockers.add("benchmark_result_receipt_manifest_mismatch")
        if receipt.covered_module_ids != expected_module_ids:
            integrity_blockers.add("benchmark_result_receipt_module_coverage_mismatch")
        if receipt.covered_capability_ids != expected_capability_ids:
            integrity_blockers.add("benchmark_result_receipt_capability_coverage_mismatch")
        if receipt.covered_schema_ids != expected_schema_ids:
            integrity_blockers.add("benchmark_result_receipt_schema_coverage_mismatch")
        if receipt.artifact_closure_sha256 != expected_closure_sha256:
            integrity_blockers.add("benchmark_result_receipt_closure_mismatch")
        if receipt.covered_artifact_ids != expected_artifact_ids:
            integrity_blockers.add("benchmark_result_receipt_artifact_coverage_mismatch")
        if evaluated > observed:
            integrity_blockers.add("benchmark_result_postverification_order_invalid")
        receipt_age_seconds = (as_of - observed).total_seconds()
        if receipt_age_seconds < 0:
            integrity_blockers.add("benchmark_result_receipt_future")
        elif receipt_age_seconds > allowed_age_seconds:
            integrity_blockers.add("benchmark_result_receipt_stale")

    if integrity_blockers:
        integrity_blockers.add(TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER)
        return None, None, integrity_blockers, outcome_blockers

    if (
        evaluation.status is not BenchmarkEvaluationStatus.PASS
        or not evaluation.benchmark_contract_satisfied
    ):
        outcome_blockers.add(f"benchmark_result_status:{evaluation.status.value}")
        outcome_blockers.update(
            f"benchmark_result_failure:{code}" for code in evaluation.failure_codes
        )
        outcome_blockers.update(
            f"benchmark_result_hold:{code}" for code in evaluation.hold_codes
        )

    return (
        evaluation.content_sha256,
        verifier_identity_sha256,
        integrity_blockers,
        outcome_blockers,
    )


def evaluate_runtime_admission(
    request: AdmissionRequest,
    *,
    trusted_policy: TrustedBenchmarkAdmissionPolicy | None = None,
    trusted_as_of_utc: str | None = None,
) -> AdmissionDecision:
    """Evaluate exact receipts and one typed, independently pinned benchmark result.

    Generic receipts establish internal packet consistency only.  Runtime
    admission can clear the trusted-result blocker only when the unique frozen
    benchmark receipt binds the canonical bytes of a fresh typed evaluation and
    every source, manifest, coverage, closure, verifier, and temporal identity
    matches exactly.  Even an ADMITTED result remains structural-only.
    """

    if not isinstance(request, AdmissionRequest):
        raise TypeError("request must be an AdmissionRequest")
    if trusted_policy is not None and not isinstance(
        trusted_policy, TrustedBenchmarkAdmissionPolicy
    ):
        raise TypeError("trusted_policy must be a TrustedBenchmarkAdmissionPolicy or None")

    trusted_clock_supplied = trusted_as_of_utc is not None
    decision_time = (
        _timestamp(trusted_as_of_utc, "trusted_as_of_utc")
        if trusted_as_of_utc is not None
        else request.as_of_utc
    )

    static_blockers: set[str] = set()
    admission_blockers = _artifact_closure_blockers(request)
    mandatory = set(MANDATORY_AUTHORITY_EXCLUSIONS)
    missing_request_exclusions = mandatory - set(request.required_exclusions)
    static_blockers.update(
        f"request_missing_exclusion:{value}" for value in missing_request_exclusions
    )

    for manifest in request.module_manifests:
        missing = set(request.required_exclusions) - set(manifest.exclusions)
        static_blockers.update(
            f"module:{manifest.module_id}:missing_exclusion:{value}" for value in missing
        )
        if not manifest.authority_ceiling.is_no_stronger_than(request.maximum_authority_ceiling):
            static_blockers.add(f"module_authority_exceeds_request:{manifest.module_id}")

    schema_consumers: dict[str, list[tuple[str, str]]] = {}
    for manifest in request.module_manifests:
        for schema in manifest.schemas:
            schema_consumers.setdefault(schema.schema_id, []).append(
                (manifest.module_id, schema.schema_sha256)
            )
    for schema_id, consumers in schema_consumers.items():
        if len({schema_sha256 for _, schema_sha256 in consumers}) > 1:
            static_blockers.update(
                f"shared_schema_hash_mismatch:{schema_id}:consumer:{module_id}"
                for module_id, _ in consumers
            )

    expected_manifest_hashes = tuple(
        sorted(item.content_sha256 for item in request.module_manifests)
    )
    expected_module_ids = tuple(sorted(item.module_id for item in request.module_manifests))
    expected_capability_ids = tuple(
        sorted(
            capability.capability_id
            for manifest in request.module_manifests
            for capability in manifest.capabilities
        )
    )
    expected_schema_ids = tuple(
        sorted(
            {
                schema.schema_id
                for manifest in request.module_manifests
                for schema in manifest.schemas
            }
        )
    )
    closure = request.artifact_closure
    expected_closure_sha256 = closure.content_sha256 if closure is not None else None
    expected_artifact_ids = closure.artifact_ids if closure is not None else ()
    as_of = _parsed_timestamp(decision_time)
    frozen_benchmark_receipt: VerificationReceipt | None = None

    for kind in request.required_verification_kinds:
        kind_blockers = (
            static_blockers if kind in _STATIC_VERIFICATION_KINDS else admission_blockers
        )
        matches = tuple(
            receipt
            for receipt in request.verification_receipts
            if receipt.verification_kind is kind
        )
        if not matches:
            kind_blockers.add(f"missing_verification:{kind.value}")
            continue
        if len(matches) != 1:
            kind_blockers.add(f"ambiguous_verification:{kind.value}")
            continue
        receipt = matches[0]
        if kind is VerificationKind.FROZEN_BENCHMARK:
            frozen_benchmark_receipt = receipt
        if receipt.verification_status is not VerificationStatus.PASS:
            kind_blockers.add(f"failed_verification:{kind.value}")
            kind_blockers.update(
                f"receipt:{receipt.receipt_id}:blocker:{value}" for value in receipt.blockers
            )
        observed = _parsed_timestamp(receipt.observed_at_utc)
        age_seconds = (as_of - observed).total_seconds()
        if age_seconds < 0:
            kind_blockers.add(f"future_verification:{kind.value}")
        elif age_seconds > request.max_receipt_age_seconds:
            kind_blockers.add(f"stale_verification:{kind.value}")
        if receipt.source_identity_sha256 != request.source_identity.content_sha256:
            kind_blockers.add(f"source_identity_mismatch:{kind.value}")
        if receipt.module_manifest_sha256s != expected_manifest_hashes:
            kind_blockers.add(f"manifest_hash_mismatch:{kind.value}")
        if receipt.covered_module_ids != expected_module_ids:
            kind_blockers.add(f"module_coverage_mismatch:{kind.value}")
        if receipt.covered_capability_ids != expected_capability_ids:
            kind_blockers.add(f"capability_coverage_mismatch:{kind.value}")
        if receipt.covered_schema_ids != expected_schema_ids:
            kind_blockers.add(f"schema_coverage_mismatch:{kind.value}")

        if kind in _ADMISSION_VERIFICATION_KINDS:
            if receipt.artifact_closure_sha256 != expected_closure_sha256:
                kind_blockers.add(f"artifact_closure_hash_mismatch:{kind.value}")
            if receipt.covered_artifact_ids != expected_artifact_ids:
                kind_blockers.add(f"artifact_coverage_mismatch:{kind.value}")
            if receipt.evidence_dimensions != _EXPECTED_ADMISSION_DIMENSIONS[kind]:
                kind_blockers.add(f"evidence_dimensions_mismatch:{kind.value}")
            expected_evidence_id = (
                request.frozen_benchmark_id
                if kind is VerificationKind.FROZEN_BENCHMARK
                else request.performance_resource_policy_id
            )
            expected_evidence_sha256 = (
                (
                    request.frozen_benchmark_verification_bundle.content_sha256
                    if request.frozen_benchmark_verification_bundle is not None
                    else request.frozen_benchmark_sha256
                )
                if kind is VerificationKind.FROZEN_BENCHMARK
                else request.performance_resource_policy_sha256
            )
            if receipt.evidence_set_id != expected_evidence_id:
                kind_blockers.add(f"evidence_set_mismatch:{kind.value}")
            if receipt.evidence_input_sha256 != expected_evidence_sha256:
                kind_blockers.add(f"evidence_input_mismatch:{kind.value}")

    (
        verified_benchmark_evaluation_sha256,
        benchmark_verifier_identity_sha256,
        benchmark_integrity_blockers,
        benchmark_outcome_blockers,
    ) = _evaluate_benchmark_result_bridge(
        request,
        trusted_policy=trusted_policy,
        trusted_clock_supplied=trusted_clock_supplied,
        frozen_benchmark_receipt=frozen_benchmark_receipt,
        expected_manifest_hashes=expected_manifest_hashes,
        expected_module_ids=expected_module_ids,
        expected_capability_ids=expected_capability_ids,
        expected_schema_ids=expected_schema_ids,
        expected_closure_sha256=expected_closure_sha256,
        expected_artifact_ids=expected_artifact_ids,
        as_of=as_of,
    )
    static_blockers.update(benchmark_integrity_blockers)
    static_blockers.update(benchmark_outcome_blockers)

    if static_blockers:
        status = AdmissionStatus.HOLD
        blockers = static_blockers | admission_blockers
    elif admission_blockers:
        status = AdmissionStatus.PRE_ADMISSION_VERIFIED
        blockers = admission_blockers
    else:
        status = AdmissionStatus.ADMITTED
        blockers = set()
    authority = AuthorityCeiling.minimum(
        (
            request.maximum_authority_ceiling,
            *(item.authority_ceiling for item in request.module_manifests),
        )
    )
    exclusions = tuple(
        sorted(
            {
                *MANDATORY_AUTHORITY_EXCLUSIONS,
                *request.required_exclusions,
                *(value for item in request.module_manifests for value in item.exclusions),
            }
        )
    )
    request_sha256 = request.content_sha256
    return AdmissionDecision(
        decision_id=f"runtime-admission:{request_sha256[:24]}",
        request_sha256=request_sha256,
        status=status,
        admitted_module_ids=(expected_module_ids if status is AdmissionStatus.ADMITTED else ()),
        pre_admission_verified_module_ids=(
            expected_module_ids if status is not AdmissionStatus.HOLD else ()
        ),
        considered_receipt_ids=tuple(item.receipt_id for item in request.verification_receipts),
        blockers=tuple(blockers),
        evaluated_at_utc=decision_time,
        verified_benchmark_evaluation_sha256=(
            verified_benchmark_evaluation_sha256
        ),
        benchmark_verifier_identity_sha256=benchmark_verifier_identity_sha256,
        trusted_benchmark_policy_sha256=(
            trusted_policy.content_sha256
            if verified_benchmark_evaluation_sha256 is not None
            and trusted_policy is not None
            else None
        ),
        authority_ceiling=authority,
        exclusions=exclusions,
        benchmark_execution_authorized=False,
        empirical_authority=False,
        formula_generation_authorized=False,
        physical_execution_authorized=False,
        compounding_authority=False,
        sensory_authority=False,
        liking_authority=False,
        safety_authority=False,
        stability_authority=False,
        purchase_authority=False,
        release_authority=False,
    )


def _diagnostic_value(payload: Mapping[str, Any]) -> str:
    return _canonical_json_bytes(payload).decode("utf-8")


def _unknown_needed_evidence(blocker: str) -> str:
    if blocker == "missing_artifact_closure" or blocker.startswith("closure_"):
        return (
            "A complete exact-hash transitive source/config/schema/data closure "
            "bound to every admitted module"
        )
    if blocker.startswith("missing_verification:"):
        kind = blocker.partition(":")[2]
        return f"One exact fresh PASS receipt for {kind} at the request source identity"
    if blocker.startswith(("stale_verification:", "future_verification:")):
        kind = blocker.partition(":")[2]
        return f"A temporally valid fresh {kind} receipt"
    if "benchmark" in blocker:
        return "The exact frozen-benchmark identity, input hash, and result receipt"
    if "performance" in blocker:
        return (
            "The exact performance/resource policy hash and result receipt covering "
            "the declared artifact closure"
        )
    return "A corrected exact-scope hash-bound receipt or manifest resolving this blocker"


def admission_to_evidence_authority_assessment(
    request: AdmissionRequest,
    decision: AdmissionDecision,
    *,
    semantic_target_scope: str,
    temporal_scope: str,
    matrix_scope: str,
    trusted_policy: TrustedBenchmarkAdmissionPolicy | None = None,
    trusted_as_of_utc: str | None = None,
) -> PlaneAssessment:
    """Project admission state onto the EVIDENCE_AUTHORITY plane.

    The projection reports structural receipt state only.  It creates no support
    interval, observation, benchmark-execution permission, scientific authority,
    or release authority.
    """

    if not isinstance(request, AdmissionRequest):
        raise TypeError("request must be an AdmissionRequest")
    if not isinstance(decision, AdmissionDecision):
        raise TypeError("decision must be an AdmissionDecision")
    if decision.request_sha256 != request.content_sha256:
        raise ValueError("decision request_sha256 does not match request")
    expected_decision = evaluate_runtime_admission(
        request,
        trusted_policy=trusted_policy,
        trusted_as_of_utc=trusted_as_of_utc,
    )
    if decision != expected_decision:
        raise ValueError("decision does not match deterministic request evaluation")

    scope = AssessmentScope(
        target_scope=semantic_target_scope,
        temporal_scope=temporal_scope,
        matrix_scope=matrix_scope,
    )
    adapter_ceiling = (
        AuthorityCeiling.WITHHELD
        if decision.status is AdmissionStatus.HOLD
        else AuthorityCeiling.minimum(
            (decision.authority_ceiling, AuthorityCeiling.STRUCTURAL_ONLY)
        )
    )
    independence_key = f"runtime-admission:{request.content_sha256[:24]}"
    request_provenance = ProvenanceRef(
        provenance_id=f"admission-request:{request.content_sha256[:24]}",
        source_ref=f"Runtime admission request {request.request_id}",
        evidence_class=EvidenceClass.HEURISTIC,
        independence_key=independence_key,
        source_sha256=request.content_sha256,
    )
    decision_provenance = ProvenanceRef(
        provenance_id=f"admission-decision:{decision.content_sha256[:24]}",
        source_ref=f"Deterministic runtime admission decision {decision.decision_id}",
        evidence_class=EvidenceClass.HEURISTIC,
        independence_key=independence_key,
        source_sha256=decision.content_sha256,
    )
    provenance = (request_provenance, decision_provenance)

    claims: list[ScopedClaim] = []

    def add_claim(
        claim_key: str,
        claim_value: str,
        claim_kind: ClaimKind,
        *,
        member_id: str | None = None,
    ) -> None:
        cardinality = ClaimCardinality.SINGLE if member_id is None else ClaimCardinality.SET_MEMBER
        identity = _canonical_json_bytes(
            {
                "claim_key": claim_key,
                "claim_value": claim_value,
                "member_id": member_id,
                "scope": scope.as_dict(),
            }
        )
        claims.append(
            ScopedClaim(
                claim_id=f"admission:{sha256(identity).hexdigest()[:24]}",
                claim_key=claim_key,
                claim_value=claim_value,
                claim_kind=claim_kind,
                authority_ceiling=adapter_ceiling,
                provenance_refs=provenance,
                cardinality=cardinality,
                member_id=member_id,
            )
        )

    add_claim(
        "runtime_admission.status",
        decision.status.value,
        ClaimKind.DIAGNOSTIC,
    )
    add_claim(
        "runtime_admission.request.sha256",
        request.content_sha256,
        ClaimKind.DIAGNOSTIC,
    )
    add_claim(
        "runtime_admission.decision.sha256",
        decision.content_sha256,
        ClaimKind.DIAGNOSTIC,
    )
    add_claim(
        "runtime_admission.source_identity",
        _diagnostic_value(
            {
                "repository_id": request.source_identity.repository_id,
                "source_task_id": request.source_identity.source_task_id,
                "worktree_path": request.source_identity.worktree_path,
                "branch_ref": request.source_identity.branch_ref,
                "head_commit": request.source_identity.head_commit,
                "workspace_state_sha256": (request.source_identity.workspace_state_sha256),
                "source_identity_sha256": request.source_identity.content_sha256,
            }
        ),
        ClaimKind.DIAGNOSTIC,
    )
    add_claim(
        "runtime_admission.artifact_closure.required",
        "true",
        ClaimKind.REQUIREMENT,
    )
    add_claim(
        "runtime_admission.artifact_closure.state",
        "present" if request.artifact_closure is not None else "absent",
        ClaimKind.DIAGNOSTIC,
    )
    if request.artifact_closure is not None:
        add_claim(
            "runtime_admission.artifact_closure.sha256",
            request.artifact_closure.content_sha256,
            ClaimKind.DIAGNOSTIC,
        )
        for artifact in request.artifact_closure.artifacts:
            add_claim(
                "runtime_admission.artifact",
                _diagnostic_value(
                    {
                        "artifact_id": artifact.artifact_id,
                        "artifact_kind": artifact.artifact_kind.value,
                        "artifact_path": artifact.artifact_path,
                        "artifact_sha256": artifact.artifact_sha256,
                        "dependency_ids": artifact.dependency_ids,
                    }
                ),
                ClaimKind.DIAGNOSTIC,
                member_id=artifact.artifact_id,
            )

    add_claim(
        "runtime_admission.frozen_benchmark.id",
        request.frozen_benchmark_id,
        ClaimKind.REQUIREMENT,
    )
    add_claim(
        "runtime_admission.frozen_benchmark.sha256",
        request.frozen_benchmark_sha256,
        ClaimKind.REQUIREMENT,
    )
    add_claim(
        "runtime_admission.frozen_benchmark.challenge_nonce",
        request.benchmark_challenge_nonce,
        ClaimKind.DIAGNOSTIC,
    )
    add_claim(
        "runtime_admission.frozen_benchmark.request_scope_sha256",
        benchmark_request_scope_sha256(request),
        ClaimKind.DIAGNOSTIC,
    )
    if request.frozen_benchmark_verification_bundle is not None:
        add_claim(
            "runtime_admission.frozen_benchmark.bundle_sha256",
            request.frozen_benchmark_verification_bundle.content_sha256,
            ClaimKind.DIAGNOSTIC,
        )
    if (
        request.frozen_benchmark_evaluation is not None
        and decision.verified_benchmark_evaluation_sha256
        == request.frozen_benchmark_evaluation.content_sha256
    ):
        add_claim(
            "runtime_admission.benchmark_evaluation.sha256",
            decision.verified_benchmark_evaluation_sha256,
            ClaimKind.DIAGNOSTIC,
        )
        add_claim(
            "runtime_admission.benchmark_evaluation.status",
            request.frozen_benchmark_evaluation.status.value,
            ClaimKind.DIAGNOSTIC,
        )
        add_claim(
            "runtime_admission.benchmark_verifier.identity_sha256",
            decision.benchmark_verifier_identity_sha256 or "unverified",
            ClaimKind.DIAGNOSTIC,
        )
        add_claim(
            "runtime_admission.benchmark_policy.sha256",
            decision.trusted_benchmark_policy_sha256 or "unverified",
            ClaimKind.DIAGNOSTIC,
        )
        add_claim(
            "runtime_admission.benchmark_output_binding.verified",
            "true",
            ClaimKind.DIAGNOSTIC,
        )
    add_claim(
        "runtime_admission.performance_resource_policy.id",
        request.performance_resource_policy_id,
        ClaimKind.REQUIREMENT,
    )
    add_claim(
        "runtime_admission.performance_resource_policy.sha256",
        request.performance_resource_policy_sha256,
        ClaimKind.REQUIREMENT,
    )

    for verification_kind in request.required_verification_kinds:
        add_claim(
            "runtime_admission.required_verification",
            verification_kind.value,
            ClaimKind.REQUIREMENT,
            member_id=f"verification:{verification_kind.value}",
        )
    for manifest in request.module_manifests:
        add_claim(
            "runtime_admission.module_manifest",
            _diagnostic_value(
                {
                    "module_id": manifest.module_id,
                    "module_path": manifest.module_path,
                    "source_sha256": manifest.source_sha256,
                    "source_artifact_id": manifest.source_artifact_id,
                    "manifest_sha256": manifest.content_sha256,
                    "capabilities": tuple(
                        {
                            "capability_id": item.capability_id,
                            "capability_sha256": item.capability_sha256,
                        }
                        for item in manifest.capabilities
                    ),
                    "schemas": tuple(
                        {
                            "schema_id": item.schema_id,
                            "schema_sha256": item.schema_sha256,
                        }
                        for item in manifest.schemas
                    ),
                }
            ),
            ClaimKind.DIAGNOSTIC,
            member_id=f"module:{manifest.module_id}",
        )
    for receipt in request.verification_receipts:
        add_claim(
            "runtime_admission.verification_receipt",
            _diagnostic_value(
                {
                    "receipt_id": receipt.receipt_id,
                    "verification_kind": receipt.verification_kind.value,
                    "verification_status": receipt.verification_status.value,
                    "receipt_sha256": receipt.content_sha256,
                    "output_sha256": receipt.output_sha256,
                    "evidence_set_id": receipt.evidence_set_id,
                    "evidence_input_sha256": receipt.evidence_input_sha256,
                    "artifact_closure_sha256": receipt.artifact_closure_sha256,
                }
            ),
            ClaimKind.DIAGNOSTIC,
            member_id=f"receipt:{receipt.receipt_id}",
        )
    for module_id in decision.pre_admission_verified_module_ids:
        add_claim(
            "runtime_admission.pre_admission_verified_module",
            module_id,
            ClaimKind.DIAGNOSTIC,
            member_id=f"pre-verified:{module_id}",
        )
    for module_id in decision.admitted_module_ids:
        add_claim(
            "runtime_admission.admitted_module",
            module_id,
            ClaimKind.DIAGNOSTIC,
            member_id=f"admitted:{module_id}",
        )
    for blocker in decision.blockers:
        blocker_id = sha256(blocker.encode("utf-8")).hexdigest()[:24]
        add_claim(
            "runtime_admission.blocker",
            blocker,
            ClaimKind.DIAGNOSTIC,
            member_id=f"blocker:{blocker_id}",
        )
    for exclusion in decision.exclusions:
        exclusion_id = sha256(exclusion.encode("utf-8")).hexdigest()[:24]
        add_claim(
            "runtime_admission.exclusion",
            exclusion,
            ClaimKind.PROHIBITION,
            member_id=f"exclusion:{exclusion_id}",
        )

    authority_flags = {
        "benchmark_execution_authorized": decision.benchmark_execution_authorized,
        "empirical_authority": decision.empirical_authority,
        "formula_generation_authorized": decision.formula_generation_authorized,
        "physical_execution_authorized": decision.physical_execution_authorized,
        "compounding_authority": decision.compounding_authority,
        "sensory_authority": decision.sensory_authority,
        "liking_authority": decision.liking_authority,
        "safety_authority": decision.safety_authority,
        "stability_authority": decision.stability_authority,
        "purchase_authority": decision.purchase_authority,
        "release_authority": decision.release_authority,
    }
    for flag_name, value in authority_flags.items():
        add_claim(
            "runtime_admission.authority_flag",
            f"{flag_name}={str(value).casefold()}",
            ClaimKind.PROHIBITION,
            member_id=f"authority-flag:{flag_name}",
        )

    unknowns = tuple(
        UnknownFact(
            unknown_id=("admission-unknown:" + sha256(blocker.encode("utf-8")).hexdigest()[:24]),
            field_key="runtime_admission.blocker",
            reason=blocker,
            needed_evidence=_unknown_needed_evidence(blocker),
            provenance_refs=provenance,
        )
        for blocker in decision.blockers
    )
    freshness_hashes = {
        request.content_sha256,
        decision.content_sha256,
        request.source_identity.content_sha256,
        request.source_identity.workspace_state_sha256,
        request.frozen_benchmark_sha256,
        request.performance_resource_policy_sha256,
        *(manifest.content_sha256 for manifest in request.module_manifests),
        *(manifest.source_sha256 for manifest in request.module_manifests),
        *(receipt.content_sha256 for receipt in request.verification_receipts),
    }
    if request.artifact_closure is not None:
        freshness_hashes.add(request.artifact_closure.content_sha256)
        freshness_hashes.update(
            artifact.artifact_sha256 for artifact in request.artifact_closure.artifacts
        )
    if request.frozen_benchmark_verification_bundle is not None:
        freshness_hashes.add(
            request.frozen_benchmark_verification_bundle.content_sha256
        )
    if request.frozen_benchmark_evaluation is not None:
        freshness_hashes.add(request.frozen_benchmark_evaluation.content_sha256)
        freshness_hashes.add(
            request.frozen_benchmark_evaluation.verifier_identity.content_sha256
        )
    if decision.trusted_benchmark_policy_sha256 is not None:
        freshness_hashes.add(decision.trusted_benchmark_policy_sha256)
    assessment_identity = _canonical_json_bytes(
        {
            "request_sha256": request.content_sha256,
            "decision_sha256": decision.content_sha256,
            "scope": scope.as_dict(),
        }
    )
    return PlaneAssessment(
        assessment_id=(
            "admission-evidence-authority:" + sha256(assessment_identity).hexdigest()[:24]
        ),
        module_id="formulation-intelligence-admission-adapter",
        plane_id=PlaneId.EVIDENCE_AUTHORITY,
        scope=scope,
        claims=tuple(claims),
        support_intervals=(),
        conflicts=(),
        unknowns=unknowns,
        failure_modes=decision.blockers,
        proposed_experiments=(),
        provenance_refs=provenance,
        authority_ceiling=adapter_ceiling,
        freshness_hashes=tuple(freshness_hashes),
        native_criteria=(),
    )


__all__ = [
    "MANDATORY_AUTHORITY_EXCLUSIONS",
    "MINIMUM_PRODUCTION_BENCHMARK_ARMS",
    "MINIMUM_PRODUCTION_BENCHMARK_CASES",
    "MINIMUM_PRODUCTION_GENERATION_GROUPS",
    "PRODUCTION_BENCHMARK_VERIFICATION_BUNDLE_SCHEMA_VERSION",
    "TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER",
    "AdmissionDecision",
    "AdmissionRequest",
    "AdmissionStatus",
    "ArtifactBinding",
    "ArtifactClosure",
    "ArtifactKind",
    "CampaignArtifactResolutionReceipt",
    "CampaignExecutionEvent",
    "CapabilityBinding",
    "ModuleAdmissionManifest",
    "PreexecutionCampaignReceipt",
    "PostexecutionCampaignReceipt",
    "ProductionArtifactBinding",
    "ProductionArtifactKind",
    "ProductionArtifactResolutionReceipt",
    "ProductionBenchmarkVerificationBundle",
    "ProductionEventKind",
    "ProductionEventStatus",
    "SchemaBinding",
    "SourceIdentity",
    "VerificationKind",
    "VerificationReceipt",
    "VerificationStatus",
    "TrustedBenchmarkAdmissionPolicy",
    "admission_to_evidence_authority_assessment",
    "benchmark_request_scope_sha256",
    "evaluate_runtime_admission",
    "verify_frozen_campaign_artifact_bytes",
    "verify_production_artifact_bytes",
]
