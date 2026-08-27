"""Stable evidence posture labels for scientific and engineering outputs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ScientificClass(str, Enum):
    """How strongly an output is supported by calculation or evidence."""

    EXACT = "EXACT"
    LITERATURE_DERIVED = "LITERATURE_DERIVED"
    EMPIRICALLY_CALIBRATED = "EMPIRICALLY_CALIBRATED"
    HEURISTIC = "HEURISTIC"
    SPECULATIVE = "SPECULATIVE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class EvidenceDescriptor:
    """Claim-level evidence posture, provenance, and disclosed caveats."""

    classification: ScientificClass
    basis: str
    sources: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "classification": self.classification.value,
            "basis": self.basis,
            "sources": list(self.sources),
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
        }


__all__ = ["EvidenceDescriptor", "ScientificClass"]
