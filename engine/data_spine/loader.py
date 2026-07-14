"""Loader: read A-Z YAML files into an in-memory MaterialRegistry.

Used at runtime by every science module. The migrate.py script writes
the YAML files; this module reads them back. Round-trip safe.
"""

from __future__ import annotations

import string
from pathlib import Path
from typing import Iterable

import yaml

from .material import Material, MaterialRegistry


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "materials"


def _letter_for(name: str) -> str:
    """Bucket a name to its A-Z file. Non-alpha leading chars map to '_'."""
    for ch in name:
        if ch.isalpha():
            return ch.upper()
    return "_"


def load_materials(data_dir: str | Path | None = None) -> list[Material]:
    """Read every <LETTER>.yaml file under data_dir into Material list."""
    base = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    materials: list[Material] = []
    for letter in list(string.ascii_uppercase) + ["_"]:
        p = base / f"{letter}.yaml"
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8") as fh:
            payload = yaml.safe_load(fh) or []
        for entry in payload:
            try:
                materials.append(Material.from_dict(entry))
            except Exception as exc:  # noqa: BLE001
                label = None
                if isinstance(entry, dict):
                    label = entry.get("canonical_name") or entry.get("name")
                print(f"[data_spine] skip {p.name}:{label!r} -> {exc}")
    return materials


def load_registry(data_dir: str | Path | None = None) -> MaterialRegistry:
    return MaterialRegistry(load_materials(data_dir))


def write_materials(
    materials: Iterable[Material],
    data_dir: str | Path | None = None,
) -> dict[str, int]:
    """Write a Material iterable into A-Z YAML buckets.

    Returns ``{letter: count}`` for reporting.
    """
    base = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    base.mkdir(parents=True, exist_ok=True)
    buckets: dict[str, list[Material]] = {}
    for m in materials:
        buckets.setdefault(_letter_for(m.canonical_name), []).append(m)
    counts: dict[str, int] = {}
    for letter, items in buckets.items():
        items.sort(key=lambda x: x.canonical_name.casefold())
        out = base / f"{letter}.yaml"
        payload = [m.to_dict() for m in items]
        with out.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(
                payload,
                fh,
                sort_keys=False,
                allow_unicode=True,
                width=100,
            )
        counts[letter] = len(items)
    return counts
