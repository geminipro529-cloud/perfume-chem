import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r5_design_comparator_20260923.json"
)
WORKBOOK = Path(
    r"C:\Users\ASUS\Downloads\Lavande_Ambre_Profond_R5_30mL_Mixing_Workbook.xlsx"
)


def _load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_r5_manifest_row_hash_and_exact_totals_are_frozen():
    manifest = _load()
    rows = manifest["rows"]
    canonical = json.dumps(
        rows,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest() == (
        manifest["canonical_formula_rows_sha256"]
    )
    assert len(rows) == 63
    assert len({row["material"] for row in rows}) == 63

    liquids = [row for row in rows if row["unit"] == "µL"]
    solids = [row for row in rows if row["unit"] == "mg"]
    assert len(liquids) == 62
    assert len(solids) == 1
    assert sum(Decimal(str(row["dose"])) for row in liquids) == Decimal(
        "5600"
    )
    assert solids[0]["material"] == "Ambrox Super"
    assert Decimal(str(solids[0]["dose"])) == Decimal("300")
    assert min(Decimal(str(row["dose"])) for row in liquids) == Decimal("5")

    by_basket = {}
    for row in liquids:
        by_basket.setdefault(row["basket"], Decimal("0"))
        by_basket[row["basket"]] += Decimal(str(row["dose"]))
    assert by_basket == {
        "B1": Decimal("890"),
        "B2": Decimal("700"),
        "B3": Decimal("655"),
        "B4": Decimal("1895"),
        "B5": Decimal("1010"),
        "B6": Decimal("450"),
    }


def test_r5_manifest_preserves_design_only_authority_and_holds():
    manifest = _load()
    assert manifest["design_only"] is True
    assert manifest["parent_reference"]["verification_state"] == (
        "PARENT_BYTES_NOT_AVAILABLE"
    )
    assert manifest["checkpoint_2_state"] == {
        "design_comparator_state": "ADMITTED_DESIGN_ONLY",
        "physical_build_state": "HOLD_STOCK_BINDING",
        "parent_equivalence_state": "HOLD_PARENT_BYTES_MISSING",
        "intensity_state": "HOLD_EXACT_CURVE_APPLICABILITY",
        "shortlist_state": "HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED",
        "pleasantness_state": "NOT_ESTABLISHED",
        "physical_liking_state": "NOT_TESTED",
        "formula_action": "NO_CHANGE",
        "formula_modified": False,
        "inventory_modified": False,
    }
    assert all(value is False for value in manifest["authority"].values())
    assert manifest["lavender_design_block"]["ratio"] == "70:30"


def test_local_r5_workbook_bytes_match_manifest_when_available():
    if not WORKBOOK.exists():
        pytest.skip("External R5 workbook is intentionally not committed")
    manifest = _load()
    assert hashlib.sha256(WORKBOOK.read_bytes()).hexdigest() == (
        manifest["source_artifact"]["sha256"]
    )
