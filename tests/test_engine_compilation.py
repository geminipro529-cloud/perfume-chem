from __future__ import annotations

import compileall
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_every_engine_module_byte_compiles():
    assert compileall.compile_dir(PROJECT_ROOT / "engine", quiet=1)


def test_release_pipeline_import_does_not_eagerly_load_scipy():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import scripts.formula_release_gate; "
                "print(any(name == 'scipy' or name.startswith('scipy.') "
                "for name in sys.modules))"
            ),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.stdout.strip() == "False"


def test_optimizer_oav_exports_remain_available_on_demand():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import engine.optimizer as optimizer; "
                "assert optimizer.OAVObjective.__name__ == 'OAVObjective'; "
                "assert callable(optimizer.score_formula_oav); "
                "assert callable(optimizer.differential_evolution_oav); "
                "print('ok')"
            ),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.stdout.strip() == "ok"
