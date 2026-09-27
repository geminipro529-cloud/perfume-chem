"""Read-only Checkpoint 19 boundary report for the three Lavande comparators.

This checkpoint-specific adapter intentionally lives outside the generic
research runtime.  It proves formula/source differences and current coverage;
it cannot fabricate a release scenario, model applicability, sensory result,
or ranking.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from engine.research.accounting import account_formula_snapshot
from engine.research.comparison import project_completion_states
from engine.research.contracts import FALSE_ACTION_AUTHORITY, stable_payload_hash
from engine.research.snapshots import (
    load_parallel_a_design_snapshot,
    load_r5_design_snapshot,
    load_r6_design_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "inventory.txt"
CAPABILITY_SUMMARY = (
    ROOT
    / "data"
    / "governance"
    / "wakayama_identity_adjudication_summary_20260927.json"
)


def _file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def evaluate_checkpoint19_comparison_boundary() -> dict[str, Any]:
    """Return the strongest current three-design comparison without overclaiming."""

    loads = (
        load_r5_design_snapshot(),
        load_r6_design_snapshot(),
        load_parallel_a_design_snapshot(),
    )
    inventory_hash = _file_hash(INVENTORY)
    capability_hash = _file_hash(CAPABILITY_SUMMARY)
    comparators: list[dict[str, Any]] = []
    unavailable_endpoints = (
        "DELIVERED_GAS_CONCENTRATION",
        "DETECTION_DIAGNOSTIC",
        "INTENSITY",
        "CHARACTER",
        "POPULATION_PLEASANTNESS",
        "PERSONAL_LIKING",
    )
    for loaded in loads:
        accounting = account_formula_snapshot(
            loaded.snapshot,
            products=(),
            stocks=(),
        )
        comparators.append(
            {
                "comparator_id": loaded.snapshot.formula_id,
                "formula_name": loaded.snapshot.formula_name,
                "formula_sha256": loaded.snapshot.sha256,
                "source_sha256": loaded.source_sha256,
                "inventory_sha256": inventory_hash,
                "capability_bundle_sha256": capability_hash,
                "release_scenario_sha256": None,
                "physical_totals": {
                    "liquid_total_uL": loaded.liquid_total_ul_decimal,
                    "solid_total_mg": loaded.solid_total_mg_decimal,
                },
                "active_accounting": accounting,
                "release_coverage_decimal": "0",
                "endpoint_results": [
                    {
                        "endpoint": endpoint,
                        "value": None,
                        "units": None,
                        "coverage": "0",
                        "applicability": "UNAVAILABLE",
                        "uncertainty": None,
                        "provenance": [],
                        "model_version": None,
                    }
                    for endpoint in unavailable_endpoints
                ],
                "pleasantness_state": "NOT_ESTABLISHED",
                "personal_liking_state": "NOT_TESTED",
                "physically_tested": False,
            }
        )
    completion = project_completion_states(
        generic_platform_contracts_pass=True,
        computational_comparison_complete=False,
        personal_selection_complete=False,
        qualified_commercial_release_receipt_present=False,
    )
    completion_states = {
        key: completion[key]
        for key in (
            "PLATFORM_SOFTWARE_COMPLETE",
            "R6_COMPUTATIONAL_EVIDENCE_COMPLETE",
            "PERSONAL_SELECTION_COMPLETE",
            "COMMERCIAL_RELEASE_READY",
        )
    }
    report = {
        "schema_version": "lavande-checkpoint19-comparison-boundary-v1",
        "comparators": comparators,
        "shared_boundary": {
            "inventory_sha256": inventory_hash,
            "capability_bundle_sha256": capability_hash,
            "release_scenario_sha256": None,
        },
        "classifications": [
            "COMPUTATIONALLY_DIFFERENT",
            "NONDISCRIMINATING_EVIDENCE",
            "NOT_PHYSICALLY_TESTED",
            "OUT_OF_DOMAIN",
        ],
        "missing_requirements": [
            "EXACT_STOCK_LOTS_AND_DENSITIES_NOT_BOUND",
            "COMMON_ACTIVE_MASS_BASIS_UNAVAILABLE",
            "APPLICABLE_RELEASE_SCENARIO_NOT_BOUND",
            "EXACT_CURVE_RANGES_AND_MATRIX_APPLICABILITY_NOT_BOUND",
            "PERSONAL_OBSERVATIONS_MISSING",
        ],
        "selection": {
            "status": "HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED",
            "ranked_candidates": [],
            "pareto_candidates": [],
            "unordered_candidates": [
                loaded.snapshot.formula_id for loaded in loads
            ],
            "best_observed_candidate": None,
            "experimental_recommendation": None,
            "formula_action": "NO_CHANGE",
        },
        "completion_states": completion_states,
        "completion_boundary": {
            "platform_basis": (
                "GENERIC_IDENTITY_AUTHORITY_JOB_RELEASE_PERCEPTION_OPTIMIZER_"
                "OBSERVATION_AND_PHYSICAL_LINEAGE_CONTRACTS_IMPLEMENTED"
            ),
            "computational_evidence_state": "WITHHELD_OUT_OF_DOMAIN",
            "personal_selection_state": "NOT_TESTED",
            "commercial_state_source": completion["commercial_state_source"],
            "automatic_commercial_authority": completion[
                "automatic_commercial_authority"
            ],
        },
        "formula_action": "NO_CHANGE",
        **FALSE_ACTION_AUTHORITY,
    }
    return {**report, "report_sha256": stable_payload_hash(report)}


__all__ = ["evaluate_checkpoint19_comparison_boundary"]
