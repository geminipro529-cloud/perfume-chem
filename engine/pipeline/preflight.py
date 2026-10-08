"""Release-pipeline preflight checks.

Preflight is intentionally narrower than the full gate stack. It verifies that
the pipeline's inputs and runtime doctrine are coherent enough to trust the
subsequent OAV/gate analysis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from math import isclose, isfinite
from typing import Any, Mapping

from engine.calibration.hashing import (
    formula_hash_from_record,
    stable_file_hash,
    stable_json_hash,
)
from engine.inventory_parser import (
    CURRENT_INVENTORY_ALIAS_CROSSWALK_SHA256,
    CURRENT_INVENTORY_AUTHORITY,
    CURRENT_INVENTORY_SNAPSHOT_PATH,
    CURRENT_INVENTORY_WORKBOOK_SHA256,
    live_inventory_text_binding,
    load_current_inventory_alias_crosswalk,
    parse_current_inventory,
)
from engine.knowledge.literature_rules import (
    build_knowledge_rule_quality_contract,
    build_literature_rule_contract,
)
from engine.name_utils import normalize_name
from engine.odt_verifier import verify_entry
from engine.pipeline.formula_state import FormulaState
from engine.schema_validator import KG_DIR, SchemaValidator


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    name: str
    status: str
    detail: str
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "check_name": self.name,
            "status": self.status,
            "detail": self.detail,
        }
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


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DOSE_RECEIPT_SCHEMA = "formula-dose-receipt-v1"


@dataclass(frozen=True, slots=True)
class FormulaDoseLineReceipt:
    """One immutable planned-volume dose bound to one exact physical stock."""

    material_name: str
    raw_ul: float
    active_ul: float | None
    stock_fraction: float | None
    fraction_basis: str
    carrier: str
    stock_id: str | None
    stock_authority: str | None
    inventory_authority: str | None
    source_rows: tuple[int, ...]
    status: str
    source_ref: str = ""
    blockers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        name = str(self.material_name).strip()
        if not name:
            raise ValueError("dose receipt material_name must not be blank")
        raw_ul = float(self.raw_ul)
        if not isfinite(raw_ul) or raw_ul <= 0.0:
            raise ValueError(f"{name}: dose receipt raw_ul must be finite and positive")
        if self.stock_fraction is None:
            fraction = None
        else:
            fraction = float(self.stock_fraction)
            if not isfinite(fraction) or not 0.0 < fraction <= 1.0:
                raise ValueError(f"{name}: dose receipt stock_fraction must be in (0, 1]")
        if self.active_ul is None:
            active_ul = None
        else:
            active_ul = float(self.active_ul)
            if not isfinite(active_ul) or active_ul < 0.0:
                raise ValueError(f"{name}: dose receipt active_ul must be finite and nonnegative")
        status = str(self.status).strip().upper()
        if status not in {"BOUND", "ABSTAINED"}:
            raise ValueError(f"{name}: dose receipt line status is invalid")
        blockers = tuple(sorted({str(item).strip() for item in self.blockers if str(item).strip()}))
        source_rows = tuple(sorted({int(value) for value in self.source_rows}))
        source_ref = str(self.source_ref or "").strip()
        if status == "BOUND":
            required = (
                fraction,
                active_ul,
                str(self.stock_id or "").strip(),
                str(self.stock_authority or "").strip(),
                str(self.inventory_authority or "").strip(),
            )
            if any(value in {None, ""} for value in required) or not (
                source_rows or source_ref
            ):
                raise ValueError(f"{name}: bound dose receipt line lacks stock lineage")
            if blockers:
                raise ValueError(f"{name}: bound dose receipt line cannot carry blockers")
            if fraction is None or active_ul is None or not isclose(
                active_ul,
                raw_ul * fraction,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise ValueError(f"{name}: dose receipt active quantity is inconsistent")
        elif not blockers:
            raise ValueError(f"{name}: abstained dose receipt line requires blockers")
        object.__setattr__(self, "material_name", name)
        object.__setattr__(self, "raw_ul", raw_ul)
        object.__setattr__(self, "active_ul", active_ul)
        object.__setattr__(self, "stock_fraction", fraction)
        object.__setattr__(self, "fraction_basis", str(self.fraction_basis).strip())
        object.__setattr__(self, "carrier", str(self.carrier).strip())
        object.__setattr__(self, "stock_id", str(self.stock_id).strip() if self.stock_id else None)
        object.__setattr__(
            self,
            "stock_authority",
            str(self.stock_authority).strip() if self.stock_authority else None,
        )
        object.__setattr__(
            self,
            "inventory_authority",
            str(self.inventory_authority).strip() if self.inventory_authority else None,
        )
        object.__setattr__(self, "source_rows", source_rows)
        object.__setattr__(self, "source_ref", source_ref)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "blockers", blockers)

    def as_dict(self) -> dict[str, Any]:
        return {
            "material_name": self.material_name,
            "raw_ul": self.raw_ul,
            "active_ul": self.active_ul,
            "stock_fraction": self.stock_fraction,
            "fraction_basis": self.fraction_basis,
            "carrier": self.carrier,
            "stock_id": self.stock_id,
            "stock_authority": self.stock_authority,
            "inventory_authority": self.inventory_authority,
            "source_rows": list(self.source_rows),
            "source_ref": self.source_ref,
            "status": self.status,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True, slots=True)
class FormulaDoseReceipt:
    """Content-addressed V5 stock/dose identity for one formula input."""

    formula_name: str
    formula_input_sha256: str
    legacy_formula_hash: str
    inventory_snapshot_sha256: str
    inventory_source_workbook_sha256: str
    inventory_authority_sheet: str
    lines: tuple[FormulaDoseLineReceipt, ...]
    status: str
    reasons: tuple[str, ...]
    receipt_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        formula_name = str(self.formula_name).strip()
        if not formula_name:
            raise ValueError("dose receipt formula_name must not be blank")
        for value, label in (
            (self.formula_input_sha256, "formula_input_sha256"),
            (self.legacy_formula_hash, "legacy_formula_hash"),
            (self.inventory_snapshot_sha256, "inventory_snapshot_sha256"),
            (
                self.inventory_source_workbook_sha256,
                "inventory_source_workbook_sha256",
            ),
        ):
            if not _SHA256_RE.fullmatch(str(value)):
                raise ValueError(f"dose receipt {label} must be lowercase SHA-256")
        lines = tuple(sorted(self.lines, key=lambda row: row.material_name.casefold()))
        if not lines:
            raise ValueError("dose receipt requires at least one positive dose line")
        if len({line.material_name.casefold() for line in lines}) != len(lines):
            raise ValueError("dose receipt material names must be unique")
        status = str(self.status).strip().upper()
        reasons = tuple(sorted({str(item).strip() for item in self.reasons if str(item).strip()}))
        if status == "BOUND":
            if reasons or any(line.status != "BOUND" for line in lines):
                raise ValueError("bound dose receipt cannot contain unresolved lines")
        elif status == "ABSTAINED":
            if not reasons:
                raise ValueError("abstained dose receipt requires a reason")
        else:
            raise ValueError("dose receipt status must be BOUND or ABSTAINED")
        object.__setattr__(self, "formula_name", formula_name)
        object.__setattr__(self, "inventory_authority_sheet", str(self.inventory_authority_sheet).strip())
        object.__setattr__(self, "lines", lines)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "reasons", reasons)
        object.__setattr__(self, "receipt_sha256", stable_json_hash(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": _DOSE_RECEIPT_SCHEMA,
            "formula_name": self.formula_name,
            "formula_input_sha256": self.formula_input_sha256,
            "legacy_formula_hash": self.legacy_formula_hash,
            "inventory_snapshot_sha256": self.inventory_snapshot_sha256,
            "inventory_source_workbook_sha256": self.inventory_source_workbook_sha256,
            "inventory_authority_sheet": self.inventory_authority_sheet,
            "lines": [line.as_dict() for line in self.lines],
            "status": self.status,
            "reasons": list(self.reasons),
            "quantity_authority": "PLANNED_VOLUME_SCREEN_ONLY",
            "physical_metrology_authority": False,
            "release_authority": False,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._payload(), "receipt_sha256": self.receipt_sha256}


def _formula_input_sha256(formula: Mapping[str, Any]) -> str:
    """Hash the exact caller projection without inventing omitted concentrations."""

    stock_fields = (
        "fraction",
        "fraction_basis",
        "carrier",
        "approximate",
        "declared",
        "stock_id",
    )
    stock_specs = {
        str(name): {
            field_name: (spec or {}).get(field_name)
            for field_name in stock_fields
            if field_name in (spec or {})
        }
        for name, spec in sorted(
            dict(formula.get("stock_specs", {}) or {}).items(),
            key=lambda item: str(item[0]).casefold(),
        )
    }
    return stable_json_hash(
        {
            "schema": "formula-dose-input-v1",
            "formula_name": str(formula.get("name", "Formula")),
            "formula_uid": str(formula.get("formula_uid", "")),
            "ingredients_ul": {
                str(name): float(value or 0.0)
                for name, value in sorted(
                    dict(formula.get("ingredients_ul", {}) or {}).items(),
                    key=lambda item: str(item[0]).casefold(),
                )
            },
            "explicit_dilutions": {
                str(name): (None if value is None else float(value))
                for name, value in sorted(
                    dict(formula.get("dilutions", {}) or {}).items(),
                    key=lambda item: str(item[0]).casefold(),
                )
            },
            "input_stock_specs": stock_specs,
        }
    )


def _status_from_checks(checks: list[PreflightCheck]) -> str:
    if any(check.status == "FAIL" for check in checks):
        return "FAIL"
    if any(check.status == "WARN" for check in checks):
        return "WARN"
    return "PASS"


def _same_stock_fraction(formula_fraction: float, stock_fraction: float) -> bool:
    """Whether a declared stock fraction names the same physical stock strength.

    The tolerance is 0.005 absolute for stocks of 10% and stronger, as before,
    and 5% relative below that, so trace stocks (0.01%, 0.1%, 0.5%, 1%) no longer
    match a neighbour five or ten times stronger or weaker.
    """

    tolerance = min(0.005, 0.05 * max(abs(formula_fraction), abs(stock_fraction)))
    return abs(formula_fraction - stock_fraction) <= tolerance


def _literal_inventory_key(name: str) -> str:
    """Normalize only spaces/case (no alias expansion)."""
    return " ".join((name or "").strip().lower().split())


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


def _schema_source_fingerprint() -> tuple[tuple[str, int, int], ...]:
    records: list[tuple[str, int, int]] = []
    for name in (
        "material_properties.json",
        "pairing_rules.json",
        "synergy_matrix.json",
        "theory_rules.json",
    ):
        path = KG_DIR / name
        try:
            stat = path.stat()
        except OSError:
            records.append((name, -1, -1))
        else:
            records.append((name, int(stat.st_mtime_ns), int(stat.st_size)))
    return tuple(records)


@lru_cache(maxsize=8)
def _cached_schema_summary(
    source_fingerprint: tuple[tuple[str, int, int], ...],
) -> dict[str, Any]:
    del source_fingerprint
    return SchemaValidator().validate_all().summary()


def _schema_check() -> PreflightCheck:
    cached = _cached_schema_summary(_schema_source_fingerprint())
    summary = {**cached, "stats": dict(cached.get("stats", {}))}
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


def _knowledge_rule_quality_check(state: FormulaState) -> tuple[PreflightCheck, float]:
    # Use precisely the ingredient keys supplied by _gate_confidence to its
    # FormulaVector/ConfidenceScorer, including any zero rows the scorer sees.
    contract = build_knowledge_rule_quality_contract(
        formula_material_names=state.raw_percentages(),
    ).as_dict()
    contract["scope"] = contract["details"]["scope"]
    contract["catalogue_context"] = contract["details"].pop("catalogue_context")
    status = contract["status"]
    if status == "FAIL":
        detail = "Structured rule evidence is not usable; see scoped findings."
    elif status == "WARN":
        detail = "Structured rule evidence needs review; see consumption and catalog findings."
    else:
        detail = "Consumed formula rule evidence passed viability screening."
    penalty = 0.0
    penalty += min(4.0, float(contract.get("invalid_entries", 0) or 0) * 0.25)
    penalty += min(2.0, float(contract.get("generic_material_refs", 0) or 0) * 0.01)
    contract["confidence_penalty"] = round(penalty, 3)
    return (
        PreflightCheck("knowledge_rule_quality", status, detail, contract),
        round(penalty, 3),
    )


def _science_check(state: FormulaState) -> tuple[PreflightCheck, float]:
    """Report formula-scoped model coverage without importing catalogue gaps.

    Dedicated ODT, data-authority, and state-sanity checks own release
    confidence.  The catalogue audit remains useful project-health context but
    has no authority to penalize a formula that does not use its sparse rows.
    """
    materials = tuple(state.materials)
    denominator = max(len(materials), 1)

    def coverage(predicate) -> float:
        return round(
            100.0 * sum(1 for material in materials if predicate(material))
            / denominator,
            3,
        )

    runtime_coverage = {
        "known_identity_pct": coverage(lambda material: material.is_known),
        "mw_available_pct": coverage(
            lambda material: material.mw_g_mol is not None
            and material.mw_g_mol > 0.0
        ),
        "vp_available_pct": coverage(
            lambda material: material.vp_pure_pa is not None
            and material.vp_pure_pa > 0.0
        ),
        "odt_available_pct": coverage(
            lambda material: material.odt_air_ppm is not None
            and material.odt_air_ppm > 0.0
        ),
        "oav_available_pct": coverage(lambda material: material.oav is not None),
        "hsp_available_pct": coverage(lambda material: material.hsp is not None),
        "ifra_structured_pct": coverage(
            lambda material: material.ifra_limit_pct is not None
        ),
    }
    core_fields = (
        "known_identity_pct",
        "mw_available_pct",
        "vp_available_pct",
        "odt_available_pct",
    )
    core_complete = all(runtime_coverage[field] >= 100.0 for field in core_fields)
    status = "PASS" if core_complete else "WARN"
    detail = (
        "Formula runtime coverage is complete for identity, MW, VP, and ODT; "
        "optional axes remain explicitly advisory."
        if core_complete
        else "Formula runtime has missing core inputs; dedicated fail-closed checks own the release verdict."
    )
    return (
        PreflightCheck(
            "science_coverage",
            status,
            detail,
            {
                "scope": "formula_runtime",
                "material_count": len(materials),
                "runtime_input_coverage_pct": runtime_coverage,
                "catalogue_context": {
                    "scope": "full_material_catalogue",
                    "evaluated_in_formula_preflight": False,
                    "coverage_report": (
                        "engine.science_audit.build_science_audit_contract"
                    ),
                    "formula_penalty_authority": False,
                },
                "limitations": [
                    "Catalogue completeness is evaluated by project audit, not per formula.",
                    "Missing optional axes remain unsupported; no values are fabricated.",
                ],
                "confidence_penalty": 0.0,
                "penalty_owners": [
                    "odt_authority",
                    "data_authority",
                    "material_identity_and_physics",
                ],
            },
        ),
        0.0,
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

    # This is the only compatibility-label choke point in release preflight.
    # Any missing, stale, or semantically drifted crosswalk raises before a
    # candidate can be selected; bypassing the optional crosswalk elsewhere
    # can only leave an alias unresolved and cannot create inventory state.
    alias_crosswalk = load_current_inventory_alias_crosswalk()
    exact_identity: dict[str, list] = defaultdict(list)
    legacy_identity: dict[str, list] = defaultdict(list)
    literal_identity: dict[str, list] = defaultdict(list)
    for record in parse_current_inventory(
        unique=False,
        include_solvents=True,
        include_unavailable=True,
    ):
        exact_identity[normalize_name(record.identity_name or record.name)].append(record)
        legacy_identity[normalize_name(record.name)].append(record)
        literal_identity[_literal_inventory_key(record.identity_name or record.name)].append(
            record
        )

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
    alias_evidence_by_material: dict[str, dict[str, Any]] = {}
    for name in ingredients:
        formula_label = str(name)
        alias_contract = alias_crosswalk.resolve(formula_label)
        direct_norm = normalize_name(formula_label)
        direct_candidates = (
            exact_identity.get(direct_norm) or legacy_identity.get(direct_norm) or []
        )
        lookup_name = (
            formula_label
            if direct_candidates
            else alias_contract.destination
            if alias_contract
            else formula_label
        )
        if alias_contract:
            alias_evidence_by_material[formula_label] = {
                "inventory_lookup_label": lookup_name,
                "identity_crosswalk_contract_id": alias_contract.contract_id,
            }
        norm = normalize_name(lookup_name)
        candidates = direct_candidates or exact_identity.get(norm) or legacy_identity.get(norm) or []
        if len(candidates) > 1:
            literal_candidates = literal_identity.get(_literal_inventory_key(lookup_name))
            if literal_candidates:
                candidates = literal_candidates
        spec = dict(stock_specs.get(name, {}) or {})
        declared = bool(spec.get("declared", name in dilutions))
        fraction_authority = (
            spec.get("fraction")
            if "fraction" in spec
            else dilutions.get(name)
        )
        if (
            not declared
            or fraction_authority is None
            or (isinstance(fraction_authority, str) and fraction_authority.strip() in {"", "-"})
        ):
            live_projection_complete = False
            issues.append({"material": name, "reason": "stock_fraction_not_declared"})
            continue
        try:
            formula_dil = float(fraction_authority)
        except (TypeError, ValueError):
            live_projection_complete = False
            issues.append({"material": name, "reason": "stock_fraction_invalid"})
            continue
        if not 0.0 < formula_dil <= 1.0:
            live_projection_complete = False
            issues.append({"material": name, "reason": "stock_fraction_out_of_range"})
            continue
        raw_ul = float(ingredients.get(name, 0.0) or 0.0)
        declared_active_ul += raw_ul * formula_dil
        formula_basis = str(spec.get("fraction_basis", "unspecified"))
        formula_carrier = normalize_name(str(spec.get("carrier", "")))
        requested_stock_id = str(spec.get("stock_id", "")).strip()
        if spec.get("conflict"):
            live_projection_complete = False
            issues.append({"material": name, "reason": "conflicting_stock_rows"})
            continue
        if requested_stock_id:
            stock_id_candidates = [
                record for record in candidates if record.stock_id == requested_stock_id
            ]
            if not stock_id_candidates:
                live_projection_complete = False
                issues.append(
                    {
                        "material": name,
                        "reason": "stock_id_not_in_current_inventory",
                        "stock_id": requested_stock_id,
                    }
                )
                continue
            candidates = stock_id_candidates
        if not candidates:
            live_projection_complete = False
            issues.append({"material": name, "reason": "not_in_inventory"})
            continue
        physical_owned = [record for record in candidates if record.status == "owned"]
        owned = [record for record in physical_owned if record.execution_ready]
        requirements = [record for record in candidates if record.requirement_state]
        if physical_owned:
            group_label = (
                physical_owned[0].identity_name
                if physical_owned[0].authority == CURRENT_INVENTORY_AUTHORITY
                else physical_owned[0].name
            )
        else:
            group_label = candidates[0].identity_name or candidates[0].name
        group = grouped_active_impact.setdefault(
            group_label,
            {
                "declared_active_ul": 0.0,
                "projected_live_active_ul": 0.0,
                "live_projection_complete": True,
            },
        )
        group["declared_active_ul"] += raw_ul * formula_dil
        physical_fraction_matches = [
            record
            for record in physical_owned
            if _same_stock_fraction(formula_dil, record.dilution)
        ]
        fraction_matches = [
            record for record in physical_fraction_matches if record.execution_ready
        ]
        held_fraction_matches = [
            record for record in physical_fraction_matches if not record.execution_ready
        ]
        if not owned:
            matching_requirements = [
                record
                for record in requirements
                if _same_stock_fraction(formula_dil, record.dilution)
            ]
            requirement_states = {
                record.requirement_state for record in matching_requirements
            }
            if "PREPARATION_REQUIRED" in requirement_states:
                reason = "preparation_required"
            elif "GAP" in requirement_states:
                reason = "inventory_gap"
            elif any(record.execution_hold_reason for record in physical_owned):
                reason = "inventory_stock_non_executable"
            elif physical_owned:
                reason = "inventory_stock_metadata_incomplete"
            else:
                reason = "inventory_stock_unavailable"
            if len(owned) == 1:
                projected_live_active_ul += raw_ul * owned[0].dilution
                group["projected_live_active_ul"] += raw_ul * owned[0].dilution
            else:
                live_projection_complete = False
                group["live_projection_complete"] = False
            issues.append(
                {
                    "material": name,
                    "reason": reason,
                    "statuses": sorted({record.status for record in candidates}),
                    "source_rows": sorted(
                        {
                            row
                            for record in matching_requirements or physical_owned
                            for row in record.source_rows
                        }
                    ),
                    "execution_holds": sorted(
                        {
                            record.execution_hold_reason
                            for record in physical_owned
                            if record.execution_hold_reason
                        }
                    ),
                    # An owned-but-held stock at another strength is a wrong
                    # strength, not only missing data; the gate needs to know.
                    "fraction_matches_formula": bool(physical_fraction_matches),
                    "formula_dilution": round(formula_dil, 6),
                    # Each held stock's recorded fraction (None when none is
                    # recorded); for a tincture this is its starting charge.
                    "held_stock_strengths": [
                        {
                            "execution_hold": record.execution_hold_reason,
                            "fraction": (
                                round(record.dilution, 6) if record.dilution > 0 else None
                            ),
                            "fraction_basis": record.fraction_basis,
                        }
                        for record in physical_owned
                        if record.execution_hold_reason
                    ],
                }
            )
            continue

        if held_fraction_matches and not fraction_matches:
            matching_requirements = [
                record
                for record in requirements
                if _same_stock_fraction(formula_dil, record.dilution)
            ]
            requirement_states = {
                record.requirement_state for record in matching_requirements
            }
            if "PREPARATION_REQUIRED" in requirement_states:
                reason = "preparation_required"
            elif "GAP" in requirement_states:
                reason = "inventory_gap"
            elif any(record.execution_hold_reason for record in held_fraction_matches):
                reason = "inventory_stock_non_executable"
            else:
                reason = "inventory_stock_metadata_incomplete"
            if len(owned) == 1:
                projected_live_active_ul += raw_ul * owned[0].dilution
                group["projected_live_active_ul"] += raw_ul * owned[0].dilution
            else:
                live_projection_complete = False
                group["live_projection_complete"] = False
            issues.append(
                {
                    "material": name,
                    "reason": reason,
                    "statuses": sorted({record.status for record in candidates}),
                    "source_rows": sorted(
                        {
                            row
                            for record in matching_requirements or held_fraction_matches
                            for row in record.source_rows
                        }
                    ),
                    "execution_holds": sorted(
                        {
                            record.execution_hold_reason
                            for record in held_fraction_matches
                            if record.execution_hold_reason
                        }
                    ),
                    "fraction_matches_formula": True,
                }
            )
            continue

        if not fraction_matches:
            matching_requirements = [
                record
                for record in requirements
                if _same_stock_fraction(formula_dil, record.dilution)
            ]
            requirement_states = {
                record.requirement_state for record in matching_requirements
            }
            live_dilutions = sorted({round(record.dilution, 6) for record in owned})
            multipliers = [
                round(record.dilution / formula_dil, 4)
                for record in owned
                if formula_dil > 0
            ]
            if "PREPARATION_REQUIRED" in requirement_states:
                reason = "preparation_required"
            elif "GAP" in requirement_states:
                reason = "inventory_gap"
            else:
                reason = "stock_fraction_mismatch"
            if len(owned) == 1:
                projected_live_active_ul += raw_ul * owned[0].dilution
                group["projected_live_active_ul"] += raw_ul * owned[0].dilution
            else:
                live_projection_complete = False
                group["live_projection_complete"] = False
            issues.append(
                {
                    "material": name,
                    "reason": reason,
                    "formula_dilution": round(formula_dil, 6),
                    "inventory_dilutions": live_dilutions,
                    "active_multiplier_if_live_stock_used": multipliers,
                    "requirement_source_rows": sorted(
                        {
                            row
                            for record in matching_requirements
                            for row in record.source_rows
                        }
                    ),
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
            live_projection_complete = False
            group["live_projection_complete"] = False
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
            live_projection_complete = False
            group["live_projection_complete"] = False
            issues.append(
                {
                    "material": name,
                    "reason": "ambiguous_live_stock",
                    "variants": [
                        {"stock_id": record.stock_id, "raw_name": record.raw_name}
                        for record in compatible
                    ],
                }
            )
            continue
        record = compatible[0]
        projected_live_active_ul += raw_ul * record.dilution
        group["projected_live_active_ul"] += raw_ul * record.dilution
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
            "stock_id": record.stock_id,
            "authority": "formula_row+inventory_snapshot",
            "inventory_authority": record.authority,
            "source_rows": list(record.source_rows),
            "source_ref": record.source_ref,
            "identity_crosswalk_contract_id": (
                alias_contract.contract_id if alias_contract else None
            ),
            "identity_crosswalk_sha256": (
                alias_crosswalk.crosswalk_sha256 if alias_contract else None
            ),
        }
        matched.append(
            {
                "material": name,
                "inventory_lookup_label": lookup_name,
                "inventory_identity": record.identity_name or record.name,
                "fraction": record.dilution,
                "fraction_basis": record.fraction_basis,
                "carrier": record.carrier,
                "stock_id": record.stock_id,
                "authority": record.authority,
                "source_rows": list(record.source_rows),
                "identity_crosswalk_contract_id": (
                    alias_contract.contract_id if alias_contract else None
                ),
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
            declared_amount = float(raw_impact["declared_active_ul"])
            impact.update(
                {
                    "projected_live_active_ul": round(projected, 6),
                    "active_multiplier_if_live_stocks_used": (
                        round(projected / declared_amount, 6)
                        if declared_amount > 0
                        else None
                    ),
                }
            )
        active_impact_by_inventory_material[material] = impact
    for blocker in list(formula.get("row_parse_blockers", []) or []):
        # The parser held this row out of ingredients_ul because a strength or
        # amount cell could not be read; it must not pass as a smaller formula.
        issues.append(
            {
                "material": str(blocker.get("material", "")),
                "reason": "formula_row_unreadable",
                "field": str(blocker.get("field", "")),
                "cell": str(blocker.get("cell", "")),
                "message": str(blocker.get("message", "")),
            }
        )
    for issue in issues:
        issue.update(alias_evidence_by_material.get(str(issue.get("material")), {}))
    data = {
        "inventory_snapshot_sha256": stable_file_hash(CURRENT_INVENTORY_SNAPSHOT_PATH),
        "inventory_source_workbook_sha256": CURRENT_INVENTORY_WORKBOOK_SHA256,
        "inventory_alias_crosswalk_sha256": CURRENT_INVENTORY_ALIAS_CROSSWALK_SHA256,
        "inventory_authority_sheet": "Current Inventory Master",
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


def build_formula_dose_receipt(
    formula: Mapping[str, Any],
    stock_contract: PreflightCheck | None = None,
) -> FormulaDoseReceipt:
    """Freeze the exact formula/V5 stock projection into one tamper-evident receipt."""

    contract = stock_contract or resolve_inventory_stock_contract(formula)
    contract_data = dict(contract.data or {})
    resolved_specs = {
        str(name): dict(spec or {})
        for name, spec in dict(contract_data.get("resolved_stock_specs", {}) or {}).items()
    }
    input_specs = {
        str(name): dict(spec or {})
        for name, spec in dict(formula.get("stock_specs", {}) or {}).items()
    }
    explicit_dilutions = dict(formula.get("dilutions", {}) or {})
    issues_by_material: dict[str, list[str]] = {}
    for issue in list(contract_data.get("issues", []) or []):
        material = str(issue.get("material", "")).strip()
        reason = str(issue.get("reason", "inventory_stock_contract_failed")).strip()
        if material:
            issues_by_material.setdefault(material.casefold(), []).append(reason)

    lines: list[FormulaDoseLineReceipt] = []
    receipt_reasons: list[str] = []
    for raw_name, raw_value in sorted(
        dict(formula.get("ingredients_ul", {}) or {}).items(),
        key=lambda item: str(item[0]).casefold(),
    ):
        name = str(raw_name)
        raw_ul = float(raw_value or 0.0)
        if raw_ul <= 0.0:
            continue
        resolved = dict(resolved_specs.get(name, {}) or {})
        fallback = dict(input_specs.get(name, {}) or {})
        raw_fraction = (
            resolved.get("fraction")
            if "fraction" in resolved
            else fallback.get("fraction")
            if "fraction" in fallback
            else explicit_dilutions.get(name)
        )
        fraction: float | None
        try:
            fraction = None if raw_fraction is None else float(raw_fraction)
        except (TypeError, ValueError):
            fraction = None
        if fraction is not None and (not isfinite(fraction) or not 0.0 < fraction <= 1.0):
            fraction = None

        blockers = list(issues_by_material.get(name.casefold(), ()))
        stock_id = str(resolved.get("stock_id", "")).strip() or None
        stock_authority = str(resolved.get("authority", "")).strip() or None
        inventory_authority = str(resolved.get("inventory_authority", "")).strip() or None
        source_rows = tuple(int(value) for value in list(resolved.get("source_rows", []) or []))
        source_ref = str(resolved.get("source_ref", "")).strip()
        declared = bool(resolved.get("declared", False))
        for condition, reason in (
            (fraction is None, "stock_fraction_not_bound"),
            (not declared, "stock_declaration_not_bound"),
            (not stock_id, "stock_id_not_bound"),
            (
                stock_authority != "formula_row+inventory_snapshot",
                "stock_authority_not_bound",
            ),
            (not inventory_authority, "inventory_authority_not_bound"),
            (
                not source_rows and not source_ref,
                "inventory_source_lineage_not_bound",
            ),
        ):
            if condition:
                blockers.append(reason)
        blockers = sorted(set(blockers))
        # Freeze each line at its own evidence grain.  A different material can
        # hold the formula-wide stock contract without invalidating an exact,
        # fully resolved line.  The receipt itself still abstains unless every
        # line is bound.
        line_status = "BOUND" if not blockers else "ABSTAINED"
        if blockers:
            receipt_reasons.extend(f"{name}:{reason}" for reason in blockers)
        lines.append(
            FormulaDoseLineReceipt(
                material_name=name,
                raw_ul=raw_ul,
                active_ul=(raw_ul * fraction if fraction is not None else None),
                stock_fraction=fraction,
                fraction_basis=str(
                    resolved.get("fraction_basis", fallback.get("fraction_basis", "unspecified"))
                ),
                carrier=str(resolved.get("carrier", fallback.get("carrier", ""))),
                stock_id=stock_id,
                stock_authority=stock_authority,
                inventory_authority=inventory_authority,
                source_rows=source_rows,
                status=line_status,
                source_ref=source_ref,
                blockers=tuple(blockers),
            )
        )

    if contract.status != "PASS" and not receipt_reasons:
        receipt_reasons.append(f"inventory_stock_contract:{contract.status}:{contract.detail}")
    status = (
        "BOUND"
        if contract.status == "PASS"
        and lines
        and all(line.status == "BOUND" for line in lines)
        else "ABSTAINED"
    )
    return FormulaDoseReceipt(
        formula_name=str(formula.get("name", "Formula")),
        formula_input_sha256=_formula_input_sha256(formula),
        legacy_formula_hash=formula_hash_from_record(formula),
        inventory_snapshot_sha256=str(
            contract_data.get("inventory_snapshot_sha256")
            or stable_file_hash(CURRENT_INVENTORY_SNAPSHOT_PATH)
        ),
        inventory_source_workbook_sha256=str(
            contract_data.get("inventory_source_workbook_sha256")
            or CURRENT_INVENTORY_WORKBOOK_SHA256
        ),
        inventory_authority_sheet=str(
            contract_data.get("inventory_authority_sheet") or "Current Inventory Master"
        ),
        lines=tuple(lines),
        status=status,
        reasons=tuple(receipt_reasons),
    )


def _dose_receipt_binding_check(
    state: FormulaState,
    receipt: FormulaDoseReceipt | None,
) -> PreflightCheck:
    if receipt is None:
        return PreflightCheck(
            "formula_dose_receipt",
            "FAIL",
            "Formula state is not bound to an immutable V5 stock/dose receipt.",
        )
    data = receipt.as_dict()
    if receipt.status != "BOUND":
        return PreflightCheck(
            "formula_dose_receipt",
            "FAIL",
            "Formula stock/dose receipt abstained and cannot support release-mode analysis.",
            data,
        )
    if (
        state.dose_receipt_sha256 != receipt.receipt_sha256
        or state.dose_receipt_status != receipt.status
    ):
        return PreflightCheck(
            "formula_dose_receipt",
            "FAIL",
            "Formula state and stock/dose receipt identities do not match.",
            data,
        )
    state_rows = {material.name: material for material in state.materials}
    mismatches: list[str] = []
    for line in receipt.lines:
        material = state_rows.get(line.material_name)
        if material is None:
            mismatches.append(f"{line.material_name}:missing_state_row")
            continue
        if line.stock_fraction is None or line.active_ul is None:
            mismatches.append(f"{line.material_name}:answerless_bound_line")
            continue
        if not isclose(material.raw_ul, line.raw_ul, rel_tol=0.0, abs_tol=1e-12):
            mismatches.append(f"{line.material_name}:raw_ul")
        if not isclose(material.dilution, line.stock_fraction, rel_tol=0.0, abs_tol=1e-12):
            mismatches.append(f"{line.material_name}:stock_fraction")
        if not isclose(material.active_ul, line.active_ul, rel_tol=0.0, abs_tol=1e-12):
            mismatches.append(f"{line.material_name}:active_ul")
        if material.stock_fraction_basis.strip().casefold() != line.fraction_basis.strip().casefold():
            mismatches.append(f"{line.material_name}:stock_fraction_basis")
        if material.stock_carrier.strip().casefold() != line.carrier.strip().casefold():
            mismatches.append(f"{line.material_name}:stock_carrier")
        if material.stock_declared is not True:
            mismatches.append(f"{line.material_name}:stock_declared")
    if mismatches:
        data["state_mismatches"] = mismatches
        return PreflightCheck(
            "formula_dose_receipt",
            "FAIL",
            "Formula state dose quantities and stock semantics do not replay from the bound receipt.",
            data,
        )
    return PreflightCheck(
        "formula_dose_receipt",
        "PASS",
        "Formula state replays exactly from one V5 stock/dose receipt.",
        data,
    )


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
            "Natural mixtures lack a required constituent decomposition: "
            + ", ".join(missing),
            {"materials": missing},
        )
    partial_profiles = [
        {"material": material.name, **material.natural_composite_metadata}
        for material in state.materials
        if material.natural_composite_metadata.get("quantitative_evaluability")
        == "PARTIAL_INPUT_COVERAGE"
    ]
    if partial_profiles:
        return PreflightCheck(
            "natural_composite_coverage",
            "WARN",
            "Partial literature constituent models have unresolved odor contributions; "
            "full quantitative evaluability is not established. "
            + "; ".join(
                f"{profile['material']}: "
                f"{profile['characterized_fraction']:.1%} nominal input coverage"
                + (
                    ", unresolved "
                    + ", ".join(row["name"] for row in profile["unresolved_constituents"])
                    if profile["unresolved_constituents"] else ""
                )
                for profile in partial_profiles
            ),
            {"partial_profiles": partial_profiles, "full_quantitative_evaluability": False},
        )
    return PreflightCheck(
        "natural_composite_coverage",
        "PASS",
        "Constituent models are present for all naturals; complete quantitative coverage is not established by this check.",
    )


def _state_sanity_check(state: FormulaState) -> PreflightCheck:
    unknown = sorted(material.name for material in state.materials if not material.is_known)
    composite_odt_authority = sorted(
        material.name
        for material in state.materials
        if material.odt_air_ppm is None and material.has_odt_authority
    )
    missing_odt = sorted(
        material.name for material in state.materials if not material.has_odt_authority
    )
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
            {
                "unknown_materials": unknown,
                "missing_odt": missing_odt,
                "missing_fields": missing_physics,
                "natural_composite_odt_authority": composite_odt_authority,
            },
        )
    if missing_physics:
        return PreflightCheck(
            "material_identity_and_physics",
            "WARN",
            f"{len(missing_physics)} materials have non-critical missing fields.",
            {
                "missing_fields": missing_physics,
                "natural_composite_odt_authority": composite_odt_authority,
            },
        )
    return PreflightCheck(
        "material_identity_and_physics",
        "PASS",
        f"{len(state.materials)} materials resolved with bulk or constituent ODT authority and core physics data.",
        {"natural_composite_odt_authority": composite_odt_authority},
    )


def _inventory_text_binding_check() -> PreflightCheck:
    """Advise when inventory.txt has drifted from the current overlay; never FAIL or HOLD."""
    binding = live_inventory_text_binding()
    date = binding.get("overlay_effective_date") or "current"
    if binding["bound"]:
        return PreflightCheck(
            "inventory_text_binding",
            "PASS",
            f"inventory.txt matches the text the {date} overlay was recorded against.",
            binding,
        )
    return PreflightCheck(
        "inventory_text_binding",
        "WARN",
        (
            f"inventory.txt has changed since the {date} overlay was recorded "
            f"({binding['actual_size_bytes']} bytes now, {binding['expected_size_bytes']} expected). "
            "The gate's stock comes from the V5 workbook and dated overlays, so edits to "
            "inventory.txt are not in the gate's stock until an overlay records them."
        ),
        binding,
    )


def run_release_preflight(
    formula: Mapping[str, Any],
    state: FormulaState,
    *,
    require_exact_ppm: bool = False,
    require_exact_finished_product_ppm: bool = False,
    stock_contract: PreflightCheck | None = None,
    dose_receipt: FormulaDoseReceipt | None = None,
) -> PreflightReport:
    checks: list[PreflightCheck] = []
    total_penalty = 0.0
    checks.append(_input_normalization_check(formula))
    checks.append(stock_contract or resolve_inventory_stock_contract(formula))
    checks.append(_inventory_text_binding_check())
    checks.append(_dose_receipt_binding_check(state, dose_receipt))
    checks.append(_schema_check())
    checks.append(_literature_check())
    knowledge_check, knowledge_penalty = _knowledge_rule_quality_check(state)
    checks.append(knowledge_check)
    total_penalty += knowledge_penalty
    odt_check, odt_penalty = _odt_authority_check(state)
    checks.append(odt_check)
    total_penalty += odt_penalty
    authority_check, authority_penalty = _data_authority_check(state)
    checks.append(authority_check)
    total_penalty += authority_penalty
    science_check, science_penalty = _science_check(state)
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
