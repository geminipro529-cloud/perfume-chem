"""One change per plan: control versus one addition or dose step, planning only."""

from copy import deepcopy

import pytest
from engine.research.contracts import stable_payload_hash
from engine.research.one_change import triangle_min_correct

from app.services.engine_job_registry import validate_engine_payload
from app.services.engine_jobs import build_engine_job_identity
from tests.unit.test_omission_comparison_jobs import execute
from tests.unit.test_omission_comparison_jobs import payload as omission_payload

# handoff_sha256 of the omission fixture on origin/master (a021473), before triangle sheets existed.
MASTER_OMISSION_HANDOFF = {
    "QUICK_REFERENCE": "5557732abb99c3ac8ef252ab25fd9461c0c07b4ff65c42507449dad43aced632",
    "CONTROLLED_REFERENCE": "b6a0c2b835223ee08743a33f930d838821ac1919830a837047721e9fce752592",
}


def row(identity, amount, *, unit="uL", fraction="0.1", basis="w/w", carrier="DPG"):
    return dict(stock_id=identity, identity_name=identity.replace("_", " ").title(), amount_decimal=amount,
                amount_unit=unit, stock_fraction_decimal=fraction, fraction_basis=basis, carrier=carrier)


def payload(change, **extra):
    return dict(schema_version="omission-comparison-plan-request-v1",
                control_rows=[row("iso_e_super", "3000", fraction="1", basis="neat", carrier=None),
                              row("ambrox", "400")],
                goal="Does the change make the drydown warmer?", change=change, **extra)


def addition(amount="200", bottle="30000", **row_kw):
    return dict(kind="ADDITION", row=row("cashmeran", amount, **row_kw), bottle_volume_ul_decimal=bottle)


def dose(direction, step="200", bottle="30000"):
    return dict(kind="DOSE_STEP", stock_id="ambrox", direction=direction, step_decimal=step,
                bottle_volume_ul_decimal=bottle)


def result_of(data):
    state, envelope, validation, _ = execute(data)
    assert state == "SUCCEEDED" and validation == "ADVISORY_FINDINGS"
    return envelope["result"]


def test_addition_plan_adds_one_row_and_offers_split_vial():
    data = payload(addition())
    original = deepcopy(data)
    result = result_of(data)
    assert data == original and result_of(data) == result
    plan = result["one_change_plan"]
    assert result["change_kind"] == "ADDITION" and result["direction"] == "UP"
    assert plan["candidate_rows"] == [*data["control_rows"], data["change"]["row"]]
    assert result["candidate_formula_sha256"] == {
        "control": stable_payload_hash(data["control_rows"]),
        "variant": stable_payload_hash(plan["candidate_rows"])}
    split = result["how_to_try"]["split_vial"]
    assert result["how_to_try"]["method"] == "SPLIT_VIAL" and result["how_to_try"]["blotter_preview"] is None
    assert (split["split_ul"], split["main_bottle_ul"], split["full_bottle_step_ul"]) == (20, 180, 200)
    assert split["stock"] == "Cashmeran (10% w/w in DPG)"
    assert "Add 20 µL of Cashmeran (10% w/w in DPG) to the vial." in split["steps"]
    assert any("add 180 µL of Cashmeran (10% w/w in DPG) to the main bottle" in s for s in split["steps"])
    assert "Pull 3,000 µL" in split["steps"][0]
    unsigned = {k: v for k, v in result.items() if k != "handoff_sha256"}
    assert stable_payload_hash(unsigned) == result["handoff_sha256"]
    assert result["blinding_state"] == "PLANNING_ONLY_NOT_AN_EXECUTABLE_BLIND_SESSION"
    assert result["physical_execution_authorized"] is False and result["bottle_modified"] is False
    assert result["protocol"]["session_count"] == 1


def test_dose_step_up_changes_only_that_row_and_offers_split():
    data = payload(dose("UP", step="300", bottle="50000"))
    result = result_of(data)
    plan = result["one_change_plan"]
    assert [r["amount_decimal"] for r in plan["candidate_rows"]] == ["3000", "700"]
    assert plan["changed_row"]["control_amount_decimal"] == "400"
    assert plan["changed_row"]["variant_amount_decimal"] == "700"
    split = result["how_to_try"]["split_vial"]
    assert (split["split_ul"], split["main_bottle_ul"]) == (18, 282)
    assert split["stock"] == "Ambrox (10% w/w in DPG)"


def test_dose_step_down_gets_fresh_vials_not_a_split():
    result = result_of(payload(dose("DOWN", step="150")))
    plan = result["one_change_plan"]
    assert [r["amount_decimal"] for r in plan["candidate_rows"]] == ["3000", "250"]
    how = result["how_to_try"]
    assert how["method"] == "FRESH_VIALS" and how["split_vial"] is None and how["blotter_preview"] is None
    assert "Nothing can be taken out" in how["why_no_split"]
    assert any("400 uL in the control, 250 uL in the variant" in s for s in how["fresh_vials"]["steps"])


@pytest.mark.parametrize("change,reason", [
    (addition(amount="50"), "under the 100 µL"),
    (addition(bottle=None), "No bottle volume"),
    (addition(bottle="3000"), "3,000 µL or less"),
    (addition(unit="mg"), "this step is in mg"),
])
def test_split_withheld_gives_one_sentence_reason_and_blotter_preview(change, reason):
    how = result_of(payload(change))["how_to_try"]
    assert how["method"] == "BLOTTER_PREVIEW" and how["split_vial"] is None
    assert reason in how["why_no_split"] and how["why_no_split"].count(". ") == 0
    preview = how["blotter_preview"]
    assert preview["times_min"] == [0, 15, 60]
    assert "only the direction of the change, not the amount" in preview["note"]
    assert any("Cashmeran (10% w/w in DPG)" in s for s in preview["steps"])


def test_split_rounds_to_whole_microlitres_and_sums_to_the_step():
    split = result_of(payload(addition(amount="105", bottle="30000")))["how_to_try"]["split_vial"]
    assert (split["split_ul"], split["main_bottle_ul"]) == (11, 94)


@pytest.mark.parametrize("tries,needed", [(3, 3), (6, 5), (9, 6), (12, 8), (18, 10), (30, 15)])
def test_triangle_threshold_is_exact_binomial_one_third(tries, needed):
    assert triangle_min_correct(tries) == needed


def test_triangle_sheet_on_every_plan_with_plain_reading():
    for change in (addition(), dose("UP"), dose("DOWN")):
        sheet = result_of(payload(change))["triangle_test"]
        assert (sheet["tries"], sheet["min_correct"]) == (6, 5)
        assert sheet["reading"] == ("5 or more right out of 6 means you can really tell them apart. "
                                    "Fewer means this test couldn't show a difference, so keep the control.")
        assert "does not blind" in sheet["blinding_note"]
    sheet = result_of(payload(addition(), triangle_tries=9))["triangle_test"]
    assert sheet["reading"].startswith("6 or more right out of 9")
    assert result_of(omission_payload())["triangle_test"]["min_correct"] == 5


@pytest.mark.parametrize("mode", ["QUICK_REFERENCE", "CONTROLLED_REFERENCE"])
def test_omission_output_is_master_output_plus_triangle_sheet(mode):
    data = omission_payload()
    data["mode"] = mode
    result = result_of(data)
    before = {k: v for k, v in result.items() if k not in ("handoff_sha256", "triangle_test")}
    assert stable_payload_hash(before) == MASTER_OMISSION_HANDOFF[mode]
    assert "change" not in validate_engine_payload(
        "OMISSION_COMPARISON_PLAN", data, request_schema_version="lab-engine-job-request-v2")


def test_omission_canonical_payload_unchanged_by_new_optional_fields():
    normalized = validate_engine_payload("OMISSION_COMPARISON_PLAN", omission_payload(),
                                         request_schema_version="lab-engine-job-request-v2")
    assert set(normalized) == {"schema_version", "control_rows", "omit_stock_ids", "protected_stock_ids",
                               "carrier_blanks", "goal", "mode", "seed"}


@pytest.mark.parametrize("mutate,message", [
    (lambda d: d.update(change=None, omit_stock_ids=[]), "Choose exactly one change"),
    (lambda d: d.update(omit_stock_ids=["ambrox"]), "both an omission and an ADDITION"),
    (lambda d: d.update(change=[addition(), dose("UP")]), "this request lists 2"),
    (lambda d: d["change"]["row"].update(stock_id="ambrox"), "not already in the control"),
    (lambda d: d.update(change=dose("DOWN", step="400")), "use an omission plan"),
    (lambda d: d.update(change=dict(dose("UP"), stock_id="missing")), "name one of the control rows"),
    (lambda d: d.update(change=dose("UP", step="0")), "greater than zero"),
    (lambda d: d.update(change=dict(kind="OMISSION")), "kind"),
])
def test_exactly_one_change_is_required(mutate, message):
    data = payload(addition())
    mutate(data)
    with pytest.raises(ValueError, match=message):
        execute(data)


def test_change_alters_durable_job_fingerprint():
    arguments = dict(job_type="OMISSION_COMPARISON_PLAN", requester="test", idempotency_key="same",
                     request_schema_version="lab-engine-job-request-v2")
    up = build_engine_job_identity(payload=payload(dose("UP")), **arguments)["job_fingerprint_sha256"]
    down = build_engine_job_identity(payload=payload(dose("DOWN")), **arguments)["job_fingerprint_sha256"]
    assert up != down
