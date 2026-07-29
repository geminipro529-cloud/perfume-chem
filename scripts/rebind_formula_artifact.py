"""Safely rebind one existing generated formula analysis artifact.

The command computes a fresh artifact through the canonical release pipeline,
prints a semantic manifest diff, and writes only after repository-state checks.
It never accepts an expected hash from the caller.
"""

from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.formula_release_gate import _append_pipeline_analysis
from scripts.verify_formula_workflow import (
    parse_formula_markdown,
    parse_pipeline_analysis_manifest,
    split_generated_pipeline_analysis,
)

_VOLATILE_MANIFEST_FIELDS = {
    "artifact_sha256",
    "generated_at_utc",
    "repository_commit",
}


def _formula_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("formula path must remain inside the repository") from exc
    if not resolved.is_file():
        raise ValueError("formula path must name an existing file")
    return resolved


def _git_status(path: Path) -> tuple[bool, bool]:
    relative = path.relative_to(PROJECT_ROOT).as_posix()
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--", relative],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    lines = [line for line in result.stdout.splitlines() if line]
    if len(lines) > 1:
        raise RuntimeError("ambiguous git status for formula path")
    if not lines:
        return False, False
    status = lines[0][:2]
    staged = status[0] not in {" ", "?"}
    unstaged = status[1] != " "
    if status == "??":
        unstaged = True
    return staged, unstaged


def _semantic_manifest(
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in manifest.items()
        if key not in _VOLATILE_MANIFEST_FIELDS
    }


def semantic_manifest_diff(
    prior: Mapping[str, Any],
    proposed: Mapping[str, Any],
) -> str:
    """Return a deterministic, human-reviewable semantic manifest diff."""

    before = json.dumps(
        _semantic_manifest(prior),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).splitlines()
    after = json.dumps(
        _semantic_manifest(proposed),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).splitlines()
    return "\n".join(
        difflib.unified_diff(
            before,
            after,
            fromfile="bound-manifest",
            tofile="proposed-manifest",
            lineterm="",
        )
    )


def _fresh_artifact(
    formula_path: Path,
    extra_args: list[str],
) -> tuple[dict[str, Any], str]:
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "formula_release_gate.py"),
        "--formula-file",
        str(formula_path),
        "--no-append-analysis",
        "--no-audit",
        "--json",
        *extra_args,
    ]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if not result.stdout.strip():
        raise RuntimeError(
            "release pipeline produced no JSON; stderr was: "
            + result.stderr.strip()[:1000]
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("release pipeline output was not valid JSON") from exc
    manifest = payload.get("run_evidence_contract")
    analysis = payload.get("analysis_markdown")
    if not isinstance(manifest, dict) or not isinstance(analysis, str):
        raise RuntimeError("release pipeline omitted the bound artifact")
    return manifest, analysis


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review and optionally apply a formula artifact rebind."
    )
    parser.add_argument("formula_file")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--allow-staged",
        action="store_true",
        help="Acknowledge an intentionally staged formula source.",
    )
    args, pipeline_args = parser.parse_known_args(argv)

    formula_path = _formula_path(args.formula_file)
    formulas = parse_formula_markdown(formula_path)
    if len(formulas) != 1:
        raise RuntimeError("rebind refuses ambiguous multi-formula documents")
    source_text = formula_path.read_text(encoding="utf-8", errors="strict")
    _source, artifact = split_generated_pipeline_analysis(source_text)
    prior = parse_pipeline_analysis_manifest(artifact)
    if not isinstance(prior, dict) or prior.get("manifest_status"):
        raise RuntimeError("rebind requires one existing canonical manifest")

    staged, unstaged = _git_status(formula_path)
    if unstaged:
        raise RuntimeError("rebind refuses unstaged formula changes")
    if staged and not args.allow_staged:
        raise RuntimeError(
            "staged formula changes require explicit --allow-staged"
        )

    proposed, analysis = _fresh_artifact(formula_path, pipeline_args)
    diff = semantic_manifest_diff(prior, proposed)
    print(diff or "No semantic manifest changes.")
    if not args.apply:
        print("Dry run only; pass --apply after reviewing the diff.")
        return 0
    _append_pipeline_analysis(formula_path, analysis, proposed)
    print("Rebind applied and verified by re-reading the artifact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
