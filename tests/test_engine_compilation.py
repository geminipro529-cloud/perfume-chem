from __future__ import annotations

import compileall
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_every_engine_module_byte_compiles():
    assert compileall.compile_dir(PROJECT_ROOT / "engine", quiet=1)
