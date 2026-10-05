from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import reconstruct


def _args(**overrides):
    values = {
        "operation": "PROPOSE",
        "api_base_url": "http://127.0.0.1:8000/api/v1/lab/v2",
        "batch_id": "bottle-1",
        "material": "Hedione",
        "amount": "15",
        "unit": "uL",
        "amount_ul": None,
        "actual_amount": None,
        "actual_unit": None,
        "stock_density_g_ml": "0.9",
        "reservation_id": "reservation-1",
        "expected_sequence": 4,
        "idempotency_key": "delta-1",
        "proposal_id": None,
        "decision": "CONFIRMED",
        "confirmer": "user",
        "standard_uncertainty_g": None,
        "measurement_method": "pipette-plus-explicit-density",
        "occurred_at": "2026-09-28T12:00:00+07:00",
        "waited_seconds": None,
        "reaction": None,
        "evaluation_decision": "HOLD",
        "actor": "user",
        "reason": "Clearer lavender at 30 minutes",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_liquid_and_crystal_quantities_keep_native_units() -> None:
    liquid_mass, liquid_basis = reconstruct._mass_for_batch_quantity(
        "15", "uL", "0.9"
    )
    crystal_mass, crystal_basis = reconstruct._mass_for_batch_quantity(
        "300", "mg", None
    )
    assert liquid_mass == "0.0135"
    assert liquid_basis["density_g_ml_decimal"] == "0.9"
    assert crystal_mass == "0.3"
    assert crystal_basis == {"conversion": "MASS_UNIT_CONVERSION_ONLY"}


def test_liquid_requires_density_only_for_mass_conversion() -> None:
    with pytest.raises(ValueError, match="density"):
        reconstruct._mass_for_batch_quantity("15", "uL", None)
    assert reconstruct._mass_for_batch_quantity("15", "mg", None)[0] == "0.015"


def test_evolving_bottle_proposal_calls_one_server_owned_lifecycle_step(monkeypatch) -> None:
    calls = []

    def fake_request(**kwargs):
        calls.append(kwargs)
        return {"id": "proposal-1", "stock_solution_id": "server-selected-stock"}

    monkeypatch.setattr(reconstruct, "_request_json", fake_request)
    result = reconstruct.handle_live_batch(_args())

    assert result["status"] == "PROPOSAL_RECORDED"
    assert result["delta_card"]["add"] == "15 uL of Hedione"
    assert result["delta_card"]["state"] == "PROPOSAL_ONLY"
    assert len(calls) == 1
    assert calls[0]["path"] == "actions"
    assert calls[0]["payload"]["planned_mass_g"] == pytest.approx(0.0135)
    assert calls[0]["payload"]["action_type"] == "ADD_STOCK"


def test_commit_is_explicit_and_does_not_repeat_prior_steps(monkeypatch) -> None:
    calls = []

    def fake_request(**kwargs):
        calls.append(kwargs)
        return {"id": "commit-1"}

    monkeypatch.setattr(reconstruct, "_request_json", fake_request)
    result = reconstruct.handle_live_batch(
        _args(operation="COMMIT", proposal_id="proposal-1")
    )
    assert result["status"] == "COMMIT_RECORDED"
    assert len(calls) == 1
    assert calls[0]["path"] == "actions/proposal-1/commit"


def test_evaluation_records_one_short_linked_personal_reaction(monkeypatch) -> None:
    calls = []

    def fake_request(**kwargs):
        calls.append(kwargs)
        return {
            "id": "evaluation-1",
            "evidence_scope": "SEQUENTIAL_PERSONAL_OBSERVATION",
        }

    monkeypatch.setattr(reconstruct, "_request_json", fake_request)
    result = reconstruct.handle_live_batch(
        _args(
            operation="EVALUATE",
            proposal_id="proposal-1",
            idempotency_key="delta-1-evaluation-1800",
            waited_seconds="1800",
            reaction="Lavender is clearer; amber stayed dry.",
            evaluation_decision="CONTINUE",
        )
    )
    assert result["status"] == "EVALUATION_RECORDED"
    assert result["evidence_scope"] == "SEQUENTIAL_PERSONAL_OBSERVATION"
    assert len(calls) == 1
    assert calls[0]["path"] == "actions/proposal-1/evaluations"
    assert calls[0]["payload"]["waited_seconds"] == 1800.0
    assert calls[0]["payload"]["decision"] == "CONTINUE"


def test_rescue_refuses_negative_delta_without_calling_server(monkeypatch) -> None:
    monkeypatch.setattr(
        reconstruct,
        "_request_json",
        lambda **_kwargs: pytest.fail("server must not be called"),
    )
    result = reconstruct.handle_batch_rescue(_args(amount="-1"))
    assert result["status"] == "ADDITIVE_REPAIR_NOT_FEASIBLE"
    assert result["formula_action"] == "NO_CHANGE"


def test_lifecycle_client_rejects_non_loopback_urls() -> None:
    result = reconstruct.handle_live_batch(
        _args(api_base_url="https://example.com/api/v1/lab/v2")
    )
    assert result["status"] == "ERROR"
    assert "loopback" in result["detail"]
