"""Execute frozen replacement-screen prompts as fresh ephemeral Sol xhigh runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT / "data" / "benchmarks" / "solforge" / "replacement_screen_v4" / "manifest.json"
)
DEFAULT_OUTPUT_ROOT = DEFAULT_MANIFEST.parent / "raw"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("phase") != "SCREEN":
        raise ValueError("manifest must be one frozen SCREEN object")
    unhashed = dict(payload)
    observed_manifest_sha256 = unhashed.pop("manifest_sha256", None)
    canonical = json.dumps(
        unhashed,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    if _sha256(canonical) != observed_manifest_sha256:
        raise ValueError("manifest internal hash mismatch")
    if payload.get("request_count") != len(payload.get("requests", ())):
        raise ValueError("manifest request count mismatch")
    return payload


def _existing_result(path: Path, dispatch_sha256: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("dispatch_sha256") != dispatch_sha256:
        raise ValueError(f"existing result has wrong dispatch hash: {path}")
    sidecar = path.with_suffix(".sha256")
    if not sidecar.exists():
        raise ValueError(f"existing result sidecar is missing: {path}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    if _sha256(path.read_bytes()) != expected:
        raise ValueError(f"existing result byte hash mismatch: {path}")
    return payload


def _execute_one(
    request: dict[str, Any],
    *,
    output_root: Path,
    model: str,
    reasoning_effort: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    request_id = request["request_id"]
    output_path = output_root / f"{request_id}.json"
    existing = _existing_result(output_path, request["dispatch_sha256"])
    if existing is not None:
        return {"request_id": request_id, "state": "REUSED_EXACT_RESULT"}

    started = datetime.now(UTC).isoformat()
    with tempfile.TemporaryDirectory(prefix=f"{request_id}-") as workdir_name:
        workdir = Path(workdir_name)
        last_message = workdir / "last-message.txt"
        command = [
            "codex",
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--color",
            "never",
            "--sandbox",
            "read-only",
            "--ask-for-approval",
            "never",
            "-m",
            model,
            "-c",
            f'model_reasoning_effort="{reasoning_effort}"',
            "-C",
            str(workdir),
            "-o",
            str(last_message),
            "-",
        ]
        completed = subprocess.run(
            command,
            input=request["dispatch_text"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
        output_text = (
            last_message.read_text(encoding="utf-8") if last_message.exists() else ""
        )
    completed_utc = datetime.now(UTC).isoformat()
    envelope = {
        "schema_version": "complexity_replacement_ephemeral_result_v1",
        "request_id": request_id,
        "case_id": request["case_id"],
        "module_id": request["module_id"],
        "phase": request["phase"],
        "role": request["role"],
        "arm": request["arm"],
        "prompt_sha256": request["prompt_sha256"],
        "dispatch_sha256": request["dispatch_sha256"],
        "model": model,
        "reasoning_effort": reasoning_effort,
        "execution_mode": "FRESH_EPHEMERAL_IGNORE_USER_CONFIG_AND_RULES",
        "started_utc": started,
        "completed_utc": completed_utc,
        "exit_code": completed.returncode,
        "output_text": output_text,
        "output_sha256": _sha256(output_text.encode("utf-8")),
        "stdout_sha256": _sha256(completed.stdout.encode("utf-8")),
        "stderr_sha256": _sha256(completed.stderr.encode("utf-8")),
        "stderr_tail": completed.stderr[-2000:],
        "authority": {
            "formula": False,
            "inventory": False,
            "physical_execution": False,
            "sensory": False,
            "safety": False,
            "purchase": False,
            "publication": False,
            "release": False,
        },
    }
    output_bytes = (
        json.dumps(envelope, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")
    output_root.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output_bytes)
    output_path.with_suffix(".sha256").write_text(
        f"{_sha256(output_bytes)}  {output_path.name}\n",
        encoding="ascii",
        newline="\n",
    )
    return {
        "request_id": request_id,
        "state": "COMPLETE" if completed.returncode == 0 and output_text else "FAILED",
        "exit_code": completed.returncode,
        "output_sha256": envelope["output_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--request-id", action="append", default=[])
    args = parser.parse_args()
    if not 1 <= args.max_workers <= 8:
        raise ValueError("max-workers must be from one to eight")
    manifest = _load_manifest(args.manifest.resolve())
    model_identity = manifest["model_identity"]
    requests = manifest["requests"]
    if args.request_id:
        selected = set(args.request_id)
        requests = [row for row in requests if row["request_id"] in selected]
        if {row["request_id"] for row in requests} != selected:
            raise ValueError("one or more selected request IDs are absent from the manifest")

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {
            executor.submit(
                _execute_one,
                request,
                output_root=args.output_root.resolve(),
                model=model_identity["model"],
                reasoning_effort=model_identity["reasoning_effort"],
                timeout_seconds=args.timeout_seconds,
            ): request["request_id"]
            for request in requests
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps(result, sort_keys=True), flush=True)
    failures = [row for row in results if row["state"] == "FAILED"]
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
