"""Design-only presentation-order balancing for bounded sensory protocols."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from engine.calibration.hashing import stable_json_hash


class OrderBalanceState(str, Enum):
    PASS_FOR_DESIGN = "PASS_FOR_DESIGN"
    REBUILD = "REBUILD"


def _labels(values: tuple[str, ...]) -> tuple[str, ...]:
    labels = tuple(str(item).strip() for item in values)
    if len(labels) < 2 or any(not item for item in labels):
        raise ValueError("at least two nonblank labels are required")
    if len(labels) != len(set(labels)):
        raise ValueError("labels must be unique")
    return labels


@dataclass(frozen=True, slots=True)
class PresentationSchedule:
    labels: tuple[str, ...]
    sequences: tuple[tuple[str, ...], ...]
    method: str = "WILLIAMS_FIRST_ORDER_BALANCED"
    random_assignment_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        normalized = _labels(self.labels)
        object.__setattr__(self, "labels", normalized)
        if not self.sequences:
            raise ValueError("sequences must not be empty")
        expected = set(normalized)
        for sequence in self.sequences:
            if len(sequence) != len(normalized) or set(sequence) != expected:
                raise ValueError(
                    "each sequence must contain every schedule label exactly once"
                )

    @property
    def schedule_sha256(self) -> str:
        return stable_json_hash(self.as_dict(include_hash=False))

    def as_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "labels": list(self.labels),
            "sequences": [list(item) for item in self.sequences],
            "method": self.method,
            "random_assignment_authorized": self.random_assignment_authorized,
            "physical_execution_authorized": self.physical_execution_authorized,
            "sensory_authority": self.sensory_authority,
        }
        if include_hash:
            payload["schedule_sha256"] = stable_json_hash(payload)
        return payload


@dataclass(frozen=True, slots=True)
class OrderBalanceAssessment:
    state: OrderBalanceState
    schedule_sha256: str
    first_position_counts: dict[str, int]
    adjacent_pair_counts: dict[str, int]
    failures: tuple[str, ...]
    physical_execution_authorized: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "state": self.state.value,
            "schedule_sha256": self.schedule_sha256,
            "first_position_counts": dict(self.first_position_counts),
            "adjacent_pair_counts": dict(self.adjacent_pair_counts),
            "failures": list(self.failures),
            "boundary": (
                "Order balance is a design diagnostic only. Random allocation, "
                "washout adequacy, execution, observations, and inference remain separate."
            ),
            "physical_execution_authorized": self.physical_execution_authorized,
            "sensory_authority": self.sensory_authority,
            "release_authority": self.release_authority,
        }
        payload["result_sha256"] = stable_json_hash(payload)
        return payload


def generate_williams_schedule(labels: tuple[str, ...]) -> PresentationSchedule:
    """Generate a first-order balanced sequence set without allocating assessors."""

    normalized = _labels(labels)
    count = len(normalized)
    first_indices = tuple(
        0
        if position == 0
        else (position + 1) // 2
        if position % 2
        else count - position // 2
        for position in range(count)
    )
    index_rows = tuple(
        tuple((value + shift) % count for value in first_indices)
        for shift in range(count)
    )
    if count % 2:
        index_rows = index_rows + tuple(tuple(reversed(row)) for row in index_rows)
    sequences = tuple(
        tuple(normalized[index] for index in row) for row in index_rows
    )
    schedule = PresentationSchedule(labels=normalized, sequences=sequences)
    assessment = assess_order_balance(schedule)
    if assessment.state is not OrderBalanceState.PASS_FOR_DESIGN:
        raise ValueError("generated schedule failed its own balance audit")
    return schedule


def assess_order_balance(schedule: PresentationSchedule) -> OrderBalanceAssessment:
    if not isinstance(schedule, PresentationSchedule):
        raise TypeError("schedule must be a PresentationSchedule")
    first_counts = Counter({label: 0 for label in schedule.labels})
    pair_counts = Counter(
        {(left, right): 0 for left in schedule.labels for right in schedule.labels if left != right}
    )
    for sequence in schedule.sequences:
        first_counts[sequence[0]] += 1
        pair_counts.update(zip(sequence, sequence[1:]))
    failures: list[str] = []
    first_values = tuple(first_counts.values())
    pair_values = tuple(pair_counts.values())
    if max(first_values) - min(first_values) > 1:
        failures.append("first-position frequencies are not balanced")
    if max(pair_values) - min(pair_values) > 1:
        failures.append("first-order adjacent carryover pairs are not balanced")
    return OrderBalanceAssessment(
        state=(
            OrderBalanceState.REBUILD
            if failures
            else OrderBalanceState.PASS_FOR_DESIGN
        ),
        schedule_sha256=schedule.schedule_sha256,
        first_position_counts=dict(sorted(first_counts.items())),
        adjacent_pair_counts={
            f"{left}->{right}": count
            for (left, right), count in sorted(pair_counts.items())
        },
        failures=tuple(failures),
    )


__all__ = [
    "OrderBalanceAssessment",
    "OrderBalanceState",
    "PresentationSchedule",
    "assess_order_balance",
    "generate_williams_schedule",
]
