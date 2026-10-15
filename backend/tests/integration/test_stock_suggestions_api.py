"""A not-ready stock carries a suggested completion; a ready one does not.

The suggestion only pre-fills the Stock page form. Every test writes to its own
temporary logs, never to the real data/user logs.
"""

import pytest

INVENTORY = "/api/v1/lab/v2/workbench/current-inventory"


@pytest.fixture(autouse=True)
def temporary_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("PERFUME_INVENTORY_COMPLETION_PATH", str(tmp_path / "completions.jsonl"))
    monkeypatch.setenv(
        "PERFUME_PERSONAL_INVENTORY_ADDITION_PATH", str(tmp_path / "additions.jsonl")
    )
    monkeypatch.setenv("PERFUME_INVENTORY_DILUTION_PATH", str(tmp_path / "dilutions.jsonl"))


@pytest.mark.asyncio
async def test_an_unready_stock_gets_a_suggestion_and_a_ready_one_does_not(client):
    inventory = (await client.get(INVENTORY)).json()
    stocks = inventory["stocks"]

    # inventory.txt says "Frangipani Absolute (10% in DPG)" with no basis.
    frangipani = next(
        stock
        for stock in stocks
        if stock["identity_name"] == "Frangipani Absolute"
        and stock["fraction_percent_decimal"] == "10"
    )
    assert frangipani["design_ready"] is False
    assert frangipani["completion_available"] is True
    suggestion = frangipani["suggested_completion"]
    assert suggestion["fraction_percent_decimal"] == "10"
    assert suggestion["fraction_basis"] == "mass_fraction"
    assert suggestion["sources"]["fraction_percent_decimal"] == "stock_record"
    assert suggestion["sources"]["fraction_basis"] == "user_rule"
    assert suggestion["saved"] is False
    # Its carrier is already recorded, so only the rule's w/w is suggested.
    assert "carrier" not in suggestion
    assert suggestion["source_text"] == "Your rule: dilutions in DPG, w/w unless recorded"
    # Nothing is saved: the stock itself is unchanged.
    assert frangipani["fraction_basis"] == "unspecified"

    # The workbook row has no carrier; inventory.txt says "Exaltolide (10%)  # 10% in DPG".
    exaltolide = next(
        stock
        for stock in stocks
        if stock["identity_name"] == "Exaltolide"
        and stock["fraction_percent_decimal"] == "10"
        and not stock["design_ready"]
    )
    suggestion = exaltolide["suggested_completion"]
    assert suggestion["carrier"] == "DPG"
    assert suggestion["sources"]["carrier"] == "inventory_txt"
    assert suggestion["source_text"] == (
        f"inventory.txt L{suggestion['inventory_line']} says '10% in DPG'; w/w by your rule"
    )

    ready = [stock for stock in stocks if stock["design_ready"]]
    assert ready
    assert all(stock["suggested_completion"] is None for stock in ready)
    unready = [
        stock for stock in stocks if not stock["design_ready"] and stock["completion_available"]
    ]
    assert any(stock["suggested_completion"] for stock in unready)


@pytest.mark.asyncio
async def test_a_stock_carries_what_the_inventory_list_says_when_it_says_otherwise(client, monkeypatch):
    # RULE 0: a row the checks' record now stands for says what inventory.txt says about it.
    from dataclasses import replace

    from engine.personal_inventory import materialize_personal_inventory

    from app.api.v1.endpoints import lab_lifecycle

    real = materialize_personal_inventory()
    noted = next(s for s in real.stocks if s.stock_id in real.canonical_stock_ids)
    note = "Your inventory list says 10% w/w in DPG"
    projection = replace(real, inventory_text_notes=((noted.stock_id, note),))
    monkeypatch.setattr(lab_lifecycle, "materialize_personal_inventory", lambda **_kwargs: projection)

    stocks = (await client.get(INVENTORY)).json()["stocks"]

    by_id = {stock["stock_id"]: stock for stock in stocks}
    assert by_id[noted.stock_id]["inventory_text_note"] == note
    assert all(stock["inventory_text_note"] is None for stock in stocks if stock["stock_id"] != noted.stock_id)
