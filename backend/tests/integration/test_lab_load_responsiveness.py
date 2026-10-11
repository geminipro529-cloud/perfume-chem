"""Load faults found by the 2026-10-11 stress test.

Slow workbench handlers used to run engine code on the event loop, so every
other request (and every open database transaction) waited for them; and each
connection gave up on a held SQLite write lock after 5 s, so a finished engine
job could fail to save under load.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

import pytest
from sqlalchemy import text

from app.api.v1.endpoints import lab_lifecycle

PREFIX = "/api/v1/lab"
SLOW_SECONDS = 1.0


async def test_app_database_connections_wait_for_a_held_write_lock() -> None:
    from app.db_session import engine

    async with engine.connect() as connection:
        busy_timeout = (await connection.execute(text("PRAGMA busy_timeout"))).scalar_one()

    # SQLite's own default is 5000 ms, which ran out under load.
    assert busy_timeout >= 30_000


def _chat_body() -> dict[str, Any]:
    return {
        "schema_version": "inventory-grounded-formula-chat-request-v2",
        "message": "a fresh green citrus cologne",
        "liquid_concentrate_ul_decimal": "6000",
        "max_materials": 20,
        "design_mode": "FAST_SKETCH",
        "variant_count": 1,
    }


@pytest.mark.parametrize("endpoint", ["formula-chat", "current-inventory"])
async def test_a_slow_workbench_request_does_not_hold_up_other_requests(
    client, monkeypatch, endpoint
) -> None:
    started = threading.Event()
    started_at: list[float] = []

    def slow(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        started_at.append(time.perf_counter())
        started.set()
        time.sleep(SLOW_SECONDS)  # stands in for seconds of engine work
        return {"slow": True}

    if endpoint == "formula-chat":
        monkeypatch.setattr(lab_lifecycle, "design_inventory_formula", slow)
        slow_request = client.post(f"{PREFIX}/v2/workbench/formula-chat", json=_chat_body())
    else:
        monkeypatch.setattr(lab_lifecycle, "materialize_personal_inventory", slow)
        monkeypatch.setattr(lab_lifecycle, "_workbench_inventory_payload", lambda payload: payload)
        slow_request = client.get(f"{PREFIX}/v2/workbench/current-inventory")

    async def health_while_slow_work_runs() -> float:
        while not started.is_set():
            await asyncio.sleep(0.01)
        response = await client.get("/health")
        assert response.status_code == 200
        return time.perf_counter() - started_at[0]

    slow_response, health_done_after = await asyncio.gather(
        slow_request, health_while_slow_work_runs()
    )

    assert slow_response.status_code == 200, slow_response.text
    assert slow_response.json() == {"slow": True}
    # Answered while the slow request was still working, not after it.
    assert health_done_after < SLOW_SECONDS / 2
