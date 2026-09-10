from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/benchmarks/solforge/rebuild_science_v1/manifest.json"


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_hash_binds_every_provider_free_component() -> None:
    payload = _manifest()
    assert payload["schema_version"] == "solforge_rebuild_science_manifest_v1"
    for binding in payload["component_bindings"]:
        path = ROOT / binding["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding["sha256"]
    assert set(payload["authority"].values()) == {False}


def test_all_23_systems_have_endpoints_and_a_critical_failure() -> None:
    systems = _manifest()["system_families"]
    assert [item["id"] for item in systems] == [f"G{i:02d}" for i in range(1, 24)]
    assert len({item["name"] for item in systems}) == 23
    assert all(len(item["primary_endpoints"]) >= 3 for item in systems)
    assert all(item["critical_failure"] for item in systems)


def test_floral_restoration_expands_subjects_without_generating_formulas() -> None:
    floral = _manifest()["floral_restoration"]
    assert floral["prior_canonical_state"] == "BLOCKED_EXTERNAL_FOUNDATION"
    assert floral["current_rebuild_state"] == "NONRUNTIME_RESTORATION_CORPUS_READY"
    assert len(floral["prior_subject_families"]) == 9
    assert {
        "magnolia",
        "mimosa",
        "ylang_ylang",
        "orange_blossom_neroli",
        "violet_flower",
        "violet_leaf_primary",
    }.issubset(floral["required_subject_expansions"])
    assert floral["combination_orders_represented"] == [1, 2, 3, 4]
    assert floral["automatic_formula_generation"] is False
    assert floral["claim_ceiling"].endswith("EXPERIMENT_DESIGN_ONLY")


def test_reference_perfumes_are_hypotheses_not_sensory_truth() -> None:
    references = _manifest()["reference_architectures"]
    assert {item["id"] for item in references} == {
        "DHP_2025_WOOD_IRIS",
        "AMOUAGE_OPUS_V",
        "AMOUAGE_REFLECTION_MAN",
        "AMOUAGE_INTERLUDE_MAN",
        "AMOUAGE_PURPOSE",
    }
    assert all(item["source_type"] == "OFFICIAL_PRODUCT_DESCRIPTION" for item in references)
    assert all(item["evidence_class"] == "HYPOTHESIS_ONLY" for item in references)
    assert all(item["source_url"].startswith("https://") for item in references)
    assert all("required_observations" in item for item in references)


def test_model_classes_cannot_be_collapsed_into_a_three_dimensional_beauty_score() -> None:
    classes = _manifest()["model_class_boundaries"]
    assert len(classes) == 8
    assert len({item["class"] for item in classes}) == 8
    forbidden = " ".join(item["cannot_support"] for item in classes).casefold()
    assert "beauty" in forbidden
    assert "liking" in forbidden
    assert "sensory success" in forbidden
