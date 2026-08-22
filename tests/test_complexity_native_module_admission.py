from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "data/governance/complexity_native_module_admission_20260822.json"

EXPECTED = {
    "engine/perception/construction_complexity.py": "f8dd92ae5da1a9aa409ed27ad2e5e789874f32bc77a156e28a65870dae871ab1",
    "engine/perception/complexity_expansion.py": "69b0e2a38f33545efa94e8e3a832091a2ce72d9496b9b211edcd60c0c8afb54e",
    "engine/scientific_validation/complexity_design_contracts.py": "ef905b8adb6c7c8bdf02372c56040295054fdbeb4dcfe39c3410cb09390ae968",
    "engine/scientific_validation/complexity_model_admission.py": "484a0d3902eb96b946f9b3e566d3caa1083187655f12ed456942c9353e0a3710",
    "engine/physics/model_lifecycle.py": "c320593f3e1bea8dd16014794e32ca5adffd557effb749f82193d487988acaaf",
    "engine/sensory/within_sniff.py": "2ac737b87a3a9e237647b4f2bd7fe4601c5634926d7267c240c606726b269caa",
    "engine/sensory/temporal_observations.py": "e730484f30ecbab428e02d31042649990db46b389d0da6bbfa13e93a6006770b",
    "engine/sensory/order_balance.py": "fe71999d09c7d2366f2ba7c6f27718ba04282435125fd37a02a06051dba5807c",
    "engine/sensory/panel_contract.py": "418ecf7f42454ba335c8113487570458fb81210db016cfe778abce72955898cc",
}


def test_admitted_native_files_match_exact_receipt() -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    recorded = {row["path"]: row["sha256"] for row in payload["native_modules"]}
    assert recorded == EXPECTED
    for relative, expected in EXPECTED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_admission_grants_no_scientific_or_release_authority() -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert payload["state"] == "NATIVE_CLEAN_ROOM_BASELINE_ADMITTED"
    assert payload["focused_tests"] == {"passed": 56, "failed": 0}
    assert all(value is False for value in payload["authority"].values())
