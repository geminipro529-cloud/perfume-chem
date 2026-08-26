from __future__ import annotations

from dataclasses import replace

import pytest

from engine.calibration.hashing import stable_formula_hash
from engine.fuckups.pre_mix_guard import evaluate_pre_mix_guard
from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority
from engine.pipeline.preflight import PreflightCheck, PreflightReport
from engine.scientific_validation.complexity_model_admission import (
    ComplexityAdmissionState,
    ComplexityClaimScope,
    ComplexityGateEvidence,
    ComplexityGateState,
    ComplexityModelAdmissionPacket,
    OAVGateBinding,
    evaluate_complexity_model_admission,
    required_complexity_gates,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


def _gates(scope: ComplexityClaimScope) -> tuple[ComplexityGateEvidence, ...]:
    links = () if scope is ComplexityClaimScope.DESIGN else ("evidence://receipt",)
    return tuple(
        ComplexityGateEvidence(
            gate_id=gate_id,
            state=ComplexityGateState.PASS,
            evidence_links=links,
        )
        for gate_id in sorted(required_complexity_gates(scope), key=lambda value: int(value[1:]))
    )


def _oav_binding(*, strict: str = "ABSTAINED", composite: str = "PASS") -> OAVGateBinding:
    return OAVGateBinding(
        formula_sha256=SHA_A,
        dose_receipt_sha256=SHA_B,
        oav_result_sha256=SHA_C,
        quantitative_ppm_status="PASS",
        odt_authority_status="PASS",
        odt_coverage_status="PASS",
        natural_composite_coverage_status=composite,
        headspace_scope_status="PASS",
        receipt_binding_status="BOUND_GATE_RECEIPT",
        strict_oav_status=strict,
        pre_mix_gate_status="PASS",
        planned_active_equivalence_status="NOT_APPLICABLE_NEW_FORMULA",
        formula_is_revision=False,
    )


def _packet(
    scope: ComplexityClaimScope,
    *,
    formula: bool = True,
    binding: OAVGateBinding | None = None,
) -> ComplexityModelAdmissionPacket:
    return ComplexityModelAdmissionPacket(
        model_id="NM-27",
        version="2.0.0",
        claim_scope=scope,
        parent_model_ids=("NM-27-v1",),
        source_hashes=(SHA_D,),
        supersession_state="ADDITIVE",
        gate_evidence=_gates(scope),
        formula_sha256=SHA_A if formula else None,
        oav_binding=binding if formula else None,
        repository_canary_pass=False,
    )


def test_non_formula_design_can_be_registry_admitted_without_oav_claim() -> None:
    result = evaluate_complexity_model_admission(
        _packet(ComplexityClaimScope.DESIGN, formula=False)
    )
    assert result.state is ComplexityAdmissionState.DESIGN_REGISTRY_ADMITTED
    assert result.oav_gate_state == "NOT_APPLICABLE_NO_FORMULA"
    assert result.release_authority is False


def test_formula_design_is_blocked_when_composite_natural_oav_fails() -> None:
    result = evaluate_complexity_model_admission(
        _packet(
            ComplexityClaimScope.DESIGN,
            binding=_oav_binding(composite="FAIL"),
        )
    )
    assert result.state is ComplexityAdmissionState.HOLD
    assert any("natural_composite" in item for item in result.oav_blockers)


def test_empirical_candidate_requires_screening_oav_but_not_strict_air() -> None:
    result = evaluate_complexity_model_admission(
        _packet(ComplexityClaimScope.EMPIRICAL_MECHANISM, binding=_oav_binding())
    )
    assert result.state is ComplexityAdmissionState.EMPIRICAL_SCOPE_CANDIDATE
    assert result.oav_gate_state == "PASS"
    assert result.physical_execution_authorized is False


def test_analytical_candidate_requires_strict_receipt_bound_oav() -> None:
    held = evaluate_complexity_model_admission(
        _packet(ComplexityClaimScope.ANALYTICAL, binding=_oav_binding())
    )
    assert held.state is ComplexityAdmissionState.HOLD
    assert any("strict_oav_status" in item for item in held.oav_blockers)

    computed = evaluate_complexity_model_admission(
        _packet(
            ComplexityClaimScope.ANALYTICAL,
            binding=_oav_binding(strict="COMPUTED"),
        )
    )
    assert computed.state is ComplexityAdmissionState.ANALYTICAL_SCOPE_CANDIDATE
    assert computed.release_authority is False


def test_revision_oav_binding_requires_immediate_parent_and_active_equivalence() -> None:
    with pytest.raises(ValueError, match="immediate parent"):
        replace(
            _oav_binding(),
            formula_is_revision=True,
            planned_active_equivalence_status="PASS",
        )

    binding = replace(
        _oav_binding(),
        formula_is_revision=True,
        parent_formula_sha256=SHA_D,
        planned_active_equivalence_status="WITHHELD",
    )
    result = evaluate_complexity_model_admission(
        _packet(ComplexityClaimScope.DESIGN, binding=binding)
    )
    assert result.state is ComplexityAdmissionState.HOLD
    assert any("active_equivalence" in item for item in result.oav_blockers)


def test_native_gate_objects_bind_directly_and_preserve_current_holds() -> None:
    formula = {
        "number": 1,
        "name": "Complexity OAV Binding Canary",
        "ingredients_ul": {"Javanol": 14.0},
        "dilutions": {"Javanol": 0.2},
    }
    gate = gate_formula(formula, ReleaseGateConfig(audit_enabled=False))
    oav_result = analyze_oav_authority(
        OAVAuthorityRequest(
            formula_name=formula["name"],
            ingredients_ul=formula["ingredients_ul"],
            dilutions=formula["dilutions"],
            dose_receipt_sha256=gate.dose_receipt.receipt_sha256,
        ),
        gate_report=gate,
    )
    preflight = PreflightReport(
        status=gate.preflight["status"],
        checks=tuple(
            PreflightCheck(
                name=item["check_name"],
                status=item["status"],
                detail=item["detail"],
                data=item.get("data", {}),
            )
            for item in gate.preflight["checks"]
        ),
        confidence_penalty=gate.preflight["confidence_penalty"],
        warnings=tuple(gate.preflight["warnings"]),
    )
    pre_mix = evaluate_pre_mix_guard(
        child_ingredients_ul=formula["ingredients_ul"],
        child_dilutions=formula["dilutions"],
    )
    formula_sha256 = stable_formula_hash(
        formula["name"], formula["ingredients_ul"], formula["dilutions"]
    )
    with pytest.raises(ValueError, match="exact formula analyzed"):
        OAVGateBinding.from_native_results(
            formula_sha256=SHA_A,
            oav_result=oav_result,
            preflight_report=preflight,
            pre_mix_report=pre_mix,
            planned_active_equivalence_status="NOT_APPLICABLE_NEW_FORMULA",
            formula_is_revision=False,
        )
    binding = OAVGateBinding.from_native_results(
        formula_sha256=formula_sha256,
        oav_result=oav_result,
        preflight_report=preflight,
        pre_mix_report=pre_mix,
        planned_active_equivalence_status="NOT_APPLICABLE_NEW_FORMULA",
        formula_is_revision=False,
    )
    assert binding.receipt_binding_status == "BOUND_GATE_RECEIPT"
    assert binding.strict_oav_status == "ABSTAINED"
    assert binding.odt_authority_status == "WARN"
    assert binding.screening_blockers
    result = evaluate_complexity_model_admission(
        replace(
            _packet(ComplexityClaimScope.DESIGN, binding=binding),
            formula_sha256=formula_sha256,
        )
    )
    assert result.state is ComplexityAdmissionState.HOLD
    assert result.release_authority is False
