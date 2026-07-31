"""Read-only B8 projection of current inventory against the frozen B0 audit."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from engine.inventory_parser import InventoryMaterial, parse_inventory
from engine.name_utils import normalize_name

_GAP_STATES = (
    "ACCEPTED_EXACT",
    "ACCEPTED_SCOPED",
    "WEAK",
    "CONFLICTED",
    "UNKNOWN",
    "MISSING",
    "NOT_APPLICABLE",
)
_DASHBOARD_DIMENSIONS = (
    "EVIDENCE_CLASS",
    "PROPERTY",
    "CURRENT_INVENTORY",
    "ACTIVE_FORMULA",
    "CHEMICAL_FAMILY",
    "REGULATORY_IMPACT",
    "MODEL_SENSITIVITY",
)
_EVIDENCE_CLASSES = {
    "MEASURED",
    "LITERATURE_DERIVED",
    "SUPPLIER_PROVIDED",
    "EMPIRICALLY_CALIBRATED",
    "MODEL_ESTIMATED",
    "HEURISTIC",
    "SPECULATIVE",
    "UNKNOWN",
}
_BANNED_KEYS = {
    "OVERALL",
    "TOTAL_CONFIDENCE",
    "COVERAGE_SCORE",
    "CONFIDENCE_PERCENT",
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_scientific_inventory(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    if path.suffix.casefold() == ".gz" or raw[:2] == b"\x1f\x8b":
        decoded = gzip.decompress(raw)
    else:
        decoded = raw
    payload = json.loads(decoded.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("scientific inventory must be a JSON object")
    observations = payload.get("material_property_observations")
    if not isinstance(observations, list):
        raise ValueError(
            "scientific inventory lacks material_property_observations"
        )
    return payload, _sha256_bytes(raw)


def _inventory_key(record: InventoryMaterial) -> str:
    return normalize_name(record.identity_name or record.name)


def _evidence_class(observation: Mapping[str, object]) -> str:
    value = str(observation.get("evidence_class") or "UNKNOWN").upper()
    return value if value in _EVIDENCE_CLASSES else "UNKNOWN"


def _gap_state(observation: Mapping[str, object]) -> str:
    if observation.get("conflict_set"):
        return "CONFLICTED"
    if observation.get("current_value") is None:
        return "MISSING"
    review_state = str(observation.get("review_state") or "").upper()
    authority = str(observation.get("authority_label") or "").upper()
    evidence = _evidence_class(observation)
    if (
        review_state.startswith("LEGACY")
        or authority
        in {
            "UNATTRIBUTED_LEGACY",
            "LEGACY_HEURISTIC",
            "UNKNOWN",
        }
    ):
        if evidence in {"HEURISTIC", "SPECULATIVE"} or authority in {
            "UNATTRIBUTED_LEGACY",
            "LEGACY_HEURISTIC",
        }:
            return "WEAK"
        return "UNKNOWN"
    if evidence in {"UNKNOWN", "SPECULATIVE"}:
        return "UNKNOWN"
    return "WEAK"


def _state_counts(
    observations: Sequence[Mapping[str, object]],
) -> dict[str, int]:
    counts = Counter(str(item["state"]) for item in observations)
    return {state: int(counts.get(state, 0)) for state in _GAP_STATES}


def _dashboard_cell(
    *,
    dimension: str,
    dimension_key: str,
    observations: Sequence[Mapping[str, object]],
    material_ids: Sequence[str],
) -> dict[str, object]:
    dimension = dimension.upper()
    dimension_key = dimension_key.upper()
    if (
        dimension not in _DASHBOARD_DIMENSIONS
        or dimension in _BANNED_KEYS
        or dimension_key in _BANNED_KEYS
    ):
        raise ValueError("invalid or aggregate B8 dashboard cell")
    counts = _state_counts(observations)
    return {
        "dimension": dimension,
        "dimension_key": dimension_key,
        "material_count": len(set(material_ids)),
        "requirements_total": len(observations),
        "accepted_exact_count": counts["ACCEPTED_EXACT"],
        "accepted_scoped_count": counts["ACCEPTED_SCOPED"],
        "weak_count": counts["WEAK"],
        "conflicted_count": counts["CONFLICTED"],
        "unknown_count": counts["UNKNOWN"],
        "missing_count": counts["MISSING"],
        "not_applicable_count": counts["NOT_APPLICABLE"],
    }


def _observation_subject_map(
    observations: Sequence[Mapping[str, object]],
) -> dict[str, tuple[str, ...]]:
    subjects: dict[str, set[str]] = defaultdict(set)
    for observation in observations:
        subject = str(observation.get("subject_id") or "").strip()
        key = normalize_name(subject)
        if key:
            subjects[key].add(subject)
    return {
        key: tuple(
            sorted(
                values,
                key=lambda value: (value.casefold(), value),
            )
        )
        for key, values in subjects.items()
    }


def _match_inventory(
    records: Sequence[InventoryMaterial],
    subject_map: Mapping[str, tuple[str, ...]],
) -> tuple[
    tuple[tuple[InventoryMaterial, tuple[str, ...]], ...],
    tuple[InventoryMaterial, ...],
]:
    matched: list[tuple[InventoryMaterial, tuple[str, ...]]] = []
    unmatched: list[InventoryMaterial] = []
    for record in sorted(records, key=lambda item: item.name.casefold()):
        subjects = subject_map.get(_inventory_key(record))
        if subjects:
            matched.append((record, subjects))
        else:
            unmatched.append(record)
    return tuple(matched), tuple(unmatched)


def build_workspace_backfill_projection(
    *,
    inventory_path: Path,
    scientific_inventory_path: Path,
) -> dict[str, object]:
    """Build a deterministic, non-promoting B8 planning projection."""

    inventory_path = Path(inventory_path)
    scientific_inventory_path = Path(scientific_inventory_path)
    inventory_bytes = inventory_path.read_bytes()
    scientific, scientific_sha256 = _load_scientific_inventory(
        scientific_inventory_path
    )
    raw_all = parse_inventory(
        inventory_path,
        unique=False,
        include_solvents=True,
        include_unavailable=True,
    )
    raw_fragrance = parse_inventory(
        inventory_path,
        unique=False,
        include_solvents=False,
        include_unavailable=True,
    )
    unique_all = parse_inventory(
        inventory_path,
        unique=True,
        include_solvents=True,
        include_unavailable=True,
    )
    unique_fragrance = parse_inventory(
        inventory_path,
        unique=True,
        include_solvents=False,
        include_unavailable=True,
    )
    owned_records = tuple(
        record
        for record in unique_fragrance
        if record.status == "owned"
    )
    unavailable_records = tuple(
        record
        for record in unique_fragrance
        if record.status != "owned"
    )

    raw_observations = scientific["material_property_observations"]
    observations = [
        item
        for item in raw_observations
        if isinstance(item, dict)
    ]
    subject_map = _observation_subject_map(observations)
    matched_owned, unmatched_owned = _match_inventory(
        owned_records,
        subject_map,
    )
    matched_unavailable, _ = _match_inventory(
        unavailable_records,
        subject_map,
    )
    selected_subject_keys = {
        _inventory_key(record) for record, _ in matched_owned
    }
    projected_observations: list[dict[str, object]] = []
    for observation in observations:
        subject_id = str(observation.get("subject_id") or "")
        subject_key = normalize_name(subject_id)
        if subject_key not in selected_subject_keys:
            continue
        projected_observations.append(
            {
                "subject_id": subject_id,
                "subject_key": subject_key,
                "property_type": str(
                    observation.get("property_type") or "UNKNOWN"
                ).upper(),
                "evidence_class": _evidence_class(observation),
                "state": _gap_state(observation),
                "affects_blocking_gate": bool(
                    observation.get("affects_blocking_gate")
                ),
                "content_sha256": str(
                    observation.get("content_sha256") or ""
                ),
            }
        )
    projected_observations.sort(
        key=lambda item: (
            str(item["subject_id"]).casefold(),
            str(item["property_type"]),
            str(item["content_sha256"]),
        )
    )

    dashboard_groups: dict[
        tuple[str, str],
        list[Mapping[str, object]],
    ] = defaultdict(list)
    dashboard_materials: dict[tuple[str, str], list[str]] = defaultdict(list)
    for observation in projected_observations:
        subject_id = str(observation["subject_key"])
        dimensions = (
            ("EVIDENCE_CLASS", str(observation["evidence_class"])),
            ("PROPERTY", str(observation["property_type"])),
            ("CURRENT_INVENTORY", "OWNED_MATCHED"),
            ("ACTIVE_FORMULA", "UNKNOWN"),
            ("CHEMICAL_FAMILY", "UNKNOWN"),
            (
                "REGULATORY_IMPACT",
                (
                    "BLOCKING_GATE"
                    if observation["affects_blocking_gate"]
                    else "NON_BLOCKING"
                ),
            ),
            ("MODEL_SENSITIVITY", "UNKNOWN"),
        )
        for dimension, dimension_key in dimensions:
            key = (dimension, dimension_key)
            dashboard_groups[key].append(observation)
            dashboard_materials[key].append(subject_id)

    synthetic_materials = {
        ("CURRENT_INVENTORY", "OWNED_UNMATCHED"): [
            record.name for record in unmatched_owned
        ],
        ("CURRENT_INVENTORY", "UNAVAILABLE"): [
            record.name for record in unavailable_records
        ],
    }
    for key, material_ids in synthetic_materials.items():
        dashboard_groups.setdefault(key, [])
        dashboard_materials[key].extend(material_ids)
    for dimension in _DASHBOARD_DIMENSIONS:
        if not any(key[0] == dimension for key in dashboard_groups):
            key = (dimension, "UNKNOWN")
            dashboard_groups[key] = []
            dashboard_materials[key] = []

    dashboard_cells = [
        _dashboard_cell(
            dimension=dimension,
            dimension_key=dimension_key,
            observations=dashboard_groups[(dimension, dimension_key)],
            material_ids=dashboard_materials[(dimension, dimension_key)],
        )
        for dimension, dimension_key in sorted(dashboard_groups)
    ]
    property_gaps = [
        {
            key: value
            for key, value in cell.items()
            if key not in {"dimension", "dimension_key"}
        }
        | {"property_type": str(cell["dimension_key"]).casefold()}
        for cell in dashboard_cells
        if cell["dimension"] == "PROPERTY"
    ]
    evidence_class_gaps = [
        {
            key: value
            for key, value in cell.items()
            if key not in {"dimension", "dimension_key"}
        }
        | {"evidence_class": cell["dimension_key"]}
        for cell in dashboard_cells
        if cell["dimension"] == "EVIDENCE_CLASS"
    ]

    summary = scientific.get("summary")
    source_summary = dict(summary) if isinstance(summary, dict) else {}
    return {
        "schema_version": "b8-workspace-backfill-projection-v1",
        "authority_state": "PLANNING_ONLY_NON_PROMOTING",
        "input_hashes": {
            "inventory_sha256": _sha256_bytes(inventory_bytes),
            "scientific_inventory_sha256": scientific_sha256,
        },
        "scientific_inventory_summary": source_summary,
        "inventory_counts": {
            "raw_entries": len(raw_all),
            "raw_fragrance_entries": len(raw_fragrance),
            "unique_normalized": len(unique_all),
            "unique_fragrance": len(unique_fragrance),
            "duplicate_canonical_entries": len(raw_all) - len(unique_all),
            "owned_unique_fragrance": len(owned_records),
            "unavailable_unique_fragrance": len(unavailable_records),
            "matched_owned_materials": len(matched_owned),
            "unmatched_owned_materials": len(unmatched_owned),
            "matched_unavailable_materials": len(matched_unavailable),
        },
        "matched_owned_materials": [
            {
                "inventory_name": record.name,
                "scientific_subject_id": subjects[0],
            }
            for record, subjects in matched_owned
        ],
        "unmatched_owned_materials": sorted(
            (record.name for record in unmatched_owned),
            key=str.casefold,
        ),
        "unavailable_materials": sorted(
            (record.name for record in unavailable_records),
            key=str.casefold,
        ),
        "property_gaps": property_gaps,
        "evidence_class_gaps": evidence_class_gaps,
        "dashboard_cells": dashboard_cells,
        "legacy_promotion_count": 0,
        "limitations": [
            "B0 legacy and unreviewed values remain weak, unknown, or missing.",
            "Active formula, chemical family, and model sensitivity are unknown "
            "because these two frozen inputs cannot prove them.",
            "This projection cannot create B1-B7 authority or authorize release.",
        ],
    }


def _json_bytes(payload: Mapping[str, object]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Project current inventory against the frozen B0 scientific audit."
        )
    )
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument(
        "--scientific-inventory",
        type=Path,
        required=True,
    )
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    projection = build_workspace_backfill_projection(
        inventory_path=args.inventory,
        scientific_inventory_path=args.scientific_inventory,
    )
    payload = _json_bytes(projection)
    if args.output is None:
        print(payload.decode("utf-8"), end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
