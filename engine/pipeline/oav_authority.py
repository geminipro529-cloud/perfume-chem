"""Canonical OAV-first authority layer for candidate formula analysis.

This module turns a candidate formula into one stable OAV verdict surface using
the existing physical path:

raw dose -> active dose -> headspace ppm -> per-material OAV ->
family-envelope OAV -> time-windowed OAV behavior -> authority verdict
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from engine.pipeline.formula_state import FormulaState, MaterialState, build_formula_state
from engine.pipeline.gates import (
    GateReport,
    GateResult,
    ReleaseGateConfig,
    _gate_oav_legibility,
    _gate_oav_scaling,
    _gate_odt_coverage,
)
from engine.pipeline.oav_intelligence import OAVIntelligenceResult, analyze_oav_intelligence
from engine.pipeline.preflight import (
    resolve_inventory_stock_contract,
    resolved_stock_specs_for_state,
)
from engine.pipeline.robustness import (
    DRIFT_WARN_THRESHOLD,
    PerturbationResult,
    RobustnessReport,
    audit_formula_robustness,
)
from engine.pipeline.simulator import (
    DEFAULT_WINDOWS,
    SimulationFrame,
    _with_default_ethanol_fill,
    simulate_formula,
)


def _formula_record_from_request(request: "OAVAuthorityRequest") -> dict[str, Any]:
    total = sum(float(v or 0.0) for v in request.ingredients_ul.values()) or 1.0
    return {
        "number": 1,
        "name": request.formula_name,
        "body": request.formula_name,
        "family_archetype": request.family_archetype,
        "ingredients_ul": {
            str(name): float(amount or 0.0) for name, amount in request.ingredients_ul.items()
        },
        "ingredients_pct": {
            str(name): float(amount or 0.0) / total * 100.0
            for name, amount in request.ingredients_ul.items()
        },
        "dilutions": {str(name): float(value or 1.0) for name, value in request.dilutions.items()},
        "stock_specs": {str(name): dict(spec or {}) for name, spec in request.stock_specs.items()},
    }


def _status_rank(status: str) -> int:
    return {"PASS": 2, "WARN": 1, "FAIL": 0}.get(status, 0)


def _family_key(material: MaterialState) -> str:
    return material.family or material.canonical_name


def _oav_coverage(state: FormulaState, attribute: str) -> dict[str, Any]:
    known = [material for material in state.materials if getattr(material, attribute) is not None]
    unknown = [material for material in state.materials if getattr(material, attribute) is None]
    total_active_ul = sum(float(material.active_ul) for material in state.materials)
    known_active_ul = sum(float(material.active_ul) for material in known)
    total_count = len(state.materials)
    return {
        "status": "COMPLETE" if not unknown else "INCOMPLETE",
        "known_material_count": len(known),
        "unknown_material_count": len(unknown),
        "total_material_count": total_count,
        "material_coverage_fraction": (
            1.0 if total_count == 0 else len(known) / total_count
        ),
        "known_active_ul": known_active_ul,
        "unknown_active_ul": total_active_ul - known_active_ul,
        "total_active_ul": total_active_ul,
        "active_ul_coverage_fraction": (
            1.0 if total_active_ul <= 1e-12 else known_active_ul / total_active_ul
        ),
        "unknown_materials": sorted(material.name for material in unknown),
    }


def _family_envelope(state: FormulaState) -> dict[str, float]:
    """Return known screening-OAV subtotals without substituting for unknown rows."""

    envelope: dict[str, float] = {}
    for material in state.materials:
        if material.screening_oav is None:
            continue
        family = _family_key(material)
        envelope[family] = envelope.get(family, 0.0) + float(material.screening_oav)
    return dict(sorted(envelope.items()))


def _family_envelope_coverage(state: FormulaState) -> dict[str, dict[str, Any]]:
    families: dict[str, list[MaterialState]] = {}
    for material in state.materials:
        families.setdefault(_family_key(material), []).append(material)
    result: dict[str, dict[str, Any]] = {}
    for family, materials in sorted(families.items()):
        known = [material for material in materials if material.screening_oav is not None]
        unknown = [material for material in materials if material.screening_oav is None]
        total_active_ul = sum(float(material.active_ul) for material in materials)
        known_active_ul = sum(float(material.active_ul) for material in known)
        result[family] = {
            "status": "COMPLETE" if not unknown else "INCOMPLETE",
            "known_material_count": len(known),
            "unknown_material_count": len(unknown),
            "total_material_count": len(materials),
            "known_active_ul": known_active_ul,
            "unknown_active_ul": total_active_ul - known_active_ul,
            "active_ul_coverage_fraction": (
                1.0 if total_active_ul <= 1e-12 else known_active_ul / total_active_ul
            ),
            "unknown_materials": sorted(material.name for material in unknown),
        }
    return result


def _dominant_leader(frame: SimulationFrame) -> str | None:
    leaders = frame.dominant_oav(limit=1)
    if not leaders:
        return None
    return str(leaders[0]["material"])


def _known_subliminal_mass_ratio_lower_bound(state: FormulaState) -> float:
    total = state.total_active_ul or 1.0
    return (
        sum(
            material.active_ul
            for material in state.materials
            if material.screening_oav is not None and material.screening_oav < 0.2
        )
        / total
    )


def _subliminal_mass_ratio(state: FormulaState) -> float | None:
    if any(material.screening_oav is None for material in state.materials):
        return None
    return _known_subliminal_mass_ratio_lower_bound(state)


def _known_perceptible_count(state: FormulaState) -> int:
    return sum(
        1
        for material in state.materials
        if material.screening_oav is not None and material.screening_oav >= 1.0
    )


def _perceptible_count(state: FormulaState) -> int | None:
    if any(material.screening_oav is None for material in state.materials):
        return None
    return _known_perceptible_count(state)


def _envelope_drift(base: Mapping[str, float], changed: Mapping[str, float]) -> float:
    families = set(base) | set(changed)
    denom = sum(abs(float(base.get(family, 0.0))) for family in families)
    if denom <= 1e-12:
        return 0.0
    delta = sum(
        abs(float(changed.get(family, 0.0)) - float(base.get(family, 0.0))) for family in families
    )
    return delta / denom


def _max_family_drift(frames: Sequence[SimulationFrame]) -> float:
    if not frames:
        return 0.0
    baseline = _family_envelope(frames[0].state)
    return max(
        (_envelope_drift(baseline, _family_envelope(frame.state)) for frame in frames), default=0.0
    )


def _leaders_changed(frames: Sequence[SimulationFrame]) -> bool:
    leaders = [_dominant_leader(frame) for frame in frames]
    compact = [leader for leader in leaders if leader]
    return len(set(compact)) > 1


def _scaling_issue_counts(result: Mapping[str, Any]) -> tuple[int, int, int]:
    findings = list(result.get("data", {}).get("findings", []))
    errors = sum(1 for row in findings if row.get("severity") == "error")
    warns = sum(1 for row in findings if row.get("severity") == "warn")
    infos = sum(1 for row in findings if row.get("severity") == "info")
    return errors, warns, infos


@dataclass(frozen=True, slots=True)
class OAVAuthorityRequest:
    formula_name: str
    ingredients_ul: Mapping[str, float]
    dilutions: Mapping[str, float] = field(default_factory=dict)
    stock_specs: Mapping[str, Mapping[str, object]] = field(default_factory=dict)
    batch_volume_ml: float = 30.0
    temperature_K: float = 305.0  # noqa: N815
    family_archetype: str = ""
    target_windows: tuple[tuple[str, float], ...] = DEFAULT_WINDOWS
    batch_scaling_targets_ml: tuple[float, ...] = ()
    candidate_metadata: Mapping[str, Any] = field(default_factory=dict)
    context: str = "skin"
    min_perceptible_materials: int = 3
    max_perceptible_channels: int = 30
    matrix_moles: Mapping[str, float] = field(default_factory=dict)
    matrix_mass_g: float = 0.0
    matrix_source: str = "omitted"

    def as_dict(self) -> dict[str, Any]:
        return {
            "formula_name": self.formula_name,
            "ingredients_ul": {str(k): float(v or 0.0) for k, v in self.ingredients_ul.items()},
            "dilutions": {str(k): float(v or 1.0) for k, v in self.dilutions.items()},
            "stock_specs": {str(name): dict(spec or {}) for name, spec in self.stock_specs.items()},
            "batch_volume_ml": float(self.batch_volume_ml),
            "temperature_K": float(self.temperature_K),
            "family_archetype": self.family_archetype,
            "target_windows": [[label, float(seconds)] for label, seconds in self.target_windows],
            "batch_scaling_targets_ml": [float(value) for value in self.batch_scaling_targets_ml],
            "candidate_metadata": dict(self.candidate_metadata),
            "context": self.context,
            "min_perceptible_materials": int(self.min_perceptible_materials),
            "max_perceptible_channels": int(self.max_perceptible_channels),
            "matrix_moles": {str(name): float(value) for name, value in self.matrix_moles.items()},
            "matrix_mass_g": float(self.matrix_mass_g),
            "matrix_source": self.matrix_source,
        }


@dataclass(frozen=True, slots=True)
class OAVMaterialRow:
    name: str
    canonical_name: str
    family: str | None
    note: str
    raw_ul: float
    dilution: float
    active_ul: float
    vapor_ppm: float | None
    odt_air_ppm: float | None
    odt_source: str
    oav: float | None
    intensity: float | None
    physics_status: str
    physics_blockers: tuple[str, ...]
    canonical_vapor_ppm: float | None
    canonical_oav: float | None
    formula_optimization_authority: bool

    @classmethod
    def from_material_state(cls, material: MaterialState) -> "OAVMaterialRow":
        return cls(
            name=material.name,
            canonical_name=material.canonical_name,
            family=material.family,
            note=material.note,
            raw_ul=float(material.raw_ul),
            dilution=float(material.dilution),
            active_ul=float(material.active_ul),
            vapor_ppm=material.screening_vapor_ppm,
            odt_air_ppm=material.odt_air_ppm,
            odt_source=str(material.sources.get("odt", "missing")),
            oav=material.screening_oav,
            intensity=material.screening_intensity,
            physics_status=material.physics_status,
            physics_blockers=material.physics_blockers,
            canonical_vapor_ppm=material.canonical_vapor_ppm,
            canonical_oav=material.canonical_oav,
            formula_optimization_authority=material.formula_optimization_authority,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "canonical_name": self.canonical_name,
            "family": self.family,
            "note": self.note,
            "raw_ul": round(self.raw_ul, 6),
            "dilution": round(self.dilution, 6),
            "active_ul": round(self.active_ul, 6),
            "vapor_ppm": (
                None if self.vapor_ppm is None else round(self.vapor_ppm, 6)
            ),
            "odt_air_ppm": self.odt_air_ppm,
            "odt_source": self.odt_source,
            "oav": None if self.oav is None else round(float(self.oav), 6),
            "intensity": None if self.intensity is None else round(float(self.intensity), 6),
            "physics_status": self.physics_status,
            "physics_blockers": list(self.physics_blockers),
            "canonical_vapor_ppm": self.canonical_vapor_ppm,
            "canonical_oav": self.canonical_oav,
            "formula_optimization_authority": self.formula_optimization_authority,
        }


@dataclass(frozen=True, slots=True)
class OAVTimeWindowSummary:
    label: str
    t_seconds: float
    family_envelope: dict[str, float]
    family_envelope_coverage: dict[str, dict[str, Any]]
    dominant_oav: list[dict[str, Any]]
    perceptible_material_count: int | None
    known_perceptible_material_count: int
    subliminal_mass_ratio: float | None
    known_subliminal_mass_ratio_lower_bound: float
    screening_oav_coverage: dict[str, Any]
    unknown_screening_oav_materials: tuple[str, ...]
    total_vapor_ppm: float | None

    @classmethod
    def from_frame(cls, frame: SimulationFrame) -> "OAVTimeWindowSummary":
        return cls(
            label=frame.label,
            t_seconds=float(frame.t_seconds),
            family_envelope={k: round(v, 6) for k, v in _family_envelope(frame.state).items()},
            family_envelope_coverage=_family_envelope_coverage(frame.state),
            dominant_oav=frame.dominant_oav(),
            perceptible_material_count=_perceptible_count(frame.state),
            known_perceptible_material_count=_known_perceptible_count(frame.state),
            subliminal_mass_ratio=_subliminal_mass_ratio(frame.state),
            known_subliminal_mass_ratio_lower_bound=(
                _known_subliminal_mass_ratio_lower_bound(frame.state)
            ),
            screening_oav_coverage=_oav_coverage(frame.state, "screening_oav"),
            unknown_screening_oav_materials=tuple(
                sorted(
                    material.name
                    for material in frame.state.materials
                    if material.screening_oav is None
                )
            ),
            total_vapor_ppm=frame.state.screening_total_vapor_ppm,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "t_seconds": round(self.t_seconds, 6),
            "family_envelope": dict(self.family_envelope),
            "family_envelope_coverage": dict(self.family_envelope_coverage),
            "dominant_oav": list(self.dominant_oav),
            "perceptible_material_count": self.perceptible_material_count,
            "known_perceptible_material_count": self.known_perceptible_material_count,
            "subliminal_mass_ratio": (
                None
                if self.subliminal_mass_ratio is None
                else round(self.subliminal_mass_ratio, 6)
            ),
            "known_subliminal_mass_ratio_lower_bound": round(
                self.known_subliminal_mass_ratio_lower_bound, 6
            ),
            "screening_oav_coverage": dict(self.screening_oav_coverage),
            "unknown_screening_oav_materials": list(
                self.unknown_screening_oav_materials
            ),
            "total_vapor_ppm": (
                None
                if self.total_vapor_ppm is None
                else round(self.total_vapor_ppm, 6)
            ),
        }


@dataclass(frozen=True, slots=True)
class OAVAuthorityResult:
    request: OAVAuthorityRequest
    state: FormulaState
    material_rows: tuple[OAVMaterialRow, ...]
    time_windows: tuple[OAVTimeWindowSummary, ...]
    odt_coverage: dict[str, Any]
    oav_legibility: dict[str, Any]
    scaling_risk: dict[str, Any]
    robustness: dict[str, Any]
    family_target_alignment: dict[str, Any]
    material_cliff_findings: tuple[dict[str, Any], ...]
    shift_zone_findings: tuple[dict[str, Any], ...]
    balance_reports: tuple[dict[str, Any], ...]
    performance_projection: dict[str, Any]
    synergy_findings: dict[str, Any]
    intelligence_status: str
    intelligence_blocking_reasons: tuple[str, ...]
    intelligence_warning_reasons: tuple[str, ...]
    primary_status: str
    screening_diagnostic_score: float
    authoritative_rank_score: float | None
    authority_rank_status: str
    blocking_reasons: tuple[str, ...]
    warning_reasons: tuple[str, ...]
    dominant_leaders_changed: bool
    top_family_drift: float | None
    screening_top_family_drift: float
    subliminal_mass_ratio: float | None
    known_subliminal_mass_ratio_lower_bound: float
    perceptible_material_count: int | None
    known_perceptible_material_count: int
    screening_oav_coverage: dict[str, Any]
    canonical_oav_coverage: dict[str, Any]
    unknown_screening_oav_materials: tuple[str, ...]
    incomplete_canonical_physics_materials: tuple[str, ...]
    missing_odt_materials: tuple[str, ...]

    @property
    def authority_rank_score(self) -> float:
        """Deprecated numeric compatibility alias; diagnostic-only, never beauty authority."""

        return self.screening_diagnostic_score

    @property
    def authority_verdict_summary(self) -> dict[str, Any]:
        return self.as_dict()["authority_verdict_summary"]

    @property
    def downstream_integration(self) -> dict[str, Any]:
        return self.as_dict()["downstream_integration"]

    @property
    def oav_intelligence(self) -> dict[str, Any]:
        return self.as_dict()["oav_intelligence"]

    def as_dict(self) -> dict[str, Any]:
        current_family_envelope = self.time_windows[0].family_envelope if self.time_windows else {}
        return {
            "request_summary": self.request.as_dict(),
            "current_batch_assumptions": {
                "backend": "engine.pipeline.formula_state + engine.pipeline.simulator",
                "context": self.request.context,
                "batch_volume_ml": round(float(self.request.batch_volume_ml), 6),
                "temperature_K": round(float(self.request.temperature_K), 6),
                "family_archetype": self.request.family_archetype,
                "batch_scaling_targets_ml": [
                    float(value) for value in self.request.batch_scaling_targets_ml
                ],
                "min_perceptible_materials": int(self.request.min_perceptible_materials),
                "max_perceptible_channels": int(self.request.max_perceptible_channels),
                "matrix_components_moles": [
                    [str(name), float(value)]
                    for name, value in sorted(self.request.matrix_moles.items())
                ],
                "matrix_mass_g": float(self.request.matrix_mass_g),
                "matrix_source": self.request.matrix_source,
            },
            "material_oav_table": [row.as_dict() for row in self.material_rows],
            "family_envelope_table": [window.as_dict() for window in self.time_windows],
            "dominant_oav_leaders_by_window": [
                {
                    "label": window.label,
                    "t_seconds": round(window.t_seconds, 6),
                    "leaders": list(window.dominant_oav),
                }
                for window in self.time_windows
            ],
            "oav_intelligence": {
                "family_target_alignment": dict(self.family_target_alignment),
                "material_cliff_findings": [dict(item) for item in self.material_cliff_findings],
                "shift_zone_findings": [dict(item) for item in self.shift_zone_findings],
                "balance_reports": [dict(item) for item in self.balance_reports],
                "performance_projection": dict(self.performance_projection),
                "synergy_findings": {
                    key: [dict(item) for item in value] if isinstance(value, tuple) else value
                    for key, value in self.synergy_findings.items()
                },
                "intelligence_status": self.intelligence_status,
                "intelligence_blocking_reasons": list(self.intelligence_blocking_reasons),
                "intelligence_warning_reasons": list(self.intelligence_warning_reasons),
            },
            "authority_verdict_summary": {
                "primary_status": self.primary_status,
                "eligible_as_measured_evaluator_authority": False,
                "beauty_authorized": False,
                "pleasantness_authorized": False,
                "liking_authorized": False,
                "authority_rank_score": (
                    None
                    if self.authoritative_rank_score is None
                    else round(self.authoritative_rank_score, 6)
                ),
                "authority_rank_status": self.authority_rank_status,
                "screening_diagnostic_score": round(
                    self.screening_diagnostic_score, 6
                ),
                "rank_semantics": "GATE_DIAGNOSTIC_ONLY_NOT_BEAUTY_OR_PLEASANTNESS_AUTHORITY",
                "blocking_reasons": list(self.blocking_reasons),
                "warning_reasons": list(self.warning_reasons),
                "dominant_leaders_changed": self.dominant_leaders_changed,
                "top_family_drift": (
                    None
                    if self.top_family_drift is None
                    else round(self.top_family_drift, 6)
                ),
                "screening_top_family_drift": round(
                    self.screening_top_family_drift, 6
                ),
                "subliminal_mass_ratio": (
                    None
                    if self.subliminal_mass_ratio is None
                    else round(self.subliminal_mass_ratio, 6)
                ),
                "known_subliminal_mass_ratio_lower_bound": round(
                    self.known_subliminal_mass_ratio_lower_bound, 6
                ),
                "perceptible_material_count": self.perceptible_material_count,
                "known_perceptible_material_count": self.known_perceptible_material_count,
                "screening_oav_coverage": dict(self.screening_oav_coverage),
                "canonical_oav_coverage": dict(self.canonical_oav_coverage),
                "unknown_screening_oav_materials": list(
                    self.unknown_screening_oav_materials
                ),
                "incomplete_canonical_physics_materials": list(
                    self.incomplete_canonical_physics_materials
                ),
                "missing_odt_materials": list(self.missing_odt_materials),
                "odt_coverage": dict(self.odt_coverage),
                "oav_legibility": dict(self.oav_legibility),
                "scaling_risk": dict(self.scaling_risk),
                "robustness": dict(self.robustness),
                "intelligence_status": self.intelligence_status,
            },
            "downstream_integration": {
                "status_rank": _status_rank(self.primary_status),
                "coverage_complete": (
                    self.screening_oav_coverage.get("status") == "COMPLETE"
                    and not self.missing_odt_materials
                ),
                "canonical_physics_complete": (
                    self.canonical_oav_coverage.get("status") == "COMPLETE"
                ),
                "perceptible_material_count": self.perceptible_material_count,
                "known_perceptible_material_count": self.known_perceptible_material_count,
                "subliminal_mass_ratio": (
                    None
                    if self.subliminal_mass_ratio is None
                    else round(self.subliminal_mass_ratio, 6)
                ),
                "known_subliminal_mass_ratio_lower_bound": round(
                    self.known_subliminal_mass_ratio_lower_bound, 6
                ),
                "current_family_envelope": dict(current_family_envelope),
                "current_family_envelope_coverage": (
                    dict(self.time_windows[0].family_envelope_coverage)
                    if self.time_windows
                    else {}
                ),
                "top_family_drift": (
                    None
                    if self.top_family_drift is None
                    else round(self.top_family_drift, 6)
                ),
                "screening_top_family_drift": round(
                    self.screening_top_family_drift, 6
                ),
                "dominant_leaders_changed": self.dominant_leaders_changed,
                "scaling_status": self.scaling_risk.get("status", "PASS"),
                "robustness_status": self.robustness.get("status", "PASS"),
                "intelligence_status": self.intelligence_status,
                "authority_rank_score": (
                    None
                    if self.authoritative_rank_score is None
                    else round(self.authoritative_rank_score, 6)
                ),
                "authority_rank_status": self.authority_rank_status,
                "screening_diagnostic_score": round(
                    self.screening_diagnostic_score, 6
                ),
                "screening_oav_coverage": dict(self.screening_oav_coverage),
                "canonical_oav_coverage": dict(self.canonical_oav_coverage),
                "unknown_screening_oav_materials": list(
                    self.unknown_screening_oav_materials
                ),
                "incomplete_canonical_physics_materials": list(
                    self.incomplete_canonical_physics_materials
                ),
            },
        }


def _result_payload(result: Any) -> dict[str, Any]:
    if hasattr(result, "as_dict"):
        return result.as_dict()
    if hasattr(result, "__dict__"):
        return dict(result.__dict__)
    return {}


def _build_gate_config(request: OAVAuthorityRequest) -> ReleaseGateConfig:
    return ReleaseGateConfig(
        batch_volume_ml=float(request.batch_volume_ml),
        temperature_K=float(request.temperature_K),
        brief="generic",
        family_archetype=request.family_archetype,
        batch_scaling_targets_ml=tuple(
            float(v) for v in request.batch_scaling_targets_ml if float(v) > 0
        ),
        min_perceptible_materials=int(request.min_perceptible_materials),
        max_perceptible_channels=int(request.max_perceptible_channels),
        matrix_components_moles=tuple(
            sorted(
                (str(name), float(value))
                for name, value in request.matrix_moles.items()
                if float(value) > 0.0
            )
        ),
        matrix_mass_g=float(request.matrix_mass_g),
        matrix_source=request.matrix_source,
        audit_enabled=False,
    )


def _gate_map(report: GateReport) -> dict[str, GateResult]:
    return {gate.gate: gate for gate in report.gates}


def _robustness_from_gate(gate: GateResult) -> RobustnessReport:
    payload = dict(gate.data or {})

    def rows(key: str) -> tuple[PerturbationResult, ...]:
        return tuple(
            PerturbationResult(
                material=str(row.get("material", "")),
                direction=str(row.get("direction", "")),
                delta_ul=float(row.get("delta_ul", 0.0) or 0.0),
                status=str(row.get("status", "WARN")),
                family_envelope_drift=float(row.get("family_envelope_drift", 0.0) or 0.0),
                top_leader_changed=bool(row.get("top_leader_changed", False)),
                safety_failed=bool(row.get("safety_failed", False)),
                brief_failed=bool(row.get("brief_failed", False)),
                detail=str(row.get("detail", "")),
            )
            for row in list(payload.get(key, []) or [])
        )

    return RobustnessReport(
        status=str(payload.get("status", gate.status)),
        checked=int(payload.get("checked", 0) or 0),
        skipped=int(payload.get("skipped", 0) or 0),
        issues=rows("issues"),
        perturbations=rows("perturbations"),
    )


def _intelligence_from_gate(gate: GateResult) -> OAVIntelligenceResult | None:
    payload = dict(gate.data or {})
    if "intelligence_status" not in payload:
        return None
    return OAVIntelligenceResult(
        family_archetype=str(payload.get("family_archetype", "")),
        mapped_family=(
            str(payload["mapped_family"]) if payload.get("mapped_family") is not None else None
        ),
        family_target_alignment=dict(payload.get("family_target_alignment", {}) or {}),
        material_cliff_findings=tuple(
            dict(row) for row in list(payload.get("material_cliff_findings", []) or [])
        ),
        shift_zone_findings=tuple(
            dict(row) for row in list(payload.get("shift_zone_findings", []) or [])
        ),
        balance_reports=tuple(dict(row) for row in list(payload.get("balance_reports", []) or [])),
        performance_projection=dict(payload.get("performance_projection", {}) or {}),
        synergy_findings=dict(payload.get("synergy_findings", {}) or {}),
        intelligence_status=str(payload.get("intelligence_status", "PASS")),
        intelligence_blocking_reasons=tuple(
            str(value) for value in list(payload.get("intelligence_blocking_reasons", []) or [])
        ),
        intelligence_warning_reasons=tuple(
            str(value) for value in list(payload.get("intelligence_warning_reasons", []) or [])
        ),
        unmapped_materials=tuple(
            str(value) for value in list(payload.get("unmapped_materials", []) or [])
        ),
    )


def _compute_screening_diagnostic_score(
    odt_coverage: Mapping[str, Any],
    oav_legibility: Mapping[str, Any],
    scaling_risk: Mapping[str, Any],
    robustness: Mapping[str, Any],
    intelligence: OAVIntelligenceResult,
    perceptible_count: int,
    subliminal_ratio: float,
    top_family_drift: float,
    missing_odt_materials: Sequence[str],
) -> float:
    score = 100.0
    score -= 18.0 * len(missing_odt_materials)
    if odt_coverage.get("status") == "FAIL":
        score -= 25.0
    elif odt_coverage.get("status") == "WARN":
        score -= 8.0
    if oav_legibility.get("status") == "FAIL":
        score -= 30.0
    elif oav_legibility.get("status") == "WARN":
        score -= 12.0
    scale_errors, scale_warns, scale_infos = _scaling_issue_counts(scaling_risk)
    score -= scale_errors * 18.0
    score -= scale_warns * 8.0
    score -= scale_infos * 2.0
    if robustness.get("status") == "WARN":
        issues = list(robustness.get("issues", []))
        score -= min(18.0, len(issues) * 3.0)
    if perceptible_count < 3:
        score -= 15.0
    else:
        score += min(8.0, (perceptible_count - 3) * 1.5)
    score -= min(20.0, subliminal_ratio * 30.0)
    if top_family_drift > DRIFT_WARN_THRESHOLD:
        score -= min(15.0, (top_family_drift - DRIFT_WARN_THRESHOLD) * 30.0)
    if intelligence.intelligence_status == "FAIL":
        score -= 20.0
    elif intelligence.intelligence_status == "WARN":
        score -= 8.0
    score -= min(18.0, len(intelligence.intelligence_blocking_reasons) * 4.0)
    score -= min(12.0, len(intelligence.intelligence_warning_reasons) * 1.5)
    return max(0.0, min(100.0, score))


def _numeric_mapping_matches(
    actual: Mapping[str, float],
    expected: Mapping[str, float],
) -> bool:
    if set(actual) != set(expected):
        return False
    return all(
        math.isclose(
            float(actual[name]),
            float(expected[name]),
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
        for name in actual
    )


def _matrix_mapping(rows: Any) -> dict[str, float]:
    source = dict(rows or {}) if isinstance(rows, Mapping) else dict(rows or ())
    return {
        str(name): float(value)
        for name, value in source.items()
        if float(value) > 0.0
    }


def _require_close(actual: Any, expected: float, label: str) -> None:
    try:
        matches = math.isclose(
            float(actual),
            float(expected),
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
    except (TypeError, ValueError):
        matches = False
    if not matches:
        raise ValueError(f"Gate report {label} does not match OAV request")


def _validate_gate_report_binding(
    request: OAVAuthorityRequest,
    gate_report: GateReport,
) -> None:
    state = gate_report.formula_state
    frames = tuple(gate_report.simulation)
    expected_windows = tuple(
        (str(label), float(seconds)) for label, seconds in request.target_windows
    )
    actual_windows = tuple((frame.label, frame.t_seconds) for frame in frames)
    if actual_windows != expected_windows:
        raise ValueError("Gate report simulation windows do not match OAV request")

    expected_doses = {
        str(name): float(value or 0.0)
        for name, value in request.ingredients_ul.items()
        if float(value or 0.0) > 0.0
    }
    actual_doses = {material.name: float(material.raw_ul) for material in state.materials}
    if not _numeric_mapping_matches(actual_doses, expected_doses):
        raise ValueError("Gate report formula state does not match OAV request doses")

    expected_dilutions = {
        name: float(request.dilutions.get(name, 1.0)) for name in expected_doses
    }
    actual_dilutions = {
        material.name: float(material.dilution) for material in state.materials
    }
    if not _numeric_mapping_matches(actual_dilutions, expected_dilutions):
        raise ValueError("Gate report dilutions do not match OAV request")

    _require_close(state.batch_volume_ml, request.batch_volume_ml, "batch volume")
    _require_close(state.temperature_K, request.temperature_K, "temperature")
    if str(state.context) != str(request.context):
        raise ValueError("Gate report context does not match OAV request")

    expected_matrix = _matrix_mapping(request.matrix_moles)
    actual_matrix = _matrix_mapping(state.matrix_components_moles)
    if not _numeric_mapping_matches(actual_matrix, expected_matrix):
        raise ValueError("Gate report matrix components do not match OAV request")
    _require_close(state.matrix_mass_g, request.matrix_mass_g, "matrix mass")
    if str(state.matrix_source) != str(request.matrix_source):
        raise ValueError("Gate report matrix source does not match OAV request")

    config_summary = dict(gate_report.config_summary or {})
    required_config_keys = {
        "batch_volume_ml",
        "temperature_K",
        "matrix_components_moles",
        "matrix_mass_g",
        "matrix_source",
        "batch_scaling_targets_ml",
    }
    missing_config_keys = sorted(required_config_keys - set(config_summary))
    if missing_config_keys:
        raise ValueError(
            "Gate report lacks explicit reuse binding for: "
            + ", ".join(missing_config_keys)
        )
    _require_close(
        config_summary["batch_volume_ml"],
        request.batch_volume_ml,
        "config batch volume",
    )
    _require_close(
        config_summary["temperature_K"],
        request.temperature_K,
        "config temperature",
    )
    if not _numeric_mapping_matches(
        _matrix_mapping(config_summary["matrix_components_moles"]),
        expected_matrix,
    ):
        raise ValueError("Gate report config matrix components do not match OAV request")
    _require_close(
        config_summary["matrix_mass_g"],
        request.matrix_mass_g,
        "config matrix mass",
    )
    if str(config_summary["matrix_source"]) != str(request.matrix_source):
        raise ValueError("Gate report config matrix source does not match OAV request")
    expected_scaling_targets = tuple(float(value) for value in request.batch_scaling_targets_ml)
    actual_scaling_targets = tuple(
        float(value) for value in config_summary["batch_scaling_targets_ml"]
    )
    if actual_scaling_targets != expected_scaling_targets:
        raise ValueError("Gate report scaling targets do not match OAV request")

    # Frames start from the temporal start state: the declared matrix, or the
    # default ethanol fill (temporal model v5) when the request declares none.
    start_state, start_assumption = _with_default_ethanol_fill(state)
    frame_expected_matrix = _matrix_mapping(start_state.matrix_components_moles)
    for frame in frames:
        frame_state = frame.state
        if frame.matrix_assumption != start_assumption:
            raise ValueError("Gate report frame matrix assumption does not match OAV request")
        _require_close(frame_state.batch_volume_ml, request.batch_volume_ml, "frame batch volume")
        _require_close(frame_state.temperature_K, request.temperature_K, "frame temperature")
        if str(frame_state.context) != str(request.context):
            raise ValueError("Gate report frame context does not match OAV request")
        frame_matrix = _matrix_mapping(frame_state.matrix_components_moles)
        if float(frame.t_seconds) <= 0.0:
            matrix_matches = _numeric_mapping_matches(frame_matrix, frame_expected_matrix)
        else:
            # The simulated matrix evaporates (diagnosis M1a): later frames
            # carry the requested components at no more than their t=0 moles.
            matrix_matches = set(frame_matrix) <= set(frame_expected_matrix) and all(
                value <= frame_expected_matrix[name] * (1.0 + 1e-12) + 1e-12
                for name, value in frame_matrix.items()
            )
        if not matrix_matches:
            raise ValueError("Gate report frame matrix components do not match OAV request")
        _require_close(frame_state.matrix_mass_g, request.matrix_mass_g, "frame matrix mass")
        if str(frame_state.matrix_source) != str(start_state.matrix_source):
            raise ValueError("Gate report frame matrix source does not match OAV request")
        frame_dilutions = {
            material.name: float(material.dilution)
            for material in frame_state.materials
        }
        if not _numeric_mapping_matches(frame_dilutions, expected_dilutions):
            raise ValueError("Gate report frame dilutions do not match OAV request")


def analyze_oav_authority(
    request: OAVAuthorityRequest,
    *,
    gate_report: GateReport | None = None,
) -> OAVAuthorityResult:
    """Run canonical OAV-first analysis and return an authority verdict surface."""
    formula = _formula_record_from_request(request)
    reused_gates: dict[str, GateResult] = {}
    if gate_report is None:
        stock_contract = resolve_inventory_stock_contract(formula)
        stock_specs = resolved_stock_specs_for_state(formula, stock_contract)
        state = build_formula_state(
            request.ingredients_ul,
            request.dilutions,
            stock_specs=stock_specs,
            batch_volume_ml=float(request.batch_volume_ml),
            temperature_K=float(request.temperature_K),
            context=request.context,
            matrix_moles=request.matrix_moles,
            matrix_mass_g=float(request.matrix_mass_g),
            matrix_source=request.matrix_source,
        )
        frames = simulate_formula(
            request.ingredients_ul,
            request.dilutions,
            batch_volume_ml=float(request.batch_volume_ml),
            temperature_K=float(request.temperature_K),
            context=request.context,
            windows=request.target_windows,
            initial_state=state,
        )
    else:
        state = gate_report.formula_state
        frames = list(gate_report.simulation)
        _validate_gate_report_binding(request, gate_report)
        reused_gates = _gate_map(gate_report)
    material_rows = tuple(
        OAVMaterialRow.from_material_state(material)
        for material in sorted(
            state.materials,
            key=lambda row: (
                row.screening_oav is not None,
                float(row.screening_oav) if row.screening_oav is not None else -math.inf,
                row.name,
            ),
            reverse=True,
        )
    )
    time_windows = tuple(OAVTimeWindowSummary.from_frame(frame) for frame in frames)

    config = _build_gate_config(request)
    odt_gate = reused_gates.get("odt_coverage") or _gate_odt_coverage(state)
    legibility_gate = reused_gates.get("oav_legibility") or _gate_oav_legibility(state, config)
    scaling_gate = (
        reused_gates.get("oav_scaling_guard")
        or reused_gates.get("oav_scaling")
        or _gate_oav_scaling(formula, config)
    )
    robustness_gate = reused_gates.get("robustness_perturbation")
    robustness_report = (
        _robustness_from_gate(robustness_gate)
        if robustness_gate is not None
        else audit_formula_robustness(formula, config)
    )
    intelligence_gate = reused_gates.get("oav_intelligence")
    intelligence = (
        _intelligence_from_gate(intelligence_gate) if intelligence_gate is not None else None
    )
    if intelligence is None:
        intelligence = analyze_oav_intelligence(state, frames, request.family_archetype)

    odt_coverage = _result_payload(odt_gate)
    oav_legibility = _result_payload(legibility_gate)
    scaling_risk = _result_payload(scaling_gate)
    robustness = robustness_report.as_dict()

    missing_odt_materials = tuple(
        sorted(m.name for m in state.materials if not m.has_odt_authority)
    )
    screening_oav_coverage = _oav_coverage(state, "screening_oav")
    canonical_oav_coverage = _oav_coverage(state, "canonical_oav")
    unknown_screening_oav_materials = tuple(
        str(name) for name in screening_oav_coverage["unknown_materials"]
    )
    incomplete_canonical_physics_materials = tuple(
        str(name) for name in canonical_oav_coverage["unknown_materials"]
    )
    perceptible_count = _perceptible_count(state)
    known_perceptible_count = _known_perceptible_count(state)
    subliminal_ratio = _subliminal_mass_ratio(state)
    known_subliminal_ratio_lower_bound = _known_subliminal_mass_ratio_lower_bound(state)
    screening_top_family_drift = _max_family_drift(frames)
    screening_coverage_complete = all(
        window.screening_oav_coverage.get("status") == "COMPLETE"
        for window in time_windows
    )
    top_family_drift = (
        screening_top_family_drift if screening_coverage_complete else None
    )
    leaders_changed = _leaders_changed(frames)

    blocking_reasons: list[str] = []
    warning_reasons: list[str] = []

    if odt_coverage.get("status") == "FAIL":
        blocking_reasons.append(
            "ODT coverage incomplete for required materials: " + ", ".join(missing_odt_materials)
        )
    elif odt_coverage.get("status") == "WARN":
        warning_reasons.append(
            str(odt_coverage.get("detail", "ODT authority is partially derived"))
        )
    if oav_legibility.get("status") == "FAIL":
        blocking_reasons.append(str(oav_legibility.get("detail", "OAV legibility failed")))
    elif oav_legibility.get("status") == "WARN":
        warning_reasons.append(str(oav_legibility.get("detail", "OAV legibility fragile")))
    if scaling_risk.get("status") == "FAIL":
        warning_count = len(list(scaling_risk.get("data", {}).get("findings", [])))
        blocking_reasons.append(f"OAV scaling blockers present ({warning_count} findings)")
    elif scaling_risk.get("status") == "WARN":
        warning_reasons.append(str(scaling_risk.get("detail", "OAV scaling warnings present")))
    if robustness_report.status == "WARN":
        warning_reasons.append(
            f"OAV robustness flagged {len(robustness_report.issues)} perturbation issue(s)"
        )
    if leaders_changed:
        warning_reasons.append("Dominant OAV leaders change across time windows")
    if screening_top_family_drift > DRIFT_WARN_THRESHOLD:
        warning_reasons.append(
            "Screening-diagnostic top family OAV drift "
            f"{screening_top_family_drift:.1%} exceeds {DRIFT_WARN_THRESHOLD:.0%}"
        )
    blocking_reasons.extend(intelligence.intelligence_blocking_reasons)
    warning_reasons.extend(intelligence.intelligence_warning_reasons)

    if blocking_reasons:
        primary_status = "FAIL"
    elif warning_reasons:
        primary_status = "WARN"
    else:
        primary_status = "PASS"

    screening_diagnostic_score = _compute_screening_diagnostic_score(
        odt_coverage,
        oav_legibility,
        scaling_risk,
        robustness,
        intelligence,
        known_perceptible_count,
        known_subliminal_ratio_lower_bound,
        screening_top_family_drift,
        missing_odt_materials,
    )
    canonical_physics_complete = canonical_oav_coverage.get("status") == "COMPLETE"
    if screening_coverage_complete and canonical_physics_complete:
        authoritative_rank_score: float | None = screening_diagnostic_score
        authority_rank_status = "DIAGNOSTIC_ONLY"
    else:
        authoritative_rank_score = None
        authority_rank_status = "WITHHELD_INCOMPLETE_OAV_OR_CANONICAL_PHYSICS"

    return OAVAuthorityResult(
        request=request,
        state=state,
        material_rows=material_rows,
        time_windows=time_windows,
        odt_coverage=odt_coverage,
        oav_legibility=oav_legibility,
        scaling_risk=scaling_risk,
        robustness=robustness,
        family_target_alignment=intelligence.family_target_alignment,
        material_cliff_findings=intelligence.material_cliff_findings,
        shift_zone_findings=intelligence.shift_zone_findings,
        balance_reports=intelligence.balance_reports,
        performance_projection=intelligence.performance_projection,
        synergy_findings=intelligence.synergy_findings,
        intelligence_status=intelligence.intelligence_status,
        intelligence_blocking_reasons=intelligence.intelligence_blocking_reasons,
        intelligence_warning_reasons=intelligence.intelligence_warning_reasons,
        primary_status=primary_status,
        screening_diagnostic_score=screening_diagnostic_score,
        authoritative_rank_score=authoritative_rank_score,
        authority_rank_status=authority_rank_status,
        blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
        warning_reasons=tuple(
            reason
            for reason in dict.fromkeys(warning_reasons)
            if reason not in dict.fromkeys(blocking_reasons)
        ),
        dominant_leaders_changed=leaders_changed,
        top_family_drift=top_family_drift,
        screening_top_family_drift=screening_top_family_drift,
        subliminal_mass_ratio=subliminal_ratio,
        known_subliminal_mass_ratio_lower_bound=(
            known_subliminal_ratio_lower_bound
        ),
        perceptible_material_count=perceptible_count,
        known_perceptible_material_count=known_perceptible_count,
        screening_oav_coverage=screening_oav_coverage,
        canonical_oav_coverage=canonical_oav_coverage,
        unknown_screening_oav_materials=unknown_screening_oav_materials,
        incomplete_canonical_physics_materials=(
            incomplete_canonical_physics_materials
        ),
        missing_odt_materials=missing_odt_materials,
    )
