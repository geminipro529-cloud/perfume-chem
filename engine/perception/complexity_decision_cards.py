"""Compact, hash-bound projections of native complexity decisions.

The card contract is intentionally narrower than the native scientific outputs.
It carries one decision into a model prompt without copying a full diagnostic
dump or granting sensory, formula, inventory, safety, or release authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_CARD_BYTES = 1600


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return value.strip()


class DecisionCardState(str, Enum):
    DECIDE = "DECIDE"
    HOLD = "HOLD"
    NONE = "NONE"


@dataclass(frozen=True, slots=True)
class DecisionCard:
    module_id: str
    decision_kind: str
    state: DecisionCardState
    decision_question: str
    decisive_evidence: tuple[str, ...]
    preserve: str
    reject: str
    controlled_comparison: str
    claim_ceiling: str
    source_result_sha256: str

    def __post_init__(self) -> None:
        for field_name in (
            "module_id",
            "decision_kind",
            "decision_question",
            "preserve",
            "reject",
            "controlled_comparison",
            "claim_ceiling",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if not isinstance(self.state, DecisionCardState):
            raise TypeError("state must be a DecisionCardState")
        if not isinstance(self.decisive_evidence, tuple):
            raise TypeError("decisive_evidence must be a tuple")
        if not 1 <= len(self.decisive_evidence) <= 3:
            raise ValueError(
                "decisive_evidence must contain one to three facts; "
                "at most three are allowed"
            )
        normalized_evidence = tuple(
            _text(item, "decisive_evidence item") for item in self.decisive_evidence
        )
        object.__setattr__(self, "decisive_evidence", normalized_evidence)
        if not isinstance(self.source_result_sha256, str) or _SHA256_RE.fullmatch(
            self.source_result_sha256
        ) is None:
            raise ValueError("source_result_sha256 must be a lowercase SHA-256 digest")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "complexity_decision_card_v1",
            "module_id": self.module_id,
            "decision_kind": self.decision_kind,
            "state": self.state.value,
            "decision_question": self.decision_question,
            "decisive_evidence": list(self.decisive_evidence),
            "preserve": self.preserve,
            "reject": self.reject,
            "controlled_comparison": self.controlled_comparison,
            "claim_ceiling": self.claim_ceiling,
            "source_result_sha256": self.source_result_sha256,
        }

    def to_json_bytes(self) -> bytes:
        encoded = json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        if len(encoded) > _MAX_CARD_BYTES:
            raise ValueError("decision card exceeds 1600 UTF-8 bytes")
        return encoded

    @property
    def card_sha256(self) -> str:
        return hashlib.sha256(self.to_json_bytes()).hexdigest()


__all__ = ["DecisionCard", "DecisionCardState"]
