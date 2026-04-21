"""Standalone outcome logger for verification bundles.

This script does not integrate with the main pipeline. It reads a verification
bundle, normalizes the observed wear-test row(s), and emits calibration-ready
records that can be imported later or trained from directly.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.calibration import ScoreCalibrationPipeline
from engine.confidence import ConfidenceScorer


DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "verification_runs" / "outcome_intake"
DEFAULT_LOG_FILE = PROJECT_ROOT / "verification_runs" / "outcome_log.jsonl"


def _to_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_int(value):
    num = _to_float(value)
    if num is None:
        return None
    return int(num)


def _normalize_phase(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    text = text.replace("-", "_").replace(" ", "_")
    aliases = {
        "pre": "pre_mix",
        "premix": "pre_mix",
        "pre_mix": "pre_mix",
        "between": "between_mix",
        "betweenmix": "between_mix",
        "between_mix": "between_mix",
        "post": "post_mix",
        "postmix": "post_mix",
        "post_mix": "post_mix",
    }
    return aliases.get(text, text)


def _split_tags(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = re.split(r"[;,|]+", str(value))
    tags: list[str] = []
    for item in raw_items:
        text = str(item).strip()
        if text:
            tags.append(text)
    return tags


def _infer_phase(observation: dict, tags: list[str]) -> str | None:
    explicit = _normalize_phase(
        observation.get("intervention_phase")
        or observation.get("phase")
        or observation.get("mix_phase")
    )
    if explicit:
        return explicit
    section = _normalize_phase(observation.get("recommendation_section") or observation.get("section"))
    if section:
        return section
    tag_set = {tag.lower().replace("-", "_").replace(" ", "_") for tag in tags}
    for phase in ("pre_mix", "between_mix", "post_mix"):
        if phase in tag_set:
            return phase
    return None


def _section_context(summary: dict, phase: str | None) -> str | None:
    if not phase:
        return None
    sections = summary.get("recommendation_sections") or {}
    section = sections.get(phase) or {}
    return section.get("context")


def _load_bundle(bundle_dir: Path) -> dict:
    summary_path = bundle_dir / "verification_summary.json"
    metadata_path = bundle_dir / "metadata.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing verification_summary.json in {bundle_dir}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    return {"summary": summary, "metadata": metadata}


def _load_observations(observations_path: Path) -> list[dict]:
    if not observations_path.exists():
        return []
    with observations_path.open("r", encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle)]
    return [row for row in rows if any((value or "").strip() for value in row.values())]


def _build_record(bundle: dict, observation: dict, bundle_dir: Path) -> dict:
    summary = bundle["summary"]
    formula = summary["formula"]
    now = datetime.now(timezone.utc).isoformat()
    observation_tags = _split_tags(observation.get("observation_tags"))
    issue_tags = _split_tags(observation.get("issue_tags"))
    desired_effects = _split_tags(observation.get("desired_effects"))
    must_preserve = _split_tags(observation.get("must_preserve"))
    must_avoid = _split_tags(observation.get("must_avoid"))
    intervention_phase = _infer_phase(observation, observation_tags)
    recommendation_section = _normalize_phase(
        observation.get("recommendation_section") or observation.get("section")
    ) or intervention_phase
    intervention_context = observation.get("intervention_context") or _section_context(summary, recommendation_section)
    bundle_sections = summary.get("recommendation_sections") or {}

    record = {
        "formula_name": formula["name"],
        "formula_version": str(formula.get("version", "1.0")),
        "ingredients": formula["ingredients_pct"],
        "total_volume_ml": None,
        "concentration_pct": None,
        "predicted_scores": summary.get("scores"),
        "rating_longevity": _to_float(observation.get("longevity_score_10")),
        "rating_sillage": _to_float(observation.get("projection_score_10")),
        "rating_balance": _to_float(observation.get("balance_score_10")),
        "rating_overall": _to_float(observation.get("overall_score_10")),
        "rating_complexity": None,
        "notes_text": observation.get("notes") or None,
        "top_notes_observed": None,
        "heart_notes_observed": None,
        "base_notes_observed": None,
        "longevity_hours": _to_float(observation.get("wear_test_hours")),
        "sillage_description": None,
        "batch_size_ml": None,
        "maceration_days": _to_int(observation.get("maceration_days")),
        "creation_date": bundle["metadata"].get("created_at"),
        "evaluation_date": observation.get("date") or now,
        "intervention_phase": intervention_phase,
        "recommendation_section": recommendation_section,
        "observation_tags": observation_tags,
        "issue_tags": issue_tags,
        "desired_effects": desired_effects,
        "must_preserve": must_preserve,
        "must_avoid": must_avoid,
        "intervention_context": intervention_context,
        "bottle_state_file": observation.get("bottle_state_file") or None,
        "additions_applied": observation.get("additions_applied") or None,
        "available_intervention_phases": list(bundle_sections.keys()),
        "tags": [
            "standalone-verification",
            bundle_dir.name,
            *(phase for phase in [intervention_phase, recommendation_section] if phase),
            *observation_tags,
            *issue_tags,
            *desired_effects,
        ],
        "bundle_dir": str(bundle_dir),
        "raw_observation": observation,
    }
    return record


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _write_preview(path: Path, payload: dict, summary: dict, readiness: dict, calibration_report: dict) -> None:
    lines = [
        f"# Outcome Intake - {payload['formula_name']}",
        "",
        f"- Bundle: {payload['bundle_dir']}",
        f"- Recorded at: {payload['evaluation_date']}",
        f"- Intervention phase: {payload.get('intervention_phase') or 'none'}",
        f"- Recommendation section: {payload.get('recommendation_section') or 'none'}",
        f"- Observation tags: {', '.join(payload.get('observation_tags') or []) or 'none'}",
        f"- Issue tags: {', '.join(payload.get('issue_tags') or []) or 'none'}",
        f"- Desired effects: {', '.join(payload.get('desired_effects') or []) or 'none'}",
        f"- Must preserve: {', '.join(payload.get('must_preserve') or []) or 'none'}",
        f"- Must avoid: {', '.join(payload.get('must_avoid') or []) or 'none'}",
        f"- Outcome count in current log: {readiness['outcome_count']}",
        f"- Calibration ready: {str(readiness['calibration_ready']).lower()}",
        "",
        "## Intervention Context",
        "",
        f"- Context: {payload.get('intervention_context') or 'none'}",
        f"- Bottle state file: {payload.get('bottle_state_file') or 'none'}",
        f"- Additions applied: {payload.get('additions_applied') or 'none'}",
        "",
        "## Predicted Scores",
        "",
    ]
    for axis, value in (payload["predicted_scores"] or {}).items():
        lines.append(f"- {axis}: {value}")

    fingerprint = summary.get("fingerprint") if isinstance(summary, dict) else None
    life_graph = summary.get("chemical_life_graph") if isinstance(summary, dict) else None
    if fingerprint:
        lines.extend(["", "## Fingerprint Preview", ""])
        radar = fingerprint.get("character_radar") or {}
        for dim, value in sorted(radar.items(), key=lambda item: item[1], reverse=True)[:5]:
            lines.append(f"- {dim}: {value}")
    if life_graph:
        lines.extend(["", "## Chemical Life Preview", ""])
        lines.append(f"- Health score: {life_graph.get('health_score')}")
        lines.append(f"- Synergy score: {((life_graph.get('synergy_report') or {}).get('overall_synergy'))}")

    lines.extend(["", "## Calibration Preview", ""])
    if calibration_report.get("axes"):
        for axis, info in calibration_report["axes"].items():
            lines.append(
                f"- {axis}: {info['samples']} sample(s), trainable={str(info['trainable']).lower()}"
            )
    else:
        lines.append("- No axes are trainable yet.")

    lines.extend(["", "## Observed Ratings", ""])
    for key in [
        "rating_longevity",
        "rating_sillage",
        "rating_balance",
        "rating_overall",
    ]:
        lines.append(f"- {key}: {payload.get(key)}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Record verification outcomes in a standalone workflow")
    parser.add_argument("--bundle-dir", required=True, help="Path to a verification_runs bundle directory")
    parser.add_argument("--observations-csv", help="Override observations.csv path")
    parser.add_argument("--output-dir", help="Directory for normalized outcome outputs")
    parser.add_argument("--log-file", help="Append normalized records to a JSONL log file")
    args = parser.parse_args()

    bundle_dir = Path(args.bundle_dir)
    if not bundle_dir.is_absolute():
        bundle_dir = PROJECT_ROOT / bundle_dir
    if not bundle_dir.exists():
        raise FileNotFoundError(f"Bundle directory not found: {bundle_dir}")

    observations_path = Path(args.observations_csv) if args.observations_csv else bundle_dir / "observations.csv"
    if not observations_path.is_absolute():
        observations_path = PROJECT_ROOT / observations_path

    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_ROOT / bundle_dir.name
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle = _load_bundle(bundle_dir)
    observations = _load_observations(observations_path)
    if not observations:
        observations = [{}]

    records = [_build_record(bundle, obs, bundle_dir) for obs in observations]

    record_path = output_dir / "outcome_record.json"
    _write_json(record_path, {"records": records, "source_bundle": str(bundle_dir)})

    log_file = Path(args.log_file) if args.log_file else DEFAULT_LOG_FILE
    if not log_file.is_absolute():
        log_file = PROJECT_ROOT / log_file
    for record in records:
        _append_jsonl(log_file, record)

    pipeline = ScoreCalibrationPipeline()
    readiness = ConfidenceScorer().outcome_readiness()
    calibration_preview = pipeline.calibration_readiness(records)
    calibration_report = pipeline.train_from_records(records).as_dict()

    _write_json(output_dir / "calibration_ready.json", {
        "bundle": str(bundle_dir),
        "readiness": readiness,
        "calibration_preview": calibration_preview,
        "calibration_report": calibration_report,
    })
    _write_preview(output_dir / "calibration_preview.md", records[0], bundle["summary"], readiness, calibration_preview)

    print("Outcome records written")
    print(f"Bundle: {bundle_dir}")
    print(f"Output dir: {output_dir}")
    print(f"Log file: {log_file}")
    print(f"Standalone records captured: {len(records)}")
    print(f"Calibration-ready axes (standalone): {', '.join(calibration_preview.get('ready_axes', [])) or 'none'}")
    print(f"Outcome count (DB): {readiness['outcome_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
