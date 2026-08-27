import os
import sys
import tempfile
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTEST_TEMP_ROOT = PROJECT_ROOT / "output" / "t" / str(os.getpid())
PYTEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(PYTEST_TEMP_ROOT)
os.environ["TMP"] = str(PYTEST_TEMP_ROOT)
tempfile.tempdir = str(PYTEST_TEMP_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Editable backend installs also expose ``backend/tests`` as a top-level
# ``tests`` package.  Pin this run to the repository's root test namespace so
# cross-test fixture imports cannot silently resolve to that unrelated package.
ROOT_TESTS = Path(__file__).resolve().parent
tests_package = types.ModuleType("tests")
tests_package.__path__ = [str(ROOT_TESTS)]
tests_package.__package__ = "tests"
sys.modules["tests"] = tests_package

os.environ.setdefault(
    "PERFUME_PIPELINE_AUDIT_PATH",
    str(Path(tempfile.gettempdir()) / "perfume_chem_pytest_pipeline_audit.jsonl"),
)


@pytest.fixture(scope="session")
def generated_knowledge_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a disposable KB from tracked sources for query validation only."""

    from engine.kb_migrate import migrate

    database = tmp_path_factory.mktemp("generated-kb") / "perfumery_kb.db"
    previous_directory = Path.cwd()
    try:
        os.chdir(PROJECT_ROOT)
        migrate(str(database))
    finally:
        os.chdir(previous_directory)
    return database
