"""Archive public PerfumersWorld evidence with hashes and content validation."""

from __future__ import annotations

import hashlib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class FetchResponse:
    status_code: int
    content_type: str
    body: bytes


_DOCUMENT_TARGETS = (
    (
        "product",
        "product.html",
        "https://www.perfumersworld.com/view.php?pro_id={sku}",
        "html",
    ),
    (
        "document_live",
        "documents_live.html",
        "https://www.perfumersworld.com/document-list.php?ifra=defaultOpen&pro_id={sku}",
        "html",
    ),
    (
        "coa",
        "coa.pdf",
        "https://www.perfumersworld.com/ifra/COA/{sku}.pdf",
        "pdf",
    ),
    (
        "legacy_msds",
        "msds_legacy.pdf",
        "https://www.perfumersworld.com/ifra/MSDS/{sku}.pdf",
        "pdf",
    ),
    (
        "legacy_allergen_sccnfp",
        "allergen_sccnfp.pdf",
        "https://www.perfumersworld.com/ifra/SCCNFP/{sku}.pdf",
        "pdf",
    ),
)


def _content_is_valid(kind: str, response: FetchResponse) -> bool:
    content_type = response.content_type.casefold()
    if kind == "pdf":
        return "pdf" in content_type and response.body.startswith(b"%PDF-")
    leading = response.body.lstrip(b"\xef\xbb\xbf\x00\t\r\n ")[:64].lower()
    return "html" in content_type and (b"<!doctype" in leading or b"<html" in leading)


def archive_perfumersworld_documents(
    *,
    skus: list[str] | tuple[str, ...] | set[str],
    output_root: Path,
    fetcher: Callable[[str], FetchResponse],
    fetched_at: str,
    max_workers: int = 8,
) -> dict[str, object]:
    """Fetch official supplier surfaces concurrently and hash valid bytes."""

    normalized_skus = sorted({str(sku).strip() for sku in skus})
    invalid = [sku for sku in normalized_skus if not re.fullmatch(r"[A-Za-z0-9]+", sku)]
    if invalid:
        raise ValueError(f"invalid PerfumersWorld SKU: {invalid[0]!r}")
    if max_workers < 1:
        raise ValueError("max_workers must be positive")

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    tasks: list[tuple[str, str, str, str, str]] = []
    for sku in normalized_skus:
        for document_kind, filename, url_template, expected_kind in _DOCUMENT_TARGETS:
            tasks.append(
                (
                    sku,
                    document_kind,
                    filename,
                    url_template.format(sku=sku),
                    expected_kind,
                )
            )

    entries: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetcher, url): (sku, document_kind, filename, url, expected)
            for sku, document_kind, filename, url, expected in tasks
        }
        for future in as_completed(futures):
            sku, document_kind, filename, url, expected_kind = futures[future]
            entry: dict[str, object] = {
                "sku": sku,
                "document_kind": document_kind,
                "url": url,
                "fetched_at": fetched_at,
                "state": "",
                "http_status": 0,
                "content_type": "",
                "relative_path": "",
                "byte_size": 0,
                "sha256": "",
                "error": "",
            }
            try:
                response = future.result()
            except Exception as exc:  # network boundary is recorded, never promoted
                entry["state"] = "FETCH_ERROR"
                entry["error"] = f"{type(exc).__name__}: {exc}"
                entries.append(entry)
                continue

            entry["http_status"] = int(response.status_code)
            entry["content_type"] = str(response.content_type)
            if response.status_code != 200:
                entry["state"] = "HTTP_ERROR"
                entries.append(entry)
                continue
            if not _content_is_valid(expected_kind, response):
                entry["state"] = "INVALID_CONTENT"
                entries.append(entry)
                continue

            destination = output_root / sku / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.body)
            relative_path = destination.relative_to(output_root).as_posix()
            entry.update(
                {
                    "state": "SAVED",
                    "relative_path": relative_path,
                    "byte_size": len(response.body),
                    "sha256": hashlib.sha256(response.body).hexdigest(),
                }
            )
            entries.append(entry)

    target_order = {
        document_kind: index
        for index, (document_kind, _filename, _url, _kind) in enumerate(
            _DOCUMENT_TARGETS
        )
    }
    entries.sort(key=lambda entry: (str(entry["sku"]), target_order[str(entry["document_kind"])]))
    states = [str(entry["state"]) for entry in entries]
    return {
        "schema_version": "perfumersworld_document_archive_v1",
        "source_authority": "OFFICIAL_PERFUMERSWORLD_PUBLIC_SURFACES",
        "fetched_at": fetched_at,
        "sku_count": len(normalized_skus),
        "target_count": len(entries),
        "saved_count": states.count("SAVED"),
        "invalid_content_count": states.count("INVALID_CONTENT"),
        "http_error_count": states.count("HTTP_ERROR"),
        "fetch_error_count": states.count("FETCH_ERROR"),
        "authority_limits": {
            "creates_inventory_ownership": False,
            "creates_stock_fraction_or_carrier": False,
            "creates_sensory_or_hedonic_evidence": False,
            "creates_final_product_safety_or_stability": False,
            "creates_formula_or_release_authority": False,
        },
        "entries": entries,
    }
