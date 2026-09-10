"""Score confirmation outputs and apply the combined six-case admission gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.perception.complexity_module_retest import ModulePairScore, ModuleRetestRole
from engine.perception.complexity_replacement_benchmark import (
    EvidenceReceiptScore,
    ReplacementScoredOutput,
    build_replacement_benchmark_receipt,
    decide_replacement_retention,
    load_replacement_benchmark_cases,
    score_evidence_receipt,
)
from scripts.score_complexity_replacement_screen import (
    _canonical_bytes,
    _parse_output,
    _read_object,
    _score_dict,
    _sha256,
    _verify_raw,
    _write_frozen,
)

DEFAULT_ROOT = (
    ROOT / "data" / "benchmarks" / "solforge" / "replacement_confirmation_v6_r1"
)
DEFAULT_CORPUS = (
    ROOT / "tests" / "fixtures" / "complexity_replacement_benchmark_cases_v6.json"
)
DEFAULT_SCREEN_RECEIPT = (
    ROOT
    / "data"
    / "benchmarks"
    / "solforge"
    / "replacement_screen_v6_r1"
    / "receipt.normalized_v2.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--screen-receipt", type=Path, default=DEFAULT_SCREEN_RECEIPT)
    parser.add_argument("--output-tag", default="")
    args = parser.parse_args()
    if args.output_tag and not all(
        character.isalnum() or character in {"-", "_"}
        for character in args.output_tag
    ):
        raise ValueError("output-tag may contain only letters, digits, hyphens, and underscores")
    benchmark_root = args.root.resolve()
    artifact_suffix = f".{args.output_tag}" if args.output_tag else ""

    def artifact_path(stem: str) -> Path:
        return benchmark_root / f"{stem}{artifact_suffix}.json"

    manifest = _read_object(benchmark_root / "manifest.json")
    if manifest.get("phase") != "CONFIRM":
        raise ValueError("confirmation scorer requires a CONFIRM manifest")
    manifest_hash = manifest.get("manifest_sha256")
    unhashed_manifest = dict(manifest)
    unhashed_manifest.pop("manifest_sha256", None)
    if _sha256(_canonical_bytes(unhashed_manifest)) != manifest_hash:
        raise ValueError("confirmation manifest internal hash mismatch")
    cases = load_replacement_benchmark_cases(args.corpus.resolve())
    cases_by_id = {case.case_id: case for case in cases}

    objective_results: list[dict[str, Any]] = []
    scored_outputs: list[ReplacementScoredOutput] = []
    for request in manifest["requests"]:
        raw_path = benchmark_root / "raw" / f"{request['request_id']}.json"
        raw = _verify_raw(raw_path, request, manifest["model_identity"])
        case = cases_by_id[request["case_id"]]
        parse_error: str | None = None
        try:
            parsed = _parse_output(raw["output_text"])
            objective_score = score_evidence_receipt(case, parsed)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            parsed = {}
            parse_error = f"{type(exc).__name__}: {exc}"
            expectation = case.objective_expectation
            if expectation is None:
                raise ValueError("confirmation case lacks objective expectation") from exc
            objective_score = EvidenceReceiptScore(
                state="FAIL",
                score=Decimal("0"),
                decision_state_match=False,
                missing_reason_codes=expectation.required_reason_codes,
                calculation_mismatches=tuple(expectation.required_calculations),
                next_action_count_pass=False,
                authority_pass=False,
                critical_error_codes=("MODEL_OUTPUT_NOT_PARSEABLE",),
                full_credit_no_augmentation=False,
            )
        role = ModuleRetestRole(request["role"])
        critical_codes = list(objective_score.critical_error_codes)
        if role is ModuleRetestRole.UNSEEN_VARIANT and objective_score.score < 100:
            critical_codes.append("UNSEEN_VARIANT_CRITICAL_FAILURE")
        critical_codes = list(dict.fromkeys(critical_codes))
        rubric_score = Decimal("0") if critical_codes else objective_score.score
        scored_outputs.append(
            ReplacementScoredOutput(
                request_id=request["request_id"],
                output_text=raw["output_text"],
                rubric_score=rubric_score,
                evaluator_id="objective-evidence-receipt-v6-confirmation",
                critical_error_codes=tuple(critical_codes),
                safe_countercase_pass=True,
                critical_trap_pass=True,
                specialist_checks_pass=objective_score.score == 100,
            )
        )
        objective_results.append(
            {
                "request_id": request["request_id"],
                "case_id": request["case_id"],
                "module_id": request["module_id"],
                "role": request["role"],
                "arm": request["arm"],
                "dispatch_sha256": request["dispatch_sha256"],
                "raw_result_file_sha256": _sha256(raw_path.read_bytes()),
                "output_sha256": raw["output_sha256"],
                "parsed_receipt": parsed,
                "parse_error": parse_error,
                "objective_score": _score_dict(objective_score),
                "rubric_score": str(rubric_score),
                "critical_error_codes": critical_codes,
            }
        )

    objective_payload = {
        "schema_version": "complexity_replacement_objective_scores_v1",
        "manifest_sha256": manifest_hash,
        "corpus_sha256": manifest["corpus_sha256"],
        "scorer_file_sha256": hashlib.sha256(
            (ROOT / "engine/perception/complexity_replacement_benchmark.py").read_bytes()
        ).hexdigest(),
        "result_count": len(objective_results),
        "results": objective_results,
        "authority": dict(manifest["authority"]),
    }
    _write_frozen(artifact_path("objective_scores"), objective_payload)
    confirmation_receipt = build_replacement_benchmark_receipt(
        run_id=manifest["run_nonce"],
        manifest=manifest,
        scored_outputs=tuple(scored_outputs),
    )
    _write_frozen(artifact_path("receipt"), confirmation_receipt)

    screen_receipt = _read_object(args.screen_receipt.resolve())
    if screen_receipt.get("receipt_sha256") != manifest.get("screen_receipt_sha256"):
        raise ValueError("confirmation manifest does not bind the supplied screen receipt")
    combined_results = [*screen_receipt["results"], *confirmation_receipt["results"]]
    included_modules = sorted({row["module_id"] for row in manifest["requests"]})
    decisions = []
    paired_scores: list[dict[str, Any]] = []
    for module_id in included_modules:
        module_results = [
            row for row in combined_results if row["module_id"] == module_id
        ]
        by_case: dict[str, dict[str, dict[str, Any]]] = {}
        for row in module_results:
            by_case.setdefault(row["case_id"], {})[row["arm"]] = row
        if len(by_case) != 6 or any(len(arms) != 3 for arms in by_case.values()):
            raise ValueError("combined admission requires six complete three-arm cases")
        plain: list[ModulePairScore] = []
        placebo: list[ModulePairScore] = []
        for case_id in sorted(by_case):
            arms = by_case[case_id]
            treatment = arms["TREATMENT"]
            role = ModuleRetestRole(treatment["role"])
            critical_regression = bool(treatment["critical_error_codes"])
            safe_pass = bool(treatment["safe_countercase_pass"])
            trap_pass = bool(treatment["critical_trap_pass"])
            specialist_pass = bool(treatment["specialist_checks_pass"])
            pair_rows = []
            for control_arm, target in (("CONTROL", plain), ("PLACEBO", placebo)):
                control = arms[control_arm]
                pair = ModulePairScore(
                    module_id=module_id,
                    case_id=case_id,
                    role=role,
                    treatment_score=Decimal(treatment["rubric_score"]),
                    control_score=Decimal(control["rubric_score"]),
                    critical_regression=critical_regression,
                    safe_countercase_pass=safe_pass,
                    critical_trap_pass=trap_pass,
                    specialist_checks_pass=specialist_pass,
                )
                target.append(pair)
                pair_rows.append(
                    {
                        "control_arm": control_arm,
                        "treatment_score": str(pair.treatment_score),
                        "control_score": str(pair.control_score),
                        "delta": str(pair.delta),
                    }
                )
            paired_scores.append(
                {
                    "module_id": module_id,
                    "case_id": case_id,
                    "role": role.value,
                    "comparisons": pair_rows,
                    "critical_regression": critical_regression,
                    "specialist_checks_pass": specialist_pass,
                }
            )
        decisions.append(decide_replacement_retention(tuple(plain), tuple(placebo)))

    result_payload = {
        "schema_version": "complexity_replacement_confirmation_result_v1",
        "manifest_sha256": manifest_hash,
        "screen_receipt_sha256": screen_receipt["receipt_sha256"],
        "confirmation_receipt_sha256": confirmation_receipt["receipt_sha256"],
        "decisions": [
            {
                "module_id": decision.module_id,
                "state": decision.state,
                "plain_control": decision.plain_control_decision.as_dict(),
                "placebo": decision.placebo_decision.as_dict(),
                "reasons": list(decision.reasons),
            }
            for decision in decisions
        ],
        "paired_scores": paired_scores,
        "authority": dict(manifest["authority"]),
    }
    _write_frozen(artifact_path("confirmation_result"), result_payload)
    admitted = [
        decision.module_id for decision in decisions if decision.state == "ADMITTED"
    ]
    status = {
        "schema_version": "complexity_replacement_confirmation_status_v1",
        "state": "CONFIRMATION_COMPLETE",
        "manifest_sha256": manifest_hash,
        "confirmation_receipt_sha256": confirmation_receipt["receipt_sha256"],
        "admitted_modules": admitted,
        "provenance_tombstones": [
            decision.module_id for decision in decisions if decision.state != "ADMITTED"
        ],
        "runtime_integration_authorized_by_gate": bool(admitted),
        "runtime_reachable": False,
        "authority": dict(manifest["authority"]),
    }
    _write_frozen(artifact_path("status"), status)
    print(json.dumps(status, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
