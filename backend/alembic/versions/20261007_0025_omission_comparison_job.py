"""Admit read-only omission-comparison planning jobs to the closed engine registry.

Revision ID: 20261007_0025
Revises: 20260929_0024
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261007_0025"
down_revision: str | None = "20260929_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PREVIOUS_JOB_TYPES = (
    "FORMULA_DESIGN",
    "FORMULA_ANALYSIS",
    "RELEASE_SIMULATION",
    "RELEASE_GATE",
    "MIXER_SEQUENCE",
    "OPTIMIZER_SEARCH",
    "CANDIDATE_EVALUATION",
    "SHORTLIST_EVALUATION",
    "MODEL_BENCHMARK",
    "PREFERENCE_ANALYSIS",
    "REFERENCE_PANEL_EVALUATION",
    "BATCH_GATE",
)
CURRENT_JOB_TYPES = ("OMISSION_COMPARISON_PLAN", *PREVIOUS_JOB_TYPES)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _set_sqlite_foreign_keys(*, enabled: bool) -> None:
    """Toggle SQLite enforcement outside a driver transaction and verify it."""

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return
    if bind.in_transaction():
        bind.commit()
    state = "ON" if enabled else "OFF"
    bind.exec_driver_sql(f"PRAGMA foreign_keys={state}")
    actual = int(bind.exec_driver_sql("PRAGMA foreign_keys").scalar_one())
    if actual != int(enabled):
        raise RuntimeError(f"failed to set SQLite foreign_keys={state}")
    bind.commit()


def _replace_job_type_constraint(values: tuple[str, ...]) -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    if is_sqlite:
        # SQLite batch mode recreates the parent table.  With populated child
        # event/result tables, dropping that parent is rejected while foreign
        # key enforcement is active.  An older migration deliberately restores
        # enforcement mid-upgrade, so this revision owns the narrow suspension
        # around its own parent-table rebuild instead of relying on env.py.
        _set_sqlite_foreign_keys(enabled=False)
        op.execute("DROP TABLE IF EXISTS _alembic_tmp_lab_engine_jobs")
        for operation in ("update", "delete"):
            op.execute(
                f"DROP TRIGGER IF EXISTS "
                f"trg_lab_engine_jobs_{operation}_append_only"
            )
    try:
        with op.batch_alter_table("lab_engine_jobs", recreate="always") as batch:
            batch.drop_constraint("ck_lab_engine_job_type", type_="check")
            batch.create_check_constraint(
                "ck_lab_engine_job_type",
                f"job_type IN ({_quoted(values)})",
            )
        if is_sqlite:
            for operation in ("UPDATE", "DELETE"):
                op.execute(
                    f"""
                    CREATE TRIGGER trg_lab_engine_jobs_{operation.lower()}_append_only
                    BEFORE {operation} ON lab_engine_jobs
                    BEGIN
                        SELECT RAISE(ABORT, 'append-only: lab_engine_jobs');
                    END
                    """
                )
            violations = bind.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(
                    "SQLite foreign-key check failed after job-table rebuild: "
                    f"{violations}"
                )
    finally:
        if is_sqlite:
            _set_sqlite_foreign_keys(enabled=True)


def upgrade() -> None:
    _replace_job_type_constraint(CURRENT_JOB_TYPES)


def downgrade() -> None:
    # Refuse before touching triggers or rebuilding a populated parent table.
    if op.get_bind().execute(sa.text(
        "SELECT count(*) FROM lab_engine_jobs WHERE job_type = 'OMISSION_COMPARISON_PLAN'"
    )).scalar_one():
        raise RuntimeError("OMISSION_JOBS_EXIST_DOWNGRADE_WITHHELD")
    _replace_job_type_constraint(PREVIOUS_JOB_TYPES)
