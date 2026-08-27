"""Immutable formula versioning with version graph tracking.

Each FormulaVersion captures a snapshot of a formula at a point in time,
along with the changes that produced it.  Versions form a directed acyclic
graph (DAG) rooted at the initial CREATE node.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from engine.calibration.hashing import stable_formula_hash

# ---------------------------------------------------------------------------
# Change types - kept as module-level constants for ergonomic reference
# ---------------------------------------------------------------------------

CHANGE_CREATE = "CREATE"
CHANGE_SUBSTITUTE = "SUBSTITUTE"
CHANGE_RESCUE = "RESCUE"
CHANGE_STYLISTIC = "STYLISTIC"
CHANGE_REBALANCE = "REBALANCE"
CHANGE_CORRECTION = "CORRECTION"

CHANGE_ADD = "ADD"
CHANGE_REMOVE = "REMOVE"
CHANGE_INCREASE = "INCREASE"
CHANGE_DECREASE = "DECREASE"

MODE_RECONSTRUCTION = "RECONSTRUCTION"
MODE_CREATIVE_FORMULATION = "CREATIVE_FORMULATION"
MODE_LIVE_BATCH = "LIVE_BATCH"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FormulaChange:
    """A single atomic change to one material in a formula."""

    material_name: str
    change_type: str  # ADD, REMOVE, INCREASE, DECREASE, SUBSTITUTE
    old_value: float | None = None
    new_value: float | None = None
    old_material: str | None = None  # populated for SUBSTITUTE
    new_material: str | None = None  # populated for SUBSTITUTE
    unit: str = "uL"
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FormulaChange:
        return cls(
            material_name=str(data["material_name"]),
            change_type=str(data["change_type"]),
            old_value=float(data["old_value"]) if data.get("old_value") is not None else None,
            new_value=float(data["new_value"]) if data.get("new_value") is not None else None,
            old_material=str(data["old_material"]) if data.get("old_material") else None,
            new_material=str(data["new_material"]) if data.get("new_material") else None,
            unit=str(data.get("unit", "uL")),
            reason=str(data.get("reason") or ""),
        )


@dataclass(frozen=True, slots=True)
class FormulaVersion:
    """An immutable snapshot of a formula at a point in its revision history."""

    version_id: str  # UUID hex
    parent_version_id: str | None  # previous version, None for initial
    timestamp: str  # ISO 8601
    formula_hash: str  # SHA-256 of the formula definition
    change_type: str  # CREATE, SUBSTITUTE, RESCUE, STYLISTIC, REBALANCE, CORRECTION
    changes: tuple[FormulaChange, ...]  # list of changes applied
    description: str = ""
    mode: str = MODE_CREATIVE_FORMULATION

    def as_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "parent_version_id": self.parent_version_id,
            "timestamp": self.timestamp,
            "formula_hash": self.formula_hash,
            "change_type": self.change_type,
            "changes": [c.as_dict() for c in self.changes],
            "description": self.description,
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FormulaVersion:
        changes_raw = data.get("changes") or ()
        changes = tuple(
            FormulaChange.from_dict(c) if isinstance(c, dict) else c for c in changes_raw
        )
        return cls(
            version_id=str(data["version_id"]),
            parent_version_id=str(data["parent_version_id"])
            if data.get("parent_version_id")
            else None,
            timestamp=str(data["timestamp"]),
            formula_hash=str(data["formula_hash"]),
            change_type=str(data["change_type"]),
            changes=changes,
            description=str(data.get("description") or ""),
            mode=str(data.get("mode", MODE_CREATIVE_FORMULATION)),
        )

    @classmethod
    def create_initial(
        cls,
        formula_hash: str,
        *,
        description: str = "",
        mode: str = MODE_CREATIVE_FORMULATION,
    ) -> FormulaVersion:
        """Convenience constructor for the very first version of a formula."""
        return cls(
            version_id=uuid.uuid4().hex,
            parent_version_id=None,
            timestamp=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            formula_hash=formula_hash,
            change_type=CHANGE_CREATE,
            changes=(),
            description=description,
            mode=mode,
        )

    @classmethod
    def derive(
        cls,
        parent: FormulaVersion,
        formula_hash: str,
        change_type: str,
        changes: tuple[FormulaChange, ...],
        *,
        description: str = "",
        mode: str | None = None,
    ) -> FormulaVersion:
        """Create a new version derived from *parent*."""
        return cls(
            version_id=uuid.uuid4().hex,
            parent_version_id=parent.version_id,
            timestamp=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            formula_hash=formula_hash,
            change_type=change_type,
            changes=changes,
            description=description,
            mode=mode if mode is not None else parent.mode,
        )


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------


def version_graph(versions: list[FormulaVersion]) -> dict[str, list[str]]:
    """Build an adjacency list representing the DAG of versions.

    Returns a dict mapping each *version_id* to a list of its child
    *version_id* values.  The root(s) have no parent (``parent_version_id`` is
    ``None``) and will not appear as children of any other node.
    """
    children: dict[str, list[str]] = {v.version_id: [] for v in versions}
    for v in versions:
        if v.parent_version_id is not None:
            parent_list = children.get(v.parent_version_id)
            if parent_list is not None:
                parent_list.append(v.version_id)
    return children


def diff_versions(v1: FormulaVersion, v2: FormulaVersion) -> list[str]:
    """Return human-readable diff lines between two versions.

    Lines describe what changed between *v1* and *v2* by comparing their
    ``changes`` tuples.  When both versions are empty (e.g. the initial
    CREATE), a single metadata line is returned.
    """
    lines: list[str] = []
    lines.append(f"--- {v1.version_id} ({v1.change_type})")
    lines.append(f"+++ {v2.version_id} ({v2.change_type})")

    if not v1.changes and not v2.changes:
        lines.append(f"  (no material changes - {v1.change_type} -> {v2.change_type})")
        return lines

    # Index v1 changes by material name for quick lookup
    v1_by_mat: dict[str, FormulaChange] = {}
    for c in v1.changes:
        v1_by_mat[c.material_name] = c

    v2_by_mat: dict[str, FormulaChange] = {}
    for c in v2.changes:
        v2_by_mat[c.material_name] = c

    all_materials = sorted(set(v1_by_mat) | set(v2_by_mat))

    for mat in all_materials:
        c1 = v1_by_mat.get(mat)
        c2 = v2_by_mat.get(mat)

        if c1 is None and c2 is not None:
            lines.append(f"+ {mat}: {c2.change_type} -> {_fmt_value(c2.new_value, c2.unit)}")
        elif c1 is not None and c2 is None:
            lines.append(f"- {mat}: {c1.change_type} ({_fmt_value(c1.old_value, c1.unit)})")
        elif c1 is not None and c2 is not None:
            if (
                c1.change_type == c2.change_type
                and c1.old_value == c2.old_value
                and c1.new_value == c2.new_value
            ):
                lines.append(f"  {mat}: unchanged")
            else:
                lines.append(
                    f"~ {mat}: {c1.change_type} {_fmt_value(c1.old_value, c1.unit)}->{_fmt_value(c1.new_value, c1.unit)}"
                    f" -> {c2.change_type} {_fmt_value(c2.old_value, c2.unit)}->{_fmt_value(c2.new_value, c2.unit)}"
                )

    return lines


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def compute_formula_hash(
    ingredients_ul: dict[str, float],
    dilutions: dict[str, float] | None = None,
) -> str:
    """Deterministic SHA-256 hash of a formula's ingredients + dilutions.

    Delegates to :func:`engine.calibration.hashing.stable_formula_hash`
    with an empty formula name so the hash is purely ingredient-based.
    """
    return stable_formula_hash("", ingredients_ul, dilutions)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fmt_value(value: float | None, unit: str = "uL") -> str:
    if value is None:
        return "-"
    return f"{value:g}{unit}"


__all__ = [
    "CHANGE_ADD",
    "CHANGE_CORRECTION",
    "CHANGE_CREATE",
    "CHANGE_DECREASE",
    "CHANGE_INCREASE",
    "CHANGE_REBALANCE",
    "CHANGE_REMOVE",
    "CHANGE_RESCUE",
    "CHANGE_STYLISTIC",
    "CHANGE_SUBSTITUTE",
    "FormulaChange",
    "FormulaVersion",
    "MODE_CREATIVE_FORMULATION",
    "MODE_LIVE_BATCH",
    "MODE_RECONSTRUCTION",
    "compute_formula_hash",
    "diff_versions",
    "version_graph",
]
