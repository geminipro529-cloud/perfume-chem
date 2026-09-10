from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from app.schemas.solforge_workbench import (
    AUTHORITY_FLAGS_FALSE,
    SolForgeWorkbenchDesignRequestV1,
)
from app.services.solforge_workbench import (
    SolForgeWorkbenchService,
    WorkbenchRuntimeConfig,
    canonical_json_bytes,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "data" / "governance" / "complexity_inventory_catalog_v1.json"
WORKBOOK_NAME = "Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _main_checkout() -> Path | None:
    completed = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    common = Path(completed.stdout.strip()).resolve()
    return common.parent if common.name == ".git" else None


def _authoritative_inventory() -> Path:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    expected = catalog["authority"]["workbook_sha256"]
    catalog_relative = Path(catalog["authority"]["workbook_path"])
    main_checkout = _main_checkout()
    candidates = [
        Path(os.environ["PERFUME_CHEM_V5_INVENTORY"])
        if os.environ.get("PERFUME_CHEM_V5_INVENTORY")
        else None,
        REPO_ROOT / catalog_relative,
        REPO_ROOT / WORKBOOK_NAME,
        main_checkout / catalog_relative if main_checkout else None,
        main_checkout / WORKBOOK_NAME if main_checkout else None,
    ]
    for candidate in candidates:
        if (
            candidate is not None
            and candidate.is_file()
            and not candidate.is_symlink()
            and _sha256_file(candidate) == expected
        ):
            return candidate.resolve()
    pytest.skip("exact V5 inventory authority is unavailable for the real-CLI smoke")


def _engine_python() -> Path:
    main_checkout = _main_checkout()
    candidates = [
        Path(os.environ["SOLFORGE_ENGINE_PYTHON"])
        if os.environ.get("SOLFORGE_ENGINE_PYTHON")
        else None,
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
        REPO_ROOT / ".venv" / "bin" / "python",
        main_checkout / ".venv" / "Scripts" / "python.exe"
        if main_checkout
        else None,
        main_checkout / ".venv" / "bin" / "python" if main_checkout else None,
        Path(sys.executable),
    ]
    for candidate in candidates:
        if candidate is None or not candidate.is_file():
            continue
        completed = subprocess.run(
            [str(candidate), "-c", "import openpyxl"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        )
        if completed.returncode == 0:
            return candidate.resolve()
    pytest.skip("a local interpreter with the root SolForge dependencies is unavailable")


def _closed_request(inventory_path: Path) -> SolForgeWorkbenchDesignRequestV1:
    inventory_sha256 = _sha256_file(inventory_path)
    case = {
        "schema_version": "solforge_case_v1",
        "state": "READY",
        "case_id": "WORKBENCH-REAL-CLI-NO-CHANGE",
        "target_identity": "austere iris with deliberate negative space",
        "ideal_architecture": {"heart": ["iris"], "space": ["negative space"]},
        "current_inventory_build": {"materials": {}},
        "inventory_path": str(inventory_path),
        "inventory_sha256": inventory_sha256,
        "formula_sha256": "b" * 64,
        "dose_receipt_sha256": "c" * 64,
        "constraints": ["select no more than one nonredundant intervention"],
        "criterion": "DEPTH",
        "forbidden_claims": ["liking", "safety", "release"],
        "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
    }
    hypotheses = {
        "schema_version": "sol_hypothesis_set_v1",
        "case_sha256": hashlib.sha256(canonical_json_bytes(case)).hexdigest(),
        "model_identity": "deterministic real-CLI smoke fixture",
        "reasoning_setting": "no model invocation",
        "prompt_sha256": "a" * 64,
        "input_sha256": "b" * 64,
        "output_sha256": "c" * 64,
        "hypotheses": [],
        "uncertainty": "no nonredundant delta is supplied",
        "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
    }
    return SolForgeWorkbenchDesignRequestV1(
        schema_version="solforge_workbench_design_request_v1",
        case=case,
        hypotheses=hypotheses,
    )


@pytest.mark.asyncio
async def test_real_cli_compiles_exact_inventory_bound_no_change_case():
    inventory_path = _authoritative_inventory()
    engine_python = _engine_python()
    short_root = REPO_ROOT / "output" / "wb-real-cli-tests"
    short_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="r-", dir=short_root) as temporary:
        artifact_root = Path(temporary).resolve()
        config = WorkbenchRuntimeConfig(
            engine_python=engine_python,
            project_root=REPO_ROOT.resolve(),
            script_path=(REPO_ROOT / "scripts" / "intervention_recommend.py").resolve(),
            inventory_path=inventory_path,
            artifact_root=artifact_root,
            timeout_seconds=90,
            max_runs=2,
            max_artifact_bytes=16 * 1024 * 1024,
            max_record_bytes=4 * 1024 * 1024,
            max_concurrent_runs=1,
        )
        response = await SolForgeWorkbenchService(config).run_design(
            _closed_request(inventory_path)
        )

        assert response.stage == "DECIDED"
        assert response.decision == "NO_CHANGE"
        assert response.admitted_module_ids == ("architectural-delta-engine",)
        assert response.arms == ()
        assert response.artifact_download_available is False
        assert response.authority_flags == AUTHORITY_FLAGS_FALSE
        assert not any(response.authority_flags.values())
        assert (artifact_root / response.run_id / "MANIFEST.json").is_file()
