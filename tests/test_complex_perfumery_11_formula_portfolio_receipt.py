from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

from engine.calibration.hashing import stable_json_hash

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DIR = ROOT / "incoming_review" / "chatgpt" / "20260819T134159Z-formula-portfolio-6a79b172"
SOURCE_PATH = CAPTURE_DIR / "Complex_Perfumery_11_Formula_Portfolio.json"
CAPTURE_MANIFEST_PATH = CAPTURE_DIR / "capture_manifest.json"
RECEIPT_PATH = (
    ROOT
    / "data"
    / "governance"
    / "complex_perfumery_11_formula_portfolio_package_receipt_20260819.json"
)
SUCCESSOR_PATH = (
    ROOT
    / "incoming_review"
    / "chatgpt"
    / "20260818T013100+0700-exact-decimal-successor-6a7992db"
    / "expanded"
    / "Perfume_Chem_V19_V20_Exact_Decimal_Formula_Artifact_Successor_2026-08-17_v2"
    / "V19_V20_EXACT_DECIMAL_FORMULA_ARTIFACT_SUCCESSOR_PACK.json"
)

FORMULA_IDS = [
    "LHOMME",
    "LANUIT",
    "DHI12",
    "PR_E07",
    "PR_E01",
    "AHS",
    "EB",
    "EE",
    "ELIXIR",
    "BDCP",
    "DHP25",
]
AUTHORITY_FALSE = {
    "factory_formula",
    "canonical_formula",
    "physical_batch",
    "bottle_addition",
    "physical_liking",
    "hedonic_proof",
    "commercial_similarity",
    "measured_headspace",
    "strict_empirical_OAV",
    "stability",
    "safety",
    "skin_use",
    "inventory_mutation",
    "procurement_authority",
    "compounding_authority",
    "installation",
    "publication",
    "release",
}


def test_exact_portfolio_is_quarantined_candidate_ancestry_not_canonical_formula_truth() -> None:
    """Preserve the exact 11-formula source while withholding every execution authority."""

    manifest = json.loads(CAPTURE_MANIFEST_PATH.read_text(encoding="utf-8"))
    unhashed = deepcopy(manifest)
    declared_manifest_hash = unhashed.pop("receipt_sha256")
    assert stable_json_hash(unhashed) == declared_manifest_hash

    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    unhashed_receipt = deepcopy(receipt)
    declared_receipt_hash = unhashed_receipt.pop("receipt_sha256")
    assert stable_json_hash(unhashed_receipt) == declared_receipt_hash
    assert receipt["schema_version"] == "external_artifact_receipt_v1"
    assert receipt["artifact"]["byte_size"] == SOURCE_PATH.stat().st_size
    assert receipt["artifact"]["sha256"] == (
        "869757d6de9cca844475c9437b2e0de7d87596ba69cb2a0f1c568d205612e9f6"
    )
    assert receipt["artifact"]["json_parse_valid"] is True
    assert not any(receipt["authority"].values())
    assert not any(
        receipt["admission"][field]
        for field in (
            "b1_promotion_allowed",
            "canonical_import_allowed",
            "formula_projection_allowed",
            "execution_allowed",
        )
    )

    assert SOURCE_PATH.stat().st_size == 2_617_388
    assert hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest() == (
        "869757d6de9cca844475c9437b2e0de7d87596ba69cb2a0f1c568d205612e9f6"
    )
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    assert list(source["portfolio"]) == FORMULA_IDS
    assert source["source_boundary"] == (
        "Evidence-weighted computational reconstructions; not manufacturer formulas or empirical "
        "similarity claims."
    )
    assert set(source["authority_false"]) == AUTHORITY_FALSE
    assert sum(len(item["current_build"]) for item in source["portfolio"].values()) == 771
    assert sum(len(item["target_ideal"]) for item in source["portfolio"].values()) == 788
    assert sum(len(item["missing"]) for item in source["portfolio"].values()) == 19
    assert sum(len(item["tests"]) for item in source["portfolio"].values()) == 55
    assert sum(len(item["gates"]) for item in source["portfolio"].values()) == 187
    assert Counter(
        gate["state"] for item in source["portfolio"].values() for gate in item["gates"]
    ) == Counter({"HOLD": 67, "PASS": 54, "CONDITIONAL": 44, "NOT_RUN": 22})
    assert len(source["pairwise_diagnostics"]) == 55
    assert all(
        item["state"] == "COMPUTATIONAL RECONSTRUCTION CANDIDATE / PHYSICAL HOLD"
        for item in source["portfolio"].values()
    )
    assert source["validation"]["overall"] == "PASS"
    assert len(source["validation"]["checks"]) == 69
    assert all(check["state"] == "PASS" for check in source["validation"]["checks"])

    summary = receipt["evidence_summary"]
    assert summary["classification"] == (
        "EXACT_ELEVEN_FORMULA_COMPUTATIONAL_PORTFOLIO_DISTINCT_CANDIDATE_LINEAGE_"
        "PHYSICAL_ANALYTICAL_AND_RELEASE_HOLD"
    )
    assert summary["formula_candidates"] == 11
    assert summary["successor_overlap_formula_ids"] == 9
    assert summary["portfolio_only_formula_ids"] == ["PR_E07", "PR_E01"]
    assert summary["overlap_current_hash_matches"] == 0
    assert summary["overlap_exact_material_part_matches"] == 0
    assert summary["native_formula_installation_performed"] is False
    assert summary["native_physics_change_required"] is False
    assert summary["promotion_allowed"] is False


def test_portfolio_and_exact_decimal_successor_are_distinct_noninterchangeable_lineages() -> None:
    """Prevent nine overlapping names from being mistaken for byte- or formula-equivalent rows."""

    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    successor = json.loads(SUCCESSOR_PATH.read_text(encoding="utf-8"))
    successor_ids = [entry["perfume_id"] for entry in successor["formula_register"]]
    overlap = [formula_id for formula_id in FORMULA_IDS if formula_id in successor_ids]
    assert len(overlap) == 9
    assert [formula_id for formula_id in FORMULA_IDS if formula_id not in successor_ids] == [
        "PR_E07",
        "PR_E01",
    ]

    register = {entry["perfume_id"]: entry for entry in successor["formula_register"]}
    assert all(
        source["portfolio"][formula_id]["current_hash"]
        not in {
            register[formula_id]["parent_formula_hash"],
            register[formula_id]["successor_formula_hash"],
        }
        for formula_id in overlap
    )

    exact_material_part_matches = 0
    for formula_id in overlap:
        source_rows = {
            (row["material"], f"{row['parts_per_1000']:.4f}")
            for row in source["portfolio"][formula_id]["current_build"]
        }
        successor_rows = {
            (row["material"], row["parts_per_1000_decimal"])
            for row in successor["current_builds_exact_decimal"][formula_id]["rows"]
        }
        exact_material_part_matches += len(source_rows & successor_rows)
    assert exact_material_part_matches == 0
