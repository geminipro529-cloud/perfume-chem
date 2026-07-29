"""Append-oriented physical execution records for canonical bottle actions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord, UTCDateTime

ACTION_TYPES = ("ADD_STOCK",)
CONFIRMATION_DECISIONS = ("CONFIRMED", "REJECTED")


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LabBottleActionProposal(LabRecord):
    __tablename__ = "lab_bottle_action_proposals"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_lab_bottle_action_proposal_idempotency",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_bottle_action_proposal_content_sha256",
        ),
        CheckConstraint(
            f"action_type IN ({_quoted(ACTION_TYPES)})",
            name="ck_lab_bottle_action_proposal_type",
        ),
        CheckConstraint(
            "planned_mass_g > 0",
            name="ck_lab_bottle_action_proposal_mass",
        ),
        CheckConstraint(
            "expected_sequence >= 0",
            name="ck_lab_bottle_action_proposal_sequence",
        ),
    )

    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    reservation_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    reservation_event_id: Mapped[str] = mapped_column(
        ForeignKey("lab_inventory_reservation_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bottle_id: Mapped[str] = mapped_column(
        ForeignKey("lab_bottles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    stock_solution_id: Mapped[str] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    planned_mass_g: Mapped[float] = mapped_column(Float, nullable=False)
    expected_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabBottleActionConfirmation(LabRecord):
    __tablename__ = "lab_bottle_action_confirmations"
    __table_args__ = (
        UniqueConstraint(
            "proposal_id",
            name="uq_lab_bottle_action_confirmation_proposal",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_bottle_action_confirmation_content_sha256",
        ),
        CheckConstraint(
            f"decision IN ({_quoted(CONFIRMATION_DECISIONS)})",
            name="ck_lab_bottle_action_confirmation_decision",
        ),
    )

    proposal_id: Mapped[str] = mapped_column(
        ForeignKey("lab_bottle_action_proposals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    confirmer_pseudonym: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    confirmed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabBottleActionCommit(LabRecord):
    __tablename__ = "lab_bottle_action_commits"
    __table_args__ = (
        UniqueConstraint(
            "proposal_id",
            name="uq_lab_bottle_action_commit_proposal",
        ),
        UniqueConstraint(
            "bottle_event_id",
            name="uq_lab_bottle_action_commit_event",
        ),
        UniqueConstraint(
            "fulfilled_reservation_event_id",
            name="uq_lab_bottle_action_commit_reservation_event",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_bottle_action_commit_content_sha256",
        ),
    )

    proposal_id: Mapped[str] = mapped_column(
        ForeignKey("lab_bottle_action_proposals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bottle_event_id: Mapped[str] = mapped_column(
        ForeignKey("lab_bottle_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fulfilled_reservation_event_id: Mapped[str] = mapped_column(
        ForeignKey("lab_inventory_reservation_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    before_state_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    after_state_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    state_diff_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


EXECUTION_TABLE_NAMES = {
    "lab_bottle_action_proposals",
    "lab_bottle_action_confirmations",
    "lab_bottle_action_commits",
}


__all__ = [
    "ACTION_TYPES",
    "CONFIRMATION_DECISIONS",
    "EXECUTION_TABLE_NAMES",
    "LabBottleActionCommit",
    "LabBottleActionConfirmation",
    "LabBottleActionProposal",
]
