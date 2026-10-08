"""Checkpoint 13 governed Wakayama identity and correction admission."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.calibration.hashing import UTF8_TEXT_FILE_HASH_ALGORITHM
from engine.research.capabilities import (
    adjudicate_wakayama_identities,
    load_local_identity_index,
)


SUMMARY = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "governance"
    / "wakayama_identity_adjudication_summary_20261007.json"
)


def test_all_314_rows_receive_one_conservative_adjudication_state() -> None:
    report = adjudicate_wakayama_identities()
    admitted_states = {
        "EXACT_IDENTITY_BOUND",
        "PRODUCT_OR_GRADE_AMBIGUOUS",
        "CAS_NAME_CONFLICT",
        "NO_LOCAL_IDENTITY",
        "WITHHELD_LICENSE_OR_SOURCE",
        "NOT_APPLICABLE",
    }
    assert report["source_row_count"] == 314
    assert report["positive_curve_count"] == 313
    assert sum(report["state_counts"].values()) == 314
    assert {row["adjudication_state"] for row in report["rows"]} <= admitted_states
    assert all(row["adjudication_state"] in admitted_states for row in report["rows"])
    assert report["capability_admission_state"] == "HOLD_EXACT_STOCK_RANGE_MATRIX_BINDING"
    assert report["exact_stock_binding_count"] == 0


def test_known_source_cas_name_conflict_and_zero_slope_are_not_promoted() -> None:
    rows = {row["source_cas"]: row for row in adjudicate_wakayama_identities()["rows"]}
    assert rows["140-88-5"]["adjudication_state"] == "CAS_NAME_CONFLICT"
    assert rows["121-33-5"]["adjudication_state"] == "NOT_APPLICABLE"
    assert rows["121-33-5"]["threshold_roundtrip"] is None


def test_every_positive_curve_passes_explicit_ng_l_to_ug_l_roundtrip() -> None:
    report = adjudicate_wakayama_identities()
    roundtrips = [row["threshold_roundtrip"] for row in report["rows"] if row["threshold_roundtrip"]]
    assert len(roundtrips) == 313
    assert all(item["passed"] for item in roundtrips)
    assert all(
        item["threshold_ug_l_air"] == pytest.approx(item["threshold_ng_l_air"] / 1000.0)
        for item in roundtrips
    )


def test_source_hash_failure_withholds_every_row(tmp_path: Path) -> None:
    original = Path("data/governance/measured_intensity_capabilities_20260923.json")
    manifest = json.loads(original.read_text(encoding="utf-8"))
    manifest["source"]["transcription_artifact_sha256"] = "0" * 64
    changed = tmp_path / "manifest.json"
    changed.write_text(json.dumps(manifest), encoding="utf-8")
    rules = json.loads(
        Path("data/governance/wakayama_identity_adjudication_rules_v1.json").read_text(
            encoding="utf-8"
        )
    )
    rule_file = tmp_path / "rules.json"
    rule_file.write_text(json.dumps(rules), encoding="utf-8")

    report = adjudicate_wakayama_identities(
        manifest_path=changed,
        rules_path=rule_file,
    )
    assert report["state_counts"] == {"WITHHELD_LICENSE_OR_SOURCE": 314}
    assert report["transcription_artifact_verified"] is False


def test_compact_adjudication_summary_reproduces_current_report() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    report = adjudicate_wakayama_identities()
    assert summary["reproduction"] == {
        "implementation": "engine/research/capabilities.py",
        "source_manifest_sha256": report["source_manifest_sha256"],
        "rules_sha256": report["rules_sha256"],
        "local_identity_manifest_schema_version": report[
            "local_identity_manifest_schema_version"
        ],
        "local_identity_hash_semantics": report[
            "local_identity_hash_semantics"
        ],
        "local_identity_manifest_sha256": report["local_identity_manifest_sha256"],
        "full_report_sha256": report["report_sha256"],
    }
    assert summary["verification"] == {
        "source_artifact_verified": report["source_artifact_verified"],
        "transcription_artifact_verified": report["transcription_artifact_verified"],
        "license_present": report["license_present"],
        "source_row_count": report["source_row_count"],
        "positive_curve_count": report["positive_curve_count"],
        "state_counts": report["state_counts"],
        "exact_stock_binding_count": report["exact_stock_binding_count"],
        "observed_range_bound_count": report["observed_range_bound_count"],
    }
    assert summary["capability_admission_state"] == report["capability_admission_state"]
    assert summary["formula_action"] == "NO_CHANGE"
    assert all(value is False for value in summary["authority"].values())


def test_local_identity_manifest_is_stable_across_lf_and_crlf_checkouts(
    tmp_path: Path,
) -> None:
    material_root = tmp_path / "materials"
    material_root.mkdir()
    payload_lf = (
        "- canonical_name: Lavender marker\n"
        "  cas: 78-70-6\n"
        "  aliases:\n"
        "    - Linalool marker\n"
    ).encode("utf-8")
    material_file = material_root / "L.yaml"
    material_file.write_bytes(payload_lf)
    lf_index = load_local_identity_index(material_root)
    material_file.write_bytes(payload_lf.replace(b"\n", b"\r\n"))
    crlf_index = load_local_identity_index(material_root)

    assert lf_index["schema_version"] == "local-material-identity-index-v2"
    assert lf_index["file_hash_semantics"] == UTF8_TEXT_FILE_HASH_ALGORITHM
    assert lf_index["file_manifest"] == crlf_index["file_manifest"]
    assert lf_index["file_manifest_sha256"] == crlf_index["file_manifest_sha256"]
