from __future__ import annotations

from decimal import Decimal

import pytest

from engine.material_capability_atlas import (
    InventoryCapabilityState,
    KnowledgeState,
    MaterialClass,
    build_material_capability_atlas,
)


@pytest.fixture(scope="module")
def atlas():
    return build_material_capability_atlas()


def test_atlas_reparses_every_current_row_and_v5_requirement(atlas) -> None:
    assert atlas.current_stock_row_count == 279
    assert atlas.current_identity_count == 258
    assert atlas.v5_stock_count == 227
    assert atlas.v5_requirement_count == 280
    assert len(atlas.records) == 258
    assert len({record.identity_key for record in atlas.records}) == 258
    assert atlas.inventory_text_sha256
    assert atlas.v5_workbook_sha256
    assert atlas.v5_snapshot_sha256
    assert atlas.user_overlay_sha256


def test_latest_user_stock_text_blocks_stale_v5_and_profile_availability(atlas) -> None:
    benzyl = atlas.project("Benzyl Salicylate")

    assert benzyl.inventory_state is InventoryCapabilityState.UNAVAILABLE
    assert benzyl.qualitative_selectable is False
    assert benzyl.quantitative_execution_ready is False
    assert any(
        conflict.field == "availability"
        and conflict.effective_source == "CURRENT_CONSOLIDATED_USER_STOCK_TEXT"
        for conflict in benzyl.conflicts
    )
    assert benzyl.legacy_hedonic_value_ignored is True
    assert benzyl.hedonic_claims == ()


def test_stale_profile_stock_never_overrides_current_alpha_irone_stock(atlas) -> None:
    irone = atlas.project("Alpha Irone")

    assert irone.inventory_state is InventoryCapabilityState.OWNED_EXECUTABLE
    assert len(irone.current_stocks) == 1
    stock = irone.current_stocks[0]
    assert stock.active_fraction == Decimal("0.1")
    assert stock.fraction_basis == "mass_fraction"
    assert stock.carrier == "dep"
    assert stock.execution_ready is True
    assert all(item.active_fraction != Decimal("0.3") for item in irone.current_stocks)
    assert any(conflict.field == "profile_stock" for conflict in irone.conflicts)


def test_owned_but_unresolved_stocks_remain_qualitative_only(atlas) -> None:
    bacdanol = atlas.project("Bacnadol")
    guaiacwood = atlas.project("Guaiacwood EO")

    assert bacdanol.canonical_name == "Bacdanol"
    assert bacdanol.inventory_state is InventoryCapabilityState.OWNED_HELD
    assert bacdanol.qualitative_selectable is True
    assert bacdanol.quantitative_execution_ready is False
    assert bacdanol.current_stocks[0].active_fraction is None
    assert "STOCK_FRACTION_UNSPECIFIED" in bacdanol.blockers

    assert guaiacwood.inventory_state is InventoryCapabilityState.OWNED_HELD
    assert guaiacwood.qualitative_selectable is True
    assert guaiacwood.quantitative_execution_ready is False
    assert guaiacwood.current_stocks[0].active_fraction == Decimal("0.33")
    assert guaiacwood.current_stocks[0].fraction_basis == "unspecified"


def test_missing_knowledge_profile_does_not_invent_cypress_capabilities(atlas) -> None:
    cypress = atlas.project("Cypress EO")

    assert cypress.inventory_state is InventoryCapabilityState.OWNED_EXECUTABLE
    assert cypress.knowledge_state is KnowledgeState.MISSING_PROFILE
    assert cypress.material_class is MaterialClass.NATURAL_MIXTURE
    assert cypress.contextual_functions == ()
    assert cypress.temporal_registers == ()
    assert cypress.interfaces == ()
    assert cypress.takeover_modes == ()
    assert "MATERIAL_CAPABILITY_PROFILE_MISSING" in cypress.blockers


def test_naturals_never_gain_constituent_or_composite_oav_authority(atlas) -> None:
    cypress = atlas.project("Cypress EO")

    assert cypress.constituent_identity_authority is False
    assert cypress.composite_oav_authority is False
    assert cypress.sensory_authority is False
    assert cypress.liking_authority is False
    assert cypress.similarity_authority is False
    assert cypress.safety_authority is False
    assert cypress.stability_authority is False
    assert cypress.compounding_authority is False
    assert cypress.release_authority is False


def test_profile_physics_is_field_provenance_not_a_beauty_claim(atlas) -> None:
    irone = atlas.project("Alpha Irone")

    cas = irone.evidence_for("cas")
    assert cas is not None
    assert cas.value == "79-69-6"
    assert cas.source_ref == "pubchem:alpha-Irone"
    assert irone.hedonic_claims == ()
    assert irone.liking_authority is False


def test_unknown_material_projection_fails_closed(atlas) -> None:
    unknown = atlas.project("Imaginary Cypress Captive")

    assert unknown.inventory_state is InventoryCapabilityState.UNLISTED
    assert unknown.qualitative_selectable is False
    assert unknown.quantitative_execution_ready is False
    assert unknown.knowledge_state is KnowledgeState.MISSING_PROFILE
    assert unknown.blockers == ("MATERIAL_UNLISTED",)
