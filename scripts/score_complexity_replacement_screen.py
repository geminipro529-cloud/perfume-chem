"""Score and freeze one completed replacement-module screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.perception.complexity_module_retest import (
    ModulePairScore,
    ModuleRetestRole,
)
from engine.perception.complexity_replacement_benchmark import (
    REPLACEMENT_MODULE_IDS,
    EvidenceReceiptScore,
    ReplacementBenchmarkCase,
    ReplacementScoredOutput,
    build_replacement_benchmark_receipt,
    decide_replacement_screen,
    load_replacement_benchmark_cases,
    score_evidence_receipt,
)

DEFAULT_ROOT = ROOT / "data" / "benchmarks" / "solforge" / "replacement_screen_v4_r2"
DEFAULT_CORPUS = (
    ROOT / "tests" / "fixtures" / "complexity_replacement_benchmark_cases_v4.json"
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain one JSON object")
    return payload


def _parse_output(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(lines[1:-1]).strip()
    payload = json.loads(candidate)
    if not isinstance(payload, dict):
        raise TypeError("model output must contain one JSON object")
    return payload


def _verify_raw(
    path: Path,
    request: Mapping[str, Any],
    model_identity: Mapping[str, str],
) -> dict[str, Any]:
    sidecar = path.with_suffix(".sha256")
    expected_file_sha256 = sidecar.read_text(encoding="ascii").split()[0]
    if _sha256(path.read_bytes()) != expected_file_sha256:
        raise ValueError(f"raw output hash mismatch: {path}")
    payload = _read_object(path)
    required_matches = {
        "request_id": request["request_id"],
        "case_id": request["case_id"],
        "module_id": request["module_id"],
        "phase": request["phase"],
        "role": request["role"],
        "arm": request["arm"],
        "prompt_sha256": request["prompt_sha256"],
        "dispatch_sha256": request["dispatch_sha256"],
        "model": model_identity["model"],
        "reasoning_effort": model_identity["reasoning_effort"],
    }
    if any(payload.get(key) != value for key, value in required_matches.items()):
        raise ValueError(f"raw output lineage mismatch: {path}")
    if payload.get("exit_code") != 0 or not payload.get("output_text"):
        raise ValueError(f"raw output did not complete: {path}")
    output_text = payload["output_text"]
    if _sha256(output_text.encode("utf-8")) != payload.get("output_sha256"):
        raise ValueError(f"raw output text hash mismatch: {path}")
    if any(value is not False for value in payload.get("authority", {}).values()):
        raise ValueError(f"raw execution receipt grants authority: {path}")
    return payload


def _score_dict(score: EvidenceReceiptScore) -> dict[str, Any]:
    payload = asdict(score)
    payload["score"] = str(score.score)
    payload["missing_reason_codes"] = list(score.missing_reason_codes)
    payload["calculation_mismatches"] = list(score.calculation_mismatches)
    payload["critical_error_codes"] = list(score.critical_error_codes)
    return payload


def _write_frozen(path: Path, payload: Mapping[str, Any]) -> None:
    sidecar = path.with_suffix(".sha256")
    if path.exists() or sidecar.exists():
        raise FileExistsError(f"refusing to overwrite frozen artifact: {path}")
    output_bytes = (
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")
    path.write_bytes(output_bytes)
    sidecar.write_text(
        f"{_sha256(output_bytes)}  {path.name}\n",
        encoding="ascii",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    args = parser.parse_args()
    benchmark_root = args.root.resolve()
    manifest_path = benchmark_root / "manifest.json"
    raw_root = benchmark_root / "raw"
    manifest = _read_object(manifest_path)
    manifest_hash = manifest.get("manifest_sha256")
    unhashed_manifest = dict(manifest)
    unhashed_manifest.pop("manifest_sha256", None)
    if _sha256(_canonical_bytes(unhashed_manifest)) != manifest_hash:
        raise ValueError("manifest internal hash mismatch")
    cases = load_replacement_benchmark_cases(args.corpus.resolve())
    cases_by_id: dict[str, ReplacementBenchmarkCase] = {
        case.case_id: case for case in cases
    }

    objective_results: list[dict[str, Any]] = []
    scored_outputs: list[ReplacementScoredOutput] = []
    score_by_request: dict[str, Decimal] = {}
    score_state_by_request: dict[str, EvidenceReceiptScore] = {}
    for request in manifest["requests"]:
        raw_path = raw_root / f"{request['request_id']}.json"
        raw = _verify_raw(raw_path, request, manifest["model_identity"])
        case = cases_by_id[request["case_id"]]
        parse_error: str | None = None
        try:
            parsed = _parse_output(raw["output_text"])
            objective_score = score_evidence_receipt(case, parsed)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            parsed = {}
            parse_error = f"{type(exc).__name__}: {exc}"
            objective_score = EvidenceReceiptScore(
                state="FAIL",
                score=Decimal("0"),
                decision_state_match=False,
                missing_reason_codes=case.objective_expectation.required_reason_codes,
                calculation_mismatches=tuple(
                    case.objective_expectation.required_calculations
                ),
                next_action_count_pass=False,
                authority_pass=False,
                critical_error_codes=("MODEL_OUTPUT_NOT_PARSEABLE",),
                full_credit_no_augmentation=False,
            )
        role = ModuleRetestRole(request["role"])
        critical_codes = list(objective_score.critical_error_codes)
        if role is ModuleRetestRole.CRITICAL_TRAP and objective_score.score < 100:
            critical_codes.append("CRITICAL_TRAP_NOT_PREVENTED")
        critical_codes = list(dict.fromkeys(critical_codes))
        rubric_score = objective_score.score
        if critical_codes:
            rubric_score = Decimal("0")
        safe_pass = (
            objective_score.score == 100
            if role is ModuleRetestRole.SAFE_COUNTERCASE
            else True
        )
        trap_pass = (
            objective_score.score == 100
            if role is ModuleRetestRole.CRITICAL_TRAP
            else True
        )
        scored = ReplacementScoredOutput(
            request_id=request["request_id"],
            output_text=raw["output_text"],
            rubric_score=rubric_score,
            evaluator_id="objective-evidence-receipt-v4",
            critical_error_codes=tuple(critical_codes),
            safe_countercase_pass=safe_pass,
            critical_trap_pass=trap_pass,
            specialist_checks_pass=objective_score.score == 100,
        )
        scored_outputs.append(scored)
        score_by_request[request["request_id"]] = rubric_score
        score_state_by_request[request["request_id"]] = objective_score
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
        "scorer_file_sha256": _sha256(
            (ROOT / "engine/perception/complexity_replacement_benchmark.py").read_bytes()
        ),
        "result_count": len(objective_results),
        "results": objective_results,
        "authority": dict(manifest["authority"]),
    }
    _write_frozen(benchmark_root / "objective_scores.json", objective_payload)

    receipt = build_replacement_benchmark_receipt(
        run_id=manifest["run_nonce"],
        manifest=manifest,
        scored_outputs=tuple(scored_outputs),
    )
    _write_frozen(benchmark_root / "receipt.json", receipt)

    requests_by_case: dict[str, dict[str, Mapping[str, Any]]] = {}
    for request in manifest["requests"]:
        requests_by_case.setdefault(request["case_id"], {})[request["arm"]] = request
    decisions = []
    paired_scores: list[dict[str, Any]] = []
    for module_id in REPLACEMENT_MODULE_IDS:
        plain: list[ModulePairScore] = []
        placebo: list[ModulePairScore] = []
        module_cases = [
            case
            for case in cases
            if case.module_id == module_id and case.phase == "SCREEN"
        ]
        for case in module_cases:
            arms = requests_by_case[case.case_id]
            treatment_request = arms["TREATMENT"]
            treatment_score = score_by_request[treatment_request["request_id"]]
            treatment_state = score_state_by_request[treatment_request["request_id"]]
            safe_pass = (
                treatment_state.score == 100
                if case.role is ModuleRetestRole.SAFE_COUNTERCASE
                else True
            )
            trap_pass = (
                treatment_state.score == 100
                if case.role is ModuleRetestRole.CRITICAL_TRAP
                else True
            )
            critical_regression = bool(treatment_state.critical_error_codes) or (
                case.role is ModuleRetestRole.CRITICAL_TRAP and not trap_pass
            )
            pair_rows = []
            for control_arm, target in (("CONTROL", plain), ("PLACEBO", placebo)):
                control_request = arms[control_arm]
                pair = ModulePairScore(
                    module_id=module_id,
                    case_id=case.case_id,
                    role=case.role,
                    treatment_score=treatment_score,
                    control_score=score_by_request[control_request["request_id"]],
                    critical_regression=critical_regression,
                    safe_countercase_pass=safe_pass,
                    critical_trap_pass=trap_pass,
                    specialist_checks_pass=treatment_state.score == 100,
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
                    "case_id": case.case_id,
                    "role": case.role.value,
                    "comparisons": pair_rows,
                    "critical_regression": critical_regression,
                    "safe_countercase_pass": safe_pass,
                    "critical_trap_pass": trap_pass,
                }
            )
        decisions.append(decide_replacement_screen(tuple(plain), tuple(placebo)))

    screen_result = {
        "schema_version": "complexity_replacement_screen_result_v2",
        "manifest_sha256": manifest_hash,
        "receipt_sha256": receipt["receipt_sha256"],
        "decisions": [
            {
                "module_id": decision.module_id,
                "state": decision.state,
                "plain_control_wins": decision.plain_control_wins,
                "placebo_wins": decision.placebo_wins,
                "reasons": list(decision.reasons),
            }
            for decision in decisions
        ],
        "paired_scores": paired_scores,
        "authority": dict(manifest["authority"]),
    }
    _write_frozen(benchmark_root / "screen_result.json", screen_result)
    passed = [decision.module_id for decision in decisions if decision.state == "PROCEED"]
    status = {
        "schema_version": "complexity_replacement_screen_status_v1",
        "state": "SCREEN_COMPLETE",
        "manifest_sha256": manifest_hash,
        "receipt_sha256": receipt["receipt_sha256"],
        "completed_requests": len(scored_outputs),
        "proceed_modules": passed,
        "stopped_modules": [
            decision.module_id for decision in decisions if decision.state == "STOP"
        ],
        "confirmation_authorized_by_gate": bool(passed),
        "runtime_reachable": False,
        "authority": dict(manifest["authority"]),
    }
    _write_frozen(benchmark_root / "status.json", status)
    print(json.dumps(status, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
