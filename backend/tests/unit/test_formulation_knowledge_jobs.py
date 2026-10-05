"""Knowledge and original research bytes participate in durable job identity."""

from __future__ import annotations

import json

import pytest

from app.services import engine_jobs
from app.services.engine_job_registry import implementation_paths


def test_knowledge_module_is_bound_to_both_runtime_job_types() -> None:
    for job_type in ("FORMULA_DESIGN", "FORMULA_ANALYSIS"):
        assert any(
            path.name == "literature_knowledge.py" for path in implementation_paths(job_type)
        )


def test_runtime_reference_bundle_contains_pack_census_and_current_documents() -> None:
    paths = engine_jobs._research_reference_paths("FORMULA_DESIGN")
    assert "data/formulation_knowledge/literature_v1.json" in paths
    assert "data/formulation_knowledge/prior_research_corpus_v1.json" in paths
    assert "docs/research/chimie_femme_pw2_20261002/README.md" in paths
    assert "data/governance/inventory_user_confirmation_20260930_aimi_identity.json" in paths


def test_current_research_source_drift_changes_reference_fingerprint(monkeypatch, tmp_path) -> None:
    root = tmp_path
    folder = root / "data/formulation_knowledge"
    folder.mkdir(parents=True)
    document = root / "docs/research/iris.md"
    document.parent.mkdir(parents=True)
    document.write_text("first", encoding="utf-8")
    (folder / "prior_research_corpus_v1.json").write_text(
        json.dumps(
            {
                "records": [{"path": "docs/research/iris.md"}],
            }
        ),
        encoding="utf-8",
    )
    (folder / "literature_v1.json").write_text('{"sources": []}', encoding="utf-8")
    monkeypatch.setattr(engine_jobs, "REPOSITORY_ROOT", root)
    paths = engine_jobs._research_reference_paths("FORMULA_DESIGN")
    before = engine_jobs._bundle_fingerprint(paths)
    document.write_text("second", encoding="utf-8")
    assert before != engine_jobs._bundle_fingerprint(paths)


@pytest.mark.parametrize(
    "path", ["../secrets.txt", "C:/outside.txt", "inventory.txt", "data/../private.txt"]
)
def test_unregistered_research_paths_fail_closed(monkeypatch, tmp_path, path) -> None:
    folder = tmp_path / "data/formulation_knowledge"
    folder.mkdir(parents=True)
    (folder / "prior_research_corpus_v1.json").write_text(
        json.dumps({"records": [{"path": path}]}), encoding="utf-8"
    )
    (folder / "literature_v1.json").write_text('{"sources": []}', encoding="utf-8")
    monkeypatch.setattr(engine_jobs, "REPOSITORY_ROOT", tmp_path)
    with pytest.raises(engine_jobs.EngineJobError, match="reference manifest"):
        engine_jobs._research_reference_paths("FORMULA_ANALYSIS")
