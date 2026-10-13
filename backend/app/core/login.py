"""One-password login for when the app listens on the network.

On this PC only (the default) nothing changes: there is no login.  When the app
listens on the network (``run_api_server.py --lan`` or ``--host <address>``) every
other device must sign in once with the lab password; the browser then keeps a
signed session cookie for 30 days.  Requests from this PC itself (loopback) never
need the password.

The password comes from ``LAB_PASSWORD`` (environment or backend/.env), else from
``data/user/lab_password.txt`` (gitignored).  When neither exists the first
network start writes a random one to that file.  Changing the password signs every
device out, because the cookie is signed with a key derived from it.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import time
from collections import deque
from pathlib import Path

from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PASSWORD_FILE = PROJECT_ROOT / "data" / "user" / "lab_password.txt"

COOKIE_NAME = "perfume_lab_session"
SESSION_SECONDS = 30 * 24 * 3600
FAILURE_WINDOW_SECONDS = 15 * 60
MAX_FAILURES = 10

LOGIN_PATH = "/login"
LOGOUT_PATH = "/logout"
# Reachable without signing in: the sign-in page itself, the health probe and the
# page's static files (the same files are public in the repository).
OPEN_PATHS = frozenset({LOGIN_PATH, "/health"})
OPEN_PREFIXES = ("/static/",)
# Pages a browser opens directly: send them to the sign-in page instead of a 401.
PAGE_PATHS = frozenset({"/", "/app"})


def login_wanted(bind_host: str, setting: bool | None) -> bool:
    """On when the app listens beyond this PC, unless LAB_LOGIN says otherwise."""
    if setting is not None:
        return setting
    name = bind_host.strip().strip("[]").lower()
    if name == "localhost":
        return False
    try:
        return not ipaddress.ip_address(name).is_loopback
    except ValueError:
        return True  # a host name other than localhost: reachable from the network


def resolve_password(
    configured: str = "", password_file: str | os.PathLike[str] = ""
) -> tuple[str, Path | None, bool]:
    """Return (password, file it lives in or None, whether it was just created)."""
    if configured.strip():
        return configured.strip(), None, False
    path = Path(password_file) if password_file else DEFAULT_PASSWORD_FILE
    if path.is_file():
        text = path.read_text(encoding="utf-8").strip()
        if text:
            return text, path, False
    password = secrets.token_urlsafe(9)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(password + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass  # Windows keeps the folder's permissions
    return password, path, True


def _signing_key(password: str) -> bytes:
    return hashlib.sha256(b"perfume-lab-session\0" + password.encode("utf-8")).digest()


def make_session_token(password: str, now: float | None = None) -> str:
    expires = int((now if now is not None else time.time()) + SESSION_SECONDS)
    body = str(expires)
    signature = hmac.new(_signing_key(password), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def session_token_valid(token: str, password: str, now: float | None = None) -> bool:
    body, dot, signature = token.partition(".")
    if not dot or not body.isdigit():
        return False
    expected = hmac.new(_signing_key(password), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    return int(body) > (now if now is not None else time.time())


def _is_loopback_client(scope: Scope) -> bool:
    client = scope.get("client")
    if not client:
        return False
    try:
        return ipaddress.ip_address(client[0]).is_loopback
    except ValueError:
        return False


def _cookie(headers: Headers) -> str:
    for part in headers.get("cookie", "").split(";"):
        name, _, value = part.strip().partition("=")
        if name == COOKIE_NAME:
            return value
    return ""


class LoginGuard:
    """ASGI middleware: sign-in page, session cookie check, failed-attempt limit."""

    def __init__(self, app: ASGIApp, *, enabled: bool, password: str = "") -> None:
        if enabled and not password:
            raise ValueError("LoginGuard needs a password when it is enabled")
        self.app = app
        self.enabled = enabled
        self.password = password
        self._failures: dict[str, deque[float]] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.enabled or scope["type"] != "http" or _is_loopback_client(scope):
            await self.app(scope, receive, send)
            return
        path = scope["path"]
        method = scope["method"]
        if path == LOGIN_PATH and method == "POST":
            response = await self._sign_in(Request(scope, receive))
        elif path == LOGIN_PATH and method in ("GET", "HEAD"):
            response = HTMLResponse(LOGIN_PAGE)
        elif path == LOGOUT_PATH and method == "POST":
            response = JSONResponse({"signed_in": False})
            response.delete_cookie(COOKIE_NAME, path="/")
        elif path in OPEN_PATHS or path.startswith(OPEN_PREFIXES) or self._signed_in(scope):
            await self.app(scope, receive, send)
            return
        elif path in PAGE_PATHS and method in ("GET", "HEAD"):
            response = RedirectResponse(LOGIN_PATH, status_code=303)
        else:
            response = JSONResponse(
                {"detail": "Sign in first: open /login on this device."},
                status_code=401,
                headers={"X-Lab-Login": "required"},
            )
        await response(scope, receive, send)

    def _signed_in(self, scope: Scope) -> bool:
        token = _cookie(Headers(scope=scope))
        return bool(token) and session_token_valid(token, self.password)

    def _client_key(self, scope: Scope) -> str:
        client = scope.get("client")
        return client[0] if client else "unknown"

    async def _sign_in(self, request: Request) -> Response:
        key = self._client_key(request.scope)
        now = time.time()
        failures = self._failures.setdefault(key, deque())
        while failures and failures[0] < now - FAILURE_WINDOW_SECONDS:
            failures.popleft()
        if len(failures) >= MAX_FAILURES:
            return JSONResponse(
                {"detail": "Too many wrong passwords. Wait 15 minutes, then try again."},
                status_code=429,
            )
        try:
            payload = json.loads(await request.body() or b"{}")
            given = payload.get("password", "") if isinstance(payload, dict) else ""
        except (ValueError, UnicodeDecodeError):
            given = ""
        if not isinstance(given, str) or not hmac.compare_digest(
            given.encode("utf-8"), self.password.encode("utf-8")
        ):
            failures.append(now)
            return JSONResponse({"detail": "Wrong password."}, status_code=401)
        failures.clear()
        response = JSONResponse({"signed_in": True})
        response.set_cookie(
            COOKIE_NAME,
            make_session_token(self.password, now),
            max_age=SESSION_SECONDS,
            path="/",
            httponly=True,
            samesite="strict",
        )
        return response


LOGIN_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Perfume Lab sign in</title>
<link rel="icon" href="data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAzMiAzMic+PHJlY3Qgd2lkdGg9JzMyJyBoZWlnaHQ9JzMyJyByeD0nOCcgZmlsbD0nIzFGNDQ2MicvPjx0ZXh0IHg9JzE2JyB5PScyMS41JyBmb250LWZhbWlseT0nR2VvcmdpYSxzZXJpZicgZm9udC1zaXplPScxNScgdGV4dC1hbmNob3I9J21pZGRsZScgZmlsbD0nI0ZGRkRGOCc+UEM8L3RleHQ+PC9zdmc+">
<style>
  body { font-family: system-ui, sans-serif; background: #f6f3ee; color: #222;
         display: flex; min-height: 100vh; align-items: center; justify-content: center;
         margin: 0; padding: 16px; box-sizing: border-box; }
  form { background: #fff; padding: 24px; border-radius: 12px; width: 100%; max-width: 320px;
         box-shadow: 0 2px 12px rgba(0,0,0,.08); }
  h1 { font-size: 1.2rem; margin: 0 0 16px; }
  input, button { width: 100%; font-size: 1rem; padding: 10px; margin-top: 8px;
                  box-sizing: border-box; border-radius: 8px; border: 1px solid #ccc; }
  button { background: #3a2f5b; color: #fff; border: none; cursor: pointer; }
  #error { color: #a01818; min-height: 1.2em; margin-top: 8px; font-size: .9rem; }
  @media (prefers-color-scheme: dark) {
    body { background: #18161c; color: #eee; }
    form { background: #24212b; }
    input { background: #18161c; color: #eee; border-color: #444; }
  }
</style>
</head>
<body>
<form id="login">
  <h1>Perfume Lab</h1>
  <label for="password">Lab password</label>
  <input id="password" type="password" autocomplete="current-password" autofocus required>
  <button type="submit">Sign in</button>
  <div id="error" role="alert"></div>
</form>
<script>
document.getElementById("login").addEventListener("submit", async (event) => {
  event.preventDefault();
  const error = document.getElementById("error");
  error.textContent = "";
  try {
    const response = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: document.getElementById("password").value }),
    });
    if (response.ok) { window.location.href = "/app"; return; }
    const body = await response.json().catch(() => ({}));
    error.textContent = body.detail || "Sign in failed (" + response.status + ").";
  } catch (problem) {
    error.textContent = "The lab app did not answer. Is it running?";
  }
});
</script>
</body>
</html>
"""
