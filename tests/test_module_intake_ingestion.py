"""Tests for the generic external-candidate ingestion adapter (engine.ingestion).

Covers: happy path, arithmetic, deterministic hash replay, product-basis preservation,
and fail-closed rejections (totals, unresolved stock, ambiguous alias, invented active
fraction, formula/empirical conflation, note-name->material, missing inventory snapshot,
missing source hash). No domain-model mutation; runs read-only.
"""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.ingestion import deterministic_hash, ingest_external_candidate
from engine.ingestion.schema import PRODUCT_BASIS, REQUIRED_CANDIDATE_FIELDS

STOCK_OK = {
    "bergamot fcf": True,
    "hedione": True,
    "iso e super": True,
    "ambrox super 30%": True,
    "opaque accord": True,
    "jasmine": False,
    "rose": False,
    "orris": False,
}


def make_candidate(overrides=None):
    cand = {
        "candidate_id": "EXT-001",
        "target_id": "TGT-001",
        "target_name": "Test Floral",
        "target_version": "v1",
        "concentration": "20% w/w",
        "region_or_jurisdiction": "EU",
        "formula_uid": "F-1",
        "parent_formula_uid": None,
        "formula_state": "COMPUTATIONAL_RECONSTRUCTION_CANDIDATE",
        "empirical_state": "NOT_EMPIRICALLY_VERIFIED",
        "source_artifact_paths": ["ext/test.json"],
        "source_artifact_hashes": ["ab12cd34"],
        "inventory_snapshot_id": "SNAP-1",
        "inventory_snapshot_hash": "ff00aa11",
        "evidence_refs": ["SRC-1"],
        "provenance": {"producer": "test", "method": "fixture"},
        "formula_rows": [
            {
                "row_number": 1,
                "raw_material_name": "Bergamot FCF",
                "canonical_material_name": "bergamot fcf",
                "exact_supplied_stock": "bergamot fcf",
                "parts": 300.0,
                "active_fraction_or_PRODUCT_BASIS": 1.0,
                "declared_carrier": None,
                "perceptual_function": "top",
                "structural_function": "radiance",
                "phase_roles": ["top"],
                "evidence_class": "structural",
                "evidence_refs": [],
                "dose_rationale": "fixture",
                "plausible_alternatives": [],
                "inventory_status": "in_stock",
                "confidence": 0.8,
                "uncertainty": 0.1,
            },
            {
                "row_number": 2,
                "raw_material_name": "Hedione",
                "canonical_material_name": "hedione",
                "exact_supplied_stock": "hedione",
                "parts": 500.0,
                "active_fraction_or_PRODUCT_BASIS": 1.0,
                "declared_carrier": None,
                "perceptual_function": "heart",
                "structural_function": "radiance",
                "phase_roles": ["heart"],
                "evidence_class": "structural",
                "evidence_refs": [],
                "dose_rationale": "fixture",
                "plausible_alternatives": [],
                "inventory_status": "in_stock",
                "confidence": 0.8,
                "uncertainty": 0.1,
            },
            {
                "row_number": 3,
                "raw_material_name": "Iso E Super",
                "canonical_material_name": "iso e super",
                "exact_supplied_stock": "iso e super",
                "parts": 200.0,
                "active_fraction_or_PRODUCT_BASIS": 1.0,
                "declared_carrier": None,
                "perceptual_function": "base",
                "structural_function": "skin effect",
                "phase_roles": ["base"],
                "evidence_class": "structural",
                "evidence_refs": [],
                "dose_rationale": "fixture",
                "plausible_alternatives": [],
                "inventory_status": "in_stock",
                "confidence": 0.8,
                "uncertainty": 0.1,
            },
        ],
    }
    if overrides:
        for k, v in overrides.items():
            if k == "formula_rows":
                cand["formula_rows"] = v
            else:
                cand[k] = v
    return cand


def run(cand, expected_total=None, out_dir=None, alias_map=None):
    d = str(out_dir) if out_dir is not None else tempfile.mkdtemp(prefix="ingest_test_")
    res = ingest_external_candidate(
        cand,
        expected_total=expected_total,
        output_dir=d,
        stock_resolver=lambda s: STOCK_OK.get(s.lower(), False),
        alias_map=alias_map,
    )
    written = res.write()
    return res, written, d


def test_happy_path_accepted():
    res, written, _ = run(make_candidate(), expected_total=1000.0)
    assert res.accepted is True
    for name in [
        "validated_candidate.json",
        "formula_rows.jsonl",
        "arithmetic_report.json",
        "alias_report.json",
        "inventory_crosswalk.json",
        "carrier_ledger.json",
        "evidence_integrity_report.json",
        "gate_dispatch_input.json",
        "ingestion_receipt.json",
        "deterministic_hash.json",
    ]:
        assert name in written, name


def test_arithmetic_and_carrier(tmp_path):
    res, written, _ = run(make_candidate(), expected_total=1000.0, out_dir=tmp_path)
    arith = json.load(open(written["arithmetic_report.json"], encoding="utf-8"))
    assert arith["total_parts"] == 1000.0
    assert arith["balance"] == "PASS"
    assert res.candidate_hash


def test_deterministic_hash_replay():
    cand = make_candidate()
    h1 = deterministic_hash({**cand, "schema_version": "external_candidate_v1"})
    h2 = deterministic_hash({**cand, "schema_version": "external_candidate_v1"})
    assert h1 == h2
    cand2 = dict(cand)
    cand2["formula_rows"] = [dict(r) for r in cand["formula_rows"]]
    cand2["formula_rows"][0]["parts"] = 301.0
    assert deterministic_hash({**cand2, "schema_version": "external_candidate_v1"}) != h1


def test_reject_bad_totals():
    res, written, _ = run(make_candidate(), expected_total=999.0)
    assert res.accepted is False
    assert any(r.code == "INVALID_FORMULA_TOTALS" for r in res.rejections)
    assert "rejection.json" in written


def test_reject_unresolved_stock():
    cand = make_candidate()
    cand["formula_rows"][0]["exact_supplied_stock"] = "jasmine"
    res, written, _ = run(cand)
    assert res.accepted is False
    codes = {r.code for r in res.rejections}
    assert "UNRESOLVED_EXACT_STOCK" in codes


def test_reject_ambiguous_alias(tmp_path):
    cand = make_candidate()
    for r in cand["formula_rows"]:
        r["canonical_material_name"] = None
        r["raw_material_name"] = "Mystery Material"
        r["exact_supplied_stock"] = "mystery material"
    res, _, _ = run(
        cand,
        expected_total=1000.0,
        out_dir=tmp_path,
        alias_map={"mystery material a": "A", "mystery material b": "B"},
    )
    assert res.accepted is False
    assert any(r.code == "AMBIGUOUS_ALIAS" for r in res.rejections)


def test_reject_invented_active_fraction():
    cand = make_candidate()
    cand["formula_rows"][0]["active_fraction_or_PRODUCT_BASIS"] = 1.5
    res, _, _ = run(cand, expected_total=1000.0)
    assert res.accepted is False
    assert any(r.code == "INVENTED_ACTIVE_FRACTION" for r in res.rejections)


def test_reject_formula_empirical_conflation():
    cand = make_candidate()
    cand["empirical_state"] = cand["formula_state"]
    res, _, _ = run(cand)
    assert res.accepted is False
    assert any(r.code == "FORMULA_EMPIRICAL_CONFLATED" for r in res.rejections)


def test_reject_note_name_to_material():
    cand = make_candidate()
    row = dict(cand["formula_rows"][0])
    row["canonical_material_name"] = "jasmine"
    row["raw_material_name"] = "jasmine"
    row["exact_supplied_stock"] = "jasmine"
    cand["formula_rows"] = cand["formula_rows"] + [row]
    res, _, _ = run(cand, expected_total=1000.0)
    assert res.accepted is False
    assert any(r.code == "NOTE_NAME_TO_MATERIAL" for r in res.rejections)


def test_reject_missing_inventory_snapshot():
    cand = make_candidate()
    cand["inventory_snapshot_id"] = None
    cand["inventory_snapshot_hash"] = None
    res, _, _ = run(cand)
    assert res.accepted is False
    assert any(r.code == "ABSENT_INVENTORY_SNAPSHOT" for r in res.rejections)


def test_reject_missing_source_hash():
    cand = make_candidate()
    cand["source_artifact_hashes"] = []
    res, _, _ = run(cand)
    assert res.accepted is False
    assert any(r.code == "MISSING_SOURCE_ARTIFACT_HASH" for r in res.rejections)


def test_product_basis_preserved(tmp_path):
    cand = make_candidate()
    row = dict(cand["formula_rows"][0])
    row["row_number"] = 4
    row["raw_material_name"] = "Opaque Accord"
    row["canonical_material_name"] = "opaque accord"
    row["exact_supplied_stock"] = "opaque accord"
    row["active_fraction_or_PRODUCT_BASIS"] = PRODUCT_BASIS
    cand["formula_rows"] = cand["formula_rows"] + [row]
    res, written, _ = run(cand, expected_total=1300.0, out_dir=tmp_path)
    assert res.accepted is True
    rows = [json.loads(line) for line in open(written["formula_rows.jsonl"], encoding="utf-8")]
    pb = [r for r in rows if r["product_basis"] is True]
    assert len(pb) == 1 and pb[0]["active_fraction"] is None


def test_schema_required_fields_present():
    cand = make_candidate()
    assert all(f in cand for f in REQUIRED_CANDIDATE_FIELDS)
