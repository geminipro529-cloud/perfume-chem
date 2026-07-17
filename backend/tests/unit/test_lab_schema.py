from pathlib import Path

from sqlalchemy import UniqueConstraint

from app.core.config import Settings
from app.models.base import Base
from app.models.lab import APPEND_ONLY_TABLES, LAB_TABLE_NAMES


def test_lab_schema_uses_collision_safe_table_names_and_no_mutable_timestamp():
    assert LAB_TABLE_NAMES
    assert all(name.startswith("lab_") for name in LAB_TABLE_NAMES)
    assert LAB_TABLE_NAMES <= set(Base.metadata.tables)
    assert "materials" not in LAB_TABLE_NAMES

    for name in APPEND_ONLY_TABLES:
        assert "updated_at" not in Base.metadata.tables[name].columns


def test_bottle_stream_has_sequence_and_idempotency_uniqueness():
    table = Base.metadata.tables["lab_bottle_events"]
    unique_column_sets = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("bottle_id", "stream_sequence") in unique_column_sets
    assert ("bottle_id", "command_id") in unique_column_sets
    assert {"expected_sequence", "correction_of_event_id", "transaction_id"} <= set(
        table.columns.keys()
    )


def test_runtime_database_url_resolves_relative_sqlite_path_from_project_root():
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///./lab-test.db",
        _env_file=None,
    )
    path_text = settings.DATABASE_URL.removeprefix("sqlite+aiosqlite:///")

    assert Path(path_text).is_absolute()
    assert Path(path_text).name == "lab-test.db"
    assert Path(path_text).parent == Path(__file__).resolve().parents[3]
