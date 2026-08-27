"""Canonical OAV-first authority layer for candidate formula analysis.

This module turns a candidate formula into one stable OAV verdict surface using
the existing physical path:

raw dose -> active dose -> headspace ppm -> per-material OAV ->
family-envelope OAV -> time-windowed OAV behavior -> authority verdict
"""

from __future__ import annotations

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
from engine.pipeline.simulator import DEFAULT_WINDOWS, SimulationFrame, simulate_formula


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


def _family_envelope(state: FormulaState) -> dict[str, float]:
    envelope: dict[str, float] = {}
    for material in state.materials:
        family = _family_key(material)
        envelope[family] = envelope.get(family, 0.0) + float(material.oav or 0.0)
    return dict(sorted(envelope.items()))


def _dominant_leader(frame: SimulationFrame) -> str | None:
    leaders = frame.dominant_oav(limit=1)
    if not leaders:
        return None
    return str(leaders[0]["material"])


def _subliminal_mass_ratio(state: FormulaState) -> float:
    total = state.total_active_ul or 1.0
    return sum(m.active_ul for m in state.materials if (m.oav or 0.0) < 0.2) / total


def _perceptible_count(state: FormulaState) -> int:
    return len(state.perceptible_materials)


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
    dose_receipt_sha256: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
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
        if self.dose_receipt_sha256 is not None:
            payload["dose_receipt_sha256"] = self.dose_receipt_sha256
        return payload


@dataclass(frozen=True, slots=True)
class OAVMaterialRow:
    name: str
    canonical_name: str
    family: str | None
    note: str
    raw_ul: float
    dilution: float
    active_ul: float
    vapor_ppm: float
    odt_air_ppm: float | None
    odt_source: str
    oav: float | None
    intensity: float | None

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
            vapor_ppm=float(material.vapor_ppm),
            odt_air_ppm=material.odt_air_ppm,
            odt_source=str(material.sources.get("odt", "missing")),
            oav=material.oav,
            intensity=material.intensity,
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
            "vapor_ppm": round(self.vapor_ppm, 6),
            "odt_air_ppm": self.odt_air_ppm,
            "odt_source": self.odt_source,
            "oav": None if self.oav is None else round(float(self.oav), 6),
            "intensity": None if self.intensity is None else round(float(self.intensity), 6),
        }


@dataclass(frozen=True, slots=True)
class OAVTimeWindowSummary:
    label: str
    t_seconds: float
    family_envelope: dict[str, float]
    dominant_oav: list[dict[str, Any]]
    perceptible_material_count: int
    subliminal_mass_ratio: float
    total_vapor_ppm: float

    @classmethod
    def from_frame(cls, frame: SimulationFrame) -> "OAVTimeWindowSummary":
        return cls(
            label=frame.label,
            t_seconds=float(frame.t_seconds),
            family_envelope={k: round(v, 6) for k, v in _family_envelope(frame.state).items()},
            dominant_oav=frame.dominant_oav(),
            perceptible_material_count=_perceptible_count(frame.state),
            subliminal_mass_ratio=_subliminal_mass_ratio(frame.state),
            total_vapor_ppm=float(frame.state.total_vapor_ppm),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "t_seconds": round(self.t_seconds, 6),
            "family_envelope": dict(self.family_envelope),
            "dominant_oav": list(self.dominant_oav),
            "perceptible_material_count": self.perceptible_material_count,
            "subliminal_mass_ratio": round(self.subliminal_mass_ratio, 6),
            "total_vapor_ppm": round(self.total_vapor_ppm, 6),
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
    receipt_binding_status: str
    strict_oav_status: str
    dose_receipt_sha256: str | None
    primary_status: str
    authority_rank_score: float
    blocking_reasons: tuple[str, ...]
    warning_reasons: tuple[str, ...]
    dominant_leaders_changed: bool
    top_family_drift: float
    subliminal_mass_ratio: float
    missing_odt_materials: tuple[str, ...]

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
                "receipt_binding_status": self.receipt_binding_status,
                "dose_receipt_sha256": self.dose_receipt_sha256,
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
                "authority_rank_score": round(self.authority_rank_score, 6),
                "blocking_reasons": list(self.blocking_reasons),
                "warning_reasons": list(self.warning_reasons),
                "dominant_leaders_changed": self.dominant_leaders_changed,
                "top_family_drift": round(self.top_family_drift, 6),
                "subliminal_mass_ratio": round(self.subliminal_mass_ratio, 6),
                "missing_odt_materials": list(self.missing_odt_materials),
                "odt_coverage": dict(self.odt_coverage),
                "oav_legibility": dict(self.oav_legibility),
                "scaling_risk": dict(self.scaling_risk),
                "robustness": dict(self.robustness),
                "intelligence_status": self.intelligence_status,
                "strict_oav_status": self.strict_oav_status,
                "receipt_binding_status": self.receipt_binding_status,
                "dose_receipt_sha256": self.dose_receipt_sha256,
            },
            "downstream_integration": {
                "status_rank": _status_rank(self.primary_status),
                "coverage_complete": not self.missing_odt_materials,
                "perceptible_material_count": _perceptible_count(self.state),
                "subliminal_mass_ratio": round(self.subliminal_mass_ratio, 6),
                "current_family_envelope": dict(current_family_envelope),
                "top_family_drift": round(self.top_family_drift, 6),
                "dominant_leaders_changed": self.dominant_leaders_changed,
                "scaling_status": self.scaling_risk.get("status", "PASS"),
                "robustness_status": self.robustness.get("status", "PASS"),
                "intelligence_status": self.intelligence_status,
                "authority_rank_score": round(self.authority_rank_score, 6),
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


def _compute_rank_score(
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


def analyze_oav_authority(
    request: OAVAuthorityRequest,
    *,
    gate_report: GateReport | None = None,
) -> OAVAuthorityResult:
    """Run canonical OAV-first analysis and return an authority verdict surface."""
    formula = _formula_record_from_request(request)
    reused_gates: dict[str, GateResult] = {}
    if gate_report is None:
        receipt_binding_status = "UNBOUND_EXPLORATORY_RECONSTRUCTION"
        dose_receipt_sha256 = request.dose_receipt_sha256
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
        if request.dose_receipt_sha256 is None:
            receipt_binding_status = "UNBOUND_GATE_REPORT_COMPAT"
            dose_receipt_sha256 = None
        elif request.dose_receipt_sha256 != gate_report.dose_receipt.receipt_sha256:
            raise ValueError("OAV request dose receipt does not match gate report")
        else:
            receipt_binding_status = "BOUND_GATE_RECEIPT"
            dose_receipt_sha256 = gate_report.dose_receipt.receipt_sha256
        state = gate_report.formula_state
        frames = list(gate_report.simulation)
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
        actual_doses = {material.name: material.raw_ul for material in state.materials}
        if actual_doses != expected_doses:
            raise ValueError("Gate report formula state does not match OAV request doses")
        reused_gates = _gate_map(gate_report)
    material_rows = tuple(
        OAVMaterialRow.from_material_state(material)
        for material in sorted(
            state.materials, key=lambda row: ((row.oav or 0.0), row.name), reverse=True
        )
    )
    time_windows = tuple(OAVTimeWindowSummary.from_frame(frame) for frame in frames)

    config = _build_gate_config(request)
    odt_gate = reused_gates.get("odt_coverage") or _gate_odt_coverage(state)
    legibility_gate = reused_gates.get("oav_legibility") or _gate_oav_legibility(state, config)
    scaling_gate = reused_gates.get("oav_scaling") or _gate_oav_scaling(formula, config)
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

    missing_odt_materials = tuple(sorted(m.name for m in state.materials if m.odt_air_ppm is None))
    perceptible_count = _perceptible_count(state)
    subliminal_ratio = _subliminal_mass_ratio(state)
    top_family_drift = _max_family_drift(frames)
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
    if top_family_drift > DRIFT_WARN_THRESHOLD:
        warning_reasons.append(
            f"Top family OAV drift {top_family_drift:.1%} exceeds {DRIFT_WARN_THRESHOLD:.0%}"
        )
    blocking_reasons.extend(intelligence.intelligence_blocking_reasons)
    warning_reasons.extend(intelligence.intelligence_warning_reasons)

    if blocking_reasons:
        primary_status = "FAIL"
    elif warning_reasons:
        primary_status = "WARN"
    else:
        primary_status = "PASS"

    rank_score = _compute_rank_score(
        odt_coverage,
        oav_legibility,
        scaling_risk,
        robustness,
        intelligence,
        perceptible_count,
        subliminal_ratio,
        top_family_drift,
        missing_odt_materials,
    )

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
        receipt_binding_status=receipt_binding_status,
        strict_oav_status="ABSTAINED",
        dose_receipt_sha256=dose_receipt_sha256,
        primary_status=primary_status,
        authority_rank_score=rank_score,
        blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
        warning_reasons=tuple(
            reason
            for reason in dict.fromkeys(warning_reasons)
            if reason not in dict.fromkeys(blocking_reasons)
        ),
        dominant_leaders_changed=leaders_changed,
        top_family_drift=top_family_drift,
        subliminal_mass_ratio=subliminal_ratio,
        missing_odt_materials=missing_odt_materials,
    )
