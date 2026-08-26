"""Derive AuthorityVector from EvidenceLedger using coverage-aware aggregation.

NEVER uses max confidence — uses coverage fraction, independence, and
contradiction penalties.
"""

from __future__ import annotations

from engine.evidence.ledger import EvidenceLedger
from engine.ifra_safety import get_ifra_limit
from engine.target.formula import AuthorityVector, TargetFormula


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def derive_authority_from_evidence(
    target: TargetFormula,
    evidence_ledger: EvidenceLedger,
    safety_ledger: EvidenceLedger | None = None,
) -> AuthorityVector:
    """Compute an :class:`AuthorityVector` from a target and evidence ledger.

    Each dimension is scored by coverage fraction (materials with data /
    total materials), with optional contradiction penalties for quantity.

    Parameters
    ----------
    target:
        The target formula hypothesis.
    evidence_ledger:
        Ledger containing evidence claims about the target.
    safety_ledger:
        Optional separate ledger for safety evidence.  If ``None``, safety
        is derived from the built-in IFRA limit database.

    Returns
    -------
    AuthorityVector
        Per-dimension authority scores.  Dimensions that require separate
        measurement pipelines (matrix, headspace, sensory, inventory,
        natural_lot) default to 0.0.
    """
    total = len(target.target_materials)
    if total == 0:
        return AuthorityVector()

    # ── identity ──────────────────────────────────────────────────────────
    identity = derive_identity_authority(target, evidence_ledger)

    # ── quantity ──────────────────────────────────────────────────────────
    quantity = _derive_quantity_authority(target, evidence_ledger)

    # ── safety ────────────────────────────────────────────────────────────
    safety = derive_safety_authority(target)

    # ── grade ─────────────────────────────────────────────────────────────
    grade = _derive_grade_authority(target)

    # ── release ───────────────────────────────────────────────────────────
    release = (
        1.0 if (identity >= 0.7 and quantity >= 0.5 and safety >= 0.5 and grade >= 0.5) else 0.0
    )

    return AuthorityVector(
        identity=identity,
        quantity=quantity,
        grade=grade,
        safety=safety,
        release=release,
        # The following dimensions require separate measurement pipelines
        # not yet available — default to 0.0.
        natural_lot=0.0,
        matrix=0.0,
        headspace=0.0,
        sensory=0.0,
        inventory=0.0,
    )


def coverage_score(materials_with_data: int, total_rows: int) -> float:
    """Return the fraction of rows that have data.

    Returns 0.0 when *total_rows* is zero.
    """
    if total_rows <= 0:
        return 0.0
    return materials_with_data / total_rows


def derive_identity_authority(
    target: TargetFormula,
    evidence: EvidenceLedger,
) -> float:
    """Return the fraction of target materials that have at least one
    evidence claim with ``identity_confidence > 0``."""
    total = len(target.target_materials)
    if total == 0:
        return 0.0

    count = 0
    for mat in target.target_materials:
        claims = evidence.get_claims_for_material(mat.identity)
        if any(c.identity_confidence > 0 for c in claims):
            count += 1

    return coverage_score(count, total)


def derive_safety_authority(target: TargetFormula) -> float:
    """Return the fraction of target materials that have a known IFRA limit."""
    total = len(target.target_materials)
    if total == 0:
        return 0.0

    count = 0
    for mat in target.target_materials:
        limit = get_ifra_limit(mat.identity)
        if limit is not None:
            count += 1

    return coverage_score(count, total)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _derive_quantity_authority(
    target: TargetFormula,
    evidence: EvidenceLedger,
) -> float:
    """Quantity authority = coverage fraction minus contradiction penalty.

    The contradiction penalty is 0.1 per material that has contradictory
    quantity claims, clamped to a maximum total penalty of 0.5.
    """
    total = len(target.target_materials)
    if total == 0:
        return 0.0

    count_with_quantity = 0
    contradiction_count = 0

    for mat in target.target_materials:
        claims = evidence.get_claims_for_material(mat.identity)
        has_quantity = any(c.quantity_confidence > 0 for c in claims)
        if has_quantity:
            count_with_quantity += 1

        # Detect contradictions: multiple claims with different reported_value
        # for the same material.
        values = {c.reported_value for c in claims if c.reported_value is not None}
        if len(values) > 1:
            contradiction_count += 1

    raw = coverage_score(count_with_quantity, total)
    penalty = min(0.5, contradiction_count * 0.1)
    return max(0.0, raw - penalty)


def _derive_grade_authority(target: TargetFormula) -> float:
    """Return the fraction of target materials with a resolved grade."""
    total = len(target.target_materials)
    if total == 0:
        return 0.0

    count = 0
    for mat in target.target_materials:
        g = mat.grade.strip().lower()
        if g and g != "unresolved":
            count += 1

    return coverage_score(count, total)


__all__ = [
    "AuthorityVector",
    "coverage_score",
    "derive_authority_from_evidence",
    "derive_identity_authority",
    "derive_safety_authority",
]
