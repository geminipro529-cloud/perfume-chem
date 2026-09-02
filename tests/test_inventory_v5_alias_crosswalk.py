from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.inventory_parser import (
    CURRENT_INVENTORY_ALIAS_CROSSWALK_PATH,
    CURRENT_INVENTORY_ALIAS_CROSSWALK_SHA256,
    InventoryAuthorityError,
    load_current_inventory_alias_crosswalk,
    parse_current_inventory,
)
from engine.name_utils import normalize_name
from engine.pipeline.preflight import (
    _dilution_consistency_check,
    build_formula_dose_receipt,
)

EXPECTED_ROWS = {
    "IDCL-001": ("2-Acetyl Pyrazine 1%", "2-Acetyl Pyrazine", 6),
    "IDCL-002": ("AAG 10%", "Allyl Amyl Glycolate (AAG)", 7),
    "IDCL-003": ("Allyl Amyl Glycolate 10%", "Allyl Amyl Glycolate (AAG)", 7),
    "IDCL-004": ("Aurantiol", "Aurantiol 10% in DPG", 254),
    "IDCL-005": ("Bergamot FCF EO", "Bergamot FCF Oil Sicilian", 42),
    "IDCL-006": ("Blood Orange EO", "Blood Orange Oil Sicilian", 50),
    "IDCL-007": ("Cedrat FCF EO", "Cedrat FCF Oil Sicilian", 66),
    "IDCL-008": ("Cis Jasmone", "cis-Jasmone", 71),
    "IDCL-009": ("Cocoa CO2 7.7%", "Cocoa CO2 Extract 7.7%", 79),
    "IDCL-010": (
        "Coffee Absolute 10%",
        "Coffee Absolute Grasse 10% in DPG",
        80,
    ),
    "IDCL-011": ("Ethyl Maltol 10%", "Ethyl Maltol 1% + 10%", 266),
    "IDCL-012": ("Grapefruit FCF EO", "Grapefruit FCF Oil Sicilian", 123),
    "IDCL-013": ("Himalayan Cedarwood EO", "Cedarwood Himalayan EO", 63),
    "IDCL-014": ("Lemon FCF EO", "Lemon FCF Oil Sicilian", 158),
    "IDCL-015": ("Opoponax 50%", "Opoponax Resinoid 50%", 189),
    "IDCL-016": ("Peru Balsam 50%", "Peru Balsam 10%", 201),
    "IDCL-017": ("Rose Essential Oil", "Rose EO", 214),
    "IDCL-018": ("Ylang Complete EO", "Ylang-Ylang EO", 251),
}


def _formula(material: str, fraction: float, carrier: str = "") -> dict[str, object]:
    return {
        "name": "Alias crosswalk probe",
        "ingredients_ul": {material: 10.0},
        "dilutions": {material: fraction},
        "stock_specs": {
            material: {
                "fraction": fraction,
                "fraction_basis": "unspecified",
                "carrier": carrier,
                "declared": True,
            }
        },
    }


def _write_crosswalk(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "crosswalk.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_crosswalk_is_exactly_hash_row_destination_and_witness_bound() -> None:
    crosswalk = load_current_inventory_alias_crosswalk()

    assert crosswalk.crosswalk_sha256 == CURRENT_INVENTORY_ALIAS_CROSSWALK_SHA256
    assert len(crosswalk.contracts) == 18
    assert {
        contract.contract_id: (
            contract.source,
            contract.destination,
            contract.current_master_row,
        )
        for contract in crosswalk.contracts
    } == EXPECTED_ROWS
    resolved = crosswalk.resolve("  bergamot   fcf eo ")
    assert resolved is not None
    assert resolved.contract_id == "IDCL-005"
    assert crosswalk.resolve("Bergamot FCF") is None


def test_crosswalk_byte_drift_aborts_before_candidate_lookup(tmp_path: Path) -> None:
    path = tmp_path / "crosswalk.json"
    path.write_bytes(CURRENT_INVENTORY_ALIAS_CROSSWALK_PATH.read_bytes() + b"\n")

    with pytest.raises(InventoryAuthorityError, match="crosswalk hash drift"):
        load_current_inventory_alias_crosswalk(path)


@pytest.mark.parametrize(
    "mutation",
    ["workbook", "snapshot", "row", "destination", "witness", "duplicate", "authority"],
)
def test_crosswalk_semantic_drift_aborts(
    tmp_path: Path,
    mutation: str,
) -> None:
    payload = json.loads(CURRENT_INVENTORY_ALIAS_CROSSWALK_PATH.read_text("utf-8"))
    if mutation == "workbook":
        payload["source"]["inventory_workbook_sha256"] = "0" * 64
    elif mutation == "snapshot":
        payload["source"]["inventory_snapshot_sha256"] = "0" * 64
    elif mutation == "row":
        payload["contracts"][0]["current_master_row"] = 7
    elif mutation == "destination":
        payload["contracts"][0]["destination"] = "Allyl Amyl Glycolate (AAG)"
    elif mutation == "witness":
        payload["contracts"][0]["required_witnesses"][0] = "invented witness"
    elif mutation == "duplicate":
        payload["contracts"][1]["source"] = payload["contracts"][0]["source"]
    else:
        payload["authority"]["inventory"] = True

    with pytest.raises(InventoryAuthorityError):
        load_current_inventory_alias_crosswalk(
            _write_crosswalk(tmp_path, payload),
            require_pinned_crosswalk=False,
        )


@pytest.mark.parametrize(
    ("material", "fraction", "carrier", "contract_id", "source_row", "stock_prefix"),
    [
        ("Bergamot FCF EO", 1.0, "", "IDCL-005", 42, "inventory:v5:"),
        ("Coffee Absolute 10%", 0.10, "dpg", "IDCL-010", 80, "inventory:v5:"),
        ("Grapefruit FCF EO", 1.0, "", "IDCL-012", 123, "inventory:v5:"),
        ("Himalayan Cedarwood EO", 1.0, "", "IDCL-013", 63, "inventory:v5:"),
        ("Lemon FCF EO", 1.0, "", "IDCL-014", 158, "inventory:v5:"),
        ("Opoponax 50%", 0.50, "dep", "IDCL-015", 189, "inventory:user-20260828:"),
        ("Rose Essential Oil", 1.0, "", "IDCL-017", 214, "inventory:user-20260828:"),
    ],
)
def test_execution_ready_aliases_bind_only_to_exact_native_stock(
    material: str,
    fraction: float,
    carrier: str,
    contract_id: str,
    source_row: int,
    stock_prefix: str,
) -> None:
    check = _dilution_consistency_check(_formula(material, fraction, carrier))

    assert check.status == "PASS"
    matched = check.data["matched_stocks"]
    assert len(matched) == 1
    assert matched[0]["material"] == material
    assert matched[0]["identity_crosswalk_contract_id"] == contract_id
    assert matched[0]["source_rows"] == [source_row]
    assert matched[0]["stock_id"].startswith(stock_prefix)


@pytest.mark.parametrize(
    ("material", "fraction", "reason", "contract_id", "source_row"),
    [
        ("2-Acetyl Pyrazine 1%", 0.01, "inventory_stock_metadata_incomplete", "IDCL-001", 6),
        ("AAG 10%", 0.10, "preparation_required", "IDCL-002", 7),
        ("Allyl Amyl Glycolate 10%", 0.10, "preparation_required", "IDCL-003", 7),
        ("Blood Orange EO", 1.0, "inventory_stock_metadata_incomplete", "IDCL-006", 50),
        ("Cedrat FCF EO", 1.0, "inventory_gap", "IDCL-007", 66),
        ("Cocoa CO2 7.7%", 0.077, "inventory_stock_metadata_incomplete", "IDCL-009", 79),
        ("Ethyl Maltol 10%", 0.10, "inventory_stock_metadata_incomplete", "IDCL-011", 266),
        ("Peru Balsam 50%", 0.50, "inventory_stock_metadata_incomplete", "IDCL-016", 201),
        ("Ylang Complete EO", 1.0, "inventory_stock_unavailable", "IDCL-018", 251),
    ],
)
def test_aliases_preserve_native_hold_preparation_gap_and_abstention(
    material: str,
    fraction: float,
    reason: str,
    contract_id: str,
    source_row: int,
) -> None:
    check = _dilution_consistency_check(_formula(material, fraction))

    assert check.status == "FAIL"
    issue = check.data["issues"][0]
    assert issue["material"] == material
    assert issue["reason"] == reason
    assert issue["identity_crosswalk_contract_id"] == contract_id
    assert source_row in issue.get("source_rows", issue.get("requirement_source_rows", []))


def test_exact_fraction_and_unknown_label_remain_fail_closed() -> None:
    mismatch = _dilution_consistency_check(_formula("Bergamot FCF EO", 0.10))
    unknown = _dilution_consistency_check(_formula("Invented Bergamot Alias", 1.0))

    assert mismatch.status == "FAIL"
    assert mismatch.data["issues"][0]["reason"] == "stock_fraction_mismatch"
    assert unknown.status == "FAIL"
    assert unknown.data["issues"][0]["reason"] == "not_in_inventory"
    assert "identity_crosswalk_contract_id" not in unknown.data["issues"][0]


@pytest.mark.parametrize(
    ("material", "fraction", "carrier", "source_row"),
    [
        ("Aurantiol", 0.10, "dpg", 254),
        ("Cis Jasmone", 1.0, "", 71),
    ],
)
def test_native_noop_aliases_preserve_stock_ids(
    material: str,
    fraction: float,
    carrier: str,
    source_row: int,
) -> None:
    native = next(
        record
        for record in parse_current_inventory(unique=False, include_unavailable=True)
        if source_row in record.source_rows
        and record.status == "owned"
        and abs(record.dilution - fraction) <= 1e-12
    )
    check = _dilution_consistency_check(_formula(material, fraction, carrier))

    assert check.status == "PASS"
    assert check.data["matched_stocks"][0]["stock_id"] == native.stock_id


def test_dose_receipt_preserves_formula_label_and_binds_canonical_stock() -> None:
    formula = _formula("Bergamot FCF EO", 1.0)
    contract = _dilution_consistency_check(formula)
    receipt = build_formula_dose_receipt(formula, contract)

    assert receipt.status == "BOUND"
    assert receipt.lines[0].material_name == "Bergamot FCF EO"
    assert receipt.lines[0].stock_id == "inventory:v5:e21b17adeb4b1fe1f12d"
    assert receipt.lines[0].source_rows == (42,)
    assert normalize_name(contract.data["matched_stocks"][0]["inventory_identity"]) == (
        normalize_name("Bergamot FCF Oil Sicilian")
    )
