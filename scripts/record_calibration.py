"""Record one empirical wear-test or panel calibration observation."""

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

from engine.calibration.hashing import formula_hash_from_record
from engine.calibration.models import (
    THAI_CLIMATE_CONTEXT,
    CalibrationRecord,
    PanelResult,
    WearTestObservation,
)
from engine.calibration.store import append_record, summarize_records
from scripts.verify_formula_workflow import parse_formula_markdown, select_formula


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append one formula calibration observation to JSONL.")
    parser.add_argument("--formula-file", required=True)
    parser.add_argument("--formula-number", type=int)
    parser.add_argument("--name", help="Substring match for formula name when file contains multiple formulas.")
    parser.add_argument("--time-min", type=float, required=True)
    parser.add_argument("--time-window", default="")
    parser.add_argument("--substrate", default="skin")
    parser.add_argument("--projection-cm", type=float)
    parser.add_argument("--intensity", type=float, help="Observed perceived intensity on 0-10 scale.")
    parser.add_argument("--dominant-note", action="append", default=[])
    parser.add_argument("--rejection-flag", action="append", default=[])
    parser.add_argument("--comment", default="")
    parser.add_argument("--climate", default=THAI_CLIMATE_CONTEXT["name"])
    parser.add_argument("--temperature-k", type=float, default=THAI_CLIMATE_CONTEXT["temperature_K"])
    parser.add_argument("--relative-humidity", type=float, default=THAI_CLIMATE_CONTEXT["relative_humidity"])
    parser.add_argument("--predicted-intensity", type=float)
    parser.add_argument("--predicted-projection-cm", type=float)
    parser.add_argument("--panelist-id")
    parser.add_argument("--liking", type=float)
    parser.add_argument("--familiarity", type=float)
    parser.add_argument("--luxury", type=float)
    parser.add_argument("--purchase-intent", type=float)
    parser.add_argument("--freshness", type=float)
    parser.add_argument("--wearability", type=float)
    parser.add_argument("--descriptor", action="append", default=[])
    parser.add_argument("--panel-comment", default="")
    parser.add_argument("--output", help="Override JSONL output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    formula_path = Path(args.formula_file)
    if not formula_path.is_absolute():
        formula_path = PROJECT_ROOT / formula_path
    formulas = parse_formula_markdown(formula_path)
    if not formulas:
        raise ValueError(f"No parseable formulas found in {formula_path}")
    formula = select_formula(formulas, args.formula_number, args.name)
    formula_hash = formula_hash_from_record(formula)

    predicted = {}
    if args.predicted_intensity is not None:
        predicted["intensity_0_10"] = args.predicted_intensity
    if args.predicted_projection_cm is not None:
        predicted["projection_cm"] = args.predicted_projection_cm

    observation = WearTestObservation(
        time_minutes=args.time_min,
        substrate=args.substrate,
        time_window=args.time_window,
        projection_cm=args.projection_cm,
        perceived_intensity_0_10=args.intensity,
        dominant_notes=tuple(args.dominant_note),
        rejection_flags=tuple(args.rejection_flag),
        comments=args.comment,
    )

    panel_results = ()
    if any(
        value is not None
        for value in (
            args.panelist_id,
            args.liking,
            args.familiarity,
            args.luxury,
            args.purchase_intent,
            args.freshness,
            args.wearability,
        )
    ) or args.descriptor:
        panel_results = (
            PanelResult(
                panelist_id=args.panelist_id or "anonymous",
                liking_0_10=args.liking,
                familiarity_0_10=args.familiarity,
                luxury_0_10=args.luxury,
                purchase_intent_0_10=args.purchase_intent,
                freshness_0_10=args.freshness,
                wearability_0_10=args.wearability,
                descriptors=tuple(args.descriptor),
                rejection_flags=tuple(args.rejection_flag),
                comments=args.panel_comment,
            ),
        )

    record = CalibrationRecord(
        formula_name=str(formula["name"]),
        formula_hash=formula_hash,
        context={
            "name": args.climate,
            "temperature_K": args.temperature_k,
            "relative_humidity": args.relative_humidity,
        },
        predicted=predicted,
        observations=(observation,),
        panel_results=panel_results,
    )
    output_path = append_record(record, args.output)
    summary = summarize_records([record], formula_hash=formula_hash)
    print(json.dumps({
        "path": str(output_path),
        "formula_name": record.formula_name,
        "formula_hash": formula_hash,
        "summary": summary,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
