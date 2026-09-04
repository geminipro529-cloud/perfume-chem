from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = (
    ROOT
    / "data"
    / "governance"
    / "inventory_v5_experiment_readiness_closure_evidence_audit_20260812.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _semantic_sha256(payload: dict[str, object]) -> str:
    canonical = dict(payload)
    canonical.pop("semantic_self_sha256", None)
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_evidence_audit_is_hash_bound_and_nonpromoting() -> None:
    audit = _load(AUDIT_PATH)

    assert audit["schema_version"] == ("perfume_chem_inventory_v5_closure_evidence_audit_v1")
    assert audit["decision"] == (
        "OPEN_PARTIAL_EVIDENCE_EXACT_STOCK_AND_PREPARATION_LINEAGE_NOT_CLOSED"
    )
    assert audit["semantic_self_sha256"] == _semantic_sha256(audit)
    for parent in audit["parents"]:
        path = ROOT / parent["path"]
        assert path.is_file()
        assert path.stat().st_size == parent["size_bytes"]
        assert _sha256(path) == parent["sha256"]
    assert all(value is False for value in audit["authority"].values())
    assert all(value is False for value in audit["claim_boundary"].values())


def test_clr_001_preserves_catalog_snapshot_and_identity_boundaries() -> None:
    audit = _load(AUDIT_PATH)
    record = {item["action_id"]: item for item in audit["audits"]}["CLR-001"]
    inventory = (ROOT / "inventory.txt").read_text(encoding="utf-8")
    snapshot = _load(ROOT / "data/governance/inventory_v5_current_stock_snapshot.json")
    crosswalk = _load(ROOT / "data/governance/inventory_v5_alias_crosswalk_20260811.json")
    catalog = _load(ROOT / "data/materials/_sources/perfumersworld_stock.parsed.json")

    assert "2-Acetyl Pyrazine (1% in DPG)" in inventory
    source_row = next(row for row in snapshot["records"] if row["_source_row"] == 6)
    assert source_row["Canonical material"] == "2-Acetyl Pyrazine"
    assert source_row["Actual stock(s)"] == (
        "2-Acetyl Pyrazine neat/as supplied; 1% working stock (carrier not stated)"
    )
    contract = next(item for item in crosswalk["contracts"] if item["contract_id"] == "IDCL-001")
    assert contract["expected_route"] == "V5_LABEL_RECHECK_HOLD"
    product = next(item for item in catalog if item["sku"] == "5EN13769")
    assert product["raw_name"] == "2-Acetyl Pyrazine 1% in DPG"
    assert product["dilution_pct"] == 1.0
    assert product["dilution_solvent"] == "DPG"

    assert record["closure_state"] == "OPEN_PARTIAL_EVIDENCE"
    assert record["supplier_catalog_proves_owned_stock"] is False
    assert record["closure_receipt_created"] is False
    assert record["execution_authorized"] is False
    assert len(record["missing_witnesses"]) == 5


def test_clr_002_keeps_instruction_separate_from_executed_preparation() -> None:
    audit = _load(AUDIT_PATH)
    record = {item["action_id"]: item for item in audit["audits"]}["CLR-002"]
    inventory = (ROOT / "inventory.txt").read_text(encoding="utf-8")
    snapshot = _load(ROOT / "data/governance/inventory_v5_current_stock_snapshot.json")
    formula = (ROOT / "formulas/demachy_redux/DHC_A_BottleA_Lemon_Extension.md").read_text(
        encoding="utf-8"
    )

    assert "Lemonile (1% in DPG)" in inventory
    source_row = next(row for row in snapshot["records"] if row["_source_row"] == 258)
    assert source_row["Actual stock(s)"] == "Lemonile neat/as supplied"
    assert "0.1 g Lemonile + 9.9 g DPG in a vial. Label." in formula

    assert record["closure_state"] == "OPEN_PARTIAL_EVIDENCE"
    assert record["compounding_instruction_proves_execution"] is False
    assert record["inventory_comment_proves_preparation"] is False
    assert record["closure_receipt_created"] is False
    assert record["execution_authorized"] is False
    assert len(record["missing_witnesses"]) == 4


def test_delegation_and_bounded_search_remain_advisory_only() -> None:
    audit = _load(AUDIT_PATH)

    assert audit["bounded_search"]["global_absence_claimed"] is False
    assert audit["bounded_search"]["exact_stock_or_preparation_binding_found_for_clr_001"] is False
    assert audit["bounded_search"]["exact_stock_or_preparation_binding_found_for_clr_002"] is False
    assert audit["delegation_evidence"]["route"] == ("DEEPLUNA_CHAT_CHEAPLUNA_CHAT_DIRECT_PRO_ONLY")
    assert audit["delegation_evidence"]["fallback_used"] is False
    assert audit["delegation_evidence"]["fast_used"] is False
    assert audit["delegation_evidence"]["scientific_acceptance"] == "SOL_LOCAL_ONLY"
    assert {job["sol_disposition"] for job in audit["delegation_evidence"]["jobs"]} == {
        "ACCEPT_OPEN_PARTIAL_EVIDENCE"
    }
