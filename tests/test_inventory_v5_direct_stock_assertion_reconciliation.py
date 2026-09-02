from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    ROOT
    / "data"
    / "governance"
    / "inventory_v5_direct_stock_assertion_reconciliation_20260812.json"
)
HUMAN_PATH = (
    ROOT
    / "docs"
    / "research"
    / "PERFUME_CHEM_INVENTORY_V5_DIRECT_STOCK_ASSERTION_RECONCILIATION_2026-08-12.md"
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


def test_reconciliation_is_hash_bound_additive_and_nonpromoting() -> None:
    report = _load(REPORT_PATH)

    assert report["schema_version"] == (
        "perfume_chem_inventory_v5_direct_stock_assertion_reconciliation_v1"
    )
    assert report["decision"] == (
        "DATA_AMBER_DPG_ASSERTIONS_RECOVERED_EXACT_STOCK_AND_PREPARATION_RECEIPTS_RED"
    )
    assert report["semantic_self_sha256"] == _semantic_sha256(report)
    assert report["mutation_policy"] == "ADDITIVE_REPORT_ONLY_NO_PARENT_MUTATION"
    assert report["authority"] == {
        "formula": False,
        "inventory_mutation": False,
        "stock_identity": False,
        "preparation": False,
        "physical_experiment": False,
        "sensory_claim": False,
        "scientific_claim": False,
        "safety": False,
        "procurement": False,
        "collection": False,
        "installation": False,
        "release": False,
    }

    for parent in report["parents"]:
        path = ROOT / parent["path"]
        assert path.is_file()
        assert path.stat().st_size == parent["size_bytes"]
        assert _sha256(path) == parent["sha256"]


def test_reconciliation_reconstructs_exact_user_assertions_and_parent_states() -> None:
    report = _load(REPORT_PATH)
    inventory_lines = (ROOT / "inventory.txt").read_text(encoding="utf-8").splitlines()
    snapshot = _load(ROOT / "data/governance/inventory_v5_current_stock_snapshot.json")
    crosswalk = _load(ROOT / "data/governance/inventory_v5_alias_crosswalk_20260811.json")
    closure = _load(
        ROOT / "data/governance/inventory_v5_experiment_readiness_closure_queue_20260812.json"
    )

    snapshot_by_row = {int(row["_source_row"]): row for row in snapshot["records"]}
    crosswalk_by_id = {row["contract_id"]: row for row in crosswalk["contracts"]}
    closure_by_id = {row["action_id"]: row for row in closure["closure_queue"]}

    units = {row["material_id"]: row for row in report["evidence_units"]}
    pyrazine = units["2_acetyl_pyrazine_1pct"]
    lemonile = units["lemonile_1pct"]

    assert inventory_lines[210] == pyrazine["inventory_assertion"]["exact_text"]
    assert inventory_lines[34] == lemonile["inventory_assertion"]["exact_text"]
    assert pyrazine["inventory_assertion"]["line_number"] == 211
    assert lemonile["inventory_assertion"]["line_number"] == 35

    assert snapshot_by_row[6]["Actual stock(s)"] == pyrazine["snapshot_state"]["actual_stocks"]
    assert snapshot_by_row[258]["Actual stock(s)"] == lemonile["snapshot_state"]["actual_stocks"]
    assert (
        crosswalk_by_id["IDCL-001"]["native_disposition"]
        == (pyrazine["crosswalk_state"]["native_disposition"])
    )
    assert closure_by_id["CLR-001"]["execution_authorized"] is False
    assert closure_by_id["CLR-002"]["execution_authorized"] is False


def test_reconciliation_quantifies_positive_and_negative_truth_without_closure() -> None:
    report = _load(REPORT_PATH)
    units = {row["material_id"]: row for row in report["evidence_units"]}

    assert report["census"] == {
        "materials_reviewed": 2,
        "user_asserted_dpg_stocks": 2,
        "snapshot_states_requiring_reconciliation": 2,
        "carrier_assertions_recovered": 2,
        "fully_closed_queue_actions": 0,
        "exact_stock_refs": 0,
        "label_or_lot_witnesses": 0,
        "complete_preparation_receipts": 0,
        "execution_ready_stocks": 0,
    }
    assert {row["queue_state"] for row in units.values()} == {"OPEN_PARTIAL_EVIDENCE"}
    assert {row["carrier_assertion"] for row in units.values()} == {"DPG"}
    assert all(row["assertion_authority"] == "USER_ASSERTED_ONLY" for row in units.values())
    assert all(row["reconciliation_effect"] == "NARROWS_PROVENANCE_ONLY" for row in units.values())

    assert units["lemonile_1pct"]["dilution_date_assertion"] == "2026-05-25"
    assert units["lemonile_1pct"]["parent_relation_assertion"] == "FROM_NEAT_STOCK"
    assert units["2_acetyl_pyrazine_1pct"]["dilution_date_assertion"] is None
    assert units["2_acetyl_pyrazine_1pct"]["parent_relation_assertion"] is None

    required_false = {
        "exact_stock_ref_present",
        "bottle_label_or_lot_witness_present",
        "concentration_basis_present",
        "parent_stock_id_present",
        "preparation_quantities_present",
        "complete_preparation_receipt_present",
        "physical_execution_ready",
    }
    for unit in units.values():
        assert required_false <= set(unit["remaining_gates"])
        assert all(unit["remaining_gates"][key] is False for key in required_false)


def test_reconciliation_preserves_literature_and_human_view_boundaries() -> None:
    report = _load(REPORT_PATH)
    references = {row["source_id"]: row for row in report["literature_context"]}

    assert references["PMID_36571813"]["role"] == ("FUTURE_CARRIER_HEADSPACE_CALIBRATION_CONTEXT")
    assert references["PMID_36571813"]["stock_identity_authority"] is False
    assert references["PMID_30949040"]["role"] == "EXCLUDED_AS_DIRECT_DPG_EVIDENCE"
    assert references["PMID_30949040"]["stock_identity_authority"] is False
    assert references["PMID_18534998"]["role"] == "FUTURE_BINARY_MIXTURE_METHOD_CONTEXT"
    assert references["PMID_34041322"]["role"] == "FUTURE_REPEATABILITY_CONTEXT"
    assert references["ISO_13301_2018"]["role"] == "FUTURE_THRESHOLD_METHOD_CONTEXT"
    assert all(row["stock_identity_authority"] is False for row in references.values())

    boundary = report["claim_boundary"]
    assert boundary["inventory_comment_is_preparation_receipt"] is False
    assert boundary["supplier_catalogue_proves_owned_bottle"] is False
    assert boundary["propylene_glycol_evidence_applies_to_dipropylene_glycol"] is False
    assert boundary["queue_action_closed"] is False
    assert boundary["physical_experiment_authorized"] is False

    human = HUMAN_PATH.read_text(encoding="utf-8")
    assert report["decision"] in human
    assert "user assertion, not a preparation receipt" in human
    assert "0 of 2 closure actions are complete" in human
    assert "No physical experiment is authorized" in human
