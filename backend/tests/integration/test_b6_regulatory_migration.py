import hashlib
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.models.lab_regulatory import (
    LabRegulatoryAuthorityFinding,
    LabRegulatoryCompositionEntry,
    LabRegulatoryCompositionProfile,
    LabRegulatoryRuleVersion,
    LabRegulatorySnapshotVersion,
    LabRegulatorySourceVersion,
    LabSupplierDocumentBinding,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
B5_HEAD = "20260731_0009"
B6_HEAD = "20260731_0010"
B6_MODELS = (
    LabRegulatorySourceVersion,
    LabRegulatoryRuleVersion,
    LabSupplierDocumentBinding,
    LabRegulatoryCompositionProfile,
    LabRegulatoryCompositionEntry,
    LabRegulatorySnapshotVersion,
    LabRegulatoryAuthorityFinding,
)
B6_TABLES = {model.__tablename__ for model in B6_MODELS}


def _config(database_path: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option(
        "sqlalchemy.url",
        f"sqlite:///{database_path.as_posix()}",
    )
    return config


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _table_state(
    connection: sqlite3.Connection,
    table_names: set[str],
) -> dict[str, tuple[int, str]]:
    state = {}
    for table_name in sorted(table_names):
        columns = tuple(
            str(row[1])
            for row in connection.execute(
                f'PRAGMA table_info("{table_name}")'
            )
        )
        rows = connection.execute(
            f'SELECT * FROM "{table_name}" ORDER BY rowid'
        ).fetchall()
        digest = hashlib.sha256(
            repr((columns, rows)).encode("utf-8")
        ).hexdigest()
        state[table_name] = (len(rows), digest)
    return state


def _insert_prior_sentinel(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_legacy_threshold_records
        (id, created_at, schema_version, material_key, medium,
         numeric_value, original_unit, verification_status,
         authority_state, source_payload_json, content_sha256)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "b6-prior-sentinel",
            "2026-07-31T00:00:00+00:00",
            "lab-legacy-threshold-v1",
            "linalool",
            "AIR",
            0.51,
            "ppb",
            "DERIVED",
            "LEGACY_CONTEXT_INCOMPLETE",
            "{}",
            "a" * 64,
        ),
    )


def _insert_official_source(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO lab_source_document_versions (
            id, source_id, version_number, schema_version, source_type,
            title, authors_json, identifiers_json, default_locator_json,
            artifact_sha256, language, review_state, independence_group,
            record_sha256, created_at
        ) VALUES (
            'b6-official-source', 'b6-source', 1, 'lab-source-document-v1',
            'REGULATION_OR_OFFICIAL_GUIDANCE', 'B6 official source', '[]',
            '{}', '{"url": "https://example.invalid"}', ?, 'en', 'REVIEWED',
            'b6-official', ?, ?
        )
        """,
        (
            "b" * 64,
            "c" * 64,
            "2026-07-31T00:00:00+00:00",
        ),
    )


def _insert_regulatory_source(
    connection: sqlite3.Connection,
    *,
    row_id: str = "b6-regulatory-source",
    status: str = "CURRENT_ENFORCED_OR_FORMALLY_NOTIFIED",
    content_sha256: str = "e" * 64,
) -> None:
    connection.execute(
        """
        INSERT INTO lab_regulatory_source_versions (
            id, created_at, authority_id, revision_number, parent_version_id,
            schema_version, authority_family, identifier, published_version,
            jurisdiction, status, notified_on, effective_from,
            effective_through, checked_at, supersedes_source_version_id,
            official_source_document_version_id, source_locator_json,
            official_source_sha256, notes_json, content_sha256
        ) VALUES (
            ?, CURRENT_TIMESTAMP, 'ifra-standards', 1, NULL,
            'lab-regulatory-source-v1', 'IFRA_STANDARD', 'IFRA Standards',
            '51', 'GLOBAL', ?, '2023-06-30', '2023-06-30', NULL,
            '2026-07-31T00:00:00+00:00', NULL, 'b6-official-source',
            '{}', ?, '{}', ?
        )
        """,
        (row_id, status, "b" * 64, content_sha256),
    )


def test_b6_migration_adds_seven_empty_tables_without_changing_prior_rows(
    tmp_path,
):
    database = tmp_path / "b6-empty.db"
    config = _config(database)
    command.upgrade(config, B5_HEAD)
    with sqlite3.connect(database) as connection:
        _insert_prior_sentinel(connection)
        connection.commit()
        prior_tables = _tables(connection) - {"alembic_version"}
        prior_state = _table_state(connection, prior_tables)

    command.upgrade(config, B6_HEAD)

    with sqlite3.connect(database) as connection:
        assert B6_TABLES <= _tables(connection)
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (B6_HEAD,)
        assert {
            table: connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            for table in B6_TABLES
        } == {table: 0 for table in B6_TABLES}
        assert _table_state(connection, prior_tables) == prior_state
        triggers = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
        for table in B6_TABLES:
            assert f"trg_{table}_no_update" in triggers
            assert f"trg_{table}_no_delete" in triggers
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_b6_migration_downgrades_only_b6_and_reupgrades_empty(tmp_path):
    database = tmp_path / "b6-roundtrip.db"
    config = _config(database)
    command.upgrade(config, B5_HEAD)
    with sqlite3.connect(database) as connection:
        _insert_prior_sentinel(connection)
        connection.commit()
        prior_tables = _tables(connection) - {"alembic_version"}
        prior_state = _table_state(connection, prior_tables)

    command.upgrade(config, B6_HEAD)
    command.downgrade(config, B5_HEAD)

    with sqlite3.connect(database) as connection:
        assert not (B6_TABLES & _tables(connection))
        assert _table_state(connection, prior_tables) == prior_state
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (B5_HEAD,)
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    command.upgrade(config, B6_HEAD)
    with sqlite3.connect(database) as connection:
        assert B6_TABLES <= _tables(connection)
        assert all(
            connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            == 0
            for table in B6_TABLES
        )


def test_b6_database_guards_source_status_and_append_only_history(tmp_path):
    database = tmp_path / "b6-constraints.db"
    config = _config(database)
    command.upgrade(config, B6_HEAD)

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _insert_official_source(connection)
        _insert_regulatory_source(connection)
        connection.commit()

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE lab_regulatory_source_versions "
                "SET status=status WHERE id='b6-regulatory-source'"
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM lab_regulatory_source_versions "
                "WHERE id='b6-regulatory-source'"
            )
        connection.rollback()
        with pytest.raises(
            sqlite3.IntegrityError,
            match="ck_lab_regulatory_source_status",
        ):
            _insert_regulatory_source(
                connection,
                row_id="b6-bad-status",
                status="CURRENT",
                content_sha256="f" * 64,
            )
