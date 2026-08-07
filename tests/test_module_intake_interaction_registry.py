"""Interaction registry loader tests (read-only; no mutation)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.interaction_registry.loader import load_registry


def _fixture(tmp_path):
    data = {
        "version": "1",
        "created": "test",
        "inventory_source": {},
        "groups": [{"id": "G1", "name": "Ionone", "short": "ionone", "phase": "heart"}],
        "interactions": [
            {
                "pair_id": "P1",
                "group_a_id": "G1",
                "group_b_id": "G2",
                "group_a": "Ionone",
                "group_b": "Musk",
                "primary_interaction": "suppression",
                "evidence_class": "STRUCTURED_HYPOTHESIS",
                "confidence": 0.4,
                "status": "hypothesis",
                "dose_window": "0-1%",
                "phase_window": "drydown",
            }
        ],
        "sources": {"SRC-1": {"title": "test"}},
        "worker_packets": [],
        "boundaries": {"note": "advisory only"},
    }
    p = tmp_path / "atlas.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def test_load_counts(tmp_path):
    reg = load_registry(_fixture(tmp_path))
    assert reg.count()["groups"] == 1
    assert reg.count()["interactions"] == 1


def test_query(tmp_path):
    reg = load_registry(_fixture(tmp_path))
    assert reg.query_group("G1")["name"] == "Ionone"
    assert reg.query_pair("P1")["evidence_class"] == "STRUCTURED_HYPOTHESIS"
    assert len(reg.pairs_for_group("G1")) == 1


def test_hypothesis_not_upgraded(tmp_path):
    reg = load_registry(_fixture(tmp_path))
    pair = reg.query_pair("P1")
    # STRUCTURED_HYPOTHESIS stays structured; the loader never upgrades it
    assert pair["evidence_class"] == "STRUCTURED_HYPOTHESIS"
    assert pair["status"] == "hypothesis"
