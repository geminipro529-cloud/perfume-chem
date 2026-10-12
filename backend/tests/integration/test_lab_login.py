"""Direction 4: one-password login when the app listens on the network."""

import httpx
import pytest
from fastapi import FastAPI

from app.core import login
from app.core.login import COOKIE_NAME, LoginGuard, login_wanted, resolve_password
from app.core.request_guard import LocalRequestGuard
from app.main import app as real_app

PASSWORD = "bench-password-7"
PHONE = ("192.168.1.30", 51000)
THIS_PC = ("127.0.0.1", 51000)


def _app(enabled: bool = True) -> FastAPI:
    app = FastAPI()

    @app.get("/app")
    async def page():
        return {"page": "lab"}

    @app.get("/api/v1/lab/materials")
    async def materials():
        return [{"canonical_name": "Iso E Super"}]

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    app.add_middleware(LoginGuard, enabled=enabled, password=PASSWORD if enabled else "")
    return app


def _client(app: FastAPI, client=PHONE) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=client)
    return httpx.AsyncClient(transport=transport, base_url="http://192.168.1.10:8000")


async def _sign_in(client: httpx.AsyncClient, password: str = PASSWORD) -> httpx.Response:
    return await client.post("/login", json={"password": password})


@pytest.mark.asyncio
async def test_signed_out_phone_is_refused_and_sent_to_the_sign_in_page():
    async with _client(_app()) as client:
        api = await client.get("/api/v1/lab/materials")
        assert api.status_code == 401
        assert api.headers["X-Lab-Login"] == "required"
        assert "Iso E Super" not in api.text
        page = await client.get("/app")
        assert page.status_code == 303
        assert page.headers["location"] == "/login"
        sign_in_page = await client.get("/login")
        assert sign_in_page.status_code == 200
        assert 'type="password"' in sign_in_page.text
        assert (await client.get("/health")).status_code == 200


@pytest.mark.asyncio
async def test_right_password_gives_a_cookie_that_opens_the_app_and_api():
    async with _client(_app()) as client:
        response = await _sign_in(client)
        assert response.status_code == 200
        cookie = response.headers["set-cookie"]
        assert cookie.startswith(f"{COOKIE_NAME}=")
        assert "HttpOnly" in cookie
        assert "SameSite=strict" in cookie
        assert (await client.get("/app")).json() == {"page": "lab"}
        materials = await client.get("/api/v1/lab/materials")
        assert materials.status_code == 200
        assert materials.json()[0]["canonical_name"] == "Iso E Super"
        await client.post("/logout")
        assert (await client.get("/api/v1/lab/materials")).status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"password": "wrong"}, {"password": 7}, {}, "text"])
async def test_wrong_or_malformed_password_gets_no_cookie(body):
    async with _client(_app()) as client:
        response = await client.post("/login", json=body)
        assert response.status_code == 401
        assert "set-cookie" not in response.headers
        assert (await client.get("/api/v1/lab/materials")).status_code == 401


@pytest.mark.asyncio
async def test_forged_expired_or_old_password_cookie_is_refused():
    now = 1_900_000_000.0
    valid = login.make_session_token(PASSWORD, now)
    assert login.session_token_valid(valid, PASSWORD, now)
    assert not login.session_token_valid(valid, PASSWORD, now + login.SESSION_SECONDS + 1)
    assert not login.session_token_valid(valid, "a-new-password", now)
    expires, _, signature = valid.partition(".")
    assert not login.session_token_valid(f"{int(expires) + 999}.{signature}", PASSWORD, now)
    async with _client(_app()) as client:
        for token in ("", "abc", f"{expires}.{'0' * 64}", "9999999999.zz"):
            client.cookies.set(COOKIE_NAME, token)
            assert (await client.get("/api/v1/lab/materials")).status_code == 401


@pytest.mark.asyncio
async def test_ten_wrong_passwords_lock_that_device_out_for_a_while():
    async with _client(_app()) as client:
        for _ in range(login.MAX_FAILURES):
            assert (await _sign_in(client, "guess")).status_code == 401
        locked = await _sign_in(client)  # even the right one, until the window passes
        assert locked.status_code == 429
        assert "set-cookie" not in locked.headers


@pytest.mark.asyncio
async def test_this_pc_never_needs_the_password():
    async with _client(_app(), client=THIS_PC) as client:
        assert (await client.get("/api/v1/lab/materials")).status_code == 200
        assert (await client.get("/app")).status_code == 200


@pytest.mark.asyncio
async def test_login_off_leaves_every_device_open():
    async with _client(_app(enabled=False)) as client:
        assert (await client.get("/api/v1/lab/materials")).status_code == 200


def test_login_is_on_exactly_when_the_app_listens_beyond_this_pc():
    assert not login_wanted("127.0.0.1", None)
    assert not login_wanted("localhost", None)
    assert not login_wanted("::1", None)
    assert login_wanted("0.0.0.0", None)
    assert login_wanted("192.168.1.20", None)
    assert login_wanted("lab-pc.local", None)
    assert not login_wanted("0.0.0.0", False)
    assert login_wanted("127.0.0.1", True)


def test_password_comes_from_setting_then_file_then_is_created(tmp_path):
    path = tmp_path / "user" / "lab_password.txt"
    assert resolve_password("  set-in-env  ", path) == ("set-in-env", None, False)
    assert not path.exists()
    created, where, new = resolve_password("", path)
    assert (where, new) == (path, True)
    assert path.read_text(encoding="utf-8").strip() == created
    assert resolve_password("", path) == (created, path, False)


def test_the_real_app_runs_the_guard_and_leaves_it_off_on_this_pc():
    guards = [m for m in real_app.user_middleware if m.cls is LoginGuard]
    assert len(guards) == 1
    assert guards[0].options["enabled"] is False  # tests run with API_BIND_HOST=127.0.0.1


@pytest.mark.asyncio
async def test_sign_in_from_the_phone_passes_the_request_guard_on_a_lan_run():
    # As in app.main: the request guard runs first, then the login guard.
    app = _app()
    app.add_middleware(LocalRequestGuard, bind_host="0.0.0.0")
    async with _client(app) as client:
        response = await client.post(
            "/login",
            json={"password": PASSWORD},
            headers={"Origin": "http://192.168.1.10:8000"},
        )
        assert response.status_code == 200
        assert (await client.get("/api/v1/lab/materials")).status_code == 200
