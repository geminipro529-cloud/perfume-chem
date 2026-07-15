from importlib.metadata import version


def test_backend_imports_installed_canonical_engine_with_runtime_data():
    from engine.data_spine.loader import DEFAULT_DATA_DIR
    from engine.workbench import PerfumeWorkbench

    assert version("perfume-chem-engine") == "0.1.0"
    assert PerfumeWorkbench.__module__ == "engine.workbench"
    assert (DEFAULT_DATA_DIR / "H.yaml").is_file()
