"""/v2/workbench/blind-tests: two saved versions as vials A and B, key hidden until the reveal."""

import json

import pytest

from app.services import batch_production as batches
from app.services import blind_tests
from app.services import formula_versions as versions
from tests.integration.test_formula_versions import CARD, ROWS

VERSIONS = "/api/v1/lab/v2/workbench/formula-versions"
URL = "/api/v1/lab/v2/workbench/blind-tests"
OTHER_ROWS = [{**ROWS[0], "amount": "900"}, *ROWS[1:]]


@pytest.fixture(autouse=True)
def blind_files(tmp_path, monkeypatch):
    monkeypatch.setenv(versions.VERSION_LOG_PATH_ENV, str(tmp_path / "formula_versions.jsonl"))
    monkeypatch.setenv(batches.BATCH_RECORD_PATH_ENV, str(tmp_path / "batch_records.jsonl"))
    monkeypatch.setenv(batches.BATCH_DIR_ENV, str(tmp_path / "batches"))
    monkeypatch.setenv(blind_tests.BLIND_TEST_PATH_ENV, str(tmp_path / "blind_tests.jsonl"))
    return tmp_path


async def _two_versions(client):
    first = (await client.post(VERSIONS, json={"name": "Rose Test", "bottle_ml": "30", "rows": ROWS, "card_text": CARD})).json()
    second = (await client.post(VERSIONS, json={
        "formula_id": first["formula_id"], "parent_version": 1, "name": "Rose Test", "bottle_ml": "30",
        "rows": OTHER_ROWS, "card_text": CARD.replace("| 600 |", "| 900 |"),
    })).json()
    return first, second


async def _create(client, first, second, **overrides):
    body = {
        "title": "Rose blind", "brief": "A rose that stays fresh",
        "first": {"formula_id": first["formula_id"], "version": first["version"], "label": "Composer"},
        "second": {"formula_id": second["formula_id"], "version": second["version"], "label": "Opus card"},
    }
    body.update(overrides)
    return await client.post(URL, json=body)


@pytest.mark.asyncio
async def test_a_test_shows_both_vials_rows_but_not_which_version_is_which(client, blind_files):
    first, second = await _two_versions(client)

    response = await _create(client, first, second)

    assert response.status_code == 201, response.text
    test = response.json()
    assert [vial["letter"] for vial in test["vials"]] == ["A", "B"]
    amounts = sorted(vial["rows"][0]["amount"] for vial in test["vials"])
    assert amounts == ["600", "900"]
    assert test["times"] == ["5 min", "1 h", "4 h"]
    assert (test["key"], test["outcome"], test["revealed"], test["picks"]) == (None, None, False, [])
    page = json.dumps(test) + json.dumps((await client.get(URL)).json())
    for hidden in ("Composer", "Opus card", first["formula_id"]):
        assert hidden not in page
    # The key is kept on the server, in Kenny's own log.
    assert "Opus card" in (blind_files / "blind_tests.jsonl").read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_the_order_is_random_and_the_key_matches_the_rows(client, blind_files, monkeypatch):
    first, second = await _two_versions(client)
    letters = []
    for draw in (0, 1):
        monkeypatch.setattr(blind_tests.secrets, "randbelow", lambda _n, draw=draw: draw)
        test = (await _create(client, first, second)).json()
        await client.post(f"{URL}/{test['test_id']}/picks", json={"time": "5 min", "choice": "A"})
        revealed = (await client.post(f"{URL}/{test['test_id']}/reveal")).json()
        composer = next(letter for letter, side in revealed["key"].items() if side["label"] == "Composer")
        vial = next(vial for vial in revealed["vials"] if vial["letter"] == composer)
        assert vial["rows"][0]["amount"] == "600"
        letters.append(composer)
    assert letters == ["A", "B"]


@pytest.mark.asyncio
async def test_picks_change_until_the_reveal_then_are_fixed_and_counted(client, blind_files):
    first, second = await _two_versions(client)
    test = (await _create(client, first, second)).json()
    picks = f"{URL}/{test['test_id']}/picks"

    early = await client.post(f"{URL}/{test['test_id']}/reveal")
    assert early.status_code == 400
    assert "at least one strip time" in early.json()["error"]["message"]

    await client.post(picks, json={"time": "5 min", "choice": "B"})
    await client.post(picks, json={"time": "5 min", "choice": "A", "name_a": 4, "name_b": 2})
    await client.post(picks, json={"time": "4 h", "choice": "same", "name_a": 3, "note": "both flat"})
    revealed = (await client.post(f"{URL}/{test['test_id']}/reveal")).json()
    late = await client.post(picks, json={"time": "1 h", "choice": "B"})

    assert [(pick["time"], pick["choice"]) for pick in revealed["picks"]] == [("5 min", "A"), ("4 h", "same")]
    assert revealed["revealed"] is True
    a_label = revealed["key"]["A"]["label"]
    assert revealed["outcome"] == [{"time": "5 min", "preferred": a_label}, {"time": "4 h", "preferred": None}]
    assert late.status_code == 400 and "fixed" in late.json()["error"]["message"]
    listed = (await client.get(URL)).json()
    tally = {row["label"]: row for row in listed["tally"]}
    b_label = revealed["key"]["B"]["label"]
    assert tally[a_label] == {"label": a_label, "picks": 2, "preferred": 1, "name_mean": 3.5}
    assert tally[b_label] == {"label": b_label, "picks": 2, "preferred": 0, "name_mean": 2.0}


@pytest.mark.asyncio
async def test_bad_tests_and_picks_are_refused(client, blind_files):
    first, second = await _two_versions(client)

    same = await _create(client, first, first)
    same_label = await client.post(URL, json={
        "title": "Rose blind",
        "first": {"formula_id": first["formula_id"], "version": 1, "label": "Composer"},
        "second": {"formula_id": second["formula_id"], "version": 2, "label": "composer"},
    })
    missing = await _create(client, first, {"formula_id": "0" * 32, "version": 1})
    test = (await _create(client, first, second)).json()
    bad_time = await client.post(f"{URL}/{test['test_id']}/picks", json={"time": "2 h", "choice": "A"})
    bad_score = await client.post(f"{URL}/{test['test_id']}/picks", json={"time": "1 h", "choice": "A", "name_a": 6})
    unknown = await client.post(f"{URL}/{'f' * 32}/picks", json={"time": "1 h", "choice": "A"})

    assert same.status_code == 400 and "same formula" in same.json()["error"]["message"]
    assert same_label.status_code == 400 and "different names" in same_label.json()["error"]["message"]
    assert missing.status_code == 404
    assert (bad_time.status_code, bad_score.status_code, unknown.status_code) == (422, 422, 404)


@pytest.mark.asyncio
async def test_a_hand_edited_log_is_refused(client, blind_files):
    first, second = await _two_versions(client)
    test = (await _create(client, first, second)).json()
    await client.post(f"{URL}/{test['test_id']}/picks", json={"time": "1 h", "choice": "B"})
    log = blind_files / "blind_tests.jsonl"
    log.write_text(log.read_text(encoding="utf-8").replace("Composer", "Composr"), encoding="utf-8")

    response = await client.get(URL)

    assert response.status_code == 400
    assert "edited by hand" in response.json()["error"]["message"]
