"""Liking value used only to break ties between materials that fit a role equally.

Kenny's personal fit (``data/user/personal_liking.json``, written by the
backend) is used for a material once its evidence reaches ``MIN_EVIDENCE``;
otherwise the crowd guess from ``pleasantness_table``; otherwise 0 ("none").
A missing or unreadable personal file means no personal data, never an error.
This never uses OAV and never outweighs a difference in role fit.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.formulation_intelligence.pleasantness_table import _resolve, crowd_pleasantness
from engine.user_records import USER_RECORDS_DIR

PERSONAL_LIKING_PATH_ENV = "PERFUME_PERSONAL_LIKING_PATH"
PERSONAL_LIKING_NAME = "personal_liking.json"
PERSONAL_SCHEMA = "personal_liking_v1"
MIN_EVIDENCE = 0.5
METHOD = "ROUNDED_FIT_6DP_THEN_LIKING_V1"


@dataclass(frozen=True, slots=True)
class Liking:
    value: float
    source: str  # "personal" | "crowd" | "none"

    def as_dict(self) -> dict[str, Any]:
        return {"value": round(self.value, 4), "source": self.source}


def personal_liking_path() -> Path:
    override = os.environ.get(PERSONAL_LIKING_PATH_ENV)
    return Path(override) if override else USER_RECORDS_DIR / PERSONAL_LIKING_NAME


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _parse_personal(data: bytes) -> tuple[dict[str, float], int] | None:
    """Personal values with enough evidence, by casefold name; None if no usable file."""
    try:
        payload = json.loads(data.decode("utf-8"))
    except ValueError:
        return None
    if not isinstance(payload, dict) or payload.get("schema") != PERSONAL_SCHEMA:
        return None
    materials = payload.get("materials")
    if not isinstance(materials, dict):
        return None
    values: dict[str, float] = {}
    for name, entry in materials.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            continue
        personal, evidence = _finite(entry.get("personal")), _finite(entry.get("evidence"))
        if personal is None or evidence is None or evidence < MIN_EVIDENCE:
            continue
        value = max(-1.0, min(1.0, personal))
        values.setdefault(name.casefold(), value)
        resolved = _resolve(name)
        if resolved is not None:
            values.setdefault(resolved.casefold(), value)
    ratings = _finite(payload.get("ratings_used"))
    return values, int(ratings) if ratings is not None and ratings >= 0 else 0


class LikingLookup:
    """One solve's liking values, cached by identity name."""

    def __init__(self, personal_path: Path | None = None) -> None:
        try:
            data: bytes | None = (personal_path or personal_liking_path()).read_bytes()
        except OSError:
            data = None
        # Hash the exact bytes parsed, so a receipt names the file it used.
        self.personal_file_sha256 = hashlib.sha256(data).hexdigest() if data is not None else None
        loaded = _parse_personal(data) if data is not None else None
        self.personal_file = loaded is not None
        self._personal, self.personal_ratings_used = loaded if loaded is not None else ({}, 0)
        self._cache: dict[str, Liking] = {}

    def __call__(self, identity_name: str) -> Liking:
        cached = self._cache.get(identity_name)
        if cached is None:
            cached = self._cache[identity_name] = self._lookup(identity_name)
        return cached

    def _lookup(self, identity_name: str) -> Liking:
        personal = self._personal.get(identity_name.casefold())
        if personal is None:
            resolved = _resolve(identity_name)
            if resolved is not None:
                personal = self._personal.get(resolved.casefold())
        if personal is not None:
            return Liking(personal, "personal")
        crowd = crowd_pleasantness(identity_name)
        if crowd is not None:
            return Liking(max(-1.0, min(1.0, float(crowd.value))), "crowd")
        return Liking(0.0, "none")

    def receipt(self) -> dict[str, Any]:
        return {
            "method": METHOD,
            "weight": None,
            "personal_file": self.personal_file,
            "personal_file_sha256": self.personal_file_sha256,
            "personal_ratings_used": self.personal_ratings_used,
        }


__all__ = ["Liking", "LikingLookup", "METHOD", "MIN_EVIDENCE", "personal_liking_path"]
