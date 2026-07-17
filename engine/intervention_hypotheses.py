"""Inventory-grounded, non-quantitative perfume intervention hypotheses."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re

from engine.intervention_context import InterventionMode
from engine.intervention_profiles import (
    family_names,
    get_observation_rules,
    get_profile,
    normalize_family_key,
    normalize_observation_signals,
    suggest_interventions,
)
from engine.scientific_contract import EvidenceDescriptor, ScientificClass


_VALID_MODES: frozenset[str] = frozenset({"pre_mix", "between_mix", "post_mix"})


@dataclass(frozen=True, slots=True)
class InterventionHypothesisRequest:
    """Qualitative observations plus the exact inventory names available to the bench."""

    brief_name: str
    observations: tuple[str, ...]
    available_materials: tuple[str, ...]
    family: str | None = None
    profile: str | None = None
    mode: InterventionMode | str = "post_mix"
    forbidden_materials: frozenset[str] = frozenset()
    limit: int = 5

    def __post_init__(self) -> None:
        brief_name = self.brief_name.strip()
        observations = _unique(self.observations)
        available_materials = _unique(self.available_materials)
        mode = str(self.mode).strip().casefold().replace("-", "_").replace(" ", "_")
        if not brief_name:
            raise ValueError("brief_name must not be empty")
        if not observations:
            raise ValueError("at least one observation is required")
        if mode not in _VALID_MODES:
            raise ValueError("mode must be pre_mix, between_mix, or post_mix")
        if not 1 <= int(self.limit) <= 20:
            raise ValueError("limit must be between 1 and 20")

        family = normalize_family_key(self.family)
        if self.family is not None and family not in family_names():
            raise ValueError(f"unknown fragrance family: {self.family}")
        profile = get_profile(self.profile) if self.profile else None
        if self.profile and profile is None:
            raise ValueError(f"unknown creative profile: {self.profile}")
        if family and profile and profile.family != family:
            raise ValueError("creative profile does not belong to the requested family")

        object.__setattr__(self, "brief_name", brief_name)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "available_materials", available_materials)
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "profile", profile.slug if profile else None)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(
            self,
            "forbidden_materials",
            frozenset(_material_key(value) for value in self.forbidden_materials),
        )
        object.__setattr__(self, "limit", int(self.limit))


@dataclass(frozen=True, slots=True)
class ObservationDiagnosis:
    """Possible interpretations of one normalized sensory observation."""

    signal: str
    labels: tuple[str, ...]
    possible_interpretations: tuple[str, ...]
    candidate_actions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InterventionHypothesis:
    """A qualitative candidate direction without invented quantitative claims."""

    signal: str
    family: str | None
    profile: str | None
    profile_label: str | None
    mode: InterventionMode
    action: str
    materials: tuple[str, ...]
    rationale: str
    rule_match_score: float
    dose_style: str
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InterventionHypothesisResult:
    brief_name: str
    normalized_observations: tuple[str, ...]
    unrecognized_observations: tuple[str, ...]
    diagnoses: tuple[ObservationDiagnosis, ...]
    hypotheses: tuple[InterventionHypothesis, ...]
    inventory_material_count: int
    evidence: EvidenceDescriptor

    def as_dict(self) -> dict[str, object]:
        return {
            "brief_name": self.brief_name,
            "normalized_observations": list(self.normalized_observations),
            "unrecognized_observations": list(self.unrecognized_observations),
            "diagnoses": [asdict(item) for item in self.diagnoses],
            "hypotheses": [asdict(item) for item in self.hypotheses],
            "inventory_material_count": self.inventory_material_count,
            "evidence": self.evidence.as_dict(),
        }


def generate_intervention_hypotheses(
    request: InterventionHypothesisRequest,
) -> InterventionHypothesisResult:
    """Match observations to inventory-valid hypotheses for later bench testing."""

    normalized = tuple(normalize_observation_signals(request.observations))
    diagnoses: list[ObservationDiagnosis] = []
    unrecognized: list[str] = []
    for signal in normalized:
        rules = get_observation_rules(signal)
        if not rules:
            unrecognized.append(signal)
            continue
        diagnoses.append(
            ObservationDiagnosis(
                signal=signal,
                labels=_unique(rule.label for rule in rules),
                possible_interpretations=_unique(rule.description for rule in rules),
                candidate_actions=_unique(
                    rule.action for rule in rules if request.mode in rule.modes
                ),
            )
        )

    available = tuple(
        material
        for material in request.available_materials
        if _material_key(material) not in request.forbidden_materials
    )
    recommendations = suggest_interventions(
        observations=normalized,
        family=request.family,
        profile=request.profile,
        mode=request.mode,
        available_materials=available,
        limit=request.limit,
    )
    hypotheses: list[InterventionHypothesis] = []
    for recommendation in recommendations:
        materials = _inventory_matches(recommendation.materials, available)
        if not materials:
            continue
        hypotheses.append(
            InterventionHypothesis(
                signal=recommendation.signal,
                family=recommendation.family,
                profile=recommendation.profile,
                profile_label=recommendation.profile_label,
                mode=recommendation.mode,
                action=recommendation.action,
                materials=materials,
                rationale="Hypothesis: " + recommendation.rationale,
                rule_match_score=recommendation.confidence,
                dose_style=recommendation.dose_style,
                notes=recommendation.notes,
            )
        )

    evidence = EvidenceDescriptor(
        classification=ScientificClass.HEURISTIC,
        basis=(
            "Normalized bottle observations were matched to curated perfumery rules "
            f"for the named brief {request.brief_name}. Inventory inclusion and explicit "
            "material exclusions are deterministic; sensory interpretation is heuristic."
        ),
        sources=(
            "engine.intervention_profiles",
            "Laing and Francis 1989, doi:10.1016/0031-9384(89)90041-3",
            "Cashion, Livermore, and Hummel 2006, doi:10.1016/j.biopsycho.2006.05.002",
            "ISO 5495:2005 paired comparison methodology",
        ),
        assumptions=(
            "The supplied observations represent repeatable impressions at stated wear stages.",
            "The supplied inventory snapshot is current and canonicalized.",
        ),
        limitations=(
            "This is not a causal diagnosis; mixture suppression and adaptation can produce "
            "the same observation through different mechanisms.",
            "No dose, OAV delta, safety status, longevity, or performance value is generated.",
            f"No hypothesis is asserted to preserve the named brief {request.brief_name}; "
            "confirm direction with controlled paired smelling trials.",
            "rule_match_score is a deterministic heuristic score, not an empirical probability.",
        ),
    )
    return InterventionHypothesisResult(
        brief_name=request.brief_name,
        normalized_observations=normalized,
        unrecognized_observations=tuple(unrecognized),
        diagnoses=tuple(diagnoses),
        hypotheses=tuple(hypotheses),
        inventory_material_count=len(request.available_materials),
        evidence=evidence,
    )


def _inventory_matches(
    recommended: tuple[str, ...], available: tuple[str, ...]
) -> tuple[str, ...]:
    """Return canonical inventory names only when a match is unambiguous."""

    selected: list[str] = []
    for name in recommended:
        key = _material_key(name)
        exact = [candidate for candidate in available if _material_key(candidate) == key]
        if exact:
            selected.extend(exact[:1])
            continue
        partial = [
            candidate
            for candidate in available
            if key in _material_key(candidate) or _material_key(candidate) in key
        ]
        if len(partial) == 1:
            selected.append(partial[0])
    return _unique(selected)


def _material_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().casefold())


def _unique(values) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item:
            continue
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return tuple(result)


__all__ = [
    "InterventionHypothesis",
    "InterventionHypothesisRequest",
    "InterventionHypothesisResult",
    "ObservationDiagnosis",
    "generate_intervention_hypotheses",
]
