"""Fit Kenny's personal liking per material and per odour family.

The fit spreads each rating, and each two-bottle pick, over the materials in the
bottle by their share.  It reads the optional crowd pleasantness table from the
repository; the ratings never leave this machine.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PROJECT_ROOT
from app.core.logging import get_logger
from app.models.liking import LikingPick, LikingRating

logger = get_logger(__name__)

# The same folder as the engine's personal stock records (engine/user_records.py).
USER_RECORDS_DIR = PROJECT_ROOT / "data" / "user"
PERSONAL_LIKING_NAME = "personal_liking.json"
PERSONAL_LIKING_PATH_ENV = "PERFUME_PERSONAL_LIKING_PATH"
CROWD_TABLE_PATH_ENV = "PERFUME_PLEASANTNESS_CROWD_PATH"
DEFAULT_CROWD_TABLE_PATH = (
    PROJECT_ROOT / "data" / "formulation_knowledge" / "pleasantness_crowd_v1.json"
)

SCHEMA = "personal_liking_v1"
PICK_STEP = 0.25
PICK_WEIGHT = 0.5
PRIOR_WEIGHT = 1.0
LISTED_EVIDENCE = 0.5
LISTED_COUNT = 5
METHOD = (
    "Each rating's distance from the crowd guess, after removing your own average offset "
    "from the crowd scale (or, with no crowd guess, its distance from your average rating), "
    "and each two-bottle pick as a quarter-point nudge, is spread over the bottle's "
    "materials by share and shrunk by one rating's worth of evidence; the result is added "
    "to the material's crowd value, or to the typical crowd value when it has none."
)


def personal_liking_path() -> Path:
    override = os.environ.get(PERSONAL_LIKING_PATH_ENV)
    if override:
        return Path(override).resolve()
    return (USER_RECORDS_DIR / PERSONAL_LIKING_NAME).resolve()


def crowd_table_path() -> Path:
    override = os.environ.get(CROWD_TABLE_PATH_ENV)
    return Path(override).resolve() if override else DEFAULT_CROWD_TABLE_PATH


_QUALIFIER = re.compile(r"\s*\(?\s*\d+(?:\.\d+)?\s*%[^()]*\)?\s*$")


def _fold(name: str) -> str:
    """Case-fold, treat hyphens and spaces alike, drop a trailing strength/solvent qualifier."""

    stripped = _QUALIFIER.sub("", name)
    return " ".join(stripped.casefold().replace("-", " ").split())


class CrowdTable:
    """Crowd pleasantness looked up by exact name, then folded name, then alias."""

    def __init__(self, materials: Mapping[str, Mapping[str, Any]] | None = None) -> None:
        self._entries: dict[str, Mapping[str, Any]] = dict(materials or {})
        self._casefold: dict[str, str] = {}
        self._aliases: dict[str, str] = {}
        for name, entry in self._entries.items():
            self._casefold.setdefault(_fold(name), name)
            for alias in entry.get("aliases") or ():
                if isinstance(alias, str):
                    self._aliases.setdefault(_fold(alias), name)

    @classmethod
    def load(cls, path: Path | None = None) -> CrowdTable:
        source = path or crowd_table_path()
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return cls()
        materials = payload.get("materials") if isinstance(payload, dict) else None
        return cls(materials if isinstance(materials, dict) else None)

    def entry(self, material: str) -> Mapping[str, Any] | None:
        if material in self._entries:
            return self._entries[material]
        key = _fold(material)
        name = self._casefold.get(key) or self._aliases.get(key)
        return self._entries[name] if name is not None else None

    def value(self, material: str) -> float | None:
        entry = self.entry(material)
        value = entry.get("value") if entry else None
        return float(value) if isinstance(value, int | float) else None

    def typical_value(self) -> float:
        """Median of every known crowd value (0 when the table has none)."""

        values = [
            float(entry["value"])
            for entry in self._entries.values()
            if isinstance(entry.get("value"), int | float)
        ]
        return float(median(values)) if values else 0.0

    def family(self, material: str) -> str | None:
        entry = self.entry(material)
        family = entry.get("family") if entry else None
        return family if isinstance(family, str) and family else None


def _observations(
    ratings: list[LikingRating], picks: Iterable[LikingPick]
) -> tuple[list[tuple[Mapping[str, float], float, float]], float]:
    """((shares, residual, weight) for every rating and non-tied pick side, offset b).

    y = (liking - 5.5) / 4.5.  b is the mean of (y - crowd guess) over the ratings that
    have a crowd guess (Kenny's own offset from the crowd scale; 0 if none).  A rated
    bottle with a crowd guess has residual y - guess - b; one without has y - mean(y).
    """

    ys = [(rating.liking - 5.5) / 4.5 for rating in ratings]
    ybar = sum(ys) / len(ys) if ys else 0.0
    gaps = [y - r.crowd_guess for y, r in zip(ys, ratings) if r.crowd_guess is not None]
    offset = sum(gaps) / len(gaps) if gaps else 0.0

    rows: list[tuple[Mapping[str, float], float, float]] = []
    for rating, y in zip(ratings, ys):
        if rating.crowd_guess is not None:
            residual = y - rating.crowd_guess - offset
        else:
            residual = y - ybar
        rows.append((rating.material_shares, residual, 1.0))
    for pick in picks:
        if pick.preferred == "same":
            continue
        sign = 1.0 if pick.preferred == "a" else -1.0
        rows.append((pick.shares_a, sign * PICK_STEP, PICK_WEIGHT))
        rows.append((pick.shares_b, -sign * PICK_STEP, PICK_WEIGHT))
    return rows, offset


def _shrunk(observations: Iterable[tuple[Mapping[str, float], float, float]]) -> dict[str, dict]:
    sums: dict[str, list[float]] = {}
    for shares, error, weight in observations:
        for name, share in shares.items():
            if share > 0:
                total = sums.setdefault(name, [0.0, 0.0, 0])
                total[0] += weight * share * error
                total[1] += weight * share
                total[2] += 1
    return {
        name: {
            "deviation": weighted / (evidence + PRIOR_WEIGHT),
            "evidence": evidence,
            "n": int(count),
        }
        for name, (weighted, evidence, count) in sums.items()
    }


def fit_personal_liking(
    ratings: Iterable[LikingRating],
    picks: Iterable[LikingPick],
    crowd: CrowdTable,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    ratings = list(ratings)
    picks = list(picks)
    observations, offset = _observations(ratings, picks)
    typical = crowd.typical_value()

    materials: dict[str, dict[str, Any]] = {}
    for name, fit in sorted(_shrunk(observations).items()):
        crowd_value = crowd.value(name)
        prior = crowd_value if crowd_value is not None else typical
        personal = max(-1.0, min(1.0, prior + fit["deviation"]))
        materials[name] = {
            "personal": personal,
            "crowd": crowd_value,
            "prior": prior,
            "prior_source": "crowd" if crowd_value is not None else "typical",
            **fit,
        }

    family_observations = []
    for shares, error, weight in observations:
        by_family: dict[str, float] = {}
        for name, share in shares.items():
            family = crowd.family(name)
            if family is not None:
                by_family[family] = by_family.get(family, 0.0) + share
        family_observations.append((by_family, error, weight))
    families = dict(sorted(_shrunk(family_observations).items()))

    listed = [
        (fit["deviation"], name)
        for name, fit in materials.items()
        if fit["evidence"] >= LISTED_EVIDENCE
    ]
    liked = [name for deviation, name in sorted(listed, key=lambda row: (-row[0], row[1]))
             if deviation > 0][:LISTED_COUNT]
    disliked = [name for deviation, name in sorted(listed) if deviation < 0][:LISTED_COUNT]

    return {
        "schema": SCHEMA,
        "updated_at": (now or datetime.now(timezone.utc)).isoformat(),
        "ratings_used": len(ratings),
        "picks_used": len(picks),
        "method": METHOD,
        "offset_b": offset,
        "typical_prior": typical,
        "materials": materials,
        "families": families,
        "liked": liked,
        "disliked": disliked,
    }


async def current_fit(session: AsyncSession) -> dict[str, Any]:
    ratings = (await session.execute(select(LikingRating))).scalars().all()
    picks = (await session.execute(select(LikingPick))).scalars().all()
    return fit_personal_liking(ratings, picks, CrowdTable.load())


def write_personal_liking(fit: Mapping[str, Any], path: Path | None = None) -> Path:
    """Replace the personal liking file in one step (temporary file, then os.replace)."""

    destination = path or personal_liking_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(fit, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, destination)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise
    return destination


async def refit_and_write(session: AsyncSession) -> dict[str, Any]:
    fit = await current_fit(session)
    write_personal_liking(fit)
    return fit


async def _commit_then_refit(session: AsyncSession) -> bool:
    """Commit, then refit from committed data and write the file.

    Returns False when the refit or file write fails after the commit; the change stays saved.
    """

    await session.commit()
    try:
        await refit_and_write(session)
    except Exception:
        logger.exception("Personal liking fit could not be written after the change was saved.")
        return False
    return True


async def save_record(session: AsyncSession, record: Any) -> tuple[Any, bool]:
    """Add a rating or pick, commit it, then refit. Returns (record, personal_fit_written)."""

    session.add(record)
    written = await _commit_then_refit(session)
    await session.refresh(record)
    return record, written


async def delete_record(session: AsyncSession, record: Any) -> bool:
    """Delete a rating or pick, commit, then refit. Returns personal_fit_written."""

    await session.delete(record)
    return await _commit_then_refit(session)


async def refit_at_startup() -> bool:
    """Refit and write once at startup if the liking tables exist.

    Cheap and best effort: any error is logged and never blocks startup.
    """

    try:
        from sqlalchemy import inspect

        from app.db_session import engine, get_session

        async with engine.connect() as connection:
            tables = await connection.run_sync(
                lambda sync: set(inspect(sync).get_table_names())
            )
        if not {LikingRating.__tablename__, LikingPick.__tablename__} <= tables:
            return False
        async with get_session() as session:
            await refit_and_write(session)
        return True
    except Exception:
        logger.exception("Personal liking refit at startup failed; continuing.")
        return False
