from __future__ import annotations

import ast
import inspect
import math
from pathlib import Path

import pytest

import engine.evidence as evidence_package
import engine.evidence.unsupported_science as c9
from engine.evidence.unsupported_science import (
    C9_AGING_PROCESSES,
    C9_LEGACY_SURFACE_IDS,
    C9_LEGACY_SURFACES,
    C9_UNSUPPORTED_OUTCOMES,
    AdaptationClaim,
    AdaptationContext,
    AdaptationEvidence,
    AgingClaim,
    AgingEvidence,
    AgingProcess,
    AssayAction,
    AssayParameter,
    AssayParameterRole,
    BuildDValidationReceipt,
    C10Use,
    C9AssessmentStatus,
    C9ClaimDecision,
    C9ContractError,
    C9EvidenceReference,
    C9LegacySurfaceRecord,
    ConcentrationResponsePoint,
    LegacyDisposition,
    MetricComparator,
    ReceptorAssayEvidence,
    ReceptorClaim,
    UnsupportedOutcome,
    ValidationMetric,
    ValidationStatus,
    assess_adaptation_claim,
    assess_aging_claim,
    assess_receptor_claim,
    assess_unsupported_outcome,
    get_c9_legacy_surface,
)
from engine.pipeline.gates import ReleaseGateConfig, gate_formula


PUBLIC_C9_NAMES = (
    "C9_AGING_PROCESSES",
    "C9_LEGACY_SURFACE_IDS",
    "C9_LEGACY_SURFACES",
    "C9_UNSUPPORTED_OUTCOMES",
    "AdaptationClaim",
    "AdaptationContext",
    "AdaptationEvidence",
    "AgingClaim",
    "AgingEvidence",
    "AgingProcess",
    "AssayAction",
    "AssayParameter",
    "AssayParameterRole",
    "BuildDValidationReceipt",
    "C10Use",
    "C9AssessmentStatus",
    "C9ClaimDecision",
    "C9ContractError",
    "C9EvidenceReference",
    "C9LegacySurfaceRecord",
    "ConcentrationResponsePoint",
    "LegacyDisposition",
    "MetricComparator",
    "ReceptorAssayEvidence",
    "ReceptorClaim",
    "UnsupportedOutcome",
    "ValidationMetric",
    "ValidationStatus",
    "assess_adaptation_claim",
    "assess_aging_claim",
    "assess_receptor_claim",
    "assess_unsupported_outcome",
    "get_c9_legacy_surface",
)


def _source() -> C9EvidenceReference:
    return C9EvidenceReference(
        source_id="doi:10.1000/c9-assay",
        locator="https://doi.org/10.1000/c9-assay",
        title="Context-bound C9 assay evidence",
    )


def _response_curve() -> tuple[ConcentrationResponsePoint, ...]:
    return (
        ConcentrationResponsePoint(1.0e-9, "mol/L", 0.05, "fraction_of_control"),
        ConcentrationResponsePoint(1.0e-7, "mol/L", 0.55, "fraction_of_control"),
        ConcentrationResponsePoint(1.0e-5, "mol/L", 0.92, "fraction_of_control"),
    )


def _assay_parameters() -> tuple[AssayParameter, ...]:
    return (
        AssayParameter(AssayParameterRole.POTENCY, "EC50", 8.0e-8, "mol/L"),
        AssayParameter(AssayParameterRole.EFFICACY, "Emax", 0.94, "fraction_of_control"),
    )


def _receptor_evidence(*, species: str = "Homo sapiens") -> ReceptorAssayEvidence:
    return ReceptorAssayEvidence(
        tested_material="Linalool",
        receptor_identity="OR1A1",
        receptor_species=species,
        cell_system="HEK293 heterologous expression",
        concentration_response=_response_curve(),
        parameters=_assay_parameters(),
        assay_action=AssayAction.AGONIST,
        source=_source(),
        applicability="Linalool at OR1A1 in the recorded HEK293 assay only",
    )


def _adaptation_context(
    *,
    species: str = "Homo sapiens",
    stimulus_protocol: str = "three 2-second orthonasal pulses at 30-second intervals",
    timescale_seconds: float = 90.0,
) -> AdaptationContext:
    return AdaptationContext(
        species=species,
        preparation="awake adult psychophysical panel",
        nervous_system_level="whole-person sensory response",
        stimulus_protocol=stimulus_protocol,
        timescale_seconds=timescale_seconds,
    )


def _adaptation_evidence(*, context: AdaptationContext | None = None) -> AdaptationEvidence:
    return AdaptationEvidence(
        context=context or _adaptation_context(),
        stimulus="Linalool in ethanol headspace",
        endpoint="within-session detection-threshold shift",
        source=_source(),
        applicability="Recorded panel, pulse protocol, matrix, and timescale only",
    )


def _aging_evidence(process: AgingProcess) -> AgingEvidence:
    return AgingEvidence(
        process=process,
        subject_identity="Formula lot C9-001",
        matrix="80:20 ethanol-water finished fragrance",
        temperature_k=298.15,
        duration_days=28.0,
        protocol="sealed amber vial, fixed fill volume, sampled on days 0, 7, 14, and 28",
        endpoint="process-specific recorded change",
        source=_source(),
        applicability="Formula lot C9-001 under the recorded storage protocol only",
    )


def _passing_receipt(
    outcome: UnsupportedOutcome = UnsupportedOutcome.LONGEVITY,
    *,
    scope: str = "20% EdP on paper blotter at 25 C and 50% RH for 8 hours",
) -> BuildDValidationReceipt:
    return BuildDValidationReceipt(
        outcome=outcome,
        model_id="build-d-longevity",
        model_version="1.0.0",
        release_sha256="a" * 64,
        endpoint="hours above preregistered panel detection criterion",
        scope=scope,
        held_out_dataset_id="held-out-panel-2026-08",
        comparator_id="constant-baseline-v1",
        metrics=(
            ValidationMetric(
                name="mean_absolute_error_hours",
                value=0.8,
                threshold=1.0,
                comparator=MetricComparator.LESS_THAN_OR_EQUAL,
            ),
        ),
        status=ValidationStatus.PASS,
    )


def _formula(ingredients: dict[str, float], *, name: str) -> dict[str, object]:
    total = sum(ingredients.values()) or 1.0
    return {
        "number": 1,
        "name": name,
        "ingredients_ul": ingredients,
        "dilutions": {},
        "ingredients_pct": {key: value / total * 100.0 for key, value in ingredients.items()},
        "body": name,
    }


def test_public_c9_contract_is_exact_and_exported_from_engine_evidence() -> None:
    assert tuple(c9.__all__) == PUBLIC_C9_NAMES
    assert tuple(evidence_package.__all__) == PUBLIC_C9_NAMES
    assert len(PUBLIC_C9_NAMES) == len(set(PUBLIC_C9_NAMES))
    for name in PUBLIC_C9_NAMES:
        assert getattr(evidence_package, name) is getattr(c9, name)


def test_evidence_reference_is_strict_and_deterministically_hashed() -> None:
    left = _source()
    right = _source()

    assert left.content_sha256 == right.content_sha256
    assert len(left.content_sha256) == 64
    assert left.as_mapping()["content_sha256"] == left.content_sha256

    changed = C9EvidenceReference(
        source_id=left.source_id,
        locator=left.locator,
        title="Different title",
    )
    assert changed.content_sha256 != left.content_sha256

    for field_name in ("source_id", "locator", "title"):
        kwargs = {
            "source_id": "source",
            "locator": "doi:10.1000/source",
            "title": "title",
        }
        kwargs[field_name] = " "
        with pytest.raises(C9ContractError, match=field_name):
            C9EvidenceReference(**kwargs)


@pytest.mark.parametrize("value", [0.0, -1.0, math.nan, math.inf])
def test_receptor_concentrations_must_be_positive_finite(value: float) -> None:
    with pytest.raises(C9ContractError, match="concentration"):
        ConcentrationResponsePoint(value, "mol/L", 0.5, "fraction")


def test_receptor_evidence_requires_ordered_curve_and_potency_efficacy() -> None:
    duplicate_curve = (
        ConcentrationResponsePoint(1.0e-9, "mol/L", 0.1, "fraction"),
        ConcentrationResponsePoint(1.0e-9, "mol/L", 0.5, "fraction"),
        ConcentrationResponsePoint(1.0e-6, "mol/L", 0.9, "fraction"),
    )
    with pytest.raises(C9ContractError, match="strictly increasing"):
        ReceptorAssayEvidence(
            tested_material="Linalool",
            receptor_identity="OR1A1",
            receptor_species="Homo sapiens",
            cell_system="HEK293",
            concentration_response=duplicate_curve,
            parameters=_assay_parameters(),
            assay_action=AssayAction.AGONIST,
            source=_source(),
            applicability="recorded assay only",
        )

    with pytest.raises(C9ContractError, match="efficacy"):
        ReceptorAssayEvidence(
            tested_material="Linalool",
            receptor_identity="OR1A1",
            receptor_species="Homo sapiens",
            cell_system="HEK293",
            concentration_response=_response_curve(),
            parameters=(_assay_parameters()[0],),
            assay_action=AssayAction.AGONIST,
            source=_source(),
            applicability="recorded assay only",
        )


def test_complete_human_receptor_assay_supports_only_recorded_assay_scope() -> None:
    evidence = _receptor_evidence()
    decision = assess_receptor_claim(ReceptorClaim.RECORDED_HUMAN_ASSAY_RESPONSE, evidence)

    assert decision.status is C9AssessmentStatus.SUPPORTED_NARROW_SCOPE
    assert decision.claim_authorized is True
    assert decision.support_scope is not None
    assert "OR1A1" in decision.support_scope
    assert decision.evidence_sha256 == (evidence.content_sha256,)

    for broad_claim in (
        ReceptorClaim.HUMAN_REPERTOIRE_MODEL,
        ReceptorClaim.PERFUME_PERCEPTION,
    ):
        withheld = assess_receptor_claim(broad_claim, evidence)
        assert withheld.status is C9AssessmentStatus.WITHHELD
        assert withheld.claim_authorized is False
        assert withheld.support_scope is None


def test_receptor_requires_human_species_for_narrow_support() -> None:
    animal = _receptor_evidence(species="Mus musculus")

    decision = assess_receptor_claim(ReceptorClaim.RECORDED_HUMAN_ASSAY_RESPONSE, animal)

    assert decision.status is C9AssessmentStatus.WITHHELD
    assert decision.claim_authorized is False
    assert any("Homo sapiens" in reason for reason in decision.reasons)


def test_tiny_receptor_subset_never_promotes_human_repertoire_or_perception() -> None:
    evidence = _receptor_evidence()

    repertoire = assess_receptor_claim(ReceptorClaim.HUMAN_REPERTOIRE_MODEL, evidence)
    perception = assess_receptor_claim(ReceptorClaim.PERFUME_PERCEPTION, evidence)

    assert repertoire.status is C9AssessmentStatus.WITHHELD
    assert perception.status is C9AssessmentStatus.WITHHELD
    assert all(not decision.claim_authorized for decision in (repertoire, perception))


def test_adaptation_context_requires_every_c9_dimension() -> None:
    for field_name in (
        "species",
        "preparation",
        "nervous_system_level",
        "stimulus_protocol",
    ):
        kwargs: dict[str, object] = {
            "species": "Homo sapiens",
            "preparation": "awake panel",
            "nervous_system_level": "whole person",
            "stimulus_protocol": "fixed pulses",
            "timescale_seconds": 90.0,
        }
        kwargs[field_name] = ""
        with pytest.raises(C9ContractError, match=field_name):
            AdaptationContext(**kwargs)

    with pytest.raises(C9ContractError, match="timescale_seconds"):
        _adaptation_context(timescale_seconds=0.0)


def test_adaptation_requires_exact_context_match() -> None:
    evidence = _adaptation_evidence()
    exact = assess_adaptation_claim(
        AdaptationClaim.RECORDED_CONTEXT_RESPONSE,
        evidence,
        requested_context=evidence.context,
    )
    mismatch = assess_adaptation_claim(
        AdaptationClaim.RECORDED_CONTEXT_RESPONSE,
        evidence,
        requested_context=_adaptation_context(
            stimulus_protocol="continuous 90-second exposure",
        ),
    )

    assert exact.status is C9AssessmentStatus.SUPPORTED_NARROW_SCOPE
    assert exact.claim_authorized is True
    assert mismatch.status is C9AssessmentStatus.WITHHELD
    assert mismatch.claim_authorized is False
    assert any("context" in reason.lower() for reason in mismatch.reasons)


def test_animal_single_cell_adaptation_does_not_transfer_to_human_fine_fragrance() -> None:
    animal_context = AdaptationContext(
        species="Mus musculus",
        preparation="isolated olfactory sensory neuron",
        nervous_system_level="single cell",
        stimulus_protocol="continuous odorant superfusion",
        timescale_seconds=60.0,
    )
    evidence = _adaptation_evidence(context=animal_context)

    decision = assess_adaptation_claim(
        AdaptationClaim.HUMAN_FINE_FRAGRANCE_ADAPTATION,
        evidence,
        requested_context=_adaptation_context(),
    )

    assert decision.status is C9AssessmentStatus.WITHHELD
    assert decision.claim_authorized is False


def test_c9_aging_processes_are_exact_and_separate() -> None:
    assert C9_AGING_PROCESSES == (
        AgingProcess.CHEMICAL_TRANSFORMATION,
        AgingProcess.DISSOLUTION_PHYSICAL_EQUILIBRATION,
        AgingProcess.PRECIPITATION_PHASE_BEHAVIOR,
        AgingProcess.OXIDATION,
        AgingProcess.SENSORY_MATURATION,
    )
    assert len(C9_AGING_PROCESSES) == len(set(C9_AGING_PROCESSES)) == 5

    for process in C9_AGING_PROCESSES:
        evidence = _aging_evidence(process)
        decision = assess_aging_claim(
            AgingClaim.PROCESS_SPECIFIC_CHANGE,
            (evidence,),
            requested_process=process,
        )
        assert decision.status is C9AssessmentStatus.SUPPORTED_NARROW_SCOPE
        assert decision.claim_authorized is True


def test_aging_process_mismatch_is_withheld() -> None:
    oxidation = _aging_evidence(AgingProcess.OXIDATION)

    decision = assess_aging_claim(
        AgingClaim.PROCESS_SPECIFIC_CHANGE,
        (oxidation,),
        requested_process=AgingProcess.PRECIPITATION_PHASE_BEHAVIOR,
    )

    assert decision.status is C9AssessmentStatus.WITHHELD
    assert decision.claim_authorized is False


def test_one_aging_process_never_promotes_universal_shelf_life() -> None:
    evidence = _aging_evidence(AgingProcess.CHEMICAL_TRANSFORMATION)

    for claim in (
        AgingClaim.UNIVERSAL_AGING,
        AgingClaim.SHELF_LIFE,
        AgingClaim.GENERIC_SENSORY_MATURATION,
    ):
        decision = assess_aging_claim(claim, (evidence,))
        assert decision.status is C9AssessmentStatus.WITHHELD
        assert decision.claim_authorized is False
        assert decision.support_scope is None


def test_aging_evidence_rejects_nonphysical_time_and_temperature() -> None:
    for field_name, bad_value in (
        ("temperature_k", 0.0),
        ("temperature_k", math.nan),
        ("duration_days", 0.0),
        ("duration_days", math.inf),
    ):
        kwargs: dict[str, object] = {
            "process": AgingProcess.OXIDATION,
            "subject_identity": "Formula C9",
            "matrix": "ethanol-water",
            "temperature_k": 298.15,
            "duration_days": 28.0,
            "protocol": "sealed vial",
            "endpoint": "peroxide marker",
            "source": _source(),
            "applicability": "recorded lot only",
        }
        kwargs[field_name] = bad_value
        with pytest.raises(C9ContractError, match=field_name):
            AgingEvidence(**kwargs)


def test_unsupported_outcome_vocabulary_is_exact() -> None:
    assert C9_UNSUPPORTED_OUTCOMES == (
        UnsupportedOutcome.LONGEVITY,
        UnsupportedOutcome.SILLAGE,
        UnsupportedOutcome.PROJECTION,
        UnsupportedOutcome.EMOTION,
        UnsupportedOutcome.HEDONIC,
    )
    assert len(C9_UNSUPPORTED_OUTCOMES) == len(set(C9_UNSUPPORTED_OUTCOMES)) == 5


def test_validation_metric_comparators_are_deterministic() -> None:
    upper = ValidationMetric(
        "mae",
        value=0.8,
        threshold=1.0,
        comparator=MetricComparator.LESS_THAN_OR_EQUAL,
    )
    lower = ValidationMetric(
        "correlation",
        value=0.7,
        threshold=0.6,
        comparator=MetricComparator.GREATER_THAN_OR_EQUAL,
    )
    failed = ValidationMetric(
        "mae",
        value=1.2,
        threshold=1.0,
        comparator=MetricComparator.LESS_THAN_OR_EQUAL,
    )

    assert upper.passed is True
    assert lower.passed is True
    assert failed.passed is False


def test_passing_validation_receipt_rejects_failed_metric_or_bad_hash() -> None:
    with pytest.raises(C9ContractError, match="passing metrics"):
        BuildDValidationReceipt(
            outcome=UnsupportedOutcome.SILLAGE,
            model_id="build-d-sillage",
            model_version="1.0.0",
            release_sha256="b" * 64,
            endpoint="radial panel detection",
            scope="test chamber only",
            held_out_dataset_id="held-out-sillage",
            comparator_id="constant-v1",
            metrics=(
                ValidationMetric(
                    "mae",
                    value=1.2,
                    threshold=1.0,
                    comparator=MetricComparator.LESS_THAN_OR_EQUAL,
                ),
            ),
            status=ValidationStatus.PASS,
        )

    with pytest.raises(C9ContractError, match="release_sha256"):
        BuildDValidationReceipt(
            outcome=UnsupportedOutcome.SILLAGE,
            model_id="build-d-sillage",
            model_version="1.0.0",
            release_sha256="not-a-sha",
            endpoint="radial panel detection",
            scope="test chamber only",
            held_out_dataset_id="held-out-sillage",
            comparator_id="constant-v1",
            metrics=(
                ValidationMetric(
                    "mae",
                    value=0.8,
                    threshold=1.0,
                    comparator=MetricComparator.LESS_THAN_OR_EQUAL,
                ),
            ),
            status=ValidationStatus.PASS,
        )


def test_unsupported_outcome_requires_passing_exact_scope_build_d_receipt() -> None:
    scope = "20% EdP on paper blotter at 25 C and 50% RH for 8 hours"
    receipt = _passing_receipt(scope=scope)

    missing = assess_unsupported_outcome(
        UnsupportedOutcome.LONGEVITY,
        receipt=None,
        requested_scope=scope,
    )
    mismatch_outcome = assess_unsupported_outcome(
        UnsupportedOutcome.SILLAGE,
        receipt=receipt,
        requested_scope=scope,
    )
    mismatch_scope = assess_unsupported_outcome(
        UnsupportedOutcome.LONGEVITY,
        receipt=receipt,
        requested_scope="skin at 32 C",
    )
    exact = assess_unsupported_outcome(
        UnsupportedOutcome.LONGEVITY,
        receipt=receipt,
        requested_scope=scope,
    )

    assert missing.status is C9AssessmentStatus.WITHHELD
    assert mismatch_outcome.status is C9AssessmentStatus.WITHHELD
    assert mismatch_scope.status is C9AssessmentStatus.WITHHELD
    assert exact.status is C9AssessmentStatus.SUPPORTED_NARROW_SCOPE
    assert exact.claim_authorized is True
    assert exact.support_scope == scope
    assert exact.evidence_sha256 == (receipt.content_sha256,)


def test_failed_build_d_receipt_never_authorizes_outcome() -> None:
    failed_receipt = BuildDValidationReceipt(
        outcome=UnsupportedOutcome.EMOTION,
        model_id="build-d-emotion",
        model_version="1.0.0",
        release_sha256="c" * 64,
        endpoint="preregistered affect rating",
        scope="recorded panel and protocol only",
        held_out_dataset_id="held-out-affect",
        comparator_id="constant-v1",
        metrics=(
            ValidationMetric(
                "mae",
                value=1.2,
                threshold=1.0,
                comparator=MetricComparator.LESS_THAN_OR_EQUAL,
            ),
        ),
        status=ValidationStatus.FAIL,
    )

    decision = assess_unsupported_outcome(
        UnsupportedOutcome.EMOTION,
        receipt=failed_receipt,
        requested_scope=failed_receipt.scope,
    )

    assert decision.status is C9AssessmentStatus.WITHHELD
    assert decision.claim_authorized is False


def test_claim_decisions_are_answerless_and_canonically_serialized() -> None:
    decision = assess_receptor_claim(
        ReceptorClaim.HUMAN_REPERTOIRE_MODEL,
        _receptor_evidence(),
    )
    payload = decision.as_mapping()

    assert isinstance(decision, C9ClaimDecision)
    assert "value" not in payload
    assert "score" not in payload
    assert "prediction" not in payload
    assert payload["content_sha256"] == decision.content_sha256
    assert decision == C9ClaimDecision.from_mapping(payload)


def test_legacy_surface_registry_is_exact_and_forbids_numeric_authority() -> None:
    expected_ids = (
        "C0-PM-022",
        "C0-PM-023",
        *(f"C0-PM-{index:03d}" for index in range(32, 49)),
    )
    assert C9_LEGACY_SURFACE_IDS == expected_ids
    assert tuple(record.surface_id for record in C9_LEGACY_SURFACES) == expected_ids
    assert len(C9_LEGACY_SURFACES) == len(set(C9_LEGACY_SURFACES)) == 19

    for record in C9_LEGACY_SURFACES:
        assert isinstance(record, C9LegacySurfaceRecord)
        assert record.numeric_claim_authority is False
        assert record.source_paths
        assert get_c9_legacy_surface(record.surface_id) is record

    assert get_c9_legacy_surface("C0-PM-022").disposition is LegacyDisposition.CAPABILITY_BOUNDARY
    assert get_c9_legacy_surface("C0-PM-023").c10_use is C10Use.CAPABILITY_BOUNDARY_ONLY
    assert get_c9_legacy_surface("C0-PM-032").disposition is LegacyDisposition.NARROW_ARITHMETIC_ONLY
    assert get_c9_legacy_surface("C0-PM-032").c10_use is C10Use.CALIBRATED_MODEL_REQUIRED
    assert get_c9_legacy_surface("C0-PM-044").disposition is LegacyDisposition.CANONICAL_ABSTENTION
    assert get_c9_legacy_surface("C0-PM-044").c10_use is C10Use.ABSTENTION_ONLY
    assert get_c9_legacy_surface("C0-PM-047").disposition is LegacyDisposition.QUARANTINED_LEGACY_FIXTURE

    forbidden_ids = set(expected_ids) - {"C0-PM-022", "C0-PM-023", "C0-PM-032", "C0-PM-044"}
    assert all(
        get_c9_legacy_surface(surface_id).c10_use is C10Use.FORBIDDEN_NUMERIC_AUTHORITY
        for surface_id in forbidden_ids
    )

    with pytest.raises(C9ContractError, match="unknown legacy surface"):
        get_c9_legacy_surface("C0-PM-999")


def test_canonical_chemistry_gate_withholds_generic_aging_and_shelf_life() -> None:
    formula = _formula(
        {"Hedione": 2500.0, "Iso E Super": 2500.0, "Habanolide": 1000.0},
        name="Stable Woods Floral",
    )
    report = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0,
            brief="generic",
            audit_enabled=False,
        ),
    )
    chemistry = {gate.gate: gate for gate in report.gates}["chemistry_stability"]

    assert chemistry.status == "PASS"
    assert "shelf_life_days" not in chemistry.data
    assert chemistry.data["aging_claim"]["claim"] == AgingClaim.SHELF_LIFE.value
    assert chemistry.data["aging_claim"]["status"] == C9AssessmentStatus.WITHHELD.value
    assert chemistry.data["aging_claim"]["claim_authorized"] is False
    assert "predicted shelf life" not in chemistry.detail.lower()
    assert "predicted maturation" not in chemistry.detail.lower()
    assert "unknown" in chemistry.detail.lower()


def test_canonical_chemistry_gate_retains_explicit_hazard_screens() -> None:
    reactive_formula = _formula(
        {"Aldehyde C12 MNA": 2000.0, "Indole": 1000.0, "Hedione": 3000.0},
        name="Reactive Jasmine",
    )
    report = gate_formula(
        reactive_formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0,
            brief="generic",
            audit_enabled=False,
        ),
    )
    chemistry = {gate.gate: gate for gate in report.gates}["chemistry_stability"]

    assert chemistry.status == "FAIL"
    assert "Schiff-base risk" in chemistry.detail
    assert chemistry.data["aging_claim"]["status"] == C9AssessmentStatus.WITHHELD.value


def test_pipeline_no_longer_imports_or_calls_generic_shelf_life_predictor() -> None:
    import engine.pipeline.gates as gates_module

    source = inspect.getsource(gates_module)
    chemistry_source = inspect.getsource(gates_module._gate_chemistry_stability)

    assert "predict_shelf_life_days" not in source
    assert "shelf_life_days" not in chemistry_source
    assert "predicted shelf life" not in chemistry_source.lower()
    assert "predicted maturation" not in chemistry_source.lower()


def test_c9_authority_module_has_no_legacy_or_runtime_dependencies() -> None:
    source_path = Path(c9.__file__).resolve()
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden_prefixes = (
        "backend",
        "database",
        "engine.chemistry",
        "engine.diffusion_model",
        "engine.emotional_mapping",
        "engine.hedonic_model",
        "engine.optimizer",
        "engine.pipeline",
        "engine.receptor",
        "engine.skin_interaction",
        "future_modules",
        "os",
        "random",
        "requests",
        "sqlite3",
        "subprocess",
        "time",
        "urllib",
    )
    assert not {
        module
        for module in imported_modules
        if any(module == prefix or module.startswith(prefix + ".") for prefix in forbidden_prefixes)
    }
