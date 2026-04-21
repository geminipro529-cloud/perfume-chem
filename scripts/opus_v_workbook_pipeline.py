from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.opus_v_workbook import (
    FORMULA_SHEETS,
    audit_to_markdown,
    build_inventory_crosswalk,
    build_verification_bundle_for_formula,
    catalog_to_dict,
    compare_formula_against_baselines,
    export_formula_weight_first,
    parse_workbook_catalog,
    run_engine_validation,
    write_json,
)


DEFAULT_WORKBOOK = "opus_v_luxury_edp_complete.xlsx"
DEFAULT_OUT_DIR = Path("output/opus_v_workbook")
DEFAULT_TARGETS = (10.0, 30.0, 50.0, 100.0)
DEFAULT_FOCUS_FORMULA = "Opus V Iris Edition Luxury Accord"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit and export the Opus V luxury workbook.")
    parser.add_argument("--workbook", default=DEFAULT_WORKBOOK, help="Workbook path to parse.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory.")
    parser.add_argument(
        "--targets",
        nargs="*",
        type=float,
        default=list(DEFAULT_TARGETS),
        help="Bottle sizes in mL for weight-first export.",
    )
    parser.add_argument(
        "--focus-formula",
        default=DEFAULT_FOCUS_FORMULA,
        help="Formula name to use for drift comparison and verification bundle generation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    catalog = parse_workbook_catalog(args.workbook)
    write_json(out_dir / "catalog.json", catalog_to_dict(catalog))
    write_json(out_dir / "audit.json", catalog.audit)

    focus_formula = catalog.formula_by_name(args.focus_formula)
    if focus_formula is None:
        raise SystemExit(f"Focus formula not found: {args.focus_formula}")

    drift_report = compare_formula_against_baselines(focus_formula)
    write_json(out_dir / "drift_report.json", drift_report)

    (out_dir / "audit_report.md").write_text(
        audit_to_markdown(catalog, drift_report),
        encoding="utf-8",
    )

    validation_bundle = {
        formula.name: run_engine_validation(formula)
        for formula in catalog.formulas
    }
    write_json(out_dir / "engine_validation.json", validation_bundle)

    workbook_substitutions = {
        formula.name: build_inventory_crosswalk(formula, catalog.substitutions)
        for formula in catalog.formulas
    }
    write_json(out_dir / "inventory_crosswalk.json", workbook_substitutions)

    shortlist_names = []
    for sheet_name in FORMULA_SHEETS:
        sheet_formulas = [formula for formula in catalog.formulas if formula.source_sheet == sheet_name]
        if sheet_formulas:
            shortlist_names.append(sheet_formulas[0].name)
    shortlist_names.append(focus_formula.name)
    shortlist_names = list(dict.fromkeys(shortlist_names))

    shortlist = []
    for name in shortlist_names:
        formula = catalog.formula_by_name(name)
        if formula is None:
            continue
        inventory = workbook_substitutions[formula.name]
        shortlist.append(
            {
                "formula_name": formula.name,
                "source_sheet": formula.source_sheet,
                "structure_mode": formula.structure_mode,
                "inventory_only_projection": {
                    "available_count": inventory["available_count"],
                    "missing_count": inventory["missing_count"],
                },
                "lowest_inventory_friction_score": inventory["available_count"] - inventory["missing_count"],
                "closest_to_original_brief": formula.name == focus_formula.name,
                "workbook_substitution_projection": inventory,
            }
        )
    write_json(out_dir / "shortlist.json", shortlist)

    verification_payloads = {
        formula.name: formula.verification_payload(batch_volume_ml=30.0)
        for formula in catalog.formulas
    }
    write_json(out_dir / "verification_payloads.json", verification_payloads)

    verification_bundle = build_verification_bundle_for_formula(focus_formula, batch_volume_ml=30.0)
    write_json(out_dir / "verification_bundle.json", verification_bundle)

    export_rows = []
    for formula in catalog.formulas:
        for target in args.targets:
            export_rows.extend(export_formula_weight_first(formula, target))
    _write_csv(out_dir / "exports_weight_first.csv", export_rows)
    write_json(out_dir / "exports_weight_first.json", export_rows)

    print(f"Workbook parsed: {catalog.meta.total_formula_count} formulas")
    print(f"Audit internal math pass: {catalog.audit.internal_math_passes if catalog.audit else False}")
    print(f"Focus formula: {focus_formula.name}")
    print(f"Drift verdict: {', '.join(drift_report['optimization_verdict'])}")
    print(f"Outputs written to: {out_dir.resolve()}")
    return 0


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
