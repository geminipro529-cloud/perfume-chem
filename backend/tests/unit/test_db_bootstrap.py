import sqlite3
from pathlib import Path

from alembic.config import Config

import app.db_bootstrap as db_bootstrap
from app.core.config import PROJECT_ROOT, Settings
from app.db_bootstrap import _sqlite_file_path, prepare_database_upgrade
from app.db_session import _enable_sqlite_foreign_keys


def test_sqlite_connection_enables_foreign_keys():
    connection = sqlite3.connect(":memory:")
    try:
        _enable_sqlite_foreign_keys(connection, None)
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        connection.close()


def test_pre_upgrade_snapshot_preserves_populated_database_and_fingerprint(tmp_path):
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE materials (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO materials (name) VALUES ('legacy iris')")
    connection.commit()
    connection.close()

    result = prepare_database_upgrade(database_path, tmp_path / "snapshots")

    assert result.source_path == database_path.resolve()
    assert result.snapshot_path is not None and result.snapshot_path.exists()
    assert len(result.schema_fingerprint_sha256) == 64
    snapshot = sqlite3.connect(result.snapshot_path)
    try:
        assert snapshot.execute("SELECT name FROM materials").fetchone()[0] == "legacy iris"
    finally:
        snapshot.close()


def test_pre_upgrade_snapshot_names_do_not_collide(tmp_path):
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE materials (id INTEGER PRIMARY KEY, name TEXT)")
    connection.commit()
    connection.close()

    first = prepare_database_upgrade(database_path, tmp_path / "snapshots")
    second = prepare_database_upgrade(database_path, tmp_path / "snapshots")

    assert first.snapshot_path != second.snapshot_path
    assert first.snapshot_path is not None and first.snapshot_path.exists()
    assert second.snapshot_path is not None and second.snapshot_path.exists()


def test_schema_fingerprint_is_calculated_from_snapshot_connection(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE materials (id INTEGER PRIMARY KEY, name TEXT)")
    connection.commit()
    connection.close()
    fingerprinted_paths: list[Path] = []
    original = db_bootstrap._schema_fingerprint

    def record_database_path(connection):
        database_file = connection.execute("PRAGMA database_list").fetchone()[2]
        fingerprinted_paths.append(Path(database_file).resolve())
        return original(connection)

    monkeypatch.setattr(db_bootstrap, "_schema_fingerprint", record_database_path)

    result = prepare_database_upgrade(database_path, tmp_path / "snapshots")

    assert result.snapshot_path is not None
    assert fingerprinted_paths == [result.snapshot_path]


def test_database_url_preserves_sqlite_memory_and_uri_forms():
    memory_url = "sqlite+aiosqlite:///:memory:"
    uri_url = "sqlite+aiosqlite:///file:lab?mode=memory&cache=shared&uri=true"

    assert Settings(DATABASE_URL=memory_url).DATABASE_URL == memory_url
    assert Settings(DATABASE_URL=uri_url).DATABASE_URL == uri_url


def test_database_url_resolves_only_file_path_and_preserves_query_string():
    url = "sqlite+aiosqlite:///data/lab.db?timeout=30&mode=rwc"

    resolved = Settings(DATABASE_URL=url).DATABASE_URL

    expected_path = (PROJECT_ROOT / "data" / "lab.db").resolve().as_posix()
    assert resolved == f"sqlite+aiosqlite:///{expected_path}?timeout=30&mode=rwc"


def test_upgrade_path_is_absent_when_alembic_url_is_unset():
    assert _sqlite_file_path(Config()) is None


def test_programmatic_alembic_config_uses_application_database_url(tmp_path):
    config_path = tmp_path / "alembic.ini"
    config_path.write_text(
        "[alembic]\nscript_location = stale\nsqlalchemy.url = sqlite:///stale.db\n",
        encoding="utf-8",
    )
    database_url = "sqlite+aiosqlite:///configured.db"

    config = db_bootstrap.build_alembic_config(config_path, database_url)

    assert config.get_main_option("sqlalchemy.url") == database_url
    assert config.get_main_option("script_location") == str(tmp_path / "alembic")
