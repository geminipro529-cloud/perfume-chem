from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.services.lab_regulatory import (
    RegulatoryAuthorityConflictError,
    SupplierDocumentBindingInput,
)
from app.services.lab_science import RegulatoryAssessmentInput
from app.services.lab_service import LabService
from tests.a2_planning_fixtures import _approved_plan
from tests.unit.test_b6_regulatory_service import (
    NOW,
    _accept_source,
    _composition_document_binding,
    _composition_entry_input,
    _composition_profile_input,
    _evaluation_input,
    _evaluation_stock,
    _formula_version_for_stocks,
    _natural_stock,
    _official_source,
    _regulatory_rule_graph,
    _regulatory_source_input,
    _required_supplier_bindings,
    _rule_input,
    _source_document_input,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
B6_HEAD = "head"


def _config(database_path: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option(
        "sqlalchemy.url",
        f"sqlite:///{database_path.as_posix()}",
    )
    return config


@asynccontextmanager
async def _migrated_service(database_path: Path):
    command.upgrade(_config(database_path), B6_HEAD)
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    try:
        async with factory() as session:
            yield session, LabService(session)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_b6_migrated_formula_and_build_plan_persist_scoped_findings(
    tmp_path,
):
    async with _migrated_service(tmp_path / "b6-formula-build.db") as (
        session,
        service,
    ):
        material, stock = await _evaluation_stock(
            service,
            name="Linalool migrated formula",
            cas_number="78-70-6",
            active_fraction=0.2,
            origin="SYNTHETIC",
            lot_number="B6-E2E-FORMULA",
        )
        formula = await _formula_version_for_stocks(
            service,
            (stock,),
            finished_concentration=0.1,
        )
        bindings = await _required_supplier_bindings(
            service,
            stock,
            digest_seed=1,
        )
        current, rule, watch, watch_rule = await _regulatory_rule_graph(
            service,
            maximum_fraction=0.03,
            material_id=material.id,
        )
        formula_snapshot = await service.evaluate_regulatory_snapshot(
            _evaluation_input(
                "FORMULA_VERSION",
                formula.id,
                primary_source_version_id=current.id,
                current_source_ids=(current.id,),
                watch_source_ids=(watch.id,),
                rule_ids=(rule.id, watch_rule.id),
                supplier_binding_ids=tuple(
                    item.id for item in bindings
                ),
            )
        )

        build_service, plan, _line, build_stock = await _approved_plan(session)
        build_material = await build_service.repository.get_material(
            build_stock.material_id
        )
        assert build_material is not None
        build_stock.supplier = "Evaluation Supplier"
        build_stock.lot_number = "B6-E2E-BUILD"
        build_stock.source_json = {
            "supplier_product": "Jasmine Absolute",
            "supplier_product_code": "JASMINE-ABSOLUTE",
            "grade": "evaluation grade",
            "origin": "SYNTHETIC",
        }
        await session.flush()
        build_bindings = await _required_supplier_bindings(
            build_service,
            build_stock,
            digest_seed=4,
        )
        (
            build_current,
            build_rule,
            build_watch,
            build_watch_rule,
        ) = await _regulatory_rule_graph(
            build_service,
            maximum_fraction=0.2,
            material_id=build_material.id,
            cas_number=None,
        )
        build_snapshot = await build_service.evaluate_regulatory_snapshot(
            _evaluation_input(
                "BUILD_PLAN_VERSION",
                plan.id,
                primary_source_version_id=build_current.id,
                current_source_ids=(build_current.id,),
                watch_source_ids=(build_watch.id,),
                rule_ids=(build_rule.id, build_watch_rule.id),
                supplier_binding_ids=tuple(
                    item.id for item in build_bindings
                ),
                finished_product_concentration=1.0,
            )
        )
        await session.commit()

        formula_findings = (
            await service.repository.regulatory_authority_findings(
                formula_snapshot.id
            )
        )
        build_findings = (
            await service.repository.regulatory_authority_findings(
                build_snapshot.id
            )
        )
        assert formula_snapshot.result_state == "PASS_FOR_DECLARED_SCOPE"
        assert [
            (item.enforced, item.result_state)
            for item in formula_findings
        ] == [
            (True, "PASS_FOR_DECLARED_SCOPE"),
            (False, "NOT_EVALUATED"),
        ]
        assert build_snapshot.result_state == "PASS_FOR_DECLARED_SCOPE"
        assert build_findings[0].observed_fraction == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_b6_migrated_eu_allergen_transition_and_natural_aggregation(
    tmp_path,
):
    async with _migrated_service(tmp_path / "b6-eu-natural.db") as (
        session,
        service,
    ):
        stock = await _natural_stock(service)
        formula = await _formula_version_for_stocks(
            service,
            (stock,),
            finished_concentration=0.001,
        )
        required = await _required_supplier_bindings(
            service,
            stock,
            digest_seed=7,
        )
        composition_binding = await _composition_document_binding(
            service,
            stock.id,
        )
        profile = await service.record_regulatory_composition_profile(
            _composition_profile_input(
                stock.id,
                composition_binding.id,
                entries=(
                    _composition_entry_input(
                        constituent_name="Limonene",
                        cas_number="138-86-3",
                        fraction=0.35,
                    ),
                ),
            )
        )
        official = await _official_source(
            service,
            digest="e" * 64,
            title="Commission Regulation EU 2023/1545",
        )
        eu_source = await service.register_regulatory_source_version(
            _regulatory_source_input(
                official.id,
                authority_family="JURISDICTIONAL_LEGISLATION",
                identifier="Commission Regulation (EU) 2023/1545",
                published_version="2023/1545",
                jurisdiction="EU",
                notified_on=date(2023, 7, 26),
                effective_from=date(2023, 8, 16),
            )
        )
        allergen_rule = await service.register_regulatory_rule_version(
            _rule_input(
                eu_source.id,
                rule_family="ALLERGEN_LABELING",
                rule_identifier="EU:2023/1545:LIMONENE:LEAVE_ON",
                material_id=None,
                substance_name="Limonene",
                cas_number="138-86-3",
                jurisdiction="EU",
                product_category="COSMETIC",
                use_classification="LEAVE_ON",
                rule_kind="DECLARATION_THRESHOLD",
                threshold_fraction=0.00001,
                maximum_fraction=None,
                declaration_wording="Limonene",
                effective_from=date(2023, 8, 16),
                placement_transition_end=date(2026, 7, 31),
                availability_transition_end=date(2028, 7, 31),
            )
        )
        base = _evaluation_input(
            "FORMULA_VERSION",
            formula.id,
            primary_source_version_id=eu_source.id,
            current_source_ids=(eu_source.id,),
            watch_source_ids=(),
            rule_ids=(allergen_rule.id,),
            supplier_binding_ids=tuple(
                item.id for item in (*required, composition_binding)
            ),
            composition_profile_ids=(profile.id,),
            finished_product_concentration=0.001,
        )
        base = replace(
            base,
            jurisdiction="EU",
            product_category="COSMETIC",
            use_classification="LEAVE_ON",
            market_action="PLACE_ON_MARKET",
        )

        transition_snapshot = await service.evaluate_regulatory_snapshot(
            replace(base, market_action_on=date(2026, 7, 31))
        )
        missing_label = await service.evaluate_regulatory_snapshot(
            replace(base, market_action_on=date(2026, 8, 1))
        )
        declared = await service.evaluate_regulatory_snapshot(
            replace(
                base,
                market_action_on=date(2026, 8, 1),
                declared_allergen_labels=("Limonene",),
            )
        )
        await session.commit()

        declared_finding = (
            await service.repository.regulatory_authority_findings(
                declared.id
            )
        )[0]
        assert transition_snapshot.result_state == "NOT_EVALUATED"
        assert missing_label.result_state == "FAIL"
        assert declared.result_state == "PASS_FOR_DECLARED_SCOPE"
        assert declared_finding.observed_fraction == pytest.approx(0.00035)


@pytest.mark.asyncio
async def test_b6_migrated_unknown_natural_never_hides_known_failure(
    tmp_path,
):
    async with _migrated_service(tmp_path / "b6-lattice.db") as (
        session,
        service,
    ):
        material, synthetic = await _evaluation_stock(
            service,
            name="Known lower bound",
            cas_number="78-70-6",
            active_fraction=1.0,
            origin="SYNTHETIC",
            lot_number="B6-E2E-KNOWN",
        )
        _, natural = await _evaluation_stock(
            service,
            name="Unknown natural",
            cas_number="8000-00-9",
            active_fraction=1.0,
            origin="NATURAL",
            lot_number="B6-E2E-UNKNOWN",
        )
        formula = await _formula_version_for_stocks(
            service,
            (synthetic, natural),
            finished_concentration=0.2,
        )
        synthetic_documents = await _required_supplier_bindings(
            service,
            synthetic,
            digest_seed=1,
        )
        natural_documents = await _required_supplier_bindings(
            service,
            natural,
            digest_seed=4,
        )
        unknown_profile = (
            await service.record_regulatory_composition_profile(
                _composition_profile_input(
                    natural.id,
                    None,
                    composition_basis="UNKNOWN",
                    completeness="UNKNOWN",
                    entries=(),
                    limitations=("composition unavailable",),
                )
            )
        )
        current, rule, watch, watch_rule = await _regulatory_rule_graph(
            service,
            maximum_fraction=0.05,
            material_id=material.id,
        )
        snapshot = await service.evaluate_regulatory_snapshot(
            _evaluation_input(
                "FORMULA_VERSION",
                formula.id,
                primary_source_version_id=current.id,
                current_source_ids=(current.id,),
                watch_source_ids=(watch.id,),
                rule_ids=(rule.id, watch_rule.id),
                supplier_binding_ids=tuple(
                    item.id
                    for item in synthetic_documents + natural_documents
                ),
                composition_profile_ids=(unknown_profile.id,),
                finished_product_concentration=0.2,
            )
        )
        await session.commit()

        assert snapshot.result_state == "FAIL"
        assert "NATURAL_COMPOSITION_UNKNOWN" in (
            snapshot.unresolved_items_json
        )


@pytest.mark.asyncio
async def test_b6_migrated_supplier_mismatch_and_a2_pass_fail_closed(
    tmp_path,
):
    async with _migrated_service(tmp_path / "b6-fail-closed.db") as (
        session,
        service,
    ):
        stock = await _natural_stock(service)
        source = await service.register_source_document(
            _source_document_input(
                source_type="SUPPLIER_COA",
                artifact_sha256="f" * 64,
                title="Mismatched supplier grade",
            )
        )
        await _accept_source(
            service,
            source.id,
            scope="supplier_regulatory_document",
        )
        with pytest.raises(RegulatoryAuthorityConflictError) as rejected:
            await service.bind_supplier_regulatory_document(
                SupplierDocumentBindingInput(
                    stock_solution_id=stock.id,
                    scope="SUPPLIER_LOT",
                    supplier="Supplier A",
                    supplier_product="Bergamot FCF",
                    supplier_product_code="BG-FCF",
                    grade="wrong grade",
                    document_type="SUPPLIER_COA",
                    document_version="test-version",
                    lot_number="LOT-42",
                    effective_on=date(2026, 7, 1),
                    expires_on=date(2027, 7, 1),
                    source_document_version_id=source.id,
                    source_locator={"section": "composition"},
                )
            )
        assert rejected.value.code == "SUPPLIER_IDENTITY_MISMATCH"

        formula = await _formula_version_for_stocks(
            service,
            (stock,),
            finished_concentration=0.1,
        )
        evidence = await service.record_evidence(
            claim_key="b6:e2e:legacy-a2-pass",
            classification="EXACT",
            source_locator="test://b6-e2e-legacy",
            source_version="1",
            method="migrated B6 fail-closed test",
            assumptions=(),
            limitations=(),
            payload_sha256=None,
        )
        assessment = await service.create_regulatory_assessment_version(
            RegulatoryAssessmentInput(
                schema_version="a2-regulatory-v1",
                subject_type="FORMULA_VERSION",
                subject_id=formula.id,
                standard_identifier="legacy-standard",
                standard_amendment="legacy",
                standard_state="CURRENT",
                source_evidence_record_id=evidence.id,
                jurisdiction="GLOBAL",
                product_category="IFRA_CATEGORY_4",
                concentration_basis="mass_fraction",
                finished_product_concentration=0.1,
                effective_date=date(2026, 1, 1),
                evaluated_at=NOW,
                result_state="PASS",
                assumptions=(),
                unresolved=(),
                permitted_wording="legacy A2 pass",
            )
        )
        await session.commit()

        assert not await service.is_b6_authoritative_assessment(
            assessment.id
        )
