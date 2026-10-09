"""Drive the real Lab page in headless Chromium with no server.

The page is opened at a fake origin and every request is answered by
``page.route``: the static files come from ``app/static`` on disk and the
API calls come from small JSON fixtures. A test can override any API call.

Use it through the ``lab`` fixture in ``tests/integration/conftest.py``::

    pytest.importorskip("playwright.sync_api")

    def test_something(lab):
        lab.open()
        lab.respond("POST", "/bottles", status=201, json={"id": "b1"})
        lab.fail("GET", "/bottles")      # abort the request like a dropped network
        ...

Playwright is optional. Test modules that use the fixture start with
``pytest.importorskip("playwright.sync_api")`` so machines without it skip.
"""

from __future__ import annotations

import copy
import glob
import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

STATIC_DIR = Path(__file__).resolve().parents[2] / "app" / "static"
ORIGIN = "http://lab.test"
APP_URL = f"{ORIGIN}/app"
API_PREFIX = "/api/v1/lab"
BOOT_DONE = "Inventory and ledger refreshed."

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json",
}

# The GETs the page makes at start-up (refresh() in lab.js), with minimal bodies.
DEFAULT_GETS: dict[str, Any] = {
    "/dashboard": {"counts": {}, "warnings": []},
    "/materials": [],
    "/stocks": [],
    "/formulas": [],
    "/bottles": [],
    "/experiments": [],
    "/v2/workbench/formula-library": {"sources": []},
    "/v2/workbench/current-inventory": {"stocks": [], "counts": {}},
}

# Records every text the #status line shows, in order, so a test can see a
# message that a later one replaced.
_STATUS_RECORDER = """
(() => {
  window.__statusHistory = [];
  let last = null;
  new MutationObserver(() => {
    const node = document.getElementById("status");
    if (!node) return;
    const entry = { text: node.textContent, error: node.classList.contains("is-error") };
    if (last && last.text === entry.text && last.error === entry.error) return;
    last = entry;
    window.__statusHistory.push(entry);
  }).observe(document, { subtree: true, childList: true, characterData: true, attributes: true });
})();
"""

Handler = Callable[[Any, Any], None]


def chromium_executable(playwright: Any) -> str | None:
    """Return a Chromium binary to launch, or None to use Playwright's default.

    Uses the bundled browser when its revision matches this Playwright version,
    otherwise any Chromium under PLAYWRIGHT_BROWSERS_PATH.
    """
    if os.path.exists(playwright.chromium.executable_path):
        return None
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
    for pattern in ("chromium-*/chrome-linux*/chrome", "chromium_headless_shell-*/chrome-linux*/headless_shell"):
        found = sorted(glob.glob(os.path.join(root, pattern)))
        if found:
            return found[-1]
    return None


class LabPage:
    """One browser page showing the Lab, with every request answered locally."""

    def __init__(self, page: Any) -> None:
        self.page = page
        self.overrides: dict[tuple[str, str], Handler] = {}
        self.requests: list[tuple[str, str]] = []
        self.unexpected: list[tuple[str, str]] = []
        self.page_errors: list[str] = []
        page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        page.add_init_script(_STATUS_RECORDER)
        page.route("**/*", self._route)

    # -- configuring API answers -------------------------------------------
    def on(self, method: str, path: str, handler: Handler) -> None:
        """Answer ``method path`` (path below /api/v1/lab) with ``handler(route, request)``."""
        self.overrides[(method.upper(), path)] = handler

    def respond(self, method: str, path: str, *, status: int = 200, json: Any = None) -> None:
        body = json

        def handler(route: Any, _request: Any) -> None:
            route.fulfill(status=status, content_type="application/json", body=_dumps(body))

        self.on(method, path, handler)

    def fail(self, method: str, path: str, error: str = "failed") -> None:
        """Make ``method path`` fail at the network level (like a dropped connection)."""
        self.on(method, path, lambda route, _request: route.abort(error))

    def reset(self, method: str, path: str) -> None:
        self.overrides.pop((method.upper(), path), None)

    # -- driving the page --------------------------------------------------
    def open(self, hash_: str = "", *, wait_for_boot: bool = True) -> None:
        self.page.goto(APP_URL + hash_)
        if wait_for_boot:
            self.wait_for_status(BOOT_DONE)

    def reload(self, *, wait_for_boot: bool = True) -> None:
        self.page.reload()
        if wait_for_boot:
            self.wait_for_status(BOOT_DONE)

    def status_history(self) -> list[dict[str, Any]]:
        return self.page.evaluate("window.__statusHistory || []")

    def wait_for_status(self, text: str, timeout: float = 10000) -> None:
        """Wait until the #status line has shown ``text`` at some point."""
        self.page.wait_for_function(
            "(text) => (window.__statusHistory || []).some((entry) => entry.text === text)",
            arg=text,
            timeout=timeout,
        )

    # -- routing -----------------------------------------------------------
    def _route(self, route: Any, request: Any) -> None:
        url = urlsplit(request.url)
        if f"{url.scheme}://{url.netloc}" != ORIGIN:
            route.abort("blockedbyclient")
            return
        path = url.path
        if path == "/app":
            self._file(route, STATIC_DIR / "index.html")
        elif path.startswith("/static/"):
            self._file(route, STATIC_DIR / path[len("/static/"):])
        elif path.startswith(API_PREFIX + "/"):
            self._api(route, request, path[len(API_PREFIX):] + (f"?{url.query}" if url.query else ""))
        else:
            route.fulfill(status=404, body="not found")

    def _file(self, route: Any, file: Path) -> None:
        file = file.resolve()
        if STATIC_DIR not in file.parents or not file.is_file():
            route.fulfill(status=404, body="not found")
            return
        route.fulfill(
            status=200,
            content_type=CONTENT_TYPES.get(file.suffix, "application/octet-stream"),
            body=file.read_bytes(),
        )

    def _api(self, route: Any, request: Any, path: str) -> None:
        key = (request.method.upper(), path)
        self.requests.append(key)
        if key in self.overrides:
            self.overrides[key](route, request)
        elif key[0] == "GET" and path in DEFAULT_GETS:
            route.fulfill(status=200, content_type="application/json", body=_dumps(copy.deepcopy(DEFAULT_GETS[path])))
        else:
            self.unexpected.append(key)
            route.fulfill(status=404, content_type="application/json", body=_dumps({"detail": f"No test fixture for {key[0]} {path}"}))


def _dumps(value: Any) -> str:
    return json.dumps(value)
