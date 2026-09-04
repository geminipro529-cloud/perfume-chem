"""Immutable pin for the current physical inventory authority.

This module intentionally contains no fallback to historical inventory versions.  Build
plans that can drive physical execution must bind to the exact V5 workbook bytes below.
A future inventory revision must change this pin explicitly and re-run the stock-lineage,
build-plan, reservation, execution, and workspace-import regression suites.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InventoryAuthorityPin:
    version: str
    file_name: str
    sha256: str
    authority_scope: str

    @property
    def snapshot_ref(self) -> str:
        return f"inventory:{self.version}:sha256:{self.sha256}"


CURRENT_INVENTORY_AUTHORITY = InventoryAuthorityPin(
    version="v5",
    file_name="Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx",
    sha256="e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331",
    authority_scope="CURRENT_STOCK_AND_PURCHASE_PLANNING_AUTHORITY",
)


def is_current_inventory_snapshot_ref(value: str) -> bool:
    """Return True only for the exact current V5 authority reference."""

    return str(value).strip() == CURRENT_INVENTORY_AUTHORITY.snapshot_ref
