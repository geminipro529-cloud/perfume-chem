"""Frozen benchmark contracts without benchmark execution or answer keys.

This module defines the public, hash-verified WP-13 case corpus and the receipts
that a future external harness must produce.  It deliberately contains no model
client, prompt runner, judge, answer key, arm-condition mapping, admission
decision, perfume formula, or empirical result.  Public cases expose challenge
prompts and required invariant *keys* only; the scorer's expected values remain
outside the corpus and outside every arm.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any, ClassVar, Iterable, Mapping, TypeVar, cast

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")
_ARM_ID_RE = re.compile(r"^arm-[0-9a-f]{8}$")
_RecordT = TypeVar("_RecordT", bound="_BenchmarkRecord")


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    if not normalized:
        raise ValueError(f"{field_name} must be nonblank")
    return normalized


def _prompt_text(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("prompt_text must be text")
    normalized = unicodedata.normalize("NFKC", value)
    if not normalized or normalized != normalized.strip():
        raise ValueError("prompt_text must be nonblank with no outer whitespace")
    return normalized


def _identifier(value: object, field_name: str) -> str:
    normalized = _text(value, field_name).casefold()
    if not _IDENTIFIER_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a normalized identifier")
    return normalized


def _digest(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a SHA-256 digest")
    normalized = value.casefold()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized


def _identifier_tuple(
    values: Iterable[str],
    field_name: str,
    *,
    nonempty: bool = False,
) -> tuple[str, ...]:
    normalized = tuple(_identifier(value, field_name) for value in values)
    if nonempty and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized))


def _digest_tuple(
    values: Iterable[str], field_name: str, *, nonempty: bool = False
) -> tuple[str, ...]:
    normalized = tuple(_digest(value, field_name) for value in values)
    if nonempty and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized))


def _nonnegative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ValueError(f"{field_name} must be nonnegative")
    return value


def _finite_nonnegative(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0:
        raise ValueError(f"{field_name} must be finite and nonnegative")
    return normalized


def _utc_timestamp(value: object, field_name: str) -> str:
    normalized = _text(value, field_name)
    if not normalized.endswith("Z"):
        raise ValueError(f"{field_name} must be an ISO-8601 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(f"{normalized[:-1]}+00:00")
    except ValueError as error:
        raise ValueError(f"{field_name} must be a valid ISO-8601 timestamp") from error
    if parsed.tzinfo != timezone.utc:
        raise ValueError(f"{field_name} must be UTC")
    return normalized


def _to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, _BenchmarkRecord):
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


def _closed_payload(
    payload: Mapping[str, Any], schema_version: str, field_names: Iterable[str]
) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    expected = {"schema_version", *field_names}
    received = set(payload)
    if received != expected:
        raise ValueError(
            f"{schema_version} payload does not match closed schema; "
            f"missing={sorted(expected - received)!r}, "
            f"extra={sorted(received - expected)!r}"
        )
    if payload["schema_version"] != schema_version:
        raise ValueError(
            f"schema_version must be {schema_version!r}, received {payload['schema_version']!r}"
        )
    return payload


def _record_payload(record_type: type[_RecordT], payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return _closed_payload(
        payload,
        record_type.SCHEMA_VERSION,
        (item.name for item in fields(cast(Any, record_type))),
    )


class _BenchmarkRecord:
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


class CorpusPartition(str, Enum):
    CROSS_FAMILY = "cross_family"
    HELD_OUT = "held_out"


class RunStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class ReceiptStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


class GateDomain(str, Enum):
    AUTHORITY = "authority"
    INVENTORY = "inventory"
    NATURAL_MIXTURE = "natural_mixture"
    PROTOCOL = "protocol"
    SAFETY = "safety"
    RECURSIVE_CLOSURE = "recursive_closure"


class PerformanceMetric(str, Enum):
    COLD_IMPORT_MS = "cold_import_ms"
    WARM_PACKET_SYNTHESIS_MS = "warm_packet_synthesis_ms"
    INCREMENTAL_ONE_PLANE_RECOMPUTE_MS = "incremental_one_plane_recompute_ms"
    PEAK_MEMORY_MIB = "peak_memory_mib"
    LARGE_PACKET_SCALING_RATIO = "large_packet_scaling_ratio"


class PerformanceComparator(str, Enum):
    AT_MOST = "at_most"
    AT_LEAST = "at_least"


MANDATORY_FAMILY_KEYS = frozenset(
    {
        "rose_soliflore",
        "narcotic_white_floral",
        "translucent_muguet",
        "iris_contrast",
        "magnolia_champaca",
        "multi_floral_bouquet",
        "citrus_cologne",
        "aromatic_fougere",
        "green",
        "chypre",
        "leather",
        "woody",
        "amber",
        "gourmand",
        "marine_ozonic",
        "musk",
        "incense_resin",
        "tobacco",
        "fruit_centered",
    }
)

MANDATORY_CHALLENGE_TAGS = frozenset(
    {
        "floral_object",
        "bouquet",
        "white_floral_takeover",
        "sparse_solution",
        "dense_solution",
        "safe_no_change",
        "unavailable_stock",
        "ambiguous_stock",
        "diluted_stock",
        "natural_composite",
        "carrier_conflict",
        "named_reference",
        "concept_only",
        "sensory_contradicts_model",
        "heterogeneous_preferences",
        "order_confounding",
        "numeric_identity_decoy",
        "modest_numeric_target_faithful",
    }
)

PUBLIC_AUTHORITY_EXCLUSIONS = (
    "compounding_authority",
    "empirical_authority",
    "formula_authority",
    "liking_authority",
    "physical_execution_authority",
    "purchase_authority",
    "release_authority",
    "safety_authority",
    "sensory_authority",
    "stability_authority",
)

FORBIDDEN_PUBLIC_KEY_NAMES = frozenset(
    {
        "answer",
        "answer_key",
        "condition",
        "condition_id",
        "expected_output",
        "expected_value",
        "gold_label",
        "judge_scores",
        "model_output",
        "scorer_key",
        "solution",
    }
)


@dataclass(frozen=True, slots=True)
class InvariantRequirements(_BenchmarkRecord):
    """Public invariant names; no expected values or scorer solution."""

    SCHEMA_VERSION = "benchmark_invariant_requirements_v1"

    required_evidence_keys: tuple[str, ...]
    authority_keys: tuple[str, ...]
    inventory_keys: tuple[str, ...]
    protocol_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "required_evidence_keys",
            "authority_keys",
            "inventory_keys",
            "protocol_keys",
        ):
            object.__setattr__(
                self,
                field_name,
                _identifier_tuple(getattr(self, field_name), field_name),
            )
        if not self.required_evidence_keys or not self.authority_keys:
            raise ValueError("every public case requires evidence and authority invariants")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> InvariantRequirements:
        data = _record_payload(cls, payload)
        return cls(
            required_evidence_keys=tuple(data["required_evidence_keys"]),
            authority_keys=tuple(data["authority_keys"]),
            inventory_keys=tuple(data["inventory_keys"]),
            protocol_keys=tuple(data["protocol_keys"]),
        )


@dataclass(frozen=True, slots=True)
class BenchmarkCase(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_public_case_v1"

    case_id: str
    partition: CorpusPartition
    family_key: str
    prompt_text: str
    prompt_sha256: str
    challenge_tags: tuple[str, ...]
    invariants: InvariantRequirements

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _identifier(self.case_id, "case_id"))
        object.__setattr__(self, "partition", CorpusPartition(self.partition))
        object.__setattr__(self, "family_key", _identifier(self.family_key, "family_key"))
        prompt = _prompt_text(self.prompt_text)
        object.__setattr__(self, "prompt_text", prompt)
        object.__setattr__(self, "prompt_sha256", _digest(self.prompt_sha256, "prompt_sha256"))
        if sha256(prompt.encode("utf-8")).hexdigest() != self.prompt_sha256:
            raise ValueError("prompt_sha256 does not match prompt_text UTF-8 bytes")
        object.__setattr__(
            self,
            "challenge_tags",
            _identifier_tuple(self.challenge_tags, "challenge_tags", nonempty=True),
        )
        if not isinstance(self.invariants, InvariantRequirements):
            raise TypeError("invariants must be InvariantRequirements")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BenchmarkCase:
        data = _record_payload(cls, payload)
        return cls(
            case_id=data["case_id"],
            partition=CorpusPartition(data["partition"]),
            family_key=data["family_key"],
            prompt_text=data["prompt_text"],
            prompt_sha256=data["prompt_sha256"],
            challenge_tags=tuple(data["challenge_tags"]),
            invariants=InvariantRequirements.from_dict(data["invariants"]),
        )


@dataclass(frozen=True, slots=True)
class AnonymizedArm(_BenchmarkRecord):
    """Opaque public arm identity with no condition or guidance disclosure."""

    SCHEMA_VERSION = "benchmark_anonymized_arm_v1"

    arm_id: str

    def __post_init__(self) -> None:
        arm_id = _identifier(self.arm_id, "arm_id")
        if not _ARM_ID_RE.fullmatch(arm_id):
            raise ValueError("arm_id must match arm- plus eight lowercase hex characters")
        object.__setattr__(self, "arm_id", arm_id)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> AnonymizedArm:
        data = _record_payload(cls, payload)
        return cls(arm_id=data["arm_id"])


@dataclass(frozen=True, slots=True)
class SealedPublicCorpus(_BenchmarkRecord):
    """Public case prompts and invariant names, explicitly without answer keys."""

    SCHEMA_VERSION = "formulation_intelligence_benchmark_public_corpus_v1"

    corpus_id: str
    sealed: bool
    cases: tuple[BenchmarkCase, ...]
    anonymized_arms: tuple[AnonymizedArm, ...]
    authority_exclusions: tuple[str, ...]
    benchmark_execution_authorized: bool
    empirical_authority: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "corpus_id", _identifier(self.corpus_id, "corpus_id"))
        if self.sealed is not True:
            raise ValueError("public corpus must be sealed")
        if self.benchmark_execution_authorized is not False:
            raise ValueError("the public corpus cannot authorize benchmark execution")
        if self.empirical_authority is not False:
            raise ValueError("the public corpus has no empirical authority")
        cases = tuple(sorted(self.cases, key=lambda item: item.case_id))
        if not cases or any(not isinstance(item, BenchmarkCase) for item in cases):
            raise TypeError("cases must contain BenchmarkCase values")
        if len({item.case_id for item in cases}) != len(cases):
            raise ValueError("case_id values must be unique")
        object.__setattr__(self, "cases", cases)
        arms = tuple(sorted(self.anonymized_arms, key=lambda item: item.arm_id))
        if not arms or any(not isinstance(item, AnonymizedArm) for item in arms):
            raise TypeError("anonymized_arms must contain AnonymizedArm values")
        if len({item.arm_id for item in arms}) != len(arms):
            raise ValueError("arm_id values must be unique")
        object.__setattr__(self, "anonymized_arms", arms)
        exclusions = _identifier_tuple(
            self.authority_exclusions, "authority_exclusions", nonempty=True
        )
        if exclusions != PUBLIC_AUTHORITY_EXCLUSIONS:
            raise ValueError("authority_exclusions must match the public corpus ceiling")
        object.__setattr__(self, "authority_exclusions", exclusions)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SealedPublicCorpus:
        data = _record_payload(cls, payload)
        return cls(
            corpus_id=data["corpus_id"],
            sealed=data["sealed"],
            cases=tuple(BenchmarkCase.from_dict(item) for item in data["cases"]),
            anonymized_arms=tuple(
                AnonymizedArm.from_dict(item) for item in data["anonymized_arms"]
            ),
            authority_exclusions=tuple(data["authority_exclusions"]),
            benchmark_execution_authorized=data["benchmark_execution_authorized"],
            empirical_authority=data["empirical_authority"],
        )


@dataclass(frozen=True, slots=True)
class RecursiveClosureReceiptRef(_BenchmarkRecord):
    """Reference to a separately generated complete transitive closure receipt."""

    SCHEMA_VERSION = "benchmark_recursive_closure_receipt_ref_v1"

    receipt_id: str
    receipt_sha256: str
    closure_manifest_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "receipt_id", _identifier(self.receipt_id, "receipt_id"))
        object.__setattr__(self, "receipt_sha256", _digest(self.receipt_sha256, "receipt_sha256"))
        object.__setattr__(
            self,
            "closure_manifest_sha256",
            _digest(self.closure_manifest_sha256, "closure_manifest_sha256"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RecursiveClosureReceiptRef:
        data = _record_payload(cls, payload)
        return cls(
            receipt_id=data["receipt_id"],
            receipt_sha256=data["receipt_sha256"],
            closure_manifest_sha256=data["closure_manifest_sha256"],
        )


@dataclass(frozen=True, slots=True)
class ArmPromptReceipt(_BenchmarkRecord):
    """Hash-only receipt for one rendered prompt; contains no condition label."""

    SCHEMA_VERSION = "benchmark_arm_prompt_receipt_v1"

    receipt_id: str
    corpus_sha256: str
    case_id: str
    arm_id: str
    case_prompt_sha256: str
    arm_instruction_sha256: str
    rendered_prompt_sha256: str
    recursive_closure: RecursiveClosureReceiptRef

    def __post_init__(self) -> None:
        object.__setattr__(self, "receipt_id", _identifier(self.receipt_id, "receipt_id"))
        object.__setattr__(self, "corpus_sha256", _digest(self.corpus_sha256, "corpus_sha256"))
        object.__setattr__(self, "case_id", _identifier(self.case_id, "case_id"))
        arm_id = _identifier(self.arm_id, "arm_id")
        if not _ARM_ID_RE.fullmatch(arm_id):
            raise ValueError("arm_id must be anonymized")
        object.__setattr__(self, "arm_id", arm_id)
        for field_name in (
            "case_prompt_sha256",
            "arm_instruction_sha256",
            "rendered_prompt_sha256",
        ):
            object.__setattr__(self, field_name, _digest(getattr(self, field_name), field_name))
        if not isinstance(self.recursive_closure, RecursiveClosureReceiptRef):
            raise TypeError("recursive_closure must be RecursiveClosureReceiptRef")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ArmPromptReceipt:
        data = _record_payload(cls, payload)
        return cls(
            receipt_id=data["receipt_id"],
            corpus_sha256=data["corpus_sha256"],
            case_id=data["case_id"],
            arm_id=data["arm_id"],
            case_prompt_sha256=data["case_prompt_sha256"],
            arm_instruction_sha256=data["arm_instruction_sha256"],
            rendered_prompt_sha256=data["rendered_prompt_sha256"],
            recursive_closure=RecursiveClosureReceiptRef.from_dict(data["recursive_closure"]),
        )


@dataclass(frozen=True, slots=True)
class BenchmarkRunReceipt(_BenchmarkRecord):
    """Execution receipt schema; hashes an output but never embeds that output."""

    SCHEMA_VERSION = "benchmark_run_receipt_v1"

    run_id: str
    arm_prompt_receipt_sha256: str
    execution_config_sha256: str
    provider_id: str
    model_id: str
    reasoning_level: str
    status: RunStatus
    output_sha256: str | None
    started_at_utc: str
    finished_at_utc: str
    input_tokens: int
    output_tokens: int
    recursive_closure: RecursiveClosureReceiptRef

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _identifier(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "arm_prompt_receipt_sha256",
            _digest(self.arm_prompt_receipt_sha256, "arm_prompt_receipt_sha256"),
        )
        object.__setattr__(
            self,
            "execution_config_sha256",
            _digest(self.execution_config_sha256, "execution_config_sha256"),
        )
        provider_id = _identifier(self.provider_id, "provider_id")
        if provider_id != "openai":
            raise ValueError("benchmark model runs are OpenAI-only")
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "model_id", _text(self.model_id, "model_id"))
        object.__setattr__(
            self, "reasoning_level", _identifier(self.reasoning_level, "reasoning_level")
        )
        object.__setattr__(self, "status", RunStatus(self.status))
        if self.output_sha256 is not None:
            object.__setattr__(self, "output_sha256", _digest(self.output_sha256, "output_sha256"))
        if self.status is RunStatus.COMPLETED and self.output_sha256 is None:
            raise ValueError("completed runs require output_sha256")
        if self.status is RunStatus.FAILED and self.output_sha256 is not None:
            raise ValueError("failed runs must not claim an output_sha256")
        object.__setattr__(
            self, "started_at_utc", _utc_timestamp(self.started_at_utc, "started_at_utc")
        )
        object.__setattr__(
            self,
            "finished_at_utc",
            _utc_timestamp(self.finished_at_utc, "finished_at_utc"),
        )
        started = datetime.fromisoformat(f"{self.started_at_utc[:-1]}+00:00")
        finished = datetime.fromisoformat(f"{self.finished_at_utc[:-1]}+00:00")
        if finished < started:
            raise ValueError("finished_at_utc must not precede started_at_utc")
        object.__setattr__(
            self, "input_tokens", _nonnegative_int(self.input_tokens, "input_tokens")
        )
        object.__setattr__(
            self, "output_tokens", _nonnegative_int(self.output_tokens, "output_tokens")
        )
        if not isinstance(self.recursive_closure, RecursiveClosureReceiptRef):
            raise TypeError("recursive_closure must be RecursiveClosureReceiptRef")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BenchmarkRunReceipt:
        data = _record_payload(cls, payload)
        return cls(
            run_id=data["run_id"],
            arm_prompt_receipt_sha256=data["arm_prompt_receipt_sha256"],
            execution_config_sha256=data["execution_config_sha256"],
            provider_id=data["provider_id"],
            model_id=data["model_id"],
            reasoning_level=data["reasoning_level"],
            status=RunStatus(data["status"]),
            output_sha256=data["output_sha256"],
            started_at_utc=data["started_at_utc"],
            finished_at_utc=data["finished_at_utc"],
            input_tokens=data["input_tokens"],
            output_tokens=data["output_tokens"],
            recursive_closure=RecursiveClosureReceiptRef.from_dict(data["recursive_closure"]),
        )


@dataclass(frozen=True, slots=True)
class JudgeReceipt(_BenchmarkRecord):
    """Receipt for blinded judging; the unblinding map is intentionally absent."""

    SCHEMA_VERSION = "benchmark_judge_receipt_v1"

    judge_receipt_id: str
    blinded_bundle_sha256: str
    rubric_sha256: str
    scorer_provider_id: str
    scorer_identity: str
    scorer_config_sha256: str
    score_artifact_sha256: str
    observed_at_utc: str
    blind_mapping_embedded: bool
    recursive_closure: RecursiveClosureReceiptRef

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "judge_receipt_id",
            _identifier(self.judge_receipt_id, "judge_receipt_id"),
        )
        for field_name in (
            "blinded_bundle_sha256",
            "rubric_sha256",
            "scorer_config_sha256",
            "score_artifact_sha256",
        ):
            object.__setattr__(self, field_name, _digest(getattr(self, field_name), field_name))
        scorer_provider_id = _identifier(self.scorer_provider_id, "scorer_provider_id")
        if scorer_provider_id not in {"human", "openai"}:
            raise ValueError("scorers must be human or OpenAI; external providers are forbidden")
        object.__setattr__(self, "scorer_provider_id", scorer_provider_id)
        object.__setattr__(self, "scorer_identity", _text(self.scorer_identity, "scorer_identity"))
        object.__setattr__(
            self,
            "observed_at_utc",
            _utc_timestamp(self.observed_at_utc, "observed_at_utc"),
        )
        if self.blind_mapping_embedded is not False:
            raise ValueError("judge receipts must not embed the blind-label mapping")
        if not isinstance(self.recursive_closure, RecursiveClosureReceiptRef):
            raise TypeError("recursive_closure must be RecursiveClosureReceiptRef")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> JudgeReceipt:
        data = _record_payload(cls, payload)
        return cls(
            judge_receipt_id=data["judge_receipt_id"],
            blinded_bundle_sha256=data["blinded_bundle_sha256"],
            rubric_sha256=data["rubric_sha256"],
            scorer_provider_id=data["scorer_provider_id"],
            scorer_identity=data["scorer_identity"],
            scorer_config_sha256=data["scorer_config_sha256"],
            score_artifact_sha256=data["score_artifact_sha256"],
            observed_at_utc=data["observed_at_utc"],
            blind_mapping_embedded=data["blind_mapping_embedded"],
            recursive_closure=RecursiveClosureReceiptRef.from_dict(data["recursive_closure"]),
        )


@dataclass(frozen=True, slots=True)
class BlindLabelAssignment(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_blind_label_assignment_v1"

    blind_label: str
    arm_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "blind_label", _identifier(self.blind_label, "blind_label"))
        arm_id = _identifier(self.arm_id, "arm_id")
        if not _ARM_ID_RE.fullmatch(arm_id):
            raise ValueError("arm_id must be anonymized")
        object.__setattr__(self, "arm_id", arm_id)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BlindLabelAssignment:
        data = _record_payload(cls, payload)
        return cls(blind_label=data["blind_label"], arm_id=data["arm_id"])


@dataclass(frozen=True, slots=True)
class BlindLabelMapping(_BenchmarkRecord):
    """Confidential scorer input, always supplied separately from corpus/arms."""

    SCHEMA_VERSION = "benchmark_blind_label_mapping_v1"

    mapping_id: str
    assignments: tuple[BlindLabelAssignment, ...]
    mapping_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "mapping_id", _identifier(self.mapping_id, "mapping_id"))
        assignments = tuple(sorted(self.assignments, key=lambda item: item.blind_label))
        if not assignments or any(
            not isinstance(item, BlindLabelAssignment) for item in assignments
        ):
            raise TypeError("assignments must contain BlindLabelAssignment values")
        if len({item.blind_label for item in assignments}) != len(assignments):
            raise ValueError("blind labels must be unique")
        if len({item.arm_id for item in assignments}) != len(assignments):
            raise ValueError("each anonymized arm may be assigned only once")
        object.__setattr__(self, "assignments", assignments)
        object.__setattr__(self, "mapping_sha256", _digest(self.mapping_sha256, "mapping_sha256"))
        actual = sha256(_canonical_json_bytes([item.as_dict() for item in assignments])).hexdigest()
        if actual != self.mapping_sha256:
            raise ValueError("mapping_sha256 does not match assignments")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> BlindLabelMapping:
        data = _record_payload(cls, payload)
        return cls(
            mapping_id=data["mapping_id"],
            assignments=tuple(BlindLabelAssignment.from_dict(item) for item in data["assignments"]),
            mapping_sha256=data["mapping_sha256"],
        )


def validate_blind_label_mapping(
    corpus: SealedPublicCorpus, *, scorer_mapping: BlindLabelMapping
) -> None:
    """Validate separate scorer input without storing or applying it."""

    if not isinstance(corpus, SealedPublicCorpus):
        raise TypeError("corpus must be SealedPublicCorpus")
    if not isinstance(scorer_mapping, BlindLabelMapping):
        raise TypeError("scorer_mapping must be supplied separately")
    expected = {item.arm_id for item in corpus.anonymized_arms}
    received = {item.arm_id for item in scorer_mapping.assignments}
    if received != expected:
        raise ValueError(
            "scorer mapping must cover every anonymized arm exactly once; "
            f"missing={sorted(expected - received)!r}, "
            f"extra={sorted(received - expected)!r}"
        )


def validate_arm_prompt_receipt(corpus: SealedPublicCorpus, receipt: ArmPromptReceipt) -> None:
    """Validate hash bindings only; never render or execute the prompt."""

    if not isinstance(corpus, SealedPublicCorpus):
        raise TypeError("corpus must be SealedPublicCorpus")
    if not isinstance(receipt, ArmPromptReceipt):
        raise TypeError("receipt must be ArmPromptReceipt")
    blockers: list[str] = []
    if receipt.corpus_sha256 != corpus.content_sha256:
        blockers.append("corpus_sha256_mismatch")
    cases = {item.case_id: item for item in corpus.cases}
    case = cases.get(receipt.case_id)
    if case is None:
        blockers.append("unknown_case_id")
    elif receipt.case_prompt_sha256 != case.prompt_sha256:
        blockers.append("case_prompt_sha256_mismatch")
    if receipt.arm_id not in {item.arm_id for item in corpus.anonymized_arms}:
        blockers.append("unknown_arm_id")
    if blockers:
        raise ValueError(f"invalid arm prompt receipt: {sorted(blockers)!r}")


@dataclass(frozen=True, slots=True)
class HardGateRequirement(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_hard_gate_requirement_v1"

    gate_key: str
    domain: GateDomain
    maximum_critical_errors: int
    compensable_by_prose_quality: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "gate_key", _identifier(self.gate_key, "gate_key"))
        object.__setattr__(self, "domain", GateDomain(self.domain))
        object.__setattr__(
            self,
            "maximum_critical_errors",
            _nonnegative_int(self.maximum_critical_errors, "maximum_critical_errors"),
        )
        if self.maximum_critical_errors != 0:
            raise ValueError("critical benchmark gates require zero errors")
        if self.compensable_by_prose_quality is not False:
            raise ValueError("critical gates are noncompensatory")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> HardGateRequirement:
        data = _record_payload(cls, payload)
        return cls(
            gate_key=data["gate_key"],
            domain=GateDomain(data["domain"]),
            maximum_critical_errors=data["maximum_critical_errors"],
            compensable_by_prose_quality=data["compensable_by_prose_quality"],
        )


@dataclass(frozen=True, slots=True)
class NonCompensatoryGateContract(_BenchmarkRecord):
    """Preregistered gates only; this record never evaluates or admits an arm."""

    SCHEMA_VERSION = "benchmark_noncompensatory_gate_contract_v1"

    contract_id: str
    hard_gates: tuple[HardGateRequirement, ...]
    required_superiority_endpoint_keys: tuple[str, ...]
    exact_keyed_correctness_compensable: bool
    safe_no_change_required: bool
    held_out_family_required: bool
    seed_order_stability_required: bool
    admission_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract_id", _identifier(self.contract_id, "contract_id"))
        hard_gates = tuple(sorted(self.hard_gates, key=lambda item: item.gate_key))
        if any(not isinstance(item, HardGateRequirement) for item in hard_gates):
            raise TypeError("hard_gates must contain HardGateRequirement values")
        if len({item.gate_key for item in hard_gates}) != len(hard_gates):
            raise ValueError("hard gate keys must be unique")
        if {item.domain for item in hard_gates} != set(GateDomain):
            raise ValueError("hard gates must cover every critical gate domain")
        object.__setattr__(self, "hard_gates", hard_gates)
        object.__setattr__(
            self,
            "required_superiority_endpoint_keys",
            _identifier_tuple(
                self.required_superiority_endpoint_keys,
                "required_superiority_endpoint_keys",
                nonempty=True,
            ),
        )
        if self.exact_keyed_correctness_compensable is not False:
            raise ValueError("exact keyed correctness is noncompensatory")
        if not (
            self.safe_no_change_required
            and self.held_out_family_required
            and self.seed_order_stability_required
        ):
            raise ValueError("no-change, held-out, and seed/order gates are required")
        if self.admission_authorized is not False:
            raise ValueError("a gate contract cannot authorize admission")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> NonCompensatoryGateContract:
        data = _record_payload(cls, payload)
        return cls(
            contract_id=data["contract_id"],
            hard_gates=tuple(HardGateRequirement.from_dict(item) for item in data["hard_gates"]),
            required_superiority_endpoint_keys=tuple(data["required_superiority_endpoint_keys"]),
            exact_keyed_correctness_compensable=data["exact_keyed_correctness_compensable"],
            safe_no_change_required=data["safe_no_change_required"],
            held_out_family_required=data["held_out_family_required"],
            seed_order_stability_required=data["seed_order_stability_required"],
            admission_authorized=data["admission_authorized"],
        )


@dataclass(frozen=True, slots=True)
class PerformanceMetricRequirement(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_performance_metric_requirement_v1"

    metric: PerformanceMetric
    unit: str
    comparator: PerformanceComparator
    bound: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric", PerformanceMetric(self.metric))
        object.__setattr__(self, "unit", _identifier(self.unit, "unit"))
        object.__setattr__(self, "comparator", PerformanceComparator(self.comparator))
        object.__setattr__(self, "bound", _finite_nonnegative(self.bound, "bound"))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PerformanceMetricRequirement:
        data = _record_payload(cls, payload)
        return cls(
            metric=PerformanceMetric(data["metric"]),
            unit=data["unit"],
            comparator=PerformanceComparator(data["comparator"]),
            bound=data["bound"],
        )


@dataclass(frozen=True, slots=True)
class ResourcePerformanceContract(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_resource_performance_contract_v1"

    contract_id: str
    requirements: tuple[PerformanceMetricRequirement, ...]
    predecessor_receipt_sha256: str
    recursive_closure_required: bool
    unsafe_quality_tradeoff_allowed: bool
    admission_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract_id", _identifier(self.contract_id, "contract_id"))
        requirements = tuple(sorted(self.requirements, key=lambda item: item.metric.value))
        if any(not isinstance(item, PerformanceMetricRequirement) for item in requirements):
            raise TypeError("requirements must contain PerformanceMetricRequirement values")
        if {item.metric for item in requirements} != set(PerformanceMetric):
            raise ValueError("requirements must cover every performance metric")
        object.__setattr__(self, "requirements", requirements)
        object.__setattr__(
            self,
            "predecessor_receipt_sha256",
            _digest(self.predecessor_receipt_sha256, "predecessor_receipt_sha256"),
        )
        if self.recursive_closure_required is not True:
            raise ValueError("performance measurement requires recursive closure binding")
        if self.unsafe_quality_tradeoff_allowed is not False:
            raise ValueError("performance cannot compensate for an unsafe answer")
        if self.admission_authorized is not False:
            raise ValueError("performance contracts cannot authorize admission")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ResourcePerformanceContract:
        data = _record_payload(cls, payload)
        return cls(
            contract_id=data["contract_id"],
            requirements=tuple(
                PerformanceMetricRequirement.from_dict(item) for item in data["requirements"]
            ),
            predecessor_receipt_sha256=data["predecessor_receipt_sha256"],
            recursive_closure_required=data["recursive_closure_required"],
            unsafe_quality_tradeoff_allowed=data["unsafe_quality_tradeoff_allowed"],
            admission_authorized=data["admission_authorized"],
        )


@dataclass(frozen=True, slots=True)
class PerformanceObservation(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_performance_observation_v1"

    metric: PerformanceMetric
    unit: str
    value: float
    sample_count: int
    conditions_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric", PerformanceMetric(self.metric))
        object.__setattr__(self, "unit", _identifier(self.unit, "unit"))
        object.__setattr__(self, "value", _finite_nonnegative(self.value, "value"))
        sample_count = _nonnegative_int(self.sample_count, "sample_count")
        if sample_count == 0:
            raise ValueError("sample_count must be positive")
        object.__setattr__(self, "sample_count", sample_count)
        object.__setattr__(
            self, "conditions_sha256", _digest(self.conditions_sha256, "conditions_sha256")
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PerformanceObservation:
        data = _record_payload(cls, payload)
        return cls(
            metric=PerformanceMetric(data["metric"]),
            unit=data["unit"],
            value=data["value"],
            sample_count=data["sample_count"],
            conditions_sha256=data["conditions_sha256"],
        )


@dataclass(frozen=True, slots=True)
class ResourcePerformanceReceipt(_BenchmarkRecord):
    SCHEMA_VERSION = "benchmark_resource_performance_receipt_v1"

    receipt_id: str
    contract: ResourcePerformanceContract
    run_receipt_sha256s: tuple[str, ...]
    observations: tuple[PerformanceObservation, ...]
    status: ReceiptStatus
    observed_at_utc: str
    recursive_closure: RecursiveClosureReceiptRef
    admission_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "receipt_id", _identifier(self.receipt_id, "receipt_id"))
        if not isinstance(self.contract, ResourcePerformanceContract):
            raise TypeError("contract must be a ResourcePerformanceContract")
        object.__setattr__(
            self,
            "run_receipt_sha256s",
            _digest_tuple(self.run_receipt_sha256s, "run_receipt_sha256s", nonempty=True),
        )
        observations = tuple(sorted(self.observations, key=lambda item: item.metric.value))
        if any(not isinstance(item, PerformanceObservation) for item in observations):
            raise TypeError("observations must contain PerformanceObservation values")
        if {item.metric for item in observations} != set(PerformanceMetric):
            raise ValueError("receipt must observe every required performance metric")
        if len(observations) != len(PerformanceMetric):
            raise ValueError("receipt must observe each performance metric exactly once")
        object.__setattr__(self, "observations", observations)
        requirements = {item.metric: item for item in self.contract.requirements}
        violations: list[str] = []
        for observation in observations:
            requirement = requirements[observation.metric]
            if observation.unit != requirement.unit:
                raise ValueError(
                    f"observation unit does not match contract for {observation.metric.value}"
                )
            passes = (
                observation.value <= requirement.bound
                if requirement.comparator is PerformanceComparator.AT_MOST
                else observation.value >= requirement.bound
            )
            if not passes:
                violations.append(observation.metric.value)
        expected_status = ReceiptStatus.PASS if not violations else ReceiptStatus.FAIL
        status = ReceiptStatus(self.status)
        if status is not expected_status:
            raise ValueError(
                "performance receipt status does not match contract observations; "
                f"violations={violations!r}"
            )
        object.__setattr__(self, "status", status)
        object.__setattr__(
            self,
            "observed_at_utc",
            _utc_timestamp(self.observed_at_utc, "observed_at_utc"),
        )
        if not isinstance(self.recursive_closure, RecursiveClosureReceiptRef):
            raise TypeError("recursive_closure must be RecursiveClosureReceiptRef")
        if self.admission_authorized is not False:
            raise ValueError("a performance receipt cannot authorize admission")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ResourcePerformanceReceipt:
        data = _record_payload(cls, payload)
        return cls(
            receipt_id=data["receipt_id"],
            contract=ResourcePerformanceContract.from_dict(data["contract"]),
            run_receipt_sha256s=tuple(data["run_receipt_sha256s"]),
            observations=tuple(
                PerformanceObservation.from_dict(item) for item in data["observations"]
            ),
            status=ReceiptStatus(data["status"]),
            observed_at_utc=data["observed_at_utc"],
            recursive_closure=RecursiveClosureReceiptRef.from_dict(data["recursive_closure"]),
            admission_authorized=data["admission_authorized"],
        )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _assert_public_keys_only(value: Any) -> None:
    if isinstance(value, Mapping):
        forbidden = set(value) & FORBIDDEN_PUBLIC_KEY_NAMES
        if forbidden:
            raise ValueError(f"public corpus contains scorer-only keys: {sorted(forbidden)!r}")
        for item in value.values():
            _assert_public_keys_only(item)
    elif isinstance(value, list):
        for item in value:
            _assert_public_keys_only(item)


def validate_corpus_coverage(corpus: SealedPublicCorpus) -> None:
    """Check the preregistered public coverage without scoring any case."""

    families = {item.family_key for item in corpus.cases}
    missing_families = MANDATORY_FAMILY_KEYS - families
    tags = {tag for item in corpus.cases for tag in item.challenge_tags}
    missing_tags = MANDATORY_CHALLENGE_TAGS - tags
    partitions = {item.partition for item in corpus.cases}
    blockers: list[str] = []
    if missing_families:
        blockers.append(f"missing families {sorted(missing_families)!r}")
    if missing_tags:
        blockers.append(f"missing challenge tags {sorted(missing_tags)!r}")
    if partitions != set(CorpusPartition):
        blockers.append("both cross_family and held_out partitions are required")
    if blockers:
        raise ValueError("; ".join(blockers))


def load_sealed_public_corpus(
    fixture_path: str | Path, digest_path: str | Path
) -> SealedPublicCorpus:
    """Load the exact sealed fixture after byte hash and closed-schema checks."""

    fixture_bytes = Path(fixture_path).read_bytes()
    expected_text = Path(digest_path).read_text(encoding="ascii").strip()
    expected_sha256 = _digest(expected_text, "fixture_sha256")
    actual_sha256 = sha256(fixture_bytes).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError(
            "sealed benchmark fixture SHA-256 mismatch; "
            f"expected={expected_sha256}, actual={actual_sha256}"
        )
    payload = json.loads(fixture_bytes.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(payload, Mapping):
        raise TypeError("public corpus fixture must contain a JSON object")
    _assert_public_keys_only(payload)
    corpus = SealedPublicCorpus.from_dict(payload)
    validate_corpus_coverage(corpus)
    return corpus


__all__ = [
    "AnonymizedArm",
    "ArmPromptReceipt",
    "BenchmarkCase",
    "BenchmarkRunReceipt",
    "BlindLabelAssignment",
    "BlindLabelMapping",
    "CorpusPartition",
    "FORBIDDEN_PUBLIC_KEY_NAMES",
    "GateDomain",
    "HardGateRequirement",
    "InvariantRequirements",
    "JudgeReceipt",
    "MANDATORY_CHALLENGE_TAGS",
    "MANDATORY_FAMILY_KEYS",
    "NonCompensatoryGateContract",
    "PUBLIC_AUTHORITY_EXCLUSIONS",
    "PerformanceComparator",
    "PerformanceMetric",
    "PerformanceMetricRequirement",
    "PerformanceObservation",
    "ReceiptStatus",
    "RecursiveClosureReceiptRef",
    "ResourcePerformanceContract",
    "ResourcePerformanceReceipt",
    "RunStatus",
    "SealedPublicCorpus",
    "load_sealed_public_corpus",
    "validate_blind_label_mapping",
    "validate_arm_prompt_receipt",
    "validate_corpus_coverage",
]
