"""Normalization, alias resolution, active-fraction/carrier accounting, and inventory crosswalk.

Decoupled and dependency-light: alias resolution is a caller-supplied hook
(default: exact-match plus whitespace/case normalization). No second truth path.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Mapping

from .schema import PRODUCT_BASIS

AliasResolver = Callable[[str], str | None]


def default_resolver(name: str) -> str | None:
    return re.sub(r"\s+", " ", name).strip().lower() or None


def resolve_alias(
    raw: str, alias_map: Mapping[str, str] | None = None
) -> tuple[str | None, list[str]]:
    """Return (canonical_name, ambiguity_notes). None canonical => AMBIGUOUS_ALIAS or UNRESOLVED."""
    norm = default_resolver(raw)
    if alias_map is None:
        return norm, []
    if norm is None:
        return None, ["unresolved alias (blank): " + str(raw)]
    canon = alias_map.get(norm)
    if canon is not None:
        return canon, []
    # ambiguous: multiple keys normalize to distinct canonicals starting with the raw name
    candidates = [v for k, v in alias_map.items() if k == norm]
    if len(candidates) == 1:
        return candidates[0], []
    prefix = [v for k, v in alias_map.items() if k.startswith(norm)]
    if len(set(prefix)) > 1:
        return None, [f"alias prefix {norm} resolves to multiple canonicals: {sorted(set(prefix))}"]
    return None, [f"unresolved alias: {raw}"]


def normalize_row(
    row: dict[str, Any],
    alias_map: Mapping[str, str] | None = None,
    stock_resolver: Callable[[str], bool] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Normalize one formula row. Returns (normalized_row, notes). Fail-closed on alias/stock."""
    notes: list[str] = []
    raw = row.get("raw_material_name", "")
    canon, alias_notes = resolve_alias(raw, alias_map)
    if canon is None:
        notes.extend(alias_notes)
    out = dict(row)
    out["canonical_material_name"] = canon
    out["_alias_resolved"] = canon is not None
    if stock_resolver is not None:
        stock_ok = stock_resolver(str(row.get("exact_supplied_stock", "")))
        out["_stock_resolved"] = stock_ok
        if not stock_ok:
            notes.append(f"exact stock unresolved: {row.get('exact_supplied_stock')}")
    af = row.get("active_fraction_or_PRODUCT_BASIS")
    if af == PRODUCT_BASIS:
        out["active_fraction"] = None
        out["product_basis"] = True
    else:
        out["active_fraction"] = float(af) if af is not None else None
        out["product_basis"] = False
    out["active_ul_estimate"] = round(
        float(row.get("parts", 0.0)) * (out["active_fraction"] or 0.0), 6
    )
    return out, notes


def carrier_ledger(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ledger: dict[str, float] = {}
    for r in rows:
        carrier = r.get("declared_carrier")
        if carrier:
            ledger[carrier] = ledger.get(carrier, 0.0) + float(r.get("parts", 0.0))
    return [{"carrier": k, "parts_total": round(v, 6)} for k, v in sorted(ledger.items())]


def inventory_crosswalk(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "row_number": r.get("row_number"),
            "raw_material_name": r.get("raw_material_name"),
            "canonical_material_name": r.get("canonical_material_name"),
            "exact_supplied_stock": r.get("exact_supplied_stock"),
            "inventory_status": r.get("inventory_status"),
            "_stock_resolved": r.get("_stock_resolved"),
            "_alias_resolved": r.get("_alias_resolved"),
        }
        for r in rows
    ]
