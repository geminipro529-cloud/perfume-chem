"""Fail-closed pre-mix guard for active-dose continuity and temporal OAV screening.

Hard gate: stock-strength rebases must preserve intended active dose unless an
explicit dose change is intended.

Screening only: time-resolved OAV can flag order-of-magnitude exposure jumps or
persistent modeled dominance, but never represents percent perceived
contribution, exact intensity, target similarity, pleasantness, or preference.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from engine.name_utils import normalize_name

STOCK_REBASE_FAIL_FOLD = 3.0
STOCK_REBASE_WARN_FOLD = 1.5
TEMPORAL_OAV_JUMP_FOLD = 10.0
STATIC_DOMINANCE_RATIO = 20.0
STATIC_DOMINANCE_MIN_OAV = 100.0
STATIC_DOMINANCE_MIN_WINDOWS = 2


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
            "findings": [x.as_dict() for x in self.findings],
            "limitations": [
                "Active-dose continuity is the hard invariant for stock rebases.",
                "Temporal OAV is screening only and is not percent perceived contribution.",
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


def evaluate_pre_mix_guard(
    *,
    child_ingredients_ul: Mapping[str, float],
    child_dilutions: Mapping[str, float],
    child_time_series: Sequence[Mapping[str, Any]] | None = None,
    parent_ingredients_ul: Mapping[str, float] | None = None,
    parent_dilutions: Mapping[str, float] | None = None,
    parent_time_series: Sequence[Mapping[str, Any]] | None = None,
    authorized_active_dose_changes: Mapping[str, str] | None = None,
) -> PreMixGuardReport:
    child_rows = _rows(child_ingredients_ul, child_dilutions)
    child_series = _series(child_time_series)

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

    if parent_available:
        assert parent_ingredients_ul is not None
        assert parent_dilutions is not None
        parent_rows = _rows(parent_ingredients_ul, parent_dilutions)
        parent_series = _series(parent_time_series)
        temporal_available = bool(parent_series and child_series)
        findings.extend(
            _revision_findings(
                parent_rows,
                child_rows,
                parent_series,
                child_series,
                authorized,
            )
        )

    findings.extend(_static_findings(child_time_series))
    findings.sort(key=lambda x: (0 if x.severity == "FAIL" else 1, x.code, x.material or ""))
    return PreMixGuardReport(tuple(findings), parent_available, temporal_available)


__all__ = [
    "PreMixFinding",
    "PreMixGuardError",
    "PreMixGuardReport",
    "evaluate_pre_mix_guard",
]
