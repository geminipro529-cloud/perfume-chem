"""Kenny's liking ratings, two-bottle picks and the personal liking fit.

Every test writes the personal liking file to its own temporary path and reads
the crowd table from a temporary path, never the real data/user/ folder.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from engine.user_records import USER_RECORDS_DIR

from app import db_bootstrap
from app.services import personal_liking

BASE = "/api/v1/feedback/liking"
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REAL_FILE = USER_RECORDS_DIR / "personal_liking.json"

CROWD = {
    "materials": {
        "Iso E Super": {"value": 0.9, "aliases": [], "family": "woody"},
        "hedione": {"value": 0.1, "aliases": [], "family": "floral"},
        "Ambroxide": {"value": 0.5, "aliases": ["Ambroxan"], "family": "woody"},
    }
}


def _real_file_state():
    return REAL_FILE.stat().st_mtime_ns if REAL_FILE.exists() else None


@pytest.fixture(autouse=True)
def liking_paths(tmp_path, monkeypatch):
    output = tmp_path / "user" / "personal_liking.json"
    crowd = tmp_path / "pleasantness_crowd_v1.json"
    monkeypatch.setenv(personal_liking.PERSONAL_LIKING_PATH_ENV, str(output))
    monkeypatch.setenv(personal_liking.CROWD_TABLE_PATH_ENV, str(crowd))
    return output, crowd


def _rating(**overrides):
    return {
        "formula_name": "Iris Cathedral",
        "formula_key": "rows-sha-1",
        "window": "opening",
        "liking": 7,
        "material_shares": {"Iso E Super": 0.5, "Hedione": 0.25},
        **overrides,
    }


def _pick(**overrides):
    return {
        "window": "1h",
        "formula_a_name": "Iris Cathedral",
        "formula_a_key": "rows-sha-1",
        "shares_a": {"Iso E Super": 0.4},
        "formula_b_name": "Iris Chapel",
        "formula_b_key": "rows-sha-2",
        "shares_b": {"Ambroxan": 0.2, "Hedione": 0.2},
        "preferred": "a",
        **overrides,
    }


async def _post_worked_case(client):
    """Two ratings and one pick; the expected fit is computed by hand in the tests."""
    first = _rating(liking=10, crowd_guess=0.2)
    second = _rating(
        formula_key="rows-sha-2",
        liking=4,
        window="4h",
        material_shares={"Hedione": 0.5, "Ambroxan": 0.25},
    )
    for body in (first, second):
        assert (await client.post(f"{BASE}/ratings", json=body)).status_code == 201
    assert (await client.post(f"{BASE}/picks", json=_pick())).status_code == 201


@pytest.mark.asyncio
async def test_rating_create_list_delete(client, liking_paths):
    output, _crowd = liking_paths
    before = _real_file_state()

    created = await client.post(
        f"{BASE}/ratings", json=_rating(complexity=6, too_loud="Hedione", note="bright")
    )
    assert created.status_code == 201, created.text
    rating = created.json()
    assert rating["source"] == "lab_card"
    assert rating["complexity"] == 6
    second = await client.post(f"{BASE}/ratings", json=_rating(window="1h", liking=3))
    assert second.status_code == 201

    listed = (await client.get(f"{BASE}/ratings")).json()
    assert [row["id"] for row in listed] == [second.json()["id"], rating["id"]]
    assert len((await client.get(f"{BASE}/ratings", params={"limit": 1})).json()) == 1
    assert json.loads(output.read_text())["ratings_used"] == 2

    assert (await client.delete(f"{BASE}/ratings/{rating['id']}")).status_code == 204
    assert (await client.delete(f"{BASE}/ratings/{rating['id']}")).status_code == 404
    assert [row["id"] for row in (await client.get(f"{BASE}/ratings")).json()] == [
        second.json()["id"]
    ]
    assert json.loads(output.read_text())["ratings_used"] == 1
    assert _real_file_state() == before


@pytest.mark.asyncio
async def test_pick_create_list_delete(client, liking_paths):
    output, _crowd = liking_paths
    created = await client.post(f"{BASE}/picks", json=_pick(preferred="same", note="close"))
    assert created.status_code == 201, created.text
    pick = created.json()
    assert pick["preferred"] == "same"
    assert [row["id"] for row in (await client.get(f"{BASE}/picks")).json()] == [pick["id"]]
    fit = json.loads(output.read_text())
    assert fit["picks_used"] == 1
    assert fit["materials"] == {}

    assert (await client.delete(f"{BASE}/picks/{pick['id']}")).status_code == 204
    assert (await client.delete(f"{BASE}/picks/{pick['id']}")).status_code == 404
    assert (await client.get(f"{BASE}/picks")).json() == []
    assert json.loads(output.read_text())["picks_used"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path, body",
    [
        ("ratings", _rating(liking=11)),
        ("ratings", _rating(window="2h")),
        ("ratings", _rating(material_shares={"Iso E Super": 1.0, "Hedione": 0.5})),
        ("ratings", _rating(material_shares={})),
        ("ratings", _rating(material_shares={"Iso E Super": 0.0})),
        ("ratings", _rating(material_shares={"Iso E Super": -0.1, "Hedione": 0.5})),
        ("picks", _pick(preferred="c")),
        ("picks", _pick(shares_b={"Ambroxan": 1.5})),
    ],
)
async def test_invalid_records_are_refused(client, liking_paths, path, body):
    output, _crowd = liking_paths
    response = await client.post(f"{BASE}/{path}", json=body)
    assert response.status_code == 422, response.text
    assert not output.exists()


@pytest.mark.asyncio
async def test_fit_without_crowd_table(client, liking_paths):
    output, crowd = liking_paths
    assert not crowd.exists()
    await _post_worked_case(client)

    fit = (await client.get(f"{BASE}/personal")).json()
    assert fit == {**json.loads(output.read_text()), "updated_at": fit["updated_at"]}
    assert fit["schema"] == "personal_liking_v1"
    assert (fit["ratings_used"], fit["picks_used"]) == (2, 1)
    materials = fit["materials"]
    # Rating 1: y = 1, crowd guess 0.2, e = 0.8.  Rating 2: y = -1/3, e = -1/3.
    # Pick a over b: +0.25 on shares_a and -0.25 on shares_b, each weight 0.5.
    iso = materials["Iso E Super"]
    assert iso["deviation"] == pytest.approx((0.5 * 0.8 + 0.5 * 0.4 * 0.25) / (0.7 + 1))
    assert iso["evidence"] == pytest.approx(0.7)
    assert iso["n"] == 2
    assert iso["crowd"] is None
    assert iso["personal"] == pytest.approx(iso["deviation"])
    hedione = materials["Hedione"]
    assert hedione["deviation"] == pytest.approx(
        (0.25 * 0.8 + 0.5 * (-1 / 3) + 0.5 * 0.2 * -0.25) / (0.85 + 1)
    )
    assert hedione["evidence"] == pytest.approx(0.85)
    assert hedione["n"] == 3
    ambroxan = materials["Ambroxan"]
    assert ambroxan["deviation"] == pytest.approx(
        (0.25 * (-1 / 3) + 0.5 * 0.2 * -0.25) / (0.35 + 1)
    )
    assert ambroxan["evidence"] == pytest.approx(0.35)
    assert ambroxan["n"] == 2
    assert fit["families"] == {}
    assert fit["liked"] == ["Iso E Super", "Hedione"]
    assert fit["disliked"] == []


@pytest.mark.asyncio
async def test_fit_with_crowd_table(client, liking_paths):
    output, crowd = liking_paths
    crowd.write_text(json.dumps(CROWD), encoding="utf-8")
    await _post_worked_case(client)

    fit = json.loads(output.read_text())
    materials = fit["materials"]
    iso_deviation = (0.5 * 0.8 + 0.5 * 0.4 * 0.25) / 1.7
    assert materials["Iso E Super"]["crowd"] == 0.9
    assert materials["Iso E Super"]["personal"] == 1.0  # 0.9 + 0.26, clamped
    assert materials["Iso E Super"]["deviation"] == pytest.approx(iso_deviation)
    # "Hedione" matches the crowd's "hedione" by casefold; "Ambroxan" by alias.
    hedione_deviation = (0.25 * 0.8 + 0.5 * (-1 / 3) - 0.025) / 1.85
    assert materials["Hedione"]["crowd"] == 0.1
    assert materials["Hedione"]["personal"] == pytest.approx(0.1 + hedione_deviation)
    ambroxan_deviation = (0.25 * (-1 / 3) - 0.025) / 1.35
    assert materials["Ambroxan"]["crowd"] == 0.5
    assert materials["Ambroxan"]["personal"] == pytest.approx(0.5 + ambroxan_deviation)

    woody = fit["families"]["woody"]
    assert woody["evidence"] == pytest.approx(0.5 + 0.25 + 0.5 * 0.4 + 0.5 * 0.2)
    assert woody["deviation"] == pytest.approx(
        (0.5 * 0.8 + 0.25 * (-1 / 3) + 0.5 * 0.4 * 0.25 + 0.5 * 0.2 * -0.25) / (1.05 + 1)
    )
    assert woody["n"] == 4
    floral = fit["families"]["floral"]
    assert floral["deviation"] == pytest.approx(hedione_deviation)
    assert floral["evidence"] == pytest.approx(0.85)
    assert floral["n"] == 3


@pytest.mark.asyncio
async def test_disliked_lists_well_evidenced_negative_materials(client, liking_paths):
    output, _crowd = liking_paths
    body = _rating(liking=1, material_shares={"Indole": 0.6, "Hedione": 0.3})
    assert (await client.post(f"{BASE}/ratings", json=body)).status_code == 201
    fit = json.loads(output.read_text())
    assert fit["liked"] == []
    assert fit["disliked"] == ["Indole"]  # Hedione has evidence 0.3 < 0.5


def test_default_file_is_in_the_personal_records_folder(monkeypatch):
    monkeypatch.delenv(personal_liking.PERSONAL_LIKING_PATH_ENV)
    assert personal_liking.personal_liking_path() == REAL_FILE.resolve()


def test_alembic_bootstrap_creates_both_tables(tmp_path):
    database = tmp_path / "fresh.db"
    config = db_bootstrap.build_alembic_config(
        BACKEND_ROOT / "alembic.ini", f"sqlite:///{database.as_posix()}"
    )
    db_bootstrap.upgrade_database(config, snapshot_directory=tmp_path / "snapshots")

    connection = sqlite3.connect(database)
    try:
        tables = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        columns = {
            table: {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            for table in ("liking_ratings", "liking_picks")
        }
    finally:
        connection.close()
    assert {"liking_ratings", "liking_picks"} <= tables
    assert {"formula_key", "window", "liking", "material_shares", "crowd_guess", "source"} <= (
        columns["liking_ratings"]
    )
    assert {"shares_a", "shares_b", "crowd_a", "crowd_b", "preferred"} <= columns["liking_picks"]
