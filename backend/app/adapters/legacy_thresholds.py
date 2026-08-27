"""Deterministic B3 quarantine adapter for legacy ODT dictionaries."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

from engine.calibration.hashing import stable_json_hash

from app.services.lab_thresholds import LegacyThresholdInput


def _status(
    material_key: str,
    odt_data: Mapping[str, Mapping[str, Any]],
    odt_verification: Mapping[str, Mapping[str, Any]],
) -> tuple[str, dict[str, Any]]:
    verification = dict(odt_verification.get(material_key, {}))
    fallback = dict(odt_data.get(material_key, {}))
    raw = verification.get("vfy", fallback.get("vfy"))
    status = str(raw).strip().upper() if raw is not None else "UNKNOWN"
    if not status:
        status = "UNKNOWN"
    payload = {
        "verification": verification,
        "legacy_entry_sources": fallback.get("sources", []),
        "legacy_entry_note": fallback.get("note"),
    }
    return status, payload


def legacy_threshold_inputs(
    *,
    odt_data: Mapping[str, Mapping[str, Any]],
    odt_verification: Mapping[str, Mapping[str, Any]],
    id_prefix: str,
) -> tuple[LegacyThresholdInput, ...]:
    """Return quarantine commands without importing or promoting any record."""

    prefix = str(id_prefix).strip()
    if not prefix:
        raise ValueError("id_prefix must not be blank")
    commands: list[LegacyThresholdInput] = []
    conventions = (
        ("odt_air", "AIR", "ppb"),
        ("odt_eth", "ETHANOL_SOLUTION", "ppm"),
    )
    for material_key in sorted(odt_data):
        entry = odt_data[material_key]
        status, payload = _status(
            material_key,
            odt_data,
            odt_verification,
        )
        for field, medium, unit in conventions:
            raw_value = entry.get(field)
            if raw_value is None:
                continue
            value = float(raw_value)
            if not isfinite(value) or value <= 0:
                continue
            identity = stable_json_hash(
                {
                    "schema": "legacy-threshold-adapter-v1",
                    "material_key": material_key,
                    "medium": medium,
                    "numeric_value": value,
                    "unit": unit,
                    "verification_status": status,
                    "source_payload": payload,
                }
            )
            command_id = f"{prefix[:18]}-{identity[:16]}"
            commands.append(
                LegacyThresholdInput(
                    record_id=command_id,
                    schema_version="lab-legacy-threshold-v1",
                    material_key=material_key,
                    medium=medium,
                    numeric_value=value,
                    original_unit=unit,
                    verification_status=status,
                    source_payload=payload,
                )
            )
    return tuple(commands)


__all__ = ["legacy_threshold_inputs"]
