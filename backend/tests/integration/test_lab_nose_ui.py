"""The Your nose page is wired into the Lab: nav, view, scripts, and text-only rendering."""

from pathlib import Path

STATIC = Path(__file__).resolve().parents[2] / "app" / "static"


def test_the_nose_view_its_scripts_and_the_page_load_hook_are_wired():
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    assert '<button class="nav-item" data-view="nose">Your nose</button>' in page
    assert page.index('data-view="batch"') < page.index('data-view="nose"') < page.index('data-view="experiments"')
    assert '<section class="view" data-panel="nose" aria-labelledby="nose-title">' in page
    assert 'id="nose-learning"' in page and 'id="blind-test"' in page
    assert page.index('src="/static/smell-log.js"') < page.index('src="/static/blind-test.js"') < page.index('src="/static/lab/core.js"')
    assert 'if (view === "nose" && typeof noseShown === "function") noseShown();' in (STATIC / "lab" / "core.js").read_text(encoding="utf-8")
    bottles = (STATIC / "lab" / "bottles.js").read_text(encoding="utf-8")
    assert "attachNoseLearning(" in bottles and "attachBlindTest(" in bottles


def test_blind_test_and_nose_scripts_write_text_only():
    for name in ("blind-test.js", "smell-log.js"):
        source = (STATIC / name).read_text(encoding="utf-8")
        assert "innerHTML" not in source and "insertAdjacentHTML" not in source, name
