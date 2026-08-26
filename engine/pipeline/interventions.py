"""Canonical intervention contract for release and optimizer outputs.

This module centralizes post-analysis diagnosis and recommendation generation so
the canonical release CLI and gate-aware optimizer expose one shared structure.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from engine.formula_recommendations import generate_intervention_recommendations
from engine.intervention_context import InterventionContext
from engine.optimizer.models import FormulaVector

SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def _build_formula_vector(formula: Mapping[str, Any], dilutions: Mapping[str, float]) -> FormulaVector:
    total_ul = sum(float(v or 0.0) for v in formula.get("ingredients_ul", {}).values()) or 1.0
    pct_ings: dict[str, float] = {}
    for name, ul in (formula.get("ingredients_ul", {}) or {}).items():
        dil = float(dilutions.get(name, 1.0) or 1.0)
        pct_ings[str(name)] = (float(ul or 0.0) * dil / total_ul) * 100.0
    return FormulaVector(ingredients=pct_ings, dilutions=dict(dilutions))


def diagnose_industry(inds: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    ten = float(inds.get("tenacity", 50) or 0.0)
    if ten < 15:
        issues.append({
            "severity": "CRITICAL", "axis": "tenacity",
            "message": f"Base perceptibility critically low ({ten:.0f}/100)",
            "detail": "Base+heart OAV <15% of total — the formula has almost no perceptible foundation",
            "suggestion": "Boost heart materials or replace dormant base materials with perceptible fixatives.",
        })
    elif ten < 30:
        issues.append({
            "severity": "HIGH", "axis": "tenacity",
            "message": f"Base perceptibility low ({ten:.0f}/100)",
            "detail": "Base+heart OAV <30% — the formula will fade quickly after top notes evaporate",
            "suggestion": "Increase heart-note dosage or add a perceptible fixative.",
        })

    lift = float(inds.get("lift", 50) or 0.0)
    if lift > 85:
        issues.append({
            "severity": "CRITICAL", "axis": "lift",
            "message": f"Top notes dominate ({lift:.0f}% of total OAV)",
            "detail": "Over 85% of perceptible OAV comes from top notes — the formula is top-heavy",
            "suggestion": "Reduce the highest-OAV top material and redistribute to heart/base.",
        })
    elif lift > 65:
        issues.append({
            "severity": "HIGH", "axis": "lift",
            "message": f"Top notes dominant ({lift:.0f}%)",
            "suggestion": "Boost heart notes to balance the opening.",
        })

    bloom = float(inds.get("bloom", 50) or 0.0)
    if bloom < 30:
        issues.append({
            "severity": "HIGH", "axis": "bloom",
            "message": f"Linear evolution ({bloom:.0f}/100)",
            "detail": "Only one dominant leader across all time windows — the formula does not evolve",
            "suggestion": "Add material with a different VP window that emerges in the heart stage.",
        })
    elif bloom < 50:
        issues.append({
            "severity": "MEDIUM", "axis": "bloom",
            "message": f"Limited evolution ({bloom:.0f}/100)",
            "detail": f"Only {int(bloom // 20)} unique dominant leaders — the formula is somewhat linear",
            "suggestion": "Ensure at least three materials with distinct VP profiles dominate different windows.",
        })

    char = float(inds.get("character", 50) or 0.0)
    if char < 40 or char > 80:
        label = "off-family" if char < 40 else "excessively unique"
        issues.append({
            "severity": "MEDIUM", "axis": "character",
            "message": f"Character {label} ({char:.0f}/100)",
            "detail": "OAV profile deviates significantly from family targets.",
            "suggestion": "Adjust material ratios to better match family OAV profile.",
        })

    bal = float(inds.get("balance", 50) or 0.0)
    if bal < 40:
        issues.append({
            "severity": "HIGH", "axis": "balance",
            "message": f"Pyramid off-target ({bal:.0f}/100)",
            "suggestion": "Adjust top/heart/base ratios to match the family target.",
        })
    return issues


def diagnose_oav_table(oav_table: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for row in oav_table:
        name = str(row.get("name", ""))
        oav = float(row.get("oav") or 0.0)
        note = str(row.get("note", ""))
        role = str(row.get("role", ""))
        active_ul = float(row.get("active_ul") or 0.0)
        if oav < 1.0 and role in {"character", "radiance", "volume"}:
            issues.append({
                "severity": "MEDIUM",
                "axis": "dormant",
                "material": name,
                "message": f"{name} is dormant (OAV={oav:.2f}) but role={role}",
                "detail": f"{active_ul:.0f} uL active — functionally invisible",
                "suggestion": f"Increase {name} or swap for a higher-VP analogue.",
            })
        if oav > 10000 and note == "base":
            issues.append({
                "severity": "INFO",
                "axis": "overdose",
                "material": name,
                "message": f"{name} at extreme OAV ({oav:.0f}) for a base note",
                "suggestion": f"Consider reducing {name} to reduce drydown saturation.",
            })
    return issues


def diagnose_gates(gates: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for gate in gates:
        status = gate.get("status")
        if status not in {"FAIL", "WARN"}:
            continue
        issues.append({
            "severity": "HIGH" if status == "FAIL" else "LOW",
            "axis": "gate",
            "gate": gate.get("gate", "?"),
            "message": str(gate.get("detail", f"Gate {status.lower()}"))[:160],
            "status": status,
        })
    return issues


def diagnose_vp_pairs(oav_table: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    low_vp = [
        row for row in oav_table
        if float(row.get("vp_pa") or 0.0) < 0.1 and float(row.get("oav") or 0.0) < 1.0
    ]
    low_vp_names = sorted({str(row.get("name", "")) for row in low_vp if row.get("name")})
    if len(low_vp_names) >= 2:
        issues.append({
            "severity": "MEDIUM",
            "axis": "vp_gap",
            "message": f"{len(low_vp_names)} low-VP materials with OAV<1: {', '.join(low_vp_names)}",
            "detail": "These materials cannot volatilize enough to interact in headspace.",
            "suggestion": "Swap one for a higher-VP analogue in the same olfactive family.",
        })
    return issues


def diagnose_data_quality(oav_table: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for row in oav_table:
        if row.get("odt_air_ppm") is not None:
            continue
        issues.append({
            "severity": "HIGH",
            "axis": "data_quality",
            "material": row.get("name", ""),
            "message": f"{row.get('name', 'material')} has no ODT data — OAV is unreliable",
        })
    return issues


def diagnose_release_report(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    issues.extend(diagnose_industry(report.get("industry_10", {}) or {}))
    issues.extend(diagnose_oav_table(list(report.get("oav_table", []) or [])))
    issues.extend(diagnose_vp_pairs(list(report.get("oav_table", []) or [])))
    issues.extend(diagnose_data_quality(list(report.get("oav_table", []) or [])))
    issues.extend(diagnose_gates(list(report.get("gates", []) or [])))
    issues.sort(key=lambda row: SEVERITY_RANK.get(str(row.get("severity", "LOW")), 99))
    return issues


def _serialize_recommendation(rec: object) -> dict[str, Any]:
    if isinstance(rec, dict):
        return dict(rec)
    return asdict(rec)


def _deterministic_repairs_from_gates(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    repairs: list[dict[str, Any]] = []
    for gate in report.get("gates", []) or []:
        if gate.get("status") != "FAIL":
            continue
        gate_name = str(gate.get("gate", ""))
        detail = str(gate.get("detail", ""))
        if gate_name == "safety_ifra_allergen":
            repairs.append({
                "gate": gate_name,
                "action": "cap_ifra_and_rebalance",
                "determinism": "hard",
                "detail": detail,
            })
        elif gate_name == "pipette_floor_neat_traces":
            repairs.append({
                "gate": gate_name,
                "action": "raise_neat_traces_to_pipette_floor",
                "determinism": "hard",
                "detail": detail,
            })
        elif gate_name == "exact_subtotal":
            repairs.append({
                "gate": gate_name,
                "action": "renormalize_to_expected_concentrate",
                "determinism": "hard",
                "detail": detail,
            })
        elif gate_name == "robustness_perturbation":
            repairs.append({
                "gate": gate_name,
                "action": "cap_safety_sensitive_materials_for_positive_perturbation",
                "determinism": "hard",
                "detail": detail,
            })
        elif gate_name in {"material_spine_coverage", "physics_data_coverage", "odt_coverage"}:
            repairs.append({
                "gate": gate_name,
                "action": "complete_material_data_spine_before_release",
                "determinism": "hard",
                "detail": detail,
            })
        elif gate_name in {"chemistry_stability", "phase_compatibility"}:
            repairs.append({
                "gate": gate_name,
                "action": "rerun_with_chemistry_constraints",
                "determinism": "hard",
                "detail": detail,
            })
    return repairs


def _repairability(report: Mapping[str, Any], deterministic_repairs: list[dict[str, Any]]) -> str:
    failed = [gate for gate in report.get("gates", []) or [] if gate.get("status") == "FAIL"]
    if not failed:
        return "none_needed"
    if deterministic_repairs and len(deterministic_repairs) == len(failed):
        return "deterministic"
    if deterministic_repairs:
        return "mixed"
    return "advisory_only"


def build_intervention_contract(
    formula: Mapping[str, Any],
    report: Mapping[str, Any],
    *,
    batch_volume_ml: float = 30.0,
    top_n: int = 5,
) -> dict[str, Any]:
    """Build one shared intervention payload for release and optimizer surfaces."""
    diagnosis = diagnose_release_report(report)
    deterministic_repairs = _deterministic_repairs_from_gates(report)

    fv = _build_formula_vector(formula, formula.get("dilutions", {}) or {})
    context = InterventionContext(
        mode="pre_mix",
        batch_volume_ml=batch_volume_ml,
        category_hint=str((report.get("config_summary") or {}).get("family_archetype") or ""),
    )
    advisory = generate_intervention_recommendations(
        fv,
        dict(report.get("scores", {}) or {}),
        top_n=top_n,
        mode="pre_mix",
        batch_volume_ml=batch_volume_ml,
        context=context,
    )
    advisory_repairs = [_serialize_recommendation(rec) for rec in advisory]
    swap_candidates = [
        rec for rec in advisory_repairs
        if str(rec.get("action", "")).upper() in {"ADD", "REBALANCE", "INCREASE"}
    ][:3]

    blocking_issues = [
        issue for issue in diagnosis
        if issue.get("severity") in {"CRITICAL", "HIGH"}
        or issue.get("status") == "FAIL"
    ]
    confidence = {
        "combined_confidence": float((report.get("confidence") or {}).get("combined_confidence", 0.0) or 0.0),
        "combined_grade": str((report.get("confidence") or {}).get("combined_grade", "UNKNOWN")),
        "preflight_status": str((report.get("preflight") or {}).get("status", "UNKNOWN")),
        "repairability": _repairability(report, deterministic_repairs),
    }
    provenance = {
        "modules": [
            "engine.pipeline.interventions",
            "engine.formula_recommendations",
            "engine.intervention_profiles",
        ],
        "diagnosis_sources": ["industry_10", "oav_table", "gates", "preflight"],
        "advisory_recommendation_count": len(advisory_repairs),
        "deterministic_repair_count": len(deterministic_repairs),
    }
    return {
        "blocking_issues": blocking_issues,
        "deterministic_repairs": deterministic_repairs,
        "advisory_repairs": advisory_repairs,
        "swap_candidates": swap_candidates,
        "confidence": confidence,
        "provenance": provenance,
    }
