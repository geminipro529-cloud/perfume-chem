"""Forms with their own submit handlers fail loudly, save once, and bottle mass is bounded."""

import json
import time

import pytest

pytest.importorskip("playwright.sync_api")

ADD_PATH = "/v2/workbench/current-inventory/add"

# name -> (view hash, form id, POST path, 422 field name, success body, setup)
FORMS = {
    "backup": ("#dashboard", "backup-form", "/backups", "label", {"snapshot_path": "snap.zip"}, None),
    "inventory-addition": ("#materials", "inventory-addition-form", ADD_PATH, "identity_name",
                           {"inventory": {"stocks": [], "counts": {}}}, "inventory"),
    "sample": ("#experiments", "sample-form", "/experiments/e1/samples", "blind_code", {"id": "s1"}, "sample"),
    "application": ("#experiments", "application-form", "/applications", "sample_id", {"id": "a1"}, "application"),
    "hypothesis": ("#perfumery", "hypothesis-form", "/intervention-hypotheses", "brief_name", {"hypotheses": []}, None),
    "trial-plan": ("#perfumery", "trial-plan-form", "/intervention-trials/plan", "material",
                   {"achieved_active_ppm_w_w": 1.0}, None),
    "assistant": ("#assistant", "assistant-form", "/assistant", "subject_id", {"payload_sha256": "0123456789abcdef"}, None),
}


def _open(lab, name, **answer):
    hash_, form_id, path, field, ok_body, setup = FORMS[name]
    lab.respond("GET", "/experiments", json=[{"id": "e1", "name": "Trial"}])
    lab.respond("GET", "/bottles", json=[{"id": "b1", "label": "Bottle"}])
    lab.open(hash_)
    form = lab.page.locator(f"#{form_id}")
    if setup == "inventory":
        lab.page.locator("#inventory-add-open").click()
        form.locator('input[name="identity_name"]').fill("Hindinol")
        form.locator('input[name="possession_confirmed"]').check()
    if setup == "application":
        form.locator('input[name="sample_id"]').fill("s1")
    if answer:
        lab.respond("POST", path, **answer)
    else:
        lab.respond("POST", path, status=201, json=ok_body)
    return form, path, field


def _posts(lab, path):
    return [item for item in lab.requests if item == ("POST", path)]


def _wait_idle(lab, form):
    form.locator('button[type="submit"]:enabled').wait_for(state="attached")


@pytest.mark.parametrize("name", list(FORMS))
def test_server_error_shows_the_inline_not_saved_box(lab, name):
    form, path, _field = _open(lab, name, status=500, json={"detail": "The disk is full."})

    form.locator('button[type="submit"]').click()
    box = lab.page.locator(f"#{form.get_attribute('id')}-error")
    box.wait_for()
    _wait_idle(lab, form)

    assert box.get_attribute("role") == "alert"
    assert box.inner_text().startswith("Not saved.")
    assert "The disk is full." in box.inner_text()
    assert len(_posts(lab, path)) == 1
    history = lab.status_history()
    assert history[-1]["error"] is True


@pytest.mark.parametrize("name", list(FORMS))
def test_conflict_shows_the_inline_not_saved_box(lab, name):
    form, _path, _field = _open(lab, name, status=409, json={"detail": "Already there."})

    form.locator('button[type="submit"]').click()
    box = lab.page.locator(f"#{form.get_attribute('id')}-error")
    box.wait_for()

    assert box.inner_text().startswith("Not saved.")
    assert "Already there." in box.inner_text()


@pytest.mark.parametrize("name", list(FORMS))
def test_unreachable_server_shows_the_inline_not_saved_box(lab, name):
    form, path, _field = _open(lab, name)
    lab.fail("POST", path)

    form.locator('button[type="submit"]').click()
    box = lab.page.locator(f"#{form.get_attribute('id')}-error")
    box.wait_for()

    assert box.inner_text().startswith("Not saved.")
    assert "Can't reach the app" in box.inner_text()


@pytest.mark.parametrize("name", list(FORMS))
def test_rejected_field_is_marked_and_nothing_is_claimed_saved(lab, name):
    form, path, field = _open(lab, name, status=422, json={"detail": [{"loc": ["body", "x"], "msg": "Field required", "type": "missing"}]})
    detail = [{"loc": ["body", field], "msg": "Field required", "type": "missing"}]
    lab.respond("POST", path, status=422, json={"detail": detail})

    form.locator('button[type="submit"]').click()
    box = lab.page.locator(f"#{form.get_attribute('id')}-error")
    box.wait_for()
    _wait_idle(lab, form)

    assert box.inner_text().startswith("Not saved.")
    assert "required" in box.inner_text()
    assert form.locator(f'[name="{field}"]').get_attribute("aria-invalid") == "true"
    texts = [entry["text"] for entry in lab.status_history()]
    assert not any("recorded" in text or "created" in text or "built" in text or "planned" in text
                   or "generated" in text or "available for personal" in text for text in texts[1:])


def test_a_good_save_clears_the_old_error_and_keeps_its_success_message(lab):
    form, path, _field = _open(lab, "assistant", status=500, json={"detail": "Boom."})
    form.locator('button[type="submit"]').click()
    lab.page.locator("#assistant-form-error").wait_for()
    _wait_idle(lab, form)

    lab.respond("POST", path, status=200, json={"payload_sha256": "0123456789abcdef"})
    form.locator('button[type="submit"]').click()
    lab.wait_for_status("Packet 0123456789 built.")

    assert lab.page.locator("#assistant-form-error").count() == 0
    assert "payload_sha256" in lab.page.locator("#assistant-output").inner_text()


def _slow(lab, path, body, delay=0.7):
    def handler(route, _request):
        time.sleep(delay)
        route.fulfill(status=201, content_type="application/json", body=__import__("json").dumps(body))

    lab.on("POST", path, handler)


@pytest.mark.parametrize("name,clicks", [("sample", 2), ("sample", 3), ("application", 2), ("application", 3)])
def test_repeated_clicks_send_one_post(lab, name, clicks):
    form, path, _field = _open(lab, name)
    _slow(lab, path, FORMS[name][4])

    button = form.locator('button[type="submit"]')
    button.click(click_count=clicks)
    lab.page.wait_for_function(
        "() => window.__statusHistory.some((entry) => /recorded/.test(entry.text))", timeout=10000
    )
    _wait_idle(lab, form)

    assert len(_posts(lab, path)) == 1


@pytest.mark.parametrize("name", list(FORMS))
def test_button_stays_disabled_while_saving_then_returns(lab, name):
    form, path, _field = _open(lab, name)
    held = []
    lab.on("POST", path, lambda route, _request: held.append(route))  # answered below, not on a timer
    button = form.locator('button[type="submit"]')

    button.click()
    deadline = time.monotonic() + 10
    while not held and time.monotonic() < deadline:
        lab.page.wait_for_timeout(20)
    assert held, "the form never sent its save"
    assert button.is_disabled()
    held[0].fulfill(status=201, content_type="application/json", body=json.dumps(FORMS[name][4]))
    _wait_idle(lab, form)
    assert button.is_enabled()
    assert len(_posts(lab, path)) == 1


@pytest.mark.parametrize("name", ["sample", "application"])
def test_a_fast_server_still_gets_one_post_from_a_double_click(lab, name):
    form, path, _field = _open(lab, name)  # answers at once
    button = form.locator('button[type="submit"]')

    button.click()
    lab.page.wait_for_timeout(150)  # a human double click's second click
    button.click(force=True)
    lab.page.wait_for_timeout(300)
    _wait_idle(lab, form)

    assert len(_posts(lab, path)) == 1


@pytest.mark.parametrize("name", list(FORMS))
def test_button_returns_after_a_failed_save(lab, name):
    form, _path, _field = _open(lab, name, status=500, json={"detail": "Nope."})

    form.locator('button[type="submit"]').click()
    lab.page.locator(f"#{form.get_attribute('id')}-error").wait_for()

    assert form.locator('button[type="submit"]').is_enabled()


def _bottle(lab, mass):
    lab.open("#bottles")
    form = lab.page.locator("#bottle-form")
    form.locator('input[name="label"]').fill("Mass test")
    form.locator('input[name="initial_mass_g"]').fill(mass)
    return form


@pytest.mark.parametrize("mass", ["1e12", "10000.5", "-1"])
def test_bottle_mass_outside_zero_to_ten_thousand_sends_nothing(lab, mass):
    lab.respond("POST", "/bottles", status=201, json={"id": "b1", "label": "Mass test", "status": "open"})
    form = _bottle(lab, mass)

    form.locator('button[type="submit"]').click()
    box = lab.page.locator("#bottle-form-error")
    box.wait_for()

    assert box.inner_text().startswith("Not saved.")
    assert "Initial mass" in box.inner_text()
    assert form.locator('input[name="initial_mass_g"]').get_attribute("aria-invalid") == "true"
    assert _posts(lab, "/bottles") == []


def test_bottle_mass_inputs_declare_the_limit(lab):
    lab.open("#bottles")
    for selector in ("#bottle-form", "#stock-form"):
        field = lab.page.locator(f'{selector} input[name="initial_mass_g"]')
        assert (field.get_attribute("min"), field.get_attribute("max"), field.get_attribute("step")) == ("0", "10000", "any")


@pytest.mark.parametrize("mass,sent", [("0", 0), ("10000", 10000), ("12.3456789", 12.3456789)])
def test_bottle_mass_in_range_still_saves(lab, mass, sent):
    lab.respond("POST", "/bottles", status=201, json={"id": "b1", "label": "Mass test", "status": "open"})
    posted = []
    lab.on("POST", "/bottles", lambda route, request: (
        posted.append(request.post_data_json),
        route.fulfill(status=201, content_type="application/json", body='{"id": "b1"}'),
    ))
    form = _bottle(lab, mass)

    form.locator('button[type="submit"]').click()
    lab.wait_for_status("Record committed.")

    assert posted == [{"label": "Mass test", "initial_mass_g": sent}]
    assert lab.page.locator("#bottle-form-error").count() == 0


def test_stock_initial_mass_over_the_limit_sends_nothing(lab):
    lab.respond("GET", "/materials", json=[{"id": "m1", "name": "Hedione", "cas_number": None}])
    lab.open("#materials")
    lab.page.get_by_text("Optional laboratory ledger tools").click()
    form = lab.page.locator("#stock-form")
    form.locator('input[name="initial_mass_g"]').fill("1e12")

    form.locator('button[type="submit"]').click()
    box = lab.page.locator("#stock-form-error")
    box.wait_for()

    assert box.inner_text().startswith("Not saved.")
    assert _posts(lab, "/stocks") == []


@pytest.mark.parametrize("name,body", [("inventory-addition", {"inventory": {"stocks": [None], "counts": {}}}), ("sample", None)])
def test_failure_after_a_good_save_says_saved_but_and_never_not_saved(lab, name, body):
    # The POST succeeds but its body makes the post-save code throw; the page must not invite a retry.
    form, path, _field = _open(lab, name, status=201, json=body)
    form.locator('button[type="submit"]').click()
    lab.page.wait_for_function(
        "() => (window.__statusHistory || []).some((entry) => entry.text.startsWith('Saved, but'))")
    _wait_idle(lab, form)

    assert form.locator(".form-error, [id$='-error']").count() == 0
    assert form.locator('[aria-invalid="true"]').count() == 0
    assert not any(entry["text"].startswith("Not saved.") for entry in lab.status_history())
    assert len(_posts(lab, path)) == 1
