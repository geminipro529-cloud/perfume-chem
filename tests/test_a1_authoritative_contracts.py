"""Authoritative Build A1 contracts from the SOL 5.6 master prompt.

These tests are intentionally stricter than the historical A1 audit bundle.
They must be observed RED against the captured A0 baseline before production
code is changed, then GREEN after the minimal A1 fixes.
"""

from __future__ import annotations

from dataclasses import replace

import pytest


def test_declared_composition_overrides_material_name() -> None:
    from engine.units.concentration import (
        DeclaredStock,
        StockComponent,
        compute_active_accounting,
    )

    stock = DeclaredStock(
        name="DPG",
        raw_amount=100.0,
        unit="uL",
        basis="v/v",
        components=(StockComponent(role="odorant_active", fraction=1.0),),
    )

    result = compute_active_accounting([stock])

    assert result.odorant_active_ul == pytest.approx(100.0)
    assert result.carrier_ul == pytest.approx(0.0)


def test_aqueous_ethanol_components_are_accounted_separately() -> None:
    from engine.units.concentration import (
        DeclaredStock,
        StockComponent,
        compute_active_accounting,
    )

    stock = DeclaredStock(
        name="Declared aqueous stock",
        raw_amount=100.0,
        unit="uL",
        basis="v/v",
        components=(
            StockComponent(role="odorant_active", fraction=0.10),
            StockComponent(role="solvent_ethanol", fraction=0.72),
            StockComponent(role="solvent_water", fraction=0.18),
        ),
    )

    result = compute_active_accounting([stock])

    assert result.odorant_active_ul == pytest.approx(10.0)
    assert result.ethanol_ul == pytest.approx(72.0)
    assert result.water_ul == pytest.approx(18.0)
    assert result.solvent_ul == pytest.approx(90.0)
    assert result.classified_total == pytest.approx(result.total_raw_ul)


@pytest.mark.parametrize(
    "stocks",
    [
        pytest.param(
            lambda declared_stock, stock_component: [
                declared_stock(
                    name="negative",
                    raw_amount=-1.0,
                    unit="uL",
                    basis="v/v",
                    components=(stock_component(role="odorant_active", fraction=1.0),),
                )
            ],
            id="negative-raw",
        ),
        pytest.param(
            lambda declared_stock, stock_component: [
                declared_stock(
                    name="overallocated",
                    raw_amount=1.0,
                    unit="uL",
                    basis="v/v",
                    components=(
                        stock_component(role="odorant_active", fraction=0.7),
                        stock_component(role="carrier", fraction=0.7),
                    ),
                )
            ],
            id="component-conservation",
        ),
        pytest.param(
            lambda declared_stock, stock_component: [
                declared_stock(
                    name="volume",
                    raw_amount=1.0,
                    unit="uL",
                    basis="v/v",
                    components=(stock_component(role="odorant_active", fraction=1.0),),
                ),
                declared_stock(
                    name="mass",
                    raw_amount=1.0,
                    unit="uL",
                    basis="w/w",
                    components=(stock_component(role="odorant_active", fraction=1.0),),
                ),
            ],
            id="mixed-basis",
        ),
    ],
)
def test_active_accounting_rejects_negative_or_mixed_basis(stocks) -> None:
    from engine.domain_errors import ReconstructionInputError
    from engine.units.concentration import (
        DeclaredStock,
        StockComponent,
        compute_active_accounting,
    )

    with pytest.raises(ReconstructionInputError):
        compute_active_accounting(stocks(DeclaredStock, StockComponent))


def test_target_row_round_trip_preserves_authoritative_fields() -> None:
    from engine.target.formula import TargetMaterial, create_target_from_rows

    row = {
        "row_id": "row-001",
        "identity": "Hedione HC",
        "canonical_identity": "hedione hc",
        "source_name": "HEDIONE HC Firmenich",
        "grade": "supplier_product",
        "supplier_grade": "HC",
        "evidence_links": ("claim-1",),
        "identity_confidence": 0.91,
        "quantity_confidence": 0.72,
        "active_amount_median": 120.0,
        "active_amount_p05": 90.0,
        "active_amount_p95": 150.0,
        "active_amount_unit": "uL",
        "raw_amount": 240.0,
        "concentration": 0.5,
        "concentration_basis": "v/v",
        "carrier": "DPG",
        "source_record": {"sheet": "formula", "row": 7},
        "provenance": {"source_sha256": "abc", "ingested_by": "contract-test"},
        "notes": "preserve verbatim",
        "extensions": {"a1.v1": {"panel_code": "P-7"}},
    }

    material = create_target_from_rows([row]).target_materials[0]
    restored = TargetMaterial.from_dict(material.as_dict())

    assert restored.as_dict() == material.as_dict()
    for field in (
        "row_id",
        "canonical_identity",
        "source_name",
        "supplier_grade",
        "evidence_links",
        "identity_confidence",
        "quantity_confidence",
        "active_amount_median",
        "active_amount_p05",
        "active_amount_p95",
        "active_amount_unit",
        "concentration_basis",
        "source_record",
        "provenance",
        "notes",
        "extensions",
    ):
        assert material.as_dict()[field] == row[field]


def test_target_row_unknown_fields_are_rejected_or_namespaced() -> None:
    from engine.domain_errors import ReconstructionInputError
    from engine.target.formula import create_target_from_rows

    row = {
        "identity": "Iso E Super",
        "raw_amount": 10.0,
        "concentration": 1.0,
        "concentration_basis": "v/v",
        "unregistered_field": {"keep": True},
    }

    with pytest.raises(ReconstructionInputError, match="unknown target-row fields"):
        create_target_from_rows([row], strict=True)

    material = create_target_from_rows([row], strict=False).target_materials[0]
    assert material.extensions["a1.v1"]["unregistered_field"] == {"keep": True}


def test_empty_target_rows_raise_domain_error() -> None:
    from engine.domain_errors import ReconstructionInputError
    from engine.target.formula import create_target_from_rows

    with pytest.raises(ReconstructionInputError, match="target"):
        create_target_from_rows([])


def test_all_twelve_axes_return_match_differ_or_unknown() -> None:
    from engine.reconstruction.anti_compression import (
        ANTI_COMPRESSION_CRITERIA,
        EvidenceMatch,
        audit_formula,
    )

    checks = audit_formula(["Opaque Base A", "Opaque Base B"], lambda _name: {})[
        "Opaque Base A<->Opaque Base B"
    ]

    assert len(checks) == len(ANTI_COMPRESSION_CRITERIA) == 12
    assert {check.result for check in checks} <= set(EvidenceMatch)


def test_missing_axis_evidence_is_unknown_not_match() -> None:
    from engine.reconstruction.anti_compression import EvidenceMatch, audit_formula, should_merge

    checks = audit_formula(["Opaque Base A", "Opaque Base B"], lambda _name: {})[
        "Opaque Base A<->Opaque Base B"
    ]

    scientific_checks = [c for c in checks if c.criterion_name != "source_roster_identity"]
    assert scientific_checks
    assert all(c.result is EvidenceMatch.UNKNOWN for c in scientific_checks)
    assert should_merge("Opaque Base A", "Opaque Base B", checks) is False


def test_should_merge_requires_exactly_twelve_conclusive_matches() -> None:
    from engine.reconstruction.anti_compression import (
        ANTI_COMPRESSION_CRITERIA,
        CompressionCheck,
        EvidenceMatch,
        should_merge,
    )

    checks = [
        CompressionCheck(
            criterion_name=axis["name"],
            result=EvidenceMatch.MATCH,
            detail="declared evidence",
            material_a="A",
            material_b="B",
        )
        for axis in ANTI_COMPRESSION_CRITERIA
    ]

    assert should_merge("A", "B", checks)
    assert not should_merge("A", "B", checks[:-1])
    assert not should_merge(
        "A",
        "B",
        [*checks[:-1], replace(checks[-1], result=EvidenceMatch.UNKNOWN)],
    )


def test_equivalence_scope_answers_all_eight_questions() -> None:
    from engine.reconstruction.anti_compression import (
        EQUIVALENCE_SCOPE_QUESTIONS,
        EvidenceMatch,
        evaluate_equivalence_scopes,
    )

    left = {
        "cas": "54464-57-2",
        "stereoisomer": "declared-mixture",
        "trade_grade": "Iso E Super",
        "supplier_product": "IFF-IES",
        "lot": "L1",
        "stock_solution": "S1",
        "physical_dose": "D1",
    }
    right = dict(left)
    results = evaluate_equivalence_scopes(left, right, functionally_substitutable=None)

    assert tuple(results) == EQUIVALENCE_SCOPE_QUESTIONS
    assert len(results) == 8
    assert results["same chemical entity?"] is EvidenceMatch.MATCH
    assert results["functionally substitutable?"] is EvidenceMatch.UNKNOWN


def test_one_stock_cannot_satisfy_distinct_target_identities() -> None:
    from engine.domain_errors import ReconstructionInputError
    from engine.inventory.stock_model import assert_unique_stock_assignments

    with pytest.raises(ReconstructionInputError, match="one stock"):
        assert_unique_stock_assignments(
            [
                ("target-identity-a", "stock-001"),
                ("target-identity-b", "stock-001"),
            ]
        )


def _event(
    event_id: str,
    event_type: str,
    *,
    batch_id: str = "batch-a",
    sequence: int,
    correction_ref: str | None = None,
    measured_mass_g: float | None = None,
):
    from engine.bottle.events import COMMITTED, BottleEvent

    return BottleEvent(
        event_id=event_id,
        batch_id=batch_id,
        event_type=event_type,
        timestamp=f"2026-01-01T00:00:{sequence:02d}Z",
        sequence=sequence,
        stock_label="Material A",
        measured_mass_g=measured_mass_g,
        confirmation=COMMITTED,
        correction_ref=correction_ref,
    )


def test_missing_correction_reference_is_rejected() -> None:
    from engine.bottle.events import CORRECT_ENTRY, compute_replay_state
    from engine.domain_errors import EventStreamError

    correction = _event(
        "c1",
        CORRECT_ENTRY,
        sequence=1,
        correction_ref="missing",
        measured_mass_g=2.0,
    )

    with pytest.raises(EventStreamError, match="missing"):
        compute_replay_state([correction])


def test_cross_batch_correction_is_rejected() -> None:
    from engine.bottle.events import CORRECT_ENTRY, DOSE_STOCK, compute_replay_state
    from engine.domain_errors import EventStreamError

    original = _event("dose", DOSE_STOCK, batch_id="batch-a", sequence=1, measured_mass_g=1.0)
    correction = _event(
        "c1",
        CORRECT_ENTRY,
        batch_id="batch-b",
        sequence=2,
        correction_ref="dose",
        measured_mass_g=2.0,
    )

    with pytest.raises(EventStreamError, match="cross-stream"):
        compute_replay_state([original, correction])


def test_correction_chain_latest_valid_value_wins_and_traces_original() -> None:
    from engine.bottle.events import CORRECT_ENTRY, DOSE_STOCK, compute_replay_state

    events = [
        _event("dose", DOSE_STOCK, sequence=1, measured_mass_g=1.0),
        _event("c1", CORRECT_ENTRY, sequence=2, correction_ref="dose", measured_mass_g=2.0),
        _event("c2", CORRECT_ENTRY, sequence=3, correction_ref="c1", measured_mass_g=3.0),
        _event("c3", CORRECT_ENTRY, sequence=4, correction_ref="c2", measured_mass_g=4.0),
    ]
    before = [event.as_dict() for event in events]

    state = compute_replay_state(events)

    assert state["Material A"] == pytest.approx(4.0)
    assert state["_correction_trace"]["dose"] == ("c1", "c2", "c3")
    assert [event.as_dict() for event in events] == before


def test_correction_cycle_is_rejected() -> None:
    from engine.bottle.events import CORRECT_ENTRY, compute_replay_state
    from engine.domain_errors import EventStreamError

    events = [
        _event("c1", CORRECT_ENTRY, sequence=1, correction_ref="c2", measured_mass_g=1.0),
        _event("c2", CORRECT_ENTRY, sequence=2, correction_ref="c1", measured_mass_g=2.0),
    ]

    with pytest.raises(EventStreamError, match="cycle"):
        compute_replay_state(events)


def test_duplicate_retry_is_idempotent() -> None:
    from engine.bottle.events import DOSE_STOCK, compute_replay_state

    event = _event("dose", DOSE_STOCK, sequence=1, measured_mass_g=1.25)
    state = compute_replay_state([event, event])

    assert state["Material A"] == pytest.approx(1.25)
    assert state["_applied_event_count"] == 1


def test_conflicting_duplicate_event_id_is_rejected() -> None:
    from engine.bottle.events import DOSE_STOCK, compute_replay_state
    from engine.domain_errors import EventStreamError

    first = _event("dose", DOSE_STOCK, sequence=1, measured_mass_g=1.0)
    conflict = replace(first, measured_mass_g=2.0)

    with pytest.raises(EventStreamError, match="duplicate event_id"):
        compute_replay_state([first, conflict])


def test_stale_sequence_is_rejected() -> None:
    from engine.bottle.events import DOSE_STOCK, compute_replay_state
    from engine.domain_errors import EventStreamError

    events = [
        _event("first", DOSE_STOCK, sequence=2, measured_mass_g=1.0),
        _event("stale", DOSE_STOCK, sequence=1, measured_mass_g=1.0),
    ]

    with pytest.raises(EventStreamError, match="stale sequence"):
        compute_replay_state(events)


def test_all_public_reconstruction_entry_points_reject_empty_inputs() -> None:
    from engine.bottle.events import compute_replay_state
    from engine.domain_errors import ReconstructionInputError
    from engine.inventory.stock_model import InventoryLedger, map_target_to_inventory
    from engine.reconstruction.anti_compression import audit_formula
    from engine.reconstruction.chassis import create_chassis_from_csv_rows
    from engine.reconstruction.rank_prior import generate_candidate_families
    from engine.reconstruction.recognizer import score_all_materials
    from engine.target.formula import create_target_from_rows

    calls = [
        lambda: audit_formula([]),
        lambda: map_target_to_inventory([], InventoryLedger([])),
        lambda: compute_replay_state([]),
        lambda: create_target_from_rows([]),
        lambda: create_chassis_from_csv_rows([]),
        lambda: generate_candidate_families([]),
        lambda: score_all_materials([]),
    ]

    for call in calls:
        with pytest.raises(ReconstructionInputError):
            call()


def test_rank_prior_rejects_zero_budget_before_math() -> None:
    from engine.domain_errors import ReconstructionInputError
    from engine.reconstruction.rank_prior import RankPriorConfig, generate_soft_rank_prior

    with pytest.raises(ReconstructionInputError, match="budget"):
        generate_soft_rank_prior(["A"], RankPriorConfig(N=1, B=0.0, p=0.65))


def test_ensemble_rejects_zero_budget_before_math() -> None:
    from engine.domain_errors import ReconstructionInputError
    from engine.reconstruction.ensembles import generate_ensemble

    with pytest.raises(ReconstructionInputError, match="budget"):
        generate_ensemble(["A"], total_budget=0.0, N=1)


def test_normalization_denominator_zero_raises_domain_error(monkeypatch) -> None:
    from engine.domain_errors import ReconstructionInputError
    from engine.reconstruction import rank_prior

    monkeypatch.setattr(rank_prior.math, "pow", lambda *_args: 0.0)

    with pytest.raises(ReconstructionInputError, match="normalization denominator"):
        rank_prior.generate_soft_rank_prior(
            ["A"],
            rank_prior.RankPriorConfig(N=1, B=1.0, p=0.65),
        )


def test_identity_and_inventory_statuses_are_independent_enums() -> None:
    from enum import Enum

    from engine.inventory.stock_model import (
        IdentityResolutionStatus,
        InventoryAvailabilityStatus,
    )

    assert issubclass(IdentityResolutionStatus, Enum)
    assert {status.value for status in IdentityResolutionStatus} == {
        "EXACT",
        "ALIAS",
        "AMBIGUOUS",
        "UNRESOLVED",
    }
    assert {status.value for status in InventoryAvailabilityStatus} == {
        "EXACT_LOT_AVAILABLE",
        "EXACT_IDENTITY_NOT_IN_STOCK",
        "GRADE_MISMATCH",
        "FUNCTIONAL_SUBSTITUTE_AVAILABLE",
        "NO_SUITABLE_STOCK",
        "NOT_TECHNICALLY_REQUIRED",
    }


def test_exact_identity_absent_stock_is_not_unresolved() -> None:
    from engine.inventory.stock_model import (
        IdentityResolutionStatus,
        InventoryAvailabilityStatus,
        InventoryLedger,
        map_target_to_inventory,
    )

    mapping = map_target_to_inventory(["Ambroxan"], InventoryLedger([]))[0]

    assert mapping.identity_status is IdentityResolutionStatus.EXACT
    assert mapping.inventory_status is InventoryAvailabilityStatus.EXACT_IDENTITY_NOT_IN_STOCK


def test_unregistered_trade_name_is_not_promoted_to_known_identity() -> None:
    from engine.inventory.stock_model import (
        IdentityResolutionStatus,
        InventoryAvailabilityStatus,
        InventoryLedger,
        map_target_to_inventory,
    )

    mapping = map_target_to_inventory(
        ["Unregistered Mystery Trade Base 9X"],
        InventoryLedger([]),
    )[0]

    assert mapping.identity_status is IdentityResolutionStatus.UNRESOLVED
    assert mapping.inventory_status is InventoryAvailabilityStatus.NO_SUITABLE_STOCK


def test_alias_identity_can_have_exact_lot_available() -> None:
    from engine.inventory.stock_model import (
        IdentityResolutionStatus,
        InventoryAvailabilityStatus,
        InventoryLedger,
        StockItem,
        map_target_to_inventory,
    )

    stock = StockItem(
        material_id="stock-1",
        label="Iso E Super",
        lot="L1",
        amount_remaining_ml=5.0,
    )
    mapping = map_target_to_inventory(["iso-e-super"], InventoryLedger([stock]))[0]

    assert mapping.identity_status is IdentityResolutionStatus.ALIAS
    assert mapping.inventory_status is InventoryAvailabilityStatus.EXACT_LOT_AVAILABLE


def test_grade_mismatch_is_inventory_not_identity_failure() -> None:
    from engine.identity.resolver import IdentityGrade
    from engine.inventory.stock_model import (
        IdentityResolutionStatus,
        InventoryAvailabilityStatus,
        InventoryLedger,
        InventoryTarget,
        StockItem,
        map_target_to_inventory,
    )

    target = InventoryTarget(
        name="Iso E Super",
        grade=IdentityGrade.SUPPLIER_PRODUCT,
        supplier="IFF",
    )
    stock = StockItem(
        material_id="stock-1",
        label="Iso E Super",
        grade=IdentityGrade.TRADE_GRADE,
        amount_remaining_ml=5.0,
    )
    mapping = map_target_to_inventory([target], InventoryLedger([stock]))[0]

    assert mapping.identity_status is IdentityResolutionStatus.EXACT
    assert mapping.inventory_status is InventoryAvailabilityStatus.GRADE_MISMATCH


def test_functional_substitute_does_not_promote_identity() -> None:
    from engine.inventory.stock_model import (
        IdentityResolutionStatus,
        InventoryAvailabilityStatus,
        InventoryLedger,
        InventoryTarget,
        StockItem,
        map_target_to_inventory,
    )

    target = InventoryTarget(name="Ambroxan", functional_substitutes=("Ambrofix",))
    substitute = StockItem(
        material_id="stock-2",
        label="Ambrofix",
        amount_remaining_ml=5.0,
    )
    mapping = map_target_to_inventory([target], InventoryLedger([substitute]))[0]

    assert mapping.identity_status is IdentityResolutionStatus.EXACT
    assert mapping.inventory_status is InventoryAvailabilityStatus.FUNCTIONAL_SUBSTITUTE_AVAILABLE


def test_same_cas_different_supplier_grade_or_lot_is_not_stock_equivalent() -> None:
    from engine.identity.resolver import IdentityGrade, are_equivalent, resolve_identity

    grade_a = resolve_identity(
        "Material A",
        grade=IdentityGrade.TRADE_GRADE,
        cas="123-45-6",
    )
    grade_b = resolve_identity(
        "Material A",
        grade=IdentityGrade.SUPPLIER_PRODUCT,
        supplier="Supplier X",
        cas="123-45-6",
    )
    lot_a = resolve_identity(
        "Material A",
        grade=IdentityGrade.SUPPLIER_LOT,
        supplier="Supplier X",
        lot="L1",
        cas="123-45-6",
    )
    lot_b = replace(lot_a, identity_id="other", lot="L2")

    assert not are_equivalent(grade_a, grade_b)
    assert not are_equivalent(lot_a, lot_b)


def test_natural_origin_participates_in_equivalence() -> None:
    from engine.identity.resolver import NaturalGrade, are_equivalent, resolve_identity

    haiti = resolve_identity(
        "Vetiveria zizanioides",
        grade=NaturalGrade.ORIGIN,
        natural_origin="Haiti",
    )
    india = replace(haiti, identity_id="other", natural_origin="India")

    assert not are_equivalent(haiti, india)


def test_invalid_grade_is_rejected() -> None:
    from engine.identity.resolver import resolve_identity

    with pytest.raises(ValueError, match="grade"):
        resolve_identity("Material A", grade="invented-grade")


def test_opaque_materials_do_not_receive_fabricated_properties() -> None:
    from engine.reconstruction.anti_compression import EvidenceMatch, audit_formula

    checks = audit_formula(["Opaque Base A", "Opaque Fragrance Oil B"])[
        "Opaque Base A<->Opaque Fragrance Oil B"
    ]

    for check in checks:
        if check.criterion_name != "source_roster_identity":
            assert check.result is EvidenceMatch.UNKNOWN


def test_missing_cas_fallback_is_conservative() -> None:
    from engine.identity.resolver import are_equivalent, resolve_identity

    first = resolve_identity("Unregistered Material")
    second = resolve_identity("Unregistered Material")

    assert not are_equivalent(first, second)


def test_registered_trade_materials_remain_non_equivalent() -> None:
    from engine.identity.resolver import are_equivalent, resolve_identity

    assert not are_equivalent(resolve_identity("Hedione"), resolve_identity("Hedione HC"))
