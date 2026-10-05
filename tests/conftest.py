import os
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTEST_TEMP_ROOT = PROJECT_ROOT / "output" / "pytest-temp"
PYTEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(PYTEST_TEMP_ROOT)
os.environ["TMP"] = str(PYTEST_TEMP_ROOT)
tempfile.tempdir = str(PYTEST_TEMP_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_EXPLICIT_AUDIT_PATH = os.environ.get("PERFUME_PIPELINE_AUDIT_PATH")
_EXPLICIT_COMPLETION_PATH = os.environ.get("PERFUME_INVENTORY_COMPLETION_PATH")
_EXPLICIT_ADDITION_PATH = os.environ.get("PERFUME_PERSONAL_INVENTORY_ADDITION_PATH")
_SESSION_SCRATCH = None
os.environ.setdefault(
    "PERFUME_PIPELINE_AUDIT_PATH",
    str(Path(tempfile.gettempdir()) / "perfume_chem_pytest_pipeline_audit.jsonl"),
)
os.environ.setdefault(
    "PERFUME_INVENTORY_COMPLETION_PATH",
    str(Path(tempfile.gettempdir()) / "perfume_chem_pytest_inventory_completions.jsonl"),
)
os.environ.setdefault(
    "PERFUME_PERSONAL_INVENTORY_ADDITION_PATH",
    str(Path(tempfile.gettempdir()) / "perfume_chem_pytest_inventory_additions.jsonl"),
)


@pytest.fixture(scope="session", autouse=True)
def managed_test_scratch(tmp_path_factory):
    """Put raw tempfile output under pytest's success/failure retention policy."""
    global _SESSION_SCRATCH
    session_temp = tmp_path_factory.getbasetemp()
    _SESSION_SCRATCH = session_temp
    previous = {
        key: os.environ.get(key)
        for key in (
            "TEMP",
            "TMP",
            "PERFUME_PIPELINE_AUDIT_PATH",
            "PERFUME_INVENTORY_COMPLETION_PATH",
            "PERFUME_PERSONAL_INVENTORY_ADDITION_PATH",
        )
    }
    previous_tempdir = tempfile.tempdir
    os.environ["TEMP"] = os.environ["TMP"] = str(session_temp)
    tempfile.tempdir = str(session_temp)
    if _EXPLICIT_AUDIT_PATH is None:
        os.environ["PERFUME_PIPELINE_AUDIT_PATH"] = str(session_temp / "pipeline_audit.jsonl")
    if _EXPLICIT_COMPLETION_PATH is None:
        os.environ["PERFUME_INVENTORY_COMPLETION_PATH"] = str(
            session_temp / "inventory_completions.jsonl"
        )
    if _EXPLICIT_ADDITION_PATH is None:
        os.environ["PERFUME_PERSONAL_INVENTORY_ADDITION_PATH"] = str(
            session_temp / "inventory_additions.jsonl"
        )
    try:
        yield
    finally:
        tempfile.tempdir = previous_tempdir
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Preserve teardown failures; remove only this session's successful scratch."""
    if exitstatus != 0 or _SESSION_SCRATCH is None:
        return
    scratch = _SESSION_SCRATCH.resolve()
    if scratch != _SESSION_SCRATCH.absolute():
        return
    if scratch == PYTEST_TEMP_ROOT.resolve() or not scratch.is_relative_to(
        PYTEST_TEMP_ROOT.resolve()
    ):
        return
    try:
        shutil.rmtree(scratch)
    except OSError as exc:
        warnings.warn(
            pytest.PytestWarning(f"Test scratch retained at {scratch}: {exc}"), stacklevel=1
        )
