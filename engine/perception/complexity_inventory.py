"""Fail-closed inventory bindings for target-first complexity modules.

The catalog is a frozen projection of the authoritative V5 workbook.  It keeps
physical availability, stock readiness, and advisory purchase hypotheses as
separate dimensions.  Inventory can constrain a current build, but it cannot
define a target, a material role, richness, liking, or hedonic value.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

_CATALOG_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "governance"
    / "complexity_inventory_catalog_v1.json"
)
_EXPECTED_WORKBOOK_SHA256 = (
    "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
)


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return _text(value, "optional text")


def _key(value: object) -> str:
    return _text(value, "material").casefold()


def _carrier_omission_key(value: str) -> str:
    """Remove only an explicit terminal carrier, preserving stock strength."""

    return re.sub(r"\s+in\s+(?:dpg|tec|dep|ipm)$", "", value).strip()


class InventoryAvailability(str, Enum):
    OWNED = "OWNED"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    PLANNED_ACQUISITION = "PLANNED_ACQUISITION"
    MISSING = "MISSING"
    PREPARABLE_NOT_MIXED = "PREPARABLE_NOT_MIXED"
    VERIFY_FIRST = "VERIFY_FIRST"
    FORBIDDEN = "FORBIDDEN"
    UNLISTED = "UNLISTED"


class StockReadiness(str, Enum):
    EXACT_STOCK_IDENTIFIED = "EXACT_STOCK_IDENTIFIED"
    STOCK_DETAIL_OPEN = "STOCK_DETAIL_OPEN"
    PREPARATION_REQUIRED = "PREPARATION_REQUIRED"
    PROCUREMENT_PENDING = "PROCUREMENT_PENDING"
    NOT_BUILDABLE = "NOT_BUILDABLE"


@dataclass(frozen=True, slots=True)
class CurrentInventoryRecord:
    source_row: int
    canonical_material: str
    status: str
    actual_stocks: str | None
    can_prepare: str | None
    family: str | None
    alias_or_non_equivalent: str | None
    formula_use_policy: str | None
    user_note: str | None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> CurrentInventoryRecord:
        source_row = value.get("source_row")
        if not isinstance(source_row, int) or source_row < 1:
            raise ValueError("source_row must be a positive integer")
        return cls(
            source_row=source_row,
            canonical_material=_text(
                value.get("canonical_material"), "canonical_material"
            ),
            status=_text(value.get("status"), "status"),
            actual_stocks=_optional_text(value.get("actual_stocks")),
            can_prepare=_optional_text(value.get("can_prepare")),
            family=_optional_text(value.get("family")),
            alias_or_non_equivalent=_optional_text(
                value.get("alias_or_non_equivalent")
            ),
            formula_use_policy=_optional_text(value.get("formula_use_policy")),
            user_note=_optional_text(value.get("user_note")),
        )


@dataclass(frozen=True, slots=True)
class InventoryProjection:
    requested_material: str
    canonical_material: str
    availability: InventoryAvailability
    stock_readiness: StockReadiness
    exact_stock_ref: str | None
    source_kind: str
    source_row: int | None
    status: str
    family: str | None = None
    purchase_class: str | None = None
    reason: str | None = None


_OPEN_MARKERS = (
    "OPEN",
    "UNSTATED",
    "UNRESOLVED",
    "UNCONFIRMED",
    "HETEROGENEOUS",
    "VERIFY",
    "DIFFERENT STOCK",
)


def _classify_current(
    record: CurrentInventoryRecord,
) -> tuple[InventoryAvailability, StockReadiness, str | None]:
    status = record.status.upper()
    if status.startswith("BANNED") or status.startswith("DO NOT USE"):
        return (
            InventoryAvailability.FORBIDDEN,
            StockReadiness.NOT_BUILDABLE,
            None,
        )
    if status.startswith("OUT OF STOCK"):
        return (
            InventoryAvailability.OUT_OF_STOCK,
            StockReadiness.NOT_BUILDABLE,
            None,
        )
    if status.startswith("PLANNED ACQUISITION"):
        return (
            InventoryAvailability.PLANNED_ACQUISITION,
            StockReadiness.PROCUREMENT_PENDING,
            None,
        )
    if status.startswith("GAP"):
        return InventoryAvailability.MISSING, StockReadiness.NOT_BUILDABLE, None
    if status.startswith("CONSTRUCTIBLE"):
        return (
            InventoryAvailability.PREPARABLE_NOT_MIXED,
            StockReadiness.PREPARATION_REQUIRED,
            None,
        )
    if status == "VERIFY":
        return (
            InventoryAvailability.VERIFY_FIRST,
            StockReadiness.STOCK_DETAIL_OPEN,
            None,
        )
    if status.startswith("HAVE"):
        if "PREPARE" in status:
            return (
                InventoryAvailability.OWNED,
                StockReadiness.PREPARATION_REQUIRED,
                None,
            )
        if record.actual_stocks is None or any(
            marker in status for marker in _OPEN_MARKERS
        ):
            return (
                InventoryAvailability.OWNED,
                StockReadiness.STOCK_DETAIL_OPEN,
                None,
            )
        return (
            InventoryAvailability.OWNED,
            StockReadiness.EXACT_STOCK_IDENTIFIED,
            record.actual_stocks,
        )
    return (
        InventoryAvailability.VERIFY_FIRST,
        StockReadiness.STOCK_DETAIL_OPEN,
        None,
    )


_SAFE_ALIAS_RELATIONSHIPS = frozenset(
    {
        "DUPLICATE",
        "CANONICAL IDENTITY",
        "DEFINED DILUTION",
        "CANONICAL BOTANICAL MAPPING",
        "ACCEPTABLE GENERIC MAPPING",
        "SPELLING NORMALIZATION",
        "LEGACY SPELLING NORMALIZATION",
    }
)
_FORBIDDEN_EQUIVALENCE_RELATIONSHIPS = frozenset(
    {
        "NOT EQUIVALENT",
        "UNVERIFIED",
        "BANNED",
        "FUNCTIONAL ACCORD ONLY",
        "SPECIES-SPECIFIC SUBSTITUTE",
        "LABEL-NAME HOLD",
        "NOT MERGED",
        "PRODUCT BASIS",
    }
)


class ComplexityInventoryCatalog:
    """Validated lookup over every current-master and advisory material row."""

    def __init__(self, value: Mapping[str, Any]) -> None:
        if value.get("schema_version") != "complexity_inventory_catalog_v1":
            raise ValueError("unsupported complexity inventory catalog")
        authority = value.get("authority")
        if not isinstance(authority, Mapping):
            raise TypeError("authority must be a mapping")
        self.workbook_sha256 = _text(
            authority.get("workbook_sha256"), "workbook_sha256"
        )
        if self.workbook_sha256 != _EXPECTED_WORKBOOK_SHA256:
            raise ValueError("inventory workbook hash is not the frozen V5 authority")
        count = authority.get("current_record_count")
        if not isinstance(count, int) or count < 1:
            raise ValueError("current_record_count must be positive")
        self.current_record_count = count

        raw_manifest = value.get("sheet_manifest")
        if not isinstance(raw_manifest, list):
            raise TypeError("sheet_manifest must be a list")
        if any(not isinstance(item, Mapping) for item in raw_manifest):
            raise TypeError("sheet manifest entries must be mappings")
        self.sheet_manifest = tuple(
            MappingProxyType(dict(item)) for item in raw_manifest
        )

        raw_records = value.get("current_records")
        if not isinstance(raw_records, list):
            raise TypeError("current_records must be a list")
        records = tuple(CurrentInventoryRecord.from_mapping(item) for item in raw_records)
        if len(records) != count:
            raise ValueError("current record count does not match authority metadata")
        by_key: dict[str, CurrentInventoryRecord] = {}
        for record in records:
            key = _key(record.canonical_material)
            if key in by_key:
                raise ValueError(f"duplicate current material: {record.canonical_material}")
            by_key[key] = record
        self.current_records = records
        self._current_by_key = MappingProxyType(by_key)
        carrier_aliases: dict[str, str] = {}
        carrier_collisions: set[str] = set()
        for canonical_key in by_key:
            alias = _carrier_omission_key(canonical_key)
            if alias == canonical_key:
                continue
            if alias in carrier_aliases and carrier_aliases[alias] != canonical_key:
                carrier_collisions.add(alias)
            else:
                carrier_aliases[alias] = canonical_key
        for alias in carrier_collisions:
            carrier_aliases.pop(alias, None)
        self._carrier_aliases = MappingProxyType(carrier_aliases)

        update = value.get("august_update_summary")
        if not isinstance(update, Mapping):
            raise TypeError("august_update_summary must be a mapping")
        added = update.get("added_materials")
        if not isinstance(added, list) or any(not isinstance(item, str) for item in added):
            raise TypeError("added_materials must be a list of text values")
        if update.get("added_count") != len(added):
            raise ValueError("August added-material count does not match its list")
        self.august_added_materials = tuple(_text(item, "added material") for item in added)

        raw_advisory = value.get("advisory_candidates")
        if not isinstance(raw_advisory, list):
            raise TypeError("advisory_candidates must be a list")
        if any(not isinstance(item, Mapping) for item in raw_advisory):
            raise TypeError("advisory candidate must be a mapping")
        self.advisory_candidates = tuple(
            MappingProxyType(dict(item)) for item in raw_advisory
        )
        advisory: dict[str, Mapping[str, Any]] = {}
        for item in self.advisory_candidates:
            material = _text(item.get("material"), "advisory material")
            advisory[_key(material)] = MappingProxyType(dict(item))
        self._advisory_by_key = MappingProxyType(advisory)

        raw_planned = value.get("planned_and_prepare")
        if not isinstance(raw_planned, list):
            raise TypeError("planned_and_prepare must be a list")
        if any(not isinstance(item, Mapping) for item in raw_planned):
            raise TypeError("planned/preparation row must be a mapping")
        self.planned_and_prepare = tuple(
            MappingProxyType(dict(item)) for item in raw_planned
        )
        planned: dict[str, Mapping[str, Any]] = {}
        for item in self.planned_and_prepare:
            material = _text(item.get("material_or_stock"), "planned material")
            planned[_key(material)] = MappingProxyType(dict(item))
        self._planned_by_key = MappingProxyType(planned)

        raw_aliases = value.get("aliases_and_non_equivalents")
        if not isinstance(raw_aliases, list):
            raise TypeError("aliases_and_non_equivalents must be a list")
        if any(not isinstance(item, Mapping) for item in raw_aliases):
            raise TypeError("alias row must be a mapping")
        self.aliases_and_non_equivalents = tuple(
            MappingProxyType(dict(item)) for item in raw_aliases
        )
        safe_aliases: dict[str, str] = {}
        forbidden_pairs: set[frozenset[str]] = set()
        for item in self.aliases_and_non_equivalents:
            left = _key(item.get("Material / name"))
            right = _key(item.get("Compared with"))
            relationship = _text(item.get("Relationship"), "relationship").upper()
            if relationship in _SAFE_ALIAS_RELATIONSHIPS and right in by_key:
                safe_aliases[left] = right
            elif relationship in _SAFE_ALIAS_RELATIONSHIPS and left in by_key:
                safe_aliases[right] = left
            if relationship in _FORBIDDEN_EQUIVALENCE_RELATIONSHIPS:
                forbidden_pairs.add(frozenset((left, right)))
        self._safe_aliases = MappingProxyType(safe_aliases)
        self._forbidden_pairs = frozenset(forbidden_pairs)

    def is_forbidden_equivalence(self, material_a: str, material_b: str) -> bool:
        return frozenset((_key(material_a), _key(material_b))) in self._forbidden_pairs

    def project(self, material: str) -> InventoryProjection:
        requested = _text(material, "material")
        requested_key = _key(requested)
        canonical_key = self._safe_aliases.get(
            requested_key,
            self._carrier_aliases.get(requested_key, requested_key),
        )
        current = self._current_by_key.get(canonical_key)
        if current is not None:
            availability, readiness, stock = _classify_current(current)
            return InventoryProjection(
                requested_material=requested,
                canonical_material=current.canonical_material,
                availability=availability,
                stock_readiness=readiness,
                exact_stock_ref=stock,
                source_kind="CURRENT_INVENTORY_MASTER",
                source_row=current.source_row,
                status=current.status,
                family=current.family,
                reason=current.formula_use_policy,
            )

        planned = self._planned_by_key.get(requested_key)
        if planned is not None:
            state = _text(planned.get("current_state"), "planned state").upper()
            availability = (
                InventoryAvailability.PLANNED_ACQUISITION
                if "PLANNED ACQUISITION" in state
                else InventoryAvailability.PREPARABLE_NOT_MIXED
                if "OWNED" in state or "STOCK PREPARATION" in _text(
                    planned.get("action_type"), "action_type"
                ).upper()
                else InventoryAvailability.MISSING
            )
            readiness = (
                StockReadiness.PROCUREMENT_PENDING
                if availability is InventoryAvailability.PLANNED_ACQUISITION
                else StockReadiness.PREPARATION_REQUIRED
                if availability is InventoryAvailability.PREPARABLE_NOT_MIXED
                else StockReadiness.NOT_BUILDABLE
            )
            return InventoryProjection(
                requested_material=requested,
                canonical_material=_text(
                    planned.get("material_or_stock"), "planned material"
                ),
                availability=availability,
                stock_readiness=readiness,
                exact_stock_ref=None,
                source_kind="PLANNED_AND_PREPARE",
                source_row=planned.get("_source_row"),
                status=_text(planned.get("current_state"), "planned state"),
                reason=_optional_text(planned.get("recommended_action")),
            )

        advisory = self._advisory_by_key.get(requested_key)
        if advisory is not None:
            return InventoryProjection(
                requested_material=requested,
                canonical_material=_text(advisory.get("material"), "advisory material"),
                availability=InventoryAvailability.MISSING,
                stock_readiness=StockReadiness.NOT_BUILDABLE,
                exact_stock_ref=None,
                source_kind="ADVISORY_CANDIDATE",
                source_row=advisory.get("_source_row"),
                status=_text(advisory.get("current_state"), "advisory state"),
                purchase_class=_optional_text(advisory.get("purchase_class")),
                reason=_optional_text(advisory.get("rationale_and_holds")),
            )

        return InventoryProjection(
            requested_material=requested,
            canonical_material=requested,
            availability=InventoryAvailability.UNLISTED,
            stock_readiness=StockReadiness.NOT_BUILDABLE,
            exact_stock_ref=None,
            source_kind="UNLISTED",
            source_row=None,
            status="UNLISTED",
            reason="No exact current-master, planned/preparation, or advisory row.",
        )


def load_complexity_inventory_catalog(
    path: str | Path | None = None,
) -> ComplexityInventoryCatalog:
    catalog_path = Path(path) if path is not None else _CATALOG_PATH
    value = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise TypeError("complexity inventory catalog root must be a mapping")
    return ComplexityInventoryCatalog(value)


__all__ = [
    "ComplexityInventoryCatalog",
    "CurrentInventoryRecord",
    "InventoryAvailability",
    "InventoryProjection",
    "StockReadiness",
    "load_complexity_inventory_catalog",
]
