"""Only unique-key violations are reported as duplicates."""

from sqlalchemy.exc import IntegrityError

from app.services.lab_service import _conflict_message


def _integrity_error(driver_message: str) -> IntegrityError:
    return IntegrityError("INSERT ...", {}, Exception(driver_message))


def test_unique_violation_says_already_exists() -> None:
    message = _conflict_message(
        _integrity_error("UNIQUE constraint failed: lab_materials.canonical_name")
    )
    assert "already exists" in message


def test_postgres_duplicate_key_says_already_exists() -> None:
    message = _conflict_message(
        _integrity_error('duplicate key value violates unique constraint "uq_name"')
    )
    assert "already exists" in message


def test_other_constraints_do_not_claim_a_duplicate() -> None:
    for driver_message in (
        "FOREIGN KEY constraint failed",
        "CHECK constraint failed: positive_amount",
        "NOT NULL constraint failed: lab_materials.canonical_name",
    ):
        message = _conflict_message(_integrity_error(driver_message))
        assert "already exists" not in message
        assert message == "The change conflicts with existing records."
