from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from app.models.lab import LabMaterial, LabStockSolution
from app.services.lab_regulatory import (
    RegulatoryAuthorityConflictError,
    RegulatoryAuthorityError,
    RegulatoryCompositionEntryInput,
    RegulatoryCompositionProfileInput,
    RegulatoryEvaluationInput,
    RegulatoryRuleInput,
    RegulatorySourceInput,
    SupplierDocumentBindingInput,
)
from app.services.lab_science import RegulatoryAssessmentInput
from app.services.lab_service import FormulaComponentInput, LabService
from app.services.lab_sources import SourceDocumentInput
from tests.a2_planning_fixtures import _approved_plan

NOW = datetime(2026, 7, 31, 0, 0, tzinfo=timezone.utc)


def _source_document_input(
    *,
    source_type: str,
    artifact_sha256: str,
    title: str,
) -> SourceDocumentInput:
    return SourceDocumentInput(
        schema_version="lab-source-document-v1",
        source_type=source_type,
        title=title,
        artifact_sha256=artifact_sha256,
        language="en",
        review_state="UNREVIEWED",
        independence_group=f"b6:{artifact_sha256[:8]}",
        authors=(),
        issuing_organization="test authority",
        container_title=None,
        publisher_or_authority="test authority",
        identifiers={"test": title},
        publication_date=date(2026, 7, 31),
        revision_date=None,
        effective_date=date(2026, 7, 31),
        retrieval_date=date(2026, 7, 31),
        edition_or_amendment="test-version",
        default_locator={"section": "official text"},
        license_or_reuse_restriction="test fixture",
        original_unit=None,
        original_terminology="official regulatory source",
        reviewer_pseudonym=None,
        preserved_artifact_path=f"evidence/b6/{artifact_sha256[:8]}.json",
    )


async def _accept_source(
    service: LabService,
    source_id: str,
    *,
    scope: str,
) -> None:
    for state in (
        "PARSED",
        "IDENTITY_RESOLVED",
        "UNIT_NORMALIZED",
        "CONDITION_NORMALIZED",
        "CONFLICT_CHECKED",
        "HUMAN_REVIEWED",
    ):
        await service.transition_evidence_workflow(
            subject_type="SOURCE_VERSION",
            subject_id=source_id,
            to_state=state,
            reviewer_pseudonym=(
                "regulatory-reviewer" if state == "HUMAN_REVIEWED" else None
            ),
            scopes=(),
            reason=f"advance to {state}",
        )
    await service.transition_evidence_workflow(
        subject_type="SOURCE_VERSION",
        subject_id=source_id,
        to_state="ACCEPTED_FOR_SCOPED_USE",
        reviewer_pseudonym="regulatory-reviewer",
        scopes=(scope,),
        reason=f"accepted for {scope}",
    )


def _regulatory_source_input(
    source_document_version_id: str,
    **overrides,
) -> RegulatorySourceInput:
    values = {
        "schema_version": "lab-regulatory-source-v1",
        "authority_family": "IFRA_STANDARD",
        "identifier": "IFRA Standards",
        "published_version": "51st Amendment",
        "jurisdiction": "GLOBAL",
        "status": "CURRENT_ENFORCED_OR_FORMALLY_NOTIFIED",
        "notified_on": date(2023, 6, 30),
        "effective_from": date(2023, 6, 30),
        "effective_through": None,
        "checked_at": NOW,
        "official_source_document_version_id": source_document_version_id,
        "source_locator": {"section": "notification"},
        "notes": {"scope": "formally notified amendment"},
        "authority_id": None,
        "parent_version_id": None,
        "supersedes_source_version_id": None,
    }
    values.update(overrides)
    return RegulatorySourceInput(**values)


def _rule_input(
    source_version_id: str,
    **overrides,
) -> RegulatoryRuleInput:
    values = {
        "schema_version": "lab-regulatory-rule-v1",
        "regulatory_source_version_id": source_version_id,
        "rule_family": "IFRA_RESTRICTION",
        "rule_identifier": "IFRA:LINALOOL:51",
        "material_id": None,
        "substance_name": "Linalool",
        "cas_number": "78-70-6",
        "jurisdiction": "GLOBAL",
        "product_category": "IFRA_CATEGORY_4",
        "use_classification": "LEAVE_ON",
        "concentration_basis": "FINISHED_PRODUCT_MASS_FRACTION",
        "rule_kind": "MAXIMUM_FINISHED_FRACTION",
        "threshold_fraction": None,
        "maximum_fraction": 0.01,
        "declaration_wording": None,
        "effective_from": date(2023, 6, 30),
        "effective_through": None,
        "placement_transition_end": None,
        "availability_transition_end": None,
        "transition_conditions": {},
        "assumptions": (),
        "rule_id": None,
        "parent_version_id": None,
    }
    values.update(overrides)
    return RegulatoryRuleInput(**values)


async def _official_source(
    service: LabService,
    *,
    digest: str = "a" * 64,
    title: str = "IFRA 51 official notification",
):
    source = await service.register_source_document(
        _source_document_input(
            source_type="REGULATION_OR_OFFICIAL_GUIDANCE",
            artifact_sha256=digest,
            title=title,
        )
    )
    await _accept_source(service, source.id, scope="regulatory_authority")
    return source


@pytest.mark.asyncio
async def test_official_source_requires_accepted_b1_scope_and_copies_digest(
    db_session,
):
    service = LabService(db_session)
    source = await service.register_source_document(
        _source_document_input(
            source_type="REGULATION_OR_OFFICIAL_GUIDANCE",
            artifact_sha256="a" * 64,
            title="IFRA 51 official notification",
        )
    )
    source_id = source.id
    source_artifact_sha256 = source.artifact_sha256
    command = _regulatory_source_input(source_id)

    with pytest.raises(RegulatoryAuthorityConflictError) as unaccepted:
        await service.register_regulatory_source_version(command)
    assert unaccepted.value.code == "REGULATORY_SOURCE_SCOPE_NOT_ACCEPTED"

    await _accept_source(service, source_id, scope="regulatory_authority")
    record = await service.register_regulatory_source_version(command)

    assert record.official_source_sha256 == source_artifact_sha256
    assert record.status == "CURRENT_ENFORCED_OR_FORMALLY_NOTIFIED"
    assert len(record.content_sha256) == 64


@pytest.mark.asyncio
async def test_official_source_rejects_wrong_b1_type_and_future_date_shape(
    db_session,
):
    service = LabService(db_session)
    supplier = await service.register_source_document(
        _source_document_input(
            source_type="SUPPLIER_SDS",
            artifact_sha256="b" * 64,
            title="supplier SDS",
        )
    )
    await _accept_source(service, supplier.id, scope="regulatory_authority")

    with pytest.raises(RegulatoryAuthorityConflictError) as wrong_type:
        await service.register_regulatory_source_version(
            _regulatory_source_input(supplier.id)
        )
    assert wrong_type.value.code == "REGULATORY_SOURCE_TYPE_INVALID"

    official = await _official_source(service, digest="c" * 64)
    with pytest.raises(RegulatoryAuthorityConflictError) as bad_future:
        await service.register_regulatory_source_version(
            _regulatory_source_input(
                official.id,
                status="FUTURE_EFFECTIVE",
                effective_from=NOW.date(),
            )
        )
    assert bad_future.value.code == "FUTURE_SOURCE_DATE_INVALID"


@pytest.mark.asyncio
async def test_consultation_is_recorded_but_cannot_supersede_or_enforce(
    db_session,
):
    service = LabService(db_session)
    current_document = await _official_source(service, digest="d" * 64)
    current = await service.register_regulatory_source_version(
        _regulatory_source_input(current_document.id)
    )
    current_id = current.id
    current_authority_id = current.authority_id
    consultation_document = await _official_source(
        service,
        digest="e" * 64,
        title="IFRA 52 consultation closed",
    )
    consultation_document_id = consultation_document.id

    with pytest.raises(RegulatoryAuthorityConflictError) as supersession:
        await service.register_regulatory_source_version(
            _regulatory_source_input(
                consultation_document_id,
                authority_id=current_authority_id,
                parent_version_id=current_id,
                published_version="52nd Amendment consultation",
                status="CONSULTATION",
                notified_on=None,
                effective_from=None,
                supersedes_source_version_id=current_id,
            )
        )
    assert supersession.value.code == "NONFINAL_SOURCE_CANNOT_SUPERSEDE"

    consultation = await service.register_regulatory_source_version(
        _regulatory_source_input(
            consultation_document_id,
            authority_id=current_authority_id,
            parent_version_id=current_id,
            published_version="52nd Amendment consultation",
            status="CONSULTATION",
            notified_on=None,
            effective_from=None,
        )
    )
    rule = await service.register_regulatory_rule_version(
        _rule_input(
            consultation.id,
            regulatory_source_version_id=consultation.id,
        )
    )

    assert not await service.is_regulatory_rule_enforceable(
        rule.id,
        evaluated_at=NOW,
        market_action="INTERNAL_SCREENING",
        market_action_on=NOW.date(),
    )


@pytest.mark.asyncio
async def test_current_supersession_makes_old_source_unselectable(db_session):
    service = LabService(db_session)
    first_document = await _official_source(service, digest="f" * 64)
    first = await service.register_regulatory_source_version(
        _regulatory_source_input(first_document.id)
    )
    second_document = await _official_source(
        service,
        digest="1" * 64,
        title="formally notified successor",
    )
    second = await service.register_regulatory_source_version(
        _regulatory_source_input(
            second_document.id,
            authority_id=first.authority_id,
            parent_version_id=first.id,
            published_version="successor",
            supersedes_source_version_id=first.id,
        )
    )

    assert second.revision_number == 2
    assert not await service.is_regulatory_source_selectable(
        first.id,
        evaluated_at=NOW,
    )
    assert await service.is_regulatory_source_selectable(
        second.id,
        evaluated_at=NOW,
    )
    with pytest.raises(RegulatoryAuthorityConflictError) as old_rule:
        await service.register_regulatory_rule_version(_rule_input(first.id))
    assert old_rule.value.code == "RULE_SOURCE_SUPERSEDED"


@pytest.mark.asyncio
async def test_eu_allergen_thresholds_and_transition_boundaries_are_date_aware(
    db_session,
):
    service = LabService(db_session)
    document = await _official_source(
        service,
        digest="2" * 64,
        title="Commission Regulation EU 2023/1545",
    )
    source = await service.register_regulatory_source_version(
        _regulatory_source_input(
            document.id,
            authority_family="JURISDICTIONAL_LEGISLATION",
            identifier="Commission Regulation (EU) 2023/1545",
            published_version="2023/1545",
            jurisdiction="EU",
            notified_on=date(2023, 7, 26),
            effective_from=date(2023, 8, 16),
        )
    )
    leave_on = await service.register_regulatory_rule_version(
        _rule_input(
            source.id,
            rule_family="ALLERGEN_LABELING",
            rule_identifier="EU:2023/1545:LINALOOL:LEAVE_ON",
            jurisdiction="EU",
            product_category="COSMETIC",
            use_classification="LEAVE_ON",
            rule_kind="DECLARATION_THRESHOLD",
            threshold_fraction=0.00001,
            maximum_fraction=None,
            declaration_wording="Linalool",
            effective_from=date(2023, 8, 16),
            placement_transition_end=date(2026, 7, 31),
            availability_transition_end=date(2028, 7, 31),
        )
    )
    rinse_off = await service.register_regulatory_rule_version(
        replace(
            _rule_input(
                source.id,
                rule_family="ALLERGEN_LABELING",
                rule_identifier="EU:2023/1545:LINALOOL:RINSE_OFF",
                jurisdiction="EU",
                product_category="COSMETIC",
                use_classification="RINSE_OFF",
                rule_kind="DECLARATION_THRESHOLD",
                threshold_fraction=0.0001,
                maximum_fraction=None,
                declaration_wording="Linalool",
                effective_from=date(2023, 8, 16),
                placement_transition_end=date(2026, 7, 31),
                availability_transition_end=date(2028, 7, 31),
            ),
            rule_id="eu-linalool-rinse-off",
        )
    )

    assert leave_on.threshold_fraction == pytest.approx(0.00001)
    assert rinse_off.threshold_fraction == pytest.approx(0.0001)
    assert not await service.is_regulatory_rule_enforceable(
        leave_on.id,
        evaluated_at=NOW,
        market_action="PLACE_ON_MARKET",
        market_action_on=date(2026, 7, 31),
    )
    assert await service.is_regulatory_rule_enforceable(
        leave_on.id,
        evaluated_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        market_action="PLACE_ON_MARKET",
        market_action_on=date(2026, 8, 1),
    )
    assert not await service.is_regulatory_rule_enforceable(
        leave_on.id,
        evaluated_at=datetime(2028, 7, 31, tzinfo=timezone.utc),
        market_action="MAKE_AVAILABLE",
        market_action_on=date(2028, 7, 31),
    )
    assert await service.is_regulatory_rule_enforceable(
        leave_on.id,
        evaluated_at=datetime(2028, 8, 1, tzinfo=timezone.utc),
        market_action="MAKE_AVAILABLE",
        market_action_on=date(2028, 8, 1),
    )


def _supplier_binding_input(
    stock_solution_id: str,
    source_document_version_id: str,
    **overrides,
) -> SupplierDocumentBindingInput:
    values = {
        "stock_solution_id": stock_solution_id,
        "scope": "SUPPLIER_LOT",
        "supplier": "Supplier A",
        "supplier_product": "Bergamot FCF",
        "supplier_product_code": "BG-FCF",
        "grade": "natural FCF",
        "document_type": "SUPPLIER_COA",
        "document_version": "test-version",
        "lot_number": "LOT-42",
        "effective_on": date(2026, 7, 1),
        "expires_on": date(2027, 7, 1),
        "source_document_version_id": source_document_version_id,
        "source_locator": {"section": "composition"},
    }
    values.update(overrides)
    return SupplierDocumentBindingInput(**values)


async def _natural_stock(service: LabService):
    material = LabMaterial(
        canonical_name="Bergamot oil FCF",
        cas_number="8007-75-8",
        original_payload_json={},
    )
    service.session.add(material)
    await service.session.flush()
    stock = LabStockSolution(
        material_id=material.id,
        supplier="Supplier A",
        lot_number="LOT-42",
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        density_g_ml=0.88,
        solvent_name=None,
        initial_mass_g=100.0,
        remaining_mass_g=100.0,
        source_json={
            "supplier_product": "Bergamot FCF",
            "supplier_product_code": "BG-FCF",
            "grade": "natural FCF",
            "origin": "NATURAL",
        },
    )
    service.session.add(stock)
    await service.session.flush()
    return stock


@pytest.mark.asyncio
async def test_supplier_document_binding_is_exact_to_product_grade_and_lot(
    db_session,
):
    service = LabService(db_session)
    stock = await _natural_stock(service)
    source = await service.register_source_document(
        _source_document_input(
            source_type="SUPPLIER_COA",
            artifact_sha256="3" * 64,
            title="Supplier A Bergamot FCF lot COA",
        )
    )
    await _accept_source(
        service,
        source.id,
        scope="supplier_regulatory_document",
    )
    binding = await service.bind_supplier_regulatory_document(
        _supplier_binding_input(stock.id, source.id)
    )

    assert binding.stock_solution_id == stock.id
    assert binding.source_artifact_sha256 == source.artifact_sha256
    assert len(binding.supplier_identity_sha256) == 64

    for field, value, code in (
        ("supplier", "Supplier B", "SUPPLIER_IDENTITY_MISMATCH"),
        ("supplier_product", "Bergamot ordinary", "SUPPLIER_IDENTITY_MISMATCH"),
        ("supplier_product_code", "OTHER", "SUPPLIER_IDENTITY_MISMATCH"),
        ("grade", "ordinary", "SUPPLIER_IDENTITY_MISMATCH"),
        ("lot_number", "LOT-99", "SUPPLIER_LOT_MISMATCH"),
    ):
        with pytest.raises(RegulatoryAuthorityConflictError) as mismatch:
            await service.bind_supplier_regulatory_document(
                _supplier_binding_input(
                    stock.id,
                    source.id,
                    **{field: value},
                )
            )
        assert mismatch.value.code == code


@pytest.mark.asyncio
async def test_supplier_document_rejects_type_scope_and_date_shape(
    db_session,
):
    service = LabService(db_session)
    stock = await _natural_stock(service)
    source = await service.register_source_document(
        _source_document_input(
            source_type="SUPPLIER_SDS",
            artifact_sha256="4" * 64,
            title="Supplier A Bergamot FCF SDS",
        )
    )
    await _accept_source(
        service,
        source.id,
        scope="supplier_regulatory_document",
    )

    with pytest.raises(RegulatoryAuthorityConflictError) as wrong_type:
        await service.bind_supplier_regulatory_document(
            _supplier_binding_input(stock.id, source.id)
        )
    assert wrong_type.value.code == "SUPPLIER_DOCUMENT_TYPE_MISMATCH"

    with pytest.raises(RegulatoryAuthorityError, match="lot_number"):
        _supplier_binding_input(
            stock.id,
            source.id,
            scope="SUPPLIER_PRODUCT",
            document_type="SUPPLIER_SDS",
        )
    with pytest.raises(RegulatoryAuthorityError, match="expires_on"):
        _supplier_binding_input(
            stock.id,
            source.id,
            document_type="SUPPLIER_SDS",
            effective_on=date(2026, 1, 1),
            expires_on=date(2025, 1, 1),
        )


def _composition_entry_input(
    **overrides,
) -> RegulatoryCompositionEntryInput:
    values = {
        "position": 1,
        "projection_family": "REGULATORY",
        "material_id": None,
        "constituent_name": "Limonene",
        "cas_number": "138-86-3",
        "fraction": 0.35,
        "fraction_basis": "MASS_FRACTION",
        "standard_uncertainty": 0.02,
        "source_locator": {"section": "constituent declaration"},
    }
    values.update(overrides)
    return RegulatoryCompositionEntryInput(**values)


def _composition_profile_input(
    stock_solution_id: str,
    supplier_document_binding_id: str | None,
    **overrides,
) -> RegulatoryCompositionProfileInput:
    values = {
        "stock_solution_id": stock_solution_id,
        "schema_version": "lab-regulatory-composition-v1",
        "origin": "NATURAL",
        "composition_basis": "LOT_SPECIFIC",
        "completeness": "COMPLETE",
        "supplier_document_binding_id": supplier_document_binding_id,
        "entries": (_composition_entry_input(),),
        "assumptions": (),
        "limitations": ("supplier-declared composition",),
        "reviewer_pseudonym": "regulatory-reviewer",
        "reviewed_at": NOW,
        "profile_id": None,
        "parent_version_id": None,
    }
    values.update(overrides)
    return RegulatoryCompositionProfileInput(**values)


async def _composition_document_binding(
    service: LabService,
    stock_id: str,
    *,
    scope: str = "SUPPLIER_LOT",
):
    source = await service.register_source_document(
        _source_document_input(
            source_type="SUPPLIER_COA",
            artifact_sha256="5" * 64,
            title=f"Supplier A composition {scope}",
        )
    )
    source_id = source.id
    await _accept_source(
        service,
        source_id,
        scope="supplier_regulatory_document",
    )
    return await service.bind_supplier_regulatory_document(
        _supplier_binding_input(
            stock_id,
            source_id,
            scope=scope,
            lot_number="LOT-42" if scope == "SUPPLIER_LOT" else None,
        )
    )


@pytest.mark.asyncio
async def test_lot_specific_natural_profile_is_atomic_and_complete(db_session):
    service = LabService(db_session)
    stock = await _natural_stock(service)
    stock_id = stock.id
    binding = await _composition_document_binding(service, stock_id)

    profile = await service.record_regulatory_composition_profile(
        _composition_profile_input(stock_id, binding.id)
    )
    entries = await service.repository.regulatory_composition_entries(profile.id)

    assert profile.origin == "NATURAL"
    assert profile.composition_basis == "LOT_SPECIFIC"
    assert profile.completeness == "COMPLETE"
    assert [(entry.position, entry.projection_family) for entry in entries] == [
        (1, "REGULATORY")
    ]
    assert await service.is_regulatory_composition_complete(profile.id)


@pytest.mark.asyncio
async def test_lot_specific_profile_rejects_product_scope_and_lot_mismatch(
    db_session,
):
    service = LabService(db_session)
    stock = await _natural_stock(service)
    stock_id = stock.id
    product_binding = await _composition_document_binding(
        service,
        stock_id,
        scope="SUPPLIER_PRODUCT",
    )

    with pytest.raises(RegulatoryAuthorityConflictError) as wrong_scope:
        await service.record_regulatory_composition_profile(
            _composition_profile_input(stock_id, product_binding.id)
        )
    assert wrong_scope.value.code == "LOT_PROFILE_DOCUMENT_SCOPE_INVALID"


@pytest.mark.asyncio
async def test_documented_proxy_requires_product_scope_and_assumptions(db_session):
    service = LabService(db_session)
    stock = await _natural_stock(service)
    stock_id = stock.id
    product_binding = await _composition_document_binding(
        service,
        stock_id,
        scope="SUPPLIER_PRODUCT",
    )

    with pytest.raises(RegulatoryAuthorityConflictError) as assumptions:
        await service.record_regulatory_composition_profile(
            _composition_profile_input(
                stock_id,
                product_binding.id,
                composition_basis="DOCUMENTED_PROXY",
            )
        )
    assert assumptions.value.code == "DOCUMENTED_PROXY_ASSUMPTIONS_REQUIRED"

    profile = await service.record_regulatory_composition_profile(
        _composition_profile_input(
            stock_id,
            product_binding.id,
            composition_basis="DOCUMENTED_PROXY",
            assumptions=("product specification used as lot proxy",),
        )
    )
    assert profile.composition_basis == "DOCUMENTED_PROXY"
    assert await service.is_regulatory_composition_complete(profile.id)


@pytest.mark.asyncio
async def test_unknown_and_partial_profiles_are_explicitly_nonpassing(db_session):
    service = LabService(db_session)
    stock = await _natural_stock(service)
    stock_id = stock.id
    unknown = await service.record_regulatory_composition_profile(
        _composition_profile_input(
            stock_id,
            None,
            composition_basis="UNKNOWN",
            completeness="UNKNOWN",
            entries=(),
            limitations=("supplier composition unavailable",),
        )
    )
    assert not await service.is_regulatory_composition_complete(unknown.id)

    binding = await _composition_document_binding(service, stock_id)
    partial = await service.record_regulatory_composition_profile(
        _composition_profile_input(
            stock_id,
            binding.id,
            completeness="PARTIAL",
        )
    )
    assert not await service.is_regulatory_composition_complete(partial.id)


def test_composition_input_rejects_projection_conflation_and_unknown_entries():
    with pytest.raises(RegulatoryAuthorityError, match="projection_family"):
        _composition_entry_input(projection_family="OLFACTORY")
    with pytest.raises(RegulatoryAuthorityError, match="projection_family"):
        _composition_entry_input(projection_family="IDENTITY_AUTHENTICITY")
    with pytest.raises(RegulatoryAuthorityError, match="entries"):
        _composition_profile_input(
            "stock",
            None,
            composition_basis="UNKNOWN",
            completeness="UNKNOWN",
            entries=(_composition_entry_input(),),
        )


async def _evaluation_stock(
    service: LabService,
    *,
    name: str,
    cas_number: str | None,
    active_fraction: float,
    origin: str,
    lot_number: str,
):
    material = LabMaterial(
        canonical_name=name,
        cas_number=cas_number,
        original_payload_json={},
    )
    service.session.add(material)
    await service.session.flush()
    code = name.upper().replace(" ", "-")
    stock = LabStockSolution(
        material_id=material.id,
        supplier="Evaluation Supplier",
        lot_number=lot_number,
        active_fraction=active_fraction,
        fraction_basis="mass_fraction",
        density_g_ml=0.9,
        solvent_name=None,
        initial_mass_g=100.0,
        remaining_mass_g=100.0,
        source_json={
            "supplier_product": name,
            "supplier_product_code": code,
            "grade": "evaluation grade",
            "origin": origin,
        },
    )
    service.session.add(stock)
    await service.session.flush()
    return material, stock


async def _required_supplier_bindings(
    service: LabService,
    stock: LabStockSolution,
    *,
    digest_seed: int,
):
    bindings = []
    identity = dict(stock.source_json)
    for offset, document_type in enumerate(
        (
            "SUPPLIER_SDS",
            "SUPPLIER_IFRA_CERTIFICATE",
            "SUPPLIER_ALLERGEN_DECLARATION",
        )
    ):
        digit = format(digest_seed + offset, "x")[-1]
        source = await service.register_source_document(
            _source_document_input(
                source_type=document_type,
                artifact_sha256=digit * 64,
                title=f"{identity['supplier_product']} {document_type}",
            )
        )
        source_id = source.id
        await _accept_source(
            service,
            source_id,
            scope="supplier_regulatory_document",
        )
        binding = await service.bind_supplier_regulatory_document(
            SupplierDocumentBindingInput(
                stock_solution_id=stock.id,
                scope="SUPPLIER_LOT",
                supplier=str(stock.supplier),
                supplier_product=str(identity["supplier_product"]),
                supplier_product_code=str(identity["supplier_product_code"]),
                grade=str(identity["grade"]),
                document_type=document_type,
                document_version="test-version",
                lot_number=str(stock.lot_number),
                effective_on=date(2026, 1, 1),
                expires_on=date(2027, 12, 31),
                source_document_version_id=source_id,
                source_locator={"section": document_type},
            )
        )
        bindings.append(binding)
    return bindings


async def _formula_version_for_stocks(
    service: LabService,
    stocks: tuple[LabStockSolution, ...],
    *,
    finished_concentration: float,
):
    formula = await service.create_formula(
        f"B6 evaluation formula {len(stocks)}"
    )
    return await service.add_formula_version(
        formula.id,
        brief={"scope": "B6 deterministic evaluation"},
        constraints={},
        concentration_fraction=finished_concentration,
        concentration_basis="mass_fraction",
        components=tuple(
            FormulaComponentInput(
                stock_solution_id=stock.id,
                requested_mass_g=1.0,
            )
            for stock in stocks
        ),
    )


async def _regulatory_rule_graph(
    service: LabService,
    *,
    maximum_fraction: float,
    material_id: str | None = None,
    cas_number: str | None = "78-70-6",
):
    current_document = await _official_source(
        service,
        digest="9" * 64,
        title="IFRA current formally notified source",
    )
    current = await service.register_regulatory_source_version(
        _regulatory_source_input(current_document.id)
    )
    current_id = current.id
    authority_id = current.authority_id
    current_rule = await service.register_regulatory_rule_version(
        _rule_input(
            current_id,
            material_id=material_id,
            cas_number=cas_number,
            maximum_fraction=maximum_fraction,
        )
    )
    watch_document = await _official_source(
        service,
        digest="a" * 64,
        title="IFRA 52 consultation closed",
    )
    watch = await service.register_regulatory_source_version(
        _regulatory_source_input(
            watch_document.id,
            authority_id=authority_id,
            parent_version_id=current_id,
            published_version="52nd Amendment consultation",
            status="CONSULTATION",
            notified_on=None,
            effective_from=None,
        )
    )
    watch_rule = await service.register_regulatory_rule_version(
        _rule_input(
            watch.id,
            rule_identifier="IFRA:LINALOOL:52:CONSULTATION",
            material_id=material_id,
            cas_number=cas_number,
            maximum_fraction=maximum_fraction / 10,
        )
    )
    return current, current_rule, watch, watch_rule


def _evaluation_input(
    subject_type: str,
    subject_id: str,
    *,
    primary_source_version_id: str,
    current_source_ids: tuple[str, ...],
    watch_source_ids: tuple[str, ...],
    rule_ids: tuple[str, ...],
    supplier_binding_ids: tuple[str, ...],
    composition_profile_ids: tuple[str, ...] = (),
    finished_product_concentration: float = 0.1,
    legacy_assessment_version_id: str | None = None,
) -> RegulatoryEvaluationInput:
    return RegulatoryEvaluationInput(
        schema_version="lab-regulatory-snapshot-v1",
        subject_type=subject_type,
        subject_id=subject_id,
        legacy_assessment_version_id=legacy_assessment_version_id,
        primary_source_version_id=primary_source_version_id,
        jurisdiction="GLOBAL",
        product_category="IFRA_CATEGORY_4",
        use_classification="LEAVE_ON",
        finished_product_concentration=finished_product_concentration,
        constituent_basis="FINISHED_PRODUCT_MASS_FRACTION",
        natural_material_assumptions=(),
        effective_on=date(2023, 6, 30),
        evaluated_at=NOW,
        evaluator_software_version="perfume-chem-b6-test",
        market_action="INTERNAL_SCREENING",
        market_action_on=NOW.date(),
        current_state_source_version_ids=current_source_ids,
        watch_source_version_ids=watch_source_ids,
        rule_version_ids=rule_ids,
        supplier_binding_ids=supplier_binding_ids,
        composition_profile_ids=composition_profile_ids,
        declared_allergen_labels=(),
        reviewer_pseudonym="regulatory-reviewer",
        reviewed_at=NOW,
        snapshot_id=None,
        parent_version_id=None,
    )


@pytest.mark.asyncio
async def test_formula_evaluation_passes_scope_and_persists_watch_finding(
    db_session,
):
    service = LabService(db_session)
    material, stock = await _evaluation_stock(
        service,
        name="Linalool evaluation",
        cas_number="78-70-6",
        active_fraction=0.2,
        origin="SYNTHETIC",
        lot_number="EVAL-1",
    )
    formula = await _formula_version_for_stocks(
        service,
        (stock,),
        finished_concentration=0.1,
    )
    bindings = await _required_supplier_bindings(
        service,
        stock,
        digest_seed=10,
    )
    current, rule, watch, watch_rule = await _regulatory_rule_graph(
        service,
        maximum_fraction=0.03,
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
            supplier_binding_ids=tuple(binding.id for binding in bindings),
        )
    )
    findings = await service.repository.regulatory_authority_findings(
        snapshot.id
    )

    assert snapshot.result_state == "PASS_FOR_DECLARED_SCOPE"
    assert snapshot.permitted_wording
    assert "certificate" not in snapshot.permitted_wording.casefold()
    assert "legal" not in snapshot.permitted_wording.casefold()
    assert [(item.enforced, item.result_state) for item in findings] == [
        (True, "PASS_FOR_DECLARED_SCOPE"),
        (False, "NOT_EVALUATED"),
    ]


@pytest.mark.asyncio
async def test_known_restriction_failure_withholds_wording(db_session):
    service = LabService(db_session)
    material, stock = await _evaluation_stock(
        service,
        name="Linalool failure",
        cas_number="78-70-6",
        active_fraction=0.2,
        origin="SYNTHETIC",
        lot_number="EVAL-2",
    )
    formula = await _formula_version_for_stocks(
        service,
        (stock,),
        finished_concentration=0.1,
    )
    bindings = await _required_supplier_bindings(
        service,
        stock,
        digest_seed=11,
    )
    current, rule, watch, watch_rule = await _regulatory_rule_graph(
        service,
        maximum_fraction=0.01,
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
            supplier_binding_ids=tuple(binding.id for binding in bindings),
        )
    )

    assert snapshot.result_state == "FAIL"
    assert snapshot.permitted_wording is None


@pytest.mark.asyncio
async def test_unknown_natural_composition_never_passes(db_session):
    service = LabService(db_session)
    material, stock = await _evaluation_stock(
        service,
        name="Unknown natural",
        cas_number="8000-00-0",
        active_fraction=1.0,
        origin="NATURAL",
        lot_number="EVAL-3",
    )
    formula = await _formula_version_for_stocks(
        service,
        (stock,),
        finished_concentration=0.1,
    )
    bindings = await _required_supplier_bindings(
        service,
        stock,
        digest_seed=12,
    )
    unknown_profile = await service.record_regulatory_composition_profile(
        _composition_profile_input(
            stock.id,
            None,
            composition_basis="UNKNOWN",
            completeness="UNKNOWN",
            entries=(),
            limitations=("composition not supplied",),
        )
    )
    current, rule, watch, watch_rule = await _regulatory_rule_graph(
        service,
        maximum_fraction=0.03,
        material_id=None,
    )

    snapshot = await service.evaluate_regulatory_snapshot(
        _evaluation_input(
            "FORMULA_VERSION",
            formula.id,
            primary_source_version_id=current.id,
            current_source_ids=(current.id,),
            watch_source_ids=(watch.id,),
            rule_ids=(rule.id, watch_rule.id),
            supplier_binding_ids=tuple(binding.id for binding in bindings),
            composition_profile_ids=(unknown_profile.id,),
        )
    )

    assert snapshot.result_state == "UNKNOWN"
    assert snapshot.permitted_wording is None
    assert "NATURAL_COMPOSITION_UNKNOWN" in snapshot.unresolved_items_json


@pytest.mark.asyncio
async def test_known_failure_outranks_unknown_natural_composition(db_session):
    service = LabService(db_session)
    material, synthetic = await _evaluation_stock(
        service,
        name="Linalool lower bound",
        cas_number="78-70-6",
        active_fraction=1.0,
        origin="SYNTHETIC",
        lot_number="EVAL-4A",
    )
    _, natural = await _evaluation_stock(
        service,
        name="Unknown natural companion",
        cas_number="8000-00-1",
        active_fraction=1.0,
        origin="NATURAL",
        lot_number="EVAL-4B",
    )
    formula = await _formula_version_for_stocks(
        service,
        (synthetic, natural),
        finished_concentration=0.2,
    )
    synthetic_bindings = await _required_supplier_bindings(
        service,
        synthetic,
        digest_seed=6,
    )
    natural_bindings = await _required_supplier_bindings(
        service,
        natural,
        digest_seed=13,
    )
    unknown_profile = await service.record_regulatory_composition_profile(
        _composition_profile_input(
            natural.id,
            None,
            composition_basis="UNKNOWN",
            completeness="UNKNOWN",
            entries=(),
            limitations=("composition not supplied",),
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
                binding.id
                for binding in synthetic_bindings + natural_bindings
            ),
            composition_profile_ids=(unknown_profile.id,),
            finished_product_concentration=0.2,
        )
    )

    assert snapshot.result_state == "FAIL"
    assert "NATURAL_COMPOSITION_UNKNOWN" in snapshot.unresolved_items_json


@pytest.mark.asyncio
async def test_build_plan_evaluation_uses_planned_active_quantity(db_session):
    service, plan, _line, stock = await _approved_plan(db_session)
    material = await service.repository.get_material(stock.material_id)
    assert material is not None
    stock.supplier = "Evaluation Supplier"
    stock.lot_number = "EVAL-BUILD"
    stock.source_json = {
        "supplier_product": "Jasmine Absolute",
        "supplier_product_code": "JASMINE-ABSOLUTE",
        "grade": "evaluation grade",
        "origin": "SYNTHETIC",
    }
    await service.session.flush()
    bindings = await _required_supplier_bindings(
        service,
        stock,
        digest_seed=7,
    )
    current, rule, watch, watch_rule = await _regulatory_rule_graph(
        service,
        maximum_fraction=0.2,
        material_id=material.id,
        cas_number=None,
    )

    snapshot = await service.evaluate_regulatory_snapshot(
        _evaluation_input(
            "BUILD_PLAN_VERSION",
            plan.id,
            primary_source_version_id=current.id,
            current_source_ids=(current.id,),
            watch_source_ids=(watch.id,),
            rule_ids=(rule.id, watch_rule.id),
            supplier_binding_ids=tuple(binding.id for binding in bindings),
            finished_product_concentration=1.0,
        )
    )
    finding = (
        await service.repository.regulatory_authority_findings(snapshot.id)
    )[0]

    assert snapshot.result_state == "PASS_FOR_DECLARED_SCOPE"
    assert finding.observed_fraction == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_legacy_a2_pass_alone_is_not_b6_authority(db_session):
    service = LabService(db_session)
    _, stock = await _evaluation_stock(
        service,
        name="Legacy A2 stock",
        cas_number="78-70-6",
        active_fraction=1.0,
        origin="SYNTHETIC",
        lot_number="EVAL-A2",
    )
    formula = await _formula_version_for_stocks(
        service,
        (stock,),
        finished_concentration=0.1,
    )
    evidence = await service.record_evidence(
        claim_key="b6:legacy-a2-pass",
        classification="EXACT",
        source_locator="test://legacy-a2",
        source_version="1",
        method="legacy A2 test",
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

    assert not await service.is_b6_authoritative_assessment(assessment.id)
