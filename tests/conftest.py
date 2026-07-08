import sys
import os
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault(
    "PERFUME_PIPELINE_AUDIT_PATH",
    str(Path(tempfile.gettempdir()) / "perfume_chem_pytest_pipeline_audit.jsonl"),
)
