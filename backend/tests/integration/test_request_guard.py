"""SEC-02/SEC-03: other web sites cannot write through Kenny's browser or rebind the app."""

import socket

import pytest
from starlette.datastructures import Headers

from app.core.request_guard import LocalRequestGuard

MATERIALS = "/api/v1/lab/materials"
LOCAL = {"Host": "127.0.0.1:8000"}
OWN_ORIGIN = "http://127.0.0.1:8000"
EVIL = "https://evil.example"
BODY = b'{"canonical_name": "Injected By Webpage"}'


async def _material_names(client):
    response = await client.get(MATERIALS, headers=LOCAL)
    assert response.status_code == 200
    return [row["canonical_name"] for row in response.json()]


@pytest.mark.asyncio
async def test_blob_post_from_another_site_is_refused(client):
    # fetch(..., {mode: "no-cors", body: new Blob([json])}): no Content-Type, foreign Origin.
    response = await client.post(MATERIALS, content=BODY, headers={**LOCAL, "Origin": EVIL})
    assert response.status_code == 403
    assert response.text == "Refused: changes are accepted only from this app's own pages."
    assert "Injected By Webpage" not in await _material_names(client)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content_type", [None, "text/plain", "application/x-www-form-urlencoded"]
)
async def test_body_that_is_not_json_is_refused_with_415(client, content_type):
    headers = dict(LOCAL)
    if content_type:
        headers["Content-Type"] = content_type
    response = await client.post(MATERIALS, content=BODY, headers=headers)
    assert response.status_code == 415
    assert "application/json" in response.text
    assert "Injected By Webpage" not in await _material_names(client)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "host, origin",
    [
        ("127.0.0.1:8000", OWN_ORIGIN),
        ("localhost:8000", "http://localhost:8000"),
        ("[::1]:8000", "http://[::1]:8000"),
        ("127.0.0.1:8000", None),
    ],
)
async def test_json_from_the_apps_own_page_is_accepted(client, host, origin):
    headers = {"Host": host, **({"Origin": origin} if origin else {})}
    response = await client.post(
        MATERIALS, json={"canonical_name": f"Guard {host} {origin}"}, headers=headers
    )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_multipart_is_refused_since_no_route_takes_uploads(client):
    files = {"file": ("packet.json", BODY, "application/json")}
    same_site = await client.post(
        "/api/v1/lab/import", files=files, headers={**LOCAL, "Origin": OWN_ORIGIN}
    )
    cross_site = await client.post(
        "/api/v1/lab/import", files=files, headers={**LOCAL, "Origin": EVIL}
    )
    assert same_site.status_code == 415
    assert cross_site.status_code == 403


@pytest.mark.asyncio
async def test_bodiless_write_from_another_site_is_refused(client):
    response = await client.delete(f"{MATERIALS}/anything", headers={**LOCAL, "Origin": EVIL})
    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "host", ["rebind.attacker.example:8761", "rebind.attacker.example", ""]
)
async def test_rebound_host_cannot_read_the_export(client, host):
    response = await client.get("/api/v1/lab/export", headers={"Host": host})
    assert response.status_code == 400
    assert response.text == "Refused: this app only answers requests addressed to this PC."


@pytest.mark.asyncio
@pytest.mark.parametrize("host", ["127.0.0.1:8000", "localhost:8000", "[::1]:8000", "localhost"])
async def test_loopback_hosts_are_answered(client, host):
    response = await client.get("/health", headers={"Host": host})
    assert response.status_code == 200


def _refusal(guard, method="GET", **headers):
    response = guard.refusal(method, Headers(headers=headers))
    return None if response is None else response.status_code


def _guard(**options):
    return LocalRequestGuard(lambda scope, receive, send: None, **options)


def test_default_answers_only_loopback_names():
    guard = _guard()
    assert _refusal(guard, host="127.0.0.1:8000") is None
    assert _refusal(guard, host="192.168.1.20:8000") == 400
    assert _refusal(guard, host="testserver") == 400  # tests add it; production does not
    assert _refusal(guard, host="127.0.0.2:8000") == 400


def test_lan_bind_answers_this_pcs_addresses_and_name_but_not_rebinding():
    guard = _guard(bind_host="0.0.0.0")
    assert _refusal(guard, host="192.168.1.20:8000") is None
    assert _refusal(guard, host=f"{socket.gethostname()}:8000") is None
    assert _refusal(guard, host="rebind.attacker.example:8000") == 400
    lan = {"host": "192.168.1.20:8000"}
    assert _refusal(guard, "POST", origin="http://192.168.1.20:8000", **lan) is None
    assert _refusal(guard, "POST", origin="http://192.168.1.99:8000", **lan) == 403


def test_explicit_host_bind_answers_that_address_only():
    guard = _guard(bind_host="192.168.1.20")
    assert _refusal(guard, host="192.168.1.20:8000") is None
    assert _refusal(guard, host="10.0.0.7:8000") == 400


def test_only_loopback_cors_origins_may_write():
    guard = _guard(cors_origins=["http://localhost:5173", "https://example.org"])
    local = {"host": "127.0.0.1:8000"}
    assert _refusal(guard, "POST", origin="http://localhost:5173", **local) is None
    assert _refusal(guard, "POST", origin="https://example.org", **local) == 403
    assert _refusal(guard, "POST", origin="null", **local) == 403


def test_bodiless_write_needs_no_content_type():
    guard = _guard()
    local = {"host": "127.0.0.1:8000"}
    assert _refusal(guard, "POST", **local) is None
    assert _refusal(guard, "POST", **{"content-length": "0"}, **local) is None
    assert _refusal(guard, "POST", **{"content-length": "2"}, **local) == 415
    assert _refusal(guard, "PUT", **{"transfer-encoding": "chunked"}, **local) == 415
