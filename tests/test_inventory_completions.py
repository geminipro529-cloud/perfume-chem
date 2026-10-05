import json

import pytest

from engine.inventory_completions import (
    InventoryCompletionConflictError,
    effective_design_ready,
    inventory_completion_requirements,
    load_inventory_completion_events,
    record_inventory_completion,
)
from engine.inventory_parser import materialize_current_inventory


def _stock(materialized, identity: str):
    return next(stock for stock in materialized.stocks if stock.identity_name == identity)


def test_completion_makes_missing_stock_design_ready_without_execution_authority(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "inventory-completions.jsonl"
    monkeypatch.setenv("PERFUME_INVENTORY_COMPLETION_PATH", str(path))
    baseline = materialize_current_inventory()
    stock = _stock(baseline, "2-Acetyl Pyrazine")

    receipt, completed = record_inventory_completion(
        stock_id=stock.stock_id,
        expected_effective_inventory_sha256=baseline.effective_inventory_sha256,
        idempotency_key="complete-2-acetyl-pyrazine",
        fraction_decimal="0.01",
        fraction_basis="mass_fraction",
        carrier="DPG",
        physical_form="solution",
        possession_confirmed=True,
        homogeneity="HOMOGENEOUS",
        final_fraction_known=True,
        source_kind="USER_LABEL_OR_RECIPE",
        user_note="Personal stock label checked.",
    )

    updated = _stock(completed, "2-Acetyl Pyrazine")
    assert receipt["release_authority"] is False
    assert receipt["compounding_authority"] is False
    assert updated.fraction_basis == "mass_fraction"
    assert updated.carrier == "dpg"
    assert updated.physical_form == "solution"
    assert effective_design_ready(updated) is True
    assert updated.execution_ready is False
    assert inventory_completion_requirements(updated) == ()
    assert completed.completion_sha256
    assert completed.effective_inventory_sha256 != baseline.effective_inventory_sha256


def test_completion_is_idempotent_and_rejects_key_reuse(tmp_path, monkeypatch) -> None:
    path = tmp_path / "inventory-completions.jsonl"
    monkeypatch.setenv("PERFUME_INVENTORY_COMPLETION_PATH", str(path))
    baseline = materialize_current_inventory()
    stock = _stock(baseline, "Cedrat FCF Sicilian")
    command = {
        "stock_id": stock.stock_id,
        "expected_effective_inventory_sha256": baseline.effective_inventory_sha256,
        "idempotency_key": "complete-cedrat",
        "fraction_decimal": "1",
        "fraction_basis": "neat",
        "carrier": "",
        "physical_form": "as_supplied",
        "possession_confirmed": True,
        "homogeneity": "NOT_APPLICABLE",
        "final_fraction_known": True,
        "source_kind": "PERSONAL_CONFIRMATION",
        "user_note": "",
    }

    first, _completed = record_inventory_completion(**command)
    replay, _replayed = record_inventory_completion(**command)
    assert replay == first
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1

    with pytest.raises(InventoryCompletionConflictError):
        record_inventory_completion(**{**command, "physical_form": "oil"})


def test_tincture_starting_charge_remains_withheld_until_final_fraction_is_known(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "inventory-completions.jsonl"
    monkeypatch.setenv("PERFUME_INVENTORY_COMPLETION_PATH", str(path))
    baseline = materialize_current_inventory()
    stock = _stock(baseline, "Kenyan Myrrh Ethanol Tincture")

    _receipt, incomplete = record_inventory_completion(
        stock_id=stock.stock_id,
        expected_effective_inventory_sha256=baseline.effective_inventory_sha256,
        idempotency_key="myrrh-starting-recipe",
        fraction_decimal="0.2",
        fraction_basis="mass_fraction",
        carrier="ethanol",
        physical_form="solution",
        possession_confirmed=True,
        homogeneity="HOMOGENEOUS",
        final_fraction_known=False,
        source_kind="USER_LABEL_OR_RECIPE",
        user_note="Starting recipe only.",
    )
    unresolved = _stock(incomplete, "Kenyan Myrrh Ethanol Tincture")
    assert effective_design_ready(unresolved) is False
    assert "final_usable_fraction_confirmation" in inventory_completion_requirements(
        unresolved
    )

    _receipt, complete = record_inventory_completion(
        stock_id=stock.stock_id,
        expected_effective_inventory_sha256=incomplete.effective_inventory_sha256,
        idempotency_key="myrrh-final-measurement",
        fraction_decimal="0.2",
        fraction_basis="mass_fraction",
        carrier="ethanol",
        physical_form="solution",
        possession_confirmed=True,
        homogeneity="HOMOGENEOUS",
        final_fraction_known=True,
        source_kind="USER_MEASUREMENT",
        user_note="Final usable concentration confirmed.",
    )
    resolved = _stock(complete, "Kenyan Myrrh Ethanol Tincture")
    assert effective_design_ready(resolved) is True
    assert resolved.execution_ready is False


def test_completion_log_hash_chain_detects_tampering(tmp_path) -> None:
    path = tmp_path / "inventory-completions.jsonl"
    path.write_text(
        json.dumps({"schema_version": "wrong"}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_inventory_completion_events(path)
