"""Create several cards: a bench sheet straight from a card, and "Mixed it? Rate it"."""

import json

import pytest

pytest.importorskip("playwright.sync_api")

from tests.integration.test_lab_ui_liking import _overlay, _row  # noqa: E402

BRIEF_A = "A cold mineral lavender"
BRIEF_B = "Dark leather and iris"


def _design(name, rows_first, rows_second):
    def variant(label, rows):
        return {
            "variant_id": label, "label": label, "critic": {"state": "PASS", "issues": []},
            "formula": {"rows": rows, "separate_totals": {"liquid_total_ul": "160", "mass_total_mg": "0"}},
            "scientific_overlays": {"pleasantness": _overlay()},
        }

    return {
        "formula_name": name,
        "assistant_message": f"{name} draft.",
        "design_variants": [variant("First", rows_first), variant("Second", rows_second)],
        "critic": {"state": "PASS", "issues": []},
    }


DESIGNS = {
    BRIEF_A: _design("Lavande Minerale", [_row("Lavender Oil", "40"), _row("Hedione", "120")],
                     [_row("Lavender Oil", "80"), _row("Hedione", "60")]),
    BRIEF_B: _design("Cuir Iris", [_row("Birch Tar", "15"), _row("Orris Butter", "60")],
                     [_row("Birch Tar", "30"), _row("Orris Butter", "40")]),
}


@pytest.fixture(scope="module")
def lab_browser():
    """Chromium that treats the fake Lab origin as secure, so crypto.subtle exists there."""
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.integration.lab_browser import ORIGIN, chromium_executable

    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=chromium_executable(playwright),
            args=[f"--unsafely-treat-insecure-origin-as-secure={ORIGIN}"],
        )
        try:
            yield browser
        finally:
            browser.close()


def _create_two(lab):
    lab.page.route("**/api/v1/feedback/**", lambda route, _request: route.fulfill(
        status=200, content_type="application/json", body=json.dumps({"ratings_used": 0, "picks_used": 0})))
    jobs = {}

    def submit(route, request):
        brief = json.loads(request.post_data)["payload"]["message"]
        job_id = f"job-{len(jobs) + 1}"
        jobs[job_id] = brief
        route.fulfill(status=202, content_type="application/json", body=json.dumps({"id": job_id, "state": "QUEUED"}))
        lab.respond("GET", f"/v2/engine-jobs/{job_id}", json={
            "id": job_id, "state": "SUCCEEDED", "timeout_seconds": 300, "events": [],
            "result": {"result": {"result": {"formula_design": DESIGNS[brief]}}},
        })

    lab.on("POST", "/v2/engine-jobs", submit)
    lab.open("#formulas")
    lab.page.evaluate("() => { window.__printed = 0; window.print = () => { window.__printed += 1; }; }")
    lab.page.fill('#several-form textarea[name="briefs"]', f"{BRIEF_A}\n{BRIEF_B}")
    lab.page.click("#several-submit")
    lab.page.locator("#several-status", has_text="Composed 2 perfumes").wait_for()
    return lab.page.locator(".several-card", has_text=BRIEF_A), lab.page.locator(".several-card", has_text=BRIEF_B)


def test_a_card_prints_its_own_bench_sheet_without_touching_the_studio(lab):
    card_a, _card_b = _create_two(lab)

    card_a.get_by_role("button", name="Bench sheet").click()

    assert lab.page.evaluate("window.__printed") == 1
    sheet = lab.page.locator("#bench-sheet")
    assert "Lavande Minerale" in sheet.text_content()
    assert "Lavender Oil" in sheet.text_content()
    assert "Birch Tar" not in sheet.text_content()
    assert lab.page.locator("#formula-chat-result").is_hidden()


def test_rate_it_opens_the_cards_formula_at_the_rating_card(lab):
    card_a, card_b = _create_two(lab)

    card_b.get_by_role("button", name="Mixed it? Rate it").click()
    assert lab.page.locator("#formula-result-name").inner_text() == "Cuir Iris"
    rate = lab.page.locator("#formula-result-liking .liking-rate")
    rate.wait_for()
    lab.page.wait_for_function(
        "() => { const box = document.querySelector('#formula-result-liking .liking-rate').getBoundingClientRect();"
        " return box.top >= -2 && box.top < window.innerHeight / 2; }"
    )

    # Another card's formula replaces the studio's only on a second click.
    rate_a = card_a.get_by_role("button", name="Mixed it? Rate it")
    rate_a.click()
    assert lab.page.locator("#formula-result-name").inner_text() == "Cuir Iris"
    card_a.get_by_role("button", name="Replace the studio's formula?").click()
    assert lab.page.locator("#formula-result-name").inner_text() == "Lavande Minerale"

    # With the same formula open on its second alternative, Rate it shows the card's own one.
    lab.page.locator("#formula-variant-picker button", has_text="Second").click()
    assert "Second" in lab.page.locator("#formula-result-variant").inner_text()
    card_a.get_by_role("button", name="Mixed it? Rate it").click()
    assert "First" in lab.page.locator("#formula-result-variant").inner_text()
    assert lab.page.locator("#formula-variant-picker button.is-active").inner_text() == "First"
