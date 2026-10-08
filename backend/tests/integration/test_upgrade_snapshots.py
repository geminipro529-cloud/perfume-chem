"""Pre-upgrade snapshots are taken only for pending migrations and pruned on every call."""

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic.config import Config

import app.db_bootstrap as db_bootstrap

BACKEND_ROOT = Path(__file__).resolve().parents[2]
FIRST_REVISION = "20260716_0001"


def _config(database_path: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def _upgrade(database_path: Path, snapshot_directory: Path, revision: str = "head"):
    return db_bootstrap.upgrade_database(
        _config(database_path), revision, snapshot_directory=snapshot_directory
    )


def _files(directory: Path) -> set[str]:
    return {path.name for path in directory.iterdir()} if directory.exists() else set()


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y%m%dT%H%M%SZ")


def _make_pair(directory: Path, stem: str, moment: datetime, suffix: str) -> str:
    base = f"{stem}-pre-upgrade-{_stamp(moment)}-{suffix}"
    (directory / f"{base}.db").write_bytes(b"snapshot")
    (directory / f"{base}.manifest.json").write_text("{}", encoding="utf-8")
    return base


def _head(database_path: Path) -> list[tuple[str]]:
    connection = sqlite3.connect(database_path)
    try:
        return connection.execute("SELECT version_num FROM alembic_version").fetchall()
    finally:
        connection.close()


def test_up_to_date_database_is_not_snapshotted(tmp_path):
    database_path = tmp_path / "lab.db"
    snapshots = tmp_path / "snapshots"
    _upgrade(database_path, snapshots)  # creates the database at head

    first = _upgrade(database_path, snapshots)
    second = _upgrade(database_path, snapshots)

    assert first is None and second is None
    assert _files(snapshots) == set()


def test_database_at_older_revision_is_snapshotted_once_then_migrated(tmp_path):
    database_path = tmp_path / "lab.db"
    snapshots = tmp_path / "snapshots"
    _upgrade(database_path, snapshots, FIRST_REVISION)
    assert _files(snapshots) == set()

    snapshot = _upgrade(database_path, snapshots)

    assert snapshot is not None and snapshot.snapshot_path is not None
    names = _files(snapshots)
    assert len([name for name in names if name.endswith(".db")]) == 1
    assert len([name for name in names if name.endswith(".manifest.json")]) == 1
    assert snapshot.snapshot_path.with_suffix(".manifest.json").exists()
    head = db_bootstrap.alembic_head_revision(_config(database_path))
    assert _head(database_path) == [(head,)]
    assert _head(snapshot.snapshot_path) == [(FIRST_REVISION,)]


def test_pre_alembic_database_is_snapshotted(tmp_path):
    database_path = tmp_path / "lab.db"
    snapshots = tmp_path / "snapshots"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE materials (id INTEGER PRIMARY KEY, name TEXT)")
    connection.commit()
    connection.close()

    snapshot = _upgrade(database_path, snapshots)

    assert snapshot is not None and snapshot.snapshot_path is not None
    assert len(_files(snapshots)) == 2


def test_upgrade_prunes_old_snapshot_pairs_and_leaves_other_files(tmp_path):
    database_path = tmp_path / "lab.db"
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    now = datetime.now(timezone.utc)
    old = [
        _make_pair(snapshots, "lab", now - timedelta(days=40 + index), f"old{index:05d}")
        for index in range(8)
    ]
    young = [
        _make_pair(snapshots, "lab", now - timedelta(days=1 + index), f"new{index:05d}")
        for index in range(2)
    ]
    ancient = _stamp(now - timedelta(days=400))
    untouched = {
        "notes.txt",
        f"lab-pre-upgrade-{ancient}-sqlite00.sqlite",
        f"lab-pre-upgrade-{ancient}-orphan00.manifest.json",
        f"other-pre-upgrade-{ancient}-otherdb0.db",
    }
    for name in untouched:
        (snapshots / name).write_text("keep", encoding="utf-8")

    _upgrade(database_path, snapshots)

    survivors = young + old[:3]
    expected = untouched | {
        f"{base}{suffix}" for base in survivors for suffix in (".db", ".manifest.json")
    }
    assert _files(snapshots) == expected


def test_snapshots_younger_than_age_limit_survive_beyond_newest_count(tmp_path):
    now = datetime.now(timezone.utc)
    young = [
        _make_pair(tmp_path, "lab", now - timedelta(days=1 + index), f"new{index:05d}")
        for index in range(7)
    ]
    old = _make_pair(tmp_path, "lab", now - timedelta(days=60), "old00000")

    db_bootstrap.prune_upgrade_snapshots(tmp_path, "lab", now=now)

    assert _files(tmp_path) == {
        f"{base}{suffix}" for base in young for suffix in (".db", ".manifest.json")
    }
    assert not (tmp_path / f"{old}.db").exists()


def test_unparseable_timestamp_falls_back_to_modification_time(tmp_path):
    now = datetime.now(timezone.utc)
    for index in range(5):
        _make_pair(tmp_path, "lab", now - timedelta(days=1 + index), f"new{index:05d}")
    invalid = tmp_path / "lab-pre-upgrade-20269999T999999Z-badtime0.db"
    invalid.write_bytes(b"snapshot")
    recent = tmp_path / "lab-pre-upgrade-20269999T999999Z-badtime1.db"
    recent.write_bytes(b"snapshot")
    aged = (now - timedelta(days=90)).timestamp()
    os.utime(invalid, (aged, aged))

    db_bootstrap.prune_upgrade_snapshots(tmp_path, "lab", now=now)

    assert not invalid.exists()
    assert recent.exists()


def test_delete_failure_is_logged_and_does_not_stop_pruning(tmp_path, monkeypatch, caplog):
    now = datetime.now(timezone.utc)
    for index in range(5):
        _make_pair(tmp_path, "lab", now - timedelta(days=1 + index), f"new{index:05d}")
    stuck = _make_pair(tmp_path, "lab", now - timedelta(days=50), "stuck000")
    gone = _make_pair(tmp_path, "lab", now - timedelta(days=60), "gone0000")
    original_unlink = Path.unlink

    def unlink(self, missing_ok=False):
        if self.name == f"{stuck}.db":
            raise PermissionError("locked")
        return original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", unlink)

    db_bootstrap.prune_upgrade_snapshots(tmp_path, "lab", now=now)

    assert (tmp_path / f"{stuck}.db").exists()
    assert (tmp_path / f"{stuck}.manifest.json").exists()
    assert not (tmp_path / f"{gone}.db").exists()
    assert not (tmp_path / f"{gone}.manifest.json").exists()
    assert f"{stuck}.db" in caplog.text
