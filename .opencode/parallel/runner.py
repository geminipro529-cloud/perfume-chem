r"""Session-isolated parallel job runner for multi-window OpenCode.

Contract:
  Each job is scoped to OPENCODE_SESSION_ID (from env).
  Runner refuses to operate if that env var is missing.
  All writes are atomic (.tmp -> os.replace).
  Cross-process file locking via msvcrt.locking (Windows).

Usage:
  python -m runner submit --kind read --path <file> --reader flash
  python -m runner submit --kind brain --prompt <text> --files <paths...> --reader glm-max-flex
  python -m runner status <job_id>
  python -m runner collect <job_id>
  python -m runner list [--session <id>]
  python -m runner cleanup [--stale-minutes 30]
"""

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


STALE_LOCK_MINUTES = int(os.environ.get("STALE_LOCK_MINUTES", "30"))
JOBS_ROOT = pathlib.Path(__file__).resolve().parent / "jobs"
BRAIN_LEDGER = pathlib.Path(__file__).resolve().parent / "brain_ledger.jsonl"

# Make `engine.*` importable when runner is invoked directly (matches the
# repo-root sys.path convention documented in AGENTS.md).
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _session_id():
    sid = os.environ.get("OPENCODE_SESSION_ID")
    if not sid:
        raise SystemExit("OPENCODE_SESSION_ID not set — refusing to operate")
    return sid


def _job_dir(job_id=None):
    base = JOBS_ROOT / _session_id()
    if job_id:
        base = base / job_id
    base.mkdir(parents=True, exist_ok=True)
    return base


def _short_hash(data, n=8):
    return hashlib.sha256(data.encode()).hexdigest()[:n]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path, content):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(str(tmp), str(path))


def _acquire_lock(lock_path):
    try:
        if lock_path.exists():
            lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
            pid = lock_data.get("pid")
            created = lock_data.get("created_at", "")
            if pid and created:
                try:
                    created_dt = datetime.fromisoformat(created)
                    age_minutes = (datetime.now(timezone.utc) - created_dt).total_seconds() / 60
                except (ValueError, OSError):
                    age_minutes = float("inf")
                if age_minutes > STALE_LOCK_MINUTES and not _is_pid_alive(pid):
                    lock_path.unlink()
    except (json.JSONDecodeError, FileNotFoundError):
        pass

    lock_data = json.dumps(
        {
            "pid": os.getpid(),
            "created_at": _now_iso(),
            "session_id": _session_id(),
        }
    )

    if sys.platform == "win32":
        lf = open(str(lock_path), "a+")
        lf.seek(0)
        lf.truncate()
        lf.write(lock_data)
        lf.flush()
        msvcrt.locking(lf.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        lf = open(str(lock_path), "r+")
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lf.seek(0)
        lf.truncate()
        lf.write(lock_data)
        lf.flush()
    return lf


def _file_unlock(lf):
    try:
        if sys.platform == "win32":
            msvcrt.locking(lf.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
        lf.close()
    except Exception:
        pass


def _is_pid_alive(pid):
    try:
        if sys.platform == "win32":
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x0400, 0, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError):
        return False


def _write_status(job_dir, status, msg=""):
    _atomic_write(
        job_dir / "status.json",
        json.dumps({"status": status, "message": msg, "updated_at": _now_iso()}, indent=2),
    )


def cmd_submit(args):
    job_id = f"job_{_short_hash(args.prompt or args.path or str(time.time()))}"
    job_dir = _job_dir(job_id)

    lock_path = job_dir / "job.lock"
    lf = _acquire_lock(lock_path)

    try:
        _write_status(job_dir, "pending")

        if args.kind == "read":
            file_path = pathlib.Path(args.path).resolve()
            if not file_path.is_file():
                _write_status(job_dir, "failed", f"File not found: {args.path}")
                _file_unlock(lf)
                return

            content = file_path.read_text(encoding="utf-8", errors="replace")
            output = {
                "path": str(file_path),
                "lines": content.splitlines(),
                "sha256": hashlib.sha256(content.encode()).hexdigest(),
                "captured_at": _now_iso(),
                "line_count": len(content.splitlines()),
                "reader": args.reader,
            }

            _write_status(job_dir, "running")
            _atomic_write(job_dir / "output.json", json.dumps(output, indent=2, ensure_ascii=False))
            _write_status(job_dir, "complete")

        elif args.kind == "brain":
            _write_status(job_dir, "running")

            files_content = {}
            for fp in args.files or []:
                p = pathlib.Path(fp).resolve()
                if p.is_file():
                    files_content[p.name] = p.read_text(encoding="utf-8", errors="replace")

            if not os.environ.get("DEEPINFRA_API_KEY", ""):
                _write_status(job_dir, "failed", "DEEPINFRA_API_KEY not set")
                _file_unlock(lf)
                return

            messages = [
                {
                    "role": "system",
                    "content": "You are GLM-5.2 max, head perfumer/scientist/engineer. Respond with structured JSON: {reasoning, decision, references}.",
                },
                {
                    "role": "user",
                    "content": json.dumps({"prompt": args.prompt, "files": files_content}),
                },
            ]

            try:
                # Routed through engine.llm_cache.cached_chat so repeated
                # (prompt, files) tuples hit the local SQLite store instead of
                # paying DeepInfra again. The cache layer writes its own
                # ledger (cache/llm_cache_ledger.jsonl) with hit/miss and
                # $-saved tracking; brain_ledger.jsonl below preserves the
                # existing job-level usage ledger contract for old consumers.
                from engine.llm_cache import cached_chat

                result = cached_chat(
                    provider="deepinfra",
                    model="zai-org/GLM-5.2",
                    messages=messages,
                    temperature=0.0,
                    max_tokens=4096,
                    top_p=1.0,
                    thinking_mode="auto",
                    service_tier="flex",
                    ttl_days=7,
                )

                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})

                ledger_entry = {
                    "job_id": job_id,
                    "timestamp": _now_iso(),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "service_tier": "flex",
                }
                BRAIN_LEDGER.parent.mkdir(parents=True, exist_ok=True)
                with open(str(BRAIN_LEDGER), "a", encoding="utf-8") as ledger:
                    ledger.write(json.dumps(ledger_entry) + "\n")

                output = {
                    "reasoning": content,
                    "decision": "see reasoning",
                    "references": [],
                    "usage": usage,
                }
                _atomic_write(
                    job_dir / "output.json", json.dumps(output, indent=2, ensure_ascii=False)
                )
                _write_status(job_dir, "complete")

            except urllib.error.HTTPError as e:
                _write_status(job_dir, "failed", f"HTTP {e.code}: {e.reason}")
            except Exception as e:
                _write_status(job_dir, "failed", str(e))
        else:
            _write_status(job_dir, "failed", f"Unknown kind: {args.kind}")

    finally:
        _file_unlock(lf)

    print(job_id)


def cmd_status(args):
    job_dir = _job_dir(args.job_id)
    status_path = job_dir / "status.json"
    if not status_path.is_file():
        print(f"job {args.job_id} not found")
        return
    print(status_path.read_text(encoding="utf-8"))


def cmd_collect(args):
    job_dir = _job_dir(args.job_id)
    status_path = job_dir / "status.json"
    output_path = job_dir / "output.json"

    if not status_path.is_file():
        print(f"job {args.job_id} not found")
        return

    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"job {args.job_id}: corrupt status")
        return

    valid = status.get("status") in ("complete", "stale_reclaimed")
    if not valid:
        print(f"job {args.job_id} not complete (status: {status.get('status')})")
        return

    if not output_path.is_file():
        print(f"job {args.job_id}: no output (status said {status.get('status')})")
        return

    print(output_path.read_text(encoding="utf-8"))


def cmd_list(args):
    session_dir = JOBS_ROOT / (args.session or _session_id())
    if not session_dir.is_dir():
        print("no jobs")
        return
    for job_path in sorted(session_dir.iterdir()):
        if job_path.is_dir():
            status_path = job_path / "status.json"
            status = "unknown"
            if status_path.is_file():
                try:
                    status = json.loads(status_path.read_text(encoding="utf-8")).get("status", "?")
                except json.JSONDecodeError:
                    status = "corrupt"
            print(f"{job_path.name}  {status}")


def cmd_cleanup(args):
    stale_minutes = args.stale_minutes
    cleaned = 0
    for session_dir in JOBS_ROOT.iterdir():
        if not session_dir.is_dir():
            continue
        for job_path in session_dir.iterdir():
            if not job_path.is_dir():
                continue
            lock_path = job_path / "job.lock"
            if not lock_path.is_file():
                continue
            try:
                lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
                pid = lock_data.get("pid")
                created = lock_data.get("created_at", "")
                if pid and created:
                    created_dt = datetime.fromisoformat(created)
                    age_minutes = (datetime.now(timezone.utc) - created_dt).total_seconds() / 60
                    if age_minutes > stale_minutes and not _is_pid_alive(pid):
                        for f in job_path.iterdir():
                            f.unlink()
                        job_path.rmdir()
                        cleaned += 1
            except (json.JSONDecodeError, FileNotFoundError, ValueError):
                pass
    print(f"cleaned {cleaned} stale job(s)")


def main():
    parser = argparse.ArgumentParser(description="OpenCode parallel job runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sp = subparsers.add_parser("submit", help="Submit a new job")
    sp.add_argument("--kind", required=True, choices=["read", "brain"])
    sp.add_argument("--path", help="File path (read jobs)")
    sp.add_argument("--prompt", help="Brain prompt")
    sp.add_argument("--files", nargs="*", help="File paths for brain context")
    sp.add_argument("--reader", default="flash", help="Target reader/model")
    sp.set_defaults(func=cmd_submit)

    sp = subparsers.add_parser("status", help="Check job status")
    sp.add_argument("job_id")
    sp.set_defaults(func=cmd_status)

    sp = subparsers.add_parser("collect", help="Collect completed job output")
    sp.add_argument("job_id")
    sp.set_defaults(func=cmd_collect)

    sp = subparsers.add_parser("list", help="List jobs")
    sp.add_argument("--session", help="Session ID filter")
    sp.set_defaults(func=cmd_list)

    sp = subparsers.add_parser("cleanup", help="Clean up stale jobs")
    sp.add_argument("--stale-minutes", type=int, default=STALE_LOCK_MINUTES)
    sp.set_defaults(func=cmd_cleanup)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
