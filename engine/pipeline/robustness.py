"""Deterministic perturbation audits for release-gate robustness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from engine.ifra_safety import IFRA_CAT4_LIMITS, score_ifra_compliance
from engine.optimizer.perfumer_logic import evaluate_perfumer_logic
from engine.pipeline.simulator import simulate_formula

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


def audit_formula_robustness(formula: Mapping, config) -> RobustnessReport:
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
    base_top_envelope, base_top_leader = _top_envelope_and_leader(
        ingredients_ul,
        dilutions,
        config,
    )
    perturbations: list[PerturbationResult] = []
    skipped = 0

    for material, amount in ingredients_ul.items():
        step = max(min(5.0, amount * 0.5), amount * 0.05)
        for direction in ("up", "down"):
            perturbed = _perturb(ingredients_ul, material, step, direction)
            if perturbed is None:
                skipped += 1
                continue
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
) -> PerturbationResult:
    top_envelope, top_leader = _top_envelope_and_leader(
        ingredients_ul, dilutions, config
    )
    drift = _envelope_drift(base_top_envelope, top_envelope)
    safety = score_ifra_compliance(
        dict(ingredients_ul),
        dict(dilutions),
        total_volume_ml=float(config.batch_volume_ml),
    )
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
    safety_failed = bool(
        safety.ifra_violations or safety.banned_flags or headroom_violations
    )
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


def _top_envelope_and_leader(
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float],
    config,
) -> tuple[dict[str, float], str | None]:
    frames = simulate_formula(
        ingredients_ul,
        dilutions,
        batch_volume_ml=float(config.batch_volume_ml),
        temperature_K=float(config.temperature_K),
        windows=(("top", 300.0),),
    )
    state = frames[0].state
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
