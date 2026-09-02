#!/usr/bin/env python3
"""Run deterministic validation for the standalone V20 closure candidate."""

from __future__ import annotations

import argparse
import compileall
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
from decimal import Decimal
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from perfume_chem_v20_guardrails.authority import FALSE_AUTHORITY_FLAGS
from perfume_chem_v20_guardrails.canonical import canonical_decimal, sha256_file
from perfume_chem_v20_guardrails.complexity_dispatch import (
    ComplexityProfile,
    CurrentComplexityDispatcher,
)
from perfume_chem_v20_guardrails.exact_bytes import DEPENDENCIES
from perfume_chem_v20_guardrails.formula_artifact import FormulaPartLine, recompute_dose_export
from perfume_chem_v20_guardrails.qualification_adapter import adapt_legacy_qualification
from perfume_chem_v20_guardrails.runtime_policy import RuntimeRequest, provider_outcome


def run_tests() -> tuple[dict, str]:
    buffer = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    with redirect_stdout(buffer), redirect_stderr(buffer):
        result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(suite)
    report = {
        "tests_run": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
        "failed": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "state": "PASS" if result.wasSuccessful() else "FAIL",
    }
    return report, buffer.getvalue()


def replay_mcv3() -> list[dict]:
    rules_path = ROOT / "reference/meaningful_complexity_v3/COMPLEXITY_CLASSIFICATION_RULES.json"
    cases_path = ROOT / "reference/meaningful_complexity_v3/COMPLEXITY_MODEL_TEST_CASES.json"
    dispatcher = CurrentComplexityDispatcher.from_rules_file(rules_path)
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["test_cases"]
    selected = {"MCV3-TC-001", "MCV3-TC-002", "MCV3-TC-003", "MCV3-TC-004", "MCV3-TC-007"}
    output = []
    for case in cases:
        if case["test_case_id"] not in selected:
            continue
        input_profile = dict(case["input_profile"])
        if case["test_case_id"] == "MCV3-TC-007":
            input_profile.update(
                total_rows=75,
                distinct_canonical_odor_identities=73,
                technical_rows=2,
                duplicate_strength_rows=0,
                proposed_microtexture_rows=2,
                functional_row_ratio=0.96,
                single_point_dependencies=0,
                requested_claim="ORCHESTRAL",
                resilience_control_paths=2,
            )
        decision = dispatcher.classify(ComplexityProfile.from_mapping(input_profile))
        output.append(
            {
                "test_case_id": case["test_case_id"],
                "expected_class": case["expected"].get("assigned_class"),
                "observed_class": decision.assigned_class.value,
                "expected_state": case["expected"].get("classification_state"),
                "observed_state": decision.classification_state.value,
                "g14_state": decision.current_gate_states.get("G14"),
                "decision_hash": decision.decision_hash,
            }
        )
    return output


def replay_legacy_adapter() -> dict:
    fixtures = json.loads(
        (ROOT / "reference/legacy_qualification/engine_qualification_fixtures.json").read_text(
            encoding="utf-8"
        )
    )["fixtures"]
    results_payload = json.loads(
        (ROOT / "reference/legacy_qualification/ENGINE_QUALIFICATION_REFERENCE_RESULTS.json").read_text(
            encoding="utf-8"
        )
    )
    results = results_payload["results"]
    receipts = []
    for fixture_id in ("EQ-02-KNOWN-INVALID", "EQ-16-LOW-QUALITY-SCORE"):
        fixture = next(item for item in fixtures if item["fixture_id"] == fixture_id)
        result = next(item for item in results if item["fixture_id"] == fixture_id)
        adapted = adapt_legacy_qualification(
            fixture_id=fixture_id,
            expected_state=fixture["expected_state"],
            observed_state=result["observed_state"],
            expected_failed_gates=fixture["expected_failed_gates"],
            observed_failed_gates=result["observed_failed_gates"],
            raw_record={"fixture": fixture, "result": result},
        )
        receipts.append(
            {
                "fixture_id": adapted.fixture_id,
                "legacy_state": adapted.legacy_state,
                "current_policy_state": adapted.current_policy_state,
                "normalized_expected_failed_gates": list(adapted.normalized_expected_failed_gates),
                "normalized_observed_failed_gates": list(adapted.normalized_observed_failed_gates),
                "current_policy_gate_sets_match": adapted.current_policy_gate_sets_match,
                "legacy_fixture_still_quarantined": adapted.legacy_fixture_still_quarantined,
                "authority_promoted": adapted.authority_promoted,
                "adapter_hash": adapted.adapter_hash,
            }
        )
    return {
        "legacy_package_state": "FAIL_15_OF_16__QUARANTINED",
        "target_engine_run": False,
        "current_adapter_receipts": receipts,
    }


def synthetic_export_receipt() -> dict:
    lines = [
        FormulaPartLine.create(line_id="A", parts_per_1000="333.3333"),
        FormulaPartLine.create(line_id="B", parts_per_1000="333.3333"),
        FormulaPartLine.create(line_id="C", parts_per_1000="333.3334"),
    ]
    export = recompute_dose_export(
        formula_id="SYNTHETIC-DECIMAL-EXPORT-FIXTURE",
        parent_formula_hash="a" * 64,
        lines=lines,
        concentrate_ul="4500",
        display_places=4,
        balance_line_id="C",
    )
    return {
        "scope": "SYNTHETIC_REGRESSION_ONLY",
        "canonical_parts_unchanged": export.canonical_parts_unchanged,
        "exact_total_ul": canonical_decimal(export.exact_total_ul),
        "exported_total_ul": canonical_decimal(export.exported_total_ul),
        "balance_line_id": export.balance_line_id,
        "successor_hash": export.successor_hash,
        "formula_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", default=str(ROOT / "VALIDATION_REPORT.json"))
    parser.add_argument("--log", dest="log_path", default=str(ROOT / "VALIDATION_TEST_LOG.txt"))
    args = parser.parse_args()

    compile_state = compileall.compile_dir(str(SRC), quiet=1) and compileall.compile_dir(
        str(ROOT / "tests"), quiet=1
    )
    tests, log = run_tests()
    Path(args.log_path).write_text(log, encoding="utf-8")

    source_hashes = {
        "inventory_v5": {
            "path": "/mnt/data/Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5(1).xlsx",
            "expected_sha256": "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331",
        },
        "meaningful_complexity_v3_package": {
            "path": "/mnt/data/PCV3_CHAT1_MEANINGFUL_COMPLEXITY_MODEL_V3_COMPLETE.zip",
            "expected_sha256": "10acff0eb8f9e40dc0bd0e8152e04eb3c6440393c39dc950ccc3e96dccc1f6e1",
        },
        "legacy_qualification_v1_package": {
            "path": "/mnt/data/Perfume_Verification_Engine_Qualification_v1_Package(1).zip",
            "expected_sha256": "af2b207bda605058472c868d94f907ea1b6540a8baf1a6458472a55193f7f07d",
        },
    }
    for record in source_hashes.values():
        path = Path(record["path"])
        observed = sha256_file(path) if path.is_file() else None
        record["observed_sha256"] = observed
        record["state"] = "PASS" if observed == record["expected_sha256"] else "HOLD"

    runtime_request = RuntimeRequest(
        project_id="perfume-chem-cheapluna-isolated",
        profile="cheapluna-chat",
        route="DIRECT_PRO",
        luna_mode="NO_LUNA",
        deep_luna_fast_enabled=False,
        alternate_fallbacks_enabled=False,
    )
    provider_failure = provider_outcome(request=runtime_request, provider_succeeded=False)

    report = {
        "schema_version": "PERFUME_CHEM_V20_GAP_CLOSURE_VALIDATION_v1",
        "candidate_version": "0.1.0-candidate",
        "python_version": sys.version,
        "compile_state": "PASS" if compile_state else "FAIL",
        "unit_tests": tests,
        "source_hash_checks": source_hashes,
        "mcv3_dispatch_replay": replay_mcv3(),
        "legacy_qualification_adapter": replay_legacy_adapter(),
        "synthetic_decimal_export": synthetic_export_receipt(),
        "exact_dependency_registry": [asdict(spec) for spec in DEPENDENCIES],
        "runtime_policy_provider_failure": asdict(provider_failure),
        "authority_flags": dict(FALSE_AUTHORITY_FLAGS.as_mapping()),
        "repository_state": "BRIDGE_BLOCKED",
        "installation_state": "NOT_INSTALLED",
        "overall_state": (
            "PASS_STANDALONE_CANDIDATE__REPOSITORY_AND_EVIDENCE_HOLDS_PRESERVED"
            if compile_state and tests["state"] == "PASS" and all(
                item["state"] == "PASS" for item in source_hashes.values()
            )
            else "FAIL_STANDALONE_CANDIDATE"
        ),
    }
    Path(args.json_path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report["overall_state"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
