"""Rate a material: API round trip, filter, delete and the personal liking file.

Every test writes the personal liking file to its own temporary path, never data/user/.
"""

import json

import pytest

from app.core.config import PROJECT_ROOT
from app.services import personal_liking

BASE = "/api/v1/feedback/liking/materials"
REAL_FILE = PROJECT_ROOT / "data" / "user" / "personal_liking.json"
CROWD = {"materials": {"Iso E Super": {"value": 0.9, "aliases": [], "family": "woody"}}}


@pytest.fixture(autouse=True)
def liking_paths(tmp_path, monkeypatch):
    output = tmp_path / "user" / "personal_liking.json"
    crowd = tmp_path / "pleasantness_crowd_v1.json"
    crowd.write_text(json.dumps(CROWD))
    monkeypatch.setenv(personal_liking.PERSONAL_LIKING_PATH_ENV, str(output))
    monkeypatch.setenv(personal_liking.CROWD_TABLE_PATH_ENV, str(crowd))
    return output


@pytest.mark.asyncio
async def test_round_trip_filter_and_delete(client, liking_paths):
    before = REAL_FILE.stat().st_mtime_ns if REAL_FILE.exists() else None
    first = await client.post(
        BASE, json={"material": "Iso E Super", "stock_label": "10% in DPG", "strength": "weak", "liking": 8}
    )
    assert first.status_code == 201, first.text
    saved = first.json()
    assert saved["personal_fit_written"] is True and saved["source"] == "stock_card"
    assert saved["strength"] == "weak" and saved["stock_label"] == "10% in DPG"
    second = await client.post(BASE, json={"material": "Mystery Resin", "liking": 3, "note": "sharp"})
    assert second.status_code == 201

    fit = json.loads(liking_paths.read_text())
    assert fit["material_ratings_used"] == 2
    assert fit["materials"]["Iso E Super"]["direct_n"] == 1
    assert fit["materials"]["Iso E Super"]["evidence"] == 1.0

    listed = (await client.get(BASE)).json()
    assert [row["id"] for row in listed] == [second.json()["id"], saved["id"]]
    only = (await client.get(BASE, params={"material": "iso e super"})).json()
    assert [row["id"] for row in only] == [saved["id"]]
    assert (await client.get(BASE, params={"material": "iso"})).json() == []

    assert (await client.delete(f"{BASE}/{saved['id']}")).status_code == 204
    assert (await client.delete(f"{BASE}/{saved['id']}")).status_code == 404
    assert json.loads(liking_paths.read_text())["material_ratings_used"] == 1
    after = REAL_FILE.stat().st_mtime_ns if REAL_FILE.exists() else None
    assert after == before


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"material": "X", "liking": 0},
        {"material": "X", "liking": 11},
        {"material": "  ", "liking": 5},
        {"material": "X", "liking": 5, "strength": "huge"},
    ],
)
async def test_bad_bodies_are_refused(client, body):
    assert (await client.post(BASE, json=body)).status_code == 422
