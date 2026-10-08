"""The knowledge route reads only files inside the knowledge folder."""

from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import data_loader

ROUTE = "/api/v1/api/v1/reference/knowledge/"


@pytest.fixture
def http():
    # No ``with`` block: the app lifespan (engine worker) is not started.
    return TestClient(app)


@pytest.fixture
def knowledge_sandbox(tmp_path, monkeypatch):
    root = tmp_path / "knowledge"
    (root / "sub").mkdir(parents=True)
    (root / "inside.md").write_text("inside knowledge", encoding="utf-8")
    outside = tmp_path / "outside.md"
    outside.write_text("SECRET outside the knowledge folder", encoding="utf-8")
    (root / "link.md").symlink_to(outside)
    monkeypatch.setattr(data_loader, "KNOWLEDGE_DIR", root)
    return tmp_path, outside


def _assert_refused(response, *absolute_paths):
    assert response.status_code == 404
    assert "SECRET" not in response.text
    for path in absolute_paths:
        assert str(path) not in response.text


def test_encoded_dotdot_cannot_read_repository_readme(http):
    repository_root = data_loader.KNOWLEDGE_DIR.resolve().parent
    assert (repository_root / "README.md").is_file()  # the escape target exists

    response = http.get(ROUTE + "..%2FREADME.md")

    assert response.status_code == 404
    assert str(repository_root) not in response.text
    assert "../README.md" in response.json()["detail"]


@pytest.mark.parametrize(
    "requested",
    [
        "..%2Foutside.md",
        "%2E%2E%2Foutside.md",
        "sub%2F..%2F..%2Foutside.md",
        "link.md",  # symlink inside the folder pointing outside it
    ],
)
def test_escape_forms_are_refused(http, knowledge_sandbox, requested):
    tmp_root, _outside = knowledge_sandbox
    _assert_refused(http.get(ROUTE + requested), tmp_root)


def test_absolute_path_is_refused_without_echoing_it(http, knowledge_sandbox):
    tmp_root, outside = knowledge_sandbox
    response = http.get(ROUTE + quote(str(outside), safe=""))
    _assert_refused(response, tmp_root, outside)
    assert response.json()["detail"] == "Knowledge file not found"


def test_file_inside_sandbox_still_served(http, knowledge_sandbox):
    response = http.get(ROUTE + "inside.md")
    assert response.status_code == 200
    assert response.json()["content"] == "inside knowledge"


def test_real_knowledge_file_still_served(http):
    real = sorted(data_loader.KNOWLEDGE_DIR.glob("*.md"))[0]
    response = http.get(ROUTE + real.name)
    assert response.status_code == 200
    assert response.json()["content"] == real.read_text(encoding="utf-8")
