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


async def _stock(client, name, *, active_fraction=1.0, density_g_ml=None):
    material = await client.post(f"{API}/materials", json={"canonical_name": name})
    stock = await client.post(
        f"{API}/stocks",
        json={
            "material_id": material.json()["id"],
            "active_fraction": active_fraction,
            "fraction_basis": "mass_fraction",
            "initial_mass_g": 5.0,
            "density_g_ml": density_g_ml,
        },
    )
    assert stock.status_code == 201, stock.text
    return stock.json()["id"]


async def _formula_bottle(client, db_session, components):
    formula = await client.post(f"{API}/formulas", json={"name": "Lavender study"})
    version = await client.post(
        f"{API}/formulas/{formula.json()['id']}/versions",
        json={"brief": {}, "constraints": {}, "components": components},
    )
    assert version.status_code == 201, version.text
    batch = LabBatch(formula_version_id=version.json()["id"], batch_code="smell-compare-batch")
    db_session.add(batch)
    await db_session.flush()
    bottle = LabBottle(label="Lavender bottle", batch_id=batch.id)
    db_session.add(bottle)
    await db_session.commit()
    return bottle.id


async def _log(client, bottle_id, **body):
    response = await client.post(f"{API}/bottles/{bottle_id}/smell-log", json=body)
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_comparison_puts_the_models_leaders_beside_what_was_smelled(client, db_session):
    from app.services.scent_curve import ScentCurveRow, compute_scent_curve

    linalool = await _stock(client, "Linalool")
    hedione = await _stock(client, "Hedione", active_fraction=0.5)
    lavender = await _stock(client, "Lavender EO")
    iso = await _stock(client, "Iso E Super", density_g_ml=0.96)
    no_amount = await _stock(client, "Orris Butter")
    unknown = await _stock(client, "Zzz Unknown Material")
    bottle_id = await _formula_bottle(
        client,
        db_session,
        [
            {"stock_solution_id": linalool, "requested_mass_g": 0.7, "requested_volume_ul": 800},
            {"stock_solution_id": hedione, "requested_mass_g": 0.9, "requested_volume_ul": 900},
            {"stock_solution_id": lavender, "requested_mass_g": 0.45, "requested_volume_ul": 500},
            {"stock_solution_id": iso, "requested_mass_g": 0.576},
            {"stock_solution_id": no_amount, "requested_mass_g": 0.1},
            {"stock_solution_id": unknown, "requested_mass_g": 0.05, "requested_volume_ul": 50},
        ],
    )
    await _log(client, bottle_id, window="strip_10m", leads=["Linalool", "Hedione"], weak=["Iso E Super"], liking=6)
    await _log(client, bottle_id, window="strip_10m", leads=["linalool"], liking=9)
    await _log(client, bottle_id, window="strip_3h", leads=["Orris Butter"], words="powdery")
    await _log(client, bottle_id, window="skin_day1", leads=["Iso E Super"], liking=8)

    response = await client.get(f"{API}/bottles/{bottle_id}/smell-log/comparison")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["available"] is True
    assert "detection screen" in body["basis"]
    assert body["not_modelled"] == [
        {"name": "Orris Butter", "reason": "no volume, and no stock density to convert its mass"},
        {"name": "Zzz Unknown Material", "reason": "the model has no odour data for it"},
    ]
    assert [w["window"] for w in body["windows"]] == ["strip_10m", "strip_3h", "skin_day1"]
    rows = [
        ScentCurveRow(identity_name="Linalool", amount_ul=800, stock_fraction=1),
        ScentCurveRow(identity_name="Hedione", amount_ul=900, stock_fraction=0.5),
        ScentCurveRow(identity_name="Lavender EO", amount_ul=500, stock_fraction=1),
        ScentCurveRow(identity_name="Iso E Super", amount_ul=600, stock_fraction=1),
        ScentCurveRow(identity_name="Zzz Unknown Material", amount_ul=50, stock_fraction=1),
    ]
    expected = {
        frame["label"]: frame["top"]
        for frame in compute_scent_curve(rows, [("strip_10m", 600.0), ("strip_3h", 10800.0)])["windows"]
    }

    ten, three, day1 = body["windows"]
    assert ten["model_in_range"] is True
    assert ten["model_time_label"] == "10 min"
    assert ten["model_top"] == expected["strip_10m"] and 1 <= len(ten["model_top"]) <= 3
    assert ten["n_entries"] == 2
    assert ten["liking_mean"] == 7.5
    assert {item["name"]: item["count"] for item in ten["you_leads"]} == {"Linalool": 2, "Hedione": 1}
    assert ten["you_leads"][0] == {"name": "Linalool", "count": 2}
    assert ten["you_weak"] == [{"name": "Iso E Super", "count": 1}]
    top = ten["model_top"]
    assert ten["agreement"] == {
        "leads_the_model_also_had_on_top": [n for n in top if n in {"Linalool", "Hedione"}],
        "model_top_you_did_not_mark_leading": [n for n in top if n not in {"Linalool", "Hedione"}],
        "you_marked_weak_but_model_had_on_top": [n for n in top if n == "Iso E Super"],
        "leads_the_model_did_not_have_on_top": [n for n in ["Linalool", "Hedione"] if n not in top],
    }
    assert three["model_time_label"] == "3 h"
    assert three["model_top"] == expected["strip_3h"]
    assert three["liking_mean"] is None
    assert three["agreement"]["leads_the_model_did_not_have_on_top"] == ["Orris Butter"]
    assert day1["model_in_range"] is False
    assert day1["model_time_label"] is None
    assert day1["model_top"] == []
    assert day1["agreement"] is None
    assert day1["model_note"] == (
        "Beyond the model's range: its time curve stops at 4 h, so it says nothing about skin day 1."
    )
    assert day1["you_leads"] == [{"name": "Iso E Super", "count": 1}]
    assert day1["liking_mean"] == 8


@pytest.mark.asyncio
async def test_comparison_without_a_batch_is_unavailable_with_a_plain_reason(client):
    bottle_id = await _bottle(client, "Loose bottle")
    await _log(client, bottle_id, window="strip_1h", leads=["Iris"])

    response = await client.get(f"{API}/bottles/{bottle_id}/smell-log/comparison")
    missing = await client.get(f"{API}/bottles/nope/smell-log/comparison")

    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["reason"] == (
        "This bottle isn't linked to a batch, so there is no formula to model."
    )
    assert response.json()["windows"] == []
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_comparison_with_no_usable_amounts_says_so(client, db_session):
    stock = await _stock(client, "Orris Butter")
    bottle_id = await _formula_bottle(client, db_session, [{"stock_solution_id": stock, "requested_mass_g": 0.1}])

    body = (await client.get(f"{API}/bottles/{bottle_id}/smell-log/comparison")).json()

    assert body["available"] is False
    assert body["reason"] == "None of the formula's rows has an amount the model can use."
    assert body["not_modelled"][0]["name"] == "Orris Butter"


def test_agreement_sets_and_one_model_run_for_in_range_windows_only():
    from app.services.lab_service import SMELL_LOG_WINDOWS
    from app.services.smell_log_compare import smell_log_comparison_windows

    calls = []

    def run_model(windows):
        calls.append(windows)
        return {"strip_1h": ["Iris", "Hedione", "Ambrox"], "strip_3h": ["Ambrox"]}

    entries = [
        {"window": "skin_day7", "leads": ["Ambrox"], "weak": [], "liking": None},
        {"window": "strip_1h", "leads": ["iris", "Musk"], "weak": ["Ambrox"], "liking": 4},
        {"window": "strip_1h", "leads": ["Iris"], "weak": [], "liking": 7},
    ]

    blocks = smell_log_comparison_windows(entries, SMELL_LOG_WINDOWS, run_model)

    assert calls == [[("strip_1h", 3600.0)]]
    one_hour, day7 = blocks
    assert one_hour["you_leads"] == [{"name": "iris", "count": 2}, {"name": "Musk", "count": 1}]
    assert one_hour["liking_mean"] == 5.5
    assert one_hour["agreement"] == {
        "leads_the_model_also_had_on_top": ["Iris"],
        "model_top_you_did_not_mark_leading": ["Hedione", "Ambrox"],
        "you_marked_weak_but_model_had_on_top": ["Ambrox"],
        "leads_the_model_did_not_have_on_top": ["Musk"],
    }
    assert day7["window"] == "skin_day7"
    assert day7["model_in_range"] is False
    assert day7["agreement"] is None


async def _lavender_bottles(client, db_session, n):
    stocks = [
        await _stock(client, "Linalool"),
        await _stock(client, "Hedione", active_fraction=0.5),
        await _stock(client, "Lavender EO"),
        await _stock(client, "Iso E Super"),
    ]
    amounts = [800, 900, 500, 600]
    components = [
        {"stock_solution_id": stock, "requested_mass_g": amount / 1000, "requested_volume_ul": amount}
        for stock, amount in zip(stocks, amounts, strict=True)
    ]
    formula = await client.post(f"{API}/formulas", json={"name": "Lavender study"})
    version = await client.post(
        f"{API}/formulas/{formula.json()['id']}/versions",
        json={"brief": {}, "constraints": {}, "components": components},
    )
    assert version.status_code == 201, version.text
    bottles = []
    for index in range(n):
        batch = LabBatch(formula_version_id=version.json()["id"], batch_code=f"calibration-{index}")
        db_session.add(batch)
        await db_session.flush()
        bottle = LabBottle(label=f"Lavender bottle {index}", batch_id=batch.id)
        db_session.add(bottle)
        await db_session.flush()
        bottles.append(bottle.id)
    await db_session.commit()
    return bottles


def _lavender_ranking_at_one_hour():
    from app.services.scent_curve import ScentCurveRow, compute_scent_curve

    rows = [
        ScentCurveRow(identity_name="Linalool", amount_ul=800, stock_fraction=1),
        ScentCurveRow(identity_name="Hedione", amount_ul=900, stock_fraction=0.5),
        ScentCurveRow(identity_name="Lavender EO", amount_ul=500, stock_fraction=1),
        ScentCurveRow(identity_name="Iso E Super", amount_ul=600, stock_fraction=1),
    ]
    frame = compute_scent_curve(rows, [("strip_1h", 3600.0)])["windows"][0]
    return [m["name"] for m in sorted((m for m in frame["materials"] if m["share"]), key=lambda m: -m["share"])]


@pytest.mark.asyncio
async def test_calibration_waits_for_ten_bottles_and_adds_no_corrected_top(client, db_session):
    ranked = _lavender_ranking_at_one_hour()
    bottles = await _lavender_bottles(client, db_session, 3)
    for bottle_id in bottles:
        await _log(client, bottle_id, window="strip_1h", leads=[ranked[3]], weak=ranked[:3])
    await _log(client, bottles[0], window="skin_day1", leads=["Iso E Super"])
    loose = await _bottle(client, "Loose bottle")
    await _log(client, loose, window="strip_1h", leads=["Iris"])

    response = await client.get(f"{API}/smell-log/calibration")
    comparison = (await client.get(f"{API}/bottles/{bottles[0]}/smell-log/comparison")).json()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema"] == "smell-log-calibration-v1"
    assert body["evidence_class"] == "UNKNOWN"
    assert body["calibrated"] is False
    assert body["reason"] == "3 of 10 bottles logged"
    assert (body["n_bottles"], body["n_bottles_skipped"], body["n_entries"]) == (3, 1, 3)
    assert "not how strong" in body["basis"]
    one_hour, day1 = comparison["windows"]
    assert one_hour["corrected_top"] is None
    assert day1["corrected_top"] is None


@pytest.mark.asyncio
async def test_ten_bottles_where_the_nose_beats_the_model_add_corrected_top(client, db_session):
    ranked = _lavender_ranking_at_one_hour()
    assert len(ranked) == 4
    bottles = await _lavender_bottles(client, db_session, 10)
    for bottle_id in bottles:
        await _log(client, bottle_id, window="strip_1h", leads=[ranked[3]], weak=ranked[:3])
    await _log(client, bottles[0], window="skin_day7", leads=["Iso E Super"])

    body = (await client.get(f"{API}/smell-log/calibration")).json()
    comparison = (await client.get(f"{API}/bottles/{bottles[0]}/smell-log/comparison")).json()

    assert body["evidence_class"] == "EMPIRICALLY_CALIBRATED"
    assert body["reason"] is None
    assert (body["baseline_score"], body["corrected_score"]) == (-30, -10)
    assert {item["name"]: item["label"] for item in body["factors"]}[ranked[3]] == "×2.0"
    one_hour, day7 = comparison["windows"]
    assert one_hour["model_top"] == ranked[:3]
    assert one_hour["corrected_top"] == [ranked[0], ranked[1], ranked[3]]
    assert day7["corrected_top"] is None
