"""OpenAI-only hybrid compute routing for formulation-intelligence work.

The router minimizes verified wall-clock time rather than maximizing worker
count.  It never grants repository, scientific, sensory, safety, or release
authority.  Dirty-file writes, Git integration, secrets, irreversible actions,
and final adjudication remain with the local parent.  Cloud work requires a
frozen packet and must still be verified locally.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass, fields
from enum import Enum
from hashlib import sha256
from typing import Any, ClassVar, Iterable, Mapping, cast

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _text(value: object, field_name: str, *, casefold: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    if not normalized:
        raise ValueError(f"{field_name} must be nonblank text")
    return normalized.casefold() if casefold else normalized


def _identifier(value: object, field_name: str) -> str:
    return _text(value, field_name, casefold=True)


def _seconds(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a finite nonnegative number")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0:
        raise ValueError(f"{field_name} must be a finite nonnegative number")
    return normalized


def _unique_sorted(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized, key=lambda item: (item.casefold(), item)))


def _primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, _CanonicalRecord):
        return value.as_dict()
    if isinstance(value, Mapping):
        return {
            str(key): _primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_primitive(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON forbids non-finite floats")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"{type(value).__name__} is not canonically serializable")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _primitive(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _closed_payload(
    payload: Mapping[str, Any],
    *,
    schema_version: str,
    record_type: type,
) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    expected = {"schema_version", *(item.name for item in fields(record_type))}
    received = set(payload)
    if received != expected:
        raise ValueError(
            f"{schema_version} payload does not match the closed schema; "
            f"missing={sorted(expected - received)!r}, "
            f"extra={sorted(received - expected)!r}"
        )
    if payload["schema_version"] != schema_version:
        raise ValueError(
            f"schema_version must be {schema_version!r}, "
            f"received {payload['schema_version']!r}"
        )
    return payload


class _CanonicalRecord:
    SCHEMA_VERSION: ClassVar[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{
                item.name: _primitive(getattr(self, item.name))
                for item in fields(cast(Any, self))
            },
        }

    @property
    def content_sha256(self) -> str:
        return sha256(_canonical_bytes(self.as_dict())).hexdigest()


class WorkKind(str, Enum):
    PRIMARY_SOURCE_RESEARCH = "primary_source_research"
    OMISSION_AUDIT = "omission_audit"
    MANIFEST_COMPARISON = "manifest_comparison"
    IMPLEMENTATION_DRAFT = "implementation_draft"
    BENCHMARK_PACKET_DESIGN = "benchmark_packet_design"
    REPOSITORY_IMPLEMENTATION = "repository_implementation"
    TEST_VERIFICATION = "test_verification"
    GIT_INTEGRATION = "git_integration"
    FINAL_ADJUDICATION = "final_adjudication"


class ComputeRoute(str, Enum):
    LOCAL_PARENT = "local_parent"
    LOCAL_NATIVE_SUBAGENT = "local_native_subagent"
    CHATGPT_WORK_CLOUD = "chatgpt_work_cloud"
    CODEX_CLOUD_REPOSITORY = "codex_cloud_repository"
    HOLD = "hold"


class RoutingDisposition(str, Enum):
    GO = "go"
    HOLD = "hold"


@dataclass(frozen=True, slots=True)
class ComputeRoutingPolicy(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "perfume_chem_compute_routing_policy_v1"

    provider: str = "openai"
    reasoning_level: str = "xhigh"
    max_active_cloud_lanes: int = 3
    minimum_net_time_saved_seconds: float = 60.0
    require_frozen_cloud_inputs: bool = True
    local_parent_is_final_acceptor: bool = True
    cloud_can_grant_repository_acceptance: bool = False
    cloud_can_grant_scientific_authority: bool = False
    cloud_can_grant_safety_or_release: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", _identifier(self.provider, "provider"))
        object.__setattr__(
            self,
            "reasoning_level",
            _identifier(self.reasoning_level, "reasoning_level"),
        )
        if self.provider != "openai":
            raise ValueError("only the OpenAI provider is permitted")
        if self.reasoning_level != "xhigh":
            raise ValueError("the current cloud comparison standard is xhigh")
        if isinstance(self.max_active_cloud_lanes, bool) or not isinstance(
            self.max_active_cloud_lanes, int
        ):
            raise TypeError("max_active_cloud_lanes must be an integer")
        if self.max_active_cloud_lanes < 0:
            raise ValueError("max_active_cloud_lanes must be nonnegative")
        object.__setattr__(
            self,
            "minimum_net_time_saved_seconds",
            _seconds(
                self.minimum_net_time_saved_seconds,
                "minimum_net_time_saved_seconds",
            ),
        )
        if not self.local_parent_is_final_acceptor:
            raise ValueError("the local parent must remain final acceptor")
        if (
            self.cloud_can_grant_repository_acceptance
            or self.cloud_can_grant_scientific_authority
            or self.cloud_can_grant_safety_or_release
        ):
            raise ValueError("cloud routing cannot mint final authority")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ComputeRoutingPolicy:
        data = _closed_payload(
            payload,
            schema_version=cls.SCHEMA_VERSION,
            record_type=cls,
        )
        return cls(
            provider=data["provider"],
            reasoning_level=data["reasoning_level"],
            max_active_cloud_lanes=data["max_active_cloud_lanes"],
            minimum_net_time_saved_seconds=data[
                "minimum_net_time_saved_seconds"
            ],
            require_frozen_cloud_inputs=data["require_frozen_cloud_inputs"],
            local_parent_is_final_acceptor=data[
                "local_parent_is_final_acceptor"
            ],
            cloud_can_grant_repository_acceptance=data[
                "cloud_can_grant_repository_acceptance"
            ],
            cloud_can_grant_scientific_authority=data[
                "cloud_can_grant_scientific_authority"
            ],
            cloud_can_grant_safety_or_release=data[
                "cloud_can_grant_safety_or_release"
            ],
        )


@dataclass(frozen=True, slots=True)
class WorkPacket(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "perfume_chem_compute_work_packet_v1"

    packet_id: str
    work_kind: WorkKind
    summary: str
    frozen_input_refs: tuple[str, ...]
    write_paths: tuple[str, ...]
    semantic_contracts: tuple[str, ...]
    expected_local_seconds: float
    expected_remote_seconds: float
    context_transfer_seconds: float
    coordination_seconds: float
    local_verification_seconds: float
    reads_live_dirty_state: bool
    writes_repository: bool
    requires_git_state: bool
    contains_secrets: bool
    irreversible_action: bool
    architecture_adjudication: bool
    scientific_adjudication: bool
    safety_or_release_authority: bool
    parallelizable: bool
    cloud_repository_bound: bool
    exact_commit_sha: str | None
    isolated_cloud_branch: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "packet_id", _identifier(self.packet_id, "packet_id"))
        object.__setattr__(self, "work_kind", WorkKind(self.work_kind))
        object.__setattr__(self, "summary", _text(self.summary, "summary"))
        object.__setattr__(
            self,
            "frozen_input_refs",
            _unique_sorted(self.frozen_input_refs, "frozen_input_refs"),
        )
        object.__setattr__(
            self, "write_paths", _unique_sorted(self.write_paths, "write_paths")
        )
        object.__setattr__(
            self,
            "semantic_contracts",
            _unique_sorted(self.semantic_contracts, "semantic_contracts"),
        )
        for field_name in (
            "expected_local_seconds",
            "expected_remote_seconds",
            "context_transfer_seconds",
            "coordination_seconds",
            "local_verification_seconds",
        ):
            object.__setattr__(self, field_name, _seconds(getattr(self, field_name), field_name))
        if self.writes_repository != bool(self.write_paths):
            raise ValueError("writes_repository must agree with write_paths")
        if self.exact_commit_sha is not None:
            digest = _identifier(self.exact_commit_sha, "exact_commit_sha")
            if not _SHA256_RE.fullmatch(digest) and not re.fullmatch(
                r"[0-9a-f]{40}", digest
            ):
                raise ValueError("exact_commit_sha must be a Git SHA-1 or SHA-256")
            object.__setattr__(self, "exact_commit_sha", digest)
        if self.isolated_cloud_branch is not None:
            object.__setattr__(
                self,
                "isolated_cloud_branch",
                _text(self.isolated_cloud_branch, "isolated_cloud_branch"),
            )
        if self.cloud_repository_bound and (
            self.exact_commit_sha is None or self.isolated_cloud_branch is None
        ):
            raise ValueError(
                "cloud repository work requires an exact commit and isolated branch"
            )
        if not self.cloud_repository_bound and (
            self.exact_commit_sha is not None or self.isolated_cloud_branch is not None
        ):
            raise ValueError(
                "commit and cloud branch require cloud_repository_bound=True"
            )

    @property
    def estimated_remote_total_seconds(self) -> float:
        return (
            self.expected_remote_seconds
            + self.context_transfer_seconds
            + self.coordination_seconds
            + self.local_verification_seconds
        )

    @property
    def estimated_net_time_saved_seconds(self) -> float:
        return self.expected_local_seconds - self.estimated_remote_total_seconds

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> WorkPacket:
        data = _closed_payload(
            payload,
            schema_version=cls.SCHEMA_VERSION,
            record_type=cls,
        )
        return cls(
            packet_id=data["packet_id"],
            work_kind=WorkKind(data["work_kind"]),
            summary=data["summary"],
            frozen_input_refs=tuple(data["frozen_input_refs"]),
            write_paths=tuple(data["write_paths"]),
            semantic_contracts=tuple(data["semantic_contracts"]),
            expected_local_seconds=data["expected_local_seconds"],
            expected_remote_seconds=data["expected_remote_seconds"],
            context_transfer_seconds=data["context_transfer_seconds"],
            coordination_seconds=data["coordination_seconds"],
            local_verification_seconds=data["local_verification_seconds"],
            reads_live_dirty_state=data["reads_live_dirty_state"],
            writes_repository=data["writes_repository"],
            requires_git_state=data["requires_git_state"],
            contains_secrets=data["contains_secrets"],
            irreversible_action=data["irreversible_action"],
            architecture_adjudication=data["architecture_adjudication"],
            scientific_adjudication=data["scientific_adjudication"],
            safety_or_release_authority=data["safety_or_release_authority"],
            parallelizable=data["parallelizable"],
            cloud_repository_bound=data["cloud_repository_bound"],
            exact_commit_sha=data["exact_commit_sha"],
            isolated_cloud_branch=data["isolated_cloud_branch"],
        )


@dataclass(frozen=True, slots=True)
class ComputeRoutingDecision(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "perfume_chem_compute_routing_decision_v1"

    packet_id: str
    route: ComputeRoute
    disposition: RoutingDisposition
    estimated_net_time_saved_seconds: float
    reason_codes: tuple[str, ...]
    cloud_compute_authorized: bool
    repository_write_authorized: bool
    local_verification_required: bool
    final_acceptance_local: bool
    provider: str
    reasoning_level: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "packet_id", _identifier(self.packet_id, "packet_id"))
        object.__setattr__(self, "route", ComputeRoute(self.route))
        object.__setattr__(self, "disposition", RoutingDisposition(self.disposition))
        if isinstance(self.estimated_net_time_saved_seconds, bool) or not isinstance(
            self.estimated_net_time_saved_seconds, (int, float)
        ):
            raise TypeError("estimated_net_time_saved_seconds must be finite")
        net = float(self.estimated_net_time_saved_seconds)
        if not math.isfinite(net):
            raise ValueError("estimated_net_time_saved_seconds must be finite")
        object.__setattr__(self, "estimated_net_time_saved_seconds", net)
        object.__setattr__(
            self, "reason_codes", _unique_sorted(self.reason_codes, "reason_codes")
        )
        object.__setattr__(self, "provider", _identifier(self.provider, "provider"))
        object.__setattr__(
            self,
            "reasoning_level",
            _identifier(self.reasoning_level, "reasoning_level"),
        )
        if self.repository_write_authorized:
            raise ValueError("routing never authorizes a repository write")
        if not self.local_verification_required or not self.final_acceptance_local:
            raise ValueError("local verification and final acceptance are mandatory")
        expected_cloud = self.route in {
            ComputeRoute.CHATGPT_WORK_CLOUD,
            ComputeRoute.CODEX_CLOUD_REPOSITORY,
        }
        if self.cloud_compute_authorized != expected_cloud:
            raise ValueError("cloud_compute_authorized disagrees with route")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ComputeRoutingDecision:
        data = _closed_payload(
            payload,
            schema_version=cls.SCHEMA_VERSION,
            record_type=cls,
        )
        return cls(
            packet_id=data["packet_id"],
            route=ComputeRoute(data["route"]),
            disposition=RoutingDisposition(data["disposition"]),
            estimated_net_time_saved_seconds=data[
                "estimated_net_time_saved_seconds"
            ],
            reason_codes=tuple(data["reason_codes"]),
            cloud_compute_authorized=data["cloud_compute_authorized"],
            repository_write_authorized=data["repository_write_authorized"],
            local_verification_required=data["local_verification_required"],
            final_acceptance_local=data["final_acceptance_local"],
            provider=data["provider"],
            reasoning_level=data["reasoning_level"],
        )


def _decision(
    packet: WorkPacket,
    policy: ComputeRoutingPolicy,
    *,
    route: ComputeRoute,
    disposition: RoutingDisposition = RoutingDisposition.GO,
    reason_codes: Iterable[str],
) -> ComputeRoutingDecision:
    return ComputeRoutingDecision(
        packet_id=packet.packet_id,
        route=route,
        disposition=disposition,
        estimated_net_time_saved_seconds=packet.estimated_net_time_saved_seconds,
        reason_codes=tuple(reason_codes),
        cloud_compute_authorized=route
        in {ComputeRoute.CHATGPT_WORK_CLOUD, ComputeRoute.CODEX_CLOUD_REPOSITORY},
        repository_write_authorized=False,
        local_verification_required=True,
        final_acceptance_local=policy.local_parent_is_final_acceptor,
        provider=policy.provider,
        reasoning_level=policy.reasoning_level,
    )


def route_work_packet(
    packet: WorkPacket,
    policy: ComputeRoutingPolicy | None = None,
) -> ComputeRoutingDecision:
    """Choose the fastest evidence-safe surface for one bounded packet."""

    active_policy = policy or ComputeRoutingPolicy()
    if (
        packet.contains_secrets
        or packet.irreversible_action
        or packet.architecture_adjudication
        or packet.scientific_adjudication
        or packet.safety_or_release_authority
        or packet.work_kind is WorkKind.FINAL_ADJUDICATION
    ):
        return _decision(
            packet,
            active_policy,
            route=ComputeRoute.LOCAL_PARENT,
            reason_codes=("LOCAL_FINAL_AUTHORITY_REQUIRED",),
        )

    if packet.reads_live_dirty_state or packet.requires_git_state:
        if packet.writes_repository:
            return _decision(
                packet,
                active_policy,
                route=ComputeRoute.LOCAL_PARENT,
                reason_codes=("LIVE_DIRTY_OR_GIT_WRITE_STAYS_LOCAL",),
            )
        return _decision(
            packet,
            active_policy,
            route=(
                ComputeRoute.LOCAL_NATIVE_SUBAGENT
                if packet.parallelizable
                else ComputeRoute.LOCAL_PARENT
            ),
            reason_codes=("LIVE_BYTES_MUST_NOT_BE_SNAPSHOTTED_STALE",),
        )

    frozen = bool(packet.frozen_input_refs)
    if packet.writes_repository:
        if not packet.cloud_repository_bound:
            return _decision(
                packet,
                active_policy,
                route=ComputeRoute.LOCAL_PARENT,
                reason_codes=("CLOUD_REPOSITORY_NOT_HASH_BOUND",),
            )
        if active_policy.require_frozen_cloud_inputs and not frozen:
            return _decision(
                packet,
                active_policy,
                route=ComputeRoute.HOLD,
                disposition=RoutingDisposition.HOLD,
                reason_codes=("CLOUD_INPUTS_NOT_FROZEN",),
            )
        if (
            packet.parallelizable
            and packet.estimated_net_time_saved_seconds
            >= active_policy.minimum_net_time_saved_seconds
        ):
            return _decision(
                packet,
                active_policy,
                route=ComputeRoute.CODEX_CLOUD_REPOSITORY,
                reason_codes=("HASH_BOUND_ISOLATED_CLOUD_DRAFT_SAVES_TIME",),
            )
        return _decision(
            packet,
            active_policy,
            route=ComputeRoute.LOCAL_PARENT,
            reason_codes=("CLOUD_REPOSITORY_OVERHEAD_EXCEEDS_SAVINGS",),
        )

    if active_policy.require_frozen_cloud_inputs and not frozen:
        return _decision(
            packet,
            active_policy,
            route=(
                ComputeRoute.LOCAL_NATIVE_SUBAGENT
                if packet.parallelizable
                else ComputeRoute.LOCAL_PARENT
            ),
            reason_codes=("CLOUD_INPUTS_NOT_FROZEN",),
        )

    if (
        packet.parallelizable
        and packet.estimated_net_time_saved_seconds
        >= active_policy.minimum_net_time_saved_seconds
    ):
        return _decision(
            packet,
            active_policy,
            route=ComputeRoute.CHATGPT_WORK_CLOUD,
            reason_codes=("FROZEN_READ_ONLY_PACKET_SAVES_NET_TIME",),
        )

    return _decision(
        packet,
        active_policy,
        route=(
            ComputeRoute.LOCAL_NATIVE_SUBAGENT
            if packet.parallelizable
            else ComputeRoute.LOCAL_PARENT
        ),
        reason_codes=("CLOUD_COORDINATION_OVERHEAD_EXCEEDS_SAVINGS",),
    )


def plan_compute_routes(
    packets: Iterable[WorkPacket],
    policy: ComputeRoutingPolicy | None = None,
) -> tuple[ComputeRoutingDecision, ...]:
    """Route packets deterministically, rejecting overlaps and excess lanes."""

    active_policy = policy or ComputeRoutingPolicy()
    packet_list = tuple(packets)
    if len({packet.packet_id for packet in packet_list}) != len(packet_list):
        raise ValueError("packet_id values must be unique")

    overlap_ids: set[str] = set()
    owners_by_lease: dict[str, list[str]] = {}
    for packet in packet_list:
        if not packet.writes_repository:
            continue
        for lease in (*packet.write_paths, *packet.semantic_contracts):
            owners_by_lease.setdefault(lease.casefold(), []).append(packet.packet_id)
    for owners in owners_by_lease.values():
        if len(owners) > 1:
            overlap_ids.update(owners)

    decisions: dict[str, ComputeRoutingDecision] = {}
    for packet in packet_list:
        if packet.packet_id in overlap_ids:
            decisions[packet.packet_id] = _decision(
                packet,
                active_policy,
                route=ComputeRoute.HOLD,
                disposition=RoutingDisposition.HOLD,
                reason_codes=("OVERLAPPING_WRITE_OR_SEMANTIC_LEASE",),
            )
        else:
            decisions[packet.packet_id] = route_work_packet(packet, active_policy)

    cloud_ids = sorted(
        (
            packet.packet_id
            for packet in packet_list
            if decisions[packet.packet_id].cloud_compute_authorized
        ),
        key=lambda packet_id: (
            -decisions[packet_id].estimated_net_time_saved_seconds,
            packet_id,
        ),
    )
    for packet_id in cloud_ids[active_policy.max_active_cloud_lanes :]:
        packet = next(item for item in packet_list if item.packet_id == packet_id)
        decisions[packet_id] = _decision(
            packet,
            active_policy,
            route=(
                ComputeRoute.LOCAL_NATIVE_SUBAGENT
                if packet.parallelizable and not packet.writes_repository
                else ComputeRoute.LOCAL_PARENT
            ),
            reason_codes=("CLOUD_LANE_CAPACITY_RESERVED_FOR_HIGHER_SAVINGS",),
        )

    return tuple(decisions[key] for key in sorted(decisions))
