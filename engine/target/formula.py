"""Target reconstruction ledger — stores the best current hypothesis of a
perfume's formula, independent of inventory.

The target NEVER references inventory; substitutions live in the build layer.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from engine.domain_errors import ReconstructionInputError
from engine.name_utils import normalize_name

# ---------------------------------------------------------------------------
# Authority tier constants
# ---------------------------------------------------------------------------

TIER_0_NOTE_INSPIRED = "note-inspired reconstruction"
TIER_1_DOCUMENTARY_FUNCTIONAL_HYPOTHESIS = "documentary functional hypothesis"
TIER_2_ENSEMBLE_CENTER = "sensory recombination hypothesis"
TIER_3_ANALYTICALLY_CONSTRAINED = "analytically constrained"
TIER_4_QUANTITATIVELY_CALIBRATED = "quantitatively calibrated"
TIER_5_BLIND_SENSORY_VALIDATED = "blind sensory validated"
TIER_6_AUTHENTICATED_FORMULA = "authenticated formula"

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TargetMaterial:
    """A single material in the target reconstruction hypothesis.

    Stores the best estimate of identity, quantity, and confidence for one
    ingredient, independent of any specific inventory stock.
    """

    identity: str  # resolved name or "UNKNOWN_*"
    row_id: str = ""
    canonical_identity: str = ""
    source_name: str = ""
    grade: str = "unresolved"
    supplier_grade: str = ""
    presence_probability: float = 1.0  # 0.0-1.0
    active_amount_median: float = 0.0  # in µL or as specified
    active_amount_p05: float = 0.0  # 5th percentile
    active_amount_p95: float = 0.0  # 95th percentile
    active_amount_unit: str = "uL"
    raw_amount: float = 0.0  # raw stock volume including carrier
    concentration: float = 1.0  # stock active fraction, 0.0-1.0
    concentration_basis: str = "unspecified"  # w/w, v/v, w/v
    carrier: str = ""
    functional_roles: tuple[str, ...] = ()
    accord_membership: tuple[str, ...] = ()
    time_windows: tuple[str, ...] = ()  # e.g. "opening", "heart", "drydown"
    evidence_links: tuple[str, ...] = ()  # evidence claim IDs
    identity_confidence: float = 0.0
    quantity_confidence: float = 0.0
    unknown_status: str = ""  # empty if known, else UNKNOWN_CAPTIVE, etc.
    source_record: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    extensions: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TargetMaterial:
        return cls(
            identity=str(data["identity"]),
            row_id=str(data.get("row_id") or ""),
            canonical_identity=str(data.get("canonical_identity") or ""),
            source_name=str(data.get("source_name") or ""),
            grade=str(data.get("grade", "unresolved")),
            supplier_grade=str(data.get("supplier_grade") or ""),
            presence_probability=float(data.get("presence_probability", 1.0)),
            active_amount_median=float(data.get("active_amount_median", 0.0)),
            active_amount_p05=float(data.get("active_amount_p05", 0.0)),
            active_amount_p95=float(data.get("active_amount_p95", 0.0)),
            active_amount_unit=str(data.get("active_amount_unit", "uL")),
            raw_amount=float(data.get("raw_amount", 0.0)),
            concentration=float(data.get("concentration", 1.0)),
            concentration_basis=str(data.get("concentration_basis", "unspecified")),
            carrier=str(data.get("carrier") or ""),
            functional_roles=tuple(str(x) for x in data.get("functional_roles") or ()),
            accord_membership=tuple(str(x) for x in data.get("accord_membership") or ()),
            time_windows=tuple(str(x) for x in data.get("time_windows") or ()),
            evidence_links=tuple(str(x) for x in data.get("evidence_links") or ()),
            identity_confidence=float(data.get("identity_confidence", 0.0)),
            quantity_confidence=float(data.get("quantity_confidence", 0.0)),
            unknown_status=str(data.get("unknown_status") or ""),
            source_record=_as_dict(data.get("source_record"), field_name="source_record"),
            provenance=_as_dict(data.get("provenance"), field_name="provenance"),
            notes=str(data.get("notes") or ""),
            extensions=_as_dict(data.get("extensions"), field_name="extensions"),
        )


@dataclass(frozen=True, slots=True)
class TargetFormula:
    """A complete target reconstruction hypothesis for one perfume product.

    Aggregates material-level estimates into a single formula hypothesis
    with an authority tier and optional acceptance timestamp.
    """

    product_id: str  # brand + name + concentration + batch year
    reference_brand: str = ""
    reference_name: str = ""
    reference_concentration: str = ""
    reference_batch_year: str = ""
    reference_url: str = ""
    target_materials: tuple[TargetMaterial, ...] = ()
    total_raw_ul: float = 0.0
    total_active_ul: float = 0.0
    authority_label: str = TIER_0_NOTE_INSPIRED
    formula_hash: str = ""
    accepted: bool = False
    accepted_timestamp: str | None = None
    evidence_ledger_ref: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "reference_brand": self.reference_brand,
            "reference_name": self.reference_name,
            "reference_concentration": self.reference_concentration,
            "reference_batch_year": self.reference_batch_year,
            "reference_url": self.reference_url,
            "target_materials": [m.as_dict() for m in self.target_materials],
            "total_raw_ul": self.total_raw_ul,
            "total_active_ul": self.total_active_ul,
            "authority_label": self.authority_label,
            "formula_hash": self.formula_hash,
            "accepted": self.accepted,
            "accepted_timestamp": self.accepted_timestamp,
            "evidence_ledger_ref": self.evidence_ledger_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TargetFormula:
        materials_raw = data.get("target_materials") or ()
        materials = tuple(
            TargetMaterial.from_dict(m) if isinstance(m, dict) else m for m in materials_raw
        )
        return cls(
            product_id=str(data["product_id"]),
            reference_brand=str(data.get("reference_brand") or ""),
            reference_name=str(data.get("reference_name") or ""),
            reference_concentration=str(data.get("reference_concentration") or ""),
            reference_batch_year=str(data.get("reference_batch_year") or ""),
            reference_url=str(data.get("reference_url") or ""),
            target_materials=materials,
            total_raw_ul=float(data.get("total_raw_ul", 0.0)),
            total_active_ul=float(data.get("total_active_ul", 0.0)),
            authority_label=str(data.get("authority_label", TIER_0_NOTE_INSPIRED)),
            formula_hash=str(data.get("formula_hash") or ""),
            accepted=bool(data.get("accepted", False)),
            accepted_timestamp=str(data["accepted_timestamp"])
            if data.get("accepted_timestamp")
            else None,
            evidence_ledger_ref=str(data.get("evidence_ledger_ref") or ""),
        )


@dataclass(frozen=True, slots=True)
class AuthorityVector:
    """Tracks authority per dimension — NEVER averaged into one number."""

    identity: float = 0.0
    quantity: float = 0.0
    grade: float = 0.0
    natural_lot: float = 0.0
    matrix: float = 0.0
    headspace: float = 0.0
    sensory: float = 0.0
    inventory: float = 0.0
    safety: float = 0.0
    release: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuthorityVector:
        return cls(
            identity=float(data.get("identity", 0.0)),
            quantity=float(data.get("quantity", 0.0)),
            grade=float(data.get("grade", 0.0)),
            natural_lot=float(data.get("natural_lot", 0.0)),
            matrix=float(data.get("matrix", 0.0)),
            headspace=float(data.get("headspace", 0.0)),
            sensory=float(data.get("sensory", 0.0)),
            inventory=float(data.get("inventory", 0.0)),
            safety=float(data.get("safety", 0.0)),
            release=float(data.get("release", 0.0)),
        )


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def accept_target_version(
    formula: TargetFormula,
    timestamp: str | None = None,
) -> TargetFormula:
    """Return a new *TargetFormula* with ``accepted=True`` and timestamp set.

    Uses ``datetime.now(timezone.utc)`` if *timestamp* is not provided.
    """
    ts = timestamp or (datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"))
    return TargetFormula(
        product_id=formula.product_id,
        reference_brand=formula.reference_brand,
        reference_name=formula.reference_name,
        reference_concentration=formula.reference_concentration,
        reference_batch_year=formula.reference_batch_year,
        reference_url=formula.reference_url,
        target_materials=formula.target_materials,
        total_raw_ul=formula.total_raw_ul,
        total_active_ul=formula.total_active_ul,
        authority_label=formula.authority_label,
        formula_hash=formula.formula_hash,
        accepted=True,
        accepted_timestamp=ts,
        evidence_ledger_ref=formula.evidence_ledger_ref,
    )


_TARGET_ROW_FIELDS = frozenset(
    {
        "row_id",
        "identity",
        "canonical_identity",
        "source_name",
        "grade",
        "supplier_grade",
        "presence_probability",
        "active_amount_median",
        "active_amount_p05",
        "active_amount_p95",
        "active_amount_unit",
        "raw_amount",
        "concentration",
        "concentration_basis",
        "carrier",
        "functional_roles",
        "accord_membership",
        "time_windows",
        "evidence_links",
        "identity_confidence",
        "quantity_confidence",
        "unknown_status",
        "source_record",
        "provenance",
        "notes",
        "extensions",
    }
)


def create_target_from_rows(
    rows: list[dict[str, Any]],
    *,
    strict: bool = True,
) -> TargetFormula:
    """Build a *TargetFormula* from a list of row dicts.

    Each row dict must contain at least ``identity``, ``raw_amount``,
    ``concentration``, and ``concentration_basis``.  Optional keys include
    ``carrier``, ``functional_roles``, ``accord_membership``,
    ``time_windows``, and ``active_amount_median``.

    Totals are computed from the rows and a formula hash is generated.
    """
    if not rows:
        raise ReconstructionInputError("target rows cannot be empty")

    materials: list[TargetMaterial] = []
    total_raw = 0.0
    total_active = 0.0

    for row_index, row in enumerate(rows, start=1):
        unknown_fields = set(row) - _TARGET_ROW_FIELDS
        extensions = _as_dict(row.get("extensions"), field_name="extensions")
        if unknown_fields:
            if strict:
                raise ReconstructionInputError(
                    "unknown target-row fields: " + ", ".join(sorted(unknown_fields))
                )
            namespace_raw = extensions.get("a1.v1", {})
            if not isinstance(namespace_raw, dict):
                raise ReconstructionInputError(
                    "extensions['a1.v1'] must be an object when preserving unknown fields"
                )
            namespace = dict(namespace_raw)
            namespace.update({key: row[key] for key in sorted(unknown_fields)})
            extensions = {**extensions, "a1.v1": namespace}

        identity = str(row.get("identity") or "UNKNOWN_*")
        row_id = str(row.get("row_id") or f"row-{row_index:04d}")
        canonical_identity = str(row.get("canonical_identity") or normalize_name(identity))
        source_name = str(row.get("source_name") or identity)
        raw_amount = float(row.get("raw_amount") or 0.0)
        concentration = float(row.get("concentration") or 1.0)
        concentration_basis = str(row.get("concentration_basis") or "unspecified")
        carrier = str(row.get("carrier") or "")
        active_amount_raw = row.get("active_amount_median")
        active_amount_median = (
            float(active_amount_raw)
            if active_amount_raw is not None
            else raw_amount * concentration
        )

        functional_roles = _to_tuple_str(row.get("functional_roles"))
        accord_membership = _to_tuple_str(row.get("accord_membership"))
        time_windows = _to_tuple_str(row.get("time_windows"))
        evidence_links = _to_tuple_str(row.get("evidence_links", ()))
        identity_confidence = float(row.get("identity_confidence", 0.0))
        quantity_confidence = float(row.get("quantity_confidence", 0.0))
        active_amount_p05 = float(row.get("active_amount_p05", 0.0))
        active_amount_p95 = float(row.get("active_amount_p95", 0.0))
        grade = str(row.get("grade", "unresolved"))
        supplier_grade = str(row.get("supplier_grade") or "")
        presence_probability = float(row.get("presence_probability", 1.0))
        active_amount_unit = str(row.get("active_amount_unit") or "uL")
        unknown_status = str(row.get("unknown_status") or "")
        source_record = _as_dict(row.get("source_record"), field_name="source_record")
        provenance = _as_dict(row.get("provenance"), field_name="provenance")
        notes = str(row.get("notes") or "")

        mat = TargetMaterial(
            identity=identity,
            row_id=row_id,
            canonical_identity=canonical_identity,
            source_name=source_name,
            raw_amount=raw_amount,
            concentration=concentration,
            concentration_basis=concentration_basis,
            carrier=carrier,
            active_amount_median=active_amount_median,
            functional_roles=functional_roles,
            accord_membership=accord_membership,
            time_windows=time_windows,
            evidence_links=evidence_links,
            identity_confidence=identity_confidence,
            quantity_confidence=quantity_confidence,
            active_amount_p05=active_amount_p05,
            active_amount_p95=active_amount_p95,
            grade=grade,
            supplier_grade=supplier_grade,
            presence_probability=presence_probability,
            active_amount_unit=active_amount_unit,
            unknown_status=unknown_status,
            source_record=source_record,
            provenance=provenance,
            notes=notes,
            extensions=extensions,
        )
        materials.append(mat)
        total_raw += raw_amount
        total_active += active_amount_median

    formula_hash = compute_target_hash(materials)

    return TargetFormula(
        product_id=_derive_product_id(materials),
        target_materials=tuple(materials),
        total_raw_ul=total_raw,
        total_active_ul=total_active,
        formula_hash=formula_hash,
    )


def compute_target_hash(materials: list[TargetMaterial]) -> str:
    """SHA-256 hash of the sorted target material identities and median amounts.

    Uses ``hashlib`` and ``json`` with ``sort_keys=True`` for deterministic
    output.
    """
    records = []
    for mat in materials:
        records.append(
            {
                "identity": normalize_name(mat.identity),
                "active_amount_median": mat.active_amount_median,
                "active_amount_unit": mat.active_amount_unit,
            }
        )
    records.sort(key=lambda r: (r["identity"], r["active_amount_median"]))
    payload = json.dumps(records, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_tuple_str(value: object) -> tuple[str, ...]:
    """Convert a value to a tuple of strings.

    Accepts ``None``, a single string, or an iterable of strings.
    """
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item))
    return (str(value),)


def _as_dict(value: object, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ReconstructionInputError(f"{field_name} must be an object")
    return dict(value)


def _derive_product_id(materials: list[TargetMaterial]) -> str:
    """Derive a unique product ID from the material list.

    Uses a short hash of the material identities so the ID is deterministic
    but not human-readable.
    """
    names = sorted(normalize_name(m.identity) for m in materials)
    seed = json.dumps(names, sort_keys=True, ensure_ascii=False)
    short_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"target_{short_hash}"


__all__ = [
    "AuthorityVector",
    "TIER_0_NOTE_INSPIRED",
    "TIER_1_DOCUMENTARY_FUNCTIONAL_HYPOTHESIS",
    "TIER_2_ENSEMBLE_CENTER",
    "TIER_3_ANALYTICALLY_CONSTRAINED",
    "TIER_4_QUANTITATIVELY_CALIBRATED",
    "TIER_5_BLIND_SENSORY_VALIDATED",
    "TIER_6_AUTHENTICATED_FORMULA",
    "TargetFormula",
    "TargetMaterial",
    "accept_target_version",
    "compute_target_hash",
    "create_target_from_rows",
]
