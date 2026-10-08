"""Safe SQLite bootstrap operations performed before schema migration."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

from alembic import command

logger = logging.getLogger(__name__)

_SNAPSHOT_TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"
# Pruning keeps this many newest pre-upgrade snapshots ...
_SNAPSHOT_KEEP_NEWEST = 5
# ... plus every snapshot younger than this.
_SNAPSHOT_KEEP_YOUNGER_THAN = timedelta(days=30)


@dataclass(frozen=True, slots=True)
class UpgradeSnapshot:
    source_path: Path
    snapshot_path: Path | None
    schema_fingerprint_sha256: str
    snapshot_sha256: str | None
    created_at: str


def build_alembic_config(config_path: Path, database_url: str) -> Config:
    """Build Alembic configuration for the same database used by the application."""

    path = config_path.resolve()
    config = Config(str(path))
    config.set_main_option("script_location", str(path.parent / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def alembic_head_revision(config: Config) -> str:
    """Return the single migration head that defines application compatibility."""

    head = ScriptDirectory.from_config(config).get_current_head()
    if head is None:
        raise ValueError("Alembic script directory has no head revision")
    return head


def _schema_fingerprint(connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        """SELECT type, name, tbl_name, COALESCE(sql, '')
           FROM sqlite_master
           WHERE name NOT LIKE 'sqlite_%'
           ORDER BY type, name"""
    ).fetchall()
    canonical = json.dumps(rows, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_database_upgrade(
    database_path: Path,
    snapshot_directory: Path,
) -> UpgradeSnapshot:
    """Create a consistent snapshot and schema fingerprint before migration."""

    source_path = database_path.resolve()
    created_at = datetime.now(timezone.utc).isoformat()
    if not source_path.exists() or source_path.stat().st_size == 0:
        empty_fingerprint = hashlib.sha256(b"[]").hexdigest()
        return UpgradeSnapshot(
            source_path=source_path,
            snapshot_path=None,
            schema_fingerprint_sha256=empty_fingerprint,
            snapshot_sha256=None,
            created_at=created_at,
        )

    snapshot_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime(_SNAPSHOT_TIMESTAMP_FORMAT)
    descriptor, snapshot_name = tempfile.mkstemp(
        prefix=f"{source_path.stem}-pre-upgrade-{timestamp}-",
        suffix=".db",
        dir=snapshot_directory,
    )
    os.close(descriptor)
    snapshot_path = Path(snapshot_name)

    source = sqlite3.connect(source_path)
    destination = sqlite3.connect(snapshot_path)
    try:
        if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("source database failed SQLite integrity_check")
        source.backup(destination)
        destination.commit()
        if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("pre-upgrade snapshot failed SQLite integrity_check")
        fingerprint = _schema_fingerprint(destination)
    finally:
        destination.close()
        source.close()

    result = UpgradeSnapshot(
        source_path=source_path,
        snapshot_path=snapshot_path.resolve(),
        schema_fingerprint_sha256=fingerprint,
        snapshot_sha256=_file_sha256(snapshot_path),
        created_at=created_at,
    )
    manifest_path = snapshot_path.with_suffix(".manifest.json")
    manifest = asdict(result)
    manifest["source_path"] = str(result.source_path)
    manifest["snapshot_path"] = str(result.snapshot_path)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result


def _sqlite_file_path(config: Config) -> Path | None:
    configured_url = config.get_main_option("sqlalchemy.url")
    if not configured_url:
        return None
    url = make_url(configured_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        return None
    if url.database == ":memory:" or url.database.startswith("file:"):
        return None
    path = Path(url.database).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _target_revisions(config: Config, revision: str) -> frozenset[str] | None:
    """Resolve the revisions a migration to ``revision`` ends at, if resolvable offline."""

    try:
        revisions = ScriptDirectory.from_config(config).get_revisions(revision)
    except Exception:
        # Relative or unknown identifiers need a live context; treat them as pending.
        return None
    return frozenset(item.revision for item in revisions if item is not None)


def _database_at_revision(config: Config, revision: str, database_path: Path) -> bool:
    """Return True only when the database already stands at the target revision."""

    if not database_path.exists() or database_path.stat().st_size == 0:
        return False
    target = _target_revisions(config, revision)
    if target is None:
        return False
    connection = sqlite3.connect(database_path)
    try:
        has_version_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        ).fetchone()
        if has_version_table is None:
            return False
        current = frozenset(
            row[0] for row in connection.execute("SELECT version_num FROM alembic_version")
        )
    finally:
        connection.close()
    return current == target


def _snapshot_created_at(path: Path, timestamp: str) -> datetime | None:
    try:
        return datetime.strptime(timestamp, _SNAPSHOT_TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    except OSError:
        return None


def prune_upgrade_snapshots(
    snapshot_directory: Path,
    database_stem: str,
    *,
    now: datetime | None = None,
) -> None:
    """Delete old pre-upgrade snapshots of one database, keeping recent ones.

    Only ``<stem>-pre-upgrade-<timestamp>-<random>.db`` files written by
    ``prepare_database_upgrade`` are candidates; each deleted snapshot takes its
    ``.manifest.json`` with it. The newest snapshots and every snapshot younger
    than the age limit are kept. Deletion failures are logged, never raised.
    """

    pattern = re.compile(
        rf"{re.escape(database_stem)}-pre-upgrade-(\d{{8}}T\d{{6}}Z)-[a-z0-9_]{{8}}\.db"
    )
    try:
        entries = list(snapshot_directory.iterdir())
    except FileNotFoundError:
        return
    except OSError:
        logger.warning("Cannot list pre-upgrade snapshots in %s", snapshot_directory, exc_info=True)
        return

    snapshots: list[tuple[datetime, str, Path]] = []
    for path in entries:
        match = pattern.fullmatch(path.name)
        if match is None or not path.is_file():
            continue
        created_at = _snapshot_created_at(path, match.group(1))
        if created_at is not None:
            snapshots.append((created_at, path.name, path))
    snapshots.sort(reverse=True)

    cutoff = (now or datetime.now(timezone.utc)) - _SNAPSHOT_KEEP_YOUNGER_THAN
    for created_at, _name, snapshot_path in snapshots[_SNAPSHOT_KEEP_NEWEST:]:
        if created_at >= cutoff:
            continue
        # The snapshot goes first: if it cannot be deleted, its manifest stays with it.
        for path in (snapshot_path, snapshot_path.with_suffix(".manifest.json")):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.warning(
                    "Cannot delete old pre-upgrade snapshot file %s", path, exc_info=True
                )
                break
            logger.info("Deleted old pre-upgrade snapshot file %s", path)


def upgrade_database(
    config: Config,
    revision: str = "head",
    *,
    snapshot_directory: Path | None = None,
) -> UpgradeSnapshot | None:
    """Back up a file-backed SQLite database when a migration is pending, then run Alembic.

    Returns None when no snapshot step ran: a non-file database, or one already
    at ``revision``. Old pre-upgrade snapshots of the database are pruned on every call.
    """

    database_path = _sqlite_file_path(config)
    snapshot = None
    if database_path is not None:
        destination = snapshot_directory or database_path.parent / "pre-upgrade-snapshots"
        if not _database_at_revision(config, revision, database_path):
            snapshot = prepare_database_upgrade(database_path, destination)
        prune_upgrade_snapshots(destination, database_path.stem)
    # Running inside the host process: keep its logging configuration.
    config.attributes["configure_logger"] = False
    command.upgrade(config, revision)
    return snapshot


__all__ = [
    "UpgradeSnapshot",
    "build_alembic_config",
    "prepare_database_upgrade",
    "prune_upgrade_snapshots",
    "upgrade_database",
]
