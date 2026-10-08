"""An explicit missing-byte HOLD is not successful historical replay."""
import json

import pytest

from tests.historical_snapshots import ROOT, historical_replay_status


def test_review_lists_exact_missing_versions_without_accepting_current_runtime():
    review = json.loads((ROOT / "data/governance/historical_source_replay_review_20261007.json").read_bytes())
    assert review["decision"] == "HOLD_HISTORICAL_REPLAY_INCOMPLETE"
    assert review["historical_receipts_modified"] is False
    assert review["current_runtime_accepted_by_this_review"] is False
    assert not any(review["authority"].values())
    rows = review["missing_sources"]
    assert len(rows) == len({(row["path"], row["original_sha256"]) for row in rows}) == 9
    for row in rows:
        assert row["original_sha256"] != row["current_sha256"]
        assert historical_replay_status(ROOT / row["path"], row["original_sha256"],
                                        row["original_size_bytes"]) == row["state"]


def test_unknown_missing_pin_cannot_borrow_a_replay_hold():
    with pytest.raises(AssertionError, match="no exact replay-HOLD review"):
        historical_replay_status(ROOT / "engine/fuckups/pre_mix_guard.py", "0" * 64)


def test_wrong_original_byte_count_cannot_borrow_a_replay_hold():
    with pytest.raises(AssertionError):
        historical_replay_status(
            ROOT / "backend/app/schemas/lab.py",
            "915cf711d0a62a9bc26f305b0d4cd6d4b9f20e1704fb2d948eda28fd040c19b4", 1,
        )
