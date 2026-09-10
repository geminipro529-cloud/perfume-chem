"""Fail-closed pre-mix guard for active-dose continuity and temporal OAV screening.

Hard gate: stock-strength rebases must preserve intended active dose unless an
explicit dose change is intended.

Screening only: time-resolved OAV can flag order-of-magnitude exposure jumps or
persistent modeled dominance, but never represents percent perceived
contribution, exact intensity, target similarity, pleasantness, or preference.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from engine.name_utils import normalize_name

if TYPE_CHECKING:
    from engine.pipeline.oav_evidence import (
        TemporalOAVCellResult,
        TemporalOAVEvidenceResult,
    )

STOCK_REBASE_FAIL_FOLD = 3.0
STOCK_REBASE_WARN_FOLD = 1.5
TEMPORAL_OAV_JUMP_FOLD = 10.0
STATIC_DOMINANCE_RATIO = 20.0
STATIC_DOMINANCE_MIN_OAV = 100.0
STATIC_DOMINANCE_MIN_WINDOWS = 2
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PreMixGuardError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PreMixFinding:
    code: str
    severity: str
    material: str | None
    detail: str
    parent_active_ul: float | None = None
    child_active_ul: float | None = None
    active_fold_change: float | None = None
    max_temporal_oav_fold_change: float | None = None
    affected_windows: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.severity not in {"FAIL", "WARN"}:
            raise PreMixGuardError("severity must be FAIL or WARN")
        if not self.code.strip() or not self.detail.strip():
            raise PreMixGuardError("finding code/detail must not be blank")

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "material": self.material,
            "detail": self.detail,
            "parent_active_ul": self.parent_active_ul,
            "child_active_ul": self.child_active_ul,
            "active_fold_change": self.active_fold_change,
            "max_temporal_oav_fold_change": self.max_temporal_oav_fold_change,
            "affected_windows": list(self.affected_windows),
        }


@dataclass(frozen=True, slots=True)
class PreMixGuardReport:
    findings: tuple[PreMixFinding, ...]
    parent_comparison_available: bool
    temporal_comparison_available: bool
    temporal_evidence_mode: str = "NONE"
    parent_temporal_oav_sha256: str | None = None
    child_temporal_oav_sha256: str | None = None

    @property
    def status(self) -> str:
        if any(x.severity == "FAIL" for x in self.findings):
            return "FAIL"
        return "WARN" if self.findings else "PASS"

    @property
    def gate_status(self) -> str:
        """Expose the screening result through the pipeline gate vocabulary."""

        return self.status

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "gate_status": self.gate_status,
            "parent_comparison_available": self.parent_comparison_available,
            "temporal_comparison_available": self.temporal_comparison_available,
            "temporal_evidence_mode": self.temporal_evidence_mode,
            "parent_temporal_oav_sha256": self.parent_temporal_oav_sha256,
            "child_temporal_oav_sha256": self.child_temporal_oav_sha256,
            "findings": [x.as_dict() for x in self.findings],
            "limitations": [
                "Active-dose continuity is the hard invariant for stock rebases.",
                "Temporal OAV is screening only and is not percent perceived contribution.",
                "Typed temporal OAV compares exact compatible cells only; it never interpolates or nearest-label matches.",
                "Static OAV dominance alone never hard-fails a formula.",
                "No target-similarity, pleasantness, or consumer-preference claim is made.",
            ],
        }


def _fraction(value: object, name: str) -> float:
    if isinstance(value, bool):
        raise PreMixGuardError(f"{name}: stock fraction must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise PreMixGuardError(f"{name}: stock fraction must be numeric") from exc
    if not math.isfinite(result) or not (0.0 < result <= 1.0):
        raise PreMixGuardError(f"{name}: stock fraction must be in (0, 1]")
    return result


def _dose(value: object, name: str) -> float:
    if isinstance(value, bool):
        raise PreMixGuardError(f"{name}: raw dose must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise PreMixGuardError(f"{name}: raw dose must be numeric") from exc
    if not math.isfinite(result) or result < 0.0:
        raise PreMixGuardError(f"{name}: raw dose must be finite and non-negative")
    return result


def _rows(
    ingredients_ul: Mapping[str, float],
    dilutions: Mapping[str, float],
) -> dict[str, dict[str, float | str]]:
    result: dict[str, dict[str, float | str]] = {}
    for name, raw in ingredients_ul.items():
        key = normalize_name(name)
        if not key or key in result:
            raise PreMixGuardError(f"duplicate/blank normalized material identity: {name}")
        if name not in dilutions:
            raise PreMixGuardError(f"{name}: missing declared stock fraction")
        raw_ul = _dose(raw, name)
        frac = _fraction(dilutions[name], name)
        result[key] = {
            "name": name,
            "raw_ul": raw_ul,
            "dilution": frac,
            "active_ul": raw_ul * frac,
        }
    return result


def _oav(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) and x > 0.0 else None


def _series(
    frames: Sequence[Mapping[str, Any]] | None,
) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    if not frames:
        return out
    for i, frame in enumerate(frames):
        if not isinstance(frame, Mapping):
            raise PreMixGuardError("temporal frames must be mappings")
        label = str(frame.get("label") or f"window_{i}")
        state = frame.get("state")
        if not isinstance(state, Mapping):
            raise PreMixGuardError(f"{label}: missing state mapping")
        materials = state.get("materials")
        if not isinstance(materials, Sequence) or isinstance(materials, (str, bytes)):
            raise PreMixGuardError(f"{label}: missing materials sequence")
        for row in materials:
            if not isinstance(row, Mapping):
                continue
            name = str(row.get("name") or "").strip()
            value = _oav(row.get("oav"))
            if name and value is not None:
                out.setdefault(normalize_name(name), {})[label] = value
    return out


def _fold(child: float, parent: float) -> float:
    if parent <= 0.0 or child <= 0.0:
        return math.inf
    r = child / parent
    return max(r, 1.0 / r)


def _temporal_increase(
    material: str,
    parent: Mapping[str, Mapping[str, float]],
    child: Mapping[str, Mapping[str, float]],
) -> tuple[float | None, tuple[str, ...]]:
    ratios: list[tuple[str, float]] = []
    p = parent.get(material, {})
    c = child.get(material, {})
    for label in sorted(set(p) & set(c)):
        if p[label] >= 1.0 and c[label] > 0.0:
            ratios.append((label, c[label] / p[label]))
    if not ratios:
        return None, ()
    max_fold = max(v for _, v in ratios)
    windows = tuple(label for label, v in ratios if v >= max(3.0, max_fold * 0.8))
    return max_fold, windows


def _revision_findings(
    parent_rows: Mapping[str, Mapping[str, float | str]],
    child_rows: Mapping[str, Mapping[str, float | str]],
    parent_series: Mapping[str, Mapping[str, float]],
    child_series: Mapping[str, Mapping[str, float]],
    authorized_active_dose_changes: Mapping[str, str],
) -> list[PreMixFinding]:
    out: list[PreMixFinding] = []
    for key in sorted(set(parent_rows) & set(child_rows)):
        p = parent_rows[key]
        c = child_rows[key]
        pd = float(p["dilution"])
        cd = float(c["dilution"])
        pa = float(p["active_ul"])
        ca = float(c["active_ul"])
        tfold, windows = _temporal_increase(key, parent_series, child_series)

        authorized_reason = authorized_active_dose_changes.get(key)
        if not math.isclose(pd, cd, rel_tol=1e-9, abs_tol=1e-12):
            active_fold = _fold(ca, pa)
            expected_raw = pa / cd
            if active_fold >= STOCK_REBASE_FAIL_FOLD and not authorized_reason:
                out.append(
                    PreMixFinding(
                        code="STOCK_REBASE_ACTIVE_EQUIVALENCE",
                        severity="FAIL",
                        material=str(c["name"]),
                        detail=(
                            f"Stock strength changed {pd:.6g}->{cd:.6g}; active dose "
                            f"changed {pa:.6g}->{ca:.6g} µL ({active_fold:.2f}x). "
                            f"Active-equivalent child raw dose is ~{expected_raw:.6g} µL."
                        ),
                        parent_active_ul=pa,
                        child_active_ul=ca,
                        active_fold_change=active_fold,
                        max_temporal_oav_fold_change=tfold,
                        affected_windows=windows,
                    )
                )
            elif active_fold >= STOCK_REBASE_FAIL_FOLD:
                out.append(
                    PreMixFinding(
                        code="AUTHORIZED_ACTIVE_DOSE_CHANGE",
                        severity="WARN",
                        material=str(c["name"]),
                        detail=(
                            f"Authorized stock/revision change altered active dose {active_fold:.2f}x: "
                            f"{authorized_reason}. Preserve this authority with the formula revision."
                        ),
                        parent_active_ul=pa,
                        child_active_ul=ca,
                        active_fold_change=active_fold,
                        max_temporal_oav_fold_change=tfold,
                        affected_windows=windows,
                    )
                )
            elif active_fold >= STOCK_REBASE_WARN_FOLD:
                out.append(
                    PreMixFinding(
                        code="STOCK_REBASE_ACTIVE_DRIFT",
                        severity="WARN",
                        material=str(c["name"]),
                        detail=(
                            f"Stock strength changed {pd:.6g}->{cd:.6g}; active dose "
                            f"drifted {active_fold:.2f}x. Active-equivalent child raw "
                            f"dose is ~{expected_raw:.6g} µL."
                        ),
                        parent_active_ul=pa,
                        child_active_ul=ca,
                        active_fold_change=active_fold,
                        max_temporal_oav_fold_change=tfold,
                        affected_windows=windows,
                    )
                )
        elif pa > 0.0 and ca / pa >= STOCK_REBASE_FAIL_FOLD:
            active_increase = ca / pa
            if authorized_reason:
                out.append(
                    PreMixFinding(
                        code="AUTHORIZED_ACTIVE_DOSE_CHANGE",
                        severity="WARN",
                        material=str(c["name"]),
                        detail=(
                            f"Authorized same-stock revision raised active dose {active_increase:.2f}x: "
                            f"{authorized_reason}. Preserve this authority with the formula revision."
                        ),
                        parent_active_ul=pa,
                        child_active_ul=ca,
                        active_fold_change=active_increase,
                        max_temporal_oav_fold_change=tfold,
                        affected_windows=windows,
                    )
                )
            else:
                out.append(
                    PreMixFinding(
                        code="ACTIVE_DOSE_REVISION_JUMP",
                        severity="FAIL",
                        material=str(c["name"]),
                        detail=(
                            f"Same-stock revision raised active dose {active_increase:.2f}x "
                            f"({pa:.6g}->{ca:.6g} µL) without explicit intentional-dose-change authority."
                        ),
                        parent_active_ul=pa,
                        child_active_ul=ca,
                        active_fold_change=active_increase,
                        max_temporal_oav_fold_change=tfold,
                        affected_windows=windows,
                    )
                )
        elif tfold is not None and tfold >= TEMPORAL_OAV_JUMP_FOLD:
            out.append(
                PreMixFinding(
                    code="TEMPORAL_OAV_ORDER_OF_MAGNITUDE_JUMP",
                    severity="WARN",
                    material=str(c["name"]),
                    detail=(
                        f"Matched-window modeled OAV increased up to {tfold:.2f}x. "
                        "Manual review required; modeled OAV is screening only."
                    ),
                    parent_active_ul=pa,
                    child_active_ul=ca,
                    active_fold_change=_fold(ca, pa),
                    max_temporal_oav_fold_change=tfold,
                    affected_windows=windows,
                )
            )
    return out


def _static_findings(
    frames: Sequence[Mapping[str, Any]] | None,
) -> list[PreMixFinding]:
    if not frames:
        return []
    leaders: dict[str, dict[str, Any]] = {}
    for i, frame in enumerate(frames):
        label = str(frame.get("label") or f"window_{i}")
        state = frame.get("state")
        if not isinstance(state, Mapping):
            continue
        mats = state.get("materials")
        if not isinstance(mats, Sequence) or isinstance(mats, (str, bytes)):
            continue
        ranked: list[tuple[str, float]] = []
        for row in mats:
            if isinstance(row, Mapping):
                name = str(row.get("name") or "").strip()
                value = _oav(row.get("oav"))
                if name and value is not None:
                    ranked.append((name, value))
        ranked.sort(key=lambda x: x[1], reverse=True)
        if len(ranked) < 2:
            continue
        name, lead = ranked[0]
        runner = ranked[1][1]
        if lead < STATIC_DOMINANCE_MIN_OAV or runner <= 0.0:
            continue
        ratio = lead / runner
        if ratio >= STATIC_DOMINANCE_RATIO:
            rec = leaders.setdefault(normalize_name(name), {"name": name, "rows": []})
            rec["rows"].append((label, lead, ratio))

    out: list[PreMixFinding] = []
    for key in sorted(leaders):
        rec = leaders[key]
        rows = rec["rows"]
        if len(rows) < STATIC_DOMINANCE_MIN_WINDOWS:
            continue
        out.append(
            PreMixFinding(
                code="PERSISTENT_MODELED_OAV_DOMINANCE",
                severity="WARN",
                material=str(rec["name"]),
                detail=(
                    f"Modeled OAV leader exceeds runner-up >= {STATIC_DOMINANCE_RATIO:.0f}x "
                    f"in {len(rows)} windows. Screening alarm only, not percent contribution."
                ),
                max_temporal_oav_fold_change=max(ratio for _, _, ratio in rows),
                affected_windows=tuple(label for label, _, _ in rows),
            )
        )
    return out


def _receipt_binding(
    label: str,
    receipt: TemporalOAVEvidenceResult | None,
    expected_sha256: str | None,
) -> tuple[str | None, bool, list[PreMixFinding]]:
    from engine.pipeline import oav_evidence as temporal_oav_contracts  # noqa: PLC0415

    if receipt is None:
        if expected_sha256 is not None:
            raise PreMixGuardError(
                f"{label}_temporal_oav_sha256 requires a {label} temporal OAV receipt"
            )
        return None, False, []
    if not isinstance(receipt, temporal_oav_contracts.TemporalOAVEvidenceResult):
        raise PreMixGuardError(
            f"{label}_temporal_oav must be a TemporalOAVEvidenceResult"
        )
    if expected_sha256 is not None and (
        not isinstance(expected_sha256, str)
        or _SHA256_RE.fullmatch(expected_sha256) is None
    ):
        raise PreMixGuardError(
            f"{label}_temporal_oav_sha256 must be a lowercase SHA-256 digest"
        )
    observed_sha256 = receipt.result_sha256
    findings: list[PreMixFinding] = []
    if expected_sha256 is not None and expected_sha256 != observed_sha256:
        findings.append(
            PreMixFinding(
                code="TEMPORAL_OAV_RECEIPT_HASH_MISMATCH",
                severity="WARN",
                material=None,
                detail=(
                    f"{label.title()} temporal OAV receipt hash does not match the "
                    "declared binding. The receipt is excluded from screening comparison."
                ),
            )
        )
        return observed_sha256, False, findings
    admissible = receipt.state in {
        temporal_oav_contracts.TemporalOAVEvidenceState.STRICT_MEASURED_TIME_SERIES,
        temporal_oav_contracts.TemporalOAVEvidenceState.MODELED_SCREEN,
    }
    if not admissible:
        findings.append(
            PreMixFinding(
                code="TEMPORAL_OAV_RECEIPT_NOT_ADMISSIBLE",
                severity="WARN",
                material=None,
                detail=(
                    f"{label.title()} temporal OAV receipt state is "
                    f"{receipt.state.value}; only complete strict-measured or modeled-screen "
                    "receipts may enter temporal screening."
                ),
            )
        )
    return observed_sha256, admissible, findings


def _typed_cell_map(
    receipt: TemporalOAVEvidenceResult,
    series: str,
) -> dict[object, TemporalOAVCellResult]:
    cells = receipt.measured_cells if series == "MEASURED" else receipt.modeled_cells
    return {cell.key: cell for cell in cells}


def _threshold_scope(cell: TemporalOAVCellResult) -> tuple[object, ...]:
    threshold = cell.evidence.threshold_interval.p50
    source = threshold.source
    source_scope = None if source is None else tuple(source.as_dict().items())
    return (
        cell.key.material_id,
        cell.key.endpoint,
        threshold.unit,
        threshold.context,
        threshold.method,
        threshold.basis.value,
        source_scope,
    )


def _headspace_scope(cell: TemporalOAVCellResult) -> tuple[object, ...]:
    headspace = cell.evidence.headspace_interval.p50
    return (
        headspace.unit,
        headspace.context,
        headspace.method,
        headspace.basis.value,
        cell.evidence.model_tier.value,
    )


def _typed_cell_label(cell: TemporalOAVCellResult) -> str:
    key = cell.key
    return f"{key.sample_id}:{key.material_id}:{key.time_seconds}:{key.endpoint}"


def _typed_comparison_findings(
    parent: TemporalOAVEvidenceResult,
    child: TemporalOAVEvidenceResult,
) -> tuple[list[PreMixFinding], bool]:
    findings: list[PreMixFinding] = []
    if parent.measurement_context_sha256 != child.measurement_context_sha256:
        findings.append(
            PreMixFinding(
                code="TEMPORAL_OAV_SCOPE_MISMATCH",
                severity="WARN",
                material=None,
                detail=(
                    "Parent and child temporal OAV measurement-context hashes differ; "
                    "no temporal cells were compared."
                ),
            )
        )
        return findings, False

    parent_measured = _typed_cell_map(parent, "MEASURED")
    child_measured = _typed_cell_map(child, "MEASURED")
    parent_modeled = _typed_cell_map(parent, "MODELED")
    child_modeled = _typed_cell_map(child, "MODELED")
    parent_all = set(parent_measured) | set(parent_modeled)
    child_all = set(child_measured) | set(child_modeled)
    exact_measured = set(parent_measured) & set(child_measured)
    exact_modeled = set(parent_modeled) & set(child_modeled)
    cross_basis = (parent_all & child_all).difference(exact_measured | exact_modeled)
    if cross_basis:
        findings.append(
            PreMixFinding(
                code="TEMPORAL_OAV_SERIES_BASIS_MISMATCH",
                severity="WARN",
                material=None,
                detail=(
                    f"{len(cross_basis)} exact temporal key(s) occur in different measured "
                    "versus modeled series and were not compared."
                ),
                affected_windows=tuple(
                    sorted(
                        f"{key.sample_id}:{key.material_id}:{key.time_seconds}:{key.endpoint}"
                        for key in cross_basis
                    )
                ),
            )
        )

    comparable = False
    for series, keys, parent_cells, child_cells in (
        ("measured", exact_measured, parent_measured, child_measured),
        ("modeled", exact_modeled, parent_modeled, child_modeled),
    ):
        for key in sorted(
            keys,
            key=lambda item: (
                item.protocol_sha256,
                item.sample_id,
                item.material_id,
                item.time_seconds,
                item.endpoint,
            ),
        ):
            parent_cell = parent_cells[key]
            child_cell = child_cells[key]
            if (
                _threshold_scope(parent_cell) != _threshold_scope(child_cell)
                or _headspace_scope(parent_cell) != _headspace_scope(child_cell)
            ):
                findings.append(
                    PreMixFinding(
                        code="THRESHOLD_CANCELLATION_INCOMPATIBLE",
                        severity="WARN",
                        material=key.material_id,
                        detail=(
                            f"Exact {series} temporal key has incompatible threshold or "
                            "headspace scope; relative OAV cancellation is withheld."
                        ),
                        affected_windows=(_typed_cell_label(parent_cell),),
                    )
                )
                continue
            if parent_cell.oav_interval is None or child_cell.oav_interval is None:
                continue
            comparable = True
            parent_interval = parent_cell.oav_interval
            child_interval = child_cell.oav_interval
            parent_median = parent_interval[1]
            child_median = child_interval[1]
            if parent_median < 1.0 or child_median <= 0.0:
                continue
            fold = child_median / parent_median
            if fold < TEMPORAL_OAV_JUMP_FOLD:
                continue
            label = _typed_cell_label(parent_cell)
            findings.append(
                PreMixFinding(
                    code="TEMPORAL_OAV_ORDER_OF_MAGNITUDE_JUMP",
                    severity="WARN",
                    material=key.material_id,
                    detail=(
                        f"Exact compatible {series} OAV median increased {fold:.2f}x. "
                        "This is a screening warning only."
                    ),
                    max_temporal_oav_fold_change=fold,
                    affected_windows=(label,),
                )
            )
            if child_interval[0] > parent_interval[2]:
                findings.append(
                    PreMixFinding(
                        code="TEMPORAL_OAV_NONOVERLAPPING_INCREASE",
                        severity="WARN",
                        material=key.material_id,
                        detail=(
                            "Child OAV interval is wholly above the compatible parent interval; "
                            "this remains screening evidence only."
                        ),
                        max_temporal_oav_fold_change=fold,
                        affected_windows=(label,),
                    )
                )
            else:
                findings.append(
                    PreMixFinding(
                        code="TEMPORAL_OAV_JUMP_WITH_INTERVAL_OVERLAP",
                        severity="WARN",
                        material=key.material_id,
                        detail=(
                            "Median OAV jump crosses the warning threshold but parent and child "
                            "intervals overlap; no directional physical conclusion is granted."
                        ),
                        max_temporal_oav_fold_change=fold,
                        affected_windows=(label,),
                    )
                )

    if not comparable and not cross_basis and not (exact_measured or exact_modeled):
        findings.append(
            PreMixFinding(
                code="NO_EXACT_TEMPORAL_OAV_MATCH",
                severity="WARN",
                material=None,
                detail=(
                    "Parent and child receipts share no exact temporal OAV cell key; "
                    "nearest labels and interpolation are forbidden."
                ),
            )
        )
    return findings, comparable


def _typed_static_findings(
    receipt: TemporalOAVEvidenceResult,
) -> list[PreMixFinding]:
    windows: dict[tuple[str, int, str], list[tuple[str, float]]] = {}
    for cell in receipt.modeled_cells:
        if cell.oav_interval is None:
            continue
        key = (cell.key.sample_id, cell.key.time_seconds, cell.key.endpoint)
        windows.setdefault(key, []).append(
            (cell.key.material_id, cell.oav_interval[1])
        )
    leaders: dict[str, dict[str, Any]] = {}
    for key, values in windows.items():
        ranked = sorted(values, key=lambda item: item[1], reverse=True)
        if len(ranked) < 2:
            continue
        name, lead = ranked[0]
        runner = ranked[1][1]
        if lead < STATIC_DOMINANCE_MIN_OAV or runner <= 0:
            continue
        ratio = lead / runner
        if ratio < STATIC_DOMINANCE_RATIO:
            continue
        record = leaders.setdefault(normalize_name(name), {"name": name, "rows": []})
        record["rows"].append((f"{key[0]}:{key[1]}:{key[2]}", ratio))
    findings: list[PreMixFinding] = []
    for normalized_name in sorted(leaders):
        record = leaders[normalized_name]
        rows = record["rows"]
        if len(rows) < STATIC_DOMINANCE_MIN_WINDOWS:
            continue
        findings.append(
            PreMixFinding(
                code="PERSISTENT_MODELED_OAV_DOMINANCE",
                severity="WARN",
                material=str(record["name"]),
                detail=(
                    f"Typed modeled OAV leader exceeds runner-up >= "
                    f"{STATIC_DOMINANCE_RATIO:.0f}x in {len(rows)} exact windows. "
                    "Screening alarm only, not percent contribution."
                ),
                max_temporal_oav_fold_change=max(ratio for _, ratio in rows),
                affected_windows=tuple(label for label, _ in rows),
            )
        )
    return findings


def evaluate_pre_mix_guard(
    *,
    child_ingredients_ul: Mapping[str, float],
    child_dilutions: Mapping[str, float],
    child_time_series: Sequence[Mapping[str, Any]] | None = None,
    parent_ingredients_ul: Mapping[str, float] | None = None,
    parent_dilutions: Mapping[str, float] | None = None,
    parent_time_series: Sequence[Mapping[str, Any]] | None = None,
    authorized_active_dose_changes: Mapping[str, str] | None = None,
    parent_temporal_oav: TemporalOAVEvidenceResult | None = None,
    child_temporal_oav: TemporalOAVEvidenceResult | None = None,
    parent_temporal_oav_sha256: str | None = None,
    child_temporal_oav_sha256: str | None = None,
) -> PreMixGuardReport:
    child_rows = _rows(child_ingredients_ul, child_dilutions)
    child_series = _series(child_time_series)
    typed_requested = any(
        value is not None
        for value in (
            parent_temporal_oav,
            child_temporal_oav,
            parent_temporal_oav_sha256,
            child_temporal_oav_sha256,
        )
    )

    if (parent_ingredients_ul is None) != (parent_dilutions is None):
        raise PreMixGuardError(
            "parent_ingredients_ul and parent_dilutions must be provided together"
        )

    authorized: dict[str, str] = {}
    for name, reason in dict(authorized_active_dose_changes or {}).items():
        key = normalize_name(str(name))
        authority = str(reason).strip()
        if not key or not authority:
            raise PreMixGuardError(
                "authorized_active_dose_changes requires non-blank material names and authority reasons"
            )
        authorized[key] = authority

    findings: list[PreMixFinding] = []
    parent_available = parent_ingredients_ul is not None
    temporal_available = False
    parent_receipt_sha256: str | None = None
    child_receipt_sha256: str | None = None

    if parent_available:
        assert parent_ingredients_ul is not None
        assert parent_dilutions is not None
        parent_rows = _rows(parent_ingredients_ul, parent_dilutions)
        parent_series = _series(parent_time_series)
        if not typed_requested:
            temporal_available = bool(parent_series and child_series)
        findings.extend(
            _revision_findings(
                parent_rows,
                child_rows,
                {} if typed_requested else parent_series,
                {} if typed_requested else child_series,
                authorized,
            )
        )

    if typed_requested:
        parent_receipt_sha256, parent_admissible, parent_findings = _receipt_binding(
            "parent", parent_temporal_oav, parent_temporal_oav_sha256
        )
        child_receipt_sha256, child_admissible, child_findings = _receipt_binding(
            "child", child_temporal_oav, child_temporal_oav_sha256
        )
        findings.extend(parent_findings)
        findings.extend(child_findings)
        if (
            parent_temporal_oav is not None
            and child_temporal_oav is not None
            and parent_admissible
            and child_admissible
        ):
            comparison_findings, temporal_available = _typed_comparison_findings(
                parent_temporal_oav, child_temporal_oav
            )
            findings.extend(comparison_findings)
        if child_temporal_oav is not None and child_admissible:
            findings.extend(_typed_static_findings(child_temporal_oav))
        temporal_mode = "TYPED_CANONICAL_RECEIPTS"
    else:
        findings.extend(_static_findings(child_time_series))
        temporal_mode = (
            "LEGACY_MODELED_SCREEN_ONLY"
            if child_time_series or parent_time_series
            else "NONE"
        )
    findings.sort(key=lambda x: (0 if x.severity == "FAIL" else 1, x.code, x.material or ""))
    return PreMixGuardReport(
        tuple(findings),
        parent_available,
        temporal_available,
        temporal_mode,
        parent_receipt_sha256,
        child_receipt_sha256,
    )


__all__ = [
    "PreMixFinding",
    "PreMixGuardError",
    "PreMixGuardReport",
    "evaluate_pre_mix_guard",
]
