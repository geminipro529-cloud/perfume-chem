"""
Perfume Pipeline Orchestrator — Real Integrated Version.

Replaces Perplexity stubs with calls to actual engine modules.
Fail-fast on integrity issues. Returns structured JSON report.

Usage:
    python "perplexity changes/perfume_pipeline_orchestrator.py"
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Mapping

# Fix stdout encoding for Unicode characters (→, µ, etc.)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Real engine imports ─────────────────────────────────────────────
from engine.pipeline.formula_state import FormulaState, MaterialState, build_formula_state
from engine.pipeline.simulator import simulate_formula, SimulationFrame, DEFAULT_WINDOWS
from engine.pipeline.gates import (
    ReleaseGateConfig,
    gate_formula,
    GateReport,
    GateResult,
    DEFAULT_CONCENTRATE_UL,
)
from engine.pipeline.oav_intelligence import analyze_oav_intelligence
from engine.pipeline.robustness import audit_formula_robustness
from engine.pipeline.audit_log import config_summary
from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority

from engine.families.registry import (
    evaluate_family_archetype,
    infer_archetype,
    get_archetype,
    ArchetypeSpec,
    BRIEF_DEFAULTS,
)

from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name
from engine.material_resolver import resolve_material
from engine.ifra_safety import IFRA_CAT4_LIMITS, score_ifra_compliance
from engine.confidence import ConfidenceScorer
from engine.knowledge.perfume_knowledge import evaluate_pyramid_balance
from engine.knowledge.pyramid_targets import PYRAMID_RATIOS, OAV_TARGETS_BY_FAMILY
from engine.ingredient_intelligence import get_profile, MaterialProfile

# ═════════════════════════════════════════════════════════════════════
# Stage Results
# ═════════════════════════════════════════════════════════════════════


@dataclass
class StageResult:
    name: str
    status: str  # PASS | FAIL | WARN | SKIP
    detail: str = ""
    data: dict = field(default_factory=dict)


def _pass(name: str, detail: str = "", **kw) -> StageResult:
    return StageResult(name=name, status="PASS", detail=detail, data=kw)


def _fail(name: str, detail: str, **kw) -> StageResult:
    return StageResult(name=name, status="FAIL", detail=detail, data=kw)


def _warn(name: str, detail: str, **kw) -> StageResult:
    return StageResult(name=name, status="WARN", detail=detail, data=kw)


# ═════════════════════════════════════════════════════════════════════
# Stage 1: Registry Integrity — detect duplicate ODT keys
# ═════════════════════════════════════════════════════════════════════


def stage1_registry_integrity(ctx: dict) -> StageResult:
    """Fail-fast on duplicate normalized ODT keys and detect deprecated entries."""
    seen: dict[str, list[str]] = {}
    for raw_key in ODT_DATA:
        norm = normalize_name(raw_key)
        if norm not in seen:
            seen[norm] = []
        seen[norm].append(raw_key)

    duplicates = {n: ks for n, ks in seen.items() if len(ks) > 1}
    if duplicates:
        detail = "; ".join(
            f"{n}: {', '.join(ks)}" for n, ks in duplicates.items()
        )
        return _fail("registry_integrity", f"duplicate normalized keys: {detail}", duplicates=duplicates)

    missing_odt = []
    for name in ctx.get("formula_materials", []):
        norm = normalize_name(name)
        if norm not in seen:
            missing_odt.append(name)

    return _pass(
        "registry_integrity",
        f"{len(ODT_DATA)} unique entries, {len(seen)} normalized keys",
        total_entries=len(ODT_DATA),
        total_normalized=len(seen),
        missing_odt=missing_odt,
    )


# ═════════════════════════════════════════════════════════════════════
# Stage 2: Name Normalization — resolve every formula material
# ═════════════════════════════════════════════════════════════════════


def stage2_name_normalization(ctx: dict) -> StageResult:
    """Resolve every formula material to canonical name. Fail on unknown."""
    raw_formula = ctx.get("raw_formula", [])
    resolved: list[dict] = []
    failures: list[str] = []

    for item in raw_formula:
        name = str(item.get("name", "")).strip()
        identity = resolve_material(name)
        canonical = identity.canonical_name
        is_known = identity.is_known
        resolved.append({
            "requested": name,
            "canonical": canonical,
            "profile_name": identity.profile_name,
            "registry_name": identity.registry_name,
            "is_known": is_known,
            "dilution": float(item.get("dilution", 1.0)),
            "percent": float(item.get("percent", 0)),
        })
        if not is_known:
            failures.append(name)

    ctx["resolved_formula"] = resolved
    if failures:
        return _fail("name_normalization", f"unknown materials: {failures}", unresolved=failures)
    return _pass(
        "name_normalization",
        f"{len(resolved)} materials resolved",
        materials=resolved,
    )


# ═════════════════════════════════════════════════════════════════════
# Stage 3: Family Resolution — brief → archetype key
# ═════════════════════════════════════════════════════════════════════


def stage3_family_resolution(ctx: dict) -> StageResult:
    """Resolve brief to archetype. Fail if unrecognized."""
    brief = str(ctx.get("brief", "")).strip()
    family_archetype = str(ctx.get("family_archetype", "")).strip()

    archetype_key = infer_archetype(brief, family_archetype)
    if not archetype_key:
        return _fail(
            "family_resolution",
            f"brief='{brief}' not in BRIEF_DEFAULTS: {list(BRIEF_DEFAULTS)}",
            brief=brief,
            available=list(BRIEF_DEFAULTS),
        )

    spec = get_archetype(archetype_key)
    if spec is None:
        return _fail(
            "family_resolution",
            f"archetype key '{archetype_key}' not found in registry",
            archetype_key=archetype_key,
        )

    ctx["archetype_key"] = archetype_key
    ctx["archetype_spec"] = spec
    ctx["resolved_family"] = spec.family
    return _pass(
        "family_resolution",
        f"brief={brief} → archetype={archetype_key} (family={spec.family})",
        archetype_key=archetype_key,
        family=spec.family,
        label=spec.label,
    )


# ═════════════════════════════════════════════════════════════════════
# Stage 4: Build Formula State — raw % → active µL → physical state
# ═════════════════════════════════════════════════════════════════════


def stage4_build_formula_state(ctx: dict) -> StageResult:
    """Convert raw formula data to canonical FormulaState."""
    expected_ul = float(ctx.get("expected_concentrate_ul", DEFAULT_CONCENTRATE_UL))
    resolved = ctx.get("resolved_formula", [])

    ingredients_ul: dict[str, float] = {}
    dilutions: dict[str, float] = {}

    for item in resolved:
        pct = float(item["percent"])
        dil = float(item["dilution"])
        name = item["canonical"]
        ul = pct * expected_ul / 100.0
        ingredients_ul[name] = ul
        dilutions[name] = dil

    if not ingredients_ul:
        return _fail("build_formula_state", "no materials in formula")

    ctx["ingredients_ul"] = ingredients_ul
    ctx["dilutions"] = dilutions

    try:
        state = build_formula_state(
            ingredients_ul,
            dilutions,
            batch_volume_ml=float(ctx.get("batch_volume_ml", 30.0)),
            temperature_K=float(ctx.get("temperature_K", 305.0)),
            context=ctx.get("context", "skin"),
        )
    except Exception as e:
        return _fail("build_formula_state", f"engine error: {e}")

    ctx["formula_state"] = state

    missing = sum(1 for m in state.materials if m.missing_fields)
    detail = (
        f"{state.material_count} materials, {missing} with missing fields, "
        f"total active: {state.total_active_ul:.1f} µL"
    )
    return _pass(
        "build_formula_state",
        detail,
        material_count=state.material_count,
        total_active_ul=state.total_active_ul,
        missing_fields_count=missing,
        missing_fields=[m.name for m in state.materials if m.missing_fields],
    )


# ═════════════════════════════════════════════════════════════════════
# Stage 5: Active Percent Check — ensure dilution-aware dosages
# ═════════════════════════════════════════════════════════════════════


def stage5_active_percent_check(ctx: dict) -> StageResult:
    """Verify active percentages are computed for all materials."""
    state: FormulaState = ctx.get("formula_state")
    if state is None:
        return _fail("active_percent_check", "no formula state")

    raw_pct = state.raw_percentages()
    active_pct = state.active_percentages()
    diffs = {}
    for name in raw_pct:
        rp = raw_pct[name]
        ap = active_pct.get(name, 0)
        if abs(rp - ap) > 0.01:
            diffs[name] = {"raw_pct": round(rp, 2), "active_pct": round(ap, 2)}

    if not diffs:
        return _pass("active_percent_check", "all materials undiluted — raw = active")

    return _pass(
        "active_percent_check",
        f"{len(diffs)} materials have dilution-adjusted active percent",
        diluted_materials=diffs,
        note_distribution=state.note_distribution(),
    )


# ═════════════════════════════════════════════════════════════════════
# Stage 6: ODT Coverage — every material must have ODT data
# ═════════════════════════════════════════════════════════════════════


def stage6_odt_coverage(ctx: dict) -> StageResult:
    """Fail on any material without ODT data."""
    state: FormulaState = ctx.get("formula_state")
    if state is None:
        return _fail("odt_coverage", "no formula state")

    missing = [m for m in state.materials if m.odt_air_ppm is None]
    if missing:
        detail = "; ".join(f"{m.name}" for m in missing)
        return _fail("odt_coverage", f"{len(missing)} missing ODT: {detail}", missing=[m.name for m in missing])

    return _pass(
        "odt_coverage",
        f"all {state.material_count} materials have ODT data",
    )


# ═════════════════════════════════════════════════════════════════════
# Stage 7: OAV Computation — compute per-material OAV, flag sub-threshold
# ═════════════════════════════════════════════════════════════════════


def stage7_oav_computation(ctx: dict) -> StageResult:
    """Compute OAV from formula state. Flag sub-threshold materials by role."""
    state: FormulaState = ctx.get("formula_state")
    if state is None:
        return _fail("oav_computation", "no formula state")

    oav_table = []
    sub_threshold = []
    for m in state.materials:
        row = {
            "name": m.name,
            "canonical": m.canonical_name,
            "note": m.note,
            "family": m.family,
            "raw_ul": round(m.raw_ul, 4),
            "dilution": m.dilution,
            "active_ul": round(m.active_ul, 4),
            "vapor_ppm": round(m.vapor_ppm, 6),
            "odt_air_ppm": m.odt_air_ppm,
            "oav": round(m.oav, 2) if m.oav is not None else None,
            "intensity": round(m.intensity, 4) if m.intensity is not None else None,
            "vp_pa": round(m.vp_pure_pa, 4) if m.vp_pure_pa is not None else None,
            "gamma": round(m.gamma, 4),
            "mole_fraction": round(m.mole_fraction, 6),
        }
        oav_table.append(row)
        if m.oav is not None and m.oav < 1:
            role = getattr(get_profile(m.canonical_name), "role", "unknown") if m.canonical_name else "unknown"
            sub_threshold.append({
                "name": m.name,
                "oav": round(m.oav, 2),
                "role": role,
                "active_ul": round(m.active_ul, 2),
            })

    ctx["oav_table"] = oav_table
    total_ppm = sum(m.vapor_ppm for m in state.materials)
    perceptible = [m for m in state.materials if m.oav is not None and m.oav >= 1]
    dominant = [m for m in state.materials if m.oav is not None and m.oav > 500]

    detail = (
        f"{len(perceptible)}/{state.material_count} perceptible (OAV>=1), "
        f"{len(sub_threshold)} sub-threshold, "
        f"total vapor: {total_ppm:.2f} ppm"
    )

    data = {
        "total_vapor_ppm": round(total_ppm, 4),
        "perceptible_count": len(perceptible),
        "sub_threshold_count": len(sub_threshold),
        "sub_threshold_materials": sub_threshold,
        "dominant_materials": [m.name for m in dominant],
        "oav_table": oav_table,
    }

    return _pass("oav_computation", detail, **data)


# ═════════════════════════════════════════════════════════════════════
# Stage 8: Family Fit — check formula against archetype anchors
# ═════════════════════════════════════════════════════════════════════


def stage8_family_fit(ctx: dict) -> StageResult:
    """Evaluate formula family fit. Fail on anchor violations."""
    state: FormulaState = ctx.get("formula_state")
    archetype_key = ctx.get("archetype_key", "")
    if state is None:
        return _fail("family_fit", "no formula state")
    if not archetype_key:
        return _fail("family_fit", "no archetype resolved")

    # Build formula record in the format families.registry expects
    ingredients_pct = state.raw_percentages()
    dilutions = {m.name: m.dilution for m in state.materials}
    total = sum(float(v or 0.0) for v in ingredients_pct.values()) or 1.0
    formula_record = {
        "number": 1,
        "name": ctx.get("formula_name", "unnamed"),
        "body": ctx.get("formula_name", ""),
        "family_archetype": archetype_key,
        "ingredients_pct": {k: float(v) / total * 100.0 for k, v in ingredients_pct.items()},
        "ingredients_ul": ctx.get("ingredients_ul", {}),
        "dilutions": dilutions,
    }

    evaluation = evaluate_family_archetype(formula_record, archetype_key)
    spec = get_archetype(archetype_key)

    failures = [c for c in evaluation.checks if c.status == "FAIL"]
    warns = [c for c in evaluation.checks if c.status == "WARN"]

    data = {
        "archetype": evaluation.archetype,
        "family": evaluation.family,
        "label": evaluation.label,
        "status": evaluation.status,
        "checks": [asdict(c) for c in evaluation.checks],
        "forbidden_hits": list(evaluation.forbidden_hits),
        "oav_targets": dict(spec.oav_targets) if spec else {},
    }

    if failures:
        detail = "; ".join(f"{c.name}: {c.detail}" for c in failures[:5])
        return _fail("family_fit", f"{len(failures)} anchor failures: {detail}", **data)

    if evaluation.status == "WARN":
        return _warn("family_fit", "some drift limits near boundary", **data)

    return _pass(
        "family_fit",
        f"all {len(evaluation.checks)} checks passed for {evaluation.label}",
        **data,
    )


# ═════════════════════════════════════════════════════════════════════
# Stage 9: Pyramid Balance — compare T/H/B vs family target
# ═════════════════════════════════════════════════════════════════════


def stage9_pyramid_balance(ctx: dict) -> StageResult:
    """Evaluate top/heart/base ratio vs family target."""
    state: FormulaState = ctx.get("formula_state")
    family = ctx.get("resolved_family", "")
    if state is None:
        return _fail("pyramid_balance", "no formula state")

    nd = state.note_distribution()
    oav_nd = state.as_dict().get("note_distribution", nd)

    target_key = family
    family_pyramids = PYRAMID_RATIOS.get(target_key, {})
    bracket = str(ctx.get("concentration_bracket", "EdP"))

    # Map bracket string to enum if needed
    bracket_key = bracket.upper().replace(" ", "_")
    target_ratio = None
    for tbr, pyr in family_pyramids.items():
        if tbr.name.upper() == bracket_key or tbr.value.upper() == bracket_key:
            target_ratio = pyr
            break
    if not target_ratio:
        # Try OAV_TARGETS_BY_FAMILY for a looser check
        oav_targets = OAV_TARGETS_BY_FAMILY.get(target_key, {})
        if oav_targets:
            target_ratio = {"top": 20, "heart": 40, "base": 40}  # standard EDP fallback
            source = "oav_targets (loose fallback)"
        else:
            target_ratio = {"top": 20, "heart": 40, "base": 40}
            source = "generic EDP fallback"
    else:
        source = f"pyramid_targets.{target_key}.{bracket}"

    actual = {"top": nd.get("top", 0), "heart": nd.get("heart", 0), "base": nd.get("base", 0)}
    if isinstance(target_ratio, dict):
        expected = target_ratio
    else:
        expected = {"top": target_ratio.top, "heart": target_ratio.heart, "base": target_ratio.base}

    deviations = {}
    for tier in ("top", "heart", "base"):
        exp = expected.get(tier, 33.3)
        act = actual.get(tier, 0)
        deviations[tier] = {"expected": exp, "actual": act, "delta": round(act - exp, 1)}

    issues = [t for t, d in deviations.items() if abs(d["delta"]) > 10]
    data = {
        "source": source,
        "target": expected,
        "actual": actual,
        "deviations": deviations,
        "oav_distribution": oav_nd,
    }

    if issues:
        detail = f"deviation in {', '.join(issues)}; source={source}"
        return _warn("pyramid_balance", detail, **data)

    return _pass("pyramid_balance", f"T/H/B within range; source={source}", **data)


# ═════════════════════════════════════════════════════════════════════
# Stage 10: Temporal Simulation — run 5-window headspace evolution
# ═════════════════════════════════════════════════════════════════════


def stage10_temporal_simulation(ctx: dict) -> StageResult:
    """Run temporal simulation and capture OAV evolution."""
    ingredients_ul = ctx.get("ingredients_ul", {})
    dilutions = ctx.get("dilutions", {})
    if not ingredients_ul:
        return _fail("temporal_simulation", "no ingredients")

    try:
        frames = simulate_formula(
            ingredients_ul,
            dilutions,
            batch_volume_ml=float(ctx.get("batch_volume_ml", 30.0)),
            temperature_K=float(ctx.get("temperature_K", 305.0)),
            context=ctx.get("context", "skin"),
        )
    except Exception as e:
        return _fail("temporal_simulation", f"simulation error: {e}")

    window_data = []
    for frame in frames:
        state = frame.state
        nd = state.note_distribution()
        leaders = frame.dominant_oav(limit=5)
        total_vapor = state.total_vapor_ppm
        window_data.append({
            "label": frame.label,
            "t_seconds": frame.t_seconds,
            "total_vapor_ppm": round(total_vapor, 4),
            "total_active_ul": round(state.total_active_ul, 2),
            "note_distribution": nd,
            "dominant_oav": leaders,
            "receptor_activation": {k: round(v, 4) for k, v in frame.receptor_activation.items()},
        })

    ctx["temporal_frames"] = frames
    ctx["temporal_data"] = window_data

    first = frames[0]
    last = frames[-1]
    evap_pct = 0.0
    if first.state.total_active_ul > 0:
        evap_pct = (1 - last.state.total_active_ul / first.state.total_active_ul) * 100

    base_at_drydown = last.state.note_distribution().get("base", 0)

    detail = (
        f"{len(window_data)} windows; "
        f"evap: {evap_pct:.0f}% over {last.t_seconds:.0f}s; "
        f"base @ drydown: {base_at_drydown:.0f}%"
    )
    return _pass("temporal_simulation", detail, windows=window_data, evaporation_pct=round(evap_pct, 1))


# ═════════════════════════════════════════════════════════════════════
# Stage 11: IFRA Safety — regulatory compliance check
# ═════════════════════════════════════════════════════════════════════


def stage11_ifra_safety(ctx: dict) -> StageResult:
    """Check IFRA compliance for all materials."""
    state: FormulaState = ctx.get("formula_state")
    if state is None:
        return _fail("ifra_safety", "no formula state")

    ifra_issues = []
    ifra_ok = 0
    batch_ml = float(ctx.get("batch_volume_ml", 30.0))
    finished_product_ul = batch_ml * 1000.0  # total bottle volume in µL
    headroom = float(ctx.get("ifra_headroom", 1.0))

    for m in state.materials:
        limit = m.ifra_limit_pct
        if limit is None:
            ifra_ok += 1
            continue
        # IFRA limits are % of FINISHED PRODUCT, not concentrate.
        # active_ul is in concentrate; divide by total bottle volume.
        active_pct_finished = (m.active_ul / finished_product_ul) * 100.0
        effective_limit = limit * headroom
        if active_pct_finished > effective_limit:
            ifra_issues.append({
                "material": m.name,
                "active_pct_finished": round(active_pct_finished, 4),
                "limit_pct": limit,
                "effective_limit": round(effective_limit, 4),
                "exceedance_pct": round((active_pct_finished / effective_limit - 1) * 100, 1),
            })
        else:
            ifra_ok += 1

    data = {
        "checked": len(state.materials),
        "compliant": ifra_ok,
        "violations": len(ifra_issues),
        "headroom": float(ctx.get("ifra_headroom", 1.0)),
        "violation_details": ifra_issues,
    }

    if ifra_issues:
        detail = f"{len(ifra_issues)} IFRA violations: " + "; ".join(
            f"{i['material']} at {i['active_pct_finished']:.3f}% (limit {i['effective_limit']:.3f}%)"
            for i in ifra_issues[:5]
        )
        return _fail("ifra_safety", detail, **data)

    return _pass("ifra_safety", f"all {ifra_ok} materials within IFRA limits", **data)


# ═════════════════════════════════════════════════════════════════════
# Stage 12: Robustness — perturbation sensitivity audit
# ═════════════════════════════════════════════════════════════════════


def stage12_robustness(ctx: dict) -> StageResult:
    """Perturbation audit — check formula stability under ±5% dose changes."""
    ingredients_ul = ctx.get("ingredients_ul", {})
    dilutions = ctx.get("dilutions", {})
    if not ingredients_ul:
        return _fail("robustness", "no ingredients")

    total = sum(float(v or 0.0) for v in ingredients_ul.values()) or 1.0
    formula_record = {
        "number": 1,
        "name": ctx.get("formula_name", "unnamed"),
        "body": ctx.get("formula_name", ""),
        "family_archetype": ctx.get("archetype_key", ""),
        "ingredients_pct": {k: float(v) / total * 100.0 for k, v in ingredients_ul.items()},
        "ingredients_ul": ingredients_ul,
        "dilutions": dilutions,
    }

    config = ReleaseGateConfig(
        expected_concentrate_ul=float(ctx.get("expected_concentrate_ul", DEFAULT_CONCENTRATE_UL)),
        batch_volume_ml=float(ctx.get("batch_volume_ml", 30.0)),
        temperature_K=float(ctx.get("temperature_K", 305.0)),
        brief=ctx.get("brief", "auto"),
        family_archetype=ctx.get("archetype_key", ""),
        ifra_headroom=float(ctx.get("ifra_headroom", 1.0)),
    )

    try:
        report = audit_formula_robustness(formula_record, config)
    except Exception as e:
        return _fail("robustness", f"audit error: {e}")

    issues = list(report.issues)
    data = {
        "status": report.status,
        "checked": report.checked,
        "issues_count": len(issues),
        "issue_details": [i.as_dict() for i in issues[:10]],
        "perturbations": [p.as_dict() for p in report.perturbations[:10]],
    }

    if report.status == "FAIL":
        detail = f"{len(issues)} failures: " + "; ".join(
            f"{i.material} {i.direction}: {i.detail}" for i in issues[:3]
        )
        return _fail("robustness", detail, **data)

    if report.status == "WARN":
        return _warn("robustness", f"{len(issues)} warnings", **data)

    return _pass("robustness", f"{report.checked} perturbations stable", **data)


# ═════════════════════════════════════════════════════════════════════
# Stage 13: OAV Intelligence — family targets, balance, synergy
# ═════════════════════════════════════════════════════════════════════


def stage13_oav_intelligence(ctx: dict) -> StageResult:
    """Run OAV intelligence analysis — family targets, contrast, synergy."""
    state: FormulaState = ctx.get("formula_state")
    frames: list[SimulationFrame] | None = ctx.get("temporal_frames")
    archetype_key = ctx.get("archetype_key", "")

    if state is None:
        return _fail("oav_intelligence", "no formula state")

    try:
        result = analyze_oav_intelligence(state, frames or (), family_archetype=archetype_key)
    except Exception as e:
        return _warn("oav_intelligence", f"analysis error: {e}")

    data = {
        "family_oav_targets": getattr(result, "family_oav_targets", {}),
        "balance_report": getattr(result, "balance_report", {}),
        "performance_projection": getattr(result, "performance_projection", {}),
        "synergy_pairs": getattr(result, "synergy_pairs", []),
        "antagonist_pairs": getattr(result, "antagonist_pairs", []),
        "shift_zones": getattr(result, "shift_zones", {}),
    }

    return _pass("oav_intelligence", "analysis complete", **data)


# ═════════════════════════════════════════════════════════════════════
# Stage 14: Confidence — formula confidence scoring
# ═════════════════════════════════════════════════════════════════════


def stage14_confidence(ctx: dict) -> StageResult:
    """Calculate formula confidence score."""
    state: FormulaState = ctx.get("formula_state")
    if state is None:
        return _fail("confidence", "no formula state")

    try:
        confidence = ConfidenceScorer().score(state.raw_percentages())
    except Exception as e:
        return _warn("confidence", f"confidence error: {e}")

    pipeline_conf = state.uncertainty.confidence_score
    combined = round((confidence.get("overall_confidence", 0) + pipeline_conf) / 2.0, 1)

    grade = "HIGH" if combined >= 80 else "MEDIUM" if combined >= 50 else "LOW" if combined >= 25 else "VERY_LOW"

    data = {
        "overall_confidence": confidence.get("overall_confidence", 0),
        "pipeline_confidence": round(pipeline_conf, 1),
        "combined_confidence": combined,
        "combined_grade": grade,
        "missing_fields": [m.name for m in state.materials if m.missing_fields],
    }

    if combined < 25:
        return _fail("confidence", f"combined confidence {combined} < 25", **data)
    if combined < 50:
        return _warn("confidence", f"combined confidence {combined}", **data)

    return _pass("confidence", f"combined confidence {combined} ({grade})", **data)


# ═════════════════════════════════════════════════════════════════════
# Stage 15: Repair Suggestions — concrete fixes for failed gates
# ═════════════════════════════════════════════════════════════════════


def stage15_repair_suggestions(ctx: dict) -> StageResult:
    """Generate concrete repair suggestions for failed gates."""
    stages: list[StageResult] = ctx.get("stage_results", [])
    failed = [s for s in stages if s.status == "FAIL"]
    warnings = [s for s in stages if s.status == "WARN"]

    suggestions = []

    for f in failed:
        if f.name == "family_fit":
            data = f.data
            spec: ArchetypeSpec | None = ctx.get("archetype_spec")
            if spec and spec.repair_pool:
                pool_desc = "; ".join(f"{m} +{pct}%" for m, pct in spec.repair_pool.items())
                suggestions.append(f"Add from repair pool: {pool_desc}")
            if data.get("forbidden_hits"):
                suggestions.append(f"Remove forbidden materials: {', '.join(data['forbidden_hits'])}")

        if f.name == "ifra_safety":
            violations = f.data.get("violation_details", [])
            for v in violations[:5]:
                suggestions.append(
                    f"Reduce {v['material']} from {v['active_pct_finished']:.3f}% "
                    f"to {v['effective_limit']:.3f}% (IFRA limit)"
                )

        if f.name == "odt_coverage":
            missing = f.data.get("missing", [])
            for m_name in missing[:5]:
                suggestions.append(f"Add ODT data for {m_name} to engine/odor_thresholds.py")

        if f.name == "robustness":
            suggestions.append("Reduce high-dose materials (±5% perturbation causes family drift)")

        if f.name == "pyramid_balance":
            deviations = f.data.get("deviations", {})
            for tier, d in deviations.items():
                delta = d.get("delta", 0)
                if abs(delta) > 10:
                    direction = "increase" if delta < 0 else "reduce"
                    suggestions.append(f"{direction} {tier} tier by {abs(delta):.0f}%")

        if f.name == "confidence":
            missing = f.data.get("missing_fields", [])
            if missing:
                suggestions.append(f"Provide missing physical data: {', '.join(missing[:5])}")

    for w in warnings:
        if w.name == "sub_threshold":
            mats = w.data.get("materials", [])
            for m in mats:
                if "musk" in m.get("role", "").lower():
                    suggestions.append(f"Increase {m['name']} dose — projection musk below threshold")

    data = {
        "failed_gates": len(failed),
        "warnings": len(warnings),
        "suggestions": suggestions,
    }

    if not suggestions:
        return _pass("repair_suggestions", "no repairs needed", suggestions=[])

    return _warn("repair_suggestions", f"{len(suggestions)} suggestions", **data)


# ═════════════════════════════════════════════════════════════════════
# Pipeline Definition — strict ordered stages
# ═════════════════════════════════════════════════════════════════════

STAGES = [
    ("registry_integrity", stage1_registry_integrity),
    ("name_normalization", stage2_name_normalization),
    ("family_resolution", stage3_family_resolution),
    ("build_formula_state", stage4_build_formula_state),
    ("active_percent_check", stage5_active_percent_check),
    ("odt_coverage", stage6_odt_coverage),
    ("oav_computation", stage7_oav_computation),
    ("family_fit", stage8_family_fit),
    ("pyramid_balance", stage9_pyramid_balance),
    ("temporal_simulation", stage10_temporal_simulation),
    ("ifra_safety", stage11_ifra_safety),
    ("robustness", stage12_robustness),
    ("oav_intelligence", stage13_oav_intelligence),
    ("confidence", stage14_confidence),
    ("repair_suggestions", stage15_repair_suggestions),
]

# ── Stages that must pass before we continue (fail-fast checkpoints) ──
# Only fail on data-integrity errors that make physics impossible.
# Structural/gate failures (family_fit, pyramid, IFRA) are NOT fail-fast —
# they get repaired in the repair loop and the pipeline keeps running
# so IFRA, robustness, confidence all get checked in one pass.
FAIL_FAST_STAGES = {
    "registry_integrity",      # Data corruption → stop
    "name_normalization",      # Unknown materials → stop
    "family_resolution",       # Can't resolve brief → stop
    "build_formula_state",     # Physics engine failure → stop
    "odt_coverage",            # Missing ODT → can't compute OAV
}


@dataclass
class PipelineReport:
    formula_name: str
    resolved_family: str | None
    archetype_key: str | None
    stages: list[StageResult]
    overall_status: str
    commercial_readiness: str
    notes: list[str]
    summary: dict


def run_pipeline(ctx: dict) -> PipelineReport:
    stages: list[StageResult] = []
    notes: list[str] = []
    ctx["stage_results"] = stages

    for stage_name, stage_fn in STAGES:
        result = stage_fn(ctx)
        stages.append(result)
        ctx.setdefault("raw_formula", [])
        ctx["stage_results"] = stages

        if result.status == "FAIL" and stage_name in FAIL_FAST_STAGES:
            notes.append(f"Fail-fast at {stage_name}: {result.detail}")
            break

    failed = [s for s in stages if s.status == "FAIL"]
    warned = [s for s in stages if s.status == "WARN"]
    passed = [s for s in stages if s.status == "PASS"]
    skipped = [s for s in stages if s.status == "SKIP"]

    if failed:
        overall_status = "FAIL"
    elif warned:
        overall_status = "WARN"
    elif skipped:
        overall_status = "WARN"
    else:
        overall_status = "PASS"

    state: FormulaState | None = ctx.get("formula_state")
    note_dist = state.note_distribution() if state else {}
    oav_table = ctx.get("oav_table", [])
    temporal_data = ctx.get("temporal_data", [])

    summary = {
        "stages": {"passed": len(passed), "warned": len(warned), "failed": len(failed), "skipped": len(skipped)},
        "materials": state.material_count if state else 0,
        "note_distribution": note_dist,
        "perceptible_count": sum(1 for m in (state.materials if state else []) if (m.oav or 0) >= 1) if state else 0,
        "total_vapor_ppm": round(state.total_vapor_ppm, 2) if state else 0,
        "archetype": ctx.get("archetype_key", ""),
    }

    if temporal_data:
        summary["evaporation_pct"] = temporal_data[-1].get("evaporation_pct", 0)
        if len(temporal_data) > 0 and len(temporal_data) > 1:
            f = temporal_data[0]
            l = temporal_data[-1]
            fv = f.get("total_vapor_ppm", 1)
            lv = l.get("total_vapor_ppm", 0)
            summary["vapor_decay"] = round((1 - lv / max(fv, 0.001)) * 100, 1)

    if oav_table:
        oavs = [r["oav"] for r in oav_table if r["oav"] is not None]
        if oavs:
            summary["oav_max"] = max(oavs)
            summary["oav_min"] = min(oavs)
            summary["oav_median"] = round(statistics.median(oavs), 1) if len(oavs) > 1 else oavs[0]
            if len(oavs) > 1:
                log_oavs = [math.log10(max(v, 0.001)) for v in oavs]
                summary["oav_contrast_sigma_log"] = round(statistics.stdev(log_oavs), 2)

    # Commercial readiness
    if overall_status == "FAIL":
        commercial_readiness = "NOT_RELEASE_READY"
    elif overall_status == "WARN":
        commercial_readiness = "CONDITIONAL_PASS"
    else:
        commercial_readiness = "TECHNICAL_PASS"

    return PipelineReport(
        formula_name=str(ctx.get("formula_name", "unnamed")),
        resolved_family=ctx.get("resolved_family"),
        archetype_key=ctx.get("archetype_key"),
        stages=stages,
        overall_status=overall_status,
        commercial_readiness=commercial_readiness,
        notes=notes,
        summary=summary,
    )


def report_to_dict(report: PipelineReport) -> dict:
    return {
        "formula_name": report.formula_name,
        "resolved_family": report.resolved_family,
        "archetype_key": report.archetype_key,
        "overall_status": report.overall_status,
        "commercial_readiness": report.commercial_readiness,
        "notes": report.notes,
        "summary": report.summary,
        "stages": [
            {
                "name": s.name,
                "status": s.status,
                "detail": s.detail,
                "data": s.data,
            }
            for s in report.stages
        ],
    }


# ═════════════════════════════════════════════════════════════════════
# Repair Loop — auto-apply fixes and re-run until pass or limit
# ═════════════════════════════════════════════════════════════════════

MAX_REPAIR_PASSES = 5


def _find_raw_idx(ctx: dict, name: str) -> int | None:
    """Find index of material in raw_formula by name match."""
    raw = ctx.get("raw_formula", [])
    for i, item in enumerate(raw):
        if normalize_name(item["name"]) == normalize_name(name):
            return i
    return None


def _scale_violators(ctx: dict, violations: list[dict]) -> list[str]:
    """Scale down IFRA violators to their effective limit. Returns list of applied fixes."""
    fixes = []
    for v in violations:
        material = v["material"]
        effective_limit = v["effective_limit"]
        active_pct = v["active_pct_finished"]
        if active_pct <= 0 or effective_limit <= 0:
            continue
        scale = effective_limit / active_pct
        idx = _find_raw_idx(ctx, material)
        if idx is None:
            continue
        item = ctx["raw_formula"][idx]
        old_pct = item["percent"]
        new_pct = round(old_pct * scale * 0.95, 4)  # 5% headroom below limit
        item["percent"] = new_pct
        fixes.append(f"Reduced {material}: {old_pct:.2f}% → {new_pct:.2f}% (IFRA)")
    return fixes


def _add_anchor_materials(ctx: dict, spec: ArchetypeSpec | None, failed_checks: list) -> list[str]:
    """Add missing or boost deficient anchor materials. Returns list of applied fixes."""
    if spec is None:
        return []
    fixes = []

    # Only boost single-material anchor rules (group totals are harder to fix automatically)
    single_mat_anchors: dict[str, float] = {}
    for rule in spec.anchors:
        mats = rule.normalized_materials
        if len(mats) == 1 and rule.minimum is not None:
            single_mat_anchors[next(iter(mats))] = rule.minimum

    # Step 1: boost any existing material that's below its single-material anchor minimum
    for item in ctx.get("raw_formula", []):
        norm = normalize_name(item["name"])
        if norm in single_mat_anchors:
            min_active = single_mat_anchors[norm]
            adjusted_dose = item["percent"] * item.get("dilution", 1.0)
            if adjusted_dose < min_active:
                boost = (min_active / adjusted_dose) * 1.1  # 10% headroom
                item["percent"] = round(item["percent"] * boost, 4)
                fixes.append(f"Boosted {item['name']}: from {adjusted_dose:.3f}% active to {min_active:.3f}% (anchor minimum)")

    # Step 2: add new materials from repair pool (only if not already present)
    if spec.repair_pool:
        for material, pct in spec.repair_pool.items():
            idx = _find_raw_idx(ctx, material)
            if idx is not None:
                continue
            ctx["raw_formula"].append({
                "name": material,
                "percent": pct,
                "dilution": 1.0,
            })
            fixes.append(f"Added {material}: {pct}% (from repair pool)")

    return fixes


def _remove_forbidden_materials(ctx: dict, forbidden_hits: list[str]) -> list[str]:
    """Remove forbidden materials from formula. Returns list of applied fixes."""
    fixes = []
    for material in forbidden_hits:
        idx = _find_raw_idx(ctx, material)
        if idx is not None:
            removed = ctx["raw_formula"].pop(idx)
            fixes.append(f"Removed {removed['name']} (forbidden)")
    return fixes


def _remove_missing_odt(ctx: dict, missing: list[str]) -> list[str]:
    """Remove materials missing ODT data. Returns list of applied fixes."""
    fixes = []
    for material in missing:
        idx = _find_raw_idx(ctx, material)
        if idx is not None:
            removed = ctx["raw_formula"].pop(idx)
            fixes.append(f"Removed {removed['name']} (missing ODT)")
    return fixes


def _rebalance_pyramid(ctx: dict, deviations: dict, spec: ArchetypeSpec | None) -> list[str]:
    """Rough pyramid rebalance: scale down over-represented tier materials."""
    fixes = []
    tier_materials: dict[str, list[dict]] = {"top": [], "heart": [], "base": []}
    for item in ctx.get("raw_formula", []):
        identity = resolve_material(item["name"])
        profile = identity.profile
        note = getattr(profile, "note", None) or "heart"
        if note in tier_materials:
            tier_materials[note].append(item)

    for tier, dev in deviations.items():
        delta = dev.get("delta", 0)
        if delta > 10 and tier_materials.get(tier):
            scale = 1.0 - (delta / 100.0) * 0.5  # reduce by half the excess
            if scale < 0.5:
                scale = 0.5
            for item in tier_materials[tier]:
                old_pct = item["percent"]
                new_pct = round(old_pct * scale, 4)
                item["percent"] = new_pct
                fixes.append(f"Reduced {item['name']}: {old_pct:.2f}% → {new_pct:.2f}% (pyramid {tier} too high)")
        elif delta < -10:
            # Try adding from repair pool or boost what exists
            if spec and spec.repair_pool and tier == "heart":
                for mat, pct in spec.repair_pool.items():
                    idx = _find_raw_idx(ctx, mat)
                    if idx is None and pct > 0:
                        ctx["raw_formula"].append({"name": mat, "percent": pct * 2, "dilution": 1.0})
                        fixes.append(f"Added {mat}: {pct * 2}% (reinforce {tier})")
                        break
    return fixes


def _apply_repairs(ctx: dict, report: PipelineReport) -> list[str]:
    """Apply all available repairs to ctx['raw_formula']. Returns list of fix descriptions."""
    all_fixes: list[str] = []
    stage_map: dict[str, StageResult] = {s.name: s for s in report.stages}

    # 1. IFRA violations — scale down to limit
    ifra = stage_map.get("ifra_safety")
    if ifra and ifra.status == "FAIL":
        violations = ifra.data.get("violation_details", [])
        all_fixes.extend(_scale_violators(ctx, violations))

    spec: ArchetypeSpec | None = ctx.get("archetype_spec")

    # 2. Family fit — add anchors, remove forbidden
    family = stage_map.get("family_fit")
    if family and family.status == "FAIL":
        checks = family.data.get("checks", [])
        failed_checks = [c for c in checks if c.get("status") == "FAIL"] if checks else []
        forbidden = family.data.get("forbidden_hits", [])
        all_fixes.extend(_add_anchor_materials(ctx, spec, failed_checks))
        all_fixes.extend(_remove_forbidden_materials(ctx, forbidden))

    # 3. Missing ODT — remove materials
    odt = stage_map.get("odt_coverage")
    if odt and odt.status == "FAIL":
        missing = odt.data.get("missing", [])
        all_fixes.extend(_remove_missing_odt(ctx, missing))

    # 4. Pyramid balance — rebalance
    pyramid = stage_map.get("pyramid_balance")
    if pyramid and pyramid.status in ("FAIL", "WARN"):
        deviations = pyramid.data.get("deviations", {})
        all_fixes.extend(_rebalance_pyramid(ctx, deviations, spec))

    return all_fixes


@dataclass
class RepairRun:
    pass_index: int
    report: PipelineReport
    fixes_applied: list[str]


def repair_until_pass(ctx: dict, max_passes: int = MAX_REPAIR_PASSES) -> tuple[PipelineReport, list[RepairRun]]:
    """Run pipeline, apply fixes, re-run until PASS or max_passes exhausted."""
    runs: list[RepairRun] = []
    last_fix_count = -1

    for pass_idx in range(1, max_passes + 1):
        # Clear cached state so stages recompute
        ctx.pop("stage_results", None)
        ctx.pop("formula_state", None)
        ctx.pop("oav_table", None)
        ctx.pop("temporal_frames", None)
        ctx.pop("temporal_data", None)
        ctx.pop("ingredients_ul", None)
        ctx.pop("dilutions", None)
        ctx.pop("resolved_formula", None)

        report = run_pipeline(ctx)
        runs.append(RepairRun(pass_index=pass_idx, report=report, fixes_applied=[]))

        if report.overall_status != "FAIL":
            return report, runs

        fixes = _apply_repairs(ctx, report)
        runs[-1].fixes_applied = fixes

        if not fixes:
            # No more automated repairs possible — keep last result as final
            # This is not an error; remaining failures need perfumer judgment
            return report, runs

        # Track progress: if same number of fixes on consecutive passes,
        # we're cycling and should stop
        current_fix_count = len(fixes)
        if current_fix_count == last_fix_count:
            # Same fixes applied twice — give up to avoid infinite loop
            return report, runs
        last_fix_count = current_fix_count

    # Max passes exhausted — return last result
    return report, runs


# ═════════════════════════════════════════════════════════════════════
# Test Fixtures — 5 major families
# ═════════════════════════════════════════════════════════════════════

TEST_FORMULAS: dict[str, dict] = {
    "woody_vetiver": {
        "formula_name": "Vetiver Classique 30mL EdP",
        "brief": "vetiver_woody",
        "expected_concentrate_ul": 6000.0,
        "batch_volume_ml": 30.0,
        "temperature_K": 305.0,
        "concentration_bracket": "EdP",
        "raw_formula": [
            {"name": "Vetiver EO", "percent": 15.0, "dilution": 1.0},
            {"name": "Bergamot FCF oil Sicilian", "percent": 10.0, "dilution": 1.0},
            {"name": "Cedrat FCF oil Sicilian", "percent": 5.0, "dilution": 1.0},
            {"name": "Iso E Super", "percent": 18.0, "dilution": 1.0},
            {"name": "Cedarwood oil Virginia", "percent": 8.0, "dilution": 1.0},
            {"name": "Vetival", "percent": 2.0, "dilution": 1.0},
            {"name": "Evernyl", "percent": 0.5, "dilution": 1.0},
            {"name": "Coumarin", "percent": 1.0, "dilution": 1.0},
            {"name": "Patchouli EO", "percent": 4.0, "dilution": 1.0},
            {"name": "Ambrox Super", "percent": 3.0, "dilution": 1.0},
            {"name": "Habanolide", "percent": 8.0, "dilution": 1.0},
            {"name": "Linalool", "percent": 4.0, "dilution": 1.0},
            {"name": "Hedione", "percent": 12.0, "dilution": 1.0},
            {"name": "Black Pepper EO", "percent": 1.5, "dilution": 0.01},
            {"name": "Javanol", "percent": 0.5, "dilution": 0.01},
        ],
    },
    "chypre": {
        "formula_name": "Chypre Vert 30mL EdP",
        "brief": "generic",
        "family_archetype": "aromatic_fougere.classic_reference",
        "expected_concentrate_ul": 6000.0,
        "batch_volume_ml": 30.0,
        "temperature_K": 305.0,
        "concentration_bracket": "EdP",
        "raw_formula": [
            {"name": "Bergamot FCF oil Sicilian", "percent": 15.0, "dilution": 1.0},
            {"name": "Cedrat FCF oil Sicilian", "percent": 5.0, "dilution": 1.0},
            {"name": "Lemon FCF oil Sicilian", "percent": 5.0, "dilution": 1.0},
            {"name": "Iso E Super", "percent": 15.0, "dilution": 1.0},
            {"name": "Patchouli EO", "percent": 8.0, "dilution": 1.0},
            {"name": "Evernyl", "percent": 1.5, "dilution": 1.0},
            {"name": "Labdanum Absolute", "percent": 2.0, "dilution": 0.5},
            {"name": "Vetiver EO", "percent": 4.0, "dilution": 1.0},
            {"name": "Galbanum Resinoid", "percent": 0.5, "dilution": 0.1},
            {"name": "Jasmine Absolute", "percent": 4.0, "dilution": 1.0},
            {"name": "Rose Absolute", "percent": 3.0, "dilution": 1.0},
            {"name": "Ambrox Super", "percent": 2.0, "dilution": 1.0},
            {"name": "Habanolide", "percent": 10.0, "dilution": 1.0},
            {"name": "Hedione", "percent": 15.0, "dilution": 1.0},
            {"name": "Linalool", "percent": 3.0, "dilution": 1.0},
            {"name": "Coumarin", "percent": 0.5, "dilution": 1.0},
            {"name": "Cedarwood oil Virginia", "percent": 6.0, "dilution": 1.0},
        ],
    },
    "oriental": {
        "formula_name": "Ambre Oriental 30mL EdP",
        "brief": "generic",
        "family_archetype": "layton_dna.indoor_amber",
        "expected_concentrate_ul": 6000.0,
        "batch_volume_ml": 30.0,
        "temperature_K": 305.0,
        "concentration_bracket": "EdP",
        "raw_formula": [
            {"name": "Bergamot FCF oil Sicilian", "percent": 8.0, "dilution": 1.0},
            {"name": "Red Mandarin EO", "percent": 5.0, "dilution": 1.0},
            {"name": "Cardamom EO", "percent": 2.0, "dilution": 1.0},
            {"name": "Benzoin Sumatra Resinoid", "percent": 4.0, "dilution": 1.0},
            {"name": "Labdanum Absolute", "percent": 3.0, "dilution": 0.5},
            {"name": "Vanillin", "percent": 6.0, "dilution": 1.0},
            {"name": "Iso E Super", "percent": 15.0, "dilution": 1.0},
            {"name": "Ambrox Super", "percent": 5.0, "dilution": 1.0},
            {"name": "Cashmeran", "percent": 2.0, "dilution": 1.0},
            {"name": "Habanolide", "percent": 10.0, "dilution": 1.0},
            {"name": "Ethylene Brassylate", "percent": 8.0, "dilution": 1.0},
            {"name": "Hedione", "percent": 15.0, "dilution": 1.0},
            {"name": "Sandalore", "percent": 5.0, "dilution": 1.0},
            {"name": "Coumarin", "percent": 1.5, "dilution": 1.0},
            {"name": "Eugenol", "percent": 0.5, "dilution": 1.0},
            {"name": "Javanol", "percent": 0.5, "dilution": 0.01},
        ],
    },
    "citrus": {
        "formula_name": "Citrus Sport 30mL EdP",
        "brief": "generic",
        "family_archetype": "aromatic_fougere.modern_mineral",
        "expected_concentrate_ul": 6000.0,
        "batch_volume_ml": 30.0,
        "temperature_K": 305.0,
        "concentration_bracket": "EdP",
        "raw_formula": [
            {"name": "Bergamot FCF oil Sicilian", "percent": 18.0, "dilution": 1.0},
            {"name": "Cedrat FCF oil Sicilian", "percent": 8.0, "dilution": 1.0},
            {"name": "Lemon FCF oil Sicilian", "percent": 8.0, "dilution": 1.0},
            {"name": "Grapefruit FCF", "percent": 6.0, "dilution": 1.0},
            {"name": "Lime Distilled EO", "percent": 4.0, "dilution": 1.0},
            {"name": "Dihydromyrcenol", "percent": 5.0, "dilution": 1.0},
            {"name": "Hedione", "percent": 15.0, "dilution": 1.0},
            {"name": "Iso E Super", "percent": 10.0, "dilution": 1.0},
            {"name": "Habanolide", "percent": 8.0, "dilution": 1.0},
            {"name": "Linalool", "percent": 5.0, "dilution": 1.0},
            {"name": "Linalyl Acetate", "percent": 3.0, "dilution": 1.0},
            {"name": "Coumarin", "percent": 0.5, "dilution": 1.0},
            {"name": "Calone", "percent": 0.3, "dilution": 0.01},
            {"name": "Floralozone", "percent": 0.5, "dilution": 0.01},
            {"name": "Ambrox Super", "percent": 2.0, "dilution": 1.0},
        ],
    },
    "green": {
        "formula_name": "Green Galbanum 30mL EdP",
        "brief": "generic",
        "family_archetype": "aromatic_fougere.classic_reference",
        "expected_concentrate_ul": 6000.0,
        "batch_volume_ml": 30.0,
        "temperature_K": 305.0,
        "concentration_bracket": "EdP",
        "raw_formula": [
            {"name": "Bergamot FCF oil Sicilian", "percent": 10.0, "dilution": 1.0},
            {"name": "Galbanum Resinoid", "percent": 2.0, "dilution": 0.1},
            {"name": "Cis-3-Hexenol", "percent": 0.5, "dilution": 0.01},
            {"name": "Violet Leaf Absolute", "percent": 1.0, "dilution": 0.1},
            {"name": "Hedione", "percent": 15.0, "dilution": 1.0},
            {"name": "Iso E Super", "percent": 15.0, "dilution": 1.0},
            {"name": "Vetiver EO", "percent": 6.0, "dilution": 1.0},
            {"name": "Patchouli EO", "percent": 5.0, "dilution": 1.0},
            {"name": "Evernyl", "percent": 1.0, "dilution": 1.0},
            {"name": "Habanolide", "percent": 10.0, "dilution": 1.0},
            {"name": "Linalool", "percent": 5.0, "dilution": 1.0},
            {"name": "Petitgrain EO", "percent": 3.0, "dilution": 1.0},
            {"name": "Coumarin", "percent": 1.0, "dilution": 1.0},
            {"name": "Cedarwood oil Virginia", "percent": 6.0, "dilution": 1.0},
            {"name": "Ambrox Super", "percent": 2.0, "dilution": 1.0},
            {"name": "Florol", "percent": 4.0, "dilution": 1.0},
            {"name": "Parmavert", "percent": 0.5, "dilution": 0.01},
        ],
    },
}

# ═════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═════════════════════════════════════════════════════════════════════

import argparse


def _parse_formula_file(path: str) -> dict:
    """Parse a simple JSON formula definition file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Formula file not found: {path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    required = {"formula_name", "brief", "raw_formula"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"Formula file missing fields: {missing}")
    return data


def _build_ctx_from_args(args: argparse.Namespace) -> dict:
    if args.file:
        return _parse_formula_file(args.file)

    ctx: dict = {
        "formula_name": args.name or "unnamed",
        "brief": args.brief,
        "expected_concentrate_ul": args.concentrate_ul,
        "batch_volume_ml": args.batch_ml,
        "temperature_K": args.temperature,
        "concentration_bracket": args.bracket,
        "ifra_headroom": args.ifra_headroom,
    }
    if args.family:
        ctx["family_archetype"] = args.family
    if args.formula:
        raw = []
        for item in args.formula:
            parts = item.split(",")
            if len(parts) >= 2:
                name = parts[0].strip()
                pct = float(parts[1].strip())
                dil = float(parts[2].strip()) if len(parts) >= 3 else 1.0
                raw.append({"name": name, "percent": pct, "dilution": dil})
        ctx["raw_formula"] = raw
    return ctx


def _register_cli(subparsers, name: str, help_text: str, formula_key: str):
    """Register one CLI subcommand that runs a specific test formula."""
    p = subparsers.add_parser(name, help=help_text)
    p.set_defaults(test_key=formula_key, use_test=True)


def _print_cli_help(parser: argparse.ArgumentParser):
    print()
    parser.print_help()
    print()
    print("Built-in test formulas:")
    for key, ctx in TEST_FORMULAS.items():
        print(f"  {key:25s}  {ctx['formula_name']}")
    print()
    print("Examples:")
    print('  python run_pipeline.py test woody_vetiver')
    print('  python run_pipeline.py --brief vetiver_woody --name "My Vetiver" --formula "Bergamot FCF,10" "Vetiver EO,5"')
    print('  python run_pipeline.py --file my_formula.json')
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Perfume Pipeline Orchestrator — validate formulas end-to-end",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = parser.add_subparsers(dest="command", help="Sub-commands")

    test_p = sub.add_parser("test", help="Run a built-in test formula")
    test_p.add_argument("test_name", nargs="?", default="", help="Test formula key (see list below)")
    test_p.add_argument("--repair", "-r", action="store_true", help="Auto-repair and re-run until pass or limit")
    test_p.add_argument("--analyze", "-a", action="store_true", help="Print full formatted perfumer analysis")

    run_p = sub.add_parser("run", help="Run pipeline on inline or file-based formula")
    run_p.add_argument("--file", "-f", type=str, default="", help="Path to JSON formula file")
    run_p.add_argument("--brief", type=str, default="generic", help="Fragrance brief key")
    run_p.add_argument("--family", type=str, default="", help="Family archetype key (overrides brief default)")
    run_p.add_argument("--name", type=str, default="", help="Formula name")
    run_p.add_argument("--formula", "-i", type=str, nargs="+", default=[], help="Ingredient: 'Name,percent,dilution'")
    run_p.add_argument("--concentrate-ul", type=float, default=DEFAULT_CONCENTRATE_UL, help="Concentrate volume in µL")
    run_p.add_argument("--batch-ml", type=float, default=30.0, help="Batch volume in mL")
    run_p.add_argument("--temperature", type=float, default=305.0, help="Temperature in Kelvin")
    run_p.add_argument("--bracket", type=str, default="EdP", help="Concentration bracket")
    run_p.add_argument("--ifra-headroom", type=float, default=1.0, help="IFRA limit multiplier")
    run_p.add_argument("--json", "-j", action="store_true", help="Output raw JSON instead of formatted report")
    run_p.add_argument("--repair", "-r", action="store_true", help="Auto-repair and re-run until pass or limit")
    run_p.add_argument("--analyze", "-a", action="store_true", help="Print full formatted perfumer analysis (like format_pipeline_analysis.py)")

    if len(sys.argv) <= 1:
        _print_cli_help(parser)
        return 1

    args = parser.parse_args()

    if args.command == "test":
        if args.test_name and args.test_name in TEST_FORMULAS:
            ctx = dict(TEST_FORMULAS[args.test_name])
        elif not args.test_name:
            print("Running all test formulas...\n")
            results: dict[str, dict] = {}
            for key, ctx in TEST_FORMULAS.items():
                report = run_pipeline(dict(ctx))
                results[key] = report_to_dict(report)
            print(json.dumps(results, indent=2, ensure_ascii=False))
            return 0
        else:
            print(f"Unknown test formula: {args.test_name}")
            print(f"Available: {list(TEST_FORMULAS.keys())}")
            return 1

        if args.repair:
            final_report, runs = repair_until_pass(ctx)
            result = report_to_dict(final_report)
            result["repair_runs"] = [
                {"pass": r.pass_index, "fixes": r.fixes_applied, "status": r.report.overall_status}
                for r in runs
            ]
            print(f"Repair mode — auto-fixing {args.test_name}...\n")
            _print_repair_log(runs)
        else:
            report = run_pipeline(ctx)
            result = report_to_dict(report)

        if args.analyze:
            _print_analysis(result)
        else:
            _print_formatted(result)
        return 0

    if args.command == "run":
        ctx = _build_ctx_from_args(args)
        if not ctx.get("raw_formula"):
            print("No formula provided. Use --formula or --file.")
            return 1

        if args.repair:
            final_report, runs = repair_until_pass(ctx)
            result = report_to_dict(final_report)
            result["repair_runs"] = [
                {"pass": r.pass_index, "fixes": r.fixes_applied, "status": r.report.overall_status}
                for r in runs
            ]
            if args.json:
                pass  # will print JSON below
            else:
                print("Repair mode — auto-fixing...\n")
                _print_repair_log(runs)
        else:
            report = run_pipeline(ctx)
            result = report_to_dict(report)

        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif args.analyze:
            _print_analysis(result)
        else:
            _print_formatted(result)
        return 0

    _print_cli_help(parser)
    return 1


def _print_repair_log(runs: list):
    """Print the repair-and-rerun log."""
    print()
    print("=" * 70)
    print("  REPAIR LOG")
    print("=" * 70)
    for run in runs:
        status = run.report.overall_status
        icon = "\u2705" if status == "PASS" else "\u26a0" if status == "WARN" else "\u2716"
        print(f"  Pass #{run.pass_index}: {icon} {status}")
        for fix in run.fixes_applied:
            print(f"    \u279c {fix}")
    print()


def _print_analysis(result: dict):
    """Print full formatted analysis directly from orchestrator data."""
    import math, statistics
    stage_map = {st["name"]: st for st in result.get("stages", [])}
    s = result.get("summary", {})
    oav_stage = stage_map.get("oav_computation", {})
    mats = oav_stage.get("data", {}).get("oav_table", [])
    mats_sorted = sorted(mats, key=lambda m: float(m.get("oav", 0) or 0), reverse=True)
    temporal_stage = stage_map.get("temporal_simulation", {})
    windows = temporal_stage.get("data", {}).get("windows", [])
    failed = [st for st in result["stages"] if st["status"] == "FAIL"]
    warned = [st for st in result["stages"] if st["status"] == "WARN"]
    passed = [st for st in result["stages"] if st["status"] == "PASS"]

    def _ol(oav):
        if oav >= 10000: return "massive"
        if oav >= 1000: return "very strong"
        if oav >= 100: return "strong"
        if oav >= 50: return "moderate-strong"
        if oav >= 10: return "moderate"
        if oav >= 5: return "perceptible"
        if oav >= 1: return "at threshold"
        return "sub-threshold"

    print("## Gate Summary")
    print()
    print(f"**{len(passed)} PASS / **{len(warned)} WARN / **{len(failed)} FAIL**")
    print()
    for g in failed:
        print(f"  FAIL {g['name']}: {g['detail'][:140]}")
    for g in warned:
        print(f"  WARN {g['name']}: {g['detail'][:140]}")
    print()

    print("## Headspace OAV \u2014 Opening (0s)")
    print()
    h = " | ".join(["#", "Material", "OAV", "Note", "Percept", "VP Pa", "Vapor ppm", "ODT ppm", "Act g", "MF%", "Role"])
    print(f"| {h} |")
    print("|" + "|".join(["-" * 10] * 11) + "|")
    total_ppm = 0
    for i, m in enumerate(mats_sorted, 1):
        oav = m.get("oav", 0) or 0
        label = _ol(oav)
        role = str(m.get("canonical", "") or "")[:30]
        vp = m.get("vp_pa", 0) or 0
        vap = m.get("vapor_ppm", 0) or 0
        odt = m.get("odt_air_ppm", 0) or 0
        ag = m.get("active_ul", 0) * 0.001 or 0
        mf = m.get("mole_fraction", 0) * 100 or 0
        note = str(m.get('note', '?')) or '?'
        name = str(m.get('name', ''))[:28] or '?'
        print(f"| {i:3d} | {name:28s} | {oav:>10.1f} | {note:5s} | {label:>12s} | {vp:>7.3f} | {vap:>9.4f} | {odt:>9.6f} | {ag:>7.4f} | {mf:>5.2f} | {role:30s}")
        total_ppm += vap
    print()
    ntop = sum(1 for m in mats_sorted if m.get("note") == "top")
    nheart = sum(1 for m in mats_sorted if m.get("note") == "heart")
    nbase = sum(1 for m in mats_sorted if m.get("note") == "base")
    print(f"**Materials:** {len(mats_sorted)} total ({ntop} top, {nheart} heart, {nbase} base)")
    print(f"**Total vapor:** {total_ppm:.2f} ppm")
    print()

    nd = s.get("note_distribution", {})
    print("### Note Distribution")
    print()
    total_act = sum(m.get("active_ul", 0) or 0 for m in mats_sorted) or 1
    total_oav = sum(m.get("oav", 0) or 0 for m in mats_sorted) or 1
    for tier_name in ("TOP", "HEART", "BASE"):
        tier = [m for m in mats_sorted if m.get("note") == tier_name.lower()]
        act_pct = sum(m.get("active_ul", 0) or 0 for m in tier) / total_act * 100
        oav_pct = sum(m.get("oav", 0) or 0 for m in tier) / total_oav * 100
        print(f"**{tier_name}:** {len(tier)} mats, {act_pct:.1f}% active, {oav_pct:.1f}% OAV")
        for mm in tier[:6]:
            o = mm.get("oav", 0) or 0
            print(f"  - {mm['name']:28s} OAV={o:>8.1f} ({_ol(o)}) VP={mm.get('vp_pa',0):.3f}Pa")
        if len(tier) > 6:
            print(f"  ... and {len(tier)-6} more")
    print()

    # Odor family distribution
    print("### OAV by Odor Family")
    print()
    fams = {}
    for m in mats_sorted:
        f = str(m.get("family", "?")) if m.get("family") is not None else "?"
        oav = m.get("oav", 0) or 0
        if f not in fams:
            fams[f] = {"oav": 0, "names": []}
        fams[f]["oav"] += oav
        fams[f]["names"].append(m["name"])
    total_fam = sum(v["oav"] for v in fams.values()) or 1
    for f, d in sorted(fams.items(), key=lambda x: x[1]["oav"], reverse=True):
        pct = d["oav"] / total_fam * 100
        bar = "=" * max(1, int(pct / 2))
        label = str(f) if f is not None else "?"
        print(f"  {label:>15s} {pct:5.1f}% {bar}  ({len(d['names'])} mats)")
    print()

    # Sub-threshold
    sub = [m for m in mats_sorted if (m.get("oav", 0) or 0) < 1]
    high = [m for m in mats_sorted if (m.get("oav", 0) or 0) > 5000]
    if sub:
        print("### Sub-threshold Materials (OAV < 1)")
        print(f"{len(sub)}/{len(mats_sorted)} materials below perceptible threshold")
        for m in sub:
            oav = m.get("oav", 0) or 0
            vp = m.get("vp_pa", 0) or 0
            act = m.get("active_ul", 0) or 0
            flag = "**Needs higher dose**" if "musk" in (str(m.get("canonical", "")) + str(m.get("name", ""))).lower() else "Structural (acceptable)"
            print(f"  - {m['name']}: OAV={oav:.2f} VP={vp:.3f}Pa act={act:.0f}uL [{flag}]")
    if high:
        print("### High-OAV Flags (>5000)")
        for m in high:
            oav = m.get("oav", 0) or 0
            print(f"  - {m['name']} OAV={oav:.0f} dominates headspace \u2014 may mask subtler notes")
    print()

    # Temporal
    if windows:
        print("## Temporal Evolution (5 Windows)")
        print()
        f_ul = windows[0].get("total_active_ul", 1)
        h = " | ".join(["Window", "Time", "T/H/B", "Vapor", "Raw uL", "Leaders"])
        print(f"| {h} |")
        print("|" + "|".join(["-" * 12] * 6) + "|")
        for w in windows:
            wn = w.get("note_distribution", {})
            dom = w.get("dominant_oav", [])
            ldrs = ", ".join(f"{d['material'][:12]}({d['oav']:.0f})" for d in dom[:3])
            evap = 100 * (1 - w.get("total_active_ul", 0) / f_ul)
            print(f"| {w['label'][:12]:12s} | {w['t_seconds']:>6.0f}s | {wn.get('top',0):>4.1f}/{wn.get('heart',0):>3.1f}/{wn.get('base',0):>4.1f} | {w.get('total_vapor_ppm',0):>6.2f}ppm | {w.get('total_active_ul',0):>6.0f} | {ldrs:>40s}")
        print()
        print("### Per-Window Detail")
        for w in windows:
            wn = w.get("note_distribution", {})
            dom = w.get("dominant_oav", [])
            evap = 100 * (1 - w.get("total_active_ul", 0) / f_ul)
            print()
            print(f"**{w['label'].upper()}** ({w['t_seconds']}s) \u2014 Evap:{evap:.0f}%")
            print(f"  T:{wn.get('top',0):.1f}% H:{wn.get('heart',0):.1f}% B:{wn.get('base',0):.1f}%  Vapor:{w.get('total_vapor_ppm',0):.2f}ppm")
            if dom:
                print("  Leaders: " + " | ".join(f"{d['material']} OAV {d['oav']:.0f}" for d in dom[:5]))
        print()

    # Perfumer assessment
    print("## Perfumer\u2019s Assessment")
    print()
    top_m = [m for m in mats_sorted if m.get("note") == "top"]
    heart_m = [m for m in mats_sorted if m.get("note") == "heart"]
    base_m = [m for m in mats_sorted if m.get("note") == "base"]

    print("### 1. Character")
    tdesc = " + ".join(f"{m['name']}({_ol(m.get('oav',0))})" for m in top_m[:3])
    hdesc = " + ".join(f"{m['name']}({_ol(m.get('oav',0))})" for m in heart_m[:2]) or "(thin)"
    bdesc = " + ".join(f"{m['name']}({_ol(m.get('oav',0))})" for m in base_m[:5])
    print(f"  Top: {tdesc}")
    print(f"  Heart: {hdesc}")
    print(f"  Base: {bdesc}")
    print()

    print("### 2. Opening (0-5min)")
    total_vapor = sum(m.get("vapor_ppm", 0) or 0 for m in mats_sorted)
    if top_m:
        lead = top_m[0]
        print(f"  {lead['name']} dominates at OAV {lead.get('oav',0):.0f} ({_ol(lead.get('oav',0))}).")
        for m in top_m[:4]:
            o = m.get("oav", 0) or 0
            print(f"  - {m['name']} OAV={o:.0f} VP={m.get('vp_pa',0):.1f}Pa ({m.get('family','?')})")
    print(f"  Total vapor: {total_vapor:.1f} ppm")
    print()

    print("### 3. Heart (30min-2hr)")
    if windows and len(windows) >= 3:
        hw = windows[2]
        hm = [(m, m.get("oav", 0) or 0) for m in mats_sorted if (m.get("oav", 0) or 0) >= 1]
        hnd = hw.get("note_distribution", {})
        for m, o in hm[:4]:
            print(f"  {m['name']} OAV={o:.0f} ({_ol(o)})")
        print(f"  T:{hnd.get('top',0):.1f}% H:{hnd.get('heart',0):.1f}% B:{hnd.get('base',0):.1f}%")
        print(f"  Vapor: {hw.get('total_vapor_ppm',0):.1f} ppm")
    print()

    print("### 4. Drydown (2hr-4hr+)")
    if windows and len(windows) >= 5:
        dw = windows[-1]
        dnd = dw.get("note_distribution", {})
        dm = [m for m in mats_sorted if (m.get("oav", 0) or 0) >= 1]
        print(f"  Base dominates at {dnd.get('base',0):.0f}% of headspace")
        for m in dm[:6]:
            o = m.get("oav", 0) or 0
            if o >= 1:
                print(f"  - {m['name']} OAV={o:.0f}")
        print(f"  Vapor: {dw.get('total_vapor_ppm',0):.1f} ppm")
    print()

    print("### 5. Sillage & Diffusion")
    carriers = [m for m in mats_sorted if (m.get("oav", 0) or 0) > 500]
    if carriers:
        cstr = " + ".join(f"{m['name']}({m['oav']:.0f})" for m in carriers[:4])
        print(f"  Primary carriers: {cstr}")
    fams2 = {}
    for m in mats_sorted:
        f = m.get("family", "?")
        oav = m.get("oav", 0) or 0
        fams2[f] = fams2.get(f, 0) + oav
    tot2 = sum(fams2.values()) or 1
    print("  OAV by family: " + " ".join(f"{f}{v/tot2*100:.0f}%" for f, v in sorted(fams2.items(), key=lambda x: x[1], reverse=True)[:4]))
    print()

    print("### 6. Longevity")
    if windows:
        fw = windows[0]
        lw = windows[-1]
        evap = 100 * (1 - lw.get("total_active_ul", 0) / max(fw.get("total_active_ul", 1), 0.001))
        persist = lw.get("note_distribution", {}).get("base", 0)
        print(f"  Evaporation: {evap:.0f}% over 4h")
        print(f"  Vapor: {fw.get('total_vapor_ppm',0):.1f} > {lw.get('total_vapor_ppm',0):.1f} ppm")
        print(f"  Base @ drydown: {persist:.0f}%")
        print(f"  Est. skin life: 6-8h moderate + 2-4h skin scent")
    print()

    print("### 7. Balance")
    oavs = [(m.get("oav", 0) or 0.001) for m in mats_sorted if (m.get("oav", 0) or 0) > 0]
    mx = max(oavs) if oavs else 0
    mn = min(oavs) if oavs else 0
    ct = statistics.stdev([math.log10(v) for v in oavs]) if len(oavs) > 1 else 0
    print(f"  Pyramid: T:{nd.get('top',0):.1f}% H:{nd.get('heart',0):.1f}% B:{nd.get('base',0):.1f}%")
    print(f"  OAV range: {mn:.2f} to {mx:.0f} (sigma-log={ct:.2f})")
    if ct > 1.2:
        print(f"  Wide contrast: citrus (OAV {mx:.0f}) dominates opening before burning off to reveal base.")
    if (nd.get('heart', 0) or 0) < 10:
        print(f"  Thin heart ({nd.get('heart',0):.1f}%) \u2014 top-to-base architecture, authentic for vetiver.")
    for label in ["massive", "very strong", "strong", "moderate-strong", "moderate", "perceptible", "at threshold", "sub-threshold"]:
        if label == "sub-threshold":
            cnt = sum(1 for o in oavs if o < 1)
        else:
            thresholds = [(10000, "massive"), (1000, "very strong"), (100, "strong"), (50, "moderate-strong"), (10, "moderate"), (5, "perceptible"), (1, "at threshold"), (0, "sub-threshold")]
            idx = next((i for i, (t, l) in enumerate(thresholds) if l == label), -1)
            if idx >= 0:
                lo = thresholds[idx][0]
                hi = thresholds[idx-1][0] if idx > 0 else 99999999
                cnt = sum(1 for o in oavs if lo <= o < hi)
        if cnt:
            print(f"    {label}: {cnt}")
    print()

    print("### 8. Flags")
    for m in mats_sorted:
        oav = m.get("oav", 0) or 0
        if oav < 1:
            role = m.get("canonical", "")[:20]
            print(f"  SUB: {m['name']} OAV={oav:.2f} role={role}")
    for m in mats_sorted:
        if "hedione" in m["name"].lower():
            odt = m.get("odt_air_ppm", 0)
            if odt >= 0.01:
                print(f"  NOTE: Hedione HC ODT={odt*1000:.1f}ppb (alias collision: pure hedione ODT=0.05ppb, OAV would be 400x higher)")
    for m in mats_sorted:
        if "evernyl" in m["name"].lower():
            pct = m.get("active_ul", 0) / sum(x.get("active_ul", 0) for x in mats_sorted) * 100 if sum(x.get("active_ul", 0) for x in mats_sorted) else 0
            if pct > 0.5:
                print(f"  IFRA: Evernyl at {pct:.2f}% active \u2014 check Cat4 limit (0.1% in product = 0.5% at 20% EdP)")
    print()


def _print_formatted(result: dict):
    """Print a readable summary of one pipeline result."""
    s = result["summary"]
    stages = result["stages"]
    fails = [st for st in stages if st["status"] == "FAIL"]
    warns = [st for st in stages if st["status"] == "WARN"]
    passes = [st for st in stages if st["status"] == "PASS"]

    bar = "=" * 70
    print(bar)
    print(f"  {result['formula_name']}")
    print(f"  Status: {result['overall_status']}  |  Readiness: {result['commercial_readiness']}")
    print(f"  Family: {result['resolved_family']}  |  Archetype: {result['archetype_key']}")
    print(bar)
    print(f"  Materials: {s['materials']}  |  Perceptible: {s['perceptible_count']}")
    print(f"  Vapor: {s['total_vapor_ppm']} ppm  |  T/H/B: {s.get('note_distribution',{}).get('top','?')}/{s.get('note_distribution',{}).get('heart','?')}/{s.get('note_distribution',{}).get('base','?')}")
    if "oav_contrast_sigma_log" in s:
        print(f"  OAV contrast: {s['oav_contrast_sigma_log']} (sigma-log)")
    print(f"  Stages: {len(passes)} PASS, {len(warns)} WARN, {len(fails)} FAIL")

    for f in fails:
        print(f"    \u2716 FAIL [{f['name']}]: {f['detail'][:140]}")
    for w in warns:
        print(f"    \u26a0 WARN [{w['name']}]: {w['detail'][:140]}")

    # Show repair suggestions if available
    repair = [st for st in stages if st["name"] == "repair_suggestions"]
    if repair:
        suggestions = repair[0].get("data", {}).get("suggestions", []) if isinstance(repair[0], dict) else getattr(repair[0], "data", {}).get("suggestions", [])
        if suggestions:
            print(f"\n  \u2192 Repair suggestions:")
            for s_ in suggestions:
                print(f"    - {s_}")
    print()


if __name__ == "__main__":
    sys.exit(main())
