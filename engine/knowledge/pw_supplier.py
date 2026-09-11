"""Merge PerfumersWorld supplier fields into material records.

Supplier intake (``tools/pw_enrich.py`` → ``data/knowledge_graph/pw_material_data_merged.json``)
provides, per material: ``relative_impact`` (Dowthwaite, Linalool = 100),
``odour_life_hrs`` (smelling strip), ``pw_class`` (ABC class), CAS, and doc
provenance. These are ``SUPPLIER_TECHNICAL`` evidence class.

This module keeps the merge import-safe so both the generator
(``_generate_material_properties.py``) and ``scripts/merge_pw_supplier_data.py``
produce identical records.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from engine.name_utils import normalize_name

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PW_PATH = _REPO_ROOT / "data" / "knowledge_graph" / "pw_material_data_merged.json"

# record fields written into material_properties.json entries
PW_FIELD_NAMES: tuple[str, ...] = (
    "pw_relative_impact",
    "pw_odour_life_hrs",
    "pw_class",
    "pw_cas",
    "pw_evidence_class",
    "pw_sku",
)


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=2)
def load_pw_supplier_fields(path: str | None = None) -> dict[str, dict[str, Any]]:
    """Return ``{normalized_name: pw fields}`` from the merged PW intake."""
    target = Path(path) if path else _PW_PATH
    if not target.exists():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    records = payload.get("materials", payload if isinstance(payload, list) else [])
    out: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            continue
        name = str(record.get("inventory_name") or record.get("pw_name") or "").strip()
        if not name:
            continue
        fields = record.get("fields") or {}
        data = {
            "pw_relative_impact": _to_float(fields.get("relative_impact")),
            "pw_odour_life_hrs": _to_float(fields.get("odour_life_hrs")),
            "pw_class": fields.get("notes_pyramid_raw"),
            "pw_cas": fields.get("cas"),
            "pw_evidence_class": str(record.get("evidence_class") or "SUPPLIER_TECHNICAL"),
            "pw_sku": record.get("sku"),
        }
        for key in {name.lower(), normalize_name(name)}:
            out.setdefault(key, data)
    return out


def pw_fields_for(name: str, table: Mapping[str, dict[str, Any]] | None = None) -> dict[str, Any] | None:
    data = table if table is not None else load_pw_supplier_fields()
    key = str(name or "").strip().lower()
    found = data.get(key) or data.get(normalize_name(name))
    if found is not None:
        return found
    for suffix in (" 100%", " 50%", " 30%", " 20%", " 10%", " 5%", " 1%"):
        if key.endswith(suffix):
            trimmed = key[: -len(suffix)].strip()
            found = data.get(trimmed) or data.get(normalize_name(trimmed))
            if found is not None:
                return found
    return None


def merge_pw_supplier_fields(
    entries: list[dict[str, Any]], *, table: Mapping[str, dict[str, Any]] | None = None
) -> dict[str, int]:
    """Attach PW supplier fields to each entry in place; return coverage stats."""
    pw = table if table is not None else load_pw_supplier_fields()
    matched = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        fields = pw_fields_for(str(entry.get("name") or ""), pw)
        if fields is None:
            alt = str(entry.get("alt_name") or "")
            if alt:
                fields = pw_fields_for(alt, pw)
        if fields is None:
            continue
        for key in PW_FIELD_NAMES:
            if fields.get(key) is not None:
                entry[key] = fields[key]
        matched += 1
    return {"entries": len(entries), "matched": matched, "pw_records": len(pw)}
