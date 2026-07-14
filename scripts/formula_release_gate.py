"""Unified pipeline CLI — chains OAV authority + formula scoring + release gates.
This is the ONLY entry point for formula analysis."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class _DataclassJSONEncoder(json.JSONEncoder):
    """Handle dataclass objects by converting them to dicts."""

    def default(self, obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        return super().default(obj)


from engine.pipeline.gates import (
    DEFAULT_CONCENTRATE_UL,
    ReleaseGateConfig,
    gate_formula,
)
from engine.pipeline.analysis import render_pipeline_analysis
from engine.pipeline.interventions import build_intervention_contract
from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority
from engine.optimizer.models import ObjectiveWeights
from engine.optimizer.scoring import FormulaScorer
from engine.pipeline.release_scoring import compute_unified_release_scores
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
        expected_retail_price_thb=args.expected_retail_price_thb or 1500.0,
    )


def _format_oav_table(state) -> list[dict]:
    return [
        {
            "name": m.name,
            "dilution": m.dilution,
            "raw_ul": round(m.raw_ul, 2),
            "active_ul": round(m.active_ul, 2),
            "mw": m.mw_g_mol,
            "mf_pct": round(m.mole_fraction * 100, 2),
            "vp_pa": m.vp_pure_pa,
            "gamma": round(m.gamma, 2),
            "vapor_ppm": round(m.vapor_ppm, 6),
            "odt_air_ppm": m.odt_air_ppm,
            "oav": round(m.oav, 2) if m.oav else None,
            "note": m.note,
        }
        for m in sorted(state.materials, key=lambda x: -(x.oav or 0))
    ]


def _append_pipeline_analysis(formula_path: Path, analysis_text: str) -> None:
    text = formula_path.read_text(encoding="utf-8", errors="replace")
    marker = "\n## Pipeline Analysis\n"
    payload = f"## Pipeline Analysis\n\n```text\n{analysis_text.rstrip()}\n```\n"
    if marker in text:
        head, _, _tail = text.partition(marker)
        formula_path.write_text(head.rstrip() + "\n\n" + payload, encoding="utf-8")
        return
    formula_path.write_text(text.rstrip() + "\n\n" + payload, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run unified pipeline: OAV + scoring + gates."
    )
    parser.add_argument("--formula-file", required=True)
    parser.add_argument(
        "--expected-concentrate-ul", type=float, default=DEFAULT_CONCENTRATE_UL
    )
    parser.add_argument("--batch-volume-ml", type=float, default=30.0)
    parser.add_argument("--temperature-k", type=float, default=305.0)
    parser.add_argument("--min-confidence", type=float, default=25.0)
    commercial = parser.add_mutually_exclusive_group()
    commercial.add_argument("--commercial-ready", action="store_true")
    commercial.add_argument("--commercial-trial", action="store_true")
    parser.add_argument("--ifra-headroom", type=float, default=None)
    parser.add_argument("--scaling-target-ml", type=float, action="append", default=[])
    parser.add_argument("--no-audit", action="store_true")
    parser.add_argument("--audit-source", default="")
    parser.add_argument(
        "--brief",
        default="auto",
        choices=[
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
        ],
    )
    parser.add_argument("--family-archetype", default="")
    parser.add_argument("--allow-preblends", action="store_true")
    parser.add_argument(
        "--expected-retail-price-thb",
        type=float,
        default=1500.0,
        help="Target retail price in THB (default: 1500). Used for mass-market tier margin check.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--print-analysis", action="store_true")
    parser.add_argument("--append-analysis", action="store_true")
    args = parser.parse_args(argv)

    formula_path = Path(args.formula_file)
    if not formula_path.is_absolute():
        formula_path = PROJECT_ROOT / formula_path
    formulas = parse_formula_markdown(formula_path)
    if not formulas:
        raise ValueError(f"No parseable formulas found in {formula_path}")

    config = _build_config(args)
    scorer = FormulaScorer(ObjectiveWeights())
    reports = []

    for formula in formulas:
        ings = formula["ingredients_ul"]
        dils = formula["dilutions"]

        # Phase 1: OAV authority analysis
        oav_req = OAVAuthorityRequest(
            formula_name=formula["name"],
            ingredients_ul=ings,
            dilutions=dils,
            batch_volume_ml=args.batch_volume_ml,
            temperature_K=args.temperature_k,
            family_archetype=config.family_archetype
            or formula.get("family_archetype", ""),
        )
        oav_result = analyze_oav_authority(oav_req)
        oav_table = _format_oav_table(oav_result.state)

        # Phase 3: Release gates
        gate_report = gate_formula(formula, config).as_dict()
        unified_scores = compute_unified_release_scores(
            formula, oav_result, gate_report, scorer=scorer
        ).as_dict()

        report = {
            **gate_report,
            "scores": unified_scores["scores"],
            "industry_10": unified_scores["industry_10"],
            "score_provenance": unified_scores["provenance"],
            "oav_authority": {
                "status": oav_result.primary_status,
                "rank_score": round(oav_result.authority_rank_score, 1),
                "perceptible": len(
                    [r for r in oav_result.material_rows if (r.oav or 0) >= 1.0]
                ),
                "subliminal_mass_pct": round(oav_result.subliminal_mass_ratio * 100, 1),
                "total_vapor_ppm": round(oav_result.state.total_vapor_ppm, 2),
                "family_drift_pct": round(oav_result.top_family_drift * 100, 1),
            },
            "oav_table": oav_table,
            "time_windows": [
                {
                    "label": w.label,
                    "t_seconds": w.t_seconds,
                    "perceptible_materials": w.perceptible_material_count,
                    "total_vapor_ppm": round(w.total_vapor_ppm, 2),
                    "dominant_leaders": [
                        {"material": l["material"], "oav": l["oav"]}
                        for l in w.dominant_oav[:5]
                    ],
                }
                for w in oav_result.time_windows
            ],
        }

        report["interventions"] = build_intervention_contract(
            formula,
            report,
            batch_volume_ml=args.batch_volume_ml,
        )
        report["diagnosis"] = list(report["interventions"].get("blocking_issues", []))
        reports.append(report)

    overall = "PASS"
    if any(r["status"] == "FAIL" for r in reports):
        overall = "FAIL"
    elif any(r["status"] == "WARN" for r in reports):
        overall = "WARN"

    payload = {
        "formula_file": str(formula_path),
        "overall": overall,
        "formulas": reports,
    }
    analysis_text = render_pipeline_analysis(payload)
    payload["analysis_markdown"] = analysis_text

    if args.json:
        print(json.dumps(payload, indent=2, cls=_DataclassJSONEncoder))
    else:
        print(f"Overall: {overall}")
        for report in reports:
            s = report.get("scores", {})
            oa = report.get("oav_authority", {})
            print(
                f"\n{report['name']}: {report['status']} ({report['commercial_readiness']})"
            )
            print(
                f"  Score: {s.get('total', 0):.1f}  |  "
                f"Sillage: {s.get('sillage', 0):.1f}  |  "
                f"Longevity: {s.get('longevity', 0):.1f}  |  "
                f"Synergy: {s.get('synergy', 0):.1f}  |  "
                f"Skin: {s.get('skin_performance', 0):.1f}"
            )
            print(
                f"  OAV: {oa.get('status', '?')} (rank={oa.get('rank_score', 0)})  |  "
                f"Perceptible: {oa.get('perceptible', '?')}  |  "
                f"Vapor: {oa.get('total_vapor_ppm', 0)} ppm"
            )
            for gate in report["gates"]:
                detail = f" - {gate['detail']}" if gate.get("detail") else ""
                print(f"  {gate['status']}: {gate['gate']}{detail}")

    if args.print_analysis:
        print(analysis_text)
    if args.append_analysis:
        _append_pipeline_analysis(formula_path, analysis_text)

    return 1 if overall == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
