"""Uncertainty helpers for gate-first formula simulation.

The simulator can only be as good as the data behind each material.  This
module keeps that limitation explicit by assigning simple uncertainty bands to
measured, estimated, fallback, and missing fields.  The values are deliberately
coarse; they are release-gate signals, not statistical proof.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable

SOURCE_UNCERTAINTY = {
    "measured": 0.05,
    "literature": 0.10,
    "registry": 0.15,
    "profile": 0.25,
    "estimated": 0.45,
    "heuristic": 0.60,
    "fallback": 0.75,
    "missing": 1.0,
}


@dataclass(frozen=True, slots=True)
class FieldUncertainty:
    field: str
    source: str
    relative_uncertainty: float
    message: str = ""


@dataclass(frozen=True, slots=True)
class FormulaUncertainty:
    relative_uncertainty: float
    confidence_score: float
    confidence_grade: str
    fields: tuple[FieldUncertainty, ...]


def uncertainty_for_source(source: str | None) -> float:
    """Return a relative uncertainty in the range 0..1 for a source label."""
    if not source:
        return SOURCE_UNCERTAINTY["missing"]
    key = source.lower()
    for token, value in SOURCE_UNCERTAINTY.items():
        if token in key:
            return value
    return SOURCE_UNCERTAINTY["estimated"]


def grade_confidence(score: float) -> str:
    if score >= 80:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    if score >= 25:
        return "LOW"
    return "VERY_LOW"


def combine_uncertainties(fields: Iterable[FieldUncertainty]) -> FormulaUncertainty:
    """Combine independent field uncertainties by RMS and map to confidence."""
    items = tuple(fields)
    if not items:
        return FormulaUncertainty(
            relative_uncertainty=1.0,
            confidence_score=0.0,
            confidence_grade="VERY_LOW",
            fields=(),
        )
    rms = sqrt(sum(f.relative_uncertainty ** 2 for f in items) / len(items))
    score = max(0.0, min(100.0, 100.0 * (1.0 - rms)))
    return FormulaUncertainty(
        relative_uncertainty=round(rms, 3),
        confidence_score=round(score, 1),
        confidence_grade=grade_confidence(score),
        fields=items,
    )


def field_uncertainty(field: str, source: str | None, message: str = "") -> FieldUncertainty:
    return FieldUncertainty(
        field=field,
        source=source or "missing",
        relative_uncertainty=uncertainty_for_source(source),
        message=message,
    )
