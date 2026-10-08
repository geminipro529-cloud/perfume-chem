from __future__ import annotations

from pathlib import Path

import pytest

from app.services import engine_jobs
from app.services.engine_job_registry import implementation_paths


def test_review_manifest_bytes_participate_in_reference_fingerprint(monkeypatch, tmp_path):
    relative = "data/formulation_knowledge/source_reviews_v1.json"
    assert relative in engine_jobs._REFERENCE_PATHS
    source = tmp_path / relative
    source.parent.mkdir(parents=True)
    source.write_text('{"review": "first"}', encoding="utf-8")
    monkeypatch.setattr(engine_jobs, "REPOSITORY_ROOT", tmp_path)
    before = engine_jobs._bundle_fingerprint(engine_jobs._REFERENCE_PATHS)
    source.write_text('{"review": "changed"}', encoding="utf-8")
    after = engine_jobs._bundle_fingerprint(engine_jobs._REFERENCE_PATHS)
    assert before != after


def test_successor_registry_and_review_implementation_are_bound():
    assert "data/governance/commercial_reference_registry_v2.json" in engine_jobs._CAPABILITY_PATHS
    assert "engine/formulation_intelligence/source_review.py" in engine_jobs._CAPABILITY_PATHS
    paths = {Path(path).as_posix() for path in implementation_paths("REFERENCE_PANEL_EVALUATION")}
    assert any(path.endswith("data/governance/commercial_reference_registry_v2.json") for path in paths)
    assert "data/governance/commercial_reference_registry_v3.json" in engine_jobs._CAPABILITY_PATHS
    assert any(path.endswith("data/governance/commercial_reference_registry_v3.json") for path in paths)


def test_review_drift_changes_full_job_identity_not_the_data_command(monkeypatch, tmp_path):
    payload = {
        "target_snapshot_id": "unchanged-design",
        "target_snapshot_sha256": "1" * 64,
        "request_interpretation_sha256": "2" * 64,
        "reference_panel_id": "global-lavender-amber-2026-v2",
        "reference_panel_sha256": "3" * 64,
        "comparison_evidence": "DOCUMENT_ONLY",
        "observation_record_ids": [],
        "seed": 17,
        "as_of_date": "2026-10-06",
    }
    review_path = tmp_path / "data/formulation_knowledge/source_reviews_v1.json"
    review_path.parent.mkdir(parents=True)
    review_path.write_text('{"review": "first"}', encoding="utf-8")
    monkeypatch.setattr(engine_jobs, "REPOSITORY_ROOT", tmp_path)
    arguments = dict(job_type="REFERENCE_PANEL_EVALUATION", payload=payload,
                     requester="same-scope", idempotency_key="same-command",
                     request_schema_version="lab-engine-job-request-v2")
    before = engine_jobs.build_engine_job_identity(**arguments)
    review_path.write_text('{"review": "changed"}', encoding="utf-8")
    after = engine_jobs.build_engine_job_identity(**arguments)
    assert before["command_sha256"] == after["command_sha256"]
    assert before["reference_bundle_sha256"] != after["reference_bundle_sha256"]
    assert before["job_fingerprint_sha256"] != after["job_fingerprint_sha256"]


def test_construction_library_and_scope_are_bound_to_job_identity(monkeypatch, tmp_path):
    for relative in (
        "data/formulation_knowledge/construction_library_v1.json",
        "data/formulation_knowledge/subtype_research_v1.json",
        "data/formulation_knowledge/subtype_research_v2.json",
        "data/formulation_knowledge/research_coverage_plan_v1.json",
    ):
        assert relative in engine_jobs._REFERENCE_PATHS
        source = tmp_path / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('{"version": "first"}', encoding="utf-8")
        monkeypatch.setattr(engine_jobs, "REPOSITORY_ROOT", tmp_path)
        before = engine_jobs._bundle_fingerprint(engine_jobs._REFERENCE_PATHS)
        source.write_text('{"version": "changed"}', encoding="utf-8")
        assert engine_jobs._bundle_fingerprint(engine_jobs._REFERENCE_PATHS) != before
    for job_type in ("FORMULA_DESIGN", "FORMULA_ANALYSIS"):
        paths = {Path(path).as_posix() for path in implementation_paths(job_type)}
        assert any(path.endswith("engine/formulation_intelligence/construction_library.py") for path in paths)
        assert any(path.endswith("engine/formulation_intelligence/subtype_research.py") for path in paths)


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_architecture_mapping_bytes_change_durable_design_identity(monkeypatch, tmp_path, version):
    relative = f"data/formulation_knowledge/architecture_adapters_v{version}.json"
    assert relative in engine_jobs._research_reference_paths("FORMULA_DESIGN")
    paths = {Path(path).as_posix() for path in implementation_paths("FORMULA_DESIGN")}
    assert any(path.endswith("engine/formulation_intelligence/architecture_bridge.py") for path in paths)
    manifest = tmp_path / relative
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"version": "first"}', encoding="utf-8")
    for filename in (
        "prior_research_corpus_v1.json", "prior_research_corpus_v2.json", "literature_v1.json"
    ):
        original = engine_jobs.REPOSITORY_ROOT / "data/formulation_knowledge" / filename
        (manifest.parent / filename).write_bytes(original.read_bytes())
    monkeypatch.setattr(engine_jobs, "REPOSITORY_ROOT", tmp_path)
    arguments = dict(
        job_type="FORMULA_DESIGN", payload={"message": "A peppery freesia perfume"},
        requester="same-scope", idempotency_key="same-design",
        request_schema_version="lab-engine-job-request-v2",
    )
    before = engine_jobs.build_engine_job_identity(**arguments)
    manifest.write_text('{"version": "changed"}', encoding="utf-8")
    after = engine_jobs.build_engine_job_identity(**arguments)
    assert before["command_sha256"] == after["command_sha256"]
    assert before["reference_bundle_sha256"] != after["reference_bundle_sha256"]
    assert before["job_fingerprint_sha256"] != after["job_fingerprint_sha256"]
    manifest.unlink()
    missing = engine_jobs.build_engine_job_identity(**arguments)
    assert missing["command_sha256"] == before["command_sha256"]
    assert missing["reference_bundle_sha256"] not in {
        before["reference_bundle_sha256"], after["reference_bundle_sha256"],
    }
    assert missing["job_fingerprint_sha256"] not in {
        before["job_fingerprint_sha256"], after["job_fingerprint_sha256"],
    }


def test_v5_operation_and_disposition_implementation_are_in_durable_fingerprints():
    paths = {Path(path).as_posix() for path in implementation_paths("FORMULA_DESIGN")}
    for relative in (
        "engine/formulation_intelligence/architecture_rules_v5.py",
        "engine/formulation_intelligence/subtype_coverage.py",
    ):
        assert relative in engine_jobs._CAPABILITY_PATHS
        assert any(path.endswith(relative) for path in paths)
    assert "data/formulation_knowledge/subtype_implementation_dispositions_v1.json" in engine_jobs._research_reference_paths("FORMULA_DESIGN")


@pytest.mark.parametrize("relative", [
    "data/governance/campaign_reference_chimie_lhomme_v1.json",
    "data/research/campaign_recovery/chimie_lhomme_v1/source_formula.md",
    "data/research/campaign_recovery/chimie_lhomme_v1/source_identity_handoff.md",
    "data/research/campaign_recovery/chimie_lhomme_v1/chat_corrections.json",
])
def test_recovered_campaign_sources_are_fingerprinted(monkeypatch, tmp_path, relative):
    assert relative in engine_jobs._REFERENCE_PATHS
    assert "engine/formulation_intelligence/campaign_reference.py" in engine_jobs._CAPABILITY_PATHS
    source = tmp_path / relative
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("first", encoding="utf-8")
    monkeypatch.setattr(engine_jobs, "REPOSITORY_ROOT", tmp_path)
    before = engine_jobs._bundle_fingerprint(engine_jobs._REFERENCE_PATHS)
    source.write_text("different", encoding="utf-8")
    assert engine_jobs._bundle_fingerprint(engine_jobs._REFERENCE_PATHS) != before
