from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.base import Base
from app.models.lab import APPEND_ONLY_TABLES
from app.models.lab_execution import EXECUTION_TABLE_NAMES


def _constraint_names(table_name: str, constraint_type) -> set[str]:
    table = Base.metadata.tables[table_name]
    return {
        str(constraint.name)
        for constraint in table.constraints
        if isinstance(constraint, constraint_type)
        and constraint.name is not None
    }


def test_execution_tables_are_registered_and_append_only():
    assert EXECUTION_TABLE_NAMES <= set(Base.metadata.tables)
    assert EXECUTION_TABLE_NAMES <= APPEND_ONLY_TABLES


def test_execution_identity_and_state_constraints_are_explicit():
    proposal_uniques = _constraint_names(
        "lab_bottle_action_proposals",
        UniqueConstraint,
    )
    proposal_checks = _constraint_names(
        "lab_bottle_action_proposals",
        CheckConstraint,
    )
    confirmation_uniques = _constraint_names(
        "lab_bottle_action_confirmations",
        UniqueConstraint,
    )
    commit_uniques = _constraint_names(
        "lab_bottle_action_commits",
        UniqueConstraint,
    )
    measurement_checks = _constraint_names(
        "lab_bottle_measurements",
        CheckConstraint,
    )

    assert "uq_lab_bottle_action_proposal_idempotency" in proposal_uniques
    assert "ck_lab_bottle_action_proposal_type" in proposal_checks
    assert (
        "uq_lab_bottle_action_confirmation_proposal"
        in confirmation_uniques
    )
    assert "uq_lab_bottle_action_commit_proposal" in commit_uniques
    assert "uq_lab_bottle_action_commit_event" in commit_uniques
    assert "ck_lab_bottle_measurement_authority" in measurement_checks
