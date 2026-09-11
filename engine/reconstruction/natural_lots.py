# QUARANTINED 2026-09-11 - no runtime references; do not develop.
# See docs/governance/engine_quarantine_manifest_20260911.md
"""Natural lot profile schema.

Stub — real lot data requires actual GC-MS runs. Provides the dataclass
structure for storing lot-specific constituent composition.
"""

from __future__ import annotations

from dataclasses import dataclass

_LOT_POOL: dict[str, NaturalLotProfile] = {}


@dataclass(frozen=True, slots=True)
class NaturalLotProfile:
    """Lot-specific constituent composition for a natural material.

    Each lot of a natural (EO, absolute, resinoid, etc.) has a unique
    chemical profile that differs from the generic material-level data.
    This schema captures the lot-specific breakdown for use in composite
    OAV calculations and substitution decisions.
    """

    lot_id: str
    material_name: str
    botanical_species: str = ""
    origin: str = ""
    extraction_method: str = ""
    supplier: str = ""
    acquisition_date: str = ""
    gcms_run_ref: str = ""
    constituents: tuple[tuple[str, float], ...] = ()  # (name, weight_percent)
    notes: str = ""


def get_lot_profile(material_name: str, lot_id: str) -> NaturalLotProfile | None:
    """Look up a lot profile by material name and lot ID.

    Stub — always returns None. FUTURE: query lot database.
    """
    key = f"{material_name}::{lot_id}"
    return _LOT_POOL.get(key)


def register_lot_profile(profile: NaturalLotProfile) -> None:
    """Register a lot profile for future lookup.

    Stub — stores profile in module-level dict. FUTURE: persist to database.
    """
    key = f"{profile.material_name}::{profile.lot_id}"
    _LOT_POOL[key] = profile
