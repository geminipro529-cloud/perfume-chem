from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from engine.physics.calibration_program import build_c5_program

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = ROOT / "docs/verification/c5/inventory_v5_rebase_assessment.json"
SNAPSHOT_PATH = ROOT / "data/governance/inventory_v5_current_stock_snapshot.json"
WORKBOOK_PATH = ROOT / "incoming_review/Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_c5_v5_rebase_receipt_binds_exact_parent_and_candidate_bytes() -> None:
    assessment = _load(ASSESSMENT_PATH)
    parent = assessment["parent_program"]
    candidate = assessment["candidate_inventory"]
    program = build_c5_program()

    assert parent == {
        "program_id": program.program_id,
        "content_sha256": program.content_sha256,
        "inventory_sha256": program.inventory_sha256,
        "material_count": len(program.materials),
        "matrix_count": len(program.matrices),
        "preserved_unchanged": True,
    }
    assert candidate["snapshot_sha256"] == _sha256(SNAPSHOT_PATH)
    assert candidate["workbook_sha256"] == _sha256(WORKBOOK_PATH)

    snapshot = _load(SNAPSHOT_PATH)
    assert candidate["authority"] == snapshot["authority"]
    assert candidate["record_count"] == snapshot["row_count"]
    assert candidate["workbook_sha256"] == snapshot["source"]["sha256"]
    assert candidate["sheet"] == snapshot["source"]["sheet"]
    assert candidate["range"] == snapshot["source"]["range"]

    canonical = dict(assessment)
    claimed_hash = canonical.pop("content_sha256")
    encoded = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    assert claimed_hash == hashlib.sha256(encoded).hexdigest()


def test_c5_v5_material_diff_is_complete_and_source_exact() -> None:
    assessment = _load(ASSESSMENT_PATH)
    snapshot = _load(SNAPSHOT_PATH)
    program = build_c5_program()
    parent_by_name = {entry.inventory_name: entry for entry in program.materials}
    source_by_row = {record["_source_row"]: record for record in snapshot["records"]}
    diffs = assessment["material_diffs"]

    assert len(diffs) == 19
    assert {item["parent_inventory_name"] for item in diffs} == set(parent_by_name)
    assert assessment["classification_counts"] == dict(
        Counter(item["classification"] for item in diffs)
    )

    for item in diffs:
        parent = parent_by_name[item["parent_inventory_name"]]
        assert item["parent_stock_fraction"] == parent.stock_fraction
        assert item["parent_stock_fraction_basis"] == parent.stock_fraction_basis
        assert item["parent_carrier"] == parent.carrier

        source_rows = item["v5_source_rows"]
        if source_rows:
            assert len(source_rows) == 1
            source = source_by_row[source_rows[0]]
            assert item["v5_canonical_material"] == source["Canonical material"]
            assert item["v5_actual_stock"] == source["Actual stock(s)"]
            assert item["v5_status"] == source["Status"]
        else:
            assert item["classification"] == "NOT_V5_QUALIFIED"
            assert item["v5_canonical_material"] is None
            assert item["v5_actual_stock"] is None
            assert item["v5_status"] is None

    missing = {
        item["parent_inventory_name"]
        for item in diffs
        if item["classification"] == "NOT_V5_QUALIFIED"
    }
    changed = {
        item["parent_inventory_name"]
        for item in diffs
        if item["classification"] == "STOCK_FORM_CHANGED"
    }
    assert missing == {"Gamma Decalactone", "Myristic Acid Powder"}
    assert changed == {"Eugenol", "Raspberry Ketone"}


def test_c5_v5_rebase_stays_answerless_and_nonpromoting() -> None:
    assessment = _load(ASSESSMENT_PATH)
    program = build_c5_program()

    assert assessment["decision"] == "HOLD_REDESIGN_REQUIRED"
    assert assessment["authority"] == {
        "program_v2_created": False,
        "inventory_mutation_authority": False,
        "formula_authority": False,
        "physical_execution_authority": False,
        "empirical_calibration_authority": False,
        "headspace_authority": False,
        "oav_authority": False,
        "sensory_authority": False,
        "safety_authority": False,
        "release_authority": False,
    }
    assert {item["matrix_id"] for item in assessment["matrix_assessments"]} == {
        entry.matrix_id for entry in program.matrices
    }
    assert all(
        item["classification"].startswith("HOLD_") for item in assessment["matrix_assessments"]
    )
    assert all(
        not value
        for key, value in assessment["authority"].items()
        if key.endswith("_authority") or key == "program_v2_created"
    )
