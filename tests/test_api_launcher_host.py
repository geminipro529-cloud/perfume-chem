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
