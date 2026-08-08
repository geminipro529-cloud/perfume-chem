"""JSONL audit log for gate and optimizer pipeline runs."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT_PATH = PROJECT_ROOT / "data" / "pipeline_audit" / "events.jsonl"
AUDIT_PATH_ENV = "PERFUME_PIPELINE_AUDIT_PATH"


def default_audit_path() -> Path:
    override = os.environ.get(AUDIT_PATH_ENV)
    if override:
        return Path(override)
    return DEFAULT_AUDIT_PATH


def append_event(event: Mapping, path: str | Path | None = None) -> dict:
    """Append one compact audit event and return the persisted payload."""
    payload = dict(event)
    payload.setdefault("event_id", uuid4().hex)
    payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

    out_path = Path(path) if path is not None else default_audit_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        fallback = DEFAULT_AUDIT_PATH
        fallback.parent.mkdir(parents=True, exist_ok=True)
        with fallback.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        payload["audit_path_fallback"] = str(fallback)
    return payload


def load_events(path: str | Path | None = None) -> list[dict]:
    in_path = Path(path) if path is not None else default_audit_path()
    if not in_path.exists():
        return []
    events: list[dict] = []
    with in_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def config_summary(config) -> dict:
    """Return stable release-gate config fields for audit logging."""
    fields = (
        "expected_concentrate_ul",
        "min_neat_trace_ul",
        "batch_volume_ml",
        "temperature_K",
        "brief",
        "family_archetype",
        "concentration_bracket",
        "allow_preblends",
        "min_confidence_score",
        "min_perceptible_materials",
        "max_perceptible_channels",
        "ifra_headroom",
        "commercial_mode",
        "commercial_confidence_policy",
        "quantitative_claim",
        "matrix_components_moles",
        "matrix_mass_g",
        "matrix_source",
        "batch_scaling_targets_ml",
        "expected_retail_price_thb",
        "price_tier",
        "audit_source",
    )
    payload = {field: getattr(config, field) for field in fields if hasattr(config, field)}
    if hasattr(config, "effective_ifra_headroom"):
        payload["effective_ifra_headroom"] = config.effective_ifra_headroom()
    return payload


def compact_gate(gate) -> dict:
    raw = gate.as_dict() if hasattr(gate, "as_dict") else dict(gate)
    data = dict(raw.get("data") or {})
    gate_name = raw.get("gate")
    compact_data: dict = {}

    if gate_name == "safety_ifra_allergen":
        compact_data = {
            key: data.get(key)
            for key in (
                "score",
                "violations",
                "headroom_violations",
                "warnings",
                "banned",
                "missing_ifra_limit",
                "headroom",
                "effective_headroom",
            )
            if key in data
        }
    elif gate_name == "robustness_perturbation":
        compact_data = {
            "status": data.get("status"),
            "checked": data.get("checked"),
            "skipped": data.get("skipped"),
            "issues": data.get("issues", []),
        }
    elif gate_name == "opaque_preblends":
        compact_data = {"materials": data.get("materials", [])}
    elif gate_name == "oav_scaling_guard":
        compact_data = {
            "source_volume_ml": data.get("source_volume_ml"),
            "targets_ml": data.get("targets_ml"),
            "findings": data.get("findings", []),
        }
    elif gate_name in {"family_drift_detector", "novelty_vs_reference"}:
        compact_data = {
            key: data.get(key)
            for key in ("family_archetype", "family", "label", "score", "forbidden_hits", "checks")
            if key in data
        }
    elif gate_name in {
        "inventory_stock_contract",
        "quantitative_authority",
        "natural_composite_coverage",
        "reference_claim_contract",
        "g15_oav_firewall",
        "architecture_concentration",
    }:
        compact_data = data
    elif gate_name in {"chemistry_stability", "phase_compatibility"}:
        compact_data = data
    elif raw.get("status") != "PASS":
        compact_data = data

    payload = {
        "gate": gate_name,
        "status": raw.get("status"),
        "detail": raw.get("detail", ""),
    }
    if compact_data:
        payload["data"] = compact_data
    return payload


def gate_report_event(
    report,
    config,
    *,
    event_type: str = "gate_formula",
    repair_actions: Sequence[Mapping] | None = None,
    source: str = "",
) -> dict:
    """Build a compact event from a GateReport without simulation payloads."""
    gates = [compact_gate(gate) for gate in getattr(report, "gates", [])]
    failed = [gate["gate"] for gate in gates if gate.get("status") == "FAIL"]
    warned = [gate["gate"] for gate in gates if gate.get("status") == "WARN"]
    confidence = dict(getattr(report, "confidence", {}) or {})
    event_source = source or getattr(config, "audit_source", "")
    evidence_gates = {
        gate["gate"]: gate
        for gate in gates
        if gate.get("gate")
        in {
            "inventory_stock_contract",
            "quantitative_authority",
            "natural_composite_coverage",
            "reference_claim_contract",
            "g15_oav_firewall",
        }
    }
    return {
        "event_type": event_type,
        "formula_name": getattr(report, "name", ""),
        "formula_number": getattr(report, "number", None),
        "formula_hash": getattr(report, "formula_hash", ""),
        "brief": getattr(config, "brief", ""),
        "source": event_source,
        "config": config_summary(config),
        "status": getattr(report, "status", "UNKNOWN"),
        "commercial_readiness": getattr(report, "commercial_readiness", "UNKNOWN"),
        "confidence": {
            "combined_confidence": confidence.get("combined_confidence"),
            "combined_grade": confidence.get("combined_grade"),
            "pipeline_confidence": confidence.get("pipeline_confidence"),
        },
        "failed_gates": failed,
        "warn_gates": warned,
        "gates": gates,
        "run_evidence": evidence_gates,
        "repair_actions": list(repair_actions or []),
    }


def summarize_events(events: Iterable[Mapping]) -> dict:
    events = list(events)
    by_event_type = Counter(str(event.get("event_type", "unknown")) for event in events)
    by_status = Counter(str(event.get("status", "UNKNOWN")) for event in events)
    gate_counts: Counter[str] = Counter()
    issue_counts: Counter[str] = Counter()

    for event in events:
        for gate in event.get("gates", []) or []:
            gate_counts[f"{gate.get('gate')}:{gate.get('status')}"] += 1
            if gate.get("status") == "PASS":
                continue
            for issue_key in _issue_keys_from_gate(gate):
                issue_counts[issue_key] += 1

    return {
        "total_events": len(events),
        "by_event_type": dict(by_event_type),
        "by_status": dict(by_status),
        "gate_status_counts": dict(gate_counts),
        "ranked_issues": [
            {"issue": issue, "count": count}
            for issue, count in issue_counts.most_common()
        ],
    }


def suggest_repairs(events: Iterable[Mapping], material: str | None = None) -> list[dict]:
    ranked = summarize_events(events).get("ranked_issues", [])
    material_lc = material.lower() if material else ""
    suggestions: list[dict] = []
    for row in ranked:
        issue = str(row["issue"])
        if material_lc and material_lc not in issue.lower():
            continue
        suggestions.append({
            "issue": issue,
            "count": row["count"],
            "suggestion": _suggestion_for_issue(issue),
        })
    return suggestions


def _issue_keys_from_gate(gate: Mapping) -> list[str]:
    name = str(gate.get("gate", "unknown"))
    data = gate.get("data", {}) or {}
    keys: list[str] = []
    if name == "safety_ifra_allergen":
        for row in data.get("violations", []) or []:
            keys.append(f"safety_ifra_allergen:{row.get('material', 'unknown')}:violation")
        for row in data.get("headroom_violations", []) or []:
            keys.append(f"safety_ifra_allergen:{row.get('material', 'unknown')}:headroom")
        for row in data.get("warnings", []) or []:
            keys.append(f"safety_ifra_allergen:{row.get('material', 'unknown')}:edge")
    elif name == "robustness_perturbation":
        for row in data.get("issues", []) or []:
            material = row.get("material", "unknown")
            if row.get("safety_failed"):
                keys.append(f"robustness_perturbation:{material}:safety_margin")
            if row.get("brief_failed"):
                keys.append(f"robustness_perturbation:{material}:brief_fragility")
            if row.get("family_envelope_drift", 0.0) > 0.25:
                keys.append(f"robustness_perturbation:{material}:family_drift")
    elif name == "opaque_preblends":
        for material in data.get("materials", []) or []:
            keys.append(f"opaque_preblends:{material}:identity")
    elif name == "oav_scaling_guard":
        for row in data.get("findings", []) or []:
            keys.append(f"oav_scaling_guard:{row.get('material', 'unknown')}:{row.get('severity', 'unknown')}")
    elif name == "chemistry_stability":
        for row in data.get("schiff_base", {}).get("pairs", []) or []:
            keys.append(f"chemistry_stability:{row.get('aldehyde', 'unknown')}:schiff_base")
        if data.get("shelf_life_days", 9999) < 365:
            keys.append("chemistry_stability:shelf_life")
        for row in data.get("oxidation_prone_materials", []) or []:
            keys.append(f"chemistry_stability:{row.get('material', 'unknown')}:oxidation")
        for row in data.get("photolabile_materials", []) or []:
            keys.append(f"chemistry_stability:{row.get('material', 'unknown')}:photolability")
    elif name == "phase_compatibility":
        for row in data.get("fail_rows", []) or []:
            keys.append(f"phase_compatibility:{row.get('material', 'unknown')}:fail")
        for row in data.get("warn_rows", []) or []:
            keys.append(f"phase_compatibility:{row.get('material', 'unknown')}:warn")
    elif name == "family_drift_detector":
        archetype = data.get("family_archetype", "unknown")
        for row in data.get("checks", []) or []:
            if row.get("status") == "FAIL":
                keys.append(f"family_drift_detector:{archetype}:{row.get('name', 'unknown')}")
        for material in data.get("forbidden_hits", []) or []:
            keys.append(f"family_drift_detector:{archetype}:forbidden:{material}")
    elif name == "novelty_vs_reference":
        keys.append(f"novelty_vs_reference:{data.get('family_archetype', 'unknown')}")
    else:
        keys.append(name)
    return keys


def _suggestion_for_issue(issue: str) -> str:
    if ":safety_margin" in issue:
        material = issue.split(":")[1]
        return f"Reduce {material} below the perturbation-safe cap or replace lost volume with legal support materials."
    if ":headroom" in issue:
        material = issue.split(":")[1]
        return f"Apply commercial IFRA headroom to {material} and rerun gate-aware repair."
    if ":violation" in issue:
        material = issue.split(":")[1]
        return f"Hard-cap {material} at its IFRA Cat 4 maximum before optimizing hedonic score."
    if issue.startswith("opaque_preblends:"):
        material = issue.split(":")[1]
        return f"Replace {material} with transparent component materials or mark the run exploratory."
    if issue.startswith("oav_scaling_guard:"):
        material = issue.split(":")[1]
        return f"Re-dilute or re-dose {material} before proportional batch scaling."
    if issue.startswith("chemistry_stability:"):
        return "Reduce reactive aldehyde/amine contact, lower oxidation-prone load, or add stabilization before rerunning."
    if issue.startswith("phase_compatibility:"):
        return "Rebalance solvent-compatible materials or swap incompatible anchors before rerunning."
    if issue.startswith("family_drift_detector:"):
        parts = issue.split(":")
        archetype = parts[1] if len(parts) > 1 else "requested archetype"
        return f"Rerun with tighter {archetype} anchor/drift constraints before accepting the formula."
    if issue.startswith("novelty_vs_reference:"):
        archetype = issue.split(":", 1)[1]
        return f"Increase the distinctive signature for {archetype}, or label the formula as a reference/control."
    if "perfumer_logic" in issue:
        return "Tighten brief grammar targets before the next optimizer pass."
    if "confidence_minimum" in issue:
        return "Add measured material data or calibration records before commercial release."
    return "Review recurring gate failure and add a deterministic repair or stricter input constraint."
