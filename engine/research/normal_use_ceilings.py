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
from dataclasses import dataclass, replace
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "normal_use_ceilings_v1"
BASIS = "active material as % of the fragrance concentrate"
DEFAULT_KIND = "normal_use_ceiling"
SCREENING_DEFAULT_KIND = "project_screening_default"
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
    kind: str = DEFAULT_KIND
    label: str = ""


@dataclass(frozen=True, slots=True)
class ScreeningDefault:
    """The project screening default for a material with no ceiling row.

    A conservative bench-design screen, not a safety or IFRA limit and not a
    use-level finding.  ``floors`` only raise the class default.
    """

    kind: str
    label: str
    aroma_chemical_fraction: Decimal
    natural_fraction: Decimal
    aroma_chemical_pct: int | float
    natural_pct: int | float
    natural_words: tuple[str, ...]
    floors: tuple[NormalUseCeiling, ...]


def _phrase_key(value: str) -> str:
    # composition_planner._key normalization, which builds the probe, plus a
    # letter/digit split so "C12", "C-12" and "C 12" are the same words.
    key = re.sub(r"[^a-z0-9]+", " ", re.sub(r"\s+", " ", value.strip()).casefold())
    key = re.sub(r"(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])", " ", key)
    return re.sub(r" +", " ", key).strip()


def _fail(message: str) -> NormalUseCeilingsError:
    return NormalUseCeilingsError(f"normal-use ceilings: {message}")


def _pct(value: object, where: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise _fail(f"{where} must be a number")
    if not 0 < value <= 100:
        raise _fail(f"{where} must be > 0 and <= 100")
    return value


def _parse_entry(index: int, entry: object, where: str | None = None) -> NormalUseCeiling:
    where = where or f"materials[{index}]"
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
    value = _pct(entry.get("max_active_pct_of_concentrate"), f"{where}.max_active_pct_of_concentrate")
    sources = entry.get("sources")
    if not isinstance(sources, list) or not sources or not all(isinstance(s, dict) for s in sources):
        raise _fail(f"{where}.sources must be a non-empty list of objects")
    if not isinstance(entry.get("note"), str):
        raise _fail(f"{where}.note must be text")
    kind = entry.get("kind", DEFAULT_KIND)
    if not isinstance(kind, str) or not kind.strip():
        raise _fail(f"{where}.kind must be non-empty text")
    return NormalUseCeiling(
        material=material.strip(),
        phrases=tuple(dict.fromkeys(phrases)),
        max_active_pct_of_concentrate=value,
        max_active_fraction=Decimal(str(value)) / Decimal(100),
        excludes=tuple(dict.fromkeys(excludes)),
        kind=kind.strip(),
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


def parse_screening_default(payload: Any) -> ScreeningDefault | None:
    """Parse the optional ``screening_default`` block; None when it is absent."""

    if not isinstance(payload, dict):
        raise _fail("top level must be an object")
    block = payload.get("screening_default")
    if block is None:
        return None
    where = "screening_default"
    if not isinstance(block, dict):
        raise _fail(f"{where} must be an object")
    if block.get("kind") != SCREENING_DEFAULT_KIND:
        raise _fail(f"{where}.kind must be {SCREENING_DEFAULT_KIND!r}")
    label = block.get("label")
    if not isinstance(label, str) or not label.strip():
        raise _fail(f"{where}.label must be non-empty text")
    aroma = _pct(
        block.get("aroma_chemical_max_active_pct_of_concentrate"),
        f"{where}.aroma_chemical_max_active_pct_of_concentrate",
    )
    natural = _pct(
        block.get("natural_max_active_pct_of_concentrate"),
        f"{where}.natural_max_active_pct_of_concentrate",
    )
    words = block.get("natural_identity_words")
    if not isinstance(words, list) or not words:
        raise _fail(f"{where}.natural_identity_words must be a non-empty list")
    natural_words: list[str] = []
    for word in words:
        key = _phrase_key(word) if isinstance(word, str) else ""
        if not key:
            raise _fail(f"{where}.natural_identity_words entries must be non-empty words")
        natural_words.append(key)
    raw_floors = block.get("typical_use_floors", [])
    if not isinstance(raw_floors, list):
        raise _fail(f"{where}.typical_use_floors must be a list")
    floors = tuple(
        replace(
            _parse_entry(index, entry, f"{where}.typical_use_floors[{index}]"),
            kind=SCREENING_DEFAULT_KIND,
            label=label.strip(),
        )
        for index, entry in enumerate(raw_floors)
    )
    return ScreeningDefault(
        kind=SCREENING_DEFAULT_KIND,
        label=label.strip(),
        aroma_chemical_fraction=Decimal(str(aroma)) / Decimal(100),
        natural_fraction=Decimal(str(natural)) / Decimal(100),
        aroma_chemical_pct=aroma,
        natural_pct=natural,
        natural_words=tuple(dict.fromkeys(natural_words)),
        floors=floors,
    )


def _read(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _fail(f"cannot read {path}: {exc}") from exc


def load_normal_use_ceilings(path: Path) -> tuple[NormalUseCeiling, ...]:
    return parse_normal_use_ceilings(_read(path))


def load_screening_default(path: Path) -> ScreeningDefault | None:
    return parse_screening_default(_read(path))


@lru_cache(maxsize=8)
def _load_cached(path_text: str) -> tuple[NormalUseCeiling, ...]:
    return load_normal_use_ceilings(Path(path_text))


@lru_cache(maxsize=8)
def _load_default_cached(path_text: str) -> ScreeningDefault | None:
    return load_screening_default(Path(path_text))


def active_normal_use_ceilings() -> tuple[NormalUseCeiling, ...]:
    return _load_cached(str(NORMAL_USE_CEILINGS_PATH))


def active_screening_default() -> ScreeningDefault | None:
    return _load_default_cached(str(NORMAL_USE_CEILINGS_PATH))


def match_screening_default(
    identity_probe: str,
    screening_default: ScreeningDefault | None = None,
) -> NormalUseCeiling | None:
    """Return the screening default for a material that has no ceiling row.

    Callers apply it only when no ceiling row and no identity hard cap
    matched.  Naturals (an identity word such as "EO" or "absolute") get the
    natural class default, everything else the aroma-chemical one; a matching
    typical-use floor can only raise it.  None when the file has no block.
    """

    default = active_screening_default() if screening_default is None else screening_default
    if default is None:
        return None
    padded = f" {_phrase_key(identity_probe)} "
    natural = any(f" {word} " in padded for word in default.natural_words)
    pct = default.natural_pct if natural else default.aroma_chemical_pct
    fraction = default.natural_fraction if natural else default.aroma_chemical_fraction
    floor = match_normal_use_ceiling(identity_probe, default.floors)
    if floor is not None and floor.max_active_fraction > fraction:
        return floor
    return NormalUseCeiling(
        material="natural" if natural else "aroma chemical",
        phrases=(),
        max_active_pct_of_concentrate=pct,
        max_active_fraction=fraction,
        kind=default.kind,
        label=default.label,
    )


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
    "SCREENING_DEFAULT_KIND",
    "ScreeningDefault",
    "active_normal_use_ceilings",
    "active_screening_default",
    "load_normal_use_ceilings",
    "load_screening_default",
    "match_normal_use_ceiling",
    "match_screening_default",
    "parse_normal_use_ceilings",
    "parse_screening_default",
]
