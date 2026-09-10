from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine.formulation_intelligence.compute_routing import (
    ComputeRoute,
    ComputeRoutingDecision,
    ComputeRoutingPolicy,
    RoutingDisposition,
    WorkKind,
    WorkPacket,
    plan_compute_routes,
    route_work_packet,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = (
    ROOT
    / "data"
    / "governance"
    / "openai_cloud_compute_collaboration_registry_20260901.json"
)


def _packet(packet_id: str, **overrides: object) -> WorkPacket:
    payload: dict[str, object] = {
        "packet_id": packet_id,
        "work_kind": WorkKind.PRIMARY_SOURCE_RESEARCH,
        "summary": "Bounded primary-source evidence packet",
        "frozen_input_refs": ("sha256:" + "a" * 64,),
        "write_paths": (),
        "semantic_contracts": (),
        "expected_local_seconds": 1200.0,
        "expected_remote_seconds": 300.0,
        "context_transfer_seconds": 30.0,
        "coordination_seconds": 60.0,
        "local_verification_seconds": 120.0,
        "reads_live_dirty_state": False,
        "writes_repository": False,
        "requires_git_state": False,
        "contains_secrets": False,
        "irreversible_action": False,
        "architecture_adjudication": False,
        "scientific_adjudication": False,
        "safety_or_release_authority": False,
        "parallelizable": True,
        "cloud_repository_bound": False,
        "exact_commit_sha": None,
        "isolated_cloud_branch": None,
    }
    payload.update(overrides)
    return WorkPacket(**payload)  # type: ignore[arg-type]


def test_frozen_independent_research_routes_to_xhigh_openai_cloud() -> None:
    decision = route_work_packet(_packet("research.wood"))

    assert decision.route is ComputeRoute.CHATGPT_WORK_CLOUD
    assert decision.disposition is RoutingDisposition.GO
    assert decision.provider == "openai"
    assert decision.reasoning_level == "xhigh"
    assert decision.cloud_compute_authorized is True
    assert decision.repository_write_authorized is False
    assert decision.local_verification_required is True
    assert decision.final_acceptance_local is True


def test_live_dirty_read_uses_true_local_native_subagent() -> None:
    decision = route_work_packet(
        _packet(
            "audit.live",
            frozen_input_refs=(),
            reads_live_dirty_state=True,
            expected_local_seconds=600.0,
        )
    )

    assert decision.route is ComputeRoute.LOCAL_NATIVE_SUBAGENT
    assert decision.cloud_compute_authorized is False
    assert "LIVE_BYTES_MUST_NOT_BE_SNAPSHOTTED_STALE" in decision.reason_codes


def test_dirty_repository_write_stays_with_local_parent() -> None:
    decision = route_work_packet(
        _packet(
            "write.dirty",
            work_kind=WorkKind.REPOSITORY_IMPLEMENTATION,
            write_paths=("engine/inventory_parser.py",),
            writes_repository=True,
            reads_live_dirty_state=True,
        )
    )

    assert decision.route is ComputeRoute.LOCAL_PARENT
    assert decision.repository_write_authorized is False


@pytest.mark.parametrize(
    "override",
    (
        {"contains_secrets": True},
        {"irreversible_action": True},
        {"architecture_adjudication": True},
        {"scientific_adjudication": True},
        {"safety_or_release_authority": True},
        {"work_kind": WorkKind.FINAL_ADJUDICATION},
    ),
)
def test_non_delegable_authority_stays_with_local_parent(
    override: dict[str, object],
) -> None:
    decision = route_work_packet(_packet("authority.final", **override))

    assert decision.route is ComputeRoute.LOCAL_PARENT
    assert decision.cloud_compute_authorized is False
    assert "LOCAL_FINAL_AUTHORITY_REQUIRED" in decision.reason_codes


def test_hash_bound_isolated_repository_draft_can_use_codex_cloud() -> None:
    decision = route_work_packet(
        _packet(
            "draft.cloud",
            work_kind=WorkKind.IMPLEMENTATION_DRAFT,
            write_paths=("engine/formulation_intelligence/wood_integration.py",),
            writes_repository=True,
            cloud_repository_bound=True,
            exact_commit_sha="b" * 40,
            isolated_cloud_branch="codex/cloud-wood-draft",
        )
    )

    assert decision.route is ComputeRoute.CODEX_CLOUD_REPOSITORY
    assert decision.cloud_compute_authorized is True
    assert decision.repository_write_authorized is False


def test_cloud_repository_binding_requires_commit_and_isolated_branch() -> None:
    with pytest.raises(ValueError, match="exact commit and isolated branch"):
        _packet(
            "draft.invalid",
            write_paths=("engine/example.py",),
            writes_repository=True,
            cloud_repository_bound=True,
        )


def test_coordination_overhead_keeps_small_packet_local() -> None:
    decision = route_work_packet(
        _packet(
            "small.local",
            expected_local_seconds=120.0,
            expected_remote_seconds=60.0,
            context_transfer_seconds=30.0,
            coordination_seconds=40.0,
            local_verification_seconds=30.0,
        )
    )

    assert decision.route is ComputeRoute.LOCAL_NATIVE_SUBAGENT
    assert "CLOUD_COORDINATION_OVERHEAD_EXCEEDS_SAVINGS" in decision.reason_codes


def test_topology_caps_cloud_lanes_by_net_time_saved() -> None:
    policy = ComputeRoutingPolicy(max_active_cloud_lanes=3)
    packets = tuple(
        _packet(
            f"cloud.{index}",
            expected_local_seconds=1200.0 + index,
        )
        for index in range(5)
    )

    decisions = plan_compute_routes(packets, policy)
    cloud = [item for item in decisions if item.cloud_compute_authorized]
    local = [item for item in decisions if not item.cloud_compute_authorized]

    assert len(cloud) == 3
    assert len(local) == 2
    assert all(
        "CLOUD_LANE_CAPACITY_RESERVED_FOR_HIGHER_SAVINGS" in item.reason_codes
        for item in local
    )


def test_overlapping_write_or_semantic_lease_holds_every_conflicting_packet() -> None:
    first = _packet(
        "write.first",
        write_paths=("engine/shared.py",),
        semantic_contracts=("contract.shared",),
        writes_repository=True,
        cloud_repository_bound=True,
        exact_commit_sha="c" * 40,
        isolated_cloud_branch="codex/first",
    )
    second = _packet(
        "write.second",
        write_paths=("engine/other.py",),
        semantic_contracts=("contract.shared",),
        writes_repository=True,
        cloud_repository_bound=True,
        exact_commit_sha="c" * 40,
        isolated_cloud_branch="codex/second",
    )

    decisions = plan_compute_routes((first, second))

    assert all(item.route is ComputeRoute.HOLD for item in decisions)
    assert all(item.disposition is RoutingDisposition.HOLD for item in decisions)
    assert all(
        "OVERLAPPING_WRITE_OR_SEMANTIC_LEASE" in item.reason_codes
        for item in decisions
    )


def test_records_round_trip_with_closed_schema_and_stable_hash() -> None:
    packet = _packet("round.trip")
    decision = route_work_packet(packet)

    restored_packet = WorkPacket.from_dict(packet.as_dict())
    restored_decision = ComputeRoutingDecision.from_dict(decision.as_dict())
    restored_policy = ComputeRoutingPolicy.from_dict(ComputeRoutingPolicy().as_dict())

    assert restored_packet == packet
    assert restored_packet.content_sha256 == packet.content_sha256
    assert restored_decision == decision
    assert restored_decision.content_sha256 == decision.content_sha256
    assert restored_policy == ComputeRoutingPolicy()
    invalid = packet.as_dict()
    invalid["unexpected"] = True
    with pytest.raises(ValueError, match="closed schema"):
        WorkPacket.from_dict(invalid)


def test_historical_cloud_registry_preserves_three_recorded_openai_lanes() -> None:
    # A byte-bound registration record, not a query or assertion of live workers.
    assert hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest() == (
        "9c9b12e123bf70f9b40b2ca95d2e869756119233a742284cc09236a09311b78d"
    )
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert payload["effective_date"] == "2026-09-01"

    assert payload["schema_version"] == "perfume_chem_openai_cloud_collaboration_v1"
    assert payload["provider_policy"]["allowed_provider"] == "openai"
    assert payload["standardization"]["reasoning_level"] == "xhigh"
    assert payload["communication_bus"]["mode"] == "local_parent_relay"
    assert payload["communication_bus"]["hidden_transcript_sharing"] is False
    assert payload["routing_policy"]["max_active_cloud_lanes"] == 3
    assert {item["lane_id"] for item in payload["lanes"]} == {
        "cloud.wood_registry",
        "cloud.floral_architecture",
        "cloud.benchmark_closure",
    }
    assert len({item["task_id"] for item in payload["lanes"]}) == 3
    assert all(item["write_lease"] == "read_only_design_packet" for item in payload["lanes"])
    assert payload["github_handoff"]["status"] == (
        "HOLD_DIRTY_CANONICAL_NOT_MANIFEST_BOUND"
    )
    assert payload["github_handoff"]["cloud_push_or_merge_authorized"] is False
    assert payload["authority_limits"]["local_byte_and_test_verification_required"] is True
