"""Structured inventory and stock model.

Refactors the existing inventory_parser.py output into a richer model
with identity resolution, substitution mapping, and ledger management.

Usage:
    from engine.inventory.stock_model import (
        InventoryLedger,
        InventoryStatus,
        StockItem,
        SubstitutionMapping,
        create_inventory_from_parser,
        map_target_to_inventory,
    )

    ledger = create_inventory_from_parser(parse_inventory())
    mappings = map_target_to_inventory(["Iso E Super", "Hedione"], ledger)
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from engine.domain_errors import LegacyWriteProhibitedError, ReconstructionInputError
from engine.identity.resolver import (
    KNOWN_NON_EQUIVALENT,
    IdentityGrade,
    MaterialIdentity,
    resolve_identity,
)
from engine.name_utils import normalize_name

# ── Inventory status constants ──────────────────────────────────────────────

EXACT_AVAILABLE = "EXACT_AVAILABLE"
PROBABLE_GRADE_MATCH = "PROBABLE_GRADE_MATCH"
FUNCTIONAL_SUBSTITUTE = "FUNCTIONAL_SUBSTITUTE"
PARTIAL_ACCORD_RECONSTRUCTION = "PARTIAL_ACCORD_RECONSTRUCTION"
UNAVAILABLE = "UNAVAILABLE"
UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"
EXACT_IDENTITY_NOT_IN_STOCK = "EXACT_IDENTITY_NOT_IN_STOCK"
TECHNICAL_NOT_REQUIRED = "TECHNICAL_NOT_REQUIRED"


class IdentityResolutionStatus(StrEnum):
    EXACT = "EXACT"
    ALIAS = "ALIAS"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


class InventoryAvailabilityStatus(StrEnum):
    EXACT_LOT_AVAILABLE = "EXACT_LOT_AVAILABLE"
    EXACT_IDENTITY_NOT_IN_STOCK = "EXACT_IDENTITY_NOT_IN_STOCK"
    GRADE_MISMATCH = "GRADE_MISMATCH"
    FUNCTIONAL_SUBSTITUTE_AVAILABLE = "FUNCTIONAL_SUBSTITUTE_AVAILABLE"
    NO_SUITABLE_STOCK = "NO_SUITABLE_STOCK"
    NOT_TECHNICALLY_REQUIRED = "NOT_TECHNICALLY_REQUIRED"


_KNOWN_IDENTITY_CANONICALS: frozenset[str] = frozenset(
    {
        "ambroxan",
        "ambrofix",
        "iso e super",
        "hedione",
        "hedione hc",
        "galaxolide",
        "habanolide",
        "ethylene brassylate",
        "alpha-isomethyl ionone",
        "methyl ionone",
        *KNOWN_NON_EQUIVALENT,
    }
)


# ── Dataclasses ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class StockItem:
    """A single physical stock entry in the perfumer's inventory.

    Each item represents one bottle or container with its own identity,
    concentration, and condition metadata.
    """

    material_id: str
    label: str
    grade: str = IdentityGrade.TRADE_GRADE
    supplier: str | None = None
    lot: str | None = None
    concentration: float = 1.0
    concentration_basis: str = "unspecified"
    carrier: str = ""
    density_g_ml: float | None = None
    amount_remaining_ml: float = 0.0
    amount_unit: str = "ml"
    date_opened: str | None = None
    date_acquired: str | None = None
    stability_status: str = "unknown"
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StockItem:
        return cls(
            material_id=str(data["material_id"]),
            label=str(data["label"]),
            grade=str(data.get("grade", IdentityGrade.TRADE_GRADE)),
            supplier=str(data["supplier"]) if data.get("supplier") else None,
            lot=str(data["lot"]) if data.get("lot") else None,
            concentration=float(data.get("concentration", 1.0)),
            concentration_basis=str(data.get("concentration_basis", "unspecified")),
            carrier=str(data.get("carrier") or ""),
            density_g_ml=float(data["density_g_ml"])
            if data.get("density_g_ml") is not None
            else None,
            amount_remaining_ml=float(data.get("amount_remaining_ml", 0.0)),
            amount_unit=str(data.get("amount_unit", "ml")),
            date_opened=str(data["date_opened"]) if data.get("date_opened") else None,
            date_acquired=str(data["date_acquired"]) if data.get("date_acquired") else None,
            stability_status=str(data.get("stability_status", "unknown")),
            notes=str(data.get("notes") or ""),
        )


@dataclass(frozen=True, slots=True)
class InventoryTarget:
    """Target identity plus optional stock-scope requirements."""

    name: str
    grade: str = IdentityGrade.TRADE_GRADE
    supplier: str | None = None
    lot: str | None = None
    functional_substitutes: tuple[str, ...] = ()
    technically_required: bool = True


@dataclass(frozen=True, slots=True)
class SubstitutionMapping:
    """Records how a target formula material maps to an actual inventory item.

    The *status* field captures the quality of the match, from exact
    availability through functional substitution to complete unavailability.
    """

    target_material: str
    build_material: str
    identity_status: IdentityResolutionStatus = IdentityResolutionStatus.UNRESOLVED
    inventory_status: InventoryAvailabilityStatus = (
        InventoryAvailabilityStatus.NO_SUITABLE_STOCK
    )
    stock_id: str = ""
    preserved_qualities: tuple[str, ...] = ()
    lost_qualities: tuple[str, ...] = ()
    confidence: float = 1.0

    @property
    def status(self) -> str:
        """Derived compatibility view for older callers."""

        if self.identity_status in {
            IdentityResolutionStatus.AMBIGUOUS,
            IdentityResolutionStatus.UNRESOLVED,
        }:
            return UNKNOWN_IDENTITY
        return {
            InventoryAvailabilityStatus.EXACT_LOT_AVAILABLE: EXACT_AVAILABLE,
            InventoryAvailabilityStatus.EXACT_IDENTITY_NOT_IN_STOCK: (
                EXACT_IDENTITY_NOT_IN_STOCK
            ),
            InventoryAvailabilityStatus.GRADE_MISMATCH: PROBABLE_GRADE_MATCH,
            InventoryAvailabilityStatus.FUNCTIONAL_SUBSTITUTE_AVAILABLE: (
                FUNCTIONAL_SUBSTITUTE
            ),
            InventoryAvailabilityStatus.NO_SUITABLE_STOCK: UNAVAILABLE,
            InventoryAvailabilityStatus.NOT_TECHNICALLY_REQUIRED: (
                TECHNICAL_NOT_REQUIRED
            ),
        }[self.inventory_status]

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_material": self.target_material,
            "build_material": self.build_material,
            "identity_status": self.identity_status.value,
            "inventory_status": self.inventory_status.value,
            "status": self.status,
            "stock_id": self.stock_id,
            "preserved_qualities": self.preserved_qualities,
            "lost_qualities": self.lost_qualities,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubstitutionMapping:
        return cls(
            target_material=str(data["target_material"]),
            build_material=str(data["build_material"]),
            identity_status=IdentityResolutionStatus(
                data.get("identity_status", IdentityResolutionStatus.UNRESOLVED)
            ),
            inventory_status=InventoryAvailabilityStatus(
                data.get(
                    "inventory_status",
                    InventoryAvailabilityStatus.NO_SUITABLE_STOCK,
                )
            ),
            stock_id=str(data.get("stock_id") or ""),
            preserved_qualities=tuple(str(x) for x in data.get("preserved_qualities") or ()),
            lost_qualities=tuple(str(x) for x in data.get("lost_qualities") or ()),
            confidence=float(data.get("confidence", 1.0)),
        )


@dataclass(frozen=True, slots=True)
class ConsumptionRecord:
    """Records a single stock depletion event.

    Tracks the before/after state of a stock item when material is
    consumed during formulation or bottle filling.  Supports reversal
    via *reversal_ref* for audit-trail integrity.
    """

    stock_id: str
    lot: str
    amount: float
    unit: str  # "ml", "g", "uL"
    concentration_basis: str
    quantity_before: float
    quantity_after: float
    build_ref: str = ""
    bottle_event_ref: str = ""
    timestamp: str = ""
    reversal_ref: str | None = None


# ── Ledger ──────────────────────────────────────────────────────────────────


class InventoryLedger:
    """A mutable collection of StockItem records.

    Provides lookup by material name or ID, lot number, and availability
    filtering.  This is the primary runtime interface for querying what
    is physically on the shelf.
    """

    def __init__(self, stock_items: list[StockItem]) -> None:
        self._items: tuple[StockItem, ...] = tuple(stock_items)

    def add_stock(self, item: StockItem) -> None:
        """Reject writes to the deprecated in-memory duplicate store."""
        del item
        raise LegacyWriteProhibitedError(
            "InventoryLedger is a read-only projection; create stock through LabService"
        )

    def remove_stock(self, material_id: str) -> StockItem | None:
        """Reject writes to the deprecated in-memory duplicate store."""
        del material_id
        raise LegacyWriteProhibitedError(
            "InventoryLedger is a read-only projection; change stock through LabService"
        )

    def find_by_material(self, name_or_id: str) -> list[StockItem]:
        """Return all stock items whose label or material_id matches.

        Matching is case-insensitive and uses ``normalize_name`` for label
        comparison.  An exact material_id match is checked first.
        """
        results: list[StockItem] = []
        key = normalize_name(name_or_id)
        for item in self._items:
            if item.material_id == name_or_id:
                results.append(item)
            elif normalize_name(item.label) == key:
                results.append(item)
        return results

    def find_by_lot(self, lot: str) -> StockItem | None:
        """Return the first stock item matching the given lot number."""
        for item in self._items:
            if item.lot == lot:
                return item
        return None

    def available_materials(self) -> list[str]:
        """Return the labels of all in-stock materials with remaining volume."""
        seen: set[str] = set()
        result: list[str] = []
        for item in self._items:
            if item.amount_remaining_ml > 0 and item.label not in seen:
                seen.add(item.label)
                result.append(item.label)
        return result

    def consume(
        self,
        stock_id: str,
        amount: float,
        unit: str = "ml",
        lot: str = "",
        concentration_basis: str = "w/w",
        build_ref: str = "",
        bottle_event_ref: str = "",
        timestamp: str | None = None,
    ) -> ConsumptionRecord:
        raise LegacyWriteProhibitedError(
            "InventoryLedger cannot consume stock; commit a movement through LabService"
        )
        """Deplete *amount* from the stock item identified by *stock_id*.

        Parameters
        ----------
        stock_id:
            The ``material_id`` of the stock item to consume from.
        amount:
            Quantity to consume in *unit*.
        unit:
            Unit of *amount* — ``"ml"``, ``"uL"``, or ``"g"``.
        lot:
            Lot number of the consumed stock (for audit trail).
        concentration_basis:
            Basis of the concentration (e.g. ``"w/w"``, ``"v/v"``).
        build_ref:
            Optional reference to the build formula that consumed this stock.
        bottle_event_ref:
            Optional reference to the bottle event that triggered consumption.
        timestamp:
            ISO-format timestamp; defaults to ``datetime.utcnow().isoformat()``.

        Returns
        -------
        ConsumptionRecord
            Immutable record of the depletion event.

        Raises
        ------
        ValueError
            When *stock_id* is not found or remaining stock is insufficient.
        """
        # ── Find stock ──────────────────────────────────────────────────
        matches = [it for it in self._items if it.material_id == stock_id]
        if not matches:
            raise ValueError(f"Stock item '{stock_id}' not found in ledger")
        stock = matches[0]

        # ── Unit conversion ─────────────────────────────────────────────
        amount_ml = amount
        if unit == "uL":
            amount_ml = amount / 1000.0
        elif unit == "g":
            if stock.density_g_ml is not None and stock.density_g_ml > 0:
                amount_ml = amount / stock.density_g_ml
            else:
                # Assume density ≈ 1.0 g/ml when unknown
                amount_ml = amount

        # ── Sufficiency check ───────────────────────────────────────────
        if stock.amount_remaining_ml < amount_ml:
            raise ValueError(
                f"Insufficient stock for '{stock_id}': "
                f"requested {amount_ml:.3f} ml, "
                f"available {stock.amount_remaining_ml:.3f} ml"
            )

        # ── Record & update ─────────────────────────────────────────────
        before = stock.amount_remaining_ml
        after = before - amount_ml

        # Update in-place — StockItem is frozen, so we replace the entry
        idx = self._items.index(stock)
        self._items[idx] = StockItem(
            material_id=stock.material_id,
            label=stock.label,
            grade=stock.grade,
            supplier=stock.supplier,
            lot=stock.lot,
            concentration=stock.concentration,
            concentration_basis=stock.concentration_basis,
            carrier=stock.carrier,
            density_g_ml=stock.density_g_ml,
            amount_remaining_ml=after,
            amount_unit=stock.amount_unit,
            date_opened=stock.date_opened,
            date_acquired=stock.date_acquired,
            stability_status=stock.stability_status,
            notes=stock.notes,
        )

        if timestamp is None:
            timestamp = datetime.now().isoformat()

        return ConsumptionRecord(
            stock_id=stock_id,
            lot=lot or (stock.lot or ""),
            amount=amount,
            unit=unit,
            concentration_basis=concentration_basis,
            quantity_before=before,
            quantity_after=after,
            build_ref=build_ref,
            bottle_event_ref=bottle_event_ref,
            timestamp=timestamp,
        )

    def select_best_lot(
        self,
        material_name: str,
        target_amount: float = 0.0,
        target_unit: str = "ml",
    ) -> tuple[StockItem | None, str]:
        """Select the best available stock item for *material_name*.

        Selection priority:
        1. Non-depleted items (``amount_remaining_ml > 0``).
        2. Highest concentration.
        3. Most remaining volume.
        4. Most recent ``date_opened``.

        Parameters
        ----------
        material_name:
            Material name or ID to look up.
        target_amount:
            Amount needed (not yet used for filtering — reserved for future).
        target_unit:
            Unit of *target_amount* (reserved for future).

        Returns
        -------
        tuple[StockItem | None, str]
            ``(best_item, status)`` where *status* is one of
            ``EXACT_AVAILABLE``, ``FUNCTIONAL_SUBSTITUTE``, or
            ``UNAVAILABLE``.
        """
        matches = self.find_by_material(material_name)
        if not matches:
            return (None, UNAVAILABLE)

        # Priority 1: non-depleted
        available = [m for m in matches if m.amount_remaining_ml > 0]
        if not available:
            available = matches  # fall back to depleted if nothing else

        # Priority 2: highest concentration
        # Priority 3: most remaining volume
        # Priority 4: most recent date_opened (None sorts last)
        def sort_key(item: StockItem) -> tuple:
            opened = item.date_opened or ""
            return (item.concentration, item.amount_remaining_ml, opened)

        best = max(available, key=sort_key)

        # Determine status
        if best.label == material_name or normalize_name(best.label) == normalize_name(
            material_name
        ):
            status = EXACT_AVAILABLE
        else:
            status = FUNCTIONAL_SUBSTITUTE

        return (best, status)

    def as_list(self) -> list[StockItem]:
        """Return a copy of the internal stock list."""
        return list(self._items)


# ── Module-level functions ──────────────────────────────────────────────────


def _identity_appears_valid(ident: MaterialIdentity) -> bool:
    """Heuristic: does the identity look like a real material name?

    Returns ``True`` when the name is a plausible material identifier
    (alphabetic characters, spaces, hyphens, apostrophes) and is longer
    than two characters.  Short gibberish strings, hash-like tokens, or
    names containing only the word "unknown" are rejected.
    """
    import re

    name = ident.name.strip()
    if not name or len(name) <= 2:
        return False
    if re.match(r"^[A-Za-z0-9\s'\-]+$", name) is None:
        return False
    if name.lower() in ("unknown", "unresolved", "none", "null", "n/a"):
        return False
    return True


def _raw_name_key(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).lower()


def _classify_identity_status(name: str) -> IdentityResolutionStatus:
    raw_key = _raw_name_key(name)
    if not raw_key or raw_key.startswith("unknown_"):
        return IdentityResolutionStatus.UNRESOLVED
    if re.search(r"(?:/|\bor\b|\band/or\b)", raw_key):
        return IdentityResolutionStatus.AMBIGUOUS
    canonical = normalize_name(name)
    if raw_key != canonical and canonical in _KNOWN_IDENTITY_CANONICALS:
        return IdentityResolutionStatus.ALIAS
    if canonical in _KNOWN_IDENTITY_CANONICALS:
        return IdentityResolutionStatus.EXACT
    return IdentityResolutionStatus.UNRESOLVED


def _pick_best_match(matches: list[StockItem]) -> StockItem:
    """Return the stock item with the highest concentration.

    When concentrations are equal, the item with the most remaining
    volume is preferred.
    """
    return max(matches, key=lambda s: (s.concentration, s.amount_remaining_ml))


def assert_unique_stock_assignments(
    assignments: list[tuple[str, str]],
) -> None:
    """Reject one physical stock assigned to distinct target identities."""

    stock_to_target: dict[str, str] = {}
    for target_identity, stock_id in assignments:
        if not stock_id:
            continue
        previous = stock_to_target.get(stock_id)
        if previous is not None and previous != target_identity:
            raise ReconstructionInputError(
                "one stock cannot satisfy multiple distinct target identities: "
                f"{stock_id!r} -> {previous!r}, {target_identity!r}"
            )
        stock_to_target[stock_id] = target_identity


def map_target_to_inventory(
    target_materials: list[str | InventoryTarget],
    inventory: InventoryLedger,
) -> list[SubstitutionMapping]:
    """Map each target formula material to the best available inventory match.

    For every material in *target_materials* the function:

    1. Looks up matching stock items in the ledger (exact label match).
    2. Falls back to identity resolution for a canonical-name lookup.
    3. Distinguishes between a known material not in stock
       (``EXACT_IDENTITY_NOT_IN_STOCK``) and a truly unresolvable name
       (``UNKNOWN_IDENTITY``).

    Parameters
    ----------
    target_materials:
        Material names as they appear in the target formula.
    inventory:
        The current inventory ledger.

    Returns
    -------
    list[SubstitutionMapping]:
        One mapping per target material, in the same order.
    """
    if not target_materials:
        raise ReconstructionInputError("inventory target cannot be empty")

    mappings: list[SubstitutionMapping] = []
    assignments: list[tuple[str, str]] = []

    for target_value in target_materials:
        target = (
            target_value
            if isinstance(target_value, InventoryTarget)
            else InventoryTarget(name=str(target_value))
        )
        identity_status = _classify_identity_status(target.name)

        if not target.technically_required:
            mappings.append(
                SubstitutionMapping(
                    target_material=target.name,
                    build_material="",
                    identity_status=identity_status,
                    inventory_status=(
                        InventoryAvailabilityStatus.NOT_TECHNICALLY_REQUIRED
                    ),
                    confidence=1.0,
                )
            )
            continue

        if identity_status in {
            IdentityResolutionStatus.AMBIGUOUS,
            IdentityResolutionStatus.UNRESOLVED,
        }:
            mappings.append(
                SubstitutionMapping(
                    target_material=target.name,
                    build_material="",
                    identity_status=identity_status,
                    inventory_status=InventoryAvailabilityStatus.NO_SUITABLE_STOCK,
                    confidence=0.0,
                    lost_qualities=(
                        f"Material {target.name} is not resolved by declared identity evidence",
                    ),
                )
            )
            continue

        matches = inventory.find_by_material(target.name)
        if matches:
            best = _pick_best_match(matches)
            grade_mismatch = (
                best.grade != target.grade
                or (target.supplier is not None and best.supplier != target.supplier)
            )
            lot_mismatch = target.lot is not None and best.lot != target.lot
            if grade_mismatch:
                inventory_status = InventoryAvailabilityStatus.GRADE_MISMATCH
                confidence = 0.0
            elif lot_mismatch:
                inventory_status = InventoryAvailabilityStatus.NO_SUITABLE_STOCK
                confidence = 0.0
            else:
                inventory_status = InventoryAvailabilityStatus.EXACT_LOT_AVAILABLE
                confidence = 1.0
            mapping = SubstitutionMapping(
                target_material=target.name,
                build_material=best.label,
                identity_status=identity_status,
                inventory_status=inventory_status,
                stock_id=best.material_id,
                confidence=confidence,
            )
            mappings.append(mapping)
            if inventory_status is InventoryAvailabilityStatus.EXACT_LOT_AVAILABLE:
                assignments.append((normalize_name(target.name), best.material_id))
            continue

        substitute_matches: list[StockItem] = []
        for substitute_name in target.functional_substitutes:
            substitute_matches.extend(inventory.find_by_material(substitute_name))
        if substitute_matches:
            best = _pick_best_match(substitute_matches)
            mappings.append(
                SubstitutionMapping(
                    target_material=target.name,
                    build_material=best.label,
                    identity_status=identity_status,
                    inventory_status=(
                        InventoryAvailabilityStatus.FUNCTIONAL_SUBSTITUTE_AVAILABLE
                    ),
                    stock_id=best.material_id,
                    confidence=0.5,
                    lost_qualities=("Functional substitute is not exact identity",),
                )
            )
            assignments.append((normalize_name(target.name), best.material_id))
            continue

        mappings.append(
            SubstitutionMapping(
                target_material=target.name,
                build_material="",
                identity_status=identity_status,
                inventory_status=(
                    InventoryAvailabilityStatus.EXACT_IDENTITY_NOT_IN_STOCK
                ),
                confidence=0.0,
                lost_qualities=(
                    f"Material {normalize_name(target.name)} is known but not in inventory",
                ),
            )
        )

    assert_unique_stock_assignments(assignments)
    return mappings


def create_inventory_from_parser(
    parsed_materials: list[dict[str, Any]],
) -> InventoryLedger:
    """Adapt the output of ``inventory_parser.parse_inventory()`` into a ledger.

    Each dict in *parsed_materials* is expected to contain at least the keys
    ``material_name``, ``concentration``, and ``concentration_basis``, matching
    the fields produced by the existing parser.

    Parameters
    ----------
    parsed_materials:
        List of material dicts from ``inventory_parser.parse_inventory()``.

    Returns
    -------
    InventoryLedger
        Populated with one ``StockItem`` per parsed entry.
    """
    items: list[StockItem] = []

    for entry in parsed_materials:
        name = str(entry.get("material_name", entry.get("name", "")))
        ident = resolve_identity(name)

        items.append(
            StockItem(
                material_id=ident.identity_id,
                label=name,
                grade=str(entry.get("grade", IdentityGrade.TRADE_GRADE)),
                concentration=float(entry.get("concentration", 1.0)),
                concentration_basis=str(entry.get("concentration_basis", "unspecified")),
                carrier=str(entry.get("carrier", "")),
                notes=str(entry.get("notes", "")),
            )
        )

    return InventoryLedger(items)


__all__ = [
    "ConsumptionRecord",
    "EXACT_AVAILABLE",
    "EXACT_IDENTITY_NOT_IN_STOCK",
    "FUNCTIONAL_SUBSTITUTE",
    "IdentityResolutionStatus",
    "InventoryAvailabilityStatus",
    "InventoryLedger",
    "InventoryTarget",
    "PARTIAL_ACCORD_RECONSTRUCTION",
    "PROBABLE_GRADE_MATCH",
    "StockItem",
    "SubstitutionMapping",
    "TECHNICAL_NOT_REQUIRED",
    "UNAVAILABLE",
    "UNKNOWN_IDENTITY",
    "assert_unique_stock_assignments",
    "create_inventory_from_parser",
    "map_target_to_inventory",
]
