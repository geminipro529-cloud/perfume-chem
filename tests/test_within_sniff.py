from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from engine.scientific_validation.complexity_model_admission import OAVGateBinding
from engine.sensory.within_sniff import (
    DeliveryApparatusKind,
    WithinSniffClaimCeiling,
    WithinSniffPulse,
    WithinSniffSequence,
    WithinSniffState,
    evaluate_within_sniff_sequence,
)

SHA_A = "a" * 64


def _oav_binding(*, strict: str = "ABSTAINED", composite: str = "PASS") -> OAVGateBinding:
    return OAVGateBinding(
        formula_sha256=SHA_A,
        dose_receipt_sha256="b" * 64,
        oav_result_sha256="c" * 64,
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


def _sequence(
    *,
    claim: WithinSniffClaimCeiling = WithinSniffClaimCeiling.DESIGN_ONLY,
    apparatus: DeliveryApparatusKind = DeliveryApparatusKind.PULSE_OLFACTOMETER,
) -> WithinSniffSequence:
    observed = claim is WithinSniffClaimCeiling.OBSERVED_WITHIN_APPARATUS_SCOPE
    return WithinSniffSequence(
        sequence_id="WS-01",
        formula_sha256=SHA_A,
        apparatus_kind=apparatus,
        apparatus_receipt_sha256="a" * 64,
        pulses=(
            WithinSniffPulse("A", Decimal("0"), Decimal("80"), Decimal("1"), "mg"),
            WithinSniffPulse("B", Decimal("80"), Decimal("80"), Decimal("1"), "mg"),
        ),
        counterbalanced_orders=(("A", "B"), ("B", "A")),
        claim_ceiling=claim,
        matched_total_delivered_mass=True,
        oav_binding=_oav_binding(strict="COMPUTED" if observed else "ABSTAINED"),
        apparatus_qualified=observed,
        delivered_mass_receipt_sha256="c" * 64 if observed else None,
        evidence_links=("evidence://within-sniff",) if observed else (),
    )


def test_design_sequence_requires_oav_gate_but_creates_no_authority() -> None:
    result = evaluate_within_sniff_sequence(_sequence())
    assert result.state is WithinSniffState.PASS_FOR_DESIGN
    assert result.physical_execution_authorized is False
    assert result.sensory_authority is False
    assert result.release_authority is False


def test_failed_oav_gate_rebuilds_sequence() -> None:
    result = evaluate_within_sniff_sequence(
        replace(_sequence(), oav_binding=_oav_binding(composite="FAIL"))
    )
    assert result.state is WithinSniffState.REBUILD
    assert any("OAV" in item for item in result.failures)


def test_observed_scope_requires_strict_oav_and_qualified_delivery() -> None:
    passing = evaluate_within_sniff_sequence(
        _sequence(claim=WithinSniffClaimCeiling.OBSERVED_WITHIN_APPARATUS_SCOPE)
    )
    assert passing.state is WithinSniffState.CONDITIONAL_EMPIRICAL
    assert passing.sensory_authority is False

    held = evaluate_within_sniff_sequence(
        replace(
            _sequence(claim=WithinSniffClaimCeiling.OBSERVED_WITHIN_APPARATUS_SCOPE),
            oav_binding=_oav_binding(strict="ABSTAINED"),
        )
    )
    assert held.state is WithinSniffState.REBUILD


def test_static_blotter_cannot_be_relabelled_within_sniff() -> None:
    result = evaluate_within_sniff_sequence(
        _sequence(apparatus=DeliveryApparatusKind.STATIC_BLOTTER)
    )
    assert result.state is WithinSniffState.REBUILD
    assert any("static blotter" in item for item in result.failures)
