"""Verified SQLite backup, staged restore, and maintenance replacement."""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import sqlite3
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from sqlalchemy.engine import URL, make_url

from app import db_bootstrap

BACKUP_DIRECTORY_NAME = "lab-backups"


class RestoreSafetyError(ValueError):
    """Raised when a restore cannot satisfy the replacement safety contract."""


class RestoreAfterSafetyCopyError(RestoreSafetyError):
    """A restore failed after the live database was copied to safety.

    The live database may already have been replaced, so the caller must tell
    the user where the safety copies are.
    """

    def __init__(
        self,
        message: str,
        *,
        pre_restore_backup: BackupArtifact | None,
        damaged_copy: Path | None,
    ) -> None:
        super().__init__(message)
        self.pre_restore_backup = pre_restore_backup
        self.damaged_copy = damaged_copy


@dataclass(frozen=True, slots=True)
class BackupArtifact:
    snapshot_path: Path
    manifest_path: Path
    snapshot_sha256: str
    schema_fingerprint_sha256: str
    schema_revision: str
    created_at: str

    def as_dict(self) -> dict[str, str]:
        payload = asdict(self)
        payload["snapshot_path"] = str(self.snapshot_path)
        payload["manifest_path"] = str(self.manifest_path)
        return payload


@dataclass(frozen=True, slots=True)
class RestoreValidation:
    valid: bool
    snapshot_path: Path
    errors: tuple[str, ...]
    snapshot_sha256: str | None
    schema_revision: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "snapshot_path": str(self.snapshot_path),
            "errors": list(self.errors),
            "snapshot_sha256": self.snapshot_sha256,
            "schema_revision": self.schema_revision,
        }


@dataclass(frozen=True, slots=True)
class StagedRestore:
    staged_path: Path
    source_snapshot_path: Path
    expected_sha256: str
    schema_revision: str

    def as_dict(self) -> dict[str, str]:
        return {
            "staged_path": str(self.staged_path),
            "source_snapshot_path": str(self.source_snapshot_path),
            "expected_sha256": self.expected_sha256,
            "schema_revision": self.schema_revision,
        }


@dataclass(frozen=True, slots=True)
class AppliedRestore:
    database_path: Path
    # None when there was no live database to back up, or it was damaged.
    pre_restore_backup: BackupArtifact | None
    # A raw byte copy of a live database that failed its integrity check.
    damaged_copy: Path | None = None


class BackupService:
    """Operate only on a configured file-backed SQLite database."""

    def __init__(
        self,
        *,
        database_path: Path,
        backup_directory: Path,
        expected_schema_revision: str,
    ) -> None:
        self.database_path = database_path.expanduser().resolve()
        self.backup_directory = backup_directory.expanduser().resolve()
        self.expected_schema_revision = expected_schema_revision.strip()
        if not self.expected_schema_revision:
            raise ValueError("expected_schema_revision must not be empty")
        self.backup_directory.mkdir(parents=True, exist_ok=True)

    def create_backup(self, label: str = "manual") -> BackupArtifact:
        if not self.database_path.exists():
            raise FileNotFoundError(self.database_path)
        safe_label = "".join(
            character if character.isalnum() or character in {"-", "_"} else "-"
            for character in label.strip()
        ).strip("-") or "manual"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        descriptor, raw_path = tempfile.mkstemp(
            prefix=f"lab-{safe_label}-{timestamp}-",
            suffix=".sqlite",
            dir=self.backup_directory,
        )
        os.close(descriptor)
        snapshot_path = Path(raw_path).resolve()

        source = sqlite3.connect(self.database_path)
        destination = sqlite3.connect(snapshot_path)
        try:
            _require_integrity(source, "source database")
            source.backup(destination)
            destination.commit()
            _require_integrity(destination, "backup snapshot")
            schema_fingerprint = _schema_fingerprint(destination)
            schema_revision = _schema_revision(destination)
        except BaseException:
            snapshot_path.unlink(missing_ok=True)
            raise
        finally:
            destination.close()
            source.close()

        _fsync_path(snapshot_path)
        artifact = BackupArtifact(
            snapshot_path=snapshot_path,
            manifest_path=snapshot_path.with_suffix(".manifest.json"),
            snapshot_sha256=_file_sha256(snapshot_path),
            schema_fingerprint_sha256=schema_fingerprint,
            schema_revision=schema_revision,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        _atomic_json_write(artifact.manifest_path, artifact.as_dict())
        return artifact

    def validate_restore(self, snapshot_path: Path) -> RestoreValidation:
        path = self._managed_snapshot(snapshot_path)
        errors: list[str] = []
        manifest_path = path.with_suffix(".manifest.json")
        manifest: dict[str, object] = {}
        if not path.exists():
            errors.append("snapshot file is missing")
        if not manifest_path.exists():
            errors.append("snapshot manifest is missing")
        else:
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                errors.append("snapshot manifest is invalid JSON")

        actual_sha: str | None = None
        schema_revision: str | None = None
        if path.exists():
            actual_sha = _file_sha256(path)
            if manifest.get("snapshot_sha256") != actual_sha:
                errors.append("snapshot digest mismatch")
            try:
                connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
                try:
                    _require_integrity(connection, "restore snapshot")
                    actual_fingerprint = _schema_fingerprint(connection)
                    schema_revision = _schema_revision(connection)
                finally:
                    connection.close()
                if manifest.get("schema_fingerprint_sha256") != actual_fingerprint:
                    errors.append("schema fingerprint mismatch")
                if manifest.get("schema_revision") != schema_revision:
                    errors.append("manifest schema revision mismatch")
                if schema_revision != self.expected_schema_revision:
                    errors.append(
                        "schema revision is not the configured application revision"
                    )
            except (sqlite3.DatabaseError, RestoreSafetyError):
                errors.append("snapshot failed SQLite integrity_check")

        return RestoreValidation(
            valid=not errors,
            snapshot_path=path,
            errors=tuple(dict.fromkeys(errors)),
            snapshot_sha256=actual_sha,
            schema_revision=schema_revision,
        )

    @property
    def stage_prefix(self) -> str:
        return f".{self.database_path.name}-restore-stage-"

    def is_stage_file(self, path: Path) -> bool:
        """Whether ``path`` is a stage copy this service made for its database."""

        return path.parent == self.database_path.parent and bool(
            re.fullmatch(re.escape(self.stage_prefix) + _STAGE_SUFFIX_PATTERN, path.name)
        )

    def stage_restore(self, snapshot_path: Path) -> StagedRestore:
        validation = self.validate_restore(snapshot_path)
        if not validation.valid or validation.snapshot_sha256 is None:
            raise RestoreSafetyError(
                "restore snapshot is not valid: " + "; ".join(validation.errors)
            )
        # A stage is a full-size copy; only the newest one is ever applied, so
        # earlier ones would otherwise pile up (hidden, dot-prefixed) beside
        # the live database.
        for leftover in self.database_path.parent.iterdir():
            if self.is_stage_file(leftover) and leftover.is_file():
                leftover.unlink(missing_ok=True)
        staged_path, descriptor = self._create_stage_file()
        try:
            with os.fdopen(descriptor, "wb") as target:
                with validation.snapshot_path.open("rb") as source:
                    shutil.copyfileobj(source, target, 1024 * 1024)
                target.flush()
                os.fsync(target.fileno())
            if _file_sha256(staged_path) != validation.snapshot_sha256:
                raise RestoreSafetyError("staged restore digest mismatch")
        except BaseException:
            staged_path.unlink(missing_ok=True)
            raise
        return StagedRestore(
            staged_path=staged_path,
            source_snapshot_path=validation.snapshot_path,
            expected_sha256=validation.snapshot_sha256,
            schema_revision=validation.schema_revision or "unknown",
        )

    def _create_stage_file(self) -> tuple[Path, int]:
        while True:
            path = self.database_path.parent / (
                f"{self.stage_prefix}{secrets.token_hex(_STAGE_SUFFIX_BYTES)}.sqlite"
            )
            try:
                return path, os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_BINARY)
            except FileExistsError:
                continue

    def apply_staged_restore(
        self,
        staged: StagedRestore,
        *,
        maintenance_mode: bool,
    ) -> AppliedRestore:
        if not maintenance_mode:
            raise RestoreSafetyError(
                "database replacement requires maintenance mode or a stopped-server command"
            )
        staged_path = staged.staged_path.resolve()
        if not self.is_stage_file(staged_path):
            raise RestoreSafetyError("staged restore is outside the managed staging area")
        if _file_sha256(staged_path) != staged.expected_sha256:
            raise RestoreSafetyError("staged restore digest mismatch")
        connection = sqlite3.connect(f"file:{staged_path.as_posix()}?mode=ro", uri=True)
        try:
            _require_integrity(connection, "staged restore")
            if _schema_revision(connection) != self.expected_schema_revision:
                raise RestoreSafetyError("staged restore schema revision mismatch")
        finally:
            connection.close()

        # Copy the live database to safety first: a verified backup when it is
        # sound, a raw byte copy when it is damaged, nothing when it is missing.
        pre_restore: BackupArtifact | None = None
        damaged_copy: Path | None = None
        if self.database_path.exists():
            if _database_is_sound(self.database_path):
                pre_restore = self.create_backup(label="pre-restore")
            else:
                damaged_copy = self._keep_damaged_copy()
        try:
            os.replace(staged_path, self.database_path)
            restored = sqlite3.connect(self.database_path)
            try:
                _require_integrity(restored, "restored database")
            finally:
                restored.close()
        except (OSError, sqlite3.Error, RestoreSafetyError) as exc:
            raise RestoreAfterSafetyCopyError(
                str(exc), pre_restore_backup=pre_restore, damaged_copy=damaged_copy
            ) from exc
        return AppliedRestore(
            database_path=self.database_path,
            pre_restore_backup=pre_restore,
            damaged_copy=damaged_copy,
        )

    def _keep_damaged_copy(self) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        copy = self.database_path.with_name(f"{self.database_path.name}.corrupt-{timestamp}")
        with self.database_path.open("rb") as source, copy.open("xb") as target:
            shutil.copyfileobj(source, target, 1024 * 1024)
            target.flush()
            os.fsync(target.fileno())
        return copy

    def _managed_snapshot(self, snapshot_path: Path) -> Path:
        path = snapshot_path.expanduser().resolve()
        if not path.is_relative_to(self.backup_directory):
            raise RestoreSafetyError("snapshot must be inside the managed backup directory")
        return path


def backup_service_for_database_url(database_url: str | URL) -> BackupService:
    """Return the BackupService the app uses for ``database_url``.

    Backups live in ``lab-backups`` beside the database file and must carry the
    current Alembic head revision.
    """

    url = make_url(database_url)
    database = url.database
    if not database or database == ":memory:" or database.startswith("file:"):
        raise RestoreSafetyError("Backup requires a file-backed SQLite database.")
    database_path = Path(database).expanduser()
    if not database_path.is_absolute():
        database_path = Path.cwd() / database_path
    alembic_config = db_bootstrap.build_alembic_config(
        Path(__file__).resolve().parents[2] / "alembic.ini",
        str(url),
    )
    return BackupService(
        database_path=database_path,
        backup_directory=database_path.parent / BACKUP_DIRECTORY_NAME,
        expected_schema_revision=db_bootstrap.alembic_head_revision(alembic_config),
    )


_STAGE_SUFFIX_BYTES = 8
_STAGE_SUFFIX_PATTERN = rf"[0-9a-f]{{{2 * _STAGE_SUFFIX_BYTES}}}\.sqlite"
_O_BINARY = getattr(os, "O_BINARY", 0)  # Windows text-mode guard


def _fsync_path(path: Path) -> None:
    # Opened for writing: Windows refuses to flush a read-only handle.
    with path.open("rb+") as handle:
        os.fsync(handle.fileno())


def _database_is_sound(path: Path) -> bool:
    """False when the database is damaged; a locked database still raises."""

    try:
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            _require_integrity(connection, "live database")
        finally:
            connection.close()
    except sqlite3.OperationalError:
        raise
    except (sqlite3.DatabaseError, RestoreSafetyError):
        return False
    return True


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _schema_fingerprint(connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        """SELECT type, name, tbl_name, COALESCE(sql, '')
           FROM sqlite_master
           WHERE name NOT LIKE 'sqlite_%'
           ORDER BY type, name"""
    ).fetchall()
    canonical = json.dumps(rows, ensure_ascii=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _schema_revision(connection: sqlite3.Connection) -> str:
    table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'"
    ).fetchone()
    if table is None:
        return "unversioned"
    row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    return str(row[0]) if row is not None else "unversioned"


def _require_integrity(connection: sqlite3.Connection, label: str) -> None:
    result = connection.execute("PRAGMA integrity_check").fetchone()
    if result is None or result[0] != "ok":
        raise RestoreSafetyError(f"{label} failed SQLite integrity_check")


def _atomic_json_write(path: Path, payload: Mapping[str, object]) -> None:
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{path.name}-",
        suffix=".tmp",
        dir=path.parent,
    )
    os.close(descriptor)
    temporary = Path(raw_path)
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "AppliedRestore",
    "BackupArtifact",
    "BackupService",
    "RestoreAfterSafetyCopyError",
    "RestoreSafetyError",
    "RestoreValidation",
    "StagedRestore",
]
