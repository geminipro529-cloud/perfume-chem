"""Read-only Checkpoint 7 research-build and curve-applicability intake.

The evaluator verifies the frozen Checkpoint 6 result, the unexecuted R6
measurement protocol, and the governed Wakayama curve capability bundle.  It
does not bind or compound a formula, simulate measured headspace, execute a
measurement, evaluate a curve, fit a mixture model, or create sensory evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from engine.calibration.hashing import stable_portable_file_hash
from engine.dose_response import load_measured_intensity_capabilities
from engine.experiments.checkpoint6_readiness import (
    Checkpoint6ContractError,
    evaluate_r6_checkpoint6_readiness,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "governance"
    / "lavande_ambre_profond_r6_cp7_research_applicability_intake_20260926.json"
)

_SCHEMA_VERSION = (
    "lavande-ambre-profond-r6-cp7-research-applicability-intake-v1"
)
_PROTOCOL_STATE = "FROZEN_NONEXECUTING_RESEARCH_APPLICABILITY_INTAKE_CONTRACT"
_REQUIRED_SAMPLE_ROLES = [
    "R6_PRIMARY_RESEARCH_SAMPLE",
    "R6_INDEPENDENT_PREPARATION_REPLICATE",
    "CARRIER_OR_MATRIX_BLANK",
    "JUSTIFIED_REFERENCE_IF_PHYSICALLY_AVAILABLE",
]
_REQUIRED_PHYSICAL_PARAMETERS = [
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
_REQUIRED_SENSORY_CONTROLS = [
    "qualified_sensory_panel_or_reviewer_scope",
    "randomized_sample_codes",
    "blinding",
    "presentation_order_balance",
    "predeclared_scales",
    "rest_intervals",
    "session_identity",
    "missingness_retention",
]
_CANONICAL_EVIDENCE_KEYS = {
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
_CHECKPOINT7_BLOCKERS = [
    "HOLD_CP7_CP6_PHYSICAL_READINESS_INCOMPLETE",
    "HOLD_CP7_RESEARCH_SAMPLE_NOT_COMPOUNDED",
    "HOLD_CP7_MEASUREMENT_EXECUTION_PARAMETERS_UNRESOLVED",
    "HOLD_CP7_MEASURED_GAS_INPUTS_UNAVAILABLE",
    "HOLD_EXACT_CURVE_APPLICABILITY",
]
_AUTHORITY = {
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
_SIDE_EFFECTS = {
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


class Checkpoint7ContractError(ValueError):
    """Raised when the Checkpoint 7 intake contract cannot be trusted."""


def _file_sha256(path: Path) -> str:
    return stable_portable_file_hash(path)


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Checkpoint7ContractError(f"{label} is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise Checkpoint7ContractError(f"{label} must be a JSON object")
    return value


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Checkpoint7ContractError(f"{label} must be an object")
    return value


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise Checkpoint7ContractError(f"{label} must be a list")
    return value


def _resolve_pinned_path(
    path_text: object,
    expected_sha256: object,
    *,
    label: str,
) -> Path:
    path = (REPOSITORY_ROOT / str(path_text or "")).resolve()
    if not path.is_relative_to(REPOSITORY_ROOT.resolve()):
        raise Checkpoint7ContractError(f"{label} escapes repository")
    if not path.is_file() or _file_sha256(path) != expected_sha256:
        raise Checkpoint7ContractError(f"{label} hash drift")
    return path


def _validate_protocol_contract(protocol: Mapping[str, Any]) -> None:
    if protocol.get("schema_version") != _SCHEMA_VERSION:
        raise Checkpoint7ContractError("unsupported Checkpoint 7 schema")
    if protocol.get("state") != _PROTOCOL_STATE:
        raise Checkpoint7ContractError("Checkpoint 7 protocol state drift")

    prerequisite = _require_mapping(
        protocol.get("checkpoint6_prerequisite"), "Checkpoint 6 prerequisite"
    )
    if prerequisite != {
        "required_state": "PASS_CP6_PHYSICAL_READINESS_BOUND_NOT_COMPOUNDED",
        "observed_state": "HOLD_CP6_PHYSICAL_LINEAGE_INPUTS_INCOMPLETE",
        "satisfied": False,
        "bypass_allowed": False,
    }:
        raise Checkpoint7ContractError("Checkpoint 6 prerequisite drift")

    literature = _require_mapping(
        protocol.get("literature_source_contract"), "literature source contract"
    )
    if literature != {
        "source": "Wakayama et al. 2019 perfumery raw-material intensity curves",
        "doi": "10.1021/acs.iecr.9b01225",
        "correction_doi": "10.1021/acs.iecr.0c05822",
        "license": "CC BY-NC 4.0",
        "permitted_use": "attributed noncommercial research only",
        "commercial_use_authorized": False,
        "source_fit_overlap": "UNKNOWN",
        "threshold_equation_revision": "WAKAYAMA_DECEMBER_2020_CORRECTION",
        "threshold_roundtrip_criterion": 1.4,
        "threshold_output_unit": "ng/L_air",
    }:
        raise Checkpoint7ContractError("literature source contract drift")

    curve_input = _require_mapping(
        protocol.get("curve_input_contract"), "curve input contract"
    )
    if curve_input != {
        "physical_quantity": "GAS_MASS_CONCENTRATION",
        "phase": "AIR",
        "unit": "ug/L_air",
        "liquid_dose_allowed": False,
        "stock_fraction_allowed": False,
        "oav_allowed": False,
        "modeled_unvalidated_release_as_measured_input_allowed": False,
        "extrapolation_authorized": False,
    }:
        raise Checkpoint7ContractError("curve input contract drift")

    release_boundary = _require_mapping(
        protocol.get("release_model_boundary"), "release model boundary"
    )
    if release_boundary != {
        "dynamic_release_authority": "SIMULATION_ONLY_UNCALIBRATED",
        "dynamic_release_is_measured_headspace": False,
        "dynamic_release_is_calibrated_release": False,
        "dynamic_release_may_establish_curve_input": False,
        "headspace_oav_is_intensity": False,
        "headspace_oav_is_pleasantness": False,
        "headspace_oav_is_formula_quality": False,
    }:
        raise Checkpoint7ContractError("release model boundary drift")

    sample = _require_mapping(
        protocol.get("research_sample_contract"), "research sample contract"
    )
    if sample != {
        "required_sample_roles": _REQUIRED_SAMPLE_ROLES,
        "documentary_r5_is_physical_comparator": False,
        "complete_cp6_binding_required": True,
        "compounding_run_required": True,
        "complete_transfer_receipt_chain_required": True,
        "aging_and_storage_receipts_required": True,
        "sample_identity_receipts_required": True,
        "research_sample_compounded": False,
        "physical_formula_modified": False,
    }:
        raise Checkpoint7ContractError("research sample contract drift")

    measurement = _require_mapping(
        protocol.get("measurement_protocol_contract"), "measurement contract"
    )
    if measurement != {
        "state": "R6_SCHEMA_FROZEN_EXECUTION_PARAMETERS_UNRESOLVED",
        "execution_ready": False,
        "domains_must_remain_separate": ["BLOTTER", "SKIN"],
        "required_physical_parameters": _REQUIRED_PHYSICAL_PARAMETERS,
        "required_sensory_controls": _REQUIRED_SENSORY_CONTROLS,
        "resolved_execution_parameters": {},
        "unresolved_execution_parameter_count": 25,
    }:
        raise Checkpoint7ContractError("measurement protocol contract drift")

    applicability = _require_mapping(
        protocol.get("applicability_contract"), "applicability contract"
    )
    if applicability != {
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
    }:
        raise Checkpoint7ContractError("applicability authority drift")

    mixture = _require_mapping(
        protocol.get("mixture_challenger_contract"), "mixture challenger contract"
    )
    if mixture != {
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
    }:
        raise Checkpoint7ContractError("mixture challenger contract drift")

    endpoint = _require_mapping(
        protocol.get("endpoint_contract"), "endpoint contract"
    )
    if endpoint != {
        "physical_release": "NOT_MEASURED",
        "sensory_intensity": "NOT_ESTABLISHED",
        "character": "NOT_ESTABLISHED",
        "pleasantness": "NOT_ESTABLISHED",
        "personal_liking": "NOT_TESTED",
        "population_liking": "NOT_TESTED",
        "beauty": "PROHIBITED_DERIVED_ENDPOINT",
    }:
        raise Checkpoint7ContractError("endpoint contract drift")

    evidence = _require_mapping(
        protocol.get("canonical_current_evidence"), "canonical current evidence"
    )
    if set(evidence) != _CANONICAL_EVIDENCE_KEYS or any(
        _require_list(evidence.get(key), f"canonical evidence {key}")
        for key in _CANONICAL_EVIDENCE_KEYS
    ):
        raise Checkpoint7ContractError(
            "Checkpoint 7 canonical evidence must remain empty"
        )

    blockers = _require_list(protocol.get("checkpoint7_blockers"), "blockers")
    if blockers != _CHECKPOINT7_BLOCKERS:
        raise Checkpoint7ContractError("Checkpoint 7 blocker set drift")

    contract = _require_mapping(
        protocol.get("checkpoint7_contract"), "Checkpoint 7 contract"
    )
    if contract != {
        "state": "SOFTWARE_COMPLETE_RESEARCH_APPLICABILITY_INTAKE_HOLD",
        "hold_state": "HOLD_CP7_BUILD_MEASUREMENT_OR_APPLICABILITY_INCOMPLETE",
        "future_pass_state": "PASS_CP7_R6_RESEARCH_SAMPLE_CHARACTERIZED",
        "formula_action": "DESIGN_SUCCESSOR_UNCHANGED",
        "physical_build_state": "NOT_BOUND",
        "research_sample_state": "NOT_COMPOUNDED",
        "measurement_execution_state": "NOT_STARTED",
        "exact_curve_applicability_state": "HOLD_EXACT_CURVE_APPLICABILITY",
        "formula_modified": False,
        "inventory_modified": False,
    }:
        raise Checkpoint7ContractError("Checkpoint 7 outcome contract drift")

    authority = _require_mapping(protocol.get("authority"), "Checkpoint 7 authority")
    if authority != _AUTHORITY:
        raise Checkpoint7ContractError("Checkpoint 7 authority boundary drift")

    side_effects = _require_mapping(protocol.get("side_effects"), "side effects")
    if side_effects != _SIDE_EFFECTS:
        raise Checkpoint7ContractError("Checkpoint 7 side-effect boundary drift")


def evaluate_r6_checkpoint7_readiness(
    *, protocol_path: Path = DEFAULT_PROTOCOL_PATH
) -> dict[str, object]:
    """Return a deterministic Checkpoint 7 abstention and evidence census."""

    protocol = _load_object(protocol_path, "Checkpoint 7 protocol")
    _validate_protocol_contract(protocol)
    inputs = _require_mapping(protocol.get("inputs"), "Checkpoint 7 inputs")
    cp6_protocol_path = _resolve_pinned_path(
        inputs.get("checkpoint6_protocol_path"),
        inputs.get("checkpoint6_protocol_sha256"),
        label="Checkpoint 6 protocol",
    )
    _resolve_pinned_path(
        inputs.get("checkpoint6_evaluator_path"),
        inputs.get("checkpoint6_evaluator_sha256"),
        label="Checkpoint 6 evaluator",
    )
    cp5_protocol_path = _resolve_pinned_path(
        inputs.get("checkpoint5_protocol_path"),
        inputs.get("checkpoint5_protocol_sha256"),
        label="Checkpoint 5 protocol",
    )

    scientific_surface = _require_mapping(
        protocol.get("scientific_surface"), "scientific surface"
    )
    scientific_fingerprints: dict[str, dict[str, str]] = {}
    resolved_scientific_paths: dict[str, Path] = {}
    for key in (
        "measured_intensity_manifest",
        "source_manifest",
        "dose_response_implementation",
        "dynamic_release_implementation",
        "headspace_oav_implementation",
        "source_artifact",
        "transcription_artifact",
    ):
        record = _require_mapping(scientific_surface.get(key), key)
        path = _resolve_pinned_path(
            record.get("path"), record.get("sha256"), label=key
        )
        resolved_scientific_paths[key] = path
        scientific_fingerprints[key] = {
            "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
            "sha256": _file_sha256(path),
        }

    try:
        checkpoint6 = evaluate_r6_checkpoint6_readiness(
            protocol_path=cp6_protocol_path
        )
    except Checkpoint6ContractError as exc:
        raise Checkpoint7ContractError(
            "Checkpoint 6 evaluation failed closed"
        ) from exc
    if checkpoint6.get("report_sha256") != inputs.get("checkpoint6_report_sha256"):
        raise Checkpoint7ContractError("Checkpoint 6 report hash drift")
    if (
        checkpoint6.get("input_integrity_state") != "VERIFIED"
        or checkpoint6.get("checkpoint6_state")
        != "SOFTWARE_COMPLETE_DOCUMENTARY_INTAKE_HOLD"
        or checkpoint6.get("documentary_input_completion_state")
        != "HOLD_CP6_PHYSICAL_LINEAGE_INPUTS_INCOMPLETE"
        or checkpoint6.get("physical_binding_state") != "NOT_CREATED"
        or checkpoint6.get("reservation_state") != "NOT_CREATED"
        or checkpoint6.get("compounding_state") != "NOT_STARTED"
    ):
        raise Checkpoint7ContractError("Checkpoint 6 prerequisite report drift")
    cp6_fingerprints = _require_mapping(
        checkpoint6.get("fingerprints"), "Checkpoint 6 fingerprints"
    )
    for key in (
        "r6_successor_rows_sha256",
        "inventory_text_sha256",
        "inventory_snapshot_sha256",
        "inventory_overlay_sha256",
    ):
        if cp6_fingerprints.get(key) != inputs.get(key):
            raise Checkpoint7ContractError(f"Checkpoint 6 {key} drift")

    cp5 = _load_object(cp5_protocol_path, "Checkpoint 5 protocol")
    cp5_measurement = _require_mapping(
        cp5.get("measurement_protocol_contract"), "Checkpoint 5 measurement"
    )
    measurement = _require_mapping(
        protocol.get("measurement_protocol_contract"), "Checkpoint 7 measurement"
    )
    for key in (
        "state",
        "execution_ready",
        "domains_must_remain_separate",
        "required_physical_parameters",
        "required_sensory_controls",
        "resolved_execution_parameters",
    ):
        if cp5_measurement.get(key) != measurement.get(key):
            raise Checkpoint7ContractError("measurement protocol predecessor drift")

    capability = load_measured_intensity_capabilities(
        resolved_scientific_paths["measured_intensity_manifest"]
    )
    curves = _require_mapping(capability.get("curves"), "measured curves")
    identity_counts = Counter(
        str(
            _require_mapping(record, "curve record")
            .get("chemical_identity", {})
            .get("identity_status")
        )
        for record in curves.values()
    )
    positive_evaluable = 0
    nonpositive_cas: list[str] = []
    observed_range_count = 0
    exact_material_binding_count = 0
    for cas, raw_record in curves.items():
        record = _require_mapping(raw_record, "curve record")
        curve = _require_mapping(record.get("curve"), "curve parameters")
        try:
            slope = float(str(curve.get("slope")))
            imax = float(str(curve.get("imax")))
        except (TypeError, ValueError) as exc:
            raise Checkpoint7ContractError("curve parameter drift") from exc
        if math.isfinite(slope) and math.isfinite(imax) and slope > 0 and imax > 1.4:
            positive_evaluable += 1
        else:
            nonpositive_cas.append(str(cas))
        applicability = _require_mapping(
            record.get("applicability"), "curve applicability"
        )
        if applicability.get("observed_range_ug_l_air") is not None:
            observed_range_count += 1
        if _require_list(
            applicability.get("exact_material_ids"), "exact material IDs"
        ):
            exact_material_binding_count += 1

    curve_inventory = _require_mapping(
        protocol.get("curve_inventory_contract"), "curve inventory contract"
    )
    calculated_inventory = {
        "source_parameter_row_count": len(curves),
        "positive_evaluable_curve_count": positive_evaluable,
        "nonpositive_slope_curve_count": len(nonpositive_cas),
        "nonpositive_slope_identity": (
            nonpositive_cas[0] if len(nonpositive_cas) == 1 else None
        ),
        "identity_exact_count": identity_counts.get("EXACT", 0),
        "identity_unadjudicated_count": identity_counts.get("UNADJUDICATED", 0),
        "identity_conflict_count": identity_counts.get("CONFLICT", 0),
        "observed_range_bound_count": observed_range_count,
        "exact_material_binding_count": exact_material_binding_count,
        "current_admission_state": capability["manifest"]["admission_state"],
    }
    if dict(curve_inventory) != calculated_inventory:
        raise Checkpoint7ContractError("curve inventory contract drift")
    if (
        capability.get("status") != "HOLD"
        or capability.get("manifest_sha256")
        != scientific_fingerprints["measured_intensity_manifest"]["sha256"]
        or capability.get("reasons")
        != ["HOLD_EXACT_IDENTITY_RANGE_MATRIX_BINDING"]
    ):
        raise Checkpoint7ContractError("measured capability admission drift")

    cp6_rows = [
        _require_mapping(value, "Checkpoint 6 row")
        for value in _require_list(
            checkpoint6.get("row_documentary_intake"), "Checkpoint 6 row intake"
        )
    ]
    if len(cp6_rows) != 63 or len({row.get("source_row") for row in cp6_rows}) != 63:
        raise Checkpoint7ContractError("Checkpoint 6 row coverage drift")
    row_applicability = [
        {
            "source_row": row.get("source_row"),
            "basket": row.get("basket"),
            "material": row.get("material"),
            "candidate_stock_id": row.get("candidate_stock_id"),
            "physical_sample_available": False,
            "measured_gas_concentration_available": False,
            "exact_curve_binding_available": False,
            "observed_range_binding_available": False,
            "matrix_delivery_scenario_binding_available": False,
            "curve_applicability_state": "HOLD_EXACT_CURVE_APPLICABILITY",
            "reason_codes": [
                "CP6_PHYSICAL_BINDING_INCOMPLETE",
                "RESEARCH_SAMPLE_NOT_COMPOUNDED",
                "MEASURED_GAS_CONCENTRATION_UNAVAILABLE",
                "EXACT_CURVE_IDENTITY_RANGE_MATRIX_BINDING_UNAVAILABLE",
            ],
        }
        for row in cp6_rows
    ]

    unresolved_parameters = (
        list(_REQUIRED_PHYSICAL_PARAMETERS) + list(_REQUIRED_SENSORY_CONTROLS)
    )
    contract = _require_mapping(
        protocol.get("checkpoint7_contract"), "Checkpoint 7 contract"
    )
    authority = dict(_require_mapping(protocol.get("authority"), "authority"))
    side_effects = dict(
        _require_mapping(protocol.get("side_effects"), "side effects")
    )
    report: dict[str, object] = {
        "schema_version": "lavande-ambre-profond-r6-cp7-readiness-report-v1",
        "status": "HOLD",
        "checkpoint7_state": contract.get("state"),
        "research_applicability_state": contract.get("hold_state"),
        "input_integrity_state": "VERIFIED",
        "checkpoint6_prerequisite": dict(
            _require_mapping(
                protocol.get("checkpoint6_prerequisite"),
                "Checkpoint 6 prerequisite",
            )
        ),
        "research_sample": dict(
            _require_mapping(
                protocol.get("research_sample_contract"), "research sample contract"
            )
        ),
        "measurement_protocol": {
            **dict(measurement),
            "unresolved_execution_parameters": unresolved_parameters,
        },
        "measured_intensity_capability": {
            "status": capability["status"],
            "reasons": list(capability["reasons"]),
            "manifest_id": capability["manifest"]["manifest_id"],
            "admission_state": capability["manifest"]["admission_state"],
            "curve_inventory": calculated_inventory,
            "literature_source_contract": dict(
                _require_mapping(
                    protocol.get("literature_source_contract"),
                    "literature source contract",
                )
            ),
        },
        "curve_input_contract": dict(
            _require_mapping(protocol.get("curve_input_contract"), "curve input")
        ),
        "release_model_boundary": dict(
            _require_mapping(
                protocol.get("release_model_boundary"), "release model boundary"
            )
        ),
        "applicability_contract": dict(
            _require_mapping(
                protocol.get("applicability_contract"), "applicability contract"
            )
        ),
        "mixture_challenger_contract": dict(
            _require_mapping(
                protocol.get("mixture_challenger_contract"), "mixture contract"
            )
        ),
        "endpoint_contract": dict(
            _require_mapping(protocol.get("endpoint_contract"), "endpoint contract")
        ),
        "applicability_census": {
            "formula_row_count": len(row_applicability),
            "physical_sample_available_row_count": 0,
            "measured_gas_input_available_row_count": 0,
            "exact_curve_applicable_row_count": 0,
            "exact_curve_with_observed_range_row_count": 0,
            "exact_curve_with_matrix_delivery_scenario_row_count": 0,
            "whole_formula_curve_applicable": False,
            "mixture_challenger_executable": False,
        },
        "row_curve_applicability": row_applicability,
        "blockers": list(_CHECKPOINT7_BLOCKERS),
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
        "fingerprints": {
            "checkpoint7_protocol_sha256": _file_sha256(protocol_path),
            "checkpoint6_protocol_sha256": _file_sha256(cp6_protocol_path),
            "checkpoint6_report_sha256": checkpoint6["report_sha256"],
            "checkpoint5_protocol_sha256": _file_sha256(cp5_protocol_path),
            "r6_successor_rows_sha256": cp6_fingerprints[
                "r6_successor_rows_sha256"
            ],
            "inventory_text_sha256": cp6_fingerprints["inventory_text_sha256"],
            "inventory_snapshot_sha256": cp6_fingerprints[
                "inventory_snapshot_sha256"
            ],
            "inventory_overlay_sha256": cp6_fingerprints[
                "inventory_overlay_sha256"
            ],
            "scientific_surface": scientific_fingerprints,
        },
    }
    report["report_sha256"] = _canonical_sha256(report)
    return report


__all__ = [
    "Checkpoint7ContractError",
    "DEFAULT_PROTOCOL_PATH",
    "evaluate_r6_checkpoint7_readiness",
]
