"""Read-only omission handoff; no observation or physical action is implied."""

from copy import deepcopy

import pytest
from engine.research.contracts import stable_payload_hash

from app.services.engine_job_executor import execute_registered_engine_job
from app.services.engine_job_registry import ENGINE_JOB_CONTRACT_VERSION_V2, validate_engine_payload
from app.services.engine_jobs import build_engine_job_identity


def payload():
    def row(identity, mass):
        return dict(stock_id=identity, identity_name=identity, amount_decimal=mass,
                    amount_unit="mg", stock_fraction_decimal="0.1", fraction_basis="w/w", carrier="DPG")
    return dict(schema_version="omission-comparison-plan-request-v1",
                control_rows=[row("fixed_flower", "120"), row("mobile_hay", "15.25")],
                omit_stock_ids=["mobile_hay"], protected_stock_ids=["fixed_flower"],
                carrier_blanks={"DPG": dict(stock_id="blank", carrier="DPG")},
                goal="Does hay add useful texture?", mode="QUICK_REFERENCE", seed=17)


def execute(data):
    normalized = validate_engine_payload("OMISSION_COMPARISON_PLAN", data,
                                         request_schema_version="lab-engine-job-request-v2")
    return execute_registered_engine_job("OMISSION_COMPARISON_PLAN", normalized,
                                         contract_version=ENGINE_JOB_CONTRACT_VERSION_V2)


@pytest.mark.parametrize("mode,sessions", [("QUICK_REFERENCE", 1), ("CONTROLLED_REFERENCE", 3)])
def test_deterministic_proposal_binds_design_and_protocol_without_blinding_claim(mode, sessions):
    data = payload()
    data["mode"] = mode
    original = deepcopy(data)
    state, envelope, validation, _ = execute(data)
    result = envelope["result"]
    assert data == original and execute(data)[1] == envelope
    assert state == "SUCCEEDED" and validation == "ADVISORY_FINDINGS"
    assert result["candidate_formula_sha256"]["control"] == result["omission_plan"]["control_sha256"]
    assert result["candidate_formula_sha256"]["omission"] == stable_payload_hash(result["omission_plan"]["candidate_rows"])
    unsigned = {k: v for k, v in result.items() if k != "handoff_sha256"}
    assert stable_payload_hash(unsigned) == result["handoff_sha256"]
    assert result["protocol"]["session_count"] == sessions
    assert result["sensory_validation"] == "NOT_TESTED"
    assert result["blinding_state"] == "PLANNING_ONLY_NOT_AN_EXECUTABLE_BLIND_SESSION"
    assert result["private_code_mapping_persisted"] is False
    assert result["observations_created"] is False and result["bottle_modified"] is False
    assert result["inventory_modified"] is False and result["physical_execution_authorized"] is False
    assert "session_codes" not in str(result)
    assert all(envelope["authority"][key] is False for key in (
        "release_authority", "safety_authority", "compounding_authority", "evidence_admission_authorized"))


@pytest.mark.parametrize("change", ["mass", "carrier", "seed", "goal"])
def test_changed_input_changes_durable_command_and_result_binding(change):
    first = payload()
    second = deepcopy(first)
    if change == "mass":
        second["control_rows"][0]["amount_decimal"] = "121"
    elif change == "carrier":
        second["control_rows"][1]["carrier"] = "ethanol"
    elif change == "seed":
        second["seed"] = 18
    else:
        second["goal"] = "Is the fruit clearer?"
    arguments = dict(job_type="OMISSION_COMPARISON_PLAN", requester="test", idempotency_key="same",
                     request_schema_version="lab-engine-job-request-v2")
    assert build_engine_job_identity(payload=first, **arguments)["job_fingerprint_sha256"] != build_engine_job_identity(payload=second, **arguments)["job_fingerprint_sha256"]
    assert execute(first)[1]["result"]["handoff_sha256"] != execute(second)[1]["result"]["handoff_sha256"]


@pytest.mark.parametrize("change", ["unit", "basis", "blank", "protected"])
def test_quantitative_hold_does_not_create_protocol(change):
    data = payload()
    if change == "unit":
        data["control_rows"][0]["amount_unit"] = "uL"
    elif change == "basis":
        data["control_rows"][0]["fraction_basis"] = "w/v"
    elif change == "blank":
        data["carrier_blanks"] = {}
    else:
        data["protected_stock_ids"].append("mobile_hay")
    state, envelope, validation, _ = execute(data)
    assert state == "WITHHELD" and validation == "WITHHOLD_UNKNOWN"
    assert envelope["result"]["protocol"] is None
    assert envelope["result"]["formula_action"] == "NO_CHANGE"


@pytest.mark.parametrize("invalid", [True, "NaN", "Infinity", "-1", "0", "1e99999999", 0.1])
def test_invalid_numbers_rejected_before_execution(invalid):
    data = payload()
    data["control_rows"][0]["amount_decimal"] = invalid
    with pytest.raises(ValueError):
        execute(data)


@pytest.mark.parametrize("key", ["compounding_authority", "decision", "module", "function", "command"])
def test_no_authority_or_execution_fields(key):
    data = payload()
    data[key] = "caller-choice"
    with pytest.raises(ValueError):
        execute(data)
    with pytest.raises(ValueError, match="REQUIRES_V2"):
        validate_engine_payload("OMISSION_COMPARISON_PLAN", payload())


def test_blank_stock_cannot_represent_two_different_carriers():
    data = payload()
    data["carrier_blanks"]["ethanol"] = dict(stock_id="blank", carrier="ethanol")
    with pytest.raises(ValueError, match="multiple carriers"):
        execute(data)


def test_extreme_bounded_decimal_total_is_exact_end_to_end():
    data = payload()
    data["control_rows"][0]["amount_decimal"] = "1234567890123456789012345678901234567890"
    data["control_rows"][1]["amount_decimal"] = "0.00000000000000000000000000000000000001"
    _, envelope, _, _ = execute(data)
    assert envelope["result"]["omission_plan"]["total_mass_mg"] == (
        "1234567890123456789012345678901234567890.00000000000000000000000000000000000001"
    )
