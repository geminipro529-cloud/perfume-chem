from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from engine.pipeline.preflight import FormulaDoseLineReceipt, FormulaDoseReceipt
from engine.scientific_validation.complexity_design_contracts import (
    CausalArmRole,
    CausalInvariant,
    CausalIsolateArm,
    CausalIsolateDesign,
    CausalIsolateState,
    FormulaSignature,
    FormulaSignatureComponent,
    NaryAssessmentState,
    NaryEvidenceState,
    NaryInteractionCandidate,
    NaryParticipant,
    SignatureComparisonState,
    compare_formula_signatures,
    evaluate_causal_isolate,
    evaluate_nary_interaction,
)
from engine.scientific_validation.complexity_model_admission import OAVGateBinding


def _hash(character: str) -> str:
    return character * 64


def _line(name: str, raw_ul: float, fraction: float, row: int) -> FormulaDoseLineReceipt:
    return FormulaDoseLineReceipt(
        material_name=name,
        raw_ul=raw_ul,
        active_ul=raw_ul * fraction,
        stock_fraction=fraction,
        fraction_basis="volume_fraction",
        carrier="DPG" if fraction < 1 else "",
        stock_id=f"stock-{row}",
        stock_authority="formula_row+inventory_snapshot",
        inventory_authority="inventory-v5",
        source_rows=(row,),
        status="BOUND",
    )


def _receipt(character: str, *lines: FormulaDoseLineReceipt) -> FormulaDoseReceipt:
    return FormulaDoseReceipt(
        formula_name=f"formula-{character}",
        formula_input_sha256=_hash(character),
        legacy_formula_hash=_hash(character),
        inventory_snapshot_sha256=_hash("a"),
        inventory_source_workbook_sha256=_hash("b"),
        inventory_authority_sheet="Current Inventory Master",
        lines=lines,
        status="BOUND",
        reasons=(),
    )


def _invariants(*, environment: str = "c") -> tuple[CausalInvariant, ...]:
    return (
        CausalInvariant("matrix", _hash("d")),
        CausalInvariant("environment", _hash(environment)),
        CausalInvariant("protocol", _hash("e")),
    )


def _arm(
    character: str,
    role: CausalArmRole,
    level: str,
    *,
    environment: str = "c",
    active_fraction: float = 1.0,
) -> CausalIsolateArm:
    receipt = _receipt(
        character,
        _line(f"material-{character}", 100.0 / active_fraction, active_fraction, 1),
    )
    return CausalIsolateArm.from_dose_receipt(
        arm_id=f"arm-{character}",
        role=role,
        axis_level=Decimal(level),
        receipt=receipt,
        invariants=_invariants(environment=environment),
    )


def _design(*arms: CausalIsolateArm) -> CausalIsolateDesign:
    return CausalIsolateDesign(
        model_id="complexity-axis-one",
        manipulated_axis_id="module-dose",
        arms=arms,
        required_invariant_ids=("matrix", "environment", "protocol"),
    )


def _oav_binding(formula_sha256: str) -> OAVGateBinding:
    return OAVGateBinding(
        formula_sha256=formula_sha256,
        dose_receipt_sha256=_hash("b"),
        oav_result_sha256=_hash("c"),
        quantitative_ppm_status="PASS",
        odt_authority_status="PASS",
        odt_coverage_status="PASS",
        natural_composite_coverage_status="PASS",
        headspace_scope_status="PASS",
        receipt_binding_status="BOUND_GATE_RECEIPT",
        strict_oav_status="NOT_TESTED",
        pre_mix_gate_status="PASS",
        planned_active_equivalence_status="PASS",
        formula_is_revision=False,
    )


def _participants() -> tuple[NaryParticipant, ...]:
    return (
        NaryParticipant("rose", "foreground", Decimal("0.5")),
        NaryParticipant("jasmine", "bridge", Decimal("0.3")),
        NaryParticipant("musk", "support", Decimal("0.2")),
    )


def _candidate(
    evidence_state: NaryEvidenceState,
    **overrides: object,
) -> NaryInteractionCandidate:
    values = {
        "interaction_id": "nary-floral-heart-one",
        "evidence_state": evidence_state,
        "participants": _participants(),
        "formula_sha256": _hash("1"),
        "formula_signature_sha256": _hash("2"),
        "matrix_sha256": _hash("3"),
        "pairwise_evidence_refs": ("PAIR-1", "PAIR-2"),
    }
    values.update(overrides)
    return NaryInteractionCandidate(**values)  # type: ignore[arg-type]


def test_causal_isolate_accepts_exact_null_full_design_without_authority() -> None:
    result = evaluate_causal_isolate(
        _design(
            _arm("1", CausalArmRole.NULL, "0"),
            _arm("2", CausalArmRole.INTERMEDIATE, "0.5"),
            _arm("3", CausalArmRole.FULL, "1"),
        )
    )

    assert result.state is CausalIsolateState.DESIGN_READY
    assert result.blockers == ()
    assert result.empirical_authority is False
    assert result.formula_mutation_authorized is False
    assert result.physical_execution_authorized is False
    assert result.release_authority is False


@pytest.mark.parametrize(
    ("arms", "message"),
    [
        (
            (
                _arm("1", CausalArmRole.INTERMEDIATE, "0.5"),
                _arm("2", CausalArmRole.FULL, "1"),
            ),
            "exactly one NULL arm",
        ),
        (
            (
                _arm("1", CausalArmRole.NULL, "0"),
                _arm("2", CausalArmRole.FULL, "1", active_fraction=0.5),
            ),
            "supplied stock total",
        ),
        (
            (
                _arm("1", CausalArmRole.NULL, "0"),
                _arm("2", CausalArmRole.FULL, "1", environment="f"),
            ),
            "environment differs",
        ),
    ],
)
def test_causal_isolate_rebuilds_on_missing_or_drifting_controls(
    arms: tuple[CausalIsolateArm, ...],
    message: str,
) -> None:
    result = evaluate_causal_isolate(_design(*arms))

    assert result.state is CausalIsolateState.REBUILD
    assert any(message in blocker for blocker in result.blockers)


def test_formula_signature_projects_canonical_dose_receipt_without_mass_claim() -> None:
    receipt = _receipt(
        "4",
        _line("rose", 20, 0.1, 1),
        _line("jasmine", 30, 1.0, 2),
    )
    signature = FormulaSignature.from_dose_receipt(
        receipt,
        sensory_system_ids={"rose": ("floral",), "jasmine": ("floral", "diffusive")},
        recognizer_ids={"rose": ("rose-heart",), "jasmine": ("white-floral",)},
        phase_ids={"rose": ("heart",), "jasmine": ("heart",)},
    )

    assert signature.quantity_basis == "PLANNED_VOLUME_UL"
    assert signature.formula_sha256 == receipt.legacy_formula_hash
    assert signature.dose_receipt_sha256 == receipt.receipt_sha256
    assert signature.formula_authority is False
    assert signature.sensory_similarity_authority is False
    assert signature.release_authority is False


def test_formula_signature_keeps_all_views_separate_and_threshold_free() -> None:
    left = FormulaSignature(
        formula_sha256=_hash("1"),
        dose_receipt_sha256=_hash("2"),
        quantity_basis="PLANNED_VOLUME_UL",
        components=(
            FormulaSignatureComponent(
                "rose",
                Decimal("50"),
                Decimal("5"),
                ("floral",),
                ("rose-heart",),
                ("heart",),
            ),
            FormulaSignatureComponent(
                "musk",
                Decimal("50"),
                Decimal("50"),
                ("diffusion",),
                ("musk-base",),
                ("base",),
            ),
        ),
    )
    right = FormulaSignature(
        formula_sha256=_hash("3"),
        dose_receipt_sha256=_hash("4"),
        quantity_basis="PLANNED_VOLUME_UL",
        components=(
            FormulaSignatureComponent(
                "rose",
                Decimal("25"),
                Decimal("2.5"),
                ("floral",),
                ("rose-heart",),
                ("heart",),
            ),
            FormulaSignatureComponent(
                "wood",
                Decimal("75"),
                Decimal("75"),
                ("structure",),
                ("wood-base",),
                ("base",),
            ),
        ),
    )

    result = compare_formula_signatures(left, right)

    assert result.state is SignatureComparisonState.COMPLETE_DIAGNOSTIC
    assert result.material_overlap_jaccard == Decimal("1") / Decimal("3")
    assert result.active_equivalent_cosine is not None
    assert result.sensory_system_overlap_jaccard == Decimal("1") / Decimal("3")
    assert result.threshold_applied is False
    assert result.sensory_similarity_authority is False
    assert result.portfolio_nonredundancy_authority is False
    assert result.release_authority is False


def test_formula_signature_abstains_only_from_unbound_views() -> None:
    component = FormulaSignatureComponent("rose", Decimal("10"), None)
    left = FormulaSignature(_hash("1"), _hash("2"), "PLANNED_VOLUME_UL", (component,))
    right = FormulaSignature(_hash("3"), _hash("4"), "PLANNED_VOLUME_UL", (component,))

    result = compare_formula_signatures(left, right)

    assert result.state is SignatureComparisonState.PARTIAL_ABSTENTION
    assert result.material_overlap_jaccard == Decimal("1")
    assert result.supplied_stock_cosine == Decimal("1")
    assert result.active_equivalent_cosine is None
    assert len(result.abstentions) == 4


def test_nary_ratios_must_sum_exactly_to_one() -> None:
    with pytest.raises(ValueError, match="sum exactly to one"):
        _candidate(
            NaryEvidenceState.HYPOTHESIS,
            participants=(
                NaryParticipant("a", "one", Decimal("0.4")),
                NaryParticipant("b", "two", Decimal("0.3")),
                NaryParticipant("c", "three", Decimal("0.2")),
            ),
        )


def test_nary_hypothesis_keeps_pair_records_nonempirical() -> None:
    result = evaluate_nary_interaction(_candidate(NaryEvidenceState.HYPOTHESIS))

    assert result.state is NaryAssessmentState.HYPOTHESIS_ONLY
    assert result.blockers == ()
    assert result.pairwise_promotion_blocked is True
    assert result.sensory_authority is False
    assert result.empirical_model_authority is False
    assert result.release_authority is False


def test_nary_design_requires_causal_and_formula_oav_bindings() -> None:
    result = evaluate_nary_interaction(_candidate(NaryEvidenceState.EXPERIMENT_DESIGN))

    assert result.state is NaryAssessmentState.HOLD
    assert "a causal-isolate design hash is required" in result.blockers
    assert "a formula-bound OAV screening receipt is required" in result.blockers


def test_nary_design_can_be_ready_but_never_empirically_authoritative() -> None:
    result = evaluate_nary_interaction(
        _candidate(
            NaryEvidenceState.EXPERIMENT_DESIGN,
            causal_isolate_sha256=_hash("4"),
            experiment_design_sha256=_hash("5"),
            oav_binding=_oav_binding(_hash("1")),
        )
    )

    assert result.state is NaryAssessmentState.DESIGN_READY
    assert result.blockers == ()
    assert result.empirical_model_authority is False
    assert result.formula_mutation_authorized is False


def test_nary_observed_scope_needs_execution_and_performed_observations() -> None:
    design = _candidate(
        NaryEvidenceState.OBSERVED_SCOPE,
        causal_isolate_sha256=_hash("4"),
        experiment_design_sha256=_hash("5"),
        oav_binding=_oav_binding(_hash("1")),
    )
    held = evaluate_nary_interaction(design)
    accepted = evaluate_nary_interaction(
        replace(
            design,
            experiment_execution_sha256=_hash("6"),
            observation_receipt_sha256s=(_hash("7"), _hash("8")),
        )
    )

    assert held.state is NaryAssessmentState.HOLD
    assert any("execution receipt" in blocker for blocker in held.blockers)
    assert any("performed observation" in blocker for blocker in held.blockers)
    assert accepted.state is NaryAssessmentState.OBSERVATION_SCOPE_CANDIDATE
    assert accepted.empirical_model_authority is False
    assert accepted.sensory_authority is False
    assert accepted.release_authority is False


def test_nary_observed_scope_rejects_mismatched_formula_oav_binding() -> None:
    result = evaluate_nary_interaction(
        _candidate(
            NaryEvidenceState.OBSERVED_SCOPE,
            causal_isolate_sha256=_hash("4"),
            experiment_design_sha256=_hash("5"),
            experiment_execution_sha256=_hash("6"),
            observation_receipt_sha256s=(_hash("7"),),
            oav_binding=_oav_binding(_hash("9")),
        )
    )

    assert result.state is NaryAssessmentState.HOLD
    assert "OAV binding formula hash does not match the candidate" in result.blockers
