from __future__ import annotations

import copy
import json
import socket
import time

import pytest

from engine.formulation_intelligence import literature_knowledge as knowledge
from engine.formulation_intelligence.source_review import (
    assess_source_use,
    load_source_reviews,
    source_record_hash,
)


def _reviews():
    return load_source_reviews(knowledge.SOURCE_REVIEWS_PATH.read_bytes())


def _bind_manifest(monkeypatch, tmp_path, manifest):
    path = tmp_path / "reviews.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(knowledge, "SOURCE_REVIEWS_PATH", path)


def test_every_source_has_an_exact_advisory_review_binding():
    pack, manifest = knowledge.load_knowledge_pack(), _reviews()
    reviews = {row["source_id"]: row for row in manifest["records"]}
    assert set(reviews) == {row["source_id"] for row in pack["sources"]}
    # A research registry must retain reviewed problems without admitting them.
    # Keep the exact known hold explicit so other accidental holds still fail.
    expected_holds = {"iff_lime_conflict_subtypes"}
    assert {key for key, row in reviews.items() if row["review_state"] == "HOLD"} == expected_holds
    for source in pack["sources"]:
        result = assess_source_use(source, reviews[source["source_id"]])
        assert reviews[source["source_id"]]["source_record_sha256"] == source_record_hash(source)
        assert result["allowed"] is (source["source_id"] not in expected_holds)
        if source["source_id"] in expected_holds:
            assert result["reason_code"] == "SOURCE_REVIEW_HOLD"
        assert result["numeric_calibration_allowed"] is False
        assert result["empirical_data_admission"] is False
        assert all(result[key] is False for key in knowledge.FALSE_AUTHORITY)


@pytest.mark.parametrize("use", ["EMPIRICAL_DATA", "MODEL_WEIGHTS", "NUMERIC_CALIBRATION", "SAFETY", "unknown"])
def test_advisory_review_cannot_admit_other_uses(use):
    source = knowledge.load_knowledge_pack()["sources"][0]
    review = _reviews()["records"][0]
    result = assess_source_use(source, review, requested_use=use)
    assert result["allowed"] is False
    assert result["reason_code"] == "SEPARATE_CAPABILITY_ADMISSION_REQUIRED"


@pytest.mark.parametrize("issue", ["RETRACTED", "EXPRESSION_OF_CONCERN", "UNKNOWN"])
def test_source_issue_removes_only_dependent_clues(monkeypatch, tmp_path, issue):
    manifest = _reviews()
    row = next(row for row in manifest["records"] if row["source_id"] == "iff_orivone")
    row["correction_retraction_state"] = issue
    _bind_manifest(monkeypatch, tmp_path, manifest)
    result = knowledge.retrieve_formulation_knowledge("rooty iris and violet petals")
    assert "iff_orivone" in result["unavailable_source_ids"]
    assert "orivone_root_texture" not in {row["claim_id"] for row in result["claims"]}
    assert "iris_root" not in result["profile_ids"]
    assert result["claims"]  # unrelated available summaries remain usable
    assert knowledge.material_knowledge("Orivone") is None


def test_source_hash_drift_and_missing_review_do_not_grant_clean_success(monkeypatch, tmp_path):
    manifest = _reviews()
    row = next(row for row in manifest["records"] if row["source_id"] == "iff_orivone")
    row["source_record_sha256"] = "0" * 64
    _bind_manifest(monkeypatch, tmp_path, manifest)
    assert "iff_orivone" in knowledge.retrieve_formulation_knowledge("rooty iris")["unavailable_source_ids"]
    manifest["records"] = [r for r in manifest["records"] if r["source_id"] != "iff_orivone"]
    _bind_manifest(monkeypatch, tmp_path, manifest)
    assert "iff_orivone" in knowledge.retrieve_formulation_knowledge("rooty iris")["unavailable_source_ids"]


@pytest.mark.parametrize("contents", [None, "{bad json", "{}", "[]"])
def test_missing_or_malformed_review_manifest_withholds_without_network(monkeypatch, tmp_path, contents):
    path = tmp_path / "missing.json"
    if contents is not None:
        path.write_text(contents, encoding="utf-8")
    monkeypatch.setattr(knowledge, "SOURCE_REVIEWS_PATH", path)
    result = knowledge.retrieve_formulation_knowledge("iris")
    assert result["state"] == "WITHHOLD_UNKNOWN"
    assert result["claims"] == []
    assert knowledge.material_knowledge("Alpha Irone") is None


@pytest.mark.parametrize("change", [
    {"numeric_calibration_allowed": True}, {"empirical_data_rights": "CC_BY"},
    {"rights_scope": "DATA_AND_WEIGHTS"}, {"review_scope": "UNKNOWN"},
    {"review_state": "REVIEWED_ADVISORY"}, {"extra_decision": "ADMIT"},
])
def test_invalid_review_or_authority_escalation_is_rejected(change):
    manifest = _reviews()
    legacy = next(row for row in manifest["records"] if row["source_id"] == "irone_isomers")
    assert legacy["review_state"] == "LEGACY_ADVISORY"
    legacy.update(change)
    with pytest.raises(ValueError):
        load_source_reviews(json.dumps(manifest).encode())
    manifest = _reviews()
    manifest["authority"]["evidence_admission_authorized"] = True
    with pytest.raises(ValueError):
        load_source_reviews(json.dumps(manifest).encode())


def test_review_fingerprint_changes_on_exact_bytes_and_returned_state_is_not_mutable(monkeypatch, tmp_path):
    before = knowledge.knowledge_fingerprints()
    manifest = _reviews()
    manifest["records"][0]["reason"] += " Additional limitation."
    _bind_manifest(monkeypatch, tmp_path, manifest)
    after = knowledge.knowledge_fingerprints()
    assert before["pack_sha256"] == after["pack_sha256"]
    assert before["source_review_manifest_sha256"] != after["source_review_manifest_sha256"]
    original = knowledge.retrieve_formulation_knowledge("iris")
    changed = copy.deepcopy(original)
    changed["source_reviews"].clear()
    assert knowledge.retrieve_formulation_knowledge("iris") == original


def test_source_hash_is_order_invariant_but_content_sensitive():
    source = knowledge.load_knowledge_pack()["sources"][0]
    assert source_record_hash(source) == source_record_hash(dict(reversed(list(source.items()))))
    assert source_record_hash(source) != source_record_hash({**source, "title": "Changed"})


def test_review_retrieval_is_offline_and_fast(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("runtime research must not use the network")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    knowledge.retrieve_formulation_knowledge("lavender amber with fruity musk")
    times = []
    for _ in range(25):
        start = time.perf_counter()
        result = knowledge.retrieve_formulation_knowledge("lavender amber with fruity musk")
        times.append(time.perf_counter() - start)
        assert result["source_review_manifest_sha256"]
        assert result["network_used"] is False
    assert sorted(times)[23] < 0.5
