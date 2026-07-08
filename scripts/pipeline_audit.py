"""Inspect pipeline audit logs and scan historical formula outputs."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.pipeline.audit_log import load_events, summarize_events, suggest_repairs
from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from scripts.verify_formula_workflow import parse_formula_markdown


def _print_json(payload: dict | list) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _cmd_summarize(args: argparse.Namespace) -> int:
    events = load_events(args.path)
    summary = summarize_events(events)
    if args.json:
        _print_json(summary)
        return 0

    print(f"Audit events: {summary['total_events']}")
    print("Status counts:")
    for status, count in summary["by_status"].items():
        print(f"  {status}: {count}")
    print("Top recurring issues:")
    for row in summary["ranked_issues"][:20]:
        print(f"  {row['count']:>4}  {row['issue']}")
    return 0


def _cmd_scan_formulas(args: argparse.Namespace) -> int:
    pattern = args.glob
    paths = [
        Path(path) for path in glob.glob(str(PROJECT_ROOT / pattern), recursive=True)
    ]
    if not paths:
        print(f"No files matched {pattern!r}")
        return 1

    ifra_headroom = args.ifra_headroom
    commercial_mode = args.commercial_ready or args.commercial_trial
    if ifra_headroom is None:
        ifra_headroom = 0.8 if commercial_mode else 1.0

    reports = []
    for path in sorted(paths):
        try:
            formulas = parse_formula_markdown(path)
        except Exception as exc:
            reports.append({"file": str(path), "error": str(exc), "formulas": []})
            continue
        file_reports = []
        for formula in formulas:
            config = ReleaseGateConfig(
                brief=args.brief,
                family_archetype=args.family_archetype,
                allow_preblends=args.allow_preblends,
                commercial_mode=commercial_mode,
                commercial_confidence_policy="warn" if args.commercial_trial else "block",
                ifra_headroom=ifra_headroom,
                batch_scaling_targets_ml=tuple(args.scaling_target_ml or ()),
                audit_enabled=not args.no_audit,
                audit_source=f"scan-formulas:{path.relative_to(PROJECT_ROOT)}",
            )
            report = gate_formula(formula, config)
            file_reports.append({
                "number": report.number,
                "name": report.name,
                "status": report.status,
                "commercial_readiness": report.commercial_readiness,
                "audit_event_id": report.audit_event_id,
                "failed_gates": [gate.gate for gate in report.gates if gate.status == "FAIL"],
                "warn_gates": [gate.gate for gate in report.gates if gate.status == "WARN"],
            })
        reports.append({"file": str(path.relative_to(PROJECT_ROOT)), "formulas": file_reports})

    if args.json:
        _print_json({"scanned_files": len(paths), "results": reports})
        return 0

    for row in reports:
        if row.get("error"):
            print(f"{row['file']}: ERROR {row['error']}")
            continue
        for report in row["formulas"]:
            print(
                f"{row['file']} #{report['number']} {report['name']}: "
                f"{report['status']} ({report['commercial_readiness']})"
            )
            if report["failed_gates"]:
                print("  FAIL: " + ", ".join(report["failed_gates"]))
            if report["warn_gates"]:
                print("  WARN: " + ", ".join(report["warn_gates"]))
    return 0


def _cmd_suggest_repairs(args: argparse.Namespace) -> int:
    events = load_events(args.path)
    suggestions = suggest_repairs(events, material=args.material)
    if args.json:
        _print_json(suggestions)
        return 0
    if not suggestions:
        print("No matching recurring issues found.")
        return 0
    for row in suggestions[:20]:
        print(f"{row['count']:>4}  {row['issue']}")
        print(f"      {row['suggestion']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review pipeline audit logs and historical formula outputs.")
    sub = parser.add_subparsers(dest="command", required=True)

    summarize = sub.add_parser("summarize", help="Summarize JSONL pipeline audit events.")
    summarize.add_argument("--path", default=None)
    summarize.add_argument("--json", action="store_true")
    summarize.set_defaults(func=_cmd_summarize)

    scan = sub.add_parser("scan-formulas", help="Run release gates across markdown formulas and log results.")
    scan.add_argument("--glob", default="formulas/**/*.md")
    scan.add_argument("--brief", default="auto", choices=["auto", "generic", "layton_dna", "aromatic_fougere", "vetiver_woody"])
    scan.add_argument("--family-archetype", default="")
    scan.add_argument("--allow-preblends", action="store_true")
    commercial = scan.add_mutually_exclusive_group()
    commercial.add_argument("--commercial-ready", action="store_true")
    commercial.add_argument("--commercial-trial", action="store_true")
    scan.add_argument("--ifra-headroom", type=float, default=None)
    scan.add_argument("--scaling-target-ml", type=float, action="append", default=[])
    scan.add_argument("--no-audit", action="store_true")
    scan.add_argument("--json", action="store_true")
    scan.set_defaults(func=_cmd_scan_formulas)

    suggest = sub.add_parser("suggest-repairs", help="Rank recurring issues and print deterministic repair suggestions.")
    suggest.add_argument("--material", default=None)
    suggest.add_argument("--path", default=None)
    suggest.add_argument("--json", action="store_true")
    suggest.set_defaults(func=_cmd_suggest_repairs)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
