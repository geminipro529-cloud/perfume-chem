"""Shared context/types for stage-aware perfume intervention recommendations.

This module defines a small, stable vocabulary for:
  - when an intervention happens (`pre_mix`, `post_mix`, `between_mix`)
  - what the operator is trying to do (style/category/target intent)
  - what was observed after mixing or wear testing

The goal is to let multiple pipeline surfaces speak the same language without
hard-wiring the recommendation policy into every caller.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Literal, Mapping, Sequence

InterventionMode = Literal["pre_mix", "post_mix", "between_mix"]

_VALID_MODES = {"pre_mix", "post_mix", "between_mix"}

_OBSERVATION_ALIASES = {
    "top fades fast": "top_fades_fast",
    "opening fades fast": "top_fades_fast",
    "opening too weak": "top_weak",
    "top too weak": "top_weak",
    "needs more top": "top_weak",
    "too sharp": "too_sharp",
    "too citrus": "too_sharp",
    "too acidic": "too_sharp",
    "too sweet": "too_sweet",
    "too gourmand": "too_sweet",
    "too floral": "too_floral",
    "too white floral": "too_floral",
    "too heavy": "too_heavy",
    "too dense": "too_heavy",
    "too loud": "too_loud",
    "too projecting": "too_loud",
    "too soft": "too_soft",
    "too flat": "too_flat",
    "too linear": "too_flat",
    "too powdery": "too_powdery",
    "too soapy": "too_soapy",
    "too cosmetic": "too_cosmetic",
    "too woody": "too_woody",
    "too musky": "too_musky",
    "drydown too thin": "drydown_thin",
    "drydown too weak": "drydown_thin",
    "drydown too heavy": "drydown_heavy",
    "heart too thin": "heart_thin",
    "heart too dense": "heart_heavy",
    "needs more lift": "needs_lift",
    "needs more diffusion": "needs_diffusion",
    "needs more texture": "needs_texture",
    "needs more depth": "needs_depth",
    "needs more warmth": "needs_warmth",
    "needs more skin": "needs_skin",
}

_STRUCTURED_TEXT_KEYS = (
    "issue_tags",
    "issues",
    "observation_tags",
    "desired_effects",
    "goals",
    "targets",
    "must_preserve",
    "must_keep",
    "preserve",
    "must_avoid",
    "avoid",
    "notes",
    "feedback",
)


def normalize_intervention_mode(mode: str | None) -> InterventionMode:
    """Normalize stage/mode strings to the shared three-mode vocabulary."""
    raw = (mode or "pre_mix").strip().lower().replace("-", "_").replace(" ", "_")
    if raw in _VALID_MODES:
        return raw  # type: ignore[return-value]
    if raw in {"postmix", "post"}:
        return "post_mix"
    if raw in {"between", "between_batches", "between_mixes"}:
        return "between_mix"
    return "pre_mix"


def normalize_observation_tag(tag: str) -> str:
    """Normalize free-text observation tags into stable snake_case signals."""
    raw = re.sub(r"\s+", " ", tag.strip().lower())
    raw = _OBSERVATION_ALIASES.get(raw, raw)
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    raw = re.sub(r"_+", "_", raw).strip("_")
    return raw


def normalize_observation_tags(tags: Iterable[str] | None) -> list[str]:
    """Normalize and deduplicate free-text observation tags."""
    if not tags:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for tag in tags:
        norm = normalize_observation_tag(tag)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        normalized.append(norm)
    return normalized


def normalize_descriptor(value: str) -> str:
    """Normalize a free-text descriptor while preserving human readability."""
    text = re.sub(r"\s+", " ", str(value).strip().lower())
    return text


def normalize_descriptors(values: Iterable[str] | None) -> list[str]:
    """Normalize and deduplicate human-readable structured descriptors."""
    if not values:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = normalize_descriptor(value)
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _flatten_text_values(value: object) -> list[str]:
    """Flatten strings/lists/mappings into a flat list of text values."""
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Mapping):
        items: list[str] = []
        for key in _STRUCTURED_TEXT_KEYS:
            if key in value:
                items.extend(_flatten_text_values(value[key]))
        return items
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        items: list[str] = []
        for item in value:
            items.extend(_flatten_text_values(item))
        return items
    text = str(value).strip()
    return [text] if text else []


@dataclass(slots=True)
class ObservationProfile:
    """Structured operator observation schema shared across intervention modes."""

    issue_tags: list[str] = field(default_factory=list)
    desired_effects: list[str] = field(default_factory=list)
    must_preserve: list[str] = field(default_factory=list)
    must_avoid: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.issue_tags = normalize_observation_tags(self.issue_tags)
        self.desired_effects = normalize_descriptors(self.desired_effects)
        self.must_preserve = normalize_descriptors(self.must_preserve)
        self.must_avoid = normalize_descriptors(self.must_avoid)
        self.notes = normalize_descriptors(self.notes)

    @classmethod
    def from_value(
        cls,
        value: object = None,
        *,
        intent_tags: Iterable[str] | None = None,
    ) -> "ObservationProfile":
        """Coerce loose CLI/API observation inputs into the structured schema."""
        if isinstance(value, cls):
            profile = cls(
                issue_tags=list(value.issue_tags),
                desired_effects=list(value.desired_effects),
                must_preserve=list(value.must_preserve),
                must_avoid=list(value.must_avoid),
                notes=list(value.notes),
            )
        elif isinstance(value, Mapping):
            profile = cls(
                issue_tags=_flatten_text_values(
                    value.get("issue_tags")
                    or value.get("issues")
                    or value.get("observation_tags")
                ),
                desired_effects=_flatten_text_values(
                    value.get("desired_effects")
                    or value.get("goals")
                    or value.get("targets")
                ),
                must_preserve=_flatten_text_values(
                    value.get("must_preserve")
                    or value.get("must_keep")
                    or value.get("preserve")
                ),
                must_avoid=_flatten_text_values(
                    value.get("must_avoid")
                    or value.get("avoid")
                ),
                notes=_flatten_text_values(value.get("notes") or value.get("feedback")),
            )
        else:
            profile = cls(notes=_flatten_text_values(value))

        if intent_tags:
            profile.desired_effects = normalize_descriptors(
                [*profile.desired_effects, *_flatten_text_values(list(intent_tags))]
            )
        return profile

    def all_text_hints(self) -> list[str]:
        """Return all structured hints as flat text for legacy heuristic paths."""
        return [
            *self.issue_tags,
            *self.desired_effects,
            *self.must_preserve,
            *self.must_avoid,
            *self.notes,
        ]

    def as_summary_lines(self) -> list[str]:
        """Return a compact human-readable summary."""
        lines: list[str] = []
        if self.issue_tags:
            lines.append(f"issue_tags={', '.join(self.issue_tags)}")
        if self.desired_effects:
            lines.append(f"desired_effects={', '.join(self.desired_effects)}")
        if self.must_preserve:
            lines.append(f"must_preserve={', '.join(self.must_preserve)}")
        if self.must_avoid:
            lines.append(f"must_avoid={', '.join(self.must_avoid)}")
        return lines


@dataclass(slots=True)
class BottleAddition:
    """A persisted bottle-level intervention already applied to a live bottle."""

    material: str
    amount_ul: float | None = None
    dose_pct: float | None = None
    dilution: float | None = None
    note: str | None = None
    recorded_at: str | None = None

    def __post_init__(self) -> None:
        self.material = str(self.material).strip()
        if self.amount_ul is not None:
            self.amount_ul = float(self.amount_ul)
        if self.dose_pct is not None:
            self.dose_pct = float(self.dose_pct)
        if self.dilution is not None:
            self.dilution = float(self.dilution)
        if self.note is not None:
            self.note = str(self.note).strip() or None
        if self.recorded_at is not None:
            self.recorded_at = str(self.recorded_at).strip() or None

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "BottleAddition":
        return cls(
            material=str(value.get("material", "")).strip(),
            amount_ul=value.get("amount_ul"),  # type: ignore[arg-type]
            dose_pct=value.get("dose_pct"),  # type: ignore[arg-type]
            dilution=value.get("dilution"),  # type: ignore[arg-type]
            note=value.get("note") or value.get("reason"),  # type: ignore[arg-type]
            recorded_at=value.get("recorded_at"),  # type: ignore[arg-type]
        )

    def resolved_dose_pct(self, batch_volume_ml: float | None) -> float | None:
        """Resolve the addition to the engine's dose_pct convention."""
        if self.dose_pct is not None:
            return float(self.dose_pct)
        if self.amount_ul is None or batch_volume_ml is None or batch_volume_ml <= 0:
            return None
        return (float(self.amount_ul) / (batch_volume_ml * 1000.0)) * 100.0


@dataclass(slots=True)
class BottleState:
    """Persisted state for an already adjusted live bottle."""

    batch_volume_ml: float | None = None
    additions: list[BottleAddition] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    source_formula: str | None = None
    source_path: str | None = None

    def __post_init__(self) -> None:
        normalized: list[BottleAddition] = []
        for addition in self.additions:
            if isinstance(addition, BottleAddition):
                normalized.append(addition)
            elif isinstance(addition, Mapping):
                normalized.append(BottleAddition.from_mapping(addition))
        self.additions = normalized
        self.notes = normalize_descriptors(self.notes)
        if self.batch_volume_ml is not None:
            self.batch_volume_ml = float(self.batch_volume_ml)
        if self.source_formula is not None:
            self.source_formula = str(self.source_formula).strip() or None
        if self.source_path is not None:
            self.source_path = str(self.source_path).strip() or None

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "BottleState":
        return cls(
            batch_volume_ml=value.get("batch_volume_ml"),  # type: ignore[arg-type]
            additions=list(value.get("additions", [])) if isinstance(value.get("additions"), Sequence) else [],
            notes=_flatten_text_values(value.get("notes")),
            source_formula=value.get("source_formula"),  # type: ignore[arg-type]
            source_path=value.get("source_path"),  # type: ignore[arg-type]
        )

    def total_added_ul(self) -> float:
        return round(sum(addition.amount_ul or 0.0 for addition in self.additions), 1)

    def apply_to_formula(self, formula_vector):
        """Apply persisted bottle additions to a FormulaVector and renormalize."""
        from engine.optimizer.models import FormulaVector

        if not isinstance(formula_vector, FormulaVector):
            raise TypeError("BottleState.apply_to_formula expects a FormulaVector instance")

        if not self.additions:
            return FormulaVector(
                ingredients=dict(formula_vector.ingredients),
                dilutions=dict(formula_vector.dilutions),
            )

        batch_volume_ml = self.batch_volume_ml
        mod_ingredients = dict(formula_vector.ingredients)
        mod_dilutions = dict(formula_vector.dilutions)

        for addition in self.additions:
            dose_pct = addition.resolved_dose_pct(batch_volume_ml)
            if dose_pct is None or dose_pct <= 0:
                continue
            mod_ingredients[addition.material] = mod_ingredients.get(addition.material, 0.0) + dose_pct
            if addition.dilution is not None:
                mod_dilutions[addition.material] = addition.dilution

        total = sum(mod_ingredients.values())
        if total > 0:
            scale = sum(formula_vector.ingredients.values()) / total
            mod_ingredients = {name: pct * scale for name, pct in mod_ingredients.items()}

        return FormulaVector(ingredients=mod_ingredients, dilutions=mod_dilutions)


@dataclass(slots=True)
class InterventionContext:
    """Context for stage-aware recommendation generation."""

    mode: InterventionMode = "pre_mix"
    batch_volume_ml: float | None = None
    concentration_pct: float | None = None
    category_hint: str | None = None
    target_style: str | None = None
    target_axes: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    observation_profile: ObservationProfile = field(default_factory=ObservationProfile)
    bottle_state: BottleState | None = None

    def __post_init__(self) -> None:
        self.mode = normalize_intervention_mode(self.mode)
        self.observations = normalize_observation_tags(self.observations)
        if isinstance(self.observation_profile, Mapping):
            self.observation_profile = ObservationProfile.from_value(self.observation_profile)
        elif not isinstance(self.observation_profile, ObservationProfile):
            self.observation_profile = ObservationProfile.from_value(self.observation_profile)
        if isinstance(self.bottle_state, Mapping):
            self.bottle_state = BottleState.from_mapping(self.bottle_state)
        if self.category_hint:
            self.category_hint = self.category_hint.strip()
        if self.target_style:
            self.target_style = self.target_style.strip()
        self.target_axes = [
            axis.strip().lower().replace(" ", "_")
            for axis in self.target_axes
            if axis and axis.strip()
        ]
        merged_observations = [*self.observations, *self.observation_profile.issue_tags]
        self.observations = normalize_observation_tags(merged_observations)

    @property
    def is_post_mix(self) -> bool:
        return self.mode == "post_mix"

    @property
    def is_between_mix(self) -> bool:
        return self.mode == "between_mix"

    @property
    def is_pre_mix(self) -> bool:
        return self.mode == "pre_mix"

    def all_hint_text(self) -> list[str]:
        """Return legacy-compatible text hints from both loose and structured input."""
        return [
            *self.observations,
            *self.observation_profile.all_text_hints(),
        ]


def additive_dose_ul_from_pct(dose_pct: float, batch_volume_ml: float | None) -> int | None:
    """Convert a % concentrate intervention into a bottle-addition estimate in µL.

    For post-mix interventions we need a practical operator-facing estimate.
    We intentionally use a conservative scale based on total bottle volume, not
    a full reformulation model, because post-mix edits are top-up operations.
    """
    if batch_volume_ml is None or batch_volume_ml <= 0:
        return None
    return max(1, round(batch_volume_ml * 1000 * (dose_pct / 100.0)))
