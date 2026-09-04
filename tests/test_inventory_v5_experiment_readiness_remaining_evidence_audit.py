from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = (
    ROOT
    / "data"
    / "governance"
    / "inventory_v5_experiment_readiness_remaining_evidence_audit_20260812.json"
)


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def test_remaining_audit_is_hash_bound_nonpromoting_and_semantically_exact() -> None:
    audit = _load(AUDIT_PATH)

    assert audit["schema_version"] == (
        "perfume_chem_inventory_v5_remaining_closure_evidence_audit_v1"
    )
    assert audit["decision"] == (
        "DATA_AMBER_REMAINING_CLOSURES_CLASSIFIED_NONE_READY_PHYSICAL_AND_REBASE_GATES_PRESERVED"
    )
    assert audit["semantic_self_sha256"] == _semantic_sha256(audit)
    for parent in audit["parents"]:
        path = ROOT / parent["path"]
        assert path.is_file()
        assert path.stat().st_size == parent["size_bytes"]
        assert _sha256(path) == parent["sha256"]
    assert all(value is False for value in audit["authority"].values())
    assert all(value is False for value in audit["claim_boundary"].values())


def test_remaining_audit_reconstructs_the_governing_queue_and_snapshot_rows() -> None:
    audit = _load(AUDIT_PATH)
    queue = _load(
        ROOT / "data/governance/inventory_v5_experiment_readiness_closure_queue_20260812.json"
    )
    expected = {item["action_id"]: item for item in queue["closure_queue"][2:]}

    assert len(audit["audits"]) == 14
    assert {item["action_id"] for item in audit["audits"]} == set(expected)
    for item in audit["audits"]:
        governing = expected[item["action_id"]]
        assert item["material_scope"] == governing["material_scope"]
        assert item["formula_rows_affected"] == governing["formula_rows_affected"]
        expected_sources = [
            {
                "source_row": source["source_row"],
                "canonical_material": source["canonical_material"],
                "status": source["status"],
                "row_uses": source["row_uses"],
            }
            for source in governing["snapshot_sources"]
        ]
        assert item["snapshot_sources"] == expected_sources
        assert item["closure_receipt_created"] is False
        assert item["execution_authorized"] is False
        assert item["missing_gate"]
        assert item["next_safe_action"]


def test_remaining_audit_dispositions_are_complete_and_none_is_ready() -> None:
    audit = _load(AUDIT_PATH)
    counts = Counter(item["disposition"] for item in audit["audits"])

    assert counts == {
        "FORMULA_REBASE_REQUIRED": 2,
        "FORMULA_REBASE_AND_STOCK_LINEAGE_REQUIRED": 1,
        "CARRIER_IDENTITY_THEN_PHYSICAL_PREPARATION_REQUIRED": 1,
        "PHYSICAL_PREPARATION_OR_LABEL_REQUIRED": 10,
    }
    assert audit["summary"] == {
        "actions_audited": 14,
        "ready_to_close": 0,
        "formula_rebase_required": 2,
        "formula_rebase_and_stock_lineage_required": 1,
        "carrier_identity_then_physical_preparation_required": 1,
        "physical_preparation_or_label_required": 10,
        "closure_receipts_created": 0,
        "physical_actions_performed": 0,
    }
    assert not any("READY_TO_CLOSE" in disposition for disposition in counts)


def test_inventory_assertions_exist_but_do_not_close_receipt_gates() -> None:
    audit = _load(AUDIT_PATH)
    inventory = (ROOT / "inventory.txt").read_text(encoding="utf-8")

    for item in audit["audits"]:
        for needle in item["inventory_evidence_needles"]:
            assert needle in inventory
    assert (
        audit["bounded_search"]["canonical_exact_stock_or_preparation_receipts_found_for_actions"]
        == 0
    )
    assert audit["bounded_search"]["formula_rebases_verified_complete"] == 0
    assert audit["bounded_search"]["global_absence_claimed"] is False


def test_deepluna_fanout_recovery_is_truthfully_scoped() -> None:
    audit = _load(AUDIT_PATH)
    evidence = audit["delegation_evidence"]

    assert evidence["route"] == "DEEPLUNA_CHAT_CHEAPLUNA_CHAT_DIRECT_PRO_ONLY"
    assert evidence["initial_requested_parallel_lanes"] == 14
    assert evidence["initial_admitted_job_count"] == 7
    assert evidence["initial_transport_failures_without_job_id"] == 7
    assert evidence["second_fresh_client_parallel_lanes"] == 7
    assert evidence["second_batch_accepted_jobs"] == 7
    assert len(evidence["accepted_job_ids"]) == 12
    assert len(set(evidence["accepted_job_ids"])) == 12
    assert evidence["runtime_limit_inferred"] is False
    assert evidence["runtime_mutated"] is False
    assert evidence["retry_of_admitted_job_performed"] is False
    assert evidence["fallback_used"] is False
    assert evidence["fast_used"] is False
    assert evidence["scientific_acceptance"] == "SOL_LOCAL_ONLY"
