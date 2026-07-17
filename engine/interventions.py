"""Constraint-first ranking for measurable perfume interventions."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
from typing import Mapping

from engine.safety_assessment import SafetyAssessmentStatus
from engine.scientific_contract import EvidenceDescriptor, ScientificClass


@dataclass(frozen=True, slots=True)
class BriefConstraints:
    name: str
    required_character_tags: frozenset[str] = frozenset()
    forbidden_materials: frozenset[str] = frozenset()
    maximum_active_addition_ppm_w_w: float = 1_000_000.0

    def __post_init__(self) -> None:
        name = self.name.strip()
        maximum = float(self.maximum_active_addition_ppm_w_w)
        if not name:
            raise ValueError("brief name must not be empty")
        if not isfinite(maximum) or maximum < 0:
            raise ValueError("maximum active addition must be finite and nonnegative")
        object.__setattr__(self, "name", name)
        object.__setattr__(
            self,
            "required_character_tags",
            frozenset(_tag(value) for value in self.required_character_tags),
        )
        object.__setattr__(
            self,
            "forbidden_materials",
            frozenset(_key(value) for value in self.forbidden_materials),
        )
        object.__setattr__(self, "maximum_active_addition_ppm_w_w", maximum)


@dataclass(frozen=True, slots=True)
class InventoryStock:
    material: str
    available_stock_mass_mg: float
    active_mass_fraction: float
    minimum_measurable_stock_mass_mg: float
    dispensing_increment_mg: float

    def __post_init__(self) -> None:
        values = (
            self.available_stock_mass_mg,
            self.active_mass_fraction,
            self.minimum_measurable_stock_mass_mg,
            self.dispensing_increment_mg,
        )
        if any(not isfinite(float(value)) for value in values):
            raise ValueError("inventory quantities must be finite")
        if self.available_stock_mass_mg < 0:
            raise ValueError("available stock mass must be nonnegative")
        if not 0 < self.active_mass_fraction <= 1:
            raise ValueError("active mass fraction must be greater than zero and at most one")
        if self.minimum_measurable_stock_mass_mg <= 0 or self.dispensing_increment_mg <= 0:
            raise ValueError("measurement minimum and increment must be greater than zero")


@dataclass(frozen=True, slots=True)
class CandidateAddition:
    material: str
    requested_active_ppm_w_w: float
    predicted_oav_delta: float
    desired_effects: Mapping[str, float]
    preserved_character_tags: frozenset[str]
    safety_status: SafetyAssessmentStatus

    def __post_init__(self) -> None:
        ppm = float(self.requested_active_ppm_w_w)
        oav = float(self.predicted_oav_delta)
        if not self.material.strip():
            raise ValueError("candidate material must not be empty")
        if not isfinite(ppm) or ppm <= 0:
            raise ValueError("candidate active ppm must be finite and greater than zero")
        if not isfinite(oav) or oav < 0:
            raise ValueError("predicted OAV delta must be finite and nonnegative")
        effects = {str(name).strip(): float(value) for name, value in self.desired_effects.items()}
        if any(not name or not isfinite(value) for name, value in effects.items()):
            raise ValueError("desired effects must be named finite values")
        object.__setattr__(self, "material", self.material.strip())
        object.__setattr__(self, "requested_active_ppm_w_w", ppm)
        object.__setattr__(self, "predicted_oav_delta", oav)
        object.__setattr__(self, "desired_effects", effects)
        object.__setattr__(
            self,
            "preserved_character_tags",
            frozenset(_tag(value) for value in self.preserved_character_tags),
        )
        object.__setattr__(self, "safety_status", SafetyAssessmentStatus(self.safety_status))


@dataclass(frozen=True, slots=True)
class InterventionRequest:
    batch_mass_g: float
    brief: BriefConstraints
    inventory: Mapping[str, InventoryStock]
    candidates: tuple[CandidateAddition, ...]

    def __post_init__(self) -> None:
        batch_mass = float(self.batch_mass_g)
        if not isfinite(batch_mass) or batch_mass <= 0:
            raise ValueError("batch mass must be finite and greater than zero")
        object.__setattr__(self, "batch_mass_g", batch_mass)
        object.__setattr__(self, "candidates", tuple(self.candidates))


@dataclass(frozen=True, slots=True)
class RankedIntervention:
    material: str
    stock_mass_mg: float
    achieved_active_ppm_w_w: float
    predicted_oav_delta: float
    desired_effects: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class RejectedIntervention:
    material: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InterventionResult:
    ranked: tuple[RankedIntervention, ...]
    rejected: tuple[RejectedIntervention, ...]
    evidence: EvidenceDescriptor


def rank_interventions(request: InterventionRequest) -> InterventionResult:
    """Filter hard constraints, then retain the nondominated candidate set."""

    inventory = {_key(name): stock for name, stock in request.inventory.items()}
    feasible: list[RankedIntervention] = []
    rejected: list[RejectedIntervention] = []

    for candidate in request.candidates:
        reasons: list[str] = []
        key = _key(candidate.material)
        if key in request.brief.forbidden_materials:
            reasons.append("forbidden by brief")
        missing_tags = request.brief.required_character_tags.difference(
            candidate.preserved_character_tags
        )
        if missing_tags:
            reasons.append(
                "does not preserve required character tags: "
                + ", ".join(sorted(missing_tags))
            )
        if candidate.safety_status is not SafetyAssessmentStatus.PASS:
            reasons.append("safety status is not pass")

        stock = inventory.get(key)
        stock_mass_mg = 0.0
        achieved_ppm = candidate.requested_active_ppm_w_w
        if stock is None:
            reasons.append("not in inventory")
        else:
            required_active_mg = (
                candidate.requested_active_ppm_w_w
                * request.batch_mass_g
                * 1000.0
                / 1_000_000.0
            )
            required_stock_mg = required_active_mg / stock.active_mass_fraction
            if required_stock_mg < stock.minimum_measurable_stock_mass_mg:
                reasons.append("below measurable stock dose")
            stock_mass_mg = (
                ceil(required_stock_mg / stock.dispensing_increment_mg)
                * stock.dispensing_increment_mg
            )
            if stock_mass_mg > stock.available_stock_mass_mg:
                reasons.append("insufficient stock")
            achieved_active_mg = stock_mass_mg * stock.active_mass_fraction
            achieved_ppm = achieved_active_mg / (request.batch_mass_g * 1000.0) * 1_000_000.0
            if achieved_ppm > request.brief.maximum_active_addition_ppm_w_w:
                reasons.append("exceeds brief maximum active addition")

        if reasons:
            rejected.append(RejectedIntervention(candidate.material, tuple(reasons)))
            continue
        feasible.append(
            RankedIntervention(
                material=candidate.material,
                stock_mass_mg=round(stock_mass_mg, 12),
                achieved_active_ppm_w_w=round(achieved_ppm, 12),
                predicted_oav_delta=candidate.predicted_oav_delta,
                desired_effects=candidate.desired_effects,
            )
        )

    nondominated: list[RankedIntervention] = []
    for ranked_candidate in feasible:
        if any(
            other is not ranked_candidate and _dominates(other, ranked_candidate)
            for other in feasible
        ):
            rejected.append(
                RejectedIntervention(ranked_candidate.material, ("Pareto-dominated",))
            )
        else:
            nondominated.append(ranked_candidate)

    nondominated.sort(
        key=lambda item: (
            -sum(item.desired_effects.values()),
            item.achieved_active_ppm_w_w,
            item.material.casefold(),
        )
    )
    rejected.sort(key=lambda item: item.material.casefold())
    return InterventionResult(
        ranked=tuple(nondominated),
        rejected=tuple(rejected),
        evidence=EvidenceDescriptor(
            classification=ScientificClass.HEURISTIC,
            basis=(
                f"Hard feasibility constraints and transparent Pareto dominance for "
                f"the named brief {request.brief.name}; character-tag assignments and "
                "predicted effects remain heuristic."
            ),
            sources=("engine.interventions",),
            assumptions=("Inventory quantities and safety statuses are current.",),
            limitations=(
                "Predicted OAV delta is a screening ratio, not a measured sensory effect.",
                "Brief preservation depends on declared character tags and requires smelling trials.",
            ),
        ),
    )


def _dominates(left: RankedIntervention, right: RankedIntervention) -> bool:
    objectives = set(left.desired_effects) | set(right.desired_effects)
    effects_no_worse = all(
        left.desired_effects.get(name, 0.0) >= right.desired_effects.get(name, 0.0)
        for name in objectives
    )
    dose_no_worse = left.achieved_active_ppm_w_w <= right.achieved_active_ppm_w_w
    strictly_better = (
        left.achieved_active_ppm_w_w < right.achieved_active_ppm_w_w
        or any(
            left.desired_effects.get(name, 0.0) > right.desired_effects.get(name, 0.0)
            for name in objectives
        )
    )
    return effects_no_worse and dose_no_worse and strictly_better


def _key(value: str) -> str:
    return " ".join(str(value).strip().casefold().split())


def _tag(value: str) -> str:
    return _key(value).replace(" ", "_")


__all__ = [
    "BriefConstraints",
    "CandidateAddition",
    "InterventionRequest",
    "InterventionResult",
    "InventoryStock",
    "RankedIntervention",
    "RejectedIntervention",
    "rank_interventions",
]
