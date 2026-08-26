import pytest


@pytest.mark.asyncio
async def test_offline_lab_app_and_assets_are_served_without_external_dependencies(client):
    page = await client.get("/app")
    css = await client.get("/static/lab.css")
    javascript = await client.get("/static/lab.js")

    assert page.status_code == 200
    assert css.status_code == 200
    assert javascript.status_code == 200
    assert "Perfume Chem Laboratory" in page.text
    for view in (
        "dashboard",
        "materials",
        "formulas",
        "bottles",
        "experiments",
        "perfumery",
        "assistant",
    ):
        assert f'data-view="{view}"' in page.text
    assert 'aria-live="polite"' in page.text
    assert "Evidence posture" in page.text
    assert "http://" not in page.text
    assert "https://" not in page.text
    assert "@media (max-width: 760px)" in css.text
    assert "prefers-reduced-motion" in css.text
    assert 'const API = "/api/v1/lab"' in javascript.text
    assert 'id="hypothesis-form"' in page.text
    assert 'id="trial-plan-form"' in page.text
    assert 'id="component-editor"' in page.text
    assert 'id="add-component-row"' in page.text
    assert 'data-component-row' in page.text
    assert 'components: componentRows()' in javascript.text
    assert 'request("/intervention-hypotheses"' in javascript.text
    assert 'request("/intervention-trials/plan"' in javascript.text
    assert "Safety remains unverified" in page.text
    assert "addEventListener" in javascript.text


@pytest.mark.asyncio
async def test_application_default_dose_is_valid_for_its_html_step(client):
    page = await client.get("/app")

    assert (
        '<input name="mass_mg" type="number" value="20" min="0.1" step="0.1" required>'
        in page.text
    )


@pytest.mark.asyncio
async def test_bottle_addition_default_mass_is_valid_for_its_html_step(client):
    page = await client.get("/app")

    assert (
        '<input name="mass_g" type="number" value="0.1" min="0.001" step="0.001" required>'
        in page.text
    )


@pytest.mark.asyncio
async def test_science_authority_view_preserves_labels_modes_and_unknowns(client):
    page = await client.get("/app")
    css = await client.get("/static/lab.css")
    javascript = await client.get("/static/lab.js")

    assert page.status_code == 200
    assert 'data-view="science"' in page.text
    assert 'data-panel="science"' in page.text
    assert 'id="science-view-mode"' in page.text
    assert '<option value="strict">Strict science</option>' in page.text
    assert '<option value="exploratory">Exploratory science</option>' in page.text
    assert 'id="science-summary"' in page.text
    assert 'id="science-sections"' in page.text
    assert 'id="science-json-download"' in page.text
    assert 'id="science-markdown-download"' in page.text
    assert "Strict-withheld records remain visible" in page.text
    assert "READ_ONLY_NON_PROMOTING" in page.text

    evidence_classes = (
        "MEASURED",
        "LITERATURE_DERIVED",
        "SUPPLIER_PROVIDED",
        "EMPIRICALLY_CALIBRATED",
        "MODEL_ESTIMATED",
        "HEURISTIC",
        "SPECULATIVE",
        "UNKNOWN",
    )
    for label in evidence_classes:
        assert f'data-evidence-class="{label}"' in page.text
        assert f"evidence-{label.lower().replace('_', '-')}" in css.text

    assert 'request(`/science/authority?view=${view}`)' in javascript.text
    assert 'scienceSections.replaceChildren(fragment)' in javascript.text
    assert "textContent" in javascript.text
    assert "strict_reason_codes" in javascript.text
    assert "evidence_class" in javascript.text
    assert "/api/v1/lab/science/report.md?view=" in javascript.text
    assert "confidence percentage" not in page.text.casefold()
    assert "confidence percentage" not in javascript.text.casefold()
