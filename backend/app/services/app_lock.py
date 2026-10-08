"""OS-level lock that marks a SQLite database as in use by the running app.

The app holds an exclusive lock on ``<database file name>.app.lock`` beside
the database for as long as it runs.  The operating system releases the lock
when the process exits, crash included, so the lock never goes stale and the
lock file is never deleted.  ``python run_api_server.py --restore`` takes the
same lock without waiting and refuses to restore when it cannot.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy.engine import URL, make_url

LOCK_SUFFIX = ".app.lock"


def lock_path_for(database_path: Path) -> Path:
    return database_path.with_name(database_path.name + LOCK_SUFFIX)


def sqlite_database_path(database_url: str | URL) -> Path | None:
    """The resolved database file of a file-backed SQLite URL, else ``None``."""

    url = make_url(database_url)
    database = url.database
    if url.get_backend_name() != "sqlite" or not database:
        return None
    if database == ":memory:" or database.startswith("file:"):
        return None
    path = Path(database).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


class AppLock:
    """A held lock; ``release`` (or process exit) gives it up."""

    def __init__(self, path: Path, descriptor: int) -> None:
        self.path = path
        self._descriptor: int | None = descriptor

    def release(self) -> None:
        descriptor, self._descriptor = self._descriptor, None
        if descriptor is None:
            return
        try:
            _unlock(descriptor)
        finally:
            os.close(descriptor)


def try_acquire(lock_path: Path) -> AppLock | None:
    """Take the lock without waiting; ``None`` when another holder has it.

    Raises ``OSError`` when the lock file cannot be opened or created.
    """

    # os.open descriptors are not inherited by child processes, so the engine
    # worker cannot keep the lock alive after the app itself has exited.
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        locked = _lock(descriptor)
    except BaseException:
        os.close(descriptor)
        raise
    if not locked:
        os.close(descriptor)
        return None
    return AppLock(lock_path, descriptor)


if sys.platform == "win32":
    import msvcrt

    def _lock(descriptor: int) -> bool:
        os.lseek(descriptor, 0, os.SEEK_SET)
        try:
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    def _unlock(descriptor: int) -> None:
        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _lock(descriptor: int) -> bool:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True

    def _unlock(descriptor: int) -> None:
        fcntl.flock(descriptor, fcntl.LOCK_UN)


__all__ = ["AppLock", "LOCK_SUFFIX", "lock_path_for", "sqlite_database_path", "try_acquire"]
