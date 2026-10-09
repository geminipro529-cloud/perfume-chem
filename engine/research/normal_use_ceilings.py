"""Per-material normal-use dose ceilings for the inventory composer.

A ceiling is the most active material, as a percentage of the fragrance
concentrate, that the composer may allocate to one free row.  It is a
bench-design bound, not a safety, IFRA or release limit.  Ceilings match on
exact identity wording only (the composer's identity probe), as whole-word
phrases; when several phrases match, the longest one wins so that, for
example, "dihydro beta ionone" never inherits "beta ionone"'s ceiling.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "normal_use_ceilings_v1"
BASIS = "active material as % of the fragrance concentrate"
NORMAL_USE_CEILINGS_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "formulation_knowledge"
    / "normal_use_ceilings_v1.json"
)


class NormalUseCeilingsError(RuntimeError):
    """The ceilings data file is malformed.

    Deliberately not a ValueError: the composer turns ValueError from dose
    allocation into a dose-infeasibility hold, and a corrupt data file must not
    be reported as an infeasible formula.
    """


@dataclass(frozen=True, slots=True)
class NormalUseCeiling:
    material: str
    phrases: tuple[str, ...]
    max_active_pct_of_concentrate: int | float
    max_active_fraction: Decimal
    excludes: tuple[str, ...] = ()


def _phrase_key(value: str) -> str:
    # composition_planner._key normalization, which builds the probe, plus a
    # letter/digit split so "C12", "C-12" and "C 12" are the same words.
    key = re.sub(r"[^a-z0-9]+", " ", re.sub(r"\s+", " ", value.strip()).casefold())
    key = re.sub(r"(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])", " ", key)
    return re.sub(r" +", " ", key).strip()


def _fail(message: str) -> NormalUseCeilingsError:
    return NormalUseCeilingsError(f"normal-use ceilings: {message}")


def _parse_entry(index: int, entry: object) -> NormalUseCeiling:
    where = f"materials[{index}]"
    if not isinstance(entry, dict):
        raise _fail(f"{where} must be an object")
    material = entry.get("material")
    if not isinstance(material, str) or not material.strip():
        raise _fail(f"{where}.material must be non-empty text")
    match = entry.get("match")
    if not isinstance(match, list) or not match:
        raise _fail(f"{where}.match must be a non-empty list of identity phrases")
    phrases: list[str] = []
    for phrase in match:
        key = _phrase_key(phrase) if isinstance(phrase, str) else ""
        if not key:
            raise _fail(f"{where}.match entries must be non-empty identity phrases")
        phrases.append(key)
    exclude = entry.get("exclude", [])
    if not isinstance(exclude, list):
        raise _fail(f"{where}.exclude must be a list of identity phrases")
    excludes: list[str] = []
    for phrase in exclude:
        key = _phrase_key(phrase) if isinstance(phrase, str) else ""
        if not key:
            raise _fail(f"{where}.exclude entries must be non-empty identity phrases")
        excludes.append(key)
    value = entry.get("max_active_pct_of_concentrate")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise _fail(f"{where}.max_active_pct_of_concentrate must be a number")
    if not 0 < value <= 100:
        raise _fail(f"{where}.max_active_pct_of_concentrate must be > 0 and <= 100")
    sources = entry.get("sources")
    if not isinstance(sources, list) or not sources or not all(isinstance(s, dict) for s in sources):
        raise _fail(f"{where}.sources must be a non-empty list of objects")
    if not isinstance(entry.get("note"), str):
        raise _fail(f"{where}.note must be text")
    return NormalUseCeiling(
        material=material.strip(),
        phrases=tuple(dict.fromkeys(phrases)),
        max_active_pct_of_concentrate=value,
        max_active_fraction=Decimal(str(value)) / Decimal(100),
        excludes=tuple(dict.fromkeys(excludes)),
    )


def parse_normal_use_ceilings(payload: Any) -> tuple[NormalUseCeiling, ...]:
    if not isinstance(payload, dict):
        raise _fail("top level must be an object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise _fail(f"schema_version must be {SCHEMA_VERSION!r}")
    status = payload.get("status")
    if not isinstance(status, str) or not status.strip():
        raise _fail("status must be non-empty text")
    if payload.get("basis") != BASIS:
        raise _fail(f"basis must be {BASIS!r}")
    materials = payload.get("materials")
    if not isinstance(materials, list):
        raise _fail("materials must be a list")
    ceilings = tuple(_parse_entry(index, entry) for index, entry in enumerate(materials))
    owners: dict[str, str] = {}
    for ceiling in ceilings:
        for phrase in ceiling.phrases:
            if phrase in owners:
                raise _fail(
                    f"identity phrase {phrase!r} is claimed by both {owners[phrase]!r} and {ceiling.material!r}"
                )
            owners[phrase] = ceiling.material
    return ceilings


def load_normal_use_ceilings(path: Path) -> tuple[NormalUseCeiling, ...]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _fail(f"cannot read {path}: {exc}") from exc
    return parse_normal_use_ceilings(payload)


@lru_cache(maxsize=8)
def _load_cached(path_text: str) -> tuple[NormalUseCeiling, ...]:
    return load_normal_use_ceilings(Path(path_text))


def active_normal_use_ceilings() -> tuple[NormalUseCeiling, ...]:
    return _load_cached(str(NORMAL_USE_CEILINGS_PATH))


def match_normal_use_ceiling(
    identity_probe: str,
    ceilings: tuple[NormalUseCeiling, ...] | None = None,
) -> NormalUseCeiling | None:
    """Return the ceiling whose longest whole-word phrase occurs in the probe.

    An entry is skipped when one of its ``exclude`` phrases occurs.

    Ties between different materials resolve to the lower ceiling.
    """

    padded = f" {_phrase_key(identity_probe)} "
    best: tuple[int, Decimal, str] | None = None
    winner: NormalUseCeiling | None = None
    for ceiling in active_normal_use_ceilings() if ceilings is None else ceilings:
        # A different material whose name contains this one ("methyl eugenol",
        # "hexyl cinnamaldehyde") is excluded rather than given its ceiling.
        if any(f" {phrase} " in padded for phrase in ceiling.excludes):
            continue
        for phrase in ceiling.phrases:
            if f" {phrase} " not in padded:
                continue
            rank = (-len(phrase), ceiling.max_active_fraction, ceiling.material)
            if best is None or rank < best:
                best, winner = rank, ceiling
    return winner


__all__ = [
    "BASIS",
    "NORMAL_USE_CEILINGS_PATH",
    "NormalUseCeiling",
    "NormalUseCeilingsError",
    "SCHEMA_VERSION",
    "active_normal_use_ceilings",
    "load_normal_use_ceilings",
    "match_normal_use_ceiling",
    "parse_normal_use_ceilings",
]
