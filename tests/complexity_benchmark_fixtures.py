from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Any, Mapping

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
