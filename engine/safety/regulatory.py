"""Versioned safety and regulatory subsystem.

Snapshots IFRA standards with dates — never hardcodes remembered limits.
Separates *historical_target* from *current_compliant_build*.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (parts per million w/w in concentrate).
- ODT in ppm for ethanol solution, ppb for air.
- OAV = concentration_ppm / ODT_ppm (dimensionless).
- IFRA limits (%) must be cross-checked against OAV to ensure
  perceptibility claims are consistent with concentration limits.
"""

from __future__ import annotations

import datetime
import hashlib
import uuid
from dataclasses import dataclass
from typing import Any

from engine.ifra_standards import load_ifra_table

# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

REDUCED_RISK_PRODUCT_TYPES: frozenset[str] = frozenset(
    {
        "deodorant",
        "cream",
        "rinse_off",
    }
)


# ═══════════════════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class RegulatorySnapshot:
    """A point-in-time snapshot of a regulatory rule set.

    Attributes:
        snapshot_id:      Unique identifier for this snapshot.
        jurisdiction:     Regulatory jurisdiction (EU, US, UK, GLOBAL).
        product_category: Product type this snapshot applies to.
        rule_set:         Named rule set version.
        effective_date:   Date the rule set came into effect (YYYY-MM-DD).
        source_url:       URL to the published standard.
        hash:             Content hash of the snapshot data for integrity.
        notes:            Free-text notes about this snapshot.
    """

    snapshot_id: str
    jurisdiction: str
    product_category: str
    rule_set: str
    effective_date: str
    source_url: str = ""
    hash: str = ""
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return snapshot fields as a plain dict."""
        return {
            "snapshot_id": self.snapshot_id,
            "jurisdiction": self.jurisdiction,
            "product_category": self.product_category,
            "rule_set": self.rule_set,
            "effective_date": self.effective_date,
            "source_url": self.source_url,
            "hash": self.hash,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class ComplianceResult:
    """Result of checking a single material against a regulatory snapshot.

    Attributes:
        material:        Material name as used in the formula.
        current_dose_pct: Current dose as % v/v of finished product
                          (active µL per finished-product mL).
        max_allowed_pct: IFRA Category 4 limit (% w/w of finished product)
                          from the sourced table; 0.0 for a prohibited
                          material; ``None`` when the table gives no number.
        exceeds:         True when a restricted dose is over its limit, or a
                          prohibited material is present.
        rule_reference:  Which rule set the caller's snapshot names.
        rule_version:    Version string of the rule set.
        detail:          Human-readable explanation.
        ifra_status:     Table status (restricted, prohibited, specification,
                          restricted_unverified, no_standard,
                          natural_no_own_standard) or ``unknown`` when the
                          material is not in the table.
        ifra_standard:   IFRA Standard id from the table, when there is one.
    """

    material: str
    current_dose_pct: float
    max_allowed_pct: float | None
    exceeds: bool
    rule_reference: str
    rule_version: str
    detail: str
    ifra_status: str = "unknown"
    ifra_standard: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return compliance result as a plain dict."""
        return {
            "material": self.material,
            "current_dose_pct": self.current_dose_pct,
            "max_allowed_pct": self.max_allowed_pct,
            "exceeds": self.exceeds,
            "rule_reference": self.rule_reference,
            "rule_version": self.rule_version,
            "detail": self.detail,
            "ifra_status": self.ifra_status,
            "ifra_standard": self.ifra_standard,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════


def check_compliance(
    formula_materials: list[dict[str, Any]],
    jurisdiction: str,
    product_category: str,
    snapshot: RegulatorySnapshot,
) -> list[ComplianceResult]:
    """Check every material in *formula_materials* against *snapshot* limits.

    Each dict in *formula_materials* must contain at minimum:
        ``name``                     — material name (str)
        ``active_ul``                — active µL in the concentrate (float / int)
        ``finished_product_volume_ml`` — total finished product volume in mL (float / int)

    The active dose is converted to a % of finished product by volume
    (active µL per finished-product mL): these inputs carry no stock dilution,
    carrier or density, so no weight basis can be estimated here.  The IFRA
    Category 4 limits it is compared with are % w/w, from the sourced table
    (``engine.ifra_standards.load_ifra_table``); there is no numeric fallback.
    Materials with no limit in the table get ``max_allowed_pct = None``.

    Returns a list of :class:`ComplianceResult` — one per material.
    """
    results: list[ComplianceResult] = []
    table = load_ifra_table()

    for mat in formula_materials:
        name: str = mat.get("name", "")
        active_ul: float = float(mat.get("active_ul", 0))
        fp_vol_ml: float = float(mat.get("finished_product_volume_ml", 0))
        material = table.lookup(name)
        status = material.status if material is not None else "unknown"
        standard = material.standard if material is not None else None

        if fp_vol_ml <= 0:
            results.append(
                ComplianceResult(
                    material=name,
                    current_dose_pct=0.0,
                    max_allowed_pct=None,
                    exceeds=False,
                    rule_reference=snapshot.rule_set,
                    rule_version=snapshot.effective_date,
                    detail="Finished product volume is zero or missing — cannot compute %.",
                    ifra_status=status,
                    ifra_standard=standard,
                )
            )
            continue

        current_pct = (active_ul / 1000.0) / fp_vol_ml * 100.0
        std_text = standard or "no IFRA standard"
        dose_text = f"Dose {current_pct:.4f}% v/v"
        max_allowed: float | None = None
        exceeds = False
        if material is None:
            detail = (
                f"'{name}' is not in the IFRA 51st Amendment Category 4 table — "
                "unknown, not checked."
            )
        elif status == "restricted":
            max_allowed = material.cat4_limit_pct
            assert max_allowed is not None  # restricted rows carry a sourced limit
            exceeds = current_pct > max_allowed
            ratio = current_pct / max_allowed
            if exceeds:
                detail = (
                    f"{dose_text} exceeds limit {max_allowed:.4f}% w/w "
                    f"({std_text}, ratio {ratio:.2f}×)."
                )
            else:
                detail = (
                    f"{dose_text} within limit {max_allowed:.4f}% w/w "
                    f"({std_text}, usage {ratio * 100:.1f}%)."
                )
        elif status == "prohibited":
            max_allowed = 0.0
            exceeds = current_pct > 0
            authority = material.authority or "IFRA"
            detail = f"{dose_text}: '{name}' is prohibited by {authority} ({std_text})."
        elif status == "specification":
            detail = (
                f"{dose_text}: '{name}' is covered by specification standard {std_text}, "
                "which sets no Category 4 % limit; check the material grade."
            )
        elif status == "restricted_unverified":
            detail = (
                f"{dose_text}: '{name}' is restricted by {std_text} but its Category 4 "
                "limit is not recorded; hold until verified."
            )
        elif status == "no_standard":
            detail = f"{dose_text}: '{name}' has no IFRA standard."
        else:  # natural_no_own_standard
            detail = (
                f"{dose_text}: '{name}' is a natural with no IFRA standard of its own; "
                "its restricted constituents are not summed here."
            )

        results.append(
            ComplianceResult(
                material=name,
                current_dose_pct=round(current_pct, 6),
                max_allowed_pct=max_allowed,
                exceeds=exceeds,
                rule_reference=snapshot.rule_set,
                rule_version=snapshot.effective_date,
                detail=detail,
                ifra_status=status,
                ifra_standard=standard,
            )
        )

    return results


def generate_compliant_build(
    target_materials: list[dict[str, Any]],
    violations: list[ComplianceResult],
) -> list[dict[str, Any]]:
    """Return an adjusted formula where violating materials are capped.

    *target_materials* — list of dicts with at minimum ``name`` and ``active_ul``.
    *violations*       — :class:`ComplianceResult` list from :func:`check_compliance`.

    For every material whose ``ComplianceResult.exceeds`` is ``True``, the
    returned dict will have its ``active_ul`` reduced so that the dose equals
    ``max_allowed_pct`` of the finished product volume.

    The original *target_materials* list is **not** modified — a new list is
    returned.  Materials without violations are copied as-is.
    """
    # Build a lookup: material name → ComplianceResult
    violation_map: dict[str, ComplianceResult] = {v.material: v for v in violations if v.exceeds}

    adjusted: list[dict[str, Any]] = []
    for mat in target_materials:
        name = mat.get("name", "")
        vio = violation_map.get(name)
        if vio is None or vio.max_allowed_pct is None:
            adjusted.append(dict(mat))
            continue

        fp_vol_ml = float(mat.get("finished_product_volume_ml", 0))
        if fp_vol_ml <= 0:
            adjusted.append(dict(mat))
            continue

        # Same volume basis as check_compliance: % of finished-product mL → µL
        max_active_ml = vio.max_allowed_pct / 100.0 * fp_vol_ml
        max_active_ul = max_active_ml * 1000.0

        capped = dict(mat)
        capped["active_ul"] = max_active_ul
        capped["_capped_from_ul"] = float(mat.get("active_ul", 0))
        capped["_compliance_note"] = (
            f"Capped from {float(mat.get('active_ul', 0)):.1f} µL "
            f"to {max_active_ul:.1f} µL ({vio.max_allowed_pct}% limit)."
        )
        adjusted.append(capped)

    return adjusted


def compare_snapshots(
    s1: RegulatorySnapshot,
    s2: RegulatorySnapshot,
) -> list[str]:
    """Return a human-readable diff between two regulatory snapshots.

    Compares every field of the two snapshots and returns a list of
    strings describing what changed.  An empty list means the snapshots
    are identical.
    """
    diffs: list[str] = []

    if s1.snapshot_id != s2.snapshot_id:
        diffs.append(f"  snapshot_id: {s1.snapshot_id!r} → {s2.snapshot_id!r}")
    if s1.jurisdiction != s2.jurisdiction:
        diffs.append(f"  jurisdiction: {s1.jurisdiction!r} → {s2.jurisdiction!r}")
    if s1.product_category != s2.product_category:
        diffs.append(f"  product_category: {s1.product_category!r} → {s2.product_category!r}")
    if s1.rule_set != s2.rule_set:
        diffs.append(f"  rule_set: {s1.rule_set!r} → {s2.rule_set!r}")
    if s1.effective_date != s2.effective_date:
        diffs.append(f"  effective_date: {s1.effective_date!r} → {s2.effective_date!r}")
    if s1.source_url != s2.source_url:
        diffs.append(f"  source_url: {s1.source_url!r} → {s2.source_url!r}")
    if s1.hash != s2.hash:
        diffs.append(f"  hash: {s1.hash!r} → {s2.hash!r}")
    if s1.notes != s2.notes:
        diffs.append(f"  notes: {s1.notes!r} → {s2.notes!r}")

    if not diffs:
        return ["Snapshots are identical."]

    header = f"Diff: {s1.snapshot_id} → {s2.snapshot_id}"
    return [header] + diffs


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _generate_snapshot_id() -> str:
    """Return a short unique snapshot identifier."""
    return f"snap_{uuid.uuid4().hex[:12]}"


def _compute_hash(data: dict[str, Any]) -> str:
    """Return a SHA-256 hex digest of the serialised *data* dict."""
    raw = str(sorted(data.items())).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def make_snapshot(
    jurisdiction: str,
    product_category: str,
    rule_set: str,
    effective_date: str | None = None,
    source_url: str = "",
    notes: str = "",
) -> RegulatorySnapshot:
    """Convenience factory that auto-generates *snapshot_id* and *hash*.

    The hash is computed from the jurisdiction, product_category, rule_set,
    and effective_date — enough to detect structural drift between snapshots
    that should be identical.
    """
    if effective_date is None:
        effective_date = datetime.date.today().isoformat()

    content: dict[str, Any] = {
        "jurisdiction": jurisdiction,
        "product_category": product_category,
        "rule_set": rule_set,
        "effective_date": effective_date,
    }

    return RegulatorySnapshot(
        snapshot_id=_generate_snapshot_id(),
        jurisdiction=jurisdiction,
        product_category=product_category,
        rule_set=rule_set,
        effective_date=effective_date,
        source_url=source_url,
        hash=_compute_hash(content),
        notes=notes,
    )


__all__ = [
    "ComplianceResult",
    "REDUCED_RISK_PRODUCT_TYPES",
    "RegulatorySnapshot",
    "check_compliance",
    "compare_snapshots",
    "generate_compliant_build",
    "make_snapshot",
]
