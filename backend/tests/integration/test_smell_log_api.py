"""Smell log: strip and skin tests of a bottle, saved as applications and observations."""

import pytest
from sqlalchemy import func, select

from app.models.lab import (
    LabApplication,
    LabBatch,
    LabBottle,
    LabExperiment,
    LabObservation,
    LabSample,
)

API = "/api/v1/lab"


async def _bottle(client, label="Iris trial"):
    response = await client.post(f"{API}/bottles", json={"label": label, "initial_mass_g": 0})
    assert response.status_code == 201
    return response.json()["id"]


async def _material_stock(client, name):
    material = await client.post(f"{API}/materials", json={"canonical_name": name})
    stock = await client.post(
        f"{API}/stocks",
        json={
            "material_id": material.json()["id"],
            "active_fraction": 0.1,
            "fraction_basis": "mass_fraction",
            "initial_mass_g": 5.0,
        },
    )
    assert stock.status_code == 201
    return stock.json()["id"]


async def _count(db_session, model):
    return int(await db_session.scalar(select(func.count()).select_from(model)) or 0)


@pytest.mark.asyncio
async def test_two_entries_reuse_one_experiment_and_list_newest_first(client, db_session):
    bottle_id = await _bottle(client)

    first = await client.post(
        f"{API}/bottles/{bottle_id}/smell-log",
        json={
            "window": "strip_10m",
            "leads": ["Iris", " Hedione "],
            "weak": ["Ambrox"],
            "liking": 7,
            "words": " powdery, a bit sharp ",
            "logged_at": "2026-10-12T10:00:00+00:00",
        },
    )
    second = await client.post(
        f"{API}/bottles/{bottle_id}/smell-log",
        json={"window": "skin_day1", "liking": 9, "logged_at": "2026-10-13T09:00:00+02:00"},
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["leads"] == ["Iris", "Hedione"]
    assert first.json()["words"] == "powdery, a bit sharp"
    assert first.json()["logged_at"] == "2026-10-12T10:00:00+00:00"
    assert await _count(db_session, LabExperiment) == 1
    assert await _count(db_session, LabSample) == 1
    assert await _count(db_session, LabApplication) == 2
    assert await _count(db_session, LabObservation) == 2

    experiment = (await db_session.execute(select(LabExperiment))).scalar_one()
    assert experiment.name == "Smell log: Iris trial"
    assert experiment.protocol_json == {"kind": "smell_log", "bottle_id": bottle_id}
    sample = (await db_session.execute(select(LabSample))).scalar_one()
    assert sample.blind_code == "smell-log"
    observation = await db_session.get(LabObservation, first.json()["id"])
    assert observation.elapsed_seconds == 600
    assert observation.observations_json == {
        "kind": "smell_log",
        "schema": "smell-log-v1",
        "window": "strip_10m",
        "surface": "strip",
        "leads": ["Iris", "Hedione"],
        "weak": ["Ambrox"],
        "liking": 7,
        "words": "powdery, a bit sharp",
    }
    application = await db_session.get(LabApplication, observation.application_id)
    assert application.applied_at.isoformat() == "2026-10-12T09:50:00+00:00"
    assert application.context_json == {"kind": "smell_log", "surface": "strip"}
    assert application.dose_json == {}

    listed = await client.get(f"{API}/bottles/{bottle_id}/smell-log")
    assert listed.status_code == 200
    body = listed.json()
    assert [window["key"] for window in body["windows"]] == [
        "strip_10m", "strip_1h", "strip_3h", "skin_day1", "skin_day7",
    ]
    assert body["windows"][3] == {
        "key": "skin_day1", "label": "Skin day 1", "surface": "skin", "seconds": 86400,
    }
    assert body["rows"] == []
    assert [entry["window"] for entry in body["entries"]] == ["skin_day1", "strip_10m"]
    assert body["entries"][0]["logged_at"] == "2026-10-13T07:00:00+00:00"
    assert body["entries"][0]["surface"] == "skin"
    assert body["entries"][0]["leads"] == []
    assert body["entries"][1] == first.json()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"window": "strip_2h", "liking": 5}, "Unknown smell log window"),
        ({"window": "strip_1h", "liking": 11}, "liking must be"),
        ({"window": "strip_1h", "liking": 0}, "liking must be"),
        ({"window": "strip_1h", "leads": ["Iris"], "weak": ["iris "]}, "cannot both lead and be weak"),
        ({"window": "strip_1h"}, "needs leads, weak, a liking or words"),
        ({"window": "strip_1h", "words": "   "}, "needs leads, weak, a liking or words"),
        ({"window": "strip_1h", "leads": [""]}, "non-empty"),
        ({"window": "strip_1h", "leads": [f"m{i}" for i in range(13)]}, "at most 12"),
        ({"window": "strip_1h", "words": "x" * 281}, "at most 280"),
        ({"window": "strip_1h", "liking": 5, "logged_at": "2026-10-12T10:00:00"}, "timezone-aware"),
    ],
)
async def test_invalid_entries_are_rejected_and_save_nothing(client, db_session, payload, message):
    bottle_id = await _bottle(client)

    response = await client.post(f"{API}/bottles/{bottle_id}/smell-log", json=payload)

    assert response.status_code == 400, response.text
    assert message in response.json()["detail"]
    assert await _count(db_session, LabExperiment) == 0
    assert await _count(db_session, LabObservation) == 0


@pytest.mark.asyncio
async def test_wrongly_typed_or_extra_fields_are_422(client):
    bottle_id = await _bottle(client)

    wrong_type = await client.post(
        f"{API}/bottles/{bottle_id}/smell-log", json={"window": "strip_1h", "liking": "lots"}
    )
    extra = await client.post(
        f"{API}/bottles/{bottle_id}/smell-log", json={"window": "strip_1h", "liking": 5, "dose": 1}
    )

    assert wrong_type.status_code == 422
    assert extra.status_code == 422


@pytest.mark.asyncio
async def test_unknown_bottle_is_404(client):
    posted = await client.post(f"{API}/bottles/nope/smell-log", json={"window": "strip_1h", "liking": 5})
    listed = await client.get(f"{API}/bottles/nope/smell-log")

    assert posted.status_code == 404
    assert listed.status_code == 404


@pytest.mark.asyncio
async def test_rows_come_from_the_bottles_formula_version_in_position_order(client, db_session):
    iris = await _material_stock(client, "Orris Butter")
    hedione = await _material_stock(client, "Hedione")
    formula = await client.post(f"{API}/formulas", json={"name": "Iris Cathedral"})
    version = await client.post(
        f"{API}/formulas/{formula.json()['id']}/versions",
        json={
            "brief": {"identity": "iris and incense"},
            "constraints": {},
            "components": [
                {"stock_solution_id": hedione, "requested_mass_g": 0.2},
                {"stock_solution_id": iris, "requested_mass_g": 0.1},
            ],
        },
    )
    assert version.status_code == 201, version.text
    batch = LabBatch(formula_version_id=version.json()["id"], batch_code="smell-log-batch")
    db_session.add(batch)
    await db_session.flush()
    bottle = LabBottle(label="Batch bottle", batch_id=batch.id)
    db_session.add(bottle)
    await db_session.commit()
    plain_bottle_id = await _bottle(client, "No formula")

    with_formula = await client.get(f"{API}/bottles/{bottle.id}/smell-log")
    without_formula = await client.get(f"{API}/bottles/{plain_bottle_id}/smell-log")

    assert with_formula.json()["rows"] == ["Hedione", "Orris Butter"]
    assert without_formula.json()["rows"] == []
    assert without_formula.json()["entries"] == []
