"""Loader: read A-Z YAML files into an in-memory MaterialRegistry.

Used at runtime by every science module. The migrate.py script writes
the YAML files; this module reads them back. Round-trip safe.
"""

from __future__ import annotations

import string
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import yaml

from .material import Material, MaterialRegistry

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "materials"
_LETTERS = tuple(string.ascii_uppercase) + ("_",)
_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def _letter_for(name: str) -> str:
    """Bucket a name to its A-Z file. Non-alpha leading chars map to '_'."""
    for ch in name:
        if ch.isalpha():
            return ch.upper()
    return "_"


def _resolved_data_dir(data_dir: str | Path | None) -> Path:
    base = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    return base.expanduser().resolve()


def _data_fingerprint(base: Path) -> tuple[tuple[str, int, int], ...]:
    """Return the cheap file identity used to invalidate parsed YAML data."""
    fingerprint: list[tuple[str, int, int]] = []
    for letter in _LETTERS:
        path = base / f"{letter}.yaml"
        if path.exists():
            stat = path.stat()
            fingerprint.append((path.name, stat.st_mtime_ns, stat.st_size))
    return tuple(fingerprint)


@lru_cache(maxsize=8)
def _load_materials_cached(
    base_path: str, _fingerprint: tuple[tuple[str, int, int], ...]
) -> tuple[Material, ...]:
    base = Path(base_path)
    materials: list[Material] = []
    for letter in _LETTERS:
        p = base / f"{letter}.yaml"
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8") as fh:
            # CSafeLoader and SafeLoader implement the same restricted YAML
            # contract; the C implementation is substantially faster on the
            # A-Z material spine while retaining safe object construction.
            payload = yaml.load(fh, Loader=_YAML_LOADER) or []
        for entry in payload:
            try:
                materials.append(Material.from_dict(entry))
            except Exception as exc:  # noqa: BLE001
                label = None
                if isinstance(entry, dict):
                    label = entry.get("canonical_name") or entry.get("name")
                print(f"[data_spine] skip {p.name}:{label!r} -> {exc}")
    return tuple(materials)


def load_materials(data_dir: str | Path | None = None) -> list[Material]:
    """Read every <LETTER>.yaml file, reusing unchanged parsed records."""
    base = _resolved_data_dir(data_dir)
    return list(_load_materials_cached(str(base), _data_fingerprint(base)))


@lru_cache(maxsize=8)
def _load_registry_cached(
    base_path: str, fingerprint: tuple[tuple[str, int, int], ...]
) -> MaterialRegistry:
    return MaterialRegistry(list(_load_materials_cached(base_path, fingerprint)))


def load_registry(data_dir: str | Path | None = None) -> MaterialRegistry:
    base = _resolved_data_dir(data_dir)
    return _load_registry_cached(str(base), _data_fingerprint(base))


def clear_data_spine_cache() -> None:
    """Clear parsed material and registry caches after an in-process write."""
    _load_registry_cached.cache_clear()
    _load_materials_cached.cache_clear()
    # material_resolver owns a second registry/result cache.  Import locally
    # to avoid a loader -> resolver -> loader import cycle during startup.
    try:
        from engine.material_resolver import clear_material_resolver_cache

        clear_material_resolver_cache()
    except ImportError:
        pass


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
    clear_data_spine_cache()
    return counts
