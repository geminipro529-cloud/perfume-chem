#!/usr/bin/env python3
"""Batch-gate ALL formula .md files in formulas/ (recursive) through
formula_release_gate.py.

Extracts concentrate volume and brief from formula metadata when present.
Skips non-formula files (_ prefix, prep_ prefix, files without formula tables).
Writes per-formula JSON output and aggregate summary. Handles failures gracefully.

Usage:
    python scripts/batch_gate_all_formulas.py                     # All formulas
    python scripts/batch_gate_all_formulas.py --subset 5           # First 5 only
    python scripts/batch_gate_all_formulas.py --brief vetiver_woody  # Override
    python scripts/batch_gate_all_formulas.py --timeout 90         # Custom timeout
    python scripts/batch_gate_all_formulas.py --dry-run            # Preview only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
FORMULAS_DIR = ROOT / "formulas"
OUTPUT_DIR = ROOT / ".omo" / "evidence" / "batch_results"

# Ensure OPENCODE_SESSION_ID is set for multi-window gate mode
if not os.environ.get("OPENCODE_SESSION_ID"):
    os.environ["OPENCODE_SESSION_ID"] = f"batch-{int(time.time())}"

# ── Constants ──────────────────────────────────────────────────────
DEFAULT_CONCENTRATE_UL = 6000
DEFAULT_BRIEF = "generic"
DEFAULT_TIMEOUT_S = 60

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
    if m:
        return m.group(1).strip()

    # Free-text Brief / Family / Brief axis
    for label in ("Brief", "Family", "Brief axis"):
        m = re.search(rf"\*\*{label}:\*\*\s*(.+?)(?:\n|$)", body, re.IGNORECASE)
        if m:
            return _map_brief_keywords(m.group(1).strip())

    return None


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

        formulas.append(fp)

    return formulas, skipped


# ── Gate runner ──────────────────────────────────────────────────────


def run_gate(
    filepath: Path,
    concentrate_ul: int,
    brief: str,
    timeout_s: int,
) -> dict:
    """Run formula_release_gate.py on one formula; return parsed JSON or error dict.

    Uses --no-append-analysis to avoid modifying formula files.
    """
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "formula_release_gate.py"),
        "--formula-file",
        str(filepath),
        "--expected-concentrate-ul",
        str(concentrate_ul),
        "--brief",
        brief,
        "--json",
        "--no-append-analysis",
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(ROOT),
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
    parser = argparse.ArgumentParser(
        description="Batch-gate all formula .md files recursively",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python scripts/batch_gate_all_formulas.py
  python scripts/batch_gate_all_formulas.py --subset 5
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

    if args.dry_run:
        print("Would gate these files (metadata auto-detected):")
        for i, fp in enumerate(formula_files):
            rel = fp.relative_to(ROOT)
            body = fp.read_text(encoding="utf-8", errors="replace")
            meta = extract_metadata(body)
            conc = args.concentrate_ul or meta["concentrate_ul"] or DEFAULT_CONCENTRATE_UL
            brief = args.brief or meta["brief_text"] or DEFAULT_BRIEF
            print(f"  {i + 1:3d}. {rel}")
            print(f"       brief={brief}  conc={conc} uL")
        return 0

    if args.subset > 0:
        formula_files = formula_files[: args.subset]
        print(f"  (--subset {args.subset}: processing first {len(formula_files)} only)")
        print()

    # ── Process ───────────────────────────────────────────────────
    summary: dict = {
        "total_formulas": len(formula_files),
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
        },
    }

    started_at = time.time()
    last_heartbeat = started_at

    for i, fp in enumerate(formula_files):
        rel = fp.relative_to(ROOT)

        # ── Metadata ────────────────────────────────────────────
        body = fp.read_text(encoding="utf-8", errors="replace")
        meta = extract_metadata(body)

        concentrate_ul = args.concentrate_ul or meta["concentrate_ul"] or DEFAULT_CONCENTRATE_UL
        brief = args.brief or meta["brief_text"] or DEFAULT_BRIEF

        # ── Gate ────────────────────────────────────────────────
        t0 = time.time()
        print(f"[{i + 1:3d}/{len(formula_files)}] {rel}", flush=True)
        print(f"       brief={brief}  conc={concentrate_ul} uL", flush=True)

        gate_output = run_gate(fp, concentrate_ul, brief, args.timeout)
        elapsed = time.time() - t0

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
        out_path = OUTPUT_DIR / f"{safe}.json"
        out_path.write_text(
            json.dumps(
                {
                    "file": str(rel),
                    "stem": fp.stem,
                    "brief_used": brief,
                    "concentrate_ul": concentrate_ul,
                    "status": status,
                    "elapsed_s": round(elapsed, 1),
                    "failed_gates": failed_gates,
                    "gate_output": gate_output,
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        summary["formulas"].append(
            {
                "file": str(rel),
                "stem": fp.stem,
                "status": status,
                "elapsed_s": round(elapsed, 1),
                "failed_gates": failed_gates,
                "brief_used": brief,
                "concentrate_ul": concentrate_ul,
            }
        )

        # ── Heartbeat ───────────────────────────────────────────
        now = time.time()
        if now - last_heartbeat >= 30:
            total_elapsed = now - started_at
            rate = (i + 1) / total_elapsed if total_elapsed > 0 else 0
            est = (len(formula_files) - (i + 1)) / rate if rate > 0 else 0
            print(
                f"       [progress: {i + 1}/{len(formula_files)} "
                f"— {total_elapsed:.0f}s elapsed, ~{est:.0f}s remaining]",
                flush=True,
            )
            last_heartbeat = now

    # ── Summary ──────────────────────────────────────────────────────
    total_elapsed = time.time() - started_at
    summary["elapsed_seconds"] = round(total_elapsed, 1)
    summary["rate_f_per_minute"] = (
        round(len(formula_files) / (total_elapsed / 60), 1) if total_elapsed > 0 else 0
    )
    summary["generated_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Gate frequency report
    gate_counts: dict[str, int] = {}
    for f in summary["formulas"]:
        for g in f["failed_gates"]:
            gate_counts[g] = gate_counts.get(g, 0) + 1
    top_gates = sorted(gate_counts.items(), key=lambda x: -x[1])[:15]
    summary["top_failed_gates"] = [{"gate": g, "count": c} for g, c in top_gates]

    # Write summary
    summary_path = OUTPUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

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
    print(f"\n  Output dir: {OUTPUT_DIR}")
    print(f"  Summary:     {summary_path}")

    return 0  # Always exit 0


def _safe_name(filepath: Path) -> str:
    """Generate a unique filesystem-safe key from relative formula path."""
    try:
        rel = filepath.relative_to(FORMULAS_DIR)
    except ValueError:
        rel = filepath.relative_to(ROOT)
    parts = list(Path(p).stem for p in rel.parts)
    key = "_".join(parts).lower()
    key = re.sub(r"[^a-z0-9_]+", "_", key)
    return key.strip("_") or "formula"


if __name__ == "__main__":
    sys.exit(main())
