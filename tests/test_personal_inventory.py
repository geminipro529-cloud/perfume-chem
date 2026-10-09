from __future__ import annotations

from pathlib import Path

import pytest

from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)
from engine.name_utils import names_match
from engine.personal_inventory import (
    PersonalInventoryConflictError,
    materialize_personal_inventory,
    record_personal_inventory_addition,
)


def _add_hindinol(path: Path):
    initial = materialize_personal_inventory(addition_path=path)
    return record_personal_inventory_addition(
        expected_design_inventory_sha256=initial.effective_inventory_sha256,
        idempotency_key="test-add-owned-hindinol",
        identity_name="Hindinol",
        category="woods / amber / structure",
        fraction_decimal="1",
        fraction_basis="neat",
        carrier="",
        physical_form="as_supplied",
        possession_confirmed=True,
        homogeneity="NOT_APPLICABLE",
        source_kind="PERSONAL_CONFIRMATION",
        supplier_name="PerfumersWorld",
        supplier_sku="4WX24656",
        user_note="Direct ownership confirmation; wishlist is not ownership authority.",
        path=path,
    )


def test_projection_recovers_live_owned_rows_and_aliases(tmp_path: Path) -> None:
    projection = materialize_personal_inventory(
        addition_path=tmp_path / "additions.jsonl"
    )

    sandalwood = [
        stock
        for stock in projection.stocks
        if names_match(stock.identity_name or stock.name, "Sandalwood Base X3")
    ]
    assert len(sandalwood) == 1
    assert sandalwood[0].authority == "LEGACY_INVENTORY_TEXT_DESIGN_ONLY"
    assert sandalwood[0].design_ready is True
    assert sandalwood[0].execution_ready is False
    assert sum(
        stock.authority == "LEGACY_INVENTORY_TEXT_DESIGN_ONLY"
        for stock in projection.stocks
    ) >= 60
    assert projection.inventory_text_sha256
    assert projection.effective_inventory_sha256 != (
        projection.canonical_effective_inventory_sha256
    )


def test_projection_does_not_bulk_import_supplier_wishlist(tmp_path: Path) -> None:
    projection = materialize_personal_inventory(
        addition_path=tmp_path / "additions.jsonl"
    )
    identities = {
        (stock.identity_name or stock.name).casefold() for stock in projection.stocks
    }

    assert "hindinol" not in identities
    assert "aphermate" not in identities


def test_personal_addition_is_hash_chained_idempotent_and_design_only(
    tmp_path: Path,
) -> None:
    path = tmp_path / "additions.jsonl"
    receipt, projection = _add_hindinol(path)
    hindinol = next(
        stock
        for stock in projection.stocks
        if (stock.identity_name or stock.name) == "Hindinol"
    )

    assert hindinol.authority == "PERSONAL_INVENTORY_ADDITION_DESIGN_ONLY"
    assert hindinol.design_ready is True
    assert hindinol.execution_ready is False
    assert hindinol.dilution == 1
    assert receipt["compounding_authority"] is False

    replay, replayed_projection = record_personal_inventory_addition(
        expected_design_inventory_sha256=projection.effective_inventory_sha256,
        idempotency_key="test-add-owned-hindinol",
        identity_name="Hindinol",
        category="woods / amber / structure",
        fraction_decimal="1",
        fraction_basis="neat",
        carrier="",
        physical_form="as_supplied",
        possession_confirmed=True,
        homogeneity="NOT_APPLICABLE",
        source_kind="PERSONAL_CONFIRMATION",
        supplier_name="PerfumersWorld",
        supplier_sku="4WX24656",
        user_note="Direct ownership confirmation; wishlist is not ownership authority.",
        path=path,
    )
    assert replay["event_sha256"] == receipt["event_sha256"]
    assert sum(
        (stock.identity_name or stock.name) == "Hindinol"
        for stock in replayed_projection.stocks
    ) == 1


def test_personal_addition_refuses_duplicate_alias_stock(tmp_path: Path) -> None:
    path = tmp_path / "additions.jsonl"
    projection = materialize_personal_inventory(addition_path=path)

    with pytest.raises(PersonalInventoryConflictError):
        record_personal_inventory_addition(
            expected_design_inventory_sha256=projection.effective_inventory_sha256,
            idempotency_key="duplicate-sandalwood-alias",
            identity_name="Sandalwood Base X3",
            category="woods / amber / structure",
            fraction_decimal="1",
            fraction_basis="neat",
            carrier="",
            physical_form="as_supplied",
            possession_confirmed=True,
            homogeneity="NOT_APPLICABLE",
            source_kind="PERSONAL_CONFIRMATION",
            path=path,
        )


def test_formula_capability_index_uses_personal_additions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "additions.jsonl"
    monkeypatch.setenv("PERFUME_PERSONAL_INVENTORY_ADDITION_PATH", str(path))
    _add_hindinol(path)

    index = build_material_capability_index(("Hindinol", "Sandalwood Base X3"))
    matches = index.exact_matches("Hindinol")
    sandalwood_matches = index.exact_matches("Sandalwood Base X3")

    assert len(matches) == 1
    assert matches[0].identity_name == "Hindinol"
    assert matches[0].design_ready is True
    assert matches[0].execution_ready is False
    assert len(sandalwood_matches) == 1
    assert sandalwood_matches[0].identity_name == "Sandalwood Base 3X"
    assert index.effective_inventory_sha256 == materialize_personal_inventory(
        addition_path=path
    ).effective_inventory_sha256


CABREUVA = "Cabreuva EO"


@pytest.fixture
def stock_page_logs(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("PERFUME_INVENTORY_COMPLETION_PATH", str(tmp_path / "completions.jsonl"))
    monkeypatch.setenv("PERFUME_PERSONAL_INVENTORY_ADDITION_PATH", str(tmp_path / "additions.jsonl"))
    monkeypatch.setenv("PERFUME_INVENTORY_DILUTION_PATH", str(tmp_path / "dilutions.jsonl"))
    return tmp_path


def _cabreuva_at_25_percent():
    from engine.inventory_completions import record_inventory_completion
    from engine.inventory_parser import materialize_current_inventory

    baseline = materialize_current_inventory()
    parent = next(s for s in baseline.stocks if s.name == "Cabreuva EO 50% in DPG")
    _receipt, completed = record_inventory_completion(
        stock_id=parent.stock_id,
        expected_effective_inventory_sha256=baseline.effective_inventory_sha256,
        idempotency_key="cabreuva-25",
        fraction_decimal="0.25",
        fraction_basis="mass_fraction",
        carrier="DPG",
        physical_form="liquid",
        possession_confirmed=True,
        homogeneity="HOMOGENEOUS",
        final_fraction_known=True,
        source_kind="PERSONAL_CONFIRMATION",
    )
    return parent.stock_id, completed


def test_stock_page_entry_is_shown_even_when_its_name_states_the_workbook_strength(
    stock_page_logs: Path,
) -> None:
    # RULE 0 (review finding S2/S3): the gate counts the 25% entry, so the
    # Stock page must list it with the workbook disagreement.
    from engine.inventory_completions import authority_disagreement

    stock_id, _completed = _cabreuva_at_25_percent()
    projection = materialize_personal_inventory()
    (completed,) = [s for s in projection.stocks if s.stock_id == stock_id]
    assert completed.name == "Cabreuva EO 50% in DPG"
    assert completed.dilution == 0.25
    assert dict(completed.authority_facts_differ)["dilution"] == 0.5
    disagreement = authority_disagreement(completed)
    assert disagreement is not None
    assert disagreement["text"].startswith("Differs from the workbook")


def test_dilution_of_a_completed_stock_is_shown_with_its_own_strength(
    stock_page_logs: Path,
) -> None:
    from engine.inventory_dilutions import PREPARED_DILUTION_AUTHORITY, record_prepared_dilution

    stock_id, completed = _cabreuva_at_25_percent()
    _receipt, materialized = record_prepared_dilution(
        parent_stock_id=stock_id,
        expected_effective_inventory_sha256=completed.effective_inventory_sha256,
        idempotency_key="cabreuva-5",
        fraction_decimal="0.05",
    )
    (gate_stock,) = [
        s for s in materialized.stocks if s.authority == PREPARED_DILUTION_AUTHORITY
    ]
    assert gate_stock.execution_ready is True
    projection = materialize_personal_inventory()
    (shown,) = [s for s in projection.stocks if s.stock_id == gate_stock.stock_id]
    assert shown.dilution == 0.05
    assert shown.name == "Cabreuva EO 5% in DPG"
    assert shown.carrier == "dpg"
