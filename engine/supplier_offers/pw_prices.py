"""PerfumersWorld list prices from the material spine, plus Buy-page arithmetic.

Pure and offline: prices come from the ``supplier:`` block of
``data/materials/*.yaml`` (loaded through ``engine.data_spine.loader``). All
money and strength values are ``Decimal``; nothing here rounds.

Strength is the active fraction of the product as sold: ``1`` for ``neat``,
``N/100`` for ``N% in <solvent>``, otherwise ``None``. A SKU starting with
``5`` that is marked ``neat`` gets ``None`` too: PerfumersWorld uses that
prefix for pre-diluted products (for example ``5VD10871`` Methyl Laitone 10%
DPG), so a neat label there cannot be trusted. With ``None`` strength only the
pack price is shown; per-active-gram and per-bottle costs are withheld.

Each ``supplier.other.pw_alternate_forms`` entry (another SKU of the same
material, usually a dilution) is indexed as its own price with ``parent_sku``
set to the record's main SKU and the parent's snapshot date.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Mapping

from engine.data_spine.loader import _data_fingerprint, _resolved_data_dir, load_materials
from engine.data_spine.material import Material

PW_LINE_FEE_USD = Decimal("0.90")
DEFAULT_PACK_G = Decimal("5")
BOTTLE_CONCENTRATE_G = Decimal("6")
SOURCE_MATERIALS_YAML = "materials_yaml"
PW_PRODUCT_URL = "https://www.perfumersworld.com/view.php?pro_id={sku}"

_DILUTED_PREFIX = "5"
_DILUTION_FORM = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*%\s+in\s+([A-Za-z]+)\s*$", re.IGNORECASE)

StockState = Literal["IN", "OUT", "UNKNOWN"]


@dataclass(frozen=True)
class PwPrice:
    sku: str
    material_name: str
    usd_per_g: Decimal
    form: str
    strength: Decimal | None
    solvent: str | None
    usd_per_active_g: Decimal | None
    observed_on: date
    source: str
    in_stock: StockState
    parent_sku: str | None = None  # main SKU of the record, for an alternate form

    def to_json(self) -> dict[str, Any]:
        return {
            "sku": self.sku,
            "material_name": self.material_name,
            "usd_per_g": str(self.usd_per_g),
            "form": self.form,
            "strength": None if self.strength is None else str(self.strength),
            "solvent": self.solvent,
            "usd_per_active_g": (
                None if self.usd_per_active_g is None else str(self.usd_per_active_g)
            ),
            "observed_on": self.observed_on.isoformat(),
            "source": self.source,
            "in_stock": self.in_stock,
            "parent_sku": self.parent_sku,
            "product_url": pw_product_url(self.sku),
        }


def pw_product_url(sku: str) -> str:
    return PW_PRODUCT_URL.format(sku=sku.strip())


def _parse_strength(sku: str, form: str) -> tuple[Decimal | None, str | None]:
    if form.strip().lower() == "neat":
        if sku.startswith(_DILUTED_PREFIX):
            return None, None
        return Decimal(1), None
    match = _DILUTION_FORM.match(form)
    if match is None:
        return None, None
    strength = Decimal(match.group(1)) / Decimal(100)
    if not Decimal(0) < strength <= Decimal(1):
        return None, None
    return strength, match.group(2).upper()


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _parse_price(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        price = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    if not price.is_finite() or price <= 0:
        return None
    return price


def _build_price(
    *,
    raw_sku: Any,
    raw_price: Any,
    form: Any,
    observed_on: date | None,
    material_name: str,
    parent_sku: str | None,
) -> PwPrice | None:
    sku = raw_sku.strip() if isinstance(raw_sku, str) else ""
    if not sku:
        return None
    usd_per_g = _parse_price(raw_price)
    if usd_per_g is None or observed_on is None or not isinstance(form, str) or not form.strip():
        return None
    strength, solvent = _parse_strength(sku, form)
    return PwPrice(
        sku=sku,
        material_name=material_name,
        usd_per_g=usd_per_g,
        form=form,
        strength=strength,
        solvent=solvent,
        usd_per_active_g=None if strength is None else usd_per_g / strength,
        observed_on=observed_on,
        source=SOURCE_MATERIALS_YAML,
        in_stock="UNKNOWN",
        parent_sku=parent_sku,
    )


def _prices_from_material(material: Material) -> list[PwPrice]:
    """The record's main PW price plus one per ``other.pw_alternate_forms`` entry.

    Alternates carry their own SKU, form and price, and inherit the parent's
    snapshot date and name; ``parent_sku`` points back at the main SKU.
    """
    supplier = material.supplier
    observed_on = _parse_date(supplier.perfumersworld_snapshot_date)
    parent_sku = (supplier.perfumersworld_sku or "").strip() or None
    prices: list[PwPrice] = []
    main = _build_price(
        raw_sku=supplier.perfumersworld_sku,
        raw_price=supplier.perfumersworld_price_usd_per_g,
        form=supplier.perfumersworld_form,
        observed_on=observed_on,
        material_name=material.canonical_name,
        parent_sku=None,
    )
    if main is not None:
        prices.append(main)
    alternates = (supplier.other or {}).get("pw_alternate_forms") or []
    for entry in alternates:
        if not isinstance(entry, dict):
            continue
        alternate = _build_price(
            raw_sku=entry.get("sku"),
            raw_price=entry.get("price_usd_per_g"),
            form=entry.get("form"),
            observed_on=observed_on,
            material_name=material.canonical_name,
            parent_sku=parent_sku,
        )
        if alternate is not None:
            prices.append(alternate)
    return prices


@lru_cache(maxsize=8)
def _index_cached(
    base_path: str, _fingerprint: tuple[tuple[str, int, int], ...]
) -> Mapping[str, PwPrice]:
    index: dict[str, PwPrice] = {}
    for material in load_materials(base_path):
        for price in _prices_from_material(material):
            current = index.get(price.sku)
            if current is None or price.observed_on > current.observed_on:
                index[price.sku] = price
    return MappingProxyType(index)


def pw_price_index(*, data_dir: Path | None = None) -> Mapping[str, PwPrice]:
    """Return a read-only ``sku -> PwPrice`` map of every usable YAML price."""
    base = _resolved_data_dir(data_dir)
    return _index_cached(str(base), _data_fingerprint(base))


def latest_pw_price(sku: str, *, data_dir: Path | None = None) -> PwPrice | None:
    """Return the newest stored PerfumersWorld price for ``sku``, or ``None``."""
    return pw_price_index(data_dir=data_dir).get(sku.strip())


def neat_thb_per_g(price: PwPrice, usd_thb_rate: Decimal) -> Decimal | None:
    """Baht per gram of active material: US$/g x rate / strength."""
    if price.strength is None:
        return None
    return price.usd_per_g * usd_thb_rate / price.strength


def cost_per_bottle_thb(
    price: PwPrice, usd_thb_rate: Decimal, neat_dose_fraction: Decimal
) -> Decimal | None:
    """Baht of this material in one 30 mL EDP (6 g concentrate) at the neat dose."""
    per_g = neat_thb_per_g(price, usd_thb_rate)
    if per_g is None:
        return None
    return per_g * neat_dose_fraction * BOTTLE_CONCENTRATE_G


def upfront_usd(price: PwPrice, grams: Decimal = DEFAULT_PACK_G) -> Decimal:
    """US$ to order ``grams`` of this SKU, including the per-line bottling fee."""
    return grams * price.usd_per_g + PW_LINE_FEE_USD
