#!/usr/bin/env python3
"""Batch-gate ALL formula .md files in formulas/ (recursive) through
formula_release_gate.py.

Extracts concentrate volume and brief from formula metadata when present.
Skips non-formula files (_ prefix, prep_ prefix, files without formula tables).
Writes per-formula JSON output and aggregate summary. Handles failures gracefully.

Usage:
    python scripts/batch_gate_all_formulas.py                     # All formulas
    python scripts/batch_gate_all_formulas.py --subset 5           # First 5 only
    python scripts/batch_gate_all_formulas.py --workers 1          # Serial execution
    python scripts/batch_gate_all_formulas.py --brief vetiver_woody  # Override
    python scripts/batch_gate_all_formulas.py --timeout 90         # Custom timeout
    python scripts/batch_gate_all_formulas.py --dry-run            # Preview only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue, SimpleQueue

# Direct script execution puts ``scripts/`` rather than the repository root on
# ``sys.path``.  Establish the root before importing the authoritative parser.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.calibration.hashing import (
    authority_payload_sha256 as authority_payload_sha256,
)
from engine.calibration.hashing import (
    scientific_and_authority_payload_hashes,
)
from engine.calibration.hashing import (
    scientific_payload_sha256 as scientific_payload_sha256,
)
from scripts.verify_formula_workflow import parse_formula_markdown

try:
    import psutil
except ImportError:  # pragma: no cover - declared runtime dependency
    psutil = None

# ── Paths ──────────────────────────────────────────────────────────
FORMULAS_DIR = ROOT / "formulas"
OUTPUT_DIR = ROOT / ".omo" / "evidence" / "batch_results"

# Ensure OPENCODE_SESSION_ID is set for multi-window gate mode
if not os.environ.get("OPENCODE_SESSION_ID"):
    os.environ["OPENCODE_SESSION_ID"] = f"batch-{int(time.time())}"

# ── Constants ──────────────────────────────────────────────────────
DEFAULT_CONCENTRATE_UL = 6000
DEFAULT_BRIEF = "generic"
DEFAULT_TIMEOUT_S = 60
DEFAULT_WORKERS = 4
MAX_WORKERS = 8
MEMORY_SAMPLE_INTERVAL_S = 0.05
PERSISTENT_WORKER_SCHEMA = "perfume-chem-formula-gate-worker-v1"
WORKER_NUMERICAL_THREAD_LIMIT = "1"
_NUMERICAL_THREAD_ENV_KEYS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
)
SUPPORTED_BRIEFS = frozenset(
    {
        "auto",
        "generic",
        "layton_dna",
        "aromatic_fougere",
        "vetiver_woody",
        "floral_aldehydic_amber",
        "dhi_2011",
        "dhp_2014",
        "woody_floral_musk",
        "gourmand_floral",
        "prada_lhomme",
    }
)

# Stem prefixes to skip (case-insensitive match on filename without ext)
SKIP_STEM_PREFIXES = ("_", "prep_")

# Name-contains patterns to skip (lowercase match on full filename)
SKIP_NAME_CONTAINS = ("_pipeline.md",)

# ── Brief keyword → pipeline brief-enum mapping ────────────────────
BRIEF_KEYWORD_MAP: list[tuple[tuple[str, ...], str]] = [
    (("layton", "pdm"), "layton_dna"),
    (("aromatic fougère", "aromatic fougere"), "aromatic_fougere"),
    (("vetiver",), "vetiver_woody"),
    (("dhi", "dior homme intense"), "dhi_2011"),
    (("dhp", "dior homme parfum"), "dhp_2014"),
    (("prada", "l'homme"), "prada_lhomme"),
    (("gourmand",), "gourmand_floral"),
    (("woody floral musk", "woody floral"), "woody_floral_musk"),
    (("floral aldehydic",), "floral_aldehydic_amber"),
]


# ── Metadata extraction ────────────────────────────────────────────


def _parse_number(raw: str) -> int | None:
    """Parse e.g. '5,155' or '~3,000' or '6 000' to int."""
    cleaned = raw.strip().lstrip("~≈").replace(",", "").replace(" ", "")
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def extract_concentrate_ul(body: str) -> int | None:
    """Extract concentrate volume in µL from formula body text."""
    patterns = [
        r"\*\*Concentrate\s+Volume:\*\*\s*~?\s*([\d,]+)\s*[u\u00b5]L",
        r"\*\*Concentrate:\*\*\s*~?\s*([\d,]+)\s*[u\u00b5]L",
        r"\*\*Total\s+concentrate:\*\*\s*~?\s*([\d,]+)\s*[u\u00b5]L",
        r"\*\*Target\s+Concentrate:\*\*\s*~?\s*([\d,]+)\s*[u\u00b5]L",
        r"\*\*Active\s+concentrate:\*\*\s*~?\s*([\d,]+)\s*[u\u00b5]L",
        r"[Cc]oncentrate\s+is\s+~?\s*([\d,]+)\s*[u\u00b5]L",
        r"Concentrate:\*\*\s*~?\s*([\d,]+)\s*[u\u00b5]L",
    ]
    for pat in patterns:
        m = re.search(pat, body)
        if m:
            val = _parse_number(m.group(1))
            if val is not None and 100 <= val <= 100_000:
                return val
    return None


def extract_brief(body: str) -> str | None:
    """Extract brief/family from formula body text."""
    # Explicit family archetype
    m = re.search(r"\*\*Family\s+archetype:\*\*\s*`?([A-Za-z0-9_.-]+)`?", body)
    if m and m.group(1).strip() in SUPPORTED_BRIEFS:
        return m.group(1).strip()

    # Free-text Brief / Family / Brief axis
    for label in ("Brief", "Family", "Brief axis"):
        m = re.search(rf"\*\*{label}:\*\*\s*(.+?)(?:\n|$)", body, re.IGNORECASE)
        if m:
            return _map_brief_keywords(m.group(1).strip())

    return None


def extract_family_archetype(body: str) -> str | None:
    """Return an exact archetype that must use the dedicated CLI argument."""

    match = re.search(
        r"\*\*Family\s+archetype:\*\*\s*`?([A-Za-z0-9_.-]+)`?",
        body,
    )
    if not match:
        return None
    value = match.group(1).strip()
    return None if value in SUPPORTED_BRIEFS else value


def _map_brief_keywords(text: str) -> str:
    """Map free-text brief description to a known pipeline brief enum."""
    lower = text.lower()
    for keywords, brief_val in BRIEF_KEYWORD_MAP:
        if any(kw in lower for kw in keywords):
            return brief_val
    return DEFAULT_BRIEF


def extract_metadata(body: str) -> dict:
    """Return {concentrate_ul, brief_text} from formula body text."""
    return {
        "concentrate_ul": extract_concentrate_ul(body),
        "brief_text": extract_brief(body),
        "family_archetype": extract_family_archetype(body),
    }


# ── Formula detection ───────────────────────────────────────────────


def _has_formula_table(body: str) -> bool:
    """Quick heuristic: does this markdown file contain a formula table?

    Looks for markdown tables with ingredient-like rows: text in col 1-2,
    dilution-like col, numeric amount in a later column. Must have at least
    3 data rows. Detects both 'Ingredient' and 'Material' header styles.
    """
    # Look for a table header row containing ingredient/material + dilution/amount
    header_pattern = (
        r"(?i)\|\s*(?:#\s*\|)?\s*"
        r"(?:ingredient|material|component)\s*\|"
    )
    if not re.search(header_pattern, body):
        return False

    # Count rows that look like formula entries:
    # | anything | something | number (possibly with unit) | ...
    # Rows where column 3 or 4 contains a recognisable amount value.
    data_row = re.compile(r"\|\s*[^|]+\s*\|\s*[^|]+\s*\|\s*[\d,.]+\s*[u\u00b5]?[Ll]?\s*\|")
    data_rows = [line for line in body.splitlines() if data_row.search(line)]
    return len(data_rows) >= 3


def should_skip_file(filepath: Path) -> tuple[bool, str]:
    """Return (skip: bool, reason: str)."""
    stem_lower = filepath.stem.lower()
    name_lower = filepath.name.lower()

    for prefix in SKIP_STEM_PREFIXES:
        if stem_lower.startswith(prefix):
            return True, f"stem prefix '{prefix}'"

    for substr in SKIP_NAME_CONTAINS:
        if substr in name_lower:
            return True, f"name contains '{substr}'"

    return False, ""


def discover_formula_files() -> tuple[list[Path], list[dict]]:
    """Scan formulas/ recursively; return (formula_paths, skipped_info)."""
    all_md = sorted(FORMULAS_DIR.rglob("*.md"), key=lambda p: str(p).lower())
    formulas: list[Path] = []
    skipped: list[dict] = []

    for fp in all_md:
        rel = str(fp.relative_to(ROOT))

        skip, reason = should_skip_file(fp)
        if skip:
            skipped.append({"file": rel, "reason": reason})
            continue

        try:
            body = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            skipped.append({"file": rel, "reason": "read error"})
            continue

        if not _has_formula_table(body):
            skipped.append({"file": rel, "reason": "no formula table detected"})
            continue

        try:
            parsed_formulas = parse_formula_markdown(fp)
        except Exception as exc:
            skipped.append(
                {
                    "file": rel,
                    "reason": f"authoritative parser error: {type(exc).__name__}",
                }
            )
            continue
        if not parsed_formulas:
            skipped.append(
                {
                    "file": rel,
                    "reason": "authoritative parser found no formulas",
                }
            )
            continue
        duplicate_identity = False
        for parsed_formula in parsed_formulas:
            names = [
                str(name).strip().casefold()
                for name in dict(parsed_formula.get("ingredients_ul", {}) or {})
                if str(name).strip()
            ]
            if len(set(names)) != len(names):
                duplicate_identity = True
                break
        if duplicate_identity:
            skipped.append(
                {
                    "file": rel,
                    "reason": (
                        "unsupported collection: parser produced duplicate "
                        "material identities"
                    ),
                }
            )
            continue

        formulas.append(fp)

    return formulas, skipped


# ── Gate runner ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class GateJob:
    """Immutable path and optional CLI overrides for one gate subprocess."""

    index: int
    filepath: Path
    concentrate_ul: int | None
    brief: str | None


@dataclass(frozen=True)
class GateExecution:
    """Isolated result from exactly one formula-gate subprocess."""

    job: GateJob
    concentrate_ul: int
    brief: str
    gate_output: dict
    elapsed_s: float
    family_archetype: str | None = None
    scientific_payload_sha256: str | None = None
    authority_payload_sha256: str | None = None


@dataclass(frozen=True)
class GateRunnerResult:
    """One worker result plus hashes calculated inside that worker lane."""

    gate_output: dict
    scientific_payload_sha256: str | None = None
    authority_payload_sha256: str | None = None


class ProcessTreeMemoryMonitor:
    """Sample aggregate RSS for the runner and its gate subprocesses."""

    def __init__(self, interval_s: float = MEMORY_SAMPLE_INTERVAL_S) -> None:
        self.interval_s = interval_s
        self.peak_rss_bytes = 0
        self.sample_count = 0
        self.sample_errors = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def available(self) -> bool:
        return psutil is not None

    def _sample(self) -> None:
        if psutil is None:
            return
        try:
            root = psutil.Process(os.getpid())
            processes = [root, *root.children(recursive=True)]
            seen: set[int] = set()
            total_rss = 0
            for process in processes:
                if process.pid in seen:
                    continue
                seen.add(process.pid)
                try:
                    total_rss += int(process.memory_info().rss)
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                    continue
            self.peak_rss_bytes = max(self.peak_rss_bytes, total_rss)
            self.sample_count += 1
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            self.sample_errors += 1

    def _run(self) -> None:
        while not self._stop.wait(self.interval_s):
            self._sample()

    def start(self) -> None:
        self._sample()
        if not self.available:
            return
        self._thread = threading.Thread(
            target=self._run,
            name="batch-process-tree-memory",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> dict[str, object]:
        self._sample()
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval_s * 4))
        if not self.available:
            return {
                "measurement_state": "UNAVAILABLE_DEPENDENCY",
                "peak_rss_bytes": None,
                "peak_rss_mib": None,
                "sample_count": 0,
                "sample_errors": 0,
            }
        return {
            "measurement_state": "MEASURED_PROCESS_TREE_RSS",
            "peak_rss_bytes": self.peak_rss_bytes,
            "peak_rss_mib": round(self.peak_rss_bytes / (1024 * 1024), 3),
            "sample_count": self.sample_count,
            "sample_errors": self.sample_errors,
            "sampling_interval_seconds": self.interval_s,
        }


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _snapshot_paths(jobs: list[GateJob]) -> list[Path]:
    """Return the deterministic, read-only input surface for one batch run."""

    paths = {job.filepath.resolve() for job in jobs}
    paths.update(
        path.resolve()
        for path in (
            Path(__file__),
            ROOT / "scripts" / "formula_release_gate.py",
            ROOT / "inventory.txt",
        )
        if path.is_file()
    )
    for pattern in (
        "engine/**/*.py",
        "future_modules/**/*.py",
        "data/**/*.json",
        "data/**/*.yaml",
        "data/**/*.yml",
        "data/**/*.csv",
        "configs/**/*.json",
        "configs/**/*.yaml",
        "configs/**/*.yml",
    ):
        paths.update(path.resolve() for path in ROOT.glob(pattern) if path.is_file())
    return sorted(paths, key=lambda path: path.as_posix().lower())


def freeze_source_snapshot(jobs: list[GateJob]) -> dict:
    """Hash exact formula, implementation, inventory, and reference bytes."""

    records = []
    for path in _snapshot_paths(jobs):
        try:
            payload = path.read_bytes()
            relative = path.relative_to(ROOT.resolve()).as_posix()
            records.append(
                {
                    "path": relative,
                    "size_bytes": len(payload),
                    "sha256": _sha256_bytes(payload),
                    "state": "AVAILABLE",
                }
            )
        except (OSError, ValueError) as exc:
            records.append(
                {
                    "path": str(path),
                    "size_bytes": None,
                    "sha256": None,
                    "state": "UNAVAILABLE",
                    "reason": type(exc).__name__,
                }
            )
    return {
        "records": records,
        "snapshot_sha256": _sha256_bytes(_canonical_json_bytes(records)),
    }


def create_run_output_dir(base: Path = OUTPUT_DIR) -> Path:
    """Create an empty, unique output directory for exactly one invocation."""

    base.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="run-", dir=str(base))).resolve()


def _gate_argv(
    filepath: Path,
    concentrate_ul: int,
    brief: str,
    family_archetype: str | None = None,
) -> list[str]:
    """Return the closed, non-writing formula-gate argument packet."""

    argv = [
        "--formula-file",
        str(filepath),
        "--expected-concentrate-ul",
        str(concentrate_ul),
        "--brief",
        brief,
        "--json",
        "--no-append-analysis",
        # Batch reports are diagnostic artifacts, not canonical admission.
        # Every worker must avoid concurrent writes to the shared JSONL audit.
        "--no-audit",
    ]
    if family_archetype:
        argv.extend(["--family-archetype", family_archetype])
    return argv


def _worker_environment() -> dict[str, str]:
    """Return a bounded environment for one process-isolated gate lane.

    The formula gate imports NumPy/OpenBLAS.  Without an explicit limit each
    child may create a numerical thread for every logical CPU, so four Python
    lanes can become 32 runnable BLAS threads on an eight-CPU host.  Formula
    gates operate on small vectors and do not benefit from nested BLAS
    parallelism.  Pinning the numerical libraries to one thread keeps the
    public worker count authoritative and prevents oversubscription while
    leaving the parent process environment untouched.
    """

    environment = os.environ.copy()
    for key in _NUMERICAL_THREAD_ENV_KEYS:
        environment[key] = WORKER_NUMERICAL_THREAD_LIMIT
    return environment


def run_gate(
    filepath: Path,
    concentrate_ul: int,
    brief: str,
    timeout_s: int,
    family_archetype: str | None = None,
) -> dict:
    """Run formula_release_gate.py on one formula; return parsed JSON or error dict.

    Uses --no-append-analysis to avoid modifying formula files.
    """
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "formula_release_gate.py"),
        *_gate_argv(filepath, concentrate_ul, brief, family_archetype),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(ROOT),
            env=_worker_environment(),
        )

        # Try stdout JSON regardless of exit code
        if proc.stdout.strip():
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError:
                pass

        # Construct error report
        stderr_tail = (proc.stderr or "(no stderr)")[-800:]
        return {
            "_error": True,
            "_error_type": "exit_code",
            "_exit_code": proc.returncode,
            "_stderr_tail": stderr_tail,
        }

    except subprocess.TimeoutExpired:
        return {"_error": True, "_error_type": "timeout", "_timeout_s": timeout_s}
    except Exception as exc:
        return {"_error": True, "_error_type": "exception", "_exception": str(exc)}


class PersistentGateWorker:
    """One source-bound release-gate process serving sequential formula jobs.

    A lane handles only one formula at a time.  A timeout or malformed receipt
    kills that exact worker process and is never retried for the current
    formula; a fresh process may serve a later formula.  This preserves the
    one-attempt contract while amortizing Python imports and immutable lookup
    caches across the batch.
    """

    def __init__(self, *, startup_timeout_s: int = 30) -> None:
        self._startup_timeout_s = max(1, int(startup_timeout_s))
        self._process: subprocess.Popen[str] | None = None
        self._responses: Queue[str | None] = Queue()
        self._stderr_tail: deque[str] = deque(maxlen=20)
        self._sequence = 0
        self.ready_receipt: dict[str, object] = {}
        self._bound_repository_receipt: tuple[str, str] | None = None
        self._start()

    def _start(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return
        self._responses = Queue()
        self._stderr_tail = deque(maxlen=20)
        popen_kwargs: dict[str, object] = {}
        if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        process = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "scripts" / "formula_release_gate.py"),
                "--batch-worker-jsonl",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(ROOT),
            env=_worker_environment(),
            **popen_kwargs,
        )
        self._process = process
        threading.Thread(
            target=self._read_stdout,
            args=(process,),
            name=f"formula-gate-worker-{process.pid}-stdout",
            daemon=True,
        ).start()
        threading.Thread(
            target=self._read_stderr,
            args=(process,),
            name=f"formula-gate-worker-{process.pid}-stderr",
            daemon=True,
        ).start()
        try:
            ready = self._next_receipt(self._startup_timeout_s)
        except Exception:
            self._terminate()
            raise
        if (
            ready.get("schema") != PERSISTENT_WORKER_SCHEMA
            or ready.get("type") != "READY"
            or not isinstance(ready.get("repository_evidence_hashes"), dict)
        ):
            self._terminate()
            raise RuntimeError("Persistent gate worker returned an invalid READY receipt")
        repository_receipt = (
            json.dumps(
                ready["repository_evidence_hashes"],
                sort_keys=True,
                separators=(",", ":"),
            ),
            str(ready.get("repository_commit")),
        )
        if (
            self._bound_repository_receipt is not None
            and repository_receipt != self._bound_repository_receipt
        ):
            self._terminate()
            raise RuntimeError(
                "Replacement worker did not bind the original repository snapshot"
            )
        self._bound_repository_receipt = repository_receipt
        self.ready_receipt = ready

    def _read_stdout(self, process: subprocess.Popen[str]) -> None:
        stream = process.stdout
        if stream is None:
            self._responses.put(None)
            return
        try:
            for line in stream:
                self._responses.put(line)
        finally:
            self._responses.put(None)

    def _read_stderr(self, process: subprocess.Popen[str]) -> None:
        stream = process.stderr
        if stream is None:
            return
        for line in stream:
            self._stderr_tail.append(line.rstrip())

    def _next_receipt(self, timeout_s: int) -> dict[str, object]:
        try:
            line = self._responses.get(timeout=timeout_s)
        except Empty as exc:
            raise TimeoutError("Persistent gate worker response timed out") from exc
        if line is None:
            detail = "\n".join(self._stderr_tail)[-800:] or "no stderr"
            raise RuntimeError(f"Persistent gate worker exited: {detail}")
        try:
            receipt = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Persistent gate worker returned malformed JSON") from exc
        if not isinstance(receipt, dict):
            raise RuntimeError("Persistent gate worker receipt must be an object")
        return receipt

    def _terminate(self) -> None:
        process = self._process
        self._process = None
        if process is None or process.poll() is not None:
            return
        children = []
        if psutil is not None:
            try:
                children = psutil.Process(process.pid).children(recursive=True)
                for child in children:
                    child.terminate()
            except (psutil.Error, OSError):
                children = []
        try:
            process.terminate()
            process.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
                process.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                pass
        if children and psutil is not None:
            _, alive = psutil.wait_procs(children, timeout=1)
            for child in alive:
                try:
                    child.kill()
                except psutil.Error:
                    pass

    def run_gate(
        self,
        filepath: Path,
        concentrate_ul: int,
        brief: str,
        timeout_s: int,
        family_archetype: str | None = None,
    ) -> dict | GateRunnerResult:
        if self._process is None or self._process.poll() is not None:
            try:
                self._start()
            except Exception as exc:
                return {
                    "_error": True,
                    "_error_type": "worker_startup",
                    "_exception": str(exc),
                }
        process = self._process
        assert process is not None
        assert process.stdin is not None
        self._sequence += 1
        request_id = f"{process.pid}:{self._sequence}"
        request = {
            "schema": PERSISTENT_WORKER_SCHEMA,
            "type": "RUN",
            "request_id": request_id,
            "argv": _gate_argv(
                filepath,
                concentrate_ul,
                brief,
                family_archetype,
            ),
        }
        try:
            process.stdin.write(
                json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
            process.stdin.flush()
            receipt = self._next_receipt(timeout_s)
        except TimeoutError:
            self._terminate()
            return {"_error": True, "_error_type": "timeout", "_timeout_s": timeout_s}
        except (OSError, RuntimeError) as exc:
            self._terminate()
            return {
                "_error": True,
                "_error_type": "worker_transport",
                "_exception": str(exc),
            }

        if (
            receipt.get("schema") != PERSISTENT_WORKER_SCHEMA
            or receipt.get("request_id") != request_id
        ):
            self._terminate()
            return {
                "_error": True,
                "_error_type": "invalid_worker_receipt",
            }
        if receipt.get("type") == "RESULT" and isinstance(
            receipt.get("gate_output"), dict
        ):
            scientific_hash = receipt.get("scientific_payload_sha256")
            authority_hash = receipt.get("authority_payload_sha256")
            for name, value in (
                ("scientific_payload_sha256", scientific_hash),
                ("authority_payload_sha256", authority_hash),
            ):
                if value is not None and not re.fullmatch(r"[0-9a-f]{64}", str(value)):
                    self._terminate()
                    return {
                        "_error": True,
                        "_error_type": "invalid_worker_receipt",
                        "_exception": f"worker returned malformed {name}",
                    }
            return GateRunnerResult(
                gate_output=dict(receipt["gate_output"]),
                scientific_payload_sha256=(
                    str(scientific_hash) if scientific_hash is not None else None
                ),
                authority_payload_sha256=(
                    str(authority_hash) if authority_hash is not None else None
                ),
            )

        self._terminate()
        return {
            "_error": True,
            "_error_type": "worker_error",
            "_exception": str(receipt.get("message", "worker returned no result")),
        }

    def close(self) -> None:
        process = self._process
        if process is None or process.poll() is not None:
            self._process = None
            return
        try:
            assert process.stdin is not None
            self._sequence += 1
            process.stdin.write(
                json.dumps(
                    {
                        "schema": PERSISTENT_WORKER_SCHEMA,
                        "type": "SHUTDOWN",
                        "request_id": f"{process.pid}:{self._sequence}",
                    },
                    separators=(",", ":"),
                )
                + "\n"
            )
            process.stdin.flush()
            process.wait(timeout=5)
            self._process = None
        except (OSError, subprocess.TimeoutExpired):
            self._terminate()


def _execute_gate_job(
    job: GateJob,
    timeout_s: int,
    *,
    gate_runner=None,
) -> GateExecution:
    """Execute one job once, preserving per-formula error isolation."""

    try:
        body = job.filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        meta = {"concentrate_ul": None, "brief_text": None}
    else:
        meta = extract_metadata(body)

    concentrate_ul = job.concentrate_ul or meta["concentrate_ul"] or DEFAULT_CONCENTRATE_UL
    family_archetype = None if job.brief else meta["family_archetype"]
    brief = job.brief or meta["brief_text"] or DEFAULT_BRIEF
    started_at = time.monotonic()
    runner = gate_runner or run_gate
    try:
        if family_archetype:
            runner_result = runner(
                job.filepath,
                concentrate_ul,
                brief,
                timeout_s,
                family_archetype=family_archetype,
            )
        else:
            runner_result = runner(
                job.filepath,
                concentrate_ul,
                brief,
                timeout_s,
            )
    except Exception as exc:
        runner_result = {
            "_error": True,
            "_error_type": "exception",
            "_exception": str(exc),
        }
    if isinstance(runner_result, GateRunnerResult):
        gate_output = runner_result.gate_output
        scientific_hash = runner_result.scientific_payload_sha256
        authority_hash = runner_result.authority_payload_sha256
    else:
        gate_output = runner_result
        scientific_hash = None
        authority_hash = None
    return GateExecution(
        job=job,
        concentrate_ul=concentrate_ul,
        brief=brief,
        gate_output=gate_output,
        elapsed_s=time.monotonic() - started_at,
        family_archetype=family_archetype,
        scientific_payload_sha256=scientific_hash,
        authority_payload_sha256=authority_hash,
    )


def _ordered_gate_executions(
    jobs: list[GateJob],
    *,
    timeout_s: int,
    workers: int,
    persistent: bool = False,
) -> Iterator[GateExecution]:
    """Yield executions in completion order with a bounded submission window.

    ``workers=1`` deliberately uses the direct serial path. For parallel runs,
    at most ``workers`` subprocess jobs (and their result payloads) are queued at
    once. A completed worker is replaced immediately. The caller sorts the final
    manifest by discovery index, so scheduling cannot change result identity.
    """

    if persistent:
        if not jobs:
            return
        lane_count = min(workers, len(jobs))
        lane_workers: list[PersistentGateWorker] = []
        try:
            try:
                if lane_count == 1:
                    lane_workers = [
                        PersistentGateWorker(
                            startup_timeout_s=max(30, timeout_s)
                        )
                    ]
                else:
                    startup_workers: list[PersistentGateWorker] = []
                    startup_errors: list[Exception] = []
                    with ThreadPoolExecutor(
                        max_workers=lane_count,
                        thread_name_prefix="formula-gate-startup",
                    ) as startup_executor:
                        startup_futures = [
                            startup_executor.submit(
                                PersistentGateWorker,
                                startup_timeout_s=max(30, timeout_s),
                            )
                            for _ in range(lane_count)
                        ]
                        for startup_future in startup_futures:
                            try:
                                startup_workers.append(startup_future.result())
                            except Exception as exc:
                                startup_errors.append(exc)
                    lane_workers = startup_workers
                    if startup_errors:
                        raise RuntimeError(
                            "Persistent gate worker startup failed: "
                            f"{startup_errors[0]}"
                        )
                evidence_receipts = {
                    json.dumps(
                        worker.ready_receipt.get("repository_evidence_hashes"),
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    for worker in lane_workers
                }
                commit_receipts = {
                    str(worker.ready_receipt.get("repository_commit"))
                    for worker in lane_workers
                }
                if len(evidence_receipts) != 1 or len(commit_receipts) != 1:
                    raise RuntimeError(
                        "Persistent workers did not bind the same repository snapshot"
                    )
            except Exception as exc:
                for worker in lane_workers:
                    worker.close()
                for job in jobs:
                    yield GateExecution(
                        job=job,
                        concentrate_ul=job.concentrate_ul or DEFAULT_CONCENTRATE_UL,
                        brief=job.brief or DEFAULT_BRIEF,
                        gate_output={
                            "_error": True,
                            "_error_type": "worker_startup",
                            "_exception": str(exc),
                        },
                        elapsed_s=0.0,
                    )
                return

            if lane_count == 1:
                worker = lane_workers[0]
                for job in jobs:
                    yield _execute_gate_job(
                        job,
                        timeout_s,
                        gate_runner=worker.run_gate,
                    )
                return

            with ThreadPoolExecutor(
                max_workers=lane_count,
                thread_name_prefix="formula-gate-persistent",
            ) as executor:
                pending: dict[
                    Future[GateExecution], tuple[GateJob, PersistentGateWorker]
                ] = {}
                completed: SimpleQueue[Future[GateExecution]] = SimpleQueue()
                next_job = 0

                def submit(job: GateJob, worker: PersistentGateWorker) -> None:
                    future = executor.submit(
                        _execute_gate_job,
                        job,
                        timeout_s,
                        gate_runner=worker.run_gate,
                    )
                    pending[future] = (job, worker)
                    future.add_done_callback(completed.put)

                for worker in lane_workers:
                    submit(jobs[next_job], worker)
                    next_job += 1

                while pending:
                    future = completed.get()
                    job, worker = pending.pop(future)
                    try:
                        execution = future.result()
                    except Exception as exc:
                        execution = GateExecution(
                            job=job,
                            concentrate_ul=(
                                job.concentrate_ul or DEFAULT_CONCENTRATE_UL
                            ),
                            brief=job.brief or DEFAULT_BRIEF,
                            gate_output={
                                "_error": True,
                                "_error_type": "exception",
                                "_exception": str(exc),
                            },
                            elapsed_s=0.0,
                        )
                    if next_job < len(jobs):
                        submit(jobs[next_job], worker)
                        next_job += 1
                    # Refill the freed lane before handing the large result to
                    # the caller for hashing and artifact persistence.  This
                    # overlaps deterministic parent-side serialization with
                    # the next formula instead of leaving a worker idle.
                    yield execution
        finally:
            for worker in lane_workers:
                worker.close()
        return

    if workers == 1:
        for job in jobs:
            yield _execute_gate_job(job, timeout_s)
        return

    with ThreadPoolExecutor(
        max_workers=workers,
        thread_name_prefix="formula-gate",
    ) as executor:
        pending: dict[Future[GateExecution], GateJob] = {}
        completed: SimpleQueue[Future[GateExecution]] = SimpleQueue()
        next_job = 0

        def submit(job: GateJob) -> None:
            future = executor.submit(_execute_gate_job, job, timeout_s)
            pending[future] = job
            future.add_done_callback(completed.put)

        while next_job < len(jobs) and len(pending) < workers:
            job = jobs[next_job]
            submit(job)
            next_job += 1

        while pending:
            future = completed.get()
            job = pending.pop(future)
            try:
                execution = future.result()
            except Exception as exc:
                execution = GateExecution(
                    job=job,
                    concentrate_ul=job.concentrate_ul or DEFAULT_CONCENTRATE_UL,
                    brief=job.brief or DEFAULT_BRIEF,
                    gate_output={
                        "_error": True,
                        "_error_type": "exception",
                        "_exception": str(exc),
                    },
                    elapsed_s=0.0,
                )

            if next_job < len(jobs):
                next_pending = jobs[next_job]
                submit(next_pending)
                next_job += 1
            yield execution


def _parse_worker_count(raw: str) -> int:
    """Argparse type enforcing the bounded worker contract."""

    try:
        workers = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("workers must be an integer") from exc
    if not 1 <= workers <= MAX_WORKERS:
        raise argparse.ArgumentTypeError(f"workers must be between 1 and {MAX_WORKERS}")
    return workers


def classify_overall(gate_output: dict) -> str:
    """PASS | WARN | FAIL | ERROR."""
    if gate_output.get("_error"):
        return "ERROR"
    overall = gate_output.get("overall", "")
    if overall in ("PASS", "WARN", "FAIL"):
        return overall
    return "ERROR"


def collect_failed_gates(gate_output: dict) -> list[str]:
    """Return sorted list of FAIL/WARN gate names from gate output."""
    names: set[str] = set()
    for formula in gate_output.get("formulas", []):
        for gate in formula.get("gates", []):
            if gate.get("status") in ("FAIL", "WARN"):
                names.add(gate.get("gate", "?"))
    return sorted(names)


# ── Main ─────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(
        description="Batch-gate all formula .md files recursively",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python scripts/batch_gate_all_formulas.py
  python scripts/batch_gate_all_formulas.py --subset 5
  python scripts/batch_gate_all_formulas.py --workers 1
  python scripts/batch_gate_all_formulas.py --brief vetiver_woody
  python scripts/batch_gate_all_formulas.py --concentrate-ul 3000 --timeout 90
  python scripts/batch_gate_all_formulas.py --dry-run
""",
    )
    parser.add_argument(
        "--subset",
        type=int,
        default=0,
        metavar="N",
        help="Only process first N formulas (0=all)",
    )
    parser.add_argument(
        "--brief",
        type=str,
        default=None,
        help="Brief override for ALL formulas (default: auto-detect, fallback generic)",
    )
    parser.add_argument(
        "--concentrate-ul",
        type=int,
        default=None,
        metavar="UL",
        help="Concentrate volume override for ALL (default: auto-detect, fallback 6000)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_S,
        metavar="SECONDS",
        help=f"Per-formula timeout in seconds (default: {DEFAULT_TIMEOUT_S})",
    )
    parser.add_argument(
        "--workers",
        type=_parse_worker_count,
        default=DEFAULT_WORKERS,
        metavar="N",
        help=(
            f"Concurrent formula-gate subprocesses (default: {DEFAULT_WORKERS}; "
            f"bounded 1-{MAX_WORKERS}; 1=serial)"
        ),
    )
    parser.add_argument(
        "--execution-mode",
        choices=("persistent", "isolated"),
        default="persistent",
        help=(
            "Worker lifecycle (default: persistent). Persistent workers reuse "
            "source-bound read-only caches; isolated starts one process per formula."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List formulas that would be gated without running",
    )
    args = parser.parse_args(argv)

    if not FORMULAS_DIR.is_dir():
        print(f"ERROR: formulas directory not found: {FORMULAS_DIR}", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Discover ─────────────────────────────────────────────────
    formula_files, skipped = discover_formula_files()

    print(f"Scan: {len(formula_files) + len(skipped)} total .md files in formulas/")
    print(f"  Skipped: {len(skipped)}")
    print(f"  To gate: {len(formula_files)} formula files")
    print()

    if args.subset > 0:
        formula_files = formula_files[: args.subset]
        print(f"  (--subset {args.subset}: processing first {len(formula_files)} only)")
        print()

    if args.dry_run:
        print("Would gate these files (metadata auto-detected):")
        for i, fp in enumerate(formula_files):
            rel = fp.relative_to(ROOT)
            body = fp.read_text(encoding="utf-8", errors="replace")
            meta = extract_metadata(body)
            conc = args.concentrate_ul or meta["concentrate_ul"] or DEFAULT_CONCENTRATE_UL
            brief = args.brief or meta["brief_text"] or DEFAULT_BRIEF
            family_archetype = None if args.brief else meta["family_archetype"]
            print(f"  {i + 1:3d}. {rel}")
            print(
                f"       brief={brief}  archetype={family_archetype or '-'}  "
                f"conc={conc} uL"
            )
        return 0

    jobs: list[GateJob] = []
    for i, fp in enumerate(formula_files):
        jobs.append(
            GateJob(
                index=i,
                filepath=fp,
                concentrate_ul=args.concentrate_ul,
                brief=args.brief,
            )
        )

    run_output_dir = create_run_output_dir(OUTPUT_DIR)
    opening_snapshot = freeze_source_snapshot(jobs)
    opening_formula_hashes = {
        str(record["path"]): record.get("sha256")
        for record in opening_snapshot["records"]
        if str(record["path"]).startswith("formulas/")
    }

    # ── Process ───────────────────────────────────────────────────
    summary: dict = {
        "schema_version": "perfume-chem-batch-result-v2",
        "total_formulas": len(jobs),
        "passed": 0,
        "warned": 0,
        "failed": 0,
        "errors": 0,
        "formulas": [],
        "skipped": skipped,
        "config": {
            "brief_override": args.brief,
            "concentrate_ul_override": args.concentrate_ul,
            "timeout_s": args.timeout,
            "workers": args.workers,
            "execution_mode": args.execution_mode,
            "worker_audit": "DISABLED",
            "numerical_threads_per_worker": int(WORKER_NUMERICAL_THREAD_LIMIT),
        },
        "run_output_directory": str(run_output_dir),
        "opening_source_snapshot_sha256": opening_snapshot["snapshot_sha256"],
    }

    memory_monitor = ProcessTreeMemoryMonitor()
    memory_monitor.start()
    started_at = time.monotonic()
    last_heartbeat = started_at
    manifest_entries: list[dict] = []
    completed_count = 0

    executions = _ordered_gate_executions(
        jobs,
        timeout_s=args.timeout,
        workers=args.workers,
        persistent=args.execution_mode == "persistent",
    )
    for execution in executions:
        completed_count += 1
        job = execution.job
        i = job.index
        fp = job.filepath
        rel = fp.relative_to(ROOT)

        # ── Metadata ────────────────────────────────────────────
        concentrate_ul = execution.concentrate_ul
        brief = execution.brief
        family_archetype = execution.family_archetype

        # ── Gate ────────────────────────────────────────────────
        print(f"[{i + 1:3d}/{len(jobs)}] {rel}", flush=True)
        print(
            f"       brief={brief}  archetype={family_archetype or '-'}  "
            f"conc={concentrate_ul} uL",
            flush=True,
        )

        gate_output = execution.gate_output
        elapsed = execution.elapsed_s

        status = classify_overall(gate_output)
        failed_gates = collect_failed_gates(gate_output)

        if status == "PASS":
            summary["passed"] += 1
        elif status == "WARN":
            summary["warned"] += 1
        elif status == "FAIL":
            summary["failed"] += 1
        else:
            summary["errors"] += 1

        # ── Console report ──────────────────────────────────────
        line = f"       -> {status:5s}  {elapsed:5.1f}s"
        if failed_gates:
            line += f"  [{', '.join(failed_gates[:6])}]"
        if gate_output.get("_error"):
            line += f"  [{gate_output.get('_error_type', '?')}]"
        print(line, flush=True)

        # ── Per-file JSON ───────────────────────────────────────
        safe = _safe_name(fp)
        out_path = run_output_dir / f"{safe}.json"
        scientific_hash = execution.scientific_payload_sha256
        authority_hash = execution.authority_payload_sha256
        if scientific_hash is None or authority_hash is None:
            scientific_hash, authority_hash = scientific_and_authority_payload_hashes(
                gate_output
            )
        artifact = {
            "schema_version": "perfume-chem-batch-artifact-v2",
            "discovery_index": i,
            "file": rel.as_posix(),
            "stem": fp.stem,
            "source_sha256": opening_formula_hashes.get(rel.as_posix()),
            "brief_used": brief,
            "family_archetype_used": family_archetype,
            "concentrate_ul": concentrate_ul,
            "status": status,
            "elapsed_s": round(elapsed, 6),
            "failed_gates": failed_gates,
            "scientific_payload_sha256": scientific_hash,
            "authority_payload_sha256": authority_hash,
            "gate_output": gate_output,
        }
        artifact_bytes = json.dumps(
            artifact,
            indent=2,
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
        out_path.write_bytes(artifact_bytes)
        manifest_entries.append(
            {
                "discovery_index": i,
                "file": rel.as_posix(),
                "source_sha256": opening_formula_hashes.get(rel.as_posix()),
                "artifact_file": out_path.name,
                "artifact_sha256": _sha256_bytes(artifact_bytes),
                "scientific_payload_sha256": scientific_hash,
                "authority_payload_sha256": authority_hash,
                "status": status,
            }
        )

        summary["formulas"].append(
            {
                "discovery_index": i,
                "file": rel.as_posix(),
                "stem": fp.stem,
                "status": status,
                "elapsed_s": round(elapsed, 1),
                "failed_gates": failed_gates,
                "brief_used": brief,
                "family_archetype_used": family_archetype,
                "concentrate_ul": concentrate_ul,
            }
        )

        # ── Heartbeat ───────────────────────────────────────────
        now = time.monotonic()
        if now - last_heartbeat >= 30:
            total_elapsed = now - started_at
            rate = completed_count / total_elapsed if total_elapsed > 0 else 0
            est = (len(formula_files) - completed_count) / rate if rate > 0 else 0
            print(
                f"       [progress: {completed_count}/{len(formula_files)} "
                f"— {total_elapsed:.0f}s elapsed, ~{est:.0f}s remaining]",
                flush=True,
            )
            last_heartbeat = now

    # ── Summary ──────────────────────────────────────────────────────
    total_elapsed = time.monotonic() - started_at
    summary["memory"] = memory_monitor.stop()
    summary["elapsed_seconds"] = round(total_elapsed, 1)
    summary["rate_f_per_minute"] = (
        round(len(formula_files) / (total_elapsed / 60), 1) if total_elapsed > 0 else 0
    )
    summary["generated_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    closing_snapshot = freeze_source_snapshot(jobs)
    source_drift = (
        opening_snapshot["snapshot_sha256"] != closing_snapshot["snapshot_sha256"]
    )
    summary["closing_source_snapshot_sha256"] = closing_snapshot["snapshot_sha256"]
    summary["source_drift"] = source_drift
    summary["batch_status"] = "FAILED_SOURCE_DRIFT" if source_drift else "COMPLETE"
    summary["formulas"] = sorted(
        summary["formulas"], key=lambda row: row["discovery_index"]
    )

    # Gate frequency report
    gate_counts: dict[str, int] = {}
    for f in summary["formulas"]:
        for g in f["failed_gates"]:
            gate_counts[g] = gate_counts.get(g, 0) + 1
    top_gates = sorted(gate_counts.items(), key=lambda x: -x[1])[:15]
    summary["top_failed_gates"] = [{"gate": g, "count": c} for g, c in top_gates]

    # Write summary
    summary_path = run_output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    result_manifest = {
        "schema_version": "perfume-chem-batch-manifest-v2",
        "opening_source_snapshot_sha256": opening_snapshot["snapshot_sha256"],
        "closing_source_snapshot_sha256": closing_snapshot["snapshot_sha256"],
        "source_drift": source_drift,
        "entries": sorted(manifest_entries, key=lambda row: row["discovery_index"]),
    }
    manifest_path = run_output_dir / "result_manifest.json"
    manifest_path.write_text(
        json.dumps(result_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (run_output_dir / "source_snapshot.open.json").write_text(
        json.dumps(opening_snapshot, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (run_output_dir / "source_snapshot.close.json").write_text(
        json.dumps(closing_snapshot, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Final console output
    print()
    print("=" * 70)
    print("  BATCH GATE COMPLETE")
    print("=" * 70)
    print(f"  Total:   {summary['total_formulas']:4d}")
    print(f"  PASS:    {summary['passed']:4d}")
    print(f"  WARN:    {summary['warned']:4d}")
    print(f"  FAIL:    {summary['failed']:4d}")
    print(f"  ERROR:   {summary['errors']:4d}")
    print(f"  Time:    {total_elapsed:.0f}s  ({summary['rate_f_per_minute']} f/min)")
    if top_gates:
        print()
        print("  Most frequent FAIL/WARN gates:")
        for name, cnt in top_gates:
            pct = cnt / max(summary["total_formulas"], 1) * 100
            print(f"    {name:45s} {cnt:3d}  ({pct:5.1f}%)")
    print(f"\n  Output dir: {run_output_dir}")
    print(f"  Summary:     {summary_path}")
    print(f"  Manifest:    {manifest_path}")

    return 2 if source_drift else 0


def _safe_name(filepath: Path) -> str:
    """Generate a readable key plus a collision-proof source-path digest."""
    try:
        rel = filepath.relative_to(FORMULAS_DIR)
    except ValueError:
        rel = filepath.relative_to(ROOT)
    parts = list(Path(p).stem for p in rel.parts)
    key = "_".join(parts).lower()
    key = re.sub(r"[^a-z0-9_]+", "_", key)
    prefix = (key.strip("_") or "formula")[:72]
    digest = hashlib.sha256(rel.as_posix().encode("utf-8")).hexdigest()[:12]
    return f"{prefix}__{digest}"


if __name__ == "__main__":
    sys.exit(main())
