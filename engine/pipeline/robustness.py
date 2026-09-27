"""Deterministic perturbation audits for release-gate robustness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from engine.ifra_safety import BANNED_MATERIALS, IFRA_CAT4_LIMITS
from engine.optimizer.perfumer_logic import evaluate_perfumer_logic
from engine.pipeline.formula_state import FormulaState, build_formula_state
from engine.pipeline.simulator import (
    DEFAULT_WINDOWS,
    REMAINING_QUANTITY_BASIS,
    TEMPORAL_AUTHORITY,
    TEMPORAL_MODEL,
    SimulationFrame,
    _remaining_raw_ul,
    simulate_formula,
)

DRIFT_WARN_THRESHOLD = 0.25


@dataclass(frozen=True, slots=True)
class PerturbationResult:
    material: str
    direction: str
    delta_ul: float
    status: str
    family_envelope_drift: float = 0.0
    top_leader_changed: bool = False
    safety_failed: bool = False
    brief_failed: bool = False
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "material": self.material,
            "direction": self.direction,
            "delta_ul": round(self.delta_ul, 6),
            "status": self.status,
            "family_envelope_drift": round(self.family_envelope_drift, 6),
            "top_leader_changed": self.top_leader_changed,
            "safety_failed": self.safety_failed,
            "brief_failed": self.brief_failed,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class RobustnessReport:
    status: str
    checked: int
    skipped: int
    issues: tuple[PerturbationResult, ...] = ()
    perturbations: tuple[PerturbationResult, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "checked": self.checked,
            "skipped": self.skipped,
            "issues": [issue.as_dict() for issue in self.issues],
            "perturbations": [row.as_dict() for row in self.perturbations],
        }


def audit_formula_robustness(
    formula: Mapping,
    config,
    *,
    gate_state: FormulaState | None = None,
    gate_simulation: Sequence[SimulationFrame] | None = None,
) -> RobustnessReport:
    """Perturb every row up/down and detect fragile safety, brief, or OAV behavior.

    This audit intentionally does not call `gate_formula`, so it can be embedded
    inside release gates without recursion.
    """
    ingredients_ul = {
        str(material): float(amount or 0.0)
        for material, amount in (formula.get("ingredients_ul", {}) or {}).items()
        if float(amount or 0.0) > 0
    }
    if len(ingredients_ul) < 2:
        return RobustnessReport(
            status="WARN",
            checked=0,
            skipped=0,
            issues=(
                PerturbationResult(
                    material="-",
                    direction="-",
                    delta_ul=0.0,
                    status="WARN",
                    detail="Need at least two materials for subtotal-preserving perturbation.",
                ),
            ),
        )

    dilutions = {
        str(material): float(value or 1.0)
        for material, value in (formula.get("dilutions", {}) or {}).items()
    }
    try:
        reusable_baseline = _bound_gate_baseline(
            ingredients_ul,
            dilutions,
            config,
            gate_state=gate_state,
            gate_simulation=gate_simulation,
        )
    except Exception:
        # Optional reuse may never turn malformed handoff data into a weaker or
        # unavailable robustness gate. Re-enter the established fresh path;
        # errors from that authoritative calculation still propagate normally.
        reusable_baseline = None
    if reusable_baseline is None:
        base_state = build_formula_state(
            ingredients_ul,
            dilutions,
            batch_volume_ml=float(config.batch_volume_ml),
            temperature_K=float(config.temperature_K),
        )
        base_top_envelope, base_top_leader = _top_envelope_and_leader(
            ingredients_ul,
            dilutions,
            config,
            initial_state=base_state,
        )
    else:
        base_state, top_frame = reusable_baseline
        base_top_envelope, base_top_leader = _envelope_and_leader(top_frame.state)
    perturbations: list[PerturbationResult] = []
    skipped = 0

    for material, amount in ingredients_ul.items():
        step = max(min(5.0, amount * 0.5), amount * 0.05)
        for direction in ("up", "down"):
            perturbed = _perturb(ingredients_ul, material, step, direction)
            if perturbed is None:
                skipped += 1
                continue
            perturbed_state = FormulaState.from_base(
                base_state,
                new_raw_ul=perturbed,
            )
            perturbations.append(
                _evaluate_perturbation(
                    formula,
                    perturbed,
                    dilutions,
                    material,
                    direction,
                    step,
                    base_top_envelope,
                    base_top_leader,
                    config,
                    initial_state=perturbed_state,
                )
            )

    issues = tuple(row for row in perturbations if row.status == "WARN")
    return RobustnessReport(
        status="WARN" if issues else "PASS",
        checked=len(perturbations),
        skipped=skipped,
        issues=issues,
        perturbations=tuple(perturbations),
    )


def _perturb(
    ingredients_ul: Mapping[str, float],
    material: str,
    step: float,
    direction: str,
) -> dict[str, float] | None:
    rows = dict(ingredients_ul)
    others = {
        name: amount for name, amount in rows.items() if name != material and amount > 0
    }
    if not others:
        return None

    if direction == "up":
        donor = max(others, key=others.get)
        if rows[donor] - step <= 0:
            return None
        rows[material] += step
        rows[donor] -= step
        return rows

    if rows[material] - step <= 0:
        return None
    receiver = max(others, key=others.get)
    rows[material] -= step
    rows[receiver] += step
    return rows


def _evaluate_perturbation(
    original_formula: Mapping,
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float],
    material: str,
    direction: str,
    step: float,
    base_top_envelope: Mapping[str, float],
    base_top_leader: str | None,
    config,
    *,
    initial_state: FormulaState,
) -> PerturbationResult:
    top_envelope, top_leader = _top_envelope_and_leader(
        ingredients_ul,
        dilutions,
        config,
        initial_state=initial_state,
    )
    drift = _envelope_drift(base_top_envelope, top_envelope)
    formula = _formula_for_logic(original_formula, ingredients_ul, dilutions)
    logic = evaluate_perfumer_logic(
        formula,
        brief=str(config.brief),
        family_archetype=str(
            getattr(config, "family_archetype", "")
            or formula.get("family_archetype", "")
        ),
    )

    headroom_violations = _headroom_violations(ingredients_ul, dilutions, config)
    safety_failed = _has_ifra_or_banned_failure(
        ingredients_ul,
        dilutions,
        config,
    ) or bool(headroom_violations)
    brief_failed = logic.status == "FAIL"
    leader_changed = bool(
        base_top_leader and top_leader and base_top_leader != top_leader
    )
    warn = safety_failed or brief_failed or drift > DRIFT_WARN_THRESHOLD

    details = []
    if safety_failed:
        details.append("safety failure under perturbation")
    if headroom_violations:
        details.append(
            "IFRA headroom failure: "
            + ", ".join(
                f"{row['material']} {row['actual_pct']:.4g}% > {row['effective_limit_pct']:.4g}%"
                for row in headroom_violations
            )
        )
    if brief_failed:
        details.append("brief grammar failure under perturbation")
    if drift > DRIFT_WARN_THRESHOLD:
        details.append(f"top family OAV drift {drift:.1%} > {DRIFT_WARN_THRESHOLD:.0%}")
    if leader_changed:
        details.append(f"top OAV leader changed {base_top_leader} -> {top_leader}")

    return PerturbationResult(
        material=material,
        direction=direction,
        delta_ul=step,
        status="WARN" if warn else "PASS",
        family_envelope_drift=drift,
        top_leader_changed=leader_changed,
        safety_failed=safety_failed,
        brief_failed=brief_failed,
        detail="; ".join(details) or "stable within perturbation thresholds",
    )


def _bound_gate_baseline(
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float],
    config,
    *,
    gate_state: FormulaState | None,
    gate_simulation: Sequence[SimulationFrame] | None,
) -> tuple[FormulaState, SimulationFrame] | None:
    """Return the gate's baseline only when every reusable input binds exactly.

    The gate state and temporal frames are an optimization, never an alternate
    source of truth. Any missing or mismatched binding falls back to the
    established fresh robustness calculation in ``audit_formula_robustness``.
    """

    if not isinstance(gate_state, FormulaState) or gate_simulation is None:
        return None

    expected_doses = {
        str(material): float(amount or 0.0)
        for material, amount in ingredients_ul.items()
        if float(amount or 0.0) > 0.0
    }
    actual_doses = {material.name: material.raw_ul for material in gate_state.materials}
    if actual_doses != expected_doses:
        return None

    expected_dilutions = {
        material: float(dilutions.get(material, 1.0) or 1.0)
        for material in expected_doses
    }
    actual_dilutions = {
        material.name: material.dilution for material in gate_state.materials
    }
    if actual_dilutions != expected_dilutions:
        return None

    expected_matrix = tuple(
        sorted(
            (
                (str(name), float(value))
                for name, value in dict(
                    getattr(config, "matrix_components_moles", ()) or ()
                ).items()
                if float(value) >= 0.0
            ),
            key=lambda row: row[0].casefold(),
        )
    )
    if (
        gate_state.batch_volume_ml != float(config.batch_volume_ml)
        or gate_state.temperature_K != float(config.temperature_K)
        or gate_state.context != "skin"
        or gate_state.matrix_components_moles != expected_matrix
        or gate_state.matrix_mass_g
        != float(getattr(config, "matrix_mass_g", 0.0) or 0.0)
        or gate_state.matrix_source
        != str(getattr(config, "matrix_source", "omitted") or "omitted")
    ):
        return None

    frames = tuple(gate_simulation)
    if not all(isinstance(frame, SimulationFrame) for frame in frames):
        return None
    actual_windows = tuple((frame.label, frame.t_seconds) for frame in frames)
    if actual_windows != DEFAULT_WINDOWS:
        return None
    if any(
        frame.temporal_model != TEMPORAL_MODEL
        or frame.temporal_authority != TEMPORAL_AUTHORITY
        or frame.remaining_quantity_basis != REMAINING_QUANTITY_BASIS
        for frame in frames
    ):
        return None
    if frames[0].state is not gate_state:
        return None

    top_frame = frames[1]
    expected_top_raw_ul = _remaining_raw_ul(gate_state, top_frame.t_seconds)
    expected_top_state = FormulaState.from_base(
        gate_state,
        new_raw_ul=expected_top_raw_ul,
    )
    if top_frame.state != expected_top_state:
        return None
    return gate_state, top_frame


def _headroom_violations(
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float],
    config,
) -> list[dict]:
    if hasattr(config, "effective_ifra_headroom"):
        headroom = float(config.effective_ifra_headroom())
    else:
        headroom = float(getattr(config, "ifra_headroom", 1.0) or 1.0)
    batch_volume_ml = float(getattr(config, "batch_volume_ml", 30.0) or 30.0)
    violations = []
    for material, amount_ul in ingredients_ul.items():
        limit = IFRA_CAT4_LIMITS.get(material)
        if limit is None:
            continue
        active_ul = float(amount_ul or 0.0) * float(dilutions.get(material, 1.0) or 1.0)
        actual_pct = (active_ul / 1000.0) / batch_volume_ml * 100.0
        effective_limit = limit * headroom
        if actual_pct > effective_limit + 1e-12:
            violations.append(
                {
                    "material": material,
                    "actual_pct": actual_pct,
                    "limit_pct": limit,
                    "effective_limit_pct": effective_limit,
                    "headroom": headroom,
                }
            )
    return violations


def _has_ifra_or_banned_failure(
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float],
    config,
) -> bool:
    """Evaluate only the two safety fields consumed by this perturbation gate.

    The former call to ``score_ifra_compliance`` also resolved physicochemical
    data, estimated skin partitioning, assembled allergen declarations, and
    scored unrelated diagnostic fields for every row of every perturbation.
    Robustness used none of those outputs.  This exact narrow check preserves
    the existing IFRA-limit and banned-name semantics while keeping the full
    safety report on the ordinary formula gate where it belongs.
    """

    batch_volume_ml = float(getattr(config, "batch_volume_ml", 30.0) or 30.0)
    for material, amount_ul in ingredients_ul.items():
        if material in BANNED_MATERIALS:
            return True
        limit = IFRA_CAT4_LIMITS.get(material)
        if limit is None:
            continue
        active_ul = float(amount_ul or 0.0) * float(
            dilutions.get(material, 1.0) or 1.0
        )
        pct_in_product = (active_ul / 1000.0) / batch_volume_ml * 100.0
        if pct_in_product > limit:
            return True
    return False


def _top_envelope_and_leader(
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float],
    config,
    *,
    initial_state: FormulaState | None = None,
) -> tuple[dict[str, float], str | None]:
    frames = simulate_formula(
        ingredients_ul,
        dilutions,
        batch_volume_ml=float(config.batch_volume_ml),
        temperature_K=float(config.temperature_K),
        windows=(("top", 300.0),),
        initial_state=initial_state,
    )
    return _envelope_and_leader(frames[0].state)


def _envelope_and_leader(
    state: FormulaState,
) -> tuple[dict[str, float], str | None]:
    envelope: dict[str, float] = {}
    leader = None
    leader_oav = -1.0
    for material in state.materials:
        oav = float(material.oav or 0.0)
        family = material.family or material.canonical_name
        envelope[family] = envelope.get(family, 0.0) + oav
        if oav > leader_oav:
            leader = material.name
            leader_oav = oav
    return envelope, leader


def _envelope_drift(base: Mapping[str, float], changed: Mapping[str, float]) -> float:
    families = set(base) | set(changed)
    denom = sum(abs(float(base.get(family, 0.0))) for family in families)
    if denom <= 1e-12:
        return 0.0
    delta = sum(
        abs(float(changed.get(family, 0.0)) - float(base.get(family, 0.0)))
        for family in families
    )
    return delta / denom


def _formula_for_logic(
    original_formula: Mapping,
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float],
) -> dict:
    total = sum(ingredients_ul.values()) or 1.0
    return {
        "number": original_formula.get("number", 1),
        "name": original_formula.get("name", "Formula"),
        "body": original_formula.get("body", ""),
        "family_archetype": original_formula.get("family_archetype", ""),
        "ingredients_ul": dict(ingredients_ul),
        "ingredients_pct": {
            material: amount / total * 100.0
            for material, amount in ingredients_ul.items()
        },
        "dilutions": dict(dilutions),
    }
