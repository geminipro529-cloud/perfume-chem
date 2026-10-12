"""Kenny's liking ratings and two-bottle picks for bottles he mixed.

Each row records which materials made up the bottle (``material_shares``) so the
personal liking fit can spread a rating over them.  These are his own records;
nothing here is sent anywhere.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.lab import UTCDateTime

LIKING_WINDOWS = ("opening", "1h", "4h")
LIKING_PICK_CHOICES = ("a", "b", "same")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LikingRating(Base):
    __tablename__ = "liking_ratings"
    __table_args__ = (
        CheckConstraint(f"window IN ({_quoted(LIKING_WINDOWS)})", name="ck_liking_ratings_window"),
        CheckConstraint("liking BETWEEN 1 AND 10", name="ck_liking_ratings_liking"),
        CheckConstraint(
            "complexity IS NULL OR complexity BETWEEN 1 AND 10",
            name="ck_liking_ratings_complexity",
        ),
        CheckConstraint(
            "crowd_guess IS NULL OR crowd_guess BETWEEN -1 AND 1",
            name="ck_liking_ratings_crowd_guess",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=_utcnow, nullable=False, index=True
    )
    formula_name: Mapped[str] = mapped_column(String(255), nullable=False)
    formula_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    window: Mapped[str] = mapped_column(String(16), nullable=False)
    liking: Mapped[int] = mapped_column(Integer, nullable=False)
    complexity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    too_loud: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    material_shares: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    crowd_guess: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="lab_card")


class LikingPick(Base):
    __tablename__ = "liking_picks"
    __table_args__ = (
        CheckConstraint(f"window IN ({_quoted(LIKING_WINDOWS)})", name="ck_liking_picks_window"),
        CheckConstraint(
            f"preferred IN ({_quoted(LIKING_PICK_CHOICES)})", name="ck_liking_picks_preferred"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=_utcnow, nullable=False, index=True
    )
    window: Mapped[str] = mapped_column(String(16), nullable=False)
    formula_a_name: Mapped[str] = mapped_column(String(255), nullable=False)
    formula_a_key: Mapped[str] = mapped_column(String(255), nullable=False)
    shares_a: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    crowd_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    formula_b_name: Mapped[str] = mapped_column(String(255), nullable=False)
    formula_b_key: Mapped[str] = mapped_column(String(255), nullable=False)
    shares_b: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    crowd_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred: Mapped[str] = mapped_column(String(8), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class LikingMaterialRating(Base):
    """One material smelled on a blotter and rated 1 to 10 (a direct observation)."""

    __tablename__ = "liking_material_ratings"
    __table_args__ = (
        CheckConstraint("liking BETWEEN 1 AND 10", name="ck_liking_material_ratings_liking"),
        CheckConstraint(
            "strength IS NULL OR strength IN ('weak', 'medium', 'strong')",
            name="ck_liking_material_ratings_strength",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=_utcnow, nullable=False, index=True
    )
    material: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    stock_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    strength: Mapped[str | None] = mapped_column(String(8), nullable=True)
    liking: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="stock_card")
