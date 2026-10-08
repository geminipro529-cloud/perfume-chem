"""Personal stock records live in data/user/ and are carried over once from output/."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

import engine.inventory_completions as completions
import engine.personal_inventory as personal
import engine.user_records as user_records

REPO_ROOT = Path(__file__).resolve().parents[1]


def _point_at(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Default and legacy folders inside tmp_path; env overrides removed."""

    new, old = tmp_path / "data" / "user", tmp_path / "output"
    old.mkdir(parents=True)
    monkeypatch.delenv(personal.ADDITION_PATH_ENV, raising=False)
    monkeypatch.delenv(completions.COMPLETION_PATH_ENV, raising=False)
    monkeypatch.setattr(personal, "DEFAULT_ADDITION_PATH", new / user_records.ADDITION_LOG_NAME)
    monkeypatch.setattr(personal, "LEGACY_ADDITION_PATH", old / user_records.ADDITION_LOG_NAME)
    monkeypatch.setattr(
        completions, "DEFAULT_COMPLETION_PATH", new / user_records.COMPLETION_LOG_NAME
    )
    monkeypatch.setattr(
        completions, "LEGACY_COMPLETION_PATH", old / user_records.COMPLETION_LOG_NAME
    )
    return new, old


def _write(path: Path, data: bytes, *, mtime: int = 1_700_000_000) -> None:
    path.write_bytes(data)
    os.utime(path, (mtime, mtime))


def test_defaults_point_into_data_user_with_unchanged_file_names():
    records = user_records.PROJECT_ROOT / "data" / "user"
    assert personal.DEFAULT_ADDITION_PATH == records / "user_inventory_addition_events.jsonl"
    assert completions.DEFAULT_COMPLETION_PATH == records / "user_inventory_completion_events.jsonl"
    assert personal.LEGACY_ADDITION_PATH == (
        user_records.PROJECT_ROOT / "output" / "user_inventory_addition_events.jsonl"
    )
    assert completions.LEGACY_COMPLETION_PATH == (
        user_records.PROJECT_ROOT / "output" / "user_inventory_completion_events.jsonl"
    )
    assert personal.ADDITION_PATH_ENV == "PERFUME_PERSONAL_INVENTORY_ADDITION_PATH"
    assert completions.COMPLETION_PATH_ENV == "PERFUME_INVENTORY_COMPLETION_PATH"


@pytest.mark.parametrize(
    ("module", "function", "name"),
    [
        (personal, "addition_log_path", user_records.ADDITION_LOG_NAME),
        (completions, "completion_log_path", user_records.COMPLETION_LOG_NAME),
    ],
)
def test_missing_default_is_filled_byte_exact_from_legacy(
    tmp_path, monkeypatch, module, function, name
):
    new, old = _point_at(tmp_path, monkeypatch)
    data = b'{"event_id":"a"}\r\n{"event_id":"b"}\n' + bytes(range(256))
    _write(old / name, data)
    before = (old / name).stat()

    resolved = getattr(module, function)()

    assert resolved == (new / name).resolve()
    assert resolved.read_bytes() == data
    assert (old / name).read_bytes() == data
    after = (old / name).stat()
    assert (after.st_mtime_ns, after.st_size) == (before.st_mtime_ns, before.st_size)
    assert sorted(p.name for p in new.iterdir()) == [name]


def test_existing_default_is_never_overwritten(tmp_path, monkeypatch):
    new, old = _point_at(tmp_path, monkeypatch)
    new.mkdir(parents=True)
    _write(old / user_records.ADDITION_LOG_NAME, b"old record\n")
    _write(new / user_records.ADDITION_LOG_NAME, b"current record\n")
    _write(old / user_records.COMPLETION_LOG_NAME, b"old details\n")
    _write(new / user_records.COMPLETION_LOG_NAME, b"current details\n")

    personal.addition_log_path()
    completions.completion_log_path()

    assert (new / user_records.ADDITION_LOG_NAME).read_bytes() == b"current record\n"
    assert (new / user_records.COMPLETION_LOG_NAME).read_bytes() == b"current details\n"


def test_no_legacy_file_copies_nothing(tmp_path, monkeypatch):
    new, _old = _point_at(tmp_path, monkeypatch)

    assert not personal.addition_log_path().exists()
    assert not completions.completion_log_path().exists()
    assert not new.exists() or list(new.iterdir()) == []


def test_env_override_or_explicit_path_copies_nothing(tmp_path, monkeypatch):
    new, old = _point_at(tmp_path, monkeypatch)
    for name in (
        user_records.ADDITION_LOG_NAME,
        user_records.COMPLETION_LOG_NAME,
        user_records.BASKET_LOG_NAME,
    ):
        _write(old / name, b"legacy\n")
    explicit = tmp_path / "explicit.jsonl"

    assert personal.addition_log_path(explicit) == explicit.resolve()
    assert completions.completion_log_path(explicit) == explicit.resolve()
    monkeypatch.setenv(personal.ADDITION_PATH_ENV, str(tmp_path / "env-additions.jsonl"))
    monkeypatch.setenv(completions.COMPLETION_PATH_ENV, str(tmp_path / "env-details.jsonl"))
    assert personal.addition_log_path() == (tmp_path / "env-additions.jsonl").resolve()
    assert completions.completion_log_path() == (tmp_path / "env-details.jsonl").resolve()

    assert not new.exists()
    assert not explicit.exists()
    assert not (tmp_path / "env-additions.jsonl").exists()
    assert not (tmp_path / "env-details.jsonl").exists()


def test_basket_log_is_copied_with_completion_log_but_lock_files_are_not(
    tmp_path, monkeypatch
):
    new, old = _point_at(tmp_path, monkeypatch)
    _write(old / user_records.COMPLETION_LOG_NAME, b"details\n")
    _write(old / user_records.BASKET_LOG_NAME, b"basket\n")
    _write(old / f"{user_records.COMPLETION_LOG_NAME}.lock", b"")
    _write(old / f"{user_records.ADDITION_LOG_NAME}.lock", b"")

    completions.completion_log_path()
    personal.addition_log_path()

    assert (new / user_records.BASKET_LOG_NAME).read_bytes() == b"basket\n"
    assert sorted(p.name for p in new.iterdir()) == sorted(
        [user_records.COMPLETION_LOG_NAME, user_records.BASKET_LOG_NAME]
    )


def test_filesystem_without_hard_links_falls_back_to_exclusive_create(
    tmp_path, monkeypatch
):
    new, old = _point_at(tmp_path, monkeypatch)
    _write(old / user_records.ADDITION_LOG_NAME, b"record\n" * 1000)

    def refuse(*_args, **_kwargs):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(user_records.os, "link", refuse)
    personal.addition_log_path()

    assert (new / user_records.ADDITION_LOG_NAME).read_bytes() == b"record\n" * 1000
    assert [p.name for p in new.iterdir()] == [user_records.ADDITION_LOG_NAME]


def test_copy_failure_raises_naming_both_paths_and_leaves_no_temp(tmp_path, monkeypatch):
    new, old = _point_at(tmp_path, monkeypatch)
    _write(old / user_records.ADDITION_LOG_NAME, b"record\n")

    def fail(*_args, **_kwargs):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(user_records.shutil, "copyfileobj", fail)
    with pytest.raises(user_records.RecordCarryOverError) as raised:
        personal.addition_log_path()

    message = str(raised.value)
    assert str(old / user_records.ADDITION_LOG_NAME) in message
    assert str((new / user_records.ADDITION_LOG_NAME).resolve()) in message
    assert list(new.iterdir()) == []
    assert (old / user_records.ADDITION_LOG_NAME).read_bytes() == b"record\n"


_RACER = """
import os, sys, time
from pathlib import Path
import engine.inventory_completions as completions
completions.DEFAULT_COMPLETION_PATH = Path(sys.argv[1])
completions.LEGACY_COMPLETION_PATH = Path(sys.argv[2])
go = Path(sys.argv[3])
print("ready", flush=True)
while not go.exists():
    time.sleep(0.001)
completions.completion_log_path()
print("done", flush=True)
"""


def test_racing_threads_and_processes_publish_one_identical_copy(tmp_path, monkeypatch):
    new, old = _point_at(tmp_path, monkeypatch)
    details = os.urandom(6 * 1024 * 1024)
    basket = os.urandom(3 * 1024 * 1024)
    _write(old / user_records.COMPLETION_LOG_NAME, details)
    _write(old / user_records.BASKET_LOG_NAME, basket)
    go = tmp_path / "go"

    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_")
        and key not in {completions.COMPLETION_PATH_ENV, personal.ADDITION_PATH_ENV}
    }
    environment["PYTHONPATH"] = str(REPO_ROOT)
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                _RACER,
                str(new / user_records.COMPLETION_LOG_NAME),
                str(old / user_records.COMPLETION_LOG_NAME),
                str(go),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
            cwd=tmp_path,
        )
        for _ in range(3)
    ]
    for process in processes:
        assert process.stdout is not None
        assert process.stdout.readline().strip() == "ready"

    barrier = threading.Barrier(9)
    errors: list[BaseException] = []

    def race() -> None:
        try:
            barrier.wait()
            completions.completion_log_path()
        except BaseException as error:  # noqa: BLE001 - collected for the assertion
            errors.append(error)

    threads = [threading.Thread(target=race) for _ in range(8)]
    for thread in threads:
        thread.start()
    go.touch()
    time.sleep(0.001)
    barrier.wait()
    for thread in threads:
        thread.join(timeout=60)
    outputs = [process.communicate(timeout=60) for process in processes]

    assert errors == []
    for process, (out, err) in zip(processes, outputs, strict=True):
        assert process.returncode == 0, err
        assert out.strip() == "done"
    assert sorted(p.name for p in new.iterdir()) == sorted(
        [user_records.COMPLETION_LOG_NAME, user_records.BASKET_LOG_NAME]
    )
    assert (new / user_records.COMPLETION_LOG_NAME).read_bytes() == details
    assert (new / user_records.BASKET_LOG_NAME).read_bytes() == basket
    assert (old / user_records.COMPLETION_LOG_NAME).read_bytes() == details
