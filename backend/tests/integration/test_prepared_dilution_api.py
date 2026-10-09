"""Stock page dilutions count as gate stocks (Kenny, 2026-10-09).

Every test writes to its own temporary logs through the environment variables
the app and the release gate both read, never to the real data/user logs.
"""

import pytest

INVENTORY = "/api/v1/lab/v2/workbench/current-inventory"
DILUTE = INVENTORY + "/dilute"
MATERIAL = "Alpha Damascone"


@pytest.fixture(autouse=True)
def temporary_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("PERFUME_INVENTORY_COMPLETION_PATH", str(tmp_path / "completions.jsonl"))
    monkeypatch.setenv(
        "PERFUME_PERSONAL_INVENTORY_ADDITION_PATH", str(tmp_path / "additions.jsonl")
    )
    path = tmp_path / "dilutions.jsonl"
    monkeypatch.setenv("PERFUME_INVENTORY_DILUTION_PATH", str(path))
    return path


async def _inventory_and_parent(client):
    inventory = (await client.get(INVENTORY)).json()
    parent = next(
        stock
        for stock in inventory["stocks"]
        if stock["identity_name"] == MATERIAL and stock["fraction_percent_decimal"] == "100"
    )
    return inventory, parent


def _command(inventory, parent, key, **overrides):
    return {
        "parent_stock_id": parent["stock_id"],
        "expected_effective_inventory_sha256": inventory[
            "canonical_effective_inventory_sha256"
        ],
        "idempotency_key": key,
        "fraction_percent_decimal": "1",
        **overrides,
    }


@pytest.mark.asyncio
async def test_a_saved_dilution_becomes_a_ready_stock_in_dpg_w_w(client, temporary_logs):
    inventory, parent = await _inventory_and_parent(client)
    assert parent["dilution_available"] is True
    assert inventory["counts"]["prepared_dilutions"] == 0

    response = await client.post(
        DILUTE,
        json=_command(
            inventory,
            parent,
            "api-damascone-1",
            amount_made_g="10",
            prepared_on="2026-10-09",
            user_note="Made for the rose trial.",
        ),
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "PREPARED_DILUTION_RECORDED"
    for flag in (
        "release_authority",
        "safety_authority",
        "compounding_authority",
        "evidence_admission_authorized",
    ):
        assert result[flag] is False
    stocks = {stock["stock_id"]: stock for stock in result["inventory"]["stocks"]}
    prepared = stocks[result["prepared_stock_id"]]
    assert prepared["identity_name"] == MATERIAL
    assert prepared["source_class"] == "PREPARED_DILUTION"
    assert prepared["fraction_percent_decimal"] == "1"
    assert prepared["fraction_basis"] == "mass_fraction"
    assert prepared["carrier"] == "dpg"
    assert prepared["design_ready"] is True
    assert prepared["execution_ready"] is True
    assert prepared["completion_available"] is False
    assert prepared["dilution_available"] is False
    assert result["inventory"]["counts"]["prepared_dilutions"] == 1
    assert stocks[parent["stock_id"]]["fraction_percent_decimal"] == "100"
    assert temporary_logs.exists()

    reread = (await client.get(INVENTORY)).json()
    assert result["prepared_stock_id"] in {stock["stock_id"] for stock in reread["stocks"]}


@pytest.mark.asyncio
@pytest.mark.parametrize("percent", ["0", "100", "150"])
async def test_a_strength_that_is_not_weaker_than_the_bottle_is_refused(
    client, temporary_logs, percent
):
    inventory, parent = await _inventory_and_parent(client)

    response = await client.post(
        DILUTE, json=_command(inventory, parent, f"api-bad-{percent}", fraction_percent_decimal=percent)
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_PREPARED_DILUTION"
    assert "strength" in error["message"]
    assert not temporary_logs.exists()


@pytest.mark.asyncio
async def test_a_reused_key_with_a_different_dilution_is_a_conflict(client):
    inventory, parent = await _inventory_and_parent(client)
    first = await client.post(DILUTE, json=_command(inventory, parent, "api-reused"))
    assert first.status_code == 200, first.text
    fresh = first.json()["inventory"]

    replay = await client.post(DILUTE, json=_command(fresh, parent, "api-reused"))
    assert replay.status_code == 200
    assert replay.json()["receipt"]["event_sha256"] == first.json()["receipt"]["event_sha256"]

    changed = await client.post(
        DILUTE, json=_command(fresh, parent, "api-reused", fraction_percent_decimal="2")
    )
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "PREPARED_DILUTION_CONFLICT"
    assert "different dilution" in changed.json()["error"]["message"]


@pytest.mark.asyncio
async def test_a_stale_inventory_view_is_refused_like_a_completion(client, temporary_logs):
    inventory, parent = await _inventory_and_parent(client)
    stale = {**inventory, "canonical_effective_inventory_sha256": "0" * 64}

    response = await client.post(DILUTE, json=_command(stale, parent, "api-stale"))

    assert response.status_code == 409
    assert "refresh" in response.json()["error"]["message"]
    assert not temporary_logs.exists()


@pytest.mark.asyncio
async def test_a_dilution_held_because_its_parent_changed_says_so_in_plain_words(
    client, temporary_logs
):
    inventory, parent = await _inventory_and_parent(client)
    first = await client.post(DILUTE, json=_command(inventory, parent, "api-held-1"))
    assert first.status_code == 200, first.text
    fresh = first.json()["inventory"]
    prepared_id = first.json()["prepared_stock_id"]
    assert {s["stock_id"]: s for s in fresh["stocks"]}[prepared_id]["gate_hold_text"] is None

    changed = await client.post(
        INVENTORY + "/complete",
        json={
            "schema_version": "personal-inventory-completion-request-v1",
            "stock_id": parent["stock_id"],
            "expected_effective_inventory_sha256": fresh[
                "canonical_effective_inventory_sha256"
            ],
            "idempotency_key": "api-held-parent-50",
            "fraction_percent_decimal": "50",
            "fraction_basis": "mass_fraction",
            "carrier": "DPG",
            "physical_form": "solution",
            "possession_confirmed": True,
            "homogeneity": "HOMOGENEOUS",
            "final_fraction_known": True,
            "source_kind": "PERSONAL_CONFIRMATION",
            "user_note": "",
        },
    )
    assert changed.status_code == 200, changed.text
    stocks = {s["stock_id"]: s for s in changed.json()["inventory"]["stocks"]}
    held = stocks[prepared_id]
    assert held["execution_ready"] is False
    assert held["gate_hold_text"] == (
        "Not counted at the gate: the parent bottle's details changed after this "
        "dilution was recorded. Record the dilution again from the bottle as it is now."
    )
    assert stocks[parent["stock_id"]]["gate_hold_text"] is None


def test_a_dilution_whose_parent_is_held_says_to_resolve_the_parent_first():
    from types import SimpleNamespace

    from engine.inventory_dilutions import PREPARED_DILUTION_AUTHORITY

    from app.api.v1.endpoints.lab_lifecycle import _gate_hold_text

    held = SimpleNamespace(
        authority=PREPARED_DILUTION_AUTHORITY,
        execution_ready=False,
        execution_hold_reason="PREPARED_DILUTION_PARENT_HELD|STOCK_INTAKE_IDENTITY_ONLY",
    )
    assert _gate_hold_text(held) == (
        "Not counted at the gate: its parent bottle is held. Resolve the parent bottle first."
    )
    ordinary = SimpleNamespace(
        authority="GOVERNED",
        execution_ready=False,
        execution_hold_reason="STOCK_INTAKE_IDENTITY_ONLY",
    )
    assert _gate_hold_text(ordinary) is None
