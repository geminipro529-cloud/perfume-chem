from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.historical_snapshots import ROOT as CANONICAL_ROOT
from tests.historical_snapshots import historical_replay_status

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    ROOT / "data" / "governance" / "inventory_v5_experiment_readiness_closure_queue_20260812.json"
)


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


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_closure_queue_is_hash_bound_nonpromoting_and_semantically_exact() -> None:
    report = _load(REPORT_PATH)

    assert report["schema_version"] == "perfume_chem_inventory_v5_closure_queue_v1"
    assert report["decision"] == (
        "DATA_AMBER_V5_EXPERIMENT_READINESS_CLOSURE_QUEUE_RANKED_PHYSICAL_EXECUTION_NOT_AUTHORIZED"
    )
    assert report["semantic_self_sha256"] == _semantic_sha256(report)
    assert all(value is False for value in report["authority"].values())
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

    held = set()
    for parent in report["parents"]:
        path = ROOT / parent["path"]
        assert path.is_file()
        if parent["path"] == "docs/research/PERFUME_CHEM_CHATGPT_PROJECT_RECONCILIATION_2026-08-10.md":
            assert historical_replay_status(CANONICAL_ROOT / parent["path"], parent["sha256"],
                                            parent["size_bytes"]) == (
                "HOLD_ORIGINAL_SOURCE_BYTES_UNAVAILABLE"
            )
            assert path.read_bytes() == (CANONICAL_ROOT / parent["path"]).read_bytes()
            held.add(parent["path"])
            continue
        assert path.stat().st_size == parent["size_bytes"]
        assert _sha256(path) == parent["sha256"]
    assert held == {"docs/research/PERFUME_CHEM_CHATGPT_PROJECT_RECONCILIATION_2026-08-10.md"}


def test_closure_queue_reconstructs_live_v5_census_and_source_rows() -> None:
    report = _load(REPORT_PATH)
    snapshot = _load(ROOT / "data/governance/inventory_v5_current_stock_snapshot.json")
    crosswalk = _load(ROOT / "data/governance/inventory_v5_alias_crosswalk_20260811.json")
    delta = _load(ROOT / "data/governance/inventory_v5_authority_delta_20260811.json")
    supplement = _load(ROOT / "data/governance/inventory_v5_authority_delta_20260811_02.json")

    assert report["census"] == {
        "snapshot_rows": snapshot["row_count"],
        "identity_crosswalk_contracts": len(crosswalk["contracts"]),
        "authority_delta_records": len(delta["records"]) + len(supplement["records"]),
        "ranked_closure_actions": len(report["closure_queue"]),
        "deferred_procurement_or_replan_holds": len(report["deferred_holds"]),
    }
    assert snapshot["row_count"] == 280
    assert len(crosswalk["contracts"]) == 18
    assert len(delta["records"]) + len(supplement["records"]) == 6

    rows = {int(row["_source_row"]): row for row in snapshot["records"]}
    for action in report["closure_queue"]:
        for source in action["snapshot_sources"]:
            row = rows[source["source_row"]]
            assert row["Canonical material"] == source["canonical_material"]
            assert row["Status"] == source["status"]
            assert int(row["Formula count"]) == source["formula_count"]
            assert int(row["Row uses"]) == source["row_uses"]

    action_by_id = {action["action_id"]: action for action in report["closure_queue"]}
    assert action_by_id["CLR-001"]["crosswalk_contract_id"] == "IDCL-001"
    assert action_by_id["CLR-005"]["formula_rows_affected"] == 53
    assert action_by_id["CLR-008"]["formula_rows_affected"] == 43
    assert action_by_id["CLR-010"]["formula_rows_affected"] == 28
    assert action_by_id["CLR-006"]["formula_rows_affected"] == 12


def test_closure_queue_is_lexicographic_cost_gated_and_falsifiable() -> None:
    report = _load(REPORT_PATH)
    queue = report["closure_queue"]
    allowed_cost_classes = {
        "EVIDENCE_ONLY",
        "FORMULA_BASIS_REBASE",
        "PREPARATION_FROM_CONFIRMED_STOCK",
        "CARRIER_IDENTITY_THEN_PREPARATION",
    }

    assert [action["rank"] for action in queue] == list(range(1, len(queue) + 1))
    assert len({action["action_id"] for action in queue}) == len(queue)
    assert {action["cost_class"] for action in queue} <= allowed_cost_classes
    assert all(action["closure_test"] for action in queue)
    assert all(action["failure_test"] for action in queue)
    assert all(action["execution_authorized"] is False for action in queue)
    assert report["ranking_policy"]["monetary_evsi_invented"] is False
    assert report["ranking_policy"]["ordering"] == [
        "direct_experiment_gate",
        "evidence_before_preparation",
        "existing_exact_stock_before_new_stock",
        "formula_rows_affected_descending_within_cost_class",
    ]

    hypothesis = report["next_hypothesis"]
    assert hypothesis["status"] == "PROSPECTIVE_ONLY"
    assert hypothesis["physical_execution_authorized"] is False
    assert hypothesis["nonlinear_model_authorized"] is False
    assert hypothesis["support_condition"]
    assert hypothesis["refutation_condition"]
    assert hypothesis["stop_conditions"]
    assert hypothesis["baselines"] == [
        "LINEAR_COMPONENT_AVERAGE_FOR_QUALITY",
        "STRONGEST_COMPONENT_FOR_INTENSITY",
        "PRESPECIFIED_HELD_OUT_NONLINEAR_RESIDUAL_ONLY_AFTER_BASELINES",
    ]


def test_closure_queue_preserves_procurement_holds_and_literature_roles() -> None:
    report = _load(REPORT_PATH)
    delta = _load(ROOT / "data/governance/inventory_v5_authority_delta_20260811.json")
    delta_by_id = {record["record_id"]: record for record in delta["records"]}
    deferred = {hold["hold_id"]: hold for hold in report["deferred_holds"]}

    assert deferred["HOLD-AMB-001"]["delta_record_id"] == ("INV-V5-DELTA-AMBRETTOLIDE-RECEIPT")
    assert (
        deferred["HOLD-AMB-001"]["formula_rows_affected"]
        == (delta_by_id["INV-V5-DELTA-AMBRETTOLIDE-RECEIPT"]["formula_count_in_parent"])
    )
    assert (
        deferred["HOLD-POL-001"]["formula_rows_affected"]
        == (delta_by_id["INV-V5-DELTA-POLYSANTOL-STOCK"]["formula_count_in_parent"])
    )
    assert all(hold["procurement_authorized"] is False for hold in deferred.values())
    assert all(hold["substitution_authorized"] is False for hold in deferred.values())

    sources = report["literature_basis"]
    assert len({source["source_id"] for source in sources}) == len(sources)
    assert {source["publication_state"] for source in sources} == {
        "PEER_REVIEWED",
        "PREPRINT",
    }
    assert all(source["role"] for source in sources)
    assert report["claim_boundary"]["universal_mixture_law_claimed"] is False
    assert report["claim_boundary"]["oav_equals_percent_contribution"] is False
    assert report["claim_boundary"]["matrix_independence_assumed"] is False
