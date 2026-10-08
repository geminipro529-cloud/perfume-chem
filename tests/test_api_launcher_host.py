"""Local app handoff stays on loopback; the app (not the launcher) owns the worker."""

import os
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def _launch(monkeypatch, *argv):
    import subprocess

    calls = []

    def popen(args, **kwargs):  # the launcher must not spawn a second worker
        calls.append(("start", args, kwargs))

    def run(app, **kwargs):
        calls.append(
            ("api", app, kwargs, os.environ.get("PERFUME_ENGINE_WORKER_AUTOSTART"))
        )

    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=run))
    monkeypatch.setattr(sys, "argv", ["run_api_server.py", *argv])
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setenv("PYTHONPATH", "")
    # Record the variable so teardown removes whatever the launcher sets.
    monkeypatch.setenv("PERFUME_ENGINE_WORKER_AUTOSTART", "unset")
    monkeypatch.delenv("PERFUME_ENGINE_WORKER_AUTOSTART")
    runpy.run_path(str(ROOT / "run_api_server.py"), run_name="__main__")
    return calls


def test_loopback_launcher_leaves_the_worker_to_the_app_lifespan(monkeypatch):
    calls = _launch(monkeypatch, "--host", "127.0.0.1")
    assert len(calls) == 1
    assert calls[0][0:2] == ("api", "app.main:app")
    assert calls[0][2]["host"] == "127.0.0.1"
    assert calls[0][2]["port"] == 8000
    assert calls[0][3] is None  # app autostart stays at its default (on)


def test_no_engine_worker_switches_app_autostart_off(monkeypatch):
    calls = _launch(monkeypatch, "--no-engine-worker")
    assert [call[0] for call in calls] == ["api"]
    assert calls[0][3] == "0"


def test_default_launch_binds_loopback_without_warning(monkeypatch, capsys):
    calls = _launch(monkeypatch)
    assert calls[0][2]["host"] == "127.0.0.1"
    assert "WARNING" not in capsys.readouterr().err


def test_lan_flag_binds_all_interfaces_and_warns(monkeypatch, capsys):
    calls = _launch(monkeypatch, "--lan")
    assert calls[0][2]["host"] == "0.0.0.0"
    err = capsys.readouterr().err
    assert "WARNING" in err
    assert "no login" in err
    assert "delete" in err


def test_explicit_non_loopback_host_warns(monkeypatch, capsys):
    calls = _launch(monkeypatch, "--host", "0.0.0.0")
    assert calls[0][2]["host"] == "0.0.0.0"
    assert "no login" in capsys.readouterr().err


def test_explicit_host_wins_over_lan(monkeypatch, capsys):
    calls = _launch(monkeypatch, "--lan", "--host", "127.0.0.1")
    assert calls[0][2]["host"] == "127.0.0.1"
    assert "WARNING" not in capsys.readouterr().err


def test_localhost_and_ipv6_loopback_do_not_warn(monkeypatch, capsys):
    for host in ("localhost", "::1"):
        calls = _launch(monkeypatch, "--host", host)
        assert calls[0][2]["host"] == host
        assert "WARNING" not in capsys.readouterr().err


def test_restore_option_restores_the_backup_and_does_not_start_the_server(
    monkeypatch, tmp_path, capsys
):
    import socket
    import sqlite3

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    monkeypatch.syspath_prepend(str(ROOT / "backend"))
    from app.services.backup_service import backup_service_for_database_url

    config = Config(str(ROOT / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend" / "alembic"))
    head = ScriptDirectory.from_config(config).get_current_head()
    database = tmp_path / "lab.db"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE alembic_version (version_num TEXT PRIMARY KEY)")
    connection.execute("INSERT INTO alembic_version VALUES (?)", (head,))
    connection.execute("CREATE TABLE lab_record (name TEXT NOT NULL)")
    connection.execute("INSERT INTO lab_record VALUES ('first')")
    connection.commit()
    connection.close()
    database_url = f"sqlite+aiosqlite:///{database.as_posix()}"
    backup = backup_service_for_database_url(database_url).create_backup("manual")
    connection = sqlite3.connect(database)
    connection.execute("INSERT INTO lab_record VALUES ('second')")
    connection.commit()
    connection.close()

    def nothing_listening(*args, **kwargs):  # a real app on :8000 must not leak in
        raise ConnectionRefusedError

    monkeypatch.setattr(socket, "create_connection", nothing_listening)
    monkeypatch.setenv("DATABASE_URL", database_url)
    calls = _launch(monkeypatch, "--restore", backup.snapshot_path.name)

    assert calls == []  # uvicorn.run was not called
    connection = sqlite3.connect(database)
    rows = connection.execute("SELECT name FROM lab_record").fetchall()
    connection.close()
    assert rows == [("first",)]
    pre_restore = sorted((tmp_path / "lab-backups").glob("lab-pre-restore-*.sqlite"))
    assert len(pre_restore) == 1
    output = capsys.readouterr().out
    assert str(pre_restore[0]) in output
    assert f"python run_api_server.py --restore {pre_restore[0].name}" in output
    assert list(tmp_path.glob(".lab.db-restore-stage-*.sqlite")) == []
