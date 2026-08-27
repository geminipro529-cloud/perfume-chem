"""DNA-preserving structural chassis derivation and validation.

Ports DNA_PRESERVING_STRUCTURAL_CHASSIS_PROTOCOL.md + suite chassis.py.

The chassis is the minimal structural skeleton of a perfume — the set of
materials that define its identity and cannot be removed or substituted
without changing the perfume's fundamental character.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from engine.domain_errors import ReconstructionInputError

# ═══════════════════════════════════════════════════════════════════════════════
# Classification constants
# ═══════════════════════════════════════════════════════════════════════════════

IMMUTABLE_CORE: str = "immutable_core"
"""Material that is absolutely essential — removing it destroys the perfume's
identity.  Never moved to the module."""

PROTECTED_ANCHOR: str = "protected_anchor"
"""Material that must stay in the core at a minimum floor dose but may have
surplus moved to the module."""

INTERFACE_RING: str = "interface_ring"
"""Material that sits at the boundary between core and module — can be
moved either way depending on the module envelope."""

MODULE_MOBILE: str = "module_mobile"
"""Material that is fully mobile — can be moved to the module socket
without affecting core identity."""

UNKNOWN_PROTECTED: str = "unknown_protected"
"""Material whose role is unknown but assumed structurally important
(conservative default)."""

UNKNOWN_MODULE_CANDIDATE: str = "unknown_module_candidate"
"""Material whose role is unknown but assumed non-essential (aggressive
default)."""

TECHNICAL: str = "technical"
"""Material present for technical reasons (solvent, preservative, diluent)
— never part of the identity."""

CARRIER: str = "carrier"
"""Material that serves as a carrier or diluent for other materials —
structural but not identity-defining."""


# ═══════════════════════════════════════════════════════════════════════════════
# Data types
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class ChassisRow:
    """A single material row in a chassis partition.

    Parameters
    ----------
    ingredient : str
        Material name.
    raw_ul : float
        Total raw µL of this material in the formula.
    active_ul : float
        Active (undiluted-equivalent) µL.
    core_raw_ul : float
        Raw µL assigned to the immutable core.
    module_raw_ul : float
        Raw µL assigned to the module socket.
    classification : str
        One of the classification constants defined above.
    """

    ingredient: str
    raw_ul: float
    active_ul: float
    core_raw_ul: float
    module_raw_ul: float
    classification: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChassisRow:
        return cls(
            ingredient=str(data.get("ingredient", "")),
            raw_ul=float(data.get("raw_ul", 0.0)),
            active_ul=float(data.get("active_ul", 0.0)),
            core_raw_ul=float(data.get("core_raw_ul", 0.0)),
            module_raw_ul=float(data.get("module_raw_ul", 0.0)),
            classification=str(data.get("classification", "")),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "ingredient": self.ingredient,
            "raw_ul": round(float(self.raw_ul), 4),
            "active_ul": round(float(self.active_ul), 4),
            "core_raw_ul": round(float(self.core_raw_ul), 4),
            "module_raw_ul": round(float(self.module_raw_ul), 4),
            "classification": self.classification,
        }


@dataclass(frozen=True, slots=True)
class ChassisPartition:
    """A complete chassis partition of a formula into core + module.

    Parameters
    ----------
    formula_name : str
        Name of the formula this partition applies to.
    core_total_ul : float
        Sum of core_raw_ul across all rows.
    module_total_ul : float
        Sum of module_raw_ul across all rows.
    total_ul : float
        Sum of raw_ul across all rows (= core_total_ul + module_total_ul).
    rows : tuple[ChassisRow, ...]
        Ordered rows of the partition.
    """

    formula_name: str
    core_total_ul: float
    module_total_ul: float
    total_ul: float
    rows: tuple[ChassisRow, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChassisPartition:
        raw_rows = data.get("rows", ())
        if isinstance(raw_rows, (list, tuple)):
            rows = tuple(ChassisRow.from_dict(r) if isinstance(r, dict) else r for r in raw_rows)
        else:
            rows = ()
        return cls(
            formula_name=str(data.get("formula_name", "")),
            core_total_ul=float(data.get("core_total_ul", 0.0)),
            module_total_ul=float(data.get("module_total_ul", 0.0)),
            total_ul=float(data.get("total_ul", 0.0)),
            rows=rows,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "formula_name": self.formula_name,
            "core_total_ul": round(float(self.core_total_ul), 4),
            "module_total_ul": round(float(self.module_total_ul), 4),
            "total_ul": round(float(self.total_ul), 4),
            "rows": [r.as_dict() for r in self.rows],
        }


@dataclass(frozen=True, slots=True)
class ModuleEnvelope:
    """Constraints and specifications for a module socket.

    Parameters
    ----------
    socket_raw_ul : float
        Total raw µL capacity of the module socket.
    active_range : tuple[float, float]
        (min, max) active µL that the module should contain.
    carrier_range : tuple[float, float]
        (min, max) carrier/diluent µL in the module.
    anchor_minimums : dict[str, float]
        Material → minimum core_raw_ul that must remain in the core.
    required_roles : tuple[str, ...]
        Functional roles that the module must collectively cover.
    family_caps : dict[str, float]
        Material family → maximum fraction of module socket.
    temporal_ranges : dict[str, tuple[float, float]]
        Temporal window label → (min_ul, max_ul) for the module.
    forbidden_materials : tuple[str, ...]
        Materials that must never appear in the module.
    """

    socket_raw_ul: float
    active_range: tuple[float, float]
    carrier_range: tuple[float, float]
    anchor_minimums: dict[str, float]
    required_roles: tuple[str, ...]
    family_caps: dict[str, float]
    temporal_ranges: dict[str, tuple[float, float]]
    forbidden_materials: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModuleEnvelope:
        raw_active = data.get("active_range", (0.0, 0.0))
        raw_carrier = data.get("carrier_range", (0.0, 0.0))
        raw_temporal = data.get("temporal_ranges", {})
        return cls(
            socket_raw_ul=float(data.get("socket_raw_ul", 0.0)),
            active_range=(
                float(raw_active[0]) if raw_active else 0.0,
                float(raw_active[1]) if len(raw_active) > 1 else 0.0,
            ),
            carrier_range=(
                float(raw_carrier[0]) if raw_carrier else 0.0,
                float(raw_carrier[1]) if len(raw_carrier) > 1 else 0.0,
            ),
            anchor_minimums=dict(data.get("anchor_minimums", {})),
            required_roles=tuple(data.get("required_roles", ())),
            family_caps=dict(data.get("family_caps", {})),
            temporal_ranges={
                str(k): (
                    float(v[0]) if v else 0.0,
                    float(v[1]) if len(v) > 1 else 0.0,
                )
                for k, v in raw_temporal.items()
            },
            forbidden_materials=tuple(data.get("forbidden_materials", ())),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "socket_raw_ul": round(float(self.socket_raw_ul), 4),
            "active_range": (
                round(float(self.active_range[0]), 4),
                round(float(self.active_range[1]), 4),
            ),
            "carrier_range": (
                round(float(self.carrier_range[0]), 4),
                round(float(self.carrier_range[1]), 4),
            ),
            "anchor_minimums": dict(self.anchor_minimums),
            "required_roles": list(self.required_roles),
            "family_caps": dict(self.family_caps),
            "temporal_ranges": {
                k: (round(float(v[0]), 4), round(float(v[1]), 4))
                for k, v in self.temporal_ranges.items()
            },
            "forbidden_materials": list(self.forbidden_materials),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════════════════


def validate_partition(
    chassis: ChassisPartition,
    expected_target: float,
    expected_core: float,
    expected_module: float,
) -> list[str]:
    """Validate that a chassis partition matches expected totals.

    Checks:
        - total_ul == expected_target
        - core_total_ul == expected_core
        - module_total_ul == expected_module
        - For every row: core_raw_ul + module_raw_ul == raw_ul

    Parameters
    ----------
    chassis : ChassisPartition
        The partition to validate.
    expected_target : float
        Expected total raw µL.
    expected_core : float
        Expected core total raw µL.
    expected_module : float
        Expected module total raw µL.

    Returns
    -------
    list[str]
        List of violation messages.  Empty list means all checks passed.
    """
    errors: list[str] = []
    tol = 1e-6

    if abs(chassis.total_ul - expected_target) > tol:
        errors.append(f"total_ul {chassis.total_ul} != expected {expected_target}")

    if abs(chassis.core_total_ul - expected_core) > tol:
        errors.append(f"core_total_ul {chassis.core_total_ul} != expected {expected_core}")

    if abs(chassis.module_total_ul - expected_module) > tol:
        errors.append(f"module_total_ul {chassis.module_total_ul} != expected {expected_module}")

    for row in chassis.rows:
        row_sum = row.core_raw_ul + row.module_raw_ul
        if abs(row_sum - row.raw_ul) > tol:
            errors.append(
                f"{row.ingredient}: core({row.core_raw_ul}) + module("
                f"{row.module_raw_ul}) = {row_sum} != raw({row.raw_ul})"
            )

    return errors


def validate_anchor_floors(
    chassis: ChassisPartition,
    envelope: ModuleEnvelope,
) -> list[str]:
    """Validate that every anchored material meets its minimum core dose.

    For each material listed in *envelope.anchor_minimums*, checks that
    its ``core_raw_ul`` in the partition is >= the specified floor.

    Parameters
    ----------
    chassis : ChassisPartition
        The partition to validate.
    envelope : ModuleEnvelope
        The module envelope containing anchor minimums.

    Returns
    -------
    list[str]
        List of violation messages.  Empty list means all floors met.
    """
    violations: list[str] = []
    tol = 1e-6

    row_map: dict[str, ChassisRow] = {r.ingredient: r for r in chassis.rows}

    for material, floor in envelope.anchor_minimums.items():
        row = row_map.get(material)
        if row is None:
            violations.append(
                f"Material '{material}' has anchor floor {floor} but "
                f"is not present in the partition"
            )
        elif row.core_raw_ul + tol < floor:
            violations.append(
                f"Material '{material}' core_raw_ul {row.core_raw_ul} is below anchor floor {floor}"
            )

    return violations


def validate_module(
    module_rows: list[ChassisRow],
    expected_total: float,
) -> list[str]:
    """Validate that the sum of module_raw_ul equals the expected total.

    Parameters
    ----------
    module_rows : list[ChassisRow]
        Rows assigned to the module socket.
    expected_total : float
        Expected sum of module_raw_ul.

    Returns
    -------
    list[str]
        List of violation messages.  Empty list means the sum matches.
    """
    errors: list[str] = []
    total = sum(r.module_raw_ul for r in module_rows)
    if abs(total - expected_total) > 1e-6:
        errors.append(f"module_raw_ul sum {total} != expected total {expected_total}")
    return errors


# ═══════════════════════════════════════════════════════════════════════════════
# Hashing
# ═══════════════════════════════════════════════════════════════════════════════


def canonical_hash(rows: list[dict], fields: list[str]) -> str:
    """Compute a canonical SHA-256 hash for a set of chassis rows.

    The hash is computed over a JSON-serialised payload containing only
    the specified *fields* from each row, sorted by key and compactly
    encoded.  This ensures deterministic, portable fingerprints.

    Parameters
    ----------
    rows : list[dict]
        List of row dicts (e.g. from ``ChassisRow.as_dict()``).
    fields : list[str]
        Subset of keys to include in the hash payload.

    Returns
    -------
    str
        Hex-encoded SHA-256 digest.
    """
    payload: list[dict[str, Any]] = []
    for row in rows:
        filtered = {k: row[k] for k in fields if k in row}
        payload.append(filtered)

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# CSV parsing
# ═══════════════════════════════════════════════════════════════════════════════


def create_chassis_from_csv_rows(
    csv_rows: list[dict[str, str]],
) -> ChassisPartition:
    """Parse CSV rows into a ``ChassisPartition``.

    Expected CSV keys (case-insensitive on first row):
        ingredient, raw_uL, active_uL, core_raw_uL, module_raw_uL,
        classification

    Parameters
    ----------
    csv_rows : list[dict[str, str]]
        List of row dicts as returned by ``csv.DictReader``.

    Returns
    -------
    ChassisPartition
        Populated partition with computed totals.

    Raises
    ------
    ValueError
        If required keys are missing from the first row.
    """
    if not csv_rows:
        raise ReconstructionInputError("chassis roster cannot be empty")

    # Normalise keys from the first row.
    raw_keys = list(csv_rows[0].keys())
    key_map: dict[str, str] = {}
    for k in raw_keys:
        key_map[k.lower().strip()] = k

    required = [
        "ingredient",
        "raw_ul",
        "active_ul",
        "core_raw_ul",
        "module_raw_ul",
        "classification",
    ]
    for r in required:
        if r not in key_map:
            raise ValueError(
                f"Missing required CSV column '{r}'. Available keys: {list(key_map.keys())}"
            )

    def _safe_float(val: str) -> float:
        try:
            return float(val.strip())
        except (ValueError, AttributeError):
            return 0.0

    rows: list[ChassisRow] = []
    for row in csv_rows:
        ingredient = row[key_map["ingredient"]].strip()
        raw_ul = _safe_float(row[key_map["raw_ul"]])
        active_ul = _safe_float(row[key_map["active_ul"]])
        core_raw_ul = _safe_float(row[key_map["core_raw_ul"]])
        module_raw_ul = _safe_float(row[key_map["module_raw_ul"]])
        classification = row[key_map["classification"]].strip().lower()

        rows.append(
            ChassisRow(
                ingredient=ingredient,
                raw_ul=raw_ul,
                active_ul=active_ul,
                core_raw_ul=core_raw_ul,
                module_raw_ul=module_raw_ul,
                classification=classification,
            )
        )

    core_total = sum(r.core_raw_ul for r in rows)
    module_total = sum(r.module_raw_ul for r in rows)
    total = sum(r.raw_ul for r in rows)

    return ChassisPartition(
        formula_name="",
        core_total_ul=core_total,
        module_total_ul=module_total,
        total_ul=total,
        rows=tuple(rows),
    )


__all__ = [
    "CARRIER",
    "ChassisPartition",
    "ChassisRow",
    "IMMUTABLE_CORE",
    "INTERFACE_RING",
    "MODULE_MOBILE",
    "ModuleEnvelope",
    "PROTECTED_ANCHOR",
    "TECHNICAL",
    "UNKNOWN_MODULE_CANDIDATE",
    "UNKNOWN_PROTECTED",
    "canonical_hash",
    "create_chassis_from_csv_rows",
    "validate_anchor_floors",
    "validate_module",
    "validate_partition",
]
