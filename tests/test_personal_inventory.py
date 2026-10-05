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
