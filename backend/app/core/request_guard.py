"""Refuse requests that another web site could make through Kenny's browser.

The app has no login, so two checks stand in for one:

* Host check (DNS rebinding): the Host header must name this PC as the app is
  served -- 127.0.0.1, localhost or ::1, plus the bind address when the launcher
  listens on the network (``--lan`` / ``--host``).  A page whose own name was
  re-pointed at this PC still sends its own name, so it gets 400.
* Cross-site writes: a POST, PUT, PATCH or DELETE whose Origin header is not the
  app's own origin gets 403, and one that carries a body must send it as
  ``application/json`` (415 otherwise).  A browser sends JSON across sites only
  after a CORS preflight, which ``CORS_ORIGINS`` decides, so a page can no longer
  slip a write through as a "simple" request with no Content-Type.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Iterable
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
ALL_INTERFACES = frozenset({"0.0.0.0", "::", ""})
STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _ip(name: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(name)
    except ValueError:
        return None


def _normal_name(name: str) -> str:
    return name.strip().strip("[]").rstrip(".").lower()


def split_host(value: str) -> tuple[str, int | None] | None:
    """``"[::1]:8000"`` -> ``("::1", 8000)``; None when the value is malformed."""
    value = value.strip()
    if not value:
        return None
    if value.startswith("["):
        name, bracket, rest = value[1:].partition("]")
        if not bracket or (rest and not rest.startswith(":")):
            return None
        port_text = rest[1:]
    elif value.count(":") > 1:
        return None  # an IPv6 address must be bracketed in a Host header
    else:
        name, _, port_text = value.partition(":")
    port = None
    if port_text:
        if not port_text.isdigit():
            return None
        port = int(port_text)
    name = _normal_name(name)
    return (name, port) if name else None


class HostPolicy:
    """Which Host names the app answers."""

    def __init__(self, bind_host: str = "127.0.0.1", extra_hosts: Iterable[str] = ()) -> None:
        names = set(LOOPBACK_HOSTS)
        names.update(_normal_name(host) for host in extra_hosts if _normal_name(host))
        bind = _normal_name(bind_host)
        # Listening on every interface (--lan): other devices reach the PC by one of
        # its addresses, which can change while the app runs, or by its name.  An
        # address cannot be re-pointed by DNS, so any IP address is allowed.
        self.any_ip_address = bind in ALL_INTERFACES
        if self.any_ip_address:
            for name in (socket.gethostname(), socket.getfqdn()):
                if _normal_name(name):
                    names.add(_normal_name(name))
        elif bind not in LOOPBACK_HOSTS:
            bind_address = _ip(bind)
            if bind_address is None or not bind_address.is_loopback:
                names.add(bind)
        self.names = frozenset(names)

    def allows(self, name: str) -> bool:
        if name in self.names:
            return True
        return self.any_ip_address and _ip(name) is not None


def _origin_key(scheme: str, name: str, port: int | None) -> tuple[str, str, int]:
    default = 443 if scheme == "https" else 80
    return scheme, name, port if port is not None else default


def _parse_origin(origin: str) -> tuple[str, str, int] | None:
    try:
        parts = urlsplit(origin.strip())
        port = parts.port
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    return _origin_key(parts.scheme, _normal_name(parts.hostname), port)


def loopback_origins(origins: Iterable[str]) -> frozenset[tuple[str, str, int]]:
    """The entries of CORS_ORIGINS that point at this PC (e.g. a dev front end)."""
    keys = set()
    for origin in origins:
        key = _parse_origin(origin)
        if key is None:
            continue
        address = _ip(key[1])
        if key[1] == "localhost" or (address is not None and address.is_loopback):
            keys.add(key)
    return frozenset(keys)


def _has_body(headers: Headers) -> bool:
    if "transfer-encoding" in headers:
        return True
    length = headers.get("content-length")
    return length is not None and length.strip() not in ("", "0")


def _media_type(headers: Headers) -> str:
    return headers.get("content-type", "").split(";", 1)[0].strip().lower()


class LocalRequestGuard:
    """ASGI middleware applying the Host, Origin and Content-Type checks."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        bind_host: str = "127.0.0.1",
        extra_hosts: Iterable[str] = (),
        cors_origins: Iterable[str] = (),
    ) -> None:
        self.app = app
        self.hosts = HostPolicy(bind_host, extra_hosts)
        self.trusted_origins = loopback_origins(cors_origins)

    def refusal(self, method: str, headers: Headers) -> PlainTextResponse | None:
        host = split_host(headers.get("host", ""))
        if host is None or not self.hosts.allows(host[0]):
            return PlainTextResponse(
                "Refused: this app only answers requests addressed to this PC.",
                status_code=400,
            )
        if method.upper() not in STATE_CHANGING_METHODS:
            return None
        origin = headers.get("origin")
        if origin is not None:
            key = _parse_origin(origin)
            own = _origin_key("http", host[0], host[1])
            if key is None or (key != own and key not in self.trusted_origins):
                return PlainTextResponse(
                    "Refused: changes are accepted only from this app's own pages.",
                    status_code=403,
                )
        if _has_body(headers) and _media_type(headers) != "application/json":
            return PlainTextResponse(
                "Refused: send the request body as JSON (Content-Type: application/json).",
                status_code=415,
            )
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            response = self.refusal(scope["method"], Headers(scope=scope))
            if response is not None:
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
