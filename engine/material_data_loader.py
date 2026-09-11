"""Load material data extracted from Python modules into ``data/engine_data/``.

The engine historically embedded large literal datasets inside
``engine/odor_thresholds.py`` and ``engine/ingredient_intelligence.py``. Those
literals now live in JSON files under ``data/engine_data/`` and are loaded here,
keeping the public module-level objects (``ODT_DATA``, ``_PROFILES``, ...)
identical. Runtime mutations that those modules applied after the literal are
left in the modules, so behaviour is unchanged.
"""
from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "engine_data"


@lru_cache(maxsize=None)
def _load_file(module: str) -> dict[str, Any]:
    path = engine_data_path(module)
    return json.loads(path.read_text(encoding="utf-8"))


def engine_data_path(module: str) -> Path:
    return _DATA_DIR / f"{module}.json"


def load_engine_data(module: str, key: str) -> Any:
    """Return a fresh copy of a dataset extracted from ``module``.

    A deep copy is returned so callers (which apply runtime mutations on top of
    the literal, e.g. ``ODT_DATA.setdefault(...)``) cannot corrupt the cached
    source loaded from disk.
    """
    return copy.deepcopy(_load_file(module)[key])


__all__ = ["load_engine_data", "engine_data_path"]
