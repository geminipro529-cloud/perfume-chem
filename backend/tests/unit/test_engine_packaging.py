import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_backend_imports_installed_canonical_engine_with_runtime_data():
    from engine.data_spine.loader import DEFAULT_DATA_DIR
    from engine.workbench import PerfumeWorkbench

    assert version("perfume-chem-engine") == "0.1.0"
    assert PerfumeWorkbench.__module__ == "engine.workbench"
    assert (DEFAULT_DATA_DIR / "H.yaml").is_file()


def test_built_wheel_installs_runtime_material_data_without_source_tree(tmp_path):
    wheel_dir = tmp_path / "wheel"
    target_dir = tmp_path / "target"
    wheel_dir.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheel_dir),
            str(REPO_ROOT),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(wheel_dir.glob("perfume_chem_engine-*.whl"))
    with ZipFile(wheel) as archive:
        assert "data/materials/H.yaml" in archive.namelist()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(target_dir),
            str(wheel),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    probe = (
        "import sys; "
        f"sys.path.insert(0, {str(target_dir)!r}); "
        "from engine.data_spine.loader import DEFAULT_DATA_DIR; "
        "assert (DEFAULT_DATA_DIR / 'H.yaml').is_file(), DEFAULT_DATA_DIR"
    )
    subprocess.run(
        [sys.executable, "-I", "-c", probe],
        check=True,
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
