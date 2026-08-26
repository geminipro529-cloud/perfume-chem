"""Inspect pipeline audit logs and scan historical formula outputs."""

# ruff: noqa: E402 - repository root must be registered before engine imports

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

from engine.knowledge.literature_rules import (
    build_knowledge_rule_quality_contract,
    build_literature_rule_contract,
)
from engine.odor_thresholds import ODT_VERIFICATION
from engine.perception.complexity_benchmark import (
    prepare_complexity_benchmark,
    prepare_relevant_ablations,
    run_complexity_census,
    score_complexity_run,
    validate_complexity_run,
    write_complexity_benchmark_receipt,
)
from engine.pipeline.audit_log import load_events, suggest_repairs, summarize_events
from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from engine.project_verification import (
    default_verification_report_path,
    run_project_verification,
    write_verification_report,
)
from engine.schema_validator import SchemaValidator
from engine.science_audit import build_science_audit_contract
from scripts.formula_release_gate import (
    current_repository_evidence_hashes,
    validate_pipeline_analysis_artifact,
)
from scripts.verify_formula_workflow import parse_formula_markdown

DISCONNECTED_MODULE_STATUS = {
    "engine.optimizer.gate_aware": "promote",
    "engine.odt_verifier": "promote",
    "engine.knowledge.embeddings": "verify_only",
    "engine.biology.microbiome": "advisory_only",
    "engine.biology.genetics": "advisory_only",
    "engine.receptor.binding": "advisory_until_coverage",
    "engine.formulator": "deprecated_from_pipeline_narrative",
    "engine.opus_v_workbook": "deprecated_from_pipeline_narrative",
    "engine.reconstruction_pipeline": "deprecated_from_pipeline_narrative",
    "engine.family_scorer": "audit_for_duplication",
    "engine.formula_analyzer": "audit_for_duplication",
    "engine.odor_ontology": "advisory_only",
    "engine.pattern_miner": "advisory_only",
    "engine.thermo.headspace": "consolidate_or_deprecate",
    "engine.thermo.trajectory": "consolidate_or_deprecate",
}


def _data_authority_coverage_report() -> dict:
    by_vfy: dict[str, int] = {}
    for meta in ODT_VERIFICATION.values():
        vfy = str((meta or {}).get("vfy", "UNKNOWN"))
        by_vfy[vfy] = by_vfy.get(vfy, 0) + 1
    total = sum(by_vfy.values()) or 1
    science = build_science_audit_contract()
    return {
        "odt_verification_counts": by_vfy,
        "odt_authoritative_pct": round(
            100.0
            * sum(by_vfy.get(key, 0) for key in ("PEER_CROSS", "PEER_SINGLE", "PEER_EST"))
            / total,
            1,
        ),
        "odt_heuristic_pct": round(
            100.0 * sum(by_vfy.get(key, 0) for key in ("DERIVED", "UNVERIFIED", "UNKNOWN")) / total,
            1,
        ),
        "science_coverage_pct": science.get("data_coverage_pct", {}),
    }


def _disconnected_module_status_report() -> dict:
    existing = {}
    for module_name, disposition in DISCONNECTED_MODULE_STATUS.items():
        relative = Path(*module_name.split(".")).with_suffix(".py")
        existing[module_name] = {
            "status": disposition,
            "path": str(relative),
            "exists": (PROJECT_ROOT / relative).exists(),
        }
    return existing


def _evidence_posture_report() -> dict:
    return {
        "authoritative_internal": [
            "schema_validation",
            "literature_rule_contract",
            "knowledge_rule_quality",
            "disconnected_module_status",
        ],
        "mixed_authority": [
            "data_authority_coverage",
        ],
        "heuristic_or_partial_science": [
            "science_audit",
        ],
        "notes": {
            "authoritative_internal": (
                "Repository-verified structure, rule inventory, and codebase status."
            ),
            "mixed_authority": (
                "Contains both verified authority counts and coverage gaps for runtime chemistry inputs."
            ),
            "heuristic_or_partial_science": (
                "Research-facing science layers with explicit heuristic, inferred, or incomplete coverage."
            ),
        },
    }


def _print_json(payload: dict | list) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _is_scratch_formula_path(path: Path) -> bool:
    return path.name.startswith("_")


def _matching_formula_paths(pattern: str, *, include_scratch: bool = False) -> list[Path]:
    paths = [Path(path) for path in glob.glob(str(PROJECT_ROOT / pattern), recursive=True)]
    paths = sorted(paths)
    if include_scratch:
        return paths
    return [path for path in paths if not _is_scratch_formula_path(path)]


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
    paths = _matching_formula_paths(pattern, include_scratch=args.include_scratch)
    if not paths:
        print(f"No files matched {pattern!r}")
        return 1

    ifra_headroom = args.ifra_headroom
    commercial_mode = args.commercial_ready or args.commercial_trial
    if ifra_headroom is None:
        ifra_headroom = 0.8 if commercial_mode else 1.0

    reports = []
    from engine.formula_metadata import pipeline_preflight_guard as _preflight

    for path in sorted(paths):
        preflight = _preflight(str(path), brief=args.brief)
        if not preflight.ok():
            reports.append(
                {
                    "file": str(path),
                    "preflight": {
                        "status": "BLOCKED",
                        "hard_blocks": preflight.hard_blocks,
                        "warnings": preflight.warnings,
                    },
                    "formulas": [],
                }
            )
            continue
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
            file_reports.append(
                {
                    "number": report.number,
                    "name": report.name,
                    "status": report.status,
                    "commercial_readiness": report.commercial_readiness,
                    "audit_event_id": report.audit_event_id,
                    "failed_gates": [gate.gate for gate in report.gates if gate.status == "FAIL"],
                    "warn_gates": [gate.gate for gate in report.gates if gate.status == "WARN"],
                }
            )
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


def _cmd_verify(args: argparse.Namespace) -> int:
    schema = SchemaValidator().validate_all().summary()
    literature = build_literature_rule_contract().as_dict()
    knowledge_rule_quality = build_knowledge_rule_quality_contract().as_dict()
    science = build_science_audit_contract()
    data_authority = _data_authority_coverage_report()
    disconnected_modules = _disconnected_module_status_report()
    evidence_posture = _evidence_posture_report()

    formula_paths = _matching_formula_paths(args.glob, include_scratch=args.include_scratch)
    formula_paths = sorted(formula_paths)[: max(1, int(args.sample_limit))]
    representative: list[dict] = []
    for path in formula_paths:
        try:
            formulas = parse_formula_markdown(path)
        except Exception as exc:
            representative.append(
                {
                    "file": str(path.relative_to(PROJECT_ROOT)),
                    "error": str(exc),
                    "formulas": [],
                }
            )
            continue
        runs = []
        for formula in formulas[:1]:
            config = ReleaseGateConfig(
                brief=args.brief,
                family_archetype=args.family_archetype,
                allow_preblends=args.allow_preblends,
                audit_enabled=not args.no_audit,
                audit_source=f"verify:{path.relative_to(PROJECT_ROOT)}",
            )
            report = gate_formula(formula, config).as_dict()
            runs.append(
                {
                    "name": report["name"],
                    "status": report["status"],
                    "commercial_readiness": report["commercial_readiness"],
                    "preflight_status": (report.get("preflight") or {}).get("status"),
                    "failed_gates": [
                        gate["gate"]
                        for gate in report.get("gates", [])
                        if gate.get("status") == "FAIL"
                    ],
                    "warn_gates": [
                        gate["gate"]
                        for gate in report.get("gates", [])
                        if gate.get("status") == "WARN"
                    ],
                }
            )
        representative.append(
            {
                "file": str(path.relative_to(PROJECT_ROOT)),
                "formulas": runs,
            }
        )

    payload = {
        "evidence_posture": evidence_posture,
        "schema_validation": schema,
        "literature_rule_contract": literature,
        "knowledge_rule_quality": knowledge_rule_quality,
        "science_audit": science,
        "data_authority_coverage": data_authority,
        "disconnected_module_status": disconnected_modules,
        "representative_runs": representative,
    }
    if args.json:
        _print_json(payload)
        return 0

    print("Schema validation:")
    print(
        f"  errors={schema['errors']} warnings={schema['warnings']} total_issues={schema['total_issues']}"
    )
    print("Literature rule contract:")
    print(
        f"  status={literature['status']} english={literature['english_sources']} "
        f"french_manifest={literature['french_manifest_entries']} "
        f"deterministic_rules={literature['deterministic_rule_entries']} "
        f"index_fresh={literature['index_fresh']}"
    )
    print("Knowledge rule quality:")
    print(
        f"  status={knowledge_rule_quality['status']} total={knowledge_rule_quality['total_entries']} "
        f"valid={knowledge_rule_quality['valid_entries']} advisory={knowledge_rule_quality['advisory_entries']} "
        f"invalid={knowledge_rule_quality['invalid_entries']}"
    )
    print("Data authority coverage:")
    print(
        f"  odt_authoritative_pct={data_authority['odt_authoritative_pct']} "
        f"odt_heuristic_pct={data_authority['odt_heuristic_pct']}"
    )
    print("Disconnected module status:")
    for module_name, meta in disconnected_modules.items():
        print(f"  {module_name}: {meta['status']} exists={meta['exists']}")
    print("Representative runs:")
    for row in representative:
        if row.get("error"):
            print(f"  {row['file']}: ERROR {row['error']}")
            continue
        for formula in row.get("formulas", []):
            print(
                f"  {row['file']} -> {formula['name']}: {formula['status']} "
                f"({formula['commercial_readiness']}) preflight={formula['preflight_status']}"
            )
            if formula["failed_gates"]:
                print("    FAIL: " + ", ".join(formula["failed_gates"]))
            if formula["warn_gates"]:
                print("    WARN: " + ", ".join(formula["warn_gates"][:8]))
    return 0


def _cmd_artifact_verify(args: argparse.Namespace) -> int:
    """Validate persisted analysis provenance without re-running formula science."""

    paths = _matching_formula_paths(
        args.glob,
        include_scratch=args.include_scratch,
    )
    if not paths:
        payload = {
            "status": "FAIL",
            "reason": f"No files matched {args.glob!r}",
            "files": [],
        }
        if args.json:
            _print_json(payload)
        else:
            print(payload["reason"])
        return 1

    rows = []
    counts: dict[str, int] = {}
    repository_hashes = current_repository_evidence_hashes()
    for path in paths:
        try:
            result = validate_pipeline_analysis_artifact(
                path,
                repository_hashes=repository_hashes,
            )
        except Exception as exc:  # fail closed for persisted evidence validation
            result = {"status": "TAMPERED", "issues": [f"validator_error:{exc}"]}
        status = str(result.get("status", "TAMPERED"))
        counts[status] = counts.get(status, 0) + 1
        rows.append(
            {
                "file": str(path.relative_to(PROJECT_ROOT)),
                **result,
            }
        )

    blocking_statuses = {"STALE", "TAMPERED"}
    blockers = [row for row in rows if row["status"] in blocking_statuses]
    overall = "FAIL" if blockers else "WARN" if counts.get("UNBOUND_LEGACY", 0) else "PASS"
    payload = {
        "status": overall,
        "policy": {
            "blocking": sorted(blocking_statuses),
            "unbound_legacy_is_current": False,
            "none_is_current": False,
            "quarantined_is_current": False,
            "quarantined_release_authority": False,
        },
        "counts": dict(sorted(counts.items())),
        "files": rows,
    }
    if args.json:
        _print_json(payload)
    else:
        print(f"Artifact verification: {overall}")
        for status, count in sorted(counts.items()):
            print(f"  {status:<15} {count}")
        for row in blockers:
            print(f"  BLOCK {row['file']}: {', '.join(row.get('issues', []))}")
    return 1 if blockers else 0


def _cmd_project_verify(args: argparse.Namespace) -> int:
    try:
        report = run_project_verification(
            project_root=PROJECT_ROOT,
            selected=args.only,
            quick=args.quick,
            include_docker=args.include_docker,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    output_path = (
        PROJECT_ROOT / args.output
        if args.output is not None
        else default_verification_report_path(PROJECT_ROOT, report)
    )
    write_verification_report(report, output_path)
    payload = report.as_dict()
    if args.json:
        _print_json(payload)
    else:
        print(f"Completion gate: {payload['completion_gate']}")
        for check in payload["checks"]:
            suffix = f" - {check['reason']}" if check.get("reason") else ""
            print(f"  {check['status']:<7} {check['name']}{suffix}")
        print(f"Report: {output_path.relative_to(PROJECT_ROOT)}")
    return 1 if report.completion_gate == "FAIL" else 0


def _cmd_complexity_benchmark(args: argparse.Namespace) -> int:
    handlers = {
        "census": run_complexity_census,
        "prepare": prepare_complexity_benchmark,
        "validate": validate_complexity_run,
        "score": score_complexity_run,
        "ablate": prepare_relevant_ablations,
        "receipt": write_complexity_benchmark_receipt,
    }
    try:
        payload = handlers[args.operation](
            project_root=PROJECT_ROOT,
            run_dir=PROJECT_ROOT / args.run_dir,
        )
    except ValueError as exc:
        payload = {
            "state": "BENCHMARK_BLOCKED",
            "operation": args.operation,
            "provider_calls": 0,
            "run_dir": args.run_dir,
            "artifacts": [],
            "blockers": [str(exc)],
        }
        _print_json(payload)
        return 2
    _print_json(payload)
    return (
        1
        if payload["state"] == "HOLD"
        or str(payload["state"]).startswith("BENCHMARK_BLOCKED")
        else 0
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review pipeline audit logs and historical formula outputs."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    summarize = sub.add_parser("summarize", help="Summarize JSONL pipeline audit events.")
    summarize.add_argument("--path", default=None)
    summarize.add_argument("--json", action="store_true")
    summarize.set_defaults(func=_cmd_summarize)

    artifact_verify = sub.add_parser(
        "artifact-verify",
        help="Validate formula analysis bindings, hashes, and staleness.",
    )
    artifact_verify.add_argument("--glob", default="formulas/**/*.md")
    artifact_verify.add_argument(
        "--include-scratch",
        action="store_true",
        help="Include underscore-prefixed scratch formulas.",
    )
    artifact_verify.add_argument("--json", action="store_true")
    artifact_verify.set_defaults(func=_cmd_artifact_verify)

    scan = sub.add_parser(
        "scan-formulas",
        help="Run release gates across markdown formulas and log results.",
    )
    scan.add_argument("--glob", default="formulas/**/*.md")
    scan.add_argument(
        "--include-scratch",
        action="store_true",
        help="Include underscore-prefixed scratch formulas in scan results.",
    )
    scan.add_argument(
        "--brief",
        default="auto",
        choices=[
            "auto",
            "generic",
            "layton_dna",
            "aromatic_fougere",
            "vetiver_woody",
            "floral_aldehydic_amber",
            "woody_floral_musk",
            "gourmand_floral",
            "prada_lhomme",
        ],
    )
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

    suggest = sub.add_parser(
        "suggest-repairs",
        help="Rank recurring issues and print deterministic repair suggestions.",
    )
    suggest.add_argument("--material", default=None)
    suggest.add_argument("--path", default=None)
    suggest.add_argument("--json", action="store_true")
    suggest.set_defaults(func=_cmd_suggest_repairs)

    verify = sub.add_parser(
        "verify",
        help="Run schema/literature/science checks plus representative release runs.",
    )
    verify.add_argument("--glob", default="formulas/**/*.md")
    verify.add_argument("--sample-limit", type=int, default=5)
    verify.add_argument(
        "--include-scratch",
        action="store_true",
        help="Include underscore-prefixed scratch formulas in representative runs.",
    )
    verify.add_argument(
        "--brief",
        default="auto",
        choices=[
            "auto",
            "generic",
            "layton_dna",
            "aromatic_fougere",
            "vetiver_woody",
            "floral_aldehydic_amber",
            "woody_floral_musk",
            "gourmand_floral",
        ],
    )
    verify.add_argument("--family-archetype", default="")
    verify.add_argument("--allow-preblends", action="store_true")
    verify.add_argument("--no-audit", action="store_true")
    verify.add_argument("--json", action="store_true")
    verify.set_defaults(func=_cmd_verify)

    project_verify = sub.add_parser(
        "project-verify",
        help="Run bounded Phase 0 repository checks and emit completion evidence.",
    )
    project_verify.add_argument(
        "--only",
        action="append",
        default=[],
        help="Run one named check; repeat to select multiple checks.",
    )
    project_verify.add_argument(
        "--quick",
        action="store_true",
        help="Run the canonical truth, science, data, and golden checks only.",
    )
    project_verify.add_argument(
        "--include-docker",
        action="store_true",
        help="Run optional Docker build and smoke checks when Docker is available.",
    )
    project_verify.add_argument(
        "--output",
        default=None,
        help=(
            "Repository-relative JSON report path. By default, full evidence uses "
            "project_verification.json and non-full evidence uses a scope suffix."
        ),
    )
    project_verify.add_argument("--json", action="store_true")
    project_verify.set_defaults(func=_cmd_project_verify)

    complexity = sub.add_parser(
        "complexity-benchmark",
        help=(
            "Prepare, validate, score, and receipt the local complexity xhigh "
            "benchmark."
        ),
    )
    complexity.add_argument(
        "--operation",
        required=True,
        choices=("census", "prepare", "validate", "score", "ablate", "receipt"),
    )
    complexity.add_argument(
        "--run-dir",
        default="output/complexity_xhigh_benchmark/current",
    )
    complexity.add_argument("--json", action="store_true")
    complexity.set_defaults(func=_cmd_complexity_benchmark)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
