import shutil
import sqlite3

import pytest

from alembic import command
from tests.integration.test_a2_planning_migration import (
    _config,
    _integrity,
    _minimum_rows,
    _revision,
    _tables,
)

A2_SCIENCE_HEAD = "20260730_0002"
A2_EXECUTION_HEAD = "20260730_0003"
EXECUTION_TABLES = {
    "lab_bottle_action_proposals",
    "lab_bottle_action_confirmations",
    "lab_bottle_action_commits",
}


def _legacy_measurement(connection: sqlite3.Connection) -> None:
    timestamp = "2026-07-30T02:00:00+00:00"
    connection.execute(
        """
        INSERT INTO lab_bottles (id, label, status, created_at)
        VALUES ('bottle-1', 'Migration bottle', 'active', ?)
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO lab_bottle_events (
            id, bottle_id, stream_sequence, expected_sequence, command_id,
            transaction_id, event_type, payload_json, created_at
        ) VALUES (
            'bottle-event-1', 'bottle-1', 1, 0, 'create-bottle-1',
            'transaction-1', 'create', '{}', ?
        )
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO lab_bottle_measurements (
            id, bottle_event_id, quantity_kind, value, unit,
            standard_uncertainty, created_at
        ) VALUES (
            'legacy-measurement-1', 'bottle-event-1', 'mass',
            0.0, 'g', 0.001, ?
        )
        """,
        (timestamp,),
    )


def _execution_rows(connection: sqlite3.Connection) -> None:
    timestamp = "2026-07-30T02:00:00+00:00"
    _minimum_rows(connection)
    _legacy_measurement(connection)
    connection.execute(
        """
        INSERT INTO lab_bottle_action_proposals (
            id, schema_version, reservation_id, reservation_event_id,
            bottle_id, action_type, stock_solution_id, planned_mass_g,
            expected_sequence, idempotency_key, actor, rationale,
            content_sha256, created_at
        ) VALUES (
            'proposal-1', 'a2-bottle-action-v1', 'reservation-1',
            'reservation-event-1', 'bottle-1', 'ADD_STOCK', 'stock-1',
            1.0, 1, 'proposal-idempotency-1', 'operator', 'Execute',
            ?, ?
        )
        """,
        ("7" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_bottle_action_confirmations (
            id, proposal_id, decision, confirmer_pseudonym, confirmed_at,
            rationale, content_sha256, created_at
        ) VALUES (
            'confirmation-1', 'proposal-1', 'CONFIRMED', 'human-1', ?,
            'Verified', ?, ?
        )
        """,
        (timestamp, "8" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_bottle_measurements (
            id, bottle_event_id, proposal_id, quantity_kind, value, unit,
            standard_uncertainty, method, measured_at, actor, created_at
        ) VALUES (
            'proposal-measurement-1', NULL, 'proposal-1', 'mass',
            0.98, 'g', 0.002, 'gravimetric', ?, 'human-1', ?
        )
        """,
        (timestamp, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_inventory_reservation_events (
            id, reservation_id, sequence, parent_event_id,
            build_plan_version_id, build_plan_line_id, stock_solution_id,
            state, reserved_mass_g, idempotency_key, command_sha256,
            actor, rationale, created_at
        ) VALUES (
            'reservation-event-2', 'reservation-1', 2,
            'reservation-event-1', 'build-plan-version-1',
            'build-line-row-1', 'stock-1', 'FULFILLED', 1.0,
            'reservation-fulfilled-1', ?, 'operator', 'Committed', ?
        )
        """,
        ("9" * 64, timestamp),
    )
    connection.execute(
        """
        INSERT INTO lab_bottle_action_commits (
            id, proposal_id, bottle_event_id,
            fulfilled_reservation_event_id, actor, rationale,
            before_state_json, after_state_json, state_diff_json,
            content_sha256, created_at
        ) VALUES (
            'commit-1', 'proposal-1', 'bottle-event-1',
            'reservation-event-2', 'operator', 'Committed',
            '{}', '{}', '{}', ?, ?
        )
        """,
        ("a" * 64, timestamp),
    )


def test_a2_execution_migration_upgrades_empty_database(tmp_path):
    database = tmp_path / "empty.db"
    command.upgrade(_config(database), A2_EXECUTION_HEAD)
    assert _revision(database) == A2_EXECUTION_HEAD
    assert EXECUTION_TABLES <= _tables(database)
    assert _integrity(database) == "ok"


def test_a2_execution_migration_upgrades_representative_database_copy(tmp_path):
    source = tmp_path / "released-copy-source.db"
    config = _config(source)
    command.upgrade(config, A2_SCIENCE_HEAD)
    with sqlite3.connect(source) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _legacy_measurement(connection)
        connection.commit()

    copied = tmp_path / "released-copy-upgrade.db"
    shutil.copy2(source, copied)
    command.upgrade(_config(copied), A2_EXECUTION_HEAD)

    with sqlite3.connect(copied) as connection:
        row = connection.execute(
            """
            SELECT bottle_event_id, proposal_id, method, measured_at, actor
            FROM lab_bottle_measurements
            WHERE id='legacy-measurement-1'
            """
        ).fetchone()
    assert row == ("bottle-event-1", None, None, None, None)
    assert _revision(copied) == A2_EXECUTION_HEAD
    assert _integrity(copied) == "ok"


def test_a2_execution_migration_downgrade_and_reupgrade(tmp_path):
    database = tmp_path / "rollback.db"
    config = _config(database)
    command.upgrade(config, A2_EXECUTION_HEAD)
    command.downgrade(config, A2_SCIENCE_HEAD)
    assert not (EXECUTION_TABLES & _tables(database))
    assert _revision(database) == A2_SCIENCE_HEAD
    command.upgrade(config, A2_EXECUTION_HEAD)
    assert _revision(database) == A2_EXECUTION_HEAD
    assert _integrity(database) == "ok"


def test_a2_execution_constraints_and_append_only_guards(tmp_path):
    database = tmp_path / "constraints.db"
    command.upgrade(_config(database), A2_EXECUTION_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _execution_rows(connection)
        connection.commit()

        for table_name in sorted(EXECUTION_TABLES):
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(
                    f"UPDATE {table_name} SET created_at=created_at "
                    f"WHERE id=(SELECT id FROM {table_name} LIMIT 1)"
                )
            connection.rollback()
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(
                    f"DELETE FROM {table_name} "
                    f"WHERE id=(SELECT id FROM {table_name} LIMIT 1)"
                )
            connection.rollback()

        invalid_statements = (
            """
            INSERT INTO lab_bottle_action_proposals (
                id, schema_version, reservation_id, reservation_event_id,
                bottle_id, action_type, stock_solution_id, planned_mass_g,
                expected_sequence, idempotency_key, actor, rationale,
                content_sha256, created_at
            ) VALUES (
                'bad-proposal', 'v1', 'reservation-1',
                'reservation-event-1', 'bottle-1', 'TRANSFER', 'stock-1',
                -1, -1, 'bad-proposal', 'operator', 'Bad', 'bad',
                CURRENT_TIMESTAMP
            )
            """,
            """
            INSERT INTO lab_bottle_action_confirmations (
                id, proposal_id, decision, confirmer_pseudonym,
                confirmed_at, rationale, content_sha256, created_at
            ) VALUES (
                'bad-confirmation', 'proposal-1', 'MAYBE', 'human',
                CURRENT_TIMESTAMP, 'Bad', 'bad-confirmation',
                CURRENT_TIMESTAMP
            )
            """,
            """
            INSERT INTO lab_bottle_measurements (
                id, bottle_event_id, proposal_id, quantity_kind, value, unit,
                created_at
            ) VALUES (
                'bad-measurement', NULL, 'proposal-1', 'mass', 1.0, 'g',
                CURRENT_TIMESTAMP
            )
            """,
        )
        for statement in invalid_statements:
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement)
            connection.rollback()
