import os
import sys
import tempfile
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

os.environ.setdefault(
    "PERFUME_PIPELINE_AUDIT_PATH",
    str(Path(tempfile.gettempdir()) / "perfume_chem_pytest_pipeline_audit.jsonl"),
)

PERFUMERY_KB_PATH = PROJECT_ROOT / "data" / "perfumery_kb.db"

# Source stores the KB migration reads. If the DB is missing or older than any
# of these, it is regenerated so knowledge tests run against source truth.
_KB_SOURCE_GLOBS = (
    "data/materials/*.yaml",
    "data/materials/_sources/*",
    "data/knowledge_graph/*.json",
    "inventory.txt",
    "engine/kb_migrate.py",
    "engine/ingredient_intelligence.py",
    "engine/odor_thresholds.py",
    "engine/knowledge/pyramid_targets.py",
    "engine/families/registry.py",
    "engine/temporal_graph.py",
    "engine/hedonic_model.py",
)


def _kb_needs_rebuild(db: Path) -> bool:
    if not db.exists():
        return True
    newest = db.stat().st_mtime
    for pattern in _KB_SOURCE_GLOBS:
        for source in PROJECT_ROOT.glob(pattern):
            try:
                newest = max(newest, source.stat().st_mtime)
            except OSError:
                continue
            if newest > db.stat().st_mtime:
                return True
    return False


@pytest.fixture(scope="session", autouse=True)
def _provision_perfumery_kb() -> None:
    """Ensure ``data/perfumery_kb.db`` exists and is newer than its sources.

    The SQLite knowledge base is a gitignored generated artifact (``*.db``);
    knowledge tests read it live. Build it from ``engine.kb_migrate.migrate``
    when missing or stale so fresh clones can run the knowledge tests.
    """
    if _kb_needs_rebuild(PERFUMERY_KB_PATH):
        from engine.kb_migrate import migrate

        migrate(str(PERFUMERY_KB_PATH))
    yield


