"""Release-pipeline preflight checks.

Preflight is intentionally narrower than the full gate stack. It verifies that
the pipeline's inputs and runtime doctrine are coherent enough to trust the
subsequent OAV/gate analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from engine.calibration.hashing import stable_file_hash
from engine.inventory_parser import INVENTORY_PATH, parse_inventory
from engine.knowledge.literature_rules import (
    build_knowledge_rule_quality_contract,
    build_literature_rule_contract,
)
from engine.name_utils import normalize_name
from engine.odt_verifier import verify_entry
from engine.pipeline.formula_state import FormulaState
from engine.schema_validator import SchemaValidator
from engine.science_audit import build_science_audit_contract, coverage_confidence_penalty


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    name: str
    status: str
    detail: str
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = {"check_name": self.name, "status": self.status, "detail": self.detail}
        if self.data:
            payload["data"] = dict(self.data)
        return payload


@dataclass(frozen=True, slots=True)
class PreflightReport:
    status: str
    checks: tuple[PreflightCheck, ...]
    confidence_penalty: float
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checks": [check.as_dict() for check in self.checks],
            "confidence_penalty": round(float(self.confidence_penalty), 3),
            "warnings": list(self.warnings),
        }


def _status_from_checks(checks: list[PreflightCheck]) -> str:
    if any(check.status == "FAIL" for check in checks):
        return "FAIL"
    if any(check.status == "WARN" for check in checks):
        return "WARN"
    return "PASS"


def _input_normalization_check(formula: Mapping[str, Any]) -> PreflightCheck:
    ingredients = formula.get("ingredients_ul", {}) or {}
    if not ingredients:
        return PreflightCheck("input_normalization", "FAIL", "No ingredient volumes found.")

    empty_names = sorted(str(name) for name in ingredients if not str(name).strip())
    negative = {
        str(name): float(value or 0.0)
        for name, value in ingredients.items()
        if float(value or 0.0) < 0
    }
    zeroes = sorted(str(name) for name, value in ingredients.items() if float(value or 0.0) == 0.0)
    if empty_names or negative:
        detail = []
        if empty_names:
            detail.append(f"empty names={len(empty_names)}")
        if negative:
            detail.append(f"negative doses={len(negative)}")
        return PreflightCheck(
            "input_normalization",
            "FAIL",
            "; ".join(detail),
            {"empty_names": empty_names, "negative_doses": negative},
        )
    if zeroes:
        return PreflightCheck(
            "input_normalization",
            "WARN",
            f"{len(zeroes)} materials carry zero volume entries.",
            {"zero_volume_materials": zeroes[:20]},
        )
    return PreflightCheck("input_normalization", "PASS", f"{len(ingredients)} ingredients parsed.")


def _schema_check() -> PreflightCheck:
    report = SchemaValidator().validate_all()
    summary = report.summary()
    if summary["errors"] > 0:
        return PreflightCheck(
            "knowledge_graph_schema",
            "WARN",
            f"{summary['errors']} schema errors in structured knowledge assets; runtime proceeds with caution.",
            summary,
        )
    if summary["warnings"] > 0:
        return PreflightCheck(
            "knowledge_graph_schema",
            "WARN",
            f"{summary['warnings']} schema warnings in structured knowledge assets.",
            summary,
        )
    return PreflightCheck("knowledge_graph_schema", "PASS", "Structured knowledge assets validated.", summary)


def _literature_check() -> PreflightCheck:
    contract = build_literature_rule_contract().as_dict()
    status = contract["status"]
    if status == "FAIL":
        detail = "Literature rule contract is not runtime-complete."
    elif status == "WARN":
        detail = "Literature rule contract is usable but needs refresh or normalization."
    else:
        detail = "Literature rule contract is present and index-aware."
    return PreflightCheck("literature_rule_contract", status, detail, contract)


def _knowledge_rule_quality_check() -> tuple[PreflightCheck, float]:
    contract = build_knowledge_rule_quality_contract().as_dict()
    status = contract["status"]
    if status == "FAIL":
        detail = "Structured runtime rules are not usable."
    elif status == "WARN":
        detail = "Structured runtime rules include degraded or orphan references."
    else:
        detail = "Structured runtime rules passed viability screening."
    penalty = 0.0
    penalty += min(4.0, float(contract.get("invalid_entries", 0) or 0) * 0.25)
    penalty += min(2.0, float(contract.get("generic_material_refs", 0) or 0) * 0.01)
    return (
        PreflightCheck("knowledge_rule_quality", status, detail, contract),
        round(penalty, 3),
    )


def _science_check() -> tuple[PreflightCheck, float]:
    contract = build_science_audit_contract()
    penalty = coverage_confidence_penalty(contract)
    status = "PASS"
    detail = "Science coverage supports deterministic runtime use."
    if penalty >= 20.0:
        status = "WARN"
        detail = f"Sparse science coverage triggers {penalty:.1f} confidence penalty."
    return (
        PreflightCheck(
            "science_coverage",
            status,
            detail,
            {
                "coverage_pct": contract.get("data_coverage_pct", {}),
                "known_weaknesses": contract.get("weaknesses", []),
                "confidence_penalty": round(penalty, 3),
            },
        ),
        penalty,
    )


def _odt_authority_check(state: FormulaState) -> tuple[PreflightCheck, float]:
    flagged: list[dict[str, Any]] = []
    tier_counts: dict[str, int] = {}
    for material in state.materials:
        entry = verify_entry(material.name, no_network=True)
        verdict = str(entry.get("verdict", "NO_DATA"))
        local_vfy = str(entry.get("local_vfy", "UNKNOWN"))
        tier_counts[local_vfy] = tier_counts.get(local_vfy, 0) + 1
        if verdict in {"SUGGESTED_CORRECTION", "NO_DATA"} or local_vfy in {"UNVERIFIED", "DERIVED"}:
            flagged.append({
                "material": material.name,
                "verdict": verdict,
                "local_vfy": local_vfy,
                "source": entry.get("source", ""),
                "reason": entry.get("reason", ""),
            })
    if not flagged:
        return (
            PreflightCheck("odt_authority", "PASS", "ODT authority is acceptable for the parsed materials.", {"tiers": tier_counts}),
            0.0,
        )
    penalty = min(8.0, len(flagged) * 0.75)
    detail = f"{len(flagged)} materials use derived/unverified or mismatched ODT authority."
    return (
        PreflightCheck("odt_authority", "WARN", detail, {"tiers": tier_counts, "flagged_materials": flagged[:25]}),
        round(penalty, 3),
    )


def _data_authority_check(state: FormulaState) -> tuple[PreflightCheck, float]:
    material_count = max(1, len(state.materials))
    odt_authoritative = 0
    vp_authoritative = 0
    gamma_heuristic = 0
    gamma_fallback = 0
    hsp_present = 0
    ifra_present = 0
    heuristic_materials: list[dict[str, Any]] = []

    for material in state.materials:
        odt_source = str(material.sources.get("odt", "")).lower()
        vp_source = str(material.sources.get("vp", "")).lower()
        if any(token in odt_source for token in ("peer_reviewed", "literature:")):
            odt_authoritative += 1
        if any(token in vp_source for token in ("data_spine", "registry:")):
            vp_authoritative += 1
        gamma_source = str(material.gamma_source or "").lower()
        if gamma_source.startswith("heuristic:"):
            gamma_heuristic += 1
            heuristic_materials.append({"material": material.name, "field": "gamma", "source": material.gamma_source})
        if gamma_source.startswith("fallback:"):
            gamma_fallback += 1
            heuristic_materials.append({"material": material.name, "field": "gamma", "source": material.gamma_source})
        if material.hsp is not None:
            hsp_present += 1
        if material.ifra_limit_pct is not None:
            ifra_present += 1

    coverage = {
        "odt_authoritative_pct": round(100.0 * odt_authoritative / material_count, 1),
        "vp_authoritative_pct": round(100.0 * vp_authoritative / material_count, 1),
        "gamma_heuristic_pct": round(100.0 * gamma_heuristic / material_count, 1),
        "gamma_fallback_pct": round(100.0 * gamma_fallback / material_count, 1),
        "hsp_available_pct": round(100.0 * hsp_present / material_count, 1),
        "ifra_structured_pct": round(100.0 * ifra_present / material_count, 1),
    }
    penalty = 0.0
    if coverage["odt_authoritative_pct"] < 50.0:
        penalty += 3.0
    if coverage["vp_authoritative_pct"] < 80.0:
        penalty += 2.0
    if coverage["gamma_fallback_pct"] > 0.0:
        penalty += 2.0
    elif coverage["gamma_heuristic_pct"] > 75.0:
        penalty += 1.5
    if coverage["ifra_structured_pct"] < 40.0:
        penalty += 1.0

    if penalty <= 0.0:
        return (
            PreflightCheck("data_authority", "PASS", "Authority coverage is adequate for live scoring.", coverage),
            0.0,
        )
    return (
        PreflightCheck(
            "data_authority",
            "WARN",
            "Live scoring relies on a meaningful amount of heuristic or sparse authority data.",
            {
                "coverage": coverage,
                "heuristic_materials": heuristic_materials[:25],
            },
        ),
        round(min(8.0, penalty), 3),
    )


def _dilution_consistency_check(formula: Mapping[str, Any]) -> PreflightCheck:
    """Fail closed unless every formula row identifies one live inventory stock."""
    from collections import defaultdict

    exact_identity: dict[str, list] = defaultdict(list)
    legacy_identity: dict[str, list] = defaultdict(list)
    for record in parse_inventory(
        unique=False,
        include_solvents=True,
        include_unavailable=True,
    ):
        exact_identity[normalize_name(record.identity_name or record.name)].append(record)
        legacy_identity[normalize_name(record.name)].append(record)

    ingredients = formula.get("ingredients_ul", {}) or {}
    dilutions = formula.get("dilutions", {}) or {}
    stock_specs = formula.get("stock_specs", {}) or {}
    issues: list[dict[str, Any]] = []
    matched: list[dict[str, Any]] = []
    resolved_stock_specs: dict[str, dict[str, Any]] = {}
    declared_active_ul = 0.0
    projected_live_active_ul = 0.0
    live_projection_complete = True
    grouped_active_impact: dict[str, dict[str, Any]] = {}
    for name in ingredients:
        norm = normalize_name(name)
        candidates = exact_identity.get(norm) or legacy_identity.get(norm) or []
        spec = dict(stock_specs.get(name, {}) or {})
        formula_dil = float(spec.get("fraction", dilutions.get(name, 1.0)) or 1.0)
        raw_ul = float(ingredients.get(name, 0.0) or 0.0)
        declared_active_ul += raw_ul * formula_dil
        formula_basis = str(spec.get("fraction_basis", "unspecified"))
        formula_carrier = normalize_name(str(spec.get("carrier", "")))
        declared = bool(spec.get("declared", name in dilutions))
        if spec.get("conflict"):
            live_projection_complete = False
            issues.append({"material": name, "reason": "conflicting_stock_rows"})
            continue
        if not candidates:
            live_projection_complete = False
            issues.append({"material": name, "reason": "not_in_inventory"})
            continue
        owned = [record for record in candidates if record.status == "owned"]
        group_label = owned[0].name if owned else candidates[0].name
        group = grouped_active_impact.setdefault(
            group_label,
            {
                "declared_active_ul": 0.0,
                "projected_live_active_ul": 0.0,
                "live_projection_complete": True,
            },
        )
        group["declared_active_ul"] += raw_ul * formula_dil
        if len(owned) == 1:
            projected_live_active_ul += raw_ul * owned[0].dilution
            group["projected_live_active_ul"] += raw_ul * owned[0].dilution
        else:
            live_projection_complete = False
            group["live_projection_complete"] = False
        if not owned:
            issues.append(
                {
                    "material": name,
                    "reason": "inventory_stock_unavailable",
                    "statuses": sorted({record.status for record in candidates}),
                }
            )
            continue
        if not declared:
            issues.append(
                {
                    "material": name,
                    "reason": "stock_fraction_not_declared",
                    "inventory_dilutions": sorted({record.dilution for record in owned}),
                }
            )
            continue

        fraction_matches = [
            record for record in owned if abs(formula_dil - record.dilution) <= 0.005
        ]
        if not fraction_matches:
            live_dilutions = sorted({round(record.dilution, 6) for record in owned})
            multipliers = [
                round(record.dilution / formula_dil, 4)
                for record in owned
                if formula_dil > 0
            ]
            issues.append(
                {
                    "material": name,
                    "reason": "stock_fraction_mismatch",
                    "formula_dilution": round(formula_dil, 6),
                    "inventory_dilutions": live_dilutions,
                    "active_multiplier_if_live_stock_used": multipliers,
                }
            )
            continue

        compatible = []
        basis_mismatches = []
        carrier_mismatches = []
        for record in fraction_matches:
            inventory_basis = record.fraction_basis
            if (
                formula_basis != "unspecified"
                and inventory_basis != "unspecified"
                and formula_basis != inventory_basis
            ):
                basis_mismatches.append(inventory_basis)
                continue
            inventory_carrier = normalize_name(record.carrier)
            if formula_carrier and inventory_carrier and formula_carrier != inventory_carrier:
                carrier_mismatches.append(inventory_carrier)
                continue
            compatible.append(record)
        if not compatible:
            issues.append(
                {
                    "material": name,
                    "reason": (
                        "stock_fraction_basis_mismatch"
                        if basis_mismatches
                        else "stock_carrier_mismatch"
                    ),
                    "formula_basis": formula_basis,
                    "inventory_bases": sorted(set(basis_mismatches)),
                    "formula_carrier": formula_carrier,
                    "inventory_carriers": sorted(set(carrier_mismatches)),
                }
            )
            continue
        if len(compatible) > 1:
            issues.append(
                {
                    "material": name,
                    "reason": "ambiguous_live_stock",
                    "variants": [record.raw_name for record in compatible],
                }
            )
            continue
        record = compatible[0]
        resolved_stock_specs[name] = {
            "fraction": formula_dil,
            "fraction_basis": (
                record.fraction_basis
                if record.fraction_basis != "unspecified"
                else formula_basis
            ),
            "carrier": record.carrier or str(spec.get("carrier", "")),
            "approximate": bool(record.approximate or spec.get("approximate", False)),
            "declared": True,
            "authority": "formula_row+inventory_snapshot",
        }
        matched.append(
            {
                "material": name,
                "inventory_identity": record.identity_name or record.name,
                "fraction": record.dilution,
                "fraction_basis": record.fraction_basis,
                "carrier": record.carrier,
            }
        )

    active_impact: dict[str, Any] = {
        "declared_active_ul": round(declared_active_ul, 6),
        "live_projection_complete": live_projection_complete,
    }
    if live_projection_complete:
        active_impact.update(
            {
                "projected_live_active_ul": round(projected_live_active_ul, 6),
                "active_multiplier_if_live_stocks_used": round(
                    projected_live_active_ul / declared_active_ul,
                    6,
                )
                if declared_active_ul > 0
                else None,
            }
        )
    active_impact_by_inventory_material: dict[str, dict[str, Any]] = {}
    for material, raw_impact in sorted(grouped_active_impact.items()):
        impact = {
            "declared_active_ul": round(raw_impact["declared_active_ul"], 6),
            "live_projection_complete": bool(
                raw_impact["live_projection_complete"]
            ),
        }
        if impact["live_projection_complete"]:
            projected = float(raw_impact["projected_live_active_ul"])
            declared = float(raw_impact["declared_active_ul"])
            impact.update(
                {
                    "projected_live_active_ul": round(projected, 6),
                    "active_multiplier_if_live_stocks_used": (
                        round(projected / declared, 6) if declared > 0 else None
                    ),
                }
            )
        active_impact_by_inventory_material[material] = impact
    data = {
        "inventory_snapshot_sha256": stable_file_hash(INVENTORY_PATH),
        "matched_stocks": matched,
        "resolved_stock_specs": resolved_stock_specs,
        "issues": issues,
        "active_impact": active_impact,
        "active_impact_by_inventory_material": active_impact_by_inventory_material,
    }
    if issues:
        names = sorted(str(issue["material"]) for issue in issues)
        return PreflightCheck(
            "inventory_stock_contract",
            "FAIL",
            f"{len(issues)} material stock contract failure(s): {', '.join(names)}",
            data,
        )
    return PreflightCheck(
        "inventory_stock_contract",
        "PASS",
        "Every formula row resolves uniquely to a declared live inventory stock.",
        data,
    )


def resolve_inventory_stock_contract(formula: Mapping[str, Any]) -> PreflightCheck:
    """Public stock-authority boundary shared by state builders and preflight."""

    return _dilution_consistency_check(formula)


def resolved_stock_specs_for_state(
    formula: Mapping[str, Any],
    stock_contract: PreflightCheck | None = None,
) -> dict[str, dict[str, object]]:
    """Merge formula declarations with uniquely resolved live-stock semantics."""

    merged = {
        str(name): dict(spec or {})
        for name, spec in (formula.get("stock_specs", {}) or {}).items()
    }
    contract = stock_contract or resolve_inventory_stock_contract(formula)
    for name, spec in dict(contract.data.get("resolved_stock_specs", {}) or {}).items():
        merged[str(name)] = dict(spec or {})
    return merged


def _quantitative_authority_check(
    state: FormulaState,
    *,
    require_exact_ppm: bool,
    require_exact_finished_product_ppm: bool = False,
) -> PreflightCheck:
    authority = state.quantitative_authority
    concentrate_ready = state.exact_mass_ppm_available
    finished_ready = state.exact_finished_product_ppm_available
    if concentrate_ready and (
        finished_ready or not require_exact_finished_product_ppm
    ):
        return PreflightCheck(
            "quantitative_authority",
            "PASS",
            "Exact active concentrate ppm w/w is available; headspace OAV remains modeled.",
            authority,
        )
    status = (
        "FAIL"
        if require_exact_ppm or require_exact_finished_product_ppm
        else "WARN"
    )
    if require_exact_finished_product_ppm and not finished_ready:
        detail = (
            "Exact finished-product ppm w/w is unavailable; commercial safety/release claims are blocked."
        )
    elif require_exact_ppm:
        detail = (
            "Exact active concentrate ppm w/w is unavailable; quantitative/release claims are blocked."
        )
    else:
        detail = (
            "Exact active concentrate ppm w/w is unavailable; OAV is an estimated diagnostic only."
        )
    return PreflightCheck("quantitative_authority", status, detail, authority)


def _headspace_scope_check(
    state: FormulaState,
    *,
    require_finished_product_scope: bool,
) -> PreflightCheck:
    basis = state.headspace_basis
    data = {
        "headspace_basis": basis,
        "matrix_source": state.matrix_source,
        "matrix_moles": state.matrix_moles,
        "stock_carrier_inclusion": state.stock_carrier_inclusion,
        "model_class": "HEURISTIC_NOT_MEASURED",
    }
    if basis == "MODELED_FINISHED_PRODUCT_EXPLICIT_MATRIX":
        return PreflightCheck(
            "headspace_scope",
            "PASS",
            "Modeled headspace uses the explicitly supplied finished-product matrix; it remains a heuristic, not measured headspace.",
            data,
        )
    if require_finished_product_scope:
        return PreflightCheck(
            "headspace_scope",
            "FAIL",
            "Finished-product headspace was requested, but the complete solvent and diluted-stock carrier matrix is not explicit.",
            data,
        )
    if basis == "MODELED_ACTIVE_CONCENTRATE_SCREEN":
        detail = (
            "Headspace/OAV is an active-concentrate screening model; the finished ethanol-water-solvent matrix is omitted."
        )
    else:
        detail = (
            "Headspace/OAV uses a partial or proxy finished matrix; unresolved stock carriers prevent complete finished-product scope."
        )
    return PreflightCheck("headspace_scope", "WARN", detail, data)


def _natural_composite_coverage_check(state: FormulaState) -> PreflightCheck:
    missing = sorted(
        material.name
        for material in state.materials
        if material.sources.get("oav_model") == "unknown:composite_decomposition_missing"
        and not material.is_opaque_preblend
    )
    if missing:
        return PreflightCheck(
            "natural_composite_coverage",
            "FAIL",
            "Natural mixtures lack required composite GC-O decomposition: "
            + ", ".join(missing),
            {"materials": missing},
        )
    return PreflightCheck(
        "natural_composite_coverage",
        "PASS",
        "Every natural mixture uses the composite OAV model.",
    )


def _state_sanity_check(state: FormulaState) -> PreflightCheck:
    unknown = sorted(material.name for material in state.materials if not material.is_known)
    missing_odt = sorted(material.name for material in state.materials if material.odt_air_ppm is None)
    missing_physics = {
        material.name: sorted(material.missing_fields)
        for material in state.materials
        if material.missing_fields
    }
    if unknown or missing_odt:
        detail = []
        if unknown:
            detail.append(f"unknown={len(unknown)}")
        if missing_odt:
            detail.append(f"missing_odt={len(missing_odt)}")
        return PreflightCheck(
            "material_identity_and_physics",
            "FAIL",
            "; ".join(detail),
            {"unknown_materials": unknown, "missing_odt": missing_odt, "missing_fields": missing_physics},
        )
    if missing_physics:
        return PreflightCheck(
            "material_identity_and_physics",
            "WARN",
            f"{len(missing_physics)} materials have non-critical missing fields.",
            {"missing_fields": missing_physics},
        )
    return PreflightCheck(
        "material_identity_and_physics",
        "PASS",
        f"{len(state.materials)} materials resolved with ODT and core physics data.",
    )


def run_release_preflight(
    formula: Mapping[str, Any],
    state: FormulaState,
    *,
    require_exact_ppm: bool = False,
    require_exact_finished_product_ppm: bool = False,
    stock_contract: PreflightCheck | None = None,
) -> PreflightReport:
    checks: list[PreflightCheck] = []
    total_penalty = 0.0
    checks.append(_input_normalization_check(formula))
    checks.append(stock_contract or resolve_inventory_stock_contract(formula))
    checks.append(_schema_check())
    checks.append(_literature_check())
    knowledge_check, knowledge_penalty = _knowledge_rule_quality_check()
    checks.append(knowledge_check)
    total_penalty += knowledge_penalty
    odt_check, odt_penalty = _odt_authority_check(state)
    checks.append(odt_check)
    total_penalty += odt_penalty
    authority_check, authority_penalty = _data_authority_check(state)
    checks.append(authority_check)
    total_penalty += authority_penalty
    science_check, science_penalty = _science_check()
    checks.append(science_check)
    total_penalty += science_penalty
    checks.append(_state_sanity_check(state))
    checks.append(
        _quantitative_authority_check(
            state,
            require_exact_ppm=require_exact_ppm,
            require_exact_finished_product_ppm=require_exact_finished_product_ppm,
        )
    )
    checks.append(
        _headspace_scope_check(
            state,
            require_finished_product_scope=require_exact_finished_product_ppm,
        )
    )
    checks.append(_natural_composite_coverage_check(state))

    warnings = tuple(check.detail for check in checks if check.status == "WARN")
    return PreflightReport(
        status=_status_from_checks(checks),
        checks=tuple(checks),
        confidence_penalty=round(total_penalty, 3),
        warnings=warnings,
    )
