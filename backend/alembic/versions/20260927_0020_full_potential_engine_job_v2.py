"""Expand the closed durable engine-job registry for the v2 research substrate.

Revision ID: 20260927_0020
Revises: 20260927_0019
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260927_0020"
down_revision: str | None = "20260927_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

V1_JOB_TYPES = (
    "FORMULA_ANALYSIS",
    "RELEASE_GATE",
    "MIXER_SEQUENCE",
    "OPTIMIZER_SEARCH",
    "SHORTLIST_EVALUATION",
    "BATCH_GATE",
)
V2_JOB_TYPES = (
    "FORMULA_ANALYSIS",
    "RELEASE_SIMULATION",
    "RELEASE_GATE",
    "MIXER_SEQUENCE",
    "OPTIMIZER_SEARCH",
    "CANDIDATE_EVALUATION",
    "SHORTLIST_EVALUATION",
    "MODEL_BENCHMARK",
    "PREFERENCE_ANALYSIS",
    "BATCH_GATE",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _drop_append_only_triggers() -> None:
    for operation in ("update", "delete"):
        op.execute(
            f"DROP TRIGGER IF EXISTS "
            f"trg_lab_engine_jobs_{operation}_append_only"
        )


def _create_append_only_triggers() -> None:
    for operation in ("UPDATE", "DELETE"):
        trigger_name = f"trg_lab_engine_jobs_{operation.lower()}_append_only"
        op.execute(
            f"""
            CREATE TRIGGER {trigger_name}
            BEFORE {operation} ON lab_engine_jobs
            BEGIN
                SELECT RAISE(ABORT, 'append-only: lab_engine_jobs');
            END
            """
        )


def _replace_job_type_constraint(values: tuple[str, ...]) -> None:
    _drop_append_only_triggers()
    with op.batch_alter_table("lab_engine_jobs", recreate="always") as batch:
        batch.drop_constraint("ck_lab_engine_job_type", type_="check")
        batch.create_check_constraint(
            "ck_lab_engine_job_type",
            f"job_type IN ({_quoted(values)})",
        )
    _create_append_only_triggers()


def upgrade() -> None:
    _replace_job_type_constraint(V2_JOB_TYPES)


def downgrade() -> None:
    # If v2-only rows exist, SQLite correctly refuses the table copy rather
    # than rewriting historical job types into a less certain v1 state.
    _replace_job_type_constraint(V1_JOB_TYPES)
