"""The commercial-pack routes on an app that includes only their router."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import commercial_pack

GATE = {"formulas": [{
    "name": "Synthetic",
    "formula_state": {"total_raw_ul": 3000.0},
    "gates": [{"gate": "safety_ifra_allergen", "status": "PASS", "data": {
        "rows": [{"material": "A", "actual_pct": 0.1, "limit_pct": 1.0, "verdict": "pass"}],
        "batch_volume_ml": 30.0,
        "ifra_table": {"amendment_in_force": 51, "category": "4"},
    }}],
}]}
META = {"lot": "L1", "date": "13/10/2026", "manufacturer_name": "Maker"}


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(commercial_pack, "PROJECT_ROOT", tmp_path)
    lot = tmp_path / "data" / "user" / "batches" / "L1"
    lot.mkdir(parents=True)
    (lot / "gate.json").write_text(json.dumps(GATE), encoding="utf-8")
    outside = tmp_path / "data" / "secret.json"
    outside.write_text(json.dumps(GATE), encoding="utf-8")
    (lot / "link.json").symlink_to(outside)
    app = FastAPI()
    app.include_router(commercial_pack.router, prefix="/pack")
    return TestClient(app), tmp_path


def test_label_route_returns_the_label(sandbox):
    http, _ = sandbox
    response = http.post("/pack/label", json={"fields": {"name": "Bloom"}, "rows": []})
    assert response.status_code == 200
    assert response.json()["draft"] is True
    assert response.json()["front"][0] == "Bloom"


def test_label_route_refuses_bad_fields(sandbox):
    http, _ = sandbox
    response = http.post("/pack/label", json={"fields": {"type": "mist"}})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_field"


def test_statement_from_inline_gate_and_from_a_batch_path(sandbox):
    http, tmp_path = sandbox
    inline = http.post("/pack/ifra-statement", json={"gate_json": GATE, "meta": META})
    by_path = http.post(
        "/pack/ifra-statement",
        json={"gate_path": "data/user/batches/L1/gate.json", "meta": META},
    )
    absolute = http.post(
        "/pack/ifra-statement",
        json={"gate_path": str(tmp_path / "data/user/batches/L1/gate.json"), "meta": META},
    )
    assert inline.status_code == by_path.status_code == absolute.status_code == 200
    assert inline.json() == by_path.json() == absolute.json()
    assert inline.json()["verdict"] == "Conforms"


@pytest.mark.parametrize("path", [
    "data/user/batches/../secret.json",
    "data/user/batches/L1/link.json",
    "data/secret.json",
    "/etc/passwd",
    "data/user/batches",
])
def test_statement_path_cannot_leave_the_batches_folder(sandbox, path):
    http, tmp_path = sandbox
    response = http.post("/pack/ifra-statement", json={"gate_path": path, "meta": META})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "gate_path_refused"
    assert str(tmp_path) not in response.text


def test_statement_needs_exactly_one_source_and_reports_a_missing_file(sandbox):
    http, _ = sandbox
    both = http.post(
        "/pack/ifra-statement",
        json={"gate_json": GATE, "gate_path": "data/user/batches/L1/gate.json"},
    )
    neither = http.post("/pack/ifra-statement", json={"meta": META})
    missing = http.post(
        "/pack/ifra-statement", json={"gate_path": "data/user/batches/L2/gate.json"}
    )
    assert both.status_code == neither.status_code == 400
    assert missing.status_code == 404
