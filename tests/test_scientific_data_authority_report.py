from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.schemas.lab_reporting import SCIENCE_EVIDENCE_CLASSES  # noqa: E402
from app.services.lab_claims import CLAIM_AUTHORITY_POLICIES  # noqa: E402

REPORT_JSON = (
    PROJECT_ROOT / "docs" / "verification" / "scientific_data_authority_report.json"
)
REPORT_MARKDOWN = (
    PROJECT_ROOT / "docs" / "verification" / "scientific_data_authority_report.md"
)

REQUIRED_TEST_CATEGORIES = (
    "source_ingestion_and_digest_verification",
    "exact_locator_preservation",
    "duplicate_and_independence_grouping",
    "observation_round_trips",
    "selected_assertion_conflict_handling",
    "unit_conversion_and_incompatibility",
    "contextual_odt_matching",
    "strict_science_mode",
    "oav_claim_boundaries",
    "rule_compilation_and_invalid_reference_prevention",
    "analytical_method_validation",
    "calibration_qc_and_uncertainty",
    "gc_o_alignment",
    "raw_file_attachment_and_digest",
    "regulatory_dates_and_snapshot_versioning",
    "natural_contribution_aggregation",
    "negative_authority_promotion_cases",
    "api_and_report_provenance",
    "export_import_backup_and_restore",
)

BUILD_B_COMPLETION_CRITERIA = (
    "runtime_values_traceable_or_explicitly_labeled",
    "selected_values_expose_policy_and_uncertainty",
    "odts_are_contextual",
    "oav_mismatches_fail_closed",
    "advisory_rules_cannot_become_hidden_numerical_truth",
    "analytical_claims_require_method_validation_and_qc",
    "regulatory_screens_are_current_dated_scoped_and_preserve_unknowns",
    "heuristic_data_remain_visibly_separate",
    "full_verification_passes",
    "no_scientific_release_claim_is_made",
)

CHECKPOINT_ROLES = (
    "build_b_baseline_gate",
    "final_runtime_implementation",
    "final_pre_b10_gate",
    "b10_report_input",
)

REQUIRED_AUTHORITY_SECTIONS = (
    "source_inventory",
    "observation_inventory",
    "migrated_data",
    "conflicts",
    "selected_assertion_policy",
    "odt_authority_by_context",
    "knowledge_rule_status",
    "analytical_method_validation_matrix",
    "regulatory_snapshot_inventory",
    "runtime_call_graph",
    "verifier",
    "remaining_unknowns",
    "claim_wording",
)


def _load_reports() -> tuple[dict[str, object], str]:
    assert REPORT_JSON.is_file(), f"missing required report: {REPORT_JSON}"
    assert REPORT_MARKDOWN.is_file(), f"missing required report: {REPORT_MARKDOWN}"
    return (
        json.loads(REPORT_JSON.read_text(encoding="utf-8")),
        REPORT_MARKDOWN.read_text(encoding="utf-8"),
    )


def test_scientific_data_authority_report_contract() -> None:
    payload, markdown = _load_reports()

    assert payload["schema_version"] == (
        "perfume-chem-scientific-data-authority-report-v1"
    )
    assert payload["build"] == "B"
    assert payload["phase"] == "B10"
    assert payload["status"] == "PASS"
    assert payload["authority_state"] == "READ_ONLY_NON_PROMOTING"
    assert payload["release_authority"] is False

    checkpoints = payload["git_checkpoints"]
    assert [item["role"] for item in checkpoints] == list(CHECKPOINT_ROLES)
    assert all(
        re.fullmatch(r"[0-9a-f]{40}", item["commit_sha"]) for item in checkpoints
    )

    assert payload["evidence_classes"] == list(SCIENCE_EVIDENCE_CLASSES)
    for section in REQUIRED_AUTHORITY_SECTIONS:
        assert section in payload
    assert set(payload["runtime_call_graph"]) == {"before", "after"}
    assert payload["runtime_call_graph"]["before"]
    assert payload["runtime_call_graph"]["after"]

    test_rows = payload["required_test_matrix"]
    assert [row["category"] for row in test_rows] == list(REQUIRED_TEST_CATEGORIES)
    assert all(row["status"] == "PASS" for row in test_rows)
    assert all(row["tests"] for row in test_rows)
    assert all(row["authority_boundary"] for row in test_rows)

    completion_rows = payload["build_b_completion"]
    assert [row["criterion"] for row in completion_rows] == list(
        BUILD_B_COMPLETION_CRITERIA
    )
    assert all(row["status"] == "SATISFIED" for row in completion_rows)
    assert all(row["evidence"] for row in completion_rows)

    policy = CLAIM_AUTHORITY_POLICIES["EXACT_CHEMICAL_IDENTITY"]
    assert payload["claim_wording"]["permitted"] == dict(policy.permitted_wording)
    assert payload["claim_wording"]["forbidden"] == list(policy.forbidden_wording)

    assert payload["remaining_unknowns"]
    assert payload["verifier"]["completion_gate"] in {"PASS", "PASS_WITH_SKIPS"}
    assert payload["verifier"]["failed"] == []
    assert "Build B status: PASS" in markdown
    assert "Scientific release authority: NOT GRANTED" in markdown
    assert payload["authority_statement"] in markdown

    serialized = json.dumps(payload, sort_keys=True).casefold()
    for prohibited in (
        "aggregate_score",
        "confidence_percent",
        "confidence_score",
        "coverage_score",
    ):
        assert prohibited not in serialized
    for credential_key in (
        '"api_key"',
        '"credential"',
        '"password"',
        '"secret"',
        '"token"',
    ):
        assert credential_key not in serialized
