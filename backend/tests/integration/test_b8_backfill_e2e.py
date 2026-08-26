from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models.lab_backfill import (
    BACKFILL_DASHBOARD_DIMENSIONS,
    BACKFILL_REQUIREMENT_TYPES,
    LabBackfillCampaignVersion,
    LabBackfillDashboardCell,
    LabBackfillGapItem,
    LabBackfillMaterialPriority,
    LabBackfillPrioritySignalLink,
)
from app.services.lab_backfill import (
    BackfillConflictError,
    BackfillGapCommand,
    BackfillMaterialCommand,
    BackfillSignalCommand,
    CreateBackfillCampaignCommand,
)
from app.services.lab_claims import ClaimAuthoritySupportInput
from app.services.lab_service import FormulaComponentInput, LabService
from tests.integration.test_b7_claim_authority_e2e import (
    _command as _b7_command,
)
from tests.integration.test_b7_claim_authority_e2e import (
    _formula_subject as _b7_formula_subject,
)
from tests.integration.test_b7_claim_authority_e2e import (
    _legacy_claim as _b7_legacy_claim,
)
from tests.integration.test_b7_claim_authority_e2e import (
    _property_assertion as _b7_property_assertion,
)

NOW = datetime(2026, 7, 31, 3, 0, tzinfo=timezone.utc)
B8_MODELS = (
    LabBackfillCampaignVersion,
    LabBackfillMaterialPriority,
    LabBackfillPrioritySignalLink,
    LabBackfillGapItem,
    LabBackfillDashboardCell,
)


def _missing_gaps(material_id: str) -> tuple[BackfillGapCommand, ...]:
    return tuple(
        BackfillGapCommand(
            requirement_type=requirement,
            state="MISSING",
            evidence_class="UNKNOWN",
            claim_authority_version_id=None,
            applicability_scope={"material_id": material_id},
            missing_requirements=(requirement,),
        )
        for requirement in BACKFILL_REQUIREMENT_TYPES
    )


def _exact_identity_gaps(
    *,
    material_id: str,
    authority_id: str,
    identity_scope: dict,
    accepted_state: str = "ACCEPTED_EXACT",
) -> tuple[BackfillGapCommand, ...]:
    return tuple(
        BackfillGapCommand(
            requirement_type=requirement,
            state=(
                accepted_state
                if requirement == "EXACT_IDENTITY"
                else "MISSING"
            ),
            evidence_class=(
                "LITERATURE_DERIVED"
                if requirement == "EXACT_IDENTITY"
                else "UNKNOWN"
            ),
            claim_authority_version_id=(
                authority_id if requirement == "EXACT_IDENTITY" else None
            ),
            applicability_scope=(
                {
                    "material_id": material_id,
                    "identity_scope": identity_scope,
                    "condition_scope": {},
                }
                if requirement == "EXACT_IDENTITY"
                else {"material_id": material_id}
            ),
            missing_requirements=(
                () if requirement == "EXACT_IDENTITY" else (requirement,)
            ),
        )
        for requirement in BACKFILL_REQUIREMENT_TYPES
    )


def _campaign(
    *,
    material_id: str,
    stock_id: str,
    parent_version_id: str | None = None,
) -> CreateBackfillCampaignCommand:
    return CreateBackfillCampaignCommand(
        campaign_key="current-lab-backfill",
        name="Current laboratory backfill",
        purpose="Prioritize unresolved scientific data without promotion.",
        as_of_utc=NOW,
        reviewer_pseudonym="b8-reviewer",
        reviewed_at=NOW,
        parent_version_id=parent_version_id,
        materials=(
            BackfillMaterialCommand(
                material_id=material_id,
                chemical_family=None,
                signals=(
                    BackfillSignalCommand(
                        signal_type="CURRENT_INVENTORY",
                        source_id=stock_id,
                    ),
                ),
                gaps=_missing_gaps(material_id),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_b8_campaign_persists_and_reconstructs_exact_snapshot(
    db_session,
):
    service = LabService(db_session)
    material = await service.create_material("B8 current material")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=10.0,
        supplier="B8 fixture",
        lot_number="B8-LOT",
    )

    campaign = await service.create_backfill_campaign(
        _campaign(material_id=material.id, stock_id=stock.id)
    )

    assert campaign.version_number == 1
    assert campaign.parent_version_id is None
    assert campaign.material_count == 1
    assert campaign.signal_count == 1
    assert campaign.gap_count == len(BACKFILL_REQUIREMENT_TYPES)
    assert campaign.missing_count == len(BACKFILL_REQUIREMENT_TYPES)
    assert campaign.release_authority is False

    priorities = await service.repository.backfill_material_priorities(
        campaign.id
    )
    assert len(priorities) == 1
    assert priorities[0].material_id == material.id
    assert priorities[0].rank == 1
    assert priorities[0].primary_priority_class == "CURRENT_INVENTORY"

    signals = await service.repository.backfill_priority_signals(
        priorities[0].id
    )
    assert len(signals) == 1
    assert signals[0].signal_type == "CURRENT_INVENTORY"
    assert signals[0].stock_solution_id == stock.id
    assert signals[0].signal_value_json["positive_balance"] is True

    gaps = await service.repository.backfill_gap_items(priorities[0].id)
    assert {gap.requirement_type for gap in gaps} == set(
        BACKFILL_REQUIREMENT_TYPES
    )
    assert {gap.state for gap in gaps} == {"MISSING"}

    dashboard = await service.repository.backfill_dashboard_cells(campaign.id)
    assert {cell.dimension for cell in dashboard} == set(
        BACKFILL_DASHBOARD_DIMENSIONS
    )
    assert all(
        cell.requirements_total
        == cell.accepted_exact_count
        + cell.accepted_scoped_count
        + cell.weak_count
        + cell.conflicted_count
        + cell.unknown_count
        + cell.missing_count
        + cell.not_applicable_count
        for cell in dashboard
    )

    reconstructed = await service.reconstruct_backfill_campaign(campaign.id)
    assert reconstructed["integrity_verified"] is True
    assert reconstructed["content_sha256"] == campaign.content_sha256
    assert reconstructed["materials"][0]["material_id"] == material.id
    assert reconstructed["materials"][0]["rank"] == 1
    assert reconstructed["materials"][0]["signals"][0]["source_id"] == stock.id
    assert "aggregate_coverage_score" not in reconstructed


@pytest.mark.asyncio
async def test_b8_rejects_cross_material_inventory_and_rolls_back_atomically(
    db_session,
):
    service = LabService(db_session)
    source_material = await service.create_material("B8 stock owner")
    target_material = await service.create_material("B8 wrong target")
    stock = await service.create_stock_solution(
        material_id=source_material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=1.0,
    )

    with pytest.raises(BackfillConflictError) as error:
        await service.create_backfill_campaign(
            _campaign(material_id=target_material.id, stock_id=stock.id)
        )
    assert error.value.code == "BACKFILL_SIGNAL_MATERIAL_MISMATCH"

    for model in B8_MODELS:
        assert (
            await db_session.scalar(select(func.count()).select_from(model))
            == 0
        )


@pytest.mark.asyncio
async def test_b8_revision_requires_latest_parent_and_preserves_chain(
    db_session,
):
    service = LabService(db_session)
    material = await service.create_material("B8 revision material")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=2.0,
    )
    root = await service.create_backfill_campaign(
        _campaign(material_id=material.id, stock_id=stock.id)
    )
    revision = await service.create_backfill_campaign(
        _campaign(
            material_id=material.id,
            stock_id=stock.id,
            parent_version_id=root.id,
        )
    )

    assert revision.version_number == 2
    assert revision.parent_version_id == root.id
    assert revision.parent_sha256 == root.content_sha256

    with pytest.raises(BackfillConflictError) as error:
        await service.create_backfill_campaign(
            _campaign(
                material_id=material.id,
                stock_id=stock.id,
                parent_version_id=root.id,
            )
        )
    assert error.value.code == "BACKFILL_PARENT_NOT_LATEST"


@pytest.mark.asyncio
async def test_b8_resolves_reviewed_formula_high_dose_and_model_signals(
    db_session,
):
    service = LabService(db_session)
    material = await service.create_material("B8 structural material")
    diluent = await service.create_material("B8 structural diluent")
    material_stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=5.0,
    )
    diluent_stock = await service.create_stock_solution(
        material_id=diluent.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=5.0,
    )
    formula = await service.create_formula("B8 reviewed formula")
    formula_version = await service.add_formula_version(
        formula.id,
        brief={"status": "caller prose is not authority"},
        constraints={},
        components=(
            FormulaComponentInput(
                stock_solution_id=material_stock.id,
                requested_mass_g=0.8,
            ),
            FormulaComponentInput(
                stock_solution_id=diluent_stock.id,
                requested_mass_g=0.2,
            ),
        ),
    )
    components = await service.repository.formula_components(
        formula_version.id
    )
    material_component = next(
        component
        for component in components
        if component.stock_solution_id == material_stock.id
    )
    experiment = await service.create_experiment(
        "B8 sensitivity",
        protocol={"version": "fixture-v1"},
    )
    prediction = await service.record_prediction(
        experiment_id=experiment.id,
        sample_id=None,
        model_key="b8-sensitivity-model",
        model_version="1.0.0",
        status="COMPUTED",
        prediction={
            "normalized_sensitivity_by_material": {material.id: 0.93}
        },
    )
    command = CreateBackfillCampaignCommand(
        campaign_key="formula-model-backfill",
        name="Formula and model backfill",
        purpose="Verify typed B8 formula and model sources.",
        as_of_utc=NOW,
        reviewer_pseudonym="b8-formula-reviewer",
        reviewed_at=NOW,
        materials=(
            BackfillMaterialCommand(
                material_id=material.id,
                chemical_family="WOODY",
                signals=(
                    BackfillSignalCommand(
                        signal_type="ACTIVE_FORMULA",
                        source_id=material_component.id,
                        operational_status="ACTIVE",
                    ),
                    BackfillSignalCommand(
                        signal_type="HIGH_DOSE_STRUCTURE",
                        source_id=material_component.id,
                    ),
                    BackfillSignalCommand(
                        signal_type="MODEL_SENSITIVITY",
                        source_id=prediction.id,
                        normalized_sensitivity=0.93,
                    ),
                ),
                gaps=_missing_gaps(material.id),
            ),
        ),
    )

    campaign = await service.create_backfill_campaign(command)
    priority = (
        await service.repository.backfill_material_priorities(campaign.id)
    )[0]
    assert priority.primary_priority_class == "ACTIVE_OR_SHIPPED_FORMULA"
    assert priority.signal_vector_json["active_or_shipped_formula"] is True
    assert priority.signal_vector_json["high_dose_structure"] == pytest.approx(
        0.8
    )
    assert priority.signal_vector_json["model_sensitivity"] == pytest.approx(
        0.93
    )
    signals = await service.repository.backfill_priority_signals(priority.id)
    by_type = {signal.signal_type: signal for signal in signals}
    assert by_type["ACTIVE_FORMULA"].applicability_json[
        "reviewer_pseudonym"
    ] == "b8-formula-reviewer"
    assert by_type["MODEL_SENSITIVITY"].evidence_class == "MODEL_ESTIMATED"
    assert (
        await service.reconstruct_backfill_campaign(campaign.id)
    )["integrity_verified"] is True


@pytest.mark.asyncio
async def test_b8_accepts_only_scope_compatible_exact_b7_authority(
    db_session,
):
    service = LabService(db_session)
    material = await service.create_material("B8 exact identity material")
    subject = await _b7_formula_subject(
        db_session,
        "b8 exact identity material",
    )
    legacy = await _b7_legacy_claim(
        db_session,
        claim_type="IDENTITY",
        subject_type="FORMULA_VERSION",
        subject_id=subject.id,
        label="b8-exact-identity",
    )
    identity_scope = {
        "identity_scope": "CHEMICAL_ENTITY",
        "material_id": material.id,
        "chemical_name": "B8 exact identity material",
        "identifier": "B8-IDENTITY-1",
    }
    first, _ = await _b7_property_assertion(
        db_session,
        label="b8-exact-identity-source-a",
        identity_scope=identity_scope,
        identity_scope_name="CHEMICAL_ENTITY",
        property_type="CHEMICAL_IDENTITY",
        value="B8 exact identity material",
        unit="dimensionless",
        conditions={},
        evidence_class="LITERATURE_DERIVED",
        standard_uncertainty=None,
    )
    second, _ = await _b7_property_assertion(
        db_session,
        label="b8-exact-identity-source-b",
        identity_scope=identity_scope,
        identity_scope_name="CHEMICAL_ENTITY",
        property_type="CHEMICAL_IDENTITY",
        value="B8 exact identity material",
        unit="dimensionless",
        conditions={},
        evidence_class="LITERATURE_DERIVED",
        standard_uncertainty=None,
    )
    authority = await service.create_claim_authority_version(
        _b7_command(
            legacy,
            payload={
                "chemical_name": "B8 exact identity material",
                "identifier": "B8-IDENTITY-1",
            },
            identity_scope=identity_scope,
            condition_scope={},
            supports=(
                ClaimAuthoritySupportInput(
                    "PROPERTY_ASSERTION",
                    first.id,
                ),
                ClaimAuthoritySupportInput(
                    "PROPERTY_ASSERTION",
                    second.id,
                ),
            ),
        )
    )
    assert authority.decision == "ALLOW_EXACT"

    command = CreateBackfillCampaignCommand(
        campaign_key="b7-exact-gap-backfill",
        name="B7 exact gap backfill",
        purpose="Verify exact B7 authority remains the only promotion path.",
        as_of_utc=NOW,
        reviewer_pseudonym="b8-b7-reviewer",
        reviewed_at=NOW,
        materials=(
            BackfillMaterialCommand(
                material_id=material.id,
                chemical_family=None,
                signals=(),
                gaps=_exact_identity_gaps(
                    material_id=material.id,
                    authority_id=authority.id,
                    identity_scope=identity_scope,
                ),
            ),
        ),
    )
    campaign = await service.create_backfill_campaign(command)
    priority = (
        await service.repository.backfill_material_priorities(campaign.id)
    )[0]
    gap = next(
        item
        for item in await service.repository.backfill_gap_items(priority.id)
        if item.requirement_type == "EXACT_IDENTITY"
    )
    assert gap.state == "ACCEPTED_EXACT"
    assert gap.claim_authority_version_id == authority.id
    assert gap.upstream_content_sha256 == authority.content_sha256
    assert (
        await service.reconstruct_backfill_campaign(campaign.id)
    )["integrity_verified"] is True

    mismatched = CreateBackfillCampaignCommand(
        campaign_key="b7-mislabeled-gap-backfill",
        name="B7 mislabeled gap",
        purpose="Reject an exact decision labeled as scoped.",
        as_of_utc=NOW,
        reviewer_pseudonym="b8-b7-reviewer",
        reviewed_at=NOW,
        materials=(
            BackfillMaterialCommand(
                material_id=material.id,
                chemical_family=None,
                signals=(),
                gaps=_exact_identity_gaps(
                    material_id=material.id,
                    authority_id=authority.id,
                    identity_scope=identity_scope,
                    accepted_state="ACCEPTED_SCOPED",
                ),
            ),
        ),
    )
    with pytest.raises(BackfillConflictError) as error:
        await service.create_backfill_campaign(mismatched)
    assert error.value.code == "BACKFILL_B7_DECISION_MISMATCH"
