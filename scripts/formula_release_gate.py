"""Strict release gate CLI for markdown formula tables.

The implementation lives in engine.pipeline.gates so optimizers, verification
bundles, and markdown writers can all call the same hard gates.  This script is
only the command-line adapter.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.pipeline.gates import DEFAULT_CONCENTRATE_UL, ReleaseGateConfig, gate_formula
from scripts.verify_formula_workflow import parse_formula_markdown


def _build_config(args: argparse.Namespace) -> ReleaseGateConfig:
    ifra_headroom = args.ifra_headroom
    commercial_mode = args.commercial_ready or args.commercial_trial
    if ifra_headroom is None:
        ifra_headroom = 0.8 if commercial_mode else 1.0
    return ReleaseGateConfig(
        expected_concentrate_ul=args.expected_concentrate_ul,
        batch_volume_ml=args.batch_volume_ml,
        temperature_K=args.temperature_k,
        brief=args.brief,
        family_archetype=args.family_archetype,
        allow_preblends=args.allow_preblends,
        min_confidence_score=args.min_confidence,
        ifra_headroom=ifra_headroom,
        commercial_mode=commercial_mode,
        commercial_confidence_policy="warn" if args.commercial_trial else "block",
        batch_scaling_targets_ml=tuple(args.scaling_target_ml or ()),
        audit_enabled=not args.no_audit,
        audit_source=args.audit_source or str(args.formula_file),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run strict release gates on formula markdown.")
    parser.add_argument("--formula-file", required=True)
    parser.add_argument("--expected-concentrate-ul", type=float, default=DEFAULT_CONCENTRATE_UL)
    parser.add_argument("--batch-volume-ml", type=float, default=30.0)
    parser.add_argument("--temperature-k", type=float, default=305.0)
    parser.add_argument("--min-confidence", type=float, default=25.0)
    commercial = parser.add_mutually_exclusive_group()
    commercial.add_argument(
        "--commercial-ready",
        action="store_true",
        help="Apply commercial-mode gates: 80% IFRA headroom by default, stricter confidence, robustness as blocker.",
    )
    commercial.add_argument(
        "--commercial-trial",
        action="store_true",
        help="Apply commercial safety/buildability gates but treat LOW confidence as a warning.",
    )
    parser.add_argument(
        "--ifra-headroom",
        type=float,
        default=None,
        help="Multiplier applied to IFRA limits. Defaults to 1.0 technical mode, 0.8 commercial mode.",
    )
    parser.add_argument(
        "--scaling-target-ml",
        type=float,
        action="append",
        default=[],
        help="Repeatable proportional batch scaling target checked by oav_scaling_guard.",
    )
    parser.add_argument("--no-audit", action="store_true", help="Disable JSONL audit logging for this run.")
    parser.add_argument("--audit-source", default="", help="Source label written to the pipeline audit log.")
    parser.add_argument(
        "--brief",
        default="auto",
        choices=["auto", "generic", "layton_dna", "aromatic_fougere", "vetiver_woody"],
        help="Perfumer-logic brief to enforce. Auto infers from formula text.",
    )
    parser.add_argument(
        "--family-archetype",
        default="",
        help="Optional family archetype key, e.g. aromatic_fougere.modern_mineral.",
    )
    parser.add_argument(
        "--allow-preblends",
        action="store_true",
        help="Warn instead of fail for FTEC/Fleuressence/FO/accord/base materials.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    formula_path = Path(args.formula_file)
    if not formula_path.is_absolute():
        formula_path = PROJECT_ROOT / formula_path
    formulas = parse_formula_markdown(formula_path)
    if not formulas:
        raise ValueError(f"No parseable formulas found in {formula_path}")

    config = _build_config(args)
    reports = [gate_formula(formula, config).as_dict() for formula in formulas]
    overall = "PASS"
    if any(report["status"] == "FAIL" for report in reports):
        overall = "FAIL"
    elif any(report["status"] == "WARN" for report in reports):
        overall = "WARN"

    payload = {"formula_file": str(formula_path), "overall": overall, "formulas": reports}

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Overall: {overall}")
        for report in reports:
            print(
                f"{report['number']}. {report['name']}: {report['status']} "
                f"({report['commercial_readiness']})"
            )
            for gate in report["gates"]:
                detail = f" - {gate['detail']}" if gate.get("detail") else ""
                print(f"  {gate['status']}: {gate['gate']}{detail}")

    return 1 if overall == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
