"""The captured post-cutoff delta is fully dispositioned and inert where preserved."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/governance/post_cutoff_supplement_20260910.json"


def _ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_every_captured_post_cutoff_path_has_one_final_disposition():
    payload = _ledger()
    entries = payload["entries"]
    assert len(entries) == 14
    assert len({entry["path"] for entry in entries}) == 14
    assert all(
        entry["disposition"]
        in {
            "RECONCILED",
            "PRESERVED_DISABLED",
            "EXCLUDED_GENERATED",
            "EXCLUDED_MECHANICAL",
        }
        for entry in entries
    )
    assert payload["private_capture"]["hash_verified"] is True
    assert payload["governing_limits"]["whole_dirty_files_imported"] is False


def test_disabled_formula_and_expanded_audit_log_are_not_activated():
    payload = _ledger()
    by_path = {entry["path"]: entry for entry in payload["entries"]}
    formula_path = "formulas/Jasmine_Sambac_Vivante_30mL_V4_Realistic_Hedonic.md"
    assert by_path[formula_path]["disposition"] == "PRESERVED_DISABLED"
    assert not (ROOT / formula_path).exists()

    audit_path = "data/pipeline_audit/events.jsonl"
    assert by_path[audit_path]["disposition"] == "EXCLUDED_GENERATED"
    assert by_path[audit_path]["captured_sha256"] != by_path[audit_path]["integration_before_sha256"]


def test_original_acceptance_and_ledger_remain_separate_from_the_supplement():
    payload = _ledger()
    assert payload["governing_limits"]["historical_ledger_modified"] is False
    assert (ROOT / "docs/governance/worktree_consolidation_ledger_20260910.json").is_file()
    assert (ROOT / "docs/governance/consolidation_acceptance_20260910.json").is_file()
