"""Freeze a hash-bound Sol xhigh replacement-module benchmark manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.perception.complexity_replacement_benchmark import (
    ReplacementScreenDecision,
    build_replacement_benchmark_manifest,
    load_replacement_benchmark_cases,
)

DEFAULT_CORPUS = (
    ROOT / "tests" / "fixtures" / "complexity_replacement_benchmark_cases_v4.json"
)
DEFAULT_RUBRIC = (
    ROOT
    / "configs"
    / "complexity"
    / "complexity_replacement_benchmark_rubric_v1.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain one JSON object")
    return payload


def _screen_decisions(path: Path | None) -> tuple[ReplacementScreenDecision, ...]:
    if path is None:
        return ()
    payload = _read_json(path)
    rows = payload.get("decisions")
    if not isinstance(rows, list):
        raise TypeError("screen result decisions must be a list")
    return tuple(
        ReplacementScreenDecision(
            module_id=row.get("module_id"),
            state=row.get("state"),
            plain_control_wins=row.get("plain_control_wins"),
            placebo_wins=row.get("placebo_wins"),
            reasons=tuple(row.get("reasons", ())),
        )
        for row in rows
        if isinstance(row, dict)
    )


def freeze_manifest(args: argparse.Namespace) -> dict[str, str | int]:
    corpus_path = args.corpus.resolve()
    rubric_path = args.rubric.resolve()
    output_path = args.output.resolve()
    sidecar_path = output_path.with_suffix(".sha256")
    if output_path.exists() or sidecar_path.exists():
        raise FileExistsError("refusing to overwrite a frozen benchmark artifact")
    cases = load_replacement_benchmark_cases(corpus_path)
    phase = args.phase.upper()
    screen_receipt = (
        _read_json(args.screen_receipt.resolve())
        if args.screen_receipt is not None
        else None
    )
    manifest = build_replacement_benchmark_manifest(
        cases=cases,
        corpus_sha256=hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        rubric_sha256=hashlib.sha256(rubric_path.read_bytes()).hexdigest(),
        run_nonce=args.run_nonce,
        model_identity={
            "provider": "OpenAI",
            "product": "Codex",
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "surface": "Codex projectless task",
            "context": "FRESH_PROJECTLESS_CONVERSATION",
        },
        phase=phase,
        screen_decisions=_screen_decisions(args.screen_result),
        screen_receipt=screen_receipt,
    )
    output_bytes = (
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output_bytes)
    file_sha256 = hashlib.sha256(output_bytes).hexdigest()
    sidecar_path.write_text(
        f"{file_sha256}  {output_path.name}\n",
        encoding="ascii",
        newline="\n",
    )
    return {
        "manifest_path": str(output_path),
        "manifest_file_sha256": file_sha256,
        "manifest_sha256": manifest["manifest_sha256"],
        "request_count": manifest["request_count"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-nonce", required=True)
    parser.add_argument("--phase", choices=("SCREEN", "CONFIRM"), required=True)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning-effort", default="xhigh")
    parser.add_argument("--screen-receipt", type=Path)
    parser.add_argument("--screen-result", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.phase == "CONFIRM" and (
        args.screen_receipt is None or args.screen_result is None
    ):
        raise ValueError("confirmation requires --screen-receipt and --screen-result")
    if args.phase == "SCREEN" and (
        args.screen_receipt is not None or args.screen_result is not None
    ):
        raise ValueError("screening cannot consume prior screen artifacts")
    print(json.dumps(freeze_manifest(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
