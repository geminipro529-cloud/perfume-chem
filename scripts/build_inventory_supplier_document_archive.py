"""Build the 273-row inventory census and archive official PW documents."""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.supplier_document_archive import (  # noqa: E402
    FetchResponse,
    archive_perfumersworld_documents,
)
from engine.supplier_document_census import build_supplier_document_census  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fetch(url: str) -> FetchResponse:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Perfume-Chem evidence archiver/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return FetchResponse(
                status_code=int(response.status),
                content_type=str(response.headers.get("Content-Type") or ""),
                body=response.read(),
            )
    except urllib.error.HTTPError as exc:
        return FetchResponse(
            status_code=int(exc.code),
            content_type=str(exc.headers.get("Content-Type") or ""),
            body=exc.read(),
        )


def _escape(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def main() -> int:
    inventory_path = PROJECT_ROOT / "inventory.txt"
    supplier_snapshot_path = (
        PROJECT_ROOT
        / "data"
        / "materials"
        / "_sources"
        / "perfumersworld_stock.parsed.json"
    )
    archive_root = PROJECT_ROOT / "data" / "external" / "perfumersworld"
    census_path = (
        PROJECT_ROOT
        / "data"
        / "governance"
        / "inventory_supplier_document_census_20260830.json"
    )
    archive_manifest_path = (
        PROJECT_ROOT
        / "data"
        / "source_manifests"
        / "perfumersworld_inventory_documents_20260830.json"
    )
    report_path = (
        PROJECT_ROOT
        / "docs"
        / "research"
        / "INVENTORY_273_MATERIAL_DOCUMENT_REGISTER_20260830.md"
    )

    census = build_supplier_document_census(
        inventory_path=inventory_path,
        supplier_snapshot_path=supplier_snapshot_path,
    )
    skus = sorted({row.perfumersworld_sku for row in census if row.perfumersworld_sku})
    fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    archive_manifest = archive_perfumersworld_documents(
        skus=skus,
        output_root=archive_root,
        fetcher=_fetch,
        fetched_at=fetched_at,
        max_workers=16,
    )
    archive_manifest.update(
        {
            "inventory_path": "inventory.txt",
            "inventory_sha256": _sha256(inventory_path),
            "supplier_snapshot_path": (
                "data/materials/_sources/perfumersworld_stock.parsed.json"
            ),
            "supplier_snapshot_sha256": _sha256(supplier_snapshot_path),
            "census_row_count": len(census),
            "unique_exact_sku_count": len(skus),
        }
    )
    archive_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    archive_manifest_path.write_text(
        json.dumps(archive_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    documents_by_sku: dict[str, list[dict[str, object]]] = defaultdict(list)
    for entry in archive_manifest["entries"]:
        documents_by_sku[str(entry["sku"])].append(entry)

    match_counts = Counter(row.perfumersworld_match_state for row in census)
    census_payload = {
        "schema_version": "perfume_chem_inventory_supplier_document_census_v1",
        "generated_at": fetched_at,
        "inventory": {
            "path": "inventory.txt",
            "sha256": _sha256(inventory_path),
            "raw_row_count": len(census),
        },
        "supplier_snapshot": {
            "path": "data/materials/_sources/perfumersworld_stock.parsed.json",
            "sha256": _sha256(supplier_snapshot_path),
        },
        "match_counts": dict(sorted(match_counts.items())),
        "unique_exact_sku_count": len(skus),
        "document_archive_manifest": (
            "data/source_manifests/perfumersworld_inventory_documents_20260830.json"
        ),
        "authority_limits": {
            "exact_supplier_documentation_is_stock_ownership": False,
            "supplier_typical_use_is_formula_authority": False,
            "supplier_odor_description_is_blinded_sensory_evidence": False,
            "supplier_ifra_or_sds_is_final_product_safety_authority": False,
            "missing_or_ambiguous_supplier_identity_is_held": True,
        },
        "rows": [
            {
                **row.as_dict(),
                "archived_documents": documents_by_sku.get(
                    row.perfumersworld_sku, []
                ),
            }
            for row in census
        ],
    }
    census_path.parent.mkdir(parents=True, exist_ok=True)
    census_path.write_text(
        json.dumps(census_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report_lines = [
        "# Inventory 273-Material Supplier Document Register — 2026-08-30",
        "",
        "This is a lossless row register, not a beauty score or formula authorization. "
        "Exact supplier documentation supports identity and document availability only. "
        "Ambiguous and missing identities remain HOLD; stock basis/carrier holds remain in force.",
        "",
        f"- Inventory rows: **{len(census)}**",
        f"- Unique exact PerfumersWorld SKUs: **{len(skus)}**",
        f"- Supplier-match states: **{dict(sorted(match_counts.items()))}**",
        f"- Official document targets saved: **{archive_manifest['saved_count']} / {archive_manifest['target_count']}**",
        f"- Invalid-content targets: **{archive_manifest['invalid_content_count']}**",
        f"- HTTP errors: **{archive_manifest['http_error_count']}**",
        f"- Fetch errors: **{archive_manifest['fetch_error_count']}**",
        "",
        "| # | Inventory material / stock | Category | Stock authority | Quantitative state | PW identity | Saved official surfaces |",
        "|---:|---|---|---|---|---|---|",
    ]
    for row in census:
        stock = f"{row.stock_fraction * 100:g}%"
        if row.stock_fraction_basis:
            stock += f" {row.stock_fraction_basis}"
        if row.stock_carrier:
            stock += f" in {row.stock_carrier.upper()}"
        quantitative = (
            "READY"
            if row.quantitative_execution_ready
            else f"HOLD: {row.execution_hold_reason or 'UNRESOLVED'}"
        )
        if row.perfumersworld_sku:
            pw_identity = (
                f"{row.perfumersworld_product_name} / {row.perfumersworld_sku} "
                f"({row.perfumersworld_match_state})"
            )
        elif row.perfumersworld_candidate_skus:
            pw_identity = (
                f"HOLD {row.perfumersworld_match_state}: "
                + ", ".join(row.perfumersworld_candidate_skus)
            )
        else:
            pw_identity = row.perfumersworld_match_state
        archived = documents_by_sku.get(row.perfumersworld_sku, [])
        saved_kinds = [
            str(entry["document_kind"])
            for entry in archived
            if entry["state"] == "SAVED"
        ]
        report_lines.append(
            "| "
            + " | ".join(
                [
                    str(row.inventory_ordinal),
                    _escape(row.inventory_raw_name),
                    _escape(row.category),
                    _escape(stock),
                    _escape(quantitative),
                    _escape(pw_identity),
                    _escape(", ".join(saved_kinds) or "none"),
                ]
            )
            + " |"
        )
    report_lines.extend(
        [
            "",
            "## Authority boundary",
            "",
            "Supplier pages, CoAs, SDS/MSDS files, allergen declarations, and IFRA material certificates do not prove the user's exact lot, current bottle homogeneity, sensory performance, liking, target fidelity, final-product safety, stability, or release. A material with missing stock basis, carrier, density, exact identity, or a product mismatch remains held at the affected layer.",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "census": str(census_path),
                "archive_manifest": str(archive_manifest_path),
                "report": str(report_path),
                "rows": len(census),
                "unique_skus": len(skus),
                "saved": archive_manifest["saved_count"],
                "targets": archive_manifest["target_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
