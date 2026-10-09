"""Where the user's personal stock records live, and their one-time carry-over.

The append-only, hash-chained record logs (stock additions, completed stock
details, prepared dilutions, basket choices) are kept in ``data/user/``.  Older versions wrote them
to ``output/``, which the project treats as throwaway scratch.  The first time a
default record path is resolved, a missing record is copied byte for byte from
``output/``; the old file is never deleted, moved or modified, and an existing
record in ``data/user/`` is never overwritten.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
USER_RECORDS_DIR = PROJECT_ROOT / "data" / "user"
LEGACY_RECORDS_DIR = PROJECT_ROOT / "output"

ADDITION_LOG_NAME = "user_inventory_addition_events.jsonl"
COMPLETION_LOG_NAME = "user_inventory_completion_events.jsonl"
BASKET_LOG_NAME = "user_basket_events.jsonl"
DILUTION_LOG_NAME = "user_inventory_dilution_events.jsonl"

_COPY_CHUNK_BYTES = 1024 * 1024
_TEMP_SUFFIX = ".carry-over-tmp"


class RecordCarryOverError(RuntimeError):
    """A record in the old folder could not be copied to the new one."""


def record_files() -> dict[str, Path]:
    """The personal record files in use, keyed by their standard file name.

    Paths follow the same rules as the logs themselves (explicit environment
    overrides win; the basket log sits beside the completion log), and
    resolving them carries old records over from ``output/``.  A file may not
    exist yet.
    """

    from engine.inventory_completions import completion_log_path
    from engine.inventory_dilutions import dilution_log_path
    from engine.personal_inventory import addition_log_path

    completion = completion_log_path()
    return {
        ADDITION_LOG_NAME: addition_log_path(),
        COMPLETION_LOG_NAME: completion,
        BASKET_LOG_NAME: completion.with_name(BASKET_LOG_NAME),
        DILUTION_LOG_NAME: dilution_log_path(),
    }


def copy_legacy_record(legacy: Path, destination: Path) -> bool:
    """Copy ``legacy`` to ``destination`` when only the legacy file exists.

    Returns True when this call published the copy.  Safe against concurrent
    callers in other threads and processes: the copy is written to a unique
    temporary file beside the destination and published with a hard link, so
    the destination appears complete or not at all, and is never overwritten.
    """

    if destination.exists():
        return False
    try:
        source = open(legacy, "rb")  # noqa: SIM115 - closed below
    except FileNotFoundError:
        return False
    except OSError as error:
        raise _carry_over_error(legacy, destination, error) from error
    try:
        with source:
            destination.parent.mkdir(parents=True, exist_ok=True)
            handle, temp_name = tempfile.mkstemp(
                prefix=f".{destination.name}.",
                suffix=_TEMP_SUFFIX,
                dir=destination.parent,
            )
            temp = Path(temp_name)
            try:
                with os.fdopen(handle, "wb") as target:
                    shutil.copyfileobj(source, target, _COPY_CHUNK_BYTES)
                    target.flush()
                    os.fsync(target.fileno())
                return _publish(temp, destination)
            finally:
                temp.unlink(missing_ok=True)
    except OSError as error:
        raise _carry_over_error(legacy, destination, error) from error


def _publish(temp: Path, destination: Path) -> bool:
    try:
        os.link(temp, destination)
    except FileExistsError:
        return False  # another caller published first
    except OSError:
        return _publish_by_exclusive_create(temp, destination)
    return True


def _publish_by_exclusive_create(temp: Path, destination: Path) -> bool:
    """Fallback for filesystems that refuse hard links."""

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        handle = os.open(destination, flags, 0o644)
    except FileExistsError:
        return False
    try:
        with os.fdopen(handle, "wb") as target, open(temp, "rb") as source:
            shutil.copyfileobj(source, target, _COPY_CHUNK_BYTES)
            target.flush()
            os.fsync(target.fileno())
    except BaseException:
        destination.unlink(missing_ok=True)  # this call created it; leave no partial record
        raise
    return True


def _carry_over_error(legacy: Path, destination: Path, error: OSError) -> RecordCarryOverError:
    return RecordCarryOverError(
        f"Could not copy the stock record {legacy} to {destination}: {error}. "
        f"Nothing was deleted; {legacy} is unchanged."
    )
