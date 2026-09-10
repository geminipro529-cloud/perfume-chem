import json
from decimal import Decimal
from hashlib import sha256

import pytest

from app.services.lab_service import IdempotencyConflictError, LabService, LabTransactionError


def _hash(label: str) -> str:
    return sha256(label.encode("utf-8")).hexdigest()


def _semantic_sha256(payload: dict) -> str:
    return sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


async def _exact_evidence(service: LabService, label: str):
    return await service.record_evidence(
        claim_key=f"stock-identity:{label}",
        classification="EXACT",
        source_locator=f"physical-label://{label}",
        source_version="1",
        method="Direct label and lot witness",
        assumptions=(),
        limitations=("No analytical purity or safety authority",),
        payload_sha256=_hash(label),
    )


async def _closed_preparation(db_session, *, uncertainty: float | None = 0.001):
    service = LabService(db_session)
    odorant = await service.create_material("Lemonile")
    carrier_material = await service.create_material("Dipropylene Glycol")
    parent_evidence = await _exact_evidence(service, "lemonile-parent")
    carrier_evidence = await _exact_evidence(service, "dpg-parent")
    parent = await service.create_stock_solution(
        material_id=odorant.id,
        active_fraction=Decimal("1"),
        fraction_basis="mass_fraction",
        initial_mass_g=Decimal("10"),
        supplier="supplier-a",
        lot_number="LEM-LOT-1",
    )
    carrier = await service.create_stock_solution(
        material_id=carrier_material.id,
        active_fraction=Decimal("1"),
        fraction_basis="mass_fraction",
        initial_mass_g=Decimal("100"),
        supplier="supplier-b",
        lot_number="DPG-LOT-1",
    )
    bottle = await service.create_bottle("Lemonile 1% preparation")
    parent_event = await service.add_stock_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=parent.id,
        mass_g=Decimal("0.1"),
        expected_sequence=1,
        command_id="prep-parent",
        standard_uncertainty=uncertainty,
        actor="operator-a",
    )
    carrier_event = await service.add_solvent_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=carrier.id,
        mass_g=Decimal("9.9"),
        expected_sequence=2,
        command_id="prep-carrier",
        standard_uncertainty=uncertainty,
        actor="operator-a",
    )
    close_event = await service.close_bottle(
        bottle_id=bottle.id,
        expected_sequence=3,
        command_id="prep-close",
        actor="operator-a",
    )
    return {
        "service": service,
        "odorant": odorant,
        "parent": parent,
        "carrier": carrier,
        "parent_evidence": parent_evidence,
        "carrier_evidence": carrier_evidence,
        "bottle": bottle,
        "parent_event": parent_event,
        "carrier_event": carrier_event,
        "close_event": close_event,
    }


async def _closed_volumetric_preparation(
    db_session,
    *,
    parent_mass_g: Decimal = Decimal("0.1"),
    carrier_mass_g: Decimal = Decimal("0.9"),
    parent_volume_ul: Decimal = Decimal("100"),
    carrier_volume_ul: Decimal = Decimal("900"),
    parent_temperature_c: Decimal = Decimal("20"),
    carrier_temperature_c: Decimal = Decimal("20"),
    volume_uncertainty_ul: Decimal | None = Decimal("0.5"),
    include_volume_conditions: bool = True,
):
    service = LabService(db_session)
    odorant = await service.create_material("Volumetric intent odorant")
    carrier_material = await service.create_material("Volumetric intent DPG")
    parent_evidence = await _exact_evidence(service, "vv-parent")
    carrier_evidence = await _exact_evidence(service, "vv-carrier")
    parent = await service.create_stock_solution(
        material_id=odorant.id,
        active_fraction=Decimal("1"),
        fraction_basis="mass_fraction",
        initial_mass_g=Decimal("10"),
        supplier="supplier-vv-parent",
        lot_number="VV-PARENT-LOT",
    )
    carrier = await service.create_stock_solution(
        material_id=carrier_material.id,
        active_fraction=Decimal("1"),
        fraction_basis="mass_fraction",
        initial_mass_g=Decimal("100"),
        supplier="supplier-vv-carrier",
        lot_number="VV-CARRIER-LOT",
    )
    conditions = {
        "delivery_mode": "EX",
        "liquid_equilibrated": True,
        "reference_standard": "ISO_8655_6_2022",
    }
    volume_conditions = conditions if include_volume_conditions else None
    bottle = await service.create_bottle("Source v/v intent preparation")
    parent_event = await service.add_stock_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=parent.id,
        mass_g=parent_mass_g,
        expected_sequence=1,
        command_id="vv-parent",
        measured_volume_ul=parent_volume_ul,
        standard_uncertainty=Decimal("0.001"),
        volume_standard_uncertainty_ul=volume_uncertainty_ul,
        volume_measurement_method="ISO 8655-6 gravimetric delivery calibration",
        volume_device_id="PIPETTE-P1000-01",
        volume_device_calibration_sha256=_hash("pipette-parent-calibration"),
        volume_reference_temperature_c=parent_temperature_c,
        volume_reference_conditions=volume_conditions,
        actor="operator-vv",
    )
    carrier_event = await service.add_solvent_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=carrier.id,
        mass_g=carrier_mass_g,
        expected_sequence=2,
        command_id="vv-carrier",
        measured_volume_ul=carrier_volume_ul,
        standard_uncertainty=Decimal("0.001"),
        volume_standard_uncertainty_ul=volume_uncertainty_ul,
        volume_measurement_method="ISO 8655-6 gravimetric delivery calibration",
        volume_device_id="PIPETTE-P1000-02",
        volume_device_calibration_sha256=_hash("pipette-carrier-calibration"),
        volume_reference_temperature_c=carrier_temperature_c,
        volume_reference_conditions=volume_conditions,
        actor="operator-vv",
    )
    close_event = await service.close_bottle(
        bottle_id=bottle.id,
        expected_sequence=3,
        command_id="vv-close",
        actor="operator-vv",
    )
    return {
        "service": service,
        "odorant": odorant,
        "parent": parent,
        "carrier": carrier,
        "parent_evidence": parent_evidence,
        "carrier_evidence": carrier_evidence,
        "bottle": bottle,
        "parent_event": parent_event,
        "carrier_event": carrier_event,
        "close_event": close_event,
    }


@pytest.mark.asyncio
async def test_closed_native_bottle_finalizes_hash_bound_child_stock(db_session):
    case = await _closed_preparation(db_session)
    service = case["service"]

    child = await service.finalize_stock_preparation(
        bottle_id=case["bottle"].id,
        material_id=case["odorant"].id,
        parent_event_id=case["parent_event"].id,
        carrier_event_id=case["carrier_event"].id,
        parent_identity_evidence_id=case["parent_evidence"].id,
        carrier_identity_evidence_id=case["carrier_evidence"].id,
        child_label="Lemonile 1% in DPG",
        child_lot_number="LEM-1PCT-20260816",
        preparation_sop_sha256=_hash("gravimetric-preparation-sop-v1"),
        balance_calibration_sha256=_hash("balance-calibration-20260816"),
        command_id="finalize-lemonile-1pct",
        actor="operator-a",
    )

    assert child.material_id == case["odorant"].id
    assert child.active_fraction_decimal_text == "0.01"
    assert child.fraction_basis == "mass_fraction"
    assert child.initial_mass_g == pytest.approx(10.0)
    assert child.solvent_name == "Dipropylene Glycol"
    assert case["parent_event"].payload_json["mass_g_decimal_text"] == "0.1"
    assert case["carrier_event"].payload_json["standard_uncertainty_decimal_text"] == "0.001"
    receipt = child.source_json["stock_preparation_receipt"]
    assert receipt["schema_version"] == "lab-stock-preparation-receipt-v1"
    assert receipt["state"] == "EXECUTED_PREPARATION_RECORDED"
    assert receipt["preparation_bottle"]["close_event_id"] == case["close_event"].id
    assert receipt["parent"]["stock_solution_id"] == case["parent"].id
    assert receipt["carrier"]["stock_solution_id"] == case["carrier"].id
    assert receipt["parent"]["measured_mass_g"] == "0.1"
    assert receipt["carrier"]["measured_mass_g"] == "9.9"
    assert receipt["child"]["initial_mass_g"] == "10"
    assert receipt["child"]["active_fraction"] == "0.01"
    assert receipt["inventory_conservation"]["mass_delta_g"] == "0"
    assert receipt["authority"] == {
        "formula_authority": False,
        "safety_authority": False,
        "scientific_authority": False,
        "sensory_authority": False,
        "release_authority": False,
    }
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    assert receipt["receipt_sha256"] == _semantic_sha256(unsigned)
    assert await service.stock_balance_g(case["parent"].id) == pytest.approx(9.9)
    assert await service.stock_balance_g(case["carrier"].id) == pytest.approx(90.1)
    assert await service.stock_balance_g(child.id) == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_v2_receipt_preserves_vv_intent_without_changing_mass_authority(
    db_session,
):
    case = await _closed_volumetric_preparation(db_session)
    service = case["service"]
    child = await service.finalize_stock_preparation(
        bottle_id=case["bottle"].id,
        material_id=case["odorant"].id,
        parent_event_id=case["parent_event"].id,
        carrier_event_id=case["carrier_event"].id,
        parent_identity_evidence_id=case["parent_evidence"].id,
        carrier_identity_evidence_id=case["carrier_evidence"].id,
        child_label="Source design nominal 10% v/v",
        child_lot_number="VV-CHILD-LOT",
        preparation_sop_sha256=_hash("vv-preparation-sop"),
        balance_calibration_sha256=_hash("vv-balance-calibration"),
        source_design_sha256=_hash("source-10pct-vv-design"),
        source_target_volume_fraction=Decimal("0.1"),
        command_id="finalize-vv",
        actor="operator-vv",
    )

    assert child.fraction_basis == "mass_fraction"
    assert child.active_fraction_decimal_text == "0.1"
    receipt = child.source_json["stock_preparation_receipt"]
    assert receipt["schema_version"] == "lab-stock-preparation-receipt-v2"
    assert receipt["parent"]["volume_delivery"]["measured_volume_ul"] == "100"
    assert receipt["parent"]["volume_delivery"]["canonical_measured_volume_ul"] == "100"
    assert receipt["carrier"]["volume_delivery"]["measured_volume_ul"] == "900"
    assert receipt["source_volume_intent"] == {
        "authority": "NONAUTHORITATIVE_PREPARATION_INTENT_AND_MEASUREMENT_METADATA",
        "source_target_grain": "PLANNED",
        "observed_volume_grain": "MEASURED_COMPONENT_DELIVERIES",
        "inventory_movement_grain": "COMMITTED_MASS_ONLY",
        "correction_policy": "CORRECTED_OR_REVERSED_INPUT_HISTORY_REJECTED",
        "source_design_sha256": _hash("source-10pct-vv-design"),
        "definition": "IUPAC_VOLUME_FRACTION_COMPONENT_VOLUMES_BEFORE_MIXING",
        "denominator": ("SUM_OF_SEPARATELY_MEASURED_COMPONENT_DELIVERY_VOLUMES_BEFORE_MIXING"),
        "target_parent_input_volume_fraction": "0.1",
        "canonical_target_parent_input_volume_fraction": "0.1",
        "fraction_unit": "1",
        "observed_parent_input_volume_fraction": "0.1",
        "total_pre_mix_component_volume_ul": "1000",
        "alignment_state": "NOMINAL_SOURCE_RATIO_MATCH_ONLY",
        "conditions_compatible": True,
        "final_mixed_solution_volume_used": False,
        "canonical_stock_fraction_basis": "mass_fraction",
        "inventory_authority": False,
        "formula_dose_authority": False,
        "mass_volume_conversion_authority": False,
        "active_mass_or_dose_authority": False,
        "volume_fraction_stock_created": False,
        "exact_stock_ref_gate_satisfied": False,
        "preparation_gate_satisfied": False,
        "safety_authority": False,
        "execution_authority": False,
        "scientific_authority": False,
        "release_authority": False,
    }
    assert receipt["inventory_conservation"] == {
        "parent_consumed_mass_g": "0.1",
        "carrier_consumed_mass_g": "0.9",
        "child_initial_mass_g": "1",
        "mass_delta_g": "0",
    }
    assert receipt["child"]["fraction_basis"] == "mass_fraction"
    assert receipt["source_volume_intent"]["inventory_authority"] is False


@pytest.mark.asyncio
async def test_vv_intent_rejects_missing_volume_uncertainty(db_session):
    case = await _closed_volumetric_preparation(
        db_session,
        volume_uncertainty_ul=None,
    )
    with pytest.raises(
        LabTransactionError,
        match="volume_standard_uncertainty_ul authority",
    ):
        await case["service"].finalize_stock_preparation(
            bottle_id=case["bottle"].id,
            material_id=case["odorant"].id,
            parent_event_id=case["parent_event"].id,
            carrier_event_id=case["carrier_event"].id,
            parent_identity_evidence_id=case["parent_evidence"].id,
            carrier_identity_evidence_id=case["carrier_evidence"].id,
            child_label="Incomplete v/v evidence",
            child_lot_number="VV-INCOMPLETE",
            preparation_sop_sha256=_hash("vv-preparation-sop"),
            balance_calibration_sha256=_hash("vv-balance-calibration"),
            source_design_sha256=_hash("source-10pct-vv-design"),
            source_target_volume_fraction=Decimal("0.1"),
            command_id="finalize-vv-incomplete",
            actor="operator-vv",
        )


@pytest.mark.asyncio
async def test_vv_intent_rejects_missing_reference_conditions(db_session):
    case = await _closed_volumetric_preparation(
        db_session,
        include_volume_conditions=False,
    )
    with pytest.raises(
        LabTransactionError,
        match="volume_reference_conditions authority",
    ):
        await case["service"].finalize_stock_preparation(
            bottle_id=case["bottle"].id,
            material_id=case["odorant"].id,
            parent_event_id=case["parent_event"].id,
            carrier_event_id=case["carrier_event"].id,
            parent_identity_evidence_id=case["parent_evidence"].id,
            carrier_identity_evidence_id=case["carrier_evidence"].id,
            child_label="Missing-condition v/v evidence",
            child_lot_number="VV-MISSING-CONDITIONS",
            preparation_sop_sha256=_hash("vv-preparation-sop"),
            balance_calibration_sha256=_hash("vv-balance-calibration"),
            source_design_sha256=_hash("source-10pct-vv-design"),
            source_target_volume_fraction=Decimal("0.1"),
            command_id="finalize-vv-missing-conditions",
            actor="operator-vv",
        )


@pytest.mark.asyncio
async def test_vv_intent_holds_incompatible_conditions_without_changing_stock_basis(
    db_session,
):
    case = await _closed_volumetric_preparation(
        db_session,
        carrier_temperature_c=Decimal("25"),
    )
    child = await case["service"].finalize_stock_preparation(
        bottle_id=case["bottle"].id,
        material_id=case["odorant"].id,
        parent_event_id=case["parent_event"].id,
        carrier_event_id=case["carrier_event"].id,
        parent_identity_evidence_id=case["parent_evidence"].id,
        carrier_identity_evidence_id=case["carrier_evidence"].id,
        child_label="Condition-held v/v intent",
        child_lot_number="VV-CONDITION-HOLD",
        preparation_sop_sha256=_hash("vv-preparation-sop"),
        balance_calibration_sha256=_hash("vv-balance-calibration"),
        source_design_sha256=_hash("source-10pct-vv-design"),
        source_target_volume_fraction=Decimal("0.1"),
        command_id="finalize-vv-condition-hold",
        actor="operator-vv",
    )
    source_intent = child.source_json["stock_preparation_receipt"]["source_volume_intent"]
    assert source_intent["alignment_state"] == "HOLD_INCOMPATIBLE_VOLUME_CONDITIONS"
    assert source_intent["conditions_compatible"] is False
    assert child.fraction_basis == "mass_fraction"


@pytest.mark.asyncio
async def test_vv_metadata_cannot_overwrite_mass_movements_or_stock_fraction(
    db_session,
):
    case = await _closed_volumetric_preparation(
        db_session,
        parent_mass_g=Decimal("0.2"),
        carrier_mass_g=Decimal("0.8"),
        parent_volume_ul=Decimal("100"),
        carrier_volume_ul=Decimal("900"),
    )
    child = await case["service"].finalize_stock_preparation(
        bottle_id=case["bottle"].id,
        material_id=case["odorant"].id,
        parent_event_id=case["parent_event"].id,
        carrier_event_id=case["carrier_event"].id,
        parent_identity_evidence_id=case["parent_evidence"].id,
        carrier_identity_evidence_id=case["carrier_evidence"].id,
        child_label="Mass-authoritative 20 percent stock",
        child_lot_number="VV-MASS-AUTHORITY",
        preparation_sop_sha256=_hash("vv-preparation-sop"),
        balance_calibration_sha256=_hash("vv-balance-calibration"),
        source_design_sha256=_hash("source-10pct-vv-design"),
        source_target_volume_fraction=Decimal("0.1"),
        command_id="finalize-vv-mass-authority",
        actor="operator-vv",
    )

    receipt = child.source_json["stock_preparation_receipt"]
    assert receipt["source_volume_intent"]["alignment_state"] == ("NOMINAL_SOURCE_RATIO_MATCH_ONLY")
    assert receipt["source_volume_intent"]["active_mass_or_dose_authority"] is False
    assert receipt["source_volume_intent"]["volume_fraction_stock_created"] is False
    assert receipt["inventory_conservation"] == {
        "parent_consumed_mass_g": "0.2",
        "carrier_consumed_mass_g": "0.8",
        "child_initial_mass_g": "1",
        "mass_delta_g": "0",
    }
    assert receipt["child"]["active_mass_g"] == "0.2"
    assert receipt["child"]["active_fraction"] == "0.2"
    assert receipt["child"]["fraction_basis"] == "mass_fraction"
    assert child.active_fraction_decimal_text == "0.2"
    assert child.fraction_basis == "mass_fraction"


@pytest.mark.asyncio
async def test_vv_intent_uses_only_component_delivery_volumes_and_holds_ratio_mismatch(
    db_session,
):
    case = await _closed_volumetric_preparation(
        db_session,
        parent_volume_ul=Decimal("90"),
    )
    child = await case["service"].finalize_stock_preparation(
        bottle_id=case["bottle"].id,
        material_id=case["odorant"].id,
        parent_event_id=case["parent_event"].id,
        carrier_event_id=case["carrier_event"].id,
        parent_identity_evidence_id=case["parent_evidence"].id,
        carrier_identity_evidence_id=case["carrier_evidence"].id,
        child_label="Ratio-held v/v intent",
        child_lot_number="VV-RATIO-HOLD",
        preparation_sop_sha256=_hash("vv-preparation-sop"),
        balance_calibration_sha256=_hash("vv-balance-calibration"),
        source_design_sha256=_hash("source-10pct-vv-design"),
        source_target_volume_fraction=Decimal("0.1"),
        command_id="finalize-vv-ratio-hold",
        actor="operator-vv",
    )
    receipt = child.source_json["stock_preparation_receipt"]
    source_intent = receipt["source_volume_intent"]
    assert source_intent["alignment_state"] == "HOLD_VOLUME_RATIO_MISMATCH"
    assert source_intent["denominator"].endswith("BEFORE_MIXING")
    assert source_intent["final_mixed_solution_volume_used"] is False
    assert "final_mixed_volume" not in source_intent
    assert receipt["inventory_conservation"]["child_initial_mass_g"] == "1"
    assert receipt["child"]["active_fraction"] == "0.1"


@pytest.mark.asyncio
async def test_finalize_is_idempotent_and_rejects_command_reuse(db_session):
    case = await _closed_preparation(db_session)
    service = case["service"]
    command = {
        "bottle_id": case["bottle"].id,
        "material_id": case["odorant"].id,
        "parent_event_id": case["parent_event"].id,
        "carrier_event_id": case["carrier_event"].id,
        "parent_identity_evidence_id": case["parent_evidence"].id,
        "carrier_identity_evidence_id": case["carrier_evidence"].id,
        "child_label": "Lemonile 1% in DPG",
        "child_lot_number": "LEM-1PCT-20260816",
        "preparation_sop_sha256": _hash("gravimetric-preparation-sop-v1"),
        "balance_calibration_sha256": _hash("balance-calibration-20260816"),
        "command_id": "finalize-idempotent",
        "actor": "operator-a",
    }

    first = await service.finalize_stock_preparation(**command)
    second = await service.finalize_stock_preparation(**command)
    assert second.id == first.id
    assert second.source_json == first.source_json

    with pytest.raises(IdempotencyConflictError):
        await service.finalize_stock_preparation(**{**command, "child_lot_number": "DIFFERENT-LOT"})


@pytest.mark.asyncio
async def test_finalize_rejects_missing_uncertainty(db_session):
    case = await _closed_preparation(db_session, uncertainty=None)
    service = case["service"]

    with pytest.raises(LabTransactionError, match="standard uncertainty"):
        await service.finalize_stock_preparation(
            bottle_id=case["bottle"].id,
            material_id=case["odorant"].id,
            parent_event_id=case["parent_event"].id,
            carrier_event_id=case["carrier_event"].id,
            parent_identity_evidence_id=case["parent_evidence"].id,
            carrier_identity_evidence_id=case["carrier_evidence"].id,
            child_label="Lemonile 1% in DPG",
            child_lot_number="LEM-1PCT-20260816",
            preparation_sop_sha256=_hash("gravimetric-preparation-sop-v1"),
            balance_calibration_sha256=_hash("balance-calibration-20260816"),
            command_id="finalize-missing-uncertainty",
            actor="operator-a",
        )


@pytest.mark.asyncio
async def test_finalize_rejects_nonexact_identity_evidence(db_session):
    case = await _closed_preparation(db_session)
    service = case["service"]
    heuristic = await service.record_evidence(
        claim_key="stock-identity:heuristic",
        classification="HEURISTIC",
        source_locator="chat://unverified-label",
        source_version="1",
        method="Text-only inference",
        assumptions=("Identity not witnessed",),
        limitations=("No lot authority",),
        payload_sha256=_hash("heuristic-evidence"),
    )

    with pytest.raises(LabTransactionError, match="classified EXACT"):
        await service.finalize_stock_preparation(
            bottle_id=case["bottle"].id,
            material_id=case["odorant"].id,
            parent_event_id=case["parent_event"].id,
            carrier_event_id=case["carrier_event"].id,
            parent_identity_evidence_id=heuristic.id,
            carrier_identity_evidence_id=case["carrier_evidence"].id,
            child_label="Lemonile 1% in DPG",
            child_lot_number="LEM-1PCT-20260816",
            preparation_sop_sha256=_hash("gravimetric-preparation-sop-v1"),
            balance_calibration_sha256=_hash("balance-calibration-20260816"),
            command_id="finalize-nonexact-evidence",
            actor="operator-a",
        )


@pytest.mark.asyncio
async def test_finalize_rejects_open_or_ambiguous_preparation_bottle(db_session):
    case = await _closed_preparation(db_session)
    service = case["service"]
    parent_stock_id = case["parent"].id
    carrier_stock_id = case["carrier"].id
    odorant_id = case["odorant"].id
    parent_evidence_id = case["parent_evidence"].id
    carrier_evidence_id = case["carrier_evidence"].id
    open_bottle = await service.create_bottle("Open preparation")
    open_parent = await service.add_stock_to_bottle(
        bottle_id=open_bottle.id,
        stock_solution_id=parent_stock_id,
        mass_g=Decimal("0.1"),
        expected_sequence=1,
        command_id="open-parent",
        standard_uncertainty=0.001,
        actor="operator-a",
    )
    open_carrier = await service.add_solvent_to_bottle(
        bottle_id=open_bottle.id,
        stock_solution_id=carrier_stock_id,
        mass_g=Decimal("0.9"),
        expected_sequence=2,
        command_id="open-carrier",
        standard_uncertainty=0.001,
        actor="operator-a",
    )
    with pytest.raises(LabTransactionError, match="terminal close event"):
        await service.finalize_stock_preparation(
            bottle_id=open_bottle.id,
            material_id=odorant_id,
            parent_event_id=open_parent.id,
            carrier_event_id=open_carrier.id,
            parent_identity_evidence_id=parent_evidence_id,
            carrier_identity_evidence_id=carrier_evidence_id,
            child_label="Open child",
            child_lot_number="OPEN-LOT",
            preparation_sop_sha256=_hash("gravimetric-preparation-sop-v1"),
            balance_calibration_sha256=_hash("balance-calibration-20260816"),
            command_id="finalize-open",
            actor="operator-a",
        )

    extra_material = await service.create_material("Unexpected material")
    extra_stock = await service.create_stock_solution(
        material_id=extra_material.id,
        active_fraction=Decimal("1"),
        fraction_basis="mass_fraction",
        initial_mass_g=Decimal("1"),
        lot_number="EXTRA-LOT",
    )
    extra_stock_id = extra_stock.id
    # Re-open is impossible, so build a second bottle with an extra component before closure.
    bottle = await service.create_bottle("Ambiguous preparation")
    parent_event = await service.add_stock_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=parent_stock_id,
        mass_g=Decimal("0.1"),
        expected_sequence=1,
        command_id="amb-parent",
        standard_uncertainty=0.001,
        actor="operator-a",
    )
    carrier_event = await service.add_solvent_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=carrier_stock_id,
        mass_g=Decimal("0.8"),
        expected_sequence=2,
        command_id="amb-carrier",
        standard_uncertainty=0.001,
        actor="operator-a",
    )
    await service.add_stock_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=extra_stock_id,
        mass_g=Decimal("0.1"),
        expected_sequence=3,
        command_id="amb-extra",
        standard_uncertainty=0.001,
        actor="operator-a",
    )
    await service.close_bottle(
        bottle_id=bottle.id,
        expected_sequence=4,
        command_id="amb-close",
        actor="operator-a",
    )

    with pytest.raises(LabTransactionError, match="exactly one parent and one carrier"):
        await service.finalize_stock_preparation(
            bottle_id=bottle.id,
            material_id=odorant_id,
            parent_event_id=parent_event.id,
            carrier_event_id=carrier_event.id,
            parent_identity_evidence_id=parent_evidence_id,
            carrier_identity_evidence_id=carrier_evidence_id,
            child_label="Ambiguous child",
            child_lot_number="AMB-LOT",
            preparation_sop_sha256=_hash("gravimetric-preparation-sop-v1"),
            balance_calibration_sha256=_hash("balance-calibration-20260816"),
            command_id="finalize-ambiguous",
            actor="operator-a",
        )


@pytest.mark.asyncio
async def test_stock_preparation_is_available_through_native_lab_api(
    client,
    db_session,
):
    odorant = (
        await client.post(
            "/api/v1/lab/materials",
            json={"canonical_name": "API preparation odorant"},
        )
    ).json()
    carrier_material = (
        await client.post(
            "/api/v1/lab/materials",
            json={"canonical_name": "API preparation DPG"},
        )
    ).json()
    parent = (
        await client.post(
            "/api/v1/lab/stocks",
            json={
                "material_id": odorant["id"],
                "active_fraction": "1",
                "fraction_basis": "mass_fraction",
                "initial_mass_g": 10,
                "supplier": "supplier-a",
                "lot_number": "API-PARENT-LOT",
            },
        )
    ).json()
    carrier = (
        await client.post(
            "/api/v1/lab/stocks",
            json={
                "material_id": carrier_material["id"],
                "active_fraction": "1",
                "fraction_basis": "mass_fraction",
                "initial_mass_g": 100,
                "supplier": "supplier-b",
                "lot_number": "API-CARRIER-LOT",
            },
        )
    ).json()
    bottle = (
        await client.post(
            "/api/v1/lab/bottles",
            json={"label": "API 1% preparation"},
        )
    ).json()
    parent_event_response = await client.post(
        f"/api/v1/lab/bottles/{bottle['id']}/additions",
        json={
            "stock_solution_id": parent["id"],
            "mass_g": "0.1",
            "measured_volume_ul": "10.00",
            "expected_sequence": 1,
            "command_id": "api-prep-parent",
            "standard_uncertainty": "0.001",
            "volume_standard_uncertainty_ul": "0.100",
            "volume_measurement_method": "ISO 8655-6 gravimetric delivery calibration",
            "volume_device_id": "API-PIPETTE-10UL",
            "volume_device_calibration_sha256": _hash("api-parent-pipette"),
            "volume_reference_temperature_c": "20.0",
            "volume_reference_conditions": {
                "delivery_mode": "EX",
                "reference_standard": "ISO_8655_6_2022",
            },
            "actor": "api-operator",
            "role": "material",
        },
    )
    assert parent_event_response.status_code == 201
    carrier_event_response = await client.post(
        f"/api/v1/lab/bottles/{bottle['id']}/additions",
        json={
            "stock_solution_id": carrier["id"],
            "mass_g": "9.9",
            "measured_volume_ul": "990.0",
            "expected_sequence": 2,
            "command_id": "api-prep-carrier",
            "standard_uncertainty": "0.001",
            "volume_standard_uncertainty_ul": "0.500",
            "volume_measurement_method": "ISO 8655-6 gravimetric delivery calibration",
            "volume_device_id": "API-PIPETTE-1000UL",
            "volume_device_calibration_sha256": _hash("api-carrier-pipette"),
            "volume_reference_temperature_c": "20.00",
            "volume_reference_conditions": {
                "delivery_mode": "EX",
                "reference_standard": "ISO_8655_6_2022",
            },
            "actor": "api-operator",
            "role": "solvent",
        },
    )
    assert carrier_event_response.status_code == 201
    close_response = await client.post(
        f"/api/v1/lab/bottles/{bottle['id']}/close",
        json={
            "expected_sequence": 3,
            "command_id": "api-prep-close",
            "actor": "api-operator",
        },
    )
    assert close_response.status_code == 201

    service = LabService(db_session)
    parent_evidence = await _exact_evidence(service, "api-parent")
    carrier_evidence = await _exact_evidence(service, "api-carrier")
    final_response = await client.post(
        "/api/v1/lab/stocks/preparations/finalize",
        json={
            "bottle_id": bottle["id"],
            "material_id": odorant["id"],
            "parent_event_id": parent_event_response.json()["id"],
            "carrier_event_id": carrier_event_response.json()["id"],
            "parent_identity_evidence_id": parent_evidence.id,
            "carrier_identity_evidence_id": carrier_evidence.id,
            "child_label": "API odorant 1% in DPG",
            "child_lot_number": "API-CHILD-LOT",
            "preparation_sop_sha256": _hash("api-sop"),
            "balance_calibration_sha256": _hash("api-balance"),
            "source_design_sha256": _hash("api-source-1pct-vv-design"),
            "source_target_volume_fraction": "0.0100",
            "command_id": "api-prep-finalize",
            "actor": "api-operator",
        },
    )
    assert final_response.status_code == 201
    child = final_response.json()
    assert child["active_fraction_decimal_text"] == "0.01"
    assert child["fraction_basis"] == "mass_fraction"
    assert child["source_json"]["stock_preparation_receipt"]["schema_version"] == (
        "lab-stock-preparation-receipt-v2"
    )
    assert (
        child["source_json"]["stock_preparation_receipt"]["source_volume_intent"]["alignment_state"]
        == "NOMINAL_SOURCE_RATIO_MATCH_ONLY"
    )
    api_receipt = child["source_json"]["stock_preparation_receipt"]
    parent_volume_delivery = api_receipt["parent"]["volume_delivery"]
    assert parent_volume_delivery["measured_volume_ul"] == "10.00"
    assert parent_volume_delivery["canonical_measured_volume_ul"] == "10"
    assert parent_volume_delivery["standard_uncertainty_ul"] == "0.100"
    assert parent_volume_delivery["canonical_standard_uncertainty_ul"] == "0.1"
    assert parent_volume_delivery["unit"] == "uL"
    assert parent_volume_delivery["reference_temperature_c"] == "20.0"
    assert parent_volume_delivery["canonical_reference_temperature_c"] == "20"
    assert api_receipt["source_volume_intent"]["target_parent_input_volume_fraction"] == "0.0100"
    assert (
        api_receipt["source_volume_intent"]["canonical_target_parent_input_volume_fraction"]
        == "0.01"
    )
    assert child["source_json"]["stock_preparation_receipt"]["authority"] == {
        "formula_authority": False,
        "safety_authority": False,
        "scientific_authority": False,
        "sensory_authority": False,
        "release_authority": False,
    }
    get_response = await client.get(f"/api/v1/lab/stocks/{child['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["source_json"] == child["source_json"]
