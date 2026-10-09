"""Server-side fixes from the Lab stress test: absurd masses, rate limit, stuck basket lock."""

import asyncio
import errno
import threading
import time

import pytest
from engine import inventory_baskets
from httpx import ASGITransport, AsyncClient

from app import main as app_main
from app.main import app

PREFIX = "/api/v1/lab"
BASKET = "/api/v1/lab/v2" + "/workbench/current-inventory/basket"
JSON = {"content-type": "application/json"}


# -- Fix 1: masses --


async def _stock_body(client):
    mat = await client.post(f"{PREFIX}/materials", json={"canonical_name": "Fix13 Mat"})
    assert mat.status_code in (200, 201), mat.text
    return {
        "material_id": mat.json()["id"],
        "active_fraction": 0.1,
        "fraction_basis": "mass_fraction",
        "initial_mass_g": 1.0,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("mass", [1e12, 10000.01])
async def test_absurd_masses_are_refused_naming_the_field(client, mass):
    body = await _stock_body(client)
    stock = await client.post(f"{PREFIX}/stocks", json={**body, "initial_mass_g": mass})
    bottle = await client.post(f"{PREFIX}/bottles", json={"label": "x", "initial_mass_g": mass})
    for response in (stock, bottle):
        assert response.status_code == 422
        assert "initial_mass_g" in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("token", [b"NaN", b"Infinity", b"-Infinity"])
async def test_non_finite_masses_are_refused(client, token):
    body = await _stock_body(client)
    bottle = await client.post(
        f"{PREFIX}/bottles",
        content=b'{"label":"x","initial_mass_g":' + token + b"}",
        headers=JSON,
    )
    stock_json = (
        '{"material_id":"%s","active_fraction":0.1,"fraction_basis":"mass_fraction",'
        '"initial_mass_g":' % body["material_id"]
    ).encode() + token + b"}"
    stock = await client.post(f"{PREFIX}/stocks", content=stock_json, headers=JSON)
    for response in (bottle, stock):
        assert response.status_code == 422
        assert "initial_mass_g" in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("mass", [0, 10000])
async def test_zero_and_the_cap_are_accepted(client, mass):
    body = await _stock_body(client)
    stock = await client.post(f"{PREFIX}/stocks", json={**body, "initial_mass_g": mass})
    bottle = await client.post(f"{PREFIX}/bottles", json={"label": "x", "initial_mass_g": mass})
    assert stock.status_code == 201, stock.text
    assert bottle.status_code == 201, bottle.text
    empty = await client.post(f"{PREFIX}/bottles", json={"label": "default"})
    assert empty.status_code == 201


# -- Fix 2: rate limit --


def _from(address):
    return AsyncClient(
        transport=ASGITransport(app=app, client=(address, 5000)), base_url="http://test"
    )


@pytest.fixture
def fresh_limiter():
    app_main._client_requests.clear()
    yield
    app_main._client_requests.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("address", ["127.0.0.1", "127.3.4.5", "::1"])
async def test_loopback_gets_600_per_window(fresh_limiter, address):
    async with _from(address) as local:
        codes = [(await local.get("/health")).status_code for _ in range(130)]
    assert 429 not in codes


@pytest.mark.asyncio
async def test_loopback_is_still_capped_at_600(fresh_limiter):
    async with _from("127.0.0.1") as local:
        codes = [(await local.get("/health")).status_code for _ in range(601)]
    assert codes[599] == 200
    assert codes[600] == 429


@pytest.mark.asyncio
async def test_static_files_and_the_page_are_not_limited(fresh_limiter):
    async with _from("203.0.113.9") as remote:
        codes = [(await remote.get("/static/lab.js")).status_code for _ in range(150)]
        assert 429 not in codes
        page = [(await remote.get("/app")).status_code for _ in range(150)]
        assert 429 not in page
        # Static requests are not counted either: the API budget is untouched.
        assert (await remote.get("/health")).status_code == 200


@pytest.mark.asyncio
async def test_other_clients_keep_120_per_window(fresh_limiter):
    async with _from("203.0.113.9") as remote:
        codes = [(await remote.get("/health")).status_code for _ in range(121)]
        last = await remote.get("/health")
    assert 429 not in codes[:120]
    assert codes[120] == 429
    assert last.json()["detail"].startswith("Rate limit exceeded. Max 120 requests")


# -- Fix 3: stuck basket-log lock --


@pytest.fixture
def basket_log(tmp_path, monkeypatch):
    path = tmp_path / "basket_events.jsonl"
    monkeypatch.setenv("PERFUME_BASKET_EVENT_PATH", str(path))
    return path


@pytest.mark.asyncio
async def test_stuck_lock_returns_503_then_recovers(client, basket_log, monkeypatch):
    fcntl = pytest.importorskip("fcntl")  # POSIX only; the user's Windows PC runs the other tests
    monkeypatch.setattr(inventory_baskets, "BASKET_LOCK_TIMEOUT_S", 0.2)
    first = await client.post(BASKET, json={"normalized_identity": "ambrox super", "basket": 1})
    assert first.status_code == 200
    before = basket_log.read_bytes()
    lock_path = basket_log.with_name(basket_log.name + ".lock")
    with lock_path.open("a+b") as holder:
        fcntl.flock(holder.fileno(), fcntl.LOCK_EX)
        started = time.monotonic()
        busy = await client.post(BASKET, json={"normalized_identity": "ambrox super", "basket": 2})
        assert time.monotonic() - started < 5
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
    assert busy.status_code == 503
    assert busy.json() == {
        "error": {
            "code": "BASKET_LOG_BUSY",
            "message": "Another save is still writing the basket log. Try again in a moment.",
        }
    }
    assert basket_log.read_bytes() == before
    again = await client.post(BASKET, json={"normalized_identity": "ambrox super", "basket": 2})
    assert again.status_code == 200


def test_windows_path_gives_up_after_the_timeout(tmp_path, monkeypatch):
    class FakeMsvcrt:
        LK_NBLCK = 2
        LK_UNLCK = 0
        calls = 0

        @classmethod
        def locking(cls, fd, mode, nbytes):
            cls.calls += 1
            if mode == cls.LK_NBLCK:
                raise OSError("locked")

    monkeypatch.setattr(inventory_baskets, "fcntl", None)
    monkeypatch.setattr(inventory_baskets, "msvcrt", FakeMsvcrt)
    monkeypatch.setattr(inventory_baskets, "BASKET_LOCK_TIMEOUT_S", 0.3)
    started = time.monotonic()
    with pytest.raises(inventory_baskets.BasketLogBusyError):
        with inventory_baskets._file_lock(tmp_path / "log.jsonl"):
            pass
    assert 0.25 <= time.monotonic() - started < 3
    assert FakeMsvcrt.calls >= 2


@pytest.mark.asyncio
async def test_waiting_on_the_lock_does_not_stall_other_requests(client, basket_log, monkeypatch):
    fcntl = pytest.importorskip("fcntl")
    monkeypatch.setattr(inventory_baskets, "BASKET_LOCK_TIMEOUT_S", 3.0)
    lock_path = basket_log.with_name(basket_log.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as holder:
        fcntl.flock(holder.fileno(), fcntl.LOCK_EX)
        save = asyncio.create_task(
            client.post(BASKET, json={"normalized_identity": "ambrox super", "basket": 4})
        )
        await asyncio.sleep(0.3)
        started = time.monotonic()
        health = await client.get("/health")
        answered_in = time.monotonic() - started
        still_waiting = not save.done()
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
    saved = await save
    assert health.status_code == 200
    assert answered_in < 1.0
    assert still_waiting
    assert saved.status_code == 200


def test_a_real_lock_error_is_raised_not_reported_as_busy(tmp_path, monkeypatch):
    class BrokenFcntl:
        LOCK_EX = 2
        LOCK_NB = 4
        LOCK_UN = 8

        @staticmethod
        def flock(fd, mode):
            raise OSError(errno.ENOLCK, "No locks available")

    monkeypatch.setattr(inventory_baskets, "fcntl", BrokenFcntl)
    monkeypatch.setattr(inventory_baskets, "BASKET_LOCK_TIMEOUT_S", 5.0)
    started = time.monotonic()
    with pytest.raises(OSError) as raised:
        with inventory_baskets._file_lock(tmp_path / "log.jsonl"):
            pass
    assert not isinstance(raised.value, inventory_baskets.BasketLogBusyError)
    assert raised.value.errno == errno.ENOLCK
    assert time.monotonic() - started < 1.0


def test_the_in_process_lock_also_gives_up_after_the_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr(inventory_baskets, "BASKET_LOCK_TIMEOUT_S", 0.2)
    log = tmp_path / "log.jsonl"
    outcome: list[BaseException | None] = []

    def save() -> None:
        try:
            inventory_baskets.record_basket_choice(
                normalized_identity="ambrox super", identity_name="Ambrox Super", basket=3, path=log
            )
            outcome.append(None)
        except BaseException as error:  # noqa: BLE001 - the test inspects it
            outcome.append(error)

    assert inventory_baskets._WRITE_LOCK.acquire(timeout=1)
    try:
        worker = threading.Thread(target=save, daemon=True)
        worker.start()
        worker.join(timeout=3)  # a regression would wait forever; fail instead of hanging
        finished = not worker.is_alive()
    finally:
        inventory_baskets._WRITE_LOCK.release()
    worker.join(timeout=3)
    assert finished, "the save waited past the timeout for the in-process lock"
    assert isinstance(outcome[0], inventory_baskets.BasketLogBusyError)
    assert not log.exists()
