from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest
import yaml

from scripts.scientific_truth_inventory import build_inventory, write_inventory


@pytest.fixture
def miniature_repo(tmp_path: Path) -> Path:
    (tmp_path / "data" / "materials").mkdir(parents=True)
    (tmp_path / "data" / "knowledge_graph").mkdir(parents=True)
    (tmp_path / "engine").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "docs" / "verification" / "b0").mkdir(parents=True)
    (tmp_path / "verification_runs").mkdir()
    (tmp_path / "tests" / "fixtures").mkdir(parents=True)

    material = [
        {
            "canonical_name": "Test Molecule",
            "mw_g_mol": 123.4,
            "density_25c_g_ml": None,
            "odt_air_ppb": 0.7,
            "provenance": {
                "mw_g_mol": "Primary:table-2",
                "odt_air_ppb": "legacy-heuristic",
            },
        }
    ]
    (tmp_path / "data" / "materials" / "T.yaml").write_text(
        yaml.safe_dump(material, sort_keys=False),
        encoding="utf-8",
    )
    (tmp_path / "data" / "knowledge_graph" / "pairing_rules.json").write_text(
        json.dumps(
            [
                {
                    "subject": "Test Molecule",
                    "relation": "synergizes",
                    "object": "Second Molecule",
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "engine" / "odor_thresholds.py").write_text(
        "ODT_DATA = {'Test Molecule': {'odt_air': 0.7, 'vfy': 'UNVERIFIED'}}\n"
        "MIXTURE_SUPPRESSION_FACTOR = 5.0\n"
        "def lookup():\n"
        "    return ODT_DATA\n",
        encoding="utf-8",
    )
    (tmp_path / "engine" / "__pycache__").mkdir()
    (tmp_path / "engine" / "__pycache__" / "odor_thresholds.pyc").write_bytes(b"cache")
    (tmp_path / "verification_runs" / "science_audit.json").write_text(
        '{"status":"baseline"}',
        encoding="utf-8",
    )
    (tmp_path / "verification_runs" / "wheel-smoke").mkdir()
    (tmp_path / "verification_runs" / "wheel-smoke" / "science_audit.py").write_text(
        "COPIED_CONSTANT = 1\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "fixtures" / "golden_formula_cases.json").write_text(
        "[]",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "test_scientific_assumption.py").write_text(
        "EXPECTED_THRESHOLD_PPB = 0.7\n"
        "def test_threshold_assumption():\n"
        "    assert EXPECTED_THRESHOLD_PPB == 0.7\n",
        encoding="utf-8",
    )
    (tmp_path / "scripts" / "scientific_truth_inventory.py").write_text(
        "INVENTORY_IMPLEMENTATION_SENTINEL = 1\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "test_scientific_truth_inventory.py").write_text(
        "INVENTORY_TEST_SENTINEL = 1\n",
        encoding="utf-8",
    )
    for name in (
        "scientific_truth_baseline.md",
        "scientific_truth_baseline.json",
        "scientific_truth_inventory.json.gz",
    ):
        (tmp_path / "docs" / "verification" / "b0" / name).write_bytes(b"generated")
    (tmp_path / ".env").write_text("SECRET_VALUE=must-not-be-read", encoding="utf-8")
    return tmp_path


def test_inventory_is_deterministic_scoped_and_claim_aware(miniature_repo: Path) -> None:
    first = build_inventory(miniature_repo)
    second = build_inventory(miniature_repo)

    assert first == second
    assert first["schema_version"] == "scientific-truth-inventory-v1"
    assert all(".env" not in item["path"] for item in first["source_digests"])
    assert all("__pycache__" not in item["path"] for item in first["source_digests"])
    assert all("wheel-smoke" not in item["path"] for item in first["source_digests"])
    assert {
        "scripts/scientific_truth_inventory.py",
        "tests/test_scientific_truth_inventory.py",
        "docs/verification/b0/scientific_truth_baseline.md",
        "docs/verification/b0/scientific_truth_baseline.json",
        "docs/verification/b0/scientific_truth_inventory.json.gz",
    }.isdisjoint(item["path"] for item in first["source_digests"])
    assert "INVENTORY_IMPLEMENTATION_SENTINEL" not in {
        item["name"] for item in first["code_constants"]
    }
    assert "INVENTORY_TEST_SENTINEL" not in {
        item["name"] for item in first["code_constants"]
    }
    assert first["summary"]["material_count"] == 1
    assert first["summary"]["material_property_observation_count"] == 3
    assert first["summary"]["knowledge_rule_count"] == 1

    observations = {
        item["property_type"]: item for item in first["material_property_observations"]
    }
    assert observations["mw_g_mol"]["current_value"] == 123.4
    assert observations["mw_g_mol"]["canonical_unit"] == "g/mol"
    assert observations["mw_g_mol"]["source_locator"] == "Primary:table-2"
    assert observations["density_25c_g_ml"]["authority_label"] == "UNKNOWN"
    assert observations["odt_air_ppb"]["authority_label"] == "LEGACY_HEURISTIC"
    assert "threshold_screening" in observations["odt_air_ppb"]["claim_impacts"]
    assert observations["odt_air_ppb"]["affects_blocking_gate"] is True

    constants = {item["name"]: item for item in first["code_constants"]}
    assert constants["MIXTURE_SUPPRESSION_FACTOR"]["current_value"] == 5.0
    assert constants["ODT_DATA"]["value_shape"] == {"kind": "dict", "length": 1}
    assert constants["ODT_DATA"]["consumers"] == ["engine/odor_thresholds.py:4"]
    assert constants["EXPECTED_THRESHOLD_PPB"]["runtime_path"] == (
        "tests/test_scientific_assumption.py"
    )
    assert any(
        item["path"] == "tests/test_scientific_assumption.py"
        for item in first["source_digests"]
    )

    assert first["legacy_fixtures"]["science_audit"]["path"] == (
        "verification_runs/science_audit.json"
    )
    assert first["legacy_fixtures"]["golden_formula_cases"]["path"] == (
        "tests/fixtures/golden_formula_cases.json"
    )


def test_inventory_rejects_non_repository_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="data/materials"):
        build_inventory(tmp_path)


def test_write_inventory_round_trips_deterministic_gzip(
    miniature_repo: Path,
    tmp_path: Path,
) -> None:
    report = build_inventory(miniature_repo)
    output = tmp_path / "scientific_truth_inventory.json.gz"

    write_inventory(report, output)
    first_bytes = output.read_bytes()
    write_inventory(report, output)

    assert output.read_bytes() == first_bytes
    with gzip.open(output, "rt", encoding="utf-8") as handle:
        assert json.load(handle) == report
