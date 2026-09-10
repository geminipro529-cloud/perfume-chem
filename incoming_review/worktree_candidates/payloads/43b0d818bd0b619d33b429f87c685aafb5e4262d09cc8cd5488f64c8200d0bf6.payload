#!/usr/bin/env python3
"""Deterministic helpers for DNA-preserving perfume chassis.

The script validates:
- target totals;
- core + parent module row-wise recombination;
- socket totals;
- protected-anchor floors;
- and alternative module totals.

It does not predict sensory similarity.
"""
from __future__ import annotations
import csv
import json
import hashlib
from pathlib import Path
from typing import Iterable

def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def f(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in ("", None) else 0.0

def canonical_hash(rows: Iterable[dict], fields: list[str]) -> str:
    payload = [{field: row.get(field) for field in fields} for row in rows]
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

def validate_partition(path: str | Path, target_total: float, core_total: float, socket_total: float) -> dict:
    rows = read_csv(path)
    errors: list[str] = []
    target = sum(f(r, "raw_uL") for r in rows)
    core = sum(f(r, "core_raw_uL") for r in rows)
    module = sum(f(r, "module_raw_uL") for r in rows)
    if abs(target-target_total) > 1e-6:
        errors.append(f"target total {target} != {target_total}")
    if abs(core-core_total) > 1e-6:
        errors.append(f"core total {core} != {core_total}")
    if abs(module-socket_total) > 1e-6:
        errors.append(f"module total {module} != {socket_total}")
    for r in rows:
        if abs(f(r,"core_raw_uL")+f(r,"module_raw_uL")-f(r,"raw_uL")) > 1e-6:
            errors.append(f"row mismatch: {r.get('ingredient')}")
    return {"path":str(path),"target":target,"core":core,"module":module,"errors":errors}

def validate_module(path: str | Path, expected_total: float) -> dict:
    rows=read_csv(path)
    total=sum(f(r,"raw_uL") for r in rows)
    errors=[] if abs(total-expected_total)<=1e-6 else [f"module total {total} != {expected_total}"]
    return {"path":str(path),"total":total,"errors":errors}

def validate_anchor_floors(partition_path: str | Path, envelope_path: str | Path) -> list[str]:
    rows={r["ingredient"]:r for r in read_csv(partition_path)}
    env=json.loads(Path(envelope_path).read_text(encoding="utf-8"))
    errors=[]
    for material,floor in env.get("protected_anchor_floors_in_core_uL",{}).items():
        if material not in rows:
            errors.append(f"missing anchor row: {material}")
            continue
        actual=f(rows[material],"core_raw_uL")
        if actual+1e-9 < float(floor):
            errors.append(f"anchor {material}: {actual} < {floor}")
    return errors
