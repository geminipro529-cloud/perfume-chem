"""Checkpoint 10 code classification is source-bound and non-destructive."""

from __future__ import annotations

import json
from pathlib import Path

from engine.calibration.hashing import (
    PORTABLE_FILE_HASH_MATCH_ALGORITHM,
    portable_file_hash_matches,
)
from tests.historical_snapshots import assert_historical_source_pin


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "data"
    / "governance"
    / "full_potential_cp10_code_classification_20260927.json"
)


def test_classified_source_hashes_match_the_frozen_september_source() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["artifact_hash_semantics"] == (
        PORTABLE_FILE_HASH_MATCH_ALGORITHM
    )
    for records in manifest["categories"].values():
        for record in records:
            path = ROOT / record["path"]
            assert path.is_file(), record["path"]
            if not portable_file_hash_matches(path, record["sha256"]):
                # A historical classification is not current-source acceptance.
                assert_historical_source_pin(record["path"], record["sha256"])


def test_classification_does_not_claim_or_authorize_deletion() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["confirmed_dead_paths"] == []
    assert manifest["authority"]["deletion_authorized"] is False
    assert all(value is False for value in manifest["authority"].values())
    assert "RETIREMENT_REVIEW_CANDIDATE_NOT_DEAD" in manifest["categories"]
