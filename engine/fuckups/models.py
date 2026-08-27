"""Data models for the fuckup registry.

Each FuckupEntry captures a complete formulation failure: what it was supposed
to be, what it actually became, the root cause, the material culprits, and
the lesson the system should learn.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RootCauseCategory(str, Enum):
    """Taxonomy of failure categories."""

    MATERIAL_MISMATCH = "material_mismatch"
    """A material was chosen that fundamentally contradicts the intended character."""

    DOSE_OVERLOAD = "dose_overload"
    """A material was dosed beyond its safe ceiling for the target family."""

    GENRE_COLLISION = "genre_collision"
    """Two incompatible genre registers collided (e.g. iris soliflore + fruity chypre)."""

    MISSING_DNA = "missing_dna"
    """Key materials that define the target DNA were absent."""

    SCAFFOLD_SWAMPING = "scaffold_swamping"
    """Transparent scaffold (Hedione/Iso E) amplified the wrong character."""

    PYRAMID_COLLAPSE = "pyramid_collapse"
    """Top/heart/base proportions collapsed, removing temporal evolution."""

    CHYPRE_DRIFT = "chypre_drift"
    """Oakmoss + labdanum + vetiver + cedar skeleton pulled the formula toward classical chypre."""

    GREEN_DRIFT = "green_drift"
    """Aromatic/green materials (juniper, petitgrain, galbanum) pulled toward fougère/chypre territory."""

    DATA_QUALITY = "data_quality"
    """Missing or wrong ODT/VP data caused bad dosing decisions."""


@dataclass(frozen=True, slots=True)
class CulpritMaterial:
    """A material that contributed to the failure."""

    name: str
    dose_ul: float
    dilution_pct: float
    oav: float
    vp_pa: float
    role: str
    why_wrong: str
    """Human-readable explanation of what this material did wrong."""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dose_ul": self.dose_ul,
            "dilution_pct": self.dilution_pct,
            "oav": self.oav,
            "vp_pa": self.vp_pa,
            "role": self.role,
            "why_wrong": self.why_wrong,
        }


@dataclass(frozen=True, slots=True)
class MissingDNA:
    """A key material that should have been present but wasn't."""

    name: str
    role_in_target: str
    alternative_used: str
    """What was used instead."""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role_in_target": self.role_in_target,
            "alternative_used": self.alternative_used,
        }


@dataclass(frozen=True, slots=True)
class FuckupEntry:
    """Complete record of a formulation failure."""

    id: str
    """Unique identifier: formula_name + date, e.g. 'cassis_iris_smoke_2026-07-05'."""

    formula_file: str
    """Relative path to the formula .md file."""

    intended_character: str
    """What the perfumer was trying to achieve."""

    actual_character: str
    """What it actually smelled like."""

    root_causes: tuple[RootCauseCategory, ...]
    """Taxonomy categories explaining the failure."""

    culprits: tuple[CulpritMaterial, ...]
    """Materials that caused damage, ranked by impact."""

    missing_dna: tuple[MissingDNA, ...]
    """Key materials that should have been present."""

    pipeline_snapshot: dict[str, Any]
    """Key pipeline metrics at time of failure (pyramid, OAV leaders, gate failures)."""

    lesson: str
    """The one-paragraph lesson the system should learn from this failure."""

    detection_rules: tuple[str, ...]
    """Natural-language rules for the detector to match. E.g. 'juniper > 40uL in non-fougere'."""

    date: str
    """ISO date of the session."""

    severity: str = "high"
    """How badly the formula missed: 'catastrophic', 'high', 'moderate', 'minor'."""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "formula_file": self.formula_file,
            "intended_character": self.intended_character,
            "actual_character": self.actual_character,
            "root_causes": [rc.value for rc in self.root_causes],
            "culprits": [c.as_dict() for c in self.culprits],
            "missing_dna": [m.as_dict() for m in self.missing_dna],
            "pipeline_snapshot": dict(self.pipeline_snapshot),
            "lesson": self.lesson,
            "detection_rules": list(self.detection_rules),
            "date": self.date,
            "severity": self.severity,
        }


@dataclass(frozen=True, slots=True)
class DetectionWarning:
    """A warning raised by the detector when a new formula matches a known pattern."""

    pattern_name: str
    """Human-readable pattern name (e.g. 'Juniper in non-fougère context')."""

    severity: str
    """'catastrophic', 'high', 'moderate', 'low'."""

    matched_rule: str
    """The specific rule that triggered."""

    violated_by: tuple[str, ...]
    """Material names that violated the rule."""

    fuckup_reference: str
    """ID of the historical fuckup this rule was learned from."""

    recommendation: str
    """What to do about it."""

    def as_dict(self) -> dict[str, Any]:
        return {
            "pattern_name": self.pattern_name,
            "severity": self.severity,
            "matched_rule": self.matched_rule,
            "violated_by": list(self.violated_by),
            "fuckup_reference": self.fuckup_reference,
            "recommendation": self.recommendation,
        }
