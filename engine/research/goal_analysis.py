"""Goal-directed perfume analysis and controlled modification hypotheses.

This module is the practical synthesis layer between formula composition,
operator observations, admitted endpoint results, and the project's existing
perfumery intervention knowledge.  It deliberately produces *clues* and small
controlled comparisons rather than a beauty score or an automatic remix.

The minimum useful request is a formula plus a plain-language goal.  Bottle
photographs, purchase receipts, lot numbers, headspace measurements, and
density records are not prerequisites for hypothesis generation.  Those facts
remain relevant only when a later claim or physical conversion actually needs
them.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from dataclasses import field as dataclass_field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, Sequence

from engine.formulation_intelligence.literature_knowledge import retrieve_formulation_knowledge
from engine.intervention_context import normalize_intervention_mode
from engine.intervention_profiles import (
    normalize_observation_signal,
    suggest_interventions,
)
from engine.inventory_parser import load_user_compounding_holds
from engine.name_utils import normalize_name

from .commercial_references import build_commercial_reference_panel
from .contracts import FALSE_ACTION_AUTHORITY, stable_payload_hash
from .request_interpretation import (
    RequestInterpretationInputV1,
    interpret_request,
)

_VALID_UNITS = {
    "uL",
    "mL",
    "mg",
    "g",
    "percent_concentrate",
}

_NON_IDENTITY_TOKENS = {
    "absolute",
    "accord",
    "amber",
    "base",
    "carrier",
    "crystal",
    "crystals",
    "dpg",
    "ethanol",
    "essential",
    "extract",
    "fcf",
    "floral",
    "fragrance",
    "musk",
    "neat",
    "oil",
    "resinoid",
    "sicilian",
    "solution",
    "stock",
    "super",
    "wood",
    "woody",
}

_CORE_IDENTITY_ROLE = re.compile(
    r"\b(?:center|centre|identity|lead|main|primary|profile|recognizable|signature)\b",
    re.I,
)
_MODIFIER_ROLE = re.compile(
    r"\b(?:accent|bridge|continuity|edge|extend|extension|link|modifier|support|trace)\b",
    re.I,
)

_EXPLICIT_INCREASE_DIRECTION = re.compile(
    r"\b(?:more|increase|boost|stronger|raise|higher)\b",
    re.IGNORECASE,
)
_NEGATIVE_DIRECTION = re.compile(
    r"\b(?:less|reduce|decrease|weaken|soften|tone\s+down|mute|remove|cut)\b",
    re.IGNORECASE,
)

# Plain-language goals are normalized to the existing intervention rule
# vocabulary.  This is a transparent rule map, not a learned sensory model.
_GOAL_SIGNAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "needs_lift",
        re.compile(r"\b(?:lift|sparkle|brighter|brightness|radiance|airy|airier)\b", re.I),
    ),
    (
        "needs_diffusion",
        re.compile(r"\b(?:diffusion|diffusive|projection|project|bloom|sillage)\b", re.I),
    ),
    (
        "needs_texture",
        re.compile(r"\b(?:texture|textural|cushion|silky|velvety|body)\b", re.I),
    ),
    (
        "needs_depth",
        re.compile(r"\b(?:depth|deeper|dimensional|dimension|layered|layering)\b", re.I),
    ),
    (
        "needs_warmth",
        re.compile(r"\b(?:warmth|warmer|warm|rounder|rounded|cozier|cozy)\b", re.I),
    ),
    (
        "needs_skin",
        re.compile(r"\b(?:skin|intimate|intimacy|skinlike|skin-like)\b", re.I),
    ),
    (
        "drydown_thin",
        re.compile(r"\b(?:longevity|longer|lasting|last\s+longer|drydown\s+weak|persistent)\b", re.I),
    ),
    (
        "too_sweet",
        re.compile(r"\b(?:less\s+sweet|reduce\s+sweetness|too\s+sweet|less\s+gourmand)\b", re.I),
    ),
    (
        "too_heavy",
        re.compile(r"\b(?:less\s+heavy|lighter|reduce\s+density|too\s+dense|too\s+heavy)\b", re.I),
    ),
    (
        "too_sharp",
        re.compile(r"\b(?:less\s+sharp|softer\s+opening|too\s+sharp|too\s+piercing)\b", re.I),
    ),
    (
        "too_flat",
        re.compile(r"\b(?:less\s+flat|less\s+linear|too\s+flat|too\s+linear|more\s+movement)\b", re.I),
    ),
    (
        "heart_thin",
        re.compile(r"\b(?:stronger\s+heart|heart\s+thin|heart\s+weak|more\s+heart)\b", re.I),
    ),
    (
        "too_woody",
        re.compile(r"\b(?:less\s+woody|reduce\s+wood|too\s+woody)\b", re.I),
    ),
    (
        "too_musky",
        re.compile(r"\b(?:less\s+musky|reduce\s+musk|too\s+musky)\b", re.I),
    ),
)

_EVALUATION_WINDOW_PATTERNS: tuple[
    tuple[str, int | None, re.Pattern[str]], ...
] = (
    (
        "OPENING",
        0,
        re.compile(r"\b(?:opening|first\s+blast|immediately|initial)\b", re.I),
    ),
    (
        "FIVE_MINUTES",
        300,
        re.compile(r"\b(?:5|five)\s*(?:m|min|mins|minute|minutes)\b", re.I),
    ),
    (
        "THIRTY_MINUTES",
        1800,
        re.compile(r"\b(?:30|thirty)\s*(?:m|min|mins|minute|minutes)\b", re.I),
    ),
    (
        "TWO_HOURS",
        7200,
        re.compile(r"\b(?:2|two)\s*(?:h|hr|hrs|hour|hours)\b", re.I),
    ),
    (
        "FOUR_HOURS",
        14400,
        re.compile(r"\b(?:4|four)\s*(?:h|hr|hrs|hour|hours)\b", re.I),
    ),
    (
        "HEART",
        None,
        re.compile(r"\b(?:heart|mid|middle)\b", re.I),
    ),
    (
        "DRYDOWN",
        None,
        re.compile(r"\b(?:drydown|dry-down|dry\s+down|late\s+stage)\b", re.I),
    ),
)

_RELATIVE_WINDOWS: dict[str, tuple[Decimal, Decimal]] = {
    "trace": (Decimal("2.5"), Decimal("5")),
    "accent": (Decimal("5"), Decimal("10")),
    "bridge": (Decimal("7.5"), Decimal("15")),
    "structure": (Decimal("10"), Decimal("20")),
}

_OPTIONAL_PERSONAL_RESEARCH_INPUTS = (
    "bottle photographs",
    "label photographs",
    "purchase receipts",
    "exact supplier lot number",
    "density when no mass-volume conversion is requested",
    "instrumental headspace measurements",
    "measured intensity-curve binding",
    "commercial release documentation",
)


def _text(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty text")
    return text


def _decimal_text(value: object, field_name: str) -> str:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric, not boolean")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite decimal") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{field_name} must be finite and greater than zero")
    rendered = format(number, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _dedupe_text(values: Iterable[object]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        key = " ".join(text.casefold().split())
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return tuple(result)


def _slug(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.casefold())).strip("_")


def _render_decimal(number: Decimal) -> str:
    rendered = format(number, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _material_tokens(value: str) -> tuple[str, ...]:
    tokens = re.findall(r"[a-z0-9]+", value.casefold())
    return tuple(
        token
        for token in tokens
        if len(token) >= 4 and token not in _NON_IDENTITY_TOKENS and not token.isdigit()
    )


@dataclass(frozen=True, slots=True)
class GoalFormulaRowV1:
    """One formula row sufficient for goal analysis.

    Exact lot and density metadata intentionally do not belong to this minimal
    contract.  A later physical conversion or claim can request them when they
    are actually relevant.
    """

    row_id: str
    material: str
    amount_decimal: str
    unit: str
    stock_fraction_decimal: str | None = None
    stock_basis: str = "UNKNOWN"
    basket: str | None = None
    role: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "row_id", _text(self.row_id, "row_id"))
        object.__setattr__(self, "material", _text(self.material, "material"))
        object.__setattr__(
            self,
            "amount_decimal",
            _decimal_text(self.amount_decimal, "amount_decimal"),
        )
        if self.unit not in _VALID_UNITS:
            raise ValueError(f"unsupported formula-row unit: {self.unit}")
        if self.stock_fraction_decimal is not None:
            fraction = Decimal(
                _decimal_text(self.stock_fraction_decimal, "stock_fraction_decimal")
            )
            if fraction > 1:
                raise ValueError("stock_fraction_decimal cannot exceed one")
            object.__setattr__(self, "stock_fraction_decimal", format(fraction, "f"))
        object.__setattr__(self, "stock_basis", _text(self.stock_basis, "stock_basis").upper())
        if self.basket is not None:
            basket = str(self.basket).strip()
            object.__setattr__(self, "basket", basket or None)
        if self.role is not None:
            role = str(self.role).strip()
            object.__setattr__(self, "role", role or None)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GoalAnalysisRequestV1:
    formula_id: str
    formula_name: str
    rows: tuple[GoalFormulaRowV1, ...]
    goals: tuple[str, ...]
    observations: tuple[str, ...] = ()
    must_preserve: tuple[str, ...] = ()
    must_avoid: tuple[str, ...] = ()
    family: str | None = None
    profile: str | None = None
    mode: str = "pre_mix"
    available_materials: tuple[str, ...] = ()
    endpoint_results: tuple[Mapping[str, Any], ...] = ()
    max_hypotheses: int = 3
    original_request: str | None = None
    desired_changes: tuple[str, ...] = ()
    execution_strategy: str | None = None
    appeal_mode: str | None = None
    comparison_evidence: str = "DOCUMENT_ONLY"
    reference_panel_id: str | None = None
    target_population: str | None = None
    requested_evaluation_windows: tuple[str, ...] = ()
    application_context: str | None = None
    active_bottle_id: str | None = None
    known_references: tuple[str, ...] = ()
    market_evidence_as_of_date: str = dataclass_field(default_factory=lambda: date.today().isoformat())

    def __post_init__(self) -> None:
        object.__setattr__(self, "formula_id", _text(self.formula_id, "formula_id"))
        object.__setattr__(self, "formula_name", _text(self.formula_name, "formula_name"))
        rows = tuple(self.rows)
        if not rows:
            raise ValueError("at least one formula row is required")
        if any(not isinstance(row, GoalFormulaRowV1) for row in rows):
            raise TypeError("rows must contain GoalFormulaRowV1 values")
        if len({row.row_id for row in rows}) != len(rows):
            raise ValueError("formula row IDs must be unique")
        object.__setattr__(self, "rows", rows)
        goals = _dedupe_text(self.goals)
        if not goals:
            raise ValueError("at least one analysis goal is required")
        object.__setattr__(self, "goals", goals)
        object.__setattr__(self, "observations", _dedupe_text(self.observations))
        object.__setattr__(self, "must_preserve", _dedupe_text(self.must_preserve))
        object.__setattr__(self, "must_avoid", _dedupe_text(self.must_avoid))
        object.__setattr__(self, "available_materials", _dedupe_text(self.available_materials))
        object.__setattr__(self, "desired_changes", _dedupe_text(self.desired_changes))
        object.__setattr__(
            self,
            "requested_evaluation_windows",
            _dedupe_text(self.requested_evaluation_windows),
        )
        object.__setattr__(self, "known_references", _dedupe_text(self.known_references))
        object.__setattr__(self, "endpoint_results", tuple(self.endpoint_results))
        raw_mode = str(self.mode).strip().lower().replace("-", "_").replace(" ", "_")
        if raw_mode not in {
            "pre_mix",
            "between_mix",
            "post_mix",
            "postmix",
            "post",
            "between",
            "between_batches",
            "between_mixes",
        }:
            raise ValueError(f"unsupported intervention mode: {self.mode}")
        object.__setattr__(self, "mode", normalize_intervention_mode(self.mode))
        if self.family is not None:
            object.__setattr__(self, "family", _text(self.family, "family"))
        if self.profile is not None:
            object.__setattr__(self, "profile", _text(self.profile, "profile"))
        for field in (
            "original_request",
            "reference_panel_id",
            "target_population",
            "application_context",
            "active_bottle_id",
        ):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _text(value, field))
        # Constructing the deterministic request object is the strict enum
        # validation boundary.  Unknown modes must not silently become
        # pre_mix or any other workflow.
        validated_interpretation = interpret_request(RequestInterpretationInputV1(
            original_request=self.original_request or "; ".join(goals),
            known_materials=tuple(row.material for row in rows),
            known_references=self.known_references,
            desired_changes=self.desired_changes or goals,
            must_preserve=self.must_preserve,
            must_avoid=self.must_avoid,
            evaluation_windows=self.requested_evaluation_windows,
            execution_strategy=self.execution_strategy,
            appeal_mode=self.appeal_mode,
            comparison_evidence=self.comparison_evidence,
            reference_panel_id=self.reference_panel_id,
            target_population=self.target_population,
            application_context=self.application_context,
            active_bottle_id=self.active_bottle_id,
        ))
        object.__setattr__(
            self,
            "execution_strategy",
            validated_interpretation["execution_strategy"],
        )
        object.__setattr__(self, "appeal_mode", validated_interpretation["appeal_mode"])
        object.__setattr__(
            self,
            "comparison_evidence",
            validated_interpretation["comparison_evidence"],
        )
        object.__setattr__(
            self,
            "market_evidence_as_of_date",
            _text(self.market_evidence_as_of_date, "market_evidence_as_of_date"),
        )
        if isinstance(self.max_hypotheses, bool) or not 1 <= int(self.max_hypotheses) <= 3:
            raise ValueError("max_hypotheses must be from one to three")
        object.__setattr__(self, "max_hypotheses", int(self.max_hypotheses))

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "goal-analysis-request-v2",
            "formula_id": self.formula_id,
            "formula_name": self.formula_name,
            "rows": [row.as_dict() for row in self.rows],
            "goals": list(self.goals),
            "observations": list(self.observations),
            "must_preserve": list(self.must_preserve),
            "must_avoid": list(self.must_avoid),
            "family": self.family,
            "profile": self.profile,
            "mode": self.mode,
            "available_materials": list(self.available_materials),
            "endpoint_results": [dict(row) for row in self.endpoint_results],
            "max_hypotheses": self.max_hypotheses,
            "original_request": self.original_request,
            "desired_changes": list(self.desired_changes),
            "execution_strategy": self.execution_strategy,
            "appeal_mode": self.appeal_mode,
            "comparison_evidence": self.comparison_evidence,
            "reference_panel_id": self.reference_panel_id,
            "target_population": self.target_population,
            "requested_evaluation_windows": list(self.requested_evaluation_windows),
            "application_context": self.application_context,
            "active_bottle_id": self.active_bottle_id,
            "known_references": list(self.known_references),
            "market_evidence_as_of_date": self.market_evidence_as_of_date,
        }


def _goal_signals(request: GoalAnalysisRequestV1) -> tuple[str, ...]:
    signals: list[str] = []
    combined = [*request.goals, *request.observations]
    for text in combined:
        normalized = normalize_observation_signal(text)
        if normalized:
            signals.append(normalized)
        for signal, pattern in _GOAL_SIGNAL_PATTERNS:
            if pattern.search(text):
                signals.append(signal)
    return _dedupe_text(signals)


def _goal_direction(goal: str) -> str:
    negative = bool(_NEGATIVE_DIRECTION.search(goal))
    positive = bool(_EXPLICIT_INCREASE_DIRECTION.search(goal))
    if negative and not positive:
        return "DECREASE"
    if positive and not negative:
        return "INCREASE"
    return "BIDIRECTIONAL"


def _evaluation_windows(goals: Sequence[str]) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    seen: set[tuple[str, int | None]] = set()
    for goal in goals:
        for label, seconds, pattern in _EVALUATION_WINDOW_PATTERNS:
            if not pattern.search(goal):
                continue
            key = (label, seconds)
            if key in seen:
                continue
            seen.add(key)
            windows.append(
                {
                    "label": label,
                    "time_seconds": seconds,
                    "source": "USER_STATED_GOAL",
                }
            )
    return windows


def _goal_row_groups(request: GoalAnalysisRequestV1) -> list[dict[str, Any]]:
    """Return formula blocks explicitly named by a goal.

    A shared token such as ``lavender`` intentionally groups both lavender oil
    rows so a test can preserve their internal ratio.
    """

    groups: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for goal in request.goals:
        goal_text = " ".join(goal.casefold().split())
        token_rows: dict[str, list[GoalFormulaRowV1]] = {}
        for row in request.rows:
            for token in _material_tokens(row.material):
                if re.search(rf"\b{re.escape(token)}\b", goal_text):
                    token_rows.setdefault(token, []).append(row)
        for token, rows in token_rows.items():
            core_rows = [
                row
                for row in rows
                if row.role and _CORE_IDENTITY_ROLE.search(row.role)
            ]
            modifier_rows = [
                row
                for row in rows
                if row.role
                and _MODIFIER_ROLE.search(row.role)
                and not _CORE_IDENTITY_ROLE.search(row.role)
            ]
            selected_rows = (
                [row for row in rows if row not in modifier_rows]
                if core_rows
                else rows
            )
            if not selected_rows:
                selected_rows = rows
            held_rows = [row for row in rows if row not in selected_rows]
            row_ids = tuple(sorted(row.row_id for row in selected_rows))
            key = (token, row_ids)
            if key in seen:
                continue
            seen.add(key)
            groups.append(
                {
                    "goal": goal,
                    "matched_term": token,
                    "direction": _goal_direction(goal),
                    "rows": tuple(selected_rows),
                    "held_rows": tuple(held_rows),
                }
            )
    return groups


def _relative_trial(
    rows: Sequence[GoalFormulaRowV1],
    *,
    direction: str,
    dose_style: str,
) -> dict[str, Any]:
    low, high = _RELATIVE_WINDOWS.get(dose_style, _RELATIVE_WINDOWS["bridge"])
    if direction == "DECREASE":
        low_change, high_change = -low, -high
    elif direction == "INCREASE":
        low_change, high_change = low, high
    else:
        low_change, high_change = -low, low
    units = {row.unit for row in rows}
    current_total: str | None = None
    unit: str | None = None
    if len(units) == 1:
        unit = next(iter(units))
        current_total = format(
            sum((Decimal(row.amount_decimal) for row in rows), Decimal("0")),
            "f",
        )
    def variant(change_percent: Decimal) -> dict[str, Any]:
        factor = Decimal("1") + change_percent / Decimal("100")
        targets = [
            {
                "row_id": row.row_id,
                "material": row.material,
                "current_amount_decimal": row.amount_decimal,
                "target_amount_decimal": _render_decimal(
                    Decimal(row.amount_decimal) * factor
                ),
                "delta_amount_decimal": _render_decimal(
                    Decimal(row.amount_decimal) * change_percent / Decimal("100")
                ),
                "unit": row.unit,
            }
            for row in rows
        ]
        target_total = (
            _render_decimal(Decimal(current_total) * factor)
            if current_total is not None
            else None
        )
        return {
            "relative_block_change_percent": _render_decimal(change_percent),
            "current_block_total_decimal": current_total,
            "target_block_total_decimal": target_total,
            "unit": unit,
            "row_targets": targets,
        }

    return {
        "control": "UNCHANGED_FORMULA",
        "low_variant": variant(low_change),
        "high_variant": variant(high_change),
        "internal_ratio_policy": "PRESERVE_CURRENT_BLOCK_RATIO",
        "constant_total_policy": "OFFSET_WITH_DECLARED_BALANCING_CARRIER_OR_ROW",
        "comparison_rule": "CHANGE_ONE_BLOCK_ONLY",
        "amount_authority": "UNROUNDED_DESIGN_TARGETS_NOT_MIXER_COMMANDS",
    }


def _addition_trial(dose_style: str) -> dict[str, Any]:
    return {
        "control": "UNCHANGED_FORMULA",
        "low_variant": "ONE_MINIMUM_MEASURABLE_STOCK_INCREMENT",
        "high_variant": "TWO_LOW_VARIANT_INCREMENTS",
        "dose_style": dose_style,
        "constant_total_policy": "OFFSET_WITH_DECLARED_BALANCING_CARRIER_OR_ROW",
        "comparison_rule": "ADD_ONE_CANDIDATE_ONLY",
        "exact_dose_state": "DEFERRED_UNTIL_STOCK_STRENGTH_AND_MEASUREMENT_INCREMENT_ARE_SELECTED",
    }


def _evolving_existing_addition_trial(
    rows: Sequence[GoalFormulaRowV1],
    *,
    dose_style: str,
    formula_totals_by_unit: Mapping[str, Decimal],
) -> dict[str, Any]:
    """Describe positive-only additions to the same physical bottle."""

    low, high = _RELATIVE_WINDOWS.get(dose_style, _RELATIVE_WINDOWS["bridge"])
    units = {row.unit for row in rows}

    def variant(change_percent: Decimal) -> dict[str, Any]:
        row_targets = []
        additions_by_unit: dict[str, Decimal] = {}
        for row in rows:
            delta = Decimal(row.amount_decimal) * change_percent / Decimal("100")
            additions_by_unit[row.unit] = additions_by_unit.get(row.unit, Decimal("0")) + delta
            row_targets.append(
                {
                    "row_id": row.row_id,
                    "material": row.material,
                    "current_amount_decimal": row.amount_decimal,
                    "delta_amount_decimal": _render_decimal(delta),
                    "resulting_amount_decimal": _render_decimal(Decimal(row.amount_decimal) + delta),
                    "unit": row.unit,
                    "operation": "ADDITIVE_ONLY",
                }
            )
        return {
            "relative_block_addition_percent": _render_decimal(change_percent),
            "row_targets": row_targets,
            "addition_totals_by_unit": {
                unit: _render_decimal(value) for unit, value in sorted(additions_by_unit.items())
            },
            "resulting_formula_totals_by_unit": {
                unit: _render_decimal(total + additions_by_unit.get(unit, Decimal("0")))
                for unit, total in sorted(formula_totals_by_unit.items())
            },
        }

    return {
        "control": "CURRENT_COMMITTED_BOTTLE_STATE",
        "low_variant": variant(low),
        "high_variant": variant(high),
        "units": sorted(units),
        "internal_ratio_policy": "PRESERVE_CURRENT_BLOCK_RATIO",
        "constant_total_policy": "NOT_APPLICABLE_EVOLVING_BOTTLE_TOTAL_INCREASES",
        "comparison_rule": "ADD_ONE_BLOCK_ONLY",
        "negative_delta_allowed": False,
        "removal_assumed": False,
        "amount_authority": "UNROUNDED_PROPOSAL_TARGETS_NOT_MIXER_COMMANDS",
    }


def _evolving_new_material_trial(dose_style: str) -> dict[str, Any]:
    trial = _addition_trial(dose_style)
    trial.update(
        {
            "control": "CURRENT_COMMITTED_BOTTLE_STATE",
            "constant_total_policy": "NOT_APPLICABLE_EVOLVING_BOTTLE_TOTAL_INCREASES",
            "negative_delta_allowed": False,
            "removal_assumed": False,
            "comparison_rule": "ADD_ONE_CANDIDATE_ONLY",
        }
    )
    return trial


def _applicable_endpoint_clues(
    endpoint_results: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    clues: list[dict[str, Any]] = []
    applicable_count = 0
    for index, endpoint in enumerate(endpoint_results):
        name = str(endpoint.get("endpoint", "UNKNOWN")).strip().upper() or "UNKNOWN"
        applicability = str(
            endpoint.get("applicability_state", endpoint.get("applicability", "UNAVAILABLE"))
        ).upper()
        value = endpoint.get("value")
        if applicability not in {"APPLICABLE", "PARTIAL"} or value is None:
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and not math.isfinite(float(value)):
            continue
        applicable_count += 1
        clues.append(
            {
                "clue_id": f"endpoint-{index + 1}",
                "evidence_class": "APPLICABLE_ENDPOINT_ESTIMATE",
                "endpoint": name,
                "statement": f"{name} supplied an applicable {applicability.lower()} estimate.",
                "value": value,
                "unit": endpoint.get("unit", endpoint.get("units")),
                "coverage": endpoint.get("coverage", endpoint.get("coverage_decimal")),
                "provenance": endpoint.get("provenance", endpoint.get("provenance_ids", [])),
                "action_authority": False,
            }
        )
    return clues, applicable_count


def _material_is_available(material: str, available: Sequence[str]) -> bool:
    if not available:
        return False
    target = _slug(material)
    return any(
        target == _slug(candidate)
        or target in _slug(candidate)
        or _slug(candidate) in target
        for candidate in available
    )


def _material_in_formula(material: str, rows: Sequence[GoalFormulaRowV1]) -> tuple[GoalFormulaRowV1, ...]:
    target = _slug(material)
    matches = [
        row
        for row in rows
        if target == _slug(row.material)
        or target in _slug(row.material)
        or _slug(row.material) in target
    ]
    return tuple(matches)


def _violates_avoid(material: str, rationale: str, avoid: Sequence[str]) -> bool:
    haystack = f"{material} {rationale}".casefold()
    return any(str(item).casefold() in haystack for item in avoid if str(item).strip())


def _commercial_concept_tags(request: GoalAnalysisRequestV1) -> tuple[str, ...]:
    """Derive literal concept tokens without inventing a commercial family."""

    source = " ".join(
        (
            request.formula_name,
            request.family or "",
            *request.goals,
        )
    ).casefold()
    source = re.sub(r"\b(?:no|not|without|avoid)\s+[^,.;]+", " ", source)
    for phrase in request.must_avoid:
        source = re.sub(rf"(?<!\w){re.escape(phrase)}(?!\w)", " ", source)
    return _dedupe_text(
        token
        for token in re.findall(r"[a-z][a-z0-9-]{2,}", source)
        if token not in {"make", "more", "less", "while", "with", "without"}
    )


def analyze_formula_for_goal(request: GoalAnalysisRequestV1) -> dict[str, Any]:
    """Return concise clues and an unordered controlled-comparison shortlist."""

    interpretation = interpret_request(
        RequestInterpretationInputV1(
            original_request=request.original_request or "; ".join(request.goals),
            known_materials=tuple(row.material for row in request.rows),
            known_references=request.known_references,
            desired_changes=request.desired_changes or request.goals,
            must_preserve=request.must_preserve,
            must_avoid=request.must_avoid,
            evaluation_windows=request.requested_evaluation_windows,
            execution_strategy=request.execution_strategy,
            appeal_mode=request.appeal_mode,
            comparison_evidence=request.comparison_evidence,
            reference_panel_id=request.reference_panel_id,
            target_population=request.target_population,
            application_context=request.application_context,
            active_bottle_id=request.active_bottle_id,
        )
    )
    request_payload = request.canonical_payload()
    hold_labels, hold_sha = load_user_compounding_holds()
    held_names = {normalize_name(label) for label in hold_labels}
    request_payload["user_compounding_holds_sha256"] = hold_sha
    knowledge = retrieve_formulation_knowledge(
        " ".join((request.formula_name or "", request.original_request or "", *request.goals)),
        avoid=tuple(interpretation["must_avoid"]),
        material_names=tuple(row.material for row in request.rows if Decimal(row.amount_decimal) > 0),
    )
    request_payload["knowledge_context"] = knowledge
    if interpretation["confirmation_required"]:
        report = {
            "schema_version": "goal-directed-formula-analysis-v2",
            "request_sha256": stable_payload_hash(request_payload),
            "formula_id": request.formula_id,
            "formula_name": request.formula_name,
            "request_interpretation": interpretation,
            "formulation_knowledge": knowledge,
            "status": "WITHHELD_REQUEST_AMBIGUOUS",
            "validation_state": "WITHHOLD_UNKNOWN",
            "applicability_state": "UNAVAILABLE",
            "clues": [],
            "modification_hypotheses": [],
            "selection": {
                "status": "WITHHELD_REQUEST_AMBIGUOUS",
                "ranked_candidates": [],
                "pareto_candidates": [],
                "unordered_candidates": [],
                "formula_action": "NO_CHANGE",
                "reason_codes": list(interpretation["ambiguities"]),
            },
            "minimum_next_evidence": "Confirm or correct the short interpretation card.",
            "prohibited_objectives_used": [],
            "beauty_score": None,
            "pleasantness": None,
            "personal_liking": None,
            "formula_modified": False,
            "physical_experiment_authorized": False,
            **FALSE_ACTION_AUTHORITY,
        }
        return {**report, "analysis_sha256": stable_payload_hash(report)}

    clues, endpoint_count = _applicable_endpoint_clues(request.endpoint_results)
    effective_preserve = tuple(interpretation["must_preserve"])
    effective_avoid = tuple(interpretation["must_avoid"])
    evaluation_windows = list(interpretation["evaluation_windows"])
    if request.original_request is None and not request.requested_evaluation_windows:
        # Preserve the v1 source label for callers that supplied the legacy
        # structured goals contract rather than a free-text request.
        evaluation_windows = _evaluation_windows(request.goals)
    elif not evaluation_windows:
        evaluation_windows = _evaluation_windows(request.goals)
    totals_by_unit: dict[str, Decimal] = {}
    for row in request.rows:
        totals_by_unit[row.unit] = totals_by_unit.get(row.unit, Decimal("0")) + Decimal(
            row.amount_decimal
        )
    hypotheses: list[dict[str, Any]] = []
    hypothesis_keys: set[tuple[str, str, tuple[str, ...]]] = set()
    evolving_bottle = interpretation["execution_strategy"] == "EVOLVING_BOTTLE"
    effective_max_hypotheses = min(request.max_hypotheses, 3)
    additive_repair_blocked = False
    commercial_panel: dict[str, Any] | None = None
    commercial_panel_withheld_reason: str | None = None
    if interpretation["appeal_mode"] == "GLOBAL_CROWD_PLEASING":
        try:
            commercial_panel = build_commercial_reference_panel(
                _commercial_concept_tags(request),
                as_of_date=request.market_evidence_as_of_date,
                panel_id=request.reference_panel_id,
            )
        except (KeyError, ValueError) as error:
            commercial_panel_withheld_reason = str(error)

    for index, observation in enumerate(request.observations, start=1):
        clues.append(
            {
                "clue_id": f"observation-{index}",
                "evidence_class": "USER_OBSERVATION",
                "endpoint": "OBSERVED_PERCEPT",
                "statement": observation,
                "action_authority": False,
            }
        )

    user_hold_blocked = False
    # First honor explicit material/block directions in the user's goal.
    for group in _goal_row_groups(request):
        rows = group["rows"]
        held_rows = group["held_rows"]
        material_label = " + ".join(row.material for row in rows)
        excluded_rows = [row for row in rows if normalize_name(row.material) in held_names]
        if excluded_rows:
            user_hold_blocked = True
            clues.append({
                "clue_id": "user-compounding-hold-" + group["matched_term"],
                "evidence_class": "USER_COMPOUNDING_EXCLUSION",
                "endpoint": "COMPOUNDING_ELIGIBILITY",
                "statement": (
                    "This block contains a material temporarily excluded by the user: "
                    + ", ".join(row.material for row in excluded_rows)
                    + ". Stock details do not clear this hold."
                ),
                "row_ids": [row.row_id for row in excluded_rows],
                "action_authority": False,
            })
            continue
        direction = group["direction"]
        if evolving_bottle and direction == "DECREASE":
            additive_repair_blocked = True
            clues.append(
                {
                    "clue_id": f"additive-limit-{group['matched_term']}",
                    "evidence_class": "PHYSICAL_OPERATION_CONSTRAINT",
                    "endpoint": "EVOLVING_BOTTLE_FEASIBILITY",
                    "statement": (
                        f"The current bottle cannot remove the existing {material_label} dose. "
                        "Only a counterbalancing addition, compatible dilution, or explicitly "
                        "chosen new formula can test this direction."
                    ),
                    "row_ids": [row.row_id for row in rows],
                    "action_authority": False,
                }
            )
            continue
        trial_direction = "INCREASE" if evolving_bottle else direction
        action = (
            "INCREASE_EXISTING_BLOCK"
            if evolving_bottle
            else (
                "TEST_EXISTING_BLOCK_LEVEL"
                if direction == "BIDIRECTIONAL"
                else f"{direction}_EXISTING_BLOCK"
            )
        )
        key = (action, group["matched_term"], tuple(row.row_id for row in rows))
        if key in hypothesis_keys:
            continue
        hypothesis_keys.add(key)
        clues.append(
            {
                "clue_id": f"formula-block-{group['matched_term']}",
                "evidence_class": "FORMULA_COMPOSITION_FACT",
                "endpoint": "FORMULA_STRUCTURE",
                "statement": (
                    f"The goal explicitly names {group['matched_term']}, and the formula "
                    f"contains {len(rows)} matching row(s): {material_label}."
                    + (
                        " The matched block is "
                        f"{_render_decimal(sum((Decimal(row.amount_decimal) for row in rows), Decimal('0')))} "
                        f"{rows[0].unit} of {_render_decimal(totals_by_unit[rows[0].unit])} "
                        f"{rows[0].unit} parsed in that unit "
                        f"({_render_decimal((sum((Decimal(row.amount_decimal) for row in rows), Decimal('0')) / totals_by_unit[rows[0].unit] * Decimal('100')).quantize(Decimal('0.0001')))}%)."
                        if len({row.unit for row in rows}) == 1
                        and totals_by_unit[rows[0].unit] > 0
                        else ""
                    )
                    + (
                        " Role-labeled modifier row(s) remain fixed in this test: "
                        + ", ".join(row.material for row in held_rows)
                        + "."
                        if held_rows
                        else ""
                    )
                ),
                "row_ids": [row.row_id for row in rows],
                "held_constant_row_ids": [row.row_id for row in held_rows],
                "action_authority": False,
            }
        )
        hypotheses.append(
            {
                "hypothesis_id": "direct-" + stable_payload_hash(
                    {
                        "goal": group["goal"],
                        "term": group["matched_term"],
                        "rows": [row.row_id for row in rows],
                        "direction": direction,
                    }
                )[:12],
                "goal": group["goal"],
                "action": action,
                "material_or_block": material_label,
                "target_row_ids": [row.row_id for row in rows],
                "held_constant_row_ids": [row.row_id for row in held_rows],
                "evidence_class": "EXPLICIT_GOAL_PLUS_FORMULA_FACT",
                "rationale": (
                    "The named block is present. In the evolving bottle, only a small "
                    "ratio-preserving positive addition is physically available; compare it "
                    "with the current committed state before adding more."
                    if evolving_bottle
                    else
                    "The named block is present, but perceptual clarity does not establish "
                    "whether more or less material will help. A small ratio-preserving "
                    "two-sided dose ladder is the shortest controlled test."
                    if direction == "BIDIRECTIONAL"
                    else "The named block is present, so a small ratio-preserving dose "
                    "ladder is the shortest controlled test of the requested direction."
                ),
                "expected_direction": (
                    "INCREASE"
                    if evolving_bottle
                    else ("EMPIRICALLY_DETERMINE" if direction == "BIDIRECTIONAL" else direction)
                ),
                "trial": (
                    _evolving_existing_addition_trial(
                        rows,
                        dose_style="bridge",
                        formula_totals_by_unit=totals_by_unit,
                    )
                    if evolving_bottle
                    else _relative_trial(
                        rows,
                        direction=trial_direction,
                        dose_style="bridge",
                    )
                ),
                "success_criteria": {
                    "desired": list(request.goals),
                    "must_preserve": list(effective_preserve),
                    "must_avoid": list(effective_avoid),
                    "evaluation_windows": evaluation_windows,
                },
                "uncertainty": (
                    "Changing the named material or block may alter several perceptual facets; "
                    "the result must be smelled against the unchanged control."
                ),
                "formula_optimization_authority": False,
                "compounding_action_authority": False,
            }
        )

    # Then use the existing transparent perfumery-rule registry for generic
    # goals such as lift, diffusion, warmth, texture, or depth.
    signals = _goal_signals(request)
    rule_recommendations = suggest_interventions(
        observations=signals,
        family=request.family,
        profile=request.profile,
        mode=request.mode,
        available_materials=request.available_materials or None,
        limit=max(effective_max_hypotheses * 2, 5),
    )
    for recommendation in rule_recommendations:
        for material in recommendation.materials:
            if len(hypotheses) >= effective_max_hypotheses:
                break
            if normalize_name(material) in held_names:
                user_hold_blocked = True
                continue
            if request.available_materials and not _material_is_available(
                material, request.available_materials
            ):
                continue
            if _violates_avoid(material, recommendation.rationale, effective_avoid):
                continue
            existing_rows = _material_in_formula(material, request.rows)
            action = "INCREASE_EXISTING_MATERIAL" if existing_rows else "ADD_CANDIDATE_MATERIAL"
            row_ids = tuple(row.row_id for row in existing_rows)
            key = (action, _slug(material), row_ids)
            if key in hypothesis_keys:
                continue
            hypothesis_keys.add(key)
            goal = next(
                (
                    item
                    for item in request.goals
                    if recommendation.signal in _goal_signals(
                        GoalAnalysisRequestV1(
                            formula_id=request.formula_id,
                            formula_name=request.formula_name,
                            rows=request.rows,
                            goals=(item,),
                        )
                    )
                ),
                request.goals[0],
            )
            hypotheses.append(
                {
                    "hypothesis_id": "rule-" + stable_payload_hash(
                        {
                            "goal": goal,
                            "signal": recommendation.signal,
                            "material": material,
                            "profile": recommendation.profile,
                        }
                    )[:12],
                    "goal": goal,
                    "action": action,
                    "material_or_block": material,
                    "target_row_ids": list(row_ids),
                    "evidence_class": "RULE_BASED_PERFUMERY_HYPOTHESIS",
                    "rationale": recommendation.rationale,
                    "expected_direction": recommendation.signal,
                    "trial": (
                        _evolving_existing_addition_trial(
                            existing_rows,
                            dose_style=recommendation.dose_style,
                            formula_totals_by_unit=totals_by_unit,
                        )
                        if existing_rows and evolving_bottle
                        else _relative_trial(
                            existing_rows,
                            direction="INCREASE",
                            dose_style=recommendation.dose_style,
                        )
                        if existing_rows
                        else _evolving_new_material_trial(recommendation.dose_style)
                        if evolving_bottle
                        else _addition_trial(recommendation.dose_style)
                    ),
                    "success_criteria": {
                        "desired": list(request.goals),
                        "must_preserve": list(effective_preserve),
                        "must_avoid": list(effective_avoid),
                        "evaluation_windows": evaluation_windows,
                    },
                    "profile": recommendation.profile,
                    "profile_label": recommendation.profile_label,
                    "rule_confidence": recommendation.confidence,
                    "uncertainty": (
                        "The material-function link is a perfumery design hypothesis, not a "
                        "measured prediction for this formula. Compare against the unchanged control."
                    ),
                    "formula_optimization_authority": False,
                    "compounding_action_authority": False,
                }
            )
        if len(hypotheses) >= effective_max_hypotheses:
            break

    hypotheses = hypotheses[:effective_max_hypotheses]
    for hypothesis in hypotheses:
        clues.append(
            {
                "clue_id": f"hypothesis-{hypothesis['hypothesis_id']}",
                "evidence_class": hypothesis["evidence_class"],
                "endpoint": "DESIGN_HYPOTHESIS",
                "statement": (
                    f"Test {hypothesis['action'].lower().replace('_', ' ')} for "
                    f"{hypothesis['material_or_block']}."
                ),
                "action_authority": False,
            }
        )

    if endpoint_count == 0:
        clues.append(
            {
                "clue_id": "measured-endpoint-gap",
                "evidence_class": "DATA_GAP",
                "endpoint": "MEASURED_OUTCOME",
                "statement": (
                    "No applicable measured outcome was supplied. The modification set is an "
                    "experiment design, not a predicted sensory winner."
                ),
                "action_authority": False,
            }
        )

    status = (
        "GOAL_DIRECTED_HYPOTHESES_READY"
        if hypotheses
        else "ADDITIVE_REPAIR_NOT_FEASIBLE"
        if additive_repair_blocked
        else "WITHHELD_USER_COMPOUNDING_HOLD"
        if user_hold_blocked
        else "GOAL_NOT_MAPPED"
    )
    validation = "ADVISORY_FINDINGS" if hypotheses else "WITHHOLD_UNKNOWN"
    applicability = "PARTIAL" if hypotheses or additive_repair_blocked else "UNAVAILABLE"
    formula_action = "PROPOSE_CONTROLLED_VARIANTS" if hypotheses else "NO_CHANGE"
    selection_status = (
        (
            "UNORDERED_HYPOTHESES"
            if evolving_bottle
            or interpretation["appeal_mode"] == "GLOBAL_CROWD_PLEASING"
            else "UNORDERED_CONTROLLED_HYPOTHESES"
        )
        if hypotheses
        else "ADDITIVE_REPAIR_NOT_FEASIBLE"
        if additive_repair_blocked
        else "WITHHELD_USER_COMPOUNDING_HOLD"
        if user_hold_blocked
        else "WITHHELD_GOAL_NOT_MAPPED"
    )
    has_bidirectional_trial = any(
        hypothesis.get("expected_direction") == "EMPIRICALLY_DETERMINE"
        for hypothesis in hypotheses
    )
    # Applicable endpoints and direct observations retain precedence. Reviewed
    # knowledge adds bounded comparison clues, never automatic dose changes.
    for claim in knowledge["claims"][:4]:
        clues.append({
            "clue_id": f"literature-{claim['claim_id']}",
            "evidence_class": claim["kind"],
            "endpoint": "FORMULATION_KNOWLEDGE_ONLY",
            "statement": claim["statement"],
            "source_ids": claim["source_ids"],
            "pack_sha256": knowledge["pack_sha256"],
            "action_authority": False,
        })
    for card in knowledge.get("subtype_context", {}).get("cards", [])[:2]:
        clues.append({
            "clue_id": f"subtype-{card['subtype_id']}",
            "evidence_class": "UNTESTED_SUBTYPE_HYPOTHESIS",
            "endpoint": "FORMULATION_KNOWLEDGE_ONLY",
            "statement": card["construction_hypothesis"],
            "source_evidence_summary": card["evidence_summary"],
            "negative_space": card["negative_space"],
            "comparison_question": card["comparison"]["question"],
            "source_ids": [binding["source_id"] for binding in card["source_bindings"]],
            "subtype_research_sha256": knowledge["subtype_research_sha256"],
            "action_authority": False,
        })
    for dossier in knowledge.get("construction_context", {}).get("dossiers", [])[:2]:
        clues.append({
            "clue_id": f"construction-{dossier['package_id']}",
            "evidence_class": "UNTESTED_ARCHITECTURE_HYPOTHESIS",
            "endpoint": "FORMULATION_KNOWLEDGE_ONLY",
            "statement": dossier["recognizers"][0],
            "negative_space": dossier["negative_space"],
            "comparison_question": dossier["comparison"]["question"],
            "source_ids": [binding["source_id"] for binding in dossier["source_bindings"]],
            "construction_library_sha256": knowledge["construction_library_sha256"],
            "action_authority": False,
        })
    report = {
        "schema_version": "goal-directed-formula-analysis-v2",
        "request_sha256": stable_payload_hash(request_payload),
        "user_compounding_holds_sha256": hold_sha,
        "formula_id": request.formula_id,
        "formula_name": request.formula_name,
        "goals": list(request.goals),
        "observations": list(request.observations),
        "must_preserve": list(effective_preserve),
        "must_avoid": list(effective_avoid),
        "evaluation_windows": evaluation_windows,
        "request_interpretation": interpretation,
        "formulation_knowledge": knowledge,
        "commercial_reference_panel": commercial_panel,
        "commercial_reference_panel_state": (
            "MARKET_SELECTED_REFERENCE_PANEL"
            if commercial_panel is not None
            else "WITHHELD_NO_APPLICABLE_CURRENT_PANEL"
            if interpretation["appeal_mode"] == "GLOBAL_CROWD_PLEASING"
            else "NOT_REQUESTED"
        ),
        "commercial_reference_panel_withheld_reason": commercial_panel_withheld_reason,
        "status": status,
        "validation_state": validation,
        "applicability_state": applicability,
        "evidence_summary": {
            "applicable_endpoint_count": endpoint_count,
            "user_observation_count": len(request.observations),
            "formula_fact_count": sum(
                clue["evidence_class"] == "FORMULA_COMPOSITION_FACT" for clue in clues
            ),
            "rule_hypothesis_count": sum(
                hypothesis["evidence_class"] == "RULE_BASED_PERFUMERY_HYPOTHESIS"
                for hypothesis in hypotheses
            ),
        },
        "clues": clues,
        "modification_hypotheses": hypotheses,
        "selection": {
            "status": selection_status,
            "ranked_candidates": [],
            "pareto_candidates": [],
            "unordered_candidates": [
                hypothesis["hypothesis_id"] for hypothesis in hypotheses
            ],
            "formula_action": formula_action,
            "reason_codes": (
                (["MEASURED_OUTCOME_NOT_SUPPLIED"] if endpoint_count == 0 else [])
                + (["ADDITIVE_REPAIR_NOT_FEASIBLE"] if additive_repair_blocked else [])
                + (
                    ["DOCUMENTARY_MARKET_REFERENCES_ARE_NOT_LIKING_LABELS"]
                    if commercial_panel is not None
                    else []
                )
                + (
                    ["NO_APPLICABLE_CURRENT_COMMERCIAL_REFERENCE_PANEL"]
                    if commercial_panel_withheld_reason is not None
                    else []
                )
            ),
        },
        "minimum_next_evidence": (
            "Compare the unchanged control, lower-block variant, and higher-block variant "
            "at the requested evaluation window; choose a direction only from that comparison."
            if has_bidirectional_trial
            else "Smell the unchanged control and one low variant first; advance to the high "
            "variant only if the requested direction improves without violating preserve/avoid criteria."
            if hypotheses
            else "Describe one concrete perceptual problem or desired direction."
        ),
        "not_required_for_hypothesis_generation": list(
            _OPTIONAL_PERSONAL_RESEARCH_INPUTS
        ),
        "prohibited_objectives_used": [],
        "beauty_score": None,
        "pleasantness": None,
        "personal_liking": None,
        "population_liking_state": "POPULATION_LIKING_NOT_ESTABLISHED",
        "proprietary_composition_state": (
            "PROPRIETARY_COMPOSITION_UNKNOWN" if commercial_panel is not None else None
        ),
        "additive_repair_state": (
            "ADDITIVE_REPAIR_NOT_FEASIBLE" if additive_repair_blocked else "NOT_BLOCKED"
        ),
        "additive_repair_alternatives": (
            [
                {
                    "priority": 1,
                    "kind": "COUNTERBALANCING_ADDITIVE_HYPOTHESIS",
                    "state": "REQUIRES_SEPARATE_POSITIVE_ONLY_HYPOTHESIS",
                },
                {
                    "priority": 2,
                    "kind": "DILUTION",
                    "state": "OFFER_ONLY_IF_COMPATIBLE_WITH_THE_GOAL",
                },
                {
                    "priority": 3,
                    "kind": "NEW_FORMULA",
                    "state": "USER_MUST_EXPLICITLY_CHOOSE",
                },
            ]
            if additive_repair_blocked
            else []
        ),
        "default_user_view": {
            "what_the_system_understood": interpretation["normalized_goal"],
            "strongest_clue": clues[0]["statement"] if clues else None,
            "proposed_delta": (
                {
                    "hypothesis_id": hypotheses[0]["hypothesis_id"],
                    "material_or_block": hypotheses[0]["material_or_block"],
                    "trial": hypotheses[0]["trial"],
                    "state": "PROPOSAL_ONLY",
                }
                if hypotheses
                else None
            ),
            "what_to_smell_for": list(request.goals),
            "uncertainty_or_stop_condition": (
                "A same-bottle request cannot remove material; stop or choose a counterbalance, dilution, or new formula."
                if additive_repair_blocked
                else "No sensory winner is established until the proposed delta is smelled."
            ),
        },
        "formula_modified": False,
        "physical_experiment_authorized": False,
        "evidence_admission_authorized": False,
        **FALSE_ACTION_AUTHORITY,
    }
    return {**report, "analysis_sha256": stable_payload_hash(report)}


__all__ = [
    "GoalAnalysisRequestV1",
    "GoalFormulaRowV1",
    "analyze_formula_for_goal",
]
