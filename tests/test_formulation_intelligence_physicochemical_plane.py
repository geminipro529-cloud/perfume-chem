from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from engine.formulation_intelligence.contracts import (
    AuthorityCeiling,
    EvidenceClass,
    PlaneAssessment,
    PlaneId,
    ProvenanceRef,
    SupportInterval,
    SupportMeasure,
    ValueState,
)
from engine.formulation_intelligence.physicochemical_plane import (
    CompositeConstituent,
    ConcentrationBasis,
    HeadspacePrediction,
    InstrumentalObservation,
    MaterialKind,
    NaturalCompositeDecomposition,
    OAVMethod,
    OdorThresholdReference,
    ODTKind,
    ODTUnit,
    PhysicochemicalMaterialIdentity,
    PhysicochemicalPacket,
    PhysicochemicalPlaneAdapter,
    PhysicochemicalScope,
    QuantitativeState,
)


def _provenance(
    provenance_id: str,
    evidence_class: EvidenceClass,
    *,
    independence_key: str | None = None,
) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=provenance_id,
        source_ref=f"test://{provenance_id}",
        evidence_class=evidence_class,
        independence_key=independence_key or provenance_id,
    )


def _scope(
    *,
    material_identity_id: str = "material:hedione:lot-7",
    condition_id: str = "condition:blotter-25c-300s",
    sample_id: str = "sample:formula-v7:aliquot-a",
) -> PhysicochemicalScope:
    return PhysicochemicalScope(
        target_scope="target:intent-sha256:abc123",
        sample_id=sample_id,
        material_identity_id=material_identity_id,
        matrix_id="matrix:ethanol-95-v7",
        condition_id=condition_id,
        temperature_c=25.0,
        elapsed_seconds=300.0,
        temporal_scope="five-minute headspace",
    )


def _molecule_identity(
    *,
    material_id: str = "material:hedione:lot-7",
    stock_fraction: float | None = 0.50,
    fraction_basis: str | None = "w/w",
    carrier_identity: str | None = "carrier:dep:lot-2",
) -> PhysicochemicalMaterialIdentity:
    return PhysicochemicalMaterialIdentity(
        material_id=material_id,
        kind=MaterialKind.EXACT_MOLECULE,
        material_label="Hedione, supplier lot 7",
        exact_identity_key="cas:24851-98-7|stereo:declared-mixture|grade:supplier-a",
        source_name="supplier-a",
        lot_id="lot-7",
        stock_fraction=stock_fraction,
        fraction_basis=fraction_basis,
        carrier_identity=carrier_identity,
    )


def _odt(
    *,
    value: float = 2.0,
    unit: ODTUnit = ODTUnit.PPM,
    kind: ODTKind = ODTKind.MONOMOLECULAR,
    source_id: str = "odt-primary-1",
) -> OdorThresholdReference:
    return OdorThresholdReference(
        threshold_id=f"threshold:{source_id}",
        value=value,
        unit=unit,
        medium_id="medium:ethanol-solution",
        threshold_kind=kind,
        source=_provenance(source_id, EvidenceClass.PRIMARY_SOURCE),
    )


def _support(
    claim_id: str,
    *,
    source_id: str,
    evidence_class: EvidenceClass,
    measure: SupportMeasure = SupportMeasure.EVIDENCE_SUPPORT,
    lower: float = 0.40,
    upper: float = 0.70,
) -> SupportInterval:
    return SupportInterval(
        interval_id=f"support:{claim_id}",
        claim_id=claim_id,
        lower=lower,
        upper=upper,
        provenance_refs=(_provenance(source_id, evidence_class),),
        support_measure=measure,
    )


def _molecule_packet(
    *,
    packet_id: str = "physchem-packet-a",
    identity: PhysicochemicalMaterialIdentity | None = None,
    scope: PhysicochemicalScope | None = None,
    concentration_ppm: float | None = 120.0,
    concentration_basis: ConcentrationBasis | None = ConcentrationBasis.PPM_W_W_CONCENTRATE,
    odt: OdorThresholdReference | None = None,
    oav: float | None = 60.0,
    quantitative_support: SupportInterval | None = None,
    predictions: tuple[HeadspacePrediction, ...] = (),
    observations: tuple[InstrumentalObservation, ...] = (),
) -> PhysicochemicalPacket:
    resolved_identity = identity or _molecule_identity()
    resolved_scope = scope or _scope(material_identity_id=resolved_identity.material_id)
    claim_id = f"physchem.oav:{packet_id}"
    return PhysicochemicalPacket(
        packet_id=packet_id,
        scope=resolved_scope,
        material=resolved_identity,
        concentration_ppm=concentration_ppm,
        concentration_basis=concentration_basis,
        odt=odt if odt is not None else _odt(),
        oav=oav,
        oav_method=OAVMethod.MONOMOLECULAR if oav is not None else None,
        composite_decomposition=None,
        quantitative_support=(
            quantitative_support
            if quantitative_support is not None
            else (
                _support(
                    claim_id,
                    source_id="oav-model-a",
                    evidence_class=EvidenceClass.COMPUTATIONAL_MODEL,
                )
                if oav is not None
                else None
            )
        ),
        headspace_predictions=predictions,
        instrumental_observations=observations,
        provenance_refs=(_provenance("formula-input-a", EvidenceClass.OFFICIAL_RECORD),),
    )


def _natural_identity() -> PhysicochemicalMaterialIdentity:
    return PhysicochemicalMaterialIdentity(
        material_id="material:magnolia-eo:lot-m1",
        kind=MaterialKind.NATURAL_MIXTURE,
        material_label="Magnolia EO, lot M1",
        exact_identity_key=(
            "botanical:magnolia-alba|part:flower|origin:declared|extraction:steam-distilled|lot:m1"
        ),
        source_name="supplier-m",
        lot_id="lot-m1",
        stock_fraction=1.0,
        fraction_basis="w/w as supplied",
        carrier_identity="carrier:none:neat-as-supplied",
    )


def _decomposition(
    identity: PhysicochemicalMaterialIdentity,
) -> NaturalCompositeDecomposition:
    return NaturalCompositeDecomposition(
        decomposition_id="decomposition:magnolia-lot-m1:gco-v1",
        material_identity_id=identity.material_id,
        method_version="gc-o decomposition v1, source-bound",
        constituents=(
            CompositeConstituent(
                constituent_id="constituent:linalool",
                exact_identity_key="cas:78-70-6|stereo:declared-mixture",
                fraction=0.25,
                fraction_basis="w/w of exact natural lot",
                odt=_odt(value=0.004, source_id="linalool-odt"),
            ),
            CompositeConstituent(
                constituent_id="constituent:methyl-eugenol",
                exact_identity_key="cas:93-15-2|achiral:true",
                fraction=0.02,
                fraction_basis="w/w of exact natural lot",
                odt=_odt(value=0.001, source_id="methyl-eugenol-odt"),
            ),
        ),
        provenance_refs=(_provenance("magnolia-gco-source", EvidenceClass.PRIMARY_SOURCE),),
    )


def test_known_packet_validates_oav_and_emits_exact_scope_plane_assessment() -> None:
    packet = _molecule_packet()
    assessment = PhysicochemicalPlaneAdapter(packet).to_plane_assessment()

    assert packet.quantitative_state is QuantitativeState.READY
    assert packet.calculated_oav == pytest.approx(60.0)
    assert assessment.plane_id is PlaneId.PHYSICOCHEMICAL
    assert assessment.scope == packet.scope.assessment_scope
    assert assessment.authority_ceiling is AuthorityCeiling.HYPOTHESIS_ONLY
    assert {claim.claim_key for claim in assessment.claims} >= {
        "physicochemical.concentration_ppm",
        "physicochemical.odt",
        "physicochemical.oav",
    }
    assert assessment.support_intervals[0].support_measure is SupportMeasure.EVIDENCE_SUPPORT
    assert PlaneAssessment.from_dict(assessment.as_dict()) == assessment
    assert PhysicochemicalPacket.from_dict(packet.as_dict()) == packet
    assert json.dumps(packet.as_dict(), sort_keys=True, allow_nan=False)


def test_oav_must_equal_ppm_divided_by_odt_after_unit_conversion() -> None:
    with pytest.raises(ValueError, match="OAV must equal concentration_ppm / ODT_ppm"):
        _molecule_packet(oav=59.0)

    ppb_odt = _odt(value=2_000.0, unit=ODTUnit.PPB)
    packet = _molecule_packet(odt=ppb_odt, oav=60.0)
    assert ppb_odt.value_ppm == pytest.approx(2.0)
    assert packet.calculated_oav == pytest.approx(60.0)


@pytest.mark.parametrize(
    ("identity", "concentration", "basis", "odt", "expected_field"),
    [
        (
            _molecule_identity(stock_fraction=None),
            120.0,
            ConcentrationBasis.PPM_W_W_CONCENTRATE,
            _odt(),
            "stock_fraction",
        ),
        (
            _molecule_identity(fraction_basis=None),
            120.0,
            ConcentrationBasis.PPM_W_W_CONCENTRATE,
            _odt(),
            "fraction_basis",
        ),
        (
            _molecule_identity(carrier_identity=None),
            120.0,
            ConcentrationBasis.PPM_W_W_CONCENTRATE,
            _odt(),
            "carrier_identity",
        ),
        (_molecule_identity(), None, None, _odt(), "concentration_ppm"),
        (_molecule_identity(), 120.0, None, _odt(), "concentration_basis"),
        (_molecule_identity(), 120.0, ConcentrationBasis.PPM_W_W_CONCENTRATE, None, "odt"),
    ],
)
def test_missing_quantitative_inputs_are_unknown_hold_not_dummy_values(
    identity: PhysicochemicalMaterialIdentity,
    concentration: float | None,
    basis: ConcentrationBasis | None,
    odt: OdorThresholdReference | None,
    expected_field: str,
) -> None:
    packet = PhysicochemicalPacket(
        packet_id=f"hold-{expected_field}",
        scope=_scope(material_identity_id=identity.material_id),
        material=identity,
        concentration_ppm=concentration,
        concentration_basis=basis,
        odt=odt,
        oav=None,
        oav_method=None,
        composite_decomposition=None,
        quantitative_support=None,
        headspace_predictions=(),
        instrumental_observations=(),
        provenance_refs=(_provenance("hold-source", EvidenceClass.OFFICIAL_RECORD),),
    )
    assessment = PhysicochemicalPlaneAdapter(packet).to_plane_assessment()

    assert packet.quantitative_state is QuantitativeState.HOLD
    assert packet.calculated_oav is None
    unknown_fields = {item.field_key for item in assessment.unknowns}
    assert f"physicochemical.{expected_field}" in unknown_fields
    criteria = {item.criterion_id: item for item in assessment.native_criteria}
    assert criteria["physicochemical_oav"].value.state is ValueState.UNKNOWN
    assert criteria["physicochemical_oav"].value.value is None
    assert all(claim.claim_key != "physicochemical.oav" for claim in assessment.claims)


def test_natural_mixture_rejects_monomolecular_oav_and_requires_composite_lineage() -> None:
    identity = _natural_identity()
    scope = _scope(material_identity_id=identity.material_id)
    source = _provenance("natural-input", EvidenceClass.OFFICIAL_RECORD)

    with pytest.raises(ValueError, match="natural mixtures cannot use monomolecular"):
        PhysicochemicalPacket(
            packet_id="natural-wrong-method",
            scope=scope,
            material=identity,
            concentration_ppm=100.0,
            concentration_basis=ConcentrationBasis.PPM_W_W_CONCENTRATE,
            odt=_odt(),
            oav=50.0,
            oav_method=OAVMethod.MONOMOLECULAR,
            composite_decomposition=None,
            quantitative_support=_support(
                "physchem.oav:natural-wrong-method",
                source_id="wrong-model",
                evidence_class=EvidenceClass.COMPUTATIONAL_MODEL,
            ),
            headspace_predictions=(),
            instrumental_observations=(),
            provenance_refs=(source,),
        )

    missing = PhysicochemicalPacket(
        packet_id="natural-missing-composite",
        scope=scope,
        material=identity,
        concentration_ppm=100.0,
        concentration_basis=ConcentrationBasis.PPM_W_W_CONCENTRATE,
        odt=None,
        oav=None,
        oav_method=OAVMethod.NATURAL_COMPOSITE,
        composite_decomposition=None,
        quantitative_support=None,
        headspace_predictions=(),
        instrumental_observations=(),
        provenance_refs=(source,),
    )
    assert missing.quantitative_state is QuantitativeState.HOLD
    assert "natural_composite_decomposition" in missing.blocking_fields

    decomposition = _decomposition(identity)
    complete = PhysicochemicalPacket(
        packet_id="natural-complete",
        scope=scope,
        material=identity,
        concentration_ppm=100.0,
        concentration_basis=ConcentrationBasis.PPM_W_W_CONCENTRATE,
        odt=_odt(
            value=0.01,
            kind=ODTKind.COMPOSITE_EFFECTIVE,
            source_id="magnolia-composite-odt",
        ),
        oav=10_000.0,
        oav_method=OAVMethod.NATURAL_COMPOSITE,
        composite_decomposition=decomposition,
        quantitative_support=_support(
            "physchem.oav:natural-complete",
            source_id="natural-composite-model",
            evidence_class=EvidenceClass.COMPUTATIONAL_MODEL,
        ),
        headspace_predictions=(),
        instrumental_observations=(),
        provenance_refs=(source,),
    )
    assert complete.quantitative_state is QuantitativeState.READY
    assert complete.composite_decomposition == decomposition


def test_headspace_prediction_and_instrumental_observation_remain_separate() -> None:
    scope = _scope()
    prediction_claim = "physchem.prediction:vapor-ppm-a"
    observation_claim = "physchem.observation:gc-headspace-a"
    prediction = HeadspacePrediction(
        prediction_id="vapor-ppm-a",
        scope=scope,
        variable_key="headspace_vapor_ppm",
        value=4.25,
        unit="ppm v/v in modeled headspace",
        model_id="modified-raoult-screen",
        model_version="v3",
        support=_support(
            prediction_claim,
            source_id="raoult-model-run-a",
            evidence_class=EvidenceClass.COMPUTATIONAL_MODEL,
        ),
        provenance_refs=(_provenance("raoult-model-run-a", EvidenceClass.COMPUTATIONAL_MODEL),),
    )
    observation = InstrumentalObservation(
        observation_id="gc-headspace-a",
        scope=scope,
        endpoint_key="headspace_vapor_ppm",
        value=3.8,
        unit="ppm v/v measured headspace",
        instrument_id="gc-fid:instrument-2",
        protocol_id="protocol:hs-spme-v1",
        support=_support(
            observation_claim,
            source_id="gc-run-a",
            evidence_class=EvidenceClass.INSTRUMENTAL_OBSERVATION,
        ),
        provenance_refs=(_provenance("gc-run-a", EvidenceClass.INSTRUMENTAL_OBSERVATION),),
    )
    packet = _molecule_packet(predictions=(prediction,), observations=(observation,))
    assessment = PhysicochemicalPlaneAdapter(packet).to_plane_assessment()
    claims = {claim.claim_key: claim for claim in assessment.claims}

    assert claims["physicochemical.prediction.headspace_vapor_ppm"].claim_kind.value == "diagnostic"
    assert (
        claims["physicochemical.observation.headspace_vapor_ppm"].claim_kind.value == "observation"
    )
    assert assessment.authority_ceiling is AuthorityCeiling.EVIDENCE_LIMITED
    assert {item.claim_id for item in assessment.support_intervals} >= {
        prediction_claim,
        observation_claim,
    }

    with pytest.raises(ValueError, match="computational_model provenance"):
        HeadspacePrediction(
            prediction_id="bad-prediction",
            scope=scope,
            variable_key="headspace_vapor_ppm",
            value=1.0,
            unit="ppm",
            model_id="model-a",
            model_version="v1",
            support=_support(
                "physchem.prediction:bad-prediction",
                source_id="bad-observation",
                evidence_class=EvidenceClass.INSTRUMENTAL_OBSERVATION,
            ),
            provenance_refs=(
                _provenance("bad-observation", EvidenceClass.INSTRUMENTAL_OBSERVATION),
            ),
        )


def test_scope_mismatch_and_natural_identity_mismatch_fail_closed() -> None:
    prediction = HeadspacePrediction(
        prediction_id="other-scope",
        scope=_scope(condition_id="other-condition"),
        variable_key="headspace_vapor_ppm",
        value=1.0,
        unit="ppm",
        model_id="model-a",
        model_version="v1",
        support=_support(
            "physchem.prediction:other-scope",
            source_id="model-other",
            evidence_class=EvidenceClass.COMPUTATIONAL_MODEL,
        ),
        provenance_refs=(_provenance("model-other", EvidenceClass.COMPUTATIONAL_MODEL),),
    )
    with pytest.raises(ValueError, match="exact scope"):
        _molecule_packet(predictions=(prediction,))

    identity = _natural_identity()
    decomposition = _decomposition(identity)
    bad_payload = decomposition.as_dict()
    bad_payload["material_identity_id"] = "material:other-natural:lot-z"
    mismatched = NaturalCompositeDecomposition.from_dict(bad_payload)
    with pytest.raises(ValueError, match="decomposition material identity"):
        PhysicochemicalPacket(
            packet_id="natural-mismatch",
            scope=_scope(material_identity_id=identity.material_id),
            material=identity,
            concentration_ppm=None,
            concentration_basis=None,
            odt=None,
            oav=None,
            oav_method=OAVMethod.NATURAL_COMPOSITE,
            composite_decomposition=mismatched,
            quantitative_support=None,
            headspace_predictions=(),
            instrumental_observations=(),
            provenance_refs=(
                _provenance("natural-mismatch-source", EvidenceClass.OFFICIAL_RECORD),
            ),
        )


def test_strict_nested_schemas_reject_missing_and_extra_fields() -> None:
    packet = _molecule_packet()
    payload: dict[str, Any] = packet.as_dict()
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="closed schema"):
        PhysicochemicalPacket.from_dict(payload)

    threshold_payload = _odt().as_dict()
    del threshold_payload["medium_id"]
    with pytest.raises(ValueError, match="closed schema"):
        OdorThresholdReference.from_dict(threshold_payload)

    material_payload = _molecule_identity().as_dict()
    material_payload["schema_version"] = "physicochemical_material_identity_v0"
    with pytest.raises(ValueError, match="schema_version"):
        PhysicochemicalMaterialIdentity.from_dict(material_payload)


def test_no_physicochemical_packet_grants_downstream_perfume_authority() -> None:
    assessment = PhysicochemicalPlaneAdapter(_molecule_packet()).to_plane_assessment()
    unknown_fields = {item.field_key for item in assessment.unknowns}
    assert {
        "downstream.perceived_contribution",
        "downstream.target_fit",
        "downstream.observed_smell",
        "downstream.liking",
        "downstream.performance",
        "downstream.safety",
        "downstream.release",
    }.issubset(unknown_fields)
    assert not any(
        forbidden in claim.claim_key
        for claim in assessment.claims
        for forbidden in ("liking", "safety", "release", "target_fit")
    )


def test_records_are_immutable_and_input_order_does_not_change_packet_hash() -> None:
    scope = _scope()
    prediction_a = HeadspacePrediction(
        prediction_id="prediction-a",
        scope=scope,
        variable_key="partial_pressure",
        value=0.01,
        unit="Pa",
        model_id="model-a",
        model_version="v1",
        support=_support(
            "physchem.prediction:prediction-a",
            source_id="model-a",
            evidence_class=EvidenceClass.COMPUTATIONAL_MODEL,
        ),
        provenance_refs=(_provenance("model-a", EvidenceClass.COMPUTATIONAL_MODEL),),
    )
    prediction_b = HeadspacePrediction(
        prediction_id="prediction-b",
        scope=scope,
        variable_key="activity_coefficient",
        value=1.8,
        unit="dimensionless model parameter",
        model_id="model-b",
        model_version="v1",
        support=_support(
            "physchem.prediction:prediction-b",
            source_id="model-b",
            evidence_class=EvidenceClass.COMPUTATIONAL_MODEL,
        ),
        provenance_refs=(_provenance("model-b", EvidenceClass.COMPUTATIONAL_MODEL),),
    )
    first = _molecule_packet(predictions=(prediction_a, prediction_b))
    second = _molecule_packet(predictions=(prediction_b, prediction_a))
    assert first == second
    assert first.content_sha256 == second.content_sha256
    with pytest.raises(FrozenInstanceError):
        first.oav = 999.0  # type: ignore[misc]
