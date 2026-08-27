from pathlib import Path

import pytest

STATIC_DIR = Path(__file__).resolve().parents[1] / "app" / "static"


@pytest.mark.asyncio
async def test_solforge_page_and_assets_are_served_without_external_dependencies(client):
    page = await client.get("/solforge")
    css = await client.get("/static/solforge.css")
    javascript = await client.get("/static/solforge.js")

    assert page.status_code == 200
    assert css.status_code == 200
    assert javascript.status_code == 200
    assert 'id="case-file"' in page.text
    assert 'id="hypotheses-file"' in page.text
    assert 'id="compile-experiment"' in page.text
    assert "Computational experiment design only" in page.text
    assert 'aria-live="polite"' in page.text
    assert "http://" not in page.text
    assert "https://" not in page.text
    assert "/static/solforge.css" in page.text
    assert "/static/solforge.js" in page.text


def test_solforge_javascript_enforces_closed_client_boundary():
    script = (STATIC_DIR / "solforge.js").read_text(encoding="utf-8")

    assert "262144" in script
    assert "524288" in script
    assert "runtimeReady" in script
    assert 'const API = "/api/v1/solforge/workbench"' in script
    assert "artifact_download_available" in script
    assert "authority_flags" in script
    assert "schema_version" in script
    assert "case-file" in script
    assert "hypotheses-file" in script
    assert "FileReader" not in script
    assert "innerHTML" not in script


def test_solforge_result_renders_evidence_limits_before_controlled_arms():
    script = (STATIC_DIR / "solforge.js").read_text(encoding="utf-8")

    assert script.index("renderBlockers") < script.index("renderArms")
    assert script.index("renderLimitations") < script.index("renderArms")
    assert "physical" in script.casefold()
    assert "release" in script.casefold()


@pytest.mark.asyncio
async def test_laboratory_app_links_to_solforge_workbench(client):
    page = await client.get("/app")

    assert page.status_code == 200
    assert 'href="/solforge"' in page.text
    assert "SolForge Workbench" in page.text


def test_solforge_styles_preserve_responsive_and_reduced_motion_support():
    stylesheet = (STATIC_DIR / "solforge.css").read_text(encoding="utf-8")

    assert "@media (max-width: 760px)" in stylesheet
    assert "prefers-reduced-motion" in stylesheet
