"""Reusable release gates for formula generation and verification.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (parts per million w/w in concentrate).
- ODT in ppm for ethanol solution, ppb for air.
- OAV = concentration_ppm / ODT_ppm (dimensionless).
- Every perceptibility claim must be backed by OAV.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from typing import Mapping

from engine.calibration.hashing import formula_hash_from_record
from engine.calibration.store import load_records, summarize_records
from engine.chemical_data_validator import blocked_reason
from engine.chemistry.maturation import predict_shelf_life_days
from engine.chemistry.photochem import photolysis_remaining_fraction
from engine.confidence import ConfidenceScorer
from engine.families.registry import (
    evaluate_family_archetype,
    get_archetype,
    infer_archetype,
    novelty_assessment,
)
from engine.ifra_safety import IFRA_CAT4_LIMITS, score_ifra_compliance
from engine.name_utils import normalize_name
from engine.optimizer.oav_guard import check_proportional_scaling
from engine.optimizer.models import FormulaVector
from engine.optimizer.perfumer_logic import evaluate_perfumer_logic
from engine.pipeline.audit_log import append_event, gate_report_event
from engine.pipeline.formula_state import FormulaState, build_formula_state
from engine.pipeline.oav_intelligence import analyze_oav_intelligence
from engine.pipeline.robustness import RobustnessReport, audit_formula_robustness
from engine.pipeline.simulator import SimulationFrame, simulate_formula
from engine.knowledge.perfume_knowledge import (
    evaluate_pyramid_balance,
    evaluate_oav_family_targets,
    suggest_accord,
    resolve_family_key,
)
from engine.science_data import StabilityRisk, get_science_profile
from engine.thermo.phase import micro_phase_risk


DEFAULT_CONCENTRATE_UL = 6000.0
MIN_NEAT_TRACE_UL = 5.0
MIN_CONFIDENCE_SCORE = 25.0
MAX_PERCEPTIBLE_CHANNELS = 30
MIN_PERCEPTIBLE_MATERIALS = 3

ALLOWED_VARIANT_DUPLICATES = [
    {"hedione", "hedione hc"},
]


@dataclass(frozen=True, slots=True)
class ReleaseGateConfig:
    expected_concentrate_ul: float = DEFAULT_CONCENTRATE_UL
    min_neat_trace_ul: float = MIN_NEAT_TRACE_UL
    batch_volume_ml: float = 30.0
    temperature_K: float = 305.0
    brief: str = "auto"
    family_archetype: str = ""
    concentration_bracket: str = "EdP"
    allow_preblends: bool = False
    min_confidence_score: float = MIN_CONFIDENCE_SCORE
    min_perceptible_materials: int = MIN_PERCEPTIBLE_MATERIALS
    max_perceptible_channels: int = MAX_PERCEPTIBLE_CHANNELS
    ifra_headroom: float = 1.0
    commercial_mode: bool = False
    commercial_confidence_policy: str = "block"
    batch_scaling_targets_ml: tuple[float, ...] = ()
    audit_enabled: bool = True
    audit_source: str = ""

    def effective_ifra_headroom(self) -> float:
        """Return the active IFRA multiplier for this gate run."""
        if self.commercial_mode and self.ifra_headroom == 1.0:
            return 0.8
        return max(0.0, min(1.0, float(self.ifra_headroom)))

    def is_commercial_trial(self) -> bool:
        return self.commercial_mode and self.commercial_confidence_policy == "warn"


@dataclass(frozen=True, slots=True)
class GateResult:
    gate: str
    status: str
    detail: str = ""
    data: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        payload = {"gate": self.gate, "status": self.status, "detail": self.detail}
        if self.data:
            payload["data"] = self.data
        return payload


@dataclass(frozen=True, slots=True)
class GateReport:
    number: int
    name: str
    status: str
    gates: tuple[GateResult, ...]
    formula_state: FormulaState
    simulation: tuple[SimulationFrame, ...]
    confidence: dict
    formula_hash: str
    calibration_summary: dict
    commercial_readiness: str
    config_summary: dict = field(default_factory=dict)
    audit_event_id: str | None = None

    def as_dict(self) -> dict:
        return {
            "number": self.number,
            "name": self.name,
            "status": self.status,
            "formula_hash": self.formula_hash,
            "gates": [g.as_dict() for g in self.gates],
            "confidence": self.confidence,
            "calibration_summary": dict(self.calibration_summary),
            "commercial_readiness": self.commercial_readiness,
            "config_summary": dict(self.config_summary),
            "audit_event_id": self.audit_event_id,
            "formula_state": self.formula_state.as_dict(),
            "time_series": [frame.as_dict() for frame in self.simulation],
        }


def _result(gate: str, status: str, detail: str = "", data: dict | None = None) -> GateResult:
    return GateResult(gate=gate, status=status, detail=detail, data=data or {})


def _config_summary(config: ReleaseGateConfig) -> dict:
    return {
        "expected_concentrate_ul": config.expected_concentrate_ul,
        "batch_volume_ml": config.batch_volume_ml,
        "temperature_K": config.temperature_K,
        "brief": config.brief,
        "family_archetype": config.family_archetype,
        "concentration_bracket": config.concentration_bracket,
        "allow_preblends": config.allow_preblends,
        "min_confidence_score": config.min_confidence_score,
        "ifra_headroom": config.ifra_headroom,
        "effective_ifra_headroom": config.effective_ifra_headroom(),
        "commercial_mode": config.commercial_mode,
        "commercial_confidence_policy": config.commercial_confidence_policy,
        "commercial_trial": config.is_commercial_trial(),
        "batch_scaling_targets_ml": list(config.batch_scaling_targets_ml),
        "audit_source": config.audit_source,
    }


def _status_from_gates(gates: list[GateResult]) -> str:
    if any(g.status == "FAIL" for g in gates):
        return "FAIL"
    if any(g.status == "WARN" for g in gates):
        return "WARN"
    return "PASS"


def _formula_vector_from_state(state: FormulaState) -> FormulaVector:
    return FormulaVector(
        ingredients=state.raw_percentages(),
        dilutions={m.name: m.dilution for m in state.materials},
    )


def _material_ifra_limit(material) -> float | None:
    return (
        IFRA_CAT4_LIMITS.get(material.name)
        or IFRA_CAT4_LIMITS.get(material.profile_name or "")
    )


def _gate_exact_subtotal(formula: Mapping, config: ReleaseGateConfig) -> GateResult:
    total_ul = sum(float(v or 0.0) for v in formula["ingredients_ul"].values())
    if abs(total_ul - config.expected_concentrate_ul) <= 0.5:
        return _result("exact_subtotal", "PASS", f"{total_ul:.1f} uL")
    return _result(
        "exact_subtotal",
        "FAIL",
        f"{total_ul:.1f} uL parsed; expected {config.expected_concentrate_ul:.1f} uL",
    )


def _gate_duplicates(state: FormulaState) -> GateResult:
    seen: dict[str, list[str]] = {}
    for material in state.materials:
        seen.setdefault(material.canonical_name, []).append(material.name)
    duplicates = {}
    allowed = {}
    for key, names in seen.items():
        if len(names) <= 1:
            continue
        lowered = {name.lower() for name in names}
        if any(lowered == allowed_set for allowed_set in ALLOWED_VARIANT_DUPLICATES):
            allowed[key] = names
        else:
            duplicates[key] = names
    if duplicates:
        return _result("duplicate_canonical_materials", "FAIL", json.dumps(duplicates, sort_keys=True))
    if allowed:
        return _result("duplicate_canonical_materials", "PASS", "allowed variants", allowed)
    return _result("duplicate_canonical_materials", "PASS")


def _gate_material_coverage(state: FormulaState) -> GateResult:
    unknown = sorted(m.name for m in state.materials if not m.is_known)
    if unknown:
        return _result("material_spine_coverage", "FAIL", ", ".join(unknown))
    return _result("material_spine_coverage", "PASS")


def _gate_data_coverage(state: FormulaState) -> GateResult:
    required = ("mw", "logp", "vp", "odt_air_ppm")
    missing = {
        m.name: [field for field in required if field in m.missing_fields]
        for m in state.materials
        if any(field in m.missing_fields for field in required)
    }
    if missing:
        return _result("physics_data_coverage", "FAIL", json.dumps(missing, sort_keys=True), missing)
    return _result("physics_data_coverage", "PASS")


def _gate_odt_coverage(state: FormulaState) -> GateResult:
    missing = sorted(m.name for m in state.materials if m.odt_air_ppm is None)
    if missing:
        return _result("odt_coverage", "FAIL", ", ".join(missing))
    return _result("odt_coverage", "PASS")


def _science_profile_for_material(material) -> tuple[object, str]:
    for candidate in (material.registry_name, material.profile_name, material.name):
        if not candidate:
            continue
        profile = get_science_profile(candidate)
        if (
            profile.stability_class != StabilityRisk.STABLE
            or profile.autoxidation_half_life_weeks is not None
            or profile.schiff_base_partners
            or profile.photostability != "stable"
        ):
            return profile, str(candidate)
    return get_science_profile(material.name), material.name


def _gate_chemistry_stability(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    active_pct = state.active_percentages()
    total_active_g = sum(m.active_g for m in state.materials) or 1.0
    active_mass_pct = {
        m.name: 100.0 * m.active_g / total_active_g
        for m in state.materials
    }
    functional_groups = {
        m.name: set(m.functional_groups)
        for m in state.materials
        if m.functional_groups
    }
    composition_g = {
        m.name: m.active_g
        for m in state.materials
        if m.active_g > 0
    }

    aldehydes = sorted(
        m.name for m in state.materials
        if "aldehyde" in functional_groups.get(m.name, set())
    )
    amines = sorted(
        m.name for m in state.materials
        if "amine" in functional_groups.get(m.name, set())
    )
    aldehyde_pct = sum(active_pct.get(name, 0.0) for name in aldehydes)
    amine_pct = sum(active_pct.get(name, 0.0) for name in amines)
    schiff_pairs: list[dict] = []
    if aldehydes and amines:
        amine_lookup = {normalize_name(name): name for name in amines}
        for material in state.materials:
            if material.name not in aldehydes:
                continue
            science_profile, science_source = _science_profile_for_material(material)
            partners = []
            for partner in science_profile.schiff_base_partners or []:
                matched = amine_lookup.get(normalize_name(partner))
                if matched and matched not in partners:
                    partners.append(matched)
            if partners:
                schiff_pairs.append({
                    "aldehyde": material.name,
                    "amines": partners,
                    "science_source": science_source,
                })
        if not schiff_pairs:
            schiff_pairs = [{"aldehyde": aldehyde, "amines": list(amines)} for aldehyde in aldehydes]

    shelf_life_days = predict_shelf_life_days(
        composition_g,
        T_K=295.0,
        bht_protected=False,
        threshold_pct=10.0,
        functional_groups=functional_groups,
    ) if composition_g else 1825

    oxidation_rows: list[dict] = []
    photolabile_rows: list[dict] = []
    flagged_materials: set[str] = set()
    for material in state.materials:
        science_profile, science_source = _science_profile_for_material(material)
        pct_mass = active_mass_pct.get(material.name, 0.0)
        if science_profile.stability_class == StabilityRisk.OXIDATION_PRONE:
            oxidation_rows.append({
                "material": material.name,
                "active_mass_pct": round(pct_mass, 3),
                "half_life_weeks": science_profile.autoxidation_half_life_weeks,
                "science_source": science_source,
            })
            flagged_materials.add(material.name)
        if science_profile.photostability in {"moderate", "labile"}:
            photolabile_rows.append({
                "material": material.name,
                "active_mass_pct": round(pct_mass, 3),
                "photostability": science_profile.photostability,
                "remaining_24h_outdoor": round(
                    photolysis_remaining_fraction(material.name, 24.0, indoor=False),
                    6,
                ),
                "science_source": science_source,
            })
            flagged_materials.add(material.name)

    reactive_mass_pct = sum(active_mass_pct.get(name, 0.0) for name in flagged_materials)
    fail_reasons: list[str] = []
    warn_reasons: list[str] = []

    if aldehyde_pct > 1.0 and amine_pct > 0.5:
        fail_reasons.append(
            f"Schiff-base risk: aldehydes {aldehyde_pct:.1f}% + amines {amine_pct:.1f}% active"
        )
    elif schiff_pairs:
        warn_reasons.append(
            f"aldehyde+amine contact present below hard threshold ({aldehyde_pct:.1f}% / {amine_pct:.1f}%)"
        )

    if shelf_life_days < 180:
        fail_reasons.append(f"predicted maturation shelf life {shelf_life_days} days")
    elif shelf_life_days < 365:
        warn_reasons.append(f"predicted maturation shelf life {shelf_life_days} days")

    if reactive_mass_pct > 20.0 and config.commercial_mode:
        fail_reasons.append(
            f"oxidation/photolability burden {reactive_mass_pct:.1f}% active mass in commercial mode"
        )
    elif reactive_mass_pct > 10.0:
        warn_reasons.append(f"oxidation/photolability burden {reactive_mass_pct:.1f}% active mass")

    data = {
        "shelf_life_days": shelf_life_days,
        "schiff_base": {
            "aldehydes": aldehydes,
            "amines": amines,
            "aldehyde_active_pct": round(aldehyde_pct, 3),
            "amine_active_pct": round(amine_pct, 3),
            "pairs": schiff_pairs,
        },
        "oxidation_prone_materials": oxidation_rows,
        "photolabile_materials": photolabile_rows,
        "reactive_material_active_mass_pct": round(reactive_mass_pct, 3),
    }
    if fail_reasons:
        return _result("chemistry_stability", "FAIL", "; ".join(fail_reasons), data)
    if warn_reasons:
        return _result("chemistry_stability", "WARN", "; ".join(warn_reasons), data)
    return _result("chemistry_stability", "PASS", f"predicted shelf life {shelf_life_days} days", data)


def _gate_phase_compatibility(state: FormulaState) -> GateResult:
    total_active_g = sum(m.active_g for m in state.materials) or 1.0
    covered = [m for m in state.materials if m.hsp is not None and m.active_g > 0]
    covered_mass_pct = 100.0 * sum(m.active_g for m in covered) / total_active_g
    hard_fail_supported = covered_mass_pct >= 80.0 and len(covered) >= 4
    data = {
        "hsp_covered_materials": [m.name for m in covered],
        "hsp_coverage_active_mass_pct": round(covered_mass_pct, 3),
        "hard_fail_supported": hard_fail_supported,
    }
    if len(covered) < 3 or covered_mass_pct < 40.0:
        detail = (
            f"HSP coverage too thin for trusted phase audit: {covered_mass_pct:.1f}% "
            f"active mass across {len(covered)} materials"
        )
        return _result("phase_compatibility", "WARN", detail, data)

    composition = {m.name: m.active_g for m in covered}
    hsp_table = {m.name: m.hsp for m in covered if m.hsp is not None}
    active_mass_pct = {
        m.name: 100.0 * m.active_g / total_active_g
        for m in covered
    }
    source_lookup = {m.name: m.hsp_source for m in covered}
    risks: list[dict] = []
    fail_rows: list[dict] = []
    warn_rows: list[dict] = []
    for name, red in micro_phase_risk(composition, hsp_table):
        pct_mass = active_mass_pct.get(name, 0.0)
        row = {
            "material": name,
            "red": round(red, 4),
            "active_mass_pct": round(pct_mass, 3),
            "hsp_source": source_lookup.get(name, "missing"),
        }
        risks.append(row)
        if pct_mass >= 2.0 and red > 1.25:
            fail_rows.append(row)
        elif pct_mass >= 1.0 and red > 1.0:
            warn_rows.append(row)

    data.update({
        "risks": risks,
        "fail_rows": fail_rows,
        "warn_rows": warn_rows,
    })
    if fail_rows and not hard_fail_supported:
        warn_rows = [*fail_rows, *warn_rows]
        data["warn_rows"] = warn_rows
        detail = (
            "tentative phase tension under partial HSP coverage: "
            + ", ".join(
                f"{row['material']} RED {row['red']:.2f} at {row['active_mass_pct']:.1f}%"
                for row in warn_rows[:4]
            )
        )
        return _result("phase_compatibility", "WARN", detail, data)
    if fail_rows:
        detail = "phase-out risk: " + ", ".join(
            f"{row['material']} RED {row['red']:.2f} at {row['active_mass_pct']:.1f}%"
            for row in fail_rows[:4]
        )
        return _result("phase_compatibility", "FAIL", detail, data)
    if warn_rows:
        detail = "phase tension: " + ", ".join(
            f"{row['material']} RED {row['red']:.2f} at {row['active_mass_pct']:.1f}%"
            for row in warn_rows[:4]
        )
        return _result("phase_compatibility", "WARN", detail, data)
    return _result("phase_compatibility", "PASS", "no HSP phase-out risk detected", data)


def _gate_preblends(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    opaque = sorted(m.name for m in state.materials if m.is_opaque_preblend)
    if not opaque:
        return _result("opaque_preblends", "PASS")
    status = "WARN" if config.allow_preblends and not config.commercial_mode else "FAIL"
    if config.commercial_mode:
        detail = "blocked in commercial mode: "
    else:
        detail = "allowed by config: " if config.allow_preblends else "not allowed: "
    return _result("opaque_preblends", status, detail + ", ".join(opaque), {"materials": opaque})


def _gate_blocked(state: FormulaState) -> GateResult:
    blocked = {
        m.name: reason
        for m in state.materials
        if (reason := blocked_reason(m.name))
    }
    if blocked:
        return _result("blocked_materials", "FAIL", json.dumps(blocked, sort_keys=True), blocked)
    return _result("blocked_materials", "PASS")


def _gate_pipette_floor(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    tiny_neat = sorted(
        f"{m.name}={m.raw_ul:.1f}uL"
        for m in state.materials
        if m.raw_ul < config.min_neat_trace_ul and m.dilution >= 0.999
    )
    if tiny_neat:
        return _result(
            "pipette_floor_neat_traces",
            "FAIL",
            "; ".join(tiny_neat) + f" below {config.min_neat_trace_ul:.1f} uL neat floor",
        )
    return _result("pipette_floor_neat_traces", "PASS")


def _gate_small_diluted_traces(state: FormulaState) -> GateResult:
    very_dilute = sorted(
        f"{m.name}={m.raw_ul:.1f}uL at {m.dilution * 100:.1f}%"
        for m in state.materials
        if m.raw_ul < 20.0 and m.dilution < 0.999
    )
    if very_dilute:
        return _result("small_diluted_traces", "WARN", "; ".join(very_dilute))
    return _result("small_diluted_traces", "PASS")


def _oav_check_as_dict(check) -> dict:
    return {
        "material": check.material,
        "source_conc_ppm": round(float(check.source_conc_ppm), 6),
        "target_conc_ppm": round(float(check.target_conc_ppm), 6),
        "odt_ppm": check.odt_ppm,
        "source_oav": check.source_oav,
        "target_oav": check.target_oav,
        "severity": check.severity,
        "message": check.message,
    }


def _gate_oav_scaling(formula: Mapping, config: ReleaseGateConfig) -> GateResult:
    targets = tuple(float(target) for target in config.batch_scaling_targets_ml if float(target) > 0)
    if not targets:
        return _result("oav_scaling_guard", "PASS", "not requested")

    ingredients = {str(k): float(v or 0.0) for k, v in formula["ingredients_ul"].items()}
    dilutions = {str(k): float(v or 1.0) for k, v in formula.get("dilutions", {}).items()}
    findings = []
    worst = "ok"
    severity_rank = {"ok": 0, "info": 1, "warn": 2, "error": 3}

    for target in targets:
        checks = check_proportional_scaling(
            ingredients,
            dilutions,
            config.batch_volume_ml,
            target,
        )
        for check in checks:
            if check.severity == "ok":
                continue
            row = _oav_check_as_dict(check)
            row["target_volume_ml"] = target
            findings.append(row)
            if severity_rank[check.severity] > severity_rank[worst]:
                worst = check.severity

    data = {
        "source_volume_ml": config.batch_volume_ml,
        "targets_ml": list(targets),
        "findings": findings,
    }
    if worst == "error":
        return _result("oav_scaling_guard", "FAIL", f"{len(findings)} scaling blocker(s)", data)
    if worst == "warn":
        status = "FAIL" if config.commercial_mode else "WARN"
        detail = f"{len(findings)} scaling warning(s)"
        if config.commercial_mode:
            detail = "commercial blocker: " + detail
        return _result("oav_scaling_guard", status, detail, data)
    if worst == "info":
        return _result("oav_scaling_guard", "WARN", f"{len(findings)} trace scaling info item(s)", data)
    return _result("oav_scaling_guard", "PASS", "all requested targets scale cleanly", data)


def _gate_safety(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    ingredients = {m.name: m.raw_ul for m in state.materials}
    dilutions = {m.name: m.dilution for m in state.materials}
    report = score_ifra_compliance(
        ingredients,
        dilutions,
        total_volume_ml=config.batch_volume_ml,
    )
    missing_ifra = sorted(
        m.name for m in state.materials
        if m.name not in IFRA_CAT4_LIMITS and (m.profile_name or "") not in IFRA_CAT4_LIMITS
    )
    headroom = config.effective_ifra_headroom()
    headroom_violations = []
    edge_dosing = []
    for material in state.materials:
        limit = _material_ifra_limit(material)
        if limit is None:
            continue
        actual_pct = (material.active_ul / 1000.0) / config.batch_volume_ml * 100.0
        effective_limit = limit * headroom
        ratio = actual_pct / limit if limit > 0 else 0.0
        effective_ratio = actual_pct / effective_limit if effective_limit > 0 else 0.0
        row = {
            "material": material.name,
            "actual_pct": round(actual_pct, 6),
            "limit_pct": limit,
            "effective_limit_pct": round(effective_limit, 6),
            "headroom": headroom,
            "usage_pct": round(ratio * 100.0, 1),
            "effective_usage_pct": round(effective_ratio * 100.0, 1),
        }
        if actual_pct > effective_limit + 1e-12:
            headroom_violations.append(row)
        elif ratio >= 0.7:
            edge_dosing.append(row)
    data = {
        "score": report.score,
        "violations": report.ifra_violations,
        "headroom_violations": headroom_violations,
        "warnings": report.ifra_warnings,
        "diagnostics": report.diagnostics,
        "edge_dosing": edge_dosing,
        "banned": report.banned_flags,
        "allergen_declarations": report.allergen_declarations,
        "dermal_exposure": report.dermal_exposure,
        "uptake_weighted_sensitizers": report.uptake_weighted_sensitizers,
        "missing_ifra_limit": missing_ifra,
        "headroom": config.ifra_headroom,
        "effective_headroom": headroom,
        "commercial_mode": config.commercial_mode,
    }
    if report.banned_flags or report.ifra_violations or headroom_violations:
        parts: list[str] = []
        if report.banned_flags:
            parts.append("banned: " + ", ".join(report.banned_flags))
        if report.ifra_violations:
            parts.append(
                "IFRA violations: "
                + ", ".join(
                    f"{v['material']} {v['actual_pct']}% > {v['limit_pct']}%"
                    for v in report.ifra_violations
                )
            )
        if headroom_violations:
            parts.append(
                f"IFRA headroom {headroom:.0%} violations: "
                + ", ".join(
                    f"{v['material']} {v['actual_pct']}% > {v['effective_limit_pct']}%"
                    for v in headroom_violations
                )
            )
        if report.diagnostics:
            parts.append("; ".join(report.diagnostics))
        return _result("safety_ifra_allergen", "FAIL", "; ".join(parts), data)
    if missing_ifra or report.ifra_warnings or report.allergen_declarations or edge_dosing:
        detail = []
        if missing_ifra:
            detail.append(f"{len(missing_ifra)} materials lack explicit IFRA Cat4 limits")
        if report.ifra_warnings or edge_dosing:
            detail.append(f"{len(report.ifra_warnings or edge_dosing)} materials near IFRA/headroom edge")
        if report.allergen_declarations:
            detail.append(f"{len(report.allergen_declarations)} EU allergen declarations")
        return _result("safety_ifra_allergen", "WARN", "; ".join(detail), data)
    return _result("safety_ifra_allergen", "PASS", f"score {report.score:.1f}", data)


def _gate_perfumer_logic(formula: Mapping, config: ReleaseGateConfig) -> GateResult:
    result = evaluate_perfumer_logic(
        formula,
        brief=config.brief,
        family_archetype=config.family_archetype,
    )
    if result.status == "FAIL":
        detail = "; ".join(
            f"{check.name}: {check.detail}"
            for check in result.checks
            if check.status == "FAIL"
        )
        return _result("perfumer_logic", "FAIL", f"{result.brief}; rerun optimizer: {detail}")
    if result.status == "WARN":
        detail = "; ".join(f"{check.name}: {check.detail}" for check in result.checks)
        return _result("perfumer_logic", "WARN", f"{result.brief}; {detail}")
    return _result("perfumer_logic", "PASS", result.brief)


def _gate_family_drift_detector(formula: Mapping, config: ReleaseGateConfig) -> GateResult:
    archetype = infer_archetype(config.brief, config.family_archetype)
    if not archetype:
        return _result("family_drift_detector", "PASS", "not requested")
    spec = get_archetype(archetype)
    if spec is None:
        return _result("family_drift_detector", "WARN", f"unknown family archetype: {archetype}")

    evaluation = evaluate_family_archetype(formula, archetype)
    failed = [check for check in evaluation.checks if check.status == "FAIL"]
    data = {
        "family_archetype": archetype,
        "family": evaluation.family,
        "label": evaluation.label,
        "checks": [
            {
                "name": check.name,
                "status": check.status,
                "detail": check.detail,
                "value": check.value,
            }
            for check in evaluation.checks
        ],
        "forbidden_hits": list(evaluation.forbidden_hits),
    }
    if failed:
        detail = "; ".join(f"{check.name}: {check.detail}" for check in failed[:4])
        return _result("family_drift_detector", "FAIL", f"{archetype}; {detail}", data)
    return _result("family_drift_detector", "PASS", f"{archetype}; no family drift", data)


def _gate_novelty_vs_reference(formula: Mapping, config: ReleaseGateConfig) -> GateResult:
    if not config.family_archetype:
        return _result("novelty_vs_reference", "PASS", "not requested")
    assessment = novelty_assessment(formula, config.family_archetype)
    return _result(
        "novelty_vs_reference",
        assessment["status"],
        assessment["detail"],
        {"family_archetype": config.family_archetype, **assessment},
    )


def _gate_perfume_knowledge(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    """Evaluate formula against comprehensive perfume knowledge taxonomy.

    Checks pyramid balance against family targets and evaluates OAV
    alignment with per-family/per-window OAV targets using the complete
    perfume knowledge system.
    """
    family = config.family_archetype or "floral"
    resolved = resolve_family_key(family)
    note_map = {m.name.lower(): str(m.note or "heart") for m in state.materials}

    active_pct = state.active_percentages()
    pyramid_eval = evaluate_pyramid_balance(
        active_pct, family=family, bracket=config.concentration_bracket, note_map=note_map,
    )

    material_oavs = {m.name: float(m.oav or 0.0) for m in state.materials if (m.oav or 0.0) > 0.0}
    material_families = {m.name: str(m.family or "unknown") for m in state.materials}

    top_oav_eval = evaluate_oav_family_targets(material_oavs, material_families, family, "top")
    heart_oav_eval = evaluate_oav_family_targets(material_oavs, material_families, family, "heart")
    base_oav_eval = evaluate_oav_family_targets(material_oavs, material_families, family, "base")

    warnings: list[str] = []
    fail_reasons: list[str] = []

    if pyramid_eval.status == "off_target":
        fail_reasons.append(f"Pyramid off-target: {pyramid_eval.details}")
    elif pyramid_eval.status == "needs_improvement":
        warnings.append(f"Pyramid needs improvement: {pyramid_eval.details}")

    for name, oav_eval in [("top", top_oav_eval), ("heart", heart_oav_eval), ("base", base_oav_eval)]:
        if oav_eval.status == "off_target":
            fail_reasons.append(f"{name} OAV off-target for family {resolved}")
        elif oav_eval.status == "needs_improvement":
            warnings.append(f"{name} OAV needs improvement for family {resolved}")

    data = {
        "family_key": resolved,
        "bracket": config.concentration_bracket,
        "pyramid": pyramid_eval.as_dict(),
        "oav_targets": {
            "top": top_oav_eval.as_dict(),
            "heart": heart_oav_eval.as_dict(),
            "base": base_oav_eval.as_dict(),
        },
    }

    if fail_reasons:
        return _result(
            "perfume_knowledge",
            "FAIL",
            "; ".join(fail_reasons[:3]),
            data,
        )
    if warnings:
        return _result(
            "perfume_knowledge",
            "WARN",
            "; ".join(warnings[:3]),
            data,
        )
    return _result(
        "perfume_knowledge",
        "PASS",
        f"Pyramid fit {pyramid_eval.overall_fit:.2f}; family {resolved} aligned",
        data,
    )


def _gate_oav_legibility(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    perceptible = [m for m in state.materials if (m.oav or 0.0) >= 1.0]
    if len(perceptible) < config.min_perceptible_materials:
        return _result(
            "oav_legibility",
            "FAIL",
            f"{len(perceptible)} perceptible materials; need >= {config.min_perceptible_materials}",
        )
    subliminal_active = sum(m.active_ul for m in state.materials if (m.oav or 0.0) < 0.2)
    subliminal_ratio = subliminal_active / (state.total_active_ul or 1.0)
    if subliminal_ratio > 0.45:
        return _result(
            "oav_legibility",
            "WARN",
            f"{subliminal_ratio:.0%} active mass is near-subliminal by OAV",
        )
    return _result("oav_legibility", "PASS", f"{len(perceptible)} perceptible materials")


def _gate_oav_intelligence(
    state: FormulaState,
    simulation: Sequence[SimulationFrame],
    config: ReleaseGateConfig,
) -> GateResult:
    if not str(config.family_archetype or "").strip():
        return _result("oav_intelligence", "PASS", "not requested")
    intelligence = analyze_oav_intelligence(state, simulation, config.family_archetype)
    status = intelligence.intelligence_status
    if status == "FAIL":
        detail = "; ".join(intelligence.intelligence_blocking_reasons[:3]) or "future-module OAV intelligence blockers present"
    elif status == "WARN":
        detail = "; ".join(intelligence.intelligence_warning_reasons[:3]) or "future-module OAV intelligence warnings present"
    else:
        detail = "future-module OAV intelligence aligned"
    return _result("oav_intelligence", status, detail, intelligence.as_dict())


def _gate_sensory_overcrowding(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    perceptible_channels = {
        m.family or m.canonical_name
        for m in state.materials
        if (m.intensity or 0.0) >= 0.5
    }
    if len(perceptible_channels) > config.max_perceptible_channels:
        return _result(
            "sensory_overcrowding",
            "FAIL",
            f"{len(perceptible_channels)} perceptible channels; olfactory-white risk",
        )
    if len(perceptible_channels) > 22:
        return _result(
            "sensory_overcrowding",
            "WARN",
            f"{len(perceptible_channels)} perceptible channels; check clarity",
        )
    return _result("sensory_overcrowding", "PASS", f"{len(perceptible_channels)} perceptible channels")


def _gate_master_perfumer(state: FormulaState, config: ReleaseGateConfig) -> GateResult:
    note = state.note_distribution()
    active = state.active_percentages()
    max_material = max(active.items(), key=lambda kv: kv[1]) if active else ("", 0.0)
    preblend_count = sum(1 for m in state.materials if m.is_opaque_preblend)
    issues: list[str] = []
    if state.material_count < 6:
        issues.append("too few materials for a finished fine-fragrance structure")
    if state.material_count > 32:
        issues.append("too many materials for a readable formula")
    if max_material[1] > 45.0:
        issues.append(f"{max_material[0]} dominates active formula at {max_material[1]:.1f}%")
    if note["top"] < 5.0:
        issues.append("opening likely underbuilt")
    if note["base"] < 15.0:
        issues.append("drydown likely underbuilt")
    if preblend_count and not config.allow_preblends:
        issues.append(f"{preblend_count} opaque preblend(s) hide perfumer intent")

    if len(issues) >= 3:
        return _result("master_perfumer_gate", "FAIL", "; ".join(issues))
    if issues:
        return _result("master_perfumer_gate", "WARN", "; ".join(issues))
    return _result("master_perfumer_gate", "PASS", "coherent, buildable, and readable")


def _gate_robustness(formula: Mapping, config: ReleaseGateConfig) -> tuple[GateResult, RobustnessReport]:
    report = audit_formula_robustness(formula, config)
    if report.status == "WARN":
        examples = "; ".join(
            f"{issue.material} {issue.direction}: {issue.detail}"
            for issue in report.issues[:3]
        )
        detail = f"{len(report.issues)} fragile perturbation(s) across {report.checked} checks"
        if examples:
            detail += f"; {examples}"
        status = "FAIL" if config.commercial_mode else "WARN"
        if config.commercial_mode:
            detail = "commercial blocker: " + detail
        return _result("robustness_perturbation", status, detail, report.as_dict()), report
    return (
        _result(
            "robustness_perturbation",
            "PASS",
            f"{report.checked} subtotal-preserving perturbations stable",
            report.as_dict(),
        ),
        report,
    )


def _gate_confidence(state: FormulaState, config: ReleaseGateConfig) -> tuple[GateResult, dict]:
    fv = _formula_vector_from_state(state)
    confidence = ConfidenceScorer().score(fv.ingredients)
    pipeline_confidence = state.uncertainty.confidence_score
    combined = round((confidence["overall_confidence"] + pipeline_confidence) / 2.0, 1)
    confidence = dict(confidence)
    confidence["pipeline_confidence"] = pipeline_confidence
    confidence["combined_confidence"] = combined
    confidence["combined_grade"] = (
        "HIGH" if combined >= 80 else
        "MEDIUM" if combined >= 50 else
        "LOW" if combined >= 25 else
        "VERY_LOW"
    )
    strict_commercial_confidence = config.commercial_mode and config.commercial_confidence_policy != "warn"
    threshold = max(
        config.min_confidence_score,
        50.0 if strict_commercial_confidence else config.min_confidence_score,
    )
    confidence["required_minimum"] = threshold
    if combined < threshold:
        return (
            _result(
                "confidence_minimum",
                "FAIL",
                f"combined confidence {combined:.1f} below {threshold:.1f}",
                confidence,
            ),
            confidence,
        )
    if combined < 50.0:
        detail = f"combined confidence {combined:.1f}"
        if config.is_commercial_trial():
            detail += "; commercial-trial warning, not sellable until calibrated"
        return (
            _result("confidence_minimum", "WARN", detail, confidence),
            confidence,
        )
    return (_result("confidence_minimum", "PASS", f"combined confidence {combined:.1f}", confidence), confidence)


def _commercial_readiness(status: str, gates: list[GateResult], confidence: dict, config: ReleaseGateConfig) -> str:
    if status == "FAIL":
        return "NOT_RELEASE_READY"
    if config.is_commercial_trial() and confidence.get("combined_confidence", 0.0) < 50.0:
        return "COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE"
    if confidence.get("combined_confidence", 0.0) < 50.0:
        return "TECHNICAL_PASS_LOW_CONFIDENCE"
    if config.is_commercial_trial() and any(g.status == "WARN" for g in gates):
        return "COMMERCIAL_TRIAL_CONDITIONAL_REVIEW"
    if config.is_commercial_trial():
        return "COMMERCIAL_TRIAL_READY"
    if config.commercial_mode and any(g.status == "WARN" for g in gates):
        return "CONDITIONAL_PASS_NEEDS_REVIEW"
    if any(g.status == "WARN" for g in gates):
        return "CONDITIONAL_PASS_NEEDS_REVIEW"
    return "COMMERCIAL_READY_FOR_TRIAL"


def gate_formula(formula: Mapping, config: ReleaseGateConfig | None = None) -> GateReport:
    """Run all reusable release gates on a parsed formula record."""
    config = config or ReleaseGateConfig()
    formula_archetype = str(formula.get("family_archetype", "") or "").strip()
    if formula_archetype and formula_archetype != config.family_archetype:
        config = replace(config, family_archetype=formula_archetype)
    if not config.family_archetype and config.brief:
        resolved = infer_archetype(config.brief, "")
        if resolved:
            config = replace(config, family_archetype=resolved)
    ingredients_ul: Mapping[str, float] = formula["ingredients_ul"]
    dilutions: Mapping[str, float] = formula.get("dilutions", {})
    state = build_formula_state(
        ingredients_ul,
        dilutions,
        batch_volume_ml=config.batch_volume_ml,
        temperature_K=config.temperature_K,
    )
    simulation = tuple(
        simulate_formula(
            ingredients_ul,
            dilutions,
            batch_volume_ml=config.batch_volume_ml,
            temperature_K=config.temperature_K,
        )
    )
    gates = [
        _gate_exact_subtotal(formula, config),
        _gate_duplicates(state),
        _gate_material_coverage(state),
        _gate_data_coverage(state),
        _gate_odt_coverage(state),
        _gate_chemistry_stability(state, config),
        _gate_phase_compatibility(state),
        _gate_preblends(state, config),
        _gate_blocked(state),
        _gate_pipette_floor(state, config),
        _gate_small_diluted_traces(state),
        _gate_oav_scaling(formula, config),
        _gate_safety(state, config),
        _gate_perfumer_logic(formula, config),
        _gate_family_drift_detector(formula, config),
        _gate_novelty_vs_reference(formula, config),
        _gate_perfume_knowledge(state, config),
        _gate_oav_legibility(state, config),
        _gate_oav_intelligence(state, simulation, config),
        _gate_sensory_overcrowding(state, config),
        _gate_master_perfumer(state, config),
    ]
    robustness_gate, _robustness = _gate_robustness(formula, config)
    gates.append(robustness_gate)
    confidence_gate, confidence = _gate_confidence(state, config)
    gates.append(confidence_gate)
    status = _status_from_gates(gates)
    formula_hash = formula_hash_from_record(formula)
    calibration_summary = summarize_records(load_records(), formula_hash=formula_hash)
    report = GateReport(
        number=int(formula.get("number", 1)),
        name=str(formula.get("name", "Formula")),
        status=status,
        gates=tuple(gates),
        formula_state=state,
        simulation=simulation,
        confidence=confidence,
        formula_hash=formula_hash,
        calibration_summary=calibration_summary,
        commercial_readiness=_commercial_readiness(status, gates, confidence, config),
        config_summary=_config_summary(config),
    )
    if config.audit_enabled:
        event = append_event(gate_report_event(report, config))
        report = replace(report, audit_event_id=str(event.get("event_id", "")))
    return report
