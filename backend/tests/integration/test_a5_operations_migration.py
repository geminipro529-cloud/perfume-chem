import sqlite3

import pytest

from alembic import command
from tests.integration.test_a2_planning_migration import (
    _config,
    _integrity,
    _minimum_rows,
    _revision,
)

A2_HEAD = "20260730_0003"
A5_HEAD = "20260730_0004"


def _legacy_movement(connection: sqlite3.Connection) -> None:
    _minimum_rows(connection)
    timestamp = "2026-07-30T04:00:00+00:00"
    connection.execute(
        """
        INSERT INTO lab_bottles (id, label, status, created_at)
        VALUES ('a5-bottle', 'A5 bottle', 'active', ?)
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO lab_bottle_events (
            id, bottle_id, stream_sequence, expected_sequence, command_id,
            transaction_id, event_type, payload_json, created_at
        ) VALUES (
            'a5-event', 'a5-bottle', 1, 0, 'a5-event-command',
            'a5-transaction', 'add_stock', '{}', ?
        )
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO lab_bottle_event_effects (
            id, event_id, bottle_id, stock_solution_id, material_id,
            mass_delta_g, created_at
        ) VALUES (
            'a5-effect', 'a5-event', 'a5-bottle', 'stock-1', 'material-1',
            1.0, ?
        )
        """,
        (timestamp,),
    )
    connection.execute(
        """
        INSERT INTO lab_inventory_movements (
            id, stock_solution_id, event_effect_id, mass_delta_g,
            reason, created_at
        ) VALUES (
            'a5-movement', 'stock-1', 'a5-effect', -1.0,
            'bottle_addition', ?
        )
        """,
        (timestamp,),
    )


def test_a5_migration_backfills_movement_contract_and_replays_downgrade(tmp_path):
    database = tmp_path / "a5-migration.db"
    config = _config(database)
    command.upgrade(config, A2_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _legacy_movement(connection)
        connection.commit()

    command.upgrade(config, A5_HEAD)
    with sqlite3.connect(database) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info('lab_inventory_movements')"
            )
        }
        row = connection.execute(
            """
            SELECT movement_type, raw_quantity, active_quantity, unit, basis,
                   balance_before, balance_after, actor, transaction_id,
                   idempotency_key, bottle_event_id
            FROM lab_inventory_movements
            WHERE id='a5-movement'
            """
        ).fetchone()
    assert {
        "movement_type",
        "raw_quantity",
        "active_quantity",
        "unit",
        "basis",
        "balance_before",
        "balance_after",
        "actor",
        "transaction_id",
        "idempotency_key",
        "bottle_event_id",
    } <= columns
    assert row == (
        "CONSUMPTION",
        1.0,
        0.1,
        "g",
        "mass",
        10.0,
        9.0,
        "legacy-migration",
        "a5-transaction",
        "legacy:a5-movement",
        "a5-event",
    )
    assert _revision(database) == A5_HEAD
    assert _integrity(database) == "ok"

    command.downgrade(config, A2_HEAD)
    assert _revision(database) == A2_HEAD
    assert _integrity(database) == "ok"
    command.upgrade(config, A5_HEAD)
    assert _revision(database) == A5_HEAD
    assert _integrity(database) == "ok"


def test_a5_movement_constraints_and_append_only_guards(tmp_path):
    database = tmp_path / "a5-constraints.db"
    config = _config(database)
    command.upgrade(config, A5_HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        _minimum_rows(connection)
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO lab_inventory_movements (
                    id, stock_solution_id, movement_type, raw_quantity,
                    active_quantity, unit, basis, balance_before,
                    balance_after, actor, transaction_id, idempotency_key,
                    reason, created_at
                ) VALUES (
                    'bad', 'stock-1', 'CONSUMPTION', 2, 3, 'g', 'mass',
                    1, -1, 'operator', 'transaction', 'bad',
                    'bad', CURRENT_TIMESTAMP
                )
                """
            )
        connection.rollback()

        connection.execute(
            """
            INSERT INTO lab_inventory_movements (
                id, stock_solution_id, movement_type, raw_quantity,
                active_quantity, unit, basis, balance_before,
                balance_after, actor, transaction_id, idempotency_key,
                admin_cause, mass_delta_g, reason, created_at
            ) VALUES (
                'valid', 'stock-1', 'ADJUSTMENT', 1, 1, 'g', 'mass',
                10, 9, 'operator', 'transaction', 'valid',
                'inventory count', -1, 'manual', CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                """
                UPDATE lab_inventory_movements
                SET actor='other'
                WHERE id='valid'
                """
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM lab_inventory_movements WHERE id='valid'"
            )
