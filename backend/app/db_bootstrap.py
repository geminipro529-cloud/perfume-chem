"""Safe SQLite bootstrap operations performed before schema migration."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

from alembic import command


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
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
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


def upgrade_database(
    config: Config,
    revision: str = "head",
    *,
    snapshot_directory: Path | None = None,
) -> UpgradeSnapshot | None:
    """Back up a file-backed SQLite database, then run Alembic."""

    database_path = _sqlite_file_path(config)
    snapshot = None
    if database_path is not None:
        destination = snapshot_directory or database_path.parent / "pre-upgrade-snapshots"
        snapshot = prepare_database_upgrade(database_path, destination)
    # Running inside the host process: keep its logging configuration.
    config.attributes["configure_logger"] = False
    command.upgrade(config, revision)
    return snapshot


__all__ = [
    "UpgradeSnapshot",
    "build_alembic_config",
    "prepare_database_upgrade",
    "upgrade_database",
]
