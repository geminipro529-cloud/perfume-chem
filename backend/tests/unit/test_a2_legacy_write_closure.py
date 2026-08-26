from __future__ import annotations

from datetime import UTC, datetime

import pytest
from engine.analytical.ledger import (
    AnalyticalLedger,
    GCMSRun,
    GCOEvent,
    HSSPMERun,
)
from engine.bottle.events import CREATE_BATCH, BottleBatch, BottleEvent
from engine.domain_errors import LegacyWriteProhibitedError
from engine.evidence.ledger import EvidenceClaim, EvidenceLedger, EvidenceSource
from engine.inventory.stock_model import InventoryLedger, StockItem
from engine.sensory.ledger import SensoryObservation, SensorySample, SensoryTrial


def _assert_prohibited(callable_) -> None:
    with pytest.raises(LegacyWriteProhibitedError, match="LabService") as error:
        callable_()
    assert error.value.code == "LEGACY_WRITE_PROHIBITED"


def test_duplicate_legacy_ledgers_reject_public_mutation():
    bottle = BottleBatch("batch")
    event = BottleEvent(
        event_id="event",
        batch_id="batch",
        event_type=CREATE_BATCH,
        timestamp=datetime.now(UTC).isoformat(),
    )
    _assert_prohibited(lambda: bottle.add_event(event))

    item = StockItem(material_id="stock", label="Stock")
    inventory = InventoryLedger([item])
    _assert_prohibited(lambda: inventory.add_stock(item))
    _assert_prohibited(lambda: inventory.remove_stock("stock"))
    _assert_prohibited(lambda: inventory.consume("stock", 1.0))

    analytical = AnalyticalLedger()
    gcms = GCMSRun("run", "instrument", "column", "program", "split", 1.0)
    hsspme = HSSPMERun("hs", "fiber", 1.0, 20.0, 40.0, 10.0, 5.0, 100, "blotter", 0.0)
    gco = GCOEvent("gco", "run", 1.0, "floral", "weak", "assessor", "once")
    _assert_prohibited(lambda: analytical.add_gcms_run(gcms, []))
    _assert_prohibited(lambda: analytical.add_hsspme_run(hsspme))
    _assert_prohibited(lambda: analytical.add_gco_event(gco))

    sensory = SensoryTrial("trial", "sample", ["assessor"])
    sample = SensorySample("sample", "formula", "batch", "ABC")
    observation = SensoryObservation(
        "observation",
        "sample",
        "assessor",
        0.0,
        3.0,
        3.0,
        3.0,
        3.0,
        3.0,
        3.0,
        3.0,
    )
    _assert_prohibited(lambda: sensory.add_sample(sample))
    _assert_prohibited(lambda: sensory.record_observation(observation))

    evidence = EvidenceLedger()
    source = EvidenceSource("source", "A")
    claim = EvidenceClaim("claim", "source", "product", "identity_presence")
    _assert_prohibited(lambda: evidence.add_source(source))
    _assert_prohibited(lambda: evidence.add_claim(claim))


def test_read_only_hydration_bypasses_public_mutators(monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("public mutator used during read-only hydration")

    monkeypatch.setattr(AnalyticalLedger, "add_gcms_run", fail_if_called)
    monkeypatch.setattr(SensoryTrial, "add_sample", fail_if_called)
    monkeypatch.setattr(EvidenceLedger, "add_source", fail_if_called)

    analytical = AnalyticalLedger.from_dict(
        {
            "gcms_runs": [
                {
                    "run": GCMSRun(
                        "run", "instrument", "column", "program", "split", 1.0
                    ).as_dict(),
                    "peaks": [],
                }
            ],
            "hsspme_runs": [],
            "gco_events": [],
        }
    )
    assert analytical.to_dict()["gcms_runs"][0]["run"]["run_id"] == "run"

    sensory = SensoryTrial.from_dict(
        {
            "trial_name": "trial",
            "reference_sample_id": "sample",
            "assessors": ["assessor"],
            "samples": [SensorySample("sample", "formula", "batch", "ABC").as_dict()],
            "observations": [],
        }
    )
    assert sensory.to_dict()["samples"][0]["sample_id"] == "sample"

    evidence = EvidenceLedger.from_dict(
        {
            "sources": [EvidenceSource("source", "A").as_dict()],
            "claims": [],
        }
    )
    assert evidence.to_dict()["sources"][0]["source_id"] == "source"
