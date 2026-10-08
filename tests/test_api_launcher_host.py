"""Local app handoff can stay on loopback without losing its managed worker."""

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace


def test_loopback_launcher_owns_worker_and_terminates_it(monkeypatch):
    import subprocess

    root = Path(__file__).resolve().parents[1]
    calls = []

    class Worker:
        def __init__(self, args, **kwargs):
            calls.append(("start", args, kwargs))

        def poll(self):
            return None

        def terminate(self):
            calls.append(("terminate",))

        def wait(self, timeout):
            calls.append(("wait", timeout))

    def run(app, **kwargs):
        calls.append(("api", app, kwargs))

    monkeypatch.setattr(subprocess, "Popen", Worker)
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=run))
    monkeypatch.setattr(sys, "argv", ["run_api_server.py", "--host", "127.0.0.1"])
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setenv("PYTHONPATH", "")
    runpy.run_path(str(root / "run_api_server.py"), run_name="__main__")
    assert calls[0][0] == "start"
    assert calls[0][1] == [sys.executable, "-m", "app.services.engine_job_worker"]
    assert calls[0][2]["cwd"] == root / "backend"
    assert calls[1][0:2] == ("api", "app.main:app")
    assert calls[1][2]["host"] == "127.0.0.1"
    assert calls[1][2]["port"] == 8000
    assert calls[2:] == [("terminate",), ("wait", 10)]
