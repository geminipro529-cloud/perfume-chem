"""Inventory-to-supplier documentation census with fail-closed identity matching.

The census preserves every physical stock row.  Supplier matches come from an
already-reviewed registry SKU or a unique case/whitespace-only name match.  It
never fuzzy-matches an inventory identity into a supplier product.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from engine.data_spine.loader import load_registry
from engine.inventory_parser import parse_inventory

_BULLET_RE = re.compile(r"^\s*[-•]\s+")


def _exact_key(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


@dataclass(frozen=True)
class SupplierDocumentCensusRow:
    inventory_ordinal: int
    inventory_source_line: int
    inventory_raw_name: str
    canonical_name: str
    category: str
    inventory_status: str
    stock_fraction: float
    stock_fraction_basis: str
    stock_carrier: str
    quantitative_execution_ready: bool
    execution_hold_reason: str
    perfumersworld_match_state: str
    perfumersworld_sku: str
    perfumersworld_candidate_skus: tuple[str, ...]
    perfumersworld_product_name: str
    perfumersworld_product_url: str
    perfumersworld_document_url: str
    supplier_snapshot_price_usd: float | None
    supplier_snapshot_price_unit: str

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["perfumersworld_candidate_skus"] = list(
            self.perfumersworld_candidate_skus
        )
        return payload


def _load_supplier_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise ValueError("PerfumersWorld supplier snapshot must be a JSON row list")
    return payload


def build_supplier_document_census(
    *,
    inventory_path: Path,
    supplier_snapshot_path: Path,
) -> list[SupplierDocumentCensusRow]:
    """Return one evidence row per inventory bullet without identity invention."""

    inventory_path = Path(inventory_path)
    supplier_snapshot_path = Path(supplier_snapshot_path)
    materials = parse_inventory(
        inventory_path,
        unique=False,
        include_solvents=True,
        include_unavailable=True,
    )
    source_lines = [
        line_number
        for line_number, line in enumerate(
            inventory_path.read_text(encoding="utf-8").splitlines(), start=1
        )
        if _BULLET_RE.match(line)
    ]
    if len(source_lines) != len(materials):
        raise ValueError(
            "inventory bullet lineage drift: "
            f"{len(source_lines)} source bullets != {len(materials)} parsed rows"
        )

    supplier_rows = _load_supplier_rows(supplier_snapshot_path)
    rows_by_exact_name: dict[str, list[dict[str, Any]]] = {}
    rows_by_sku: dict[str, dict[str, Any]] = {}
    for supplier_row in supplier_rows:
        sku = str(supplier_row.get("sku") or "").strip()
        if sku:
            rows_by_sku.setdefault(sku, supplier_row)
        keys = {
            _exact_key(supplier_row.get("base_name")),
            _exact_key(supplier_row.get("raw_name")),
        }
        for key in keys - {""}:
            rows_by_exact_name.setdefault(key, []).append(supplier_row)

    registry = load_registry()
    census: list[SupplierDocumentCensusRow] = []
    for ordinal, (source_line, material) in enumerate(
        zip(source_lines, materials, strict=True), start=1
    ):
        registry_material = registry.get(material.name)
        supplier_refs = getattr(registry_material, "supplier", None)
        registry_sku = str(
            getattr(supplier_refs, "perfumersworld_sku", "") or ""
        ).strip()

        exact_candidates = rows_by_exact_name.get(_exact_key(material.name), [])
        candidate_by_sku = {
            str(row.get("sku") or "").strip(): row
            for row in exact_candidates
            if str(row.get("sku") or "").strip()
        }
        candidate_skus = tuple(sorted(candidate_by_sku))

        if registry_sku:
            match_state = "REGISTRY_SKU"
            selected_sku = registry_sku
        elif len(candidate_skus) == 1:
            match_state = "EXACT_NAME_SKU"
            selected_sku = candidate_skus[0]
        elif len(candidate_skus) > 1:
            match_state = "AMBIGUOUS_EXACT_NAME"
            selected_sku = ""
        else:
            match_state = "NO_EXACT_PW_MATCH"
            selected_sku = ""

        selected = rows_by_sku.get(selected_sku, {})
        product_name = str(
            selected.get("base_name") or selected.get("raw_name") or ""
        ).strip()
        census.append(
            SupplierDocumentCensusRow(
                inventory_ordinal=ordinal,
                inventory_source_line=source_line,
                inventory_raw_name=material.raw_name,
                canonical_name=material.name,
                category=material.category,
                inventory_status=material.status,
                stock_fraction=material.dilution,
                stock_fraction_basis=material.fraction_basis,
                stock_carrier=material.carrier,
                quantitative_execution_ready=material.execution_ready,
                execution_hold_reason=material.execution_hold_reason,
                perfumersworld_match_state=match_state,
                perfumersworld_sku=selected_sku,
                perfumersworld_candidate_skus=candidate_skus,
                perfumersworld_product_name=product_name,
                perfumersworld_product_url=(
                    f"https://www.perfumersworld.com/view.php?pro_id={selected_sku}"
                    if selected_sku
                    else ""
                ),
                perfumersworld_document_url=(
                    "https://www.perfumersworld.com/document-list.php"
                    f"?ifra=defaultOpen&pro_id={selected_sku}"
                    if selected_sku
                    else ""
                ),
                supplier_snapshot_price_usd=(
                    float(selected["price_usd"])
                    if selected.get("price_usd") is not None
                    else None
                ),
                supplier_snapshot_price_unit=str(
                    selected.get("price_unit") or ""
                ).strip(),
            )
        )
    return census
