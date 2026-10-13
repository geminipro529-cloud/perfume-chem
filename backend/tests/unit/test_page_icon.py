"""Every Lab page names its icon, so browsers stop asking for a missing /favicon.ico (finding 8)."""

from __future__ import annotations

from pathlib import Path

from app.core.login import LOGIN_PAGE

INDEX = Path(__file__).resolve().parents[2] / "app" / "static" / "index.html"


def test_the_lab_page_and_the_sign_in_page_name_an_inline_icon() -> None:
    for page in (INDEX.read_text(encoding="utf-8"), LOGIN_PAGE):
        head = page.split("</head>", 1)[0]
        assert '<link rel="icon" href="data:image/svg+xml,' in head
