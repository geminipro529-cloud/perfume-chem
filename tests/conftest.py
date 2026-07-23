import os
import sys
import tempfile
from pathlib import Path

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
