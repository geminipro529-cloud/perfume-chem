#!/usr/bin/env python3
"""Reconstruction pipeline CLI - evidence to target formula to chassis to modules.

Usage:
    python scripts/reconstruct.py --mode RECONSTRUCTION build \\
        --evidence evidence.json --output target.json
    python scripts/reconstruct.py --mode STRUCTURAL_CHASSIS chassis \\
        --target target.json --envelope envelope.json --output chassis.md
    python scripts/reconstruct.py --mode FLANKER_MODULE module \\
        --chassis chassis.json --direction "electric citrus" --output module.json
    python scripts/reconstruct.py validate --chassis chassis.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Mode constants
# ---------------------------------------------------------------------------

MODE_CHOICES = [
    "RECONSTRUCTION",
    "CREATIVE_FORMULATION",
    "STRUCTURAL_CHASSIS",
    "FLANKER_MODULE",
    "INVENTORY_MAPPING",
    "LIVE_BATCH",
    "BATCH_RESCUE",
    "SENSORY_EXPERIMENT",
    "ANALYTICAL_INTERPRETATION",
    "COMPLIANCE_BUILD",
    "RELEASE_REVIEW",
]

# ---------------------------------------------------------------------------
# Module availability flags
# ---------------------------------------------------------------------------

try:
    from engine.reconstruction.rank_prior import (
        PRESETS,
        RankPriorConfig,
        RankPriorResult,
        generate_soft_rank_prior,
    )

    _HAS_RANK_PRIOR = True
except ImportError as e:
    _HAS_RANK_PRIOR = False
    _RANK_PRIOR_ERR = str(e)

try:
    from engine.reconstruction.quantity_inference import (
        FunctionalConstraint,
        PotencyCorrection,
        override_rank_prior,
        reconcile_total,
    )

    _HAS_QUANTITY_INFERENCE = True
except ImportError as e:
    _HAS_QUANTITY_INFERENCE = False
    _QUANTITY_INFERENCE_ERR = str(e)

try:
    from engine.reconstruction.recognizer import score_all_materials

    _HAS_RECOGNIZER = True
except ImportError as e:
    _HAS_RECOGNIZER = False
    _RECOGNIZER_ERR = str(e)

try:
    from engine.reconstruction.chassis import (
        CARRIER,
        IMMUTABLE_CORE,
        INTERFACE_RING,
        MODULE_MOBILE,
        PROTECTED_ANCHOR,
        TECHNICAL,
        UNKNOWN_MODULE_CANDIDATE,
        UNKNOWN_PROTECTED,
        ChassisPartition,
        ChassisRow,
        ModuleEnvelope,
        validate_anchor_floors,
        validate_partition,
    )

    _HAS_CHASSIS = True
except ImportError as e:
    _HAS_CHASSIS = False
    _CHASSIS_ERR = str(e)

try:
    from engine.target.formula import (
        TIER_0_NOTE_INSPIRED,
        TIER_1_DOCUMENTARY_FUNCTIONAL_HYPOTHESIS,
        TIER_2_ENSEMBLE_CENTER,
        TargetFormula,
        TargetMaterial,
        create_target_from_rows,
    )

    _HAS_TARGET = True
except ImportError as e:
    _HAS_TARGET = False
    _TARGET_ERR = str(e)

# ---------------------------------------------------------------------------
# Module envelope presets
# ---------------------------------------------------------------------------

MODULE_ENVELOPES: dict[str, dict[str, Any]] = {
    "electric_citrus": {
        "label": "Electric Citrus",
        "socket_raw_ul": 1200.0,
        "active_range": (200.0, 600.0),
        "carrier_range": (400.0, 800.0),
        "anchor_minimums": {},
        "required_roles": ("radiance", "top_note"),
        "family_caps": {"citrus": 0.6, "ester": 0.3},
        "temporal_ranges": {
            "opening": (300.0, 800.0),
            "top": (100.0, 400.0),
            "heart": (0.0, 100.0),
        },
        "forbidden_materials": ("vanillin", "ethyl_maltol", "coumarin"),
    },
    "creamy_iris": {
        "label": "Creamy Iris",
        "socket_raw_ul": 1000.0,
        "active_range": (150.0, 500.0),
        "carrier_range": (300.0, 700.0),
        "anchor_minimums": {},
        "required_roles": ("character", "fixative"),
        "family_caps": {"ionone": 0.5, "musk": 0.3},
        "temporal_ranges": {
            "opening": (0.0, 100.0),
            "heart": (200.0, 600.0),
            "drydown": (100.0, 400.0),
        },
        "forbidden_materials": ("coumarin", "ethyl_vanillin"),
    },
    "smoky_leather": {
        "label": "Smoky Leather",
        "socket_raw_ul": 800.0,
        "active_range": (100.0, 400.0),
        "carrier_range": (200.0, 500.0),
        "anchor_minimums": {},
        "required_roles": ("character", "base"),
        "family_caps": {"leather": 0.5, "phenolic": 0.3},
        "temporal_ranges": {
            "heart": (100.0, 400.0),
            "drydown": (200.0, 500.0),
        },
        "forbidden_materials": ("bergamot", "limonene", "linalool"),
    },
    "transparent_aquatic": {
        "label": "Transparent Aquatic",
        "socket_raw_ul": 900.0,
        "active_range": (100.0, 350.0),
        "carrier_range": (300.0, 600.0),
        "anchor_minimums": {},
        "required_roles": ("radiance", "volume"),
        "family_caps": {"aquatic": 0.5, "aldehyde": 0.3},
        "temporal_ranges": {
            "opening": (200.0, 500.0),
            "top": (100.0, 300.0),
            "heart": (0.0, 100.0),
        },
        "forbidden_materials": ("vanillin", "coumarin", "ethyl_maltol"),
    },
    "warm_amber": {
        "label": "Warm Amber",
        "socket_raw_ul": 1100.0,
        "active_range": (200.0, 500.0),
        "carrier_range": (400.0, 700.0),
        "anchor_minimums": {},
        "required_roles": ("fixative", "base"),
        "family_caps": {"amber": 0.5, "balsamic": 0.3},
        "temporal_ranges": {
            "heart": (100.0, 400.0),
            "drydown": (300.0, 700.0),
        },
        "forbidden_materials": ("calone", "aquatic_materials"),
    },
    "green_galbanum": {
        "label": "Green Galbanum",
        "socket_raw_ul": 700.0,
        "active_range": (80.0, 300.0),
        "carrier_range": (200.0, 450.0),
        "anchor_minimums": {},
        "required_roles": ("character", "top_note"),
        "family_caps": {"green": 0.5, "herbal": 0.3},
        "temporal_ranges": {
            "opening": (200.0, 500.0),
            "top": (100.0, 300.0),
        },
        "forbidden_materials": ("vanillin", "ethyl_maltol", "coumarin"),
    },
}


def _resolve_direction(direction: str) -> str:
    """Resolve a free-text direction string to a module envelope key."""
    direction_lower = direction.strip().lower()
    # Direct match
    if direction_lower in MODULE_ENVELOPES:
        return direction_lower
    # Fuzzy match against labels
    for key, spec in MODULE_ENVELOPES.items():
        if direction_lower == spec["label"].lower():
            return key
        if direction_lower in spec["label"].lower():
            return key
    # Fallback: return the closest match or first envelope
    if MODULE_ENVELOPES:
        return next(iter(MODULE_ENVELOPES))
    return ""


# ---------------------------------------------------------------------------
# Subcommand: build
# ---------------------------------------------------------------------------


def _cmd_build(args: argparse.Namespace) -> dict[str, Any]:
    """Build a target formula from evidence JSON."""
    if not _HAS_RANK_PRIOR:
        return {"status": "ERROR", "detail": f"rank_prior module not available: {_RANK_PRIOR_ERR}"}
    if not _HAS_QUANTITY_INFERENCE:
        return {
            "status": "ERROR",
            "detail": f"quantity_inference module not available: {_QUANTITY_INFERENCE_ERR}",
        }
    if not _HAS_TARGET:
        return {"status": "ERROR", "detail": f"target.formula module not available: {_TARGET_ERR}"}

    evidence_path = Path(args.evidence)
    if not evidence_path.is_absolute():
        evidence_path = PROJECT_ROOT / evidence_path
    if not evidence_path.exists():
        return {"status": "ERROR", "detail": f"Evidence file not found: {evidence_path}"}

    with open(evidence_path, encoding="utf-8") as f:
        evidence: list[dict[str, Any]] = json.load(f)

    if not isinstance(evidence, list):
        return {"status": "ERROR", "detail": "Evidence JSON must be a list of material records"}

    # Extract ordered material list from evidence (rank order)
    ordered_materials: list[str] = []
    for entry in evidence:
        mat_name = entry.get("material", "").strip()
        if mat_name and mat_name not in ordered_materials:
            ordered_materials.append(mat_name)

    if not ordered_materials:
        return {"status": "ERROR", "detail": "No materials found in evidence"}

    # Generate rank prior using MEDIUM preset
    preset_key = args.preset or "MEDIUM"
    if preset_key not in PRESETS:
        return {
            "status": "ERROR",
            "detail": f"Unknown preset '{preset_key}'. Available: {list(PRESETS.keys())}",
        }
    config = PRESETS[preset_key]
    prior_result: RankPriorResult = generate_soft_rank_prior(ordered_materials, config)

    # Build potency corrections from evidence
    corrections: list[PotencyCorrection] = []
    constraints: list[FunctionalConstraint] = []
    for entry in evidence:
        mat_name = entry.get("material", "").strip()
        if not mat_name:
            continue
        source_class = entry.get("source_class", "unknown")
        identity_conf = float(entry.get("identity_confidence", 0.5))
        quantity_conf = float(entry.get("quantity_confidence", 0.5))

        # Potency correction based on source class
        factor_map = {
            "gcms_quantified": 1.0,
            "gcms_semiquantified": 0.8,
            "sensory_estimate": 0.6,
            "literature_reference": 0.7,
            "functional_inference": 0.5,
            "unknown": 0.5,
        }
        factor = factor_map.get(source_class, 0.5)
        corrections.append(
            PotencyCorrection(
                material=mat_name,
                factor=factor,
                justification=f"source_class={source_class}, identity_conf={identity_conf}",
                source="evidence",
            )
        )

        # Functional constraint from quantity confidence
        if quantity_conf < 0.3:
            constraints.append(
                FunctionalConstraint(
                    material=mat_name,
                    role="trace accent",
                    min_dose=0.0,
                    max_dose=prior_result.prior.get(mat_name, 0) * 1.5,
                    required_oav=0.0,
                    notes=f"low quantity confidence ({quantity_conf})",
                )
            )

    # Adjust doses
    adjusted = override_rank_prior(prior_result.prior, constraints, corrections)

    # Reconcile to target total
    target_total = args.target_total_ul or prior_result.total
    reconciled = reconcile_total(adjusted, target_total)

    # Build target formula rows
    rows: list[dict[str, Any]] = []
    for mat_name in ordered_materials:
        dose = reconciled.get(mat_name, 0.0)
        if dose <= 0:
            continue
        # Find evidence entry for confidence
        ev = next((e for e in evidence if e.get("material", "").strip() == mat_name), {})
        rows.append(
            {
                "identity": mat_name,
                "raw_amount": dose,
                "active_amount_median": dose,
                "concentration": 1.0,
                "concentration_basis": "v/v",
                "carrier": "",
                "functional_roles": ["character"],
                "identity_confidence": float(ev.get("identity_confidence", 0.5)),
                "quantity_confidence": float(ev.get("quantity_confidence", 0.5)),
            }
        )

    target = create_target_from_rows(rows)

    # Set authority label based on mode
    mode = args.mode or "RECONSTRUCTION"
    if mode == "RECONSTRUCTION":
        target = TargetFormula(
            product_id=target.product_id,
            reference_brand=target.reference_brand,
            reference_name=target.reference_name,
            reference_concentration=target.reference_concentration,
            reference_batch_year=target.reference_batch_year,
            reference_url=target.reference_url,
            target_materials=target.target_materials,
            total_raw_ul=target.total_raw_ul,
            total_active_ul=target.total_active_ul,
            authority_label=TIER_1_DOCUMENTARY_FUNCTIONAL_HYPOTHESIS,
            formula_hash=target.formula_hash,
            accepted=target.accepted,
            accepted_timestamp=target.accepted_timestamp,
            evidence_ledger_ref=target.evidence_ledger_ref,
        )

    result = target.as_dict()
    result["rank_prior"] = prior_result.as_dict()
    result["adjusted_doses"] = {k: round(v, 4) for k, v in reconciled.items()}
    result["mode"] = mode
    result["brief"] = args.brief or ""
    result["generated_at"] = datetime.now(timezone.utc).isoformat()

    return result


# ---------------------------------------------------------------------------
# Subcommand: chassis
# ---------------------------------------------------------------------------


def _cmd_chassis(args: argparse.Namespace) -> dict[str, Any]:
    """Derive a structural chassis from a target formula."""
    if not _HAS_CHASSIS:
        return {"status": "ERROR", "detail": f"chassis module not available: {_CHASSIS_ERR}"}
    if not _HAS_RECOGNIZER:
        return {"status": "ERROR", "detail": f"recognizer module not available: {_RECOGNIZER_ERR}"}

    target_path = Path(args.target)
    if not target_path.is_absolute():
        target_path = PROJECT_ROOT / target_path
    if not target_path.exists():
        return {"status": "ERROR", "detail": f"Target file not found: {target_path}"}

    with open(target_path, encoding="utf-8") as f:
        target_data: dict[str, Any] = json.load(f)

    envelope_path = Path(args.envelope)
    if not envelope_path.is_absolute():
        envelope_path = PROJECT_ROOT / envelope_path
    if not envelope_path.exists():
        return {"status": "ERROR", "detail": f"Envelope file not found: {envelope_path}"}

    with open(envelope_path, encoding="utf-8") as f:
        envelope_data: dict[str, Any] = json.load(f)

    # Build envelope
    _ar = envelope_data.get("active_range", (100.0, 500.0))
    _cr = envelope_data.get("carrier_range", (200.0, 600.0))
    envelope = ModuleEnvelope(
        socket_raw_ul=float(envelope_data.get("socket_raw_ul", 1000.0)),
        active_range=(float(_ar[0]), float(_ar[1])),
        carrier_range=(float(_cr[0]), float(_cr[1])),
        anchor_minimums=dict(envelope_data.get("anchor_minimums", {})),
        required_roles=tuple(envelope_data.get("required_roles", ())),
        family_caps=dict(envelope_data.get("family_caps", {})),
        temporal_ranges={
            k: (float(v[0]), float(v[1]))
            for k, v in envelope_data.get("temporal_ranges", {}).items()
        },
        forbidden_materials=tuple(envelope_data.get("forbidden_materials", ())),
    )

    # Load target materials
    materials_list = target_data.get("target_materials", [])
    if not materials_list:
        return {"status": "ERROR", "detail": "No target materials found in target file"}

    total_raw = float(target_data.get("total_raw_ul", 0.0))
    if total_raw <= 0:
        total_raw = sum(float(m.get("raw_amount", 0.0)) for m in materials_list)

    # Score recognizers
    scored_materials = score_all_materials(
        [
            {
                "name": m.get("identity", ""),
                "role": (m.get("functional_roles") or ["character"])[0]
                if isinstance(m.get("functional_roles"), (list, tuple))
                else "character",
                "note": "reconstructed",
                "dose_ul": float(m.get("raw_amount", 0.0)),
                "connected_count": 0,
            }
            for m in materials_list
        ]
    )

    # Build chassis partition
    rows: list[ChassisRow] = []
    for sm in scored_materials:
        name = sm["name"]
        raw_ul = sm["dose_ul"]
        active_ul = raw_ul  # assume neat for chassis
        recognizer = sm["recognizer"]
        mobility = sm["mobility"]
        anchor_floor = sm["anchor_floor"]

        # Classify
        if recognizer >= 0.8:
            classification = IMMUTABLE_CORE
        elif recognizer >= 0.6:
            classification = PROTECTED_ANCHOR
        elif mobility >= 0.6:
            classification = MODULE_MOBILE
        elif mobility >= 0.3:
            classification = INTERFACE_RING
        else:
            classification = PROTECTED_ANCHOR

        # Allocate core vs module
        if classification == IMMUTABLE_CORE:
            core_raw = raw_ul
            module_raw = 0.0
        elif classification == MODULE_MOBILE:
            core_raw = raw_ul * anchor_floor
            module_raw = raw_ul - core_raw
        elif classification == PROTECTED_ANCHOR:
            core_raw = raw_ul * anchor_floor
            module_raw = raw_ul - core_raw
        elif classification == INTERFACE_RING:
            core_raw = raw_ul * 0.5
            module_raw = raw_ul - core_raw
        else:
            core_raw = raw_ul
            module_raw = 0.0

        rows.append(
            ChassisRow(
                ingredient=name,
                raw_ul=raw_ul,
                active_ul=active_ul,
                core_raw_ul=round(core_raw, 4),
                module_raw_ul=round(module_raw, 4),
                classification=classification,
            )
        )

    core_total = sum(r.core_raw_ul for r in rows)
    module_total = sum(r.module_raw_ul for r in rows)

    partition = ChassisPartition(
        formula_name=target_data.get("product_id", ""),
        core_total_ul=round(core_total, 4),
        module_total_ul=round(module_total, 4),
        total_ul=round(total_raw, 4),
        rows=tuple(rows),
    )

    # Validate
    validation_errors = validate_partition(partition, total_raw, core_total, module_total)
    anchor_errors = validate_anchor_floors(partition, envelope)

    result = partition.as_dict()
    result["envelope"] = envelope.as_dict()
    result["scored_materials"] = scored_materials
    result["validation"] = {
        "partition_errors": validation_errors,
        "anchor_errors": anchor_errors,
        "valid": len(validation_errors) == 0 and len(anchor_errors) == 0,
    }
    result["mode"] = args.mode or "STRUCTURAL_CHASSIS"
    result["generated_at"] = datetime.now(timezone.utc).isoformat()

    return result


def _render_chassis_markdown(result: dict[str, Any]) -> str:
    """Render chassis result as project-format markdown."""
    lines: list[str] = []
    lines.append("# Structural Chassis")
    lines.append("")
    lines.append(
        f"**Date:** {result.get('generated_at', 'unknown')[:10]}  "
        f"| **Mode:** {result.get('mode', 'STRUCTURAL_CHASSIS')}"
    )
    lines.append("")
    lines.append("## Concept Lock")
    lines.append("")
    lines.append(f"- Formula: {result.get('formula_name', 'Unnamed')}")
    lines.append(f"- Core total: {result.get('core_total_ul', 0):.1f} µL")
    lines.append(f"- Module socket: {result.get('module_total_ul', 0):.1f} µL")
    lines.append(f"- Total: {result.get('total_ul', 0):.1f} µL")
    lines.append("")
    lines.append("## Formula Table")
    lines.append("")
    lines.append("| # | Ingredient | Stock | Raw uL | Active uL | Role |")
    lines.append("|---|------------|-------|--------|-----------|------|")
    for i, row in enumerate(result.get("rows", []), start=1):
        lines.append(
            f"| {i} | {row['ingredient']} | neat | {row['raw_ul']:.1f} | "
            f"{row['active_ul']:.1f} | {row['classification']} |"
        )
    lines.append("")
    lines.append("## Chassis Partition")
    lines.append("")
    lines.append("| Ingredient | Core uL | Module uL | Classification |")
    lines.append("|------------|---------|-----------|----------------|")
    for row in result.get("rows", []):
        lines.append(
            f"| {row['ingredient']} | {row['core_raw_ul']:.1f} | "
            f"{row['module_raw_ul']:.1f} | {row['classification']} |"
        )
    lines.append("")
    lines.append("## Flanker Interface")
    lines.append("")
    lines.append(f"- Socket capacity: {result.get('module_total_ul', 0):.1f} µL")
    lines.append("- DPG reserve slot: 200-400 µL for carrier/diluent")
    lines.append("- Module materials must not exceed socket capacity")
    lines.append("- Anchor floors are enforced by validation")
    lines.append("")
    validation = result.get("validation", {})
    if validation.get("valid"):
        lines.append("**Validation: PASS**")
    else:
        lines.append("**Validation: FAIL**")
        for err in validation.get("partition_errors", []):
            lines.append(f"- Partition error: {err}")
        for err in validation.get("anchor_errors", []):
            lines.append(f"- Anchor error: {err}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subcommand: module
# ---------------------------------------------------------------------------


def _cmd_module(args: argparse.Namespace) -> dict[str, Any]:
    """Generate a flanker module formula from a chassis."""
    if not _HAS_CHASSIS:
        return {"status": "ERROR", "detail": f"chassis module not available: {_CHASSIS_ERR}"}

    chassis_path = Path(args.chassis)
    if not chassis_path.is_absolute():
        chassis_path = PROJECT_ROOT / chassis_path
    if not chassis_path.exists():
        return {"status": "ERROR", "detail": f"Chassis file not found: {chassis_path}"}

    with open(chassis_path, encoding="utf-8") as f:
        chassis_data: dict[str, Any] = json.load(f)

    # Resolve direction
    direction = args.direction or ""
    envelope_key = _resolve_direction(direction)
    if not envelope_key:
        return {
            "status": "ERROR",
            "detail": (
                f"Could not resolve direction '{direction}'. "
                f"Available: {list(MODULE_ENVELOPES.keys())}"
            ),
        }

    envelope_spec = MODULE_ENVELOPES[envelope_key]
    _ar2 = envelope_spec["active_range"]
    _cr2 = envelope_spec["carrier_range"]
    envelope = ModuleEnvelope(
        socket_raw_ul=float(envelope_spec["socket_raw_ul"]),
        active_range=(float(_ar2[0]), float(_ar2[1])),
        carrier_range=(float(_cr2[0]), float(_cr2[1])),
        anchor_minimums=dict(envelope_spec["anchor_minimums"]),
        required_roles=tuple(envelope_spec["required_roles"]),
        family_caps=dict(envelope_spec["family_caps"]),
        temporal_ranges={
            k: (float(v[0]), float(v[1])) for k, v in envelope_spec["temporal_ranges"].items()
        },
        forbidden_materials=tuple(envelope_spec["forbidden_materials"]),
    )

    # Extract module-mobile materials from chassis
    rows_data = chassis_data.get("rows", [])
    module_materials: list[dict[str, Any]] = []
    for row in rows_data:
        module_ul = float(row.get("module_raw_ul", 0.0))
        if module_ul > 0:
            module_materials.append(
                {
                    "ingredient": row["ingredient"],
                    "module_raw_ul": module_ul,
                    "classification": row.get("classification", ""),
                }
            )

    # Build module formula
    module_rows: list[dict[str, Any]] = []
    for mm in module_materials:
        module_rows.append(
            {
                "identity": mm["ingredient"],
                "raw_amount": mm["module_raw_ul"],
                "active_amount_median": mm["module_raw_ul"],
                "concentration": 1.0,
                "concentration_basis": "v/v",
                "carrier": "",
                "functional_roles": ["module"],
            }
        )

    # Add DPG carrier to fill socket
    current_module_total = sum(r["raw_amount"] for r in module_rows)
    socket_capacity = envelope.socket_raw_ul
    dpg_needed = max(0.0, socket_capacity - current_module_total)
    if dpg_needed > 0:
        module_rows.append(
            {
                "identity": "Dipropylene Glycol",
                "raw_amount": dpg_needed,
                "active_amount_median": 0.0,
                "concentration": 1.0,
                "concentration_basis": "v/v",
                "carrier": "DPG",
                "functional_roles": ["carrier"],
            }
        )

    result: dict[str, Any] = {
        "module_name": envelope_spec["label"],
        "direction": direction,
        "envelope_key": envelope_key,
        "envelope": envelope.as_dict(),
        "module_rows": module_rows,
        "module_total_ul": round(sum(r["raw_amount"] for r in module_rows), 4),
        "socket_capacity_ul": socket_capacity,
        "dpg_carrier_ul": round(dpg_needed, 4),
        "chassis_source": str(chassis_path),
        "mode": args.mode or "FLANKER_MODULE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return result


def _render_module_markdown(result: dict[str, Any]) -> str:
    """Render module result as project-format markdown."""
    lines: list[str] = []
    lines.append(f"# Flanker Module: {result.get('module_name', 'Unnamed')}")
    lines.append("")
    lines.append(
        f"**Date:** {result.get('generated_at', 'unknown')[:10]}  "
        f"| **Direction:** {result.get('direction', 'unknown')}  "
        f"| **Mode:** {result.get('mode', 'FLANKER_MODULE')}"
    )
    lines.append("")
    lines.append("## Module Formula")
    lines.append("")
    lines.append("| # | Ingredient | Stock | Raw uL | Active uL | Role |")
    lines.append("|---|------------|-------|--------|-----------|------|")
    for i, row in enumerate(result.get("module_rows", []), start=1):
        role = (row.get("functional_roles") or ["module"])[0]
        lines.append(
            f"| {i} | {row['identity']} | neat | {row['raw_amount']:.1f} | "
            f"{row['active_amount_median']:.1f} | {role} |"
        )
    lines.append("")
    lines.append("## Socket Summary")
    lines.append("")
    lines.append(f"- Socket capacity: {result.get('socket_capacity_ul', 0):.1f} µL")
    lines.append(f"- Module total: {result.get('module_total_ul', 0):.1f} µL")
    lines.append(f"- DPG carrier: {result.get('dpg_carrier_ul', 0):.1f} µL")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subcommand: validate
# ---------------------------------------------------------------------------


def _cmd_validate(args: argparse.Namespace) -> dict[str, Any]:
    """Validate a chassis partition."""
    if not _HAS_CHASSIS:
        return {"status": "ERROR", "detail": f"chassis module not available: {_CHASSIS_ERR}"}

    chassis_path = Path(args.chassis)
    if not chassis_path.is_absolute():
        chassis_path = PROJECT_ROOT / chassis_path
    if not chassis_path.exists():
        return {"status": "ERROR", "detail": f"Chassis file not found: {chassis_path}"}

    with open(chassis_path, encoding="utf-8") as f:
        chassis_data: dict[str, Any] = json.load(f)

    # Reconstruct ChassisPartition from data
    rows_data = chassis_data.get("rows", [])
    rows: list[ChassisRow] = []
    for rd in rows_data:
        rows.append(
            ChassisRow(
                ingredient=rd.get("ingredient", ""),
                raw_ul=float(rd.get("raw_ul", 0.0)),
                active_ul=float(rd.get("active_ul", 0.0)),
                core_raw_ul=float(rd.get("core_raw_ul", 0.0)),
                module_raw_ul=float(rd.get("module_raw_ul", 0.0)),
                classification=rd.get("classification", ""),
            )
        )

    partition = ChassisPartition(
        formula_name=chassis_data.get("formula_name", ""),
        core_total_ul=float(chassis_data.get("core_total_ul", 0.0)),
        module_total_ul=float(chassis_data.get("module_total_ul", 0.0)),
        total_ul=float(chassis_data.get("total_ul", 0.0)),
        rows=tuple(rows),
    )

    # Validate partition totals
    errors = validate_partition(
        partition,
        partition.total_ul,
        partition.core_total_ul,
        partition.module_total_ul,
    )

    # Validate row sums
    for row in partition.rows:
        if abs(row.core_raw_ul + row.module_raw_ul - row.raw_ul) > 1e-6:
            errors.append(
                f"{row.ingredient}: core({row.core_raw_ul}) + module({row.module_raw_ul}) "
                f"!= raw({row.raw_ul})"
            )

    # Validate envelope if present
    envelope_data = chassis_data.get("envelope")
    if envelope_data:
        _ar3 = envelope_data.get("active_range", (100.0, 500.0))
        _cr3 = envelope_data.get("carrier_range", (200.0, 600.0))
        envelope = ModuleEnvelope(
            socket_raw_ul=float(envelope_data.get("socket_raw_ul", 1000.0)),
            active_range=(float(_ar3[0]), float(_ar3[1])),
            carrier_range=(float(_cr3[0]), float(_cr3[1])),
            anchor_minimums=dict(envelope_data.get("anchor_minimums", {})),
            required_roles=tuple(envelope_data.get("required_roles", ())),
            family_caps=dict(envelope_data.get("family_caps", {})),
            temporal_ranges={
                k: (float(v[0]), float(v[1]))
                for k, v in envelope_data.get("temporal_ranges", {}).items()
            },
            forbidden_materials=tuple(envelope_data.get("forbidden_materials", ())),
        )
        anchor_errors = validate_anchor_floors(partition, envelope)
        errors.extend(anchor_errors)

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "formula_name": partition.formula_name,
        "total_ul": partition.total_ul,
        "core_total_ul": partition.core_total_ul,
        "module_total_ul": partition.module_total_ul,
        "row_count": len(partition.rows),
    }


# ---------------------------------------------------------------------------
# Remaining stub subcommands: SENSORY_EXPERIMENT,
# ANALYTICAL_INTERPRETATION, COMPLIANCE_BUILD, RELEASE_REVIEW,
# INVENTORY_MAPPING
# ---------------------------------------------------------------------------


_BATCH_UNITS = {"uL", "mL", "mg", "g"}
_BATCH_OPERATIONS = {
    "REPLAY",
    "PROPOSE",
    "CONFIRM",
    "MEASURE",
    "COMMIT",
    "EVALUATE",
}


def _decimal_text(value: object, field: str, *, positive: bool = True) -> str:
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"{field} must be a decimal number") from exc
    if not number.is_finite() or (number <= 0 if positive else number < 0):
        qualifier = "greater than zero" if positive else "nonnegative"
        raise ValueError(f"{field} must be finite and {qualifier}")
    rendered = format(number.normalize(), "f")
    return "0" if rendered in {"-0", ""} else rendered


def _canonical_batch_unit(value: str) -> str:
    unit = {"ul": "uL", "µl": "uL", "ml": "mL", "mg": "mg", "g": "g"}.get(
        str(value).strip().casefold()
    )
    if unit not in _BATCH_UNITS:
        raise ValueError(f"unsupported batch quantity unit: {value}")
    return unit


def _mass_for_batch_quantity(
    amount_decimal: str,
    unit: str,
    density_g_ml_decimal: str | None,
) -> tuple[str, dict[str, Any]]:
    amount = Decimal(amount_decimal)
    density: Decimal | None = None
    if unit in {"uL", "mL"}:
        if density_g_ml_decimal is None:
            raise ValueError(
                "stock density in g/mL is required only because the canonical bottle ledger "
                "must convert this liquid transfer to mass"
            )
        density_text = _decimal_text(density_g_ml_decimal, "stock_density_g_ml")
        density = Decimal(density_text)
        volume_ml = amount / Decimal("1000") if unit == "uL" else amount
        mass = volume_ml * density
        basis = {
            "conversion": "LIQUID_VOLUME_TIMES_EXPLICIT_DENSITY",
            "density_g_ml_decimal": density_text,
        }
    elif unit == "mg":
        mass = amount / Decimal("1000")
        basis = {"conversion": "MASS_UNIT_CONVERSION_ONLY"}
    else:
        mass = amount
        basis = {"conversion": "NO_CONVERSION"}
    return _decimal_text(mass, "planned_mass_g"), basis


def _local_api_base(value: str) -> str:
    parsed = urlparse(str(value).strip())
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("batch lifecycle API must be an explicit loopback HTTP URL")
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError("batch lifecycle API URL must not contain credentials, query, or fragment")
    return str(value).rstrip("/")


def _request_json(
    *,
    api_base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{_local_api_base(api_base_url)}/{path.lstrip('/')}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310 - loopback is validated
            content = response.read().decode("utf-8")
    except HTTPError as exc:
        content = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(content)
        except json.JSONDecodeError:
            detail = {"error": {"code": "HTTP_ERROR", "message": content[:500]}}
        return {"status": "BLOCKED", "http_status": exc.code, **detail}
    except URLError as exc:
        return {
            "status": "BLOCKED",
            "error": {
                "code": "LOCAL_LIFECYCLE_API_UNAVAILABLE",
                "message": str(exc.reason),
            },
        }
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("local lifecycle API returned non-JSON content") from exc
    if not isinstance(result, dict):
        raise ValueError("local lifecycle API returned a non-object response")
    return result


def _requested_batch_quantity(args: argparse.Namespace, *, actual: bool = False) -> dict[str, Any]:
    amount_value = getattr(args, "actual_amount", None) if actual else getattr(args, "amount", None)
    unit_value = getattr(args, "actual_unit", None) if actual else getattr(args, "unit", None)
    if amount_value is None and not actual and getattr(args, "amount_ul", None) is not None:
        amount_value = args.amount_ul
        unit_value = "uL"
    if actual and amount_value is None:
        amount_value = getattr(args, "amount", None)
        unit_value = unit_value or getattr(args, "unit", None)
    if amount_value is None or unit_value is None:
        raise ValueError("this lifecycle operation requires --amount and --unit")
    amount_text = _decimal_text(amount_value, "amount")
    unit = _canonical_batch_unit(unit_value)
    mass_g, conversion = _mass_for_batch_quantity(
        amount_text,
        unit,
        getattr(args, "stock_density_g_ml", None),
    )
    return {
        "amount_decimal": amount_text,
        "unit": unit,
        "mass_g_decimal": mass_g,
        "conversion": conversion,
    }


def _batch_lifecycle(args: argparse.Namespace, *, rescue: bool) -> dict[str, Any]:
    operation = str(args.operation).strip().upper()
    if operation not in _BATCH_OPERATIONS:
        raise ValueError(f"unsupported batch lifecycle operation: {operation}")
    mode = "BATCH_RESCUE" if rescue else "LIVE_BATCH"
    api_base = _local_api_base(args.api_base_url)
    bottle_id = str(args.batch_id).strip()
    if not bottle_id:
        raise ValueError("batch_id must not be blank")
    if operation == "REPLAY":
        response = _request_json(
            api_base_url=api_base,
            method="GET",
            path=f"bottles/{bottle_id}/replay",
        )
        return {
            "status": "BLOCKED" if response.get("status") == "BLOCKED" else "BOTTLE_REPLAY",
            "mode": mode,
            "server": response,
        }

    proposal_id = str(getattr(args, "proposal_id", "") or "").strip()
    now = datetime.now(timezone.utc).isoformat()
    actor = str(args.actor).strip()
    reason = str(getattr(args, "reason", "") or "Personal evolving-bottle delta").strip()
    if operation == "PROPOSE":
        try:
            quantity = _requested_batch_quantity(args)
        except ValueError as exc:
            if "greater than zero" in str(exc) and rescue:
                return {
                    "status": "ADDITIVE_REPAIR_NOT_FEASIBLE",
                    "mode": mode,
                    "formula_action": "NO_CHANGE",
                    "reason": "An evolving bottle cannot execute a negative or zero removal delta.",
                }
            raise
        material = str(getattr(args, "material", "") or "").strip()
        if not material:
            raise ValueError("PROPOSE requires --material")
        reservation_id = str(getattr(args, "reservation_id", "") or "").strip()
        idempotency_key = str(getattr(args, "idempotency_key", "") or "").strip()
        if not reservation_id or not idempotency_key or args.expected_sequence is None:
            raise ValueError(
                "PROPOSE requires --reservation-id, --expected-sequence, and --idempotency-key"
            )
        density_note = quantity["conversion"].get("density_g_ml_decimal")
        rationale = (
            f"{reason}; material_label={material}; requested_quantity="
            f"{quantity['amount_decimal']} {quantity['unit']}"
            + (f"; density_g_ml={density_note}" if density_note else "")
        )
        response = _request_json(
            api_base_url=api_base,
            method="POST",
            path="actions",
            payload={
                "schema_version": "evolving-bottle-action-v1",
                "reservation_id": reservation_id,
                "bottle_id": bottle_id,
                "action_type": "ADD_STOCK",
                "planned_mass_g": float(Decimal(quantity["mass_g_decimal"])),
                "expected_sequence": args.expected_sequence,
                "idempotency_key": idempotency_key,
                "actor": actor,
                "rationale": rationale,
            },
        )
        return {
            "status": "PROPOSAL_RECORDED" if response.get("status") != "BLOCKED" else "BLOCKED",
            "mode": mode,
            "delta_card": {
                "add": f"{quantity['amount_decimal']} {quantity['unit']} of {material}",
                "purpose": reason,
                "state": "PROPOSAL_ONLY",
                "requested_quantity": quantity,
                "negative_delta_allowed": False,
            },
            "server": response,
        }
    if not proposal_id:
        raise ValueError(f"{operation} requires --proposal-id")
    if operation == "EVALUATE":
        command_id = str(getattr(args, "idempotency_key", "") or "").strip()
        reaction = str(getattr(args, "reaction", "") or "").strip()
        if not command_id or args.expected_sequence is None:
            raise ValueError(
                "EVALUATE requires --idempotency-key and --expected-sequence"
            )
        if not reaction or args.waited_seconds is None:
            raise ValueError("EVALUATE requires --reaction and --waited-seconds")
        waited_seconds = float(
            Decimal(_decimal_text(args.waited_seconds, "waited_seconds", positive=False))
        )
        response = _request_json(
            api_base_url=api_base,
            method="POST",
            path=f"actions/{proposal_id}/evaluations",
            payload={
                "schema_version": "evolving-bottle-evaluation-v1",
                "bottle_id": bottle_id,
                "expected_sequence": args.expected_sequence,
                "command_id": command_id,
                "actor": actor,
                "evaluated_at": args.occurred_at or now,
                "waited_seconds": waited_seconds,
                "reaction": reaction,
                "decision": args.evaluation_decision,
            },
        )
        return {
            "status": (
                "BLOCKED"
                if response.get("status") == "BLOCKED"
                else "EVALUATION_RECORDED"
            ),
            "mode": mode,
            "evidence_scope": "SEQUENTIAL_PERSONAL_OBSERVATION",
            "server": response,
        }
    if operation == "CONFIRM":
        decision = str(args.decision).strip().upper()
        response = _request_json(
            api_base_url=api_base,
            method="POST",
            path=f"actions/{proposal_id}/confirmations",
            payload={
                "decision": decision,
                "confirmer_pseudonym": args.confirmer,
                "confirmed_at": args.occurred_at or now,
                "rationale": reason,
            },
        )
        return {
            "status": (
                "BLOCKED" if response.get("status") == "BLOCKED" else "CONFIRMATION_RECORDED"
            ),
            "mode": mode,
            "server": response,
        }
    if operation == "MEASURE":
        quantity = _requested_batch_quantity(args, actual=True)
        response = _request_json(
            api_base_url=api_base,
            method="POST",
            path=f"actions/{proposal_id}/measurements",
            payload={
                "quantity_kind": "mass",
                "value": float(Decimal(quantity["mass_g_decimal"])),
                "unit": "g",
                "standard_uncertainty": (
                    None
                    if args.standard_uncertainty_g is None
                    else float(Decimal(_decimal_text(args.standard_uncertainty_g, "standard_uncertainty_g", positive=False)))
                ),
                "method": args.measurement_method,
                "measured_at": args.occurred_at or now,
                "actor": actor,
            },
        )
        return {
            "status": "BLOCKED" if response.get("status") == "BLOCKED" else "MEASUREMENT_RECORDED",
            "mode": mode,
            "actual_quantity": quantity,
            "server": response,
        }
    response = _request_json(
        api_base_url=api_base,
        method="POST",
        path=f"actions/{proposal_id}/commit",
        payload={"actor": actor, "rationale": reason},
    )
    return {
        "status": "BLOCKED" if response.get("status") == "BLOCKED" else "COMMIT_RECORDED",
        "mode": mode,
        "server": response,
    }


def handle_live_batch(args: argparse.Namespace) -> dict[str, Any]:
    """Use the server-owned, replay-safe evolving-bottle lifecycle."""

    try:
        return _batch_lifecycle(args, rescue=False)
    except ValueError as exc:
        return {"status": "ERROR", "mode": "LIVE_BATCH", "detail": str(exc)}


def handle_batch_rescue(args: argparse.Namespace) -> dict[str, Any]:
    """Use the same positive-only lifecycle for a corrective bottle delta."""

    try:
        return _batch_lifecycle(args, rescue=True)
    except ValueError as exc:
        return {"status": "ERROR", "mode": "BATCH_RESCUE", "detail": str(exc)}


def handle_sensory_experiment(args: argparse.Namespace) -> dict[str, Any]:
    """Design a blind sensory trial (stub)."""
    print(
        "NOT_IMPLEMENTED: Mode SENSORY_EXPERIMENT requires the "
        "experiments/planner and sensory/ledger modules.",
        file=sys.stderr,
    )
    print(
        "To complete: generate coded samples, time-point evaluation sheets, "
        "and blind trial protocol.",
        file=sys.stderr,
    )
    print(file=sys.stderr)
    # Demonstration: try to import the planner module
    try:
        from engine.experiments.planner import design_blind_trial  # type: ignore[import-untyped]

        print("  engine.experiments.planner.design_blind_trial available", file=sys.stderr)
    except ImportError:
        print("  engine.experiments.planner not yet implemented", file=sys.stderr)
    print(f"  output path: {args.output}", file=sys.stderr)
    return {
        "status": "NOT_IMPLEMENTED",
        "mode": "SENSORY_EXPERIMENT",
        "output": args.output,
    }


def handle_analytical_interpretation(args: argparse.Namespace) -> dict[str, Any]:
    """Ingest GC-MS / HS-SPME instrument data (stub)."""
    print(
        "NOT_IMPLEMENTED: Mode ANALYTICAL_INTERPRETATION requires GC-MS/HS-SPME data ingestion.",
        file=sys.stderr,
    )
    print(
        "To complete: parse instrument export files, align RI/OAV with known "
        "standards, populate GCMSPeak and GCOEvent records in AnalyticalLedger.",
        file=sys.stderr,
    )
    print(file=sys.stderr)
    print(f"  data file: {args.data_file}", file=sys.stderr)
    return {
        "status": "NOT_IMPLEMENTED",
        "mode": "ANALYTICAL_INTERPRETATION",
        "data_file": args.data_file,
    }


def handle_compliance_build(args: argparse.Namespace) -> dict[str, Any]:
    """Generate a jurisdiction-compliant formula (stub)."""
    print(
        "NOT_IMPLEMENTED: Mode COMPLIANCE_BUILD requires versioned IFRA/ECHA regulatory snapshots.",
        file=sys.stderr,
    )
    print(
        "To complete: load target formula, apply jurisdiction-specific IFRA "
        "limits, generate compliant build with capped doses, produce "
        "substitution report.",
        file=sys.stderr,
    )
    print(file=sys.stderr)
    # Demonstration: try to import the regulatory module
    try:
        from engine.safety.regulatory import check_compliance  # type: ignore[import-untyped]

        print("  engine.safety.regulatory.check_compliance available", file=sys.stderr)
    except ImportError:
        print("  engine.safety.regulatory not yet implemented", file=sys.stderr)
    print(f"  target: {args.target}", file=sys.stderr)
    print(f"  jurisdiction: {args.jurisdiction}", file=sys.stderr)
    print(f"  product_category: {args.product_category}", file=sys.stderr)
    return {
        "status": "NOT_IMPLEMENTED",
        "mode": "COMPLIANCE_BUILD",
        "target": args.target,
        "jurisdiction": args.jurisdiction,
        "product_category": args.product_category,
    }


def handle_release_review(args: argparse.Namespace) -> dict[str, Any]:
    """Delegate to formula_release_gate.py for full gate evaluation."""
    import subprocess

    formula_file = args.formula_file
    concentrate_ul = args.concentrate_ul or 4500

    print(
        "NOT_IMPLEMENTED: Mode RELEASE_REVIEW delegates to "
        "formula_release_gate.py for full gate evaluation.",
        file=sys.stderr,
    )
    print(file=sys.stderr)
    print(
        f"  Running: python scripts/formula_release_gate.py --formula-file {formula_file} ...",
        file=sys.stderr,
    )
    print(file=sys.stderr)

    cmd = [
        sys.executable,
        "scripts/formula_release_gate.py",
        "--formula-file",
        formula_file,
        "--expected-concentrate-ul",
        str(concentrate_ul),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return {
        "status": "NOT_IMPLEMENTED" if result.returncode != 0 else "OK",
        "mode": "RELEASE_REVIEW",
        "formula_file": formula_file,
        "concentrate_ul": concentrate_ul,
        "subprocess_returncode": result.returncode,
    }


def handle_inventory_mapping(args: argparse.Namespace) -> dict[str, Any]:
    """Map a target formula to available inventory (stub)."""
    print(
        "NOT_IMPLEMENTED: Mode INVENTORY_MAPPING requires the "
        "inventory/stock_model and build/ledger modules.",
        file=sys.stderr,
    )
    print(
        "To complete: load target formula, map each row to inventory via "
        "engine.inventory.stock_model.map_target_to_inventory(), generate "
        "substitution report, create build formula.",
        file=sys.stderr,
    )
    print(file=sys.stderr)

    # Demonstration: try to load target JSON and call map_target_to_inventory
    target_path = Path(args.target)
    if not target_path.is_absolute():
        target_path = PROJECT_ROOT / target_path
    if target_path.exists():
        print(f"  Target loaded: {target_path}", file=sys.stderr)
        try:
            from engine.inventory.stock_model import (  # type: ignore[import-untyped]
                map_target_to_inventory,
            )

            print(
                "  engine.inventory.stock_model.map_target_to_inventory available", file=sys.stderr
            )
        except ImportError:
            print("  engine.inventory.stock_model not yet implemented", file=sys.stderr)
    else:
        print(f"  Target file not found: {target_path}", file=sys.stderr)

    print(f"  inventory: {args.inventory}", file=sys.stderr)
    return {
        "status": "NOT_IMPLEMENTED",
        "mode": "INVENTORY_MAPPING",
        "target": args.target,
        "inventory": args.inventory,
    }


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reconstruction pipeline CLI - evidence to target to chassis to modules."
    )
    parser.add_argument(
        "--mode",
        default="RECONSTRUCTION",
        choices=MODE_CHOICES,
        help="Pipeline mode (default: RECONSTRUCTION)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    parser.add_argument(
        "--brief",
        default="",
        help="Family archetype brief (e.g. 'aromatic_fougere', 'chypre')",
    )
    parser.add_argument(
        "--preset",
        default="MEDIUM",
        help="Rank prior preset (default: MEDIUM). Available: FLAT, MEDIUM, STEEP, etc.",
    )
    parser.add_argument(
        "--target-total-ul",
        type=float,
        default=0.0,
        help="Target total active µL for dose reconciliation (default: from preset)",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand")

    # build
    build_parser = subparsers.add_parser("build", help="Build target formula from evidence")
    build_parser.add_argument("--evidence", required=True, help="Path to evidence JSON file")
    build_parser.add_argument("--output", required=True, help="Path for output target JSON")

    # chassis
    chassis_parser = subparsers.add_parser("chassis", help="Derive structural chassis from target")
    chassis_parser.add_argument("--target", required=True, help="Path to target JSON file")
    chassis_parser.add_argument("--envelope", required=True, help="Path to envelope JSON file")
    chassis_parser.add_argument("--output", required=True, help="Path for output chassis file")

    # module
    module_parser = subparsers.add_parser("module", help="Generate flanker module formula")
    module_parser.add_argument("--chassis", required=True, help="Path to chassis JSON file")
    module_parser.add_argument(
        "--direction",
        required=True,
        help="Module direction (e.g. 'electric citrus', 'creamy iris')",
    )
    module_parser.add_argument("--output", required=True, help="Path for output module file")

    # validate
    validate_parser = subparsers.add_parser("validate", help="Validate a chassis partition")
    validate_parser.add_argument("--chassis", required=True, help="Path to chassis JSON file")

    def add_batch_lifecycle_arguments(
        command_parser: argparse.ArgumentParser,
        *,
        rescue: bool,
    ) -> None:
        command_parser.add_argument("--batch-id", required=True, help="Bottle/batch identifier")
        command_parser.add_argument(
            "--operation",
            choices=sorted(_BATCH_OPERATIONS),
            default="PROPOSE",
            help="One explicit lifecycle step; no step automatically commits the next",
        )
        command_parser.add_argument("--material", help="Human-readable material label")
        command_parser.add_argument("--amount", help="Requested positive addition as a decimal")
        command_parser.add_argument("--unit", choices=sorted(_BATCH_UNITS), help="uL, mL, mg, or g")
        command_parser.add_argument(
            "--amount-ul",
            help="Backward-compatible alias for --amount <value> --unit uL",
        )
        command_parser.add_argument(
            "--stock-density-g-ml",
            help="Required only when converting a liquid uL/mL transfer for the mass ledger",
        )
        command_parser.add_argument("--reservation-id", help="Active server-owned reservation")
        command_parser.add_argument("--expected-sequence", type=int, help="Current bottle stream sequence")
        command_parser.add_argument("--idempotency-key", help="Replay-safe proposal identity")
        command_parser.add_argument("--proposal-id", help="Proposal used by confirm/measure/commit")
        command_parser.add_argument(
            "--decision",
            choices=("CONFIRMED", "REJECTED"),
            default="CONFIRMED",
        )
        command_parser.add_argument("--confirmer", default="personal-research-user")
        command_parser.add_argument("--actual-amount", help="Actual transferred amount for MEASURE")
        command_parser.add_argument(
            "--actual-unit",
            choices=sorted(_BATCH_UNITS),
            help="Actual transfer unit; defaults to --unit",
        )
        command_parser.add_argument(
            "--standard-uncertainty-g",
            help="Optional gravimetric standard uncertainty in g",
        )
        command_parser.add_argument(
            "--measurement-method",
            default="user-confirmed-transfer-with-explicit-unit-conversion-v1",
        )
        command_parser.add_argument("--occurred-at", help="Aware ISO timestamp; defaults to now")
        command_parser.add_argument(
            "--waited-seconds",
            help="Elapsed time before an EVALUATE reaction",
        )
        command_parser.add_argument(
            "--reaction",
            help="One short personal sensory reaction for EVALUATE",
        )
        command_parser.add_argument(
            "--evaluation-decision",
            choices=("CONTINUE", "HOLD", "DILUTE", "STOP", "CANNOT_DETERMINE"),
            default="HOLD",
        )
        command_parser.add_argument("--actor", default="personal-research-user")
        command_parser.add_argument(
            "--api-base-url",
            default="http://127.0.0.1:8000/api/v1/lab/v2",
            help="Loopback Perfume-Chem API only",
        )
        command_parser.add_argument(
            "--reason",
            required=rescue,
            default=None,
            help="Short purpose for the additive delta",
        )

    # live-batch
    batch_parser = subparsers.add_parser(
        "live-batch", help="Run one replay-safe evolving-bottle lifecycle step"
    )
    add_batch_lifecycle_arguments(batch_parser, rescue=False)
    batch_parser.set_defaults(func=handle_live_batch)

    # batch-rescue
    rescue_parser = subparsers.add_parser(
        "batch-rescue", help="Run one positive-only corrective bottle lifecycle step"
    )
    add_batch_lifecycle_arguments(rescue_parser, rescue=True)
    rescue_parser.set_defaults(func=handle_batch_rescue)

    # sensory-experiment
    sensory_parser = subparsers.add_parser(
        "sensory-experiment", help="Design blind sensory trial (stub)"
    )
    sensory_parser.add_argument("--output", required=True, help="Output path for trial protocol")
    sensory_parser.set_defaults(func=handle_sensory_experiment)

    # analytical-interpretation
    analytical_parser = subparsers.add_parser(
        "analytical-interpretation", help="Ingest GC-MS/HS-SPME data (stub)"
    )
    analytical_parser.add_argument(
        "--data-file", required=True, help="Path to instrument export file"
    )
    analytical_parser.set_defaults(func=handle_analytical_interpretation)

    # compliance-build
    compliance_parser = subparsers.add_parser(
        "compliance-build", help="Generate jurisdiction-compliant formula (stub)"
    )
    compliance_parser.add_argument("--target", required=True, help="Path to target formula JSON")
    compliance_parser.add_argument(
        "--jurisdiction", default="EU", help="Jurisdiction code (default: EU)"
    )
    compliance_parser.add_argument(
        "--product-category",
        default="leave_on_edp",
        help="Product category (default: leave_on_edp)",
    )
    compliance_parser.set_defaults(func=handle_compliance_build)

    # release-review
    release_parser = subparsers.add_parser(
        "release-review", help="Run full gate evaluation via formula_release_gate.py"
    )
    release_parser.add_argument(
        "--formula-file", required=True, help="Path to formula markdown file"
    )
    release_parser.add_argument(
        "--concentrate-ul", type=float, default=4500, help="Expected concentrate µL (default: 4500)"
    )
    release_parser.set_defaults(func=handle_release_review)

    # inventory-mapping
    inventory_parser = subparsers.add_parser(
        "inventory-mapping", help="Map target formula to available inventory (stub)"
    )
    inventory_parser.add_argument("--target", required=True, help="Path to target formula JSON")
    inventory_parser.add_argument("--inventory", required=True, help="Path to inventory file")
    inventory_parser.set_defaults(func=handle_inventory_mapping)

    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return 1

    # Dispatch
    if args.subcommand == "build":
        result = _cmd_build(args)
    elif args.subcommand == "chassis":
        result = _cmd_chassis(args)
    elif args.subcommand == "module":
        result = _cmd_module(args)
    elif args.subcommand == "validate":
        result = _cmd_validate(args)
    elif args.subcommand in (
        "live-batch",
        "batch-rescue",
        "sensory-experiment",
        "analytical-interpretation",
        "compliance-build",
        "release-review",
        "inventory-mapping",
    ):
        result = args.func(args)
    else:
        print(f"Unknown subcommand: {args.subcommand}", file=sys.stderr)
        return 1

    # Handle errors
    if isinstance(result, dict) and result.get("status") == "ERROR":
        detail = result.get("detail", "Unknown error")
        print(f"ERROR: {detail}", file=sys.stderr)
        if args.json:
            print(json.dumps(result, indent=2))
        return 1

    # Output
    if args.subcommand == "validate":
        is_pass = result.get("status") == "PASS"
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Validation: {result['status']}")
            for err in result.get("errors", []):
                print(f"  FAIL: {err}")
            if is_pass:
                print(f"  All {result.get('row_count', 0)} rows valid")
        return 0 if is_pass else 1

    # Lifecycle and compatibility subcommands: print JSON if requested and return.
    if args.subcommand in (
        "live-batch",
        "batch-rescue",
        "sensory-experiment",
        "analytical-interpretation",
        "compliance-build",
        "release-review",
        "inventory-mapping",
    ):
        if args.json:
            print(json.dumps(result, indent=2))
        return 0

    # Write output file
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    if args.subcommand == "chassis":
        # Write both markdown and JSON
        md = _render_chassis_markdown(result)
        json_path = output_path.with_suffix(".json")
        md_path = output_path.with_suffix(".md") if output_path.suffix != ".md" else output_path

        md_path.write_text(md, encoding="utf-8")
        json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Chassis written to:")
            print(f"  Markdown: {md_path}")
            print(f"  JSON:     {json_path}")
            print(
                f"  Core: {result.get('core_total_ul', 0):.1f} µL  |  "
                f"Module: {result.get('module_total_ul', 0):.1f} µL  |  "
                f"Total: {result.get('total_ul', 0):.1f} µL"
            )
            validation = result.get("validation", {})
            if validation.get("valid"):
                print("  Validation: PASS")
            else:
                print("  Validation: FAIL")
                for err in validation.get("partition_errors", []):
                    print(f"    Partition: {err}")
                for err in validation.get("anchor_errors", []):
                    print(f"    Anchor: {err}")

    elif args.subcommand == "module":
        md = _render_module_markdown(result)
        json_path = (
            output_path.with_suffix(".json") if output_path.suffix != ".json" else output_path
        )
        md_path = output_path.with_suffix(".md") if output_path.suffix != ".md" else output_path

        md_path.write_text(md, encoding="utf-8")
        json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Module written to:")
            print(f"  Markdown: {md_path}")
            print(f"  JSON:     {json_path}")
            print(
                f"  Module: {result.get('module_name', '?')}  |  "
                f"Total: {result.get('module_total_ul', 0):.1f} µL  |  "
                f"DPG: {result.get('dpg_carrier_ul', 0):.1f} µL"
            )

    elif args.subcommand == "build":
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            material_count = len(result.get("target_materials", []))
            print(f"Target formula written to: {output_path}")
            print(f"  Materials: {material_count}")
            print(f"  Total raw: {result.get('total_raw_ul', 0):.1f} µL")
            print(f"  Total active: {result.get('total_active_ul', 0):.1f} µL")
            print(f"  Authority: {result.get('authority_label', '?')}")
            print(f"  Mode: {result.get('mode', '?')}")
            if args.brief:
                print(f"  Brief: {args.brief}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
