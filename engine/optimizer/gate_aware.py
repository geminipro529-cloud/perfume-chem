"""Gate-aware optimizer repair loop.

This module does not replace existing optimizer objectives. It wraps their raw
concentrate output, runs the reusable release gates, applies deterministic
repairs for gates that can be repaired without changing the brief, and records
blocked rerun requirements for gates that need a new optimization pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from engine.ifra_safety import IFRA_CAT4_LIMITS
from engine.pipeline.interventions import build_intervention_contract
from engine.pipeline.audit_log import append_event, gate_report_event
from engine.pipeline.gates import GateReport, ReleaseGateConfig, gate_formula
from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority
from engine.pipeline.release_scoring import compute_unified_release_scores


RawPct = Mapping[str, float]
StockDilutions = Mapping[str, float]
RepairPool = Mapping[str, float] | Sequence[str] | None
RerunCallback = Callable[[dict[str, tuple[float | None, float | None]], tuple["GateRepairAction", ...]], RawPct]


REPAIRABLE_GATES = {
    "safety_ifra_allergen",
    "pipette_floor_neat_traces",
    "exact_subtotal",
    "robustness_perturbation",
}


@dataclass(frozen=True, slots=True)
class GateRepairAction:
    """A constraint or formula mutation caused by a failed release gate."""

    pass_index: int
    gate: str
    action: str
    status: str
    material: str | None = None
    before_ul: float | None = None
    after_ul: float | None = None
    before_pct: float | None = None
    after_pct: float | None = None
    effect: str = "SAFER"
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "pass_index": self.pass_index,
            "gate": self.gate,
            "action": self.action,
            "status": self.status,
            "material": self.material,
            "before_ul": self.before_ul,
            "after_ul": self.after_ul,
            "before_pct": self.before_pct,
            "after_pct": self.after_pct,
            "effect": self.effect,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class GateAwareOptimizationResult:
    """Final result after gate repair attempts."""

    name: str
    raw_concentrate_pct: dict[str, float]
    gate_report: GateReport
    repair_actions: tuple[GateRepairAction, ...]
    iterations: int
    interventions: dict | None = None
    audit_event_id: str | None = None

    @property
    def status(self) -> str:
        return self.gate_report.status

    @property
    def commercial_readiness(self) -> str:
        return self.gate_report.commercial_readiness

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "raw_concentrate_pct": {
                key: round(value, 6)
                for key, value in self.raw_concentrate_pct.items()
            },
            "status": self.status,
            "commercial_readiness": self.commercial_readiness,
            "iterations": self.iterations,
            "audit_event_id": self.audit_event_id,
            "interventions": dict(self.interventions or {}),
            "repair_actions": [action.as_dict() for action in self.repair_actions],
            "gate_report": self.gate_report.as_dict(),
        }


def normalize_raw_pct(raw_pct: RawPct) -> dict[str, float]:
    """Normalize positive raw concentrate percentages to exactly 100%."""
    positive = {
        str(material): max(0.0, float(value or 0.0))
        for material, value in raw_pct.items()
    }
    total = sum(positive.values())
    if total <= 0:
        return {}
    return {
        material: value * 100.0 / total
        for material, value in positive.items()
        if value > 0
    }


def raw_pct_to_formula_record(
    name: str,
    raw_pct: RawPct,
    stock_dilutions: StockDilutions | None = None,
    *,
    concentrate_ul: float = 6000.0,
    number: int = 1,
    body: str = "",
    family_archetype: str = "",
) -> dict:
    """Build the formula mapping expected by release gates."""
    normalized = normalize_raw_pct(raw_pct)
    dilutions = dict(stock_dilutions or {})
    ingredients_ul = {
        material: pct * concentrate_ul / 100.0
        for material, pct in normalized.items()
    }
    return {
        "number": number,
        "name": name,
        "body": body or name,
        "ingredients_ul": ingredients_ul,
        "ingredients_pct": normalized,
        "dilutions": {material: float(dilutions.get(material, 1.0)) for material in normalized},
        "family_archetype": family_archetype,
    }


def max_raw_ul_for_ifra(
    limit_pct: float,
    batch_volume_ml: float,
    dilution: float,
    *,
    headroom: float = 1.0,
) -> float:
    """Return the maximum raw stock uL allowed by a finished-product IFRA limit."""
    dilution = max(float(dilution or 1.0), 1e-9)
    return (float(limit_pct) * float(headroom) / 100.0) * float(batch_volume_ml) * 1000.0 / dilution


def _raw_pct_to_ul(raw_pct: RawPct, concentrate_ul: float) -> dict[str, float]:
    return {
        material: pct * concentrate_ul / 100.0
        for material, pct in normalize_raw_pct(raw_pct).items()
    }


def _ul_to_pct(raw_ul: Mapping[str, float]) -> dict[str, float]:
    total = sum(max(0.0, float(value or 0.0)) for value in raw_ul.values())
    if total <= 0:
        return {}
    return {
        material: max(0.0, float(value or 0.0)) * 100.0 / total
        for material, value in raw_ul.items()
        if value > 0
    }


def _failed_gates(report: GateReport) -> list:
    return [gate for gate in report.gates if gate.status == "FAIL"]


def _gate(report: GateReport, name: str):
    for gate in report.gates:
        if gate.gate == name:
            return gate
    return None


def _effective_ifra_headroom(config: ReleaseGateConfig) -> float:
    if hasattr(config, "effective_ifra_headroom"):
        return config.effective_ifra_headroom()
    return float(getattr(config, "ifra_headroom", 1.0) or 1.0)


def _ifra_limit_for_material(material: str) -> float | None:
    return IFRA_CAT4_LIMITS.get(material)


def _repair_pool_weights(raw_ul: Mapping[str, float], repair_pool: RepairPool, excluded: set[str]) -> dict[str, float]:
    if isinstance(repair_pool, Mapping):
        weights = {
            str(material): max(0.0, float(weight or 0.0))
            for material, weight in repair_pool.items()
            if str(material) in raw_ul and str(material) not in excluded
        }
    elif repair_pool:
        weights = {
            str(material): 1.0
            for material in repair_pool
            if str(material) in raw_ul and str(material) not in excluded
        }
    else:
        weights = {
            material: max(0.0, amount)
            for material, amount in raw_ul.items()
            if material not in excluded and amount > 0
        }

    weights = {material: weight for material, weight in weights.items() if weight > 0}
    if weights:
        return weights

    candidates = {
        material: amount
        for material, amount in raw_ul.items()
        if material not in excluded and amount > 0
    }
    if not candidates:
        return {}
    material = max(candidates, key=candidates.get)
    return {material: 1.0}


def _redistribute_ul(
    raw_ul: dict[str, float],
    excess_ul: float,
    *,
    repair_pool: RepairPool,
    excluded: set[str],
    pass_index: int,
    gate_name: str,
) -> tuple[dict[str, float], list[GateRepairAction]]:
    if excess_ul <= 1e-9:
        return raw_ul, []

    weights = _repair_pool_weights(raw_ul, repair_pool, excluded)
    if not weights:
        return raw_ul, [
            GateRepairAction(
                pass_index=pass_index,
                gate=gate_name,
                action="redistribute_excess",
                status="BLOCKED",
                before_ul=round(excess_ul, 6),
                effect="BLOCKED",
                detail="No legal repair-pool material available for displaced volume.",
            )
        ]

    total_weight = sum(weights.values())
    actions: list[GateRepairAction] = []
    for material, weight in weights.items():
        add_ul = excess_ul * weight / total_weight
        before = raw_ul.get(material, 0.0)
        raw_ul[material] = before + add_ul
        actions.append(
            GateRepairAction(
                pass_index=pass_index,
                gate=gate_name,
                action="rebalance_displaced_volume",
                status="APPLIED",
                material=material,
                before_ul=round(before, 6),
                after_ul=round(raw_ul[material], 6),
                before_pct=round(_safe_pct(before, raw_ul), 6),
                after_pct=round(_safe_pct(raw_ul[material], raw_ul), 6),
                effect="SAFER",
                detail=f"Received {add_ul:.3f} uL displaced from a hard gate repair.",
            )
        )
    return raw_ul, actions


def _safe_pct(amount_ul: float, raw_ul: Mapping[str, float]) -> float:
    total = sum(max(0.0, float(value or 0.0)) for value in raw_ul.values()) or 1.0
    return 100.0 * float(amount_ul or 0.0) / total


def _apply_ifra_repairs(
    raw_pct: RawPct,
    report: GateReport,
    stock_dilutions: StockDilutions,
    config: ReleaseGateConfig,
    *,
    concentrate_ul: float,
    repair_pool: RepairPool,
    pass_index: int,
) -> tuple[dict[str, float], list[GateRepairAction], dict[str, tuple[float | None, float | None]]]:
    safety = _gate(report, "safety_ifra_allergen")
    violations = []
    if safety:
        violations.extend(safety.data.get("violations", []) or [])
        violations.extend(safety.data.get("headroom_violations", []) or [])
    if not violations:
        return normalize_raw_pct(raw_pct), [], {}

    raw_ul = _raw_pct_to_ul(raw_pct, concentrate_ul)
    actions: list[GateRepairAction] = []
    constraints: dict[str, tuple[float | None, float | None]] = {}
    excess_total = 0.0
    excluded = set()

    for violation in violations:
        material = str(violation.get("material", ""))
        if material not in raw_ul:
            continue
        limit_pct = float(violation.get("limit_pct"))
        dilution = float(stock_dilutions.get(material, 1.0))
        current_ul = raw_ul[material]
        max_ul = max_raw_ul_for_ifra(
            limit_pct,
            config.batch_volume_ml,
            dilution,
            headroom=_effective_ifra_headroom(config),
        )
        target_ul = max(0.0, min(current_ul, max_ul - 1e-6))
        if target_ul >= current_ul:
            continue

        before_total = sum(raw_ul.values()) or concentrate_ul
        before_pct = 100.0 * current_ul / before_total
        raw_ul[material] = target_ul
        excess_total += current_ul - target_ul
        excluded.add(material)
        constraints[material] = (None, target_ul)
        actions.append(
            GateRepairAction(
                pass_index=pass_index,
                gate="safety_ifra_allergen",
                action="cap_ifra_finished_product_limit",
                status="APPLIED",
                material=material,
                before_ul=round(current_ul, 6),
                after_ul=round(target_ul, 6),
                before_pct=round(before_pct, 6),
                after_pct=round(100.0 * target_ul / before_total, 6),
                effect="SAFER",
                detail=(
                    f"IFRA Cat4 {limit_pct:.4g}% finished-product limit with "
                    f"{_effective_ifra_headroom(config):.0%} headroom; "
                    f"max raw stock {max_ul:.3f} uL at dilution {dilution:.3g}."
                ),
            )
        )

    raw_ul, redistribution = _redistribute_ul(
        raw_ul,
        excess_total,
        repair_pool=repair_pool,
        excluded=excluded,
        pass_index=pass_index,
        gate_name="safety_ifra_allergen",
    )
    actions.extend(redistribution)
    return _ul_to_pct(raw_ul), actions, constraints


def _apply_robustness_repairs(
    raw_pct: RawPct,
    report: GateReport,
    stock_dilutions: StockDilutions,
    config: ReleaseGateConfig,
    *,
    concentrate_ul: float,
    repair_pool: RepairPool,
    pass_index: int,
) -> tuple[dict[str, float], list[GateRepairAction], dict[str, tuple[float | None, float | None]]]:
    robustness = _gate(report, "robustness_perturbation")
    issues = (robustness.data.get("issues", []) if robustness else []) or []
    safety_issues = [
        issue for issue in issues
        if issue.get("safety_failed") and issue.get("direction") == "up"
    ]
    if not safety_issues:
        return normalize_raw_pct(raw_pct), [], {}

    raw_ul = _raw_pct_to_ul(raw_pct, concentrate_ul)
    actions: list[GateRepairAction] = []
    constraints: dict[str, tuple[float | None, float | None]] = {}
    excess_total = 0.0
    excluded = set()

    for issue in safety_issues:
        material = str(issue.get("material", ""))
        if material not in raw_ul:
            continue
        current_ul = raw_ul[material]
        delta_ul = max(0.0, float(issue.get("delta_ul", 0.0) or 0.0))
        limit = _ifra_limit_for_material(material)
        dilution = float(stock_dilutions.get(material, 1.0))
        headroom_cap = current_ul
        if limit is not None:
            headroom_cap = max_raw_ul_for_ifra(
                limit,
                config.batch_volume_ml,
                dilution,
                headroom=_effective_ifra_headroom(config),
            )
        perturbation_cap = max(0.0, current_ul - delta_ul)
        target_ul = max(0.0, min(current_ul, perturbation_cap, headroom_cap - 1e-6))
        if target_ul >= current_ul:
            continue

        before_total = sum(raw_ul.values()) or concentrate_ul
        before_pct = 100.0 * current_ul / before_total
        raw_ul[material] = target_ul
        excess_total += current_ul - target_ul
        excluded.add(material)
        constraints[material] = (None, target_ul)
        actions.append(
            GateRepairAction(
                pass_index=pass_index,
                gate="robustness_perturbation",
                action="cap_robustness_safety_margin",
                status="APPLIED",
                material=material,
                before_ul=round(current_ul, 6),
                after_ul=round(target_ul, 6),
                before_pct=round(before_pct, 6),
                after_pct=round(100.0 * target_ul / before_total, 6),
                effect="SAFER",
                detail=(
                    f"Material-up perturbation of {delta_ul:.3f} uL caused safety failure; "
                    f"cap uses min(current-delta={perturbation_cap:.3f}, "
                    f"headroom-cap={headroom_cap:.3f})."
                ),
            )
        )

    raw_ul, redistribution = _redistribute_ul(
        raw_ul,
        excess_total,
        repair_pool=repair_pool,
        excluded=excluded,
        pass_index=pass_index,
        gate_name="robustness_perturbation",
    )
    actions.extend(redistribution)
    return _ul_to_pct(raw_ul), actions, constraints


def _apply_pipette_repairs(
    raw_pct: RawPct,
    stock_dilutions: StockDilutions,
    config: ReleaseGateConfig,
    *,
    concentrate_ul: float,
    pass_index: int,
) -> tuple[dict[str, float], list[GateRepairAction]]:
    raw_ul = _raw_pct_to_ul(raw_pct, concentrate_ul)
    actions: list[GateRepairAction] = []

    for material, amount_ul in list(raw_ul.items()):
        dilution = float(stock_dilutions.get(material, 1.0))
        if amount_ul <= 0 or amount_ul >= config.min_neat_trace_ul or dilution < 0.999:
            continue

        deficit = config.min_neat_trace_ul - amount_ul
        donors = {
            donor: amount
            for donor, amount in raw_ul.items()
            if donor != material and amount > config.min_neat_trace_ul + deficit
        }
        if not donors:
            actions.append(
                GateRepairAction(
                    pass_index=pass_index,
                    gate="pipette_floor_neat_traces",
                    action="raise_neat_trace_to_floor",
                    status="BLOCKED",
                    material=material,
                    before_ul=round(amount_ul, 6),
                    after_ul=round(config.min_neat_trace_ul, 6),
                    effect="BUILDABILITY",
                    detail="No donor material had enough volume to preserve subtotal.",
                )
            )
            continue

        donor = max(donors, key=donors.get)
        donor_before = raw_ul[donor]
        raw_ul[material] = config.min_neat_trace_ul
        raw_ul[donor] = donor_before - deficit
        actions.append(
            GateRepairAction(
                pass_index=pass_index,
                gate="pipette_floor_neat_traces",
                action="raise_neat_trace_to_floor",
                status="APPLIED",
                material=material,
                before_ul=round(amount_ul, 6),
                after_ul=round(config.min_neat_trace_ul, 6),
                effect="BUILDABILITY",
                detail=f"Moved {deficit:.3f} uL from {donor}.",
            )
        )

    return _ul_to_pct(raw_ul), actions


def _nonrepairable_actions(report: GateReport, pass_index: int) -> list[GateRepairAction]:
    actions: list[GateRepairAction] = []
    for gate in _failed_gates(report):
        if gate.gate in REPAIRABLE_GATES:
            continue
        action = "block_unknown_or_forbidden_material"
        effect = "BLOCKED"
        if gate.gate == "perfumer_logic":
            action = "rerun_with_tighter_brief_grammar"
            effect = "BRIEF_FIT"
        elif gate.gate in {"material_spine_coverage", "physics_data_coverage", "odt_coverage"}:
            action = "block_missing_material_data"
        elif gate.gate == "chemistry_stability":
            action = "rerun_with_stability_constraints"
            effect = "CHEMISTRY"
        elif gate.gate == "phase_compatibility":
            action = "rerun_with_phase_compatibility_constraints"
            effect = "CHEMISTRY"
        elif gate.gate == "opaque_preblends":
            action = "block_opaque_preblend"
        actions.append(
            GateRepairAction(
                pass_index=pass_index,
                gate=gate.gate,
                action=action,
                status="BLOCKED",
                effect=effect,
                detail=gate.detail,
            )
        )
    return actions


def optimize_until_release_ready(
    name: str,
    raw_concentrate_pct: RawPct,
    stock_dilutions: StockDilutions | None = None,
    *,
    config: ReleaseGateConfig | None = None,
    concentrate_ul: float = 6000.0,
    repair_pool: RepairPool = None,
    max_passes: int = 4,
    number: int = 1,
    body: str = "",
    family_archetype: str = "",
    rerun_optimizer: RerunCallback | None = None,
) -> GateAwareOptimizationResult:
    """Run gates, repair deterministic failures, and stop on release-ready output.

    Safety failures are repaired by introducing hard raw-uL caps. Missing data,
    forbidden preblends, blocked materials, and brief grammar failures are
    returned as blocked repair actions unless a caller supplies a rerun callback.
    """
    config = config or ReleaseGateConfig()
    stock_dilutions = dict(stock_dilutions or {})
    current = normalize_raw_pct(raw_concentrate_pct)
    actions: list[GateRepairAction] = []
    constraints: dict[str, tuple[float | None, float | None]] = {}
    report: GateReport | None = None

    for pass_index in range(1, max_passes + 1):
        formula = raw_pct_to_formula_record(
            name,
            current,
            stock_dilutions,
            concentrate_ul=concentrate_ul,
            number=number,
            body=body,
            family_archetype=family_archetype,
        )
        report = gate_formula(formula, config)
        failed = _failed_gates(report)
        if not failed:
            break

        changed = False
        repaired, new_actions, new_constraints = _apply_ifra_repairs(
            current,
            report,
            stock_dilutions,
            config,
            concentrate_ul=concentrate_ul,
            repair_pool=repair_pool,
            pass_index=pass_index,
        )
        if new_actions:
            current = repaired
            actions.extend(new_actions)
            constraints.update(new_constraints)
            changed = any(action.status == "APPLIED" for action in new_actions)

        if changed:
            continue

        if any(gate.gate == "pipette_floor_neat_traces" for gate in failed):
            repaired, new_actions = _apply_pipette_repairs(
                current,
                stock_dilutions,
                config,
                concentrate_ul=concentrate_ul,
                pass_index=pass_index,
            )
            if new_actions:
                current = repaired
                actions.extend(new_actions)
                changed = changed or any(action.status == "APPLIED" for action in new_actions)

        if changed:
            continue

        if any(gate.gate == "robustness_perturbation" for gate in failed):
            repaired, new_actions, new_constraints = _apply_robustness_repairs(
                current,
                report,
                stock_dilutions,
                config,
                concentrate_ul=concentrate_ul,
                repair_pool=repair_pool,
                pass_index=pass_index,
            )
            if new_actions:
                current = repaired
                actions.extend(new_actions)
                constraints.update(new_constraints)
                changed = changed or any(action.status == "APPLIED" for action in new_actions)

        if changed:
            continue

        blocked = _nonrepairable_actions(report, pass_index)
        if blocked:
            actions.extend(blocked)
            if rerun_optimizer is None:
                break
            current = normalize_raw_pct(rerun_optimizer(constraints, tuple(actions)))
            actions.append(
                GateRepairAction(
                    pass_index=pass_index,
                    gate="optimizer_rerun",
                    action="rerun_optimizer_with_gate_constraints",
                    status="APPLIED",
                    effect="BRIEF_FIT",
                    detail="Caller-supplied optimizer rerun returned a new candidate.",
                )
            )
            continue

        actions.append(
            GateRepairAction(
                pass_index=pass_index,
                gate="repair_loop",
                action="no_repair_available",
                status="BLOCKED",
                effect="BLOCKED",
                detail="Release gates failed but no deterministic repair changed the candidate.",
            )
        )
        break

    formula = raw_pct_to_formula_record(
        name,
        current,
        stock_dilutions,
        concentrate_ul=concentrate_ul,
        number=number,
        body=body,
        family_archetype=family_archetype,
    )
    final_report = gate_formula(formula, config)
    authority = analyze_oav_authority(
        OAVAuthorityRequest(
            formula_name=name,
            ingredients_ul=formula["ingredients_ul"],
            dilutions=formula["dilutions"],
            batch_volume_ml=config.batch_volume_ml,
            temperature_K=config.temperature_K,
            family_archetype=family_archetype,
        )
    )
    unified_scores = compute_unified_release_scores(formula, authority, final_report.as_dict()).as_dict()
    optimizer_report = {
        **final_report.as_dict(),
        "scores": unified_scores["scores"],
        "industry_10": unified_scores["industry_10"],
        "score_provenance": unified_scores["provenance"],
        "oav_table": [
            {
                "name": row.name,
                "dilution": row.dilution,
                "raw_ul": round(row.raw_ul, 2),
                "active_ul": round(row.active_ul, 2),
                "vapor_ppm": round(row.vapor_ppm, 6),
                "odt_air_ppm": row.odt_air_ppm,
                "oav": round(row.oav, 2) if row.oav is not None else None,
                "note": row.note,
            }
            for row in authority.material_rows
        ],
    }
    interventions = build_intervention_contract(
        formula,
        optimizer_report,
        batch_volume_ml=config.batch_volume_ml,
    )
    iterations = pass_index if "pass_index" in locals() else 0
    audit_event_id = None
    if config.audit_enabled:
        event = append_event(
            gate_report_event(
                final_report,
                config,
                event_type="optimize_until_release_ready",
                repair_actions=[action.as_dict() for action in actions],
            )
        )
        audit_event_id = str(event.get("event_id", ""))
    return GateAwareOptimizationResult(
        name=name,
        raw_concentrate_pct=normalize_raw_pct(current),
        gate_report=final_report,
        repair_actions=tuple(actions),
        iterations=iterations,
        interventions=interventions,
        audit_event_id=audit_event_id,
    )


def render_gate_audit_markdown(result: GateAwareOptimizationResult | Mapping) -> list[str]:
    """Render a compact release audit block for optimized formula markdown."""
    payload = result.as_dict() if hasattr(result, "as_dict") else dict(result)
    report = payload.get("gate_report", {})
    confidence = report.get("confidence", {})
    calibration = report.get("calibration_summary", {})
    config = report.get("config_summary", {})
    gates = report.get("gates", [])
    actions = payload.get("repair_actions", [])
    lines = [
        "### Release Gate Audit",
        "",
        f"**Gate status:** `{payload.get('status', report.get('status', 'UNKNOWN'))}`",
        f"**Commercial readiness:** `{payload.get('commercial_readiness', report.get('commercial_readiness', 'UNKNOWN'))}`",
        f"**Family archetype:** `{config.get('family_archetype') or 'not set'}`",
        f"**Commercial mode:** `{config.get('commercial_mode', False)}`",
        f"**Commercial confidence policy:** `{config.get('commercial_confidence_policy', 'block')}`",
        (
            f"**IFRA headroom:** `{float(config.get('effective_ifra_headroom', config.get('ifra_headroom', 1.0))):.0%}` "
            f"(configured `{float(config.get('ifra_headroom', 1.0)):.0%}`)"
        ),
        (
            f"**Audit event:** `{payload.get('audit_event_id') or report.get('audit_event_id') or 'not logged'}`"
        ),
        (
            f"**Confidence:** `{confidence.get('combined_grade', 'UNKNOWN')}` "
            f"({float(confidence.get('combined_confidence', 0.0)):.1f} combined)"
        ),
        "",
    ]
    if calibration:
        lines.extend([
            "### Calibration Summary",
            "",
            (
                f"Records `{calibration.get('formula_records', 0)}`, "
                f"wear observations `{calibration.get('wear_observations', 0)}`, "
                f"panel results `{calibration.get('panel_results', 0)}`, "
                f"ready `{calibration.get('calibration_ready', False)}`"
            ),
            "",
        ])
        intensity_bias = calibration.get("mean_intensity_bias_0_10")
        projection_bias = calibration.get("mean_projection_bias_cm")
        if intensity_bias is not None or projection_bias is not None:
            lines.extend([
                (
                    f"Mean bias: intensity `{intensity_bias if intensity_bias is not None else 'n/a'}`, "
                    f"projection `{projection_bias if projection_bias is not None else 'n/a'} cm`"
                ),
                "",
            ])
    lines.extend([
        "| Gate | Status | Detail |",
        "|---|---:|---|",
    ])

    for gate in gates:
        detail = str(gate.get("detail", "")).replace("|", "/")
        if len(detail) > 180:
            detail = detail[:177] + "..."
        lines.append(f"| {gate.get('gate')} | {gate.get('status')} | {detail or '-'} |")

    lines.extend(["", "### Repair History", ""])
    if actions:
        lines.extend([
            "| Pass | Gate | Action | Material | Change | Effect |",
            "|---:|---|---|---|---:|---|",
        ])
        for action in actions:
            before = action.get("before_ul")
            after = action.get("after_ul")
            change = "-"
            if before is not None or after is not None:
                change = f"{before if before is not None else '-'} -> {after if after is not None else '-'} uL"
            detail = action.get("detail") or action.get("status", "")
            lines.append(
                f"| {action.get('pass_index')} | {action.get('gate')} | "
                f"{action.get('action')} | {action.get('material') or '-'} | "
                f"{change} | {action.get('effect')}: {str(detail).replace('|', '/')} |"
            )
    else:
        lines.append("No repair actions were needed after the optimizer pass.")

    frames = report.get("time_series", [])
    if frames:
        lines.extend(["", "### Gate Time-Series OAV Leaders", ""])
        for frame in frames:
            leaders = frame.get("dominant_oav", [])[:5]
            leader_text = ", ".join(
                f"{row.get('material')} OAV={float(row.get('oav', 0.0)):.1f} ppm={float(row.get('ppm', 0.0)):.6f}"
                for row in leaders
            )
            lines.append(f"- `{frame.get('label')}` ({float(frame.get('t_seconds', 0.0)):.0f}s): {leader_text}")
    lines.append("")
    return lines
