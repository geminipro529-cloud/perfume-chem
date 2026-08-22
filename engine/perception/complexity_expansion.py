"""Native, non-authoritative contracts for Complex Perfumery expansion maps.

The module validates and compares design-registry records.  It never imports a
formula, mutates inventory, ranks perfume quality, or creates release authority.
External registries remain source ancestry until their rights and admission
receipts are resolved separately.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from engine.calibration.hashing import stable_json_hash

_DIRECTION_ID = re.compile(r"ED-\d{3}\Z")
_DOMAIN_ID = re.compile(r"DX-\d{2}\Z")


class ExpansionPriority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class ExpansionOrigin(str, Enum):
    INHERITED = "INHERITED_V1"
    FRONTIER = "NEW_V2_FRONTIER"


class ExpansionAuditState(str, Enum):
    PASS = "PASS"
    PASS_WITH_REVIEW = "PASS_WITH_REVIEW"
    HOLD = "HOLD"


class ExpansionSaturationState(str, Enum):
    ACTIVE_FRONTIER_REMAINS = "ACTIVE_FRONTIER_REMAINS"
    SATURATED_FOR_DECLARED_SCOPE = "SATURATED_FOR_DECLARED_SCOPE"


def _text(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must not be blank")
    return text


def _sha256(value: object, field_name: str) -> str:
    text = _text(value, field_name).lower()
    if re.fullmatch(r"[0-9a-f]{64}", text) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def _normalize_title(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def _title_similarity(left: str, right: str) -> float:
    left_tokens = set(_normalize_title(left).split())
    right_tokens = set(_normalize_title(right).split())
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


@dataclass(frozen=True, slots=True)
class ExpansionDirection:
    direction_id: str
    domain_id: str
    title: str
    origin: ExpansionOrigin
    current_state: str
    priority: ExpansionPriority
    evidence_ceiling: str
    mechanism_contract: str | None = None
    first_discriminator: str | None = None
    failure_mode: str | None = None
    formula_mutation_authorized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        direction_id = _text(self.direction_id, "direction_id")
        domain_id = _text(self.domain_id, "domain_id")
        if _DIRECTION_ID.fullmatch(direction_id) is None:
            raise ValueError("direction_id must match ED-###")
        if _DOMAIN_ID.fullmatch(domain_id) is None:
            raise ValueError("domain_id must match DX-##")
        object.__setattr__(self, "direction_id", direction_id)
        object.__setattr__(self, "domain_id", domain_id)
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(self, "current_state", _text(self.current_state, "current_state"))
        object.__setattr__(self, "evidence_ceiling", _text(self.evidence_ceiling, "evidence_ceiling"))
        if not isinstance(self.origin, ExpansionOrigin):
            raise TypeError("origin must be an ExpansionOrigin")
        if not isinstance(self.priority, ExpansionPriority):
            raise TypeError("priority must be an ExpansionPriority")
        if self.origin is ExpansionOrigin.FRONTIER:
            for field_name in (
                "mechanism_contract",
                "first_discriminator",
                "failure_mode",
            ):
                value = getattr(self, field_name)
                if value is None:
                    raise ValueError(f"{field_name} is required for a frontier direction")
                object.__setattr__(self, field_name, _text(value, field_name))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ExpansionDirection":
        if value.get("formula_mutation_authorized") is not False:
            raise ValueError("formula_mutation_authorized must remain false")
        try:
            origin = ExpansionOrigin(str(value.get("origin")))
        except ValueError as exc:
            raise ValueError("origin is invalid") from exc
        try:
            priority = ExpansionPriority(str(value.get("priority")))
        except ValueError as exc:
            raise ValueError("priority is invalid") from exc
        return cls(
            direction_id=str(value.get("direction_id") or ""),
            domain_id=str(value.get("domain_id") or ""),
            title=str(value.get("title") or ""),
            origin=origin,
            current_state=str(value.get("current_state") or ""),
            priority=priority,
            evidence_ceiling=str(value.get("evidence_ceiling") or ""),
            mechanism_contract=value.get("mechanism_contract"),
            first_discriminator=value.get("first_discriminator"),
            failure_mode=value.get("failure_mode"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "direction_id": self.direction_id,
            "domain_id": self.domain_id,
            "title": self.title,
            "origin": self.origin.value,
            "current_state": self.current_state,
            "priority": self.priority.value,
            "evidence_ceiling": self.evidence_ceiling,
            "mechanism_contract": self.mechanism_contract,
            "first_discriminator": self.first_discriminator,
            "failure_mode": self.failure_mode,
            "formula_mutation_authorized": self.formula_mutation_authorized,
        }


@dataclass(frozen=True, slots=True)
class ExpansionRegistryAudit:
    state: ExpansionAuditState
    source_package_sha256: str
    direction_count: int
    domain_count: int
    counts_by_domain: Mapping[str, int]
    counts_by_origin: Mapping[str, int]
    counts_by_priority: Mapping[str, int]
    invalid_records: Mapping[str, tuple[str, ...]]
    duplicate_direction_ids: tuple[str, ...]
    duplicate_domain_ids: tuple[str, ...]
    orphan_domain_ids: tuple[str, ...]
    empty_domain_ids: tuple[str, ...]
    exact_title_duplicates: tuple[tuple[str, str], ...]
    semantic_collision_candidates: tuple[tuple[str, str, float], ...]
    source_admission: bool = field(default=False, init=False)
    formula_authority: bool = field(default=False, init=False)
    inventory_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "state": self.state.value,
            "source_package_sha256": self.source_package_sha256,
            "direction_count": self.direction_count,
            "domain_count": self.domain_count,
            "counts_by_domain": dict(self.counts_by_domain),
            "counts_by_origin": dict(self.counts_by_origin),
            "counts_by_priority": dict(self.counts_by_priority),
            "invalid_records": {
                key: list(value) for key, value in self.invalid_records.items()
            },
            "duplicate_direction_ids": list(self.duplicate_direction_ids),
            "duplicate_domain_ids": list(self.duplicate_domain_ids),
            "orphan_domain_ids": list(self.orphan_domain_ids),
            "empty_domain_ids": list(self.empty_domain_ids),
            "exact_title_duplicates": [list(item) for item in self.exact_title_duplicates],
            "semantic_collision_candidates": [
                [left, right, score]
                for left, right, score in self.semantic_collision_candidates
            ],
            "automatic_merges": 0,
            "global_exhaustiveness_claim": False,
            "source_admission": self.source_admission,
            "formula_authority": self.formula_authority,
            "inventory_authority": self.inventory_authority,
            "release_authority": self.release_authority,
        }
        payload["result_sha256"] = stable_json_hash(payload)
        return payload


@dataclass(frozen=True, slots=True)
class ExpansionDiscoveryRound:
    round_id: str
    new_p0_p1_count: int
    source_classes: tuple[str, ...]
    evidence_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "round_id", _text(self.round_id, "round_id"))
        if isinstance(self.new_p0_p1_count, bool) or self.new_p0_p1_count < 0:
            raise ValueError("new_p0_p1_count must be a non-negative integer")
        classes = tuple(
            sorted({_text(item, "source_classes").upper() for item in self.source_classes})
        )
        if not classes:
            raise ValueError("source_classes must not be empty")
        object.__setattr__(self, "source_classes", classes)
        object.__setattr__(
            self,
            "evidence_sha256",
            _sha256(self.evidence_sha256, "evidence_sha256"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "round_id": self.round_id,
            "new_p0_p1_count": self.new_p0_p1_count,
            "source_classes": list(self.source_classes),
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class ExpansionSaturationAssessment:
    state: ExpansionSaturationState
    declared_scope: str
    round_count: int
    last_two_zero_new_p0_p1: bool
    required_source_classes_present: bool
    missing_source_classes: tuple[str, ...]
    input_sha256: str
    global_exhaustiveness_claim: bool = field(default=False, init=False)
    formula_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "state": self.state.value,
            "declared_scope": self.declared_scope,
            "round_count": self.round_count,
            "last_two_zero_new_p0_p1": self.last_two_zero_new_p0_p1,
            "required_source_classes_present": self.required_source_classes_present,
            "missing_source_classes": list(self.missing_source_classes),
            "global_exhaustiveness_claim": self.global_exhaustiveness_claim,
            "reopen_triggers": [
                "new target scope",
                "new physical data",
                "new inventory lot",
                "new primary source",
                "repository state change",
            ],
            "input_sha256": self.input_sha256,
            "formula_authority": self.formula_authority,
            "release_authority": self.release_authority,
        }
        payload["result_sha256"] = stable_json_hash(payload)
        return payload


def assess_bounded_saturation(
    rounds: Sequence[ExpansionDiscoveryRound],
    *,
    declared_scope: str,
) -> ExpansionSaturationAssessment:
    """Close only a declared search scope after two evidence-diverse null rounds."""

    if isinstance(rounds, (str, bytes)) or not isinstance(rounds, Sequence):
        raise TypeError("rounds must be a sequence")
    if any(not isinstance(item, ExpansionDiscoveryRound) for item in rounds):
        raise TypeError("rounds must contain ExpansionDiscoveryRound values")
    round_ids = tuple(item.round_id for item in rounds)
    if len(round_ids) != len(set(round_ids)):
        raise ValueError("round IDs must be unique")
    scope = _text(declared_scope, "declared_scope")
    last_two = tuple(rounds[-2:])
    no_new_high = len(last_two) == 2 and all(
        item.new_p0_p1_count == 0 for item in last_two
    )
    required_sources = {"PROJECT", "PRIMARY", "OFFICIAL_STANDARD_OR_GUIDANCE"}
    observed_sources = {
        source_class for item in rounds for source_class in item.source_classes
    }
    missing_sources = tuple(sorted(required_sources - observed_sources))
    state = (
        ExpansionSaturationState.SATURATED_FOR_DECLARED_SCOPE
        if no_new_high and not missing_sources
        else ExpansionSaturationState.ACTIVE_FRONTIER_REMAINS
    )
    return ExpansionSaturationAssessment(
        state=state,
        declared_scope=scope,
        round_count=len(rounds),
        last_two_zero_new_p0_p1=no_new_high,
        required_source_classes_present=not missing_sources,
        missing_source_classes=missing_sources,
        input_sha256=stable_json_hash(
            {
                "declared_scope": scope,
                "rounds": [item.as_dict() for item in rounds],
            }
        ),
    )


def audit_expansion_registry(
    registry: Mapping[str, Any],
    *,
    source_package_sha256: str,
    semantic_threshold: float = 0.72,
) -> ExpansionRegistryAudit:
    """Validate a registry as design ancestry without admitting its contents."""

    package_sha = _sha256(source_package_sha256, "source_package_sha256")
    if not 0.0 <= semantic_threshold <= 1.0:
        raise ValueError("semantic_threshold must be between zero and one")
    raw_domains = registry.get("domains")
    raw_directions = registry.get("directions")
    if not isinstance(raw_domains, Sequence) or isinstance(raw_domains, (str, bytes)):
        raise ValueError("domains must be a sequence")
    if not isinstance(raw_directions, Sequence) or isinstance(raw_directions, (str, bytes)):
        raise ValueError("directions must be a sequence")

    domain_ids: list[str] = []
    for index, item in enumerate(raw_domains):
        if not isinstance(item, Mapping):
            domain_ids.append(f"INVALID_DOMAIN_{index}")
        else:
            domain_ids.append(str(item.get("domain_id") or ""))
    direction_ids: list[str] = []
    valid: list[ExpansionDirection] = []
    invalid: dict[str, tuple[str, ...]] = {}
    for index, item in enumerate(raw_directions):
        record_id = f"ROW_{index:03d}"
        if not isinstance(item, Mapping):
            invalid[record_id] = ("direction record must be a mapping",)
            direction_ids.append(record_id)
            continue
        record_id = str(item.get("direction_id") or record_id)
        direction_ids.append(record_id)
        try:
            valid.append(ExpansionDirection.from_mapping(item))
        except (TypeError, ValueError) as exc:
            invalid[record_id] = (str(exc),)

    duplicate_directions = tuple(
        sorted(key for key, count in Counter(direction_ids).items() if key and count > 1)
    )
    duplicate_domains = tuple(
        sorted(key for key, count in Counter(domain_ids).items() if key and count > 1)
    )
    known_domains = {item for item in domain_ids if _DOMAIN_ID.fullmatch(item)}
    by_domain = Counter(item.domain_id for item in valid)
    orphan = tuple(sorted(set(by_domain) - known_domains))
    empty = tuple(sorted(known_domains - set(by_domain)))

    exact: list[tuple[str, str]] = []
    semantic: list[tuple[str, str, float]] = []
    for left_index, left in enumerate(valid):
        for right in valid[left_index + 1 :]:
            left_title = _normalize_title(left.title)
            right_title = _normalize_title(right.title)
            if left_title == right_title:
                exact.append((left.direction_id, right.direction_id))
                continue
            score = _title_similarity(left.title, right.title)
            if score >= semantic_threshold:
                semantic.append((left.direction_id, right.direction_id, round(score, 6)))

    hard_failures = bool(
        invalid
        or duplicate_directions
        or duplicate_domains
        or orphan
        or empty
        or exact
    )
    state = (
        ExpansionAuditState.HOLD
        if hard_failures
        else ExpansionAuditState.PASS_WITH_REVIEW
        if semantic
        else ExpansionAuditState.PASS
    )
    return ExpansionRegistryAudit(
        state=state,
        source_package_sha256=package_sha,
        direction_count=len(raw_directions),
        domain_count=len(raw_domains),
        counts_by_domain=dict(sorted(by_domain.items())),
        counts_by_origin=dict(sorted(Counter(item.origin.value for item in valid).items())),
        counts_by_priority=dict(
            sorted(Counter(item.priority.value for item in valid).items())
        ),
        invalid_records=invalid,
        duplicate_direction_ids=duplicate_directions,
        duplicate_domain_ids=duplicate_domains,
        orphan_domain_ids=orphan,
        empty_domain_ids=empty,
        exact_title_duplicates=tuple(exact),
        semantic_collision_candidates=tuple(semantic),
    )


def pareto_experiment_frontier(
    candidates: Iterable[tuple[ExpansionDirection, float, float]],
) -> tuple[ExpansionDirection, ...]:
    """Remove dominated experiment candidates without creating a beauty score."""

    rows = list(candidates)
    priority = {item: index for index, item in enumerate(ExpansionPriority)}
    for _, feasibility, decision_value in rows:
        if not math.isfinite(feasibility) or not math.isfinite(decision_value):
            raise ValueError("feasibility and decision_value must be finite")
    frontier: list[tuple[ExpansionDirection, float, float]] = []
    for candidate in rows:
        direction, feasibility, decision_value = candidate
        dominated = any(
            other is not candidate
            and priority[other[0].priority] <= priority[direction.priority]
            and other[1] >= feasibility
            and other[2] >= decision_value
            and (
                priority[other[0].priority] < priority[direction.priority]
                or other[1] > feasibility
                or other[2] > decision_value
            )
            for other in rows
        )
        if not dominated:
            frontier.append(candidate)
    frontier.sort(
        key=lambda item: (
            priority[item[0].priority],
            -item[2],
            -item[1],
            item[0].title.casefold(),
        )
    )
    return tuple(item[0] for item in frontier)


__all__ = [
    "ExpansionAuditState",
    "ExpansionDiscoveryRound",
    "ExpansionDirection",
    "ExpansionOrigin",
    "ExpansionPriority",
    "ExpansionRegistryAudit",
    "ExpansionSaturationAssessment",
    "ExpansionSaturationState",
    "assess_bounded_saturation",
    "audit_expansion_registry",
    "pareto_experiment_frontier",
]
