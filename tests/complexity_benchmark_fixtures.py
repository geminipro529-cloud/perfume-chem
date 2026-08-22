from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from engine.perception.complexity_benchmark import BenchmarkEvidence, TelemetrySummary
from engine.perception.complexity_ensemble import ComplexityBundle, ComplexityCasePacket
from engine.perception.complexity_xhigh import XHighExecutionReceipt, XHighRequest

INVENTORY_WORKBOOK_SHA256 = (
    "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
)
LOCAL_INVENTORY_SHA256 = (
    "dc3c7ffc6e27711aa38d26bd3aef09b7046f1834353e7171eb78729fbd2cc4ec"
)
USEFUL_COMPLEXITY_DEFINITION = {
    "positive_evidence": [
        "identity-linked facets",
        "coherent perceptual planes, contrasts, and textures",
        "meaningful temporal unfolding",
        "testable hedonic-potential mechanisms",
        "restraint, spacing, dosage control, or negative space",
    ],
    "invalid_proxies": [
        "ingredient count",
        "module count",
        "interaction count",
        "descriptor count",
        "novelty",
        "response length",
        "jargon",
        "technical density",
    ],
    "claim_ceiling": "DESIGN_HYPOTHESIS_NOT_TESTED",
    "musk_policy": {
        "selection_rule": (
            "one exact musk or distinct-role layers; never reward musk count"
        ),
        "exception_only_materials": ["Tonalide", "Macrolide", "Musk Ketone"],
        "exception_fields": [
            "target_tonal_role",
            "why_alternatives_fail",
            "loss_if_omitted",
            "failure_mode",
            "omission_control",
            "alternative_control",
        ],
        "current_depleted_exception_state": "HOLD_PROCUREMENT_REQUIRED",
    },
}

ROOT = Path(__file__).resolve().parents[1]


def valid_case_mapping(
    *,
    relevant_families: tuple[str, ...] = ("construction_profile",),
    module_inputs: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    inputs = module_inputs
    if inputs is None:
        inputs = {
            "construction_profile": {
                "materials": [{"name": "A", "oav": 10.0, "intensity": 2.0}],
                "frames": [
                    {
                        "label": "opening",
                        "t_seconds": 0.0,
                        "materials": [
                            {"name": "A", "oav": 10.0, "intensity": 2.0}
                        ],
                    }
                ],
                "inputs": {},
            }
        }
    return {
        "case_id": "CX-A01",
        "category": "TARGET_ARCHITECTURE",
        "target_name": "Compact Coherent Iris",
        "target_identity": "recognizable iris construction without row-count padding",
        "brief": "Audit architecture and preserve target identity.",
        "inventory_authority_sha256": INVENTORY_WORKBOOK_SHA256,
        "local_inventory_sha256": LOCAL_INVENTORY_SHA256,
        "inventory_reconciliation_state": "MATCH",
        "evidence_refs": ["fixture:cx-a01"],
        "evidence_sha256s": ["a" * 64],
        "relevant_families": list(relevant_families),
        "module_inputs": dict(inputs),
        "expected_invariants": {
            "complexity_definition": USEFUL_COMPLEXITY_DEFINITION,
            "anti_complication_case": True,
            "required_depth_fields": [
                "identity_linked_facets",
                "coherent_richness",
                "temporal_unfolding",
                "restraint_or_subtraction",
                "hedonic_potential_hypotheses",
                "complication_risks",
            ],
            "forbidden_claims": [
                "row count proves quality",
                "more ingredients means more richness",
                "hedonic success is tested",
            ],
        },
        "permitted_claim_ceiling": "COMPUTATIONAL_DESIGN_ONLY",
        "nonce": "CX-A01-0123456789abcdef",
    }


def expansion_payload() -> dict[str, Any]:
    return {
        "registry": {
            "domains": [{"domain_id": "DX-01"}, {"domain_id": "DX-02"}],
            "directions": [
                {
                    "direction_id": "ED-001",
                    "domain_id": "DX-01",
                    "title": "Functional diversity",
                    "origin": "INHERITED_V1",
                    "current_state": "FORMAL MODEL / REGISTRY",
                    "priority": "P0",
                    "evidence_ceiling": "DESIGN",
                    "formula_mutation_authorized": False,
                },
                {
                    "direction_id": "ED-002",
                    "domain_id": "DX-02",
                    "title": "Within sniff pulse order",
                    "origin": "NEW_V2_FRONTIER",
                    "current_state": "MISSING_OR_UNDERFORMALIZED",
                    "priority": "P1",
                    "evidence_ceiling": "DESIGN_ONLY",
                    "mechanism_contract": "Compare matched pulse order.",
                    "first_discriminator": "Counterbalanced order effect.",
                    "failure_mode": "Apparatus artifact.",
                    "formula_mutation_authorized": False,
                },
            ],
        },
        "source_package_sha256": "a" * 64,
        "frontier_values": [
            {"direction_id": "ED-001", "impact": 0.8, "information_gain": 0.8},
            {"direction_id": "ED-002", "impact": 0.6, "information_gain": 0.9},
        ],
        "discovery_rounds": [],
        "declared_scope": "bounded fixture review",
    }


def causal_payload() -> dict[str, Any]:
    invariant_values = {
        "matrix": "d" * 64,
        "environment": "c" * 64,
        "protocol": "e" * 64,
    }
    arms = []
    for character, role, level in (
        ("1", "NULL", "0"),
        ("2", "INTERMEDIATE", "0.5"),
        ("3", "FULL", "1"),
    ):
        arms.append(
            {
                "arm_id": f"arm-{character}",
                "role": role,
                "axis_level": level,
                "formula_sha256": character * 64,
                "dose_receipt_sha256": "f" * 64,
                "supplied_stock_total_ul": "100",
                "active_equivalent_total_ul": "100",
                "carrier_total_ul": "0",
                "invariants": [
                    {"invariant_id": key, "value_sha256": value}
                    for key, value in invariant_values.items()
                ],
            }
        )
    return {
        "operation": "causal_isolate",
        "model_id": "complexity-axis-one",
        "manipulated_axis_id": "module-dose",
        "arms": arms,
        "required_invariant_ids": ["matrix", "environment", "protocol"],
    }


def admission_payload() -> dict[str, Any]:
    return {
        "operation": "model_admission",
        "model_id": "NM-27",
        "version": "2.0.0",
        "claim_scope": "DESIGN",
        "parent_model_ids": ["NM-27-v1"],
        "source_hashes": ["d" * 64],
        "supersession_state": "ADDITIVE",
        "gate_evidence": [
            {
                "gate_id": gate_id,
                "state": "PASS",
                "evidence_links": [],
                "reason": None,
            }
            for gate_id in ("M0", "M1", "M5", "M16")
        ],
        "formula_sha256": None,
        "oav_binding": None,
        "repository_canary_pass": False,
        "no_scalar_compensation": True,
    }


def within_sniff_payload() -> dict[str, Any]:
    return {
        "operation": "within_sniff",
        "sequence_id": "WS-01",
        "formula_sha256": "a" * 64,
        "apparatus_kind": "PULSE_OLFACTOMETER",
        "apparatus_receipt_sha256": "a" * 64,
        "pulses": [
            {
                "channel": "A",
                "onset_ms": "0",
                "duration_ms": "80",
                "delivered_mass": "1",
                "delivered_mass_unit": "mg",
            },
            {
                "channel": "B",
                "onset_ms": "80",
                "duration_ms": "80",
                "delivered_mass": "1",
                "delivered_mass_unit": "mg",
            },
        ],
        "counterbalanced_orders": [["A", "B"], ["B", "A"]],
        "claim_ceiling": "DESIGN_ONLY",
        "matched_total_delivered_mass": True,
        "oav_binding": {
            "formula_sha256": "a" * 64,
            "dose_receipt_sha256": "b" * 64,
            "oav_result_sha256": "c" * 64,
            "quantitative_ppm_status": "PASS",
            "odt_authority_status": "PASS",
            "odt_coverage_status": "PASS",
            "natural_composite_coverage_status": "PASS",
            "headspace_scope_status": "PASS",
            "receipt_binding_status": "BOUND_GATE_RECEIPT",
            "strict_oav_status": "ABSTAINED",
            "pre_mix_gate_status": "PASS",
            "planned_active_equivalence_status": "NOT_APPLICABLE_NEW_FORMULA",
            "formula_is_revision": False,
            "parent_formula_sha256": None,
            "oav_per_time_role": "SCREENING_ONLY",
        },
        "apparatus_qualified": False,
        "delivered_mass_receipt_sha256": None,
        "evidence_links": [],
    }


def musk_payload(
    *,
    material: str = "Zenolide",
    exception_call: Mapping[str, Any] | None = None,
    inventory_state: str = "OWNED",
) -> dict[str, Any]:
    return {
        "target_identity": "quiet skin aura with negative space",
        "target_brief": None,
        "candidates": [
            {
                "material": material,
                "role": "DEPTH",
                "target_function": "one exact skin-depth plane without laundry bloom",
                "why_nonredundant": "the architecture has no other musk plane",
                "inventory_state": inventory_state,
                "exact_stock_ref": (
                    "inventory:Zenolide:neat" if inventory_state == "OWNED" else None
                ),
                "exception": dict(exception_call) if exception_call is not None else None,
                "fingerprint": None,
            }
        ],
        "pairwise_nonredundancy": [],
    }


def valid_bundle(case: ComplexityCasePacket) -> ComplexityBundle:
    output = {"axes": {"formula_structure": {"status": "AVAILABLE"}}}
    return ComplexityBundle(
        case_id=case.case_id,
        state="PASS",
        case_input_sha256=case.input_sha256,
        registry_sha256="b" * 64,
        omitted_families=(),
        family_outputs={"construction_profile": output},
        module_runs=(),
        blockers=(),
    )


def valid_execution_receipt(
    request: XHighRequest,
    *,
    response_bytes: bytes = b'{"ok":true}',
) -> XHighExecutionReceipt:
    return XHighExecutionReceipt(
        request_id=request.request_id,
        nonce=request.nonce,
        provider="OpenAI",
        product="ChatGPT",
        model_identity="ChatGPT-current",
        reasoning_effort="xhigh",
        context_clean=True,
        prior_case_transcript_visible=False,
        prompt_sha256=request.prompt_sha256,
        attachment_sha256s=request.attachment_sha256s,
        submitted_at="2026-08-22T10:00:00Z",
        completed_at="2026-08-22T10:01:00Z",
        completion_state="SUCCEEDED",
        conversation_id="chatgpt:test-cx-a01-control",
        response_sha256=hashlib.sha256(response_bytes).hexdigest(),
        input_tokens=1000,
        output_tokens=500,
        latency_ms=60000,
        price_usd=Decimal("1.00"),
    )


def case_by_id(case_id: str) -> ComplexityCasePacket:
    payload = json.loads(
        (ROOT / "tests/fixtures/complexity_xhigh_cases_v1.json").read_text(
            encoding="utf-8"
        )
    )
    raw = dict(next(item for item in payload["cases"] if item["case_id"] == case_id))
    refs = raw.pop("module_input_refs")
    raw["module_inputs"] = {
        family: payload["shared_module_inputs"][reference]
        for family, reference in refs.items()
    }
    expected = dict(raw["expected_invariants"])
    definition_ref = expected.pop("complexity_definition_ref")
    response_ref = expected.pop("valid_response_ref")
    expected["complexity_definition"] = payload["shared_invariants"][
        definition_ref
    ]
    expected["valid_response"] = payload["rubric"][response_ref]
    for key in (
        "required_depth_fields",
        "required_claim_states",
        "forbidden_claims",
        "required_sections",
    ):
        expected[key] = payload["shared_invariants"][key]
    raw["expected_invariants"] = expected
    return ComplexityCasePacket.from_mapping(raw)


def valid_response(case: ComplexityCasePacket) -> dict[str, Any]:
    evidence_ref = case.evidence_refs[0]
    return {
        "target_identity": {
            "identity": case.target_identity,
            "preserved": True,
            "evidence_refs": [evidence_ref],
        },
        "functional_architecture": {
            "roles": [
                {
                    "function": "recognition and identity continuity",
                    "target_link": case.target_identity,
                }
            ],
            "temporal_handoffs": ["opening to residue remains target-linked"],
            "failure_boundaries": ["avoid redundancy, mud, and decorative padding"],
            "evidence_refs": [evidence_ref],
        },
        "depth_and_richness_analysis": {
            "identity_linked_facets": [
                {
                    "facet": "recognition plane",
                    "target_link": case.target_identity,
                    "evidence_refs": [evidence_ref],
                }
            ],
            "coherent_richness": {
                "claim": "Depth comes from coherent contrast tied to the target.",
                "target_linked_contrast": "recognition versus controlled residue",
                "evidence_refs": [evidence_ref],
            },
            "temporal_unfolding": {
                "claim": "Opening and residue are assessed as distinct handoff planes.",
                "evidence_refs": [evidence_ref],
            },
            "restraint_or_subtraction": {
                "action": "remove any support that fails an omission comparison",
                "evidence_refs": [evidence_ref],
            },
            "hedonic_potential_hypotheses": [
                {
                    "state": "DESIGN_HYPOTHESIS_NOT_TESTED",
                    "target_linked_mechanism": (
                        "cleaner target recognition may improve hedonic potential"
                    ),
                    "controlled_sensory_comparison": (
                        "blind matched-dose full design versus one-at-a-time omission"
                    ),
                    "evidence_refs": [evidence_ref],
                }
            ],
            "complication_risks": [
                {
                    "risk": "redundancy or mud can reduce legibility",
                    "control": "strongest-single and omission controls",
                }
            ],
        },
        "target_ideal_formula": {
            "state": "COMPUTATIONAL_DESIGN_ONLY",
            "materials": ["IDEAL_DESIGN_PLACEHOLDER"],
            "inventory_independent": True,
        },
        "current_inventory_build": {
            "state": "NOT_PHYSICALLY_COMPOUNDED",
            "materials": ["CURRENT_BUILD_PLACEHOLDER"],
            "exact_stock_refs": [],
        },
        "missing_chemical_impact": {
            "strongly_covered": ["target recognition"],
            "weakly_covered": [],
            "genuinely_missing": [],
            "candidate_status": "EVIDENCE_GAP_NOT_INVENTORY_GAP",
            "controlled_comparison": "matched-dose omission versus full design",
        },
        "controlled_test_plan": {
            "isolation": "change one target-linked function at a time",
            "controls": ["full design", "omission", "strongest current alternative"],
            "dose_time_substrate": "matched dose, fixed timepoints, fixed substrate",
            "blinding": "randomized blinded labels",
            "endpoints": ["target recognition", "mud", "preference"],
            "decision_rule": "retain only a repeatable target-linked gain",
        },
        "claims": [
            {
                "claim": "The architecture is a design hypothesis.",
                "state": "DESIGN_HYPOTHESIS_NOT_TESTED",
                "evidence_refs": [evidence_ref],
                "authority_ceiling": case.permitted_claim_ceiling,
            },
            {
                "claim": "Physical liking and similarity remain untested.",
                "state": "NOT_TESTED",
                "evidence_refs": [evidence_ref],
                "authority_ceiling": case.permitted_claim_ceiling,
            },
            {
                "claim": "Any unresolved source or stock issue remains held.",
                "state": "HOLD",
                "evidence_refs": [evidence_ref],
                "authority_ceiling": case.permitted_claim_ceiling,
            },
        ],
        "conflicts_and_holds": [
            {
                "issue": "No silent conflict resolution or stock promotion.",
                "state": "HOLD_IF_UNRESOLVED",
                "next_action": "verify exact source or stock bytes",
            }
        ],
        "answer_markdown": (
            "Preserve the target, keep ideal and current build separate, and test "
            "the smallest discriminating change. Physical liking remains NOT TESTED."
        ),
    }


def benchmark_evidence(
    *,
    wins: int,
    median_delta: int,
    new_critical: int = 0,
    category_regression: int = 0,
) -> BenchmarkEvidence:
    return BenchmarkEvidence(
        pair_count=16,
        treatment_wins=wins,
        median_delta=Decimal(median_delta),
        new_treatment_critical_failures=new_critical,
        category_median_deltas={
            "TARGET_ARCHITECTURE": Decimal(-category_regression),
            "RECONSTRUCTION_REVISION": Decimal("5"),
            "MISSING_CHEMICAL_IMPACT": Decimal("5"),
            "EXPERIMENTAL_EVIDENCE_DESIGN": Decimal("5"),
        },
        receipts_valid=True,
    )


def telemetry_summary(
    *,
    state: str = "EXPOSED",
    treatment_price: str = "1.50",
) -> TelemetrySummary:
    if state != "EXPOSED":
        return TelemetrySummary(
            state=state,
            median_control_price_usd=None,
            median_treatment_price_usd=None,
        )
    return TelemetrySummary(
        state="EXPOSED",
        median_control_price_usd=Decimal("1.00"),
        median_treatment_price_usd=Decimal(treatment_price),
    )
