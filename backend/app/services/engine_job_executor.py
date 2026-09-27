"""Fixed in-process executors for the closed engine-job registry.

Every handler is read-only and returns advisory evidence.  Unsupported
scientific applicability is a successful WITHHELD result, never an invitation
to substitute a heuristic or execute caller-selected code.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from engine.calibration.hashing import (
    stable_json_hash,
)
from engine.calibration.hashing import (
    stable_portable_file_hash as stable_file_hash,
)
from engine.preference import PairwisePreference
from engine.research.contracts import FALSE_ACTION_AUTHORITY, ReleaseScenarioV1
from engine.research.goal_analysis import (
    GoalAnalysisRequestV1,
    GoalFormulaRowV1,
    analyze_formula_for_goal,
)
from engine.research.preference import (
    DavidsonFitConfigV1,
    fit_davidson_personal_preference,
)
from engine.research.release import (
    FiniteReleaseParametersV1,
    ReleaseComponentV1,
    simulate_finite_release,
)
from engine.research.selection import OfflineCandidateV1, compare_search_arms

from app.services.engine_job_registry import ENGINE_JOB_CONTRACT_VERSION_V2
from app.services.validation_pipeline import validate_formula

_FALSE_AUTHORITY = {
    "release_authority": False,
    "safety_authority": False,
    "compounding_authority": False,
    "evidence_admission_authorized": False,
}

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_R5_COMPARATOR_MANIFEST = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r5_design_comparator_20260923.json"
)
_R5_CP3_READINESS_PROTOCOL = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r5_cp3_readiness_protocol_20260926_v5.json"
)
_R5_CP3_READINESS_PREDECESSOR = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r5_cp3_readiness_protocol_20260924_v4.json"
)
_R5_BASELINE_DECISION = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r5_standalone_baseline_decision_20260926.json"
)
_R6_AIMI_DECISION = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r6_aimi_user_decision_20260926.json"
)
_R6_AIMI_SUCCESSOR = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r6_aimi_design_successor_20260926.json"
)
_R6_CP5_INPUT_PROTOCOL = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r6_cp5_execution_input_protocol_20260926.json"
)
_R6_CP5_EVALUATOR = (
    _REPOSITORY_ROOT / "engine" / "experiments" / "checkpoint5_readiness.py"
)
_R6_CP6_LINEAGE_PROTOCOL = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r6_cp6_physical_lineage_intake_20260926.json"
)
_R6_CP6_EVALUATOR = (
    _REPOSITORY_ROOT / "engine" / "experiments" / "checkpoint6_readiness.py"
)
_R6_CP7_RESEARCH_PROTOCOL = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r6_cp7_research_applicability_intake_20260926.json"
)
_R6_CP7_EVALUATOR = (
    _REPOSITORY_ROOT / "engine" / "experiments" / "checkpoint7_readiness.py"
)
_R6_CP8_SENSORY_PROTOCOL = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r6_cp8_sensory_evidence_intake_20260926.json"
)
_CP10_LEGACY_SURFACE_TRANSITIONS = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "full_potential_cp10_legacy_surface_transitions_20260927.json"
)
_R5_CP3_MEASUREMENT_SCHEMA = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r5_cp3_readiness_protocol_20260924.json"
)
_R5_STOCK_CONFIRMATION = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "inventory_user_confirmation_20260924_r5_remaining_stock_forms_v3.json"
)
_AROMA_MORE_PRODUCT_RESOLUTION = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "inventory_supplier_product_resolution_20260924_aroma_more_lavender_4042.json"
)
_R5_CURRENT_INVENTORY_OVERLAY = (
    _REPOSITORY_ROOT
    / "data"
    / "governance"
    / "inventory_user_authority_overlay_20260924_r5_remaining_stock_forms_v3.json"
)
_INVENTORY_TEXT = _REPOSITORY_ROOT / "inventory.txt"
_BASIS_TO_ENGINE = {
    "NEAT": "neat",
    "V_V": "volume_fraction",
    "W_W": "mass_fraction",
}
_CP5_BLOCKER_OWNERSHIP = {
    "checkpoint5": [
        "HOLD_AIMI_BOTTLE_TO_REFERENCE_IDENTITY_UNVERIFIED",
        "HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING",
        "HOLD_MEASUREMENT_PROTOCOL_EXECUTION_PARAMETERS_UNRESOLVED",
    ],
    "checkpoint6": [
        "HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING",
        "HOLD_REQUIRED_WORKING_STOCKS_NOT_PREPARED",
        "BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING",
    ],
    "checkpoint7": ["HOLD_EXACT_CURVE_APPLICABILITY"],
    "checkpoint8": [
        "PLEASANTNESS_NOT_ESTABLISHED",
        "PHYSICAL_LIKING_NOT_TESTED",
    ],
}
_CP5_AUTHORITY = {
    "checkpoint5_input_contract_record_authorized": True,
    "evidence_admission_authorized": False,
    "stock_preparation_authorized": False,
    "reservation_authorized": False,
    "physical_experiment_authorized": False,
    "compounding_authorized": False,
    "purchase_authorized": False,
    "inventory_mutation_authorized": False,
    "physical_formula_mutation_authorized": False,
    "safety_authorized": False,
    "release_authorized": False,
}
_CP6_BLOCKERS = [
    "HOLD_ALL_BUILD_PLAN_STOCK_BINDINGS_MISSING",
    "HOLD_REQUIRED_WORKING_STOCKS_NOT_PREPARED",
    "BOTTLE_LOT_AND_PREPARATION_RECEIPTS_MISSING",
]
_CP6_AUTHORITY = {
    "checkpoint6_intake_contract_record_authorized": True,
    "evidence_admission_authorized": False,
    "stock_preparation_authorized": False,
    "reservation_authorized": False,
    "physical_experiment_authorized": False,
    "compounding_authorized": False,
    "purchase_authorized": False,
    "inventory_mutation_authorized": False,
    "physical_formula_mutation_authorized": False,
    "safety_authorized": False,
    "release_authorized": False,
}
_CP6_SIDE_EFFECTS = {
    "backend_record_created": False,
    "build_plan_created": False,
    "physical_binding_created": False,
    "prepared_stock_receipt_created": False,
    "reservation_created": False,
    "compounding_run_created": False,
    "mixer_command_created": False,
    "transfer_record_created": False,
    "inventory_modified": False,
    "physical_formula_modified": False,
}
_CP6_SUPPORTED_INVARIANTS = [
    "FINITE_DECIMAL_QUANTITIES",
    "W_W_REQUIRES_MASS",
    "V_V_REQUIRES_VOLUME",
    "PREPARATION_CONSERVATION",
    "EXACT_STOCK_FRACTION_AND_BASIS_MATCH",
    "DENSITY_AND_PROVENANCE_REQUIRED_FOR_VOLUME_BINDING",
    "EXACT_FORMULA_COMPONENT_MASS_MATCH",
    "COMPLETE_ALL_LINE_BINDING",
    "BASKET_FIRST_DESCENDING_LIQUID_ORDER",
    "APPEND_ONLY_FALSE_AUTHORITY_RECORDS",
]
_CP6_ADMISSION_GAPS = [
    "INVENTORY_CANDIDATE_TO_BACKEND_STOCK_MAPPING_UNRESOLVED",
    "PLAN_LEVEL_LINEAGE_RECEIPTS_ARE_UNVERIFIED_STRINGS",
    "PREPARATION_RECEIPT_OPTIONAL_AT_BINDER_BOUNDARY",
    "PER_ROW_BOTTLE_LOT_RECEIPT_NOT_REPRESENTED",
    "CARRIER_PROVENANCE_NOT_CANONICALLY_RESOLVED",
    "DENSITY_PROVENANCE_IS_TEXT_NOT_RECEIPT_BOUND",
    "EXACT_TARGET_WEIGHED_MASS_ROUTE_NOT_ACCEPTED_BY_VOLUME_BINDER",
    "NEXT_COMMAND_IS_STATE_CHANGING_NOT_DOCUMENTARY",
]
_CP7_BLOCKERS = [
    "HOLD_CP7_CP6_PHYSICAL_READINESS_INCOMPLETE",
    "HOLD_CP7_RESEARCH_SAMPLE_NOT_COMPOUNDED",
    "HOLD_CP7_MEASUREMENT_EXECUTION_PARAMETERS_UNRESOLVED",
    "HOLD_CP7_MEASURED_GAS_INPUTS_UNAVAILABLE",
    "HOLD_EXACT_CURVE_APPLICABILITY",
]
_CP7_AUTHORITY = {
    "checkpoint7_intake_contract_record_authorized": True,
    "evidence_admission_authorized": False,
    "stock_preparation_authorized": False,
    "physical_binding_authorized": False,
    "reservation_authorized": False,
    "compounding_authorized": False,
    "physical_experiment_authorized": False,
    "measurement_execution_authorized": False,
    "sensory_evaluation_authorized": False,
    "formula_optimization_authorized": False,
    "purchase_authorized": False,
    "inventory_mutation_authorized": False,
    "physical_formula_mutation_authorized": False,
    "safety_authorized": False,
    "release_authorized": False,
}
_CP7_SIDE_EFFECTS = {
    "backend_record_created": False,
    "build_plan_created": False,
    "physical_binding_created": False,
    "prepared_stock_receipt_created": False,
    "reservation_created": False,
    "compounding_run_created": False,
    "mixer_command_created": False,
    "transfer_record_created": False,
    "research_sample_created": False,
    "measurement_executed": False,
    "sensory_evaluation_executed": False,
    "inventory_modified": False,
    "physical_formula_modified": False,
}
_CP8_BLOCKERS = [
    "HOLD_CP8_CP7_RESEARCH_CHARACTERIZATION_INCOMPLETE",
    "HOLD_CP8_PHYSICAL_SENSORY_SAMPLES_UNAVAILABLE",
    "HOLD_CP8_SENSORY_PROTOCOL_BINDINGS_INCOMPLETE",
    "HOLD_CP8_EXACT_CONDITION_HUMAN_OBSERVATIONS_UNAVAILABLE",
    "PLEASANTNESS_NOT_ESTABLISHED",
    "PHYSICAL_LIKING_NOT_TESTED",
]
_CP8_AUTHORITY = {
    "checkpoint8_intake_contract_record_authorized": True,
    "evidence_admission_authorized": False,
    "human_study_authorized": False,
    "physical_experiment_authorized": False,
    "sensory_evaluation_authorized": False,
    "participant_recruitment_authorized": False,
    "model_training_authorized": False,
    "model_calibration_authorized": False,
    "formula_optimization_authorized": False,
    "compounding_authorized": False,
    "purchase_authorized": False,
    "inventory_mutation_authorized": False,
    "physical_formula_mutation_authorized": False,
    "safety_authorized": False,
    "release_authorized": False,
}
_CP8_SIDE_EFFECTS = {
    "backend_record_created": False,
    "physical_sample_created": False,
    "participant_contacted": False,
    "human_observation_created": False,
    "sensory_evaluation_executed": False,
    "model_trained": False,
    "model_calibrated": False,
    "formula_ranked": False,
    "inventory_modified": False,
    "physical_formula_modified": False,
}


def _percentages(
    payload: dict[str, Any],
) -> tuple[dict[str, float], str | None, str | None]:
    rows = list(payload.get("rows", []))
    dimensions = {
        "volume" if str(row["amount_unit"]) in {"uL", "mL"} else "mass"
        for row in rows
    }
    if len(dimensions) != 1:
        return {}, None, "HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED"
    dimension = next(iter(dimensions))
    totals: dict[str, Decimal] = {}
    for row in rows:
        basis = str(row.get("concentration_basis", "UNKNOWN"))
        fraction_text = row.get("concentration_fraction_decimal")
        if basis == "UNKNOWN":
            return {}, None, "HOLD_STOCK_BINDING"
        if fraction_text is None:
            if basis != "NEAT":
                return {}, None, "HOLD_STOCK_BINDING"
            fraction = Decimal(1)
        else:
            fraction = Decimal(str(fraction_text))
        if basis == "NEAT" and fraction != Decimal(1):
            return {}, None, "HOLD_STOCK_BINDING"
        if (dimension == "volume" and basis == "W_W") or (
            dimension == "mass" and basis == "V_V"
        ):
            return {}, None, "HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED"

        amount = Decimal(str(row["amount_decimal"]))
        if row["amount_unit"] in {"mL", "g"}:
            amount *= Decimal(1000)
        material = str(row["material"])
        totals[material] = totals.get(material, Decimal(0)) + amount * fraction
    total = sum(totals.values(), Decimal(0))
    if total <= 0:
        return {}, None, "INVALID_ZERO_TOTAL"
    return (
        {
            material: float(amount / total * Decimal(100))
            for material, amount in totals.items()
        },
        f"active_{dimension}",
        None,
    )


def _formula_analysis(payload: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    percentages, percentage_basis, hold = _percentages(payload)
    if hold is not None:
        return (
            "WITHHELD",
            {
                "status": hold,
                "formula_action": "NO_CHANGE",
                "formula_modified": False,
                **_FALSE_AUTHORITY,
            },
            hold,
        )
    report = validate_formula(percentages)
    terminal = (
        "SUCCEEDED"
        if report.state in {"ADVISORY_COMPLETE", "ADVISORY_FINDINGS"}
        else "WITHHELD"
    )
    return (
        terminal,
        {
            "status": report.state,
            "formula_id": payload["formula_id"],
            "formula_name": payload["formula_name"],
            "row_count": len(payload["rows"]),
            "percentage_basis": percentage_basis,
            "validation": report.to_dict(),
            "formula_action": "NO_CHANGE",
            "formula_modified": False,
            **_FALSE_AUTHORITY,
        },
        report.state,
    )


def _formula_goal_analysis_v2(
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any], str]:
    """Run goal-directed clues even when quantitative conversion is withheld."""

    # Formula validation and common-basis status remain visible, but a missing
    # density or mixed mass/volume basis does not prevent qualitative research
    # hypotheses from being generated.
    baseline_terminal, baseline_result, baseline_validation = _formula_analysis(payload)
    from engine.inventory_parser import inventory_names

    rows = tuple(
        GoalFormulaRowV1(
            row_id=str(row["row_id"]),
            material=str(row["material"]),
            amount_decimal=str(row["amount_decimal"]),
            unit=str(row["amount_unit"]),
            stock_fraction_decimal=(
                str(row["concentration_fraction_decimal"])
                if row.get("concentration_fraction_decimal") is not None
                else ("1" if row.get("concentration_basis") == "NEAT" else None)
            ),
            stock_basis=str(row.get("concentration_basis", "UNKNOWN")),
            basket=(str(row["basket"]) if row.get("basket") else None),
            role=(str(row["role"]) if row.get("role") else None),
        )
        for row in payload["rows"]
    )
    analysis = analyze_formula_for_goal(
        GoalAnalysisRequestV1(
            formula_id=str(payload["formula_id"]),
            formula_name=str(payload["formula_name"]),
            rows=rows,
            goals=tuple(payload["goals"]),
            observations=tuple(payload.get("observations", [])),
            must_preserve=tuple(payload.get("must_preserve", [])),
            must_avoid=tuple(payload.get("must_avoid", [])),
            family=payload.get("family"),
            profile=payload.get("profile"),
            mode=str(payload.get("mode", "pre_mix")),
            available_materials=tuple(
                inventory_names(
                    unique=True,
                    include_solvents=False,
                    include_unavailable=False,
                )
            ),
            max_hypotheses=int(payload.get("max_hypotheses", 5)),
        )
    )
    hypotheses = list(analysis["modification_hypotheses"])
    validation = str(analysis["validation_state"])
    terminal = "SUCCEEDED" if hypotheses else "WITHHELD"
    findings: list[dict[str, Any]] = []
    if baseline_terminal != "SUCCEEDED":
        findings.append(
            {
                "code": "QUANTITATIVE_FORMULA_VALIDATION_WITHHELD",
                "state": baseline_validation,
            }
        )
    if analysis["evidence_summary"]["applicable_endpoint_count"] == 0:
        findings.append({"code": "MEASURED_OUTCOME_NOT_SUPPLIED"})
    result = {
        "formula_id": payload["formula_id"],
        "formula_name": payload["formula_name"],
        "workflow_mode": payload["workflow_mode"],
        "baseline_formula_validation": baseline_result,
        "goal_analysis": analysis,
        "formula_action": analysis["selection"]["formula_action"],
        "formula_modified": False,
        "selection": analysis["selection"],
    }
    return terminal, _v2_envelope(
        validation_state=validation,
        applicability_state=str(analysis["applicability_state"]),
        findings=findings,
        missing_requirements=(
            [] if hypotheses else ["ONE_CONCRETE_SENSORY_DIRECTION"]
        ),
        result=result,
    ), validation


def _withheld_result(code: str, **detail: Any) -> tuple[str, dict[str, Any], str]:
    return (
        "WITHHELD",
        {
            "status": code,
            "formula_action": "NO_CHANGE",
            "formula_modified": False,
            **detail,
            **_FALSE_AUTHORITY,
        },
        code,
    )


def _release_gate(payload: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    """Run the actual in-process gate only for dimensionally eligible rows."""

    unsupported = [
        str(row["row_id"])
        for row in payload["rows"]
        if row["amount_unit"] in {"mg", "g"}
    ]
    if unsupported:
        return _withheld_result(
            "HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED",
            release_gate_diagnostic_complete=False,
            unsupported_mass_row_ids=unsupported,
        )

    ingredients_ul: dict[str, Decimal] = {}
    dilutions: dict[str, Decimal] = {}
    stock_specs: dict[str, dict[str, Any]] = {}
    for row in payload["rows"]:
        material = str(row["material"])
        basis = str(row.get("concentration_basis", "UNKNOWN"))
        fraction_text = row.get("concentration_fraction_decimal")
        if basis == "UNKNOWN" or basis not in _BASIS_TO_ENGINE:
            return _withheld_result(
                "HOLD_STOCK_BINDING",
                release_gate_diagnostic_complete=False,
                unresolved_row_id=str(row["row_id"]),
            )
        if fraction_text is None:
            if basis != "NEAT":
                return _withheld_result(
                    "HOLD_STOCK_BINDING",
                    release_gate_diagnostic_complete=False,
                    unresolved_row_id=str(row["row_id"]),
                )
            fraction = Decimal(1)
        else:
            fraction = Decimal(str(fraction_text))
        if basis == "NEAT" and fraction != Decimal(1):
            return _withheld_result(
                "HOLD_STOCK_BINDING",
                release_gate_diagnostic_complete=False,
                inconsistent_neat_row_id=str(row["row_id"]),
            )

        amount = Decimal(str(row["amount_decimal"]))
        amount_ul = amount * (Decimal(1000) if row["amount_unit"] == "mL" else Decimal(1))
        prior_fraction = dilutions.get(material)
        prior_spec = stock_specs.get(material)
        spec = {
            "declared": True,
            "fraction": float(fraction),
            "fraction_basis": _BASIS_TO_ENGINE[basis],
            "carrier": str(row.get("carrier") or ""),
            "stock_id": str(row.get("stock_id") or ""),
            "approximate": False,
        }
        if prior_fraction is not None and (
            prior_fraction != fraction or prior_spec != spec
        ):
            return _withheld_result(
                "HOLD_CONFLICTING_DUPLICATE_STOCK_BINDING",
                release_gate_diagnostic_complete=False,
                material=material,
            )
        ingredients_ul[material] = ingredients_ul.get(material, Decimal(0)) + amount_ul
        dilutions[material] = fraction
        stock_specs[material] = spec

    # Import lazily so API processes do not pay the engine startup cost merely
    # for exposing the asynchronous job endpoints.
    from engine.pipeline.gates import ReleaseGateConfig, gate_formula

    formula = {
        "number": 1,
        "name": str(payload["formula_name"]),
        "ingredients_ul": {
            material: float(amount) for material, amount in ingredients_ul.items()
        },
        "dilutions": {
            material: float(fraction) for material, fraction in dilutions.items()
        },
        "stock_specs": stock_specs,
        "source_engine_job_formula_id": str(payload["formula_id"]),
    }
    config = ReleaseGateConfig(
        expected_concentrate_ul=float(
            Decimal(str(payload["expected_concentrate_ul_decimal"]))
        ),
        batch_volume_ml=float(
            Decimal(str(payload.get("final_volume_ml_decimal", "30")))
        ),
        brief=str(payload["brief"]),
        quantitative_claim=True,
        audit_enabled=False,
        mode="RELEASE_REVIEW",
        action="REPORT",
    )
    report = gate_formula(formula, config)
    report_payload = report.as_dict()
    if report.status == "PASS":
        terminal_state = "SUCCEEDED"
        validation_state = "ADVISORY_COMPLETE"
    elif report.status == "WARN":
        terminal_state = "SUCCEEDED"
        validation_state = "ADVISORY_FINDINGS"
    else:
        terminal_state = "WITHHELD"
        validation_state = "WITHHOLD_RELEASE_GATE_FINDINGS"
    return (
        terminal_state,
        {
            "status": report.status,
            "release_gate_diagnostic_complete": True,
            "gate_report": report_payload,
            "formula_action": "NO_CHANGE",
            "formula_modified": False,
            **_FALSE_AUTHORITY,
        },
        validation_state,
    )


def _mixer_sequence(payload: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    def basket_key(row: dict[str, Any]) -> tuple[int, Decimal, str]:
        basket = str(row.get("basket") or "ZZ")
        if basket == "W0":
            basket_rank = 0
        elif basket.startswith("B") and basket[1:].isdigit():
            # Preserve the physical basket identifier.  The declared row order
            # remains part of the job hash; execution uses basket first.
            basket_rank = int(basket[1:])
        else:
            basket_rank = 999
        amount = Decimal(str(row["amount_decimal"]))
        mass_rank = 1 if row["amount_unit"] in {"mg", "g"} else 0
        return (basket_rank * 2 + mass_rank, -amount, str(row["row_id"]))

    ordered = sorted(payload["rows"], key=basket_key)
    return (
        "WITHHELD",
        {
            "status": "HOLD_PHYSICAL_AUTHORITY_NOT_GRANTED",
            "ordering_contract": payload["order_policy"],
            "steps": [
                {
                    "sequence": index,
                    "row_id": row["row_id"],
                    "material": row["material"],
                    "basket": row.get("basket"),
                    "operation": row["operation"],
                    "amount_decimal": row["amount_decimal"],
                    "amount_unit": row["amount_unit"],
                    "stock_id": row.get("stock_id"),
                }
                for index, row in enumerate(ordered, start=1)
            ],
            "physical_instruction_authorized": False,
            "formula_action": "NO_CHANGE",
            **_FALSE_AUTHORITY,
        },
        "HOLD_PHYSICAL_AUTHORITY_NOT_GRANTED",
    )


def _approved_legacy_surface_transitions(
    change_scope: str,
) -> set[tuple[str, str, str]]:
    """Return explicitly governed source transitions for one compatibility scope."""

    try:
        manifest = json.loads(
            _CP10_LEGACY_SURFACE_TRANSITIONS.read_text(encoding="utf-8")
        )
        if (
            manifest.get("schema_version")
            != "full-potential-cp10-legacy-surface-transitions-v1"
            or manifest.get("state")
            != "ADDITIVE_COMPATIBILITY_TRANSITION_NOT_HISTORICAL_REWRITE"
            or set(manifest.get("authority", {})) != set(_FALSE_AUTHORITY)
            or any(
                value is not False
                for value in manifest.get("authority", {}).values()
            )
        ):
            return set()
        approved: set[tuple[str, str, str]] = set()
        for transition in manifest.get("transitions", []):
            if (
                transition.get("change_scope") != change_scope
                or transition.get("historical_protocol_rewritten") is not False
            ):
                continue
            if change_scope == "MODULE_AUTHORITY_DOCUMENTATION_ONLY":
                if transition.get("executable_curve_semantics_changed") is not False:
                    continue
            elif change_scope == "ADDITIVE_PHYSICAL_LINEAGE_EXTENSION":
                if transition.get("checkpoint6_contract_semantics_preserved") is not True:
                    continue
            else:
                continue
            path = transition.get("path")
            frozen = transition.get("frozen_sha256")
            current = transition.get("current_sha256")
            if not all(
                isinstance(value, str) and value
                for value in (path, frozen, current)
            ):
                continue
            approved.add((path, frozen, current))
        return approved
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return set()


def _load_checkpoint7_intake_receipt(
    *,
    checkpoint6_protocol_sha256: str,
    checkpoint5_protocol_sha256: str,
    checkpoint6_inputs: dict[str, Any],
    checkpoint5_measurement: dict[str, Any],
) -> tuple[str | None, dict[str, Any] | None]:
    if not _R6_CP7_RESEARCH_PROTOCOL.is_file():
        return "HOLD_CP7_RESEARCH_PROTOCOL_UNAVAILABLE", None
    try:
        protocol = json.loads(
            _R6_CP7_RESEARCH_PROTOCOL.read_text(encoding="utf-8")
        )
        inputs = dict(protocol["inputs"])
        scientific_surface = {
            key: dict(protocol["scientific_surface"][key])
            for key in (
                "measured_intensity_manifest",
                "source_manifest",
                "dose_response_implementation",
                "dynamic_release_implementation",
                "headspace_oav_implementation",
                "source_artifact",
                "transcription_artifact",
            )
        }
        prerequisite = dict(protocol["checkpoint6_prerequisite"])
        literature = dict(protocol["literature_source_contract"])
        curve_inventory = dict(protocol["curve_inventory_contract"])
        curve_input = dict(protocol["curve_input_contract"])
        release_boundary = dict(protocol["release_model_boundary"])
        sample = dict(protocol["research_sample_contract"])
        measurement = dict(protocol["measurement_protocol_contract"])
        applicability = dict(protocol["applicability_contract"])
        mixture = dict(protocol["mixture_challenger_contract"])
        endpoint = dict(protocol["endpoint_contract"])
        evidence = dict(protocol["canonical_current_evidence"])
        blockers = list(protocol["checkpoint7_blockers"])
        contract = dict(protocol["checkpoint7_contract"])
        authority = dict(protocol["authority"])
        side_effects = dict(protocol["side_effects"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return "HOLD_CP7_RESEARCH_PROTOCOL_INVALID", None
    if authority != _CP7_AUTHORITY or side_effects != _CP7_SIDE_EFFECTS:
        return "HOLD_CP7_RESEARCH_PROTOCOL_AUTHORITY_ESCALATION", None

    expected_surface_paths = {
        "measured_intensity_manifest": (
            "data/governance/measured_intensity_capabilities_20260923.json"
        ),
        "source_manifest": (
            "data/source_manifests/optimizer_sensory_research_20260909.json"
        ),
        "dose_response_implementation": "engine/dose_response.py",
        "dynamic_release_implementation": "engine/physics/dynamic_release.py",
        "headspace_oav_implementation": "engine/physics/headspace_oav.py",
        "source_artifact": (
            "output/optimizer_research_20260909/wakayama_2019/"
            "ie9b01225_si_001.pdf"
        ),
        "transcription_artifact": (
            "output/optimizer_research_20260909/wakayama_2019/"
            "wakayama-intensity.txt"
        ),
    }
    approved_transitions = _approved_legacy_surface_transitions(
        "MODULE_AUTHORITY_DOCUMENTATION_ONLY"
    )

    surface_valid = True
    for key, relative_path in expected_surface_paths.items():
        path = _REPOSITORY_ROOT / relative_path
        record = scientific_surface[key]
        current_sha256 = stable_file_hash(path) if path.is_file() else None
        exact_match = record.get("sha256") == current_sha256
        approved_transition = (
            relative_path,
            str(record.get("sha256")),
            str(current_sha256),
        ) in approved_transitions
        if (
            record.get("path") != relative_path
            or not path.is_file()
            or not (exact_match or approved_transition)
        ):
            surface_valid = False
            break

    required_physical_parameters = [
        "authorized_sample_scale",
        "application_mass_or_volume",
        "application_basis",
        "surface_area",
        "substrate_selection",
        "temperature_c",
        "relative_humidity_percent",
        "airflow",
        "enclosure_geometry",
        "sampling_schedule",
        "headspace_collection_method",
        "available_instrument_method",
        "instrument_calibration",
        "matrix_calibration",
        "replicate_structure",
        "aging_conditions",
        "storage_conditions",
    ]
    required_sensory_controls = [
        "qualified_sensory_panel_or_reviewer_scope",
        "randomized_sample_codes",
        "blinding",
        "presentation_order_balance",
        "predeclared_scales",
        "rest_intervals",
        "session_identity",
        "missingness_retention",
    ]
    evidence_keys = {
        "physical_build_bindings",
        "compounding_run_receipts",
        "transfer_receipts",
        "research_sample_receipts",
        "independent_preparation_receipts",
        "carrier_or_matrix_blank_receipts",
        "reference_sample_receipts",
        "aging_storage_receipts",
        "instrument_calibration_receipts",
        "matrix_calibration_receipts",
        "measured_gas_observations",
        "exact_curve_binding_receipts",
    }
    cp6_evaluator_hash = (
        stable_file_hash(_R6_CP6_EVALUATOR)
        if _R6_CP6_EVALUATOR.is_file()
        else "MISSING"
    )
    if (
        protocol.get("schema_version")
        != "lavande-ambre-profond-r6-cp7-research-applicability-intake-v1"
        or protocol.get("state")
        != "FROZEN_NONEXECUTING_RESEARCH_APPLICABILITY_INTAKE_CONTRACT"
        or inputs.get("checkpoint6_protocol_path")
        != (
            "data/governance/"
            "lavande_ambre_profond_r6_cp6_physical_lineage_intake_20260926.json"
        )
        or inputs.get("checkpoint6_protocol_sha256")
        != checkpoint6_protocol_sha256
        or inputs.get("checkpoint6_evaluator_path")
        != "engine/experiments/checkpoint6_readiness.py"
        or inputs.get("checkpoint6_evaluator_sha256") != cp6_evaluator_hash
        or inputs.get("checkpoint6_report_sha256")
        != "d3475d086589da88ee0c615889b0130dcd7f3c0617a0dfb60c8042b2dcfe5400"
        or inputs.get("checkpoint5_protocol_path")
        != (
            "data/governance/"
            "lavande_ambre_profond_r6_cp5_execution_input_protocol_20260926.json"
        )
        or inputs.get("checkpoint5_protocol_sha256")
        != checkpoint5_protocol_sha256
        or any(
            inputs.get(key) != checkpoint6_inputs.get(key)
            for key in (
                "r6_successor_rows_sha256",
                "inventory_text_sha256",
                "inventory_snapshot_sha256",
                "inventory_overlay_sha256",
            )
        )
        or not surface_valid
        or prerequisite
        != {
            "required_state": "PASS_CP6_PHYSICAL_READINESS_BOUND_NOT_COMPOUNDED",
            "observed_state": "HOLD_CP6_PHYSICAL_LINEAGE_INPUTS_INCOMPLETE",
            "satisfied": False,
            "bypass_allowed": False,
        }
        or literature
        != {
            "source": (
                "Wakayama et al. 2019 perfumery raw-material intensity curves"
            ),
            "doi": "10.1021/acs.iecr.9b01225",
            "correction_doi": "10.1021/acs.iecr.0c05822",
            "license": "CC BY-NC 4.0",
            "permitted_use": "attributed noncommercial research only",
            "commercial_use_authorized": False,
            "source_fit_overlap": "UNKNOWN",
            "threshold_equation_revision": "WAKAYAMA_DECEMBER_2020_CORRECTION",
            "threshold_roundtrip_criterion": 1.4,
            "threshold_output_unit": "ng/L_air",
        }
        or curve_inventory
        != {
            "source_parameter_row_count": 314,
            "positive_evaluable_curve_count": 313,
            "nonpositive_slope_curve_count": 1,
            "nonpositive_slope_identity": "121-33-5",
            "identity_exact_count": 0,
            "identity_unadjudicated_count": 313,
            "identity_conflict_count": 1,
            "observed_range_bound_count": 0,
            "exact_material_binding_count": 0,
            "current_admission_state": (
                "HOLD_EXACT_IDENTITY_RANGE_MATRIX_BINDING"
            ),
        }
        or curve_input
        != {
            "physical_quantity": "GAS_MASS_CONCENTRATION",
            "phase": "AIR",
            "unit": "ug/L_air",
            "liquid_dose_allowed": False,
            "stock_fraction_allowed": False,
            "oav_allowed": False,
            "modeled_unvalidated_release_as_measured_input_allowed": False,
            "extrapolation_authorized": False,
        }
        or release_boundary.get("dynamic_release_authority")
        != "SIMULATION_ONLY_UNCALIBRATED"
        or any(
            value is not False
            for key, value in release_boundary.items()
            if key != "dynamic_release_authority"
        )
        or sample
        != {
            "required_sample_roles": checkpoint5_measurement.get("sample_roles"),
            "documentary_r5_is_physical_comparator": False,
            "complete_cp6_binding_required": True,
            "compounding_run_required": True,
            "complete_transfer_receipt_chain_required": True,
            "aging_and_storage_receipts_required": True,
            "sample_identity_receipts_required": True,
            "research_sample_compounded": False,
            "physical_formula_modified": False,
        }
        or measurement.get("state")
        != "R6_SCHEMA_FROZEN_EXECUTION_PARAMETERS_UNRESOLVED"
        or measurement.get("execution_ready") is not False
        or measurement.get("domains_must_remain_separate")
        != checkpoint5_measurement.get("domains_must_remain_separate")
        or measurement.get("required_physical_parameters")
        != required_physical_parameters
        or measurement.get("required_sensory_controls")
        != required_sensory_controls
        or measurement.get("resolved_execution_parameters") != {}
        or measurement.get("unresolved_execution_parameter_count") != 25
        or applicability
        != {
            "exact_stock_identity_required": True,
            "per_curve_observed_range_required": True,
            "exact_matrix_required": True,
            "exact_delivery_required": True,
            "exact_scenario_required": True,
            "measured_gas_concentration_required": True,
            "whole_natural_transfer_authorized": False,
            "commercial_product_transfer_authorized": False,
            "full_perfume_transfer_authorized": False,
            "family_similarity_may_bind_curve": False,
            "constituent_similarity_may_bind_whole_product_curve": False,
            "proxy_curve_may_clear_checkpoint7": False,
            "current_exact_curve_applicable_row_count": 0,
            "current_full_formula_curve_applicable": False,
        }
        or mixture
        != {
            "models": [
                "STRONGEST_COMPONENT",
                "FITTED_PARTIAL_ADDITION",
                "PRIMACY_TRANSFER",
            ],
            "models_remain_separate": True,
            "averaging_authorized": False,
            "missing_component_calibration_abstains_whole_mixture": True,
            "current_execution_authorized": False,
            "partial_addition_empirical_admission_state": "HOLD",
            "formula_optimization_authority": False,
        }
        or endpoint
        != {
            "physical_release": "NOT_MEASURED",
            "sensory_intensity": "NOT_ESTABLISHED",
            "character": "NOT_ESTABLISHED",
            "pleasantness": "NOT_ESTABLISHED",
            "personal_liking": "NOT_TESTED",
            "population_liking": "NOT_TESTED",
            "beauty": "PROHIBITED_DERIVED_ENDPOINT",
        }
        or set(evidence) != evidence_keys
        or any(not isinstance(value, list) or value for value in evidence.values())
        or blockers != _CP7_BLOCKERS
        or contract
        != {
            "state": "SOFTWARE_COMPLETE_RESEARCH_APPLICABILITY_INTAKE_HOLD",
            "hold_state": (
                "HOLD_CP7_BUILD_MEASUREMENT_OR_APPLICABILITY_INCOMPLETE"
            ),
            "future_pass_state": "PASS_CP7_R6_RESEARCH_SAMPLE_CHARACTERIZED",
            "formula_action": "DESIGN_SUCCESSOR_UNCHANGED",
            "physical_build_state": "NOT_BOUND",
            "research_sample_state": "NOT_COMPOUNDED",
            "measurement_execution_state": "NOT_STARTED",
            "exact_curve_applicability_state": "HOLD_EXACT_CURVE_APPLICABILITY",
            "formula_modified": False,
            "inventory_modified": False,
        }
    ):
        return "HOLD_CP7_RESEARCH_PROTOCOL_DRIFT", None

    receipt = {
        "protocol_manifest_sha256": stable_file_hash(
            _R6_CP7_RESEARCH_PROTOCOL
        ),
        "protocol_id": protocol.get("protocol_id"),
        "protocol_state": protocol.get("state"),
        "checkpoint7_state": contract.get("state"),
        "research_applicability_state": contract.get("hold_state"),
        "checkpoint6_prerequisite": prerequisite,
        "research_sample_contract": sample,
        "measurement_protocol": measurement,
        "literature_source_contract": literature,
        "curve_inventory": curve_inventory,
        "curve_input_contract": curve_input,
        "release_model_boundary": release_boundary,
        "applicability_contract": applicability,
        "mixture_challenger_contract": mixture,
        "endpoint_contract": endpoint,
        "applicability_census": {
            "formula_row_count": 63,
            "physical_sample_available_row_count": 0,
            "measured_gas_input_available_row_count": 0,
            "exact_curve_applicable_row_count": 0,
            "whole_formula_curve_applicable": False,
            "mixture_challenger_executable": False,
        },
        "scientific_surface": scientific_surface,
        "canonical_current_evidence": evidence,
        "blockers": blockers,
        "formula_action": contract.get("formula_action"),
        "physical_build_state": contract.get("physical_build_state"),
        "research_sample_state": contract.get("research_sample_state"),
        "measurement_execution_state": contract.get(
            "measurement_execution_state"
        ),
        "exact_curve_applicability_state": contract.get(
            "exact_curve_applicability_state"
        ),
        "authority": authority,
        "side_effects": side_effects,
    }
    return None, receipt


def _load_checkpoint8_intake_receipt(
    *,
    checkpoint7_protocol_sha256: str,
    checkpoint7_receipt: dict[str, Any],
) -> tuple[str | None, dict[str, Any] | None]:
    if not _R6_CP8_SENSORY_PROTOCOL.is_file():
        return "HOLD_CP8_SENSORY_PROTOCOL_UNAVAILABLE", None
    try:
        protocol = json.loads(
            _R6_CP8_SENSORY_PROTOCOL.read_text(encoding="utf-8")
        )
        inputs = dict(protocol["inputs"])
        scientific_surface = {
            key: dict(protocol["scientific_surface"][key])
            for key in (
                "hedonic_platform",
                "formulation_intelligence_contracts",
                "panel_contract",
                "sensory_source_manifest",
                "ma_2021_benchmark",
                "panel_contract_review",
                "legacy_hedonic_implementation",
                "optimizer_scoring_implementation",
            )
        }
        prerequisite = dict(protocol["checkpoint7_prerequisite"])
        external = {
            key: dict(protocol["external_evidence_boundary"][key])
            for key in ("bierling_2025", "ma_2021")
        }
        platform = dict(protocol["empty_hedonic_platform_contract"])
        panel = dict(protocol["panel_intake_contract"])
        endpoint = dict(protocol["endpoint_contract"])
        legacy = dict(protocol["legacy_heuristic_quarantine"])
        evidence = dict(protocol["canonical_current_evidence"])
        blockers = list(protocol["checkpoint8_blockers"])
        contract = dict(protocol["checkpoint8_contract"])
        authority = dict(protocol["authority"])
        side_effects = dict(protocol["side_effects"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return "HOLD_CP8_SENSORY_PROTOCOL_INVALID", None
    if authority != _CP8_AUTHORITY or side_effects != _CP8_SIDE_EFFECTS:
        return "HOLD_CP8_SENSORY_PROTOCOL_AUTHORITY_ESCALATION", None

    expected_surface_paths = {
        "hedonic_platform": (
            "engine/formulation_intelligence/hedonic_platform.py"
        ),
        "formulation_intelligence_contracts": (
            "engine/formulation_intelligence/contracts.py"
        ),
        "panel_contract": "engine/sensory/panel_contract.py",
        "sensory_source_manifest": (
            "data/source_manifests/optimizer_sensory_research_20260909.json"
        ),
        "ma_2021_benchmark": (
            "data/governance/"
            "ma_2021_binary_mixture_baseline_benchmark_20260812.json"
        ),
        "panel_contract_review": (
            "docs/research/"
            "PERFUME_CHEM_C0_SENSORY_PANEL_CONTRACT_2026-08-09.md"
        ),
        "legacy_hedonic_implementation": "engine/hedonic_model.py",
        "optimizer_scoring_implementation": "engine/optimizer/scoring.py",
    }
    surface_valid = True
    for key, relative_path in expected_surface_paths.items():
        path = _REPOSITORY_ROOT / relative_path
        record = scientific_surface[key]
        if (
            record.get("path") != relative_path
            or not path.is_file()
            or record.get("sha256") != stable_file_hash(path)
        ):
            surface_valid = False
            break

    expected_external = {
        "bierling_2025": {
            "source_id": "bierling_2025",
            "article_doi": "10.1038/s41597-025-04644-2",
            "dataset_doi": "10.5281/zenodo.14727277",
            "license": "CC BY 4.0",
            "included_participant_codes": 1227,
            "included_odor_codes": 73,
            "published_headline_odor_count": 74,
            "included_nonempty_numeric_pleasantness_rows": 12005,
            "pleasantness_scale": "1-100",
            "scope": "MONOMOLECULAR_ODORS_POPULATION_DATA",
            "mixture_level_liking_data": False,
            "systematic_multi_dose_response_data": False,
            "r6_formula_transfer_authorized": False,
            "r6_personal_liking_established": False,
        },
        "ma_2021": {
            "dataset_article_doi": "10.1016/j.dib.2021.107143",
            "same_source_intensity_doi": "10.1016/j.foodchem.2021.129483",
            "same_source_pleasantness_doi": "10.1093/chemse/bjaa020",
            "claim": "SOURCE_INTERNAL_CALIBRATION_ONLY",
            "unique_mixture_groups": 198,
            "source_trial_rows": 222,
            "best_predefined_pleasantness_baseline": (
                "pleasantness_squared_intensity_weighted"
            ),
            "best_predefined_pleasantness_rmse": "0.394525286290",
            "formula_prediction_authorized": False,
            "cross_study_generalization_authorized": False,
            "participant_level_inference_authorized": False,
            "sensory_claim_authorized": False,
            "r6_formula_transfer_authorized": False,
        },
    }
    expected_platform = {
        "schema_version": "hedonic_evidence_platform_v4",
        "target_scope": "lavande-ambre-profond-r6",
        "temporal_scope": "unresolved",
        "matrix_scope": "unresolved",
        "platform_sha256": (
            "999ead7dab43cb7b5ec26b1610d4c23311eaf4fb885f00db9b706d9fd6b3c336"
        ),
        "scope_sha256": (
            "14fbf97e65a18e0058af06d6aa508554a57856181adb9ded1e609fca0e9577c1"
        ),
        "assessment_sha256": (
            "c67c1f8122eed1cce59a667b8cda639a435299ff7925f74db2c9379e00b48a5a"
        ),
        "assessment_id": "hedonic-platform:a7442bbaa9e57360ced60d53",
        "authority_ceiling": "withheld",
        "view_count": 0,
        "decision_count": 0,
        "unknown_fact_count": 1,
        "native_criterion_count": 12,
        "all_native_criteria_unknown": True,
        "ranked_winner_available": False,
    }
    expected_binding_ids = [
        "sample_manifest",
        "preparation_dose_ppm_manifest",
        "formula_oav_manifest",
        "randomization_manifest",
        "anchor_reference_manifest",
        "participant_plan",
        "environment_timing_manifest",
        "analysis_plan",
        "ethics_privacy_safety_review",
    ]
    expected_panel = {
        "lexicon_sha256": (
            "5a0804a923cc312d9075ee8614cd1aa79941e65bba7bba35922f40148043c490"
        ),
        "draft_protocol_sha256": (
            "f795e561bf075a2a8ac4e7c7f131e87e37f9df3865b089068c403c2d40895441"
        ),
        "empty_exit_report_sha256": (
            "aaaf45a7b2a5c972593e20143ac1c6180f4ab4aa56c3b3df5d37fafef38a1bc3"
        ),
        "exit_decision": "hold",
        "protocol_locked": False,
        "required_binding_ids": expected_binding_ids,
        "required_binding_count": 9,
        "bound_binding_count": 0,
        "panel_gate_ids": ["discrimination", "agreement", "repeatability"],
        "locked_panel_gate_count": 0,
        "timepoints_seconds": [],
        "repeat_count": 0,
        "study_authorized": False,
        "release_authority": False,
        "model_calibration_authority": False,
    }
    expected_endpoint = {
        "construction_axes": [
            "airiness",
            "separability",
            "density",
            "coherence",
            "target_fidelity",
            "contrast",
            "emergence",
            "recognition",
        ],
        "pleasantness_endpoint": "pleasantness",
        "pairwise_liking_endpoint": "exact_condition_preference_outcome",
        "aversion_and_defect_endpoints_remain_separate": True,
        "blotter_and_skin_domains_remain_separate": True,
        "individual_and_population_liking_remain_separate": True,
        "unlike_endpoints_may_not_be_summed": True,
        "beauty_endpoint": "PROHIBITED_DERIVED_ENDPOINT",
        "pleasantness_state": "NOT_ESTABLISHED",
        "personal_liking_state": "NOT_TESTED",
        "population_liking_state": "NOT_TESTED",
    }
    expected_legacy = {
        "empty_input_score": 50,
        "empty_input_class": "unknown",
        "coverage_status": "NO_ACTIVE_MATERIALS",
        "classification": "HEURISTIC_DIAGNOSTIC_INDEX",
        "ranking_status": "WITHHELD",
        "formula_optimization_authority": False,
        "sensory_validation_status": "NOT_ESTABLISHED",
        "full_formula_pleasantness_status": "NOT_ESTABLISHED",
        "pleasantness_class_scope": "FIXED_VALENCE_TABLE_SUBSET_ONLY",
        "may_populate_hedonic_platform_observations": False,
        "may_select_or_rank_r6": False,
    }
    evidence_keys = {
        "physical_sample_receipts",
        "locked_protocol_receipts",
        "participant_qualification_receipts",
        "exact_condition_observations",
        "panel_performance_results",
        "criterion_preference_views",
        "population_preference_views",
        "pareto_decision_states",
    }
    cp7_evaluator_hash = (
        stable_file_hash(_R6_CP7_EVALUATOR)
        if _R6_CP7_EVALUATOR.is_file()
        else "MISSING"
    )
    if (
        protocol.get("schema_version")
        != "lavande-ambre-profond-r6-cp8-sensory-evidence-intake-v1"
        or protocol.get("state")
        != "FROZEN_NONEXECUTING_SENSORY_EVIDENCE_INTAKE_CONTRACT"
        or protocol.get("protocol_id")
        != "lavande-ambre-profond-r6-cp8-sensory-evidence-intake-20260926"
        or inputs.get("checkpoint7_protocol_path")
        != (
            "data/governance/"
            "lavande_ambre_profond_r6_cp7_research_applicability_intake_20260926.json"
        )
        or inputs.get("checkpoint7_protocol_sha256")
        != checkpoint7_protocol_sha256
        or inputs.get("checkpoint7_evaluator_path")
        != "engine/experiments/checkpoint7_readiness.py"
        or inputs.get("checkpoint7_evaluator_sha256") != cp7_evaluator_hash
        or inputs.get("checkpoint7_report_sha256")
        != "9b8d6e7b2897f01c889c8bd5493b9f2134f34c20ea4d1532cc9d366692e22d57"
        or checkpoint7_receipt.get("checkpoint7_state")
        != "SOFTWARE_COMPLETE_RESEARCH_APPLICABILITY_INTAKE_HOLD"
        or checkpoint7_receipt.get("research_applicability_state")
        != "HOLD_CP7_BUILD_MEASUREMENT_OR_APPLICABILITY_INCOMPLETE"
        or prerequisite
        != {
            "required_state": "PASS_CP7_R6_RESEARCH_SAMPLE_CHARACTERIZED",
            "observed_state": (
                "HOLD_CP7_BUILD_MEASUREMENT_OR_APPLICABILITY_INCOMPLETE"
            ),
            "satisfied": False,
            "bypass_allowed": False,
        }
        or not surface_valid
        or external != expected_external
        or platform != expected_platform
        or panel != expected_panel
        or endpoint != expected_endpoint
        or legacy != expected_legacy
        or set(evidence) != evidence_keys
        or any(not isinstance(value, list) or value for value in evidence.values())
        or blockers != _CP8_BLOCKERS
        or contract
        != {
            "state": "SOFTWARE_COMPLETE_SENSORY_EVIDENCE_INTAKE_HOLD",
            "hold_state": (
                "HOLD_CP8_PHYSICAL_STUDY_OR_EXACT_SCOPE_EVIDENCE_INCOMPLETE"
            ),
            "future_pass_state": (
                "PASS_CP8_R6_EXACT_SCOPE_SENSORY_EVIDENCE_RECORDED"
            ),
            "project_phase": (
                "SOFTWARE_CHECKPOINT_SEQUENCE_COMPLETE_EXTERNAL_VALIDATION_PENDING"
            ),
            "formula_action": "NO_CHANGE",
            "ranked_candidates": [],
            "best_observed_candidate": None,
            "experimental_recommendation": None,
            "shortlist_ordering": "UNORDERED_DIVERSE_SET",
            "formula_modified": False,
            "inventory_modified": False,
        }
    ):
        return "HOLD_CP8_SENSORY_PROTOCOL_DRIFT", None

    receipt = {
        "protocol_manifest_sha256": stable_file_hash(
            _R6_CP8_SENSORY_PROTOCOL
        ),
        "protocol_id": protocol.get("protocol_id"),
        "protocol_state": protocol.get("state"),
        "checkpoint8_state": contract.get("state"),
        "sensory_evidence_state": contract.get("hold_state"),
        "project_phase": contract.get("project_phase"),
        "checkpoint7_prerequisite": prerequisite,
        "external_evidence_boundary": external,
        "hedonic_platform_contract": platform,
        "panel_intake_contract": panel,
        "endpoint_contract": endpoint,
        "legacy_heuristic_quarantine": legacy,
        "evidence_census": {
            "physical_sample_receipt_count": 0,
            "locked_protocol_receipt_count": 0,
            "participant_qualification_receipt_count": 0,
            "exact_condition_observation_count": 0,
            "panel_performance_result_count": 0,
            "criterion_preference_view_count": 0,
            "population_preference_view_count": 0,
            "pareto_decision_state_count": 0,
            "ranked_candidate_count": 0,
        },
        "scientific_surface": scientific_surface,
        "canonical_current_evidence": evidence,
        "blockers": blockers,
        "formula_action": contract.get("formula_action"),
        "ranked_candidates": contract.get("ranked_candidates"),
        "best_observed_candidate": contract.get("best_observed_candidate"),
        "experimental_recommendation": contract.get(
            "experimental_recommendation"
        ),
        "shortlist_ordering": contract.get("shortlist_ordering"),
        "authority": authority,
        "side_effects": side_effects,
    }
    return None, receipt


def _shortlist(payload: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    if not _R5_COMPARATOR_MANIFEST.is_file():
        return _withheld_result(
            "HOLD_COMPARATOR_MANIFEST_UNAVAILABLE",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    actual_manifest_sha256 = stable_file_hash(_R5_COMPARATOR_MANIFEST)
    if payload["comparator_manifest_sha256"] != actual_manifest_sha256:
        return _withheld_result(
            "HOLD_COMPARATOR_MANIFEST_HASH_MISMATCH",
            expected_comparator_manifest_sha256=actual_manifest_sha256,
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    if not _R5_CP3_READINESS_PROTOCOL.is_file():
        return _withheld_result(
            "HOLD_CP3_READINESS_PROTOCOL_UNAVAILABLE",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    if not _R6_AIMI_DECISION.is_file() or not _R6_AIMI_SUCCESSOR.is_file():
        return _withheld_result(
            "HOLD_CP4_AIMI_SUCCESSOR_UNAVAILABLE",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    if (
        not _R6_CP5_INPUT_PROTOCOL.is_file()
        or not _R5_CP3_MEASUREMENT_SCHEMA.is_file()
    ):
        return _withheld_result(
            "HOLD_CP5_INPUT_PROTOCOL_UNAVAILABLE",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    if not _R6_CP6_LINEAGE_PROTOCOL.is_file():
        return _withheld_result(
            "HOLD_CP6_LINEAGE_PROTOCOL_UNAVAILABLE",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    try:
        readiness_protocol = json.loads(
            _R5_CP3_READINESS_PROTOCOL.read_text(encoding="utf-8")
        )
        readiness_inputs = dict(readiness_protocol["inputs"])
        readiness_predecessor = dict(readiness_protocol["predecessor"])
        readiness_authority = dict(readiness_protocol["authority"])
        readiness_stock = dict(readiness_protocol["stock_binding_review"])
        readiness_parent = dict(readiness_protocol["parent_search"])
        readiness_baseline = dict(readiness_protocol["baseline_decision_contract"])
        readiness_revision = dict(readiness_protocol["revision_decision_contract"])
        readiness_measurement = dict(
            readiness_protocol["measurement_protocol_contract"]
        )
        readiness_constant_total = dict(
            readiness_protocol["constant_total_basis_contract"]
        )
        readiness_blockers = list(readiness_protocol["blocker_order"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return _withheld_result(
            "HOLD_CP3_READINESS_PROTOCOL_INVALID",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    if any(value is not False for value in readiness_authority.values()):
        return _withheld_result(
            "HOLD_CP3_READINESS_PROTOCOL_AUTHORITY_ESCALATION",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    if (
        readiness_baseline.get("state") != "R5_STANDALONE_BASELINE_ACCEPTED"
        or readiness_baseline.get("parent_bytes_required_for_baseline") is not False
        or readiness_baseline.get("parent_equivalence_state")
        != "NOT_CLAIMED_STANDALONE_BASELINE"
        or readiness_baseline.get("r4_equivalence_claimed") is not False
        or readiness_baseline.get("r4_improvement_claimed") is not False
        or readiness_parent.get("required_for_standalone_baseline") is not False
        or readiness_parent.get("equivalence_claimed") is not False
        or readiness_parent.get("improvement_claimed") is not False
        or readiness_revision.get("formula_mutation_authorized") is not False
        or readiness_revision.get("exact_r5_build_claim_allowed") is not False
    ):
        return _withheld_result(
            "HOLD_CP3_BASELINE_DECISION_CONTRACT_DRIFT",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    governed_paths = (
        _R5_CP3_READINESS_PREDECESSOR,
        _R5_BASELINE_DECISION,
        _R5_STOCK_CONFIRMATION,
        _AROMA_MORE_PRODUCT_RESOLUTION,
        _R5_CURRENT_INVENTORY_OVERLAY,
        _INVENTORY_TEXT,
    )
    if not all(path.is_file() for path in governed_paths):
        return _withheld_result(
            "HOLD_CP3_READINESS_PROTOCOL_UNAVAILABLE",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    expected_predecessor = {
        "path": (
            "data/governance/"
            "lavande_ambre_profond_r5_cp3_readiness_protocol_20260924_v4.json"
        ),
        "sha256": stable_file_hash(_R5_CP3_READINESS_PREDECESSOR),
    }
    governed_input_hashes = {
        "inventory_text_sha256": stable_file_hash(_INVENTORY_TEXT),
        "inventory_overlay_sha256": stable_file_hash(
            _R5_CURRENT_INVENTORY_OVERLAY
        ),
        "stock_confirmation_receipt_sha256": stable_file_hash(
            _R5_STOCK_CONFIRMATION
        ),
        "aroma_more_product_resolution_sha256": stable_file_hash(
            _AROMA_MORE_PRODUCT_RESOLUTION
        ),
        "baseline_decision_receipt_sha256": stable_file_hash(
            _R5_BASELINE_DECISION
        ),
    }
    if readiness_predecessor != expected_predecessor or any(
        readiness_inputs.get(key) != value
        for key, value in governed_input_hashes.items()
    ):
        return _withheld_result(
            "HOLD_CP3_READINESS_PROTOCOL_DRIFT",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    if (
        readiness_inputs.get("design_comparator_manifest_sha256")
        != actual_manifest_sha256
    ):
        return _withheld_result(
            "HOLD_CP3_READINESS_PROTOCOL_DRIFT",
            expected_comparator_manifest_sha256=actual_manifest_sha256,
            protocol_comparator_manifest_sha256=readiness_inputs.get(
                "design_comparator_manifest_sha256"
            ),
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    readiness_protocol_sha256 = stable_file_hash(_R5_CP3_READINESS_PROTOCOL)
    try:
        aimi_decision = json.loads(_R6_AIMI_DECISION.read_text(encoding="utf-8"))
        aimi_successor = json.loads(_R6_AIMI_SUCCESSOR.read_text(encoding="utf-8"))
        aimi_decision_message = dict(aimi_decision["message_fact"])
        successor_parent = dict(aimi_successor["parent"])
        successor_cp3 = dict(aimi_successor["checkpoint3_protocol"])
        successor_decision = dict(aimi_successor["user_decision"])
        successor_replacement = dict(aimi_successor["row_replacement"])
        successor_row = dict(successor_replacement["successor_row"])
        successor_applicability = dict(aimi_successor["model_applicability"])
        successor_invariants = dict(aimi_successor["successor_invariants"])
        successor_contract = dict(aimi_successor["checkpoint4_contract"])
        successor_authority = dict(aimi_successor["authority"])
        successor_blockers = list(aimi_successor["blocker_order"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return _withheld_result(
            "HOLD_CP4_AIMI_SUCCESSOR_INVALID",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    aimi_decision_sha256 = stable_file_hash(_R6_AIMI_DECISION)
    aimi_successor_sha256 = stable_file_hash(_R6_AIMI_SUCCESSOR)
    if (
        aimi_successor.get("schema_version")
        != "lavande-ambre-profond-design-successor-delta-v1"
        or aimi_successor.get("state") != "ADMITTED_DESIGN_SUCCESSOR_ONLY"
        or successor_parent.get("sha256") != actual_manifest_sha256
        or successor_cp3.get("sha256") != readiness_protocol_sha256
        or successor_decision.get("sha256") != aimi_decision_sha256
        or aimi_decision_message.get("normalized_decision")
        != "USE_OWNED_GIVAUDAN_AIMI_IN_A_SEPARATELY_IDENTIFIED_R5_SUCCESSOR"
        or successor_replacement.get("source_row") != 47
        or successor_row.get("material") != "Givaudan AIMI"
        or successor_row.get("dose") != 50
        or successor_row.get("unit") != "µL"
        or successor_replacement.get("nominal_transfer_preserved") is not True
        or successor_replacement.get("chemical_active_equivalence_claimed")
        is not False
        or successor_replacement.get("sensory_equivalence_claimed") is not False
        or successor_replacement.get("oav_equivalence_claimed") is not False
        or successor_applicability.get("chemical_identity_state")
        != "HOLD_BOTTLE_TO_REFERENCE_IDENTITY_UNVERIFIED"
        or successor_authority.get("design_successor_record_authorized") is not True
        or any(
            value is not False
            for key, value in successor_authority.items()
            if key != "design_successor_record_authorized"
        )
    ):
        return _withheld_result(
            "HOLD_CP4_AIMI_SUCCESSOR_CONTRACT_DRIFT",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    try:
        cp5_protocol = json.loads(
            _R6_CP5_INPUT_PROTOCOL.read_text(encoding="utf-8")
        )
        cp5_inputs = dict(cp5_protocol["inputs"])
        cp5_gap_matrix = dict(cp5_protocol["gap_matrix_contract"])
        cp5_aimi_scope = dict(cp5_protocol["aimi_scope_contract"])
        cp5_constant_total = dict(cp5_protocol["constant_total_basis_contract"])
        cp5_sub_10 = dict(cp5_protocol["sub_10_ul_contract"])
        cp5_sub_10_rows = [dict(row) for row in cp5_sub_10["rows"]]
        cp5_measurement = dict(cp5_protocol["measurement_protocol_contract"])
        cp5_measurement_endpoints = dict(cp5_measurement["endpoints"])
        cp5_ownership = {
            key: list(cp5_protocol["blocker_ownership"][key])
            for key in _CP5_BLOCKER_OWNERSHIP
        }
        cp5_contract = dict(cp5_protocol["checkpoint5_contract"])
        cp5_authority = dict(cp5_protocol["authority"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return _withheld_result(
            "HOLD_CP5_INPUT_PROTOCOL_INVALID",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    if cp5_authority != _CP5_AUTHORITY:
        return _withheld_result(
            "HOLD_CP5_INPUT_PROTOCOL_AUTHORITY_ESCALATION",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    expected_cp5_paths = {
        "r6_successor_path": (
            "data/governance/"
            "lavande_ambre_profond_r6_aimi_design_successor_20260926.json"
        ),
        "checkpoint3_protocol_path": (
            "data/governance/"
            "lavande_ambre_profond_r5_cp3_readiness_protocol_20260926_v5.json"
        ),
        "measurement_schema_path": (
            "data/governance/"
            "lavande_ambre_profond_r5_cp3_readiness_protocol_20260924.json"
        ),
        "inventory_text_path": "inventory.txt",
    }
    expected_sub_10_rows = [
        (20, "Haitian Vetiver EO", "5", "UNRESOLVED"),
        (43, "Linalool Oxide", "5", "UNRESOLVED"),
        (68, "Rosemary EO", "5", "UNRESOLVED"),
    ]
    actual_sub_10_rows = [
        (
            row.get("source_row"),
            row.get("material"),
            str(row.get("nominal_amount_ul")),
            row.get("route_state"),
        )
        for row in cp5_sub_10_rows
    ]
    cp5_measurement_schema_sha256 = stable_file_hash(
        _R5_CP3_MEASUREMENT_SCHEMA
    )
    cp5_protocol_sha256 = stable_file_hash(_R6_CP5_INPUT_PROTOCOL)
    if (
        cp5_protocol.get("schema_version")
        != "lavande-ambre-profond-r6-cp5-execution-input-protocol-v1"
        or cp5_protocol.get("state")
        != "FROZEN_NONEXECUTABLE_INPUT_COLLECTION_CONTRACT"
        or any(cp5_inputs.get(key) != value for key, value in expected_cp5_paths.items())
        or cp5_inputs.get("r6_successor_sha256") != aimi_successor_sha256
        or cp5_inputs.get("r6_successor_rows_sha256")
        != successor_invariants.get("successor_canonical_rows_sha256")
        or cp5_inputs.get("checkpoint3_protocol_sha256")
        != readiness_protocol_sha256
        or cp5_inputs.get("measurement_schema_sha256")
        != cp5_measurement_schema_sha256
        or cp5_inputs.get("inventory_text_sha256")
        != stable_file_hash(_INVENTORY_TEXT)
        or cp5_gap_matrix.get("required_row_count") != 63
        or cp5_gap_matrix.get("binding_candidates_are_execution_authority")
        is not False
        or cp5_gap_matrix.get("missing_values_are_never_imputed") is not True
        or cp5_gap_matrix.get("mass_volume_never_summed") is not True
        or cp5_aimi_scope.get("stock_id")
        != "inventory:user-20260904:a45ff6250b56cec5bbad"
        or cp5_aimi_scope.get("scope_state")
        != "BOTTLE_SPECIFIC_EMPIRICAL_REQUIRED"
        or cp5_aimi_scope.get("reference_disposition")
        != "REFERENCE_NOT_USED_FOR_QUANTITATIVE_APPLICABILITY"
        or cp5_aimi_scope.get("reference_linked_properties_allowed") is not False
        or cp5_aimi_scope.get("family_or_description_equivalence_allowed")
        is not False
        or cp5_aimi_scope.get("supplier_reference_proves_owned_bottle_identity")
        is not False
        or cp5_constant_total.get("state")
        != "HOLD_ROW_CONVERSION_INPUTS_AND_DERIVED_TOTAL_MISSING"
        or cp5_constant_total.get("selected_basis") != "active_mass_g"
        or cp5_constant_total.get("constant_total_amount_decimal") is not None
        or cp5_constant_total.get("conversion_inputs_complete") is not False
        or cp5_constant_total.get("generic_density_allowed") is not False
        or cp5_constant_total.get("solid_mass_kept_separate") is not True
        or cp5_constant_total.get("mass_volume_never_summed") is not True
        or cp5_sub_10.get("state") != "HOLD_SUB_10_UL_ROUTES_UNRESOLVED"
        or cp5_sub_10.get("working_stock_preparation_authorized") is not False
        or cp5_sub_10.get("direct_measurement_authorized") is not False
        or actual_sub_10_rows != expected_sub_10_rows
        or cp5_measurement.get("state")
        != "R6_SCHEMA_FROZEN_EXECUTION_PARAMETERS_UNRESOLVED"
        or cp5_measurement.get("execution_ready") is not False
        or cp5_measurement.get("documentary_r5_is_physical_comparator")
        is not False
        or cp5_measurement.get("domains_must_remain_separate")
        != ["BLOTTER", "SKIN"]
        or cp5_measurement.get("resolved_execution_parameters") != {}
        or cp5_measurement_endpoints
        != {
            "physical_release": "SEPARATE_ENDPOINT",
            "sensory_intensity": "SEPARATE_ENDPOINT",
            "character": "SEPARATE_ENDPOINT",
            "pleasantness": "NOT_ESTABLISHED",
            "personal_liking": "NOT_TESTED",
            "population_liking": "NOT_TESTED",
            "beauty": "PROHIBITED_DERIVED_ENDPOINT",
        }
        or cp5_ownership != _CP5_BLOCKER_OWNERSHIP
        or cp5_contract.get("state")
        != "SOFTWARE_COMPLETE_INPUT_COLLECTION_HOLD"
        or cp5_contract.get("hold_state") != "HOLD_CP5_INPUTS_INCOMPLETE"
        or cp5_contract.get("formula_action") != "DESIGN_SUCCESSOR_UNCHANGED"
        or cp5_contract.get("physical_build_state")
        != "HOLD_NO_BUILD_PLAN_BINDING"
        or cp5_contract.get("physical_formula_modified") is not False
        or cp5_contract.get("inventory_modified") is not False
    ):
        return _withheld_result(
            "HOLD_CP5_INPUT_PROTOCOL_DRIFT",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    try:
        cp6_protocol = json.loads(
            _R6_CP6_LINEAGE_PROTOCOL.read_text(encoding="utf-8")
        )
        cp6_inputs = dict(cp6_protocol["inputs"])
        cp6_implementation = {
            key: dict(cp6_protocol["implementation_surface"][key])
            for key in (
                "physical_lineage_service",
                "physical_lineage_schema",
                "physical_lineage_model",
                "physical_lineage_migration",
            )
        }
        cp6_prerequisite = dict(cp6_protocol["checkpoint5_prerequisite"])
        cp6_boundary = dict(cp6_protocol["candidate_identity_boundary"])
        cp6_evidence_schema = dict(cp6_protocol["documentary_evidence_schema"])
        cp6_preparations = [
            dict(row) for row in cp6_protocol["required_child_stock_preparations"]
        ]
        cp6_sub_10_routes = [
            dict(row) for row in cp6_protocol["required_sub_10_ul_routes"]
        ]
        cp6_evidence = dict(cp6_protocol["canonical_current_evidence"])
        cp6_interface_audit = dict(cp6_protocol["operational_interface_audit"])
        cp6_supported_invariants = list(
            cp6_interface_audit["supported_invariants"]
        )
        cp6_admission_gaps = list(cp6_interface_audit["admission_gaps"])
        cp6_blockers = list(cp6_protocol["checkpoint6_blockers"])
        cp6_contract = dict(cp6_protocol["checkpoint6_contract"])
        cp6_authority = dict(cp6_protocol["authority"])
        cp6_side_effects = dict(cp6_protocol["side_effects"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return _withheld_result(
            "HOLD_CP6_LINEAGE_PROTOCOL_INVALID",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    if cp6_authority != _CP6_AUTHORITY or cp6_side_effects != _CP6_SIDE_EFFECTS:
        return _withheld_result(
            "HOLD_CP6_LINEAGE_PROTOCOL_AUTHORITY_ESCALATION",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )

    expected_cp6_implementation_paths = {
        "physical_lineage_service": "backend/app/services/physical_lineage.py",
        "physical_lineage_schema": "backend/app/schemas/physical_lineage.py",
        "physical_lineage_model": "backend/app/models/lab_cp2_physical.py",
        "physical_lineage_migration": (
            "backend/alembic/versions/20260923_0017_cp2_physical_lineage.py"
        ),
    }
    approved_cp6_transitions = _approved_legacy_surface_transitions(
        "ADDITIVE_PHYSICAL_LINEAGE_EXTENSION"
    )
    cp6_implementation_valid = True
    for key, relative_path in expected_cp6_implementation_paths.items():
        path = _REPOSITORY_ROOT / relative_path
        record = cp6_implementation[key]
        current_sha256 = stable_file_hash(path) if path.is_file() else None
        exact_match = record.get("sha256") == current_sha256
        approved_transition = (
            relative_path,
            str(record.get("sha256")),
            str(current_sha256),
        ) in approved_cp6_transitions
        if (
            record.get("path") != relative_path
            or not path.is_file()
            or not (exact_match or approved_transition)
        ):
            cp6_implementation_valid = False
            break

    expected_cp6_evidence_keys = {
        "bottle_lot_receipts",
        "backend_stock_mapping_receipts",
        "liquid_conversion_receipts",
        "child_stock_preparation_receipts",
        "sub_10_ul_route_receipts",
        "build_plan_bindings",
        "inventory_reservations",
    }
    expected_cp6_preparations = [
        (
            31,
            "Heliotropal / piperonal",
            "inventory:v5:593f575b080f30401f9b",
            "0.1",
            "W_W",
            "DPG",
            "MISSING",
        ),
        (
            59,
            "Black Pepper EO",
            "inventory:v5:4bb69da9b62fe8fbd8bb",
            "0.1",
            "V_V",
            "ethanol",
            "MISSING",
        ),
        (
            63,
            "Nutmeg EO",
            "inventory:user-20260830:caa7c7f7418d43c86660",
            "0.1",
            "V_V",
            "ethanol",
            "MISSING",
        ),
    ]
    actual_cp6_preparations = [
        (
            row.get("source_row"),
            row.get("material"),
            row.get("parent_candidate_stock_id"),
            str(row.get("target_fraction_decimal")),
            row.get("target_basis"),
            row.get("target_carrier"),
            row.get("receipt_state"),
        )
        for row in cp6_preparations
    ]
    expected_cp6_sub_10_routes = [
        (20, "Haitian Vetiver EO", "5", "MISSING"),
        (43, "Linalool Oxide", "5", "MISSING"),
        (68, "Rosemary EO", "5", "MISSING"),
    ]
    actual_cp6_sub_10_routes = [
        (
            row.get("source_row"),
            row.get("material"),
            str(row.get("nominal_amount_ul")),
            row.get("route_receipt_state"),
        )
        for row in cp6_sub_10_routes
    ]
    expected_cp6_required_fields = {
        "required_bottle_lot_fields": [
            "source_row",
            "candidate_stock_id",
            "bottle_id",
            "lot_or_batch_id",
            "label_evidence_sha256",
            "supplier_or_preparer",
            "captured_at",
            "reviewer",
            "admission_receipt_id",
        ],
        "required_backend_stock_mapping_fields": [
            "source_row",
            "candidate_stock_id",
            "backend_stock_solution_id",
            "identity_evidence_sha256",
            "admission_receipt_id",
        ],
        "required_density_fields": [
            "source_row",
            "candidate_stock_id",
            "density_g_ml_decimal",
            "temperature_c_decimal",
            "method",
            "standard_uncertainty_decimal",
            "provenance_sha256",
            "admission_receipt_id",
        ],
        "required_weighed_mass_fields": [
            "source_row",
            "candidate_stock_id",
            "target_weighed_stock_mass_g_decimal",
            "method",
            "standard_uncertainty_g_decimal",
            "measurement_receipt_sha256",
            "admission_receipt_id",
        ],
    }
    if (
        cp6_protocol.get("schema_version")
        != "lavande-ambre-profond-r6-cp6-physical-lineage-intake-v1"
        or cp6_protocol.get("state")
        != "FROZEN_NONEXECUTING_DOCUMENTARY_INTAKE_CONTRACT"
        or cp6_inputs.get("checkpoint5_protocol_path")
        != (
            "data/governance/"
            "lavande_ambre_profond_r6_cp5_execution_input_protocol_20260926.json"
        )
        or cp6_inputs.get("checkpoint5_protocol_sha256") != cp5_protocol_sha256
        or cp6_inputs.get("checkpoint5_evaluator_path")
        != "engine/experiments/checkpoint5_readiness.py"
        or not _R6_CP5_EVALUATOR.is_file()
        or cp6_inputs.get("checkpoint5_evaluator_sha256")
        != stable_file_hash(_R6_CP5_EVALUATOR)
        or cp6_inputs.get("checkpoint5_report_sha256")
        != "0c3716c889c2f84827b16597865ef63ef462fc9e2dae4d701d303c9d11a54111"
        or cp6_inputs.get("r6_successor_rows_sha256")
        != successor_invariants.get("successor_canonical_rows_sha256")
        or cp6_inputs.get("inventory_text_sha256")
        != cp5_inputs.get("inventory_text_sha256")
        or cp6_inputs.get("inventory_snapshot_sha256")
        != cp5_inputs.get("inventory_snapshot_sha256")
        or cp6_inputs.get("inventory_overlay_sha256")
        != cp5_inputs.get("inventory_overlay_sha256")
        or not cp6_implementation_valid
        or cp6_prerequisite
        != {
            "required_state": "PASS_CP5_INPUTS_FROZEN_NONEXECUTABLE",
            "observed_state": "HOLD_CP5_INPUTS_INCOMPLETE",
            "satisfied": False,
            "bypass_allowed": False,
        }
        or cp6_boundary.get("candidate_field") != "intended_stock_id"
        or cp6_boundary.get("required_bridge")
        != "ADJUDICATED_INVENTORY_CANDIDATE_TO_BACKEND_STOCK_MAPPING_RECEIPT"
        or cp6_boundary.get("automatic_namespace_translation_allowed") is not False
        or any(
            cp6_boundary.get(key) is not False
            for key in (
                "candidate_is_backend_stock_solution_id",
                "candidate_is_bottle_lot_receipt",
                "candidate_is_preparation_receipt",
                "candidate_is_physical_binding",
            )
        )
        or cp6_evidence_schema.get("required_source_row_count") != 63
        or cp6_evidence_schema.get("bottle_lot_receipt_required_for_every_row")
        is not True
        or cp6_evidence_schema.get("backend_stock_mapping_required_for_every_row")
        is not True
        or cp6_evidence_schema.get(
            "liquid_conversion_evidence_required_row_count"
        )
        != 62
        or cp6_evidence_schema.get("solid_direct_mass_row_count") != 1
        or cp6_evidence_schema.get("allowed_liquid_conversion_routes")
        != [
            "LOT_SPECIFIC_DENSITY_WITH_IMMUTABLE_PROVENANCE",
            "EXACT_TARGET_WEIGHED_STOCK_MASS",
        ]
        or cp6_evidence_schema.get("generic_density_allowed") is not False
        or cp6_evidence_schema.get("mass_volume_never_summed") is not True
        or cp6_evidence_schema.get("missing_values_are_never_imputed") is not True
        or cp6_evidence_schema.get(
            "documentary_completion_is_not_execution_authority"
        )
        is not True
        or any(
            cp6_evidence_schema.get(key) != value
            for key, value in expected_cp6_required_fields.items()
        )
        or actual_cp6_preparations != expected_cp6_preparations
        or actual_cp6_sub_10_routes != expected_cp6_sub_10_routes
        or set(cp6_evidence) != expected_cp6_evidence_keys
        or any(not isinstance(value, list) or value for value in cp6_evidence.values())
        or cp6_supported_invariants != _CP6_SUPPORTED_INVARIANTS
        or cp6_admission_gaps != _CP6_ADMISSION_GAPS
        or cp6_interface_audit.get(
            "operational_service_calls_allowed_in_checkpoint6"
        )
        is not False
        or cp6_interface_audit.get("persistent_api_changes_allowed_in_checkpoint6")
        is not False
        or cp6_blockers != _CP6_BLOCKERS
        or cp6_contract
        != {
            "state": "SOFTWARE_COMPLETE_DOCUMENTARY_INTAKE_HOLD",
            "hold_state": "HOLD_CP6_PHYSICAL_LINEAGE_INPUTS_INCOMPLETE",
            "future_pass_state": "PASS_CP6_PHYSICAL_READINESS_BOUND_NOT_COMPOUNDED",
            "formula_action": "DESIGN_SUCCESSOR_UNCHANGED",
            "all_line_documentary_preconditions_complete": False,
            "physical_binding_state": "NOT_CREATED",
            "reservation_state": "NOT_CREATED",
            "compounding_state": "NOT_STARTED",
            "formula_modified": False,
            "inventory_modified": False,
        }
    ):
        return _withheld_result(
            "HOLD_CP6_LINEAGE_PROTOCOL_DRIFT",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    cp6_protocol_sha256 = stable_file_hash(_R6_CP6_LINEAGE_PROTOCOL)
    cp7_error, cp7_receipt = _load_checkpoint7_intake_receipt(
        checkpoint6_protocol_sha256=cp6_protocol_sha256,
        checkpoint5_protocol_sha256=cp5_protocol_sha256,
        checkpoint6_inputs=cp6_inputs,
        checkpoint5_measurement=cp5_measurement,
    )
    if cp7_error is not None or cp7_receipt is None:
        return _withheld_result(
            cp7_error or "HOLD_CP7_RESEARCH_PROTOCOL_INVALID",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    cp8_error, cp8_receipt = _load_checkpoint8_intake_receipt(
        checkpoint7_protocol_sha256=stable_file_hash(
            _R6_CP7_RESEARCH_PROTOCOL
        ),
        checkpoint7_receipt=cp7_receipt,
    )
    if cp8_error is not None or cp8_receipt is None:
        return _withheld_result(
            cp8_error or "HOLD_CP8_SENSORY_PROTOCOL_INVALID",
            ranked_candidates=[],
            best_observed_candidate=None,
            experimental_recommendation=None,
            shortlist_ordering="UNORDERED_DIVERSE_SET",
            inventory_modified=False,
        )
    manifest = json.loads(_R5_COMPARATOR_MANIFEST.read_text(encoding="utf-8"))
    comparator_state = dict(manifest["checkpoint_2_state"])
    if cp5_constant_total.get("conversion_inputs_complete") is not True:
        state = "HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING"
    elif payload["constant_total_basis"] == "UNRESOLVED":
        state = "HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED"
    else:
        state = "WITHHELD_NONDISCRIMINATING_EVIDENCE"
    return (
        "WITHHELD",
        {
            "selection_status": state,
            "ranked_candidates": [],
            "best_observed_candidate": None,
            "experimental_recommendation": None,
            "shortlist_ordering": "UNORDERED_DIVERSE_SET",
            "formula_action": "NO_CHANGE",
            "formula_modified": False,
            "inventory_modified": False,
            "predicted_liking": None,
            "comparator_manifest_sha256": actual_manifest_sha256,
            "comparator_id": manifest["comparator_id"],
            "comparator_state": comparator_state,
            "checkpoint3_protocol_manifest_sha256": readiness_protocol_sha256,
            "checkpoint3_readiness": {
                "protocol_state": readiness_protocol.get("state"),
                "baseline_state": readiness_baseline.get("state"),
                "parent_equivalence_state": readiness_baseline.get(
                    "parent_equivalence_state"
                ),
                "revision_state": readiness_revision.get("state"),
                "stock_binding_state": readiness_stock.get("state"),
                "constant_total_basis_state": readiness_constant_total.get("state"),
                "constant_total_basis": readiness_constant_total,
                "measurement_protocol_state": readiness_measurement.get("state"),
                "blockers": readiness_blockers,
                "authority": readiness_authority,
            },
            "checkpoint4_successor": {
                "successor_manifest_sha256": aimi_successor_sha256,
                "successor_id": aimi_successor.get("successor_id"),
                "state": successor_contract.get("state"),
                "formula_action": successor_contract.get("formula_action"),
                "substitution_state": "AIMI_SELECTED_NOMINAL_50_UL_TRANSFER",
                "active_equivalence_state": (
                    "NOT_CLAIMED_INTENDED_MATERIAL_CHANGE"
                ),
                "successor_rows_sha256": successor_invariants.get(
                    "successor_canonical_rows_sha256"
                ),
                "model_applicability": successor_applicability,
                "blockers": successor_blockers,
                "authority": successor_authority,
            },
            "checkpoint5_input_freeze": {
                "protocol_manifest_sha256": cp5_protocol_sha256,
                "protocol_id": cp5_protocol.get("protocol_id"),
                "protocol_state": cp5_protocol.get("state"),
                "checkpoint5_state": cp5_contract.get("state"),
                "input_completion_state": cp5_contract.get("hold_state"),
                "formula_action": cp5_contract.get("formula_action"),
                "aimi_scope": cp5_aimi_scope,
                "constant_total_basis": cp5_constant_total,
                "sub_10_ul_contract": cp5_sub_10,
                "measurement_protocol_state": cp5_measurement.get("state"),
                "blocker_ownership": cp5_ownership,
                "authority": cp5_authority,
            },
            "checkpoint6_documentary_intake": {
                "protocol_manifest_sha256": cp6_protocol_sha256,
                "protocol_id": cp6_protocol.get("protocol_id"),
                "protocol_state": cp6_protocol.get("state"),
                "checkpoint6_state": cp6_contract.get("state"),
                "documentary_input_completion_state": cp6_contract.get(
                    "hold_state"
                ),
                "checkpoint5_prerequisite": cp6_prerequisite,
                "candidate_identity_boundary": cp6_boundary,
                "documentary_evidence_schema": cp6_evidence_schema,
                "documentary_census": {
                    "candidate_stock_row_count": 63,
                    "row_documentary_preconditions_complete_count": 0,
                    "physical_binding_eligible_row_count": 0,
                    "bottle_lot_receipt_missing_row_count": 63,
                    "backend_stock_mapping_missing_row_count": 63,
                    "liquid_conversion_missing_row_count": 62,
                    "child_stock_preparation_missing_row_count": 3,
                    "sub_10_ul_route_missing_row_count": 3,
                },
                "required_child_stock_preparations": cp6_preparations,
                "required_sub_10_ul_routes": cp6_sub_10_routes,
                "canonical_current_evidence": cp6_evidence,
                "operational_interface_audit": {
                    "supported_invariants": cp6_supported_invariants,
                    "admission_gaps": cp6_admission_gaps,
                    "operational_service_calls_allowed_in_checkpoint6": False,
                    "persistent_api_changes_allowed_in_checkpoint6": False,
                },
                "implementation_surface": cp6_implementation,
                "blockers": cp6_blockers,
                "formula_action": cp6_contract.get("formula_action"),
                "physical_binding_state": cp6_contract.get(
                    "physical_binding_state"
                ),
                "reservation_state": cp6_contract.get("reservation_state"),
                "compounding_state": cp6_contract.get("compounding_state"),
                "authority": cp6_authority,
                "side_effects": cp6_side_effects,
            },
            "checkpoint7_research_applicability_intake": cp7_receipt,
            "checkpoint8_sensory_evidence_intake": cp8_receipt,
            **_FALSE_AUTHORITY,
        },
        state,
    )


def _v2_envelope(
    *,
    validation_state: str,
    applicability_state: str,
    result: dict[str, Any],
    missing_requirements: list[Any] | None = None,
    findings: list[Any] | None = None,
) -> dict[str, Any]:
    """Return the common authority-false v2 result envelope."""

    return {
        "schema_version": "lab-engine-result-envelope-v2",
        "validation": {
            "state": validation_state,
            "applicability_state": applicability_state,
            "findings": findings or [],
            "missing_requirements": missing_requirements or [],
            "processing_allowed": validation_state
            in {"ADVISORY_COMPLETE", "ADVISORY_FINDINGS"},
        },
        "endpoint_results": result.pop("endpoint_results", []),
        "selection": result.pop(
            "selection",
            {
                "status": "NOT_REQUESTED",
                "ranked_candidates": [],
                "pareto_candidates": [],
                "unordered_candidates": [],
                "formula_action": "NO_CHANGE",
                "reason_codes": [],
            },
        ),
        "result": result,
        "authority": {
            "scientific_claim_scope": "ADVISORY_EVIDENCE_ONLY",
            **FALSE_ACTION_AUTHORITY,
        },
        **_FALSE_AUTHORITY,
    }


def _release_simulation_v2(
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any], str]:
    scenario = ReleaseScenarioV1(
        **{
            **payload["scenario"],
            "timepoints_seconds": tuple(payload["scenario"]["timepoints_seconds"]),
        }
    )
    parameters = FiniteReleaseParametersV1(
        **{
            **payload["parameters"],
            "matrix_ids": tuple(payload["parameters"]["matrix_ids"]),
            "supported_substrates": tuple(
                payload["parameters"]["supported_substrates"]
            ),
        }
    )
    components = tuple(ReleaseComponentV1(**row) for row in payload["components"])
    release = simulate_finite_release(
        components,
        scenario=scenario,
        parameters=parameters,
    )
    validation = str(release["validation_state"])
    terminal = (
        "SUCCEEDED"
        if validation in {"ADVISORY_COMPLETE", "ADVISORY_FINDINGS"}
        else "WITHHELD"
    )
    envelope = _v2_envelope(
        validation_state=validation,
        applicability_state=str(release["applicability_state"]),
        missing_requirements=list(release.get("missing_requirements", [])),
        findings=[{"code": code} for code in release.get("reason_codes", [])],
        result={
            "formula_sha256": payload["formula_sha256"],
            "release_trajectory": release,
            "formula_action": "NO_CHANGE",
        },
    )
    return terminal, envelope, validation


def _candidate_from_payload(row: dict[str, Any]) -> OfflineCandidateV1:
    return OfflineCandidateV1(
        candidate_id=row["candidate_id"],
        variables=row["variables"],
        endpoint_value=row["endpoint_value"],
        prediction_interval=tuple(row["prediction_interval"]),
        coverage_decimal=row["coverage_decimal"],
        applicability_state=row["applicability_state"],
        feature_lineage=tuple(row["feature_lineage"]),
        model_signs=row["model_signs"],
    )


def _candidate_evaluation_v2(
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any], str]:
    candidate = _candidate_from_payload(payload["candidate"])
    applicable = candidate.applicability_state == "APPLICABLE"
    validation = "ADVISORY_COMPLETE" if applicable else "WITHHOLD_UNKNOWN"
    endpoint_result = {
        "candidate_id": candidate.candidate_id,
        "formula_sha256": payload["candidate"].get("formula_sha256"),
        "endpoint": payload["endpoint_id"],
        "value": candidate.endpoint_value if applicable else None,
        "units": "endpoint-native",
        "coverage": candidate.coverage_decimal,
        "applicability": candidate.applicability_state,
        "uncertainty": list(candidate.prediction_interval),
        "provenance": list(candidate.feature_lineage),
        "model_version": "caller-observation-server-validated-v2",
    }
    envelope = _v2_envelope(
        validation_state=validation,
        applicability_state=candidate.applicability_state,
        findings=([] if applicable else [{"code": "CANDIDATE_NOT_APPLICABLE"}]),
        result={
            "endpoint_results": [endpoint_result],
            "candidate": candidate.as_dict(),
            "formula_action": "NO_CHANGE",
        },
    )
    return ("SUCCEEDED" if applicable else "WITHHELD"), envelope, validation


def _shortlist_v2(payload: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    candidates = [_candidate_from_payload(row) for row in payload["candidates"]]
    lower_is_better = bool(payload["lower_is_better"])
    direction = 1.0 if lower_is_better else -1.0
    reasons: list[str] = []
    if any(row.applicability_state != "APPLICABLE" for row in candidates):
        reasons.append("CANDIDATE_OUT_OF_DOMAIN")
    if len({row.coverage_decimal for row in candidates}) != 1:
        reasons.append("CANDIDATE_COVERAGE_DIFFERS")
    if any(
        len({sign for sign in row.model_signs.values() if sign != 0}) > 1
        for row in candidates
    ):
        reasons.append("MODEL_SIGNS_DISAGREE")
    ordered = sorted(
        candidates,
        key=lambda row: (direction * row.endpoint_value, row.candidate_id),
    )
    separated = all(
        (
            left.prediction_interval[1] < right.prediction_interval[0]
            if lower_is_better
            else left.prediction_interval[0] > right.prediction_interval[1]
        )
        for left, right in zip(ordered, ordered[1:])
    )
    if len(ordered) > 1 and not separated:
        reasons.append("UNCERTAINTY_INTERVALS_NONDISCRIMINATING")
    withheld = bool(reasons)
    validation = "WITHHOLD_UNKNOWN" if withheld else "ADVISORY_COMPLETE"
    selection = {
        "status": (
            "WITHHELD_NONDISCRIMINATING_EVIDENCE"
            if withheld
            else "SUPPORTED_ENDPOINT_ORDERING"
        ),
        "ranked_candidates": [] if withheld else [row.as_dict() for row in ordered],
        "pareto_candidates": [],
        "unordered_candidates": (
            sorted(row.candidate_id for row in candidates) if withheld else []
        ),
        "formula_action": "NO_CHANGE" if withheld else "PROPOSE_ONLY",
        "reason_codes": sorted(set(reasons)),
    }
    envelope = _v2_envelope(
        validation_state=validation,
        applicability_state="PARTIAL" if withheld else "APPLICABLE",
        findings=[{"code": code} for code in reasons],
        result={
            "endpoint_id": payload["endpoint_id"],
            "selection": selection,
        },
    )
    return ("WITHHELD" if withheld else "SUCCEEDED"), envelope, validation


def _optimizer_search_v2(
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any], str]:
    benchmark = compare_search_arms(
        tuple(_candidate_from_payload(row) for row in payload["candidates"]),
        baseline_id=payload["baseline_id"],
        endpoint_id=payload["endpoint_id"],
        budget_per_arm=payload["budget_per_arm"],
        seeds=tuple(payload["seeds"]),
        minimize=payload["minimize"],
    )
    supported = benchmark["selection_status"] == "SUPPORTED_ENDPOINT_ORDERING"
    validation = "ADVISORY_COMPLETE" if supported else "WITHHOLD_UNKNOWN"
    selection = {
        "status": benchmark["selection_status"],
        "ranked_candidates": benchmark.get("ranked_candidates", []),
        "pareto_candidates": benchmark.get("pareto_candidates", []),
        "unordered_candidates": benchmark.get("unordered_candidates", []),
        "formula_action": benchmark.get("formula_action", "NO_CHANGE"),
        "reason_codes": benchmark.get("reason_codes", []),
    }
    envelope = _v2_envelope(
        validation_state=validation,
        applicability_state="APPLICABLE" if supported else "PARTIAL",
        findings=[
            {"code": code} for code in benchmark.get("reason_codes", [])
        ],
        result={
            "search_id": payload["search_id"],
            "benchmark": benchmark,
            "selection": selection,
        },
    )
    return ("SUCCEEDED" if supported else "WITHHELD"), envelope, validation


def _preference_analysis_v2(
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any], str]:
    comparisons = tuple(PairwisePreference(**row) for row in payload["comparisons"])
    fitted = fit_davidson_personal_preference(
        comparisons,
        criterion_id=payload["criterion_id"],
        config=DavidsonFitConfigV1(
            minimum_comparisons=payload["minimum_comparisons"],
            minimum_sessions=payload["minimum_sessions"],
            regularization=payload["regularization"],
            bootstrap_replicates=payload["bootstrap_replicates"],
            bootstrap_seed=payload["bootstrap_seed"],
        ),
    )
    usable = fitted["status"] == "DIAGNOSTIC_PERSONAL_EVIDENCE"
    validation = "ADVISORY_FINDINGS" if usable else "WITHHOLD_UNKNOWN"
    envelope = _v2_envelope(
        validation_state=validation,
        applicability_state="PARTIAL" if usable else "UNAVAILABLE",
        findings=[{"code": code} for code in fitted.get("reason_codes", [])],
        result={
            "analysis_id": payload["analysis_id"],
            "personal_preference": fitted,
            "formula_action": "NO_CHANGE",
        },
    )
    return ("SUCCEEDED" if usable else "WITHHELD"), envelope, validation


def _batch_gate_v2(payload: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    expected_hash = stable_json_hash(
        {
            "schema_version": "engine-batch-corpus-v2",
            "formulas": payload["formulas"],
        }
    )
    if expected_hash != payload["frozen_corpus_sha256"]:
        validation = "INVALID_INPUT"
        envelope = _v2_envelope(
            validation_state=validation,
            applicability_state="UNAVAILABLE",
            findings=[{"code": "FROZEN_CORPUS_HASH_MISMATCH"}],
            result={
                "corpus_id": payload["corpus_id"],
                "server_corpus_sha256": expected_hash,
                "formula_action": "NO_CHANGE",
            },
        )
        return "WITHHELD", envelope, validation
    results = []
    for index, formula in enumerate(payload["formulas"]):
        terminal, result, validation = _release_gate(formula)
        results.append(
            {
                "discovery_index": index,
                "formula_id": formula["formula_id"],
                "terminal_state": terminal,
                "validation_state": validation,
                "result_sha256": stable_json_hash(result),
                "result": result,
            }
        )
    results.sort(key=lambda row: row["discovery_index"])
    all_succeeded = all(row["terminal_state"] == "SUCCEEDED" for row in results)
    validation = "ADVISORY_COMPLETE" if all_succeeded else "ADVISORY_FINDINGS"
    envelope = _v2_envelope(
        validation_state=validation,
        applicability_state="APPLICABLE" if all_succeeded else "PARTIAL",
        findings=(
            []
            if all_succeeded
            else [{"code": "ONE_OR_MORE_FORMULAS_WITHHELD"}]
        ),
        result={
            "corpus_id": payload["corpus_id"],
            "frozen_corpus_sha256": expected_hash,
            "worker_count_requested": payload["worker_count"],
            "execution_order": "DETERMINISTIC_DISCOVERY_INDEX",
            "formula_results": results,
            "formula_action": "NO_CHANGE",
        },
    )
    return "SUCCEEDED", envelope, validation


def _execute_v2_engine_job(
    job_type: str, payload: dict[str, Any]
) -> tuple[str, dict[str, Any], str]:
    if job_type == "RELEASE_SIMULATION":
        return _release_simulation_v2(payload)
    if job_type == "CANDIDATE_EVALUATION":
        return _candidate_evaluation_v2(payload)
    if job_type == "SHORTLIST_EVALUATION":
        return _shortlist_v2(payload)
    if job_type in {"OPTIMIZER_SEARCH", "MODEL_BENCHMARK"}:
        return _optimizer_search_v2(payload)
    if job_type == "PREFERENCE_ANALYSIS":
        return _preference_analysis_v2(payload)
    if job_type == "BATCH_GATE":
        return _batch_gate_v2(payload)
    if job_type == "FORMULA_ANALYSIS":
        return _formula_goal_analysis_v2(payload)
    elif job_type == "RELEASE_GATE":
        terminal, result, validation = _release_gate(payload)
    elif job_type == "MIXER_SEQUENCE":
        terminal, result, validation = _mixer_sequence(payload)
    else:
        raise ValueError("UNSUPPORTED_ENGINE_JOB_TYPE")
    applicability = "APPLICABLE" if terminal == "SUCCEEDED" else "PARTIAL"
    return terminal, _v2_envelope(
        validation_state=validation,
        applicability_state=applicability,
        result={"legacy_compatible_result": result, "formula_action": "NO_CHANGE"},
    ), validation


def execute_registered_engine_job(
    job_type: str,
    payload: dict[str, Any],
    *,
    contract_version: str | None = None,
) -> tuple[str, dict[str, Any], str, dict[str, Any]]:
    """Execute one already-validated registry command without dynamic dispatch."""

    if contract_version == ENGINE_JOB_CONTRACT_VERSION_V2:
        state, result, validation = _execute_v2_engine_job(job_type, payload)
        return state, result, validation, {"executor": "closed-registry-v2"}
    if job_type == "FORMULA_ANALYSIS":
        state, result, validation = _formula_analysis(payload)
    elif job_type == "MIXER_SEQUENCE":
        state, result, validation = _mixer_sequence(payload)
    elif job_type == "SHORTLIST_EVALUATION":
        state, result, validation = _shortlist(payload)
    elif job_type == "RELEASE_GATE":
        state, result, validation = _release_gate(payload)
    elif job_type == "OPTIMIZER_SEARCH":
        state, validation = "WITHHELD", "WITHHELD_NONDISCRIMINATING_EVIDENCE"
        result = {
            "selection_status": validation,
            "ranked_candidates": [],
            "best_observed_candidate": None,
            "experimental_recommendation": None,
            "formula_action": "NO_CHANGE",
            "benchmark_equal_budget": False,
            **_FALSE_AUTHORITY,
        }
    elif job_type == "BATCH_GATE":
        state, validation = "WITHHELD", "WITHHOLD_CANONICAL_FORMULA_BINDINGS_REQUIRED"
        result = {
            "status": validation,
            "corpus_id": payload["corpus_id"],
            "frozen_corpus_sha256": payload["frozen_corpus_sha256"],
            "formula_count": len(payload["formula_ids"]),
            "formula_action": "NO_CHANGE",
            **_FALSE_AUTHORITY,
        }
    else:  # The registry prevents this branch; keep the executor fail-closed.
        raise ValueError("UNSUPPORTED_ENGINE_JOB_TYPE")
    return state, result, validation, {"executor": "closed-registry-v1"}


__all__ = ["execute_registered_engine_job"]
