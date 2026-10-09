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


@pytest.fixture(scope="session")
def built_perfumery_kb(tmp_path_factory) -> Path:
    """Build the knowledge base from this checkout's sources, once per session.

    ``*.db`` is gitignored, so a clean checkout has no ``data/perfumery_kb.db``.
    The build goes to session scratch; the repository KB and its tracked
    ``-wal``/``-shm`` files are never read or written.
    """
    from engine.kb_migrate import migrate

    target = tmp_path_factory.mktemp("perfumery_kb") / "perfumery_kb.db"
    return Path(migrate(str(target)))


@pytest.fixture
def perfumery_kb(built_perfumery_kb, monkeypatch) -> Path:
    """Point the read-only KB query modules at the session-built database."""
    from engine import kb_rules_api, knowledge_base, property_estimator

    monkeypatch.setattr(knowledge_base, "_DB_PATH", built_perfumery_kb)
    monkeypatch.setattr(kb_rules_api, "_DB_PATH", built_perfumery_kb)
    monkeypatch.setattr(property_estimator, "_KB_PATH", built_perfumery_kb)
    return built_perfumery_kb


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


@pytest.fixture(scope="module", autouse=True)
def historical_august_inventory_inputs(request, tmp_path_factory):
    """Replay four immutable August audits without claiming they describe today."""
    names = {
        "test_inventory_v5_direct_stock_assertion_reconciliation",
        "test_inventory_v5_experiment_readiness_closure_evidence_audit",
        "test_inventory_v5_experiment_readiness_closure_queue",
        "test_inventory_v5_experiment_readiness_remaining_evidence_audit",
    }
    if request.module.__name__.split(".")[-1] not in names:
        yield
        return
    from tests.historical_snapshots import copy_august_inventory_snapshot

    root = tmp_path_factory.mktemp("inventory-august-snapshot")
    sources = [
        value for name, value in vars(request.module).items()
        if name.endswith("_PATH") and isinstance(value, Path)
    ]
    sources.extend([
        PROJECT_ROOT / "data/governance/inventory_v5_current_stock_snapshot.json",
        PROJECT_ROOT / "data/materials/_sources/perfumersworld_stock.parsed.json",
        PROJECT_ROOT / "formulas/demachy_redux/DHC_A_BottleA_Lemon_Extension.md",
    ])
    copy_august_inventory_snapshot(root, sources)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(request.module, "ROOT", root)
        for name, value in vars(request.module).items():
            if name.endswith("_PATH") and isinstance(value, Path):
                patch.setattr(request.module, name, root / value.relative_to(PROJECT_ROOT))
        yield


@pytest.fixture(autouse=True)
def gin_algorithm_stock_contracts(request, monkeypatch):
    """Only algorithm fixtures use the explicit September stock-contract set."""
    if request.module.__name__.split(".")[-1] not in {
        "test_evidence_design_portfolio", "test_global_design_cli"
    }:
        return
    from engine import inventory_parser as inventory
    from tests.historical_snapshots import gin_stock_contract_fixture

    materialized = gin_stock_contract_fixture()
    monkeypatch.setattr(inventory, "materialize_current_inventory", lambda *a, **k: materialized)


@pytest.fixture(scope="module", autouse=True)
def historical_checkpoint_inputs(request, tmp_path_factory):
    """Only the frozen CP3-8 contract tests replay September's original inputs.

    The production default still rejects October drift. See the independent
    current-input regression; this fixture never changes canonical files.
    """
    names = {
        "test_r5_checkpoint3_readiness", "test_r6_aimi_checkpoint4_readiness",
        "test_r6_checkpoint5_readiness", "test_r6_checkpoint6_readiness",
        "test_r6_checkpoint7_readiness", "test_r6_checkpoint8_readiness",
    }
    if request.module.__name__.split(".")[-1] not in names:
        yield
        return
    import functools
    import importlib
    from dataclasses import replace

    import engine.inventory_parser as inventory
    from tests.historical_snapshots import copy_checkpoint_snapshot

    root = tmp_path_factory.mktemp("checkpoint-september-snapshot")
    inventory_path = copy_checkpoint_snapshot(root)
    base = inventory.materialize_current_inventory(
        apply_user_overlay=False, apply_user_completions=False
    )
    original_inventory = inventory._apply_current_user_inventory_overlay(
        base, inventory.load_current_user_inventory_overlay(
            inventory.R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_PATH
        )
    )
    # The private merge helper always stamps the current head. The fixture
    # explicitly applied the verified historical overlay, so retain its own
    # pin rather than the unrelated October head label.
    original_inventory = replace(
        original_inventory,
        overlay_sha256=inventory.R5_REMAINING_STOCK_FORMS_V3_USER_INVENTORY_OVERLAY_SHA256,
    )
    assert original_inventory.overlay_sha256 == (
        "0bccf890ee05487b20daca94d02c65103c2a22ed4c6435ba8cb311cd041575fb"
    )
    modules = [importlib.import_module(f"engine.experiments.checkpoint{i}_readiness")
               for i in range(3, 9)]
    replacements = {}
    for module in modules[:3]:
        for name, function in vars(module).items():
            if name.startswith("evaluate_r") and function.__module__ == module.__name__:
                replacements[function] = functools.partial(
                    function, inventory_text_path=inventory_path, inventory=original_inventory
                )
    with pytest.MonkeyPatch.context() as patch:
        for module in modules:
            patch.setattr(module, "REPOSITORY_ROOT", root)
            for name, function in list(vars(module).items()):
                if callable(function) and function in replacements:
                    patch.setattr(module, name, replacements[function])
        for name, function in list(vars(request.module).items()):
            if callable(function) and function in replacements:
                patch.setattr(request.module, name, replacements[function])
        if hasattr(request.module, "DEFAULT_INVENTORY_TEXT_PATH"):
            patch.setattr(request.module, "DEFAULT_INVENTORY_TEXT_PATH", inventory_path)
        yield
