"""Freeze deterministic scores from completed projectless benchmark sessions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.perception.complexity_replacement_benchmark import (
    ModuleRetestArm,
    ModuleRetestRole,
    ReplacementScoredOutput,
    _screen_decisions_from_receipt,
    build_replacement_benchmark_receipt,
    load_replacement_benchmark_cases,
    score_evidence_receipt,
)

_AUTHORITY_KEYS = {
    "formula",
    "inventory",
    "physical_execution",
    "sensory",
    "safety",
    "purchase",
    "publication",
    "release",
}
_TOOL_PAYLOAD_TYPES = {
    "computer_call",
    "custom_tool_call",
    "function_call",
    "local_shell_call",
    "mcp_call",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain one JSON object")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _session_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"{path}:{line_number} must contain one JSON object")
        records.append(value)
    return records


def _extract_session(
    *,
    session_path: Path,
    thread_id: str,
    dispatch_text: str,
    expected_model: str,
    expected_effort: str,
) -> tuple[str, dict[str, Any]]:
    records = _session_records(session_path)
    meta = next(
        (row.get("payload") for row in records if row.get("type") == "session_meta"),
        None,
    )
    if not isinstance(meta, Mapping) or meta.get("id") != thread_id:
        raise ValueError(f"session identity mismatch for {thread_id}")
    contexts = [
        row.get("payload")
        for row in records
        if row.get("type") == "turn_context" and isinstance(row.get("payload"), Mapping)
    ]
    if len(contexts) != 1:
        raise ValueError(f"expected one turn context for {thread_id}")
    context = contexts[0]
    if context.get("model") != expected_model or context.get("effort") != expected_effort:
        raise ValueError(f"model identity mismatch for {thread_id}")

    prompt_matches = 0
    final_outputs: list[str] = []
    tool_call_count = 0
    for row in records:
        if row.get("type") != "response_item":
            continue
        payload = row.get("payload")
        if not isinstance(payload, Mapping):
            continue
        if payload.get("type") in _TOOL_PAYLOAD_TYPES:
            tool_call_count += 1
        if payload.get("type") != "message":
            continue
        content = payload.get("content")
        if not isinstance(content, list):
            continue
        texts = [
            item.get("text")
            for item in content
            if isinstance(item, Mapping) and isinstance(item.get("text"), str)
        ]
        if payload.get("role") == "user" and any(dispatch_text in text for text in texts):
            prompt_matches += 1
        if payload.get("role") == "assistant" and payload.get("phase") == "final_answer":
            final_outputs.extend(texts)
    if prompt_matches != 1:
        raise ValueError(f"exact dispatch prompt mismatch for {thread_id}")
    if tool_call_count:
        raise ValueError(f"benchmark task used tools for {thread_id}")
    if len(final_outputs) != 1:
        raise ValueError(f"expected one final output for {thread_id}")
    return final_outputs[0], {
        "thread_id": thread_id,
        "session_file": session_path.name,
        "session_sha256": _sha256(session_path.read_bytes()),
        "actual_model": context["model"],
        "actual_reasoning_effort": context["effort"],
        "network_state": "RESTRICTED"
        if context.get("network") == "restricted"
        else str(context.get("network")),
        "exact_dispatch_prompt_match": True,
        "tool_call_count": 0,
    }


def _write_frozen_json(path: Path, value: Mapping[str, Any]) -> str:
    if path.exists() or path.with_suffix(".sha256").exists():
        raise FileExistsError(f"refusing to overwrite frozen artifact: {path}")
    data = (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(data)
    digest = _sha256(data)
    path.with_suffix(".sha256").write_text(
        f"{digest}  {path.name}\n",
        encoding="ascii",
        newline="\n",
    )
    return digest


def score_run(args: argparse.Namespace) -> dict[str, Any]:
    manifest = _read_json(args.manifest.resolve())
    mapping = _read_json(args.mapping.resolve())
    if mapping.get("schema_version") != "evidence_foundation_execution_map_v1":
        raise ValueError("unsupported execution mapping schema")
    authority = mapping.get("authority")
    if (
        not isinstance(authority, Mapping)
        or set(authority) != _AUTHORITY_KEYS
        or any(authority[key] is not False for key in _AUTHORITY_KEYS)
    ):
        raise ValueError("execution mapping authority must be exact and all false")
    map_rows = mapping.get("requests")
    request_rows = manifest.get("requests")
    if not isinstance(map_rows, list) or not isinstance(request_rows, list):
        raise TypeError("manifest and execution mapping requests must be lists")
    thread_by_request = {
        row.get("request_id"): row.get("thread_id") for row in map_rows if isinstance(row, Mapping)
    }
    request_ids = {row.get("request_id") for row in request_rows}
    if set(thread_by_request) != request_ids or len(thread_by_request) != len(map_rows):
        raise ValueError("execution mapping must cover each manifest request exactly once")

    cases = {case.case_id: case for case in load_replacement_benchmark_cases(args.corpus.resolve())}
    scored_outputs: list[ReplacementScoredOutput] = []
    executions: list[dict[str, Any]] = []
    for request in request_rows:
        if not isinstance(request, Mapping):
            raise TypeError("manifest request must be an object")
        request_id = request["request_id"]
        thread_id = thread_by_request[request_id]
        matches = tuple(args.archive_dir.resolve().glob(f"*{thread_id}.jsonl"))
        if len(matches) != 1:
            raise ValueError(f"expected one archived session for {thread_id}")
        output_text, execution = _extract_session(
            session_path=matches[0],
            thread_id=thread_id,
            dispatch_text=request["dispatch_text"],
            expected_model=manifest["model_identity"]["model"],
            expected_effort=manifest["model_identity"]["reasoning_effort"],
        )
        case = cases[request["case_id"]]
        parse_error = False
        try:
            output_payload = json.loads(output_text)
        except json.JSONDecodeError:
            output_payload = {}
            parse_error = True
        if not isinstance(output_payload, Mapping):
            output_payload = {}
            parse_error = True
        observed_critical = ("INVALID_JSON_OUTPUT",) if parse_error else ()
        objective = score_evidence_receipt(
            case,
            output_payload,
            observed_critical_error_codes=observed_critical,
        )
        critical_errors = list(objective.critical_error_codes)
        is_treatment = request["arm"] == ModuleRetestArm.TREATMENT.value
        is_trap = request["role"] == ModuleRetestRole.CRITICAL_TRAP.value
        if is_treatment and is_trap and objective.score != Decimal("100"):
            critical_errors.append(case.critical_error)
        critical_errors = list(dict.fromkeys(critical_errors))
        final_score = Decimal("0") if critical_errors else objective.score
        full_credit = final_score == Decimal("100")
        scored_outputs.append(
            ReplacementScoredOutput(
                request_id=request_id,
                output_text=output_text,
                rubric_score=final_score,
                evaluator_id="deterministic-evidence-receipt-v8",
                critical_error_codes=tuple(critical_errors),
                safe_countercase_pass=(
                    not is_treatment
                    or request["role"] != ModuleRetestRole.SAFE_COUNTERCASE.value
                    or full_credit
                ),
                critical_trap_pass=(not is_treatment or not is_trap or full_credit),
                specialist_checks_pass=(not is_treatment or full_credit),
            )
        )
        execution.update(
            {
                "request_id": request_id,
                "case_id": request["case_id"],
                "module_id": request["module_id"],
                "arm": request["arm"],
                "dispatch_sha256": request["dispatch_sha256"],
                "output_sha256": _sha256(output_text.encode("utf-8")),
                "objective_score": str(final_score),
                "critical_error_codes": critical_errors,
            }
        )
        executions.append(execution)

    receipt = build_replacement_benchmark_receipt(
        run_id=mapping["run_id"],
        manifest=manifest,
        scored_outputs=tuple(scored_outputs),
    )
    decisions = _screen_decisions_from_receipt(receipt["results"])
    decisions_payload = {
        "schema_version": "evidence_foundation_screen_decisions_v1",
        "run_id": mapping["run_id"],
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
        "authority": dict(manifest["authority"]),
    }
    execution_payload = {
        "schema_version": "evidence_foundation_execution_receipt_v1",
        "run_id": mapping["run_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "result_count": len(executions),
        "results": executions,
        "ignored_attempts": mapping.get("ignored_attempts", []),
        "authority": dict(manifest["authority"]),
    }
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt_hash = _write_frozen_json(output_dir / "receipt.json", receipt)
    decisions_hash = _write_frozen_json(output_dir / "screen_decisions.json", decisions_payload)
    execution_hash = _write_frozen_json(output_dir / "execution_receipt.json", execution_payload)
    return {
        "receipt_file_sha256": receipt_hash,
        "receipt_sha256": receipt["receipt_sha256"],
        "decisions_file_sha256": decisions_hash,
        "execution_file_sha256": execution_hash,
        "decisions": decisions_payload["decisions"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(score_run(_parser().parse_args()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
