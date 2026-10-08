"""Canonical intervention contract for release and optimizer outputs.

This module centralizes post-analysis diagnosis and recommendation generation so
the canonical release CLI and gate-aware optimizer expose one shared structure.
"""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any, Mapping

from engine.formula_recommendations import generate_intervention_recommendations
from engine.intervention_context import InterventionContext
from engine.optimizer.models import FormulaVector

# Release-gate statuses that block release (mirrors gates.BLOCKING_STATUSES;
# kept local so this module does not import the gate engine). HOLD means a gate
# could not decide because data is missing: it blocks like FAIL.
_BLOCKING_GATE_STATUSES = frozenset({"HOLD", "FAIL"})

SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def _finite_metric(values: Mapping[str, Any], key: str) -> float | None:
    """Return an explicitly supplied finite metric without inventing a default."""

    value = values.get(key)
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _screening_issue(**values: Any) -> dict[str, Any]:
    """Mark a heuristic observation as incapable of authorizing a remix."""

    return {
        **values,
        "evidence_role": "HEURISTIC_SCREENING_ONLY",
        "claim_ceiling": "NOT_A_SENSORY_OUTCOME_OR_COMPOUNDING_AUTHORITY",
        "compounding_action_authority": False,
        "requires_controlled_comparison": True,
    }


def _build_formula_vector(formula: Mapping[str, Any], dilutions: Mapping[str, float]) -> FormulaVector:
    total_ul = sum(float(v or 0.0) for v in formula.get("ingredients_ul", {}).values()) or 1.0
    pct_ings: dict[str, float] = {}
    for name, ul in (formula.get("ingredients_ul", {}) or {}).items():
        dil = float(dilutions.get(name, 1.0) or 1.0)
        pct_ings[str(name)] = (float(ul or 0.0) * dil / total_ul) * 100.0
    return FormulaVector(ingredients=pct_ings, dilutions=dict(dilutions))


def diagnose_industry(inds: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    ten = _finite_metric(inds, "tenacity")
    if ten is not None and ten < 15:
        issues.append(_screening_issue(**{
            "severity": "CRITICAL", "axis": "tenacity",
            "message": f"Low base+heart share in the legacy OAV screen ({ten:.0f}/100)",
            "detail": (
                "This heuristic ratio does not establish rapid fade, longevity, "
                "or the absence of a perceptual foundation."
            ),
            "suggestion": (
                "Inspect qualified time-series coverage and use a controlled temporal "
                "comparison before changing any dose."
            ),
        }))
    elif ten is not None and ten < 30:
        issues.append(_screening_issue(**{
            "severity": "HIGH", "axis": "tenacity",
            "message": f"Low base+heart share in the legacy OAV screen ({ten:.0f}/100)",
            "detail": (
                "This heuristic ratio is not a calibrated prediction of fade, "
                "longevity, or perceived base strength."
            ),
            "suggestion": (
                "Inspect qualified time-series coverage and use a controlled temporal "
                "comparison before changing any dose."
            ),
        }))

    lift = _finite_metric(inds, "lift")
    if lift is not None and lift > 85:
        issues.append(_screening_issue(**{
            "severity": "CRITICAL", "axis": "lift",
            "message": f"High top-note share in the legacy OAV screen ({lift:.0f}%)",
            "detail": (
                "An OAV share does not establish sensory dominance, imbalance, "
                "or perceived mixture contribution."
            ),
            "suggestion": (
                "Review qualified modeled time windows and, if needed, compare "
                "constant-total variants; do not reduce a material from this ratio alone."
            ),
        }))
    elif lift is not None and lift > 65:
        issues.append(_screening_issue(**{
            "severity": "HIGH", "axis": "lift",
            "message": f"High top-note share in the legacy OAV screen ({lift:.0f}%)",
            "detail": "This ratio is not a calibrated measure of perceived dominance.",
            "suggestion": (
                "Use a controlled temporal comparison before changing top, heart, "
                "or base doses."
            ),
        }))

    bloom = _finite_metric(inds, "bloom")
    if bloom is not None and bloom < 30:
        issues.append(_screening_issue(**{
            "severity": "HIGH", "axis": "bloom",
            "message": f"Few distinct leaders in the legacy modeled windows ({bloom:.0f}/100)",
            "detail": (
                "A repeated modeled OAV leader does not prove that the perfume is "
                "sensorially linear or does not evolve."
            ),
            "suggestion": (
                "Check temporal applicability and compare measured or qualified "
                "descriptor trajectories before altering the formula."
            ),
        }))
    elif bloom is not None and bloom < 50:
        issues.append(_screening_issue(**{
            "severity": "MEDIUM", "axis": "bloom",
            "message": f"Few distinct leaders in the legacy modeled windows ({bloom:.0f}/100)",
            "detail": (
                f"The screen found about {int(bloom // 20)} distinct modeled leaders; "
                "this is not a validated sensory-evolution endpoint."
            ),
            "suggestion": "Use a controlled temporal comparison before changing the formula.",
        }))

    char = _finite_metric(inds, "character")
    if char is not None and (char < 40 or char > 80):
        issues.append(_screening_issue(**{
            "severity": "MEDIUM", "axis": "character",
            "message": f"Legacy OAV-family alignment screen is outside its target band ({char:.0f}/100)",
            "detail": (
                "Chemical-family/OAV similarity is not a measured character, receptor, "
                "or recognizability result."
            ),
            "suggestion": (
                "Evaluate concentration-aware descriptor evidence and a controlled "
                "character comparison before altering ratios."
            ),
        }))

    bal = _finite_metric(inds, "balance")
    if bal is not None and bal < 40:
        issues.append(_screening_issue(**{
            "severity": "HIGH", "axis": "balance",
            "message": f"Legacy pyramid diagnostic is outside its target band ({bal:.0f}/100)",
            "detail": "The pyramid diagnostic is not a calibrated mixture-balance judgment.",
            "suggestion": "Treat this as a controlled-comparison hypothesis, not an automatic ratio repair.",
        }))
    return issues


def diagnose_oav_table(oav_table: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for row in oav_table:
        name = str(row.get("name", ""))
        screening_oav = _finite_metric(
            row,
            "screening_oav" if "screening_oav" in row else "oav",
        )
        canonical_oav = _finite_metric(row, "canonical_oav")
        if screening_oav is None and canonical_oav is None:
            # Unknown is not dormant.  Data-quality reporting handles the
            # missing endpoint without turning it into a physical diagnosis.
            continue
        oav = canonical_oav if canonical_oav is not None else screening_oav
        assert oav is not None
        note = str(row.get("note", ""))
        role = str(row.get("role", ""))
        active_ul = float(row.get("active_ul") or 0.0)
        if oav < 1.0 and role in {"character", "radiance", "volume"}:
            basis = "input-complete modeled" if canonical_oav is not None else "screening"
            issues.append(_screening_issue(**{
                "severity": "MEDIUM",
                "axis": "modeled_detection_screen",
                "material": name,
                "message": f"{name} has {basis} gas OAV below 1 ({oav:.2f}) for role={role}",
                "detail": (
                    f"{active_ul:.0f} uL modeled active dose. This is a detection-related "
                    "screen under the stated model, not proof that the material is "
                    "functionally invisible in the mixture."
                ),
                "suggestion": (
                    f"Check {name}'s phase, threshold, matrix, and concentration applicability; "
                    "use a controlled comparison before increasing or replacing it."
                ),
            }))
        if oav > 10000 and note == "base":
            issues.append(_screening_issue(**{
                "severity": "INFO",
                "axis": "high_oav_screen",
                "material": name,
                "message": f"{name} has a high modeled OAV screen ({oav:.0f})",
                "detail": (
                    "A large OAV does not by itself establish overdose, saturation, "
                    "sensory dominance, mixture share, or unpleasantness."
                ),
                "suggestion": (
                    f"Do not change the {name} dose from OAV alone; require an applicable "
                    "intensity/character model or a controlled sensory comparison."
                ),
            }))
    return issues


def diagnose_gates(gates: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for gate in gates:
        status = gate.get("status")
        if status not in {"FAIL", "HOLD", "WARN"}:
            continue
        blocking = status in _BLOCKING_GATE_STATUSES
        issues.append({
            "severity": "HIGH" if blocking else "LOW",
            "axis": "gate",
            "gate": gate.get("gate", "?"),
            "message": str(gate.get("detail", f"Gate {status.lower()}"))[:160],
            "status": status,
            "blocks_release": blocking,
            "remediation_required": blocking,
            "compounding_action_authority": False,
            "physical_change_authority": False,
        })
    return issues


def diagnose_vp_pairs(oav_table: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    low_vp: list[Mapping[str, Any]] = []
    for row in oav_table:
        vp_pa = _finite_metric(row, "vp_pa")
        canonical_oav = _finite_metric(row, "canonical_oav")
        if vp_pa is None or canonical_oav is None:
            # Missing values are unknown, and screening-only OAV is not enough
            # to support even this qualified pair diagnostic.
            continue
        if vp_pa < 0.1 and canonical_oav < 1.0:
            low_vp.append(row)
    low_vp_names = sorted({str(row.get("name", "")) for row in low_vp if row.get("name")})
    if len(low_vp_names) >= 2:
        issues.append(_screening_issue(**{
            "severity": "MEDIUM",
            "axis": "vp_gap",
            "message": (
                f"{len(low_vp_names)} low-VP materials have input-complete modeled "
                f"OAV<1: {', '.join(low_vp_names)}"
            ),
            "detail": (
                "This qualified modeled condition does not establish that the materials "
                "cannot interact in headspace or in perception."
            ),
            "suggestion": (
                "Check matrix/substrate applicability and test a controlled alternative; "
                "do not swap a material from this screen alone."
            ),
        }))
    return issues


def diagnose_data_quality(oav_table: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for row in oav_table:
        if row.get("odt_air_ppm") is not None or row.get("canonical_oav") is not None:
            continue
        issues.append({
            "severity": "HIGH",
            "axis": "data_quality",
            "material": row.get("name", ""),
            "message": (
                f"{row.get('name', 'material')} has no compatible gas-threshold "
                "support for a numerical OAV"
            ),
            "detail": (
                "This blocks a supported numerical OAV claim, but it does not block "
                "every formulation hypothesis or an independently calibrated intensity curve."
            ),
            "compounding_action_authority": False,
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
    payload = dict(rec) if isinstance(rec, dict) else asdict(rec)
    payload["authority_state"] = "UNVALIDATED_ADVISORY"
    payload["proposal_status"] = "UNVALIDATED_ADVISORY"
    payload["formula_optimization_authority"] = False
    payload["compounding_action_authority"] = False
    payload["requires_controlled_comparison"] = True
    payload["selection_basis"] = "LEGACY_DIAGNOSTIC_TOTAL_NOT_ADMITTED"
    return payload


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
    for repair in repairs:
        repair.update({
            "blocks_release": True,
            "remediation_required": True,
            "compounding_action_authority": False,
            "physical_change_authority": False,
            "requires_new_formula_version": True,
        })
    return repairs


def _repairability(report: Mapping[str, Any], deterministic_repairs: list[dict[str, Any]]) -> str:
    gates = report.get("gates", []) or []
    failed = [gate for gate in gates if gate.get("status") == "FAIL"]
    if not failed:
        # A HOLD is not repairable by changing the formula: it needs data.
        if any(gate.get("status") == "HOLD" for gate in gates):
            return "data_required"
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
    include_advisory_recommendations: bool = False,
) -> dict[str, Any]:
    """Build one shared intervention payload for release and optimizer surfaces.

    ``include_advisory_recommendations`` is deliberately opt-in. Diagnosis,
    blocking issues, and hard deterministic repairs are independent of the
    comparatively expensive heuristic recommendation generator and are always
    produced. A caller that explicitly requests advisory search still receives
    non-authoritative controlled-comparison hypotheses unless a separately
    admitted ranking endpoint grants formula-optimization authority.
    """
    diagnosis = diagnose_release_report(report)
    deterministic_repairs = _deterministic_repairs_from_gates(report)
    ranking = dict(report.get("ranking", {}) or {})
    formula_optimization_authority = bool(
        ranking.get("formula_optimization_authority", False)
    )

    # OAV/industry indices remain useful hypotheses, but they cannot cause a
    # remix when the ranking endpoint is withheld. Gate failures retain
    # release-blocking authority, but neither the failure nor a deterministic
    # repair label authorizes a physical change or recompounding action.
    if not formula_optimization_authority:
        for issue in diagnosis:
            if issue.get("axis") == "gate":
                blocking = issue.get("status") in _BLOCKING_GATE_STATUSES
                issue["blocks_release"] = blocking
                issue["remediation_required"] = blocking
                issue["compounding_action_authority"] = False
                issue["physical_change_authority"] = False
                continue
            original_severity = str(issue.get("severity", "INFO"))
            issue["diagnostic_severity"] = original_severity
            issue["severity"] = "INFO"
            issue["compounding_action_authority"] = False
            issue["requires_controlled_comparison"] = True
            if issue.get("suggestion"):
                issue["suggestion"] = (
                    "Controlled-comparison hypothesis only; do not auto-recompound. "
                    + str(issue["suggestion"])
                )

    if include_advisory_recommendations:
        fv = _build_formula_vector(formula, formula.get("dilutions", {}) or {})
        context = InterventionContext(
            mode="pre_mix",
            batch_volume_ml=batch_volume_ml,
            category_hint=str(
                (report.get("config_summary") or {}).get("family_archetype") or ""
            ),
        )
        advisory = generate_intervention_recommendations(
            fv,
            dict(report.get("scores", {}) or {}),
            top_n=top_n,
            mode="pre_mix",
            batch_volume_ml=batch_volume_ml,
            context=context,
            include_unvalidated_advisory=True,
        )
        advisory_repairs = [_serialize_recommendation(rec) for rec in advisory]
        if not formula_optimization_authority:
            for repair in advisory_repairs:
                repair["compounding_action_authority"] = False
                repair["requires_controlled_comparison"] = True
        advisory_status = "COMPUTED"
    else:
        advisory_repairs = []
        advisory_status = "SKIPPED_NOT_REQUESTED"

    swap_candidates = (
        [
            rec
            for rec in advisory_repairs
            if str(rec.get("action", "")).upper() in {"ADD", "REBALANCE", "INCREASE"}
            and rec.get("formula_optimization_authority") is True
            and rec.get("compounding_action_authority") is True
        ][:3]
        if formula_optimization_authority
        else []
    )

    blocking_issues = [
        issue
        for issue in diagnosis
        if (
            issue.get("blocks_release", False)
            or issue.get("status") in _BLOCKING_GATE_STATUSES
            or (
                issue.get("compounding_action_authority", False)
                and issue.get("severity") in {"CRITICAL", "HIGH"}
            )
        )
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
        "advisory_recommendations_requested": include_advisory_recommendations,
        "advisory_status": advisory_status,
        "deterministic_repair_count": len(deterministic_repairs),
        "formula_optimization_authority": formula_optimization_authority,
        "ranking_status": str(ranking.get("status", "UNAVAILABLE")),
    }
    return {
        "blocking_issues": blocking_issues,
        "deterministic_repairs": deterministic_repairs,
        "advisory_repairs": advisory_repairs,
        "swap_candidates": swap_candidates,
        "confidence": confidence,
        "provenance": provenance,
    }
