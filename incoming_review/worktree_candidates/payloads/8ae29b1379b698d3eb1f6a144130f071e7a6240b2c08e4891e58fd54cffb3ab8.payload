from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services import inventory_v5_authority_delta as delta


def test_inventory_v5_delta_chain_is_six_records_and_nonpromoting() -> None:
    payload = delta._load_delta()
    supplement = delta._load_supplement(payload)
    records = delta._all_delta_records()

    assert len(payload["records"]) == 5
    assert len(supplement["records"]) == 1
    assert len(records) == 6
    assert payload["clearance_receipts"] == []
    assert supplement["clearance_receipts"] == []
    assert payload["operational_effect"] == "FAIL_CLOSED_BLOCK_ONLY"
    assert all(value is False for value in payload["authority"].values())
    assert all(value is False for value in supplement["authority"].values())
    polysantol = delta.inventory_v5_execution_hold_for_material("Polysantol")
    assert polysantol is not None
    assert polysantol["state"] == "OUT_OF_STOCK_REPLAN_REQUIRED"
    assert polysantol["formula_count_in_parent"] == 84
    assert len(polysantol["affected_target_ids"]) == 84


@pytest.mark.parametrize(
    "material_name,state",
    [
        ("Phenyl Ethyl Dimethyl Carbinyl Acetate", "LABEL_VERIFY"),
        ("Oakmoss Absolute IFRA 10%", "PRODUCT_BASIS_UNRESOLVED"),
        ("Ambrettolide 10% in DPG", "PHYSICAL_RECEIPT_PENDING"),
        (
            "Orris Liquid (30%)",
            "EXACT_STOCK_AND_PREPARATION_RECEIPT_REQUIRED",
        ),
    ],
)
def test_inventory_v5_delta_holds_unverified_physical_bases(
    material_name: str,
    state: str,
) -> None:
    record = delta.inventory_v5_execution_hold_for_material(material_name)
    assert record is not None
    assert record["state"] == state


def test_dbca_spelling_delta_does_not_invent_a_stock_hold() -> None:
    record = delta.inventory_v5_delta_record_for_material(
        "Dimethyl Benzyl Carbonyl Acetate"
    )

    assert record is not None
    assert record["canonical_name"] == "Dimethyl Benzyl Carbinyl Acetate"
    assert record["cas_rn"] == "151-05-3"
    assert record["state"] == "PENDING_NEXT_SOURCE_REVISION"
    assert delta.inventory_v5_execution_hold_for_material(
        "Dimethyl Benzyl Carbinyl Acetate"
    ) is None


def test_inventory_v5_delta_tamper_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = delta._load_delta()
    payload["records"][0]["state"] = "HAVE"
    tampered = tmp_path / "delta.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(delta, "_DELTA_PATH", tampered)

    with pytest.raises(delta.InventoryV5AuthorityDeltaError) as error:
        delta.inventory_v5_execution_hold_for_material("Polysantol")

    assert error.value.code == "INVENTORY_V5_AUTHORITY_DELTA_INVALID"


def test_orris_liquid_supplement_tamper_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = delta._load_supplement(delta._load_delta())
    payload["records"][0]["latest_formula_workbook"]["admission_authorized"] = True
    tampered = tmp_path / "supplement.json"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(delta, "_SUPPLEMENT_PATH", tampered)

    with pytest.raises(delta.InventoryV5AuthorityDeltaError) as error:
        delta.inventory_v5_execution_hold_for_material("Orris Liquid")

    assert error.value.code == "INVENTORY_V5_AUTHORITY_DELTA_INVALID"
