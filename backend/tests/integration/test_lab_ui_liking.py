"""The Lab formula card's pleasantness block, rating rows, A/B pick and personal fit."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

FORMULA_LIKING_JS = Path(__file__).resolve().parents[2] / "app" / "static" / "formula-liking.js"
EVIL = "<img src=x onerror=alert(1)>"
LABEL = "Crowd guess: panel averages and hand estimates. Not a measurement; your own ratings decide."


def _row(material, amount):
    return {
        "material": material, "amount_decimal": amount, "amount_unit": "uL", "stock_id": f"s-{amount}",
        "stock_label": f"{material} 10%", "stock_fraction_decimal": "0.1", "fraction_basis": "mass_fraction",
        "carrier": "DPG", "operation": "DIRECT_ADD", "execution_ready": True, "slot_label": "slot",
        "role": "role", "note": "heart", "rationale": "why",
    }


def _window(label, seconds, score, coverage, status):
    return {
        "window": label, "t_seconds": seconds, "pleasantness": None if score is None else score / 50 - 1,
        "score_0_100": score, "coverage": coverage, "status": status, "strength_shares": {},
        "contributors": [{"material": EVIL, "share": 0.6, "value": 0.4, "source": "table"}, {"material": "Hedione", "share": 0.3, "value": 0.5, "source": "table"}],
        "unrated": [], "dose_adjusted": [],
    }


def _overlay(overall=0.3):
    return {
        "state": "CROWD_GUESS", "label": LABEL, "method": "m", "overall": overall,
        "windows": [
            _window("opening", 0, 70, 0.8, "CROWD_GUESS"), _window("top", 300, 66, 0.7, "CROWD_GUESS"),
            _window("heart", 1800, 60, 0.6, "CROWD_GUESS"), _window("late_heart", 7200, 55, 0.3, "LOW_COVERAGE"),
            _window("drydown", 14400, None, 0.0, "NO_RATED_MATERIALS"),
        ],
        "rating_windows": {
            "opening": {"material_shares": {EVIL: 0.6, "Hedione": 0.4}, "crowd_guess": 0.4, "coverage": 0.8},
            "1h": {"material_shares": {"Hedione": 1.0}, "crowd_guess": 0.2, "coverage": 0.6},
            "4h": {"material_shares": {"Hedione": 1.0}, "crowd_guess": None, "coverage": 0.0},
        },
    }


ROWS = [_row(EVIL, "40"), _row("Hedione", "120")]
ROWS_B = [_row(EVIL, "80"), _row("Hedione", "60")]


def _result(variants=False):
    result = {
        "formula_name": "Liking test", "assistant_message": "Draft.",
        "optimized_formula": {"rows": ROWS, "separate_totals": {"liquid_total_ul": "160", "mass_total_mg": "0"}},
        "critic": {"state": "PASS", "issues": []},
        "scientific_overlays": {"pleasantness": _overlay()},
    }
    if variants:
        result["design_variants"] = [
            {"label": "Variant one", "formula": result["optimized_formula"], "critic": {"state": "PASS", "issues": []},
             "scientific_overlays": {"pleasantness": _overlay()}},
            {"label": "Variant two", "formula": {"rows": ROWS_B, "separate_totals": {"liquid_total_ul": "140", "mass_total_mg": "0"}},
             "critic": {"state": "PASS", "issues": []}, "scientific_overlays": {"pleasantness": _overlay(None)}},
        ]
    return result


def _canonical(rows):
    texts = sorted(json.dumps({"amount": r["amount_decimal"], "material": r["material"], "stock_fraction": r["stock_fraction_decimal"],
                               "unit": r["amount_unit"]}, separators=(",", ":"), ensure_ascii=False) for r in rows)
    return "[" + ",".join(texts) + "]"


def _node(expression):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; the formula-liking wording test needs it")
    program = f"const liking = require({json.dumps(str(FORMULA_LIKING_JS))});\nprocess.stdout.write(JSON.stringify({expression}));"
    completed = subprocess.run([node, "-e", program], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(completed.stdout)


def test_pleasantness_lines_name_each_window_coverage_and_contributors():
    result = _node(f"liking.pleasantnessLines({json.dumps(_overlay())})")
    assert result["lines"][0] == f"Opening: 70/100 (80% of what you'd smell has a crowd value) · led by {EVIL}, Hedione"
    assert result["lines"][1].startswith("5 min: 66/100")
    assert result["lines"][2].startswith("30 min: 60/100")
    assert result["lines"][3].startswith("2 h: only 30% of what you'd smell has a crowd value, so 55/100 is a weak guess")
    assert result["lines"][4].startswith("4 h: none of what you'd smell has a crowd value")
    assert result["label"] == LABEL
    assert "oav" not in json.dumps(result).lower()


def test_rating_link_needs_rating_windows_and_canonical_rows_match_python():
    overlay = _overlay()
    del overlay["rating_windows"]
    link = _node(f"liking.likingRatingLink({json.dumps(overlay)}, 'opening')")
    assert link["ok"] is False and "can't link a rating to its materials" in link["reason"]
    assert _node(f"liking.likingCanonicalRows({json.dumps(list(reversed(ROWS)))})") == _canonical(ROWS)


@pytest.mark.asyncio
async def test_formula_card_wires_the_liking_block(client):
    page = await client.get("/app")
    javascript = await client.get("/static/lab.js")
    helper = await client.get("/static/formula-liking.js")

    assert helper.status_code == 200
    assert page.text.index('src="/static/formula-liking.js"') < page.text.index('src="/static/lab.js"')
    assert page.text.index('id="formula-result-totals"') < page.text.index('id="formula-result-liking"')
    assert "renderFormulaLiking(result, variantIndex, selected)" in javascript.text
    assert "innerHTML" not in helper.text


# -- browser ------------------------------------------------------------------


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


def _open(lab, result):
    feedback = []

    def answer(route, request):
        path = request.url.split("/api/v1/feedback", 1)[1]
        body = json.loads(request.post_data) if request.post_data else None
        feedback.append((request.method, path, body))
        if request.method == "POST":
            route.fulfill(status=201, content_type="application/json", body=json.dumps({"id": 7, **body}))
        elif request.method == "DELETE":
            route.fulfill(status=204, body="")
        else:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(
                {"ratings_used": 3, "picks_used": 1, "liked": [EVIL], "disliked": ["Hedione"]}))

    lab.page.route("**/api/v1/feedback/**", answer)
    lab.respond("POST", "/v2/workbench/formula-chat", json=result)
    lab.open("#formulas")
    lab.page.locator('#formula-chat-form textarea[name="message"]').fill("a liking test")
    lab.page.locator("#formula-chat-submit").click()
    lab.page.locator("#formula-result-liking .liking-row").first.wait_for()
    return feedback


def test_browser_shows_windows_saves_a_rating_with_undo_and_keeps_names_as_text(lab):
    pytest.importorskip("playwright.sync_api")
    feedback = _open(lab, _result())
    box = lab.page.locator("#formula-result-liking")
    windows = box.locator(".liking-windows li")
    assert windows.count() == 5
    assert windows.nth(0).text_content().startswith("Opening: 70/100")
    assert EVIL in windows.nth(0).text_content()
    assert box.locator("img").count() == 0
    assert box.locator(".liking-pick").count() == 0

    row = box.locator('.liking-row[data-window="opening"]')
    assert row.locator(".liking-save").is_disabled()
    row.locator('[data-liking="8"]').click()
    row.locator('select[name="complexity"]').select_option("6")
    row.locator('input[name="too_loud"]').fill("the musk")
    row.locator(".liking-save").click()
    row.locator(".liking-status", has_text="Saved").wait_for()
    method, path, body = feedback[-1]
    assert (method, path) == ("POST", "/liking/ratings")
    assert body == {
        "formula_name": "Liking test", "formula_key": hashlib.sha256(_canonical(ROWS).encode()).hexdigest(),
        "window": "opening", "liking": 8, "complexity": 6, "too_loud": "the musk", "note": None,
        "material_shares": {EVIL: 0.6, "Hedione": 0.4}, "crowd_guess": 0.4, "source": "lab_card",
    }
    row.locator(".liking-undo").click()
    row.locator(".liking-status", has_text="Removed").wait_for()
    assert feedback[-1][:2] == ("DELETE", "/liking/ratings/7")

    box.locator(".liking-personal summary").click()
    box.locator(".liking-personal-body", has_text="3 ratings and 1 A/B picks").wait_for()
    assert EVIL in box.locator(".liking-personal-body").text_content()
    assert box.locator("img").count() == 0


def test_browser_without_rating_windows_disables_save(lab):
    pytest.importorskip("playwright.sync_api")
    result = _result()
    del result["scientific_overlays"]["pleasantness"]["rating_windows"]
    _open(lab, result)
    row = lab.page.locator('#formula-result-liking .liking-row[data-window="1h"]')
    row.locator('[data-liking="5"]').click()
    assert row.locator(".liking-save").is_disabled()
    assert "can't link a rating to its materials" in row.locator(".inline-warning").text_content()


def test_browser_two_formulas_show_the_ab_pick_and_post_it(lab):
    pytest.importorskip("playwright.sync_api")
    feedback = _open(lab, _result(variants=True))
    box = lab.page.locator("#formula-result-liking")
    assert box.locator(".liking-variants li").all_text_contents() == [
        "Variant one: about 65/100 overall", "Variant two: no overall crowd guess (too little of it has a crowd value)"]
    pick = box.locator(".liking-pick")
    assert pick.locator('select[name="formula_a"] option').count() == 2  # main and variant one have the same rows
    pick.locator('select[name="window"]').select_option("1h")
    pick.locator('[data-preferred="b"]').click()
    pick.locator(".liking-status", has_text="Saved").wait_for()
    method, path, body = feedback[-1]
    assert (method, path) == ("POST", "/liking/picks")
    assert body["window"] == "1h" and body["preferred"] == "b"
    assert body["formula_b_name"] == "Liking test · Variant two"
    assert body["formula_b_key"] == hashlib.sha256(_canonical(ROWS_B).encode()).hexdigest()
    assert body["shares_a"] == {"Hedione": 1.0} and body["crowd_a"] == 0.2
