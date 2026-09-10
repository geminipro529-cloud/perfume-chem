"""Preserve structured B1 rights and claim-scoped derivation metadata.

Revision ID: 20260810_0013
Revises: 20260731_0012
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260810_0013"
down_revision: str | None = "20260731_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_TYPES = (
    "AUTHENTICATED_FORMULA_OR_DOSSIER",
    "PRIMARY_PEER_REVIEWED_PAPER",
    "PRIMARY_RESEARCH_DATASET",
    "REVIEW_PAPER",
    "STANDARD",
    "REGULATION_OR_OFFICIAL_GUIDANCE",
    "AUTHORITATIVE_DATABASE_RECORD",
    "SUPPLIER_COA",
    "SUPPLIER_SPECIFICATION",
    "SUPPLIER_SDS",
    "SUPPLIER_IFRA_CERTIFICATE",
    "SUPPLIER_ALLERGEN_DECLARATION",
    "PATENT",
    "LOCAL_ANALYTICAL_EXPERIMENT",
    "LOCAL_SENSORY_EXPERIMENT",
    "EXPERT_NOTE",
    "SECONDARY_RECONSTRUCTION",
    "COMMUNITY_OBSERVATION",
    "AI_GENERATED_HYPOTHESIS",
)
LEGACY_SOURCE_TYPES = tuple(
    value for value in SOURCE_TYPES if value != "PRIMARY_RESEARCH_DATASET"
)
LEGACY_RIGHTS = {
    "reuse_status": "UNKNOWN",
    "license_or_reuse_restriction": "UNVERIFIED_LEGACY_ROW",
    "license_url": None,
    "redistribution_allowed": False,
    "spdx_identifier": None,
    "notes": "Legacy row requires explicit manifest rebind.",
}


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _drop_append_only_triggers(table_name: str) -> None:
    for operation in ("UPDATE", "DELETE"):
        op.execute(
            f"DROP TRIGGER IF EXISTS "
            f"trg_{table_name}_{operation.lower()}_append_only"
        )


def _create_append_only_triggers(table_name: str) -> None:
    for operation in ("UPDATE", "DELETE"):
        trigger_name = f"trg_{table_name}_{operation.lower()}_append_only"
        op.execute(
            f"""
            CREATE TRIGGER {trigger_name}
            BEFORE {operation} ON {table_name}
            BEGIN
                SELECT RAISE(ABORT, 'append-only: {table_name}');
            END
            """
        )


def _rights_default() -> str:
    # A plain server-default string is quoted by SQLAlchemy as one literal.
    # Passing JSON through sa.text() would treat ``:null`` / ``:false`` as
    # bind markers and corrupt the stored JSON during SQLite batch DDL.
    return json.dumps(LEGACY_RIGHTS, separators=(",", ":"))


def _set_sqlite_foreign_keys(*, enabled: bool) -> None:
    connection = op.get_bind()
    if connection.dialect.name != "sqlite":
        return
    state = "ON" if enabled else "OFF"
    # Alembic's SQLite environment enables foreign keys before entering a
    # non-transactional-DDL migration, which leaves a SQLAlchemy autobegin
    # transaction open. SQLite ignores a foreign_keys PRAGMA inside a live
    # transaction, so close that driver transaction before and after toggling.
    if connection.in_transaction():
        connection.commit()
    connection.exec_driver_sql(f"PRAGMA foreign_keys={state}")
    actual = int(connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one())
    if actual != int(enabled):
        raise RuntimeError(f"failed to set SQLite foreign_keys={state}")
    connection.commit()


def _assert_sqlite_foreign_keys_clean() -> None:
    connection = op.get_bind()
    if connection.dialect.name != "sqlite":
        return
    violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(
            "structured-rights migration created foreign-key violations"
        )


def _upgrade_schema() -> None:
    _drop_append_only_triggers("lab_source_document_versions")
    with op.batch_alter_table(
        "lab_source_document_versions",
        recreate="always",
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "rights_json",
                sa.JSON(),
                server_default=_rights_default(),
                nullable=False,
            )
        )
        batch_op.drop_constraint("ck_lab_source_type", type_="check")
        batch_op.create_check_constraint(
            "ck_lab_source_type",
            f"source_type IN ({_quoted(SOURCE_TYPES)})",
        )
    _create_append_only_triggers("lab_source_document_versions")

    op.add_column(
        "lab_source_derivation_links",
        sa.Column(
            "relation_scopes_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    _set_sqlite_foreign_keys(enabled=False)
    try:
        _upgrade_schema()
        _assert_sqlite_foreign_keys_clean()
    finally:
        _set_sqlite_foreign_keys(enabled=True)


def _downgrade_schema() -> None:
    _drop_append_only_triggers("lab_source_derivation_links")
    with op.batch_alter_table(
        "lab_source_derivation_links",
        recreate="always",
    ) as batch_op:
        batch_op.drop_column("relation_scopes_json")
    _create_append_only_triggers("lab_source_derivation_links")

    _drop_append_only_triggers("lab_source_document_versions")
    with op.batch_alter_table(
        "lab_source_document_versions",
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint("ck_lab_source_type", type_="check")
        batch_op.create_check_constraint(
            "ck_lab_source_type",
            f"source_type IN ({_quoted(LEGACY_SOURCE_TYPES)})",
        )
        batch_op.drop_column("rights_json")
    _create_append_only_triggers("lab_source_document_versions")


def downgrade() -> None:
    _set_sqlite_foreign_keys(enabled=False)
    try:
        _downgrade_schema()
        _assert_sqlite_foreign_keys_clean()
    finally:
        _set_sqlite_foreign_keys(enabled=True)
