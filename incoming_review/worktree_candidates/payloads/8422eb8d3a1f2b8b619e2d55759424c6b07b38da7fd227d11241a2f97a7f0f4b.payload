from __future__ import annotations

import csv
import hashlib
import io
import json
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile

from engine.calibration.hashing import stable_json_hash
from engine.ingestion.archive_quarantine import scan_archive_graph_quarantine
from engine.ingestion.package_receipts import (
    load_external_package_receipt,
    validate_external_package_receipt,
    verify_external_package_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = (
    ROOT
    / "data"
    / "governance"
    / "chat_c_formula_corpora_patent_mining_xhigh_v1_package_receipt_20260819.json"
)
CAPTURE_DIR = (
    ROOT / "incoming_review" / "chatgpt" / ("20260819T124503Z-chat-c-formula-corpora-6a753b26")
)
CAPTURE_MANIFEST_PATH = CAPTURE_DIR / "source_manifest.json"
PACKAGE_ROOT = "CHAT_C_FORMULA_CORPORA_PATENT_MINING_XHIGH"


def _read_json(archive: ZipFile, member: str) -> dict:
    return json.loads(archive.read(f"{PACKAGE_ROOT}/{member}"))


def test_chat_c_package_is_exact_source_grammar_with_zero_execution_authority() -> None:
    """Protect exact recovery and keep patent/history rows out of executable formulas."""

    receipt = load_external_package_receipt(RECEIPT_PATH)
    validate_external_package_receipt(receipt)
    package_path = ROOT / receipt["package"]["locator"]
    verification = verify_external_package_bytes(receipt, package_path=package_path)

    assert verification.integrity_verified is True
    assert verification.status == "VERIFIED_QUARANTINED"
    assert verification.package_sha256 == (
        "ce6e95f40cd53bdc3c94f169ccb9761638500ae085be23df7b7abc2db94bb42d"
    )
    assert verification.archive_entry_count == 27
    assert verification.archive_file_count == 27
    assert verification.promotion_allowed is False
    assert verification.errors == ()
    assert receipt["provenance"]["conversation_id"] == ("6a753b26-53b4-83ec-92ec-02cdc8d63629")
    assert receipt["provenance"]["rights"]["reuse_status"] == "UNKNOWN"
    assert receipt["provenance"]["rights"]["redistribution_allowed"] is False
    assert not any(receipt["authority"].values())
    assert not any(
        receipt["admission"][field]
        for field in (
            "b1_promotion_allowed",
            "canonical_import_allowed",
            "repository_content_import_allowed",
            "row_projection_allowed",
        )
    )

    capture_manifest = json.loads(CAPTURE_MANIFEST_PATH.read_text(encoding="utf-8"))
    unhashed = deepcopy(capture_manifest)
    declared_manifest_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_manifest_hash
    manifest_parent = next(
        parent
        for parent in receipt["parents"]
        if parent["relation"] == "BINDS_BROWSER_CAPTURE_MANIFEST"
    )
    assert manifest_parent["byte_size"] == CAPTURE_MANIFEST_PATH.stat().st_size
    assert (
        manifest_parent["sha256"] == hashlib.sha256(CAPTURE_MANIFEST_PATH.read_bytes()).hexdigest()
    )

    with ZipFile(package_path) as archive:
        assert archive.testzip() is None
        ledger = _read_json(archive, "SHA256SUMS.json")
        assert ledger["file_count"] == len(ledger["files"]) == 26
        expected_names = {f"{PACKAGE_ROOT}/{name}" for name in ledger["files"]}
        assert expected_names == set(archive.namelist()) - {f"{PACKAGE_ROOT}/SHA256SUMS.json"}
        for relative_path, expected in ledger["files"].items():
            payload = archive.read(f"{PACKAGE_ROOT}/{relative_path}")
            assert len(payload) == expected["bytes"]
            assert hashlib.sha256(payload).hexdigest() == expected["sha256"]

        validation = _read_json(archive, "VALIDATION_REPORT.json")
        worker = _read_json(archive, "WORKER_MANIFEST.json")
        patents = _read_json(archive, "PATENT_WORKED_EXAMPLE_REGISTRY.json")
        historical = _read_json(archive, "HISTORICAL_REPRESENTATIVE_EXAMPLES.json")
        grammar_rows = list(
            csv.DictReader(
                io.StringIO(
                    archive.read(f"{PACKAGE_ROOT}/FORMULA_GRAMMAR_DATASET.csv").decode("utf-8-sig")
                )
            )
        )
        delta_rows = list(
            csv.DictReader(
                io.StringIO(
                    archive.read(f"{PACKAGE_ROOT}/FORMULA_DELTA_LEDGER.csv").decode("utf-8-sig")
                )
            )
        )

    counts = validation["counts"]
    assert validation["state"] == "PASS_WITH_DECLARED_HOLDS"
    assert counts == {
        "controlled_delta_rows": 2,
        "formula_grammar_rows": 130,
        "historical_examples_validated": 2,
        "historical_formula_rows": 25,
        "historical_source_bytes_pinned": 1,
        "patent_formula_arms": 5,
        "patent_formula_rows": 105,
        "patent_publications_byte_pinned": 4,
    }
    assert validation["baseline"]["access_state"] == (
        "MANIFEST_AND_PACKAGE_SHA_VERIFIED; UPSTREAM_ZIP_BYTES_NOT_MOUNTED_LOCALLY"
    )
    assert "HOLD_BASELINE_PACKAGE_BYTES" in validation["declared_holds"]
    assert "HOLD_PERMISSION_CREDENTIALS_OLFACTORIAN" in validation["declared_holds"]
    assert validation["checks"]["no_silent_trade_to_molecule_conversion"] is True
    assert validation["checks"]["patent_sensory_claims_not_independent_validation"] is True
    assert validation["checks"]["original_rows_preserved"] is True

    patent_examples = [example for record in patents["records"] for example in record["examples"]]
    assert len(patents["records"]) == 4
    assert len(patent_examples) == 5
    assert [len(example["formula_rows"]) for example in patent_examples] == [22, 13, 13, 25, 32]
    assert [len(example["formula_rows"]) for example in historical["examples"]] == [16, 9]
    assert len(grammar_rows) == 130
    assert len(delta_rows) == 2
    assert {row["source_document_id"] for row in grammar_rows} == {
        "DEITE1892",
        "EP3042891A1",
        "US20120058073A1",
        "US6495186B1",
        "US8168163B2",
    }
    assert {row["frequency_is_hedonic"] for row in grammar_rows} == {"FALSE"}
    assert {row["product_basis"] for row in grammar_rows} == {"FALSE", "TRUE"}
    us816_rows = [row for row in grammar_rows if row["source_document_id"] == "US8168163B2"]
    assert len(us816_rows) == 26
    assert {row["normalization_state"] for row in us816_rows} == {
        "MATHEMATICAL_REEXPRESSION_OF_SOURCE_TOTAL_990"
    }
    assert {row["causal_control_role"] for row in us816_rows} == {"CONTROL", "TEST"}
    collapsed_absence_rows = [
        row
        for row in us816_rows
        if (row["example_id"], row["raw_material_text"])
        in {
            ("C-PAT-002-EX3-PLUS", "DPG"),
            (
                "C-PAT-002-EX3-MINUS",
                "[(4E,4Z)-5-methoxy-3-methyl-4-pentenyl]-benzene",
            ),
        }
    ]
    assert len(collapsed_absence_rows) == 2
    assert {row["raw_amount"] for row in collapsed_absence_rows} == {"0"}

    assert worker["formula_mutations"] == 0
    assert worker["inventory_mutations"] == 0
    assert worker["physical_truth_mutations"] == 0
    assert worker["release_state_mutations"] == 0

    graph = scan_archive_graph_quarantine(package_path)
    assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
    assert graph.all_nodes_terminal is True
    assert graph.promotion_allowed is False
    assert "PARTIAL_MEMBER_SCAN" in {
        finding.code for node in graph.nodes for finding in node.scan.findings
    }

    summary = receipt["evidence_summary"]
    assert summary["package_recovered"] is True
    assert summary["internal_checksum_entries_verified"] == 26
    assert summary["patent_formula_rows"] == 105
    assert summary["historical_formula_rows"] == 25
    assert summary["formula_grammar_rows"] == 130
    assert summary["source_explicit_absence_rows_expected"] == 2
    assert summary["package_explicit_absence_rows_preserved_as_non_numeric"] == 0
    assert summary["source_explicit_absence_representation_lossless"] is False
    assert summary["source_rows_admitted"] == 0
    assert summary["executable_formula_rows_installed"] == 0
    assert summary["promotion_allowed"] is False
