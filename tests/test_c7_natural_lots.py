from __future__ import annotations

import ast
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from engine.physics.natural_lots import (
    C7_COMPOSITION_PRECEDENCE,
    PERMITTED_CONSTITUENT_BASES,
    AnalyticalRunReference,
    AuthenticityAssessment,
    AuthenticityDecision,
    AuthenticityDeviation,
    AuthenticityReferenceRange,
    CalibrationState,
    CensoringState,
    CompositionAuthority,
    ConstituentBasis,
    ConstituentObservation,
    IdentityConfidence,
    LotAgingObservation,
    NaturalCompositionCompleteness,
    NaturalCompositionProfile,
    NaturalCompositionRequest,
    NaturalCompositionSelection,
    NaturalLotContractError,
    NaturalMaterialLot,
    NaturalProjection,
    ObservationOrigin,
    ProjectionEntry,
    ProjectionFamily,
    ProjectionStatus,
    ReviewState,
    SelectionStatus,
    SourceDocumentKind,
    SourceDocumentReference,
    UnresolvedDisclosureState,
    UnresolvedFractionDisclosure,
    UnresolvedFractionKind,
    UnresolvedFractionObservation,
    assess_authenticity_profile,
    build_natural_projection,
    select_natural_composition,
    validate_aging_series,
)

PUBLIC_C7_NAMES = {
    "C7_COMPOSITION_PRECEDENCE",
    "PERMITTED_CONSTITUENT_BASES",
    "AnalyticalRunReference",
    "AuthenticityAssessment",
    "AuthenticityDecision",
    "AuthenticityDeviation",
    "AuthenticityReferenceRange",
    "CalibrationState",
    "CensoringState",
    "CompositionAuthority",
    "ConstituentBasis",
    "ConstituentObservation",
    "IdentityConfidence",
    "LotAgingObservation",
    "NaturalCompositionCompleteness",
    "NaturalCompositionProfile",
    "NaturalCompositionRequest",
    "NaturalCompositionSelection",
    "NaturalLotContractError",
    "NaturalMaterialLot",
    "NaturalProjection",
    "ObservationOrigin",
    "ProjectionEntry",
    "ProjectionFamily",
    "ProjectionStatus",
    "ReviewState",
    "SelectionStatus",
    "SourceDocumentKind",
    "SourceDocumentReference",
    "UnresolvedDisclosureState",
    "UnresolvedFractionDisclosure",
    "UnresolvedFractionKind",
    "UnresolvedFractionObservation",
    "assess_authenticity_profile",
    "build_natural_projection",
    "select_natural_composition",
    "validate_aging_series",
}


def digest(character: str) -> str:
    return character * 64


def source_document(
    *,
    document_id: str = "doc-coa-1",
    subject_lot_id: str | None = "lot-1",
    kind: SourceDocumentKind = SourceDocumentKind.COA,
) -> SourceDocumentReference:
    return SourceDocumentReference(
        document_id=document_id,
        document_kind=kind,
        source_id="supplier:example",
        subject_lot_id=subject_lot_id,
        document_sha256=digest("a"),
        version="2026-01",
    )


def analytical_run(
    *,
    analytical_run_id: str = "run-1",
    subject_lot_id: str = "lot-1",
) -> AnalyticalRunReference:
    return AnalyticalRunReference(
        analytical_run_id=analytical_run_id,
        run_authority_id="run-authority-1",
        subject_lot_id=subject_lot_id,
        method_id="gc-fid-method-1",
        run_sha256=digest("b"),
    )


def natural_lot(**overrides: object) -> NaturalMaterialLot:
    values: dict[str, object] = {
        "lot_id": "lot-1",
        "material_id": "material-lavender",
        "material_name": "Lavender EO",
        "botanical_species": "Lavandula angustifolia",
        "variety_or_chemotype": "linalool/linalyl acetate",
        "plant_part": "flowering tops",
        "geographic_origin": "Provence, France",
        "harvest_or_production_date": date(2025, 7, 15),
        "extraction_method": "steam distillation",
        "processing": ("filtered",),
        "supplier_id": "supplier-1",
        "supplier_product": "Lavender EO Maillette",
        "supplier_lot": "batch-77",
        "received_on": date(2025, 9, 1),
        "opened_on": date(2025, 9, 10),
        "storage_conditions": ("amber glass", "15-20 C", "dark"),
        "oxidation_stability_observations": ("no visible resinification",),
        "source_documents": (source_document(),),
        "analytical_runs": (analytical_run(),),
        "authenticity_status": AuthenticityDecision.INSUFFICIENT_EVIDENCE,
        "unknown_identity_fields": (),
    }
    values.update(overrides)
    return NaturalMaterialLot(**values)  # type: ignore[arg-type]


def constituent(
    *,
    observation_id: str = "obs-linalool",
    source_lot_id: str | None = "lot-1",
    chemical_id: str = "cas:78-70-6",
    chemical_name: str = "linalool",
    identity_confidence: IdentityConfidence = IdentityConfidence.CONFIRMED,
    origin: ObservationOrigin = ObservationOrigin.EXACT_LOT_MEASURED,
    value: float | None = 0.42,
    lower_bound: float | None = None,
    upper_bound: float | None = None,
    basis: ConstituentBasis = ConstituentBasis.CALIBRATED_MASS_FRACTION,
    calibration_state: CalibrationState = CalibrationState.CALIBRATED,
    response_model_id: str | None = "response-model-1",
    standard_uncertainty: float | None = 0.01,
    uncertainty_note: str = "one standard uncertainty",
    lod: float | None = 0.0001,
    loq: float | None = 0.0003,
    censoring: CensoringState = CensoringState.NONE,
    analytical_run_id: str | None = "run-1",
    review_state: ReviewState = ReviewState.REVIEWED,
) -> ConstituentObservation:
    return ConstituentObservation(
        observation_id=observation_id,
        source_lot_id=source_lot_id,
        chemical_id=chemical_id,
        chemical_name=chemical_name,
        identity_confidence=identity_confidence,
        origin=origin,
        value=value,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        basis=basis,
        method_id="gc-fid-method-1",
        calibration_state=calibration_state,
        response_model_id=response_model_id,
        standard_uncertainty=standard_uncertainty,
        uncertainty_note=uncertainty_note,
        lod=lod,
        loq=loq,
        censoring=censoring,
        source_id="source-1",
        source_sha256=digest("c"),
        analytical_run_id=analytical_run_id,
        review_state=review_state,
    )


def area_observation(
    *,
    observation_id: str = "obs-area-linalool",
    source_lot_id: str | None = "lot-1",
    origin: ObservationOrigin = ObservationOrigin.EXACT_LOT_MEASURED,
    value: float = 42.0,
    analytical_run_id: str | None = "run-1",
) -> ConstituentObservation:
    return constituent(
        observation_id=observation_id,
        source_lot_id=source_lot_id,
        origin=origin,
        value=value,
        basis=ConstituentBasis.NORMALIZED_AREA_PERCENT,
        calibration_state=CalibrationState.UNCALIBRATED,
        response_model_id=None,
        standard_uncertainty=0.5,
        uncertainty_note="repeat-injection area uncertainty only",
        analytical_run_id=analytical_run_id,
    )


def unresolved_observation(
    *,
    observation_id: str = "unknown-peak-1",
    source_lot_id: str | None = "lot-1",
    kind: UnresolvedFractionKind = UnresolvedFractionKind.UNKNOWN_PEAK,
    value: float | None = 8.0,
    basis: ConstituentBasis = ConstituentBasis.NORMALIZED_AREA_PERCENT,
    limit_value: float | None = None,
    analytical_run_id: str | None = "run-1",
) -> UnresolvedFractionObservation:
    return UnresolvedFractionObservation(
        observation_id=observation_id,
        source_lot_id=source_lot_id,
        kind=kind,
        value=value,
        basis=basis,
        limit_value=limit_value,
        method_id="gc-fid-method-1",
        source_id="source-1",
        source_sha256=digest("d"),
        analytical_run_id=analytical_run_id,
        notes=("retention window retained",),
        review_state=ReviewState.REVIEWED,
    )


def present_unresolved(
    *observations: UnresolvedFractionObservation,
) -> UnresolvedFractionDisclosure:
    rows = observations or (unresolved_observation(),)
    return UnresolvedFractionDisclosure(
        state=UnresolvedDisclosureState.PRESENT,
        observations=tuple(rows),
        review_method_id="gc-fid-method-1",
        source_ids=("source-1",),
        limitations=("unknown identities retained",),
    )


def reviewed_no_unresolved() -> UnresolvedFractionDisclosure:
    return UnresolvedFractionDisclosure(
        state=UnresolvedDisclosureState.REVIEWED_NONE_OBSERVED,
        observations=(),
        review_method_id="gc-fid-method-1",
        source_ids=("source-1",),
        limitations=("limited to the validated detection domain",),
    )


def profile(
    *,
    profile_id: str = "profile-exact-quant",
    authority: CompositionAuthority = CompositionAuthority.EXACT_LOT_QUANTIFIED,
    completeness: NaturalCompositionCompleteness = NaturalCompositionCompleteness.PARTIAL,
    observations: tuple[ConstituentObservation, ...] | None = None,
    unresolved: UnresolvedFractionDisclosure | None = None,
    lot_id: str | None = "lot-1",
    supplier_product: str | None = "Lavender EO Maillette",
    supplier_lot: str | None = "batch-77",
    botanical_species: str | None = "Lavandula angustifolia",
    variety_or_chemotype: str | None = "linalool/linalyl acetate",
    geographic_origin: str | None = "Provence, France",
    extraction_method: str | None = "steam distillation",
    source_documents: tuple[SourceDocumentReference, ...] | None = None,
) -> NaturalCompositionProfile:
    if observations is None:
        observations = (constituent(),)
    if unresolved is None:
        unresolved = present_unresolved()
    if source_documents is None:
        source_documents = (source_document(subject_lot_id=lot_id),)
    return NaturalCompositionProfile(
        profile_id=profile_id,
        schema_version="c7-natural-composition-v1",
        profile_version=1,
        parent_profile_sha256=None,
        material_id="material-lavender",
        lot_id=lot_id,
        supplier_product=supplier_product,
        supplier_lot=supplier_lot,
        botanical_species=botanical_species,
        variety_or_chemotype=variety_or_chemotype,
        geographic_origin=geographic_origin,
        extraction_method=extraction_method,
        authority=authority,
        completeness=completeness,
        observations=observations,
        unresolved=unresolved,
        source_documents=source_documents,
        assumptions=("values retain their declared basis",),
        limitations=("no basis conversion is authorized",),
    )


def request() -> NaturalCompositionRequest:
    return NaturalCompositionRequest(
        material_id="material-lavender",
        requested_lot_id="lot-1",
        supplier_product="Lavender EO Maillette",
        supplier_lot="batch-77",
        botanical_species="Lavandula angustifolia",
        variety_or_chemotype="linalool/linalyl acetate",
        geographic_origin="Provence, France",
        extraction_method="steam distillation",
    )


def relative_profile() -> NaturalCompositionProfile:
    return profile(
        profile_id="profile-exact-relative",
        authority=CompositionAuthority.EXACT_LOT_RELATIVE_PROFILE,
        observations=(area_observation(),),
    )


def supplier_profile() -> NaturalCompositionProfile:
    return profile(
        profile_id="profile-supplier",
        authority=CompositionAuthority.SUPPLIER_BATCH_SPECIFIC,
        observations=(
            constituent(
                source_lot_id="batch-77",
                origin=ObservationOrigin.SUPPLIER_BATCH_REPORTED,
                analytical_run_id=None,
            ),
        ),
        unresolved=UnresolvedFractionDisclosure(
            state=UnresolvedDisclosureState.NOT_REPORTED,
            observations=(),
            review_method_id=None,
            source_ids=("supplier:example",),
            limitations=("supplier document did not disclose unknown fraction",),
        ),
        lot_id=None,
        source_documents=(source_document(subject_lot_id="batch-77"),),
    )


def specific_literature_profile() -> NaturalCompositionProfile:
    return profile(
        profile_id="profile-literature-specific",
        authority=CompositionAuthority.SPECIFIC_LITERATURE_PROXY,
        observations=(
            constituent(
                source_lot_id=None,
                origin=ObservationOrigin.LITERATURE_REPORTED,
                value=None,
                lower_bound=0.25,
                upper_bound=0.48,
                basis=ConstituentBasis.LITERATURE_RANGE,
                calibration_state=CalibrationState.NOT_APPLICABLE,
                response_model_id=None,
                standard_uncertainty=None,
                uncertainty_note="literature range; study uncertainty not reported",
                lod=None,
                loq=None,
                analytical_run_id=None,
            ),
        ),
        unresolved=UnresolvedFractionDisclosure(
            state=UnresolvedDisclosureState.NOT_REPORTED,
            observations=(),
            review_method_id=None,
            source_ids=("doi:example",),
            limitations=("study did not report unresolved fraction",),
        ),
        lot_id=None,
        supplier_product=None,
        supplier_lot=None,
        source_documents=(
            source_document(
                subject_lot_id=None,
                kind=SourceDocumentKind.LITERATURE,
            ),
        ),
    )


def generic_profile() -> NaturalCompositionProfile:
    return profile(
        profile_id="profile-generic",
        authority=CompositionAuthority.GENERIC_MATERIAL_PROXY,
        observations=(
            constituent(
                source_lot_id=None,
                origin=ObservationOrigin.GENERIC_PROXY,
                value=None,
                lower_bound=0.1,
                upper_bound=0.6,
                basis=ConstituentBasis.LITERATURE_RANGE,
                calibration_state=CalibrationState.NOT_APPLICABLE,
                response_model_id=None,
                standard_uncertainty=None,
                uncertainty_note="generic proxy range",
                lod=None,
                loq=None,
                analytical_run_id=None,
            ),
        ),
        unresolved=UnresolvedFractionDisclosure(
            state=UnresolvedDisclosureState.NOT_REPORTED,
            observations=(),
            review_method_id=None,
            source_ids=("repository:generic-profile",),
            limitations=("generic profile has no lot-specific unknown fraction",),
        ),
        lot_id=None,
        supplier_product=None,
        supplier_lot=None,
        botanical_species=None,
        variety_or_chemotype=None,
        geographic_origin=None,
        extraction_method=None,
        source_documents=(
            source_document(
                subject_lot_id=None,
                kind=SourceDocumentKind.LITERATURE,
            ),
        ),
    )


def test_c7_closed_vocabularies_and_precedence_are_exact() -> None:
    assert {item.value for item in ConstituentBasis} == {
        "CALIBRATED_MASS_FRACTION",
        "CALIBRATED_MOLAR_FRACTION",
        "ESTIMATED_MASS_FRACTION",
        "RESPONSE_CORRECTED_RELATIVE_FRACTION",
        "NORMALIZED_AREA_PERCENT",
        "RELATIVE_RESPONSE",
        "PRESENCE_ONLY",
        "LITERATURE_RANGE",
        "UNKNOWN",
    }
    assert PERMITTED_CONSTITUENT_BASES == tuple(ConstituentBasis)
    assert C7_COMPOSITION_PRECEDENCE == tuple(CompositionAuthority)
    assert [item.value for item in C7_COMPOSITION_PRECEDENCE] == [
        "EXACT_LOT_QUANTIFIED",
        "EXACT_LOT_RELATIVE_PROFILE",
        "SUPPLIER_BATCH_SPECIFIC",
        "SPECIFIC_LITERATURE_PROXY",
        "GENERIC_MATERIAL_PROXY",
        "UNKNOWN",
    ]
    assert {item.value for item in ProjectionFamily} == {
        "OLFACTORY_HEADSPACE",
        "REGULATORY_ALLERGEN",
        "IDENTITY_AUTHENTICITY",
    }
    assert {item.value for item in UnresolvedFractionKind} == {
        "UNKNOWN_PEAK",
        "COELUTION",
        "UNRESOLVED_GROUP",
        "UNIDENTIFIED_GC_O_EVENT",
        "BELOW_QUANTITATION",
        "UNASSIGNED_MASS",
        "UNASSIGNED_AREA",
    }


def test_c7_module_exports_only_the_declared_contract() -> None:
    from engine.physics import natural_lots

    assert set(natural_lots.__all__) == PUBLIC_C7_NAMES
    assert len(natural_lots.__all__) == len(set(natural_lots.__all__))
    assert "does not" in (natural_lots.__doc__ or "").lower()
    assert "concentration" in (natural_lots.__doc__ or "").lower()


def test_source_and_analytical_references_are_exact_lot_hash_bound() -> None:
    document = source_document()
    run = analytical_run()
    assert (
        document.content_sha256
        != replace(
            document,
            document_sha256=digest("e"),
        ).content_sha256
    )
    assert run.content_sha256 != replace(run, method_id="method-2").content_sha256
    assert SourceDocumentReference.from_mapping(document.to_mapping()) == document
    assert AnalyticalRunReference.from_mapping(run.to_mapping()) == run

    with pytest.raises(NaturalLotContractError, match="SHA-256"):
        replace(document, document_sha256="not-a-hash")
    with pytest.raises(NaturalLotContractError, match="unknown fields"):
        SourceDocumentReference.from_mapping({**document.to_mapping(), "url": "x"})


def test_natural_material_lot_requires_supplier_lot_and_exact_bindings() -> None:
    lot = natural_lot()
    assert lot.source_documents[0].subject_lot_id == lot.lot_id
    assert lot.analytical_runs[0].subject_lot_id == lot.lot_id
    assert NaturalMaterialLot.from_mapping(lot.to_mapping()) == lot

    with pytest.raises(NaturalLotContractError, match="supplier_lot"):
        natural_lot(supplier_lot="")
    with pytest.raises(NaturalLotContractError, match="source document.*lot"):
        natural_lot(source_documents=(source_document(subject_lot_id="other"),))
    with pytest.raises(NaturalLotContractError, match="analytical run.*lot"):
        natural_lot(analytical_runs=(analytical_run(subject_lot_id="other"),))
    with pytest.raises(NaturalLotContractError, match="duplicate"):
        natural_lot(source_documents=(source_document(), source_document()))


def test_natural_material_lot_unknown_fields_are_explicit() -> None:
    with pytest.raises(NaturalLotContractError, match="unknown_identity_fields"):
        natural_lot(variety_or_chemotype=None)

    lot = natural_lot(
        variety_or_chemotype=None,
        geographic_origin=None,
        unknown_identity_fields=("geographic_origin", "variety_or_chemotype"),
    )
    assert lot.variety_or_chemotype is None
    assert lot.geographic_origin is None
    assert lot.unknown_identity_fields == (
        "geographic_origin",
        "variety_or_chemotype",
    )
    with pytest.raises(NaturalLotContractError, match="declared unknown"):
        natural_lot(unknown_identity_fields=("botanical_species",))


def test_natural_material_lot_date_chronology_fails_closed() -> None:
    with pytest.raises(NaturalLotContractError, match="harvest_or_production_date"):
        natural_lot(harvest_or_production_date=date(2025, 10, 1))
    with pytest.raises(NaturalLotContractError, match="opened_on"):
        natural_lot(opened_on=date(2025, 8, 1))


def test_every_lot_identity_axis_changes_content_hash() -> None:
    baseline = natural_lot()
    variants = (
        replace(baseline, botanical_species="Lavandula latifolia"),
        replace(baseline, variety_or_chemotype="camphor-rich"),
        replace(baseline, plant_part="leaves"),
        replace(baseline, geographic_origin="Bulgaria"),
        replace(baseline, extraction_method="solvent extraction"),
        replace(baseline, supplier_product="Lavender EO Fine"),
        replace(baseline, supplier_lot="batch-78"),
        replace(baseline, processing=("rectified",)),
        replace(baseline, storage_conditions=("refrigerated",)),
    )
    assert len({baseline.content_sha256, *(item.content_sha256 for item in variants)}) == 10


@pytest.mark.parametrize(
    ("basis", "value", "calibration", "response_model"),
    (
        (ConstituentBasis.CALIBRATED_MASS_FRACTION, 0.4, CalibrationState.CALIBRATED, "model"),
        (ConstituentBasis.CALIBRATED_MOLAR_FRACTION, 0.4, CalibrationState.CALIBRATED, "model"),
        (ConstituentBasis.ESTIMATED_MASS_FRACTION, 0.4, CalibrationState.UNCALIBRATED, None),
        (
            ConstituentBasis.RESPONSE_CORRECTED_RELATIVE_FRACTION,
            0.4,
            CalibrationState.RESPONSE_CORRECTED,
            "model",
        ),
        (ConstituentBasis.NORMALIZED_AREA_PERCENT, 40.0, CalibrationState.UNCALIBRATED, None),
        (ConstituentBasis.RELATIVE_RESPONSE, 40.0, CalibrationState.UNCALIBRATED, None),
    ),
)
def test_quantitative_constituent_bases_retain_value_and_authority(
    basis: ConstituentBasis,
    value: float,
    calibration: CalibrationState,
    response_model: str | None,
) -> None:
    observation = constituent(
        basis=basis,
        value=value,
        calibration_state=calibration,
        response_model_id=response_model,
    )
    assert observation.value == value
    assert observation.basis is basis
    assert observation.supports_absolute_composition is (
        basis
        in {
            ConstituentBasis.CALIBRATED_MASS_FRACTION,
            ConstituentBasis.CALIBRATED_MOLAR_FRACTION,
        }
    )
    assert ConstituentObservation.from_mapping(observation.to_mapping()) == observation


def test_presence_unknown_and_literature_range_shapes_are_distinct() -> None:
    presence = constituent(
        source_lot_id=None,
        origin=ObservationOrigin.LITERATURE_REPORTED,
        value=None,
        basis=ConstituentBasis.PRESENCE_ONLY,
        calibration_state=CalibrationState.NOT_APPLICABLE,
        response_model_id=None,
        standard_uncertainty=None,
        lod=None,
        loq=None,
        analytical_run_id=None,
    )
    unknown = replace(presence, basis=ConstituentBasis.UNKNOWN)
    literature = replace(
        presence,
        basis=ConstituentBasis.LITERATURE_RANGE,
        lower_bound=0.2,
        upper_bound=0.6,
    )
    assert presence.value is None and presence.lower_bound is None
    assert unknown.value is None and unknown.upper_bound is None
    assert literature.value is None
    assert (literature.lower_bound, literature.upper_bound) == (0.2, 0.6)

    with pytest.raises(NaturalLotContractError, match="numeric"):
        replace(presence, value=1.0)
    with pytest.raises(NaturalLotContractError, match="lower_bound.*upper_bound"):
        replace(literature, lower_bound=0.7)


def test_calibrated_and_response_corrected_bases_require_matching_models() -> None:
    with pytest.raises(NaturalLotContractError, match="CALIBRATED"):
        constituent(calibration_state=CalibrationState.UNCALIBRATED)
    with pytest.raises(NaturalLotContractError, match="response_model_id"):
        constituent(response_model_id=None)
    with pytest.raises(NaturalLotContractError, match="RESPONSE_CORRECTED"):
        constituent(
            basis=ConstituentBasis.RESPONSE_CORRECTED_RELATIVE_FRACTION,
            calibration_state=CalibrationState.CALIBRATED,
        )


def test_normalized_area_percent_cannot_masquerade_as_concentration() -> None:
    area = area_observation(value=62.5)
    assert area.basis is ConstituentBasis.NORMALIZED_AREA_PERCENT
    assert area.value == 62.5
    assert area.supports_absolute_composition is False
    with pytest.raises(NaturalLotContractError, match="CALIBRATED"):
        replace(area, basis=ConstituentBasis.CALIBRATED_MASS_FRACTION)
    with pytest.raises(NaturalLotContractError, match="0.*100"):
        area_observation(value=100.01)


def test_fraction_bases_are_bounded_without_forcing_profile_closure() -> None:
    with pytest.raises(NaturalLotContractError, match="0.*1"):
        constituent(value=1.01)

    first = area_observation(value=40.0)
    second = replace(
        first,
        observation_id="obs-area-linalyl-acetate",
        chemical_id="cas:115-95-7",
        chemical_name="linalyl acetate",
        value=33.0,
    )
    relative = profile(
        authority=CompositionAuthority.EXACT_LOT_RELATIVE_PROFILE,
        observations=(first, second),
    )
    assert relative.named_totals_by_basis == {"NORMALIZED_AREA_PERCENT": 73.0}
    assert relative.named_totals_by_basis["NORMALIZED_AREA_PERCENT"] != 100.0


def test_exact_lot_measurements_require_exact_run_and_source_lot() -> None:
    with pytest.raises(NaturalLotContractError, match="analytical_run_id"):
        constituent(analytical_run_id=None)
    with pytest.raises(NaturalLotContractError, match="source_lot_id"):
        constituent(source_lot_id=None)

    reported = constituent(
        source_lot_id="batch-77",
        origin=ObservationOrigin.SUPPLIER_BATCH_REPORTED,
        analytical_run_id=None,
    )
    assert reported.analytical_run_id is None


def test_lod_loq_and_censoring_are_fail_closed() -> None:
    censored = constituent(
        value=None,
        censoring=CensoringState.BELOW_LOQ,
    )
    assert censored.value is None
    assert censored.loq == 0.0003
    with pytest.raises(NaturalLotContractError, match="LOQ"):
        constituent(value=None, censoring=CensoringState.BELOW_LOQ, loq=None)
    with pytest.raises(NaturalLotContractError, match="censored"):
        constituent(value=0.1, censoring=CensoringState.BELOW_LOD)
    with pytest.raises(NaturalLotContractError, match="LOD.*LOQ"):
        constituent(lod=0.1, loq=0.01)


@pytest.mark.parametrize("kind", tuple(UnresolvedFractionKind))
def test_every_unresolved_fraction_kind_remains_visible(
    kind: UnresolvedFractionKind,
) -> None:
    if kind is UnresolvedFractionKind.BELOW_QUANTITATION:
        observation = unresolved_observation(
            kind=kind,
            value=None,
            limit_value=0.5,
        )
    elif kind is UnresolvedFractionKind.UNIDENTIFIED_GC_O_EVENT:
        observation = unresolved_observation(
            kind=kind,
            value=None,
            basis=ConstituentBasis.PRESENCE_ONLY,
            limit_value=None,
        )
    elif kind is UnresolvedFractionKind.UNASSIGNED_MASS:
        observation = unresolved_observation(
            kind=kind,
            value=0.08,
            basis=ConstituentBasis.ESTIMATED_MASS_FRACTION,
        )
    else:
        observation = unresolved_observation(kind=kind)
    disclosure = present_unresolved(observation)
    assert disclosure.observations[0].kind is kind
    assert UnresolvedFractionDisclosure.from_mapping(disclosure.to_mapping()) == disclosure


def test_unresolved_disclosure_cannot_be_omitted_or_misstated() -> None:
    with pytest.raises(NaturalLotContractError, match="PRESENT"):
        UnresolvedFractionDisclosure(
            state=UnresolvedDisclosureState.PRESENT,
            observations=(),
            review_method_id="method",
            source_ids=("source",),
            limitations=(),
        )
    with pytest.raises(NaturalLotContractError, match="NOT_REPORTED"):
        replace(
            present_unresolved(),
            state=UnresolvedDisclosureState.NOT_REPORTED,
        )
    with pytest.raises(NaturalLotContractError, match="review_method_id"):
        replace(reviewed_no_unresolved(), review_method_id=None)


@pytest.mark.parametrize(
    "authority",
    (
        CompositionAuthority.EXACT_LOT_QUANTIFIED,
        CompositionAuthority.EXACT_LOT_RELATIVE_PROFILE,
    ),
)
def test_exact_lot_profile_levels_require_matching_observation_lot(
    authority: CompositionAuthority,
) -> None:
    observation = (
        constituent(source_lot_id="other")
        if authority is CompositionAuthority.EXACT_LOT_QUANTIFIED
        else area_observation(source_lot_id="other")
    )
    with pytest.raises(NaturalLotContractError, match="exact lot"):
        profile(authority=authority, observations=(observation,))


def test_profile_authority_labels_cannot_be_promoted_by_shape() -> None:
    with pytest.raises(NaturalLotContractError, match="quantified"):
        profile(
            authority=CompositionAuthority.EXACT_LOT_QUANTIFIED,
            observations=(area_observation(),),
        )
    with pytest.raises(NaturalLotContractError, match="relative"):
        profile(
            authority=CompositionAuthority.EXACT_LOT_RELATIVE_PROFILE,
            observations=(constituent(),),
        )
    with pytest.raises(NaturalLotContractError, match="supplier"):
        profile(
            authority=CompositionAuthority.SUPPLIER_BATCH_SPECIFIC,
            lot_id=None,
            supplier_lot=None,
        )
    with pytest.raises(NaturalLotContractError, match="specific proxy"):
        profile(
            authority=CompositionAuthority.SPECIFIC_LITERATURE_PROXY,
            lot_id=None,
            supplier_product=None,
            supplier_lot=None,
            botanical_species=None,
        )


def test_unknown_profile_has_no_answer_bearing_observations() -> None:
    unknown = profile(
        profile_id="profile-unknown",
        authority=CompositionAuthority.UNKNOWN,
        completeness=NaturalCompositionCompleteness.UNKNOWN,
        observations=(),
        unresolved=UnresolvedFractionDisclosure(
            state=UnresolvedDisclosureState.NOT_REPORTED,
            observations=(),
            review_method_id=None,
            source_ids=(),
            limitations=("composition unavailable",),
        ),
        lot_id=None,
        supplier_product=None,
        supplier_lot=None,
        botanical_species=None,
        variety_or_chemotype=None,
        geographic_origin=None,
        extraction_method=None,
        source_documents=(),
    )
    assert unknown.observations == ()
    with pytest.raises(NaturalLotContractError, match="UNKNOWN"):
        replace(unknown, observations=(area_observation(source_lot_id=None),))


def test_profile_round_trip_rejects_nested_and_top_level_tampering() -> None:
    original = profile()
    assert NaturalCompositionProfile.from_mapping(original.to_mapping()) == original

    nested = original.to_mapping()
    observations = nested["observations"]
    assert isinstance(observations, list)
    first = observations[0]
    assert isinstance(first, dict)
    first["value"] = 0.99
    with pytest.raises(NaturalLotContractError, match="content_sha256"):
        NaturalCompositionProfile.from_mapping(nested)

    with pytest.raises(NaturalLotContractError, match="unknown fields"):
        NaturalCompositionProfile.from_mapping({**original.to_mapping(), "normalized_to_100": True})


def test_selection_uses_exact_six_level_precedence() -> None:
    candidates = (
        generic_profile(),
        supplier_profile(),
        relative_profile(),
        specific_literature_profile(),
        profile(),
    )
    selected = select_natural_composition(request(), candidates)
    assert isinstance(selected, NaturalCompositionSelection)
    assert selected.status is SelectionStatus.SELECTED
    assert selected.selected_profile is not None
    assert selected.selected_profile.profile_id == "profile-exact-quant"
    assert selected.selected_authority is CompositionAuthority.EXACT_LOT_QUANTIFIED
    assert selected.precedence_rank == 1
    assert selected.fallback_steps == 0
    assert selected.uncertainty_widened is False


@pytest.mark.parametrize(
    ("candidate_factory", "authority", "rank", "steps"),
    (
        (
            relative_profile,
            CompositionAuthority.EXACT_LOT_RELATIVE_PROFILE,
            2,
            1,
        ),
        (supplier_profile, CompositionAuthority.SUPPLIER_BATCH_SPECIFIC, 3, 2),
        (
            specific_literature_profile,
            CompositionAuthority.SPECIFIC_LITERATURE_PROXY,
            4,
            3,
        ),
        (generic_profile, CompositionAuthority.GENERIC_MATERIAL_PROXY, 5, 4),
    ),
)
def test_selection_discloses_every_fallback(
    candidate_factory: object,
    authority: CompositionAuthority,
    rank: int,
    steps: int,
) -> None:
    assert callable(candidate_factory)
    selected = select_natural_composition(request(), (candidate_factory(),))
    assert selected.status is SelectionStatus.SELECTED
    assert selected.selected_authority is authority
    assert selected.precedence_rank == rank
    assert selected.fallback_steps == steps
    assert selected.uncertainty_widened is True
    assert selected.warnings


def test_selection_requires_exact_lot_supplier_and_proxy_scope_matches() -> None:
    wrong_lot = replace(relative_profile(), lot_id="other")
    wrong_batch = replace(supplier_profile(), supplier_lot="batch-99")
    wrong_species = replace(
        specific_literature_profile(),
        botanical_species="Lavandula latifolia",
    )
    selected = select_natural_composition(
        request(),
        (wrong_lot, wrong_batch, wrong_species, generic_profile()),
    )
    assert selected.selected_authority is CompositionAuthority.GENERIC_MATERIAL_PROXY


def test_equal_rank_disagreement_is_ambiguous_and_no_profile_abstains() -> None:
    first = relative_profile()
    second = replace(first, profile_id="profile-exact-relative-2")
    ambiguous = select_natural_composition(request(), (first, second))
    assert ambiguous.status is SelectionStatus.AMBIGUOUS
    assert ambiguous.selected_profile is None
    assert ambiguous.selected_authority is CompositionAuthority.UNKNOWN

    abstained = select_natural_composition(request(), ())
    assert abstained.status is SelectionStatus.ABSTAINED
    assert abstained.selected_profile is None
    assert abstained.precedence_rank == 6


def test_request_from_lot_preserves_exact_identity() -> None:
    lot = natural_lot()
    from_lot = NaturalCompositionRequest.from_lot(lot)
    assert from_lot.requested_lot_id == lot.lot_id
    assert from_lot.supplier_lot == lot.supplier_lot
    assert from_lot.botanical_species == lot.botanical_species


def test_three_projection_families_are_separate_and_basis_preserving() -> None:
    relative = relative_profile()
    olfactory = build_natural_projection(relative, ProjectionFamily.OLFACTORY_HEADSPACE)
    identity = build_natural_projection(relative, ProjectionFamily.IDENTITY_AUTHENTICITY)
    regulatory = build_natural_projection(relative, ProjectionFamily.REGULATORY_ALLERGEN)

    assert isinstance(olfactory, NaturalProjection)
    assert isinstance(olfactory.entries[0], ProjectionEntry)
    assert olfactory.status is ProjectionStatus.AVAILABLE
    assert identity.status is ProjectionStatus.AVAILABLE
    assert regulatory.status is ProjectionStatus.WITHHELD
    assert regulatory.entries == ()
    assert olfactory.family is ProjectionFamily.OLFACTORY_HEADSPACE
    assert identity.family is ProjectionFamily.IDENTITY_AUTHENTICITY
    assert olfactory.content_sha256 != identity.content_sha256
    assert olfactory.entries[0].basis is ConstituentBasis.NORMALIZED_AREA_PERCENT
    assert olfactory.entries[0].value == 42.0
    assert identity.entries[0].basis is ConstituentBasis.NORMALIZED_AREA_PERCENT


def test_regulatory_projection_requires_complete_mass_fraction_authority() -> None:
    complete = profile(
        completeness=NaturalCompositionCompleteness.COMPLETE,
        unresolved=reviewed_no_unresolved(),
    )
    regulatory = build_natural_projection(
        complete,
        ProjectionFamily.REGULATORY_ALLERGEN,
    )
    assert regulatory.status is ProjectionStatus.AVAILABLE
    assert regulatory.entries
    assert all(
        entry.basis is ConstituentBasis.CALIBRATED_MASS_FRACTION for entry in regulatory.entries
    )

    partial = replace(complete, completeness=NaturalCompositionCompleteness.PARTIAL)
    assert (
        build_natural_projection(
            partial,
            ProjectionFamily.REGULATORY_ALLERGEN,
        ).status
        is ProjectionStatus.WITHHELD
    )
    assert (
        build_natural_projection(
            generic_profile(),
            ProjectionFamily.REGULATORY_ALLERGEN,
        ).entries
        == ()
    )


def test_projection_entry_cannot_relabel_its_source_basis() -> None:
    projection = build_natural_projection(
        relative_profile(),
        ProjectionFamily.IDENTITY_AUTHENTICITY,
    )
    entry = projection.entries[0]
    with pytest.raises(NaturalLotContractError, match="source observation"):
        replace(entry, basis=ConstituentBasis.CALIBRATED_MASS_FRACTION)


def reference_range(
    *,
    basis: ConstituentBasis = ConstituentBasis.NORMALIZED_AREA_PERCENT,
    lower_bound: float = 35.0,
    upper_bound: float = 45.0,
) -> AuthenticityReferenceRange:
    return AuthenticityReferenceRange(
        reference_id="reference-linalool",
        chemical_id="cas:78-70-6",
        basis=basis,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        source_id="iso-profile-example",
        source_sha256=digest("f"),
    )


def test_authenticity_comparison_uses_only_basis_compatible_values() -> None:
    assessment = assess_authenticity_profile(
        relative_profile(),
        (reference_range(),),
        expected_chemotype="linalool/linalyl acetate",
        observed_chemotype="linalool/linalyl acetate",
        possible_adulteration_indicators=(),
        limitations=("reference supplied for contract test",),
    )
    assert isinstance(assessment, AuthenticityAssessment)
    assert assessment.decision is AuthenticityDecision.CONSISTENT_WITH_REFERENCE
    assert assessment.compared_observation_count == 1
    assert assessment.deviations == ()

    incompatible = assess_authenticity_profile(
        relative_profile(),
        (
            reference_range(
                basis=ConstituentBasis.CALIBRATED_MASS_FRACTION,
                lower_bound=0.35,
                upper_bound=0.45,
            ),
        ),
        expected_chemotype=None,
        observed_chemotype=None,
        possible_adulteration_indicators=(),
        limitations=(),
    )
    assert incompatible.decision is AuthenticityDecision.INSUFFICIENT_EVIDENCE
    assert incompatible.compared_observation_count == 0


def test_authenticity_deviation_chemotype_and_indicator_decisions_are_explicit() -> None:
    outside = assess_authenticity_profile(
        replace(
            relative_profile(),
            observations=(area_observation(value=55.0),),
        ),
        (reference_range(),),
        expected_chemotype=None,
        observed_chemotype=None,
        possible_adulteration_indicators=(),
        limitations=(),
    )
    assert outside.decision is AuthenticityDecision.OUTSIDE_REFERENCE_PROFILE
    assert len(outside.deviations) == 1
    assert isinstance(outside.deviations[0], AuthenticityDeviation)

    mismatch = assess_authenticity_profile(
        relative_profile(),
        (reference_range(),),
        expected_chemotype="linalool/linalyl acetate",
        observed_chemotype="camphor-rich",
        possible_adulteration_indicators=(),
        limitations=(),
    )
    assert mismatch.decision is AuthenticityDecision.CHEMOTYPE_MISMATCH

    indicators = assess_authenticity_profile(
        relative_profile(),
        (reference_range(),),
        expected_chemotype=None,
        observed_chemotype=None,
        possible_adulteration_indicators=("undeclared marker supplied by reviewer",),
        limitations=(),
    )
    assert indicators.decision is AuthenticityDecision.POSSIBLE_ADULTERATION_INDICATORS


def aging_observation(
    *,
    observation_id: str,
    sequence_number: int,
    observed_at: datetime,
    previous_observation_sha256: str | None,
    lot_id: str = "lot-1",
) -> LotAgingObservation:
    return LotAgingObservation(
        observation_id=observation_id,
        lot_id=lot_id,
        sequence_number=sequence_number,
        observed_at=observed_at,
        storage_conditions=("amber glass", "dark"),
        oxidation_stability_observations=("odor/color review recorded",),
        source_document_ids=("doc-coa-1",),
        analytical_run_ids=("run-1",),
        previous_observation_sha256=previous_observation_sha256,
    )


def test_aging_series_versions_state_without_changing_lot_identity() -> None:
    first = aging_observation(
        observation_id="aging-1",
        sequence_number=1,
        observed_at=datetime(2025, 9, 10, tzinfo=timezone.utc),
        previous_observation_sha256=None,
    )
    second = aging_observation(
        observation_id="aging-2",
        sequence_number=2,
        observed_at=datetime(2025, 10, 10, tzinfo=timezone.utc),
        previous_observation_sha256=first.content_sha256,
    )
    series = validate_aging_series(natural_lot(), (first, second))
    assert series == (first, second)
    assert all(item.lot_id == "lot-1" for item in series)


def test_aging_series_rejects_identity_time_sequence_and_hash_drift() -> None:
    first = aging_observation(
        observation_id="aging-1",
        sequence_number=1,
        observed_at=datetime(2025, 9, 10, tzinfo=timezone.utc),
        previous_observation_sha256=None,
    )
    second = aging_observation(
        observation_id="aging-2",
        sequence_number=2,
        observed_at=datetime(2025, 10, 10, tzinfo=timezone.utc),
        previous_observation_sha256=first.content_sha256,
    )
    with pytest.raises(NaturalLotContractError, match="lot identity"):
        validate_aging_series(natural_lot(), (first, replace(second, lot_id="other")))
    with pytest.raises(NaturalLotContractError, match="contiguous"):
        validate_aging_series(
            natural_lot(),
            (first, replace(second, sequence_number=3)),
        )
    with pytest.raises(NaturalLotContractError, match="strictly increasing"):
        validate_aging_series(
            natural_lot(),
            (first, replace(second, observed_at=first.observed_at)),
        )
    with pytest.raises(NaturalLotContractError, match="previous.*SHA-256"):
        validate_aging_series(
            natural_lot(),
            (first, replace(second, previous_observation_sha256=digest("0"))),
        )


def test_lot_aging_observation_requires_timezone_and_round_trips() -> None:
    with pytest.raises(NaturalLotContractError, match="timezone-aware"):
        aging_observation(
            observation_id="aging-1",
            sequence_number=1,
            observed_at=datetime(2025, 9, 10),
            previous_observation_sha256=None,
        )
    item = aging_observation(
        observation_id="aging-1",
        sequence_number=1,
        observed_at=datetime(2025, 9, 10, tzinfo=timezone.utc),
        previous_observation_sha256=None,
    )
    assert LotAgingObservation.from_mapping(item.to_mapping()) == item


def test_c7_module_has_no_legacy_backend_database_oav_or_sensory_dependency() -> None:
    source_path = Path(__file__).resolve().parents[1] / "engine" / "physics" / "natural_lots.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    imported_modules: set[str] = set()
    prohibited_calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called = node.func.id
            elif isinstance(node.func, ast.Attribute):
                called = node.func.attr
            else:
                continue
            if called.casefold() in {
                "connect",
                "execute",
                "executescript",
                "get_lot_profile",
                "register_lot_profile",
                "composite_headspace",
                "composite_oav",
            }:
                prohibited_calls.add(called)

    assert not any(
        module.startswith(
            (
                "backend",
                "sqlalchemy",
                "sqlite3",
                "engine.reconstruction",
                "engine.pipeline",
                "engine.analytical",
                "engine.safety",
                "engine.sensory",
            )
        )
        for module in imported_modules
    )
    assert prohibited_calls == set()
