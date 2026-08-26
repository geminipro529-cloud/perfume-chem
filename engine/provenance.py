"""W3C-PROV-shaped provenance records for canonical scientific artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required_text(name: str, value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _aware(name: str, value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return _aware("timestamp", value).isoformat().replace("+00:00", "Z")


def _digest(name: str, value: str) -> str:
    normalized = str(value).lower()
    if not _SHA256.fullmatch(normalized):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return normalized


@dataclass(frozen=True, slots=True)
class Entity:
    entity_id: str
    entity_type: str
    content_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "entity_id", _required_text("entity_id", self.entity_id)
        )
        object.__setattr__(
            self,
            "entity_type",
            _required_text("entity_type", self.entity_type),
        )
        object.__setattr__(
            self,
            "content_sha256",
            _digest("content_sha256", self.content_sha256),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "prov:id": self.entity_id,
            "prov:type": self.entity_type,
            "perfume:contentSha256": self.content_sha256,
        }


@dataclass(frozen=True, slots=True)
class Activity:
    activity_id: str
    activity_type: str
    started_at: datetime
    ended_at: datetime
    parameters: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "activity_id",
            _required_text("activity_id", self.activity_id),
        )
        object.__setattr__(
            self,
            "activity_type",
            _required_text("activity_type", self.activity_type),
        )
        started = _aware("started_at", self.started_at)
        ended = _aware("ended_at", self.ended_at)
        if ended < started:
            raise ValueError("activity ended_at precedes started_at")
        object.__setattr__(self, "started_at", started)
        object.__setattr__(self, "ended_at", ended)
        object.__setattr__(self, "parameters", dict(self.parameters))

    def as_dict(self) -> dict[str, Any]:
        return {
            "prov:id": self.activity_id,
            "prov:type": self.activity_type,
            "prov:startedAtTime": _timestamp(self.started_at),
            "prov:endedAtTime": _timestamp(self.ended_at),
            "perfume:parameters": dict(self.parameters),
        }


@dataclass(frozen=True, slots=True)
class Agent:
    agent_id: str
    agent_type: str
    label: str

    def __post_init__(self) -> None:
        for field_name in ("agent_id", "agent_type", "label"):
            object.__setattr__(
                self,
                field_name,
                _required_text(field_name, getattr(self, field_name)),
            )

    def as_dict(self) -> dict[str, str]:
        return {
            "prov:id": self.agent_id,
            "prov:type": self.agent_type,
            "prov:label": self.label,
        }


@dataclass(frozen=True, slots=True)
class Generation:
    entity_id: str
    activity_id: str
    generated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "entity_id", _required_text("entity_id", self.entity_id)
        )
        object.__setattr__(
            self,
            "activity_id",
            _required_text("activity_id", self.activity_id),
        )
        object.__setattr__(
            self,
            "generated_at",
            _aware("generated_at", self.generated_at),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "prov:entity": self.entity_id,
            "prov:activity": self.activity_id,
            "prov:atTime": _timestamp(self.generated_at),
        }


@dataclass(frozen=True, slots=True)
class Derivation:
    generated_entity_id: str
    source_entity_id: str
    activity_id: str
    transformation: str

    def __post_init__(self) -> None:
        for field_name in (
            "generated_entity_id",
            "source_entity_id",
            "activity_id",
            "transformation",
        ):
            object.__setattr__(
                self,
                field_name,
                _required_text(field_name, getattr(self, field_name)),
            )

    def as_dict(self) -> dict[str, str]:
        return {
            "prov:generatedEntity": self.generated_entity_id,
            "prov:usedEntity": self.source_entity_id,
            "prov:activity": self.activity_id,
            "perfume:transformation": self.transformation,
        }


@dataclass(frozen=True, slots=True)
class HumanReview:
    state: str
    reviewer_agent_id: str
    reviewed_at: datetime
    rationale: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", _required_text("state", self.state))
        object.__setattr__(
            self,
            "reviewer_agent_id",
            _required_text("reviewer_agent_id", self.reviewer_agent_id),
        )
        object.__setattr__(
            self,
            "reviewed_at",
            _aware("reviewed_at", self.reviewed_at),
        )
        object.__setattr__(
            self,
            "rationale",
            _required_text("rationale", self.rationale),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "state": self.state,
            "reviewer_agent_id": self.reviewer_agent_id,
            "reviewed_at": _timestamp(self.reviewed_at),
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class AIProposalProvenance:
    model_id: str
    instruction_digest: str
    records_read: tuple[str, ...]
    output_record: str
    review_status: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "model_id", _required_text("model_id", self.model_id)
        )
        object.__setattr__(
            self,
            "instruction_digest",
            _digest("instruction_digest", self.instruction_digest),
        )
        object.__setattr__(
            self,
            "records_read",
            tuple(
                _required_text("records_read entry", item)
                for item in self.records_read
            ),
        )
        object.__setattr__(
            self,
            "output_record",
            _required_text("output_record", self.output_record),
        )
        object.__setattr__(
            self,
            "review_status",
            _required_text("review_status", self.review_status),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "instruction_digest": self.instruction_digest,
            "records_read": list(self.records_read),
            "output_record": self.output_record,
            "review_status": self.review_status,
        }


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    schema_version: str
    entities: tuple[Entity, ...]
    activities: tuple[Activity, ...]
    agents: tuple[Agent, ...]
    generations: tuple[Generation, ...]
    derivations: tuple[Derivation, ...]
    software_version: str
    model_version: str | None
    evidence_class: str
    uncertainty: Mapping[str, Any]
    human_review: HumanReview | None

    def __post_init__(self) -> None:
        if self.schema_version != "provenance-v1":
            raise ValueError("unsupported provenance schema")
        entity_ids = _unique_ids(
            "entity", tuple(entity.entity_id for entity in self.entities)
        )
        activity_ids = _unique_ids(
            "activity",
            tuple(activity.activity_id for activity in self.activities),
        )
        agent_ids = _unique_ids(
            "agent", tuple(agent.agent_id for agent in self.agents)
        )
        for generation in self.generations:
            if generation.entity_id not in entity_ids:
                raise ValueError("generation references an unknown entity")
            if generation.activity_id not in activity_ids:
                raise ValueError("generation references an unknown activity")
        for derivation in self.derivations:
            if (
                derivation.generated_entity_id not in entity_ids
                or derivation.source_entity_id not in entity_ids
            ):
                raise ValueError("derivation references an unknown entity")
            if derivation.activity_id not in activity_ids:
                raise ValueError("derivation references an unknown activity")
        if (
            self.human_review is not None
            and self.human_review.reviewer_agent_id not in agent_ids
        ):
            raise ValueError("human review references an unknown agent")
        object.__setattr__(
            self,
            "software_version",
            _required_text("software_version", self.software_version),
        )
        if self.model_version is not None:
            object.__setattr__(
                self,
                "model_version",
                _required_text("model_version", self.model_version),
            )
        object.__setattr__(
            self,
            "evidence_class",
            _required_text("evidence_class", self.evidence_class),
        )
        object.__setattr__(self, "uncertainty", dict(self.uncertainty))

    def source_entities(self, generated_entity_id: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    item.source_entity_id
                    for item in self.derivations
                    if item.generated_entity_id == generated_entity_id
                }
            )
        )

    def as_prov_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "prov:entity": [item.as_dict() for item in self.entities],
            "prov:activity": [item.as_dict() for item in self.activities],
            "prov:agent": [item.as_dict() for item in self.agents],
            "prov:wasGeneratedBy": [
                item.as_dict() for item in self.generations
            ],
            "prov:wasDerivedFrom": [
                item.as_dict() for item in self.derivations
            ],
            "perfume:softwareVersion": self.software_version,
            "perfume:modelVersion": self.model_version,
            "perfume:evidenceClass": self.evidence_class,
            "perfume:uncertainty": dict(self.uncertainty),
        }
        if self.human_review is not None:
            payload["perfume:humanReview"] = self.human_review.as_dict()
        return payload


def _unique_ids(kind: str, values: tuple[str, ...]) -> set[str]:
    normalized = {_required_text(f"{kind}_id", value) for value in values}
    if len(normalized) != len(values):
        raise ValueError(f"duplicate {kind} id")
    return normalized


__all__ = [
    "AIProposalProvenance",
    "Activity",
    "Agent",
    "Derivation",
    "Entity",
    "Generation",
    "HumanReview",
    "ProvenanceRecord",
]
