"""/v2/workbench/formula-versions: saved versions from the Edit a formula page."""

import hashlib
import json

import pytest

from app.services import batch_production as batches
from app.services import formula_versions as versions

URL = "/api/v1/lab/v2/workbench/formula-versions"

CARD = """# Rose Test

| Material | Dilution | Amount (µL) |
|---|---|---:|
| Hedione | neat | 600 |
| Rose Oxide | 1% w/w in DPG | 333.333 |
| Ethanol | | 29000 |
"""

ROWS = [
    {"material": "Hedione", "fraction": "1", "basis": "neat", "amount": "600", "note": "heart"},
    {"material": "Rose Oxide", "stock_id": "Rose Oxide|0.01", "fraction": "0.01", "basis": "mass_fraction",
     "carrier": "DPG", "amount": "1000/3", "note": "top"},
    {"material": "Ethanol", "amount": "29000"},
]


@pytest.fixture(autouse=True)
def version_files(tmp_path, monkeypatch):
    monkeypatch.setenv(versions.VERSION_LOG_PATH_ENV, str(tmp_path / "formula_versions.jsonl"))
    monkeypatch.setenv(batches.BATCH_RECORD_PATH_ENV, str(tmp_path / "batch_records.jsonl"))
    monkeypatch.setenv(batches.BATCH_DIR_ENV, str(tmp_path / "batches"))
    return tmp_path


def _body(**overrides):
    body = {"name": "Rose Test", "bottle_ml": "30", "rows": ROWS, "card_text": CARD}
    body.update(overrides)
    return body


def _log_lines(tmp_path):
    return (tmp_path / "formula_versions.jsonl").read_bytes().splitlines()


@pytest.mark.asyncio
async def test_a_first_save_is_version_one_and_keeps_the_rows_exactly(client, version_files):
    saved = await client.post(URL, json=_body(note="first pour"))

    assert saved.status_code == 201
    version = saved.json()
    assert len(version["formula_id"]) == 32
    assert (version["version"], version["parent_version"], version["note"], version["created"]) == (1, None, "first pour", True)
    assert version["card_sha256"] == hashlib.sha256(CARD.encode("utf-8")).hexdigest()
    assert (version["locked"], version["locked_by"], version["bottles"]) == (False, [], [])
    # 1000/3 µL stays a fraction; nothing is rounded on the way in or out.
    assert version["rows"][1]["amount"] == "1000/3"
    assert version["rows"][2] == {"material": "Ethanol", "stock_id": None, "fraction": "", "basis": "",
                                  "carrier": None, "solid": False, "amount": "29000", "note": ""}
    assert version["card_text"] == CARD

    listed = (await client.get(URL)).json()
    assert [(f["name"], f["latest"]) for f in listed["formulas"]] == [("Rose Test", 1)]
    assert "rows" not in listed["formulas"][0]["versions"][0]
    assert listed["formulas"][0]["versions"][0]["row_count"] == 3
    one = await client.get(f"{URL}/{version['formula_id']}/1")
    assert one.status_code == 200 and one.json()["rows"] == version["rows"]


@pytest.mark.asyncio
async def test_saving_the_same_content_again_makes_no_new_version_and_a_change_makes_the_next(client, version_files):
    first = (await client.post(URL, json=_body())).json()
    formula_id = first["formula_id"]

    again = await client.post(URL, json=_body(formula_id=formula_id, parent_version=1, note="no change"))
    assert again.status_code == 200
    assert (again.json()["version"], again.json()["created"]) == (1, False)
    assert len(_log_lines(version_files)) == 1

    changed_rows = [dict(ROWS[0], amount="650"), *ROWS[1:]]
    second = await client.post(URL, json=_body(formula_id=formula_id, parent_version=1, rows=changed_rows))
    assert second.status_code == 201
    assert (second.json()["version"], second.json()["parent_version"]) == (2, 1)
    # Version 1 is unchanged.
    assert (await client.get(f"{URL}/{formula_id}/1")).json()["rows"][0]["amount"] == "600"
    listed = (await client.get(URL)).json()["formulas"]
    assert [v["version"] for v in listed[0]["versions"]] == [1, 2]


@pytest.mark.asyncio
async def test_a_version_locks_once_a_batch_is_made_from_its_card(client, version_files):
    version = (await client.post(URL, json=_body())).json()
    other = (await client.post(URL, json=_body(name="Other", card_text=CARD.replace("600", "700")))).json()

    plan = batches.plan_batch(source_path=None, text=CARD, name=None, bottles="2", bottle_ml="30",
                              card_total_ml="30", loss_percent="3")
    batches.record_batch(lot="KS-1", made_on="2026-10-14", made_by="", plan=plan, gate_run_id=None, notes="")

    locked = (await client.get(f"{URL}/{version['formula_id']}/1")).json()
    assert (locked["locked"], locked["locked_by"]) == (True, ["KS-1"])
    assert (await client.get(f"{URL}/{other['formula_id']}/1")).json()["locked"] is False


@pytest.mark.asyncio
async def test_bottles_are_tied_to_one_version_at_a_time(client, version_files):
    version = (await client.post(URL, json=_body())).json()
    formula_id = version["formula_id"]
    second = (await client.post(URL, json=_body(formula_id=formula_id, rows=ROWS[:2]))).json()
    assert second["version"] == 2
    bottle = (await client.post("/api/v1/lab/bottles", json={"label": "Rose bottle 1"})).json()

    tied = await client.post(f"{URL}/{formula_id}/1/bottles", json={"bottle_id": bottle["id"]})
    assert tied.status_code == 200
    assert [(b["bottle_id"], b["label"]) for b in tied.json()["bottles"]] == [(bottle["id"], "Rose bottle 1")]
    # Tying it again changes nothing.
    assert (await client.post(f"{URL}/{formula_id}/1/bottles", json={"bottle_id": bottle["id"]})).status_code == 200
    assert len(_log_lines(version_files)) == 3

    elsewhere = await client.post(f"{URL}/{formula_id}/2/bottles", json={"bottle_id": bottle["id"]})
    assert elsewhere.status_code == 400
    assert "Rose Test version 1" in elsewhere.json()["error"]["message"]

    untied = await client.post(f"{URL}/{formula_id}/1/bottles", json={"bottle_id": bottle["id"], "tied": False})
    assert untied.status_code == 200 and untied.json()["bottles"] == []
    moved = await client.post(f"{URL}/{formula_id}/2/bottles", json={"bottle_id": bottle["id"]})
    assert [b["bottle_id"] for b in moved.json()["bottles"]] == [bottle["id"]]

    again = await client.post(f"{URL}/{formula_id}/1/bottles", json={"bottle_id": bottle["id"], "tied": False})
    assert again.status_code == 400
    missing = await client.post(f"{URL}/{formula_id}/1/bottles", json={"bottle_id": "no-such-bottle"})
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_a_hand_edited_log_is_refused_not_read(client, version_files):
    await client.post(URL, json=_body())
    await client.post(URL, json=_body(name="Second"))
    path = version_files / "formula_versions.jsonl"
    lines = path.read_bytes().splitlines()
    first = json.loads(lines[0])
    first["version"]["rows"][0]["amount"] = "6000"
    path.write_bytes(json.dumps(first, sort_keys=True).encode() + b"\n" + lines[1] + b"\n")

    listed = await client.get(URL)
    assert listed.status_code == 400
    assert "edited by hand" in listed.json()["error"]["message"]
    # Nothing more is written on a broken chain.
    assert (await client.post(URL, json=_body(name="Third"))).status_code == 400
    assert len(path.read_bytes().splitlines()) == 2


@pytest.mark.asyncio
async def test_unknown_formulas_and_versions_are_not_found(client):
    assert (await client.get(f"{URL}/{'0' * 32}/1")).status_code == 404
    unknown = await client.post(URL, json=_body(formula_id="0" * 32))
    assert unknown.status_code == 404
    orphan = await client.post(URL, json=_body(parent_version=1))
    assert orphan.status_code == 400
    version = (await client.post(URL, json=_body())).json()
    assert (await client.get(f"{URL}/{version['formula_id']}/2")).status_code == 404
    bad_parent = await client.post(URL, json=_body(formula_id=version["formula_id"], parent_version=5, name="New"))
    assert bad_parent.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        {"rows": []},
        {"rows": [dict(ROWS[0], amount="0")]},
        {"rows": [dict(ROWS[0], amount="1.5")]},
        {"rows": [dict(ROWS[0], amount="-1")]},
        {"rows": [dict(ROWS[0], amount="1/0")]},
        {"rows": [dict(ROWS[0], note="middle")]},
        {"rows": [dict(ROWS[0], extra=1)]},
        {"card_text": ""},
        {"name": " "},
        {"extra": 1},
    ],
)
async def test_a_malformed_save_is_refused(client, version_files, change):
    response = await client.post(URL, json=_body(**change))

    assert response.status_code == 422
    assert not (version_files / "formula_versions.jsonl").exists()
