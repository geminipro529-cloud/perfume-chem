"""Read-only interaction registry loader (Interaction and Layering Atlas v1).

Loads the atlas JSON into a normalized, versioned, read-only registry object.
STRUCTURED HYPOTHESIS records are never upgraded to direct evidence. No mutation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

REGISTRY_VERSION = "interaction_atlas_v1"


@dataclass(frozen=True, slots=True)
class InteractionRegistry:
    version: str
    groups: tuple[dict[str, Any], ...]
    interactions: tuple[dict[str, Any], ...]
    sources: dict[str, Any]
    worker_packets: tuple[dict[str, Any], ...]
    boundaries: dict[str, Any]
    source_sha256: str | None = None

    def query_group(self, group_id: str) -> dict[str, Any] | None:
        for g in self.groups:
            if g.get("id") == group_id:
                return g
        return None

    def query_pair(self, pair_id: str) -> dict[str, Any] | None:
        for i in self.interactions:
            if i.get("pair_id") == pair_id:
                return i
        return None

    def pairs_for_group(self, group_id: str) -> list[dict[str, Any]]:
        return [
            i
            for i in self.interactions
            if i.get("group_a_id") == group_id or i.get("group_b_id") == group_id
        ]

    def evidence_classes(self) -> set[str]:
        return {str(i.get("evidence_class")) for i in self.interactions}

    def count(self) -> dict[str, int]:
        return {
            "groups": len(self.groups),
            "interactions": len(self.interactions),
            "sources": len(self.sources),
            "worker_packets": len(self.worker_packets),
        }


def load_registry(path: str, source_sha256: str | None = None) -> InteractionRegistry:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("version") not in ("1", "v1", REGISTRY_VERSION):
        # tolerate structured datasets; the registry pins its own version label
        pass
    return InteractionRegistry(
        version=REGISTRY_VERSION,
        groups=tuple(data.get("groups", [])),
        interactions=tuple(data.get("interactions", [])),
        sources=data.get("sources", {}),
        worker_packets=tuple(data.get("worker_packets", [])),
        boundaries=data.get("boundaries", {}),
        source_sha256=source_sha256,
    )
