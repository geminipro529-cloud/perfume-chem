from __future__ import annotations

from typing import Any, Mapping

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
