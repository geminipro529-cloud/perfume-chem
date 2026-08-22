from __future__ import annotations

from engine.perception.citrus_selection import (
    CitrusCandidate,
    CitrusCandidateScope,
    CitrusInventoryState,
    bind_citrus_inventory,
)
from engine.perception.complexity_inventory import (
    InventoryAvailability,
    StockReadiness,
    load_complexity_inventory_catalog,
)
from engine.perception.musk_design import (
    InventoryState,
    MuskCandidate,
    MuskRole,
    bind_musk_inventory,
)


def test_catalog_covers_every_current_master_record_and_august_addition() -> None:
    catalog = load_complexity_inventory_catalog()

    assert catalog.workbook_sha256 == (
        "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
    )
    assert catalog.current_record_count == 280
    assert len(catalog.current_records) == 280
    assert len(catalog.august_added_materials) == 30
    assert {
        "Freesia HDI",
        "Dimethyl Benzyl Carbonyl Acetate",
        "Lemonile",
        "Methyl Pamplemousse 10%",
        "Pamzest",
        "Paradisamide",
        "Heliotropin",
        "Skatole 1%",
        "Tonkarome 20%",
        "Bourgeonal 20% in TEC",
        "Ethyl Maltol 1% + 10%",
        "Aldehyde C10 neat",
        "Aldehyde C11 neat",
        "Aldehyde C12 MNA neat",
        "Delta Decalactone",
        "Maple Lactone 20%",
        "Raspberry Ketone 20% in DPG",
        "Dynascone 10% in DPG",
        "Hexyl Acetate 1%",
        "Triplal",
        "Peonile",
        "Damascol",
        "Alpha Damascone",
        "Rhodinol ex Citronella",
        "Citronellal",
        "Phenethyl Acetate",
        "Gamma Nonalactone 10%",
        "Helichrysum EO",
        "Cassis Base 345B",
        "Benzyl Benzoate",
    } == set(catalog.august_added_materials)
    assert all(
        catalog.project(record.canonical_material).source_kind
        == "CURRENT_INVENTORY_MASTER"
        for record in catalog.current_records
    )
    assert all(
        catalog.project(material).source_kind == "CURRENT_INVENTORY_MASTER"
        for material in catalog.august_added_materials
    )


def test_catalog_keeps_availability_and_stock_readiness_as_separate_dimensions() -> None:
    catalog = load_complexity_inventory_catalog()

    habanolide = catalog.project("Habanolide")
    assert habanolide.availability is InventoryAvailability.OWNED
    assert habanolide.stock_readiness is StockReadiness.EXACT_STOCK_IDENTIFIED
    assert habanolide.exact_stock_ref == (
        "Habanolide neat/as supplied; CAS 111879-80-2"
    )

    freesia = catalog.project("Freesia HDI")
    assert freesia.availability is InventoryAvailability.OWNED
    assert freesia.stock_readiness is StockReadiness.STOCK_DETAIL_OPEN
    assert freesia.exact_stock_ref is None

    ambrettolide = catalog.project("Ambrettolide 10%")
    assert ambrettolide.availability is InventoryAvailability.PLANNED_ACQUISITION
    assert ambrettolide.stock_readiness is StockReadiness.PROCUREMENT_PENDING
    assert ambrettolide.exact_stock_ref is None

    banned = catalog.project("DO NOT USE — Iris FTEC")
    assert banned.availability is InventoryAvailability.FORBIDDEN
    assert banned.stock_readiness is StockReadiness.NOT_BUILDABLE


def test_catalog_preserves_advisory_candidates_without_inventing_stock() -> None:
    catalog = load_complexity_inventory_catalog()

    ethylene_brassylate = catalog.project("Ethylene Brassylate")
    assert ethylene_brassylate.availability is InventoryAvailability.MISSING
    assert ethylene_brassylate.stock_readiness is StockReadiness.NOT_BUILDABLE
    assert ethylene_brassylate.source_kind == "ADVISORY_CANDIDATE"
    assert ethylene_brassylate.purchase_class == (
        "HIGH_VALUE ARCHITECTURAL EXPANSION"
    )
    assert ethylene_brassylate.exact_stock_ref is None

    unlisted = catalog.project("Imaginary Citrus X")
    assert unlisted.availability is InventoryAvailability.UNLISTED
    assert unlisted.source_kind == "UNLISTED"


def test_catalog_never_collapses_explicit_non_equivalents() -> None:
    catalog = load_complexity_inventory_catalog()

    galbanum_eo = catalog.project("Galbanum EO")
    galbanum_resinoid = catalog.project("Galbanum Resinoid 10%")
    assert galbanum_eo.availability is InventoryAvailability.OWNED
    assert galbanum_resinoid.availability is InventoryAvailability.MISSING
    assert galbanum_eo.canonical_material != galbanum_resinoid.canonical_material

    assert catalog.is_forbidden_equivalence("Galbanum EO", "Galbanum Resinoid")
    assert catalog.is_forbidden_equivalence("Habanolide", "Galaxolide 50%") is False


def test_citrus_binding_changes_only_inventory_fields() -> None:
    catalog = load_complexity_inventory_catalog()
    candidate = CitrusCandidate(
        material="Neroli EO 10%",
        roles=("orange-blossom bridge",),
        axis_matches=("bitter", "floral", "green", "diffusive", "heart-linked"),
        axis_conflicts=(),
        inventory_state=CitrusInventoryState.MISSING,
        exact_stock_ref=None,
        transition_to_heart="links peel bitterness into orange blossom",
        evidence_refs=("target-architecture:test",),
        selection_scope=CitrusCandidateScope.SUPPORT_ONLY,
    )

    bound = bind_citrus_inventory(candidate, catalog)

    assert bound.inventory_state is CitrusInventoryState.OWNED
    assert bound.exact_stock_ref == "Neroli EO 10% in DPG"
    assert bound.roles == candidate.roles
    assert bound.axis_matches == candidate.axis_matches
    assert bound.transition_to_heart == candidate.transition_to_heart
    assert bound.selection_scope is CitrusCandidateScope.SUPPORT_ONLY


def test_musk_binding_covers_owned_planned_and_missing_without_count_reward() -> None:
    catalog = load_complexity_inventory_catalog()

    def candidate(material: str) -> MuskCandidate:
        return MuskCandidate(
            material=material,
            role=MuskRole.TEXTURE,
            target_function="test the exact target-linked texture",
            why_nonredundant="hypothesis only; no count reward",
            inventory_state=InventoryState.UNKNOWN,
            exact_stock_ref=None,
        )

    habanolide = bind_musk_inventory(candidate("Habanolide"), catalog)
    romandolide = bind_musk_inventory(candidate("Romandolide"), catalog)
    ambrettolide = bind_musk_inventory(candidate("Ambrettolide 10%"), catalog)
    ethylene = bind_musk_inventory(candidate("Ethylene Brassylate"), catalog)

    assert (habanolide.inventory_state, habanolide.exact_stock_ref) == (
        InventoryState.OWNED,
        "Habanolide neat/as supplied; CAS 111879-80-2",
    )
    assert (romandolide.inventory_state, romandolide.exact_stock_ref) == (
        InventoryState.OWNED,
        "Romandolide neat/as supplied",
    )
    assert (ambrettolide.inventory_state, ambrettolide.exact_stock_ref) == (
        InventoryState.PLANNED_ACQUISITION,
        None,
    )
    assert (ethylene.inventory_state, ethylene.exact_stock_ref) == (
        InventoryState.MISSING,
        None,
    )
    assert all(
        item.role is MuskRole.TEXTURE
        for item in (habanolide, romandolide, ambrettolide, ethylene)
    )
