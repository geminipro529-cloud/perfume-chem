"""The Lab page's own scripts: index.html loads lab/core.js first and lab/boot.js last.

Tests that look for a piece of the page's code read every page file joined in
load order, so code can move between page files without the test changing.
"""

import re
from dataclasses import dataclass
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "app" / "static"
INDEX_HTML = STATIC / "index.html"
FIRST_LAB_SCRIPT = 'src="/static/lab/core.js"'
_PAGE_SCRIPT = re.compile(r'<script src="/static/(lab/[a-z-]+\.js)" defer></script>')


def lab_script_paths(index_html: str) -> list[str]:
    """The page files index.html loads, in order, relative to /static/."""
    paths = _PAGE_SCRIPT.findall(index_html)
    assert paths, "index.html loads no lab/*.js page files"
    return paths


def read_lab_script() -> str:
    """The page files from disk, joined in the order index.html loads them."""
    paths = lab_script_paths(INDEX_HTML.read_text(encoding="utf-8"))
    return "\n".join((STATIC / path).read_text(encoding="utf-8") for path in paths)


@dataclass(frozen=True)
class LabScript:
    status_code: int
    text: str


async def get_lab_script(client) -> LabScript:
    """The page files as the server sends them; status_code is the first non-200 one, else 200."""
    page = await client.get("/app")
    responses = [await client.get(f"/static/{path}") for path in lab_script_paths(page.text)]
    failed = [response.status_code for response in responses if response.status_code != 200]
    return LabScript(failed[0] if failed else 200, "\n".join(response.text for response in responses))
