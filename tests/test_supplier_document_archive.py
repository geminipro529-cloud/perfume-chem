from __future__ import annotations

import hashlib
from pathlib import Path

from engine.supplier_document_archive import (
    FetchResponse,
    archive_perfumersworld_documents,
)


def test_archive_hashes_valid_official_surfaces_and_rejects_false_pdfs(tmp_path: Path) -> None:
    html = b"<!doctype html><html><body>official</body></html>"
    pdf = b"%PDF-1.7\ncontrolled fixture"

    def fetcher(url: str) -> FetchResponse:
        if "/ifra/COA/" in url:
            return FetchResponse(200, "application/pdf", pdf)
        if "/ifra/MSDS/" in url:
            return FetchResponse(200, "text/html", html)
        if "/ifra/SCCNFP/" in url:
            return FetchResponse(404, "text/html", b"not found")
        return FetchResponse(200, "text/html; charset=utf-8", html)

    manifest = archive_perfumersworld_documents(
        skus=["6UP07515"],
        output_root=tmp_path,
        fetcher=fetcher,
        fetched_at="2026-08-30T00:00:00Z",
        max_workers=2,
    )

    assert manifest["schema_version"] == "perfumersworld_document_archive_v1"
    assert manifest["sku_count"] == 1
    assert manifest["target_count"] == 5
    assert manifest["saved_count"] == 3
    assert manifest["invalid_content_count"] == 1
    assert manifest["http_error_count"] == 1

    saved = {entry["document_kind"]: entry for entry in manifest["entries"]}
    assert saved["product"]["state"] == "SAVED"
    assert saved["document_live"]["state"] == "SAVED"
    assert saved["coa"]["state"] == "SAVED"
    assert saved["legacy_msds"]["state"] == "INVALID_CONTENT"
    assert saved["legacy_allergen_sccnfp"]["state"] == "HTTP_ERROR"

    coa_path = tmp_path / saved["coa"]["relative_path"]
    assert coa_path.read_bytes() == pdf
    assert saved["coa"]["byte_size"] == len(pdf)
    assert saved["coa"]["sha256"] == hashlib.sha256(pdf).hexdigest()
    assert not (tmp_path / "6UP07515" / "msds_legacy.pdf").exists()


def test_archive_rejects_sku_path_traversal(tmp_path: Path) -> None:
    def fetcher(url: str) -> FetchResponse:
        raise AssertionError("invalid SKU must be rejected before fetching")

    try:
        archive_perfumersworld_documents(
            skus=["../secret"],
            output_root=tmp_path,
            fetcher=fetcher,
            fetched_at="2026-08-30T00:00:00Z",
        )
    except ValueError as exc:
        assert "invalid PerfumersWorld SKU" in str(exc)
    else:
        raise AssertionError("path-traversal SKU was accepted")
